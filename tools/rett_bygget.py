"""Retter et forslag fra spotfabrikken etter en «rett»-beslutning i gjennomgangen (Theodor/Claude 16.10.2026) - før
godkjenn_spot.py. Endrer bare data/kandidater/bygget/<id>.json (og minikartet), aldri spots.json. Hvert rettet felt
merkes med kilden (standard «forslag fra Claude 16.10, ukalibrert») i «_rettet».

  python tools/rett_bygget.py <id> [--facing 305] [--offshore-wind 80,170] [--hoyder 1.5,3.5,5.0]
                                   [--bw-fra <annen id>] [--nytt-snitt [--snitt-maks 3000]] [--merk "<tekst>"]

--facing: ny facing; snittet for BarentsWatch-punktet blir da foreldet (krever --nytt-snitt eller --bw-fra).
--nytt-snitt: henter dybdene langs (ny) facing på nytt (EMODnet) og setter BarentsWatch-punktet til FORELØPIG, så
  snittet i Actions (find_bw_point.yml, kandidater) og velg_bw_punkt.py må kjøres før godkjenn_spot.py.
--bw-fra: bruker BarentsWatch-punktet og snittfila til en annen bygget spot (f.eks. nabospot på samme strand)."""
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
BYGGET = ROOT / "data" / "kandidater" / "bygget"


def opt(name, default=None):
    a = sys.argv
    return next((a[i + 1] for i, x in enumerate(a) if x == name and i + 1 < len(a)), default)


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        sys.exit(__doc__)
    sid = sys.argv[1]
    bf = BYGGET / f"{sid}.json"
    b = json.loads(bf.read_text(encoding="utf-8"))
    s = b["spot"]
    merk = opt("--merk", "forslag fra Claude 16.10, ukalibrert")
    rettet = dict(s.get("_rettet") or {})
    if opt("--facing"):
        s["facing"] = float(opt("--facing"))
        rettet["facing"] = merk
        b["flagg"] = [f for f in b.get("flagg", []) if "facing" not in f and "vindussektor" not in f]
        if not ("--nytt-snitt" in sys.argv or opt("--bw-fra")):
            sys.exit("Ny facing gjør BarentsWatch-snittet foreldet - bruk --nytt-snitt eller --bw-fra")
    if opt("--offshore-wind"):
        s["offshore_wind"] = [int(x) for x in opt("--offshore-wind").split(",")]
        s["_offshore_vind"] = merk
        rettet["offshore_wind"] = merk
    if opt("--hoyder"):
        lo, hi, mx = (float(x) for x in opt("--hoyder").split(","))
        s["ideal_height"], s["max_height"] = [lo, hi], mx
        s["_ideal_height"] = merk
        rettet["ideal_height/max_height"] = merk
        b["flagg"] = [f for f in b.get("flagg", []) if "ideal_height" not in f]
    if opt("--bw-fra"):
        other = json.loads((BYGGET / f"{opt('--bw-fra')}.json").read_text(encoding="utf-8"))["spot"]
        if not other.get("barentswatch_point") or not other.get("_barentswatch_snitt"):
            sys.exit(f"{opt('--bw-fra')} har ikke et BarentsWatch-punkt fra snittet")
        s["barentswatch_point"] = dict(other["barentswatch_point"])
        s["_barentswatch_snitt"] = other["_barentswatch_snitt"]
        s["_barentswatch"] = f"Samme punkt som {opt('--bw-fra')} (nabospot på samme strand) - {merk}. " + (other.get("_barentswatch") or "")
        rettet["barentswatch_point"] = merk
        b["flagg"] = [f for f in b.get("flagg", []) if "BarentsWatch" not in f and "EMODnet-dybde" not in f]
    if "--nytt-snitt" in sys.argv:
        import bygg_spot
        maks = int(opt("--snitt-maks", bygg_spot.BW_MAX_M))
        rows, first = bygg_spot.bw_transect(s["spot"]["lat"], s["spot"]["lon"], s["facing"], max_m=maks)
        b["snitt"] = rows
        s["barentswatch_point"] = {"lat": first["lat"], "lon": first["lon"]} if first else None
        s["_barentswatch"] = (f"FORELØPIG: nytt snitt langs {s['facing']}° til {maks} m - venter på BarentsWatch-snitt i Actions "
                              f"(find_bw_point.yml, kandidater{', maks_m=' + str(maks) if maks != 1500 else ''}) og velg_bw_punkt.py.")
        s.pop("_barentswatch_snitt", None)
        b["flagg"] = [f for f in b.get("flagg", []) if "BarentsWatch" not in f and "EMODnet-dybde" not in f]
        rettet["barentswatch_point"] = f"nytt snitt langs {s['facing']}° ({merk})"
    s["_rettet"] = rettet
    b["rettet"] = dt.date.today().isoformat()
    bf.write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    try:
        import bygg_spot
        import kystdata
        bygg_spot.minikart(BYGGET / f"{sid}.png", kystdata.land("osm"), s["spot"]["lat"], s["spot"]["lon"], sid, s.get("swell_window"),
                           s.get("facing"), s.get("offshore_wind"), s.get("offshore") or {"lat": "–", "lon": "–"}, s.get("barentswatch_point"),
                           b.get("snitt", []), bw_label="BarentsWatch (foreløpig)" if "FORELØPIG" in (s.get("_barentswatch") or "") else "BarentsWatch")
    except Exception as e:  # noqa: BLE001
        print(f"minikartet ble ikke tegnet på nytt: {e}")
    print(f"{sid}: rettet {sorted(rettet)}; flagg nå: {b['flagg'] or 'ingen'}")


if __name__ == "__main__":
    main()
