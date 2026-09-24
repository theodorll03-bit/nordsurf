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
import notify
import sun
import tide as tidemod
from rating import angle_diff, rate

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
OUT = ROOT / "docs" / "data" / "forecast.json"
HOURS_AHEAD = 72
REPORT = []  # kilderapport, vises i Actions


def pick(*vals):
    return next((v for v in vals if v is not None), None)


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


def build_spot(spot, now, learned):
    name = spot["name"]
    print(name)
    if learned.get("transfer"):
        spot = {**spot, "transfer": learned["transfer"]}  # lært fra loggene slår startverdien
    s, o = spot["spot"], spot["offshore"]
    ocean_spot = safe(name, "met.no hav (spot)", sources.metno_ocean, s["lat"], s["lon"])
    ocean_off = safe(name, "met.no hav (ute)", sources.metno_ocean, o["lat"], o["lon"])
    marine = safe(name, "Open-Meteo svell (ute)", sources.openmeteo_marine, o["lat"], o["lon"])
    weather = safe(name, "met.no vind", sources.metno_weather, s["lat"], s["lon"])
    swell_values = [v.get("swell_height") for v in marine.values() if v.get("swell_height") is not None]
    if marine and not swell_values:
        REPORT.append((name, "Open-Meteo svellhøyde", "tom", "havpunktet gir ingen svellhøyde, bruker met.no"))
    bw = {}
    if spot.get("barentswatch_point"):
        p = spot["barentswatch_point"]
        bw = safe(name, "BarentsWatch", sources.barentswatch_point, p["lat"], p["lon"])
    tides = safe(name, "Kartverket tidevann", sources.kartverket_tide, s["lat"], s["lon"],
                 now - dt.timedelta(hours=12), now + dt.timedelta(hours=HOURS_AHEAD + 12), default=[])

    hours = []
    for i in range(HOURS_AHEAD):
        t = now + dt.timedelta(hours=i)
        k = sources.hour_key(t)
        sp, off, mar, w = ocean_spot.get(k), ocean_off.get(k), marine.get(k), weather.get(k)
        if not sp and not mar:
            continue
        dir_off = pick((off or {}).get("dir"), (mar or {}).get("dir"))
        dir_spot = (sp or {}).get("dir")
        turn = angle_diff(dir_off, dir_spot) if dir_off is not None and dir_spot is not None else None
        light = sun.light(s["lat"], s["lon"], t)
        hour = {
            "t": k,
            "height_offshore": pick((off or {}).get("height"), (mar or {}).get("height")),
            "height_spot_model": (sp or {}).get("height"),
            "swell_offshore": (mar or {}).get("swell_height"),
            "bw_height": bw.get(k),
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

    public = {k: v for k, v in spot.items() if not k.startswith("_")}
    light_days = sun.light_days(s["lat"], s["lon"], now)
    return {**public, "hours": hours, "tide_events": tides, "calibration": learned, "light_days": light_days}


def write_report():
    lines = ["| Spot | Kilde | Status | Detaljer |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in REPORT]
    text = "\n".join(lines)
    print("\nKilderapport\n" + text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Kilderapport\n\n" + text + "\n")


def main():
    config = json.loads(SPOTS.read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    logs = safe("alle", "Loggene dine (GitHub)", sources.github_logs, default=[])
    spots = []
    for s in config["spots"]:
        if s.get("enabled"):
            spots.append(build_spot(s, now, calibrate.learn(s["id"], logs)))
    forecast = {"generated": now.isoformat(), "spots": spots,
                "notify": {k: v for k, v in notify.load_settings().items() if not k.startswith("_")}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(forecast, ensure_ascii=False), encoding="utf-8")
    print(f"Skrev {OUT}")
    notify.run(forecast, now)
    write_report()


if __name__ == "__main__":
    main()
