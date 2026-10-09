"""Regresjonstest for skiva (docs/js/map.js): hovedsvellinja (og
dens aria-tekst) skal ALLTID vise treff/bom ut fra h.directness (ren
geometrisk eksponering) - ALDRI ut fra h.bw_confirms eller
h.spot_direction_factor. 06.10.2026, Theodors rettelse (Farstadsanden 337
grader, Nordneset - se STATUS.md), meldingens tillegg punkt c: "dette er en
regresjon [...] skiva skal ALLTID tegnes fra svellet ute sin eksponering
[...] ALDRI fra bw_confirms/spot_direction_factor".

Ingen JS-testrammeverk i repoet (ikke installert: Node.js finnes ikke på
denne maskinen - se STATUS.md). To uavhengige sjekker i stedet, begge i
Python, samme stil som de andre testfilene:

1. Et EKTE uttrekk av map.js sin kildetekst (ikke en kopi) - garanterer at
   selve klassifiseringslinjene faktisk finnes og ikke nevner bw_confirms/
   spot_direction_factor. Fanger en regresjon der NOEN ANNEN linje endres.
2. En Python-port av selve formelen (samme tre terskler), kjørt mot flere
   (retning, directness, bw_confirms)-kombinasjoner. Fanger en regresjon i
   TERSKLENE selv. Porten kan i prinsippet gå ut av synk med map.js uten at
   sjekk 1 fanger det - derfor begge, ikke bare én.

Kjør: python fetcher/test_map_disc.py"""
import re
from pathlib import Path

MAP_JS = (Path(__file__).parent.parent / "docs" / "js" / "kart.js").read_text(encoding="utf-8")  # kart først (09.10.2026): skivas regel lever videre i kartmotoren

# ---------- 1. Kildetekst-sjekk ----------
# discAriaLabel() sin "miss"-variabel (skjermleser-teksten).
m_aria = re.search(r'const miss = h\.directness!=null && h\.directness < ([\d.]+);', MAP_JS)
assert m_aria, "fant ikke wedgeAriaLabel() sin miss-sjekk i kart.js - er linja endret?"
assert "bw_confirms" not in m_aria.group(0) and "spot_direction_factor" not in m_aria.group(0)
ARIA_MISS_THRESHOLD = float(m_aria.group(1))

# discSvgMarkup() sin hovedsvellinje (dn = h.directness, cls = miss/edge/treff).
m_dn = re.search(r'const dn = h\.directness;', MAP_JS)
assert m_dn, "fant ikke 'const dn = h.directness;' i discSvgMarkup() - er den endret til å lese et annet felt?"
m_cls = re.search(
    r'const cls = missing \|\| dn==null \|\| dn < ([\d.]+) \? "miss" : dn >= ([\d.]+) \? "" : "edge";', MAP_JS)
assert m_cls, ("fant ikke wedgeMarkup() sin cls-linje i forventet form - sjekk om noen har lagt "
               "bw_confirms/spot_direction_factor inn i klassifiseringen (selve regresjonen denne testen "
               "er skrevet mot, se modul-docstringen).")
assert "bw_confirms" not in m_cls.group(0) and "spot_direction_factor" not in m_cls.group(0)
MISS_THRESHOLD, FULL_THRESHOLD = float(m_cls.group(1)), float(m_cls.group(2))
print(f"1: map.js sin hovedsvellinje klassifiserer kun fra h.directness (grenser {MISS_THRESHOLD}/{FULL_THRESHOLD}, "
      f"ingen bw_confirms/spot_direction_factor i uttrykket) - OK")

# Samme grense i discAriaLabel() (skjermleser) og discSvgMarkup() (visuell) -
# en regresjon som bare retter den ene (f.eks. visningen, ikke teksten) skal
# fanges her, ikke oppdages som et snikende avvik mellom syn og skjermleser.
assert ARIA_MISS_THRESHOLD == MISS_THRESHOLD, (
    f"discAriaLabel() sin miss-grense ({ARIA_MISS_THRESHOLD}) og discSvgMarkup() sin ({MISS_THRESHOLD}) "
    f"har sprikt - skjermleser og visning vil si forskjellige ting for samme time")
print(f"2: discAriaLabel() (skjermleser) og discSvgMarkup() (visuell) bruker samme grense ({MISS_THRESHOLD}) - OK")

# Samme grense som rating.py sin egen overstyringsgrense (SPOT_DIRECTION_OVERRIDE_EXPOSURE)
# - skiva og ratingmotoren skal si det samme, med samme tall, ikke to nære
# men ulike konstanter holdt i hånd av to filer.
from rating import SPOT_DIRECTION_OVERRIDE_EXPOSURE
assert MISS_THRESHOLD == SPOT_DIRECTION_OVERRIDE_EXPOSURE, (
    f"map.js sin miss-grense ({MISS_THRESHOLD}) stemmer ikke med rating.SPOT_DIRECTION_OVERRIDE_EXPOSURE "
    f"({SPOT_DIRECTION_OVERRIDE_EXPOSURE})")
print(f"3: map.js sin miss-grense stemmer med rating.SPOT_DIRECTION_OVERRIDE_EXPOSURE ({MISS_THRESHOLD}) - OK")

# Den lille, bevisst SEPARATE pila ved sentrum (spotSwellMarkup) SKAL
# fortsatt lese spot_direction_factor - det er et annet signal (hva
# BarentsWatch selv sier ved PUNKTET), ikke en feil. Låser at den bevisste
# separasjonen faktisk består, ikke bare at hovedlinja er ren.
assert 'h.spot_direction_factor===0' in MAP_JS and 'class="disc-spot-swell' in MAP_JS, (
    "fant ikke den separate disc-spot-swell-pila (spot_direction_factor) - er den fjernet, eller har "
    "hovedlinja og den lille pila blitt slått sammen til ett signal?")
print("4: den separate BarentsWatch-ved-punktet-pila (spot_direction_factor) finnes fortsatt, uendret - OK")


# ---------- 2. Python-port av selve klassifiseringsformelen ----------
def disc_hit_class(dir_offshore, directness, bw_confirms):
    """Speiler map.js sin discSvgMarkup()-linje (se over) - bw_confirms er
    med som PARAMETER her bare for å BEVISE at den ikke brukes i uttrykket,
    aldri lest under."""
    missing = dir_offshore is None
    dn = directness
    if missing or dn is None or dn < MISS_THRESHOLD:
        return "miss"
    if dn >= FULL_THRESHOLD:
        return "hit"
    return "edge"


_cases = [
    # (dir_offshore, directness, bw_confirms, forventet) - bw_confirms
    # variert FEIL vei (True ved lav directness, False ved høy) nettopp for
    # å vise at den ikke endrer svaret.
    (338, 0.146, True, "miss"),   # den ekte hendelsen - bw_confirms var feilaktig True
    (338, 0.146, False, "miss"),  # samme directness, motsatt bw_confirms - samme klasse
    (305, 1.0, True, "hit"),
    (305, 1.0, False, "hit"),      # bw_confirms False skal IKKE gjøre et ekte treff til miss
    (300, 0.8, True, "edge"),
    (300, MISS_THRESHOLD, False, "edge"),      # strengt mindre-enn - nøyaktig på grensa er IKKE miss
    (None, None, True, "miss"),    # retning mangler
]
for dir_off, dn, bwc, expected in _cases:
    got = disc_hit_class(dir_off, dn, bwc)
    assert got == expected, f"dir={dir_off} directness={dn} bw_confirms={bwc}: forventet {expected}, fikk {got}"
print(f"5: {len(_cases)} kombinasjoner av retning/directness/bw_confirms gir riktig klasse - OK")

print("Alle tester ok")
