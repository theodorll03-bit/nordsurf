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

# 26.09.2026: mildere vind - 3 m/s offshore gir ingen vindstraff i det hele
# tatt (se breakdown). bw_dir = spotens facing (rett inn mot stranda) - uten
# den blir timen "usikker" (se testene i bunnen for hvorfor) og ville
# feilaktig kappes.
# 06.10.2026, Theodors rettelse (andre runde): 10 s periode gir nå 0,85
# (god, ikke lenger full uttelling - se period_score()), derfor 3 stjerner
# her (4 krever enten lengre periode eller høyde nærmere idealmidten).
ok = rate({"bw_height": 1.2, "dir_offshore": 300, "bw_dir": G["facing"], "turn": 5, "period": 10, "wind_speed": 3, "wind_dir": 120}, G)
show("Vanlig ok dag", ok); assert ok["stars"] == 3

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
# 15.10.2026 (5-stjerners-porten): svellenergien må være KJENT og over full-grensen for 5 - 2,0 m ute ved 15 s
# (× 1,25 topperiode) = 2 760 kJ; lik totalhøyde beholder svellandel 1,0 og surfehøyden nøyaktig i midten
epic = rate({"bw_height": H_EPIC, "dir_offshore": 300.5, "bw_dir": G["facing"], "turn": 3, "period": 15, "wind_speed": 1, "wind_dir": 120, "swell_offshore": 2.0, "height_offshore": 2.0}, G)
show("Alt perfekt", epic); assert epic["stars"] == 5

# Nesten perfekt, men 11 s periode: skal ikke bli 5.
near = rate({"bw_height": 1.4, "dir_offshore": 300, "turn": 3, "period": 11, "wind_speed": 1, "wind_dir": 120}, G)
show("Nesten perfekt, 11 s", near); assert near["stars"] <= 4

# Uten BarentsWatch og med dreining: maks 3 uansett.
unc = rate({"height_spot_model": 1.5, "dir_offshore": 308, "turn": 15, "period": 15, "wind_speed": 1, "wind_dir": 90}, E)
show("Usikker (met.no, 15 grader dreining)", unc); assert unc["stars"] <= 3 and unc["uncertain"]

# 26.09.2026: mildere vind. 15.10.2026 (Theodors regel 1, glatt kurve): 6 m/s onshore
# ligger mellom 5 (−1) og 8 (−2) -> −1,33, rundet til −1 til slutt (ingen svellenergi
# oppgitt -> ingen demping). Før: −2 (trinn 5-8 m/s).
on = rate({"bw_height": 1.4, "dir_offshore": 300, "turn": 3, "period": 15, "wind_speed": 6, "wind_dir": 300}, G)
show("Perfekt svell, onshore 6 m/s", on); assert on["faded"] == 1

# Tidevann: spot som bare liker lavt vann mister en stjerne på flo. Bruker
# samme periode-justerte høyde som "Alt perfekt" - se forklaringen der.
T = {**G, "tide": ["lav", "middels"]}
base = {"bw_height": H_EPIC, "dir_offshore": 300.5, "bw_dir": G["facing"], "turn": 3, "period": 15, "wind_speed": 1, "wind_dir": 120, "swell_offshore": 2.0, "height_offshore": 2.0}
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
# 16.11.2026 (Theodor, punkt e): svak pålandsvind under ca. 5 m/s trekker ikke lenger. Før ga 4 m/s ett poeng ned.
show("6.3a: 0,9m/16s, 4 m/s onshore, uten kast", c3); assert c3["stars"] == 4

c4 = rate({**base09, "period": 16, "wind_speed": 4, "wind_dir": 300, "gust": 12}, G)
show("6.3b: 0,9m/16s, 4 m/s onshore, kast 12 (eff. 6,0 - kast teller høyst 2 m/s, Theodor 15.10)", c4); assert c4["stars"] == 3

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
assert abs(wind_penalty(12, 120, G) - 0.5) < 1e-9   # 15.10.2026: glatt kurve offshore 10 -> 0, 14 -> 1
print(f"{'6.5: offshore 9/12 m/s straff':<40} 0 0,5")

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
# 15.10.2026: 5-stjerners-porten legger til én linje («Ikke Rått: …» / «Rått-svell …») når potensialet var 4
assert len([l for l in bd if not l.startswith(("Ikke Rått", "Rått-svell", "Femte stjerne"))]) == 11
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
from rating import swell_share as _swell_share, is_fjord
L = spots["lenangsoyra"]
# 23.11.2026 (bw_tillit, svar.md 23.11.2026 kl. 14.05): Lenangsøyra og Russelv er fjord-spots. Tester som bruker dem som
# vanlige kyst-spots (svellandel, periode og retning ved BarentsWatch-punktet, gap-grensa som bare løfter) får en
# kystkopi uten fjord-feltene, så de tester det de testet. De faste observasjonene (7.1, 29.5 og 31.1) bruker de ekte spotene.
FJORD_FELT = ("bw_tillit", "transfer", "transfer_locked", "andel_forelopig")
GAP_FELT = ("gap_spot", "gap_soft_edge", "gap_transfer", "gap_edge_taper", "gap_min_share", "swell_window_tegnet")


def kystkopi(spot, behold_gap=False):
    """Spoten som vanlig kyst-spot: bw_tillit "kyst", uten låst andel. behold_gap=True beholder gap-feltene
    (Russelv før 23.11.2026: gap-spot der grensa bare løfter)."""
    bort = FJORD_FELT + (() if behold_gap else GAP_FELT)
    return dict({k: v for k, v in spot.items() if k not in bort and not (k.startswith("_") and k[1:] in bort)}, bw_tillit="kyst")


LK = kystkopi(L)   # Lenangsøyra slik den var før 23.11.2026: standard andel 0,6, ingen gap-felt
assert is_fjord(L) and not is_fjord(LK) and "transfer" not in LK and "gap_spot" not in LK and LK["swell_window"] == L["swell_window"]
# 24.11.2026 (svar.md 23.11.2026 kl. 21.00, S34 a): den ekte Russelv har Breivikeidets vindu, myke kant og andel (345-30,
# 0,22). RH er Russelv slik den var 16.-23.11.2026: tegnet vindu 348-19, hard kant og andel 0,20. Ingen ekte spot har
# hard kant nå, så testene av hard kant og av tallene fra main står på RH og på kystkopien RK (laget fra RH i test 31).
RH = dict({k: v for k, v in R.items() if k not in ("gap_soft_edge", "gap_edge_taper", "gap_min_share", "andel_forelopig")},
          gap_transfer=0.2, transfer=0.2, swell_window_tegnet=[348, 19])
assert is_fjord(RH) and is_fjord(R) and RH["swell_window"] == R["swell_window"] and RH["facing"] == R["facing"]

# 7.1: Lenangsøyra 26.09.2026 - i praksis mest vindsjø, retning på tvers av
# fjorden. Skal bli flatt og markert som uenige kilder.
l1 = rate({"bw_height": 0.7, "bw_height_max": 1.4, "swell_offshore": 1.3, "dir_offshore": 277,
           "height_offshore": 2.7, "period": 9, "bw_dir": 290,
           "wind_speed": 7, "wind_dir": 200, "gust": 10}, L)
show("7.1: Lenangsøyra 26.09 (mest vindsjø)", l1)
assert l1["height"] < 0.35 and l1["likely_flat"] and l1["sources_disagree"] and l1["stars"] == 0

# 7.2: samme dag, men med ekte nordlig svell rett inn mot stranda.
# 23.11.2026: 7.2-7.4 kjøres på kystkopien LK (se over). Den ekte Lenangsøyra regner nå slikt svell som fjord-spot (test 40).
# 06.10.2026, Theodors rettelse (andre runde, se STATUS.md): energifaktoren
# er nå universell - 560 kJ totalenergi er like over standard "zero"-grensa
# (500), faktor 0,66 ganger potensialet ned. Fortsatt ekte kilder enige
# (sources_disagree skal fortsatt være usann - lav energi er ikke det samme
# som uenige kilder).
l2 = rate({"bw_height": 1.0, "swell_offshore": 1.2, "dir_offshore": 19, "height_offshore": 1.3,
           "period": 13, "bw_dir": 5, "wind_speed": 2, "wind_dir": None}, LK)
show("7.2: Lenangsøyra, ekte nordlig svell", l2)
assert l2["stars"] >= 2 and not l2["sources_disagree"]

# 7.3: samme som 7.2, men BarentsWatch-periode 5 s - tydelig vindsjø selv om
# swell_share og retningen isolert sett ser fine ut.
# 17.11.2026 (Theodors regel, se rating.bw_swell_dominates()): gjelder når
# svellandelen ute er under 0,9 (her 1,2 av 1,4 m = 0,86). Med 0,92 som i 7.2
# og svak vind settes den korte perioden til side (7.3b).
l3 = rate({"bw_height": 1.0, "swell_offshore": 1.2, "dir_offshore": 19, "height_offshore": 1.4,
           "period": 13, "bw_dir": 5, "bw_period": 5, "wind_speed": 2, "wind_dir": None}, LK)
show("7.3: samme, men BarentsWatch-periode 5 s", l3)
assert l3["height"] < l2["height"] and l3["stars"] < l2["stars"]
l3b = rate({"bw_height": 1.0, "swell_offshore": 1.2, "dir_offshore": 19, "height_offshore": 1.3,
            "period": 13, "bw_dir": 5, "bw_period": 5, "wind_speed": 2, "wind_dir": None}, LK)
show("7.3b: svellandel 92 %, svak vind", l3b)
assert l3b["height"] == l2["height"] and l3b["stars"] == l2["stars"] and l3b["bw_period_basis"] == "ute"
# kraftig pålandsvind (9 m/s rett inn, facing 0): den korte perioden gjelder igjen
l3c = rate({"bw_height": 1.0, "swell_offshore": 1.2, "dir_offshore": 19, "height_offshore": 1.3,
            "period": 13, "bw_dir": 5, "bw_period": 5, "wind_speed": 9, "wind_dir": 0}, LK)
assert l3c["bw_period_basis"] == "bw" and l3c["height"] < l2["height"]

# 7.4: samme som 7.2, men BarentsWatch-retning fra 80 grader - 70 grader
# skrått på stranda (facing 0). FØR 27.09.2026 (Theodors rettelse, Unstad
# for lav - se STATUS.md) ga dette 0: retningsfaktoren ved punktet alene
# avgjorde. NÅ er dir_offshore=19 godt eksponert (samme retning som 7.2,
# som allerede går opp) - vi vet da at svellet treffer, og stoler ikke
# lenger på BarentsWatch sin egen (upålitelige) retning ved punktet.
# Retningsfaktoren overstyres til 1,0, se barentswatch_height().
l4 = rate({"bw_height": 1.0, "swell_offshore": 1.2, "dir_offshore": 19, "height_offshore": 1.3,
           "period": 13, "bw_dir": 80, "wind_speed": 2, "wind_dir": None}, LK)
show("7.4: samme, men BarentsWatch-retning 80 grader", l4)
# 06.10.2026: samme energifaktor-effekt som 7.2 (560 kJ, faktor 0,66) - se der.
assert l4["height"] == 0.92 and l4["stars"] == 2 and l4["spot_direction_overridden"]

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
           "period": 13, "wind_speed": 2, "wind_dir": None}, LK)   # kystkopien (23.11.2026), se over 7.2
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

# 8.10: 06.10.2026, Theodors rettelse (andre runde, se CLAUDE.md/STATUS.md) -
# period_score() er nå en universell, lineær kurve mellom faste punkter,
# IKKE lenger per spot (gammel spot["min_period"], identisk 8 for alle 8
# spots, ga 8 s FULL uttelling - for sterkt for en kort periode). Fjernet
# fra spots.json (ubrukt alle andre steder, sjekket).
from rating import period_score
assert period_score(None) == 0.5
assert period_score(4) == 0.4    # under laveste punkt: flat på 0,4
assert period_score(6) == 0.4
assert period_score(7) == 0.525  # lineært mellom 6 (0,4) og 8 (0,65)
assert period_score(8) == 0.65
assert period_score(10) == 0.85
assert period_score(12) == 0.95
assert period_score(14) == 1.0
assert period_score(20) == 1.0   # over høyeste punkt: flat på 1,0
print("8.10: period_score() - ny lineær kurve (6/8/10/12/14 s = 0,4/0,65/0,85/0,95/1,0), OK")

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

# 12.1b (Theodor S24 b, 22.11.2026, og S26 b, 23.11.2026): regnelinja sier «og sterk vind» bare når vinden har tatt
# poeng eller er sterk: effektiv vind med kast (effective_wind, samme mål som vindkurven) fra 8 m/s, fralands fra 12 m/s -
# samme grenser som ordet i docs/js/app.js (calmWindWord). Før sto det også i 1 m/s (Seines 21.11.2026 kl. 12-14).
# Bare tekst: poeng, høyde og low_reason er like i alle tilfellene.
blown_base = {"bw_height": 1.2, "bw_period": 5.5, "bw_dir": G["facing"], "swell_offshore": 0.9,
              "height_offshore": 5.9, "dir_offshore": G["facing"], "period": 7}
fra_land = (G["facing"] + 180) % 360
def blown_line(**wind):
    r = rate(dict(blown_base, **wind), G)
    assert (r["stars"], r["low_reason"], r["blown_out"], r["height"]) == (0, "blown_out", True, blown["height"]), r
    lines = [line for line in r["breakdown"] if "blåst ut" in line]
    assert len(lines) == 1, r["breakdown"]
    return lines[0]
STERK = "Surfehøyde: blåst ut - mye vindsjø og sterk vind, ikke surfbart (BarentsWatch 1,2 m totalt ved punktet)"
SVAK = "Surfehøyde: blåst ut - mye vindsjø, ikke surfbart (BarentsWatch 1,2 m totalt ved punktet)"
assert blown_line(wind_speed=14, wind_dir=301, gust=21) == STERK      # den ekte timen: uendret tekst
assert blown_line(wind_speed=1, wind_dir=301, gust=2) == SVAK         # 1 m/s er ikke sterk vind
assert blown_line(wind_speed=7.9, wind_dir=301) == SVAK               # rett under grensa, pålands, uten kast: middelvinden alene
assert blown_line(wind_speed=8.0, wind_dir=301) == STERK              # på grensa
assert blown_line(wind_speed=7.9, wind_dir=301, gust=6) == SVAK       # kast under middelvinden teller ikke
# S26 b: kastene teller med for pålandsvind også (før: 8 m/s middelvind uten kast)
assert blown_line(wind_speed=7.9, wind_dir=301, gust=20) == STERK     # teller som 9,9
assert blown_line(wind_speed=7.9, wind_dir=301, gust=12) == STERK     # Horseid-typen 22.11: 7,9 m/s med kast 12 teller som 9,1
assert blown_line(wind_speed=7.0, wind_dir=301, gust=10.3) == SVAK    # teller som 7,99: rett under
assert blown_line(wind_speed=6.5, wind_dir=301, gust=11.5) == STERK   # teller som nøyaktig 8,0 (6,5 + 0,3 * 5): på grensa
assert blown_line(wind_speed=9.2, wind_dir=fra_land, gust=14) == SVAK   # fralands 9 m/s, teller som 10,6: under 12
assert blown_line(wind_speed=11, wind_dir=fra_land, gust=20) == STERK   # fralands, teller som 13
# grensa for fralandsvind er nøyaktig 12 m/s med kast (11 + min(2, 0,3 * kastene over middelvinden))
assert blown_line(wind_speed=11, wind_dir=fra_land, gust=14) == SVAK    # teller som 11,9
assert blown_line(wind_speed=11, wind_dir=fra_land, gust=14.4) == STERK  # teller som 12,0 (11 + 0,3 * 3,4 = 12,02)
assert blown_line(wind_speed=10, wind_dir=fra_land, gust=30) == STERK   # tillegget for kast stopper på 2: teller som 12,0
# sidevind og skrå pålandsvind følger 8 m/s med kast, ikke fralandsgrensa
from rating import wind_type as _wind_type_s24b
for _off, _wt in ((90, "side"), (270, "side"), (135, "sideonshore"), (225, "sideonshore")):
    _d = (G["facing"] + 180 + _off) % 360
    assert _wind_type_s24b(_d, G) == _wt, (_d, _wind_type_s24b(_d, G))
    assert blown_line(wind_speed=7.9, wind_dir=_d) == SVAK, _wt
    assert blown_line(wind_speed=8.0, wind_dir=_d) == STERK, _wt
    assert blown_line(wind_speed=7.9, wind_dir=_d, gust=12) == STERK, _wt   # S26 b: teller som 9,1
    assert blown_line(wind_speed=6.5, wind_dir=_d, gust=11.4) == SVAK, _wt  # teller som 7,97
    assert blown_line(wind_speed=6.5, wind_dir=_d, gust=11.5) == STERK, _wt  # teller som 8,0
    assert blown_line(wind_speed=9.6, wind_dir=_d, gust=11) == STERK, _wt   # under 12 med kast, men ikke fralands
assert blown_line(wind_speed=5.0) == SVAK                             # ukjent retning under 8 m/s
assert blown_line(wind_speed=9.0) == STERK                            # ukjent retning fra 8 m/s
assert blown_line(wind_speed=6.0, gust=12) == SVAK                    # ukjent retning med kast: teller som 7,8
assert blown_line(wind_speed=6.0, gust=14) == STERK                   # teller som 8,0 (6 + min(2, 2,4))
# samme funksjon gir grensa for ordet i henteren (publish.wind_blamed) - None når vindstyrken mangler, aldri «svak»
from rating import blown_out_wind_strong as _bows
assert _bows(None, 25, "onshore") is None and _bows(7.9, None, "onshore") is False and _bows(7.9, 12, "side") is True
assert _bows(7.9, 12, None) is True and _bows(9.9, None, "offshore") is False and _bows(11.9, None, "offshore") is False and _bows(12.0, None, "offshore") is True
# spots med egen vindkurve (fysikk-kontrolløren og feiljegeren 23.11.2026): middelvinden mot spotens grense, uansett kast,
# og fralands fra den høyeste av grensa og 12 m/s. Se også 37.7 (Breivikeidet) og 38.3 (Unstad).
assert _bows(13.9, 22, "onshore", 14.0) is False and _bows(14.0, None, "onshore", 14.0) is True and _bows(None, 25, "onshore", 14.0) is None
assert _bows(13.9, 22, "offshore", 14.0) is False and _bows(14.0, 14, "offshore", 14.0) is True     # Unstad fralands: 14 (høyere enn 12)
assert _bows(6.5, 11.5, "onshore", 8.0) is False and _bows(8.0, None, "onshore", 8.0) is True         # Breivikeidet: 8 på middelvinden
assert _bows(11.9, 20, "offshore", 8.0) is False and _bows(12.0, None, "offshore", 8.0) is True       # Breivikeidet fralands: 12
assert _bows(13.9, 22, None, 14.0) is False and _bows(14.0, None, None, 14.0) is True                 # ukjent retning
assert "wind_calm_ms" not in rate(dict(blown_base, wind_speed=5, wind_dir=301), G)                    # bare spots med egen kurve har feltet
assert blown_line() == SVAK                                           # mangler vinden, nevnes den ikke
assert blown_line(wind_dir=301, gust=25) == SVAK                      # mangler styrken, nevnes den ikke
# Har vinden tatt poeng, står «og sterk vind» også under 8 m/s. is_blown_out() krever low_hs, og da er potensialet 0,
# så det skjer ikke gjennom rate() i dag: her tvinges flagget på, og linja prøves direkte.
import rating as _rating_s24b
_bb_s24b = _rating_s24b.build_breakdown
_rating_s24b.build_breakdown = lambda *a, **k: _bb_s24b(*a, **dict(k, wind_took_points=True))
try:
    assert blown_line(wind_speed=1, wind_dir=301, gust=2) == STERK    # tatt poeng: teksten står
    assert blown_line(wind_dir=301, gust=25) == SVAK                  # men aldri uten vindstyrke
    assert blown_line() == SVAK
finally:
    _rating_s24b.build_breakdown = _bb_s24b
assert blown_line(wind_speed=1, wind_dir=301, gust=2) == SVAK         # og flagget er av igjen

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
# 06.10.2026, Theodors rettelse (Farstadsanden 337 grader, Nordneset - se
# STATUS.md): samme ekte avstand/bredde-data som produksjonen, slik at
# item 17 under (Unstad 28.09) faktisk PRØVER rating.blocked_by_near_obstacle()
# sin bredde-sjekk mot ekte tall - uten disse to linjene ville item 17 bestått
# "gratis" (feltene mangler, blocked_by_near_obstacle() faller da alltid
# tilbake til False, uavhengig av om bredde-grensa er riktig satt).
U16["exposure_distance_km"], U16["exposure_width_km"] = _fetch16.resolve_obstacle_geometry(
    U16, _exposure_baseline_real)
assert U16["exposure_distance_km"] is not None and U16["exposure_width_km"] is not None

# 16.1: Unstad 26.09.2026 kl. 14:45 (fast observasjon i CLAUDE.md) - minst
# 3 stjerner, og surfehøyden skal være ca. 2,4 m (det faktisk observerte).
# 06.10.2026, Theodors rettelse (andre runde, se STATUS.md): svell_offshore/
# height_offshore var 1,0/1,0 her siden denne testen opprinnelig ble skrevet
# (surf_factor_prior-saken, 30.09.2026) - bare bw_height/bw_dir/surf_factor
# betydde noe DA. Energifaktoren (ny, se rate()) leser disse to feltene -
# rettet til EKTE svell ute (3,48 m/15 s, Theodors egen rekonstruksjon,
# ca. 8350 kJ - 07.10.2026: perioden her er omregnet til 18,75 s, se
# energy_period(), derfor høyere enn den opprinnelige ca. 5300 kJ).
# height_offshore satt likt (ikke en egen vindsjø-andel kjent)
# - gir samme swell_share=1,0 som 1,0/1,0 ga, så selve høyde-/stjernekjeden
# (bw_height, surf_factor_prior) er UENDRET av dette, bare energifaktoren er.
r_2609 = rate({"bw_height": 0.9, "bw_dir": U16["facing"], "bw_period": 15.0, "dir_offshore": 300,
               "swell_offshore": 3.48, "height_offshore": 3.48, "period": 15, "wind_speed": 3.0,
               "wind_dir": sum(U16["offshore_wind"]) // 2}, U16)
show("16.1: Unstad 26.09 kl. 14:45 (surf_factor_prior)", r_2609)
assert r_2609["stars"] >= 3
assert abs(r_2609["surf_height"] - 2.4) < 0.1
assert any(line.startswith("Surf-faktor 1,45 (startverdi fra 2 observasjoner)") for line in r_2609["breakdown"])
assert r_2609["energy_swell_kj"] is not None and r_2609["energy_swell_kj"] >= 2000  # full energifaktor

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

# 19.3: Farstadsanden med 1,6 m svell ute og 10 s (ca. 785 kJ - 07.10.2026,
# Theodors oppgave: energien regnes nå med topperiode når den finnes, ellers
# middelperioden × PEAK_PERIOD_FACTOR_DEFAULT (1,25) - testens hour-mock har
# ingen swell_peak_period, så 10 s × 1,25 = 12,5 s brukes her, se
# energy_period(). Fortsatt godt under Magnus sin "zero"-grense 1500 kJ) skal
# gi klart færre stjerner MED reglene enn UTEN - energifaktoren ganger
# potensialet kraftig ned før vind/tidevann.
# 06.10.2026, Theodors rettelse (andre runde): energifaktoren er nå
# UNIVERSELL - "UTEN lokale regler" (F19_no_rules) får nå OGSÅ en viss
# demping (standardgrensene 2000/500/0,5, ikke lenger nøytral 1,0), bare
# svakere enn Magnus sine strengere 3000/1500/0,7. Sammenligner derfor
# FAKTOREN direkte (fra energy_factor(), robust mot avrunding til hele
# stjerner - ca. 500 kJ havner så vidt over standard-"zero" 500 men langt
# under Magnus sin 1500, så begge dempes, men Magnus sin klart mer) - i
# tillegg til stjernene, som fortsatt skal gå samme vei eller være like
# (aldri at reglene gir FLERE stjerner enn uten).
from rating import energy_factor as _energy_factor
h_lowenergy = {"swell_offshore": 1.6, "height_offshore": 1.8, "dir_offshore": 310, "period": 10,
               "wind_speed": 3, "wind_dir": 130, "gust": 4, "tide": {"state": "lav", "rising": True}}
r_with_rules = rate(h_lowenergy, F19)
r_without_rules = rate(h_lowenergy, F19_no_rules)
show("19.3: Farstadsanden 1,6 m/10 s MED lokale regler", r_with_rules)
show("19.3: Farstadsanden 1,6 m/10 s UTEN lokale regler", r_without_rules)
assert abs(r_with_rules["energy_swell_kj"] - 785) < 50  # "ca. 785 kJ", se oppdatert merknad over
assert r_with_rules["energy_period_source"] == "omregnet"  # ingen swell_peak_period i denne mocken
assert (_energy_factor(F19, r_with_rules["energy_swell_kj"])
        < _energy_factor(F19_no_rules, r_without_rules["energy_swell_kj"]))
assert r_with_rules["stars"] <= r_without_rules["stars"]

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

# 19.6: ingen andre spots (utenom Farstadsanden og, siden 06.10.2026 andre
# runde, Unstad - se STATUS.md) har local_rules - rate() sitt resultat for
# dem skal derfor være identisk med/uten denne hele oppgaven (regresjon mot
# resten av testfila, ikke bare et nytt sjekkpunkt her).
for other_id in ("grotfjord", "tromvik", "ersfjordstranda", "russelv", "lenangsoyra", "steinkrossa"):
    assert spots[other_id].get("local_rules") is None, f"{other_id} skal IKKE ha local_rules"

# ---------- 06.10.2026, Theodors rettelse (urgent): bw_confirms skal ikke
# overstyre en nær, BRED hindring (Farstadsanden/Nordneset) ----------
# Ekte hendelse: Farstadsanden viste treff (heltrukket svellinje, stjerner,
# bw_confirms) for svell ute fra 338 grader - utenfor vinduet [284,326], og
# linja går over Nordneset og skjærene utenfor (dybde 0,1 m i sjøkartet),
# under 1 km fra stranda. bw_confirms (BarentsWatch sin EGEN bekreftelse ved
# punktet) overstyrte eksponeringen uansett - feil når hindringen er NÆR OG
# BRED (geometrien sikrere enn BarentsWatch sin retning der), motsatt av
# Unstad 28.09 (se item 17) som bw_confirms ble laget for (hindring smal/
# fjern, GFS sin retning det usikre leddet). Se rating.blocked_by_near_obstacle()
# og STATUS.md.
from rating import blocked_by_near_obstacle as _blocked_by_near_obstacle
F20 = dict(spots["farstadsanden"])
_smoothed20, _raw20, _warn20 = _fetch.resolve_exposure(F20, _exposure_baseline_real, "Farstadsanden")
assert _warn20 is None
F20["exposure_smoothed"], F20["exposure_raw"] = _smoothed20, _raw20
F20["exposure_distance_km"], F20["exposure_width_km"] = _fetch.resolve_obstacle_geometry(
    F20, _exposure_baseline_real)
assert F20["exposure_distance_km"] is not None and F20["exposure_width_km"] is not None

# 20.1: Nordneset sett fra Farstadsanden - nær (under 2 km) OG bred (over
# 5 km på tvers, klart over WIDE_OBSTACLE_MIN_KM) for retningene som var
# involvert i den ekte hendelsen (328-352). Tallene i seg selv (ikke bare at
# de passerer en grense) - til STATUS.md og til å dokumentere hvorfor dette
# IKKE er samme situasjon som Unstad (se 20.2).
for d in (330, 338, 345, 350):
    dist, width = F20["exposure_distance_km"][d], F20["exposure_width_km"][d]
    print(f"20.1: Farstadsanden {d} grader - hindring {dist} km unna, {width} km bred")
    assert dist is not None and dist < 2.0
    assert width is not None and width >= 2.0

# 20.2: Unstad 245-252 grader - til sammenligning (Theodors eksplisitte
# spørsmål: "vis avstanden til hindringen ved Unstad for retningene 245 til
# 252"). 248-251 er nær (1,6 km) men SMAL (0,61 km) - en skjær/odde svellet
# bøyer seg rundt, ikke en vegg. Skal ALDRI blokkeres av bredde-sjekken,
# uansett hvor nær den er - det er nettopp denne situasjonen (smal, nær
# hindring) rettelsen ikke skal røre, se item 17.
for d in range(245, 253):
    dist = U16["exposure_distance_km"][d]
    width = U16["exposure_width_km"][d]
    print(f"20.2: Unstad {d} grader - hindring {dist} km unna, {width} km bred"
          if dist is not None else f"20.2: Unstad {d} grader - ingen hindring innen 150 km")
    assert not _blocked_by_near_obstacle(d, U16), f"{d} grader skal IKKE blokkeres (smal hindring)"

# 20.3: FAST OBSERVASJON (lagt til CLAUDE.md 06.10.2026, Theodor bekreftet på
# kartet): Farstadsanden, svell fra 330-358 grader over Nordneset (under 1 km
# fra stranda) treffer ikke, uansett hva BarentsWatch sier ved punktet -
# BarentsWatch ser ikke denne skjermingen. Testen her: svell ute fra 338,
# BarentsWatch 1,0 m RETT INN (bw_dir = facing, altså best mulig tenkelig
# "bekreftelse" ved punktet) skal likevel IKKE gi bw_confirms, og høyst 1
# stjerne. Blocked_near slår inn FØR bw_confirms får sjansen til å sette
# dirfac til 1,0.
h_338 = {"bw_height": 1.0, "bw_dir": F20["facing"], "bw_period": 10.0, "dir_offshore": 338,
         "swell_offshore": 1.5, "height_offshore": 2.0, "period": 11.0,
         "wind_speed": 5.0, "wind_dir": 130.0}
r_338 = rate(h_338, F20)
show("20.3: Farstadsanden 338 grader, BarentsWatch 1,0 m rett inn", r_338)
assert r_338["bw_confirms"] is False, "bw_confirms skal IKKE slå inn over Nordneset (338 grader)"
assert r_338["stars"] <= 1, f"forventet høyst 1 stjerne, fikk {r_338['stars']}"
assert r_338["directness"] < 0.667
# 20.4 (audit, meldingens punkt d): nettopp FORDI bw_confirms nå er riktig,
# skal lavstjerne-ordet også si hvorfor (samme root cause som skiva - se
# rating.classify_low_rating() sin "treffer_ikke"-grein, som eksplisitt
# sjekker "not bw_confirms"). sources_disagree skal også slå inn (svellet
# ute og punktet er reelt uenige, ikke en falsk bekreftelse som dekker det).
assert r_338["low_reason"] == "treffer_ikke"
assert r_338["sources_disagree"] is True

# 20.5: positiv kontroll - samme spot, svell ute MIDT I vinduet (305, nær
# full eksponering - 0,974 glattet, ikke nøyaktig 1,0 fordi glattingen
# (sigma 10 grader) alltid bløder noe inn fra Nordneset sin skygge 23 grader
# unna) og BarentsWatch rett inn, skal fortsatt gi bw_confirms og flere
# stjerner. Rettelsen skal bare stoppe FALSKE bekreftelser bak en bred
# hindring, ikke ekte treff på åpen kyst.
h_305 = {"bw_height": 1.0, "bw_dir": F20["facing"], "bw_period": 10.0, "dir_offshore": 305,
         "swell_offshore": 1.5, "height_offshore": 2.0, "period": 11.0,
         "wind_speed": 5.0, "wind_dir": 130.0}
r_305 = rate(h_305, F20)
show("20.5: Farstadsanden 305 grader (åpen kyst), BarentsWatch 1,0 m rett inn", r_305)
assert r_305["bw_confirms"] is True
assert r_305["directness"] >= 0.95
assert r_305["stars"] > r_338["stars"]

# 20.6: item 17 (Unstad 28.09, se over) kjørte FØR denne seksjonen, men bruker
# U16 som nå (etter wiringen ved 20.2) har ekte bredde/avstand-data - dens
# bw_confirms==True og stars>=3 der er derfor allerede en ekte, ende-til-ende
# bekreftelse på at bredde-grensa ikke rører Unstad. Gjentar bare selve
# påstanden her, samlet, som et eksplisitt regresjonspunkt for denne
# seksjonen (ikke en ny beregning).
for h in h_2809:
    r17b = rate(h, U16)
    assert r17b["bw_confirms"] is True and r17b["stars"] >= 3

# ---------- 06.10.2026, Theodors rettelse (andre runde): offshore avgjøres
# av offshore_wind-sektoren (kan være utvidet), men side/side-onshore/onshore
# måles fra FACING, ikke fra sektorens senter eller kant - se wind_type()
# sin docstring for begrunnelsen (en bredere offshore-sektor et sted skal
# ikke gjøre den stikk motsatte, verste retningen mildere) ----------
from rating import wind_type

# 21.1: for en spot der offshore_wind er NØYAKTIG facing+180 ± 45 grader
# (den opprinnelige, implisitte antagelsen for alle 8 spots) er dette
# matematisk identisk med den aller første versjonen (vinkel til SENTERET
# av offshore_wind) - se wind_type() sin docstring for beviset. Sveip hele
# senter-avstanden 0-180 i hele grader for hver spot, sammenlignet mot den
# opprinnelige firedelte grensa (0-45/45-100/100-135/135-180).
#
# MEN: sjekket mot ekte spots.json (06.10.2026) - bare 4 av de 7 andre
# spotene (tromvik, ersfjordstranda, russelv, farstadsanden) har FAKTISK
# offshore_wind nøyaktig sentrert på facing+180 (0 graders avvik). Grøtfjord
# (6 grader), lenangsøyra (opprinnelig 20 grader - se under) og steinkrossa
# (5 grader) avviker - for DISSE endrer rettelsen altså noe reelt (24/80/20
# av 360 grader bytter kategori i den opprinnelige sjekken), ikke bare for
# Unstad. Verifisert: ingen av disse timene endret stjerner i dagens ekte
# 48-timersvarsel (se STATUS.md) - men IKKE en usynlig endring i prinsippet,
# og derfor ikke stilltiende antatt uendret her lenger - testet eksplisitt
# begge veier i stedet. Theodor sa ja til at alle tre endres reelt.
#
# 06.10.2026, andre runde: Lenangsøyra sin facing (var 0, "sett på
# satellittbilde") rettet til 19 grader - midtpunktet av den EKTE, helt
# åpne sektoren (samme landdeteksjon som exposure_baseline.py/
# check_spot.py, se STATUS.md), identisk med swell_window [15,23]. Falt
# avviket fra 80 til 4 av 360 grader - testet under som en egen sjekk,
# IKKE lagt i OFFSET_CENTER_SPOTS sin "avviker reelt"-sjekk lenger (for
# liten/usikker til å garantere n_diff > 0 ved en fremtidig avrundingsendring
# andre steder - se 21.1c).
OLD_BOUNDARIES = ((45, "offshore"), (100, "side"), (135, "sideonshore"), (180, "onshore"))


def old_wind_type_by_center(center_offset):
    for limit, kind in OLD_BOUNDARIES:
        if center_offset <= limit:
            return kind


def old_wind_type(wind_dir, spot):
    from rating import angle_diff as _ad
    a, b = spot["offshore_wind"]
    center = (a + ((b - a) % 360) / 2) % 360
    return old_wind_type_by_center(_ad(wind_dir, center))


# 15.10.2026: farstadsanden tatt ut - offshore_wind UTVIDET til [85,200] (observasjon 15.10, samme regel som Unstad), ikke lenger eksakt facing+180±45
# 16.11.2026: russelv flyttet ned - facing rettet 315 -> 350 (S10), offshore_wind [90,180] beholdt, så senteret (135) er ikke lenger facing+180
EXACT_CENTER_SPOTS = ("tromvik", "ersfjordstranda")
OFFSET_CENTER_SPOTS = ("grotfjord", "lenangsoyra", "steinkrossa", "farstadsanden", "russelv")

for other_id in EXACT_CENTER_SPOTS:
    sp = spots[other_id]
    for d in range(360):
        assert wind_type(d, sp) == old_wind_type(d, sp), f"{other_id} ved {d} grader"
print(f"21.1a: {len(EXACT_CENTER_SPOTS)} spots (offshore_wind nøyaktig sentrert på facing+180) - "
      f"wind_type() matematisk uendret for alle 360 grader, OK")

for other_id in OFFSET_CENTER_SPOTS:
    sp = spots[other_id]
    n_diff = sum(1 for d in range(360) if wind_type(d, sp) != old_wind_type(d, sp))
    assert n_diff > 0, f"{other_id} forventet å avvike fra senter-regelen (offshore_wind ikke sentrert på facing+180)"
print(f"21.1b: {len(OFFSET_CENTER_SPOTS)} spots (offshore_wind IKKE sentrert på facing+180) - "
      f"wind_type() endrer seg reelt for noen grader, bekreftet (ikke antatt uendret)")

# 21.2: Unstad - de fem observasjonene (modellvind, se STATUS.md punkt 14)
# skal ALLE klassifiseres offshore med den utvidede sektoren [70,232] -
# selve grunnen til den første rettelsen.
U21 = spots["unstad"]
assert U21["offshore_wind"] == [70, 232]
_unstad_obs_wind = [
    ("26.09 kl. 14:45", 213), ("26.09 kl. 14:45 (øvre)", 220),
    ("27.09 morgen", 193), ("27.09 morgen (øvre)", 227),
    ("27.09 ettermiddag", 188), ("27.09 ettermiddag (øvre)", 191),
    ("28.09 (allerede riktig)", 145), ("28.09 (øvre)", 150),
    ("05.10", 199), ("05.10 (øvre)", 206),
]
for label, d in _unstad_obs_wind:
    assert wind_type(d, U21) == "offshore", f"{label} ({d} grader) ga {wind_type(d, U21)}, forventet offshore"
print("21.2: Unstad - alle 10 observerte vindretninger (fem observasjoner) er offshore med [70,232], OK")

# 21.3: 06.10.2026, Theodors rettelse (andre runde) - 294,8 grader (Unstad
# sin facing, altså dead onshore, verstefall) skal ALLTID være onshore,
# uansett hvor bred offshore_wind er et annet sted. Dette var selve
# regresjonen den forrige kant-til-sektor-versjonen innførte (294,8/300
# grader ble mildere klassifisert bare fordi sektoren ble bredere på
# S/SSV-siden) - nå målt fra facing i stedet, uavhengig av sektorens bredde.
# 100 grader (midt i den opprinnelige, rene geometriske offshore-sektoren)
# er fortsatt offshore.
assert wind_type(100, U21) == "offshore"
assert wind_type(294.8, U21) == "onshore"
assert wind_type(300, U21) == "onshore"
assert wind_type(335, U21) == "onshore"
print("21.3: Unstad - 100 grader offshore; 294,8 (facing/verstefall), 300 og 335 grader alle onshore "
      "(rettet tilbake fra forrige versjons regresjon), OK")

# ---------- 23: 07.10.2026, Theodors rettelse: "Treffer ikke", ikke "Flatt",
# når retningen er årsaken og energien ute er høy ----------
# Grøtfjord om ca. 10 dager: svell ute 2,3 m/15 s fra 271°, 15° utenfor
# vinduet [286,310], offshore 5 m/s. Appen viste "Flatt, 0,1 m". Energien
# (ca. 3650 kJ - 07.10.2026, Theodors oppgave: perioden her er omregnet til
# 18,75 s, ×PEAK_PERIOD_FACTOR_DEFAULT, ingen swell_peak_period i mocken)
# er godt over "treffer ikke"-grensa uansett - bare selve TALLET endret seg,
# ikke klassifiseringen.
import fetch as _fetch23
_expo23 = json.loads((Path(__file__).parent.parent / "data" / "exposure_baseline.json").read_text())
G23 = dict(G)
_sm23, _raw23, _ = _fetch23.resolve_exposure(G23, _expo23, "Grøtfjord")
if _sm23 is not None:
    G23["exposure_smoothed"], G23["exposure_raw"] = _sm23, _raw23
h_271 = {"swell_offshore": 2.3, "height_offshore": 2.5, "dir_offshore": 271, "period": 15,
         "wind_speed": 5, "wind_dir": 120, "gust": 7}
r_271 = rate(h_271, G23)
show("23.1: Grøtfjord 2,3 m/15 s fra 271° (15° utenfor)", r_271)
assert r_271["stars"] == 0 and r_271["height"] < 0.35
assert r_271["energy_swell_kj"] > 2000
assert r_271["low_reason"] == "treffer_ikke", r_271["low_reason"]
# Samme retning, men LITE energi ute (0,8 m/7 s = ca. 96 kJ, omregnet
# periode 8,75 s): da ER det flatt.
r_271_low = rate({**h_271, "swell_offshore": 0.8, "height_offshore": 1.0, "period": 7}, G23)
assert r_271_low["stars"] == 0 and r_271_low["low_reason"] == "flat", r_271_low["low_reason"]
# Energi ukjent (ingen svellfelt - met.no-reserven): fortsatt "flat" (w, toppen av fila).
assert w["low_reason"] == "flat"
# BarentsWatch-timer rører ikke denne regelen: Grøtfjord 26.09 (2,2 m/15,6 s
# ute fra 272°, BarentsWatch 0,33 m, observert helt flatt) er fortsatt "Flatt".
assert g26["low_reason"] == "flat" and g26["stars"] == 0
# Grøtfjord 25.09 (fast observasjon: 3° utenfor vinduet, helt flatt, 1,76
# m/9,2 s = ca. 510 kJ, over zero-grensa 500): fortsatt 0 stjerner - ordet
# blir "Treffer ikke" (retningen VAR årsaken den dagen), ikke "Flatt".
assert just_outside["stars"] == 0 and just_outside["low_reason"] == "treffer_ikke", just_outside["low_reason"]
print(f"23: retning + høy energi ute = 'Treffer ikke' ({r_271['energy_swell_kj']} kJ), lav energi = 'Flatt', "
      f"BarentsWatch-timer uendret, Grøtfjord 24-26.09 fortsatt 0 stjerner, OK")

# ---------- 24: 07.10.2026, Theodors rettelse punkt 2: periodeavhengig
# diffraksjonsdemping ----------
from rating import diffraction_period_weight, diffraction_damping
assert diffraction_period_weight(None) == 1.0 and diffraction_period_weight(8) == 1.0 and diffraction_period_weight(6) == 1.0
assert diffraction_period_weight(14) == 0.6 and diffraction_period_weight(18) == 0.6
assert round(diffraction_period_weight(11), 4) == 0.8
assert diffraction_damping(None, 12) == 1.0
assert round(diffraction_damping(0.3, 8), 9) == 0.3            # som før ved kort periode (flyttall)
assert round(diffraction_damping(0.3, 14), 4) == round(1 - 0.7 * 0.6, 4)  # 0,58 ved langt svell
assert diffraction_damping(0.3, 11) > diffraction_damping(0.3, 8)
# Grøtfjord 24.09 (met.no/Windy, kortere periode) og 25.09 (9,2 s): fortsatt 0 stjerner (g, w, just_outside over).
assert g["stars"] == 0 and w["stars"] == 0 and just_outside["stars"] == 0 and g26["stars"] == 0
# Theodors time (23.1, 2,3 m/15 s fra 271°): uendret - flat-sperren (0,12 m på
# spoten, under 0,35 m) slår inn FØR dempingen får betydning. 0 stjerner,
# "Treffer ikke".
r_271b = rate(h_271, G23)
assert r_271b["stars"] == 0 and r_271b["height"] == r_271["height"] and r_271b["low_reason"] == "treffer_ikke"
# 07.10.2026, Theodors ja (se spots.json sin _exposure_override_279): 280°
# (6° utenfor) fikk FØR denne rettelsen en 0→2-stjerners effekt fra
# diffraksjonsdempingen alene (0,6-gulvet ved 15 s), nøyaktig det
# fysikk-kontrolløren advarte om - eneste observasjon i 276-285 grader
# (26.09) var helt flatt. Nytt exposure_override (tak 0,2) på nøyaktig
# denne sektoren slår AV den ekstra dempingen helt (needs_extra_damping
# krever exposure_override_cap() is None, se rate()) - 280° gir nå samme,
# lave resultat ved 8 og 15 s, uansett periode.
r_280_15 = rate({**h_271, "dir_offshore": 280}, G23)
r_280_8 = rate({**h_271, "dir_offshore": 280, "period": 8}, G23)
assert r_280_15["stars"] == 0 and r_280_15["low_reason"] == "treffer_ikke", (r_280_15["surf_height"], r_280_15["stars"])
assert r_280_8["surf_height"] == r_280_15["surf_height"]  # overridet gjør perioden irrelevant her
# Overridet er smalt (276-285), ikke en generell bremse på diffraksjons-
# dempingen - diffraction_damping() sin egen periodeavhengighet (testet
# isolert over) er urørt, og 271/272 grader (rett utenfor overridet) har
# fortsatt exposure_override_cap() None, bare dempet av exposure()-kurven.
from rating import exposure_override_cap as _cap23
assert _cap23(271, G23) is None and _cap23(272, G23) is None
assert _cap23(280, G23) == 0.2 and _cap23(285, G23) == 0.2 and _cap23(286, G23) is None
print(f"24: diffraksjonsdemping p(T) - Grøtfjord 24-26.09 fortsatt 0, Theodors time uendret (0 stjerner, {r_271b['height']} m, "
      f"treffer ikke), 280° (nytt override 276-285) uendret ved 8/15 s ({r_280_15['surf_height']} m begge), "
      f"overridet sin grense (271/286 upåvirket) OK")

# ---------- 25: 07.10.2026, Theodors oppgave: energien skal måles i samme
# periode-type (topperiode) som surf-forecast, uten å røre surfehøyde-
# formelen eller selve "Periode"-visningen ----------
from rating import energy_period as _energy_period, PEAK_PERIOD_FACTOR_DEFAULT as _PPFD

# 25.1: ren funksjonstest av energy_period() - fire grener.
assert _energy_period(12, 16) == (16, "topp")  # ekte topperiode finnes - brukes RÅTT, ingen omregning
assert _energy_period(12, None) == (12 * _PPFD, "omregnet")  # ingen topperiode - middelperiode × faktor
assert _energy_period(12, 0) == (12 * _PPFD, "omregnet")  # topperiode 0 (ugyldig) - samme som manglende
assert _energy_period(12, -1) == (12 * _PPFD, "omregnet")  # negativ - samme
assert _energy_period(None, 16) == (16, "topp")  # topperiode finnes selv om middelperioden mangler
assert _energy_period(None, None) == (None, None)  # ingen periode i det hele tatt
assert _energy_period(0, None) == (None, None)  # middelperiode 0 uten topperiode - ingen gyldig periode
print(f"25.1: energy_period() sine fire grener (topp/omregnet/begge mangler/ugyldig topp) - OK")

# 25.2: rate() bruker FAKTISK topperioden når den finnes (swell_peak_period),
# IKKE middelperioden × faktor - og surfehøyden/"Periode"-visningen er
# UENDRET av dette (bare energien skal endre seg, Theodors eksplisitte punkt
# 2). Samme spot/vind/retning/høyde begge ganger, bare swell_peak_period
# forskjellig - skiller ALENE om energien endres eller ikke.
h_peak_base = {"swell_offshore": 2.0, "height_offshore": 2.0, "dir_offshore": 10,  # midt i Russelv sitt vindu [5,15]
               "period": 12, "wind_speed": 3, "wind_dir": 135}  # midt i offshore_wind [90,180]
r_with_peak = rate({**h_peak_base, "swell_peak_period": 16}, R)
r_without_peak = rate({**h_peak_base, "swell_peak_period": None}, R)
show("25.2: med topperiode (16 s)", r_with_peak)
show("25.2: uten topperiode (omregnet fra 12 s)", r_without_peak)
assert r_with_peak["energy_period_source"] == "topp"
assert r_without_peak["energy_period_source"] == "omregnet"
# Surfehøyden (og alt den avhenger av) er HELT uendret - energien er det
# ENESTE som skiller de to kjøringene.
assert r_with_peak["surf_height"] == r_without_peak["surf_height"]
assert r_with_peak["height"] == r_without_peak["height"]
assert r_with_peak["breaking_height"] == r_without_peak["breaking_height"]
# rate() returnerer aldri noen "period"-nøkkel (sjekket: grep "period":
# i rating.py gir ingen treff) - "Periode" i appen er derfor STRUKTURELT
# uendret av dette (leses fra hour["period"], satt av fetch.py FØR rate()
# kalles, aldri overskrevet av resultatet).
#
# Energien MED topperiode skal være HØYERE enn uten (16 s > 12×1,25=15 s).
assert r_with_peak["energy_swell_kj"] > r_without_peak["energy_swell_kj"]
assert abs(r_without_peak["energy_swell_kj"] - _energy_kj(2.0, 12 * _PPFD)) < 0.5
assert abs(r_with_peak["energy_swell_kj"] - _energy_kj(2.0, 16)) < 0.5
# Breakdown-teksten nevner hvilken periode som faktisk ble brukt (Theodors
# punkt 1c - "vis i forklaringen hvilken periode som er brukt").
energy_line_with = next(line for line in r_with_peak["breakdown"] if line.startswith("Energi (svell)"))
energy_line_without = next(line for line in r_without_peak["breakdown"] if line.startswith("Energi (svell)"))
assert "topperiode 16,0 s" in energy_line_with, energy_line_with
assert "omregnet til 15,0 s" in energy_line_without, energy_line_without
print(f"25.2: energy_period_source 'topp'/'omregnet' riktig valgt, surfehøyde/breaking_height UENDRET "
      f"({r_with_peak['surf_height']} m begge), energi {r_without_peak['energy_swell_kj']} kJ (omregnet) "
      f"vs {r_with_peak['energy_swell_kj']} kJ (topp) - breakdown viser begge periodene, OK")


# ---------- 15.10.2026, Theodors del 4: 287° er INNENFOR vinduet 284-326 ----------
# Appen viste «Ute: utenfor vinduet (287°, vindu 284-326°)» (rettet 14.10 i
# directionHitText, se STATUS.md) - testen her er den eksakte vindu-testen som
# både rating.py og appens inSwellWindow skal følge: kantene inklusive.
from rating import in_sector as _in_sector, degrees_outside as _deg_out
F26 = spots["farstadsanden"]
assert F26["swell_window"] == [284, 326]
assert _in_sector(287, F26["swell_window"]) and _deg_out(287, F26) == 0
assert _in_sector(284, F26["swell_window"]) and _in_sector(326, F26["swell_window"])
assert not _in_sector(283, F26["swell_window"]) and _deg_out(283, F26) == 1
assert not _in_sector(327, F26["swell_window"]) and _deg_out(327, F26) == 1
print("26.1: 287° er innenfor Farstadsanden sitt vindu 284-326 (kantene inklusive, 283/327 utenfor) - OK")
# ---------- 15.10.2026, Farstadsanden «Holy portugal» (Martin, kl. 17:20/17:50) ----------
# Store, rene bølger som lukker seg i tuber, 6-8 surfere, sjøsprøyt bakover; hodehøyt til
# godt over hodet, ansikt ca. 2-3 m (anslag fra bilder); Theodor 4-5 stjerner. Inndata: dagens
# kjøring (15.10 kl. 15Z) for timen kl. 17, med BarentsWatch fra det NYE punktet (snitt 900 m@310,
# 2,2 m - se data/bw_point_search/snitt_2026-10-15.md); det gamle punktet (0,71 m, i brytesonen)
# ga «Dårlig» 1,0 m. Kravet er satt som Unstad 27.09: MINST 3 stjerner og surfehøyde minst
# 2,0 m - målet er 4-5 (vinden fra 211° regnes fortsatt som side, sektoren går til 200°, og
# den lokale offshore_strict-regelen tar −0,7 - se STATUS.md). Vindregelen 15.10 (glatt kurve,
# svelldemping, kast maks +2 m/s, lokal regel erstatter) er en del av dette.
F27 = dict(spots["farstadsanden"])
# som produksjonen (fetch.build_spot): glattet eksponering fra data/exposure_baseline.json, så
# retningen 289° får 0,71 («i utkanten av vinduet», bw_confirms) som i rapporten - ikke 1,0
_sm27, _raw27, _warn27 = _fetch.resolve_exposure(F27, _exposure_baseline_real, "Farstadsanden")
assert _warn27 is None
F27["exposure_smoothed"], F27["exposure_raw"] = _sm27, _raw27
F27["exposure_distance_km"], F27["exposure_width_km"] = _fetch.resolve_obstacle_geometry(F27, _exposure_baseline_real)
H27 = {"t": "2026-10-15T15:00Z", "height_offshore": 6.6, "swell_offshore": 4.24, "swell_model": "gfs", "secondary_swell_height": 0.0, "secondary_swell_dir": 0, "secondary_swell_period": 0.0, "swell_peak_period": None, "dir_offshore": 289, "period": 17.35, "turn": 14.399999999999977, "wind_speed": 8.2, "wind_dir": 211.0, "gust": 13.7, "tide": {"level": 0.53, "state": "middels", "rising": False}, "light": "dag", "daylight": True, "bw_interpolated": False, "bw_source": "norce", "bw_file_source": "hustadvika3x2v", "bw_height": 2.19, "bw_height_max": 4.161, "bw_period": 12.896, "bw_dir": 300, "bw_dir_raw": 120}
r27 = rate(dict(H27), F27)
show("27.1: Farstadsanden 15.10 kl. 17, nytt punkt + ny vind", r27)
assert r27["stars"] >= 3 and r27["surf_height"] >= 2.0, (r27["stars"], r27["surf_height"], r27["low_reason"])
assert r27["wind_type"] == "side" and F27["offshore_wind"] == [85, 200]
# samme time med det gamle punktet (0,71 m, i brytesonen): høyden halveres (1,0 m mot observert
# 2-3 m) - det var punktet som tok høyden, og den gamle vindregelen (−2 for 8 m/s side med kast)
# som tok stjernene (1 stjerne i dagens app; med ny vindregel alene 3)
r27_old = rate(dict(H27, bw_height=0.71, bw_height_max=1.35, bw_dir=306, bw_dir_raw=126), F27)
show("27.2: samme time, gammelt punkt 0,71 m", r27_old)
assert r27_old["surf_height"] < 1.5 and r27_old["surf_height"] < r27["surf_height"]
print("27: Farstadsanden 15.10 kl. 17 - nytt punkt + ny vind gir minst 3 stjerner og 2,0 m+, gammelt punkt under 1,5 m - OK")
# ---------- 15.10.2026, Theodors punkt 3: 5-stjerners-porten («Rått») ----------
# Formelen gir aldri 5 selv (potential = min(4, int(5·score))); den femte stjernen gis bare når ALT
# er kjent og oppfylt (five_star_swell_gate + five_star_losses, fysikk-kontrollørens forslag).
from rating import five_star_swell_gate, FIVE_STAR_HS_MIN, FIVE_STAR_PERIOD_MIN, FIVE_STAR_ENERGY_MIN_KJ
EPIC_H = {"bw_height": H_EPIC, "dir_offshore": 300.5, "bw_dir": G["facing"], "turn": 3, "period": 15, "wind_speed": 1, "wind_dir": 120, "swell_offshore": 2.0, "height_offshore": 2.0}
r28 = rate(dict(EPIC_H), G)
assert r28["stars"] == 5 and r28["faded"] == 0 and any(l.startswith("Rått-svell") for l in r28["breakdown"]), (r28["stars"], r28["breakdown"][-3:])
# hvert vilkår brutt alene -> 4 (eller lavere), aldri 5
cases = {
    "periode 12 s": dict(EPIC_H, period=12),
    "energi ukjent": {k: v for k, v in EPIC_H.items() if k not in ("swell_offshore", "height_offshore")},
    "energi under 2 000 kJ": dict(EPIC_H, swell_offshore=1.0, height_offshore=1.0),
    "svell i kanten (288° i 286-310)": dict(EPIC_H, dir_offshore=288),
    "svell utenfor vinduet": dict(EPIC_H, dir_offshore=283),
    "reservemodellen (ingen BarentsWatch)": dict({k: v for k, v in EPIC_H.items() if k not in ("bw_height", "bw_dir")}, height_spot_model=1.0),
    "sidevind 4 m/s (straff 0, men ikke offshore)": dict(EPIC_H, wind_speed=4, wind_dir=30),
    "offshore 11 m/s (straff 0,25)": dict(EPIC_H, wind_speed=11, wind_dir=120),
    "vindretning ukjent (fart 1 m/s)": {k: v for k, v in EPIC_H.items() if k != "wind_dir"},   # kontrollør: ukjent retning skal ikke gi 5
}
for navn, h in cases.items():
    r = rate(dict(h), G)
    assert r["stars"] <= 4, (navn, r["stars"])
    print(f"28.1 {navn:46} {r['stars']} hele, {r['faded']} tapt")
# sidevind 4 m/s: porten (del A) er åpen, men den femte stjernen holdes tilbake -> 4 + 1 blass (vind)
r_side = rate(dict(EPIC_H, wind_speed=4, wind_dir=30), G)
assert r_side["stars"] == 4 and r_side["faded_wind"] == 1 and any(l.startswith("Femte stjerne holdes tilbake: vinden") for l in r_side["breakdown"]), (r_side["stars"], r_side["faded_wind"], r_side["breakdown"][-3:])
# tidevann: spot med preferanse - flo holder den femte tilbake (4 + 1 blass tidevann), ukjent tidevann -> ikke 5
T28 = {**G, "tide": ["lav", "middels"]}   # (T brukes til noe annet lenger opp i fila)
r_flo = rate({**EPIC_H, "tide": {"state": "høy"}}, T28); r_lav = rate({**EPIC_H, "tide": {"state": "lav"}}, T28); r_uk = rate(dict(EPIC_H), T28)
assert r_lav["stars"] == 5 and r_flo["stars"] == 4 and r_flo["faded_tide"] == 1 and r_uk["stars"] == 4, (r_lav["stars"], r_flo["stars"], r_flo["faded_tide"], r_uk["stars"])
# høyden: 0,85 = |h − mid| <= 0,375·(hi − lo) - like innenfor og like utenfor
G_lo, G_hi = G["ideal_height"]; mid = (G_lo + G_hi) / 2
h_in = _solve_h_for_surf_height(mid + 0.37 * (G_hi - G_lo), 15); h_out = _solve_h_for_surf_height(mid + 0.40 * (G_hi - G_lo), 15)
assert rate(dict(EPIC_H, bw_height=h_in), G)["stars"] == 5 and rate(dict(EPIC_H, bw_height=h_out), G)["stars"] == 4
# Farstadsanden 15.10 kl. 17 (test 27) med 3 m/s offshore i stedet for 8 m/s side: Rått (hs 0,85 tar 2,53 m i [1,0, 3,0])
r_fs = rate(dict(H27, wind_speed=3.0, wind_dir=130.0, gust=4.0, tide={"level": 0.3, "state": "lav", "rising": False}), F27)
assert r_fs["stars"] == 5, (r_fs["stars"], r_fs["breakdown"][-4:])
# faste observasjoner: Unstad 26.09-rekonstruksjonen (test 16.x, Theodor: 4 stjerner) oppfyller alle vilkår og får 5 -
# KREVER THEODORS JA (står i PR/STATUS); alle andre faste observasjoner er uendret (sjekket av testene over)
print("28: 5-stjerners-porten - alt oppfylt gir 5, hvert vilkår brutt gir høyst 4, sidevind/flo holder den femte tilbake som blass, Farstadsanden 15.10 med offshore 3 m/s gir Rått - OK")
# 29: BarentsWatch-perioden settes til side når nesten alt ute er svell (17.11.2026, Theodors regel; kilder:
# observasjon 17.11.2026, Theodor (Breivikeidet) og observasjon 16.11.2026 (bilde, Russelv)). Erstatter A1 fra 16.11.
# Tallene er Russelv 16.11 kl. 11Z slik timen ble publisert: BarentsWatch 0,26 m fra 6° med 4,4 s ved punktet,
# svell ute 2,42 m av 2,3 m totalt (andel 1,0) fra 20° med 7,9 s, vind 4,6 m/s fra 106° (fralands ved Russelv).
from rating import (bw_swell_dominates, bw_period_factor, bw_period_factor_for, BW_SWELL_SHARE_MIN, BW_SWELL_PERIOD_MIN_S,
                    BW_SWELL_STRONG_ONSHORE_MS, BW_SWELL_SEAWARD_DEG)
assert (BW_SWELL_SHARE_MIN, BW_SWELL_PERIOD_MIN_S, BW_SWELL_STRONG_ONSHORE_MS, BW_SWELL_SEAWARD_DEG) == (0.9, 7.0, 6.0, 60)
# 29 tester periodefaktoren alene: Russelv som kyst-spot uten gap-feltene (gap-grensa er test 31). 23.11.2026: den ekte
# Russelv er fjord-spot (test 39 og 40), så R29 er en kystkopi. Før 23.11 var den {**R, "gap_spot": False}.
R29 = kystkopi(R)
assert not is_fjord(R29) and "gap_spot" not in R29 and R29["facing"] == R["facing"] and R29["barentswatch_point"] == R["barentswatch_point"]
rus_1611 = {"bw_height": 0.2567, "bw_dir": 6.0, "bw_period": 4.43, "bw_height_max": 0.4877, "swell_offshore": 2.42,
            "height_offshore": 2.3, "dir_offshore": 20, "period": 7.9, "wind_speed": 4.6, "wind_dir": 106.0, "gust": 7.1}
BW29 = (bw_period_factor(4.43), "bw")
# 29.1: svellandel 1,0, 7,9 s ute og svak vind - den korte perioden ved punktet brukes ikke, faktoren er 1,0
assert bw_swell_dominates(rus_1611, R29) and bw_period_factor_for(rus_1611, R29) == (1.0, "ute")
r29 = rate(dict(rus_1611), R29)
r29_unknown = rate(dict(rus_1611, wind_speed=None), R29)
show("29.1: Russelv 16.11 kl. 11Z", r29)
assert r29["height"] > r29_unknown["height"], (r29["height"], r29_unknown["height"])
assert any("ikke brukt" in line for line in r29["breakdown"]), r29["breakdown"]
# 29.2: manglende data er aldri en høyere faktor - ukjent vindstyrke, svellandel eller svellperiode ute gir faktoren som før
assert bw_period_factor_for(dict(rus_1611, wind_speed=None), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, swell_offshore=None), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, height_offshore=None), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, period=None), R29) == BW29
# et anslag fra totalhøyden er ikke en målt svellandel
assert bw_period_factor_for(dict(rus_1611, swell_model="total_fallback"), R29) == BW29
# 29.3: grensene. Svellandel 0,9 eller mer, og svellperiode ute 7 s eller mer.
assert bw_period_factor_for(dict(rus_1611, height_offshore=2.42 / 0.89), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, height_offshore=2.42 / 0.9), R29) == (1.0, "ute")
assert bw_period_factor_for(dict(rus_1611, period=6.9), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, period=7.0), R29) == (1.0, "ute")
# 29.4: unntaket er kraftig pålandsvind på spoten (middelvind fra 6 m/s, pålands eller skrått pålands; grensa er
# fysikk-kontrollørens, 17.11.2026) - den lager sin egen sjø ved punktet. Fralandsvind gjør det aldri. Sterk vind
# med ukjent retning regnes som pålands. Kastene teller ikke.
assert bw_period_factor_for(dict(rus_1611, wind_speed=6.0, wind_dir=350.0), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, wind_speed=6.0, wind_dir=41.0), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, wind_speed=6.0, wind_dir=None), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, wind_speed=5.9, wind_dir=350.0), R29) == (1.0, "ute")
assert bw_period_factor_for(dict(rus_1611, wind_speed=5.9, wind_dir=350.0, gust=14.0), R29) == (1.0, "ute")
assert bw_period_factor_for(dict(rus_1611, wind_speed=12.0, wind_dir=106.0), R29) == (1.0, "ute")
# svak vind med ukjent retning er fortsatt svak vind
assert bw_period_factor_for(dict(rus_1611, wind_dir=None), R29) == (1.0, "ute")
# 29.4b: bølgene ved punktet må komme fra havsiden (under 60° fra facing 350). Ukjent retning ved punktet eller
# ukjent facing: faktoren som før.
assert bw_period_factor_for(dict(rus_1611, bw_dir=49.0), R29) == (1.0, "ute")
assert bw_period_factor_for(dict(rus_1611, bw_dir=291.0), R29) == (1.0, "ute")
assert bw_period_factor_for(dict(rus_1611, bw_dir=50.0), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, bw_dir=290.0), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, bw_dir=170.0), R29) == BW29
assert bw_period_factor_for(dict(rus_1611, bw_dir=None), R29) == BW29
assert bw_period_factor_for(rus_1611, {k: v for k, v in R29.items() if k != "facing"}) == BW29
# 29.5: lav svellandel - faktoren står. Unstad med vindsjø ute (andel 0,83) og Lenangsøyra 26.09 (test 7.1, andel 0,48):
# 7.1 er fortsatt flatt.
U29 = spots["unstad"]
u29 = {"bw_height": 1.2, "bw_dir": 250.0, "bw_period": 5.0, "swell_offshore": 1.5, "height_offshore": 1.8,
       "dir_offshore": 290, "period": 11, "wind_speed": 6, "wind_dir": 225.0, "gust": 9}
assert not bw_swell_dominates(u29, U29) and bw_period_factor_for(u29, U29) == (bw_period_factor(5.0), "bw")
l29 = {"bw_height": 0.7, "bw_height_max": 1.4, "swell_offshore": 1.3, "dir_offshore": 277, "height_offshore": 2.7,
       "period": 9, "bw_dir": 290, "bw_period": 4.5, "wind_speed": 7, "wind_dir": 200, "gust": 10}
assert not bw_swell_dominates(l29, L) and bw_period_factor_for(l29, L) == (bw_period_factor(4.5), "bw")
r29l = rate(dict(l29), L)
assert r29l["height"] < 0.35 and r29l["likely_flat"] and r29l["stars"] == 0, (r29l["height"], r29l["stars"])
# 29.6: faktoren blir aldri LAVERE enn BarentsWatch-perioden alene ga (kort periode ute, lang ved punktet)
assert bw_period_factor_for(dict(rus_1611, bw_period=7.0, period=5.0), R29) == (bw_period_factor(7.0), "bw")
# 29.7: BarentsWatch-periode fra 8 s gir full faktor uansett - uendret. Uten BarentsWatch-periode: nøytralt, ingen basis.
assert bw_period_factor_for(dict(rus_1611, bw_period=9.0), R29) == (1.0, "bw")
assert bw_period_factor_for(dict(rus_1611, bw_period=None), R29) == (bw_period_factor(None), None)
print("29: periodefaktoren ved BarentsWatch-punktet - svellandel fra 0,9 og svellperiode ute fra 7 s setter kort toppperiode til side, unntatt ved pålandsvind fra 6 m/s, og bare når bølgene ved punktet kommer fra havsiden; manglende data og lav svellandel som før; aldri lavere faktor - OK")
# 30: (ledig) A2 med vindhistorikk ble prøvd 16.11.2026 og ikke tatt inn - se rating.bw_period_factor_for().

# 31: gap-regelen (svar.md 16.11.2026 kl. 15.45, funn punkt 3; kilde: observasjon 16.11.2026 (bilde, Russelv)).
# Nedre grense for Hs ved spoten = svell ute × gap_transfer, bare for spots merket gap_spot.
from rating import gap_floor, GAP_MIN_PERIOD_S, GAP_EDGE_DEG
# 22.11.2026: Breivikeidet er også gap-spot (svar.md 22.11.2026 kl. 12.20, se test 36).
# 23.11.2026: Lenangsøyra også (svar.md 23.11.2026 kl. 14.05, se test 39 og 40). Ingen andre.
assert sorted(i for i, sp in spots.items() if sp.get("gap_spot")) == ["breivikeidet", "lenangsoyra", "russelv"]
# 24.11.2026 (svar.md 23.11.2026 kl. 21.00, S34 a): Russelv som Breivikeidet. Vindu 345-30 med myk kant og andel 0,22,
# merket foreløpig. Før: 348-19, hard kant og 0,20 (står på kopien RH). 16.11 kom svellet fra 20°, langs fjordaksen
# (5-25°), så hele andelen gjelder: 2,42 × 0,22 = 0,53 m (før 0,48 m).
B31 = spots["breivikeidet"]
assert R["gap_soft_edge"] is True and R["gap_edge_taper"] == B31["gap_edge_taper"] == [20, 5] and R["andel_forelopig"] is True
assert R["gap_transfer"] == R["transfer"] == B31["gap_transfer"] == 0.22 and R["swell_window_tegnet"] == B31["swell_window_tegnet"] == [345, 30]
assert R["swell_window"] == [[5, 15], [349, 356]]      # det ordinære vinduet er ikke rørt
assert GAP_MIN_PERIOD_S == 7.0 and GAP_EDGE_DEG == 2
assert "gap_soft_edge" not in RH and RH["gap_transfer"] == 0.2 and RH["swell_window_tegnet"] == [348, 19]
assert abs(gap_floor(rus_1611, R) - 2.42 * 0.22) < 1e-9 and abs(gap_floor(rus_1611, RH) - 2.42 * 0.2) < 1e-9
r31 = rate(dict(rus_1611), R)
show("31.1: Russelv 16.11 kl. 11Z med gap-grensa", r31)
# målet i svar.md: 1-2 poeng, sett rundt 1 m. Mer enn 2 er for raust.
assert r31["stars"] in (1, 2) and r31["gap_floor"] and r31["uncertain"] and r31["height"] == 0.53, (r31["stars"], r31["height"])
assert r31["low_reason"] not in ("flat", "treffer_ikke", "blown_out") and not r31["likely_flat"], r31["low_reason"]      # surfbart
assert 0.9 <= r31["surf_height_sets"] <= 1.2, r31["surf_height_sets"]
assert any(line.startswith("Løftet til") for line in r31["breakdown"]), r31["breakdown"]
# 31.2: retningen - i det tegnede vinduet eller høyst 2° utenfor kanten. Den ekte Russelv (345-30) og kopien RH (348-19).
for d, inne in ((345, True), (0, True), (19, True), (22, True), (30, True), (32, True), (33, False), (343, True), (342, False), (90, False)):
    assert (gap_floor(dict(rus_1611, dir_offshore=d), R) is not None) == inne, d
for d, inne in ((348, True), (0, True), (19, True), (21, True), (22, False), (346, True), (345, False), (90, False)):
    assert (gap_floor(dict(rus_1611, dir_offshore=d), RH) is not None) == inne, d
# 31.3: perioden ute minst 7 s
assert gap_floor(dict(rus_1611, period=6.9), R) is None and gap_floor(dict(rus_1611, period=7.0), R) is not None
# 31.4: ikke blåst ut - pålands eller skrått pålands fra 8 m/s tar grensa bort, fralands gjør det aldri
assert wind_type(350.0, R) == "onshore" and wind_type(41.0, R) == "sideonshore" and wind_type(106.0, R) == "offshore"
assert gap_floor(dict(rus_1611, wind_speed=8.0, wind_dir=350.0), R) is None
assert gap_floor(dict(rus_1611, wind_speed=8.0, wind_dir=41.0), R) is None
assert gap_floor(dict(rus_1611, wind_speed=7.9, wind_dir=350.0), R) is not None
assert gap_floor(dict(rus_1611, wind_speed=12.0, wind_dir=106.0), R) is not None
# 31.5: manglende data er aldri en grense (grunnregelen), og anslag fra totalhøyden teller ikke som svell
for mangler in ("swell_offshore", "dir_offshore", "period"):
    assert gap_floor({k: v for k, v in rus_1611.items() if k != mangler}, R) is None, mangler
assert gap_floor(dict(rus_1611, swell_model="total_fallback"), R) is None
# 31.6: bare merkede spots, og bare med tegnet vindu
assert gap_floor(rus_1611, R29) is None and gap_floor(rus_1611, LK) is None and gap_floor(rus_1611, G) is None
assert gap_floor(rus_1611, {k: v for k, v in R.items() if k != "swell_window_tegnet"}) is None
# uten låst gap_transfer: ingen grense. Spotens vanlige transfer (0,6 som standard, og lært etter hvert) brukes aldri.
assert gap_floor(rus_1611, dict({k: v for k, v in R.items() if k != "gap_transfer"}, transfer=0.6)) is None
assert gap_floor(rus_1611, dict(LK, gap_spot=True, swell_window_tegnet=[12, 23], transfer=0.6)) is None
# 31.7: grensa løfter bare. Viser BarentsWatch mer, står BarentsWatch-tallet. Det gjelder en gap-spot som er kyst-spot
# (RK: Russelv slik den var før 23.11.2026, med gap-feltene (348-19, hard kant, 0,20) og uten låst andel).
RK = kystkopi(RH, behold_gap=True)
assert RK["gap_spot"] and RK["gap_transfer"] == 0.2 and "transfer" not in RK and not is_fjord(RK)
r31_hoy = rate(dict(rus_1611, bw_height=1.2, bw_period=8.5), RK)
assert r31_hoy["height"] > 0.48 and not r31_hoy["gap_floor"], (r31_hoy["height"], r31_hoy["gap_floor"])
# 16.11 med 0,20 (RK og RH) ga 0,48 m. Med 0,22 er høyden 0,53 m og poengene de samme.
assert rate(dict(rus_1611), RK)["height"] == rate(dict(rus_1611), RH)["height"] == 0.48
assert rate(dict(rus_1611), RK)["stars"] == rate(dict(rus_1611), RH)["stars"] == r31["stars"]
# 23.11.2026 (bw_tillit, S32 a): den ekte Russelv er fjord-spot. Der står andelshøyden: BarentsWatch løfter den ikke.
r31_fjord = rate(dict(rus_1611, bw_height=1.2, bw_period=8.5), R)
assert r31_fjord["height"] == 0.53 and r31_fjord["uncertain"], (r31_fjord["height"], r31_fjord["uncertain"])
# 31.8: uten BarentsWatch (reserven svell ute) gjelder samme grense
r31_res = rate({k: v for k, v in rus_1611.items() if not k.startswith("bw_")}, R)
assert r31_res["height_source"] == "svell_ute" and r31_res["height"] == 0.53 and r31_res["gap_floor"], (r31_res["height_source"], r31_res["height"])
# 31.9: varselet for 17.11.2026 slik det sto 16.11 kl. 18Z (svell 2,16 m fra 17°, 7,8 s, vind 4,2 m/s fra 41° med kast 8,7).
# Dette er en FORVENTNING, ikke en observasjon (fysikk-kontrollør 16.11.2026). Med periode-regelen fra 17.11 (svellandel
# 0,90, test 29) sto BarentsWatch-høyden 0,65 m × 0,9 = 0,59 m, over gap-grensa 0,43 m, så grensa ble ikke brukt.
# 23.11.2026 (bw_tillit): Russelv er fjord-spot, og høyden er andelshøyden. BarentsWatch løfter den ikke. Kystkopien
# RK gir 0,59 m som før. 24.11.2026 (S34 a): andelen er 0,22, så høyden er 2,16 m × 0,22 = 0,48 m (med 0,20: 0,43 m).
# Det som låses (svar.md 17.11.2026, S17 punkt 5: «Russelv 17.11 (pålands, 3 s): ikke høyere enn i dag»): høyst 1 poeng,
# og «kildene uenige» kapper ikke timen.
rus_1711 = {"bw_height": 0.65, "bw_dir": 2.0, "bw_period": 3.0, "swell_offshore": 2.16, "height_offshore": 2.4,
            "dir_offshore": 17, "period": 7.8, "wind_speed": 4.2, "wind_dir": 41.0, "gust": 8.7}
r31_17 = rate(dict(rus_1711), R)
show("31.9: Russelv 17.11 kl. 11Z (varsel)", r31_17)
assert r31_17["height"] == 0.48 and not r31_17["sources_disagree"] and r31_17["stars"] <= 1, (r31_17["stars"], r31_17["height"])
# med 0,20 (RH) ga timen 0,43 m og 0 poeng. Med 0,22 gir den 1 poeng, som kystkopien RK (main før 23.11): høyst 1 holder.
assert (rate(dict(rus_1711), RH)["height"], rate(dict(rus_1711), RH)["stars"]) == (0.43, 0) and r31_17["stars"] == 1
r31_17k = rate(dict(rus_1711), RK)
assert not r31_17k["gap_floor"] and r31_17k["height"] == 0.59 and not r31_17k["sources_disagree"] and r31_17k["stars"] <= 1, (r31_17k["stars"], r31_17k["height"])
assert r31_17["stars"] <= r31_17k["stars"]   # «ikke høyere enn i dag» gjelder også mot kystkopien
# pålands 7,8 m/s med kast (17.11 kl. 07Z) gir 0: fralands gir svell, pålands gir vindsjø
assert rate(dict(rus_1711, wind_speed=7.8, wind_dir=10.0, gust=12.0), R)["stars"] == 0
# 31.9b: samme time med mer vindsjø ute (svellandel 0,83, periode-regelen gjelder ikke): BarentsWatch-høyden dempes til
# 0,2 m, gap-grensa løfter til 0,43 m, og «kildene uenige» kapper ikke timen bare fordi svellet ligger 2° utenfor det
# BEREGNEDE vinduet når det ligger midt i det TEGNEDE. Uten gap-merket er kildene uenige og timen får 0.
rus_1711_vs = dict(rus_1711, height_offshore=2.6)
r31_vs = rate(dict(rus_1711_vs), R)
assert r31_vs["gap_floor"] and r31_vs["height"] == 0.48 and not r31_vs["sources_disagree"] and r31_vs["stars"] <= 1, (r31_vs["stars"], r31_vs["height"])
assert rate(dict(rus_1711_vs), R29)["sources_disagree"] and rate(dict(rus_1711_vs), R29)["stars"] == 0
# 31.10: unntaket i «kildene uenige» følger retningen ute, ikke om grensa ble brukt (fysikk-kontrollør 16.11.2026):
# mer energi ved punktet skal aldri gi lavere vurdering. Svell 4 m fra 17°, 10 s, BarentsWatch 1,4 m og 1,6 m.
stor = {"bw_dir": 2.0, "bw_period": 9.0, "swell_offshore": 4.0, "height_offshore": 4.2, "dir_offshore": 17, "period": 10.0,
        "wind_speed": 3.0, "wind_dir": 106.0}
r_lav, r_hoy = rate(dict(stor, bw_height=1.4), R), rate(dict(stor, bw_height=1.6), R)
assert not r_lav["sources_disagree"] and not r_hoy["sources_disagree"] and r_hoy["stars"] >= r_lav["stars"], (r_lav["stars"], r_hoy["stars"])
# svell utenfor det tegnede vinduet (33° og mer; 22° og mer på RH) får ikke unntaket; vindsjø-andel og retning ved punktet teller som før
assert rate(dict(rus_1711_vs, dir_offshore=33), R)["sources_disagree"] and not rate(dict(rus_1711_vs, dir_offshore=30), R)["sources_disagree"]
assert rate(dict(rus_1711_vs, dir_offshore=30), RH)["sources_disagree"]
assert rate(dict(rus_1711, swell_offshore=1.0), R)["sources_disagree"]      # svellandel under 50 %
print("31: gap-regelen - bare gap-spots, bare i det tegnede vinduet (±2°), fra 7 s, låst andel, ikke blåst ut, løfter aldri ned; Russelv 16.11 gir 1-2 poeng med 0,53 m (S34 a), 17.11 høyst 1 - OK")

# 32: mildere vindkurver ved svak vind (forslag e, Theodor 16.11.2026: «Se bort ifra vinden, når det er snakk om så lite
# har det jo nesten ingenting å si»). Ingen straff under 6 m/s for side og skrått pålands, under 5 m/s for pålands.
from rating import wind_curve_penalty, WIND_PENALTY_CURVES, BLOWN_OUT_WIND_MS
GAMLE_KURVER_32 = {"offshore": ((10, 0), (14, 1), (18, 2)), "side": ((5, 0), (10, 1), (14, 2), (18, 3)),
                   "sideonshore": ((3, 0), (7, 1), (11, 2), (15, 3)), "onshore": ((2, 0), (5, 1), (8, 2), (11, 3), (14, 4))}
def _gammel_straff(eff, kind):
    pts = GAMLE_KURVER_32[kind]
    if eff <= pts[0][0]:
        return 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if eff <= x1:
            return y0 + (y1 - y0) * (eff - x0) / (x1 - x0)
    return float(pts[-1][1])
assert wind_curve_penalty(6.0, "side") == 0 and wind_curve_penalty(6.0, "sideonshore") == 0 and wind_curve_penalty(5.0, "onshore") == 0
assert WIND_PENALTY_CURVES["offshore"] == GAMLE_KURVER_32["offshore"] and BLOWN_OUT_WIND_MS == 8.0
MOTER_GAMMEL = {"offshore": 0.0, "side": 10.0, "sideonshore": 8.0, "onshore": 8.0}   # herfra og opp er alt som før
for kind in GAMLE_KURVER_32:
    forrige = 0.0
    for i in range(0, 251):
        eff = i / 10
        ny, gml = wind_curve_penalty(eff, kind), _gammel_straff(eff, kind)
        assert ny <= gml + 1e-9, (kind, eff, ny, gml)              # aldri strengere enn før
        assert ny >= forrige - 1e-9, (kind, eff)                   # stiger jevnt
        if eff >= MOTER_GAMMEL[kind]:
            assert abs(ny - gml) < 1e-9, (kind, eff, ny, gml)      # ekte blåst-ut-vind straffes som før
        forrige = ny
print("32: vindkurvene e - ingen straff under 6/6/5 m/s (side/skrått pålands/pålands), aldri strengere enn før, uendret fra 10/8/8 m/s og for fralands - OK")

# 33: Russelv i spots.json etter S10 (ja 16.11.2026): facing 350, punktet lenger ut er hovedpunkt, og eksponeringstabellen gjelder fortsatt
assert R["facing"] == 350 and R["offshore_wind"] == [90, 180]
assert R["barentswatch_point"] == {"lat": 69.952217, "lon": 20.208673} and R["barentswatch_point_shadow"] == {"lat": 69.949979, "lon": 20.215157}
assert _exposure_baseline_real["russelv"]["checksum"] == _spot_checksum(R)
print("33: Russelv - facing 350, byttet BarentsWatch-punkt, sjekksummen i exposure_baseline.json stemmer - OK")

# 34: Breivikeidet 17.11.2026 (fast observasjon; kilde: observasjon 17.11.2026, Theodor): hoftehøyt og rent på sandbanken
# kl. 09-10 norsk tid (08-09Z), hodehøye sett ca. kl. 10.30-10.50 (09.30-09.50Z), vindstille. Appen viste 0 poeng og
# «flatt» hele formiddagen. Kl. 07Z er ikke observert. Timene er slik de ble publisert 16.11 kl. 18Z (07-09Z) og
# 17.11 kl. 11Z (10Z).
from rating import energy_factor, energy_thresholds_used
B34 = spots["breivikeidet"]
assert B34["spot"] == {"lat": 69.6680714, "lon": 19.6554882} and B34["swell_window"] == [345, 30] and B34["ideal_height"] == [0.5, 1.5]
# unntatt energiregelen, og ingen andre spots er det
# (22.11.2026: local_rules har bare den myke tidevannsregelen, ingen energigrense - se test 36)
assert [i for i, sp in spots.items() if sp.get("no_energy_rule")] == ["breivikeidet"] and "min_energy_kj" not in B34["local_rules"]
assert energy_thresholds_used(B34) is None and energy_factor(B34, 900) == 1.0 and energy_factor(B34, 0) == 1.0
assert energy_thresholds_used(spots["grotfjord"])[:2] == (2000, 500) and energy_factor(spots["grotfjord"], 900) < 1.0      # standardgrensene gjelder alle andre
bre_1711 = {
    7: {"height_offshore": 2.4, "swell_offshore": 2.28, "swell_model": "standard", "bw_height": 0.49, "bw_dir": 19.0, "bw_period": 2.73,
        "bw_height_max": 0.93, "dir_offshore": 17, "period": 7.7, "wind_speed": 5.5, "wind_dir": 29.0, "gust": 10.5,
        "tide": {"level": 0.73, "state": "høy", "rising": False}},
    8: {"height_offshore": 2.4, "swell_offshore": 2.24, "swell_model": "standard", "bw_height": 0.43, "bw_dir": 19.0, "bw_period": 2.57,
        "bw_height_max": 0.82, "dir_offshore": 17, "period": 7.75, "wind_speed": 5.4, "wind_dir": 22.0, "gust": 10.5,
        "tide": {"level": 0.47, "state": "middels", "rising": False}},
    9: {"height_offshore": 2.3, "swell_offshore": 2.22, "swell_model": "standard", "bw_height": 0.37, "bw_dir": 19.0, "bw_period": 2.4,
        "bw_height_max": 0.7, "dir_offshore": 17, "period": 7.75, "wind_speed": 4.3, "wind_dir": 14.0, "gust": 9.1,
        "tide": {"level": 0.23, "state": "lav", "rising": False}},
    10: {"height_offshore": 2.3, "swell_offshore": 2.2, "swell_model": "standard", "bw_height": 0.4433, "bw_dir": 19.0, "bw_period": 2.57,
         "dir_offshore": 17, "period": 7.75, "wind_speed": 4.3, "wind_dir": 10.0, "gust": 8.1},
}
r34 = {t: rate(dict(h), B34) for t, h in bre_1711.items()}
for t in sorted(r34):
    show(f"34: Breivikeidet 17.11 kl. {t:02d}Z", r34[t])
for t, r in r34.items():
    # ikke lenger «flatt»: den korte toppperioden ved punktet (2,4-2,7 s) er satt til side, og høyden er hoftehøy
    assert r["bw_period_basis"] == "ute" and not r["likely_flat"] and 0.5 <= r["surf_height"] <= 0.9, (t, r["height"], r["surf_height"])
    assert r["zero_losses"]["energy"] == 0, (t, r["zero_losses"])
# Fast observasjon: kl. 08Z og 09Z (hoftehøyt og rent) gir minst 2 poeng (Theodor 23.11.2026, S27; før: minst 1).
# Varselet sa 5,4 og 4,3 m/s pålands med kast 10,5 og 9,1 mens det var vindstille på stranda. Fra 23.11.2026 tar
# vinden ingen poeng under 8 m/s middelvind på Breivikeidet (wind_local i spots.json, se test 37).
assert r34[8]["stars"] >= 2 and r34[9]["stars"] >= 2, (r34[8]["stars"], r34[9]["stars"])
assert (r34[7]["stars"], r34[8]["stars"], r34[9]["stars"], r34[10]["stars"]) == (2, 2, 2, 2), [r34[t]["stars"] for t in sorted(r34)]   # S27
# uten modellvinden er alle timene 2 poeng: avviket ligger i vindvarselet og ikke i bølgehøyden
for t in (7, 8, 9, 10):
    assert rate(dict(bre_1711[t], wind_speed=1.0, gust=2.0), B34)["stars"] == 2, t
# pålandsvind fra 6 m/s middelvind setter ikke perioden ved punktet til side (bw_period_basis «bw»). Fra 22.11.2026
# holder gap-grensa høyden oppe (test 36). S27 (23.11.2026): under 8 m/s middelvind tar vinden ingen poeng på
# Breivikeidet, så timen er 2 også med 6 m/s. Fra 8 m/s faller gap-grensa bort, og timen er blåst ut som før.
r34_vind = rate(dict(bre_1711[8], wind_speed=6.0), B34)
assert r34_vind["bw_period_basis"] == "bw" and r34_vind["stars"] == 2 and r34_vind["faded_wind"] == 0, (r34_vind["bw_period_basis"], r34_vind["stars"])
assert r34_vind["gap_floor"] and r34_vind["low_reason"] is None, (r34_vind["gap_floor"], r34_vind["low_reason"])
r34_vind8 = rate(dict(bre_1711[8], wind_speed=8.0), B34)
assert r34_vind8["stars"] == 0 and not r34_vind8["gap_floor"] and r34_vind8["low_reason"] == "blown_out", (r34_vind8["stars"], r34_vind8["low_reason"])
# 17.11-timene har ikke vannstand i cm (publisert før 22.11.2026): tidevannsregelen tar ingenting, og linja sier at
# vannstanden mangler (aldri «tåler alt» for en spot med regelen, fysikk-kontrolløren 22.11.2026)
assert all("Tidevann: vannstanden mangler, ingen straff" in r["breakdown"] and "Tidevann: spoten tåler alt" not in r["breakdown"]
           and r["local_rules"]["lines"] == ["Tidevann: vannstanden mangler, ingen straff"] and r["local_rules"]["stars_lost"] == 0 for r in r34.values())
print("34: Breivikeidet 17.11 - ikke flatt, hoftehøyt, uten energiregel; kl. 07-10Z gir 2, 2, 2, 2 poeng (S27), også uten modellvinden; 8 m/s pålands er blåst ut - OK")
# 35: ukjent vind (19.11.2026, fysikk-kontrollørens regel, forslag til svar.md S22; kilder: samme konvensjon som
# wind_penalty() og bw_swell_dominates() (ukjent retning regnes som pålands), og grunnregelen: manglende data er aldri 0).
from rating import gap_blocked_by_wind, BLOWN_OUT_WIND_MS, FLAT_HS_THRESHOLD
assert BLOWN_OUT_WIND_MS == 8.0
# 35.1: kjent styrke fra 8 m/s og ukjent retning tar gap-grensa bort, som kjent pålandsvind. Under 8 m/s står den.
assert gap_floor(dict(rus_1611, wind_speed=8.0, wind_dir=None), R) is None and gap_blocked_by_wind(dict(rus_1611, wind_speed=8.0, wind_dir=None), R)
assert abs(gap_floor(dict(rus_1611, wind_speed=7.9, wind_dir=None), R) - 2.42 * 0.22) < 1e-9
assert not gap_blocked_by_wind(dict(rus_1611, wind_speed=7.9, wind_dir=None), R) and not gap_blocked_by_wind(dict(rus_1611, wind_speed=12.0, wind_dir=106.0), R)
# sidevind tar ikke grensa bort, heller ikke ved 12 m/s (feiljegeren 21.11.2026): bare pålands, skrå pålands og ukjent retning
from rating import wind_type as wind_type35
h35_side = dict(rus_1611, wind_speed=12.0, wind_dir=240.0)
assert wind_type35(240.0, R) == "side" and not gap_blocked_by_wind(h35_side, R) and abs(gap_floor(h35_side, R) - 2.42 * 0.22) < 1e-9
# hjelperen følger de samme vilkårene som grensa: bare gap-spots, bare svell i vinduet, bare fra 7 s
u35 = dict(rus_1611, wind_speed=9.0, wind_dir=None)
assert gap_blocked_by_wind(u35, R) and not gap_blocked_by_wind(u35, R29) and not gap_blocked_by_wind(u35, G)
assert not gap_blocked_by_wind(dict(u35, dir_offshore=33), R) and not gap_blocked_by_wind(dict(u35, period=6.9), R)
assert not gap_blocked_by_wind(dict(u35, dir_offshore=30), RH) and gap_blocked_by_wind(dict(u35, dir_offshore=30), R)
# 35.2: ukjent STYRKE tar ikke grensa bort. Høyden står (0,53 m), og vinden vi mangler koster sitt faste ene poeng.
ukjent35 = dict(wind_speed=None, wind_dir=None, gust=None)
assert abs(gap_floor(dict(rus_1611, **ukjent35), R) - 2.42 * 0.22) < 1e-9 and not gap_blocked_by_wind(dict(rus_1611, **ukjent35), R)
r35_obs = rate(dict(rus_1611, **ukjent35), R)
assert r35_obs["gap_floor"] and r35_obs["uncertain"] and r35_obs["height"] == 0.53, (r35_obs["gap_floor"], r35_obs["height"])
# 35.6: observasjonstimen uten vindvarsel får aldri vinden som grunn
assert r35_obs["low_reason"] != "blown_out" and r35_obs["zero_losses"]["wind"] == 0, (r35_obs["low_reason"], r35_obs["zero_losses"])
# 35.3: en tenkt time med mye svell gjennom gapet (4,0 m, 10 s fra 10°; BarentsWatch 0,3 m med 4 s ved punktet)
def t35(**kw):
    h = dict(swell_offshore=4.0, height_offshore=4.4, swell_model="gfs", dir_offshore=10, period=10.0, bw_height=0.3, bw_dir=350.0,
             bw_period=4.0, wind_speed=2.0, wind_dir=135.0, gust=None, tide={"level": 0.5, "state": "middels", "rising": True}, turn=0)
    h.update(kw)
    return h
r35 = {"fralands": rate(t35(), R), "palands": rate(t35(wind_speed=9.0, wind_dir=350.0), R),
       "retning": rate(t35(wind_speed=9.0, wind_dir=None), R), "styrke": rate(t35(**ukjent35), R)}
for k in ("fralands", "palands", "retning", "styrke"):
    show(f"35.3: Russelv, svell 4,0 m, vind {k}", r35[k])
assert r35["fralands"]["stars"] == 3 and r35["fralands"]["gap_floor"] and r35["fralands"]["low_reason"] is None
# kjent pålands 9 m/s: grensa er borte, og timen er blåst ut, ikke flat (C)
assert (r35["palands"]["stars"], r35["palands"]["low_reason"], r35["palands"]["gap_floor"]) == (0, "blown_out", False), r35["palands"]
# ukjent retning ved 9 m/s gir det samme som kjent pålands, ikke et poeng mer (før: 1 poeng med grensa)
assert (r35["retning"]["stars"], r35["retning"]["low_reason"], r35["retning"]["gap_floor"]) == (0, "blown_out", False), r35["retning"]
# ukjent styrke: grensa står, ett poeng under beste kjente, og ingen vindgrunn
assert (r35["styrke"]["stars"], r35["styrke"]["low_reason"], r35["styrke"]["gap_floor"]) == (2, None, True), r35["styrke"]
assert r35["styrke"]["stars"] <= r35["fralands"]["stars"] - 1 and r35["styrke"]["faded_wind"] == 1
# 35.4: samme time med 2,5 m svell og ukjent vind: 1 poeng uten vindgrunn (før: blown_out)
r35_25 = rate(t35(swell_offshore=2.5, **ukjent35), R)
assert (r35_25["stars"], r35_25["low_reason"]) == (1, None), (r35_25["stars"], r35_25["low_reason"])
# 35.5: en vanlig spot. Grøtfjord, svell 1,0 m, 10 s fra 300°, BarentsWatch 0,9 m med 9 s: kjent svak fralandsvind gir 2 poeng,
# ukjent vind 1 poeng uten vindgrunn (før: blown_out).
g35 = dict(swell_offshore=1.0, height_offshore=1.1, dir_offshore=300, bw_height=0.9, bw_dir=300.0, bw_period=9.0)
r35_g, r35_gu = rate(t35(**g35, wind_dir=120.0), G), rate(t35(**g35, **ukjent35), G)
assert r35_g["stars"] == 2 and (r35_gu["stars"], r35_gu["low_reason"]) == (1, None), (r35_g["stars"], r35_gu["stars"], r35_gu["low_reason"])
# 35.7: målingen rører vi ikke. Mest vindsjø ved punktet (BarentsWatch 0,8 m, svellandel 0,3) er blåst ut også uten vindvarsel.
from rating import is_blown_out
assert is_blown_out(dict(bw_height=0.8, **ukjent35), G, "barentswatch", {"swell_share": 0.3}, True)
assert not is_blown_out(dict(bw_height=0.8, **ukjent35), G, "barentswatch", {"swell_share": 0.9}, True)
# Og gjennom rate(): kravet om kjent styrke gjelder bare vindstraffen (wind_dominant), ikke målingen. Uten vindvarsel er
# timen fortsatt blown_out når BarentsWatch måler mest vindsjø (fysikk-kontrolløren 19.11.2026: uten denne ble den stormsjo).
h35_sjo = dict(swell_offshore=0.4, height_offshore=1.5, swell_model="gfs", dir_offshore=300, period=8.0, bw_height=0.8,
               bw_dir=300.0, bw_period=3.5, tide={"level": 0.5, "state": "middels", "rising": True}, turn=0, **ukjent35)
assert (rate(h35_sjo, G)["low_reason"], rate(h35_sjo, G)["blown_out"]) == ("blown_out", True), (rate(h35_sjo, G)["low_reason"], rate(h35_sjo, G)["blown_out"])
# 35.8: bokføringen ved ukjent styrke. Det faste poenget står under "cap" og ikke under "wind", så ordet ved 0 poeng blir
# «Ikke surfbart nå» og ikke «Blåst ut». Stjernene er de samme som før.
r35_0 = rate(t35(**dict(g35, swell_offshore=2.0, height_offshore=2.1, bw_height=1.8), **ukjent35), G)
assert r35_0["stars"] == 0 and r35_0["low_reason"] is None and r35_0["faded_wind"] == 1, (r35_0["stars"], r35_0["low_reason"], r35_0["faded_wind"])
assert r35_0["zero_losses"]["wind"] == 0 and r35_0["zero_losses"]["cap"] >= 1, r35_0["zero_losses"]
# kjent vind bokføres som før. 23.11.2026 (bw_tillit): på fjord-spoten står andelshøyden også når vinden tar grensa bort.
# Taket for usikkert varsel (4 til 3) bokføres da som i fralandstimen, og vinden tar de tre poengene. På kystkopien RK
# er høyden 0,09 m og ingenting bokføres (som den ekte Russelv før 23.11).
assert r35["retning"]["zero_losses"]["wind"] == 3 and r35["retning"]["zero_losses"]["cap"] == r35["fralands"]["zero_losses"]["cap"] == 1, r35["retning"]["zero_losses"]
assert rate(t35(wind_speed=9.0, wind_dir=None), RK)["zero_losses"]["cap"] == 0 and rate(t35(wind_speed=7.9, wind_dir=None), R)["zero_losses"]["wind"] == 2
# 35.9: ordet når vinden tar grensa bort. Varselet for Russelv 22.11.2026 kl. 01Z (svell 1,16 m fra 352°, 9,6 s, 8,35 m/s fra
# 304°): grensa ville vært 0,23 m, under flat-sperren, så timen er flat med og uten vinden. Ordet er fortsatt flat.
h35_live = t35(swell_offshore=1.16, height_offshore=1.3, dir_offshore=352, period=9.6, wind_speed=8.35, wind_dir=304.0)
assert gap_blocked_by_wind(h35_live, R) and 1.16 * R["gap_transfer"] < FLAT_HS_THRESHOLD
assert (rate(h35_live, R)["stars"], rate(h35_live, R)["low_reason"]) == (0, "flat")
assert rate(dict(h35_live, wind_speed=2.0, wind_dir=135.0), R)["low_reason"] == "flat"
# med 2,5 m svell (grense 0,5 m) er samme vind «blåst ut»
assert rate(dict(h35_live, swell_offshore=2.5, height_offshore=2.7), R)["low_reason"] == "blown_out"
# akkurat på flat-sperren er timen blåst ut, rett under er den flat (feiljegeren 21.11.2026). RH: svell 1,75 m ganger 0,2
# = 0,35 m, og 1,74 m er under. Den ekte Russelv (0,22 fra 24.11.2026): 1,60 m gir 0,352 m, og 1,59 m gir 0,3498 m.
sv35 = FLAT_HS_THRESHOLD / RH["gap_transfer"]
assert sv35 * RH["gap_transfer"] == FLAT_HS_THRESHOLD > 1.74 * RH["gap_transfer"]
assert rate(t35(swell_offshore=sv35, height_offshore=1.95, wind_speed=9.0, wind_dir=350.0), RH)["low_reason"] == "blown_out"
assert rate(t35(swell_offshore=1.74, height_offshore=1.94, wind_speed=9.0, wind_dir=350.0), RH)["low_reason"] == "flat"
assert 1.60 * R["gap_transfer"] >= FLAT_HS_THRESHOLD > 1.59 * R["gap_transfer"]
assert rate(t35(swell_offshore=1.60, height_offshore=1.80, wind_speed=9.0, wind_dir=350.0), R)["low_reason"] == "blown_out"
assert rate(t35(swell_offshore=1.59, height_offshore=1.79, wind_speed=9.0, wind_dir=350.0), R)["low_reason"] == "flat"
print("35: ukjent vind - ukjent retning fra 8 m/s regnes som pålands for gap-grensa, ukjent styrke beholder grensa og får aldri vinden som grunn, det faste poenget bokføres som usikkert varsel - OK")

# 36: Breivikeidet 22.11.2026 (fast observasjon; kilde: observasjon 22.11.2026, Theodor): rene, fine bølger, omtrent som
# 17.11 og kanskje litt mindre, i vannet kl. 09.00-11.30 norsk tid (08.00-10.30Z), «definitivt best på laveste vann».
# Appen sa 0 poeng og 0,0 m hele dagen: svellet ute kom fra 349-2°, utenfor det gamle vinduet 15-25, og svellandelen
# (0,74-0,76) var for lav til at den korte perioden ved punktet ble satt til side. Timene er fra varselet 21.11 kl. 11Z,
# vannstanden fra Kartverkets flo og fjære samme dag. Svar og krav: svar.md 22.11.2026 kl. 12.20 (S19).
import datetime as _dt36
import tide as _tide36
from rating import gap_edge_factor, gap_floor_height, gap_swell_in_window, tide_level_penalty
B36 = spots["breivikeidet"]
assert B36["swell_window"] == B36["swell_window_tegnet"] == [345, 30] and B36["gap_spot"] and B36["gap_transfer"] == 0.22 and B36["gap_edge_taper"] == [20, 5]   # S27
# 23.11.2026 (svar.md 23.11.2026 kl. 14.05): Lenangsøyra har samme vindu og myke kant som Breivikeidet (test 39 og 40).
# 24.11.2026 (svar.md 23.11.2026 kl. 21.00, S34 a): Russelv også.
assert sorted(i for i, sp in spots.items() if sp.get("gap_soft_edge")) == ["breivikeidet", "lenangsoyra", "russelv"]
assert [i for i, sp in spots.items() if (sp.get("local_rules") or {}).get("tide_level")] == ["breivikeidet"]
assert B36["local_rules"]["tide_level"] == {"full_below_cm": 200, "max_at_cm": 280, "penalty": 0.7} and B36["local_rules"]["weight"] == 0.7
assert B36["transfer"] == B36["gap_transfer"] and B36["transfer_locked"] and "tide" not in B36 and "exposure_override" not in B36
# skyggepunktet er bare til logging (S19 a): ratingen leser fortsatt hovedpunktet
assert B36["barentswatch_point_shadow"] == {"lat": 69.671471, "lon": 19.659025} and B36["barentswatch_point"] != B36["barentswatch_point_shadow"]
ev36 = [{"time": "2026-11-22T03:54:00+00:00", "type": "fjære", "cm": 81}, {"time": "2026-11-22T10:10:00+00:00", "type": "flo", "cm": 280},
        {"time": "2026-11-22T16:18:00+00:00", "type": "fjære", "cm": 98}]
def tide36(t):
    return _tide36.state_at(ev36, _dt36.datetime(2026, 11, 22, t, 30, tzinfo=_dt36.timezone.utc))
# 36.1: vannstanden i cm følger samme kurve som nivået (cosinus mellom flo og fjære). Uten cm i hendelsene: ingen cm.
assert tide36(8) == {"level": 0.84, "state": "høy", "rising": True, "cm": 247} and tide36(10)["cm"] == 279 and tide36(13)["cm"] == 177
assert "cm" not in _tide36.state_at([{k: v for k, v in e.items() if k != "cm"} for e in ev36], _dt36.datetime(2026, 11, 22, 8, 30, tzinfo=_dt36.timezone.utc))
# (t, total ute, svell ute, retning, periode, BarentsWatch-høyde, vind, kast, vindretning)
rad36 = [(7, 3.9, 2.90, 349, 7.65, 0.36, 4.6, 8.1, 332), (8, 3.8, 2.88, 350, 7.60, 0.36, 5.1, 8.9, 317), (9, 3.8, 2.86, 351, 7.55, 0.35, 5.2, 9.7, 314),
         (10, 3.7, 2.60, 355, 7.50, 0.35, 5.3, 9.5, 319), (11, 3.6, 2.32, 358, 7.50, 0.34, 4.0, 9.1, 329), (12, 3.4, 2.06, 2, 7.45, 0.34, 4.0, 7.8, 330),
         (13, 3.3, 2.02, 2, 7.35, 0.34, 1.7, 6.6, 165)]
bre_2211 = {t: {"height_offshore": tot, "swell_offshore": sv, "swell_model": "standard", "bw_height": bw, "bw_dir": 347.0, "bw_period": 1.6,
                "dir_offshore": d, "period": p, "wind_speed": ws, "wind_dir": float(wd), "gust": g, "tide": tide36(t)}
            for (t, tot, sv, d, p, bw, ws, g, wd) in rad36}
r36 = {t: rate(dict(h), B36) for t, h in bre_2211.items()}
for t in sorted(r36):
    show(f"36: Breivikeidet 22.11 kl. {t:02d}Z", r36[t])
# 36.2: fast observasjon. Kl. 08Z og 09Z minst 2 poeng (Theodor 23.11.2026, S27; før: kl. 08Z minst 1), og surfehøyde
# ca. 0,4-0,8 m i timene Theodor var i vannet.
assert r36[8]["stars"] >= 2 and r36[9]["stars"] >= 2, (r36[8]["stars"], r36[9]["stars"])
for t in (8, 9, 10):
    assert r36[t]["stars"] >= 2 and 0.4 <= r36[t]["surf_height"] <= 0.8 and not r36[t]["likely_flat"], (t, r36[t]["stars"], r36[t]["surf_height"])
    # høyden er et anslag (gap-grensa), merket usikkert og derfor aldri over 3
    assert r36[t]["gap_floor"] and r36[t]["uncertain"] and r36[t]["bw_period_basis"] == "bw", (t, r36[t]["gap_floor"], r36[t]["bw_period_basis"])
    # uten modellvinden (5 m/s på skrå inn, kast 9-10) er timene også 2 poeng: tidevannsregelen alene tar aldri et poeng
    assert rate(dict(bre_2211[t], wind_speed=1.0, gust=2.0), B36)["stars"] == 2, t
assert [r36[t]["stars"] for t in sorted(r36)] == [2, 2, 2, 2, 2, 2, 2], [r36[t]["stars"] for t in sorted(r36)]   # S27
# Før S27 var kl. 12-13Z under flat-sperren (svell 2,0 m ganger 0,165 = 0,33-0,34 m).
# S27: kl. 12-13Z (2,0 m fra 2°) gir andelen 0,209 (0,95 av 0,22) 0,42-0,43 m, over flat-sperren. Ikke observert (Theodor var ute kl. 10.30Z).
assert all(not r36[t]["likely_flat"] and r36[t]["low_reason"] is None for t in (12, 13)), [(r36[t]["likely_flat"], r36[t]["low_reason"]) for t in (12, 13)]
# 36.3: myk kant. Fem grader innenfor kanten er hele andelen, på kanten to tredeler, og to grader utenfor er siste time
# som regnes med. Lenger ut gjelder ikke grensa, og timen er flat som før.
h36 = bre_2211[8]
# S27: fra den vestre kanten (345) går andelen opp over 20 grader, fra den østre (30) over 5. 350° gir 0,75 av 0,22 = 0,165.
assert abs(gap_edge_factor(h36, B36) - 0.75) < 0.001 and abs(gap_floor_height(h36, B36) - 2.88 * 0.165) < 0.001
assert abs(gap_edge_factor(dict(h36, dir_offshore=345), B36) - 2 / 3) < 0.01 and abs(gap_edge_factor(dict(h36, dir_offshore=30), B36) - 2 / 3) < 0.01
assert gap_edge_factor(dict(h36, dir_offshore=343), B36) < gap_edge_factor(dict(h36, dir_offshore=345), B36) < gap_edge_factor(dict(h36, dir_offshore=347), B36) < 1.0
assert gap_swell_in_window(dict(h36, dir_offshore=343), B36) and not gap_swell_in_window(dict(h36, dir_offshore=342), B36)
assert not gap_swell_in_window(dict(h36, dir_offshore=33), B36)
# vinduet krysser nord: 359, 0, 0,4 og 360 grader er alle midt i, med hele andelen
for d36 in (359.0, 359.6, 0, 0.4, 360.0):
    assert gap_swell_in_window(dict(h36, dir_offshore=d36), B36) and 0.89 < gap_edge_factor(dict(h36, dir_offshore=d36), B36) < 0.93, d36
# hele andelen langs fjordaksen (5-25°), og den østre kanten som før (5 grader)
for d36 in (5, 10, 17, 20, 25):
    assert gap_edge_factor(dict(h36, dir_offshore=d36), B36) == 1.0, d36
assert abs(gap_edge_factor(dict(h36, dir_offshore=27), B36) - (0.667 + 0.333 * 3 / 5)) < 1e-9
# uten gap_edge_taper er faktoren den samme som før (directness mot det tegnede vinduet, 5 grader fra begge kanter)
B36_uten = {k: v for k, v in B36.items() if k != "gap_edge_taper"}
from rating import directness as _dir36
for d36 in range(343, 393):
    assert gap_edge_factor(dict(h36, dir_offshore=d36 % 360), B36_uten) == _dir36(d36 % 360, {"swell_window": [345, 30]}), d36
r36_ute = rate(dict(h36, dir_offshore=340), B36)
assert not r36_ute["gap_floor"] and r36_ute["stars"] == 0 and r36_ute["likely_flat"], (r36_ute["gap_floor"], r36_ute["stars"])
# Uten myk kant (RH, Russelv før 24.11.2026): hele andelen også på kanten av det tegnede vinduet (348-19)
assert gap_edge_factor(dict(rus_1611, dir_offshore=348), RH) == 1.0 and abs(gap_floor_height(dict(rus_1611, dir_offshore=348), RH) - 2.42 * 0.2) < 1e-9
# 24.11.2026 (S34 a): den ekte Russelv har samme myke kant som Breivikeidet, grad for grad
for d36 in range(343, 393):
    assert gap_edge_factor(dict(rus_1611, dir_offshore=d36 % 360), R) == gap_edge_factor(dict(h36, dir_offshore=d36 % 360), B36), d36
# 36.4: de vanlige vilkårene for gap-grensa gjelder. Kort periode (under 7 s) og pålandsvind fra 8 m/s tar den bort.
assert not rate(dict(h36, period=6.9), B36)["gap_floor"] and rate(dict(h36, period=6.9), B36)["stars"] == 0
assert not rate(dict(h36, wind_speed=8.0, wind_dir=20.0), B36)["gap_floor"]
# 36.5: tidevannsregelen. Full uttelling til 2,0 m, jevnt opp til 0,7 × 0,7 = 0,49 ved 2,8 m, og aldri mer.
def lvl36(cm):
    return tide_level_penalty({"tide": {"level": 0.5, "state": "middels", "rising": True, "cm": cm}}, B36)
assert lvl36(150)[0] == 0.0 and lvl36(200)[0] == 0.0 and "ingen straff" in lvl36(200)[1]
assert abs(lvl36(240)[0] - 0.245) < 1e-9 and abs(lvl36(280)[0] - 0.49) < 1e-9 and abs(lvl36(330)[0] - 0.49) < 1e-9
# formen på regelen (feiljegeren 22.11.2026): grensene må stå i rekkefølge, weight må finnes, regelen alene tar aldri et
# helt poeng (aldri sperre), og den kombineres ikke med en vanlig tidevannspreferanse - da ville linja i regnestykket
# skjult det andre fradraget. Negativ vannstand gir ingen straff og skrives ikke som «-0,0 m».
for i36, sp36 in spots.items():
    tl36 = (sp36.get("local_rules") or {}).get("tide_level")
    if tl36:
        assert 0 <= tl36["full_below_cm"] < tl36["max_at_cm"] and 0 < sp36["local_rules"]["weight"] * tl36["penalty"] < 0.5, i36
        assert "tide" not in sp36 and "tide_prefer" not in sp36["local_rules"], i36
assert lvl36(-4) == (0.0, "Tidevann (0,0 m over sjøkartnull): lavt nok, ingen straff"), lvl36(-4)
assert lvl36(280)[0] < 0.5       # under et halvt poeng: regelen alene runder aldri et poeng bort
assert "jo lavere vann, jo bedre" in lvl36(247)[1] and "2,5 m over sjøkartnull" in lvl36(247)[1] and "−0,29" in lvl36(247)[1]
# manglende vannstand er aldri 0 og gir aldri straff: uten cm, uten tidevann i det hele tatt, og for spots uten regelen
mangler36 = (0.0, "Tidevann: vannstanden mangler, ingen straff")
assert tide_level_penalty({"tide": {"level": 0.99, "state": "høy", "rising": True}}, B36) == mangler36
assert tide_level_penalty({"tide": None}, B36) == mangler36 and tide_level_penalty({}, B36) == mangler36
assert tide_level_penalty({"tide": tide36(10)}, spots["unstad"]) == (0.0, None) and tide_level_penalty({"tide": tide36(10)}, R) == (0.0, None)
r36_ucm = rate(dict(bre_2211[9], tide={"level": 0.97, "state": "høy", "rising": True}), B36)
assert r36_ucm["stars"] == 2 and r36_ucm["local_rules"]["lines"] == [mangler36[1]] and mangler36[1] in r36_ucm["breakdown"], r36_ucm["stars"]
assert "Tidevann: spoten tåler alt" not in r36_ucm["breakdown"]
r36_utide = rate(dict(bre_2211[9], tide=None), B36)      # Kartverket svarte ikke: samme tekst, ingen straff
assert r36_utide["stars"] == 2 and mangler36[1] in r36_utide["breakdown"] and "Tidevann: spoten tåler alt" not in r36_utide["breakdown"]
# kl. 09Z (2,7 m, straff 0,45) var timen der regelen vippet: vinden tok 0,2, og sammen ble det ett poeng.
# S27 (23.11.2026): vinden (5,2 m/s) tar ingenting under 8 m/s, og regelen alene (0,45) tar ikke poenget. Timen er 2,
# og linja om vannstanden står i forklaringen i stedet for «tåler alt».
assert r36[9]["stars"] == 2 and r36[9]["faded_wind"] == 0 and r36[9]["faded_tide"] == 0 and r36[9]["local_rules"]["stars_lost"] == 0, r36[9]["local_rules"]
assert r36[9]["breakdown"][-1] == "Totalt: 2 av 5 stjerner", r36[9]["breakdown"][-1]
assert any("jo lavere vann, jo bedre" in l for l in r36[9]["breakdown"]) and "Tidevann: spoten tåler alt" not in r36[9]["breakdown"]
assert r36[9]["local_rules"]["source"] == "Observasjoner 17.11 og 22.11.2026"       # appen viser kilden uten navn
# på lavt vann (1,8 m) står linja uten straff
r36_lav = rate(dict(bre_2211[9], tide={"level": 0.5, "state": "middels", "rising": False, "cm": 180}), B36)
assert r36_lav["stars"] == 2 and "Tidevann (1,8 m over sjøkartnull): lavt nok, ingen straff" in r36_lav["breakdown"], r36_lav["stars"]
# 36.6: reserven bortenfor BarentsWatch-horisonten (svell ute × andelen 0,22 × retningsfaktoren til gap-grensa, S27;
# før: transfer 0,15 × retningstreff). swell_window og
# swell_window_tegnet er like (345-30), så et nordsvell varsles likt tre døgn fram og når BarentsWatch-timene kommer.
# Med Russelvs oppsett (swell_window 15-25, bare det tegnede vinduet 345-30) demper reserven brytehøyden utenfor
# swell_window, og samme svell ville stått som 0 poeng til det kom innenfor horisonten (prøvd 22.11.2026).
# Reserven har ikke gap-grensas krav om 7 s (fysikk-kontrolløren 22.11.2026, vilkår 4): under 7 s gjelder
# reserveregningen uten «usikker». Fra 7 s gjelder gap-grensa, og timen merkes usikker. Fra S27 (23.11.2026) er
# høyden den samme på begge sider av 7 s. 0 av 5454 timer i varselet 22.11 kl. 11Z var i dette hjørnet, og
# 2 mørke timer (26.11 kl. 01-02Z) i varselet 23.11 kl. 01Z.
res36 = lambda **kw: rate({**h36, "bw_height": None, "bw_dir": None, "bw_period": None, "swell_offshore": 3.0, "height_offshore": 3.1,
                           "dir_offshore": 350.0, "wind_speed": 1.0, "gust": 2.0, **kw}, B36)
r36_res, r36_kort = res36(period=7.6), res36(period=6.5)
assert r36_res["height_source"] == "svell_ute" and r36_res["gap_floor"] and r36_res["uncertain"] and r36_res["stars"] == 2, (r36_res["stars"], r36_res["gap_floor"])
assert abs(r36_res["height"] - 0.495) < 0.006 and 0.4 <= r36_res["surf_height"] <= 0.8, (r36_res["height"], r36_res["surf_height"])
# S27: reserven bruker samme andel og retningsfaktor som grensa (0,22 × 0,75 ved 350°), så tallet er det samme under 7 s
assert r36_kort["height_source"] == "svell_ute" and not r36_kort["gap_floor"] and abs(r36_kort["height"] - 0.495) < 0.006, (r36_kort["gap_floor"], r36_kort["height"])
# bw_tillit (23.11.2026, fysikk-kontrolløren, valg 3 i): under 7 s er reserven for en fjord-spot usikker (før: ikke usikker)
assert r36_kort["stars"] == 2 and r36_kort["uncertain"] and r36_kort["surf_height"] <= r36_res["surf_height"], (r36_kort["stars"], r36_kort["surf_height"])
# lenger ut enn to grader utenfor kanten gir reserven ingenting (0 poeng), også med langt svell. I kantsonen
# (343-344° og 31-32°) gir reserven det samme som BarentsWatch-sonen (S27, test 37.2).
assert res36(period=7.6, dir_offshore=342.0)["stars"] == 0 and res36(period=7.6, dir_offshore=335.0)["stars"] == 0
print("36: Breivikeidet 22.11 - gap-grensa med myk kant gir 2 poeng kl. 07-13Z (S27) og 0,7-0,8 m surfehøyde kl. 08-10Z, hard kant på kopien RH og samme myke kant på Russelv (S34 a); myk tidevannsregel på vannstanden, høyst 0,49 og aldri uten cm - OK")

# 37: S27 (Theodor 23.11.2026, fysikk-kontrolløren 23.11.2026; kilder: observasjonene 17.11 og 22.11.2026). Breivikeidet:
# andelen er låst til observasjonene (0,22 langs fjordaksen, 0,165 ved 350°), reserven bruker samme andel og
# retningsfaktor som gap-grensa, og vinden tar ingen poeng under 8 m/s middelvind. Gjelder bare Breivikeidet.
from rating import _wind_raw, _wind_eff, wind_curve_penalty, blown_out_wind_ms, local_wind, effective_wind, wind_penalty_parts
B37 = spots["breivikeidet"]
# 37.1: låst andel har de tre fjord-spotene (Breivikeidet, og fra 23.11.2026 Russelv og Lenangsøyra, svar.md kl. 14.05),
# myk kant har alle tre (Russelv fra 24.11.2026, S34 a). Egen vindkurve har bare Breivikeidet og Unstad (S29 a, test 38).
for felt37, ids37 in (("transfer_locked", ["breivikeidet", "lenangsoyra", "russelv"]), ("gap_edge_taper", ["breivikeidet", "lenangsoyra", "russelv"]), ("gap_soft_edge", ["breivikeidet", "lenangsoyra", "russelv"])):
    assert sorted(i for i, sp in spots.items() if sp.get(felt37)) == ids37, felt37
assert sorted(i for i, sp in spots.items() if sp.get("wind_local")) == ["breivikeidet", "unstad"]
assert B37["transfer"] == B37["gap_transfer"] == 0.22 and B37["wind_local"]["source"] == "Observasjon 17.11.2026"
# formen på feltene (feiljegeren 23.11.2026: en skrivefeil her ville gitt KeyError eller deling på null i rate())
assert len(B37["gap_edge_taper"]) == 2 and all(isinstance(g, (int, float)) and g > 0 for g in B37["gap_edge_taper"])
assert B37["wind_local"]["calm_below_ms"] > 0 and set(B37["wind_local"]["curves"]) == {"offshore", "side", "sideonshore", "onshore"}
assert all(len(pkt) == 2 for kurve in B37["wind_local"]["curves"].values() for pkt in kurve)
# 37.2: reserven er lik gap-grensa for hver grad fra to grader utenfor kanten til to grader utenfor (343-32°), når
# perioden er minst 7 s og vinden er svak. Da hopper verken høyden, surfehøyden eller poengene når
# BarentsWatch-timene tar slutt (feiljegeren 23.11.2026: i kantsonen 343-344° og 31-32° ga reserven 0 poeng der
# BarentsWatch-sonen ga 2, fordi surfehøyden ble dempet en gang til).
for d37 in range(343, 393):
    h37 = {"height_offshore": 2.6, "swell_offshore": 2.5, "swell_model": "standard", "bw_height": None, "bw_dir": None, "bw_period": None,
           "dir_offshore": float(d37 % 360), "period": 7.5, "wind_speed": 1.0, "wind_dir": 203.0, "gust": 2.0}
    r37 = rate(dict(h37), B37)
    assert r37["height_source"] == "svell_ute" and abs(r37["height"] - gap_floor_height(h37, B37)) < 0.006, (d37, r37["height"], gap_floor_height(h37, B37))
    # og under 7 s er høyden den samme (bare «usikker» og gap-merket faller bort)
    assert abs(rate(dict(h37, period=6.5), B37)["height"] - r37["height"]) < 1e-9, d37
    # samme svell med et lavt BarentsWatch-tall ved punktet (0,20 m, som 17.11 og 22.11): samme surfehøyde og poeng
    for sv37 in (2.5, 3.2):
        res37 = rate(dict(h37, swell_offshore=sv37, height_offshore=sv37 + 0.1), B37)
        bw37 = rate(dict(h37, swell_offshore=sv37, height_offshore=sv37 + 0.1, bw_height=0.20, bw_dir=float(d37 % 360), bw_period=3.0), B37)
        assert bw37["height_source"] == "barentswatch" and bw37["gap_floor"], (d37, sv37)
        assert res37["stars"] == bw37["stars"] and res37["surf_height"] == bw37["surf_height"], (d37, sv37, res37["stars"], bw37["stars"], res37["surf_height"], bw37["surf_height"])
assert rate(dict(h37, swell_offshore=3.2, height_offshore=3.3, dir_offshore=343.0), B37)["stars"] == 2      # kantsonen gir poeng også i reserven
assert rate(dict(h37, dir_offshore=340.0), B37)["stars"] == 0 and rate(dict(h37, dir_offshore=35.0), B37)["stars"] == 0
# 37.3: vindkurven. Under 8 m/s middelvind: ingen straff for noen vindtype, uansett kast. Fra 8 m/s: de vanlige
# kurvene lest på middelvinden, og aldri strengere enn de vanlige kurvene med kast.
assert blown_out_wind_ms(B37) == 8.0 == BLOWN_OUT_WIND_MS and local_wind(spots["grotfjord"]) is None and blown_out_wind_ms(spots["grotfjord"]) == 8.0
for kind37 in ("offshore", "side", "sideonshore", "onshore"):
    for v10 in range(0, 80):
        for g37 in (None, v10 / 10 + 5, 25.0):
            assert _wind_eff(v10 / 10, g37, B37) == v10 / 10 and _wind_raw(v10 / 10, kind37, B37) == 0.0, (kind37, v10, g37)
    for v10 in range(80, 260):
        assert abs(_wind_raw(v10 / 10, kind37, B37) - wind_curve_penalty(v10 / 10, kind37)) < 1e-9, (kind37, v10)
        assert _wind_raw(v10 / 10, kind37, B37) <= wind_curve_penalty(effective_wind(v10 / 10, v10 / 10 * 1.6), kind37) + 1e-9, (kind37, v10)
assert _wind_raw(8.0, "onshore", B37) == 2.0 and _wind_raw(7.99, "onshore", B37) == 0.0
# gjennom wind_penalty_parts(): 7,9 m/s rett inn (20°) med kast 20 tar ingenting på Breivikeidet, men 2 poeng eller mer ellers
assert wind_penalty_parts(7.9, 20.0, B37, 20.0)["pen"] == 0
assert wind_penalty_parts(7.9, 20.0, {k: v for k, v in B37.items() if k != "wind_local"}, 20.0)["pen"] >= 2
assert wind_penalty_parts(None, 20.0, B37)["pen"] == wind_penalty_parts(None, 20.0, {k: v for k, v in B37.items() if k != "wind_local"})["pen"]   # ukjent styrke som før
# 37.4: torsdag 26.11 (varselet 23.11 kl. 01Z) er en forventning, ikke en observasjon: 1,84 m svell fra 23°, 7,35 s,
# 1,5 m/s fralands og 0,6 m vann gir 2 poeng som usikkert anslag gjennom gapet. Med andelen 0,19 ville høyden vært
# 0,35 m og timen flat. Under ca. 1,59 m svell (0,35 m / 0,22) er timen flat også nå.
tors37 = {"height_offshore": 2.4, "swell_offshore": 1.84, "swell_model": "standard", "bw_height": None, "bw_dir": None, "bw_period": None,
          "dir_offshore": 23, "period": 7.35, "wind_speed": 1.5, "wind_dir": 203.0, "gust": None,
          "tide": {"level": 0.05, "state": "lav", "rising": True, "cm": 63}}
r37_tors = rate(dict(tors37), B37)
show("37: Breivikeidet torsdag 26.11 kl. 06Z (forventning)", r37_tors)
assert r37_tors["stars"] == 2 and r37_tors["uncertain"] and r37_tors["gap_floor"] and r37_tors["height_source"] == "svell_ute", (r37_tors["stars"], r37_tors["gap_floor"])
assert abs(r37_tors["height"] - 1.84 * 0.22) < 0.006 and 0.5 <= r37_tors["surf_height"] <= 0.8, (r37_tors["height"], r37_tors["surf_height"])
assert rate(dict(tors37, swell_offshore=1.76), B37)["stars"] == 2          # det laveste svellet torsdag (1,76-1,84 m)
r37_lav = rate(dict(tors37, swell_offshore=1.55), B37)
assert r37_lav["stars"] == 0 and r37_lav["likely_flat"] and r37_lav["low_reason"] == "flat", (r37_lav["stars"], r37_lav["low_reason"])
r37_019 = rate(dict(tors37), dict(B37, transfer=0.19, gap_transfer=0.19))
assert r37_019["stars"] == 0 and r37_019["likely_flat"], (r37_019["stars"], r37_019["height"])
# 37.5: 22.11 kl. 09-10Z med vindkurven og tidevannsregelen sammen: 2 poeng, og regelen tar ikke et helt poeng
for t in (9, 10):
    assert r36[t]["stars"] == 2 and r36[t]["faded_wind"] == 0 and r36[t]["local_rules"]["stars_lost"] == 0, (t, r36[t]["stars"], r36[t]["local_rules"])
# 37.6 (feiljegeren 23.11.2026): lav svellandel ute (GFS sin deling i svell og vindsjø) gir «blåst ut» som før, også under 8 m/s -
# vindkurven tar bare bort den vinddrevne delen. Ordet er det samme med og uten kurven.
for v37 in (3.0, 7.9, 8.0):
    for sv37 in (0.6, 0.8, 1.2):
        lav37 = {"height_offshore": 1.8, "swell_offshore": sv37, "swell_model": "standard", "dir_offshore": 320.0, "period": 6.0,
                 "bw_height": 0.6, "bw_dir": 320.0, "bw_period": 3.0, "wind_speed": v37, "wind_dir": 20.0, "gust": v37 + 3}
        med37, uten37 = rate(dict(lav37), B37), rate(dict(lav37), {k: v for k, v in B37.items() if k != "wind_local"})
        assert med37["low_reason"] == uten37["low_reason"] and med37["stars"] == uten37["stars"] == 0, (v37, sv37, med37["low_reason"], uten37["low_reason"])
assert rate(dict(lav37, wind_speed=3.0, swell_offshore=0.6), B37)["low_reason"] == "blown_out"
# 37.7 (fysikk-kontrolløren og feiljegeren 23.11.2026): «og sterk vind» i regnestykket følger spotens egen grense, 8 m/s
# MIDDELVIND uansett kast (12 fralands). Før sa linja «og sterk vind» ved 6 m/s med kast 14, mens vindlinja under sa
# «ingen effekt». Timen har grensa med seg (wind_calm_ms), så dagens time i henteren og ordet i appen bruker den samme.
def linje37(v, g, vdir=20.0):
    r = rate(dict(lav37, swell_offshore=0.6, wind_speed=v, gust=g, wind_dir=vdir), B37)
    assert r["low_reason"] == "blown_out" and r["stars"] == 0 and r["wind_calm_ms"] == 8.0, (v, g, r["low_reason"])
    linjer = [x for x in r["breakdown"] if "blåst ut" in x]
    assert len(linjer) == 1, r["breakdown"]
    return "og sterk vind" in linjer[0]
assert _wind_type_s24b(20.0, B37) == "onshore" and _wind_type_s24b(200.0, B37) == "offshore"
assert not linje37(6.5, 11.5) and not linje37(6.0, 14.0) and not linje37(7.9, 12.0)   # kastene teller ikke her
assert linje37(8.0, 8.0) and linje37(9.0, None)
assert not linje37(11.9, 20.0, 200.0) and linje37(12.0, 12.0, 200.0)                   # fralands: 12 m/s middelvind
assert "wind_calm_ms" not in rate(dict(lav37, swell_offshore=0.6, wind_speed=3.0), {k: v for k, v in B37.items() if k != "wind_local"})
print("37: Breivikeidet S27 - låst andel bare på fjord-spotene, reserven lik gap-grensa 343-32°, ingen vindstraff under 8 m/s, torsdag 26.11 gir 2 poeng som anslag - OK")

# 38: S29 a (Theodor 22.11.2026 og ja i svar.md 23.11.2026; forslag fra fysikk-kontrolløren 22.11.2026). Unstad har egen
# vindkurve: under 14 m/s middelvind tar vinden ingen poeng, uansett retning og kast. Fra 14 m/s en mildere kurve
# enn den vanlige, lest på middelvinden. Gjelder bare Unstad (og Breivikeidet med sin egen kurve, test 37).
U38 = spots["unstad"]
U38_uten = {k: v for k, v in U38.items() if k != "wind_local"}
KINDS38 = ("onshore", "sideonshore", "side", "offshore")
# 38.1: formen på feltet og kilden
assert U38["wind_local"]["calm_below_ms"] == 14.0 == blown_out_wind_ms(U38) and U38["wind_local"]["source"] == "Theodor 22.11.2026"
assert set(U38["wind_local"]["curves"]) == set(KINDS38) and all(len(pkt) == 2 for kurve in U38["wind_local"]["curves"].values() for pkt in kurve)
assert blown_out_wind_ms(U38_uten) == 8.0
# 38.2: under 14 m/s middelvind ingen straff for noen vindtype, uansett kast. Fra 14 m/s aldri strengere enn de
# vanlige kurvene (verken lest på middelvinden eller med kast), og aldri fallende med økende vind.
for kind38 in KINDS38:
    for v10 in range(0, 140):
        for g38 in (None, v10 / 10 + 8, 30.0):
            assert _wind_eff(v10 / 10, g38, U38) == v10 / 10 and _wind_raw(v10 / 10, kind38, U38) == 0.0, (kind38, v10, g38)
    forrige38 = 0.0
    for v10 in range(140, 320):
        raw38 = _wind_raw(v10 / 10, kind38, U38)
        assert raw38 <= wind_curve_penalty(v10 / 10, kind38) + 1e-9, (kind38, v10, raw38)
        assert raw38 <= wind_curve_penalty(effective_wind(v10 / 10, v10 / 10 * 1.5), kind38) + 1e-9, (kind38, v10, raw38)
        assert raw38 >= forrige38 - 1e-9, (kind38, v10, raw38, forrige38)
        forrige38 = raw38
# tallene i kurven: 14, 16, 18, 22 og 26 m/s (pålands, skrått pålands, side, fralands)
for v38, venter38 in ((14.0, (0.0, 0.0, 0.0, 0.0)), (16.0, (1.0, 0.75, 0.5, 0.5)), (18.0, (2.0, 1.5, 1.0, 1.0)),
                      (22.0, (3.0, 2.5, 2.0, 2.0)), (26.0, (4.0, 3.0, 3.0, 2.0))):
    assert tuple(round(_wind_raw(v38, k, U38), 6) for k in KINDS38) == venter38, (v38, [_wind_raw(v38, k, U38) for k in KINDS38])
# gjennom wind_penalty_parts(): 13,9 m/s rett inn (295°) med kast 22 tar ingenting på Unstad, men 4 poeng uten kurven
assert wind_penalty_parts(13.9, 295.0, U38, 22.0)["pen"] == 0 and wind_penalty_parts(13.9, 295.0, U38_uten, 22.0)["pen"] == 4
assert wind_penalty_parts(None, 295.0, U38)["pen"] == wind_penalty_parts(None, 295.0, U38_uten)["pen"] == 1    # ukjent styrke som før
# 38.3: «blåst ut». Lav svellandel ute (GFS sin deling i svell og vindsjø) gir «blåst ut» som før, også under 14 m/s (samme ord med og
# uten kurven). Vinden alene gir ikke «blåst ut» under 14 m/s pålands, men gjør det fra 14 m/s.
def lav38(sv, v):
    return {"height_offshore": 1.8, "swell_offshore": sv, "swell_model": "standard", "dir_offshore": 200.0, "period": 6.0,
            "bw_height": 0.6, "bw_dir": 200.0, "bw_period": 3.0, "wind_speed": v, "wind_dir": 295.0, "gust": v + 3}
for v38 in (7.0, 10.0, 13.9, 14.0):
    med38, uten38 = rate(lav38(0.5, v38), U38), rate(lav38(0.5, v38), U38_uten)
    assert med38["low_reason"] == uten38["low_reason"] == "blown_out" and med38["stars"] == uten38["stars"] == 0, (v38, med38["low_reason"])
assert rate(lav38(1.6, 7.0), U38)["low_reason"] == rate(lav38(1.6, 7.0), U38_uten)["low_reason"] == "treffer_ikke"
for v38 in (10.0, 13.9):
    assert rate(lav38(1.6, v38), U38)["low_reason"] == "treffer_ikke" and rate(lav38(1.6, v38), U38_uten)["low_reason"] == "blown_out", v38
assert rate(lav38(1.6, 14.0), U38)["low_reason"] == rate(lav38(1.6, 14.0), U38_uten)["low_reason"] == "blown_out"
# «og sterk vind» i regnestykket følger Unstads egen grense (fysikk-kontrolløren og feiljegeren 23.11.2026): 14 m/s
# middelvind, uansett kast. Under den sier linja bare «mye vindsjø», og timen har grensa med seg (wind_calm_ms).
def linje38(v, g, vdir=295.0, sv=0.5):
    r = rate(dict(lav38(sv, v), gust=g, wind_dir=vdir), U38)
    assert r["low_reason"] == "blown_out" and r["stars"] == 0 and r["wind_calm_ms"] == 14.0, (v, g, r["low_reason"])
    linjer = [x for x in r["breakdown"] if "blåst ut" in x]
    assert len(linjer) == 1, r["breakdown"]
    return "og sterk vind" in linjer[0]
assert not linje38(7.0, 10.0) and not linje38(10.0, 13.0) and not linje38(13.9, 22.0) and linje38(14.0, 14.0)
# Unstad 22.11.2026 kl. 11Z (kontrollørens tilfelle): 8,2 m/s skrått pålands, kast 14, svellandel 0,13
skra38 = next(float(d) for d in range(0, 360, 5) if _wind_type_s24b(float(d), U38) == "sideonshore")
assert not linje38(8.2, 14.0, skra38, sv=0.24)
assert "wind_calm_ms" not in rate(lav38(0.5, 7.0), U38_uten)
# 38.4: kurven gjør aldri en time dårligere. Samme time med og uten kurven, for alle vindtyper og styrker 0-30 m/s.
for vdir38 in (295.0, 355.0, 20.0, 120.0):
    for v38 in range(0, 31, 2):
        t38 = {"height_offshore": 2.2, "swell_offshore": 2.0, "swell_model": "standard", "dir_offshore": 300.0, "period": 11.0,
               "bw_height": 1.6, "bw_dir": 300.0, "bw_period": 10.0, "wind_speed": float(v38), "wind_dir": vdir38, "gust": v38 * 1.4}
        assert rate(dict(t38), U38)["stars"] >= rate(dict(t38), U38_uten)["stars"], (vdir38, v38)
# de faste observasjonene for Unstad 26.-28.09 er testet over med spots.json slik den står nå, altså med kurven
# (05.10 finnes bare som vindretninger i test 21.2). Det femte poenget krever fortsatt ren vind (five_star_losses(),
# fralands eller under 3 m/s) også på Unstad og Breivikeidet: kurven endrer ikke den sperra (feiljegeren 23.11.2026).
print("38: Unstad S29 a - egen vindkurve: ingen vindstraff under 14 m/s middelvind, mildere kurve fra 14 m/s, lav svellandel gir «blåst ut» som før, aldri dårligere enn uten kurven - OK")
# 39: tillit til BarentsWatch per spot, bw_tillit (svar.md 23.11.2026 kl. 11.25, Theodor; fysikk-kontrolløren 23.11.2026;
# kilder: observasjon 17.11.2026 og 22.11.2026, Theodor). "kyst" (alle spots uten feltet) er uendret. For "fjord" er
# høyden svell ute × andelen i begge soner når svellet kommer fra det tegnede vinduet og perioden ute er minst 7 s, og
# BarentsWatch er bare et tegn på krapp sjø ved punktet (minst 0,6 m med toppperiode under 4 s gjør timen usikker, S32 e).
from rating import (is_fjord, fjord_in_window, fjord_share_height, fjord_chop, FJORD_CHOP_MIN_HEIGHT_M,
                    FJORD_CHOP_MAX_PERIOD_S, gap_blocked_by_wind, wind_type as _wt39)
FJORD39 = ["breivikeidet", "lenangsoyra", "russelv"]   # godkjente fjord-spots (PR A: Breivikeidet. 23.11.2026, svar.md kl. 14.05: Russelv og Lenangsøyra)
# 39.1: formen. bw_tillit mangler eller er "kyst"/"fjord". En fjord-spot har feltene en gap-spot har, og en låst andel
# lik gap_transfer. En lås uten transfer er ikke lov (feiljegeren S27). Myk kant krever fjord.
for i39, sp39 in spots.items():
    assert sp39.get("bw_tillit", "kyst") in ("kyst", "fjord"), i39
    assert not sp39.get("transfer_locked") or sp39.get("transfer") is not None, i39
    assert isinstance(sp39.get("andel_forelopig", False), bool), i39
    if sp39.get("gap_soft_edge"):
        assert is_fjord(sp39), i39
    if is_fjord(sp39):
        assert sp39.get("gap_spot") and sp39.get("swell_window_tegnet") and sp39.get("transfer_locked"), i39
        assert 0.05 <= sp39["gap_transfer"] <= 0.4 and sp39["transfer"] == sp39["gap_transfer"], i39
assert sorted(i for i, sp in spots.items() if is_fjord(sp)) == FJORD39
# andelen er merket «foreløpig» på Lenangsøyra (svar.md 23.11.2026 kl. 14.05) og Russelv (svar.md 23.11.2026 kl. 21.00, S34 a):
# satt lik Breivikeidets, uten en observasjon derfra som bestemmer tallet
assert sorted(i for i, sp in spots.items() if sp.get("andel_forelopig")) == ["lenangsoyra", "russelv"]
assert FJORD_CHOP_MIN_HEIGHT_M == 0.6 and FJORD_CHOP_MAX_PERIOD_S == 4.0
B39 = spots["breivikeidet"]
# 39.2: kyst er uendret. Med "kyst" satt eller feltet borte gir rate() det samme i alle felt, også regnestykket.
timer39 = [rus_1611, rus_1711, rus_1711_vs, stor, bre_2211[8], bre_1711[8], tors37,
           dict(rus_1611, wind_speed=9.0, wind_dir=350.0), dict(rus_1611, period=6.5), dict(rus_1611, bw_height=0.8, bw_period=3.0)]
for i39, sp39 in spots.items():
    if is_fjord(sp39):
        continue
    for h39 in timer39:
        assert rate(dict(h39), sp39) == rate(dict(h39), dict(sp39, bw_tillit="kyst")), i39
        assert not fjord_in_window(h39, sp39) and fjord_share_height(h39, sp39) is None and not fjord_chop(h39, sp39), i39
# 23.11.2026: Russelv og Lenangsøyra er fjord nå. Kystkopiene (se test 7) regnes som alle andre kyst-spots, med og uten feltet.
for sp39 in (RK, LK):
    for h39 in timer39:
        assert rate(dict(h39), sp39) == rate(dict(h39), {k: v for k, v in sp39.items() if k != "bw_tillit"}), sp39["id"]
        assert not fjord_in_window(h39, sp39) and fjord_share_height(h39, sp39) is None and not fjord_chop(h39, sp39), sp39["id"]
# 39.3: like soner for fjord. Svell fra 343-32°, 7 s eller mer: samme poeng, surfehøyde og ord med og uten BarentsWatch
# når punktet er stille (0,3 m, 2,5 s). Med vindsperre (fra 8 m/s pålands, skrått pålands eller ukjent retning): 0 poeng,
# høyden er andelshøyden, og ordet er «blåst ut» (eller «flatt» når andelshøyden er under flat-sperra) i begge soner.
assert (_wt39(20.0, B39), _wt39(80.0, B39), _wt39(120.0, B39), _wt39(200.0, B39)) == ("onshore", "sideonshore", "side", "offshore")
n39 = 0
for d39 in range(343, 393, 3):
    for sv39 in (1.5, 2.0, 2.5, 3.0, 3.5):
        for p39 in (7.0, 7.6, 9.0, 12.0):
            for ws39, wd39 in ((0.5, 200.0), (4.0, 20.0), (7.9, 20.0), (8.0, 20.0), (8.0, 80.0), (9.0, 80.0), (12.0, 120.0),
                               (12.0, 200.0), (9.0, None), (None, 20.0)):
                for g39 in (None, 14.0):
                    res39 = {"height_offshore": sv39 + 0.2, "swell_offshore": sv39, "swell_model": "standard", "dir_offshore": float(d39 % 360),
                             "period": p39, "wind_speed": ws39, "wind_dir": wd39, "gust": g39}
                    bw39 = dict(res39, bw_height=0.3, bw_dir=float(d39 % 360), bw_period=2.5)
                    a39, b39 = rate(dict(res39), B39), rate(dict(bw39), B39)
                    assert a39["height_source"] == "svell_ute" and b39["height_source"] == "barentswatch"
                    # flatt i kantsonen heter «treffer ikke» i reserven og «flatt» i BarentsWatch-sonen, som i main (classify_low_rating())
                    ord39 = [{"treffer_ikke": "flat"}.get(r["low_reason"], r["low_reason"]) for r in (a39, b39)]
                    assert (a39["stars"], a39["surf_height"], ord39[0], a39["uncertain"]) == (b39["stars"], b39["surf_height"], ord39[1], b39["uncertain"]), (d39, sv39, p39, ws39, wd39, g39, a39["stars"], b39["stars"], a39["low_reason"], b39["low_reason"])
                    assert abs(a39["height"] - fjord_share_height(res39, B39)) < 0.006 and abs(b39["height"] - a39["height"]) < 1e-9
                    if gap_blocked_by_wind(res39, B39):
                        assert a39["stars"] == 0 and ord39[0] == ord39[1] == ("blown_out" if fjord_share_height(res39, B39) >= 0.35 else "flat"), (d39, sv39, ws39, wd39)
                    n39 += 1
# skrått pålands 8 og 9 m/s gir 0 i begge soner (feiljegeren S27, funn 2: reserven ga 1)
for ws39 in (8.0, 9.0):
    h39 = {"height_offshore": 3.4, "swell_offshore": 3.2, "swell_model": "standard", "dir_offshore": 17.0, "period": 7.6, "wind_speed": ws39, "wind_dir": 80.0, "gust": ws39 + 3}
    assert rate(dict(h39), B39)["stars"] == 0 and rate(dict(h39, bw_height=0.3, bw_dir=17.0, bw_period=2.5), B39)["stars"] == 0, ws39
    assert rate(dict(h39), B39)["height"] == round(3.2 * 0.22, 2) and rate(dict(h39), B39)["low_reason"] == "blown_out"
# BarentsWatch løfter ikke over andelen: 1,2 m med 8,5 s ved punktet gir samme høyde som et stille punkt
assert rate(dict(bre_2211[8], bw_height=1.2, bw_period=8.5, bw_dir=20.0), B39)["height"] == r36[8]["height"]
# 39.4: krapp sjø ved punktet. 0,6 m og under 4 s gjør timen usikker (høyst 3), ikke «kildene uenige» og ikke et tak
# på 1 poeng (S32 e, svar.md 23.11.2026 kl. 14.00). 0,59 m, 4,0 s og manglende tall gir ingenting. Regelen hever
# aldri, og lang periode senker aldri.
k39 = lambda **kw: rate(dict(bre_2211[8], **kw), B39)
assert fjord_chop(dict(bre_2211[8], bw_height=0.6, bw_period=3.99), B39) and not fjord_chop(dict(bre_2211[8], bw_height=0.59, bw_period=3.99), B39)
assert not fjord_chop(dict(bre_2211[8], bw_height=0.6, bw_period=4.0), B39) and not fjord_chop(dict(bre_2211[8], bw_height=0.6, bw_period=None), B39)
r39k = k39(bw_height=0.6, bw_period=3.99)
assert r39k["stars"] == r36[8]["stars"] == 2 and r39k["uncertain"] and not r39k["sources_disagree"], (r39k["stars"], r39k["sources_disagree"])
assert r39k["sources_disagree_reason"] is None and r39k["height"] == r36[8]["height"]
# under 7 s gjelder BarentsWatch som for en kyst-spot, og der er krapp sjø det eneste som gjør timen usikker:
# samme poeng og høyde med og uten tegnet, også når punktet viser 1,5 m med 3 s (2 poeng, ikke kappet til 1)
u39 = {"height_offshore": 2.6, "swell_offshore": 2.5, "swell_model": "standard", "dir_offshore": 17.0, "period": 6.5,
       "wind_speed": 1.0, "wind_dir": 203.0, "gust": 2.0, "bw_dir": 347.0}
for bwh39, bwp39, bwp39b, st39 in ((0.6, 3.99, 4.0, 0), (1.5, 3.0, 6.0, 2)):
    ra39, rb39 = rate(dict(u39, bw_height=bwh39, bw_period=bwp39), B39), rate(dict(u39, bw_height=bwh39, bw_period=bwp39b), B39)
    assert ra39["uncertain"] and not rb39["uncertain"] and not ra39["sources_disagree"], (bwh39, ra39["uncertain"], rb39["uncertain"])
    assert ra39["stars"] == rb39["stars"] == st39 and ra39["height"] == rb39["height"], (bwh39, ra39["stars"], rb39["stars"])
# feiljegeren 23.11.2026 (etterkontrollen): en time med 3 poeng får 3 også med tegnet, så et tak på 2 ikke slipper gjennom
t39 = {"height_offshore": 2.1, "swell_offshore": 2.0, "swell_model": "standard", "dir_offshore": 17.0, "period": 9.0,
       "wind_speed": 1.0, "wind_dir": 203.0, "gust": 2.0, "bw_dir": 347.0}
ra39, rb39 = rate(dict(t39, bw_height=0.7, bw_period=3.0), B39), rate(dict(t39, bw_height=0.7, bw_period=4.0), B39)
assert fjord_chop(dict(t39, bw_height=0.7, bw_period=3.0), B39) and ra39["stars"] == rb39["stars"] == 3, (ra39["stars"], rb39["stars"])
assert ra39["uncertain"] and rb39["uncertain"] and ra39["height"] == rb39["height"] and not ra39["sources_disagree"]
for kw39 in ({"bw_height": 0.59, "bw_period": 3.99}, {"bw_height": 0.6, "bw_period": 4.0}, {"bw_height": 0.6, "bw_period": None}):
    assert k39(**kw39)["stars"] == 2 and not k39(**kw39)["sources_disagree"], kw39
for bwh39 in (0.0, 0.3, 0.59, 0.6, 0.9, 1.5, 2.5):
    for bwp39 in (1.0, 2.5, 3.99, 4.0, 6.0, 9.0, 14.0, None):
        assert k39(bw_height=bwh39, bw_period=bwp39)["stars"] <= r36[8]["stars"], (bwh39, bwp39)
        if bwp39 is not None and bwp39 >= 7.0:
            assert k39(bw_height=bwh39, bw_period=bwp39)["stars"] == r36[8]["stars"], (bwh39, bwp39)
# de faste observasjonene har ikke krapp sjø ved punktet (0,33-0,49 m med 1,6-2,7 s)
assert not any(fjord_chop(h, B39) for h in list(bre_1711.values()) + list(bre_2211.values()))
# reserven har ikke BarentsWatch, så regelen kan bare slå til innenfor horisonten
assert not fjord_chop(dict(tors37, bw_height=None), B39)
# 39.5: reserven for en fjord-spot er usikker under 7 s (samme høyde som fra 7 s) og når svellretningen ute mangler.
# For en kyst-spot er det som før (kystkopien av Russelv uten svellretning er ikke usikker i reserven). Russelv og
# Lenangsøyra er fjord fra 23.11.2026 og følger samme regel som Breivikeidet.
res39 = {"height_offshore": 2.6, "swell_offshore": 2.5, "swell_model": "standard", "dir_offshore": 17.0, "period": 6.5,
         "wind_speed": 1.0, "wind_dir": 203.0, "gust": 2.0}
assert rate(dict(res39), B39)["uncertain"] and abs(rate(dict(res39), B39)["height"] - rate(dict(res39, period=7.5), B39)["height"]) < 1e-9
assert rate(dict(res39, dir_offshore=None), B39)["uncertain"]
assert not rate(dict(res39, dir_offshore=None), RK)["uncertain"]
for sp39 in (R, L):
    assert rate(dict(res39), sp39)["uncertain"] and rate(dict(res39, dir_offshore=None), sp39)["uncertain"], sp39["id"]
    assert abs(rate(dict(res39), sp39)["height"] - rate(dict(res39, period=7.5), sp39)["height"]) < 1e-9, sp39["id"]
# 39.6: lært eller bygd eksponering rører ikke andelen (feiljegeren S27, punkt 4). Med rå eksponering 0 og glattet 0,4
# overalt er reserven fortsatt lik andelshøyden og lik BarentsWatch-sonen.
B39e = dict(B39, exposure_raw=[0.0] * 360, exposure_smoothed=[0.4] * 360)
for d39 in (343, 350, 0, 17, 30, 32):
    h39 = dict(res39, dir_offshore=float(d39), period=7.6, swell_offshore=3.0, height_offshore=3.2)
    a39, b39 = rate(dict(h39), B39e), rate(dict(h39, bw_height=0.3, bw_dir=float(d39), bw_period=2.5), B39e)
    assert abs(a39["height"] - fjord_share_height(h39, B39)) < 0.006 and a39["stars"] == b39["stars"] and a39["surf_height"] == b39["surf_height"], d39
# 39.7 (feiljegeren 23.11.2026): 39.2 sammenlikner bare denne koden med seg selv, så her er en kyst-spot låst til
# tallene fra main 41e25be. Det var Russelv, som da var gap-spot med tegnet vindu, men kyst. Fra 23.11.2026 er Russelv
# fjord, så tallene står på kystkopien RK (Russelv slik den var): i reserven med rå eksponering 0 gjelder den ekstra
# dempingen fortsatt (bare fjord-spots slipper den), og svell fra vinduet gir 0 poeng. Uten sperra: 1-2 poeng.
R39e = dict(RK, exposure_raw=[0.0] * 360, exposure_smoothed=[0.4] * 360)
for d39 in (346.0, 350.0, 5.0, 17.0, 19.0):
    for p39, sh39 in ((7.9, 0.36), (10.0, 0.48)):
        r39 = rate({"height_offshore": 2.6, "swell_offshore": 2.4, "swell_model": "standard", "dir_offshore": d39, "period": p39,
                    "wind_speed": 2.0, "wind_dir": 106.0, "gust": 4.0}, R39e)
        assert (r39["stars"], r39["height"], r39["surf_height"]) == (0, 0.58, sh39), (d39, p39, r39["stars"], r39["height"], r39["surf_height"])
        # en fjord-spot slipper den ekstra dempingen som Breivikeidet i 39.6. RH (hard kant): høyden er andelshøyden 2,4 × 0,20
        hf39 = {"height_offshore": 2.6, "swell_offshore": 2.4, "swell_model": "standard", "dir_offshore": d39, "period": p39,
                "wind_speed": 2.0, "wind_dir": 106.0, "gust": 4.0}
        f39 = rate(dict(hf39), dict(RH, exposure_raw=[0.0] * 360, exposure_smoothed=[0.4] * 360))
        assert f39["height"] == 0.48 and f39["surf_height"] > sh39 and f39["stars"] >= 1 and f39["low_reason"] != "treffer_ikke", (d39, p39, f39["stars"], f39["height"], f39["surf_height"], f39["low_reason"])
        # den ekte Russelv (24.11.2026, S34 a): andelshøyden 2,4 × 0,22 × den myke kanten, aldri «treffer ikke»
        e39 = rate(dict(hf39), dict(R, exposure_raw=[0.0] * 360, exposure_smoothed=[0.4] * 360))
        assert abs(e39["height"] - fjord_share_height(hf39, R)) < 0.006 and e39["low_reason"] != "treffer_ikke", (d39, p39, e39["height"], e39["low_reason"])
        # surfehøyden er bruddhøyden (Komar og Gaughan) av andelshøyden, uten ekstra demping
        assert e39["surf_height"] == round(breaking_height(fjord_share_height(hf39, R), p39), 2), (d39, p39, e39["surf_height"])
        if d39 in (5.0, 17.0, 19.0):      # langs fjordaksen er hele andelen med: 0,53 m, mer enn med 0,20
            assert e39["height"] == 0.53 and e39["surf_height"] > f39["surf_height"] and e39["stars"] >= f39["stars"] >= 1, (d39, p39, e39["stars"], e39["surf_height"])
        else:
            # S36 b (svar.md 24.11.2026 kl. 10.25), låst her: på vestkanten (346° og 350°) er andelen på Russelv aldri under
            # 0,20 (gap_min_share), så 2,4 m svell gir igjen 0,48 m og 1 poeng ved 7,9 s (2 poeng ved 10 s), som RH. Med
            # S34 a alene (bare den myke kanten) var det 0,36 og 0,40 m og 0 poeng ved 7,9 s.
            vest39 = {(346.0, 7.9): (1, 0.48, 0.78), (346.0, 10.0): (2, 0.48, 0.86), (350.0, 7.9): (1, 0.48, 0.78), (350.0, 10.0): (2, 0.48, 0.86)}
            assert (e39["stars"], e39["height"], e39["surf_height"]) == vest39[(d39, p39)], (d39, p39, e39["stars"], e39["height"], e39["surf_height"])
            assert e39["height"] == f39["height"] and e39["stars"] >= f39["stars"] and e39["low_reason"] not in ("flat", "treffer_ikke"), (d39, p39)
            # uten gap_min_share (S34 a alene) er tallene de lave: feltet er det som bærer vestkanten
            u39 = rate(dict(hf39), dict({k: v for k, v in R.items() if k != "gap_min_share"}, exposure_raw=[0.0] * 360, exposure_smoothed=[0.4] * 360))
            assert u39["height"] == {346.0: 0.36, 350.0: 0.40}[d39] and u39["stars"] == e39["stars"] - 1, (d39, p39, u39["height"], u39["stars"])
# utenfor vinduet er en fjord-spot lik en kyst-spot i alle felt, også med krapp sjø ved punktet (0,7 m, 3 s)
for d39 in (40.0, 60.0, 300.0):
    h39 = {"height_offshore": 2.6, "swell_offshore": 2.4, "swell_model": "standard", "dir_offshore": d39, "period": 9.0,
           "wind_speed": 2.0, "wind_dir": 203.0, "gust": 4.0, "bw_height": 0.7, "bw_dir": 20.0, "bw_period": 3.0}
    assert not fjord_in_window(h39, B39) and not fjord_chop(h39, B39), d39
    assert rate(dict(h39), B39) == rate(dict(h39), dict(B39, bw_tillit="kyst")) and rate(dict(h39), B39)["stars"] == 3, d39
# reserven er usikker også når perioden ute mangler
assert rate(dict(res39, period=None), B39)["uncertain"]
# ordene i regnestykket: «Løftet til» bare når andelen er over BarentsWatch-tallet etter justering. Er punktet høyere
# (1,2 m med 8,5 s), eller tar vinden gap-grensa bort, står høyden uten «Løftet til». «vinden teller først fra 8 m/s her» står bare
# i vindlinja når vindsperra slår til (ikke ved 7,9 m/s pålands eller 13 m/s fralands).
gap39 = lambda r: [x for x in r["breakdown"] if "gjennom gapet, andel" in x]
vind39 = lambda r: [x for x in r["breakdown"] if x.startswith("Vind ")]
l39 = {"height_offshore": 2.6, "swell_offshore": 2.5, "swell_model": "standard", "dir_offshore": 17.0, "period": 7.6,
       "wind_speed": 1.0, "wind_dir": 203.0, "gust": 2.0, "bw_height": 0.4, "bw_dir": 347.0, "bw_period": 1.6}
SLUTT39 = " m: svell ute 2,5 m gjennom gapet, andel 0,22. Anslag, ikke kystmodellens tall"
assert gap39(rate(dict(l39), B39)) == ["Løftet til 0,6" + SLUTT39]
assert gap39(rate(dict(l39, bw_height=None, bw_dir=None, bw_period=None), B39)) == ["Løftet til 0,6" + SLUTT39]
assert gap39(rate(dict(l39, bw_height=1.2, bw_dir=20.0, bw_period=8.5), B39)) == ["0,6" + SLUTT39]
for kw39 in ({}, {"bw_height": None, "bw_dir": None, "bw_period": None}):
    r39 = rate(dict(l39, wind_speed=9.0, wind_dir=20.0, gust=12.0, **kw39), B39)
    assert r39["stars"] == 0 and gap39(r39) == ["0,6" + SLUTT39], (kw39, gap39(r39))
    assert len(vind39(r39)) == 1 and ", vinden teller først fra 8 m/s her: " in vind39(r39)[0], vind39(r39)
for kw39 in ({"wind_speed": 7.9, "wind_dir": 20.0, "gust": 12.0}, {"wind_speed": 13.0, "wind_dir": 200.0, "gust": 18.0}, {}):
    r39 = rate(dict(l39, **kw39), B39)
    assert gap39(r39) == ["Løftet til 0,6" + SLUTT39] and not any(", vinden teller først fra 8 m/s her: " in x for x in r39["breakdown"]), (kw39, r39["breakdown"])
# 24.11.2026 (feiljegeren, funn 4): reserven under 7 s har samme andelshøyde (share_height uten gap_floor) og får samme
# linje uten «Løftet til». Med BarentsWatch-tall under 7 s er høyden ikke andelen, og linja står ikke.
r39_kort = rate(dict(l39, period=6.5, bw_height=None, bw_dir=None, bw_period=None), B39)
assert r39_kort.get("share_height") is True and not r39_kort["gap_floor"] and gap39(r39_kort) == ["0,6" + SLUTT39], gap39(r39_kort)
assert "share_height" not in rate(dict(l39, period=6.5), B39) and gap39(rate(dict(l39, period=6.5), B39)) == []
# «Retning: …» leses fra det tegnede vinduet når høyden er andelshøyden (feiljegeren, funn 2). Russelv med svell fra 25°:
# eksponeringen mot swell_window gir «svakt inn i skyggen», det tegnede vinduet (345-30) gir «treffer vinduet», som
# Breivikeidet. Utenfor vinduet og på kystkopien er ordet som før.
ret39 = lambda r: [x for x in r["breakdown"] if x.startswith("Retning: ")]
h39_25 = dict(l39, dir_offshore=25.0)
R39x = dict(R, exposure_raw=[0.0] * 360, exposure_smoothed=[0.3] * 360)
assert ret39(rate(dict(h39_25), R39x)) == ret39(rate(dict(h39_25), B39)) == ["Retning: treffer vinduet"]
assert ret39(rate(dict(h39_25), dict(R39x, bw_tillit="kyst"))) == ["Retning: svakt inn i skyggen"]
assert ret39(rate(dict(h39_25, dir_offshore=28.0), R39x)) == ret39(rate(dict(h39_25, dir_offshore=28.0), B39)) == ["Retning: i utkanten av vinduet"]
assert ret39(rate(dict(h39_25, dir_offshore=60.0), R39x)) == ret39(rate(dict(h39_25, dir_offshore=60.0), dict(R39x, bw_tillit="kyst")))
print(f"39: bw_tillit - kyst uendret, fjord bare {FJORD39}; like soner i {n39} timer, vindsperre gir 0 i begge, krapp sjø fra 0,6 m og under 4 s gjør timen usikker, reserven usikker under 7 s og uten retning, kystkopien av Russelv låst til main - OK")
# 40: «Lyngen henger sammen» (svar.md 23.11.2026 kl. 14.05, Theodor: «Hvis det er surf på Breivikeidet er det så å si
# alltid bølger på de to andre spottene i Lyngen»; kilder: observasjon 17.11.2026 og 22.11.2026, Theodor, og observasjon
# 16.11.2026, bilde, Russelv). Russelv og Lenangsøyra er fjord-spots med samme vindu, myke kant og andel som Breivikeidet
# (345-30, 0,22, merket foreløpig): Lenangsøyra fra 23.11.2026, Russelv fra 24.11.2026 (svar.md 23.11.2026 kl. 21.00,
# S34 a; før: 348-19, hard kant og 0,20).
# Timene under er de to faste Breivikeidet-dagene med de lagrede tallene for de to spotene: 17.11 fra
# data/backtest/inputs/2026-11-16T12.json (varselet fra 16.11 kl. 12Z), 22.11 fra det lagrede varselet fra 21.11 kl. 11Z
# (samme fil som test 36). Svellet ute er det samme som i test 34 og 36.
# (dag, time, total ute, svell ute, retning, periode, BarentsWatch høyde, retning, toppperiode, maks, vind, vindretning, kast, tidevann)
rad40 = {
    "russelv": [("17.11", 8, 2.6, 2.24, 17, 7.75, 0.58, 2.0, 3.2, 1.102, 7.2, 19.0, 13.0, (0.52, "middels", False)),
                ("17.11", 9, 2.5, 2.22, 17, 7.75, 0.61, 2.0, 3.2, 1.159, 5.3, 39.0, 10.8, (0.26, "lav", False)),
                ("22.11", 8, 3.8, 2.88, 350, 7.6, 1.2833, 345.0, 3.4, 2.4383, 7.6, 350.0, 14.5, (0.8, "høy", True)),
                ("22.11", 9, 3.7, 2.86, 351, 7.55, 1.26, 345.0, 3.4, 2.394, 3.7, 349.0, 12.9, (0.96, "høy", True)),
                ("22.11", 10, 3.6, 2.6, 355, 7.5, 1.2533, 345.0, 3.4, 2.3813, 7.6, 355.0, 12.0, (1.0, "høy", False))],
    "lenangsoyra": [("17.11", 8, 2.5, 2.24, 17, 7.75, 0.7467, 10.0, 3.8, 1.4187, 9.0, 25.0, 12.7, (0.52, "middels", False)),
                    ("17.11", 9, 2.4, 2.22, 17, 7.75, 0.78, 10.0, 3.8, 1.482, 6.8, 25.0, 12.7, (0.26, "lav", False)),
                    ("22.11", 8, 3.8, 2.88, 350, 7.6, 0.9067, 344.0, 3.1, 1.7227, 9.1, 5.0, 13.0, (0.8, "høy", True)),
                    ("22.11", 9, 3.8, 2.86, 351, 7.55, 0.89, 344.0, 3.1, 1.691, 7.8, 7.0, 12.4, (0.96, "høy", True)),
                    ("22.11", 10, 3.7, 2.6, 355, 7.5, 0.8867, 344.0, 3.1, 1.6847, 6.0, 6.0, 10.8, (1.0, "høy", False))]}


def time40(rad, bw=True):
    (_dag, _t, tot, sv, d, p, bwh, bwd, bwp, bwmax, ws, wd, g, (niva, tilstand, stiger)) = rad
    h = {"height_offshore": tot, "swell_offshore": sv, "swell_model": "standard", "dir_offshore": d, "period": p,
         "wind_speed": ws, "wind_dir": wd, "gust": g, "tide": {"level": niva, "state": tilstand, "rising": stiger}}
    return dict(h, bw_height=bwh, bw_dir=bwd, bw_period=bwp, bw_height_max=bwmax) if bw else h


def ikke_flatt40(r):
    """Timen viser verken «Flatt» eller «Treffer ikke» i appen: surfehøyden er minst 0,3 m (SMALL_SURF_MIN_M i
    docs/js/app.js, under den kan en 0-time hete «Flatt»), og grunnen er verken "flat" eller "treffer_ikke"."""
    return (r["surf_height"] is not None and r["surf_height"] >= 0.3 and not r["likely_flat"]
            and r["low_reason"] not in ("flat", "treffer_ikke"))


B40 = spots["breivikeidet"]
# svellet ute er det samme i timene for de tre spotene (samme punkt ute), så sammenlikningen under er time mot time
for i40 in rad40:
    for rad in rad40[i40]:
        bre40 = (bre_1711 if rad[0] == "17.11" else bre_2211)[rad[1]]
        assert (rad[3], rad[4], rad[5]) == (bre40["swell_offshore"], bre40["dir_offshore"], bre40["period"]), (i40, rad[:2])
# 40.1: begge dagene, begge spotene, begge soner: surfehøyde over 0, og verken «Flatt» eller «Treffer ikke». Poengene
# kan vinden og energiregelen ta (de to spotene har standard vindkurve og energiregel, Breivikeidet har egne).
r40 = {}
for i40 in rad40:
    for rad in rad40[i40]:
        for sone40 in (True, False):
            r = rate(time40(rad, bw=sone40), spots[i40])
            r40[(i40, rad[0], rad[1], sone40)] = r
            if sone40:
                show(f"40: {spots[i40]['name']} {rad[0]} kl. {rad[1]:02d}Z", r)
            assert r["height_source"] == ("barentswatch" if sone40 else "svell_ute"), (i40, rad[:2], sone40)
            assert r["surf_height"] > 0 and ikke_flatt40(r), (i40, rad[:2], sone40, r["surf_height"], r["low_reason"])
            # høyden er andelshøyden (svell ute × andel × kantfaktor), merket som anslag, og timen er usikker
            andel40 = fjord_share_height(time40(rad), spots[i40])
            # svell ute × andel × kantfaktor, og på Russelv aldri under 0,20 i 348-19° (gap_min_share, S36 b, test 41)
            kant40 = rad[3] * spots[i40]["gap_transfer"] * gap_edge_factor(time40(rad), spots[i40])
            assert abs(andel40 - (max(kant40, rad[3] * 0.2) if i40 == "russelv" else kant40)) < 1e-9, (i40, rad[:2], andel40, kant40)
            assert r["height"] == round(andel40, 2) and r.get("share_height") is True and r["uncertain"], (i40, rad[:2], sone40, r["height"])
            assert not r["sources_disagree"], (i40, rad[:2], sone40)
            # 0 poeng er aldri fordi høyden mangler: vinden eller energiregelen har tatt poengene
            assert r["stars"] >= 1 or r["zero_losses"]["wind"] + r["zero_losses"]["energy"] >= 1, (i40, rad[:2], sone40, r["zero_losses"])
        # like soner: samme høyde, surfehøyde, poeng og ord med og uten BarentsWatch-tallene
        a40, b40 = r40[(i40, rad[0], rad[1], True)], r40[(i40, rad[0], rad[1], False)]
        assert (a40["stars"], a40["height"], a40["surf_height"], a40["low_reason"]) == (b40["stars"], b40["height"], b40["surf_height"], b40["low_reason"]), (i40, rad[:2])
# kystkopiene (spotene slik de var) ga «flatt»-grunn eller under 0,3 m i minst én av disse timene: testen biter
assert not all(ikke_flatt40(rate(time40(rad, bw=sone40), sp40)) for i40, sp40 in (("russelv", RK), ("lenangsoyra", LK))
               for rad in rad40[i40] for sone40 in (True, False))
# 40.2: «treffer ikke» kommer aldri for en fjord-spot med svellet i det tegnede vinduet, heller ikke når den lærte eller
# bygde eksponeringen sier at retningen bommer (rå 0, glattet 0,1 overalt), i begge soner, for alle vinder.
# Russelv 17.11 kl. 09Z ga «treffer ikke» med 0,44 m ved spoten (andel 0,20) før unntaket i classify_low_rating().
assert r40[("russelv", "17.11", 9, True)]["low_reason"] != "treffer_ikke" and r40[("russelv", "17.11", 9, True)]["height"] == 0.49
n40 = 0
for sp40 in (R, RH, L, B40):
    lav40 = dict(sp40, exposure_raw=[0.0] * 360, exposure_smoothed=[0.1] * 360)
    for d40 in range(343, 393):
        for sv40 in (0.8, 1.5, 2.2, 3.0):
            for p40 in (6.0, 7.0, 9.0, 13.0):
                for ws40, wd40 in ((1.0, 200.0), (5.0, 20.0), (9.0, 20.0), (None, None)):
                    h40 = {"height_offshore": sv40 + 0.3, "swell_offshore": sv40, "swell_model": "standard", "dir_offshore": float(d40 % 360),
                           "period": p40, "wind_speed": ws40, "wind_dir": wd40, "gust": None}
                    if not fjord_in_window(h40, sp40):
                        continue
                    for spv40 in (sp40, lav40):
                        for hv40 in (h40, dict(h40, bw_height=0.3, bw_dir=float(d40 % 360), bw_period=2.5)):
                            assert rate(dict(hv40), spv40)["low_reason"] != "treffer_ikke", (sp40["id"], d40, sv40, p40, ws40)
                            n40 += 1
assert n40 > 5000, n40
# 24.11.2026 (fysikk-kontrolløren, vilkår 5): unntaket gjelder bare når høyden ER andelshøyden (share_height). Med
# BarentsWatch-tall og svellperiode under 7 s er høyden BarentsWatch-høyden, spoten regnes som en kyst-spot, og ordet
# er det samme som for kystkopien: «treffer ikke» når eksponeringen sier at retningen bommer. Fra 7 s er høyden
# andelshøyden, og ordet kommer aldri.
for sp40 in (R, RH, L, B40):
    lav40 = dict(sp40, exposure_raw=[0.0] * 360, exposure_smoothed=[0.1] * 360)
    kort40 = {"height_offshore": 1.8, "swell_offshore": 1.5, "swell_model": "standard", "dir_offshore": 17.0, "period": 6.5,
              "wind_speed": 1.0, "wind_dir": 200.0, "gust": None, "bw_height": 0.8, "bw_dir": 17.0, "bw_period": 6.0}
    assert fjord_in_window(kort40, lav40), sp40["id"]
    rk40, rkyst40 = rate(dict(kort40), lav40), rate(dict(kort40), dict(lav40, bw_tillit="kyst"))
    assert "share_height" not in rk40 and rk40["low_reason"] == rkyst40["low_reason"] == "treffer_ikke", (sp40["id"], rk40["low_reason"], rkyst40["low_reason"])
    assert (rk40["stars"], rk40["height"], rk40["surf_height"]) == (rkyst40["stars"], rkyst40["height"], rkyst40["surf_height"]), sp40["id"]
    rl40 = rate(dict(kort40, period=7.5), lav40)
    assert rl40.get("share_height") is True and rl40["low_reason"] != "treffer_ikke", (sp40["id"], rl40["low_reason"])
# kystkopien av Russelv får fortsatt «treffer ikke» for samme svell med lav eksponering: unntaket gjelder bare fjord
assert rate({"height_offshore": 1.8, "swell_offshore": 1.5, "swell_model": "standard", "dir_offshore": 5.0, "period": 9.0,
             "wind_speed": 1.0, "wind_dir": 200.0, "gust": None}, dict(RK, exposure_raw=[0.0] * 360, exposure_smoothed=[0.1] * 360))["low_reason"] == "treffer_ikke"
# 40.3: Lenangsøyra (svar.md 23.11.2026 kl. 14.05) og Russelv (svar.md 23.11.2026 kl. 21.00, S34 a) har samme vindu og
# kant som Breivikeidet, og andelen er minst like stor for alle retninger: ikke smalere vindu og ikke lavere andel.
# Derfor er høyden og surfehøyden minst Breivikeidets i hver time de to faste dagene (Russelv: 40.4).
for sp40 in (L, R):
    assert sp40["swell_window_tegnet"] == B40["swell_window_tegnet"] == [345, 30] and sp40["gap_edge_taper"] == B40["gap_edge_taper"], sp40["id"]
    assert sp40["gap_transfer"] >= B40["gap_transfer"] and sp40["gap_soft_edge"] and sp40["andel_forelopig"] is True, sp40["id"]
    for d40 in range(360):
        h40 = {"swell_offshore": 2.0, "swell_model": "standard", "dir_offshore": float(d40), "period": 8.0}
        assert fjord_in_window(h40, sp40) == fjord_in_window(h40, B40), (sp40["id"], d40)
        if fjord_in_window(h40, B40):
            assert fjord_share_height(h40, sp40) >= fjord_share_height(h40, B40) > 0, (sp40["id"], d40)
assert "andel_forelopig" not in B40
bre40 = {("17.11", t): r34[t] for t in (8, 9)}
bre40.update({("22.11", t): r36[t] for t in (8, 9, 10)})
for rad in rad40["lenangsoyra"]:
    assert r40[("lenangsoyra", rad[0], rad[1], True)]["surf_height"] >= bre40[rad[:2]]["surf_height"], rad[:2]
# 40.4: Russelv mot Breivikeidet, surfehøyde før vind i samme time (svar.md 23.11.2026 kl. 14.05, sjekk, og kl. 21.00,
# S34 a). Med samme vindu, kant og andel som Breivikeidet er høyden ved spoten og surfehøyden minst like stor i alle
# fem timene. Fra S36 b (svar.md 24.11.2026 kl. 10.25) er Russelv større 22.11 (svell fra 350-355°, andel 0,20 mot
# Breivikeidets 0,165-0,19), og lik 17.11 (17°, 0,22 på begge). Med 0,20 og hard kant (RH) var 17.11 kl. 08 og 09Z under Breivikeidet (0,73 m mot 0,79 m): det var funnet
# som S34 a retter. Lista under er timene der sjekken ikke holder, og den skal være tom.
under40, under40_rh = [], []
for rad in rad40["russelv"]:
    rus40, b40 = r40[("russelv", rad[0], rad[1], True)], bre40[rad[:2]]
    print(f"40.4: {rad[0]} kl. {rad[1]:02d}Z surfehøyde Russelv {rus40['surf_height']} m ({rus40['height']} m), Breivikeidet {b40['surf_height']} m ({b40['height']} m)")
    assert rus40["height"] >= b40["height"], (rad[:2], rus40["height"], b40["height"])
    if rus40["surf_height"] < b40["surf_height"]:
        under40.append(rad[:2])
    if rate(time40(rad), RH)["surf_height"] < b40["surf_height"]:
        under40_rh.append(rad[:2])
assert under40 == [], under40
assert under40_rh == [("17.11", 8), ("17.11", 9)], under40_rh      # testen biter: med 0,20 holder ikke 17.11
# 40.5: andelshøyden har sitt eget felt, share_height (svar.md 23.11.2026 kl. 14.05). Det finnes bare når høyden er
# andelshøyden for en fjord-spot: også når vinden gir 0 poeng (gap_floor er da usann) og i reserven under 7 s.
# Kyst-spots har det aldri, og en fjord-spot har det ikke utenfor det tegnede vinduet eller når BarentsWatch gjelder (under 7 s).
for i40, sp40 in list(spots.items()) + [("RK", RK), ("LK", LK)]:
    if not is_fjord(sp40):
        for h40 in timer39 + [time40(rad, bw=sone40) for i in rad40 for rad in rad40[i] for sone40 in (True, False)]:
            assert "share_height" not in rate(dict(h40), sp40), i40
for sp40 in (R, RH, L, B40):
    inne40 = {"height_offshore": 2.8, "swell_offshore": 2.5, "swell_model": "standard", "dir_offshore": 5.0, "period": 8.0,
              "wind_speed": 2.0, "wind_dir": 200.0, "gust": 4.0}
    bw40 = dict(bw_height=0.4, bw_dir=5.0, bw_period=3.0)
    for kw40 in ({}, bw40, dict(bw40, bw_height=1.4, bw_period=8.5)):
        r = rate(dict(inne40, **kw40), sp40)
        assert r.get("share_height") is True and r["gap_floor"], (sp40["id"], kw40)
        v40 = rate(dict(inne40, wind_speed=10.0, wind_dir=sp40["facing"], gust=14.0, **kw40), sp40)      # pålands 10 m/s: 0 poeng, høyden står
        assert v40.get("share_height") is True and not v40["gap_floor"] and v40["stars"] == 0 and v40["height"] == r["height"], (sp40["id"], kw40)
    assert rate(dict(inne40, period=6.5), sp40).get("share_height") is True and not rate(dict(inne40, period=6.5), sp40)["gap_floor"], sp40["id"]
    assert "share_height" not in rate(dict(inne40, period=6.5, **bw40), sp40), sp40["id"]
    for d40 in (60.0, 277.0):
        for kw40 in ({}, bw40):
            assert "share_height" not in rate(dict(inne40, dir_offshore=d40, **kw40), sp40), (sp40["id"], d40)
    assert "share_height" not in rate(dict(inne40, swell_offshore=None, **bw40), sp40) and "share_height" not in rate({"height_spot_model": 1.0, "period": 8.0}, sp40)
# 40.6: de faste observasjonene for de to spotene ligger utenfor det som er endret, eller holder med fjord-reglene.
# Lenangsøyra 26.09.2026 (vestlig sjø fra 277°, ikke surfbart, test 7.1 og 29.5): svellet er utenfor det tegnede
# vinduet, så timen regnes som for kystkopien i alle felt (bare andelen som vises, "transfer", er en annen). Russelv
# 16.11.2026 (test 31.1): 0,53 m (0,48 m før 24.11.2026), 1 poeng, surfbart.
uten40 = lambda r: {k: v for k, v in r.items() if k != "transfer"}
assert not fjord_in_window(l29, L) and uten40(rate(dict(l29), L)) == uten40(rate(dict(l29), LK))
assert rate(dict(l29), L)["stars"] == 0 and rate(dict(l29), L)["likely_flat"] and rate(dict(l29), L)["height"] < 0.35
# Taket mot vestlig sjø (225-320°, fra 26.09) står: uten det holder ikke observasjonen når kystlinjedataene bommer.
assert L["exposure_override"] == [{"from": 225, "to": 320, "max": 0.05}] and exposure_override_cap(277, L) == 0.05
r40_1611 = rate(dict(rus_1611), R)
assert (r40_1611["height"], r40_1611["stars"]) == (0.53, 1) and 0.9 <= r40_1611["surf_height_sets"] <= 1.2 and r40_1611.get("share_height") is True and ikke_flatt40(r40_1611)
print(f"40: Lyngen henger sammen - Russelv og Lenangsøyra har surfehøyde over 0 og verken «Flatt» eller «Treffer ikke» 17.11 kl. 08-09Z og 22.11 kl. 08-10Z i begge soner, aldri «treffer ikke» når høyden er andelshøyden ({n40} timer i det tegnede vinduet), Lenangsøyra og Russelv minst som Breivikeidet (S34 a), share_height bare for andelshøyden - OK")
# 41: S36 b (svar.md 24.11.2026 kl. 10.25): «Russelv får det største av Breivikeidets kurve og den gamle 0,20 med hard
# kant i 348–19°.» Feltet gap_min_share på Russelv og rating.gap_share(). Ingen andre spots har feltet.
from rating import gap_share
B41 = spots["breivikeidet"]
assert [i for i, sp in spots.items() if sp.get("gap_min_share")] == ["russelv"]
assert R["gap_min_share"] == {"window": [348, 19], "share": 0.2} and "gap_min_share" not in RH and "gap_min_share" not in RK
assert R["swell_window_tegnet"] == [345, 30] and R["gap_transfer"] == 0.22      # vinduet appen viser, og andelen langs aksen, er som i S34 a
# 41.1: andelen grad for grad. Den største av de to, aldri noe annet tall.
for d41 in range(343, 393):
    hd41 = {"swell_offshore": 2.4, "swell_model": "standard", "dir_offshore": float(d41 % 360), "period": 7.9}
    bre41 = gap_share(hd41, B41)
    rh41 = 0.2 if gap_swell_in_window(hd41, RH) else 0.0
    assert abs(gap_share(hd41, R) - max(bre41, rh41)) < 1e-12, (d41, gap_share(hd41, R), bre41, rh41)
    assert gap_share(hd41, B41) == B41["gap_transfer"] * gap_edge_factor(hd41, B41) and gap_share(hd41, L) == gap_share(hd41, B41), d41
assert gap_share(dict(hd41, dir_offshore=345.0), R) < 0.2 == gap_share(dict(hd41, dir_offshore=346.0), R) == gap_share(dict(hd41, dir_offshore=350.0), R)
assert gap_share(dict(hd41, dir_offshore=17.0), R) == 0.22 and gap_share(dict(hd41, dir_offshore=21.0), R) == 0.22 and gap_share(dict(hd41, dir_offshore=30.0), R) < 0.2
# 41.2: for hver grad 340-35°, 7,9 og 10 s, begge soner: Russelv gir aldri lavere høyde, surfehøyde eller poeng enn RH
# (Russelv 16.-23.11), og høyden er aldri under Breivikeidets kurve. Tre svellhøyder, svak fralandsvind.
# ETT UNNTAK, og det er ikke S36 b men fjord-regelen i det bredere vinduet fra S34 a: i BarentsWatch-sonen UTENFOR RHs
# vindu (343-345° og 22-32°) var RH en kyst-spot og brukte BarentsWatch-tallet, mens Russelv nå bruker andelshøyden
# («BarentsWatch løfter den ikke», S32 a). Viser punktet mer enn andelen, er høyden lavere enn hos RH. Testen prøver
# BARE 0,3 m ved punktet: da er de timene som blir lavere (343-345°) under flat-sperra hos begge, så bare høydetallet
# skiller. De telles (lavere41), og kravet der er poeng og surfehøyde, ikke høyde.
# Det gjelder IKKE generelt (fysikk-kontrolløren 24.11.2026): med mer ved punktet kan også surfehøyden og poengene bli
# lavere enn hos RH i 343-345° og 22-32°. Ekte: 22.11.2026 kl. 10Z (344°, punktet 1,24 m med 3,4 s) gir 0,60 m mot
# 0,63 m surfehøyde, 0 poeng begge veier. Regnet: 2,4 m og 14 s fra 343° med 0,8 m og 7-11 s ved punktet ga 4 poeng
# hos RH og gir 0 nå. Ingen poeng er tapt i de fire avspilte varslene. Lagt fram for Theodor som S39. Testen låser
# altså ikke «aldri lavere enn RH» utenfor 346-21° i BarentsWatch-sonen.
n41, storre41, lavere41 = 0, 0, []
for d41 in range(340, 396):
    for p41 in (7.9, 10.0):
        for sv41 in (1.8, 2.4, 3.2):
            for bw41 in ({}, {"bw_height": 0.3, "bw_dir": float(d41 % 360), "bw_period": 4.0}):
                h41 = {"height_offshore": sv41 + 0.2, "swell_offshore": sv41, "swell_model": "standard", "dir_offshore": float(d41 % 360),
                       "period": p41, "wind_speed": 2.0, "wind_dir": 106.0, "gust": 4.0, **bw41}
                r41, rh41 = rate(dict(h41), R), rate(dict(h41), RH)
                assert r41["surf_height"] >= rh41["surf_height"] and r41["stars"] >= rh41["stars"], (d41, p41, sv41, bw41, r41["surf_height"], rh41["surf_height"], r41["stars"], rh41["stars"])
                if bw41 and fjord_in_window(h41, R) and not fjord_in_window(h41, RH):
                    if r41["height"] < rh41["height"]:
                        lavere41.append((d41 % 360, p41, sv41, r41["height"], rh41["height"]))
                else:
                    assert r41["height"] >= rh41["height"], (d41, p41, sv41, bw41, r41["height"], rh41["height"])
                if fjord_in_window(h41, B41):
                    assert r41["height"] >= round(fjord_share_height(h41, B41), 2), (d41, p41, sv41, r41["height"])
                storre41 += r41["height"] > rh41["height"]
                n41 += 1
assert storre41 > 100, storre41
assert lavere41 and {x[0] for x in lavere41} <= {343, 344, 345} | set(range(22, 33)) and all(x[4] < 0.35 for x in lavere41), lavere41
print(f"41.2: {len(lavere41)} av {n41} timer har lavere høyde enn RH (BarentsWatch-sonen utenfor 346-21°, begge flate): retninger {sorted({x[0] for x in lavere41})}")
# 41.3: når 0,20-greina vinner (350°): share_height, anslag-linja med «andel 0,20», «Retning: …» fra det tegnede vinduet, og
# aldri «treffer ikke», i begge soner, også når vinden tar poengene og i reserven under 7 s. Tallet i linja er det som er brukt.
v41 = {"height_offshore": 2.6, "swell_offshore": 2.4, "swell_model": "standard", "dir_offshore": 350.0, "period": 7.9,
       "wind_speed": 2.0, "wind_dir": 106.0, "gust": 4.0}
R41 = dict(R, exposure_raw=[0.0] * 360, exposure_smoothed=[0.1] * 360)
gap41 = lambda r: [x for x in r["breakdown"] if "gjennom gapet, andel" in x]
SLUTT41 = " m: svell ute 2,4 m gjennom gapet, andel 0,20. Anslag, ikke kystmodellens tall"
for kw41, loftet41 in (({}, True), ({"bw_height": 0.3, "bw_dir": 350.0, "bw_period": 4.0}, True), ({"bw_height": 1.4, "bw_dir": 350.0, "bw_period": 8.5}, False),
                       ({"wind_speed": 10.0, "wind_dir": 350.0, "gust": 14.0}, False), ({"period": 6.5}, False)):
    r41 = rate(dict(v41, **kw41), R41)
    assert r41.get("share_height") is True and r41["height"] == 0.48 == round(2.4 * gap_share(v41, R), 2), (kw41, r41["height"])
    assert gap41(r41) == [("Løftet til 0,5" if loftet41 else "0,5") + SLUTT41], (kw41, gap41(r41))
    assert [x for x in r41["breakdown"] if x.startswith("Retning: ")] == ["Retning: treffer vinduet"] and r41["low_reason"] != "treffer_ikke", (kw41, r41["low_reason"])
    assert r41["gap_floor"] == loftet41 or kw41 == {"bw_height": 1.4, "bw_dir": 350.0, "bw_period": 8.5}, kw41
# med BarentsWatch-tall og under 7 s er høyden ikke andelen: ingen share_height, ingen linje, og ordet er som for en kyst-spot
k41 = rate(dict(v41, period=6.5, bw_height=0.8, bw_dir=350.0, bw_period=6.0), R41)
assert "share_height" not in k41 and gap41(k41) == [] and k41["low_reason"] == "treffer_ikke"
# reserven og BarentsWatch-sonen er like også i 0,20-greina
assert rate(dict(v41), R)["height"] == rate(dict(v41, bw_height=0.3, bw_dir=350.0, bw_period=4.0), R)["height"] == 0.48
print(f"41: S36 b - Russelvs andel er den største av Breivikeidets kurve og 0,20 i 348-19 (±2°), aldri under Breivikeidet, og aldri lavere surfehøyde eller poeng enn RH i {n41} testtimer med 0,3 m ved punktet (340-35°, 7,9 og 10 s, begge soner; utenfor 346-21° i BarentsWatch-sonen kan mer ved punktet gi lavere, S39), share_height, anslag-linja «andel 0,20», retningsordet og «treffer ikke» som ellers - OK")

# ---------- 44: S29 c del 2 (24.11.2026) - lang sjø fra havsiden som GFS kaller vindsjø. FORSLAG, STÅR AV ----------
# Observasjon 21.11.2026, Theodor (story fra Lofoten Surfsenter, dagslys, klokkeslett ukjent): Unstad «litt under
# hodehøyt og rent». Appen viste 0 poeng og 0,0 m i alle lyse timer. Timene er fra det lagrede varselet 21.11 kl. 11Z.
# Feltene for den samlede sjøen og vindsjø-delen ute ble ikke lagret den gang: de er GFS Wave sine egne tall for de
# samme timene, hentet med ett kall til Open-Meteo 24.11.2026 (past_days). Regelen krever Theodors ja før den slås på.
import rating as _rating44
from rating import long_sea, exposure_override_cap, blocked_by_near_obstacle
assert _rating44.LONG_SEA_AS_SWELL is False, "regelen for lang sjø skal stå AV til Theodor har sagt ja (S29 c)"
assert _rating44.LONG_SEA_SPOTS == {"unstad"}
U44 = dict(spots["unstad"])
_sm44, _raw44, _warn44 = _fetch.resolve_exposure(U44, _exposure_baseline_real, "Unstad")
U44["exposure_smoothed"], U44["exposure_raw"] = _sm44, _raw44
U44["exposure_distance_km"], U44["exposure_width_km"] = _fetch.resolve_obstacle_geometry(U44, _exposure_baseline_real)
U44["transfer"], U44["surf_factor"] = 0.6, 1.45
H44 = {
    11: {"t": "2026-11-21T11:00Z", "bw_period_real_max_3h": 9.4, "total_model": "gfs", "height_offshore": 3.2, "swell_offshore": 0.58, "swell_model": "gfs", "dir_offshore": 250, "period": 12.0, "swell_peak_period": None, "turn": 92.2, "wind_speed": 7.2, "wind_dir": 5.0, "gust": 12.7, "tide": {"level": 0.63, "state": "middels", "rising": False}, "light": "dag", "daylight": True, "bw_interpolated": True, "bw_height": 0.43, "bw_height_max": 0.817, "bw_period": 7.7, "bw_dir": 316.0, "height_spot_model": 2.7, "dir_spot": 342.2, "total_height_offshore": 2.76, "total_dir_offshore": 3, "total_period_offshore": 10.15, "wind_wave_height_offshore": 2.7, "wind_wave_dir_offshore": 359, "wind_wave_period_offshore": 10.15},
    12: {"t": "2026-11-21T12:00Z", "bw_period_real_max_3h": 9.4, "total_model": "gfs", "height_offshore": 3.1, "swell_offshore": 0.56, "swell_model": "gfs", "dir_offshore": 250, "period": 11.95, "swell_peak_period": None, "turn": 91.5, "wind_speed": 7.0, "wind_dir": 357.0, "gust": 11.7, "tide": {"level": 0.38, "state": "middels", "rising": False}, "light": "skumring", "daylight": True, "bw_interpolated": False, "bw_height": 0.37, "bw_height_max": 0.703, "bw_period": 9.4, "bw_dir": 312.0, "height_spot_model": 2.6, "dir_spot": 341.5, "total_height_offshore": 2.7, "total_dir_offshore": 4, "total_period_offshore": 10.2, "wind_wave_height_offshore": 2.64, "wind_wave_dir_offshore": 358, "wind_wave_period_offshore": 10.15},
    13: {"t": "2026-11-21T13:00Z", "bw_period_real_max_3h": 9.4, "total_model": "gfs", "height_offshore": 2.9, "swell_offshore": 0.52, "swell_model": "gfs", "dir_offshore": 250, "period": 11.9, "swell_peak_period": None, "turn": 90.8, "wind_speed": 6.0, "wind_dir": 351.0, "gust": 11.4, "tide": {"level": 0.15, "state": "lav", "rising": False}, "light": "skumring", "daylight": True, "bw_interpolated": True, "bw_height": 0.43, "bw_height_max": 0.817, "bw_period": 7.7, "bw_dir": 316.0, "height_spot_model": 2.5, "dir_spot": 340.8, "total_height_offshore": 2.6, "total_dir_offshore": 4, "total_period_offshore": 10.15, "wind_wave_height_offshore": 2.54, "wind_wave_dir_offshore": 358, "wind_wave_period_offshore": 10.1},
    # 22.11.2026 kl. 12Z (samme varsel): toppperioden ved punktet er 4,3 s. Støtte: surfbart ca. kl. 13Z (Theodor 23.11.2026)
    36: {"t": "2026-11-22T12:00Z", "bw_period_real_max_3h": 4.3, "total_model": "gfs", "height_offshore": 2.7, "swell_offshore": 0.38, "swell_model": "gfs", "dir_offshore": 251, "period": 11.1, "swell_peak_period": None, "turn": 90.9, "wind_speed": 8.1, "wind_dir": 355.0, "gust": 13.1, "tide": {"level": 0.57, "state": "middels", "rising": False}, "light": "skumring", "daylight": True, "bw_interpolated": False, "bw_height": 0.53, "bw_height_max": 1.007, "bw_period": 4.3, "bw_dir": 324.0, "height_spot_model": 2.4, "dir_spot": 341.9, "total_height_offshore": 2.44, "total_dir_offshore": 4, "total_period_offshore": 9.75, "wind_wave_height_offshore": 2.42, "wind_wave_dir_offshore": 0, "wind_wave_period_offshore": 9.75},
}
_FELT44 = ("bw_period_real_max_3h", "total_model", "total_height_offshore", "total_dir_offshore", "total_period_offshore", "wind_wave_height_offshore", "wind_wave_dir_offshore", "wind_wave_period_offshore")
# 44.1 AV (slik main står): feltene fra del 1 endrer ingenting i ratingen - samme svar med og uten dem, og timene står på 0
for _t, _h in H44.items():
    _med, _uten = rate(dict(_h), U44), rate({k: v for k, v in _h.items() if k not in _FELT44}, U44)
    assert _med == _uten, f"feltene fra S29 c del 1 skal ikke endre ratingen ({_t})"
    assert _med["stars"] == 0 and _med["surf_height"] == 0.0 and "long_sea" not in _med
    assert long_sea(_h, U44) is None


def _med_regel44(h, spot, spots=frozenset({"unstad"}), variant="vindu"):
    """rate() med regelen slått på bare inni kallet. variant: "vindu" (A'), "time" (A) eller None (B)."""
    old = (_rating44.LONG_SEA_AS_SWELL, _rating44.LONG_SEA_SPOTS, _rating44.LONG_SEA_BW_CONFIRM)
    _rating44.LONG_SEA_AS_SWELL, _rating44.LONG_SEA_SPOTS, _rating44.LONG_SEA_BW_CONFIRM = True, spots, variant
    try:
        return rate(dict(h), spot)
    finally:
        _rating44.LONG_SEA_AS_SWELL, _rating44.LONG_SEA_SPOTS, _rating44.LONG_SEA_BW_CONFIRM = old


# 44.2 PÅ (A', grunnvalget): målet for 21.11 (minst 2 poeng i minst én lys time, helst 3). Surfehøyden blir
# 1,02-1,15 m, litt under «ca. 1,2-1,6 m» (BarentsWatch-høyden 0,37-0,43 m tatt for god, 10,1 s). Usikker (høyst 3).
# Kl. 11 og 13Z er 7,7 s ved punktet interpolert; det er den ekte modelltimen kl. 12Z (9,4 s) som bekrefter.
assert _rating44.LONG_SEA_BW_CONFIRM == "vindu" and _rating44.LONG_SEA_BW_PERIOD_MIN_S == 7.0
r44 = {t: _med_regel44(h, U44) for t, h in H44.items()}
for _t in (11, 12, 13, 36):
    show(f"44.2: Unstad {H44[_t]['t'][5:13]}Z med regelen (A')", r44[_t])
assert [r44[t]["stars"] for t in (11, 12, 13)] == [3, 2, 3], [r44[t]["stars"] for t in (11, 12, 13)]
assert [r44[t]["surf_height"] for t in (11, 12, 13)] == [1.15, 1.02, 1.14], [r44[t]["surf_height"] for t in (11, 12, 13)]
assert all(r44[t]["uncertain"] and not r44[t]["sources_disagree"] and r44[t]["low_reason"] is None for t in (11, 12, 13))
assert r44[11]["long_sea"] == {"swell_offshore": 2.76, "period": 10.15, "dir_offshore": 359} and r44[11]["bw_period_basis"] == "lang_sjo"
assert r44[11]["energy_swell_kj"] > 2000 and r44[11]["swell_share"] == 1.0 and r44[11]["bw_confirms"]
# 22.11 kl. 12Z i varselet fra 21.11 (4,3 s i de ekte modelltimene kl. 09, 12 og 15Z): A' og A rører den ikke,
# B (ingen periodegrense ved punktet, svaret på S40: nei) løfter den. Etter M4 (44.7) til 2 poeng og 1,01 m, før 3 og 1,34 m
assert r44[36]["stars"] == 0 and "long_sea" not in r44[36]
rB44 = {t: _med_regel44(h, U44, variant=None) for t, h in H44.items()}
assert [rB44[t]["stars"] for t in (11, 12, 13, 36)] == [3, 2, 3, 2] and rB44[36]["surf_height"] == 1.01
rA44 = {t: _med_regel44(h, U44, variant="time") for t, h in H44.items()}
assert [rA44[t]["stars"] for t in (11, 12, 13, 36)] == [3, 2, 3, 0] and "long_sea" not in rA44[36]
# forskjellen på A og A': en time med 4,3 s ved punktet, men 8,4 s i en ekte modelltime to timer senere
# (22.11 kl. 13Z i varselet fra 22.11 kl. 01Z: 5,7 s interpolert, 8,4 s kl. 15Z) - og omvendt en interpolert 7,7 s
# uten noen ekte modelltime over 7 s i vinduet
_h44v = dict(H44[36], bw_period=5.7, bw_dir=320.0, bw_height=0.5, bw_interpolated=True, bw_period_real_max_3h=8.4)
assert _med_regel44(_h44v, U44)["stars"] == 2 and "long_sea" not in _med_regel44(_h44v, U44, variant="time")
_h44i = dict(H44[11], bw_period_real_max_3h=6.9)
assert "long_sea" not in _med_regel44(_h44i, U44) and "long_sea" in _med_regel44(_h44i, U44, variant="time")
assert "long_sea" not in _med_regel44(dict(H44[11], bw_period_real_max_3h=None), U44), "mangler perioden i vinduet: regelen gjør ingenting"
# 44.3 hvert vilkår for seg: uten det slår regelen ikke til, og timen er som på main
for _navn, _endring in (
        ("vindsjø-delen er kort (8,9 s)", {"wind_wave_period_offshore": 8.9}),
        ("vinden er for sterk for så kort sjø (13,5 m/s mot 10,15 s)", {"wind_speed": 13.5}),
        ("vinden mangler", {"wind_speed": None}),
        ("sjøen kommer mer enn 30° utenfor vinduet (10°)", {"wind_wave_dir_offshore": 10}),
        ("sjøen kommer fra land (120°)", {"wind_wave_dir_offshore": 120}),
        ("bølgene ved punktet kommer ikke inn (350°, 55° fra facing)", {"bw_dir": 350.0}),
        ("retningen ved punktet mangler", {"bw_dir": None}),
        ("svellet er ikke et GFS-felt", {"swell_model": "standard"}),
        ("svellet er et anslag fra totalhøyden", {"swell_model": "total_fallback"}),
        ("vindsjø-høyden mangler", {"wind_wave_height_offshore": None}),
        ("vindsjø-retningen mangler", {"wind_wave_dir_offshore": None}),
        ("vindsjø-perioden mangler", {"wind_wave_period_offshore": None}),
        ("ingen ekte modelltime med minst 7 s ved punktet innen ±3 timer", {"bw_period_real_max_3h": 6.9}),
        ("svellet i timen er glattet av despike_swell() (M3, 44.6)", {"swell_despiked": {"swell_height": 2.4, "dir": 355, "period": 9.8}}),
        ("totalhøyden ute mangler (M3)", {"total_height_offshore": None}),
        ("totalhøyden ute er ikke GFS sin egen (M3)", {"total_model": "standard"}),
        ("totalhøyden ute har ikke noe modellmerke (M3)", {"total_model": None}),
        ("ingen BarentsWatch-høyde (reserven)", {"bw_height": None, "bw_dir": None, "bw_period": None, "bw_period_real_max_3h": None})):
    _h = dict(H44[11], **_endring)
    assert _med_regel44(_h, U44) == rate(dict(_h), U44), _navn
# andre spots er ikke med (bare Unstad har en observasjon), fjord-spots aldri, og taket Theodor har satt (exposure_override) gjelder
_K44 = dict(spots["kvalvika"], transfer=0.6, surf_factor=1.0)
_hk44 = dict(H44[11], bw_dir=_K44["facing"], wind_wave_dir_offshore=_K44["facing"])
assert _med_regel44(_hk44, _K44) == rate(dict(_hk44), _K44), "regelen gjelder bare Unstad"
assert "long_sea" in _med_regel44(_hk44, _K44, spots=None), "med alle kyst-spots (ikke foreslått) ville den slått til"
for _sid in ("breivikeidet", "russelv", "lenangsoyra"):
    _f = dict(spots[_sid]); _hf = dict(H44[11], bw_dir=_f["facing"], wind_wave_dir_offshore=_f["facing"], dir_offshore=_f["facing"])
    assert is_fjord(_f) and _med_regel44(_hf, _f, spots=None) == rate(dict(_hf), _f), _sid
_G44 = dict(spots["grotfjord"], transfer=0.6, surf_factor=1.0)
_hg44 = dict(H44[11], bw_dir=_G44["facing"], bw_height=0.8, wind_wave_dir_offshore=320)   # 320° ligger under Grøtfjords tak (311-330)
assert exposure_override_cap(320, _G44) is not None and _med_regel44(_hg44, _G44, spots=None) == rate(dict(_hg44), _G44)
_F44 = dict(F27)
_hf44 = dict(H27, wind_wave_height_offshore=5.06, wind_wave_period_offshore=9.5, wind_wave_dir_offshore=338, total_height_offshore=6.6, total_model="gfs")
assert blocked_by_near_obstacle(338, _F44) and _med_regel44(_hf44, _F44, spots=None, variant=None) == r27, "Nordneset: lang sjø fra 338° løfter aldri Farstadsanden"
# 44.4 regelen kan bare løfte. Verste fall for Unstads faste observasjoner: hele resten av totalhøyden ute lagt inn
# som lang sjø (10 s) rett inn mot stranda. 27.09 kl. 08 gir 4 på main og ville fått 3 med taket for usikre timer:
# da gjelder main sitt svar. Alle kravene i CLAUDE.md holder (27.09 kl. 06-08 minst 2, 28.09 kl. 12-15 minst 3).
import backtest as _backtest44
_n44 = 0
for _c in _backtest44.fixed_cases():
    if _c["spot"] != "unstad":
        continue
    _h = dict(_c["hour"])
    _ww = max(0.0, _h["height_offshore"] ** 2 - _h["swell_offshore"] ** 2) ** 0.5
    _h.update(swell_model="gfs", total_model="gfs", total_height_offshore=_h["height_offshore"], wind_wave_height_offshore=_ww or None,
              wind_wave_period_offshore=10.0 if _ww else None, wind_wave_dir_offshore=294.8 if _ww else None)
    _for, _etter = rate(dict(_c["hour"]), U44), _med_regel44(_h, U44)
    assert _etter["stars"] >= _for["stars"] and _etter["stars"] >= _c["expect"].get("stars_min", 0), (_c["id"], _for["stars"], _etter["stars"])
    _n44 += 1
assert _n44 == 8
# Farstadsanden 15.10 kl. 17 (test 27 og 28): vindsjø-delen den dagen er ikke lagret. Var den lang og fra vinduet
# (antatt her: 5,06 m fra 300° med 9,5 s), ville omregningen gitt 2 poeng i stedet for 4 (den bytter 17 s svell
# mot 9,5 s sjø som hovedsvell, og tar hele BarentsWatch-høyden for god). Fordi regelen bare kan løfte, gjelder da
# det vanlige svaret - testen holder også om regelen en gang skulle gjelde alle kyst-spots.
_hf44b = dict(_hf44, wind_wave_dir_offshore=300)
assert long_sea(dict(_hf44b), _F44) is None   # bryteren er av
assert _med_regel44(_hf44b, _F44, spots=None, variant=None) == r27
# 44.5 læringen: en time der regelen har slått til (feltet long_sea) gir aldri et transfer-par (calibrate) eller et
# eksponeringspar (exposure_learn) - svellet i timen er fortsatt det lille GFS skilte ut, høyden ved punktet er den lange sjøen
import calibrate as _calibrate44, exposure_learn as _exposure_learn44
_par44 = {"t": "2026-11-21T12:00Z", "height_source": "barentswatch", "bw_interpolated": False, "sources_disagree": False,
          "spot_direction_factor": 1.0, "bw_height": 0.9, "swell_offshore": 2.0, "directness": 1.0, "dir_offshore": 290,
          "height_offshore": 2.2, "swell_share": 0.91, "period": 12.0}
assert len(_calibrate44.bw_pairs_for_run([dict(_par44)], "x", U44)) == 1
assert _calibrate44.bw_pairs_for_run([dict(_par44, long_sea={"swell_offshore": 2.7, "period": 10.15, "dir_offshore": 358})], "x", U44) == []
_e44 = _exposure_learn44.exposure_pairs_for_run
assert len(_e44([dict(_par44)], "x", U44)) == 1 and _e44([dict(_par44, long_sea={"swell_offshore": 2.7})], "x", U44) == []
_h44l = {**H44[12], **r44[12]}
assert _h44l["height_source"] == "barentswatch"
assert "long_sea" in _h44l and _calibrate44.bw_pairs_for_run([_h44l], "x", U44) == [] and _e44([_h44l], "x", U44) == []
# 44.6 M3 (fysikk-kontrolløren 24.11.2026, S40): svellet i en time kan være byttet mot snittet av nabotimene
# (sources.despike_swell(), originalen i swell_despiked). Vindsjø-delen og totalen er timens rå GFS-tall. Lagt sammen
# ville de telt den samme sjøen to ganger. Eksempel: GFS la sjøen i svell-delen i nabotimene (2,5 m) og i vindsjø-delen
# i denne timen (svell 0,56 m, vindsjø 2,64 m, total 2,70 m). Glattet svell er 2,5 m: kvadratsummen med 2,64 m er 3,64 m,
# 35 % over GFS sin egen totalhøyde. (a) En glattet time er aldri med i regelen. (b) Uansett grunn blir svell og lang sjø
# lagt sammen aldri mer enn GFS sin totalhøyde i timen, og totalhøyden i svellandelen er GFS sin egen.
import math
_h44d = dict(H44[12], swell_offshore=2.5, period=9.8, dir_offshore=355, swell_despiked={"swell_height": 0.56, "dir": 250, "period": 11.95})
assert math.sqrt(2.5 ** 2 + H44[12]["wind_wave_height_offshore"] ** 2) > 1.3 * H44[12]["total_height_offshore"]
assert _med_regel44(_h44d, U44) == rate(dict(_h44d), U44) and "long_sea" not in _med_regel44(_h44d, U44), "M3: glattet svell skal ikke legges sammen med rå vindsjø"
_old44 = _rating44.LONG_SEA_AS_SWELL
_rating44.LONG_SEA_AS_SWELL = True
try:
    _ls44 = long_sea(dict(H44[12], swell_offshore=2.5), U44)          # ikke merket som glattet, men delene er mer enn helheten
    _ls44n = long_sea(dict(H44[12]), U44)
finally:
    _rating44.LONG_SEA_AS_SWELL = _old44
assert _ls44["swell_offshore"] == H44[12]["total_height_offshore"] == _ls44["height_offshore"], "M3: aldri mer enn GFS sin totalhøyde"
assert abs(_ls44n["swell_offshore"] - math.sqrt(0.56 ** 2 + 2.64 ** 2)) < 1e-9 and _ls44n["height_offshore"] == 2.7
for _t in (11, 12, 13):   # de tre lyse timene 21.11: kvadratsummen er alt innenfor totalen (høyst 0,01 m over), så svaret er som før M3
    assert r44[_t]["long_sea"]["swell_offshore"] <= H44[_t]["total_height_offshore"]
# 44.7 M4 (fysikk-kontrolløren 24.11.2026, S40): H i surfehøyde-formelen var hele BarentsWatch-høyden ved punktet, også
# når toppen der er kort. Nå: er toppperioden ved punktet i selve timen under 7 s (eller mangler), regnes høyst halve
# energien ved punktet som lang sjø (H / √2). Er den 7 s eller mer i timen, brukes hele høyden som før.
assert _rating44.LONG_SEA_SHORT_PEAK_ENERGY_SHARE == 0.5
# 21.11 kl. 15Z i varselet fra 21.11 kl. 11Z: 0,55 m fra 324° med 4,3 s ved punktet, 9,4 s i modelltimen kl. 12Z
_h44k = dict(H44[13], t="2026-11-21T15:00Z", bw_height=0.55, bw_dir=324.0, bw_period=4.3, bw_interpolated=False, bw_period_real_max_3h=9.4,
             wind_speed=7.3, wind_dir=0.0, light="mørkt", daylight=False)
_rk44 = _med_regel44(_h44k, U44)
show("44.7: Unstad 21.11 kl. 15Z, kort topp ved punktet (4,3 s)", _rk44)
assert _rk44["bw_period_basis"] == "lang_sjo_kort_topp" and abs(_rk44["height"] - 0.55 / math.sqrt(2)) < 0.006, _rk44["height"]
_rk44l = _med_regel44(dict(_h44k, bw_period=7.0), U44)     # samme time med 7,0 s i timen: hele høyden
assert _rk44l["bw_period_basis"] == "lang_sjo" and _rk44l["height"] == 0.55
assert 0 < _rk44["surf_height"] < _rk44l["surf_height"] and _rk44["stars"] <= _rk44l["stars"] <= 3 and _rk44["uncertain"]
# surfehøyden følger H^0,8 (Komar og Gaughan): (1/√2)^0,8 = 0,758
assert abs(_rk44["surf_height"] / _rk44l["surf_height"] - 0.5 ** 0.4) < 0.01, (_rk44["surf_height"], _rk44l["surf_height"])
# mangler perioden i timen (A' kan slå til på modelltimen ved siden av): som kort topp, aldri som lang
assert _med_regel44(dict(_h44k, bw_period=None), U44)["bw_period_basis"] == "lang_sjo_kort_topp"
# flat-sperren gjelder den reduserte høyden: 0,49 m med kort topp er 0,346 m lang sjø, under 0,35 m. Da gir regelen
# ingenting, og timen står som uten regelen (0 poeng)
_rk44f = _med_regel44(dict(_h44k, bw_height=0.49), U44)
assert _rk44f == rate(dict(_h44k, bw_height=0.49), U44) and _rk44f["stars"] == 0
# perioden i formelen er fortsatt sjøens periode ute (CLAUDE.md «Konvensjoner»), ikke toppen ved punktet
assert _rk44["long_sea"]["period"] == H44[13]["wind_wave_period_offshore"]
print(f"44: S29 c del 2 står AV - feltene fra del 1 endrer ingenting; med regelen på (A') gir Unstad 21.11 kl. 11-13Z 3, 2 og 3 poeng (1,15, 1,02 og 1,14 m, usikker), A, A' og B skiller seg som beskrevet, hvert vilkår kan stoppe den, bare Unstad, aldri fjord-spots, tak og Nordneset gjelder, den kan bare løfte, læringen hopper over timene, M3 (glattet svell er aldri med, aldri mer enn GFS sin total) og M4 (kort topp ved punktet: høyst halve energien) - OK")
print("Alle tester ok")
