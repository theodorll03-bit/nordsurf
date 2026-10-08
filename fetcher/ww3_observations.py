"""NB, sjette fysikk-kontrollrunde (07.10.2026) - TRE KJENTE FEIL i dette
skriptet, IKKE rettet (konklusjonen i STATUS.md endret seg ikke uansett -
se der FØR du bruker output herfra til noe): (1) linje ~195 sender
`data["ptp1"]` (WW3 sin TOPPERIODE) rett inn i `swell_period`-parameteren,
som CLAUDE.md sin konvensjon forutsetter er MIDDELPERIODEN - WW3 har egne
middelperiode-felt (`pt01c1`/`pt02c1`) som IKKE er brukt her, og
"WW3-surfehøyde"-tallene i data/ww3/observations.md er derfor kunstig høye.
(2) docstring-avsnittet under om transfer er feil, se punkt (3) i STATUS.md
sin "Tre konkrete feil"-liste. (3) "App faktisk"-kolonnen i output
mis-siterer BarentsWatch sin høyde som "met.no/Open-Meteo" for Unstad 26.09
(se STATUS.md). Engangs-analyseverktøy, ikke en del av produksjonspipelinen,
ingen tester - rettes bare hvis dette faktisk tas i bruk igjen.

Theodors oppfølging 07.10.2026 (del 2 av 2, etter ratio+glidning-saken i
STATUS.md): er WW3 svaret på at Unstad har vært undervurdert (observert
surfehøyde 1,4-2,2 ganger det appen beregnet)? Henter WW3 sitt ARKIV (ikke
"latest files", som bare dekker ca. 11 døgn tilbake - se
fetcher/ww3_explore.py) for de faktiske observasjonstidspunktene, kjører
WW3 sin svellpartisjon gjennom DEN VIRKELIGE rate()-kjeden (transfer,
exposure, diffraksjonsdemping - samme kode som produksjon), MEN med
surf_factor satt til SURF_FACTOR_DEFAULT (1,0) i stedet for spotens lærte/
prior-verdi - Theodors eksplisitte "uten surf_factor_prior". Sammenlignes
mot det som ble observert og det appen faktisk beregnet den gangen (hentet
fra CLAUDE.md/STATUS.md sine allerede dokumenterte tall, IKKE gjettet).

Arkivet (thredds.met.no sin ww3_4km_archive_files-katalog, bekreftet
07.10.2026 live) går tilbake til minst 2016 og dekker september 2026 fullt -
samme filnavnmønster som "latest files" MEN med en "4km_"-infiks
(ww3_4km_YYYYMMDDTHHZ.nc, ikke ww3_YYYYMMDDTHHZ.nc) og organisert i
YYYY/MM/DD-mapper. Siden arkivdata FINNES for alle de etterspurte
tidspunktene, er punkt (e) i Theodors oppgave (sett opp løpende arkivering
hvis arkivdata IKKE finnes) ikke aktuelt.

Rutenettet er IDENTISK mellom latest_files og archive_files (bekreftet
live: samme (i,j)-indeks gir samme lat/lon i begge) - gjenbruker derfor
indeksene som allerede ble funnet i data/ww3/report.md (samme økt) i stedet
for å kjøre det kostbare søket (ww3_explore.find_point()) på nytt for hvert
tidspunkt:
    Unstad (564,298), Grøtfjord (622,294), Lenangsøyra (646,296)

Hver arkivfil dekker 73 timer (0-72t) fra sitt eget referansetidspunkt
(bekreftet via .dds/.das), i hele klokketimer. For hvert observasjonstidspunkt
brukes RUNEN med kortest mulig (ikke-negativ) ledetid - runden som nettopp
har startet FØR eller PÅ måltidspunktet (00/06/12/18Z) - det nærmeste WW3 kan
komme en "nowcast" uten en egen analyse-kjøring.

Pipelinen (spot_height() + breaking_height() + diffraksjonsdemping, alt fra
rating.py - IKKE reimplementert her) trenger spotens eksponeringskurve
(data/exposure_baseline.json, ren geometri - del B sin BarentsWatch-lærte
forbedring er IKKE brukt her, se STATUS.md for hvorfor) og en transfer-verdi
(dagens kalibrerte, fra docs/data/forecast.json - **NB, feil, se NB-blokken
øverst i fila: transfer er IKKE modell-uavhengig**, den er lært MOT
BarentsWatch med GFS/standardmodellen sin svellhøyde som den ene halvdelen
av hvert par - å sette inn WW3 sin svellhøyde uten å lære transfer på nytt
er ikke en ren "samme formel, annen kilde"-sammenligning. Svekker ikke
selve Hs-sammenligningen i STATUS.md, som skjer FØR transfer - antas her
likevel ikke å ha drevet nevneverdig på to uker). surf_factor settes til 1,0
(SURF_FACTOR_DEFAULT) for ALLE spots her, uavhengig av hva de normalt bruker -
det er selve "uten surf_factor_prior".

Kjør: python fetcher/ww3_observations.py
Skriver data/ww3/observations.md."""
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ww3_explore import parse_grid_block, VARS  # noqa: E402
import fetch  # noqa: E402
import rating  # noqa: E402

OUT_DIR = ROOT / "data" / "ww3"
ARCHIVE_ROOT = "https://thredds.met.no/thredds/dodsC/ww3_4km_archive_files"
REQUEST_PAUSE_S = 1.0

INDEX = {
    "unstad": (564, 298),
    "grotfjord": (622, 294),
    "lenangsoyra": (646, 296),
}

TZ_OSLO = dt.timezone(dt.timedelta(hours=2))  # CEST - sommertid gjelder hele perioden (24.09-07.10.2026)

# Dagens kalibrerte transfer (docs/data/forecast.json, 07.10.2026) - se
# moduldocstring for hvorfor dette (og ikke en historisk rekonstruksjon) er
# et rimelig valg.
TRANSFER = {"unstad": 0.57, "grotfjord": 0.6, "lenangsoyra": 0.6}


def run_url(run_dt):
    return (f"{ARCHIVE_ROOT}/{run_dt:%Y}/{run_dt:%m}/{run_dt:%d}/"
            f"ww3_4km_{run_dt:%Y%m%dT%HZ}.nc")


def nearest_run(target_utc):
    """Siste 6-timers kjøring (00/06/12/18Z) PÅ eller FØR target_utc - kortest
    mulig ledetid. Returnerer (run_datetime, lead_hours)."""
    run_hour = (target_utc.hour // 6) * 6
    run_dt = target_utc.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    lead = round((target_utc - run_dt).total_seconds() / 3600)
    return run_dt, lead


def fetch_hour(i, j, run_dt, lead_hours):
    import requests
    import time
    url = run_url(run_dt)
    expr = ",".join(f"{v}.{v}[{lead_hours}:1:{lead_hours}][{i}][{j}]" for v in VARS)
    r = requests.get(f"{url}.ascii?{expr}", timeout=60)
    r.raise_for_status()
    time.sleep(REQUEST_PAUSE_S)
    out = {}
    for v in VARS:
        rows = parse_grid_block(r.text, v)
        out[v] = rows[0][0] if rows and rows[0] and rows[0][0] == rows[0][0] else None
    return out


def rate_with_ww3(spot_id, swell_height, swell_dir, swell_period, exposure_data):
    """Kjører DEN VIRKELIGE rating.rate() med WW3 sin svellpartisjon i stedet
    for GFS, surf_factor tvunget til 1,0 (uten surf_factor_prior). Returnerer
    hele rate()-resultatet (surf_height, breaking_height, directness, stars,
    breakdown) - ikke en reimplementasjon av formelen."""
    spots = json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]
    spot = dict(next(s for s in spots if s["id"] == spot_id))
    smoothed, raw, warning = fetch.resolve_exposure(spot, exposure_data, spot["name"])
    if warning:
        print(f"  ADVARSEL eksponering for {spot_id}: {warning}")
    if smoothed is not None:
        spot["exposure_smoothed"] = smoothed
        spot["exposure_raw"] = raw
    spot["transfer"] = TRANSFER[spot_id]
    spot["surf_factor"] = rating.SURF_FACTOR_DEFAULT  # = 1,0, Theodors "uten surf_factor_prior"
    hour = {
        "swell_offshore": swell_height, "dir_offshore": swell_dir, "period": swell_period,
        "height_offshore": swell_height,  # bare til energy_total - ikke brukt i selve høyden
        "bw_height": None, "height_spot_model": None, "swell_model": "gfs",
        "wind_speed": None, "wind_dir": None, "gust": None, "tide": None, "turn": None,
    }
    return rating.rate(hour, spot)


# ---------- Observasjonene (Theodors liste, 07.10.2026) ----------
# local_dt: valgt representativt tidspunkt. For tidspunkt uten en eksakt
# dokumentert klokketid (27.09 ettermiddag, Grøtfjord/Lenangsøyra sine
# heldags-"flatt"-observasjoner) er valget markert eksplisitt i merknaden -
# se data/ww3/observations.md sin egen kommentar per rad, ikke gjettet stille.
# app_* er det appen FAKTISK viste/beregnet den gangen, hentet direkte fra
# allerede dokumenterte tall i CLAUDE.md/STATUS.md (IKKE rekonstruert her).
OBS = [
    dict(spot="unstad", local_dt=dt.datetime(2026, 9, 26, 14, 45, tzinfo=TZ_OSLO),
         observed="over hodet, nær dobbelt over hodet, tønner, offshore - 4 stjerner",
         observed_m="2,4-3,6 (SIZE_M: Over hodet - Dobbelt over hodet)",
         app_swell="Hs 0,9 m, 15 s (met.no/Open-Meteo)", app_surf_height="ca. 2,4 m (MED surf_factor_prior)",
         note="CLAUDE.md fast observasjon"),
    dict(spot="unstad", local_dt=dt.datetime(2026, 9, 27, 7, 0, tzinfo=TZ_OSLO),
         observed="brysthøyt til hodehøyt, rene linjer, ca. 3 stjerner (morgen)",
         observed_m="1,3-1,8 (SIZE_M: Brysthøy - Hodehøy)",
         app_swell="251°/12,6 s (kl. 08, nærmeste i kjeden)", app_surf_height="1,03 m (kl. 08, STATUS.md Oppgave 1 pkt 2)",
         note="representativ time i 06-10-kjeden - kl. 07 valgt, midt i vinduet"),
    dict(spot="unstad", local_dt=dt.datetime(2026, 9, 27, 17, 0, tzinfo=TZ_OSLO),
         observed="(ingen dokumentert observasjon)", observed_m=None,
         app_swell="(ikke rekonstruert)", app_surf_height="(ikke rekonstruert)",
         note="'27.09 ettermiddag' finnes BARE som et vindretningsdatapunkt (CLAUDE.md, kl. 14-20 lokal) - ingen egen surfehøyde-/stjerne-observasjon er dokumentert. Kl. 17 (midtpunkt) valgt for å vise WW3 likevel, uten en 'observert'-kolonne å sammenligne mot."),
    dict(spot="unstad", local_dt=dt.datetime(2026, 9, 28, 13, 0, tzinfo=TZ_OSLO),
         observed="lange rene linjer, offshore-sprøyt, 'firing' - 4 til 5 stjerner", observed_m=None,
         app_swell="3-5° utenfor vinduet, eksponering 62-66 %", app_surf_height="1,2 m, periode 12 s (STATUS.md pkt 11)",
         note="CLAUDE.md fast observasjon - ingen metertall oppgitt for selve observasjonen, bare kvalitativ 'firing'"),
    dict(spot="unstad", local_dt=dt.datetime(2026, 10, 5, 10, 45, tzinfo=TZ_OSLO),
         observed="over hodet, hule bølger, offshore-sprøyt - 4 til 5 stjerner",
         observed_m="2,4 (SIZE_M: Over hodet)",
         app_swell="BarentsWatch 0,6-0,9 m (kl. 09-12)", app_surf_height="1,0-1,1 m (STATUS.md pkt 13)",
         note="STATUS.md punkt 13 (05.10) - appens egen kjede der (kl. 09-12) brukt direkte"),
    dict(spot="grotfjord", local_dt=dt.datetime(2026, 9, 24, 12, 0, tzinfo=TZ_OSLO),
         observed="helt flatt", observed_m="0 (flat-sperre)",
         app_swell="met.no 1,9 m total, BarentsWatch 0,3 m, Windy 1,7 m fra ca. 267°", app_surf_height="0 m, 0 stjerner",
         note="CLAUDE.md fast observasjon (heldags - kl. 12 lokal valgt som representativ)"),
    dict(spot="grotfjord", local_dt=dt.datetime(2026, 9, 25, 12, 0, tzinfo=TZ_OSLO),
         observed="helt flatt, svell ute fra ca. 313 grader", observed_m="0 (flat-sperre)",
         app_swell="svell ute fra ca. 313° (3° utenfor [286,310]-vinduet)", app_surf_height="0 m, 0 stjerner",
         note="CLAUDE.md fast observasjon (heldags - kl. 12 lokal valgt som representativ)"),
    dict(spot="grotfjord", local_dt=dt.datetime(2026, 9, 26, 12, 0, tzinfo=TZ_OSLO),
         observed="helt flatt", observed_m="0 (flat-sperre)",
         app_swell="(ingen detaljer dokumentert)", app_surf_height="0 m, 0 stjerner",
         note="CLAUDE.md fast observasjon (heldags - kl. 12 lokal valgt som representativ)"),
    dict(spot="lenangsoyra", local_dt=dt.datetime(2026, 9, 26, 12, 0, tzinfo=TZ_OSLO),
         observed="ikke surfbart, mest vindsjø, bølgene i Ullsfjorden kom fra vest", observed_m="0 (flat-sperre, ikke målt)",
         app_swell="BarentsWatch-retning 70° fra facing (test_rating.py 7.1)", app_surf_height="0 m, 0 stjerner, sources_disagree",
         note="CLAUDE.md fast observasjon (ingen eksakt klokketid oppgitt - kl. 12 lokal valgt som representativ)"),
]


def main():
    exposure_data = json.loads((ROOT / "data" / "exposure_baseline.json").read_text(encoding="utf-8"))
    lines = ["# WW3 arkiv mot observasjonene (Theodors oppgave 07.10.2026, del 2 av 2)\n",
             "Svellpartisjon (phs1/pdir1/ptp1) kjørt gjennom DEN VIRKELIGE rate()-kjeden "
             "(transfer, eksponering, diffraksjonsdemping), surf_factor=1,0 (uten surf_factor_prior). "
             "Totalfeltet (hs/dir/tp) vises til sammenligning, IKKE kjørt gjennom pipelinen "
             "(blander vindsjø inn, se merknad i STATUS.md).\n"]
    lines.append("| Spot | Tidspunkt (lokal) | Kjøring (ledetid) | WW3 total hs/dir/tp | WW3 svell phs1/pdir1/ptp1 | "
                 "WW3 vindsjø phs0/pdir0/ptp0 | WW3-surfehøyde (svell, uten prior) | Retningstreff | Observert | App faktisk (svell/surfehøyde) | Merknad |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for o in OBS:
        i, j = INDEX[o["spot"]]
        target_utc = o["local_dt"].astimezone(dt.timezone.utc)
        run_dt, lead = nearest_run(target_utc)
        print(f"{o['spot']} {o['local_dt']} -> UTC {target_utc:%Y-%m-%dT%H:%MZ}, kjøring {run_dt:%Y-%m-%dT%HZ}, ledetid {lead}t")
        data = fetch_hour(i, j, run_dt, lead)
        result = rate_with_ww3(o["spot"], data["phs1"], data["pdir1"], data["ptp1"], exposure_data)
        # NB: result["stars"] er IKKE brukt her - wind_penalty(None,...) gir
        # automatisk 1 tapt stjerne for "ukjent vind" (rating.py:659), ikke 0.
        # En stjernekolonne uten ekte historisk vind ville derfor sett ut som
        # en vind-straff, ikke en ren svell-sammenligning - utelatt helt i
        # stedet for å vise et misvisende tall. Se STATUS.md.
        lines.append(
            f"| {o['spot']} | {o['local_dt']:%Y-%m-%d %H:%M} | {run_dt:%Y-%m-%dT%HZ} (+{lead}t) | "
            f"{data['hs']}/{data['dir']}/{data['tp']} | {data['phs1']}/{data['pdir1']}/{data['ptp1']} | "
            f"{data['phs0']}/{data['pdir0']}/{data['ptp0']} | "
            f"{result['surf_height']} m | {result['directness']} | "
            f"{o['observed']}" + (f" (~{o['observed_m']} m)" if o.get('observed_m') else "") + " | "
            f"{o['app_swell']} -> {o['app_surf_height']} | {o['note']} |")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "observations.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Skrev {OUT_DIR / 'observations.md'}")


if __name__ == "__main__":
    main()
