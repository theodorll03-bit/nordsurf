"""ROADMAP oppgave J (PLAN FØRST): utforsk met.no sin bølgemodell WAM800
(MyWave WAM, 800 m) på thredds.met.no - hvilke datasett som finnes, hvilke
regioner som dekker hver spot, variabelnavn for total/svell/vindsjø (høyde,
periode, retning og retningskonvensjon), horisont og oppdatering. Henter
BARE punktene vi trenger (OPeNDAP, ett rutepunkt per spot), aldri hele
filer. Kobles IKKE inn i ratingen - skriver en rapport (data/wam800/) som
Theodor leser før noe bestemmes (ROADMAP J.6).

Kjøres av .github/workflows/wam800.yml (skyøkten har ikke nett mot
thredds.met.no - utforskingen må skje i GitHub Actions). Lokalt:
    pip install netCDF4 numpy requests
    python fetcher/wam800_explore.py

Metode per datasett:
1. Katalogen (catalog.xml) leses og alle .nc-datasett listes.
2. Hvert datasett åpnes via OPeNDAP (bare metadata først): variabler,
   attributter (standard_name, long_name, units), tid, rutenett (lat/lon).
3. For hver spot: punktet 1,5 km ut i retning facing (ROADMAP J.2: "1 til
   2 km ut ... ikke inne i le") - nærmeste VÅTE rutepunkt (hs ikke maskert
   ved første tidssteg) til det punktet, innen 3 km. Koordinater og avstand
   rapporteres. Første datasett som dekker spoten vinner (regionene i
   WAM800 er ikke kjent på forhånd - rapporten viser hvilket som traff).
4. 48 timer hentes for punktet: total, svell og vindsjø (høyde, periode,
   retning) - variabelnavnene gjenkjennes på standard_name/long_name
   ("swell", "wind_sea"/"windsea"/"sea"), aldri hardkodet.
5. Rapport: tabell per spot mot BarentsWatch ved spoten (bw_height/bw_dir)
   og Open-Meteo/GFS svell ute (swell_offshore/dir/period) fra
   docs/data/forecast.json for samme timer.

Retningskonvensjon: rapporteres RÅTT sammen med attributtene - CLAUDE.md
sin regel (alt internt er "fra"-retning) håndheves først når/hvis dette
kobles inn, og bare etter at konvensjonen er bevist mot en kjent dag (samme
som BarentsWatch-saken 26.09.2026)."""
import datetime as dt
import json
import math
import os
import re
import sys
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
FORECAST = ROOT / "docs" / "data" / "forecast.json"
OUT_DIR = ROOT / "data" / "wam800"

THREDDS = "https://thredds.met.no/thredds"
# Kandidatkataloger - den første som svarer brukes, resten står i rapporten.
CATALOGS = [
    "fou-hi/mywavewam800/catalog.xml",
    "fou-hi/mywavewam800m/catalog.xml",
    "fou-hi/mywavewam800s/catalog.xml",
    "fou-hi/catalog.xml",
]
POINT_OUT_KM = 1.5
MAX_DIST_KM = 3.0
HOURS = 48
UA = {"User-Agent": f"nordsurf-wam800-explore ({os.environ.get('UA_CONTACT', 'ukjent-kontakt')})"}


def pt(lat, lon, bearing, d_km):
    return (lat + d_km * math.cos(math.radians(bearing)) / 110.57,
            lon + d_km * math.sin(math.radians(bearing)) / (111.32 * math.cos(math.radians(lat))))


def dist_km(lat1, lon1, lat2, lon2):
    dlat = (lat2 - lat1) * 110.57
    dlon = (lon2 - lon1) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dlat, dlon)


def list_catalog(path):
    """Alle datasett (navn, urlPath) i en THREDDS-katalog, pluss underkataloger."""
    url = f"{THREDDS}/catalog/{path}"
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {"t": "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"}
    datasets, subs = [], []
    for d in root.iter("{http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0}dataset"):
        up = d.get("urlPath")
        if up and up.endswith(".nc"):
            datasets.append((d.get("name"), up))
    for c in root.iter("{http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0}catalogRef"):
        href = c.get("{http://www.w3.org/1999/xlink}href")
        if href:
            subs.append((c.get("{http://www.w3.org/1999/xlink}title"), href))
    return datasets, subs


def classify_vars(ds):
    """Finn total/svell/vindsjø-variabler for høyde, periode og retning ut
    fra navn og attributter. Returnerer dict {rolle: variabelnavn} og en
    liste med alle variabler (navn, dims, attributter) til rapporten."""
    info, roles = [], {}
    for name, v in ds.variables.items():
        attrs = {k: str(getattr(v, k)) for k in ("standard_name", "long_name", "units") if hasattr(v, k)}
        info.append({"name": name, "dims": list(v.dimensions), "shape": list(v.shape), **attrs})
        text = (name + " " + attrs.get("standard_name", "") + " " + attrs.get("long_name", "")).lower()
        if len(v.dimensions) < 2:
            continue
        part = "swell" if "swell" in text else ("sea" if ("wind_sea" in text or "windsea" in text or "wind sea" in text or re.search(r"\bsea\b", name.lower())) else "total")
        if "height" in text or name.lower().startswith("hs") or "significant" in text:
            kind = "hs"
        elif "period" in text or name.lower().startswith(("tp", "tm", "t0")):
            kind = "tp"
        elif "direction" in text or name.lower().startswith(("thq", "dir", "th")):
            kind = "dir"
        else:
            continue
        key = f"{part}_{kind}"
        # foretrekk peak-periode (tp) foran mean (tm) der begge finnes
        if key not in roles or ("peak" in text and "peak" not in roles[key + "_text"]):
            roles[key] = name
            roles[key + "_text"] = text
    return {k: v for k, v in roles.items() if not k.endswith("_text")}, info


def grid(ds):
    """(lat2d, lon2d) uansett om rutenettet er 1D (lat/lon-vektorer) eller 2D."""
    import numpy as np
    for la_name, lo_name in (("latitude", "longitude"), ("lat", "lon")):
        if la_name in ds.variables and lo_name in ds.variables:
            la, lo = ds.variables[la_name][:], ds.variables[lo_name][:]
            if la.ndim == 1:
                lo2, la2 = np.meshgrid(lo, la)
                return la2, lo2
            return la, lo
    raise RuntimeError("fant ikke lat/lon i datasettet")


def nearest_wet(la2, lo2, wet, lat, lon, max_km):
    """Indeks (j, i) til nærmeste våte rutepunkt innen max_km, eller None."""
    import numpy as np
    d = np.hypot((la2 - lat) * 110.57, (lo2 - lon) * 111.32 * math.cos(math.radians(lat)))
    d = np.where(wet, d, np.inf)
    j, i = np.unravel_index(int(np.argmin(d)), d.shape)
    if not math.isfinite(d[j, i]) or d[j, i] > max_km:
        return None, None
    return (int(j), int(i)), float(d[j, i])


def explore_dataset(name, url_path, spots):
    import numpy as np
    from netCDF4 import Dataset, num2date
    url = f"{THREDDS}/dodsC/{url_path}"
    out = {"name": name, "url": url, "ok": False}
    ds = Dataset(url)
    try:
        roles, info = classify_vars(ds)
        out["variables"] = info
        out["roles"] = roles
        attrs = {k: str(ds.getncattr(k)) for k in ds.ncattrs() if k.lower() in ("title", "institution", "source", "history", "comment", "summary", "references", "creator_name")}
        out["global_attrs"] = attrs
        tvar = ds.variables.get("time")
        times = num2date(tvar[:], tvar.units) if tvar is not None else []
        out["time_start"] = str(times[0]) if len(times) else None
        out["time_end"] = str(times[-1]) if len(times) else None
        out["time_steps"] = int(len(times))
        hs_name = roles.get("total_hs")
        if not hs_name:
            out["note"] = "fant ingen total-høyde-variabel"
            return out
        la2, lo2 = grid(ds)
        hs0 = ds.variables[hs_name][0]
        hs0 = hs0[0] if hs0.ndim == 3 else hs0  # evt. (time, 1, y, x)
        wet = ~np.ma.getmaskarray(hs0)
        out["grid"] = {"shape": list(la2.shape), "lat_range": [float(la2.min()), float(la2.max())],
                       "lon_range": [float(lo2.min()), float(lo2.max())], "wet_points": int(wet.sum())}
        out["spots"] = {}
        n = min(HOURS, len(times))
        for s in spots:
            lat, lon = s["spot"]["lat"], s["spot"]["lon"]
            plat, plon = pt(lat, lon, s["facing"], POINT_OUT_KM)
            idx, d = nearest_wet(la2, lo2, wet, plat, plon, MAX_DIST_KM)
            if idx is None:
                continue
            j, i = idx
            series = []
            cols = {}
            for role, vname in roles.items():
                v = ds.variables[vname]
                arr = v[:n, j, i] if v.ndim == 3 else v[:n, 0, j, i]
                cols[role] = [None if np.ma.is_masked(x) else round(float(x), 2) for x in np.ma.asarray(arr)]
            for k in range(n):
                row = {"t": times[k].isoformat() if hasattr(times[k], "isoformat") else str(times[k])}
                for role, vals in cols.items():
                    row[role] = vals[k]
                series.append(row)
            out["spots"][s["id"]] = {
                "point": {"lat": float(la2[j, i]), "lon": float(lo2[j, i])},
                "asked": {"lat": plat, "lon": plon},
                "distance_km": round(d, 2),
                "distance_from_spot_km": round(dist_km(lat, lon, float(la2[j, i]), float(lo2[j, i])), 2),
                "series": series,
            }
        out["ok"] = True
    finally:
        ds.close()
    return out


def forecast_lookup():
    if not FORECAST.exists():
        return {}
    fc = json.loads(FORECAST.read_text(encoding="utf-8"))
    return {s["id"]: {h["t"]: h for h in s["hours"]} for s in fc["spots"]}


def hour_key(t_iso):
    t = dt.datetime.fromisoformat(t_iso.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:00Z")


def write_report(results, catalog_notes, spots):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# WAM800-utforsking (ROADMAP oppgave J), kjørt {now}", ""]
    lines += ["## Kataloger", ""] + [f"- {n}" for n in catalog_notes] + [""]
    fc = forecast_lookup()
    covered = {}
    for r in results:
        lines.append(f"## Datasett: {r['name']}")
        lines.append(f"- URL: {r['url']}")
        if not r.get("ok"):
            lines.append(f"- FEIL: {r.get('error') or r.get('note')}")
            lines.append("")
            continue
        g = r.get("grid", {})
        lines.append(f"- Tid: {r['time_start']} → {r['time_end']} ({r['time_steps']} steg)")
        lines.append(f"- Rutenett: {g.get('shape')} punkter, lat {g.get('lat_range')}, lon {g.get('lon_range')}, våte punkter {g.get('wet_points')}")
        lines.append(f"- Globale attributter: {json.dumps(r.get('global_attrs', {}), ensure_ascii=False)[:600]}")
        lines.append(f"- Roller (gjenkjent automatisk): {json.dumps(r['roles'], ensure_ascii=False)}")
        lines.append("- Variabler (navn, dims, standard_name/long_name/units):")
        for v in r["variables"]:
            if len(v["dims"]) >= 2:
                lines.append(f"  - `{v['name']}` {v['dims']} {v.get('standard_name','')} / {v.get('long_name','')} / {v.get('units','')}")
        lines.append("")
        for sid, sp in r.get("spots", {}).items():
            if sid in covered:
                lines.append(f"- {sid}: dekkes også her ({sp['distance_km']} km fra ønsket punkt) - allerede rapportert fra {covered[sid]}")
                continue
            covered[sid] = r["name"]
            name = next(s["name"] for s in spots if s["id"] == sid)
            lines.append(f"### {name} - punkt {sp['point']['lat']:.5f}, {sp['point']['lon']:.5f} ({sp['distance_km']} km fra ønsket punkt 1,5 km ut, {sp['distance_from_spot_km']} km fra spoten)")
            lines.append("")
            lines.append("| Tid (UTC) | WAM total Hs/Tp/dir | WAM svell Hs/Tp/dir | WAM vindsjø Hs/Tp/dir | BW ved spoten Hs/dir(fra) | GFS svell ute Hs/Tp/dir |")
            lines.append("|---|---|---|---|---|---|")
            for row in sp["series"][:HOURS]:
                k = hour_key(row["t"])
                f = fc.get(sid, {}).get(k, {})
                def trio(p):
                    return f"{row.get(p+'_hs','–')} / {row.get(p+'_tp','–')} / {row.get(p+'_dir','–')}"
                bw = f"{f.get('bw_height','–')} / {f.get('bw_dir','–')}" if f else "–"
                gfs = f"{f.get('swell_offshore','–')} / {f.get('period','–')} / {f.get('dir_offshore','–')}" if f else "–"
                lines.append(f"| {k} | {trio('total')} | {trio('swell')} | {trio('sea')} | {bw} | {gfs} |")
            lines.append("")
    missing = [s["name"] for s in spots if s["id"] not in covered]
    lines += ["## Spots uten dekning i noe datasett", "", (", ".join(missing) if missing else "ingen - alle dekket"), ""]
    lines += ["## Neste steg (ROADMAP J.4-J.6)", "",
              "Sammenlign kildene mot de faste observasjonene (krever arkivdata for 24.-28.09 og 05.10.2026 - sjekk om thredds har arkiv), "
              "og foreslå bruk (J.5) i STATUS.md. Ingenting kobles inn uten Theodors ja.", ""]
    (OUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (OUT_DIR / "latest.json").write_text(json.dumps({"run": now, "catalogs": catalog_notes, "datasets": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lines[:80]))


def main():
    config = json.loads(SPOTS.read_text(encoding="utf-8"))
    spots = [s for s in config["spots"] if s.get("enabled")]
    catalog_notes, datasets = [], []
    for c in CATALOGS:
        try:
            ds, subs = list_catalog(c)
            catalog_notes.append(f"{c}: {len(ds)} datasett, {len(subs)} underkataloger {[t for t, _ in subs][:12]}")
            datasets += ds
            if ds:
                break
        except Exception as e:
            catalog_notes.append(f"{c}: FEIL {str(e)[:160]}")
    # Begrens til de nyeste filene per navnemønster (katalogene kan ha
    # arkiv - vi vil bare ha de siste kjøringene, maks 8 datasett).
    datasets = sorted(set(datasets), key=lambda x: x[0], reverse=True)[:8]
    results = []
    for name, up in datasets:
        print("Datasett:", name, up)
        try:
            results.append(explore_dataset(name, up, spots))
        except Exception as e:
            traceback.print_exc()
            results.append({"name": name, "url": f"{THREDDS}/dodsC/{up}", "ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"})
    write_report(results, catalog_notes, spots)


if __name__ == "__main__":
    main()
