"""Engangsverktøy (Theodors oppgave 05.10.2026 - se STATUS.md): bygger et
rutenett av kandidatpunkter rundt Unstad og Farstadsanden (mistanke om at
dagens BarentsWatch-punkter ligger i le/for nær land eller svellmodellen
der er upålitelig - Unstad sin surfehøyde og Farstadsanden sin BarentsWatch-
totalhøyde har begge vist seg for lave mot observasjoner/andre kilder) og
henter BarentsWatch for hvert punkt, 48 timer frem. Lagrer resultatet i
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
import datetime as dt
from pathlib import Path

import sources
from diagnose_bw_direction import raw_barentswatch, openmeteo_with_total_dir

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "bw_point_search"
HOURS_AHEAD = 48
DISTANCES_KM = [0.15, 0.25, 0.5, 1.0, 2.0]
OFFSETS_DEG = [-20, 0, 20]
SPOT_IDS = ["unstad", "farstadsanden"]


def pt(lat, lon, bearing, d):
    return (lat + d * math.cos(math.radians(bearing)) / 110.57,
            lon + d * math.sin(math.radians(bearing)) / (111.32 * math.cos(math.radians(lat))))


def grid_points(spot):
    """Rutenett (facing, facing-20, facing+20) x (150/250/500/1000/2000 m),
    pluss dagens to punkter (barentswatch_point/_near) til sammenligning."""
    s = spot["spot"]
    facing = spot["facing"]
    points = {}
    for off in OFFSETS_DEG:
        bearing = (facing + off) % 360
        for d in DISTANCES_KM:
            la, lo = pt(s["lat"], s["lon"], bearing, d)
            label = f"{round(d * 1000)}m@{bearing:.0f}"
            points[label] = {"lat": round(la, 6), "lon": round(lo, 6), "bearing": bearing, "dist_m": round(d * 1000)}
    for key, label in (("barentswatch_point", "dagens 250m-punkt"), ("barentswatch_point_near", "dagens 150m-punkt")):
        p = spot.get(key)
        if p:
            points[label] = {"lat": p["lat"], "lon": p["lon"], "bearing": None, "dist_m": None}
    return points


def search_spot(spot, now, cutoff):
    print(f"\n===== {spot['name']} (facing {spot['facing']}) =====")
    om = openmeteo_with_total_dir(spot["offshore"]["lat"], spot["offshore"]["lon"])
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
            if tdt < now or tdt > cutoff:
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
                "offshore_swell_dir": omk.get("swell_dir"),
                "offshore_total_height": omk.get("wave_height"),
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
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now + dt.timedelta(hours=HOURS_AHEAD)

    result = {"generated": now.isoformat(), "hours_ahead": HOURS_AHEAD,
              "spots": {sid: search_spot(spots[sid], now, cutoff) for sid in SPOT_IDS}}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "result.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSkrev {out_path}")


if __name__ == "__main__":
    main()
