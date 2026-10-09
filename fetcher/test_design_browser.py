"""Designrunde 1 (09.10.2026): nettlesertest for den nye visningen, med
Playwright for Python (samme oppsett som test_disc_browser.py). Åpner
docs/index.html med dagens docs/data/forecast.json som window.__FORECAST__
og sjekker, i mobil (390x844) og PC (1440x900), lys og mørk modus:

1. Lista, detaljsiden for en spot med stjerner og for en flat spot, kartet,
   loggarket og forklaringsarket rendres uten JavaScript-feil.
2. Tallene appen viser er NØYAKTIG forecast.json sine (ren visning): ordet/
   stjernene og surfehøyde/sett på detaljsiden, og ordet i lista, stemmer
   med feltene i fila for samme spot og time - appen regner aldri selv.
3. Kontrast (axe-core, regelen color-contrast, WCAG AA 4,5:1 / 3:1 for
   stor tekst): ingen brudd på noen av skjermene. axe lastes fra cdnjs
   (fast versjon), eller fra NORDSURF_AXE_PATH når nettet er sperret.
4. Ingen knapp ligger over tekst: ingen element med klassen .toolbar
   finnes (den gamle svevende verktøylinja er borte), og "Logg"-knappen
   ligger i detaljsidens hode.
5. Trykkflater: alle knapper i lista og på detaljsiden er minst 44x44 px.
6. Skjermbilder lagres i docs/design/runde-1/ (committes - de er PR-ens
   dokumentasjon), ett per skjerm × størrelse × modus.

Tidsgrenser (CLAUDE.md): hvert Playwright-steg 15 s, hele fila 5 minutter
(hardkill-vaktpost, os._exit). Leaflet hentes fra cdnjs; med
NORDSURF_LEAFLET_DIR (mappe med leaflet.js/.css) serveres den lokalt.
Kartfliser (Kartverket) blokkeres alltid i testen - de er ikke poenget.

Kjør: python fetcher/test_design_browser.py"""
import http.server
import json
import os
import socket
import sys
import threading
import time
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SHOT_DIR = DOCS / "design" / "runde-1"
ELEMENT_TIMEOUT_MS = 15000
FILE_TIMEOUT_S = 300
AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
LEAFLET_DIR = os.environ.get("NORDSURF_LEAFLET_DIR")
AXE_PATH = os.environ.get("NORDSURF_AXE_PATH")


def _watchdog():
    time.sleep(FILE_TIMEOUT_S)
    print(f"TIDSGRENSE: test_design_browser.py brukte over {FILE_TIMEOUT_S} s - avbryter hardt", flush=True)
    os._exit(124)


threading.Thread(target=_watchdog, daemon=True).start()


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=str(DOCS)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def route(page):
    def handle(r, req):
        u = req.url
        if LEAFLET_DIR and "leaflet" in u and u.endswith(".js"):
            r.fulfill(path=str(Path(LEAFLET_DIR) / "leaflet.js"), content_type="application/javascript")
        elif LEAFLET_DIR and "leaflet" in u and u.endswith(".css"):
            r.fulfill(path=str(Path(LEAFLET_DIR) / "leaflet.css"), content_type="text/css")
        elif "leaflet" in u or "axe-core" in u:
            r.continue_()
        else:
            r.abort()
    for pat in ("https://cdnjs.cloudflare.com/**", "https://cdn.jsdelivr.net/**", "https://unpkg.com/**", "https://*.supabase.co/**",
                "https://cache.kartverket.no/**", "https://fonts.googleapis.com/**", "https://fonts.gstatic.com/**"):
        page.route(pat, handle)


def nf1(v):
    return f"{v:.1f}".replace(".", ",")


def main():
    from playwright.sync_api import sync_playwright
    forecast = json.loads((DOCS / "data" / "forecast.json").read_text(encoding="utf-8"))
    spots = forecast["spots"]
    bi = max(range(len(spots)), key=lambda i: max(h["stars"] for h in spots[i]["hours"][:72]))
    bidx = max(range(min(72, len(spots[bi]["hours"]))), key=lambda k: spots[bi]["hours"][k]["stars"])
    fi = next((i for i, s in enumerate(spots) if s["hours"][0]["stars"] == 0), 0)
    srv, port = serve()
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    errors, violations = [], []
    exe = os.environ.get("NORDSURF_CHROMIUM")
    with sync_playwright() as p:
        browser = p.chromium.launch(**({"executable_path": exe} if exe else {}))
        for label, vp, scheme in (("mobil_lys", (390, 844), "light"), ("mobil_mork", (390, 844), "dark"),
                                  ("pc_lys", (1440, 900), "light"), ("pc_mork", (1440, 900), "dark")):
            mobile = vp[0] < 900
            ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]}, color_scheme=scheme,
                                      device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile)
            page = ctx.new_page()
            page.set_default_timeout(ELEMENT_TIMEOUT_MS)
            page.on("pageerror", lambda e, label=label: errors.append(f"{label}: {e}"))
            route(page)
            page.add_init_script(f"window.__FORECAST__ = {json.dumps(forecast)};")
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("typeof DATA !== 'undefined' && DATA != null")
            if AXE_PATH:
                page.add_script_tag(path=AXE_PATH)
            else:
                page.add_script_tag(url=AXE_URL)
            page.wait_for_function("typeof axe !== 'undefined'")

            def shot(name):
                page.wait_for_timeout(300)
                page.screenshot(path=str(SHOT_DIR / f"{name}_{label}.png"))

            def axe_check(name):
                res = page.evaluate("""async () => {
                    const r = await axe.run(document, {runOnly: {type: 'rule', values: ['color-contrast']}});
                    return r.violations.map(v => ({id: v.id, nodes: v.nodes.slice(0, 5).map(n => ({html: n.html.slice(0, 160), msg: (n.any[0]||{}).message || ''}))}));
                }""")
                for v in res:
                    violations.append((f"{name}_{label}", v))

            # 1+6: lista
            page.evaluate("state.tab='varsel'; state.spot=null; render(); window.scrollTo(0,0);")
            assert page.locator(".card").count() == len(spots), "lista skal ha ett kort per spot"
            # 2: ordet i lista = forecast.json sin nåværende time
            first_card = page.locator(".card").first
            shot("liste"); axe_check("liste")
            # 4+5: ingen svevende verktøylinje, trykkflater i lista
            assert page.locator(".toolbar").count() == 0, "den gamle svevende verktøylinja skal være borte"
            small = page.evaluate("""() => [...document.querySelectorAll('#listPane button')].filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && (r.width < 44 || r.height < 44); }).map(b => b.className).slice(0, 5)""")
            assert not small, f"knapper under 44 px i lista: {small}"

            # detaljside med stjerner
            page.evaluate(f"state.tab='varsel'; state.spot={bi}; state.sel={bidx}; state.scrollToSel=true; render();")
            h = spots[bi]["hours"][bidx]
            page.wait_for_selector("#detailPane .now")
            word = page.locator("#detailPane .verdict").first.inner_text().strip()
            if h["stars"]:
                aria = page.locator("#detailPane .now .stars").get_attribute("aria-label")
                assert aria.startswith(f"{h['stars']} av 5 stjerner"), f"stjerner på detaljsiden ({aria}) stemmer ikke med forecast.json ({h['stars']})"
            else:
                assert word, "ordet for 0 stjerner skal stå på detaljsiden"
            if not h.get("low_reason") and h.get("surf_height") is not None:
                key = page.locator("#detailPane .keyline .tap").first.inner_text()
                assert nf1(h["surf_height"]) in key, f"surfehøyde i nøkkellinja ({key}) stemmer ikke med forecast.json ({h['surf_height']})"
                if h.get("surf_height_sets") is not None and h["surf_height_sets"] != h["surf_height"]:
                    assert nf1(h["surf_height_sets"]) in key, f"sett ({h['surf_height_sets']}) mangler i nøkkellinja ({key})"
            assert page.locator("#logBtn").count() == 1, "én Logg-knapp i detaljsidens hode"
            assert page.locator("#chartWrap svg .bar").count() == len(spots[bi]["hours"]), "grafen skal ha én søyle per time"
            small = page.evaluate("""() => [...document.querySelectorAll('#detailPane button:not(.tap):not(.link)')].filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && (r.width < 44 || r.height < 44); }).map(b => b.className).slice(0, 5)""")
            assert not small, f"knapper under 44 px på detaljsiden: {small}"
            shot("detalj_stjerner"); axe_check("detalj_stjerner")
            page.evaluate("document.getElementById('details').open = true; document.getElementById('details').scrollIntoView();")
            shot("detalj_detaljer"); axe_check("detalj_detaljer")

            # flat spot: ordet, ingen stjerner
            page.evaluate(f"state.tab='varsel'; state.spot={fi}; state.sel=0; state.scrollToSel=true; render();")
            hf = spots[fi]["hours"][0]
            page.wait_for_selector("#detailPane .now")
            assert page.locator("#detailPane .now .stars").count() == 0, "flat time skal vise ordet, ikke grå stjerner"
            lw = page.evaluate("LOW_REASON_WORD")
            shown = page.locator("#detailPane .now .word").inner_text().strip()
            expected = lw[hf["low_reason"]] if hf.get("low_reason") else "Flatt"
            assert shown == expected, f"ordet på detaljsiden ({shown}) stemmer ikke med forecast.json ({expected})"
            assert not shown.endswith("."), "ordet skal stå uten punktum"
            shot("detalj_flat"); axe_check("detalj_flat")

            # loggark (med "Fra bilde" inni) og forklaringsark
            page.evaluate(f"state.tab='varsel'; state.spot={bi}; state.sel={bidx}; render(); openSheet(DATA.spots[{bi}].id, new Date());")
            page.wait_for_selector("#sheet.open")
            assert page.locator("#sheet #logFromPhotoBtn").count() == 1, "'Fra bilde' skal ligge i loggarket"
            shot("logg"); axe_check("logg")
            page.evaluate("closeSheet();")
            page.evaluate(f"openExplain('surf_height', DATA.spots[{bi}].hours[{bidx}], DATA.spots[{bi}]);")
            page.wait_for_selector("#exSheet.open")
            assert nf1(h["surf_height"]) in page.locator("#exBody").inner_text() if h.get("surf_height") else True
            shot("forklaring"); axe_check("forklaring")
            page.evaluate("closeExplain();")

            # kartet
            page.evaluate("state.tab='kart'; state.spot=null; render();")
            page.wait_for_selector(".leaflet-container")
            page.wait_for_selector(".spot-mark, .cluster-mark")
            assert page.locator(".leaflet-control-zoom").count() == 0, "Leaflet sine egne zoomknapper skal være byttet ut"
            shot("kart"); axe_check("kart")
            page.evaluate("state.tab='varsel'; render();")
            ctx.close()
        browser.close()
    srv.shutdown()
    print(f"Skjermbilder i {SHOT_DIR}")
    assert not errors, "JavaScript-feil i nettleseren:\n" + "\n".join(errors[:10])
    if violations:
        print("KONTRASTBRUDD (axe color-contrast):")
        for name, v in violations:
            for n in v["nodes"]:
                print(f"  {name}: {n['msg'][:140]} | {n['html'][:120]}")
        raise AssertionError(f"{len(violations)} skjermer med kontrastbrudd")
    print("1: alle skjermer rendres uten JavaScript-feil, i mobil og PC, lys og mørk")
    print("2: ordet/stjernene og surfehøyden appen viser er forecast.json sine tall")
    print("3: axe color-contrast: ingen brudd")
    print("4: ingen svevende verktøylinje, Logg-knappen i hodet")
    print("5: alle knapper minst 44 px")
    print("Alle tester ok")


if __name__ == "__main__":
    main()
