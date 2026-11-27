"""Nettlesertest for søk, Utforsk og spotsiden, PC (1440x900, lys og mørk) og tilleggene.

Kjører hele løkka per bredde i spotside_felles.kjor() for PC, med ordtabellene og svellvinduet (punkt 13 og 14), og
delene etter løkka som kjøres én gang: svak vind (S21/S24/S26), S28 «Om spotten», skjemafeltene i WebKit (hoppes over der
WebKit ikke er installert, som i CI) og tools/kontrast.py. Mobil kjøres av test_spotside_mobil_browser.py.

Påstandene står i fetcher/spotside_felles.py (kjor()), som også har beskrivelsen av hva som sjekkes. Denne fila eier
bare utvalget og tidsgrensa. Skjermbilder: docs/design/spotside/etter/*_pc_*.png.

Tidsgrenser (CLAUDE.md): hvert Playwright-steg maks 15 s, hele fila maks GRENSE_S sekunder (hardkill, exit 124),
testserveren stoppes uansett utfall. Målt 27.11.2026 lokalt: 93-103 s (se STATUS.md). Ikke målt i CI ennå: OK-linja skriver sekundene, og grensa skal
ha minst 40 % margin over det CI faktisk bruker. Nærmer fila seg grensa, deles eller forenkles den - grensa heves ikke.
Trenger: pip install playwright && playwright install chromium.
Kjør: python fetcher/test_spotside_pc_browser.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spotside_felles  # noqa: E402

GRENSE_S = 240

if __name__ == "__main__":
    spotside_felles.kjor(Path(__file__).name, GRENSE_S, bredder=(spotside_felles.PC,), tillegg=True)
