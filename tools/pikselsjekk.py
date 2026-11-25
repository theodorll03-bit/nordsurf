"""Pikselsjekk (designfase 4, 25.11.2026): lokalt verktøy for endringer som ikke skal synes. Ikke i CI (Linux tegner
skrift annerledes enn macOS, og det lagres ingen fasitbilder i git).

    python3 tools/pikselsjekk.py ta <repo> <utmappe> [--oppsett m390,pc1440] [--data vanlig,gode] [--dekning]
    python3 tools/pikselsjekk.py sml <mappe a> <mappe b> [<mappe a2> <mappe b2>]

«ta» åpner docs/index.html i Chromium med fast klokke, blokkerte eksterne kall, skjulte foto og reduced_motion, går
gjennom skjermene (Hjem, Søk, spotsiden, loggarket, forklaringsarkene, Logger, Innstillinger, Utforsk) og tar bilder av
hele siden (to like bilder på rad). Til hvert bilde lagres også målene og de beregnede stilene for hvert element.
«sml» lister bildene som er ulike, med området som skiller (trenger Pillow bare til det), og elementene som har fått
andre mål eller stiler. Med fire mapper telles bare bilder som er ulike i begge parene (regelen i
privat/kontor/observasjoner/teknisk-plan-fase4: ett ulikt bilde i én kjøring kan være støy).
Mål støyen først: kjør «ta» to ganger på samme kode.

Datasettene: «vanlig» er fetcher/fixtures/forecast.json (ekte varsel, kveld, ingen 4 eller 5). «gode» er samme varsel med
innlagte dager: 5 og 4 poeng, usikkert, forbud, manglende data, mørkt hele dagen, alle årsakene ved 0 og tapte poeng, dag.
«--dekning» skriver dek.json: hvilke selektorer i docs/css som traff noe (til å finne død CSS).

Utmappa skal ligge utenfor git (privat/ eller en midlertidig mappe)."""
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import zlib
from pathlib import Path

STEG_MS = 8_000
OPPSETT = {   # navn: (bredde, høyde, tema, skrift, kontrast)
    "m320": (320, 568, "light", "", None), "m375": (375, 548, "light", "", None),
    "m390": (390, 844, "light", "", None), "m390d": (390, 844, "dark", "", None), "m390x2": (390, 844, "light", "200%", None),
    "m390k": (390, 844, "light", "", "more"),
    "pc1024": (1024, 800, "light", "", None), "pc1280": (1280, 900, "light", "", None),
    "pc1440": (1440, 900, "light", "", None), "pc1440d": (1440, 900, "dark", "", None),
}
HULL = ("surf_height", "surf_height_sets", "swell_offshore", "period", "dir_offshore", "energy_swell_kj", "wind_speed", "wind_dir", "gust", "air_temp", "water_temp", "confidence")
STILER = ("color", "background-color", "background-image", "font-family", "font-size", "font-weight", "font-stretch", "font-style", "line-height", "letter-spacing",
          "text-transform", "text-align", "text-decoration-line", "white-space", "display", "position", "top", "right", "bottom", "left", "margin", "padding", "gap",
          "border", "border-radius", "box-shadow", "outline", "opacity", "visibility", "overflow", "flex", "align-items", "justify-content", "grid-template-columns", "grid-template-rows",
          "grid-area", "min-width", "min-height", "max-width", "max-height", "width", "height", "transform", "z-index", "fill", "stroke", "stroke-width", "vertical-align", "cursor", "pointer-events")
STIL_JS = """(P) => { const ut = [], r1 = (v) => Math.round(v * 100) / 100;
  const stil = (c) => P.map(p => c.getPropertyValue(p));
  const gaa = (e, sti) => { const r = e.getBoundingClientRect(), c = getComputedStyle(e);
    ut.push([sti, [e.tagName.toLowerCase() + (e.id ? '#' + e.id : ''), r1(r.x + scrollX), r1(r.y + scrollY), r1(r.width), r1(r.height), ...stil(c)]]);
    for(const ps of ['::before', '::after']){ const q = getComputedStyle(e, ps); if(q.content !== 'none' && q.content !== 'normal') ut.push([sti + ps, ['', 0, 0, 0, 0, ...stil(q)]]); }
    let k = 0; for(const b of e.children){ if(!/^(SCRIPT|STYLE|LINK|CANVAS)$/.test(b.tagName) && !b.classList.contains('ml-kart') && !b.classList.contains('vindlag') && !b.classList.contains('kilelag')) gaa(b, sti + '/' + k); k++; } };
  gaa(document.body, ''); return ut; }"""


# ---------- CSS-leser (også brukt av fetcher/test_tokens.py) ----------
def uten_kommentarer(css):
    return re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), css, flags=re.S)


def regler(css):
    """[(linje, [@-regler rundt], selektor, [(egenskap, verdi)])] - går inn i @media, @container og @supports."""
    css = uten_kommentarer(css)
    ut = []

    def deklarasjoner(b):
        ds, d, dybde = [], "", 0
        for ch in b + ";":
            dybde += {"(": 1, ")": -1}.get(ch, 0)
            if ch == ";" and dybde == 0:
                if ":" in d:
                    p, v = d.split(":", 1)
                    ds.append((p.strip(), " ".join(v.split())))
                d = ""
            else:
                d += ch
        return ds

    def les(s, start, rundt):
        i = st = 0
        while i < len(s):
            if s[i] == "{":
                sel = s[st:i].strip()
                foran = st + len(s[st:i]) - len(s[st:i].lstrip())
                d, j = 1, i + 1
                while d:
                    d += {"{": 1, "}": -1}.get(s[j], 0)
                    j += 1
                inni = s[i + 1:j - 1]
                if sel.startswith("@") and "{" in inni:
                    les(inni, start + i + 1, rundt + [sel])
                else:
                    ut.append((css.count("\n", 0, start + foran) + 1, rundt, sel, deklarasjoner(inni)))
                i = st = j
            elif s[i] == ";" and s[st:i].strip().startswith("@"):
                i += 1
                st = i
            else:
                i += 1

    les(css, 0, [])
    return ut


# ---------- testdata ----------
def data_vanlig(varsel):
    return varsel, dt.datetime.fromisoformat(varsel["generated"].replace("Z", "+00:00")) + dt.timedelta(minutes=70)


def data_gode(varsel):
    """Innlagte dager (bare visning): dagene i lista under, per spot. Tallene er ikke varsel, de er valgt for å få fram
    hver tilstand. Timene i lyset får dagens poeng midt på dagen og ett mindre på kantene."""
    v = json.loads(json.dumps(varsel))
    gen = dt.datetime(2026, 10, 15, 7, 0, tzinfo=dt.timezone.utc)
    v["generated"] = gen.isoformat()
    # poeng per dag fra 15.10, eller en årsak ved 0. «t» = tapte poeng på vind og tidevann, «u» = usikkert (lang sjø)
    plan = {
        "unstad": [5, "4t", 3, 2, 1, "flat", "miss", 5, 4, "dark"], "grotfjord": ["4t", 5, "miss", 3, "dark", 4, 2, 1, "blown_out"],
        "steinkrossa": [4, "forbud", "forbud", 3, 5, 0, 1], "lenangsoyra": ["miss", "miss", 4, "miss", 2, 3, 0], "tromvik": ["dark"] * 10,
        "ersfjordstranda": ["blown_out", "treffer_ikke", "stormsjo", "gro", "smaa", "flat", "3t"], "russelv": ["3u", "4u", 2, "blown_out", 0, 1, 5],
        "farstadsanden": ["2t", "5t", "treffer_ikke", 4, 3, "stormsjo", "gro"],
    }
    for s in v["spots"]:
        if s["id"] == "steinkrossa":
            s["restriksjoner"] = [{"type": "surfeforbud", "gjelder": "begge", "fra": "10-16", "til": "10-17", "grunn": "fuglefredning"}]
        if s["id"] == "russelv":
            s["status"], s["forelopig_fra"], s["andel_forelopig"] = "forelopig", "2026-10-10", True
        ut = []
        for h in s["hours"]:
            t = dt.datetime.fromisoformat(h["t"].replace("Z", "+00:00"))
            if t < gen:
                continue
            dag, kl = (t + dt.timedelta(hours=2)).date().toordinal() - dt.date(2026, 10, 15).toordinal(), t.hour
            rad = plan.get(s["id"], [])
            hva = str(rad[dag]) if dag < len(rad) else None
            if hva is None:
                ut.append(h)
                continue
            lyst = h.get("light") in ("dag", "skumring")
            if hva == "dark":
                h["light"], h["daylight"] = "mørkt", False
            elif hva == "miss":
                for k in HULL:
                    if k in h:
                        h[k] = None
                h.update(stars=0, low_reason=None, breakdown=[], light=h.get("light"))
            else:
                n = int(hva[0]) if hva[0].isdigit() else 0
                if n and lyst and not 8 <= kl <= 12:
                    n -= 1
                h.update(stars=n, low_reason=None, likely_flat=False, blown_out=False, uncertain=False, faded=0, faded_wind=0, faded_tide=0, sources_disagree=False,
                         zero_losses={"energy": 0, "wind": 0, "tide": 0, "local": 0, "cap": 0}, surf_height=round(0.5 + 0.35 * n + 0.02 * kl, 2), period=9.5 + n,
                         swell_offshore=round(0.9 + 0.5 * n, 1), bw_height=1.2, confidence=70 + 5 * n, wind_speed=2.4 + n, wind_type="offshore" if n >= 4 else "side", gust=7.0 + n)
                h["surf_height_sets"] = round(h["surf_height"] * 1.27, 2)
                if n >= 4 and s.get("swell_window"):
                    w = s["swell_window"]
                    w = w[0] if isinstance(w[0], list) else w
                    h["dir_offshore"] = float((w[0] + ((w[1] - w[0]) % 360) / 2) % 360)
                if hva.endswith("t"):
                    h["faded_wind"], h["faded_tide"] = (1 if kl % 2 else 2) if n <= 3 else 1, 1 if n <= 3 and kl % 3 == 0 else 0
                    h["faded"] = h["faded_wind"] + h["faded_tide"]
                if hva.endswith("u"):
                    h["uncertain"], h["long_sea"] = True, {"height": 1.8, "dir": 355, "period": 9.8}
                if hva in ("flat", "0"):
                    h.update(low_reason="flat" if hva == "flat" else None, surf_height=0.0, surf_height_sets=0.0)
                if hva == "smaa":
                    h.update(low_reason="flat", surf_height=0.45, surf_height_sets=0.6)
                if hva == "gro":
                    h.update(low_reason="flat", surf_height=1.1, surf_height_sets=1.4, zero_losses={"energy": 1, "wind": 0, "tide": 0, "local": 0, "cap": 0})
                if hva in ("blown_out", "treffer_ikke", "stormsjo"):
                    h.update(low_reason=hva, wind_speed=13.0, wind_type="onshore", gust=18.0, zero_losses={"energy": 0, "wind": 3 if hva == "blown_out" else 0, "tide": 0, "local": 0, "cap": 0})
            ut.append(h)
        s["hours"] = ut
    return v, gen + dt.timedelta(minutes=70)


# ---------- bildene ----------
def ta(repo, ut, oppsett, datasett, dekning):
    repo, ut = Path(repo).resolve(), Path(ut).resolve()
    ut.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(repo / "fetcher"))
    os.chdir(repo)
    import publish
    import testserver
    from playwright.sync_api import sync_playwright
    varsel = json.loads((repo / "fetcher" / "fixtures" / "forecast.json").read_text(encoding="utf-8"))
    hashfil = ut / "hash.json"
    hasher = json.loads(hashfil.read_text()) if hashfil.exists() else {}
    feil, selektorer, treff = [], [], set()
    for f in ("app.css", "ui.css"):
        for ln, rundt, se, _ in regler((repo / "docs" / "css" / f).read_text(encoding="utf-8")):
            if se.startswith("@") or any("keyframes" in a for a in rundt):
                continue
            for x in re.split(r",(?![^()]*\))", se):
                b = re.sub(r"::?(hover|active|focus-visible|focus-within|focus|before|after|placeholder|-webkit-[\w-]+|disabled)", "", x).strip()
                selektorer.append((f, ln, x.strip(), (b + " *" if b.endswith((">", "+", "~")) else b) or "*"))
    grunner = sorted({s[3] for s in selektorer})
    DEK_JS = "(bs)=>{const t=[];for(const b of bs){try{if(document.querySelector(b))t.push(b)}catch(e){}}return t}"
    srv, port = testserver.serve(repo / "docs")
    try:
        with sync_playwright() as p:
            br = p.chromium.launch(args=["--lang=nb-NO", *testserver.WEBGL_ARGS])
            for dsnavn in datasett:
                v, naa = {"vanlig": data_vanlig, "gode": data_gode}[dsnavn](varsel)
                ov, det = publish.split(v)
                ov_txt, det_txt = json.dumps(ov, ensure_ascii=False), {k: json.dumps(x, ensure_ascii=False) for k, x in det.items()}
                for navn in oppsett:
                    b, h, tema, skrift, kontrast = OPPSETT[navn]
                    mob = b < 1024
                    ctx = br.new_context(viewport={"width": b, "height": h}, color_scheme=tema, locale="nb-NO", timezone_id="Europe/Oslo", device_scale_factor=1,
                                         is_mobile=mob, has_touch=mob, reduced_motion="reduce", service_workers="block", **({"contrast": kontrast} if kontrast else {}))
                    pg = ctx.new_page()
                    pg.set_default_timeout(STEG_MS)
                    pg.clock.set_fixed_time(naa)
                    pg.on("pageerror", lambda e, n=navn: feil.append(f"{n}: {e}"))
                    for pat in ("https://cdn.jsdelivr.net/**", "https://*.supabase.co/**", "https://fonts.g*/**", "https://cache.kartverket.no/**"):
                        pg.route(pat, lambda r: r.abort())
                    pg.route("**/data/oversikt.json", lambda r: r.fulfill(status=200, content_type="application/json", body=ov_txt))
                    pg.route("**/data/spots/*.json", lambda r: r.fulfill(status=200, content_type="application/json", body=det_txt[r.request.url.split("?")[0].rsplit("/", 1)[-1][:-5]]))
                    pg.add_init_script("""if(!localStorage.getItem('nordsurf.logs.v1')) localStorage.setItem('nordsurf.logs.v1', JSON.stringify([{id:'a',t:new Date(Date.now()-26*36e5).toISOString(),spot:'unstad',stars:3,size:'Brysthøy',wind:'offshore',type:'own'},{id:'b',t:new Date(Date.now()-8*864e5).toISOString(),spot:'grotfjord',stars:4,type:'own'}]))""")
                    pg.goto(f"http://127.0.0.1:{port}/index.html")
                    pg.wait_for_function("window.Front && typeof DATA!=='undefined' && DATA && document.querySelector('#viewHjem :is(#forside, .hjem-linje)')")
                    pg.evaluate("()=>{ try{ Auth.state.favorites = new Set(['grotfjord','unstad','steinkrossa','tromvik']) }catch(e){} }")
                    if skrift:
                        pg.evaluate("f=>document.documentElement.style.fontSize=f", skrift)
                    # kartflata (WebGL), vindstrekene og kilen tegnes ikke likt fra gang til gang. Merkene og kortene på Utforsk er med
                    pg.add_style_tag(content=".sp-foto,.ml-kart canvas,.vindlag,.kilelag{visibility:hidden!important} input,select,textarea{caret-color:transparent!important}")

                    def bilde(n, hel=True):
                        pg.wait_for_timeout(120)
                        pg.evaluate("()=>{document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager'); if(document.activeElement && !document.activeElement.matches('[data-behold]')) document.activeElement.blur(); return Promise.all([document.fonts.ready, ...[...document.images].map(i=>i.decode().catch(()=>0))])}")
                        if dekning:
                            treff.update(pg.evaluate(DEK_JS, grunner))
                        hoyde = pg.evaluate("document.documentElement.scrollHeight")
                        hel = hel and hoyde < 12000   # 200 % tekst: for høy side til ett bilde, da bare vinduet
                        if hel:
                            pg.evaluate("window.scrollTo(0, 0)")   # dagvelgeren på spotsiden er sticky: rullet side gir ulike helbilder
                        forrige, png = None, None
                        for _ in range(10):
                            png = pg.screenshot(full_page=hel, animations="disabled")
                            if png == forrige:
                                break
                            forrige = png
                            pg.wait_for_timeout(150)
                        else:
                            feil.append(f"ustabilt bilde: {navn}_{dsnavn}_{n}")
                        key = f"{navn}_{dsnavn}_{n}"
                        (ut / f"{key}.png").write_bytes(png)
                        hasher[key] = hashlib.sha256(png).hexdigest()[:16]
                        with gzip.open(ut / f"{key}.stil.gz", "wt", encoding="utf-8", compresslevel=3) as f:
                            json.dump(pg.evaluate(STIL_JS, list(STILER)), f, ensure_ascii=False)

                    def gaa(hash_, sel):
                        pg.evaluate("h=>{location.hash=h}", hash_)
                        pg.wait_for_selector(sel)

                    def klikk(sel, nr=0):
                        e = pg.query_selector_all(sel)
                        if len(e) > nr:
                            e[nr].evaluate("e=>e.click()")
                            return True
                        return False

                    def esc():
                        pg.keyboard.press("Escape")
                        pg.wait_for_timeout(120)


                    def hjem():
                        pg.evaluate("Front.refresh()")
                        bilde("hjem")
                        if mob:
                            if klikk("#favRediger"):
                                bilde("hjem-rediger")
                                klikk("#favRediger")
                            if klikk(".regionvelger button", 1):
                                bilde("hjem-region")
                            pg.evaluate("()=>{ Auth.state.favorites = new Set(); Front.refresh() }")
                            bilde("hjem-uten")
                            pg.evaluate("()=>{ Auth.state.favorites = new Set(['grotfjord','unstad','steinkrossa','tromvik']); Front.refresh() }")
                        else:
                            if klikk("#fsAlle"):
                                bilde("hjem-alle")
                            if klikk(".fs-seg button", 1):
                                bilde("hjem-imorgen")
                            if klikk(".fs-faner button", 0):
                                bilde("hjem-alleregioner")
                            for sel, n in ((".fs-seg button", "seg"), (".fs-faner button:nth-child(2)", "fane"), (".fs-tabell tr.s", "rad"), ("#temaKnapp", "tema")):
                                e = pg.query_selector(sel)
                                if e and navn == "pc1440":
                                    e.hover()
                                    bilde("hover-" + n)
                            pg.mouse.move(0, 0)
                            for q in ("un", "zzzz"):
                                pg.fill("#sokPC", q)
                                bilde("sokdrop-" + q)
                            pg.fill("#sokPC", "")
                            esc()

                    def sok():
                        if not mob:
                            return
                        gaa("#sok", "#viewSok:not([hidden])")
                        bilde("sok")
                        for q in ("gr", "t", "zzzz"):
                            pg.fill("#sokM", q)
                            bilde("sok-" + q)

                    def spot():
                        ids = ("unstad", "farstadsanden", "steinkrossa") if dsnavn == "vanlig" else ("unstad", "grotfjord", "steinkrossa", "lenangsoyra", "tromvik", "ersfjordstranda", "russelv")
                        for sid in ids:
                            gaa(f"#spot={sid}", "#viewSpot:not([hidden]) .dom")
                            pg.wait_for_function("id => !document.querySelector('.spw') || document.querySelector('#miniKort svg .land') || /mangler/.test((document.querySelector('#miniKort .kredit')||{}).textContent||'')", arg=sid)
                            bilde(f"spot-{sid}")
                            full = sid in ("unstad", "ersfjordstranda")
                            for k in ((1, 2, 3, 4, 5, 6, 8) if full else (1, 3)):
                                if klikk("#viewSpot .dagknapp", k):
                                    pg.wait_for_timeout(60)
                                    if mob and k == 1:
                                        bilde(f"spot-{sid}-d{k}-vindu", hel=False)   # rullet, med dagvelgeren stående øverst
                                    bilde(f"spot-{sid}-d{k}")
                            inp = pg.query_selector("#tstripeVelg")
                            if inp:
                                inp.evaluate("e=>{ e.value = String(+e.value + 2 <= +e.max ? +e.value + 2 : e.min); e.dispatchEvent(new Event('input')) }")
                                bilde(f"spot-{sid}-time")
                            pg.evaluate("()=>{ const h = document.querySelector('#viewSpot #hvorfor'); if(h) h.open = true }")
                            bilde(f"spot-{sid}-hvorfor")

                    def ark():
                        gaa("#spot=unstad", "#viewSpot:not([hidden]) .dom")
                        pg.wait_for_timeout(200)
                        nokler = pg.evaluate("Object.keys(EXPLAIN)") if navn in ("m390", "pc1440") else ["surf_height", "wind", "confidence"]
                        pg.evaluate("()=> ensureSpot('unstad')")
                        for k in nokler:
                            pg.evaluate("k=>{ const s = DATA.spots.find(x=>x.id==='unstad'); openExplain(k, s.hours.find(h=> h.stars >= 1) || s.hours[0], s) }", k)
                            bilde("ark-" + k, hel=False)
                            esc()
                        klikk("#viewSpot #loggHer")
                        pg.wait_for_timeout(150)
                        bilde("ark-logg", hel=False)
                        klikk("#starPick button", 4)
                        klikk('[data-group="type"] button', 1)
                        klikk('[data-group="size"] button', 2)
                        klikk('[data-group="wind"] button', 1)
                        bilde("ark-logg-valgt", hel=False)
                        pg.evaluate("()=>{ const s = document.querySelector('#sheet'); s.scrollTop = s.scrollHeight }")
                        bilde("ark-logg-bunn", hel=False)
                        esc()
                        pg.evaluate("()=>{ const s = document.querySelector('#witnessSheet'); document.querySelector('#witnessSub').textContent = 'Unstad i går kl. 14'; s.classList.add('open') }")
                        bilde("ark-vitne", hel=False)
                        pg.evaluate("()=>{ document.querySelector('#witnessSheet').classList.remove('open') }")

                    def sider():
                        gaa("#logger", "#viewSide:not([hidden])")
                        bilde("logger")
                        pg.evaluate("()=>{ localStorage.setItem('nordsurf.logs.v1', '[]'); Front.refresh() }")
                        bilde("logger-tom")
                        gaa("#innstillinger", "#viewSide:not([hidden])")
                        bilde("innstillinger")
                        pg.evaluate("()=>{ window.__u = Auth.state.user; Auth.state.user = {id: 'x', email: 'test@example.com'}; Auth.state.profile = {display_name: 'Test'}; Front.refresh() }")
                        bilde("innstillinger-inne")
                        pg.evaluate("()=>{ Auth.state.user = window.__u; Auth.state.profile = null; toast('Økt slettet', 'Angre', ()=>0, 60000) }")
                        bilde("toast", hel=False)
                        pg.evaluate("()=>{ document.querySelector('#toast').classList.remove('show'); document.querySelector('#feil').hidden = false }")
                        bilde("feil", hel=False)
                        pg.evaluate("()=>{ document.querySelector('#feil').hidden = true }")

                    def utforsk():
                        gaa("#utforsk", "#viewUtforsk:not([hidden])")
                        try:
                            pg.wait_for_selector(".mk, .klynge", state="attached")
                        except Exception as e:   # noqa: BLE001
                            feil.append(f"{navn}: ingen merker på Utforsk ({str(e)[:60]})")
                        pg.wait_for_timeout(700)
                        bilde("utforsk", hel=False)
                        for nr, n in ((0, "a"), (1, "b")):
                            if klikk(".mk", nr):
                                pg.wait_for_timeout(400)
                                bilde("utforsk-kort-" + n, hel=False)
                        if klikk("#dagChips .chip", 2):
                            pg.wait_for_timeout(200)
                            bilde("utforsk-dag", hel=False)
                        klikk("#kortLukk")
                        if klikk("#utforskChips .chip.dashed"):
                            pg.wait_for_timeout(200)
                            bilde("utforsk-utenfor", hel=False)

                    def gammelt():
                        pg.evaluate("()=>{ DATA.generated = new Date(Date.now() - 20 * 36e5).toISOString(); location.hash = '#hjem'; Front.refresh() }")
                        pg.wait_for_timeout(100)
                        bilde("hjem-gammelt", hel=False)

                    for f in (hjem, sok, spot, ark, sider, utforsk, gammelt):
                        try:
                            f()
                        except Exception as e:   # noqa: BLE001
                            feil.append(f"{navn} {dsnavn} {f.__name__}: {str(e)[:160]}")
                    ctx.close()
                    hashfil.write_text(json.dumps(hasher, indent=1, sort_keys=True))
            br.close()
    finally:
        srv.shutdown()
    if dekning:
        fil = ut / "dek.json"
        gammel = {tuple(x[:3]): x[4] for x in json.loads(fil.read_text())} if fil.exists() else {}
        fil.write_text(json.dumps([(f, ln, x, b, b in treff or gammel.get((f, ln, x), False)) for f, ln, x, b in selektorer], ensure_ascii=False))
    print(f"{len(hasher)} bilder i {ut}")
    for x in feil:
        print("  MERK:", x)


def sammenlikn(a, b):
    """{bilde: (området som skiller eller «mangler», [elementer med andre stiler])} for bildene som er ulike."""
    a, b = Path(a), Path(b)
    ha, hb = (json.loads((x / "hash.json").read_text()) for x in (a, b))
    ulike = {}
    for k in sorted(set(ha) | set(hb)):
        if k not in ha or k not in hb:
            ulike[k] = ("mangler i den ene", [])
            continue
        stil = []
        fa, fb = a / f"{k}.stil.gz", b / f"{k}.stil.gz"
        if fa.exists() and fb.exists():
            ra, rb = gzip.decompress(fa.read_bytes()), gzip.decompress(fb.read_bytes())
            if zlib.crc32(ra) != zlib.crc32(rb):
                da, db = dict(map(tuple_, json.loads(ra))), dict(map(tuple_, json.loads(rb)))
                for sti in list(da) + [x for x in db if x not in da]:
                    if da.get(sti) != db.get(sti):
                        x, y = da.get(sti), db.get(sti)
                        navn = ("element", "x", "y", "bredde", "høyde") + STILER
                        stil.append((sti, (x or y)[0], [f"{navn[i]}: {x[i]} -> {y[i]}" for i in range(len(x)) if x[i] != y[i]] if x and y else ["bare i den ene"]))
        if ha[k] != hb[k]:
            try:
                from PIL import Image, ImageChops
                A, B = (Image.open(x / f"{k}.png").convert("RGB") for x in (a, b))
                omr = "ulik størrelse %s %s" % (A.size, B.size) if A.size != B.size else str(ImageChops.difference(A, B).getbbox())
            except ImportError:
                omr = "ulikt"
            ulike[k] = (omr, stil)
        elif stil:
            ulike[k] = (None, stil)
    return ulike, len(set(ha) & set(hb))


def tuple_(x):
    return x[0], tuple(x[1])


def sml(mapper):
    par = [sammenlikn(mapper[i], mapper[i + 1]) for i in range(0, len(mapper), 2)]
    for nr, (u, n) in enumerate(par):
        pk = [k for k in u if u[k][0]]
        st = [k for k in u if u[k][1]]
        print(f"par {nr + 1}: {n} bilder i begge, {len(pk)} ulike i piksler, {len(st)} med andre stiler eller mål")
        for k in u:
            omr, stil = u[k]
            print("  ", k, omr or "like piksler", f"{len(stil)} elementer" if stil else "")
            for sti, tag, hva in stil[:3]:
                print("       ", tag, sti, "; ".join(hva[:4]))
    if len(par) == 2:
        begge = sorted(k for k in par[0][0] if par[0][0][k][0] and k in par[1][0] and par[1][0][k][0])
        print(f"ulike piksler i begge parene: {len(begge)}", *begge, sep="\n   ")
        return 1 if begge else 0
    return 1 if any(x[0] for u, _ in par for x in u.values()) else 0


if __name__ == "__main__":
    arg = sys.argv[1:]
    if len(arg) >= 3 and arg[0] == "ta":
        valg = {x: arg[arg.index(x) + 1].split(",") for x in ("--oppsett", "--data") if x in arg}
        ta(arg[1], arg[2], valg.get("--oppsett", list(OPPSETT)), valg.get("--data", ["vanlig", "gode"]), "--dekning" in arg)
    elif len(arg) in (3, 5) and arg[0] == "sml":
        sys.exit(sml(arg[1:]))
    else:
        print(__doc__)
        sys.exit(2)
