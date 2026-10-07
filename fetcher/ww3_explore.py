"""ROADMAP oppgave J (PLAN FØRST, gjenåpnet 07.10.2026 - WAM800 er lagt ned,
se STATUS.md): utforsk met.no sin WAVEWATCH III 4 km regionale modell
("met.no WW III 4km", thredds.met.no sin fou-hi/ww3_4km-katalog) som
mulig kilde for svell/vindsjø hver for seg langs kysten. Kobles IKKE inn i
ratingen - skriver en rapport Theodor leser før noe bestemmes.

Henter BARE enkeltpunkter via OPeNDAP sitt tekstbaserte .ascii-grensesnitt
(ingen netCDF4/xarray nødvendig, bare `requests`) - aldri hele filen
(8,8 GB per kjøring). Metode per spot:

1. Rutenettet er en ROTERT POL-projeksjon (rlat/rlon er gitterkoordinater,
   latitude/longitude er de ekte geografiske 2D-feltene) - finner nærmeste
   punkt med et grovt (stride 20), så et finere (stride 2) søk i et lite
   vindu rundt det grove treffet.
2. Det nærmeste punktet kan være en LAND-celle (hs er NaN) selv om
   lat/lon-koordinaten er riktig - søker derfor i en 13x13-nabolag etter
   nærmeste VÅTE celle (samme idé som find_bw_point.py/wam800_explore.py).
3. En kort pause mellom hver spot (THREDDS sin egen advarsel: "avoid
   spawning multiple parallel sessions... can impact service availability"):
   uten den ga noen raske, tette kall en tydelig FEIL (men ikke krasjende)
   indeks for enkelte spots (sett direkte 07.10.2026 - Unstad og Steinkrøssa
   fikk et punkt 12-15 km feil i en tett kjøring, korrekt med 1 sekunds
   pause mellom). Trolig delvis/korrupt respons på et overbelastet, delt
   API, ikke en feil i selve søkelogikken - se STATUS.md.
4. Henter total (hs/dir/tp) og begge partisjonene - 0 er vindsjø, 1 er
   svell (bekreftet fra variablenes standard_name, se STATUS.md): phs0/
   ptp0/pdir0 (vindsjø), phs1/ptp1/pdir1 (svell). Retningene er ALLEREDE
   "fra" (sea_surface_wave_from_direction) - IKKE "mot" som WAM800/
   BarentsWatch sin rå API - trenger ingen +180 hvis dette en gang kobles
   inn.

Kjør: python fetcher/ww3_explore.py [spot_id eller "alle"]
Skriver data/ww3/report.md."""
import json
import math
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
OUT_DIR = ROOT / "data" / "ww3"

BASE = "https://thredds.met.no/thredds/dodsC/ww3_4km_latest_files/ww3_20261007T06Z.nc"
NRLAT, NRLON = 1026, 624
COARSE_STRIDE = 20
FINE_STRIDE = 2
WET_SEARCH_RADIUS = 8  # celler (ca 32 km ved 4 km oppløsning)
HOURS = 6

VARS = ["hs", "dir", "tp", "phs0", "ptp0", "pdir0", "phs1", "ptp1", "pdir1"]
_LEAD_BRACKETS = re.compile(r"^(\[\d+\])+,?\s*")


REQUEST_PAUSE_S = 1.0  # se moduldocstring punkt 3 - unngår korrupte/trunkerte svar


def fetch_ascii(var_expr):
    r = requests.get(f"{BASE}.ascii?{var_expr}", timeout=60)
    r.raise_for_status()
    time.sleep(REQUEST_PAUSE_S)
    return r.text


def parse_grid_block(text, varname):
    """Data-blokken for `varname` (IKKE Structure-deklarasjonen øverst) som
    en 2D-liste. Strip ALLE innledende [i]-indeksgrupper per linje (en
    skalar tids-indeks gir to indekser foran selve tallene)."""
    header_marker = f"\n{varname}["
    start = text.index(header_marker) + 1
    start = text.index("\n", start) + 1
    rows = []
    for line in text[start:].splitlines():
        if not line.startswith("["):
            break
        rest = _LEAD_BRACKETS.sub("", line)
        rows.append([float(x) for x in rest.split(",") if x.strip()])
    return rows


def nearest_index(lat_grid, lon_grid, target_lat, target_lon):
    best, best_d = None, 1e9
    for i, row_lat in enumerate(lat_grid):
        for j, (la, lo) in enumerate(zip(row_lat, lon_grid[i])):
            d = (la - target_lat) ** 2 + ((lo - target_lon) * 0.55) ** 2
            if d < best_d:
                best_d, best = d, (i, j)
    return best


MAX_REASONABLE_KM = 10.0  # se find_point() - over dette: trolig korrupt svar, prøv på nytt
MAX_RETRIES = 4


def find_point(target_lat, target_lon):
    """Som _find_point_once(), men prøver på nytt (med lengre pause) hvis
    resultatet er mistenkelig langt unna - sett direkte 07.10.2026: noen få
    raske, tette OPeNDAP-kall ga en tydelig FEIL (men ikke krasjende) indeks
    for enkelte spots (Unstad/Steinkrøssa fikk et punkt 12-15 km feil i en
    tett kjøring) - en pause mellom ENKELTKALL alene løste det ikke
    pålitelig, så resultatet valideres i stedet mot en fornuftig avstand
    (høyst MAX_REASONABLE_KM - generøst for et 4 km rutenett + søkevinduet)
    før det godtas."""
    for attempt in range(MAX_RETRIES):
        result = _find_point_once(target_lat, target_lon)
        if result and result[-1] <= MAX_REASONABLE_KM:
            return result
        print(f"  (mistenkelig avstand {result[-1] if result else '?'} km, forsøk {attempt+1}/{MAX_RETRIES} - prøver på nytt)")
        time.sleep(3.0)
    return result


def _find_point_once(target_lat, target_lon):
    """(i, j, ekte_lat, ekte_lon, avstand_km) for nærmeste VÅTE celle."""
    expr = (f"latitude.latitude[0:{COARSE_STRIDE}:{NRLAT-1}][0:{COARSE_STRIDE}:{NRLON-1}],"
            f"longitude.longitude[0:{COARSE_STRIDE}:{NRLAT-1}][0:{COARSE_STRIDE}:{NRLON-1}]")
    text = fetch_ascii(expr)
    lat_c, lon_c = parse_grid_block(text, "latitude"), parse_grid_block(text, "longitude")
    ci, cj = nearest_index(lat_c, lon_c, target_lat, target_lon)

    i0 = max(0, (ci - 1) * COARSE_STRIDE)
    i1 = min(NRLAT - 1, (ci + 1) * COARSE_STRIDE)
    j0 = max(0, (cj - 1) * COARSE_STRIDE)
    j1 = min(NRLON - 1, (cj + 1) * COARSE_STRIDE)
    expr = (f"latitude.latitude[{i0}:{FINE_STRIDE}:{i1}][{j0}:{FINE_STRIDE}:{j1}],"
            f"longitude.longitude[{i0}:{FINE_STRIDE}:{i1}][{j0}:{FINE_STRIDE}:{j1}]")
    text = fetch_ascii(expr)
    lat_f, lon_f = parse_grid_block(text, "latitude"), parse_grid_block(text, "longitude")
    bi, bj = nearest_index(lat_f, lon_f, target_lat, target_lon)
    i, j = i0 + bi * FINE_STRIDE, j0 + bj * FINE_STRIDE
    la, lo = lat_f[bi][bj], lon_f[bi][bj]

    r = WET_SEARCH_RADIUS
    i0, i1 = max(0, i - r), min(NRLAT - 1, i + r)
    j0, j1 = max(0, j - r), min(NRLON - 1, j + r)
    text = fetch_ascii(f"hs.hs[0][{i0}:1:{i1}][{j0}:1:{j1}]")
    rows = parse_grid_block(text, "hs")
    best, best_d = None, 1e9
    for ri, row in enumerate(rows):
        for rj, v in enumerate(row):
            if v == v:  # ikke NaN
                d = math.hypot(ri - (i - i0), rj - (j - j0))
                if d < best_d:
                    best_d, best = d, (i0 + ri, j0 + rj)
    if best is None:
        return None
    wi, wj = best
    # ekte km-avstand (cos(breddegrad) for lengdegraden, ikke en fast
    # tilnærming - 07.10.2026, rettet etter at en fast 0,55-faktor var for
    # unøyaktig ved 68-70 N til å fange opp korrupte svar pålitelig, se
    # find_point()) + rutenettets egen oppløsning (4 km/celle) for
    # vått-celle-søkets forskyvning fra det fine treffet.
    dlat_km = (la - target_lat) * 111.32
    dlon_km = (lo - target_lon) * 111.32 * math.cos(math.radians(target_lat))
    dist_km = math.hypot(dlat_km, dlon_km) + best_d * 4
    return wi, wj, la, lo, dist_km


def fetch_hours(i, j, hours=HOURS):
    expr = ",".join(f"{v}.{v}[0:1:{hours-1}][{i}][{j}]" for v in VARS)
    text = fetch_ascii(expr)
    out = {}
    for v in VARS:
        rows = parse_grid_block(text, v)
        out[v] = [r[0] if r and r[0] == r[0] else None for r in rows]
    return out


def main():
    config = json.loads(SPOTS.read_text(encoding="utf-8"))
    arg = sys.argv[1] if len(sys.argv) > 1 else "alle"
    lines = ["# WW3 4km-utforsking (ROADMAP oppgave J, gjenåpnet 07.10.2026)\n"]
    for spot in config["spots"]:
        if not spot.get("enabled"):
            continue
        if arg != "alle" and spot["id"] != arg:
            continue
        o = spot["offshore"]
        print(spot["name"])
        found = find_point(o["lat"], o["lon"])
        if not found:
            lines.append(f"## {spot['name']}\nIngen våt celle funnet.\n")
            continue
        i, j, la, lo, dist = found
        data = fetch_hours(i, j)
        lines.append(f"## {spot['name']}\nPunkt ({la:.4f},{lo:.4f}), indeks ({i},{j}), {dist:.1f} km fra havpunktet.\n")
        lines.append("| time | hs (total) | dir | tp | vindsjø (phs0/pdir0/ptp0) | svell (phs1/pdir1/ptp1) |")
        lines.append("|---|---|---|---|---|---|")
        for k in range(len(data["hs"])):
            lines.append(f"| {k} | {data['hs'][k]} | {data['dir'][k]} | {data['tp'][k]} | "
                         f"{data['phs0'][k]}/{data['pdir0'][k]}/{data['ptp0'][k]} | "
                         f"{data['phs1'][k]}/{data['pdir1'][k]}/{data['ptp1'][k]} |")
        lines.append("")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Skrev {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
