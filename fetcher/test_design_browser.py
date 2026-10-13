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
   favoritt, ved samme time), ellers «Ingen surf de neste 3 dagene i …» og
   neste dag med stjerner - og trykk åpner spoten på SAMME time som kartet viser;
   mangler noen timer data i vinduet, sier svarlinja det (grunnregelen);
9. flate spots (0 stjerner) har ingen lapp på kartet - bare spots med
   stjerner, favoritter og valgt spot; ingen streker fra prikk til lapp;
   kantpiler bare for stjerner og favoritter; én tekst på kartet når hele
   utsnittet er 0 stjerner; en spot der tallet MANGLER er aldri den grå
   0-prikken (stiplet prikk og lappen «–»);
10. ukeoversikten har riktig farge per dag (beste rating i lyse timer, grå
    for 0, stiplet når tallet mangler eller lyset er ukjent) og riktige
    dagsbokstaver;
11. tiden er en pille («Nå» / «Tor 17:00»), trykk åpner glidebryter og play,
    og «Tilbake til nå» vises når tiden ikke står på nå;
12. vindstrekene vises bare når en spot er valgt, og flate merker og
    listerader animeres ikke;
13. når nåtimen flytter seg (appen står åpen / kommer fra bakgrunnen), følger
    svarlinja, uka og «Nå» med - en tid brukeren har flyttet til, blir stående.

Skjermbildene lagres i docs/design/oversikt/etter/ (mobil og PC).

Tidsgrenser (CLAUDE.md): hvert Playwright-steg maks 15 s, hele fila maks 5
minutter (hardkill), testserveren stoppes uansett utfall.

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
LETTERS = "MTOTFLS"   # mandag ... søndag
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
    day = "i dag" if e.date() == dt.datetime.now(OSLO).date() else WD_SHORT[e.weekday()].lower()
    return f"{a.hour:02d}–{day} {end}"


def main():
    watchdog = _watchdog()
    srv, port = serve()
    forecast = json.loads((DOCS / "data" / "forecast.json").read_text(encoding="utf-8"))
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
                    small = page.evaluate("""() => [...document.querySelectorAll('button')].filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.width < 43.5 || r.height < 43.5) && !b.closest('.hbar') && !b.classList.contains('hbar') && !b.classList.contains('tap') && !b.closest('.mk-pill'); }).map(b => { const r = b.getBoundingClientRect(); return `${b.className || b.id} ${b.dataset.id || ''} ${r.width.toFixed(1)}x${r.height.toFixed(1)} ${getComputedStyle(b).display}`; }).slice(0, 6)""")
                    assert not small, f"knapper under 44 px ({label}, {name}): {small}"
                    unnamed = page.evaluate("""() => [...document.querySelectorAll('button')].filter(b => b.getBoundingClientRect().width > 0 && !(b.getAttribute('aria-label') || b.textContent.trim() || b.title)).map(b => b.className).slice(0, 5)""")
                    assert not unnamed, f"knapper uten tilgjengelig navn ({label}, {name}): {unnamed}"

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
                        assert f"Ingen surf de neste 3 dagene {area}" in info["text"], f"svarlinja ({view}) sier '{info['text']}'"
                        gaps = mirror_gaps(reg, w0, w3, max_idx, len(data[0]["hours"]))
                        assert ("Noen timer mangler data" in info["text"]) == gaps, f"svarlinja ({view}) sier '{info['text']}' - forecast.json {'mangler' if gaps else 'mangler ikke'} data i vinduet"
                        if ans:
                            sid, i, _, _ = ans
                            name = next(s["name"] for s in spots if s["id"] == sid)
                            assert info["tag"] == "BUTTON" and info["spot"] == sid and info["idx"] == i and "Neste dag med stjerner" in info["text"] and name in info["text"], f"neste dag med stjerner ({view}): {info}, forventet {sid} time {i}"
                        else:
                            assert info["tag"] == "DIV" and "Neste dag med stjerner" not in info["text"], f"ingen stjerner i uka: svarlinja skal ikke peke noe sted ({view}): {info}"
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
                wd = "I dag" if t_a.date() == dt.datetime.now(OSLO).date() else WD_SHORT[t_a.weekday()]
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
                page.evaluate(f"(() => {{ const h = DATA.spots.find(s => s.id === '{M}').hours[{idx}]; h.stars = 0; h.low_reason = null; h.surf_height = null; Front.refresh(); }})()"); page.wait_for_timeout(400)
                mm = page.evaluate(f"""(() => {{ const m = document.querySelector(".mk[data-id='{M}']"), d = getComputedStyle(m.querySelector('.mk-dot'));
                    const r = document.querySelector("#list .row[data-spot='{M}']");
                    return {{miss: m.classList.contains('miss'), bare: m.classList.contains('bare'), label: m.querySelector('.mk-label').textContent, border: d.borderTopStyle, bg: d.backgroundColor,
                             aria: m.getAttribute('aria-label'), note: document.getElementById('mapNote').hidden, row: r.querySelector('.rt .lb').textContent, rowAria: r.getAttribute('aria-label')}}; }})()""")
                assert mm["miss"] and not mm["bare"] and mm["label"] == "–", f"tallet mangler: merket skal ha lappen «–», ikke være en flat prikk: {mm}"
                alpha = float(mm["bg"].rstrip(")").split(",")[3]) if mm["bg"].startswith("rgba") else (0.0 if mm["bg"] == "transparent" else 1.0)
                assert mm["border"] == "dashed" and alpha == 0, f"tallet mangler: stiplet, hul prikk - aldri den grå 0-prikken: {mm}"
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
                heads = page.evaluate("[...document.querySelectorAll('#list .rows-head span')].map(s => s.textContent)")
                first_row = page.evaluate("document.querySelector('#list .row').dataset.spot")
                assert heads[:2] == ["Favoritter", "Andre spots"] and first_row == fav, f"favoritter øverst i lista: {heads}, første rad {first_row}"
                # kantpiler bare for stjerner/favoritter: utenfor Troms-utsnittet
                outside = [s for s in spots if s["id"] not in region["nord"]]
                for s in outside:
                    assert page.evaluate(f"document.querySelector(\".mk-edge[data-id='{s['id']}']\").hidden") or page.locator(".mk-edge.cluster:visible").count(), f"{s['id']} er flat og ikke favoritt - ingen kantpil"
                page.evaluate(setjs(outside[0]["id"], idx, 2) + "Front.refresh();"); page.wait_for_timeout(400)
                assert not page.evaluate(f"document.querySelector(\".mk-edge[data-id='{outside[0]['id']}']\").hidden"), f"{outside[0]['id']} har stjerner - skal ha kantpil"
                page.evaluate(f"Auth.state.favorites.add('{outside[-1]['id']}'); Front.refresh();"); page.wait_for_timeout(400)
                assert not page.evaluate(f"document.querySelector(\".mk-edge[data-id='{outside[-1]['id']}']\").hidden"), f"{outside[-1]['id']} er favoritt - skal ha kantpil"
                shot("kart_stjerner")
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
                    # klyngepil («N spots»): farge og etikett = beste rating i valgt time blant spotene i klynga
                    if page.locator(".mk-edge.cluster:visible").count():
                        info = page.evaluate("""() => { const c = document.querySelector('.mk-edge.cluster'); return {label: c.querySelector('.mk-label').textContent, cls: c.className}; }""")
                        assert info["label"] == "beste 2★" and "r-2" in info["cls"].split(), f"klyngepil: {info}"
                    if view == "alle":
                        shot("alle_tett")
                page.evaluate(restore); page.wait_for_timeout(300)
                page.locator(".seg button[data-view='nord']").click(); page.wait_for_timeout(1200)

                # ---- 10. ukeoversikten: riktig farge og bokstav per dag ----
                today = dt.datetime.now(OSLO).date()
                days = [(today + dt.timedelta(days=k)) for k in range(7)]
                def check_week(where):
                    data = page_data()
                    for s in data:
                        cells = page.evaluate(f"[...document.querySelectorAll(\"#list .row[data-spot='{s['id']}'] .wd\")].map(w => ({{day: w.dataset.day, cls: w.querySelector('.wc').className.replace('wc', '').trim(), letter: w.querySelector('b').textContent}}))")
                        assert [c["day"] for c in cells] == [d.isoformat() for d in days], f"{s['id']}: dagene i ukeoversikten {[c['day'] for c in cells]}"
                        assert [c["letter"] for c in cells] == [LETTERS[d.weekday()] for d in days], f"{s['id']}: dagsbokstaver {[c['letter'] for c in cells]}"
                        exp = [day_best(s["hours"], w0, d.isoformat()) for d in days]
                        assert [c["cls"] for c in cells] == exp, f"{s['id']} ({where}): ukeoversikten {[c['cls'] for c in cells]}, forecast.json gir {exp}"
                check_week("dagens data")
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
                # sortering: favoritter øverst, så beste rating de neste 3 dagene (lyse timer)
                data = page_data()
                def best3(s):
                    return max([(h.get("stars") or 0) for h in s["hours"][w0:w3] if usable(h) and known(h)] or [-1])
                order = page.evaluate("[...document.querySelectorAll('#list .row')].map(r => r.dataset.spot)")
                exp_order = [s["id"] for s in sorted(data, key=lambda s: -best3(s))]
                assert order == exp_order, f"lista skal sorteres etter beste rating de neste 3 dagene: {order}, forventet {exp_order}"

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
                wd = "I dag" if t30.date() == dt.datetime.now(OSLO).date() else WD_SHORT[t30.weekday()]
                assert page.locator("#timePillT").text_content() == f"{wd} {t30.hour:02d}:00", page.locator("#timePillT").text_content()
                page.keyboard.press("Escape"); page.wait_for_timeout(300)
                assert page.locator("#timePanel").is_hidden(), "Escape lukker tidspanelet"
                assert page.locator(back_sel).is_visible(), "tiden står ikke på nå: «Tilbake til nå» skal synes"
                assert page.locator(back_sel).text_content().strip() == "Tilbake til nå"
                shot("tilbake")
                axe_check("tilbake"); buttons_ok("tilbake")
                page.locator(back_sel).click(); page.wait_for_timeout(400)
                assert page.evaluate("Front.state.idx") == w0 and page.locator("#timePillT").text_content() == "Nå" and page.locator(back_sel).is_hidden(), "«Tilbake til nå» setter tiden til nå"

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
    print("4: arket på mobil starter i halv høyde med svarlinja og lista synlig, og dras mellom liste, halv og kart")
    print("5: avspilling ruller tiden, regionvalg virker")
    print("6: axe color-contrast: ingen brudd, alle knapper minst 44 px med tilgjengelig navn")
    print("7: prefers-reduced-motion skrur av animasjonene")
    print("8: svarlinja velger tidligste gode time i området (speilet i Python), og trykk åpner spoten på samme time som kartet")
    print("9: flate spots har ingen lapp, ingen streker, kantpiler bare for stjerner/favoritter, tekst når hele utsnittet er 0 stjerner")
    print("10: ukeoversikten har riktig farge og bokstav per dag, stiplet når tallet mangler")
    print("11: tidspillen («Nå»/«Tor 17:00») åpner glidebryter og play, «Tilbake til nå» når tiden ikke står på nå")
    print("12: vindstrekene bare ved valgt spot, flate merker og listerader står stille")
    print("13: ny time: svarlinja, uka og «Nå» følger nåtimen, en flyttet tid blir stående")
    print("grunnregelen: tall som mangler gir stiplet prikk og «–» på kartet, forbehold i svarlinja og stiplet dag i uka - aldri 0")
    print("Alle tester ok")


if __name__ == "__main__":
    main()
