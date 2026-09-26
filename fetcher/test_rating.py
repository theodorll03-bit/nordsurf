"""Tester ratingen mot det du faktisk har observert. Kjør: python fetcher/test_rating.py"""
import json
from pathlib import Path
from rating import rate, period_factor, wind_penalty, effective_height

spots = {s["id"]: s for s in json.loads((Path(__file__).parent.parent / "spots.json").read_text())["spots"]}
G, E, R = spots["grotfjord"], spots["ersfjordstranda"], spots["russelv"]
MID = sum(G["ideal_height"]) / 2

def show(label, r): print(f"{label:<40} {r['stars']} hele, {r['faded']} tapt  ({r['height']} m, {r['height_source']})")

# Observert 24.09.2026: met.no sa 1,9 m i Grøtfjord, det var helt flatt.
g = rate({"height_spot_model": 1.9, "dir_offshore": 311, "turn": 32, "period": 11, "wind_speed": 3, "wind_dir": 180}, G)
show("Grøtfjord 24.09 (met.no)", g); assert g["stars"] == 0 and g["likely_flat"]

# Samme dag, BarentsWatch sa 0,3 m. Observert flatt.
g2 = rate({"bw_height": 0.3, "dir_offshore": 311, "turn": 32, "period": 11, "wind_speed": 3, "wind_dir": 180}, G)
show("Grøtfjord 24.09 (BarentsWatch)", g2); assert g2["stars"] == 0

# Observert 24.09.2026 kl 09: Windy viste 1,7 m 11 s fra ca. 267 grader i bukta. Helt flatt.
w = rate({"height_spot_model": 1.7, "dir_offshore": 267, "turn": None, "period": 11, "wind_speed": 3, "wind_dir": 120}, G)
show("Grøtfjord 24.09 kl 09 (Windy-tall)", w); assert w["stars"] == 0 and w["likely_flat"]

# Ny høydeberegning: bare svellet ute ganget med faktor, vindsjøen teller ikke.
# Direkte treff (300 grader, godt innenfor [291,310]): 1,0 * 0,6 * 1,0 = 0,6 m.
sv = rate({"swell_offshore": 1.0, "height_spot_model": 2.4, "dir_offshore": 300, "turn": 5,
           "period": 11, "wind_speed": 3, "wind_dir": 120}, G)
show("Svell 1,0 m ute, met.no total 2,4 m", sv)
assert sv["height_source"] == "svell_ute" and sv["height"] == 0.6

# 26.09.2026: mildere vind. En BarentsWatch-dag midt i idealhøyden med bare
# 3 m/s offshore skal nå gi full pott - det er nesten ingen vind i praksis.
ok = rate({"bw_height": 1.2, "dir_offshore": 300, "turn": 5, "period": 10, "wind_speed": 3, "wind_dir": 120}, G)
show("Vanlig ok dag", ok); assert ok["stars"] == 4

# 5 stjerner krever alt: EFFEKTIV høyde (høyde * periodefaktor, se
# period_factor) nøyaktig midt i ideal_height, lang periode, midt i vinduet,
# blankt. Ved 15 s periode (faktor 1,25) er det den ekte høyden 1,12 m -
# ikke 1,4 m som før periodefaktoren fantes - som treffer midten (1,4 m
# effektivt). Se README/samtalen 26.09.2026 for hvorfor: periodefaktoren
# virker BARE i height_score, og løfter man i tillegg den ekte høyden til
# 1,4 m ved 15 s blir den EFFEKTIVE høyden 1,75 m - forbi idealmidten, og
# gir 4 stjerner, ikke 5. Testen bruker derfor høyden som faktisk treffer
# midten ved denne perioden, ikke et gjettet tall.
H_EPIC = round(MID / period_factor(15), 4)
epic = rate({"bw_height": H_EPIC, "dir_offshore": 300.5, "turn": 3, "period": 15, "wind_speed": 1, "wind_dir": 120}, G)
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
base = {"bw_height": H_EPIC, "dir_offshore": 300.5, "turn": 3, "period": 15, "wind_speed": 1, "wind_dir": 120}
lo = rate({**base, "tide": {"state": "lav"}}, T); hi = rate({**base, "tide": {"state": "høy"}}, T)
show("Liker lavt vann, fjære", lo); show("Liker lavt vann, flo", hi)
assert lo["stars"] == 5 and hi["stars"] == 4 and hi["faded_tide"] == 1
# Observert 25.09.2026: svell ute 313 grader, vinduet er [291,310] - bare 3
# grader utenfor. Helt flatt i praksis (0 stjerner, som stemmer). Skyggekurven
# gir 0.47 m her (ikke under 0.35 m), så likely_flat er ikke satt for denne -
# det er tilsiktet i den nye modellen: likely_flat er nå bare for reelt lav
# beregnet høyde eller for reserven (metno_korrigert), ikke for svell_ute nær
# kanten. Stjernene (den faktiske observasjonen) stemmer uansett.
just_outside = rate({"swell_offshore": 1.76, "dir_offshore": 313.3, "turn": 13.6,
                      "period": 9.2, "wind_speed": 1.6, "wind_dir": 79}, G)
show("Grøtfjord 25.09, 3 grader utenfor vinduet", just_outside)
assert just_outside["stars"] == 0

# Retning skal telle på selve høyden, ikke bare stjernene: midt i vinduet
# skal gi høyere meter-tall enn en retning nær kanten, selv om begge er
# teknisk sett innenfor.
center = rate({"swell_offshore": 2.0, "dir_offshore": 300.5, "turn": 5, "period": 11,
               "wind_speed": 1, "wind_dir": 120}, G)
edge = rate({"swell_offshore": 2.0, "dir_offshore": 291, "turn": 5, "period": 11,
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
base09 = {"bw_height": 0.9, "dir_offshore": 300}
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
assert c5["stars"] in (2, 3) and c5["stars"] < c1["stars"]

# 6.5: offshore vind - ingen straff til 10 m/s, -1 fra der.
assert wind_penalty(9, 120, G) == 0
assert wind_penalty(12, 120, G) == 1
print(f"{'6.5: offshore 9/12 m/s straff':<40} 0 1")

# 6.6: periodefaktoren, inkludert interpolasjon ved 11,5 s.
assert period_factor(7) == 0.9
assert period_factor(10) == 1.0
assert period_factor(13) == 1.15
assert period_factor(18) == 1.3
expected_11_5 = 1.0 + (1.15 - 1.0) * (11.5 - 10) / (13 - 10)
assert abs(period_factor(11.5) - expected_11_5) < 1e-9
print(f"{'6.6: periodefaktor 7/10/13/18/11.5s':<40} {period_factor(7)} {period_factor(10)} {period_factor(13)} {period_factor(18)} {period_factor(11.5)}")

# 6.7: kalibreringen (og den viste høyden) bruker vanlig høyde, ikke effektiv
# høyde - effective_height() skal bare brukes i height_score, aldri lekke ut
# i "height"-feltet som logges/kalibreres mot.
r_period = rate({"bw_height": 1.0, "dir_offshore": 300, "period": 16, "wind_speed": 1, "wind_dir": 120}, G)
assert r_period["height"] == 1.0  # ikke 1.0 * 1.3 = 1.3
assert effective_height(1.0, 16) == 1.3  # men height_score bruker 1.3 internt
print(f"{'6.7: vist høyde vs effektiv (1,0 m/16s)':<40} vist={r_period['height']} effektiv={effective_height(1.0, 16)}")

# 6.8: breakdown finnes, har ett ledd per faktor pluss totalen, og totalen
# stemmer med stjernene som faktisk ble gitt.
bd = c4["breakdown"]
assert len(bd) == 6  # høyde, periode, retning, vind, tidevann, totalt
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

print("Alle tester ok")
