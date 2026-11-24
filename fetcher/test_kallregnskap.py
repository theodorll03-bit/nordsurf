"""S6: kallregnskapet (tools/kallregnskap.py) skal ligge under 50 % av hver kjent grense hos Open-Meteo
(minutt, time, døgn, måned) - for spots.json i dag og for neste steg (30 spots: Troms + Lofoten/Vesterålen).
Feiler testen, må henteren pace eller dele mer FØR flere spots legges inn (ROADMAP seksjon S).

Kjør: python fetcher/test_kallregnskap.py   (ingen nett)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import kallregnskap as k  # noqa: E402

cfg = json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))
enabled = [s for s in cfg["spots"] if s.get("enabled")]
base = k.regnskap(enabled)
for r in (base, k.scaled(base, 30)):
    u = k.utnyttelse(r)
    over = {g: f"{v:.0%}" for g, v in u.items() if v > 0.5}
    assert not over, f"{r['spots']} spots: Open-Meteo over 50 % av grensen: {over}"
    print(f"{r['spots']} spots: Open-Meteo " + ", ".join(f"{g} {v:.0%}" for g, v in u.items()) + " - under 50 % - OK")
# vekten følger vilkårene: 2 uker og 15 variabler = 1,5; 4 uker = 2,0 per 10 variabler; 16 dager og 10 variabler = 16/14
assert abs(k.om_weight(15, 14) - 1.5) < 1e-9 and abs(k.om_weight(10, 28) - 2.0) < 1e-9 and abs(k.om_weight(10, 16) - 16 / 14) < 1e-9
print("Vektingen følger Open-Meteo sine eksempler - OK")
# S29 c del 1 (24.11.2026): regnskapet teller de variablene henteren faktisk ber om - GFS-kallet har vindsjø-delen
# i tillegg, standardmodellen ikke. Legger noen til en variabel i sources._marine_params(), feiler dette til
# regnskapet er oppdatert.
sys.path.insert(0, str(ROOT / "fetcher"))
import sources  # noqa: E402
n_gfs = len(sources._marine_params([0], [0], sources.OPENMETEO_SWELL_MODEL)["hourly"].split(","))
n_std = len(sources._marine_params([0], [0], None)["hourly"].split(","))
n_wind = len(sources._wind_params([0], [0])["hourly"].split(","))
assert (n_gfs, n_std, n_wind) == (k.OM_MARINE_VARS_GFS, k.OM_MARINE_VARS, k.OM_WIND_VARS), (n_gfs, n_std, n_wind)
assert sources._marine_params([0], [0], None)["forecast_days"] == k.OM_DAYS
print(f"Regnskapet teller det henteren ber om: GFS {n_gfs}, standardmodellen {n_std} og vind {n_wind} variabler, {k.OM_DAYS} dager - OK")
print("Alle tester ok")
