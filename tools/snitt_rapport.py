"""Snittrapport for BarentsWatch-punktene (Theodor 15.10.2026, Farstadsanden «Holy
portugal»): leser data/bw_point_search/result.json (workflowen «Finn BarentsWatch-
punkt», snitt langs facing 0-1500 m med 100 m-steg) og data/bw_point_search/
depths.json (EMODnet Bathymetry REST, Norway_kyst_50m, åpen), og skriver
markdown-tabeller til data/bw_point_search/snitt_<dato>.md.

Regel for valg av punkt (Theodor, del 2): første punkt utover som oppfyller alle:
  - Hs øker mindre enn 10 % per 100 m videre utover (har flatet ut),
  - retningen er innenfor ±30° av svellet ute (ikke i le bak et skjær),
  - dybden er minst ca. 8 m (når vi har dybde),
  - punktet ligger på vann (BarentsWatch svarte, dybde > 0).
De andre spotene: bare rapport - punkter der Hs øker over 30 % innen 300 m
utover merkes (tyder på at punktet ligger inne i brytesonen).

Kjør: python tools/snitt_rapport.py [--hour 2026-10-15T12:00Z] (standard: første time)"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "data" / "bw_point_search" / "result.json"
DEP = ROOT / "data" / "bw_point_search" / "depths.json"
OSLO = ZoneInfo("Europe/Oslo")
MIN_DEPTH_M = 8.0


def angle_diff(a, b):
    d = abs((a - b) % 360)
    return min(d, 360 - d)


def oslo(k):
    return dt.datetime.fromisoformat(k.replace("Z", "+00:00")).astimezone(OSLO)


def fmt(v, nd=2, unit=""):
    return "–" if v is None else (f"{v:.{nd}f}".replace(".", ",") + unit)


def transect_rows(spot_res, depths, hour_key):
    rows = []
    for label, p in spot_res["points"].items():
        h = p["hours"].get(hour_key) or {}
        d = (depths or {}).get(label, {})
        rows.append({"label": label, "dist": p["requested"].get("dist_m"), "hs": h.get("height"), "hmax": h.get("max_height"),
                     "period": h.get("period"), "dir": h.get("dir"), "swell_dir": h.get("offshore_swell_dir"),
                     "swell_h": h.get("offshore_swell_height"), "depth": d.get("depth_m"), "lat": p["requested"]["lat"], "lon": p["requested"]["lon"]})
    return rows


def choose(rows):
    """Regelen over, på snittpunktene (de med avstand), sortert utover."""
    tr = sorted([r for r in rows if r["dist"] is not None], key=lambda r: r["dist"])
    why = {}
    for i, r in enumerate(tr):
        reasons = []
        nxt = tr[i + 1] if i + 1 < len(tr) else None
        if r["hs"] is None:
            reasons.append("ingen BarentsWatch-tall")
        elif nxt and nxt["hs"] is not None and r["hs"] > 0 and (nxt["hs"] - r["hs"]) / r["hs"] >= 0.10:
            reasons.append(f"Hs øker {100 * (nxt['hs'] - r['hs']) / r['hs']:.0f} % til neste punkt")
        if r["dir"] is not None and r["swell_dir"] is not None and angle_diff(r["dir"], r["swell_dir"]) > 30:
            reasons.append(f"retning {r['dir']:.0f}° er {angle_diff(r['dir'], r['swell_dir']):.0f}° fra svellet ute ({r['swell_dir']:.0f}°)")
        if r["depth"] is not None and r["depth"] < MIN_DEPTH_M:
            reasons.append(f"dybde {r['depth']:.1f} m under {MIN_DEPTH_M:.0f} m")
        if r["depth"] is not None and r["depth"] <= 0:
            reasons.append("på land")
        why[r["label"]] = reasons
        if not reasons:
            return r, why
    return None, why


def brytesone_flag(rows):
    """Punkter der Hs øker over 30 % innen 300 m utover."""
    tr = sorted([r for r in rows if r["dist"] is not None and r["hs"]], key=lambda r: r["dist"])
    flagged = []
    for r in tr:
        later = [x for x in tr if r["dist"] < x["dist"] <= r["dist"] + 300 and x["hs"]]
        if later and max(x["hs"] for x in later) > 1.3 * r["hs"]:
            flagged.append(r["label"])
    return flagged


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hour", default=None, help="UTC-time som 2026-10-15T12:00Z (standard: første time i resultatet)")
    ap.add_argument("--res", default=str(RES), help="resultatfila fra find_bw_point.py (standard: result.json)")
    ap.add_argument("--out", default=None, help="markdown-fila (standard: snitt_<dato>.md ved siden av resultatet)")
    a = ap.parse_args()
    res_path = Path(a.res)
    res = json.loads(res_path.read_text(encoding="utf-8"))
    depths = json.loads(DEP.read_text(encoding="utf-8")) if DEP.exists() else {}
    first = (res["spots"].get("farstadsanden") or next(iter(res["spots"].values())))["points"]
    all_hours = sorted({k for p in first.values() for k in p["hours"]})
    hour_key = a.hour or all_hours[0]
    out = [f"# Snitt langs facing, BarentsWatch {res['generated'][:16]}Z, time {hour_key} (kl. {oslo(hour_key):%H} norsk tid)", ""]
    chosen_all = {}
    for sid, sp in res["spots"].items():
        rows = transect_rows(sp, depths.get(sid), hour_key)
        chosen, why = choose(rows)
        flagged = brytesone_flag(rows)
        chosen_all[sid] = {"chosen": chosen, "flagged": flagged}
        out.append(f"## {sid} (facing {sp['facing']})")
        out.append("")
        out.append("| Punkt | m fra fjæra | Hs | Hs_max | periode | retning | svell ute | dybde | merknad |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for r in sorted(rows, key=lambda r: (r["dist"] is None, r["dist"] or 0, r["label"])):
            mark = []
            if chosen and r["label"] == chosen["label"]:
                mark.append("**VALGT**")
            if r["label"] in flagged:
                mark.append("Hs +30 % innen 300 m")
            if r["label"] in why and why[r["label"]]:
                mark.append("; ".join(why[r["label"]]))
            dist = "–" if r["dist"] is None else str(r["dist"])
            out.append(f"| {r['label']} | {dist} | {fmt(r['hs'], 2, ' m')} | {fmt(r['hmax'], 2, ' m')} | {fmt(r['period'], 1, ' s')} | {fmt(r['dir'], 0, '°')} | "
                       f"{fmt(r['swell_h'], 1, ' m')} fra {fmt(r['swell_dir'], 0, '°')} | {fmt(r['depth'], 1, ' m')} | {' · '.join(mark)} |")
        out.append("")
        if chosen:
            out.append(f"Valgt etter regelen: **{chosen['label']}** ({chosen['lat']}, {chosen['lon']}), Hs {fmt(chosen['hs'], 2, ' m')}, dybde {fmt(chosen['depth'], 1, ' m')}.")
        else:
            out.append("Ingen punkter oppfyller alle vilkårene i denne timen.")
        if flagged:
            out.append(f"Brytesone-mistanke (Hs +30 % innen 300 m utover): {', '.join(flagged)}.")
        out.append("")
    if "farstadsanden" not in res["spots"]:
        return write(out, res_path, a, hour_key, chosen_all)
    # Farstadsanden: alle timene i dag 12-18 og i morgen 08-16 for noen nøkkelpunkter
    out.append("## Farstadsanden time for time (BarentsWatch gir 3-timers verdier)")
    out.append("")
    keys = ["dagens barentswatch_point", "dagens barentswatch_point_near", "snitt Theodors opprinnelige punkt 06.10", "snitt nålen (BW-kartet 2 m)"] + [k for k in first if k.startswith("snitt ") and k.split(" ")[1].endswith("@310")]
    hours = [k for k in all_hours if (oslo(k).date() == oslo(hour_key).date() and 12 <= oslo(k).hour <= 18) or (oslo(k).date() == oslo(hour_key).date() + dt.timedelta(days=1) and 8 <= oslo(k).hour <= 16)]
    out.append("| Punkt | " + " | ".join(f"{oslo(k):%a %H}" for k in hours) + " |")
    out.append("|---|" + "---|" * len(hours))
    for k in keys:
        p = first[k]
        cells = [f"{fmt(p['hours'].get(h, {}).get('height'), 2)}/{fmt(p['hours'].get(h, {}).get('period'), 0)}s/{fmt(p['hours'].get(h, {}).get('dir'), 0)}°" for h in hours]
        out.append(f"| {k} | " + " | ".join(cells) + " |")
    out.append("")
    out.append("Celler: Hs m / periode s / retning fra. Timene er de nærmeste BarentsWatch har: 3-timers steg.")
    return write(out, res_path, a, hour_key, chosen_all)


def write(out, res_path, a, hour_key, chosen_all):
    md = "\n".join(out)
    path = Path(a.out) if a.out else res_path.parent / f"snitt_{oslo(hour_key):%Y-%m-%d}.md"
    path.write_text(md, encoding="utf-8")
    print(md[:200] + " …")
    print(f"\nSkrev {path}")
    for sid, v in chosen_all.items():
        c = v["chosen"]
        print(f"{sid:16} valgt: {c['label'] if c else '-':40} brytesone-mistanke: {', '.join(v['flagged']) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
