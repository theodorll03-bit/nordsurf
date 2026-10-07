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
assert "## Samlet" in text and "## grunnlinje" in text and "## energi_tp" in text and "| grunnlinje |" in text and "SAMME saker" in text
print("6: rapport OK")
print("Alle tester ok")
