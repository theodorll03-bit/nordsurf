"""Tester for testlaben (fetcher/backtest.py). Kjør: python fetcher/test_backtest.py
Rask, uten nett: de faste sakene må holde i grunnlinja (samme sannhet som
test_rating.py), variantene må kjøre uten å krasje, og målene må regnes
riktig på et lite syntetisk sett."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest  # noqa: E402

# 1: grunnlinja holder alle faste observasjoner (CLAUDE.md) - det er selve
# forutsetningen for å bruke testlaben som dommer.
cases, results, ctx = backtest.run(["grunnlinje", "energi_tp"], logs=[])
base = results["grunnlinje"]["summary"]
assert base["fixed_failed"] == [], base["fixed_failed"]
assert base["evaluated"] == len(cases) >= 15
print(f"1: grunnlinje holder {base['fixed_hold']} faste observasjoner, surfehøyde-feil {base['surf_mae']} m, treff ±1 {base['hit1']}")

# 2: energi_tp evaluerer alle saker med Tp = gjennomsnitt × 1,25 (GFS for
# alt, trenger ikke WW3) og holder de faste observasjonene (energifaktoren er
# allerede mettet ved Unstads lokale terskler - ingen endring).
etp = results["energi_tp"]["summary"]
assert etp["evaluated"] == len(cases) and etp["fixed_failed"] == [], etp
assert all(x["r"]["_energy_period_factor"] == backtest.TP_FROM_MEAN for x in results["energi_tp"]["rows"])
print("2: energi_tp kjører på alle saker med Tp = gjennomsnitt × 1,25 og holder de faste observasjonene")

# 2b: grunnlinja på SAMME saker er regnet for hver variant, og syntetiske saker
# hoppes over av alle varianter som henter eksterne data for klokkeslettet.
assert results["energi_tp"]["baseline_same"]["evaluated"] == etp["evaluated"]
synthetic = [c["id"] for c in cases if c.get("synthetic")]
assert "farstadsanden_338" in synthetic
_, res2b, _ = backtest.run(["ww3_svell", "ww3_begge", "energi_ww3", "vind_korr"], logs=[])
for name, res in res2b.items():
    assert not any(x["case"]["id"] in synthetic for x in res["rows"]), name
    assert res["baseline_same"]["evaluated"] == res["summary"]["evaluated"], name
print("2b: grunnlinje-på-samme-saker finnes for alle varianter, syntetiske saker hoppes over")

# 3: varianter som trenger WW3/vind hopper over saker uten data (ikke krasj,
# ikke falske treff) - uten arkiv er alt "ikke evaluert".
_, res3, _ = backtest.run(["ww3_svell", "ww3_begge", "energi_ww3", "vind_korr"], logs=[])
for name in ("ww3_svell", "ww3_begge", "energi_ww3", "vind_korr"):
    r = res3[name]
    if not ctx["ww3"] and name in ("ww3_svell", "ww3_begge", "energi_ww3"):
        assert r["summary"]["evaluated"] == 0 and r["skipped"] == len(cases), name
    if not ctx["wind"] and name == "vind_korr":
        assert r["summary"]["evaluated"] == 0 and r["skipped"] == len(cases), name
print("3: WW3-/vind-varianter hopper over saker uten data i stedet for å gjette")

# 3b: laert_eksponering (Theodor 14.10.2026, punkt 2) - del B koblet inn i
# varianten, skyggemodus i grunnlinja. Uten lærte bøtter er den identisk med
# grunnlinja; med syntetiske par (samme som test_pipeline 9) får Unstad del B
# sin transfer (0,6) og den lærte kurven - grunnlinja ikke.
import tempfile, os
import fetch  # noqa: E402
assert fetch.EXPOSURE_LEARNED_IN_RATING is False
_, res3b, ctx3b = backtest.run(["grunnlinje", "laert_eksponering"], logs=[])
same = res3b["laert_eksponering"]
assert same["summary"]["evaluated"] == len(cases) and same["summary"]["fixed_failed"] == []
base_rows = {x["case"]["id"]: x["r"] for x in res3b["grunnlinje"]["rows"]}
if not fetch.EXPOSURE_LEARNED.exists() or all(v["lang"] == 0 and v["kort"] == 0 for v in ctx3b["laert"].values()):
    assert all((x["r"]["stars"], x["r"]["surf_height"]) == (base_rows[x["case"]["id"]]["stars"], base_rows[x["case"]["id"]]["surf_height"]) for x in same["rows"]), "uten lærte bøtter skal varianten være lik grunnlinja"
spots3b = backtest.load_spots()
expo3b = json.loads(backtest.EXPOSURE_BASELINE.read_text(encoding="utf-8"))
def _pairs(bucket, ratio, n=6):
    return [{"t": f"2026-09-{20+i%3:02d}T{(bucket+i) % 24:02d}:00Z", "bucket": bucket, "period_group": "lang", "ratio": ratio} for i in range(n)]
fx3b = {"unstad": _pairs(26, 0.6) + _pairs(27, 0.6) + _pairs(28, 0.6) + _pairs(31, 0.3)}
sp_on = backtest.prepare_spot("unstad", spots3b, expo3b, {}, {}, exposure_learned=fx3b, learned_exposure_active=True)
sp_off = backtest.prepare_spot("unstad", spots3b, expo3b, {}, {}, exposure_learned=fx3b)   # None = som produksjonen (skygge)
assert sp_on["transfer_source"] == "eksponering" and sp_on["transfer"] == 0.6 and "exposure_smoothed_lang" in sp_on
assert sp_off["transfer_source"] != "eksponering" and "exposure_smoothed_lang" not in sp_off
assert sp_on["_learned_buckets"] == {"lang": 4, "kort": 0, "par": 24} == sp_off["_learned_buckets"]
rep3b = backtest.report(cases, res3b, ctx3b)
assert "laert_eksponering: del B kjører i SKYGGEMODUS" in rep3b and "Lærte bøtter lang/kort (par) per spot: " in rep3b
print("3b: laert_eksponering = grunnlinja uten lærte bøtter; med syntetiske par kobles del B inn bare i varianten, rapporten sier hva som er lært")

# 4: judge() - stjernegrenser, surfehøyde-toleranse, ±1-treff og benchmark-avvik.
c = {"expect": {"stars_min": 3, "surf_m": 2.4, "size_m": 2.4, "stars_obs": 4}}
j = backtest.judge(c, {"stars": 3, "surf_height": 2.6})
assert j["holds"] is True and j["surf_err"] == 0.2 and j["hit1"] is True
j = backtest.judge(c, {"stars": 2, "surf_height": 2.4})
assert j["holds"] is False and j["hit1"] is False
j = backtest.judge({"expect": {"stars_max": 1, "low_reason": "treffer_ikke"}}, {"stars": 1, "surf_height": 0.9, "low_reason": "flat"})
assert j["holds"] is False
jb = backtest.judge({"expect": {"stars": 3, "surf_height_m": 1.0}, "benchmark": True}, {"stars": 4, "surf_height": 1.3})
assert jb["bench_dstars"] == 1 and jb["bench_dm"] == 0.3
# intervall '4-5 stjerner': 3 er én stjerne fra 4 (treff), 2 er to fra (bom), 5 er innenfor (avvik 0)
ji = backtest.judge({"expect": {"stars_min": 3, "stars_obs": [4, 5]}}, {"stars": 3, "surf_height": 1.2})
assert ji["hit1"] is True and ji["star_bias"] == -1
assert backtest.judge({"expect": {"stars_obs": [4, 5]}}, {"stars": 2, "surf_height": 1.0})["hit1"] is False
assert backtest.judge({"expect": {"stars_obs": [4, 5]}}, {"stars": 5, "surf_height": 1.0})["star_bias"] == 0
# manglende surfehøyde er None, ikke 0 (og ikke et "perfekt treff" mot flatt)
jn = backtest.judge({"expect": {"stars_max": 0, "size_m": 0.0}}, {"stars": 0, "surf_height": None})
assert jn["surf_err"] is None
s = backtest.summarize([{"case": {"id": "a"}, "j": {"holds": True, "surf_err": 0.1, "hit1": True}},
                        {"case": {"id": "b"}, "j": {"holds": False, "surf_err": 0.3, "hit1": False}}])
assert s["fixed_hold"] == "1/2" and s["fixed_failed"] == ["b"] and s["surf_mae"] == 0.2 and s["hit1"] == "1/2"
s2 = backtest.summarize([{"case": {"id": "a"}, "r": {}, "j": {"holds": True, "surf_err": None, "hit1": True, "star_bias": -1}},
                         {"case": {"id": "b"}, "r": {}, "j": {"holds": True, "surf_err": 0.3, "hit1": False, "star_bias": -2}}])
assert s2["surf_mae"] == 0.3 and s2["surf_n"] == 1 and s2["star_bias"] == -1.5
print("4: judge()/summarize() regner grenser, feil og treff riktig")

# 5: log_cases() bygger saker av loggenes egne lagrede inndata, og
# benchmark_cases() bruker inndata-arkivet.
logs = [{"id": "abc12345", "spot": "unstad", "t": "2026-09-26T12:45:00.000Z", "stars": 4, "size": "Over hodet", "type": "observed",
         "bwHeight": 0.9, "bwDir": 294.8, "bwPeriod": 15.0, "swellOffshore": 3.48, "dirOffshore": 300, "forecastPeriod": 15, "forecastStars": 4}]
lc = backtest.log_cases(logs)
assert len(lc) == 1 and lc[0]["t"] == "2026-09-26T12:00Z" and lc[0]["expect"] == {"stars_obs": 4, "size_m": 2.4} and lc[0]["hour"]["bw_height"] == 0.9
bc = backtest.benchmark_cases({"unstad": {"2026-10-07T12:00Z": {"bw_height": 1.0, "period": 10}}})
assert bc == [] or all(b.get("hour") is not None for b in bc)
print("5: log_cases()/benchmark_cases() OK")

# 6: rapporten er gyldig markdown med samlet tabell og én tabell per variant.
text = backtest.report(cases, results, ctx)
assert "## Forbehold" in text and "Uavhengige saker" in text and "Faste observasjoner (justeringsgrunnlag" in text and "## grunnlinje" in text and "## energi_tp" in text and "| grunnlinje |" in text and "SAMME saker" in text
assert results["grunnlinje"]["summary_fixed"]["evaluated"] == 15 and results["grunnlinje"]["summary_indep"]["evaluated"] == 0
print("6: rapport OK")

# 7: WW3-arkivets verdisperre: periode 0 (kildens "0 s"-mønster) og fyllverdier
# blir None, og en partisjon uten periode er fraværende - aldri "0 m svell".
import ww3_archive  # noqa: E402
assert ww3_archive.sane("ptp1", 0.0) is None and ww3_archive.sane("ptp1", 0.5) is None and ww3_archive.sane("ptp1", 11.2) == 11.2
assert ww3_archive.sane("phs1", 9.97e36) is None and ww3_archive.sane("pdir0", 361) is None and ww3_archive.sane("hs", float("nan")) is None
row = ww3_archive.drop_empty_partitions({"hs": 2.0, "dir": 250.0, "tp": 11.0, "phs0": 0.0, "pdir0": 180.0, "ptp0": None, "phs1": 2.0, "pdir1": 250.0, "ptp1": 11.0})
assert row["phs0"] is None and row["pdir0"] is None and row["phs1"] == 2.0
assert ww3_archive.index_of([__import__("datetime").datetime(2026, 10, 7, h, tzinfo=__import__("datetime").timezone.utc) for h in range(0, 12)],
                            __import__("datetime").datetime(2026, 10, 7, 6, tzinfo=__import__("datetime").timezone.utc)) == 6
print("7: WW3-verdisperre, tomme partisjoner og tidsakse-oppslag OK")

# 8: Unstads myke tidevannsregel (Lofoten Surfsenter, 09.11.2026 - Theodors ja 10.11.2026).
# To av de faste observasjonene var gode økter PÅ HØYVANN (26.09 kl. 14:45 og 28.09 ca. kl. 13).
# På høyvann koster regelen høyst én stjerne, lav og middels koster ingenting (samme tall som
# uten regelen), og en femte stjerne krever lav eller middels vannstand. Ingen fast observasjon
# kommer under kravet sitt på høyvann. Det er 28.09 (krav 3) som holder regelen myk: med
# fradrag 1,0 faller den til 2 - 26.09 holder 4 også da.
import rating  # noqa: E402
sp8 = backtest.prepare_spot("unstad", backtest.load_spots(), json.loads(backtest.EXPOSURE_BASELINE.read_text(encoding="utf-8")), {}, {})
assert sp8["local_rules"]["tide_prefer"] == ["lav", "middels"] and sp8["local_rules"]["tide_penalty_high"] == 0.5
uten8 = dict(sp8, local_rules={k: v for k, v in sp8["local_rules"].items() if not k.startswith("tide_")})
hard8 = dict(sp8, local_rules=dict(sp8["local_rules"], tide_penalty_high=1.0))
under_hard8 = []
for c8 in (c for c in backtest.fixed_cases() if c["spot"] == "unstad"):
    st8 = {s: rating.rate(dict(c8["hour"], tide={"state": s}), sp8)["stars"] for s in ("lav", "middels", "høy")}
    for8 = rating.rate(dict(c8["hour"], tide={"state": "høy"}), uten8)["stars"]
    assert st8["lav"] == st8["middels"] == for8 and for8 - 1 <= st8["høy"] <= st8["lav"] and st8["høy"] < 5, (c8["id"], st8, for8)
    assert st8["høy"] >= c8["expect"]["stars_min"], (c8["id"], st8)
    if c8["id"] == "unstad_2609":
        assert st8["høy"] >= 4 and rating.rate(dict(c8["hour"], tide={"state": "høy"}), hard8)["stars"] >= 4, st8
    if rating.rate(dict(c8["hour"], tide={"state": "høy"}), hard8)["stars"] < c8["expect"]["stars_min"]:
        under_hard8.append(c8["id"])
assert under_hard8 and all(i.startswith("unstad_2809") for i in under_hard8), under_hard8
print(f"8: Unstads tidevannsregel er myk - høyvann koster høyst én stjerne og ingen fast observasjon faller under kravet (med fradrag 1,0 ville {len(under_hard8)} timer 28.09 falt) OK")
print("Alle tester ok")
