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
6.  Hjem: topplinja/datolinja med lyset og startstedet, ukerutene; PC (B4 steg 6, SPEC §6D): forsiden med
    hovedbildet (dagens beste), «Beste i dag» med samme dagstall som ukerutene og «Neste 7 dager» per spot;
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

Spotsiden i design B 4.0 (mobil steg 4, SPEC §6B; PC steg 6, SPEC §6C) - punkt 8-11 sjekkes i spot_mobil() på begge:
dommen har samme tall som Hjem og ukeoversikten, timens svell/surf/vind/tidevann er varselets, retningsskiva
sier vinduet som rating.in_sector, kornfotoet følger temaet (Trykk/Lodd) med kreditering, tilbakeknappen
følger stakken (Hjem/Utforsk), timevalg med skjult glidebryter, piltaster og trykk, «Tilbake til nå»,
korall bare fra 4 poeng, tapte poeng stiplet, og mørke, forbudte og tomme timer uten tall. På PC i tillegg: 7 store
dagkolonner, etikettkolonnen i «time for time», musa over en time velger den, «Om spotten» med sikkerheten og
minikartet med kystlinje.

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
SF_ID = "farstadsanden"   # spoten som får svak vind uten svell i alle timer, med ny retning hver time (S21 a, S24 a og S26)
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


def tankestreker():
    """S42: « - » og « – » i strenger og maler i docs/js (ikke kommentarer og ikke ${...}-uttrykk) og i teksten i docs/*.html."""
    funn = []
    for f in sorted((Path(__file__).resolve().parent.parent / "docs" / "js").glob("*.js")):
        t, ut = f.read_text(encoding="utf-8"), []
        def les(i, ln, slutt):   # kode fram til «}» på nivå 0 når slutt er sann, ellers til slutten av fila
            niva, forrige = 0, ""
            while i < len(t):
                c = t[i]
                if c == "\n": ln += 1; i += 1; continue
                if t.startswith("//", i): i = t.find("\n", i) if "\n" in t[i:] else len(t); continue
                if t.startswith("/*", i): j = t.index("*/", i); ln += t.count("\n", i, j); i = j + 2; continue
                if c in "\"'":
                    j = i + 1
                    while t[j] != c: j += 2 if t[j] == "\\" else 1
                    ut.append((ln, t[i + 1:j])); i = j + 1; forrige = "x"; continue
                if c == "`":
                    i += 1; start, buf = ln, ""
                    while t[i] != "`":
                        if t[i] == "\\": buf += t[i:i + 2]; i += 2; continue
                        if t.startswith("${", i): i, ln = les(i + 2, ln, True); buf += "X"; continue
                        ln += t[i] == "\n"; buf += t[i]; i += 1
                    ut.append((start, buf)); i += 1; forrige = "x"; continue
                if c == "/" and (forrige == "" or forrige in "(,=:[!&|?{};+>"):   # regulært uttrykk
                    j, klasse = i + 1, False
                    while t[j] != "\n" and (t[j] != "/" or klasse):
                        if t[j] == "\\": j += 1
                        elif t[j] == "[": klasse = True
                        elif t[j] == "]": klasse = False
                        j += 1
                    i = j + 1; forrige = "x"; continue
                if c == "{": niva += 1
                if c == "}":
                    if slutt and niva == 0: return i + 1, ln
                    niva -= 1
                if not c.isspace(): forrige = c
                i += 1
            return i, ln
        les(0, 1, False)
        assert len(ut) > 5 or f.stat().st_size < 12000, f"leseren fant for få strenger i {f.name}: {len(ut)}"
        funn += [f"{f.name}:{ln}: {s[max(0, m.start() - 30):m.end() + 30]}" for ln, s in ut for m in re.finditer(r"\S [-–—] \S", s)]
    for f in sorted((Path(__file__).resolve().parent.parent / "docs").glob("*.html")):
        ren = re.sub(r"<!--.*?-->|<script.*?</script>|<style.*?</style>", "", f.read_text(encoding="utf-8"), flags=re.S)
        funn += [f"{f.name}: {m.group(0)}" for m in re.finditer(r".{0,30}\S [-–—] \S.{0,30}", ren)]
    return funn


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
    // skilletegnet « · » i metalinja på Hjem (.sk) skal klippes bort når leddet står først på en linje (feiljegeren 25.11.2026,
    // funn 6). Bare tegnet er unntatt: selve leddene sjekkes som all annen tekst, og tegnets plass låses i fase 2-delen.
    if(a.el.classList.contains('sk') && a.el.closest('.favlinje .etikett')) continue;
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
  const buttons = [...document.querySelectorAll('button, a.tap, a.knapp1, .topnav a, .srad, .tabs a, .sokknapp, .chip, .dagfane, a.rad, a.favkort, a.favlinje')]
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
                mobile = vp[0] < 1024
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
                page.wait_for_function("window.Front && typeof DATA !== 'undefined' && DATA && document.querySelector('#viewHjem :is(#forside, .hjem-linje)')")
                cdp = ctx.new_cdp_session(page)

                # Kilden til lokale regler (10.11.2026, Unstads tidevannsregel): hver delregel skrives med sin egen
                # kilde, og hver kilde i spots.json har sin egen tekst i STR.localSourceText (ikke reserveteksten).
                for sp_ in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]:
                    lr_ = sp_.get("local_rules")
                    if not lr_:
                        continue
                    energi_, tide_, kjente_ = page.evaluate("(lr) => [localSourceText({local_rules: lr}, {}), localSourceText({local_rules: lr}, {}, 'tide'), Object.keys(STR.localSourceText)]", lr_)
                    assert lr_["source"] in kjente_ and lr_.get("tide_source", lr_["source"]) in kjente_, (sp_["id"], lr_, kjente_)
                    assert (energi_ == tide_) == ("tide_source" not in lr_), (sp_["id"], energi_, tide_)
                    if sp_["id"] == "unstad":
                        assert energi_ == "Grense satt ut fra observasjonene 26.09 til 05.10" and tide_ == "Ifølge Lofoten Surfsenter", (energi_, tide_)
                        assert page.evaluate("(lr) => localSourceLabel(lr.source, lr)", lr_) == "Observasjoner 26.09-05.10.2026; tidevann: Lofoten Surfsenter"
                    if sp_["id"] == "breivikeidet":
                        # 22.11.2026 (S19): tidevannsregelen på vannstanden har samme kilde som resten, og samme ordlyd som Unstads
                        assert energi_ == tide_ == "Grense satt ut fra observasjonene 17.11, 22.11 og 26.11", (energi_, tide_)   # 26.11.2026: tre dager
                        assert page.evaluate("(lr) => localSourceLabel(lr.source, lr)", lr_) == "Observasjoner 17.11-26.11.2026"

                # S28 (Theodor 23.11.2026): «Best på lavt vann» for en spot med regel på vannstanden (local_rules.tide_level, jo lavere jo
                # bedre - bare Breivikeidet), i tidevannscella (detailsGrid), forklaringen (EXPLAIN.tide) og tidevannskortet (Tidevann.html og
                # prefTekst, som også står i «Om spotten» på PC). Alle andre spots viser det samme som før. Spotmetaen er spots.json slik
                # publish.py legger den i detaljfila (local_rules og tide_regel), timene og tidevannet fra Grøtfjord i fiksturen.
                tv_spots = [x for x in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"] if x.get("status") != "hemmelig"]
                tv_h = details["grotfjord"]["hours"][now_idx(details["grotfjord"]["hours"])]
                for sp_ in tv_spots:
                    meta_ = dict(details["grotfjord"], **{k: v for k, v in sp_.items() if k in ("id", "name", "local_rules", "tide")}, tide_regel=publish.tide_regel(sp_))
                    if "local_rules" not in sp_: meta_.pop("local_rules", None)
                    if "tide" not in sp_: meta_.pop("tide", None)
                    got_ = page.evaluate("""([s, h]) => { const t = new Date(h.t), d = document.createElement('div');
                        d.innerHTML = detailsGrid(s, h, t); const celle = d.querySelector('[data-explain="tide"] .n').textContent;
                        d.innerHTML = Tidevann.html(s, t.getTime(), t.getTime(), true); const kort = d.querySelector('.tv-fot > span').textContent;
                        const fork = Object.fromEntries(EXPLAIN.tide.numbers(h, s))["Spoten"];
                        return {celle, kort, pref: Tidevann.prefTekst(s), fork, lav: tideLowBest(s)}; }""", [meta_, tv_h])
                    lav_ = bool((sp_.get("local_rules") or {}).get("tide_level"))
                    pref_ = (meta_["tide_regel"] or {}).get("prefer")
                    gammel_kort = (f"{sp_['name']} er best på " + {("lav",): "lav", ("lav", "middels"): "lav til middels", ("middels", "høy"): "middels til høy", ("høy",): "høy", ("middels",): "middels"}[tuple(x for x in ("lav", "middels", "høy") if x in pref_)] + " vannstand") if pref_ else "Spoten tåler alt tidevann"
                    if lav_:
                        # 26.11.2026 (svar.md 26.11.2026 kl. 13.10): regelen har et gulv, og ordet sier det
                        assert got_["kort"] == got_["pref"] == got_["fork"] == "Best på lavt vann, men ikke under ca. 1,6 m" and got_["lav"], (sp_["id"], got_)
                        assert got_["celle"].endswith("Best på lavt vann, men ikke under ca. 1,6 m") and "tåler alt" not in got_["celle"], got_
                    else:
                        # som før: cella sier «tåler alt» uten spot.tide, kortet følger tide_regel. Forklaringen sier «liker lav og middels vann» for
                        # en spot med lokal regel på flo og fjære (local_rules.tide_prefer, fysikk-kontrolløren 24.11.2026, vilkår 2), ellers «tåler alt»
                        lp_ = (sp_.get("local_rules") or {}).get("tide_prefer")
                        assert got_["kort"] == got_["pref"] == gammel_kort and got_["fork"] == (f"liker {' og '.join(lp_)} vann" if lp_ else "tåler alt tidevann") and got_["celle"].endswith("Spoten tåler alt tidevann") and not got_["lav"], (sp_["id"], got_)
                assert sorted(x["id"] for x in tv_spots if (x.get("local_rules") or {}).get("tide_level")) == ["breivikeidet"]
                # regelen må ha effekt: vekt 0 eller ingen økning mot flo er ikke «best på lavt vann»
                lr_b = next(x for x in tv_spots if x["id"] == "breivikeidet")["local_rules"]
                assert page.evaluate("(lr) => [tideLowBest({local_rules: lr}), tideLowBest({local_rules: {...lr, weight: 0}}), tideLowBest({local_rules: {...lr, tide_level: {...lr.tide_level, penalty: 0}}}), tideLowBest({}), tideLowBest(null)]", lr_b) == [True, False, False, False, False]
                # uten gulv (regelen slik den sto 22.11.2026) er ordet «Best på lavt vann» som før, i lang og kort form
                assert page.evaluate("(lr) => { const u = {...lr, tide_level: {full_below_cm: 200, max_at_cm: 280, penalty: 0.7}}; return [tideLowBestTekst({local_rules: u}), tideLowBestTekst({local_rules: u}, true), tideLowBestTekst({local_rules: lr}), tideLowBestTekst({local_rules: lr}, true), tideLowBestTekst({})]; }", lr_b) == ["Best på lavt vann", "Best på lavt vann", "Best på lavt vann, men ikke under ca. 1,6 m", "Best på lavt vann, over 1,6 m", ""]

                # S28: vindtallet rett under spotens egen grense (wind_calm_ms) er én desimal rundet ned, ellers hele m/s som før. Samme
                # regel som rating.wind_ms_text() i regnestykket, for 0-30 m/s i hundredeler uten grense og med grensene 8 og 14.
                vt_ = page.evaluate("() => { const ut = {}; for(const c of [null, 8, 14]) ut[String(c)] = Array.from({length: 3001}, (_, i) => windMsText({wind_speed: i / 100, wind_calm_ms: c})); return ut; }")
                for c_ in (None, 8.0, 14.0):
                    py_ = [rating.wind_ms_text(i / 100, c_) for i in range(3001)]
                    js_ = vt_[str(int(c_)) if c_ else "null"]
                    # Python runder x,5 til nærmeste partall, Intl.NumberFormat bort fra null: bare tallene utenfor grensesonen kan skille
                    avvik_ = [i / 100 for i in range(3001) if js_[i] != py_[i] and not (i % 100 == 50 and abs(float(py_[i].replace(",", ".")) - float(js_[i].replace(",", "."))) == 1)]
                    assert not avvik_, (c_, avvik_[:10])
                    if c_:
                        lo_ = int(c_ * 100) - 50
                        assert [js_[i] for i in (lo_ - 1, lo_, lo_ + 46, lo_ + 49, int(c_ * 100))] == [str(int(c_) - 1), f"{int(c_) - 1},5", f"{int(c_) - 1},9", f"{int(c_) - 1},9", str(int(c_))], (c_, [js_[i] for i in (lo_ - 1, lo_, lo_ + 46, lo_ + 49, int(c_ * 100))])

                # «For mye vind» (Theodor S15 a, 17.11.2026): fralandsvind som har tatt poeng heter ikke «Blåst ut». «Blåst ut» står
                # når vinden ikke er fralands, og når ingen poeng er tapt på vind (det meste er vindsjø i svak fralandsvind).
                vo = page.evaluate("""() => { const b = {stars: 0, period: 10, surf_height: 1.2, wind_speed: 15, light: 'dag'}, z = (w) => ({energy: 0, wind: w, tide: 0, local: 0, cap: 0});
                    const par = (x) => [ratingWord({...b, ...x}), ratingWordExplain({...b, ...x})];
                    return {fra: par({low_reason: 'blown_out', wind_type: 'offshore', zero_losses: z(3)}), gammel: par({low_reason: 'blown_out', wind_type: 'offshore', faded_wind: 2}),
                        null_fra: par({wind_type: 'offshore', zero_losses: z(3)}), pa: par({low_reason: 'blown_out', wind_type: 'onshore', zero_losses: z(3)}),
                        side: par({low_reason: 'blown_out', wind_type: 'side', zero_losses: z(2)}), sjo: par({low_reason: 'blown_out', wind_type: 'offshore', wind_speed: 3, zero_losses: z(0)}),
                        null_pa: par({wind_type: 'onshore', zero_losses: z(3)}),
                        sterk: par({low_reason: 'blown_out', wind_type: 'offshore', wind_speed: 15, zero_losses: z(0)}), kast: par({low_reason: 'blown_out', wind_type: 'offshore', wind_speed: 10.5, gust: 17, zero_losses: z(0)}),
                        band: par({low_reason: 'blown_out', wind_type: 'offshore', wind_speed: 11, faded_wind: 1, zero_losses: z(0)}), under: par({low_reason: 'blown_out', wind_type: 'offshore', wind_speed: 11.5, gust: 12, zero_losses: z(0)}),
                        ukjent: par({low_reason: 'blown_out', wind_type: 'offshore', wind_speed: null, zero_losses: z(0)}), sterk_pa: par({low_reason: 'blown_out', wind_type: 'onshore', wind_speed: 15, zero_losses: z(0)}), ny: STR.wordTooMuchWind, ut: STR.lowReason.blown_out, fork: STR.wordExplain[STR.wordTooMuchWind]}; }""")
                assert vo["ny"] == "For mye vind" and vo["ny"] != vo["ut"] and vo["fork"], vo
                assert vo["fra"] == [vo["ny"], vo["fork"]] and vo["null_fra"] == [vo["ny"], vo["fork"]] and vo["gammel"][0] == vo["ny"], f"fralandsvind som tar poengene skal hete «{vo['ny']}»: {vo}"
                # sterk fralandsvind uten poeng å ta (potensial 0) og båndet der bare faded_wind viser tapet (fysikk-kontrolløren 19.11.2026)
                assert all(vo[k][0] == vo["ny"] for k in ("sterk", "kast", "band")), f"sterk fralandsvind skal hete «{vo['ny']}» også uten tapte poeng: {vo}"
                assert all(vo[k][0] == vo["ut"] for k in ("pa", "side", "sjo", "null_pa", "under", "ukjent", "sterk_pa")), f"«{vo['ut']}» skal stå når vinden ikke er fralands, eller er svakere enn 12 m/s uten tapte poeng: {vo}"

                # Ukjent vind (fysikk-kontrolløren 19.11.2026, forslag S22). Mangler vindstyrken, bokfører henteren det faste poenget
                # som usikkert varsel (zero_losses.cap), og ordet ved 0 poeng er «Ikke surfbart nå», aldri «Blåst ut». Er styrken kjent
                # og retningen ukjent, heter vind som tar poeng (eller er fra 8 m/s) «For mye vind».
                uv = page.evaluate("""() => { const b = {stars: 0, period: 10, surf_height: 1.0, light: 'dag'}, z = (w, c) => ({energy: 0, wind: w, tide: 0, local: 0, cap: c});
                    return {styrke: [ratingWord({...b, low_reason: null, wind_speed: null, wind_type: null, zero_losses: z(0, 1)}), ratingWordExplain({...b, low_reason: null, wind_speed: null, wind_type: null, zero_losses: z(0, 1)})],
                        retning: ratingWord({...b, low_reason: 'blown_out', wind_speed: 9, wind_type: null, zero_losses: z(0, 0)}), tapt: ratingWord({...b, stars: 1, low_reason: 'blown_out', wind_speed: 7.9, wind_type: null, zero_losses: z(2, 0)}),
                        null_retning: ratingWord({...b, wind_speed: 7.9, wind_type: null, zero_losses: z(2, 0)}), svak: ratingWord({...b, low_reason: 'blown_out', wind_speed: 3, wind_type: null, zero_losses: z(0, 0)}),
                        maalt: ratingWord({...b, low_reason: 'blown_out', wind_speed: null, wind_type: null, zero_losses: z(0, 1)}),
                        atte: ratingWord({...b, low_reason: 'blown_out', wind_speed: 8, wind_type: null, zero_losses: z(0, 0)}), under: ratingWord({...b, low_reason: 'blown_out', wind_speed: 7.9, wind_type: null, zero_losses: z(0, 0)}),
                        kast: ratingWord({...b, low_reason: 'blown_out', wind_speed: 6, gust: 14, wind_type: null, zero_losses: z(0, 0)}),
                        ikke: STR.wordNotNow, cap: STR.notNowCap, mye: STR.wordTooMuchWind, ut: STR.lowReason.blown_out}; }""")
                assert uv["styrke"] == [uv["ikke"], uv["cap"]] and uv["ikke"] == "Ikke surfbart nå", f"ukjent vindstyrke ved 0 poeng skal hete «{uv['ikke']}»: {uv}"
                assert uv["retning"] == uv["mye"] and uv["tapt"] == uv["mye"] and uv["null_retning"] == uv["mye"], f"ukjent retning med kjent styrke skal hete «{uv['mye']}»: {uv}"
                # svak vind fra ukjent retning som ikke har tatt poeng, og målt vindsjø uten vindvarsel (rating.is_blown_out), beholder «Blåst ut»
                # når surfehøyden er fra 0,8 m (her 1,0 m). Under 0,8 m følger ordet surfehøyden, se «svak vind uten poengtap» under (S24 a, S26 b).
                assert uv["svak"] == uv["ut"] and uv["maalt"] == uv["ut"], uv
                # grensa er 8 m/s på vindstyrken uten kast, som BLOWN_OUT_WIND_MS i henteren: 8,0 er «For mye vind», 7,9 og 6 m/s med kast 14 er det ikke
                assert uv["atte"] == uv["mye"] and uv["under"] == uv["ut"] and uv["kast"] == uv["ut"], f"grensa for ukjent retning skal være 8 m/s uten kast: {uv}"

                # Svak vind uten poengtap (Theodor S21 a, 20.11.2026, S24 a, 22.11.2026, og S26 b, 23.11.2026): appen skylder ikke på vinden
                # når det ikke er svell. Ordet følger surfehøyden: «Flatt» under 0,3 m, «Smått» fra 0,3 m. Fra 0,8 m er det bølger (vindsjø),
                # og «Blåst ut» står. Svak er effektiv vind med kast (effectiveWind, samme mål som vindkurven) under 12 m/s fralands og under
                # 8 m/s fra alle andre retninger, også ukjent.
                sf = page.evaluate("""() => { const b = {stars: 0, period: 4, low_reason: 'blown_out', wind_type: 'offshore', wind_speed: 4, bw_height: 0.6, light: 'dag'}, z = (w) => ({energy: 0, wind: w, tide: 0, local: 0, cap: 0});
                    const alt = (x) => { const h = {...b, zero_losses: z(0), ...x}; return [ratingWord(h), ratingWordExplain(h), heightMForDisplay(h), lowReasonNotice(h)]; };
                    return {null_m: alt({surf_height: 0}), under: alt({surf_height: 0.29}), paa: alt({surf_height: 0.3}), smaa: alt({surf_height: 0.79}), stor: alt({surf_height: 0.8}),
                        mangler: alt({surf_height: null}), tapt: alt({surf_height: 0.1, zero_losses: z(1)}), falmet: alt({surf_height: 0.1, faded_wind: 1}), sterk: alt({surf_height: 0.1, wind_speed: 12}),
                        kast: alt({surf_height: 0.1, wind_speed: 10.5, gust: 17}), elleve: alt({surf_height: 0.1, wind_speed: 11.9}), styrke: alt({surf_height: 0.1, wind_speed: null}),
                        paland: alt({surf_height: 0.1, wind_type: 'onshore'}), side: alt({surf_height: 0.1, wind_type: 'side'}), retning: alt({surf_height: 0.1, wind_type: null}),
                        skra: alt({surf_height: 0, wind_type: 'sideonshore'}), side_smaa: alt({surf_height: 0.5, wind_type: 'side'}), pa_smaa: alt({surf_height: 0.79, wind_type: 'onshore'}),
                        pa_under: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 7.9}), side_under: alt({surf_height: 0.1, wind_type: 'side', wind_speed: 7.9}), retn_under: alt({surf_height: 0.1, wind_type: null, wind_speed: 7.9}),
                        skra_under: alt({surf_height: 0.1, wind_type: 'sideonshore', wind_speed: 7.9}), pa_lavkast: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 7.9, gust: 5}),
                        pa_kast_under: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 6, gust: 12}), side_kast_under: alt({surf_height: 0.1, wind_type: 'side', wind_speed: 6.5, gust: 11.4}),
                        retn_kast_under: alt({surf_height: 0.1, wind_type: null, wind_speed: 6, gust: 12}), skra_kast_under: alt({surf_height: 0.1, wind_type: 'sideonshore', wind_speed: 7, gust: 10.3}),
                        pa_kast: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 6, gust: 14}), pa_kast12: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 7.9, gust: 12}),
                        side_kast: alt({surf_height: 0.1, wind_type: 'side', wind_speed: 6.5, gust: 11.5}), skra_kast12: alt({surf_height: 0, wind_type: 'sideonshore', wind_speed: 7.9, gust: 12}),
                        retn_kast: alt({surf_height: 0.1, wind_type: null, wind_speed: 6, gust: 14}),
                        pa_atte: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 8}), side_atte: alt({surf_height: 0.1, wind_type: 'side', wind_speed: 8}), skra_atte: alt({surf_height: 0.1, wind_type: 'sideonshore', wind_speed: 8}),
                        retn_atte: alt({surf_height: 0.1, wind_type: null, wind_speed: 8}), fra_atte: alt({surf_height: 0.1, wind_speed: 8}), fra_kast: alt({surf_height: 0.1, wind_speed: 8, gust: 14}),
                        pa_tapt: alt({surf_height: 0.1, wind_type: 'onshore', zero_losses: z(1)}), side_falmet: alt({surf_height: 0.1, wind_type: 'side', faded_wind: 1}), retn_tapt: alt({surf_height: 0.1, wind_type: null, zero_losses: z(1)}),
                        pa_styrke: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: null}), pa_mangler: alt({surf_height: null, wind_type: 'onshore'}), pa_stor: alt({surf_height: 0.8, wind_type: 'onshore'}),
                        side_ett: alt({surf_height: 0.5, stars: 1, wind_type: 'side'}),
                        egen_skra: alt({surf_height: 0.1, wind_type: 'sideonshore', wind_speed: 8.2, gust: 14, wind_calm_ms: 14}), egen_under: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 13.9, gust: 22, wind_calm_ms: 14}),
                        egen_paa: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 14, wind_calm_ms: 14}), egen_bre: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 6.5, gust: 11.5, wind_calm_ms: 8}),
                        egen_bre_paa: alt({surf_height: 0.1, wind_type: 'onshore', wind_speed: 8, wind_calm_ms: 8}), egen_fra: alt({surf_height: 0.1, wind_speed: 11.9, gust: 20, wind_calm_ms: 8}),
                        egen_fra_paa: alt({surf_height: 0.1, wind_speed: 12, wind_calm_ms: 8}), egen_fra14: alt({surf_height: 0.1, wind_speed: 13.9, gust: 20, wind_calm_ms: 14}),
                        egen_retn: alt({surf_height: 0.1, wind_type: null, wind_speed: 9, wind_calm_ms: 14}), egen_retn_paa: alt({surf_height: 0.1, wind_type: null, wind_speed: 14, wind_calm_ms: 14}),
                        egen_stor: alt({surf_height: 0.8, wind_type: 'onshore', wind_speed: 5, wind_calm_ms: 14}),
                        ett: alt({surf_height: 0.5, stars: 1}), flat: alt({surf_height: 0.1, low_reason: 'flat'}), stormsjo: alt({surf_height: 0.1, low_reason: 'stormsjo'}),
                        flatt: STR.starWords[0], smatt: STR.wordSmall, smatt_fork: STR.wordExplain[STR.wordSmall], daarlig: STR.starWords[1], ut: STR.lowReason.blown_out, ut_fork: STR.wordExplain[STR.lowReason.blown_out],
                        mye: STR.wordTooMuchWind, mye_fork: STR.wordExplain[STR.wordTooMuchWind], setn: STR.notice.blown_out + '.', setn_storm: STR.notice.stormsjo + '.'}; }""")
                assert (sf["flatt"], sf["smatt"], sf["daarlig"], sf["ut"], sf["mye"]) == ("Flatt", "Smått", "Dårlig", "Blåst ut", "For mye vind"), sf
                # ordet, forklaringen, høyden som vises og setningen på forsiden: en flat time har ingen av de tre siste
                assert sf["null_m"] == [sf["flatt"], None, None, None] and sf["under"] == [sf["flatt"], None, None, None], f"svak fralandsvind uten svell skal hete «{sf['flatt']}» uten tall og uten setning om vinden: {sf}"
                assert sf["paa"] == [sf["smatt"], sf["smatt_fork"], None, None] and sf["smaa"] == [sf["smatt"], sf["smatt_fork"], None, None], f"fra 0,3 m skal ordet være «{sf['smatt']}»: {sf}"
                assert sf["elleve"][0] == sf["flatt"] and sf["elleve"][3] is None, f"under 12 m/s uten tapte poeng gjelder regelen: {sf}"
                # fra 0,8 m, og når høyden eller vindstyrken mangler (manglende data er aldri 0), står «Blåst ut» med tallet og setningen som før
                assert sf["stor"] == [sf["ut"], sf["ut_fork"], 0.8, sf["setn"]] and sf["mangler"] == [sf["ut"], sf["ut_fork"], 0.6, sf["setn"]] and sf["styrke"] == [sf["ut"], sf["ut_fork"], 0.1, sf["setn"]], sf
                # vind som har tatt poeng eller er fra 12 m/s (med kast), heter «For mye vind» som før (S15 a), med den nye forklaringen (S21 b)
                assert all(sf[k] == [sf["mye"], sf["mye_fork"], 0.1, sf["setn"]] for k in ("tapt", "falmet", "sterk", "kast")), f"vind som tar poeng eller er sterk skal hete «{sf['mye']}»: {sf}"
                assert sf["mye_fork"] == "Vinden er for sterk." and sf["mye_fork"] != sf["ut_fork"], sf
                # alle retninger (S24 a): svak pålandsvind, sidevind, skrå pålandsvind og vind fra ukjent retning får ordet etter surfehøyden.
                # Rett under grensa: 7,9 m/s uten kast, kast under middelvinden, og kast som teller til 7,8-7,99 (S26 b).
                svake = ("paland", "side", "retning", "skra", "pa_under", "side_under", "retn_under", "skra_under", "pa_lavkast", "pa_kast_under", "side_kast_under", "retn_kast_under", "skra_kast_under")
                assert all(sf[k] == [sf["flatt"], None, None, None] for k in svake), f"svak vind uten poengtap skal hete «{sf['flatt']}» fra alle retninger: { {k: sf[k] for k in svake} }"
                assert sf["side_smaa"] == [sf["smatt"], sf["smatt_fork"], None, None] and sf["pa_smaa"] == [sf["smatt"], sf["smatt_fork"], None, None], f"fra 0,3 m skal ordet være «{sf['smatt']}» også i side- og pålandsvind: {sf}"
                # grensa er 8 m/s effektiv vind med kast (S26 b, som fysikk-kontrolløren): 8,0 m/s, 6 m/s med kast 14 (teller som 8,0),
                # 6,5 med kast 11,5 (8,0) og 7,9 med kast 12 (9,1, Horseid- og Bunes-typen 22.11) er ikke svak. Da står «Blåst ut» med tallet
                # og setningen. Fralandsvind på 8 m/s, også med kast 14, er fortsatt svak (grensa der er 12 m/s med kast).
                sterke = ("pa_atte", "side_atte", "skra_atte", "pa_kast", "pa_kast12", "side_kast")
                assert all(sf[k] == [sf["ut"], sf["ut_fork"], 0.1, sf["setn"]] for k in sterke), f"fra 8 m/s med kast skal side- og pålandsvind hete «{sf['ut']}»: { {k: sf[k] for k in sterke} }"
                assert sf["skra_kast12"] == [sf["ut"], sf["ut_fork"], 0.6, sf["setn"]], sf   # 0,0 m: tallet er BarentsWatch-høyden som før
                assert sf["fra_atte"] == [sf["flatt"], None, None, None] and sf["fra_kast"] == [sf["flatt"], None, None, None], sf
                # ukjent retning: «For mye vind» fra 8 m/s middelvind (windLossWord, som før). Under det, men fra 8 m/s med kast, «Blåst ut».
                assert sf["retn_atte"] == [sf["mye"], sf["mye_fork"], 0.1, sf["setn"]] and sf["retn_kast"] == [sf["ut"], sf["ut_fork"], 0.1, sf["setn"]], sf
                # vind som har tatt poeng, er ikke svak: «Blåst ut» fra siden og fra havet, «For mye vind» når retningen er ukjent
                assert sf["pa_tapt"] == [sf["ut"], sf["ut_fork"], 0.1, sf["setn"]] and sf["side_falmet"] == [sf["ut"], sf["ut_fork"], 0.1, sf["setn"]] and sf["retn_tapt"] == [sf["mye"], sf["mye_fork"], 0.1, sf["setn"]], sf
                # manglende vindstyrke eller surfehøyde er aldri 0, og fra 0,8 m er det bølger: «Blåst ut» som før
                assert sf["pa_styrke"] == [sf["ut"], sf["ut_fork"], 0.1, sf["setn"]] and sf["pa_mangler"] == [sf["ut"], sf["ut_fork"], 0.6, sf["setn"]] and sf["pa_stor"] == [sf["ut"], sf["ut_fork"], 0.8, sf["setn"]], sf
                assert sf["side_ett"][0] == sf["daarlig"] and sf["side_ett"][2] == 0.5 and sf["side_ett"][3] is None, sf
                # Spots med egen vindkurve (Unstad 14 m/s, Breivikeidet 8) har grensa si med i timen (wind_calm_ms, fysikk-kontrolløren og
                # feiljegeren 23.11.2026): ordet skylder på vinden først fra spotens grense, målt på middelvinden uansett kast, og fralands fra
                # den høyeste av grensa og 12 m/s. Unstad 22.11 kl. 11Z (8,2 m/s skrått pålands, kast 14) heter «Flatt», ikke «Blåst ut».
                egne_svake = ("egen_skra", "egen_under", "egen_bre", "egen_fra", "egen_fra14", "egen_retn")
                assert all(sf[k] == [sf["flatt"], None, None, None] for k in egne_svake), f"under spotens egen vindgrense skal ordet følge surfehøyden: { {k: sf[k] for k in egne_svake} }"
                assert sf["egen_paa"] == [sf["ut"], sf["ut_fork"], 0.1, sf["setn"]] and sf["egen_bre_paa"] == [sf["ut"], sf["ut_fork"], 0.1, sf["setn"]] and sf["egen_stor"] == [sf["ut"], sf["ut_fork"], 0.8, sf["setn"]], sf
                assert sf["egen_fra_paa"] == [sf["mye"], sf["mye_fork"], 0.1, sf["setn"]] and sf["egen_retn_paa"] == [sf["mye"], sf["mye_fork"], 0.1, sf["setn"]], sf
                # Samme grense i henteren (S26): windBlamed i appen og publish.wind_blamed() (dagens time, best_hour) er like for
                # alle kombinasjoner av retning, vind, kast, høyde, poengtap, poeng og spotens egen vindgrense (ingen, 8 og 14 m/s).
                # Og ordet og windBlamed sier det samme.
                import publish as _pub_s26
                _z = lambda w: {"energy": 0, "wind": w, "tide": 0, "local": 0, "cap": 0}
                grid = [dict(low_reason=lr, stars=st, wind_type=wt, wind_speed=ws, gust=gu, surf_height=sh, zero_losses=_z(zw), faded_wind=fw, bw_height=1.0, period=8, light="dag", wind_calm_ms=cm)
                        for lr in ("blown_out", "flat") for st in (0, 1) for wt in ("offshore", "side", "sideonshore", "onshore", None)
                        for ws in (None, 0, 5, 6.5, 7, 7.9, 8, 9, 11, 11.9, 12, 13.9, 14) for gu in (None, 5, 10.3, 11.4, 11.5, 12, 14, 14.4, 20) for cm in (None, 8, 14)
                        for sh in (None, 0, 0.29, 0.5, 0.79, 0.8) for zw, fw in ((0, 0), (1, 0), (0, 1)) if lr == "blown_out" or (wt == "side" and zw == fw == 0)]
                js_wb = page.evaluate("(g) => g.map(h => [windBlamed(h), ratingWord(h)])", grid)
                avvik = [(h, j) for h, j in zip(grid, js_wb) if j[0] != _pub_s26.wind_blamed(h)]
                assert not avvik, f"windBlamed (app.js) og publish.wind_blamed ulike i {len(avvik)} av {len(grid)} timer, f.eks. {avvik[:3]}"
                assert all(j[0] == (j[1] in (sf["ut"], sf["mye"])) for h, j in zip(grid, js_wb) if h["low_reason"] == "blown_out"), "windBlamed skal være sann nøyaktig når ordet skylder på vinden"
                # Dagens time ved likt poeng og lik høyde (S26, feiljegeren 22.11): en time der vinden får skylda går foran, ellers den
                # første. betterDayHour i appen, bestOfDay og spanOfDay i spotgraf.js og publish.best_hour gir samme time og samme ord.
                dr = page.evaluate("""() => { SpotGraf.defaultDay({hours: []}, 0, Front.helpers);   // hjelperne bestOfDay bruker (settes ellers av spotsiden)
                    const z = {energy: 0, wind: 0, tide: 0, local: 0, cap: 0};
                    const bo = (t, ws, wt, x) => ({t, stars: 0, low_reason: 'blown_out', wind_type: wt, wind_speed: ws, surf_height: 0, surf_height_sets: 0, bw_height: 1.2, zero_losses: z, light: 'dag', ...(x || {})});
                    const velg = (hours) => { const s = {id: 'x', hours}, d = {key: '2026-11-22', idxs: hours.map((_, i) => i), step: 1}; const i = SpotGraf.bestOfDay(s, d);
                        return [hours[i].t, ratingWord(hours[i]), SpotGraf.spanOfDay(s, d).word]; };
                    return {horseid: velg([bo('11', 8.2, 'sideonshore'), bo('12', 7.9, 'sideonshore'), bo('13', 7.4, 'onshore')]),
                        snudd: velg([bo('13', 7.4, 'onshore'), bo('12', 7.9, 'sideonshore'), bo('11', 8.2, 'sideonshore')]),
                        kast: velg([bo('11', 3, 'onshore'), bo('12', 7.9, 'onshore', {gust: 12}), bo('13', 9, 'side')]),
                        svake: velg([bo('11', 3, 'onshore'), bo('12', 5, 'side'), bo('13', 2, 'offshore')]),
                        hoyde: velg([bo('11', 9, 'onshore'), bo('12', 3, 'side', {surf_height: 0.5, surf_height_sets: 0.6})]),
                        poeng: velg([bo('11', 9, 'onshore'), bo('12', 3, 'side', {stars: 1, low_reason: null, surf_height: 0.3}), bo('13', 3, 'side', {surf_height: 0.5})]),
                        mork: velg([bo('11', 9, 'onshore', {light: 'mørkt'}), bo('12', 3, 'side'), bo('13', 7.9, 'onshore')])}; }""")
                assert dr["horseid"][:2] == ["11", sf["ut"]] and dr["snudd"][:2] == ["11", sf["ut"]], f"Horseid-typen: dagen skal hete «{sf['ut']}» uansett rekkefølge: {dr}"
                assert dr["kast"][:2] == ["12", sf["ut"]] and dr["svake"][:2] == ["11", sf["flatt"]], dr
                assert dr["hoyde"][:2] == ["12", sf["smatt"]] and dr["poeng"][:2] == ["12", sf["daarlig"]] and dr["mork"][:2] == ["12", sf["flatt"]], dr
                assert all(v[2] == v[1] for v in dr.values()), f"ordet i dagfanen (spanOfDay) skal være ordet for dagens time: {dr}"
                # og publish.best_hour velger samme time for de samme dagene
                _bo = lambda t, ws, wt, **x: dict({"t": t, "stars": 0, "low_reason": "blown_out", "wind_type": wt, "wind_speed": ws, "surf_height": 0, "zero_losses": _z(0), "light": "dag"}, **x)
                for navn, hs in (("horseid", [_bo("11", 8.2, "sideonshore"), _bo("12", 7.9, "sideonshore"), _bo("13", 7.4, "onshore")]),
                                 ("snudd", [_bo("13", 7.4, "onshore"), _bo("12", 7.9, "sideonshore"), _bo("11", 8.2, "sideonshore")]),
                                 ("kast", [_bo("11", 3, "onshore"), _bo("12", 7.9, "onshore", gust=12), _bo("13", 9, "side")]),
                                 ("svake", [_bo("11", 3, "onshore"), _bo("12", 5, "side"), _bo("13", 2, "offshore")]),
                                 ("hoyde", [_bo("11", 9, "onshore"), _bo("12", 3, "side", surf_height=0.5)]),
                                 ("mork", [_bo("11", 9, "onshore", light="mørkt"), _bo("12", 3, "side"), _bo("13", 7.9, "onshore")])):
                    assert _pub_s26.best_hour(hs)[0]["t"] == dr[navn][0], (navn, dr[navn])
                # en time med 1 poeng får poengordet og tallet sitt, og andre grunner er urørt
                assert sf["ett"][0] == sf["daarlig"] and sf["ett"][2] == 0.5 and sf["ett"][3] is None, sf
                assert sf["flat"][0] == sf["flatt"] and sf["flat"][2] is None and sf["stormsjo"][0] == "Stormsjø" and sf["stormsjo"][2] == 0.6, sf
                # regelen gjelder bare `blown_out`: stormsjø i svak fralandsvind beholder setningen sin på forsiden
                assert sf["stormsjo"][3] == sf["setn_storm"] == "Mest vindsjø, lite ekte svell.", sf

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
                            spot = spot.removesuffix(" (foreløpig)")   # en ny spot har «(foreløpig)» bak navnet (S45 3 a)
                            rad = next((r for r in rader if r["navn"].lower() == spot.lower()), None)
                            assert rad, f"overskriften nevner «{spot}», som ikke står i lista: {setn}"
                            i = kol(dag)
                            # ordet er ordet for tallet, eller årsaksordet («Blåst ut») når timen har en low_reason - på dag 0 står det i raden
                            assert rad["celler"][i].isdigit() and int(rad["celler"][i]) >= 1 and (hj["ord"][int(rad["celler"][i])] == ordet or ordet in hj["nullord"]), f"«{setn}» stemmer ikke med ruta {rad['celler'][i]} for {spot}"
                            # andre setning (en senere dag) sies bare fra 2 poeng (Theodor 16.11.2026)
                            assert nr == 0 or i == 0 or int(rad["celler"][i]) >= 2, f"«{setn}» som andre setning, men ruta er {rad['celler'][i]}"
                            assert i > 0 or f"{ordet}" in rad["meta"], f"«{setn}», men raden sier {rad['meta']}"
                            assert all(not r["celler"][i].isdigit() or int(r["celler"][i]) <= int(rad["celler"][i]) for r in rader), f"«{setn}», men en annen favoritt har høyere tall den dagen"
                            continue
                        # dårlig dag og en bedre dag senere: rådet (designrevisjon fase 3 punkt 5). «Lite å hente i dag.» sies
                        # bare når ingen favoritt har 2 eller mer den dagen og ingen mangler data, og andre setning er da
                        # «X er best, dag.» med den beste dagen (fra 2 poeng) senere i lista
                        mm = re.match(rf"^Lite å hente {DAG_RE}\.$", setn)
                        if mm:
                            i = kol(mm.group(1))
                            assert nr == 0 and i == 0 and len(hj["set"]) == 2, f"«{setn}» skal være første setning og ha et råd etter seg: {hj['set']}"
                            assert all(not r["celler"][0].isdigit() or int(r["celler"][0]) < 2 for r in rader), f"«{setn}», men en favoritt har 2 eller mer: {[r['celler'][0] for r in rader]}"
                            assert any(r["celler"][0].isdigit() for r in rader) and not any("miss" in r["cls"][0] for r in rader), f"«{setn}»: {[(r['celler'][0], r['cls'][0]) for r in rader]}"
                            continue
                        mm = re.match(rf"^(.+) er best, {DAG_RE}(?:, usikkert)?\.$", setn)
                        if mm:
                            spot, dag = mm.groups()
                            spot = spot.removesuffix(" (foreløpig)")
                            assert nr == 1 and hj["set"][0].startswith("Lite å hente "), f"«{setn}» uten «Lite å hente» foran: {hj['set']}"
                            rad = next((r for r in rader if r["navn"].lower() == spot.lower()), None)
                            assert rad, f"overskriften nevner «{spot}», som ikke står i lista: {setn}"
                            i = kol(dag)
                            assert i > 0 and rad["celler"][i].isdigit() and int(rad["celler"][i]) >= 2, f"«{setn}», men ruta er {rad['celler'][i]}"
                            beste = max(int(r["celler"][k]) for r in rader for k in range(1, len(r["celler"])) if r["celler"][k].isdigit())
                            assert int(rad["celler"][i]) == beste, f"«{setn}», men den beste ruta senere er {beste}"
                            continue
                        mm = re.match(r"^Best kl\. (\d\d)–(\d\d)\.$", setn)
                        if mm:
                            m1 = re.match(rf"^(.+) på (.+) {DAG_RE}\.$", hj["set"][0])
                            assert nr == 1 and m1, f"«{setn}» uten en spot i første setning: {hj['set']}"
                            rad = next(r for r in rader if r["navn"].lower() == m1.group(2).removesuffix(" (foreløpig)").lower())
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
                    const forbud = {restriksjoner: [{type: 'surfeforbud', gjelder: 'sjø'}]}, ny = {status: 'forelopig'}, PF = STR.spotForelopig('P');
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
                        'lyset over for én, surf senere': t([spot('A', ['over', 0, 3, 0]), spot('B', [0])], true, [H.ingenRest, H.ordSpot(W[3], 'A', dag(2))]),
                        'lyset over for én, 1 poeng hos den andre': t([spot('A', ['over', 0, 3, 0]), spot('B', [1, 0])], true, [H.ordSpot(W[1], 'B', dag(0)), H.ordSpot(W[3], 'A', dag(2))]),
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
                        'foreløpig favoritt teller': t([spot('A', [0]), spot('P', [3, 0], ny)], true, [H.ordSpot(W[3], PF, dag(0)), best]),
                        'foreløpig utenfor favorittene': t([spot('A', [2, 0]), spot('P', [3, 0], ny)], false, [H.ordSpot(W[2], 'A', dag(0)), best]),
                        'bare foreløpig er surfbar': t([spot('A', [0]), spot('P', [3, 0], ny)], false, [H.ordSpot(W[3], PF, dag(0)), best]),
                        // S45 3 a (svar.md 26.11.2026 kl. 13.10): en ny spot nevnes når den har minst 2 og alle andre er under 2, med «foreløpig» bak navnet
                        'ny spot med 2, de andre under 2': t([spot('A', [1, 0]), spot('B', [0]), spot('P', [2, 0], ny)], false, [H.ordSpot(W[2], PF, dag(0)), best]),
                        'ny spot med 3, en annen har 1': t([spot('A', [1, 0]), spot('P', [3, 0], ny)], false, [H.ordSpot(W[3], PF, dag(0)), best]),
                        'ny spot med 2, en annen har 2': t([spot('A', [2, 0]), spot('P', [2, 0], ny)], false, [H.ordSpot(W[2], 'A', dag(0)), best]),
                        'ny spot med 5, en annen har 2': t([spot('A', [2, 0]), spot('P', [5, 0], ny)], false, [H.ordSpot(W[2], 'A', dag(0)), best]),
                        'ny spot med 1, en annen har 1': t([spot('A', [1, 0]), spot('P', [1, 0], ny)], false, [H.ordSpot(W[1], 'A', dag(0)), best]),
                        'ny spot med 1, de andre har 0 (eldre regel)': t([spot('A', [0]), spot('P', [1, 0], ny)], false, [H.ordSpot(W[1], PF, dag(0)), best]),
                        'ny spot senere i uka': t([spot('A', [1, 0]), spot('P', [0, 0, 3, 0], ny)], false, [H.lite(dag(0)), H.bestSpot(PF, dag(2))]),
                        'ny spot senere, en annen har 2 den dagen': t([spot('A', [1, 0, 2, 0]), spot('P', [0, 0, 3, 0], ny)], false, [H.lite(dag(0)), H.bestSpot('A', dag(2))]),
                        'ny spot med forbud løftes ikke fram': t([spot('A', [1, 0]), spot('P', [3, 0], Object.assign({}, ny, forbud))], false, [H.ordSpot(W[1], 'A', dag(0)), best]),
                        'gammel foreløpig spot (over 14 dager) teller som de andre, med merket': t([spot('A', [2, 0]), spot('P', [3, 0], {status: 'forelopig', forelopig_fra: '2020-01-01'})], false, [H.ordSpot(W[3], PF, dag(0)), best]),
                        'andel_forelopig er ikke en ny spot': t([spot('A', [1, 0]), spot('P', [3, 0], {andel_forelopig: true})], false, [H.ordSpot(W[3], 'P', dag(0)), best]),
                        // en spot med status «hemmelig» skal aldri finnes i dataene (CLAUDE.md), og nevnes uansett aldri
                        'hemmelig spot nevnes aldri': t([spot('A', [1, 0]), spot('HEMMELIGX', [5], {status: 'hemmelig'})], false, [H.ordSpot(W[1], 'A', dag(0)), best]),
                        'hemmelig favoritt nevnes aldri': t([spot('A', [0]), spot('HEMMELIGX', [5], {status: 'hemmelig'})], true, [H.ord(W[0], dag(0)), H.ingenNeste(n)]),
                        'bare en hemmelig spot': t([spot('HEMMELIGX', [5], {status: 'hemmelig'})], false, []),
                        'bedre dag senere': t([spot('A', [2, 0, 4, 0]), spot('B', [1, 3, 0])], true, [H.ordSpot(W[2], 'A', dag(0)), H.ordSpot(W[4], 'A', dag(2))]),
                        'bare 1 poeng senere': t([spot('A', [0, 0, 1, 0])], true, [H.ord(W[0], dag(0))]),
                        '1 poeng før 2 poeng senere': t([spot('A', [0, 1, 0, 2, 0])], true, [H.lite(dag(0)), H.bestSpot('A', dag(3))]),
                        'råd: 1 i dag, 3 senere hos en annen': t([spot('A', [1, 0]), spot('B', [0, 0, 3, 0])], true, [H.lite(dag(0)), H.bestSpot('B', dag(2))]),
                        'ikke råd når dagen har 2': t([spot('A', [2, 0, 4, 0])], true, [H.ordSpot(W[2], 'A', dag(0)), H.ordSpot(W[4], 'A', dag(2))]),
                        'ikke råd når data mangler i dag': t([spot('A', [0, 3]), spot('B', ['miss', 0])], true, [H.manglerDag(dag(0)), H.ordSpot(W[3], 'A', dag(1))]),
                        'ikke råd i mørket': t([spot('A', ['dark', 3])], true, [H.morkt(dag(0)), H.ordSpot(W[3], 'A', dag(1))]),
                        '1 poeng i dag, 1 senere': t([spot('A', [1, 0, 1, 0])], true, [H.ordSpot(W[1], 'A', dag(0)), best]),
                        'to dager, ingen surf': t([spot('A', [0]), spot('B', [0])], true, [H.ord(W[0], dag(0)), H.ingen(dag(1))], dager.slice(0, 2)),
                        'én dag': t([spot('A', [0])], true, [H.ord(W[0], dag(0))], dager.slice(0, 1)),
                    };
                }"""

                # spotsiden er klar: dommen (B 4.0 - mobil fra steg 4, PC fra steg 6)
                SPOT_KLAR = "#viewSpot:not([hidden]) .dom"
                INN = "#viewSpot :is(.sp-inn, .spw-inn)"   # innholdet under navneplata (mobil / PC)

                def vindu_over(sid, dag, naar):
                    # spotsiden følger samme regel som forsiden og favorittradene (kontrolløren 19.11.2026): dommen og kolonnen i
                    # «Neste 7 dager» viser «Best hh–hh» bare mens vinduet er åpent. `naar` er etter vinduet til `sid` den dagen;
                    # kl. T0 er dagen i morgen og vinduet åpent. Siden åpnes på dagens beste time, og Hjem står igjen etterpå.
                    bi = next(i for i, x in enumerate(details[sid]["hours"]) if x["t"] == next(d for d in OV[sid]["dager"] if d["d"] == dag)["h"]["t"])
                    def les():
                        go("#hjem", "#viewHjem:not([hidden])"); go(f"#spot={sid}&t={bi}", SPOT_KLAR)
                        return page.evaluate("""(dag) => { const q = (s) => { const e = document.querySelector('#viewSpot ' + s); return e ? e.textContent.trim() : null; };
                            return {tall: q('.dom .t-tall'), vindu: q('.dom .t-vindu'), kol: q(`.dagknapp.stor[data-day="${dag}"] .dk-best`), koltall: q(`.dagknapp.stor[data-day="${dag}"] .dk-tall`),
                                strek: document.querySelectorAll('#viewSpot #spStripe .bst.pa').length, aria: [...document.querySelectorAll('#viewSpot #spStripe [aria-label], #viewSpot #spStripe [aria-valuetext]')].some(e => /beste vindu/.test((e.getAttribute('aria-label') || '') + (e.getAttribute('aria-valuetext') || '')))}; }""", dag)
                    over = les()
                    page.clock.set_fixed_time(T0); apen = les(); page.clock.set_fixed_time(naar)
                    assert (over["tall"] or "").isdigit() and int(over["tall"]) >= 1 and over["vindu"] is None, f"dommen på spotsiden skal ikke vise «Best» etter at vinduet er over ({sid}, {naar}): {over}"
                    assert apen["tall"] == over["tall"] and re.fullmatch(r"\d\d–\d\d", apen["vindu"] or ""), f"dommen på spotsiden skal vise vinduet mens det er åpent ({sid}): {apen}"
                    # streken over det beste vinduet i timestripa følger samme regel (feiljegeren 19.11.2026)
                    assert over["strek"] == 0 and not over["aria"], f"streken over det beste vinduet skal ikke stå etter at vinduet er over ({sid}, {naar}): {over}"
                    assert apen["strek"] >= 1 and apen["aria"], f"streken over det beste vinduet skal stå mens vinduet er åpent ({sid}): {apen}"
                    if not mobile:
                        assert over["koltall"] == over["tall"] and over["kol"] == "–", f"kolonnen i «Neste 7 dager» skal ikke vise «Best» etter at vinduet er over ({sid}): {over}"
                        assert re.fullmatch(r"Best \d\d–\d\d", apen["kol"] or ""), f"kolonnen i «Neste 7 dager» skal vise vinduet mens det er åpent ({sid}): {apen}"
                        # siden velger oppsett når den tegnes: krysser bredden 1024 px (et nettbrett som snus), tegnes den på nytt (feiljegeren 19.11.2026)
                        assert page.query_selector("#viewSpot .spw-hode") and not page.query_selector("#viewSpot .sp-hode"), "PC-oppsettet mangler på spotsiden"
                        # brukeren blir stående der de var: rullingen og en åpen «Hvorfor» overlever byttet (feiljegeren 19.11.2026)
                        page.evaluate("() => { document.querySelector('#viewSpot #hvorfor').open = true; window.scrollTo(0, 320); }")
                        page.set_viewport_size({"width": 800, "height": vp[1]}); page.wait_for_selector("#viewSpot .sp-hode")
                        st = page.evaluate("() => ({y: window.scrollY, apen: !!(document.querySelector('#viewSpot #hvorfor') || {}).open})")
                        assert st["y"] >= 300 and st["apen"], f"spotsiden hoppet til toppen eller lukket «Hvorfor» da bredden krysset 1024 px: {st}"
                        assert not page.query_selector("#viewSpot .spw-hode"), "PC-oppsettet står igjen under 1024 px"
                        # på den smaleste nettsiden (1024 px) får forklaringa egen linje, og ingenting renner ut av timekolonnen og over skiva
                        page.set_viewport_size({"width": 1024, "height": vp[1]}); page.wait_for_selector("#viewSpot .spw-hode")
                        ute = page.evaluate("""() => { const k = document.querySelector('#viewSpot .spw-time').getBoundingClientRect();
                            return [...document.querySelectorAll('#viewSpot .spw-time .maal > *')].filter(e => e.textContent.trim() && (e.scrollWidth > e.clientWidth + 1 || e.getBoundingClientRect().right > k.right + 1))
                              .map(e => e.className + ' «' + e.textContent.trim() + '»'); }""")
                        assert page.query_selector("#viewSpot .spw-time .maal") and not ute, f"målene renner ut av timekolonnen ved 1024 px ({sid}): {ute}"
                        # det lengste ordet som kan stå der tallet står («Surfing forbudt», 135 px mot 114 px kolonne målt 19.11.2026), brytes i to linjer.
                        # Ordet settes inn i siden som står framme: spoten i testen har ingen forbudsperiode.
                        ord_ute = page.evaluate("""() => { const k = document.querySelector('#viewSpot .spw-time').getBoundingClientRect(), mv = document.querySelector('#viewSpot .spw-time .maal .mv'), for_ = mv.innerHTML;
                            mv.innerHTML = '<span class="ordv">Surfing forbudt</span>'; const rg = document.createRange(); rg.selectNodeContents(mv); const ut = Math.round(rg.getBoundingClientRect().right - k.right);
                            mv.innerHTML = for_; return ut; }""")
                        assert ord_ute <= 1, f"«Surfing forbudt» renner {ord_ute} px ut av timekolonnen ved 1024 px"
                        page.set_viewport_size({"width": vp[0], "height": vp[1]}); page.wait_for_selector("#viewSpot .spw-hode")
                        assert not page.query_selector("#viewSpot .sp-hode") and page.evaluate("window.__S.idx") == bi, "mobiloppsettet står igjen over 1024 px, eller timen ble byttet"
                        st = page.evaluate("() => ({y: window.scrollY, apen: !!(document.querySelector('#viewSpot #hvorfor') || {}).open})")
                        assert st["y"] >= 300 and st["apen"], f"spotsiden hoppet til toppen eller lukket «Hvorfor» på vei tilbake over 1024 px: {st}"
                    # siden tegnes også på nytt av seg selv: ved ny time (tickNow) og etter Front.refresh() (økt logget, synk ferdig).
                    # Brukeren blir stående der de var (feiljegeren 19.11.2026). Merket på dommen viser at siden faktisk ble tegnet på nytt.
                    for hva, utlos in (("ny time", "() => { window.__S.now = 'gammel time'; document.dispatchEvent(new Event('visibilitychange')); }"), ("Front.refresh()", "() => Front.refresh()")):
                        page.evaluate("() => { document.querySelector('#viewSpot #hvorfor').open = true; document.querySelector('#viewSpot .dom').dataset.gammel = '1'; window.scrollTo(0, 320); }")
                        # fokus (et felt med id ved ny time, en dagknapp ved refresh) og dagrekka står også (feiljegeren 19.11.2026)
                        LES_FOKUS = "() => { const dv = document.querySelector('#viewSpot .dagvelger'), a = document.activeElement; return {x: dv ? dv.scrollLeft : null, fokus: a.id || (a.dataset || {}).day || a.tagName}; }"
                        page.evaluate("""(dagknapp) => { const dv = document.querySelector('#viewSpot .dagvelger'); if(dv) dv.scrollLeft = dv.scrollWidth;
                            const e = (dagknapp && document.querySelector('#viewSpot .dagknapp[aria-pressed="false"]')) || document.querySelector('#viewSpot #tstripeVelg') || document.querySelector('#viewSpot #loggHer');
                            e.focus({preventScroll: true}); }""", hva != "ny time")
                        fo = page.evaluate(LES_FOKUS)
                        assert fo["fokus"] not in ("BODY", "") and (fo["x"] or 0) > (0 if mobile else -1), f"fikk ikke satt fokus eller rullet dagrekka før {hva} ({label}): {fo}"
                        page.evaluate(utlos); page.wait_for_selector(SPOT_KLAR)
                        fo2 = page.evaluate(LES_FOKUS)
                        assert fo2 == fo, f"spotsiden mistet fokus eller plassen i dagrekka ved {hva} ({label}): før {fo}, etter {fo2}"
                        st = page.evaluate("() => ({y: window.scrollY, apen: !!(document.querySelector('#viewSpot #hvorfor') || {}).open, gammel: !!document.querySelector('#viewSpot .dom[data-gammel]')})")
                        assert not st["gammel"], f"spotsiden ble ikke tegnet på nytt ved {hva}: testen prøver ingenting"
                        assert st["y"] >= 300 and st["apen"], f"spotsiden hoppet til toppen eller lukket «Hvorfor» ved {hva} ({label}): {st}"
                    # Ny time når første spot mangler «nå» (hentingen feilet i regionen): nøkkelen er klokketimen, så siden tegnes
                    # likevel på nytt. Med nå-timen til første spot som nøkkel sto null mot null resten av økta (fysikk-kontrolløren 19.11.2026).
                    ms0 = page.evaluate("() => { window.__naa0 = DATA.spots[0].naa; DATA.spots[0].naa = []; document.dispatchEvent(new Event('visibilitychange')); return Date.now(); }")
                    page.wait_for_selector(SPOT_KLAR); page.evaluate("() => { document.querySelector('#viewSpot .dom').dataset.gammel = '1'; }")
                    page.clock.set_fixed_time(dt.datetime.fromtimestamp(ms0 / 1000 + 3600, dt.timezone.utc)); page.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))"); page.wait_for_selector(SPOT_KLAR)
                    assert not page.query_selector("#viewSpot .dom[data-gammel]"), f"spotsiden ble ikke tegnet på nytt ved ny time når første spot mangler «nå» ({label})"
                    page.clock.set_fixed_time(dt.datetime.fromtimestamp(ms0 / 1000, dt.timezone.utc)); page.evaluate("() => { DATA.spots[0].naa = window.__naa0; document.dispatchEvent(new Event('visibilitychange')); }"); page.wait_for_selector(SPOT_KLAR)
                    # Innstillinger tegnes ikke på nytt ved ny time: tekst som ikke er lagret, og fokus, blir stående (feiljegeren 19.11.2026)
                    go("#innstillinger", "#viewSide:not([hidden]) #syncRepo")
                    inn = page.evaluate("""() => { const i = document.querySelector('#syncRepo'); i.value = 'theo/halv'; i.focus(); window.__S.now = 'gammel time'; document.dispatchEvent(new Event('visibilitychange'));
                        return {repo: document.querySelector('#syncRepo').value, fokus: document.activeElement.id, now: window.__S.now}; }""")
                    assert inn["repo"] == "theo/halv" and inn["fokus"] == "syncRepo" and inn["now"] != "gammel time", f"Innstillinger mistet teksten eller fokus ved ny time ({label}): {inn}"
                    # Ved innlogging (authchange) og når synken er ferdig (Front.refresh()) tegnes Innstillinger på nytt: teksten som ikke
                    # er lagret, fokus og markøren står (feiljegeren 19.11.2026)
                    for hva in ("authchange", "Front.refresh()"):
                        inn = page.evaluate("""(hva) => { const i = document.querySelector('#syncRepo'); i.value = 'theo/halv'; i.focus(); i.setSelectionRange(4, 4); i.dataset.gammel = '1';
                            if(hva === 'authchange') window.dispatchEvent(new Event('authchange')); else Front.refresh();
                            const j = document.querySelector('#syncRepo'); return {tegnet: !j.dataset.gammel, repo: j.value, fokus: document.activeElement.id, merket: j.selectionStart}; }""", hva)
                        assert inn["tegnet"], f"Innstillinger ble ikke tegnet på nytt ved {hva}: testen prøver ingenting"
                        assert inn["repo"] == "theo/halv" and inn["fokus"] == "syncRepo" and inn["merket"] == 4, f"Innstillinger mistet teksten, fokus eller markøren ved {hva} ({label}): {inn}"
                    # er verdien lagret i mellomtiden («Lagre og synk» trimmer og lagrer, og synken tegner siden på nytt), vinner den lagrede
                    lagret = page.evaluate("""() => { const k = 'nordsurf.sync.v1', for0 = localStorage.getItem(k); document.querySelector('#syncRepo').value = ' theo/ny ';
                        localStorage.setItem(k, JSON.stringify({repo: 'theo/ny'})); Front.refresh(); const v = document.querySelector('#syncRepo').value;
                        if(for0 == null) localStorage.removeItem(k); else localStorage.setItem(k, for0);
                        Front.refresh(); return {v, etter: document.querySelector('#syncRepo').value}; }""")
                    assert lagret["v"] == "theo/ny" and lagret["etter"] != " theo/ny ", f"den lagrede verdien skal vinne over teksten i feltet ({label}): {lagret}"
                    go("#hjem", "#viewHjem:not([hidden]) :is(#forside, .hjem-linje)")
                    # Hjem: bare høyden endrer seg når adresselinja på mobil glir inn og ut, og da skal ingenting tegnes på nytt.
                    # Ny bredde tegner Hjem på nytt (kartet følger bredden), men brukeren blir stående der de var.
                    HM = "#viewHjem :is(#forside, .hjem-linje)"
                    hjem_na = lambda: page.evaluate("(hm) => ({y: window.scrollY, gammel: !!document.querySelector(hm + '[data-gammel]')})", HM)
                    page.evaluate("(hm) => { document.querySelector(hm).dataset.gammel = '1'; window.scrollTo(0, 150); }", HM)
                    assert hjem_na()["y"] >= 140, f"Hjem er for kort til å prøve rullingen ({label})"
                    page.set_viewport_size({"width": vp[0], "height": vp[1] - 80}); page.wait_for_timeout(200)
                    st = hjem_na(); assert st["gammel"] and st["y"] >= 140, f"Hjem ble tegnet på nytt eller hoppet til toppen da bare høyden endret seg ({label}): {st}"
                    page.set_viewport_size({"width": vp[0] + 10, "height": vp[1] - 80}); page.wait_for_timeout(200)
                    st = hjem_na(); assert not st["gammel"] and st["y"] >= 140, f"Hjem skal tegnes på nytt ved ny bredde og bli stående ({label}): {st}"
                    page.set_viewport_size({"width": vp[0], "height": vp[1]}); page.wait_for_timeout(200)
                    page.evaluate("window.scrollTo(0, 0)")

                SYN_STRIPE_JS = r"""() => {
                  // timestripa med kjente timer (21.10, sommertid): 3, 3 med ett tapt på vind, 4 med ett tapt på tidevann,
                  // 5, en mørk time, en uten data, en i forbudsperiode og en ekte 0
                  const dag = '2026-10-21';
                  const mk = (hh, o) => Object.assign({t: `${dag}T${String(hh - 2).padStart(2, '0')}:00Z`, light: 'dag', stars: 0, faded: 0, surf_height: 1, wind_speed: 5, wind_dir: 180, wind_type: 'offshore'}, o);
                  const s = {id: 'syn', hours: [mk(8, {stars: 3}), mk(9, {stars: 3, faded: 1, faded_wind: 1}), mk(10, {stars: 4, faded: 1, faded_tide: 1}), mk(11, {stars: 5}),
                    mk(12, {light: 'mørkt', stars: 4}), mk(13, {surf_height: null}), mk(14, {_forbud: true}), mk(15, {low_reason: 'flat', surf_height: 0}),
                    mk(16, {stars: 1, surf_height: null}), mk(17, {low_reason: 'stormsjo', surf_height: null, bw_height: null}), mk(18, {surf_height: 0.04}), mk(19, {low_reason: 'treffer_ikke', surf_height: 1.2})], max_height: 2, ideal_height: [1, 1.5]};
                  const Hh = {usable: h => h.light === 'dag' || h.light === 'skumring', mork: h => h.light === 'mørkt', known: h => !!h && !(!h.stars && !h.low_reason && h.surf_height == null), stars: h => h.stars || 0, heightText: Front.helpers.heightText, hoydeVist: Front.helpers.hoydeVist, hoydeMangler: Front.helpers.hoydeMangler, erSjo: Front.helpers.erSjo};
                  const d = {key: dag, idxs: s.hours.map((_, i) => i), step: 1}, best = new Set([2, 3]);
                  const boks = document.createElement('div');
                  document.querySelector('#viewSpot :is(.sp-inn, .spw-inn)').appendChild(boks);
                  const ut = {kol: {}, aria: {}, valgt: {}};
                  const tapt = (e) => { const i = e.querySelector('i.tapt'); return i ? {stil: getComputedStyle(i).borderTopStyle, farge: getComputedStyle(i).borderTopColor} : null; };
                  // timen kl. 08 er valgt: tapte poeng vises bare der (designrevisjon fase 3 punkt 4)
                  boks.innerHTML = Timestripe.html(s, d, 0, best, Hh);
                  for(const tk of boks.querySelectorAll('.tk')){
                    const e = tk.querySelector('.segs'), pa = e.querySelector('i.pa'), bst = tk.querySelector('.bst'), sb = tk.querySelector('.srf .sbx'), st = sb && sb.querySelector('i');
                    ut.kol[tk.dataset.hh] = {cls: e.className.replace(/^segs ?/, ''), n: e.children.length, pa: e.querySelectorAll('i.pa').length, tapt: e.querySelectorAll('i.tapt').length, tv: e.querySelectorAll('i.tapt.tv').length, vist: tapt(e),
                      farge: pa ? getComputedStyle(pa).backgroundColor : null, mork: tk.classList.contains('mork'), best: bst.classList.contains('pa') ? (bst.classList.contains('k') ? 'korall' : 'blekk') : null,
                      stolpe: st ? Math.round(st.getBoundingClientRect().height) : null, stolpeFarge: st ? getComputedStyle(st).backgroundColor : null, skravur: !!sb && sb.classList.contains('miss'), boks: sb ? Math.round(sb.getBoundingClientRect().height) : null};
                  }
                  const il = boks.querySelector('.ideal');
                  ut.ideal = il ? {y: getComputedStyle(il).getPropertyValue('--y').trim(), tekst: il.textContent.trim()} : null;
                  // velger man 09 (−1 vind) og 10 (−1 tidevann), står det tapte poenget stiplet i blekk der
                  for(const [i, hh] of [[1, '09'], [2, '10']]){
                    boks.innerHTML = Timestripe.html(s, d, i, best, Hh);
                    ut.valgt[hh] = Object.assign(tapt(boks.querySelector(`.tk[data-hh='${hh}'] .segs`)) || {}, {andre: [...boks.querySelectorAll('.tk:not(.valgt) .segs i.tapt')].map(e => getComputedStyle(e).borderTopStyle).filter(x => x !== 'none').length});
                  }
                  boks.remove();
                  const tmp = document.createElement('div');
                  for(let i = 0; i < s.hours.length; i++){ tmp.innerHTML = Timestripe.html(s, d, i, best, Hh); ut.aria[String(i + 8).padStart(2, '0')] = tmp.querySelector('input').getAttribute('aria-valuetext'); }
                  return ut;
                }"""

                def spot_mobil(scheme):
                    # ---- 8–11: spotsiden i design B 4.0 - mobil (SPEC §6B, steg 4) og PC (SPEC §6C, steg 6) med samme
                    # innhold: dommen, timen (#spOver), skiva (#spUnder), timestripa og dagvelgeren. Forskjellene står ved sjekken.
                    def tekst(sel):
                        return page.evaluate("(sel) => { const e = document.querySelector(sel); return e ? e.textContent.replace(/\\s+/g, ' ').trim() : null; }", sel)

                    def valgt():
                        # timen glidebryteren (VoiceOver og piltaster) står på, og kolonnen den hører til
                        return page.evaluate("(() => { const inp = document.querySelector('#tstripeVelg'), k = document.querySelector(`#tstripe .tk[data-k='${inp.value}']`); return {k: +inp.value, i: +k.dataset.i, hh: k.dataset.hh, aria: inp.getAttribute('aria-valuetext'), dag: document.querySelector('#tstripe').dataset.day}; })()")

                    def dommen():
                        return page.evaluate("""(() => { const q = (s) => { const e = document.querySelector('#viewSpot ' + s); return e ? e.textContent.trim() : null; };
                            return {cls: document.querySelector('#viewSpot .dom').className, tall: q('.dom .t-tall'), ord: q('.dom-ord b'), dag: q('.dom-ord .etikett'), vindu: q('.dom .t-vindu')}; })()""")

                    def maalene():
                        return page.evaluate("Object.fromEntries([...document.querySelectorAll('#spOver .maal')].map(m => [m.querySelector('.etikett').textContent.trim(), m.textContent.replace(/\\s+/g, ' ').trim()]))")

                    def kolonner():
                        return page.evaluate("[...document.querySelectorAll('#tstripe .tk')].map(k => ({k: +k.dataset.k, i: +k.dataset.i, hh: k.dataset.hh}))")

                    def aapne(par):
                        go(f"#spot={par[0]}&t={par[1]}", "#viewSpot:not([hidden]) #tilbakeNa")
                        v = valgt(); assert v["i"] == par[1], f"siden skal stå på timen i adressen: {par}, {v}"
                        t = tekst(INN); m_ = re.search(r"(?<![a-zæøå])null|undefined|NaN", t)   # «sjøkartnull» (tidevannsraden på PC) er et ord, ikke en tom verdi
                        assert not m_, f"{par}: …{t[max(0, m_.start() - 200):m_.end() + 60]}"
                        return details[par[0]]["hours"][par[1]]

                    def tallene(t):
                        return [float(x.replace(",", ".")) for x in re.findall(r"\d+,\d", t or "")]

                    # ---- 8. Unstad nå ----
                    go("#utforsk", "#viewUtforsk:not([hidden])")
                    go("#spot=unstad", SPOT_KLAR)
                    page.wait_for_selector("#tstripe .tsvg")
                    assert page.evaluate("window.__S.idx") is None, "spotsiden uten &t= skal stå på «nå» (S.idx null)"
                    hs = details["unstad"]["hours"]; imorgen = (TODAY + dt.timedelta(days=1)).isoformat()
                    # åpnet på «nå» kl. 22 (lyset er over): siden viser i morgen og dagens beste lyse time, «I dag» er ute av rekka
                    dager = page.evaluate("[...document.querySelectorAll('.dagknapp')].map(b => b.dataset.day)")
                    assert dager == sorted({oslo_day(x["t"]) for x in hs} - {TODAY.isoformat()}), f"dagvelgeren skal ha alle dagene i varselet etter i dag: {dager}"
                    assert page.get_attribute(".dagknapp[aria-pressed='true']", "data-day") == imorgen
                    v = valgt(); h = hs[v["i"]]
                    assert v["dag"] == imorgen and oslo_day(h["t"]) == imorgen and light_of(h) in ("dag", "skumring"), (v, h["t"], light_of(h))
                    assert tekst("#spOver .sek-spot h2") == f"Kl. {v['hh']}" and tekst("#spUnder h2") == f"Retning kl. {v['hh']}"
                    assert not page.query_selector("#tilbakeNa"), "«Tilbake til nå» skal ikke vises når siden står på «nå»"
                    # dommen: samme tall som Hjem og ukeoversikten (dagssammendraget fra publish.py)
                    cls, st = day_cls(OV["unstad"], imorgen); dom = dommen()
                    assert cls.startswith("r-") and dom["tall"] == str(min(5, st)) and cls in dom["cls"].split(), (cls, st, dom)
                    # ordet etter tallet er karakteren, årsaken (Blåst ut, Treffer ikke, Stormsjø) står på egen linje (fase 3 punkt 5)
                    kar = page.evaluate("(h) => karakter(h)", next(x for x in OV["unstad"]["dager"] if x["d"] == imorgen)["h"])
                    assert dom["ord"] == kar["ord"] and tekst("#viewSpot .dom .dom-grunn") == kar["aarsak"], (dom, kar, tekst("#viewSpot .dom .dom-grunn"))
                    assert dom["dag"].lower() == "i morgen" and (dom["vindu"] is not None) == (st >= 1), dom
                    # timen: surfehøyden ved spoten er det store tallet (designrevisjon fase 3 punkt 1, godkjent av Theodor 21.11), med
                    # kroppsmålet under; svellet ute er en rad på linje med vind og tidevann - tallene er varselets
                    # S45 5: en mørk time har «–» uten tall. S45 2: er tallet totalhøyden (Stormsjø, Blåst ut uten surfehøyde), heter det «Sjø» og har ikke kroppsmål
                    ht = page.evaluate("(h) => Front.helpers.mork(h) ? null : Front.helpers.heightText(h)", h)
                    sjo_ = bool(ht) and page.evaluate("(h) => Front.helpers.erSjo(h)", h)
                    assert tekst("#spOver .t-svell") == (f"{ht}m" if ht else "–"), (tekst("#spOver .t-svell"), ht)
                    assert tekst("#spOver .svell > .etikett") == ("Sjø" if sjo_ else "Surf"), tekst("#spOver .svell > .etikett")
                    assert ht is None or tekst("#spOver .svell > .svell-sub") == (None if sjo_ else page.evaluate("(h) => Spot.kroppshoyde(h)", h)), tekst("#spOver .svell > .svell-sub")
                    # samme ord i det skjermleseren leser for hver time i timestripa
                    sv_aria = page.evaluate("[...document.querySelectorAll('#tstripe [aria-label]')].map(e => e.getAttribute('aria-label')).filter(a => /svell/i.test(a))")
                    assert page.evaluate("STR.spot.timeSvell('1,2')") == "Svell ute 1,2 m" and all("Svell ute " in a_ for a_ in sv_aria), sv_aria[:3]
                    maal = maalene()
                    assert list(maal)[:2] == ["Svell ute", "Vind"], list(maal)   # svellet ute, ikke bølgene på stranda (Theodor S20 a, 20.11.2026)
                    sub = maal["Svell ute"]
                    assert nf1(h["swell_offshore"]) in sub and f"{r0(h['period'])} s" in sub and f"{r0(h['dir_offshore'])}°" in sub, (sub, h["swell_offshore"], h["period"], h["dir_offshore"])
                    if h["surf_height"] is not None and h["surf_height"] > 0 and not h.get("low_reason"):
                        surf = tekst("#spOver .svell.surf")
                        assert nf1(h["surf_height"]) in surf and kroppshoyde(h["surf_height"], h.get("surf_height_sets")) in surf, (surf, h["surf_height"])
                    assert f"{r0(h['wind_speed'])}m/s" in maal["Vind"].replace(" ", "").replace("\xa0", ""), maal
                    assert page.evaluate("(h) => windLabel(h)", h) in maal["Vind"] and not re.search(r"offshore|onshore", " ".join(maal.values()), re.I), maal
                    assert re.search(r"\d,\d ?m", maal["Tidevann"]), maal
                    if light_of(h) != "mørkt":
                        assert tekst("#spOver .tdom .rute") == str(min(5, h.get("stars") or 0)) and tekst("#spOver .tdom .to") == page.evaluate("(h) => karakter(h).ord", h)
                    # faktalinja: under timen på mobil; på PC metalinja under navnet (kjøretid og dato først)
                    fakta = tekst("#spOver .fakta-linje" if mobile else "#spMeta")
                    assert (fakta.startswith("Lys ") if mobile else " Lys " in fakta) and "Oppdatert" in fakta, fakta
                    # retningsskiva: vinduet sies likt som rating.in_sector, og sikkerheten står i kildelinja
                    assert vindu_tekst(h, SP["unstad"]) in tekst("#spUnder .skive-forkl"), (tekst("#spUnder .skive-forkl"), h["dir_offshore"], h.get("directness"))
                    sa = page.get_attribute("#spUnder .skive", "aria-label")
                    inne = any(rating.in_sector(h["dir_offshore"], sec) for sec in rating.window_sectors(SP["unstad"]))
                    assert sa.startswith(f"Unstad kl. {v['hh']}: svell fra {r0(h['dir_offshore'])} grader, {'innenfor' if inne else 'utenfor'} svellvinduet"), sa
                    if mobile:
                        assert tekst("#spUnder .kilder.sikk") == sikkerhet(h["confidence"], h["zone"]) and tekst("#spUnder .kilder.sikk + .kilder").startswith("Varsel fra "), tekst("#spUnder .kilder")
                    else:   # PC: sikkerheten står i «Om spotten» (Data)
                        om = page.evaluate("Object.fromEntries([...document.querySelectorAll('#spOm .spw-om > div')].map(d => [d.querySelector('dt').textContent.trim(), d.querySelector('dd').textContent.trim()]))")
                        assert om.get("Data", "").startswith(sikkerhet(h["confidence"], h["zone"])), om
                        assert om.get("Vindu") and om.get("Fralands") and om.get("Vender mot"), om
                    assert page.get_attribute("#tstripe .tsvg", "aria-label").startswith("Tidevann: "), "tidevannskurven skal ha etikett"
                    # kornfotoet: Trykk i lyst tema og Lodd i mørkt, med kreditering under navnet og kortformen under skiva
                    page.wait_for_function("[...document.querySelectorAll('#viewSpot .sp-foto')].some(b => getComputedStyle(b).display !== 'none' && b.naturalWidth > 0)")
                    foto = page.evaluate("[...document.querySelectorAll('#viewSpot .sp-foto')].filter(b => getComputedStyle(b).display !== 'none').map(b => [b.getAttribute('src'), b.alt])")
                    assert foto == [[f"img/spots/unstad-{'lodd' if scheme == 'mork' else 'trykk'}.jpg", "Satellittbilde av Unstad ovenfra, nord opp"]], foto
                    for sel in (INN + " > .kredit", "#viewSpot .kredit.liten"):
                        k = tekst(sel); assert "Sentinel-2" in k and "CC BY 4.0" in k and "Kartverket" in k, (sel, k)
                    # tilbakeknappen følger stakken: hit kom vi fra Utforsk (PC har toppmenyen i stedet, og regionen lenker til Utforsk)
                    if mobile:
                        assert page.get_attribute("#spotBack", "aria-label") == "Tilbake til Utforsk" and tekst("#spotBack") == "Utforsk", (page.get_attribute("#spotBack", "aria-label"), tekst("#spotBack"))
                    else:
                        assert not page.is_visible("#spotBack") and tekst("#spotRegion").startswith("Lofoten"), tekst("#spotRegion")
                        # SPEC §6C: 7 store dagkolonner, tabellen time for time med etikettkolonnen, minikartet med kystlinje
                        assert page.locator(".dagvelger.sju .dagknapp.stor").count() == 7, page.locator(".dagvelger.sju .dagknapp").count()
                        etik = page.evaluate("[...document.querySelectorAll('#tstripe .tetik > *')].map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
                        assert etik[:5] == ["Kl.", "Vurdering", "Surf m", "Svell fra", "Vind m/s"] and (len(etik) == 6) == bool(page.query_selector("#tstripe .tsvg")), etik
                        page.wait_for_selector("#miniKort .minikart path.land")
                    shot("unstad-na", scheme); audit("unstad-na")
                    # S38 2 a: etikettene i KL.-blokka, skiva og kildelinja åpner forklaringsarket. Trykkflaten er minst 44 px høy,
                    # fokus er synlig, og Escape lukker arket og gir fokus tilbake til etiketten
                    fk = page.evaluate("""() => [...document.querySelectorAll('#viewSpot .forklar')].filter(e => e.getClientRects().length).map(e => { const b = e.getBoundingClientRect();
                        return {key: e.dataset.explain, tag: e.tagName, h: Math.round(b.height), w: Math.round(b.width), finnes: !!EXPLAIN[e.dataset.explain]}; })""")
                    nokler = {f_["key"] for f_ in fk}
                    surf_ark = "hs" if tekst("#spOver .svell > .etikett") == "Sjø" else "surf_height"   # «SJØ» (totalhøyden, S45 2) åpner arket om signifikant høyde
                    assert {surf_ark, "swell", "wind", "tide", "direction", "confidence"} <= nokler and (not mobile or "hs" in nokler), f"etikettene som skal kunne trykkes ({scheme}): {sorted(nokler)}"
                    assert all(f_["tag"] == "BUTTON" and f_["finnes"] and f_["h"] >= 44 and f_["w"] >= 44 for f_ in fk), f"trykkflatene skal være knapper på minst 44 x 44 px: {[f_ for f_ in fk if f_['h'] < 44 or f_['w'] < 44]}"
                    for key_, tittel_ in (("swell", "Svell ute"), ("confidence", "Sikkerhet"), ("exposure", "Eksponering"), ("hs", "Signifikant høyde")):
                        if key_ not in nokler:
                            continue
                        page.keyboard.press("Tab")   # tastatur sist brukt: fokus satt fra skript regnes som synlig fokus
                        fokus_ = page.evaluate("""(k) => { const e = [...document.querySelectorAll(`#viewSpot .forklar[data-explain="${k}"]`)].find(x => x.getClientRects().length); e.scrollIntoView({block: 'center'}); e.focus();
                            const c = getComputedStyle(e); return [document.activeElement === e, c.outlineStyle, c.outlineWidth]; }""", key_)
                        assert fokus_ == [True, "solid", "2px"], f"synlig fokus på etiketten {key_}: {fokus_}"
                        page.keyboard.press("Enter"); page.wait_for_selector("#exSheet.open")
                        assert page.text_content("#exTitle").strip() == tittel_ and page.get_attribute("#exSheet", "aria-hidden") == "false", (key_, page.text_content("#exTitle"))
                        assert not re.search(r"(?<![a-zæøå])null|undefined|NaN", page.text_content("#exBody")), page.text_content("#exBody")[:200]
                        page.keyboard.press("Escape"); page.wait_for_selector("#exSheet:not(.open)", state="attached")
                        assert page.evaluate("(k) => document.activeElement && document.activeElement.dataset.explain === k", key_), f"fokus skal tilbake til etiketten {key_} når arket lukkes"
                    # med musa eller fingeren
                    page.click("#spOver .forklar[data-explain='wind']"); page.wait_for_selector("#exSheet.open")
                    assert page.text_content("#exTitle").strip() == "Vind"
                    # arket er modalt: Tab og Shift+Tab blir i arket (feiljegeren 25.11.2026, funn 15)
                    for tast_ in ("Tab", "Tab", "Shift+Tab", "Shift+Tab"):
                        page.keyboard.press(tast_)
                        assert page.evaluate("!!document.activeElement.closest('#exSheet')"), f"{tast_} gikk ut av arket: {page.evaluate('document.activeElement.outerHTML.slice(0, 80)')}"
                    # tapte poeng er stiplet bare for valgt time, og det sier arkene også (funn 9)
                    assert page.evaluate("[EXPLAIN.wind.how().join(' '), EXPLAIN.stars.what].every(t => /stiplede ruter i timestripa, bare for valgt time/i.test(t))"), "arkene om vind og poeng skal si at de stiplede rutene bare gjelder valgt time"
                    # trykkflatene ligger ikke oppå hverandre i KL.-blokka: minst 44 px kan treffes, også på lave skjermer (funn 16)
                    page.click("#exClose"); page.wait_for_selector("#exSheet:not(.open)", state="attached")
                    for bw_, bh_ in ((375, 548), (375, 667), (390, 663), vp) if mobile else ((1024, 800), (1280, 800), vp):
                        page.set_viewport_size({"width": bw_, "height": bh_}); page.wait_for_timeout(200)
                        treff_ = page.evaluate("""[...document.querySelectorAll('#spOver .forklar')].map(e => { e.scrollIntoView({block: 'center'}); const b = e.getBoundingClientRect(); let n = 0;
                            for(let y = b.top + .5; y < b.bottom; y++){ const el = document.elementFromPoint(b.left + 12, y); if(el && el.closest('.forklar') === e) n++; } return [e.dataset.explain, n]; })""")
                        # 375 x 548: radene er lavere der, så KL.-blokka står over fanelinja etter dagbytte (ui.css)
                        assert len(treff_) == 4 and all(n_ >= (28 if bh_ <= 600 and k_ != "surf_height" else 44) for k_, n_ in treff_), f"trykkflatene i KL.-blokka ({bw_} x {bh_}): {treff_}"
                    page.set_viewport_size({"width": vp[0], "height": vp[1]}); page.wait_for_timeout(200)
                    # tallet ved streken for nedre grense dekker ingen stolpe og står på skjermen (funn 10)
                    il_ = page.evaluate("""() => { const a = document.querySelector('#tstripe .ideal span').getBoundingClientRect(); return {treffer: [...document.querySelectorAll('#tstripe .sbx i, #tstripe .segs, #tstripe .tk')].filter(e => { const c = e.getBoundingClientRect(); return Math.min(a.right, c.right) - Math.max(a.left, c.left) > 0.5 && Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top) > 0.5; }).length,
                        venstre: a.left, hoyre: a.right, w: innerWidth, hoyde: a.height}; }""")
                    assert il_["treffer"] == 0 and il_["venstre"] >= 16 and il_["hoyre"] <= il_["w"] - 15.5 and il_["hoyde"] > 0, f"tallet ved streken skal stå utenfor timene: {il_}"
                    page.click("#spOver .forklar[data-explain='wind']"); page.wait_for_selector("#exSheet.open")
                    page.click("#exClose"); page.wait_for_selector("#exSheet:not(.open)", state="attached")
                    page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(100)
                    # S42 (feiljegeren, fase 2 runde 5): ingen tankestrek (« - » eller « – ») i arkene eller i tekstene i strings.js
                    strek = page.evaluate("""(h) => { const spot = DATA.spots.find(x => x.id === 'unstad'), ut = [], re = / [-–] /;
                        for(const k of Object.keys(EXPLAIN)){ openExplain(k, h, spot); const t = document.getElementById('exSheet').textContent; if(re.test(t)) ut.push(k + ': ' + t.match(/.{0,30} [-–] .{0,30}/)[0]); }
                        closeExplain();
                        const gaa = (o, sti) => { for(const [k, v] of Object.entries(o)){ if(typeof v === 'string' && re.test(v)) ut.push(sti + k + ': ' + v); else if(v && typeof v === 'object') gaa(v, sti + k + '.'); } };
                        gaa(STR, 'STR.'); ut.push(...[STR.witness.sub('A', 'i dag', '10', 3)].filter(x => re.test(x))); return ut; }""", h)
                    assert not strek, f"tankestrek i tekster brukeren ser: {strek}"
                    assert not tankestreker(), f"tankestrek i tekst i docs (S42; feiljegeren 25.11.2026, funn 8): {tankestreker()}"
                    page.evaluate("window.scrollTo(0, 0)")
                    hoye = page.evaluate("""[...document.querySelectorAll('#viewSpot .t-tall, #viewSpot .t-svell, #viewSpot .mv, #viewSpot .t-vindu, #viewSpot .dagknapp .rute')]
                        .filter(el => el.getBoundingClientRect().height > 1.6 * parseFloat(getComputedStyle(el).fontSize)).map(el => el.className + ' «' + el.textContent.trim() + '»')""")
                    assert not hoye, f"tall brutt over flere linjer ({scheme}): {hoye}"
                    # korall fra 4, blekk til og med 3, tapte poeng stiplet, og ingen segmenter i mørke, forbudte eller tomme timer
                    syn = page.evaluate(SYN_STRIPE_JS); kol = syn["kol"]
                    assert sorted(kol) == [f"{x:02d}" for x in range(6, 20)], sorted(kol)   # 06 og 07 har vært: varselet starter kl. 08
                    assert kol["06"]["cls"] == kol["07"]["cls"] == "vaert" and kol["07"]["n"] == 0, kol["07"]
                    assert (kol["08"]["cls"], kol["08"]["pa"], kol["08"]["tapt"]) == ("r-3", 3, 0) and (kol["09"]["cls"], kol["09"]["pa"], kol["09"]["tapt"]) == ("r-3", 3, 1), (kol["08"], kol["09"])
                    assert (kol["10"]["cls"], kol["10"]["pa"], kol["10"]["tapt"]) == ("r-4", 4, 1) and (kol["11"]["cls"], kol["11"]["pa"], kol["11"]["tapt"]) == ("r-5", 5, 0), (kol["10"], kol["11"])
                    assert kol["08"]["farge"] == kol["09"]["farge"] != kol["10"]["farge"] == kol["11"]["farge"], f"blekk til og med 3 og korall fra 4: {[kol[x]['farge'] for x in ('08', '09', '10', '11')]}"
                    # designrevisjon fase 3 punkt 4: tapte poeng (vind og tidevann) er stiplet i blekk, ikke korall, og vises bare for valgt time
                    vg = syn["valgt"]
                    assert (kol["09"]["tv"], kol["10"]["tv"]) == (0, 1) and kol["09"]["vist"]["stil"] == kol["10"]["vist"]["stil"] == "none", f"tapte poeng skal bare vises for valgt time ({scheme}): {kol['09']} {kol['10']}"
                    assert vg["09"]["stil"] == vg["10"]["stil"] == "dashed" and vg["09"]["farge"] == vg["10"]["farge"] == kol["08"]["farge"] != kol["10"]["farge"] and vg["09"]["andre"] == vg["10"]["andre"] == 0, f"tapt skal være stiplet blekk på valgt time ({scheme}): {vg}"
                    # surfehøyden som stolpe: fast skala 0 til max_height (2 m = 48 px), linje ved ideal_height (1 m), ingen stolpe ved flatt
                    # eller forbud, skravur når data mangler (aldri en lav stolpe), og stolpen finnes også i en mørk time
                    assert [kol[x]["stolpe"] for x in ("08", "11", "12", "13", "14", "15")] == [24, 24, 24, None, None, None] and kol["08"]["boks"] == 48, [(x, kol[x]["stolpe"]) for x in kol]
                    assert kol["13"]["skravur"] and not kol["15"]["skravur"] and kol["12"]["stolpeFarge"] != kol["08"]["stolpeFarge"], (kol["12"], kol["13"], kol["15"])
                    assert syn["ideal"] == {"y": "24px", "tekst": "1,0 m"}, syn["ideal"]
                    # feiljegeren 25.11.2026, funn 3 og 7: høyden mangler i en time med vurdering (1 poeng, Stormsjø) = skravur. Flatt (0,04 m) og
                    # Treffer ikke mangler ingenting: tom grunnlinje, uten stolpe på 2 px og uten «0,0 m» i det skjermleseren leser
                    assert [(kol[x]["stolpe"], kol[x]["skravur"]) for x in ("16", "17", "18", "19")] == [(None, True), (None, True), (None, False), (None, False)], [(x, kol[x]["stolpe"], kol[x]["skravur"]) for x in ("16", "17", "18", "19")]
                    assert "surf" not in syn["aria"]["18"].lower() and "surf" in syn["aria"]["08"].lower(), (syn["aria"]["18"], syn["aria"]["08"])
                    # det den lokale tidevannsregelen tar (local_rules.stars_lost, Breivikeidet når tidevannet er størst) vises som tidevann
                    s33 = page.evaluate("""() => { const lok = {stars: 1, faded: 0, faded_wind: 0, faded_tide: 0, local_rules: {stars_lost: 1}}, begge = {stars: 2, faded: 2, faded_wind: 1, faded_tide: 1, local_rules: {stars_lost: 1}};
                        return {lok: [tideLost(lok), lostAll(lok), lostParts(lok).map(p => p.tekst)], begge: [tideLost(begge), lostAll(begge), lostParts(begge).map(p => p.tekst)],
                          ingen: [tideLost({stars: 2}), lostAll({stars: 2}), lostParts({stars: 2}).length, tideLost(null), lostAll(null)], gammel: lostParts({stars: 1, faded: 1}).map(p => p.tekst), aria: [starsAriaLost(1, lok), starsAriaLost(2, begge), starsAriaLost(1, {stars: 1, faded: 1}), starsAriaLost(2, {stars: 2}), starsAriaLost(3, null)]}; }""")
                    assert s33["lok"] == [1, 1, ["−1 tidevann"]] and s33["begge"] == [2, 3, ["−1 vind", "−2 tidevann"]] and s33["ingen"] == [0, 0, 0, 0, 0] and s33["gammel"] == ["−1"], s33
                    # M3 (feiljegeren 24.11.2026): tallet leses opp med samme oppdeling som timestripa. Eldre varsel uten delingen som før.
                    assert s33["aria"] == ["1 av 5, 1 tapt på tidevann", "2 av 5, 1 tapt på vind, 2 tapt på tidevann", "1 av 5, 1 tapt på vind eller tidevann", "2 av 5", "3 av 5"], s33
                    # vilkår 1 (fysikk-kontrolløren 24.11.2026): når tidevannet får poenget, er low_reason tom og ordet poengets ord, også i
                    # fralandsvind 10,2-12 m/s med surfehøyde fra 0,8 m på Breivikeidet (wind_calm_ms 8). Aldri «Blåst ut» der.
                    ord33 = page.evaluate("""() => [10.2, 11, 11.99].map(v => ratingWord({stars: 1, low_reason: null, wind_type: 'offshore', wind_speed: v, wind_calm_ms: 8, surf_height: 1.35, period: 8,
                        light: 'dag', faded: 0, faded_wind: 0, faded_tide: 0, zero_losses: {energy: 0, wind: 0, tide: 0, local: 1, cap: 0}, local_rules: {stars_lost: 1}})).concat([STR.starWords[1], LOW_REASON_WORD.blown_out])""")
                    assert ord33[:3] == [ord33[3]] * 3 and ord33[3] != ord33[4], ord33
                    assert kol["12"]["mork"] and kol["12"]["n"] == 0, f"en mørk time har ingen segmenter: {kol['12']}"
                    assert kol["13"]["cls"] == "miss" and kol["13"]["n"] == 0, f"en time uten data er skravert, aldri 0: {kol['13']}"
                    assert kol["14"]["cls"] == "forbud" and kol["14"]["n"] == 0, f"en time i forbudsperioden har ingen vurdering: {kol['14']}"
                    assert (kol["15"]["cls"], kol["15"]["n"], kol["15"]["pa"]) == ("r-0", 5, 0), kol["15"]
                    assert [kol[x]["best"] for x in ("09", "10", "11", "12")] == [None, "korall", "korall", None], [kol[x]["best"] for x in kol]
                    ar = syn["aria"]
                    assert ar["08"].startswith("kl. 08, 3 av 5.") and ar["09"].startswith("kl. 09, 3 av 5, 1 tapt på vind.") and ar["10"].startswith("kl. 10, 4 av 5, 1 tapt på tidevann, beste vindu."), ar
                    assert ar["12"].startswith("kl. 12, mørkt, ingen vurdering.") and ar["13"].startswith("kl. 13, mangler data.") and ar["14"].startswith("kl. 14, surfing forbudt.") and ar["15"].startswith("kl. 15, 0 av 5."), ar
                    if (details["unstad"].get("tide_regel") or {}).get("prefer"):
                        assert page.query_selector("#tstripe .tsvg rect.bnd"), "spoten har et foretrukket tidevannsnivå, men båndet mangler"
                    # timevalg som i dag: den skjulte glidebryteren (VoiceOver), piltaster og trykk i stripa
                    kols = kolonner(); n = len(kols)
                    m = next(c for c in kols if c["i"] >= 0 and c["k"] != v["k"] and c["k"] + 1 < n and c["k"] + 1 != v["k"])
                    page.evaluate("(k) => { const inp = document.querySelector('#tstripeVelg'); inp.value = String(k); inp.dispatchEvent(new Event('input', {bubbles: true})); }", m["k"])
                    page.wait_for_selector("#tilbakeNa")
                    hm = hs[m["i"]]; v2 = valgt()
                    assert page.evaluate("window.__S.idx") == m["i"] and v2["k"] == m["k"], (m, v2)
                    assert tekst("#spOver .sek-spot h2") == f"Kl. {m['hh']}" and tekst("#spUnder h2") == f"Retning kl. {m['hh']}"
                    assert v2["aria"].startswith(f"kl. {m['hh']}, " + ("mørkt, ingen vurdering" if light_of(hm) == "mørkt" else f"{hm.get('stars') or 0} av 5")), v2["aria"]
                    assert nf1(hm["swell_offshore"]) in maalene()["Svell ute"]
                    vk = page.evaluate("[...document.querySelectorAll('#tstripe .tk.valgt')].map(e => +e.dataset.k)")
                    assert vk == [m["k"]], f"klassen «valgt» (tapte poeng) skal flytte med timen: {vk}, {m}"
                    ring = page.evaluate("parseFloat(document.querySelector('#tstripe .ring').style.left)")
                    assert abs(ring - m["k"] / n * 100) < 0.01, (ring, m, n)
                    audit("unstad-valgt")
                    page.focus("#tstripeVelg"); page.keyboard.press("ArrowRight")
                    nxt = kols[m["k"] + 1]
                    page.wait_for_function(f"window.__S.idx === {nxt['i']}")
                    assert tekst("#spOver .sek-spot h2") == f"Kl. {nxt['hh']}"
                    t = next(c for c in kols if c["i"] >= 0 and c["k"] != nxt["k"] and c["k"] != v["k"])
                    x, y = page.eval_on_selector(f"#tstripe .tk[data-k='{t['k']}']", "e => { e.scrollIntoView({block: 'center'}); const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
                    if mobile:
                        page.touchscreen.tap(x, y)
                    else:   # PC: å holde musa over en time velger den (SPEC §6C punkt 5) - uten klikk
                        page.mouse.move(x, y)
                    page.wait_for_function(f"window.__S.idx === {t['i']}")
                    assert tekst("#spOver .sek-spot h2") == f"Kl. {t['hh']}" and valgt()["k"] == t["k"]
                    page.click("#tilbakeNa"); page.wait_for_function("window.__S.idx === null")
                    assert not page.query_selector("#tilbakeNa") and valgt()["i"] == v["i"] and page.get_attribute(".dagknapp[aria-pressed='true']", "data-day") == imorgen
                    # ---- 9. sommertiden slutter 25.10: 6-timers dager med riktige Oslo-timer, og dagens tall lest av timene ----
                    for d in (24, 25, 26):
                        key = f"2026-10-{d}"
                        exp = [f"{oslo(x['t']):%H}" for x in hs if oslo_day(x["t"]) == key]
                        page.click(f".dagknapp[data-day='{key}']"); page.wait_for_selector(f"#tstripe[data-day='{key}']"); page.wait_for_timeout(150)
                        assert page.get_attribute(f".dagknapp[data-day='{key}']", "aria-pressed") == "true"
                        hh = [c["hh"] for c in kolonner()]
                        tikk = page.evaluate("[...document.querySelectorAll('#tstripe .tikk span')].map(s => s.textContent.trim()).filter(Boolean)")
                        assert hh == exp, f"{key}: kolonnene skal være {exp}, fikk {hh}"
                        assert tikk == exp, f"{key}: tikkene skal være {exp}, fikk {tikk}"
                        assert len(exp) == 4, (key, exp)
                        assert oslo_day(hs[page.evaluate("window.__S.idx")]["t"]) == key
                        # dagen ligger utenfor dagssammendragene: tallet leses av timene med samme regel som dayBest()
                        cls, st, bi = day_best(hs, now_idx(hs), key); dom = dommen(); knapp = tekst(f".dagknapp[data-day='{key}'] .rute")
                        if cls.startswith("r-"):
                            assert dom["tall"] == knapp == str(min(5, st)), (key, cls, st, dom, knapp)
                            assert (dom["vindu"] == f"{oslo(hs[bi]['t']):%H}") if st >= 1 else dom["vindu"] is None, (key, dom, bi)
                        else:
                            assert dom["tall"] is None and knapp == "" and dom["ord"] == {"miss": "Mangler data", "dark": "Mørkt"}[cls], (key, cls, dom, knapp)
                    shot("unstad-6t", scheme); audit("unstad-6t")
                    # tilbakeknappen følger stakken: fra Hjem heter den «Hjem» og går dit (bare mobil)
                    if mobile:
                        go("#hjem", "#viewHjem:not([hidden]) :is(#forside, .hjem-linje)")
                        go("#spot=unstad", SPOT_KLAR)
                        assert page.get_attribute("#spotBack", "aria-label") == "Tilbake til Hjem" and tekst("#spotBack") == "Hjem"
                        page.click("#spotBack"); page.wait_for_selector("#viewHjem:not([hidden]) :is(#forside, .hjem-linje)")
                    go("#utforsk", "#viewUtforsk:not([hidden])")
                    # ---- Farstadsanden ----
                    go("#spot=farstadsanden", SPOT_KLAR)
                    page.wait_for_selector("#tstripe .tsvg")
                    shot("farstadsanden", scheme); audit("farstadsanden")
                    # ---- 11. «Treffer ikke» ----
                    aapne(treffer)
                    # karakteren etter tallet, årsaken på egen linje, og «–» som det store tallet (regel (c): ingen pålitelig høyde)
                    assert tekst("#spOver .tdom .to") == "Ikke surfbart" and tekst("#spOver .tdom .rute") == "0" and tekst("#spOver .tgrunn").startswith("Treffer ikke"), ("«Treffer ikke» i en lys time skal vise tallet 0, karakteren og årsaken", tekst("#spOver .sek-spot"), tekst("#spOver .tgrunn"))
                    assert tekst("#spOver .t-svell") == "–" and "Treffer ikke" in tekst("#spOver .svell.surf"), tekst("#spOver .svell.surf")
                    assert page.evaluate(f"document.querySelectorAll(\"#tstripe .tk[data-i='{treffer[1]}'] .segs.r-0 i.pa\").length") == 0
                    shot("treffer-ikke", scheme); audit("treffer-ikke")
                    if treffer_mork:   # samme i en mørk time: ingen vurdering, bare «Bare lyse timer får tall» - grunnen står fortsatt i surf-raden
                        hx = aapne(treffer_mork)
                        assert tekst("#spOver .sek-spot .sub") == "Bare lyse timer får tall" and not page.query_selector("#spOver .tdom"), tekst("#spOver .sek-spot")
                        assert page.evaluate(f"document.querySelector(\"#tstripe .tk[data-i='{treffer_mork[1]}'] .segs\").children.length") == 0, "en mørk time skal ikke ha segmenter"
                        assert "mørkt, ingen vurdering" in valgt()["aria"]
                        # S45 5 a (svar.md 26.11.2026 kl. 13.10): «–» i mørke timer uten ord under, heller ikke «Treffer ikke»
                        assert tekst("#spOver .t-svell") == "–" and not page.query_selector("#spOver .svell.surf .svell-sub") and tekst("#spOver .svell > .etikett") == "Surf", f"en mørk time skal bare ha «–» under SURF: {tekst('#spOver .svell.surf')}"
                    # Theodor 16.10 (Grøtfjord 17.10 kl. 14): ved surfehøyde 0 og «Blåst ut» er tallet BarentsWatch-høyden (regel (c))
                    bo = next(((sid, i) for sid, d in details.items() for i, x in enumerate(d["hours"]) if x.get("surf_height") == 0
                               and x.get("low_reason") == "blown_out" and (x.get("bw_height") or 0) > 0.5 and i > now_idx(d["hours"]) and light_of(x) != "mørkt" and page.evaluate("(h) => visesSomSjo(h)", x)), None)
                    if bo:   # tallet er totalhøyden: «SJØ», ett tall, ikke noe kroppsmål (S45 2). Bare lyse timer: en mørk time har «–» (S45 5 a)
                        hx = aapne(bo); tall = tallene(tekst("#spOver .svell.surf"))
                        assert len(tall) == 1 and abs(tall[0] - hx["bw_height"]) <= 0.051, (bo, tekst("#spOver .svell.surf"), hx["bw_height"])
                        assert tekst("#spOver .svell > .etikett") == "Sjø" and not page.query_selector("#spOver .svell.surf .svell-sub"), tekst("#spOver .svell.surf")
                    ok = next(((sid, i) for sid, d in details.items() for i, x in enumerate(d["hours"]) if (x.get("surf_height") or 0) > 0.3
                               and x.get("surf_height_sets") is not None and not x.get("low_reason") and i > now_idx(d["hours"]) and light_of(x) != "mørkt"), None)
                    if ok:
                        hx = aapne(ok); tall = tallene(tekst("#spOver .svell.surf"))
                        assert tall and abs(tall[0] - hx["surf_height"]) <= 0.051 and abs(tall[-1] - hx["surf_height_sets"]) <= 0.051, (ok, tekst("#spOver .svell.surf"), hx["surf_height"], hx["surf_height_sets"])   # JS og Python runder x,x5 ulikt
                    # ---- ekte 0 (flat-sperren): ordet, aldri «–» eller «null» (fysikk-kontrollør runde 2) ----
                    flat = next(((sid, i) for sid, d in details.items() for i, x in enumerate(d["hours"]) if x.get("low_reason") == "flat" and x.get("surf_height") == 0 and i > now_idx(d["hours"])), None)
                    if flat:
                        hx = aapne(flat); surf = tekst("#spOver .svell.surf")
                        assert not tallene(surf) and tekst("#spOver .t-svell") == "–" and "Mangler" not in surf, (flat, surf)
                        assert (page.evaluate("(h) => ratingWord(h)", hx) in surf) == (light_of(hx) != "mørkt"), (flat, surf)   # mørk time: ingen karakter under «–» (feiljegeren 25.11.2026, funn 2)
                    # «Treffer ikke» med surfehøyde > 0: regel (c) sier intet pålitelig tall → ordet, ikke et tall (runde 3)
                    ti = next(((sid, i) for sid, d in details.items() for i, x in enumerate(d["hours"]) if x.get("low_reason") == "treffer_ikke" and (x.get("surf_height") or 0) > 0 and i > now_idx(d["hours"]) and light_of(x) != "mørkt"), None)
                    if ti:
                        aapne(ti); surf = tekst("#spOver .svell.surf")
                        assert "Treffer ikke" in surf and not tallene(surf) and tekst("#spOver .t-svell") == "–", (ti, surf)
                    # ---- 10. spotsiden på dagen uten tall: «Mangler data» og skravur, aldri 0 ----
                    aapne((MISS_ID, first_miss_idx))
                    dom = dommen()
                    assert dom["ord"] == "Mangler data" and dom["tall"] is None and dom["vindu"] is None, dom
                    assert tekst("#spOver .sek-spot .sub") == "Mangler data" and not page.query_selector("#spOver .tdom") and not page.query_selector("#spOver .t-svell"), tekst("#spOver")
                    assert set(maalene()) <= {"Tidevann"}, f"dagen uten tall skal ikke vise surf eller vind: {maalene()}"
                    # mobil: tom stiplet rute; PC: dagen ligger i de 7 store kolonnene - ordet, ingen tall
                    knapp = page.evaluate(f"(() => {{ const b = document.querySelector(\".dagknapp[data-day='{MISS_DAY.isoformat()}']\"), r = b.querySelector('.rute'); return r ? [r.className, r.textContent.trim(), ''] : [b.className, b.querySelector('.dk-v').textContent.trim(), b.querySelector('.dk-best').textContent.trim() + [...b.querySelectorAll('.dk-sub')].map(e => e.textContent).join('')]; }})()")
                    assert "miss" in knapp[0].split() and knapp[1] == ("" if mobile else "Mangler data") and knapp[2] in ("", "–"), f"dagknappen for dagen uten tall: {knapp}"
                    segs = page.evaluate("[...document.querySelectorAll('#tstripe .tk')].filter(k => +k.dataset.i >= 0).map(k => k.querySelector('.segs').className)")
                    assert segs and all(c == "segs miss" for c in segs), f"timene uten data skal være skravert: {segs}"
                    assert "mangler data" in valgt()["aria"]
                    shot("mangler-data", scheme); audit("mangler-data")
                    # ---- feiljegeren 25.11.2026 (fase 3): KL.-blokka og stripa med endrede tall i en lys time på Unstad ----
                    go("#spot=unstad", SPOT_KLAR); page.wait_for_selector("#tstripe .tsvg"); i_ = valgt()["i"]
                    aapne(("unstad", i_))   # timen i adressen: den står også når den gjøres mørk
                    def med(endring):
                        page.evaluate("""([i, e]) => { const s = DATA.spots.find(x => x.id === 'unstad'); s.__gml = s.__gml || {...s.hours[i]}; s.hours[i] = {...s.__gml, light: 'dag', daylight: true, faded: 0, faded_wind: 0, faded_tide: 0, long_sea: false, ...e}; Front.refresh(); }""", [i_, endring])
                        page.wait_for_timeout(150)
                        return page.evaluate("""() => { const k = document.querySelector('#tstripe .tk.valgt'), v = document.querySelector('#spOver .svell.surf'), sub = v.querySelector('.svell-sub');
                            return {stort: v.querySelector('.t-svell') ? v.querySelector('.t-svell').textContent : null, under: sub ? sub.textContent : null, stolpe: !!k.querySelector('.sbx i'), skravur: k.querySelector('.sbx').classList.contains('miss'), tall: k.querySelector('.srf b') ? k.querySelector('.srf b').textContent : null,
                                etikett: v.querySelector('.etikett').textContent.trim(), ark: v.querySelector('.etikett .forklar').dataset.explain, omriss: k.querySelector('.srf').classList.contains('sjo'), graa: !!v.querySelector('.t-surf.mork'),
                                fyll: k.querySelector('.sbx i') ? getComputedStyle(k.querySelector('.sbx i')).backgroundColor : null, aria: document.querySelector('#tstripeVelg').getAttribute('aria-valuetext')}; }""")
                    # ---- S45 (svar.md 26.11.2026 kl. 13.10) ----
                    # 2: Stormsjø, og Blåst ut når surfehøyden er 0, viser totalhøyden ved spoten (regel (c)). Da heter tallet «SJØ», ikke
                    # «SURF», det har ikke kroppsmål, etiketten åpner arket om signifikant høyde, stolpen er et omriss, og skjermleseren sier «sjø»
                    for e_, tall_ in (({"stars": 0, "low_reason": "stormsjo", "surf_height": 0.91, "surf_height_sets": 1.16, "bw_height": 2.65, "wind_speed": 15.2, "wind_type": "onshore"}, "2,7"),
                                      ({"stars": 1, "low_reason": "stormsjo", "surf_height": 0.91, "surf_height_sets": 1.16, "bw_height": 2.65, "wind_speed": 15.2, "wind_type": "onshore"}, "2,7"),
                                      ({"stars": 0, "low_reason": "blown_out", "surf_height": 0, "surf_height_sets": None, "bw_height": 1.9, "wind_speed": 12, "wind_type": "onshore"}, "1,9")):
                        sj_ = med(e_)
                        assert sj_["etikett"] == "Sjø" and sj_["stort"] == f"{tall_}m" and sj_["under"] is None and sj_["ark"] == "hs", f"S45 2, totalhøyden skal hete SJØ og ikke ha kroppsmål: {e_} {sj_}"
                        assert sj_["stolpe"] and sj_["omriss"] and sj_["fyll"] == "rgba(0, 0, 0, 0)" and f"Sjø {tall_} m" in sj_["aria"] and "surf" not in sj_["aria"].lower(), f"S45 2, stripa og skjermleseren: {sj_}"
                        assert page.evaluate("(h) => Spot.kroppshoyde(h)", {**e_, "light": "dag"}) is None, "S45 2: ikke kroppsmål for totalhøyden"
                        assert not re.search(r"hode|hofte|bryst|skulder|kne", tekst("#spOver").lower()), f"S45 2: kroppsmål i en time med totalhøyden: {tekst('#spOver')}"
                    # … og bare da: Blåst ut med ekte surfehøyde, og Stormsjø uten totalhøyde, er fortsatt «SURF» med kroppsmål
                    for e_, tall_ in (({"stars": 0, "low_reason": "blown_out", "surf_height": 1.4, "surf_height_sets": 1.8, "bw_height": 1.9, "wind_speed": 12, "wind_type": "onshore"}, "1,4–1,8"),
                                      ({"stars": 0, "low_reason": "stormsjo", "surf_height": 0.91, "surf_height_sets": 1.16, "bw_height": None, "wind_speed": 15.2, "wind_type": "onshore"}, "0,9")):
                        su_ = med(e_)
                        assert su_["etikett"] == "Surf" and su_["stort"] == f"{tall_}m" and su_["under"] and su_["ark"] == "surf_height" and not su_["omriss"] and f"Surf {tall_} m" in su_["aria"], f"S45 2 gjelder bare totalhøyden: {e_} {su_}"
                    # de samme timene i listene, i regionraden, på kortet i Utforsk, i tabellen på forsiden og for skjermleseren: «sjø 2,7 m»
                    sjl_ = page.evaluate("""() => { const F = Front.helpers, b = (o) => Object.assign({light: 'dag', faded: 0, t: '2026-10-15T10:00Z'}, o), tmp = document.createElement('div');
                        const st = b({stars: 0, low_reason: 'stormsjo', surf_height: 0.91, surf_height_sets: 1.16, bw_height: 2.65, wind_speed: 15.2, wind_type: 'onshore'});
                        const bl = b({stars: 0, low_reason: 'blown_out', surf_height: 0, bw_height: 1.9, wind_speed: 12, wind_type: 'onshore'});
                        const su = b({stars: 0, low_reason: 'blown_out', surf_height: 1.4, surf_height_sets: 1.8, bw_height: 1.9, wind_speed: 12, wind_type: 'onshore'});
                        const les = (h) => { tmp.innerHTML = F.naHtml(h, null, ratingWord(h)); return [...tmp.childNodes].map(e => e.textContent.trim()); };
                        return {st: les(st), bl: les(bl), su: les(su), merket: [st, bl, su].map(h => F.hoydeMedMerke(h)), sjo: [st, bl, su].map(h => F.erSjo(h)), hvorfor: [st, bl, su].map(h => surfHeadline(h)),
                                ro: [st, bl, su].map(h => visesSomSjo(h)), svak: visesSomSjo(b({stars: 0, low_reason: 'blown_out', surf_height: 0, bw_height: 0.5, wind_speed: 1})), forbud: visesSomSjo({...st, _forbud: true})}; }""")
                    assert sjl_["st"] == ["Ikke surfbart", "sjø 2,7 m", "Stormsjø"] and sjl_["bl"] == ["Ikke surfbart", "sjø 1,9 m", "Blåst ut"] and sjl_["su"] == ["Ikke surfbart", "1,4–1,8 m", "Blåst ut"], f"S45 2 i listene: {sjl_}"
                    assert sjl_["merket"] == ["sjø 2,7 m", "sjø 1,9 m", "1,4–1,8 m"] and sjl_["sjo"] == [True, True, False] and sjl_["ro"] == [True, True, False] and not sjl_["svak"] and not sjl_["forbud"], f"S45 2: {sjl_}"
                    assert sjl_["hvorfor"] == ["Stormsjø (sjø 2,7 m)", "Blåst ut (sjø 1,9 m)", "Blåst ut (1,4 m)"], f"S45 2 i «Hvorfor»: {sjl_['hvorfor']}"
                    # 5 a: en mørk time har «–» uten tall og uten ord under, også når timen har en høyde. Stripa viser den fortsatt, dempet
                    for e_ in ({"stars": 2, "low_reason": None, "surf_height": 1.2, "surf_height_sets": 1.5}, {"stars": 0, "low_reason": "treffer_ikke", "surf_height": 1.2}, {"stars": 0, "low_reason": "stormsjo", "surf_height": 0.9, "bw_height": 2.65}):
                        mk_ = med({**e_, "light": "mørkt", "daylight": False})
                        assert mk_["stort"] == "–" and mk_["under"] is None and mk_["etikett"] == "Surf" and not mk_["graa"], f"S45 5 a, mørk time: {e_} {mk_}"
                        assert not re.search(r"\d,\d ?m\b", tekst("#spOver .svell.surf")), f"S45 5 a: tall i en mørk time: {tekst('#spOver .svell.surf')}"
                    assert med({"stars": 2, "low_reason": None, "surf_height": 1.2, "surf_height_sets": 1.5, "light": "mørkt", "daylight": False})["stolpe"], "mørk time: høyden står fortsatt som dempet stolpe i stripa (småvalg 4 a)"
                    # funn 3: en flat time har «–» i det store tallet og i stripa, som i listene. Ikke «0,0 m, Nesten flatt»
                    fl_ = med({"stars": 0, "low_reason": None, "surf_height": 0.04, "surf_height_sets": 0.05, "zero_losses": None, "local_rules": None})
                    assert fl_["stort"] == "–" and fl_["under"] == "Flatt" and not fl_["stolpe"] and not fl_["skravur"] and fl_["tall"] == (None if mobile else "–"), f"flat time: {fl_}"
                    # en mørk flat time: ingen karakter under «–» (funn 2)
                    fm_ = med({"light": "mørkt", "daylight": False, "stars": 0, "low_reason": "flat", "surf_height": 0.04})
                    assert fm_["stort"] == "–" and fm_["under"] is None, f"mørk flat time: {fm_}"
                    # funn 6: svellet mangler i en time med andre tall: raden står med ordet for det, og periode og retning når de finnes
                    med({"swell_offshore": None, "period": 9.0, "dir_offshore": 300}); rad_ = maalene()["Svell ute"]
                    assert "–" in rad_ and "Mangler data" in rad_ and "9 s" in rad_ and "300°" in rad_ and not re.search(r"\d,\d", rad_), rad_
                    med({"swell_offshore": None, "period": None, "dir_offshore": None}); rad_ = maalene()["Svell ute"]
                    assert "Mangler data" in rad_ and not re.search(r"\d", rad_), rad_
                    # funn 7: en time med vurdering, men uten høyde, er skravert i stripa
                    for e_ in ({"stars": 1, "low_reason": None, "surf_height": None, "surf_height_sets": None}, {"stars": 0, "low_reason": "stormsjo", "surf_height": None, "surf_height_sets": None, "bw_height": None}):
                        mh_ = med(e_); assert mh_["stort"] == "–" and mh_["skravur"] and not mh_["stolpe"], f"time uten høyde: {e_} {mh_}"
                        # runde 2 e: ordet for at høyden mangler under «–», ikke karakteren («– Dårlig»), også i en mørk time
                        assert mh_["under"] == "Mangler data", f"under «–» når høyden mangler: {mh_}"
                        mm_ = med({**e_, "light": "mørkt", "daylight": False}); assert mm_["stort"] == "–" and mm_["under"] == "Mangler data", f"mørk time uten høyde: {mm_}"
                    if mobile:   # runde 2, viktig 1: trykk på sikkerheten og «kystmodell 100 m» åpner hvert sitt ark, midt i og 20 px over og under
                        med({"stars": 1, "low_reason": None, "confidence": 90, "zone": "barentswatch", "uncertain": False})
                        for bw_, bh_ in ((375, 548), (390, 663), (393, 700), (402, 720), (412, 732), (430, 780)):
                            page.set_viewport_size({"width": bw_, "height": bh_}); page.wait_for_timeout(150)
                            for key_, ord_, tittel_ in (("confidence", "Høy sikkerhet · kystmodell 100 m", "Sikkerhet"), ("hs", "kystmodell 100 m", "Signifikant høyde")):
                                for dy_ in (-20, 0, 20):
                                    x_, y_, to_ = page.evaluate("""(k) => { const e = document.querySelector(`#viewSpot .kilder .forklar[data-explain="${k}"]`); e.scrollIntoView({block: 'center', behavior: 'instant'}); const b = e.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2, e.textContent]; }""", key_)
                                    assert to_ == ord_, to_
                                    page.mouse.click(x_, y_ + dy_); page.wait_for_selector("#exSheet.open")
                                    assert page.text_content("#exTitle").strip() == tittel_, f"trykk {dy_} px fra midten av «{ord_}» ({bw_} x {bh_}) åpnet «{page.text_content('#exTitle')}»"
                                    page.keyboard.press("Escape"); page.wait_for_selector("#exSheet:not(.open)", state="attached"); page.wait_for_timeout(50)
                        page.set_viewport_size({"width": vp[0], "height": vp[1]}); page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(150)
                    else:   # runde 2 b: 200 % tekst på nettsiden: surfetallet er klart størst, og ordene i radene brytes ikke midt i
                        med({"stars": 1, "low_reason": None, "surf_height": 3.0, "surf_height_sets": 3.7})
                        page.evaluate("document.documentElement.style.fontSize = '200%'")
                        for bw_ in (1024, 1060, 1280, 1440):
                            page.set_viewport_size({"width": bw_, "height": vp[1]}); page.wait_for_timeout(150)
                            b2 = page.evaluate("""() => { const brutt = [], w = document.createTreeWalker(document.querySelector('#spOver .maalene'), NodeFilter.SHOW_TEXT);
                                while(w.nextNode()){ const t = w.currentNode; for(const m of t.textContent.matchAll(/[A-Za-zÆØÅæøå0-9:,°]{3,}/g)){ const r = document.createRange(); r.setStart(t, m.index); r.setEnd(t, m.index + m[0].length); if(new Set([...r.getClientRects()].filter(x => x.width > 0).map(x => Math.round(x.top))).size > 1) brutt.push(m[0]); } }
                                return {brutt, px: parseFloat(getComputedStyle(document.querySelector('#spOver .t-surf')).fontSize), rad: parseFloat(getComputedStyle(document.querySelector('#spOver .maal .mv')).fontSize)}; }""")
                            assert not b2["brutt"] and b2["px"] >= 2 * b2["rad"], f"200 % tekst på {bw_} px: {b2}"
                            if bw_ == 1440:   # runde 3 k: også ved 175 % på 1440 px slår oppsettet inn, så «pålands» og «Tidevann» ikke brytes midt i
                                page.evaluate("document.documentElement.style.fontSize = '175%'"); page.wait_for_timeout(150)
                                b3 = page.evaluate("""() => { const brutt = [], w = document.createTreeWalker(document.querySelector('#spOver .maalene'), NodeFilter.SHOW_TEXT);
                                    while(w.nextNode()){ const t = w.currentNode; for(const m of t.textContent.matchAll(/[A-Za-zÆØÅæøå0-9:,°]{3,}/g)){ const r = document.createRange(); r.setStart(t, m.index); r.setEnd(t, m.index + m[0].length); if(new Set([...r.getClientRects()].filter(x => x.width > 0).map(x => Math.round(x.top))).size > 1) brutt.push(m[0]); } }
                                    return {brutt, px: parseFloat(getComputedStyle(document.querySelector('#spOver .t-surf')).fontSize), rad: parseFloat(getComputedStyle(document.querySelector('#spOver .maal .mv')).fontSize)}; }""")
                                assert not b3["brutt"] and b3["px"] >= 2 * b3["rad"], f"175 % tekst på 1440 px: {b3}"
                        page.evaluate("document.documentElement.style.fontSize = ''"); page.set_viewport_size({"width": vp[0], "height": vp[1]}); page.wait_for_timeout(150)
                    # funn 1 (stopper): det store tallet står på én linje og i kolonnen sin, også på smale nettsider
                    for bredder_, e_ in (((1024, 1200, 1280, 1300, 1440) if not mobile else (320, 360, 390), x) for x in ({"surf_height": 3.0, "surf_height_sets": 3.7}, {"surf_height": 10.2, "surf_height_sets": 13.0}, {"surf_height": 10.2, "surf_height_sets": None})):
                        med({"stars": 3, "low_reason": None, **e_})
                        for bw_ in bredder_:
                            page.set_viewport_size({"width": bw_, "height": vp[1]}); page.wait_for_timeout(150)
                            t1 = page.evaluate("""() => { const e = document.querySelector('#spOver .t-surf'), r = document.createRange(); r.selectNodeContents(e); const b = r.getBoundingClientRect(), k = document.querySelector('#spOver').getBoundingClientRect();
                                return {tekst: e.textContent, linjer: Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)), ut: Math.round(b.right - k.right), px: Math.round(parseFloat(getComputedStyle(e).fontSize))}; }""")
                            assert t1["linjer"] == 1 and t1["ut"] <= 0 and t1["px"] >= 28, f"det store tallet skal stå på én linje og i kolonnen ({bw_} px): {t1}"
                        page.set_viewport_size({"width": vp[0], "height": vp[1]}); page.wait_for_timeout(150)
                    # runde 2 c: nettlesere uten cqi (Safari før 16) får en reserve i px, ikke brødtekststørrelsen
                    res_ = page.evaluate("""() => { for(const ark of document.styleSheets){ let rr; try { rr = ark.cssRules; } catch(e){ continue; }
                        for(let i = rr.length - 1; i >= 0; i--) if(rr[i] instanceof CSSSupportsRule && /cqi/.test(rr[i].conditionText)){ const t = rr[i].cssText; ark.deleteRule(i); const px = getComputedStyle(document.querySelector('#spOver .t-surf')).fontSize; ark.insertRule(t, i); return px; } } return null; }""")
                    assert res_ in ("40px", "30px"), f"reserven for det store tallet (40 px, 30 px for et spenn): {res_}"
                    # funn 17 og runde 2 f: «, usikkert» (lang sjø) står i dommen, og i dagkolonnene på nettsiden
                    dk_ = page.evaluate("""() => { const s = DATA.spots.find(x => x.id === 'unstad'), kn = document.querySelector('.dagvelger .dagknapp[aria-pressed="true"]'), o = s.dager.find(x => x.d === kn.dataset.day), gml = o.h, foer = document.querySelector('#viewSpot .dom-ord b').textContent;
                        o.h = {...o.h, stars: Math.max(1, o.h.stars || 0), low_reason: null, long_sea: true}; Front.refresh();
                        const k2 = document.querySelector('.dagknapp.stor[aria-pressed="true"]'), ut = [foer, document.querySelector('#viewSpot .dom-ord b').textContent, ...(k2 ? [k2.querySelector('.dk-ord').textContent, k2.getAttribute('aria-label')] : [])]; o.h = gml; Front.refresh(); return ut; }""")
                    assert "usikkert" not in dk_[0] and len(dk_) == (2 if mobile else 4) and all(", usikkert" in x for x in dk_[1:]), f"«, usikkert» i dommen og dagkolonnen: {dk_}"
                    page.evaluate("(i) => { const s = DATA.spots.find(x => x.id === 'unstad'); s.hours[i] = s.__gml; delete s.__gml; Front.refresh(); }", i_)

                for scheme in ("mork", "lys"):
                    media(scheme)
                    bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
                    assert bg == ("rgb(0, 41, 65)" if scheme == "mork" else "rgb(242, 239, 232)"), f"temaet følger ikke systemet ({label}, {scheme}): {bg}"
                    # ---- 6. Hjem ----
                    go("#hjem", "#viewHjem:not([hidden]) :is(#forside, .hjem-linje)")
                    gen = oslo(FORECAST["generated"])
                    if mobile:   # B 4.0 steg 3: topplinja «ONS 14.10 · LYS 06:50–18:00» og «Fra Tromsø», oppdatert-tiden står nederst
                        dato = f"{WD[TODAY.weekday()][:3].capitalize()} {TODAY:%d.%m} · " + (f"Lys {_LYS[0]:%H:%M}–{_LYS[-1]:%H:%M}" if _LYS else "Mørkt hele dagen")
                        linje = page.text_content("#viewHjem .hjem-linje")
                        assert dato in linje and f"Fra {FRA_NAVN}" in linje, f"topplinja mangler «{dato}» eller startstedet: {linje}"
                        assert f"Oppdatert i dag kl. {gen:%H:%M}." in page.text_content("#viewHjem .kilder"), "oppdatert-tiden mangler nederst på Hjem"
                    else:   # B4 steg 6 (SPEC §6D): datolinja «Onsdag 14.10 · Lys 06:50–18:00 · Fra Tromsø · Oppdatert 21:00 · 8 spots»
                        dato = f"{WD[TODAY.weekday()].capitalize()} {TODAY:%d.%m} · " + (f"Lys {_LYS[0]:%H:%M}–{_LYS[-1]:%H:%M}" if _LYS else "Mørkt hele dagen")
                        linje = page.text_content("#forside .fs-dato")
                        assert linje.startswith(dato) and f"Fra {FRA_NAVN}" in linje and f"Oppdatert {gen:%H:%M}" in linje and linje.endswith(f"{len(OV)} spots"), f"datolinja: {linje}, ventet «{dato} …»"
                        # «Neste 7 dager» per spot i Steinkrøssas region: dagen uten tall er «–», aldri 0
                        page.click(f"#forside [data-fsreg='{OV[MISS_ID]['region']}']"); page.wait_for_selector(f"#forside [data-fsreg='{OV[MISS_ID]['region']}'][aria-pressed='true']")
                    miss_cells = page.evaluate("""() => { const rad = [...document.querySelectorAll('#viewHjem .regionliste a.favlinje, #forside table.fs-matrise tbody tr')].find(r => r.textContent.includes('Steinkrøssa'));
                        return rad ? [...rad.querySelectorAll('.uke i, td')].map(c => ({cls: c.className, txt: c.textContent.trim()})) : null; }""")
                    assert miss_cells, "fant ikke Steinkrøssa på Hjem"
                    if mobile:
                        # Designrevisjonen fase 2 punkt 1: regionradene har samme form som favorittradene, og tallet er dagens
                        # (dayBest). «Mørkt nå. Tallene gjelder i morgen.» står én gang over lista når radene viser i morgen (T0 er
                        # kl. 22:10): da står dagens ord uten «Nå». Sortert etter dagens tall. «Nå» med ordet og høyden for
                        # nå-timen (S38 1 b) prøves under, i lys, før det lysner og etter midnatt.
                        reg_r = page.evaluate("""() => { const H = Front.helpers, key = Front.state.hjemDag;
                            return [...document.querySelectorAll('#viewHjem .regionliste a.favlinje')].map(r => { const s = DATA.spots.find(s => r.getAttribute('href') === '#spot=' + s.id), b = H.dayBest(s, key);
                                return {navn: s.name, tall: r.querySelector('.t-listetall').textContent.trim(), st: b.st, meta: r.querySelector('.etikett').textContent, setn: !!r.querySelector('.setn'), uke: r.querySelectorAll('.uke i').length}; }); }""")
                        assert reg_r, "ingen regionrader på Hjem"
                        for r in reg_r:
                            assert r["tall"] == ("" if r["st"] is None else str(min(5, r["st"]))), f"regionraden skal vise dagens tall (dayBest): {r}"
                            assert "Nå" not in r["meta"].split() and "Mørkt nå" not in r["meta"] and not r["setn"] and r["uke"] == 7, f"regionraden: {r}"
                        SORT_JS = """(q) => { const H = Front.helpers, key = Front.state.hjemDag, er = [...document.querySelectorAll(q)].map(r => DATA.spots.find(s => r.getAttribute('href') === '#spot=' + s.id));
                            const n = (s) => { const st = H.dayBest(s, key).st; return {navn: s.name, st: st == null ? -1 : st, kj: (window.KJORETID && KJORETID.min[s.id]) || Infinity}; };
                            const skal = er.map(n).sort((a, b) => b.st - a.st || a.kj - b.kj || a.navn.localeCompare(b.navn, 'nb'));
                            return {er: er.map(s => s.name), skal: skal.map(x => x.navn), kjAvgjor: skal.some((x, i) => i && skal[i - 1].st === x.st && skal[i - 1].kj !== x.kj), navnAvgjor: skal.some((x, i) => i && skal[i - 1].st === x.st && skal[i - 1].kj === x.kj)}; }"""
                        srt = page.evaluate(SORT_JS, "#viewHjem .regionliste a.favlinje")
                        assert srt["er"] == srt["skal"], f"regionradene skal stå etter dagens tall, så kjøretid, så navn: {srt}"
                        assert srt["kjAvgjor"], f"testdataene skal ha minst to regionrader med samme tall og ulik kjøretid, ellers prøver ikke testen den andre nøkkelen: {srt}"
                        merk = page.text_content("#viewHjem #hjemMerk") if page.query_selector("#viewHjem #hjemMerk") else None
                        assert merk == "Mørkt nå. Tallene gjelder i morgen.", f"T0 er kl. 22:10 - linja over lista mangler: {merk}"
                        assert not page.query_selector("#viewHjem .rad, #viewHjem .chip, #viewHjem .hjem-bunn"), "gamle rader, brikker eller Innstillinger-pille på mobil-Hjem"
                        assert not any(r["meta"].startswith("I morgen:") or " · I morgen:" in r["meta"] for r in reg_r), f"«I morgen:» skal ikke stå på hver rad når linja står over lista: {reg_r[:2]}"
                        # ... og der den IKKE skal stå: midt på dagen (lyst), og etter midnatt før nattas første varsel (da er radene «i dag»)
                        # (varselet i testfila er laget kl. 21, så dag 1 er «over» i dataene selv: for «i lys» lånes sammendraget fra dag 2)
                        # S38 1 b (svar.md 24.11.2026 kl. 22.25; Theodors ønske 17.11.2026, S15 b): når radene viser i dag, står «Nå» med
                        # ordet og høyden for nå-timen sist i metalinja («Kvaløya · ca. 45 min · Nå Smått 0,6–0,8 m»). Er nå-timen mørk
                        # (før det lysner, etter midnatt), sier raden «Nå Mørkt», uten tall. Tallet til venstre er fortsatt dagens.
                        # «i lys»: dag 1 i testfila er «over» og nå-timene er fra kl. 21, så dagssammendraget lånes fra dag 2, og nå-timen
                        # er ukas beste time for spoten flyttet til klokka. «før det lysner»: samme dag, men nå-timen er mørk.
                        # feiljegeren 25.11.2026, funn 12: mørketid uten lyse timer. Overskriften sier at det er mørkt, aldri «Ingen surf»
                        # om dager uten vurdering. Med tall (0) alle dagene sier den «Ingen surf de neste …» som før.
                        ovs_ = page.evaluate("""() => { const H = Front.helpers, sp = DATA.spots.slice(0, 3), days = H.weekDays(sp), null0 = {stars: 0, surf_height: 0.1, low_reason: 'flat', t: days[0].key + 'T10:00Z', light: 'dag'};
                            const gml = sp.map(s => s.dager), sett = (f) => { for(const s of sp) s.dager = days.map((d, i) => f(d, i)); const o = H.overskrift(sp, days, true); return o; };
                            const mork = sett((d) => ({d: d.key, status: 'dark'})), blandet = sett((d, i) => i % 2 ? {d: d.key, status: 'dark'} : {d: d.key, status: 'ok', h: {...null0, t: d.key + 'T10:00Z'}, start: d.key + 'T10:00Z', slutt: d.key + 'T10:00Z'}),
                                  null_ = sett((d) => ({d: d.key, status: 'ok', h: {...null0, t: d.key + 'T10:00Z'}, start: d.key + 'T10:00Z', slutt: d.key + 'T10:00Z'}));
                            sp.forEach((s, i) => { s.dager = gml[i]; }); return {mork, blandet, null_, n: days.length - 1}; }""")
                        assert ovs_["mork"][-1] == f"Mørkt de neste {ovs_['n']} dagene." and not any("Ingen surf" in l for l in ovs_["mork"]), f"mørketid: overskriften skal si at det er mørkt, ikke «Ingen surf»: {ovs_['mork']}"
                        assert not any("neste" in l for l in ovs_["blandet"]), f"noen dager mørke og noen med 0: ingen setning om de neste dagene: {ovs_['blandet']}"
                        assert ovs_["null_"][-1] == f"Ingen surf de neste {ovs_['n']} dagene.", f"alle dager med tall og 0: som før: {ovs_['null_']}"
                        naa_sett = {}
                        for nar_, tid_ in (("i lys", T0 - dt.timedelta(hours=10)), ("før det lysner", T0 - dt.timedelta(hours=15)), ("etter midnatt", T0 + dt.timedelta(hours=3))):
                            page.clock.set_fixed_time(tid_)
                            if nar_ == "etter midnatt":
                                # testfilas nå-timer rekker ikke over midnatt: uten nå-time står dagens ord med «I dag:» foran, som før S38 1 b
                                page.evaluate("Front.refresh()"); page.wait_for_timeout(150)
                                uten_ = page.evaluate("""() => { const H = Front.helpers, key = Front.state.hjemDag; return [...document.querySelectorAll('#viewHjem .regionliste a.favlinje')].map(r => { const s = DATA.spots.find(s => r.getAttribute('href') === '#spot=' + s.id);
                                    return {naa: !!H.naaOf(s), st: H.dayBest(s, key).st, meta: r.querySelector('.etikett').textContent}; }); }""")
                                assert uten_ and not any(r["naa"] for r in uten_) and any(r["st"] is not None for r in uten_), f"etter midnatt skal testfila ikke ha noen nå-time: {uten_[:3]}"
                                assert all("I dag: " in r["meta"] and "Nå " not in r["meta"] for r in uten_ if r["st"] is not None), f"uten nå-time skal raden vise dagens ord med «I dag:» foran: {uten_[:3]}"
                                # ... og med en (mørk) nå-time, som i et ferskt varsel: «Nå Mørkt»
                                page.evaluate("""(iso) => { window.__naa0 = DATA.spots.map(s => s.naa); for(const s of DATA.spots){ const h = (s.dager[1] && s.dager[1].h) || s.naa[0]; s.naa = h ? [{...h, t: iso, light: 'mørkt', daylight: false}] : []; } }""",
                                              tid_.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:00Z"))
                            else:
                                page.evaluate("""([lys, iso]) => { window.__dag0 = DATA.spots.map(s => s.dager[0]); window.__naa0 = DATA.spots.map(s => s.naa); for(const s of DATA.spots){ const d0 = s.dager[0], d1 = s.dager[1];
                                    s.dager[0] = {...d1, d: d0.d, lys_til: d0.d + 'T16:00Z', h: d1.h ? {...d1.h, t: d0.d + 'T10:00Z'} : d1.h, start: d0.d + 'T10:00Z', slutt: d0.d + 'T10:00Z'};
                                    // nå-timen: ukas beste time for spoten (så noen rader får høyde i meter), flyttet til klokka
                                    const h = s.dager.map(d => d.h).filter(Boolean).sort((a, b) => (b.stars || 0) - (a.stars || 0) || (b.surf_height || 0) - (a.surf_height || 0))[0] || s.naa[0];
                                    s.naa = h ? [{...h, t: iso, light: lys ? 'dag' : 'mørkt', daylight: lys}] : []; } }""",
                                              [nar_ == "i lys", tid_.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:00Z")])
                            page.evaluate("Front.refresh()"); page.wait_for_timeout(150)
                            lys_ = page.evaluate("""() => { const H = Front.helpers, key = Front.state.hjemDag; return {merk: !!document.querySelector('#viewHjem #hjemMerk'), dag: key, tekst: document.querySelector('#viewHjem').textContent.includes('Tallene gjelder i morgen'),
                                rader: [...document.querySelectorAll('#viewHjem .regionliste a.favlinje')].map(r => { const s = DATA.spots.find(s => r.getAttribute('href') === '#spot=' + s.id), h = H.naaOf(s), b = H.dayBest(s, key), oh = h ? H.ordOgHoyde(h) : null;
                                    const e = r.querySelector('.etikett'), ledd = [...e.querySelectorAll('.ledd')], sist = ledd[ledd.length - 1], enh = sist.querySelector('.enh');
                                    return {navn: s.name, st: b.st, tall: r.querySelector('.t-listetall').textContent.trim(), meta: e.textContent, sist: sist.textContent.replace(/\s+/g, ' ').trim().replace(/^· /, ''), aria: r.getAttribute('aria-label'),
                                      mork: !!h && H.mork(h), kjent: !!h && H.known(h), forbud: H.forbudNa(s), ord: oh ? oh.ord.replace(/\s+nå$/, '') + (H.mork(h) ? '' : H.usikkertTillegg(h)) : null, hoyde: oh ? oh.hoyde : null, dagord: b.h ? ratingWord(b.h) : null,
                                      enhStil: enh ? getComputedStyle(enh).textTransform : null, hoyreUt: Math.round(sist.getBoundingClientRect().right - r.getBoundingClientRect().right), overflyt: e.scrollWidth - e.clientWidth}; })}; }""")
                            assert not lys_["merk"] and not lys_["tekst"], f"«Mørkt nå. Tallene gjelder i morgen.» skal ikke stå {nar_}: {lys_}"
                            assert lys_["dag"] == tid_.astimezone(OSLO).date().isoformat(), f"radene skal vise dagen i dag {nar_}: {lys_['dag']}"
                            assert lys_["rader"] and all("I dag:" not in r["meta"] and "I morgen:" not in r["meta"] or r["st"] is None or not r["kjent"] for r in lys_["rader"]), f"metalinja {nar_}: {lys_['rader'][:3]}"
                            med = [r for r in lys_["rader"] if r["st"] is not None and r["kjent"] and not r["forbud"]]
                            assert med, f"ingen regionrader med tall og nå-time {nar_}"
                            for r in med:
                                assert r["tall"] == str(min(5, r["st"])), f"tallet til venstre skal være dagens, også med «Nå» i metalinja ({nar_}): {r}"
                                assert r["hoyreUt"] <= 0 and r["overflyt"] <= 0, f"nå-leddet går ut av raden ({label}, {nar_}): {r}"
                                if r["mork"]:
                                    assert r["sist"] == "Nå Mørkt" and not re.search(r"\d", r["sist"]) and ". Nå mørkt." in r["aria"], f"mørk nå-time skal stå som «Nå Mørkt» uten tall ({nar_}): {r}"
                                else:
                                    vent_ = f"Nå {r['ord']}" + (f" {r['hoyde']} m" if r["hoyde"] else " –")   # «–» ved Flatt og Treffer ikke, som i listene (fase 3, funn 14)
                                    assert r["sist"] == vent_ and f". Nå {r['ord'].lower()}" in r["aria"], f"«Nå» med ordet og høyden for nå-timen skal stå sist i metalinja ({nar_}): {r} (ventet «{vent_}»)"
                                    assert not r["hoyde"] or r["enhStil"] == "none", f"enheten «m» i nå-leddet skal ikke stå i versaler: {r}"
                            for r in lys_["rader"]:
                                if r["st"] is None:
                                    assert not r["sist"].startswith("Nå "), f"en rad uten tall skal ikke ha «Nå» ({nar_}): {r}"
                            naa_sett[nar_] = med
                            page.evaluate("() => { DATA.spots.forEach((s, i) => { if(window.__dag0) s.dager[0] = window.__dag0[i]; s.naa = window.__naa0[i]; }); delete window.__dag0; delete window.__naa0; }")
                        # prøven er ikke tom: i lys finnes rader med høyde i meter og rader uten, og ingen er mørke; før det lysner og
                        # etter midnatt er alle mørke
                        assert any(r["hoyde"] and re.fullmatch(r"Nå .+ \d+,\d(–\d+,\d)? m", r["sist"]) for r in naa_sett["i lys"]) and not any(r["mork"] for r in naa_sett["i lys"]), f"i lys: {[r['sist'] for r in naa_sett['i lys']]}"
                        assert all(r["mork"] for r in naa_sett["før det lysner"]) and all(r["mork"] for r in naa_sett["etter midnatt"]), "nå-timen skal være mørk før det lysner og etter midnatt i testdataene"
                        assert [r["sist"] for r in naa_sett["i lys"]] != [r["sist"] for r in naa_sett["før det lysner"]], "raden før det lysner skal ikke være lik raden midt på dagen"
                        page.clock.set_fixed_time(T0); page.evaluate("Front.refresh()"); page.wait_for_timeout(150)
                        assert page.query_selector("#viewHjem #hjemMerk"), "linja skal stå igjen når klokka er tilbake på 22:10"
                        # feiljegeren (fase 2 runde 5): «usikkert» står også på dagens ord i regionraden (lang sjø), som på nå-leddet
                        usk = page.evaluate("""() => { const H = Front.helpers, key = Front.state.hjemDag, rader = [...document.querySelectorAll('#viewHjem .regionliste a.favlinje')];
                            const s = rader.map(r => DATA.spots.find(x => r.getAttribute('href') === '#spot=' + x.id)).find(x => { const b = H.dayBest(x, key); return b.st != null && b.h && !b.h.long_sea; });
                            if(!s) return null;
                            const h = H.dayBest(s, key).h; h.long_sea = true; Front.refresh();
                            const r = document.querySelector(`#viewHjem .regionliste a.favlinje[href="#spot=${s.id}"]`), ut = {navn: s.name, meta: r.querySelector('.etikett').textContent.replace(/\\s+/g, ' '), aria: r.getAttribute('aria-label')};
                            delete h.long_sea; Front.refresh(); return ut; }""")
                        assert usk and ", usikkert" in usk["meta"] and ", usikkert" in usk["aria"] and "Nå " not in usk["meta"], f"«usikkert» mangler på dagens ord i regionraden: {usk}"
                    cell = miss_cells[4]   # T0 er kl. 22:10 - dagens lys er over, ukeradene starter i morgen (PR #12 punkt c), så dag 5 er rute 4
                    assert ("miss" in cell["cls"] or "tom" in cell["cls"]) and cell["txt"] in ("", "–"), f"dagen uten tall skal være stiplet uten tall på Hjem: {cell}"
                    if not mobile:
                        # forsiden (SPEC §6D): hovedbildet er dagens beste, tabellen «Beste i dag» har samme dagstall som matrisen
                        page.click("#forside [data-fsreg='']"); page.wait_for_selector("#forside [data-fsreg=''][aria-pressed='true']")
                        fs = page.evaluate("""() => ({helt: (document.querySelector('#forside .fs-helt .fs-navn') || {}).textContent || null, tall: (document.querySelector('#forside .fs-helt .fs-tall') || {}).textContent || null,
                            rader: [...document.querySelectorAll('#forside table.fs-tabell tr.s')].map(r => ({id: r.dataset.spot, tall: (r.querySelector('.t-listetall') || {}).textContent || '', stripe: r.querySelectorAll('.fs-stripe i').length})),
                            kol: [...document.querySelectorAll('#forside table.fs-tabell thead th')].map(t => t.textContent.trim()), dag: document.querySelector('#forside .fs-seg [aria-pressed="true"]').textContent.trim(),
                            tittel: document.querySelector('#forside table.fs-tabell').previousElementSibling.querySelector('h2').textContent.trim(),
                            linje: (document.querySelector('#forside .fs-helt .fs-plate .etikett') || {}).textContent || ''})""")
                        # tallet i kolonnen er svellet ute, og overskriften følger dagen som er valgt (Theodor S20 a og b, 20.11.2026)
                        assert fs["dag"] == "I morgen" and fs["kol"] == ["#", "Spot", "I morgen", "Best", "Surf", "06–18"] and fs["tittel"] == "Beste i morgen", fs
                        # etter lyset er knappene «I morgen» og ukedagen etter: en navngitt dag heter «Beste fredag» (Theodor S25, 22.11.2026),
                        # og linja på hovedbildet sier det samme som overskriften over tabellen
                        assert fs["linje"].split(" · ")[1] == fs["tittel"], fs
                        page.click("#forside [data-fsdag='1']"); page.wait_for_selector("#forside [data-fsdag='1'][aria-pressed='true']")
                        fs2 = page.evaluate("({dag: document.querySelector('#forside .fs-seg [aria-pressed=\"true\"]').textContent.trim(), tittel: document.querySelector('#forside table.fs-tabell').previousElementSibling.querySelector('h2').textContent.trim(), linje: (document.querySelector('#forside .fs-helt .fs-plate .etikett') || {}).textContent || ''})")
                        assert fs2["dag"] not in ("I dag", "I morgen") and fs2["tittel"] == "Beste " + fs2["dag"].lower(), fs2
                        assert not fs2["linje"] or fs2["linje"].split(" · ")[1] == fs2["tittel"], fs2   # har dagen et hovedbilde, sier linja det samme
                        page.click("#forside [data-fsdag='0']"); page.wait_for_selector("#forside [data-fsdag='0'][aria-pressed='true']")
                        imorgen = (TODAY + dt.timedelta(days=1)).isoformat()
                        for r in fs["rader"]:
                            cls, st = day_cls(OV[r["id"]], imorgen)
                            assert r["tall"] == (str(min(5, st)) if cls.startswith("r-") else ""), (r, cls, st)
                            assert r["stripe"] in (0, 13), r
                        if fs["helt"]:
                            hid = next(i for i, x in OV.items() if x["name"] == fs["helt"])
                            cls, st = day_cls(OV[hid], imorgen)
                            assert cls.startswith("r-") and st >= 1 and fs["tall"] == str(min(5, st)) and all(not r["tall"] or int(r["tall"]) <= int(fs["tall"]) for r in fs["rader"]), (fs, cls, st)
                        # et vindu som er over, er ikke et råd (fysikk-kontrolløren 16.11.2026): «Best hh–hh» og ringen vises bare mens
                        # vinduet er åpent, og tidsstripa blanker timene som har gått siden oversikten ble laget. Klokka flyttes til
                        # 70 minutter etter at det første vinduet er over («slutt» er starten på vinduets siste time, så 130 minutter etter den)
                        # på en dag med surfbare spots, og settes tilbake etterpå.
                        t_ = lambda iso: dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
                        vinduer = sorted((t_(d["slutt"]), d["d"]) for x in OV.values() for d in x["dager"] if "timer" in d and d.get("slutt") and d.get("h") and (d["h"].get("stars") or 0) >= 1)
                        assert vinduer, "testvarselet har ingen surfbar dag med «timer»"
                        sent, sdag = vinduer[0][0] + dt.timedelta(minutes=130), vinduer[0][1]
                        assert sent.astimezone(OSLO).date().isoformat() == sdag, (sent, sdag)
                        page.clock.set_fixed_time(sent); page.evaluate("Front.refresh()"); page.wait_for_selector("#forside table.fs-tabell")
                        fs2 = page.evaluate("""() => ({dag: document.querySelector('#forside .fs-seg [aria-pressed="true"]').textContent.trim(), tittel: document.querySelector('#forside table.fs-tabell').previousElementSibling.querySelector('h2').textContent.trim(),
                            helt: (document.querySelector('#forside .fs-helt .fs-navn') || {}).textContent || null, best: (document.querySelector('#forside .fs-helt .fs-best') || {}).textContent || null,
                            ring: !!document.querySelector('#forside .fs-helt .fs-best svg'), aria: (document.querySelector('#forside .fs-helt') || {getAttribute(){ return ''; }}).getAttribute('aria-label') || '',
                            rader: [...document.querySelectorAll('#forside table.fs-tabell tr.s')].map(r => ({id: r.dataset.spot, bst: r.querySelector('.fs-bst').textContent.trim(), stripe: [...r.querySelectorAll('.fs-stripe i')].map(i => i.className)}))})""")
                        assert fs2["dag"] == "I dag" and fs2["tittel"] == "Beste i dag", fs2
                        assert not fs2["helt"] or fs2["aria"].split(" · ")[1] == "Beste i dag", fs2   # linja på hovedbildet leses først i aria-teksten
                        def apent(sid):
                            d = next((x for x in OV[sid]["dager"] if x["d"] == sdag), None)
                            return bool(d and d.get("slutt") and d.get("h") and (d["h"].get("stars") or 0) >= 1 and t_(d["slutt"]) + dt.timedelta(hours=1) > sent)
                        naa_kl, over_n = sent.astimezone(OSLO).hour, 0
                        for r in fs2["rader"]:
                            assert (r["bst"] != "–") == apent(r["id"]), f"«Best» i tabellen skal bare vises mens vinduet er åpent: {r}"
                            over_n += r["bst"] == "–" and day_cls(OV[r["id"]], sdag)[1] not in (None, 0)
                            if r["stripe"]:
                                kode = next(x for x in OV[r["id"]]["dager"] if x["d"] == sdag)["timer"]
                                vent = ["vaert" if 6 + i < naa_kl else f"r-{c}" if c in "012345" else {"m": "mork", "x": "miss", ".": "vaert"}[c] for i, c in enumerate(kode)]
                                assert r["stripe"] == vent, f"tidsstripa skal følge «timer» og blanke timene som har gått: {r['id']} {kode} {r['stripe']}"
                        if fs2["helt"]:
                            hid = next(i for i, x in OV.items() if x["name"] == fs2["helt"])
                            assert bool(fs2["best"]) == apent(hid) and bool(re.search(r"Best \d\d–\d\d", fs2["aria"])) == apent(hid), f"«Best» i hovedbildet bare mens vinduet er åpent: {fs2}"
                            over_n += not apent(hid)
                        assert over_n >= 1, f"ingen vinduer var over kl. {sent}: testen prøver ingenting"
                        vindu_over(next(i for i, x in OV.items() if any(d["d"] == sdag and d.get("slutt") and t_(d["slutt"]) == vinduer[0][0] and (d.get("h") or {}).get("stars") for d in x["dager"])), sdag, sent)
                        page.clock.set_fixed_time(T0); page.evaluate("Front.refresh()"); page.wait_for_selector("#forside table.fs-tabell")
                    shot("hjem", scheme); audit("hjem")
                    if mobile:
                        # ---- 6b. Hjem på mobil: overskriften og favorittlinjene (B 4.0 steg 3, SPEC §6A) ----
                        HJEM_JS = """() => ({
                            set: [...document.querySelectorAll('#viewHjem .hjem-overskrift span')].map(e => e.textContent.trim()),
                            rader: [...document.querySelectorAll('#viewHjem .favliste:not(.regionliste) .favlinje')].map(r => ({navn: r.querySelector('.t-navn').textContent.trim(), tall: r.querySelector('.t-listetall').textContent.trim(),
                                meta: r.querySelector('.etikett').textContent.trim(), obs: (r.querySelector('.etikett.obs') || {}).textContent || null, href: r.getAttribute('href'),
                                celler: [...r.querySelectorAll('.uke i')].map(c => c.textContent.trim()), cls: [...r.querySelectorAll('.uke i')].map(c => c.className), setn: (r.querySelector('.setn') || {}).textContent || '', dager: [...r.querySelectorAll('.uke b')].map(c => c.textContent.trim())})),
                            ord: STR.starWords, nullord: [STR.starWords[0], STR.wordSmall, STR.wordMushy, STR.wordTide, STR.wordNotNow.replace(/\\s+nå$/, ''), STR.wordLittleSwell, STR.wordUncertain, STR.wordTooMuchWind, ...Object.values(STR.lowReason)], rediger: (document.querySelector('#favRediger') || {}).textContent || null, fjern: document.querySelectorAll('#viewHjem [data-fjern]').length})"""
                        uten = page.evaluate(HJEM_JS)
                        assert 1 <= len(uten["set"]) <= 2 and not uten["rader"] and uten["rediger"] is None, f"Hjem uten favoritter: {uten}"
                        page.evaluate("""(ids) => { window.__auth0 = window.Auth; window.__logs0 = localStorage.getItem('nordsurf.logs.v1');
                            window.Auth = {state: {ready: true, user: {id: 'test'}, profile: null, favorites: new Set(ids)}, toggleFavorite: async (id) => { Auth.state.favorites.delete(id); }};
                            localStorage.setItem('nordsurf.logs.v1', JSON.stringify([{t: new Date(Date.now() - 26 * 36e5).toISOString(), spot: ids[0], stars: 3, size: 'Brysthøy', wind: 'Offshore', type: 'own'},
                                {t: new Date(Date.now() - 8 * 864e5).toISOString(), spot: ids[1], stars: 4, size: 'Hodehøy', wind: 'Offshore', type: 'own'},
                                {t: new Date(Date.now() + 2 * 36e5).toISOString(), spot: ids[1], stars: 5, size: 'Hodehøy', wind: 'Offshore', type: 'own'}]));
                            Front.refresh(); }""", FAV_IDS)
                        page.wait_for_selector("#viewHjem .favliste:not(.regionliste) a.favlinje")
                        hj = page.evaluate(HJEM_JS)
                        assert [r["href"] for r in hj["rader"]] and sorted(r["href"] for r in hj["rader"]) == sorted(f"#spot={i}" for i in FAV_IDS), f"favorittlinjene: {hj['rader']}"
                        for r in hj["rader"]:
                            assert r["tall"] == r["celler"][0] or (r["tall"] == "" and r["celler"][0] in ("", "–")), f"tallet foran {r['navn']} er ikke dagens rute: {r}"
                            assert len(r["celler"]) == 7 and len(r["dager"]) == 7, f"ukeoversikten på {r['navn']}: {r}"
                            sid = r["href"].split("=")[1]; m = KJORETID.get(sid)
                            # «ca.» foran: tallene er anslag (svar 16.11.2026)
                            kj = None if not m else "ca. " + (f"{m // 60} t" + (f" {m % 60} min" if m % 60 else "") if m >= 60 else f"{m} min")
                            assert (f" · {kj} · " in r["meta"]) if kj else (" min" not in r["meta"] and " t ·" not in r["meta"] and "ca. " not in r["meta"]), f"kjøretiden på {r['navn']}: {r['meta']}"
                        g = next(r for r in hj["rader"] if r["href"] == f"#spot={FAV_IDS[0]}")
                        assert g["obs"] and g["obs"].startswith("Obs ") and "3 av 5 · Brysthøy · Fralands" in g["obs"], f"OBS-linja fra loggen mangler: {g}"
                        assert all(r["obs"] is None for r in hj["rader"] if r is not g), f"OBS-linje fra en logg eldre enn 7 dager eller fram i tid: {hj['rader']}"
                        # overskriften sier aldri noe annet enn lista (SPEC §8): ordet er ordet for tallet i ruta den dagen, og ingen favoritt har høyere
                        assert 1 <= len(hj["set"]) <= 2, f"overskriften skal være én eller to setninger: {hj['set']}"
                        sjekk_overskrift(hj)
                        # et vindu som er over, er ikke et råd, heller ikke på favorittradene (fysikk-kontrolløren 19.11.2026): «Best kl. hh–hh.»
                        # står bare mens vinduet er åpent. Spoten med det første vinduet den dagen radene viser, legges til som favoritt,
                        # klokka flyttes til 70 minutter etter at det vinduet er over (samme regel som på PC-forsiden over), og alt settes tilbake.
                        tf = lambda iso: dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
                        vist = lambda sid, r: next((d for d in OV[sid]["dager"][:2] if WD[dt.date.fromisoformat(d["d"]).weekday()].startswith(r["dager"][0].lower())), None)
                        surfbar = lambda d: bool(d and d.get("slutt") and d.get("h") and (d["h"].get("stars") or 0) >= 1)
                        fdag = vist(FAV_IDS[0], hj["rader"][0])["d"]
                        fvind = sorted((tf(d["slutt"]), i) for i, x in OV.items() for d in x["dager"][:2] if d["d"] == fdag and surfbar(d))
                        assert fvind, f"testvarselet har ingen surfbar spot {fdag}"
                        fsent, fid = fvind[0][0] + dt.timedelta(minutes=130), fvind[0][1]
                        page.clock.set_fixed_time(fsent)
                        page.evaluate("(id) => { window.__fav0 = new Set(Auth.state.favorites); Auth.state.favorites.add(id); Front.refresh(); }", fid); page.wait_for_selector(f'#viewHjem .favliste:not(.regionliste) a.favlinje[href="#spot={fid}"]')
                        hj2, fover = page.evaluate(HJEM_JS), 0
                        for r in hj2["rader"]:
                            sid = r["href"].split("=")[1]; d0 = vist(sid, r)
                            assert d0 and d0["d"] == fdag, f"fant ikke dagen raden til {r['navn']} viser: {r['dager']}"
                            surf = surfbar(d0) and r["tall"].isdigit() and int(r["tall"]) >= 1
                            aapent = surf and tf(d0["slutt"]) + dt.timedelta(hours=1) > fsent
                            assert ("Best kl." in r["setn"]) == aapent, f"«Best kl.» på favorittraden bare mens vinduet er åpent (kl. {fsent}): {r}"
                            fover += surf and not aapent
                        assert fover >= 1, f"ingen favorittvinduer var over kl. {fsent}: testen prøver ingenting"
                        vindu_over(fid, fdag, fsent); page.wait_for_selector(f'#viewHjem .favliste:not(.regionliste) a.favlinje[href="#spot={fid}"]')
                        page.clock.set_fixed_time(T0); page.evaluate("() => { Auth.state.favorites = window.__fav0; Front.refresh(); }"); page.wait_for_selector("#viewHjem .favliste:not(.regionliste) a.favlinje")
                        assert len(page.evaluate(HJEM_JS)["rader"]) == len(FAV_IDS), "favorittene ble ikke satt tilbake etter vindusprøven"
                        # de samme reglene på oppdiktede dager (kontrolløren 12.11.2026): manglende data er aldri «ingen surf»,
                        # «dagens lys er over» og forbud sies som det er, en foreløpig favoritt teller, aldri «de neste 1 dagene»
                        syn = page.evaluate(SYN_JS)
                        for navn, c in syn.items():
                            assert c["fikk"] == c["ventet"], f"overskriften, tilfellet «{navn}»: fikk {c['fikk']}, ventet {c['ventet']}"
                            assert not any(re.search(r"\bnå\b|neste 1 dagene", x) for x in c["fikk"]), f"overskriften, tilfellet «{navn}»: {c['fikk']}"
                            assert not any("HEMMELIGX" in x for x in c["fikk"]), f"overskriften nevner en hemmelig spot, tilfellet «{navn}»: {c['fikk']}"
                        assert page.evaluate("STR.spotForelopig('Breivikeidet')") == "Breivikeidet (foreløpig)"
                        shot("hjem-fav", scheme); audit("hjem-fav")
                        page.click("#favRediger"); page.wait_for_selector("#viewHjem [data-fjern]")
                        red = page.evaluate(HJEM_JS)
                        assert red["fjern"] == len(FAV_IDS) and red["rediger"] == "Ferdig" and page.get_attribute("#favRediger", "aria-pressed") == "true", f"redigeringen av favoritter: {red}"
                        assert page.evaluate("document.activeElement && document.activeElement.id") == "favRediger", "fokus skal stå på «Ferdig» etter at lista er tegnet på nytt"
                        assert page.evaluate("[...document.querySelectorAll('#viewHjem .favliste:not(.regionliste) .favlinje')].every(r => r.getAttribute('role') === 'group' && (r.getAttribute('aria-label') || '').length > 10)"), "radene i redigering mangler navn for skjermleser"
                        assert page.get_attribute("#viewHjem .favleggtil a", "href") == "#sok", "«Legg til spot» skal åpne søket"
                        audit("hjem-rediger")
                        page.click(f'#viewHjem [data-fjern="{FAV_IDS[1]}"]'); page.wait_for_function(f"document.querySelectorAll('#viewHjem [data-fjern]').length === {len(FAV_IDS) - 1}")
                        assert page.evaluate("document.activeElement && document.activeElement.id") == "favRediger", "fokus skal stå på «Ferdig» etter «Fjern»"
                        page.click("#favRediger"); page.wait_for_selector("#viewHjem .favliste:not(.regionliste) a.favlinje")
                        etter = page.evaluate(HJEM_JS)
                        assert sorted(r["href"] for r in etter["rader"]) == sorted(f"#spot={i}" for i in FAV_IDS if i != FAV_IDS[1]), "«Fjern» tok ikke bort favoritten"
                        sjekk_overskrift(etter)
                        page.evaluate("""() => { window.Auth = window.__auth0; delete window.__auth0;
                            if(window.__logs0 == null) localStorage.removeItem('nordsurf.logs.v1'); else localStorage.setItem('nordsurf.logs.v1', window.__logs0); Front.refresh(); }""")
                        page.wait_for_function("!document.querySelector('#viewHjem .favliste:not(.regionliste) .favlinje')")
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
                    # ny størrelse tegner ikke Utforsk på nytt (kartet flytter seg selv, utforsk.js); bare når oppsettet byttes ved 1024 px
                    UM = "#utforskChips [data-view]"
                    u_gammel = lambda: page.evaluate("(um) => !!document.querySelector(um + '[data-gammel]')", UM)
                    page.evaluate("(um) => { document.querySelector(um).dataset.gammel = '1'; }", UM)
                    page.set_viewport_size({"width": vp[0] + 10, "height": vp[1] - 80}); page.wait_for_timeout(200)
                    assert u_gammel() and page.query_selector("#viewUtforsk:not([hidden]) :is(.mk, .klynge)"), f"Utforsk ble tegnet på nytt, eller kartet mistet spotene, ved ny størrelse ({label})"
                    page.set_viewport_size({"width": 800 if not mobile else 1100, "height": vp[1]}); page.wait_for_timeout(300)
                    assert not u_gammel(), f"Utforsk skal tegnes på nytt når oppsettet byttes ved 1024 px ({label})"
                    page.set_viewport_size({"width": vp[0], "height": vp[1]}); page.wait_for_selector("#viewUtforsk:not([hidden]) :is(.mk, .klynge)"); page.wait_for_timeout(500)
                    # kartet står der brukeren la det ved ny time og Front.refresh() (innlogging, synk ferdig): før hoppet det tilbake til
                    # regionen hver hele time (feiljegeren 19.11.2026). Regionknappen og navigasjon hit setter utsnittet som før
                    zoom = lambda: page.evaluate("window.__kart.getZoom()")
                    NY_TIME = "() => { window.__S.now = 'gammel time'; document.dispatchEvent(new Event('visibilitychange')); }"
                    z0 = zoom()
                    for hva, utlos in (("ny time", NY_TIME), ("Front.refresh()", "() => Front.refresh()")):
                        page.evaluate("(um) => { window.__kart.jumpTo({zoom: window.__kart.getZoom() + 2}); document.querySelector(um).dataset.gammel = '1'; }", UM); page.wait_for_timeout(200)
                        z1 = zoom(); page.evaluate(utlos); page.wait_for_timeout(300)
                        assert z1 > z0 + 1 and not u_gammel(), f"Utforsk ble ikke zoomet inn eller ikke tegnet på nytt ved {hva}: testen prøver ingenting ({label}): {z0} -> {z1}"
                        assert abs(zoom() - z1) < 0.01, f"Utforsk-kartet hoppet tilbake ved {hva} ({label}): zoom {z1} -> {zoom()}"
                        page.click("#utforskChips [data-view='Troms']"); page.wait_for_timeout(1000)
                        assert abs(zoom() - z0) < 0.01, f"regionknappen skal sette utsnittet som før ({label}): zoom {zoom()}, ventet {z0}"
                    page.evaluate("window.__kart.jumpTo({zoom: window.__kart.getZoom() + 2})")
                    go("#hjem", "#viewHjem:not([hidden]) :is(#forside, .hjem-linje)"); go("#utforsk", "#viewUtforsk:not([hidden]) :is(.mk, .klynge)"); page.wait_for_timeout(500)
                    assert abs(zoom() - z0) < 0.01, f"navigasjon til Utforsk skal sette utsnittet som før ({label}): zoom {zoom()}, ventet {z0}"
                    # etter et trykk på en klynge er ingen region valgt: uten rettingen zoomet timen ut til hele kartet
                    kl0 = page.query_selector("#viewUtforsk .klynge")
                    if kl0:
                        kl0.click(); page.wait_for_timeout(1000); zk = zoom()
                        page.evaluate(NY_TIME); page.wait_for_timeout(300)
                        assert zk > z0 and abs(zoom() - zk) < 0.01, f"Utforsk-kartet hoppet ut av klyngen ved ny time ({label}): zoom {z0} -> {zk} -> {zoom()}"
                        page.click("#utforskChips [data-view='Troms']"); page.wait_for_timeout(1000)
                        assert abs(zoom() - z0) < 0.01, f"regionknappen skal sette utsnittet som før etter klyngen ({label}): zoom {zoom()}, ventet {z0}"
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
                    # kortet i en mørk time: «Mørkt», og verken høyde eller vurderingsord i Surf (S44 3; feiljegeren 25.11.2026, funn 2)
                    for m in [m_ for m_ in mk if known(naa_of(OV[m_["id"]])) and light_of(naa_of(OV[m_["id"]])) == "mørkt"][:3]:
                        click_mk(m["id"]); page.wait_for_selector("#kartKort:not([hidden])")
                        kt = page.evaluate("[document.querySelector('#kartKort .vurd .ord').textContent.trim(), document.querySelector('#kartKort .fakta div:first-child b').textContent.trim(), document.querySelector('#kartKort .vurd').textContent]")
                        assert kt[0] == "Mørkt" and kt[1] == "–" and not re.search(r"\d", kt[2]), f"kortet i en mørk time ({m['id']}): {kt}"
                        page.click("#kortLukk"); page.wait_for_selector("#kartKort", state="hidden")
                    # kortet for en spot med ekte 0 nå i lys: Surf = ordet, aldri «–»/«null»
                    nul = next((m for m in mk if naa_of(OV[m["id"]]).get("surf_height") == 0 and naa_of(OV[m["id"]]).get("low_reason")), None)
                    if nul:
                        click_mk(nul["id"]); page.wait_for_selector("#kartKort:not([hidden])")
                        h0 = naa_of(OV[nul["id"]])
                        surf_txt = page.text_content("#kartKort .fakta div:first-child b").strip()
                        exp_word = page.evaluate("(h) => ratingWord(h)", h0)
                        assert (surf_txt == "–") if light_of(h0) == "mørkt" else (surf_txt not in ("–", "null", "") and (exp_word in surf_txt or "m" in surf_txt)), (surf_txt, exp_word)
                        page.click("#kortLukk"); page.wait_for_selector("#kartKort", state="hidden")
                    day3 = TODAY + dt.timedelta(days=3)
                    page.click(f"#dagChips .chip[data-day='{day3.isoformat()}']"); page.wait_for_timeout(300)
                    def val_day3(sid):
                        cls, st = day_cls(OV[sid], day3.isoformat())
                        return ("miss" if cls == "miss" else "r-0" if cls == "dark" else cls), st
                    mk3, _ = check_colors(val_day3, str(day3))
                    for m in mk3:
                        if val_day3(m["id"])[0] == "miss": assert m["ord"] == "–", m
                    if not mobile:   # skjermleseren får det samme som raden viser: karakteren, høyden og årsaken (feiljegeren 25.11.2026, funn 14)
                        ul = page.evaluate("""[...document.querySelectorAll('#utforskListe .srad')].filter(r => !r.querySelector('.rute:is(.miss, .mork, .forbud, .over)')).map(r => { const na = r.querySelector('.na'), q = (s) => { const e = na.querySelector(s); return e ? e.textContent.trim() : null; };
                            return {aria: r.getAttribute('aria-label'), navn: r.querySelector('.nm b').textContent.trim(), ord: na.firstChild.textContent.trim(), hoyde: q('.num'), grunn: q('.grunn'), st: r.querySelector('.rute').textContent.trim()}; })""")
                        assert ul, "ingen rader med tall i Utforsk-lista"
                        for r in ul:
                            assert r["aria"] == f"{r['navn']}: " + ", ".join(x for x in (r["ord"], r["hoyde"] if r["hoyde"] != "–" else None, r["grunn"].lower() if r["grunn"] else None, f"{r['st']} av 5") if x), f"teksten for skjermleseren skal være den raden viser: {r}"
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
                    spot_mobil(scheme)
                    # ---- 12. Logger tom ----
                    go("#logger", "#viewSide:not([hidden])")
                    assert "Ingen økter logget ennå" in page.text_content("#viewSide")
                    audit("logger")
                    # ---- 16. 200 % tekst (mobil) og prefers-contrast: more ----
                    if mobile:
                        page.evaluate("document.documentElement.style.fontSize = '200%'")
                        go("#hjem", "#viewHjem:not([hidden]) :is(#forside, .hjem-linje)"); shot("hjem-200", scheme); audit("hjem-200")
                        go("#spot=unstad", SPOT_KLAR); page.wait_for_timeout(300); shot("unstad-200", scheme); audit("unstad-200")
                        brutt = page.evaluate("""[...document.querySelectorAll('#viewSpot .tall, #viewSpot .t-tall, #viewSpot .t-svell, #viewSpot .mv, #viewSpot .t-vindu')]
                            .filter(el => el.getClientRects().length > 1 || el.getBoundingClientRect().height > 1.6 * parseFloat(getComputedStyle(el).fontSize)).map(el => el.className + ' «' + el.textContent.trim() + '»')""")
                        assert not brutt, f"tall brutt over to linjer ved 200 %: {brutt}"
                        navn = page.evaluate("(() => { const h = document.querySelector('#viewSpot .sp-navn h1'), r = document.createRange(); r.selectNodeContents(h); return [r.getBoundingClientRect().right, innerWidth]; })()")
                        assert navn[0] <= navn[1] - 15, f"spotnavnet går ut av skjermen ved 200 % tekst: {navn}"
                        # 320 px: krediteringen brytes i kolonnen (feiljegeren 25.11.2026, funn 18)
                        page.set_viewport_size({"width": 320, "height": 568}); page.wait_for_timeout(250)
                        kr_ = page.evaluate("[...document.querySelectorAll('#viewSpot .kredit')].map(k => { const r = document.createRange(); r.selectNodeContents(k); return [Math.round(r.getBoundingClientRect().right), Math.round(k.getBoundingClientRect().right)]; })")
                        assert kr_ and all(a_ <= b_ + 1 for a_, b_ in kr_), f"krediteringen går ut av kolonnen ved 200 % tekst på 320 px: {kr_}"
                        page.set_viewport_size({"width": vp[0], "height": vp[1]}); page.wait_for_timeout(150)
                        page.evaluate("document.documentElement.style.fontSize = ''")
                    else:
                        # søkelista på nettsiden ved 200 %: ordet, høyden og årsaken står under navnet, ikke oppå det eller i neste rad (funn 18)
                        go("#hjem", "#viewHjem:not([hidden]) :is(#forside, .hjem-linje)")
                        page.evaluate("document.documentElement.style.fontSize = '200%'")
                        page.fill("#sokPC", "o"); page.wait_for_selector("#sokDrop:not([hidden]) .srad"); page.wait_for_timeout(200)
                        so_ = page.evaluate("""() => { const R = [...document.querySelectorAll('#sokDrop .srad')], ut = [], f = (e) => { const r = document.createRange(); r.selectNodeContents(e); return r.getBoundingClientRect(); };
                            R.forEach((r, i) => { const n = f(r.querySelector('.nm')), a = f(r.querySelector('.na')), b = r.getBoundingClientRect(); if(Math.min(n.right, a.right) - Math.max(n.left, a.left) > 1 && Math.min(n.bottom, a.bottom) - Math.max(n.top, a.top) > 2) ut.push(r.innerText); if(a.bottom > b.bottom + 1 || n.bottom > b.bottom + 1) ut.push('ut av raden: ' + r.innerText); }); return {n: R.length, ut}; }""")
                        assert so_["n"] and not so_["ut"], f"søkelista ved 200 % tekst: {so_}"
                        page.fill("#sokPC", ""); page.keyboard.press("Escape"); page.evaluate("document.documentElement.style.fontSize = ''")
                    media(scheme, "more")
                    go("#hjem", "#viewHjem:not([hidden]) :is(#forside, .hjem-linje)"); shot("hjem-kontrast", scheme); audit("hjem-kontrast")
                    go("#spot=unstad", SPOT_KLAR); page.wait_for_timeout(300); shot("unstad-kontrast", scheme); audit("unstad-kontrast")
                    media(scheme)
                if not mobile:
                    # ---- 13. ordtabellene ----
                    for a, b in ((0.1, 0.2), (0.3, 0.5), (0.5, 0.9), (1.0, 1.3), (1.2, 1.7), (1.6, 2.1), (2.0, 2.5), (2.6, 3.4), (3.0, 4.2), (0.8, None)):
                        got = page.evaluate("([a, b]) => Spot.kroppshoyde({surf_height: a, surf_height_sets: b})", [a, b])
                        assert got == kroppshoyde(a, b), (a, b, got)
                    assert page.evaluate("() => Spot.kroppshoyde({surf_height: null})") in (None, "", "–")
                    assert page.evaluate("() => Spot.kroppshoyde({stars: 0, low_reason: 'stormsjo', surf_height: 0.9, surf_height_sets: 1.2, bw_height: 2.7})") is None, "S45 2: totalhøyden har ikke kroppsmål"
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
                # ---- Designrevisjonen 21.11.2026, fase 1 (privat/designrevisjon-2026-11-21/PLAN.md) ----
                page.evaluate("document.documentElement.style.fontSize = ''")
                HJEM_KLAR = "#viewHjem:not([hidden]) :is(#forside, .hjem-linje)"
                go("#utforsk", "#viewUtforsk:not([hidden])"); go("#hjem", HJEM_KLAR)
                # punkt 8: tilbakeknappen går ett steg tilbake i historikken (ikke et nytt steg oppå), og Hjem står der den sto
                hoyde = page.evaluate("document.documentElement.scrollHeight - innerHeight")
                assert hoyde >= 200, f"Hjem er for kort til å prøve rullingen ({label}): {hoyde}"
                y0 = min(300, hoyde)
                page.evaluate(f"window.scrollTo(0, {y0})"); page.wait_for_timeout(150)
                for hvordan in ("knappen", "nettleseren"):
                    for0 = page.evaluate("({ns: history.state && history.state.ns, len: history.length, y: scrollY})")
                    assert for0["y"] == y0 and isinstance(for0["ns"], int), f"Hjem før spoten ({label}): {for0}"
                    page.evaluate("Front.openSpot('unstad')"); page.wait_for_selector(SPOT_KLAR); page.wait_for_timeout(150)
                    paa = page.evaluate("({ns: history.state && history.state.ns, len: history.length, y: scrollY})")
                    assert paa["ns"] == for0["ns"] + 1 and paa["y"] == 0, f"spotsiden skal være et nytt steg og stå øverst ({label}): {paa}"
                    if hvordan == "nettleseren":
                        page.go_back()
                    elif mobile:
                        page.click("#spotBack")
                    else:
                        page.evaluate("Front.closeSpot()")
                    page.wait_for_selector(HJEM_KLAR); page.wait_for_timeout(200)
                    etter = page.evaluate("({ns: history.state && history.state.ns, len: history.length, y: scrollY, hash: location.hash})")
                    assert etter["ns"] == for0["ns"] and etter["len"] == paa["len"] and etter["hash"] == "#hjem", f"tilbake med {hvordan} skal gå ett steg tilbake, ikke lage et nytt ({label}): {for0} {paa} {etter}"
                    assert etter["y"] == y0, f"Hjem skal stå der den sto etter tilbake med {hvordan} ({label}): {etter}"
                if mobile:
                    # to trykk i samme øyeblikk på «Tilbake» (feiljegeren 24.11.2026, funn 4): bare ett steg tilbake, aldri ut av appen
                    for0 = page.evaluate("({ns: history.state && history.state.ns, y: scrollY})")
                    page.evaluate("Front.openSpot('unstad')"); page.wait_for_selector(SPOT_KLAR); page.wait_for_timeout(150)
                    page.dblclick("#spotBack"); page.wait_for_timeout(400)
                    assert "index.html" in page.url and page.url.endswith("#hjem"), f"to raske trykk på «Tilbake» gikk ut av appen: {page.url}"
                    page.wait_for_selector(HJEM_KLAR)
                    dbl = page.evaluate("({ns: history.state && history.state.ns, y: scrollY})")
                    assert dbl == for0, f"to raske trykk på «Tilbake» skal gå ett steg, til Hjem der den sto ({label}): {for0} {dbl}"
                    # sperra slipper igjen: neste gang virker knappen som vanlig
                    page.evaluate("Front.openSpot('unstad')"); page.wait_for_selector(SPOT_KLAR); page.wait_for_timeout(150)
                    page.click("#spotBack"); page.wait_for_selector(HJEM_KLAR); page.wait_for_timeout(200)
                    assert page.evaluate("({ns: history.state && history.state.ns, y: scrollY})") == for0, f"«Tilbake» skal virke igjen etter et dobbelttrykk ({label})"
                # «Hvorfor» (feiljegeren 24.11.2026, funn 2 og 3): en linje som starter med tallet får «Høyde på spoten» som etikett,
                # punktum som desimaltegn vises med komma, og klokkeslett og datoer står som de er
                hv_ = page.evaluate("""() => ({gap: breakdownDeler('0,1 m: svell ute 0,8 m gjennom gapet, andel 0,12. Anslag, ikke kystmodellens tall'),
                    loft: breakdownDeler('Løftet til 0,4 m: svell ute 1,8 m gjennom gapet, andel 0,22. Anslag, ikke kystmodellens tall'),
                    energi: breakdownDeler('Energi (svell) 243 kJ (periode omregnet til 7,6 s, ×1,25): teller 65 %'),
                    energiGml: breakdownDeler('Energi (svell) 243 kJ (periode omregnet til 7,6 s, ×1,25): faktor 0.65 (potensial ganget ned)'),
                    tide: ['Høyvann. Lokale sier lavt og middels vann er best her: −0,7 poeng.', 'Lavvann. Lokale sier høyt vann er best her: −0,35 poeng.', 'Middels vannstand. Lokale sier lavt vann er best her: −1 poeng.'].map(breakdownDeler),
                    tideLik: breakdownDeler('Tidevann (lav): foretrukket lokalt, ingen straff'), vind: breakdownDeler('Vind 5 m/s skrått pålands, kast 10 (teller som 6,5): −0,3'),
                    total: breakdownDeler('Totalt: 1 av 5 stjerner (3 uten vind og tidevann)'), vindord: STR.wind,
                    nullord: ['Høyvann. Lokale sier lavt og middels vann er best her: −0,7 poeng.', 'Tidevann (høy): ikke blant det lokale favoriserer - −1 stjerne (vektet −0,70)'].map(l =>
                        zeroCause({stars: 0, surf_height: 0.8, zero_losses: {energy: 0, wind: 0, tide: 0, local: 1, cap: 0}, local_rules: {lines: [l], stars_lost: 1}}).word), tideord: STR.wordTide,
                    komma: ['faktor 0.65', '−0.5 stjerne (vektet −0.3)', 'faktor 1.00', 'kl. 08.02', '17.11.2026', 'observasjonene 17.11 og 22.11', 'kl. 09.30-09.50Z', '5.10', '0,65'].map(breakdownKomma), hs: STR.cell.hs})""")
                assert hv_["hs"] == "Høyde på spoten" and hv_["gap"] == {"etikett": "Høyde på spoten", "verdi": "0,1 m", "virkning": "svell ute 0,8 m gjennom gapet, andel 0,12. Anslag, ikke kystmodellens tall"}, hv_["gap"]
                assert hv_["loft"]["etikett"] == "Løftet til" and hv_["loft"]["verdi"] == "0,4 m", hv_["loft"]
                # S42 (svar.md 24.11.2026 kl. 22.25): c) «teller 65 %» står som virkning, a) tidevannslinja «Høyvann. Lokale sier …: −0,7 poeng.»
                # får etiketten «Tidevann», vannstanden som verdi og resten som virkning (uten punktum til slutt), b) vindordene er
                # appens, og «skrått pålands» er eget ord, d) «(3 uten vind og tidevann)» står i totalen. Et eldre varsel med de gamle
                # ordene leses som før.
                assert hv_["energi"] == {"etikett": "Energi (svell)", "verdi": "243 kJ (periode omregnet til 7,6 s, ×1,25)", "virkning": "teller 65 %"}, hv_["energi"]
                assert hv_["energiGml"]["virkning"] == "faktor 0,65 (potensial ganget ned)" and hv_["energiGml"]["verdi"] == "243 kJ (periode omregnet til 7,6 s, ×1,25)", hv_["energiGml"]
                assert hv_["tide"] == [{"etikett": "Tidevann", "verdi": "Høyvann", "virkning": "Lokale sier lavt og middels vann er best her: −0,7 poeng"},
                                       {"etikett": "Tidevann", "verdi": "Lavvann", "virkning": "Lokale sier høyt vann er best her: −0,35 poeng"},
                                       {"etikett": "Tidevann", "verdi": "Middels vannstand", "virkning": "Lokale sier lavt vann er best her: −1 poeng"}], hv_["tide"]
                assert hv_["tideLik"] == {"etikett": "Tidevann", "verdi": "lav", "virkning": "foretrukket lokalt, ingen straff"}, hv_["tideLik"]
                assert hv_["vind"] == {"etikett": "Vind", "verdi": "5 m/s skrått pålands, kast 10 (teller som 6,5)", "virkning": "−0,3"}, hv_["vind"]
                # fysikk-kontrolløren 25.11.2026: ordet ved 0 poeng («tidevannsordet») leser den samme linja, ny og gammel form
                assert hv_["nullord"] == [hv_["tideord"], hv_["tideord"]] and hv_["tideord"], f"0 poeng tatt av den lokale tidevannsregelen skal få tidevannsordet: {hv_['nullord']}"
                assert hv_["total"]["etikett"] == "Totalt" and hv_["total"]["verdi"] == "1 av 5 poeng (3 uten vind og tidevann)", hv_["total"]
                assert hv_["vindord"] == {"offshore": "fralands", "side": "sidevind", "sideonshore": "skrått pålands", "onshore": "pålands"} and hv_["vindord"] == rating.WIND_TYPE_WORD, hv_["vindord"]
                assert hv_["komma"] == ["faktor 0,65", "−0,5 stjerne (vektet −0,3)", "faktor 1,00", "kl. 08.02", "17.11.2026", "observasjonene 17.11 og 22.11", "kl. 09.30-09.50Z", "5.10", "0,65"], hv_["komma"]
                # S37 a, b og c (svar.md 24.11.2026 kl. 10.25): når høyden er andelshøyden (share_height eller gap_floor), står «–» i stedet
                # for prosenttallet under Sikkerhet, «Slik regnes det ut» for høyden er teksten fra svaret, og «Eksponering denne timen»
                # viser andelen fra regnestykket. Timer uten feltene (alle kyst-spots) er uendret.
                s37 = page.evaluate("""() => { const kyst = {confidence: 99, confidence_source: 'målt', height: 0.39, swell_offshore: 1.76, height_source: 'barentswatch', directness: 0.167, transfer: 0.22, day: 3, zone: 'barentswatch', stars: 1, breakdown: ['Totalt: 1 av 5 stjerner']};
                    const andel = {...kyst, share_height: true, breakdown: ['Løftet til 0,4 m: svell ute 1,8 m gjennom gapet, andel 0,21. Anslag, ikke kystmodellens tall']}, uten = {...andel, breakdown: []}, gulv = {...kyst, gap_floor: true, breakdown: andel.breakdown};
                    const les = (h) => ({sikkerhet: EXPLAIN.confidence.numbers(h)[0], hs: EXPLAIN.hs.how(h), eksp: EXPLAIN.exposure.numbers(h)[0], transfer: EXPLAIN.exposure.numbers(h)[1], celle: sikkerhetProsent(h, '–'), andel: andelBrukt(h)});
                    const alle = Object.values(EXPLAIN).flatMap(e => e.numbers ? e.numbers(andel, {}).filter(r => r[0] === 'Sikkerhet').map(r => r[1]) : []);
                    return {kyst: les(kyst), andel: les(andel), uten: les(uten), gulv: les(gulv), tom: les({...andel, breakdown: [], height: null}), mangler: les({...kyst, confidence: null}), alle, gapHow: STR.gapHow}; }""")
                assert s37["gapHow"] == "Svell ute × andelen som kommer gjennom gapet. Anslag, ikke kystmodellens tall.", s37["gapHow"]
                for navn_ in ("andel", "gulv"):
                    x_ = s37[navn_]
                    assert x_["sikkerhet"] == ["Sikkerhet", "–"] and x_["celle"] == "–" and x_["hs"] == [s37["gapHow"]], f"S37 a og b ({navn_}): {x_}"
                    assert x_["eksp"] == ["Eksponering denne timen", "0,21 · andel gjennom gapet"] and x_["andel"] == "0,21", f"S37 c ({navn_}): andelen skal være tallet i regnestykket: {x_}"
                assert s37["alle"] and set(s37["alle"]) == {"–"}, f"S37 a: ingen forklaring skal vise prosenttallet for en andelstime: {s37['alle']}"
                assert s37["uten"]["andel"] == "0,22" and s37["uten"]["eksp"][1] == "0,22 · andel gjennom gapet", f"S37 c uten linja i regnestykket: høyden delt på svellet ute: {s37['uten']}"
                assert s37["tom"]["andel"] is None and s37["tom"]["eksp"][1] == "mangler", f"S37 c: andel som ikke finnes, vises som «mangler», aldri 0: {s37['tom']}"
                k_ = s37["kyst"]
                assert k_["sikkerhet"] == ["Sikkerhet", "99 %"] and k_["celle"] == "99 %" and k_["eksp"] == ["Eksponering denne timen", "17 %"] and k_["andel"] is None, f"timer uten andelshøyde skal være uendret: {k_}"
                assert len(k_["hs"]) == 2 and k_["hs"][0].startswith("BarentsWatch sin totalhøyde ved punktet") and k_["transfer"] == s37["andel"]["transfer"] == ["Transfer (direkte treff)", "22 %"], k_
                assert s37["mangler"]["sikkerhet"] == ["Sikkerhet", "mangler"] and s37["mangler"]["celle"] == "–", s37["mangler"]
                # en fane (nytt steg fram) går til toppen som før
                go("#logger", "#viewSide:not([hidden])"); go("#hjem", HJEM_KLAR)
                assert page.evaluate("scrollY") == 0, f"Hjem skal stå øverst når man går dit med fanen ({label})"
                # lenke rett til spoten (forrige steg er ikke Hjem): knappen bytter ut steget i stedet for å gå ut av appen
                page.goto(f"http://127.0.0.1:{port}/index.html?lenke=1#spot=unstad"); page.wait_for_selector(SPOT_KLAR)
                len0 = page.evaluate("history.length")
                page.evaluate("Front.closeSpot()"); page.wait_for_selector(HJEM_KLAR)
                bytt = page.evaluate("({len: history.length, hash: location.hash, view: document.body.dataset.view})")
                assert bytt == {"len": len0, "hash": "#hjem", "view": "hjem"}, f"tilbake fra en spot som ble åpnet med lenke ({label}): {bytt}"
                # punkt 1, 2, 6, 9, 10 og 11 på spotsiden
                page.emulate_media(color_scheme="dark"); go("#spot=unstad", SPOT_KLAR)
                page.wait_for_function("[...document.querySelectorAll('#viewSpot .sp-foto')].some(b => getComputedStyle(b).display !== 'none' && b.naturalWidth > 0)")
                f1 = page.evaluate("""() => { const q = (x) => document.querySelector('#viewSpot ' + x), cs = (e) => getComputedStyle(e), r = (e) => e.getBoundingClientRect();
                    const k = q('.kredit.linje'), a = k.querySelector('a'), hode = q('.sp-hode, .spw-hode'), hv = q('#hvorfor'); hv.open = true;
                    const rader = [...hv.querySelectorAll('.hv-tab > div')].map(d => [...d.children].map(c => c.textContent.trim()));
                    const ut = {kredit: k.textContent.trim(), kredH: r(k).height,
                        lenkeH: r(a).height, lenkeB: r(a).width, href: a.getAttribute('href'), hodeH: r(hode).height, kant: cs(hode).boxShadow, hele: (q('.kilder.foto') || document.querySelector('#bunn')).textContent,
                        tallBunn: r(q('.dom .t-tall')).bottom + scrollY, ordBunn: r(q('.dom-ord b')).bottom + scrollY, hero: parseFloat(cs(q('.t-hero')).fontSize), etikett: parseFloat(cs(q('.etikett')).fontSize),
                        fakta: cs(q('.fakta-linje')).color, ink: cs(document.body).color, rader, hvTekst: hv.textContent, uke2: (q('.uke2 .etikett') || {}).textContent || null, uke2Kant: q('.uke2 .rute') ? cs(q('.uke2 .rute')).borderTopStyle : null,
                        komma: [...document.querySelectorAll('#viewSpot .t-svell .des')].map(e => e.textContent)};
                    hv.open = false; return ut; }""")
                assert f1["kredit"] == "Sentinel-2 · Copernicus/Kartverket · CC BY 4.0" and f1["kredH"] <= 46, f"under toppbildet skal det stå én linje (44 px høy, to linjer ville gitt 88) ({label}): {f1['kredit']!r}, {f1['kredH']} px"
                assert f1["lenkeH"] >= 44 and f1["lenkeB"] >= 44 and f1["href"].startswith("https://creativecommons.org/licenses/by/4.0"), f"lisenslenka skal ha 44 px trykkflate ({label}): {f1['lenkeH']} x {f1['lenkeB']}"
                assert "Laget av Sentinel-2" in f1["hele"] and "CESBIO og CNES" in f1["hele"] and "Farger og korn: Nordsurf" in f1["hele"], f"hele krediteringen skal stå under Kilder nederst ({label})"
                assert round(f1["hodeH"]) == (160 if mobile else 260) and f1["hero"] == (60 if mobile else 96), f"toppbildet og navnet ({label}): {f1['hodeH']}, {f1['hero']}"
                assert f1["kant"] != "none" and "0px 0px 0px 1px" in f1["kant"], f"bildet skal ha kant i mørketid ({label}): {f1['kant']}"
                # dommen (tall og ord) står i første skjermbilde på 390 x 663 og 1200 x 660 (mobil: over fanelinja på 64 px)
                grense = 663 - 64 if mobile else 660
                assert f1["tallBunn"] <= grense and f1["ordBunn"] <= grense, f"dommen skal synes uten rulling ({label}): tall {f1['tallBunn']}, ord {f1['ordBunn']}, grense {grense}"
                assert f1["etikett"] == 12 and f1["fakta"] == f1["ink"], f"etiketter 12 px og faktalinja i blekk ({label}): {f1['etikett']}, {f1['fakta']}"
                assert f1["komma"] == [","], f"desimalkommaet i det store svelltallet skal stå i .des ({label}): {f1['komma']}"
                # «Hvorfor»: tabell med etikett, verdi og virkning hver for seg, og «poeng» i stedet for «stjerner»
                assert len(f1["rader"]) >= 5 and all(r_[0] and len(r_) in (2, 3) for r_ in f1["rader"] if len(r_) > 1), f"«Hvorfor» skal være en tabell ({label}): {f1['rader']}"
                assert "stjerne" not in f1["hvTekst"].lower() and re.fullmatch(r"\d av 5 poeng.*", f1["rader"][-1][1]) and f1["rader"][-1][0] == "Totalt", f"«Hvorfor» skal si poeng ({label}): {f1['rader'][-1]}"
                per = next((r_ for r_ in f1["rader"] if r_[0] == "Periode"), None)
                assert per and len(per) == 3 and re.fullmatch(r"\d+ s \(ute\)", per[1]) and per[2], f"verdi og virkning skal stå i hver sin celle ({label}): {per}"
                if not mobile:
                    assert f1["uke2"] == "Uke 2 · usikker" and f1["uke2Kant"] == "dashed", f"dag 8 og utover skal ha etikett og stiplet ramme ({label}): {f1['uke2']}, {f1['uke2Kant']}"
                page.emulate_media(color_scheme="light"); page.wait_for_timeout(100)
                assert page.evaluate("getComputedStyle(document.querySelector('#viewSpot :is(.sp-hode, .spw-hode)')).boxShadow") in ("none", "rgba(0, 0, 0, 0) 0px 0px 0px 1px"), f"ingen kant rundt bildet om dagen ({label})"
                # punkt 3, 4 og 5: ringen rundt «Best» bare fra 4 (i korall), nullene roligere, 1 og 2 med eget fyll
                if not mobile:
                    go("#hjem", HJEM_KLAR)
                    def helt(stjerner):
                        # alle dagene: Unstad får n poeng i en lys time med åpent vindu, de andre spotene får 0 - da er Unstad hovedbildet
                        page.evaluate("""(n) => { const sp = DATA.spots.find(x => x.id === 'unstad'), mal = sp.dager.find(x => x.h).h;
                            sp.dager.forEach(d => { d.status = 'ok'; d.h = {...(d.h || mal), t: d.d + 'T10:00Z', stars: n, faded: 0, light: 'dag', low_reason: null}; d.start = d.h.t; d.slutt = d.d + 'T12:00Z'; });
                            DATA.spots.forEach(x => { if(x !== sp) x.dager.forEach(d => { if(d.h) d.h.stars = 0; }); });
                            Front.state.fsDag = 1; Front.state.fsRegion = ''; Front.refresh(); }""", stjerner)
                        page.wait_for_selector("#forside .fs-helt")
                        return page.evaluate("""() => { const h = document.querySelector('#forside .fs-helt'), b = h.querySelector('.fs-best'), p = h.querySelector('.fs-ring path');
                            return {cls: h.className, navn: h.querySelector('.fs-navn').textContent, best: b && b.textContent.trim(), ring: !!p, farge: p && getComputedStyle(p).stroke,
                                signal: getComputedStyle(document.documentElement).getPropertyValue('--signal').trim(), kredit: document.querySelector('#forside .fs-helt + .kredit').textContent.trim()}; }""")
                    h3 = helt(3)
                    assert h3["navn"] == "Unstad" and " r-3" in h3["cls"] and h3["best"] and not h3["ring"], f"ingen ring rundt «Best» under 4 poeng: {h3}"
                    assert h3["kredit"] == "Sentinel-2 · Copernicus/Kartverket · CC BY 4.0", h3["kredit"]
                    h4 = helt(4)
                    assert " r-4" in h4["cls"] and h4["ring"] and h4["farge"] == "rgb(192, 81, 81)" and h4["signal"].upper() == "#C05151", f"ringen rundt «Best» fra 4 poeng skal være korall: {h4}"
                    nul = page.evaluate("""() => { const c = [...document.querySelectorAll('#forside .fs-matrise td.r-0 .mx')][0], t = [...document.querySelectorAll('#forside .fs-matrise td .mx.tre, #forside .fs-matrise td .mx.hoy')][0];
                        const i1 = document.querySelector('#forside .fs-tegn i.r-1'), cs = getComputedStyle;
                        return {vekt0: c && cs(c).fontWeight, farge0: c && cs(c).color, tekst0: c && c.textContent, vektAndre: t && cs(t).fontWeight, lav: cs(i1).backgroundColor, muted: cs(document.querySelector('#forside .fs-dato')).color}; }""")
                    assert nul["tekst0"] == "0" and nul["vekt0"] == "500" and nul["farge0"] == nul["muted"] and nul["vektAndre"] == "800", f"nullene i matrisa: dempet, vekt 500 og fortsatt tallet 0: {nul}"
                    assert nul["lav"] == "rgb(138, 132, 120)", f"fyllet for 1 og 2 om dagen skal være #8A8478: {nul['lav']}"
                else:
                    go("#hjem", HJEM_KLAR)
                    uk = page.evaluate("""() => { const n = document.querySelector('#viewHjem .uke i.r-0'), cs = getComputedStyle; return n && {vekt: cs(n).fontWeight, tekst: n.textContent, kant: cs(n).boxShadow, farge: cs(n).color, muted: cs(document.querySelector('#viewHjem .kilder')).color}; }""")
                    assert uk and uk["tekst"] == "0" and uk["vekt"] == "500" and uk["farge"] == uk["muted"] and "216, 210, 198" in uk["kant"], f"nullene i ukerutene: dempet, vekt 500, tynn ramme og fortsatt tallet 0: {uk}"
                # ---- Designrevisjonen 21.11.2026, fase 2: B 4.0 ferdig på mobil (privat/designrevisjon-2026-11-21/PLAN.md) ----
                page.emulate_media(color_scheme="light"); page.evaluate("document.documentElement.removeAttribute('data-theme')")
                page.mouse.move(0, 0)
                go("#utforsk", "#viewUtforsk:not([hidden])"); go("#hjem", HJEM_KLAR)
                INK, PAPIR = "rgb(0, 41, 65)", "rgb(242, 239, 232)"
                # Runde 3 (24.11.2026): merket «Foreløpig» står i metalinja i alle radene - regionradene og favorittene på mobil-Hjem,
                # søketreffene, og på nettsiden forsidetabellen og lista på Utforsk. Feltene leses fra spots.json (status
                # «forelopig» for Bøvær og Breivikeidet, andel_forelopig for Russelv og Lenangsøyra). Testfilas varsel er eldre enn de
                # to første, så de legges inn i siden som kopier av Grøtfjord. Unstad er kalibrert og skal ikke ha merket.
                SJ = {x["id"]: x for x in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
                MERKET = ["bovaer", "breivikeidet", "russelv", "lenangsoyra"]
                assert all(SJ[i].get("status") == "forelopig" for i in MERKET[:2]) and all(SJ[i].get("andel_forelopig") for i in MERKET[2:]), "spots.json: de fire spotene skal være merket foreløpig"
                assert SJ["unstad"].get("status") != "forelopig" and not SJ["unstad"].get("andel_forelopig"), "spots.json: Unstad er kalibrert"
                page.evaluate("""(sj) => { const mal = DATA.spots.find(s => s.id === 'grotfjord'); window.__r3 = {lagt: [], auth: window.Auth, region: Front.helpers.chosenRegion()};
                    for(const x of sj){ let s = DATA.spots.find(y => y.id === x.id);
                        if(!s){ s = {...mal, id: x.id, name: x.name, area: x.area, region: 'Troms', spot: mal.spot}; DATA.spots.push(s); window.__r3.lagt.push(x.id); }
                        if(x.status === 'forelopig'){ s.status = 'forelopig'; s.forelopig_fra = '2026-11-01T00:00:00Z'; } if(x.andel_forelopig) s.andel_forelopig = true; }
                    window.Auth = {state: {ready: true, user: {id: 't', email: 't@eksempel.no'}, profile: null, favorites: new Set([...sj.map(x => x.id), 'unstad'])}, toggleFavorite: async () => {}, signOut: async () => {}};
                    Front.helpers.setRegion('Troms'); Front.state.visAlle.Troms = true; Front.state.fsRegion = ''; Front.state.fsAlle = true; Front.refresh(); }""",
                    [{"id": i, "name": SJ[i]["name"], "area": SJ[i].get("area"), "status": SJ[i].get("status"), "andel_forelopig": SJ[i].get("andel_forelopig")} for i in MERKET])
                page.wait_for_timeout(200)
                LES_MERKE = """(q) => Object.fromEntries([...document.querySelectorAll(q.rad)].map(r => { const a = r.matches('a') ? r : r.querySelector('a'), id = (a.getAttribute('href').match(/#spot=([^&]+)/) || [])[1], e = r.querySelector(q.meta);
                    return [decodeURIComponent(id), e ? e.textContent.replace(/\\s+/g, ' ').trim() : null]; }))"""
                def merke_sjekk(hvor, rad, meta):
                    m_ = page.evaluate(LES_MERKE, {"rad": rad, "meta": meta})
                    # Unstad kan stå i hovedbildet på forsiden i stedet for i tabellen: da er Grøtfjord den kalibrerte spoten som sjekkes
                    uten = "unstad" if "unstad" in m_ else "grotfjord"
                    assert set(MERKET) | {uten} <= set(m_), f"{hvor} ({label}): radene mangler: {sorted((set(MERKET) | {uten}) - set(m_))}"
                    for i_ in MERKET:
                        assert m_[i_].split(" · ").count("Foreløpig") == 1, f"{hvor} ({label}): «Foreløpig» skal stå én gang i metalinja for {i_}: {m_[i_]!r}"
                    assert "Foreløpig" not in m_[uten], f"{hvor} ({label}): {uten} er kalibrert og skal ikke ha merket: {m_[uten]!r}"
                    return m_
                if mobile:
                    merke_sjekk("favorittradene", "#viewHjem .favliste:not(.regionliste) a.favlinje", ".etikett")
                    page.evaluate("() => { Auth.state.favorites.delete('unstad'); DATA.spots.find(s => s.id === 'unstad').__region = DATA.spots.find(s => s.id === 'unstad').region; DATA.spots.find(s => s.id === 'unstad').region = 'Troms'; Front.refresh(); }"); page.wait_for_timeout(150)
                    mr = merke_sjekk("regionradene", "#viewHjem .regionliste a.favlinje", ".etikett")
                    page.evaluate("() => { const u = DATA.spots.find(s => s.id === 'unstad'); u.region = u.__region; delete u.__region; }")
                    # metalinja: leddene står med « · » mellom seg som før, og ingen ledd er brutt midt i (bare mellom leddene)
                    ledd = page.evaluate("""() => [...document.querySelectorAll('#viewHjem .favlinje .etikett')].map(e => { const lh = parseFloat(getComputedStyle(e).lineHeight), d = [...e.querySelectorAll('.ledd')];
                        return {tekst: e.textContent.trim(), ledd: d.map(x => x.textContent.trim().replace(/^· /, '')), forst: d.filter((x, i) => i === 0 && x.querySelector('.sk')).length, sk: d.slice(1).filter(x => !x.querySelector('.sk')).length, hoye: d.filter(x => x.getBoundingClientRect().height > lh * 1.5).length, utenfor: d.filter(x => x.getBoundingClientRect().right > innerWidth - 15).length}; })""")
                    assert ledd and all(l_["ledd"] and l_["tekst"] == " · ".join(l_["ledd"]) and l_["hoye"] == 0 and l_["utenfor"] == 0 for l_ in ledd), f"metalinja skal bare brytes mellom leddene: {[l_ for l_ in ledd if l_['hoye'] or l_['utenfor'] or l_['tekst'] != ' · '.join(l_['ledd'])][:2]}"
                    # feiljegeren 25.11.2026, funn 6: skilletegnet hører til leddet etter (aldri hengende sist på linja): det står i
                    # luften til venstre for leddet, og et ledd som står først på en linje har det utenfor .etikett (klippet bort)
                    assert all(l_["forst"] == 0 and l_["sk"] == 0 for l_ in ledd), "hvert ledd utenom det første skal ha skilletegnet sitt foran seg"
                    heng = page.evaluate("""() => { let brutt = 0, synlig = 0, etter = 0; for(const e of document.querySelectorAll('#viewHjem .favlinje .etikett:not(.obs)')){ const eb = e.getBoundingClientRect(), d = [...e.querySelectorAll('.ledd')];
                        if(d.length && getComputedStyle(e).overflow !== 'hidden') synlig += 100;
                        d.forEach((x, i) => { if(!i) return; const sk = x.querySelector('.sk').getBoundingClientRect(), forrige = d[i - 1].getBoundingClientRect(), ny = x.getBoundingClientRect().top > forrige.top + 2;
                            if(ny){ brutt++; if(sk.right > eb.left + 0.5) synlig++; } else if(sk.left < forrige.right - 0.5 || sk.right > eb.right) etter++; }); }
                        return {brutt, synlig, etter}; }""")
                    assert heng["synlig"] == 0 and heng["etter"] == 0, f"skilletegnet skal være klippet bort der linja brytes, og stå mellom leddene ellers: {heng}"
                    assert heng["brutt"] >= 1, f"testdataene skal ha minst én metalinje over to linjer: {heng}"
                    assert mr["lenangsoyra"].startswith("Lyngen · Foreløpig · ca. 1 t 20 min · "), f"Lenangsøyra: sted, merke og kjøretid i metalinja: {mr['lenangsoyra']!r}"
                    go("#sok", "#viewSok:not([hidden]) #sokM")
                    merke_sjekk("søket", "#viewSok .srad", ".nm small")
                    go("#hjem", HJEM_KLAR)
                else:
                    page.wait_for_selector("#forside table.fs-tabell tr.s")
                    merke_sjekk("forsidetabellen", "#forside table.fs-tabell tr.s", ".fs-nm .etikett")
                    page.evaluate("() => { Front.state.utforskView = null; Front.state.utforskViewSatt = true; Front.state.listeAlle = true; }")
                    go("#utforsk", "#viewUtforsk:not([hidden]) #utforskListe .srad")
                    merke_sjekk("lista på Utforsk", "#utforskListe .srad", ".nm small")
                    go("#hjem", HJEM_KLAR)
                page.evaluate("""() => { const r = window.__r3; DATA.spots = DATA.spots.filter(s => !r.lagt.includes(s.id)); for(const s of DATA.spots){ if(['russelv', 'lenangsoyra'].includes(s.id)) delete s.andel_forelopig; }
                    window.Auth = r.auth; Front.helpers.setRegion(r.region); delete Front.state.visAlle.Troms; Front.state.fsRegion = null; Front.state.fsAlle = false; Front.state.listeAlle = false; delete window.__r3; Front.refresh(); }""")
                page.wait_for_timeout(200)
                print(f"fase 2 runde 3 ({label}): «Foreløpig» i metalinja for Bøvær, Breivikeidet, Russelv og Lenangsøyra, ikke for Unstad - OK")
                # punkt 2 (kildefilene): duplikatene er slettet, ikke overstyrt, og alle radier er var(--radius) - unntatt de runde
                # kartmerkene, skiva og prikkene i forklaringen til eksponeringsfiguren
                app_css, ui_css = (DOCS / "css" / "app.css").read_text(encoding="utf-8"), (DOCS / "css" / "ui.css").read_text(encoding="utf-8")
                for forbudt in ("\n.primary{", "\n.ghost{", "\n.btn{", "\n.chips button{", "\n:focus-visible{", "\n.back{", "\nnav.tabs{"):
                    assert forbudt not in "\n" + app_css, f"app.css har fortsatt duplikatet {forbudt.strip()!r}"
                assert ui_css.count(".primary,.ghost{all:unset") == 1 and "\n.primary{" not in ui_css and "\n.ghost{" not in ui_css, "ui.css: .primary og .ghost skal bare være navn på .knapp1 og .knapp2"
                import re as _re
                radier = {}
                for navn_, css_ in (("app.css", app_css), ("ui.css", ui_css)):
                    for m_ in _re.finditer(r"([^{}]+)\{[^{}]*?border-radius:([^;}]+)", css_):
                        if m_.group(2).strip() != "var(--radius)":
                            radier[f"{navn_} {m_.group(1).strip().splitlines()[-1][-40:]}"] = m_.group(2).strip()
                assert set(radier.values()) <= {"50%"} and len(radier) <= 7, f"radier som ikke er var(--radius): {radier}"
                assert all(any(k in sel for k in (".mk-dot", ".klynge", ".skive", ".help-btn", ".expo-legend")) for sel in radier), f"runde hjørner utenom kartmerkene, skiva og figurprikkene: {radier}"
                assert ui_css.count(":root :focus-visible{outline:2px solid var(--focus);outline-offset:2px}") == 1, "fokusringen skal stå ett sted i ui.css"
                icon = (DOCS / "icon.svg").read_text(encoding="utf-8")
                assert "#F2EFE8" in icon and "#002941" in icon and "#F6F1E8" not in icon and "#1E1B16" not in icon, "icon.svg skal bruke tokenene (#F2EFE8 og #002941)"
                # punkt 5: fire faner med etikett, søk har egen aktiv tilstand
                FOKUS_JS = """(q) => { const e = [...document.querySelectorAll(q)].find(x => x.getClientRects().length && !x.closest('[hidden]')); if(!e) return null; e.focus({preventScroll: true});
                    const c = getComputedStyle(e); return document.activeElement === e ? `${c.outlineStyle} ${c.outlineWidth} ${c.outlineColor}` : 'fikk ikke fokus'; }"""
                def ring(sel_liste, hvor):
                    page.keyboard.press("Tab")   # tastatur sist brukt: fokus satt fra skript regnes da som synlig fokus
                    for q in sel_liste:
                        r_ = page.evaluate(FOKUS_JS, q)
                        assert r_ == f"solid 2px {INK}", f"fokusringen skal være 2 px blekk på {q} ({hvor}, {label}): {r_}"
                if mobile:
                    faner = page.evaluate("[...document.querySelectorAll('.tabbar .tabs a')].map(a => ({nav: a.dataset.nav, txt: a.textContent.trim(), cur: a.getAttribute('aria-current'), w: a.getBoundingClientRect().width, h: a.getBoundingClientRect().height}))")
                    assert [f_["nav"] for f_ in faner] == ["hjem", "utforsk", "logger", "sok"] and [f_["txt"] for f_ in faner] == ["Hjem", "Utforsk", "Logger", "Søk"], f"fanelinja: {faner}"
                    assert all(f_["w"] >= 44 and f_["h"] >= 44 for f_ in faner) and [f_["cur"] for f_ in faner] == ["page", None, None, None], f"fanelinja: {faner}"
                    # punkt 1 og 6: topplinja har ordmerket (20-22 px høyt) og «Fra Tromsø» som går til Innstillinger
                    topp = page.evaluate("""() => { const wm = document.querySelector('#viewHjem .hjem-linje .wm svg'), f = document.querySelector('#hjemFra'), b = f.getBoundingClientRect();
                        return {wm: wm && wm.getBoundingClientRect().height, navn: wm && wm.getAttribute('aria-label'), fra: f.textContent.trim(), href: f.getAttribute('href'), aria: f.getAttribute('aria-label'), w: b.width, h: b.height,
                                kort: document.querySelectorAll('#viewHjem .kort, #viewHjem .rad, #viewHjem .chip').length,
                                runde: [...document.querySelectorAll('#viewHjem *')].filter(e => e.getClientRects().length && getComputedStyle(e).borderTopLeftRadius !== '0px').length,
                                skygger: [...document.querySelectorAll('#viewHjem .favlinje, #viewHjem .favliste')].filter(e => getComputedStyle(e).boxShadow !== 'none').length,
                                venstre: [...new Set([...document.querySelectorAll('#viewHjem .hjem-linje, #viewHjem .hjem-overskrift, #viewHjem .sek, #viewHjem .favlinje, #viewHjem .regionvelger, #viewHjem .kilder')].map(e => Math.round(e.getBoundingClientRect().left)))]}; }""")
                    assert topp["wm"] and 20 <= topp["wm"] <= 22 and topp["navn"] == "Nordsurf", f"ordmerket i topplinja skal være 20-22 px høyt: {topp}"
                    assert topp["fra"] == f"Fra {FRA_NAVN}" and topp["href"] == "#innstillinger" and "Innstillinger" in topp["aria"] and topp["fra"] in topp["aria"] and topp["w"] >= 44 and topp["h"] >= 44, f"«Fra {FRA_NAVN}» skal åpne Innstillinger: {topp}"
                    assert topp["kort"] == 0 and topp["runde"] == 0 and topp["skygger"] == 0 and topp["venstre"] == [16], f"mobil-Hjem: ingen kort, ingen radius, ingen skygge og felles venstrekant 16 px: {topp}"
                    # favorittene står etter dagens tall, så kjøretid (spots uten kjøretid sist), så navnet
                    page.evaluate("() => { window.__auth2 = window.Auth; window.Auth = {state: {ready: true, user: {id: 't', email: 't@eksempel.no'}, profile: null, favorites: new Set(DATA.spots.map(s => s.id))}, toggleFavorite: async () => {}, signOut: async () => {}}; Front.refresh(); }")
                    page.wait_for_selector("#viewHjem .favliste:not(.regionliste) a.favlinje")
                    fv = page.evaluate("""() => { const H = Front.helpers, key = Front.state.hjemDag; return [...document.querySelectorAll('#viewHjem .favliste:not(.regionliste) a.favlinje')].map(r => { const s = DATA.spots.find(s => r.getAttribute('href') === '#spot=' + s.id), b = H.dayBest(s, key);
                        return [b.st == null ? -1 : b.st, (window.KJORETID && KJORETID.min[s.id]) || 1e9, s.name, !!r.querySelector('.setn'), getComputedStyle(r.querySelector('.t-listetall')).fontSize, getComputedStyle(r.querySelector('.t-navn')).textTransform]; }); }""")
                    srt = page.evaluate(SORT_JS, "#viewHjem .favliste:not(.regionliste) a.favlinje")
                    assert len(fv) == len(OV) and srt["er"] == srt["skal"], f"favorittene skal stå etter dagens tall, så kjøretid, så navn: {srt}"
                    assert srt["kjAvgjor"] and srt["navnAvgjor"], f"testdataene skal prøve både kjøretid og navn som nøkkel: {srt}"
                    assert all(px == "44px" and tt == "uppercase" for *_, px, tt in fv), f"favorittraden: tallet 44 px og navnet i versaler: {fv[:2]}"
                    # punkt 5 med tastatur: Tab fra toppen når «Fra Tromsø», Enter åpner Innstillinger, og kontoen (innloggingen) nås med Tab
                    # start fra «Hopp til innholdet», det første som kan få fokus på siden (søket over har flyttet startpunktet for Tab)
                    page.evaluate("() => { window.scrollTo(0, 0); document.querySelector('a.skip').focus(); }")
                    for _i in range(3):
                        page.keyboard.press("Tab")
                        if page.evaluate("document.activeElement && document.activeElement.id") == "hjemFra": break
                    assert page.evaluate("document.activeElement.id") == "hjemFra", "«Fra Tromsø» nås ikke med Tab fra toppen av Hjem"
                    assert page.evaluate("(() => { const c = getComputedStyle(document.activeElement); return `${c.outlineStyle} ${c.outlineWidth} ${c.outlineColor}`; })()") == f"solid 2px {INK}", "fokusringen på «Fra Tromsø»"
                    ring([".tabs a", "#favRediger", ".regionvelger button", "#viewHjem a.favlinje"], "Hjem")
                    page.focus("#hjemFra"); page.keyboard.press("Enter"); page.wait_for_selector("#viewSide:not([hidden]) #omrade")
                    page.evaluate("() => { window.Auth = {state: {ready: true, user: null, profile: null, favorites: new Set()}, toggleFavorite: async () => {}}; Front.refresh(); }"); page.wait_for_selector("#authEmail")
                    page.evaluate("document.activeElement && document.activeElement.blur()")
                    sett_ = []
                    for _i in range(8):
                        page.keyboard.press("Tab"); sett_.append(page.evaluate("document.activeElement && (document.activeElement.id || document.activeElement.className)"))
                    assert "authEmail" in sett_ and "authSend" in sett_ and "omrade" in sett_, f"innloggingen og området skal nås med Tab i Innstillinger: {sett_}"
                    inn = page.evaluate("""() => { const cs = getComputedStyle, p = document.querySelector('#authSend'), g = document.querySelector('#export'), i = document.querySelector('#authEmail').getBoundingClientRect();
                        return {sek: document.querySelectorAll('#detailPane .sek').length, sec: document.querySelectorAll('#detailPane .sec').length, pBg: cs(p).backgroundColor, pTekst: cs(p).color, pFont: cs(p).fontFamily, pR: cs(p).borderTopLeftRadius, pH: p.getBoundingClientRect().height,
                                gBg: cs(g).backgroundColor, gKant: cs(g).boxShadow, gR: cs(g).borderTopLeftRadius, gH: g.getBoundingClientRect().height, epost: [Math.round(i.width), Math.round(i.height)], venstre: Math.round(document.querySelector('#detailPane .sek').getBoundingClientRect().left)}; }""")
                    assert inn["sek"] >= 5 and inn["sec"] == 0 and inn["venstre"] == 16, f"Innstillinger skal ha seksjonsstreken og venstrekant 16 px: {inn}"
                    assert inn["pBg"] == INK and inn["pTekst"] == PAPIR and "Martian" in inn["pFont"] and inn["pR"] == "0px" and inn["pH"] >= 44, f"primærknappen (.primary) skal ha formen til .knapp1: {inn}"
                    assert inn["gBg"] == "rgba(0, 0, 0, 0)" and "2px inset" in inn["gKant"] and INK in inn["gKant"] and inn["gR"] == "0px" and inn["gH"] >= 44, f"sekundærknappen (.ghost) skal ha formen til .knapp2: {inn}"
                    assert inn["epost"][0] >= 300 and inn["epost"][1] >= 44, f"e-postfeltet skal fylle bredden og være 44 px høyt: {inn['epost']}"
                    FELT_JS = """() => Object.fromEntries([...document.querySelectorAll('#detailPane select, #detailPane input')].map(e => { const b = e.getBoundingClientRect(), c = getComputedStyle(e);
                        return [e.id, {w: Math.round(b.width), h: Math.round(b.height), strek: c.boxShadow.includes('inset') && c.boxShadow.includes('-2px'), form: c.appearance || c.webkitAppearance, radius: c.borderTopLeftRadius}]; }))"""
                    felt = page.evaluate(FELT_JS)
                    assert set(felt) >= {"authEmail", "omrade", "syncRepo", "syncToken"} and all(v["w"] >= 300 and v["h"] >= 44 and v["strek"] and v["radius"] == "0px" for v in felt.values()), f"feltene i Innstillinger skal ha samme form (hele bredden, 44 px, 2 px strek under): {felt}"
                    assert felt["omrade"]["form"] == "none" and felt["omrade"]["h"] == felt["authEmail"]["h"], f"områdevelgeren skal tegnes av appen (ellers 23 px i Safari) og være like høy som e-postfeltet: {felt['omrade']}"
                    audit("fase2-innstillinger")
                    page.evaluate("() => { window.Auth = window.__auth2; delete window.__auth2; Front.refresh(); }")
                    # punkt 3: Søk og Logger har seksjonsstreken og samme listerad. Tom tilstand i Logger: én linje per seksjon
                    go("#sok", "#viewSok:not([hidden]) #sokM")
                    assert page.evaluate("[...document.querySelectorAll('.tabbar [aria-current]')].map(a => a.dataset.nav)") == ["sok"], "søk skal ha egen aktiv tilstand i fanelinja"
                    sok = page.evaluate("""() => { const cs = getComputedStyle, r = document.querySelector('#viewSok .srad'), f = document.querySelector('#viewSok .sok-field');
                        return {sek: [...document.querySelectorAll('#viewSok .sek h2')].map(h => h.textContent), navn: cs(r.querySelector('.nm b')).fontFamily, versaler: cs(r.querySelector('.nm b')).textTransform, radH: r.getBoundingClientRect().height,
                                felt: cs(f).borderTopLeftRadius, minste: Math.min(...[...document.querySelectorAll('#viewSok *')].filter(e => e.getClientRects().length && e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(cs(e).fontSize)))}; }""")
                    assert sok["sek"][-2:] == ["Områder", "Alle spots"] and "Martian" in sok["navn"] and sok["versaler"] == "uppercase" and sok["radH"] >= 44 and sok["felt"] == "0px" and sok["minste"] >= 11.9, f"Søk: {sok}"
                    ring(["#viewSok .chip", "#viewSok .srad", "#sokAvbryt"], "Søk")
                    # S44 3: Søk er lik Hjem. Klokka er 22:10: mørke timer får ikke tall, og raden sier at det er mørkt
                    na_ = page.evaluate("[...document.querySelectorAll('#viewSok .srad .na')].map(e => e.textContent.replace(/\\s+/g, ' ').trim())")
                    assert na_ and "Mørkt" in na_ and not any(re.search(r"\d", x) for x in na_), f"Søk i mørket skal si «Mørkt» uten tall: {na_[:8]}"
                    # fase 3 punkt 3: listeraden viser surfehøyden ved spoten, og «–» der ordet er Flatt eller Treffer ikke. Årsaken på egen linje
                    rad3 = page.evaluate("""() => { const n = Front.helpers.naHtml, b = (o) => Object.assign({light: 'dag', faded: 0, wind_speed: 4, wind_type: 'offshore'}, o), tmp = document.createElement('div');
                        const les = (h) => { tmp.innerHTML = n(h, null, ratingWord(h)); return [...tmp.childNodes].map(e => e.textContent.trim()); };
                        return {flatt: les(b({stars: 0, low_reason: 'flat', surf_height: 0})), treffer: les(b({stars: 0, low_reason: 'treffer_ikke', surf_height: 1.2})),
                                to: les(b({stars: 2, surf_height: 1.2})), blaast: les(b({stars: 0, low_reason: 'blown_out', surf_height: 1.4, wind_speed: 14, wind_type: 'onshore'}))}; }""")
                    assert rad3["flatt"] == ["Flatt", "–"] and rad3["treffer"] == ["Ikke surfbart", "–", "Treffer ikke"] and rad3["to"] == ["Ok", "1,2 m"], rad3
                    assert rad3["blaast"] == ["Ikke surfbart", "1,4 m", "Blåst ut"], rad3
                    # lang sjø: «, usikkert» står i Søk og Utforsk-lista også (feiljegeren 25.11.2026, funn 17)
                    assert page.evaluate("Front.helpers.naHtml({stars: 2, surf_height: 1.2, light: 'dag', long_sea: true}, null, 'Ok')").startswith("Ok, usikkert<span")
                    audit("fase2-sok")
                    go("#logger", "#viewSide:not([hidden]) #detailPane .sek")
                    lg = page.evaluate("""() => ({sek: document.querySelectorAll('#detailPane .sek').length, tomme: [...document.querySelectorAll('#detailPane .tomlinje')].map(p => p.textContent.trim()), kort: document.querySelectorAll('#detailPane .kort').length,
                        venstre: Math.round(document.querySelector('#detailPane .sek').getBoundingClientRect().left)})""")
                    assert lg["sek"] >= 6 and lg["kort"] == 0 and lg["venstre"] == 16, f"Logger skal ha seksjonsstreken, ingen kort og venstrekant 16 px: {lg}"
                    assert len(lg["tomme"]) == len(set(lg["tomme"])) and lg["tomme"].count("Ingen logger med varsel å sammenligne mot ennå.") == 1, f"tom tilstand i Logger skal stå én gang per seksjon: {lg['tomme']}"
                    audit("fase2-logger")
                    # punkt 4: dagvelgeren står over dommen og følger med. Etter dagbytte står dag, dom og time synlig sammen på 390 x 663
                    page.set_viewport_size({"width": 390, "height": 663})
                    go("#spot=unstad", SPOT_KLAR)
                    MAAL4 = """() => { const r = (q) => { const e = document.querySelector('#viewSpot ' + q); if(!e) return null; const b = e.getBoundingClientRect(); return [Math.round(b.top), Math.round(b.bottom)]; };
                        const dv = document.querySelector('#viewSpot .dagvelger'), dom = document.querySelector('#viewSpot .dom');
                        return {fane: Math.round(document.querySelector('.tabbar').getBoundingClientRect().top), dag: r('.dagknapp[aria-pressed="true"]'), dv: r('.dagvelger'), tall: r('.dom .t-tall') || r('.dom-ord b'), ord: r('.dom-ord b'), kl: r('#spOver .sek-spot'), time: r('#spOver .maalene') || r('#spOver .svell'),
                                pos: getComputedStyle(dv).position, foran: !!(dv.compareDocumentPosition(dom) & Node.DOCUMENT_POSITION_FOLLOWING), strek: getComputedStyle(document.querySelector('#viewSpot .dagknapp[aria-pressed="true"]')).borderBottomWidth,
                                rull: document.documentElement.scrollWidth - innerWidth}; }"""
                    for hvor in ("øverst", "nederst"):
                        page.evaluate("(ned) => window.scrollTo(0, ned ? document.querySelector('#viewSpot #tstripe').getBoundingClientRect().top + scrollY - 200 : 0)", hvor == "nederst"); page.wait_for_timeout(100)
                        if hvor == "nederst":   # rullet forbi: dagvelgeren står fast øverst i vinduet (ikke bare position:sticky i stilen)
                            fast = page.evaluate("(() => { const b = document.querySelector('#viewSpot .dagvelger').getBoundingClientRect(); return [Math.round(b.top), Math.round(b.bottom), scrollY]; })()")
                            assert fast[0] == 0 and fast[2] > 400, f"dagvelgeren skal stå fast øverst når siden er rullet ned: {fast}"
                        kn = page.locator('#viewSpot .dagknapp[aria-pressed="false"]').nth(1 if hvor == "øverst" else 2)
                        valgt_dag = kn.get_attribute("data-day")
                        kn.click(); page.wait_for_function("(d) => { const k = document.querySelector('#viewSpot .dagknapp[aria-pressed=\"true\"]'); return k && k.dataset.day === d; }", arg=valgt_dag); page.wait_for_timeout(100)
                        m4 = page.evaluate(MAAL4)
                        assert m4["pos"] == "sticky" and m4["foran"] and m4["strek"] == "3px" and m4["rull"] <= 0, f"dagvelgeren skal stå over dommen, følge med og ha 3 px strek under valgt dag: {m4}"
                        assert 0 <= m4["dag"][0] and m4["dag"][1] <= m4["tall"][0] and m4["tall"][1] <= m4["kl"][0] and m4["time"][1] <= m4["fane"], f"etter dagbytte ({hvor} på siden) skal dag, dom og time stå synlig sammen over fanelinja ({m4['fane']} px): {m4}"
                    ring(["#viewSpot .dagknapp", "#spotBack", "#viewSpot .fav-btn", "#viewSpot #hvorfor summary", "#loggHer"], "spotsiden")
                    # Runde 2 (feiljegeren 24.11.2026): også på lave skjermer, og for alle dagene i varselet. Trykk fra toppen av siden.
                    ALLE4 = """() => { const r = (q) => { const e = document.querySelector('#viewSpot ' + q); if(!e) return null; const b = e.getBoundingClientRect(); return [Math.round(b.top), Math.round(b.bottom)]; };
                        const alle = [...document.querySelectorAll('#viewSpot .dagknapp')].map(k => k.dataset.day), ut = [];
                        const trykk = (d) => { window.scrollTo(0, 0); document.querySelector(`#viewSpot .dagknapp[data-day="${d}"]`).click(); };
                        const valgt = document.querySelector('#viewSpot .dagknapp[aria-pressed="true"]').dataset.day, andre = alle.filter(d => d !== valgt);
                        trykk(andre[0]);
                        for(const d of [...andre.slice(1), valgt, andre[0]]){ trykk(d);
                            ut.push({dag: d, valgt: document.querySelector('#viewSpot .dagknapp[aria-pressed="true"]').dataset.day, fane: Math.round(document.querySelector('.tabbar').getBoundingClientRect().top), dv: r('.dagvelger'),
                                     tall: r('.dom .t-tall') || r('.dom-ord b'), ord: r('.dom-ord b'), kl: r('#spOver .sek-spot'), stort: r('#spOver .t-svell') || r('#spOver .svell'), blokk: r('#spOver'), y: Math.round(scrollY)}); }
                        return ut; }"""
                    for bw_, bh_ in ((320, 568), (360, 640), (375, 548), (390, 663)):   # 320 x 568: feiljegeren 25.11.2026, funn 20. 375 x 548: iPhone SE med verktøylinja i Safari (S38 2 a)
                        page.set_viewport_size({"width": bw_, "height": bh_})
                        for sid_ in ("unstad", "farstadsanden"):
                            go("#hjem", HJEM_KLAR); go(f"#spot={sid_}", SPOT_KLAR)
                            d4 = page.evaluate(ALLE4)
                            assert len(d4) >= 8 and all(m_["valgt"] == m_["dag"] for m_ in d4), f"dagbytte ({sid_}, {bw_} x {bh_}): {[(m_['dag'], m_['valgt']) for m_ in d4][:4]}"
                            for m_ in d4:
                                assert m_["dv"][0] >= 0 and m_["dv"][1] <= m_["tall"][0] and m_["ord"][1] <= m_["kl"][0] and m_["kl"][1] <= m_["stort"][0], f"etter dagbytte skal dagvelgeren stå over dommen og dommen over «Kl.» ({sid_}, {bw_} x {bh_}): {m_}"
                                assert m_["blokk"][1] <= m_["fane"], f"etter dagbytte skal hele KL.-blokka stå over fanelinja ({sid_}, {bw_} x {bh_}, {m_['dag']}): {m_}"
                            print(f"fase 2 punkt 4 ({sid_}, {bw_} x {bh_}): {len(d4)} dager, KL.-blokka slutter {min(m_['fane'] - m_['blokk'][1] for m_ in d4)}-{max(m_['fane'] - m_['blokk'][1] for m_ in d4)} px over fanelinja - OK")
                    page.set_viewport_size({"width": 390, "height": 663})
                    print(f"fase 2 punkt 4 (mobil 390 x 663): etter dagbytte nederst på siden står valgt dag {m4['dag']}, tallet {m4['tall']}, «Kl.» {m4['kl']} og timens rader til {m4['time'][1]} px, fanelinja starter på {m4['fane']} px - OK")
                    # tidevannsregelen på mobil (S33 a): en kort setning på egen linje under TIDEVANN-raden, på én linje på 390 px
                    for sid_ in ("farstadsanden", "grotfjord"):
                        go(f"#spot={sid_}", SPOT_KLAR)
                        tv = page.evaluate("""() => { const s = DATA.spots.find(x => x.id === Front.state.spotId), p = document.querySelector('#viewSpot .maal .mu-pref'), b = p && p.getBoundingClientRect();
                            return {vent: Tidevann.prefKort(s), hel: Tidevann.prefTekst(s), tekst: p && p.textContent, linjer: p && Math.round(b.height / parseFloat(getComputedStyle(p).lineHeight)), hoyre: b && Math.round(b.right), rader: document.querySelectorAll('#viewSpot .maal').length}; }""")
                        if sid_ == "farstadsanden":
                            assert tv["hel"] == "Farstadsanden er best på lav til middels vannstand" and tv["vent"] == "Best på lav til middels vannstand", tv
                            assert tv["tekst"] == tv["vent"] and tv["linjer"] == 1 and tv["hoyre"] <= 374, f"tidevannsregelen skal stå på én linje i TIDEVANN-raden på 390 px: {tv}"
                        else:
                            assert tv["vent"] == "" and tv["tekst"] is None and tv["rader"] >= 1, f"en spot uten tidevannsregel skal ikke ha noen linje: {tv}"
                    page.set_viewport_size({"width": vp[0], "height": vp[1]})
                else:
                    # punkt 6: ordmerket i toppen er ca. 28 px høyt med 44 px trykkflate. Punkt 7: tilstandene på nettsiden
                    wm = page.evaluate("(() => { const a = document.querySelector('.topbar .wm'), s = a.querySelector('svg'); return [s.getBoundingClientRect().height, a.getBoundingClientRect().height, a.getAttribute('href')]; })()")
                    assert 27 <= wm[0] <= 29 and wm[1] >= 44 and wm[2] == "#hjem", f"ordmerket på nettsiden: ca. 28 px høyt, 44 px trykkflate: {wm}"
                    ring([".topbar .wm", ".topnav a", "#temaKnapp", "#forside .fs-seg button", "#forside .fs-faner button", "#forside .knapp1", ".bunn a[href='#innstillinger']"], "forsiden")
                    # mørketid nås med tastaturet: mellomrom på knappen bytter tema
                    page.focus("#temaKnapp"); page.keyboard.press("Space"); page.wait_for_timeout(100)
                    assert page.evaluate("document.documentElement.dataset.theme") == "dark" and page.get_attribute("#temaKnapp", "aria-pressed") == "true", "«Mørketid» skal kunne slås på med tastaturet"
                    page.keyboard.press("Space"); page.wait_for_timeout(100)
                    assert page.evaluate("document.documentElement.dataset.theme") == "light"
                    page.evaluate("() => { document.documentElement.removeAttribute('data-theme'); try{ localStorage.removeItem('nordsurf.tema'); }catch(e){} }")
                    k1 = page.locator("#forside .knapp1").first
                    k1.scroll_into_view_if_needed(); k1.hover(); page.wait_for_timeout(100)
                    assert page.evaluate("(() => { const c = getComputedStyle(document.querySelector('#forside .knapp1')); return [c.backgroundColor, c.color]; })()") == [PAPIR, INK], "den fylte knappen skal snus når musa er over"
                    fn = page.locator('#forside .fs-faner button[aria-pressed="false"]').first
                    fn.hover(); page.wait_for_timeout(100)
                    strek = page.evaluate("""() => [getComputedStyle(document.querySelector('#forside .fs-faner button[aria-pressed="false"]:hover'), '::after').height, getComputedStyle(document.querySelector('#forside .fs-faner button[aria-pressed="true"]'), '::after').height]""")
                    assert strek == ["1px", "3px"], f"tekstfanene: 1 px strek under musa, 3 px under den valgte: {strek}"
                    page.mouse.move(0, 0)
                    go("#spot=unstad", SPOT_KLAR)
                    dk = page.evaluate("""() => { const v = getComputedStyle(document.querySelector('#viewSpot .dagknapp.stor[aria-pressed="true"]')), a = getComputedStyle(document.querySelector('#viewSpot .dagknapp.stor[aria-pressed="false"]'));
                        return [v.borderBottomWidth, v.borderBottomColor, v.borderTopWidth, a.borderBottomColor, document.querySelectorAll('#viewSpot .mu-pref').length]; }""")
                    assert dk[:3] == ["3px", INK, "2px"] and dk[3] != INK and dk[4] == 0, f"valgt dag på nettsiden: 3 px blekk under (ikke 4 px over), og tidevannsregelen står i «Om spotten», ikke i raden: {dk}"
                    ring(["#viewSpot .dagknapp.stor", "#viewSpot .fav-btn", "#viewSpot #loggHer", "#spotRegion"], "spotsiden")
                print(f"designrevisjonen fase 2 ({label}): én knappefamilie og én fokusring, {'fire faner, «Fra Tromsø» til Innstillinger, regionfaner, seksjonsstreken i Søk, Logger og Innstillinger, dagvelgeren øverst' if mobile else 'ordmerket 28 px, hover og valgt dag med 3 px strek under'} - OK")
                ctx.close()
            # ---- S21 a, S24 a og S26 på skjermen: alle timene på én spot er svak vind uten svell og uten poengtap, og vinden dreier fra
            # time til time (fralands, side, pålands, skrått pålands, 3 m/s med kast 5). Spotsiden sier «Flatt» for dagen og for timen,
            # uten høydetall og uten setningen «Sterk vind ødelegger bølgene» (ui.js favSetning). Runde 2 (S26, dagens time): hver tredje
            # time er 7,9 m/s pålands med kast 12 (teller som 9,1, ikke svak). Da heter hver dag med en slik lys time «Blåst ut», og
            # dagens ord (dayBest fra publish.best_hour), timen dagen åpnes på (bestOfDay) og ordet i dagfanen (spanOfDay) er samme time. ----
            for runde in ("svak", "dagsregel"):
                fc_sf = json.loads(json.dumps(FORECAST))
                for s in fc_sf["spots"]:
                    if s["id"] == SF_ID:
                        for i, h in enumerate(s["hours"]):
                            h.update(stars=0, faded=0, faded_wind=0, faded_tide=0, low_reason="blown_out", wind_type=("offshore", "side", "onshore", "sideonshore")[i % 4], wind_speed=3.0, gust=5.0, surf_height=0.0, surf_height_sets=0.0, bw_height=1.0,
                                     zero_losses={"energy": 0, "wind": 0, "tide": 0, "local": 0, "cap": 0})
                            if runde == "dagsregel" and i % 3 == 2:
                                h.update(wind_type="onshore", wind_speed=7.9, gust=12.0)
                ov_sf, det_sf = publish.split(fc_sf)
                ctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="nb-NO", timezone_id="Europe/Oslo", device_scale_factor=2, is_mobile=True, has_touch=True)
                page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS); page.clock.set_fixed_time(T0)
                page.on("pageerror", lambda e, r=runde: errors.append(f"svak vind ({r}): {e}"))
                route(page)
                def sf_route(rt, req, ov_sf=ov_sf, det_sf=det_sf):
                    path = req.url.split("?")[0]
                    if path.endswith("/data/oversikt.json"):
                        return rt.fulfill(status=200, content_type="application/json", body=json.dumps(ov_sf, ensure_ascii=False))
                    rt.fulfill(status=200, content_type="application/json", body=json.dumps(det_sf[path.rsplit("/", 1)[-1][:-5]], ensure_ascii=False))
                page.route("**/data/oversikt.json", sf_route)
                page.route("**/data/spots/*.json", sf_route)
                page.goto(f"http://127.0.0.1:{port}/index.html#spot={SF_ID}")
                page.wait_for_selector("#viewSpot:not([hidden]) .dom"); page.wait_for_selector("#viewSpot #tstripe .tk")
                dom = page.evaluate("""() => ({ord: document.querySelector('#viewSpot .dom-ord b').textContent.trim(), grunn: (document.querySelector('#viewSpot .dom-grunn') || {}).textContent || null, setn: (document.querySelector('#viewSpot .dom-setn') || {}).textContent || null,
                    vindu: (document.querySelector('#viewSpot .dom .t-vindu') || {}).textContent || null, tekst: document.querySelector('#viewSpot').innerText})""")
                # dag for dag: dagens time fra oversikten (publish.best_hour), timen dagen åpnes på og ordet i dagfanen
                dager = page.evaluate("""([det, ov]) => { const s = {...det, ...ov, hours: det.hours}, Hh = Front.helpers; SpotGraf.defaultDay(s, Hh.nowIdx(s), Hh);
                    return SpotGraf.days(s).map(d => { const b = Hh.dayBest(s, d.key), i = SpotGraf.bestOfDay(s, d), lys = d.idxs.map(j => s.hours[j]).filter(h => Hh.usable(h) && Hh.known(h));
                        return {key: d.key, b: b.h ? b.h.t : null, b_ord: b.h ? ratingWord(b.h) : null, vist: s.hours[i].t, vist_ord: ratingWord(s.hours[i]), fane: SpotGraf.spanOfDay(s, d).word,
                            blaast: lys.some(h => windBlamed(h)), lys: lys.length}; }); }""", [det_sf[SF_ID], next(x for x in ov_sf["spots"] if x["id"] == SF_ID)])
                med_tall = [d for d in dager if d["b"] is not None]
                assert med_tall, dager
                for d in med_tall:
                    assert d["b"] == d["vist"] and d["b_ord"] == d["vist_ord"] == d["fane"], f"{runde}: dagens ord, timen som vises og dagfanen skal være samme time: {d}"
                    assert d["b_ord"] == ("Blåst ut" if d["blaast"] else "Flatt"), f"{runde}: {d}"
                if runde == "svak":
                    assert not any(d["blaast"] for d in dager), dager
                    assert dom["ord"] == "Flatt" and dom["setn"] is None and dom["vindu"] is None, f"dagens beste time i svak vind uten svell skal hete «Flatt» uten setning om vinden: {dom['ord']!r}, {dom['setn']!r}, {dom['vindu']!r}"
                    assert "Sterk vind" not in dom["tekst"] and "Blåst ut" not in dom["tekst"] and "BLÅST UT" not in dom["tekst"], "spotsiden skal ikke skylde på vinden når alle timene er svak vind uten svell, uansett retning"
                else:
                    assert sum(d["blaast"] for d in med_tall) >= 2, f"testdataene skal ha minst to dager med en blåst lys time: {dager}"
                    # fase 3 punkt 5: ordet etter tallet er karakteren, årsaken «Blåst ut» står på egen linje
                    assert dom["ord"] == "Ikke surfbart" and (dom["grunn"] or "").lower() == "blåst ut", f"dagens årsak skal være «Blåst ut» når en like god lys time samme dag er blåst ut (S26): {dom['ord']!r}, {dom['grunn']!r}"
                ctx.close()
            # ---- S28 på skjermen (PC, «Om spotten»): en Breivikeidet laget av Lenangsøyra-timene i fiksturen med metaen fra
            # spots.json (local_rules.tide_level) sier «Best på lavt vann». Grøtfjord (ingen regel) og Farstadsanden (tide_prefer)
            # sier det samme som før. ----
            fc_b = json.loads(json.dumps(FORECAST))
            bre_cfg = next(x for x in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"] if x["id"] == "breivikeidet")
            bre_fc = json.loads(json.dumps(next(x for x in fc_b["spots"] if x["id"] == "lenangsoyra")))
            bre_fc.update({k: bre_cfg[k] for k in ("id", "name", "facing", "swell_window", "offshore_wind", "local_rules") if k in bre_cfg})
            fc_b["spots"].append(bre_fc)
            ov_b, det_b = publish.split(fc_b)
            assert det_b["breivikeidet"]["tide_regel"] is None and det_b["breivikeidet"]["local_rules"]["tide_level"]
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="nb-NO", timezone_id="Europe/Oslo", color_scheme="light")
            page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS); page.clock.set_fixed_time(T0)
            page.on("pageerror", lambda e: errors.append(f"S28 Om spotten: {e}"))
            route(page)
            def b_route(rt, req, ov_b=ov_b, det_b=det_b):
                path = req.url.split("?")[0]
                if path.endswith("/data/oversikt.json"):
                    return rt.fulfill(status=200, content_type="application/json", body=json.dumps(ov_b, ensure_ascii=False))
                rt.fulfill(status=200, content_type="application/json", body=json.dumps(det_b[path.rsplit("/", 1)[-1][:-5]], ensure_ascii=False))
            page.route("**/data/oversikt.json", b_route)
            page.route("**/data/spots/*.json", b_route)
            # Det brukeren faktisk ser (feiljegeren V1, 24.11.2026): ordene står ett sted på spotsiden, i «Om spotten» (#spOm) på 1440, for
            # Breivikeidet og ikke for Unstad. Tidevannskortet og forklaringen tegnes ikke på spotsiden nå (designfase 2), så testene
            # over som kaller funksjonene direkte, sier ikke at ordene synes. Skjermleseren får setningen i tidevannskurvens etikett.
            om_b, sett_b, kurve_b = {}, {}, {}
            for sid_ in ("breivikeidet", "grotfjord", "farstadsanden", "unstad"):
                page.goto(f"http://127.0.0.1:{port}/index.html#spot={sid_}")
                page.wait_for_selector("#viewSpot:not([hidden]) #spOm .spw-om")
                om_b[sid_] = page.evaluate("Object.fromEntries([...document.querySelectorAll('#spOm .spw-om > div')].map(d => [d.querySelector('dt').textContent.trim(), d.querySelector('dd').textContent.trim()]))").get("Tidevann")
                sett_b[sid_] = page.evaluate("[document.querySelector('#viewSpot').innerText.split('Best på lavt vann').length - 1, document.querySelector('#spOm').innerText.split('Best på lavt vann').length - 1]")
                page.wait_for_selector("#tstripe .tsvg")
                kurve_b[sid_] = page.get_attribute("#tstripe .tsvg", "aria-label")
            assert {k: om_b[k] for k in ("breivikeidet", "grotfjord", "farstadsanden")} == {"breivikeidet": "Best på lavt vann, men ikke under ca. 1,6 m", "grotfjord": "Spoten tåler alt tidevann", "farstadsanden": "Farstadsanden er best på lav til middels vannstand"}, om_b
            assert sett_b["breivikeidet"] == [1, 1], f"«Best på lavt vann» skal stå ett sted på Breivikeidets spotside på 1440, i «Om spotten»: {sett_b}"
            assert sett_b["unstad"] == sett_b["grotfjord"] == sett_b["farstadsanden"] == [0, 0] and "Best på lavt vann" not in (om_b["unstad"] or ""), f"«Best på lavt vann» står bare for Breivikeidet: {sett_b} {om_b}"
            assert kurve_b["breivikeidet"].startswith("Tidevann: ") and kurve_b["breivikeidet"].endswith(" Best på lavt vann, men ikke under ca. 1,6 m."), kurve_b["breivikeidet"]
            assert "Best på lavt vann" not in kurve_b["unstad"] + kurve_b["grotfjord"] + kurve_b["farstadsanden"] and kurve_b["farstadsanden"].endswith(" Farstadsanden er best på lav til middels vannstand."), kurve_b
            # på 390 (S33 a, plassen kom med designrevisjonen fase 2): ordene står ett sted, under raden TIDEVANN i KL.-blokka
            # (Tidevann.prefKort() leser Tidevann.prefTekst()), på én linje og innenfor skjermen. De andre spotene har sin egen
            # setning eller ingen, aldri Breivikeidets.
            page.set_viewport_size({"width": 390, "height": 844})
            mob_b = {}
            for sid_ in ("breivikeidet", "grotfjord", "farstadsanden", "unstad"):
                page.goto(f"http://127.0.0.1:{port}/index.html#spot={sid_}"); page.reload()
                page.wait_for_selector("#viewSpot:not([hidden]) #tstripe .tsvg")
                mob_b[sid_] = page.evaluate("""() => { const p = [...document.querySelectorAll('#viewSpot .maal .mu-pref')], b = p[0] ? p[0].getBoundingClientRect() : null;
                    return {pref: p.map(e => e.textContent.trim()), antall: document.querySelector('#viewSpot').innerText.split('Best på lavt vann').length - 1,
                            linjer: b ? Math.round(b.height / parseFloat(getComputedStyle(p[0]).lineHeight)) : 0, hoyre: b ? Math.round(b.right) : 0, bredde: innerWidth}; }""")
            assert mob_b["breivikeidet"]["pref"] == ["Best på lavt vann, over 1,6 m"] and mob_b["breivikeidet"]["antall"] == 1, f"«Best på lavt vann» skal stå ett sted på mobil, under raden TIDEVANN: {mob_b['breivikeidet']}"
            assert mob_b["breivikeidet"]["linjer"] == 1 and mob_b["breivikeidet"]["hoyre"] <= mob_b["breivikeidet"]["bredde"] - 16, f"«Best på lavt vann» skal stå på én linje innenfor skjermen: {mob_b['breivikeidet']}"
            # (Unstad har ingen tidevannsregel i testfila fra 14.10.2026: ingen linje der. Regelen kom 10.11.2026.)
            assert mob_b["grotfjord"]["pref"] == [] and mob_b["farstadsanden"]["pref"] == ["Best på lav til middels vannstand"] and mob_b["unstad"]["pref"] in ([], ["Best på lav til middels vannstand"]), mob_b
            assert mob_b["grotfjord"]["antall"] == mob_b["farstadsanden"]["antall"] == mob_b["unstad"]["antall"] == 0, f"«Best på lavt vann» står bare for Breivikeidet: {mob_b}"
            page.goto(f"http://127.0.0.1:{port}/index.html#spot=breivikeidet"); page.reload(); page.wait_for_selector("#viewSpot:not([hidden]) #tstripe .tsvg")
            assert page.get_attribute("#tstripe .tsvg", "aria-label").endswith(" Best på lavt vann, men ikke under ca. 1,6 m.")
            ctx.close()
            browser.close()
            # ---- Designrevisjonen fase 2, runde 2: skjemafeltene i WebKit (Safari). Nedtrekkslista var 23 px høy der med
            # nettleserens egen form (feiljegeren 24.11.2026). WebKit er ikke installert i CI (bare Chromium): da hoppes delen
            # over med en linje i utskriften, og formen er uansett låst i Chromium-delen over (appearance: none, 44 px).
            try:
                wk = p.webkit.launch()
            except Exception as e:   # noqa: BLE001
                wk = None
                print(f"fase 2 runde 2: WebKit er ikke installert her ({str(e).splitlines()[0][:80]}) - WebKit-delen er hoppet over")
            if wk:
                try:
                    ctx = wk.new_context(viewport={"width": 390, "height": 663}, has_touch=True, locale="nb-NO", timezone_id="Europe/Oslo")
                    page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS); page.clock.set_fixed_time(T0)
                    route(page)
                    page.route("**/data/oversikt.json", lambda rt, req: rt.fulfill(status=200, content_type="application/json", body=OV_BODY))
                    page.goto(f"http://127.0.0.1:{port}/index.html#innstillinger"); page.wait_for_selector("#viewSide:not([hidden]) #omrade")
                    page.evaluate("() => { window.Auth = {state: {ready: true, user: null, profile: null, favorites: new Set()}, toggleFavorite: async () => {}}; Front.refresh(); }"); page.wait_for_selector("#authEmail")
                    wf = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#detailPane select, #detailPane input')].map(e => { const b = e.getBoundingClientRect(), c = getComputedStyle(e);
                        return [e.id, {w: Math.round(b.width), h: Math.round(b.height), strek: c.boxShadow.includes('inset') && c.boxShadow.includes('-2px')}]; }))""")
                    assert set(wf) >= {"authEmail", "omrade", "syncRepo", "syncToken"} and all(v["w"] >= 300 and v["h"] >= 44 and v["strek"] for v in wf.values()), f"WebKit: feltene i Innstillinger skal være 44 px høye med strek under: {wf}"
                    assert wf["omrade"]["h"] == wf["authEmail"]["h"], f"WebKit: områdevelgeren skal være like høy som e-postfeltet: {wf}"
                    print(f"fase 2 runde 2 (WebKit 390 x 663): områdevelgeren {wf['omrade']['w']} x {wf['omrade']['h']} px med strek under, som e-postfeltet - OK")
                    ctx.close()
                finally:
                    wk.close()
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
