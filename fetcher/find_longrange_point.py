"""Engangsverktøy (Theodors oppgave 07.10.2026 - Lyngen-spotene viste "-" i
hele langtidssonen fra fredag av): finner et sekundært havpunkt for
GFS Wave sin langtidsdel når hovedpunktet ligger i en rute det grove
0,25-graders rutenettet regner som land (smale sund/gap mellom øyer -
bekreftet for Russelv og Lenangsøyra, se STATUS.md og spots.json sin
`_offshore_longrange`-kommentar). Metoden: gå videre ut fra havpunktet,
i SAMME retning som spoten -> havpunktet allerede peker, til GFS Wave
har reell dekning (ikke bokstavelig 0,0 på alt).

Lett verktøy, bare `requests` (ikke basemap/shapely som check_spot.py/
exposure_baseline.py - unngår den tunge installasjonen for noe som bare
trenger ekte nettverksoppslag, ikke kystlinjegeometri). Kjør:
    python fetcher/find_longrange_point.py <spot_id eller alle>
"""
import json
import math
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"

STEP_KM = 5.0
MAX_KM = 60.0
CHECK_DAYS = 2  # nok til å skille "rutenettet mangler punktet helt" fra en rolig time


def bearing(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def pt(lat, lon, bearing_deg, d_km):
    return (lat + d_km * math.cos(math.radians(bearing_deg)) / 110.57,
            lon + d_km * math.sin(math.radians(bearing_deg)) / (111.32 * math.cos(math.radians(lat))))


def gfs_coverage(lat, lon, days=CHECK_DAYS):
    """(antall_ikke_null, totalt, node_lat, node_lon) for wave_height over
    `days` døgn, GFS Wave. 07.10.2026, fysikk-kontrollørens funn: Open-Meteo
    svarer med den FAKTISKE rutenettnoden den brukte (toppnivå latitude/
    longitude i JSON-svaret, ofte ulik koordinaten man spurte om - et
    0,25-graders rutenett snapper til nærmeste node). Et punkt som akkurat
    består dekningssjekken ligger per definisjon rett ved en rutenettgrense
    - bruk NODEN, ikke spørre-koordinaten, som endelig svar, ellers kan et
    senere, identisk spørsmål i prinsippet snappe til en annen (verre) node."""
    params = {"latitude": lat, "longitude": lon, "hourly": "wave_height",
              "timezone": "GMT", "forecast_days": days, "models": "ncep_gfswave025"}
    r = requests.get("https://marine-api.open-meteo.com/v1/marine", params=params, timeout=30)
    r.raise_for_status()
    d = r.json()
    heights = d["hourly"]["wave_height"]
    nonzero = sum(1 for v in heights if v not in (None, 0))
    return nonzero, len(heights), d["latitude"], d["longitude"]


def find_point(spot_lat, spot_lon, off_lat, off_lon, step_km=STEP_KM, max_km=MAX_KM):
    """Returnerer (node_lat, node_lon, avstand_km, retning) for GFS sin
    FAKTISKE rutenettnode ved første punkt lenger ute enn havpunktet, i
    samme retning, med full dekning - eller None."""
    b = bearing(spot_lat, spot_lon, off_lat, off_lon)
    d = 0.0
    while d <= max_km:
        lat, lon = pt(off_lat, off_lon, b, d)
        nonzero, total, node_lat, node_lon = gfs_coverage(lat, lon)
        print(f"  d={d:5.1f} km ({lat:.4f},{lon:.4f}) -> node ({node_lat:.4f},{node_lon:.4f}): {nonzero}/{total} timer ikke-null")
        if nonzero >= total - 2:
            return node_lat, node_lon, d, b
        d += step_km
    return None


def main():
    config = json.loads(SPOTS.read_text(encoding="utf-8"))
    arg = sys.argv[1] if len(sys.argv) > 1 else "alle"
    for spot in config["spots"]:
        if not spot.get("enabled"):
            continue
        if arg != "alle" and spot["id"] != arg:
            continue
        o = spot["offshore"]
        nonzero, total, _, _ = gfs_coverage(o["lat"], o["lon"], days=16)
        if nonzero >= total - 2:
            print(f"{spot['name']}: havpunktet har full dekning ({nonzero}/{total}) - trenger ikke offshore_longrange")
            continue
        print(f"{spot['name']}: havpunktet mangler dekning ({nonzero}/{total} over 16 dager) - søker videre ut")
        found = find_point(spot["spot"]["lat"], spot["spot"]["lon"], o["lat"], o["lon"])
        if found:
            lat, lon, d, b = found
            print(f"  -> FUNNET: {lat:.4f}, {lon:.4f} ({d} km videre ut i retning {b:.1f} grader)")
        else:
            print(f"  -> ingen dekning funnet innen {MAX_KM} km - trenger manuell vurdering")


if __name__ == "__main__":
    main()
