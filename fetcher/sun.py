"""Solhøyde uten eksterne kall. Brukbart lys = sola høyere enn 6 grader under horisonten
(borgerlig tussmørke). Det gjør at appen fungerer i mørketida."""
import math
import datetime as dt

USABLE = -6.0


def elevation(lat, lon, t: dt.datetime) -> float:
    n = t.timestamp() / 86400 + 2440587.5 - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    dec = math.asin(math.sin(eps) * math.sin(lam))
    gmst = (18.697374558 + 24.06570982441908 * n) % 24
    ha = math.radians(gmst * 15 + lon) - ra
    la = math.radians(lat)
    return math.degrees(math.asin(math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha)))


def light(lat, lon, hour_start: dt.datetime) -> str:
    """'dag', 'skumring' eller 'mørkt' for timen, målt midt i timen."""
    e = elevation(lat, lon, hour_start + dt.timedelta(minutes=30))
    if e > 0:
        return "dag"
    if e > USABLE:
        return "skumring"
    return "mørkt"


def utc_offset(t: dt.datetime) -> int:
    """Norsk tid: +2 om sommeren (siste søndag i mars til siste søndag i oktober), ellers +1."""
    def last_sunday(m):
        d = dt.datetime(t.year, m, 31, 1, tzinfo=dt.timezone.utc)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    return 2 if last_sunday(3) <= t < last_sunday(10) else 1


def light_days(lat, lon, start: dt.datetime, days=4):
    """Brukbart lys per norsk dato: {'2026-12-15': {'start': iso, 'end': iso, 'sun': bool}}."""
    out = {}
    for i in range(days):
        day0 = (start + dt.timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day0 = day0 - dt.timedelta(hours=utc_offset(day0))  # lokal midnatt i UTC
        first = last = None
        has_sun = False
        for m in range(0, 24 * 60, 10):
            t = day0 + dt.timedelta(minutes=m)
            e = elevation(lat, lon, t)
            if e > USABLE:
                first = first or t
                last = t
            has_sun = has_sun or e > 0
        key = (day0 + dt.timedelta(hours=12)).date().isoformat()
        out[key] = {"start": first.isoformat() if first else None,
                    "end": last.isoformat() if last else None, "sun": has_sun}
    return out
