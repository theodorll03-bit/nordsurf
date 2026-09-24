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


# ---------- Høyde på spoten ----------

def refraction_factor(turn):
    """Din dreiningsregel. Liten dreining: modellen treffer.
    Stor dreining: svellet må bøye seg inn, modellen overdriver."""
    if turn is None:
        return 1.0
    if turn < 10:
        return 1.0
    if turn <= 25:
        return 1.0 - 0.4 * (turn - 10) / 15  # 1.0 ned til 0.6
    return 0.15


DEFAULT_TRANSFER = 0.7  # startverdi til loggene har lært den ekte faktoren


def spot_height(hour, spot=None):
    """Beste anslag på bølgehøyde på spoten, og hvilken kilde det kom fra.

    1. BarentsWatch, når den finnes (finmasket kystmodell).
    2. Bare svellet ute (Open-Meteo), uten vindsjø, ganget med spotens
       faktor, dreiningsregelen og hvor godt retningen treffer vinduet.
       Faktoren læres fra loggene dine.
    3. Reserve: total bølgehøyde fra met.no på spoten, med dreiningsregelen
       og retningen.

    Retningen teller med her, ikke bare på stjernene: en retning nær kanten
    av vinduet betyr mindre svellenergi når stranda, selv om den teknisk
    sett er innenfor.
    """
    if hour.get("bw_height") is not None:
        return hour["bw_height"], "barentswatch"
    transfer = (spot or {}).get("transfer", DEFAULT_TRANSFER)
    dir_factor = direction_score(hour.get("dir_offshore"), spot) if spot else 1.0
    if hour.get("swell_offshore") is not None:
        h = hour["swell_offshore"] * transfer * refraction_factor(hour.get("turn")) * dir_factor
        return h, "svell_ute"
    h = hour.get("height_spot_model")
    if h is None:
        return None, None
    return h * refraction_factor(hour.get("turn")) * dir_factor, "metno_korrigert"


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


def direction_score(d, spot):
    if d is None:
        return 0.5
    best = 0.0
    for start, end in window_sectors(spot):
        if in_sector(d, [start, end]):
            width = max((end - start) % 360, 1)
            center = (start + width / 2) % 360
            best = max(best, 1.0 - 0.2 * angle_diff(d, center) / (width / 2))
    if best:
        return best
    # Utenfor vinduet: observert 25.09.2026 at 3 grader utenfor holdt Grøtfjord
    # helt flatt. Ingen delvis kreditt nær kanten - utenfor er utenfor.
    return 0.1


def swell_stars(hour, spot):
    h, source = spot_height(hour, spot)
    score = height_score(h, spot) * period_score(hour.get("period"), spot)
    if source == "barentswatch":
        # BarentsWatch måler høyden direkte på spoten - retningens effekt på
        # energien er allerede med i det tallet. For de andre kildene er
        # retningen alt bakt inn i h via spot_height(), så her ville en ny
        # multiplikasjon telt den samme rabatten to ganger.
        score *= direction_score(hour.get("dir_offshore"), spot)
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
    dir_hit = direction_score(hour.get("dir_offshore"), spot)
    # Ærlighet: uten BarentsWatch og med dreining vet vi mindre. Maks 3 stjerner.
    uncertain = source != "barentswatch" and (hour.get("turn") or 0) >= 10
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
        # Hvor mye av svellet som treffer, basert på retning i vinduet.
        # Brukes til å justere selve høyden, ikke bare stjernene.
        "direction_hit": round(dir_hit, 3),
        # Trolig flatt: svellet må bøye seg kraftig inn, eller kommer utenfor vinduet
        "likely_flat": source != "barentswatch" and (
            (hour.get("turn") is not None and hour["turn"] > 25)
            or dir_hit <= 0.1
        ),
    }
