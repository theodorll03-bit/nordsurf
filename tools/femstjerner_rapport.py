"""5-stjerners-porten («Rått») - backtest (Theodor 15.10.2026, punkt 3): alle timer i de siste 30
dagene for alle spots (én kjøring per dag fra git-historikken til docs/data/forecast.json, timene for
den dagen - historikken starter 24.09.2026) pluss dagens varsel: hvilke timer som ville fått 5, andelen
av dagslystimene (mål: under ca. 2 %), ingen på dager vi vet var dårlige (CLAUDE.md), og sideeffekten
av at fradrag nå trekkes fra 5 når Rått-svellet er der (timer som går +1).

«Gammel» rating = fetcher/rating.py på main (git show), «ny» = arbeidstreet.
Kjør: python tools/femstjerner_rapport.py --runs <mappe med YYYY-MM-DD.json> [--forecast docs/data/forecast.json]
Skriver data/backtest/femstjerner_2026-10-15.md."""
import argparse
import datetime as dt
import glob
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))
import backtest  # noqa: E402
import rating as rating_new  # noqa: E402

OSLO = ZoneInfo("Europe/Oslo")
# dager vi VET var dårlige (CLAUDE.md faste observasjoner): spot -> datoer
BAD_DAYS = {"grotfjord": {"2026-09-24", "2026-09-25", "2026-09-26", "2026-10-05"}, "lenangsoyra": {"2026-09-26"}, "farstadsanden": {"2026-10-06"}}


def load_old_rating():
    src = subprocess.run(["git", "show", "main:fetcher/rating.py"], capture_output=True, text=True, timeout=60, cwd=ROOT).stdout
    tmp = Path(tempfile.mkdtemp()) / "rating_old.py"; tmp.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("rating_old", tmp); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def oslo(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(OSLO)


def light(h):
    l = h.get("light")
    return l if l is not None else ("mørkt" if h.get("daylight") is False else "dag" if h.get("daylight") is True else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", required=True)
    ap.add_argument("--forecast", default=str(ROOT / "docs" / "data" / "forecast.json"))
    ap.add_argument("--out", default=str(ROOT / "data" / "backtest" / "femstjerner_2026-10-15.md"))
    a = ap.parse_args()
    old = load_old_rating()
    spots = backtest.load_spots()
    expo = json.loads((ROOT / "data" / "exposure_baseline.json").read_text(encoding="utf-8"))
    calib = json.loads((ROOT / "data" / "bw_calibration.json").read_text(encoding="utf-8"))
    prep = {sid: backtest.prepare_spot(sid, spots, expo, calib) for sid in spots if spots[sid].get("enabled")}
    files = sorted(glob.glob(str(Path(a.runs) / "*.json")))
    sources = [(dt.date.fromisoformat(Path(f).stem), json.loads(Path(f).read_text(encoding="utf-8")), True) for f in files]
    if Path(a.forecast).exists():
        fc = json.loads(Path(a.forecast).read_text(encoding="utf-8"))
        sources.append((None, fc, False))
    n_hours = n_light = 0
    fives, plus, minus = [], [], []
    bad_hits = []
    for day, run, only_day in sources:
        for s in run["spots"]:
            sid = s["id"]
            if sid not in prep:
                continue
            for h in s["hours"]:
                if only_day and oslo(h["t"]).date() != day:
                    continue
                n_hours += 1
                if light(h) in ("dag", "skumring"):
                    n_light += 1
                ro = old.rate(dict(h), prep[sid]); rn = rating_new.rate(dict(h), prep[sid])
                if rn["stars"] == 5:
                    fives.append((sid, h["t"], rn, h))
                    if oslo(h["t"]).date().isoformat() in BAD_DAYS.get(sid, set()):
                        bad_hits.append((sid, h["t"]))
                if rn["stars"] > ro["stars"]:
                    plus.append((sid, h["t"], ro["stars"], rn["stars"], rn))
                elif rn["stars"] < ro["stars"]:
                    minus.append((sid, h["t"], ro["stars"], rn["stars"], rn))
    out = ["# 5-stjerners-porten («Rått») - backtest", "",
           f"{len(files)} dager fra git-historikken ({Path(files[0]).stem} … {Path(files[-1]).stem}) + dagens varsel: {n_hours} timer, {n_light} i dagslys/skumring, {len(prep)} spots.", "",
           f"## Timer som ville fått 5: {len(fives)} ({100 * len(fives) / max(1, n_light):.2f} % av dagslystimene, mål under ca. 2 %)", ""]
    if fives:
        out += ["| Spot | tid | surf | periode | energi | vind | svell fra | forklaring |", "|---|---|---|---|---|---|---|---|"]
        for sid, t, r, h in fives:
            out.append(f"| {sid} | {oslo(t):%d.%m kl. %H} | {r.get('surf_height')} m | {h.get('period')} s | {h.get('energy_swell_kj') or r.get('energy_swell_kj')} kJ | {h.get('wind_speed')} m/s {r.get('wind_type')} | {h.get('dir_offshore')}° | {next((l for l in r['breakdown'] if l.startswith('Rått')), '')} |")
    else:
        out.append("Ingen timer - de tre ukene hadde ingen Rått-dag i BarentsWatch-sonen med ren vind (nærmest: Farstadsanden 20.10 kl. 10-16 i dagens varsel - feiler på sone og sidevind 3-4 m/s).")
    out += ["", f"## Kjente dårlige dager (CLAUDE.md): {len(bad_hits)} timer med 5" + (" - " + ", ".join(f"{s} {t}" for s, t in bad_hits) if bad_hits else " - ingen"), ""]
    out += [f"## Sideeffekt: fradrag trekkes fra 5 når Rått-svellet er der - {len(plus)} timer +1, {len(minus)} timer ned", ""]
    if plus:
        out += ["| Spot | tid | før → etter | hvorfor ikke 5 |", "|---|---|---|---|"]
        for sid, t, a_, b_, r in plus[:40]:
            why = next((l for l in r["breakdown"] if l.startswith(("Femte stjerne", "Vind", "Tidevann ("))), "")
            out.append(f"| {sid} | {oslo(t):%d.%m kl. %H} | {a_}★ → {b_}★ | {why} |")
    out.append("")
    md = "\n".join(out)
    Path(a.out).write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
