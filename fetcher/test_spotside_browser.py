"""Nettlesertest for den nye strukturen (Theodor 14./15.10.2026, gren design/spotside):
søk først, kartet som Utforsk, spotside med mye info. Åpner den faktiske docs/index.html
i Chromium med den faste testfila fetcher/fixtures/forecast.json (ekte varsel 14.10.2026
kl. 19Z) servert slik appen får den (data/oversikt.json og data/spots/<id>.json fra
fetcher/publish.py), klokka fast på T0 = 70 minutter etter varselet (page.clock), i
mobil (390x844) og PC (1440x900), lys og mørk (prefers-color-scheme), og sjekker:

1.  ingen JavaScript-feil på noen av sidene;
2.  temaet følger systemet: body-bakgrunnen er --surface for valgt fargeskjema;
3.  ingen tekst overlapper annen tekst, og ingen tekst klippes av en boks eller faller
    utenfor vinduet (bounding boxes i hvert lag: side, flytende kort, brikker, fanelinje);
4.  ingen tekst under 11 px (SVG-tekst regnet om med viewBox-skalaen), alle knapper minst
    44x44 (søylene i timegrafen unntatt - hele kolonnen er trykkflaten), alle knapper har navn;
5.  «grotfjord» (uten ø) finner Grøtfjord først; ingen treff gir «Ingen spots heter «x». …»;
6.  Hjem: datolinja («Onsdag 14. oktober · oppdatert 21:00»), beste økt, ukerutene;
7.  Utforsk: markørene nå har stjernene nå (ratingklasse r-N), en annen dag har dagens beste
    dagslystime (speil av dayBest i ui.js), valgt markør beholder navnet, kortet nederst sier
    spot og dag;
8.  spotsiden (Unstad nå): «Nå · <dag> kl. HH», ordet (ratingWord), SURF/SVELL/VIND/ENERGI
    er forecast-tallene, «Innenfor/Utenfor vinduet» stemmer NØYAKTIG med rating.in_sector,
    minikartet har kystlinje (Unstad og Farstadsanden);
9.  sommertiden slutter 25.10.2026: 6-timers dagene 24., 25. og 26.10 har kolonner med riktige
    Oslo-timer (02 08 14 20 / 02 07 13 19 / 01 07 13 19) - både data-hh og aksen;
10. manglende tall vises aldri som 0: en dag uten tall (lagt inn i testdata for Steinkrøssa)
    gir stiplet rute uten tall på Hjem, «–» på markøren i Utforsk, «–» på spotsiden;
11. «Treffer ikke» vises som ordet, med «Tilbake til nå»;
12. Logger tom: «Ingen økter logget ennå»;
13. kroppshøyde-, energi- og sikkerhetsordene (Spot.*) følger tabellene i prompten;
14. svellvindu-testen i appen (inSwellWindow) er lik rating.in_sector for 0-359° for alle spots;
15. tools/kontrast.py: tekst ≥4,5:1 og grafikk ≥3:1 i begge temaer;
16. skjermbilder (docs/design/spotside/etter/): Hjem, søk med og uten treff, Utforsk nå og en
    annen dag med valgt markør, Unstad nå, 25.10 (6-timers steg), Farstadsanden, «Treffer ikke»,
    + 200 % tekst og prefers-contrast: more - mobil og PC, lys og mørk.

Tidsgrenser (CLAUDE.md): hvert Playwright-steg maks 15 s, hele fila maks 5 minutter (hardkill),
testserveren stoppes uansett utfall. Trenger: pip install playwright && playwright install chromium.
Kjør: python fetcher/test_spotside_browser.py"""
import datetime as dt
import http.server
import json
import os
import socket
import subprocess
import sys
import threading
from functools import partial
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SHOT_DIR = DOCS / "design" / "spotside" / "etter"
SHOT_DIR.mkdir(parents=True, exist_ok=True)
ELEMENT_TIMEOUT_MS = 15_000
FILE_TIMEOUT_S = 300
OSLO = ZoneInfo("Europe/Oslo")
FIXTURE = ROOT / "fetcher" / "fixtures" / "forecast.json"
FORECAST = json.loads(FIXTURE.read_text(encoding="utf-8"))
T0 = (dt.datetime.fromisoformat(FORECAST["generated"].replace("Z", "+00:00")) + dt.timedelta(minutes=70)).astimezone(dt.timezone.utc)
TODAY = T0.astimezone(OSLO).date()
WD = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
MND = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "desember"]
MISS_ID, MISS_DAY = "steinkrossa", TODAY + dt.timedelta(days=5)   # dagen uten tall (punkt 10)
sys.path.insert(0, str(ROOT / "fetcher"))
import rating  # noqa: E402
import sun  # noqa: E402
import testserver  # noqa: E402

# Hjem på mobil (B 4.0 steg 3): startstedet og kjøretidene i docs/js/kjoretid.js, og lyset der i dag regnet med sun.py
import re  # noqa: E402
_KJ = (DOCS / "js" / "kjoretid.js").read_text(encoding="utf-8")
_FRA = re.search(r'fra:\s*\{navn:\s*"([^"]+)",\s*lat:\s*([\d.]+),\s*lon:\s*([\d.]+)\}', _KJ)
FRA_NAVN, FRA_LAT, FRA_LON = _FRA.group(1), float(_FRA.group(2)), float(_FRA.group(3))
KJORETID = {k: int(v) for k, v in re.findall(r'(\w+):\s*(\d+)', re.search(r'min:\s*\{([^}]*)\}', _KJ).group(1))}
_M0 = dt.datetime(TODAY.year, TODAY.month, TODAY.day, tzinfo=OSLO)
_LYS = [_M0 + dt.timedelta(minutes=m) for m in range(0, 1440, 10) if sun.elevation(FRA_LAT, FRA_LON, _M0 + dt.timedelta(minutes=m)) > sun.USABLE]
_SPOTS = json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))
_UKJENT = sorted(set(KJORETID) - {x["id"] for x in (_SPOTS["spots"] if isinstance(_SPOTS, dict) else _SPOTS) if x.get("status") != "hemmelig"})
assert not _UKJENT, f"docs/js/kjoretid.js har id-er som ikke er offentlige spots i spots.json: {_UKJENT}"
# favorittene testen later som brukeren har (Supabase er stengt i testen): to med kjøretid, og Steinkrøssa uten
# kjøretid og med en dag uten tall (MISS_DAY)
FAV_IDS = ["grotfjord", "unstad", MISS_ID]
assert MISS_ID not in KJORETID and all(i in KJORETID for i in FAV_IDS[:2])


def _watchdog():
    def _kill():
        print(f"TIDSAVBRUDD: test_spotside_browser.py brukte over {FILE_TIMEOUT_S}s - avbrutt (se CLAUDE.md).", file=sys.stderr, flush=True)
        os._exit(124)
    t = threading.Timer(FILE_TIMEOUT_S, _kill); t.daemon = True; t.start(); return t


def serve():
    # S3: med HTTP Range (206) som GitHub Pages - PMTiles-kartet trenger det (fetcher/testserver.py)
    return testserver.serve(DOCS)


def route(page):
    for pat in ("https://cdn.jsdelivr.net/**", "https://*.supabase.co/**", "https://fonts.googleapis.com/**", "https://fonts.gstatic.com/**",
                    "https://cache.kartverket.no/**"):   # Kartverket blokkert: Utforsk viser OSM-reserven, likt lokalt og i CI
        page.route(pat, lambda r, req: r.abort())


def r0(v):
    return int(v + 0.5) if v >= 0 else -int(-v + 0.5)


def nf1(v):
    return f"{v:.1f}".replace(".", ",")


def oslo(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(OSLO)


def oslo_day(t):
    return oslo(t).date().isoformat()


def now_idx(hours):
    """speiler currentHour() i app.js: første time som ikke er over ennå"""
    for i, h in enumerate(hours):
        if dt.datetime.fromisoformat(h["t"].replace("Z", "+00:00")) + dt.timedelta(hours=1) > T0:
            return i
    return 0


def naa_of(s):
    """speiler naaOf() i ui.js: klokkas time blant de publiserte nå-timene, ellers den siste"""
    return next((h for h in s["naa"] if dt.datetime.fromisoformat(h["t"].replace("Z", "+00:00")) + dt.timedelta(hours=1) > T0), s["naa"][-1] if s["naa"] else None)


def day_cls(s, key):
    """speiler dayBest() i ui.js på dagssammendraget (publish.day_summary): (cls, stjerner)"""
    d = next((x for x in s["dager"] if x["d"] == key), None)
    if not d or d["status"] == "miss" or not d.get("h"):
        return "miss", None
    if d["status"] == "dark":
        return "dark", None
    st = d["h"].get("stars") or 0
    return f"r-{min(5, st)}", st


def known(h):
    return bool(h) and not (not (h.get("stars") or 0) and not h.get("low_reason") and h.get("surf_height") is None)


def light_of(h):
    return h.get("light") or ("mørkt" if h.get("daylight") is False else "dag" if h.get("daylight") is True else None)


def day_best(hours, w0, key):
    """speiler dayBest() i ui.js - ukjent lys teller aldri som dagslys, dag uten kjente tall = «miss»"""
    anyh = light = unk = miss = False
    best, best_h, idx = -1, None, -1
    for i in range(w0, len(hours)):
        h = hours[i]; k = oslo_day(h["t"])
        if k > key: break
        if k != key: continue
        anyh = True; l = light_of(h)
        if l is None:
            unk = True
            if not known(h) or (h.get("stars") or 0) >= 1: miss = True
            continue
        if l not in ("dag", "skumring"): continue
        light = True
        if not known(h): miss = True; continue
        st = h.get("stars") or 0
        if st > best or (st == best and (h.get("surf_height") or 0) > ((best_h or {}).get("surf_height") or 0)):
            best, best_h, idx = st, h, i
    if not anyh: return "miss", None, -1
    if best >= 1: return f"r-{min(5, best)}", best, idx
    if miss or (not light and unk): return "miss", None, -1
    if not light: return "dark", None, -1
    return "r-0", 0, idx


# ---- tabellene fra prompten (punkt 13) ----
KROPP = [(0.3, "Nesten flatt"), (0.6, "Ankel- til knehøyt"), (0.9, "Kne- til hoftehøyt"), (1.2, "Hofte- til brysthøyt"),
         (1.5, "Bryst- til skulderhøyt"), (1.8, "Skulder- til hodehøyt"), (2.4, "Hodehøyt og litt over"), (3.4, "Godt over hodet")]


def kroppshoyde(a, b):
    m = (a + b) / 2 if b is not None else a
    for lim, word in KROPP:
        if m < lim: return word
    return "Over dobbel hodehøyde"


def energi_ord(kj):
    # universelle grenser (fysikk-kontrollør 15.10.2026: spotens local_rules er dens behov, ikke et ord på svellet)
    return "Svakt" if kj < 500 else "Middels kraft" if kj < 2000 else "Kraftig" if kj < 10000 else "Svært kraftig"


def vindu_tekst(h, spot):
    # speiler Spot.vinduTekst: vinduet fra rating.in_sector, graden av treff fra eksponeringen (directness)
    inside = any(rating.in_sector(h["dir_offshore"], sec) for sec in rating.window_sectors(spot))
    if not inside:
        return "Utenfor vinduet, men bekreftet ved spoten" if h.get("bw_confirms") else "Utenfor vinduet"
    d = h.get("directness")
    if d is None or d >= 0.999: return "Innenfor vinduet"
    if d >= 0.667: return "I kanten av vinduet"
    return "I vinduet, men skjermet"


def sikkerhet(conf, zone):
    s = "Høy sikkerhet" if conf >= 80 else "Middels sikkerhet" if conf >= 55 else "Lav sikkerhet"
    return f"{s} · " + {"barentswatch": "kystmodell 100 m", "reserve": "havmodell", "langtid": "langtidsmodell"}[zone]


AUDIT_JS = r"""() => {
  const view = document.querySelector('main .view:not([hidden])');
  const roots = [view, document.querySelector('.tabbar'), document.querySelector('.topbar'), document.querySelector('#sokDrop')].filter(Boolean);
  const vis = el => { const r = el.getBoundingClientRect(); if(!(r.width > 0 && r.height > 0)) return false; const d = el.closest('details'); if(d && !d.open && !el.closest('summary')) return false; const cs = getComputedStyle(el); return cs.visibility !== 'hidden' && cs.display !== 'none' && cs.opacity !== '0'; };
  const cls = el => (el.className && el.className.baseVal !== undefined) ? el.className.baseVal : (el.className || '');
  const layer = el => { const l = el.closest('.kartkort, .dagchips, .utforsk-top, .tabbar, .topbar, .sok-drop, .kart, .sheet, #toast'); return l ? (l.id || cls(l)) : 'side'; };
  // den synlige delen av et element: rammen klippet mot alle forfedre som klipper (overflow hidden/clip/auto/scroll
  // - f.eks. dagfaner som er rullet ut av syne); tom = ikke synlig
  const clipRect = el => { let r = el.getBoundingClientRect(); let x0 = r.left, y0 = r.top, x1 = r.right, y1 = r.bottom;
    for(let p = el.parentElement; p && p !== document.documentElement; p = p.parentElement){ const cs = getComputedStyle(p);
      if(/(hidden|clip|auto|scroll)/.test(cs.overflowX + ' ' + cs.overflowY)){ const pr = p.getBoundingClientRect(); x0 = Math.max(x0, pr.left); y0 = Math.max(y0, pr.top); x1 = Math.min(x1, pr.right); y1 = Math.min(y1, pr.bottom); } }
    return {left: x0, top: y0, right: x1, bottom: y1, width: x1 - x0, height: y1 - y0}; };
  const leaves = [];
  for(const root of roots) for(const el of root.querySelectorAll('*')){
    if(el.closest('[hidden]') || !vis(el)) continue;
    if(![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const r = clipRect(el), cs = getComputedStyle(el);
    if(r.width <= 1 || r.height <= 1) continue;
    let fs = parseFloat(cs.fontSize);
    const svg = el.ownerSVGElement;
    if(svg){ const vb = svg.viewBox.baseVal; if(vb && vb.width) fs = fs * svg.getBoundingClientRect().width / vb.width; }
    leaves.push({el, r, fs, layer: layer(el), text: el.textContent.trim().slice(0, 40), tag: el.tagName, cls: cls(el)});
  }
  const name = a => `${a.tag}.${a.cls} «${a.text}»`;
  const overlap = [];
  for(let i = 0; i < leaves.length; i++) for(let j = i + 1; j < leaves.length; j++){
    const a = leaves[i], b = leaves[j];
    if(a.layer !== b.layer || a.el.contains(b.el) || b.el.contains(a.el)) continue;
    if(a.el.parentElement === b.el.parentElement) continue;   // linjebrudd i samme blokk (linjehøyde 1,05) er ikke kollisjon
    const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left), h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
    if(w > 3 && h > 3) overlap.push(`${name(a)} × ${name(b)}`);
  }
  const clipped = [];
  for(let a of leaves){
    if(a.el.ownerSVGElement) continue;
    const ar = a.el.getBoundingClientRect(); a = {...a, r: ar};
    let p = a.el.parentElement, done = false;
    while(p && p !== document.body){
      const cs = getComputedStyle(p), ox = cs.overflowX;
      if(ox === 'auto' || ox === 'scroll'){ done = true; break; }   // rullbar boks: innholdet kan ligge utenfor
      if(ox === 'hidden' || ox === 'clip'){ const pr = p.getBoundingClientRect(); if(a.r.right > pr.right + 1 || a.r.left < pr.left - 1) clipped.push(`klippet av ${p.tagName}.${cls(p)}: ${name(a)}`); done = true; break; }
      p = p.parentElement;
    }
    if(!done && (a.r.right > innerWidth + 1 || a.r.left < -1)) clipped.push(`utenfor vinduet: ${name(a)} (${a.r.left.toFixed(0)}–${a.r.right.toFixed(0)})`);
  }
  const small = leaves.filter(a => a.fs < 10.95).map(a => `${name(a)} ${a.fs.toFixed(1)}px`);
  const buttons = [...document.querySelectorAll('button, a.tap, .topnav a, .srad, .tabs a, .sokknapp, .chip, .dagfane, a.rad, a.favkort, a.favlinje')]
    .filter(b => !b.closest('[hidden]') && vis(b) && !b.classList.contains('soyle') && !b.closest('.mk-pill'))
    .filter(b => { const r = b.getBoundingClientRect(); return r.width < 43.5 || r.height < 43.5; })
    .map(b => { const r = b.getBoundingClientRect(); return `${b.tagName}.${cls(b)} ${r.width.toFixed(0)}x${r.height.toFixed(0)}`; });
  const unnamed = [...document.querySelectorAll('button, a')].filter(b => !b.closest('[hidden]') && vis(b) && !(b.getAttribute('aria-label') || b.textContent.trim() || b.title)).map(b => cls(b));
  return {overlap: overlap.slice(0, 8), clipped: clipped.slice(0, 8), small: small.slice(0, 8), buttons: buttons.slice(0, 8), unnamed: unnamed.slice(0, 5),
          hscroll: document.documentElement.scrollWidth > innerWidth + 1, n: leaves.length};
}"""


def main():
    watchdog = _watchdog()
    srv, port = serve()
    import publish
    overview, details = publish.split(FORECAST)
    # punkt 10: én dag uten tall for Steinkrøssa, i både oversikten og detaljfila
    def blank(h):
        if oslo_day(h["t"]) == MISS_DAY.isoformat():
            for k in ("surf_height", "surf_height_sets", "swell_offshore", "period", "dir_offshore", "energy_swell_kj", "wind_speed", "wind_dir", "gust", "light", "air_temp", "water_temp", "confidence"):
                if k in h: h[k] = None
            h["stars"] = 0; h["low_reason"] = None; h["breakdown"] = []
            h.pop("daylight", None)
        return h
    fc_miss = json.loads(json.dumps(FORECAST))
    for s in fc_miss["spots"]:
        if s["id"] == MISS_ID: s["hours"] = [blank(h) for h in s["hours"]]
    overview, details = publish.split(fc_miss)   # oversikt-2: sammendragene regnes av publish.py på det endrede varselet
    OV_BODY = json.dumps(overview, ensure_ascii=False)
    DET_BODY = {sid: json.dumps(d, ensure_ascii=False) for sid, d in details.items()}
    OV = {s["id"]: s for s in overview["spots"]}
    SP = {s["id"]: s for s in FORECAST["spots"]}   # spotfeltene (svellvindu, local_rules) ligger i varselets spot, ikke i detaljfila
    errors = []
    first_miss_idx = next(i for i, h in enumerate(details[MISS_ID]["hours"]) if oslo_day(h["t"]) == MISS_DAY.isoformat())
    # en LYS time: en mørk time viser «Mørkt» i stedet for ordet (B4 SPEC §5)
    treffer = next((sid, i) for sid, d in details.items() for i, h in enumerate(d["hours"]) if h.get("low_reason") == "treffer_ikke" and i > now_idx(d["hours"]) and light_of(h) in ("dag", "skumring"))
    treffer_mork = next(((sid, i) for sid, d in details.items() for i, h in enumerate(d["hours"]) if h.get("low_reason") == "treffer_ikke" and i > now_idx(d["hours"]) and light_of(h) == "mørkt"), None)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("NORDSURF_CHROMIUM")
            nb_env = {**os.environ, "LANG": "nb_NO.UTF-8", "LANGUAGE": "nb_NO", "LC_ALL": "nb_NO.UTF-8"}
            browser = p.chromium.launch(args=["--lang=nb-NO", *testserver.WEBGL_ARGS], env=nb_env, **({"executable_path": exe} if exe else {}))
            for label, vp in (("mobil", (390, 844)), ("pc", (1440, 900))):
                mobile = vp[0] < 900
                ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]}, color_scheme="dark", locale="nb-NO", timezone_id="Europe/Oslo",
                                          device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile)
                page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS)
                page.clock.set_fixed_time(T0)
                page.on("pageerror", lambda e, label=label: errors.append(f"{label}: {e}"))
                page.on("console", lambda m, label=label: errors.append(f"{label} console: {m.text}") if m.type == "error" and "ERR_FAILED" not in m.text and "404" not in m.text else None)
                route(page)
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

                def media(scheme, contrast="no-preference"):
                    cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "dark" if scheme == "mork" else "light"}, {"name": "prefers-contrast", "value": contrast}]})
                    page.wait_for_timeout(150)

                def go(hash_, sel):
                    page.evaluate(f"location.hash = '{hash_}'")
                    try:
                        page.wait_for_selector(sel)
                    except Exception:
                        if errors: print("JavaScript-feil før tidsavbruddet:\n" + "\n".join(errors[:10]))   # ellers skjuler tidsavbruddet årsaken
                        raise
                    page.wait_for_timeout(250)

                def shot(name, scheme):
                    page.screenshot(path=str(SHOT_DIR / f"{name}_{label}_{scheme}.png"), full_page=False)

                def audit(name):
                    a = page.evaluate(AUDIT_JS)
                    where = f"({label}, {scheme}, {name})"
                    assert not a["overlap"], f"tekst som overlapper {where}: {a['overlap']}"
                    assert not a["clipped"], f"tekst som klippes eller faller utenfor {where}: {a['clipped']}"
                    assert not a["small"], f"tekst under 11 px {where}: {a['small']}"
                    assert not a["buttons"], f"knapper under 44 px {where}: {a['buttons']}"
                    assert not a["unnamed"], f"knapper uten navn {where}: {a['unnamed']}"
                    assert not a["hscroll"], f"siden ruller vannrett {where}"
                    assert a["n"] > 3, f"for få tekster funnet {where}: {a['n']}"

                DAG_RE = r"(i dag|i morgen|\w+dag)"

                def sjekk_overskrift(hj):
                    # Overskriften sier aldri noe annet enn lista (SPEC §8). Hver setning må kjennes igjen - en ukjent setning
                    # er en feil - og sjekkes mot rutene: bare «0» er ingen surf, en rute uten tall (mangler data) er det aldri.
                    assert 1 <= len(hj["set"]) <= 2, f"overskriften skal være én eller to setninger: {hj['set']}"
                    rader = hj["rader"]

                    def kol(dag):
                        dagnavn = {"i dag": WD[TODAY.weekday()], "i morgen": WD[(TODAY.weekday() + 1) % 7]}.get(dag, dag)
                        return next(k for k, d in enumerate(rader[0]["dager"]) if dagnavn.startswith(d.lower()))

                    def ingen_surf(i, setn):
                        assert all(r["celler"][i] == "0" or ("miss" not in r["cls"][i] and r["celler"][i] == "") for r in rader), f"«{setn}», men lista har surf eller mangler data: {[(r['celler'][i], r['cls'][i]) for r in rader]}"

                    for nr, setn in enumerate(hj["set"]):
                        mm = re.match(rf"^(.+) på (.+) {DAG_RE}\.$", setn)
                        if mm:
                            ordet, spot, dag = mm.groups()
                            rad = next((r for r in rader if r["navn"].lower() == spot.lower()), None)
                            assert rad, f"overskriften nevner «{spot}», som ikke står i lista: {setn}"
                            i = kol(dag)
                            # ordet er ordet for tallet, eller årsaksordet («Blåst ut») når timen har en low_reason - på dag 0 står det i raden
                            assert rad["celler"][i].isdigit() and int(rad["celler"][i]) >= 1 and (hj["ord"][int(rad["celler"][i])] == ordet or ordet in hj["nullord"]), f"«{setn}» stemmer ikke med ruta {rad['celler'][i]} for {spot}"
                            assert i > 0 or f"{ordet}" in rad["meta"], f"«{setn}», men raden sier {rad['meta']}"
                            assert all(not r["celler"][i].isdigit() or int(r["celler"][i]) <= int(rad["celler"][i]) for r in rader), f"«{setn}», men en annen favoritt har høyere tall den dagen"
                            continue
                        mm = re.match(r"^Best kl\. (\d\d)–(\d\d)\.$", setn)
                        if mm:
                            m1 = re.match(rf"^(.+) på (.+) {DAG_RE}\.$", hj["set"][0])
                            assert nr == 1 and m1, f"«{setn}» uten en spot i første setning: {hj['set']}"
                            rad = next(r for r in rader if r["navn"].lower() == m1.group(2).lower())
                            assert kol(m1.group(3)) == 0 and rad["setn"].strip().endswith(setn), f"«{setn}» er ikke vinduet på raden til {rad['navn']}: {rad['setn']}"
                            continue
                        mm = re.match(rf"^Ingen surf {DAG_RE}\.$", setn)
                        if mm:
                            ingen_surf(kol(mm.group(1)), setn); continue
                        mm = re.match(r"^Ingen surf de neste (\d+) dagene\.$", setn)
                        if mm:
                            assert nr == 1 and int(mm.group(1)) == len(rader[0]["celler"]) - 1 >= 2, f"«{setn}» med {len(rader[0]['celler'])} dager i lista"
                            for i in range(1, len(rader[0]["celler"])):
                                ingen_surf(i, setn)
                            continue
                        mm = re.match(rf"^Mangler data {DAG_RE}\.$", setn)
                        if mm:
                            i = kol(mm.group(1))
                            assert any("miss" in r["cls"][i] for r in rader) and not any(r["celler"][i].isdigit() and int(r["celler"][i]) >= 1 for r in rader), f"«{setn}»: {[(r['celler'][i], r['cls'][i]) for r in rader]}"
                            continue
                        if setn == "Ingen surf resten av dagen.":
                            assert nr == 0 and any("over" in r["cls"][0] for r in rader), f"«{setn}», men lyset er ikke over for noen: {[r['cls'][0] for r in rader]}"
                            ingen_surf(0, setn); continue
                        if setn in ("Dagens lys er over.", "Ingen data i lyse timer."):
                            kl = "over" if setn.startswith("Dagens") else "miss"
                            assert nr == 0 and all(kl in r["cls"][0] for r in rader), f"«{setn}»: {[r['cls'][0] for r in rader]}"
                            continue
                        mm = re.match(rf"^(.+) {DAG_RE}\.$", setn)
                        assert mm and mm.group(1) in hj["nullord"] + ["Mørkt", "Surfing forbudt"], f"ukjent setning i overskriften: «{setn}»"
                        i = kol(mm.group(2)); kl = {"Mørkt": "dark", "Surfing forbudt": "forbud"}.get(mm.group(1))
                        assert all((kl in r["cls"][i] and r["celler"][i] == "") if kl else r["celler"][i] == "0" for r in rader), f"«{setn}»: {[(r['celler'][i], r['cls'][i]) for r in rader]}"

                # overskrift() på oppdiktede dager: tall = dagens beste, ellers «miss», «dark» eller «over»
                SYN_JS = """() => {
                    const H = STR.hjem, W = STR.starWords, dager = Front.helpers.weekDays(), ov = Front.helpers.overskrift;
                    const dag = (i) => relDay(new Date(dager[i].key + 'T11:00:00Z'));
                    const spot = (name, celler, ekstra) => Object.assign({id: name.toLowerCase(), name, dager: dager.map((d, i) => { const c = celler[Math.min(i, celler.length - 1)];
                        if(c && typeof c === 'object') return Object.assign({d: d.key, start: d.key + 'T09:00:00Z', slutt: d.key + 'T11:00:00Z'}, c, {h: Object.assign({t: d.key + 'T10:00:00Z'}, c.h)});
                        return typeof c === 'string' ? {d: d.key, status: c} : {d: d.key, h: {stars: c, surf_height: c ? 1.2 : 0.1, low_reason: c ? null : 'flat', t: d.key + 'T10:00:00Z'}, start: d.key + 'T09:00:00Z', slutt: d.key + 'T11:00:00Z'}; })}, ekstra || {});
                    const best = H.best('11', '14'), n = dager.length - 1;   // timene 09, 10 og 11 UTC er kl. 11–14 norsk sommertid 15.10
                    const forbud = {restriksjoner: [{type: 'surfeforbud', gjelder: 'sjø'}]}, ny = {status: 'forelopig'};
                    const smatt = {h: {stars: 0, surf_height: 0.5, low_reason: 'flat'}}, ikkeNa = {h: {stars: 0, surf_height: 1.0, low_reason: null, period: 12}};
                    const forbi = {h: {stars: 3, surf_height: 1.2, low_reason: null}, slutt: '2020-01-01T11:00:00Z'};   // vinduet er over
                    const t = (spots, egne, ventet, d) => ({fikk: ov(spots, d || dager, egne), ventet});
                    return {
                        'mangler data er ikke ingen surf': t([spot('A', [0]), spot('B', ['miss'])], true, [H.manglerDag(dag(0))]),
                        'mangler data senere i uka': t([spot('A', [0]), spot('B', [0, 0, 'miss', 0])], true, [H.ord(W[0], dag(0))]),
                        'alt mangler': t([spot('A', ['miss']), spot('B', ['miss'])], true, [STR.bestNoLight + '.']),
                        'flatt hele uka': t([spot('A', [0]), spot('B', [0])], true, [H.ord(W[0], dag(0)), H.ingenNeste(n)]),
                        'dagens lys er over': t([spot('A', ['over', 0]), spot('B', ['over', 0])], true, [H.over + '.', H.ingenNeste(n)]),
                        'lyset over, surf senere': t([spot('A', ['over', 0, 3, 0]), spot('B', ['over', 0])], true, [H.over + '.', H.ordSpot(W[3], 'A', dag(2))]),
                        'lyset over for én': t([spot('A', ['over', 0]), spot('B', [0])], true, [H.ingenRest, H.ingenNeste(n)]),
                        'lyset over og mangler data': t([spot('A', ['over', 0]), spot('B', ['miss', 0])], true, [H.manglerDag(dag(0)), H.ingenNeste(n)]),
                        'mørkt og mangler data': t([spot('A', ['dark', 0]), spot('B', ['miss', 0])], true, [H.manglerDag(dag(0)), H.ingenNeste(n)]),
                        'forbud og flatt': t([spot('A', [3], forbud), spot('B', [0])], true, [H.ingen(dag(0)), H.ingenNeste(n)]),
                        'ulike 0-ord samme dag': t([spot('A', [0]), spot('B', [smatt, 0])], true, [H.ingen(dag(0)), H.ingenNeste(n)]),
                        'samme 0-ord, ikke flatt': t([spot('A', [smatt, 0]), spot('B', [smatt, 0])], true, [H.ord(STR.wordSmall, dag(0)), H.ingenNeste(n)]),
                        'ikke surfbart uten «nå»': t([spot('A', [ikkeNa, 0])], true, [H.ord(STR.wordNotNow.replace(/\\s+nå$/, ''), dag(0)), H.ingenNeste(n)]),
                        'dagens vindu er over': t([spot('A', [forbi, 0])], true, [H.ordSpot(W[3], 'A', dag(0))]),
                        'vinduet over, surf senere': t([spot('A', [forbi, 0, 2, 0])], true, [H.ordSpot(W[3], 'A', dag(0)), H.ordSpot(W[2], 'A', dag(2))]),
                        'forbud utenfor favorittene': t([spot('A', [4], forbud), spot('B', [2, 0])], false, [H.ordSpot(W[2], 'B', dag(0)), best]),
                        'forbud for alle': t([spot('A', [3], forbud), spot('B', [2], forbud)], true, [H.ord(H.forbud, dag(0)), H.ingenNeste(n)]),
                        'mørkt i dag': t([spot('A', ['dark', 0]), spot('B', ['dark', 0])], true, [H.morkt(dag(0)), H.ingenNeste(n)]),
                        'foreløpig favoritt teller': t([spot('A', [0]), spot('P', [3, 0], ny)], true, [H.ordSpot(W[3], 'P', dag(0)), best]),
                        'foreløpig utenfor favorittene': t([spot('A', [2, 0]), spot('P', [3, 0], ny)], false, [H.ordSpot(W[2], 'A', dag(0)), best]),
                        'bare foreløpig er surfbar': t([spot('A', [0]), spot('P', [3, 0], ny)], false, [H.ordSpot(W[3], 'P', dag(0)), best]),
                        'bedre dag senere': t([spot('A', [2, 0, 4, 0]), spot('B', [1, 3, 0])], true, [H.ordSpot(W[2], 'A', dag(0)), H.ordSpot(W[4], 'A', dag(2))]),
                        'to dager, ingen surf': t([spot('A', [0]), spot('B', [0])], true, [H.ord(W[0], dag(0)), H.ingen(dag(1))], dager.slice(0, 2)),
                        'én dag': t([spot('A', [0])], true, [H.ord(W[0], dag(0))], dager.slice(0, 1)),
                    };
                }"""

                def ord_dom():
                    return page.text_content("#viewSpot .vurdering .ord").strip()

                for scheme in ("mork", "lys"):
                    media(scheme)
                    bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
                    assert bg == ("rgb(0, 41, 65)" if scheme == "mork" else "rgb(242, 239, 232)"), f"temaet følger ikke systemet ({label}, {scheme}): {bg}"
                    # ---- 6. Hjem ----
                    go("#hjem", "#viewHjem:not([hidden]) #bestKort")
                    gen = oslo(FORECAST["generated"])
                    if mobile:   # B 4.0 steg 3: topplinja «ONS 14.10 · LYS 06:50–18:00» og «Fra Tromsø», oppdatert-tiden står nederst
                        dato = f"{WD[TODAY.weekday()][:3].capitalize()} {TODAY:%d.%m} · " + (f"Lys {_LYS[0]:%H:%M}–{_LYS[-1]:%H:%M}" if _LYS else "Mørkt hele dagen")
                        linje = page.text_content("#viewHjem .hjem-linje")
                        assert dato in linje and f"Fra {FRA_NAVN}" in linje, f"topplinja mangler «{dato}» eller startstedet: {linje}"
                        assert f"Oppdatert i dag kl. {gen:%H:%M}." in page.text_content("#viewHjem .kilder"), "oppdatert-tiden mangler nederst på Hjem"
                    else:
                        dato = f"{WD[TODAY.weekday()].capitalize()} {TODAY.day}. {MND[TODAY.month - 1]} · oppdatert {gen:%H:%M}"
                        assert dato in page.text_content("#viewHjem"), f"datolinja mangler «{dato}»"
                    miss_cells = page.evaluate("""() => { const rad = [...document.querySelectorAll('#viewHjem a.rad, #viewHjem table.spots tr')].find(r => r.textContent.includes('Steinkrøssa'));
                        return rad ? [...rad.querySelectorAll('.uke i, td.celle, .celle')].map(c => ({cls: c.className, txt: c.textContent.trim()})) : null; }""")
                    assert miss_cells, "fant ikke Steinkrøssa på Hjem"
                    cell = miss_cells[4]   # T0 er kl. 22:10 - dagens lys er over, ukeradene starter i morgen (PR #12 punkt c), så dag 5 er rute 4
                    assert "miss" in cell["cls"] and cell["txt"] in ("", "–"), f"dagen uten tall skal være stiplet uten tall på Hjem: {cell}"
                    shot("hjem", scheme); audit("hjem")
                    if mobile:
                        # ---- 6b. Hjem på mobil: overskriften og favorittlinjene (B 4.0 steg 3, SPEC §6A) ----
                        HJEM_JS = """() => ({
                            set: [...document.querySelectorAll('#viewHjem .hjem-overskrift span')].map(e => e.textContent.trim()),
                            rader: [...document.querySelectorAll('#viewHjem .favlinje')].map(r => ({navn: r.querySelector('.t-navn').textContent.trim(), tall: r.querySelector('.t-listetall').textContent.trim(),
                                meta: r.querySelector('.etikett').textContent.trim(), obs: (r.querySelector('.etikett.obs') || {}).textContent || null, href: r.getAttribute('href'),
                                celler: [...r.querySelectorAll('.uke i')].map(c => c.textContent.trim()), cls: [...r.querySelectorAll('.uke i')].map(c => c.className), setn: (r.querySelector('.setn') || {}).textContent || '', dager: [...r.querySelectorAll('.uke b')].map(c => c.textContent.trim())})),
                            ord: STR.starWords, nullord: [STR.starWords[0], STR.wordSmall, STR.wordMushy, STR.wordTide, STR.wordNotNow.replace(/\\s+nå$/, ''), STR.wordLittleSwell, STR.wordUncertain, ...Object.values(STR.lowReason)], rediger: (document.querySelector('#favRediger') || {}).textContent || null, fjern: document.querySelectorAll('#viewHjem [data-fjern]').length})"""
                        uten = page.evaluate(HJEM_JS)
                        assert 1 <= len(uten["set"]) <= 2 and not uten["rader"] and uten["rediger"] is None, f"Hjem uten favoritter: {uten}"
                        page.evaluate("""(ids) => { window.__auth0 = window.Auth; window.__logs0 = localStorage.getItem('nordsurf.logs.v1');
                            window.Auth = {state: {ready: true, user: {id: 'test'}, profile: null, favorites: new Set(ids)}, toggleFavorite: async (id) => { Auth.state.favorites.delete(id); }};
                            localStorage.setItem('nordsurf.logs.v1', JSON.stringify([{t: new Date(Date.now() - 26 * 36e5).toISOString(), spot: ids[0], stars: 3, size: 'Brysthøy', wind: 'Offshore', type: 'own'},
                                {t: new Date(Date.now() - 8 * 864e5).toISOString(), spot: ids[1], stars: 4, size: 'Hodehøy', wind: 'Offshore', type: 'own'},
                                {t: new Date(Date.now() + 2 * 36e5).toISOString(), spot: ids[1], stars: 5, size: 'Hodehøy', wind: 'Offshore', type: 'own'}]));
                            Front.refresh(); }""", FAV_IDS)
                        page.wait_for_selector("#viewHjem a.favlinje")
                        hj = page.evaluate(HJEM_JS)
                        assert [r["href"] for r in hj["rader"]] and sorted(r["href"] for r in hj["rader"]) == sorted(f"#spot={i}" for i in FAV_IDS), f"favorittlinjene: {hj['rader']}"
                        for r in hj["rader"]:
                            assert r["tall"] == r["celler"][0] or (r["tall"] == "" and r["celler"][0] in ("", "–")), f"tallet foran {r['navn']} er ikke dagens rute: {r}"
                            assert len(r["celler"]) == 7 and len(r["dager"]) == 7, f"ukeoversikten på {r['navn']}: {r}"
                            sid = r["href"].split("=")[1]; m = KJORETID.get(sid)
                            kj = None if not m else (f"{m // 60} t" + (f" {m % 60} min" if m % 60 else "") if m >= 60 else f"{m} min")
                            assert (f" · {kj} · " in r["meta"]) if kj else (" min" not in r["meta"] and " t ·" not in r["meta"]), f"kjøretiden på {r['navn']}: {r['meta']}"
                        g = next(r for r in hj["rader"] if r["href"] == f"#spot={FAV_IDS[0]}")
                        assert g["obs"] and g["obs"].startswith("Obs ") and "3 av 5 · Brysthøy · Offshore" in g["obs"], f"OBS-linja fra loggen mangler: {g}"
                        assert all(r["obs"] is None for r in hj["rader"] if r is not g), f"OBS-linje fra en logg eldre enn 7 dager eller fram i tid: {hj['rader']}"
                        # overskriften sier aldri noe annet enn lista (SPEC §8): ordet er ordet for tallet i ruta den dagen, og ingen favoritt har høyere
                        assert 1 <= len(hj["set"]) <= 2, f"overskriften skal være én eller to setninger: {hj['set']}"
                        sjekk_overskrift(hj)
                        # de samme reglene på oppdiktede dager (kontrolløren 12.11.2026): manglende data er aldri «ingen surf»,
                        # «dagens lys er over» og forbud sies som det er, en foreløpig favoritt teller, aldri «de neste 1 dagene»
                        syn = page.evaluate(SYN_JS)
                        for navn, c in syn.items():
                            assert c["fikk"] == c["ventet"], f"overskriften, tilfellet «{navn}»: fikk {c['fikk']}, ventet {c['ventet']}"
                            assert not any(re.search(r"\bnå\b|neste 1 dagene", x) for x in c["fikk"]), f"overskriften, tilfellet «{navn}»: {c['fikk']}"
                        shot("hjem-fav", scheme); audit("hjem-fav")
                        page.click("#favRediger"); page.wait_for_selector("#viewHjem [data-fjern]")
                        red = page.evaluate(HJEM_JS)
                        assert red["fjern"] == len(FAV_IDS) and red["rediger"] == "Ferdig" and page.get_attribute("#favRediger", "aria-pressed") == "true", f"redigeringen av favoritter: {red}"
                        assert page.evaluate("document.activeElement && document.activeElement.id") == "favRediger", "fokus skal stå på «Ferdig» etter at lista er tegnet på nytt"
                        assert page.evaluate("[...document.querySelectorAll('#viewHjem .favlinje')].every(r => r.getAttribute('role') === 'group' && (r.getAttribute('aria-label') || '').length > 10)"), "radene i redigering mangler navn for skjermleser"
                        assert page.get_attribute("#viewHjem .favleggtil a", "href") == "#sok", "«Legg til spot» skal åpne søket"
                        audit("hjem-rediger")
                        page.click(f'#viewHjem [data-fjern="{FAV_IDS[1]}"]'); page.wait_for_function(f"document.querySelectorAll('#viewHjem [data-fjern]').length === {len(FAV_IDS) - 1}")
                        assert page.evaluate("document.activeElement && document.activeElement.id") == "favRediger", "fokus skal stå på «Ferdig» etter «Fjern»"
                        page.click("#favRediger"); page.wait_for_selector("#viewHjem a.favlinje")
                        etter = page.evaluate(HJEM_JS)
                        assert sorted(r["href"] for r in etter["rader"]) == sorted(f"#spot={i}" for i in FAV_IDS if i != FAV_IDS[1]), "«Fjern» tok ikke bort favoritten"
                        sjekk_overskrift(etter)
                        page.evaluate("""() => { window.Auth = window.__auth0; delete window.__auth0;
                            if(window.__logs0 == null) localStorage.removeItem('nordsurf.logs.v1'); else localStorage.setItem('nordsurf.logs.v1', window.__logs0); Front.refresh(); }""")
                        page.wait_for_function("!document.querySelector('#viewHjem .favlinje')")
                    # ---- 5. søk ----
                    if mobile:
                        page.click(".sokknapp"); page.wait_for_selector("#sokM")
                        page.fill("#sokM", "grotfjord"); page.wait_for_selector("#sokRes .srad")
                        assert page.text_content("#sokRes .srad .nm b").strip() == "Grøtfjord"
                        shot("sok-treff", scheme); audit("sok-treff")
                        page.fill("#sokM", "xyzzy"); page.wait_for_selector("#sokRes .ingen-treff")
                        assert page.text_content("#sokRes .ingen-treff").strip() == "Ingen spots heter «xyzzy». Prøv et område, som Senja eller Lofoten."
                        shot("sok-ingen", scheme); audit("sok-ingen")
                        page.click("#sokAvbryt"); page.wait_for_selector("#viewHjem:not([hidden])")
                    else:
                        page.fill("#sokPC", "grotfjord"); page.wait_for_selector("#sokDrop:not([hidden]) .srad")
                        assert page.text_content("#sokDrop .srad .nm b").strip() == "Grøtfjord"
                        shot("sok-treff", scheme); audit("sok-treff")
                        page.fill("#sokPC", "xyzzy"); page.wait_for_selector("#sokDrop .ingen-treff")
                        assert "Ingen spots heter «xyzzy»" in page.text_content("#sokDrop .ingen-treff")
                        shot("sok-ingen", scheme); audit("sok-ingen")
                        page.fill("#sokPC", ""); page.keyboard.press("Escape"); page.wait_for_selector("#sokDrop", state="hidden")
                    # ---- 7. Utforsk (Tillegg 2: standardutsnitt = valgt region, klynger under 48 px) ----
                    go("#utforsk", "#viewUtforsk:not([hidden]) .mk, #viewUtforsk:not([hidden]) .klynge")
                    page.wait_for_timeout(500)
                    def click_mk(sid):
                        # lappen er trykkflaten når den vises (lappene kolliderer aldri); ellers prikken
                        pill = page.query_selector(f".mk[data-id='{sid}']:not(.bare) .mk-pill")
                        if pill: pill.click()
                        else: page.click(f".mk[data-id='{sid}'] .mk-dot", force=True)
                    def markers():
                        return page.evaluate("[...document.querySelectorAll('.mk')].filter(m => !m.hidden).map(m => ({id: m.dataset.id, cls: m.className, ord: m.querySelector('.ord') ? m.querySelector('.ord').textContent : '', bare: m.classList.contains('bare')}))")
                    def clusters():
                        return page.evaluate("[...document.querySelectorAll('.klynge')].map(k => ({ids: k.dataset.ids.split(','), cls: k.className, n: +k.querySelector('b').textContent}))")
                    def check_colors(val, what):
                        mk, cl = markers(), clusters()
                        assert mk or cl, f"ingen markører/klynger ({what})"
                        for m in mk:
                            exp, _ = val(m["id"]); assert exp in m["cls"].split(), f"markøren {what} for {m['id']} skal ha {exp}: {m['cls']}"
                        for c in cl:
                            best = max((val(sid)[1] or 0) for sid in c["ids"]); assert f"r-{best}" in c["cls"].split() and c["n"] == len(c["ids"]), (c, best)
                        return mk, cl
                    def val_now(sid):
                        h = naa_of(OV[sid]); st = h.get("stars") or 0
                        if known(h) and light_of(h) == "mørkt": return "r-0", None   # mørk time: ingen vurdering på skjermen (B4 SPEC §5)
                        return (f"r-{min(5, st)}" if known(h) else "miss"), (st if known(h) else None)
                    mk, cl = check_colors(val_now, "nå")
                    assert page.text_content("#utforskChips [aria-pressed='true']").strip() == "Troms", "standardutsnittet skal være valgt region (Troms)"
                    shot("utforsk-na", scheme); audit("utforsk-na")
                    # kortet for en spot med ekte 0 nå: Surf = ordet, aldri «–»/«null»
                    nul = next((m for m in mk if naa_of(OV[m["id"]]).get("surf_height") == 0 and naa_of(OV[m["id"]]).get("low_reason")), None)
                    if nul:
                        click_mk(nul["id"]); page.wait_for_selector("#kartKort:not([hidden])")
                        h0 = naa_of(OV[nul["id"]])
                        surf_txt = page.text_content("#kartKort .fakta div:first-child b").strip()
                        exp_word = page.evaluate("(h) => ratingWord(h)", h0)
                        assert surf_txt not in ("–", "null", "") and (exp_word in surf_txt or "m" in surf_txt), (surf_txt, exp_word)
                        page.click("#kortLukk"); page.wait_for_selector("#kartKort", state="hidden")
                    day3 = TODAY + dt.timedelta(days=3)
                    page.click(f"#dagChips .chip[data-day='{day3.isoformat()}']"); page.wait_for_timeout(300)
                    def val_day3(sid):
                        cls, st = day_cls(OV[sid], day3.isoformat())
                        return ("miss" if cls == "miss" else "r-0" if cls == "dark" else cls), st
                    mk3, _ = check_colors(val_day3, str(day3))
                    for m in mk3:
                        if val_day3(m["id"])[0] == "miss": assert m["ord"] == "–", m
                    # valgt markør beholder navnet: Lofoten-utsnittet har én spot (Unstad)
                    page.click("#utforskChips [data-view='Lofoten']"); page.wait_for_timeout(900)
                    click_mk("unstad"); page.wait_for_selector("#kartKort:not([hidden])")
                    kort = page.text_content("#kartKort")
                    assert "Unstad" in kort and WD[day3.weekday()] in kort, f"kortet skal si Unstad og {WD[day3.weekday()]}: {kort[:120]}"
                    sel = next(m for m in markers() if m["id"] == "unstad")
                    assert "sel" in sel["cls"].split() and not sel["bare"], f"valgt markør skal beholde navnet: {sel}"
                    shot("utforsk-dag-valgt", scheme); audit("utforsk-dag-valgt")
                    page.click("#kortLukk"); page.wait_for_selector("#kartKort", state="hidden")
                    # dagen uten tall: «–» på markøren (zoom inn i klyngen hvis spoten ligger i en)
                    page.click("#utforskChips [data-view='Troms']"); page.wait_for_timeout(900)
                    page.click(f"#dagChips .chip[data-day='{MISS_DAY.isoformat()}']"); page.wait_for_timeout(300)
                    kl = next((c for c in clusters() if MISS_ID in c["ids"]), None)
                    if kl:
                        page.click(f".klynge[data-ids='{','.join(kl['ids'])}']"); page.wait_for_timeout(900)
                    mm = next(m for m in markers() if m["id"] == MISS_ID)
                    assert "miss" in mm["cls"].split() and mm["ord"] == "–", f"markøren for dagen uten tall: {mm}"
                    page.click("#dagChips .chip[data-day='']"); page.wait_for_timeout(200)
                    page.click("#utforskChips [data-view='Troms']"); page.wait_for_timeout(300)
                    # ---- 8. Unstad nå ----
                    go("#spot=unstad", "#viewSpot:not([hidden]) .vurdering .ord")
                    page.wait_for_selector("#miniKort .minikart path.land")
                    assert page.evaluate("window.__S.idx") is None, "spotsiden uten &t= skal stå på «nå» (S.idx null)"
                    hs = details["unstad"]["hours"]; idx = now_idx(hs); h = hs[idx]
                    naa = page.text_content("#viewSpot .naa").strip()
                    assert naa.startswith("Nå · ") and f"kl. {oslo(h['t']):%H}" in naa, naa
                    # B4 SPEC §5: en mørk time får ingen vurdering på skjermen - ordet er «Mørkt», uten tall, med «Bare lyse timer får tall»
                    if light_of(h) == "mørkt":
                        assert ord_dom() == "Mørkt" and not page.query_selector("#viewSpot .vurdering .rtall"), ord_dom()
                        assert "bare lyse timer får tall" in page.text_content("#viewSpot .vurdering").lower()
                    else:
                        assert ord_dom() == page.evaluate("(h) => ratingWord(h)", h), ord_dom()
                        assert page.text_content("#viewSpot .vurdering .rtall").strip() == str(min(5, h.get("stars") or 0))
                    kort4 = page.evaluate("[...document.querySelectorAll('#viewSpot .kort4 .kort')].map(k => k.textContent.replace(/\\s+/g, ' ').trim())")
                    surf = kort4[0]
                    if h["surf_height"] is not None and h["surf_height"] > 0 and not h.get("low_reason"):
                        assert nf1(h["surf_height"]) in surf, (surf, h["surf_height"])
                        assert kroppshoyde(h["surf_height"], h.get("surf_height_sets")) in surf, surf
                    assert nf1(h["swell_offshore"]) in kort4[1] and f"{r0(h['period'])}s" in kort4[1].replace(" ", ""), kort4[1]
                    assert vindu_tekst(h, SP["unstad"]) in kort4[1], (kort4[1], h["dir_offshore"], h.get("directness"), SP["unstad"]["swell_window"])
                    assert f"{r0(h['wind_speed'])}m/s" in kort4[2].replace(" ", "").replace(" ", ""), kort4[2]
                    kj = h.get("energy_swell_kj")
                    if kj is not None:
                        assert str(r0(kj)) in kort4[3].replace(" ", "").replace(" ", "").replace("\xa0", ""), (kort4[3], kj)
                        assert energi_ord(kj) in kort4[3], kort4[3]
                    assert sikkerhet(h["confidence"], h["zone"]) == page.text_content("#viewSpot .sikker").strip()
                    shot("unstad-na", scheme); audit("unstad-na")
                    # punkt 1 (Theodor 15.10): tallspenn på én linje (kortene og dagfanene), tallet aldri brutt
                    brudd = page.evaluate("""() => [...document.querySelectorAll('#viewSpot .kort4 .v, #viewSpot .dagfane .h')].filter(el => el.getBoundingClientRect().height > 1.5 * parseFloat(getComputedStyle(el).fontSize)).map(el => el.className + ' «' + el.textContent.trim() + '» ' + el.getBoundingClientRect().height.toFixed(0) + 'px')
                        .concat([...document.querySelectorAll('#viewSpot .tall')].filter(el => el.getClientRects().length > 1).map(el => 'brutt tall «' + el.textContent.trim() + '»'))""")
                    assert not brudd, f"tallspenn over flere linjer ({label}, {scheme}): {brudd}"
                    # punkt 3: åpnet på «nå» kl. 22 (mørkt) viser grafen i morgen, kortene nå
                    assert page.evaluate("document.querySelector('.dagfane[aria-selected=\"true\"]').dataset.day") == (TODAY + dt.timedelta(days=1)).isoformat()
                    assert page.evaluate("[...document.querySelectorAll('.dagfane')].map(b => b.dataset.day)")[0] > TODAY.isoformat(), "«I dag» skal ikke vises når det er mørkt resten av dagen"
                    # punkt 2: aldri «0,0–» i et spenn
                    assert not [x for x in page.evaluate("[...document.querySelectorAll('.dagfane .h')].map(e => e.textContent.trim())") if x.startswith("0,0")]
                    # ---- 9. sommertiden slutter 25.10: 6-timers dager med riktige Oslo-timer ----
                    for d in (24, 25, 26):
                        key = f"2026-10-{d}"
                        exp = [f"{oslo(x['t']):%H}" for x in hs if oslo_day(x["t"]) == key]
                        page.click(f".dagfane[data-day='{key}']"); page.wait_for_selector(f".dagfane[data-day='{key}'][aria-selected='true']"); page.wait_for_timeout(150)
                        hh = [f"{int(x):02d}" for x in page.evaluate("[...document.querySelectorAll('#graf .kol')].map(k => k.dataset.hh)")]
                        akse = page.evaluate("[...document.querySelectorAll('#graf .akse span')].map(s => s.textContent.trim()).filter(Boolean)")
                        assert hh == exp, f"{key}: kolonnene skal være {exp}, fikk {hh}"
                        assert akse == exp, f"{key}: aksen skal være {exp}, fikk {akse}"
                        assert len(exp) == 4, (key, exp)
                    shot("unstad-6t", scheme); audit("unstad-6t")
                    # ---- Farstadsanden ----
                    go("#spot=farstadsanden", "#viewSpot:not([hidden]) .vurdering .ord")
                    page.wait_for_selector("#miniKort .minikart path.land")
                    shot("farstadsanden", scheme); audit("farstadsanden")
                    # ---- 11. «Treffer ikke» ----
                    go(f"#spot={treffer[0]}&t={treffer[1]}", "#viewSpot:not([hidden]) #tilbakeNa")
                    assert ord_dom() == "Treffer ikke", ord_dom()
                    assert page.text_content("#viewSpot .vurdering .rtall").strip() == "0", "«Treffer ikke» i en lys time skal vise tallet 0"
                    shot("treffer-ikke", scheme); audit("treffer-ikke")
                    if treffer_mork:   # samme i en mørk time: «Mørkt» uten tall øverst, grunnen står fortsatt i surfekortet
                        go(f"#spot={treffer_mork[0]}&t={treffer_mork[1]}", "#viewSpot:not([hidden]) #tilbakeNa")
                        assert ord_dom() == "Mørkt" and not page.query_selector("#viewSpot .vurdering .rtall"), ord_dom()
                        assert "Treffer ikke" in page.text_content("#viewSpot .kort4"), "grunnen skal stå i kortene også i en mørk time"
                    # Theodor 16.10 (Grøtfjord 17.10 kl. 14): tallet i valgt søyle er det søylen tegner - ved surfehøyde 0
                    # ordet, aldri BarentsWatch-høyden («1,3» i en tom søyle)
                    bo = next(((sid, i) for sid, d in details.items() for i, x in enumerate(d["hours"]) if x.get("surf_height") == 0
                               and x.get("low_reason") == "blown_out" and (x.get("bw_height") or 0) > 0.5 and i > now_idx(d["hours"])), None)
                    if bo:
                        go(f"#spot={bo[0]}&t={bo[1]}", "#viewSpot:not([hidden]) #tilbakeNa")
                        lbl = page.evaluate("(() => { const e = document.querySelector('#langtid .soyle .tall'); return e ? e.textContent.trim() : null; })()")
                        word = page.evaluate("(h) => ratingWord(h)", details[bo[0]]["hours"][bo[1]])
                        assert lbl == word, (bo, lbl, word)
                    ok = next(((sid, i) for sid, d in details.items() for i, x in enumerate(d["hours"]) if (x.get("surf_height") or 0) > 0.3
                               and x.get("surf_height_sets") is not None and i > now_idx(d["hours"])), None)
                    if ok:
                        go(f"#spot={ok[0]}&t={ok[1]}", "#viewSpot:not([hidden]) #tilbakeNa")
                        lbl = page.evaluate("(() => { const e = document.querySelector('#langtid .soyle .tall'); return e ? e.textContent.trim() : null; })()")
                        want = details[ok[0]]["hours"][ok[1]]["surf_height_sets"]
                        assert lbl and abs(float(lbl.replace(",", ".")) - want) <= 0.051, (ok, lbl, want)   # JS og Python runder x,x5 ulikt
                    # ---- ekte 0 (flat-sperren): ordet, aldri «–» eller «null» (fysikk-kontrollør runde 2) ----
                    flat = next(((sid, i) for sid, d in details.items() for i, x in enumerate(d["hours"]) if x.get("low_reason") == "flat" and x.get("surf_height") == 0 and i > now_idx(d["hours"])), None)
                    if flat:
                        go(f"#spot={flat[0]}&t={flat[1]}", "#viewSpot:not([hidden]) #tilbakeNa")
                        word = page.evaluate("(h) => ratingWord(h)", details[flat[0]]["hours"][flat[1]])
                        k4 = page.evaluate("[...document.querySelectorAll('#viewSpot .kort4 .kort')].map(k => k.textContent.replace(/\\s+/g, ' ').trim())")
                        assert word in k4[0] and "null" not in " ".join(k4) and not k4[0].startswith("Surf –"), (word, k4)
                    # «Treffer ikke» med surfehøyde > 0: regel (c) sier intet pålitelig tall → ordet, ikke «–» (runde 3)
                    ti = next(((sid, i) for sid, d in details.items() for i, x in enumerate(d["hours"]) if x.get("low_reason") == "treffer_ikke" and (x.get("surf_height") or 0) > 0 and i > now_idx(d["hours"])), None)
                    if ti:
                        go(f"#spot={ti[0]}&t={ti[1]}", "#viewSpot:not([hidden]) #tilbakeNa")
                        k4 = page.evaluate("[...document.querySelectorAll('#viewSpot .kort4 .kort')].map(k => k.textContent.replace(/\\s+/g, ' ').trim())")
                        assert "Treffer ikke" in k4[0] and not k4[0].startswith("Surf –"), k4[0]
                    # ---- 10. spotsiden på dagen uten tall: «–», aldri 0 ----
                    go(f"#spot={MISS_ID}&t={first_miss_idx}", "#viewSpot:not([hidden]) #tilbakeNa")
                    assert ord_dom() == "–", ord_dom()
                    k4 = page.evaluate("[...document.querySelectorAll('#viewSpot .kort4 .kort .v')].map(v => v.textContent.trim())")
                    assert all(v == "–" for v in k4), f"kortene på dagen uten tall skal vise «–»: {k4}"
                    assert "0" not in page.text_content(f".dagfane[data-day='{MISS_DAY.isoformat()}']"), "dagfanen for dagen uten tall viser et 0"
                    # ---- 12. Logger tom ----
                    go("#logger", "#viewSide:not([hidden])")
                    assert "Ingen økter logget ennå" in page.text_content("#viewSide")
                    audit("logger")
                    # ---- 16. 200 % tekst (mobil) og prefers-contrast: more ----
                    if mobile:
                        page.evaluate("document.documentElement.style.fontSize = '200%'")
                        go("#hjem", "#viewHjem:not([hidden]) #bestKort"); shot("hjem-200", scheme); audit("hjem-200")
                        go("#spot=unstad", "#viewSpot:not([hidden]) .vurdering .ord"); page.wait_for_timeout(300); shot("unstad-200", scheme); audit("unstad-200")
                        brutt = page.evaluate("[...document.querySelectorAll('#viewSpot .tall')].filter(el => el.getClientRects().length > 1).map(el => el.textContent.trim())")
                        assert not brutt, f"tall brutt over to linjer ved 200 %: {brutt}"
                        page.evaluate("document.documentElement.style.fontSize = ''")
                    media(scheme, "more")
                    go("#hjem", "#viewHjem:not([hidden]) #bestKort"); shot("hjem-kontrast", scheme); audit("hjem-kontrast")
                    go("#spot=unstad", "#viewSpot:not([hidden]) .vurdering .ord"); page.wait_for_timeout(300); shot("unstad-kontrast", scheme); audit("unstad-kontrast")
                    media(scheme)
                if not mobile:
                    # ---- 13. ordtabellene ----
                    for a, b in ((0.1, 0.2), (0.3, 0.5), (0.5, 0.9), (1.0, 1.3), (1.2, 1.7), (1.6, 2.1), (2.0, 2.5), (2.6, 3.4), (3.0, 4.2), (0.8, None)):
                        got = page.evaluate("([a, b]) => Spot.kroppshoyde({surf_height: a, surf_height_sets: b})", [a, b])
                        assert got == kroppshoyde(a, b), (a, b, got)
                    assert page.evaluate("() => Spot.kroppshoyde({surf_height: null})") in (None, "", "–")
                    for kj in (0, 100, 499, 500, 1999, 2000, 9999, 10000, 50000):
                        assert page.evaluate("(kj) => Spot.energiOrd(kj)", kj) == energi_ord(kj), kj
                    # regel (c): «Blåst ut» uten surfehøyde viser BarentsWatch-høyden, «Stormsjø» alltid den
                    assert page.evaluate("() => Spot.visHoyde({low_reason: 'blown_out', surf_height: 0, surf_height_sets: 0, bw_height: 0.58})") == {"a": 0.58, "b": None}
                    assert page.evaluate("() => Spot.visHoyde({low_reason: 'stormsjo', surf_height: 0.4, surf_height_sets: 0.5, bw_height: 2.1})") == {"a": 2.1, "b": None}
                    assert page.evaluate("() => Spot.visHoyde({low_reason: 'treffer_ikke', surf_height: 0.4, bw_height: 1.0})") is None
                    assert page.evaluate("() => Spot.visHoyde({surf_height: 1.6, surf_height_sets: 2.1})") == {"a": 1.6, "b": 2.1}
                    for h_, exp in (({"dir_offshore": 300, "directness": 1.0}, "Innenfor vinduet"), ({"dir_offshore": 300, "directness": 0.7}, "I kanten av vinduet"),
                                    ({"dir_offshore": 300, "directness": 0.3}, "I vinduet, men skjermet"), ({"dir_offshore": 200, "directness": 0.0}, "Utenfor vinduet"),
                                    ({"dir_offshore": 200, "directness": 0.0, "bw_confirms": True}, "Utenfor vinduet, men bekreftet ved spoten"), ({"dir_offshore": 300}, "Innenfor vinduet")):
                        got = page.evaluate("([h, w]) => Spot.vinduTekst(h, {swell_window: w}).txt", [h_, [284, 326]])
                        assert got == exp, (h_, got)
                    for conf, zone in ((95, "barentswatch"), (80, "barentswatch"), (79, "reserve"), (55, "langtid"), (54, "langtid")):
                        assert page.evaluate("([c, z]) => Spot.sikkerhet({confidence: c, zone: z})", [conf, zone]) == sikkerhet(conf, zone)
                    # ---- 14. svellvinduet: nøyaktig som rating.in_sector ----
                    for sid, d in SP.items():
                        js = page.evaluate("(w) => Array.from({length: 360}, (_, deg) => inSwellWindow(deg, {swell_window: w}))", d["swell_window"])
                        py = [any(rating.in_sector(deg, sec) for sec in rating.window_sectors(d)) for deg in range(360)]
                        bad = [deg for deg in range(360) if js[deg] != py[deg]]
                        assert not bad, f"{sid}: inSwellWindow ulik rating.in_sector for {bad[:10]} (vindu {d['swell_window']})"
                ctx.close()
            browser.close()
    finally:
        srv.shutdown()
        watchdog.cancel()
    assert not errors, "JavaScript-feil: " + "\n".join(errors[:10])
    # ---- 15. kontrast ----
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "kontrast.py"), "-q"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, "kontrast: " + r.stdout[-800:] + r.stderr[-300:]
    print(f"OK: test_spotside_browser ({len(list(SHOT_DIR.glob('*.png')))} skjermbilder i {SHOT_DIR.relative_to(ROOT)})")


if __name__ == "__main__":
    main()
