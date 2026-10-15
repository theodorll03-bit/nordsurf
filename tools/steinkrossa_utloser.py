"""Steinkrøssa: nytt BarentsWatch-snitt første dag med ekte svell inn i vinduet (Theodor 15.10.2026,
nattjobben ROADMAP K del 0.4).

Skyggepunktet for Steinkrøssa (1 400 m ut, 29 m dyp - data/bw_point_search/snitt_2026-10-15.md) ble
valgt på en dag med vindsjø fra SSV, og ligger trolig utenfor skjermingen. Snittet skal derfor tas på
nytt første gang varselet har svell ute på minst 1,5 m og 10 s fra innenfor Steinkrøssas vindu, i
timer BarentsWatch dekker (t <= bw_until - snittet henter BarentsWatch sitt eget varsel for de
timene). Resultatet går i data/bw_point_search/ (egen fil, result.json røres ikke). Punktet flyttes
ALDRI automatisk - det er Theodors avgjørelse.

Kjøres daglig fra Testlab-workflowen (.github/workflows/backtest.yml, jobben steinkrossa_snitt):
  python tools/steinkrossa_utloser.py sjekk     -> skriver trigger=1/0 og hour=<UTC> til $GITHUB_OUTPUT
  python tools/steinkrossa_utloser.py ferdig <UTC-time> <resultatfil> -> noterer at snittet er tatt
Etter «ferdig» gjør «sjekk» ingenting mer (første dag, ikke hver dag).

Leser bare docs/data/forecast.json (hentet med fetcher/hent_varsel.sh). Manglende verdier (None)
oppfyller aldri vilkårene."""
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))
from rating import in_sector  # noqa: E402

SPOT = "steinkrossa"
MIN_SWELL_M = 1.5
MIN_PERIOD_S = 10.0
STATE = ROOT / "data" / "bw_point_search" / "steinkrossa_utloser.json"
FORECAST = ROOT / "docs" / "data" / "forecast.json"


def qualifying_hours(forecast, spot_cfg, now):
    """Timer fra nå til bw_until med svell ute >= 1,5 m, periode >= 10 s og retning i vinduet."""
    sp = next((s for s in forecast["spots"] if s["id"] == SPOT), None)
    if not sp or not sp.get("bw_until"):
        return []
    until = sp["bw_until"]
    out = []
    for h in sp["hours"]:
        t = dt.datetime.fromisoformat(h["t"].replace("Z", "+00:00"))
        # find_bw_point.py henter 48 timer frem - timen må ligge innenfor både bw_until og de 48 timene
        if t < now or h["t"] > until or t > now + dt.timedelta(hours=45):
            continue
        # bare ekte svell (GFS Wave eller standardmodellen) - reserven «total_fallback» er totalhøyde med
        # retning/periode fra hele sjøtilstanden (vindsjø inkludert) og teller ikke (fysikk-kontrollør 15.10)
        if h.get("swell_model") not in ("gfs", "standard"):
            continue
        sw, per, d = h.get("swell_offshore"), h.get("period"), h.get("dir_offshore")
        if sw is None or per is None or d is None:
            continue
        if sw >= MIN_SWELL_M and per >= MIN_PERIOD_S and in_sector(d, spot_cfg["swell_window"]):
            out.append(h)
    return out


def emit(**kw):
    path = os.environ.get("GITHUB_OUTPUT")
    lines = [f"{k}={v}" for k, v in kw.items()]
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print(" ".join(lines))


def sjekk():
    if STATE.exists():
        st = json.loads(STATE.read_text(encoding="utf-8"))
        print(f"Snittet er alt tatt {st.get('kjort')} (time {st.get('time')}) - gjør ingenting.")
        return emit(trigger=0, hour="")
    if not FORECAST.exists():
        print("Fant ikke docs/data/forecast.json - ingen sjekk i dag.")
        return emit(trigger=0, hour="")
    spots = {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
    fc = json.loads(FORECAST.read_text(encoding="utf-8"))
    hits = qualifying_hours(fc, spots[SPOT], dt.datetime.now(dt.timezone.utc))
    if not hits:
        print(f"Ingen timer med svell ute >= {MIN_SWELL_M} m og {MIN_PERIOD_S:.0f} s fra vinduet {spots[SPOT]['swell_window']} innen bw_until.")
        return emit(trigger=0, hour="")
    best = max(hits, key=lambda h: (h["swell_offshore"], h["period"]))
    print(f"{len(hits)} timer oppfyller vilkårene; sterkest {best['t']}: {best['swell_offshore']} m, {best['period']} s fra {best['dir_offshore']}°.")
    # BarentsWatch har 3-timers steg (00, 03, 06 … UTC): nærmeste steg, aldri før nå
    t = dt.datetime.fromisoformat(best["t"].replace("Z", "+00:00"))
    t3 = t.replace(minute=0) + dt.timedelta(hours=round((t.hour % 3) / 3) * 3 - t.hour % 3)
    if t3 < dt.datetime.now(dt.timezone.utc):
        t3 += dt.timedelta(hours=3)
    emit(trigger=1, hour=t3.strftime("%Y-%m-%dT%H:00Z"))


def has_data(hour, res_file):
    """Fikk snittet BarentsWatch-tall for timen? (minst tre punkter med høyde)"""
    try:
        res = json.loads((ROOT / res_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    pts = res.get("spots", {}).get(SPOT, {}).get("points", {})
    return sum(1 for p in pts.values() if (p.get("hours", {}).get(hour) or {}).get("height") is not None) >= 3


def ferdig(hour, res_file):
    if not has_data(hour, res_file):
        # ikke noter noe - jobben prøver igjen neste dag (ett mislykket snitt skal ikke bruke opp forsøket)
        print(f"Snittet mangler BarentsWatch-tall for {hour} - ingen tilstand skrevet, prøver igjen neste dag.")
        return
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"kjort": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "time": hour,
                                 "resultat": res_file, "vilkaar": f"svell ute >= {MIN_SWELL_M} m, >= {MIN_PERIOD_S:.0f} s, i vinduet, innen bw_until",
                                 "_merk": "Punktet flyttes ikke automatisk - Theodor avgjør (ROADMAP K del 0.4)."},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Notert: {STATE}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "sjekk":
        sjekk()
    elif len(sys.argv) >= 4 and sys.argv[1] == "ferdig":
        ferdig(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
