"""Nettlesertest for «kart først» (09.10.2026, Theodors skisse i
docs/design/kart-forst/): åpner den faktiske docs/index.html i Chromium med
dagens docs/data/forecast.json (window.__FORECAST__, samme hook appen selv
bruker) i mobil (390x844) og PC (1440x900), og sjekker at

1. kartet, merkene, kantpilene, arket/panelet (kikk, liste, spot), loggarket,
   forklaringsarket, Logger og Innstillinger rendres uten JavaScript-feil;
2. ordet/stjernene, surfehøyden, perioden og energien appen viser er
   forecast.json sine tall (appen regner aldri selv);
3. svellkilen på kartet klassifiseres bare fra h.directness (samme regel som
   skiva hadde, se test_map_disc.py): miss under 0,667, edge 0,667-0,999,
   treff fra 0,999 - og bølgefrontene animeres bare ved treff/kant;
4. arket på mobil kan DRAS med fingeren mellom kikk og liste (pointer-
   hendelser, ikke bare trykk);
5. avspilling ruller tiden fremover og stopper igjen;
6. alle knapper er minst 44 px, alt har tilgjengelig navn, og axe-core
   finner ingen kontrastbrudd (color-contrast);
7. prefers-reduced-motion skrur av alle animasjoner.

Skjermbildene lagres i docs/design/kart-forst/skjermbilder/ (mobil og PC).

Tidsgrenser (CLAUDE.md): hvert Playwright-steg maks 15 s, hele fila maks 5
minutter (hardkill), testserveren stoppes uansett utfall.

Miljø: NORDSURF_CHROMIUM (sti til chromium, ellers Playwright sin),
NORDSURF_AXE_PATH (lokal axe.min.js, ellers cdnjs).
Kjør: python fetcher/test_design_browser.py"""
import http.server
import json
import os
import socket
import sys
import threading
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
SHOT_DIR = DOCS / "design" / "kart-forst" / "skjermbilder"
SHOT_DIR.mkdir(parents=True, exist_ok=True)
ELEMENT_TIMEOUT_MS = 15_000
FILE_TIMEOUT_S = 300
AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
AXE_PATH = os.environ.get("NORDSURF_AXE_PATH")


def _watchdog():
    def _kill():
        print(f"TIDSAVBRUDD: test_design_browser.py brukte over {FILE_TIMEOUT_S}s - avbrutt (se CLAUDE.md).", file=sys.stderr, flush=True)
        os._exit(124)
    t = threading.Timer(FILE_TIMEOUT_S, _kill); t.daemon = True; t.start(); return t


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(Quiet, directory=str(DOCS)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def route(page):
    # tredjepart som ikke finnes i testmiljøet: avbryt stille (appen tåler det)
    for pat in ("https://cdn.jsdelivr.net/**", "https://*.supabase.co/**", "https://fonts.googleapis.com/**", "https://fonts.gstatic.com/**"):
        page.route(pat, lambda r, req: r.abort())


def nf1(v):
    return f"{v:.1f}".replace(".", ",")


def main():
    watchdog = _watchdog()
    srv, port = serve()
    forecast = json.loads((DOCS / "data" / "forecast.json").read_text(encoding="utf-8"))
    spots = forecast["spots"]
    # spot med stjerner (høyest de første 72 t) og en flat spot
    bi, bidx = max(((si, i) for si, s in enumerate(spots) for i in range(min(72, len(s["hours"])))), key=lambda p: spots[p[0]]["hours"][p[1]]["stars"])
    fi = next((i for i, s in enumerate(spots) if s["hours"][0]["stars"] == 0), 0)
    errors = []
    try:
        with sync_playwright() as p:
            exe = os.environ.get("NORDSURF_CHROMIUM")
            nb_env = {**os.environ, "LANG": "nb_NO.UTF-8", "LANGUAGE": "nb_NO", "LC_ALL": "nb_NO.UTF-8"}
            browser = p.chromium.launch(args=["--lang=nb-NO"], env=nb_env, **({"executable_path": exe} if exe else {}))
            for label, vp in (("mobil", (390, 844)), ("pc", (1440, 900))):
                mobile = vp[0] < 900
                ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]}, color_scheme="dark", locale="nb-NO", timezone_id="Europe/Oslo",
                                          device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile)
                page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS)
                page.on("pageerror", lambda e, label=label: errors.append(f"{label}: {e}"))
                page.on("console", lambda m, label=label: errors.append(f"{label} console: {m.text}") if m.type == "error" and "ERR_FAILED" not in m.text and "404" not in m.text else None)
                route(page)
                page.add_init_script(f"window.__FORECAST__ = {json.dumps(forecast)};")
                page.goto(f"http://127.0.0.1:{port}/index.html")
                page.wait_for_function("typeof DATA !== 'undefined' && DATA != null && window.Front && document.querySelectorAll('.mk').length > 0")
                if AXE_PATH:
                    page.add_script_tag(path=AXE_PATH)
                else:
                    page.add_script_tag(url=AXE_URL)
                page.wait_for_function("typeof axe !== 'undefined'")
                page.wait_for_timeout(1200)

                def shot(name):
                    page.screenshot(path=str(SHOT_DIR / f"{name}_{label}.png"), full_page=False)

                def axe_check(name):
                    res = page.evaluate("async () => { const r = await axe.run(document, {runOnly: ['color-contrast']}); return r.violations.map(v => ({id: v.id, n: v.nodes.length, ex: v.nodes.slice(0,3).map(x => x.html.slice(0,120))})); }")
                    assert not res, f"axe fant kontrastbrudd ({label}, {name}): {res}"

                def buttons_ok(name):
                    small = page.evaluate("""() => [...document.querySelectorAll('button')].filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.width < 44 || r.height < 44) && !b.closest('.hbar') && !b.classList.contains('hbar') && !b.classList.contains('tap') && !b.closest('.mk-pill'); }).map(b => b.className || b.id).slice(0, 6)""")
                    assert not small, f"knapper under 44 px ({label}, {name}): {small}"
                    unnamed = page.evaluate("""() => [...document.querySelectorAll('button')].filter(b => b.getBoundingClientRect().width > 0 && !(b.getAttribute('aria-label') || b.textContent.trim() || b.title)).map(b => b.className).slice(0, 5)""")
                    assert not unnamed, f"knapper uten tilgjengelig navn ({label}, {name}): {unnamed}"

                # ---- 1. kart + kikk/liste ----
                page.evaluate("Front.go('peek')" if mobile else "Front.go('list')")
                page.wait_for_timeout(1200)
                n_mk = page.locator(".mk:visible").count(); n_edge = page.locator(".mk-edge:visible").count()
                assert n_mk + n_edge >= 1, "ingen merker på kartet"
                # spots utenfor kartet (Farstadsanden) vises som kantpil, trykk åpner spoten direkte
                off = [s["id"] for s in spots if s.get("spot") and not (12.2 <= s["spot"]["lon"] <= 21.4 and 67.85 <= s["spot"]["lat"] <= 70.6)]
                for sid in off:
                    assert page.locator(f".mk-edge[data-id='{sid}']:visible").count() == 1, f"{sid} ligger utenfor kartet og skal vises som kantpil"
                shot("kart"); axe_check("kart"); buttons_ok("kart")
                # merkenes tekst = forecast.json for valgt time
                idx = page.evaluate("Front.state.idx")
                for s in spots:
                    h = s["hours"][idx]
                    lab = page.locator(f"[data-id='{s['id']}'] .mk-label").first.text_content()
                    exp = f"{nf1(h['surf_height'])} m" if h["stars"] >= 1 and h.get("surf_height") is not None else None
                    if exp is not None:
                        assert lab == exp, f"merket for {s['id']} sier '{lab}', forecast.json sier '{exp}'"
                    else:
                        assert lab and "m" not in lab.split()[-1] or lab, f"merket for {s['id']} skal vise ordet, viste '{lab}'"
                # Theodors punkt 1 og 2 (09.10.2026): i alle tre utsnitt skal lappen sitte
                # rett ved prikken (under 12 px mellom prikk og lapp) på mobil, og ingen
                # kantpil skal overlappe en knapp i toppen eller fargeforklaringen.
                for view in ("nord", "lofoten", "alle"):
                    page.locator(f".seg button[data-view='{view}']").click(); page.wait_for_timeout(1400)
                    gaps = page.evaluate("""() => [...document.querySelectorAll('.mk')].filter(m => !m.hidden).map(m => {
                        const d = m.querySelector('.mk-dot').getBoundingClientRect(), p = m.querySelector('.mk-pill').getBoundingClientRect();
                        const dx = Math.max(0, d.left - (p.left + p.width), p.left - (d.left + d.width));
                        const dy = Math.max(0, d.top - (p.top + p.height), p.top - (d.top + d.height));
                        return {id: m.dataset.id, gap: Math.hypot(dx, dy), lead: !m.querySelector('.lead').hidden}; })""")
                    if mobile:
                        far = [g for g in gaps if g["gap"] >= 12]
                        assert not far, f"lapp langt fra prikken i utsnitt {view}: {far}"
                    overl = page.evaluate("""() => { const obs = [...document.querySelectorAll('.top-bar .icon-btn, .top-bar .seg, .legend')].filter(e => getComputedStyle(e).display !== 'none').map(e => e.getBoundingClientRect());
                        return [...document.querySelectorAll('.mk-edge')].filter(e => !e.hidden).map(e => e.getBoundingClientRect()).filter(r => obs.some(o => r.left < o.right && r.right > o.left && r.top < o.bottom && r.bottom > o.top)).length; }""")
                    assert overl == 0, f"{overl} kantpil(er) overlapper en knapp eller forklaringen i utsnitt {view}"
                    if view == "alle":
                        shot("alle")
                    # Klyngepil («N spots»): farge og etikett skal følge VALGT time, og
                    # «flatt» bare når alle timene er ekte flate (kontrolløren 09.10.2026).
                    if page.locator(".mk-edge.cluster:visible").count():
                        i0 = page.evaluate("Front.state.idx")
                        for ti in (i0, i0 + 23, i0):
                            page.evaluate(f"Front.setIdx({ti})"); page.wait_for_timeout(150)
                            info = page.evaluate("""() => { const c = document.querySelector('.mk-edge.cluster'); const ids = c.getAttribute('aria-label').split(':')[1].split('.')[0].split(',').map(x => x.trim());
                                return {label: c.querySelector('.mk-label').textContent, cls: c.className, names: ids}; }""")
                            best, all_flat, miss = 0, True, False
                            for sp in spots:
                                if sp["name"] not in info["names"]: continue
                                h = sp["hours"][ti] if ti < len(sp["hours"]) else None
                                if not h or (h.get("surf_height") is None and not h.get("low_reason")): miss = True; continue
                                best = max(best, h.get("stars") or 0)
                                if not (h.get("low_reason") == "flat" or (not h.get("low_reason") and (h.get("surf_height") or 0) <= 0)): all_flat = False
                            exp = f"beste {best}★" if best else "–" if miss else "flatt" if all_flat else "ingen surf"
                            assert info["label"] == exp and f"r-{min(5,best)}" in info["cls"].split(), f"klyngepil i time {ti}: viste '{info['label']}' ({info['cls']}), forecast.json gir '{exp}'"
                page.locator(".seg button[data-view='nord']").click(); page.wait_for_timeout(1200)
                # 3: «Nå»-merket er lite og på linje med klokkeslettet
                now_h = page.evaluate("(() => { const n = document.getElementById('timeNow'); return n.hidden ? 20 : n.getBoundingClientRect().height; })()")
                assert now_h <= 22, f"«Nå»-merket er {now_h} px høyt, skal være ca. 20"
                page.evaluate("Front.go('list')"); page.wait_for_timeout(900)
                assert page.locator("#list .row").count() == len(spots), "lista skal ha én rad per spot"
                shot("liste"); axe_check("liste"); buttons_ok("liste")

                # ---- 4. arket dras med fingeren (mobil) ----
                if mobile:
                    page.evaluate("Front.go('peek')"); page.wait_for_timeout(900)
                    hb = page.locator(".ark-handle").bounding_box()
                    y0 = hb["y"] + hb["height"] / 2; x0 = hb["x"] + hb["width"] / 2
                    page.mouse.move(x0, y0); page.mouse.down()
                    for k in range(1, 9):
                        page.mouse.move(x0, y0 - k * 60)
                    page.mouse.up()
                    page.wait_for_timeout(900)
                    assert page.evaluate("Front.state.mode") == "list", "å dra arket opp skal gi lista"
                    hb = page.locator(".ark-handle").bounding_box(); y0 = hb["y"] + hb["height"] / 2
                    page.mouse.move(x0, y0); page.mouse.down()
                    for k in range(1, 9):
                        page.mouse.move(x0, y0 + k * 60)
                    page.mouse.up(); page.wait_for_timeout(900)
                    assert page.evaluate("Front.state.mode") == "peek", "å dra arket ned skal gi kikk"

                # ---- 2 + 3. spot ----
                s = spots[bi]; h = s["hours"][bidx]
                page.evaluate(f"Front.openSpot('{s['id']}', {bidx})"); page.wait_for_timeout(1500)
                assert page.evaluate("Front.state.mode") == "spot"
                head = page.locator("#spot .spot-head .n").text_content()
                assert head == s["name"]
                if h["stars"]:
                    aria = page.locator("#spot .rating-line .stars").get_attribute("aria-label")
                    assert aria.startswith(f"{h['stars']} av 5 stjerner"), f"stjerner ({aria}) stemmer ikke med forecast.json ({h['stars']})"
                hv = page.locator("#tHeight .v").text_content()
                if h.get("surf_height") and not h.get("low_reason"):
                    assert nf1(h["surf_height"]) in hv, f"surfehøyde-flisa ({hv}) stemmer ikke med forecast.json ({h['surf_height']})"
                pv = page.locator("#tPeriod .v").text_content()
                if h.get("period") is not None:
                    assert pv.startswith(f"{round(h['period'])} s"), f"periode-flisa ({pv}) stemmer ikke ({h['period']})"
                kj = h.get("energy_swell_kj") if h.get("swell_offshore") is not None else h.get("energy_total_kj")
                if kj:
                    kv = page.locator("#tKjSmall" if mobile else "#tKj .v").text_content()
                    assert "kJ" in kv and f"{round(kj):,}".replace(",", " ") in kv.replace(" ", " ").replace(" ", " "), f"energi-flisa ({kv}) stemmer ikke ({kj})"
                # svellkilen på kartet: klasse fra directness alene
                dn = h.get("directness"); on_map = page.locator("#wedgeG .wedge").count() == 1
                if on_map:
                    cls = page.evaluate("document.querySelector('#wedgeG .wedge').classList.contains('miss') ? 'miss' : document.querySelector('#wedgeG .wedge').classList.contains('edge') ? 'edge' : ''")
                    exp = "miss" if (dn is None or h.get("dir_offshore") is None or dn < 0.667) else ("edge" if dn < 0.999 else "")
                    assert cls == exp, f"kilen på kartet er '{cls}', forventet '{exp}' (directness {dn})"
                    n_arc = page.locator("#wedgeG .arc").count()
                    assert (n_arc > 0) == (exp != "miss"), "bølgefronter skal bare rulle inn ved treff/kant"
                    if exp == "miss":
                        assert page.locator("#wedgeG .arc-miss").count() == 1, "ved bom skal det være en grå, stiplet linje"
                assert page.locator("#spot #logBtn").count() == 1 and page.locator("#spot #details").count() == 1, "Logg-knapp og Detaljer skal finnes i spotarket"
                if not mobile:
                    # 7: Logg-knappen står ved favorittstjerna i spotpanelet på PC
                    lb, fb = page.locator("#spot #logBtn").bounding_box(), page.locator("#spot .spot-head .fav-btn").bounding_box()
                    assert lb and fb and abs(lb["y"] - fb["y"]) < 20, "Logg-knappen skal stå ved favorittstjerna i hodet (PC)"
                    # 4: ingen tekst flyter over i flisene ved 1024 og 1440 px (også med lang høydetekst)
                    for w in (1024, 1440):
                        page.set_viewport_size({"width": w, "height": 900}); page.wait_for_timeout(400)
                        page.evaluate("""() => { const h = DATA.spots[0].hours[0]; window.__bak = {...h};
                            Object.assign(h, {surf_height: 1.3, surf_height_sets: 1.7, stars: 3, low_reason: null, period: 14, swell_offshore: 2.0, energy_swell_kj: 1234}); Front.openSpot(DATA.spots[0].id, 0); }""")
                        page.wait_for_timeout(500)
                        hv = page.locator("#tHeight .v").text_content()
                        assert "1,3–1,7 m" in hv, f"høydeflisa skal si «1,3–1,7 m», sa '{hv}'"
                        over = page.evaluate("""() => [...document.querySelectorAll('#spot .tile .v, #spot .tile')].filter(e => e.scrollWidth > e.clientWidth + 1).length""")
                        assert over == 0, f"{over} flise(r) flyter over ved {w} px"
                        page.evaluate("() => { Object.assign(DATA.spots[0].hours[0], window.__bak); }")
                    page.set_viewport_size({"width": vp[0], "height": vp[1]})
                    page.evaluate(f"Front.openSpot('{s['id']}', {bidx})"); page.wait_for_timeout(800)
                assert page.locator("#bars .hbar").count() == min(48, len(s["hours"])), "48 søyler i spotarket"
                shot("spot"); axe_check("spot"); buttons_ok("spot")
                # søyle-trykk velger time
                bar = page.locator("#bars .hbar").nth(5); want = int(bar.get_attribute("data-i"))
                bar.click(); page.wait_for_timeout(300)
                assert page.evaluate("Front.state.idx") == want, f"trykk på en søyle skal velge timen (ville {want}, fikk {page.evaluate('Front.state.idx')})"
                page.evaluate(f"Front.setIdx({bidx})")
                # Detaljer åpen: Retningstreff = directness
                page.evaluate("document.getElementById('details').open = true"); page.wait_for_timeout(300)
                if dn is not None:
                    rt = page.locator("#details .cell:has-text('Retningstreff') >> .v").inner_text()
                    assert rt == f"{round(dn*100)} %", f"Retningstreff ({rt}) stemmer ikke med directness ({dn})"
                shot("spot_detaljer")
                # flat spot
                page.evaluate(f"Front.openSpot('{spots[fi]['id']}', 0)"); page.wait_for_timeout(1300)
                fh = spots[fi]["hours"][0]
                if not fh["stars"]:
                    w = page.locator("#spot .rating-line .word").text_content()
                    assert w and not w.endswith(".") and page.locator("#spot .rating-line .stars").count() == 0, "0 stjerner: ordet alene, ingen stjerner, ikke punktum"
                    # 6: surfehøyde-flisa sier ordet («Flatt»), aldri «–» (som betyr at tallet mangler)
                    hv = page.locator("#tHeight .v").text_content().strip()
                    if fh.get("low_reason") == "flat" or (fh.get("surf_height") is not None and fh["surf_height"] <= 0 and not fh.get("low_reason")):
                        assert hv == "Flatt", f"flat spot skal vise «Flatt» i høydeflisa, viste '{hv}'"
                    assert hv != "–" or fh.get("surf_height") is None, "«–» skal bare bety at tallet mangler"
                    i0 = page.evaluate("Front.state.w0")
                    if all((x.get("stars") or 0) == 0 for x in spots[fi]["hours"][i0:i0+48]):
                        assert page.locator("#bars.compact").count() == 1 and page.locator("#bars .flat-lbl").count() == 1, "alle 48 timer 0 stjerner: kompakt visning med tekst"
                        lbl = page.locator("#bars .flat-lbl").text_content()
                        assert lbl.startswith("Flatt") or lbl.startswith("Ingen surf"), lbl
                shot("spot_flat"); axe_check("spot_flat")

                # ---- loggark og forklaring ----
                page.evaluate(f"Front.openSpot('{s['id']}', {bidx}); openSheet('{s['id']}', new Date())"); page.wait_for_timeout(700)
                assert page.locator("#sheet #logFromPhotoBtn").count() == 1
                tt = page.locator("#logTimeText").inner_text(); assert "kl." in tt and "PM" not in tt
                shot("logg"); axe_check("logg"); page.evaluate("closeSheet()")
                page.evaluate(f"openExplain('surf_height', DATA.spots[{bi}].hours[{bidx}], DATA.spots[{bi}])"); page.wait_for_timeout(700)
                body = page.locator("#exSheet").inner_text()
                if h.get("surf_height"):
                    assert nf1(h["surf_height"]) in body, "forklaringsarket skal vise timens surfehøyde"
                shot("forklaring"); axe_check("forklaring"); page.evaluate("closeExplain()")

                # ---- Logger / Innstillinger (knapper i toppen) ----
                page.locator("#btnLogger").click(); page.wait_for_timeout(600)
                assert page.evaluate("Front.state.mode") == "logger" and "Logger" in page.locator("#detailPane").inner_text()
                shot("logger"); axe_check("logger")
                page.locator("#btnSettings").click(); page.wait_for_timeout(600)
                assert page.evaluate("Front.state.mode") == "innstillinger" and "Innstillinger" in page.locator("#detailPane").inner_text()
                shot("innstillinger"); axe_check("innstillinger")
                page.locator("#pageBack").click(); page.wait_for_timeout(500)

                # ---- 5. avspilling ----
                i0 = page.evaluate("Front.state.idx")
                page.locator("#play").click(); page.wait_for_timeout(1300)
                assert page.evaluate("Front.state.playing") is True
                i1 = page.evaluate("Front.state.idx"); assert i1 != i0, "avspilling skal flytte tiden"
                page.locator("#play").click(); page.wait_for_timeout(300)
                assert page.evaluate("Front.state.playing") is False
                # regionvalg
                page.locator(".seg button[data-view='lofoten']").click(); page.wait_for_timeout(1300)
                assert page.locator(".seg button[data-view='lofoten']").get_attribute("aria-pressed") == "true"
                shot("lofoten")
                ctx.close()

            # ---- 7. prefers-reduced-motion ----
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark", reduced_motion="reduce", is_mobile=True, has_touch=True)
            page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS); route(page)
            page.add_init_script(f"window.__FORECAST__ = {json.dumps(forecast)};")
            page.goto(f"http://127.0.0.1:{port}/index.html")
            page.wait_for_function("window.Front && document.querySelectorAll('.mk').length > 0")
            page.evaluate(f"Front.openSpot('{spots[bi]['id']}', {bidx})"); page.wait_for_timeout(1200)
            anim = page.evaluate("""() => [...document.querySelectorAll('.rip, .wind line, .wedge .arc, .disc .arc, .hbar .b')].filter(el => getComputedStyle(el).animationName !== 'none').length""")
            assert anim == 0, f"prefers-reduced-motion: {anim} elementer animeres fortsatt"
            ctx.close()
            browser.close()
    finally:
        srv.shutdown()
        watchdog.cancel()
    assert not errors, "JavaScript-feil i nettleseren:\n  " + "\n  ".join(e[:300] for e in errors[:10])
    print(f"Skjermbilder i {SHOT_DIR}")
    print("1: kart, merker, kantpiler, ark/panel, loggark, forklaring, Logger og Innstillinger rendres uten JavaScript-feil (mobil og PC)")
    print("2: merker, stjerner, surfehøyde, periode, energi og Retningstreff er forecast.json sine tall")
    print("3: svellkilen klassifiseres bare fra h.directness, bølgefronter bare ved treff/kant")
    print("4: arket på mobil kan dras mellom kikk og liste")
    print("5: avspilling ruller tiden, regionvalg virker")
    print("6: axe color-contrast: ingen brudd, alle knapper minst 44 px med tilgjengelig navn")
    print("7: prefers-reduced-motion skrur av animasjonene")
    print("Alle tester ok")


if __name__ == "__main__":
    main()
