"""06.10.2026, Theodors rettelse (Farstadsanden 337 grader, Nordneset - se
STATUS.md): ekte nettleser-tester for skiva, med Playwright for Python (ikke
Node - se README/STATUS.md for hvorfor). Åpner den faktiske docs/index.html
i Chromium, med en fast, hardkodet testfil for forecast.json
(window.__FORECAST__ - samme hook appen selv bruker til "oppdiktet vær",
se DATA = window.__FORECAST__ || fetch(...) i docs/index.html), og sjekker:

1. Skiva (kartet): svell ute med eksponering under 0,667 gir grå, stiplet
   linje UTEN strøm-animasjon, OGSÅ når bw_confirms er sann (selve
   regresjonen Theodor meldte). Eksponering 1,0 gir farget, heltrukket,
   ANIMERT linje.
2. "Retningstreff" (detaljsiden), ordet for lav rating (samme side) og
   kartmerket (før skiva åpnes - markøren skjules mens skiva vises, se
   map.js sin renderMarkers()) sier det samme som skiva for SAMME time.
3. Skjermbilder i mobilvisning, lagret til fetcher/test_screenshots/ (se
   .gitignore - ikke committet, regenereres hver kjøring).

Trenger: pip install playwright && playwright install chromium (kjørt én
gang, se README). Kjør: python fetcher/test_disc_browser.py"""
import http.server
import json
import socket
import threading
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
SHOT_DIR = Path(__file__).parent / "test_screenshots"
SHOT_DIR.mkdir(exist_ok=True)

# ---------- Fast testfil for forecast.json ----------
# Begge timer er basert på et EKTE hour-objekt fra rate()/fetch.py (samme
# felt, samme typer) - bare de feltene som er relevante for denne testen er
# overstyrt per scenario (se kommentarene). Én spot (Farstadsanden) er nok,
# og gjør markør-søk trivielt (ingen klynging å skille fra - se
# map.js sin computeGroups()).
HOUR_BASE = {
    "height_offshore": 2.0, "height_spot_model": 1.6, "swell_offshore": 1.5,
    "swell_model": "standard", "secondary_swell_height": None, "secondary_swell_dir": None,
    "secondary_swell_period": None, "bw_period": 10.0, "bw_interpolated": False,
    "bw_height_max": 1.4, "bw_source": "norce", "bw_file_source": "hustadvika3x2v",
    "bw_dir_raw": 130.0, "bw_height_near": 0.75, "turn": None, "period": 11.0,
    "water_temp": 10.0, "wind_speed": 5.0, "wind_dir": 130.0, "gust": 7.0, "air_temp": 9.0,
    "wind_interpolated": False, "light": "dag", "daylight": True,
    "tide": {"level": 1.0, "state": "middels", "rising": True},
    "faded": 0, "faded_wind": 0, "faded_tide": 0, "wind_type": "offshore",
    "height": 0.75, "height_source": "barentswatch", "surf_height_sets": 1.0,
    "breaking_height": 0.6, "surf_factor": 1.0, "transfer": 0.6, "uncertain": False,
    "breakdown": ["Test-time, se fetcher/test_disc_browser.py"],
    "sources_disagree_reason": None, "swell_share": 0.9,
    "spot_direction_diff": 0, "spot_direction_offshore": False,
    "spot_direction_overridden": False, "likely_flat": False, "blown_out": False,
}

# Scenario 1 ("miss"): Farstadsanden 338 grader, BarentsWatch 1,0 m rett inn.
# directness/bw_confirms/low_reason/stars er de EKTE tallene rate() gir etter
# rettelsen (se fetcher/test_rating.py post 20.3) - bw_confirms satt til
# True her for å bevise at frontend IKKE stoler på det feltet alene (selve
# regresjonen Theodor meldte gikk nettopp via bw_confirms).
HOUR_MISS = {**HOUR_BASE, "t": "2026-10-06T15:00Z", "dir_offshore": 338,
             "bw_height": 1.0, "bw_dir": 310.0, "directness": 0.146,
             "spot_direction_factor": 1.0, "bw_confirms": True,
             "sources_disagree": True,
             "sources_disagree_reason": ("Kildene er uenige. BarentsWatch viser 1,0 m, men svellet ute "
                                          "krysser Nordneset (338°, utenfor vinduet). Trolig ikke surfbart. "
                                          "Logg gjerne hva du ser."),
             "stars": 0, "surf_height": 0.0, "low_reason": "treffer_ikke"}

# Scenario 2 ("hit"): midt i vinduet (305 grader), IDEALISERT fullt åpen
# eksponering (1,0) - positiv kontroll for den "rene treff"-klassen
# (dn>=0.999, se map.js). 06.10.2026, fysikk-kontrollør sitt funn: en ekte
# rate()-kjøring for 305 grader ved Farstadsanden gir smoothed eksponering
# 0,974, ikke 1,0 (glattingen - sigma 10 grader - bløder alltid noe inn fra
# Nordneset sin skygge 23 grader unna, se STATUS.md) - 0,974 ville faktisk
# klassifisert som "edge", ikke et rent treff. 1,0 her er derfor en bevisst
# idealisert verdi (tester selve "rent treff"-koden), IKKE noe Farstadsanden
# kan vise i produksjon for NOEN retning - se HOUR_EDGE under for den
# realistiske, faktiske kurveverdien i kantsonen i stedet.
HOUR_HIT = {**HOUR_BASE, "t": "2026-10-06T18:00Z", "dir_offshore": 305,
            "bw_height": 1.0, "bw_dir": 310.0, "directness": 1.0,
            "spot_direction_factor": 1.0, "bw_confirms": True,
            "sources_disagree": False, "stars": 3, "surf_height": 1.1,
            "low_reason": None}

# Scenario 3 ("edge"): 320 grader, EKTE smoothed eksponering fra
# data/exposure_baseline.json (0,774 - lest derfra, ikke gjettet) - dekker
# skivas tredje, mellomste klasse (0,667 <= dn < 0,999 -> "edge") i
# nettleseren også, ikke bare i test_map_disc.py sin formel-port.
HOUR_EDGE = {**HOUR_BASE, "t": "2026-10-06T21:00Z", "dir_offshore": 320,
             "bw_height": 0.9, "bw_dir": 310.0, "directness": 0.774,
             "spot_direction_factor": 1.0, "bw_confirms": True,
             "sources_disagree": False, "stars": 2, "surf_height": 0.9,
             "low_reason": None}

SPOT = {
    "id": "farstadsanden", "name": "Farstadsanden", "area": "Hustadvika", "enabled": True,
    "spot": {"lat": 62.983474, "lon": 7.152127}, "offshore": {"lat": 63.0602, "lon": 6.9843},
    "barentswatch_point": {"lat": 62.985072, "lon": 7.148631},
    "barentswatch_point_near": {"lat": 62.984433, "lon": 7.15003},
    "swell_window": [284, 326], "offshore_wind": [85, 175], "min_period": 8,
    "ideal_height": [1.0, 3.0], "max_height": 4.5, "facing": 310,
    "transfer": 0.6, "surf_factor": 1.0, "tide_events": [], "bw_until": "2026-10-08T18:00Z",
    "calibration": {"logs": 0, "surf_factor_logs": 0, "transfer_logs": None, "transfer_bw": None,
                    "bw_pairs": 0, "bw_days": 0, "transfer_used": 0.6, "transfer_source": "standard",
                    "surf_factor_used": 1.0, "surf_factor_source": "standard",
                    "surf_factor_prior_n": None, "exposure_pairs": 0,
                    "exposure_buckets_learned_lang": 0, "exposure_buckets_learned_kort": 0,
                    "exposure_override_suggestions": [], "exposure_curve": []},
    "light_days": {"2026-10-06": {"start": "2026-10-06T05:10:00+00:00",
                                   "end": "2026-10-06T17:30:00+00:00", "sun": True}},
    "hours": [HOUR_MISS, HOUR_HIT, HOUR_EDGE],
}
FIXTURE = {"generated": "2026-10-06T15:00:00+00:00", "spots": [SPOT], "notify": {"min_stars": 3, "hours_ahead": 36, "spots": []}}


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server():
    """Samme fremgangsmåte som den tidligere brukte serve_docs.py i denne
    økten: python3 -m http.server krasjer i dette sandkasse-miljøet
    (PermissionError på os.getcwd() inni argparse) - unngås helt ved å
    instansiere ThreadingHTTPServer/SimpleHTTPRequestHandler direkte."""
    port = _free_port()
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def hit_class(markup):
    import re
    m = re.search(r'<line class="disc-swell ?([a-z]*)"', markup)
    return m.group(1) if m else None


def crests_class(markup):
    import re
    m = re.search(r'<g class="disc-crests ?([a-z]*)"', markup)
    return m.group(1) if m else None


def main():
    server, port = _start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            device = p.devices["iPhone 13"]
            context = browser.new_context(**device)
            page = context.new_page()
            page.add_init_script(f"window.__FORECAST__ = {json.dumps(FIXTURE)};")
            # Undertrykk "forklar kartet"-boblen (map.js sin
            # maybeShowExplainAuto()) - den dekker skiva på skjermbildet
            # ellers, uten å påvirke selve testen (den styrer bare om
            # boblen vises, ikke noe disc-logikken leser).
            page.add_init_script("try{localStorage.setItem('nordsurf.mapExplainSeen.v1','1');}catch(e){}")
            page.goto(f"http://127.0.0.1:{port}/index.html")
            # DATA/state/render/STAR_WORDS/LOW_REASON_WORD er toppnivå let/
            # const/function i hovedskriptet (ikke en IIFE, i motsetning til
            # map.js) - de blir ALDRI egenskaper på window (bare var/function
            # ville blitt det), men er fortsatt vanlige, synlige navn i
            # samme skript-scope, og dermed lesbare/kallbare direkte fra
            # page.evaluate() (samme realm). "window.DATA" ville alltid vært
            # undefined - ikke bruk window.-prefiks for disse.
            page.wait_for_function("typeof DATA !== 'undefined' && DATA != null")

            star_words = page.evaluate("STAR_WORDS")
            low_words = page.evaluate("LOW_REASON_WORD")

            def check_scenario(idx, hour, label):
                # ---------- 1. Detaljsiden: Retningstreff + lavstjerne-ordet ----------
                page.evaluate(f"state.tab='varsel'; state.spot=0; state.sel={idx}; render();")
                verdict = page.locator(".verdict").inner_text()
                retningstreff = page.locator('.cell:has-text("Retningstreff") >> .v').inner_text()
                expected_pct = f"{round(hour['directness'] * 100)} %"
                assert retningstreff == expected_pct, (
                    f"{label}: Retningstreff viste '{retningstreff}', forventet '{expected_pct}'")
                expected_word = low_words[hour["low_reason"]] if hour["low_reason"] else star_words[hour["stars"]]
                if hour["low_reason"]:
                    assert verdict.startswith(expected_word), (
                        f"{label}: forsidens ord var '{verdict}', forventet å starte med '{expected_word}'")
                print(f"{label}: detaljside - Retningstreff {retningstreff}, ordet '{expected_word}' - OK")

                # ---------- 2. Kartet: merket (FØR skiva åpnes) ----------
                page.evaluate("state.tab='kart'; state.spot=null; render();")
                # Avvelg forrige scenarios valgte spot på KARTET - map.js sin
                # EGEN mapState.spotId (ikke appens state.spot over, en annen
                # variabel) er ikke nullstilt av dette alene, og en valgt
                # spot sitt eget merke er skjult mens skiva vises (se
                # renderMarkers() sin "isSelected: continue"). Et klikk på
                # tomt kart (onMapBackgroundClick) avvelger ekte, uansett
                # hvilken spot som var valgt.
                page.wait_for_selector(".leaflet-container")
                page.locator(".leaflet-container").click(position={"x": 5, "y": 5})
                page.wait_for_selector(".spot-mark")
                slider = page.locator("#mapSlider")
                slider.evaluate(f"el => {{ el.value={idx}; el.dispatchEvent(new Event('input', {{bubbles:true}})); }}")
                marker = page.locator(".spot-mark")
                marker_label = marker.get_attribute("aria-label")
                if hour["low_reason"]:
                    # heightText() (map.js) viser low_reason-ORDET i stedet
                    # for en høyde når det er satt - samme ord som verdict.
                    assert expected_word in marker_label, (
                        f"{label}: kartmerket sa '{marker_label}', forventet ordet '{expected_word}' i det")
                else:
                    # Uten low_reason viser heightText() en ekte høyde i
                    # meter, ALDRI et lavstjerne-ord - det er den riktige
                    # konsistensen her (samme funksjon, samme felt som
                    # verdict ville brukt OM low_reason hadde vært satt).
                    assert "m" in marker_label and not any(w in marker_label for w in low_words.values()), (
                        f"{label}: kartmerket sa '{marker_label}', forventet en ekte høyde, ikke et lavstjerne-ord")
                print(f"{label}: kartmerket - '{marker_label}' - OK")

                # ---------- 3. Skiva ----------
                # Tre klasser, samme grenser som map.js (og test_map_disc.py
                # sin formel-port): miss (dn<0,667), edge (0,667<=dn<0,999),
                # rent treff (dn>=0,999, tom klasse) - IKKE en binær hit/miss-
                # sjekk, ellers ville HOUR_EDGE (0,774) feilaktig blitt
                # forventet som et rent treff.
                dn = hour["directness"]
                expected_class = "miss" if dn < 0.667 else ("edge" if dn < 0.999 else "")
                marker.click()
                page.wait_for_selector(".disc-wrap")
                disc_html = page.locator(".disc-wrap").inner_html()
                hc, cc = hit_class(disc_html), crests_class(disc_html)
                assert hc == expected_class and cc == expected_class, (
                    f"{label}: forventet klasse '{expected_class}' (directness {dn}), fikk linje='{hc}' crests='{cc}'")
                if expected_class == "miss":
                    assert "disc-miss-label" in disc_html, f"{label}: mangler 'Treffer ikke'-etikett ved miss"
                else:
                    assert "disc-miss-label" not in disc_html, f"{label}: fant 'Treffer ikke'-etikett ved et ekte treff/kantsone"
                print(f"{label}: skiva - linje='{hc}' crests='{cc}' (directness {dn}, "
                      f"bw_confirms {hour['bw_confirms']}) - OK")

                page.wait_for_timeout(700)  # la disc-enter/strøm-animasjonen roe seg før skjermbildet
                page.screenshot(path=str(SHOT_DIR / f"disc_{label}.png"))

            check_scenario(0, HOUR_MISS, "miss_338grader")
            check_scenario(1, HOUR_HIT, "hit_305grader")
            check_scenario(2, HOUR_EDGE, "edge_320grader")

            browser.close()
    finally:
        server.shutdown()

    print(f"Skjermbilder lagret i {SHOT_DIR}")
    print("Alle tester ok")


if __name__ == "__main__":
    main()
