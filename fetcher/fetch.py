"""Henter varsel for alle spots og skriver docs/data/forecast.json.

Kjør lokalt:  python fetcher/fetch.py
Kjøres automatisk hver tredje time av GitHub Actions.
"""

import os
import json
import math
import datetime as dt
from pathlib import Path

import sources
import calibrate
import exposure_learn
import notify
import sun
import tide as tidemod
import longrange
from exposure import spot_checksum
from rating import (angle_diff, directness, rate, swell_share, bw_period_factor,
                     SURF_FACTOR_DEFAULT, SURF_FACTOR_MIN, SURF_FACTOR_MAX)

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
OUT = ROOT / "docs" / "data" / "forecast.json"
BW_CALIB = ROOT / "data" / "bw_calibration.json"
EXPOSURE_BASELINE = ROOT / "data" / "exposure_baseline.json"
EXPOSURE_LEARNED = ROOT / "data" / "exposure.json"
# 06.10.2026, ROADMAP oppgave B: 16 døgn (var 5), men stopper fortsatt ved
# kortest tilgjengelige kilde. Dag 8-16 lagres hver 6. time, se longrange.py.
HOURS_AHEAD_MAX = longrange.HOURS
ARCHIVE_DIR = longrange.ARCHIVE_DIR   # overstyres av test_pipeline.py (tmp)
LEDGER = longrange.LEDGER
# 06.10.2026, Theodors rettelse (manglende svelldata ble tolket som 0, se
# CLAUDE.md og STATUS.md): forsiktig anslått svellandel for en time der
# sources.openmeteo_marine() måtte bruke totalhøyden som reserve (ingen
# kilde har et ekte, utskilt svellfelt) - IKKE beregnet, et bevisst
# forsiktig Theodor-tall (se build_spot()).
SWELL_SHARE_FALLBACK_ESTIMATE = 0.6
REPORT = []  # kilderapport, vises i Actions
# Advarsler om at retningskonvensjonen mot BarentsWatch kan ha blitt feil
# igjen (se build_spot()) - vises ØVERST i kilderapporten, ikke i selve
# tabellen, og endrer aldri ratingen automatisk.
CONVENTION_WARNINGS = []
# 27.09.2026, Theodors rettelse (Unstad for lav - se STATUS.md): fornufts-
# sjekk mot at BarentsWatch-justeringen (svellandel/periode/retning) trekker
# for hardt ned - se low_adjustment_warning(). Samme plassering/prinsipp som
# CONVENTION_WARNINGS over.
LOW_ADJUSTMENT_WARNINGS = []
# 05.10.2026, Theodors rettelse (Farstadsanden - se STATUS.md): sikring mot
# at et BarentsWatch-punkt ligger i le - se bw_point_in_lee_warning().
BW_LEE_WARNINGS = []


def pick(*vals):
    return next((v for v in vals if v is not None), None)


def _hours_available(source_dict, now):
    """Timer fra now til siste tilgjengelige tidspunkt i kilden. 0 hvis tom."""
    if not source_dict:
        return 0
    last = sources.parse_iso(max(source_dict))
    return max(0, int((last - now).total_seconds() // 3600) + 1)


def _timestep_summary(raw, now):
    """27.09.2026: horisont og hvor tidssteget mellom påfølgende tidspunkter
    endrer seg for en RÅ kildedict (før evt. interpolering) - til
    kilderapporten, se ROADMAP ("vinden forsvinner fra onsdag kl. 12").
    met.no sitt Locationforecast (vind) går fra time- til 6-timerssteg etter
    ca. 51 timer (live sjekket 27.09.2026) - Oceanforecast og Open-Meteo
    Marine har IKKE samme problem, bekreftet her ved at de ikke viser noen
    endring. Returnerer (horisont_timer, tekst)."""
    if not raw:
        return 0, "ingen data"
    times = sorted(raw)
    last = sources.parse_iso(times[-1])
    horizon = max(0, int((last - now).total_seconds() // 3600) + 1)
    parsed = [sources.parse_iso(t) for t in times]
    prev_gap = None
    for a, b in zip(parsed, parsed[1:]):
        gap = round((b - a).total_seconds() / 3600)
        if prev_gap is not None and gap != prev_gap:
            return horizon, f"tidssteg endres fra {prev_gap}t til {gap}t ved {sources.hour_key(a)}"
        prev_gap = gap
    return horizon, "jevnt tidssteg hele horisonten"


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


def resolve_obstacle_geometry(spot, exposure_data):
    """06.10.2026, Theodors rettelse (Farstadsanden 337 grader, Nordneset -
    se STATUS.md): avstand OG bredde (km) til nærmeste hindring per grad,
    samme sjekksum-vern som resolve_exposure() - men ALDRI en advarsel i
    kilderapporten for seg selv (resolve_exposure() sitt kall varsler
    allerede om sjekksum-avvik). (None, None) (ingen blokkering mulig, samme
    trygge retning som blocked_by_near_obstacle() sin egen fallback) hvis
    eksponeringsdata mangler, sjekksummen ikke stemmer, eller fila er fra
    FØR distance_km/width_km fantes (eldre exposure_baseline.json)."""
    entry = exposure_data.get(spot["id"])
    if entry is None or entry.get("checksum") != spot_checksum(spot):
        return None, None
    return entry.get("distance_km"), entry.get("width_km")


def sanitize_hour_fields(hour):
    """06.10.2026, Theodors rettelse (HASTER-funn, Unstad 14 dager frem
    viste "Flatt, svell 0,0 m fra 0 grader, periode 0 s" - manglende data
    var tolket som 0 hele veien, se CLAUDE.md sin nye grunnregel). To
    uavhengige opprensker, begge FØR rate() kalles (slik at både ratingen
    OG breakdown-teksten får de riktige, sanerte tallene - ikke bare
    visningen etterpå):

    1. Svell ute markert `swell_model=="total_fallback"` (se
       sources.openmeteo_marine()) har fått `swell_offshore` satt til
       TOTALHØYDEN (reserve, ingen kilde hadde et ekte, utskilt svellfelt) -
       dempes her med SWELL_SHARE_FALLBACK_ESTIMATE, et forsiktig ANSLAG
       (ikke beregnet - vi vet bokstavelig talt ikke den ekte svellandelen
       for timen).
    2. Kast kan fysisk ikke være lavere enn middelvinden - settes til None
       for å unngå å vise en selvmotsigende kombinasjon ("16 m/s med kast
       3"). rating.effective_wind() ignorerer allerede kast under
       middelvinden (kun gust>speed gir et tillegg), så dette endrer ALDRI
       ratingen - bare visningen og breakdown-teksten ("mangler kast, vis
       bare vind", se CLAUDE.md).

    Muterer `hour` i stedet (kalt rett før rate(), samme mønster som resten
    av build_spot()). Returnerer True hvis kast ble nullstilt (til
    fornuftssjekken i kilderapporten sin telling), ellers False."""
    if hour.get("swell_model") == "total_fallback" and hour.get("swell_offshore") is not None:
        hour["swell_offshore"] *= SWELL_SHARE_FALLBACK_ESTIMATE
    gust, wind_speed = hour.get("gust"), hour.get("wind_speed")
    if gust is not None and wind_speed is not None and gust < wind_speed:
        hour["gust"] = None
        return True
    return False


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


BW_PLAUSIBILITY_WIND_MIN = 10.0  # m/s
BW_PLAUSIBILITY_SHARE_MAX = 0.3  # svellandel
BW_PLAUSIBILITY_DEG = 60  # grader fra vindretningen


def bw_direction_plausible(hour):
    """27.09.2026: permanent plausibilitetssjekk (se ROADMAP og STATUS.md,
    "test source/fileSource-hypotesen med data" - hypotesen om at ulike
    BarentsWatch-kilder/filer kan bruke ulik retningskonvensjon ble tidligere
    avvist på resonnement alene, aldri testet mot ekte data).

    I timer med sterk vind (10 m/s+) og lav svellandel (under 30 %) er sjøen
    ved punktet stort sett vindsjø - da BØR BarentsWatch-retningen ("fra")
    ligge innenfor ca 60 grader av vindretningen (vindsjø følger vinden).
    Sjekker BÅDE med (bw_dir, dagens konverterte "fra") og uten (bw_dir_raw,
    rått "mot" fra API-et) omregningen - stemmer én konsekvent og den andre
    ikke, er det et konkret tegn på at konvensjonen varierer med kilden.

    Krever en ekte BarentsWatch-retning for timen (bw_dir ikke None) - ellers
    ville reservemodell-timer (ingen BarentsWatch i det hele tatt, f.eks.
    lokalt uten nøkler) telt som "gjelder", med matches=None tolket som
    "stemmer ikke" av en gal grunn (mangler data, ikke feil retning).

    Endrer ALDRI ratingen - bare rapportert (kilderapport og, etter neste
    Actions-kjøring, en tabell i STATUS.md). Returnerer
    (gjelder_denne_timen, stemmer_med_omregning, stemmer_uten_omregning) -
    de to siste er None når sjekken ikke gjelder eller rå-retningen mangler."""
    wind_speed, wind_dir = hour.get("wind_speed"), hour.get("wind_dir")
    bw_dir = hour.get("bw_dir")
    share, share_known = swell_share(hour)
    if wind_speed is None or wind_dir is None or bw_dir is None or not share_known:
        return False, None, None
    if wind_speed < BW_PLAUSIBILITY_WIND_MIN or share >= BW_PLAUSIBILITY_SHARE_MAX:
        return False, None, None
    bw_dir_raw = hour.get("bw_dir_raw")
    matches = angle_diff(bw_dir, wind_dir) <= BW_PLAUSIBILITY_DEG
    matches_raw = angle_diff(bw_dir_raw, wind_dir) <= BW_PLAUSIBILITY_DEG if bw_dir_raw is not None else None
    return True, matches, matches_raw


def bw_plausibility_report(hours, name):
    """Teller opp bw_direction_plausible() sitt resultat per source/fileSource
    for denne spoten sin kjøring, og legger en rad i kilderapporten hvis noen
    timer var aktuelle. Selve tabellen (per spot OG per source/fileSource,
    slik ROADMAP ber om) bygges i STATUS.md etter neste Actions-kjøring, når
    det finnes ekte tall - denne rapporten er grunnlaget den bygges fra.

    27.09.2026, fysikk-kontrollør sitt funn: interpolerte timer har ekte,
    interpolerte bw_dir/bw_dir_raw-verdier (satt av sources.bw_interpolate()),
    men ALDRI bw_source/bw_file_source (ingen ekte kilde for en syntetisk
    mellomtime) - de ville endt i en uspesifisert "?/?"-bøtte og utvannet
    nettopp per-kilde-statistikken denne rapporten skal bygge. Samme filter
    som bw_sources-tellingen rett over i build_spot()."""
    by_source = {}
    for h in hours:
        if h.get("bw_interpolated"):
            continue
        applies, matches, matches_raw = bw_direction_plausible(h)
        if not applies:
            continue
        key = (h.get("bw_source"), h.get("bw_file_source"))
        rec = by_source.setdefault(key, {"n": 0, "match": 0, "match_raw": 0})
        rec["n"] += 1
        rec["match"] += bool(matches)
        rec["match_raw"] += bool(matches_raw)
    if not by_source:
        return
    parts = [f"{src or '?'}/{file_src or '?'}: {rec['match']}/{rec['n']} med omregning, "
             f"{rec['match_raw']}/{rec['n']} uten"
             for (src, file_src), rec in sorted(by_source.items())]
    REPORT.append((name, "BarentsWatch-retning vs. vind (plausibilitet)", "ok", "; ".join(parts)))


BW_LEE_RATIO = 0.10  # se bw_point_in_lee_warning()
BW_LEE_MIN_OFFSHORE = 2.0  # m, se bw_point_in_lee_warning()


def bw_point_in_lee_warning(hours, spot, name):
    """05.10.2026, Theodors rettelse (Farstadsanden - se STATUS.md): generell
    sikring mot at et BarentsWatch-punkt ligger i le (f.eks. bak en odde,
    eller i en skjermet lomme/grunt vann nær land som BarentsWatch sin egen,
    finmaskede modell demper kraftig, men som vår grovere kystlinjesjekk
    ikke nødvendigvis fanger opp). Et slikt punkt gir en kunstig lav
    totalhøyde UANSETT hvor mye energi det faktisk er ute - verken
    is_blown_out() eller classify_low_rating() kan se forskjell på et ekte
    flatt punkt og et punkt som bare måler feil, siden begge bare ser
    BarentsWatch sin egen bw_height.

    Fysikk-kontrollør fant (05.10.2026) at en første versjon av denne
    manglet retningsfiltreringen convention_warning() over allerede har, og
    derfor ga falsk alarm for Grøtfjord 25.09.2026 (en FAST observasjon i
    CLAUDE.md: helt flatt fordi svellet var 3 grader UTENFOR vinduet, ikke
    fordi noe punkt ligger i le) - lav bw_height når svellet ute ikke engang
    treffer vinduet er forventet og sier INGENTING om punktets plassering.
    Bare timer der svellet ute faktisk ER mot vinduet (directness over 0,5,
    samme grense og funksjon som convention_warning()) telles derfor med.

    Hvis bw_height er under BW_LEE_RATIO (10 %) av totalhøyden ute
    (height_offshore) i MER ENN HALVPARTEN av disse timene der totalhøyden
    ute i tillegg er over BW_LEE_MIN_OFFSHORE (2 m - så stille dager med
    lite energi totalt ikke trigger dette ved en tilfeldighet), er det et
    tegn på at punktet systematisk ligger i le. Endrer ALDRI ratingen selv -
    bare rapportert."""
    stormy = [h for h in hours if h.get("height_offshore") is not None
              and h["height_offshore"] > BW_LEE_MIN_OFFSHORE and h.get("bw_height") is not None
              and directness(h.get("dir_offshore"), spot) > 0.5]
    if not stormy:
        return None
    low = [h for h in stormy if h["bw_height"] < BW_LEE_RATIO * h["height_offshore"]]
    if len(low) <= len(stormy) / 2:
        return None
    return (f"BarentsWatch-punktet for {name} ligger trolig i le. BarentsWatch-høyden er under "
            f"{int(BW_LEE_RATIO * 100)} % av totalhøyden ute i {len(low)} av {len(stormy)} timer "
            f"med svell mot vinduet og over {BW_LEE_MIN_OFFSHORE:.0f} m totalt ute.")


LOW_ADJUSTMENT_RATIO = 0.25  # se low_adjustment_warning()


def low_adjustment_warning(hours, name):
    """27.09.2026, Theodors rettelse (Unstad for lav - se STATUS.md, punkt 5):
    fornuftssjekk mot at BarentsWatch-justeringen (min(svellandel, periode-
    faktor) × retningsfaktor, se rating.barentswatch_height()) trekker for
    hardt ned. Hvis den justerte høyden (hour["height"]) er under
    LOW_ADJUSTMENT_RATIO (25 %) av BarentsWatch sin egen totalhøyde
    (bw_height) i MER ENN HALVPARTEN av spotens DAGSLYS-timer med
    BarentsWatch-data, er det et tegn på at ett av leddene systematisk
    trekker for hardt ned for akkurat denne spoten - varsler med hvilket
    ledd (gjennomsnittet blant de lave timene, samme min()-logikk som
    avgjør hvilket ledd som faktisk er det begrensende). Endrer ALDRI
    ratingen selv - bare rapportert, som convention_warning()."""
    day_bw = [h for h in hours if h.get("daylight") and h.get("height_source") == "barentswatch"
              and h.get("bw_height") and h.get("height") is not None]
    if not day_bw:
        return None
    low = [h for h in day_bw if h["height"] < LOW_ADJUSTMENT_RATIO * h["bw_height"]]
    if len(low) <= len(day_bw) / 2:
        return None
    shares, pfs, dirfacs = [], [], []
    for h in low:
        share, share_known = swell_share(h)
        pf = bw_period_factor(h.get("bw_period"))
        if share <= pf:
            shares.append(share)
        else:
            pfs.append(pf)
        if h.get("spot_direction_factor") is not None and h["spot_direction_factor"] < 0.999:
            dirfacs.append(h["spot_direction_factor"])
    terms = []
    if shares:
        terms.append(f"svellandel (snitt {round(100 * sum(shares) / len(shares))} %)")
    if pfs:
        terms.append(f"BarentsWatch-periodefaktoren (snitt {sum(pfs) / len(pfs):.2f})")
    if dirfacs:
        terms.append(f"retningsfaktoren ved punktet (snitt {sum(dirfacs) / len(dirfacs):.2f})")
    worst = ", ".join(terms) if terms else "et ukjent ledd"
    return (f"{name}: justert høyde er under {int(LOW_ADJUSTMENT_RATIO * 100)} % av BarentsWatch sin "
            f"totalhøyde i {len(low)} av {len(day_bw)} dagslystimer med BarentsWatch-data. "
            f"Mest sannsynlig årsak: {worst}.")


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


def build_spot(spot, now, learned, bw_calib, run_id, exposure_data, exposure_learned_data, ledger=None):
    name = spot["name"]
    ledger = ledger or {}
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
    weather_raw = safe(name, "met.no vind", sources.metno_weather, s["lat"], s["lon"])
    # 27.09.2026, ROADMAP oppgave 1: Locationforecast (vind) går fra time- til
    # 6-timerssteg etter ca. 51 timer - interpolert her (se
    # sources.weather_interpolate() sin docstring) slik at ingen time mister
    # vind helt og får datafeil-straffen for ukjent vind. Oceanforecast og
    # Open-Meteo Marine sjekket for samme problem (se _timestep_summary()
    # under) - ingen av dem trenger tilsvarende interpolering.
    weather = sources.weather_interpolate(weather_raw)
    # 06.10.2026, ROADMAP oppgave B: met.no så langt den rekker (ca. 10 døgn,
    # 6-timers steg mot slutten, interpolert over), deretter Open-Meteo
    # GFS-vind til dag 16. Hver time får wind_source ("metno"/"openmeteo").
    wind_lr_raw = safe(name, "Open-Meteo GFS-vind (langtid)", sources.openmeteo_wind, s["lat"], s["lon"])
    weather = sources.merge_wind(weather, wind_lr_raw)
    for label, raw_src in (("met.no hav (spot)", ocean_spot), ("met.no hav (ute)", ocean_off),
                            ("Open-Meteo svell (ute)", marine), ("met.no vind", weather_raw)):
        _, txt = _timestep_summary(raw_src, now)
        REPORT.append((name, f"{label}, tidssteg", "ok" if raw_src else "tom", txt))
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

    # 06.10.2026, Theodors rettelse (Farstadsanden 337 grader, Nordneset -
    # se STATUS.md): avstand/bredde til nærmeste hindring, til
    # rating.blocked_by_near_obstacle() - samme kilde (exposure_baseline.json)
    # og sjekksum-vern som eksponeringen over, bare de to ekstra feltene.
    exposure_distance_km, exposure_width_km = resolve_obstacle_geometry(spot, exposure_data)
    if exposure_distance_km is not None:
        spot["exposure_distance_km"] = exposure_distance_km
    if exposure_width_km is not None:
        spot["exposure_width_km"] = exposure_width_km

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
    # surf_factor: rekkefølge 1) lært fra loggene (calibrate.learn(), minst
    # MIN_LOGS logger), 2) surf_factor_prior i spots.json (en startverdi satt
    # fra ekte, navngitte observasjoner FØR det finnes nok logger til å lære
    # selv - se Unstad sin _surf_factor_prior-kommentar, 30.09.2026), 3)
    # SURF_FACTOR_DEFAULT (1,0). En lært verdi overstyrer ALLTID prioren så
    # snart det finnes nok logger - prioren er bare et bedre startpunkt enn
    # 1,0 for en spot der formelen er kjent å bomme systematisk.
    if learned.get("surf_factor") is not None:
        surf_factor_value, surf_factor_source = learned["surf_factor"], "logs"
    elif spot.get("surf_factor_prior") is not None:
        surf_factor_value = round(min(SURF_FACTOR_MAX, max(SURF_FACTOR_MIN, spot["surf_factor_prior"])), 2)
        surf_factor_source = "prior"
    else:
        surf_factor_value, surf_factor_source = SURF_FACTOR_DEFAULT, "standard"
    spot["transfer"], spot["surf_factor"] = transfer_value, surf_factor_value
    # Bare til bruk i rate()/build_breakdown() under (samme mønster som
    # exposure_smoothed) - ekskludert fra offentlig utdata lenger ned,
    # siden calibration.surf_factor_source allerede dekker det samme.
    spot["surf_factor_source"] = surf_factor_source

    hours = []
    gust_lower_than_wind = 0  # se data_sanity_warnings() under
    for i in range(horizon):
        t = now + dt.timedelta(hours=i)
        k = sources.hour_key(t)
        # ROADMAP oppgave B: dag 8-16 bare hver 6. time (filstørrelse, se longrange.py).
        day = longrange.day_index(now, t)
        if not longrange.keep_row(t, day):
            continue
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
            # 27.09.2026: hvilken BarentsWatch-kilde/fil punktet kom fra -
            # permanent sjekk (se ROADMAP og STATUS.md, "test source/
            # fileSource-hypotesen med data"). None for interpolerte timer
            # (ingen ekte kilde for en syntetisk mellomverdi). Brukes ALDRI
            # til å velge eller endre verdier - bare rapportert.
            "bw_source": bwk.get("source") if bwk else None,
            "bw_file_source": bwk.get("file_source") if bwk else None,
            # Rå (ukonvertert) BarentsWatch-retning - bare til
            # plausibilitetssjekken under, ALDRI brukt i ratingen (bw_dir,
            # over, er den konverterte "fra"-verdien som brukes der).
            "bw_dir_raw": bwk.get("dir_raw") if bwk else None,
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
        if sanitize_hour_fields(hour):
            gust_lower_than_wind += 1
        hour.update(rate(hour, spot))
        # ROADMAP oppgave B: sone, dag frem og sikkerhet i prosent (kapper
        # ALDRI stjernene - bare merket). "målt" når spoten har nok
        # sammenligninger for dette antallet dager frem, ellers "anslag".
        hour["day"] = day
        hour["zone"] = longrange.zone_for(hour["height_source"], day)
        hour["confidence"], hour["confidence_source"] = longrange.confidence_for(ledger, spot["id"], day)
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
    total_fallback_hours = sum(1 for h in hours if h.get("swell_model") == "total_fallback")
    none_hours = sum(1 for h in hours if h.get("swell_model") is None)
    REPORT.append((name, "Svellmodell", "ok",
                   f"GFS Wave {gfs_hours}t, standardmodell (reserve) {std_hours}t, "
                   f"totalhøyde-reserve {total_fallback_hours}t, ingen svelldata {none_hours}t"))
    # 06.10.2026, Theodors rettelse (punkt 6, se CLAUDE.md): fornuftssjekk -
    # tilfeller der tallene motsier hverandre, telt per sone (ikke bare
    # totalt), til å fange nye varianter av "manglende data tolket som 0"
    # tidlig, i kilderapporten, uten å vente på at noen legger merke til det
    # i appen.
    sanity_zones = ("barentswatch", "reserve", "langtid")
    height_no_swell = {z: 0 for z in sanity_zones}
    zero_period = {z: 0 for z in sanity_zones}
    for h in hours:
        z = h.get("zone")
        if z not in height_no_swell:
            continue
        if (h.get("height_offshore") or 0) > 1 and not h.get("swell_offshore"):
            height_no_swell[z] += 1
        if h.get("period") == 0:
            zero_period[z] += 1
    sanity_hits = sum(height_no_swell.values()) + sum(zero_period.values()) + gust_lower_than_wind
    sanity_txt = (f"totalhøyde over 1 m men svell 0/mangler: BarentsWatch {height_no_swell['barentswatch']}, "
                  f"reserve {height_no_swell['reserve']}, langtid {height_no_swell['langtid']}. "
                  f"Periode nøyaktig 0: BarentsWatch {zero_period['barentswatch']}, reserve {zero_period['reserve']}, "
                  f"langtid {zero_period['langtid']}. Kast lavere enn vind (nullstilt): {gust_lower_than_wind}.")
    REPORT.append((name, "Fornuftssjekk (manglende data)", "ok" if sanity_hits == 0 else "feil", sanity_txt))
    zones = {z: sum(1 for h in hours if h.get("zone") == z) for z in ("barentswatch", "reserve", "langtid")}
    winds = {w: sum(1 for h in hours if h.get("wind_source") == w) for w in ("metno", "openmeteo")}
    REPORT.append((name, "Soner (rader)", "ok", f"BarentsWatch {zones['barentswatch']}, reserve {zones['reserve']}, langtid {zones['langtid']} (hver 6. time)"))
    REPORT.append((name, "Vindkilde (rader)", "ok" if winds["metno"] else "tom",
                   f"met.no {winds['metno']}, Open-Meteo GFS {winds['openmeteo']}, ingen {len(hours) - winds['metno'] - winds['openmeteo']}"))

    # 27.09.2026: hvilke BarentsWatch source/fileSource-kombinasjoner som
    # faktisk ble brukt denne kjøringen - permanent sjekk (se ROADMAP og
    # STATUS.md, "test source/fileSource-hypotesen med data"). Bare
    # RÅ (ikke-interpolerte) timer har en ekte kilde å telle.
    bw_sources = {}
    for h in hours:
        if h.get("bw_interpolated"):
            continue
        if h.get("bw_source") is None and h.get("bw_file_source") is None:
            continue
        key = (h.get("bw_source"), h.get("bw_file_source"))
        bw_sources[key] = bw_sources.get(key, 0) + 1
    if bw_sources:
        src_txt = ", ".join(f"{src or '?'} / {file_src or '?'}: {n}t" for (src, file_src), n in sorted(bw_sources.items()))
        REPORT.append((name, "BarentsWatch source/fileSource", "ok", src_txt))

    bw_plausibility_report(hours, name)

    low_adj = low_adjustment_warning(hours, name)
    if low_adj:
        LOW_ADJUSTMENT_WARNINGS.append(low_adj)

    bw_lee = bw_point_in_lee_warning(hours, spot, name)
    if bw_lee:
        BW_LEE_WARNINGS.append(bw_lee)

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

    new_pairs = calibrate.bw_pairs_for_run(hours, run_id, spot)
    merged_pairs = calibrate.merge_bw_pairs(bw_pairs_existing, new_pairs, now)
    bw_calib[spot["id"]] = merged_pairs
    bw_days = len({p["t"][:10] for p in merged_pairs})

    # Del B: nye eksponeringspar bygges FRA hours (trenger swell_share,
    # sources_disagree osv. - rate() sitt resultat), og lagres for BRUK NESTE
    # KJØRING (se kommentaren over exposure_pairs_existing lenger opp).
    new_exposure_pairs = exposure_learn.exposure_pairs_for_run(hours, run_id, spot)
    merged_exposure_pairs = exposure_learn.merge_pairs(exposure_pairs_existing, new_exposure_pairs, now)
    exposure_learned_data[spot["id"]] = merged_exposure_pairs
    exposure_override_suggestions = exposure_learn.override_removal_suggestions(
        spot.get("exposure_override"), learned_kort, learned_lang)

    # exposure_smoothed/exposure_raw/exposure_smoothed_lang/exposure_smoothed_kort
    # er interne tall (én per grad) bare til bruk i rate() over - ikke noe
    # appen trenger å vise, ekskludert fra utdata. exposure_distance_km/
    # exposure_width_km (06.10.2026) er samme slags tabell, bare til
    # rating.blocked_by_near_obstacle() - resultatet (directness/bw_confirms
    # per time) er allerede i hours, ikke rå-tabellene selv.
    _internal_keys = {"exposure_smoothed", "exposure_raw", "exposure_smoothed_lang", "exposure_smoothed_kort",
                       "surf_factor_source", "exposure_distance_km", "exposure_width_km"}
    public = {k: v for k, v in spot.items() if not k.startswith("_") and k not in _internal_keys}
    # 06.10.2026, Theodors rettelse (punkt 4): var 4 dager (funksjonens egen
    # standardverdi) - for kort til et 16-dagers varsel. Dag 9-16 viste
    # dermed "–" for lys/mørketid der appen faktisk har time- og
    # dagbrikke-data (langtid-sonen).
    light_days = sun.light_days(s["lat"], s["lon"], now, days=longrange.DAYS)
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
        "surf_factor_prior_n": spot.get("surf_factor_prior_n"),
        # Del B, ROADMAP oppgave 4 - hvor mye eksponering som er lært akkurat
        # nå (par fra FØR denne kjøringen, se over), til Logger-fanen og
        # STATUS.md.
        "exposure_pairs": len(merged_exposure_pairs),
        "exposure_buckets_learned_lang": len(learned_lang),
        "exposure_buckets_learned_kort": len(learned_kort),
        "exposure_override_suggestions": exposure_override_suggestions,
        # ROADMAP oppgave B: treffprosent per antall dager frem (Logger-fanen),
        # fra kjøringene FØR denne (denne kjøringens egen scoring skjer etter
        # at spotene er bygget, se main()).
        "accuracy": longrange.accuracy_table(ledger, spot["id"]),
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


HEALTH_MIN_HOURS = 48  # færre timer enn dette for en spot er et tegn på at kildene sviktet


def health_check(spots):
    """ROADMAP oppgave G (overvåking av henteren), 07.10.2026: enkel
    helsesjekk av en ferdig kjøring - alle spots har data fra hver kilde,
    ingen tomme eller ugyldige tall, horisont som forventet. Legger rader i
    kilderapporten og returnerer en liste problemer (tom = frisk). Hvert
    problem sendes som driftsvarsel til Theodor (notify.alert()) av main().

    Kildene sjekkes på det som faktisk ender i forecast.json per time (ikke
    på REPORT-radene) - det er det appen ser. "Mangler for alle spots" er
    kriteriet (ROADMAP): én spot uten BarentsWatch er normalt (punktet kan
    ligge utenfor dekningen), alle uten er et utfall eller en utgått nøkkel.
    BarentsWatch sjekkes bare når nøkler finnes (BW_CLIENT_ID) - lokalt og
    i testene finnes de ikke, og det er ikke et utfall."""
    problems = []
    n = len(spots)
    if not n:
        REPORT.append(("alle", "Helsesjekk", "feil", "ingen spots bygget"))
        return ["ingen spots bygget"]
    checks = [
        ("met.no vind", lambda s: any(h.get("wind_source") == "metno" for h in s["hours"])),
        ("Open-Meteo svell ute", lambda s: any(h.get("swell_offshore") is not None for h in s["hours"])),
        ("Kartverket tidevann", lambda s: any(h.get("tide") is not None for h in s["hours"])),
    ]
    if os.environ.get("BW_CLIENT_ID"):
        checks.append(("BarentsWatch", lambda s: any(h.get("bw_height") is not None for h in s["hours"])))
    else:
        REPORT.append(("alle", "Helsesjekk: BarentsWatch", "info", "ingen nøkler i miljøet - ikke sjekket"))
    for label, fn in checks:
        ok = sum(1 for s in spots if fn(s))
        REPORT.append(("alle", f"Helsesjekk: {label}", "ok" if ok == n else ("feil" if ok == 0 else "delvis"),
                       f"{ok} av {n} spots har data"))
        if ok == 0:
            problems.append(f"{label} mangler for alle {n} spots")
    for s in spots:
        hrs = s.get("hours") or []
        if len(hrs) < HEALTH_MIN_HOURS:
            problems.append(f"{s['name']}: bare {len(hrs)} timer i varselet (ventet minst {HEALTH_MIN_HOURS})")
        bad = [h.get("t") for h in hrs
               if not (isinstance(h.get("stars"), int) and 0 <= h["stars"] <= 5)
               or any(isinstance(v, float) and (math.isnan(v) or math.isinf(v)) for v in h.values())]
        if bad:
            problems.append(f"{s['name']}: {len(bad)} timer med ugyldige tall (første {bad[0]})")
    REPORT.append(("alle", "Helsesjekk", "ok" if not problems else "feil",
                   "; ".join(problems) if problems else f"alle {n} spots har data, gyldige tall og minst {HEALTH_MIN_HOURS} timer"))
    return problems


def write_report():
    lines = ["| Spot | Kilde | Status | Detaljer |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in REPORT]
    text = "\n".join(lines)
    all_warnings = CONVENTION_WARNINGS + LOW_ADJUSTMENT_WARNINGS + BW_LEE_WARNINGS
    if all_warnings:
        text = "\n".join(f"**{w}**" for w in all_warnings) + "\n\n" + text
    print("\nKilderapport\n" + text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Kilderapport\n\n" + text + "\n")


def main():
    config = json.loads(SPOTS.read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    run_id = now.isoformat()
    logs = safe("alle", "Loggene dine (GitHub)", sources.github_logs, default=[])
    ledger = longrange.load_ledger(LEDGER)
    bw_calib = json.loads(BW_CALIB.read_text(encoding="utf-8")) if BW_CALIB.exists() else {}
    exposure_data = json.loads(EXPOSURE_BASELINE.read_text(encoding="utf-8")) if EXPOSURE_BASELINE.exists() else {}
    exposure_learned_data = json.loads(EXPOSURE_LEARNED.read_text(encoding="utf-8")) if EXPOSURE_LEARNED.exists() else {}
    spots = []
    for s in config["spots"]:
        if s.get("enabled"):
            spots.append(build_spot(s, now, calibrate.learn(s["id"], logs), bw_calib, run_id,
                                     exposure_data, exposure_learned_data, ledger))
    forecast = {"generated": now.isoformat(), "spots": spots,
                "notify": {k: v for k, v in notify.load_settings().items() if not k.startswith("_")}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(forecast, ensure_ascii=False), encoding="utf-8")
    print(f"Skrev {OUT}")
    # ROADMAP oppgave B: arkiver denne kjøringen (små filer), mål eldre
    # varsel mot fasit (denne kjøringens nærmeste timer + loggene), lagre.
    longrange.write_archive(now, spots, ARCHIVE_DIR)
    pruned = longrange.prune_archives(now, ARCHIVE_DIR)
    scored_now, scored_logs = longrange.score_runs(now, spots, logs, ledger, ARCHIVE_DIR)
    longrange.save_ledger(ledger, LEDGER)
    REPORT.append(("alle", "Treffsikkerhet (langtid)", "ok",
                   f"{scored_now} nye sammenligninger mot eget varsel, {scored_logs} mot logger, {pruned} arkiv slettet"))
    BW_CALIB.parent.mkdir(parents=True, exist_ok=True)
    BW_CALIB.write_text(json.dumps(bw_calib, ensure_ascii=False, indent=1), encoding="utf-8")
    EXPOSURE_LEARNED.parent.mkdir(parents=True, exist_ok=True)
    EXPOSURE_LEARNED.write_text(json.dumps(exposure_learned_data, ensure_ascii=False, indent=1), encoding="utf-8")
    notify.run(forecast, now)
    # ROADMAP oppgave G: helsesjekk til slutt (alt over er skrevet uansett -
    # et halvdårlig varsel er bedre enn ingen), ett driftsvarsel per problem.
    for problem in health_check(spots):
        notify.alert("Nordsurf: henteren har et problem", problem, problem, now)
    write_report()


if __name__ == "__main__":
    main()
