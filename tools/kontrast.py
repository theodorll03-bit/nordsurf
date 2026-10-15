"""Kontrastsjekk for fargevariablene i docs/css/ui.css (Theodor 15.10.2026, HIG-tillegget punkt 15):
tekst mot flate minst 4,5:1, grafikk (ratingfyll, kystlinje, piler, fokusring) minst 3:1 - i både lys
og mørk. Leser tokenene rett fra CSS-en (ingen nettleser), så en endret farge fanges her med en gang.
Kjør: python tools/kontrast.py (exit 1 ved brudd). Kjøres også av fetcher/test_spotside_browser.py.

Parene som sjekkes er de som faktisk brukes i appen (se ui.css):
- tekst: --ink og --muted på --surface/--raised/--sunken og på glasset (blandet over --surface);
  --rN-ink (ordet) på --raised og --surface; --rN-on (tallet i ruter og ratingstripen) på --rN for N=1..5
  (0 stjerner tegnes som tom rute uten tall, så --r0-on brukes aldri til tekst); --on-selected på --selected;
  --ink på --land og --sea (kompassbokstavene i minikartet).
- grafikk: --rN på --raised (ruter, prikker, stolper); --coast mot --land ELLER --sea (kystlinjen ligger
  mellom dem - den må skille seg fra minst én side); --ink på --land og --sea (piler, vindu); --focus på
  --surface og --raised; --muted på --raised (stiplede rammer for manglende tall)."""
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


def pairs(toks):
    """[(beskrivelse, forgrunn, bakgrunn, minimum)] - fargene oppløst til rgb."""
    surface = rgb(toks["surface"], toks)
    col = lambda name, base=None: rgb(toks[name], toks, base)
    glass = col("glass", surface)
    out = []
    for fg in ("ink", "muted"):
        for bg in ("surface", "raised", "sunken"):
            out.append((f"tekst --{fg} på --{bg}", col(fg), col(bg), TEXT_MIN))
        out.append((f"tekst --{fg} på glasset", col(fg), glass, TEXT_MIN))
    for n in range(6):
        for bg in ("raised", "surface"):
            out.append((f"ordet --r{n}-ink på --{bg}", col(f"r{n}-ink"), col(bg), TEXT_MIN))
        out.append((f"fyll --r{n} på --raised (grafikk)", col(f"r{n}"), col("raised"), GRAPHIC_MIN))
        if n >= 1:
            out.append((f"tallet --r{n}-on på --r{n}", col(f"r{n}-on"), col(f"r{n}"), TEXT_MIN))
    out.append(("tekst --on-selected på --selected", col("on-selected"), col("selected"), TEXT_MIN))
    for bg in ("land", "sea"):
        out.append((f"kompass/piler --ink på --{bg}", col("ink"), col(bg), TEXT_MIN))
    for bg in ("surface", "raised"):
        out.append((f"fokusring --focus på --{bg} (grafikk)", col("focus"), col(bg), GRAPHIC_MIN))
    out.append(("stiplet ramme --muted på --raised (grafikk)", col("muted"), col("raised"), GRAPHIC_MIN))
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
        for p in pairs(toks):
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
