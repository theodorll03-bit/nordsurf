"""Vindmålinger fra met.no Frost (oppgave 2 / Theodors svar 07.10.2026) i
SKYGGEMODUS: hentes, lagres og sammenlignes med met.no-vinden appen bruker -
ALDRI inn i ratingen. Første stasjon: Eggum (SN85470, 5 km fra Unstad, samme
ytterkyst) - de andre spotenes kandidater (STATUS.md) legges til i STATIONS
når de er verifisert mot Frost sin stasjonsliste.

Krever FROST_CLIENT_ID i miljøet (Frost bruker client-id som brukernavn i
HTTP basic auth, tomt passord). Uten den: skriver ingenting, sier det i
loggen - manglende målinger er None, aldri 0.

Skriver:
- data/wind_obs/obs_<YYYY-MM-DD>.json: {"spot": {"<t UTC>": {"speed", "dir",
  "gust", "station"}}} - formatet testlaben (backtest.load_wind_obs(),
  variant vind_korr) leser. Samme dag-fil oppdateres (merge), aldri 0 for
  manglende element.
- data/wind_obs/compare_latest.md: per spot, time for time de siste 48
  timene: målt mot varslet (docs/data/forecast.json sin wind_speed/wind_dir
  for samme time - varselet er det som lå i fila nå, ikke varselet som
  gjaldt da), feil i retning (signert, varsel − målt) og styrke, og snitt.

Kjør: python fetcher/wind_obs.py [--days N] [--dates 2026-09-26,2026-09-28]
  --days N: de siste N døgnene (standard 2).
  --dates: enkeltdøgn i tillegg (f.eks. observasjonsdagene for Unstad), så
  testlaben får målt vind for de faste observasjonene."""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "wind_obs"
FORECAST = ROOT / "docs" / "data" / "forecast.json"
FROST = "https://frost.met.no/observations/v0.jsonld"
# spot-id -> (Frost-kilde, navn). Bare Eggum er verifisert som første steg.
STATIONS = {"unstad": ("SN85470", "Eggum")}
ELEMENTS = {"wind_speed": "speed", "wind_from_direction": "dir", "max(wind_speed_of_gust PT1H)": "gust"}
UA = {"User-Agent": f"nordsurf-wind-obs ({os.environ.get('UA_CONTACT', 'ukjent-kontakt')})"}


def frost_hours(client_id, source, day):
    """{t: {speed, dir, gust}} for ett døgn (UTC) fra én stasjon. Elementer
    som mangler i svaret blir None (aldri 0). Feil → RuntimeError med status."""
    start = dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc)
    ref = f"{start:%Y-%m-%dT%H:%M:%SZ}/{start + dt.timedelta(days=1):%Y-%m-%dT%H:%M:%SZ}"
    r = requests.get(FROST, params={"sources": source, "referencetime": ref, "elements": ",".join(ELEMENTS), "timeresolutions": "PT1H"},
                     auth=(client_id, ""), headers=UA, timeout=60)
    if r.status_code == 412:          # Frost: ingen data for valget - ikke en feil, bare tomt
        return {}
    if r.status_code != 200:
        raise RuntimeError(f"Frost {r.status_code}: {(r.text or '')[:160]}")
    out = {}
    for item in r.json().get("data", []):
        t = item.get("referenceTime", "")[:13] + ":00Z"
        row = out.setdefault(t, {"speed": None, "dir": None, "gust": None})
        for ob in item.get("observations", []):
            key = ELEMENTS.get(ob.get("elementId"))
            if key and ob.get("value") is not None:
                row[key] = float(ob["value"])
    return out


def parse_hour_key(t):
    return dt.datetime.strptime(t, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)


def write_obs(spot_id, station, hours):
    """Merger timene inn i dag-filene (én fil per UTC-døgn)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_day = {}
    for t, row in hours.items():
        by_day.setdefault(t[:10], {})[t] = {**row, "station": station}
    written = []
    for day, rows in by_day.items():
        path = OUT_DIR / f"obs_{day}.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        data.setdefault(spot_id, {}).update(rows)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        written.append(path.name)
    return written


def signed_diff(a, b):
    return ((a - b + 180) % 360) - 180


def compare(spot_id, obs, forecast_hours, max_hours=48):
    """Rader (markdown) og snitt: varsel − målt per time, de siste max_hours."""
    rows, dirs, speeds = [], [], []
    fc = {h["t"]: h for h in forecast_hours}
    for t in sorted(obs)[-max_hours:]:
        o, f = obs[t], fc.get(t)
        if not f or o.get("speed") is None or f.get("wind_speed") is None:
            continue
        dd = signed_diff(f["wind_dir"], o["dir"]) if o.get("dir") is not None and f.get("wind_dir") is not None else None
        ds = f["wind_speed"] - o["speed"]
        rows.append(f"| {t} | {o['speed']:.1f} m/s fra {o['dir']:.0f}° | {f['wind_speed']:.1f} m/s fra {f['wind_dir']:.0f}° | {dd:+.0f}° | {ds:+.1f} m/s |"
                    if dd is not None else f"| {t} | {o['speed']:.1f} m/s (retning mangler) | {f['wind_speed']:.1f} m/s fra {f.get('wind_dir')}° | – | {ds:+.1f} m/s |")
        speeds.append(ds)
        if dd is not None:
            dirs.append(dd)
    summary = (f"{len(rows)} timer: retningsfeil snitt {sum(dirs) / len(dirs):+.0f}° (|snitt| {sum(abs(x) for x in dirs) / len(dirs):.0f}°), "
               f"styrkefeil snitt {sum(speeds) / len(speeds):+.1f} m/s" if rows and dirs else f"{len(rows)} timer med felles data")
    return rows, summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--dates", default="")
    args = ap.parse_args(argv)
    client_id = os.environ.get("FROST_CLIENT_ID")
    if not client_id:
        print("FROST_CLIENT_ID mangler - ingen vindmålinger hentet (skyggemodus, ingenting skrevet)")
        return 0
    today = dt.datetime.now(dt.timezone.utc).date()
    days = [today - dt.timedelta(days=k) for k in range(args.days)]
    days += [dt.date.fromisoformat(x) for x in args.dates.split(",") if x.strip()]
    forecast = json.loads(FORECAST.read_text(encoding="utf-8")) if FORECAST.exists() else {"spots": []}
    fc_hours = {s["id"]: s["hours"] for s in forecast["spots"]}
    lines = [f"# Vindmålinger (Frost) mot met.no-varselet - {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC", "",
             "Skyggemodus: målingene brukes ikke i ratingen. Varselet er det som ligger i forecast.json nå.", ""]
    for spot_id, (source, name) in STATIONS.items():
        obs = {}
        for day in sorted(set(days)):
            try:
                obs.update(frost_hours(client_id, source, day))
            except Exception as e:
                print(f"  {name} {day}: {e}")
        if not obs:
            print(f"  {name}: ingen målinger")
            lines += [f"## {spot_id} - {name} ({source})", "", "ingen målinger hentet", ""]
            continue
        print(f"  {name}: {len(obs)} timer, skrev {write_obs(spot_id, f'{name} {source}', obs)}")
        rows, summary = compare(spot_id, obs, fc_hours.get(spot_id, []))
        lines += [f"## {spot_id} - {name} ({source})", "", summary, "", "| Time (UTC) | Målt | Varslet (met.no) | Retning varsel − målt | Styrke varsel − målt |", "|---|---|---|---|---|"] + rows + [""]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "compare_latest.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
