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
   rå eksponering bruker for selve bølgegenereringen ute i havet. d_open
   er grensa for hvor langt ut åpningen (punkt 3) letes etter - utenfor
   d_open ligger spoten per definisjon i åpent vann.
2. Åpning ved spoten (opening_frac, width_deg): andel av samme halvsirkel
   som ER fri linje når man måler fra SPOTEN selv (0-1), og den
   sammenhengende vifta av frie grader rundt facing. Bare til informasjon
   (tabellen i STATUS.md) - brukes IKKE i f lenger, se punkt 3.
3. Åpningen B og avstanden d til den: for hvert punkt langs strålen som
   ga d_open (RADIAL_STEP km mellom punktene, fra spoten og ut til
   d_open) måles den frie TVERRBREDDEN W(d) = fri avstand til land
   vinkelrett på facing, til venstre (facing-90) pluss til høyre
   (facing+90), hver side begrenset til WIDTH_CAP_KM. Punkter der strålen
   selv krysser land (skjær, holme) hoppes over. For hvert punkt regnes
   f(d) = W(d) / (W(d) + 2 × d × tan(20 grader)) - Theodors formel, med
   W(d) som åpningens bredde og d som avstanden fra åpningen inn til
   spoten. Spotens f er det MINSTE f(d) langs strålen: det smaleste
   snittet, vektet med hvor langt inn fra det snittet spoten ligger, er
   det som begrenser hvor mye energi som når fram. B = W ved det
   punktet, d_b = avstanden dit. height_factor_raw = sqrt(f).

   07.10.2026 (skyøkt, etter fysikk-kontrollør 06.10 natt): den første
   versjonen satte B = (vifta i radianer ved spoten) × d_open og spread =
   2 × d_open × tan(20°), så d_open forkortet seg bort og f var bare en
   funksjon av vinkelen ved spoten. Nå er B en EKTE, uavhengig målt
   bredde (meter land-til-land på tvers av strålen) og d en ekte avstand
   - ingen felles faktor. Avviket fra ROADMAP sin ordlyd ("B ved punktet
   i a, vinkelrett på facing", altså ved d_open selv): ved d_open-punktet
   er bæringene facing±90 PER DEFINISJON frie i minst OPEN_HORIZON_KM, så
   B målt der ville alltid vært minst 2 × OPEN_HORIZON_KM = 50 km - et
   tall som styres av horisontkonstanten, ikke av bukta. Det smaleste
   snittet på veien ut er derimot en ekte egenskap ved bukta. Se
   STATUS.md for tabellen med begge variantene.
4. Normalisering: height_factor = height_factor_raw delt på Unstad sin
   egen height_factor_raw (REFERENCE_SPOT, Theodors instruks: "normalisert
   så en åpen spot (Unstad) får ca. 1,0"). Unstad ligger selv i en liten
   vik (ca. 1,5-2 km bred, se STATUS.md) og får derfor rå f under 1,0 -
   normaliseringen setter den vika som "åpen". En spot som er råere enn
   Unstad (f.eks. Tromvik, 07.10.2026) får height_factor over 1,0 og
   dermed INGEN skjermingseffekt i ratingen (rating.shelter_transfer_factor()
   gir 1,0 for alt som ikke er strengt mellom 0 og 1) - aldri en bonus.

Periode-vektingen (skjermingsfaktor = 1-(1-height_factor)×p(T), kort
periode straffes mer enn lang) er IKKE del av dette skriptet - det er en
EGEN, time-for-time-beregning i rating.py (bruker hver times ekte
periode) - bare inputet (denne normaliserte height_factor, statisk per
spot) lagres her. Se rating.shelter_transfer_factor()/transfer_prior().

Skjermingen påvirker BARE høyden ved stranda (transfer_prior i
reservemodellen) - aldri energigrensene (Theodors avgjørelse 07.10.2026:
energien måles ute, før skjermingen). Konstantene under
(DIFFRACTION_HALF_ANGLE, REFERENCE_SPOT) og p(T)-kurven i rating.py står
på CLAUDE.md sin "krever Theodors ja"-liste."""
import json
import math
from pathlib import Path

from exposure import spot_checksum

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
OUT = ROOT / "data" / "shelter.json"

OPEN_HORIZON_KM = 25.0     # km - lokal "ute av bukta"-horisont, se moduldocstring punkt 1
RADIAL_STEP = 0.5          # km - steg utover langs facing-strålene og langs hver bæring
MAX_SEARCH_KM = 80.0       # km - øvre grense for d_open-søket (Lenangsøyra venter ~40 km, se ROADMAP)
ANGLE_STEP_SEARCH = 5      # grader - halvsirkel-sveipets oppløsning UNDER d_open-søket (kostnad)
DIFFRACTION_HALF_ANGLE = 20  # grader - Theodors spredningsvinkel i f-formelen (krever Theodors ja)
REFERENCE_SPOT = "unstad"   # normaliseres mot denne, se moduldocstring punkt 4 (krever Theodors ja)
WIDTH_CAP_KM = MAX_SEARCH_KM  # km per side - tak på tverrbredde-sveipet (bare en kostnadsgrense:
                              # en side som er åpen til havs gir f ≈ 1 uansett om taket er 80 eller 150)
WIDTH_STEP = 0.25          # km - oppløsning i tverrbredde-sveipet (finere enn RADIAL_STEP, smale sund)

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


# Samme kysttoleranse og punktformel som exposure_baseline.py (COAST_FUZZ/
# COAST_STEP/pt) - gjentatt her i stedet for importert, fordi
# exposure_baseline.py laster basemap på modulnivå, og rating-testene skal
# kunne teste denne geometrien med SYNTETISK land (bare shapely) uten
# basemap (CI-feil 07.10.2026). test_rating.py 22.9 sjekker at verdiene er
# like når exposure_baseline faktisk kan importeres.
COAST_FUZZ = 0.3   # km
COAST_STEP = 0.05  # km


def pt(lat, lon, bearing, d):
    return (lat + d * math.cos(math.radians(bearing)) / 110.57,
            lon + d * math.sin(math.radians(bearing)) / (111.32 * math.cos(math.radians(lat))))


def _land_tools():
    """shapely lastes først her (ikke på modulnivå), så rating-testene kan
    importere modulen og teste geometrien med SYNTETISK land (en hvilken som
    helst `land` med .contains(Point)). build_land (basemap/GSHHS) lastes
    bare når build_spot_shelter() faktisk trenger ekte land."""
    from shapely.geometry import Point
    return None, pt, COAST_FUZZ, COAST_STEP, Point


def _is_land(land, lat, lon, bearing, d):
    _, pt, _, _, Point = _land_tools()
    la, lo = pt(lat, lon, bearing, d)
    return land.contains(Point(lo, la))


def _skip_coast(land, lat, lon, bearing):
    """Første avstand med vann innen kysttoleransen (COAST_FUZZ), eller
    None hvis land er sammenhengende gjennom hele toleransen."""
    _, _, COAST_FUZZ, COAST_STEP, _ = _land_tools()
    d0 = 0.0
    while d0 < COAST_FUZZ and _is_land(land, lat, lon, bearing, d0):
        d0 += COAST_STEP
    if _is_land(land, lat, lon, bearing, d0):
        return None
    return d0


def open_within(land, lat, lon, bearing, horizon=OPEN_HORIZON_KM, step=RADIAL_STEP):
    """True hvis det finnes sammenhengende vann innen kysttoleransen (samme
    300 m/50 m-regel som exposure_baseline.first_land_distance()) OG ingen
    land fra der til horizon km langs strålen. Egen, billigere variant av
    first_land_distance() (som alltid søker til hele MAXD=150 km - unødig
    dyrt når vi bare spør om spoten har sluppet unna den nære
    bukt-/odde-geometrien)."""
    d = _skip_coast(land, lat, lon, bearing)
    if d is None:
        return False  # land sammenhengende gjennom hele kysttoleransen
    while d < horizon:
        if _is_land(land, lat, lon, bearing, d):
            return False
        d += step
    return True


def free_width_km(land, lat, lon, bearing, cap=WIDTH_CAP_KM, step=WIDTH_STEP):
    """Fri avstand (km) til land langs bæringen fra (lat, lon), etter
    kysttoleransen, begrenset til cap. 0,0 hvis land er sammenhengende
    gjennom hele toleransen (punktet ligger inntil land i den retningen)."""
    d = _skip_coast(land, lat, lon, bearing)
    if d is None:
        return 0.0
    while d < cap:
        if _is_land(land, lat, lon, bearing, d):
            return d
        d += step
    return cap


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


RAYS = (("facing", 0), ("facing-20", -20), ("facing+20", 20))


def find_d_open(land, lat, lon, facing):
    """Korteste avstand - over de tre strålene facing, facing-20, facing+20
    (Theodors instruks: "bruk kortest") - før halvsirkelen sentrert på
    facing er helt fri fra det punktet. Returnerer (d_open_km, hvilken_stråle)
    eller None hvis ingen av de tre åpner seg innen MAX_SEARCH_KM (ingen av
    de åtte ekte spotene ventes å treffe denne grensen, se STATUS.md)."""
    _, pt, _, _, _ = _land_tools()
    best = None
    for ray_name, offset in RAYS:
        ray = (facing + offset) % 360
        d = RADIAL_STEP
        while d <= MAX_SEARCH_KM:
            plat, plon = pt(lat, lon, ray, d)
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
    for å kreve at facing selv er fri). Bare til informasjon siden
    07.10.2026 - se moduldocstring punkt 2."""
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


def energy_fraction(width_km, distance_km):
    """Theodors formel: f = B / (B + 2 × d × tan(20°)) - andelen av energien
    gjennom en åpning med bredde B (km) som fortsatt ligger innenfor samme
    bredde d km lenger inn, når bølgene sprer seg med halv vinkel
    DIFFRACTION_HALF_ANGLE. 1,0 for uendelig bred åpning eller d = 0."""
    spread = 2 * distance_km * math.tan(math.radians(DIFFRACTION_HALF_ANGLE))
    if width_km + spread <= 0:
        return 0.0
    return width_km / (width_km + spread)


def aperture_profile(land, lat, lon, facing, ray_bearing, d_open, step=RADIAL_STEP):
    """Tverrbredde W(d) og f(d) for hvert punkt langs strålen fra spoten ut
    til d_open (moduldocstring punkt 3). Hver rad: dict med d_km, left_km,
    right_km, width_km, f. Punkter der strålen selv ligger på land hoppes
    over (ingen rad)."""
    _, pt, _, _, Point = _land_tools()
    rows = []
    d = step
    while d <= d_open + 1e-9:
        plat, plon = pt(lat, lon, ray_bearing, d)
        if land.contains(Point(plon, plat)):
            d += step
            continue
        left = free_width_km(land, plat, plon, (facing - 90) % 360)
        right = free_width_km(land, plat, plon, (facing + 90) % 360)
        width = left + right
        rows.append({"d_km": round(d, 2), "left_km": round(left, 2), "right_km": round(right, 2),
                     "width_km": round(width, 2), "f": round(energy_fraction(width, d), 4)})
        d += step
    return rows


def limiting_aperture(rows):
    """Raden med MINSTE f langs strålen - det smaleste snittet vektet med
    avstanden inn til spoten (moduldocstring punkt 3). None uten rader."""
    if not rows:
        return None
    return min(rows, key=lambda r: r["f"])


def build_spot_shelter(spot, land=None):
    """Hele geometrien for én spot. `land` kan gis inn (tester med syntetisk
    kystlinje) - ellers bygges GSHHS-landet rundt spoten."""
    lat, lon = spot["spot"]["lat"], spot["spot"]["lon"]
    facing = spot["facing"]
    if land is None:
        from exposure_baseline import build_land  # basemap/GSHHS, bare for ekte kjøringer
        land = build_land(lat, lon)
    found = find_d_open(land, lat, lon, facing)
    opening_frac, width_deg = opening_frac_and_width_deg(land, lat, lon, facing)
    divergence = facing_window_divergence_deg(spot)
    reliable = divergence <= FACING_WINDOW_DIVERGENCE_MAX
    base = {
        "checksum": spot_checksum(spot),
        "d_open_km": None, "d_open_ray": None,
        "opening_frac": round(opening_frac, 3), "width_deg": width_deg,
        "b_km": None, "d_b_km": None, "f": None, "height_factor_raw": None,
        "facing_window_divergence_deg": divergence, "reliable": False,
    }
    if found is None:
        return base
    d_open, ray_name = found
    ray_bearing = (facing + dict(RAYS)[ray_name]) % 360
    rows = aperture_profile(land, lat, lon, facing, ray_bearing, d_open)
    lim = limiting_aperture(rows)
    if lim is None:
        return {**base, "d_open_km": round(d_open, 2), "d_open_ray": ray_name}
    f = lim["f"]
    return {
        **base,
        "d_open_km": round(d_open, 2), "d_open_ray": ray_name,
        "b_km": lim["width_km"], "d_b_km": lim["d_km"],
        "f": round(f, 3), "height_factor_raw": round(math.sqrt(f), 4),
        # 06.10.2026, natt: ROADMAP oppgave I ber om å forankre søket i
        # facing. Når facing og swell_window (en egen, uavhengig
        # kystlinjesjekk) peker mer enn FACING_WINDOW_DIVERGENCE_MAX grader
        # fra hverandre, er det et tegn på at de ble satt uavhengig av
        # hverandre (se Lenangsøyra-saken, STATUS.md) - height_factor over
        # er da beregnet på riktig METODE, men mot høyst sannsynlig FEIL
        # åpning. "reliable": false her gjør at fetch.py sin resolve_shelter()
        # IKKE bruker tallet i ratingen (se der) - verdien vises likevel her,
        # ingenting skjules.
        "reliable": reliable,
    }


def normalize(out, reference=REFERENCE_SPOT):
    """height_factor = height_factor_raw / referansens height_factor_raw
    (moduldocstring punkt 4). None der rå verdi eller referanse mangler.
    Kan bli over 1,0 for en spot råere enn referansen - ratingen gir da
    ingen effekt (aldri bonus), se rating.shelter_transfer_factor()."""
    ref = (out.get(reference) or {}).get("height_factor_raw")
    for entry in out.values():
        raw = entry.get("height_factor_raw")
        entry["height_factor"] = round(raw / ref, 3) if (raw is not None and ref) else None
    return out


def main():
    config = json.loads(SPOTS.read_text(encoding="utf-8"))
    spots = [s for s in config["spots"] if s.get("enabled")]
    out = {}
    for spot in spots:
        print(spot["name"])
        out[spot["id"]] = build_spot_shelter(spot)
        e = out[spot["id"]]
        print(f"  d_open {e['d_open_km']} km ({e['d_open_ray']}), B {e['b_km']} km ved {e['d_b_km']} km, "
              f"f {e['f']}, rå {e['height_factor_raw']}, pålitelig {e['reliable']}")
    normalize(out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Skrev {OUT}")


if __name__ == "__main__":
    main()
