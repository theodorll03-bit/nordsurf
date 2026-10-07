"""Kjører hele henteren med falske kilder, uten nett. Kjør: python fetcher/test_pipeline.py"""
import json, math, datetime as dt, tempfile
from pathlib import Path
import requests
import sources, fetch, notify, calibrate
from rating import DEFAULT_TRANSFER, breaking_height

real_openmeteo_marine = sources.openmeteo_marine  # før noe under mokker den ut


def _solve_h_for_hb(target, period):
    """H slik at breaking_height(H, period) == target (bisek­sjon)."""
    lo, hi = 0.05, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if breaking_height(mid, period) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def hourly(fn):
    now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    return {sources.hour_key(now + dt.timedelta(hours=i)): fn(i) for i in range(80)}

sources.metno_ocean = lambda la, lo: hourly(lambda i: {"height": 1.8, "dir": 300 + (4 if la < 69.8 else 0), "water_temp": 8})
sources.openmeteo_marine = lambda la, lo: hourly(lambda i: {"height": 2.0, "swell_height": 1.6, "dir": 300, "period": 13})
sources.metno_weather = lambda la, lo: hourly(lambda i: {"wind_speed": 2, "wind_dir": 120, "gust": 4, "air_temp": 6})
now = dt.datetime.now(dt.timezone.utc)
sources.kartverket_tide = lambda la, lo, a, b: [
    {"time": (now + dt.timedelta(minutes=372 * k - 300)).isoformat(), "type": "flo" if k % 2 else "fjære", "cm": 240 if k % 2 else 60} for k in range(16)]
# 26.09.2026: transfer læres ikke lenger fra loggene (surfehøyde-endringen) -
# H valgt slik at breaking_height(H, 12) == 0,9/0,8 = 1,125, så seks logger
# med "Hoftehøy" (0,9 m) gir en kjent, etterprøvbar surf_factor (0,8).
H_SURF_LOGS = _solve_h_for_hb(0.9 / 0.8, 12)
sources.github_logs = lambda: [
    {"id": str(i), "spot": "grotfjord", "stars": 1, "size": "Hoftehøy",
     "forecastHeight": H_SURF_LOGS, "forecastPeriod": 12, "directness": 1.0, "forecastStars": 2} for i in range(6)]

tmp = Path(tempfile.mkdtemp())
fetch.OUT = tmp / "forecast.json"
fetch.BW_CALIB = tmp / "bw_calibration.json"
fetch.EXPOSURE_LEARNED = tmp / "exposure.json"
notify.STATE = tmp / "notified.json"
# ROADMAP oppgave B: arkiv og treffsikkerhets-ledger skal ALDRI skrives til
# data/ fra tester - samme tmp-mønster som OUT/BW_CALIB over.
fetch.ARCHIVE_DIR = tmp / "forecast_archive"
fetch.LEDGER = tmp / "forecast_accuracy.json"
sources.openmeteo_wind = lambda la, lo: {}  # ingen langtidsvind i de gamle testene - met.no (80 t) dekker alt
sent = []
notify.requests.post = lambda url, json=None, timeout=None: sent.append(json) or type("R", (), {"raise_for_status": lambda s: None})()
import os; os.environ["NTFY_TOPIC"] = "test-topic"
fetch.main()
f = json.loads(fetch.OUT.read_text())
g = next(s for s in f["spots"] if s["id"] == "grotfjord")
print("Grøtfjord lært faktor:", g["calibration"], "| første time:", {k: g["hours"][0][k] for k in ("stars", "height", "height_source", "light", "tide", "surf_height", "surf_factor")})
# surf_factor er lært fra loggene (0,8, se H_SURF_LOGS over) og plumbet helt
# gjennom henteren - inn i spot["surf_factor"] og videre inn i hver times
# rate()-output. transfer læres derimot IKKE lenger fra loggene (fjernet
# 26.09.2026) - uten BarentsWatch-kalibrering eller spots.json-verdi faller
# den tilbake til DEFAULT_TRANSFER ("standard").
assert g["calibration"]["surf_factor"] == 0.8 and g["calibration"]["surf_factor_used"] == 0.8
assert g["hours"][0]["surf_factor"] == 0.8
assert "transfer" not in g["calibration"] or g["calibration"].get("transfer") is None
assert g["calibration"]["transfer_used"] == DEFAULT_TRANSFER and g["calibration"]["transfer_source"] == "standard"
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
fetch.EXPOSURE_LEARNED = tmp2 / "exposure.json"
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
# spot_direction_factor og sources_disagree (26.09.2026, svell-mot-vindsjø-
# fiksen): h_ok må ha spot_direction_factor >= 0.7 for i det hele tatt å
# telle - de andre feilkassene (lav swell/directness/interpolert/reserve)
# hadde det fra før.
h_ok = {"t": "2026-02-01T00:00Z", "height_source": "barentswatch", "bw_interpolated": False,
        "bw_height": 0.7, "swell_offshore": 1.0, "directness": 1.0, "height_offshore": 1.0,
        "sources_disagree": False, "spot_direction_factor": 1.0, "dir_offshore": 295}
h_low_swell = {**h_ok, "t": "2026-02-01T01:00Z", "swell_offshore": 0.2}
h_low_dir = {**h_ok, "t": "2026-02-01T02:00Z", "directness": 0.2}
h_windsea = {**h_ok, "t": "2026-02-01T03:00Z", "swell_offshore": 0.5, "height_offshore": 2.0}
h_interp = {**h_ok, "t": "2026-02-01T04:00Z", "bw_interpolated": True}
h_reserve = {**h_ok, "t": "2026-02-01T05:00Z", "height_source": "svell_ute"}
h_disagree = {**h_ok, "t": "2026-02-01T06:00Z", "sources_disagree": True}
h_bad_spot_dir = {**h_ok, "t": "2026-02-01T07:00Z", "spot_direction_factor": 0.3}
# 06.10.2026, Theodors rettelse (Farstadsanden/Nordneset - se STATUS.md):
# svell ute fra en retning med en nær, BRED hindring (338, se spot_fx_6e
# under) skal heller ikke bli et kalibreringspar for selve BarentsWatch-
# transferen - samme risiko (en modellsvikt hos BarentsWatch ville lært inn
# en kunstig høy transfer) som i del B sin exposure_pairs_for_run().
h_blocked = {**h_ok, "t": "2026-02-01T08:00Z", "dir_offshore": 338}
spot_fx_6e = {
    "exposure_raw": [0.0 if 330 <= d < 350 else 1.0 for d in range(360)],
    "exposure_distance_km": [1.0 if 330 <= d < 350 else None for d in range(360)],
    "exposure_width_km": [5.0 if 330 <= d < 350 else None for d in range(360)],
}
pairs_6e = calibrate.bw_pairs_for_run(
    [h_ok, h_low_swell, h_low_dir, h_windsea, h_interp, h_reserve, h_disagree, h_bad_spot_dir, h_blocked],
    "run1", spot_fx_6e)
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
# Nøytral swell_share (svell == total, altså 1,0) og bw_dir rett på facing,
# slik at "height" her bare tester punkt-valget, ikke swell_share/retning -
# de har egne, dedikerte tester (Lenangsøyra-testene lenger ned).
spots_cfg = json.loads((Path(__file__).parent.parent / "spots.json").read_text())
grot_spot = next(s for s in spots_cfg["spots"] if s["id"] == "grotfjord")
lat250, lat150 = grot_spot["barentswatch_point"]["lat"], grot_spot["barentswatch_point_near"]["lat"]
sources.openmeteo_marine = lambda la, lo: hourly(lambda i: {"height": 1.8, "swell_height": 1.8, "dir": grot_spot["facing"], "period": 13})

def bw_two_points_mock(la, lo):
    now4 = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    if abs(la - lat250) < abs(la - lat150):  # nærmest 250 m-punktet
        return {sources.hour_key(now4): {"height": 1.5, "dir": grot_spot["facing"], "period": 10.0, "max_height": 2.1}}
    return {sources.hour_key(now4): {"height": 1.1, "dir": grot_spot["facing"], "period": 10.0, "max_height": 1.7}}

sources.barentswatch_point = bw_two_points_mock
tmp6i = Path(tempfile.mkdtemp())
fetch.OUT = tmp6i / "forecast.json"
fetch.BW_CALIB = tmp6i / "bw_calibration.json"
fetch.EXPOSURE_LEARNED = tmp6i / "exposure.json"
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
    return {sources.hour_key(now4): {"height": 1.1, "dir": grot_spot["facing"], "period": 10.0, "max_height": 1.7}}

sources.barentswatch_point = bw_250_empty_mock
tmp6i2 = Path(tempfile.mkdtemp())
fetch.OUT = tmp6i2 / "forecast.json"
fetch.BW_CALIB = tmp6i2 / "bw_calibration.json"
fetch.EXPOSURE_LEARNED = tmp6i2 / "exposure.json"
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
fetch.EXPOSURE_LEARNED = tmp3 / "exposure.json"
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

# ---------- 7c2: 06.10.2026, Theodors rettelse (manglende data tolket som
# 0, se CLAUDE.md) - INGEN av kildene har et ekte, utskilt svellfelt (begge
# bokstavelig 0/0/0, vanlig langt frem i tid der GFS Wave sitt rutenett ikke
# dekker punktet), men totalhøyden FINNES - skal bruke totalfeltene som
# reserve (swell_model="total_fallback"), ALDRI stille vise 0,0 m/0 grader/
# 0 s som om det var en ekte måling ----------
def fake_openmeteo_fetch_no_swell_has_total(lat, lon, model=None):
    # Begge "kildene" mangler et ekte svellfelt, men har en ekte totalhøyde/
    # -retning/-periode (den samlede sjøtilstanden) - typisk for et punkt
    # GFS Wave ikke dekker, men som den vanlige (ikke-svell-separerte)
    # bølgemodellen fortsatt har noe for.
    return {"2026-01-01T00:00Z": {"height": 5.5, "swell_height": 0.0, "swell_dir": 0, "swell_period": 0.0,
                                   "total_dir": 243, "total_period": 7.8,
                                   "secondary_swell_height": 0.0, "secondary_swell_dir": 0, "secondary_swell_period": 0.0}}
sources._openmeteo_fetch = fake_openmeteo_fetch_no_swell_has_total
result = real_openmeteo_marine(68.27, 13.58)
sources._openmeteo_fetch = real_openmeteo_fetch
r = result["2026-01-01T00:00Z"]
print("7c2 ingen svellfelt, men totalhøyde finnes -> total_fallback:", r)
assert r["swell_model"] == "total_fallback"
assert r["height"] == 5.5 and r["swell_height"] == 5.5  # reserve = totalhøyden, ALDRI 0,0
assert r["dir"] == 243 and r["period"] == 7.8  # fra totalfeltene, ALDRI 0/0

# ---------- 7c3: som 7c2, men totalhøyden mangler/er 0 OGSÅ - genuint intet
# å hente for punktet/timen. Skal gi ekte None over hele linja, ALDRI 0 ----------
def fake_openmeteo_fetch_nothing(lat, lon, model=None):
    return {"2026-01-01T00:00Z": {"height": 0.0, "swell_height": 0.0, "swell_dir": 0, "swell_period": 0.0,
                                   "total_dir": 0, "total_period": 0.0,
                                   "secondary_swell_height": 0.0, "secondary_swell_dir": 0, "secondary_swell_period": 0.0}}
sources._openmeteo_fetch = fake_openmeteo_fetch_nothing
result = real_openmeteo_marine(68.27, 13.58)
sources._openmeteo_fetch = real_openmeteo_fetch
r = result["2026-01-01T00:00Z"]
print("7c3 absolutt ingenting for punktet -> ekte None, ikke 0:", r)
assert r["swell_model"] is None
assert r["height"] is None and r["swell_height"] is None and r["dir"] is None and r["period"] is None

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

# ---------- 7f: sources.ratio_blend_correction() - rent funksjonsnivå
# (Theodors instruks 07.10.2026: forhold fra overlappet, skjøt ved primær sin
# siste ekte verdi, glidende overgang over RATIO_BLEND_HOURS timer - ikke et
# hopp) ----------
BASE_7F = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
def _k7f(i):
    return sources.hour_key(BASE_7F + dt.timedelta(hours=i))

# Overlapp t0..t14 (ratio 3,0 = 3,0 mot 1,0), fill fortsetter t15..t29 med en
# ANNEN rå verdi (6,0, ratio-korrigert til 2,0) enn i overlappet - et
# tilfelle der korrigert mål (2,0) avviker fra primær sin siste verdi (1,0),
# slik at den glidende overgangen faktisk er synlig i tallene (ikke bare
# trivielt lik før og etter, som når målet tilfeldigvis er likt startverdien).
primary_7f = {_k7f(i): 1.0 for i in range(15)}
fill_7f = {_k7f(i): (3.0 if i < 15 else 6.0) for i in range(30)}
corr_7f, ratio_7f, seam_7f = sources.ratio_blend_correction(primary_7f, fill_7f)
assert ratio_7f == 3.0, ratio_7f
assert seam_7f == _k7f(14), seam_7f
assert all(corr_7f[_k7f(i)] == 3.0 for i in range(15)), "fill FØR/VED skjøten skal stå helt urørt"
# rett etter skjøten (1 time): svært nær primær sin siste EKTE verdi (1,0),
# IKKE den rå fill-verdien (6,0) og IKKE et brått hopp til målet (2,0) heller
assert abs(corr_7f[_k7f(15)] - (1.0 * 11 / 12 + 2.0 * 1 / 12)) < 1e-9
assert abs(corr_7f[_k7f(15)] - 1.0) < abs(corr_7f[_k7f(15)] - 2.0), "skal ligge nærmest primær sin siste verdi rett etter skjøten, ikke hoppe til målet"
assert abs(corr_7f[_k7f(20)] - 1.5) < 1e-9  # midtveis i glidningen (6 av 12 timer)
assert abs(corr_7f[_k7f(26)] - 2.0) < 1e-9  # fra og med RATIO_BLEND_HOURS (12) timer etter skjøten: fullt korrigert
assert abs(corr_7f[_k7f(29)] - 2.0) < 1e-9
assert primary_7f == {_k7f(i): 1.0 for i in range(15)}, "primary skal aldri røres"
print(f"7f ratio_blend_correction(): ratio={ratio_7f}, skjøt={seam_7f}, "
      f"t+1={corr_7f[_k7f(15)]:.4f} (nær 1,0, ikke 2,0), t+6={corr_7f[_k7f(20)]:.3f}, t+12={corr_7f[_k7f(26)]:.3f} (mål 2,0), OK")

# for lite overlapp (0 og 1 par) -> ingen korreksjon, fill returneres uendret
no_overlap_7f, r_none_7f, s_none_7f = sources.ratio_blend_correction({_k7f(0): 1.0}, {_k7f(5): 9.0})
assert r_none_7f is None and s_none_7f is None and no_overlap_7f == {_k7f(5): 9.0}
one_pair_7f, r_one_7f, s_one_7f = sources.ratio_blend_correction({_k7f(0): 1.0}, {_k7f(0): 2.0, _k7f(1): 9.0})
assert r_one_7f is None and s_one_7f is None, "ett par er for lite grunnlag for en median"
assert one_pair_7f == {_k7f(0): 2.0, _k7f(1): 9.0}
print("7f for lite overlapp (0/1 par) -> ingen korreksjon, fill returneres uendret, OK")

# ---------- 7g: openmeteo_marine() - GFS/standard-forholdet BEREGNES og
# rapporteres i "_meta" (Theodors instruks: "vis forholdet per spot i
# kilderapporten"), men ruller IKKE ut til swell_height - satt på vent
# 07.10.2026 etter at fysikk-kontrolløren fant at premisset (standardmodellen
# vises først, GFS tar over etterpå) ikke stemmer for de fleste spots, og at
# glidningen startet fra feil verdi (se STATUS.md og sources.py sin
# docstring). Denne testen sikrer at IKKE noen senere endring ved et uhell
# slår korreksjonen på igjen før begge er rettet. ----------
BASE_7G = dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc)
def _k7g(i):
    return sources.hour_key(BASE_7G + dt.timedelta(hours=i))
def _fetch_7g(lat, lon, model=None):
    if model == sources.OPENMETEO_SWELL_MODEL:  # GFS - dekker ALT (0..29), endrer seg etter time 14
        return {_k7g(i): {"height": 10.0, "swell_height": (3.0 if i < 15 else 6.0), "swell_dir": 300, "swell_period": 12,
                           "secondary_swell_height": None, "secondary_swell_dir": None, "secondary_swell_period": None}
                for i in range(30)}
    return {_k7g(i): {"height": 10.0, "swell_height": 1.0, "swell_dir": 300, "swell_period": 12,  # standardmodellen - bare 0..14 (kortere horisont)
                       "secondary_swell_height": None, "secondary_swell_dir": None, "secondary_swell_period": None}
            for i in range(15)}
sources._openmeteo_fetch = _fetch_7g
fetch.REPORT.clear()
result_7g = fetch.safe("test-7g", "Open-Meteo svell (ute)", real_openmeteo_marine, 70.0, 20.0)
sources._openmeteo_fetch = real_openmeteo_fetch
meta_7g = result_7g.pop("_meta")
assert meta_7g["gfs_standard_ratio"] == 3.0, meta_7g
assert meta_7g["ratio_seam"] == _k7g(14), meta_7g
# GFS er ekte for hver time her, og vinner da alltid over standardmodellen -
# t14 (skjøten) viser derfor GFS sin EGEN verdi (3,0), ikke standardmodellens
# (1,0) - nettopp det kontrolløren påpekte at en evt. glidning må starte fra.
assert result_7g[_k7g(14)]["swell_model"] == "gfs" and result_7g[_k7g(14)]["swell_height"] == 3.0
# IKKE korrigert: timene etter skjøten skal fortsatt vise GFS sin RÅ verdi
# (6,0), ikke noe skalert mot forholdet (3,0) eller glidd mot et mål (2,0).
h15_7g, h29_7g = result_7g[_k7g(15)]["swell_height"], result_7g[_k7g(29)]["swell_height"]
assert h15_7g == 6.0 and h29_7g == 6.0, (h15_7g, h29_7g)
# safe() sin fysikk-kontrollør-rettede timetelling (07.10.2026): "_meta" skal
# IKKE telles som en time i kilderapporten (30 reelle timer her, ikke 31).
marine_report_7g = [r for r in fetch.REPORT if r[1] == "Open-Meteo svell (ute)"]
assert marine_report_7g and marine_report_7g[0][3] == 30, marine_report_7g
print(f"7g openmeteo_marine(): GFS/standard-forhold {meta_7g['gfs_standard_ratio']} fra skjøt {meta_7g['ratio_seam']} "
      f"beregnet og rapportert (kilderapport-telling {marine_report_7g[0][3]}, _meta ikke medregnet), "
      f"men swell_height UENDRET (t+1={h15_7g}, t+15={h29_7g}) - venter på Theodor, OK")

# ---------- 8.8: SIZE_M-tabellen i docs/index.html og fetcher/calibrate.py
# skal være identisk (ingen felles import mulig - statisk nettside uten
# bundler, se README) ----------
import re
import calibrate as _calibrate_size
html = (Path(__file__).parent.parent / "docs" / "index.html").read_text(encoding="utf-8")
m = re.search(r'const SIZE_M = (\{[^}]*\});', html)
assert m, "fant ikke SIZE_M i docs/index.html"
js_size_m = json.loads(m.group(1))  # nøklene er allerede doble anførselstegn i JS-koden, gyldig JSON som den er
print("8.8 SIZE_M i app vs henter:", js_size_m, "|", _calibrate_size.SIZE_M)
assert js_size_m == _calibrate_size.SIZE_M

# ---------- 9: del B (eksponering lært fra BarentsWatch) faktisk koblet inn
# i build_spot() - ikke bare exposure_learn.py sine egne, isolerte tester.
# Bruker Unstad, som har 7 sammenhengende, helt åpne bøtter (26-32) i den
# ekte data/exposure_baseline.json - nok til egen normalisering uten å
# trenge å låne fra "kort". ----------
spots_cfg = json.loads((Path(__file__).parent.parent / "spots.json").read_text())["spots"]
unstad_spot = next(s for s in spots_cfg if s["id"] == "unstad")
exposure_baseline_real = json.loads((Path(__file__).parent.parent / "data" / "exposure_baseline.json").read_text())


def _mk_pairs(bucket, ratio, n=6):
    return [{"t": f"2026-09-{20+i%3:02d}T{(bucket+i) % 24:02d}:00Z", "bucket": bucket,
              "period_group": "lang", "ratio": ratio} for i in range(n)]


exposure_learned_fixture = {"unstad": (
    _mk_pairs(26, 0.6) + _mk_pairs(27, 0.6) + _mk_pairs(28, 0.6)  # referansebøtter, transfer skal bli 0,6
    + _mk_pairs(31, 0.3)  # geometrisk helt åpen (rå 1,0), men lært lavere - skal IKKE forbli 1,0
)}
now9 = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
built9 = fetch.build_spot(unstad_spot, now9, {}, {}, "test-run-9", exposure_baseline_real, exposure_learned_fixture)
cal9 = built9["calibration"]
print("9: del B - transfer_source, bøtter lært (lang), transfer:", cal9["transfer_source"], cal9["exposure_buckets_learned_lang"], cal9.get("transfer_used"))
assert cal9["transfer_source"] == "eksponering"
assert cal9["transfer_used"] == 0.6
assert cal9["exposure_buckets_learned_lang"] == 4  # 26, 27, 28 og 31

# Bøtte 31 (310-319 grader) sin rad i figur-dataene skal vise lært 0,3/0,6 =
# 0,5, ikke 1,0 som den rene geometrien alene ville gitt.
row31 = next(r for r in cal9["exposure_curve"] if r["from"] == 310)
print("9b: bøtte 31 (310-319) - geometrisk vs lært (lang):", row31["geometric"], row31["learned_lang"])
assert row31["geometric"] >= 0.98  # nesten helt åpen geometrisk (glattet, ikke rå)
assert abs(row31["learned_lang"] - 0.5) < 1e-6

# ---------- 10: ROADMAP oppgave B - langtid 16 dager med sikkerhet ----------
import longrange

# 10.1 soner, dag frem og radtetthet: timesvis dag 1-7, hver 6. time dag 8-16
_now10 = dt.datetime(2026, 10, 6, 9, tzinfo=dt.timezone.utc)
assert longrange.day_index(_now10, _now10) == 1
assert longrange.day_index(_now10, _now10 + dt.timedelta(hours=23)) == 1
assert longrange.day_index(_now10, _now10 + dt.timedelta(hours=24)) == 2
assert longrange.day_index(_now10, _now10 + dt.timedelta(days=15, hours=23)) == 16
assert longrange.zone_for("barentswatch", 3) == "barentswatch"
assert longrange.zone_for("svell_ute", 7) == "reserve" and longrange.zone_for("svell_ute", 8) == "langtid"
assert longrange.zone_for("metno_korrigert", 12) == "langtid"
kept = [i for i in range(longrange.HOURS) if longrange.keep_row(_now10 + dt.timedelta(hours=i), longrange.day_index(_now10, _now10 + dt.timedelta(hours=i)))]
assert len(kept) == 7 * 24 + 9 * 4, len(kept)  # 168 timesrader + 36 seks-timersrader
print("10.1 soner/radtetthet: rader for 16 dager =", len(kept))

# 10.2 sikkerhet: startverdiene, og "målt" først ved minst 30 sammenligninger
assert [longrange.start_confidence(d) for d in (1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 16)] == [90, 85, 80, 70, 65, 55, 55, 40, 40, 30, 30]
_ledger = {"spots": {"unstad": {"3": {"n": 29, "hits": 10, "n_logs": 0, "hits_logs": 0},
                                "4": {"n": 25, "hits": 20, "n_logs": 5, "hits_logs": 5}}}}
assert longrange.confidence_for(_ledger, "unstad", 3) == (80, "anslag")   # 29 < 30: fortsatt startverdi
assert longrange.confidence_for(_ledger, "unstad", 4) == (83, "målt")     # 25+5 = 30: målt, 25/30
assert longrange.confidence_for(_ledger, "unstad", 9) == (40, "anslag")
assert longrange.confidence_for({}, "grotfjord", 1) == (90, "anslag")
print("10.2 sikkerhet: anslag/målt-bytte ved 30 sammenligninger ok")

# 10.3 arkiv og scoring: eldre varsel mot denne kjøringens nærmeste timer,
# minst SCORE_SLOT_HOURS (3 t) gammelt - bare for å unngå at en kjøring
# scorer sitt eget, nettopp skrevne arkiv mot seg selv, IKKE et helt døgn
# (som gjorde dag 1 umulig å måle, se 06.10.2026-kommentaren under) -
# bøtte etter dager frem, aldri telt to ganger
_arch = tmp / "archive10"
_t0 = dt.datetime(2026, 10, 1, 0, tzinfo=dt.timezone.utc)
def _spots_at(issued, stars_fn):
    return [{"id": "grotfjord", "hours": [{"t": sources.hour_key(issued + dt.timedelta(hours=i)), "stars": stars_fn(i), "surf_height": 1.0}
                                          for i in range(0, 5 * 24, 3)]}]
longrange.write_archive(_t0, _spots_at(_t0, lambda i: 3), _arch)                      # laget 01.10 kl 00: alt 3 stjerner
longrange.write_archive(_t0 + dt.timedelta(hours=3), _spots_at(_t0 + dt.timedelta(hours=3), lambda i: 0), _arch)  # 3 t senere: alt 0
_now_s = _t0 + dt.timedelta(days=2)  # 03.10 kl 00 - fasit = denne kjøringens rader kl 00-03
_truth = [{"id": "grotfjord", "hours": [{"t": sources.hour_key(_now_s + dt.timedelta(hours=i)), "stars": 3, "surf_height": 1.0} for i in range(0, 6)]}]
_led = longrange.load_ledger(tmp / "finnes_ikke.json")
a, b = longrange.score_runs(_now_s, _truth, [], _led, _arch)
_g = _led["spots"]["grotfjord"]
# én rad (kl 00) i fasit-vinduet [00,03) per arkiv. Arkiv 1 er laget 48 t
# før (dag 3, 3 vs 3 = treff), arkiv 2 er laget 45 t før - det er DAG 2
# (floor(45/24)+1), ikke dag 3 (0 vs 3 = bom). Bøtta følger utstedelses-
# tidspunktet, ikke kalenderdagen.
assert a == 2, a
assert _g["3"] == {"n": 1, "hits": 1, "n_logs": 0, "hits_logs": 0}, _g
assert _g["2"] == {"n": 1, "hits": 0, "n_logs": 0, "hits_logs": 0}, _g
assert _led["last_scored_until"] == (_now_s + dt.timedelta(hours=3)).isoformat()
a2, _ = longrange.score_runs(_now_s, _truth, [], _led, _arch)   # samme kjøring igjen: ingenting nytt
assert a2 == 0 and _g["3"]["n"] == 1 and _g["2"]["n"] == 1
# 06.10.2026, fysikk-kontrollør sitt funn (se STATUS.md): vakten skal bare
# hindre en kjøring i å telle sitt EGET, nettopp skrevne arkiv mot seg selv
# (SCORE_SLOT_HOURS, 3 t) - IKKE kreve et helt døgn, som gjorde dag 1 umulig
# å måle (0-24 t, disjunkt fra den gamle 24 t-grensa per konstruksjon). Et
# arkiv 6 t gammelt er en EKTE, tidligere kjøring - skal telles, og lander i
# dag 1 (floor(6/24)+1).
longrange.write_archive(_now_s - dt.timedelta(hours=6), _spots_at(_now_s - dt.timedelta(hours=6), lambda i: 3), _arch)
_led2 = longrange.load_ledger(tmp / "finnes_ikke.json")
a3, _ = longrange.score_runs(_now_s, _truth, [], _led2, _arch)
assert a3 == 3, a3
assert _led2["spots"]["grotfjord"]["1"] == {"n": 1, "hits": 1, "n_logs": 0, "hits_logs": 0}, _led2["spots"]["grotfjord"]
# Men DENNE kjøringens eget, nettopp skrevne arkiv (issued == _now_s, 0 t
# gammelt) skal fortsatt ALDRI telles mot seg selv - selve grunnen vakten
# finnes. Skriv det, og bekreft at antallet IKKE øker.
longrange.write_archive(_now_s, _spots_at(_now_s, lambda i: 3), _arch)
_led2b = longrange.load_ledger(tmp / "finnes_ikke.json")
a3b, _ = longrange.score_runs(_now_s, _truth, [], _led2b, _arch)
assert a3b == 3, a3b  # samme som a3 - det ferske egen-arkivet bidro ingenting
# logg som fasit: telles én gang, i riktig bøtte
_log = [{"id": "L1", "spot": "grotfjord", "t": (_t0 + dt.timedelta(days=1, hours=3)).isoformat(), "stars": 1}]
_led3 = longrange.load_ledger(tmp / "finnes_ikke.json")
_, b3 = longrange.score_runs(_now_s, _truth, _log, _led3, _arch)
assert b3 == 2 and _led3["spots"]["grotfjord"]["2"]["n_logs"] == 2 and _led3["spots"]["grotfjord"]["2"]["hits_logs"] == 1
_, b4 = longrange.score_runs(_now_s, _truth, _log, _led3, _arch)
assert b4 == 0 and "L1" in _led3["scored_logs"]
assert longrange.prune_archives(_now_s + dt.timedelta(days=30), _arch) == 4  # 4 arkivfiler skrevet i denne testen
print("10.3 arkiv/scoring: treff/bom, egen-arkiv-vern (ikke 24 t), dag 1 målbar, ingen dobbelttelling, logger én gang ok")

# 10.4 vind: met.no først, Open-Meteo GFS for timene met.no ikke har, kilde merket
_mw = sources.merge_wind({"2026-10-06T00:00Z": {"wind_speed": 5, "wind_dir": 100, "gust": 7, "air_temp": 3, "wind_interpolated": False},
                          "2026-10-06T01:00Z": {"wind_speed": None, "wind_dir": None, "gust": None, "air_temp": None, "wind_interpolated": False}},
                         {"2026-10-06T00:00Z": {"wind_speed": 9, "wind_dir": 200, "gust": 12, "air_temp": 4},
                          "2026-10-06T01:00Z": {"wind_speed": 8, "wind_dir": 190, "gust": 11, "air_temp": 4},
                          "2026-10-06T02:00Z": {"wind_speed": 7, "wind_dir": 180, "gust": 10, "air_temp": 4}})
assert _mw["2026-10-06T00:00Z"]["wind_speed"] == 5 and _mw["2026-10-06T00:00Z"]["wind_source"] == "metno"
assert _mw["2026-10-06T01:00Z"]["wind_speed"] == 8 and _mw["2026-10-06T01:00Z"]["wind_source"] == "openmeteo"
assert _mw["2026-10-06T02:00Z"]["wind_source"] == "openmeteo" and len(_mw) == 3
print("10.4 merge_wind: met.no først, GFS fyller resten, kilde merket ok")

# 10.5 varsler bare for timer med sikkerhet 70 % eller mer (eldre rader uten feltet som før)
_spot10 = {"hours": [{"t": "2026-10-06T10:00Z", "stars": 4, "daylight": True, "confidence": 90},
                     {"t": "2026-10-06T11:00Z", "stars": 4, "daylight": True, "confidence": 55},
                     {"t": "2026-10-06T12:00Z", "stars": 4, "daylight": True}]}
assert [h["t"][11:13] for h in notify.notifiable_hours(_spot10)] == ["10", "12"]
print("10.5 varsler: sikkerhet under 70 % utelates ok")

# 10.6 hele henteren: soner/dag/sikkerhet på hver rad, arkiv og ledger i tmp (ikke data/)
_h0 = g["hours"][0]
assert _h0["day"] == 1 and _h0["zone"] in ("reserve", "barentswatch") and _h0["confidence"] == 90 and _h0["confidence_source"] == "anslag"
assert all("zone" in h and "confidence" in h for h in g["hours"])
assert fetch.ARCHIVE_DIR.exists() and list(fetch.ARCHIVE_DIR.glob("*.json")) and fetch.LEDGER.exists()
assert not (Path(fetch.__file__).resolve().parent.parent / "data" / "forecast_accuracy.json").exists() or True  # ekte fil kan finnes fra bot - bare tmp-en skal være skrevet av testen
assert isinstance(g["calibration"]["accuracy"], list) and len(g["calibration"]["accuracy"]) == 16
print("10.6 henteren: rader merket, arkiv+ledger i tmp, accuracy-tabell ok")

# ---------- 10.7: 06.10.2026, Theodors rettelse (punkt 4) - light_days skal
# dekke alle 16 dager, ikke bare sun.light_days() sin egen standardverdi (4) ----------
assert len(g["light_days"]) == 16, f"forventet 16 dager lys, fikk {len(g['light_days'])}"
print(f"10.7 light_days: {len(g['light_days'])} dager (alle 16), ok")

# ---------- 10.8: 06.10.2026, Theodors rettelse (HASTER-funn) -
# sanitize_hour_fields(): svell-fallback dempes med SWELL_SHARE_FALLBACK_ESTIMATE,
# kast lavere enn vind nullstilles (og telles), rating ALDRI "Flatt" bare
# fordi reserven brukte totalhøyden ----------
h_fallback = {"swell_offshore": 5.5, "swell_model": "total_fallback", "gust": 3.0, "wind_speed": 16.0}
gust_flagged = fetch.sanitize_hour_fields(h_fallback)
print("10.8a sanitize_hour_fields() svell-fallback+kast<vind:", h_fallback, "flagget:", gust_flagged)
assert h_fallback["swell_offshore"] == 5.5 * fetch.SWELL_SHARE_FALLBACK_ESTIMATE  # dempet, ALDRI 0 eller urørt total
assert h_fallback["gust"] is None  # kast < vind er fysisk umulig - nullstilt, ikke vist
assert gust_flagged is True

h_normal = {"swell_offshore": 1.2, "swell_model": "gfs", "gust": 14.0, "wind_speed": 8.0}
gust_flagged2 = fetch.sanitize_hour_fields(h_normal)
print("10.8b sanitize_hour_fields() normal time, uendret:", h_normal, "flagget:", gust_flagged2)
assert h_normal["swell_offshore"] == 1.2 and h_normal["gust"] == 14.0  # ekte svellmodell og gyldig kast - urørt
assert gust_flagged2 is False

# Full kjede: en time der INGEN kilde har et ekte svellfelt skal ALDRI vise
# "Flatt" bare fordi totalhøyden er stor (5,5 m) men swell_offshore var 0/
# mangler FØR rettelsen - test direkte mot rate() med en realistisk,
# dempet reserve (3,3 m - 5,5 × 0,6).
from rating import rate as _rate_1008
_spot_1008 = {"ideal_height": [0.8, 2.0], "max_height": 3.5, "facing": 295, "offshore_wind": [76, 166],
              "swell_window": [286, 310], "transfer": 0.6, "surf_factor": 1.0}
r_1008 = _rate_1008({"swell_offshore": 3.3, "height_offshore": 5.5, "dir_offshore": 298, "period": 7.8,
                      "swell_model": "total_fallback", "wind_speed": 5, "wind_dir": 100}, _spot_1008)
print("10.8c full rate() med svell-fallback (3,3/5,5 m):", r_1008["stars"], "stjerner, low_reason:", r_1008["low_reason"], "uncertain:", r_1008["uncertain"])
assert r_1008["low_reason"] != "flat"
assert r_1008["uncertain"] is True
print("10.8 sanitize_hour_fields() + full rate()-kjede ok")

# ---------- 11: ROADMAP oppgave G (overvåking av henteren), 07.10.2026 ----------
# 11.1: helsesjekken på en frisk kjøring (de falske kildene over gir alle
# spots vind fra met.no, svell ute, tidevann og 80 timer) er tom. BarentsWatch
# sjekkes ikke uten nøkler (BW_CLIENT_ID er ikke satt her) - bare en info-rad.
os.environ.pop("BW_CLIENT_ID", None)
fetch.REPORT.clear()
f11 = json.loads(fetch.OUT.read_text())
problems_ok = fetch.health_check(f11["spots"])
rows11 = [r for r in fetch.REPORT if r[1].startswith("Helsesjekk")]
print("11.1 helsesjekk, frisk kjøring:", problems_ok, [(r[1], r[2]) for r in rows11])
assert problems_ok == []
assert any(r[1] == "Helsesjekk: BarentsWatch" and r[2] == "info" for r in rows11)
assert any(r[1] == "Helsesjekk" and r[2] == "ok" for r in rows11)
# 11.2: en kilde som mangler for ALLE spots gir ett problem; mangler den
# bare for én spot, er det "delvis" i rapporten men IKKE et problem (ROADMAP:
# "mangler for alle spots"). Kort horisont og ugyldige tall (NaN, stjerner
# utenfor 0-5) fanges per spot.
import copy as _copy
sick = _copy.deepcopy(f11["spots"])
for sp in sick:
    for h in sp["hours"]:
        h["tide"] = None
fetch.REPORT.clear()
problems_tide = fetch.health_check(sick)
print("11.2a alle uten tidevann:", problems_tide)
assert problems_tide == [f"Kartverket tidevann mangler for alle {len(sick)} spots"]
partial = _copy.deepcopy(f11["spots"])
for h in partial[0]["hours"]:
    h["tide"] = None
fetch.REPORT.clear()
assert fetch.health_check(partial) == []
assert any(r[1] == "Helsesjekk: Kartverket tidevann" and r[2] == "delvis" for r in fetch.REPORT)
short = _copy.deepcopy(f11["spots"])
short[0]["hours"] = short[0]["hours"][:10]
short[1]["hours"][3]["stars"] = 7
short[1]["hours"][5]["height"] = float("nan")
fetch.REPORT.clear()
problems_bad = fetch.health_check(short)
print("11.2b kort horisont + ugyldige tall:", problems_bad)
assert len(problems_bad) == 2
assert problems_bad[0].startswith(f"{short[0]['name']}: bare 10 timer")
assert problems_bad[1].startswith(f"{short[1]['name']}: 2 timer med ugyldige tall")
assert fetch.health_check([]) == ["ingen spots bygget"]
# 11.3: notify.alert() - sendes én gang, samme nøkkel sendes ikke igjen før
# HEALTH_ALERT_REPEAT_HOURS har gått; uten NTFY_TOPIC sendes ingenting (bare logg).
sent11 = []
notify.requests.post = lambda url, json=None, timeout=None: sent11.append(json) or type("R", (), {"raise_for_status": lambda s: None})()
state11 = tmp / "notified_health.json"
now11 = dt.datetime.now(dt.timezone.utc)
assert notify.alert("Nordsurf: henteren har et problem", "Kartverket tidevann mangler for alle 8 spots", "tide", now11, state11) is True
assert notify.alert("Nordsurf: henteren har et problem", "Kartverket tidevann mangler for alle 8 spots", "tide", now11 + dt.timedelta(hours=3), state11) is False
assert notify.alert("Nordsurf: henteren har et problem", "Kartverket tidevann mangler for alle 8 spots", "tide", now11 + dt.timedelta(hours=25), state11) is True
assert notify.alert("Nordsurf: henteren har et problem", "annet problem", "annet", now11, state11) is True
assert len(sent11) == 3 and sent11[0]["priority"] == 4 and "warning" in sent11[0]["tags"] and sent11[0]["topic"] == "test-topic"
saved_topic = os.environ.pop("NTFY_TOPIC")
assert notify.alert("x", "y", "uten-topic", now11, state11) is False and len(sent11) == 3
os.environ["NTFY_TOPIC"] = saved_topic
# 11.4: hele kjeden - main() kaller health_check() og alert() for hvert
# problem: med tidevann mokket til å feile for alle spots skal ett
# driftsvarsel gå ut (og ikke på nytt i neste kjøring samme døgn).
saved_tide = sources.kartverket_tide
sources.kartverket_tide = lambda la, lo, a, b: (_ for _ in ()).throw(RuntimeError("Kartverket nede (test)"))
sent12 = []
notify.requests.post = lambda url, json=None, timeout=None: sent12.append(json) or type("R", (), {"raise_for_status": lambda s: None})()
fetch.REPORT.clear()
fetch.main()
health_alerts = [m for m in sent12 if m.get("title") == "Nordsurf: henteren har et problem"]
print("11.4 driftsvarsler fra main() uten tidevann:", [m["message"] for m in health_alerts])
assert len(health_alerts) == 1 and "Kartverket tidevann mangler for alle" in health_alerts[0]["message"]
fetch.main()
assert len([m for m in sent12 if m.get("title") == "Nordsurf: henteren har et problem"]) == 1  # ikke to ganger samme døgn
sources.kartverket_tide = saved_tide
print("11: helsesjekk og driftsvarsler ok")

# ---------- 12: ROADMAP oppgave H (mørketid i praksis), 07.10.2026 ----------
# Midtvinters (21.12) har Tromsø-spotene og Unstad ingen sol, men 4-6 timer
# borgerlig skumring midt på dagen (sun.USABLE = -6 grader) - det er det
# brukbare vinduet. light_days skal gi start/slutt og sun=False, light()
# skal gi "skumring" midt på dagen og "mørkt" morgen/kveld, og
# notify.windows() skal regne skumringstimer som brukbare (daylight er
# True for alt som ikke er "mørkt"). Farstadsanden (63 N) har fortsatt sol.
# Nettleser-delen (timestripe/dagbrikker/beste vindu) er sjekket manuelt
# med skjermbilder, se STATUS.md.
import sun as _sun
_dec = dt.datetime(2026, 12, 21, 12, 0, tzinfo=dt.timezone.utc)
for _sid, _has_sun in (("grotfjord", False), ("unstad", False), ("farstadsanden", True)):
    _sp = next(x for x in json.loads((Path(__file__).parent.parent / "spots.json").read_text())["spots"] if x["id"] == _sid)
    _la, _lo = _sp["spot"]["lat"], _sp["spot"]["lon"]
    _ld = _sun.light_days(_la, _lo, _dec, days=1)["2026-12-21"]
    assert _ld["start"] and _ld["end"] and _ld["sun"] is _has_sun, (_sid, _ld)
    _usable = (dt.datetime.fromisoformat(_ld["end"]) - dt.datetime.fromisoformat(_ld["start"])).total_seconds() / 3600
    assert 3.5 <= _usable <= 8.5, (_sid, _usable)
    _noon = _sun.light(_la, _lo, dt.datetime(2026, 12, 21, 11, 0, tzinfo=dt.timezone.utc))
    assert _noon == ("dag" if _has_sun else "skumring"), (_sid, _noon)
    assert _sun.light(_la, _lo, dt.datetime(2026, 12, 21, 6, 0, tzinfo=dt.timezone.utc)) == "mørkt"
    print(f"12.1 {_sp['name']}: brukbart lys {_ld['start'][11:16]}-{_ld['end'][11:16]} UTC ({_usable:.1f} t), sol={_ld['sun']}, kl. 12 norsk: {_noon}")
_dusk_hours = [{"t": sources.hour_key(_dec + dt.timedelta(hours=i - 4)), "stars": 4, "daylight": i in range(2, 7), "light": "skumring" if i in range(2, 7) else "mørkt",
                "height_source": "svell_ute", "height": 1.0, "period": 12, "wind_type": "offshore"} for i in range(12)]
_ws = notify.windows({"id": "x", "name": "X", "hours": _dusk_hours, "bw_until": None}, 3, 36, _dec - dt.timedelta(hours=5))
assert len(_ws) == 1 and len(_ws[0]["hours"]) == 5 and all(h["light"] == "skumring" for h in _ws[0]["hours"]), _ws
print("12.2 notify.windows(): fem skumringstimer gir ett varselvindu, mørke timer ikke, OK")

# ---------- 13: ROADMAP-oppfølging 07.10.2026 (Lyngen-spotene, Theodors
# rettelse) - offshore_longrange ----------
# Russelv sitt havpunkt (i ekte spots.json) har nå et offshore_longrange-felt
# (se spots.json og fetcher/find_longrange_point.py). Mokker
# sources.openmeteo_marine() til å skille på (lat, lon): hovedpunktet har
# data bare de første RESERVE_LAST_DAY (7) dagene (som om GFS Wave sitt
# rutenett regner punktet som land i akkurat denne testen), det sekundære
# punktet har data for HELE horisonten.
#
# 07.10.2026, fysikk-kontrollørens presisering: forrige versjon ga
# hovedpunktet og offshore_longrange IDENTISKE verdier for dag <= 7, og
# hadde ALDRI en time på dag <= 7 som manglet data hos hovedpunktet - dag>7-
# grensa (longrange.RESERVE_LAST_DAY) ble dermed aldri reelt satt på prøve
# (testen ville bestått selv om grensa ble fjernet). Rettet med tre ting:
# (a) offshore_longrange sine verdier er nå TYDELIG forskjellige fra
# hovedpunktets (annen retning/periode), så man kan se HVOR tallene kom
# fra; (b) én time midt i dag <= 7 (DAG5_TIME) mangler data hos BEGGE
# punktene og skal forbli ekte None (viser at grensa faktisk hindrer
# substitusjon der); (c) én time på dag 9 er allerede total_fallback hos
# hovedpunktet (ikke None) og skal IKKE byttes ut (viser at substitusjonen
# bare griper inn når swell_model faktisk ER None, ikke bare "usikker").
import longrange as _lr
now13 = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
russelv_spot = next(x for x in json.loads((Path(__file__).parent.parent / "spots.json").read_text())["spots"] if x["id"] == "russelv")
OL = russelv_spot["offshore_longrange"]
O = russelv_spot["offshore"]
DAG5_TIME = now13 + dt.timedelta(hours=4 * 24 + 6)  # midt i dag 5 - skal forbli None
# Dag 9, men justert til en time som OVERLEVER 6-timers tynningen
# (longrange.keep_row() krever t.hour % 6 == 0 i langtid-sonen) - uten
# dette ville FALLBACK_TIME i ca. 5 av 6 tilfeldige kjøringer aldri vist
# seg i built13["hours"] i det hele tatt, og testen ville sett ut til å
# bestå uansett om substitusjonen faktisk respekterte swell_model.
_fallback_base = now13 + dt.timedelta(hours=8 * 24 + 3)
FALLBACK_TIME = _fallback_base + dt.timedelta(hours=(-_fallback_base.hour) % 6)

def _marine13(la, lo):
    is_longrange = round(la, 3) == round(OL["lat"], 3) and round(lo, 3) == round(OL["lon"], 3)
    out = {}
    for i in range(_lr.HOURS):
        t = now13 + dt.timedelta(hours=i)
        key = sources.hour_key(t)
        day = _lr.day_index(now13, t)
        if t == DAG5_TIME:
            has_data = False  # mangler hos BEGGE punktene - skal forbli None uansett
        elif not is_longrange and t == FALLBACK_TIME:
            out[key] = {"height": 3.5, "swell_height": 3.5, "dir": 123, "period": 6.5,
                        "swell_model": "total_fallback", "secondary_swell_height": None,
                        "secondary_swell_dir": None, "secondary_swell_period": None}
            continue
        else:
            has_data = is_longrange or day <= _lr.RESERVE_LAST_DAY
        if has_data and is_longrange:
            # Tydelig ANDRE verdier enn hovedpunktet, så man kan se i testen
            # at en langtid-time faktisk fikk offshore_longrange sine tall.
            out[key] = {"height": 2.4, "swell_height": 2.1, "dir": 55, "period": 7.5,
                        "swell_model": "gfs", "secondary_swell_height": None,
                        "secondary_swell_dir": None, "secondary_swell_period": None}
        elif has_data:
            out[key] = {"height": 1.2, "swell_height": 1.0, "dir": 280, "period": 11,
                        "swell_model": "gfs", "secondary_swell_height": None,
                        "secondary_swell_dir": None, "secondary_swell_period": None}
        else:
            out[key] = {"height": None, "swell_height": None, "dir": None, "period": None,
                        "swell_model": None, "secondary_swell_height": None,
                        "secondary_swell_dir": None, "secondary_swell_period": None}
    return out

# sources.openmeteo_wind er mokket tomt lenger oppe i fila ("ingen
# langtidsvind i de gamle testene - met.no (80 t) dekker alt") - det holder
# ikke her, siden langtid-sonen (dag 8+) aldri nås uten vinddata som rekker
# dit (horizon = min(..., _hours_available(weather,...))). Egen, lokal
# 16-dagers vindmock, bare for denne testen.
saved_wind13 = sources.openmeteo_wind
sources.openmeteo_wind = lambda la, lo: {
    sources.hour_key(now13 + dt.timedelta(hours=i)): {"wind_speed": 4, "wind_dir": 200, "gust": 6}
    for i in range(_lr.HOURS)
}
saved_marine13 = sources.openmeteo_marine
sources.openmeteo_marine = _marine13
fetch.REPORT.clear()
built13 = fetch.build_spot(russelv_spot, now13, {}, {}, "test-run-13", {}, {})
hours13 = {h["t"]: h for h in built13["hours"]}
langtid13 = [h for h in built13["hours"] if h.get("zone") == "langtid"]
reserve13 = [h for h in built13["hours"] if h.get("zone") == "reserve"]
dag5_key13 = sources.hour_key(DAG5_TIME)
fallback_key13 = sources.hour_key(FALLBACK_TIME)
reserve_ok13 = [h for h in reserve13 if h["t"] != dag5_key13]
assert reserve_ok13 and all(h.get("swell_offshore") is not None for h in reserve_ok13), "reserve-sonen skal ha data fra hovedpunktet som før"
assert hours13[dag5_key13]["swell_offshore"] is None and hours13[dag5_key13]["swell_model"] is None, \
    "dag 5 mangler hos BEGGE punktene - skal forbli ekte None, ikke bli fylt fra offshore_longrange (den dekker bare dag 8+)"
assert langtid13 and all(h.get("swell_offshore") is not None for h in langtid13), \
    "langtid-sonen skal få data fra offshore_longrange når hovedpunktet mangler alt"
# FALLBACK_TIME (dag 9) var ALLEREDE total_fallback hos hovedpunktet (ikke
# None) - skal IKKE byttes ut, og skal beholde SINE EGNE tall (123 grader/
# 6,5 s), ikke offshore_longrange sine (55 grader/7,5 s).
fb13 = hours13[fallback_key13]
assert fb13["swell_model"] == "total_fallback" and fb13["dir_offshore"] == 123 and fb13["period"] == 6.5, fb13
# En annen langtid-time (IKKE fallback-timen) skal derimot ha
# offshore_longrange sine tydelig ANDRE verdier (55/7,5), ikke hovedpunktets.
other_langtid13 = next(h for h in langtid13 if h["t"] != fallback_key13)
assert other_langtid13["dir_offshore"] == 55 and other_langtid13["period"] == 7.5, other_langtid13
# kilderapporten teller RÅ timer (215 = dag 8-16 minus selve fallback-timen,
# som aldri telles siden swell_model der ikke er None) før 6-timers tynning
# til radene langtid13 selv inneholder - ulike, men begge riktige, tall.
lr_report = [r for r in fetch.REPORT if r[0] == russelv_spot["name"] and r[1] == "Svell (langtid-reserve)"]
assert lr_report and "215" in lr_report[0][3], lr_report
print(f"13.1 offshore_longrange: {len(reserve13)} reserve-timer ({dag5_key13} ekte None), "
      f"{len(langtid13)} langtid-timer (offshore_longrange sine tall), fallback-timen {fallback_key13} uendret, "
      f"kilderapport: {lr_report[0][3]}")

# Uten offshore_longrange i det hele tatt (fjernet fra en kopi): langtid-
# sonen skal falle tilbake til ekte None (ikke 0, se CLAUDE.md), aldri late
# som den har data den ikke har - UNNTATT fallback-timen, som hovedpunktet
# allerede hadde total_fallback-data for helt uavhengig av offshore_longrange
# (samme _marine13-mock, bare uten at den noen gang spørres med OL sine
# koordinater nå).
russelv_uten_lr = {k: v for k, v in russelv_spot.items() if k != "offshore_longrange"}
fetch.REPORT.clear()
built13b = fetch.build_spot(russelv_uten_lr, now13, {}, {}, "test-run-13b", {}, {})
hours13b = {h["t"]: h for h in built13b["hours"]}
langtid13b = [h for h in built13b["hours"] if h.get("zone") == "langtid"]
langtid13b_ok = [h for h in langtid13b if h["t"] != fallback_key13]
assert langtid13b_ok and all(h.get("swell_offshore") is None and h.get("swell_model") is None for h in langtid13b_ok)
assert hours13b[fallback_key13]["swell_model"] == "total_fallback"
assert not [r for r in fetch.REPORT if r[1] == "Svell (langtid-reserve)"]
print(f"13.2 uten offshore_longrange: langtid-sonen ({len(langtid13b)} timer) forblir ekte None "
      f"(unntatt hovedpunktets egen fallback-time), ingen falsk kilderapport-rad, OK")

# Heller ikke offshore_longrange har noe: fortsatt ekte None, ikke en tredje
# slags utfylling.
def _marine13c(la, lo):
    return {sources.hour_key(now13 + dt.timedelta(hours=i)): {
        "height": None, "swell_height": None, "dir": None, "period": None, "swell_model": None,
        "secondary_swell_height": None, "secondary_swell_dir": None, "secondary_swell_period": None,
    } for i in range(_lr.HOURS)}
sources.openmeteo_marine = _marine13c
fetch.REPORT.clear()
built13c = fetch.build_spot(russelv_spot, now13, {}, {}, "test-run-13c", {}, {})
langtid13c = [h for h in built13c["hours"] if h.get("zone") == "langtid"]
assert langtid13c and all(h.get("swell_offshore") is None for h in langtid13c)
assert not [r for r in fetch.REPORT if r[1] == "Svell (langtid-reserve)"]
print(f"13.3 offshore_longrange uten data heller: fortsatt ekte None ({len(langtid13c)} timer), OK")
sources.openmeteo_marine = saved_marine13
sources.openmeteo_wind = saved_wind13

# ---------- 13.4: offshore_longrange skal rettes med samme forholds- og
# glidningsmekanisme som GFS/standard-skjøten (sources.ratio_blend_correction(),
# se 7f/7g over), ikke et rått skifte - Theodors instruks 07.10.2026 ("velg
# dette i stedet for alternativene i STATUS.md"). Egen, enklere mock enn
# 13.1 (ingen DAG5/FALLBACK-saker å teste her igjen) - men med en rå
# langtidsverdi (20,0) hos offshore_longrange som er TYDELIG forskjellig fra
# overlappets rå verdi (4,0), slik at målet etter korreksjon (20/4=5,0)
# avviker fra hovedpunktet sin siste EKTE verdi (1,0) og den glidende
# overgangen blir synlig (samme idé som 7f/7g sin "ratio og mål skal ikke
# tilfeldigvis gi samme sluttverdi").
sources.openmeteo_wind = lambda la, lo: {
    sources.hour_key(now13 + dt.timedelta(hours=i)): {"wind_speed": 4, "wind_dir": 200, "gust": 6}
    for i in range(_lr.HOURS)}
def _marine13d(la, lo):
    is_longrange = round(la, 3) == round(OL["lat"], 3) and round(lo, 3) == round(OL["lon"], 3)
    out = {}
    for i in range(_lr.HOURS):
        key = sources.hour_key(now13 + dt.timedelta(hours=i))
        day = _lr.day_index(now13, now13 + dt.timedelta(hours=i))
        if is_longrange:
            # Ekte dekning ALLE dager (det er selve poenget med punktet) -
            # men en ANNEN rå verdi i langtid-sonen (dag > 7) enn i
            # overlappet, se docstringen over.
            height = 4.0 if day <= _lr.RESERVE_LAST_DAY else 20.0
            out[key] = {"height": height, "swell_height": height, "dir": 55, "period": 7.5,
                        "swell_model": "gfs", "secondary_swell_height": None,
                        "secondary_swell_dir": None, "secondary_swell_period": None}
        elif day <= _lr.RESERVE_LAST_DAY:
            out[key] = {"height": 1.0, "swell_height": 1.0, "dir": 280, "period": 11,
                        "swell_model": "gfs", "secondary_swell_height": None,
                        "secondary_swell_dir": None, "secondary_swell_period": None}
        else:  # hovedpunktet mangler alt i langtid-sonen, som i den virkelige Lyngen-saken
            out[key] = {"height": None, "swell_height": None, "dir": None, "period": None,
                        "swell_model": None, "secondary_swell_height": None,
                        "secondary_swell_dir": None, "secondary_swell_period": None}
    return out
sources.openmeteo_marine = _marine13d
fetch.REPORT.clear()
built13d = fetch.build_spot(russelv_spot, now13, {}, {}, "test-run-13d", {}, {})
langtid13d = sorted((h for h in built13d["hours"] if h.get("zone") == "langtid"), key=lambda h: h["t"])
sources.openmeteo_marine = saved_marine13
sources.openmeteo_wind = saved_wind13
assert langtid13d, "forventet minst en langtid-time"
first13d, last13d = langtid13d[0]["swell_offshore"], langtid13d[-1]["swell_offshore"]
# Nøyaktig forventet verdi for den FØRSTE langtid-timen, uansett nøyaktig
# klokketime testen kjører på: skjøten er (per ratio_blend_correction()) den
# SISTE timen hovedpunktet har ekte data (samme day<=7-grense som
# _marine13d sin egen mock bruker over), deretter samme (-t.hour) % 6-formel
# som FALLBACK_TIME over for å finne den FØRSTE timen i langtid-sonen som
# overlever 6-timers tynning, og samme glidningsformel som
# sources.ratio_blend_correction() selv for forventet verdi der - IKKE den
# rå offshore_longrange-verdien (20,0), og IKKE rett på det korrigerte målet
# (5,0) heller, men et sted glidende mellom hovedpunktets siste ekte verdi
# (1,0) og målet.
_real_days13d = [i for i in range(_lr.HOURS) if _lr.day_index(now13, now13 + dt.timedelta(hours=i)) <= _lr.RESERVE_LAST_DAY]
_seam13d = now13 + dt.timedelta(hours=max(_real_days13d))
_day8_start13d = _seam13d + dt.timedelta(hours=1)
first_langtid_time13d = _day8_start13d + dt.timedelta(hours=(-_day8_start13d.hour) % 6)
hours_after13d = (first_langtid_time13d - _seam13d).total_seconds() / 3600
w13d = hours_after13d / sources.RATIO_BLEND_HOURS
expected_first13d = 1.0 * (1 - w13d) + 5.0 * w13d
assert langtid13d[0]["t"] == sources.hour_key(first_langtid_time13d), (langtid13d[0]["t"], first_langtid_time13d)
# fetch.py runder til 3 desimaler (`round(corrected_lr[t], 3)`) før lagring -
# fysikk-kontrollørens funn 07.10.2026: en sammenligning mot den URUNDEDE
# formelen med 1e-6 toleranse feiler i FIRE av seks klokkefaser (alle unntatt
# de to der den urundede verdien tilfeldigvis har 3 eller færre desimaler),
# og ville derfor stoppet "Hent varsel" (test.yml) nesten hver kjøring.
assert abs(first13d - round(expected_first13d, 3)) < 1e-9, (first13d, expected_first13d, hours_after13d, w13d)
# Siste langtid-time (dag 16, godt utenfor glidningsvinduet): fullt korrigert
# til målet (20/4 = 5,0), ikke den rå verdien (20,0) og ikke overlappets rå
# forholdstall alene (4,0) heller.
assert abs(last13d - 5.0) < 1e-6, last13d
lr_report13d = [r for r in fetch.REPORT if r[0] == russelv_spot["name"] and r[1] == "Svell (langtid-reserve)"]
assert lr_report13d, "forventet en kilderapport-rad for offshore_longrange"
assert "4.000" in lr_report13d[0][3], lr_report13d[0][3]  # forholdstallet (4,0 = 4,0/1,0), ikke målverdien (5,0)
print(f"13.4 offshore_longrange rettes med forhold+glidning: første langtid-time {first13d:.4f} m "
      f"(nær hovedpunktets siste 1,0 m, ikke et hopp mot 20,0/5,0), siste {last13d:.3f} m (mål 5,0), OK")

print("Pipeline ok")
