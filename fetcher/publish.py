"""S2 (ROADMAP oppgave S, Theodors ja 10.10.2026): delte datafiler for appen.

Leser varselet henteren har skrevet (docs/data/forecast.json - fetch.py er
uendret) og skriver filene appen faktisk laster:

  docs/data/oversikt.json       lastes ved åpning: alle spots med spotfeltene
                                (vindu, kalibrering, lokale regler ...) og
                                timene i forsidens rekkevidde (HOME_DAYS døgn)
                                med BARE feltene forsiden leser (HOME_HOUR_FIELDS)
  docs/data/spots/<id>.json     lastes når en spot åpnes: alle timene med alle
                                felt unntatt de appen aldri leser (DETAIL_EXCLUDE)
  docs/data/forecast.json       hele varselet UTEN «hemmelig»-spots (publiseres i
                                overgangen for eldre app-versjoner, og er det
                                verktøyene henter - se hent_varsel.sh)

Alle filene har samme «run» (et fingeravtrykk av varselets innhold): appen
blander aldri oversikten fra én kjøring med en detaljfil fra en annen - to
kjøringer i samme time har samme «generated» (fetch.py runder ned til hel time).

Ren omforming - ingen tall regnes eller endres her, feltene kopieres som de
er (og et felt som mangler, mangler fortsatt: aldri 0, se grunnregelen).

Atomisk: alt skrives i en ny mappe ved siden av og byttes inn til slutt
(detaljfilene først, oversikt.json sist), så appen aldri ser en halv kjøring.

Spots med status «hemmelig» publiseres aldri - verken i oversikten, som
detaljfil eller i forecast.json (CLAUDE.md: en statisk side kan ikke holde noe
hemmelig; artifacten «varsel» i et offentlig repo kan lastes ned av alle).

Feltlistene er låst av testene: docs/js skal ikke lese noe felt i
DETAIL_EXCLUDE (test_publish.py), og forsiden skal se lik ut med bare
oversikten som med hele varselet (test_design_browser.py).

Kjør: python fetcher/publish.py [--src docs/data/forecast.json] [--out docs/data]"""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "data" / "forecast.json"
OUT = ROOT / "docs" / "data"

# Forsidens timefelt (målt 14.10.2026: hver time pakket i en Proxy mens forsiden
# - svarlinje, liste, kart, uke, avspilling, tidspille, regionvalg - kjørte i
# mobil og PC; pluss feltene i grener dagens data ikke traff: daylight når light
# mangler, faded_wind/faded_tide/sources_disagree i ordet ved 0 stjerner,
# energy_total_kj når svellfeltet mangler).
# + «transfer»: Logger-siden viser første times transfer når spoten mangler
# calibration.transfer_used (eldre varsel) - uten feltet ville den vist
# standardverdien som et faktum (fysikk-kontrollør 14.10.2026).
HOME_HOUR_FIELDS = (
    "t", "stars", "faded", "light", "daylight", "surf_height", "low_reason", "period",
    "local_rules", "zero_losses", "faded_wind", "faded_tide", "sources_disagree",
    "energy_swell_kj", "energy_total_kj", "swell_offshore", "swell_model", "transfer",
    # Spotside/søk (Theodor 15.10.2026): Hjem og Utforsk viser høydespennet, vinden
    # (m/s og type) og svellet ute med retning uten å åpne spoten.
    "surf_height_sets", "wind_speed", "wind_type", "dir_offshore",
)

# Detaljfila: ALLE timefelt unntatt de som aldri leses av docs/js (målt
# 14.10.2026 mot varselets 67 felt: 55 leses, disse 12 aldri - de blir igjen i
# henterens eget varsel og arkiv). Utelatt-liste, ikke tillatt-liste: et nytt
# felt henteren legger til, kommer med av seg selv - ord og forklaringer kan
# aldri forsvinne stille. test_publish.py sjekker at docs/js ikke leser noen av dem.
DETAIL_EXCLUDE = (
    "breaking_height", "bw_dir_raw", "bw_file_source", "bw_source", "dir_spot", "energy_period_source",
    "height_spot_model", "likely_flat", "spot_direction_offshore", "spot_direction_overridden",
    "swell_peak_period", "turn",
)

HOME_DAYS = 9   # glidebryteren dekker 7 døgn; to døgns margin så ukeoversikten er lik også når varselet er litt gammelt


def _t(h):
    return datetime.fromisoformat(h["t"].replace("Z", "+00:00"))


def _pick(h, fields):
    # bare felt som FINNES i timen - et felt som mangler skal fortsatt mangle (aldri 0/None lagt til)
    return {k: h[k] for k in fields if k in h}


def public_forecast(forecast):
    """Varselet uten «hemmelig»-spots (samme objekt hvis det ikke finnes noen)."""
    spots = forecast.get("spots", [])
    if not any(s.get("status") == "hemmelig" for s in spots):
        return forecast
    return dict(forecast, spots=[s for s in spots if s.get("status") != "hemmelig"])


def run_id(forecast):
    """Fingeravtrykk av varselets innhold (12 hex) - likt for samme varsel, ulikt ellers."""
    return hashlib.sha256(json.dumps(forecast, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def split(forecast, exclude=DETAIL_EXCLUDE, home_fields=HOME_HOUR_FIELDS, home_days=HOME_DAYS):
    """(oversikt, {spot_id: detalj}) fra et helt varsel. Endrer ikke varselet."""
    forecast = public_forecast(forecast)
    spots = forecast.get("spots", [])
    run = run_id(forecast)
    top = {k: v for k, v in forecast.items() if k != "spots"}
    overview = dict(top, format="oversikt-1", run=run, home_days=home_days, spots=[])
    details = {}
    for s in spots:
        hours = s.get("hours", [])
        t0 = _t(hours[0]) if hours else None
        horizon = t0 + timedelta(days=home_days) if t0 else None
        meta = {k: v for k, v in s.items() if k != "hours"}
        overview["spots"].append(dict(meta, hours=[_pick(h, home_fields) for h in hours if _t(h) <= horizon]))
        details[s["id"]] = {"format": "spot-1", "generated": forecast.get("generated"), "run": run, "id": s["id"],
                            "hours": [{k: v for k, v in h.items() if k not in exclude} for h in hours]}
    return overview, details


def write(forecast, out_dir=OUT):
    """Skriv oversikt.json, spots/<id>.json og forecast.json (uten «hemmelig») atomisk inn i out_dir."""
    out_dir = Path(out_dir)
    overview, details = split(forecast)
    public = public_forecast(forecast)
    tmp = out_dir / ".publish-tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "spots").mkdir(parents=True)
    for sid, d in details.items():
        (tmp / "spots" / f"{sid}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (tmp / "oversikt.json").write_text(json.dumps(overview, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # samme formatering som fetch.py - uten «hemmelig» er fila byte for byte den henteren skrev
    (tmp / "forecast.json").write_text(json.dumps(public, ensure_ascii=False), encoding="utf-8")
    # bytt inn: detaljfilene først, oversikten sist (appen leser oversikten først)
    old_spots = out_dir / "spots"
    if old_spots.exists():
        shutil.rmtree(old_spots)
    (tmp / "spots").rename(old_spots)
    (tmp / "forecast.json").replace(out_dir / "forecast.json")
    (tmp / "oversikt.json").replace(out_dir / "oversikt.json")
    shutil.rmtree(tmp)
    return overview, details


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", default=str(SRC))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    forecast = json.loads(Path(a.src).read_text(encoding="utf-8"))
    overview, details = write(forecast, a.out)
    ov = Path(a.out) / "oversikt.json"
    sizes = [(Path(a.out) / "spots" / f"{sid}.json").stat().st_size for sid in details]
    print(f"Skrev {ov} ({ov.stat().st_size // 1024} KiB, {len(overview['spots'])} spots, "
          f"{len(overview['spots'][0]['hours']) if overview['spots'] else 0} timer per spot) og {len(details)} detaljfiler "
          f"(snitt {sum(sizes) // max(1, len(sizes)) // 1024} KiB)")


if __name__ == "__main__":
    main()
