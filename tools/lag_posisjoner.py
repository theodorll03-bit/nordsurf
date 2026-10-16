"""Startpunktet for Theodors gjennomgang av kandidatposisjonene (svar 3.5, 16.10.2026): skriver
data/kandidater/posisjoner.json med listepinnen som posisjon for alle kandidater (satt_av «liste», sikkerhet
«ikke sjekket»), og alternative markører per kandidat:
  - «osm-strand»: midt på sjøkanten av hver OSM-strand innen 1,5 km, 100 m ut (KONVENSJON.md)
  - «stedsnavn»: Kartverkets stedsnavn med kandidatens navn/alias innen 3 km
Forslag fra andre (tools/importer_forslag.py) ligger i «forslag» og røres ikke her.

Kjøres trygt flere ganger: en posisjon Theodor har satt (satt_av «theodor») eller vurdert, og alle forslag,
beholdes - bare listepinnen og alternativene fylles inn på nytt. Hemmelige og forbudte kandidater er ikke med,
men en oppføring Theodor har satt eller vurdert beholdes alltid (merket «status_endret» hvis statusen er endret).

  python tools/lag_posisjoner.py"""
import datetime as dt
import json
import sys
from pathlib import Path

from shapely.geometry import Point

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import kystdata  # noqa: E402
import koordinatjakt as kj  # noqa: E402

POS = ROOT / "data" / "kandidater" / "posisjoner.json"
KAND = ROOT / "data" / "kandidater" / "kandidater.json"


def alternativer(k, land):
    d = kj.BEVIS / k["id"]
    if not (d / "stedsnavn.json").exists() or not (d / "osm.json").exists():
        return []
    sn = json.loads((d / "stedsnavn.json").read_text(encoding="utf-8"))
    osm = json.loads((d / "osm.json").read_text(encoding="utf-8"))
    pin = k["pin_liste"]
    L = kj.Lokal(land, pin["lat"], pin["lon"], half_deg=0.045)   # ca. 5 km - alternativene ligger innen 3 km
    out = []
    for b in kj.osm_beaches(osm, L):
        if b["geom"].distance(Point(0, 0)) > 1500:
            continue
        mid, seal = kj.seaward_mid(b["geom"], L)
        if seal <= 0:
            continue
        p = L.to_water(mid)
        la, lo = L.ll(p.x, p.y)
        out.append({"kilde": "osm-strand", "navn": b["name"], "lat": round(la, 6), "lon": round(lo, 6),
                    "merknad": f"midt på sjøkanten ({seal:.0f} m), 100 m ut"})
    st = kj.stems(k)
    seen = set()
    for h in sn.get("navn_treff", []) + sn.get("naer", []):
        if not kj.name_match(h["navn"], st) or (h.get("m") or 0) > 3000:
            continue
        key = (round(h["lat"], 4), round(h["lon"], 4))
        if key in seen:
            continue
        seen.add(key)
        out.append({"kilde": "stedsnavn", "navn": f"{h['navn']} ({h['type']})", "lat": h["lat"], "lon": h["lon"]})
    return out


def main():
    kand = [k for k in json.loads(KAND.read_text(encoding="utf-8"))["kandidater"] if k["status"] == "kandidat"]
    old = json.loads(POS.read_text(encoding="utf-8"))["kandidater"] if POS.exists() else {}
    land = kystdata.land("osm")
    today = dt.date.today().isoformat()
    out = {}
    # Theodors godkjenninger og notater slettes aldri: får en kandidat senere status «hemmelig» eller «forbudt»,
    # beholdes oppføringen, merket med statusen (kontrollør 16.10 - ellers ville det vært sletting av data)
    kstatus = {k["id"]: k["status"] for k in json.loads(KAND.read_text(encoding="utf-8"))["kandidater"]}
    aktive = {k["id"] for k in kand}
    for kid, prev in old.items():
        if kid not in aktive and (prev.get("satt_av") == "theodor" or prev.get("vurdering")):
            out[kid] = {**prev, "status_endret": kstatus.get(kid, "finnes ikke i kandidater.json")}
    for k in kand:
        prev = old.get(k["id"], {})
        if prev.get("satt_av") == "theodor" or prev.get("vurdering"):
            rec = prev   # Theodors posisjon og vurdering røres aldri
        else:
            rec = {"spot": dict(k["pin_liste"]), "sikkerhet": "ikke sjekket", "satt_av": "liste", "metode": "listepinne", "dato": today}
        rec["alternativer"] = alternativer(k, land)
        rec["forslag"] = prev.get("forslag", [])
        rec.pop("status_endret", None)
        out[k["id"]] = rec
    doc = {"_info": "Posisjoner for kandidatene (Theodor 16.10.2026, svar 3.5). Startpunkt: listepinnen (satt_av «liste», ikke sjekket). "
                    "Theodor godkjenner/flytter i tools/koordinatsjekk/ (satt_av «theodor»); forslag fra andre (tools/importer_forslag.py) "
                    "ligger i «forslag» og overskriver aldri en godkjent posisjon. Spotfabrikken bygger bare fra godkjente posisjoner.",
           "kandidater": out}
    POS.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_alt = sum(len(v["alternativer"]) for v in out.values())
    print(f"Skrev {POS.relative_to(ROOT)}: {len(out)} kandidater, {n_alt} alternative markører, "
          f"{sum(1 for v in out.values() if v.get('satt_av') == 'theodor')} satt av Theodor (beholdt)")


if __name__ == "__main__":
    main()
