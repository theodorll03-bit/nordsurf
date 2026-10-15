"""Minikart per spot (Theodor 14.10.2026, punkt 4c): den lokale kystlinjen i en
sirkel med radius 3,5 km rundt spoten, som forenklede SVG-stier, lagret i
docs/data/minikart.json (lastes bare på spotsiden).

Kilde: OpenStreetMap sin kystlinje (natural=coastline) via Overpass API -
samme kilde som S3 skal bruke (ROADMAP oppgave S, Theodors svar 2: ikke
GSHHS til visning). Kreditering i appen: «© OpenStreetMap-bidragsytere».

Koordinater: viewBox -100…100, x = Δlon·cos(lat0)·111,32 km, y = -Δlat·110,57 km,
skalert med 100/3,5. Nord opp. Toleranse i forenklingen ca. 15 m.

Land og sjø: OSM tegner kystlinjen med land på VENSTRE side av retningen.
Sirkelen deles opp av kystlinjene (shapely polygonize); hver flate får land
eller sjø etter hvilken side av nærmeste kystlinjesegment flatens punkt ligger.

Henting: curl (denne maskinens Python har en LibreSSL som ikke får håndhilst
på overpass-api.de); requests brukes hvis curl mangler. Alle kall har frist.
Kjør: python tools/lag_minikart.py [--spot <id>] [--out docs/data/minikart.json]"""
import argparse
import datetime as dt
import json
import math
import subprocess
import sys
import time
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, split, unary_union

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data" / "minikart.json"
PREVIEW_DIR = ROOT / "docs" / "design" / "spotside" / "minikart"
RADIUS_KM = 3.5
SCALE = 100 / RADIUS_KM
TOL_KM = 0.015
UA = "nordsurf-minikart (tools/lag_minikart.py, github.com/theodorll03-bit/nordsurf)"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


CACHE_DIR = None   # --cache <mappe>: rå Overpass-svar per spot (til utvikling, ikke committet)


def overpass(lat, lon, radius_m, key=None):
    """Rå Overpass-svar. Den offentlige tjenesten køer forespørsler (39 s ventetid
    sett 15.10.2026) - lang frist, nytt forsøk med pause, og mellomlager per spot."""
    cache = CACHE_DIR / f"{key}.json" if (CACHE_DIR and key) else None
    if cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    q = f'[out:json][timeout:90];(way["natural"="coastline"](around:{radius_m},{lat},{lon}););out geom;'
    last = None
    for attempt in range(3):
        for url in OVERPASS:
            try:
                r = subprocess.run(["curl", "-sS", "-m", "120", "-A", UA, "--data-urlencode", f"data={q}", url],
                                   capture_output=True, text=True, timeout=130)
                if r.returncode == 0 and r.stdout.strip().startswith("{"):
                    data = json.loads(r.stdout)
                    if cache:
                        cache.write_text(json.dumps(data), encoding="utf-8")
                    return data
                last = f"curl rc={r.returncode}: {r.stderr.strip()[:120]} {r.stdout[:80]!r}"
            except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
                last = repr(e)[:160]
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"Overpass svarte ikke: {last}")


def project(lat0, lon0):
    k = math.cos(math.radians(lat0))
    def f(lat, lon):   # km, y nordover (positiv = nord) - snus til SVG ved skriving
        return ((lon - lon0) * k * 111.32, (lat - lat0) * 110.57)
    return f


def side_is_land(point, segments):
    """Nærmeste kystlinjesegment avgjør: land på venstre side av retningen (OSM)."""
    best, bd = None, None
    for a, b, seg in segments:
        d = seg.distance(point)
        if bd is None or d < bd:
            bd, best = d, (a, b)
    if best is None:
        return False
    (ax, ay), (bx, by) = best
    cross = (bx - ax) * (point.y - ay) - (by - ay) * (point.x - ax)
    return cross > 0


def svg_path(poly_or_line, closed):
    def ring(coords):
        pts = [f"{x * SCALE:.1f},{-y * SCALE:.1f}" for x, y in coords]
        return "M" + "L".join(pts) + ("Z" if closed else "")
    if closed:
        return ring(poly_or_line.exterior.coords) + "".join(ring(i.coords) for i in poly_or_line.interiors)
    return ring(poly_or_line.coords)


def build(spot):
    lat0, lon0 = spot["spot"]["lat"], spot["spot"]["lon"]
    data = overpass(lat0, lon0, int(RADIUS_KM * 1000) + 800, key=spot["id"])
    proj = project(lat0, lon0)
    circle = Point(0, 0).buffer(RADIUS_KM, 128)
    # linjene klippes mot en LITT større sirkel, så de krysser den ekte randen i stedet
    # for å ende nøyaktig på den (da får split() en ekte krysning å dele etter)
    circle_big = Point(0, 0).buffer(RADIUS_KM + 0.3, 128)
    lines, segments, islands = [], [], []
    for w in data.get("elements", []):
        if w.get("type") != "way" or len(w.get("geometry", [])) < 2:
            continue
        pts = [proj(p["lat"], p["lon"]) for p in w["geometry"]]
        closed = len(pts) > 3 and abs(pts[0][0] - pts[-1][0]) < 1e-9 and abs(pts[0][1] - pts[-1][1]) < 1e-9
        if closed:
            # lukket kystlinje = øy/holme (OSM tegner dem mot klokka, land innenfor)
            poly = Polygon(pts)
            if not poly.is_valid:
                poly = poly.buffer(0)
            piece = poly.intersection(circle)
            if not piece.is_empty:
                islands.append(piece)
            continue
        # retningen (land på venstre side) tas fra de ORIGINALE segmentene - shapely
        # sin klipping kan snu en linje, og da ville land og sjø byttet plass
        for a, b in zip(pts, pts[1:]):
            if max(abs(a[0]), abs(a[1]), abs(b[0]), abs(b[1])) <= RADIUS_KM + 0.8:
                segments.append((a, b, LineString([a, b])))
        lines.append(LineString(pts))
    # OSM deler kysten i mange korte ways - slå dem sammen til sammenhengende linjer FØR
    # klippingen, ellers kan en way som starter og slutter inne i sirkelen ikke dele den
    merged = linemerge(lines) if len(lines) > 1 else (lines[0] if lines else None)
    lines = []
    for ln in ([merged] if merged is not None and merged.geom_type == "LineString" else list(getattr(merged, "geoms", []))):
        clipped = ln.intersection(circle_big)
        for part in ([clipped] if clipped.geom_type == "LineString" else list(getattr(clipped, "geoms", []))):
            if not part.is_empty and part.geom_type == "LineString":
                lines.append(part)
    # åpne kystlinjer deler sirkelen i flater (split, ikke polygonize: snap treffer bare
    # hjørner, og uten eksakt noding mot sirkelen ble hele sirkelen ÉN flate)
    pieces = [circle]
    for ln in lines:
        nxt = []
        for pc in pieces:
            try:
                r = split(pc, ln)
                nxt.extend(g for g in r.geoms if g.geom_type == "Polygon" and g.area > 1e-9)
            except Exception:   # noqa: BLE001 - en linje som ikke deler flaten
                nxt.append(pc)
        pieces = nxt
    faces = pieces
    land_polys = [pc for pc in pieces if segments and side_is_land(pc.representative_point(), segments)] + islands
    face_area = sum(f.area for f in faces)
    spot_on_land = side_is_land(Point(0, 0), segments) if segments else None
    land_union = unary_union(land_polys) if land_polys else None
    land_out = []
    if land_union is not None and not land_union.is_empty:
        geoms = [land_union] if land_union.geom_type == "Polygon" else list(land_union.geoms)
        for g in geoms:
            gs = g.simplify(TOL_KM, preserve_topology=True)
            if not gs.is_empty and gs.area > 1e-4:
                land_out.append(svg_path(gs, True))
    coast_out = []
    for ln in lines:
        s = ln.intersection(circle).simplify(TOL_KM, preserve_topology=True)
        if s.geom_type == "MultiLineString":
            for g in s.geoms:
                if g.length > 0.02:
                    coast_out.append(svg_path(g, False))
            continue
        if s.geom_type != "LineString":
            continue
        if not s.is_empty and s.length > 0.02:
            coast_out.append(svg_path(s, False))
    land_share = (land_union.area / circle.area) if land_union is not None and not land_union.is_empty else 0.0
    return {"lat": lat0, "lon": lon0, "land": land_out, "coast": coast_out,
            "n_ways": sum(1 for e in data.get("elements", []) if e.get("type") == "way"), "land_share": round(land_share, 3),
            "_faces": len(faces), "_face_cover": round(face_area / circle.area, 3), "_spot_on_land": spot_on_land}


def preview_svg(spot, mk):
    land = "".join(f'<path d="{d}" fill="#F2EDE2"/>' for d in mk["land"])
    coast = "".join(f'<path d="{d}" fill="none" stroke="#8F8268" stroke-width="0.8"/>' for d in mk["coast"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-110 -110 220 220" width="440" height="440">'
            f'<clipPath id="c"><circle r="100"/></clipPath><circle r="100" fill="#B7D3DF"/>'
            f'<g clip-path="url(#c)">{land}{coast}</g><circle r="100" fill="none" stroke="#55656E"/>'
            f'<circle r="2.5" fill="#0E1A21"/><text x="0" y="-103" text-anchor="middle" font-size="7" font-family="sans-serif">N · {spot["name"]} · 3,5 km</text></svg>')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spot", help="bare denne spot-id-en")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--cache", help="mappe for rå Overpass-svar (utvikling)")
    a = ap.parse_args()
    global CACHE_DIR
    if a.cache:
        CACHE_DIR = Path(a.cache); CACHE_DIR.mkdir(parents=True, exist_ok=True)
    spots = [s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]
             if s.get("enabled") and s.get("status") != "hemmelig" and (not a.spot or s["id"] == a.spot)]
    out_path = Path(a.out)
    existing = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    result = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "radius_km": RADIUS_KM,
              "source": "OpenStreetMap-bidragsytere (ODbL), natural=coastline via Overpass API", "viewbox": [-100, 100],
              "spots": dict(existing.get("spots", {}))}
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for s in spots:
        t0 = time.time()
        mk = build(s)
        result["spots"][s["id"]] = mk
        (PREVIEW_DIR / f"{s['id']}.svg").write_text(preview_svg(s, mk), encoding="utf-8")
        print(f"{s['name']:16} {mk['n_ways']:3} ways, {len(mk['coast'])} kystlinjer, {mk['_faces']} flater dekker {mk['_face_cover']*100:.0f} %, "
              f"{len(mk['land'])} landflater = {mk['land_share']*100:.0f} % av sirkelen, pinnen på land: {mk['_spot_on_land']} ({time.time()-t0:.1f} s)")
        for k in ("_faces", "_face_cover", "_spot_on_land"):
            mk.pop(k, None)
        time.sleep(4)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Skrev {out_path} ({out_path.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
