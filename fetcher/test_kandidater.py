"""Hemmelige spots skal aldri ligge i en fil som spores av git (Theodor 16.10.2026).

1. Ingen JSON-fil i git har et objekt med "status": "hemmelig".
2. Ingen fil i git inneholder id eller navn på en hemmelig spot. Testen kjenner dem bare som SHA-256 (samme
   lister som tools/importer_kandidater.py) og sammenligner med hashen av hvert ord i filene - så den virker
   i CI uten privat/, og uten å skrive navnene selv.
3. Finnes privat/kandidater/hemmelige.json lokalt: heller ikke koordinatene (4 desimaler) finnes i git.

Kjør: python fetcher/test_kandidater.py   (ingen nett, under 10 s)"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEMMELIG_SHA256 = {
    # utelatt fra alt (15.10.2026): id og navn
    "58e28d08733f9d5b4e0b508a6ccd6ab988b865726c756bed3c2e48ac7474e2d6",
    "2007adaed5630bd1ec35ab1211417b572bada24910b55f70bd22997eff56c27e",
    # hemmelige (16.10.2026): id-er og navn
    "ba1d1270c59cfc646104d71135cfafa674f187058bba6ba75b9adf639f3a5f1b",
    "e909f8cfab26c651456268a168823d319782afdf23afc92897de2e430369578f",
    "dd170ec624305a0d560682111e40f417b5a90a8d67c15c17fff1de6d6a00f022",
}
SKIP_SUFFIX = {".png", ".jpg", ".woff2", ".pmtiles", ".ico", ".pdf", ".xlsx", ".gz", ".zip"}

files = [ROOT / f for f in subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.splitlines()]
files = [f for f in files if f.is_file() and f.suffix.lower() not in SKIP_SUFFIX]


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


bad_status, bad_name = [], []
for f in files:
    try:
        text = f.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    if f.suffix == ".json":
        try:
            if any(o.get("status") == "hemmelig" for o in walk(json.loads(text))):
                bad_status.append(str(f.relative_to(ROOT)))
        except ValueError:
            pass
    low = text.lower()
    toks = set(re.findall(r"[a-zæøå0-9][a-zæøå0-9-]*", low)) | set(re.findall(r"[a-zæøå]+ \([a-zæøå]+\)", low))
    if any(hashlib.sha256(t.encode("utf-8")).hexdigest() in HEMMELIG_SHA256 for t in toks):
        bad_name.append(str(f.relative_to(ROOT)))
assert not bad_status, f"spots med status «hemmelig» i filer som spores av git: {bad_status}"
assert not bad_name, f"id eller navn på en hemmelig spot i filer som spores av git: {bad_name}"
print(f"1-2: {len(files)} filer i git - ingen status «hemmelig», ingen id/navn på hemmelige spots - OK")

priv = ROOT / "privat" / "kandidater" / "hemmelige.json"
if priv.exists():
    # kontrollør 16.10: også korte skrivemåter (tallene som i kilden, uten etterfølgende nuller)
    coords = [(repr(float(k["pin_liste"]["lat"])), repr(float(k["pin_liste"]["lon"]))) for k in json.loads(priv.read_text(encoding="utf-8"))["kandidater"]]
    hits = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for la, lo in coords:
            # lat og lon nær hverandre (innen 80 tegn), med eller uten flere desimaler bak
            if re.search(rf"(?<![\d.]){re.escape(la)}\d*\D.{{0,80}}?(?<![\d.]){re.escape(lo)}\d*\b", text, re.S):
                hits.append(str(f.relative_to(ROOT)))
    assert not hits, f"koordinatene til en hemmelig spot står i filer som spores av git: {sorted(set(hits))}"
    print(f"3: koordinatene til {len(coords)} hemmelige spots finnes ikke i git - OK")
else:
    print("3: privat/kandidater/hemmelige.json finnes ikke her (CI) - koordinatsjekken hoppes over")
print("Alle tester ok")
