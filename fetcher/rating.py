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
    Dette er den VISTE høyden og høyden kalibreringen læres mot - IKKE den
    "effektive" høyden ranger bruker (se effective_height/period_factor
    lenger ned), som bare skal påvirke rangeringen, ikke tallet du ser.

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

PERIOD_FACTOR_POINTS = [(8, 0.9), (10, 1.0), (13, 1.15), (16, 1.3)]


def period_factor(p):
    """Langt svell bygger seg høyere opp når det treffer grunnen enn kort
    svell med samme signifikante høyde ute. Brukes BARE til å justere
    height_score (rangeringen) - aldri til selve høyde-tallet du ser eller
    til kalibreringen mot BarentsWatch/loggene, som begge skal måle den
    ekte, fysiske høyden uforstyrret. Lineær interpolasjon mellom punktene,
    flatt ut utenfor endene."""
    if p is None:
        return 1.0
    pts = PERIOD_FACTOR_POINTS
    if p <= pts[0][0]:
        return pts[0][1]
    if p >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= p <= x1:
            return y0 + (y1 - y0) * (p - x0) / (x1 - x0)
    return pts[-1][1]


def effective_height(h, period):
    """Høyden brukt bare i height_score - se period_factor()."""
    if h is None:
        return None
    return h * period_factor(period)


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
    """Mildere enn før, og med vilje: nå som period_factor() (over) også
    belønner lang periode via height_score, skal ikke denne straffe det
    samme to ganger. Den skal bare straffe KORT periode (dårlig energi,
    lite driv), ikke lenger gi ekstra uttelling for lang periode."""
    if p is None:
        return 0.5
    if p < spot["min_period"] - 2:
        return 0.4
    if p < spot["min_period"]:
        return 0.6
    if p < 10:
        return 0.85
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
    period = hour.get("period")
    eff_h = effective_height(h, period)
    score = (
        height_score(eff_h, spot)
        * period_score(period, spot)
        * direction_score(hour.get("dir_offshore"), spot, source)
    )
    return int(5 * score + 1e-9)  # rund ned


# ---------- Vind ----------

def wind_type(wind_dir, spot):
    """Firedelt etter vinkelen mellom vindretningen og MIDTEN av spotens
    offshore_wind-sektor (0 = rett fra land): offshore 0-45, side 45-100,
    side-onshore 100-135, onshore 135-180."""
    if wind_dir is None:
        return None
    off_sector = spot["offshore_wind"]
    center = (off_sector[0] + ((off_sector[1] - off_sector[0]) % 360) / 2) % 360
    a = angle_diff(wind_dir, center)
    if a <= 45:
        return "offshore"
    if a <= 100:
        return "side"
    if a <= 135:
        return "sideonshore"
    return "onshore"


def effective_wind(speed, gust):
    """Når kastene er kraftigere enn middelvinden kjennes det verre enn
    middelvinden alene skulle tilsi. Uten kastdata: bare middelvind."""
    if speed is None:
        return None
    if gust is not None and gust > speed:
        return speed + 0.3 * (gust - speed)
    return speed


WIND_PENALTY_TABLE = (
    # (øvre grense effektiv vind eksklusiv, {vindtype: straff-funksjon(eff)})
    (3, {"offshore": lambda e: 0, "side": lambda e: 0, "sideonshore": lambda e: 0, "onshore": lambda e: 0}),
    (5, {"offshore": lambda e: 0, "side": lambda e: 0, "sideonshore": lambda e: 1, "onshore": lambda e: 1}),
    (8, {"offshore": lambda e: 0, "side": lambda e: 1, "sideonshore": lambda e: 1, "onshore": lambda e: 2}),
    (11, {"offshore": lambda e: 1 if e > 10 else 0, "side": lambda e: 2, "sideonshore": lambda e: 2, "onshore": lambda e: 3}),
)


def wind_penalty(speed, wind_dir, spot, gust=None):
    if speed is None:
        return 1  # ukjent vind: ikke gi full pott
    eff = effective_wind(speed, gust)
    kind = wind_type(wind_dir, spot) or "onshore"  # ukjent retning: anta verste fall
    for limit, table in WIND_PENALTY_TABLE:
        if eff <= limit:
            return table[kind](eff)
    # over 11 m/s effektiv
    if kind == "offshore":
        return 2 if eff > 14 else 1
    if kind == "side":
        return 3
    if kind == "sideonshore":
        return 3
    return 4


def wind_label(speed, wind_type_):
    """Tekst for vinden på detaljsiden: 'blankt'/'nesten blankt' under
    henholdsvis 1,5 og 3 m/s, ellers vindtypen (side/offshore/...)."""
    if speed is None:
        return None
    if speed < 1.5:
        return "blankt"
    if speed < 3:
        return "nesten blankt"
    return wind_type_


WIND_TYPE_WORD = {"offshore": "offshore", "side": "sidevind", "sideonshore": "side-onshore", "onshore": "onshore"}


def tide_penalty(tide, spot):
    """Spoten kan si hvilke tidevann den liker: 'tide': ['lav', 'middels', 'høy'].
    Utenfor det koster 'tide_penalty' stjerner (standard 1)."""
    ok = spot.get("tide")
    if not ok or not tide:
        return 0
    return 0 if tide["state"] in ok else spot.get("tide_penalty", 1)


# ---------- Forklaring (breakdown) ----------

def _height_word(score):
    if score <= 0:
        return "flatt"
    if score < 0.4:
        return "svak"
    if score < 0.7:
        return "middels"
    if score < 0.9:
        return "god"
    return "veldig god"


def _period_word(score):
    if score >= 1.0:
        return "full uttelling"
    if score >= 0.85:
        return "god uttelling"
    if score >= 0.6:
        return "redusert"
    return "sterkt redusert"


def _direction_word(dir_hit):
    if dir_hit is None:
        return "ukjent"
    if dir_hit >= 0.9:
        return "treffer vinduet"
    if dir_hit >= 0.5:
        return "i utkanten av vinduet"
    if dir_hit <= 0.001:
        return "treffer ikke vinduet"
    return "svakt inn i skyggen"


def _fmt_m(v):
    return f"{v:.1f}".replace(".", ",") + " m"


def _fmt_penalty(n):
    return "ingen effekt" if n == 0 else f"−{n}"


def build_breakdown(hour, spot, h, source, eff_h, period, hs, ps, dir_hit,
                     wind_speed, wind_dir, gust, wt, wp, tide, tide_pen,
                     potential, solid, lost_wind, lost_tide, uncertain, capped_from):
    items = []
    if h is None:
        items.append("Høyde: ingen data")
    else:
        pf = period_factor(period)
        felt = f", føles som ca. {_fmt_m(eff_h)}" + (f" på {period:.0f} s" if period is not None else "") if (pf > 1.05 or pf < 0.95) else ""
        items.append(f"Høyde {_fmt_m(h)}{felt}: {_height_word(hs)}")
    if period is None:
        items.append("Periode: ukjent")
    else:
        items.append(f"Periode {period:.0f} s: {_period_word(ps)}")
    items.append(f"Retning: {_direction_word(dir_hit)}")
    if wind_speed is None:
        items.append("Vind: ukjent")
    else:
        label = wind_label(wind_speed, WIND_TYPE_WORD.get(wt, wt or ""))
        gusttxt = f" med kast {gust:.0f}" if gust is not None and gust > wind_speed else ""
        items.append(f"Vind {wind_speed:.0f} m/s {label}{gusttxt}: {_fmt_penalty(wp)}")
    if not spot.get("tide"):
        items.append("Tidevann: spoten tåler alt")
    elif not tide:
        items.append("Tidevann: ukjent")
    else:
        items.append(f"Tidevann ({tide.get('state','?')}): {_fmt_penalty(tide_pen)}")
    if capped_from is not None and capped_from > potential:
        items.append(f"Usikkert varsel: kappet fra {capped_from} til maks 3 stjerner (ingen BarentsWatch, og retning utenfor vinduet eller stor dreining)")
    without_wind = min(potential, solid + lost_wind)
    total = f"Totalt: {solid} av 5 stjerner"
    if lost_wind > 0:
        total += f" ({without_wind} uten vind)"
    items.append(total)
    return items


def rate(hour, spot):
    """Stjerner for én time. Blasse stjerner = det vind og tidevann tar."""
    h, source = spot_height(hour, spot)
    period = hour.get("period")
    eff_h = effective_height(h, period)
    hs = height_score(eff_h, spot)
    ps = period_score(period, spot)
    dir_hit = directness(hour.get("dir_offshore"), spot)
    ds = direction_score(hour.get("dir_offshore"), spot, source)
    score = hs * ps * ds
    potential = int(5 * score + 1e-9)  # rund ned

    deg_out = degrees_outside(hour.get("dir_offshore"), spot)
    # Ærlighet: uten BarentsWatch, med dreining eller utenfor vinduet vet vi
    # mindre. Maks 3 stjerner. Svell godt innenfor vinduet, nær kanten, gjør
    # IKKE varselet usikkert i seg selv.
    uncertain = source != "barentswatch" and (
        (hour.get("turn") or 0) >= 10 or (deg_out or 0) > 0
    )
    capped_from = potential if (uncertain and potential > 3) else None
    if uncertain:
        potential = min(potential, 3)

    wind_speed, wind_dir, gust = hour.get("wind_speed"), hour.get("wind_dir"), hour.get("gust")
    wt = wind_type(wind_dir, spot)
    wp = wind_penalty(wind_speed, wind_dir, spot, gust)
    lost_wind = min(potential, wp)
    tide_pen = tide_penalty(hour.get("tide"), spot)
    lost_tide = min(potential - lost_wind, tide_pen)
    solid = potential - lost_wind - lost_tide

    breakdown = build_breakdown(
        hour, spot, h, source, eff_h, period, hs, ps, dir_hit,
        wind_speed, wind_dir, gust, wt, wp, hour.get("tide"), tide_pen,
        potential, solid, lost_wind, lost_tide, uncertain, capped_from,
    )

    return {
        "stars": solid,
        "faded": lost_wind + lost_tide,
        "faded_wind": lost_wind,
        "faded_tide": lost_tide,
        "wind_type": wt,
        "height": None if h is None else round(h, 2),
        "height_source": source,
        "transfer": spot.get("transfer", DEFAULT_TRANSFER),
        "uncertain": uncertain,
        "breakdown": breakdown,
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
