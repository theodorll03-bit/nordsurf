"""Tester Del B (eksponering lært fra BarentsWatch). Kjør: python fetcher/test_exposure_learn.py"""
import datetime as dt

from exposure_learn import (
    bucket_of, period_group, exposure_pairs_for_run, merge_pairs,
    learned_bucket_value, geometric_reference_buckets, normalize_period_group,
    bucket_pair_counts, blend_curve, override_removal_suggestions, MIN_PAIRS_PER_BUCKET,
)

# 1: bucket_of()
assert bucket_of(0) == 0
assert bucket_of(9) == 0
assert bucket_of(10) == 1
assert bucket_of(359) == 35
assert bucket_of(300) == 30
print("1: bucket_of(0/9/10/359/300)", bucket_of(0), bucket_of(9), bucket_of(10), bucket_of(359), bucket_of(300))

# 2: period_group()
assert period_group(9.9) == "kort"
assert period_group(10.0) == "lang"
assert period_group(15) == "lang"
assert period_group(None) is None
print("2: period_group(9.9/10/15/None)", period_group(9.9), period_group(10.0), period_group(15), period_group(None))

# 3: exposure_pairs_for_run() - filtrering
base_hour = {"t": "2026-09-27T00:00Z", "height_source": "barentswatch", "bw_interpolated": False,
             "sources_disagree": False, "swell_offshore": 2.0, "swell_share": 0.9,
             "dir_offshore": 295, "bw_height": 1.0, "period": 12}

def mk(**over):
    return {**base_hour, **over}

p_ok = exposure_pairs_for_run([mk()], "run1")
assert len(p_ok) == 1
assert p_ok[0]["bucket"] == bucket_of(295) and p_ok[0]["period_group"] == "lang"
assert p_ok[0]["ratio"] == round(1.0 * 0.9 / 2.0, 4)

assert exposure_pairs_for_run([mk(height_source="svell_ute")], "r") == []
assert exposure_pairs_for_run([mk(bw_interpolated=True)], "r") == []
assert exposure_pairs_for_run([mk(sources_disagree=True)], "r") == []
assert exposure_pairs_for_run([mk(swell_offshore=0.4)], "r") == []
assert exposure_pairs_for_run([mk(swell_share=0.6)], "r") == []
assert exposure_pairs_for_run([mk(period=None)], "r") == []
assert exposure_pairs_for_run([mk(dir_offshore=None)], "r") == []
print("3: exposure_pairs_for_run() filtrering ok, 1 gyldig par av 8 varianter")

# 4: merge_pairs() - dedup og 120-dagers grense
now = dt.datetime(2026, 9, 27, tzinfo=dt.timezone.utc)
old_pair = {"t": "2026-01-01T00:00Z", "bucket": 0, "period_group": "lang", "ratio": 0.5, "run": "old"}
existing = [old_pair, {"t": "2026-09-26T00:00Z", "bucket": 1, "period_group": "lang", "ratio": 0.4, "run": "r0"}]
new = [{"t": "2026-09-26T00:00Z", "bucket": 1, "period_group": "lang", "ratio": 0.6, "run": "r1"},
       {"t": "2026-09-27T00:00Z", "bucket": 2, "period_group": "lang", "ratio": 0.7, "run": "r1"}]
merged = merge_pairs(existing, new, now)
assert old_pair not in merged  # over 120 dager gammel
assert len(merged) == 2
assert next(p for p in merged if p["t"] == "2026-09-26T00:00Z")["ratio"] == 0.6  # nyeste kjøring vinner
print("4: merge_pairs() dedup + 120-dagers grense ok,", len(merged), "par igjen")

# 5: learned_bucket_value() - minst 6 par over minst 2 døgn
few = [{"t": f"2026-09-2{i}T00:00Z", "ratio": 0.5} for i in range(3)]
assert learned_bucket_value(few) is None
same_day = [{"t": "2026-09-20T0" + str(i) + ":00Z", "ratio": 0.5} for i in range(6)]
assert learned_bucket_value(same_day) is None  # nok par, men bare 1 døgn
enough = [{"t": "2026-09-20T00:00Z", "ratio": 0.4}, {"t": "2026-09-20T03:00Z", "ratio": 0.5},
          {"t": "2026-09-21T00:00Z", "ratio": 0.6}, {"t": "2026-09-21T03:00Z", "ratio": 0.5},
          {"t": "2026-09-22T00:00Z", "ratio": 0.5}, {"t": "2026-09-22T03:00Z", "ratio": 0.7}]
assert learned_bucket_value(enough) == 0.5
print("5: learned_bucket_value() for få par / 1 døgn / nok -", learned_bucket_value(few), learned_bucket_value(same_day), learned_bucket_value(enough))

# 6: geometric_reference_buckets()
geo = [1.0] * 360
geo[45] = 0.5  # ødelegger bøtte 4 (40-49)
refs = geometric_reference_buckets(geo)
assert 4 not in refs
assert 3 in refs and 5 in refs
assert len(refs) == 35
print("6: geometric_reference_buckets() ekskluderer bøtte 4, beholder 35 av 36")

# 7: normalize_period_group() - full normalisering, ingen låning nødvendig
geo_open = [1.0] * 360
for i in range(100, 110):
    geo_open[i] = 0.0  # bøtte 10 er IKKE geometrisk åpen - skal ikke telle som referanse,
                        # selv om den også får en lært verdi (læres for alle bøtter med nok par)
pairs_lang = []
for b in (0, 1, 2):  # 3 referansebøtter, transfer skal bli medianen av disse (0,6)
    for i in range(MIN_PAIRS_PER_BUCKET):
        day = 20 + i % 3
        pairs_lang.append({"t": f"2026-09-{day:02d}T0{i}:00Z", "bucket": b, "period_group": "lang", "ratio": 0.6})
for i in range(MIN_PAIRS_PER_BUCKET):  # bøtte 10: lavere forhold - skal bli lært eksponering < 1
    day = 20 + i % 3
    pairs_lang.append({"t": f"2026-09-{day:02d}T1{i}:00Z", "bucket": 10, "period_group": "lang", "ratio": 0.3})

learned_lang, transfer_lang, ref_lang = normalize_period_group(pairs_lang, "lang", geo_open)
assert transfer_lang == 0.6
assert ref_lang == {0, 1, 2}
assert abs(learned_lang[10] - 0.5) < 1e-9  # 0.3 / 0.6
assert abs(learned_lang[0] - 1.0) < 1e-9   # 0.6 / 0.6
print("7: normalize_period_group() 'lang', transfer", transfer_lang, "learned[10]", learned_lang[10])

# 7b: for få referansebøtter og ingen å låne fra -> ingen normalisering
learned_none, transfer_none, ref_none = normalize_period_group(pairs_lang[:MIN_PAIRS_PER_BUCKET], "lang", geo_open)
assert transfer_none is None and learned_none == {} and ref_none == set()
print("7b: normalize_period_group() med bare 1 referansebøtte -> ingen normalisering")

# 8: 'kort' låner fra 'lang' når den mangler egne referansebøtter
pairs_kort = []
for i in range(MIN_PAIRS_PER_BUCKET):  # bare 1 bøtte lært i 'kort' - ikke nok til egen normalisering
    day = 20 + i % 3
    pairs_kort.append({"t": f"2026-09-{day:02d}T2{i}:00Z", "bucket": 20, "period_group": "kort", "ratio": 0.45})
learned_kort, transfer_kort, ref_kort = normalize_period_group(pairs_kort, "kort", geo_open,
                                                                borrow_from=(learned_lang, transfer_lang, ref_lang))
assert transfer_kort == transfer_lang  # lånt fra lang
assert ref_kort == ref_lang
assert abs(learned_kort[20] - 0.75) < 1e-9  # 0.45 / 0.6
print("8: 'kort' låner transfer/referanse fra 'lang' - transfer", transfer_kort, "learned[20]", learned_kort[20])

# 8b: 'kort' med for lite EGET og INGEN å låne fra -> ingen normalisering
learned_kort_alone, transfer_kort_alone, _ = normalize_period_group(pairs_kort, "kort", geo_open)
assert transfer_kort_alone is None and learned_kort_alone == {}
print("8b: 'kort' uten nok egne bøtter og ingen borrow_from -> ingen normalisering")

# 8c: bucket_pair_counts()
counts_lang = bucket_pair_counts(pairs_lang, "lang")
assert counts_lang[0] == MIN_PAIRS_PER_BUCKET and counts_lang[10] == MIN_PAIRS_PER_BUCKET
assert 20 not in counts_lang  # bøtte 20 har bare 'kort'-par
print("8c: bucket_pair_counts()", counts_lang)

# 9: blend_curve() - 0 par gir ren geometri, mange par nærmer seg lært verdi
geo_curve = [1.0] * 360
learned_bucket = {5: 0.2}
no_pairs = blend_curve(learned_bucket, geo_curve, {})
assert no_pairs[55] == 1.0  # bøtte 5 = grader 50-59, ingen par -> uendret geometri
many_pairs = blend_curve(learned_bucket, geo_curve, {5: 990})  # vekt = 990/1000 = 0.99
assert abs(many_pairs[55] - (0.99 * 0.2 + 0.01 * 1.0)) < 1e-9
few_pairs = blend_curve(learned_bucket, geo_curve, {5: 6})  # vekt = 6/16 = 0.375
assert abs(few_pairs[55] - (0.375 * 0.2 + 0.625 * 1.0)) < 1e-9
print("9: blend_curve() 0/6/990 par ->", no_pairs[55], round(few_pairs[55], 3), round(many_pairs[55], 3))

# 10: override_removal_suggestions()
overrides = [{"from": 311, "to": 330, "max": 0.2}]
# bøtte 31 (310-319) og 32 (320-329) dekker sektoren - lært under taket i bøtte 32
learned_short_ov = {}
learned_long_ov = {32: 0.1}
sugg = override_removal_suggestions(overrides, learned_short_ov, learned_long_ov)
assert len(sugg) == 1 and sugg[0]["learned_max"] == 0.1
# ingen lært verdi i sektoren -> ikke noe forslag
assert override_removal_suggestions(overrides, {}, {}) == []
# lært verdi OVER taket -> ikke noe forslag (overriden trengs fortsatt)
assert override_removal_suggestions(overrides, {}, {32: 0.5}) == []
print("10: override_removal_suggestions() foreslår fjerning bare når lært < tak,", sugg)

print("Alle tester ok")
