"""Designrunde 1 (09.10.2026), Theodors regel 2: BARE visning. Denne testen
bekrefter at ingenting som lager tallene er endret på designgrenen:

1. Filene som regner ratingen og henter data (fetcher/rating.py, fetch.py,
   sources.py, calibrate.py, exposure_learn.py, exposure.py, longrange.py,
   tide.py, sun.py, notify.py) og spots.json er BYTE FOR BYTE like filene på
   main (origin/main, eller main lokalt). Går main videre mens grenen lever,
   er det main-versjonen som gjelder - testen sammenligner alltid mot den
   nyeste main den finner.
2. docs/data/forecast.json er ikke rørt av designgrenen: fila er lik main
   sin (henteren skriver den, aldri designarbeidet).
3. Tallene i ratingen er uendret: alle faste observasjoner (test_rating.py)
   gir samme stjerner og surfehøyde som før - kjøres som en del av den
   vanlige testkjøringen, men sjekkes her én gang til mot en fast tabell.

Kjør: python fetcher/test_display_only.py   (ingen nett, under 10 s)."""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))

RATING_FILES = ["fetcher/rating.py", "fetcher/fetch.py", "fetcher/sources.py", "fetcher/calibrate.py", "fetcher/exposure_learn.py",
                "fetcher/exposure.py", "fetcher/longrange.py", "fetcher/tide.py", "fetcher/sun.py", "fetcher/notify.py", "spots.json"]
DATA_FILES = ["docs/data/forecast.json"]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)


def main_ref():
    for ref in ("origin/main", "main"):
        if git("rev-parse", "--verify", ref).returncode == 0:
            return ref
    return None


def sha_ref(ref, path):
    r = git("show", f"{ref}:{path}")
    return hashlib.sha256(r.stdout.encode("utf-8")).hexdigest() if r.returncode == 0 else None


def sha_file(path):
    p = ROOT / path
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


ref = main_ref()
assert ref, "fant ikke main (origin/main eller main) å sammenligne mot"
head = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
if head == "main":
    print(f"1-2: står på main selv ({ref}) - ingenting å sammenligne, hopper over hash-sjekken")
else:
    bad = []
    for path in RATING_FILES + DATA_FILES:
        a, b = sha_file(path), sha_ref(ref, path)
        if a != b:
            bad.append(path)
    assert not bad, f"designgrenen har endret filer som lager tallene (skal være like {ref}): {bad}"
    print(f"1-2: {len(RATING_FILES)} rating-/hentefiler og {len(DATA_FILES)} datafil(er) er byte for byte like {ref}")

# 3: faste observasjoner gir samme tall som før (fast tabell, uavhengig av test_rating.py)
import backtest  # noqa: E402
cases, results, _ = backtest.run(["grunnlinje"], logs=[])
rows = {x["case"]["id"]: (x["r"]["stars"], x["r"]["surf_height"]) for x in results["grunnlinje"]["rows"]}
EXPECTED = {
    "grotfjord_2409_metno": (0, 0.0), "grotfjord_2409_bw": (0, 0.0), "grotfjord_2409_windy": (0, 0.1), "grotfjord_2509": (0, 0.0),
    "grotfjord_2609": (0, 0.0), "lenangsoyra_2609": (0, 0.0), "unstad_2609": (4, 2.42), "unstad_2709_06": (3, 1.48),
    "unstad_2709_07": (3, 1.34), "unstad_2709_08": (4, 1.49), "unstad_2809_12": (3, 1.21), "unstad_2809_13": (3, 1.17),
    "unstad_2809_14": (3, 1.15), "unstad_2809_15": (3, 1.11), "farstadsanden_338": (0, 1.28),
}
diff = {k: (rows.get(k), v) for k, v in EXPECTED.items() if rows.get(k) is None or rows[k][0] != v[0] or abs((rows[k][1] or 0) - v[1]) > 0.005}
assert not diff, f"stjerner/surfehøyde har endret seg for faste observasjoner: {diff}"
print(f"3: {len(EXPECTED)} faste observasjoner gir samme stjerner og surfehøyde som før")
print("Alle tester ok")
