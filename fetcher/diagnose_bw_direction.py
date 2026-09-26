"""Engangsdiagnose: er BarentsWatch sin totalMeanWaveDirection "fra" eller "mot"?

Kjøres bare manuelt via workflow_dispatch (se .github/workflows/diagnose_bw.yml).
Skriver ALDRI ut nøkler, token eller Authorization-headeren.

Henter rå BarentsWatch-data (uten sources.py sin tolkning, for å se de faktiske
feltene og hvilket punkt BarentsWatch valgte), og Open-Meteo sin GFS Wave-modell
for de samme spotenes havpunkt (samme modell som fetch.py bruker i drift -
ECMWF WAM ble vurdert, men gir ingen svelldekomponering på Open-Meteo i det
hele tatt, bekreftet tidligere i dette prosjektet - GFS Wave er den eneste av
de to som faktisk har swell_wave_direction å sammenligne mot).

For hver time regnes vinkelforskjellen (korteste vei, 0-180) mellom
totalMeanWaveDirection og:
  - Open-Meteo sin totale bølgeretning (wave_direction) - "total mot total"
  - Open-Meteo sin svellretning (swell_wave_direction) - "total mot svell"
Bare timer der svellet dominerer (swell >= 70 % av total) telles i
konklusjonen, med Unstad og Russelv fremhevet (mest åpne, minst lokal
avbøying nær land).
"""
import os
import json
import datetime as dt
from pathlib import Path

import requests
import sources

ROOT = Path(__file__).resolve().parent.parent
HOURS_AHEAD = 24


def angle_diff(a, b):
    d = abs((a - b) % 360)
    return 360 - d if d > 180 else d


def openmeteo_with_total_dir(lat, lon):
    """sources._openmeteo_fetch() henter wave_direction fra Open-Meteo, men
    forkaster den (bare swell_dir brukes i drift) - egen variant her som
    beholder den, siden vi trenger BEGGE (total og svell) til sammenligningen."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wave_height,wave_direction,swell_wave_height,swell_wave_direction,swell_wave_period",
        "timezone": "GMT",
        "forecast_days": 2,
        "models": sources.OPENMETEO_SWELL_MODEL,
    }
    r = sources._get("https://marine-api.open-meteo.com/v1/marine", params)
    h = r.json()["hourly"]
    out = {}
    for i, t in enumerate(h["time"]):
        key = t + "Z" if len(t) == 16 else t
        key = key[:13] + ":00Z"
        out[key] = {
            "wave_height": h["wave_height"][i],
            "wave_dir": h["wave_direction"][i],
            "swell_height": h["swell_wave_height"][i],
            "swell_dir": h["swell_wave_direction"][i],
        }
    return out


def raw_barentswatch(lat, lon):
    """Som sources.barentswatch_point(), men beholder RÅ felt (inkl. punktet
    BarentsWatch faktisk valgte) i stedet for å tolke dem."""
    url = os.environ.get("BW_POINT_URL")
    token = sources.barentswatch_token()
    if not url or not token:
        print("  (mangler BW_POINT_URL eller klarte ikke å hente token)")
        return []
    r = requests.get(
        url.format(lat=lat, lon=lon),
        headers={**sources.HEADERS, "Authorization": f"Bearer {token}"},
        timeout=sources.TIMEOUT,
    )
    if r.status_code == 204:
        return []
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("forecast") or data.get("data") or []


def main():
    spots = json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now + dt.timedelta(hours=HOURS_AHEAD)

    all_diffs_total, all_diffs_swell = [], []
    exposed_diffs_total, exposed_diffs_swell = [], []
    EXPOSED = {"unstad", "russelv"}

    for spot in spots:
        if not spot.get("enabled"):
            continue
        name, sid = spot["name"], spot["id"]
        p = spot["barentswatch_point"]
        print(f"\n===== {name} =====")
        print(f"Forespurt punkt: lat={p['lat']}, lon={p['lon']}")

        rows = raw_barentswatch(p["lat"], p["lon"])
        if not rows:
            print("  Ingen BarentsWatch-data (se over).")
            continue

        seen_point = False
        om = openmeteo_with_total_dir(spot["offshore"]["lat"], spot["offshore"]["lon"])

        print(f"{'Tid':<18} {'BW hs':>6} {'BW max':>7} {'BW dir':>7} {'BW per':>7}  {'OM wave_h':>9} {'OM wave_dir':>11} {'OM swell_h':>10} {'OM swell_dir':>12}  {'diff/total':>10} {'diff/swell':>10}")
        for row in rows:
            t = row.get("forecastTime") or row.get("time") or row.get("validTime")
            if not t:
                continue
            tdt = sources.parse_iso(t)
            if tdt < now or tdt > cutoff:
                continue
            if not seen_point:
                print(f"BarentsWatch valgte punkt: lat={row.get('latitude')}, lon={row.get('longitude')}")
                seen_point = True

            bw_hs = row.get("totalSignificantWaveHeight")
            bw_max = row.get("expectedMaximumWaveHeight")
            bw_dir = row.get("totalMeanWaveDirection")
            bw_per = row.get("totalPeakPeriod")

            k = sources.hour_key(tdt)
            omk = om.get(k, {})
            wave_h, wave_dir = omk.get("wave_height"), omk.get("wave_dir")
            swell_h, swell_dir = omk.get("swell_height"), omk.get("swell_dir")

            d_total = angle_diff(bw_dir, wave_dir) if bw_dir is not None and wave_dir is not None else None
            d_swell = angle_diff(bw_dir, swell_dir) if bw_dir is not None and swell_dir is not None else None
            dominates = swell_h is not None and wave_h and swell_h >= 0.7 * wave_h

            # Konklusjonen (summarize() nedenfor) bruker bare timer der
            # svellet dominerer, som spesifisert - selve tabellen viser alt,
            # med "*" på de timene som telles med.
            if d_total is not None and dominates:
                all_diffs_total.append(d_total)
                if sid in EXPOSED:
                    exposed_diffs_total.append(d_total)
            if d_swell is not None and dominates:
                all_diffs_swell.append(d_swell)
                if sid in EXPOSED:
                    exposed_diffs_swell.append(d_swell)

            line = (f"{k:<18} {bw_hs!s:>6} {bw_max!s:>7} {bw_dir!s:>7} {bw_per!s:>7}  "
                    f"{wave_h!s:>9} {wave_dir!s:>11} {swell_h!s:>10} {swell_dir!s:>12}  "
                    f"{d_total if d_total is not None else '-':>10} {d_swell if d_swell is not None else '-':>10}{' *' if dominates else ''}")
            print(line)

        if not seen_point:
            print("  Ingen timer innenfor de neste 24 timene i BarentsWatch-svaret.")

    def summarize(label, vals):
        if not vals:
            print(f"{label}: ingen data")
            return
        vals = sorted(vals)
        mid = vals[len(vals) // 2]
        print(f"{label}: median {mid:.0f} grader, {len(vals)} timer, min {vals[0]:.0f}, maks {vals[-1]:.0f}")

    print("\n===== OPPSUMMERING =====")
    print("(* i tabellene over = svellet dominerer, minst 70 % av total høyde ute)")
    summarize("Alle spots, diff mot Open-Meteo total (wave_direction)", all_diffs_total)
    summarize("Alle spots, diff mot Open-Meteo svell (swell_wave_direction)", all_diffs_swell)
    summarize("Unstad+Russelv (mest åpne), diff mot total", exposed_diffs_total)
    summarize("Unstad+Russelv (mest åpne), diff mot svell", exposed_diffs_swell)
    print("\nTolkning: forskjell under ca 40 grader -> BarentsWatch bruker 'fra'.")
    print("Forskjell rundt 180 grader -> BarentsWatch bruker 'mot' (da må 180 legges til/trekkes fra ved bruk).")
    print("Noe midt imellom -> usikkert, vis frem tallene.")


if __name__ == "__main__":
    main()
