"""Henter varsel for alle spots og skriver docs/data/forecast.json.

Kjør lokalt:  python fetcher/fetch.py
Kjøres automatisk hver tredje time av GitHub Actions.
"""

import os
import json
import datetime as dt
from pathlib import Path

import sources
import calibrate
import exposure_learn
import notify
import sun
import tide as tidemod
from exposure import spot_checksum
from rating import angle_diff, directness, rate, SURF_FACTOR_DEFAULT

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
OUT = ROOT / "docs" / "data" / "forecast.json"
BW_CALIB = ROOT / "data" / "bw_calibration.json"
EXPOSURE_BASELINE = ROOT / "data" / "exposure_baseline.json"
EXPOSURE_LEARNED = ROOT / "data" / "exposure.json"
HOURS_AHEAD_MAX = 120  # 5 døgn, men stopper ved kortest tilgjengelige kilde
REPORT = []  # kilderapport, vises i Actions
# Advarsler om at retningskonvensjonen mot BarentsWatch kan ha blitt feil
# igjen (se build_spot()) - vises ØVERST i kilderapporten, ikke i selve
# tabellen, og endrer aldri ratingen automatisk.
CONVENTION_WARNINGS = []


def pick(*vals):
    return next((v for v in vals if v is not None), None)


def _hours_available(source_dict, now):
    """Timer fra now til siste tilgjengelige tidspunkt i kilden. 0 hvis tom."""
    if not source_dict:
        return 0
    last = sources.parse_iso(max(source_dict))
    return max(0, int((last - now).total_seconds() // 3600) + 1)


def resolve_exposure(spot, exposure_data, name):
    """Glattet OG rå eksponering (del C) for spoten, hvis den finnes og
    sjekksummen stemmer med spots.json sitt NÅVÆRENDE innhold - ellers
    (None, None) (rating.py sine exposure()/raw_exposure_zero() faller da
    tilbake til directness()/vindu-grensa). Rådataene brukes til å avgjøre
    NÅR reservemodellen skal dempe Hb en ekstra gang (se rating.py sin
    raw_exposure_zero(), Theodors rettelse 27.09.2026 tredje runde).
    Returnerer (smoothed_eller_None, raw_eller_None, advarsel_eller_None)."""
    entry = exposure_data.get(spot["id"])
    if entry is None:
        return None, None, (f"{name}: ingen eksponeringsdata bygget ennå (kjør fetcher/exposure_baseline.py "
                             f"manuelt) - bruker vindu og skyggekurve som reserve")
    if entry.get("checksum") != spot_checksum(spot):
        return None, None, (f"{name}: eksponeringens sjekksum stemmer ikke med spots.json - facing, "
                             f"svellvindu eller koordinater er endret siden siste kjøring av "
                             f"fetcher/exposure_baseline.py. Bruker vindu og skyggekurve som reserve")
    return entry["smoothed"], entry["raw"], None


def convention_warning(hours, spot, name):
    """Sikring på SPOTNIVÅ mot at BarentsWatch-retningskonvensjonen
    ("mot"->"fra", +180 i sources.py) skulle bli feil igjen: blant timene
    med ekte svell ute mot vinduet (swell_offshore over 0,5 m OG directness
    over 0,5 - "eksponering", se rating.directness), sjekk hvor mange som
    har BarentsWatch-retning over 150 grader fra facing (går ut fra land,
    se rating.spot_direction_factor). Mer enn halvparten: en fungerende
    konvensjon skal ikke gi det mønsteret når det samtidig ER ekte svell på
    vei inn - returner en varselstekst. Endrer ALDRI ratingen selv."""
    relevant = [
        h for h in hours
        if h.get("swell_offshore") is not None and h["swell_offshore"] > 0.5
        and directness(h.get("dir_offshore"), spot) > 0.5
        and h.get("bw_dir") is not None
    ]
    offshore = [h for h in relevant if h.get("spot_direction_diff") is not None
                and h["spot_direction_diff"] > 150]
    if relevant and len(offshore) > len(relevant) / 2:
        return (f"Mulig feil i BarentsWatch-retningskonvensjonen for {name}: "
                f"{len(offshore)} av {len(relevant)} timer med ekte svell ute mot vinduet "
                f"har BarentsWatch-retning over 150 grader fra facing ved spoten. "
                f"Ratingen er ikke endret automatisk.")
    return None


def safe(spot, label, fn, *args, default=None):
    try:
        res = fn(*args)
        n = len(res) if hasattr(res, "__len__") else 1
        REPORT.append((spot, label, "ok" if n else "tom", n))
        return res
    except Exception as e:
        REPORT.append((spot, label, "feil", str(e)[:120]))
        print(f"  {label} feilet: {e}")
        return {} if default is None else default


def build_spot(spot, now, learned, bw_calib, run_id, exposure_data, exposure_learned_data):
    name = spot["name"]
    print(name)
    # Kopi FØR noe muteres under (exposure_smoothed/exposure_raw/transfer/
    # surf_factor osv. settes rett på denne dicten) - ellers ville config
    # sin egen spots.json-liste blitt endret i minnet, ikke bare den lokale
    # kopien som brukes til å bygge dette svaret.
    spot = dict(spot)
    s, o = spot["spot"], spot["offshore"]
    ocean_spot = safe(name, "met.no hav (spot)", sources.metno_ocean, s["lat"], s["lon"])
    ocean_off = safe(name, "met.no hav (ute)", sources.metno_ocean, o["lat"], o["lon"])
    marine = safe(name, "Open-Meteo svell (ute)", sources.openmeteo_marine, o["lat"], o["lon"])
    weather = safe(name, "met.no vind", sources.metno_weather, s["lat"], s["lon"])
    swell_values = [v.get("swell_height") for v in marine.values() if v.get("swell_height") is not None]
    if marine and not swell_values:
        REPORT.append((name, "Open-Meteo svellhøyde", "tom", "havpunktet gir ingen svellhøyde, bruker met.no"))

    # barentswatch_point (ca 250 m ut) er punktet ratingen og kalibreringen
    # bruker. barentswatch_point_near (ca 150 m ut, det opprinnelige punktet)
    # hentes i tillegg og lagres bare til sammenligning (bw_height_near) - se
    # spots.json sin _info. Gir 250 m-punktet ingen data, brukes 150 m-punktet
    # i ratingen for dette spotet også, og det logges i kilderapporten.
    bw_raw = {}
    if spot.get("barentswatch_point"):
        p = spot["barentswatch_point"]
        bw_raw = safe(name, "BarentsWatch (250 m)", sources.barentswatch_point, p["lat"], p["lon"])
    bw_raw_near = {}
    if spot.get("barentswatch_point_near"):
        pn = spot["barentswatch_point_near"]
        bw_raw_near = safe(name, "BarentsWatch (150 m)", sources.barentswatch_point, pn["lat"], pn["lon"])

    bw_fallback = not bw_raw and bool(bw_raw_near)
    bw_used = bw_raw_near if bw_fallback else bw_raw
    if bw_fallback:
        REPORT.append((name, "BarentsWatch 250 m", "feil", "ingen data - bruker 150 m-punktet i ratingen for dette spotet"))

    bw_hourly = sources.bw_interpolate(bw_used)
    bw_hourly_near = sources.bw_interpolate(bw_raw_near)
    bw_until = max(bw_used) if bw_used else None
    if bw_used:
        REPORT.append((name, "BarentsWatch periode", "ok", f"{min(bw_used)} -> {max(bw_used)}, bw_until {bw_until}"))

    horizon = min(HOURS_AHEAD_MAX, _hours_available(marine, now), _hours_available(weather, now))
    REPORT.append((name, "Horisont", "ok", f"{horizon} timer"))

    tides = safe(name, "Kartverket tidevann", sources.kartverket_tide, s["lat"], s["lon"],
                 now - dt.timedelta(hours=12), now + dt.timedelta(hours=HOURS_AHEAD_MAX + 12), default=[])

    # 27.09.2026, ROADMAP oppgave 2: glattet eksponering (del C) erstatter
    # vindu+skyggekurve for reservemodellen (se rating.exposure()) - men bare
    # når sjekksummen stemmer med spots.json sitt NÅVÆRENDE innhold. Endres
    # facing/vindu/koordinater uten å bygge exposure_baseline.py på nytt,
    # faller spoten tilbake til directness() (varslet i kilderapporten) i
    # stedet for å bruke utdaterte eksponeringstall stille. Gjøres FØR
    # transfer under, siden del B sin lærte transfer (om den finnes) trenger
    # denne geometrien (referansebøttene) for å normalisere seg selv.
    exposure_smoothed, exposure_raw, exposure_warning = resolve_exposure(spot, exposure_data, name)
    if exposure_smoothed is not None:
        spot["exposure_smoothed"] = exposure_smoothed
        spot["exposure_raw"] = exposure_raw
    if exposure_warning:
        REPORT.append((name, "Eksponering (del C)", "feil", exposure_warning))

    # 27.09.2026, ROADMAP oppgave 4 (del B): eksponering LÆRT fra BarentsWatch,
    # per 10-graders bøtte og periodegruppe (kort/lang) - blandet med den
    # geometriske kurven (se exposure_learn.py sin modul-docstring for hele
    # metoden). Samme unngå-sirkularitet-mønster som transfer over: bruker
    # PAR FRA FØR denne kjøringen (nye par fra timene som bygges under kan
    # ikke brukes her - de trenger selv rate() sitt resultat, se lenger ned).
    # Krever gyldig geometrisk rå-eksponering (referansebøttene, se
    # exposure_learn.geometric_reference_buckets()) - ingen normalisering
    # uten den.
    exposure_pairs_existing = exposure_learned_data.get(spot["id"], [])
    learned_lang = learned_kort = {}
    counts_lang = counts_kort = {}
    transfer_lang = transfer_kort = None
    if exposure_raw is not None:
        learned_lang, transfer_lang, ref_lang = exposure_learn.normalize_period_group(
            exposure_pairs_existing, "lang", exposure_raw)
        learned_kort, transfer_kort, ref_kort = exposure_learn.normalize_period_group(
            exposure_pairs_existing, "kort", exposure_raw, borrow_from=(learned_lang, transfer_lang, ref_lang))
        counts_lang = exposure_learn.bucket_pair_counts(exposure_pairs_existing, "lang")
        counts_kort = exposure_learn.bucket_pair_counts(exposure_pairs_existing, "kort")
        if learned_lang:
            spot["exposure_smoothed_lang"] = exposure_learn.blend_curve(learned_lang, exposure_smoothed, counts_lang)
        if learned_kort:
            spot["exposure_smoothed_kort"] = exposure_learn.blend_curve(learned_kort, exposure_smoothed, counts_kort)

    # Effektiv transfer for reserven brukes med kalibreringshistorikk FRA FØR
    # denne kjøringen - nye par fra akkurat nå legges til historikken lenger
    # ned og gjelder først fra neste kjøring (unngår sirkularitet: parene
    # bygges av bw_height/svell/directness og trenger ikke selve transferen).
    # 27.09.2026, ROADMAP oppgave 4: del B sin transfer (medianforholdet i
    # referansebøttene den lærte kurven normaliseres mot, se
    # exposure_learn.normalize_period_group()) er mer presis enn den gamle,
    # retningsløse bw_transfer() - brukes derfor FØR den når den finnes.
    # Bruker alltid "lang" periodegruppe her (samme antagelse som den
    # geometriske modellen sin bølgelengde, ~12 s) - "kort" sin transfer er
    # uansett lik "lang" sin med mindre "lang" ikke er lært ennå.
    bw_pairs_existing = bw_calib.get(spot["id"], [])
    if learned.get("transfer"):
        transfer_value, transfer_source = learned["transfer"], "logs"
    elif transfer_lang is not None:
        transfer_value, transfer_source = round(min(1.2, max(0.05, transfer_lang)), 2), "eksponering"
    else:
        transfer_value, transfer_source = calibrate.effective_transfer(spot, learned, bw_pairs_existing)
    # surf_factor har bare én kilde (loggene/observasjonene dine) - ingen
    # rekkefølge å velge mellom som for transfer, bare standard 1,0 til det
    # finnes nok logger (se calibrate.learn()).
    surf_factor_value = learned.get("surf_factor", SURF_FACTOR_DEFAULT)
    surf_factor_source = "logs" if learned.get("surf_factor") is not None else "standard"
    spot["transfer"], spot["surf_factor"] = transfer_value, surf_factor_value

    hours = []
    for i in range(horizon):
        t = now + dt.timedelta(hours=i)
        k = sources.hour_key(t)
        sp, off, mar, w = ocean_spot.get(k), ocean_off.get(k), marine.get(k), weather.get(k)
        if not sp and not mar:
            continue
        # Svellretningen skal ALDRI komme fra met.no sin samlede sjøtilstand
        # (svell 1, svell 2 og vindsjø blandet) - bare fra Open-Meteo sitt
        # svellfelt (GFS Wave, med standardmodellen som reserve, se sources.py).
        # met.no brukes fortsatt til reservehøyden (metno_korrigert under) og
        # til dreiningsdiagnosen (turn), via dir_spot.
        dir_off = (mar or {}).get("dir")
        dir_spot = (sp or {}).get("dir")
        turn = angle_diff(dir_off, dir_spot) if dir_off is not None and dir_spot is not None else None
        light = sun.light(s["lat"], s["lon"], t)
        bwk = bw_hourly.get(k)
        bwk_near = bw_hourly_near.get(k)
        hour = {
            "t": k,
            "height_offshore": pick((off or {}).get("height"), (mar or {}).get("height")),
            "height_spot_model": (sp or {}).get("height"),
            "swell_offshore": (mar or {}).get("swell_height"),
            "swell_model": (mar or {}).get("swell_model"),
            "secondary_swell_height": (mar or {}).get("secondary_swell_height"),
            "secondary_swell_dir": (mar or {}).get("secondary_swell_dir"),
            "secondary_swell_period": (mar or {}).get("secondary_swell_period"),
            "bw_height": bwk.get("height") if bwk else None,
            "bw_dir": bwk.get("dir") if bwk else None,
            "bw_period": bwk.get("period") if bwk else None,
            "bw_interpolated": bwk.get("interpolated") if bwk else None,
            # Maks bølgehøyde fra BarentsWatch - bare til visning, se
            # sources.barentswatch_point sin docstring for hvorfor.
            "bw_height_max": bwk.get("max_height") if bwk else None,
            # 150 m-punktet, bare til sammenligning (Logger-fanen). Brukes
            # ALDRI i ratingen eller kalibreringen - bw_height (over) er det.
            "bw_height_near": bwk_near.get("height") if bwk_near else None,
            "dir_offshore": dir_off,
            "dir_spot": dir_spot,
            "turn": turn,
            "period": (mar or {}).get("period"),
            "water_temp": (sp or {}).get("water_temp"),
            **(w or {}),
            "light": light,
            "daylight": light != "mørkt",  # brukbart lys, også skumring i mørketida
            "tide": tidemod.state_at(tides, t + dt.timedelta(minutes=30)) if tides else None,
        }
        hour.update(rate(hour, spot))
        hours.append(hour)

    if not hours and horizon:
        # Kildene rapporterte data (horisont > 0), men ingen enkelttime hadde
        # verken met.no- eller Open-Meteo-data på forventet klokkeslett - tyder
        # på at klokkeslettene i kildene ikke stemmer med "now" som ventet.
        # Logg nok til å diagnostisere uten en ny runde med skjermbilder.
        expected_k = sources.hour_key(now)
        REPORT.append((name, "Ingen timer bygget", "feil",
                       f"horisont {horizon}t men 0 bygget. Ventet nøkkel {expected_k}. "
                       f"met.no hav (spot): {min(ocean_spot) if ocean_spot else '-'} .. {max(ocean_spot) if ocean_spot else '-'} ({len(ocean_spot)}t). "
                       f"Open-Meteo: {min(marine) if marine else '-'} .. {max(marine) if marine else '-'} ({len(marine)}t)."))

    gfs_hours = sum(1 for h in hours if h.get("swell_model") == "gfs")
    std_hours = sum(1 for h in hours if h.get("swell_model") == "standard")
    none_hours = sum(1 for h in hours if h.get("swell_model") is None)
    REPORT.append((name, "Svellmodell", "ok", f"GFS Wave {gfs_hours}t, standardmodell (reserve) {std_hours}t, ingen svelldata {none_hours}t"))

    # 27.09.2026, andre runde: BarentsWatch-retning over 150 grader fra facing
    # betyr nå bare at bølgene ved punktet faktisk går ut fra land (ordinær
    # straff, retningsfaktor 0 - se rating.spot_direction_factor), IKKE et
    # feiltegn i seg selv. MEN hvis konvensjonen ("mot"->"fra", +180) skulle
    # bli feil igjen en gang i fremtiden, ville det vise seg nettopp som en
    # bølge av slike >150-timer akkurat når det samtidig ER ekte svell ute
    # mot vinduet - det skal en fungerende konvensjon aldri gi mye av.
    # Sikring på SPOTNIVÅ (ikke per time), endrer ALDRI ratingen automatisk.
    warning = convention_warning(hours, spot, name)
    if warning:
        CONVENTION_WARNINGS.append(warning)

    new_pairs = calibrate.bw_pairs_for_run(hours, run_id)
    merged_pairs = calibrate.merge_bw_pairs(bw_pairs_existing, new_pairs, now)
    bw_calib[spot["id"]] = merged_pairs
    bw_days = len({p["t"][:10] for p in merged_pairs})

    # Del B: nye eksponeringspar bygges FRA hours (trenger swell_share,
    # sources_disagree osv. - rate() sitt resultat), og lagres for BRUK NESTE
    # KJØRING (se kommentaren over exposure_pairs_existing lenger opp).
    new_exposure_pairs = exposure_learn.exposure_pairs_for_run(hours, run_id)
    merged_exposure_pairs = exposure_learn.merge_pairs(exposure_pairs_existing, new_exposure_pairs, now)
    exposure_learned_data[spot["id"]] = merged_exposure_pairs
    exposure_override_suggestions = exposure_learn.override_removal_suggestions(
        spot.get("exposure_override"), learned_kort, learned_lang)

    # exposure_smoothed/exposure_raw/exposure_smoothed_lang/exposure_smoothed_kort
    # er interne tall (én per grad) bare til bruk i rate() over - ikke noe
    # appen trenger å vise, ekskludert fra utdata.
    _internal_keys = {"exposure_smoothed", "exposure_raw", "exposure_smoothed_lang", "exposure_smoothed_kort"}
    public = {k: v for k, v in spot.items() if not k.startswith("_") and k not in _internal_keys}
    light_days = sun.light_days(s["lat"], s["lon"], now)
    calibration = {
        **learned,
        "transfer_logs": learned.get("transfer"),
        "transfer_bw": calibrate.bw_transfer(merged_pairs),
        "bw_pairs": len(merged_pairs),
        "bw_days": bw_days,
        "transfer_used": transfer_value,
        "transfer_source": transfer_source,
        "surf_factor_used": surf_factor_value,
        "surf_factor_source": surf_factor_source,
        # Del B, ROADMAP oppgave 4 - hvor mye eksponering som er lært akkurat
        # nå (par fra FØR denne kjøringen, se over), til Logger-fanen og
        # STATUS.md.
        "exposure_pairs": len(merged_exposure_pairs),
        "exposure_buckets_learned_lang": len(learned_lang),
        "exposure_buckets_learned_kort": len(learned_kort),
        "exposure_override_suggestions": exposure_override_suggestions,
        # Til figuren i Logger-fanen: én rad per 10-graders bøtte. "geometrisk"
        # er del C sin glattede kurve midt i bøtta (uendret av del B) - til
        # sammenligning med det som faktisk er lært.
        "exposure_curve": ([
            {
                "from": b * 10, "to": b * 10 + 9,
                "geometric": round(exposure_smoothed[b * 10 + 5], 3),
                "learned_lang": round(learned_lang[b], 3) if b in learned_lang else None,
                "learned_kort": round(learned_kort[b], 3) if b in learned_kort else None,
                "pairs_lang": counts_lang.get(b, 0),
                "pairs_kort": counts_kort.get(b, 0),
            }
            for b in range(36)
        ] if exposure_smoothed is not None else None),
    }
    return {**public, "hours": hours, "tide_events": tides, "bw_until": bw_until,
            "calibration": calibration, "light_days": light_days}


def write_report():
    lines = ["| Spot | Kilde | Status | Detaljer |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in REPORT]
    text = "\n".join(lines)
    if CONVENTION_WARNINGS:
        text = "\n".join(f"**{w}**" for w in CONVENTION_WARNINGS) + "\n\n" + text
    print("\nKilderapport\n" + text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Kilderapport\n\n" + text + "\n")


def main():
    config = json.loads(SPOTS.read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    run_id = now.isoformat()
    logs = safe("alle", "Loggene dine (GitHub)", sources.github_logs, default=[])
    bw_calib = json.loads(BW_CALIB.read_text(encoding="utf-8")) if BW_CALIB.exists() else {}
    exposure_data = json.loads(EXPOSURE_BASELINE.read_text(encoding="utf-8")) if EXPOSURE_BASELINE.exists() else {}
    exposure_learned_data = json.loads(EXPOSURE_LEARNED.read_text(encoding="utf-8")) if EXPOSURE_LEARNED.exists() else {}
    spots = []
    for s in config["spots"]:
        if s.get("enabled"):
            spots.append(build_spot(s, now, calibrate.learn(s["id"], logs), bw_calib, run_id,
                                     exposure_data, exposure_learned_data))
    forecast = {"generated": now.isoformat(), "spots": spots,
                "notify": {k: v for k, v in notify.load_settings().items() if not k.startswith("_")}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(forecast, ensure_ascii=False), encoding="utf-8")
    print(f"Skrev {OUT}")
    BW_CALIB.parent.mkdir(parents=True, exist_ok=True)
    BW_CALIB.write_text(json.dumps(bw_calib, ensure_ascii=False, indent=1), encoding="utf-8")
    EXPOSURE_LEARNED.parent.mkdir(parents=True, exist_ok=True)
    EXPOSURE_LEARNED.write_text(json.dumps(exposure_learned_data, ensure_ascii=False, indent=1), encoding="utf-8")
    notify.run(forecast, now)
    write_report()


if __name__ == "__main__":
    main()
