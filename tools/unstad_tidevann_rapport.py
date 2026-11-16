"""T2c (Theodor 09.11.2026, Lofoten Surfsenter): «Lofoten er best på lavvann.»
Viser hva en myk tidevannsregel for Unstad (`local_rules.tide_prefer` + `tide_penalty_high`,
samme mønster som Farstadsanden) ville gjort: tidevannet ved de faste observasjonene, og
stjerner før og etter for de neste 48 timene og for de siste 14 dagene det finnes inndata for.

Bare rapport - endrer ingenting. En ny lokal regel på en live spot krever Theodors ja.
Skriver data/backtest/t2c_unstad_tidevann_2026-11-10.md.

Inndata: detaljfila som ligger live (--live) og alle publiserte varsler i git-historikken
(docs/data/forecast.json, 24.09-14.10.2026). Etter 14.10 er timenes inndata ikke lagret
(arkivet har bare stjerner og surfehøyde), så «14 dager tilbake» er 01.-14.10, ikke 27.10-10.11.

Kjør: python3 tools/unstad_tidevann_rapport.py --live <unstad.json>   (tar 1-2 minutter)"""
import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))
sys.path.insert(0, str(ROOT / "tools"))
import rating  # noqa: E402
import unstad_vind_rapport as t2a  # noqa: E402  (git_runs, nowcast, prepared)

OSLO = ZoneInfo("Europe/Oslo")
OUT = ROOT / "data" / "backtest" / "t2c_unstad_tidevann_2026-11-10.md"
KILDE = "Lofoten Surfsenter, 09.11.2026"

# Variantene som vises. Vekt 0,7 er den Unstads local_rules har i dag (én vekt per spot).
VARIANTER = [
    ("V1", "bare lav er foretrukket, fradrag 1", {"tide_prefer": ["lav"], "tide_penalty_high": 1}),
    ("V2", "lav og middels er foretrukket, fradrag 1 (som Farstadsanden)", {"tide_prefer": ["lav", "middels"], "tide_penalty_high": 1}),
    ("V3", "lav og middels er foretrukket, fradrag 0,5 (myk)", {"tide_prefer": ["lav", "middels"], "tide_penalty_high": 0.5}),
]

# De faste observasjonene for Unstad (CLAUDE.md), i norsk tid. (dato, fra time, til og med time, tekst)
OBS = [
    ((2026, 9, 26), 14, 15, "26.09 ca. kl. 14:45: over hodet, tønner, offshore. 4 stjerner"),
    ((2026, 9, 27), 6, 9, "27.09 morgen: rene linjer, bryst- til hodehøyt. Ca. 3 stjerner"),
    ((2026, 9, 28), 12, 15, "28.09 ca. kl. 13: «Safe to say it's firing». 4 til 5 stjerner"),
    ((2026, 10, 5), 9, 12, "05.10 kl. 09–12"),
]


def utc(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00"))


def with_rule(spot, rule):
    s = dict(spot)
    s["local_rules"] = dict(spot.get("local_rules") or {}, **rule)
    return s


def stars(h, spot):
    return rating.rate(dict(h), spot)["stars"]


def tide_txt(h):
    t = h.get("tide") or {}
    if t.get("state") is None:
        return "ukjent"
    lvl = t.get("level")
    return f"{t['state']} ({round(100 * lvl)} %{', stiger' if t.get('rising') else ', faller'})" if lvl is not None else t["state"]


FIRE_PLUSS = {}  # (tabellnavn, variant) -> (lyse timer med 4+ før, etter); brukes i «Kort svar»


def period_table(name, hours, spot, variants):
    known = [h for h in hours if (h.get("tide") or {}).get("state") is not None]
    st = Counter(h["tide"]["state"] for h in known)
    before = {h["t"]: stars(h, spot) for h in known}
    L = [f"### {name}", "",
         f"{len(hours)} timer, {len(known)} med kjent tidevann: {st.get('lav', 0)} lav, {st.get('middels', 0)} middels, {st.get('høy', 0)} høy. "
         f"Timer med minst 1 stjerne i dag: {sum(1 for v in before.values() if v >= 1)} (lyse: {sum(1 for h in known if before[h['t']] >= 1 and h.get('daylight'))}).", "",
         "| Variant | Timer som mister 1 stjerne | ... av dem lyse | Timer som flytter seg 2 eller mer | Lyse timer med 3+ stjerner før → etter | Lyse timer med 4+ før → etter |",
         "|---|---|---|---|---|---|"]
    lys = [h for h in known if h.get("daylight")]
    for kode, _, rule in variants:
        sp = with_rule(spot, rule)
        after = {h["t"]: stars(h, sp) for h in known}
        d = {t: before[t] - after[t] for t in before}
        FIRE_PLUSS[(name, kode)] = (sum(1 for h in lys if before[h['t']] >= 4), sum(1 for h in lys if after[h['t']] >= 4))
        L.append(f"| {kode} | {sum(1 for v in d.values() if v == 1)} | {sum(1 for h in lys if d[h['t']] == 1)} | {sum(1 for v in d.values() if abs(v) >= 2)} | "
                 f"{sum(1 for h in lys if before[h['t']] >= 3)} → {sum(1 for h in lys if after[h['t']] >= 3)} | "
                 f"{sum(1 for h in lys if before[h['t']] >= 4)} → {sum(1 for h in lys if after[h['t']] >= 4)} |")
    up = 0
    for kode, _, rule in variants:
        sp = with_rule(spot, rule)
        up += sum(1 for h in known if stars(h, sp) > before[h["t"]])
    L += ["", f"Timer som går opp i noen variant: {up} (regelen kan bare trekke ned).", ""]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", required=True)
    a = ap.parse_args()
    spot = t2a.prepared()
    live = json.loads(Path(a.live).read_text(encoding="utf-8"))
    runs = t2a.git_runs()
    now = t2a.nowcast(runs)
    by_t = {utc(h["t"]): h for h in now}

    L = ["# T2c: tidevann på Unstad (Lofoten Surfsenter, 09.11.2026)", "",
         "Laget av `tools/unstad_tidevann_rapport.py`. Bare rapport: ingenting i appen er endret.", "",
         "Påstanden fra Lofoten Surfsenter: «Lofoten er best på lavvann.»", "",
         "KORT_SVAR", "",
         "## Slik deler tide.py inn", "",
         "Nivået regnes fra 0 (fjære) til 1 (flo) mellom to nabovendepunkter. Under en tredel er «lav», over to tredeler «høy», ellers «middels». "
         "En tidevannssyklus er ca. 12,4 timer, så hver tilstand varer omtrent like lenge: rundt en tredel av døgnet hver.", "",
         "Unstad har i dag ingen tidevannsregel («spoten tåler alt»). Varianter som er regnet (vekt 0,7, den Unstads lokale regler har fra før):", ""]
    L += [f"- **{k}:** {txt}. Vektet fradrag {str(round(0.7 * r['tide_penalty_high'], 2)).replace('.', ',')} stjerne utenfor det foretrukne." for k, txt, r in VARIANTER]
    L += ["", "Fradraget legges sammen med vind og andre fradrag før avrunding (0,5 rundes opp). Et fradrag på 0,7 koster derfor alltid en stjerne. "
          "Et fradrag på 0,35 koster ingenting alene, men en stjerne sammen med et lite vindfradrag (over 0,15). "
          "En femte stjerne krever uansett foretrukket tidevann når spoten har en slik regel (`five_star_losses`).", ""]

    # ---------- Observasjonene ----------
    L += ["## 1. Tidevannet ved de faste observasjonene", "",
          "Timene er hentet fra varselet som lå ute da (siste kjøring før timen), og stjernene er regnet på nytt med dagens kode.", "",
          "| Observasjon | Time (norsk tid) | Tidevann | Stjerner i dag | V1 | V2 | V3 |", "|---|---|---|---|---|---|---|"]
    obs_states = []
    for (y, m, d), h0, h1, txt in OBS:
        for hh in range(h0, h1 + 1):
            t = dt.datetime(y, m, d, hh, tzinfo=OSLO).astimezone(dt.timezone.utc)
            h = by_t.get(t)
            if h is None:
                L.append(f"| {txt} | {hh:02d}:00 | ingen time i historikken | – | – | – | – |")
                continue
            b = stars(h, spot)
            v = [stars(h, with_rule(spot, r)) for _, _, r in VARIANTER]
            obs_states.append(((h.get("tide") or {}).get("state"), txt, b, v))
            L.append(f"| {txt} | {hh:02d}:00 | {tide_txt(h)} | {b} | {v[0]} | {v[1]} | {v[2]} |")
    L.append("")
    hi = sorted({txt.split(':')[0].split(' ca.')[0].split(' morgen')[0].split(' kl.')[0] for s, txt, _, _ in obs_states if s == "høy"})
    lo = sorted({txt.split(':')[0].split(' ca.')[0].split(' morgen')[0].split(' kl.')[0] for s, txt, _, _ in obs_states if s == "lav"})
    L += [f"Observasjoner med minst én time på høyvann: {', '.join(hi) if hi else 'ingen'}. Med minst én time på lavvann: {', '.join(lo) if lo else 'ingen'}.", ""]
    w28 = [by_t[t] for t in by_t if t.astimezone(OSLO).date() == dt.date(2026, 9, 28) and 12 <= t.astimezone(OSLO).hour <= 15]
    r28 = [rating.rate(dict(h), spot) for h in w28]
    if w28 and all(h.get("bw_height") is not None and r.get("swell_share") is not None for h, r in zip(w28, r28)):
        k = lambda v, nd: f"{v:.{nd}f}".replace(".", ",")
        L += [f"Om 28.09: varselet som lå ute gir 0 stjerner i disse timene, også med dagens kode. Det er ikke vindstraffen "
              f"(den trekker {max(r.get('faded_wind') or 0 for r in r28)} stjerner, selv med {min(h['wind_speed'] for h in w28):.0f}–{max(h['wind_speed'] for h in w28):.0f} m/s fraland). "
              f"Nullen kommer av at BarentsWatch-punktet viste {k(min(h['bw_height'] for h in w28), 1)}–{k(max(h['bw_height'] for h in w28), 1)} m "
              f"og svellandelen var {k(min(r['swell_share'] for r in r28), 2)}–{k(max(r['swell_share'] for r in r28), 2)}. "
              f"Høyden ved spoten havner da under flat-grensa på {k(rating.FLAT_HS_THRESHOLD, 2)} m, og timen merkes «blåst ut» på grunn av lav svellandel. "
              "Den faste observasjonen i testene bruker egne inndata og er ikke berørt. "
              "Tidevannet står fast: det fyrte på høyvann. Funnet er verdt å merke seg for seg selv: en økt som var god, sto som 0 i varselet. "
              "Det er samme BarentsWatch-punkt som i T2b (250 m ut).", ""]
    kort = ["## Kort svar", "",
            "- **To av de fire faste observasjonene var gode økter på høyvann:** 26.09 (4 stjerner, 75–93 % av flo) og 28.09 («firing», 4 til 5 stjerner, 75–100 %). "
            "05.10 gikk fra høyvann til middels. Bare 27.09 var på lavvann. Regelen må derfor være myk.",
            "FIRE_PLUSS_TEKST",
            "- Den myke varianten (V3, lav og middels foretrukket, vektet fradrag 0,35) lar 26.09 stå på 4. Den koster bare en stjerne når noe annet også trekker litt ned.",
            "- Ingen time flytter seg 2 eller mer i noen variant, verken de neste 48 timene eller bakover.",
            "- **Anbefaling: V3, hvis regelen skal inn nå.** Ingenting er endret. Se forslaget nederst."]
    L[L.index("KORT_SVAR"):L.index("KORT_SVAR") + 1] = kort

    # ---------- Perioder ----------
    L += ["## 2. Før og etter", ""]
    g = utc(live["generated"])
    nxt = [h for h in live["hours"] if g <= utc(h["t"]) < g + dt.timedelta(hours=48)]
    L += period_table(f"De neste 48 timene (kjøringen {live['generated'][:16]}Z)", nxt, spot, VARIANTER)
    last = max(by_t)
    back = [h for t, h in sorted(by_t.items()) if last - dt.timedelta(days=14) < t <= last]
    L += period_table(f"14 dager tilbake med inndata ({(last - dt.timedelta(days=14)).strftime('%d.%m')}–{last.strftime('%d.%m.%Y')})", back, spot, VARIANTER)
    ALLE = "Alle publiserte timer 24.09–14.10"
    L += period_table(ALLE, [h for _, h in sorted(by_t.items())], spot, VARIANTER)
    f0 = FIRE_PLUSS[(ALLE, "V1")][0]
    tap = sorted(FIRE_PLUSS[(ALLE, k)][0] - FIRE_PLUSS[(ALLE, k)][1] for k in ("V1", "V2"))
    L[L.index("FIRE_PLUSS_TEKST")] = (
        "- En regel etter Farstadsanden-mønsteret (V1 eller V2, vektet fradrag 0,7) tar alltid en hel stjerne på høyvann. "
        f"Den ville tatt 26.09 fra 4 til 3 stjerner i varselet som lå ute, og fjernet {tap[0]} til {tap[1]} av de {f0} lyse timene med 4 stjerner eller mer 24.09–14.10.")

    L += ["## Forslag (krever Theodors ja, ingenting er gjort)", "",
          "1. **V3 for Unstad:** `tide_prefer: [\"lav\", \"middels\"]`, `tide_penalty_high: 0.5`, i Unstads `local_rules` (vekt 0,7 som i dag, vektet fradrag 0,35). "
          f"Kilden «{KILDE}» føres opp i CLAUDE.md under «Lokalkunnskap» og i `source`-feltet ved siden av dagens kilde.",
          "2. **Bivirkning å kjenne til:** med en slik regel kan en time på høyvann aldri få den femte stjernen. 28.09 («4 til 5 stjerner») var på høyvann. "
          "Skal femte stjerne fortsatt være mulig på høyvann, må `five_star_losses` få et unntak for myke regler. Det er en kodeendring som ikke er gjort.",
          "3. **Én vekt per spot:** `local_rules` har ett `weight`-felt. Unstads energiterskler og tidevannsregelen deler derfor vekten 0,7. "
          "Skal Surfsenterets regel ha egen vekt, må koden få vekt per regel.",
          "4. **Testene fanger ikke forskjellen:** `test_rating.py` og `test_backtest.py` er grønne med alle tre variantene (kjørt 10.11 mot en kopi av spots.json per variant). "
          "Forskjellen mellom dem vises bare i varselet som lå ute, som i tabellene over. Kommer regelen inn, bør 26.09 kl. 14:45 med høyvann inn som egen test.",
          "5. **Spørsmål til deg:** skal regelen gjelde flere Lofoten-spots? Surfsenteret sa «Lofoten», ikke «Unstad». "
          "For Unstad taler to av fire gode økter imot en hard regel. For de andre Lofoten-spotene finnes ingen observasjoner ennå.", ""]
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
