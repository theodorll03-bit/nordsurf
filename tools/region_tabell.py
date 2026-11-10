"""Samletabell for en region fra spotfabrikken (Theodor 16.10.2026, punkt 8c): leser data/kandidater/bygget/<id>.json for
kandidatene i regionene og skriver en markdown-tabell med id, facing, vindu, offshore_wind, havpunkt, BarentsWatch-punkt
(dybde og avstand ut fra spoten), tidevannssted og flagg - til gjennomgang før godkjenn_spot.py.

  python tools/region_tabell.py "Lofoten,Vesterålen" data/kandidater/bygget/lofoten-vesteralen.md"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BYGGET = ROOT / "data" / "kandidater" / "bygget"
KAND = ROOT / "data" / "kandidater" / "kandidater.json"
POS = ROOT / "data" / "kandidater" / "posisjoner.json"


def dist_m(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def fmt_w(w):
    if not w:
        return "–"
    return " + ".join(f"{a}–{b}" for a, b in (w if isinstance(w[0], list) else [w]))


def main():
    regioner = set(sys.argv[1].split(","))
    out = Path(sys.argv[2])
    kand = {k["id"]: k for k in json.loads(KAND.read_text(encoding="utf-8"))["kandidater"]}
    pos = json.loads(POS.read_text(encoding="utf-8"))["kandidater"]
    rows, mangler = [], []
    for kid in sorted(k for k, v in kand.items() if v.get("region") in regioner and v["status"] == "kandidat"):
        p = pos.get(kid, {})
        bf = BYGGET / f"{kid}.json"
        if not bf.exists():
            if p.get("vurdering"):
                mangler.append(f"{kid} ({p.get('vurdering')})")
            continue
        b = json.loads(bf.read_text(encoding="utf-8"))
        s = b["spot"]
        bw = s.get("barentswatch_point")
        if bw:
            snitt = list(b.get("snitt", []))
            for f in BYGGET.glob("*.json"):   # punktet kan være lånt fra en nabospot (rett_bygget.py --bw-fra)
                if f.stem not in (kid,) and not f.stem.startswith("validering"):
                    try:
                        snitt += json.loads(f.read_text(encoding="utf-8")).get("snitt", [])
                    except (ValueError, KeyError):
                        pass
            row = next((r for r in snitt if abs(r["lat"] - bw["lat"]) < 1e-6 and abs(r["lon"] - bw["lon"]) < 1e-6), None)
            dyp = f"{row['dybde_m']} m dyp" if row and row.get("dybde_m") is not None else "dybde ukjent"
            bw_txt = f"{bw['lat']}, {bw['lon']} ({dyp}, {dist_m(s['spot'], bw):.0f} m ut)"
            if "FORELØPIG" in (s.get("_barentswatch") or ""):
                bw_txt = "foreløpig: " + bw_txt
        else:
            bw_txt = "**mangler**"
        hav = s.get("offshore")
        rows.append(f"| {kid} | {kand[kid]['name']} | {kand[kid]['region']} | {s.get('facing') if s.get('facing') is not None else '–'}° | {fmt_w(s.get('swell_window'))} | "
                    f"{fmt_w(s.get('offshore_wind'))} | {f'{hav[chr(108)+chr(97)+chr(116)]}, {hav[chr(108)+chr(111)+chr(110)]}' if hav else '–'} | {bw_txt} | "
                    f"{(s.get('tidevann') or {}).get('name') or '–'}{' (' + str(s['tidevann'].get('delay')) + ' min)' if (s.get('tidevann') or {}).get('delay') not in (None, '0') else ''} | {'; '.join(b.get('flagg') or []) or '–'} |")
    L = [f"# Spotfabrikken: {', '.join(sorted(regioner))} ({len(rows)} spots)", "",
         "Forslag fra tools/bygg_spot.py for posisjonene som er godkjent (Claude, delegert av Theodor 16.10.2026). Ingenting er lagt inn i "
         "spots.json - det skjer med tools/godkjenn_spot.py etter gjennomgang (fra 10.11.2026: spotansvarligs data/kandidater/bygget/<region>-gjennomgang.csv; 16.10: privat/kandidater/bygg_godkjent_claude.csv). "
         "Tidevann: Kartverkets referansested for posisjonen (samme oppslag som henteren; mange steder bruker Andenes med egen forsinkelse og faktor). Minikart per spot: data/kandidater/bygget/<id>.png. Vindu: fri linje 150 km over GSHHS f (300 m kysttoleranse). Facing: "
         "strandnormal ±150 m langs kysten. Offshore-vind: motsatt av facing ±45° (standard, ubekreftet). BarentsWatch: snittregelen 15.10.", "",
         "| id | Navn | Region | facing | Vindu | Offshore-vind | Havpunkt | BarentsWatch-punkt | Tidevann | Flagg |",
         "|---|---|---|---|---|---|---|---|---|---|"] + rows
    if mangler:
        L += ["", f"Ikke bygget: {', '.join(mangler)}."]
    L += ["", "Kyst © OpenStreetMap-bidragsytere og GSHHS; dybde EMODnet Bathymetry; tidevann © Kartverket; bølger BarentsWatch."]
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Skrev {out} ({len(rows)} spots)")


if __name__ == "__main__":
    main()
