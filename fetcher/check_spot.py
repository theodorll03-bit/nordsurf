"""Sjekker at en spot har rett, fri linje til åpent hav, og foreslår havpunkt.

Krever kystlinjedata (stor nedlasting, bare for dette verktøyet):
    pip install basemap basemap-data-hires shapely
Kjør: python fetcher/check_spot.py <lat> <lon> <fra_grad> <til_grad>
"""
import sys, math
from mpl_toolkits.basemap import Basemap
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep

lat, lon, w0, w1 = map(float, sys.argv[1:5])
m = Basemap(projection="cyl", llcrnrlat=lat - 1.5, urcrnrlat=lat + 1.8,
            llcrnrlon=lon - 4.5, urcrnrlon=lon + 4.5, resolution="f")
land = prep(unary_union([Polygon(list(zip(*xy))).buffer(0)
                         for xy, t in zip(m.coastpolygons, m.coastpolygontypes) if t == 1 and len(xy[0]) > 2]))

def pt(b, d, la=lat, lo=lon):
    return (la + d * math.cos(math.radians(b)) / 110.57,
            lo + d * math.sin(math.radians(b)) / (111.32 * math.cos(math.radians(la))))

def is_land(la, lo):
    return land.contains(Point(lo, la))

def free_distance(b, maxd=150):
    d, start = 0.0, None
    while d < maxd:
        onl = is_land(*pt(b, d))
        if start is None:
            if not onl:
                start = d
            elif d > 2:
                return 0
        elif onl:
            return d - start
        d += 0.1
    return maxd

def inwin(b):
    return w0 <= b <= w1 if w0 <= w1 else (b >= w0 or b <= w1)

open_b = [b for b in range(360) if inwin(b) and free_distance(b) >= 150]
if not open_b:
    sys.exit("Ingen retning i vinduet har fri linje til åpent hav.")
secs = []
for b in open_b:
    if secs and b - secs[-1][1] == 1:
        secs[-1][1] = b
    else:
        secs.append([b, b])
if len(secs) > 1 and secs[0][0] == 0 and secs[-1][1] == 359:
    secs[0][0] = secs.pop()[0]
main = max(secs, key=lambda s: (s[1] - s[0]) % 360)
c = (main[0] + ((main[1] - main[0]) % 360) / 2) % 360
d = 5
while any(is_land(*pt(b, r, *pt(c, d))) for b in range(0, 360, 10) for r in (5, 10)):
    d += 1
print("Fri sikt til åpent hav:", secs)
print(f"Havpunkt: {pt(c, d)[0]:.4f}, {pt(c, d)[1]:.4f} ({d} km ut, retning {c:.0f} grader)")
