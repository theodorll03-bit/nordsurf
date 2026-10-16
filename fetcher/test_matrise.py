"""S6 (ROADMAP seksjon S): henteren som matrise per region skal gi BYTE FOR BYTE samme resultat som den
sekvensielle kjøringen - forecast.json, kalibreringen (bw_calibration.json), eksponeringen (exposure.json),
treffsikkerheten (forecast_accuracy.json), arkivet og varselstatusen (notified.json). Kjører begge veiene med
de samme falske kildene som test_pipeline.py (uten nett), med læringsdataene fra data/ som utgangspunkt.

Kjør: python fetcher/test_matrise.py   (ingen nett, under 30 s)"""
import datetime as dt
import json
import os
import shutil
import tempfile
from pathlib import Path

os.environ["NORDSURF_WW3"] = "0"
import sources, fetch, notify, calibrate  # noqa: E401,E402
fetch.WW3_ENABLED = False

ROOT = Path(__file__).resolve().parent.parent
NOW = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
os.environ["NORDSURF_NOW"] = NOW.isoformat()


def hourly(fn):
    return {sources.hour_key(NOW + dt.timedelta(hours=i)): fn(i) for i in range(80)}


# samme falske kilder som test_pipeline.py (med fast tid, så begge veiene ser samme timer)
sources.metno_ocean = lambda la, lo: hourly(lambda i: {"height": 1.8 + 0.01 * (i % 7), "dir": 300 + (4 if la < 69.8 else 0), "water_temp": 8})
sources.openmeteo_marine = lambda la, lo, apply_ratio_correction=True: hourly(lambda i: {"height": 2.0, "swell_height": 1.6, "dir": 300 + (i % 5), "period": 13})
sources.metno_weather = lambda la, lo: hourly(lambda i: {"wind_speed": 2 + (i % 4), "wind_dir": 120, "gust": 4, "air_temp": 6})
sources.kartverket_tide = lambda la, lo, a, b: [
    {"time": (NOW + dt.timedelta(minutes=372 * k - 300)).isoformat(), "type": "flo" if k % 2 else "fjære", "cm": 240 if k % 2 else 60} for k in range(16)]
sources.github_logs = lambda: [
    {"id": str(i), "spot": "grotfjord", "stars": 1, "size": "Hoftehøy", "forecastHeight": 1.0,
     "forecastPeriod": 12, "directness": 1.0, "forecastStars": 2} for i in range(6)]
sources.openmeteo_wind = lambda la, lo: {}
sources.barentswatch_point = lambda la, lo: hourly(lambda i: {"height": 0.9, "dir": 300.0, "period": 11.0}) if i_bw_ok(la) else {}
def i_bw_ok(la):   # noqa: E302 - noen punkter uten data, så reserven (150 m) og «mangler» også prøves
    return round(la * 1000) % 3 != 0


def prefetch_stub(marine_points, wind_points, **k):
    # samlekallet: fyller mellomlageret slik det ekte gjør (her med de falske svarene), så matrisen må ta det med seg
    for la, lo in marine_points:
        for model in ("gfs", "standard"):
            sources._OM_CACHE[sources._om_key("marine", la, lo, model)] = {"t": [la, lo, model]}
    return {"points": len(marine_points), "jobs": 2 * len(marine_points), "calls": 2, "failed": 0, "cached": 0}


sources.openmeteo_prefetch = prefetch_stub
notify.requests.post = lambda url, json=None, timeout=None: type("R", (), {"raise_for_status": lambda s: None})()
os.environ["NTFY_TOPIC"] = "test-topic"
for k in ("BW_CLIENT_ID", "BW_CLIENT_SECRET", "LOGS_REPO", "LOGS_TOKEN", "GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY"):
    os.environ.pop(k, None)

SEED = {"bw_calibration.json": ROOT / "data" / "bw_calibration.json", "exposure.json": ROOT / "data" / "exposure.json",
        "forecast_accuracy.json": ROOT / "data" / "forecast_accuracy.json"}


def fresh(tmp):
    """Ny prosess: tomme modul-lister og mellomlagre, og læringsdataene som de står i git."""
    for lst in (fetch.REPORT, fetch.EXPOSURE_REPORT, fetch.CONVENTION_WARNINGS, fetch.LOW_ADJUSTMENT_WARNINGS, fetch.BW_LEE_WARNINGS):
        lst.clear()
    sources.openmeteo_clear_cache()
    fetch.OUT = tmp / "docs" / "forecast.json"
    fetch.BW_CALIB = tmp / "bw_calibration.json"
    fetch.EXPOSURE_LEARNED = tmp / "exposure.json"
    fetch.LEDGER = tmp / "forecast_accuracy.json"
    fetch.ARCHIVE_DIR = tmp / "forecast_archive"
    notify.STATE = tmp / "notified.json"


def seed(tmp):
    tmp.mkdir(parents=True, exist_ok=True)
    for name, src in SEED.items():
        if src.exists():
            shutil.copy(src, tmp / name)


def snapshot(tmp):
    return {str(p.relative_to(tmp)): p.read_bytes() for p in sorted(tmp.rglob("*")) if p.is_file()}


base = Path(tempfile.mkdtemp())
seq, mat = base / "sekvensiell", base / "matrise"
seed(seq)
seed(mat)

# 1. sekvensiell (som før S6, og reserven i forecast.yml)
fresh(seq)
fetch.main()
A = snapshot(seq)

# 2. matrise: forjobb → én jobb per region (hver som en ny prosess) → samlejobb
work = base / "artifacts"
fresh(mat)
fetch.forjobb(work / "forjobb")
meta = json.loads((work / "forjobb" / "meta.json").read_text(encoding="utf-8"))
regions = meta["regions"]
assert len(regions) >= 2, f"testen trenger minst to regioner (spots.json): {regions}"
for r in regions:
    fresh(mat)
    fetch.region_job(r, work / "forjobb", work / "regioner")
fresh(mat)
fetch.samle(work / "regioner", work / "forjobb")
B = snapshot(mat)

assert set(A) == set(B), f"ulike filer: bare sekvensiell {sorted(set(A) - set(B))}, bare matrise {sorted(set(B) - set(A))}"
diff = [k for k in A if A[k] != B[k]]
assert not diff, f"matrisen gir andre bytes enn den sekvensielle kjøringen i: {diff}"
fc = json.loads(A["docs/forecast.json"])
n_hours = sum(len(s["hours"]) for s in fc["spots"])
print(f"1: matrise ({len(regions)} regioner: {', '.join(regions)}) = sekvensiell byte for byte i {len(A)} filer "
      f"({len(fc['spots'])} spots, {n_hours} timer) - OK")

# 3. en region som feiler: de andre leveres, spotene i den mangler (aldri 0), og kilderapporten sier fra
fresh(mat)
for p in (work / "regioner").glob("*.json"):
    p.unlink()
for r in regions[1:]:
    fresh(mat)
    fetch.region_job(r, work / "forjobb", work / "regioner")
fresh(mat)
fetch.samle(work / "regioner", work / "forjobb")
fc2 = json.loads((mat / "docs" / "forecast.json").read_text(encoding="utf-8"))
mangler = {s["id"] for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"] if s.get("enabled") and fetch.region_of(s) == regions[0]}
assert mangler and not mangler & {s["id"] for s in fc2["spots"]}, "spotene i regionen som feilet skal mangle, ikke stå med 0"
assert any(r[1] == f"Region {regions[0]}" and r[2] == "feil" for r in fetch.REPORT), "kilderapporten skal si at regionen feilet"
print(f"2: regionen «{regions[0]}» feiler - {len(fc2['spots'])} spots leveres, {len(mangler)} mangler (ikke 0), kilderapporten sier fra - OK")

# 4. regionlista følger spots.json sin «regions» (nord til sør), og alle aktive spots har en region
cfg = json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))
want = [r["name"] for r in sorted(cfg["regions"], key=lambda r: r.get("order", 999))]
assert regions == [r for r in want if r in regions], (regions, want)
assert all(s.get("region") for s in cfg["spots"] if s.get("enabled")), "en aktiv spot mangler region - havner i «Uten region»"
print(f"3: regionene i spots.json-rekkefølge {regions}, alle aktive spots har region - OK")
shutil.rmtree(base, ignore_errors=True)
print("Alle tester ok")
