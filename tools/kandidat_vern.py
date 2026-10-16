"""Vern for kandidatene (ROADMAP K del A punkt 5, 15.10.2026): slår opp hver kandidat mot
Miljødirektoratets Naturbase (verneområder, ArcGIS REST, NLOD) innenfor 2 km av listepinnen, og henter
forskriften på Lovdata for hvert treff.

  python tools/kandidat_vern.py hent     -> Naturbase-treff + forskriftstekst (rå i privat/kandidater/bevis/vern/)
  python tools/kandidat_vern.py utdrag   -> skriver ferdsels-paragrafene per forskrift til privat/…/vern/utdrag.md
                                            (til manuell lesing - restriksjonene legges inn for hånd i
                                            data/kandidater/vern_forskrifter.json, bare det som står der)
  python tools/kandidat_vern.py skriv    -> data/kandidater/vern.json (treff per kandidat + restriksjoner fra
                                            vern_forskrifter.json, aldri gjettet)

Avstanden er fra listepinnen til verneområdets polygon (0 = pinnen ligger inne i området). Et treff
innen 2 km betyr ikke at spoten ligger i området - vern.json sier avstanden, og restriksjonene gjelder
bare det området forskriften beskriver."""
import html
import json
import re
import sys
import time
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parent.parent
KAND = ROOT / "data" / "kandidater" / "kandidater.json"
RAW = ROOT / "privat" / "kandidater" / "bevis" / "vern"
FORSKRIFTER = ROOT / "data" / "kandidater" / "vern_forskrifter.json"
OUT = ROOT / "data" / "kandidater" / "vern.json"
NB = "https://kart.miljodirektoratet.no/arcgis/rest/services/vern/MapServer/0/query"
UA = {"User-Agent": "nordsurf/1.0 (ikke-kommersiell surfevarsel; github.com/theodorll03-bit/nordsurf)"}
RADIUS_M = 2000
TO_UTM = Transformer.from_crs(4326, 25833, always_xy=True)


def naturbase(lat, lon):
    r = requests.get(NB, params={
        "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
        "distance": RADIUS_M, "units": "esriSRUnit_Meter",
        "outFields": "naturvernId,navn,offisieltNavn,verneform,verneforskrift,faktaark,vernedato",
        "returnGeometry": "true", "outSR": 25833, "f": "geojson"}, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def forskrift_id(url):
    m = re.search(r"forskrift/(\d{4}-\d{2}-\d{2}-\d+)", url or "")
    return m.group(1) if m else None


def lovdata_text(fid):
    """Forskriftsteksten (offentlig side på lovdata.no), som ren tekst."""
    r = requests.get(f"https://lovdata.no/dokument/LF/forskrift/{fid}", headers=UA, timeout=60)
    if r.status_code == 404:
        r = requests.get(f"https://lovdata.no/dokument/SF/forskrift/{fid}", headers=UA, timeout=60)
    r.raise_for_status()
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", r.text, flags=re.S)
    t = re.sub(r"<br\s*/?>|</p>|</h\d>|</li>|</div>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", t)).strip()


def hent():
    kand = json.loads(KAND.read_text(encoding="utf-8"))["kandidater"]
    RAW.mkdir(parents=True, exist_ok=True)
    hits = {}
    for k in kand:
        p = k["pin_liste"]
        f = RAW / f"naturbase_{k['id']}.json"
        if not f.exists():
            f.write_text(json.dumps(naturbase(p["lat"], p["lon"]), ensure_ascii=False), encoding="utf-8")
            time.sleep(0.3)
        gj = json.loads(f.read_text(encoding="utf-8"))
        x, y = TO_UTM.transform(p["lon"], p["lat"])
        out = []
        for ft in gj.get("features", []):
            a = ft["properties"]
            d = shape(ft["geometry"]).distance(Point(x, y)) if ft.get("geometry") else None
            out.append({"naturvernId": a.get("naturvernId"), "navn": a.get("offisieltNavn") or a.get("navn"), "verneform": a.get("verneform"),
                        "forskrift": a.get("verneforskrift"), "faktaark": a.get("faktaark"), "vernedato": a.get("vernedato"),
                        "avstand_m": None if d is None else round(d)})
        hits[k["id"]] = sorted(out, key=lambda h: (h["avstand_m"] is None, h["avstand_m"] or 0))
    (RAW / "treff.json").write_text(json.dumps(hits, ensure_ascii=False, indent=1), encoding="utf-8")
    fids = sorted({forskrift_id(h["forskrift"]) for hs in hits.values() for h in hs if forskrift_id(h["forskrift"])})
    print(f"{sum(1 for v in hits.values() if v)} av {len(hits)} kandidater har verneområde innen {RADIUS_M} m; {len(fids)} forskrifter")
    for fid in fids:
        f = RAW / f"lovdata_{fid}.txt"
        if f.exists():
            continue
        f.write_text(lovdata_text(fid), encoding="utf-8")
        time.sleep(1.0)
    print(f"Forskriftene ligger i {RAW}")


FERDSEL = re.compile(r"ferdsel|ilandstigning|ferdes|opphold|forbudt å|forbud mot", re.I)


def utdrag():
    hits = json.loads((RAW / "treff.json").read_text(encoding="utf-8"))
    by_f = {}
    for sid, hs in hits.items():
        for h in hs:
            fid = forskrift_id(h["forskrift"])
            if fid:
                by_f.setdefault(fid, {"navn": set(), "spots": set()})
                by_f[fid]["navn"].add(h["navn"]); by_f[fid]["spots"].add(f"{sid} ({h['avstand_m']} m)")
    out = []
    for fid, v in sorted(by_f.items()):
        t = (RAW / f"lovdata_{fid}.txt").read_text(encoding="utf-8")
        out.append(f"## {fid}: {', '.join(sorted(v['navn']))}\nSpots: {', '.join(sorted(v['spots']))}\n")
        paras = [p.strip() for p in re.split(r"\n(?=§)", t) if FERDSEL.search(p)]
        out += [p[:2500] + "\n" for p in paras] or ["(ingen ferdselsparagraf funnet automatisk - les hele)\n"]
    (RAW / "utdrag.md").write_text("\n".join(out), encoding="utf-8")
    print(f"Skrev {RAW / 'utdrag.md'} ({len(by_f)} forskrifter)")


def skriv():
    hits = json.loads((RAW / "treff.json").read_text(encoding="utf-8"))
    fs = json.loads(FORSKRIFTER.read_text(encoding="utf-8"))["forskrifter"] if FORSKRIFTER.exists() else {}
    out = {}
    for sid, hs in hits.items():
        if not hs:
            continue
        rows = []
        for h in hs:
            fid = forskrift_id(h["forskrift"])
            f = fs.get(fid, {})
            # en forskrift kan dekke flere verneområder (f.eks. Jærstrendene) - restriksjonen gjelder bare området den nevner
            rs = [r for r in f.get("restriksjoner", []) if not r.get("verneomrade") or r["verneomrade"] == h["navn"]]
            rows.append({**h, "lovdata": f"https://lovdata.no/forskrift/{fid}" if fid else None,
                         "restriksjoner": rs, "lest": fid in fs, "merknad": f.get("merknad")})
        out[sid] = rows
    OUT.write_text(json.dumps({"_info": "Verneområder (Naturbase, Miljødirektoratet, NLOD) innen 2 km av listepinnen, med restriksjoner "
                                        "lest fra forskriften på Lovdata (data/kandidater/vern_forskrifter.json). Står det ikke i forskriften, "
                                        "står det ingenting her. avstand_m 0 = pinnen ligger inne i området.",
                               "kandidater": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Skrev {OUT.relative_to(ROOT)}: {len(out)} kandidater med treff")


if __name__ == "__main__":
    {"hent": hent, "utdrag": utdrag, "skriv": skriv}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
