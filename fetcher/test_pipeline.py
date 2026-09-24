"""Kjører hele henteren med falske kilder, uten nett. Kjør: python fetcher/test_pipeline.py"""
import json, math, datetime as dt, tempfile
from pathlib import Path
import sources, fetch, notify

def hourly(fn):
    now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    return {sources.hour_key(now + dt.timedelta(hours=i)): fn(i) for i in range(80)}

sources.metno_ocean = lambda la, lo: hourly(lambda i: {"height": 1.8, "dir": 300 + (4 if la < 69.8 else 0), "water_temp": 8})
sources.openmeteo_marine = lambda la, lo: hourly(lambda i: {"height": 2.0, "swell_height": 1.6, "dir": 300, "period": 13})
sources.metno_weather = lambda la, lo: hourly(lambda i: {"wind_speed": 2, "wind_dir": 120, "gust": 4, "air_temp": 6})
now = dt.datetime.now(dt.timezone.utc)
sources.kartverket_tide = lambda la, lo, a, b: [
    {"time": (now + dt.timedelta(minutes=372 * k - 300)).isoformat(), "type": "flo" if k % 2 else "fjære", "cm": 240 if k % 2 else 60} for k in range(16)]
sources.github_logs = lambda: [
    {"id": str(i), "spot": "grotfjord", "stars": 1, "size": "Knehøy", "swellOffshore": 1.2, "forecastStars": 2} for i in range(6)]

tmp = Path(tempfile.mkdtemp())
fetch.OUT = tmp / "forecast.json"
notify.STATE = tmp / "notified.json"
sent = []
notify.requests.post = lambda url, json=None, timeout=None: sent.append(json) or type("R", (), {"raise_for_status": lambda s: None})()
import os; os.environ["NTFY_TOPIC"] = "test-topic"
fetch.main()
f = json.loads(fetch.OUT.read_text())
g = next(s for s in f["spots"] if s["id"] == "grotfjord")
print("Grøtfjord lært faktor:", g["calibration"], "| første time:", {k: g["hours"][0][k] for k in ("stars", "height", "height_source", "light", "tide")})
assert g["calibration"]["transfer"] == 0.42 and g["hours"][0]["transfer"] == 0.42
assert all("light" in h for h in g["hours"])
print("Varsler sendt:", [m["title"] for m in sent])
fetch.main()  # andre kjøring skal ikke sende samme varsel igjen
print("Etter andre kjøring:", len(sent), "varsler totalt")
assert len(sent) == len({m["title"] for m in sent})
print("Pipeline ok")
