"""Tester ratingen mot det du faktisk har observert. Kjør: python fetcher/test_rating.py"""
import json
from pathlib import Path
from rating import rate

spots = {s["id"]: s for s in json.loads((Path(__file__).parent.parent / "spots.json").read_text())["spots"]}
G, E = spots["grotfjord"], spots["ersfjordstranda"]

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
sv = rate({"swell_offshore": 1.0, "height_spot_model": 2.4, "dir_offshore": 300, "turn": 5,
           "period": 11, "wind_speed": 3, "wind_dir": 120}, G)
show("Svell 1,0 m ute, met.no total 2,4 m", sv); assert sv["height_source"] == "svell_ute" and sv["height"] < 1.0

# Strenghet: en helt ok dag skal ikke gi mer enn 3.
ok = rate({"bw_height": 1.2, "dir_offshore": 300, "turn": 5, "period": 10, "wind_speed": 3, "wind_dir": 120}, G)
show("Vanlig ok dag", ok); assert ok["stars"] <= 3

# 5 stjerner krever alt: midt i ideell høyde, lang periode, midt i vinduet, blankt.
epic = rate({"bw_height": 1.4, "dir_offshore": 300.5, "turn": 3, "period": 15, "wind_speed": 1, "wind_dir": 120}, G)
show("Alt perfekt", epic); assert epic["stars"] == 5

# Nesten perfekt, men 11 s periode: skal ikke bli 5.
near = rate({"bw_height": 1.4, "dir_offshore": 300, "turn": 3, "period": 11, "wind_speed": 1, "wind_dir": 120}, G)
show("Nesten perfekt, 11 s", near); assert near["stars"] <= 4

# Uten BarentsWatch og med dreining: maks 3 uansett.
unc = rate({"height_spot_model": 1.5, "dir_offshore": 308, "turn": 15, "period": 15, "wind_speed": 1, "wind_dir": 90}, E)
show("Usikker (met.no, 15 grader dreining)", unc); assert unc["stars"] <= 3 and unc["uncertain"]

# Onshore 6 m/s skal ta minst 3 stjerner.
on = rate({"bw_height": 1.4, "dir_offshore": 300, "turn": 3, "period": 15, "wind_speed": 6, "wind_dir": 300}, G)
show("Perfekt svell, onshore 6 m/s", on); assert on["faded"] >= 3
# Tidevann: spot som bare liker lavt vann mister en stjerne på flo.
T = {**G, "tide": ["lav", "middels"]}
base = {"bw_height": 1.4, "dir_offshore": 300.5, "turn": 3, "period": 15, "wind_speed": 1, "wind_dir": 120}
lo = rate({**base, "tide": {"state": "lav"}}, T); hi = rate({**base, "tide": {"state": "høy"}}, T)
show("Liker lavt vann, fjære", lo); show("Liker lavt vann, flo", hi)
assert lo["stars"] == 5 and hi["stars"] == 4 and hi["faded_tide"] == 1
# Observert 25.09.2026: svell ute 313 grader, vinduet er [291,310] - bare 3
# grader utenfor. Helt flatt i praksis, ingen delvis kreditt nær kanten.
just_outside = rate({"swell_offshore": 1.76, "dir_offshore": 313.3, "turn": 13.6,
                      "period": 9.2, "wind_speed": 1.6, "wind_dir": 79}, G)
show("Grøtfjord 25.09, 3 grader utenfor vinduet", just_outside)
assert just_outside["stars"] == 0 and just_outside["likely_flat"]

print("Alle tester ok")
