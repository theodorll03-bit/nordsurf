"""Spotfabrikken (ROADMAP K del C, 16.10.2026): bygger et forslag til spots.json-oppføring for en kandidat
ut fra posisjonen i data/kandidater/posisjoner.json (bare sikkerhet A eller B, eller godkjent av Theodor) -
aldri fra listepinnen. Skriver data/kandidater/bygget/<id>.json og et minikart <id>.png. Endrer ALDRI
spots.json (det gjør tools/godkjenn_spot.py, og bare når Theodor kjører den).

Samme konvensjoner som spots.json og fetcher/check_spot.py:
- swell_window: retningene (hver grad) med fri linje til åpent hav (150 km) over GSHHS f, med 300 m
  kysttoleranse - største sammenhengende sektor.
- facing (Theodor 16.10): strandas normal der bølgene brekker, fra OSM-kystlinja ±150 m langs kysten fra
  nærmeste kystpunkt til nålen - ikke midten av vinduet (vinduet regnes for seg).
- offshore_wind: motsatt av facing ±45° (Theodor 16.10; ±60 var feil), merket «standard, ubekreftet».
- offshore (havpunkt): som check_spot.py - langs midten av vinduet, minst 5 km ut og 10 km åpent hav rundt.
- barentswatch_point: snittregelen 15.10 (første punkt ut fra stranda med minst 8 m dyp og flat Hs). Hs må
  hentes fra BarentsWatch i Actions (find_bw_point.yml) - lokalt finnes bare dybden (EMODnet Bathymetry REST),
  så punktet her er FORELØPIG: første snittpunkt med EMODnet-dybde ≥ 8 m, merket «venter på BarentsWatch-snitt».
- tidevann: Kartverkets referansested for posisjonen (vannstand.kartverket.no, locationdata).
- ideal_height/max_height: beachbreak som Tromsø-spotene ([0.8, 2.0] / 3.5); point/reef tomt + «Theodor må sette».
- Ingen local_rules.

  python tools/bygg_spot.py <kandidat-id …>
  python tools/bygg_spot.py --kjent <spots.json-id …>   validering mot de 8 (posisjonen fra spots.json)
Kystdata fra tools/kystdata.py (privat/geodata/, sett NORDSURF_PRIVAT hvis privat/ ligger et annet sted)."""
import datetime as dt
import json
import math
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import shapely
import shapely.ops
from shapely.geometry import LineString, Point

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import kystdata  # noqa: E402
import kandidat_triage as kt  # noqa: E402

POS = ROOT / "data" / "kandidater" / "posisjoner.json"
KAND = ROOT / "data" / "kandidater" / "kandidater.json"
OUT = ROOT / "data" / "kandidater" / "bygget"
UA = "nordsurf/1.0 (ikke-kommersiell surfevarsel; github.com/theodorll03-bit/nordsurf)"
OPEN_KM = 150
COAST_FUZZ_M = 300
WIN_MIN_DEG = 3      # smalere åpne sektorer er støy (én-to stråler forbi en odde)
SKJAER_MAX_M2 = 20000   # 2 ha
FACING_HALF_M = 150   # Theodor 16.10: ±150 m langs kysten fra nærmeste kystpunkt
BW_STEP_M, BW_MAX_M, BW_MIN_DEPTH = 100, 1500, 8.0
OFFSHORE_HALF_DEG = 45
BEACH_IDEAL, BEACH_MAX = [0.8, 2.0], 3.5


def http_get(url):
    """curl - Python 3.9/LibreSSL feiler mot noen moderne TLS-tjenester."""
    p = subprocess.run(["curl", "-sf", "--max-time", "60", "-A", UA, url], capture_output=True, timeout=90)
    if p.returncode != 0:
        raise RuntimeError(f"henting feilet ({p.returncode}): {url[:80]}")
    return p.stdout


def free_m(g, bearing, max_m):
    """Fri strekning over sjø i retningen (m), med kysttoleranse som check_spot.py; 0 = blokkert fra start."""
    s = math.sin(math.radians(bearing)), math.cos(math.radians(bearing))
    fz = np.arange(0, COAST_FUZZ_M + 1, 50.0)
    land = shapely.contains_xy(g, fz * s[0], fz * s[1])
    sea = np.flatnonzero(~land)
    if not len(sea):
        return 0.0
    start = fz[sea[0]]
    d = np.arange(start, max_m + start + 1, 100.0)
    hit = np.flatnonzero(shapely.contains_xy(g, d * s[0], d * s[1]))
    return float(d[hit[0]] - start) if len(hit) else float(max_m)


def window(gshhs_local):
    shapely.prepare(gshhs_local)
    ok = [b for b in range(360) if free_m(gshhs_local, b, OPEN_KM * 1000) >= OPEN_KM * 1000]
    if not ok:
        return None, []
    runs = []
    for b in ok:
        if runs and b - runs[-1][-1] == 1:
            runs[-1].append(b)
        else:
            runs.append([b])
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == 359:
        runs[0] = runs.pop() + runs[0]
    # alle sektorer minst WIN_MIN_DEG brede (spots.json tillater flere, f.eks. Russelv [[5,15],[349,356]]); én → [a, b]
    keep = [[r[0], r[-1]] for r in runs if len(r) >= WIN_MIN_DEG]
    if not keep:
        main = max(runs, key=len)
        keep = [[main[0], main[-1]]]
    return (keep[0] if len(keep) == 1 else keep), [[r[0], r[-1]] for r in runs]


def facing_from_coast(osm_local):
    """Strandas normal der bølgene brekker (Theodor 16.10.2026): kystlinja (OSM) ±150 m langs kysten fra
    nærmeste kystpunkt til nålen; retningen er korden mellom endene, og normalen er den av de to som peker ut
    i sjøen fra kystpunktet. Ikke 500 m-snitt og ikke midten av vinduet. Returnerer (facing, usikker)."""
    o = Point(0, 0)
    near = osm_local.intersection(o.buffer(3000))
    rings = []
    for poly in getattr(near, "geoms", [near]):
        # holmer og skjær under 2 ha er ikke stranda der bølgene brekker (Farstadsanden: et skjær foran stranda
        # var nærmeste kyst og ga en normal inn i land) - de tas bort fra «nærmeste kyst»
        if poly.geom_type != "Polygon" or poly.area < SKJAER_MAX_M2:
            continue
        rings.append(LineString(poly.exterior.coords))   # ikke innsjøer (interiors) - bare sjøkysten
    if not rings:
        return None, False, None
    line = min(rings, key=lambda r: r.distance(o))
    c = shapely.ops.nearest_points(line, o)[0]
    s0, L = line.project(c), line.length
    closed = line.is_ring or line.coords[0] == line.coords[-1]
    a, b = s0 - FACING_HALF_M, s0 + FACING_HALF_M
    if closed and L > 2 * FACING_HALF_M:
        p1, p2 = line.interpolate(a % L), line.interpolate(b % L)
    else:
        p1, p2 = line.interpolate(max(0.0, a)), line.interpolate(min(L, b))
    if p1.distance(p2) < 1:
        return None, False, None
    axis = math.degrees(math.atan2(p2.x - p1.x, p2.y - p1.y)) % 360
    cand = []
    for n in ((axis + 90) % 360, (axis + 270) % 360):
        q = [Point(c.x + d * math.sin(math.radians(n)), c.y + d * math.cos(math.radians(n))) for d in (30, 100, 200, 400)]
        cand.append((sum(not osm_local.contains(p) for p in q), n))
    tie = cand[0][0] == cand[1][0]
    best = max(cand, key=lambda x: x[0])
    return round(best[1], 1), tie, round(c.distance(o))


def pt(lat, lon, bearing, d_km):
    return (lat + d_km * math.cos(math.radians(bearing)) / 110.57,
            lon + d_km * math.sin(math.radians(bearing)) / (111.32 * math.cos(math.radians(lat))))


def havpunkt(gshhs, lat, lon, win):
    """Som check_spot.py: langs midten av vinduet, fra 5 km og ut til det er 10 km åpent hav rundt."""
    if isinstance(win[0], list):
        win = max(win, key=lambda w: (w[1] - w[0]) % 360)   # havpunktet langs den bredeste sektoren
    c = (win[0] + ((win[1] - win[0]) % 360) / 2) % 360
    shapely.prepare(gshhs)
    d = 5
    while d < 80 and any(gshhs.contains(Point(*pt(*pt(lat, lon, c, d), b, r)[::-1])) for b in range(0, 360, 10) for r in (5, 10)):
        d += 1
    la, lo = pt(lat, lon, c, d)
    return {"lat": round(la, 4), "lon": round(lo, 4)}, round(c, 1), d


def depth(lat, lon):
    try:
        j = json.loads(http_get(f"https://rest.emodnet-bathymetry.eu/depth_sample?geom=POINT({lon}%20{lat})"))
        v = j.get("avg")
        return None if v is None else round(-float(v), 1)
    except Exception:  # noqa: BLE001 - manglende dybde er «mangler», aldri 0
        return None


def bw_transect(lat, lon, facing):
    rows = []
    for dm in range(0, BW_MAX_M + 1, BW_STEP_M):
        la, lo = pt(lat, lon, facing, dm / 1000)
        rows.append({"m": dm, "lat": round(la, 6), "lon": round(lo, 6), "dybde_m": depth(la, lo)})
        time.sleep(0.2)
    first = next((r for r in rows if r["dybde_m"] is not None and r["dybde_m"] >= BW_MIN_DEPTH), None)
    return rows, first


def tide_zone(lat, lon):
    try:
        x = http_get(f"https://vannstand.kartverket.no/tideapi.php?tide_request=locationdata&lat={lat}&lon={lon}&datatype=all"
                     f"&refcode=cd&lang=nb&fromtime=2026-10-16T00:00&totime=2026-10-16T01:00")
        loc = ET.fromstring(x).find(".//location")
        if loc is None:
            return None
        return {k: loc.get(k) for k in ("name", "code", "delay", "factor", "obsname")}
    except Exception:  # noqa: BLE001
        return None


def minikart(path, osm, lat, lon, spot, win, fac, offw, hav, bw, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pyproj import Transformer
    tr = Transformer.from_crs(4326, f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m", always_xy=True)
    R = 6000
    land = shapely.clip_by_rect(osm, lon - 0.25, lat - 0.08, lon + 0.25, lat + 0.08)
    land = shapely.transform(land, lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1])))
    fig, ax = plt.subplots(figsize=(6, 6), dpi=110)
    ax.set_facecolor("#B7D3DF")
    for p in getattr(land, "geoms", [land]):
        if p.geom_type == "Polygon":
            ax.fill(*p.exterior.xy, color="#F2EDE2", ec="#8F8268", lw=0.6)
    if win:
        rays = [a for w in (win if isinstance(win[0], list) else [win])
                for a in np.linspace(w[0], w[0] + (w[1] - w[0]) % 360, max(2, (w[1] - w[0]) % 360 + 1))]
        for a in rays:
            ax.plot([0, R * math.sin(math.radians(a))], [0, R * math.cos(math.radians(a))], color="#0B7483", lw=0.4, alpha=0.5)
    if fac is not None:
        ax.annotate("", xy=(2500 * math.sin(math.radians(fac)), 2500 * math.cos(math.radians(fac))), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color="#0E1A21", lw=1.8))
    if offw:
        c = (offw[0] + ((offw[1] - offw[0]) % 360) / 2) % 360
        ax.annotate("", xy=(0, 0), xytext=(2200 * math.sin(math.radians(c)), 2200 * math.cos(math.radians(c))),
                    arrowprops=dict(arrowstyle="->", color="#22A36B", lw=1.4))
    for r in rows:
        x, y = tr.transform(r["lon"], r["lat"])
        ax.plot(x, y, "o", ms=2.5, color="#55656E")
    if bw:
        x, y = tr.transform(bw["lon"], bw["lat"])
        ax.plot(x, y, "s", ms=7, color="#BF8A00", label="BarentsWatch (foreløpig)")
    ax.plot(0, 0, "o", ms=9, color="#E0623A", mec="white", label="spot")
    ax.set_xlim(-R, R)
    ax.set_ylim(-R, R)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"{spot}: vindu {win}, facing {fac}, havpunkt {hav['lat']}, {hav['lon']}", fontsize=8)
    ax.legend(loc="lower left", fontsize=7)
    ax.text(0.99, 0.01, "© OpenStreetMap-bidragsytere · 6 km", transform=ax.transAxes, ha="right", fontsize=6)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def build(sid, name, lat, lon, typ, kilde, region=None, png=True):
    gs = kystdata.land("gshhs")
    osm = kystdata.land("osm")
    from pyproj import Transformer
    def local(g, half_deg_lat, half_deg_lon):
        clip = shapely.clip_by_rect(g, lon - half_deg_lon, lat - half_deg_lat, lon + half_deg_lon, lat + half_deg_lat)
        tr = Transformer.from_crs(4326, f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m", always_xy=True)
        return shapely.transform(clip, lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1])))
    g150 = local(gs, 1.6, 1.6 / math.cos(math.radians(lat)) * 1.05)
    o_near = local(osm, 0.02, 0.05)
    win, all_runs = window(g150)
    fac, tie, kyst_m = facing_from_coast(o_near)
    flags = []
    if tie:
        flags.append("facing usikker: begge normalene på kystlinja har like mye sjø - kan være snudd 180°")
    if fac is not None and win:
        for w in (win if isinstance(win[0], list) else [win]):
            mid = (w[0] + ((w[1] - w[0]) % 360) / 2) % 360
            if kt.angle_diff(mid, fac) > 90:
                flags.append(f"vindussektor {w} ligger mer enn 90° fra facing - kan være bak stranda (tange/øyr smalere enn kysttoleransen)")
            elif kt.angle_diff(mid, fac) > 45 and kyst_m is not None and kyst_m > 100:
                # varsel, ikke regel: nålen står langt fra kysten OG facing peker langt fra vinduet - typisk en nål i
                # hjørnet av en buet strand (Farstadsanden). Hver for seg slår begge til for gode spots (konvensjonen
                # er ca. 100 m ut; Russelv/Steinkrøssa har riktig facing langt fra midten av vinduet).
                flags.append(f"facing {fac}° er {kt.angle_diff(mid, fac):.0f}° fra midten av vinduet {w}, og nærmeste kystpunkt er "
                             f"{kyst_m} m unna - står nålen i hjørnet av en buet strand? Sjekk facing")
    if fac is None:
        flags.append("fant ikke sjøkyst (over 2 ha) innen ca. 2 km - facing mangler")
    # Theodor 16.10: standard offshore-vind er motsatt av facing ±45° (6 av 8 i spots.json; ±60 var feil)
    offw = [round((fac + 180 - OFFSHORE_HALF_DEG) % 360), round((fac + 180 + OFFSHORE_HALF_DEG) % 360)] if fac is not None else None
    hav = hav_c = hav_d = None
    if win:
        hav, hav_c, hav_d = havpunkt(gs, lat, lon, win)
    else:
        flags.append("ingen retning med fri linje til åpent hav (150 km)")
    rows, first = bw_transect(lat, lon, fac) if fac is not None else ([], None)
    if fac is not None and not first:
        flags.append("ingen snittpunkt med EMODnet-dybde ≥ 8 m innen 1,5 km")
    tz = tide_zone(lat, lon)
    if not tz:
        flags.append("Kartverket ga ikke tidevannssted")
    is_beach = typ == "beach"
    if not is_beach:
        flags.append("ideal_height/max_height: Theodor må sette (ikke beachbreak)")
    spot = {
        "id": sid, "name": name, "enabled": True, "status": "forelopig", "region": region,
        "spot": {"lat": round(lat, 6), "lon": round(lon, 6)},
        "facing": fac, "swell_window": win,
        "_vindu": f"Spotfabrikken {dt.date.today().isoformat()}: fri linje til åpent hav ({OPEN_KM} km) over GSHHS f med {COAST_FUZZ_M} m kysttoleranse, alle sektorer {all_runs}; største brukt. Små øyer/skjær kan mangle i GSHHS - ubekreftet.",
        "offshore_wind": offw, "_offshore_vind": "standard, ubekreftet (motsatt av facing ±45°)",
        "offshore": hav, "_havpunkt": f"Langs midten av vinduet ({hav_c}°), {hav_d} km ut, 10 km åpent hav rundt (GSHHS f, som check_spot.py)." if hav else None,
        "barentswatch_point": {"lat": first["lat"], "lon": first["lon"]} if first else None,
        "_barentswatch": (f"FORELØPIG: første snittpunkt langs facing med EMODnet-dybde ≥ {BW_MIN_DEPTH:.0f} m ({first['m']} m ut, {first['dybde_m']} m dyp). "
                          "Venter på BarentsWatch-snitt i Actions (find_bw_point.yml) for flat Hs - regelen fra 15.10.") if first else None,
        "tidevann": tz,
        "ideal_height": BEACH_IDEAL if is_beach else None, "max_height": BEACH_MAX if is_beach else None,
        "kilde": kilde,
    }
    out = {"spot": spot, "snitt": rows, "flagg": flags, "bygget": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")}
    if png:
        OUT.mkdir(parents=True, exist_ok=True)
        minikart(OUT / f"{sid}.png", osm, lat, lon, sid, win, fac, offw, hav or {"lat": "–", "lon": "–"}, first, rows)
    return out


def arc(w):
    """Mengden hele grader i et vindu [a, b] (kan gå over 360) eller en liste av slike."""
    if w and isinstance(w[0], list):
        return set().union(*(arc(x) for x in w))
    a, b = w
    return {(a + i) % 360 for i in range(((b - a) % 360) + 1)}


def validate(ids):
    spots = {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
    rows = []
    for sid in ids:
        s = spots[sid]
        typ = "beach"
        b = build(sid, s["name"], s["spot"]["lat"], s["spot"]["lon"], typ, "validering mot spots.json", png=True)
        n = b["spot"]
        fac_d = None if n["facing"] is None else kt.angle_diff(n["facing"], s["facing"])
        ref, new = arc(s["swell_window"]), arc(n["swell_window"]) if n["swell_window"] else set()
        overlap = len(ref & new) / len(ref) if ref else None
        extra = sorted(new - ref)
        off_ref, off_new = arc(s["offshore_wind"]), arc(n["offshore_wind"]) if n["offshore_wind"] else set()
        off_ov = len(off_ref & off_new) / len(off_ref) if off_ref else None
        bwp, bwr = n["barentswatch_point"], s.get("barentswatch_point")
        bw_d = round(kt_dist(bwp, bwr)) if bwp and bwr else None
        bw_ut = round(kt_dist(bwr, s["spot"])) if bwr else None
        ok = fac_d is not None and fac_d <= 15 and overlap is not None and overlap >= 0.70
        rows.append({"id": sid, "facing": [n["facing"], s["facing"], fac_d], "vindu": [n["swell_window"], s["swell_window"], overlap, len(extra)],
                     "offshore": [n["offshore_wind"], s["offshore_wind"], off_ov], "bw": [bw_d, bw_ut, (bwp or {}), b["snitt"]],
                     "havpunkt": [n["offshore"], s["offshore"], round(kt_dist(n["offshore"], s["offshore"]) / 1000, 1) if n["offshore"] else None],
                     "tidevann": n["tidevann"], "innenfor": ok, "flagg": b["flagg"]})
        print(f"{sid:16} facing {n['facing']} / {s['facing']} (Δ {fac_d})  vindu {n['swell_window']} / {s['swell_window']} overlapp "
              f"{'–' if overlap is None else f'{overlap:.0%}'}  offshore-overlapp {'–' if off_ov is None else f'{off_ov:.0%}'}  BW-punkt Δ {bw_d} m  "
              f"{'OK' if ok else 'UTENFOR'}", flush=True)
    return rows


def kt_dist(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--kjent" in sys.argv:
        rows = validate(args)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "validering_kjente.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return
    if not POS.exists():
        sys.exit("Mangler data/kandidater/posisjoner.json - spotfabrikken bygger bare fra en kontrollert posisjon (A2), aldri fra listepinnen.")
    pos = json.loads(POS.read_text(encoding="utf-8"))["kandidater"]
    kand = {k["id"]: k for k in json.loads(KAND.read_text(encoding="utf-8"))["kandidater"]}
    for sid in args:
        p = pos.get(sid)
        if not p or not p.get("spot") or not (p.get("sikkerhet") in ("A", "B") or p.get("vurdering") == "godkjent"):
            print(f"{sid}: hopper over - posisjonen er ikke A/B eller godkjent av Theodor")
            continue
        if kand[sid].get("venter_pa_theodor"):
            print(f"{sid}: hopper over - {kand[sid]['venter_pa_theodor']}")
            continue
        k = kand[sid]
        bt = (k["hint"].get("break_type") or "").lower()
        typ = "beach" if bt.startswith("beach") else "point" if bt.startswith("point") else "reef" if bt.startswith("reef") else "ukjent"
        b = build(sid, k["name"], p["spot"]["lat"], p["spot"]["lon"], typ, "liste 15.10 + spotfabrikken", region=k.get("region"))
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{sid}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{sid}: skrev {OUT / (sid + '.json')} (flagg: {b['flagg'] or 'ingen'})")


if __name__ == "__main__":
    main()
