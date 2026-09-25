"""Henter rådata fra kildene. Alle tider i UTC, nøkkel = 'YYYY-MM-DDTHH:00Z'."""

import os
import time
import datetime as dt
import xml.etree.ElementTree as ET

import requests

CONTACT = os.environ.get("UA_CONTACT", "ukjent-kontakt")
HEADERS = {"User-Agent": f"nordsurf/0.1 ({CONTACT})"}
TIMEOUT = 45


def hour_key(ts: dt.datetime) -> str:
    ts = ts.astimezone(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    return ts.strftime("%Y-%m-%dT%H:00Z")


def parse_iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _get(url, params=None, headers=None):
    # Kildene timer av og til ut forbigående når flere spots hentes tett etter
    # hverandre (sett i Actions-kjøringer). Prøv opp til tre ganger med pause.
    last_err = None
    for attempt, wait in enumerate((0, 3, 8)):
        if wait:
            time.sleep(wait)
        try:
            r = requests.get(url, params=params, headers=headers or HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r
        except (requests.Timeout, requests.ConnectionError) as e:
            last_err = e
    raise last_err


# ---------- met.no ----------

def metno_ocean(lat, lon):
    """Bølgehøyde, retning og vanntemp. {time: {...}}"""
    r = _get(
        "https://api.met.no/weatherapi/oceanforecast/2.0/complete",
        {"lat": round(lat, 4), "lon": round(lon, 4)},
    )
    out = {}
    for step in r.json()["properties"]["timeseries"]:
        d = step["data"]["instant"]["details"]
        out[hour_key(parse_iso(step["time"]))] = {
            "height": d.get("sea_surface_wave_height"),
            "dir": d.get("sea_surface_wave_from_direction"),
            "water_temp": d.get("sea_water_temperature"),
        }
    return out


def metno_weather(lat, lon):
    """Vind, kast og lufttemp. {time: {...}}"""
    r = _get(
        "https://api.met.no/weatherapi/locationforecast/2.0/complete",
        {"lat": round(lat, 4), "lon": round(lon, 4)},
    )
    out = {}
    for step in r.json()["properties"]["timeseries"]:
        d = step["data"]["instant"]["details"]
        out[hour_key(parse_iso(step["time"]))] = {
            "wind_speed": d.get("wind_speed"),
            "wind_dir": d.get("wind_from_direction"),
            "gust": d.get("wind_speed_of_gust"),
            "air_temp": d.get("air_temperature"),
        }
    return out


def metno_sun(lat, lon, date: dt.date):
    """Soloppgang og solnedgang. None i mørketid eller midnattssol."""
    r = _get(
        "https://api.met.no/weatherapi/sunrise/3.0/sun",
        {"lat": round(lat, 4), "lon": round(lon, 4), "date": date.isoformat(), "offset": "+00:00"},
    )
    p = r.json()["properties"]
    rise = (p.get("sunrise") or {}).get("time")
    set_ = (p.get("sunset") or {}).get("time")
    noon_elev = ((p.get("solarnoon") or {}).get("disc_centre_elevation"))
    return {"rise": rise, "set": set_, "noon_elevation": noon_elev}


# ---------- Open-Meteo (periode og offshore-svell) ----------

def openmeteo_marine(lat, lon):
    r = _get(
        "https://marine-api.open-meteo.com/v1/marine",
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": "wave_height,wave_direction,wave_period,swell_wave_height,"
            "swell_wave_direction,swell_wave_peak_period",
            "timezone": "GMT",
            "forecast_days": 5,
        },
    )
    h = r.json()["hourly"]
    out = {}
    for i, t in enumerate(h["time"]):
        key = t + "Z" if len(t) == 16 else t
        key = key[:13] + ":00Z"
        period = h["swell_wave_peak_period"][i] or h["wave_period"][i]
        out[key] = {
            "height": h["wave_height"][i],          # total: svell + vindsjø
            "swell_height": h["swell_wave_height"][i],  # bare svellet
            "dir": h["swell_wave_direction"][i] or h["wave_direction"][i],
            "period": period,
        }
    return out


# ---------- Kartverket (tidevann) ----------

def kartverket_tide(lat, lon, start: dt.datetime, end: dt.datetime):
    """Flo og fjære. Liste med {time, type, cm}. Tom liste hvis noe feiler."""
    try:
        r = _get(
            "https://vannstand.kartverket.no/tideapi.php",
            {
                "lat": lat,
                "lon": lon,
                "fromtime": start.strftime("%Y-%m-%dT%H:%M"),
                "totime": end.strftime("%Y-%m-%dT%H:%M"),
                "datatype": "tab",
                "refcode": "cd",
                "lang": "nb",
                "tide_request": "locationdata",
            },
        )
        root = ET.fromstring(r.content)
        out = []
        for wl in root.iter("waterlevel"):
            out.append(
                {
                    "time": parse_iso(wl.get("time")).astimezone(dt.timezone.utc).isoformat(),
                    "type": "flo" if wl.get("flag") == "high" else "fjære",
                    "cm": round(float(wl.get("value"))),
                }
            )
        return out
    except Exception as e:  # tidevann er fint å ha, ikke kritisk
        print(f"  tidevann feilet: {e}")
        return []


# ---------- BarentsWatch ----------

_bw_token = None


def barentswatch_token():
    global _bw_token
    if _bw_token:
        return _bw_token
    cid = os.environ.get("BW_CLIENT_ID")
    secret = os.environ.get("BW_CLIENT_SECRET")
    if not cid or not secret:
        return None
    r = requests.post(
        "https://id.barentswatch.no/connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": secret,
            "scope": "api",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    _bw_token = r.json()["access_token"]
    return _bw_token


def barentswatch_point(lat, lon):
    """Bølgehøyde, retning og periode fra BarentsWatch for et punkt, i
    tretimersteg opp til ca 60 timer frem. {time: {"height","dir","period"}}

    Bruker /v1/waveforecastpoint/nearest/all (se Waveforecast OpenAPI doc).
    BW_POINT_URL (se README) må ha ?x={lon}&y={lat} - x er lengdegrad, y er
    breddegrad. Uten BW_POINT_URL/token brukes reservemodellen.
    """
    url = os.environ.get("BW_POINT_URL")
    token = barentswatch_token()
    if not url or not token:
        return {}
    r = requests.get(
        url.format(lat=lat, lon=lon),
        headers={**HEADERS, "Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    if os.environ.get("BW_DEBUG"):
        print(f"  DEBUG bw {lat},{lon}: status={r.status_code} body={r.text[:400]!r}")
    if r.status_code == 204:  # ingen data for dette punktet
        return {}
    r.raise_for_status()
    data = r.json()
    rows = data if isinstance(data, list) else data.get("forecast") or data.get("data") or []
    out = {}
    for row in rows:
        if "totalMeanWaveDirection" in row and row.get("totalMeanWaveDirection") is None:
            continue  # modellen har ingen data for denne timen (sett som h=0.0, dir=None, period~1.2s)
        t = row.get("forecastTime") or row.get("time") or row.get("validTime")
        h = next(
            (
                row[k]
                for k in ("totalSignificantWaveHeight", "significantWaveHeight", "waveHeight", "hs", "value")
                if row.get(k) is not None
            ),
            None,
        )  # 0.0 (flatt hav) er en gyldig verdi, ikke "mangler" - "or" ville feilaktig hoppet videre
        if t is None or h is None:
            continue
        d = row.get("totalMeanWaveDirection")
        p = row.get("totalPeakPeriod")
        out[hour_key(parse_iso(t))] = {
            "height": float(h),
            "dir": float(d) if d is not None else None,
            "period": float(p) if p is not None else None,
        }
    return out


def _lerp(a, b, frac):
    if a is None or b is None:
        return None
    return a + (b - a) * frac


def _lerp_circular(a, b, frac):
    """Korteste vei rundt 0/360 grader, f.eks 350 -> 10 midt mellom gir 0, ikke 180."""
    if a is None or b is None:
        return None
    diff = ((b - a + 180) % 360) - 180
    return (a + diff * frac) % 360


def bw_interpolate(raw):
    """Fyller BarentsWatch sine tretimerspunkter (fra barentswatch_point) til
    én verdi per hele time. Høyde og periode: lineær interpolasjon. Retning:
    sirkulær. Interpolerer bare mellom punkter maks 3 timer fra hverandre -
    mangler et punkt midt i serien, står timene i hullet uten BarentsWatch.
    Ekstrapolerer aldri forbi første/siste punkt. {time: {height,dir,period,interpolated}}
    """
    if not raw:
        return {}
    times = sorted(raw)
    out = {t: {**raw[t], "interpolated": False} for t in times}
    for t0, t1 in zip(times, times[1:]):
        d0, d1 = parse_iso(t0), parse_iso(t1)
        gap = round((d1 - d0).total_seconds() / 3600)
        if not (0 < gap <= 3):
            continue  # hull i serien - ikke fyll, og ikke ekstrapoler
        v0, v1 = raw[t0], raw[t1]
        for step in range(1, gap):
            frac = step / gap
            tk = hour_key(d0 + dt.timedelta(hours=step))
            out[tk] = {
                "height": _lerp(v0.get("height"), v1.get("height"), frac),
                "dir": _lerp_circular(v0.get("dir"), v1.get("dir"), frac),
                "period": _lerp(v0.get("period"), v1.get("period"), frac),
                "interpolated": True,
            }
    return out


# ---------- Loggene dine (privat GitHub-repo) ----------

def github_logs():
    """Leser logs.json fra det private repoet appen synker til. Tom liste hvis ikke satt opp."""
    repo = os.environ.get("LOGS_REPO")
    token = os.environ.get("LOGS_TOKEN")
    if not repo or not token:
        return []
    r = requests.get(
        f"https://api.github.com/repos/{repo}/contents/logs.json",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json",
                 "User-Agent": HEADERS["User-Agent"]},
        timeout=TIMEOUT,
    )
    if r.status_code == 404:
        return []
    r.raise_for_status()
    data = r.json()
    deleted = set(data.get("deleted", []))
    return [l for l in data.get("logs", []) if l.get("id") not in deleted]
