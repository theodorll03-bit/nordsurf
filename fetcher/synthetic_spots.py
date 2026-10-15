"""Syntetiske spots til skaleringstestene (Tillegg 2, Theodor 15.10.2026): N spots spredt
langs hele norskekysten, hver med timene (og meta) kopiert fra en ekte spot i et varsel,
så oversikt.json/appen kan testes med 100+ spots uten nye tall. Bare til tester - aldri
publisert. Koordinatene følger en grov kystlinje (Lindesnes -> Nordkapp), regionen følger
breddegraden, navnene er «Testspot NNN»."""
import copy
import json
import math

# grov kyst (lat, lon) sør -> nord
COAST = [(58.0, 7.0), (58.9, 5.6), (59.9, 5.1), (61.0, 4.9), (62.0, 5.1), (62.6, 6.3), (63.4, 8.0),
         (64.5, 10.5), (65.5, 12.0), (66.5, 12.8), (67.5, 13.5), (68.3, 13.7), (69.0, 16.5), (69.8, 18.8),
         (70.2, 21.5), (70.6, 24.5), (71.0, 25.8)]
REGIONS = [(58.0, "Agder"), (58.6, "Rogaland"), (59.8, "Vestland"), (62.3, "Møre og Romsdal"), (63.3, "Trøndelag"),
           (65.0, "Nordland"), (67.4, "Lofoten"), (68.6, "Troms"), (70.0, "Finnmark")]


def region_for(lat):
    r = REGIONS[0][1]
    for lo, name in REGIONS:
        if lat >= lo:
            r = name
    return r


def point_along(f):
    """Punkt f (0-1) langs kysten, lineært mellom knekkpunktene."""
    n = len(COAST) - 1
    x = f * n
    i = min(n - 1, int(x))
    t = x - i
    (a1, o1), (a2, o2) = COAST[i], COAST[i + 1]
    return a1 + (a2 - a1) * t, o1 + (o2 - o1) * t


def make(forecast, n=100, seed=1):
    """Varsel med n syntetiske spots (deterministisk): timene og meta fra de ekte spotene etter tur."""
    base = [s for s in forecast["spots"] if s.get("enabled", True)]
    out = copy.deepcopy({k: v for k, v in forecast.items() if k != "spots"})
    spots = []
    for k in range(n):
        src = copy.deepcopy(base[k % len(base)])
        f = (k + 0.5) / n
        lat, lon = point_along(f)
        # liten, deterministisk spredning så to spots i samme region ikke ligger oppå hverandre
        lat += 0.02 * math.sin(k * 1.7 + seed)
        lon += 0.03 * math.cos(k * 2.3 + seed)
        src["id"] = f"test{k:03d}"
        src["name"] = f"Testspot {k:03d}"
        src["area"] = f"Område {k // 10}"
        src["region"] = region_for(lat)
        src["aliases"] = [f"T{k}"]
        src["spot"] = {"lat": round(lat, 5), "lon": round(lon, 5)}
        src["status"] = None
        spots.append(src)
    out["spots"] = spots
    regions = []
    for name in dict.fromkeys(s["region"] for s in spots):
        regions.append({"name": name, "order": len(regions) + 1})
    return out, regions


if __name__ == "__main__":
    import sys
    fc = json.load(open(sys.argv[1]))
    out, regions = make(fc, int(sys.argv[2]) if len(sys.argv) > 2 else 100)
    print(json.dumps({"spots": [(s["id"], s["region"], s["spot"]) for s in out["spots"]][:5], "regions": regions}, ensure_ascii=False))
