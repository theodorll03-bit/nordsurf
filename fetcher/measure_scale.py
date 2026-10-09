"""Måler dagens grenser for skalering (ROADMAP «Skalering til mange spots»,
planfase - bygger ingenting, endrer ingenting i varselet).

Kjøres i GitHub Actions (workflow «Mål skalering», workflow_dispatch) med de
samme hemmelighetene som «Hent varsel», fordi kildene ikke kan nås fra
skyøkten. Skriver en tabell til loggen:
1. per spot og kilde: svartid (s) og svarstørrelse (byte) for hvert kall
   henteren gjør i dag - sekvensielt, akkurat som fetch.py
2. samme kall for alle spots i parallell (4 og 8 tråder) - veggtid og om
   noen kilde svarer 429/5xx (bruksgrense)
3. tiden de rene regnedelene tar (rate() for alle timer, longrange.score_runs)

Tidsgrense: hele scriptet avbrytes etter BUDGET_S (CLAUDE.md: ingenting
uten tidsgrense). Kjør: python fetcher/measure_scale.py
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sources  # noqa: E402
import rating   # noqa: E402

BUDGET_S = 900
SPOTS = Path(__file__).parent.parent / "spots.json"
_t0 = time.time()
threading.Thread(target=lambda: (time.sleep(BUDGET_S), print("TIDSAVBRUDD", flush=True), os._exit(124)), daemon=True).start()


def timed(label, fn, *args):
    t = time.time()
    try:
        r = fn(*args)
        size = len(json.dumps(r, default=str)) if r is not None else 0
        return {"label": label, "s": round(time.time() - t, 2), "bytes": size, "status": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"label": label, "s": round(time.time() - t, 2), "bytes": 0, "status": f"feil {type(e).__name__}: {str(e)[:80]}"}


def calls_for(spot):
    s, o = spot["spot"], spot["offshore"]
    now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    calls = [
        ("met.no hav (spot)", sources.metno_ocean, s["lat"], s["lon"]),
        ("met.no hav (ute)", sources.metno_ocean, o["lat"], o["lon"]),
        ("Open-Meteo svell (ute)", sources.openmeteo_marine, o["lat"], o["lon"]),
        ("met.no vind", sources.metno_weather, s["lat"], s["lon"]),
        ("Open-Meteo GFS-vind", sources.openmeteo_wind, s["lat"], s["lon"]),
        ("Kartverket tidevann", sources.kartverket_tide, s["lat"], s["lon"], now, now + dt.timedelta(days=16)),
    ]
    if spot.get("offshore_longrange"):
        ol = spot["offshore_longrange"]
        calls.append(("Open-Meteo svell (langtid-reserve)", sources.openmeteo_marine, ol["lat"], ol["lon"]))
    if spot.get("barentswatch_point"):
        p = spot["barentswatch_point"]; calls.append(("BarentsWatch (250 m)", sources.barentswatch_point, p["lat"], p["lon"]))
    if spot.get("barentswatch_point_near"):
        p = spot["barentswatch_point_near"]; calls.append(("BarentsWatch (150 m)", sources.barentswatch_point, p["lat"], p["lon"]))
    return calls


def main():
    spots = [s for s in json.loads(SPOTS.read_text(encoding="utf-8"))["spots"] if s.get("enabled")]
    print(f"# Mål skalering - {len(spots)} spots, {dt.datetime.now(dt.timezone.utc).isoformat()}", flush=True)
    print("\n## 1. Sekvensielt, som fetch.py i dag\n")
    print("| Spot | Kilde | Tid (s) | Svar (byte) | Status |\n|---|---|---|---|---|", flush=True)
    per_source = {}
    t_seq = time.time()
    for sp in spots:
        for label, fn, *args in calls_for(sp):
            r = timed(label, fn, *args)
            per_source.setdefault(label, []).append(r)
            print(f"| {sp['name']} | {label} | {r['s']} | {r['bytes']} | {r['status']} |", flush=True)
    seq_total = time.time() - t_seq
    print(f"\nSum sekvensielt for {len(spots)} spots: {seq_total:.1f} s ({seq_total/len(spots):.1f} s per spot)\n")
    print("| Kilde | Kall | Snitt (s) | Maks (s) | Snitt svar (byte) | Feil |\n|---|---|---|---|---|---|")
    for label, rs in per_source.items():
        ok = [r for r in rs if r["status"] == "ok"]
        print(f"| {label} | {len(rs)} | {sum(r['s'] for r in rs)/len(rs):.2f} | {max(r['s'] for r in rs):.2f} | "
              f"{(sum(r['bytes'] for r in ok)/len(ok)) if ok else 0:.0f} | {len(rs)-len(ok)} |", flush=True)

    for workers in (4, 8):
        print(f"\n## 2. Parallelt, {workers} tråder (alle spots, alle kilder)\n", flush=True)
        jobs = [(sp["name"], c) for sp in spots for c in calls_for(sp)]
        t = time.time()
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            res = list(ex.map(lambda j: (j[0], timed(j[1][0], j[1][1], *j[1][2:])), jobs))
        wall = time.time() - t
        fails = [(n, r) for n, r in res if r["status"] != "ok"]
        print(f"Veggtid {wall:.1f} s for {len(jobs)} kall ({wall/len(spots):.1f} s per spot). Feil: {len(fails)}")
        for n, r in fails[:20]:
            print(f"- {n} / {r['label']}: {r['status']}")
        by = {}
        for _, r in res:
            by.setdefault(r["label"], []).append(r["s"])
        print("\n| Kilde | Snitt (s) | Maks (s) |\n|---|---|---|")
        for label, ss in by.items():
            print(f"| {label} | {sum(ss)/len(ss):.2f} | {max(ss):.2f} |", flush=True)

    print("\n## 3. Rene regnedeler (ingen nett)\n", flush=True)
    fc = Path(__file__).parent.parent / "docs/data/forecast.json"
    if fc.exists():
        d = json.loads(fc.read_text(encoding="utf-8"))
        t = time.time(); n = 0
        for sp in d["spots"]:
            for h in sp["hours"]:
                rating.rate(h, sp); n += 1
        el = time.time() - t
        print(f"rating.rate() for {n} timer ({len(d['spots'])} spots): {el:.2f} s ({el/len(d['spots'])*1000:.0f} ms per spot)")
    try:
        import longrange
        ledger = longrange.load_ledger(longrange.LEDGER)
        now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
        t = time.time()
        longrange.score_runs(now, d["spots"], [], ledger, longrange.ARCHIVE_DIR)
        print(f"longrange.score_runs(): {time.time()-t:.2f} s (arkiv: {len(list(Path(longrange.ARCHIVE_DIR).glob('*.json')))} filer)")
    except Exception as e:  # noqa: BLE001
        print(f"score_runs: hoppet over ({e})")
    print(f"\nTotalt scriptet: {time.time()-_t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
