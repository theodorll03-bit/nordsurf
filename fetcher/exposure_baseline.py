"""Glidende geometrisk utgangspunkt for eksponering per retning (del C,
26.09.2026) - brukes i reservemodellen der BarentsWatch ikke har lært nok
ennå (se calibrate.blend_exposure()). Erstatter etter hvert av seg selv av
ekte, lærte data fra BarentsWatch (del B) - se README "Eksponering per
retning".

Manuelt verktøy, kjøres sjelden (ikke i hver fetch.py-kjøring), samme tunge
avhengighet som check_spot.py:
    pip install basemap basemap-data-hires shapely
Kjør: python fetcher/exposure_baseline.py
Skriver data/exposure_baseline.json for alle spots i spots.json.

Metode, per spot, per grad 0-359 (26.09.2026, rettet mot ekte diffraksjonsfysikk
etter at den første, rent geometriske heuristikken ga urealistisk høy
eksponering for brede vindu som Unstad/Ersfjordstranda):

1. Gå utover langs strålen (0,5 km steg) til maxd=150 km eller land, etter
   en streng kysttoleranse (se COAST_FUZZ under) - ingen land innen maxd gir
   rå eksponering 1,0.
2. Land funnet: dette er en blokkert retning. Finn HINDRINGENS BREDDE PÅ
   TVERS (ikke tykkelsen langs strålen) ved å se hvor mange NABOGRADER som
   treffer land på omtrent samme avstand - det er den samme fysiske
   landmassen sett fra spoten. Bredde i km = antall grader × (pi/180) ×
   avstand (buelengde ved den avstanden).
3. Skyggelengde (kunnskapsformel for diffraksjon bak en knivsegg-hindring,
   Fresnel-tilnærming): L = W² / lambda, W = bredde på tvers i km,
   lambda = 0,225 km (svell på ca 12 s bølgeperiode på dypt vann,
   g*T²/(2*pi) = 9,81*12²/(2*pi) ~ 225 m). Er avstanden fra hindringen til
   spoten MINDRE enn L: spoten står i dyp skygge, rå eksponering 0,0. Er den
   STØRRE: rå eksponering vokser gradvis mot 1,0 jo lenger utenfor skyggen
   spoten ligger: `1 - L/avstand`.

Dette er en kjent, men grov, tilnærming (ekte diffraksjon avhenger også av
bølgeretning og -spektrum, ikke bare bredde og avstand) - god nok til et
utgangspunkt, ikke en presis modell. Glattes til slutt med en normalfordeling
(sigma ca 10 grader) over alle 360 gradene, som tar seg av selve bøyingen
rundt kantene til hindringene (bredde/skyggelengde-formelen over gir den rå,
ikke-bøyde eksponeringen per grad)."""
import sys
import json
import math
from pathlib import Path

from mpl_toolkits.basemap import Basemap
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.prepared import prep

from exposure import spot_checksum

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
OUT = ROOT / "data" / "exposure_baseline.json"

MAXD = 150        # km, regnes som åpent hav
STEP = 0.5        # km, oppløsning langs strålen (utenfor kystsonen)
WAVELENGTH = 0.225  # km - svell ca 12 s bølgeperiode på dypt vann (g*T^2/2pi)
WIDTH_TOL = 2.0   # km - hvor nær hverandre treffavstander må være for å regnes som samme hindring


def build_land(lat, lon):
    m = Basemap(projection="cyl", llcrnrlat=lat - 1.5, urcrnrlat=lat + 1.8,
                llcrnrlon=lon - 4.5, urcrnrlon=lon + 4.5, resolution="f")
    return prep(unary_union([Polygon(list(zip(*xy))).buffer(0)
                             for xy, t in zip(m.coastpolygons, m.coastpolygontypes) if t == 1 and len(xy[0]) > 2]))


def pt(lat, lon, bearing, d):
    return (lat + d * math.cos(math.radians(bearing)) / 110.57,
            lon + d * math.sin(math.radians(bearing)) / (111.32 * math.cos(math.radians(lat))))


# 26.09.2026, punkt 3: strengere kysttoleranse. Spoten selv ligger på/nær
# kystlinja (samme presisjonsproblem som check_spot.py sin free_distance()
# løser med sin egen 2 km-toleranse), men her kreves sammenhengende vann
# innen bare 300 m - når linja IKKE når vann innen det, regnes retningen
# som reelt blokkert fra start (avstand 0,0 km), ikke bare hoppet over.
COAST_FUZZ = 0.3   # km
COAST_STEP = 0.05  # km - finere oppløsning enn STEP, bare i kystsonen


def first_land_distance(land, lat, lon, bearing):
    """Avstand (km) til første landtreff langs strålen, etter kysttoleransen.
    0,0 hvis linja ikke når sammenhengende vann innen COAST_FUZZ (blokkert
    fra start). None hvis åpent hav helt til MAXD (ingen hindring i det
    hele tatt)."""
    def is_land(d):
        la, lo = pt(lat, lon, bearing, d)
        return land.contains(Point(lo, la))

    d0 = 0.0
    while d0 < COAST_FUZZ and is_land(d0):
        d0 += COAST_STEP
    if is_land(d0):
        return 0.0

    d = d0
    while d < MAXD:
        if is_land(d):
            return d
        d += STEP
    return None


def obstacle_width_deg(hits, bearing):
    """Hindringens bredde PÅ TVERS sett fra spoten, i grader: hvor mange
    naboretninger som treffer land på omtrent samme avstand (WIDTH_TOL) -
    det er trolig den samme fysiske landmassen. Brukes til å regne om til
    km (buelengde) i shadow_exposure()."""
    d_hit = hits[bearing]
    width = 1
    b = bearing
    while width < 360:
        b2 = (b + 1) % 360
        d2 = hits[b2]
        if d2 is None or d2 == 0.0 or abs(d2 - d_hit) > WIDTH_TOL:
            break
        b, width = b2, width + 1
    b = bearing
    while width < 360:
        b2 = (b - 1) % 360
        d2 = hits[b2]
        if d2 is None or d2 == 0.0 or abs(d2 - d_hit) > WIDTH_TOL:
            break
        b, width = b2, width + 1
    return width


def shadow_exposure(hits, bearing):
    """Rå eksponering for én grad, ut fra skyggelengden bak hindringen den
    treffer (se modul-docstringen for formelen). Returnerer
    (rå_eksponering, avstand_km, bredde_km, skyggelengde_L_km) - de tre
    siste er None når retningen er helt åpen eller blokkert fra start."""
    d_hit = hits[bearing]
    if d_hit is None:
        return 1.0, None, None, None
    if d_hit == 0.0:
        return 0.0, 0.0, None, None
    width_deg = obstacle_width_deg(hits, bearing)
    width_km = math.radians(width_deg) * d_hit
    shadow_l = (width_km ** 2) / WAVELENGTH
    if d_hit < shadow_l:
        raw = 0.0
    else:
        raw = max(0.0, min(1.0, 1 - shadow_l / d_hit))
    return raw, d_hit, width_km, shadow_l


def gaussian_smooth(values, sigma=10.0):
    n = len(values)
    radius = int(sigma * 3)
    weights = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-radius, radius + 1)]
    wsum = sum(weights)
    out = []
    for i in range(n):
        acc = 0.0
        for k, w in zip(range(-radius, radius + 1), weights):
            acc += values[(i + k) % n] * w
        out.append(acc / wsum)
    return out


def build_spot_baseline(spot):
    lat, lon = spot["spot"]["lat"], spot["spot"]["lon"]
    land = build_land(lat, lon)
    hits = [first_land_distance(land, lat, lon, b) for b in range(360)]
    shadow = [shadow_exposure(hits, b) for b in range(360)]
    raw = [s[0] for s in shadow]
    smoothed = gaussian_smooth(raw)
    return {
        "checksum": spot_checksum(spot),
        "raw": [round(v, 3) for v in raw],
        "smoothed": [round(v, 3) for v in smoothed],
        # 06.10.2026, Theodors rettelse (Farstadsanden 337 grader, Nordneset -
        # se STATUS.md): avstand til nærmeste hindring i km, per grad. None =
        # helt åpent (ingen hindring innen MAXD) eller blokkert fra start
        # (0,0 - "hindringen" er da stranda/neset selv, ikke en avgrenset
        # gjenstand å måle avstand til). shadow_exposure() regnet dette
        # allerede ut for selve eksponeringstallet - lagres nå i tillegg, til
        # rating.blocked_by_near_obstacle() (ikke brukt i eksponeringstallet
        # selv, bare til å avgjøre om bw_confirms kan overstyre en retning).
        "distance_km": [round(s[1], 2) if s[1] is not None else None for s in shadow],
        # 06.10.2026: hindringens BREDDE på tvers, i km (samme s[2] som
        # allerede regnes ut for selve skyggelengde-formelen) - Theodor
        # kalte Farstadsanden sin hindring (Nordneset) "en nær, BRED
        # hindring". En kort skyggelengde L=W²/λ kan gjøre rå eksponering 0
        # selv for en SMAL hindring tett innpå (sett ved Unstad 248-251
        # grader, se STATUS.md) - bredden skiller de to, avstanden alene
        # gjør det ikke.
        # 06.10.2026, fysikk-kontrollør sitt funn: "if s[1]/s[2] else None"
        # (over og her) brukte Python-sannhet på et flyttall - en EKTE
        # avstand/bredde på 0,0 (blokkert fra start, se kommentaren over) ble
        # da feilaktig til None, selv om 0,0 er en gyldig, meningsbærende
        # verdi (ikke "mangler data"). "is not None" skiller de to riktig.
        # Ufarlig i praksis i dag (shadow_exposure() returnerer alltid
        # width_km=None nettopp når distance_km=0,0), men ingen grunn til å
        # stole stilltiende på at den koblingen aldri endres.
        "width_km": [round(s[2], 2) if s[2] is not None else None for s in shadow],
    }


def main():
    config = json.loads(SPOTS.read_text(encoding="utf-8"))
    out = {}
    for spot in config["spots"]:
        if not spot.get("enabled"):
            continue
        print(spot["name"])
        out[spot["id"]] = build_spot_baseline(spot)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Skrev {OUT}")


if __name__ == "__main__":
    main()
