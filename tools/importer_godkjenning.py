"""Legger inn en posisjonsgodkjenning fra en CSV i data/kandidater/posisjoner.json (Theodor 16.10.2026, punkt 8: gjennomgangen
av posisjonene for Lofoten og Vesterålen er delegert til Claude i chatten; Theodor beholder ja/nei til merge av region-PR-ene).

    id,lat,lon,beslutning,sikkerhet,satt_av,dato,begrunnelse        (privat/kandidater/godkjent_claude.csv)

beslutning «godkjent» → spot = (lat, lon), vurdering «godkjent», satt_av fra CSV-en (må være en kjent godkjenner);
«venter_lokalkunnskap» (eller «usikker») → vurdering «venter_lokalkunnskap», posisjonen endres ikke, bygges ikke;
«avvist» → vurdering «avvist». En posisjon Theodor selv har satt (satt_av «theodor») røres aldri.

  python tools/importer_godkjenning.py [sti til csv]"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POS = ROOT / "data" / "kandidater" / "posisjoner.json"
CSV = ROOT / "privat" / "kandidater" / "godkjent_claude.csv"
CLAUDE = "claude (delegert av Theodor 16.10.2026)"


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else CSV
    doc = json.loads(POS.read_text(encoding="utf-8"))
    pos = doc["kandidater"]
    tell = {}
    with src.open(encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            kid, bes, av = row["id"].strip(), row["beslutning"].strip(), row["satt_av"].strip()
            if kid not in pos:
                sys.exit(f"linje {i}: {kid} er ikke en kandidat i posisjoner.json")
            if av != CLAUDE:
                # kontrollør 16.10: en CSV kan ikke skrive Theodors navn - hans egne godkjenninger gjøres i koordinatsjekk
                sys.exit(f"linje {i}: satt_av «{av}» - CSV-en kan bare gi «{CLAUDE}»")
            p = pos[kid]
            if p.get("satt_av") == "theodor":
                print(f"{kid}: Theodor har alt satt posisjonen - røres ikke")
                continue
            p.setdefault("startpunkt", p.get("spot"))
            if bes == "godkjent":
                p["spot"] = {"lat": round(float(row["lat"]), 6), "lon": round(float(row["lon"]), 6)}
                p["vurdering"] = "godkjent"
                p["sikkerhet"] = (row.get("sikkerhet") or "").strip() or p.get("sikkerhet")
                p["metode"] = "godkjent forslag (flyfoto)"
            elif bes in ("venter_lokalkunnskap", "usikker"):
                p["vurdering"] = "venter_lokalkunnskap"
            elif bes == "avvist":
                p["vurdering"] = "avvist"
            else:
                sys.exit(f"linje {i}: ukjent beslutning «{bes}»")
            p["satt_av"] = av
            p["dato"] = (row.get("dato") or "").strip()
            p["begrunnelse"] = (row.get("begrunnelse") or "").strip()[:800]
            tell[bes] = tell.get(bes, 0) + 1
    POS.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"La inn {tell} i {POS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
