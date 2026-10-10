"""S1 (ROADMAP oppgave S): måler Open-Meteo alene, per HTTP-kall.

Spørsmålene (Theodor 10.10.2026): hvor ofte henger ett kall med DELT frist
(5 s oppkobling, 20 s svar) mot dagens 45 s; gir flere punkter i samme kall
samme tall som ett punkt om gangen; og hvordan oppfører det seg parallelt.
Bygger ingenting i henteren. Kjøres i Actions («Mål Open-Meteo»), fordi
Open-Meteo ikke kan nås fra skyøkten. Budsjett 13 min (hardkill).

Kjør: python fetcher/measure_openmeteo.py
"""
import concurrent.futures as cf
import json
import os
import sys
import threading
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import sources  # noqa: E402

BUDGET_S = 780
SPOTS = Path(__file__).parent.parent / "spots.json"
MARINE = "https://marine-api.open-meteo.com/v1/marine"
WIND = "https://api.open-meteo.com/v1/forecast"
HOURLY_MARINE = ("wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_direction,"
                 "swell_wave_period,swell_wave_peak_period,secondary_swell_wave_height,"
                 "secondary_swell_wave_direction,secondary_swell_wave_period")
HOURLY_WIND = "wind_speed_10m,wind_direction_10m,wind_gusts_10m,temperature_2m"
_t0 = time.time()
threading.Thread(target=lambda: (time.sleep(BUDGET_S), print("TIDSAVBRUDD", flush=True), os._exit(124)), daemon=True).start()


def once(url, params, timeout):
    """Ett forsøk, ingen gjentak. Returnerer (status, sekunder, json|None)."""
    t = time.time()
    try:
        r = requests.get(url, params=params, headers=sources.HEADERS, timeout=timeout)
        r.raise_for_status()
        return "ok", time.time() - t, r.json()
    except requests.Timeout:
        return "tidsavbrudd", time.time() - t, None
    except requests.ConnectionError as e:
        return f"tilkobling: {str(e)[:60]}", time.time() - t, None
    except requests.HTTPError as e:
        return f"http {e.response.status_code if e.response is not None else '?'}", time.time() - t, None


def marine_params(lats, lons, model):
    p = {"latitude": ",".join(str(x) for x in lats), "longitude": ",".join(str(x) for x in lons),
         "hourly": HOURLY_MARINE, "timezone": "GMT", "forecast_days": 16}
    if model:
        p["models"] = model
    return p


def wind_params(lats, lons):
    return {"latitude": ",".join(str(x) for x in lats), "longitude": ",".join(str(x) for x in lons),
            "hourly": HOURLY_WIND, "wind_speed_unit": "ms", "timezone": "GMT", "forecast_days": 16,
            "models": sources.OPENMETEO_WIND_MODEL}


def main():
    spots = [s for s in json.loads(SPOTS.read_text(encoding="utf-8"))["spots"] if s.get("enabled")]
    off = [(s["name"], s["offshore"]["lat"], s["offshore"]["lon"]) for s in spots]
    near = [(s["name"], s["spot"]["lat"], s["spot"]["lon"]) for s in spots]
    calls = []
    for n, la, lo in off:
        calls.append((n, "GFS Wave", MARINE, marine_params([la], [lo], sources.OPENMETEO_SWELL_MODEL)))
        calls.append((n, "standard", MARINE, marine_params([la], [lo], None)))
    for n, la, lo in near:
        calls.append((n, "GFS-vind", WIND, wind_params([la], [lo])))
    print(f"# Mål Open-Meteo - {len(spots)} spots, {len(calls)} enkeltkall per runde", flush=True)

    # 1. sekvensielt, ETT forsøk per kall, delt frist (5 s oppkobling, 20 s svar)
    print("\n## 1. Sekvensielt, ett forsøk per kall, frist (5, 20) s\n\n| Spot | Kall | Status | Tid (s) |\n|---|---|---|---|", flush=True)
    single = {}
    stats = {}
    for n, kind, url, params in calls:
        st, el, js = once(url, params, (5, 20))
        single[(n, kind)] = js
        stats.setdefault(kind, []).append((st, el))
        print(f"| {n} | {kind} | {st} | {el:.1f} |", flush=True)
    print("\n| Kall | Forsøk | ok | tidsavbrudd | annet | Snitt ok (s) |\n|---|---|---|---|---|---|")
    for kind, rs in stats.items():
        ok = [e for s_, e in rs if s_ == "ok"]
        print(f"| {kind} | {len(rs)} | {len(ok)} | {sum(1 for s_, _ in rs if s_ == 'tidsavbrudd')} | "
              f"{sum(1 for s_, _ in rs if s_ not in ('ok', 'tidsavbrudd'))} | {(sum(ok)/len(ok)) if ok else 0:.2f} |", flush=True)
    print(f"\nTid så langt: {time.time()-_t0:.0f} s", flush=True)

    # 2. flere punkter i samme kall (alle havpunkt i ett), inntil 3 forsøk, samme frist
    print("\n## 2. Flere punkter i samme kall\n", flush=True)
    batch = {}
    for kind, url, params in (
        ("GFS Wave", MARINE, marine_params([la for _, la, _ in off], [lo for _, _, lo in off], sources.OPENMETEO_SWELL_MODEL)),
        ("standard", MARINE, marine_params([la for _, la, _ in off], [lo for _, _, lo in off], None)),
        ("GFS-vind", WIND, wind_params([la for _, la, _ in near], [lo for _, _, lo in near])),
    ):
        for attempt in range(3):
            st, el, js = once(url, params, (5, 30))
            print(f"- {kind}, {len(off)} punkter i ett kall, forsøk {attempt+1}: {st}, {el:.1f} s, "
                  f"{len(json.dumps(js)) if js else 0} byte", flush=True)
            if st == "ok":
                batch[kind] = js
                break
    # sammenlign tallene med enkeltkallene for samme punkt
    print("\n| Kall | Punkt | Samme rutenettpunkt? | Identiske timeverdier? |\n|---|---|---|---|")
    for kind, pts in (("GFS Wave", off), ("standard", off), ("GFS-vind", near)):
        arr = batch.get(kind)
        if not isinstance(arr, list):
            print(f"| {kind} | - | samlekall feilet eller ga ikke liste | - |")
            continue
        for i, (n, la, lo) in enumerate(pts):
            s1 = single.get((n, kind))
            if s1 is None or i >= len(arr):
                print(f"| {kind} | {n} | enkeltkall mangler | - |")
                continue
            b = arr[i]
            same_pt = (abs(b.get("latitude", 0) - s1.get("latitude", 0)) < 1e-6 and abs(b.get("longitude", 0) - s1.get("longitude", 0)) < 1e-6)
            same_vals = b.get("hourly") == s1.get("hourly")
            print(f"| {kind} | {n} | {'ja' if same_pt else 'NEI'} ({b.get('latitude')},{b.get('longitude')} mot {s1.get('latitude')},{s1.get('longitude')}) | {'ja' if same_vals else 'NEI'} |", flush=True)
    # hvor mange av havpunktene deler Open-Meteo sitt eget rutenettpunkt?
    for kind in ("GFS Wave", "standard"):
        arr = batch.get(kind)
        if isinstance(arr, list):
            pts = {(round(b.get("latitude", 0), 4), round(b.get("longitude", 0), 4)) for b in arr}
            print(f"- {kind}: {len(arr)} havpunkt → {len(pts)} unike rutenettpunkt hos Open-Meteo", flush=True)
    print(f"\nTid så langt: {time.time()-_t0:.0f} s", flush=True)

    # 3. parallelt, 4 tråder, ett forsøk per kall, delt frist
    print("\n## 3. Parallelt, 4 tråder, ett forsøk per kall, frist (5, 20) s\n", flush=True)
    t = time.time()
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(lambda c: (c[0], c[1], once(c[2], c[3], (5, 20))), calls))
    wall = time.time() - t
    oks = [r for r in res if r[2][0] == "ok"]
    print(f"Veggtid {wall:.1f} s for {len(calls)} kall; ok {len(oks)}, tidsavbrudd {sum(1 for r in res if r[2][0]=='tidsavbrudd')}, "
          f"annet {sum(1 for r in res if r[2][0] not in ('ok','tidsavbrudd'))}; snitt ok {sum(r[2][1] for r in oks)/len(oks) if oks else 0:.2f} s", flush=True)
    for n, kind, (st, el, _) in res:
        if st != "ok":
            print(f"- {n} / {kind}: {st} etter {el:.1f} s")
    print(f"\nTotalt scriptet: {time.time()-_t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
