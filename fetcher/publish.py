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
from zoneinfo import ZoneInfo

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
    "surf_height_sets", "bw_height", "wind_speed", "wind_type", "dir_offshore",
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

HOME_DAYS = 9   # (oversikt-1) glidebryteren dekket 7 døgn; to døgns margin

# ---------- oversikt-2 (Tillegg 2, Theodor 15.10.2026): forsiden laster ikke timer ----------
# Per spot: «naa» (nå-timen) og «dager» (dagssammendrag for SUMMARY_DAYS døgn). Utvalg og
# maksverdier, ingen ny fysikk. Feltene i nå-timen/den beste timen er de appen trenger for
# ordet (ratingWord: stars/low_reason/zero_losses/faded_*/sources_disagree), høyden, vinden,
# svellet ute og lyset. bw_height bare der regel (c) krever det (Blåst ut/Stormsjø).
NAA_FIELDS = ("t", "stars", "faded", "light", "daylight", "surf_height", "surf_height_sets", "low_reason",
              "zero_losses", "faded_wind", "faded_tide", "sources_disagree", "period", "energy_swell_kj",
              "wind_speed", "wind_type", "wind_dir", "swell_offshore", "dir_offshore", "gust", "zone")
BW_WHEN = ("blown_out", "stormsjo")   # regel (c), app.js heightMForDisplay
SUMMARY_DAYS = 7
NAA_HOURS = 4   # nå-timen + de tre neste (henteren kjører hver 3. time - klokkas time finnes alltid)
# spotfeltene forsiden/Utforsk/søket trenger - resten av meta ligger i detaljfila (spotsiden)
META_FIELDS = ("id", "name", "area", "region", "aliases", "spot", "status", "facing", "enabled")
OSLO = ZoneInfo("Europe/Oslo")
REGION_MARGIN_DEG = (0.15, 0.4)   # (lat, lon) rundt rammen av spotene i regionen


ROUND = {"surf_height": 2, "surf_height_sets": 2, "period": 1, "wind_speed": 1, "wind_dir": 0, "swell_offshore": 2,
         "dir_offshore": 0, "gust": 1, "energy_swell_kj": 0, "bw_height": 2}


def _naa_hour(h):
    """Timen slik forsiden trenger den: bare felt som finnes, avrundet (ikke ny fysikk - samme tall
    som detaljfila viser med nf1/nf0), None og «false»-standarder utelatt for plassen (100+ spots)."""
    out = {}
    for k in NAA_FIELDS:
        if k not in h or h[k] is None:
            continue
        v = h[k]
        if k in ROUND and isinstance(v, (int, float)) and not isinstance(v, bool):
            v = round(v, ROUND[k]) if ROUND[k] else int(round(v))
        if k == "daylight" and h.get("light") is not None:
            continue
        if k in ("sources_disagree", "faded_wind", "faded_tide") and not v:
            continue
        out[k] = v
    if h.get("low_reason") in BW_WHEN and h.get("bw_height") is not None:
        out["bw_height"] = round(h["bw_height"], 2)
    return out


def _light(h):
    l = h.get("light")
    if l is None:
        return "mørkt" if h.get("daylight") is False else ("dag" if h.get("daylight") is True else None)
    return l


def known(h):
    """Samme regel som appen (ui.js known()): 0 stjerner uten grunn og uten surfehøyde = tallet mangler."""
    return bool(h) and not (not (h.get("stars") or 0) and not h.get("low_reason") and h.get("surf_height") is None)


def best_hour(hours):
    """Den beste timen blant de gitte (én dag): flest stjerner, ved likhet høyest surf_height, bare
    timer der lyset ikke er «mørkt» (ukjent lys teller ikke) og tallet finnes. Samme regel som
    appen bruker (dayBest/bestOfDay i ui.js/spotgraf.js) - flyttet hit og testet her (Tillegg 2).
    Returnerer (time, status): status «ok», «miss» (en lys time mangler tall) eller «dark»."""
    best, miss, light = None, False, False
    for h in hours:
        l = _light(h)
        if l is None:
            if not known(h) or (h.get("stars") or 0) >= 1:
                miss = True
            continue
        if l == "mørkt":
            continue
        light = True
        if not known(h):
            miss = True
            continue
        st = h.get("stars") or 0
        if best is None or st > (best.get("stars") or 0) or (st == (best.get("stars") or 0) and (h.get("surf_height") or 0) > (best.get("surf_height") or 0)):
            best = h
    if best is not None and (best.get("stars") or 0) >= 1:
        return best, "ok"
    if miss:
        return None, "miss"
    if not light:
        return None, "dark"
    return best, "ok"


def day_summary(hours):
    """Dagssammendrag for én dag: beste time (best_hour) med feltene appen trenger, slutt på vinduet
    (sammenhengende lyse timer samme dag med samme stjerner), laveste surf_height blant lyse timer
    over 0 og høyeste surf_height_sets i lyse timer. Mangler tall: «miss», mørkt hele dagen: «dark»."""
    b, status = best_hour(hours)
    out = {"status": status}
    if b is None:
        return out
    out["h"] = _naa_hour(b)
    st = b.get("stars") or 0
    idx = next(i for i, h in enumerate(hours) if h is b)
    end = idx
    while end + 1 < len(hours) and _light(hours[end + 1]) not in (None, "mørkt") and (hours[end + 1].get("stars") or 0) == st and known(hours[end + 1]):
        end += 1
    out["slutt"] = hours[end]["t"]
    lys = [h for h in hours if _light(h) not in (None, "mørkt") and known(h)]
    over0 = [h["surf_height"] for h in lys if h.get("surf_height") is not None and h["surf_height"] > 0]
    sets = [h.get("surf_height_sets") if h.get("surf_height_sets") is not None else h.get("surf_height") for h in lys]
    sets = [x for x in sets if x is not None]
    if over0 and sets and max(sets) > 0:
        out["lo"], out["hi"] = round(min(over0), 2), round(max(sets), 2)
    return out


def summarise(hours, now, days=SUMMARY_DAYS):
    """{«naa»: nå-timen, «dager»: [sammendrag per døgn fra i dag]} for ett spot."""
    naa = []
    for h in hours:
        if _t(h) + timedelta(hours=1) > now:
            naa.append(h)
        if len(naa) >= NAA_HOURS:
            break
    if not naa and hours:
        naa = [hours[-1]]
    today = now.astimezone(OSLO).date()
    by_day = {}
    for h in hours:
        d = _t(h).astimezone(OSLO).date()
        if d < today:
            continue
        by_day.setdefault(d, []).append(h)
    dager = []
    for k in range(days):
        d = today + timedelta(days=k)
        hs = [h for h in by_day.get(d, []) if _t(h) + timedelta(hours=1) > now]
        summ = day_summary(hs) if hs else {"status": "miss"}
        summ["d"] = d.isoformat()
        dager.append(summ)
    return {"naa": [_naa_hour(h) for h in naa], "dager": dager}


def regions_for(spots, regions_cfg):
    """Regionliste med rekkefølge (spots.json) og kartutsnitt: rammen rundt spotene pluss margin."""
    cfg = {r["name"]: r for r in (regions_cfg or [])}
    names = []
    for s in spots:
        r = s.get("region") or s.get("area")
        if r and r not in names:
            names.append(r)
    names.sort(key=lambda n: (cfg.get(n, {}).get("order", 999), n))
    out = []
    for n in names:
        pts = [(s["spot"]["lat"], s["spot"]["lon"]) for s in spots if (s.get("region") or s.get("area")) == n and s.get("spot")]
        reg = {"name": n, "n": len(pts)}
        if pts:
            la, lo = [p[0] for p in pts], [p[1] for p in pts]
            reg["extent"] = [round(min(la) - REGION_MARGIN_DEG[0], 3), round(min(lo) - REGION_MARGIN_DEG[1], 3),
                             round(max(la) + REGION_MARGIN_DEG[0], 3), round(max(lo) + REGION_MARGIN_DEG[1], 3)]
        out.append(reg)
    return out


def load_spots_cfg(path=None):
    """(regioner med rekkefølge, {id: spot}) fra spots.json - region/aliases legges på spots i
    varselet som mangler dem (eldre varsel, testfila). Tom hvis fila mangler."""
    p = Path(path) if path else ROOT / "spots.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], {}
    return d.get("regions", []), {s["id"]: s for s in d.get("spots", [])}



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


def split(forecast, exclude=DETAIL_EXCLUDE, now=None, regions_cfg=None, days=SUMMARY_DAYS):
    """(oversikt, {spot_id: detalj}) fra et helt varsel. Endrer ikke varselet.
    oversikt-2: per spot bare meta (META_FIELDS), nå-timen og dagssammendrag - ingen timer.
    Detaljfila har spotens hele meta og alle timene (unntatt DETAIL_EXCLUDE)."""
    forecast = public_forecast(forecast)
    spots = forecast.get("spots", [])
    run = run_id(forecast)
    if now is None:
        now = datetime.fromisoformat(forecast["generated"].replace("Z", "+00:00")) if forecast.get("generated") else datetime.now(ZoneInfo("UTC"))
    cfg_spots = {}
    if regions_cfg is None:
        regions_cfg, cfg_spots = load_spots_cfg()
    top = {k: v for k, v in forecast.items() if k != "spots"}
    overview = dict(top, format="oversikt-2", run=run, summary_days=days, regions=[], spots=[])
    details = {}
    for s in spots:
        hours = s.get("hours", [])
        meta_all = {k: v for k, v in s.items() if k != "hours"}
        cfg = cfg_spots.get(s["id"], {})
        for k in ("region", "aliases"):
            if k not in meta_all and cfg.get(k) is not None:
                meta_all[k] = cfg[k]
        meta = {k: v for k, v in meta_all.items() if k in META_FIELDS}
        if "region" not in meta and s.get("area"):
            meta["region"] = s["area"]
        overview["spots"].append(dict(meta, **summarise(hours, now, days)))
        details[s["id"]] = dict(meta_all, format="spot-2", generated=forecast.get("generated"), run=run,
                                hours=[{k: v for k, v in h.items() if k not in exclude} for h in hours])
    overview["regions"] = regions_for(overview["spots"], regions_cfg)
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
