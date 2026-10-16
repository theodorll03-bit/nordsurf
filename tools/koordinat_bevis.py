"""Bevis for koordinatjakten (ROADMAP K del A2 punkt 1, 15.10.2026). Henter og mellomlagrer, per
kandidat, i privat/kandidater/bevis/<id>/ (aldri i git):

  a. stedsnavn.json - Kartverkets stedsnavn-API (ws.geonorge.no/stedsnavn/v1, CC BY 4.0): søk på navn og
     alle aliaser i kommunen, og alle stedsnavn innen 3 km av søkesenteret; vi tar vare på typene i
     NAVNETYPER med representasjonspunkt og avstand.
  b. osm.json - OpenStreetMap via Overpass (ODbL, © OpenStreetMap-bidragsytere), innen 3 km:
     natural=beach/sand/shingle (geometri) og sport=surfing - fra et samlet uttrekk for hele Norge
     (sju breddebånd, privat/geodata/strender_*.json). Parkering er ikke med (brukes ikke i valget).
  c. kystlinja kommer fra tools/kystdata.py (OSM-landpolygoner) - leses når hypotesene lages.
  d. Flyfoto: Norge i bilder (WMS) er «norway digital restricted» og krever innlogging (sjekket
     15.10.2026) - ingen flyfoto hentes. Theodor gjør den visuelle sjekken i tools/koordinatsjekk/.

Søkesenteret er listepinnen, eller (--blind) stedsnavnets eget punkt: for de 8 vi har fra før er
listepinnen i praksis vår egen nål (1-5 m unna), så valideringen kjøres blindt fra stedsnavnet.

Kjør: python tools/koordinat_bevis.py [--blind] [id ...]   (standard: alle kandidater)"""
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
KAND = ROOT / "data" / "kandidater" / "kandidater.json"
BEVIS = ROOT / "privat" / "kandidater" / "bevis"
UA = {"User-Agent": "nordsurf/1.0 (ikke-kommersiell surfevarsel; github.com/theodorll03-bit/nordsurf)"}
SN = "https://ws.geonorge.no/stedsnavn/v1"
OVERPASS = os.environ.get("NORDSURF_OVERPASS") or "https://overpass-api.de/api/interpreter"
RADIUS_M = 3000
NAVNETYPER = {"Strand", "Vik", "Bukt", "Odde", "Nes", "Tange", "Skjær", "Grunne", "Os", "Elv", "Havbukt", "Fjære", "Sand", "Halvøy", "Eid"}


def dist_m(a_lat, a_lon, b_lat, b_lon):
    la1, lo1, la2, lo2 = map(math.radians, (a_lat, a_lon, b_lat, b_lon))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def get(url, params, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code in (429, 502, 503, 504):
                raise requests.HTTPError(str(r.status_code))
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if i == tries - 1:
                raise
            time.sleep(4 * (i + 1))


def navnesok(navn, kommune):
    d = get(f"{SN}/navn", {"sok": navn, "fuzzy": "false", "kommunenavn": kommune, "utkoordsys": 4258, "treffPerSide": 50})
    return [{"navn": n["skrivemåte"], "type": n["navneobjekttype"], "lat": n["representasjonspunkt"]["nord"],
             "lon": n["representasjonspunkt"]["øst"], "sok": navn} for n in d.get("navn", [])]


def naer(lat, lon):
    out, side = [], 1
    while True:
        d = get(f"{SN}/punkt", {"nord": lat, "ost": lon, "koordsys": 4258, "radius": RADIUS_M, "utkoordsys": 4258, "treffPerSide": 500, "side": side})
        for n in d.get("navn", []):
            typ = n.get("navneobjekttype")
            if typ in NAVNETYPER and n.get("stedsnavn"):
                p = n["representasjonspunkt"]
                out.append({"navn": n["stedsnavn"][0]["skrivemåte"], "type": typ, "lat": p["nord"], "lon": p["øst"], "m": n.get("meterFraPunkt")})
        md = d.get("metadata", {})
        if md.get("viserTil", 0) >= md.get("totaltAntallTreff", 0) or side >= 5:
            return out
        side += 1


GEO = ROOT / "privat" / "geodata"
_BULK = None


def _bulk():
    """OSM-strender (natural=beach/sand/shingle) og sport=surfing for hele Norge, hentet én gang i sju
    breddebånd fra Overpass (privat/geodata/strender_*.json) - ett kall per bånd i stedet for ett per
    kandidat (Overpass svarte 429 på enkeltkallene 15.10.2026). Parkering er ikke med (brukes ikke i valget)."""
    global _BULK
    if _BULK is None:
        seen, els = set(), []
        for f in sorted(GEO.glob("strender_*.json")):
            for e in json.loads(f.read_text(encoding="utf-8")).get("elements", []):
                key = (e["type"], e["id"])
                if key in seen:
                    continue
                seen.add(key)
                pts = [(n["lat"], n["lon"]) for n in e.get("geometry", [])] + [(n["lat"], n["lon"]) for m in e.get("members", []) for n in m.get("geometry", [])]
                if "lat" in e:
                    pts.append((e["lat"], e["lon"]))
                if pts:
                    e["_bb"] = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
                    els.append(e)
        if not els:
            sys.exit(f"Mangler OSM-strender i {GEO} (strender_*.json) - se docstringen")
        _BULK = els
    return _BULK


def overpass(lat, lon):
    """Elementene fra båndfilene som ligger innen RADIUS_M (rammetest med margin)."""
    dlat = RADIUS_M / 111000 + 0.01
    dlon = dlat / max(0.2, math.cos(math.radians(lat)))
    out = [{k: v for k, v in e.items() if k != "_bb"} for e in _bulk()
           if not (e["_bb"][2] < lat - dlat or e["_bb"][0] > lat + dlat or e["_bb"][3] < lon - dlon or e["_bb"][1] > lon + dlon)]
    return {"elements": out, "_kilde": "Overpass, bånd for hele Norge (privat/geodata/strender_*.json)"}


def kandidat_bevis(k, blind=False):
    d = BEVIS / k["id"]
    d.mkdir(parents=True, exist_ok=True)
    sn_f, osm_f = d / ("stedsnavn_blind.json" if blind else "stedsnavn.json"), d / ("osm_blind.json" if blind else "osm.json")
    if sn_f.exists() and osm_f.exists():
        return json.loads(sn_f.read_text(encoding="utf-8"))
    kommune = (k.get("kommune") or "").split("/")[0].strip()
    navn_treff = []
    for n in [k["name"]] + k.get("aliases", []):
        n = n.split("(")[0].strip()
        if n and len(n) > 2:
            try:
                navn_treff += navnesok(n, kommune)
            except requests.HTTPError:
                pass
            time.sleep(0.2)
    if blind:
        # startpunkt: stedsnavnet med spotens navn, helst en strand/sand/vik/bukt («Strand i sjø» osv.), ellers første treff
        pri = ["Strand", "Sand", "Fjære", "Vik", "Bukt", "Havbukt", "Odde", "Nes", "Tange", "Os", "Skjær", "Grunne"]
        main = k["name"].split("(")[0].strip().lower()
        # hovednavnet foran aliaser, så typen (strand før vik før odde …)
        rank = lambda h: (h["sok"].lower() != main, pri.index(h["type"].split(" ")[0]) if h["type"].split(" ")[0] in pri else len(pri))
        hits = sorted(navn_treff, key=rank)
        if not hits:
            sn = {"senter": None, "navn_treff": navn_treff, "naer": [], "merknad": "blind: ingen stedsnavntreff å starte fra"}
            sn_f.write_text(json.dumps(sn, ensure_ascii=False, indent=1), encoding="utf-8")
            osm_f.write_text("{}", encoding="utf-8")
            return sn
        c = hits[0]
        lat, lon = c["lat"], c["lon"]
    else:
        lat, lon = k["pin_liste"]["lat"], k["pin_liste"]["lon"]
    for h in navn_treff:
        h["m"] = round(dist_m(lat, lon, h["lat"], h["lon"]))
    sn = {"senter": {"lat": lat, "lon": lon, "kilde": "stedsnavn" if blind else "listepinne"}, "navn_treff": navn_treff, "naer": naer(lat, lon)}
    sn_f.write_text(json.dumps(sn, ensure_ascii=False, indent=1), encoding="utf-8")
    osm_f.write_text(json.dumps(overpass(lat, lon), ensure_ascii=False), encoding="utf-8")
    return sn


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    blind = "--blind" in sys.argv
    kand = json.loads(KAND.read_text(encoding="utf-8"))["kandidater"]
    if args:
        kand = [k for k in kand if k["id"] in args]
    for i, k in enumerate(kand):
        try:
            sn = kandidat_bevis(k, blind)
            print(f"{i + 1:3}/{len(kand)} {k['id']:34} navn {len(sn['navn_treff']):2} nær {len(sn['naer']):3}", flush=True)
        except Exception as e:  # noqa: BLE001 - én kandidat skal ikke stoppe resten
            print(f"{i + 1:3}/{len(kand)} {k['id']:34} FEIL: {e}", flush=True)


if __name__ == "__main__":
    main()
