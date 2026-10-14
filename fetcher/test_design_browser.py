"""Nettlesertest for forsiden («kart først» 09.10.2026, «oversikt» 13.10.2026):
åpner den faktiske docs/index.html i Chromium med dagens
docs/data/forecast.json (window.__FORECAST__, samme hook appen selv bruker) i
mobil (390x844) og PC (1440x900), og sjekker at

1. kartet, merkene, kantpilene, arket/panelet, loggarket, forklaringsarket,
   Logger og Innstillinger rendres uten JavaScript-feil;
2. ordet/stjernene, surfehøyden, perioden og energien appen viser er
   forecast.json sine tall (appen regner aldri selv);
3. svellkilen på kartet klassifiseres bare fra h.directness (samme regel som
   skiva hadde, se test_map_disc.py) - og bølgefrontene animeres bare ved
   treff/kant;
4. arket på mobil starter i halv høyde (svarlinja og lista synlig uten å
   dra) og kan DRAS med fingeren mellom liste, halv og kart;
5. avspilling ruller tiden fremover og stopper igjen;
6. alle knapper er minst 44 px, alt har tilgjengelig navn, og axe-core
   finner ingen kontrastbrudd (color-contrast);
7. prefers-reduced-motion skrur av alle animasjoner.

Oversikt (Theodor 13.10.2026), egne sjekker:
8. svarlinja velger riktig time: tidligste time med minst 2 stjerner i lyse
   timer de neste 72 timene i området i utsnittet (flest stjerner, så
   favoritt, ved samme time), ellers «Ingen gode økter i … de neste 3 dagene»
   og «Neste mulighet: …» - og trykk åpner spoten på SAMME time som kartet viser;
   mangler noen timer data i vinduet, sier svarlinja det (grunnregelen);
9. flate spots (0 stjerner) har ingen lapp på kartet - bare spots med
   stjerner, favoritter og valgt spot; ingen streker fra prikk til lapp;
   kantpiler bare for stjerner og favoritter; én tekst på kartet når hele
   utsnittet er 0 stjerner; en spot der tallet MANGLER er aldri den grå
   0-prikken (stiplet prikk og lappen «–»); på mobil ligger kantpilene langs
   kanten av kartet, ikke midt i kartet over arket;
10. ukeoversikten har riktig farge per dag (beste rating i lyse timer, grå
    for 0, stiplet når tallet mangler eller lyset er ukjent), to bokstaver per
    dag (ti on to …), ring rundt i dag, og alt får plass på 390 px; lista følger
    regionvalget (favoritter øverst, så regionen, så «Andre områder» - lukket
    på mobil, åpen på PC; «Alle» som før); kolonnen til høyre har tittelen
    «nå» (eller tidspunktet når tiden er flyttet);
11. tiden er en pille («Nå» / «Tor 17:00»), trykk åpner glidebryter og play,
    og «Tilbake til nå» vises når tiden ikke står på nå;
12. vindstrekene vises bare når en spot er valgt, og flate merker og
    listerader animeres ikke;
13. når nåtimen flytter seg (appen står åpen / kommer fra bakgrunnen), følger
    svarlinja, uka og «Nå» med - en tid brukeren har flyttet til, blir stående.

Skjermbildene lagres i docs/design/oversikt/etter/ (mobil og PC).

Tidsgrenser (CLAUDE.md): hvert Playwright-steg maks 15 s, hele fila maks 5
minutter (hardkill), testserveren stoppes uansett utfall.

Data og klokke (S2, 14.10.2026): testen bruker den faste testfila
fetcher/fixtures/forecast.json (ekte varsel 14.10.2026 kl. 19Z) - ikke dagens
varsel, som ikke ligger i git lenger - og serverer den slik appen får den:
data/oversikt.json og data/spots/<id>.json laget av fetcher/publish.py. Siden
kjører med Date fast på T0 = litt etter at varselet ble laget
(page.clock.set_fixed_time - tidtakerne går som vanlig), og testen regner selv
fra samme T0. Da avhenger testen verken av dagens data eller av en timegrense
midt i kjøringen (CI 14.10.2026 kl. 13:00Z).

0. S2: forsiden med bare oversikten er lik forsiden med hele varselet (svarlinja,
   lista, merkene, kantpilene, teksten på kartet) i alle tre utsnitt og over
   glidebryterens timer; forsiden laster aldri en detaljfil; en spot som åpnes
   viser «Henter detaljene …» (ingen tall, ingen kile) til fila er her; svarer
   detaljfila med feil, sier arket det og «Prøv igjen» henter på nytt; er
   detaljfila fra en annen kjøring (nytt varsel publisert), lastes siden på
   nytt én gang.

Miljø: NORDSURF_CHROMIUM (sti til chromium, ellers Playwright sin),
NORDSURF_AXE_PATH (lokal axe.min.js, ellers cdnjs).
Kjør: python fetcher/test_design_browser.py"""
import datetime as dt
import http.server
import json
import os
import socket
import sys
import threading
from functools import partial
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
SHOT_DIR = DOCS / "design" / "oversikt" / "etter"
SHOT_DIR.mkdir(parents=True, exist_ok=True)
ELEMENT_TIMEOUT_MS = 15_000
FILE_TIMEOUT_S = 300
AXE_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
AXE_PATH = os.environ.get("NORDSURF_AXE_PATH")
OSLO = ZoneInfo("Europe/Oslo")
FIXTURE = ROOT / "fetcher" / "fixtures" / "forecast.json"   # fast varsel (14.10.2026 kl. 19Z), ikke dagens
T0 = (dt.datetime.fromisoformat(json.loads(FIXTURE.read_text(encoding="utf-8"))["generated"].replace("Z", "+00:00"))
      + dt.timedelta(minutes=70)).astimezone(dt.timezone.utc)   # «nå» for hele kjøringen, i siden og i testen
TODAY = T0.astimezone(OSLO).date()
DAY2 = ["ma", "ti", "on", "to", "fr", "lø", "sø"]   # mandag ... søndag (Theodor 13.10.2026)
WD_SHORT = ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"]


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


def r0(v):
    """hele tall som appens nf0 (Intl.NumberFormat, halfExpand): ,5 rundes bort fra null.
    Pythons round() runder ,5 til nærmeste partall (74,5 -> 74) og bommer på appen (75)."""
    return int(v + 0.5) if v >= 0 else -int(-v + 0.5)


def nf1(v):
    return f"{v:.1f}".replace(".", ",")


def oslo(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(OSLO)


def oslo_day(t):
    return oslo(t).date().isoformat()


# ---- speil av appens regler (front.js) - testen regner selv, sammenligner med DOM ----
def usable(h):
    return bool(h) and h.get("light") in ("dag", "skumring")


def known(h):
    return bool(h) and not (not (h.get("stars") or 0) and not h.get("low_reason") and h.get("surf_height") is None)


def day_best(hours, w0, day_key):
    """speiler dayBest() i front.js (light = Kart.lightOf(h), None = ukjent lys)"""
    anyh = light = unk = miss = False
    best = -1
    for i in range(w0, len(hours)):
        h = hours[i]; k = oslo_day(h["t"])
        if k > day_key: break
        if k != day_key: continue
        anyh = True
        lt = h.get("light")
        if lt is None:
            unk = True
            if not known(h) or (h.get("stars") or 0) >= 1: miss = True
            continue
        if lt not in ("dag", "skumring"): continue
        light = True
        if not known(h): miss = True; continue
        best = max(best, h.get("stars") or 0)
    if not anyh: return "miss"
    if best >= 1: return f"r-{min(5, best)}"
    if miss or (not light and unk): return "miss"
    if not light: return "dark"
    return "r-0"


def mirror_answer(region, w0, w3, max_idx, favs=()):
    """speiler answer() i front.js: (kind, (spot_id, i, j, stjerner) | None)"""
    def first(lo, hi, min_st):
        for i in range(lo, hi):
            best = None
            for s in region:
                h = s["hours"][i] if i < len(s["hours"]) else None
                if not h or not usable(h) or (h.get("stars") or 0) < min_st: continue
                st, fav = h["stars"], s["id"] in favs
                if best is None or st > best[1] or (st == best[1] and fav and not best[2]):
                    best = (s, st, fav)
            if best:
                s, st = best[0], best[1]; j = i
                while j + 1 <= max_idx and j + 1 < len(s["hours"]) and usable(s["hours"][j + 1]) and (s["hours"][j + 1].get("stars") or 0) == st:
                    j += 1
                return (s["id"], i, j, st)
        return None
    good = first(w0, min(w3, max_idx + 1), 2)
    return ("good", good) if good else ("none", first(w0, max_idx + 1, 1))


def mirror_gaps(region, w0, w3, max_idx, n_hours):
    """speiler windowGaps() i front.js: mangler noe i vinduet «Ingen surf …» gjelder?"""
    hi = min(w3, max_idx + 1)
    if hi < w3 or w3 >= n_hours: return True
    for s in region:
        for i in range(w0, hi):
            h = s["hours"][i] if i < len(s["hours"]) else None
            if not h: return True
            lt = h.get("light")
            if lt == "mørkt": continue
            if not known(h): return True
            if lt is None and (h.get("stars") or 0) >= 2: return True
    return False


def span_text(a, b):
    """speiler spanText() i front.js (a, b: første og siste time i Oslo-tid)"""
    end = f"{(b.hour + 1) % 24:02d}"
    if a.date() == b.date(): return f"{a.hour:02d}–{end}"
    e = b + dt.timedelta(hours=1)
    day = "i dag" if e.date() == TODAY else WD_SHORT[e.weekday()].lower()
    return f"{a.hour:02d}–{day} {end}"


def main():
    watchdog = _watchdog()
    srv, port = serve()
    forecast = json.loads(FIXTURE.read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT / "fetcher"))
    import publish
    overview, details = publish.split(forecast)
    OV_BODY = json.dumps(overview, ensure_ascii=False)
    DET_BODY = {sid: json.dumps(d, ensure_ascii=False) for sid, d in details.items()}
    EXPECT_ERR = {"on": False}
    spots = forecast["spots"]
    LOW = {"flat": "Flatt", "blown_out": "Blåst ut", "stormsjo": "Stormsjø", "treffer_ikke": "Treffer ikke"}
    STARW = ["Flatt", "Dårlig", "Ok", "Bra", "Veldig bra", "Rått"]
    def zero_cause(h, spot):
        # speiler zeroCause() i docs/js/app.js (Theodors regel 09.10.2026, tredje runde)
        per = h.get("period")
        if per is not None and per < 9: return "Grøtete"
        lr = h.get("local_rules") or {}
        z = h.get("zero_losses")
        c = ({k: z.get(k) or 0 for k in ("energy", "wind", "tide", "local")} if z
             else {"energy": 0, "wind": h.get("faded_wind") or 0, "tide": h.get("faded_tide") or 0, "local": lr.get("stars_lost") or 0})
        cap = (z.get("cap") or 0) if z else 0
        mx = max(c.values()); win = [k for k, v in c.items() if v == mx and mx > 0]
        if mx == 0 and cap == 0: return "Ikke surfbart nå"
        if cap >= mx: return "Usikkert" if h.get("sources_disagree") else "Ikke surfbart nå"
        if len(win) != 1: return "Ikke surfbart nå"
        w = win[0]
        if w == "energy":
            return "For lite svell" if (spot and (spot.get("local_rules") or {}).get("min_energy_kj")) else "Grøtete"
        if w == "wind": return "Blåst ut"
        if w == "tide": return "Feil tidevann"
        pen = [l for l in (lr.get("lines") or []) if "−" in l]
        if len(pen) != 1: return "Ikke surfbart nå"
        return "Feil tidevann" if pen[0].startswith("Tidevann") else "Blåst ut" if pen[0].startswith("Vind") else "Ikke surfbart nå"
    def word_of(h, spot=None):
        # speiler ratingWord() i docs/js/app.js (Theodors ja 09.10.2026: Flatt/Smått, og årsaksordet fra 0,8 m)
        if not h: return "–"
        if not (h.get("stars") or 0) and not h.get("low_reason") and h.get("surf_height") is None: return "–"
        if not (h.get("stars") or 0) and (h.get("low_reason") in ("flat", None)) and h.get("surf_height") is not None:
            return zero_cause(h, spot) if h["surf_height"] >= 0.8 else "Smått" if h["surf_height"] >= 0.3 else "Flatt"
        if h.get("low_reason"): return LOW.get(h["low_reason"], STARW[0])
        return STARW[min(5, h.get("stars") or 0)]
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
                page.clock.set_fixed_time(T0)
                page.on("pageerror", lambda e, label=label: errors.append(f"{label}: {e}"))
                page.on("console", lambda m, label=label: errors.append(f"{label} console: {m.text}") if m.type == "error" and "ERR_FAILED" not in m.text and "404" not in m.text and not EXPECT_ERR["on"] else None)
                route(page)
                # S2: varselet slik appen får det - oversikten og én fil per spot (publish.split på testfila)
                HOLD = {"on": False, "fail": set(), "newrun": set(), "routes": [], "count": {}}
                def data_route(rt, req, HOLD=HOLD):
                    path = req.url.split("?")[0]
                    key = "oversikt" if path.endswith("/data/oversikt.json") else path.rsplit("/", 1)[-1][:-5]
                    HOLD["count"][key] = HOLD["count"].get(key, 0) + 1
                    HOLD.setdefault("log", []).append((key, "fail" if key in HOLD["fail"] else "newrun" if key in HOLD["newrun"] else "hold" if HOLD["on"] else "ok"))
                    if key == "oversikt":
                        return rt.fulfill(status=200, content_type="application/json", body=OV_BODY)
                    if key in HOLD["fail"]:
                        HOLD["fail"].discard(key)
                        return rt.fulfill(status=500, body="feil")
                    if key in HOLD["newrun"]:   # som om et nytt varsel er publisert etter at oversikten ble lastet
                        HOLD["newrun"].discard(key)
                        return rt.fulfill(status=200, content_type="application/json", body=json.dumps(dict(json.loads(DET_BODY[key]), run="annen-kjoring"), ensure_ascii=False))
                    if HOLD["on"]:
                        HOLD["routes"].append((rt, key)); return
                    rt.fulfill(status=200, content_type="application/json", body=DET_BODY[key])
                page.route("**/data/oversikt.json", data_route)
                page.route("**/data/spots/*.json", data_route)
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

                def edges_on_edge(where):
                    # mobil: kantpilene ligger langs kanten av kartet (side- eller overkant), aldri midt i kartet over arket
                    ed = page.evaluate("""() => { const top = document.querySelector('.top-bar .ctrl').getBoundingClientRect().bottom + 8;
                        return [...document.querySelectorAll('.mk-edge')].filter(e => !e.hidden).map(e => { const r = e.getBoundingClientRect();
                            return {id: e.dataset.id || e.textContent.trim(), l: Math.round(r.left), r: Math.round(r.right), t: Math.round(r.top), top: Math.round(top), W: innerWidth}; }); }""")
                    off = [e for e in ed if not (e["l"] <= 12 or e["r"] >= e["W"] - 12 or e["t"] <= e["top"] + 12)]
                    assert not off, f"mobil ({where}): kantpilene skal ligge langs kanten av kartet, ikke midt i kartet over arket: {off}"
                    return ed

                def edges_clear(where):
                    # en kantpil skal aldri dekke en spot på kartet (prikken eller en synlig lapp)
                    bad = page.evaluate("""() => { const box = el => el.getBoundingClientRect();
                        const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
                        const mks = [...document.querySelectorAll('.mk')].filter(m => !m.hidden && box(m.querySelector('.mk-dot')).width > 0);
                        const tg = mks.flatMap(m => [{id: m.dataset.id, r: box(m.querySelector('.mk-dot'))}].concat(m.classList.contains('bare') ? [] : [{id: m.dataset.id + ' (lapp)', r: box(m.querySelector('.mk-pill'))}]));
                        return [...document.querySelectorAll('.mk-edge')].filter(e => !e.hidden).flatMap(e => tg.filter(t => hit(box(e), t.r)).map(t => [e.dataset.id || 'klynge', t.id])); }""")
                    assert not bad, f"kantpil som dekker en spot ({label}, {where}): {bad}"

                def axe_check(name):
                    res = page.evaluate("async () => { const r = await axe.run(document, {runOnly: ['color-contrast']}); return r.violations.map(v => ({id: v.id, n: v.nodes.length, ex: v.nodes.slice(0,3).map(x => x.html.slice(0,120))})); }")
                    assert not res, f"axe fant kontrastbrudd ({label}, {name}): {res}"

                def buttons_ok(name):
                    small = page.evaluate("""() => [...document.querySelectorAll('button')].filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.width < 43.5 || r.height < 43.5) && !b.closest('.hbar') && !b.classList.contains('hbar') && !b.classList.contains('tap') && !b.closest('.mk-pill'); }).map(b => { const r = b.getBoundingClientRect(); return `${b.className || b.id} ${b.dataset.id || ''} ${r.width.toFixed(1)}x${r.height.toFixed(1)} ${getComputedStyle(b).display}`; }).slice(0, 6)""")
                    assert not small, f"knapper under 44 px ({label}, {name}): {small}"
                    unnamed = page.evaluate("""() => [...document.querySelectorAll('button')].filter(b => b.getBoundingClientRect().width > 0 && !(b.getAttribute('aria-label') || b.textContent.trim() || b.title)).map(b => b.className).slice(0, 5)""")
                    assert not unnamed, f"knapper uten tilgjengelig navn ({label}, {name}): {unnamed}"

                # ---- 0. S2: oversikten ved åpning, detaljfila når en spot åpnes ----
                SNAP = """() => { const txt = el => el ? el.textContent.replace(/\\s+/g, ' ').trim() : null;
                  const snap = () => ({
                    ans: (b => b ? [b.tagName, b.className, b.dataset.spot || '', b.dataset.idx || '', b.getAttribute('aria-label') || '', txt(b)] : null)(document.getElementById('ansBtn')),
                    heads: [...document.querySelectorAll('#list .rows-head')].map(txt),
                    rows: [...document.querySelectorAll('#list .row')].map(r => [r.dataset.spot, r.className, r.getAttribute('aria-label'), r.querySelector('.rt').innerHTML, [...r.querySelectorAll('.wc')].map(w => w.className).join(' ')]),
                    mks: [...document.querySelectorAll('.mk')].map(m => [m.dataset.id, m.className, m.hidden, txt(m.querySelector('.mk-label')), m.getAttribute('aria-label')]),
                    edges: [...document.querySelectorAll('.mk-edge')].filter(e => !e.hidden).map(e => [e.dataset.id || '', e.className, txt(e.querySelector('.mk-label')), e.getAttribute('aria-label')]),
                    note: (n => n.hidden ? null : n.textContent)(document.getElementById('mapNote')),
                    pill: document.getElementById('timePillT').textContent, col: txt(document.getElementById('colNow')) });
                  const out = [], mx = Front.state.maxIdx;
                  for(const v of ['nord', 'lofoten', 'alle']){
                    document.querySelector(`.seg button[data-view='${v}']`).click();
                    for(let i = Front.state.w0; i <= mx; i += 7){ Front.setIdx(i); Front.refresh(); out.push([v, i, snap()]); }
                  }
                  document.querySelector(".seg button[data-view='nord']").click(); Front.backToNow();
                  return out; }"""
                snap_ov = page.evaluate(SNAP)
                n_det = sum(v for k, v in HOLD["count"].items() if k != "oversikt")
                assert HOLD["count"].get("oversikt") == 1 and n_det == 0, f"forsiden skal bare laste oversikten (én gang), ingen detaljfil: {HOLD['count']}"
                assert page.evaluate("DATA.spots.every(s => s._full === false && s.hours.length < 200)"), "oversikten har bare forsidens timer"
                # en spot som åpnes: «Henter detaljene …» (ingen tall, ingen kile) til detaljfila er her
                X = spots[2]["id"]
                HOLD["on"] = True
                page.evaluate(f"Front.openSpot('{X}')"); page.wait_for_timeout(500)
                assert [k for _, k in HOLD["routes"]] == [X], f"åpnet {X}: forventet nøyaktig én henting av dens detaljfil, fikk {[k for _, k in HOLD['routes']]}"
                ld = page.evaluate("({txt: (document.querySelector('#spot .spot-loading') || {}).textContent || null, tiles: !!document.querySelector('#spot #tHeight'), wedge: document.querySelectorAll('#wedgeG .wedge').length, n: document.querySelector('#spot .spot-head .n').textContent})")
                assert ld["txt"] == "Henter detaljene …" and not ld["tiles"] and ld["wedge"] == 0 and ld["n"] == spots[2]["name"], f"mens detaljfila hentes: navnet, ingen tall, ingen kile: {ld}"
                rt0, key0 = HOLD["routes"].pop(); HOLD["on"] = False
                rt0.fulfill(status=200, content_type="application/json", body=DET_BODY[key0])
                page.wait_for_function("!!document.querySelector('#spot #tHeight')")
                assert page.evaluate(f"DATA.spots.find(s => s.id === '{X}')._full") is True and page.evaluate(f"DATA.spots.find(s => s.id === '{X}').hours.length") == len(spots[2]["hours"])
                # detaljfila svarer med feil: arket sier det (ingen tall), «Prøv igjen» henter på nytt
                Y = spots[4]["id"]
                HOLD["fail"].add(Y); EXPECT_ERR["on"] = True
                page.evaluate("Front.go('home')"); page.wait_for_timeout(300)
                page.evaluate(f"Front.openSpot('{Y}')")
                page.wait_for_function("!!document.getElementById('retrySpot')")
                bad = page.evaluate("({txt: document.querySelector('#spot .spot-loading').textContent, tiles: !!document.querySelector('#spot #tHeight')})")
                assert bad["txt"].startswith("Fikk ikke hentet detaljene") and not bad["tiles"], f"feil i detaljfila: {bad}"
                page.wait_for_timeout(200); EXPECT_ERR["on"] = False
                page.locator("#retrySpot").click()
                page.wait_for_function("!!document.querySelector('#spot #tHeight')")
                page.evaluate("Front.go('home')"); page.wait_for_timeout(400)
                # nytt varsel publisert mens appen er åpen (detaljfila har et annet «run» enn oversikten):
                # siden lastes på nytt én gang - aldri tall fra to kjøringer blandet
                Z = spots[6]["id"]
                HOLD["newrun"].add(Z); EXPECT_ERR["on"] = True
                # vent på selve den nye lastingen («load»): expect_navigation ville også slått til på
                # adresseendringen (#/spot/<id>, replaceState) som openSpot gjør FØR detaljfila er hentet,
                # og en venting som så står midt i en ekte ny lasting kan tidsavbrytes (flakket 14.10.2026)
                with page.expect_event("load", timeout=ELEMENT_TIMEOUT_MS):
                    page.evaluate(f"Front.openSpot('{Z}')")
                page.wait_for_function("window.Front && document.querySelectorAll('.mk').length > 0")
                page.wait_for_timeout(600); EXPECT_ERR["on"] = False
                assert HOLD["count"]["oversikt"] == 2 and page.evaluate("sessionStorage.getItem('nordsurf.reloadFor')") == "annen-kjoring", f"annen kjøring i detaljfila: siden skal lastes på nytt én gang ({HOLD['count']})"
                # etter ny lasting åpnes spoten igjen fra adressen (#/spot/<id>) - nå med detaljfila fra samme kjøring
                try:
                    page.wait_for_function("!!document.querySelector('#spot #tHeight')")
                except Exception as e:   # noqa: BLE001 - diagnose: hva viste arket, og hva skjedde med hentingene?
                    diag = page.evaluate(f"""() => {{ const s = DATA.spots.find(x => x.id === '{Z}'); return {{state: {{mode: Front.state.mode, spot: Front.state.spotId}},
                        full: s._full, loadErr: s._loadErr || null, run: DATA.run, sheet: (document.getElementById('spot') || {{innerText: ''}}).innerText.replace(/\\s+/g, ' ').slice(0, 160),
                        reloadFor: sessionStorage.getItem('nordsurf.reloadFor'), hash: location.hash}}; }}""")
                    raise AssertionError(f"etter ny lasting kom ikke detaljene ({label}): {diag}; hentinger {HOLD['count']} {HOLD.get('log')}; feil {errors[-3:]}") from e
                after = page.evaluate(f"({{spot: Front.state.spotId, full: DATA.spots.filter(s => s._full !== false).map(s => s.id)}})")
                assert after == {"spot": Z, "full": [Z]}, f"etter ny lasting: {Z} åpen med detaljene, de andre bare oversikten: {after}"
                page.evaluate("Front.go('home')"); page.wait_for_timeout(400)
                if AXE_PATH:
                    page.add_script_tag(path=AXE_PATH)
                else:
                    page.add_script_tag(url=AXE_URL)
                page.wait_for_function("typeof axe !== 'undefined'")
                # alle spots fulle: forsiden skal se HELT lik ut som med bare oversikten
                assert page.evaluate("ensureAll().then(() => DATA.spots.every(s => s._full === true))")
                snap_full = page.evaluate(SNAP)
                if snap_ov != snap_full:
                    diff = next((a, b) for a, b in zip(snap_ov, snap_full) if a != b)
                    key = next(k for k in diff[0][2] if diff[0][2][k] != diff[1][2][k])
                    raise AssertionError(f"forsiden er ulik med bare oversikten og med hele varselet ({label}, {diff[0][0]}, time {diff[0][1]}, {key}):\n  oversikt: {diff[0][2][key]}\n  hele:     {diff[1][2][key]}")
                print(f"0 ({label}): forsiden lik med bare oversikten og med hele varselet ({len(snap_ov)} tilstander), bare oversikten lastet ved åpning, detaljfila ved åpnet spot - OK")

                st = page.evaluate("({w0: Front.state.w0, w3: Front.state.w3, maxIdx: Front.state.maxIdx})")
                w0, w3, max_idx = st["w0"], st["w3"], st["maxIdx"]
                region = {v: page.evaluate(f"[...Kart.viewSpotIds('{v}')]") for v in ("nord", "lofoten")}
                region["alle"] = [s["id"] for s in spots]

                # ---- 4a. arket starter i halv høyde (mobil), svarlinja og lista synlig uten å dra ----
                if mobile:
                    top = page.evaluate("document.getElementById('ark').getBoundingClientRect().top")
                    assert abs(top - vp[1] * 0.5) <= vp[1] * 0.04, f"arket skal starte i halv høyde (ca. {vp[1]*0.5:.0f} px), startet på {top:.0f} px"
                    assert page.evaluate("Front.state.mode") == "home" and page.evaluate("Front.state.sheet") == "half"
                    vis = page.evaluate("""() => { const H = innerHeight, a = document.getElementById('ansBtn').getBoundingClientRect();
                        const rows = [...document.querySelectorAll('#list .row')].filter(r => { const b = r.getBoundingClientRect(); return b.top >= 0 && b.bottom <= H; }).length;
                        return {ans: a.top >= 0 && a.bottom <= H, rows}; }""")
                    assert vis["ans"] and vis["rows"] >= 2, f"svarlinja og minst to rader skal synes uten å dra: {vis}"
                else:
                    a = page.evaluate("(() => { const p = document.getElementById('ark').getBoundingClientRect(), a = document.getElementById('ansBtn').getBoundingClientRect(), l = document.querySelector('#list .row').getBoundingClientRect(); return {p: p.top, a: a.top, l: l.top}; })()")
                    assert a["a"] - a["p"] < 40 and a["l"] > a["a"], f"panelet skal vise svarlinja øverst, så lista: {a}"

                # ---- 8. svarlinja på dagens data = speilet i Python ----
                def page_data():
                    return page.evaluate("DATA.spots.map(s => ({id: s.id, hours: s.hours.map(h => ({t: h.t, stars: h.stars, light: Kart.lightOf(h), surf_height: h.surf_height, low_reason: h.low_reason}))}))")
                def check_answer(view, favs=()):
                    data = page_data()
                    reg = [s for s in data if s["id"] in region[view]]
                    kind, ans = mirror_answer(reg, w0, w3, max_idx, set(favs))
                    info = page.evaluate("(() => { const b = document.getElementById('ansBtn'); return {tag: b.tagName, spot: b.dataset.spot || null, idx: b.dataset.idx ? +b.dataset.idx : null, text: b.textContent.replace(/\\s+/g, ' ').trim()}; })()")
                    area = "på noen spot" if view == "alle" else f"i {'Troms' if view == 'nord' else 'Lofoten'}"
                    if kind == "good":
                        sid, i, j, n = ans
                        name = next(s["name"] for s in spots if s["id"] == sid)
                        span = span_text(oslo(data[0]["hours"][i]["t"]), oslo(data[0]["hours"][j]["t"]))
                        assert info["tag"] == "BUTTON" and info["spot"] == sid and info["idx"] == i, f"svarlinja ({view}) valgte {info}, forventet {sid} time {i}"
                        assert info["text"].startswith("Neste gode økt") and name in info["text"] and span in info["text"], f"svarlinja ({view}) sier '{info['text']}', forventet {name} {span}"
                    else:
                        assert f"Ingen gode økter {area} de neste 3 dagene" in info["text"], f"svarlinja ({view}) sier '{info['text']}'"
                        gaps = mirror_gaps(reg, w0, w3, max_idx, len(data[0]["hours"]))
                        assert ("Noen timer mangler data" in info["text"]) == gaps, f"svarlinja ({view}) sier '{info['text']}' - forecast.json {'mangler' if gaps else 'mangler ikke'} data i vinduet"
                        if ans:
                            sid, i, _, _ = ans
                            name = next(s["name"] for s in spots if s["id"] == sid)
                            assert info["tag"] == "BUTTON" and info["spot"] == sid and info["idx"] == i and "Neste mulighet: " in info["text"] and name in info["text"], f"neste mulighet ({view}): {info}, forventet {sid} time {i}"
                        else:
                            assert info["tag"] == "DIV" and "Neste mulighet" not in info["text"], f"ingen stjerner i uka: svarlinja skal ikke peke noe sted ({view}): {info}"
                    return kind, ans
                for v in ("nord", "lofoten", "alle"):
                    page.evaluate(f"document.querySelector(\".seg button[data-view='{v}']\").click()"); page.wait_for_timeout(250)
                    check_answer(v)
                page.evaluate("document.querySelector(\".seg button[data-view='nord']\").click()"); page.wait_for_timeout(600)

                # ---- 8b. svarlinja med kjente timer (injisert) - tidligste gode time vinner ----
                page_bak = "window.__bak = DATA.spots.map(s => s.hours.map(h => ({stars: h.stars, surf_height: h.surf_height, low_reason: h.low_reason, light: h.light, daylight: h.daylight})))"
                page.evaluate(page_bak)
                restore = "DATA.spots.forEach((s, si) => s.hours.forEach((h, i) => Object.assign(h, __bak[si][i]))); Front.refresh();"
                nord = [s for s in spots if s["id"] in region["nord"]]
                def lys(s, lo, hi, n=1):
                    # første time i [lo, hi) der n timer på rad har brukbart lys
                    for i in range(lo, hi - n + 1):
                        if all(usable(s["hours"][i + k]) for k in range(n)): return i
                    return None
                def mørk(s, lo, hi):
                    return next((i for i in range(lo, hi) if s["hours"][i].get("light") == "mørkt"), None)
                A, B, C, D = nord[-1], nord[1], nord[0], nord[3]
                # en time der A har to lyse timer på rad og B er lys samme time
                hA = next((i for i in range(w0 + 14, w3 - 1) if usable(A["hours"][i]) and usable(A["hours"][i + 1]) and usable(B["hours"][i])), None)
                assert hA is not None, "fant ingen lyse timer de neste 3 dagene å teste svarlinja mot"
                hD = mørk(D, w0, hA)
                hC = lys(C, hA + 3, w3)
                hFar = lys(C, w3 + 1, max_idx + 1)
                setjs = lambda sid, i, n: f"(() => {{ const h = DATA.spots.find(s => s.id === '{sid}').hours[{i}]; h.stars = {n}; h.surf_height = {1.0 + n * 0.2}; h.low_reason = null; }})();"
                zero_nord = f"DATA.spots.forEach(s => {{ if({json.dumps(region['nord'])}.includes(s.id)) s.hours.forEach((h, i) => {{ if(i >= {w0}) {{ h.stars = 0; h.low_reason = 'flat'; h.surf_height = 0.1; }} }}); }});"
                page.evaluate(zero_nord + setjs(A["id"], hA, 3) + setjs(A["id"], hA + 1, 3) + setjs(B["id"], hA, 2)
                              + (setjs(C["id"], hC, 4) if hC else "") + (setjs(D["id"], hD, 5) if hD is not None else "")
                              + (setjs(C["id"], hFar, 5) if hFar else "") + "Front.refresh();")
                page.wait_for_timeout(500)
                kind, ans = check_answer("nord")
                assert kind == "good" and ans[0] == A["id"] and ans[1] == hA and ans[3] == 3, f"svarlinja skulle valgt {A['id']} kl. time {hA} (3 stjerner), valgte {ans}"
                # trykk: spoten åpnes på SAMME time, og kartet og pillen viser samme time
                page.evaluate("document.getElementById('ansBtn').click()"); page.wait_for_timeout(1300)
                opened = page.evaluate("({mode: Front.state.mode, spot: Front.state.spotId, idx: Front.state.idx, pill: document.getElementById('timePillT').textContent, head: document.querySelector('#spot .spot-head .s').textContent})")
                t_a = oslo(spots[0]["hours"][hA]["t"])
                wd = "I dag" if t_a.date() == TODAY else WD_SHORT[t_a.weekday()]
                assert opened["mode"] == "spot" and opened["spot"] == A["id"] and opened["idx"] == hA, f"trykk på svarlinja skal åpne {A['id']} på time {hA}: {opened}"
                assert opened["pill"] == f"{wd} {t_a.hour:02d}:00", f"tidspillen ({opened['pill']}) skal vise svarets time {wd} {t_a.hour:02d}:00"
                assert f"{t_a.hour:02d}:00" in opened["head"], f"spotarket ({opened['head']}) skal vise svarets time"
                mk = page.evaluate(f"(() => {{ const m = document.querySelector(\".mk[data-id='{A['id']}']\"); return {{bare: m.classList.contains('bare'), label: m.querySelector('.mk-label').textContent}}; }})()")
                assert not mk["bare"] and mk["label"] == f"{nf1(1.6)} m", f"kartmerket for {A['id']} skal vise samme time som svarlinja (1,6 m): {mk}"
                page.evaluate("Front.go('home')"); page.wait_for_timeout(300)
                page.evaluate("Front.backToNow()"); page.wait_for_timeout(300)
                # ingen god time de neste 72 t, men stjerner senere i uka: «Ingen surf …» + neste dag med stjerner
                page.evaluate(zero_nord + (setjs(C["id"], hFar, 1) if hFar else "") + "Front.refresh();"); page.wait_for_timeout(400)
                kind, ans = check_answer("nord")
                assert kind == "none" and (ans is not None) == bool(hFar), f"forventet «Ingen surf» med neste dag med stjerner: {kind} {ans}"
                # ingen stjerner i det hele tatt: ingen knapp
                page.evaluate(zero_nord + "Front.refresh();"); page.wait_for_timeout(400)
                kind, ans = check_answer("nord")
                assert kind == "none" and ans is None
                assert "mangler" not in page.locator("#ansBtn").text_content(), "alle timer har tall: svarlinja skal ikke si at noe mangler"
                shot("svar_ingen")
                # ---- 8c. grunnregelen: «Ingen surf …» er en påstand om hele vinduet ----
                G = nord[2]; hG = lys(G, w0 + 1, w3)
                assert hG is not None, "fant ingen lys time i vinduet å fjerne tallet fra"
                hours_of = f"DATA.spots.find(s => s.id === '{G['id']}').hours"
                # (a) en lys time uten tall: svarlinja sier at noen timer mangler data
                page.evaluate(f"(() => {{ const h = {hours_of}[{hG}]; h.stars = 0; h.low_reason = null; h.surf_height = null; Front.refresh(); }})()"); page.wait_for_timeout(300)
                kind, ans = check_answer("nord")
                txt = page.locator("#ansBtn").text_content()
                assert kind == "none" and "Noen timer mangler data" in txt, f"en lys time uten tall: svarlinja skal si at noen timer mangler data, sa '{txt}'"
                shot("svar_mangler")
                # (b) ukjent lys med 2 stjerner: ikke en god økt (lyset er ukjent), og heller ikke «ingen surf» uten forbehold
                page.evaluate(f"(() => {{ const h = {hours_of}[{hG}]; Object.assign(h, {{stars: 2, surf_height: 1.4, low_reason: null, light: null, daylight: null}}); Front.refresh(); }})()"); page.wait_for_timeout(300)
                kind, ans = check_answer("nord")
                assert kind == "none" and "Noen timer mangler data" in page.locator("#ansBtn").text_content(), "2 stjerner med ukjent lys: forbehold i svarlinja"
                # (c) ukjent lys med kjent 0 stjerner: ingen surf uansett lys - ikke noe forbehold
                page.evaluate(f"(() => {{ const h = {hours_of}[{hG}]; Object.assign(h, {{stars: 0, surf_height: 0.1, low_reason: 'flat'}}); Front.refresh(); }})()"); page.wait_for_timeout(300)
                kind, ans = check_answer("nord")
                assert kind == "none" and "mangler" not in page.locator("#ansBtn").text_content(), "ukjent lys, men kjent flatt: ingen grunn til forbehold"
                # (d) samme time mørk: teller ikke
                page.evaluate(f"(() => {{ const h = {hours_of}[{hG}]; Object.assign(h, {{stars: 0, low_reason: null, surf_height: null, light: 'mørkt', daylight: false}}); Front.refresh(); }})()"); page.wait_for_timeout(300)
                kind, ans = check_answer("nord")
                assert "mangler" not in page.locator("#ansBtn").text_content(), "en mørk time uten tall gjelder ikke svaret"
                page.evaluate(restore); page.wait_for_timeout(300)

                # ---- 9. kartet: lapp bare ved stjerner/favoritt/valgt, tekst når alt er 0 ----
                # alle spots flate fra nå (kjent utgangspunkt, uavhengig av dagens varsel)
                page.evaluate(f"DATA.spots.forEach(s => s.hours.forEach((h, i) => {{ if(i >= {w0}) {{ h.stars = 0; h.low_reason = 'flat'; h.surf_height = 0.1; }} }})); Front.refresh();")
                page.wait_for_timeout(500)
                idx = page.evaluate("Front.state.idx")
                note = page.evaluate("(() => { const n = document.getElementById('mapNote'); return n.hidden ? null : n.textContent; })()")
                assert note == "Flatt i hele Troms nå", f"alle spots i Troms er flate nå: teksten på kartet skal si «Flatt i hele Troms nå», sa {note!r}"
                labels = page.evaluate("[...document.querySelectorAll('.mk')].filter(m => !m.hidden).map(m => ({id: m.dataset.id, bare: m.classList.contains('bare'), pill: getComputedStyle(m.querySelector('.mk-pill')).display}))")
                assert labels and all(x["bare"] and x["pill"] == "none" for x in labels), f"flate spots skal ikke ha lapp: {labels}"
                assert page.locator(".lead").count() == 0, "ingen streker fra prikk til lapp"
                edges = page.evaluate("[...document.querySelectorAll('.mk-edge')].filter(e => !e.hidden).map(e => e.dataset.id || e.className)")
                assert not edges, f"kantpiler bare for spots med stjerner eller favoritter - alt er flatt nå, men fant {edges}"
                shot("kart_flatt")
                # tallet mangler for én spot: stiplet prikk og lappen «–», aldri den grå 0-prikken - og ingen påstand på kartet
                M = nord[-1]["id"]
                page.evaluate(f"(() => {{ const h = DATA.spots.find(s => s.id === '{M}').hours[{idx}]; h.stars = 0; h.low_reason = null; h.surf_height = null; Front.refresh(); }})()"); page.wait_for_timeout(800)   # prikkens bakgrunn toner over 0,4 s
                mm = page.evaluate(f"""(() => {{ const m = document.querySelector(".mk[data-id='{M}']"), d = getComputedStyle(m.querySelector('.mk-dot'));
                    const r = document.querySelector("#list .row[data-spot='{M}']");
                    return {{miss: m.classList.contains('miss'), bare: m.classList.contains('bare'), label: m.querySelector('.mk-label').textContent, border: d.borderTopStyle, bg: d.backgroundColor,
                             aria: m.getAttribute('aria-label'), note: document.getElementById('mapNote').hidden, row: r.querySelector('.rt .lb').textContent, rowAria: r.getAttribute('aria-label')}}; }})()""")
                assert mm["miss"] and not mm["bare"] and mm["label"] == "–", f"tallet mangler: merket skal ha lappen «–», ikke være en flat prikk: {mm}"
                alpha = float(mm["bg"].rstrip(")").split(",")[3]) if mm["bg"].startswith("rgba") else (0.0 if mm["bg"] == "transparent" else 1.0)
                assert mm["border"] == "dashed" and alpha <= 0.02, f"tallet mangler: stiplet, hul prikk - aldri den grå 0-prikken: {mm}"   # ≤ 0,02: toningens siste rest, ikke en grå prikk
                assert "tallet mangler" in mm["aria"] and "tallet mangler" in mm["rowAria"] and mm["row"] == "–", f"tallet mangler: skjermleseren og lista skal si det: {mm}"
                assert mm["note"], "et tall som mangler gir ingen «Flatt i hele …»-påstand på kartet"
                shot("kart_mangler")
                page.evaluate(f"(() => {{ const h = DATA.spots.find(s => s.id === '{M}').hours[{idx}]; h.stars = 0; h.low_reason = 'flat'; h.surf_height = 0.1; Front.refresh(); }})()"); page.wait_for_timeout(300)
                assert page.evaluate("document.getElementById('mapNote').textContent") == "Flatt i hele Troms nå"
                # «Bare smått» / «Ingen surf» / skjult når noen har stjerner
                small = f"(() => {{ const h = DATA.spots.find(s => s.id === '{nord[0]['id']}').hours[{idx}]; h.surf_height = 0.5; }})(); Front.refresh();"
                page.evaluate(small); page.wait_for_timeout(250)
                assert page.evaluate("document.getElementById('mapNote').textContent") == "Bare smått i hele Troms nå"
                page.evaluate(f"(() => {{ const h = DATA.spots.find(s => s.id === '{nord[1]['id']}').hours[{idx}]; h.low_reason = 'blown_out'; }})(); Front.refresh();"); page.wait_for_timeout(250)
                assert page.evaluate("document.getElementById('mapNote').textContent") == "Ingen surf i hele Troms nå"
                page.evaluate("document.querySelector(\".seg button[data-view='alle']\").click()"); page.wait_for_timeout(700)
                n_alle = page.evaluate("(() => { const n = document.getElementById('mapNote'); return n.hidden ? null : n.textContent; })()")
                assert n_alle is None or n_alle.endswith("på alle spots nå"), n_alle
                page.evaluate("document.querySelector(\".seg button[data-view='nord']\").click()"); page.wait_for_timeout(700)
                # én spot med stjerner: teksten forsvinner, den spoten får lapp, de flate ikke
                page.evaluate(setjs(nord[2]["id"], idx, 2) + "Front.refresh();"); page.wait_for_timeout(400)
                assert page.evaluate("document.getElementById('mapNote').hidden"), "teksten skal bort når en spot i utsnittet har stjerner"
                lab = page.evaluate(f"(() => {{ const m = document.querySelector(\".mk[data-id='{nord[2]['id']}']\"); return {{bare: m.classList.contains('bare'), text: m.querySelector('.mk-label').textContent}}; }})()")
                assert not lab["bare"] and lab["text"] == f"{nf1(1.4)} m", f"spot med stjerner skal ha lapp med høyden: {lab}"
                assert page.evaluate(f"document.querySelector(\".mk[data-id='{nord[3]['id']}']\").classList.contains('bare')"), "flat spot skal fortsatt være uten lapp"
                # lappen: navn og ord i Geist, bare tall i Geist Mono
                fonts = page.evaluate(f"(() => {{ const m = document.querySelector(\".mk[data-id='{nord[2]['id']}']\"); return {{label: getComputedStyle(m.querySelector('.mk-label')).fontFamily, num: getComputedStyle(m.querySelector('.mk-label .num')).fontFamily, name: getComputedStyle(m.querySelector('.mk-name')).fontFamily}}; }})()")
                first_family = lambda f: f.split(",")[0].strip().strip('"')
                assert first_family(fonts["label"]) == "Geist" and first_family(fonts["name"]) == "Geist" and first_family(fonts["num"]) == "Geist Mono", f"lappens skrift: {fonts}"
                # favoritt med 0 stjerner: lapp, og øverst i lista under «Favoritter»
                fav = nord[4]["id"]
                page.evaluate(f"Auth.state.favorites.add('{fav}'); Front.refresh();"); page.wait_for_timeout(400)
                assert not page.evaluate(f"document.querySelector(\".mk[data-id='{fav}']\").classList.contains('bare')"), "favoritt skal ha lapp selv med 0 stjerner"
                heads = page.evaluate("[...document.querySelectorAll('#list .rows-head .rh-l')].map(s => s.textContent)")
                first_row = page.evaluate("document.querySelector('#list .row').dataset.spot")
                assert heads == ["Favoritter", "Troms", "Andre områder"] and first_row == fav, f"favoritter øverst i lista: {heads}, første rad {first_row}"
                # kantpiler bare for stjerner/favoritter: utenfor Troms-utsnittet
                outside = [s for s in spots if s["id"] not in region["nord"]]
                for s in outside:
                    assert page.evaluate(f"document.querySelector(\".mk-edge[data-id='{s['id']}']\").hidden") or page.locator(".mk-edge.cluster:visible").count(), f"{s['id']} er flat og ikke favoritt - ingen kantpil"
                page.evaluate(setjs(outside[0]["id"], idx, 2) + "Front.refresh();"); page.wait_for_timeout(400)
                assert not page.evaluate(f"document.querySelector(\".mk-edge[data-id='{outside[0]['id']}']\").hidden"), f"{outside[0]['id']} har stjerner - skal ha kantpil"
                page.evaluate(f"Auth.state.favorites.add('{outside[-1]['id']}'); Front.refresh();"); page.wait_for_timeout(400)
                assert not page.evaluate(f"document.querySelector(\".mk-edge[data-id='{outside[-1]['id']}']\").hidden"), f"{outside[-1]['id']} er favoritt - skal ha kantpil"
                shot("kart_stjerner")
                edges_clear("Troms, stjerner og favoritt utenfor")
                if mobile:
                    ed = edges_on_edge("Troms, stjerner og favoritt utenfor")
                    assert len(ed) >= 2, f"to kantpiler (stjerner + favoritt) forventet: {ed}"
                page.evaluate(f"Auth.state.favorites.clear(); {restore}"); page.wait_for_timeout(500)

                # ---- 9b. lappene i alle tre utsnitt når ALLE har stjerner (tettest mulig) ----
                page.evaluate(f"DATA.spots.forEach(s => {{ const h = s.hours[{idx}]; h.stars = 2; h.surf_height = 1.2; h.low_reason = null; }}); Front.refresh();")
                for view in ("nord", "lofoten", "alle"):
                    page.locator(f".seg button[data-view='{view}']").click(); page.wait_for_timeout(1400)
                    lay = page.evaluate("""() => { const mks = [...document.querySelectorAll('.mk')].filter(m => !m.hidden);
                        const shown = mks.filter(m => !m.classList.contains('bare'));
                        const box = el => el.getBoundingClientRect();
                        const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
                        const gap = m => { const d = box(m.querySelector('.mk-dot')), p = box(m.querySelector('.mk-pill'));
                            return Math.hypot(Math.max(0, d.left - p.right, p.left - d.right), Math.max(0, d.top - p.bottom, p.top - d.bottom)); };
                        const ovl = []; shown.forEach(m => { const p = box(m.querySelector('.mk-pill')); mks.forEach(n => { if(n === m) return;
                            if(hit(p, box(n.querySelector('.mk-dot')))) ovl.push([m.dataset.id, 'prikk', n.dataset.id]);
                            if(!n.classList.contains('bare') && hit(p, box(n.querySelector('.mk-pill')))) ovl.push([m.dataset.id, 'lapp', n.dataset.id]); }); });
                        const dots = mks.map(m => { const d = box(m.querySelector('.mk-dot')); return {id: m.dataset.id, x: d.left + d.width/2, y: d.top + d.height/2}; });
                        const dist = (r, q) => Math.hypot(Math.max(r.left - q.x, 0, q.x - r.right), Math.max(r.top - q.y, 0, q.y - r.bottom));
                        const wrong = shown.filter(m => { const r = box(m.querySelector('.mk-pill')); const own = dist(r, dots.find(d => d.id === m.dataset.id));
                            return dots.some(d => d.id !== m.dataset.id && dist(r, d) <= own); }).map(m => m.dataset.id);
                        return {n: mks.length, shown: shown.length, far: shown.filter(m => gap(m) >= 12).map(m => m.dataset.id), ovl, wrong, pass: document.getElementById('markersLayer').dataset.pills}; }""")
                    assert lay["shown"] >= 1 and not lay["far"] and not lay["ovl"] and not lay["wrong"], f"lappene i utsnitt {view} ({label}): {lay}"
                    if not mobile and view != "alle":
                        assert lay["shown"] == lay["n"], f"PC har plass: alle {lay['n']} lapper skal vises i utsnitt {view}, viste {lay['shown']}"
                    overl = page.evaluate("""() => { const obs = [...document.querySelectorAll('.top-bar .icon-btn, .top-bar .seg, .top-bar .tctl, .legend, .map-note')].filter(e => !e.hidden && getComputedStyle(e).display !== 'none').map(e => e.getBoundingClientRect());
                        return [...document.querySelectorAll('.mk-edge')].filter(e => !e.hidden).map(e => e.getBoundingClientRect()).filter(r => obs.some(o => r.left < o.right && r.right > o.left && r.top < o.bottom && r.bottom > o.top)).length; }""")
                    assert overl == 0, f"{overl} kantpil(er) overlapper en knapp, pillen eller forklaringen i utsnitt {view}"
                    edges_clear(f"alle med stjerner, {view}")
                    if mobile:
                        edges_on_edge(f"alle med stjerner, {view}")
                    # klyngepil («N spots»): farge og etikett = beste rating i valgt time blant spotene i klynga
                    if page.locator(".mk-edge.cluster:visible").count():
                        info = page.evaluate("""() => { const c = document.querySelector('.mk-edge.cluster'); return {label: c.querySelector('.mk-label').textContent, cls: c.className}; }""")
                        assert info["label"] == "beste 2★" and "r-2" in info["cls"].split(), f"klyngepil: {info}"
                    if view == "alle":
                        shot("alle_tett")
                page.evaluate(restore); page.wait_for_timeout(300)
                page.locator(".seg button[data-view='nord']").click(); page.wait_for_timeout(1200)

                # ---- 10. ukeoversikten: riktig farge og bokstav per dag ----
                today = TODAY
                days = [(today + dt.timedelta(days=k)) for k in range(7)]
                def check_week(where):
                    data = page_data()
                    for s in data:
                        cells = page.evaluate(f"[...document.querySelectorAll(\"#list .row[data-spot='{s['id']}'] .wd\")].map(w => ({{day: w.dataset.day, cls: w.querySelector('.wc').className.replace('wc', '').trim(), letter: w.querySelector('b').textContent, today: w.classList.contains('today')}}))")
                        assert [c["day"] for c in cells] == [d.isoformat() for d in days], f"{s['id']}: dagene i ukeoversikten {[c['day'] for c in cells]}"
                        assert [c["letter"] for c in cells] == [DAY2[d.weekday()] for d in days], f"{s['id']}: dagsbokstaver {[c['letter'] for c in cells]}"
                        assert [c["today"] for c in cells] == [True] + [False] * 6, f"{s['id']}: bare dagens felt skal være markert {[c['today'] for c in cells]}"
                        exp = [day_best(s["hours"], w0, d.isoformat()) for d in days]
                        assert [c["cls"] for c in cells] == exp, f"{s['id']} ({where}): ukeoversikten {[c['cls'] for c in cells]}, forecast.json gir {exp}"
                check_week("dagens data")
                ring = page.evaluate("(() => { const w = [...document.querySelectorAll('#list .row')[0].querySelectorAll('.wd')]; return w.map(x => getComputedStyle(x.querySelector('.wc')).outlineStyle); })()")
                assert ring[0] == "solid" and all(r == "none" for r in ring[1:]), f"tynn ring rundt dagens felt, ingen andre: {ring}"
                if mobile:
                    # 390 px: navnene får plass, og dagsbokstavene overlapper ikke (alle rader, også «Andre områder»)
                    page.evaluate("Front.state.others = true; Front.refresh()"); page.wait_for_timeout(300)
                    fit = page.evaluate("""() => [...document.querySelectorAll('#list .row')].map(r => { const b = r.querySelector('.nm b');
                        const labs = [...r.querySelectorAll('.wd b')].map(x => x.getBoundingClientRect());
                        let ovl = 0; for(let i = 1; i < labs.length; i++) if(labs[i].left < labs[i-1].right) ovl++;
                        const row = r.getBoundingClientRect(), wk = r.querySelector('.week').getBoundingClientRect();
                        return {id: r.dataset.spot, trunc: b.scrollWidth > b.clientWidth + 0.5, ovl, inside: wk.left >= row.left && wk.right <= row.right, w: innerWidth}; })""")
                    bad = [f for f in fit if f["trunc"] or f["ovl"] or not f["inside"]]
                    assert fit and fit[0]["w"] == 390 and not bad, f"390 px: navn avkortet eller dagsbokstaver som overlapper: {bad}"
                    page.evaluate("Front.state.others = null; Front.refresh()"); page.wait_for_timeout(300)
                # kolonnetittelen «nå» over ratingen til høyre (første rad), høyrekant mot høyrekant
                cn = page.evaluate("(() => { const c = document.getElementById('colNow'), r = document.querySelector('#list .row .rt'); const a = c.getBoundingClientRect(), b = r.getBoundingClientRect(); return {text: c.textContent, dx: Math.abs(a.right - b.right), above: a.bottom <= b.top}; })()")
                assert cn["text"] == "nå" and cn["dx"] <= 2 and cn["above"], f"«nå» skal stå over ratingen i første rad: {cn}"
                # en dag der tallet mangler i alle lyse timer: stiplet ramme, aldri grå (0 stjerner)
                k_miss, sid = 4, spots[0]["id"]
                page.evaluate(f"(() => {{ const s = DATA.spots.find(x => x.id === '{sid}'); s.hours.forEach(h => {{ if(dayKey(new Date(h.t)) === '{days[k_miss].isoformat()}') {{ h.stars = 0; h.low_reason = null; h.surf_height = null; }} }}); Front.refresh(); }})()")
                page.wait_for_timeout(300)
                check_week("dag uten tall")
                bs = page.evaluate(f"getComputedStyle(document.querySelector(\"#list .row[data-spot='{sid}'] .wd[data-day='{days[k_miss].isoformat()}'] .wc\")).borderTopStyle")
                assert bs == "dashed", f"dag uten tall skal ha stiplet ramme, hadde {bs}"
                # en dag med stjerner i lyse timer: fargen etter beste rating
                page.evaluate(f"(() => {{ const s = DATA.spots.find(x => x.id === '{sid}'); const hs = s.hours.filter(h => dayKey(new Date(h.t)) === '{days[2].isoformat()}' && (h.light === 'dag' || h.light === 'skumring')); if(hs[0]) {{ hs[0].stars = 4; hs[0].surf_height = 1.5; hs[0].low_reason = null; }} Front.refresh(); }})()")
                page.wait_for_timeout(300)
                check_week("dag med 4 stjerner")
                # en dag der lyset er ukjent hele dagen (men tallene finnes og er 0): stiplet, aldri «mørkt» eller grå
                page.evaluate(f"(() => {{ const s = DATA.spots.find(x => x.id === '{sid}'); s.hours.forEach(h => {{ if(dayKey(new Date(h.t)) === '{days[5].isoformat()}') {{ h.light = null; h.daylight = null; h.stars = 0; h.low_reason = 'flat'; h.surf_height = 0.1; }} }}); Front.refresh(); }})()")
                page.wait_for_timeout(300)
                check_week("dag med ukjent lys")
                unk = page.evaluate(f"document.querySelector(\"#list .row[data-spot='{sid}'] .wd[data-day='{days[5].isoformat()}'] .wc\").className")
                assert "miss" in unk.split(), f"ukjent lys hele dagen skal være stiplet («mangler»), var '{unk}'"
                col = page.evaluate(f"getComputedStyle(document.querySelector(\"#list .row[data-spot='{sid}'] .wd[data-day='{days[2].isoformat()}'] .wc\")).backgroundColor")
                assert col == "rgb(45, 195, 211)", f"4 stjerner skal være turkis (#2DC3D3), var {col}"
                shot("uke")
                page.evaluate(restore); page.wait_for_timeout(400)
                # ---- 10b. lista følger regionvalget (Theodor 13.10.2026) ----
                # favoritter øverst uansett region, så spotene i regionen, så «Andre områder»
                # (lukket på mobil, åpen på PC); «Alle» som før. Hver gruppe: beste rating de
                # neste 3 dagene (lyse timer), så rekkefølgen i spots.json.
                data = page_data()
                def best3(s):
                    return max([(h.get("stars") or 0) for h in s["hours"][w0:w3] if usable(h) and known(h)] or [-1])
                def sorted_ids(ss):
                    return [s["id"] for s in sorted(ss, key=lambda s: -best3(s))]   # stabil sortering = spots.json ved likt
                def list_heads():
                    return page.evaluate("[...document.querySelectorAll('#list .rows-head')].map(h => ({label: h.querySelector('.rh-l').textContent, btn: h.tagName === 'BUTTON', open: h.getAttribute('aria-expanded')}))")
                def list_order():
                    return page.evaluate("[...document.querySelectorAll('#list .row')].map(r => r.dataset.spot)")
                for view, name in (("nord", "Troms"), ("lofoten", "Lofoten")):
                    page.locator(f".seg button[data-view='{view}']").click(); page.wait_for_timeout(900)
                    own = [x for x in data if x["id"] in region[view]]; oth = [x for x in data if x["id"] not in region[view]]
                    heads = list_heads()
                    assert [h["label"] for h in heads] == [name, "Andre områder"], f"lista i {view}: {heads}"
                    assert heads[1]["btn"] and heads[1]["open"] == ("false" if mobile else "true"), f"«Andre områder» skal være lukket på mobil og åpen på PC: {heads[1]}"
                    assert page.evaluate("document.getElementById('othersRows').hidden") == mobile
                    assert list_order() == sorted_ids(own) + sorted_ids(oth), f"rekkefølgen i {view}: {list_order()}, forventet {sorted_ids(own) + sorted_ids(oth)}"
                page.locator("#othersBtn").click(); page.wait_for_timeout(300)
                assert page.evaluate("document.getElementById('othersRows').hidden") != mobile and page.locator("#othersBtn").get_attribute("aria-expanded") == ("true" if mobile else "false"), "trykk på «Andre områder» åpner/lukker gruppa"
                page.locator("#othersBtn").click(); page.wait_for_timeout(300)
                page.locator(".seg button[data-view='alle']").click(); page.wait_for_timeout(900)
                assert [h["label"] for h in list_heads()] == ["Alle spots"] and page.locator("#othersBtn").count() == 0, f"«Alle»: alle spots sortert som før: {list_heads()}"
                assert list_order() == sorted_ids(data), f"«Alle»: {list_order()}, forventet {sorted_ids(data)}"
                page.locator(".seg button[data-view='nord']").click(); page.wait_for_timeout(900)
                fo = [x for x in data if x["id"] not in region["nord"]][0]["id"]
                page.evaluate(f"Auth.state.favorites.add('{fo}'); Front.refresh();"); page.wait_for_timeout(400)
                assert [h["label"] for h in list_heads()][:2] == ["Favoritter", "Troms"] and list_order()[0] == fo, f"en favoritt utenfor regionen skal stå øverst: {list_heads()}, {list_order()[:2]}"
                assert fo not in page.evaluate("[...document.querySelectorAll('#othersRows .row')].map(r => r.dataset.spot)"), "favoritten skal ikke også stå under «Andre områder»"
                shot("liste_favoritt")
                page.evaluate("Auth.state.favorites.clear(); Front.refresh();"); page.wait_for_timeout(400)

                # ---- 1. kart + liste ----
                page.evaluate("Front.go('home')")
                page.wait_for_timeout(1200)
                n_mk = page.locator(".mk:visible").count()
                assert n_mk >= 1, "ingen merker på kartet"
                shot("kart"); axe_check("kart"); buttons_ok("kart")
                # merkenes tekst = forecast.json for valgt time (lappen står i DOM også når den er skjult)
                idx = page.evaluate("Front.state.idx")
                for s in spots:
                    h = s["hours"][idx]
                    lab = page.locator(f"[data-id='{s['id']}'] .mk-label").first.text_content()
                    exp = f"{nf1(h['surf_height'])} m" if h["stars"] >= 1 and h.get("surf_height") is not None else None
                    if exp is not None:
                        assert lab == exp, f"merket for {s['id']} sier '{lab}', forecast.json sier '{exp}'"
                    else:
                        assert lab == word_of(h, s), f"merket for {s['id']} skal ha ordet «{word_of(h, s)}», hadde '{lab}'"
                    bare = page.evaluate(f"document.querySelector(\".mk[data-id='{s['id']}']\").classList.contains('bare')")
                    hidden = page.evaluate(f"document.querySelector(\".mk[data-id='{s['id']}']\").hidden")
                    if not hidden and not h["stars"] and known(h):
                        assert bare, f"{s['id']} har 0 stjerner nå - prikk uten lapp"
                    if not hidden and not known(h):
                        assert page.evaluate(f"document.querySelector(\".mk[data-id='{s['id']}']\").classList.contains('miss')"), f"tallet mangler for {s['id']} - stiplet prikk, ikke 0-prikken"
                page.evaluate("Front.go('list')"); page.wait_for_timeout(900)
                assert page.locator("#list .row").count() == len(spots), "lista skal ha én rad per spot"
                shot("liste"); axe_check("liste"); buttons_ok("liste")

                # ---- 4b. arket dras med fingeren (mobil): liste ↔ halv ↔ kart ----
                if mobile:
                    def drag(dy):
                        hb = page.locator(".ark-handle").bounding_box()
                        y0 = hb["y"] + hb["height"] / 2; x0 = hb["x"] + hb["width"] / 2
                        page.mouse.move(x0, y0); page.mouse.down()
                        for k in range(1, 9):
                            page.mouse.move(x0, y0 + k * dy / 8)
                        page.mouse.up(); page.wait_for_timeout(900)
                    page.evaluate("Front.go('half')"); page.wait_for_timeout(900)
                    drag(-320)
                    assert page.evaluate("Front.state.sheet") == "full", "å dra arket opp fra halv høyde skal gi mer liste"
                    drag(320)
                    assert page.evaluate("Front.state.sheet") == "half", "å dra arket ned fra lista skal gi halv høyde"
                    drag(300)
                    assert page.evaluate("Front.state.sheet") == "map", "å dra arket ned fra halv høyde skal gi mer kart"
                    vis = page.evaluate("(() => { const a = document.getElementById('ansBtn').getBoundingClientRect(); return a.top >= 0 && a.bottom <= innerHeight; })()")
                    assert vis, "svarlinja skal synes også når arket er dratt ned for mer kart"
                    shot("kart_mer")
                    assert page.evaluate("Front.state.mode") == "home"
                    # områdevalg: kartmodus står, lista i full høyde senkes til halv (så det nye området synes)
                    page.locator(".seg button[data-view='nord']").click(); page.wait_for_timeout(700)
                    assert page.evaluate("Front.state.sheet") == "map", "områdevalg i kartmodus skal la arket stå nede"
                    page.evaluate("Front.go('list')"); page.wait_for_timeout(700)
                    page.locator(".seg button[data-view='nord']").click(); page.wait_for_timeout(900)
                    assert page.evaluate("Front.state.sheet") == "half", "områdevalg fra lista i full høyde skal senke arket til halv høyde"
                    page.evaluate("Front.go('half')"); page.wait_for_timeout(900)

                # ---- 11. tiden: pille, panel, «Tilbake til nå» ----
                back_sel = "#backNowM" if mobile else "#backNow"
                assert page.locator("#timePillT").text_content() == "Nå" and page.locator(back_sel).is_hidden(), "på nåtimen: pillen sier «Nå», ingen «Tilbake til nå»"
                assert page.locator("#timePanel").is_hidden(), "glidebryteren og play er skjult til pillen trykkes"
                page.locator("#timePill").click(); page.wait_for_timeout(400)
                assert page.locator("#timePanel").is_visible() and page.locator("#play").is_visible() and page.locator("#tid").is_visible(), "trykk på pillen åpner glidebryter og play"
                assert page.locator("#timePill").get_attribute("aria-expanded") == "true"
                now_h = page.evaluate("document.getElementById('timeNow').getBoundingClientRect().height")
                assert now_h <= 22, f"«Nå»-merket er {now_h} px høyt, skal være ca. 20"
                shot("tid")
                page.evaluate(f"Front.setIdx({w0 + 30})"); page.wait_for_timeout(300)
                t30 = oslo(spots[0]["hours"][w0 + 30]["t"])
                wd = "I dag" if t30.date() == TODAY else WD_SHORT[t30.weekday()]
                assert page.locator("#timePillT").text_content() == f"{wd} {t30.hour:02d}:00", page.locator("#timePillT").text_content()
                assert page.locator("#colNow").text_content() == f"{wd.lower()} {t30.hour:02d}:00", f"kolonnetittelen skal følge tiden: {page.locator('#colNow').text_content()}"
                page.keyboard.press("Escape"); page.wait_for_timeout(300)
                assert page.locator("#timePanel").is_hidden(), "Escape lukker tidspanelet"
                assert page.locator(back_sel).is_visible(), "tiden står ikke på nå: «Tilbake til nå» skal synes"
                assert page.locator(back_sel).text_content().strip() == "Tilbake til nå"
                shot("tilbake")
                axe_check("tilbake"); buttons_ok("tilbake")
                page.locator(back_sel).click(); page.wait_for_timeout(400)
                assert page.evaluate("Front.state.idx") == w0 and page.locator("#timePillT").text_content() == "Nå" and page.locator(back_sel).is_hidden(), "«Tilbake til nå» setter tiden til nå"
                assert page.locator("#colNow").text_content() == "nå"

                # ---- 12. animasjon bare der det er noe å vise ----
                assert page.evaluate("getComputedStyle(document.getElementById('windLayer')).opacity") == "0", "vindstrekene skal ikke vises før en spot er valgt"
                still = page.evaluate("""() => [...document.querySelectorAll('.mk.r-0 .rip, #list .row')].filter(el => getComputedStyle(el).animationName !== 'none').length""")
                assert still == 0, f"{still} flate merker eller listerader animeres"

                # ---- 13. ny time mens appen står åpen / kommer fra bakgrunnen ----
                sc0 = page.evaluate("(() => { const sc = document.querySelector('#ark .ark-scroll'); sc.scrollTop = 40; return sc.scrollTop; })()")
                page.evaluate(f"window.__ch = currentHour; window.currentHour = () => {w0 + 1}; document.dispatchEvent(new Event('visibilitychange'))"); page.wait_for_timeout(400)
                t1 = page.evaluate("({w0: Front.state.w0, idx: Front.state.idx, pill: document.getElementById('timePillT').textContent, sc: document.querySelector('#ark .ark-scroll').scrollTop})")
                assert t1["w0"] == w0 + 1 and t1["idx"] == w0 + 1 and t1["pill"] == "Nå", f"ny time: vinduet og «Nå» skal følge nåtimen: {t1}"
                assert abs(t1["sc"] - sc0) <= 1, f"ny time: lista skal beholde scrollen ({sc0} → {t1['sc']})"
                page.evaluate(f"Front.setIdx({w0 + 10}); window.currentHour = () => {w0 + 2}; document.dispatchEvent(new Event('visibilitychange'))"); page.wait_for_timeout(400)
                t2 = page.evaluate("({w0: Front.state.w0, idx: Front.state.idx})")
                assert t2 == {"w0": w0 + 2, "idx": w0 + 10}, f"ny time: en tid brukeren har flyttet til, skal bli stående: {t2}"
                page.evaluate("window.currentHour = window.__ch; Front.backToNow(); document.dispatchEvent(new Event('visibilitychange'))"); page.wait_for_timeout(400)
                assert page.evaluate("({w0: Front.state.w0, idx: Front.state.idx})") == {"w0": w0, "idx": w0}
                page.evaluate("document.querySelector('#ark .ark-scroll').scrollTop = 0")

                # ---- 2 + 3. spot ----
                s = spots[bi]; h = s["hours"][bidx]
                page.evaluate(f"Front.openSpot('{s['id']}', {bidx})"); page.wait_for_timeout(1500)
                assert page.evaluate("Front.state.mode") == "spot"
                if h.get("wind_speed") is not None and h.get("wind_dir") is not None:
                    assert float(page.evaluate("getComputedStyle(document.getElementById('windLayer')).opacity")) > 0, "vindstrekene vises når en spot er valgt"
                assert not page.evaluate(f"document.querySelector(\".mk[data-id='{s['id']}']\").classList.contains('bare')") or page.evaluate(f"document.querySelector(\".mk[data-id='{s['id']}']\").hidden"), "valgt spot skal ha lapp"
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
                    assert pv.startswith(f"{r0(h['period'])} s"), f"periode-flisa ({pv}) stemmer ikke ({h['period']})"
                kj = h.get("energy_swell_kj") if h.get("swell_offshore") is not None else h.get("energy_total_kj")
                if kj:
                    kv = page.locator("#tKjSmall" if mobile else "#tKj .v").text_content()
                    assert "kJ" in kv and f"{r0(kj):,}".replace(",", " ") in kv.replace(" ", " ").replace(" ", " "), f"energi-flisa ({kv}) stemmer ikke ({kj})"
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
                    # Logg-knappen står ved favorittstjerna i spotpanelet på PC
                    lb, fb = page.locator("#spot #logBtn").bounding_box(), page.locator("#spot .spot-head .fav-btn").bounding_box()
                    assert lb and fb and abs(lb["y"] - fb["y"]) < 20, "Logg-knappen skal stå ved favorittstjerna i hodet (PC)"
                    # ingen tekst flyter over i flisene ved 1024 og 1440 px (også med lang høydetekst)
                    for w in (1024, 1440):
                        page.set_viewport_size({"width": w, "height": 900}); page.wait_for_timeout(400)
                        page.evaluate("""() => { const h = DATA.spots[0].hours[0]; window.__bak1 = {...h};
                            Object.assign(h, {surf_height: 1.3, surf_height_sets: 1.7, stars: 3, low_reason: null, period: 14, swell_offshore: 2.0, energy_swell_kj: 1234}); Front.openSpot(DATA.spots[0].id, 0); }""")
                        page.wait_for_timeout(500)
                        hv = page.locator("#tHeight .v").text_content()
                        assert "1,3–1,7 m" in hv, f"høydeflisa skal si «1,3–1,7 m», sa '{hv}'"
                        over = page.evaluate("""() => [...document.querySelectorAll('#spot .tile .v, #spot .tile')].filter(e => e.scrollWidth > e.clientWidth + 1).length""")
                        assert over == 0, f"{over} flise(r) flyter over ved {w} px"
                        page.evaluate("() => { Object.assign(DATA.spots[0].hours[0], window.__bak1); }")
                    page.set_viewport_size({"width": vp[0], "height": vp[1]})
                    page.evaluate(f"Front.openSpot('{s['id']}', {bidx})"); page.wait_for_timeout(800)
                assert page.locator("#bars .hbar").count() == min(48, len(s["hours"])), "48 søyler i spotarket"
                shot("spot"); axe_check("spot"); buttons_ok("spot")
                # søyler for mørke timer er synlige og kan trykkes (kartets nattlag-regel traff dem før: opacity 0, pointer-events none)
                nb = page.evaluate("[...document.querySelectorAll('#bars .hbar.night')].map(b => getComputedStyle(b).opacity + '/' + getComputedStyle(b).pointerEvents)")
                assert all(x == "1/auto" for x in nb), f"søyler for mørke timer skal synes og kunne trykkes: {sorted(set(nb))}"
                # søyle-trykk velger time
                bar = page.locator("#bars .hbar").nth(5); want = int(bar.get_attribute("data-i"))
                bar.click(); page.wait_for_timeout(300)
                assert page.evaluate("Front.state.idx") == want, f"trykk på en søyle skal velge timen (ville {want}, fikk {page.evaluate('Front.state.idx')})"
                page.evaluate(f"Front.setIdx({bidx})")
                # Detaljer åpen: Retningstreff = directness
                page.evaluate("document.getElementById('details').open = true"); page.wait_for_timeout(300)
                if dn is not None:
                    rt = page.locator("#details .cell:has-text('Retningstreff') >> .v").inner_text()
                    assert rt == f"{r0(dn*100)} %", f"Retningstreff ({rt}) stemmer ikke med directness ({dn})"
                shot("spot_detaljer")
                # flat spot
                page.evaluate(f"Front.openSpot('{spots[fi]['id']}', 0)"); page.wait_for_timeout(1300)
                fh = spots[fi]["hours"][0]
                if not fh["stars"]:
                    w = page.locator("#spot .rating-line .word").text_content()
                    assert w and not w.endswith(".") and page.locator("#spot .rating-line .stars").count() == 0, "0 stjerner: ordet alene, ingen stjerner, ikke punktum"
                    # surfehøyde-flisa sier ordet («Flatt»), aldri «–» (som betyr at tallet mangler)
                    hv = page.locator("#tHeight .v").text_content().strip()
                    if fh.get("low_reason") == "flat" or (fh.get("surf_height") is not None and fh["surf_height"] <= 0 and not fh.get("low_reason")):
                        assert hv == word_of(fh, spots[fi]), f"flat spot skal vise «{word_of(fh, spots[fi])}» i høydeflisa, viste '{hv}'"
                    assert hv != "–" or fh.get("surf_height") is None, "«–» skal bare bety at tallet mangler"
                    i0 = page.evaluate("Front.state.w0")
                    if all((x.get("stars") or 0) == 0 for x in spots[fi]["hours"][i0:i0+48]):
                        assert page.locator("#bars.compact").count() == 1 and page.locator("#bars .flat-lbl").count() == 1, "alle 48 timer 0 stjerner: kompakt visning med tekst"
                        lbl = page.locator("#bars .flat-lbl").text_content()
                        assert lbl.split()[0] in ("Flatt", "Smått", "Ingen"), lbl
                        assert page.locator("#bars.compact .d").count() == 0, "kompakt graf skal ikke ha dagnavn"
                shot("spot_flat"); axe_check("spot_flat")
                # ordet ved 0 stjerner med grunn flat (Theodors ja 09.10.2026, tre runder): under
                # 0,3 m «Flatt», 0,3 til under 0,8 m «Smått»; fra 0,8 m følger ordet det som trekker
                # mest (Grøtete / Blåst ut / Feil tidevann / For lite svell / Ikke surfbart nå) - i
                # rating, lapp, liste og forklaringen bak ratingen (trykk). Bare ordet, ikke stjernene.
                i0 = page.evaluate("Front.state.w0")
                MAGNUS = "Magnus, lokal surfer (Molde)"
                base = {"surf_height_sets": None, "stars": 0, "faded": 0, "faded_wind": 0, "faded_tide": 0, "zero_losses": {"energy": 0, "wind": 0, "tide": 0, "local": 0, "cap": 0}, "low_reason": "flat", "local_rules": None, "period": 11, "sources_disagree": False}
                OBS = "Observasjoner 26.09-05.10.2026"
                Z = lambda **k: {"energy": 0, "wind": 0, "tide": 0, "local": 0, "cap": 0, **k}
                CASES = [
                    ({"surf_height": 0.5}, "Smått", "for lite til en stjerne", None),
                    ({"surf_height": 0.3}, "Smått", None, None),
                    ({"surf_height": 0.29}, "Flatt", None, None),
                    ({"surf_height": 0.79}, "Smått", None, None),
                    ({"surf_height": 0.0}, "Flatt", None, None),
                    ({"surf_height": 1.0, "period": 7}, "Grøtete", "kort periode og lite energi gjør dem svake", None),
                    ({"surf_height": 0.8, "period": 8.9, "zero_losses": Z(wind=3)}, "Grøtete", "kort periode", None),
                    ({"surf_height": 1.0, "zero_losses": Z(energy=2, wind=1)}, "Grøtete", "for lite energi i svellet til å gi kraft", None),
                    ({"surf_height": 1.0, "zero_losses": Z(wind=2, energy=1)}, "Blåst ut", "vinden", None),
                    ({"surf_height": 1.0, "zero_losses": Z(tide=2, wind=1)}, "Feil tidevann", "tidevannet passer ikke", None),
                    ({"surf_height": 1.0, "zero_losses": Z(energy=1, local=2), "local_rules": {"source": MAGNUS, "stars_lost": 2, "lines": ["Tidevann (høy): ikke blant det lokale favoriserer - −1 stjerne (vektet −0.7)"]}}, "Feil tidevann", "Ifølge Magnus, lokal surfer: tidevann (høy)", None),
                    ({"surf_height": 1.0, "zero_losses": Z(local=1), "local_rules": {"source": MAGNUS, "stars_lost": 1, "lines": ["Tidevann (lav): foretrukket lokalt, ingen straff", "Vind 5 m/s sidevind: strengere lokal grense (over 4 m/s) - −1 stjerne (vektet −0.7)"]}}, "Blåst ut", "Ifølge Magnus, lokal surfer: Grøtfjord trenger offshore. Nå 5 m/s sidevind.", None),
                    ({"surf_height": 1.0, "zero_losses": Z(energy=2, local=1), "local_rules": {"source": MAGNUS, "stars_lost": 1, "lines": ["Vind 5 m/s sidevind: strengere lokal grense (over 4 m/s) - −1 stjerne (vektet −0.7)"]}, "energy_swell_kj": 601}, "For lite svell", "Ifølge Magnus, lokal surfer: for lite svellenergi ute (601 kJ, full uttelling fra 3 000 kJ)", {"min_energy_kj": {"full": 3000, "zero": 1500}, "source": MAGNUS, "weight": 0.7}),
                    ({"surf_height": 1.0, "zero_losses": Z(energy=1), "local_rules": {"source": OBS, "stars_lost": 0, "lines": []}, "energy_swell_kj": 166}, "For lite svell", "Grense satt ut fra observasjonene 26.09 til 05.10: for lite svellenergi ute (166 kJ, full uttelling fra 400 kJ)", {"min_energy_kj": {"full": 400, "zero": 200}, "source": OBS, "weight": 0.7}),
                    ({"surf_height": 1.0, "zero_losses": Z(energy=1, wind=1)}, "Ikke surfbart nå", "hovedårsak", None),
                    ({"surf_height": 1.0}, "Ikke surfbart nå", "for lite til en stjerne", None),
                    ({"surf_height": 1.0, "zero_losses": None, "faded_wind": 2}, "Blåst ut", "vinden", None),
                    ({"surf_height": 1.0, "zero_losses": Z(energy=1, cap=2)}, "Ikke surfbart nå", "kappet", None),
                    ({"surf_height": 1.0, "zero_losses": Z(energy=1, wind=1, cap=2), "sources_disagree": True}, "Usikkert", "Kildene er uenige om svellet når inn til spoten.", None),
                    ({"surf_height": 1.0, "zero_losses": Z(local=2), "local_rules": {"source": MAGNUS, "stars_lost": 2, "lines": ["Tidevann (høy): ikke blant det lokale favoriserer - −1 stjerne (vektet −0.7)", "Vind 5 m/s sidevind: strengere lokal grense (over 4 m/s) - −1 stjerne (vektet −0.7)"]}}, "Ikke surfbart nå", "hovedårsak", None),
                ]
                for fields, word, exp_note, spot_rules in CASES:
                    inj = dict(base); inj.update(fields)
                    spot_copy = dict(spots[0]); spot_copy["local_rules"] = spot_rules
                    assert word_of(dict(spots[0]["hours"][i0], **inj), spot_copy) == word, f"testens eget speil er uenig for {fields}"
                    page.evaluate(f"""() => {{ const s = DATA.spots[0], h = s.hours[{i0}]; window.__bak2 = {{...h}}; window.__bakR = s.local_rules;
                        s.local_rules = {json.dumps(spot_rules)}; Object.assign(h, {json.dumps(inj, ensure_ascii=False)}); Front.openSpot(s.id, {i0}); }}""")
                    page.wait_for_timeout(450)
                    rw = page.locator("#spot .rating-line .word").text_content().strip()
                    assert rw == word, f"{fields}: ratingordet skal være «{word}», var '{rw}'"
                    if exp_note and spots[0]["hours"][i0].get("breakdown"):
                        page.locator("#spot #bdOpen").click(); page.wait_for_timeout(300)
                        note = page.locator("#bdBody .bd-note").text_content().replace(" ", " ").replace(" ", " ")
                        assert note.startswith(word) and exp_note in note, f"forklaringen ved trykk skal forklare «{word}» ({exp_note}), sa '{note}'"
                        assert not ("Ifølge Observasjoner" in note or "Ifølge observasjon" in note), f"en kilde som ikke er en person skal ikke skrives som en person: '{note}'"
                        page.evaluate("closeBreakdown()"); page.wait_for_timeout(200)
                    ml = page.locator(f"[data-id='{spots[0]['id']}'] .mk-label").first.text_content().strip()
                    assert ml == word, f"{fields}: lappen på kartet skal si «{word}», sa '{ml}'"
                    page.evaluate("Front.go('list')"); page.wait_for_timeout(450)
                    lw = page.locator(f"#list .row[data-spot='{spots[0]['id']}'] .rt .lb").text_content().strip()
                    assert lw == word, f"{fields}: lista skal si «{word}», sa '{lw}'"
                    page.evaluate(f"() => {{ const s = DATA.spots[0]; Object.assign(s.hours[{i0}], window.__bak2); s.local_rules = window.__bakR; }}")
                page.evaluate(f"Front.openSpot('{spots[fi]['id']}', 0)"); page.wait_for_timeout(600)

                # ---- loggark og forklaring ----
                page.evaluate(f"Front.openSpot('{s['id']}', {bidx}); openSheet('{s['id']}', new Date())"); page.wait_for_timeout(700)
                assert page.locator("#sheet #logFromPhotoBtn").count() == 1
                tt = page.locator("#logTimeText").inner_text(); assert "kl." in tt and "PM" not in tt
                shot("logg"); axe_check("logg")
                # S2: lagret logg tar med varselets tall for timen fra spotens detaljfil (slått opp på tidspunktet)
                n_logs = page.evaluate("loadLogs().length")
                page.evaluate("document.querySelector('#starPick button[data-n=\"3\"]').click()")
                page.locator("#saveLog").click(); page.wait_for_timeout(600)
                saved = page.evaluate("loadLogs()")
                assert len(saved) == n_logs + 1, f"loggen skal være lagret ({n_logs} -> {len(saved)})"
                e = saved[-1]
                hk = next(x for x in s["hours"] if x["t"] == e["t"][:13] + ":00Z")
                assert e["spot"] == s["id"] and e["stars"] == 3, f"lagret logg: {e}"
                for k_log, k_fc in (("forecastPeriod", "period"), ("directness", "directness"), ("energySwellKj", "energy_swell_kj"), ("dirOffshore", "dir_offshore")):
                    assert e.get(k_log) == hk.get(k_fc), f"loggens {k_log} ({e.get(k_log)}) skal være varselets {k_fc} for timen ({hk.get(k_fc)})"
                page.evaluate(f"saveLogs(loadLogs().slice(0, {n_logs}))")   # testloggen ut igjen
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
                assert page.evaluate("Front.state.mode") == "home"

                # ---- 5. avspilling (fra tidspanelet) ----
                page.evaluate("Front.backToNow()"); page.wait_for_timeout(200)
                i0 = page.evaluate("Front.state.idx")
                page.locator("#timePill").click(); page.wait_for_timeout(300)
                page.locator("#play").click(); page.wait_for_timeout(1300)
                assert page.evaluate("Front.state.playing") is True
                i1 = page.evaluate("Front.state.idx"); assert i1 != i0, "avspilling skal flytte tiden"
                page.locator("#play").click(); page.wait_for_timeout(300)
                assert page.evaluate("Front.state.playing") is False
                page.keyboard.press("Escape"); page.wait_for_timeout(200)
                page.evaluate("Front.backToNow()"); page.wait_for_timeout(200)
                # regionvalg
                page.locator(".seg button[data-view='lofoten']").click(); page.wait_for_timeout(1300)
                assert page.locator(".seg button[data-view='lofoten']").get_attribute("aria-pressed") == "true"
                check_answer("lofoten")
                shot("lofoten")
                page.locator(".seg button[data-view='alle']").click(); page.wait_for_timeout(1300)
                check_answer("alle")
                shot("alle")
                ctx.close()

            # ---- 7. prefers-reduced-motion ----
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark", reduced_motion="reduce", is_mobile=True, has_touch=True)
            page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS); route(page)
            page.clock.set_fixed_time(T0)
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
    print("0: S2 - forsiden lik med bare oversikten og med hele varselet; detaljfila hentes når en spot åpnes («Henter detaljene …», feil med «Prøv igjen»)")
    print("1: kart, merker, kantpiler, ark/panel, loggark, forklaring, Logger og Innstillinger rendres uten JavaScript-feil (mobil og PC)")
    print("2: merker, stjerner, surfehøyde, periode, energi og Retningstreff er forecast.json sine tall")
    print("3: svellkilen klassifiseres bare fra h.directness, bølgefronter bare ved treff/kant")
    print("4: arket på mobil starter i halv høyde med svarlinja og lista synlig, og dras mellom liste, halv og kart")
    print("5: avspilling ruller tiden, regionvalg virker")
    print("6: axe color-contrast: ingen brudd, alle knapper minst 44 px med tilgjengelig navn")
    print("7: prefers-reduced-motion skrur av animasjonene")
    print("8: svarlinja velger tidligste gode time i området (speilet i Python), og trykk åpner spoten på samme time som kartet")
    print("9: flate spots har ingen lapp, ingen streker, kantpiler bare for stjerner/favoritter (på mobil langs kanten av kartet), tekst når hele utsnittet er 0 stjerner")
    print("10: ukeoversikten har riktig farge og to bokstaver per dag, ring rundt i dag, stiplet når tallet mangler, får plass på 390 px; kolonnetittelen «nå»")
    print("10b: lista følger regionvalget - favoritter øverst, så regionen, så «Andre områder» (lukket på mobil, åpen på PC); «Alle» som før")
    print("11: tidspillen («Nå»/«Tor 17:00») åpner glidebryter og play, «Tilbake til nå» når tiden ikke står på nå")
    print("12: vindstrekene bare ved valgt spot, flate merker og listerader står stille")
    print("13: ny time: svarlinja, uka og «Nå» følger nåtimen, en flyttet tid blir stående")
    print("grunnregelen: tall som mangler gir stiplet prikk og «–» på kartet, forbehold i svarlinja og stiplet dag i uka - aldri 0")
    print("Alle tester ok")


if __name__ == "__main__":
    main()
