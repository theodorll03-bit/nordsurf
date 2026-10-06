"""Rating i Magicseaweed-stil.

Svellet gir 0 til 5 stjerner. Vinden trekker fra. Det som trekkes fra vises
som blasse stjerner: hvor bra det kunne vært med riktig vind.
"""
import math


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
    Brukes bare for reserven (metno_korrigert) - svell_ute bruker exposure()."""
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


def exposure_override_cap(d, spot):
    """Tak på eksponeringen for retning d, fra spots.json sin
    exposure_override (liste av {"from", "to", "max"}) - dekker kjente hull
    i kystlinjedataene (se f.eks. Grøtfjord sin _exposure_override-kommentar).
    None hvis ingen override dekker retningen. Fjernes ALDRI automatisk -
    bare foreslått i Logger-fanen når del B har lært noe (se ROADMAP)."""
    if d is None:
        return None
    for o in spot.get("exposure_override") or []:
        if in_sector(d, [o["from"], o["to"]]):
            return o["max"]
    return None


PERIOD_SHORT_MAX = 10  # sekunder ute - under dette er "kort" periodegruppe, se exposure_learn.py


def exposure(d, spot, period=None):
    """0 til 1: hvor mye av svellet utenfor som når spoten fra retning d -
    del C sin glattede, geometriske eksponering (exposure_baseline.py),
    slått sammen i fetch.py til spot["exposure_smoothed"] (360 verdier,
    indeks = gradtall) etter en gyldig sjekksum mot spots.json. Erstatter
    directness() (vindu + skyggekurve) for reservemodellen og for
    sources_disagree (27.09.2026, ROADMAP oppgave 2) - directness() brukes
    nå bare som reserve HVIS eksponeringsdata mangler eller er ugyldige for
    spoten (ingen exposure_baseline.json bygget ennå, eller sjekksummen ikke
    stemmer - fetch.py varsler da i kilderapporten). exposure_override sitt
    tak gjelder uansett hvilken av de to som brukes.

    27.09.2026, ROADMAP oppgave 4 (del B): diffraksjon avhenger av
    bølgelengden (samme λ som i exposure_baseline.py sin skyggelengde-formel),
    så en retning kan ha ulik lært eksponering for kort (under 10 s) og lang
    (10 s og over) periode ute. fetch.py setter, når nok er lært,
    spot["exposure_smoothed_kort"]/["_lang"] (blandet med geometrien, se
    exposure_learn.blend_curve()) - denne funksjonen velger riktig kurve
    etter `period` (svellets periode UTE, IKKE BarentsWatch sin periode ved
    kysten). Mangler periode, eller ingen lært kurve for gruppen: faller
    tilbake til spot["exposure_smoothed"] (ren geometri, eller del B sin
    'lang'-kurve hvis den også er satt der - se fetch.py)."""
    if d is None:
        value = directness(d, spot)
    else:
        pg = "kort" if period is not None and period < PERIOD_SHORT_MAX else "lang"
        curve = spot.get(f"exposure_smoothed_{pg}") or spot.get("exposure_smoothed")
        value = curve[int(round(d)) % 360] if curve else directness(d, spot)
    cap = exposure_override_cap(d, spot)
    return value if cap is None else min(value, cap)


# 07.10.2026, Theodors rettelse: periodeavhengig diffraksjonsdemping. Samme
# kurve som skjermingen i ROADMAP oppgave I (rating.shelter_period_weight()
# på grenen lokal/uferdig) - holdes som egne konstanter her til den grenen
# eventuelt merges, da skal de to deles. Står på CLAUDE.md sin "krever ja"-
# liste sammen med skjermingskonstantene.
DIFFRACTION_PERIOD_SHORT = 8     # s - full demping her og kortere
DIFFRACTION_PERIOD_LONG = 14     # s - DIFFRACTION_PERIOD_LONG_WEIGHT av dempingen her og lengre
DIFFRACTION_PERIOD_LONG_WEIGHT = 0.6


def diffraction_period_weight(period):
    """p(T): 1,0 ved 8 s eller kortere, lineært ned til 0,6 ved 14 s eller
    lengre. Ukjent periode: 1,0 (full demping - samme forsiktige antagelse
    som resten av ratingen)."""
    if period is None or period <= DIFFRACTION_PERIOD_SHORT:
        return 1.0
    if period >= DIFFRACTION_PERIOD_LONG:
        return DIFFRACTION_PERIOD_LONG_WEIGHT
    span = DIFFRACTION_PERIOD_LONG - DIFFRACTION_PERIOD_SHORT
    return 1.0 - (1.0 - DIFFRACTION_PERIOD_LONG_WEIGHT) * (period - DIFFRACTION_PERIOD_SHORT) / span


def diffraction_damping(dir_hit, period):
    """Ekstra Hb-demping for svell som bare når spoten ved diffraksjon (rå
    eksponering 0, se raw_exposure_zero()): 1 - (1 - dir_hit) × p(T). Ved
    8 s eller kortere er det nøyaktig dir_hit (som før 07.10.2026), ved 14 s
    eller lengre bare 60 % av tapet."""
    if dir_hit is None:
        return 1.0
    return 1.0 - (1.0 - dir_hit) * diffraction_period_weight(period)


def raw_exposure_zero(d, spot):
    """Sann når retning d bare kan nå spoten ved å bøye seg (diffraktere)
    rundt land - RÅ geometrisk eksponering (før glatting) er 0 i
    exposure_baseline.py sine tall, altså en reell, ublokkert siktlinje
    finnes IKKE i det hele tatt for denne retningen (se
    exposure_baseline.shadow_exposure()). Mangler rådata for spoten (ingen
    exposure_baseline.json bygget, eller sjekksummen ikke stemmer): faller
    tilbake til vindu-grensa (degrees_outside > 0) som samme konsept - i
    directness() sin egen modell er vindu-kanten der en fri siktlinje slutter.
    27.09.2026, tredje runde (ROADMAP oppgave 2, Theodors rettelse): brukt i
    rate() til å avgjøre NÅR Hb skal dempes en ekstra gang med eksponeringen,
    se der."""
    if d is None:
        return False
    raw = spot.get("exposure_raw")
    if raw is not None:
        return raw[int(round(d)) % 360] <= 0.0
    return degrees_outside(d, spot) > 0


NEAR_OBSTACLE_MAX_KM = 2.0  # se blocked_by_near_obstacle()
WIDE_OBSTACLE_MIN_KM = 2.0  # se blocked_by_near_obstacle()


def blocked_by_near_obstacle(d, spot):
    """06.10.2026, Theodors rettelse (Farstadsanden 337 grader, Nordneset -
    se STATUS.md): sann når retning d har en NÆR, BRED hindring foran seg -
    rå geometrisk eksponering 0 (spoten står i dyp skygge, se
    raw_exposure_zero()) OG hindringen (første landtreff langs strålen) er
    NÆRMERE enn NEAR_OBSTACLE_MAX_KM (2 km) OG BREDERE enn WIDE_OBSTACLE_MIN_KM
    (2 km) på tvers.

    Bredden er IKKE valgfri pynt: en skyggelengde L=W²/λ kan gjøre rå
    eksponering 0 selv for en SMAL hindring tett innpå (Unstad 248-251
    grader: 1,6 km unna, men bare 0,61 km BRED - en liten skjær/odde svellet
    bøyer seg rundt, ikke en vegg). Farstadsanden sin hindring (Nordneset,
    330-352 grader) er 1,0 km unna OG 5,5 km BRED - en helt annen situasjon.
    Avstand alene (Theodors opprinnelige, bokstavelige ordlyd) ville blokkert
    BEGGE - verifisert at det ville brutt Unstad 28.09.2026 sin faste
    observasjon (dir_offshore 248-250 grader der). Lagt til bredde-kravet
    for akkurat denne grunnen, samme 2 km-terskel som avstanden (symmetrisk,
    ikke en ny, ubegrunnet konstant) - se STATUS.md for tallene fra begge
    spots og hvorfor.

    Theodors tredje betingelse ("spoten ligger innenfor skyggelengden L fra
    exposure_baseline") er for øvrig IKKE en egen sjekk - den er, ved
    konstruksjon, allerede det samme som rå eksponering 0:
    exposure_baseline.shadow_exposure() setter nettopp raw=0,0 NÅR OG BARE
    NÅR avstanden til hindringen er mindre enn skyggelengden L.
    raw_exposure_zero() alene dekker den betingelsen.

    Brukt til å avgjøre når bw_confirms IKKE skal kunne overstyre
    retningsfaktoren (se barentswatch_height()) - motsatt situasjon av
    Unstad 28.09.2026, som bw_confirms ble laget for: der var svellet ute
    bare 3-5 grader utenfor vinduet og hindringen smal, så GFS sin retning
    var det usikre leddet. Her er geometrien (en bred halvøy under 2 km
    unna) sikrere enn BarentsWatch sin retning ved punktet.

    Mangler avstands- eller breddedata (eldre exposure_baseline.json, eller
    ugyldig sjekksum): faller tilbake til False (ingen blokkering) - samme
    forsiktige retning som raw_exposure_zero() sin egen fallback når rådata
    mangler helt."""
    if not raw_exposure_zero(d, spot):
        return False
    dist, width = spot.get("exposure_distance_km"), spot.get("exposure_width_km")
    if not dist or not width:
        return False
    i = int(round(d)) % 360
    km, w = dist[i], width[i]
    return km is not None and km < NEAR_OBSTACLE_MAX_KM and w is not None and w >= WIDE_OBSTACLE_MIN_KM


def swell_share(hour):
    """Andel av totalhøyden ute (swell_offshore / height_offshore) som er
    ekte svell - resten er vindsjø. BarentsWatch måler TOTALHØYDE (svell +
    vindsjø sammen), så dette brukes til å anslå hvor mye av en
    BarentsWatch-høyde som faktisk er svell. Avgrenset til 0,2-1,0 (under
    0,2 sier forholdet for lite til å stole på). Mangler en av høydene:
    1,0 (nøytralt) og "ukjent" (andre returverdi), IKKE straffet i seg selv,
    men gjør timen mer usikker et annet sted."""
    swell, total = hour.get("swell_offshore"), hour.get("height_offshore")
    if swell is None or total is None or total <= 0:
        return 1.0, False
    return min(1.0, max(0.2, swell / total)), True


BW_PERIOD_FACTOR_POINTS = [(6, 0.3), (8, 0.6)]  # deretter 1.0 fra og med 8s


def bw_period_factor(period):
    """Periodefaktor fra BarentsWatch sin egen periode (totalPeakPeriod -
    TOPPPERIODE, bekreftet mot BarentsWatch sin OpenAPI-spec 26.09.2026,
    derfor ingen nedjustering av grensene, som middelperiode ville trengt).
    Ekstra, uavhengig sjekk på om det er vindsjø: kort periode er vindsjø
    uansett hva swell_share sier. Mangler periode: 1,0 (nøytralt)."""
    if period is None:
        return 1.0
    (x0, y0), (x1, y1) = BW_PERIOD_FACTOR_POINTS
    if period < x0:
        return y0
    if period < x1:
        return y0 + (y1 - y0) * (period - x0) / (x1 - x0)
    return 1.0


SPOT_DIRECTION_ERROR_DEG = 150  # se spot_direction_factor() sin docstring


def spot_direction_factor(bw_dir_from, facing):
    """0 til 1: går bølgene ved BarentsWatch-punktet inn mot stranda?
    bw_dir_from er allerede konvertert til "fra" (se sources.barentswatch_point
    - BarentsWatch sitt eget felt er retningen bølgene GÅR MOT). facing er
    retningen rett ut i vannet fra stranda (spots.json). 0-30 grader avvik:
    1,0. 30-60: lineært ned til 0,3. Over 60: 0. Mangler retning eller
    facing: 1,0 (nøytralt, men "ukjent" i andre returverdi).

    27.09.2026, andre runde: over SPOT_DIRECTION_ERROR_DEG (150) grader fra
    facing betyr at bølgene ved punktet FAKTISK går ut fra land - typisk
    vindsjø fra land, ikke svell inn. Dette er en KJENT retning, ikke en
    ukjent eller mistenkelig en (den forrige runden trodde dette var et
    symptom på en manglende "mot"->"fra"-konvertering i sources.py - det
    var det, men konverteringen er nå rettet ved kilden, og et ekte >150-
    graders avvik er en normal, forventet observasjon på noen spots, ikke
    et feiltegn). Får derfor faktor 0 (ekte straff, som resten av kurven
    over 60 grader), IKKE nøytral 1,0, og gjør IKKE timen usikker eller
    utløser sources_disagree alene (se rate()). Tredje returverdi er sann
    nettopp for dette tilfellet (>150 grader), til bruk i forklaringsteksten
    ("bølgene går ut fra land") og i fetch.py sin spotnivå-sikring mot at
    konvensjonen skulle bli feil igjen. Returnerer (verdi, kjent, ut fra
    land)."""
    if bw_dir_from is None or facing is None:
        return 1.0, False, False
    diff = angle_diff(bw_dir_from, facing)
    if diff <= 30:
        return 1.0, True, False
    if diff <= 60:
        return 1.0 - 0.7 * (diff - 30) / 30, True, False
    if diff <= SPOT_DIRECTION_ERROR_DEG:
        return 0.0, True, False
    return 0.0, True, True


SPOT_DIRECTION_OVERRIDE_EXPOSURE = 0.667  # se barentswatch_height() sin docstring
BW_CONFIRM_DIFF_DEG = 30  # se barentswatch_height() sin docstring (bw_confirms)
# BW_CONFIRM_MIN_HEIGHT settes IKKE til en egen konstant her - FLAT_HS_THRESHOLD
# (0,35 m, "samme grense som flatt") er definert lenger ned i fila og brukes
# direkte inni barentswatch_height() i stedet, siden modulnivå-kode kjører i
# filrekkefølge (en alias-konstant her ville feilet ved import).


def barentswatch_height(hour, spot):
    """BarentsWatch gir totalhøyde (svell + vindsjø), ikke bare svell -
    skalert her til et anslag på ekte svell ved spoten:
    bw_height × min(swell_share, bw_period_factor) × spot_direction_factor.
    min(), ikke produkt, av swell_share og periodefaktoren: de er to
    uavhengige mål på samme spørsmål (er dette vindsjø?), og skal ikke
    straffe dobbelt for det samme.

    27.09.2026, Theodors rettelse (Unstad for lav - se STATUS.md): retnings-
    faktoren over ble laget for tilfeller der svellet UTE kommer utenfor
    vinduet (Lenangsøyra 26.09.2026) - da vet vi ikke om det treffer, og
    BarentsWatch-retningen VED KYSTEN er det beste vi har. Men når svellet
    ute allerede har god eksponering mot spoten (exposure() >= 0,667 - samme
    grense som sources_disagree sin "dårlig eksponert"), vet vi ALLEREDE at
    det treffer - og BarentsWatch sin egen retning ved kystpunktet har vist
    seg upålitelig i akkurat den situasjonen (Unstad 26.09 og 27.09.2026,
    se CLAUDE.md sine faste observasjoner: retningen ved punktet varierte
    med flere grader time for time mens det ekte svellet utvilsomt traff).

    30.09.2026 (Unstad 28.09.2026, "Safe to say it's firing" - se STATUS.md):
    motsatt tilfelle. Svellet ute var 3-5 grader UTENFOR vinduet (eksponering
    62-66 %, rett under 0,667-grensen over), MEN BarentsWatch ved SPOTEN selv
    sa bølgene kom inn nesten rett på (1 grad fra facing) med god høyde -
    altså en ekte bekreftelse fra kystmodellen, ikke en upålitelig
    enkeltmåling. Svellretningen ute (GFS, Open-Meteo) kan bomme 10-20
    grader; BarentsWatch sin egen kystmodell ved punktet er mer presis der
    den faktisk har data. Ny, uavhengig bekreftelse: `bw_confirms` - sann
    når retningen ved punktet er innenfor BW_CONFIRM_DIFF_DEG (30) grader av
    facing OG høyden UTEN retningsfaktoren (bw × min(svellandel,
    periodefaktor) - beregnet FØR dirfac, for å unngå sirkularitet: om
    punktet bekrefter skal ikke avhenge av selve retningsfaktoren den
    avgjør) er minst FLAT_HS_THRESHOLD (0,35 m, samme grense som "flatt"). Når BarentsWatch bekrefter på denne måten, brukes heller ikke
    lav eksponering ute til å trekke ned retningsfaktoren - samme idé som
    eksponerings-overstyringen over, bare fra motsatt kant (punktet i stedet
    for det ytre svellet). De to overstyringene er uavhengige av hverandre
    (ett er nok), og begge brukes også i rate() sin sources_disagree (se
    der) - når BarentsWatch bekrefter, skal lav eksponering ute ikke alene
    utløse "kildene uenige" heller.

    Retningsfaktoren brukes derfor BARE når INGEN av de to overstyringene
    slår til - ellers er den 1,0, uansett hva BarentsWatch-retningen ved
    punktet isolert sett ville gitt. Skru IKKE av dette ved å sette grensene
    til 0 eller 1 - da mister man sikringen (Lenangsøyra ville gått opp)."""
    bw = hour["bw_height"]
    share, share_known = swell_share(hour)
    pf = bw_period_factor(hour.get("bw_period"))
    bw_dir = hour.get("bw_dir")
    facing = spot.get("facing")
    raw_dirfac, dir_known, dir_offshore = spot_direction_factor(bw_dir, facing)
    diff = angle_diff(bw_dir, facing) if dir_known else None
    # Høyden UTEN retningsfaktoren - bw_confirms sin egen bekreftelse skal
    # ikke avhenge av overstyringen den selv er med på å avgjøre.
    h_sans_dir = bw * min(share, pf)
    # 06.10.2026, Theodors rettelse (Farstadsanden 337 grader - se STATUS.md):
    # bw_confirms skal ikke kunne overstyre når svellet ute (dir_off, IKKE
    # bw_dir - det er bw_confirms sin EGEN retning, aldri sjekket mot seg
    # selv) treffer en nær, bred hindring - se blocked_by_near_obstacle().
    dir_off = hour.get("dir_offshore")
    blocked_near = blocked_by_near_obstacle(dir_off, spot)
    bw_confirms = (dir_known and diff <= BW_CONFIRM_DIFF_DEG
                   and h_sans_dir >= FLAT_HS_THRESHOLD and not blocked_near)
    # Krever at dir_offshore FAKTISK er kjent - exposure()/directness() sin
    # egen "ukjent retning"-nøytralverdi (0,7, se directness() sin docstring)
    # ligger OVER 0,667-grensa, og ville ellers overstyrt retningsfaktoren
    # uten noen bekreftelse i det hele tatt på at svellet ute treffer -
    # stikk i strid med selve premisset for regelen. Funnet av
    # fysikk-kontrollør 30.09.2026 (Theodors rettelse, Unstad for lav).
    offshore_exposure = exposure(dir_off, spot, hour.get("period")) if dir_off is not None else None
    exposure_overridden = offshore_exposure is not None and offshore_exposure >= SPOT_DIRECTION_OVERRIDE_EXPOSURE
    overridden = exposure_overridden or bw_confirms
    dirfac = 1.0 if overridden else raw_dirfac
    h = bw * min(share, pf) * dirfac
    detail = {
        "swell_share": share, "swell_share_known": share_known,
        "bw_period_factor": pf,
        "spot_direction_factor": dirfac,
        # "Kjent" rører IKKE overstyringen - den sier bare om vi FAKTISK har
        # en BarentsWatch-retning og facing å sammenligne (uendret av om vi
        # velger å stole på den eller ikke), og skal fortsatt gjøre timen
        # usikker når retningen ved punktet rett og slett mangler (se 7.7 i
        # test_rating.py - overstyringen erstatter IKKE ekte data vi ikke
        # har). "Ut fra land" derimot er en PÅSTAND om selve retningen -
        # den skal ikke vises når vi nettopp har valgt å ikke stole på den.
        "spot_direction_known": dir_known,
        # Bølgene ved punktet går faktisk ut fra land (avvik over
        # SPOT_DIRECTION_ERROR_DEG) - se spot_direction_factor() sin
        # docstring og rate() sin bruk av dette. bw_confirms krever diff<=30,
        # uforenlig med >150 - trenger ikke slås av for den overstyringen.
        "spot_direction_offshore": False if exposure_overridden else dir_offshore,
        # Selve gradavviket (0-180), til visning ("70 grader skrått på
        # stranda") - factoren alene sier ikke hvor mange grader det var.
        # Vises uansett overstyring, til feilsøking/kilderapport.
        "spot_direction_diff": diff,
        # Bare EKSPONERINGS-overstyringen - styrer "ikke brukt, svellet ute
        # treffer godt"-teksten i breakdown (se build_breakdown()). Når
        # bw_confirms alene er sann, er raw_dirfac allerede 1,0 (diff<=30
        # gir alltid 1,0 i spot_direction_factor()), så normal tekst
        # ("rett inn mot stranda") er allerede riktig uten særtilfelle.
        "spot_direction_overridden": exposure_overridden,
        "bw_confirms": bw_confirms,
    }
    return h, detail


def spot_height(hour, spot=None):
    """Beste anslag på bølgehøyde på spoten, hvilken kilde det kom fra, og
    (bare for BarentsWatch) detaljene bak beregningen (se barentswatch_height).
    Dette er Hs (signifikant høyde) ved spoten - grunnlaget for surf_height
    (se breaking_height() lenger ned), IKKE selve surfehøyden man ser i
    appen. Også det kalibreringen (transfer) læres mot - egen, fysisk
    størrelse, ikke det man ser fra stranda (det er surf_factor sin jobb).

    1. BarentsWatch, når den finnes (finmasket kystmodell som allerede tar
       hensyn til skjerming bak odder og øyer) - se barentswatch_height().
    2. Bare svellet ute (Open-Meteo), uten vindsjø, ganget med spotens
       faktor og exposure() - hvor mye av svellet som når spoten fra denne
       retningen (glattet geometri, del C - se exposure() sin docstring).
       Faktoren læres fra loggene dine (transfer). Bruker IKKE
       dreiningsregelen her, ellers straffes skrått svell to ganger.
    3. Reserve: total bølgehøyde fra met.no på spoten, med dreiningsregelen.
    """
    if hour.get("bw_height") is not None:
        h, detail = barentswatch_height(hour, spot or {})
        return h, "barentswatch", detail
    transfer = (spot or {}).get("transfer", DEFAULT_TRANSFER)
    if hour.get("swell_offshore") is not None:
        h = hour["swell_offshore"] * transfer * exposure(hour.get("dir_offshore"), spot, hour.get("period"))
        return h, "svell_ute", None
    h = hour.get("height_spot_model")
    if h is None:
        return None, None, None
    return h * refraction_factor(hour.get("turn")), "metno_korrigert", None


# ---------- Surfehøyde ----------
# 26.09.2026: signifikant høyde (Hs, gjennomsnittet ute i vannet) er ikke det
# surfere ser eller logger - det er høyden der bølgene BREKKER. Langt svell
# reiser seg mye mer på grunt vann enn kort svell med samme Hs. Tidligere
# forsøkte periodefaktoren (nå fjernet) å lappe dette med en svak, ufysisk
# multiplikator bare i rangeringen. Nå brukes en ekte, empirisk formel, og
# resultatet (surf_height) er det som faktisk vises og kalibreres mot.

SURF_G = 9.81
SURF_SETS_FACTOR = 1.27  # settene (de største bølgene) er ca 1.27x Hb
FLAT_HS_THRESHOLD = 0.35  # under dette er det uansett flatt, se rate()
SURF_FACTOR_DEFAULT = 1.0
SURF_FACTOR_MIN, SURF_FACTOR_MAX = 0.5, 1.6


def breaking_height(h, period):
    """Hb, høyden der bølgene brekker - Komar og Gaughan (1972):
    Hb = 0,39 * g^(1/5) * (T * H^2)^(2/5)
    H = signifikant høyde ved spoten (m), T = svellets periode UTE i sekunder
    (Open-Meteo - perioden endres ikke av grunning, se rate()). Empirisk
    formel laget for rette, jevne SANDSTRENDER - pointbreak og revbrekk kan
    avvike fra dette. Derfor læres en egen surf_factor per spot fra loggene
    (se calibrate.py), i stedet for å stole blindt på formelen alene.
    Kontrollverdier (Unstad 26.09.2026, etter at retningskonvensjonen ble
    rettet): H 0,9 m/T 15 s -> Hb ca 1,67 m, sett ca 2,1 m - stemte med
    video fra Lofoten Surfsenter samme time."""
    if h is None or period is None or h <= 0:
        return None
    return 0.39 * SURF_G ** 0.2 * (period * h ** 2) ** 0.4


WATER_RHO = 1025  # kg/m3, sjøvann
ENERGY_COEF = WATER_RHO * SURF_G ** 2 / (16 * math.pi)  # se energy_kj()


def energy_kj(height, period):
    """06.10.2026, Theodors oppgave (Magnus, lokal surfer - se CLAUDE.md sin
    'Lokalkunnskap'): bølgeenergi i kJ, samme mål som surf-forecast.com viser.
    E = rho * g^2 * H^2 * T^2 / (16*pi) - energien i ÉN BØLGELENGDE PER METER
    BØLGETOPP for en jevn (monokromatisk) bølge: arealenergitetthet
    (1/8)*rho*g*H^2 ganget med bølgelengden i dypt vann, L = g*T^2/(2*pi).
    H og T er SAMME par som resten av appen bruker ute (ikke BarentsWatch sin
    periode ved kysten) - kalleren velger om H er svell_offshore (ekte svell,
    brukt i de myke lokale reglene) eller height_offshore (totalhøyde,
    sannsynligvis det yr/surf-forecast selv viser, se 1b i oppgaven).

    Kontrollert mot fem tall Theodor leste av surf-forecast.com for
    Farstadsanden: 2,4 m/11 s, 3 m/11 s, 3 m/14 s, 4 m/15 s, 5,5 m/16 s.
    Formelen (fysisk korrekt utledet, se over) treffer tre av fem innenfor
    5 % (1,1-4,5 % avvik), men IKKE 3 m/11 s (7,9 %) eller 5,5 m/16 s (5,6 %)
    - ingen enkelt konstant foran H^2*T^2 kan treffe alle fem innenfor 5 %
    samtidig (det underliggende forholdstallet surf-forecast sitt tall/
    (H^2*T^2) spriker fra 1,82 til 2,06 mellom de fem punktene, et 11,5 %
    sprik i seg selv - trolig avrunding i H/T før surf-forecast sin egen,
    interne beregning, forsterket av kvadratleddene). Theodor varslet selv
    (se STATUS.md). Endret ALDRI stjernene direkte - bare et tall til visning
    og én av flere faktorer i de myke lokale reglene (se local_rules_effect())."""
    if height is None or period is None or height <= 0 or period <= 0:
        return None
    return ENERGY_COEF * height ** 2 * period ** 2 / 1000


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


PERIOD_SCORE_POINTS = [(6, 0.4), (8, 0.65), (10, 0.85), (12, 0.95), (14, 1.0)]  # se period_score()


def period_score(p):
    """06.10.2026, Theodors rettelse (se CLAUDE.md/STATUS.md): lineær kurve
    mellom faste punkter - 6 s eller kortere 0,4; 8 s 0,65; 10 s 0,85; 12 s
    0,95; 14 s eller lengre 1,0. Universell, IKKE lenger per spot (gammel
    `spot["min_period"]`, identisk 8 for alle 8 spots - feltet er derfor
    fjernet fra spots.json, det differensierte aldri noe i praksis).

    Begrunnelse (Theodors egen, ikke oppfunnet): breaking_height() (Komar og
    Gaughan) belønner lang periode gjennom selve surfehøyden (høyere bølger
    ved samme Hs) - men IKKE kraften i bølgene. Kort periode gir svake
    bølger selv ved samme høyde (mindre vannmasse i bevegelse per bølge,
    kortere bølgelengde). Dette er IKKE dobbelttelling: høyde og kraft er to
    ulike fysiske egenskaper, og formelen fanger bare den første. Gammel
    kurve ga 8 s FULL uttelling (1,0) - urealistisk sterkt for en kort
    periode, og ga typiske 8-sekunders dager 3 stjerner for lett."""
    if p is None:
        return 0.5
    (x0, y0) = PERIOD_SCORE_POINTS[0]
    if p <= x0:
        return y0
    for (x0, y0), (x1, y1) in zip(PERIOD_SCORE_POINTS, PERIOD_SCORE_POINTS[1:]):
        if p <= x1:
            return y0 + (y1 - y0) * (p - x0) / (x1 - x0)
    return PERIOD_SCORE_POINTS[-1][1]


def direction_score(d, spot, source=None):
    """Retningsstraff for stjernene. Når høyden allerede kommer fra en kilde
    som tar hensyn til retningen (svell_ute sin exposure(), eller
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


# ---------- Vind ----------

def wind_type(wind_dir, spot):
    """06.10.2026, Theodors rettelse (andre runde - Unstad sin utvidede
    offshore_wind [70,232] gjorde en tidligere versjon av denne funksjonen
    (kant-avstand til SEKTOREN for hele firedelingen) mildere for NV-vind
    (280-320 grader) UTEN observasjonsstøtte - se STATUS.md). To uavhengige
    spørsmål nå, ikke ett:

    1. Offshore: avgjøres ALENE av spotens offshore_wind-sektor (kan være
       utvidet, eller i prinsippet flere deler - se in_sector()). Rent
       geografisk/empirisk, ikke avledet fra facing.
    2. Ellers (side/side-onshore/onshore): avgjøres av vinkelen til FACING
       (retningen stranda vender ut mot havet - IKKE senteret eller kanten
       av offshore-sektoren). Vind innenfor 45 grader av facing er dead
       onshore (kommer rett fra den kanten havet står åpent), 45-80 grader
       side-onshore, over 80 side. Fysisk riktigere enn å måle fra
       offshore-sektoren: en VID offshore-sektor (som Unstad sin nye) skal
       ikke gjøre den stikk motsatte, verste retningen (294,8 grader for
       Unstad) mildere bare fordi sektoren ble bredere et annet sted.

    For en spot der offshore_wind er NØYAKTIG facing+180 ± 45 grader (den
    opprinnelige, implisitte antagelsen for alle 8 spots) gir dette TALLMESSIG
    samme svar som den aller første versjonen av denne funksjonen (vinkel til
    SENTERET av offshore_wind) - bevist: utenfor sektoren er vinkel-til-kant
    X alltid senter-avstand 45+X, og senter-avstand = 180 - vinkel-til-facing
    (facing og senteret er motsatte punkter) gir nøyaktig de samme fire
    grensene (45/100/135 fra senter <-> 45/80 fra facing). Men IKKE alle 8
    spots har offshore_wind eksakt sentrert på facing+180 (Grøtfjord,
    Lenangsøyra og Steinkrøssa avviker 5-20 grader, sjekket mot spots.json)
    - for DEM endrer denne rettelsen altså noe reelt, ikke bare Unstad. Se
    STATUS.md for den fulle, verifiserte tabellen (ikke antatt)."""
    if wind_dir is None:
        return None
    if in_sector(wind_dir, spot["offshore_wind"]):
        return "offshore"
    facing = spot.get("facing")
    if facing is None:
        return "onshore"  # ukjent facing: anta verste fall, samme filosofi som andre steder
    b = angle_diff(wind_dir, facing)
    if b < 45:
        return "onshore"
    if b < 80:
        return "sideonshore"
    return "side"


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


def _share_word(share):
    if share >= 0.9:
        return "nesten bare svell"
    if share >= 0.7:
        return "mest svell"
    if share >= 0.5:
        return "blandet, en del vindsjø"
    return "mest vindsjø"


def _bw_period_word(pf):
    if pf >= 1.0:
        return "lang nok til å være ekte svell"
    if pf >= 0.6:
        return "i grenseland"
    return "kort, trolig vindsjø"


def _spot_dir_word(dirfac):
    if dirfac >= 1.0:
        return "rett inn mot stranda"
    if dirfac > 0:
        return "skrått inn mot stranda"
    return "går ikke inn mot stranda"


def _fmt_m(v):
    return f"{v:.1f}".replace(".", ",") + " m"


def _fmt_penalty(n):
    return "ingen effekt" if n == 0 else f"−{n}"


def disagree_reason(hour, dir_hit, bw_detail):
    """Kort norsk forklaring på HVA av 4a-betingelsene som slo inn, til
    varselbanneret på detaljsiden (5c). Bygget her, ikke i appen - appen
    skal bare vise det henteren faktisk regnet ut."""
    reasons = []
    if dir_hit is not None and dir_hit < SPOT_DIRECTION_OVERRIDE_EXPOSURE:
        reasons.append("svellet ute er dårlig eksponert mot spoten")
    if bw_detail["swell_share"] < 0.5:
        reasons.append("det er mest vindsjø")
    if bw_detail["spot_direction_factor"] < 0.5:
        reasons.append("bølgene ved spoten går ikke inn mot stranda")
    bw_h = hour.get("bw_height")
    bw_txt = _fmt_m(bw_h) if bw_h is not None else "en del"
    return f"Kildene er uenige. BarentsWatch viser {bw_txt}, men {' og '.join(reasons)}. Trolig ikke surfbart. Logg gjerne hva du ser."


def build_breakdown(hour, spot, h, source, bw_detail, hb, surf_factor, surf_height,
                     surf_height_sets, low_hs, blown_out, hb_damping, period, hs, ps, dir_hit,
                     wind_speed, wind_dir, gust, wt, wp, tide, tide_pen,
                     potential, solid, lost_wind, lost_tide, uncertain,
                     sources_disagree, capped_from, disagree_cap,
                     energy_swell_kj=None, energy_factor_value=1.0):
    items = []
    # 27.09.2026 (Theodors rettelse, Unstad for lav - se STATUS.md): tallet
    # vi regner videre med (h) er JUSTERT for BarentsWatch (svellandel,
    # periode, retning ved punktet) - skal aldri kalles "signifikant" alene,
    # det begrepet gjelder BarentsWatch sin EGEN totalhøyde (bw_height).
    # Egen "Etter justering"-linje under viser selve justeringen, med bare
    # leddene som faktisk trekker ned (samme visning som docs/index.html
    # sin surfAdjustmentLine()).
    bw_h = hour.get("bw_height") if source == "barentswatch" else None
    if h is None:
        items.append("Signifikant høyde: ingen data")
    elif bw_h is not None:
        items.append(f"BarentsWatch {_fmt_m(bw_h)} signifikant")
    else:
        items.append(f"Signifikant høyde {_fmt_m(h)} ute ved spoten")
    if source == "barentswatch" and bw_detail is not None:
        share_pct = round(bw_detail["swell_share"] * 100)
        items.append(f"Svellandel: {share_pct} % ({_share_word(bw_detail['swell_share'])})")
        if hour.get("bw_period") is not None:
            items.append(f"BarentsWatch-periode {hour['bw_period']:.0f} s: {_bw_period_word(bw_detail['bw_period_factor'])}")
        if bw_detail["spot_direction_offshore"]:
            items.append("Bølgene ved spoten går ut fra land. Trolig vindsjø fra land, ikke svell inn.")
        elif bw_detail.get("spot_direction_overridden"):
            items.append("Retning ved spoten: ikke brukt - svellet ute treffer godt")
        else:
            items.append(f"Retning ved spoten: {_spot_dir_word(bw_detail['spot_direction_factor'])}")
        if h is not None and bw_h is not None:
            share, pf, dirfac = bw_detail["swell_share"], bw_detail["bw_period_factor"], bw_detail["spot_direction_factor"]
            share_ok, pf_ok, dir_ok = share >= 0.999, pf >= 0.999, dirfac >= 0.999
            if not (share_ok and pf_ok and dir_ok):
                reasons = []
                if not share_ok and (pf_ok or share <= pf):
                    reasons.append(f"svellandel {round(share * 100)} %")
                elif not pf_ok:
                    reasons.append("kort BarentsWatch-periode")
                if not dir_ok:
                    reasons.append("retning ved punktet")
                items.append(f"Etter justering {_fmt_m(h)} ({', '.join(reasons)})")
    if h is not None:
        if period is None:
            items.append("Periode (ute): ukjent")
        else:
            items.append(f"Periode {period:.0f} s (ute): {_period_word(ps)}")
        # 06.10.2026, Theodors oppgave (andre runde): energifaktoren er nå
        # universell (alle spots) - egen linje her i stedet for bare i
        # local_rules sin egen seksjon (som fortsatt bare viser Farstadsanden
        # sine tide-/vind-spesifikke straffer). Viser svell-energien (det
        # regelen faktisk bruker, se rate()), IKKE totalhøyde-energien
        # ("Svell ute"-cella over viser den, som energy_total_kj).
        if energy_swell_kj is not None:
            if energy_factor_value < 0.999:
                items.append(f"Energi (svell) {round(energy_swell_kj)} kJ: faktor {energy_factor_value:.2f} "
                              f"(potensial ganget ned)")
            else:
                items.append(f"Energi (svell) {round(energy_swell_kj)} kJ: over terskelen, ingen effekt")
        if blown_out:
            items.append(f"Surfehøyde: blåst ut - mye vindsjø og sterk vind, ikke surfbart "
                         f"(BarentsWatch {_fmt_m(hour['bw_height'])} totalt ved punktet)")
        elif low_hs:
            items.append(f"Surfehøyde: flatt (signifikant høyde under {_fmt_m(FLAT_HS_THRESHOLD)})")
        elif hb is None:
            items.append("Surfehøyde: ingen data (mangler periode)")
        else:
            if hb_damping < 0.999:
                damp = (" (dempet, bølgene ved spoten treffer skrått)" if source == "barentswatch"
                        else " (dempet, svellet er i kanten av eller utenfor vinduet)")
            else:
                damp = ""
            items.append(f"Bruddhøyde (Hb, Komar og Gaughan 1972) {_fmt_m(hb)}{damp}")
            sf_line = f"Surf-faktor {surf_factor:.2f}".replace(".", ",")
            # 30.09.2026 (Theodors rettelse, Unstad for lav - se STATUS.md):
            # en surf_factor_prior fra spots.json (startverdi fra ekte,
            # navngitte observasjoner, FØR det finnes nok logger til å lære
            # selv) skal vises som nettopp det - ikke se ut som en lært verdi.
            if spot.get("surf_factor_source") == "prior":
                n = spot.get("surf_factor_prior_n")
                sf_line += f" (startverdi fra {n} observasjoner)" if n else " (startverdi, ikke lært fra logger)"
            items.append(sf_line)
            items.append(f"Surfehøyde {_fmt_m(surf_height)}, sett ca. {_fmt_m(surf_height_sets)}: {_height_word(hs)}")
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
    if sources_disagree and disagree_cap is not None and disagree_cap > potential:
        items.append(f"Kilder uenige: kappet fra {disagree_cap} til maks 1 stjerne")
    elif capped_from is not None and capped_from > potential:
        items.append(f"Usikkert varsel: kappet fra {capped_from} til maks 3 stjerner (ingen BarentsWatch, og retning utenfor vinduet eller stor dreining)")
    without_wind = min(potential, solid + lost_wind)
    total = f"Totalt: {solid} av 5 stjerner"
    if lost_wind > 0:
        total += f" ({without_wind} uten vind)"
    items.append(total)
    return items


BLOWN_OUT_WIND_MS = 8.0  # samme grense som WIND_PENALTY_TABLE sin "kraftig"-sone
BLOWN_OUT_SHARE_MAX = 0.5  # samme "mest vindsjø"-grense som _share_word()
# 27.09.2026, fysikk-kontrollør sitt funn: samme grense som sources_disagree
# (se rate(), "BarentsWatch viser en reell totalhøyde (0,5 m+)") - IKKE
# FLAT_HS_THRESHOLD (0,35 m), som ville latt 0,36-0,49 m telle som "reell
# energi" selv om det fortsatt reelt sett er lite.
BLOWN_OUT_MIN_BW_HEIGHT = 0.5


def is_blown_out(hour, spot, source, bw_detail, low_hs):
    """27.09.2026: Grøtfjord tirsdag kl. 14 viste "Trolig flatt"/0,0 m mens
    svellet ute var 0,9 av 5,9 m totalt (mest vindsjø) og vinden 14 m/s
    side-onshore, kast 21 - ikke flatt (lite energi), men BLÅST UT (mye
    energi, bare ikke ekte svell). Skiller de to: flatt er fortsatt
    low_hs alene (lav BarentsWatch-høyde OGSÅ - lite energi totalt), blåst
    ut er low_hs PÅ TROSS AV en reell, ikke-lav BarentsWatch-totalhøyde,
    fordi svellandelen er lav eller vinden er sterk og onshore/side-onshore.
    Bare for BarentsWatch (samme kilde som viste 0,0 m i det ekte tilfellet) -
    reservemodellen (svell_ute/metno_korrigert) har ikke noe eget mål på
    "totalhøyde ved spoten" uavhengig av selve svellberegningen."""
    if not (low_hs and source == "barentswatch" and bw_detail is not None):
        return False
    bw = hour.get("bw_height")
    if bw is None or bw < BLOWN_OUT_MIN_BW_HEIGHT:
        return False
    share_low = bw_detail["swell_share"] < BLOWN_OUT_SHARE_MAX
    wt = wind_type(hour.get("wind_dir"), spot)
    speed = hour.get("wind_speed")
    strong_onshore = wt in ("onshore", "sideonshore") and speed is not None and speed >= BLOWN_OUT_WIND_MS
    return share_low or strong_onshore


STORMSJO_SHARE_MAX = 0.4  # "lav svellandel", se classify_low_rating()
LOW_RATING_FLAT_SURF_HEIGHT_MAX = 0.4  # "surfehøyde under ca. 0,4 m", se classify_low_rating()


def classify_low_rating(hour, spot, source, bw_detail, low_hs, surf_height, dir_hit,
                         potential, lost_wind, lost_tide, solid, blown_out, energy_swell=None):
    """05.10.2026 (Theodors rettelse, Grøtfjord kl. 11-17, 05.10.2026 - se
    STATUS.md): ordet for 0 og 1 stjerne skal si HVORFOR, ikke bare "Flatt"
    for alt (den gamle STAR_WORDS[0] i appen var bokstavelig talt "Flatt",
    uansett årsak - is_blown_out() over krevde low_hs, så en time med reell
    høyde som ble null-stjerners av ren vindstraff falt tvers igjennom til
    "Flatt"). Fire grunner, sjekket i denne rekkefølgen (den første som
    stemmer vinner):

    1. flat: reelt lite totalenergi - flat-sperren (low_hs) eller lav
       surfehøyde (under LOW_RATING_FLAT_SURF_HEIGHT_MAX), OG BarentsWatch
       sin egen totalhøyde (der den finnes) er også lav. Dette er den
       opprinnelige "likely_flat"-saken - ingen energi å hente uansett
       hvorfor. Når low_hs er sann er potensialet (under) uansett 0, så
       denne kan aldri kollidere med "blown_out" sin vind-dominans-sjekk.
    2. blown_out: IKKE flatt (reell høyde, eller den gamle
       is_blown_out()-saken: reell BarentsWatch-totalhøyde PÅ TROSS AV
       low_hs), men vindstraffen er det som faktisk tok (de fleste av)
       stjernene. "Vind-dominant" krever et potensial på minst 1 FØR vind
       og tidevann - ellers var det ingenting vinden kunne ta.
       06.10.2026, Theodors rettelse (andre runde, se STATUS.md): grensa var
       opprinnelig 2, satt i en tid der bare høyde/periode/retning (og en
       sjelden Farstadsanden-only energiregel) kunne redusere potensialet
       FØR vind. Nå energifaktoren er universell kan DEN alene presse
       potensialet ned til 1 - "minst 2" ville da feilaktig skjult en ekte
       vind-dominert time (Grøtfjord 05.10.2026, lav svellenergi OG 13 m/s
       onshore samtidig) bak et tomt `low_reason`. "Minst 1" dekker fortsatt
       det opprinnelige poenget (potensial 0 betyr bokstavelig talt
       ingenting å ta), og krever fortsatt at vind faktisk tok noe
       (lost_wind > 0) minst like mye som tidevannet.
    3. stormsjo: lav svellandel (det meste av BarentsWatch sin totalhøyde
       er vindsjø, ikke ekte svell) OG en reell totalhøyde (ikke lite
       energi totalt - det er heller 1, flat).
    4. treffer_ikke: svellet ute bommer på vinduet (dir_hit under samme
       0,667-grense som sources_disagree), og BarentsWatch ved SPOTEN
       bekrefter ikke treff (bw_confirms, se barentswatch_height()) -
       svellet når rett og slett ikke denne spoten nå.

    None hvis stjernene er 2 eller mer (ingen grunn å forklare), eller hvis
    ingen av de fire slår til (f.eks. bare tidevannet som tok stjernene).

    07.10.2026, Theodors rettelse (Grøtfjord om ca. 10 dager: svell ute 2,3
    m/15 s, ca. 2 200 kJ, fra 271° - 15° utenfor vinduet, bak Tromvik-
    halvøya - appen sa "Flatt, 0,1 m"): med så mye energi ute er det ikke
    flatt, det er svellet som ikke treffer. Når høyden er lav FORDI
    retningen bommer (reservemodellen, dir_hit under 0,667) OG svellenergien
    ute er høy (over spotens "zero"-grense i energifaktoren - under den er
    energien reelt lav uansett), er ordet "treffer_ikke", ikke "flat".
    "Flat" bare når energien ute også er lav (eller ukjent). Gjelder ikke
    BarentsWatch-timer: der har kystmodellen selv målt lite ved punktet
    (Grøtfjord 26.09.2026: 2,2 m/15,6 s ute fra 272°, BarentsWatch 0,33 m -
    observert helt flatt, og ordet forblir "Flatt")."""
    if solid > 1:
        return None
    bw = hour.get("bw_height") if source == "barentswatch" else None
    little_total = bw is None or bw < BLOWN_OUT_MIN_BW_HEIGHT
    flat = little_total and (low_hs or (surf_height is not None and surf_height < LOW_RATING_FLAT_SURF_HEIGHT_MAX))
    if flat:
        if (source != "barentswatch" and dir_hit is not None and dir_hit < SPOT_DIRECTION_OVERRIDE_EXPOSURE
                and energy_swell is not None and energy_swell >= energy_thresholds_used(spot)[1]):
            return "treffer_ikke"
        return "flat"
    wind_dominant = potential >= 1 and lost_wind > 0 and lost_wind >= lost_tide
    if blown_out or wind_dominant:
        return "blown_out"
    if bw_detail is not None and not little_total and bw_detail["swell_share"] < STORMSJO_SHARE_MAX:
        return "stormsjo"
    if (dir_hit is not None and dir_hit < SPOT_DIRECTION_OVERRIDE_EXPOSURE
            and not (bw_detail and bw_detail.get("bw_confirms"))):
        return "treffer_ikke"
    return None


# ---------- Myke lokale regler (Magnus, se CLAUDE.md "Lokalkunnskap") ----------
# 06.10.2026, Theodors oppgave. Valgfritt felt spot["local_rules"] - ingen
# effekt i det hele tatt når feltet mangler (de aller fleste spots). Hver
# delregel i local_rules er uavhengig valgfri (sjekk begge nøklene den
# trenger finnes, ikke bare at local_rules selv finnes) - en spot kan sette
# bare energi, bare tidevann, osv.

LOCAL_ENERGY_FACTOR_FLOOR = 0.3  # se energy_factor()
# 06.10.2026, Theodors rettelse (se CLAUDE.md/STATUS.md): energifaktoren er
# ikke lenger en Farstadsanden-only "myk regel" (spot["local_rules"]) - den
# gjelder nå ALLE spots, med disse standardgrensene. En spot med
# local_rules.min_energy_kj/weight (i dag bare Farstadsanden, Magnus sine
# 3000/1500/0,7) overstyrer dem, akkurat som før.
ENERGY_FULL_DEFAULT = 2000   # kJ
ENERGY_ZERO_DEFAULT = 500    # kJ
ENERGY_WEIGHT_DEFAULT = 0.5


def energy_factor(spot, energy_swell):
    """Hvor mye svellstjernene (potensialet) skal ganges med ut fra
    SVELLENERGIEN ute (energy_swell - EKTE svell, IKKE totalhøyden som
    inkluderer vindsjø, se energy_kj()/rate() sin egen begrunnelse), FØR
    vind og tidevann trekker fra (Theodors eksplisitte rekkefølge, se
    rate()). 1,0 fra full-grensa, lineært ned til 0,3 ved zero-grensa, 0,3
    under zero. Universell (se modulnivå-konstantene over) - en spot med
    `local_rules.min_energy_kj`/`weight` (i dag bare Farstadsanden)
    overstyrer begge deler.

    weight (0-1, Theodors "klype salt") demper EFFEKTEN av regelen, ikke
    terskelen: faktor = 1 - weight*(1 - rå_faktor) - weight=0 gir alltid
    faktor 1,0 (ingen effekt i det hele tatt), weight=1 gir rå_faktor
    ublandet. Mangler energi: ingen effekt (nøytral 1,0) - en myk regel
    skal aldri straffe for data den ikke har.

    ROADMAP oppgave I (skjerming, ikke bygget ennå): `spot["shelter_factor"]`
    - når den finnes - justerer BEGGE grensene OPP (delt på faktoren, som er
    under 1,0 for en skjermet spot), siden en skjermet spot trenger mer
    energi UTE for samme effekt PÅ STRANDA. Ingen spot har dette feltet i
    dag - rent forberedt, uten effekt før oppgave I setter det."""
    if energy_swell is None:
        return 1.0
    rules = spot.get("local_rules") or {}
    thresholds = rules.get("min_energy_kj") or {}
    full = thresholds.get("full", ENERGY_FULL_DEFAULT)
    zero = thresholds.get("zero", ENERGY_ZERO_DEFAULT)
    shelter = spot.get("shelter_factor")
    if shelter is not None and 0 < shelter < 1:
        full, zero = full / shelter, zero / shelter
    if full is None or zero is None or full <= zero:
        return 1.0
    if energy_swell >= full:
        raw = 1.0
    elif energy_swell <= zero:
        raw = LOCAL_ENERGY_FACTOR_FLOOR
    else:
        raw = LOCAL_ENERGY_FACTOR_FLOOR + (1 - LOCAL_ENERGY_FACTOR_FLOOR) * (energy_swell - zero) / (full - zero)
    weight = rules.get("weight", ENERGY_WEIGHT_DEFAULT)
    return 1 - weight * (1 - raw)


def energy_thresholds_used(spot):
    """(full, zero, weight) FAKTISK brukt for spoten akkurat nå - samme
    standard/override/skjerming-logikk som energy_factor(), men uten å
    trenge en energi-verdi. Til visning (calibration sine *_used-felt,
    samme mønster som transfer_used/surf_factor_used) og til
    Logger-fanen sitt læringsforslag (se docs/index.html)."""
    rules = spot.get("local_rules") or {}
    thresholds = rules.get("min_energy_kj") or {}
    full = thresholds.get("full", ENERGY_FULL_DEFAULT)
    zero = thresholds.get("zero", ENERGY_ZERO_DEFAULT)
    shelter = spot.get("shelter_factor")
    if shelter is not None and 0 < shelter < 1:
        full, zero = full / shelter, zero / shelter
    return full, zero, rules.get("weight", ENERGY_WEIGHT_DEFAULT)


def local_rules_penalty(hour, spot, wind_type_, wind_speed):
    """Tidevann og en strengere offshore-sjekk, begge "koster stjerner" -
    trekkes fra `solid` (ETTER vind og tidevann sin vanlige straff, se
    rate()), som et eget, klart merket fradrag - IKKE lagt inn i
    faded_wind/faded_tide sin bokføring, som fortsatt bare skal vise hva
    VIND og TIDEVANN alene tar.

    weight demper hvert fradrag direkte (effektiv straff = weight*rå_straff
    stjerner), summert FØR avrunding til nærmeste hele stjerne (0,5 rundes
    OPP - vanlig avrunding, ikke Pythons "bankers rounding" som ville gitt
    0 for nøyaktig 0,5 her, uforutsigbart for noe som skal vises som "koster
    én stjerne")."""
    rules = spot.get("local_rules")
    if not rules:
        return 0, []
    weight = rules.get("weight", 1.0)
    lines = []
    raw_total = 0.0

    if "tide_penalty_high" in rules and "tide_prefer" in rules:
        tide = hour.get("tide")
        state = tide.get("state") if tide else None
        if state is not None:
            if state not in rules["tide_prefer"]:
                pen = weight * rules["tide_penalty_high"]
                raw_total += pen
                lines.append(f"Tidevann ({state}): ikke blant det lokale favoriserer - "
                             f"−{rules['tide_penalty_high']} stjerne (vektet −{pen:.1f})")
            else:
                lines.append(f"Tidevann ({state}): foretrukket lokalt, ingen straff")

    if rules.get("offshore_strict"):
        strict_hit = (wind_type_ in ("side", "sideonshore")
                      and wind_speed is not None and wind_speed > 4)
        if strict_hit:
            pen = weight * 1
            raw_total += pen
            lines.append(f"Vind {wind_speed:.0f} m/s {WIND_TYPE_WORD.get(wind_type_, wind_type_)}: "
                         f"strengere lokal grense (over 4 m/s) - −1 stjerne (vektet −{pen:.1f})")

    extra_stars = math.floor(raw_total + 0.5)
    return extra_stars, lines


def rate(hour, spot):
    """Stjerner for én time. Blasse stjerner = det vind og tidevann tar."""
    h, source, bw_detail = spot_height(hour, spot)
    period = hour.get("period")  # Open-Meteo, svellet UTE - uendret av grunning
    # 27.09.2026, ROADMAP oppgave 2: eksponering (del C, glattet geometri)
    # erstatter directness() (vindu + skyggekurve) her - se exposure() sin
    # docstring. Brukes til Hb-demping for reservemodellen (under) og til
    # sources_disagree (samme grense 0,667 som før).
    dir_hit = exposure(hour.get("dir_offshore"), spot, period)

    # Flat-sperre: under FLAT_HS_THRESHOLD signifikant høyde ved spoten er
    # det uansett flatt i praksis. Komar og Gaughan sin formel gjør små
    # bølger urealistisk store ved lang periode (0,3 m/11 s gir Hb ca 0,6 m)
    # - Grøtfjord 24.09.2026 var et ekte eksempel: 0,3 m fra BarentsWatch,
    # helt flatt observert.
    low_hs = h is not None and h < FLAT_HS_THRESHOLD
    blown_out = is_blown_out(hour, spot, source, bw_detail, low_hs)
    hb_raw = None if (h is None or low_hs) else breaking_height(h, period)
    # 26.09.2026: svell i kanten av eller utenfor svellvinduet har bøyd seg
    # rundt en odde (diffraksjon) - bredere retningsspredning, mindre samlet
    # energi langs bølgefronten, og bygger seg IKKE opp på grunt vann som et
    # rent, uforstyrret svell. Komar og Gaughan sin formel vet ikke det (laget
    # for åpen kyst), og ga derfor for høy Hb for Grøtfjord 25.09.2026 (svell
    # 3 grader utenfor vinduet, observert helt flatt, men formelen alene ga
    # 3 stjerner). Dempes derfor - men bare når h IKKE allerede har samme
    # retningsfaktor bakt inn, ellers straffes retningen to ganger (funnet av
    # fysikk-kontrollør 27.09.2026, ROADMAP oppgave 2: h for svell_ute er
    # `swell_offshore * transfer * exposure(...)`, og h for barentswatch er
    # `bw * ... * spot_direction_factor` - begge har ALLEREDE dempet h selv.
    # Komar og Gaughan sin Hb ∝ H^0,8 arver da automatisk den samme
    # dempingen; å gange Hb med faktoren en gang til ga effektivt eksponent
    # ~1,8, ikke ~1,0, og var usynlig tidligere fordi både directness() (i et
    # vindu) og spot_direction_factor (nær-direkte treff) stort sett var
    # ≈1,0 i de faste observasjonene - exposure() sin videre spennvidde midt
    # i et vindu gjorde feilen synlig, se STATUS.md).
    #
    # 27.09.2026, tredje runde (Theodors rettelse - Ersfjordstranda 30.09 vs.
    # Unstad 30.09 viste at "ingen ny demping" var for enkelt): svell som
    # treffer med fri eller delvis fri siktlinje (rå geometrisk eksponering
    # over 0) skal IKKE dempes en ekstra gang - det var selve dobbelttellingen
    # over. Men svell som bare når spoten ved DIFFRAKSJON rundt land (rå
    # eksponering nøyaktig 0, se raw_exposure_zero()) bygger seg empirisk
    # dårligere opp enn Komar og Gaughan sin formel (laget for åpen kyst)
    # tror - samme fysikk som Grøtfjord 25.09.2026 sin observasjon (3 grader
    # utenfor vinduet, helt flatt) allerede viste. Der dempes Hb fortsatt med
    # eksponeringen, i tillegg til at eksponeringen alt er i h. Gjelder bare
    # reservemodellen (svell_ute) - BarentsWatch sin egen kystmodell har
    # allerede regnet ut den ekte bøyingen inn mot punktet, og dempes aldri
    # en gang til her. metno_korrigert (reserven sin reserve) har ingen
    # retningsfaktor i h i det hele tatt, og dempes derfor alltid med dir_hit.
    #
    # 27.09.2026, funnet av fysikk-kontrollør ved gjennomgang av tredje runde:
    # exposure_override (manuelt, kalibrert tak - se exposure_override_cap())
    # er allerede den endelige, menneskelig satte "sannheten" om hvor mye som
    # når spoten fra en retning - typisk satt NETTOPP for grader der rå
    # eksponering er 0 og geometrien ikke kan stoles på (Grøtfjord 317-330,
    # se spots.json). Den ekstra diffraksjons-dempingen over ville da dempet
    # samme retning to ganger (capet i h, OG en gang til her) - dropper derfor
    # den ekstra dempingen når en override dekker retningen.
    #
    # 07.10.2026, Theodors rettelse (Grøtfjord om ca. 10 dager, 2,3 m/15 s
    # fra 271°): dempingen skal avhenge av perioden - langt svell bøyer seg
    # bedre rundt land. Samme p(T)-kurve som skjermingen i oppgave I: full
    # demping ved 8 s eller kortere, 60 % av dempingen ved 14 s eller lengre,
    # lineært imellom (diffraction_period_weight()). Dempingsfaktoren blir
    # 1 - (1 - dir_hit) × p(T): ved 8 s som før (dir_hit), ved 14 s mildere.
    if source == "svell_ute":
        dir_off = hour.get("dir_offshore")
        needs_extra_damping = (raw_exposure_zero(dir_off, spot)
                                and exposure_override_cap(dir_off, spot) is None)
        hb_damping = diffraction_damping(dir_hit, period) if needs_extra_damping else 1.0
    elif source == "barentswatch":
        hb_damping = 1.0
    else:
        hb_damping = dir_hit
    hb = None if hb_raw is None else hb_raw * hb_damping
    surf_factor = spot.get("surf_factor", SURF_FACTOR_DEFAULT)
    surf_height = 0.0 if low_hs else (None if hb is None else hb * surf_factor)
    surf_height_sets = None if surf_height is None else surf_height * SURF_SETS_FACTOR

    hs = height_score(surf_height, spot)
    ps = period_score(period)
    ds = direction_score(hour.get("dir_offshore"), spot, source)
    score = hs * ps * ds
    potential = int(5 * score + 1e-9)  # rund ned

    deg_out = degrees_outside(hour.get("dir_offshore"), spot)
    # Ærlighet: uten BarentsWatch, med dreining eller utenfor vinduet vet vi
    # mindre. Maks 3 stjerner. Svell godt innenfor vinduet, nær kanten, gjør
    # IKKE varselet usikkert i seg selv. For BarentsWatch: usikkert bare hvis
    # vi IKKE har retning ved punktet (spot_direction_factor er da et
    # nøytralt anslag, 1,0, ikke et ekte "treffer rett inn"). 27.09.2026,
    # andre runde: bølger som går ut fra land (>150 grader fra facing) er en
    # KJENT retning, ikke ukjent - gir ekte straff (faktor 0) via h over, men
    # gjør IKKE timen usikker i seg selv, på samme måte som en helt vanlig
    # dårlig retning (60-150 grader) heller ikke gjør det.
    uncertain = (
        (source != "barentswatch" and ((hour.get("turn") or 0) >= 10 or (deg_out or 0) > 0))
        or (source == "barentswatch" and bw_detail is not None
            and not bw_detail["spot_direction_known"])
        # 06.10.2026, Theodors rettelse (manglende svelldata, se CLAUDE.md):
        # ingen kilde hadde et ekte, utskilt svellfelt for timen - svellet
        # ute er et forsiktig anslag fra totalhøyden (se fetch.build_spot()
        # og sources.openmeteo_marine()), ikke en ekte måling. Gjør timen
        # usikker uansett kilde (vanligvis svell_ute/langtid, men prinsippet
        # er generelt).
        or hour.get("swell_model") == "total_fallback"
    )
    # Kildene uenige: BarentsWatch viser en reell totalhøyde (0,5 m+), men
    # svellet ute er dårlig eksponert mot spoten, mest av totalhøyden er
    # vindsjø, eller
    # bølgene ved BarentsWatch-punktet går ikke inn mot stranda. Strengere
    # enn den vanlige usikkerhets-kappingen (maks 1, ikke 3) - dette er ikke
    # bare mangel på data, men tegn på at det trolig ikke er surfbart.
    # 27.09.2026, andre runde: retningsleddet skal IKKE utløse dette alene når
    # bølgene går helt ut fra land (>150 grader) - h er da uansett nesten 0
    # (spot_direction_factor 0 demper høyden selv), og "kildene uenige" sin
    # strenge 1-stjerne-kapping er ment for tvetydige, ikke entydig flate,
    # timer.
    # 30.09.2026, Unstad 28.09.2026 ("Safe to say it's firing" - se STATUS.md):
    # dårlig eksponering ute (dir_hit) skal heller ikke ALENE utløse "kildene
    # uenige" når BarentsWatch ved SPOTEN selv bekrefter treff (bw_confirms,
    # se barentswatch_height()) - svellretningen ute (GFS) kan bomme 10-20
    # grader, BarentsWatch sin kystmodell ved punktet vinner når de er uenige.
    sources_disagree = (
        source == "barentswatch" and bw_detail is not None
        and (hour.get("bw_height") or 0) >= 0.5
        and ((dir_hit < SPOT_DIRECTION_OVERRIDE_EXPOSURE and not bw_detail.get("bw_confirms"))
             or bw_detail["swell_share"] < 0.5
             or (bw_detail["spot_direction_factor"] < 0.5 and not bw_detail["spot_direction_offshore"]))
    )
    if sources_disagree:
        uncertain = True

    capped_from = potential if (uncertain and not sources_disagree and potential > 3) else None
    disagree_cap = potential if (sources_disagree and potential > 1) else None
    if sources_disagree:
        potential = min(potential, 1)
    elif uncertain:
        potential = min(potential, 3)

    # 06.10.2026, Theodors oppgave (Magnus, lokal surfer - se CLAUDE.md sin
    # "Lokalkunnskap"): bølgeenergi i kJ, og energifaktoren - FØR vind og
    # tidevann, se energy_factor(). energy_swell (EKTE svell ute, ikke
    # totalhøyden - samme mål som surf-forecast og Magnus bruker) er leddet
    # regelen (standard eller Magnus sin) faktisk gjelder mot (se
    # energy_kj()). energy_total (totalhøyde, inkluderer vindsjø) vises også
    # (energy_total_kj, til "Svell ute"-cella når svell_offshore mangler),
    # men brukes ALDRI i selve regelen - vindsjø er ikke organisert
    # svellenergi, og ville latt en vindsjø-dominert time telle som mye
    # energi den ikke har.
    #
    # 06.10.2026, Theodors rettelse (andre runde, fant av fysikk-kontrollør
    # sin indirekte avsløring via Unstad - se STATUS.md): regelen leste
    # FEILAKTIG energy_total her, ikke energy_swell, helt siden oppgave A
    # (dette feltet het da bare "energy_total", og var det eneste tallet
    # Farstadsanden sine kontrollverdier ble sjekket mot - men Farstadsanden
    # har typisk lav vindsjø-andel, så feilen var usynlig der). Unstad (høy
    # periode, stor vindsjø-andel i enkelte timer) gjorde feilen synlig:
    # 26.09.2026 sin ekte observasjon ("over hodet", 4 stjerner) har
    # svell_offshore 3,48 m/15 s (ca. 5300 kJ, full faktor) men
    # height_offshore langt høyere i den gamle, upresise testfixturen - ga
    # feilaktig lav faktor (0,65) og falt 2 stjerner, over Theodors egen
    # 1-stjernes toleranse. energifaktoren er nå UNIVERSELL (alle spots,
    # ikke bare Farstadsanden) - se energy_factor() sine standardgrenser.
    energy_swell = energy_kj(hour.get("swell_offshore"), period)
    energy_total = energy_kj(hour.get("height_offshore"), period)
    energy_factor_value = energy_factor(spot, energy_swell)
    if energy_factor_value < 0.999:
        potential = int(potential * energy_factor_value + 1e-9)

    wind_speed, wind_dir, gust = hour.get("wind_speed"), hour.get("wind_dir"), hour.get("gust")
    wt = wind_type(wind_dir, spot)
    wp = wind_penalty(wind_speed, wind_dir, spot, gust)
    lost_wind = min(potential, wp)
    tide_pen = tide_penalty(hour.get("tide"), spot)
    lost_tide = min(potential - lost_wind, tide_pen)
    solid = potential - lost_wind - lost_tide

    local_extra_stars, local_rules_lines = local_rules_penalty(hour, spot, wt, wind_speed)
    if local_extra_stars:
        solid = max(0, solid - local_extra_stars)
    local_rules_source = None
    if spot.get("local_rules"):
        src = spot["local_rules"].get("source", "")
        local_rules_source = src.split(",")[0].strip() if src else None

    low_reason = classify_low_rating(hour, spot, source, bw_detail, low_hs, surf_height, dir_hit,
                                      potential, lost_wind, lost_tide, solid, blown_out, energy_swell)

    breakdown = build_breakdown(
        hour, spot, h, source, bw_detail, hb, surf_factor, surf_height,
        surf_height_sets, low_hs, blown_out, hb_damping, period, hs, ps, dir_hit,
        wind_speed, wind_dir, gust, wt, wp, hour.get("tide"), tide_pen,
        potential, solid, lost_wind, lost_tide, uncertain,
        sources_disagree, capped_from, disagree_cap, energy_swell, energy_factor_value,
    )

    return {
        "stars": solid,
        "faded": lost_wind + lost_tide,
        "faded_wind": lost_wind,
        "faded_tide": lost_tide,
        "wind_type": wt,
        "height": None if h is None else round(h, 2),
        "height_source": source,
        # Surfehøyde (der bølgene brekker) og settene - se breaking_height().
        # Dette er tallet som vises og som logges/kalibreres mot (surf_factor),
        # IKKE "height" over, som fortsatt er Hs (signifikant høyde ute).
        "surf_height": None if surf_height is None else round(surf_height, 2),
        "surf_height_sets": None if surf_height_sets is None else round(surf_height_sets, 2),
        "breaking_height": None if hb is None else round(hb, 2),
        "surf_factor": round(surf_factor, 3),
        "transfer": spot.get("transfer", DEFAULT_TRANSFER),
        "uncertain": uncertain,
        "breakdown": breakdown,
        # Hvor stor andel av svellet ved direkte treff som når spoten akkurat
        # nå. Brukes til å justere selve høyden (for svell_ute), og vises i
        # appen som "retningstreff".
        "directness": round(dir_hit, 3),
        # Kildene (BarentsWatch-totalhøyde vs. ekte svell og retning ved
        # spoten) er uenige - trolig ikke surfbart selv om høyden ser grei
        # ut. Se disagree_reason() for hvorfor. Varsles ALDRI (notify.py).
        "sources_disagree": sources_disagree,
        "sources_disagree_reason": disagree_reason(hour, dir_hit, bw_detail) if sources_disagree else None,
        "swell_share": round(bw_detail["swell_share"], 3) if bw_detail else None,
        "spot_direction_factor": round(bw_detail["spot_direction_factor"], 3) if bw_detail else None,
        # Gradavviket bak spot_direction_factor - til visning ("70 grader
        # skrått på stranda"). None hvis retning eller facing er ukjent.
        "spot_direction_diff": (round(bw_detail["spot_direction_diff"])
                                 if bw_detail and bw_detail["spot_direction_diff"] is not None else None),
        # Bølgene ved BarentsWatch-punktet går faktisk ut fra land (avvik over
        # SPOT_DIRECTION_ERROR_DEG fra facing - trolig vindsjø fra land, ikke
        # svell inn). Brukes i fetch.py sin spotnivå-sikring mot at
        # retningskonvensjonen skulle bli feil igjen.
        "spot_direction_offshore": bool(bw_detail and bw_detail["spot_direction_offshore"]),
        # 27.09.2026, Theodors rettelse: sann når retningsfaktoren ved
        # BarentsWatch-punktet ble overstyrt til 1,0 fordi svellet ute
        # allerede har god eksponering (se barentswatch_height()).
        "spot_direction_overridden": bool(bw_detail and bw_detail.get("spot_direction_overridden")),
        # 30.09.2026, Theodors rettelse (Unstad 28.09.2026): sann når
        # BarentsWatch ved SPOTEN selv bekrefter treff (retning innenfor
        # BW_CONFIRM_DIFF_DEG av facing OG høyde uten retningsfaktor over
        # FLAT_HS_THRESHOLD) - se barentswatch_height(). Overstyrer både
        # retningsfaktoren og sources_disagree sitt eksponeringsledd.
        "bw_confirms": bool(bw_detail and bw_detail.get("bw_confirms")),
        # Trolig flatt: enten er signifikant høyde reelt lav (surf_height er
        # da tvunget til 0, uansett hva formelen ellers ville gitt), eller
        # reserven (metno_korrigert) har stor dreining/retning langt utenfor
        # vinduet - den kilden tar ikke selv hensyn til noen av delene.
        "likely_flat": low_hs or (
            source == "metno_korrigert" and (
                (hour.get("turn") is not None and hour["turn"] > 25)
                or (deg_out is not None and deg_out > 20)
            )
        ),
        # 27.09.2026: blåst ut - IKKE lite energi (BarentsWatch måler en reell
        # totalhøyde), men lav svellandel og/eller sterk onshore/side-onshore
        # vind, se is_blown_out(). Appen bør vise "Blåst ut" og
        # BarentsWatch-totalhøyden i stedet for "Trolig flatt"/0,0 m for disse
        # timene - stjernene er fortsatt 0 (low_hs gjelder uansett).
        "blown_out": blown_out,
        # 05.10.2026 (Theodors rettelse, Grøtfjord kl. 11-17 - se STATUS.md):
        # EN av "flat", "blown_out", "stormsjo", "treffer_ikke", eller None -
        # se classify_low_rating(). Bare satt for 0 og 1 stjerne. Appen skal
        # bruke DETTE feltet overalt (detaljside, liste, dagbrikker, kartets
        # høydeplate) i stedet for å gjette fra stjernetallet alene -
        # likely_flat/blown_out over beholdes uendret (egen, mer snever
        # betydning de alt var i bruk for), ikke erstattet av dette.
        "low_reason": low_reason,
        # 06.10.2026, Theodors oppgave: bølgeenergi i kJ, se energy_kj().
        # energy_swell er fra ekte svell (swell_offshore) - det de myke
        # lokale reglene under bruker. energy_total er fra totalhøyde ute
        # (height_offshore) - trolig det yr/surf-forecast selv viser, vist
        # ved siden av, ikke brukt i reglene.
        "energy_swell_kj": None if energy_swell is None else round(energy_swell),
        "energy_total_kj": None if energy_total is None else round(energy_total),
        # Myke lokale regler (Magnus, se CLAUDE.md "Lokalkunnskap") - None
        # når spoten ikke har local_rules. "stars_lost" er ETT tall (allerede
        # avrundet, summert på tvers av tidevann/vind-delreglene) - energi
        # sin effekt er IKKE i dette tallet (den ganger potensialet NED før
        # vind/tidevann i det hele tatt, se energy_factor() - det er ikke et
        # eget stjerne-fradrag å telle opp samme måte, og vises nå som egen
        # linje i den vanlige breakdown over i stedet for her, siden
        # energifaktoren er universell og ikke lenger Farstadsanden-only).
        "local_rules": None if not spot.get("local_rules") else {
            "source": local_rules_source,
            "stars_lost": local_extra_stars,
            "lines": local_rules_lines,
        },
    }
