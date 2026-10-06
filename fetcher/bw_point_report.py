"""ROADMAP oppgave E (06.10.2026): les data/bw_point_search/result.json (skrevet
av workflowen "Finn BarentsWatch-punkt") og rapporter, per spot:

1. Dagens barentswatch_point: hvor stor andel av totalhøyden ute BarentsWatch
   gir i timer der svellet ute faktisk kommer inn i vinduet (directness over
   0,5 - samme filter som fetch.convention_warning()/bw_point_in_lee_warning(),
   så lav andel pga. svell UTENFOR vinduet ikke teller som "punkt i le").
   FLAGGES hvis mer enn halvparten av de timene ligger under 25 % (Theodors
   grense) - samme "mer enn halvparten"-prinsipp som de andre sikringene.
2. Alle kandidatpunktene: medianandel over de samme timene, hvilket rutepunkt
   BarentsWatch faktisk valgte (flere kandidater kan snappe til SAMME celle),
   og en lenke.
3. Et FORSLAG til nytt punkt etter prosent-metoden: kandidaten med høyest
   medianandel. Kandidater over 100 % av svellet ute avvises IKKE (Theodors
   presisering 06.10.2026: nær land bygger bølgene seg opp på grunnere vann,
   ved odder samler svellet seg) - de merkes "høy, sjekk".
4. For spots med observasjoner (Unstad, Grøtfjord, Lenangsøyra): hver
   kandidat sammenlignes med observasjonene, se observation_fit(). Theodors
   ønske var "punktet som passer observasjonene best, ikke bare det som
   ligger nærmest en fast prosent av svellet ute" - men fysikk-kontrollør
   (06.10.2026) viste at metoden ikke kan RANGERE kandidater: et konstant
   forhold skalerer alle datoene likt, og surf_factor kalibreres om igjen.
   Den brukes derfor som KONSISTENSSJEKK: holder kandidatene de flate dagene
   flate (Grøtfjord/Lenangsøyra), og kan et avvik i det hele tatt lukkes
   med en punktflytting (Unstad - svaret er nei for 05.10)?
   Bare rapportert - endrer ALDRI spots.json. Krever Theodors ja (CLAUDE.md).

Kjør: python fetcher/bw_point_report.py   (ingen nøkler trengs - leser bare fila)
"""
import json
import statistics
from pathlib import Path

from rating import directness

ROOT = Path(__file__).resolve().parent.parent
RESULT = ROOT / "data" / "bw_point_search" / "result.json"
LOW_RATIO = 0.25       # Theodors grense, "under 25 prosent av totalhøyden ute"
HIGH_RATIO = 1.0       # over totalhøyden ute: "høy, sjekk" - IKKE avvist (Theodors presisering 06.10.2026)
MIN_HOURS = 4          # færre timer i vinduet enn dette: for lite å si noe fra


MIN_SWELL_OFFSHORE = 0.5  # m - samme krav som fetch.convention_warning()


def in_window_hours(point, spot):
    """Timer der svellet ute kommer inn i vinduet OG begge høydene finnes.
    Fysikk-kontrollør 06.10.2026: SAMME filter som fetch.convention_warning()
    - krever også ekte svell ute (over 0,5 m) og kjent svellretning
    (directness(None) er en nøytral 0,7 og ville ellers telt som "i
    vinduet"), og en BarentsWatch-høyde på nøyaktig 0,0 behandles som
    manglende data (punkt på/ved land i BarentsWatch sitt grid, eller
    Open-Meteo uten dekning - sett for Russelv/Lenangsøyra sine havpunkt),
    ikke som flatt hav."""
    out = []
    for k, h in sorted(point["hours"].items()):
        tot, sw, sd = h.get("offshore_total_height"), h.get("offshore_swell_height"), h.get("offshore_swell_dir")
        if not h.get("height") or not tot or not sw or sw <= MIN_SWELL_OFFSHORE or sd is None:
            continue
        if directness(sd, spot) <= 0.5:
            continue
        out.append((k, h["height"], tot, h["height"] / tot))
    return out


def same_cell_groups(points):
    """Kandidater med byte-identiske tidsserier snappet til SAMME
    BarentsWatch-celle (fysikk-kontrollør 06.10.2026: 2-6 par per spot,
    grid ca. 100-250 m). chosen_point i result.json er bare et EKKO av de
    forespurte koordinatene og sier ingenting om dette. {label: første
    label med samme serie, eller None}"""
    seen, group = {}, {}
    for label, p in points.items():
        key = json.dumps({k: [v.get("height"), v.get("dir"), v.get("period")] for k, v in sorted(p["hours"].items())})
        group[label] = seen.setdefault(key, label) if seen.get(key) != label else None
        if group[label] == label:
            group[label] = None
    return group


def report_spot(sid, data, spot):
    name = spot["name"]
    points = data["points"]
    current = points.get("dagens barentswatch_point")
    print(f"\n===== {name} =====")
    if not current or not current["hours"]:
        print("  Dagens punkt: ingen BarentsWatch-data i kjøringen.")
    else:
        rows = in_window_hours(current, spot)
        has_totals = any(h.get("offshore_total_height") for h in current["hours"].values())
        if not has_totals:
            print("  Dagens punkt: Open-Meteo ga ingen totalhøyde ute for havpunktet i denne kjøringen - "
                  "prosent-metoden er umulig (BarentsWatch-dataene kan likevel være fine, se forholdene under).")
        elif len(rows) < MIN_HOURS:
            print(f"  Dagens punkt: bare {len(rows)} timer med svell mot vinduet i denne 48-timersperioden - "
                  f"for lite til prosent-metoden. Kjør workflowen på nytt en dag med svell i vinduet.")
        else:
            low = [r for r in rows if r[3] < LOW_RATIO]
            med = statistics.median(r[3] for r in rows)
            flag = len(low) > len(rows) / 2
            print(f"  Dagens punkt: median {med:.0%} av totalhøyden ute over {len(rows)} timer mot vinduet, "
                  f"{len(low)} under {LOW_RATIO:.0%}.{'  <-- FLAGGET: trolig i le' if flag else ''}")

    groups = same_cell_groups(points)
    print(f"  {'Kandidat':<30}{'median':>8}{'timer':>7}  samme BarentsWatch-celle som")
    scored = []
    for label, p in points.items():
        rows = in_window_hours(p, spot)
        same = groups.get(label) or "-"
        if len(rows) < MIN_HOURS:
            print(f"  {label:<30}{'-':>8}{len(rows):>7}  {same}")
            continue
        med = statistics.median(r[3] for r in rows)
        scored.append((med, label, p, len(rows)))
        print(f"  {label:<30}{med:>8.0%}{len(rows):>7}  {same}")

    # 06.10.2026, Theodors presisering: kandidater over 100 % av svellet ute
    # AVVISES IKKE - nær land bygger bølgene seg opp på grunnere vann, og ved
    # odder kan svellet samle seg. De merkes "høy, sjekk" og er med i
    # forslaget på lik linje.
    candidates = [s for s in scored if not s[1].startswith("dagens")]
    if candidates:
        med, label, p, n = max(candidates, key=lambda s: s[0])
        cur_med = next((s[0] for s in scored if s[1] == "dagens barentswatch_point"), None)
        better = cur_med is None or med > cur_med * 1.5
        high = " (høy, sjekk - over 100 % av svellet ute)" if med > HIGH_RATIO else ""
        print(f"  FORSLAG (prosent-metoden): {label} - median {med:.0%}{high} over {n} timer"
              + (f" (dagens {cur_med:.0%})" if cur_med is not None else "")
              + (" - klart bedre, foreslås" if better else " - ikke klart bedre enn dagens, ingen grunn til å flytte")
              + f"\n           {p['link']}\n           Endres IKKE uten Theodors ja.")
    else:
        print("  FORSLAG: ingen kandidat med nok timer.")


# ---------- Sammenligning med observasjonene (Theodors presisering 06.10.2026) ----------
# BarentsWatch sitt punkt-API gir VARSEL, ikke historikk - vi kan ikke spørre
# hva en kandidat viste 26.09. Metoden her: mål forholdet kandidat/dagens
# punkt over timene i result.json (samme timer, parvis), og skaler det
# dagens punkt FAKTISK ga på observasjonsdagene (hentet fra git-historikken
# til forecast.json, samme tall som de faste observasjonene i test_rating.py
# bygger på). Så kjøres HELE produksjonskjeden (rating.rate) på de skalerte
# tallene. Antakelsen - at forholdet mellom to punkter 150-1000 m fra
# hverandre er omtrent stabilt på tvers av svellretning/periode - er et
# ANSLAG, ikke en måling, og merkes slik. Surfehøyden påvirkes ikke av vind
# eller tidevann, så sammenligningen er uavhengig av vindmodell-saken ved
# Unstad (se ROADMAP "Venter på Theodor").

# Dagens punkts inndata på observasjonsdagene. bw_dir i "fra"-konvensjon
# (25./26.09 lå rått som 113/114 "mot" i forecast.json før rettelsen 27.09).
OBSERVATIONS = {
    "unstad": [
        ("26.09 kl. 14:45 - over hodet, tønner, 4 stjerner", 2.4, [
            {"bw_height": 0.9, "bw_dir": 294.8, "bw_period": 15.0, "dir_offshore": 300,
             "swell_offshore": 1.0, "height_offshore": 1.0, "period": 15, "wind_speed": 3.0, "wind_dir": 115},
        ]),
        ("27.09 kl. 06-08 - brysthøy til hodehøy (1,3-1,8 m), ca. 3 stjerner", 1.55, [
            {"bw_height": 0.8366666666666667, "bw_dir": 295.0, "bw_period": 9.8, "swell_offshore": 2.56,
             "height_offshore": 3.5, "dir_offshore": 255, "period": 9.45, "wind_speed": 7.8, "wind_dir": 227.0, "gust": 13.9},
            {"bw_height": 0.7533333333333334, "bw_dir": 295.0, "bw_period": 9.8, "swell_offshore": 2.54,
             "height_offshore": 3.5, "dir_offshore": 255, "period": 9.2, "wind_speed": 6.5, "wind_dir": 211.0, "gust": 12.9},
            {"bw_height": 0.67, "bw_dir": 295.0, "bw_period": 9.8, "swell_offshore": 2.72,
             "height_offshore": 3.4, "dir_offshore": 251, "period": 12.55, "wind_speed": 5.4, "wind_dir": 193.0, "gust": 10.8},
        ]),
        ("28.09 kl. 12-15 - 'Safe to say it's firing', kjeden 1,2 m bekreftet av Theodor", 1.2, [
            {"bw_height": 0.60, "bw_dir": 294.0, "bw_period": 11.5, "swell_offshore": 1.40, "height_offshore": 2.00,
             "dir_offshore": 249, "period": 12.0, "wind_speed": 7.5, "wind_dir": 145.0, "gust": 10.5},
            {"bw_height": 0.58, "bw_dir": 293.5, "bw_period": 11.8, "swell_offshore": 1.35, "height_offshore": 1.95,
             "dir_offshore": 248, "period": 12.1, "wind_speed": 7.8, "wind_dir": 148.0, "gust": 11.0},
            {"bw_height": 0.57, "bw_dir": 295.0, "bw_period": 12.0, "swell_offshore": 1.32, "height_offshore": 1.90,
             "dir_offshore": 250, "period": 12.0, "wind_speed": 8.0, "wind_dir": 150.0, "gust": 11.5},
            {"bw_height": 0.55, "bw_dir": 294.0, "bw_period": 11.6, "swell_offshore": 1.28, "height_offshore": 1.85,
             "dir_offshore": 249, "period": 11.8, "wind_speed": 7.6, "wind_dir": 147.0, "gust": 10.8},
        ]),
        ("05.10 kl. 09-12 - over hodet, hule bølger ('Lofoten leverte bølga')", 2.4, [
            {"bw_height": 0.877, "bw_dir": 294.333, "bw_period": 10.336, "swell_offshore": 1.78, "height_offshore": 3.9,
             "dir_offshore": 268, "period": 8.5, "wind_speed": 8.9, "wind_dir": 204.0, "gust": 17.7},
            {"bw_height": 0.753, "bw_dir": 294.667, "bw_period": 10.368, "swell_offshore": 2.08, "height_offshore": 3.9,
             "dir_offshore": 261, "period": 8.75, "wind_speed": 9.5, "wind_dir": 206.0, "gust": 15.9},
            {"bw_height": 0.63, "bw_dir": 295.0, "bw_period": 10.4, "swell_offshore": 2.4, "height_offshore": 4.0,
             "dir_offshore": 255, "period": 9.0, "wind_speed": 9.2, "wind_dir": 205.0, "gust": 16.0},
            {"bw_height": 0.703, "bw_dir": 295.0, "bw_period": 10.4, "swell_offshore": 2.58, "height_offshore": 4.1,
             "dir_offshore": 254, "period": 9.15, "wind_speed": 9.2, "wind_dir": 199.0, "gust": 15.6},
        ]),
    ],
    "grotfjord": [
        ("24.09 - helt flatt (BarentsWatch 0,3 m)", "flat", [
            {"bw_height": 0.3, "dir_offshore": 311, "turn": 32, "period": 11, "wind_speed": 3, "wind_dir": 180},
        ]),
        ("25.09 kl. 12 - helt flatt, svell ute fra ca. 318", "flat", [
            {"bw_height": 0.12, "bw_dir": 293.0, "bw_period": 6.1, "swell_offshore": 0.9, "dir_offshore": 318, "period": 8.15},
        ]),
        ("26.09 kl. 12 - helt flatt, svell 2,4 m/16 s fra 273 (utenfor vinduet)", "flat", [
            {"bw_height": 0.26, "bw_dir": 294.0, "bw_period": 6.3, "swell_offshore": 2.36, "dir_offshore": 273, "period": 16.45},
        ]),
    ],
    "lenangsoyra": [
        ("26.09 - ikke surfbart, mest vindsjø, bølgene fra vest", "flat", [
            {"bw_height": 0.7, "bw_height_max": 1.4, "swell_offshore": 1.3, "dir_offshore": 277,
             "height_offshore": 2.7, "period": 9, "bw_dir": 290, "wind_speed": 7, "wind_dir": 200, "gust": 10},
        ]),
    ],
}
MIN_RATIO_HEIGHT = 0.05  # m - under dette er forholdet mellom to punkter bare støy


def ratio_to_current(point, current):
    """Median av kandidat/dagens punkt over SAMME timer (parvis), bare timer
    der begge er over MIN_RATIO_HEIGHT. (median, antall timer, min, maks)."""
    ratios = []
    for k, h in point["hours"].items():
        c = current["hours"].get(k)
        if not c or h.get("height") is None or c.get("height") is None:
            continue
        if h["height"] < MIN_RATIO_HEIGHT or c["height"] < MIN_RATIO_HEIGHT:
            continue
        ratios.append(h["height"] / c["height"])
    if not ratios:
        return None, 0, None, None
    return statistics.median(ratios), len(ratios), min(ratios), max(ratios)


def rating_spot(sid, spot):
    """Samme spot-oppsett som de faste observasjonstestene i test_rating.py
    bruker: Unstad med surf_factor fra prior og ekte eksponering (seksjon 16),
    de andre som rene spots.json-dicter. Det er testene som er fasiten her."""
    s = dict(spot)
    if sid == "unstad":
        from rating import SURF_FACTOR_MAX, SURF_FACTOR_MIN
        import fetch
        s["surf_factor"] = round(min(SURF_FACTOR_MAX, max(SURF_FACTOR_MIN, s["surf_factor_prior"])), 2)
        s["surf_factor_source"] = "prior"
        baseline = json.loads((ROOT / "data" / "exposure_baseline.json").read_text(encoding="utf-8"))
        smoothed, raw, _ = fetch.resolve_exposure(s, baseline, s["name"])
        s["exposure_smoothed"], s["exposure_raw"] = smoothed, raw
    return s


def observation_fit(sid, data, spot):
    obs = OBSERVATIONS.get(sid)
    if not obs:
        return
    from rating import rate
    current = data["points"].get("dagens barentswatch_point")
    if not current or not current["hours"]:
        print("  Observasjons-sammenligning: ingen data for dagens punkt, kan ikke skalere.")
        return
    rspot = rating_spot(sid, spot)
    numeric = all(t != "flat" for _, t, _ in obs)
    print(f"\n  Sammenligning med observasjonene (ANSLAG: kandidat/dagens-forhold målt nå, "
          f"skalert på det dagens punkt ga observasjonsdagene):")
    head = "".join(f"{lbl.split(' ')[0]:>8}" for lbl, _, _ in obs)
    print(f"  {'Kandidat':<30}{'forhold':>8}{'timer':>6}{head}{'  avvik' if numeric else '  flate dager'}")
    rows = []
    for label, p in data["points"].items():
        r, n, lo, hi = ratio_to_current(p, current)
        if r is None:
            print(f"  {label:<30}{'-':>8}{n:>6}  (ingen timer med høyde over {MIN_RATIO_HEIGHT} m i begge punkt)")
            continue
        per_date = []
        for _, target, hours in obs:
            vals, stars = [], []
            for h in hours:
                hh = dict(h)
                hh["bw_height"] = h["bw_height"] * r
                res = rate(hh, rspot)
                vals.append(res["surf_height"] if res["surf_height"] is not None else 0.0)
                stars.append(res["stars"])
            per_date.append((statistics.mean(vals), all(s == 0 for s in stars)))
        if numeric:
            err = statistics.mean(abs(m - t) for (m, _), (_, t, _) in zip(per_date, obs))
            cells = "".join(f"{m:>8.2f}" for m, _ in per_date)
            print(f"  {label:<30}{r:>8.2f}{n:>6}{cells}{err:>8.2f}")
            rows.append((err, label, p, r, per_date))
        else:
            flat_days = sum(1 for _, f in per_date if f)
            cells = "".join(f"{('flatt' if f else f'{m:.2f} m'):>8}" for m, f in per_date)
            print(f"  {label:<30}{r:>8.2f}{n:>6}{cells}{flat_days:>8}/{len(obs)}")
            rows.append((-flat_days, label, p, r))
    if not rows:
        return
    if numeric:
        targets = "  ".join(f"{lbl.split(' ')[0]} = {t} m" for lbl, t, _ in obs)
        print(f"  (observert: {targets}; avvik = snitt |anslått - observert| i m)")
        # Fysikk-kontrollør 06.10.2026: med et KONSTANT forhold r skaleres alle
        # datoene likt (surfehøyde ∝ r^0,8), og surf_factor (lært/prior) ville
        # bli kalibrert om igjen og viske ut forskjellen. Tabellen kan derfor
        # IKKE kåre en "beste" kandidat - avviks-rangeringen over er
        # sirkulær. Det eneste gyldige den sier: ingen multiplikativ
        # punktendring kan løfte ÉN dato uten å løfte de andre like mye.
        # Vist med tall: forholdet som trengs for å treffe hver dato alene.
        cur = next((x for x in rows if x[1] == "dagens barentswatch_point"), None)
        if cur:
            needed = []
            for (m, _), (lbl, t, _) in zip(cur[4], obs):
                needed.append((lbl.split(" ")[0], (t / m) ** (1 / 0.8) if m > 0 else float("inf")))
            txt = ", ".join(f"{d}: r={v:.2f}" for d, v in needed)
            lo, hi = min(v for _, v in needed), max(v for _, v in needed)
            print(f"  Forhold som trengs for å treffe hver dato ALENE (dagens punkt, surfehøyde ∝ r^0,8): {txt}")
            print(f"  INGEN kandidat foreslås fra denne metoden: ett og samme forhold kan ikke treffe alle datoene "
                  f"(trenger {lo:.2f} til {hi:.2f}) - en punktflytting løfter alle datoene likt. "
                  f"Avviket som ikke lar seg lukke slik er derfor ikke et punktplasseringsproblem.")
    else:
        cur = next((x for x in rows if x[1] == "dagens barentswatch_point"), None)
        full = [x for x in rows if x[0] == -len(obs)]
        print(f"  {len(full)} av {len(rows)} punkt holder alle {len(obs)} observasjonsdagene flate"
              + (f" (dagens: {-cur[0]}/{len(obs)})" if cur else "") + ".")
        if full:
            # Blant dem som holder alle flate: det med høyest forhold gir mest
            # signal de dagene det faktisk ER svell - men alle i lista passer
            # observasjonene like godt.
            best = max(full, key=lambda x: x[3])
            print(f"  FORSLAG (observasjons-metoden): ingen grunn til å flytte hvis dagens punkt holder alle flate; "
                  f"høyest forhold blant de som passer: {best[1]} ({best[3]:.2f})\n           {best[2]['link']}"
                  f"\n           Endres IKKE uten Theodors ja.")


def main():
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    spots = {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
    print(f"result.json generert {data['generated']}, {data['hours_ahead']} timer frem")
    for sid, sd in data["spots"].items():
        report_spot(sid, sd, spots[sid])
        observation_fit(sid, sd, spots[sid])


if __name__ == "__main__":
    main()
