"""Lærer av loggene: surf_factor (hvor godt Komar og Gaughan sin bruddhøyde-
formel stemmer med det du faktisk ser, per spot), og om varselet bommer på
stjernene. Lærer også en uavhengig transfer fra BarentsWatch, ved å
sammenligne reservemodellens inngangsverdier (svell ute * directness) mot
BarentsWatch sine egne, ekte målinger - se bw_transfer()/effective_transfer().

26.09.2026: transfer læres IKKE lenger fra loggene (størrelse / (svell ute *
directness)) - den sammenlignet surfehøyde (det du ser) med Hs (signifikant
høyde), som er to forskjellige fysiske størrelser. Loggene brukes nå bare
til surf_factor (størrelse / Hb, se rating.breaking_height), i tillegg til
tidevann/stjerne-bias som før."""
import datetime as dt
from statistics import median

from rating import breaking_height, FLAT_HS_THRESHOLD, SURF_FACTOR_MIN, SURF_FACTOR_MAX, blocked_by_near_obstacle

DIRECTNESS_MIN_FOR_SURF_FACTOR = 0.667  # se learn()

# Størrelser i meter SURFEHØYDE (høyden der bølgene brekker), ikke Hs.
# 26.09.2026: Hodehøy er ny, Over hodet endret fra 2,0 til 2,4, Dobbelt over
# hodet er ny. Gamle logger beholder etiketten sin, men får den nye
# meterverdien - se README for hvor mange logger det gjaldt da endringen ble
# gjort. Samme tabell finnes i docs/index.html - test_pipeline.py sjekker at
# de er like.
SIZE_M = {
    "Flatt": 0.0, "Knehøy": 0.5, "Hoftehøy": 0.9, "Brysthøy": 1.3,
    "Hodehøy": 1.8, "Over hodet": 2.4, "Dobbelt over hodet": 3.6,
}
MIN_LOGS = 5

BW_MIN_PAIRS = 40  # trenger nok par før vi stoler på medianen
BW_MIN_DAYS = 3    # spredt over minst tre døgn, ikke bare én værsituasjon
BW_MAX_AGE_DAYS = 30


def learn(spot_id, logs):
    """surf_factor = median(logget størrelse i meter / Hb fra formelen på
    loggtidspunktet). Bare logger der Hs ved spoten (forecastHeight) var
    minst FLAT_HS_THRESHOLD og perioden ute (forecastPeriod) er kjent - uten
    dem kan ikke Hb regnes ut. Observasjoner (type "observed") teller likt
    som egne økter (size/stjerner betyr det samme uansett hvem som så det).

    26.09.2026: logger der directness var under DIRECTNESS_MIN_FOR_SURF_FACTOR
    telles ikke. Grøtfjord var flatt tre dager på rad (24.-26.09.2026) fordi
    svellet kom fra feil retning (skyggekurven/diffraksjon), ikke fordi
    spoten generelt får mindre bølger enn formelen sier - en slik logg ville
    feilaktig lært ned surf_factor for HELE spoten, ikke bare for skrått
    svell (som allerede dempes for seg, se rating.rate())."""
    mine = [l for l in logs if l.get("spot") == spot_id]
    ratios = [
        SIZE_M[l["size"]] / breaking_height(l["forecastHeight"], l["forecastPeriod"])
        for l in mine
        if l.get("size") in SIZE_M
        and (l.get("forecastHeight") or 0) >= FLAT_HS_THRESHOLD
        and l.get("forecastPeriod") is not None
        and (l.get("directness") if l.get("directness") is not None else 1.0) >= DIRECTNESS_MIN_FOR_SURF_FACTOR
    ]
    stars = [l["stars"] - l["forecastStars"] for l in mine if l.get("forecastStars") is not None]
    out = {"logs": len(mine), "surf_factor_logs": len(ratios)}
    if len(ratios) >= MIN_LOGS:
        out["surf_factor"] = round(min(SURF_FACTOR_MAX, max(SURF_FACTOR_MIN, median(ratios))), 2)
    if stars:
        out["bias"] = round(sum(stars) / len(stars), 2)
        out["hits"] = sum(1 for d in stars if abs(d) <= 1)
        out["compared"] = len(stars)
    return out


def bw_pairs_for_run(hours, run_id, spot):
    """Kalibreringspar for denne kjøringen: bare RÅ (ikke interpolerte)
    BarentsWatch-timer der svellet ute klart dominerer bildet og retningen
    treffer godt nok til at et forhold sier noe fornuftig om direkte treff.
    I tillegg (26.09.2026, svell-mot-vindsjø-fiksen): aldri timer der
    kildene er uenige (sources_disagree), og bare der bølgene ved
    BarentsWatch-punktet klart går inn mot stranda (spot_direction_factor
    minst 0,7) - ellers lærer vi feil forhold fra en time som i
    virkeligheten var mest vindsjø eller feil retning.

    06.10.2026, Theodors rettelse (Farstadsanden 337 grader, Nordneset - se
    STATUS.md): heller aldri timer der svellet ute kommer fra en retning med
    en nær, BRED hindring (rating.blocked_by_near_obstacle()) - samme risiko
    som i exposure_learn.exposure_pairs_for_run() (se dens docstring): en
    hindring BarentsWatch sin egen modell ikke ser, ville gitt en kunstig
    HØY transfer her (bw deles på en lav, men FEILAKTIG lav, dn - directness
    - uten denne sjekken alene, siden dn<0,3-grensa under ikke fanger hele
    skyggesonen, bare den dypeste delen av den)."""
    pairs = []
    for h in hours:
        if h.get("height_source") != "barentswatch" or h.get("bw_interpolated"):
            continue
        if h.get("sources_disagree"):
            continue
        if (h.get("spot_direction_factor") or 0) < 0.7:
            continue
        bw, swell, dn = h.get("bw_height"), h.get("swell_offshore"), h.get("directness")
        if bw is None or swell is None or dn is None:
            continue
        if swell < 0.3 or dn < 0.3:
            continue
        if blocked_by_near_obstacle(h.get("dir_offshore"), spot):
            continue
        total = h.get("height_offshore")
        if total is not None and swell < 0.7 * total:
            continue
        pairs.append({"t": h["t"], "ratio": round(bw / (swell * dn), 4), "run": run_id})
    return pairs


def merge_bw_pairs(existing, new_pairs, now):
    """Behold nyeste kjøring per tidspunkt (dedup), fjern par eldre enn 30 døgn."""
    by_time = {p["t"]: p for p in existing}
    for p in new_pairs:
        by_time[p["t"]] = p
    cutoff = now - dt.timedelta(days=BW_MAX_AGE_DAYS)
    return [p for p in by_time.values() if dt.datetime.fromisoformat(p["t"].replace("Z", "+00:00")) >= cutoff]


def bw_transfer(pairs):
    """Lært transfer fra BarentsWatch, eller None hvis for få par eller for få døgn."""
    if len(pairs) < BW_MIN_PAIRS:
        return None
    days = {p["t"][:10] for p in pairs}
    if len(days) < BW_MIN_DAYS:
        return None
    return round(min(1.2, max(0.05, median(p["ratio"] for p in pairs))), 2)


def effective_transfer(spot, learned, bw_pairs):
    """Rekkefølge: 1) lært fra BarentsWatch, 2) transfer satt i spots.json,
    3) transfer_prior fra skjerming (ROADMAP oppgave I, 06.10.2026 natt - en
    geometrisk startverdi ut fra hvor åpen spoten er, bare når
    spot["shelter_factor"] er satt av fetch.py sin resolve_shelter()), 4)
    DEFAULT_TRANSFER. 26.09.2026: learn() setter ikke lenger "transfer" (se
    modul-docstringen) - "logs"-grenen under er bare igjen for at
    rekkefølgen fortsatt virker om noe skulle sette den eksternt."""
    from rating import DEFAULT_TRANSFER, transfer_prior
    if learned.get("transfer"):
        return learned["transfer"], "logs"
    bw_t = bw_transfer(bw_pairs)
    if bw_t is not None:
        return bw_t, "barentswatch"
    if spot.get("transfer") is not None:
        return spot["transfer"], "spots.json"
    if spot.get("shelter_factor") is not None:
        return transfer_prior(spot), "skjerming"
    return DEFAULT_TRANSFER, "standard"
