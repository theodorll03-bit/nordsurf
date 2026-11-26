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


# 16.10.2026 (Theodor, Grøtfjord lørdag 17.10, punkt 3a): myk kant på exposure_override-taket. I stedet for å
# hoppe fra 1 til taket på én grad ved sonens kant, går taket lineært fra 1 ved kanten ned til fullt tak
# OVERRIDE_TAPER_DEG grader INN i sonen (dypere inne gjelder taket uendret - hullet beholdes). Fysisk: modellens
# svellretning er et middel over en retningsspredning på typisk ±15-30°, så en time «2° inne i sonen» har mye av
# energien fra retninger utenfor den - en bratt kant er falsk presisjon. Utenfor sonen (f.eks. inne i
# svellvinduet) endres ingenting. Open-Meteo gir ingen retningsspredning per time, så bredden er et fast anslag.
# Den geometriske kurven gjelder fortsatt (min av de to), så kanten mot skygge utenfor vinduet blir ikke mildere
# enn geometrien. 0 = av (gammel, bratt kant). Krever Theodors ja (exposure_override står på lista).
# AV (0) 16.10.2026: med 12 bryter den en fast observasjon - Grøtfjord 25.09.2026, 313° (2° inn i 311-330-sonen),
# helt flatt, får 2 stjerner/1,09 m (test_display_only/test_rating). Observasjonen sier at kanten ved 311 ER bratt
# der; se data/backtest/hopp_2026-10-16.md. Beholdt som bryter til backtest og en eventuell sone-for-sone-bruk.
OVERRIDE_TAPER_DEG = 0


def exposure_override_cap_soft(d, spot):
    """Som exposure_override_cap(), men med myk overgang de første OVERRIDE_TAPER_DEG gradene inn i sonen (se over).
    Brukes bare i exposure() - exposure_override_cap() (streng: dekker sonen retningen?) er uendret for
    diffraksjonsdempingen."""
    if d is None:
        return None
    caps = []
    for o in spot.get("exposure_override") or []:
        a, b = o["from"], o["to"]
        if not in_sector(d, [a, b]):
            continue
        depth = min((d - a) % 360, (b - d) % 360)
        frac = 1.0 if OVERRIDE_TAPER_DEG <= 0 else min(1.0, (depth + 1) / OVERRIDE_TAPER_DEG)
        caps.append(o["max"] if frac >= 1.0 else 1.0 - (1.0 - o["max"]) * frac)
    return min(caps) if caps else None


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
    cap = exposure_override_cap_soft(d, spot)
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
    8 s eller kortere er det lik dir_hit (som før 07.10.2026), ved 14 s
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


BW_SWELL_SHARE_MIN = 0.9  # se bw_swell_dominates()
BW_SWELL_PERIOD_MIN_S = 7.0  # se bw_swell_dominates()
# Grensa for «kraftig pålandsvind» (fysikk-kontrollør 17.11.2026): 6,0 m/s
# MIDDELVIND, ikke kast (middelvinden styrer bølgeveksten). Med 20-30 km strøk
# gir 6 m/s ca. 0,5 m med 3 s (fetch-begrenset vekst, SPM/JONSWAP), nok til å
# forklare hele høyden ved fjordpunktene. Grensa er satt med observasjonen i
# tankene: fysisk kan 5-6 m/s forsvares, og 5 bryter observasjonen (varselet
# sa 5,4-5,5 m/s på Breivikeidet 17.11 mens det var vindstille på stranda).
BW_SWELL_STRONG_ONSHORE_MS = 6.0
BW_SWELL_SEAWARD_DEG = 60  # bølgene ved punktet må komme fra havsiden: under 60° fra facing


def bw_swell_dominates(hour, spot):
    """Skal den korte toppperioden ved BarentsWatch-punktet settes til side
    fordi nesten alt ute er svell? 17.11.2026, Theodors regel (observasjon
    17.11.2026, Theodor: Breivikeidet hoftehøyt og rent kl. 08-09Z med
    hodehøye sett ca. kl. 09.30-09.50Z, vindstille; BarentsWatch 0,37-0,43 m
    med 2,4-2,6 s ved punktet, svellandel 93-97 % og svell ute 2,2-2,3 m med
    7,75 s; appen viste 0 poeng og «flatt»).

    EMPIRISK regel, ikke fysikk (fysikk-kontrollør 17.11.2026): toppperioden
    er perioden til den delen av spekteret som har mest energi, så 2,4-2,9 s
    ved punktet ER vindsjø i kystmodellen (bratthet ca. 0,04, og høyden fulgte
    modellvinden). Regelen traff observasjonen fordi modellvinden var feil
    (5,5 m/s i varselet, vindstille på stranda) og laget omtrent like mye sjø
    som det ekte svellet. Den er fysisk riktig der punktet viser 6-7,5 s og
    lav bratthet (ekte svell som den gamle kurven straffet).

    True når ALT dette er kjent og oppfylt:
    - svellandelen ute er BW_SWELL_SHARE_MIN eller mer, og svellet er et ekte
      svellfelt (ikke et anslag fra totalhøyden, swell_model total_fallback),
    - svellperioden ute (hour["period"]) er BW_SWELL_PERIOD_MIN_S eller mer,
    - bølgene ved punktet kommer fra havsiden: bw_dir er under
      BW_SWELL_SEAWARD_DEG fra facing. Sjø fra land eller langs land er laget
      i fjorden bak,
    - vinden på spoten er IKKE kraftig pålands: middelvind under
      BW_SWELL_STRONG_ONSHORE_MS, eller ikke onshore/side-onshore. Kraftig
      pålandsvind lager sin egen sjø ved punktet, og da er den korte
      perioden reell.
    Mangler svellandelen, svellperioden, retningen ved punktet, facing eller
    vindstyrken: False (den vanlige periodefaktoren brukes). Sterk vind med
    ukjent retning: False.

    Erstatter A1 (bw_can_be_windsea(), 16.11.2026: vindretning mot retningen
    ved punktet) og A2 (vindhistorikk, aldri tatt inn).

    Kjente svakheter (fysikk-kontrollør 16.11 og 17.11.2026): bratt sjø ved
    punktet (1,0 m med 3,8 s, bratthet 0,046) får full faktor når svellandelen
    ute er høy og vinden er under grensa. Regelen ser bare vinden i samme time
    og på spoten, ikke gammel vindsjø eller vinden ute i fjorden. Bråkanter:
    ved andel 0,9, periode 7,0 s og vindgrensa hopper faktoren fra 0,3 til
    1,0. Glidende overganger er en oppfølger."""
    share, share_known = swell_share(hour)
    period = hour.get("period")
    if not share_known or share < BW_SWELL_SHARE_MIN:
        return False
    # et anslag fra totalhøyden er ikke en målt svellandel (som i gap_floor())
    if hour.get("swell_model") == "total_fallback":
        return False
    if period is None or period < BW_SWELL_PERIOD_MIN_S:
        return False
    bw_dir, facing = hour.get("bw_dir"), spot.get("facing")
    if bw_dir is None or facing is None or angle_diff(bw_dir, facing) >= BW_SWELL_SEAWARD_DEG:
        return False
    speed = hour.get("wind_speed")
    if speed is None:
        return False
    if speed >= BW_SWELL_STRONG_ONSHORE_MS:
        wt = wind_type(hour.get("wind_dir"), spot)
        if wt is None or wt in ("onshore", "sideonshore"):
            return False
    return True


# ---------- Lang sjø som GFS kaller vindsjø (S29 c del 2, 24.11.2026) - PÅ for Unstad fra S40 ----------
# Slått på 24.11.2026 etter svar.md 24.11.2026 kl. 22.25 (S40: «a, med vilkår»): variant A' («vindu», 7 s ved
# stranda), bare Unstad, etter at M3 og M4 er rettet og appen viser den lange sjøen. Variant B er nei («den løfter
# krapp sjø»). Sier Theodor at han har sett Unstad flat med lang sjø rett fra nord, slås regelen av igjen
# (LONG_SEA_AS_SWELL = False) til den er sett på på nytt. Med False er rate() uendret for alle timer (test 44.1).
# Krever Theodors ja: å endre bryteren, LONG_SEA_SPOTS, variantene eller tallene under.
#
# Observasjon 21.11.2026, Theodor (story fra Lofoten Surfsenter): Unstad «litt under hodehøyt og rent». Appen viste
# 0 poeng og 0,0 m i alle lyse timer. GFS Wave la nordsjøen i VINDSJØ-delen: 2,5-2,9 m fra 357-1 grader med
# 9,7-10,2 s middelperiode, mens svell-delen bare var 0,5-0,6 m fra 250 grader (tallene hentet med ett kall til
# Open-Meteo 24.11.2026). Svellandelen (0,2), energien (under 200 kJ) og «kildene uenige» leser alle den delingen.
#
# HVA REGELEN RETTER (fysikk-kontrolløren 24.11.2026): SVELLANDELEN, ikke svellvinduet. Feilen ligger i
# swell_share(), som bruker GFS sin deling av sjøen ute i svell og vindsjø. Vinduet og geometrien står: Unstad
# ligger fortsatt i skygge for sjø fra nord (eksponering 0,01-0,04 ved 355-0 grader, bak en smal odde 0,4 km
# bred), og det er BarentsWatch sin egen retning ved punktet (312-324 grader) som sier at sjøen bøyer seg inn.
#
# Regelen: når vindsjø-delen ute er LANG og BarentsWatch-punktet viser sjø rett inn, regnes den som svell i
# svellandelen, energien, perioden og retningen (én og samme omregning av timen, brukt i alle ledd -
# fysikk-kontrollørens forslag 22.11.2026: «ett felles vilkår, c utløser og S23-vilkåret bekrefter»). Den er et
# anslag, så timen merkes usikker (høyst 3 poeng). Svellandelen og BarentsWatch-periodefaktoren er to mål på det
# samme spørsmålet (min() i barentswatch_height()), og regelen setter begge til 1,0 - en dobbel oppheving, ikke
# en dobbel telling. Svellandelens nevner byttes samtidig fra met.no sin totalhøyde til GFS sin egen (samme
# modell som delene), ellers ville andelen blitt ca. 0,84 og ikke 1,0 av ren modellforskjell.
LONG_SEA_AS_SWELL = True
# Bare Unstad: den eneste spoten med en observasjon av dette (21.11.2026). None betyr alle kyst-spots - prøvd
# 24.11.2026 på fem lagrede varsler: timer på andre spots (Vikten, Kvalvika, Bøvær, Bunes, Skagsanden, Persfjord,
# Grøtfjord) flyttet seg 2 poeng eller mer uten noen observasjon. Se STATUS.md.
LONG_SEA_SPOTS = frozenset({"unstad"})
# Middelperioden (Tm) til vindsjø-delen ute. GFS har ikke toppperiode for den delen. 9 s middelperiode svarer til
# ca. 11-12 s toppperiode, og fullt utviklet sjø med så lang middelperiode krever ca. 16-18 m/s.
LONG_SEA_MIN_PERIOD_S = 9.0
# Bølgealder mot vinden PÅ SPOTEN: fasefarten (1,56 × T) minst 1,2 × middelvinden. ÆRLIG OM HVA DEN ER
# (fysikk-kontrolløren 24.11.2026): dette skiller IKKE dønning fra vindsjø. Vinden er vinden på stranda, ikke
# vinden ute der sjøen ble laget, og GFS kalte sjøen vindsjø nettopp fordi vinden ute fortsatt drev den (ved
# 10,1 s minst ca. 9,3 m/s langs bølgeretningen). 21.-22.11.2026 var dette trolig moden nordsjø, ikke gammel
# dønning. Vilkåret stopper sjelden noe (1,2: 40 timer, 1,5: 35, 1,7: 23 i variant B). Det er bare en svak
# sperre mot storm på stedet: 9 s sjø slipper gjennom opp til 11,7 m/s, 10 s opp til 13 m/s.
LONG_SEA_WAVE_AGE = 1.2
LONG_SEA_PHASE_SPEED_PER_S = 9.81 / (2 * math.pi)   # m/s per sekund periode (dypt vann)
# Høyst 30 grader utenfor svellvinduet (der SHADOW_CURVE går til 0). Tilpasset hendelsen: sjøen kom 22-26 grader
# utenfor Unstads vindu, og med 20 slår regelen aldri til. Grensa gjør lite arbeid som vindu - det er
# BarentsWatch-retningen ved punktet som bærer retningen. Den stopper sjø fra land og langs land.
LONG_SEA_WINDOW_MARGIN_DEG = 30
# Bekreftelsen ved punktet: bølgene kommer inn innen BW_CONFIRM_DIFF_DEG (30 grader) av facing, som bw_confirms,
# og toppperioden ved punktet er minst LONG_SEA_BW_PERIOD_MIN_S. Hvor perioden leses, er de tre variantene:
#   "vindu" (A', grunnvalget, fysikk-kontrollørens forslag 24.11.2026): i minst én EKTE modelltime innen ±3 timer
#           (bw_period_real_max_3h, regnet i henteren av sources.bw_real_period_max()).
#   "time"  (A): i selve timen, også når tallet er interpolert.
#   None    (B): ingen periodegrense ved punktet.
# Grunnen til A': BarentsWatch-punktet ved Unstad ga 21.11.2026 toppperiode 4,3, 9,4, 4,3, 8,5 og 4,3 s i fem
# modelltimer på rad (hver tredje time) i den samme sjøen. Det er et tosidig spekter der to systemer er omtrent
# like store, og toppen velger det ene. 4,3 s betyr ikke at den lange sjøen mangler. A bruker øyeblikksverdien,
# også interpolerte 7,7 s som ikke finnes i noe spekter, og slår av og på (3, 0, 3 poeng). B ser helt bort fra
# det eneste beviset fra selve spoten, og løfter timer der punktet bare ser 4-5 s krapp sjø hele døgnet.
# Svakheten i alle tre (H i surfehøyde-formelen var HELE BarentsWatch-høyden ved punktet, også den lokale sjøen,
# koblet med den lange sjøens periode) er rettet for timer med kort topp, se LONG_SEA_SHORT_PEAK_ENERGY_SHARE.
# I timer med lang topp ved punktet er høyden fortsatt hele Hs der, og den kan inneholde noe lokal sjø.
LONG_SEA_BW_CONFIRM = "vindu"
LONG_SEA_BW_PERIOD_MIN_S = 7.0
# M4 (fysikk-kontrolløren 24.11.2026, rettet etter svar.md 24.11.2026 kl. 22.25, S40): i en time der toppperioden ved
# punktet I SELVE TIMEN er under LONG_SEA_BW_PERIOD_MIN_S (eller mangler), er den lange sjøen ikke det største
# systemet ved punktet. Toppen i et tosidig spekter står på systemet med høyest energitetthet, og vindsjø er
# bredere i frekvens enn dønning, så med kort topp har den korte sjøen minst like mye energi som den lange. Den
# lange sjøen er da HØYST halve energien ved punktet: H = Hs / √2. Det er en øvre grense, ikke et anslag på
# midten. Faktoren brukes på høyden ved punktet (plassen til periodefaktoren i barentswatch_height()), så
# surfehøyde-formelen får den lange sjøens andel av høyden sammen med den lange sjøens periode, ikke hele høyden.
# Perioden i formelen er fortsatt sjøens periode ute (CLAUDE.md «Konvensjoner»). Flat-sperren (0,35 m) gjelder
# den reduserte høyden: under ca. 0,50 m ved punktet med kort topp gir regelen ingenting.
# Timer der toppen ved punktet er minst 7 s i selve timen (også interpolert), får hele høyden som før.
LONG_SEA_SHORT_PEAK_ENERGY_SHARE = 0.5


def long_sea(hour, spot):
    """S29 c del 2 (på for Unstad fra S40): er GFS sin vindsjø-del ute egentlig lang sjø fra havsiden som skal regnes som
    svell? Returnerer None (nei, eller noe mangler) eller en dict med den omregnede timen:
    {"swell_offshore", "height_offshore", "period", "dir_offshore", "swell_peak_period", "_long_sea"}.

    ALT dette må være kjent og oppfylt (mangler noe: None, regelen gjør aldri noe på manglende data):
    1. Bryteren LONG_SEA_AS_SWELL er på, og spoten er med (LONG_SEA_SPOTS).
    2. Spoten er en kyst-spot med BarentsWatch-tall i timen. Fjord-spots regner høyden fra en låst andel, og
       reserven (dag 3 og utover) har ingen kystmodell som kan bekrefte.
    3. Svellet ute er et ekte GFS-felt (swell_model "gfs"): vindsjø-delen og svell-delen er da samme modell.
    4. Vindsjø-delen ute er lang: middelperiode minst LONG_SEA_MIN_PERIOD_S.
    5. Fasefarten (1,56 × perioden) er minst LONG_SEA_WAVE_AGE × middelvinden på spoten. Bare en svak sperre
       mot storm på stedet, ikke et skille mellom dønning og vindsjø (se LONG_SEA_WAVE_AGE). Ukjent vind: None.
    6. Den kommer fra havsiden: retningen er i svellvinduet eller høyst LONG_SEA_WINDOW_MARGIN_DEG utenfor, den
       treffer ikke en nær og bred hindring (blocked_by_near_obstacle(), Nordneset ved Farstadsanden), og ingen
       exposure_override dekker retningen (Lenangsøyra 225-320, Grøtfjord: der har Theodor satt taket selv).
    7. BarentsWatch-punktet bekrefter: bølgene kommer inn innen BW_CONFIRM_DIFF_DEG av facing, og toppperioden
       ved punktet er minst LONG_SEA_BW_PERIOD_MIN_S - i en ekte modelltime innen ±3 timer (A', grunnvalget), i
       selve timen (A) eller uten periodekrav (B), se LONG_SEA_BW_CONFIRM. Mangler perioden: None.

    8. (M3, S40) Svellet i timen er GFS sitt eget tall for timen: en time der despike_swell() har byttet svellet
       mot snittet av nabotimene (swell_despiked) er aldri med. Der har GFS flyttet sjøen mellom svell og vindsjø
       i én time, og nabosnittet lagt sammen med timens rå vindsjø-del ville telt den samme sjøen to ganger.
       Og totalhøyden ute må være GFS sin egen (total_model «gfs»), ellers None.

    Regelen retter svellandelen, ikke svellvinduet: geometrien og vinduet er uendret.

    Når regelen slår til, brukes BarentsWatch-høyden uten periodefaktoren når toppen ved punktet er lang i selve
    timen, og med LONG_SEA_SHORT_PEAK_ENERGY_SHARE når den er kort (M4, se bw_period_factor_for()).

    Omregningen: høyden er svell og lang sjø lagt sammen som energi (kvadratrot av kvadratsummen), men aldri
    mer enn GFS sin egen totalhøyde i timen (M3: delene kan ikke være mer enn helheten). Periode og retning er
    fra den største av de to (samme modell, CLAUDE.md «Konvensjoner»). Totalhøyden er GFS sin egen (samme modell
    som delene). Toppperioden mangler (GFS har den aldri)."""
    if not LONG_SEA_AS_SWELL or spot is None:
        return None
    if LONG_SEA_SPOTS is not None and spot.get("id") not in LONG_SEA_SPOTS:
        return None
    if is_fjord(spot) or hour.get("bw_height") is None or hour.get("swell_model") != "gfs":
        return None
    # M3: svellet i timen er glattet (nabosnitt), vindsjø-delen er timens rå tall - de hører ikke sammen
    if hour.get("swell_despiked"):
        return None
    total = hour.get("total_height_offshore")
    if total is None or total <= 0 or hour.get("total_model") != "gfs":
        return None
    ww_h, ww_t, ww_d = (hour.get("wind_wave_height_offshore"), hour.get("wind_wave_period_offshore"),
                        hour.get("wind_wave_dir_offshore"))
    sw_h, sw_t, sw_d = hour.get("swell_offshore"), hour.get("period"), hour.get("dir_offshore")
    if ww_h is None or ww_t is None or ww_d is None or ww_h <= 0 or sw_h is None:
        return None
    if ww_t < LONG_SEA_MIN_PERIOD_S:
        return None
    wind = hour.get("wind_speed")
    if wind is None or LONG_SEA_PHASE_SPEED_PER_S * ww_t < LONG_SEA_WAVE_AGE * wind:
        return None
    out = degrees_outside(ww_d, spot)
    if out is None or out > LONG_SEA_WINDOW_MARGIN_DEG:
        return None
    if blocked_by_near_obstacle(ww_d, spot) or exposure_override_cap(ww_d, spot) is not None:
        return None
    bw_p, bw_d, facing = hour.get("bw_period"), hour.get("bw_dir"), spot.get("facing")
    if bw_d is None or facing is None or angle_diff(bw_d, facing) > BW_CONFIRM_DIFF_DEG:
        return None
    if LONG_SEA_BW_CONFIRM is not None:
        confirm_p = hour.get("bw_period_real_max_3h") if LONG_SEA_BW_CONFIRM == "vindu" else bw_p
        if confirm_p is None or confirm_p < LONG_SEA_BW_PERIOD_MIN_S:
            return None
    combined = min(math.sqrt(sw_h ** 2 + ww_h ** 2), total)   # M3: aldri mer enn GFS sin egen totalhøyde
    main_is_long_sea = ww_h >= sw_h or sw_t is None or sw_d is None
    return {
        "swell_offshore": combined,
        "height_offshore": total,
        "period": ww_t if main_is_long_sea else sw_t,
        "dir_offshore": ww_d if main_is_long_sea else sw_d,
        "swell_peak_period": None if main_is_long_sea else hour.get("swell_peak_period"),
        "_long_sea": True,
    }


def bw_period_factor_for(hour, spot):
    """Periodefaktoren slik barentswatch_height() bruker den, og hvilken
    periode den bygger på: "bw" (BarentsWatch sin toppperiode), "ute"
    (BarentsWatch-perioden er kort, men satt til side fordi svellet
    dominerer, se bw_swell_dominates()) eller None når BarentsWatch-perioden
    mangler. Regelen kan bare ta bort en vindsjø-straff, aldri legge til en.
    Største løft: 0,3 til 1,0."""
    # S29 c del 2 (S40: på for Unstad): lang sjø fra havsiden (long_sea()). Kurven under er laget for å ta ned vindsjø
    # (0,3 under 6 s, 0,45-0,6 for 7-8 s), og her er sjøen ute 9 s eller mer. Står foran «mangler periode»: i
    # variant A' og B kan regelen slå til uten toppperiode ved punktet i selve timen.
    # M4 (S40): er toppen ved punktet kort i selve timen (eller mangler den), er den lange sjøen høyst halve
    # energien der - se LONG_SEA_SHORT_PEAK_ENERGY_SHARE.
    if hour.get("_long_sea"):
        bw_p = hour.get("bw_period")
        if bw_p is None or bw_p < LONG_SEA_BW_PERIOD_MIN_S:
            return math.sqrt(LONG_SEA_SHORT_PEAK_ENERGY_SHARE), "lang_sjo_kort_topp"
        return 1.0, "lang_sjo"
    bw_period = hour.get("bw_period")
    pf = bw_period_factor(bw_period)
    if bw_period is None:
        return pf, None
    if pf < 1.0 and bw_swell_dominates(hour, spot):
        return 1.0, "ute"
    return pf, "bw"


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
    pf, pf_basis = bw_period_factor_for(hour, spot)
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
        # "ute" når en kort BarentsWatch-periode er satt til side fordi svellet
        # dominerer (se bw_swell_dominates()).
        "bw_period_basis": pf_basis,
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


GAP_MIN_PERIOD_S = 7.0  # se gap_floor()
GAP_EDGE_DEG = 2  # se gap_floor(): slingring utenfor kanten av det tegnede vinduet


def gap_swell_in_window(hour, spot):
    """Sann når spoten er en gap-spot (gap_spot, swell_window_tegnet og låst
    gap_transfer) og det ekte svellfeltet ute kommer fra det tegnede vinduet,
    eller høyst GAP_EDGE_DEG utenfor kanten. Mangler noe: False. Brukes av
    gap_floor() og av unntaket i rate() sin sources_disagree."""
    if not spot or not spot.get("gap_spot"):
        return False
    tegnet, d = spot.get("swell_window_tegnet"), hour.get("dir_offshore")
    if not tegnet or spot.get("gap_transfer") is None or d is None or hour.get("swell_offshore") is None:
        return False
    if hour.get("swell_model") == "total_fallback":
        return False
    sectors = tegnet if isinstance(tegnet[0], list) else [tegnet]
    return min(distance_to_sector(d, sec) for sec in sectors) <= GAP_EDGE_DEG


def gap_edge_factor(hour, spot):
    """Hvor mye av gap-andelen som gjelder for denne svellretningen. 1,0 for
    gap-spots uten "gap_soft_edge" (Russelv: hele andelen i hele det tegnede
    vinduet, uendret).

    22.11.2026 (svar.md 22.11.2026 kl. 12.20, S19: «Vinduet blir ca. 345–30°
    med myk kant»; kilder: observasjon 17.11.2026 og 22.11.2026, Theodor): for
    en spot merket "gap_soft_edge" glir andelen fra 0,667 på kanten av det
    tegnede vinduet til 1,0 fem grader innenfor, og faller videre utenfor.
    Det er samme kurve som directness() bruker for svellvinduet, lest mot det
    TEGNEDE vinduet. Kall bare når gap_swell_in_window() er sann.

    23.11.2026 (svar.md 23.11.2026 kl. 11.20, S27; kilder: observasjon
    17.11.2026 og 22.11.2026, Theodor): en spot kan sette "gap_edge_taper"
    [fra første kant, fra andre kant] i grader. Inne i vinduet går andelen da
    fra 0,667 på hver kant opp til 1,0 så mange grader inn, hver side for seg.
    Uten feltet er begge 5 grader (EDGE_TAPER), og tallet er det samme som
    før. Utenfor vinduet (høyst GAP_EDGE_DEG) gjelder skyggekurven som før.
    Breivikeidet: [20, 5]. Svell fra 17° (langs fjordaksen) ga hoftehøyt
    17.11, mens større svell fra 350° ga litt mindre 22.11."""
    if not spot.get("gap_soft_edge"):
        return 1.0
    d, tegnet = hour["dir_offshore"], {"swell_window": spot["swell_window_tegnet"]}
    taper = spot.get("gap_edge_taper")
    if not taper or degrees_outside(d, tegnet) > 0:
        return directness(d, tegnet)
    start, end = next(sec for sec in window_sectors(tegnet) if in_sector(d, sec))
    edge = SHADOW_CURVE[0][1]
    return min(1.0, *(edge + (1.0 - edge) * angle_diff(d, kant) / bredde
                      for kant, bredde in ((start, taper[0]), (end, taper[1]))))


def gap_share(hour, spot):
    """Andelen av svellet ute som når en gap-spot for denne svellretningen:
    gap_transfer × gap_edge_factor(). Kall bare når gap_swell_in_window() er sann.

    24.11.2026 (svar.md 24.11.2026 kl. 10.25, S36 b): en spot kan sette
    "gap_min_share" {"window": [fra, til], "share": tall}. Kommer svellet ute
    fra det vinduet, eller høyst GAP_EDGE_DEG utenfor kanten, er andelen aldri
    lavere enn "share" (hard kant: hele tallet i hele vinduet). Andelen er da
    den største av de to. Bare Russelv har feltet: 0,20 i 348-19, det som
    gjaldt 16.-23.11.2026, så ANDELEN i 346-21° ikke er lavere enn den var før
    S34 a. Det er ikke et gulv for høyden utenfor 346-21°: i BarentsWatch-sonen
    ved 343-345° og 22-32° bruker fjord-regelen andelshøyden der Russelv før
    S34 a var en kyst-spot med BarentsWatch-tallet, og høyden kan være lavere
    (fysikk-kontrolløren 24.11.2026, lagt fram som S39). Uten feltet er
    tallet som før."""
    andel = spot["gap_transfer"] * gap_edge_factor(hour, spot)
    minst = spot.get("gap_min_share")
    if minst and distance_to_sector(hour["dir_offshore"], minst["window"]) <= GAP_EDGE_DEG:
        andel = max(andel, minst["share"])
    return andel


def gap_floor_height(hour, spot):
    """Høyden gap-grensa gir uten å se på vinden: svell ute × gap_share()
    (gap_transfer × gap_edge_factor(), og aldri under gap_min_share når spoten
    har det). Kall bare når gap_swell_in_window() er sann."""
    return hour["swell_offshore"] * gap_share(hour, spot)


def gap_blocked_by_wind(hour, spot):
    """Sann når gap-grensa ellers ville gjeldt (svell i det tegnede vinduet,
    perioden ute minst GAP_MIN_PERIOD_S), men vinden tar den bort: kjent
    styrke fra BLOWN_OUT_WIND_MS, og retningen er pålands, skrått pålands
    eller ukjent.

    19.11.2026 (fysikk-kontrolløren, forslag til svar.md S22): ukjent
    retning regnes som pålands, samme konvensjon som wind_penalty() og
    bw_swell_dominates(). Før løftet grensa høyden ved 9 m/s og ukjent
    retning, så timen kunne få et poeng mer enn den samme timen med kjent
    pålandsvind. Ukjent styrke gir False (se gap_floor()). Brukes av
    gap_floor() og av classify_low_rating(): en slik time er blåst ut,
    ikke flat."""
    period = hour.get("period")
    if not gap_swell_in_window(hour, spot) or period is None or period < GAP_MIN_PERIOD_S:
        return False
    speed = hour.get("wind_speed")
    return (speed is not None and speed >= blown_out_wind_ms(spot)
            and wind_type(hour.get("wind_dir"), spot) in ("onshore", "sideonshore", None))


def gap_floor(hour, spot):
    """Nedre grense for Hs ved spoten for en gap-spot, eller None.

    16.11.2026, forslag etter observasjon 16.11.2026 (bilde, Russelv) og
    svar.md 16.11.2026 kl. 15.45 (funn punkt 3): Russelv var surfbart med
    rene sett rundt 1 m mens BarentsWatch-punktet viste 0,26 m. Svellet kom
    gjennom gapet Theodor har tegnet (swell_window_tegnet), og kystmodellen
    slapp for lite inn. For spots merket "gap_spot" i spots.json gjelder
    derfor en nedre grense: svell ute ganger gap_transfer (og for spots med
    "gap_soft_edge" ganger gap_edge_factor(), se den). Andelen må stå
    låst i spots.json. Spotens vanlige transfer brukes ALDRI her: fetch.py
    skriver den aktive (standard eller lærte) andelen inn i spot["transfer"],
    og den er som regel mye høyere (standard 0,6) og flytter seg når
    kalibreringen lærer.

    Gjelder bare når ALT dette er kjent og oppfylt (mangler noe: None):
    - spoten er merket gap_spot og har swell_window_tegnet og gap_transfer
    - det finnes et ekte svellfelt ute (ikke anslag fra totalhøyden)
    - svellretningen ute ligger i det tegnede vinduet, eller høyst
      GAP_EDGE_DEG utenfor kanten. Retningen ute kommer i hele grader og
      vipper en grad eller to fra time til time: 16.11.2026 lå den på
      19-20° mens Russelvs vindu slutter på 19°.
    - perioden ute er minst GAP_MIN_PERIOD_S
    - vinden er ikke blåst ut, se gap_blocked_by_wind(): kjent styrke fra
      BLOWN_OUT_WIND_MS, pålands, skrått pålands eller ukjent retning.
      Ukjent STYRKE tar ikke grensa bort: høyden er et mål på svellet, og
      vinden vi mangler koster allerede sitt faste ene poeng i
      wind_penalty(). Uten grensa ville timen falt til 0,0 m og «flatt»
      bare fordi vindvarselet mangler (manglende data er aldri 0).
    Grensa kan bare løfte høyden, aldri senke den (se spot_height())."""
    period = hour.get("period")
    if not gap_swell_in_window(hour, spot) or period is None or period < GAP_MIN_PERIOD_S:
        return None
    if gap_blocked_by_wind(hour, spot):
        return None
    return gap_floor_height(hour, spot)


def gap_floor_applied(hour, spot, h, source):
    """Sann når høyden rate() regner videre med ER gap-grensa (se gap_floor())."""
    if h is None or source not in ("barentswatch", "svell_ute"):
        return False
    floor = gap_floor(hour, spot)
    return floor is not None and abs(h - floor) < 1e-9


# ---------- Tillit til BarentsWatch per spot (bw_tillit) ----------
# 23.11.2026 (svar.md 23.11.2026 kl. 11.25, Theodor; kilder: observasjon 17.11.2026 og 22.11.2026, Theodor):
# «høyden regnes fra svell ute × en andel satt fra observasjoner, med samme gap-grense og myke kant som
# Breivikeidet, også i reservesonen; BarentsWatch brukes bare som tegn på krapp sjø ved punktet».
# bw_tillit er en etikett: "kyst" (standard, alle spots uten feltet, uendret) eller "fjord". En fjord-spot må
# ha feltene en gap-spot har, og en låst andel (transfer_locked, transfer lik gap_transfer). Test 39.1 sjekker det.
# Fjord-reglene gjelder bare når svellet ute kommer fra det tegnede vinduet (høyst GAP_EDGE_DEG utenfor).
# Utenfor er spoten en vanlig kyst-spot.
FJORD_CHOP_MIN_HEIGHT_M = 0.6   # høyde ved BarentsWatch-punktet, se fjord_chop()
FJORD_CHOP_MAX_PERIOD_S = 4.0   # toppperiode ved BarentsWatch-punktet (under), se fjord_chop()


def is_fjord(spot):
    """Sann når spoten er merket bw_tillit "fjord" i spots.json."""
    return bool(spot) and spot.get("bw_tillit") == "fjord"


def fjord_in_window(hour, spot):
    """Sann for en fjord-spot når svellet ute kommer fra det tegnede vinduet (se gap_swell_in_window())."""
    return is_fjord(spot) and gap_swell_in_window(hour, spot)


def fjord_share_height(hour, spot):
    """Andelshøyden for en fjord-spot: svell ute × gap_share() (gap_transfer × gap_edge_factor(), og aldri under
    gap_min_share når spoten har det), når svellet ute kommer fra
    det tegnede vinduet og perioden ute er minst GAP_MIN_PERIOD_S. Ellers None. Vinden ser den ikke på: tar
    vinden grensa bort (gap_blocked_by_wind()), er høyden den samme, og rate() gir 0 poeng (se der).
    BarentsWatch løfter den aldri og senker den aldri (fysikk-kontrolløren 23.11.2026, valg 1 A)."""
    if not fjord_in_window(hour, spot):
        return None
    period = hour.get("period")
    if period is None or period < GAP_MIN_PERIOD_S:
        return None
    return gap_floor_height(hour, spot)


def fjord_share_applied(hour, spot, h, source):
    """Sann når høyden rate() regner videre med ER andelshøyden for en fjord-spot: svell ute × gap_share()
    (gap_transfer × gap_edge_factor(), og aldri under gap_min_share), med svellet ute i det tegnede vinduet. Gjelder også når vinden tar gap-grensa bort
    (gap_floor_applied() er da usann), og i reserven under GAP_MIN_PERIOD_S, der høyden er det samme tallet
    (transfer er lik gap_transfer, test 39.1 krever det). Med BarentsWatch-tall og under GAP_MIN_PERIOD_S
    (eller ukjent periode) gjelder kystmodellen som for en kyst-spot, og svaret er usant."""
    if h is None or source not in ("barentswatch", "svell_ute") or not fjord_in_window(hour, spot):
        return False
    if source == "barentswatch" and fjord_share_height(hour, spot) is None:
        return False
    return abs(h - gap_floor_height(hour, spot)) < 1e-9


def fjord_chop(hour, spot):
    """Krapp sjø ved BarentsWatch-punktet for en fjord-spot: svellet ute er i det tegnede vinduet, og punktet
    viser minst FJORD_CHOP_MIN_HEIGHT_M med toppperiode under FJORD_CHOP_MAX_PERIOD_S. Mangler høyden eller
    perioden: False (manglende data er aldri et tegn). rate() gjør da timen usikker (høyst 3 poeng), ikke mer:
    perioden ved punktet er ikke til å stole på i en fjord (S32 e, svar.md 23.11.2026 kl. 14.00: Breivikeidet
    viste 1,6 s mens 8 s svell kom inn, Russelv 16.11 viste 4,4 s på en god dag). Regelen kan bare senke.
    Grensene (fysikk-kontrolløren 23.11.2026): Breivikeidet 17.11 og 22.11 var rent og surfbart med 0,33-0,49 m
    og 1,6-2,7 s ved punktet. 0,6 m med under 4 s er vindsjø fra ca. 7 m/s over 30 km i JONSWAP. Svakhet: den
    krappe sjøen ved punktet er laget av den samme modellvinden som tok feil 17.11."""
    if not fjord_in_window(hour, spot):
        return False
    bw, p = hour.get("bw_height"), hour.get("bw_period")
    if bw is None or p is None:
        return False
    return bw >= FJORD_CHOP_MIN_HEIGHT_M and p < FJORD_CHOP_MAX_PERIOD_S


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

    For gap-spots (se gap_floor()) løftes 1 og 2 til den nedre grensa når den
    er høyere. Kilden er uendret, og rate() gjør timen usikker.

    For fjord-spots (bw_tillit "fjord") med svellet i det tegnede vinduet og minst GAP_MIN_PERIOD_S er høyden
    andelshøyden i begge soner (fjord_share_height()), også når vinden tar grensa bort. BarentsWatch løfter den
    ikke. Kilden heter fortsatt "barentswatch" der punktet har tall, fordi rate() bruker detaljene derfra.
    """
    floor = gap_floor(hour, spot)
    fjord_h = fjord_share_height(hour, spot)
    if hour.get("bw_height") is not None:
        h, detail = barentswatch_height(hour, spot or {})
        if fjord_h is not None:
            h = fjord_h
        elif floor is not None and floor > h:
            h = floor
        return h, "barentswatch", detail
    transfer = (spot or {}).get("transfer", DEFAULT_TRANSFER)
    if hour.get("swell_offshore") is not None:
        # 23.11.2026 (S27, og bw_tillit samme dag): for en fjord-spot bruker reserven samme retningsfaktor som
        # gap-grensa i det tegnede vinduet, så svell ute × transfer er det samme tallet som grensa når andelene er like
        if fjord_in_window(hour, spot):
            # gap_share() er gap_transfer × kantfaktoren, og aldri under gap_min_share (S36 b). Delt på gap_transfer
            # er det kantfaktoren når spoten ikke har gap_min_share.
            retning = gap_share(hour, spot) / spot["gap_transfer"]
        else:
            retning = exposure(hour.get("dir_offshore"), spot, hour.get("period"))
        h = hour["swell_offshore"] * transfer * retning
        if floor is not None and floor > h:
            h = floor
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

# 07.10.2026, Theodors oppgave (surf-forecast-sammenligning, Farstadsanden
# 15.10 - se STATUS.md): surf-forecast bruker TOPPERIODEN (Tp) i sin egen
# kJ-utregning, ikke middelperioden (Tm) GFS Wave/Open-Meteo sin
# "swell_wave_period" er. Periode i ANDRE potens i energy_kj() (E ∝ T²) gjør
# selv en moderat Tp/Tm-forskjell stor - Theodors eget eksempel (12 s mot
# 16 s) gir (16/12)² ≈ 1,78× i energi av periodevalget ALENE, før selve
# høydeforskjellen. START-faktor, IKKE kalibrert ennå (se energy_period()).
PEAK_PERIOD_FACTOR_DEFAULT = 1.25


def energy_period(period, peak_period):
    """Hvilken periode energy_kj() skal bruke, og hvor den kom fra - ALDRI
    brukt til surfehøyde-formelen (breaking_height()) eller selve
    "Periode"-visningen i appen, som begge fortsatt bruker middelperioden
    (`period`) uendret, slik de alltid har gjort (Theodors eksplisitte
    instruks - bare ENERGIEN skal endres nå).

    1. Topperiode direkte, når kilden faktisk har den (`peak_period`, se
       sources.openmeteo_marine() - i praksis bare noen ganger, når
       standardmodellen er den valgte kilden for timen; GFS Wave har aldri
       dette feltet).
    2. Ellers: middelperioden ganget med PEAK_PERIOD_FACTOR_DEFAULT (1,25,
       en START-verdi - Theodors instruks: kalibrer den mot
       benchmark-sammenligninger fra surf-forecast når det er minst 10 - se
       data/benchmark/).

    Returnerer (periode_til_energi, "topp"/"omregnet"/None) - periode er
    `None` hvis ingen periode i det hele tatt finnes å regne fra."""
    if peak_period is not None and peak_period > 0:
        return peak_period, "topp"
    if period is None or period <= 0:
        return None, None
    return period * PEAK_PERIOD_FACTOR_DEFAULT, "omregnet"


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

# ---------- 5 stjerner («Rått») - Theodor 15.10.2026, fysikk-kontrollørens forslag ----------
# Før: int(5·score) og height_score (1,0 bare nøyaktig midt i ideal_height) gjorde 4 til toppen i
# praksis (0 av 1 600 timer i varselet 15.10). Nå gir formelen ALDRI 5 selv (potential = min(4, …)); den
# femte stjernen gis bare av en bevisst port der ALT er kjent og oppfylt (manglende ≠ oppfylt):
#  A (svellsiden, five_star_swell_gate): dagens regning gir potensial 4, timen er verken usikker
#    eller «kildene uenige»; høyden kommer fra BarentsWatch (kystmodellen, dag 1-3) og bw_confirms;
#    height_score(surf_height) ≥ FIVE_STAR_HS_MIN (0,85 = |h − mid| ≤ 0,375·(hi − lo); 0,9 ville vært
#    «midterste halvdel», men utelukker Farstadsanden 15.10 kl. 17, det eneste observerte 4-5-tilfellet
#    modellen når); middelperioden ute ≥ 13 s; svellenergi kjent, energifaktor full OG ≥ 2 000 kJ
#    (gulv - Unstads lokale full-grense 400 skal ikke definere Rått); svellretning i vinduet med minst
#    min(EDGE_TAPER, bredde/4) margin og eksponering ≥ 0,667; tidevann kjent når spoten har preferanse.
#  B (den femte stjernen er sprø, five_star_losses): vind kjent med straff nøyaktig 0 (generell og
#    lokal) OG offshore eller under FIVE_STAR_CALM_MS effektivt; tidevann uten straff og foretrukket
#    når spoten har preferanse - ellers holdes den femte stjernen tilbake (bokført som tapt på vind/
#    tidevann). Krever Theodors ja (stjernegrenser): Unstad 26.09-rekonstruksjonen (test 16.1, 4
#    observert) oppfylte alle vilkår og fikk 5 fram til 10.11.2026. Med Unstads tidevannsregel
#    (tide_prefer) får den 4 uten kjent tidevann og på høyvann. Se STATUS.md 15.10.2026 og 10.11.2026.
FIVE_STAR_HS_MIN = 0.85
FIVE_STAR_PERIOD_MIN = 13.0   # s, middelperiode ute (hour["period"])
FIVE_STAR_CALM_MS = 3.0       # = wind_label() sin «nesten blankt»-grense
FIVE_STAR_ENERGY_MIN_KJ = 2000.0   # gulv for 5 poeng uansett local_rules (port A, uendret 17.11.2026)


def _tide_prefer(spot):
    return spot.get("tide") or (spot.get("local_rules") or {}).get("tide_prefer")


def five_star_swell_gate(hour, spot, *, source, bw_detail, surf_height, period, energy_swell,
                         energy_factor_value, dir_hit, uncertain, sources_disagree):
    """Del A: svellsiden av 5-stjerners-porten. (åpen, liste over vilkår som feiler)."""
    fails = []
    if source != "barentswatch" or not (bw_detail and bw_detail.get("bw_confirms")):
        fails.append("ikke BarentsWatch-sonen med bekreftet treff")
    if uncertain or sources_disagree:
        fails.append("usikkert varsel")
    if surf_height is None or height_score(surf_height, spot) < FIVE_STAR_HS_MIN:
        fails.append("høyden ikke midt i spotens beste spenn")
    if period is None or period < FIVE_STAR_PERIOD_MIN:
        fails.append("periode under 13 s")
    if energy_swell is None or energy_factor_value < 0.999 or energy_swell < FIVE_STAR_ENERGY_MIN_KJ:
        fails.append("svellenergi ikke over full-grensen")
    d = hour.get("dir_offshore")
    if d is None or degrees_outside(d, spot) > 0:
        fails.append("svell ikke i vinduet")
    else:
        width = next(((end - start) % 360 for start, end in window_sectors(spot) if in_sector(d, [start, end])), 360)
        if degrees_inside(d, spot) < min(EDGE_TAPER, width / 4):
            fails.append("svell i kanten av vinduet")
    if dir_hit is None or dir_hit < SPOT_DIRECTION_OVERRIDE_EXPOSURE:
        fails.append("svellet dårlig eksponert")
    prefer = _tide_prefer(spot)
    if prefer and (hour.get("tide") or {}).get("state") is None:
        fails.append("tidevann ukjent")
    return not fails, fails


def five_star_losses(hour, spot, wind_parts, local_wind_raw, tide_pen, local_tide_raw):
    """Del B: hva som holder den femte stjernen tilbake - «wind», «tide» eller None."""
    if (hour.get("wind_speed") is None or hour.get("wind_dir") is None or wind_parts["pen"] > 0 or local_wind_raw > 0
            or not (wind_parts["kind"] == "offshore" or (wind_parts["eff"] is not None and wind_parts["eff"] < FIVE_STAR_CALM_MS))):
        return "wind"
    prefer = _tide_prefer(spot)
    if tide_pen > 0 or local_tide_raw > 0 or (prefer and (hour.get("tide") or {}).get("state") not in prefer):
        return "tide"
    return None



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


GUST_FACTOR = 0.3        # kastene teller 30 % av forskjellen mellom kast og middelvind ...
GUST_MAX_ADD_MS = 2.0    # ... men kan legge til høyst 2 m/s (Theodor 15.10.2026: 8,7 m/s med kast 15 ble før 10,7 og et helt trinn)


def effective_wind(speed, gust):
    """Når kastene er kraftigere enn middelvinden kjennes det verre enn
    middelvinden alene skulle tilsi. Uten kastdata: bare middelvind.
    15.10.2026 (Theodors regel 3): effektiv vind = middelvind + 0,3 × (kast −
    middelvind), men kastene kan legge til høyst 2 m/s."""
    if speed is None:
        return None
    if gust is not None and gust > speed:
        return speed + min(GUST_MAX_ADD_MS, GUST_FACTOR * (gust - speed))
    return speed


# 15.10.2026, Theodors regel 1 (Farstadsanden «Holy portugal» - se STATUS.md): glatt
# kurve i stedet for trinn (7,9 m/s ga −1, 8,1 m/s ga −2). Effektiv vind (m/s) ->
# straff i stjerner, lineært mellom punktene, 0 under første punkt, flatt etter siste.
# Avrundes IKKE her - først til slutt, sammen med resten av ratingen (rate()).
# 16.11.2026, forslag e (Theodor 16.11.2026: «Se bort ifra vinden, når det er snakk om så lite
# har det jo nesten ingenting å si»): ingen straff under 6 m/s for side og skrått pålands og
# under 5 m/s for pålands. Derfra bygges straffen opp til den møter den gamle kurven: side ved
# 10 m/s, skrått pålands og pålands ved 8 m/s (blåst ut-grensa, BLOWN_OUT_WIND_MS). Over det
# er alt som før. Gamle punkter: side (5,0) (10,1); skrått pålands (3,0) (7,1) (11,2);
# pålands (2,0) (5,1) (8,2).
WIND_PENALTY_CURVES = {
    "offshore": ((10, 0), (14, 1), (18, 2)),
    "side": ((6, 0), (10, 1), (14, 2), (18, 3)),
    "sideonshore": ((6, 0), (8, 1.25), (11, 2), (15, 3)),
    # 17.11.2026 (S13): kurven fra 16.11 står. Fysikk-kontrollørens alternativ
    # (5,0) (7; 5/3) (8,2) var STRENGERE mellom 5 og 8 m/s, ikke slakere, og
    # kontrolløren trakk det 17.11.2026 (det ga Breivikeidet 17.11 kl. 08Z
    # 0 poeng av vinden alene). Theodor: vind under ca. 6-7 m/s betyr nesten
    # ingenting. Kurvene tas opp igjen når loggene har flere dager.
    "onshore": ((5, 0), (8, 2), (11, 3), (14, 4)),
}
# Theodors regel 2: svellets styrke demper vindstraffen (alle typer unntatt offshore).
# Faktor 1,0 ved 2 000 kJ eller lavere, 0,6 ved 15 000 eller mer, log-interpolert
# mellom. Mangler energien: 1,0 (grunnregelen - ukjent demper ikke).
SWELL_DAMP_KJ_LOW = 2000.0
SWELL_DAMP_KJ_HIGH = 15000.0
SWELL_DAMP_MIN = 0.6


def local_wind(spot):
    """Spotens egen, slakere vindkurve fra spots.json ("wind_local"), eller None.

    23.11.2026 (svar.md 23.11.2026 kl. 11.20, S27; kilde: observasjon 17.11.2026, Theodor: vindstille på stranda
    mens varselet sa 4-5,5 m/s pålands med kast 9-10,5). Breivikeidet og Unstad (S29 a, 23.11.2026) har feltet.
    Under "calm_below_ms" MIDDELVIND tar vinden ingen poeng, og vinden alene gir aldri «Blåst ut» (lav svellandel
    ute, GFS sin deling i svell og vindsjø, gjør det fortsatt, som for alle spots). Fra grensa brukes spotens egne kurver ("curves") på
    MIDDELVINDEN, uten kasttillegget (effective_wind()): da avgjør ikke kastene om grensa er nådd, og observasjonen
    gjaldt vinden på stranda, ikke kastene i varselet. Dempingen fra svellenergien gjelder som før. Ukjent
    vindstyrke er fortsatt ukjent (1 poeng, se wind_penalty()), aldri «svak vind»."""
    return (spot or {}).get("wind_local")


def blown_out_wind_ms(spot):
    """Middelvinden der pålands og skrått pålands vind regnes som «kraftig» (blåst ut) for spoten."""
    lw = local_wind(spot)
    return float(lw["calm_below_ms"]) if lw else BLOWN_OUT_WIND_MS


def wind_calm_ms(spot):
    """Spotens egen vindgrense i m/s middelvind (wind_local.calm_below_ms), eller None for en spot uten egen
    vindkurve. Følger med hver time som "wind_calm_ms" (bare for spots med egen kurve), så teksten i
    regnestykket, dagens time i henteren (publish.wind_blamed()) og ordet på skjermen (calmWindWord() i
    docs/js/app.js) bruker samme grense som ratingen (fysikk-kontrolløren og feiljegeren 23.11.2026)."""
    lw = local_wind(spot)
    return float(lw["calm_below_ms"]) if lw else None


def _wind_eff(speed, gust, spot):
    """Vinden kurven leses på: effektiv vind med kast, eller middelvinden for en spot med egen kurve (local_wind())."""
    return speed if local_wind(spot) is not None else effective_wind(speed, gust)


def _wind_raw(eff, kind, spot):
    """Rå vindstraff for spoten: de vanlige kurvene, eller spotens egne (local_wind())."""
    lw = local_wind(spot)
    if lw is None:
        return wind_curve_penalty(eff, kind)
    if eff < float(lw["calm_below_ms"]):
        return 0.0
    curves = lw["curves"]
    return wind_curve_penalty(eff, kind, curves.get(kind) or curves["onshore"])


def wind_curve_penalty(eff, kind, pts=None):
    """Rå vindstraff (float) fra kurven for vindtypen (eller fra pts, se _wind_raw())."""
    pts = pts or WIND_PENALTY_CURVES.get(kind) or WIND_PENALTY_CURVES["onshore"]
    if eff <= pts[0][0]:
        return 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if eff <= x1:
            return y0 + (y1 - y0) * (eff - x0) / (x1 - x0)
    return float(pts[-1][1])


def swell_damping(energy_swell_kj):
    """Faktoren vindstraffen ganges med: 1,0 for svakt svell, ned til 0,6 for svært kraftig."""
    if energy_swell_kj is None or energy_swell_kj <= SWELL_DAMP_KJ_LOW:
        return 1.0
    if energy_swell_kj >= SWELL_DAMP_KJ_HIGH:
        return SWELL_DAMP_MIN
    f = math.log(energy_swell_kj / SWELL_DAMP_KJ_LOW) / math.log(SWELL_DAMP_KJ_HIGH / SWELL_DAMP_KJ_LOW)
    return 1.0 - (1.0 - SWELL_DAMP_MIN) * f


def wind_penalty(speed, wind_dir, spot, gust=None, energy_swell_kj=None):
    """Vindstraff i stjerner (float, avrundes først i rate()). Ukjent vind: 1
    (ikke full pott). Ukjent retning: verste fall (onshore)."""
    if speed is None:
        return 1.0
    eff = _wind_eff(speed, gust, spot)
    kind = wind_type(wind_dir, spot) or "onshore"
    pen = _wind_raw(eff, kind, spot)
    if kind != "offshore":
        pen *= swell_damping(energy_swell_kj)
    return pen


def wind_penalty_parts(speed, wind_dir, spot, gust=None, energy_swell_kj=None):
    """Samme som wind_penalty(), men med leddene til forklaringen:
    {eff, kind, raw, damp, pen}."""
    if speed is None:
        return {"eff": None, "kind": wind_type(wind_dir, spot), "raw": 1.0, "damp": 1.0, "pen": 1.0}
    eff = _wind_eff(speed, gust, spot)
    kind = wind_type(wind_dir, spot) or "onshore"
    raw = _wind_raw(eff, kind, spot)
    damp = swell_damping(energy_swell_kj) if kind != "offshore" else 1.0
    return {"eff": eff, "kind": kind, "raw": raw, "damp": damp, "pen": raw * damp}


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


# S42 b (svar.md 24.11.2026 kl. 22.25): de samme ordene som resten av appen (STR.wind i docs/js/strings.js). Bare tekst.
WIND_TYPE_WORD = {"offshore": "fralands", "side": "sidevind", "sideonshore": "skrått pålands", "onshore": "pålands"}


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


_COMPASS16 = ("N", "NNØ", "NØ", "ØNØ", "Ø", "ØSØ", "SØ", "SSØ", "S", "SSV", "SV", "VSV", "V", "VNV", "NV", "NNV")


def _compass16(deg):
    """Himmelretningen for en fra-retning, samme 16 ord som compass() i docs/js/app.js."""
    return _COMPASS16[int((deg % 360) / 22.5 + 0.5) % 16]


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
    """«ingen effekt» under 0,05, «−1» når det runder til et helt tall med én desimal,
    ellers «−0,7» (flytende vindstraff, 15.10.2026)."""
    if n is None or n < 0.05:
        return "ingen effekt"
    if abs(n - round(n)) < 0.05:
        return f"−{int(round(n))}"
    return f"−{n:.1f}".replace(".", ",")


def wind_ms_text(speed, calm_ms=None):
    """Vindstyrken i hele m/s, som før. 23.11.2026 (S28, ja fra Theodor i svar.md 23.11.2026; feiljegeren 23.11.2026):
    på en spot med egen vindgrense (calm_ms = wind_calm_ms(spot), Breivikeidet 8 og Unstad 14 m/s middelvind) viste
    avrundingen 7,5-7,99 m/s som «8» og 13,5-13,99 som «14», mens vinden teller først fra grensa. Når avrundingen
    ellers ville vist grensa uten at den er nådd, står én desimal, rundet ned («7,9»). Alle andre tall og spots som før.
    Samme regel som windMsText() i docs/js/app.js."""
    txt = f"{speed:.0f}"
    if calm_ms is not None and speed < calm_ms and float(txt) >= calm_ms:
        return f"{math.floor(speed * 10) / 10:.1f}".replace(".", ",")
    return txt


def disagree_reason(hour, dir_hit, bw_detail, fjord=False):
    """Kort norsk forklaring på HVA av 4a-betingelsene som slo inn, til
    varselbanneret på detaljsiden (5c). Bygget her, ikke i appen - appen
    skal bare vise det henteren faktisk regnet ut.
    23.11.2026 (bw_tillit): for en fjord-spot med svellet i det tegnede vinduet nevnes ikke eksponeringen ute
    (den teller ikke der, se sources_disagree i rate())."""
    reasons = []
    if dir_hit is not None and dir_hit < SPOT_DIRECTION_OVERRIDE_EXPOSURE and not fjord:
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
                     energy_swell_kj=None, energy_factor_value=1.0,
                     energy_period_value=None, energy_period_source=None,
                     five_open=False, five_fails=None, five_lost=None, wind_took_points=True, tide_level_line=None,
                     fjord_wind_block=False, tide_lost_local=0):
    items = []
    # 27.09.2026 (Theodors rettelse, Unstad for lav - se STATUS.md): tallet
    # vi regner videre med (h) er JUSTERT for BarentsWatch (svellandel,
    # periode, retning ved punktet) - skal aldri kalles "signifikant" alene,
    # det begrepet gjelder BarentsWatch sin EGEN totalhøyde (bw_height).
    # Egen "Etter justering"-linje under viser selve justeringen, med bare
    # leddene som faktisk trekker ned (samme visning som docs/index.html
    # sin surfAdjustmentLine()).
    bw_h = hour.get("bw_height") if source == "barentswatch" else None
    gap_used = gap_floor_applied(hour, spot, h, source)
    # bw_tillit (23.11.2026): for en fjord-spot er høyden andelshøyden også når vinden tar grensa bort, og
    # BarentsWatch-tallet etter justering kan være høyere enn den. Da står ikke «Løftet til».
    fjord_h = fjord_share_height(hour, spot) if source in ("barentswatch", "svell_ute") else None
    fjord_not_lifted = fjord_h is not None and h is not None and (not gap_used or (
        bw_h is not None and bw_detail is not None
        and bw_h * min(bw_detail["swell_share"], bw_detail["bw_period_factor"]) * bw_detail["spot_direction_factor"] > h + 1e-9))
    long_sea_used = bool(hour.get("_long_sea"))
    if long_sea_used and period is not None and hour.get("dir_offshore") is not None:
        # S40 (svar.md 24.11.2026): timen er regnet med den lange sjøen værmodellen kaller vindsjø (long_sea()).
        # Linja står øverst, så «Hvorfor» sier det først. Tallene er de regelen brukte (svell og lang sjø samlet).
        items.append(f"Lang sjø ute {_fmt_m(hour['swell_offshore'])} fra {_compass16(hour['dir_offshore'])}, {period:.0f} s: "
                     "regnet som svell, usikkert")
    if h is None:
        items.append("Signifikant høyde: ingen data")
    elif bw_h is not None:
        items.append(f"BarentsWatch {_fmt_m(bw_h)} signifikant")
    else:
        items.append(f"Signifikant høyde {_fmt_m(h)} ute ved spoten")
    if source == "barentswatch" and bw_detail is not None:
        share_pct = round(bw_detail["swell_share"] * 100)
        items.append(f"Svellandel: {share_pct} % ({'lang sjø regnet som svell' if long_sea_used else _share_word(bw_detail['swell_share'])})")
        if hour.get("bw_period") is not None and bw_detail.get("bw_period_basis") == "ute":
            items.append(f"BarentsWatch-periode {hour['bw_period']:.0f} s: ikke brukt. "
                         + f"Nesten alt ute er svell med periode {period:.1f} s".replace(".", ","))
        elif long_sea_used:
            # M4 og K1 (fysikk-kontrolløren 25.11.2026): regelen leser toppperioden ved punktet I SELVE TIMEN, også når
            # tallet er jevnet ut mellom to modelltimer (BarentsWatch gir tall hver tredje time). Da står det i linja.
            # Under 7 s eller ukjent: høyst halve energien der er den lange sjøen. Ellers hele høyden.
            jevnet = " (jevnet ut mellom to modelltimer)" if hour.get("bw_interpolated") else ""
            bw_p_txt = f"{hour['bw_period']:.0f} s{jevnet}" if hour.get("bw_period") is not None else "ukjent"
            if bw_detail.get("bw_period_basis") == "lang_sjo_kort_topp":
                items.append(f"BarentsWatch-periode {bw_p_txt}: kort, høyst halve energien regnes som lang sjø")
            else:
                items.append(f"BarentsWatch-periode {bw_p_txt}: lang, hele høyden ved punktet regnes som lang sjø")
        elif hour.get("bw_period") is not None:
            items.append(f"BarentsWatch-periode {hour['bw_period']:.0f} s: {_bw_period_word(bw_detail['bw_period_factor'])}")
        if bw_detail["spot_direction_offshore"]:
            items.append("Bølgene ved spoten går ut fra land. Trolig vindsjø fra land, ikke svell inn.")
        elif bw_detail.get("spot_direction_overridden"):
            items.append("Retning ved spoten: ikke brukt, svellet ute treffer godt")
        else:
            items.append(f"Retning ved spoten: {_spot_dir_word(bw_detail['spot_direction_factor'])}")
        if h is not None and bw_h is not None and not gap_used and fjord_h is None:
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
    if fjord_not_lifted:
        andel = gap_share(hour, spot)
        items.append((f"{_fmt_m(h)}: svell ute {_fmt_m(hour['swell_offshore'])} gjennom gapet, "
                      f"andel {andel:.2f}").replace(".", ",") + ". Anslag, ikke kystmodellens tall")
    elif gap_used:
        # gap_used er bare sann når andelen finnes (se gap_floor())
        andel = gap_share(hour, spot)
        items.append((f"Løftet til {_fmt_m(h)}: svell ute {_fmt_m(hour['swell_offshore'])} gjennom gapet, "
                      f"andel {andel:.2f}").replace(".", ",") + ". Anslag, ikke kystmodellens tall")
    elif fjord_share_applied(hour, spot, h, source):
        # 24.11.2026 (feiljegeren, funn 4): reserven under 7 s for en fjord-spot. Høyden er samme andel (share_height),
        # men gap-grensa gjelder ikke der, så linja manglet. Samme ord som over, uten «Løftet til». Bare tekst.
        andel = gap_share(hour, spot)
        items.append((f"{_fmt_m(h)}: svell ute {_fmt_m(hour['swell_offshore'])} gjennom gapet, "
                      f"andel {andel:.2f}").replace(".", ",") + ". Anslag, ikke kystmodellens tall")
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
            # 07.10.2026, Theodors oppgave: vis HVILKEN periode energien ble
            # regnet med, og om den er omregnet - "Periode"-cella (period,
            # over) viser uansett alltid den ekte middelperioden, uendret.
            if energy_period_source == "topp":
                period_note = f" (topperiode {energy_period_value:.1f} s)".replace(".", ",")
            elif energy_period_source == "omregnet":
                period_note = (f" (periode omregnet til {energy_period_value:.1f} s, "
                                f"×{PEAK_PERIOD_FACTOR_DEFAULT})").replace(".", ",")
            else:
                period_note = ""
            if energy_factor_value < 0.999:
                # S42 c (svar.md 24.11.2026 kl. 22.25): «teller 65 %» i stedet for «faktor 0.65 (potensial ganget ned)».
                # Bare tekst: tallet er energy_factor_value, rundet til hele prosent (aldri 100 her, minst 99,9 % går over)
                items.append(f"Energi (svell) {round(energy_swell_kj)} kJ{period_note}: "
                              f"teller {min(99, round(energy_factor_value * 100))} %")
            elif energy_thresholds_used(spot) is None:
                # 17.11.2026: spoten er unntatt energiregelen - bare tallet
                items.append(f"Energi (svell) {round(energy_swell_kj)} kJ{period_note}")
            else:
                items.append(f"Energi (svell) {round(energy_swell_kj)} kJ{period_note}: over terskelen, ingen effekt")
        if blown_out:
            # 22.11.2026 (Theodor S24 b): linja sa «og sterk vind» også i 1 m/s (Seines 21.11 kl. 12-14, under ordet
            # «Flatt»). Vinden nevnes bare når den har tatt poeng eller er sterk (blown_out_wind_strong(): effektiv vind
            # med kast, samme mål som vindkurven og som ordet i docs/js/app.js, Theodor S26 b 23.11.2026; en spot med
            # egen vindkurve bruker sin egen grense på middelvinden, wind_calm_ms()). Mangler
            # vindstyrken, nevnes den ikke. is_blown_out() krever low_hs, og da er potensialet 0 og vinden har ingenting
            # å ta: i dag er det derfor styrken som avgjør, og wind_took_points står som sikring hvis den regelen endres.
            # Bare tekst, ingen poeng eller høyder.
            strong_wind = blown_out_wind_strong(wind_speed, gust, wt, wind_calm_ms(spot)) is True
            cause = "mye vindsjø og sterk vind" if (wind_took_points and wind_speed is not None) or strong_wind else "mye vindsjø"
            items.append(f"Surfehøyde: blåst ut, {cause}, ikke surfbart "
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
    # 24.11.2026 (feiljegeren, funn 2): når høyden er andelshøyden for en fjord-spot, sier linja hvor svellet ligger i
    # det TEGNEDE vinduet (samme directness() som ellers, bare mot det vinduet høyden er regnet fra). dir_hit leses
    # fra eksponeringen mot swell_window, som ikke kjenner gapet, og ga «svakt inn i skyggen» rett under «svell ute
    # gjennom gapet». Bare ordet i regnestykket: ingen tall i ratingen bruker dette.
    dir_word_hit = dir_hit
    if fjord_share_applied(hour, spot, h, source):
        dir_word_hit = directness(hour["dir_offshore"], {"swell_window": spot["swell_window_tegnet"]})
    items.append(f"Retning: {_direction_word(dir_word_hit)}")
    if wind_speed is None:
        items.append("Vind: ukjent")
    else:
        label = wind_label(wind_speed, WIND_TYPE_WORD.get(wt, wt or ""))
        # 15.10.2026: «Vind 9 m/s sidevind, kast 15 (teller som 10,7), dempet av kraftig svell: −0,7»
        wpp = wind_penalty_parts(wind_speed, wind_dir, spot, gust, energy_swell_kj)
        gusttxt = ""
        if gust is not None and gust > wind_speed and wpp["eff"] is not None and wpp["eff"] > wind_speed + 0.05:
            gusttxt = f", kast {gust:.0f} (teller som {wpp['eff']:.1f})".replace(".", ",")
        elif gust is not None and gust > wind_speed and local_wind(spot) is not None:
            gusttxt = f", kast {gust:.0f}"
        lw = local_wind(spot)
        if lw is not None and wind_speed < float(lw["calm_below_ms"]):
            gusttxt += f" (vinden teller først fra {float(lw['calm_below_ms']):.0f} m/s middelvind her)"
        damptxt = ""
        if wpp["damp"] < 0.999:
            damptxt = ", dempet av " + ("svært kraftig" if (energy_swell_kj or 0) >= 10000 else "kraftig") + " svell"
        if fjord_wind_block:
            # bw_tillit (23.11.2026): vinden tar gap-grensa bort for en fjord-spot, og timen får 0 (se rate())
            damptxt += f", vinden teller først fra {blown_out_wind_ms(spot):.0f} m/s her"
        elif wp is not None and wpp["pen"] < wp - 1e-9:
            damptxt += ", lokal regel strengere"
        items.append(f"Vind {wind_ms_text(wind_speed, wind_calm_ms(spot))} m/s {label}{gusttxt}{damptxt}: {_fmt_penalty(wp)}")
    if tide_level_line:
        # 22.11.2026: spoten har en myk regel på vannstanden (tide_level_penalty()) - da er «tåler alt» feil.
        # 24.11.2026 (fysikk-kontrolløren, vilkår 2): det samme for en spot med lokal regel på flo og fjære
        # (local_rules.tide_prefer, Farstadsanden og Unstad) - linja er den local_rules_penalty() skriver.
        items.append(tide_level_line)
    elif (spot.get("local_rules") or {}).get("tide_prefer") and "tide_penalty_high" in spot["local_rules"]:
        items.append("Tidevann: ukjent")   # regelen finnes, men tidevannet mangler for timen: aldri «tåler alt»
    elif not spot.get("tide"):
        items.append("Tidevann: spoten tåler alt")
    elif not tide:
        items.append("Tidevann: ukjent")
    else:
        items.append(f"Tidevann ({tide.get('state','?')}): {_fmt_penalty(tide_pen)}")
    if sources_disagree and disagree_cap is not None and disagree_cap > potential:
        items.append(f"Kilder uenige: kappet fra {disagree_cap} til maks 1 stjerne")
    elif capped_from is not None and capped_from > potential:
        # S40 (feiljegeren 25.11.2026, V4): i en time regnet med lang sjø er grunnen selve omregningen, ikke manglende BarentsWatch
        grunn = ("lang sjø regnet som svell er et anslag" if long_sea_used
                 else "ingen BarentsWatch, og retning utenfor vinduet eller stor dreining")
        items.append(f"Usikkert varsel: kappet fra {capped_from} til maks 3 stjerner ({grunn})")
    # 15.10.2026: 5-stjerners-porten
    if five_open:
        items.append("Rått-svell: høyden midt i spotens beste spenn, 13 s eller lengre, kraftig svell midt i vinduet, BarentsWatch bekrefter: 5 mulig")
        if five_lost == "wind":
            items.append("Femte stjerne holdes tilbake: vinden er ikke ren (fralands eller nesten blank uten straff)")
        elif five_lost == "tide":
            items.append("Femte stjerne holdes tilbake: tidevannet er ikke det spoten liker")
    elif five_fails:
        items.append("Ikke Rått: " + ", ".join(five_fails[:3]))
    without_wind = min(potential, solid + lost_wind)
    total = f"Totalt: {solid} av 5 stjerner"
    tide_lost = lost_tide + tide_lost_local   # som tideLost() i docs/js/app.js: faded_tide og local_rules.stars_lost
    if lost_wind > 0 and tide_lost > 0:
        # S42 d (svar.md 24.11.2026 kl. 22.25): har både vinden og tidevannet tatt poeng, sier parentesen begge.
        # Tallet er det faste pluss det de to tok (faded_wind, faded_tide og local_rules.stars_lost). Bare tekst.
        total += f" ({min(potential, solid + lost_wind + tide_lost)} uten vind og tidevann)"
    elif lost_wind > 0:
        total += f" ({without_wind} uten vind)"
    items.append(total)
    return items


BLOWN_OUT_WIND_MS = 8.0  # «kraftig» onshore/side-onshore (ordet følger zero_losses som før - Theodor 15.10.2026, regel 5)
BLOWN_OUT_SHARE_MAX = 0.5  # samme "mest vindsjø"-grense som _share_word()
BLOWN_OUT_TEXT_OFFSHORE_MS = 12.0  # bare teksten i regnestykket: fralandsvind er «sterk» fra 12 m/s med kast (OFFSHORE_STRONG_MS i docs/js/app.js)
BLOWN_OUT_TEXT_WIND_MS = 8.0  # bare teksten: vind fra andre og ukjente retninger er «sterk» fra 8 m/s med kast (CALM_WIND_MS i docs/js/app.js, S26 b)


def blown_out_wind_strong(wind_speed, gust, wt, calm_ms=None):
    """23.11.2026 (Theodor S26 b, som fysikk-kontrolløren): er vinden i en blåst ut-time sterk nok til å få
    skylda? Målt som effektiv vind med kast (effective_wind(), samme mål som vindkurven i ratingen):
    fralandsvind fra 12 m/s, vind fra siden, fra havet, skrått fra havet og fra ukjent retning fra 8 m/s.
    Mangler kastet, er det middelvinden alene (som effective_wind()). Mangler vindstyrken: None, aldri 0.
    En spot med egen vindkurve (calm_ms = wind_calm_ms(spot); fysikk-kontrolløren og feiljegeren 23.11.2026,
    S29 a): der får vinden skylda først fra spotens egen grense, målt på MIDDELVINDEN uansett kast (som
    kurven leses), og fralands fra den høyeste av grensa og 12 m/s. Unstad: 14 m/s. Breivikeidet: 8 m/s, og
    12 fralands. Ellers sa linja «og sterk vind» mens vindlinja under sa «ingen effekt».
    Samme grenser som ordet på skjermen (calmWindWord() i docs/js/app.js) og som dagens time ved likt
    poeng og lik høyde (publish.best_hour()). Bare tekst og visning: is_blown_out() og poengene er
    uendret (den grensa er middelvinden uten kast mot blown_out_wind_ms(spot): 8 m/s, eller spotens egen)."""
    if calm_ms is not None:
        if wind_speed is None:
            return None
        return wind_speed >= (max(calm_ms, BLOWN_OUT_TEXT_OFFSHORE_MS) if wt == "offshore" else calm_ms)
    eff = effective_wind(wind_speed, gust)
    if eff is None:
        return None
    return eff >= (BLOWN_OUT_TEXT_OFFSHORE_MS if wt == "offshore" else BLOWN_OUT_TEXT_WIND_MS)
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
    # 23.11.2026 (S27, se local_wind()): en spot med egen vindkurve er ikke blåst ut AV VINDEN under grensa
    # (blown_out_wind_ms()). Lav svellandel (share_low) gjelder som før: den er GFS sin deling av sjøen ute i
    # svell og vindsjø (swell_share()), ikke vinden på stranda (fysikk-kontrolløren 23.11.2026).
    # Ukjent vindstyrke er ikke sterk vind (S22).
    strong_onshore = wt in ("onshore", "sideonshore") and speed is not None and speed >= blown_out_wind_ms(spot)
    return share_low or strong_onshore


STORMSJO_SHARE_MAX = 0.4  # "lav svellandel", se classify_low_rating()
LOW_RATING_FLAT_SURF_HEIGHT_MAX = 0.4  # "surfehøyde under ca. 0,4 m", se classify_low_rating()


def classify_low_rating(hour, spot, source, bw_detail, low_hs, surf_height, dir_hit,
                         potential, lost_wind, lost_tide, solid, blown_out, energy_swell=None, share_used=False):
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
    observert helt flatt, og ordet forblir "Flatt").

    23.11.2026 (svar.md 23.11.2026 kl. 14.05, Theodor: «Hvis det er surf på
    Breivikeidet er det så å si alltid bølger på de to andre spottene i
    Lyngen»; kilder: observasjon 17.11.2026 og 22.11.2026, Theodor): en fjord-spot
    (bw_tillit "fjord") får aldri "treffer_ikke" når høyden timen regnes med
    ER andelshøyden (share_used, se fjord_share_applied()). Høyden er der
    regnet fra det tegnede vinduet (fjord_share_height() og
    gap_edge_factor()), mens dir_hit leses fra eksponeringstabellen, som
    ikke kjenner gapet (Russelv 17.11.2026 kl. 09Z: svell fra 17°, 0,44 m
    ved spoten, dir_hit 0,53). Ordet ville sagt at svellet bommer i en time
    der høyden kommer fra nettopp det svellet. Er høyden lav, er ordet
    "flat". Ellers vinner de andre grunnene som før.
    24.11.2026 (fysikk-kontrolløren, vilkår 5): unntaket gjelder bare når
    andelshøyden faktisk er brukt. Før gjaldt det hele det tegnede vinduet,
    også med BarentsWatch-tall og svellperiode under 7 s, der høyden er
    BarentsWatch-høyden og spoten regnes som en kyst-spot. Der, og utenfor
    det tegnede vinduet, er ordet som for en kyst-spot."""
    if solid > 1:
        return None
    fjord = bool(share_used)   # høyden er andelshøyden: se siste avsnitt i docstringen
    # 19.11.2026 (fysikk-kontrolløren, forslag S22): svellet kommer gjennom gapet, men gap-grensa er tatt bort av
    # kraftig pålandsvind (eller vind fra ukjent retning). Timen er blåst ut, ikke flat: BarentsWatch-høyden ved
    # punktet er lav fordi kystmodellen slipper for lite inn, ikke fordi svellet mangler (Russelv 16.11.2026).
    # Bare når grensa ville løftet høyden over flat-sperren: er svellet ute så lite at timen er flat også uten
    # vinden (grense under FLAT_HS_THRESHOLD), er ordet fortsatt flat.
    if gap_blocked_by_wind(hour, spot) and gap_floor_height(hour, spot) >= FLAT_HS_THRESHOLD:
        return "blown_out"
    bw = hour.get("bw_height") if source == "barentswatch" else None
    little_total = bw is None or bw < BLOWN_OUT_MIN_BW_HEIGHT
    flat = little_total and (low_hs or (surf_height is not None and surf_height < LOW_RATING_FLAT_SURF_HEIGHT_MAX))
    if flat:
        if (not fjord and source != "barentswatch" and dir_hit is not None and dir_hit < SPOT_DIRECTION_OVERRIDE_EXPOSURE
                and energy_swell is not None
                and energy_swell >= (energy_thresholds_used(spot) or (None, LOW_ENERGY_WORD_KJ))[1]):
            return "treffer_ikke"
        return "flat"
    # 19.11.2026 (fysikk-kontrolløren, forslag S22): ukjent vindstyrke koster det faste ene poenget i wind_penalty(),
    # men vi vet ikke at det blåser. En time uten vindstyrke får aldri vinden som grunn.
    wind_dominant = (hour.get("wind_speed") is not None
                     and potential >= 1 and lost_wind > 0 and lost_wind >= lost_tide)
    if blown_out or wind_dominant:
        return "blown_out"
    if bw_detail is not None and not little_total and bw_detail["swell_share"] < STORMSJO_SHARE_MAX:
        return "stormsjo"
    if (not fjord and dir_hit is not None and dir_hit < SPOT_DIRECTION_OVERRIDE_EXPOSURE
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
# Standardgrensene (full, zero) i kJ for spots uten egne tall (06.10.2026).
# Egne tall i local_rules.min_energy_kj overstyrer (Farstadsanden, Magnus
# sine 3000/1500/0,7, og Unstad).
# 17.11.2026: en spot med kilde på at regelen ikke passer, setter
# no_energy_rule i spots.json (kilden står i _no_energy_rule) og får ingen
# energiregel. Breivikeidet er den
# eneste (observasjon 17.11.2026, Theodor: hoftehøyt og rent på sandbanken
# med ca. 900 kJ ute, standardgrensene tok 1 poeng).
# Port A for 5 poeng (FIVE_STAR_ENERGY_MIN_KJ) gjelder uansett.
ENERGY_DEFAULT_KJ = (2000, 500)
ENERGY_WEIGHT_DEFAULT = 0.5
# Ordgrense, ikke ratingregel: under denne svellenergien ute heter en lav
# time «flatt» og ikke «treffer ikke» (se classify_low_rating()). Samme tall
# som den gamle standard zero-grensa.
LOW_ENERGY_WORD_KJ = 500


def _energy_thresholds(spot):
    """(full, zero, weight) for spoten, eller None når spoten er unntatt
    energiregelen (no_energy_rule i spots.json)."""
    if spot.get("no_energy_rule"):
        return None
    rules = spot.get("local_rules") or {}
    thresholds = rules.get("min_energy_kj") or {}
    full = thresholds.get("full", ENERGY_DEFAULT_KJ[0])
    zero = thresholds.get("zero", ENERGY_DEFAULT_KJ[1])
    shelter = spot.get("shelter_factor")
    if shelter is not None and 0 < shelter < 1:
        full, zero = full / shelter, zero / shelter
    return full, zero, rules.get("weight", ENERGY_WEIGHT_DEFAULT)


def energy_factor(spot, energy_swell):
    """Hvor mye svellstjernene (potensialet) skal ganges med ut fra
    SVELLENERGIEN ute (energy_swell - EKTE svell, IKKE totalhøyden som
    inkluderer vindsjø, se energy_kj()/rate() sin egen begrunnelse), FØR
    vind og tidevann trekker fra (Theodors eksplisitte rekkefølge, se
    rate()). 1,0 fra full-grensa, lineært ned til 0,3 ved zero-grensa, 0,3
    under zero. Standardgrensene gjelder alle spots uten egne tall. En spot
    med `no_energy_rule` i spots.json er unntatt og får 1,0 (se
    modulnivå-kommentaren over).

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
    used = _energy_thresholds(spot)
    if used is None:
        return 1.0
    full, zero, weight = used
    if full is None or zero is None or full <= zero:
        return 1.0
    if energy_swell >= full:
        raw = 1.0
    elif energy_swell <= zero:
        raw = LOCAL_ENERGY_FACTOR_FLOOR
    else:
        raw = LOCAL_ENERGY_FACTOR_FLOOR + (1 - LOCAL_ENERGY_FACTOR_FLOOR) * (energy_swell - zero) / (full - zero)
    return 1 - weight * (1 - raw)


def energy_thresholds_used(spot):
    """(full, zero, weight) FAKTISK brukt for spoten akkurat nå, eller None
    når spoten er unntatt energiregelen (17.11.2026). Samme
    override/skjerming-logikk som energy_factor(), men uten å trenge en
    energi-verdi."""
    return _energy_thresholds(spot)


def _m_text(cm):
    """Vannstand i meter med én desimal og desimalkomma (aldri «-0,0»)."""
    return f"{cm / 100:.1f}".replace(".", ",").replace("-0,0", "0,0")


def _tide_level_clock(hour):
    """« kl. 09.30» (norsk tid) for tidspunktet vannstanden i timen gjelder, eller tom streng uten timens tid.
    Vannstanden per time er regnet 30 minutter etter timeslaget (fetch.py), mens spotsiden viser nivået på timeslaget i
    raden TIDEVANN. Uten klokkeslettet sto 1,3 m i raden og 1,57 m i «Hvorfor» for samme time (feiljegeren 26.11.2026, V2).
    Bare tekst."""
    t = hour.get("t")
    if not isinstance(t, str):
        return ""
    try:
        import datetime as _dt
        from zoneinfo import ZoneInfo
        tid = _dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
        if tid.tzinfo is None:
            tid = tid.replace(tzinfo=_dt.timezone.utc)
        return (tid + _dt.timedelta(minutes=30)).astimezone(ZoneInfo("Europe/Oslo")).strftime(" kl. %H.%M")
    except Exception:
        return ""


def _tide_level_low_part(level_rule):
    """(gulv_cm, bunn_cm, fradrag) for den nedre delen av regelen, eller None når den mangler eller ikke er gyldig:
    alle tre feltene må være tall, bunnen under gulvet og fradraget over 0. Halve eller ugyldige felt slår den nedre
    delen av (ingen straff, ingen krasj), og regelen virker som uten den (feiljegeren 26.11.2026, kosmetisk 5)."""
    v = [level_rule.get(k) for k in ("low_full_above_cm", "low_max_at_cm", "low_penalty")]
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in v):
        return None
    top, bottom, pen = v
    if not (bottom < top and pen > 0):
        return None
    return top, bottom, pen


def tide_level_penalty(hour, spot, potential=None):
    """Myk lokal regel på vannstanden i cm over sjøkartnull (local_rules["tide_level"]): (fradrag vektet med weight, linje).
    Øvre del, «lavere vann er bedre»: ingen straff opp til "full_below_cm", så jevnt opp til "penalty" ved "max_at_cm" og
    aldri mer. Nedre del (valgfri, 26.11.2026, svar.md 26.11.2026 kl. 13.10; kilde: observasjon 26.11.2026, Theodor: «Ikke
    surfbart før 10-10:30 pga lavvann»): ingen straff fra "low_full_above_cm" og opp, så jevnt opp til "low_penalty" ved
    "low_max_at_cm" og aldri mer under det. Mellom de to grensene er det ingen straff. Mangler regelen: (0.0, None).
    Mangler vannstanden (uten cm, eller Kartverket feilet): (0.0, linje som sier at vannstanden mangler) - manglende data
    er aldri 0, gir aldri straff, og er aldri «tåler alt». 22.11.2026 (svar.md 22.11.2026 kl. 12.20; kilder: observasjon
    17.11.2026 og 22.11.2026, Theodor).
    potential (bare tekst, feiljegeren 26.11.2026, kosmetisk 1): det timen har før vind og tidevann. Er det 0, sier linja
    «ingen poeng å ta» i stedet for et fradrag som ikke ble tatt. Tallet som returneres er det samme uansett."""
    rules = spot.get("local_rules") or {}
    level_rule = rules.get("tide_level")
    cm = (hour.get("tide") or {}).get("cm")
    if not level_rule:
        return 0.0, None
    if cm is None:
        # manglende vannstand er aldri 0 cm og aldri «tåler alt»: ingen straff, og teksten sier at tallet mangler
        return 0.0, "Tidevann: vannstanden mangler, ingen straff"
    weight = rules.get("weight", 1.0)
    lo, hi = level_rule["full_below_cm"], level_rule["max_at_cm"]
    share = min(1.0, max(0.0, (cm - lo) / (hi - lo)))
    pen = weight * level_rule["penalty"] * share
    m = _m_text(cm)
    low = _tide_level_low_part(level_rule)
    if low is None:
        # regel uten nedre del (ingen spot har det i dag): ordene fra 22.11.2026
        if pen > 0:
            return pen, f"Tidevann ({m} m over sjøkartnull): jo lavere vann, jo bedre her" + f": −{pen:.2f} poeng".replace(".", ",")
        return 0.0, f"Tidevann ({m} m over sjøkartnull): lavt nok, ingen straff"
    low_top, low_bottom, low_raw = low
    gulv, kl = _m_text(low_top), _tide_level_clock(hour)
    tomt = potential is not None and potential <= 0      # ingenting å ta: linja påstår ikke et tap
    if pen > 0:
        tall = "ingen poeng å ta" if tomt else f"−{pen:.2f} poeng".replace(".", ",")
        return pen, f"Tidevann ({m} m over sjøkartnull{kl}): lavere vann er bedre her, ned til ca. {gulv} m: {tall}"
    low_share = min(1.0, max(0.0, (low_top - cm) / (low_top - low_bottom)))
    low_pen = weight * low_raw * low_share
    if low_pen > 0:
        # samme form som linja for flo og fjære (S42 a): «Lavt vann. …: −N poeng.» Appen leser den med TIDEVANN_LINJE.
        # Ordet følger tide.state som forklaringsarket («Middels vann» ved 1,57 m 26.11.2026; feiljegeren, kosmetisk 2).
        ordet = TIDE_STATE_WORD.get((hour.get("tide") or {}).get("state")) if (hour.get("tide") or {}).get("state") in ("lav", "middels") else "Lavt vann"
        # to desimaler på vannstanden her: 1,57 m ved en grense på 1,6 m skal ikke stå som «1,6 m, og under ca. 1,6 m»
        m2 = f"{cm / 100:.2f}".replace(".", ",").replace("-", "−")
        tall = "ingen poeng å ta" if tomt else f"−{low_pen:.2f}".replace(".", ",") + " poeng"
        return low_pen, f"{ordet}. {m2} m{kl or ' midt i timen'}, og under ca. {gulv} m er det for lite vann her: {tall}."
    return 0.0, f"Tidevann ({m} m over sjøkartnull{kl}): passe vannstand, ingen straff"


def local_tide_prefer_line(spot, lines):
    """Tidevannslinja local_rules_penalty() skrev for en spot med lokal regel på flo og fjære (local_rules.tide_prefer),
    ellers None. 24.11.2026 (fysikk-kontrolløren, vilkår 2): regnestykket sa «Tidevann: spoten tåler alt» for
    Farstadsanden og Unstad mens den lokale regelen tok ett poeng. Bare tekst."""
    rules = spot.get("local_rules") or {}
    if "tide_penalty_high" not in rules or "tide_prefer" not in rules:
        return None
    return next((l for l in lines if (l.startswith("Tidevann (") and "foretrukket lokalt" in l)
                 or (l.split(". ")[0] in TIDE_STATE_WORD.values() and "Lokale sier" in l)), None)


# S42 a (svar.md 24.11.2026 kl. 22.25): ordene i linja for den lokale regelen på flo og fjære. Bare tekst.
# 25.11.2026 (feiljegeren på designfase 2, funn 2): «Høyt vann», ikke «Høyvann». Ordet følger tide.state, som er «høy» i
# hele den øverste tredelen av syklusen, også når vannet faller to timer etter flo. «Høyvann» er et tidspunkt.
TIDE_STATE_WORD = {"høy": "Høyt vann", "middels": "Middels vann", "lav": "Lavt vann"}
TIDE_PREFER_WORD = {"lav": "lavt", "middels": "middels", "høy": "høyt"}


def tide_prefer_words(prefer):
    """«lavt og middels» av ["lav", "middels"], i fast rekkefølge (lavt, middels, høyt)."""
    ord_ = [TIDE_PREFER_WORD[k] for k in ("lav", "middels", "høy") if k in prefer]
    return " og ".join([", ".join(ord_[:-1]), ord_[-1]]) if len(ord_) > 1 else "".join(ord_)


def local_rules_penalty(hour, spot, wind_type_, wind_speed, potential=None):
    """Tidevann og en strengere offshore-sjekk, begge "koster stjerner".
    15.10.2026 (Theodors regel 4): returnerer (tidevann_rå, vind_rå, linjer),
    begge vektet med weight. Tidevannsfradraget er et eget, additivt ledd i
    rate(); VINDfradraget legges ikke oppå den generelle vindstraffen, men
    erstatter den når det er strengere (rate(): wp = max(generell, lokal)) -
    og bokføres da som vind (zero_losses["wind"]), ikke som "local". Alt
    summeres som flyttall i rate() og rundes til slutt (0,5 opp)."""
    rules = spot.get("local_rules")
    if not rules:
        return 0.0, 0.0, []
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
                # 24.11.2026 (fysikk-kontrolløren, vilkår 2): desimalkomma, som resten av regnestykket. To desimaler,
                # som linja for vannstanden (tide_level_penalty(), «−0,49»): med én sto Unstads 0,35 som «−0,3», og
                # vind −0,2 og tidevann «−0,3» så ikke ut som ett poeng (feiljegeren V2 og kontrolløren 24.11.2026).
                # S42 a (svar.md 24.11.2026 kl. 22.25): «Høyvann. Lokale sier lavt og middels vann er best her: −0,7 poeng.»
                # i stedet for «Tidevann (høy): ikke blant det lokale favoriserer - −1 stjerne (vektet −0,70)». Tallet er
                # det vektede fradraget (det som faktisk trekkes), med to desimaler når det trengs (Unstad: −0,35).
                tall = f"{pen:.2f}".rstrip("0").rstrip(".").replace(".", ",")
                lines.append(f"{TIDE_STATE_WORD.get(state, f'Tidevann ({state})')}. Lokale sier "
                             f"{tide_prefer_words(rules['tide_prefer'])} vann er best her: −{tall} poeng.")
            else:
                lines.append(f"Tidevann ({state}): foretrukket lokalt, ingen straff")

    level_pen, level_line = tide_level_penalty(hour, spot, potential)
    if level_line:
        raw_total += level_pen
        lines.append(level_line)

    local_wind = 0.0
    if rules.get("offshore_strict"):
        strict_hit = (wind_type_ in ("side", "sideonshore")
                      and wind_speed is not None and wind_speed > 4)
        if strict_hit:
            local_wind = weight * 1
            lines.append(f"Vind {wind_speed:.0f} m/s {WIND_TYPE_WORD.get(wind_type_, wind_type_)}: "
                         f"strengere lokal grense (over 4 m/s): −" + f"{local_wind:.1f}".replace(".", ",") + " poeng, "
                         f"erstatter den generelle vindstraffen hvis strengere")

    # 15.10.2026 (Theodors regel 4): det lokale VINDfradraget legges ikke oppå den generelle
    # vindstraffen (Farstadsanden ble straffet to ganger, −2 og −1) - rate() tar
    # max(generell, lokal × vekt). Tidevannsfradraget er fortsatt et eget, additivt ledd.
    return raw_total, local_wind, lines


def rate(hour, spot, _long_sea=True):
    """Stjerner for én time. Blasse stjerner = det vind og tidevann tar."""
    # S29 c del 2 (LONG_SEA_AS_SWELL, på for Unstad fra S40): lang sjø fra havsiden som GFS kaller vindsjø, regnes som svell
    # i ALLE ledd under (svellandel, energi, periode, retning). Timen selv (det som lagres og vises) røres ikke.
    # Regelen kan bare løfte: gir omregningen ikke FLERE poeng enn den vanlige regningen (taket på 3 for en usikker
    # time, flat-sperren, eller surfehøyde over ideal_height), gjelder den vanlige (long_sea_base under, brukt helt til slutt).
    long_sea_hour = long_sea(hour, spot) if _long_sea else None
    long_sea_base = None
    if long_sea_hour is not None:
        long_sea_base = rate(hour, spot, _long_sea=False)
        long_sea_gfs = {"swell_offshore": hour.get("swell_offshore"), "period": hour.get("period"), "dir_offshore": hour.get("dir_offshore")}
        hour = {**hour, **long_sea_hour}
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
    gap_used = gap_floor_applied(hour, spot, h, source)
    share_used = fjord_share_applied(hour, spot, h, source)
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
        # 23.11.2026 (S27, feiljegeren): for en gap-spot med myk kant har spot_height() allerede brukt
        # gap_edge_factor() i hele kantsonen (også de 2 gradene utenfor det tegnede vinduet). Ekstra demping her
        # ville dempet samme retning to ganger, og reserven ville gitt lavere surfehøyde enn BarentsWatch-sonen
        # for samme svell (0 mot 2 poeng ved 343-344 og 31-32 grader). Samme tanke som override-unntaket over.
        # (bw_tillit 23.11.2026: gjelder alle fjord-spots, ikke bare den med myk kant)
        gap_soft = fjord_in_window(hour, spot)
        needs_extra_damping = (raw_exposure_zero(dir_off, spot)
                                and exposure_override_cap(dir_off, spot) is None
                                and not gap_soft)
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
    potential = min(4, int(5 * score + 1e-9))  # rund ned; 5 gis bare av porten (five_star_swell_gate, under)

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
        # 16.11.2026: høyden er løftet til gap-grensa (svell ute × andel),
        # et anslag og ikke kystmodellens eget tall - se gap_floor().
        or gap_used
        # 23.11.2026 (bw_tillit, fysikk-kontrolløren): en fjord-spot uten BarentsWatch er usikker under
        # GAP_MIN_PERIOD_S (andelen er satt fra observasjoner med 7,4-8,1 s) og når svellretningen ute mangler.
        # Andelshøyden er et anslag i begge soner, også når vinden tar grensa bort (timen har da 0 poeng).
        or fjord_share_height(hour, spot) is not None
        or (is_fjord(spot) and source == "svell_ute"
            and (hour.get("dir_offshore") is None
                 or (gap_swell_in_window(hour, spot) and (period is None or period < GAP_MIN_PERIOD_S))))
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
    # 16.11.2026: for en gap-spot sier det tegnede vinduet at svellet kommer
    # inn. Da kan ikke dårlig eksponering ute alene bety «kildene uenige»
    # (Russelv 17.11.2026: svell fra 17°, to grader utenfor det beregnede
    # vinduet, men midt i det tegnede). Vilkåret er retningen ute
    # (gap_swell_in_window()), ikke om gap-grensa ble brukt (fysikk-kontrollør
    # 16.11.2026: ellers ga MER energi ved punktet lavere vurdering). Vindsjø-
    # andel og retning ved punktet teller som før.
    sources_disagree = (
        source == "barentswatch" and bw_detail is not None
        and (hour.get("bw_height") or 0) >= 0.5
        and ((dir_hit < SPOT_DIRECTION_OVERRIDE_EXPOSURE and not bw_detail.get("bw_confirms")
              and not gap_swell_in_window(hour, spot))
             or bw_detail["swell_share"] < 0.5
             or (bw_detail["spot_direction_factor"] < 0.5 and not bw_detail["spot_direction_offshore"]))
    )
    # 23.11.2026 (bw_tillit): for en fjord-spot er BarentsWatch bare et tegn på krapp sjø ved punktet (fjord_chop()).
    # Tegnet gjør bare timen usikker (S32 e), det er ikke «kildene uenige».
    if source == "barentswatch" and fjord_chop(hour, spot):
        uncertain = True
    # S29 c del 2 (S40: på for Unstad): omregningen er et anslag, ikke modellens egen deling - høyst 3 poeng.
    if long_sea_hour is not None:
        uncertain = True
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
    # 1-stjernes toleranse. Energifaktoren er UNIVERSELL (alle spots) fra
    # 06.10.2026. 17.11.2026: unntatt er spots med
    # no_energy_rule i spots.json (bare Breivikeidet) - se energy_factor().
    #
    # 07.10.2026, Theodors oppgave (surf-forecast-sammenligning): ENERGIEN
    # alene (ikke surfehøyden, se breaking_height() over - uendret, bruker
    # fortsatt `period`) regnes med topperiode når den finnes, ellers
    # middelperioden omregnet - se energy_period()/PEAK_PERIOD_FACTOR_DEFAULT.
    energy_period_value, energy_period_source = energy_period(period, hour.get("swell_peak_period"))
    energy_swell = energy_kj(hour.get("swell_offshore"), energy_period_value)
    energy_total = energy_kj(hour.get("height_offshore"), energy_period_value)
    energy_factor_value = energy_factor(spot, energy_swell)
    # 09.10.2026, Theodors ordregel ved 0 stjerner og minst 0,8 m surfehøyde
    # (se docs/js/app.js zeroCause()): appen trenger å vite hva som faktisk
    # trekker MEST - energifaktoren, vinden, tidevannet, de lokale reglene
    # eller kappingen ved usikkert varsel/uenige kilder. Den vanlige
    # bokføringen (faded_wind/faded_tide = det vinden og tidevannet tok av
    # det som var IGJEN etter energifaktoren) egner seg ikke til det: med
    # lite energi ville energien alltid "vinne" selv når vinden er det
    # største problemet (fysikk-kontrollør 09.10.2026). Derfor ett eget,
    # rent visningsfelt `zero_losses` der hver faktor måles ALENE mot
    # potensialet FØR energifaktoren (vind/tidevann: min(potensial, straff)),
    # energi = før − etter, lokale regler = det de faktisk tok av det som var
    # igjen, kapping = det kappingen tok. Stjernene er uendret.
    faded_cap = ((disagree_cap - 1) if disagree_cap is not None
                 else (capped_from - 3) if capped_from is not None else 0)
    potential_before_energy = potential
    if energy_factor_value < 0.999:
        potential = int(potential * energy_factor_value + 1e-9)
    faded_energy = potential_before_energy - potential

    # 15.10.2026: 5-stjerners-porten (del A) - bare når alt annet gir 4
    five_open, five_fails = False, []
    if potential == 4:
        five_open, five_fails = five_star_swell_gate(
            hour, spot, source=source, bw_detail=bw_detail, surf_height=surf_height, period=period,
            energy_swell=energy_swell, energy_factor_value=energy_factor_value, dir_hit=dir_hit,
            uncertain=uncertain, sources_disagree=sources_disagree)
        if five_open:
            potential = 5

    wind_speed, wind_dir, gust = hour.get("wind_speed"), hour.get("wind_dir"), hour.get("gust")
    wt = wind_type(wind_dir, spot)
    # 15.10.2026 (Theodors regler 1-4): vindstraffen er en glatt kurve (float), dempet av
    # svellets energi, kastene teller høyst 2 m/s, og en strengere LOKAL vindregel
    # erstatter den generelle (max), legges ikke oppå. Alle fradrag summeres som
    # flyttall og rundes først til slutt (0,5 opp) - stjernene er fortsatt hele.
    wind_parts = wind_penalty_parts(wind_speed, wind_dir, spot, gust, energy_swell)
    wp_general = wind_parts["pen"]
    local_tide_raw, local_wind_raw, local_rules_lines = local_rules_penalty(hour, spot, wt, wind_speed, potential)
    wp = max(wp_general, local_wind_raw)
    # 23.11.2026 (bw_tillit, feiljegeren S27 funn 2): for en fjord-spot tar vinden alt når den tar gap-grensa bort
    # (gap_blocked_by_wind(): fra 8 m/s pålands, skrått pålands eller ukjent retning), i begge soner. Høyden som
    # vises er andelshøyden (spot_height()), ikke 0,0.
    fjord_wind_block = fjord_in_window(hour, spot) and gap_blocked_by_wind(hour, spot)
    if fjord_wind_block:
        wp = max(wp, potential)
    tide_pen = tide_penalty(hour.get("tide"), spot)
    raw_solid = potential - wp - tide_pen - local_tide_raw
    solid = max(0, min(potential, math.floor(raw_solid + 0.5)))
    # del B: den femte stjernen er sprø - holdes tilbake hvis vinden eller tidevannet ikke er rent
    five_lost = None
    if potential == 5:
        five_lost = five_star_losses(hour, spot, wind_parts, local_wind_raw, tide_pen, local_tide_raw)
        if five_lost and solid == 5:
            solid = 4
    # bokføring i hele stjerner (det som vises som blasse stjerner): «uten vind» er det samme
    # regnestykket uten vindleddet (fysikk-kontrollør 15.10.2026: en egen avrunding av vinden
    # kunne gi «(4 uten vind)» når tidevannsregelen alene tok stjernen), så vind først, så
    # tidevann, så lokalt
    lost_total = potential - solid
    without_wind = max(0, min(potential, math.floor(potential - tide_pen - local_tide_raw + 0.5)))
    if five_lost == "tide" and without_wind == 5:
        without_wind = 4   # den femte stjernen holdes tilbake av tidevannet også uten vind
    lost_wind = max(0, without_wind - solid)
    tide_cap = tide_pen if five_lost != "tide" else max(1, tide_pen)
    # 23.11.2026 (S28, ja fra Theodor i svar.md 23.11.2026; feiljegeren 22.11.2026: Breivikeidet 22.11 kl. 09-10Z,
    # potensial 2, vinden −0,3 og tidevannsregelen −0,45 tok ett poeng sammen, og appen sa «(2 uten vind)»): når
    # verken vinden eller tidevannet ALENE tar poenget, får det største fradraget skylda. Uavgjort: vinden, som før.
    # Poengene er de samme. Tidevannets del går som før først til den vanlige tidevannsregelen (faded_tide), så til
    # de lokale reglene (local_rules.stars_lost). Ikke når det femte poenget holdes tilbake (five_lost).
    # 24.11.2026 (fysikk-kontrolløren, vilkår 1): ordet følger den samme bokføringen. low_reason og «og sterk vind» i
    # regnestykket leser lost_wind og lost_tide ETTER omfordelingen, så en time der tidevannet får poenget ikke heter
    # «blown_out» mens tapet vises som tidevann (Breivikeidet, fralandsvind 10,2-12 m/s: appen sa «Blåst ut»).
    wind_alone_lost = potential - max(0, min(potential, math.floor(potential - wp + 0.5)))
    if (lost_wind > 0 and five_lost is None and wind_alone_lost == 0 and without_wind == potential
            and tide_pen + local_tide_raw > wp):
        lost_wind = 0
    lost_tide = min(lost_total - lost_wind, tide_cap)
    local_extra_stars = lost_total - lost_wind - lost_tide
    solid_before_local = solid + local_extra_stars
    # 19.11.2026 (fysikk-kontrolløren, forslag S22): mangler vindstyrken, er det faste poenget et fradrag for et
    # usikkert varsel og ikke for vind vi har sett. Det bokføres under "cap", så ordet ved 0 poeng blir «Ikke surfbart
    # nå» og ikke «Blåst ut». Stjernene og faded_wind er uendret.
    wind_alone = min(potential_before_energy, math.floor(wp + 0.5))
    zero_losses = {
        "energy": faded_energy,
        "wind": 0 if wind_speed is None else wind_alone,
        "tide": min(potential_before_energy, tide_pen),
        "local": local_extra_stars,
        "cap": faded_cap + (wind_alone if wind_speed is None else 0),
    }
    local_rules_source = None
    if spot.get("local_rules"):
        src = spot["local_rules"].get("source", "")
        local_rules_source = src.split(",")[0].strip() if src else None

    low_reason = classify_low_rating(hour, spot, source, bw_detail, low_hs, surf_height, dir_hit,
                                      potential, lost_wind, lost_tide, solid, blown_out, energy_swell,
                                      share_used=share_used)

    breakdown = build_breakdown(
        hour, spot, h, source, bw_detail, hb, surf_factor, surf_height,
        surf_height_sets, low_hs, blown_out, hb_damping, period, hs, ps, dir_hit,
        wind_speed, wind_dir, gust, wt, wp, hour.get("tide"), tide_pen,
        potential, solid, lost_wind, lost_tide, uncertain,
        sources_disagree, capped_from, disagree_cap, energy_swell, energy_factor_value,
        energy_period_value, energy_period_source,
        five_open=five_open, five_fails=five_fails if potential_before_energy >= 4 or potential >= 4 else None, five_lost=five_lost,
        wind_took_points=lost_wind > 0 or zero_losses["wind"] > 0,
        tide_level_line=tide_level_penalty(hour, spot, potential)[1] or local_tide_prefer_line(spot, local_rules_lines),
        fjord_wind_block=fjord_wind_block, tide_lost_local=local_extra_stars,
    )

    result = {
        "stars": solid,
        "faded": lost_wind + lost_tide,
        "faded_wind": lost_wind,
        "faded_tide": lost_tide,
        # bare visning (hva som trekker mest ved 0 stjerner), se over
        "zero_losses": zero_losses,
        "wind_type": wt,
        # spotens egen vindgrense (bare spots med egen vindkurve) - se wind_calm_ms(). Bare tekst og visning.
        **({"wind_calm_ms": wind_calm_ms(spot)} if wind_calm_ms(spot) is not None else {}),
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
        "sources_disagree_reason": disagree_reason(hour, dir_hit, bw_detail,
                                                   fjord=fjord_in_window(hour, spot)) if sources_disagree else None,
        "swell_share": round(bw_detail["swell_share"], 3) if bw_detail else None,
        # Periodefaktoren slik ratingen brukte den, og hva den bygger på ("bw",
        # "ute") - appen viser riktig ledd uten å regne selv.
        "bw_period_factor": round(bw_detail["bw_period_factor"], 3) if bw_detail else None,
        "bw_period_basis": bw_detail.get("bw_period_basis") if bw_detail else None,
        # Sann når høyden er løftet til gap-grensa (se gap_floor()).
        "gap_floor": gap_used,
        # S29 c del 2 (S40: på for Unstad): feltet finnes bare når regelen har regnet om timen (long_sea()) - det
        # svellet ratingen faktisk brukte, så appen og læringen (exposure_learn) kan se det. Aldri med bryteren av.
        # S40: height_offshore er GFS sin totalhøyde (nevneren i svellandelen), short_peak sier at toppen ved punktet
        # var kort i timen (M4), og gfs_swell er svell-delen slik GFS skilte den ut (det timen selv har lagret).
        # publish.vis_lang_sjo() bruker dette til å vise den lange sjøen i appen i stedet for svell-delen.
        **({"long_sea": {"swell_offshore": round(long_sea_hour["swell_offshore"], 2), "period": long_sea_hour["period"],
                         "dir_offshore": long_sea_hour["dir_offshore"],
                         "height_offshore": round(long_sea_hour["height_offshore"], 2),
                         "short_peak": bw_detail is not None and bw_detail.get("bw_period_basis") == "lang_sjo_kort_topp",
                         "gfs_swell": long_sea_gfs}} if long_sea_hour is not None else {}),
        # 23.11.2026 (svar.md 23.11.2026 kl. 14.05): sann når høyden ER andelshøyden for en fjord-spot (svell ute ×
        # andel × kantfaktor, se fjord_share_applied()). Feltet finnes bare da, så kyst-spots har det aldri. Det er
        # et eget felt fordi "gap_floor" over er usann når vinden har tatt gap-grensa bort og i reserven under 7 s:
        # for en fjord-spot er høyden andelshøyden også da. Bare til visning («anslag, ikke kystmodellens tall»).
        **({"share_height": True} if share_used else {}),
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
        # 07.10.2026, Theodors oppgave: hvilken periode energien over faktisk
        # ble regnet med ("topp" = ekte topperiode, "omregnet" = middelperiode
        # × PEAK_PERIOD_FACTOR_DEFAULT, None = ingen periode i det hele
        # tatt) - til fremtidig kalibrering (data/benchmark/), ikke bare
        # synlig i breakdown-teksten.
        "energy_period_source": energy_period_source,
        # Myke lokale regler (Magnus, se CLAUDE.md "Lokalkunnskap") - None
        # når spoten ikke har local_rules. "stars_lost" er ETT tall: det det
        # LOKALE tidevannsfradraget tok etter avrunding (15.10.2026: den lokale
        # vindregelen erstatter den generelle vindstraffen når den er strengere,
        # og bokføres da under "wind", ikke her - se local_rules_penalty()) - energi
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
    # S40: regelen gjelder bare når den gir FLERE poeng enn den vanlige regningen. Gir den like mange eller færre
    # (taket på 3, flat-sperren etter M4, surfehøyde over ideal_height), står timen akkurat som uten regelen: ingen
    # time skifter bare ord eller høyde, og ingen går ned.
    # K2 (fysikk-kontrolløren 25.11.2026): treffet merkes (long_sea_seen), så læringen kan hoppe over timen også da.
    # Svellet i timen er fortsatt det lille GFS skilte ut, mens høyden ved punktet er den lange sjøen. Resten av
    # svaret er den vanlige regningen, urørt. Appen leser ikke merket (publish.DETAIL_EXCLUDE).
    if long_sea_base is not None and result["stars"] <= long_sea_base["stars"]:
        return {**long_sea_base, "long_sea_seen": True}
    return result
