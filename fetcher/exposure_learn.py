"""Del B, 27.09.2026 (ROADMAP oppgave 4): eksponering per retning LÆRT fra
BarentsWatch sine egne, ekte punktmålinger - erstatter etter hvert av seg
selv det rent geometriske utgangspunktet i del C (exposure_baseline.py) der
det er nok data til å stole på det. Se README "Eksponering per retning".

Metode, kort:
1. Par: én BarentsWatch-time per spot og tidspunkt der svellet ute er ekte
   og stort nok til at forholdet sier noe fornuftig (se exposure_pairs_for_run()).
   Lagres i data/exposure.json, 120 døgn.
2. Bøtter: 10 grader hver (36 per spot). En bøtte er "lært" med minst 6 par
   spredt over minst 2 døgn (medianen av parenes forhold).
3. To periodegrupper (kort < 10 s, lang >= 10 s ute) - diffraksjon avhenger
   av bølgelengden (samme fysikk som exposure_baseline.py sin skyggelengde-
   formel, L = W²/λ), så et smalt gap kan slippe kortere periode lettere
   gjennom enn lengre. Læres og normaliseres HVER FOR SEG.
4. Normalisering: forholdet i en bøtte er egentlig transfer × eksponering
   (BarentsWatch måler den ekte, kombinerte effekten). For å skille dem må vi
   vite hvor eksponeringen er ca. 1,0 - bruker bøtter der den GEOMETRISKE
   modellen (del C sin rå kurve) sier fri sikt i alle 10 gradene, og krever
   minst 3 slike lærte "referansebøtter" i samme periodegruppe. Transfer =
   medianen av alle par-forhold i akkurat disse referansebøttene. Lært
   eksponering i en bøtte = bøttens median-forhold / transfer.
   Kort periode kan låne referansebøttene og transferen fra lang periode når
   den ikke har 3 egne - lang periode låner ALDRI fra kort (kort er mer
   utsatt for lokal vindsjø og mindre representativ for selve geometrien).
5. Blanding med geometrien: vekt = par-i-bøtte / (par-i-bøtte + 10) - få par
   gir nesten bare geometri, mange par gir nesten bare lært verdi.
"""
import datetime as dt
from statistics import median

from rating import in_sector, PERIOD_SHORT_MAX

BUCKET_DEG = 10
N_BUCKETS = 360 // BUCKET_DEG
MIN_PAIRS_PER_BUCKET = 6
MIN_DAYS_PER_BUCKET = 2
MIN_REFERENCE_BUCKETS = 3
REFERENCE_RAW_MIN = 0.999  # geometrisk rå eksponering, hele bøtta, for å regnes som "fri sikt"
MAX_AGE_DAYS = 120
BLEND_HALF_LIFE_PAIRS = 10  # vekt lært = par / (par + denne)


def bucket_of(d):
    """0-35, bøtte-indeks for retning d (grader, 0 = nord)."""
    return int(d // BUCKET_DEG) % N_BUCKETS


def period_group(period):
    """'kort' under 10 s, 'lang' 10 s og over. None hvis periode mangler -
    parene forkastes da (se exposure_pairs_for_run)."""
    if period is None:
        return None
    return "kort" if period < PERIOD_SHORT_MAX else "lang"


def exposure_pairs_for_run(hours, run_id):
    """Kalibreringspar for denne kjøringen: bare RÅ (ikke interpolerte)
    BarentsWatch-timer med et stort nok, overveiende ekte svell ute til at
    forholdet bw_height*swell_share / swell_offshore sier noe fornuftig om
    hvor mye av svellet som når punktet fra akkurat denne retningen. Aldri
    timer der kildene er uenige (sources_disagree) - de er per definisjon
    ikke til å stole på."""
    pairs = []
    for h in hours:
        if h.get("height_source") != "barentswatch" or h.get("bw_interpolated"):
            continue
        if h.get("sources_disagree"):
            continue
        swell = h.get("swell_offshore")
        share = h.get("swell_share")
        dir_off = h.get("dir_offshore")
        bw = h.get("bw_height")
        period = h.get("period")
        pg = period_group(period)
        if None in (swell, share, dir_off, bw, pg):
            continue
        if swell < 0.5 or share < 0.7:
            continue
        pairs.append({
            "t": h["t"], "bucket": bucket_of(dir_off), "period_group": pg,
            "ratio": round((bw * share) / swell, 4), "run": run_id,
        })
    return pairs


def merge_pairs(existing, new_pairs, now):
    """Behold nyeste kjøring per tidspunkt (dedup), fjern par eldre enn 120 døgn."""
    by_time = {p["t"]: p for p in existing}
    for p in new_pairs:
        by_time[p["t"]] = p
    cutoff = now - dt.timedelta(days=MAX_AGE_DAYS)
    return [p for p in by_time.values() if dt.datetime.fromisoformat(p["t"].replace("Z", "+00:00")) >= cutoff]


def _bucket_groups(pairs, pg):
    """{bøtte: [par]} for én periodegruppe."""
    out = {}
    for p in pairs:
        if p["period_group"] != pg:
            continue
        out.setdefault(p["bucket"], []).append(p)
    return out


def learned_bucket_value(bucket_pairs):
    """Median-forhold for en bøtte, eller None hvis for få par eller for
    få døgn (se MIN_PAIRS_PER_BUCKET/MIN_DAYS_PER_BUCKET)."""
    if len(bucket_pairs) < MIN_PAIRS_PER_BUCKET:
        return None
    days = {p["t"][:10] for p in bucket_pairs}
    if len(days) < MIN_DAYS_PER_BUCKET:
        return None
    return median(p["ratio"] for p in bucket_pairs)


def geometric_reference_buckets(raw_geometry):
    """Hvilke bøtter (0-35) den GEOMETRISKE modellen (del C sin rå kurve,
    360 tall) sier har fri sikt i HELE bøtta - brukes som anker til å skille
    transfer fra eksponering (se modul-docstringen, punkt 4)."""
    if not raw_geometry:
        return set()
    out = set()
    for b in range(N_BUCKETS):
        lo = b * BUCKET_DEG
        if all(raw_geometry[lo + i] >= REFERENCE_RAW_MIN for i in range(BUCKET_DEG)):
            out.add(b)
    return out


def normalize_period_group(pairs, pg, raw_geometry, borrow_from=None):
    """Lærte, normaliserte eksponeringsverdier per bøtte for én periodegruppe,
    og transferen de ble normalisert mot. Returnerer
    (bøtte->lært_eksponering, transfer, referansebøtter_brukt) - alle tomme/
    None hvis normalisering ikke er mulig (færre enn MIN_REFERENCE_BUCKETS
    lærte referansebøtter, og ingen borrow_from å låne fra).

    borrow_from: resultatet fra normalize_period_group() for 'lang', brukt av
    'kort' når den ikke har nok egne referansebøtter (se modul-docstringen,
    punkt 4 - "kort kan låne fra lang, ikke omvendt"). 'lang' sender ALDRI
    inn en borrow_from selv."""
    groups = _bucket_groups(pairs, pg)
    geo_ref = geometric_reference_buckets(raw_geometry)
    learned_in_ref = {b for b in geo_ref if b in groups and learned_bucket_value(groups[b]) is not None}

    if len(learned_in_ref) >= MIN_REFERENCE_BUCKETS:
        ref_pairs = [p for b in learned_in_ref for p in groups[b]]
        transfer = median(p["ratio"] for p in ref_pairs)
        used_ref = learned_in_ref
    elif borrow_from is not None and borrow_from[1] is not None:
        transfer = borrow_from[1]
        used_ref = borrow_from[2]
    else:
        return {}, None, set()

    learned = {}
    for b, bucket_pairs in groups.items():
        v = learned_bucket_value(bucket_pairs)
        if v is not None:
            learned[b] = max(0.0, min(1.0, v / transfer))
    return learned, transfer, used_ref


def bucket_pair_counts(pairs, pg):
    """{bøtte: antall par} for én periodegruppe - til blend_curve() sin vekt
    og til STATUS.md/Logger-fanen sin rapportering av hvor mye som er lært."""
    groups = _bucket_groups(pairs, pg)
    return {b: len(p) for b, p in groups.items()}


def blend_curve(learned_by_bucket, geometric_smoothed, pair_counts):
    """360 tall: blander lært eksponering (per bøtte) med den glattede,
    geometriske kurven fra del C. Vekt lært = par / (par + BLEND_HALF_LIFE_PAIRS)
    - 0 par gir ren geometri (uendret av del B), mange par nærmer seg den
    lærte verdien. Bøtter uten noe lært (under MIN_PAIRS_PER_BUCKET) har
    pair_counts 0 der og forblir derfor ren geometri automatisk."""
    out = list(geometric_smoothed)
    for b in range(N_BUCKETS):
        learned = learned_by_bucket.get(b)
        n = pair_counts.get(b, 0)
        if learned is None or n <= 0:
            continue
        weight = n / (n + BLEND_HALF_LIFE_PAIRS)
        lo = b * BUCKET_DEG
        for i in range(BUCKET_DEG):
            idx = lo + i
            out[idx] = weight * learned + (1 - weight) * geometric_smoothed[idx]
    return out


def override_removal_suggestions(overrides, learned_short, learned_long):
    """exposure_override sett i spots.json der en LÆRT verdi (kort eller
    lang periode, hvilken som helst) i bøttene overriden dekker allerede
    ligger under taket - et forslag om at overriden kanskje ikke trengs
    lenger, IKKE en automatisk fjerning (se ROADMAP oppgave 4)."""
    out = []
    for o in overrides or []:
        sector = [o["from"], o["to"]]
        covered = [b for b in range(N_BUCKETS)
                   if any(in_sector((b * BUCKET_DEG + i) % 360, sector) for i in range(BUCKET_DEG))]
        learned_values = [learned_short.get(b) for b in covered if learned_short.get(b) is not None]
        learned_values += [learned_long.get(b) for b in covered if learned_long.get(b) is not None]
        if learned_values and max(learned_values) < o["max"]:
            out.append({"from": o["from"], "to": o["to"], "cap": o["max"], "learned_max": round(max(learned_values), 3)})
    return out
