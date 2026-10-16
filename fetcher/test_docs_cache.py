"""Sjekker at docs/sw.js sin cache-versjon faktisk stemmer med innholdet i
docs/ (utenom docs/data/, som alltid hentes ferskt uansett - se sw.js).

26.09.2026 til 03.10.2026: ni commits endret docs/index.html/docs/js/map.js/
docs/css/map.css uten at CACHE i docs/sw.js ble bumpet - installerte PWA-er
oppdaget derfor ikke at noe hadde endret seg, og serverte en gammel, cachet
kopi av appen i flere dager (se STATUS.md). CACHE er nå en hash av docs/
sitt innhold i stedet for en manuelt telt streng (se update_sw_cache.py),
så den kan ikke lenger glemmes - bare oppdages som utdatert, her.

Kjør: python fetcher/update_sw_cache.py (ikke denne fila) for å RETTE en
utdatert versjon. Kjør: python fetcher/test_docs_cache.py for å bare sjekke."""
from update_sw_cache import docs_hash, current_version, SW

want = docs_hash()
have = current_version(SW.read_text(encoding="utf-8"))
assert have == want, (
    f"docs/sw.js sin cache-versjon ({have}) stemmer ikke med docs/ sitt "
    f"innhold ({want}) - kjør 'python fetcher/update_sw_cache.py' og "
    f"commit resultatet sammen med de andre docs/-endringene."
)
print(f"docs/sw.js sin cache-versjon stemmer med docs/ sitt innhold ({want})")

# S3 (16.10.2026): alle filene i SHELL må finnes - ellers feiler cache.addAll() i install, og en ny
# sw.js blir aldri tatt i bruk (listen hadde css/kart.css og js/front.js, som ikke fantes).
import json, re  # noqa: E402
sw = SW.read_text(encoding="utf-8")
shell = json.loads("[" + re.search(r"const SHELL = \[(.*?)\];", sw, re.S).group(1).replace("\n", " ") + "]")
missing = [f for f in shell if f != "./" and not (SW.parent / f).is_file()]
assert not missing, f"sw.js sin SHELL har filer som ikke finnes i docs/: {missing}"
print(f"Alle {len(shell)} filene i sw.js sin SHELL finnes")

# 16.10.2026 (PR #17): en endring bare i sw.js (SHELL-lista, logikk) skal også gi nytt CACHE-navn,
# ellers kan en ny service worker gjenbruke det gamle lageret; CACHE-linja selv påvirker ikke hashen.
import os, re, update_sw_cache as u   # noqa: E401,E402
orig = SW.read_text(encoding="utf-8")
try:
    SW.write_text(orig.replace('"index.html",', '"index.html", "ny-fil.js",', 1), encoding="utf-8")
    changed = docs_hash()
    SW.write_text(u.CACHE_ANY_RE.sub('const CACHE = "nordsurf-000000000000";', orig), encoding="utf-8")
    same = docs_hash()
finally:
    SW.write_text(orig, encoding="utf-8")
assert changed != want, "en SHELL-endring i sw.js ga samme CACHE-navn"
assert same == want, "CACHE-linja selv påvirker hashen (sirkulært)"
print("SHELL-endring gir nytt CACHE-navn, CACHE-linja er nøytral - OK")
# 16.10.2026: forecast.yml kjørte fetcher/test_map_disc.py etter at fila ble pensjonert (PR #7, 15.10) -
# «Hent varsel» feilet fra 15.10 kl. 19Z til 16.10 uten nytt varsel. Alle skript workflowene kjører må finnes.
import pathlib, re as _re   # noqa: E402,E401
_root = SW.parent.parent
_mangler = []
for _wf in sorted((_root / ".github" / "workflows").glob("*.yml")):
    for _f in _re.findall(r"python3? ((?:fetcher|tools)/[\w./-]+\.py)", _wf.read_text(encoding="utf-8")):
        if not (_root / _f).exists():
            _mangler.append(f"{_wf.name}: {_f}")
assert not _mangler, f"workflows kjører skript som ikke finnes: {_mangler}"
print("Alle skript workflowene kjører finnes - OK")
print("Alle tester ok")
