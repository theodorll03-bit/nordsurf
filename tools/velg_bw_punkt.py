"""Velger BarentsWatch-punktet for spots fra spotfabrikken ut fra snittet i Actions (Theodor 16.10.2026, ROADMAP K del C):
leser resultatfila fra find_bw_point.yml (input «kandidater», data/bw_point_search/result_*_kandidater.json) og
dybden spotfabrikken alt har hentet (EMODnet, «snitt» i data/kandidater/bygget/<id>.json), og bruker regelen fra
15.10 (som tools/snitt_rapport.py choose(): første punkt utover der Hs øker under 10 % per 100 m, retning innen 30° av
svellet ute, dybde ≥ 8 m) - men strengere: manglende dybde eller Hs godtas aldri. Regelen prøves for hver
BarentsWatch-time der svellet ute kommer fra innenfor vinduet; valgt er punktet i timen med størst svell ute der
regelen finner et punkt. Skriver barentswatch_point, _barentswatch og _barentswatch_snitt i bygget-fila.
Finner regelen ingen punkt i noen time, settes barentswatch_point til null med et flagg («BarentsWatch uten data»
hvis punktene ikke svarte) - aldri et gjettet punkt.

  python tools/velg_bw_punkt.py data/bw_point_search/result_<tid>_kandidater.json [id …]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "fetcher"))
import snitt_rapport as sr  # noqa: E402

BYGGET = ROOT / "data" / "kandidater" / "bygget"


def in_window(d, win):
    from rating import in_sector
    if not win:
        return False
    return any(in_sector(d, w) for w in (win if isinstance(win[0], list) else [win]))


def choose_strict(rows):
    """Som snitt_rapport.choose(), men manglende data godtas aldri (kontrollør 16.10): dybden må være kjent og minst
    8 m, og Hs må være kjent både i punktet og i neste punkt utover (ellers kan «flater ut» ikke vurderes)."""
    tr = sorted([r for r in rows if r["dist"] is not None], key=lambda r: r["dist"])
    for i, r in enumerate(tr):
        nxt = tr[i + 1] if i + 1 < len(tr) else None
        if r["hs"] is None or r["hs"] <= 0 or r["depth"] is None or r["depth"] < sr.MIN_DEPTH_M:
            continue
        if nxt is None or nxt["hs"] is None or (nxt["hs"] - r["hs"]) / r["hs"] >= 0.10:
            continue
        if r["dir"] is None or r["swell_dir"] is None or sr.angle_diff(r["dir"], r["swell_dir"]) > 30:
            continue
        return r
    return None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    res_path = Path(sys.argv[1])
    res = json.loads(res_path.read_text(encoding="utf-8"))
    ids = sys.argv[2:] or list(res["spots"])
    rel = str(res_path.resolve().relative_to(ROOT))
    for sid in ids:
        bf = BYGGET / f"{sid}.json"
        if sid not in res["spots"] or not bf.exists():
            print(f"{sid}: hopper over - mangler i resultatet eller i bygget/")
            continue
        b = json.loads(bf.read_text(encoding="utf-8"))
        sp = res["spots"][sid]
        dyp = {}
        by_m = {r["m"]: r.get("dybde_m") for r in b.get("snitt", [])}
        for label, p in sp["points"].items():
            dm = p["requested"].get("dist_m")
            if dm is not None:
                dyp[label] = {"depth_m": by_m.get(dm)}
        hours = sorted({k for p in sp["points"].values() for k in p["hours"]})
        any_data = any(h.get("height") is not None for p in sp["points"].values() for h in p["hours"].values())
        win = b["spot"].get("swell_window")
        best = None
        for hk in hours:
            rows = sr.transect_rows(sp, dyp, hk)
            sdir = next((r["swell_dir"] for r in rows if r["swell_dir"] is not None), None)
            # bare timer der svellet ute kommer fra innenfor vinduet (kontrollør 16.10: største svell kan komme bakfra)
            if sdir is None or not in_window(sdir, win):
                continue
            chosen = choose_strict(rows)
            if chosen:
                swell = max((r["swell_h"] or 0) for r in rows)
                if best is None or swell > best[0]:
                    best = (swell, hk, chosen)
        s = b["spot"]
        s["_barentswatch_snitt"] = rel
        b["flagg"] = [f for f in b.get("flagg", []) if "BarentsWatch" not in f]
        if best:
            # valgt punkt har kjent dybde ≥ 8 m (choose_strict) - da er fabrikkens foreløpige dybdeflagg utdatert
            b["flagg"] = [f for f in b["flagg"] if "EMODnet-dybde" not in f]
            _, hk, c = best
            s["barentswatch_point"] = {"lat": c["lat"], "lon": c["lon"]}
            s["_barentswatch"] = (f"Snitt langs facing ({rel}), regelen fra 15.10: {c['label']}, {c['dist']} m ut, dybde "
                                  f"{sr.fmt(c['depth'], 1, ' m')}, Hs {sr.fmt(c['hs'], 2, ' m')} kl. {hk}.")
            print(f"{sid}: valgt {c['label']} ({c['dist']} m, {sr.fmt(c['depth'], 1, ' m')})")
        else:
            s["barentswatch_point"] = None
            s["_barentswatch"] = f"Snitt langs facing ({rel}): regelen fant ikke noe punkt i noen time."
            b["flagg"].append("BarentsWatch uten data" if not any_data else "BarentsWatch: regelen fant ikke noe punkt (Hs flater ikke ut / for grunt / retning) - Theodor må velge")
            print(f"{sid}: ikke noe punkt ({'ingen data' if not any_data else 'regelen fant ingenting'})")
        bf.write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
