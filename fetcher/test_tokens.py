"""Designfase 4 (25.11.2026): avstander, skrift og vekter i CSS-en kommer fra variablene i docs/css/ui.css. Kjøres av
test_docs_cache.py (som alt går i CI), og kan kjøres for seg: python3 fetcher/test_tokens.py. Ren Python, under ett sekund.

Reglene (docs/css/*.css og <style> i docs/*.html, også inni @media, @container og @supports):
- padding, margin, gap, row-gap og column-gap: bare 0, auto, %, var(), env() og calc() av dem. Ingen egne px, rem eller em.
- font-size (og størrelsen i font): var(--t-*), inherit, eller min(), max(), clamp() og calc() med en --t-* i.
- font-weight (og vekten i font): 400, 500, 600, 800, normal, inherit. 700 er på vei ut (fase 4, PR 2).
- Hver var(--x) uten reserve må være definert i CSS-en eller settes fra JS. En tom variabel gir ingen feilmelding,
  bare feil størrelse (16 px) eller luft 0.
- style="..." i docs/js og docs/index.html: ingen px i padding, margin og gap.

Dagens unntak står i tokens_unntak.txt. Lista kan bare krympe: testen feiler når en ny verdi kommer til, når et unntak
ikke lenger trengs, og når lista er kortere enn MAKS (da senkes MAKS, så tallet aldri går opp igjen)."""
import collections
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from pikselsjekk import regler, uten_kommentarer  # noqa: E402

UNNTAK = Path(__file__).resolve().parent / "tokens_unntak.txt"
# Senkes når lista blir kortere, aldri heves. Hevet én gang, 26.11.2026, da main (designfase 3, runde 4 og 5) ble flettet
# inn med tre verdier som alt var på skjermen: 9 px over «LANG SJØ UTE» og reservestørrelsene for surfetallet (før 165 og 62).
MAKS = {"avstand": 166, "skrift": 64, "vekt": 29, "js": 4}
AVSTAND = re.compile(r"^(padding|margin)(-|$)|^(gap|row-gap|column-gap)$")
MED_ENHET = re.compile(r"(?<![\w.#-])-?(?:\d+\.?\d*|\.\d+)(?:px|r?em|ch|ex|[dsl]?v[whib]|cq[whib]|vmin|vmax|pt|cm|mm)\b")
VEKTER = {"400", "500", "600", "800", "normal", "inherit"}
TILLATT_SKRIFT = re.compile(r"^(inherit|var\(--t-[\w-]+\)|(?:min|max|clamp|calc)\(.*var\(--t-[\w-]+\).*\))$")
# settes av nettleseren eller en annen fil, ikke i docs/css: ingen i dag
KJENTE_VAR = set()


def er_tall_uten_null(v):
    return [x for x in MED_ENHET.findall(v) if float(re.match(r"-?[\d.]+", x).group(0)) != 0]


def css_funn(fil, css):
    """[(slag, fil, selektor, egenskap, verdi)] for alt som ikke er en variabel."""
    ut = []
    for _linje, rundt, sel, dekl in regler(css):
        if sel.startswith(("@font-face", "@page")) or any("keyframes" in a for a in rundt):
            continue
        sel = " ".join(sel.split())
        for egenskap, verdi in dekl:
            if AVSTAND.match(egenskap) and er_tall_uten_null(verdi):
                ut.append(("avstand", fil, sel, egenskap, verdi))
            vekt = storrelse = None
            if egenskap == "font-size":
                storrelse = verdi
            elif egenskap == "font-weight":
                vekt = verdi
            elif egenskap == "font" and verdi != "inherit" and not verdi.startswith("-apple-system"):   # systemets tekststørrelse (HIG 4)
                m = re.match(r"^(?:(?:italic|normal)\s+)?(?:(\d{3}|bold|normal)\s+)?((?:[\w-]+\([^/]*\))|[^\s/]+)(?:\s*/|\s)", verdi)
                assert m, f"{fil}: leser ikke font: {verdi}"
                vekt, storrelse = m.group(1), m.group(2)
            if storrelse is not None and not TILLATT_SKRIFT.match(storrelse):
                ut.append(("skrift", fil, sel, egenskap, verdi))
            if vekt is not None and vekt not in VEKTER:
                ut.append(("vekt", fil, sel, egenskap, verdi))
    return ut


def js_funn(fil, kode):
    ut = []
    for m in re.finditer(r"style=\\?([\"'])(.*?)\\?\1", kode):
        for d in re.split(r";(?![^{]*\})", m.group(2)):
            if ":" in d:
                p, v = d.split(":", 1)
                if AVSTAND.match(p.strip()) and er_tall_uten_null(v):
                    ut.append(("js", fil, "style", p.strip(), " ".join(v.split())))
    for m in re.finditer(r"\.style\.((?:padding|margin)\w*|gap|rowGap|columnGap)\s*=\s*([^;\n]+)", kode):
        if er_tall_uten_null(m.group(2)):
            ut.append(("js", fil, "style", m.group(1), m.group(2).strip()))
    return ut


def udefinerte(css, kode):
    """Variabler som brukes uten reserve og aldri får en verdi. css og kode er {fil: tekst}."""
    ren = {f: uten_kommentarer(t) for f, t in css.items()}
    definert = set(KJENTE_VAR)
    for t in list(ren.values()) + list(kode.values()):
        definert |= set(re.findall(r"(--[\w-]+)\s*:", t))
        definert |= set(re.findall(r"setProperty\(\s*[\"'`](--[\w-]+)", t))
    ut = []
    for f, t in list(ren.items()) + list(kode.items()):
        for m in re.finditer(r"var\(\s*(--[\w-]+)\s*([,)])", t):
            if m.group(2) == ")" and m.group(1) not in definert:
                ut.append((f, m.group(1)))
    return sorted(set(ut))


def les_unntak(tekst):
    ut = []
    for nr, linje in enumerate(tekst.splitlines(), 1):
        if linje.strip() and not linje.startswith("#"):
            deler = linje.split("\t")
            assert len(deler) == 5 and deler[0] in MAKS, f"tokens_unntak.txt linje {nr}: {linje!r}"
            ut.append(tuple(deler))
    return ut


def feil(funn, unntak, maks):
    a, b = collections.Counter(funn), collections.Counter(unntak)
    ut = [f"ny verdi utenfor variablene: {' | '.join(x)}" for x in sorted((a - b).elements())]
    ut += [f"unntaket trengs ikke lenger, ta det ut av tokens_unntak.txt: {' | '.join(x)}" for x in sorted((b - a).elements())]
    n = collections.Counter(x[0] for x in unntak)
    for slag, tak in maks.items():
        if n[slag] > tak:
            ut.append(f"lista over {slag} har vokst: {n[slag]} unntak, taket er {tak}")
        elif n[slag] < tak:
            ut.append(f"lista over {slag} er kortere: senk MAKS fra {tak} til {n[slag]}")
    return ut


def les_docs():
    css = {p.name: p.read_text(encoding="utf-8") for p in sorted((ROOT / "docs" / "css").glob("*.css"))}
    kode = {p.name: p.read_text(encoding="utf-8") for p in sorted((ROOT / "docs" / "js").glob("*.js"))}
    for p in sorted((ROOT / "docs").glob("*.html")):
        t = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S)
        for nr, blokk in enumerate(re.findall(r"<style[^>]*>(.*?)</style>", t, re.S)):
            css[f"{p.name} <style>" + (f" {nr + 1}" if nr else "")] = blokk
        kode[p.name] = re.sub(r"<style[^>]*>.*?</style>", "", t, flags=re.S)
    return css, kode


def alle_funn(css, kode):
    return [x for f, t in css.items() for x in css_funn(f, t)] + [x for f, t in kode.items() for x in js_funn(f, t)]


def selvtest():
    """Testen må kunne bli rød."""
    f = lambda css: [(x[0], x[3], x[4]) for x in css_funn("x.css", css)]   # noqa: E731
    assert f(".a{margin:0 auto;padding:var(--s2) calc(-1 * var(--s3)) 5%;gap:0px}") == []
    assert f(".a{padding:calc(var(--s2) + env(safe-area-inset-top,0px))}") == []
    assert f("@media (min-width:1px){@container (max-width:9px){.a{margin-top:7px}}}") == [("avstand", "margin-top", "7px")]
    assert f("@supports (gap:1px){.a{gap:.5em}}") == [("avstand", "gap", ".5em")]
    assert f(".a{width:7px;top:3px;box-shadow:0 1px 2px red;transform:translate(4px)} /* .b{margin:7px} */") == []
    assert f("@keyframes k{from{margin:7px}} @font-face{font-weight:100 800}") == []
    assert f(".a{font-size:var(--t-brod)} .b{font-size:min(var(--t-tall), 40vw)} .c{font-size:inherit;font:inherit}") == []
    assert f(".a{font-size:13px}") == [("skrift", "font-size", "13px")] and f(".a{font-size:var(--fs-body)}") == [("skrift", "font-size", "var(--fs-body)")]
    assert f(".a{font:700 13px/1.4 var(--mono)}") == [("skrift", "font", "700 13px/1.4 var(--mono)"), ("vekt", "font", "700 13px/1.4 var(--mono)")]
    assert f(".a{font:var(--t-brod)/1.4 var(--mono);font-weight:800}") == [] and f(".a{font-weight:900}") == [("vekt", "font-weight", "900")]
    assert js_funn("x.js", 'h = `<p style="margin:8px 0;width:3px">`; e.style.paddingTop = "4px"') == [("js", "x.js", "style", "margin", "8px 0"), ("js", "x.js", "style", "paddingTop", '"4px"')]
    assert udefinerte({"a.css": ":root{--a:1px} .x{top:var(--a);left:var(--b, 0px);right:var(--c);bottom:var(--d)} /* --c:1px */"}, {"a.js": 'e.style.setProperty("--d", 1)'}) == [("a.css", "--c")]
    x, tak = ("avstand", "a.css", ".a", "margin", "7px"), {"avstand": 1, "skrift": 0, "vekt": 0, "js": 0}
    assert feil([x], [x], tak) == []
    assert len(feil([x, x], [x], tak)) == 1 and "ny verdi" in feil([x, x], [x], tak)[0]
    assert any("trengs ikke" in e for e in feil([], [x], tak))
    assert any("vokst" in e for e in feil([x, x], [x, x], tak)) and any("senk MAKS" in e for e in feil([], [], tak))


def main():
    selvtest()
    css, kode = les_docs()
    funn = alle_funn(css, kode)
    if "--skriv" in sys.argv:   # skriv lista på nytt (bare til å ta UT unntak; taket MAKS stopper det motsatte)
        hode = [x for x in UNNTAK.read_text(encoding="utf-8").splitlines() if x.startswith("#")] if UNNTAK.exists() else []
        UNNTAK.write_text("\n".join(hode + ["\t".join(x) for x in sorted(funn)]) + "\n", encoding="utf-8")
    tomme = udefinerte(css, kode)
    assert not tomme, f"variabler som brukes, men aldri får en verdi: {tomme}"
    unntak = les_unntak(UNNTAK.read_text(encoding="utf-8"))
    f = feil(funn, unntak, MAKS)
    assert not f, "designvariablene (se toppen av fetcher/test_tokens.py):\n  " + "\n  ".join(f)
    n = collections.Counter(x[0] for x in unntak)
    print("Designvariablene: " + ", ".join(f"{n[k]} unntak for {k}" for k in MAKS) + ", alle var() er definert - OK")


if __name__ == "__main__":
    main()
    print("Alle tester ok")
