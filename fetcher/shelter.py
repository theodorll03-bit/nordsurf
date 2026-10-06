"""Skjerming per spot (ROADMAP oppgave I, 06.10.2026) - hvor beskyttet
reservemodellens transfer skal starte på FØR noe er lært fra BarentsWatch
eller loggene (kan ta måneder for en lite besøkt spot). Grøtfjord ligger
langt inne i en bukt med smal åpning, Unstad rett ut mot havet -
reservemodellen brukte tidligere samme DEFAULT_TRANSFER for begge til
transfer var lært.

Manuelt verktøy, kjøres sjelden (ikke i hver fetch.py-kjøring), samme
tunge avhengighet som exposure_baseline.py/check_spot.py:
    pip install basemap basemap-data-hires shapely
Kjør: python fetcher/shelter.py
Skriver data/shelter.json for alle spots i spots.json.

Metode per spot (samme landdeteksjon - GSHHS, 300 m kysttoleranse - som
check_spot.py/exposure_baseline.py, gjenbrukt direkte via build_land()/
pt() derfra - ingen egen kystlinje-håndtering):

1. d_open: avstanden man må gå fra spoten - i retning facing, og facing
   ± 20 grader (korteste av de tre vinner) - før HELE halvsirkelen (180
   grader, sentrert på facing) har fri linje til åpent hav. "Fri linje"
   her betyr ingen land innen OPEN_HORIZON_KM: en LOKAL "ute av
   bukta/odden"-horisont, IKKE samme 150 km som exposure_baseline.py sin
   rå eksponering bruker for selve bølgegenereringen ute i havet - den
   er irrelevant for dette, bukten/åpningen løser seg innen få titalls
   km for alle spotene vi har.
2. Åpning ved spoten (opening_frac): andel av samme halvsirkel som ER fri
   linje når man måler fra SPOTEN selv, ikke fra d_open-punktet (0-1).
3. B: bredden på selve åpningen, vinkelrett på facing. Målt som den
   sammenhengende vifta av frie grader rundt facing - ved spoten - omregnet
   til km ved avstanden d_open (bredde = vinkel i radianer × d_open; vifta
   blir bredere med avstanden, som en kjegle ut fra spoten).
4. f = B / (B + 2 × d_open × tan(20 grader)) - andelen bølgeenergi som
   diffrakterer gjennom åpningen og videre inn til spoten (Theodors formel
   - en fast spredningsvinkel i stedet for exposure_baseline.py sin
   Fresnel-skyggelengde, som gjelder et annet spørsmål: skygge bak EN
   hindring, ikke gjennom EN åpning). height_factor_raw = sqrt(f).
5. Normalisering: height_factor = height_factor_raw delt på Unstad sin
   egen height_factor_raw. Unstad er den mest åpne av de åtte (ventet,
   se STATUS.md for tabellen) - uten normalisering ville selv en
   fullstendig åpen spot (halvsirkelen 100 % fri helt fra spoten) fått
   height_factor_raw ≈ sqrt(pi / (pi + 2*tan(20°))) ≈ 0,90, ikke 1,0
   (B og d_open skalerer likt når vifta er konstant bred, så f har et
   tak som ikke avhenger av avstanden alene - normaliseringen flytter
   DETTE taket til 1,0, Theodors egen instruks).

Periode-vektingen (skjermingsfaktor = 1-(1-height_factor)×p(T), kort
periode straffes mer enn lang) er IKKE del av dette skriptet - det er en
EGEN, time-for-time-beregning i rating.py (bruker hver times ekte
periode) - bare inputet (denne normaliserte height_factor, statisk per
spot) lagres her. Se rating.shelter_transfer_factor()/transfer_prior()."""
import json
import math
from pathlib import Path

from shapely.geometry import Point

from exposure_baseline import build_land, pt, COAST_FUZZ, COAST_STEP
from exposure import spot_checksum

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
OUT = ROOT / "data" / "shelter.json"

OPEN_HORIZON_KM = 25.0     # km - lokal "ute av bukta"-horisont, se moduldocstring punkt 1
RADIAL_STEP = 0.5          # km - steg utover langs facing-strålene og langs hver bæring
MAX_SEARCH_KM = 80.0       # km - øvre grense for d_open-søket (Lenangsøyra venter ~40 km, se ROADMAP)
ANGLE_STEP_SEARCH = 5      # grader - halvsirkel-sveipets oppløsning UNDER d_open-søket (kostnad)
DIFFRACTION_HALF_ANGLE = 20  # grader - Theodors spredningsvinkel i f-formelen
REFERENCE_SPOT = "unstad"   # normaliseres mot denne, se moduldocstring punkt 5

# 06.10.2026, natt: metoden over er forankret i facing (Theodors egen instruks
# - "gå ut i retning facing"). For Russelv og Steinkrøssa viste en manuell
# sjekk at facing ligger 55-60 grader fra swell_window sitt senter (samme
# mønster, bare mye større, enn det Lenangsøyra hadde FØR dagens facing-fix -
# se STATUS.md) - åpningen min metode finner nær facing er da høyst
# sannsynlig IKKE den samme åpningen swell_window (en egen, uavhengig
# kystlinjesjekk) peker på. Flagges her i stedet for å gjette - fetch.py
# bruker IKKE shelter_factor for en spot der dette er over terskelen (se
# resolve_shelter()). Alle de andre seks spotene er under 10 grader.
FACING_WINDOW_DIVERGENCE_MAX = 30  # grader


def _ang_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _window_center(window):
    """Midtpunktet av svellvinduet - av det BREDESTE segmentet for en spot
    med flere disjunkte vindu (Russelv sin [[5,15],[349,356]]-form)."""
    if isinstance(window[0], list):
        lo, hi = max(window, key=lambda p: (p[1] - p[0]) % 360)
    else:
        lo, hi = window
    span = (hi - lo) % 360
    return (lo + span / 2) % 360


def facing_window_divergence_deg(spot):
    return round(_ang_diff(spot["facing"], _window_center(spot["swell_window"])), 1)


def _is_land(land, lat, lon, bearing, d):
    la, lo = pt(lat, lon, bearing, d)
    return land.contains(Point(lo, la))


def open_within(land, lat, lon, bearing, horizon=OPEN_HORIZON_KM, step=RADIAL_STEP):
    """True hvis det finnes sammenhengende vann innen kysttoleransen (samme
    300 m/50 m-regel som exposure_baseline.first_land_distance()) OG ingen
    land fra der til horizon km langs strålen. Egen, billigere variant av
    first_land_distance() (som alltid søker til hele MAXD=150 km - unødig
    dyrt når vi bare spør om spoten har sluppet unna den nære
    bukt-/odde-geometrien)."""
    d0 = 0.0
    while d0 < COAST_FUZZ and _is_land(land, lat, lon, bearing, d0):
        d0 += COAST_STEP
    if _is_land(land, lat, lon, bearing, d0):
        return False  # land sammenhengende gjennom hele kysttoleransen
    d = d0
    while d < horizon:
        if _is_land(land, lat, lon, bearing, d):
            return False
        d += step
    return True


def half_circle_open(land, lat, lon, facing, horizon=OPEN_HORIZON_KM, step=RADIAL_STEP,
                      angle_step=ANGLE_STEP_SEARCH):
    """True hvis HELE halvsirkelen (180 grader, sentrert på facing) er fri
    linje fra (lat, lon) - grov vinkeloppløsning (angle_step), brukt bare
    under d_open-søket under for å holde kostnaden nede. Avslutter på
    første blokkerte bæring (vanligste utfall mens man fortsatt er inne i
    bukta)."""
    b = -90
    while b <= 90:
        if not open_within(land, lat, lon, (facing + b) % 360, horizon, step):
            return False
        b += angle_step
    return True


def find_d_open(land, lat, lon, facing):
    """Korteste avstand - over de tre strålene facing, facing-20, facing+20
    (Theodors instruks: "bruk kortest") - før halvsirkelen sentrert på
    facing er helt fri fra det punktet. Returnerer (d_open_km, hvilken_stråle)
    eller None hvis ingen av de tre åpner seg innen MAX_SEARCH_KM (ingen av
    de åtte ekte spotene ventes å treffe denne grensen, se STATUS.md)."""
    best = None
    for ray_name, ray in (("facing", facing), ("facing-20", facing - 20), ("facing+20", facing + 20)):
        d = RADIAL_STEP
        while d <= MAX_SEARCH_KM:
            plat, plon = pt(lat, lon, ray % 360, d)
            if half_circle_open(land, plat, plon, facing):
                if best is None or d < best[0]:
                    best = (d, ray_name)
                break
            d += RADIAL_STEP
    return best


def opening_frac_and_width_deg(land, lat, lon, facing):
    """Målt VED SPOTEN (ikke ved d_open-punktet): (a) opening_frac - andel
    av halvsirkelen (181 grader, -90 til +90 om facing) som er fri linje;
    (b) width_deg - den sammenhengende vifta av frie grader RUNDT facing
    (robust mot at facing selv havner på feil side av en kystlinje-piksel
    helt tett på spoten: starter på nærmeste frie grad til facing i stedet
    for å kreve at facing selv er fri)."""
    half = [(facing + b) % 360 for b in range(-90, 91)]
    open_flags = [open_within(land, lat, lon, b) for b in half]
    opening_frac = sum(open_flags) / len(open_flags)
    idx0 = None
    for delta in range(91):
        for cand in (90 + delta, 90 - delta):
            if 0 <= cand < len(open_flags) and open_flags[cand]:
                idx0 = cand
                break
        if idx0 is not None:
            break
    if idx0 is None:
        return opening_frac, 0.0
    width = 1
    i = idx0
    while i + 1 < len(open_flags) and open_flags[i + 1]:
        i += 1
        width += 1
    i = idx0
    while i - 1 >= 0 and open_flags[i - 1]:
        i -= 1
        width += 1
    return opening_frac, float(width)


def build_spot_shelter(spot):
    lat, lon = spot["spot"]["lat"], spot["spot"]["lon"]
    facing = spot["facing"]
    land = build_land(lat, lon)
    found = find_d_open(land, lat, lon, facing)
    opening_frac, width_deg = opening_frac_and_width_deg(land, lat, lon, facing)
    divergence = facing_window_divergence_deg(spot)
    reliable = divergence <= FACING_WINDOW_DIVERGENCE_MAX
    if found is None:
        return {
            "checksum": spot_checksum(spot),
            "d_open_km": None, "d_open_ray": None,
            "opening_frac": round(opening_frac, 3), "width_deg": width_deg,
            "b_km": None, "f": None, "height_factor_raw": None,
            "facing_window_divergence_deg": divergence, "reliable": False,
        }
    d_open, ray = found
    b_km = math.radians(width_deg) * d_open
    spread = 2 * d_open * math.tan(math.radians(DIFFRACTION_HALF_ANGLE))
    f = b_km / (b_km + spread) if (b_km + spread) > 0 else 0.0
    height_factor_raw = math.sqrt(f)
    return {
        "checksum": spot_checksum(spot),
        "d_open_km": round(d_open, 2), "d_open_ray": ray,
        "opening_frac": round(opening_frac, 3), "width_deg": width_deg,
        "b_km": round(b_km, 2), "f": round(f, 3), "height_factor_raw": round(height_factor_raw, 4),
        # 06.10.2026, natt: ROADMAP oppgave I ber om å forankre søket i
        # facing. Når facing og swell_window (en egen, uavhengig
        # kystlinjesjekk) peker mer enn FACING_WINDOW_DIVERGENCE_MAX grader
        # fra hverandre, er det et tegn på at de ble satt uavhengig av
        # hverandre (se Lenangsøyra-saken, STATUS.md) - height_factor over
        # er da beregnet på riktig METODE, men mot høyst sannsynlig FEIL
        # åpning. "reliable": false her gjør at fetch.py sin resolve_shelter()
        # IKKE bruker tallet i ratingen (se der) - verdien vises likevel her,
        # ingenting skjules.
        "facing_window_divergence_deg": divergence, "reliable": reliable,
    }


def main():
    config = json.loads(SPOTS.read_text(encoding="utf-8"))
    spots = [s for s in config["spots"] if s.get("enabled")]
    out = {}
    for spot in spots:
        print(spot["name"])
        out[spot["id"]] = build_spot_shelter(spot)

    ref = out.get(REFERENCE_SPOT, {}).get("height_factor_raw")
    for sid, entry in out.items():
        raw = entry["height_factor_raw"]
        if raw is None or not ref:
            entry["height_factor"] = None
            continue
        entry["height_factor"] = round(raw / ref, 3)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Skrev {OUT}")


if __name__ == "__main__":
    main()
