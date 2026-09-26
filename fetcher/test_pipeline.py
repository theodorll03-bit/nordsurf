"""Kjører hele henteren med falske kilder, uten nett. Kjør: python fetcher/test_pipeline.py"""
import json, math, datetime as dt, tempfile
from pathlib import Path
import requests
import sources, fetch, notify, calibrate
from rating import DEFAULT_TRANSFER

real_openmeteo_marine = sources.openmeteo_marine  # før noe under mokker den ut

# Loggen skal læres mot toppfaktoren ved direkte treff: forhold = størrelse / (svellOffshore * directness).
# Gamle logger uten feltet antas direkte (directness 1.0) - se lengre ned, uendret 0.42-sjekk.
# Her: fem logger med directness 0.5 skal gi dobbelt så høyt forhold som samme logger uten directness ville gjort.
direct_ratio = round(0.5 / (1.2 * 0.5), 2)
half_directness_logs = [
    {"spot": "x", "size": "Knehøy", "swellOffshore": 1.2, "directness": 0.5} for _ in range(5)
]
half_result = calibrate.learn("x", half_directness_logs)
print("Læring med directness 0,5:", half_result, "| forventet forhold:", direct_ratio)
assert half_result["transfer"] == direct_ratio == 0.83

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
fetch.BW_CALIB = tmp / "bw_calibration.json"
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

# ---------- 6a-c: BarentsWatch-interpolasjon ----------
base = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
raw = {
    sources.hour_key(base): {"height": 0.6, "dir": 300.0, "period": 10.0},
    sources.hour_key(base + dt.timedelta(hours=3)): {"height": 0.9, "dir": 310.0, "period": 11.0},
    sources.hour_key(base + dt.timedelta(hours=6)): {"height": 0.3, "dir": 290.0, "period": 9.0},
}
interp = sources.bw_interpolate(raw)
print("6a interpolerte høyder t+1..t+5:", [round(interp[sources.hour_key(base + dt.timedelta(hours=i))]["height"], 3) for i in range(1, 6)])
assert interp[sources.hour_key(base)]["interpolated"] is False
assert interp[sources.hour_key(base + dt.timedelta(hours=1))]["height"] == 0.7
assert interp[sources.hour_key(base + dt.timedelta(hours=2))]["height"] == 0.8
assert interp[sources.hour_key(base + dt.timedelta(hours=4))]["height"] == 0.7
assert interp[sources.hour_key(base + dt.timedelta(hours=5))]["height"] == 0.5
assert interp[sources.hour_key(base + dt.timedelta(hours=1))]["interpolated"] is True
assert round(interp[sources.hour_key(base + dt.timedelta(hours=1))]["dir"], 2) == 303.33

raw_gap = {
    sources.hour_key(base): {"height": 0.6, "dir": 300.0, "period": 10.0},
    sources.hour_key(base + dt.timedelta(hours=9)): {"height": 0.3, "dir": 290.0, "period": 9.0},
}
interp_gap = sources.bw_interpolate(raw_gap)
print("6b hull over 3 timer: ingen fylte timer mellom punktene:", len(interp_gap) == 2)
assert len(interp_gap) == 2  # ni timer mellom - ikke fyll, ikke ekstrapoler

assert sources.hour_key(base - dt.timedelta(hours=1)) not in interp  # 6c: aldri før første punkt
assert sources.hour_key(base + dt.timedelta(hours=7)) not in interp  # 6c: aldri etter siste punkt

# ---------- 6d: BarentsWatch som hovedkilde og bytte ved bw_until ----------
def bw_hourly_mock(la, lo):
    now2 = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    return {sources.hour_key(now2 + dt.timedelta(hours=i)): {"height": 0.5, "dir": 300.0, "period": 10.0} for i in (0, 3, 6, 9)}

sources.barentswatch_point = bw_hourly_mock
tmp2 = Path(tempfile.mkdtemp())
fetch.OUT = tmp2 / "forecast.json"
fetch.BW_CALIB = tmp2 / "bw_calibration.json"
notify.STATE = tmp2 / "notified.json"
sent2 = []
notify.requests.post = lambda url, json=None, timeout=None: sent2.append(json) or type("R", (), {"raise_for_status": lambda s: None})()
fetch.main()
f2 = json.loads(fetch.OUT.read_text())
g2 = next(s for s in f2["spots"] if s["id"] == "grotfjord")
before = [h for h in g2["hours"] if h["t"] <= g2["bw_until"]]
after = [h for h in g2["hours"] if h["t"] > g2["bw_until"]]
print("6d bw_until:", g2["bw_until"], "| timer før/etter:", len(before), len(after))
assert before and all(h["height_source"] == "barentswatch" for h in before)
assert after and all(h["height_source"] != "barentswatch" for h in after)

# ---------- 6e: filtre for kalibreringspar ----------
h_ok = {"t": "2026-02-01T00:00Z", "height_source": "barentswatch", "bw_interpolated": False,
        "bw_height": 0.7, "swell_offshore": 1.0, "directness": 1.0, "height_offshore": 1.0}
h_low_swell = {**h_ok, "t": "2026-02-01T01:00Z", "swell_offshore": 0.2}
h_low_dir = {**h_ok, "t": "2026-02-01T02:00Z", "directness": 0.2}
h_windsea = {**h_ok, "t": "2026-02-01T03:00Z", "swell_offshore": 0.5, "height_offshore": 2.0}
h_interp = {**h_ok, "t": "2026-02-01T04:00Z", "bw_interpolated": True}
h_reserve = {**h_ok, "t": "2026-02-01T05:00Z", "height_source": "svell_ute"}
pairs_6e = calibrate.bw_pairs_for_run([h_ok, h_low_swell, h_low_dir, h_windsea, h_interp, h_reserve], "run1")
print("6e kalibreringspar (skal være 1):", pairs_6e)
assert len(pairs_6e) == 1 and pairs_6e[0]["t"] == h_ok["t"] and pairs_6e[0]["ratio"] == 0.7

# ---------- 6f: bw_transfer krever nok par OG nok døgn ----------
def make_pairs(n_per_day, days, ratio):
    return [{"t": f"2026-03-{d + 1:02d}T{i:02d}:00Z", "ratio": ratio} for d in range(days) for i in range(n_per_day)]

few = make_pairs(15, 2, 0.5)  # 30 par, 2 døgn - under begge grensene
enough = make_pairs(15, 4, 0.55)  # 60 par, 4 døgn - over begge
one_day_only = make_pairs(42, 1, 0.9)  # 42 par, men bare 1 døgn
print("6f bw_transfer (få/nok/ett døgn):", calibrate.bw_transfer(few), calibrate.bw_transfer(enough), calibrate.bw_transfer(one_day_only))
assert calibrate.bw_transfer(few) is None
assert calibrate.bw_transfer(enough) == 0.55
assert calibrate.bw_transfer(one_day_only) is None

# ---------- 6g: rekkefølge logs -> BarentsWatch -> spots.json -> DEFAULT_TRANSFER ----------
spot_with_transfer, spot_no_transfer = {"transfer": 0.33}, {}
learned_with, learned_none = {"transfer": 0.77}, {}
r1 = calibrate.effective_transfer(spot_with_transfer, learned_with, enough)
r2 = calibrate.effective_transfer(spot_with_transfer, learned_none, enough)
r3 = calibrate.effective_transfer(spot_with_transfer, learned_none, few)
r4 = calibrate.effective_transfer(spot_no_transfer, learned_none, few)
print("6g rekkefølge:", r1, r2, r3, r4)
assert r1 == (0.77, "logs")
assert r2 == (0.55, "barentswatch")
assert r3 == (0.33, "spots.json")
assert r4 == (DEFAULT_TRANSFER, "standard")

# ---------- 6h: varsel skal bare bruke ekte BarentsWatch-timer ----------
now3 = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
def th(i): return sources.hour_key(now3 + dt.timedelta(hours=i))
hours_6h = (
    [{"t": th(i), "stars": 5, "daylight": True, "height_source": "barentswatch",
      "height": 1.0, "period": 10, "wind_type": "offshore"} for i in range(10)]
    + [{"t": th(i), "stars": 5, "daylight": True, "height_source": "svell_ute",
        "height": 1.0, "period": 10, "wind_type": "offshore"} for i in range(10, 20)]
)
spot_bw = {"id": "testspot", "name": "Testspot", "hours": hours_6h, "bw_until": th(9)}
ws_bw = notify.windows(spot_bw, min_stars=3, hours_ahead=100, now=now3)
covered = sum(len(w["hours"]) for w in ws_bw)
print("6h timer dekket med bw_until satt (skal være 10, bare BarentsWatch-delen):", covered)
assert covered == 10

spot_no_bw = {**spot_bw, "bw_until": None}
ws_no_bw = notify.windows(spot_no_bw, min_stars=3, hours_ahead=100, now=now3)
covered_no_bw = sum(len(w["hours"]) for w in ws_no_bw)
print("6h timer dekket uten bw_until (skal være 20, alle timer):", covered_no_bw)
assert covered_no_bw == 20

# ---------- 6i: 250 m-punktet brukes i ratingen, 150 m bare til sammenligning
# (bw_height_near) - og 250 m uten data faller tilbake til 150 m for RATINGEN ----------
spots_cfg = json.loads((Path(__file__).parent.parent / "spots.json").read_text())
grot_spot = next(s for s in spots_cfg["spots"] if s["id"] == "grotfjord")
lat250, lat150 = grot_spot["barentswatch_point"]["lat"], grot_spot["barentswatch_point_near"]["lat"]

def bw_two_points_mock(la, lo):
    now4 = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    if abs(la - lat250) < abs(la - lat150):  # nærmest 250 m-punktet
        return {sources.hour_key(now4): {"height": 1.5, "dir": 300.0, "period": 10.0, "max_height": 2.1}}
    return {sources.hour_key(now4): {"height": 1.1, "dir": 300.0, "period": 10.0, "max_height": 1.7}}

sources.barentswatch_point = bw_two_points_mock
tmp6i = Path(tempfile.mkdtemp())
fetch.OUT = tmp6i / "forecast.json"
fetch.BW_CALIB = tmp6i / "bw_calibration.json"
notify.STATE = tmp6i / "notified.json"
fetch.main()
f6i = json.loads(fetch.OUT.read_text())
g6i = next(s for s in f6i["spots"] if s["id"] == "grotfjord")
h6i = g6i["hours"][0]
print("6i bw_height (250m)/bw_height_near (150m)/bw_height_max:", h6i["bw_height"], h6i["bw_height_near"], h6i["bw_height_max"])
assert h6i["bw_height"] == 1.5 and h6i["bw_height_near"] == 1.1 and h6i["bw_height_max"] == 2.1
assert h6i["height"] == 1.5  # ratingen bruker 250 m-punktet

# 250 m-punktet gir ingen data -> ratingen skal falle tilbake til 150 m.
def bw_250_empty_mock(la, lo):
    now4 = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    if abs(la - lat250) < abs(la - lat150):
        return {}
    return {sources.hour_key(now4): {"height": 1.1, "dir": 300.0, "period": 10.0, "max_height": 1.7}}

sources.barentswatch_point = bw_250_empty_mock
tmp6i2 = Path(tempfile.mkdtemp())
fetch.OUT = tmp6i2 / "forecast.json"
fetch.BW_CALIB = tmp6i2 / "bw_calibration.json"
notify.STATE = tmp6i2 / "notified.json"
fetch.main()
f6i2 = json.loads(fetch.OUT.read_text())
g6i2 = next(s for s in f6i2["spots"] if s["id"] == "grotfjord")
h6i2 = g6i2["hours"][0]
print("6i 250m tom -> bw_height (falt tilbake)/bw_height_near:", h6i2["bw_height"], h6i2["bw_height_near"])
assert h6i2["bw_height"] == 1.1 and h6i2["bw_height_near"] == 1.1  # begge er 150 m-punktet nå

# ---------- 7a: svellretning skal ALDRI komme fra met.no sin samlede sjøtilstand ----------
sources.metno_ocean = lambda la, lo: hourly(lambda i: {"height": 1.8, "dir": 325, "water_temp": 8})
sources.openmeteo_marine = lambda la, lo: hourly(lambda i: {"height": 2.0, "swell_height": 1.6, "dir": 266, "period": 13, "swell_model": "gfs"})
tmp3 = Path(tempfile.mkdtemp())
fetch.OUT = tmp3 / "forecast.json"
fetch.BW_CALIB = tmp3 / "bw_calibration.json"
notify.STATE = tmp3 / "notified.json"
fetch.main()
f3 = json.loads(fetch.OUT.read_text())
g3 = next(s for s in f3["spots"] if s["id"] == "grotfjord")
dir0 = g3["hours"][0]["dir_offshore"]
print("7a svellretning met.no=325 vs Open-Meteo hovedsvell=266 -> dir_offshore:", dir0)
assert dir0 == 266

# ---------- 7b: openmeteo_marine faller tilbake til standardmodellen når GFS mangler svelldata for en time ----------
def fake_openmeteo_fetch(lat, lon, model=None):
    if model == sources.OPENMETEO_SWELL_MODEL:
        return {
            "2026-01-01T00:00Z": {"height": 1.5, "swell_height": 1.0, "swell_dir": 260, "swell_period": 11,
                                   "secondary_swell_height": None, "secondary_swell_dir": None, "secondary_swell_period": None},
            "2026-01-01T01:00Z": {"height": 1.4, "swell_height": None, "swell_dir": None, "swell_period": None,
                                   "secondary_swell_height": None, "secondary_swell_dir": None, "secondary_swell_period": None},
        }
    return {  # standardmodellen (reserve) - har data begge timer, også der GFS mangler
        "2026-01-01T00:00Z": {"height": 1.5, "swell_height": 0.9, "swell_dir": 250, "swell_period": 9,
                               "secondary_swell_height": None, "secondary_swell_dir": None, "secondary_swell_period": None},
        "2026-01-01T01:00Z": {"height": 1.4, "swell_height": 0.8, "swell_dir": 240, "swell_period": 8,
                               "secondary_swell_height": None, "secondary_swell_dir": None, "secondary_swell_period": None},
    }
real_openmeteo_fetch = sources._openmeteo_fetch
sources._openmeteo_fetch = fake_openmeteo_fetch
result = real_openmeteo_marine(69.5, 17.0)
sources._openmeteo_fetch = real_openmeteo_fetch
print("7b GFS har data kl 00, mangler kl 01:", result["2026-01-01T00:00Z"]["dir"], result["2026-01-01T00:00Z"]["swell_model"],
      "|", result["2026-01-01T01:00Z"]["dir"], result["2026-01-01T01:00Z"]["swell_model"])
assert result["2026-01-01T00:00Z"]["dir"] == 260 and result["2026-01-01T00:00Z"]["swell_model"] == "gfs"
assert result["2026-01-01T01:00Z"]["dir"] == 240 and result["2026-01-01T01:00Z"]["swell_model"] == "standard"

# ---------- 7c: GFS svarer med bokstavelig 0.0/0 (ikke null) der ruta ikke har
# gyldig sjødekning (sett i Lyngen) - skal falle tilbake til standardmodellen,
# ikke bli tolket som ekte (og retningsløs) flau sjø ----------
def fake_openmeteo_fetch_zero(lat, lon, model=None):
    if model == sources.OPENMETEO_SWELL_MODEL:
        return {"2026-01-01T00:00Z": {"height": 0.0, "swell_height": 0.0, "swell_dir": 0, "swell_period": 0.0,
                                       "secondary_swell_height": 0.0, "secondary_swell_dir": 0, "secondary_swell_period": 0.0}}
    return {"2026-01-01T00:00Z": {"height": 0.88, "swell_height": 0.56, "swell_dir": 271, "swell_period": 17.3,
                                   "secondary_swell_height": 0.48, "secondary_swell_dir": 327, "secondary_swell_period": 6.55}}
sources._openmeteo_fetch = fake_openmeteo_fetch_zero
result = real_openmeteo_marine(70.35, 20.45)
sources._openmeteo_fetch = real_openmeteo_fetch
print("7c GFS svarer med 0.0 pa alt (ingen dekning) -> faller til standardmodellen:", result["2026-01-01T00:00Z"])
assert result["2026-01-01T00:00Z"]["dir"] == 271 and result["2026-01-01T00:00Z"]["swell_model"] == "standard"
assert result["2026-01-01T00:00Z"]["height"] == 0.88

# ---------- 7d: _get prøver igjen på midlertidige HTTP-feil (429/5xx), men
# ikke på varige (sett i Actions: kildene svarer av og til med 503 når flere
# spots hentes tett etter hverandre) ----------
class FakeResp:
    def __init__(self, status):
        self.status_code = status
    def raise_for_status(self):
        if self.status_code >= 400:
            e = requests.HTTPError(f"{self.status_code}")
            e.response = self
            raise e
    def json(self):
        return {"ok": True}

calls = {"n": 0}
def flaky_get(url, params=None, headers=None, timeout=None):
    calls["n"] += 1
    return FakeResp(503) if calls["n"] < 3 else FakeResp(200)
real_requests_get, real_sleep = requests.get, sources.time.sleep
requests.get, sources.time.sleep = flaky_get, lambda s: None
r = sources._get("https://example.test")
requests.get = real_requests_get
print("7d _get prøver igjen på 503, lykkes på forsøk", calls["n"])
assert calls["n"] == 3 and r.json() == {"ok": True}

calls["n"] = 0
def always_404(url, params=None, headers=None, timeout=None):
    calls["n"] += 1
    return FakeResp(404)
requests.get = always_404
try:
    sources._get("https://example.test")
    raised = False
except requests.HTTPError:
    raised = True
requests.get, sources.time.sleep = real_requests_get, real_sleep
print("7d _get gir opp med en gang på 404, antall forsøk:", calls["n"])
assert raised and calls["n"] == 1

# ---------- 7e: openmeteo_marine mister ikke standardmodellen selv om GFS-
# kallet timer ut (sett i live kjøring 26.09.2026 - Open-Meteo brukte over
# 45s på GFS-kallet for to spots samtidig, og hele funksjonen kastet før den
# rakk å prøve standardmodellen, som ellers hadde gitt data) ----------
def flaky_openmeteo_fetch(lat, lon, model=None):
    if model == sources.OPENMETEO_SWELL_MODEL:
        raise requests.Timeout("Read timed out (read timeout=45)")
    return {"2026-01-01T00:00Z": {"height": 0.88, "swell_height": 0.56, "swell_dir": 271, "swell_period": 17.3,
                                   "secondary_swell_height": 0.48, "secondary_swell_dir": 327, "secondary_swell_period": 6.55}}
sources._openmeteo_fetch = flaky_openmeteo_fetch
result = real_openmeteo_marine(70.35, 20.45)
sources._openmeteo_fetch = real_openmeteo_fetch
print("7e GFS-kallet timer ut -> faller likevel til standardmodellen:", result["2026-01-01T00:00Z"])
assert result["2026-01-01T00:00Z"]["dir"] == 271 and result["2026-01-01T00:00Z"]["swell_model"] == "standard"

# begge feiler -> skal fortsatt kaste, slik at safe() rapporterer det som feil
def always_fails(lat, lon, model=None):
    raise requests.Timeout("Read timed out (read timeout=45)")
sources._openmeteo_fetch = always_fails
try:
    real_openmeteo_marine(70.35, 20.45)
    raised = False
except RuntimeError:
    raised = True
sources._openmeteo_fetch = real_openmeteo_fetch
print("7e begge modellene feiler -> kaster fortsatt:", raised)
assert raised

print("Pipeline ok")
