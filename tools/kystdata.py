"""Kystlinje for hele Norge til kandidatverktøyene (ROADMAP K, 15.10.2026): to land-masker, lagret
lokalt (aldri i git) i privat/geodata/:

- gshhs_f_norge.wkb: GSHHS full oppløsning via basemap - det fysikken bruker i dag (check_spot.py,
  exposure_baseline.py). Mangler små øyer og skjær.
- osm_land_norge.wkb: OpenStreetMap sine landpolygoner (osmdata.openstreetmap.de,
  land-polygons-split-4326, © OpenStreetMap-bidragsytere, ODbL). Norges kystlinje i OSM er i stor
  grad importert fra Kartverkets N50, så den brukes her i stedet for N50 kystkontur (N50 finnes bare
  som bestilling per kommune hos Geonorge).

land(kilde) gir en shapely-geometri i lon/lat (EPSG:4326). Første kjøring bygger filene
(OSM: leser 1,3 GB shapefil, et par minutter); senere kjøringer leser wkb-filene.

Kjør: python tools/kystdata.py   (bygger begge og skriver størrelse)"""
import os
import sys
import time
from pathlib import Path

import shapely
from shapely import wkb
from shapely.geometry import box, shape

ROOT = Path(__file__).resolve().parent.parent
GEO = Path(os.environ.get("NORDSURF_PRIVAT") or ROOT / "privat") / "geodata"
NORGE_BBOX = (3.0, 57.0, 32.5, 71.6)   # lon0, lat0, lon1, lat1
OSM_SHP = GEO / "land-polygons-split-4326" / "land_polygons.shp"
FILES = {"gshhs": GEO / "gshhs_f_norge.wkb", "osm": GEO / "osm_land_norge.wkb"}
_cache = {}


def _build_gshhs():
    from mpl_toolkits.basemap import Basemap
    from shapely.geometry import Polygon
    lo0, la0, lo1, la1 = NORGE_BBOX
    m = Basemap(projection="cyl", llcrnrlat=la0, urcrnrlat=la1, llcrnrlon=lo0, urcrnrlon=lo1, resolution="f")
    polys = [Polygon(list(zip(*xy))).buffer(0) for xy, t in zip(m.coastpolygons, m.coastpolygontypes) if t == 1 and len(xy[0]) > 2]
    return shapely.union_all(polys)


def _build_osm():
    import shapefile
    if not OSM_SHP.exists():
        sys.exit(f"Mangler {OSM_SHP} - last ned land-polygons-split-4326.zip fra osmdata.openstreetmap.de og pakk ut i {GEO}")
    lo0, la0, lo1, la1 = NORGE_BBOX
    keep = []
    with shapefile.Reader(str(OSM_SHP)) as sf:
        for sh in sf.iterShapes():
            b = sh.bbox
            if b[2] < lo0 or b[0] > lo1 or b[3] < la0 or b[1] > la1:
                continue
            keep.append(shape(sh.__geo_interface__).buffer(0))
    return shapely.union_all(keep).intersection(box(*NORGE_BBOX))


def land(kilde):
    """Land-geometrien for 'gshhs' eller 'osm' (lon/lat)."""
    if kilde in _cache:
        return _cache[kilde]
    f = FILES[kilde]
    if f.exists():
        g = wkb.loads(f.read_bytes())
    else:
        t = time.time()
        g = _build_gshhs() if kilde == "gshhs" else _build_osm()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(wkb.dumps(g))
        print(f"Bygde {f.name} på {time.time() - t:.0f} s ({f.stat().st_size / 1e6:.1f} MB)")
    _cache[kilde] = g
    return g


if __name__ == "__main__":
    for k in FILES:
        g = land(k)
        print(k, g.geom_type, f"{FILES[k].stat().st_size / 1e6:.1f} MB")
