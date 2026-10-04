"""Holder docs/sw.js sin cache-versjon i takt med innholdet i docs/ (utenom
docs/data/, som alltid hentes ferskt uansett, se sw.js). Løser at CACHE
tidligere måtte bumpes for hånd og ble glemt (26.09.2026 til 03.10.2026,
9 commits med PWA-endringer uten at installerte PWA-er oppdaget noe - se
STATUS.md). Versjonen er en hash av filene, ikke en manuelt telt streng -
den kan derfor aldri bli glemt, bare oppdaget som utdatert.

Kjør uten flagg for å RETTE sw.js (skriver ny versjon hvis den er utdatert).
Kjør med --check for å bare SJEKKE (feiler med exit 1, endrer ingenting) -
det er dette fetcher/test_docs_cache.py gjør før hver commit, se CLAUDE.md
sin arbeidsmåte.
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SW = DOCS / "sw.js"
CACHE_RE = re.compile(r'const CACHE = "nordsurf-([0-9a-f]+)";')
# Matcher ALT etter "nordsurf-" (ikke bare hex) - fanger opp den gamle,
# manuelt tellede "v9"-stilen også, så overgangen til hash kan gjøres i ett
# steg av dette scriptet selv, uten en manuell mellomrunde.
CACHE_ANY_RE = re.compile(r'const CACHE = "nordsurf-[^"]*";')


def docs_hash():
    """Sha256 (korttrunkert) av navn og innhold for alle filer i docs/,
    utenom docs/data/ (ferske varseldata, uendret av PWA-shell-cachen) og
    sw.js selv (ville vært sirkulært - fila kan ikke hashe sin egen verdi)."""
    h = hashlib.sha256()
    files = [
        p.relative_to(DOCS) for p in DOCS.rglob("*")
        if p.is_file() and p.relative_to(DOCS).parts[0] != "data" and p.name != "sw.js"
    ]
    for rel in sorted(files, key=str):
        h.update(str(rel).encode("utf-8"))
        h.update((DOCS / rel).read_bytes())
    return h.hexdigest()[:12]


def current_version(text):
    m = CACHE_RE.search(text)
    return m.group(1) if m else None


def main():
    check_only = "--check" in sys.argv
    text = SW.read_text(encoding="utf-8")
    want = docs_hash()
    have = current_version(text)
    if have == want:
        print(f"docs/sw.js sin cache-versjon stemmer med docs/ sitt innhold ({want})")
        return 0
    if check_only:
        print(f"docs/sw.js sin cache-versjon er UTDATERT: har {have}, docs/ hasher nå til {want}.\n"
              f"Kjør 'python fetcher/update_sw_cache.py' (uten --check) og commit resultatet.")
        return 1
    new_text, n = CACHE_ANY_RE.subn(f'const CACHE = "nordsurf-{want}";', text, count=1)
    if n == 0:
        print("Fant ikke CACHE-linjen i docs/sw.js - sjekk at formatet er "
              '`const CACHE = "nordsurf-<noe>";`.', file=sys.stderr)
        return 1
    SW.write_text(new_text, encoding="utf-8")
    print(f"Oppdaterte docs/sw.js sin cache-versjon: {have} -> {want}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
