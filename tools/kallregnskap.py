"""Kallregnskap for henteren (S6, ROADMAP seksjon S, 16.10.2026): kall per kjøring, per time, per døgn og per
måned per kilde, regnet fra spots.json, mot vilkårene til kildene.

Vilkår (lest 16.10.2026):
- Open-Meteo, gratis API (open-meteo.com/en/terms og /en/pricing): ikke-kommersiell bruk, under 10 000 kall per
  døgn, 5 000 per time og 600 per minutt (og 300 000 per måned, «ikke håndhevet ennå»). «Requests for data
  covering more than 10 weather variables or extending over a period of more than 2 weeks for a single location
  are considered multiple API calls … fractional counts are used» (2 uker og 15 variabler = 1,5 kall; 4 uker = 3,0).
  Et samlekall med flere koordinater teller per punkt. Vår vekt per punkt: max(1, variabler/10) × max(1, dager/14)
  = 1,0 × 16/14 = 1,14 for både svell (10 variabler) og vind (4 variabler).
- met.no (api.met.no/doc/TermsOfService): ingen tallfestet grense - «ikke overbelast», identifiser deg (User-Agent),
  maks 4 desimaler i koordinatene, respekter Expires; uformelt ca. 20 kall/s før 429.
- BarentsWatch (bølgevarsel): ingen formelle grenser; NLOD, kreditering i appen («data via BarentsWatch»).
- Kartverket (tidevann): ingen dokumentert grense.

Antakelser: én kjøring hver 3. time (8 per døgn, forecast.yml), alle Open-Meteo-kall i én kjøring kan falle innenfor
samme minutt og time (verste fall), hvert unike punkt hentes én gang per kjøring (deling bare på identiske punkt,
som S1/S6). Fremskrivningen til 30/100/300 spots skalerer snittet per spot fra spots.json i dag (hver ny spot får
egne punkt - forsiktig anslag), og regner én S6-jobb per 10 spots (en region) for logg- og token-kallene.

  python tools/kallregnskap.py            tabell (markdown) for spots.json i dag og 30/100/300 spots"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_PER_DAY = 8
OM_DAYS, OM_MARINE_VARS, OM_WIND_VARS = 16, 10, 4
OM_MARINE_MODELS = 2          # GFS Wave + standardmodellen (sources.openmeteo_prefetch)
OM_BATCH = 10                 # punkter per samlekall (sources.OPENMETEO_BATCH)
LIMITS = {"Open-Meteo": {"minutt": 600, "time": 5000, "døgn": 10000, "måned": 300000}}
METNO_INFORMAL_PER_S = 20


def om_weight(n_vars, days=OM_DAYS):
    return max(1.0, n_vars / 10) * max(1.0, days / 14)


def _key(p):
    return (round(p["lat"], 4), round(p["lon"], 4))


def regnskap(spots, jobs=1):
    """Kall per kjøring per kilde for en liste aktive spots (spots.json-format)."""
    marine = {_key(s["offshore"]) for s in spots} | {_key(s["offshore_longrange"]) for s in spots if s.get("offshore_longrange")}
    wind = {_key(s["spot"]) for s in spots}
    om_points = len(marine) * OM_MARINE_MODELS + len(wind)
    om_weighted = len(marine) * OM_MARINE_MODELS * om_weight(OM_MARINE_VARS) + len(wind) * om_weight(OM_WIND_VARS)
    om_http = OM_MARINE_MODELS * math.ceil(len(marine) / OM_BATCH) + math.ceil(len(wind) / OM_BATCH)
    bw = sum(1 for s in spots for k in ("barentswatch_point", "barentswatch_point_near", "barentswatch_point_shadow") if s.get(k))
    return {
        "spots": len(spots),
        "Open-Meteo": {"http": om_http, "punkt": om_points, "vektet": round(om_weighted, 1)},
        "met.no": 3 * len(spots),                   # hav (spot), hav (ute), vind
        "BarentsWatch": bw + jobs,                  # punktene + ett token per jobb
        "Kartverket": len(spots),
        "GitHub (logger)": jobs + (1 if jobs > 1 else 0),   # hver jobb + samlejobben
    }


def per_day(r):
    om = r["Open-Meteo"]["vektet"]
    return {"minutt": om, "time": om, "døgn": om * RUNS_PER_DAY, "måned": om * RUNS_PER_DAY * 30}


def scaled(base, n):
    """Fremskrivning til n spots: snittet per spot fra spots.json i dag, én jobb per 10 spots."""
    f = n / base["spots"]
    jobs = max(1, math.ceil(n / 10))
    om = base["Open-Meteo"]
    return {
        "spots": n,
        "Open-Meteo": {"http": math.ceil(om["http"] * f), "punkt": round(om["punkt"] * f), "vektet": round(om["vektet"] * f, 1)},
        "met.no": round(base["met.no"] * f),
        "BarentsWatch": round((base["BarentsWatch"] - 1) * f) + jobs,
        "Kartverket": round(base["Kartverket"] * f),
        "GitHub (logger)": jobs + (1 if jobs > 1 else 0),
    }


def utnyttelse(r):
    d = per_day(r)
    return {k: d[k] / LIMITS["Open-Meteo"][k] for k in LIMITS["Open-Meteo"]}


def tabell(rows):
    L = ["| Spots | Open-Meteo per kjøring: HTTP / punkt / vektet | Open-Meteo vektet per døgn (grense 10 000) | per time (5 000) | "
         "verste minutt (600) | per måned (300 000) | met.no per kjøring | BarentsWatch per kjøring | Kartverket per kjøring |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        om, d, u = r["Open-Meteo"], per_day(r), utnyttelse(r)
        L.append(f"| {r['spots']} | {om['http']} / {om['punkt']} / {om['vektet']:.0f} | {d['døgn']:.0f} ({u['døgn']:.0%}) | {d['time']:.0f} ({u['time']:.0%}) | "
                 f"{d['minutt']:.0f} ({u['minutt']:.0%}) | {d['måned']:.0f} ({u['måned']:.0%}) | {r['met.no']} | {r['BarentsWatch']} | {r['Kartverket']} |")
    return "\n".join(L)


def main():
    cfg = json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))
    enabled = [s for s in cfg["spots"] if s.get("enabled")]
    base = regnskap(enabled)
    rows = [base] + [scaled(base, n) for n in (30, 100, 300) if n != base["spots"]]
    print(tabell(rows))
    print(f"\nmet.no: ingen tallfestet grense; S6 kjører høyst 4 regionjobber samtidig (max-parallel), hver sekvensielt "
          f"(ca. 0,6 s per kall) - ca. 4-7 kall/s samlet, under det uformelle taket på ca. {METNO_INFORMAL_PER_S}/s.")


if __name__ == "__main__":
    main()
