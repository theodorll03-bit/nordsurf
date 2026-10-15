"""Kartfliser for Utforsk (S3, nattjobben 15.-16.10.2026, ROADMAP K del B): land og kystlinje for
hele Norge som vektorfliser (MVT) i PMTiles-filer, fra OpenStreetMap sine landpolygoner
(osmdata.openstreetmap.de, land-polygons-split-4326, © OpenStreetMap-bidragsytere, ODbL).

To filer, så kartet virker uten nett og resten hentes ved bruk:
  docs/geo/norge-oversikt.pmtiles  z0-OVERSIKT_MAX - liten, precaches hel i sw.js
  docs/geo/norge-detalj.pmtiles    OVERSIKT_MAX+1 - DETALJ_MAX - hentes med range requests, mellomlagres
                                   flis-område for flis-område med tak (sw.js)
MapLibre overzoomer DETALJ_MAX opp til zoom 14.

Hver flis har to lag: «land» (polygoner, fylles) og «kyst» (bare ekte kystlinje - flis-kanter og
skjøtene mellom OSM sine oppdelte biter er tatt bort, så streken aldri tegner rutenett). Forenklet
til ca. en halv skjermpiksel per zoomnivå (512 px fliser).

Krever: pyshp, shapely 2, pyproj, mapbox-vector-tile, pmtiles (python), og shapefila lokalt
(privat/geodata/land-polygons-split-4326/, ikke i git). Kjør:
  python tools/lag_kartfliser.py [--maks 11] [--oversikt 7]"""
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
OUT = ROOT / "docs" / "geo"
BBOX = (2.0, 56.8, 33.0, 71.8)          # lon0, lat0, lon1, lat1 - fastlands-Norge med litt luft (Svalbard ikke med)
R = 6378137.0
WORLD = 2 * math.pi * R
EXTENT = 4096
TILE_PX = 512
TO_MERC = Transformer.from_crs(4326, 3857, always_xy=True)


def merc_bbox():
    x0, y0 = TO_MERC.transform(BBOX[0], BBOX[1])
    x1, y1 = TO_MERC.transform(BBOX[2], BBOX[3])
    return x0, y0, x1, y1


def load_pieces():
    import shapefile
    lo0, la0, lo1, la1 = BBOX
    geoms = []
    with shapefile.Reader(str(SHP)) as sf:
        for sh in sf.iterShapes():
            b = sh.bbox
            if b[2] < lo0 or b[0] > lo1 or b[3] < la0 or b[1] > la1:
                continue
            geoms.append(shapely.geometry.shape(sh.__geo_interface__))
    arr = np.array(geoms, dtype=object)
    arr = shapely.transform(arr, lambda xy: np.column_stack(TO_MERC.transform(xy[:, 0], xy[:, 1])))
    return shapely.make_valid(arr)


LOW_MAX = 7     # z0-7 fra de sammenslåtte polygonene, z8+ fra rå biter slått sammen per flis
MERGED_WKB = PRIVAT / "geodata" / "osm_land_norge.wkb"   # tools/kystdata.py (grenen kandidater/import)


def load_merged():
    """De samme OSM-bitene slått sammen til hele øyer/fastland (wkb fra tools/kystdata.py, eller bygget her)."""
    from shapely import wkb
    if MERGED_WKB.exists():
        g = wkb.loads(MERGED_WKB.read_bytes())
    else:
        sys.exit(f"Mangler {MERGED_WKB} - kjør tools/kystdata.py først (bygger den fra samme shapefil)")
    parts = shapely.get_parts(g)
    return shapely.transform(parts, lambda xy: np.column_stack(TO_MERC.transform(xy[:, 0], xy[:, 1])))


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


def make_tile(z, x, y, tree, pieces_z, tol=None):
    """pieces_z: allerede forenklede, sammenhengende polygoner (lave zoom), eller rå OSM-biter (tol satt):
    da slås bitene sammen FØR forenkling - ellers gir uavhengig forenklede naboer smale glipper som
    tegnes som streker inne i land."""
    b = tile_bounds(z, x, y)
    size = b[2] - b[0]
    buf = size * 8 / EXTENT          # litt utenfor flisa, så strekene ikke kuttes synlig i kanten
    q = box(b[0] - buf, b[1] - buf, b[2] + buf, b[3] + buf)
    idx = tree.query(q)
    if not len(idx):
        return None                    # bare hav
    parts = shapely.clip_by_rect(pieces_z[idx], *q.bounds)
    parts = parts[~shapely.is_empty(parts)]
    if not len(parts):
        return None
    land = shapely.union_all(parts)
    if tol is not None:
        land = shapely.make_valid(shapely.simplify(land, tol, preserve_topology=False))
        if land.geom_type == "GeometryCollection":
            land = shapely.union_all([g for g in shapely.get_parts(land) if g.geom_type in ("Polygon", "MultiPolygon")])
    if land.is_empty:
        return None
    full = land.area >= q.area * 0.99999
    # kystlinje = kanten av land, minus klippekanten (flis + buffer) - skjøtene mellom bitene er borte etter union
    coast = None if full else shapely.difference(land.boundary, q.exterior.buffer(size * 1e-6))
    feats_land = [{"geometry": to_tile(land, b), "properties": {}}]
    layers = [{"name": "land", "features": feats_land}]
    if coast is not None and not coast.is_empty:
        layers.append({"name": "kyst", "features": [{"geometry": to_tile(coast, b), "properties": {}}]})
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
                    "vector_layers": [{"id": "land", "fields": {}}, {"id": "kyst", "fields": {}}]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maks", type=int, default=11)
    ap.add_argument("--oversikt", type=int, default=7)
    ap.add_argument("--bare-mal", action="store_true", help="bare mål størrelse per zoom, skriv ikke filer")
    a = ap.parse_args()
    t0 = time.time()
    pieces = load_pieces()
    print(f"{len(pieces)} landbiter i rammen ({time.time() - t0:.0f} s)", flush=True)
    tree = shapely.STRtree(pieces)
    piece_area = shapely.area(pieces)
    merged = load_merged()
    print(f"{len(merged)} sammenhengende landpolygoner ({time.time() - t0:.0f} s)", flush=True)
    mtree = shapely.STRtree(merged)
    tiles = {}
    stats = {}
    for z in range(0, a.maks + 1):
        tol = WORLD / 2 ** z / TILE_PX * 0.5         # en halv skjermpiksel
        low = z <= LOW_MAX
        if low:
            # lave zoom: hele, sammenslåtte polygoner (ingen skjøter) forenklet én gang per zoom
            pz = shapely.simplify(merged, tol, preserve_topology=True)
            # små øyer under ca. 2x2 piksler tas bort (usynlige uansett)
            tiny = shapely.area(pz) < (2 * WORLD / 2 ** z / TILE_PX) ** 2
            pz = np.where(tiny | shapely.is_empty(pz), shapely.Polygon(), pz)
        else:
            # høye zoom: rå biter, men øyer/skjær under ca. 2x2 piksler tas bort (målt på hele biten, så
            # oppdelte fastlandsbiter ikke forsvinner - de er større enn rutenettets minste rester)
            praw = np.where(piece_area < (2 * WORLD / 2 ** z / TILE_PX) ** 2, shapely.Polygon(), pieces)
        xs, ys = tile_range(z)
        n, size = 0, 0
        tz = time.time()
        for x in xs:
            for y in ys:
                d = make_tile(z, x, y, mtree, pz) if low else make_tile(z, x, y, tree, praw, tol)
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
