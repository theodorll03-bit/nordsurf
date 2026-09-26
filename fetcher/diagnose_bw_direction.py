"""Engangsdiagnose: er BarentsWatch sin totalMeanWaveDirection "fra" eller "mot"?

Kjøres bare manuelt via workflow_dispatch (se .github/workflows/diagnose_bw.yml).
Skriver ALDRI ut nøkler, token eller Authorization-headeren.

27.09.2026: utvidet til å teste en ny hypotese - at retningskonvensjonen kan
variere med DATAKILDE i BarentsWatch (de kombinerer en finmasket kystmodell
med grovere modeller, og punktet kan få ulik kilde mellom kjøringer). Henter
nå RÅ data (uten sources.py sin tolkning) for BEGGE punktene per spot
(barentswatch_point og barentswatch_point_near), 48 timer frem, og beholder
source/fileSource per tidsverdi. Bygger en tabell per spot og per
source/fileSource: antall tidsverdier, og hvor mange som har over 150 grader
avvik fra spotens facing (samme grense som rating.SPOT_DIRECTION_ERROR_DEG).

Sammenligner også rå verdi mot det som faktisk står i det commitede
docs/data/forecast.json for samme tidspunkt (barentswatch_point) - avviker
de, er det en feil i vår egen henting/parsing, ikke i BarentsWatch sin data.

Beholder også den opprinnelige Open-Meteo-sammenligningen (GFS Wave - eneste
modellen med swell_wave_direction, ECMWF WAM gir ingen svelldekomponering,
bekreftet tidligere i prosjektet), for barentswatch_point.
"""
import os
import json
import datetime as dt
from pathlib import Path

import requests
import sources

ROOT = Path(__file__).resolve().parent.parent
HOURS_AHEAD = 48
SPOT_DIRECTION_ERROR_DEG = 150  # samme grense som rating.py


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
        "forecast_days": 3,
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
    """Som sources.barentswatch_point(), men beholder ALLE rå felt (source,
    fileSource, punktet BarentsWatch faktisk valgte) i stedet for å tolke dem."""
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

    forecast_path = ROOT / "docs" / "data" / "forecast.json"
    forecast = json.loads(forecast_path.read_text(encoding="utf-8")) if forecast_path.exists() else None
    forecast_by_spot = {s["id"]: {h["t"]: h for h in s["hours"]} for s in forecast["spots"]} if forecast else {}

    all_diffs_total, all_diffs_swell = [], []
    exposed_diffs_total, exposed_diffs_swell = [], []
    EXPOSED = {"unstad", "russelv"}

    # source_table[(spot_name, point_label, source, fileSource)] = {"n": int, "over150": int}
    source_table = {}
    mismatches = []  # (spot, t, raw_dir, stored_dir)

    for spot in spots:
        if not spot.get("enabled"):
            continue
        name, sid = spot["name"], spot["id"]
        facing = spot.get("facing")
        print(f"\n===== {name} (facing {facing}) =====")

        om = None
        for point_label, point_key in (("250m (barentswatch_point)", "barentswatch_point"),
                                        ("150m (barentswatch_point_near)", "barentswatch_point_near")):
            p = spot.get(point_key)
            if not p:
                continue
            print(f"\n  -- {point_label}, forespurt lat={p['lat']}, lon={p['lon']} --")
            rows = raw_barentswatch(p["lat"], p["lon"])
            if not rows:
                print("     Ingen BarentsWatch-data.")
                continue

            seen_point = False
            for row in rows:
                t = row.get("forecastTime") or row.get("time") or row.get("validTime")
                if not t:
                    continue
                tdt = sources.parse_iso(t)
                if tdt < now or tdt > cutoff:
                    continue
                if not seen_point:
                    print(f"     BarentsWatch valgte punkt: lat={row.get('latitude')}, lon={row.get('longitude')}")
                    seen_point = True

                bw_dir = row.get("totalMeanWaveDirection")
                bw_hs = row.get("totalSignificantWaveHeight")
                src = row.get("source")
                file_src = row.get("fileSource")
                k = sources.hour_key(tdt)

                if bw_dir is not None and facing is not None:
                    key = (name, point_label, src, file_src)
                    entry = source_table.setdefault(key, {"n": 0, "over150": 0})
                    entry["n"] += 1
                    if angle_diff(bw_dir, facing) > SPOT_DIRECTION_ERROR_DEG:
                        entry["over150"] += 1

                if point_key == "barentswatch_point":
                    stored = forecast_by_spot.get(sid, {}).get(k)
                    if stored is not None and stored.get("bw_dir") is not None and bw_dir is not None:
                        if abs(angle_diff(stored["bw_dir"], bw_dir)) > 0.5:
                            mismatches.append((name, k, bw_dir, stored["bw_dir"]))

                    if om is None:
                        om = openmeteo_with_total_dir(spot["offshore"]["lat"], spot["offshore"]["lon"])
                    omk = om.get(k, {})
                    wave_h, wave_dir = omk.get("wave_height"), omk.get("wave_dir")
                    swell_h, swell_dir = omk.get("swell_height"), omk.get("swell_dir")
                    d_total = angle_diff(bw_dir, wave_dir) if bw_dir is not None and wave_dir is not None else None
                    d_swell = angle_diff(bw_dir, swell_dir) if bw_dir is not None and swell_dir is not None else None
                    dominates = swell_h is not None and wave_h and swell_h >= 0.7 * wave_h
                    if d_total is not None and dominates:
                        all_diffs_total.append(d_total)
                        if sid in EXPOSED:
                            exposed_diffs_total.append(d_total)
                    if d_swell is not None and dominates:
                        all_diffs_swell.append(d_swell)
                        if sid in EXPOSED:
                            exposed_diffs_swell.append(d_swell)

                diff_facing = angle_diff(bw_dir, facing) if bw_dir is not None and facing is not None else None
                flag = " !!! >150" if diff_facing is not None and diff_facing > SPOT_DIRECTION_ERROR_DEG else ""
                print(f"     {k:<18} dir={bw_dir!s:>7} hs={bw_hs!s:>6} source={src!s:<20} fileSource={file_src!s:<30} "
                      f"diff/facing={diff_facing if diff_facing is not None else '-':>6}{flag}")

            if not seen_point:
                print("     Ingen timer innenfor vinduet i BarentsWatch-svaret.")

    def summarize(label, vals):
        if not vals:
            print(f"{label}: ingen data")
            return
        vals = sorted(vals)
        mid = vals[len(vals) // 2]
        print(f"{label}: median {mid:.0f} grader, {len(vals)} timer, min {vals[0]:.0f}, maks {vals[-1]:.0f}")

    print("\n===== OPPSUMMERING: Open-Meteo-sammenligning (barentswatch_point) =====")
    print("(bare timer der svellet dominerer, minst 70 % av total høyde ute)")
    summarize("Alle spots, diff mot Open-Meteo total (wave_direction)", all_diffs_total)
    summarize("Alle spots, diff mot Open-Meteo svell (swell_wave_direction)", all_diffs_swell)
    summarize("Unstad+Russelv (mest åpne), diff mot total", exposed_diffs_total)
    summarize("Unstad+Russelv (mest åpne), diff mot svell", exposed_diffs_swell)

    print("\n===== OPPSUMMERING: per spot / punkt / kilde =====")
    print(f"{'Spot':<16} {'Punkt':<32} {'source':<20} {'fileSource':<30} {'N':>4} {'>150 grader':>12}")
    for (spot_name, point_label, src, file_src), v in sorted(source_table.items()):
        print(f"{spot_name:<16} {point_label:<32} {src!s:<20} {file_src!s:<30} {v['n']:>4} {v['over150']:>12}")

    print("\n===== OPPSUMMERING: rå API-verdi vs det som står i docs/data/forecast.json =====")
    if not forecast:
        print("Fant ikke docs/data/forecast.json i denne kjøringen (uventet - sjekket ut sammen med koden).")
    elif not mismatches:
        print("Ingen avvik funnet (for tidspunktene som overlapper) - egen henting/parsing stemmer med det som er commitet.")
    else:
        for spot_name, k, raw_dir, stored_dir in mismatches:
            print(f"  AVVIK: {spot_name} {k}: rå API={raw_dir}, forecast.json={stored_dir}")

    print("\nTolkning: forskjell under ca 40 grader -> BarentsWatch bruker 'fra'.")
    print("Forskjell rundt 180 grader -> BarentsWatch bruker 'mot' (da må 180 legges til/trekkes fra ved bruk).")
    print("Noe midt imellom -> usikkert, vis frem tallene.")


if __name__ == "__main__":
    main()
