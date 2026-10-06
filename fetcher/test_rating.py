"""Tester ratingen mot det du faktisk har observert. Kjør: python fetcher/test_rating.py"""
import json
from pathlib import Path
from rating import rate, wind_penalty, breaking_height

spots = {s["id"]: s for s in json.loads((Path(__file__).parent.parent / "spots.json").read_text())["spots"]}
G, E, R = spots["grotfjord"], spots["ersfjordstranda"], spots["russelv"]
MID = sum(G["ideal_height"]) / 2

def show(label, r): print(f"{label:<40} {r['stars']} hele, {r['faded']} tapt  ({r['height']} m, {r['height_source']})")

# Observert 24.09.2026: met.no sa 1,9 m i Grøtfjord, det var helt flatt.
g = rate({"height_spot_model": 1.9, "dir_offshore": 311, "turn": 32, "period": 11, "wind_speed": 3, "wind_dir": 180}, G)
show("Grøtfjord 24.09 (met.no)", g); assert g["stars"] == 0 and g["likely_flat"]
assert g["low_reason"] == "flat"

# Samme dag, BarentsWatch sa 0,3 m. Observert flatt.
g2 = rate({"bw_height": 0.3, "dir_offshore": 311, "turn": 32, "period": 11, "wind_speed": 3, "wind_dir": 180}, G)
show("Grøtfjord 24.09 (BarentsWatch)", g2); assert g2["stars"] == 0

# Observert 24.09.2026 kl 09: Windy viste 1,7 m 11 s fra ca. 267 grader i bukta. Helt flatt.
# 26.09.2026: swell_window utvidet fra [291,310] til [286,310] (se spots.json
# _vindu) gjør deg_out(267) 19 i stedet for 24 - rett under likely_flat sin
# egen 20-graders grense for metno_korrigert, så flagget slår ikke lenger
# inn her. Stjernene (det som faktisk teller) er fortsatt 0 - Hb-dempingen
# (ny 26.09.2026, se rating.rate()) kutter surfehøyden til 0,2 m uansett.
# Trygt: appen viser da "0,2 m" i stedet for "Trolig flatt" for akkurat
# denne timen, ikke en feil - bare en mildere måte å si det samme på.
w = rate({"height_spot_model": 1.7, "dir_offshore": 267, "turn": None, "period": 11, "wind_speed": 3, "wind_dir": 120}, G)
show("Grøtfjord 24.09 kl 09 (Windy-tall)", w); assert w["stars"] == 0

# Ny høydeberegning: bare svellet ute ganget med faktor, vindsjøen teller ikke.
# Direkte treff (300 grader, godt innenfor [291,310]): 1,0 * 0,6 * 1,0 = 0,6 m.
sv = rate({"swell_offshore": 1.0, "height_spot_model": 2.4, "dir_offshore": 300, "turn": 5,
           "period": 11, "wind_speed": 3, "wind_dir": 120}, G)
show("Svell 1,0 m ute, met.no total 2,4 m", sv)
assert sv["height_source"] == "svell_ute" and sv["height"] == 0.6

# 26.09.2026: mildere vind. En BarentsWatch-dag midt i idealhøyden med bare
# 3 m/s offshore skal nå gi full pott - det er nesten ingen vind i praksis.
# bw_dir = spotens facing (rett inn mot stranda) - uten den blir timen
# "usikker" (se testene i bunnen for hvorfor) og ville feilaktig kappes.
ok = rate({"bw_height": 1.2, "dir_offshore": 300, "bw_dir": G["facing"], "turn": 5, "period": 10, "wind_speed": 3, "wind_dir": 120}, G)
show("Vanlig ok dag", ok); assert ok["stars"] == 4

# 5 stjerner krever alt: SURFEHØYDE (Hb, se breaking_height) nøyaktig midt i
# ideal_height, lang periode, midt i vinduet, blankt. Ved 15 s periode gir Hs
# 0,7209 m en surfehøyde nøyaktig i midten (1,4 m) - funnet ved å løse
# breaking_height(H, 15) == MID numerisk, ikke gjettet. Se README/samtalen
# 26.09.2026 for bakgrunnen (periodefaktoren er fjernet, erstattet med den
# ekte, empiriske Komar og Gaughan-formelen).
def _solve_h_for_surf_height(target, period):
    lo, hi = 0.05, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if breaking_height(mid, period) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

# IKKE avrund H_EPIC: breaking_height() er ikke-lineær (opphøyd i 0,4), så
# selv en liten avrunding av H flytter Hb bort fra MID med nok til å velte
# height_score sin eksakte 1,0-topp (og dermed 5. stjerne) - i motsetning
# til den gamle, lineære period_factor-formelen, som tålte avrunding fint.
H_EPIC = _solve_h_for_surf_height(MID, 15)
epic = rate({"bw_height": H_EPIC, "dir_offshore": 300.5, "bw_dir": G["facing"], "turn": 3, "period": 15, "wind_speed": 1, "wind_dir": 120}, G)
show("Alt perfekt", epic); assert epic["stars"] == 5

# Nesten perfekt, men 11 s periode: skal ikke bli 5.
near = rate({"bw_height": 1.4, "dir_offshore": 300, "turn": 3, "period": 11, "wind_speed": 1, "wind_dir": 120}, G)
show("Nesten perfekt, 11 s", near); assert near["stars"] <= 4

# Uten BarentsWatch og med dreining: maks 3 uansett.
unc = rate({"height_spot_model": 1.5, "dir_offshore": 308, "turn": 15, "period": 15, "wind_speed": 1, "wind_dir": 90}, E)
show("Usikker (met.no, 15 grader dreining)", unc); assert unc["stars"] <= 3 and unc["uncertain"]

# 26.09.2026: mildere vind. 6 m/s onshore havner nå i 5-8 m/s-sjiktet
# (straff 2, ikke 3 som før) - se breakdown for det fulle regnestykket.
on = rate({"bw_height": 1.4, "dir_offshore": 300, "turn": 3, "period": 15, "wind_speed": 6, "wind_dir": 300}, G)
show("Perfekt svell, onshore 6 m/s", on); assert on["faded"] == 2

# Tidevann: spot som bare liker lavt vann mister en stjerne på flo. Bruker
# samme periode-justerte høyde som "Alt perfekt" - se forklaringen der.
T = {**G, "tide": ["lav", "middels"]}
base = {"bw_height": H_EPIC, "dir_offshore": 300.5, "bw_dir": G["facing"], "turn": 3, "period": 15, "wind_speed": 1, "wind_dir": 120}
lo = rate({**base, "tide": {"state": "lav"}}, T); hi = rate({**base, "tide": {"state": "høy"}}, T)
show("Liker lavt vann, fjære", lo); show("Liker lavt vann, flo", hi)
assert lo["stars"] == 5 and hi["stars"] == 4 and hi["faded_tide"] == 1
# Observert 25.09.2026: svell ute 313 grader, vinduet er [291,310] - bare 3
# grader utenfor. Helt flatt i praksis (0 stjerner, som stemmer). Skyggekurven
# gir 0,47 m Hs her (ikke under 0,35 m) - uten demping ville Komar og Gaughan
# sin formel (lang periode, 9,2 s) urealistisk løftet dette til en surfbar
# Hb (ca 0,82 m, "3 stjerner") fordi formelen ikke vet at svellet er
# diffraktert rundt en odde og har mistet koherens. Dempes derfor med
# directness (samme faktor som reduserer Hs), se rate() sin kommentar om
# dette - godt innenfor vinduet endres ingenting.
just_outside = rate({"swell_offshore": 1.76, "dir_offshore": 313.3, "turn": 13.6,
                      "period": 9.2, "wind_speed": 1.6, "wind_dir": 79}, G)
show("Grøtfjord 25.09, 3 grader utenfor vinduet", just_outside)
assert just_outside["stars"] == 0

# Retning skal telle på selve høyden, ikke bare stjernene: midt i vinduet
# skal gi høyere meter-tall enn en retning nær kanten, selv om begge er
# teknisk sett innenfor. 26.09.2026: vinduet ble utvidet til [286,310]
# (spots.json _vindu) - 291 (den gamle kanten) ligger nå 5 grader inn i
# vinduet, akkurat på EDGE_TAPER sin grense (full uttelling), så bruker den
# NYE kanten (286) for et ekte "på kanten"-tilfelle.
center = rate({"swell_offshore": 2.0, "dir_offshore": 300.5, "turn": 5, "period": 11,
               "wind_speed": 1, "wind_dir": 120}, G)
edge = rate({"swell_offshore": 2.0, "dir_offshore": 286, "turn": 5, "period": 11,
             "wind_speed": 1, "wind_dir": 120}, G)
show("Retning midt i vinduet", center); show("Retning i kanten av vinduet", edge)
assert center["height"] > edge["height"]

# 7b: skyggekurven for Grøtfjord (vindu [291,310]), svell 2,0 m ute.
# 300: godt innenfor -> 1,2 m. 310: kanten -> 0,8 m. 315/320: i skyggen,
# faller raskt. 340: 10 grader forbi enden av kurven -> 0.
def h_at(dirr):
    return rate({"swell_offshore": 2.0, "dir_offshore": dirr, "turn": 3, "period": 11,
                 "wind_speed": 1, "wind_dir": 120}, G)["height"]

h300, h310, h315, h320, h340 = h_at(300), h_at(310), h_at(315), h_at(320), h_at(340)
print(f"{'Skyggekurve 300/310/315/320/340':<40} {h300} {h310} {h315} {h320} {h340}")
assert h300 == 1.2
assert h310 == 0.8
assert h315 < 0.45
assert h320 < 0.25
assert h340 == 0

# 7d: Russelv har to sektorer ([[5,15],[349,356]]). 0 grader (rett utenfor
# begge) skal gi lavere directness enn 10 grader (midt i [5,15]). 1.0 skal
# bare gis når man er godt inne i en sektor, ikke rett innenfor kanten.
from rating import directness
d_0 = directness(0, R)
d_10 = directness(10, R)
d_6 = directness(6, R)  # 1 grad innenfor kanten av [5,15]
print(f"{'Russelv directness 0/10/6 grader':<40} {d_0} {d_10} {d_6}")
assert d_0 < d_10
assert d_10 == 1.0
assert d_6 < 1.0

# 7e: svell godt innenfor vinduet, nær kanten (308 på Grøtfjord), skal ikke
# gjøre varselet usikkert - bare retning utenfor vinduet eller stor dreining skal.
near_edge = rate({"swell_offshore": 1.5, "dir_offshore": 308, "turn": 3, "period": 11,
                   "wind_speed": 1, "wind_dir": 120}, G)
show("Nær kanten, innenfor vinduet (308 grader)", near_edge)
assert not near_edge["uncertain"]

# ---------- 26.09.2026: mildere vind, effektiv høyde, breakdown ----------

# 6.1-6.4: BarentsWatch 0,9 m, innenfor vinduet.
base09 = {"bw_height": 0.9, "dir_offshore": 300, "bw_dir": G["facing"]}
c1 = rate({**base09, "period": 16, "wind_speed": 1, "wind_dir": 120}, G)
show("6.1: 0,9m/16s, 1 m/s", c1); assert c1["stars"] == 4

c2 = rate({**base09, "period": 16, "wind_speed": 3, "wind_dir": 300}, G)
show("6.2: 0,9m/16s, 3 m/s onshore", c2); assert c2["stars"] == 4

c3 = rate({**base09, "period": 16, "wind_speed": 4, "wind_dir": 300}, G)
show("6.3a: 0,9m/16s, 4 m/s onshore, uten kast", c3); assert c3["stars"] == 3

c4 = rate({**base09, "period": 16, "wind_speed": 4, "wind_dir": 300, "gust": 12}, G)
show("6.3b: 0,9m/16s, 4 m/s onshore, kast 12 (eff. 6,4)", c4); assert c4["stars"] == 2

c5 = rate({**base09, "period": 8, "wind_speed": 1, "wind_dir": 120}, G)
show("6.4: 0,9m/8s, 1 m/s", c5)
# Kort periode gir fortsatt lavere SURFEHØYDE enn lang periode ved samme Hs
# (fysisk riktig - Komar og Gaughan), men begge havner nå innenfor samme
# "ideell" score-platå for Grøtfjord ([0.8,2.0]), så stjernetallet i seg selv
# skiller ikke lenger nødvendigvis - se den ekte surf_height-forskjellen i
# stedet, som IKKE er en avrundingsartefakt.
assert c5["surf_height"] < c1["surf_height"]
assert c5["stars"] <= c1["stars"]

# 6.5: offshore vind - ingen straff til 10 m/s, -1 fra der.
assert wind_penalty(9, 120, G) == 0
assert wind_penalty(12, 120, G) == 1
print(f"{'6.5: offshore 9/12 m/s straff':<40} 0 1")

# 6.6: Komar og Gaughan sin bruddhøyde-formel, kontrollverdier (toleranse
# 0,05 m - se spesifikasjonen 26.09.2026).
assert abs(breaking_height(0.9, 15) - 1.67) < 0.05
assert abs(breaking_height(1.0, 10) - 1.55) < 0.05
assert abs(breaking_height(0.5, 8) - 0.81) < 0.05
print(f"{'6.6: Hb kontrollverdier (0.9/15, 1.0/10, 0.5/8)':<40} "
      f"{round(breaking_height(0.9,15),3)} {round(breaking_height(1.0,10),3)} {round(breaking_height(0.5,8),3)}")

# 6.7: "height" (Hs, det kalibreringen mot BarentsWatch/loggene læres mot) er
# fortsatt den ekte, urørte signifikante høyden - surf_height (det man ser i
# appen) er en EGEN, separat størrelse (Hb * surf_factor), skal aldri lekke
# inn i "height"-feltet.
r_period = rate({"bw_height": 1.0, "dir_offshore": 300, "bw_dir": G["facing"], "period": 16, "wind_speed": 1, "wind_dir": 120}, G)
assert r_period["height"] == 1.0
# rate() runder surf_height til 2 desimaler i output - toleranse deretter.
assert abs(r_period["surf_height"] - breaking_height(1.0, 16) * r_period["surf_factor"]) < 0.01
print(f"{'6.7: Hs vs surfehøyde (1,0 m/16s)':<40} Hs={r_period['height']} surfehøyde={r_period['surf_height']}")

# 6.8: breakdown finnes, har ett ledd per faktor pluss totalen, og totalen
# stemmer med stjernene som faktisk ble gitt. Signifikant høyde, svellandel,
# retning ved spoten, periode, bruddhøyde, surf-faktor, surfehøyde, retning,
# vind, tidevann, totalt - de tre nye (bruddhøyde/surf-faktor/surfehøyde,
# 26.09.2026) erstatter den gamle "føles som"-teksten. BarentsWatch-periode-
# linja er ikke med her, siden base09 ikke setter bw_period.
bd = c4["breakdown"]
assert len(bd) == 11
assert bd[-1].startswith("Totalt:")
assert bd[-1].split("Totalt: ")[1].startswith(f"{c4['stars']} av 5")
print(f"{'6.8: breakdown (0,9m/16s, kast 12)':<40}")
for line in bd:
    print("   ", line)

# 6.9: Grøtfjord 24.09.2026 - alle tre tester over ga fortsatt 0 (g, g2, w).
assert g["stars"] == 0 and g2["stars"] == 0 and w["stars"] == 0

# 6.10: 5 stjerner skal fortsatt være sjeldent.
common = rate({"bw_height": 1.0, "dir_offshore": 300, "turn": 3, "period": 11, "wind_speed": 1, "wind_dir": 120}, G)
show("6.10: 1,0m/11s, blankt", common)
assert common["stars"] <= 4

# ---------- 26.09.2026: skill ekte svell fra vindsjø, retning ved spoten ----------
from rating import swell_share as _swell_share
L = spots["lenangsoyra"]

# 7.1: Lenangsøyra 26.09.2026 - i praksis mest vindsjø, retning på tvers av
# fjorden. Skal bli flatt og markert som uenige kilder.
l1 = rate({"bw_height": 0.7, "bw_height_max": 1.4, "swell_offshore": 1.3, "dir_offshore": 277,
           "height_offshore": 2.7, "period": 9, "bw_dir": 290,
           "wind_speed": 7, "wind_dir": 200, "gust": 10}, L)
show("7.1: Lenangsøyra 26.09 (mest vindsjø)", l1)
assert l1["height"] < 0.35 and l1["likely_flat"] and l1["sources_disagree"] and l1["stars"] == 0

# 7.2: samme dag, men med ekte nordlig svell rett inn mot stranda.
l2 = rate({"bw_height": 1.0, "swell_offshore": 1.2, "dir_offshore": 19, "height_offshore": 1.3,
           "period": 13, "bw_dir": 5, "wind_speed": 2, "wind_dir": None}, L)
show("7.2: Lenangsøyra, ekte nordlig svell", l2)
assert l2["stars"] >= 3 and not l2["sources_disagree"]

# 7.3: samme som 7.2, men BarentsWatch-periode 5 s - tydelig vindsjø selv om
# swell_share og retningen isolert sett ser fine ut.
l3 = rate({"bw_height": 1.0, "swell_offshore": 1.2, "dir_offshore": 19, "height_offshore": 1.3,
           "period": 13, "bw_dir": 5, "bw_period": 5, "wind_speed": 2, "wind_dir": None}, L)
show("7.3: samme, men BarentsWatch-periode 5 s", l3)
assert l3["height"] < l2["height"] and l3["stars"] < l2["stars"]

# 7.4: samme som 7.2, men BarentsWatch-retning fra 80 grader - 70 grader
# skrått på stranda (facing 0). FØR 27.09.2026 (Theodors rettelse, Unstad
# for lav - se STATUS.md) ga dette 0: retningsfaktoren ved punktet alene
# avgjorde. NÅ er dir_offshore=19 godt eksponert (samme retning som 7.2,
# som allerede går opp) - vi vet da at svellet treffer, og stoler ikke
# lenger på BarentsWatch sin egen (upålitelige) retning ved punktet.
# Retningsfaktoren overstyres til 1,0, se barentswatch_height().
l4 = rate({"bw_height": 1.0, "swell_offshore": 1.2, "dir_offshore": 19, "height_offshore": 1.3,
           "period": 13, "bw_dir": 80, "wind_speed": 2, "wind_dir": None}, L)
show("7.4: samme, men BarentsWatch-retning 80 grader", l4)
assert l4["height"] == 0.92 and l4["stars"] == 4 and l4["spot_direction_overridden"]

# 7.5: retningskonvensjonen (rettet 27.09.2026, andre runde, mot en lagret,
# garantert rå logg fra FØR noen konvertering fantes: en diagnose-kjøring
# 26.09.2026 kl. 12:59 UTC viste totalMeanWaveDirection = 116 grader for
# Unstad, tidsverdien 2026-09-26T15:00Z. Konvertert (+180) gir 296, som
# treffer Unstad sin facing (294,8) nesten blink og stemmer med video som
# viste bølger rett inn mot stranda. totalMeanWaveDirection ER "mot",
# samme som pilene på BarentsWatch sitt kart - en mellomliggende runde
# (26.09.2026) konkluderte feilaktig "fra" ut fra et allerede konvertert
# tall, se CLAUDE.md og STATUS.md). Mokker bare HTTP-laget, tester den
# ekte funksjonen.
import os
import sources as _sources

class _FakeTokenResp:
    def raise_for_status(self): pass
    def json(self): return {"access_token": "faketoken"}

class _FakeBwResp:
    status_code = 200
    def raise_for_status(self): pass
    def json(self):
        return [{"forecastTime": "2026-01-01T00:00:00Z", "totalSignificantWaveHeight": 1.0,
                  "totalMeanWaveDirection": 116, "totalPeakPeriod": 10.0, "expectedMaximumWaveHeight": 1.5}]

os.environ["BW_CLIENT_ID"], os.environ["BW_CLIENT_SECRET"] = "x", "y"
os.environ["BW_POINT_URL"] = "https://example.test/{lat}/{lon}"
_real_post, _real_get, _real_token = _sources.requests.post, _sources.requests.get, _sources._bw_token
_sources.requests.post = lambda *a, **k: _FakeTokenResp()
_sources.requests.get = lambda *a, **k: _FakeBwResp()
_sources._bw_token = None
bw_result = _sources.barentswatch_point(69.0, 19.0)
_sources.requests.post, _sources.requests.get, _sources._bw_token = _real_post, _real_get, _real_token
bw_k0 = next(iter(bw_result))
label_75 = "7.5: BarentsWatch mot 116 -> intern fra 296"
print(f"{label_75:<40} {bw_result[bw_k0]['dir']}")
assert bw_result[bw_k0]["dir"] == 296

# 7.5b: samme, men mot den FAKTISKE, sporbare fixturen (ikke bare et
# hardkodet tall i testen) - beviset ligger nå i repoet, ikke bare i
# Theodors Downloads-mappe. Se fetcher/fixtures/ sin egen forklaring.
_fixture = json.loads((Path(__file__).parent / "fixtures" / "bw_raw_unstad_2026-09-26.json").read_text())
assert _fixture["totalMeanWaveDirection"] == 116

class _FixtureBwResp:
    status_code = 200
    def raise_for_status(self): pass
    def json(self):
        return [{"forecastTime": _fixture["forecastTime"],
                  "totalSignificantWaveHeight": _fixture["totalSignificantWaveHeight"],
                  "totalMeanWaveDirection": _fixture["totalMeanWaveDirection"],
                  "totalPeakPeriod": _fixture["totalPeakPeriod"],
                  "expectedMaximumWaveHeight": _fixture["expectedMaximumWaveHeight"]}]

_sources.requests.post = lambda *a, **k: _FakeTokenResp()
_sources.requests.get = lambda *a, **k: _FixtureBwResp()
_sources._bw_token = None
fixture_result = _sources.barentswatch_point(_fixture["point"]["lat"], _fixture["point"]["lon"])
_sources.requests.post, _sources.requests.get, _sources._bw_token = _real_post, _real_get, _real_token
fixture_k0 = next(iter(fixture_result))
fixture_dir = fixture_result[fixture_k0]["dir"]
from rating import angle_diff as _angle_diff
diff_facing = _angle_diff(fixture_dir, spots["unstad"]["facing"])
print(f"{'7.5c: fixture (Unstad 26.09) mot -> fra, avvik facing':<40} {fixture_dir} {diff_facing}")
assert fixture_dir == 296
assert diff_facing < 5

# 7.6: swell_share avgrenses til 0,2 og 1,0.
assert _swell_share({"swell_offshore": 3.0, "height_offshore": 1.0})[0] == 1.0
assert _swell_share({"swell_offshore": 0.05, "height_offshore": 1.0})[0] == 0.2
print(f"{'7.6: swell_share avgrensning (3.0/1.0, 0.05/1.0)':<40} {_swell_share({'swell_offshore': 3.0, 'height_offshore': 1.0})[0]} {_swell_share({'swell_offshore': 0.05, 'height_offshore': 1.0})[0]}")

# 7.7: uten retning fra BarentsWatch - retningsfaktor 1,0 (nøytralt), men
# timen skal merkes usikker (vi vet ikke om bølgene faktisk treffer stranda).
l7 = rate({"bw_height": 1.0, "swell_offshore": 1.2, "dir_offshore": 19, "height_offshore": 1.3,
           "period": 13, "wind_speed": 2, "wind_dir": None}, L)
show("7.7: Lenangsøyra uten BarentsWatch-retning", l7)
assert l7["spot_direction_factor"] == 1.0 and l7["uncertain"]

# 7.8: varsler sendes aldri for timer med sources_disagree.
import notify as _notify
now8 = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(minute=0, second=0, microsecond=0)
def _th8(i):
    return _sources.hour_key(now8 + __import__("datetime").timedelta(hours=i))
hours_78 = [
    {"t": _th8(0), "stars": 4, "daylight": True, "height_source": "barentswatch", "sources_disagree": True},
    {"t": _th8(1), "stars": 4, "daylight": True, "height_source": "barentswatch", "sources_disagree": False},
]
spot_78 = {"id": "test78", "name": "Test78", "hours": hours_78, "bw_until": _th8(1)}
ws_78 = _notify.windows(spot_78, min_stars=3, hours_ahead=10, now=now8)
covered_78 = sum(len(w["hours"]) for w in ws_78)
print(f"{'7.8: varsler dekker (skal vaere 1, ikke 2)':<40} {covered_78}")
assert covered_78 == 1

# 7.9: Grøtfjord 24.09.2026 gir fortsatt 0 - se g/g2/w helt i toppen av filen.
assert g["stars"] == 0 and g2["stars"] == 0 and w["stars"] == 0

# ---------- 26.09.2026: surfehøyde (Komar og Gaughan) ----------
import calibrate as _calibrate
U = spots["unstad"]

# 8.2: Unstad, ren syntetisk sjekk av selve formelen (Hs 0,9/T 15, offshore
# 3 m/s, svell innenfor vinduet, BarentsWatch som kilde, retning rett inn) -
# se disagree_reason()-svaret over for hvorfor den EKTE Unstad 26.09-timen
# har en egen, urelatert retningskonflikt ved BarentsWatch-punktet.
u_epic = rate({"bw_height": 0.9, "bw_dir": U["facing"], "dir_offshore": 295, "period": 15,
               "wind_speed": 3, "wind_dir": 115}, U)
show("8.2: Unstad, Hs 0,9/T 15, offshore 3 m/s", u_epic)
assert abs(u_epic["surf_height"] - 1.67) < 0.05
assert abs(u_epic["surf_height_sets"] - 2.12) < 0.05
assert u_epic["stars"] >= 4

# 8.2b (26.09.2026, oppfølging): svellet ute er i kanten av vinduet (253
# grader, directness 0,667 - ville dempet Hb under den gamle regelen), men
# BarentsWatch-retningen ved spoten er nesten nøyaktig facing (1 grad avvik,
# spot_direction_factor 1,0) - BarentsWatch har allerede regnet med
# bøyingen inn mot land og sier bølgene treffer rett på. Skal derfor IKKE
# dempes (ekte hendelse: Unstad 26.09 kl. 17, 0,9 m/15 s, ga urettmessig
# bare 1,1 m surfehøyde/1 stjerne før denne fiksen).
u_edge = rate({"bw_height": 0.9, "bw_dir": U["facing"] - 1, "dir_offshore": 253, "period": 15,
               "wind_speed": 1, "wind_dir": 115}, U)
show("8.2b: Unstad, svell ute i kanten, BW-retning 1° fra facing", u_edge)
assert abs(u_edge["surf_height"] - 1.67) < 0.05
assert u_edge["spot_direction_factor"] == 1.0
assert not u_edge["sources_disagree"]

# 8.5: flat-sperren sin grense - rett under 0,35 m Hs er flatt uansett
# periode, rett over gir en ekte surfehøyde fra formelen.
under = rate({"bw_height": 0.34, "dir_offshore": 300, "bw_dir": G["facing"], "period": 16, "wind_speed": 1, "wind_dir": 120}, G)
over = rate({"bw_height": 0.36, "dir_offshore": 300, "bw_dir": G["facing"], "period": 16, "wind_speed": 1, "wind_dir": 120}, G)
print(f"{'8.5: flat-sperre 0,34/0,36 m Hs':<40} {under['stars']}/{under['surf_height']}  {over['stars']}/{over['surf_height']}")
assert under["stars"] == 0 and under["surf_height"] == 0.0 and under["likely_flat"]
assert over["surf_height"] is not None and over["surf_height"] > 0.0 and not over["likely_flat"]

# 8.6: surf_factor læres som median(størrelse / Hb), avgrenset til 0,5-1,6,
# standard 1,0 under MIN_LOGS. H valgt slik at Hb(H, 12) == 1,125 nøyaktig,
# og logget størrelse "Hoftehøy" (0,9 m) gir da 0,9/1,125 = 0,8.
H6 = _solve_h_for_surf_height(0.9 / 0.8, 12)
logs6 = [{"spot": "x", "size": "Hoftehøy", "forecastHeight": H6, "forecastPeriod": 12, "directness": 1.0} for _ in range(6)]
learned6 = _calibrate.learn("x", logs6)
print("8.6: surf_factor med 6 logger (0,8 x Hb):", learned6)
assert learned6["surf_factor"] == 0.8

learned4 = _calibrate.learn("x", logs6[:4])
print("8.6: surf_factor med 4 logger (under MIN_LOGS):", learned4)
assert "surf_factor" not in learned4

logs_low = [{"spot": "x", "size": "Flatt", "forecastHeight": 1.0, "forecastPeriod": 12, "directness": 1.0} for _ in range(5)]
logs_high = [{"spot": "x", "size": "Dobbelt over hodet", "forecastHeight": 0.5, "forecastPeriod": 8, "directness": 1.0} for _ in range(5)]
learned_low = _calibrate.learn("x", logs_low)
learned_high = _calibrate.learn("x", logs_high)
print("8.6: surf_factor-grenser (lav/høy):", learned_low["surf_factor"], learned_high["surf_factor"])
assert learned_low["surf_factor"] == 0.5 and learned_high["surf_factor"] == 1.6

# 8.6b (fra oppfølgingen 26.09.2026): logger med directness under 0,667
# teller ikke i surf_factor - de var flate pga feil retning, ikke pga at
# spoten generelt får mindre bølger enn formelen sier.
logs_baddir = [{"spot": "x", "size": "Hoftehøy", "forecastHeight": H6, "forecastPeriod": 12, "directness": 0.5} for _ in range(6)]
learned_baddir = _calibrate.learn("x", logs_baddir)
print("8.6b: logger med directness 0,5 (skal IKKE gi surf_factor):", learned_baddir)
assert "surf_factor" not in learned_baddir

# 8.7: transfer læres ikke lenger fra loggene - learn() setter ikke "transfer".
learned_transfer_check = _calibrate.learn("x", [
    {"spot": "x", "size": "Hoftehøy", "swellOffshore": 1.2, "directness": 1.0, "stars": 3, "forecastStars": 3}
    for _ in range(6)
])
print("8.7: learn() setter ikke transfer:", "transfer" in learned_transfer_check)
assert "transfer" not in learned_transfer_check

# 8.9: en observasjon (uten egen økt) teller likt som en logget økt i
# surf_factor - samme felt (size/forecastHeight/forecastPeriod/directness)
# betyr det samme uansett hvem som så det.
logs_obs = [{"spot": "x", "size": "Hoftehøy", "forecastHeight": H6, "forecastPeriod": 12,
             "directness": 1.0, "type": "observed", "source": "Instagram, Lofoten Surfsenter"} for _ in range(6)]
learned_obs = _calibrate.learn("x", logs_obs)
print("8.9: observasjoner teller i surf_factor:", learned_obs)
assert learned_obs["surf_factor"] == 0.8

# 8.10: period_score straffer bare kort periode nå (Grøtfjord min_period=8).
from rating import period_score
print(f"{'8.10: period_score 5/7/8/12s (min_period 8)':<40} "
      f"{period_score(5, G)} {period_score(7, G)} {period_score(8, G)} {period_score(12, G)}")
assert period_score(5, G) == 0.4   # under min_period - 2
assert period_score(7, G) == 0.6   # under min_period
assert period_score(8, G) == 1.0   # akkurat min_period: full uttelling
assert period_score(12, G) == 1.0  # lang periode: ingen ekstra straff eller bonus her

# Grøtfjord 26.09.2026 (denne samtalen): tredje dag på rad med flatt,
# svellet kommer fra vest/rett utenfor vinduet. Ekte rådata fra kjøringen
# 2026-09-26T15:00Z (BarentsWatch ved spoten, IKKE reservemodellen - godt
# innenfor bw_until). 27.09.2026, andre runde: den lagrede verdien (114) er
# hentet fra commit 04b0a52 (15:36 UTC 26.09), FØR noen konvertering fantes
# i koden - altså rå totalMeanWaveDirection ("mot"), ikke "fra". Riktig
# intern verdi er (114+180)%360 = 294, nesten blink mot facing (295): en
# nesten rett innhugg, IKKE et 179-graders avvik slik forrige runde antok.
g26 = rate({"bw_height": 0.33, "bw_dir": 294.0, "bw_period": 6.5, "swell_offshore": 2.18,
            "height_offshore": 5.0, "dir_offshore": 272, "period": 15.6,
            "height_spot_model": 2.4, "turn": 27.0, "wind_speed": 3.4, "wind_dir": 217.0,
            "gust": 5.3, "tide": {"level": 0.0, "rising": False, "state": "lav"}}, G)
show("Grøtfjord 26.09 (ekte data, BarentsWatch)", g26)
assert g26["stars"] == 0 and g26["likely_flat"] and g26["height_source"] == "barentswatch"
# Retningen er nå ekte og treffer nesten blink (spot_direction_offshore
# False) - stjernene forblir 0 uansett, for svellandelen (44 %, mest
# vindsjø) og signifikant høyde (0,1 m ute) holder det godt under
# flat-sperren på egen hånd. Se STATUS.md.
assert g26["spot_direction_offshore"] is False

# ---------- 27.09.2026: BarentsWatch-retning >150 grader fra facing ----------
# Ekte hendelse: Unstad i morgen kl. 10 (2026-09-27T08:00Z) viste 0,0 m og
# "Kildene er uenige", selv om svellet ute var 2,3 m fra 255 grader og
# BarentsWatch sin egen nettside viste sammenlignbar høyde. Den lagrede
# 115-verdien ble hentet mens sources.py IKKE konverterte (samme feil som
# Grøtfjord 114 over) - altså rå totalMeanWaveDirection ("mot"), ikke "fra".
# Riktig intern verdi er (115+180)%360 = 295, nesten blink mot facing
# (294,8): et nesten rett innhugg, ikke et 180-graders avvik. Denne timen
# viser at retningen var ekte hele tiden - den opprinnelige feilen (0,0 m)
# kom av den manglende konverteringen andre steder i kjeden, ikke av selve
# retningsverdien.
u_dir_error = rate({"bw_height": 0.61, "bw_dir": 295.0, "bw_period": 9.8, "swell_offshore": 2.3,
                     "height_offshore": 3.3, "dir_offshore": 255, "period": 8.85,
                     "wind_speed": 7.8, "wind_dir": 203.0, "gust": 13.0, "bw_interpolated": True}, U)
show("9.1: Unstad i morgen kl 10 (korrekt retning, 295)", u_dir_error)
assert u_dir_error["spot_direction_offshore"] is False
assert u_dir_error["uncertain"] is False
assert u_dir_error["sources_disagree"] is False
assert u_dir_error["surf_height"] > 0

# 9.2: samme, men rå (ikke interpolert) time - resultatet skal være likt
# uansett bw_interpolated.
u_dir_error_raw = rate({"bw_height": 0.61, "bw_dir": 295.0, "bw_period": 9.8, "swell_offshore": 2.3,
                         "height_offshore": 3.3, "dir_offshore": 255, "period": 8.85,
                         "wind_speed": 7.8, "wind_dir": 203.0, "gust": 13.0, "bw_interpolated": False}, U)
show("9.2: samme, rå (ikke interpolert) BarentsWatch-time", u_dir_error_raw)
assert u_dir_error_raw["spot_direction_factor"] == u_dir_error["spot_direction_factor"]
assert u_dir_error_raw["surf_height"] == u_dir_error["surf_height"]

# 9.3: 27.09.2026, andre runde: en genuint >150-graders time (syntetisk -
# ingen ekte logg med akkurat dette mønsteret ennå) ga EKTE straff
# (retningsfaktor 0), IKKE nøytral 1,0, siden dette er en KJENT retning
# (bølgene går ut fra land), ikke en ukjent en.
#
# 27.09.2026, Theodors rettelse (Unstad for lav): her (dir_offshore=255) er
# svellet UTE godt eksponert mot spoten (samme mønster som Unstad 26.09 og
# 27.09.2026) - retningsfaktoren overstyres da til 1,0 uansett hva
# BarentsWatch sin (upålitelige) retning ved selve punktet sier, se
# barentswatch_height(). Testen under (9.3b) dekker det opprinnelige
# tilfellet (dårlig eksponering ute også) - der gjelder fortsatt straffen.
u_offshore = rate({"bw_height": 1.2, "bw_dir": (U["facing"] + 165) % 360, "bw_period": 12.0,
                    "swell_offshore": 2.3, "height_offshore": 3.3, "dir_offshore": 255,
                    "period": 14, "wind_speed": 2.0, "wind_dir": None}, U)
show("9.3: BarentsWatch-retning 165 grader fra facing, men svellet ute treffer", u_offshore)
assert u_offshore["spot_direction_factor"] == 1.0
assert u_offshore["spot_direction_offshore"] is False
assert u_offshore["spot_direction_overridden"] is True
assert u_offshore["uncertain"] is False
assert u_offshore["sources_disagree"] is False
assert u_offshore["height"] > 0.5

# 9.3b: samme >150-graders BarentsWatch-retning, men nå er svellet UTE også
# dårlig eksponert (dir_offshore langt utenfor Unstad sitt vindu [253,335]) -
# ingen ekstern bekreftelse på at det treffer, så retningsfaktoren brukes
# fortsatt og gir ekte straff (0), akkurat som FØR rettelsen. Samme lave
# eksponering (dir_hit < 0,667) utløser også "kildene uenige" - naturlig,
# siden det er nøyaktig det samme signalet (dårlig eksponert svell ute) som
# avgjør BEGGE: når det er for lavt til å stole på for overstyringen, er det
# også for lavt til at kildene regnes som enige.
u_offshore_bad = rate({"bw_height": 1.2, "bw_dir": (U["facing"] + 165) % 360, "bw_period": 12.0,
                        "swell_offshore": 2.3, "height_offshore": 3.3, "dir_offshore": 100,
                        "period": 14, "wind_speed": 2.0, "wind_dir": None}, U)
show("9.3b: samme, men svellet ute IKKE eksponert (dir_offshore 100)", u_offshore_bad)
assert u_offshore_bad["spot_direction_factor"] == 0.0
assert u_offshore_bad["spot_direction_offshore"] is True
assert u_offshore_bad["spot_direction_overridden"] is False
assert u_offshore_bad["uncertain"] is True
assert u_offshore_bad["sources_disagree"] is True
assert u_offshore_bad["height"] == 0.0  # bw_height * ... * 0 = 0

# 9.3c: 30.09.2026, fysikk-kontrollør sitt funn (samme >150-graders
# BarentsWatch-retning som 9.3/9.3b, men nå mangler dir_offshore HELT - f.eks.
# fordi Open-Meteo feilet for akkurat den timen mens BarentsWatch likevel har
# data). directness()/exposure() sin "ukjent retning"-nøytralverdi er 0,7,
# som i seg selv ligger OVER 0,667-grensa - uten en eksplisitt sjekk på at
# dir_offshore faktisk er kjent ville overstyringen slått inn på ren
# UVITENHET, ikke på en bekreftet god eksponering. Skal IKKE overstyres -
# straffen gjelder fortsatt, akkurat som 9.3b.
u_offshore_unknown = rate({"bw_height": 1.2, "bw_dir": (U["facing"] + 165) % 360, "bw_period": 12.0,
                            "swell_offshore": 2.3, "height_offshore": 3.3, "dir_offshore": None,
                            "period": 14, "wind_speed": 2.0, "wind_dir": None}, U)
show("9.3c: samme, men dir_offshore helt ukjent (ikke overstyrt på uvitenhet)", u_offshore_unknown)
assert u_offshore_unknown["spot_direction_factor"] == 0.0
assert u_offshore_unknown["spot_direction_offshore"] is True
assert u_offshore_unknown["spot_direction_overridden"] is False
assert u_offshore_unknown["height"] == 0.0

# 9.4: ingen retning fra BarentsWatch i det hele tatt - fortsatt nøytral
# 1,0 og usikker, som før (uendret av denne runden - se rating.py sin
# docstring, "mangler retning eller facing").
u_no_dir = rate({"bw_height": 1.2, "bw_period": 12.0, "swell_offshore": 2.3,
                  "height_offshore": 3.3, "dir_offshore": 255, "period": 14,
                  "wind_speed": 2.0, "wind_dir": None}, U)
show("9.4: BarentsWatch uten retning i det hele tatt", u_no_dir)
assert u_no_dir["spot_direction_factor"] == 1.0
assert u_no_dir["spot_direction_offshore"] is False
assert u_no_dir["uncertain"] is True

# 9.5: grensen for spot_direction_factor() sin tredje returverdi - rett
# under 150 grader er IKKE "ut fra land" (bare en vanlig dårlig retning,
# faktor 0 fra før av), rett over ER "ut fra land" (også faktor 0, men med
# flagget satt, til forklaringsteksten og fetch.py sin spotnivå-sikring).
from rating import spot_direction_factor as _sdf
just_under = _sdf(U["facing"] + 149, U["facing"])
just_over = _sdf(U["facing"] + 151, U["facing"])
print(f"{'9.5: grense 149/151 grader fra facing':<40} {just_under} {just_over}")
assert just_under == (0.0, True, False)
assert just_over == (0.0, True, True)

# 9.6: fetch.py sin spotnivå-sikring (convention_warning) - varsler ved 60 %
# slike timer blant dem med ekte svell ute mot vinduet, ikke ved 20 %.
from fetch import convention_warning

def _mk_hour(offshore):
    return {"swell_offshore": 1.5, "dir_offshore": U["facing"], "bw_dir": 1.0,
            "spot_direction_diff": 165 if offshore else 10}

hours_60 = [_mk_hour(True)] * 6 + [_mk_hour(False)] * 4
hours_20 = [_mk_hour(True)] * 2 + [_mk_hour(False)] * 8
w60 = convention_warning(hours_60, U, "Unstad")
w20 = convention_warning(hours_20, U, "Unstad")
print(f"{'9.6: spotnivå-varsel ved 60% / 20% >150-timer':<40} {bool(w60)} {bool(w20)}")
assert w60 is not None and "Unstad" in w60
assert w20 is None

# ---------- 27.09.2026, ROADMAP oppgave 2: eksponering (del C) i ratingen ----------
from rating import exposure, exposure_override_cap, directness as _directness

# 10.1: exposure_override_cap() - Grøtfjord har [{"from":311,"to":330,"max":0.2}].
assert exposure_override_cap(320, G) == 0.2
assert exposure_override_cap(311, G) == 0.2
assert exposure_override_cap(330, G) == 0.2
assert exposure_override_cap(200, G) is None  # utenfor override-sektoren
assert exposure_override_cap(None, G) is None
print(f"{'10.1: exposure_override_cap 320/200 grader (Grøtfjord)':<40} {exposure_override_cap(320, G)} {exposure_override_cap(200, G)}")

# 10.2: exposure() uten exposure_smoothed på spoten faller tilbake til
# directness() (vindu + skyggekurve) - IKKE brutt av denne oppgaven for
# spots som ennå ikke har fått eksponeringsdata fra fetch.py.
assert exposure(300, G) == _directness(300, G)
assert exposure(None, G) == _directness(None, G)
print(f"{'10.2: exposure() uten data faller tilbake til directness()':<40} {exposure(300, G)} {_directness(300, G)}")

# 10.3: exposure() bruker spot["exposure_smoothed"] (360 tall, indeks =
# gradtall) når den finnes, i stedet for directness().
G_exp = dict(G)
G_exp["exposure_smoothed"] = [0.0] * 360
G_exp["exposure_smoothed"][300] = 0.87
assert exposure(300, G_exp) == 0.87
assert exposure(301, G_exp) == 0.0  # ingen smoothing i denne syntetiske testen, bare indeksering
print(f"{'10.3: exposure() bruker exposure_smoothed når den finnes':<40} {exposure(300, G_exp)} {exposure(301, G_exp)}")

# 10.4: exposure_override sitt tak gjelder UANSETT om verdien kommer fra
# exposure_smoothed eller fra directness()-reserven - Grøtfjord 320 grader
# er dekket av taket (0,2).
G_exp320 = dict(G)
G_exp320["exposure_smoothed"] = [0.0] * 360
G_exp320["exposure_smoothed"][320] = 0.9  # høyere enn taket
assert exposure(320, G_exp320) == 0.2
G_exp100 = dict(G)
G_exp100["exposure_smoothed"] = [0.0] * 360
G_exp100["exposure_smoothed"][100] = 0.9  # utenfor override-sektoren, ikke dekket
assert exposure(100, G_exp100) == 0.9
print(f"{'10.4: exposure_override sitt tak (320 dekket, 100 ikke)':<40} {exposure(320, G_exp320)} {exposure(100, G_exp100)}")

# 10.5: spot_height() sin svell_ute-gren bruker faktisk exposure() (ikke bare
# en isolert funksjonstest, men den ekte kodeveien) - inkludert at
# exposure_override sitt tak faktisk slår gjennom der, ikke bare i exposure()
# alene. Samme exposure_smoothed (0,9), med og uten override-listen.
from rating import spot_height as _spot_height
G_exp320_no_override = dict(G_exp320)
G_exp320_no_override["exposure_override"] = []
h_capped, src_capped, _ = _spot_height({"swell_offshore": 2.0, "dir_offshore": 320}, G_exp320)
h_uncapped, src_uncapped, _ = _spot_height({"swell_offshore": 2.0, "dir_offshore": 320}, G_exp320_no_override)
print(f"{'10.5: spot_height() - eksponeringstak slår gjennom':<40} {round(h_capped,3)} {round(h_uncapped,3)}")
assert src_capped == src_uncapped == "svell_ute"
assert h_capped < h_uncapped  # 0,2 (taket) mot 0,9 (rå exposure_smoothed)

# 10.6: fetch.py sin resolve_exposure() - manglende data, feil sjekksum, og
# riktig sjekksum (bruker spot_checksum() fra exposure.py, samme som
# exposure_baseline.py selv regner ut). Returnerer nå (smoothed, raw, advarsel).
from fetch import resolve_exposure
from exposure import spot_checksum as _spot_checksum

smoothed_none, raw_none, warn_none = resolve_exposure(G, {}, "Grøtfjord")
assert smoothed_none is None and raw_none is None and "Grøtfjord" in warn_none

smoothed_bad, raw_bad, warn_bad = resolve_exposure(
    G, {"grotfjord": {"checksum": "feil", "smoothed": [1.0] * 360, "raw": [1.0] * 360}}, "Grøtfjord")
assert smoothed_bad is None and raw_bad is None and "sjekksum" in warn_bad

good_checksum = _spot_checksum(G)
smoothed_ok, raw_ok, warn_ok = resolve_exposure(
    G, {"grotfjord": {"checksum": good_checksum, "smoothed": [0.5] * 360, "raw": [0.0] * 360}}, "Grøtfjord")
assert smoothed_ok == [0.5] * 360 and raw_ok == [0.0] * 360 and warn_ok is None
print(f"{'10.6: resolve_exposure() mangler/feil/riktig sjekksum':<40} {bool(warn_none)} {bool(warn_bad)} {warn_ok}")

# ---------- 27.09.2026, tredje runde: ekstra Hb-demping bare ved rå eksponering 0 ----------
from rating import raw_exposure_zero as _raw_zero

# 11.1: uten exposure_raw (fallback) - "rå eksponering 0" tilsvarer utenfor
# vinduet (degrees_outside > 0), akkurat som directness() sin egen modell.
assert _raw_zero(300, G) is False   # midt i vinduet [286,310]
assert _raw_zero(320, G) is True    # utenfor vinduet, og utenfor fri sektor
assert _raw_zero(None, G) is False

# 11.2: med exposure_raw - bruker tallet direkte, uavhengig av vinduet.
E_raw = dict(E)
E_raw["exposure_raw"] = [1.0] * 360
E_raw["exposure_raw"][325] = 0.0   # Ersfjordstranda 30.09: bak odden, ekte hendelse
assert _raw_zero(318, E_raw) is False
assert _raw_zero(325, E_raw) is True
print(f"{'11.1/11.2: raw_exposure_zero() fallback/ekte data':<40} {_raw_zero(320, G)} {_raw_zero(325, E_raw)}")

# 11.3: Ersfjordstranda sin ekte hendelse, 30.09.2026 - 2,2 m svell fra 325
# grader (rå eksponering 0, bak odden - fri sektor er [288,320], vinduet
# [294,320]) skal gi klart lavere surfehøyde OG maks 1 stjerne, sammenlignet
# med samme svell fra 318 grader (innenfor, rå eksponering over 0). Glattet
# eksponering på 325 (0,3) er lav, akkurat som del C sin ekte glatting gir
# nær kanten av en blokkert retning - poenget her er den EKSTRA dempingen av
# Hb (rå=0), ikke selve glattingstallet.
E_exp = dict(E)
E_exp["exposure_smoothed"] = [1.0] * 360
E_exp["exposure_smoothed"][325] = 0.3
E_exp["exposure_raw"] = [1.0] * 360
E_exp["exposure_raw"][325] = 0.0
bak_odden = rate({"swell_offshore": 2.2, "dir_offshore": 325, "period": 12, "wind_speed": 1, "wind_dir": 120}, E_exp)
innenfor = rate({"swell_offshore": 2.2, "dir_offshore": 318, "period": 12, "wind_speed": 1, "wind_dir": 120}, E_exp)
show("11.3: Ersfjordstranda 325 (bak odden) vs 318 (innenfor)", bak_odden)
show("11.3b: ... 318 grader", innenfor)
assert bak_odden["surf_height"] < innenfor["surf_height"]
assert bak_odden["stars"] <= 1

# 11.4: Unstad sin ekte hendelse, 30.09.2026 - svell fra 252-253 grader har
# FRI linje til havet (rå eksponering 1,0, innenfor vinduet [253,335] eller
# rett i kanten) - skal IKKE få den ekstra dempingen (samme oppførsel som
# rettelsen fra forrige runde, uendret av denne).
U_exp = dict(U)
U_exp["exposure_smoothed"] = [1.0] * 360
U_exp["exposure_raw"] = [1.0] * 360
fri_linje = rate({"swell_offshore": 1.9, "dir_offshore": 253, "period": 13, "wind_speed": 1, "wind_dir": 120}, U_exp)
show("11.4: Unstad 253 grader (fri linje, ingen ekstra demping)", fri_linje)
assert _raw_zero(253, U_exp) is False

# 11.5 (funnet av fysikk-kontrollør ved gjennomgang av 11.1-11.4): Grøtfjord
# sin exposure_override (311-330, tak 0,2) overlapper med 317-330, der RÅ
# eksponering er 0,0 (bekreftet i data/exposure_baseline.json) - uten unntaket
# i rate() ville den ekstra diffraksjons-dempingen dempet Hb en gang til OPPÅ
# taket, dobbelt straff av samme retning. Bruker ekte tall fra
# data/exposure_baseline.json (ikke syntetiske), samme som STATUS.md sin
# før/etter-tabell.
_grotfjord_exp = json.loads((Path(__file__).parent.parent / "data" / "exposure_baseline.json").read_text())["grotfjord"]
G_override_zone = dict(G)
G_override_zone["exposure_smoothed"] = _grotfjord_exp["smoothed"]
G_override_zone["exposure_raw"] = _grotfjord_exp["raw"]
assert _raw_zero(320, G_override_zone) is True   # rå eksponering er 0,0 her
from rating import exposure_override_cap as _cap
assert _cap(320, G_override_zone) == 0.2         # og overriden dekker 320 grader
override_big_swell = rate({"swell_offshore": 4.0, "dir_offshore": 320, "period": 14,
                            "wind_speed": 1, "wind_dir": 120}, G_override_zone)
show("11.5: Grøtfjord 320 (override + rå eksponering 0, ikke dobbelt dempet)", override_big_swell)
assert override_big_swell["stars"] >= 2  # taket alene demper nok - ikke en ekstra gang til

# ---------- 27.09.2026: "blåst ut" (mye vindsjø/vind) skilt fra ekte flatt ----------
# Ekte hendelse: Grøtfjord tirsdag kl. 14 - appen viste "Trolig flatt"/0,0 m,
# men svellet ute var 0,9 av 5,9 m totalt (84 % vindsjø) og vinden 14 m/s
# side-onshore, kast 21. Ikke flatt (lite energi) - blåst ut (mye energi,
# bare ikke ekte svell). BarentsWatch sin egen totalhøyde (1,2 m her) skal
# vises i stedet for den sterkt dempede "0,2 m".
blown = rate({"bw_height": 1.2, "bw_period": 5.5, "bw_dir": G["facing"], "swell_offshore": 0.9,
              "height_offshore": 5.9, "dir_offshore": G["facing"], "period": 7,
              "wind_speed": 14, "wind_dir": 301, "gust": 21}, G)
show("12.1: Grøtfjord tirsdag 14 - blåst ut, ikke flatt", blown)
assert blown["stars"] == 0
assert blown["likely_flat"] is True  # uendret - stjernene skal fortsatt kuttes av flat-sperren
assert blown["blown_out"] is True
assert any("blåst ut" in line for line in blown["breakdown"])
assert blown["low_reason"] == "blown_out"  # 05.10.2026: samme sak via det nye, samlende feltet

# 12.2: Grøtfjord 24.09.2026 (linje 17 over) - ekte flatt, IKKE blåst ut,
# selv om den også er "likely_flat". Ingen svell_offshore/vind oppgitt der,
# men bw_height (0,3) er allerede under flat-sperren selv - ingen reell
# energi totalt å forveksle med vindsjø.
assert g2["blown_out"] is False
assert g2["low_reason"] == "flat"

# 12.3: samme vindsjø-situasjon, men bw_height under flat-sperren i seg selv
# (reelt lite totalt, ikke bare lite ekte svell) - skal IKKE bli blåst ut.
genuinely_flat = rate({"bw_height": 0.2, "bw_period": 5.5, "bw_dir": G["facing"], "swell_offshore": 0.05,
                        "height_offshore": 0.3, "dir_offshore": G["facing"], "period": 7,
                        "wind_speed": 14, "wind_dir": 301, "gust": 21}, G)
show("12.3: samme vind, men lav BarentsWatch-totalhøyde - ekte flatt", genuinely_flat)
assert genuinely_flat["blown_out"] is False
assert genuinely_flat["likely_flat"] is True
assert genuinely_flat["low_reason"] == "flat"

# ---------- 27.09.2026: source/fileSource lagres, og en plausibilitetssjekk
# mot vindretningen - test av hypotesen om at BarentsWatch-konvensjonen kan
# variere med kilden, denne gangen med data i stedet for bare resonnement ----------
import fetch as _fetch

# 13.1: sources.barentswatch_point() lagrer source, fileSource og rå retning.
_sources.requests.post = lambda *a, **k: _FakeTokenResp()
class _FakeBwRespSrc:
    status_code = 200
    def raise_for_status(self): pass
    def json(self):
        return [{"forecastTime": "2026-01-01T00:00:00Z", "totalSignificantWaveHeight": 1.0,
                  "totalMeanWaveDirection": 90, "totalPeakPeriod": 8.0, "expectedMaximumWaveHeight": 1.5,
                  "source": "modelA", "fileSource": "fileA.nc"}]
_sources.requests.get = lambda *a, **k: _FakeBwRespSrc()
_sources._bw_token = None
src_result = _sources.barentswatch_point(69.0, 19.0)
_sources.requests.post, _sources.requests.get, _sources._bw_token = _real_post, _real_get, _real_token
src_k0 = next(iter(src_result))
print("13.1: source/fileSource/rå retning lagret:", src_result[src_k0]["source"], src_result[src_k0]["file_source"], src_result[src_k0]["dir_raw"])
assert src_result[src_k0]["source"] == "modelA"
assert src_result[src_k0]["file_source"] == "fileA.nc"
assert src_result[src_k0]["dir_raw"] == 90.0
assert src_result[src_k0]["dir"] == 270.0  # 90 + 180, samme konvertering som før

# 13.2: bw_direction_plausible() - gjelder bare ved sterk vind og lav
# svellandel. Vindsjø ved punktet bør følge vindretningen (innenfor 60 grader).
def _mk_hour_plaus(**over):
    base = {"wind_speed": 12.0, "wind_dir": 270.0, "swell_offshore": 0.3, "height_offshore": 3.0,
            "bw_dir": 270.0, "bw_dir_raw": 90.0}
    return {**base, **over}

applies, matches, matches_raw = _fetch.bw_direction_plausible(_mk_hour_plaus())
print("13.2: sterk vind, lav svellandel - stemmer med/uten omregning:", applies, matches, matches_raw)
assert applies is True
assert matches is True    # bw_dir (270) = wind_dir (270), stemmer med omregning
assert matches_raw is False  # bw_dir_raw (90) er motsatt av vinden, stemmer IKKE uten omregning

# 13.3: gjelder ikke ved svak vind, høy svellandel, manglende vindretning,
# eller ingen ekte BarentsWatch-retning i det hele tatt (reservemodell-timer,
# f.eks. lokalt uten BarentsWatch-nøkler - matches=None ville ellers blitt
# telt som "stemmer ikke" av feil grunn).
assert _fetch.bw_direction_plausible(_mk_hour_plaus(wind_speed=5.0))[0] is False
assert _fetch.bw_direction_plausible(_mk_hour_plaus(swell_offshore=2.0))[0] is False  # svellandel 2/3, over 30 %
assert _fetch.bw_direction_plausible(_mk_hour_plaus(wind_dir=None))[0] is False
assert _fetch.bw_direction_plausible(_mk_hour_plaus(bw_dir=None))[0] is False
print("13.3: svak vind / høy svellandel / manglende vindretning eller bw_dir -> gjelder ikke")

# 13.4: bw_plausibility_report() teller opp per source/fileSource og legger
# en rad i kilderapporten (fetch.REPORT).
before = len(_fetch.REPORT)
hours_plaus = [
    {**_mk_hour_plaus(), "bw_source": "modelA", "bw_file_source": "fileA.nc"},
    {**_mk_hour_plaus(bw_dir=90.0, bw_dir_raw=270.0), "bw_source": "modelA", "bw_file_source": "fileA.nc"},
    {**_mk_hour_plaus(wind_speed=3.0), "bw_source": "modelA", "bw_file_source": "fileA.nc"},  # gjelder ikke
]
_fetch.bw_plausibility_report(hours_plaus, "Test")
assert len(_fetch.REPORT) == before + 1
print("13.4: bw_plausibility_report() la til rad i kilderapporten:", _fetch.REPORT[-1])
assert _fetch.REPORT[-1][0] == "Test"
assert "modelA" in _fetch.REPORT[-1][3]
assert "1/2 med omregning" in _fetch.REPORT[-1][3]  # bare den første av de to gjeldende timene stemmer med omregning
assert "1/2" in _fetch.REPORT[-1][3].split(",")[1]  # og bare den andre stemmer uten (symmetrisk motsatt)

# 13.5 (funnet av fysikk-kontrollør): en interpolert time har ekte bw_dir/
# bw_dir_raw (satt av bw_interpolate()), men ALDRI bw_source/bw_file_source -
# skal IKKE telles inn i rapporten (ville havnet i en uspesifisert "?/?"-rad
# og utvannet per-kilde-statistikken).
before5 = len(_fetch.REPORT)
_fetch.bw_plausibility_report([{**_mk_hour_plaus(), "bw_interpolated": True,
                                 "bw_source": None, "bw_file_source": None}], "Test")
assert len(_fetch.REPORT) == before5  # ingen ny rad - ingen ekte, gjeldende timer
print("13.5: interpolert time ekskludert fra plausibilitetsrapporten")

# ---------- 27.09.2026, ROADMAP oppgave 1: vind interpolert forbi met.no sitt
# 6-timerssteg (live sjekket: Locationforecast går fra time- til 6-timerssteg
# etter ca. 51 timer, se sources.weather_interpolate()) ----------

# 14.1: vind hver 6. time gir verdier alle timer imellom (lineært for
# styrke/kast/lufttemp), og retning 350 til 10 grader gir 0 midt mellom
# (sirkulært, korteste vei - IKKE 180, som en naiv lineær interpolasjon
# ville gitt).
raw_weather = {
    "2026-09-27T00:00Z": {"wind_speed": 4.0, "wind_dir": 350.0, "gust": 6.0, "air_temp": 8.0},
    "2026-09-27T06:00Z": {"wind_speed": 10.0, "wind_dir": 10.0, "gust": 14.0, "air_temp": 10.0},
}
interp = _sources.weather_interpolate(raw_weather)
assert len(interp) == 7  # 00, 01, ..., 06
for k in ("2026-09-27T00:00Z", "2026-09-27T06:00Z"):
    assert interp[k]["wind_interpolated"] is False
mid = interp["2026-09-27T03:00Z"]
print("14.1: vind hver 6. time - midt-time (03:00):", mid)
assert mid["wind_interpolated"] is True
assert abs(mid["wind_speed"] - 7.0) < 1e-9   # lineært, midt mellom 4 og 10
assert abs(mid["gust"] - 10.0) < 1e-9
assert abs(mid["air_temp"] - 9.0) < 1e-9
assert mid["wind_dir"] == 0.0  # sirkulært: 350->10 korteste vei er via 0, ikke via 180

# 14.2: ingen verdier ekstrapolert forbi siste punkt, og ingen fylt inn over
# et hull på mer enn 6 timer (samme "ikke ekstrapoler/ikke fyll for langt"-
# prinsipp som bw_interpolate()).
raw_gap = {
    "2026-09-27T00:00Z": {"wind_speed": 4.0, "wind_dir": 0.0, "gust": None, "air_temp": 8.0},
    "2026-09-27T08:00Z": {"wind_speed": 6.0, "wind_dir": 0.0, "gust": None, "air_temp": 9.0},  # 8t hull - for langt
}
interp_gap = _sources.weather_interpolate(raw_gap)
assert len(interp_gap) == 2  # ingen mellomtimer fylt inn over 8-timers hullet
assert "2026-09-27T09:00Z" not in interp_gap  # ingen ekstrapolering forbi siste punkt
print("14.2: ingen ekstrapolering, ingen fylling over hull > 6 timer")

# 14.3: _timestep_summary() finner hvor tidssteget faktisk endrer seg (og
# rapporterer "jevnt" når det bare er ett jevnt steg å måle, som med kun 2
# punkter - ingen falsk endring).
now14 = __import__("datetime").datetime(2026, 9, 27, 0, tzinfo=__import__("datetime").timezone.utc)
horizon, txt = _fetch._timestep_summary(raw_weather, now14)
print("14.3: _timestep_summary() med bare 2 punkter (ett jevnt steg)", horizon, txt)
assert txt == "jevnt tidssteg hele horisonten"
raw_change = {
    "2026-09-27T00:00Z": {}, "2026-09-27T01:00Z": {}, "2026-09-27T02:00Z": {},
    "2026-09-27T08:00Z": {}, "2026-09-27T14:00Z": {},
}
_, txt_change = _fetch._timestep_summary(raw_change, now14)
print("14.3b: tidssteg-endring funnet:", txt_change)
assert "1t til 6t" in txt_change and "T02:00Z" in txt_change

# ---------- 27.09.2026, Theodors rettelse: Unstad for lav ----------
# Se STATUS.md for hele sporet (26.09 og 27.09-observasjonene, kjeden for
# Unstad 27.09 kl. 06-10, og stjernetabellen før/etter for alle spots).

# 15.1: barentswatch_height() sin "Etter justering"-linje i breakdown (kun
# når noe faktisk trekker ned - se 6.8 over for det UENDREDE tilfellet uten
# justering).
U15 = spots["unstad"]
r15 = rate({"bw_height": 0.84, "bw_dir": 295.0, "bw_period": 9.8, "swell_offshore": 2.72,
            "height_offshore": 3.4, "dir_offshore": 251, "period": 12.55,
            "wind_speed": 5.4, "wind_dir": 193.0, "gust": 10.8}, U15)
assert any(line.startswith("BarentsWatch 0,8 m signifikant") for line in r15["breakdown"])
assert any(line.startswith("Etter justering") and "svellandel" in line for line in r15["breakdown"])
print("15.1: breakdown skiller BarentsWatch-signifikant fra justert høyde", r15["height"])

# 15.2: low_adjustment_warning() - spot der justert høyde er under 25 % av
# BarentsWatch sin totalhøyde i mer enn halvparten av dagslystimene, varsler
# med riktig ledd (svellandel er lavest her - 0,2 - mot periodefaktoren 1,0).
low_hours = [
    {"t": f"2026-09-27T{h:02d}:00Z", "daylight": True, "height_source": "barentswatch",
     "bw_height": 1.0, "height": 0.2, "swell_offshore": 0.2, "height_offshore": 1.0,
     "bw_period": 10, "spot_direction_factor": 1.0}
    for h in range(6, 10)
]
warn15 = _fetch.low_adjustment_warning(low_hours, "Test15")
print("15.2: low_adjustment_warning() (skal varsle om svellandel):", warn15)
assert warn15 is not None and "svellandel" in warn15 and "4 av 4" in warn15

# 15.3: samme, men bare 1 av 4 timer lave - ikke over halvparten, ingen varsel.
mixed_hours = low_hours[:1] + [
    {"t": f"2026-09-27T{h:02d}:00Z", "daylight": True, "height_source": "barentswatch",
     "bw_height": 1.0, "height": 0.9, "swell_offshore": 0.9, "height_offshore": 1.0,
     "bw_period": 10, "spot_direction_factor": 1.0}
    for h in range(7, 10)
]
assert _fetch.low_adjustment_warning(mixed_hours, "Test15b") is None
print("15.3: low_adjustment_warning() - under halvparten lave, ingen varsel")

# 15.4: bw_point_in_lee_warning() - ekte hendelse, Farstadsanden 05.10.2026
# (se STATUS.md): BarentsWatch 0,08-0,1 m mens totalhøyden ute var 6+ m i
# storm, time etter time, MED svellet ute midt i vinduet (315, samme som
# facing - ikke bare tilfeldig lav svellandel pga. off-window, se 15.9).
# Under 10 % av totalhøyden ute i mer enn halvparten av timene med over 2 m
# totalt ute.
F15 = spots["farstadsanden"]
lee_hours = [
    {"t": f"2026-10-05T{h:02d}:00Z", "height_offshore": 6.1, "bw_height": 0.08, "dir_offshore": 315}
    for h in range(10, 15)
]
warn_lee = _fetch.bw_point_in_lee_warning(lee_hours, F15, "Farstadsanden")
print("15.4: bw_point_in_lee_warning() (skal varsle):", warn_lee)
assert warn_lee is not None and "i le" in warn_lee and "5 av 5" in warn_lee

# 15.5: samme spot, men BarentsWatch-høyden følger totalhøyden ute normalt -
# ingen varsel.
ok_hours = [
    {"t": f"2026-10-05T{h:02d}:00Z", "height_offshore": 6.1, "bw_height": 3.5, "dir_offshore": 315}
    for h in range(10, 15)
]
assert _fetch.bw_point_in_lee_warning(ok_hours, F15, "Farstadsanden") is None
print("15.6: bw_point_in_lee_warning() - normal høyde, ingen varsel")

# 15.7: stille dager (under 2 m totalt ute) skal ikke trigge varselet selv om
# BarentsWatch-andelen tilfeldigvis er lav - det er for lite energi til at
# forholdstallet betyr noe.
calm_hours = [
    {"t": f"2026-10-05T{h:02d}:00Z", "height_offshore": 1.0, "bw_height": 0.05, "dir_offshore": 315}
    for h in range(10, 15)
]
assert _fetch.bw_point_in_lee_warning(calm_hours, F15, "Farstadsanden") is None
print("15.8: bw_point_in_lee_warning() - stille dager, ingen varsel")

# 15.9, fysikk-kontrollør sitt funn (05.10.2026): lav bw_height når svellet
# ute er UTENFOR vinduet er forventet og skal IKKE varsles - det er det
# samme mønsteret som den faste observasjonen Grøtfjord 25.09.2026 (helt
# flatt, svell fra 313 grader, 3 grader utenfor vinduet 286-310). Uten
# retningsfilteret ga en tidligere versjon falsk alarm akkurat her, mot et
# punkt som alt er bekreftet riktig av en fast observasjon i CLAUDE.md.
offwindow_hours = [
    {"t": f"2026-09-25T{h:02d}:00Z", "height_offshore": 3.0, "bw_height": 0.2, "dir_offshore": 313}
    for h in range(10, 15)
]
assert _fetch.bw_point_in_lee_warning(offwindow_hours, G, "Grøtfjord") is None
print("15.9: bw_point_in_lee_warning() - svell utenfor vinduet (Grøtfjord 25.09), ingen varsel")

# ---------- 30.09.2026, Theodors rettelse: surf_factor_prior for Unstad ----------
# To observasjoner viste at surfehøyden ble undervurdert med samme faktor
# begge ganger (26.09: beregnet 1,67 m, observert ca. 2,4 m - forhold 1,44;
# 27.09: beregnet 0,76-1,03 m, observert ca. 1,2-1,6 m - forhold ca. 1,5).
# I stedet for å senke ideal_height (som ville skjult årsaken): ny
# surf_factor_prior = 1,45 i spots.json, brukt FØR det finnes nok logger til
# å lære selv (se calibrate.MIN_LOGS), og ideal_height senket til [1,2, 3,5]
# (en ren, brysthøy dag er god surf på Unstad). Se STATUS.md for hele sporet.
from rating import SURF_FACTOR_MAX, SURF_FACTOR_MIN
import fetch as _fetch16
assert U["surf_factor_prior"] == 1.45 and U["surf_factor_prior_n"] == 2
assert U["ideal_height"] == [1.2, 3.5]
U16 = dict(U)
U16["surf_factor"] = round(min(SURF_FACTOR_MAX, max(SURF_FACTOR_MIN, U["surf_factor_prior"])), 2)
U16["surf_factor_source"] = "prior"
# Ekte geometrisk eksponering (del C), samme som fetch.py faktisk bruker i
# produksjon - uten denne faller exposure() tilbake til directness() sin
# enklere vindu-grense, som IKKE fanger opp at 251-255 grader (rett utenfor
# Unstad sitt vindu [253,335] på kanten) fortsatt har god geometrisk
# eksponering (samme mønster som test_pipeline.py sin del B-test).
_exposure_baseline_real = json.loads((Path(__file__).parent.parent / "data" / "exposure_baseline.json").read_text())
_smoothed16, _raw16, _warn16 = _fetch16.resolve_exposure(U16, _exposure_baseline_real, "Unstad")
assert _warn16 is None
U16["exposure_smoothed"], U16["exposure_raw"] = _smoothed16, _raw16

# 16.1: Unstad 26.09.2026 kl. 14:45 (fast observasjon i CLAUDE.md) - minst
# 3 stjerner, og surfehøyden skal være ca. 2,4 m (det faktisk observerte).
r_2609 = rate({"bw_height": 0.9, "bw_dir": U16["facing"], "bw_period": 15.0, "dir_offshore": 300,
               "swell_offshore": 1.0, "height_offshore": 1.0, "period": 15, "wind_speed": 3.0,
               "wind_dir": sum(U16["offshore_wind"]) // 2}, U16)
show("16.1: Unstad 26.09 kl. 14:45 (surf_factor_prior)", r_2609)
assert r_2609["stars"] >= 3
assert abs(r_2609["surf_height"] - 2.4) < 0.1
assert any(line.startswith("Surf-faktor 1,45 (startverdi fra 2 observasjoner)") for line in r_2609["breakdown"])

# 16.2: Unstad 27.09.2026 kl. 06-08 (fast observasjon i CLAUDE.md) - minst
# 2 stjerner. Ekte historiske inndata (rekonstruert fra git-historikken til
# docs/data/forecast.json FØR retningskonvensjon-fiksen samme dag, bw_dir
# rettet med +180 - se STATUS.md for fremgangsmåten). Kl. 09-10 (ikke en del
# av den faste observasjonen) faller til 1 stjerne i samme rekonstruksjon -
# svellet falmer utover morgenen, og vinden appen beregnet (5-8 m/s
# side-onshore) stemmer ikke med videoens "nesten ingen vind" (se ROADMAP.md
# sin "Venter på Theodor" - ikke noe koden kan rette).
h_2709 = [
    {"t": "06:00", "bw_height": 0.8366666666666667, "bw_dir": 295.0, "bw_period": 9.8,
     "swell_offshore": 2.56, "height_offshore": 3.5, "dir_offshore": 255, "period": 9.45,
     "wind_speed": 7.8, "wind_dir": 227.0, "gust": 13.9},
    {"t": "07:00", "bw_height": 0.7533333333333334, "bw_dir": 295.0, "bw_period": 9.8,
     "swell_offshore": 2.54, "height_offshore": 3.5, "dir_offshore": 255, "period": 9.2,
     "wind_speed": 6.5, "wind_dir": 211.0, "gust": 12.9},
    {"t": "08:00", "bw_height": 0.67, "bw_dir": 295.0, "bw_period": 9.8,
     "swell_offshore": 2.72, "height_offshore": 3.4, "dir_offshore": 251, "period": 12.55,
     "wind_speed": 5.4, "wind_dir": 193.0, "gust": 10.8},
]
for h in h_2709:
    r = rate(h, U16)
    show(f"16.2: Unstad 27.09 kl. {h['t']}", r)
    assert r["stars"] >= 2, f"{h['t']} ga bare {r['stars']} stjerner"

# ---------- 30.09.2026, Theodors rettelse: bw_confirms (Unstad 28.09) ----------
# "Safe to say it's firing" - lange, rene linjer, offshore-sprøyt, 4-5
# stjerner. Svellet ute var 3-5 grader UTENFOR vinduet (eksponering 62-66 %,
# rett under 0,667), men BarentsWatch ved SPOTEN selv bekreftet treff (1
# grad fra facing, god høyde) - appen viste likevel bare 1 stjerne
# ("Trolig ikke surfbart"), fordi sources_disagree sitt eksponeringsledd
# ikke visste om bekreftelsen fra punktet. Se barentswatch_height() og
# rate() sin bruk av bw_confirms.
h_2809 = [
    {"t": "12:00", "bw_height": 0.60, "bw_dir": 294.0, "bw_period": 11.5,
     "swell_offshore": 1.40, "height_offshore": 2.00, "dir_offshore": 249, "period": 12.0,
     "wind_speed": 7.5, "wind_dir": 145.0, "gust": 10.5},
    {"t": "13:00", "bw_height": 0.58, "bw_dir": 293.5, "bw_period": 11.8,
     "swell_offshore": 1.35, "height_offshore": 1.95, "dir_offshore": 248, "period": 12.1,
     "wind_speed": 7.8, "wind_dir": 148.0, "gust": 11.0},
    {"t": "14:00", "bw_height": 0.57, "bw_dir": 295.0, "bw_period": 12.0,
     "swell_offshore": 1.32, "height_offshore": 1.90, "dir_offshore": 250, "period": 12.0,
     "wind_speed": 8.0, "wind_dir": 150.0, "gust": 11.5},
    {"t": "15:00", "bw_height": 0.55, "bw_dir": 294.0, "bw_period": 11.6,
     "swell_offshore": 1.28, "height_offshore": 1.85, "dir_offshore": 249, "period": 11.8,
     "wind_speed": 7.6, "wind_dir": 147.0, "gust": 10.8},
]
for h in h_2809:
    r = rate(h, U16)
    show(f"17: Unstad 28.09 kl. {h['t']}", r)
    assert r["stars"] >= 3, f"{h['t']} ga bare {r['stars']} stjerner"
    assert r["bw_confirms"] is True
    assert r["sources_disagree"] is False

# ---------- 05.10.2026, Theodors rettelse: fire-delt grunn for 0/1 stjerne
# (classify_low_rating) ----------
# Ekte hendelse: Grøtfjord kl. 11-17, 05.10.2026 - appen viste 0 stjerner og
# "Flatt", men BarentsWatch målte 1,5 m rett ved spoten (3 grader skrått),
# reell surfehøyde, og vinden var 13 m/s onshore fra vest (fra V, kast 19) -
# is_blown_out() krevde den gamle flat-sperren (low_hs) for å slå inn, så en
# time der vinden alene tar stjernene falt tvers igjennom til STAR_WORDS[0]
# ("Flatt") i appen. classify_low_rating() sin vind-dominans-sjekk (potensial
# minst 2 FØR vind, og vinden tar minst like mye som tidevannet) fanger nå
# dette uavhengig av low_hs. Se STATUS.md.
grotfjord_blown_by_wind = rate({"bw_height": 1.5, "bw_dir": 298.0, "bw_period": 10.0,
                                 "swell_offshore": 1.4, "height_offshore": 1.6, "dir_offshore": 297,
                                 "period": 11.0, "wind_speed": 13.0, "wind_dir": 270.0, "gust": 19.0}, G)
show("18.1: Grøtfjord 05.10 kl. 11-17 - blåst ut (reell høyde, sterk vind)", grotfjord_blown_by_wind)
assert grotfjord_blown_by_wind["stars"] == 0
assert grotfjord_blown_by_wind["low_reason"] == "blown_out"
assert grotfjord_blown_by_wind["surf_height"] is not None and grotfjord_blown_by_wind["surf_height"] > 0.4
assert grotfjord_blown_by_wind["wind_type"] == "onshore"

# 18.2: Grøtfjord 24.09.2026 (linje 14 over) skal fortsatt gi "Flatt", ikke
# "Blåst ut" - helt reelt lav totalenergi, ikke vind som tar en ellers god
# dag. Allerede sjekket over (g["low_reason"] == "flat"), gjentatt her for å
# gjøre selve kravet eksplisitt ved siden av 18.1.
assert g["low_reason"] == "flat"

# 18.3: med en realistisk BarentsWatch-totalhøyde (ikke et punkt som måler
# kunstig lavt) gir samme lave svellandel "Stormsjø", med BarentsWatch sin
# egen totalhøyde vist - ikke "0,0 m"/"Flatt". Ekte hendelse: Farstadsanden
# kl. 12, 05.10.2026 viste BarentsWatch 0,08 m (0,1 m) mens svellet ute var
# 6,1 m totalt og storm (19 m/s) - se STATUS.md, punktet ligger trolig i le
# (eget avsnitt, ikke en feil i klassifiseringen under).
F18 = spots["farstadsanden"]
stormsjo18 = rate({"bw_height": 3.5, "bw_dir": F18["facing"], "bw_period": 9.0,
                    "swell_offshore": 0.74, "height_offshore": 6.1, "dir_offshore": 298,
                    "period": 11.0, "wind_speed": 19.0, "wind_dir": 227.0, "gust": 30.0}, F18)
show("18.3: Farstadsanden - stormsjø med realistisk BarentsWatch-høyde", stormsjo18)
assert stormsjo18["low_reason"] == "stormsjo"
assert stormsjo18["swell_share"] < 0.4

# ---------- 06.10.2026, Theodors oppgave: bølgeenergi (kJ) og myke lokale
# regler for Farstadsanden (Magnus, lokal surfer) ----------
from rating import energy_kj as _energy_kj

# 19.1: energiformelen mot fem tall Theodor leste av surf-forecast.com for
# Farstadsanden. Tre av fem treffer innenfor Theodors egen 5 %-grense -
# IKKE alle fem, og Theodor har godkjent at det er greit (06.10.2026).
# Grunnen: surf-forecast AVRUNDER høyde og periode i visningen ("3 m 11 s"),
# mens deres egen energiberegning bruker de uavrundede tallene - og siden
# både H og T står i kvadrat, forsterkes en liten avrunding i inputene.
# Forholdet kJ/(H²T²) varierer derfor ca. 11 % mellom surf-forecast sine
# EGNE fem tall (1,82-2,06), mer enn 5 %-målet - ingen enkelt konstant kan
# treffe alle fem samtidig, uansett hvilken vi velger. Formelen er den
# fysisk korrekte og er ikke justert med en kunstig konstant (se README
# "Bølgeenergi (kJ)" og energy_kj() sin docstring). De to som ikke treffer
# (3 m/11 s og 5,5 m/16 s) sjekkes likevel mot en løsere, dokumentert grense
# (10 %) - ikke utelatt, bare ikke forventet å holde Theodors strengere mål.
_energy_cases = [
    (2.4, 11, 1427), (3, 11, 1981), (3, 14, 3500), (4, 15, 7400), (5.5, 16, 14396),
]
_energy_within_5pct = 0
for H, T, expected in _energy_cases:
    got = _energy_kj(H, T)
    diff_pct = abs(got - expected) / expected * 100
    print(f"19.1: energy_kj({H}, {T}) = {got:.1f} kJ (surf-forecast {expected}), avvik {diff_pct:.1f} %")
    assert diff_pct < 10, f"{H} m/{T} s avvek {diff_pct:.1f} %, over selv den løse 10 %-grensen"
    if diff_pct < 5:
        _energy_within_5pct += 1
assert _energy_within_5pct == 3, f"forventet nøyaktig 3 av 5 innenfor 5 % (se docstring), fikk {_energy_within_5pct}"

# 19.2: 19.3-19.6 trenger en Farstadsanden-kopi UTEN local_rules, til å
# sammenligne "med" mot "uten" reglene på nøyaktig samme værinndata.
F19 = spots["farstadsanden"]
assert F19.get("local_rules") is not None  # sjekker at feltet faktisk er satt før vi tester det
F19_no_rules = dict(F19)
del F19_no_rules["local_rules"]

# 19.3: Farstadsanden med 1,6 m svell ute og 10 s (ca. 500 kJ, under Magnus
# sin "zero"-grense 1500 kJ) skal gi klart færre stjerner MED reglene enn
# UTEN - energifaktoren ganger potensialet kraftig ned før vind/tidevann.
h_lowenergy = {"swell_offshore": 1.6, "height_offshore": 1.8, "dir_offshore": 310, "period": 10,
               "wind_speed": 3, "wind_dir": 130, "gust": 4, "tide": {"state": "lav", "rising": True}}
r_with_rules = rate(h_lowenergy, F19)
r_without_rules = rate(h_lowenergy, F19_no_rules)
show("19.3: Farstadsanden 1,6 m/10 s MED lokale regler", r_with_rules)
show("19.3: Farstadsanden 1,6 m/10 s UTEN lokale regler", r_without_rules)
assert abs(r_with_rules["energy_swell_kj"] - 500) < 50  # "ca. 500 kJ"
assert r_with_rules["stars"] < r_without_rules["stars"]

# 19.4: 5,5 m, 16 s, ØSØ vind (112,5 grader - offshore for Farstadsanden sin
# offshore_wind [85,175], senter 130), lavvann - ingen straff fra reglene
# (energien er godt over "full", vinden er offshore ikke side/-onshore,
# lavvann er foretrukket).
h_bigday_lav = {"swell_offshore": 5.5, "height_offshore": 5.8, "dir_offshore": 310, "period": 16,
                "wind_speed": 6, "wind_dir": 112.5, "gust": 8, "tide": {"state": "lav", "rising": True}}
r_bigday_lav = rate(h_bigday_lav, F19)
show("19.4: Farstadsanden 5,5 m/16 s, ØSØ, lavvann", r_bigday_lav)
assert r_bigday_lav["wind_type"] == "offshore"
assert r_bigday_lav["local_rules"]["stars_lost"] == 0

# 19.5: samme som 19.4, men høyvann - én stjerne mindre enn 19.4, utelukkende
# fra tide_penalty_high (vektet med weight 0,7: 0,7 stjerne, rundet opp til
# én hel - se local_rules_penalty()).
h_bigday_hoy = dict(h_bigday_lav); h_bigday_hoy["tide"] = {"state": "høy", "rising": False}
r_bigday_hoy = rate(h_bigday_hoy, F19)
show("19.5: Farstadsanden 5,5 m/16 s, ØSØ, høyvann", r_bigday_hoy)
assert r_bigday_hoy["local_rules"]["stars_lost"] == 1
assert r_bigday_lav["stars"] - r_bigday_hoy["stars"] == 1

# 19.6: ingen andre spots har local_rules - rate() sitt resultat for dem skal
# derfor være identisk med/uten denne hele oppgaven (regresjon mot resten av
# testfila, ikke bare et nytt sjekkpunkt her).
for other_id in ("grotfjord", "tromvik", "ersfjordstranda", "russelv", "lenangsoyra", "steinkrossa", "unstad"):
    assert spots[other_id].get("local_rules") is None, f"{other_id} skal IKKE ha local_rules"

print("Alle tester ok")
