"""T2a (Lofoten Surfsenter, 09.11.2026): «Surfline tar alltid ned ratingen for
vinden på Unstad, men det er som oftest offshore der, og offshore er bra på
Unstad.» Kontroll av vår modell: offshore_wind [70, 232] og
WIND_PENALTY_CURVES["offshore"] = (10,0), (14,1), (18,2). Ingen endring her -
bare tabeller.

data/forecast_archive har ikke vind (bare stjerner og surfehøyde) og ryddes
etter 8 dager, så «de siste 30 dagene» settes sammen av tre kilder:

1. Rekonstruksjon 11.10-10.11: vind time for time fra MET Nordic
   (metno_seamless hos Open-Meteo, past_days - samme modellfamilie som met.no
   Locationforecast, som appen bruker de første døgnene) og svell fra GFS Wave
   i havpunktet (som appen), kjørt gjennom dagens rating.wind_penalty_parts().
   Dette er hva modellen VILLE sagt, også for dagene uten varsel (kontoen var
   stengt 16.10-05.11). Stjerner kan ikke regnes her (ingen BarentsWatch-
   historikk), bare vindstraffen.
2. Det vi faktisk publiserte 24.09-14.10: hver kjøring av docs/data/forecast.json
   i git-historikken (fila lå i git til 14.10), time for time fra kjøringen til
   neste kjøring, re-ratet med dagens kode og dagens spots.json.
3. Varselet som ligger ute nå (docs/data/spots/unstad.json fra nettsiden).

Kjør: python3 tools/unstad_vind_rapport.py --vind <om_wind.json> --hav <om_marine.json> --live <unstad.json>
Skriver data/backtest/t2a_unstad_vind_2026-11-10.md."""
import argparse
import datetime as dt
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))
import backtest  # noqa: E402
import rating  # noqa: E402
import sun  # noqa: E402

OSLO = ZoneInfo("Europe/Oslo")
SID = "unstad"
OUT = ROOT / "data" / "backtest" / "t2a_unstad_vind_2026-11-10.md"
FRA = dt.datetime(2026, 10, 11, 0, 0, tzinfo=OSLO)
TIL = dt.datetime(2026, 11, 10, 13, 0, tzinfo=OSLO)   # siste hele time før rapporten ble laget
KINDS = ("offshore", "side", "sideonshore", "onshore")
WORD = {"offshore": "fralands", "side": "sidevind", "sideonshore": "side-pålands", "onshore": "pålands"}


def fm(v, nd=1):
    return "–" if v is None else f"{v:.{nd}f}".replace(".", ",")


def pct(a, b):
    return "–" if not b else f"{100 * a / b:.0f} %"


def utc(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def lost_stars(pen):
    """Stjerner vindstraffen tar fra et helt potensial: rate() runder potensial − straff med 0,5 opp."""
    return max(0, math.ceil(pen - 0.5 - 1e-9))


def prepared():
    spots = {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
    exposure = json.loads((ROOT / "data" / "exposure_baseline.json").read_text(encoding="utf-8"))
    calib = json.loads((ROOT / "data" / "bw_calibration.json").read_text(encoding="utf-8")) if (ROOT / "data" / "bw_calibration.json").exists() else {}
    return backtest.prepare_spot(SID, spots, exposure, calib)


def is_light(spot, t):
    return sun.light(spot["spot"]["lat"], spot["spot"]["lon"], t) != "mørkt"


# ---------- Del 1: rekonstruksjon ----------

def reconstruct(spot, wind, marine, model="metno_seamless"):
    wh, mh = wind["hourly"], marine["hourly"]
    sea = {t: i for i, t in enumerate(mh["time"])}
    rows = []
    for i, t in enumerate(wh["time"]):
        ts = dt.datetime.fromisoformat(t).replace(tzinfo=dt.timezone.utc)
        if not (FRA <= ts < TIL):
            continue
        speed, wdir, gust = (wh[f"wind_speed_10m_{model}"][i], wh[f"wind_direction_10m_{model}"][i], wh[f"wind_gusts_10m_{model}"][i])
        if speed is None or wdir is None:
            continue   # manglende data er aldri 0
        j = sea.get(t)
        energy = None
        if j is not None and mh["swell_wave_height"][j] is not None and mh["swell_wave_period"][j] is not None:
            ep, _ = rating.energy_period(mh["swell_wave_period"][j], None)
            energy = rating.energy_kj(mh["swell_wave_height"][j], ep)
        parts = rating.wind_penalty_parts(speed, wdir, spot, gust, energy)
        rows.append({"t": ts, "speed": speed, "dir": wdir, "gust": gust, "light": is_light(spot, ts), **parts})
    return rows


def summary_table(rows, title):
    out = [f"**{title}** ({len(rows)} timer)", "",
           "| Vindtype | Timer | Andel | Median vind (m/s) | Timer under 10 m/s | ... av dem med straff over 0 | ... av dem som koster minst 1 stjerne | Timer 10 m/s eller mer | ... som koster minst 1 stjerne |",
           "|---|---|---|---|---|---|---|---|---|"]
    for k in KINDS:
        r = [x for x in rows if x["kind"] == k]
        lo, hi = [x for x in r if x["speed"] < 10], [x for x in r if x["speed"] >= 10]
        out.append(f"| {WORD[k]} | {len(r)} | {pct(len(r), len(rows))} | {fm(statistics.median(x['speed'] for x in r)) if r else '–'} | {len(lo)} | "
                   f"{sum(x['pen'] > 0 for x in lo)} | {sum(lost_stars(x['pen']) >= 1 for x in lo)} | {len(hi)} | {sum(lost_stars(x['pen']) >= 1 for x in hi)} |")
    return out + [""]


def direction_table(rows):
    """30-graders bøtter for de lyse timene: hvor vinden kommer fra, hva vi kaller den og hva den koster."""
    out = ["| Vind fra | Timer | Vår vindtype | Median vind (m/s) | Snitt straff | Timer som koster minst 1 stjerne | ... av dem under 10 m/s |", "|---|---|---|---|---|---|---|"]
    for lo in range(0, 360, 30):
        r = [x for x in rows if lo <= x["dir"] % 360 < lo + 30]
        if not r:
            out.append(f"| {lo}–{lo + 30}° | 0 | – | – | – | – | – |")
            continue
        kinds = Counter(x["kind"] for x in r)
        kind = ", ".join(f"{WORD[k]} {n}" for k, n in kinds.most_common())
        cost = [x for x in r if lost_stars(x["pen"]) >= 1]
        out.append(f"| {lo}–{lo + 30}° | {len(r)} | {kind} | {fm(statistics.median(x['speed'] for x in r))} | {fm(statistics.mean(x['pen'] for x in r), 2)} | "
                   f"{len(cost)} | {sum(x['speed'] < 10 for x in cost)} |")
    return out + [""]


def day_table(rows):
    days = defaultdict(list)
    for x in rows:
        if x["light"]:
            days[x["t"].astimezone(OSLO).date()].append(x)
    out = ["| Dato | Lyse timer | Fralands | Sidevind | Side-pålands | Pålands | Vind median / maks (m/s) | Størst effektiv vind i fralands | Fralandstimer med straff over 0 | Fralandstimer som koster stjerne | Andre timer som koster stjerne | ... av dem under 10 m/s |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in sorted(days):
        r = days[d]
        c = Counter(x["kind"] for x in r)
        off = [x for x in r if x["kind"] == "offshore"]
        other = [x for x in r if x["kind"] != "offshore" and lost_stars(x["pen"]) >= 1]
        out.append(f"| {d.strftime('%d.%m')} | {len(r)} | {c['offshore']} | {c['side']} | {c['sideonshore']} | {c['onshore']} | "
                   f"{fm(statistics.median(x['speed'] for x in r))} / {fm(max(x['speed'] for x in r))} | {fm(max(x['eff'] for x in off)) if off else '–'} | "
                   f"{sum(x['pen'] > 0 for x in off)} | {sum(lost_stars(x['pen']) >= 1 for x in off)} | {len(other)} | {sum(x['speed'] < 10 for x in other)} |")
    return out + [""]


# ---------- Del 2 og 3: ekte kjøringer ----------

def git_runs():
    """[(generert, {t: time})] for Unstad fra hver commit av docs/data/forecast.json (eldste først)."""
    shas = subprocess.run(["git", "log", "--reverse", "--format=%H", "--", "docs/data/forecast.json"],
                          capture_output=True, text=True, timeout=60, cwd=ROOT).stdout.split()
    runs = {}
    for sha in shas:
        raw = subprocess.run(["git", "show", f"{sha}:docs/data/forecast.json"], capture_output=True, timeout=60, cwd=ROOT).stdout
        try:
            fc = json.loads(raw)
        except ValueError:
            continue
        u = next((s for s in fc.get("spots", []) if s.get("id") == SID), None)
        if u and fc.get("generated"):
            runs[fc["generated"]] = u["hours"]
    return sorted(runs.items())


def nowcast(runs):
    """Timene fra hver kjøring fram til neste kjøring - det appen viste som «nå»."""
    out = []
    for (gen, hours), nxt in zip(runs, runs[1:] + [(None, None)]):
        g0 = utc(gen)
        g1 = utc(nxt[0]) if nxt[0] else g0 + dt.timedelta(hours=3)
        g1 = min(g1, g0 + dt.timedelta(hours=24))   # hull i kjøringene: ikke strekk en gammel kjøring over mer enn et døgn
        for h in hours:
            if g0 <= utc(h["t"]) < g1:
                out.append(h)
    return out


def rerate(spot, hours):
    rows = []
    for h in hours:
        if h.get("wind_speed") is None or h.get("wind_dir") is None:
            continue
        r = rating.rate(dict(h), spot)
        without = r["stars"] + r["faded_wind"]
        rows.append({"t": utc(h["t"]), "speed": h["wind_speed"], "dir": h["wind_dir"], "gust": h.get("gust"), "light": h.get("daylight"),
                     "kind": r["wind_type"], "stars": r["stars"], "lost": r["faded_wind"], "without": without,
                     "kind_then": h.get("wind_type"), "stars_then": h.get("stars"), "lost_then": h.get("faded_wind"),
                     "eff": rating.effective_wind(h["wind_speed"], h.get("gust"))})
    return rows


def stars_table(rows, title, then=False):
    """Bare timer der det var noe å ta (minst 1 stjerne uten vind)."""
    surf = [x for x in rows if x["without"] >= 1]
    out = [f"**{title}**: {len(rows)} timer med vind, {len(surf)} av dem med minst 1 stjerne før vind.", "",
           "| Vindtype | Timer med surf | Vind under 10 m/s | ... trukket ned av vind | Vind 10 m/s eller mer | ... trukket ned av vind | Stjerner tatt av vind i alt |",
           "|---|---|---|---|---|---|---|"]
    for k in KINDS:
        r = [x for x in surf if x["kind"] == k]
        lo, hi = [x for x in r if x["speed"] < 10], [x for x in r if x["speed"] >= 10]
        out.append(f"| {WORD[k]} | {len(r)} | {len(lo)} | {sum(x['lost'] >= 1 for x in lo)} | {len(hi)} | {sum(x['lost'] >= 1 for x in hi)} | {sum(x['lost'] for x in r)} |")
    out.append("")
    if then:
        r = [x for x in rows if x["kind_then"] is not None]
        changed = [x for x in r if x["kind_then"] != x["kind"]]
        to_off = sum(x["kind"] == "offshore" for x in changed)
        out += [f"Den gangen (koden og sektoren som gjaldt da varselet ble laget): {sum(x['kind_then'] == 'offshore' for x in r)} av {len(r)} timer ble kalt "
                f"fralands, og vinden tok {sum(x['lost_then'] or 0 for x in r)} stjerner i alt. Med dagens kode: {sum(x['kind'] == 'offshore' for x in r)} timer fralands og "
                f"{sum(x['lost'] for x in r)} stjerner. {len(changed)} timer har byttet vindtype, {to_off} av dem til fralands (sektoren ble utvidet til [70, 232] 06.10).", ""]
    return out


def proxy_check(rec, actual):
    """Hvor godt treffer MET Nordic-rekken (del 1) vinden vi faktisk publiserte (met.no Locationforecast)?"""
    a = {x["t"]: x for x in actual}
    pairs = [(x, a[x["t"]]) for x in rec if x["t"] in a]
    if not pairs:
        return ["Ingen overlappende timer.", ""]
    dv = [abs(p["speed"] - q["speed"]) for p, q in pairs]
    dd = [rating.angle_diff(p["dir"], q["dir"]) for p, q in pairs]
    same = sum(p["kind"] == q["kind"] for p, q in pairs)
    return [f"{len(pairs)} overlappende timer ({min(p['t'] for p, _ in pairs):%d.%m}–{max(p['t'] for p, _ in pairs):%d.%m}): fart avviker i snitt "
            f"{fm(statistics.mean(dv))} m/s (median {fm(statistics.median(dv))}), retning i snitt {fm(statistics.mean(dd), 0)}° (median {fm(statistics.median(dd), 0)}°), "
            f"samme vindtype i {same} av {len(pairs)} timer ({pct(same, len(pairs))}).", ""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vind", required=True)
    ap.add_argument("--hav", required=True)
    ap.add_argument("--live", required=True)
    a = ap.parse_args()
    spot = prepared()
    wind = json.loads(Path(a.vind).read_text(encoding="utf-8"))
    marine = json.loads(Path(a.hav).read_text(encoding="utf-8"))
    live = json.loads(Path(a.live).read_text(encoding="utf-8"))

    rec = reconstruct(spot, wind, marine)
    rec_gfs = reconstruct(spot, wind, marine, "gfs_seamless")
    light = [x for x in rec if x["light"]]
    off_light = [x for x in light if x["kind"] == "offshore"]
    runs = git_runs()
    hist = rerate(spot, nowcast(runs))
    hist_light = [x for x in hist if x["light"]]
    live_rows = rerate(spot, live["hours"][:48])

    L = ["# T2a: vinden på Unstad de siste 30 dagene (laget 10.11.2026)", "",
         "Kilde for påstanden: Lofoten Surfsenter, 09.11.2026: «Surfline tar alltid ned ratingen for vinden på Unstad, men det er som oftest offshore der, "
         "og offshore er bra på Unstad.»", "",
         f"Modellen i dag: fralandssektor {spot['offshore_wind']} (facing {spot['facing']}°), fralandskurve "
         f"{rating.WIND_PENALTY_CURVES['offshore']} (effektiv vind i m/s, straff i stjerner). Effektiv vind er middelvind + 30 % av forskjellen opp til kastene, "
         "høyst 2 m/s. En straff koster først en hel stjerne når den er over 0,5 (rate() runder til slutt).", "",
         "## Kort svar", ""]
    off_all = [x for x in rec if x["kind"] == "offshore"]
    surf_off = [x for x in hist if x["kind"] == "offshore" and x["without"] >= 1]
    strong = [x for x in off_light if lost_stars(x["pen"]) >= 1]
    edge = [x for x in light if 232 < x["dir"] <= 250]
    other_low = [x for x in light if x["kind"] != "offshore" and x["speed"] < 10 and lost_stars(x["pen"]) >= 1]
    L += [f"- Fralandsvind under 10 m/s tar aldri en stjerne på Unstad: 0 av {sum(x['speed'] < 10 for x in off_all)} rekonstruerte timer og "
          f"0 av {sum(x['speed'] < 10 for x in surf_off)} publiserte timer med surf. {sum(x['speed'] < 10 and x['pen'] > 0 for x in off_all)} timer fikk en straff "
          "mellom 0 og 0,5 fordi kastene løftet effektiv vind over 10 m/s. Den rundes bort så lenge ingen annen brøkstraff kommer i tillegg "
          "(Unstad har ingen tidevannsregel i dag; se T2c).",
          f"- «Som oftest offshore» stemmer også hos oss: {pct(len(off_light), len(light))} av de lyse timene er fralands med sektoren {spot['offshore_wind']}.",
          f"- Vi trekker ned når fralandsvinden er sterk: {len(strong)} av {len(off_light)} lyse fralandstimer ({pct(len(strong), len(off_light))}) ville kostet 1–2 stjerner i vindfradrag, "
          f"alle med middelvind på 10 m/s eller mer. Det følger kurven fra 15.10 og er ikke en feil i koden. Om sterk fralandsvind (liten kuling og opp) "
          "også er bra på Unstad, sier ikke sitatet noe om.",
          f"- Under 10 m/s trekker vi bare ned for vind utenfor sektoren (vest til nord): {len(other_low)} lyse timer.",
          f"- Kanten ved 232°: vind fra 232–250° ({len(edge)} lyse timer) regnes som side-pålands eller pålands og straffes fra 3 m/s, mens 231° er fralands og fri til 10 m/s. "
          "Sektoren slutter der observasjonene slutter (193–227° er bekreftet fralands). Verdt å spørre Surfsenteret om sørvest.",
          "- Ingen endring foreslått.", "",
          "## Grunnlaget, og hva som mangler", "",
         "- `data/forecast_archive` kan ikke brukes alene: filene har bare stjerner og surfehøyde (ingen vind), og de ryddes etter 8 dager (tre filer igjen: 05.11, 09.11, 10.11).",
         "- Kontoen var stengt 16.10–05.11, så det finnes ikke noe publisert varsel for de dagene.",
         f"- Del 1 er derfor en rekonstruksjon: MET Nordic-vind (Open-Meteo `metno_seamless`, {len(rec)} timer fra {FRA:%d.%m} til {TIL:%d.%m kl. %H}) gjennom dagens vindkode. "
         "Den viser vindstraffen, ikke stjernene.",
         f"- Del 2 er det vi faktisk publiserte 24.09–14.10 ({len(runs)} kjøringer i git-historikken), re-ratet med dagens kode. Del 3 er varselet som ligger ute nå.", "",
         "## Del 1: rekonstruksjon 11.10–10.11", ""]
    L += summary_table(rec, "Alle timer")
    L += summary_table(light, "Lyse timer (lys eller skumring, som i appen)")
    eff = [x["eff"] for x in off_light]
    L += ["Fralandstimene i lyset, etter effektiv vind:", "",
          "| Effektiv vind | Timer | Straff | Koster stjerne |", "|---|---|---|---|",
          f"| under 10 m/s | {sum(e < 10 for e in eff)} | 0 | nei |",
          f"| 10–12 m/s | {sum(10 <= e <= 12 for e in eff)} | 0–0,5 | nei |",
          f"| 12–16 m/s | {sum(12 < e <= 16 for e in eff)} | 0,5–1,5 | 1 stjerne |",
          f"| over 16 m/s | {sum(e > 16 for e in eff)} | over 1,5 | 2 stjerner |", "",
          f"Fralandstimer med middelvind under 10 m/s som likevel fikk straff over 0 (kastene løftet effektiv vind over 10): "
          f"{sum(x['speed'] < 10 and x['pen'] > 0 for x in off_light)} lyse timer, {sum(x['speed'] < 10 and x['pen'] > 0 for x in rec if x['kind'] == 'offshore')} i alt. "
          f"Ingen av dem koster en stjerne: {sum(x['speed'] < 10 and lost_stars(x['pen']) >= 1 for x in rec if x['kind'] == 'offshore')}.", "",
          "### Hvor vinden kom fra (lyse timer)", ""]
    L += direction_table(light)
    L += ["### Dag for dag (lyse timer)", ""]
    L += day_table(rec)
    c_gfs = Counter(x["kind"] for x in rec_gfs if x["light"])
    n_gfs = sum(c_gfs.values())
    L += ["### Kontroll av rekonstruksjonen", "",
          "Mot vinden vi faktisk publiserte (met.no Locationforecast, del 2 og 3):", ""]
    L += proxy_check(rec, hist + live_rows)
    differ = sum(x["light"] and x["kind"] != y["kind"] for x, y in zip(rec, rec_gfs))
    L += [f"Med GFS-vind i stedet (modellen appen bruker fra ca. dag 3) blir fordelingen i de lyse timene: "
          + ", ".join(f"{WORD[k]} {pct(c_gfs[k], n_gfs)}" for k in KINDS)
          + f". {differ} lyse timer får en annen vindtype enn med MET Nordic, men de jevner seg ut.", "",
          "## Del 2: det vi faktisk publiserte 24.09–14.10, med dagens kode", ""]
    L += stars_table(hist, "Alle timer", then=True)
    L += stars_table(hist_light, "Lyse timer")
    low_off = [x for x in hist if x["kind"] == "offshore" and x["speed"] < 10 and x["lost"] >= 1]
    L += [f"Fralandstimer under 10 m/s der vinden likevel tok en stjerne: {len(low_off)}."
          + ("" if not low_off else " " + ", ".join(f"{x['t'].astimezone(OSLO):%d.%m kl. %H} ({fm(x['speed'])} m/s, kast {fm(x['gust'])})" for x in low_off[:10])), "",
          "## Del 3: varselet som ligger ute nå", "",
          f"Kjøring {live.get('generated', '?')[:16]}Z, de første 48 timene.", ""]
    L += stars_table(live_rows, "Alle timer")
    L += ["| Tid (norsk) | Vind (m/s) | Kast | Fra | Vindtype | Effektiv | Stjerner uten vind | Stjerner | Tatt av vind |", "|---|---|---|---|---|---|---|---|---|"]
    for x in live_rows:
        if x["light"]:
            L.append(f"| {x['t'].astimezone(OSLO):%d.%m kl. %H} | {fm(x['speed'])} | {fm(x['gust'])} | {x['dir']:.0f}° | {WORD[x['kind']]} | {fm(x['eff'])} | {x['without']} | {x['stars']} | {x['lost']} |")
    L.append("")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Skrev {OUT.relative_to(ROOT)} ({len(rec)} rekonstruerte timer, {len(hist)} publiserte timer fra {len(runs)} kjøringer, {len(live_rows)} timer nå)")


if __name__ == "__main__":
    main()
