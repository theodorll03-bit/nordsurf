"""Skyggerapport for BarentsWatch-punktene (Theodor 15.10.2026, skyggemodus 14 dager):
for hver spot sammenlignes surfehøyden fra dagens punkt (i bruk) med surfehøyden fra
snittregelens punkt (skyggepunktet) - time for time fra arkivet (data/forecast_archive/,
[stjerner, surf, surf_skygge, surf_skygge_uten_prior] per time fra 15.10.2026) - og mot
logger (sources.github_logs(), bare i Actions med LOGS_REPO/LOGS_TOKEN) og benchmarks
(data/benchmarks.json) etter hvert som de kommer: for hvert observasjonstidspunkt hentes
begge surfehøydene fra den siste kjøringen før tidspunktet, og avviket mot observert
størrelse (calibrate.SIZE_M) vises. Unstad: også uten surf_factor_prior.

Bare rapport - endrer ingenting. Skriver data/backtest/skygge_latest.md.
Kjør: python tools/skygge_rapport.py"""
import datetime as dt
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))
import calibrate  # noqa: E402
import sources  # noqa: E402

ARCHIVE = ROOT / "data" / "forecast_archive"
OUT = ROOT / "data" / "backtest" / "skygge_latest.md"
BENCH = ROOT / "data" / "benchmarks.json"


def fm(v, nd=2):
    return "–" if v is None else f"{v:.{nd}f}".replace(".", ",")


def load_runs():
    runs = []
    for f in sorted(glob.glob(str(ARCHIVE / "*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        runs.append((dt.datetime.fromisoformat(d["issued"]), d["spots"]))
    return runs


def main():
    runs = load_runs()
    spots = {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
    out = [f"# Skyggemodus for BarentsWatch-punktene - {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC", "",
           f"{len(runs)} kjøringer i arkivet. Skyggeverdier finnes fra 15.10.2026 (kjøringer uten dem telles ikke).", ""]
    # ---- 1. time for time, per spot ----
    out += ["## 1. Surfehøyde fra dagens punkt mot skyggepunktet (alle arkiverte timer der i bruk kom fra BarentsWatch)", "",
            "Små dager: skyggen under 1,5 m surf; store: 1,5 m og over (forholdet mellom punktene er tilstandsavhengig - brytesone bare på store dager).", "",
            "| Spot | timer | i bruk flatt, skygge ikke | små dager: median skygge/i bruk (n) | store dager: median (n) | skygge ≥ 1 stjerne mer | uten prior, store dager (Unstad) |", "|---|---|---|---|---|---|---|"]
    for sid, sp in spots.items():
        if not sp.get("enabled") or not sp.get("barentswatch_point_shadow"):
            continue
        pairs, flat, more, nop = [], 0, 0, []
        for issued, data in runs:
            for t, v in (data.get(sid) or {}).items():
                if len(v) < 3 or v[2] is None or v[1] is None:
                    continue
                if len(v) > 5 and v[5] == 0:
                    continue   # i bruk kom fra reservemodellen den timen - epler mot pærer
                if v[1] <= 0 and v[2] > 0:
                    flat += 1   # brytesone-timene: stranda «flat» i bruk, skyggen ikke
                pairs.append((v[1], v[2]))
                if len(v) > 3 and v[3] is not None and v[2] >= 1.5:
                    nop.append(v[3] / v[2] if v[2] else None)
                if len(v) > 4 and v[4] is not None and v[0] is not None and v[4] >= v[0] + 1:
                    more += 1
        if not pairs:
            out.append(f"| {sid} | 0 | – | – | – | – | – |"); continue
        def med(xs):
            xs = sorted(x for x in xs if x is not None); return (xs[len(xs) // 2] if xs else None), len(xs)
        small = [b / a for a, b in pairs if a and a > 0 and b < 1.5]
        large = [b / a for a, b in pairs if a and a > 0 and b >= 1.5]
        ms, ns = med(small); ml, nl = med(large); mn, nn = med(nop)
        rolle = " (rollene snudd: skyggen er nålen i brytesonen)" if sid == "farstadsanden" else ""
        out.append(f"| {sid}{rolle} | {len(pairs)} | {flat} | {fm(ms)} ({ns}) | {fm(ml)} ({nl}) | {more} | {fm(mn) + ' × skygge (' + str(nn) + ')' if nn else '–'} |")
    out.append("")
    # ---- 2. mot logger og benchmarks ----
    logs = []
    try:
        logs = sources.github_logs()
    except Exception as e:  # noqa: BLE001
        out.append(f"Logger kunne ikke leses: {e}")
    bench = json.loads(BENCH.read_text(encoding="utf-8")) if BENCH.exists() else {}
    obs = []
    for l in logs:
        if l.get("spot") in spots and l.get("t") and l.get("size") in calibrate.SIZE_M:
            obs.append((l["spot"], l["t"], calibrate.SIZE_M[l["size"]], f"logg ({l.get('type', '?')})"))
    for b in (bench.get("benchmarks") or bench.get("items") or []) if isinstance(bench, dict) else []:
        if b.get("spot") in spots and b.get("t") and b.get("surf_height_m") is not None:
            obs.append((b["spot"], b["t"], b["surf_height_m"], f"benchmark ({b.get('source', '?')})"))
    out += ["## 2. Mot logger og benchmarks (siste kjøring før tidspunktet)", ""]
    if not obs:
        out.append("Ingen logger/benchmarks tilgjengelig her (loggene leses bare i Actions med LOGS_REPO/LOGS_TOKEN; benchmarks i data/benchmarks.json).")
    else:
        out += ["| Spot | tid | observert | i bruk | skygge | uten prior | nærmest | kilde |", "|---|---|---|---|---|---|---|---|"]
        for sid, t, size_m, src in sorted(obs, key=lambda x: x[1]):
            tt = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
            key = tt.strftime("%Y-%m-%dT%H:00Z")
            best = None
            for issued, data in runs:
                if issued <= tt and key in (data.get(sid) or {}):
                    best = data[sid][key]
            if not best or len(best) < 3:
                out.append(f"| {sid} | {t} | {fm(size_m)} m | – | – | – | – | {src} |"); continue
            a, b, c = best[1], best[2], (best[3] if len(best) > 3 else None)
            cands = [(abs(a - size_m), "i bruk") if a is not None else None, (abs(b - size_m), "skygge") if b is not None else None, (abs(c - size_m), "skygge uten prior") if c is not None else None]
            cands = [x for x in cands if x]
            near = min(cands)[1] if cands else "–"
            out.append(f"| {sid} | {t} | {fm(size_m)} m | {fm(a)} m | {fm(b)} m | {fm(c)} m | {near} | {src} |")
    out.append("")
    out.append("Ingen spot flyttes før Theodor sier ja for akkurat den spoten. Unstad: om surf_factor_prior fjernes ved flytting avgjøres av små/store-delingen over (ROADMAP). Se etter: (1) Unstad - er forholdet ca. 1 på små dager? Da er prioren ikke et brytesone-artefakt. (2) Steinkrøssa - timer der skyggen gir stjerner mens stranda er flat tyder på at punktet ligger utenfor skjermingen. (3) Andelen timer der skyggepunktet mangler tall mens i bruk har.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
