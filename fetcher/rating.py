"""Rating i Magicseaweed-stil.

Svellet gir 0 til 5 stjerner. Vinden trekker fra. Det som trekkes fra vises
som blasse stjerner: hvor bra det kunne vært med riktig vind.
"""


def angle_diff(a, b):
    """Minste vinkel mellom to retninger, 0 til 180."""
    d = abs((a - b) % 360)
    return 360 - d if d > 180 else d


def in_sector(direction, sector):
    """Er retningen innenfor sektoren [start, slutt]? Sektoren kan gå over 360."""
    start, end = sector
    direction %= 360
    if start <= end:
        return start <= direction <= end
    return direction >= start or direction <= end


def distance_to_sector(direction, sector):
    if in_sector(direction, sector):
        return 0
    return min(angle_diff(direction, sector[0]), angle_diff(direction, sector[1]))


def window_sectors(spot):
    """Svellvinduet kan være én sektor [a, b] eller flere [[a, b], [c, d]]."""
    w = spot["swell_window"]
    return w if isinstance(w[0], list) else [w]


def degrees_outside(d, spot):
    """0 hvis retningen er innenfor en av sektorene i vinduet. Ellers minste
    vinkelavstand til nærmeste kant. None hvis d er None."""
    if d is None:
        return None
    return min(distance_to_sector(d, s) for s in window_sectors(spot))


def degrees_inside(d, spot):
    """For sektoren d ligger innenfor: minste vinkelavstand til de to
    kantene. 0 hvis d er utenfor alle sektorer (eller None)."""
    if d is None:
        return 0
    for start, end in window_sectors(spot):
        if in_sector(d, [start, end]):
            return min(angle_diff(d, start), angle_diff(d, end))
    return 0


# ---------- Høyde på spoten ----------

def refraction_factor(turn):
    """Din dreiningsregel. Liten dreining: modellen treffer.
    Stor dreining: svellet må bøye seg inn, modellen overdriver.
    Brukes bare for reserven (metno_korrigert) - svell_ute bruker directness()."""
    if turn is None:
        return 1.0
    if turn < 10:
        return 1.0
    if turn <= 25:
        return 1.0 - 0.4 * (turn - 10) / 15  # 1.0 ned til 0.6
    return 0.15


DEFAULT_TRANSFER = 0.6  # andel av svellet ute som når stranda ved DIREKTE treff
EDGE_TAPER = 5  # grader innenfor kanten der høyden glir opp til 1.0
# (grader utenfor vinduet, andel av høyden ved direkte treff). 0.667 på kanten
# tilsvarer 0.4 når transfer er 0.6. Kalibrert mot kystteknikk (diffraksjon
# bak en odde: ca 70% langs skyggegrensen for uregelmessige bølger), resten
# er anslag. Læres ALDRI fra loggene - bare transfer gjør det.
SHADOW_CURVE = [(0, 0.667), (5, 0.333), (10, 0.167), (20, 0.05), (30, 0.0)]


def directness(d, spot):
    """0 til 1: hvor stor andel av svellet ved direkte treff som når spoten,
    basert på hvor retningen ligger i forhold til svellvinduet."""
    if d is None:
        return 0.7  # ukjent retning, nøytralt anslag
    if degrees_outside(d, spot) == 0:
        edge = SHADOW_CURVE[0][1]
        deg_in = degrees_inside(d, spot)
        if deg_in >= EDGE_TAPER:
            return 1.0
        return min(1.0, edge + (1.0 - edge) * deg_in / EDGE_TAPER)
    deg_out = degrees_outside(d, spot)
    if deg_out >= SHADOW_CURVE[-1][0]:
        return SHADOW_CURVE[-1][1]
    for (x0, y0), (x1, y1) in zip(SHADOW_CURVE, SHADOW_CURVE[1:]):
        if x0 <= deg_out <= x1:
            return y0 + (y1 - y0) * (deg_out - x0) / (x1 - x0)
    return SHADOW_CURVE[-1][1]


def spot_height(hour, spot=None):
    """Beste anslag på bølgehøyde på spoten, og hvilken kilde det kom fra.

    1. BarentsWatch, når den finnes (finmasket kystmodell som allerede tar
       hensyn til skjerming bak odder og øyer).
    2. Bare svellet ute (Open-Meteo), uten vindsjø, ganget med spotens
       faktor og directness() - hvor direkte svellet treffer vinduet.
       Faktoren læres fra loggene dine. Bruker IKKE dreiningsregelen her,
       ellers straffes skrått svell to ganger.
    3. Reserve: total bølgehøyde fra met.no på spoten, med dreiningsregelen.
    """
    if hour.get("bw_height") is not None:
        return hour["bw_height"], "barentswatch"
    transfer = (spot or {}).get("transfer", DEFAULT_TRANSFER)
    if hour.get("swell_offshore") is not None:
        h = hour["swell_offshore"] * transfer * directness(hour.get("dir_offshore"), spot)
        return h, "svell_ute"
    h = hour.get("height_spot_model")
    if h is None:
        return None, None
    return h * refraction_factor(hour.get("turn")), "metno_korrigert"


# ---------- Svellstjerner ----------
# Strengt med vilje: 5 stjerner skal være sjeldent. Hver faktor er 1.0 bare
# når forholdene er virkelig gode, og stjernene rundes NED.

def height_score(h, spot):
    lo, hi = spot["ideal_height"]
    mx = spot["max_height"]
    if h is None or h <= 0.4:
        return 0.0
    if h < lo:
        return 0.15 + 0.6 * (h - 0.4) / (lo - 0.4)  # under ideell: maks 0.75
    mid = (lo + hi) / 2
    if h <= hi:
        return 1.0 - 0.2 * abs(h - mid) / (hi - mid)  # 1.0 i midten, 0.8 i kantene
    if h <= mx:
        return 0.8 - 0.4 * (h - hi) / (mx - hi)
    return 0.25


def period_score(p, spot):
    if p is None:
        return 0.5
    if p < spot["min_period"] - 2:
        return 0.3
    if p < spot["min_period"]:
        return 0.5
    if p < 10:
        return 0.65
    if p < 12:
        return 0.8
    if p < 14:
        return 0.92
    return 1.0


def direction_score(d, spot, source=None):
    """Retningsstraff for stjernene. Når høyden allerede kommer fra en kilde
    som tar hensyn til retningen (svell_ute sin directness(), eller
    BarentsWatch sin egen kystmodell), skal denne ikke straffe en gang til -
    da ville samme rabatt telt dobbelt. Bare reserven (metno_korrigert, og
    ukjent kilde) bruker den egentlige retningsstraffen."""
    if source in ("svell_ute", "barentswatch"):
        return 1.0
    if d is None:
        return 0.5
    off = degrees_outside(d, spot)
    if off == 0:
        return 1.0
    return 0.5 if off <= 20 else 0.1


def swell_stars(hour, spot):
    h, source = spot_height(hour, spot)
    score = (
        height_score(h, spot)
        * period_score(hour.get("period"), spot)
        * direction_score(hour.get("dir_offshore"), spot, source)
    )
    return int(5 * score + 1e-9)  # rund ned


# ---------- Vind ----------

def wind_type(wind_dir, spot):
    if wind_dir is None:
        return None
    off_sector = spot["offshore_wind"]
    if in_sector(wind_dir, off_sector):
        return "offshore"
    center = (off_sector[0] + ((off_sector[1] - off_sector[0]) % 360) / 2) % 360
    onshore_center = (center + 180) % 360
    if angle_diff(wind_dir, onshore_center) <= 45:
        return "onshore"
    return "sideonshore"


def wind_penalty(speed, wind_dir, spot):
    if speed is None:
        return 1  # ukjent vind: ikke gi full pott
    if speed < 1.5:
        return 0  # blankt
    kind = wind_type(wind_dir, spot)
    if kind == "offshore":
        if speed > 12:
            return 2
        return 1 if speed > 9 else 0
    if kind == "sideonshore":
        if speed < 3:
            return 1
        return 2 if speed < 6 else 3
    # onshore
    if speed < 3:
        return 1
    if speed < 5:
        return 2
    if speed < 8:
        return 3
    return 5


def tide_penalty(tide, spot):
    """Spoten kan si hvilke tidevann den liker: 'tide': ['lav', 'middels', 'høy'].
    Utenfor det koster 'tide_penalty' stjerner (standard 1)."""
    ok = spot.get("tide")
    if not ok or not tide:
        return 0
    return 0 if tide["state"] in ok else spot.get("tide_penalty", 1)


def rate(hour, spot):
    """Stjerner for én time. Blasse stjerner = det vind og tidevann tar."""
    potential = swell_stars(hour, spot)
    h, source = spot_height(hour, spot)
    dir_hit = directness(hour.get("dir_offshore"), spot)
    deg_out = degrees_outside(hour.get("dir_offshore"), spot)
    # Ærlighet: uten BarentsWatch, med dreining eller utenfor vinduet vet vi
    # mindre. Maks 3 stjerner. Svell godt innenfor vinduet, nær kanten, gjør
    # IKKE varselet usikkert i seg selv.
    uncertain = source != "barentswatch" and (
        (hour.get("turn") or 0) >= 10 or (deg_out or 0) > 0
    )
    if uncertain:
        potential = min(potential, 3)
    lost_wind = min(potential, wind_penalty(hour.get("wind_speed"), hour.get("wind_dir"), spot))
    lost_tide = min(potential - lost_wind, tide_penalty(hour.get("tide"), spot))
    solid = potential - lost_wind - lost_tide
    return {
        "stars": solid,
        "faded": lost_wind + lost_tide,
        "faded_wind": lost_wind,
        "faded_tide": lost_tide,
        "wind_type": wind_type(hour.get("wind_dir"), spot),
        "height": None if h is None else round(h, 2),
        "height_source": source,
        "transfer": spot.get("transfer", DEFAULT_TRANSFER),
        "uncertain": uncertain,
        # Hvor stor andel av svellet ved direkte treff som når spoten akkurat
        # nå. Brukes til å justere selve høyden (for svell_ute), og vises i
        # appen som "retningstreff".
        "directness": round(dir_hit, 3),
        # Trolig flatt: enten er beregnet høyde reelt lav, eller reserven
        # (metno_korrigert) har stor dreining/retning langt utenfor vinduet -
        # den kilden tar ikke selv hensyn til noen av delene.
        "likely_flat": (h is not None and h < 0.35) or (
            source == "metno_korrigert" and (
                (hour.get("turn") is not None and hour["turn"] > 25)
                or (deg_out is not None and deg_out > 20)
            )
        ),
    }
