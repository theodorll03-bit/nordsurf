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
print("Alle tester ok")
