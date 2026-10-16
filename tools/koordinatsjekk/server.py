"""Gjennomgangsside for kandidatposisjonene (ROADMAP K del A2 punkt 4, 15.10.2026). Bare lokalt - ikke
publisert. Theodor går gjennom forslagene i rekkefølge C, B, «posisjon» fra triagen, A:

    python3 tools/koordinatsjekk/server.py      → åpne http://127.0.0.1:8765/

Viser per kandidat listepinnen (grå), posisjonen som skal godkjennes (stor, kan dras), alternative markører
(OSM-strand brun, stedsnavn blå, forslag fra tools/importer_forslag.py lilla - klikk for å flytte posisjonen dit)
og OSM-strender (omriss) på Kartverkets topografiske kart (cache.kartverket.no, CC BY 4.0). Region for region
(Lofoten og Vesterålen først) med teller «12 av 27 sjekket»; i regionen «posisjon» fra triagen først, så anslått
posisjon, så resten. G = godkjenn, U = usikker, A = avvis, ←/→ = forrige/neste. Lenke til Norgeskart med
FLYFOTO-laget og markør på punktet (backgroundLayer=Nibcache_UTM33_EUREF89_v2, sok=lat,lon - testet 16.10),
og Google Maps satellitt som reserve.

Hver vurdering lagres med POST til denne serveren i data/kandidater/posisjoner.json (satt_av «theodor»,
tidspunkt). MapLibre GL JS 5.24.0: docs/vendor/ fra S3 hvis den finnes, ellers lastet ned én gang til
privat/vendor/ (samme versjon)."""
import datetime as dt
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pyproj import Transformer

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
POS = ROOT / "data" / "kandidater" / "posisjoner.json"
KAND = ROOT / "data" / "kandidater" / "kandidater.json"
TRIAGE = ROOT / "data" / "kandidater" / "triage.json"
BEVIS = ROOT / "privat" / "kandidater" / "bevis"
VENDOR_DIRS = [ROOT / "docs" / "vendor", ROOT / "privat" / "vendor"]
MAPLIBRE = "5.24.0"
PORT = 8765
UTM33 = Transformer.from_crs(4326, 25833, always_xy=True)   # Norgeskart bruker EUREF89 UTM 33 i lenkene


def vendor(name):
    for d in VENDOR_DIRS:
        for cand in (d / name, d / "maplibre" / name, d / f"maplibre-gl-{MAPLIBRE}" / name):
            if cand.exists():
                return cand
    d = VENDOR_DIRS[1]
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sfL", "-o", str(d / name), f"https://cdn.jsdelivr.net/npm/maplibre-gl@{MAPLIBRE}/dist/{name}"], check=True, timeout=120)
    return d / name


def evidence(kid):
    out = {"navn": [], "strender": []}
    d = BEVIS / kid
    sn = d / "stedsnavn.json"
    if sn.exists():
        s = json.loads(sn.read_text(encoding="utf-8"))
        seen = set()
        for h in s.get("navn_treff", []) + s.get("naer", []):
            key = (h["navn"], round(h["lat"], 5), round(h["lon"], 5))
            if key not in seen:
                seen.add(key)
                out["navn"].append({"navn": h["navn"], "type": h["type"], "lat": h["lat"], "lon": h["lon"]})
    osm = d / "osm.json"
    if osm.exists():
        for e in json.loads(osm.read_text(encoding="utf-8")).get("elements", []):
            t = e.get("tags", {})
            if t.get("natural") in ("beach", "sand", "shingle"):
                rings = [e["geometry"]] if e.get("geometry") else [m["geometry"] for m in e.get("members", []) if m.get("geometry")]
                for r in rings:
                    out["strender"].append({"navn": t.get("name"), "coords": [[n["lon"], n["lat"]] for n in r]})
    return out


FORSTE_REGIONER = ["Lofoten", "Vesterålen"]   # Theodor 16.10: disse først, så resten nord til sør


def payload():
    pos = json.loads(POS.read_text(encoding="utf-8"))["kandidater"]
    kdoc = json.loads(KAND.read_text(encoding="utf-8"))
    kand = {k["id"]: k for k in kdoc["kandidater"]}
    regs = FORSTE_REGIONER + [r for r in kdoc.get("regioner_forslag", []) if r not in FORSTE_REGIONER]
    tri = json.loads(TRIAGE.read_text(encoding="utf-8"))["kandidater"] if TRIAGE.exists() else {}
    rows = []
    for kid, p in pos.items():
        k = kand.get(kid)
        if not k or k["status"] != "kandidat":
            continue   # hemmelige og forbudte er aldri med
        t = tri.get(kid, {})
        # rekkefølge i regionen: «posisjon» i triagen, så anslått posisjon, så resten; lav prioritet sist
        grp = 0 if t.get("status") == "posisjon" else 1 if k.get("coord_confidence") == "estimated" else 2
        if k.get("prioritet") == "lav":
            grp = 3
        f = p.get("spot") or k["pin_liste"]
        e, n = UTM33.transform(f["lon"], f["lat"])
        rows.append({"id": kid, "navn": k["name"], "region": k.get("region"), "kommune": k.get("kommune"), "type": k["hint"].get("break_type"),
                     "pinne": k["pin_liste"], "forslag": f, "sikkerhet": p.get("sikkerhet"), "metode": p.get("metode"),
                     "satt_av": p.get("satt_av"), "vurdering": p.get("vurdering"), "triage": t.get("status"),
                     "coord_confidence": k.get("coord_confidence"), "vern": k.get("vern_merknad"),
                     "flagg": (t.get("osm") or {}).get("hvorfor", []), "gruppe": grp,
                     "alternativer": p.get("alternativer", []), "andre_forslag": p.get("forslag", []),
                     "bevis": evidence(kid), "utm33": {"e": round(e), "n": round(n)}})
    ri = lambda r: regs.index(r) if r in regs else len(regs)
    rows.sort(key=lambda r: (ri(r["region"]), r["gruppe"], r["navn"]))
    return rows


VERN = ROOT / "data" / "kandidater" / "vern.json"
VERN_VARSEL_M = 200


def vern_sjekk(kid, lat, lon):
    """Ligger posisjonen i (eller innen 200 m av) et verneområde der forskriften har ferdsels- eller surfeforbud
    for sjø/strand? Bruker Naturbase-geometrien som er mellomlagret i privat/ (tools/kandidat_vern.py)."""
    from shapely.geometry import Point, shape
    raw = BEVIS / "vern" / f"naturbase_{kid}.json"
    if not raw.exists() or not VERN.exists():
        return None
    forbud = {h["navn"]: h["restriksjoner"] for h in json.loads(VERN.read_text(encoding="utf-8")).get("kandidater", {}).get(kid, [])
              if any(r.get("type") in ("ferdselsforbud", "surfeforbud") and r.get("gjelder") in ("sjø", "strand", "begge")
                     and not r.get("stedsbundet") for r in h.get("restriksjoner") or [])}
    if not forbud:
        return None
    x, y = UTM33.transform(lon, lat)
    out = []
    for f in json.loads(raw.read_text(encoding="utf-8")).get("features", []):
        navn = f["properties"].get("offisieltNavn") or f["properties"].get("navn")
        if navn in forbud and f.get("geometry"):
            d = shape(f["geometry"]).distance(Point(x, y))
            if d <= VERN_VARSEL_M:
                out.append(f"{'INNE I' if d == 0 else f'{d:.0f} m fra'} {navn} - vurder forbudet på nytt (data/kandidater/vern_vurdering.json)")
    return "; ".join(out) or None


def save(body):
    pos = json.loads(POS.read_text(encoding="utf-8"))
    p = pos["kandidater"].get(body["id"])
    if p is None or body.get("valg") not in ("G", "U", "A"):
        return False
    if body.get("lat") is not None and body.get("lon") is not None:
        new = {"lat": round(float(body["lat"]), 6), "lon": round(float(body["lon"]), 6)}
        if new != p.get("spot"):
            p.setdefault("startpunkt", p.get("spot"))
            p["spot"] = new
            p["metode"] = body.get("kilde") or "flyttet av Theodor i koordinatsjekk"
    p["vurdering"] = {"G": "godkjent", "U": "usikker", "A": "avvist"}[body["valg"]]
    p["sikkerhet"] = {"G": "godkjent", "U": "usikker", "A": "avvist"}[body["valg"]]
    p["satt_av"] = "theodor"
    p["dato"] = dt.datetime.now().astimezone().isoformat(timespec="minutes")
    if body.get("notat"):
        p["notat_theodor"] = str(body["notat"])[:500]
    varsel = vern_sjekk(body["id"], p["spot"]["lat"], p["spot"]["lon"])
    if varsel:
        p["vern_varsel"] = varsel
    else:
        p.pop("vern_varsel", None)
    POS.write_text(json.dumps(pos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return varsel or True


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/kandidater":
            return self._send(200, json.dumps(payload(), ensure_ascii=False), "application/json")
        if path in ("/vendor/maplibre-gl.js", "/vendor/maplibre-gl.css"):
            f = vendor(path.rsplit("/", 1)[1])
            return self._send(200, f.read_bytes(), "text/css" if path.endswith(".css") else "application/javascript")
        self._send(404, "ikke funnet", "text/plain")

    def do_POST(self):
        if self.path != "/api/vurdering":
            return self._send(404, "ikke funnet", "text/plain")
        n = int(self.headers.get("Content-Length") or 0)
        try:
            r = save(json.loads(self.rfile.read(n)))
        except (ValueError, KeyError):
            r = False
        self._send(200 if r else 400, json.dumps({"ok": bool(r), "vern_varsel": r if isinstance(r, str) else None}, ensure_ascii=False), "application/json")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not POS.exists():
        sys.exit(f"Mangler {POS} - kjør python3 tools/lag_posisjoner.py først")
    print(f"Koordinatsjekk: http://127.0.0.1:{PORT}/  (Ctrl-C for å stoppe; vurderingene lagres i {POS.relative_to(ROOT)})")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
