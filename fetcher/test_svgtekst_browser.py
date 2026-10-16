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

OVERLAP_JS = r"""() => { const els = [...document.querySelectorAll('#tideKort .tv-lbl, #tideKort .tv-ax')];
  const r = els.map(e => e.getBoundingClientRect()); const out = [];
  for(let i = 0; i < r.length; i++) for(let j = i + 1; j < r.length; j++){
    const w = Math.min(r[i].right, r[j].right) - Math.max(r[i].left, r[j].left), h = Math.min(r[i].bottom, r[j].bottom) - Math.max(r[i].top, r[j].top);
    if(w > 0.5 && h > 0.5) out.push(els[i].textContent + ' × ' + els[j].textContent); }
  const kort = document.querySelector('#tideKort').getBoundingClientRect();
  r.forEach((b, i) => { if(b.left < kort.left - 0.5 || b.right > kort.right + 0.5) out.push('utenfor kortet: ' + els[i].textContent); });
  return {out, n: els.length}; }"""


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
                mobile = vp[0] < 900
                ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]}, color_scheme="light", locale="nb-NO", timezone_id="Europe/Oslo",
                                          device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile)
                page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS)
                page.clock.set_fixed_time(NOW)
                page.on("pageerror", lambda e, label=label: errors.append(f"{label}: {e}"))
                page.on("console", lambda m, label=label: errors.append(f"{label} console: {m.text}") if m.type == "error" and "ERR_FAILED" not in m.text and "404" not in m.text else None)
                for pat in ("https://cdn.jsdelivr.net/**", "https://*.supabase.co/**", "https://fonts.googleapis.com/**", "https://fonts.gstatic.com/**"):
                    page.route(pat, lambda r, req: r.abort())

                def data_route(rt, req):
                    path = req.url.split("?")[0]
                    if path.endswith("/data/oversikt.json"):
                        return rt.fulfill(status=200, content_type="application/json", body=OV_BODY)
                    rt.fulfill(status=200, content_type="application/json", body=DET_BODY[path.rsplit("/", 1)[-1][:-5]])
                page.route("**/data/oversikt.json", data_route)
                page.route("**/data/spots/*.json", data_route)
                page.goto(f"http://127.0.0.1:{port}/index.html")
                page.wait_for_function("window.Front && typeof DATA !== 'undefined' && DATA && document.querySelector('#viewHjem #bestKort')")
                cdp = ctx.new_cdp_session(page)

                def media(scheme):
                    cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "dark" if scheme == "mork" else "light"}]})
                    page.wait_for_timeout(150)

                def go(hash_):
                    page.evaluate(f"location.hash = '{hash_}'")
                    page.wait_for_selector("#viewSpot:not([hidden]) #tideKort")
                    page.wait_for_timeout(200)

                def show_card():
                    page.evaluate("document.querySelector('#tideKort').scrollIntoView({block: 'center'})")
                    # animasjonen (bare første gang kortet kommer i bildet) skal starte når kortet er i bildet og bli ferdig
                    page.wait_for_function("() => { const c = document.querySelector('#tideGraf svg').classList; return !c.contains('intro') || c.contains('go'); }")
                    page.wait_for_timeout(50)
                    page.wait_for_function("""() => document.getAnimations().filter(a => a.playState === 'running' && a.effect && a.effect.getComputedTiming().iterations !== Infinity).length === 0""")
                    page.wait_for_timeout(100)
                    synlig = page.evaluate("""() => [...document.querySelectorAll('#tideKort .tv-ext')].map(e => getComputedStyle(e).opacity)""")
                    assert synlig and all(o == "1" for o in synlig), f"flo/fjære-etikettene er ikke synlige etter animasjonen: {synlig}"
                    dash = page.evaluate("getComputedStyle(document.querySelector('#tideKort .tv-curve')).strokeDashoffset")
                    assert dash in ("0", "0px"), f"kurven er ikke ferdig tegnet: {dash}"

                def check_text(sel, where, minimum=1):
                    tx = page.evaluate(SVG_TEXT_JS, sel)
                    assert len(tx) >= minimum, f"for få SVG-tekster {where} ({sel}): {len(tx)}"
                    bad = [f"«{t['txt']}» {t['fs']:.1f}px ({t['svg']})" for t in tx if not 9.95 <= t["fs"] <= 14.05]
                    assert not bad, f"SVG-tekst utenfor 10-14 px {where}: {bad[:6]}"
                    return tx

                for scheme in ("lys", "mork"):
                    media(scheme)
                    where = f"({label}, {scheme})"
                    # ---- Farstadsanden nå (tirsdag 20.10 kl. 11) ----
                    go("#spot=farstadsanden")
                    show_card()
                    sp = SP["farstadsanden"]
                    cm, stiger, nxt = tide_cm(sp["tide_events"], NOW)
                    h_txt = page.text_content("#tideKort .tv-h").replace("\u00a0", " ").strip()
                    assert re.fullmatch(r"\d+,\d\s*m", h_txt) and h_txt.startswith(f1(cm)), f"vannstand {where}: «{h_txt}», ventet {f1(cm)} m"
                    trend = page.text_content("#tideKort .tv-trend").strip()
                    assert trend == ("Stiger" if stiger else "Synker"), f"trend {where}: {trend}"
                    neste = page.text_content("#tideKort .tv-neste").replace("\u00a0", " ").strip()
                    nt = dt.datetime.fromisoformat(nxt["time"].replace("Z", "+00:00"))
                    mins = round((nt - NOW).total_seconds() / 60)
                    om = f"om {mins // 60} t {mins % 60} min" if mins >= 60 else f"om {mins} min"
                    nf1 = f"{nxt['cm'] / 100:.1f}".replace(".", ",")
                    want = f"{nxt['type'].capitalize()} {nt.astimezone(OSLO):%H:%M} · {nf1} m · {om}"
                    assert neste == want, f"neste ekstrem {where}: «{neste}», ventet «{want}»"
                    sl = page.locator("#tideGraf")
                    assert sl.get_attribute("role") == "slider", "grafen er ikke role=slider"
                    vt = sl.get_attribute("aria-valuetext")
                    assert vt == f"11:00, {f1(cm)} meter, {'stiger' if stiger else 'synker'}", f"aria-valuetext {where}: {vt}"
                    assert page.locator("#tideKort .tv-band").count() >= 1, f"bånd for foretrukket vannstand mangler {where}"
                    fot = page.text_content("#tideKort .tv-fot").strip()
                    assert "Farstadsanden er best på lav til middels vannstand" in fot, f"forklaringen {where}: {fot}"
                    assert page.locator("#tideKort .tv-past").count() == 1, f"delen av dagen som har gått er ikke dempet {where}"
                    smal = page.evaluate("document.querySelector('#tideGraf').clientWidth") < 520
                    lbl = [t.strip() for t in page.locator("#tideKort .tv-lbl").all_text_contents()]
                    assert lbl and all((re.fullmatch(r"\d\d:\d\d \d+,\d", t) if smal else re.fullmatch(r"(Flo|Fjære) \d\d:\d\d · \d+,\d m", t)) for t in lbl), f"etikettene {where}: {lbl}"
                    ov = page.evaluate(OVERLAP_JS)
                    assert ov["n"] >= 7 and not ov["out"], f"etiketter som overlapper eller faller utenfor {where}: {ov}"
                    check_text("#tideKort svg text", f"tidevannskortet {where}", 7)
                    check_text("#viewSpot .tv-mini svg text", f"tidevannsraden i timegrafen {where}", 5)
                    check_text("#viewSpot .minikart text", f"kompasset i minikartet {where}", 4)
                    page.locator("#tideKort").screenshot(path=str(SHOT_DIR / f"farstadsanden_{label}_{scheme}.png"))
                    # ---- samhandling: piltast og trykk flytter valgt tid for hele siden ----
                    sl.focus(); page.keyboard.press("ArrowRight"); page.wait_for_timeout(250)
                    vt2 = page.get_attribute("#tideGraf", "aria-valuetext")
                    assert vt2.startswith("11:15, "), f"piltast høyre {where}: {vt2}"
                    assert page.evaluate("document.activeElement && document.activeElement.id") == "tideGraf", f"fokus forlot grafen {where}"
                    assert "kl. 11" in page.text_content("#viewSpot .naa"), f"overskriften fulgte ikke valgt tid {where}"
                    assert page.locator("#tilbakeNa").count() == 1, f"«Tilbake til nå» mangler etter piltast {where}"
                    n2 = page.text_content("#tideKort .tv-neste").strip()
                    assert n2.startswith("Neste: ") and " om " not in n2, f"nedtelling bare på nå {where}: {n2}"
                    page.keyboard.press("ArrowLeft"); page.wait_for_timeout(250)
                    assert page.get_attribute("#tideGraf", "aria-valuetext").startswith("11:00, "), f"piltast venstre {where}"
                    box = sl.bounding_box()
                    page.mouse.click(box["x"] + 6 + (box["width"] - 12) * 15 / 24, box["y"] + box["height"] / 2)
                    page.wait_for_timeout(300)
                    vt3 = page.get_attribute("#tideGraf", "aria-valuetext")
                    assert vt3.startswith("15:00, "), f"trykk i grafen {where}: {vt3}"
                    assert "kl. 15" in page.text_content("#viewSpot .naa"), f"trykk flyttet ikke valgt time {where}"
                    assert page.locator("#viewSpot .kol.valgt[data-hh='15']").count() == 1, f"timegrafen fulgte ikke {where}"
                    page.click("#tilbakeNa"); page.wait_for_timeout(200)
                    # ---- en annen dag: ikke dempet ----
                    i_ons = next(i for i, h in enumerate(details["farstadsanden"]["hours"]) if h["t"] == "2026-10-21T10:00Z")
                    go(f"#spot=farstadsanden&t={i_ons}")
                    assert page.locator("#tideKort .tv-past").count() == 0, f"en annen dag skal ikke dempes {where}"
                    # ---- Unstad: ingen preferanse ----
                    go("#spot=unstad")
                    show_card()
                    assert page.locator("#tideKort .tv-band").count() == 0, f"Unstad har bånd {where}"
                    assert "Spoten tåler alt tidevann" in page.text_content("#tideKort .tv-fot"), f"Unstad-teksten {where}"
                    ov = page.evaluate(OVERLAP_JS)
                    assert not ov["out"], f"etiketter som overlapper {where} (Unstad): {ov}"
                    check_text("#tideKort svg text", f"tidevannskortet Unstad {where}", 7)
                    check_text("#viewSpot .minikart text", f"kompasset Unstad {where}", 4)
                    page.locator("#tideKort").screenshot(path=str(SHOT_DIR / f"unstad_{label}_{scheme}.png"))
                    # ---- tidevann mangler ----
                    go(f"#spot={MISS_ID}")
                    t = page.text_content("#tideKort").strip()
                    assert "Tidevann mangler" in t and not re.search(r"\d", t), f"tidevann mangler {where}: «{t}»"
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
