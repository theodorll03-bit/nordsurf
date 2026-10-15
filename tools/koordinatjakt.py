"""Koordinatjakt (ROADMAP K del A2 punkt 2-3 og 5-6, 15.10.2026): foreslår spotens punkt ut fra
bevisene i privat/kandidater/bevis/<id>/ (tools/koordinat_bevis.py) og OSM-kysten (tools/kystdata.py),
etter konvensjonen i data/kandidater/KONVENSJON.md.

Hypoteser: listepinnen, stedsnavntreff (navn/aliaser i kommunen, og strand/vik/odde/nes/skjær/os innen
3 km), OSM-strender (natural=beach/sand/shingle) og nærmeste vannkant. Valg etter type:
  beachbreak: midt på strandas sjøkant (den delen av strandpolygonet som ligger mot vannet), flyttet
              OFFSET_M ut i sjøen vinkelrett på vannkanten
  pointbreak: tuppen av odden/neset (stedsnavn) - nærmeste vannkant, OFFSET_M ut
  reef:       skjæret/grunna (stedsnavn) hvis det finnes, ellers som beachbreak/vannkant
  elveos:     utenfor osen: vannkanten nærmest os-/elvenavnet, OFFSET_M ut
  ellers:     nærmeste vannkant til søkesenteret, OFFSET_M ut (metode «vannkant»)

Sikkerhet (Theodors fire kjennetegn): navnetreff, riktig strand/bunntype, brytende bølger eller surfbar
formasjon synlig, retningen stemmer (fasing i punktet mot best_swell_dir ≤ 60°). A = alle fire, B = to
av fire, C = resten. Flyfoto er ikke åpent (Norge i bilder krever innlogging), så det tredje kjennetegnet
kan ikke vurderes her - ingen kandidat kan få A før Theodor har sett på flyfoto (tools/koordinatsjekk/).

  python tools/koordinatjakt.py --blind <id …>   validering: start fra stedsnavnet, aldri listepinnen
  python tools/koordinatjakt.py                  alle kandidater → data/kandidater/posisjoner.json/.md"""
import datetime as dt
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

import shapely
import shapely.ops
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import kystdata  # noqa: E402
import kandidat_triage as kt  # noqa: E402

KAND = ROOT / "data" / "kandidater" / "kandidater.json"
BEVIS = ROOT / "privat" / "kandidater" / "bevis"
OUT_JSON = ROOT / "data" / "kandidater" / "posisjoner.json"
OUT_MD = ROOT / "data" / "kandidater" / "posisjoner.md"
OFFSET_M = 100          # KONVENSJON.md: de 8 nålene ligger 24-153 m ut fra vannkanten, median ca. 105 m
SEAEDGE_M = 40          # del av strandpolygonets kant som regnes som sjøkant (innen 40 m av vannkanten)
NAME_NEAR_M = 1000
FLAG_MOVED_M = 500
FLAG_CLOSE_M = 100
POINT_TYPES = {"Odde", "Nes", "Tange", "Halvøy"}
REEF_TYPES = {"Skjær", "Grunne"}
OS_TYPES = {"Os", "Elv"}
STRAND_TYPES = {"Strand", "Sand", "Fjære"}


def norm(s):
    s = (s or "").lower().replace("æ", "ae").replace("ø", "o").replace("å", "a")
    s = unicodedata.normalize("NFD", s)
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in s if unicodedata.category(c) != "Mn")).strip()


def stems(k):
    """Navnebiter å lete etter: navn og aliaser, uten parenteser og generiske ord."""
    generic = {"beach", "strand", "stranda", "point", "reef", "left", "right", "the", "bay", "sand", "sanden", "nord", "sor", "vest", "ost"}
    out = set()
    for n in [k["name"]] + k.get("aliases", []):
        n = norm(n.split("(")[0])
        for w in n.split():
            if len(w) >= 4 and w not in generic:
                out.add(w)
    return out


def name_match(name, st):
    n = norm(name)
    return any(s in n or (len(n) >= 4 and n in s) for s in st)


def kind(k):
    bt = (k["hint"].get("break_type") or "").lower()
    if "river" in bt:
        return "elveos"
    if bt.startswith("point"):
        return "point"
    if bt.startswith("reef") or bt.startswith("slab"):
        return "reef"
    if "beach" in bt:
        return "beach"
    return "ukjent"


class Lokal:
    """Lokal asimut-ekvidistant projeksjon rundt søkesenteret, med OSM-land og vannkant."""

    def __init__(self, land, lat, lon):
        self.lat, self.lon = lat, lon
        self.fwd = Transformer.from_crs(4326, f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m", always_xy=True)
        self.inv = Transformer.from_crs(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m", 4326, always_xy=True)
        self.land, edge = kt.local_land(land, lat, lon)
        self.coast = self.land.boundary.difference(edge.buffer(1))
        shapely.prepare(self.land)

    def xy(self, lat, lon):
        return self.fwd.transform(lon, lat)

    def ll(self, x, y):
        lo, la = self.inv.transform(x, y)
        return la, lo

    def to_water(self, p, toward=None):
        """Nærmeste punkt på vannkanten, flyttet OFFSET_M ut i sjøen (bort fra land)."""
        c = shapely.ops.nearest_points(self.coast, p)[0]
        best = None
        for ang in range(0, 360, 10):
            q = Point(c.x + OFFSET_M * math.sin(math.radians(ang)), c.y + OFFSET_M * math.cos(math.radians(ang)))
            if self.land.contains(q) or self.land.distance(q) < OFFSET_M * 0.6:
                continue
            score = self.land.distance(q) - (0 if toward is None else 0.3 * q.distance(toward))
            if best is None or score > best[0]:
                best = (score, q)
        return best[1] if best else c


def osm_beaches(osm, L):
    out = []
    for e in osm.get("elements", []):
        t = e.get("tags", {})
        if t.get("natural") not in ("beach", "sand", "shingle"):
            continue
        rings = []
        if e["type"] == "way" and e.get("geometry"):
            rings.append([L.xy(n["lat"], n["lon"]) for n in e["geometry"]])
        elif e["type"] == "relation":
            for m in e.get("members", []):
                if m.get("role") == "outer" and m.get("geometry"):
                    rings.append([L.xy(n["lat"], n["lon"]) for n in m["geometry"]])
        for r in rings:
            if len(r) < 3:
                continue
            g = Polygon(r).buffer(0) if r[0] == r[-1] and len(r) >= 4 else LineString(r)
            if not g.is_empty:
                out.append({"geom": g, "name": t.get("name"), "natural": t.get("natural")})
    return out


def surfing_nodes(osm, L):
    pts = []
    for e in osm.get("elements", []):
        if e.get("tags", {}).get("sport") == "surfing":
            if "lat" in e:
                pts.append(Point(*L.xy(e["lat"], e["lon"])))
            elif e.get("geometry"):
                pts.append(LineString([L.xy(n["lat"], n["lon"]) for n in e["geometry"]]).centroid)
    return pts


def seaward_mid(beach, L):
    """Midt på den delen av strandas kant som ligger mot vannet."""
    edge = beach.boundary if beach.geom_type.endswith("Polygon") else beach
    sea = edge.intersection(L.coast.buffer(SEAEDGE_M))
    lines = [g for g in getattr(sea, "geoms", [sea]) if g.geom_type == "LineString" and g.length > 0]
    if lines:
        merged = shapely.ops.linemerge(lines)
        parts = list(getattr(merged, "geoms", [merged]))
        longest = max(parts, key=lambda g: g.length)
        return longest.interpolate(0.5, normalized=True), longest.length
    return beach.centroid, 0.0


def choose(k, sn, osm, land, center, pin):
    """(punkt i lokal xy, metode, bevis-dict) for kandidaten."""
    L = Lokal(land, center["lat"], center["lon"])
    st = stems(k)
    typ = kind(k)
    names = []
    for h in sn.get("navn_treff", []) + sn.get("naer", []):
        x, y = L.xy(h["lat"], h["lon"])
        names.append({**h, "p": Point(x, y), "match": name_match(h["navn"], st), "base": h["type"].split(" ")[0]})
    matched = [h for h in names if h["match"]]
    beaches = osm_beaches(osm, L)
    for b in beaches:
        b["match"] = bool(b["name"]) and name_match(b["name"], st)
        b["dist"] = b["geom"].distance(Point(0, 0))
        b["near_name"] = min([b["geom"].distance(h["p"]) for h in matched] or [1e9])
    pin_p = Point(*L.xy(pin["lat"], pin["lon"])) if pin else None
    anchor = pin_p or Point(0, 0)   # blind: startpunktet bevisene ble hentet rundt (sentrum i den lokale projeksjonen)
    ev = {"type": typ, "stedsnavn_treff": sorted({f"{h['navn']} ({h['type']})" for h in matched})[:6], "_matched": matched,
          "osm_strender": len(beaches), "osm_surfing": len(surfing_nodes(osm, L))}

    def pick_named(types):
        # innen 1,5 km av startpunktet - et stedsnavn lenger unna er en annen plass (elvenavnets punkt ligger midt på elva)
        cands = ([h for h in matched if h["base"] in types and h["p"].distance(anchor) <= 1500]
                 or [h for h in names if h["base"] in types and h["p"].distance(anchor) <= 1500])
        return min(cands, key=lambda h: (not h["match"], h["p"].distance(anchor))) if cands else None

    if typ == "point":
        h = pick_named(POINT_TYPES)
        if h:
            ev["grunnlag"] = f"odde/nes: {h['navn']}"
            return L.to_water(h["p"]), "pointbreak: tuppen av odden (stedsnavn) → vannkanten", ev, L
    if typ == "reef":
        h = pick_named(REEF_TYPES)
        if h and not L.land.contains(h["p"]):
            ev["grunnlag"] = f"skjær/grunne: {h['navn']}"
            return h["p"], "reef: skjæret/grunna (stedsnavn)", ev, L
    if typ == "elveos":
        h = pick_named(OS_TYPES)
        if h:
            ev["grunnlag"] = f"os/elv: {h['navn']}"
            return L.to_water(h["p"]), "elveos: vannkanten ved os-/elvenavnet", ev, L
    if beaches and typ in ("beach", "ukjent", "reef", "point"):
        def score(b):
            return (b["match"] * 3 + (b["near_name"] <= 150) * 2 - b["geom"].distance(anchor) / 1000.0
                    + min(b["geom"].length, 2000) / 4000.0)
        cand = [b for b in beaches if b["geom"].distance(anchor) <= 1500 or b["match"]]
        if cand:
            b = max(cand, key=score)
            mid, seal = seaward_mid(b["geom"], L)
            ev["grunnlag"] = f"OSM-strand{' «' + b['name'] + '»' if b['name'] else ''} ({b['natural']}, sjøkant {seal:.0f} m)"
            ev["strand_navnetreff"] = b["match"]
            return L.to_water(mid), "beachbreak: midt på strandas sjøkant (OSM) → 100 m ut", ev, L
    base = anchor
    ev["grunnlag"] = "ingen strand/odde funnet - nærmeste vannkant"
    return L.to_water(base), "vannkant nærmest " + ("listepinnen" if pin_p else "stedsnavnet"), ev, L


def sikkerhet(k, ev, fas, best, p):
    # navnetreff: et stedsnavn med spotens navn innen 1 km av punktet, eller OSM-stranda bærer navnet
    n = any(h["p"].distance(p) <= NAME_NEAR_M for h in ev["_matched"]) or bool(ev.get("strand_navnetreff"))
    b = ev.get("grunnlag", "").startswith(("OSM-strand", "odde", "skjær", "os/elv"))
    v = False   # ingen åpne flyfoto - kan ikke vurderes her
    r = fas is not None and best is not None and kt.angle_diff(fas, best) <= kt.AVVIK_FLAGG
    score = sum([n, b, v, r])
    grad = "A" if score == 4 else "B" if score >= 2 else "C"
    return grad, {"navnetreff": n, "strand_bunn": b, "synlig": None, "retning": r}


def begrunnelse(grad, kj, ev, flag):
    hvor = ev.get("grunnlag", "")
    ok = [t for t, v in (("navnetreff", kj["navnetreff"]), ("strand/bunntype", kj["strand_bunn"]), ("retningen", kj["retning"])) if v]
    s1 = f"Plassert etter {hvor}; stemmer: {', '.join(ok) or 'ingenting av de tre vi kan sjekke'}."
    s2 = "Brytende bølger er ikke sett (ingen åpne flyfoto) - Theodor må se." if grad != "C" else "For lite støtte - Theodor må se."
    if flag:
        s2 = s2[:-1] + f"; flagg: {', '.join(flag)}."
    return f"{s1} {s2}"


def run(kand, land, blind):
    out = {}
    for k in kand:
        d = BEVIS / k["id"]
        snf, osf = d / ("stedsnavn_blind.json" if blind else "stedsnavn.json"), d / ("osm_blind.json" if blind else "osm.json")
        if not snf.exists() or not osf.exists():
            out[k["id"]] = {"sikkerhet": "C", "metode": "mangler bevis", "begrunnelse": "Bevisene er ikke hentet (koordinat_bevis.py).", "spot": None}
            continue
        sn, osm = json.loads(snf.read_text(encoding="utf-8")), json.loads(osf.read_text(encoding="utf-8"))
        center = sn.get("senter")
        if not center:
            out[k["id"]] = {"sikkerhet": "C", "metode": "ingen stedsnavntreff", "begrunnelse": "Fant ikke navnet i kommunen - ingen startpunkt uten listepinnen.", "spot": None}
            continue
        pin = None if blind else k["pin_liste"]
        p, metode, ev, L = choose(k, sn, osm, land, center, pin)
        la, lo = L.ll(p.x, p.y)
        a = kt.analyse(land, la, lo)
        fas = a["sektor"]["fasing"] if a["sektor"] else None
        best = kt.parse_compass(k["hint"].get("best_swell_dir"))
        grad, kj = sikkerhet(k, ev, fas, best, p)
        moved = round(Point(*L.xy(k["pin_liste"]["lat"], k["pin_liste"]["lon"])).distance(p))
        flag = []
        if moved > FLAG_MOVED_M:
            flag.append(f"flyttet {moved} m fra listepinnen")
        if fas is not None and best is not None and kt.angle_diff(fas, best) > kt.AVVIK_FLAGG:
            flag.append(f"fasing {fas:.0f}° mot lista {best:.0f}°")
        if not a["sektor"]:
            flag.append("ingen åpen sektor i punktet")
        out[k["id"]] = {"spot": {"lat": round(la, 6), "lon": round(lo, 6)}, "sikkerhet": grad, "metode": metode, "flyttet_m": moved,
                        "kjennetegn": kj, "fasing": fas, "sektor": a["sektor"], "kyst_m": a["kyst_m"], "paa_land": a["paa_land"],
                        "stedsnavn_treff": ev["stedsnavn_treff"], "grunnlag": ev.get("grunnlag"), "flagg": flag,
                        "begrunnelse": begrunnelse(grad, kj, ev, flag), "satt_av": "claude-code",
                        "dato": dt.date.today().isoformat(), "blind": blind}
    # to spots nærmere enn 100 m
    ids = [i for i, v in out.items() if v.get("spot")]
    for i, a_ in enumerate(ids):
        for b_ in ids[i + 1:]:
            pa, pb = out[a_]["spot"], out[b_]["spot"]
            dd = kt_dist(pa, pb)
            if dd < FLAG_CLOSE_M:
                for x, y in ((a_, b_), (b_, a_)):
                    out[x]["flagg"].append(f"{dd:.0f} m fra {y}")
    return out


def kt_dist(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def main():
    blind = "--blind" in sys.argv
    ids = [a for a in sys.argv[1:] if not a.startswith("--")]
    kand = json.loads(KAND.read_text(encoding="utf-8"))["kandidater"]
    if ids:
        kand = [k for k in kand if k["id"] in ids]
    land = kystdata.land("osm")
    res = run(kand, land, blind)
    if blind:
        spots = {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
        print("Blind validering (spots.json leses først nå):")
        for k in kand:
            r = res[k["id"]]
            s = spots.get(k.get("nordsurf_id") or k["id"])
            d = kt_dist(r["spot"], s["spot"]) if r.get("spot") and s else None
            r["avstand_til_nal_m"] = None if d is None else round(d)
            print(f"  {k['id']:16} {r['sikkerhet']} {('–' if d is None else f'{d:5.0f} m')}  {r['metode']}  [{r.get('grunnlag')}]")
        (BEVIS / "validering_blind.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        return res
    return res


if __name__ == "__main__":
    main()
