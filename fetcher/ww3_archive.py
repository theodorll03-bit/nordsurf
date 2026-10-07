"""WW3-arkiv for testlaben (skyøkt 07.10.2026, oppgave 1): henter met.no sin
WAVEWATCH III 4 km (svell/vindsjø hver for seg) for de tidspunktene
testlaben trenger, og lagrer dem kompakt i data/ww3/archive/. Kjøres i
GitHub Actions (.github/workflows/backtest.yml) - thredds.met.no er ikke
nåbar fra skyøkten. Gjenbruker punktsøket i fetcher/ww3_explore.py
(rotert rutenett, nærmeste våte celle), henter BARE enkeltpunkter via
OPeNDAP .ascii, aldri hele filer.

To jobber per kjøring:
1. "Fersk": siste fil i ww3_4km_latest_files, de neste HOURS_AHEAD timene
   for alle spots - arkivet vokser hver uke, så fremtidige observasjoner
   og benchmarks får WW3-tall å sammenligne mot.
2. "Observasjoner": for hvert tidspunkt i backtest.fixed_cases() (og
   loggene, hvis LOGS_REPO finnes) prøves ww3_4km_archive-katalogen for
   den dagen (kjøringene 00/06/12/18Z samme dag, så dagen før). Finnes
   fila, hentes timen. Finnes den ikke (arkivet rekker ikke så langt
   bakover), noteres det - aldri 0.

Filformat (data/ww3/archive/<issued>.json):
  {"issued": "...", "file": "<url>", "spots": {spot_id: {"<t UTC>": {hs,dir,tp,phs0,pdir0,ptp0,phs1,pdir1,ptp1, "point": [lat,lon], "dist_km": ..}}}}
Retningene er allerede "fra" (sea_surface_wave_from_direction, se
ww3_explore.py) - ingen omregning."""
import datetime as dt
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ww3_explore as wx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "ww3" / "archive"
POINTS_CACHE = ROOT / "data" / "ww3" / "points.json"
THREDDS = "https://thredds.met.no/thredds"
LATEST_CATALOG = f"{THREDDS}/catalog/ww3_4km_latest_files/catalog.xml"
ARCHIVE_CATALOGS = [f"{THREDDS}/catalog/ww3_4km_archive/catalog.xml", f"{THREDDS}/catalog/fou-hi/ww3_4km_archive/catalog.xml"]
HOURS_AHEAD = 48
UA = {"User-Agent": f"nordsurf-ww3-archive ({os.environ.get('UA_CONTACT', 'ukjent-kontakt')})"}
NS = "{http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0}"
XLINK = "{http://www.w3.org/1999/xlink}"


def list_catalog(url):
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    files = [(d.get("name"), d.get("urlPath")) for d in root.iter(NS + "dataset") if d.get("urlPath")]
    refs = [(c.get(XLINK + "title"), c.get(XLINK + "href")) for c in root.iter(NS + "catalogRef")]
    return files, refs


FIELD_FILE = re.compile(r"^ww3_(\d{8})T(\d{2})Z\.nc$")


def issue_time(name):
    """Utstedelsestid for en RUTENETT-fil (ww3_<dato>T<time>Z.nc). Andre
    filer i samme katalog (f.eks. ww3_POI_SPC_*.nc, punktspektra) gir
    None - de har ikke hs/dir/tp på rutenettet og ga HTTP 400 i første
    Actions-kjøring 07.10.2026."""
    m = FIELD_FILE.match(name or "")
    if not m:
        return None
    return dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H").replace(tzinfo=dt.timezone.utc)


def find_archive_file(target):
    """URL (dodsC) til en arkivfil som dekker `target` (UTC), eller None.
    Prøver kjøringene samme dag og dagen før, nyeste først - en fil dekker
    normalt ~3 døgn fra utstedelsen."""
    candidates = []
    for cat in ARCHIVE_CATALOGS:
        try:
            files, refs = list_catalog(cat)
        except Exception as e:
            print(f"  katalog {cat}: {e}")
            continue
        # underkataloger per år/måned?
        for title, href in refs:
            sub = href if href.startswith("http") else cat.rsplit("/", 1)[0] + "/" + href
            if target.strftime("%Y") in (title or "") or target.strftime("%Y%m") in (title or "") or "archive" in (title or "").lower():
                try:
                    f2, _ = list_catalog(sub)
                    files += f2
                except Exception:
                    pass
        for name, path in files:
            t0 = issue_time(name)
            if t0 and 0 <= (target - t0).total_seconds() / 3600 < 72:
                candidates.append((t0, path))
        if candidates:
            break
    if not candidates:
        return None
    t0, path = max(candidates, key=lambda x: x[0])
    return f"{THREDDS}/dodsC/{path}", t0


def latest_file():
    files, _ = list_catalog(LATEST_CATALOG)
    dated = [(issue_time(n), p) for n, p in files if issue_time(n)]
    if not dated:
        raise RuntimeError("ingen daterte filer i ww3_4km_latest_files")
    t0, path = max(dated)
    return f"{THREDDS}/dodsC/{path}", t0


def fetch_point_hours(base_url, i, j, idx_from, idx_to):
    """Rader (dict per time) for tidsindeksene idx_from..idx_to (inkl.)."""
    wx.BASE = base_url
    expr = ",".join(f"{v}.{v}[{idx_from}:1:{idx_to}][{i}][{j}]" for v in wx.VARS)
    text = wx.fetch_ascii(expr)
    cols = {}
    for v in wx.VARS:
        rows = wx.parse_grid_block(text, v)
        cols[v] = [r[0] if r and r[0] == r[0] else None for r in rows]
    n = min(len(c) for c in cols.values())
    return [{v: (None if cols[v][k] is None else round(cols[v][k], 2)) for v in wx.VARS} for k in range(n)]


def load_points():
    return json.loads(POINTS_CACHE.read_text(encoding="utf-8")) if POINTS_CACHE.exists() else {}


def ensure_points(spots, base_url):
    """Rutenettindeks per spot (nærmeste våte celle til havpunktet) - søkes én
    gang og mellomlagres i data/ww3/points.json (rutenettet er fast)."""
    pts = load_points()
    wx.BASE = base_url
    for s in spots:
        if s["id"] in pts:
            continue
        o = s["offshore"]
        found = wx.find_point(o["lat"], o["lon"])
        if found:
            i, j, la, lo, dist = found
            pts[s["id"]] = {"i": i, "j": j, "lat": la, "lon": lo, "dist_km": round(dist, 1)}
            print(f"  {s['name']}: punkt ({la:.4f},{lo:.4f}) indeks ({i},{j}), {dist:.1f} km fra havpunktet")
        else:
            print(f"  {s['name']}: ingen våt celle funnet")
        time.sleep(1.0)
    POINTS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    POINTS_CACHE.write_text(json.dumps(pts, ensure_ascii=False, indent=1), encoding="utf-8")
    return pts


def hour_key(t):
    return t.strftime("%Y-%m-%dT%H:00Z")


def write_archive(issued, file_url, spots_data):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{issued:%Y-%m-%dT%H}.json"
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"issued": issued.isoformat(), "file": file_url, "spots": {}}
    for sid, hours in spots_data.items():
        existing["spots"].setdefault(sid, {}).update(hours)
    path.write_text(json.dumps(existing, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path


def main():
    spots = [s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"] if s.get("enabled")]
    # 1. fersk
    try:
        url, t0 = latest_file()
        print("Siste fil:", url, t0)
        pts = ensure_points(spots, url)
        data = {}
        for s in spots:
            p = pts.get(s["id"])
            if not p:
                continue
            rows = fetch_point_hours(url, p["i"], p["j"], 0, HOURS_AHEAD - 1)
            data[s["id"]] = {hour_key(t0 + dt.timedelta(hours=k)): {**rows[k], "point": [p["lat"], p["lon"]], "dist_km": p["dist_km"]} for k in range(len(rows))}
            print(f"  {s['name']}: {len(rows)} timer")
            time.sleep(1.0)
        print("Skrev", write_archive(t0, url, data))
    except Exception as e:
        print("Fersk henting feilet:", e)
        pts = load_points()
    # 2. observasjonstidspunkter
    import backtest
    targets = {}
    for c in backtest.fixed_cases():
        targets.setdefault(c["spot"], set()).add(c["t"])
    if os.environ.get("LOGS_REPO") and os.environ.get("LOGS_TOKEN"):
        try:
            import sources
            for c in backtest.log_cases(sources.github_logs()):
                targets.setdefault(c["spot"], set()).add(c["t"])
        except Exception as e:
            print("Logger kunne ikke hentes:", e)
    have = backtest.load_ww3_archive()
    missing = {sid: sorted(t for t in ts if t not in have.get(sid, {})) for sid, ts in targets.items()}
    by_file = {}
    for sid, ts in missing.items():
        p = pts.get(sid)
        if not p:
            continue
        for t in ts:
            target = dt.datetime.strptime(t, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
            found = find_archive_file(target)
            if not found:
                print(f"  {sid} {t}: ingen arkivfil dekker tidspunktet")
                continue
            url, t0 = found
            by_file.setdefault((url, t0), []).append((sid, target))
    for (url, t0), items in by_file.items():
        data = {}
        for sid, target in items:
            p = pts[sid]
            k = int((target - t0).total_seconds() // 3600)
            try:
                rows = fetch_point_hours(url, p["i"], p["j"], k, k)
            except Exception as e:
                print(f"  {sid} {target}: {e}")
                continue
            if rows:
                data.setdefault(sid, {})[hour_key(target)] = {**rows[0], "point": [p["lat"], p["lon"]], "dist_km": p["dist_km"]}
                print(f"  {sid} {hour_key(target)}: svell {rows[0]['phs1']} m/{rows[0]['ptp1']} s fra {rows[0]['pdir1']}°, vindsjø {rows[0]['phs0']} m")
            time.sleep(1.0)
        if data:
            print("Skrev", write_archive(t0, url, data))


if __name__ == "__main__":
    main()
