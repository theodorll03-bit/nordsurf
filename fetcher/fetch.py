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
BW_CALIB = ROOT / "data" / "bw_calibration.json"
HOURS_AHEAD_MAX = 120  # 5 døgn, men stopper ved kortest tilgjengelige kilde
REPORT = []  # kilderapport, vises i Actions


def pick(*vals):
    return next((v for v in vals if v is not None), None)


def _hours_available(source_dict, now):
    """Timer fra now til siste tilgjengelige tidspunkt i kilden. 0 hvis tom."""
    if not source_dict:
        return 0
    last = sources.parse_iso(max(source_dict))
    return max(0, int((last - now).total_seconds() // 3600) + 1)


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


def build_spot(spot, now, learned, bw_calib, run_id):
    name = spot["name"]
    print(name)
    s, o = spot["spot"], spot["offshore"]
    ocean_spot = safe(name, "met.no hav (spot)", sources.metno_ocean, s["lat"], s["lon"])
    ocean_off = safe(name, "met.no hav (ute)", sources.metno_ocean, o["lat"], o["lon"])
    marine = safe(name, "Open-Meteo svell (ute)", sources.openmeteo_marine, o["lat"], o["lon"])
    weather = safe(name, "met.no vind", sources.metno_weather, s["lat"], s["lon"])
    swell_values = [v.get("swell_height") for v in marine.values() if v.get("swell_height") is not None]
    if marine and not swell_values:
        REPORT.append((name, "Open-Meteo svellhøyde", "tom", "havpunktet gir ingen svellhøyde, bruker met.no"))

    bw_raw = {}
    if spot.get("barentswatch_point"):
        p = spot["barentswatch_point"]
        bw_raw = safe(name, "BarentsWatch", sources.barentswatch_point, p["lat"], p["lon"])
    bw_hourly = sources.bw_interpolate(bw_raw)
    bw_until = max(bw_raw) if bw_raw else None
    if bw_raw:
        REPORT.append((name, "BarentsWatch periode", "ok", f"{min(bw_raw)} -> {max(bw_raw)}, bw_until {bw_until}"))

    horizon = min(HOURS_AHEAD_MAX, _hours_available(marine, now), _hours_available(weather, now))
    REPORT.append((name, "Horisont", "ok", f"{horizon} timer"))

    tides = safe(name, "Kartverket tidevann", sources.kartverket_tide, s["lat"], s["lon"],
                 now - dt.timedelta(hours=12), now + dt.timedelta(hours=HOURS_AHEAD_MAX + 12), default=[])

    # Effektiv transfer for reserven brukes med kalibreringshistorikk FRA FØR
    # denne kjøringen - nye par fra akkurat nå legges til historikken lenger
    # ned og gjelder først fra neste kjøring (unngår sirkularitet: parene
    # bygges av bw_height/svell/directness og trenger ikke selve transferen).
    bw_pairs_existing = bw_calib.get(spot["id"], [])
    transfer_value, transfer_source = calibrate.effective_transfer(spot, learned, bw_pairs_existing)
    spot = {**spot, "transfer": transfer_value}

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

    new_pairs = calibrate.bw_pairs_for_run(hours, run_id)
    merged_pairs = calibrate.merge_bw_pairs(bw_pairs_existing, new_pairs, now)
    bw_calib[spot["id"]] = merged_pairs
    bw_days = len({p["t"][:10] for p in merged_pairs})

    public = {k: v for k, v in spot.items() if not k.startswith("_")}
    light_days = sun.light_days(s["lat"], s["lon"], now)
    calibration = {
        **learned,
        "transfer_logs": learned.get("transfer"),
        "transfer_bw": calibrate.bw_transfer(merged_pairs),
        "bw_pairs": len(merged_pairs),
        "bw_days": bw_days,
        "transfer_used": transfer_value,
        "transfer_source": transfer_source,
    }
    return {**public, "hours": hours, "tide_events": tides, "bw_until": bw_until,
            "calibration": calibration, "light_days": light_days}


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
    run_id = now.isoformat()
    logs = safe("alle", "Loggene dine (GitHub)", sources.github_logs, default=[])
    bw_calib = json.loads(BW_CALIB.read_text(encoding="utf-8")) if BW_CALIB.exists() else {}
    spots = []
    for s in config["spots"]:
        if s.get("enabled"):
            spots.append(build_spot(s, now, calibrate.learn(s["id"], logs), bw_calib, run_id))
    forecast = {"generated": now.isoformat(), "spots": spots,
                "notify": {k: v for k, v in notify.load_settings().items() if not k.startswith("_")}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(forecast, ensure_ascii=False), encoding="utf-8")
    print(f"Skrev {OUT}")
    BW_CALIB.parent.mkdir(parents=True, exist_ok=True)
    BW_CALIB.write_text(json.dumps(bw_calib, ensure_ascii=False, indent=1), encoding="utf-8")
    notify.run(forecast, now)
    write_report()


if __name__ == "__main__":
    main()
