"""Farstadsanden 15.10.2026 (Theodors oppgave, del 5): tabeller til PR-en.

1. Farstadsanden 15.10 kl. 10-18, time for time, fire scenarioer: nå (gammelt
   punkt, gammel vind), bare nytt BarentsWatch-punkt, bare ny vind (sektor og
   regel), begge. Surfehøyde, sett, stjerner, ord og vindtype. Kl. 17-18 mot
   observasjonen (Martin: hodehøyt til godt over hodet, 4-5 stjerner).
2. Alle timer de siste 14 dagene for alle spots (én kjøring per dag fra git-
   historikken til docs/data/forecast.json, timene for den dagen): antall
   timer som endres med -1, +1 og +2 eller mer, og de 10 største endringene
   med forklaring (vindlinja i breakdown før og etter).
3. Kontroll: timer med onshore over 10 m/s og periode under 9 s skal fortsatt
   ha 0-1 stjerner - unntakene listes.

«Gammel» rating = fetcher/rating.py og spots.json på main (git show), «ny» =
arbeidstreet. BarentsWatch-punktet kan bare byttes for timene snittet dekker
(data/bw_point_search/result.json, 3-timers verdier - timene imellom
interpoleres lineært, timer før første snittverdi får «–»).

Kjør: python tools/farstad_rapport.py --forecast <forecast.json> --runs <mappe med YYYY-MM-DD.json>
Skriver data/backtest/farstad_2026-10-15.md."""
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
SID = "farstadsanden"
NEW_POINT_LABEL = "snitt 900m@310"
STAR_WORDS = ["Flatt", "Dårlig", "Ok", "Bra", "Veldig bra", "Rått"]
LOW = {"flat": "Flatt", "blown_out": "Blåst ut", "stormsjo": "Stormsjø", "treffer_ikke": "Treffer ikke"}
WT = {"offshore": "offshore", "side": "sidevind", "sideonshore": "side-onshore", "onshore": "onshore", None: "–"}


def git_show(path):
    return subprocess.run(["git", "show", f"main:{path}"], capture_output=True, text=True, timeout=60, cwd=ROOT).stdout


def load_old_rating():
    src = git_show("fetcher/rating.py")
    tmp = Path(tempfile.mkdtemp()) / "rating_old.py"
    tmp.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("rating_old", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prepared(spots_json, sid):
    spots = {s["id"]: s for s in spots_json["spots"]}
    exposure = json.loads((ROOT / "data" / "exposure_baseline.json").read_text(encoding="utf-8"))
    calib = json.loads((ROOT / "data" / "bw_calibration.json").read_text(encoding="utf-8")) if (ROOT / "data" / "bw_calibration.json").exists() else {}
    return backtest.prepare_spot(sid, spots, exposure, calib)


def word(r):
    if not r.get("stars"):
        return LOW.get(r.get("low_reason"), "Flatt")
    return STAR_WORDS[min(5, r["stars"])]


def fm(v, nd=1):
    return "–" if v is None else f"{v:.{nd}f}".replace(".", ",")


def oslo(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(OSLO)


def new_point_hours(transect):
    """{t_utc: {height,max,period,dir}} for det nye punktet, med lineær interpolasjon mellom 3-timers verdiene."""
    p = transect["spots"][SID]["points"][NEW_POINT_LABEL]["hours"]
    keys = sorted(p)
    out = {}
    for a, b in zip(keys, keys[1:]):
        ta, tb = dt.datetime.fromisoformat(a.replace("Z", "+00:00")), dt.datetime.fromisoformat(b.replace("Z", "+00:00"))
        n = int((tb - ta).total_seconds() // 3600)
        for k in range(n):
            f = k / n
            t = ta + dt.timedelta(hours=k)
            va, vb = p[a], p[b]
            def lerp(x, y):
                return None if x is None or y is None else x + (y - x) * f
            da, db = va.get("dir"), vb.get("dir")
            d = None if da is None or db is None else (da + ((db - da + 180) % 360 - 180) * f) % 360
            out[t.strftime("%Y-%m-%dT%H:%MZ")] = {"height": lerp(va.get("height"), vb.get("height")), "max": lerp(va.get("max_height"), vb.get("max_height")),
                                                  "period": lerp(va.get("period"), vb.get("period")), "dir": d, "exact": k == 0}
    last = keys[-1]; out[last] = {"height": p[last].get("height"), "max": p[last].get("max_height"), "period": p[last].get("period"), "dir": p[last].get("dir"), "exact": True}
    return out


def with_new_point(hour, np):
    v = np.get(hour["t"])
    if not v or v["height"] is None:
        return None
    h = dict(hour)
    h["bw_height"] = v["height"]; h["bw_height_max"] = v["max"]; h["bw_period"] = v["period"]
    h["bw_dir"] = v["dir"]; h["bw_dir_raw"] = None if v["dir"] is None else (v["dir"] + 180) % 360
    h["bw_interpolated"] = not v["exact"]
    return h


def wind_line(r):
    return next((l for l in r.get("breakdown", []) if l.startswith("Vind")), "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--forecast", default=str(ROOT / "docs" / "data" / "forecast.json"))
    ap.add_argument("--runs", required=True, help="mappe med én forecast.json per dag (YYYY-MM-DD.json)")
    ap.add_argument("--out", default=str(ROOT / "data" / "backtest" / "farstad_2026-10-15.md"))
    a = ap.parse_args()
    rating_old = load_old_rating()
    spots_old = json.loads(git_show("spots.json"))
    spots_new = json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))
    fc = json.loads(Path(a.forecast).read_text(encoding="utf-8"))
    transect = json.loads((ROOT / "data" / "bw_point_search" / "result.json").read_text(encoding="utf-8"))
    np_hours = new_point_hours(transect)
    out = [f"# Farstadsanden 15.10.2026: punkt, vind og tabeller (varsel {fc['generated'][:16]}Z)", ""]

    # ---------- 1. fire scenarioer ----------
    f_old, f_new = prepared(spots_old, SID), prepared(spots_new, SID)
    fsp = next(s for s in fc["spots"] if s["id"] == SID)
    hours = [h for h in fsp["hours"] if oslo(h["t"]).date() == dt.date(2026, 10, 15) and 10 <= oslo(h["t"]).hour <= 18]
    # timene dagens kjøring ikke har (kjøringen fra kl. 15Z starter kl. 17): fra nærmeste eldre kjøring med full inndata
    have = {oslo(h["t"]).hour for h in hours}
    older = sorted(glob.glob(str(Path(a.runs) / "*.json")))
    fill_src = None
    if older and len(have) < 9:
        prev = json.loads(Path(older[-1]).read_text(encoding="utf-8"))
        psp = next((s for s in prev["spots"] if s["id"] == SID), None)
        if psp:
            extra = [dict(h, _fra=prev["generated"][:16]) for h in psp["hours"] if oslo(h["t"]).date() == dt.date(2026, 10, 15) and 10 <= oslo(h["t"]).hour <= 18 and oslo(h["t"]).hour not in have]
            hours = sorted(hours + extra, key=lambda h: h["t"]); fill_src = prev["generated"][:16]
    scen = [("nå (gammelt punkt, gammel vind)", rating_old, f_old, False), ("bare nytt punkt", rating_old, f_old, True),
            ("bare ny vind (sektor og regel)", rating_new, f_new, False), ("begge", rating_new, f_new, True)]
    out.append("## 1. Farstadsanden 15.10 kl. 10-18, fire scenarioer")
    out.append("")
    out.append("Celler: surfehøyde–sett m · stjerner · ord · vindtype. BarentsWatch ved det nye punktet finnes bare fra kl. 14 (3-timers verdier, «~» = interpolert)."
               + (f" Timer merket «(14.10)» kommer fra kjøringen {fill_src}Z - dagens kjøring (kl. 15Z) har dem ikke." if fill_src else ""))
    out.append("")
    out.append("| kl. | " + " | ".join(s[0] for s in scen) + " |")
    out.append("|---|" + "---|" * len(scen))
    for h in hours:
        cells = []
        for name, mod, sp, newp in scen:
            hh = with_new_point(h, np_hours) if newp else dict(h)
            if hh is None:
                cells.append("–"); continue
            r = mod.rate(hh, sp)
            tag = "~" if newp and hh.get("bw_interpolated") else ""
            cells.append(f"{tag}{fm(r.get('surf_height'))}–{fm(r.get('surf_height_sets'))} · {r['stars']}★ · {word(r)} · {WT.get(r.get('wind_type'), r.get('wind_type'))}")
        wl = f"{h.get('wind_speed'):.0f} m/s fra {h.get('wind_dir'):.0f}°, kast {h.get('gust'):.0f}" if h.get("wind_speed") is not None else "vind –"
        out.append(f"| {oslo(h['t']):%H}{' (14.10)' if h.get('_fra') else ''} ({wl}; svell {fm(h.get('swell_offshore'))} m {fm(h.get('period'),0)} s fra {h.get('dir_offshore')}°; BW gammelt {fm(h.get('bw_height'),2)} m) | " + " | ".join(cells) + " |")
    out.append("")
    out.append("Observasjonen kl. 17:20/17:50 (Martin): store, rene bølger som lukker seg i tuber, 6-8 surfere, sjøsprøyt bakover; hodehøyt til godt over hodet, ansikt ca. 2-3 m (anslag); Theodor 4-5 stjerner.")
    out.append("")
    # vindlinja kl. 17 før/etter
    h17 = next((h for h in hours if oslo(h["t"]).hour == 17), None)
    if h17:
        r_old = rating_old.rate(dict(h17), f_old); hb = with_new_point(h17, np_hours); r_new = rating_new.rate(hb or dict(h17), f_new)
        out.append(f"Forklaringslinja for vind kl. 17 - før: «{wind_line(r_old)}» · etter: «{wind_line(r_new)}»")
        out.append("")
        out.append("Hele forklaringen kl. 17 med begge endringene (hvorfor ikke 4-5 stjerner):")
        out.append("")
        for line in r_new.get("breakdown", []):
            out.append(f"- {line}")
        out.append("")

    # ---------- 2. fordeling over 14 dager ----------
    out.append("## 2. Alle timer de siste 14 dagene (én kjøring per dag, timene for den dagen), alle spots: gammel mot ny vindregel")
    out.append("")
    prep_old = {s["id"]: prepared(spots_old, s["id"]) for s in spots_old["spots"] if s.get("enabled")}
    prep_new = {s["id"]: prepared(spots_new, s["id"]) for s in spots_new["spots"] if s.get("enabled")}
    counts = {"-2 eller mer": 0, "-1": 0, "0": 0, "+1": 0, "+2 eller mer": 0}
    changes, n_hours = [], 0
    control_exc, control_n = [], 0
    for f in sorted(glob.glob(str(Path(a.runs) / "*.json"))):
        day = dt.date.fromisoformat(Path(f).stem)
        run = json.loads(Path(f).read_text(encoding="utf-8"))
        for s in run["spots"]:
            sid = s["id"]
            if sid not in prep_old or sid not in prep_new:
                continue
            for h in s["hours"]:
                if oslo(h["t"]).date() != day:
                    continue
                n_hours += 1
                ro = rating_old.rate(dict(h), prep_old[sid]); rn = rating_new.rate(dict(h), prep_new[sid])
                d = rn["stars"] - ro["stars"]
                key = "-2 eller mer" if d <= -2 else "+2 eller mer" if d >= 2 else {-1: "-1", 0: "0", 1: "+1"}[d]
                counts[key] += 1
                if d:
                    changes.append((abs(d), d, sid, h["t"], ro, rn, h))
                if rn.get("wind_type") == "onshore" and (h.get("wind_speed") or 0) > 10 and (h.get("period") or 99) < 9:
                    control_n += 1
                    if rn["stars"] > 1:
                        control_exc.append((sid, h["t"], rn["stars"], h.get("wind_speed"), h.get("period"), wind_line(rn)))
    out.append(f"{n_hours} timer ({len(glob.glob(str(Path(a.runs) / '*.json')))} dager). Endring i stjerner (ny − gammel):")
    out.append("")
    out.append("| −2 eller mer | −1 | uendret | +1 | +2 eller mer |")
    out.append("|---|---|---|---|---|")
    out.append(f"| {counts['-2 eller mer']} | {counts['-1']} | {counts['0']} | {counts['+1']} | {counts['+2 eller mer']} |")
    out.append("")
    out.append("De 10 største endringene:")
    out.append("")
    out.append("| Spot | tid | før → etter | vind før | vind etter |")
    out.append("|---|---|---|---|---|")
    for _, d, sid, t, ro, rn, h in sorted(changes, key=lambda x: (-x[0], x[2], x[3]))[:10]:
        out.append(f"| {sid} | {oslo(t):%d.%m kl. %H} | {ro['stars']}★ {word(ro)} → {rn['stars']}★ {word(rn)} | {wind_line(ro)} | {wind_line(rn)} |")
    out.append("")
    # ---------- 3. kontroll ----------
    out.append("## 3. Kontroll: onshore over 10 m/s og periode under 9 s skal gi 0-1 stjerner")
    out.append("")
    out.append(f"{control_n} slike timer i materialet, {len(control_exc)} unntak." + ("" if control_exc else " Ingen unntak."))
    for sid, t, st, ws, per, wl in control_exc[:20]:
        out.append(f"- {sid} {oslo(t):%d.%m kl. %H}: {st}★, {ws:.0f} m/s, {per:.0f} s - {wl}")
    out.append("")
    md = "\n".join(out)
    Path(a.out).write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
