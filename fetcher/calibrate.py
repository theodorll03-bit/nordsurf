"""Lærer av loggene: hvor stor del av svellet ute som faktisk når stranda, og om varselet bommer."""
from statistics import median

SIZE_M = {"Flatt": 0.0, "Knehøy": 0.5, "Hoftehøy": 0.9, "Brysthøy": 1.3, "Over hodet": 2.0}
MIN_LOGS = 5


def learn(spot_id, logs):
    mine = [l for l in logs if l.get("spot") == spot_id]
    ratios = [SIZE_M[l["size"]] / l["swellOffshore"] for l in mine
              if l.get("size") in SIZE_M and (l.get("swellOffshore") or 0) > 0.2]
    stars = [l["stars"] - l["forecastStars"] for l in mine if l.get("forecastStars") is not None]
    out = {"logs": len(mine), "size_logs": len(ratios)}
    if len(ratios) >= MIN_LOGS:
        out["transfer"] = round(min(1.2, max(0.05, median(ratios))), 2)
    if stars:
        out["bias"] = round(sum(stars) / len(stars), 2)
        out["hits"] = sum(1 for d in stars if abs(d) <= 1)
        out["compared"] = len(stars)
    return out
