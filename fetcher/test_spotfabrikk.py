"""Spotfabrikkens godkjenningsregler (Theodor 16.10.2026): tools/godkjenn_spot.py skal bare legge inn en bygget spot
når posisjonen er godkjent av Theodor eller av Claude (delegert), posisjonen i bygget-fila er den godkjente,
BarentsWatch-snittet er kjørt og felt og høyder finnes - og fabrikkens flagg krever --overstyr med kommentar.
spots.json er håndformatert: innsettingen skal la de eksisterende spotene stå byte for byte.

Kjør: python fetcher/test_spotfabrikk.py   (ingen nett, under 5 s)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import godkjenn_spot as g  # noqa: E402

spots = json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))
snitt = "data/bw_point_search/snitt_2026-10-15.md"   # en fil som finnes - står for «snittet er kjørt»
P = {"lat": 68.1, "lon": 13.9}
bygget = {"spot": {"id": "testspot", "spot": P, "facing": 300.0, "swell_window": [260, 340], "offshore": {"lat": 68.2, "lon": 13.5},
                   "offshore_wind": [75, 165], "barentswatch_point": {"lat": 68.11, "lon": 13.88}, "_barentswatch": "Snitt …",
                   "_barentswatch_snitt": snitt, "ideal_height": [0.8, 2.0], "max_height": 3.5, "region": "Lofoten"}, "flagg": []}
kand = {"testspot": {"id": "testspot", "status": "kandidat"}}
DELEGERT = "claude (delegert av Theodor 16.10.2026)"
SPOTANSVARLIG = "spotansvarlig (agent, Theodor 10.11.2026)"   # Theodor 10.11.2026: subagenten har overtatt gjennomgangen

def check(pos, b=bygget):
    return g.check("testspot", b, spots, {"testspot": pos}, kand)

# 1. ikke godkjent → stopp (også listepinnen og «forslag»)
why, _ = check({"spot": P, "satt_av": "liste"})
assert any("ikke godkjent" in w for w in why), why
why, _ = check({"spot": P, "satt_av": DELEGERT, "vurdering": "venter_lokalkunnskap"})
assert any("ikke godkjent" in w for w in why), why
# 2. godkjent av Theodor, Claude (delegert) eller spotansvarlig, alt på plass → ingen stopp
for av in ("theodor", DELEGERT, SPOTANSVARLIG):
    why, flagg = check({"spot": P, "satt_av": av, "vurdering": "godkjent"})
    assert not why and not flagg, (av, why, flagg)
# 3. bygget for en annen posisjon enn den godkjente → stopp
why, _ = check({"spot": {"lat": 68.2, "lon": 13.9}, "satt_av": DELEGERT, "vurdering": "godkjent"})
assert any("ikke lik" in w for w in why), why
# 4. snittet ikke kjørt (foreløpig punkt) → stopp; høyder mangler → stopp
b4 = json.loads(json.dumps(bygget)); b4["spot"]["_barentswatch"] = "FORELØPIG: …"
why, _ = check({"spot": P, "satt_av": DELEGERT, "vurdering": "godkjent"}, b4)
assert any("snittet" in w for w in why), why
b5 = json.loads(json.dumps(bygget)); b5["spot"]["ideal_height"] = None
why, _ = check({"spot": P, "satt_av": DELEGERT, "vurdering": "godkjent"}, b5)
assert any("ideal_height" in w for w in why), why
# 5. fabrikkens flagg og BarentsWatch uten data → flagg (krever --overstyr), ikke stopp
b6 = json.loads(json.dumps(bygget)); b6["flagg"] = ["facing … står nålen i hjørnet av en buet strand?"]; b6["spot"]["barentswatch_point"] = None
why, flagg = check({"spot": P, "satt_av": DELEGERT, "vurdering": "godkjent"}, b6)
assert not why and len(flagg) == 2 and any("BarentsWatch uten data" in f for f in flagg), (why, flagg)
# 6. innsettingen lar de eksisterende spotene stå
text = (ROOT / "spots.json").read_text(encoding="utf-8")
out = g.insert_text(text, spots, {"id": "testspot", "status": "forelopig"}, None)
new = json.loads(out)
assert new["spots"][:-1] == spots["spots"] and new["spots"][-1]["id"] == "testspot"
assert out.startswith(text.rstrip()[: text.rstrip().rindex("}\n  ]")])
# 7. importer_godkjenning: en CSV kan bare gi den delegerte godkjenneren, aldri «theodor»
import csv, importer_godkjenning as ig, subprocess, tempfile  # noqa: E401,E402
with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id", "lat", "lon", "beslutning", "sikkerhet", "satt_av", "dato", "begrunnelse"])
    w.writerow(["bleik", 69.28, 15.97, "godkjent", "B", "theodor", "2026-10-16", "x"])
r = subprocess.run([sys.executable, str(ROOT / "tools" / "importer_godkjenning.py"), f.name], capture_output=True, text=True, timeout=30)
assert r.returncode != 0 and "kan bare gi" in (r.stderr + r.stdout), r
import godkjennere  # noqa: E402
assert "theodor" not in godkjennere.FRA_CSV and {DELEGERT, SPOTANSVARLIG} == godkjennere.FRA_CSV, godkjennere.FRA_CSV
assert godkjennere.GODKJENNERE == {"theodor", DELEGERT, SPOTANSVARLIG} and ig.FRA_CSV is godkjennere.FRA_CSV
# 8. velg_bw_punkt.choose_strict: ukjent dybde eller ukjent Hs i neste punkt godtas aldri
import velg_bw_punkt as vb  # noqa: E402
row = lambda d, hs, dep: {"label": f"snitt {d}m", "dist": d, "hs": hs, "depth": dep, "dir": 300.0, "swell_dir": 300.0, "swell_h": 2.0, "lat": 1, "lon": 1}
assert vb.choose_strict([row(0, 1.0, None), row(100, 1.05, None), row(200, 1.06, None)]) is None          # dybde ukjent
assert vb.choose_strict([row(0, 1.0, 9.0), row(100, None, 10.0)]) is None                                  # neste Hs ukjent
assert vb.choose_strict([row(0, 1.0, 4.0), row(100, 1.5, 9.0), row(200, 1.55, 12.0), row(300, 1.56, 14.0)])["dist"] == 100
assert vb.in_window(350, [315, 16]) and not vb.in_window(270, [315, 16]) and vb.in_window(10, [[5, 15], [349, 356]])
print("Spotfabrikken: godkjent av Theodor/Claude (delegert)/spotansvarlig kreves, posisjon må stemme, snitt og høyder kreves, flagg krever --overstyr, spots.json urørt ved innsetting - OK")
print("Alle tester ok")
