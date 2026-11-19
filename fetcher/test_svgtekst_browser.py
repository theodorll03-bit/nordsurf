"""Nettlesertest for tidevannskortet og SVG-tekst i ekte piksler (Theodor 16.10.2026, gren design/tidevann).

Åpner docs/index.html i Chromium med den faste testfila fetcher/fixtures/forecast.json (publisert med
fetcher/publish.py), men med «generated» flyttet til tirsdag 20.10.2026 kl. 10 og klokka fast på kl. 11 norsk tid
(page.clock) - syntetisk «nå», ekte tidevann (Kartverket) og timer fra fiksturen. Mobil (390x844) og PC (1440x900),
lys og mørk, og sjekker:

1.  ingen JavaScript-feil;
2.  ALL SVG-tekst på spotsiden (tidevannskortet, tidevannsraden i timegrafen, kompasset i minikartet), i Utforsk
    og i eksponeringsgrafen (Logger) er 10-14 px målt i nettleseren: getComputedStyle(font-size) × (faktisk
    bredde / viewBox-bredde) fra getBoundingClientRect - på både 390 og 1440 px;
3.  ingen etiketter i tidevannskortet overlapper (bounding boxes, flo/fjære-etiketter og aksen);
4.  toppen: vannstand med to desimaler og komma («1,39 m»), «Stiger»/«Synker» som stemmer med kurven, neste
    flo/fjære med nedtelling («om 2 t 31 min») på nå - og «Neste: …» uten nedtelling på et annet tidspunkt;
    vannstanden er nøyaktig cosinus-kurven mellom Kartverkets flo og fjære (regnet uavhengig her);
5.  Farstadsanden (tide_prefer i local_rules): bånd for foretrukket vannstand og «Farstadsanden er best på lav til
    middels vannstand»; grensene i detaljfila er de samme som tide.state_at bruker (1/3, 2/3). Unstad (ingen
    preferanse): ikke noe bånd, «Spoten tåler alt tidevann»;
6.  grafen er role=slider med aria-valuetext («11:00, 1,39 meter, synker»); piltast høyre flytter valgt tid et
    kvarter for hele siden (overskriften «kl. 11», timegrafen) og beholder fokus; trykk i grafen flytter til
    nærmeste kvarter;
7.  delen av dagen som har gått dempes bare i dag;
8.  tidevann mangler (tide_events tom): «Tidevann mangler», aldri et tall;
9.  skjermbilder i docs/design/tidevann/etter/: Farstadsanden og Unstad, mobil og PC, lys og mørk (kortet).

Design B 4.0 har ikke tidevannskortet lenger (mobil fra steg 4, PC fra steg 6, SPEC §6C: tidevannet er en rad i
«time for time»): vannstanden står i måleraden og kurven i timestripa. spot_mobil() - samme sjekk på 390 og 1440 px -
sjekker samme cosinus-kurve, retningen mot neste flo/fjære («snur» nær ekstremen), båndet for foretrukket vannstand,
SVG-teksten i stripa og retningsskiva (og kompasset i minikartet på PC), og at manglende tidevann aldri blir et tall.
Punktene 3, 6 og 7 over gjaldt kortet og er borte med det; den tykke delen av kortets kurve mot tide.state_at
er erstattet av båndet i stripa (samme terskler, punkt 5).

Tidsgrenser (CLAUDE.md): hvert Playwright-steg maks 15 s, hele fila maks 5 minutter (hardkill),
testserveren stoppes uansett utfall. Kjør: python fetcher/test_svgtekst_browser.py"""
import datetime as dt
import json
import math
import os
import re
import sys
import threading
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SHOT_DIR = DOCS / "design" / "tidevann" / "etter"
SHOT_DIR.mkdir(parents=True, exist_ok=True)
ELEMENT_TIMEOUT_MS = 15_000
FILE_TIMEOUT_S = 300
OSLO = ZoneInfo("Europe/Oslo")
NOW = dt.datetime(2026, 10, 20, 11, 0, tzinfo=OSLO).astimezone(dt.timezone.utc)   # tirsdag 20.10 kl. 11
sys.path.insert(0, str(ROOT / "fetcher"))
import publish  # noqa: E402
import testserver  # noqa: E402

FORECAST = json.loads((ROOT / "fetcher" / "fixtures" / "forecast.json").read_text(encoding="utf-8"))
FORECAST["generated"] = (NOW - dt.timedelta(hours=1)).isoformat()
MISS_ID = "steinkrossa"   # punkt 8: uten tidevann
for s in FORECAST["spots"]:
    if s["id"] == MISS_ID:
        s["tide_events"] = []


def _watchdog():
    def _kill():
        print(f"TIDSAVBRUDD: test_svgtekst_browser.py brukte over {FILE_TIMEOUT_S}s - avbrutt (se CLAUDE.md).", file=sys.stderr, flush=True)
        os._exit(124)
    t = threading.Timer(FILE_TIMEOUT_S, _kill); t.daemon = True; t.start(); return t


def tide_cm(events, t):
    """uavhengig speil av kurven: cosinus mellom to motsatte ekstremer (fetcher/tide.py)"""
    ev = sorted(((dt.datetime.fromisoformat(e["time"].replace("Z", "+00:00")), e) for e in events), key=lambda x: x[0])
    for (ta, a), (tb, b) in zip(ev, ev[1:]):
        if ta <= t <= tb and a["type"] != b["type"]:
            f = (1 - math.cos(math.pi * (t - ta) / (tb - ta))) / 2
            return a["cm"] + (b["cm"] - a["cm"]) * f, b["type"] == "flo", next(e for tt, e in ev if tt > t)
    return None


def f1(cm):   # én desimal: vannstanden mellom flo og fjære er beregnet, ikke målt (kontrollør 16.10)
    return f"{cm / 100:.1f}".replace(".", ",")


SVG_TEXT_JS = r"""(sel) => [...document.querySelectorAll(sel)].filter(t => { const r = t.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !t.closest('[hidden]'); })
  .map(t => { const svg = t.ownerSVGElement, vb = svg.viewBox.baseVal, w = svg.getBoundingClientRect().width;
    const fs = parseFloat(getComputedStyle(t).fontSize) * (vb && vb.width ? w / vb.width : 1);
    return {fs, txt: t.textContent.trim().slice(0, 30), svg: (svg.className.baseVal || '') + ' ' + w.toFixed(0) + '/' + (vb ? vb.width.toFixed(0) : '-'), h: t.getBoundingClientRect().height}; })"""

def main():
    watchdog = _watchdog()
    srv, port = testserver.serve(DOCS)
    overview, details = publish.split(FORECAST)
    OV_BODY = json.dumps(overview, ensure_ascii=False)
    DET_BODY = {sid: json.dumps(d, ensure_ascii=False) for sid, d in details.items()}
    SP = {s["id"]: s for s in FORECAST["spots"]}
    errors = []
    # punkt 5: grensene i detaljfila er rating-regelens (tide.state_at: lav < 1/3, høy > 2/3), ikke nye tall
    tr = details["farstadsanden"].get("tide_regel")
    assert tr and tr["prefer"] == ["lav", "middels"], f"tide_regel for Farstadsanden: {tr}"
    assert abs(tr["lav_maks"] - 1 / 3) < 1e-3 and abs(tr["hoy_min"] - 2 / 3) < 1e-3, f"tersklene: {tr}"
    assert details["unstad"].get("tide_regel") is None, "Unstad har ingen tidevannspreferanse"
    try:
        with sync_playwright() as p:
            exe = os.environ.get("NORDSURF_CHROMIUM")
            nb_env = {**os.environ, "LANG": "nb_NO.UTF-8", "LANGUAGE": "nb_NO", "LC_ALL": "nb_NO.UTF-8"}
            browser = p.chromium.launch(args=["--lang=nb-NO", *testserver.WEBGL_ARGS], env=nb_env, **({"executable_path": exe} if exe else {}))
            for label, vp in (("mobil", (390, 844)), ("pc", (1440, 900))):
                mobile = vp[0] < 1024
                ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]}, color_scheme="light", locale="nb-NO", timezone_id="Europe/Oslo",
                                          device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile)
                page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS)
                page.clock.set_fixed_time(NOW)
                page.on("pageerror", lambda e, label=label: errors.append(f"{label}: {e}"))
                page.on("console", lambda m, label=label: errors.append(f"{label} console: {m.text}") if m.type == "error" and "ERR_FAILED" not in m.text and "404" not in m.text else None)
                for pat in ("https://cdn.jsdelivr.net/**", "https://*.supabase.co/**", "https://fonts.googleapis.com/**", "https://fonts.gstatic.com/**",
                    "https://cache.kartverket.no/**"):   # Kartverket blokkert: Utforsk viser OSM-reserven, likt lokalt og i CI
                    page.route(pat, lambda r, req: r.abort())

                def data_route(rt, req):
                    path = req.url.split("?")[0]
                    if path.endswith("/data/oversikt.json"):
                        return rt.fulfill(status=200, content_type="application/json", body=OV_BODY)
                    rt.fulfill(status=200, content_type="application/json", body=DET_BODY[path.rsplit("/", 1)[-1][:-5]])
                page.route("**/data/oversikt.json", data_route)
                page.route("**/data/spots/*.json", data_route)
                page.goto(f"http://127.0.0.1:{port}/index.html")
                page.wait_for_function("window.Front && typeof DATA !== 'undefined' && DATA && document.querySelector('#viewHjem :is(#forside, .hjem-linje)')")
                cdp = ctx.new_cdp_session(page)

                def media(scheme):
                    cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "dark" if scheme == "mork" else "light"}]})
                    page.wait_for_timeout(150)

                def go(hash_, sel="#viewSpot:not([hidden]) .dom"):
                    page.evaluate(f"location.hash = '{hash_}'")
                    page.wait_for_selector(sel)
                    page.wait_for_timeout(200)

                def check_text(sel, where, minimum=1):
                    tx = page.evaluate(SVG_TEXT_JS, sel)
                    assert len(tx) >= minimum, f"for få SVG-tekster {where} ({sel}): {len(tx)}"
                    bad = [f"«{t['txt']}» {t['fs']:.1f}px ({t['svg']})" for t in tx if not 9.95 <= t["fs"] <= 14.05]
                    assert not bad, f"SVG-tekst utenfor 10-14 px {where}: {bad[:6]}"
                    return tx

                def spot_mobil(scheme, where):
                    # spotsiden (design B 4.0, mobil steg 4 og PC steg 6): tidevannet står i måleraden og som kurve i timestripa
                    STRIPE = "#viewSpot:not([hidden]) #tstripe"

                    def tide_rad():
                        return page.evaluate("""(() => { const m = [...document.querySelectorAll('#spOver .maal')].find(m => m.querySelector('.etikett').textContent.trim() === 'Tidevann');
                            return m ? {v: m.querySelector('.mv').textContent.replace(/\s+/g, ' ').trim(), u: m.querySelector('.mu').textContent.replace(/\s+/g, ' ').trim()} : null; })()""")

                    def valgt_t(sid):
                        i = page.evaluate("(() => { const inp = document.querySelector('#tstripeVelg'); return +document.querySelector(`#tstripe .tk[data-k='${inp.value}']`).dataset.i; })()")
                        return dt.datetime.fromisoformat(details[sid]["hours"][i]["t"].replace("Z", "+00:00"))

                    def sjekk_rad(sid, hva):
                        t = valgt_t(sid); rad = tide_rad(); cm, stiger, nxt = tide_cm(SP[sid]["tide_events"], t)
                        assert rad and re.fullmatch(r"\d+,\d ?m", rad["v"]) and rad["v"].startswith(f1(cm)), f"vannstand {hva} {where}: {rad}, ventet {f1(cm)} m"
                        ekstr = [dt.datetime.fromisoformat(e["time"].replace("Z", "+00:00")) for e in SP[sid]["tide_events"]]
                        naer = [x for x in ekstr if abs((x - t).total_seconds()) <= 40 * 60]
                        if naer:
                            assert rad["u"].startswith("snur ") and any(f"{x.astimezone(OSLO):%H:%M}" in rad["u"] for x in naer), f"nær flo/fjære {hva} {where}: {rad}"
                        else:
                            nt = dt.datetime.fromisoformat(nxt["time"].replace("Z", "+00:00"))
                            assert rad["u"].startswith("↑" if stiger else "↓") and rad["u"].endswith(f"{'høy' if stiger else 'lav'} {nt.astimezone(OSLO):%H:%M}"), f"retning {hva} {where}: {rad}, ventet {'↑ høy' if stiger else '↓ lav'} {nt.astimezone(OSLO):%H:%M}"
                        return t

                    def kurve_ok(hva):
                        ov = page.evaluate("""() => { const svg = document.querySelector('#tstripe .tsvg').getBoundingClientRect(), els = [...document.querySelectorAll('#tstripe .tsvg text')], r = els.map(e => e.getBoundingClientRect()), out = [];
                          for(let i = 0; i < r.length; i++) for(let j = i + 1; j < r.length; j++){
                            const w = Math.min(r[i].right, r[j].right) - Math.max(r[i].left, r[j].left), h = Math.min(r[i].bottom, r[j].bottom) - Math.max(r[i].top, r[j].top);
                            if(w > 0.5 && h > 0.5) out.push(els[i].textContent + ' × ' + els[j].textContent); }
                          r.forEach((b, i) => { if(b.left < svg.left - 0.5 || b.right > svg.right + 0.5) out.push('utenfor stripa: ' + els[i].textContent); });
                          return {out, n: els.length}; }""")
                        assert ov["n"] >= 2 and not ov["out"], f"flo/fjære-etiketter som overlapper eller faller utenfor {hva} {where}: {ov}"
                        check_text("#tstripe .tsvg text", f"tidevannskurven i timestripa {hva} {where}", 2)
                        check_text("#viewSpot .skive svg text", f"retningsskiva {hva} {where}", 4)

                    # ---- Farstadsanden nå (tirsdag 20.10 kl. 11) ----
                    go("#spot=farstadsanden", STRIPE + " .tsvg")
                    assert page.get_attribute("#tstripe", "data-day") == NOW.astimezone(OSLO).date().isoformat() and page.evaluate("window.__S.idx") is None
                    t0 = sjekk_rad("farstadsanden", "Farstadsanden")
                    assert t0 == NOW, f"siden skal stå på timen som er nå {where}: {t0}"
                    assert page.locator("#tstripe .naalinje").count() == 1 and "Nå" in page.text_content("#tstripe .tikk"), f"nå-linja mangler i dag {where}"
                    # foretrukket vannstand (tide_regel, samme terskler som tide.state_at): bånd bak kurven og setningen i etiketten
                    assert page.locator("#tstripe .tsvg rect.bnd").count() >= 1, f"båndet for foretrukket vannstand mangler {where}"
                    etikett = page.get_attribute("#tstripe .tsvg", "aria-label")
                    assert etikett.startswith("Tidevann: ") and "Farstadsanden er best på lav til middels vannstand" in etikett, f"etiketten {where}: {etikett}"
                    kurve_ok("Farstadsanden")
                    if not mobile:   # minikartet på PC (SPEC §6C punkt 6): kompasset i ekte piksler
                        page.wait_for_selector("#miniKort .minikart path.land")
                        check_text("#viewSpot .minikart text", f"kompasset i minikartet {where}", 4)
                    page.locator("#spStripe").screenshot(path=str(SHOT_DIR / f"farstadsanden_{label}_{scheme}.png"))
                    # ---- samhandling: piltast flytter valgt time for hele siden, også tidevannet ----
                    page.focus("#tstripeVelg"); page.keyboard.press("ArrowRight"); page.wait_for_timeout(250)
                    assert page.text_content("#spOver .sek-spot h2").strip() == "Kl. 12" and page.text_content("#spUnder h2").strip() == "Retning kl. 12", f"piltast høyre {where}"
                    assert page.evaluate("document.activeElement && document.activeElement.id") == "tstripeVelg", f"fokus forlot timevelgeren {where}"
                    assert page.locator("#tilbakeNa").count() == 1, f"«Tilbake til nå» mangler etter piltast {where}"
                    assert sjekk_rad("farstadsanden", "kl. 12") == NOW + dt.timedelta(hours=1)
                    assert re.search(r"(stigende|synkende|høyvann|lavvann|snur)", page.get_attribute("#tstripeVelg", "aria-valuetext")), page.get_attribute("#tstripeVelg", "aria-valuetext")
                    page.click("#tilbakeNa"); page.wait_for_timeout(200)
                    assert page.locator("#tilbakeNa").count() == 0 and page.text_content("#spOver .sek-spot h2").strip() == "Kl. 11", f"«Tilbake til nå» {where}"
                    # ---- en annen dag: ingen nå-linje ----
                    i_ons = next(i for i, h in enumerate(details["farstadsanden"]["hours"]) if h["t"] == "2026-10-21T10:00Z")
                    go(f"#spot=farstadsanden&t={i_ons}", STRIPE + "[data-day='2026-10-21'] .tsvg")
                    assert page.locator("#tstripe .naalinje").count() == 0, f"nå-linja skal bare vises i dag {where}"
                    sjekk_rad("farstadsanden", "onsdag kl. 12")
                    # ---- Unstad: ingen preferanse, ikke noe bånd ----
                    go("#spot=unstad", STRIPE + " .tsvg")
                    assert page.locator("#tstripe .tsvg rect.bnd").count() == 0 and "best på" not in page.get_attribute("#tstripe .tsvg", "aria-label"), f"Unstad har foretrukket vannstand {where}"
                    sjekk_rad("unstad", "Unstad")
                    kurve_ok("Unstad")
                    page.locator("#spStripe").screenshot(path=str(SHOT_DIR / f"unstad_{label}_{scheme}.png"))
                    # ---- tidevann mangler: ingen rad og ingen kurve, aldri et tall ----
                    go(f"#spot={MISS_ID}", STRIPE + " .kolonner")
                    page.wait_for_timeout(200)
                    assert tide_rad() is None and page.locator("#tstripe .tsvg").count() == 0, f"tidevann mangler {where}: {tide_rad()}"
                    assert "tidevann" not in (page.get_attribute("#tstripeVelg", "aria-valuetext") or "").lower(), f"tidevann mangler, men leses opp {where}"

                for scheme in ("lys", "mork"):
                    media(scheme)
                    where = f"({label}, {scheme})"
                    spot_mobil(scheme, where)
                    # ---- Utforsk og eksponeringsgrafen (Logger) ----
                    page.evaluate("location.hash = '#utforsk'"); page.wait_for_timeout(400)
                    tx = page.evaluate(SVG_TEXT_JS, "main .view:not([hidden]) svg text")
                    bad = [x for x in tx if not 9.95 <= x["fs"] <= 14.05]
                    assert not bad, f"SVG-tekst i Utforsk utenfor 10-14 px {where}: {bad[:4]}"
                    page.evaluate("""() => { const v = document.querySelector('main .view:not([hidden])') || document.body;
                      const c = Array.from({length: 36}, (_, i) => ({geometric: Math.abs(Math.sin(i / 6)), learned_lang: i % 3 ? .5 : null, pairs_lang: i % 4}));
                      const d = document.createElement('div'); d.id = 'expoTest'; d.className = 'kort'; d.innerHTML = exposureChartSVG('x', c, []); v.prepend(d); }""")
                    page.wait_for_timeout(200)
                    check_text("#expoTest svg text", f"eksponeringsgrafen {where}", 6)
                    page.evaluate("document.querySelector('#expoTest').remove()")
                ctx.close()
            browser.close()
    finally:
        srv.shutdown()
        watchdog.cancel()
    assert not errors, f"JavaScript-feil: {errors[:5]}"
    print("Tidevannskortet og SVG-tekst i ekte piksler: alle sjekker ok (390 og 1440 px, lys og mørk)")


if __name__ == "__main__":
    main()
