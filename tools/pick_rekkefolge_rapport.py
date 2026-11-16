#!/usr/bin/env python3
"""T2 (10.11.2026): før/etter-tabell for kilden til svellretningen (`dir_offshore`).

Spørsmålet fra 25.09.2026 var om rekkefølgen i `pick()` skulle byttes, slik at
Open-Meteo sitt svellfelt går foran met.no sin samlede sjøtilstand. Byttet ble
gjort samme dag (0fe002b): `dir_offshore` kommer nå BARE fra svellfeltet.
Denne rapporten viser hva den gamle rekkefølgen (met.no først) ville gitt for
de samme timene, så det er mulig å se hva byttet betyr i stjerner.

Endrer ingenting. Leser de publiserte detaljfilene (docs/data/spots/<id>.json
fra GitHub Pages, én GET per spot med --hent) og met.no Oceanforecast i
havpunktet (ett kall per havpunkt, lagres i --cache så omkjøring er uten kall).

    python3 tools/pick_rekkefolge_rapport.py --live-dir <mappe> --cache <fil> [--hent]
"""
import argparse
import datetime as dt
import json
import statistics
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))
import backtest  # noqa: E402
import rating  # noqa: E402
import sources  # noqa: E402
import sun  # noqa: E402

PAGES = "https://theodorll03-bit.github.io/nordsurf/data/spots/{}.json"
OUT = ROOT / "data" / "backtest" / "t2_pick_rekkefolge_2026-11-10.md"
TIMER = 48


def utc(t):
    return dt.datetime.strptime(t, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)


def angle_diff(a, b):
    return abs(((a - b + 180) % 360) - 180)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-dir", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--hent", action="store_true")
    a = ap.parse_args()
    live, cache_p = Path(a.live_dir), Path(a.cache)
    cache = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {}

    spots = {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
    exposure = json.loads((ROOT / "data" / "exposure_baseline.json").read_text(encoding="utf-8"))
    calib_p = ROOT / "data" / "bw_calibration.json"
    calib = json.loads(calib_p.read_text(encoding="utf-8")) if calib_p.exists() else {}

    rows, run, avvik = [], None, 0
    sen = {"n": 0, "ned": 0, "lik": 0, "opp": 0, "to": 0, "dd": []}
    for sid, s in spots.items():
        if not s.get("enabled", True):
            continue
        f = live / f"{sid}.json"
        if not f.exists() and a.hent:
            try:
                with urllib.request.urlopen(PAGES.format(sid), timeout=20) as r:
                    f.write_bytes(r.read())
            except Exception as e:  # mangler på Pages: hopp over, si fra
                print(f"{sid}: ingen detaljfil ({e})", file=sys.stderr)
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        run = run or d.get("generated")
        o = s["offshore"]
        key = f"{round(o['lat'], 4)},{round(o['lon'], 4)}"
        if key not in cache:
            if not a.hent:
                continue
            cache[key] = {"hentet": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                          "dir": {k: v.get("dir") for k, v in sources.metno_ocean(o["lat"], o["lon"]).items()}}
            cache_p.write_text(json.dumps(cache), encoding="utf-8")
        met = cache[key]["dir"]
        spot = backtest.prepare_spot(sid, spots, exposure, calib)
        hours = sorted((h for h in d["hours"] if met.get(h["t"]) is not None and h.get("dir_offshore") is not None), key=lambda h: h["t"])
        if not hours:
            continue
        t0 = utc(hours[0]["t"])
        for h in hours:  # resten av met.no-horisonten, mest uten BarentsWatch: bare summert
            if utc(h["t"]) >= t0 + dt.timedelta(hours=TIMER) and h.get("bw_height") is None:
                e, g = rating.rate(dict(h), spot)["stars"], dict(h)
                g["dir_offshore"] = met[h["t"]]
                f_ = rating.rate(g, spot)["stars"]
                sen["n"] += 1
                sen["ned" if e < f_ else "opp" if e > f_ else "lik"] += 1
                sen["to"] += abs(e - f_) >= 2
                sen["dd"].append(angle_diff(met[h["t"]], h["dir_offshore"]))
        hours = [h for h in hours if utc(h["t"]) < t0 + dt.timedelta(hours=TIMER)]
        r = {"id": sid, "name": s["name"], "n": len(hours), "dd": [], "ned": 0, "lik": 0, "opp": 0, "to": 0, "lys_for": 0, "lys_etter": 0, "bw": 0, "fra": hours[0]["t"]}
        for h in hours:
            etter = rating.rate(dict(h), spot)["stars"]
            if h.get("stars") is not None and etter != h["stars"]:
                avvik += 1
            g = dict(h)
            g["dir_offshore"] = met[h["t"]]
            for_ = rating.rate(g, spot)["stars"]
            r["dd"].append(angle_diff(met[h["t"]], h["dir_offshore"]))
            r["bw"] += h.get("bw_height") is not None
            r["ned" if etter < for_ else "opp" if etter > for_ else "lik"] += 1
            r["to"] += abs(etter - for_) >= 2
            if sun.light(s["spot"]["lat"], s["spot"]["lon"], utc(h["t"])) != "mørkt":
                r["lys_for"] += for_ >= 1
                r["lys_etter"] += etter >= 1
        rows.append(r)

    n = sum(r["n"] for r in rows)
    alle_dd = [x for r in rows for x in r["dd"]]
    tot = {k: sum(r[k] for r in rows) for k in ("ned", "lik", "opp", "to", "lys_for", "lys_etter", "bw")}
    L = ["# T2: kilden til svellretningen (`pick()`), før og etter", "",
         f"Kjøring {run}. De første {TIMER} timene der både varselet og met.no har retning, fra {min(r['fra'] for r in rows)}. "
         f"{len(rows)} spots, {n} timer. Laget av `tools/pick_rekkefolge_rapport.py`. Ingenting er endret.", "",
         "## Kort svar", "",
         "- **Byttet er allerede gjort.** Siden 25.09.2026 (0fe002b) kommer `dir_offshore` bare fra Open-Meteo sitt svellfelt. "
         "met.no sin samlede sjøtilstand (svell og vindsjø blandet) brukes ikke lenger til svellretning. Det er ingenting igjen å bytte.",
         "- De faste observasjonene fra og med 26.09 og alt som er kalibrert siden, er gjort med dagens rekkefølge. Bare Grøtfjord 24.09 er eldre enn byttet.",
         f"- Tabellen viser hva den gamle rekkefølgen (met.no først) ville gitt nå: retningen avviker median {statistics.median(alle_dd):.0f}° "
         f"(største {max(alle_dd):.0f}°), {tot['ned'] + tot['opp']} av {n} timer ville hatt et annet stjernetall, og {tot['to']} ville flyttet seg 2 eller mer.",
         f"- Lenger ut, der BarentsWatch ikke rekker, betyr byttet mye: {sen['ned'] + sen['opp']} av {sen['n']} timer ville hatt et annet stjernetall "
         f"({sen['ned']} færre i dag, {sen['opp']} flere), og {sen['to']} flytter seg 2 eller mer. met.no-retningen blander inn vindsjø og gir oftere treff i svellvinduet.",
         "- **Anbefaling: la det stå som i dag.** Svellfeltet er den riktige kilden (samme felt som Windy viser som svell 1). Ingen avgjørelse trengs.", "",
         "## Før (met.no først) mot etter (svellfeltet, i bruk i dag)", "",
         "«Færre i dag» betyr at dagens kode gir færre stjerner enn den gamle rekkefølgen ville gitt. «Lyse timer» er timer med lys og minst 1 stjerne.", "",
         "| Spot | Timer | Med BW | Avvik i retning, median | Største | Færre i dag | Likt | Flere i dag | Flyttet 2+ | Lyse timer før | Lyse timer i dag |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: -(r["ned"] + r["opp"])):
        L.append(f"| {r['name']} | {r['n']} | {r['bw']} | {statistics.median(r['dd']):.0f}° | {max(r['dd']):.0f}° | {r['ned']} | {r['lik']} | {r['opp']} | {r['to']} | {r['lys_for']} | {r['lys_etter']} |")
    L += [f"| **Alle** | {n} | {tot['bw']} | {statistics.median(alle_dd):.0f}° | {max(alle_dd):.0f}° | {tot['ned']} | {tot['lik']} | {tot['opp']} | {tot['to']} | {tot['lys_for']} | {tot['lys_etter']} |", "",
          "## Lenger ut, uten BarentsWatch", "",
          f"{tot['bw']} av de {n} timene over har BarentsWatch-høyde, og der betyr svellretningen lite. Uten BarentsWatch styrer retningen høyden direkte. "
          f"For timene etter de første {TIMER}, så langt met.no rekker og uten BarentsWatch ({sen['n']} timer, alle spots): retningen avviker median "
          f"{statistics.median(sen['dd']) if sen['dd'] else 0:.0f}°, dagens kode gir færre stjerner i {sen['ned']} timer, likt i {sen['lik']} og flere i {sen['opp']}. "
          f"{sen['to']} timer flytter seg 2 eller mer.", "",
          "## Forbehold", "",
          f"- Kontroll: dagens kode gir samme stjernetall som det publiserte varselet i {n - avvik} av {n} timer.",
          "- met.no-retningen er hentet i dag, varselet er fra kjøringen over. Retningene er derfor ikke fra nøyaktig samme modellkjøring.",
          "- «Før» bytter bare `dir_offshore`. Den gamle koden regnet også `turn` fra met.no-retningen, og `turn` påvirker kappingen ved usikkert varsel "
          "i timene uten BarentsWatch. Tallene lenger ut er derfor omtrentlige.",
          "- Ett utsnitt på 48 timer. Hvor mye byttet betyr, avhenger av hvor mye vindsjø det er: jo mer vindsjø, jo lenger fra svellretningen ligger met.no-tallet.", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"skrev {OUT.relative_to(ROOT)}: {len(rows)} spots, {n} timer, avvik {avvik}")


if __name__ == "__main__":
    main()
