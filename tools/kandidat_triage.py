"""Triage av kandidatene (ROADMAP K del A punkt 4, 15.10.2026). Per kandidat og per kystkilde
(GSHHS f, som fysikken bruker i dag, og OSM-landpolygoner, som i Norge i stor grad er N50 - se
tools/kystdata.py):

- ligger listepinnen på land eller i sjøen, og hvor langt er det til kysten
- stråler hver 5. grad, opptil 40 km: fri strekning over sjø fra kysten og ut (samme kysttoleranse
  som check_spot.py: land de første 300 m fra pinnen hoppes over; land helt gjennom de 300 m = blokkert)
- åpen sektor = største sammenhengende sett retninger med minst 20 km fri strekning; fasing =
  sirkelsnittet av retningene i sektoren
- avvik mot best_swell_dir i lista (kompassord → sirkelsnitt), flagg over 60°

Status (fra OSM-kjøringen, GSHHS vises ved siden av) - første som slår til:
  posisjon: over 300 m inne på land, over 1 km ute i sjøen, eller ingen åpen sektor
  vern:     vern_mistanke fra lista, eller pinnen ligger i (eller innen 200 m av) et verneområde der
            forskriften har ferdsels- eller surfeforbud for sjø eller strand (data/kandidater/vern.json)
  sjekk:    anslått posisjon (coord_confidence estimated), svak dokumentasjon, avvik over 60°,
            150-300 m inne på land, åpen sektor smalere enn 10°, eller forbud for sjø/strand i et
            verneområde 200 m-2 km unna (pinnen er ubekreftet - kan ligge i området)
  Verneområder 600 m-2 km unna der forskriften ikke er lest, står som «vern ikke lest» i hvorfor.
  klar:     ellers

Skriver data/kandidater/triage.json og triage.md. Kjør: python tools/kandidat_triage.py"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import Point, box

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import kystdata  # noqa: E402

KAND = ROOT / "data" / "kandidater" / "kandidater.json"
VERN = ROOT / "data" / "kandidater" / "vern.json"
OUT_JSON = ROOT / "data" / "kandidater" / "triage.json"
OUT_MD = ROOT / "data" / "kandidater" / "triage.md"
SPOTS = ROOT / "spots.json"

RAY_STEP_DEG = 5
RAY_MAX_M = 40000
SAMPLE_M = 25
OPEN_MIN_M = 20000
COAST_FUZZ_M = 300
SEA_MAX_M = 1000
LAND_CHECK_M, LAND_POS_M = 150, 300
AVVIK_FLAGG = 60
VERN_NEAR_M = 200
SECTOR_MIN_DEG = 10   # smalere åpen sektor (f.eks. én stråle) er støy, ikke en fasing → sjekk (fysikk-kontrollør 15.10)
KILDER = ("osm", "gshhs")
COMPASS = {n: i * 22.5 for i, n in enumerate("N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split())}


def circ_mean(degs):
    if not degs:
        return None
    s = sum(math.sin(math.radians(d)) for d in degs)
    c = sum(math.cos(math.radians(d)) for d in degs)
    if abs(s) < 1e-9 and abs(c) < 1e-9:
        return None
    return round(math.degrees(math.atan2(s, c)) % 360, 1)


def angle_diff(a, b):
    d = abs((a - b) % 360)
    return min(d, 360 - d)


def parse_compass(txt):
    """«NW», «W/NW», «SW-W», «NW (SW-N window)» → sirkelsnitt av kompassordene (før parentes); ukjent → None."""
    if not txt or txt.strip().lower() == "unknown":
        return None
    main = txt.split("(")[0]
    toks = re.findall(r"\b(NNE|ENE|ESE|SSE|SSW|WSW|WNW|NNW|NE|SE|SW|NW|N|E|S|W)\b", main.upper())
    return circ_mean([COMPASS[t] for t in toks])


def local_land(land, lat, lon, half_deg=0.5):
    """Land innenfor ca. 50 km (half_deg breddegrader), i meter i en asimut-ekvidistant projeksjon sentrert på pinnen."""
    dlat, dlon = half_deg, half_deg / math.cos(math.radians(lat)) * 1.05
    clip = shapely.clip_by_rect(land, lon - dlon, lat - dlat, lon + dlon, lat + dlat)
    tr = Transformer.from_crs(4326, f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m", always_xy=True)
    g = shapely.transform(clip, lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1])))
    edge = shapely.transform(box(lon - dlon, lat - dlat, lon + dlon, lat + dlat).exterior,
                             lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1])))
    return g, edge


def rays(g):
    """Fri strekning (m) per retning: fra første sjøpunkt innen kysttoleransen til første land."""
    shapely.prepare(g)
    out = {}
    d = np.arange(0, RAY_MAX_M + COAST_FUZZ_M + SAMPLE_M, SAMPLE_M, dtype=float)
    for b in range(0, 360, RAY_STEP_DEG):
        x, y = d * math.sin(math.radians(b)), d * math.cos(math.radians(b))
        land = shapely.contains_xy(g, x, y)
        sea_idx = np.flatnonzero(~land)
        if not len(sea_idx) or d[sea_idx[0]] > COAST_FUZZ_M:
            out[b] = 0.0
            continue
        s = sea_idx[0]
        after = np.flatnonzero(land[s:])
        free = (d[s + after[0]] - d[s]) if len(after) else (d[-1] - d[s])
        out[b] = float(min(free, RAY_MAX_M))
    return out


def open_sector(free):
    dirs = sorted(free)
    ok = [b for b in dirs if free[b] >= OPEN_MIN_M]
    if not ok:
        return None
    runs = []
    for b in ok:
        if runs and b - runs[-1][-1] == RAY_STEP_DEG:
            runs[-1].append(b)
        else:
            runs.append([b])
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == 360 - RAY_STEP_DEG:
        runs[0] = runs.pop() + runs[0]
    run = max(runs, key=len)
    return {"fra": run[0], "til": run[-1], "bredde": (len(run) - 1) * RAY_STEP_DEG, "fasing": circ_mean(run)}


def analyse(land, lat, lon):
    g, edge = local_land(land, lat, lon)
    o = Point(0, 0)
    on_land = bool(g.contains(o))
    coast = g.boundary.difference(edge.buffer(1)) if not g.is_empty else None
    dist = round(coast.distance(o)) if coast is not None and not coast.is_empty else None
    free = rays(g)
    sec = open_sector(free)
    return {"paa_land": on_land, "kyst_m": dist, "sektor": sec, "fri_m": {str(b): round(v) for b, v in free.items()}}


def _forbud_txt(h, r):
    per = f"{r['fra']}–{r['til']}" if r.get("fra") else "hele året"
    return f"{h['navn']} ({h['avstand_m']} m): {r['type']} {per} ({r.get('gjelder')})"


def vern_hits(vern, kid):
    """(nær, i nærheten, ulest): forbud for sjø/strand i et verneområde innen 200 m av pinnen (→ vern),
    200 m-2 km (→ minst sjekk - pinnen er ubekreftet), og verneområder innen 2 km der forskriften ikke er lest."""
    near, around, unread = [], [], []
    for h in (vern.get("kandidater", {}).get(kid) or []):
        d = h.get("avstand_m")
        if not h.get("lest"):
            unread.append(f"{h['navn']} ({d} m)")
            continue
        for r in h.get("restriksjoner") or []:
            if r.get("stedsbundet"):
                continue   # gjelder bare et navngitt sted inne i området (f.eks. Rott i Jærstrendene)
            if r.get("type") in ("ferdselsforbud", "ilandstigningsforbud", "surfeforbud") and r.get("gjelder") in ("sjø", "strand", "begge"):
                (near if d is not None and d <= VERN_NEAR_M else around).append(_forbud_txt(h, r))
    return near, around, unread


def status_for(k, a, avvik, vh):
    near, around, unread = vh
    flagg = []
    pos = []
    if a["paa_land"] and a["kyst_m"] is not None and a["kyst_m"] > LAND_POS_M:
        pos.append(f"{a['kyst_m']} m inne på land")
    if not a["paa_land"] and a["kyst_m"] is not None and a["kyst_m"] > SEA_MAX_M:
        pos.append(f"{a['kyst_m']} m ute i sjøen")
    if not a["sektor"]:
        pos.append("ingen åpen sektor (≥ 20 km)")
    if k.get("vern_mistanke"):
        flagg.append("vern_mistanke i lista")
    flagg += ["vern: " + t for t in near]
    if unread:
        flagg.append(f"vern ikke lest: {len(unread)} område(r) 600 m-2 km unna ({', '.join(unread[:3])}{' …' if len(unread) > 3 else ''})")
    sj = []
    sj += ["forbud i nærheten: " + t for t in around]
    if a["sektor"] and a["sektor"]["bredde"] < SECTOR_MIN_DEG:
        sj.append(f"smal åpen sektor ({a['sektor']['bredde']}°)")
    if k.get("coord_confidence") == "estimated":
        sj.append("anslått posisjon")
    if k.get("dokumentasjon") == "svak":
        sj.append("svak dokumentasjon")
    if avvik is not None and avvik > AVVIK_FLAGG:
        sj.append(f"avvik {avvik:.0f}° mot best_swell_dir")
    if a["paa_land"] and a["kyst_m"] is not None and LAND_CHECK_M <= a["kyst_m"] <= LAND_POS_M:
        sj.append(f"{a['kyst_m']} m inne på land")
    if pos:
        return "posisjon", pos + sj + flagg
    if k.get("vern_mistanke") or near:
        return "vern", flagg + sj
    if sj:
        return "sjekk", sj + flagg
    return "klar", flagg


def main():
    kand = json.loads(KAND.read_text(encoding="utf-8"))["kandidater"]
    vern = json.loads(VERN.read_text(encoding="utf-8")) if VERN.exists() else {}
    spots = {s["id"]: s for s in json.loads(SPOTS.read_text(encoding="utf-8"))["spots"]}
    lands = {k: kystdata.land(k) for k in KILDER}
    res = {}
    for i, k in enumerate(kand):
        p = k["pin_liste"]
        best = parse_compass(k["hint"].get("best_swell_dir"))
        row = {"id": k["id"], "name": k["name"], "region": k["region"], "status_liste": k["status"], "best_swell_dir_grader": best}
        for src in KILDER:
            a = analyse(lands[src], p["lat"], p["lon"])
            fas = a["sektor"]["fasing"] if a["sektor"] else None
            avvik = round(angle_diff(fas, best)) if fas is not None and best is not None else None
            st, why = status_for(k, a, avvik, vern_hits(vern, k["id"]))
            row[src] = {**a, "avvik": avvik, "status": st, "hvorfor": why}
        if k.get("nordsurf_id"):
            s = spots[k["nordsurf_id"]]
            row["spots_json"] = {"facing": s.get("facing"), "swell_window": s.get("swell_window")}
        row["status"] = row["osm"]["status"]
        res[k["id"]] = row
        print(f"{i + 1:3}/{len(kand)} {k['id']:34} osm {row['osm']['status']:8} gshhs {row['gshhs']['status']:8} "
              f"fasing {row['osm']['sektor']['fasing'] if row['osm']['sektor'] else '-'}/{row['gshhs']['sektor']['fasing'] if row['gshhs']['sektor'] else '-'}", flush=True)
    OUT_JSON.write_text(json.dumps({"_info": __doc__.split("\n\n")[0], "kandidater": res}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_md(res, kand)


def fmt_deg(v):
    return "–" if v is None else f"{v:.0f}°"


def fmt_sec(a):
    s = a["sektor"]
    return f"{s['fra']}–{s['til']} ({s['fasing']:.0f}°)" if s else "ingen"


def vern_forslag_md():
    """Theodor 16.10.2026 (3b): vernesjekk på posisjonsforslagene (data/kandidater/posisjoner.json «forslag»). Naturbase
    hentes rundt SELVE forslaget (innen 2 km, mellomlagret i privat/kandidater/bevis/vern/naturbase_<id>_forslag_<lat>_<lon>.json)
    - ikke rundt listepinnen, som kan ligge km unna (kontrollør 16.10: Bunes er flyttet 2 km). Restriksjonene leses fra
    vern_forskrifter.json; et verneområde innen 200 m der forskriften ikke er lest, står som «forskrift ikke lest»."""
    pos_f = ROOT / "data" / "kandidater" / "posisjoner.json"
    fs_f = ROOT / "data" / "kandidater" / "vern_forskrifter.json"
    raw_d = ROOT / "privat" / "kandidater" / "bevis" / "vern"
    if not pos_f.exists() or not fs_f.exists():
        return []
    import time
    from shapely.geometry import shape
    import kandidat_vern as kv
    to = Transformer.from_crs(4326, 25833, always_xy=True)
    pos = json.loads(pos_f.read_text(encoding="utf-8"))["kandidater"]
    forskr = json.loads(fs_f.read_text(encoding="utf-8"))["forskrifter"]
    rows = []
    for kid, p in sorted(pos.items()):
        for f in p.get("forslag") or []:
            raw = raw_d / f"naturbase_{kid}_forslag_{f['lat']:.5f}_{f['lon']:.5f}.json"
            if not raw.exists():
                raw_d.mkdir(parents=True, exist_ok=True)
                raw.write_text(json.dumps(kv.naturbase(f["lat"], f["lon"]), ensure_ascii=False), encoding="utf-8")
                time.sleep(0.3)
            x, y = to.transform(f["lon"], f["lat"])
            for ft in json.loads(raw.read_text(encoding="utf-8")).get("features", []):
                a = ft["properties"]
                if not ft.get("geometry"):
                    continue
                d = shape(ft["geometry"]).distance(Point(x, y))
                navn = a.get("offisieltNavn") or a.get("navn")
                fid = kv.forskrift_id(a.get("verneforskrift"))
                rs = [r for r in (forskr.get(fid) or {}).get("restriksjoner", [])
                      if (not r.get("verneomrade") or r["verneomrade"] == navn) and not r.get("stedsbundet")
                      and r.get("type") in ("ferdselsforbud", "surfeforbud") and r.get("gjelder") in ("sjø", "strand", "begge")]
                if rs:
                    hva = "; ".join(f"{r['type']} {r['fra'] + '–' + r['til'] if r.get('fra') else 'hele året'} ({r['gjelder']})" for r in rs)
                elif fid not in forskr and d <= VERN_NEAR_M:
                    hva = "forskrift ikke lest"
                else:
                    continue
                rows.append(f"| {kid} | {f['satt_av']} ({f.get('sikkerhet') or '–'}, flyttet {f.get('flyttet_m') if f.get('flyttet_m') is not None else '–'} m) | "
                            f"{navn} | {hva} | {'**INNE I**' if d == 0 else f'{d:.0f} m utenfor'} |")
    head = ["", "## Vernesjekk på forslagsposisjonene (Theodor 16.10.2026)", "",
            "Naturbase hentet rundt hvert posisjonsforslag (innen 2 km). Tabellen viser verneområder der forskriften har ferdsels- eller "
            "surfeforbud for sjø/strand, og verneområder innen 200 m der forskriften ikke er lest. Ligger et forslag inne i et område med "
            "forbud, må vern_vurdering.json vurderes på nytt før spoten kan bygges. (Teksten lenger opp gjelder listepinnene.)", ""]
    if not rows:
        return head + ["Ingen av forslagene har et verneområde med forbud innen 2 km."]
    return head + ["| Kandidat | Forslag | Verneområde | Forbud | Avstand |", "|---|---|---|---|---|"] + rows


def write_md(res, kand):
    order = ["posisjon", "vern", "sjekk", "klar"]
    cand = [r for r in res.values() if r["status_liste"] == "kandidat"]
    cnt = {src: {s: sum(1 for r in cand if r[src]["status"] == s) for s in order} for src in KILDER}
    L = ["# Triage av kandidatene (Theodors liste 15.10.2026)", "",
         "Generert av `tools/kandidat_triage.py`. Status fra OSM-kysten (i Norge i stor grad N50), GSHHS f (fysikken i dag) ved siden av. "
         "Fasing = sirkelsnittet av den største sammenhengende sektoren med minst 20 km fri strekning (stråler hver 5. grad, 40 km). "
         "Posisjonen er listepinnen - ikke kontrollert ennå (det er del A2). Ingenting her er publisert.", "",
         f"**{len(cand)} kandidater** (de 8 vi har fra før står nederst):", "",
         "| Kyst | " + " | ".join(order) + " |", "|---|" + "---|" * len(order)]
    for src in KILDER:
        L.append(f"| {src} | " + " | ".join(str(cnt[src][s]) for s in order) + " |")
    L += ["", "Til sammenligning (Claudes kjøring med GSHHS f, i Theodors melding): 41 klar, 43 sjekk, 18 posisjon, 5 vern.", ""]
    diff = [r for r in cand if r["osm"]["status"] != r["gshhs"]["status"]]
    L += [f"**Ulik status mellom kystkildene: {len(diff)}** - " + ", ".join(f"{r['id']} ({r['gshhs']['status']}→{r['osm']['status']})" for r in diff), ""]
    L += ["## Trolig feil posisjon (status «posisjon»)", "", "| Kandidat | Region | Pinne | Kyst (OSM) | GSHHS | Sektor OSM | Hvorfor |", "|---|---|---|---|---|---|---|"]
    for r in sorted([r for r in cand if r["status"] == "posisjon"], key=lambda r: (r["region"] or "", r["id"])):
        o, g = r["osm"], r["gshhs"]
        L.append(f"| {r['name']} | {r['region'] or '–'} | {'land' if o['paa_land'] else 'sjø'} | {o['kyst_m']} m | {'land' if g['paa_land'] else 'sjø'} {g['kyst_m']} m | {fmt_sec(o)} | {'; '.join(o['hvorfor'])} |")
    regs = [r for r in json.loads(KAND.read_text(encoding='utf-8'))["regioner_forslag"]] + [None]
    for reg in regs:
        rows = [r for r in cand if r["region"] == reg and r["status"] != "posisjon"]
        if not rows:
            continue
        L += ["", f"## {reg or 'Uten region'}", "", "| Kandidat | Status | GSHHS | Kyst | Sektor OSM | Sektor GSHHS | Lista | Avvik | Hvorfor |", "|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda r: (order.index(r["status"]), r["id"])):
            o, g = r["osm"], r["gshhs"]
            L.append(f"| {r['name']} | {r['status']} | {g['status']} | {'land' if o['paa_land'] else 'sjø'} {o['kyst_m']} m | {fmt_sec(o)} | {fmt_sec(g)} | "
                     f"{fmt_deg(r['best_swell_dir_grader'])} | "
                     f"{'–' if o['avvik'] is None else str(o['avvik']) + '°'} | {'; '.join(o['hvorfor']) or '–'} |")
    L += ["", "## Listas påstander om forbud og vern (punkt 5)", "",
          "- **Pigsty, Orrestranda, Kvassheim: BEKREFTET.** Pinnene ligger i Jærstrendene fuglefredningsområde (0 m). Forskriften "
          "(https://lovdata.no/forskrift/2003-12-12-1675, § 3 B nr. 6 d): «I sjøområda er det forbod mot bruk av vannscooter/vannjet, "
          "andre former for vannmotorsport, bølgjesurfing og bruk av seglbrett f.o.m. 1. oktober t.o.m. 31. mars.» Gjelder sjøområdene "
          "i fuglefredingsområdene, ikke hele landskapsvernområdet.",
          "- **Seines: vern bekreftet, forbud AVKREFTET.** Pinnen ligger i Seinesodden naturreservat (0 m), men forskriften "
          "(https://lovdata.no/forskrift/1997-12-19-1356) har ikke ferdselsforbud - bare forbud mot motorferdsel og brettseiling (seilbrett) "
          "hele året; surfebrett nevnes ikke. Militært område står verken i forskriften eller i Naturbase (ikke sjekket i andre kilder).",
          "- Ellers funnet: **Eggum** (277 m fra Eggum naturreservat) og **The Frog** (579 m fra Nykvåg/Nykan naturreservat) - "
          "«Bruk av … surfebrett … er forbudt» hele året i begge reservatene; om spoten ligger i reservatet avgjøres av posisjonen (A2).",
          ""]
    L += vern_forslag_md()
    kj = [r for r in res.values() if r["status_liste"] == "i_nordsurf"]
    L += ["", "## De 8 vi har fra før (kontroll av metoden - spots.json røres ikke)", "",
          "| Spot | Fasing OSM | Fasing GSHHS | spots.json facing | Vindu i spots.json | Sektor OSM | Kyst (OSM) |", "|---|---|---|---|---|---|---|"]
    for r in kj:
        o, g, s = r["osm"], r["gshhs"], r["spots_json"]
        L.append(f"| {r['name']} | {o['sektor']['fasing'] if o['sektor'] else '–'} | {g['sektor']['fasing'] if g['sektor'] else '–'} | {s['facing']} | {s['swell_window']} | {fmt_sec(o)} | {'land' if o['paa_land'] else 'sjø'} {o['kyst_m']} m |")
    L += ["", "Kilder: kystlinje © OpenStreetMap-bidragsytere (ODbL), GSHHS (Wessel og Smith, LGPL); verneområder © Miljødirektoratet, Naturbase (NLOD)."]
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Skrev {OUT_JSON.relative_to(ROOT)} og {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
