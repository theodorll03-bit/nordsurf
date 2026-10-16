"""Engangsverktøy (Theodors oppgave 05.10.2026, utvidet til alle spots
06.10.2026 - ROADMAP oppgave E, se STATUS.md): bygger et rutenett av
kandidatpunkter rundt hver aktiv spot (startet med Unstad og Farstadsanden -
mistanke om at dagens BarentsWatch-punkter ligger i le/for nær land eller at
svellmodellen der er upålitelig; begge viste seg for lave mot observasjoner/
andre kilder) og henter BarentsWatch for hvert punkt, 48 timer frem. Lagrer resultatet i
data/bw_point_search/result.json, committet FRA workflowen (se
.github/workflows/find_bw_point.yml) - slik kan punktene sammenlignes og nye
foreslås i en senere økt uten nøkler eller `gh` CLI lokalt.

Kjøres bare manuelt via workflow_dispatch. Skriver ALDRI ut nøkler, token
eller Authorization-headeren - samme mønster som diagnose_bw_direction.py,
som denne gjenbruker raw_barentswatch()/openmeteo_with_total_dir() fra (for
ikke å duplisere selve BarentsWatch/Open-Meteo-oppslaget).

pt() er IKKE importert fra exposure_baseline.py/check_spot.py, selv om
formelen er identisk der - de drar med seg basemap/shapely (tunge
avhengigheter, bare installert for de verktøyene), denne workflowen
installerer bare `requests`."""
import json
import math
import os
import datetime as dt
from pathlib import Path

import sources
from diagnose_bw_direction import raw_barentswatch

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "bw_point_search"
HOURS_AHEAD = 48
# 06.10.2026, ROADMAP oppgave E: utvidet fra bare Unstad/Farstadsanden til
# ALLE aktive spots, og 2000 m-ringen tatt ut (oppgaven sier 150/250/500/
# 1000 m). 8 spots x (3 retninger x 4 avstander + dagens 2 punkter) = 112
# BarentsWatch-oppslag per kjøring - greit for et manuelt engangsverktøy.
DISTANCES_KM = [0.15, 0.25, 0.5, 1.0]
OFFSETS_DEG = [-20, 0, 20]
GRID_ON = False
HOURS_BACK = 12   # 15.10.2026: ta med timene tidligere i dag (12-18 lokal) hvis BarentsWatch fortsatt serverer dem


def pt(lat, lon, bearing, d):
    return (lat + d * math.cos(math.radians(bearing)) / 110.57,
            lon + d * math.sin(math.radians(bearing)) / (111.32 * math.cos(math.radians(lat))))


# 14.10.2026, Theodors oppgave (Farstadsanden torsdag 15.10): et SNITT fra
# stranda og ut mot NV langs facing (0/150/300/500/800 m), pluss nålen Theodor
# ba om først 06.10 (62.986005/7.147075 - rettet av ham samme dag til dagens
# punkt) og BarentsWatch-kartets 2 m-punkt ved Breivika (62.98688/7.14407).
# Målet: finne punktet like utenfor brytesonen - dagens punkt (58 m fra
# pinnen) ligger nesten i fjæra, der 100 m-modellen allerede har brukket
# bølgene (0,9 m der mot 2 m 280 m lenger ute).
# 15.10.2026, Theodors oppgave (Farstadsanden - observasjon 15.10, «Holy portugal»):
# snitt langs facing fra fjæra og 1,5 km ut med 100 m mellomrom, for ALLE spots
# (de sju andre bare som rapport: punkter der Hs øker over 30 % innen 300 m
# utover tyder på at punktet ligger inne i brytesonen). Farstadsanden får i
# tillegg dagens punkt og _near (legges til av grid_points), Theodors
# opprinnelige punkt 62.986005/7.147075 og nålen 62.98688/7.14407.
TRANSECT_DISTS_M = list(range(0, int(os.environ.get("BW_SEARCH_MAX_M") or 1500) + 1, 100))   # 16.10: kan forlenges (G-frame til 3 km)
TRANSECTS = {
    "farstadsanden": {
        "bearing": 310,
        "dists_m": TRANSECT_DISTS_M,
        "extra": {"Theodors opprinnelige punkt 06.10": {"lat": 62.986005, "lon": 7.147075},
                  "nålen (BW-kartet 2 m)": {"lat": 62.98688, "lon": 7.14407}},
    },
}


def transect_for(spot):
    """Snittet for spoten: eget oppsett i TRANSECTS, ellers langs facing med standardavstandene."""
    tr = TRANSECTS.get(spot["id"])
    if tr:
        return tr
    return {"bearing": spot["facing"], "dists_m": TRANSECT_DISTS_M, "extra": {}}


def transect_points(spot):
    """Snittpunktene for spoten (se TRANSECTS), eller tomt."""
    tr = transect_for(spot)
    s = spot["spot"]
    out = {}
    for d in tr["dists_m"]:
        la, lo = pt(s["lat"], s["lon"], tr["bearing"], d / 1000)
        out[f"snitt {d}m@{tr['bearing']}"] = {"lat": round(la, 6), "lon": round(lo, 6), "bearing": tr["bearing"], "dist_m": d}
    for label, q in tr["extra"].items():
        out[f"snitt {label}"] = {"lat": q["lat"], "lon": q["lon"], "bearing": None, "dist_m": None}
    return out


def grid_points(spot):
    """Rutenett (facing, facing-20, facing+20) x (150/250/500/1000/2000 m),
    pluss dagens to punkter (barentswatch_point/_near) til sammenligning."""
    s = spot["spot"]
    facing = spot["facing"]
    points = {}
    # 15.10.2026: rutenettet (3 retninger x 4 avstander) er slått av - snittet langs facing
    # med 100 m-steg er det Theodor ba om; sett GRID_ON = True for det gamle søket
    for off in (OFFSETS_DEG if GRID_ON else []):
        bearing = (facing + off) % 360
        for d in DISTANCES_KM:
            la, lo = pt(s["lat"], s["lon"], bearing, d)
            label = f"{round(d * 1000)}m@{bearing:.0f}"
            points[label] = {"lat": round(la, 6), "lon": round(lo, 6), "bearing": bearing, "dist_m": round(d * 1000)}
    # 06.10.2026: IKKE "dagens 250m-punkt" - Farstadsanden sin barentswatch_point
    # er nå valgt manuelt av Theodor i BarentsWatch sitt eget kart (se spots.json
    # sin _barentswatch-kommentar), ikke nødvendigvis på noen av rutenett-
    # avstandene over. Nøytral etikett, riktig for alle spots.
    for key, label in (("barentswatch_point", "dagens barentswatch_point"),
                        ("barentswatch_point_near", "dagens barentswatch_point_near")):
        p = spot.get(key)
        if p:
            points[label] = {"lat": p["lat"], "lon": p["lon"], "bearing": None, "dist_m": None}
    points.update(transect_points(spot))
    return points


def search_spot(spot, now, cutoff):
    print(f"\n===== {spot['name']} (facing {spot['facing']}) =====")
    # 06.10.2026 (fysikk-kontrollør, oppgave E): SAMME henting som produksjonen
    # (GFS Wave med standardmodellen som reserve, time for time) - GFS alene
    # har ingen dekning ved Russelv/Lenangsøyra sine havpunkt i Ullsfjorden og
    # ga 0,0 på alt der i første kjøring, så prosent-metoden ble umulig.
    om = sources.openmeteo_marine(spot["offshore"]["lat"], spot["offshore"]["lon"])
    points = grid_points(spot)
    out = {"facing": spot["facing"], "offshore_point": spot["offshore"], "points": {}}

    for label, p in points.items():
        print(f"  -- {label}: forespurt lat={p['lat']}, lon={p['lon']} --")
        rows = raw_barentswatch(p["lat"], p["lon"])
        hours, chosen_point = {}, None
        for row in rows:
            t = row.get("forecastTime") or row.get("time") or row.get("validTime")
            if not t:
                continue
            tdt = sources.parse_iso(t)
            if tdt < now - dt.timedelta(hours=HOURS_BACK) or tdt > cutoff:
                continue
            if chosen_point is None:
                chosen_point = {"lat": row.get("latitude"), "lon": row.get("longitude")}
            bw_dir_raw = row.get("totalMeanWaveDirection")
            # mot -> fra, se sources.barentswatch_point() sin docstring.
            bw_dir = (bw_dir_raw + 180) % 360 if bw_dir_raw is not None else None
            k = sources.hour_key(tdt)
            omk = om.get(k, {})
            hours[k] = {
                "height": row.get("totalSignificantWaveHeight"),
                "max_height": row.get("expectedMaximumWaveHeight"),
                "dir": bw_dir,
                "period": row.get("totalPeakPeriod"),
                "source": row.get("source"),
                "file_source": row.get("fileSource"),
                "offshore_swell_height": omk.get("swell_height"),
                "offshore_swell_dir": omk.get("dir"),
                "offshore_total_height": omk.get("height"),
                "offshore_swell_model": omk.get("swell_model"),
            }
        print(f"     {len(hours)} timer, BarentsWatch valgte punkt: {chosen_point}")
        out["points"][label] = {
            "requested": p,
            "chosen_point": chosen_point,
            "link": f"https://www.barentswatch.no/bolgevarsel/point/{p['lon']}_{p['lat']}",
            "hours": hours,
        }
    return out


def main():
    spots = {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
    # 16.10.2026 (nattjobben, ROADMAP K del C.1): BW_SEARCH_KANDIDATER=id,… henter snittet for spots fra
    # spotfabrikken (data/kandidater/bygget/<id>.json) i stedet for spots.json - samme snitt og samme regel.
    kand = [x.strip() for x in os.environ.get("BW_SEARCH_KANDIDATER", "").split(",") if x.strip()]
    if kand:
        spots = {}
        for kid in kand:
            f = ROOT / "data" / "kandidater" / "bygget" / f"{kid}.json"
            if not f.exists():
                print(f"Hopper over {kid}: {f} finnes ikke (kjør tools/bygg_spot.py først)")
                continue
            sp = json.loads(f.read_text(encoding="utf-8"))["spot"]
            if sp.get("facing") is None or not sp.get("offshore"):
                print(f"Hopper over {kid}: facing eller havpunkt mangler")
                continue
            spots[kid] = sp
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now + dt.timedelta(hours=HOURS_AHEAD)

    # 15.10.2026 (nattjobben, ROADMAP K del 0.4): BW_SEARCH_SPOTS=steinkrossa,… begrenser søket til
    # noen spots, BW_SEARCH_OUT=<fil> skriver til en egen fil i stedet for result.json (som da står urørt).
    only = {x.strip() for x in os.environ.get("BW_SEARCH_SPOTS", "").split(",") if x.strip()}
    result = {"generated": now.isoformat(), "hours_ahead": HOURS_AHEAD,
              "spots": {sid: search_spot(s, now, cutoff) for sid, s in spots.items() if s.get("enabled") and (not only or sid in only)}}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / (os.environ.get("BW_SEARCH_OUT") or "result.json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSkrev {out_path}")


if __name__ == "__main__":
    main()
