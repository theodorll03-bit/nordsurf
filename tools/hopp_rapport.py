"""Enkelttimer som faller og kommer tilbake (Theodor 16.10.2026, Grøtfjord lørdag 17.10 kl. 13-14): leser en mappe med
forecast.json-filer (én per kjøring - fra git-historikken før 14.10 og varsel-artifactene etter) og finner timer der
stjernene faller minst 2 eller surfehøyden faller minst 60 % i én time og er tilbake timen etter. Hver slik time får
en årsak (første som slår til):

  manglende data     surfehøyde, svell ute eller BarentsWatch-høyde mangler (None) i timen, men ikke i naboene
  kildebytte         høydekilden (BarentsWatch / svell ute) er en annen enn i begge naboene
  svelloppdeling     svellet ute faller over 40 %, mens totalhøyden ute er innen 15 % - GFS bytter svellsystem
  vinduskant         retningsfaktoren (directness) faller over 40 % - svellretningen vingler over en vinduskant
  flat-sperre        Hs ved spoten (etter justering) så vidt under 0,35 m mens naboene er så vidt over (innen 0,15 m)
  vind               vindstraffen/«Blåst ut» slår til bare i timen, svellet er stabilt
  annet

Bare de første 48 timene i hver kjøring telles (det appen viser mest). Skriver markdown til stdout.

  python tools/hopp_rapport.py <mappe med forecast-filer> [fra-dato]"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

H48 = 48
FLAT = 0.35   # rating.FLAT_HS_THRESHOLD


def num(v):
    return v if isinstance(v, (int, float)) else None


def classify(a, h, b):
    for k in ("surf_height", "swell_offshore", "bw_height"):
        if h.get(k) is None and a.get(k) is not None and b.get(k) is not None:
            return "manglende data"
    src = h.get("height_source")
    if src and src != a.get("height_source") and src != b.get("height_source"):
        return "kildebytte"
    sw, swa, swb = num(h.get("swell_offshore")), num(a.get("swell_offshore")), num(b.get("swell_offshore"))
    to, toa, tob = num(h.get("height_offshore")), num(a.get("height_offshore")), num(b.get("height_offshore"))
    if None not in (sw, swa, swb, to, toa, tob) and min(swa, swb) > 0 and sw < 0.6 * min(swa, swb) \
            and abs(to - (toa + tob) / 2) <= 0.15 * max((toa + tob) / 2, 0.1):
        return "svelloppdeling"
    d, da, db = num(h.get("directness")), num(a.get("directness")), num(b.get("directness"))
    if None not in (d, da, db) and min(da, db) > 0 and d < 0.6 * min(da, db):
        return "vinduskant"
    hs, hsa, hsb = num(h.get("height")), num(a.get("height")), num(b.get("height"))
    if None not in (hs, hsa, hsb) and hs < FLAT and min(hsa, hsb) >= FLAT and max(hsa, hsb) - hs <= 0.15:
        return "flat-sperre"
    if h.get("low_reason") == "blown_out" and a.get("low_reason") != "blown_out" and b.get("low_reason") != "blown_out":
        return "vind"
    return "annet"


def dips(hours):
    out = []
    for i in range(1, len(hours) - 1):
        a, h, b = hours[i - 1], hours[i], hours[i + 1]
        sa, s, sb = a.get("stars") or 0, h.get("stars") or 0, b.get("stars") or 0
        ha, hh, hb = num(a.get("surf_height")), num(h.get("surf_height")), num(b.get("surf_height"))
        star_dip = s <= min(sa, sb) - 2
        h_dip = None not in (ha, hb) and min(ha, hb) >= 0.3 and (hh is None or hh <= 0.4 * min(ha, hb))
        if star_dip or h_dip:
            out.append((i, star_dip, h_dip))
    return out


def main():
    folder = Path(sys.argv[1])
    fra = sys.argv[2] if len(sys.argv) > 2 else ""
    files = sorted(folder.glob("*.json"))
    seen = {}
    occ = Counter()
    n_runs = n_hours = 0
    for f in files:
        try:
            fc = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        gen = fc.get("generated", "")
        if gen[:10] < fra:
            continue
        n_runs += 1
        for sp in fc.get("spots", []):
            hours = [h for h in sp.get("hours", []) if h.get("t", "") >= gen[:13]][:H48]
            n_hours += len(hours)
            for i, sd, hd in dips(hours):
                h = hours[i]
                cause = classify(hours[i - 1], h, hours[i + 1])
                key = (sp["id"], h["t"])
                occ[cause] += 1
                if key not in seen or gen > seen[key]["gen"]:
                    seen[key] = {"gen": gen, "cause": cause, "stars": (hours[i - 1].get("stars"), h.get("stars"), hours[i + 1].get("stars")),
                                 "surf": (hours[i - 1].get("surf_height"), h.get("surf_height"), hours[i + 1].get("surf_height")),
                                 "sd": sd, "hd": hd}
    by_cause = Counter(v["cause"] for v in seen.values())
    by_spot = defaultdict(Counter)
    for (sid, _), v in seen.items():
        by_spot[sid][v["cause"]] += 1
    causes = ["svelloppdeling", "vinduskant", "flat-sperre", "kildebytte", "manglende data", "vind", "annet"]
    L = [f"# Enkelttimer som faller og kommer tilbake ({n_runs} kjøringer fra {fra or 'start'}, første 48 t, {n_hours} spot-timer)", "",
         "Fall = stjernene minst 2 under begge naboene, eller surfehøyden ≤ 40 % av begge naboene (naboene ≥ 0,3 m). "
         "Telt per (spot, time) - siste kjøring som viste timen avgjør årsaken; «forekomster» teller hver kjøring.", "",
         "| Årsak | Unike (spot, time) | Forekomster |", "|---|---|---|"]
    for c in causes:
        L.append(f"| {c} | {by_cause[c]} | {occ[c]} |")
    L.append(f"| **sum** | **{sum(by_cause.values())}** | **{sum(occ.values())}** |")
    L += ["", "| Spot | " + " | ".join(causes) + " |", "|---|" + "---|" * len(causes)]
    for sid in sorted(by_spot):
        L.append(f"| {sid} | " + " | ".join(str(by_spot[sid][c]) for c in causes) + " |")
    L += ["", "Eksempler (siste 15):", ""]
    for (sid, t), v in sorted(seen.items(), key=lambda kv: kv[0][1])[-15:]:
        L.append(f"- {sid} {t}: {v['cause']}, stjerner {v['stars']}, surf {v['surf']}")
    print("\n".join(L))


if __name__ == "__main__":
    main()
