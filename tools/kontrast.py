"""Kontrastsjekk for fargevariablene i docs/css/ui.css (Theodor 15.10.2026, HIG-tillegget punkt 15; parene
er lagt om til design B 4.0 «Papir» 12.11.2026, docs/design/b4/SPEC.md §2): tekst mot flate minst 4,5:1,
grafikk og stor tekst minst 3:1 - i både dag og mørketid. Leser tokenene rett fra CSS-en (ingen nettleser),
så en endret farge fanges her med en gang.
Kjør: python tools/kontrast.py (exit 1 ved brudd). Kjøres også av fetcher/test_spotside_browser.py.

Parene som sjekkes er de som faktisk brukes i appen (se ui.css):
- tekst: --ink og --muted på --surface/--raised/--sunken og på glasset (blandet over --surface);
  --rN-ink (ordet) på --raised og --surface; --rN-on (tallet i ruta) på --rN for N=1..5;
  --on-selected på --selected; --ink på --land og --sea (kompassbokstavene i minikartet);
  --on-kartland på --kartland (stedsnavn på land).
- stor tekst og grafikk (3:1): --rN-tall på --surface (tallet alene er stort; korall er bare lov på tekst fra
  24 px fet i dagtema, SPEC §1 regel 2); --r3..--r5 på --raised (fylte ruter); --signal på --surface;
  --kartland mot --surface; --coast mot --land ELLER --sea; --focus på --surface og --raised; --muted på
  --raised (stiplede rammer); --water på --raised (tidevannskurven); --dim på --surface (tekst og pil i mørk
  time, bevisst dempet).
- IKKE krav: --outline-fyllet (--r0..--r2 og tomme ruter) mot flaten. Ruta er pynt; tallet i ruta bærer
  meningen (SPEC §8: farge er aldri eneste bærer), og tallet sjekkes over.
- Tallet i korallruta (--on-signal på --signal) er 4,03:1 om dagen. Theodor 12.11.2026: fargen beholdes, og
  tallet oppå korall er alltid minst 14 px fet, så det regnes som stor tekst (krav 3:1). Gjelder --rN-on på
  --rN der --rN er korall, i begge temaer. Størrelsen står i ui.css (.rute, .uke i, .plot .rs, .klynge .ring)
  og sjekkes ikke her (skriftstørrelser leses ikke). WCAG regner stor tekst fra 14 pt fet (ca. 18,7 px): .rute og
  .uke i (19 px) er over, .plot .rs og .klynge .ring (14 px fet) følger bare Theodors regel.
- --dim og --swell-miss oppå --night (tekst og pil i mørk time): krav 3:1. Dagfargen er #5E5A51 (Theodor 12.11)."""
import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "docs" / "css" / "ui.css"
TEXT_MIN, GRAPHIC_MIN = 4.5, 3.0


def block(css, head):
    i = css.index(head)
    j = css.index("{", i) + 1
    depth = 1
    k = j
    while depth:
        depth += {"{": 1, "}": -1}.get(css[k], 0)
        k += 1
    return css[j:k - 1]


def tokens(body):
    out = {}
    for m in re.finditer(r"--([\w-]+)\s*:\s*([^;]+);", body):
        out[m.group(1)] = m.group(2).strip()
    return out


def rgb(value, toks, base=None):
    """Hex eller rgba() til (r, g, b) i 0-255; rgba blandes over `base` (allerede oppløst)."""
    value = value.strip()
    m = re.fullmatch(r"var\(--([\w-]+)\)", value)
    if m:
        return rgb(toks[m.group(1)], toks, base)
    if value.startswith("#"):
        v = value[1:]
        if len(v) == 3:
            v = "".join(ch * 2 for ch in v)
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"rgba?\(([^)]*)\)", value)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        r, g, b = (float(p) for p in parts[:3])
        a = float(parts[3]) if len(parts) > 3 else 1.0
        if a < 1 and base is not None:
            return tuple(round(a * c + (1 - a) * bc) for c, bc in zip((r, g, b), base))
        return (round(r), round(g), round(b))
    raise ValueError(f"forstår ikke fargen {value!r}")


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = c
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def pairs(toks, tema="lys"):
    """[(beskrivelse, forgrunn, bakgrunn, minimum)] - fargene oppløst til rgb. Gjennomsiktige farger blandes over --surface."""
    surface = rgb(toks["surface"], toks)
    col = lambda name: rgb(toks[name], toks, surface)
    glass = col("glass")
    out = []
    for fg in ("ink", "muted"):
        for bg in ("surface", "raised", "sunken"):
            out.append((f"tekst --{fg} på --{bg}", col(fg), col(bg), TEXT_MIN))
        out.append((f"tekst --{fg} på glasset", col(fg), glass, TEXT_MIN))
    for n in range(6):
        for bg in ("raised", "surface"):
            out.append((f"ordet --r{n}-ink på --{bg}", col(f"r{n}-ink"), col(bg), TEXT_MIN))
        out.append((f"tallet alene --r{n}-tall på --surface (stor tekst)", col(f"r{n}-tall"), surface, GRAPHIC_MIN))
        if n >= 3:
            out.append((f"fyll --r{n} på --raised (grafikk)", col(f"r{n}"), col("raised"), GRAPHIC_MIN))
        if n >= 1:
            korall = toks[f"r{n}"].strip() == "var(--signal)"
            out.append((f"tallet --r{n}-on på --r{n}" + (" (minst 14 px fet = stor tekst, Theodor 12.11)" if korall else ""),
                        col(f"r{n}-on"), col(f"r{n}"), GRAPHIC_MIN if korall else TEXT_MIN))
    out.append(("tekst --on-selected på --selected", col("on-selected"), col("selected"), TEXT_MIN))
    out.append(("stedsnavn --on-kartland på --kartland", col("on-kartland"), col("kartland"), TEXT_MIN))
    for bg in ("land", "sea"):
        out.append((f"kompass/piler --ink på --{bg}", col("ink"), col(bg), TEXT_MIN))
    for bg in ("surface", "raised"):
        out.append((f"fokusring --focus på --{bg} (grafikk)", col("focus"), col(bg), GRAPHIC_MIN))
    out.append(("korall --signal på --surface (stor tekst og grafikk)", col("signal"), surface, GRAPHIC_MIN))
    out.append(("land --kartland mot --surface (grafikk)", col("kartland"), surface, GRAPHIC_MIN))
    out.append(("mørk time --dim på --surface (dempet tekst og pil)", col("dim"), surface, GRAPHIC_MIN))
    for fg in ("dim", "swell-miss"):
        out.append((f"mørk time --{fg} oppå --night (tekst og pil)", col(fg), col("night"), GRAPHIC_MIN))
    out.append(("tekst --muted oppå --night", col("muted"), col("night"), TEXT_MIN))
    out.append(("stiplet ramme --muted på --raised (grafikk)", col("muted"), col("raised"), GRAPHIC_MIN))
    out.append(("tidevannskurven --water på --raised (grafikk)", col("water"), col("raised"), GRAPHIC_MIN))
    # kystlinjen: nok mot minst én av sidene
    coast = col("coast")
    best = max(ratio(coast, col("land")), ratio(coast, col("sea")))
    out.append(("kystlinje --coast mot --land eller --sea (beste side, grafikk)", None, None, GRAPHIC_MIN, best))
    return out


def check(verbose=True):
    css = CSS.read_text(encoding="utf-8")
    light = tokens(block(css, ":root{"))
    dark = dict(light)
    dark.update(tokens(block(css, ':root[data-theme="dark"]')))
    # mørk under prefers-color-scheme skal være identisk med [data-theme="dark"]
    media = tokens(block(css, ':root:not([data-theme="light"])'))
    diff = {k for k in media if media[k] != dark.get(k)} | {k for k in dark if k not in light or dark[k] != light[k]} - set(media)
    diff -= {k for k in dark if k in light and dark[k] == light[k]}
    failures = []
    for name, toks in (("lys", light), ("mørk", dark)):
        for p in pairs(toks, name):
            r = p[4] if len(p) > 4 else ratio(p[1], p[2])
            ok = r >= p[3] - 1e-9
            if verbose:
                print(f"{name:5} {r:5.2f}:1 {'ok  ' if ok else 'FEIL'} {p[0]} (krav {p[3]:.1f})")
            if not ok:
                failures.append(f"{name}: {p[0]} = {r:.2f}:1, krav {p[3]:.1f}:1")
    if diff:
        failures.append(f"mørk under prefers-color-scheme og [data-theme=dark] er ikke like: {sorted(diff)}")
    return failures


if __name__ == "__main__":
    f = check(verbose="-q" not in sys.argv)
    if f:
        print("\nKONTRASTBRUDD:\n  " + "\n  ".join(f))
        sys.exit(1)
    print("Kontrast OK: alle par over kravet i lys og mørk.")
