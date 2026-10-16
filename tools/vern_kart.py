"""Kart over et verneområde mot kandidatpinnen (Theodor 16.10.2026, svar 3.3): tegner grensen til
naturreservatet (Naturbase, Miljødirektoratet, NLOD), listepinnen, OSM-kysten og -strendene og stedsnavn,
så det kan avgjøres om selve bølgen ligger innenfor. Skriver data/kandidater/vern/<id>.png og skriver
avstander til terminalen.

  python tools/vern_kart.py <id> "<verneområdets navn>" [...]"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import shapely  # noqa: E402
from pyproj import Transformer  # noqa: E402
from shapely.geometry import Point, shape  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import kystdata  # noqa: E402

BEVIS = ROOT / "privat" / "kandidater" / "bevis"
OUT = ROOT / "data" / "kandidater" / "vern"
TO = Transformer.from_crs(4326, 25833, always_xy=True)
R = 1500


def main(kid, navn):
    k = {x["id"]: x for x in json.loads((ROOT / "data/kandidater/kandidater.json").read_text(encoding="utf-8"))["kandidater"]}[kid]
    pin = k["pin_liste"]
    px, py = TO.transform(pin["lon"], pin["lat"])
    nb = json.loads((BEVIS / "vern" / f"naturbase_{kid}.json").read_text(encoding="utf-8"))
    res = [shape(f["geometry"]) for f in nb["features"] if (f["properties"].get("offisieltNavn") or f["properties"].get("navn")) == navn]
    if not res:
        sys.exit(f"Fant ikke «{navn}» i Naturbase-treffene for {kid}")
    reservat = shapely.union_all(res)
    land = kystdata.land("osm")
    clip = shapely.clip_by_rect(land, pin["lon"] - 0.08, pin["lat"] - 0.03, pin["lon"] + 0.08, pin["lat"] + 0.03)
    land_u = shapely.transform(clip, lambda xy: np.column_stack(TO.transform(xy[:, 0], xy[:, 1])))
    sn = json.loads((BEVIS / kid / "stedsnavn.json").read_text(encoding="utf-8"))
    osm = json.loads((BEVIS / kid / "osm.json").read_text(encoding="utf-8"))

    fig, ax = plt.subplots(figsize=(7, 7), dpi=120)
    ax.set_facecolor("#B7D3DF")
    for p in getattr(land_u, "geoms", [land_u]):
        if p.geom_type == "Polygon":
            ax.fill(*p.exterior.xy, color="#F2EDE2", ec="#8F8268", lw=0.7)
    for p in getattr(reservat, "geoms", [reservat]):
        if p.geom_type == "Polygon":
            ax.fill(*p.exterior.xy, color="#22A36B", alpha=0.25, ec="#167A4F", lw=2)
    for e in osm.get("elements", []):
        if e.get("tags", {}).get("natural") in ("beach", "sand", "shingle") and e.get("geometry"):
            xy = np.array([TO.transform(n["lon"], n["lat"]) for n in e["geometry"]])
            ax.plot(xy[:, 0], xy[:, 1], color="#B8441F", lw=1.8)
    seen = set()
    for h in sn.get("navn_treff", []) + sn.get("naer", []):
        x, y = TO.transform(h["lon"], h["lat"])
        if abs(x - px) < R and abs(y - py) < R and h["navn"] not in seen:
            seen.add(h["navn"])
            ax.plot(x, y, "o", ms=4, color="#0B7483")
            ax.annotate(f"{h['navn']} ({h['type']})", (x, y), fontsize=7, xytext=(4, 3), textcoords="offset points")
    ax.plot(px, py, "o", ms=10, color="#7D8C95", mec="white", label=f"listepinne {k['name']}")
    for r_ in (100, 300):
        ax.add_patch(plt.Circle((px, py), r_, fill=False, ls="--", lw=0.8, color="#55656E"))
    d = reservat.distance(Point(px, py))
    ax.set_xlim(px - R, px + R)
    ax.set_ylim(py - R, py + R)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"{k['name']}: {navn} (grønt) - pinnen {d:.0f} m unna. Ringer 100/300 m. Strender (OSM) rødt.", fontsize=8)
    ax.legend(loc="lower left", fontsize=7)
    ax.text(0.99, 0.01, "Verneområde © Miljødirektoratet (NLOD) · kyst/strender © OpenStreetMap-bidragsytere · stedsnavn © Kartverket · 3 × 3 km",
            transform=ax.transAxes, ha="right", fontsize=5.5)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{kid}.png", bbox_inches="tight")
    plt.close(fig)
    sea = shapely.difference(reservat, land_u)
    print(f"{kid}: pinnen {d:.0f} m fra «{navn}»; reservatets sjøareal {sea.area / 1000:.0f} daa; skrev {OUT / (kid + '.png')}")


if __name__ == "__main__":
    a = sys.argv[1:]
    for i in range(0, len(a), 2):
        main(a[i], a[i + 1])
