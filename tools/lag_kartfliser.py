"""Kartfliser for Utforsk (S3, nattjobben 15.-16.10.2026, ROADMAP K del B): land og kystlinje for
hele Norge som vektorfliser (MVT) i PMTiles-filer, fra OpenStreetMap sine landpolygoner
og kystlinjer (osmdata.openstreetmap.de, land-polygons-split-4326 og coastlines-split-4326,
© OpenStreetMap-bidragsytere, ODbL).

To filer, så kartet virker uten nett og resten hentes ved bruk:
  docs/geo/norge-oversikt.pmtiles  z0-OVERSIKT_MAX - liten, precaches hel i sw.js
  docs/geo/norge-detalj.pmtiles    OVERSIKT_MAX+1 - DETALJ_MAX - hentes med range requests, mellomlagres
                                   flis-område for flis-område med tak (sw.js)
MapLibre overzoomer DETALJ_MAX opp til zoom 14.

Lag: «land» (polygoner, fylles) fra landpolygonene, «kyst» (strek) fra OSM sine kystlinjer
(coastlines-split-4326, linjer - aldri omrisset av polygonene, så rammen, flis-kanter og skjøtene mellom
de oppdelte bitene aldri kan tegnes som kyst), og i oversiktens z7 «kjerne» (landet krympet 600 m innover).
Detaljfliser lages bare der det er kyst innen 1 km; inne på land vises kjernen fra oversikten (fra z8),
som aldri når ut i sjøen. Dataene klippes mot en ramme som er større enn kartets
maxBounds (16.10.2026: landet stoppet før i en loddrett strek i øst). Forenklet til ca. en halv
skjermpiksel per zoomnivå (512 px fliser).

Krever: pyshp, shapely 2, pyproj, mapbox-vector-tile, pmtiles (python), og shapefila lokalt
(privat/geodata/land-polygons-split-4326/ og coastlines-split-4326/, ikke i git). Kjør:
  python tools/lag_kartfliser.py [--maks 12] [--oversikt 7]"""
import argparse
import gzip
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
PRIVAT = Path(os.environ.get("NORDSURF_PRIVAT") or "/Users/theodorlund/nordsurf/privat")
SHP = PRIVAT / "geodata" / "land-polygons-split-4326" / "land_polygons.shp"
LINES = PRIVAT / "geodata" / "coastlines-split-4326" / "lines.shp"
OUT = ROOT / "docs" / "geo"
# Rammen for dataene er STØRRE enn kartets maxBounds (docs/js/kart.js: [1, 56.3]-[34, 72.3]), så klippekanten
# alltid ligger utenfor det man kan se (Theodor 16.10: landet stoppet i en loddrett strek i øst ved 33° Ø).
BBOX = (-1.0, 55.0, 36.0, 73.5)          # lon0, lat0, lon1, lat1 (Svalbard ikke med)
R = 6378137.0
WORLD = 2 * math.pi * R
EXTENT = 4096
TILE_PX = 512
COAST_NEAR_M = 1000     # detaljfliser bare der det er kyst innen 1 km (Web Mercator-meter)
KJERNE_M = 600          # Web Mercator-meter (ved 68-70° N ca. 205-225 ekte m; 1 km over er ca. 340-375 m) - «kjerne» = landet krympet 600 m innover (oversikten, vises fra z8): når aldri ut i sjøen
                        # (z7 er forenklet med ca. 300 m), og dekker alt som ligger mer enn ca. 900 m fra kysten -
                        # nærmere kysten finnes det alltid en detaljflis (COAST_NEAR_M) med det ekte landet
TO_MERC = Transformer.from_crs(4326, 3857, always_xy=True)


def merc_bbox():
    x0, y0 = TO_MERC.transform(BBOX[0], BBOX[1])
    x1, y1 = TO_MERC.transform(BBOX[2], BBOX[3])
    return x0, y0, x1, y1


def _read(shp):
    import shapefile
    lo0, la0, lo1, la1 = BBOX
    geoms = []
    with shapefile.Reader(str(shp)) as sf:
        for sh in sf.iterShapes():
            b = sh.bbox
            if b[2] < lo0 or b[0] > lo1 or b[3] < la0 or b[1] > la1:
                continue
            geoms.append(shapely.geometry.shape(sh.__geo_interface__))
    arr = shapely.clip_by_rect(np.array(geoms, dtype=object), *BBOX)
    arr = arr[~shapely.is_empty(arr)]
    return shapely.transform(arr, lambda xy: np.column_stack(TO_MERC.transform(xy[:, 0], xy[:, 1])))


def load_pieces():
    """OSM sine landbiter (land-polygons-split-4326) innenfor rammen, klippet mot den."""
    return shapely.make_valid(_read(SHP))


def load_lines():
    """OSM sine kystlinjer (coastlines-split-4326, linjer) innenfor rammen. Kyststreken tegnes fra disse,
    aldri som omriss av landpolygonene - da kan verken rammen, flis-kanter eller skjøtene mellom de
    oppdelte bitene noen gang bli tegnet som kyst."""
    arr = _read(LINES)
    return np.array([g for a in arr for g in shapely.get_parts(a) if g.geom_type == "LineString"], dtype=object)


LOW_MAX = 7     # z0-7 fra de sammenslåtte polygonene, z8+ fra rå biter slått sammen per flis
MERGED_WKB = PRIVAT / "geodata" / "osm_land_kartramme.wkb"


def load_merged(pieces):
    """Landbitene slått sammen til hele øyer/fastland (mellomlagret i privat/geodata/)."""
    from shapely import wkb
    if MERGED_WKB.exists():
        return shapely.get_parts(wkb.loads(MERGED_WKB.read_bytes()))
    g = shapely.union_all(pieces)
    MERGED_WKB.write_bytes(wkb.dumps(g))
    return shapely.get_parts(g)


def tile_bounds(z, x, y):
    n = 2 ** z
    size = WORLD / n
    minx = -WORLD / 2 + x * size
    maxy = WORLD / 2 - y * size
    return minx, maxy - size, minx + size, maxy


def tile_range(z):
    x0, y0, x1, y1 = merc_bbox()
    n = 2 ** z
    size = WORLD / n
    tx0, tx1 = int((x0 + WORLD / 2) // size), int((x1 + WORLD / 2) // size)
    ty0, ty1 = int((WORLD / 2 - y1) // size), int((WORLD / 2 - y0) // size)
    return range(tx0, tx1 + 1), range(ty0, ty1 + 1)


def to_tile(g, b):
    minx, miny, maxx, maxy = b
    sx, sy = EXTENT / (maxx - minx), EXTENT / (maxy - miny)
    return shapely.transform(g, lambda xy: np.column_stack(((xy[:, 0] - minx) * sx, (maxy - xy[:, 1]) * sy)))


def small_ring(line, min_area):
    """Lukket kystlinje rundt en øy/et skjær under ca. 2x2 piksler (samme grense som landet bruker)."""
    c = shapely.get_coordinates(line)
    return len(c) >= 4 and (c[0] == c[-1]).all() and shapely.Polygon(c).area < min_area


def make_tile(z, x, y, tree, pieces_z, ltree, lines_z, tol=None, detail=False, ktree=None, kjerne_z=None):
    """Land (fyll) fra polygonene, kyst (strek) fra OSM-kystlinjene. pieces_z: forenklede, sammenhengende
    polygoner (lave zoom) eller rå OSM-biter (tol satt - slås sammen per flis FØR forenkling, ellers gir
    uavhengig forenklede naboer smale glipper inne i land). detail: bare fliser med kyst innen COAST_NEAR_M.
    ktree/kjerne_z (oversikten): landets «kjerne» (KJERNE_M innover) som eget lag, vist fra z8."""
    b = tile_bounds(z, x, y)
    size = b[2] - b[0]
    buf = size * 8 / EXTENT          # litt utenfor flisa, så strekene ikke kuttes synlig i kanten
    q = box(b[0] - buf, b[1] - buf, b[2] + buf, b[3] + buf)
    li = ltree.query(q)
    if detail and not len(ltree.query(q.buffer(COAST_NEAR_M))):
        return None                    # ingen kyst nær: oversikten under er riktig (helt land eller helt hav)
    idx = tree.query(q)
    land = shapely.Polygon()
    if len(idx):
        parts = shapely.clip_by_rect(pieces_z[idx], *q.bounds)
        parts = parts[~shapely.is_empty(parts)]
        if len(parts):
            land = shapely.union_all(parts)
            if tol is not None:
                land = shapely.make_valid(shapely.simplify(land, tol, preserve_topology=False))
                if land.geom_type == "GeometryCollection":
                    land = shapely.union_all([g for g in shapely.get_parts(land) if g.geom_type in ("Polygon", "MultiPolygon")])
    coast = shapely.Polygon()
    if len(li):
        cl = shapely.clip_by_rect(lines_z[li], *q.bounds)
        cl = cl[~shapely.is_empty(cl)]
        if len(cl):
            if tol is not None:
                cl = shapely.simplify(cl, tol, preserve_topology=False)
            parts = [g for g in shapely.get_parts(cl) if g.geom_type == "LineString" and not g.is_empty]
            coast = shapely.MultiLineString(parts) if parts else shapely.Polygon()
    if land.is_empty and coast.is_empty:
        return None
    layers = []
    if ktree is not None:
        ki = ktree.query(q)
        if len(ki):
            kp = shapely.clip_by_rect(kjerne_z[ki], *q.bounds)
            kp = kp[~shapely.is_empty(kp)]
            if len(kp):
                layers.append({"name": "kjerne", "features": [{"geometry": to_tile(shapely.union_all(kp), b), "properties": {}}]})
    if not land.is_empty:
        layers.append({"name": "land", "features": [{"geometry": to_tile(land, b), "properties": {}}]})
    if not coast.is_empty:
        layers.append({"name": "kyst", "features": [{"geometry": to_tile(coast, b), "properties": {}}]})
    if not layers:
        return None
    import mapbox_vector_tile
    data = mapbox_vector_tile.encode(layers, default_options={"y_coord_down": True, "extents": EXTENT})
    return gzip.compress(data, 9)


def write_pmtiles(path, tiles, zmin, zmax):
    from pmtiles.tile import Compression, TileType, zxy_to_tileid
    from pmtiles.writer import Writer
    with open(path, "wb") as f:
        w = Writer(f)
        for (z, x, y), data in sorted(tiles.items(), key=lambda kv: zxy_to_tileid(*kv[0])):
            w.write_tile(zxy_to_tileid(z, x, y), data)
        w.finalize({"tile_type": TileType.MVT, "tile_compression": Compression.GZIP,
                    "min_zoom": zmin, "max_zoom": zmax,
                    "min_lon_e7": int(BBOX[0] * 1e7), "min_lat_e7": int(BBOX[1] * 1e7),
                    "max_lon_e7": int(BBOX[2] * 1e7), "max_lat_e7": int(BBOX[3] * 1e7),
                    "center_zoom": 5, "center_lon_e7": int(15 * 1e7), "center_lat_e7": int(66 * 1e7)},
                   {"name": "Nordsurf kyst", "attribution": "© OpenStreetMap-bidragsytere",
                    "vector_layers": [{"id": "land", "fields": {}}, {"id": "kjerne", "fields": {}}, {"id": "kyst", "fields": {}}]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maks", type=int, default=12)
    ap.add_argument("--oversikt", type=int, default=7)
    ap.add_argument("--bare-mal", action="store_true", help="bare mål størrelse per zoom, skriv ikke filer")
    a = ap.parse_args()
    t0 = time.time()
    pieces = load_pieces()
    print(f"{len(pieces)} landbiter i rammen ({time.time() - t0:.0f} s)", flush=True)
    lines = load_lines()
    print(f"{len(lines)} kystlinjebiter i rammen ({time.time() - t0:.0f} s)", flush=True)
    tree, ltree = shapely.STRtree(pieces), shapely.STRtree(lines)
    piece_area = shapely.area(pieces)
    merged = load_merged(pieces)
    print(f"{len(merged)} sammenhengende landpolygoner ({time.time() - t0:.0f} s)", flush=True)
    mtree = shapely.STRtree(merged)
    big = merged[shapely.area(merged) > (2 * KJERNE_M) ** 2]
    kjerne = shapely.buffer(big, -KJERNE_M)
    kjerne = kjerne[~shapely.is_empty(kjerne)]
    ktree = shapely.STRtree(kjerne)
    print(f"{len(kjerne)} kjerne-polygoner ({time.time() - t0:.0f} s)", flush=True)
    tiles, stats = {}, {}
    for z in range(0, a.maks + 1):
        tol = WORLD / 2 ** z / TILE_PX * 0.5         # en halv skjermpiksel
        min_area = (2 * WORLD / 2 ** z / TILE_PX) ** 2  # øyer/skjær under ca. 2x2 piksler tas bort (usynlige)
        lz = np.where([small_ring(g, min_area) for g in lines], shapely.LineString(), lines)
        low = z <= a.oversikt
        if low:
            pz = shapely.simplify(merged, tol, preserve_topology=True)
            pz = np.where((shapely.area(pz) < min_area) | shapely.is_empty(pz), shapely.Polygon(), pz)
            lz = shapely.simplify(lz, tol, preserve_topology=False)
            kz = shapely.simplify(kjerne, tol, preserve_topology=True) if z == a.oversikt else None
        else:
            praw = np.where(piece_area < min_area, shapely.Polygon(), pieces)
        xs, ys = tile_range(z)
        n, size, tz = 0, 0, time.time()
        for x in xs:
            for y in ys:
                d = (make_tile(z, x, y, mtree, pz, ltree, lz, ktree=ktree if kz is not None else None, kjerne_z=kz) if low
                     else make_tile(z, x, y, tree, praw, ltree, lz, tol=tol, detail=True))
                if d:
                    tiles[(z, x, y)] = d
                    n += 1
                    size += len(d)
        stats[z] = (n, size)
        print(f"z{z:2}: {n:6} fliser, {size / 1e6:7.2f} MB ({time.time() - tz:.0f} s)", flush=True)
    if a.bare_mal:
        print(json.dumps(stats))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    lo = {k: v for k, v in tiles.items() if k[0] <= a.oversikt}
    hi = {k: v for k, v in tiles.items() if k[0] > a.oversikt}
    write_pmtiles(OUT / "norge-oversikt.pmtiles", lo, 0, a.oversikt)
    write_pmtiles(OUT / "norge-detalj.pmtiles", hi, a.oversikt + 1, a.maks)
    for f in ("norge-oversikt.pmtiles", "norge-detalj.pmtiles"):
        print(f, f"{(OUT / f).stat().st_size / 1e6:.2f} MB")
    print(f"Ferdig på {time.time() - t0:.0f} s")


if __name__ == "__main__":
    sys.exit(main())
