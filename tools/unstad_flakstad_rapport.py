"""T2b (Theodor 09.11.2026, Lofoten Surfsenter): «Unstad er nesten alltid større enn Flakstad.»
Sammenligner surfehøyde og stjerner for Unstad mot Flakstad-spotene time for time, finner
årsaken når de er for like eller står feil vei, og viser før/etter for mulige rettelser.

Bare rapport - endrer ingenting. Punkter, vinduer, facing og surf_factor_prior krever
Theodors ja (CLAUDE.md). Skriver data/backtest/t2b_unstad_flakstad_2026-11-10.md.

Grunnlaget er tynt, og rapporten sier det: skagsanden kom i arkivet først 10.11.2026
(spotene ble lagt til 16.10, kontoen var stengt 16.10-05.11), og ramberg er slått av
(enabled false) og har aldri vært hentet i produksjon. Derfor:
  1. Unstad mot Skagsanden: detaljfilene fra kjøringen som ligger live (--unstad, --skagsanden).
  2. Unstad mot Ramberg: bare timene uten BarentsWatch, regnet med Rambergs spot-oppsett på
     Skagsandens havdata (havpunktene ligger 2,7 km fra hverandre). Rekonstruksjon, ikke varsel.
  3. Unstads punkt i bruk mot skyggepunktet (700 m ut): arkivet i git-historikken fra 15.10.

Kjør: python3 tools/unstad_flakstad_rapport.py --unstad <unstad.json> --skagsanden <skagsanden.json>
(detaljfilene: https://theodorll03-bit.github.io/nordsurf/data/spots/<id>.json)"""
import argparse
import datetime as dt
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))
import backtest  # noqa: E402
import rating  # noqa: E402

OUT = ROOT / "data" / "backtest" / "t2b_unstad_flakstad_2026-11-10.md"
LIK = 0.1          # m: mindre forskjell enn dette teller som «lik»
SURF_MIN = 0.3     # m: forholdstall regnes bare når begge har minst så mye surf
FLAKSTAD_FAKTOR = 0.8   # alternativ C i før/etter: bare et regneeksempel, ikke et forslag til tall


def fm(v, nd=2):
    return "–" if v is None else f"{v:.{nd}f}".replace(".", ",")


def pct(a, b):
    return "–" if not b else f"{round(100 * a / b)} %"


def med(v):
    v = [x for x in v if x is not None]
    return statistics.median(v) if v else None


def utc(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00"))


def in_window(d, w):
    return d is not None and rating.in_sector(d, w)


def load_spots():
    return {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}


def prepared(sid, spots):
    exposure = json.loads((ROOT / "data" / "exposure_baseline.json").read_text(encoding="utf-8"))
    f = ROOT / "data" / "bw_calibration.json"
    calib = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    return backtest.prepare_spot(sid, spots, exposure, calib)


def compare(pairs):
    """pairs: [(a, b)] surfehøyder, None er utelatt før kallet. a = Unstad."""
    n = len(pairs)
    big = sum(1 for a, b in pairs if a - b > LIK)
    small = sum(1 for a, b in pairs if b - a > LIK)
    ratio = med([a / b for a, b in pairs if a >= SURF_MIN and b >= SURF_MIN])
    both = sum(1 for a, b in pairs if a >= SURF_MIN and b >= SURF_MIN)
    return {"n": n, "big": big, "eq": n - big - small, "small": small, "ratio": ratio, "both": both,
            "ma": med([a for a, _ in pairs]), "mb": med([b for _, b in pairs])}


def compare_row(name, pairs):
    c = compare(pairs)
    if not c["n"]:
        return f"| {name} | 0 | – | – | – | – | – | – |"
    return (f"| {name} | {c['n']} | {c['big']} ({pct(c['big'], c['n'])}) | {c['eq']} ({pct(c['eq'], c['n'])}) | "
            f"{c['small']} ({pct(c['small'], c['n'])}) | {fm(c['ma'])} | {fm(c['mb'])} | "
            f"{fm(c['ratio'])} ({c['both']} t) |")


HEAD = ["| Utvalg | Timer | Unstad større | Lik (±0,1 m) | Unstad mindre | Median Unstad (m) | Median Flakstad-spot (m) | Typisk forhold Unstad/Flakstad-spot (timer der begge har ≥ 0,3 m) |",
        "|---|---|---|---|---|---|---|---|"]


def star_row(name, pairs):
    n = len(pairs)
    hi = sum(1 for a, b in pairs if a > b)
    lo = sum(1 for a, b in pairs if a < b)
    return f"| {name} | {n} | {hi} | {n - hi - lo} | {lo} |"


def rerate(spot, hours):
    """Timene til en annen spot, regnet med denne spotens oppsett. Bare timer uten BarentsWatch
    (bw_height None) gir mening: BarentsWatch-tallene hører til den andre spotens punkt."""
    out = {}
    for h in hours:
        if h.get("bw_height") is not None or h.get("swell_offshore") is None:
            continue
        r = rating.rate(dict(h), spot)
        out[h["t"]] = (r.get("surf_height"), r.get("stars"))
    return out


def git_archive_runs(sid):
    """Alle arkivfiler som noen gang er lagt til i git (fila ryddes etter ca. 8 dager, historikken
    har dem). Gir [(issued, {t: rad})] for spoten, bare rader med skyggekolonner."""
    log = subprocess.run(["git", "log", "--all", "--diff-filter=A", "--format=%H", "--name-only", "--", "data/forecast_archive/"],
                         cwd=ROOT, capture_output=True, text=True, timeout=120).stdout.split("\n")
    seen, runs, commit = set(), [], None
    for line in log:
        line = line.strip()
        if not line:
            continue
        if not line.startswith("data/"):
            commit = line
            continue
        if line in seen:
            continue
        seen.add(line)
        raw = subprocess.run(["git", "show", f"{commit}:{line}"], cwd=ROOT, capture_output=True, text=True, timeout=60)
        if raw.returncode != 0:
            continue
        d = json.loads(raw.stdout)
        rows = d["spots"].get(sid)
        if rows:
            runs.append((utc(d["issued"]), rows))
    return sorted(runs, key=lambda x: x[0])


def nowcast(runs, max_h=24):
    """Hver time tas fra den siste kjøringen før timen (høyst max_h timer gammel)."""
    out = {}
    for i, (issued, rows) in enumerate(runs):
        end = min(runs[i + 1][0] if i + 1 < len(runs) else issued + dt.timedelta(hours=max_h), issued + dt.timedelta(hours=max_h))
        for t, row in rows.items():
            if issued <= utc(t) < end:
                out[t] = row
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unstad", required=True)
    ap.add_argument("--skagsanden", required=True)
    a = ap.parse_args()
    U = json.loads(Path(a.unstad).read_text(encoding="utf-8"))
    S = json.loads(Path(a.skagsanden).read_text(encoding="utf-8"))
    spots = load_spots()
    su, ss, sr = spots["unstad"], spots["skagsanden"], spots["ramberg"]
    uh = {h["t"]: h for h in U["hours"]}
    sh = {h["t"]: h for h in S["hours"]}
    ts = [t for t in uh if t in sh and uh[t].get("surf_height") is not None and sh[t].get("surf_height") is not None]
    bw = [t for t in ts if uh[t].get("height_source") == "barentswatch" and sh[t].get("height_source") == "barentswatch"]
    res = [t for t in ts if t not in set(bw)]
    run = U.get("generated")

    L = [f"# T2b: Unstad mot Flakstad (Lofoten Surfsenter, 09.11.2026)", "",
         "Laget av `tools/unstad_flakstad_rapport.py`. Bare rapport: ingenting i appen er endret.", "",
         "Påstanden fra Lofoten Surfsenter: «Unstad er nesten alltid større enn Flakstad.»", "",
         "KORT_SVAR", "",
         "## Grunnlaget (tynt)", "",
         f"- **Unstad mot Skagsanden:** én kjøring, {run}, {len(ts)} timer ({len(bw)} med BarentsWatch for begge, {len(res)} lenger fram med bare svellet ute). "
         "Skagsanden kom i arkivet først 10.11.2026 (lagt til 16.10, kontoen var stengt 16.10–05.11). Det finnes ingen eldre timer å sammenligne.",
         "- **Ramberg** er slått av (holdt tilbake til denne oppgaven) og har aldri vært hentet i produksjon. Det finnes ingen BarentsWatch-tall for Rambergs punkt lokalt. "
         "Ramberg er derfor bare regnet for timene uten BarentsWatch, med Rambergs oppsett på Skagsandens havdata (havpunktene ligger 2,7 km fra hverandre). Det er en rekonstruksjon, ikke et varsel.",
         "- **Backtesten** (de faste observasjonene 26.09–05.10) har bare Unstad. Flakstad-spotene fantes ikke da, og det finnes ingen observasjon fra Flakstad.",
         "- **Hvilken strand mener Surfsenteret?** Skagsanden er stranda ved Flakstad kirke (Lofoten Beach Camp). Ramberg ligger 2,4 km lenger sørvest. Begge har `area: Flakstad`. Rapporten viser begge.", ""]

    # ---------- 1 ----------
    L += ["## 1. Unstad mot Skagsanden, time for time", "", "Surfehøyde:", ""] + HEAD
    pr = lambda tt: [(uh[t]["surf_height"], sh[t]["surf_height"]) for t in tt]  # noqa: E731
    lys = [t for t in ts if uh[t].get("daylight")]
    L += [compare_row("Alle timer", pr(ts)), compare_row("Med BarentsWatch (første 2 døgn)", pr(bw)),
          compare_row("Uten BarentsWatch (dag 3–9)", pr(res)), compare_row("Bare lyse timer", pr(lys))]
    surf = [t for t in ts if max(uh[t]["surf_height"], sh[t]["surf_height"]) >= SURF_MIN]
    L += [compare_row("Timer der minst én av dem har 0,3 m eller mer", pr(surf)),
          compare_row("... av dem med BarentsWatch", pr([t for t in surf if t in set(bw)])),
          compare_row("... av dem uten BarentsWatch", pr([t for t in surf if t in set(res)]))]
    inw = [t for t in ts if in_window(uh[t].get("dir_offshore"), su["swell_window"])]
    inboth = [t for t in inw if in_window(sh[t].get("dir_offshore"), ss["swell_window"])]
    onlys = [t for t in ts if t not in set(inw) and in_window(sh[t].get("dir_offshore"), ss["swell_window"])]
    onlyu = [t for t in inw if t not in set(inboth)]
    L += [compare_row(f"Svellet ute i Unstads vindu {su['swell_window']}, ikke i Skagsandens {ss['swell_window']}", pr(onlyu)),
          compare_row("Svellet ute i begge vinduene", pr(inboth)),
          compare_row("Svellet ute i Skagsandens vindu, ikke i Unstads", pr(onlys)), ""]
    L += ["Stjerner:", "", "| Utvalg | Timer | Unstad flere | Like mange | Unstad færre |", "|---|---|---|---|---|"]
    st = lambda tt: [(uh[t]["stars"], sh[t]["stars"]) for t in tt if uh[t].get("stars") is not None and sh[t].get("stars") is not None]  # noqa: E731
    L += [star_row("Alle timer", st(ts)), star_row("Med BarentsWatch", st(bw)), star_row("Uten BarentsWatch", st(res)), star_row("Bare lyse timer", st(lys)), ""]

    # ---------- 2 ----------
    L += ["## 2. Unstad mot Ramberg (rekonstruksjon, bare timene uten BarentsWatch)", ""]
    try:
        pram = prepared("ramberg", spots)
        pska = prepared("skagsanden", spots)
        ram = rerate(pram, S["hours"])
        ska = rerate(pska, S["hours"])
        # Kontroll: Skagsanden regnet på nytt skal gi det samme som det publiserte varselet.
        diffs = [abs(ska[t][0] - sh[t]["surf_height"]) for t in ska if t in sh and ska[t][0] is not None and sh[t].get("surf_height") is not None]
        tt = [t for t in res if t in ram and ram[t][0] is not None]
        L += [f"Kontroll av metoden: Skagsanden regnet på nytt lokalt avviker fra det publiserte varselet med høyst {fm(max(diffs) if diffs else None)} m over {len(diffs)} timer.", ""]
        L += HEAD + [compare_row(f"Ramberg som i spots.json (facing {sr['facing']}, vindu {sr['swell_window']})", [(uh[t]["surf_height"], ram[t][0]) for t in tt])]
        r315 = dict(pram, facing=315)
        ram315 = rerate(r315, S["hours"])
        L += [compare_row("Ramberg med facing 315 (grenen region/ramberg-315)", [(uh[t]["surf_height"], ram315[t][0]) for t in tt if ram315[t][0] is not None]), "",
              "Uten BarentsWatch styres høyden av vinduet og facing spiller liten rolle. Derfor er de to radene like eller nesten like. "
              "Forskjellen mellom 287,7 og 315 viser seg først i timene med BarentsWatch, og de kan bare regnes i en prøvehenting.", ""]
    except Exception as e:  # rapporten skal ikke stoppe på den delen som er en rekonstruksjon
        L += [f"Kunne ikke regnes lokalt ({type(e).__name__}: {e}).", ""]

    # ---------- 3 ----------
    L += ["## 3. Årsaken: BarentsWatch-punktene (timene med BarentsWatch)", "",
          "| | Unstad, punkt i bruk (250 m ut, 3,9 m dyp) | Unstad, skyggepunkt (700 m ut, 8,5 m dyp) | Skagsanden (500 m ut, 9,3 m dyp) |", "|---|---|---|---|"]
    g = lambda d, k, tt: med([d[t].get(k) for t in tt])  # noqa: E731
    L += [f"| BarentsWatch Hs, median (m) | {fm(g(uh, 'bw_height', bw))} | {fm(g(uh, 'bw_height_shadow', bw))} | {fm(g(sh, 'bw_height', bw))} |",
          f"| BarentsWatch-periode, median (s) | {fm(g(uh, 'bw_period', bw), 1)} | ikke lagret | {fm(g(sh, 'bw_period', bw), 1)} |",
          f"| Hs ved spoten etter justering, median (m) | {fm(g(uh, 'height', bw))} | – | {fm(g(sh, 'height', bw))} |",
          f"| Surf-faktor | {fm(U.get('surf_factor'))} (startverdi fra 2 observasjoner) | – | {fm(S.get('surf_factor'))} |",
          f"| Surfehøyde, median (m) | {fm(g(uh, 'surf_height', bw))} | – | {fm(g(sh, 'surf_height', bw))} |", ""]
    rat = [(uh[t]["bw_height"] / uh[t]["bw_height_shadow"], uh[t]["bw_height_shadow"]) for t in bw
           if uh[t].get("bw_height") is not None and uh[t].get("bw_height_shadow")]
    stor, liten = [r for r, s in rat if s >= 1.0], [r for r, s in rat if s < 1.0]
    us = [(uh[t]["bw_height_shadow"] / sh[t]["bw_height"]) for t in bw if uh[t].get("bw_height_shadow") is not None and sh[t].get("bw_height")]
    ui = [(uh[t]["bw_height"] / sh[t]["bw_height"]) for t in bw if uh[t].get("bw_height") is not None and sh[t].get("bw_height")]
    L += [f"- Unstads punkt i bruk viser median {fm(med([r for r, _ in rat]))} av det skyggepunktet viser ({len(rat)} timer): "
          f"{fm(med(stor))} når skyggepunktet har 1 m eller mer ({len(stor)} t), {fm(med(liten))} når det har under 1 m ({len(liten)} t).",
          f"- Mot Skagsandens punkt: Unstads punkt i bruk viser median {fm(med(ui))} av Skagsandens Hs, skyggepunktet {fm(med(us))}.",
          f"- Svellretningen ute i disse timene: {sum(1 for t in bw if in_window(uh[t].get('dir_offshore'), su['swell_window']))} av {len(bw)} timer i Unstads vindu, "
          f"{sum(1 for t in bw if in_window(sh[t].get('dir_offshore'), ss['swell_window']))} av {len(bw)} i Skagsandens. Median periode ute {fm(g(uh, 'period', bw), 1)} s.", ""]

    # ---------- 4 ----------
    runs = git_archive_runs("unstad")
    now = nowcast(runs)
    rows = [r for r in now.values() if len(r) >= 5 and r[1] is not None and r[2] is not None]
    L += ["## 4. Unstad: punktet i bruk mot skyggepunktet, alle kjøringer i arkivet siden 15.10", "",
          f"{len(runs)} kjøringer i git-historikken, men bare fire av dem har skyggetall for Unstad. {len(rows)} timer med begge tallene (hver time fra siste kjøring før timen, høyst 24 timer gammel). "
          "Kjøringer: " + ", ".join(d.strftime('%d.%m') for d in sorted({i.date() for i, r in runs if any(len(x) >= 5 and x[2] is not None for x in r.values())})) + ".", "",
          "| Utvalg (surfehøyde fra skyggepunktet uten startverdi) | Timer | Median i bruk (m) | Median skygge med faktor 1,45 (m) | Median skygge uten (m) | Stjerner: skygge flere / like / færre |", "|---|---|---|---|---|---|"]
    for name, f in (("Alle", lambda r: True), ("Under 1,0 m", lambda r: r[3] is not None and r[3] < 1.0), ("1,0 m eller mer", lambda r: r[3] is not None and r[3] >= 1.0)):
        rr = [r for r in rows if f(r)]
        sp = [(r[4], r[0]) for r in rr if r[4] is not None and r[0] is not None]
        L.append(f"| {name} | {len(rr)} | {fm(med([r[1] for r in rr]))} | {fm(med([r[2] for r in rr]))} | {fm(med([r[3] for r in rr]))} | "
                 f"{sum(1 for x, y in sp if x > y)} / {sum(1 for x, y in sp if x == y)} / {sum(1 for x, y in sp if x < y)} |")
    L.append("")

    # ---------- 5 ----------
    ark = None
    for issued, r in runs:
        if run and abs((issued - utc(run)).total_seconds()) < 3 * 3600:
            ark = r
    L += ["## 5. Før og etter (timene med BarentsWatch i kjøringen over)", ""]
    if ark:
        tt = [t for t in bw if t in ark and len(ark[t]) >= 5 and ark[t][2] is not None]
        L += HEAD
        L += [compare_row("I dag", [(uh[t]["surf_height"], sh[t]["surf_height"]) for t in tt]),
              compare_row("A: Unstads punkt flyttes til 700 m, startverdien 1,45 beholdes", [(ark[t][2], sh[t]["surf_height"]) for t in tt]),
              compare_row("B: som A, men uten startverdien", [(ark[t][3], sh[t]["surf_height"]) for t in tt if ark[t][3] is not None]),
              compare_row(f"C: Skagsanden ganges med {fm(FLAKSTAD_FAKTOR, 1)} (regneeksempel), Unstad som i dag", [(uh[t]["surf_height"], FLAKSTAD_FAKTOR * sh[t]["surf_height"]) for t in tt]), ""]
        mv = [(ark[t][4] - uh[t]["stars"]) for t in tt if ark[t][4] is not None and uh[t].get("stars") is not None]
        L += [f"Unstads stjerner med A mot i dag, {len(mv)} timer: {sum(1 for x in mv if x > 0)} opp, {sum(1 for x in mv if x == 0)} uendret, {sum(1 for x in mv if x < 0)} ned. "
              f"Timer som flytter seg 2 eller mer: {sum(1 for x in mv if abs(x) >= 2)}.", "",
              "| Time (UTC) | Svell ute (m, retning, periode) | Unstad Hs i bruk / skygge | Unstad surf i dag (★) | A (★) | B | Skagsanden Hs | Skagsanden surf (★) |", "|---|---|---|---|---|---|---|---|"]
        for t in tt[::3]:
            x, y, r = uh[t], sh[t], ark[t]
            L.append(f"| {t[5:16].replace('T', ' ')} | {fm(x.get('swell_offshore'), 1)}, {x.get('dir_offshore')}°, {fm(x.get('period'), 1)} s | {fm(x.get('bw_height'))} / {fm(x.get('bw_height_shadow'))} | "
                     f"{fm(x['surf_height'])} ({x['stars']}) | {fm(r[2])} ({r[4]}) | {fm(r[3])} | {fm(y.get('bw_height'))} | {fm(y['surf_height'])} ({y['stars']}) |")
        L.append("")
    else:
        L += ["Fant ikke kjøringen i arkivet, så A og B kan ikke vises.", ""]

    cb, cr, cs = compare(pr(bw)), compare(pr(res)), compare(pr(surf))
    kort = ["## Kort svar", "",
            f"- Varselet sier ikke det Surfsenteret sier. I de {cb['n']} timene med BarentsWatch er Unstad aldri større enn Skagsanden "
            f"({cb['big']} større, {cb['eq']} like, {cb['small']} mindre). I timene der minst én av dem har surf, er Unstad større i {pct(cs['big'], cs['n'])} og mindre i {pct(cs['small'], cs['n'])}.",
            f"- De er ikke for like fordi de deler noe. De har hvert sitt havpunkt og hvert sitt BarentsWatch-punkt. Transfer er lik (0,6, standard), men den brukes bare uten BarentsWatch.",
            f"- Forskjellen oppstår på Unstad-siden: BarentsWatch-punktet til Unstad ligger 250 m ut på 3,9 m dyp og viser median {fm(med([r for r, _ in rat]))} av det punktet 700 m ut viser. "
            f"Punktet 700 m ut viser {fm(med(us))} av Skagsandens. Kystmodellen gir altså omtrent like mye sjø i de to buktene i dette været, og Unstad-tallet halveres mellom 700 m og 250 m. "
            "Om det skyldes at punktet ligger i brenningen eller i le for nordlig sjø, kan ikke denne kjøringen avgjøre. Kort periode i punktet og svært lavt forhold på små dager ligner le.",
            "- Været i denne kjøringen er lite typisk: kort vindsjø fra nord og nordnordvest (7–9 s), som treffer Skagsanden rett på og ligger i kanten av eller utenfor Unstads vindu. "
            "At Skagsanden (vindu til 4°) er størst i nordlig sjø, er fysisk ventet. Kjøringen motsier derfor ikke Surfsenteret, og den kan ikke avgjøre hva som skjer på en vanlig vestlig svelldag.",
            f"- Uten BarentsWatch (dag 3–9) styrer vinduene alt: Unstad er større i {cr['big']} timer (svell fra vest-sørvest, utenfor Skagsandens vindu) og mindre i {cr['small']} (svell fra nord).",
            "- **Anbefaling: ingen endring av tall nå.** Grunnlaget er én kjøring uten observasjon, og det er ikke vist at rekkefølgen er feil i dette været. Flytting av Unstads punkt (A) snur rekkefølgen, men kan ikke prøves mot de faste observasjonene, "
            f"og gir nesten tre ganger så høy surf i de {len(rows)} arkivtimene med skyggetall (fire kjøringer siden 15.10, median 3,1 m mot 1,1 m). Se forslaget nederst."]
    L[L.index("KORT_SVAR"):L.index("KORT_SVAR") + 1] = kort
    L += ["## Forslag (krever Theodors ja, ingenting er gjort)", "",
          "1. **Ikke skaler ned Flakstad (C).** Det er ikke vist noen feil der. Skagsandens punkt følger regelen fra 15.10 (500 m ut, 9,3 m dyp), og det finnes ingen observasjon som sier at tallene er for høye. "
          "En fast faktor ville også trekke ned Skagsanden på de dagene nordlig svell faktisk treffer best der.",
          "2. **Unstads BarentsWatch-punkt bør flyttes ut til 700 m (A), men ikke før det er prøvd på en vestlig svelldag.** Det er samme sak som ROADMAP N. "
          "Grunnen til å vente: startverdien 1,45 er lært på det gamle punktet (26.09 og 27.09). De faste observasjonene kan ikke regnes på nytt med det nye punktet, fordi BarentsWatch-tall for 700 m-punktet ikke finnes for de dagene. "
          "I arkivtimene med skyggetall (fire kjøringer siden 15.10) gir A median 3,1 m der varselet i dag gir 1,1 m. Uten en observasjon vet vi ikke hvilket av tallene som er riktig.",
          "3. **Neste svelldag er trolig 15.–16.11:** varselet har 2,5 m svell fra 250° med 12 s periode. Fra 13.–14.11 dekker BarentsWatch de timene. "
          "Da kan denne rapporten kjøres på nytt (ingen ekstra kall), og én størrelse fra Unstad og én fra Flakstad samme dag avgjør om det blir A (behold 1,45), B (fjern 1,45) eller noe midt imellom.",
          "4. **Ramberg** kan ikke vurderes lokalt i timene med BarentsWatch (ingen tall for punktet). Facing 315 (grenen region/ramberg-315) må ses i en prøvehenting samme svelldag.",
          "5. Spør Lofoten Surfsenter: mener de Skagsanden eller Ramberg med «Flakstad»? Gjelder «nesten alltid større» også når svellet kommer fra nord?", ""]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
