"""Legger inn posisjonsforslag fra en CSV som egne markører på gjennomgangssiden (Theodor 16.10.2026, svar
3.5) - f.eks. fra en flyfoto-runde i chatten. Leser privat/kandidater/forslag.csv med kolonnene

    id,lat,lon,kilde,begrunnelse[,sikkerhet,flyttet_m,alternativ]

og legger hvert forslag i «forslag»-lista til kandidaten i data/kandidater/posisjoner.json (satt_av = kilden).
Overskriver ALDRI posisjonen («spot») eller en vurdering Theodor har gjort - forslaget blir bare en markør
han kan velge (klikk) og godkjenne. Samme id + kilde erstatter et tidligere forslag fra samme kilde.
Ukjente id-er, og hemmelige/forbudte kandidater, hoppes over med en melding.

  python tools/importer_forslag.py [sti til csv]"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POS = ROOT / "data" / "kandidater" / "posisjoner.json"
CSV = ROOT / "privat" / "kandidater" / "forslag.csv"


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else CSV
    if not src.exists():
        sys.exit(f"Fant ikke {src} (kolonner: id,lat,lon,kilde,begrunnelse)")
    if not POS.exists():
        sys.exit("Mangler data/kandidater/posisjoner.json - kjør python tools/lag_posisjoner.py først")
    doc = json.loads(POS.read_text(encoding="utf-8"))
    pos = doc["kandidater"]
    n = skip = 0
    with src.open(encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            kid = (row.get("id") or "").strip()
            if kid not in pos:
                print(f"linje {i}: hopper over «{kid}» - ikke en kandidat i posisjoner.json")
                skip += 1
                continue
            try:
                lat, lon = float(row["lat"]), float(row["lon"])
            except (KeyError, TypeError, ValueError):
                print(f"linje {i}: hopper over {kid} - lat/lon mangler eller er ugyldig")
                skip += 1
                continue
            if not (57 <= lat <= 72 and 3 <= lon <= 32):
                print(f"linje {i}: hopper over {kid} - {lat}, {lon} er utenfor Norge")
                skip += 1
                continue
            kilde = (row.get("kilde") or "ukjent").strip()[:60]
            fs = [x for x in pos[kid].get("forslag", []) if x.get("satt_av") != kilde]
            rec = {"lat": round(lat, 6), "lon": round(lon, 6), "satt_av": kilde,
                   "begrunnelse": (row.get("begrunnelse") or "").strip()[:800], "dato": dt.date.today().isoformat()}
            sik = (row.get("sikkerhet") or "").strip().upper()
            if sik in ("A", "B", "C"):
                rec["sikkerhet"] = sik
            try:
                rec["flyttet_m"] = round(float(row["flyttet_m"])) if (row.get("flyttet_m") or "").strip() else None
            except ValueError:
                rec["flyttet_m"] = None
            if (row.get("alternativ") or "").strip():
                rec["alternativ"] = row["alternativ"].strip()[:300]
            fs.append(rec)
            pos[kid]["forslag"] = fs
            n += 1
    POS.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"La inn {n} forslag ({skip} hoppet over) i {POS.relative_to(ROOT)} - ingen godkjent posisjon er endret")


if __name__ == "__main__":
    main()
