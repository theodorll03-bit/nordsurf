"""Henter rådata fra kildene. Alle tider i UTC, nøkkel = 'YYYY-MM-DDTHH:00Z'."""

import os
import time
import datetime as dt
import xml.etree.ElementTree as ET

import requests

CONTACT = os.environ.get("UA_CONTACT", "ukjent-kontakt")
HEADERS = {"User-Agent": f"nordsurf/0.1 ({CONTACT})"}
TIMEOUT = 30


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
    """Bølgehøyde fra BarentsWatch for et punkt. {time: height}

    Innlogging er ferdig. Selve punkt-endepunktet må fylles inn etter at du har
    registrert klienten: åpne 'Waveforecast OpenAPI doc' på
    developer.barentswatch.no/docs/waveforecast, finn endepunktet for punktvarsel,
    og sett BW_POINT_URL (se README). Uten det brukes met.no med dreiningsregelen.
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
    r.raise_for_status()
    data = r.json()
    rows = data if isinstance(data, list) else data.get("forecast") or data.get("data") or []
    out = {}
    for row in rows:
        t = row.get("time") or row.get("forecastTime") or row.get("validTime")
        h = (
            row.get("significantWaveHeight")
            or row.get("waveHeight")
            or row.get("hs")
            or row.get("value")
        )
        if t is not None and h is not None:
            out[hour_key(parse_iso(t))] = float(h)
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
