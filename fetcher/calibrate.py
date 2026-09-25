"""Lærer av loggene: hvor stor del av svellet ute som faktisk når stranda, og om varselet bommer.
Lærer også en uavhengig transfer fra BarentsWatch, ved å sammenligne reservemodellens
inngangsverdier (svell ute * directness) mot BarentsWatch sine egne, ekte målinger."""
import datetime as dt
from statistics import median

SIZE_M = {"Flatt": 0.0, "Knehøy": 0.5, "Hoftehøy": 0.9, "Brysthøy": 1.3, "Over hodet": 2.0}
MIN_LOGS = 5

BW_MIN_PAIRS = 40  # trenger nok par før vi stoler på medianen
BW_MIN_DAYS = 3    # spredt over minst tre døgn, ikke bare én værsituasjon
BW_MAX_AGE_DAYS = 30


def learn(spot_id, logs):
    mine = [l for l in logs if l.get("spot") == spot_id]
    # Forholdet skal være toppfaktoren ved DIREKTE treff, ikke ved skrått
    # svell - del derfor på directness også. Logger uten feltet (gamle
    # logger, eller loggført før denne endringen) antas direkte (1.0).
    # Svell langt utenfor vinduet (directness under 0.3) sier lite om
    # direkte treff og ville gitt urimelig store forhold - hoppes over.
    ratios = [
        SIZE_M[l["size"]] / (l["swellOffshore"] * (l.get("directness") if l.get("directness") is not None else 1.0))
        for l in mine
        if l.get("size") in SIZE_M
        and (l.get("swellOffshore") or 0) > 0.2
        and (l.get("directness") if l.get("directness") is not None else 1.0) >= 0.3
    ]
    stars = [l["stars"] - l["forecastStars"] for l in mine if l.get("forecastStars") is not None]
    out = {"logs": len(mine), "size_logs": len(ratios)}
    if len(ratios) >= MIN_LOGS:
        out["transfer"] = round(min(1.2, max(0.05, median(ratios))), 2)
    if stars:
        out["bias"] = round(sum(stars) / len(stars), 2)
        out["hits"] = sum(1 for d in stars if abs(d) <= 1)
        out["compared"] = len(stars)
    return out


def bw_pairs_for_run(hours, run_id):
    """Kalibreringspar for denne kjøringen: bare RÅ (ikke interpolerte)
    BarentsWatch-timer der svellet ute klart dominerer bildet og retningen
    treffer godt nok til at et forhold sier noe fornuftig om direkte treff."""
    pairs = []
    for h in hours:
        if h.get("height_source") != "barentswatch" or h.get("bw_interpolated"):
            continue
        bw, swell, dn = h.get("bw_height"), h.get("swell_offshore"), h.get("directness")
        if bw is None or swell is None or dn is None:
            continue
        if swell < 0.3 or dn < 0.3:
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
    """Rekkefølge: 1) lært fra loggene dine, 2) lært fra BarentsWatch,
    3) transfer satt i spots.json, 4) DEFAULT_TRANSFER."""
    from rating import DEFAULT_TRANSFER
    if learned.get("transfer"):
        return learned["transfer"], "logs"
    bw_t = bw_transfer(bw_pairs)
    if bw_t is not None:
        return bw_t, "barentswatch"
    if spot.get("transfer") is not None:
        return spot["transfer"], "spots.json"
    return DEFAULT_TRANSFER, "standard"
