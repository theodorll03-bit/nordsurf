"""Testlab for treffsikkerhet (skyøkt 07.10.2026, Theodors oppgave 1).

Mål: teste en idé ("variant") mot alle observasjoner og benchmarks FØR den
går inn i ratingen. Leser og rapporterer BARE - endrer aldri spots.json,
rating.py eller noe annet (oppgave 1e). All logikk som avviker fra dagens
rating lever her, som midlertidige omskrivinger av inndata eller
monkeypatch av enkeltfunksjoner i rating.py INNENFOR ett kall - rating.py
selv er urørt (en lokal økt jobber i fetcher/ samtidig, derfor ingen
endringer i eksisterende filer).

Kjør:  python fetcher/backtest.py            (alle varianter, skriver data/backtest/)
       python fetcher/backtest.py grunnlinje  (én variant)

Saker ("cases") - hvert tidspunkt vi har noe å måle mot:
  1. Faste observasjoner fra CLAUDE.md, med de rekonstruerte inndataene som
     test_rating.py bruker (ekte historiske tall fra forecast.json sin
     git-historikk / BarentsWatch-logger). Forventning: stjernegrense
     (minst/høyst), observert surfehøyde der den finnes.
  2. Loggene (type egen økt/observert) fra logs.json i det private repoet
     (sources.github_logs(), bare i GitHub Actions der LOGS_REPO/LOGS_TOKEN
     finnes). Inndataene er de loggen selv lagret på loggtidspunktet
     (forecastHeight/bwHeight/swellOffshore/dirOffshore/forecastPeriod/...)
     - vind og tidevann mangler i eldre logger, da brukes nøytrale verdier
     og saken merkes "delvis". Forventning: loggede stjerner og størrelse.
  3. Benchmarks: data/benchmarks.json - tall Theodor har lest av
     surf-forecast.com/Surfline (skjermbilder) for et tidspunkt: stjerner/
     rating, surfehøyde, energi. Inndataene hentes fra det NYE
     inndata-arkivet (data/backtest/inputs/, en kompakt kopi av hver kjørings
     forecast.json-timer, skrevet av workflowen) for samme time. Fila er
     tom til Theodor fyller den - formatet står i FORMAT_BENCHMARKS under.

Datakilder som leses: data/forecast_archive/ (stjerner/surfehøyde per
kjøring - til "treff innenfor én stjerne" for logger uten lagrede inndata),
data/bw_calibration.json (transfer-par, til effektiv transfer som i
fetch.py), data/exposure_baseline.json (eksponering, som fetch.py),
data/ww3/archive/ (WW3 4 km per spot/time, hentet av ww3_archive.py i
Actions - thredds er ikke nåbar fra skyøkten), data/wind_obs/ (ekte
vindmålinger, oppgave 2 - når de finnes).

Varianter (oppgave 1c):
  grunnlinje     dagens rating, uendret.
  ww3_svell      svell ute (høyde/retning/periode) fra WW3 sin svellpartisjon
                 (phs1/pdir1/ptp1) i stedet for GFS, OG uten surf_factor_prior
                 for Unstad (surf_factor 1,0 med mindre loggene har lært noe).
  energi_tp      energien regnes med TOPPperiode: WW3 sin ptp1 der den
                 finnes, ellers GFS-gjennomsnitt × 1,25. Bare energifaktoren
                 - surfehøyde-formelen bruker fortsatt gjennomsnittsperioden.
  ww3_begge      begge WW3-partisjonene (vindsjø 0 og svell 1) vurderes hver
                 for seg mot vindu og eksponering, beste stjerner teller.
  vind_korr      met.no-vinden justeres med feilen målt mot nærmeste
                 KystVær-stasjon i samme time (oppgave 2e) - bare der
                 data/wind_obs/ har en måling for spoten og timen.

Mål per variant (oppgave 1b): faste observasjoner som holder (n/N og hvilke
som ryker), gjennomsnittlig absolutt feil i surfehøyde mot observert
størrelse (m), treff innenfor én stjerne (andel), avvik mot surf-forecast/
Surfline-benchmarks (stjerner og meter) der de finnes, og hvor mange saker
varianten faktisk kunne evalueres på (en variant som trenger WW3-data for et
tidspunkt uten WW3-data hopper over saken - den telles som "ikke evaluert",
aldri som treff eller bom).
"""
import datetime as dt
import glob
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibrate  # noqa: E402
import exposure_learn  # noqa: E402
import fetch  # noqa: E402
import rating  # noqa: E402
from rating import rate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
EXPOSURE_BASELINE = ROOT / "data" / "exposure_baseline.json"
BW_CALIB = ROOT / "data" / "bw_calibration.json"
ARCHIVE_DIR = ROOT / "data" / "forecast_archive"
WW3_ARCHIVE_DIR = ROOT / "data" / "ww3" / "archive"
WIND_OBS_DIR = ROOT / "data" / "wind_obs"
INPUTS_DIR = ROOT / "data" / "backtest" / "inputs"
BENCHMARKS = ROOT / "data" / "benchmarks.json"
OUT_DIR = ROOT / "data" / "backtest"

SIZE_M = calibrate.SIZE_M
TP_FROM_MEAN = 1.25   # toppperiode ≈ 1,25 × gjennomsnittsperiode (Theodors tall, oppgave 1c)
SURF_TOL_M = 0.3      # "surfehøyde ca. X m" i en fast observasjon: ± så mye regnes som treff

FORMAT_BENCHMARKS = {
    "_format": "Liste av objekter. spot = id fra spots.json, t = UTC-time (YYYY-MM-DDTHH:00Z), source = 'surf-forecast' eller 'surfline', "
               "stars = deres rating omregnet til 0-5 (valgfritt), surf_height_m = deres surfehøyde/bølgehøyde på stranda (valgfritt), "
               "energy_kj = surf-forecast sin energi (valgfritt), note = fritekst. Inndataene for timen hentes fra data/backtest/inputs/.",
    "benchmarks": [],
}


# ---------------------------------------------------------------------------
# Spot-oppsett - samme kjede som fetch.build_spot(), uten nett
# ---------------------------------------------------------------------------

def load_spots():
    cfg = json.loads(SPOTS.read_text(encoding="utf-8"))
    return {s["id"]: s for s in cfg["spots"] if s.get("enabled")}


def prepare_spot(spot_id, spots, exposure_data, bw_calib, learned=None, use_prior=True, exposure_learned=None):
    """Spot-dict slik fetch.build_spot() ville satt den opp for en kjøring
    (eksponering del C, hindringsgeometri, del B lært eksponering/transfer,
    transfer fra BarentsWatch-par, surf_factor fra logger/prior), uten nett.
    use_prior=False dropper surf_factor_prior (variant ww3_svell).
    Speiler build_spot() steg for steg - glir de fra hverandre, er
    'grunnlinje' ikke lenger produksjonen (kontrollørens punkt 07.10.2026)."""
    spot = json.loads(json.dumps(spots[spot_id]))
    sm, raw, _ = fetch.resolve_exposure(spot, exposure_data, spot["name"])
    if sm is not None:
        spot["exposure_smoothed"], spot["exposure_raw"] = sm, raw
    d_km, w_km = fetch.resolve_obstacle_geometry(spot, exposure_data)
    if d_km is not None:
        spot["exposure_distance_km"] = d_km
    if w_km is not None:
        spot["exposure_width_km"] = w_km
    learned = learned or {}
    # del B (som i build_spot): lært eksponering per bøtte/periodegruppe, og
    # dens transfer - bare når geometrisk rå-eksponering finnes.
    pairs = (exposure_learned or {}).get(spot_id, [])
    transfer_lang = None
    if sm is not None and raw is not None:
        learned_lang, transfer_lang, ref_lang = exposure_learn.normalize_period_group(pairs, "lang", raw)
        learned_kort, transfer_kort, _ = exposure_learn.normalize_period_group(pairs, "kort", raw, borrow_from=(learned_lang, transfer_lang, ref_lang))
        if learned_lang:
            spot["exposure_smoothed_lang"] = exposure_learn.blend_curve(learned_lang, sm, exposure_learn.bucket_pair_counts(pairs, "lang"))
        if learned_kort:
            spot["exposure_smoothed_kort"] = exposure_learn.blend_curve(learned_kort, sm, exposure_learn.bucket_pair_counts(pairs, "kort"))
    if learned.get("transfer"):
        transfer, transfer_source = learned["transfer"], "logs"
    elif transfer_lang is not None:
        transfer, transfer_source = round(min(1.2, max(0.05, transfer_lang)), 2), "eksponering"
    else:
        transfer, transfer_source = calibrate.effective_transfer(spot, learned, bw_calib.get(spot_id, []))
    spot["transfer"], spot["transfer_source"] = transfer, transfer_source
    if learned.get("surf_factor") is not None:
        spot["surf_factor"], spot["surf_factor_source"] = learned["surf_factor"], "logs"
    elif use_prior and spot.get("surf_factor_prior") is not None:
        spot["surf_factor"] = round(min(rating.SURF_FACTOR_MAX, max(rating.SURF_FACTOR_MIN, spot["surf_factor_prior"])), 2)
        spot["surf_factor_source"] = "prior"
    else:
        spot["surf_factor"], spot["surf_factor_source"] = rating.SURF_FACTOR_DEFAULT, "standard"
    return spot


# ---------------------------------------------------------------------------
# Saker
# ---------------------------------------------------------------------------

def fixed_cases():
    """De faste observasjonene i CLAUDE.md, med samme rekonstruerte inndata
    som test_rating.py (ekte historiske tall). Forventninger slik CLAUDE.md
    formulerer dem."""
    U_off = 151  # midt i Unstad sin offshore_wind [70,232] - samme som test 16.1
    cases = [
        dict(id="grotfjord_2409_metno", spot="grotfjord", t="2026-09-24T12:00Z", source="fast observasjon",
             hour={"height_spot_model": 1.9, "dir_offshore": 311, "turn": 32, "period": 11, "wind_speed": 3, "wind_dir": 180},
             expect={"stars_max": 0, "size_m": 0.0}, label="Grøtfjord 24.09 (met.no 1,9 m) - helt flatt"),
        dict(id="grotfjord_2409_bw", spot="grotfjord", t="2026-09-24T12:00Z", source="fast observasjon",
             hour={"bw_height": 0.3, "dir_offshore": 311, "turn": 32, "period": 11, "wind_speed": 3, "wind_dir": 180},
             expect={"stars_max": 0, "size_m": 0.0}, label="Grøtfjord 24.09 (BarentsWatch 0,3 m) - helt flatt"),
        dict(id="grotfjord_2409_windy", spot="grotfjord", t="2026-09-24T09:00Z", source="fast observasjon",
             hour={"height_spot_model": 1.7, "dir_offshore": 267, "turn": None, "period": 11, "wind_speed": 3, "wind_dir": 120},
             expect={"stars_max": 0, "size_m": 0.0}, label="Grøtfjord 24.09 kl. 09 (Windy 1,7 m fra 267°) - helt flatt"),
        dict(id="grotfjord_2509", spot="grotfjord", t="2026-09-25T12:00Z", source="fast observasjon",
             hour={"swell_offshore": 1.76, "dir_offshore": 313.3, "turn": 13.6, "period": 9.2, "wind_speed": 1.6, "wind_dir": 79},
             expect={"stars_max": 0, "size_m": 0.0}, label="Grøtfjord 25.09 (3° utenfor vinduet) - helt flatt", direction_bound=True),
        dict(id="grotfjord_2609", spot="grotfjord", t="2026-09-26T15:00Z", source="fast observasjon",
             hour={"bw_height": 0.33, "bw_dir": 294.0, "bw_period": 6.5, "swell_offshore": 2.18, "height_offshore": 5.0,
                   "dir_offshore": 272, "period": 15.6, "height_spot_model": 2.4, "turn": 27.0, "wind_speed": 3.4,
                   "wind_dir": 217.0, "gust": 5.3, "tide": {"level": 0.0, "rising": False, "state": "lav"}},
             expect={"stars_max": 0, "size_m": 0.0}, label="Grøtfjord 26.09 (BarentsWatch 0,33 m) - helt flatt"),
        dict(id="lenangsoyra_2609", spot="lenangsoyra", t="2026-09-26T12:00Z", source="fast observasjon",
             hour={"bw_height": 0.7, "bw_height_max": 1.4, "swell_offshore": 1.3, "dir_offshore": 277, "height_offshore": 2.7,
                   "period": 9, "bw_dir": 290, "wind_speed": 7, "wind_dir": 200, "gust": 10},
             expect={"stars_max": 1}, label="Lenangsøyra 26.09 - ikke surfbart (vindsjø på tvers)"),
        dict(id="unstad_2609", spot="unstad", t="2026-09-26T12:00Z", source="fast observasjon",
             hour={"bw_height": 0.9, "bw_dir": 294.8, "bw_period": 15.0, "dir_offshore": 300, "swell_offshore": 3.48,
                   "height_offshore": 3.48, "period": 15, "wind_speed": 3.0, "wind_dir": U_off},
             expect={"stars_min": 3, "surf_m": 2.4, "size_m": 2.4, "stars_obs": 4}, label="Unstad 26.09 kl. 14:45 - over hodet, 4 stjerner"),
    ]
    for t, h in (("06", {"bw_height": 0.8366666666666667, "bw_dir": 295.0, "bw_period": 9.8, "swell_offshore": 2.56, "height_offshore": 3.5, "dir_offshore": 255, "period": 9.45, "wind_speed": 7.8, "wind_dir": 227.0, "gust": 13.9}),
                 ("07", {"bw_height": 0.7533333333333334, "bw_dir": 295.0, "bw_period": 9.8, "swell_offshore": 2.54, "height_offshore": 3.5, "dir_offshore": 255, "period": 9.2, "wind_speed": 6.5, "wind_dir": 211.0, "gust": 12.9}),
                 ("08", {"bw_height": 0.67, "bw_dir": 295.0, "bw_period": 9.8, "swell_offshore": 2.72, "height_offshore": 3.4, "dir_offshore": 251, "period": 12.55, "wind_speed": 5.4, "wind_dir": 193.0, "gust": 10.8})):
        cases.append(dict(id=f"unstad_2709_{t}", spot="unstad", t=f"2026-09-27T{t}:00Z", source="fast observasjon", hour=h,
                          expect={"stars_min": 2, "size_m": 1.55, "stars_obs": 3}, label=f"Unstad 27.09 kl. {t} - brysthøyt til hodehøyt, ca. 3 stjerner"))
    for t, h in (("12", {"bw_height": 0.60, "bw_dir": 294.0, "bw_period": 11.5, "swell_offshore": 1.40, "height_offshore": 2.00, "dir_offshore": 249, "period": 12.0, "wind_speed": 7.5, "wind_dir": 145.0, "gust": 10.5}),
                 ("13", {"bw_height": 0.58, "bw_dir": 293.5, "bw_period": 11.8, "swell_offshore": 1.35, "height_offshore": 1.95, "dir_offshore": 248, "period": 12.1, "wind_speed": 7.8, "wind_dir": 148.0, "gust": 11.0}),
                 ("14", {"bw_height": 0.57, "bw_dir": 295.0, "bw_period": 12.0, "swell_offshore": 1.32, "height_offshore": 1.90, "dir_offshore": 250, "period": 12.0, "wind_speed": 8.0, "wind_dir": 150.0, "gust": 11.5}),
                 ("15", {"bw_height": 0.55, "bw_dir": 294.0, "bw_period": 11.6, "swell_offshore": 1.28, "height_offshore": 1.85, "dir_offshore": 249, "period": 11.8, "wind_speed": 7.6, "wind_dir": 147.0, "gust": 10.8})):
        cases.append(dict(id=f"unstad_2809_{t}", spot="unstad", t=f"2026-09-28T{t}:00Z", source="fast observasjon", hour=h,
                          expect={"stars_min": 3, "stars_obs": [4, 5]}, label=f"Unstad 28.09 kl. {t} - 'firing', 4-5 stjerner"))
    cases.append(dict(id="farstadsanden_338", spot="farstadsanden", t="2026-10-06T12:00Z", source="fast observasjon",
                      hour={"bw_height": 1.0, "bw_dir": 310, "bw_period": 10.0, "dir_offshore": 338, "swell_offshore": 1.5,
                            "height_offshore": 2.0, "period": 11.0, "wind_speed": 5.0, "wind_dir": 130.0},
                      expect={"stars_max": 1, "low_reason": "treffer_ikke"}, label="Farstadsanden, svell fra 338° over Nordneset - treffer ikke",
                      synthetic=True, direction_bound=True))
    return cases


def log_cases(logs):
    """Saker fra loggene (egne økter/observert). Inndata = det loggen lagret
    på loggtidspunktet. Vind/tidevann finnes ikke i loggene - settes nøytralt
    (ingen vindstraff) og saken merkes delvis."""
    out = []
    for l in logs:
        if l.get("stars") is None or not l.get("spot"):
            continue
        hour = {"bw_height": l.get("bwHeight"), "bw_dir": l.get("bwDir"), "bw_period": l.get("bwPeriod"),
                "swell_offshore": l.get("swellOffshore"), "dir_offshore": l.get("dirOffshore"),
                "period": l.get("forecastPeriod"), "height_spot_model": None if l.get("bwHeight") is not None or l.get("swellOffshore") is not None else l.get("forecastHeight"),
                "wind_speed": 2.0, "wind_dir": None}
        if l.get("tideState"):
            hour["tide"] = {"state": l["tideState"], "rising": None}
        t = l["t"].replace("Z", "+00:00")
        try:
            tt = dt.datetime.fromisoformat(t).astimezone(dt.timezone.utc)
        except ValueError:
            continue
        expect = {"stars_obs": l["stars"]}
        if l.get("size") in SIZE_M:
            expect["size_m"] = SIZE_M[l["size"]]
        out.append(dict(id=f"logg_{l.get('id', '')[:8]}", spot=l["spot"], t=tt.strftime("%Y-%m-%dT%H:00Z"), source=f"logg ({l.get('type', 'session')})",
                        hour=hour, expect=expect, partial=True, forecast_stars=l.get("forecastStars"),
                        label=f"Logg {l['spot']} {tt:%d.%m %H}: {l['stars']} stjerner{', ' + l['size'] if l.get('size') else ''}"))
    return out


def load_inputs_archive():
    """{spot: {t: hour_inputs}} fra data/backtest/inputs/*.json (skrevet av
    workflowen, kompakt kopi av forecast.json sine inndata per time)."""
    out = {}
    for f in sorted(glob.glob(str(INPUTS_DIR / "*.json"))):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        for sid, hours in d.get("spots", {}).items():
            out.setdefault(sid, {}).update(hours)
    return out


def benchmark_cases(inputs):
    if not BENCHMARKS.exists():
        return []
    data = json.loads(BENCHMARKS.read_text(encoding="utf-8"))
    out = []
    for b in data.get("benchmarks", []):
        hour = inputs.get(b.get("spot"), {}).get(b.get("t"))
        expect = {k: b[k] for k in ("stars", "surf_height_m", "energy_kj") if b.get(k) is not None}
        out.append(dict(id=f"bench_{b.get('source')}_{b.get('spot')}_{b.get('t')}", spot=b.get("spot"), t=b.get("t"),
                        source=f"benchmark ({b.get('source')})", hour=hour, expect=expect, benchmark=True,
                        label=f"{b.get('source')} {b.get('spot')} {b.get('t')}"))
    return out


# ---------------------------------------------------------------------------
# WW3 og vindmålinger (arkiv skrevet av workflowen)
# ---------------------------------------------------------------------------

def load_ww3_archive():
    """{spot: {t: {hs,dir,tp,phs0,pdir0,ptp0,phs1,pdir1,ptp1}}}. Siste
    kjøring per time vinner (filene sorteres etter navn = utstedelsestid)."""
    out = {}
    for f in sorted(glob.glob(str(WW3_ARCHIVE_DIR / "*.json"))):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        for sid, hours in d.get("spots", {}).items():
            out.setdefault(sid, {}).update(hours)
    return out


def load_wind_obs():
    """{spot: {t: {speed, dir, gust, station}}} fra data/wind_obs/*.json."""
    out = {}
    for f in sorted(glob.glob(str(WIND_OBS_DIR / "obs_*.json"))):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        for sid, hours in d.get("spots", {}).items():
            out.setdefault(sid, {}).update(hours)
    return out


# ---------------------------------------------------------------------------
# Varianter
# ---------------------------------------------------------------------------

@contextmanager
def patched(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def run_baseline(case, spot, ctx):
    return rate(dict(case["hour"]), spot)


def external_ok(case, needs_direction=False):
    """Kan saken bruke EKSTERNE data for timen (WW3, vindmålinger)? Nei for
    syntetiske saker (tenkte inndata, f.eks. Farstadsanden 338°) - ekte WW3
    for det klokkeslettet beskriver et annet hav. Nei også for retningsbundne
    saker når varianten bytter retningen (geometriregel for ÉN retning)."""
    if case.get("synthetic"):
        return False
    if needs_direction and case.get("direction_bound"):
        return False
    return True


def ww3_swell_for(case, ctx):
    """WW3-svellpartisjonen for timen, bare når ALLE tre feltene finnes
    (høyde, retning og periode fra samme modell - aldri None inn i ratingen)."""
    w = ctx["ww3"].get(case["spot"], {}).get(case["t"])
    if not w or any(w.get(k) is None for k in ("phs1", "pdir1", "ptp1")):
        return None
    return w


def run_ww3_swell(case, spot, ctx):
    if not external_ok(case, needs_direction=True):
        return None
    w = ww3_swell_for(case, ctx)
    if w is None:
        return None  # ingen (fullstendige) WW3-data for timen: ikke evaluert
    hour = dict(case["hour"])
    hour["swell_offshore"], hour["dir_offshore"], hour["period"] = w["phs1"], w["pdir1"], w["ptp1"]
    hour["height_offshore"] = w.get("hs", hour.get("height_offshore"))
    hour["swell_model"] = "ww3"
    return rate(hour, spot)


def run_energy_tp(case, spot, ctx):
    """Energifaktoren med toppperiode anslått som gjennomsnitt × 1,25
    (Theodors tall) - samme modell (GFS) for høyde og periode. Surfehøyde-
    formelen beholder gjennomsnittet - derfor en lokal omskriving av
    rating.energy_kj innenfor kallet, ikke av hour['period']. Faktoren er
    alltid over 1 (en toppperiode under gjennomsnittet er fysisk
    selvmotsigende - kontrollørens punkt 07.10.2026, da en tidligere versjon
    blandet WW3-periode med GFS-høyde)."""
    real = rating.energy_kj

    def energy_tp(height, period):
        return real(height, None if period is None else period * TP_FROM_MEAN)
    with patched(rating, "energy_kj", energy_tp):
        r = rate(dict(case["hour"]), spot)
    r["_energy_period_factor"] = TP_FROM_MEAN
    return r


def ww3_energy_patch(hour, w):
    """rating.energy_kj byttet ut så svellenergien regnes av WW3 sitt EGNE
    svell (phs1, ptp1 - toppperiode) og totalenergien av WW3 sin totale
    (hs, tp), begge fra samme modell. Alt annet i ratingen (surfehøyde,
    retning, eksponering) er urørt. Kallene skilles på argumentverdiene
    (rating sender hour sine egne tall): er svell- og totalhøyden ute
    IDENTISKE i inndataene (f.eks. Unstad 26.09, 3,48/3,48), får begge
    svellenergien - ufarlig, totalenergien vises bare og brukes aldri i
    ratingen."""
    real = rating.energy_kj
    swell_h, swell_t = hour.get("swell_offshore"), hour.get("period")
    total_h = hour.get("height_offshore")

    def energy_ww3(height, period):
        if height is not None and height == swell_h and period == swell_t:
            return real(w["phs1"], w["ptp1"])
        if height is not None and height == total_h and w.get("hs") is not None and w.get("tp") is not None:
            return real(w["hs"], w["tp"])
        return real(height, period)
    return patched(rating, "energy_kj", energy_ww3)


def run_energy_ww3(case, spot, ctx):
    """Energi (bare energien) fra WW3: svellenergi av phs1/ptp1, totalenergi
    av hs/tp. GFS beholdes for surfehøyde, retning og alt annet."""
    if not external_ok(case):
        return None
    w = ww3_swell_for(case, ctx)
    if w is None:
        return None
    hour = dict(case["hour"])
    with ww3_energy_patch(hour, w):
        r = rate(hour, spot)
    r["_energy_ww3"] = f"{w['phs1']} m/{w['ptp1']} s"
    return r


def run_ww3_both(case, spot, ctx):
    """Begge WW3-partisjonene hver for seg mot vindu/eksponering, beste
    stjerner teller (ved likhet: svellet, partisjon 1)."""
    if not external_ok(case, needs_direction=True):
        return None
    w = ww3_swell_for(case, ctx)   # krever hele svellpartisjonen (1)
    if w is None:
        return None
    best = None
    for p in ("1", "0"):
        if any(w.get(k + p) is None for k in ("phs", "pdir", "ptp")):
            continue
        hour = dict(case["hour"])
        hour["swell_offshore"], hour["dir_offshore"], hour["period"] = w["phs" + p], w["pdir" + p], w["ptp" + p]
        hour["height_offshore"] = w.get("hs", hour.get("height_offshore"))
        hour["swell_model"] = "ww3-" + ("svell" if p == "1" else "vindsjo")
        if p == "0":
            # Vindsjøen prøves mot vindu/eksponering/surfehøyde, men energi-
            # faktoren skal ALDRI lese vindsjø (CLAUDE.md), og svellandelen
            # (swell_share, styrer "blåst ut"/"kildene uenige") skal fortsatt
            # være ekte svell / total: begge bygger på phs1, ikke phs0.
            swell_hour = {"swell_offshore": w["phs1"], "height_offshore": w.get("hs")}
            real_share = rating.swell_share
            with ww3_energy_patch(hour, w), patched(rating, "swell_share", lambda h: real_share(swell_hour)):
                r = rate(hour, spot)
        else:
            r = rate(hour, spot)
        r["_partition"] = p
        if best is None or r["stars"] > best["stars"]:
            best = r
    return best


def run_wind_corr(case, spot, ctx):
    """met.no-vinden erstattet med målt vind fra nærmeste KystVær-stasjon
    for samme time (oppgave 2e: 'varselet justeres med feilen nå' - for et
    tilbakeblikk er feilen i timen selv den beste tilgjengelige)."""
    if not external_ok(case):
        return None
    o = ctx["wind"].get(case["spot"], {}).get(case["t"])
    if not o or o.get("speed") is None:
        return None
    hour = dict(case["hour"])
    hour["wind_speed"], hour["wind_dir"] = o["speed"], o.get("dir", hour.get("wind_dir"))
    if o.get("gust") is not None:
        hour["gust"] = o["gust"]
    r = rate(hour, spot)
    r["_wind_station"] = o.get("station")
    return r


VARIANTS = {
    "grunnlinje": dict(fn=run_baseline, use_prior=True, desc="Dagens rating, uendret"),
    "ww3_svell": dict(fn=run_ww3_swell, use_prior=False, desc="WW3-svell (phs1/pdir1/ptp1) i stedet for GFS, uten surf_factor_prior for Unstad"),
    "energi_tp": dict(fn=run_energy_tp, use_prior=True, desc=f"Energi med toppperiode anslått som gjennomsnitt × {TP_FROM_MEAN} (GFS for alt)"),
    "energi_ww3": dict(fn=run_energy_ww3, use_prior=True, desc="Energi fra WW3 (svell phs1/ptp1, total hs/tp - høyde og periode fra samme modell), ellers som i dag"),
    "ww3_begge": dict(fn=run_ww3_both, use_prior=False, desc="Begge WW3-svellene hver for seg mot vindu/eksponering, beste teller (uten prior)"),
    "vind_korr": dict(fn=run_wind_corr, use_prior=True, desc="met.no-vind erstattet med målt vind fra nærmeste KystVær-stasjon (oppgave 2e)"),
}


# ---------------------------------------------------------------------------
# Mål
# ---------------------------------------------------------------------------

def stars_interval(v):
    """Observerte stjerner som intervall: 4 → (4, 4); [4, 5] → (4, 5). En
    Instagram-observasjon '4-5 stjerner' er et intervall, ikke 4,5 - avstand
    måles til nærmeste ende (kontrollørens punkt 07.10.2026)."""
    if isinstance(v, (list, tuple)):
        return float(min(v)), float(max(v))
    return float(v), float(v)


def judge(case, r):
    """Returnerer dict med: holds (for faste observasjoner: True/False/None),
    surf_err (m eller None), hit1 (treff innenfor én stjerne mot observerte
    stjerner, True/False/None), bench_dstars/bench_dm (benchmark-avvik)."""
    e = case["expect"]
    out = {"stars": r["stars"], "surf": r.get("surf_height"), "low_reason": r.get("low_reason")}
    holds = None
    if "stars_min" in e or "stars_max" in e or "surf_m" in e or "low_reason" in e:
        holds = True
        if "stars_min" in e and r["stars"] < e["stars_min"]:
            holds = False
        if "stars_max" in e and r["stars"] > e["stars_max"]:
            holds = False
        if "surf_m" in e and (r.get("surf_height") is None or abs(r["surf_height"] - e["surf_m"]) > SURF_TOL_M):
            holds = False
        if "low_reason" in e and r.get("low_reason") != e["low_reason"]:
            holds = False
    out["holds"] = holds
    if "size_m" in e:
        # manglende surfehøyde er IKKE 0 (grunnregelen): feilen blir None og
        # saken holdes utenfor snittet
        out["surf_err"] = None if r.get("surf_height") is None else round(abs(r["surf_height"] - e["size_m"]), 2)
    if "stars_obs" in e:
        lo, hi = stars_interval(e["stars_obs"])
        bias = r["stars"] - hi if r["stars"] > hi else (r["stars"] - lo if r["stars"] < lo else 0)
        out["star_bias"] = bias
        out["hit1"] = abs(bias) <= 1.0
    if case.get("benchmark"):
        if "stars" in e:
            out["bench_dstars"] = r["stars"] - e["stars"]
        if "surf_height_m" in e and r.get("surf_height") is not None:
            out["bench_dm"] = round(r["surf_height"] - e["surf_height_m"], 2)
        if "energy_kj" in e and r.get("energy_swell_kj") is not None:
            out["bench_dkj"] = round(r["energy_swell_kj"] - e["energy_kj"])
    return out


def summarize(rows):
    fixed = [x for x in rows if x["j"].get("holds") is not None]
    held = [x for x in fixed if x["j"]["holds"]]
    errs = [x["j"]["surf_err"] for x in rows if x["j"].get("surf_err") is not None]
    hits = [x["j"]["hit1"] for x in rows if x["j"].get("hit1") is not None]
    biases = [x["j"]["star_bias"] for x in rows if x["j"].get("star_bias") is not None]
    bkj = [abs(x["j"]["bench_dkj"]) for x in rows if x["j"].get("bench_dkj") is not None]
    p0 = sum(1 for x in rows if (x.get("r") or {}).get("_partition") == "0")
    bstars = [abs(x["j"]["bench_dstars"]) for x in rows if x["j"].get("bench_dstars") is not None]
    bm = [abs(x["j"]["bench_dm"]) for x in rows if x["j"].get("bench_dm") is not None]
    return {
        "evaluated": len(rows),
        "fixed_hold": f"{len(held)}/{len(fixed)}" if fixed else "–",
        "fixed_failed": [x["case"]["id"] for x in fixed if not x["j"]["holds"]],
        "surf_mae": round(sum(errs) / len(errs), 2) if errs else None,
        "surf_n": len(errs),
        "hit1": f"{sum(hits)}/{len(hits)}" if hits else "–",
        "hit1_pct": round(100 * sum(hits) / len(hits)) if hits else None,
        "star_bias": round(sum(biases) / len(biases), 2) if biases else None,
        "star_bias_n": len(biases),
        "partition0_wins": p0,
        "bench_kj_mae": round(sum(bkj) / len(bkj)) if bkj else None,
        "bench_stars_mae": round(sum(bstars) / len(bstars), 2) if bstars else None,
        "bench_m_mae": round(sum(bm) / len(bm), 2) if bm else None,
        "bench_n": max(len(bstars), len(bm)),
    }


# ---------------------------------------------------------------------------
# Kjøring og rapport
# ---------------------------------------------------------------------------

def fmt(v):
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.2f}".replace(".", ",")
    return str(v)


def run(variant_names=None, logs=None):
    spots = load_spots()
    exposure_data = json.loads(EXPOSURE_BASELINE.read_text(encoding="utf-8")) if EXPOSURE_BASELINE.exists() else {}
    bw_calib = json.loads(BW_CALIB.read_text(encoding="utf-8")) if BW_CALIB.exists() else {}
    logs = logs if logs is not None else []
    learned = {sid: calibrate.learn(sid, logs) for sid in spots}
    inputs = load_inputs_archive()
    ctx = {"ww3": load_ww3_archive(), "wind": load_wind_obs()}
    cases = fixed_cases() + log_cases(logs) + benchmark_cases(inputs)
    cases = [c for c in cases if c["spot"] in spots and c.get("hour")]
    names = variant_names or list(VARIANTS)
    results = {}
    exposure_learned = json.loads(fetch.EXPOSURE_LEARNED.read_text(encoding="utf-8")) if fetch.EXPOSURE_LEARNED.exists() else {}
    for name in dict.fromkeys(["grunnlinje"] + list(names)):   # grunnlinja alltid, for "samme saker"-kolonnen
        v = VARIANTS[name]
        rows, skipped = [], 0
        spot_cache = {}
        for c in cases:
            if c["spot"] not in spot_cache:
                spot_cache[c["spot"]] = prepare_spot(c["spot"], spots, exposure_data, bw_calib, learned.get(c["spot"]), use_prior=v["use_prior"], exposure_learned=exposure_learned)
            r = v["fn"](c, spot_cache[c["spot"]], ctx)
            if r is None:
                skipped += 1
                continue
            rows.append({"case": c, "r": {k: r.get(k) for k in ("stars", "faded", "surf_height", "height", "height_source", "low_reason", "energy_swell_kj", "_energy_period_factor", "_energy_ww3", "_partition", "_wind_station")}, "j": judge(c, r)})
        results[name] = {"desc": v["desc"], "rows": rows, "skipped": skipped, "summary": summarize(rows)}
    # grunnlinja regnet på NØYAKTIG de sakene hver variant evaluerte - bare
    # det er en rettferdig sammenligning når variantene hopper over saker
    base_rows = {x["case"]["id"]: x for x in results["grunnlinje"]["rows"]}
    for name, res in results.items():
        ids = {x["case"]["id"] for x in res["rows"]}
        res["baseline_same"] = summarize([base_rows[i] for i in ids if i in base_rows])
    if "grunnlinje" not in names:
        results = {k: v for k, v in results.items() if k in names}
    return cases, results, ctx


def report(cases, results, ctx, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    L = [f"# Testlab for treffsikkerhet - {now:%Y-%m-%d %H:%M} UTC", "",
         f"Saker: {len(cases)} ({sum(1 for c in cases if c['source']=='fast observasjon')} faste observasjoner, "
         f"{sum(1 for c in cases if c['source'].startswith('logg'))} logger, {sum(1 for c in cases if c.get('benchmark'))} benchmarks). "
         f"WW3-arkiv: {sum(len(v) for v in ctx['ww3'].values())} spot-timer. Vindmålinger: {sum(len(v) for v in ctx['wind'].values())} spot-timer.", ""]
    L += ["## Samlet", "", "| Variant | Evaluert | Faste obs. holder | Surfehøyde-feil (m, snitt) | Treff ±1 stjerne | Stjerneavvik (snitt, fortegn) | Benchmark-avvik (stjerner / m / kJ) | Ikke evaluert | Grunnlinje på SAMME saker (holder / feil m / treff ±1) |", "|---|---|---|---|---|---|---|---|---|"]
    for name, res in results.items():
        s, b = res["summary"], res.get("baseline_same") or {}
        p0 = f" (partisjon 0 vant {s['partition0_wins']})" if s.get("partition0_wins") else ""
        L.append(f"| {name} | {s['evaluated']}{p0} | {s['fixed_hold']}{' (ryker: ' + ', '.join(s['fixed_failed']) + ')' if s['fixed_failed'] else ''} | "
                 f"{fmt(s['surf_mae'])} (n={s['surf_n']}) | {s['hit1']}{' (' + str(s['hit1_pct']) + ' %)' if s['hit1_pct'] is not None else ''} | "
                 f"{('+' if (s['star_bias'] or 0) > 0 else '') + fmt(s['star_bias'])} (n={s['star_bias_n']}) | "
                 f"{fmt(s['bench_stars_mae'])} / {fmt(s['bench_m_mae'])} / {fmt(s['bench_kj_mae'])} (n={s['bench_n']}) | {res['skipped']} | "
                 f"{b.get('fixed_hold', '–')} / {fmt(b.get('surf_mae'))} / {b.get('hit1', '–')} |")
    L.append("")
    for name, res in results.items():
        L += [f"## {name} - {res['desc']}", "", "| Sak | Forventet | Stjerner | Surfehøyde | Ord | Holder | Feil (m) | ±1 |", "|---|---|---|---|---|---|---|---|"]
        for x in res["rows"]:
            c, r, j = x["case"], x["r"], x["j"]
            e = c["expect"]
            exp = ", ".join(f"{k}={v}" for k, v in e.items())
            extra = ""
            if r.get("_energy_period_factor"):
                extra = f" (Tp-faktor {r['_energy_period_factor']})"
            if r.get("_energy_ww3"):
                extra = f" (WW3-energi av {r['_energy_ww3']})"
            if r.get("_partition"):
                extra = f" (partisjon {r['_partition']})"
            if r.get("_wind_station"):
                extra = f" ({r['_wind_station']})"
            L.append(f"| {c['label']}{' [delvis]' if c.get('partial') else ''} | {exp} | {r['stars']}{extra} | {fmt(r['surf_height'])} | {r.get('low_reason') or ''} | "
                     f"{'ja' if j.get('holds') else ('NEI' if j.get('holds') is False else '–')} | {fmt(j.get('surf_err'))} | "
                     f"{'ja' if j.get('hit1') else ('nei' if j.get('hit1') is False else '–')} |")
        L.append("")
    L += ["## Merknader", "",
          "- Faste observasjoner har inndata rekonstruert fra ekte kjøringer (samme som test_rating.py). Logger bruker inndataene loggen selv lagret (uten vind/tidevann - merket [delvis]).",
          "- Varianter som trenger WW3 eller vindmålinger for en time uten data hopper over saken (telles under 'Ikke evaluert'). Sammenlign bare varianter på samme saker.",
          "- Saker merket retningsbundet (Grøtfjord 25.09 '3° utenfor vinduet', Farstadsanden 338° over Nordneset) tester en geometriregel for ÉN bestemt inndata-retning; variantene som bytter retningen mot WW3 hopper over dem (en annen modells retning gjør forventningen meningsløs, ikke feil). Syntetiske saker (tenkte inndata, Farstadsanden 338°) hoppes over av ALLE varianter som henter eksterne data for klokkeslettet.",
          "- ww3_svell/ww3_begge tester TRE ting samtidig: WW3 i stedet for GFS, WW3 sin TOPPPERIODE (ptp1) der ratingen ellers bruker gjennomsnittsperioden (Komar og Gaughan, period_score, p(T)), og uten surf_factor_prior. Transfer-kalibreringen (reservemodellen) er lært mot GFS-skalaen og brukes urørt på WW3-svellet.",
          "- Observerte stjerner kan være et intervall ('4-5'): treff ±1 og stjerneavviket måles mot nærmeste ende. Stjerneavviket har fortegn (negativt = appen rater lavere enn observert).",
          "- Kolonnen 'Grunnlinje på SAMME saker' er dagens rating regnet på nøyaktig de sakene varianten evaluerte - sammenlign den, ikke grunnlinjeraden øverst, når varianten hopper over saker.",
          "- Dekning: WW3-arkivet ('fersk', 48 t) og inndata-bildet (72 t) tas bare ukentlig - logger/benchmarks i dagene imellom får 'ikke evaluert' i variantene som trenger dem.",
          "- Benchmarks: fyll data/benchmarks.json (format i fila) med tall fra surf-forecast/Surfline; inndataene for timen hentes fra data/backtest/inputs/ (skrives av workflowen hver uke og kan kjøres oftere).",
          "- Testlaben endrer aldri spots.json eller ratingen.", ""]
    return "\n".join(L)


def write_outputs(text, cases, results, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{now:%Y-%m-%d}.md").write_text(text, encoding="utf-8")
    (OUT_DIR / "latest.md").write_text(text, encoding="utf-8")
    hist_path = OUT_DIR / "history.json"
    hist = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []
    hist.append({"run": now.isoformat(), "cases": len(cases), **{n: r["summary"] for n, r in results.items()}})
    hist_path.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
    if not BENCHMARKS.exists():
        BENCHMARKS.write_text(json.dumps(FORMAT_BENCHMARKS, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    names = [a for a in sys.argv[1:] if a in VARIANTS] or None
    logs = []
    if os.environ.get("LOGS_REPO") and os.environ.get("LOGS_TOKEN"):
        try:
            import sources
            logs = sources.github_logs()
        except Exception as e:
            print(f"Logger kunne ikke hentes: {e}")
    cases, results, ctx = run(names, logs)
    text = report(cases, results, ctx)
    print(text)
    write_outputs(text, cases, results)


if __name__ == "__main__":
    main()
