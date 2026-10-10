"""Henter rådata fra kildene. Alle tider i UTC, nøkkel = 'YYYY-MM-DDTHH:00Z'."""

import os
import time
import datetime as dt
import xml.etree.ElementTree as ET

import requests

CONTACT = os.environ.get("UA_CONTACT", "ukjent-kontakt")
HEADERS = {"User-Agent": f"nordsurf/0.1 ({CONTACT})"}
TIMEOUT = 45


def hour_key(ts: dt.datetime) -> str:
    ts = ts.astimezone(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    return ts.strftime("%Y-%m-%dT%H:00Z")


def parse_iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


RETRYABLE_STATUS = {429, 500, 502, 503, 504}


# S1 (ROADMAP oppgave S, 10.10.2026): Open-Meteo hang til 45 s-fristen på ca.
# halvparten av kallene fra GitHub sine runnere (måleworkflowen «Mål
# skalering» 09.10.2026: 90 av 94 s per spot var Open-Meteo-venting), uten
# feilkode - kallet hang bare. Derfor: (1) delt frist for Open-Meteo - 5 s
# på oppkobling, 20 s på svar - med samme fire forsøk som før; (2) ett
# samlekall for alle punkter per modell før spot-løkka (openmeteo_prefetch,
# Open-Meteo tar flere koordinater i samme kall og svarer med én post per
# punkt i samme rekkefølge, med location_id); (3) mellomlager per
# (kilde, lat, lon, modell) på 4 desimaler, så spots med samme punkt (eller
# samme offshore_longrange) henter én gang. Faller samlekallet, hentes
# punktene enkeltvis som før - tallene er identiske (samme modell, samme
# rutenettpunkt, bekreftet i «Mål Open-Meteo»), bare færre kall.
# «Mål Open-Meteo» 10.10.2026 kl. 08:31 UTC (24 enkeltkall): hengingen er på
# OPPKOBLINGEN (nøyaktig 5,1 s ved delt frist), ikke på svaret - 1 av 24
# sekvensielt, 4 av 24 med 4 tråder; når det svarer, svarer det på 0,2-0,5 s.
# Samlekall gir identiske timeverdier og samme rutenettpunkt som enkeltkall
# (bekreftet for alle 8 vindpunkt), men hang like ofte (6 av 6 forsøk for
# havpunktene den morgenen) - derfor er samlekallet bare en snarvei med
# enkeltkall som reserve, aldri eneste vei. Pausene mellom forsøk er korte
# for Open-Meteo (1/3/6 s - et heng er et heng, ikke en 429), så et kall som
# henger fire ganger koster ca. 30 s, ikke 214.
OPENMETEO_TIMEOUT = (5, 20)
OPENMETEO_BATCH_TIMEOUT = (5, 40)
OPENMETEO_PAUSES = (0, 1, 3, 6)             # samlekall: fire forsøk
OPENMETEO_SINGLE_PAUSES = (0, 1, 3, 6, 10, 10)   # enkeltkall: seks forsøk - det er reserven, og hvert forsøk koster bare 5 s ved heng
OPENMETEO_BATCH = 10            # punkter per samlekall
OPENMETEO_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
OPENMETEO_WIND_URL = "https://api.open-meteo.com/v1/forecast"
_OM_CACHE = {}


def openmeteo_clear_cache():
    _OM_CACHE.clear()


def _om_key(kind, lat, lon, model):
    return (kind, round(float(lat), 4), round(float(lon), 4), model)


def _get(url, params=None, headers=None, timeout=TIMEOUT, pauses=(0, 4, 10, 20)):
    # Kildene timer av og til ut forbigående, eller svarer midlertidig med
    # 429/5xx, når flere spots hentes tett etter hverandre (sett i
    # Actions-kjøringer, som deler IP-adresser med mange andre). Sett i live
    # kjøring 26.09.2026: Open-Meteo brukte over 45s å svare i tre forsøk på
    # rad for to spots samtidig - økt til fire forsøk med lengre pauser.
    # Gir opp med en gang på en varig feil (f.eks. 404), der nytt forsøk
    # aldri vil hjelpe.
    last_err = None
    for attempt, wait in enumerate(pauses):
        if wait:
            time.sleep(wait)
        try:
            r = requests.get(url, params=params, headers=headers or HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except (requests.Timeout, requests.ConnectionError) as e:
            # ConnectTimeout (henger på oppkoblingen) mot ReadTimeout (treg
            # server) - skilles i loggen, se S1-målingen over _get()
            print(f"  {url.split('/')[2]} forsøk {attempt + 1}: {type(e).__name__}")
            last_err = e
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code not in RETRYABLE_STATUS:
                raise
            last_err = e
    raise last_err


# ---------- met.no ----------

def metno_ocean(lat, lon):
    """Bølgehøyde, retning og vanntemp. {time: {...}}"""
    r = _get(
        "https://api.met.no/weatherapi/oceanforecast/2.0/complete",
        {"lat": round(lat, 4), "lon": round(lon, 4)},
    )
    out = {}
    for step in r.json()["properties"]["timeseries"]:
        d = step["data"]["instant"]["details"]
        out[hour_key(parse_iso(step["time"]))] = {
            "height": d.get("sea_surface_wave_height"),
            "dir": d.get("sea_surface_wave_from_direction"),
            "water_temp": d.get("sea_water_temperature"),
        }
    return out


def metno_weather(lat, lon):
    """Vind, kast og lufttemp. {time: {...}}"""
    r = _get(
        "https://api.met.no/weatherapi/locationforecast/2.0/complete",
        {"lat": round(lat, 4), "lon": round(lon, 4)},
    )
    out = {}
    for step in r.json()["properties"]["timeseries"]:
        d = step["data"]["instant"]["details"]
        out[hour_key(parse_iso(step["time"]))] = {
            "wind_speed": d.get("wind_speed"),
            "wind_dir": d.get("wind_from_direction"),
            "gust": d.get("wind_speed_of_gust"),
            "air_temp": d.get("air_temperature"),
        }
    return out


def metno_sun(lat, lon, date: dt.date):
    """Soloppgang og solnedgang. None i mørketid eller midnattssol."""
    r = _get(
        "https://api.met.no/weatherapi/sunrise/3.0/sun",
        {"lat": round(lat, 4), "lon": round(lon, 4), "date": date.isoformat(), "offset": "+00:00"},
    )
    p = r.json()["properties"]
    rise = (p.get("sunrise") or {}).get("time")
    set_ = (p.get("sunset") or {}).get("time")
    noon_elev = ((p.get("solarnoon") or {}).get("disc_centre_elevation"))
    return {"rise": rise, "set": set_, "noon_elevation": noon_elev}


# ---------- Open-Meteo (periode og offshore-svell) ----------

# GFS Wave sitt svellfelt er nærmest Windy i egen sjekk (25.09.2026, Ersfjordstranda
# kl. 14): retning 262° og høyde 0,88 m mot Windys 266°/0,8 m. ECMWF WAM ble også
# testet, men den modellen har ingen svelldekomponering i det hele tatt på
# Open-Meteo (bare total sjøtilstand) - derfor ikke brukt. Open-Meteo sin egen
# standardmodell ("best_match", her MeteoFrance Wave) traff dårligere (275°) og
# brukes bare som reserve når GFS mangler data for et punkt eller en time.
OPENMETEO_SWELL_MODEL = "ncep_gfswave025"


def _openmeteo_fetch(lat, lon, model=None):
    """Rådata fra Open-Meteo Marine, ev. med en bestemt modell valgt eksplisitt
    via `models`. {time: {height, swell_height, swell_dir, swell_period,
    swell_peak_period, total_dir, total_period, secondary_swell_height,
    secondary_swell_dir, secondary_swell_period}}

    06.10.2026, Theodors rettelse (manglende data ble tolket som 0, se
    CLAUDE.md og STATUS.md): total_dir/total_period (wave_direction/
    wave_period - den SAMLEDE sjøtilstanden, svell + vindsjø) ble FØR hentet
    fra API-et (sto allerede i "hourly"-parameteren over) men ALDRI lagret -
    trengs nå som reserve i openmeteo_marine() når ingen av kildene har et
    ekte, utskilt svellfelt for punktet (vanlig langt frem i tid, der GFS
    Wave sitt rutenett ikke dekker alle punkt for hver time).

    07.10.2026, Theodors oppgave (energien skal måles likt som surf-forecast,
    se CLAUDE.md "Lokalkunnskap"/Magnus): `swell_wave_peak_period`
    (topperiode, IKKE middelperioden `swell_wave_period` over - samme
    forskjell som Tp/Tm i oseanografien) - bare til energy_kj(), ALDRI til
    surfehøyde-formelen eller selve "Periode"-visningen (uendret, se
    rating.py). Bekreftet live 07.10.2026: standardmodellen (models=None) gir
    ekte verdier her for de punktene sjekket; GFS Wave (ncep_gfswave025) gir
    bokstavelig None for ALLE timer her (feltet finnes i svaret, men er
    alltid tomt for akkurat denne modellen) - treffer derfor i praksis bare
    unntaksvis (når standardmodellen er den valgte kilden for timen, se
    openmeteo_marine()), ikke "vanligvis"."""
    key = _om_key("marine", lat, lon, model)
    if key in _OM_CACHE:   # fra openmeteo_prefetch() eller et tidligere punkt med samme koordinater
        # samme dict-objekt til alle som spør - openmeteo_marine() og merge_wind()
        # lager nye dicts og endrer aldri dette på stedet (må forbli slik)
        return _OM_CACHE[key]
    r = _get(OPENMETEO_MARINE_URL, _marine_params([lat], [lon], model), timeout=OPENMETEO_TIMEOUT, pauses=OPENMETEO_SINGLE_PAUSES)
    out = _parse_marine_hourly(r.json()["hourly"])
    _OM_CACHE[key] = out
    return out


def _marine_params(lats, lons, model):
    params = {
        "latitude": ",".join(str(x) for x in lats),
        "longitude": ",".join(str(x) for x in lons),
        "hourly": "wave_height,wave_direction,wave_period,swell_wave_height,"
        "swell_wave_direction,swell_wave_period,swell_wave_peak_period,"
        "secondary_swell_wave_height,secondary_swell_wave_direction,"
        "secondary_swell_wave_period",
        "timezone": "GMT",
        # 06.10.2026, ROADMAP oppgave B: 16 dager. Live sjekket samme dag:
        # GFS Wave (ncep_gfswave025) gir svelldata alle 384 timer, mens
        # standardmodellen (models=None) bare har svelldata til ca. dag 9 -
        # dag 10-16 kommer derfor alltid fra GFS alene (openmeteo_marine() sin
        # time-for-time-sammenslåing håndterer det uten egen kode).
        "forecast_days": 16,
    }
    if model:
        params["models"] = model
    return params


def _parse_marine_hourly(h):
    n = len(h["time"])
    missing = [None] * n
    out = {}
    for i, t in enumerate(h["time"]):
        key = t + "Z" if len(t) == 16 else t
        key = key[:13] + ":00Z"
        out[key] = {
            "height": h["wave_height"][i],  # total: svell + vindsjø
            "swell_height": h["swell_wave_height"][i],
            "swell_dir": h["swell_wave_direction"][i],
            "swell_period": h["swell_wave_period"][i],
            "swell_peak_period": h.get("swell_wave_peak_period", missing)[i],
            "total_dir": h["wave_direction"][i],
            "total_period": h["wave_period"][i],
            "secondary_swell_height": h.get("secondary_swell_wave_height", missing)[i],
            "secondary_swell_dir": h.get("secondary_swell_wave_direction", missing)[i],
            "secondary_swell_period": h.get("secondary_swell_wave_period", missing)[i],
        }
    return out


def _has_real_swell(v):
    """True hvis kilden faktisk har svelldata for punktet. Enkelte modellpunkt
    (sett i smale fjordløp der GFS Wave sitt 0.25-graders rutenett ikke har
    gyldig sjødekning) svarer med bokstavelig 0.0/0 på alt i stedet for null -
    skilles fra en ekte flau/stille sjø ved at retningen da også er nøyaktig 0."""
    return v.get("swell_height") not in (None, 0) and v.get("swell_dir") is not None


RATIO_BLEND_HOURS = 12  # Theodors instruks 07.10.2026: glidende overgang, ikke et hopp


def ratio_blend_correction(primary, fill, blend_hours=RATIO_BLEND_HOURS, blend_from_series=None):
    """07.10.2026, Theodors rettelse (generalisert fra Lyngen-saken, se
    STATUS.md): når en serie (`fill` - f.eks. GFS langt frem, eller et
    sekundært havpunkt sin egen GFS-serie) skal FORTSETTE etter at en annen,
    mer pålitelig serie (`primary` - f.eks. standardmodellen ved samme
    punkt, eller hovedpunktet sin egen beste verdi) sin EGEN dekning tar
    slutt, kan de to ligge på systematisk ulik skala (sett for Lyngen: GFS
    fra det nye punktet ga ca. 25 % høyere totalhøyde enn standardmodellen
    ved hovedpunktet i samme periode). I stedet for et rått skifte midt i en
    tallrekke:

    1. Finn ALLE tidspunkt der BEGGE seriene har en ekte (ikke None/0)
       verdi - overlappet, uansett om det er sammenhengende eller spredt
       (GFS sin egen dekning har i praksis spredte, enkeltstående hull innen
       sin egen horisont - det er IKKE det samme som at dekningen "tar
       slutt", se punkt 3).
    2. `ratio` = median(fill / primary) over overlappet. `None` hvis færre
       enn to par (for lite grunnlag).
    3. "Skjøten" er SISTE tidspunkt (kronologisk) der `primary` har en ekte
       verdi - der `primary` sin egen dekning faktisk tar slutt for godt.
    4. Etter skjøten: `fill` sin verdi korrigeres til `primary` sin skala
       (delt på `ratio`), og GLIR LINEÆRT inn fra en startverdi over
       `blend_hours` timer - ingen brå hopp i tallet som vises.

    07.10.2026, fysikk-kontrollørens funn (andre runde): startverdien for
    glidningen skal være det som FAKTISK ble vist i skjøtetimen - IKKE
    nødvendigvis `primary[seam]`. Når `fill` også er ekte og VELGES i
    skjøtetimen (f.eks. GFS vinner over standardmodellen når begge er ekte,
    se openmeteo_marine()), er `primary[seam]` en skjult verdi ingen så -
    glidning fra den ga et kunstig dykk/hopp (verdien falt til
    `primary[seam]` et øyeblikk, før den gled videre mot målet). `fill`
    sin EGEN urørte verdi i skjøtetimen IGJEN (`fill[seam]`, siden `fill`
    aldri endres på/før skjøten, se punkt 4) er alltid identisk med det som
    faktisk vises der når `fill` er den valgte kilden - men når `primary`
    heller er den viste kilden i skjøtetimen, er ikke `fill[seam]` riktig
    heller. `blend_from_series` (valgfri, f.eks. den faktisk VISTE serien,
    uavhengig av hvilken av `primary`/`fill` som vant hver time) løser dette
    generelt - standardverdi (ingen gitt) er `primary[seam]`, som er riktig
    for Lyngen sin krysspunkt-bruk (der `primary` ALLTID er den viste verdien
    ved hovedpunktet, se fetch.py).

    Rører ALDRI `primary` sine egne verdier, og `fill` bare for tidspunkt
    ETTER skjøten. Returnerer (korrigert_fill_dict, ratio_eller_None,
    skjøt_tidspunkt_eller_None) - `fill` uendret (kopiert) hvis ingen skjøt/
    ratio kan regnes ut (f.eks. `primary` mangler helt, eller aldri
    overlapper med `fill`)."""
    overlap = [(t, fill[t] / primary[t]) for t in sorted(set(primary) & set(fill))
               if primary.get(t) not in (None, 0) and fill.get(t) not in (None, 0)]
    if len(overlap) < 2:
        return dict(fill), None, None
    ratios = sorted(r for _, r in overlap)
    n = len(ratios)
    ratio = ratios[n // 2] if n % 2 else (ratios[n // 2 - 1] + ratios[n // 2]) / 2
    primary_real_times = [t for t, v in primary.items() if v not in (None, 0)]
    if not primary_real_times:
        return dict(fill), None, None
    seam = max(primary_real_times)
    seam_dt = parse_iso(seam)
    blend_start = (blend_from_series or primary).get(seam, primary[seam])
    corrected = dict(fill)
    for t, v in fill.items():
        if v in (None, 0) or t <= seam:
            continue
        hours_after = (parse_iso(t) - seam_dt).total_seconds() / 3600
        target = v / ratio
        if hours_after < blend_hours:
            w = hours_after / blend_hours
            corrected[t] = blend_start * (1 - w) + target * w
        else:
            corrected[t] = target
    return corrected, ratio, seam


def openmeteo_marine(lat, lon, apply_ratio_correction=True):
    """Hovedsvellet (retning, høyde, periode), fra GFS Wave. Faller tilbake til
    Open-Meteo sin standardmodell for en time der GFS ikke har svelldata for
    punktet. Totalhøyden (inkl. vindsjø) og sekundærsvellet følger med, men
    sekundærsvellet lagres bare - det skal ikke vises eller brukes i ratingen.
    {time: {height, swell_height, dir, period, peak_period, swell_model,
    secondary_swell_height, secondary_swell_dir, secondary_swell_period}},
    peak_period er svellets TOPPERIODE (bare til energy_kj(), se
    rating.energy_period()) - ofte None (se _openmeteo_fetch() sin
    docstring: GFS Wave har aldri dette feltet, bare standardmodellen).
    PLUSS en spesialnøkkel "_meta" ({gfs_standard_ratio, ratio_seam} eller
    fraværende hvis ikke nok overlapp til å regne ut - se
    ratio_blend_correction()) - IKKE en time, må plukkes ut før resten av
    dicten brukes som et tidsoppslag (fetch.py gjør dette rett etter kallet).
    swell_model er "gfs", "standard", "total_fallback" (se under) eller None
    (ingen av kildene har NOE, verken svell eller totalhøyde, for punktet).

    07.10.2026, Theodors instruks (etter å ha sett fysikk-kontrollørens funn
    at premisset - standardmodellen vises først, GFS tar over etterpå - ikke
    stemmer for de fleste spots): korriger likevel, SAMME metode som Lyngen
    sin krysspunkt-bruk (fetch.py), for alle spots - "så alt følger én
    regel". "_meta" sitt forhold mellom GFS og standardmodellen vises i
    kilderapporten OG brukes til å skalere "swell_height" etter skjøten (se
    ratio_blend_correction()). Se STATUS.md.

    07.10.2026, fysikk-kontrollørens funn (tredje runde): Lyngen sin
    `offshore_longrange` er OGSÅ bare et havpunkt, kalt via DENNE funksjonen
    (fetch.py) - uten en sperre ville den få sin EGEN samme-punkt-korreksjon
    her (f.eks. forhold 0,88), FØR fetch.py sin krysspunkt-korreksjon deler
    på SITT forhold (f.eks. 0,915) en gang til - dobbel korreksjon, opptil
    +53 % i glidningsvinduet, samme type feil som ble funnet og rettet for
    Lyngen tidligere (se STATUS.md). `apply_ratio_correction=False`
    (fetch.py sender dette BARE for offshore_longrange-kallet) hopper over
    MUTASJONEN av "swell_height" (og selve "_meta"-beregningen, siden ingen
    bruker den der uansett - fetch.py kastet den allerede) - resten av
    funksjonen er identisk, punktet sin egen rå GFS/standard-seleksjon
    (modell-valg per time) er fortsatt uendret og korrekt.

    Henter GFS- og standardmodell-kallene hver for seg: timer det ene ut
    (sett i praksis - Open-Meteo kan svare tregt), skal ikke det andre
    kastes bort også. Bare hvis BEGGE feiler gir funksjonen tomt resultat.

    06.10.2026, Theodors rettelse (HASTER-funn: Unstad 14 dager frem viste
    "Flatt, svell 0,0 m fra 0 grader, periode 0 s" - manglende data var
    tolket som 0 hele veien ned, se CLAUDE.md sin nye grunnregel). Når INGEN
    av kildene har et ekte, utskilt svellfelt (_has_real_swell() falsk for
    begge - vanlig langt frem i tid, der GFS Wave sitt rutenett ikke dekker
    alle punkt for hver time), brukte den gamle koden likevel GFS sin EGNE,
    rå `swell_height/swell_dir/swell_period` som om de var gyldige - og de
    kan være bokstavelig 0/0/0 i akkurat denne situasjonen (samme årsak som
    _has_real_swell() selv ble laget for å oppdage), ikke bare `None`.
    `swell_model=None` var det ENESTE signalet om at noe var galt - et
    signal fetch.py ikke sjekket før den brukte tallene.

    Nå: bruker TOTALFELTENE (wave_height/wave_direction/wave_period - den
    samlede sjøtilstanden, svell + vindsjø) som en eksplisitt RESERVE i
    stedet, markert `swell_model="total_fallback"` - et tredje, ekte signal
    fetch.py bruker til å dempe svellandelen med et forsiktig anslag (se
    der) og merke timen usikker. Bare hvis TOTALHØYDEN også mangler for
    begge kilder er resultatet ekte `None` over hele linja, med
    `swell_model=None`."""
    try:
        primary = _openmeteo_fetch(lat, lon, model=OPENMETEO_SWELL_MODEL)
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
        print(f"  GFS Wave feilet for ({lat},{lon}), bruker bare standardmodellen: {e}")
        primary = {}
    try:
        fallback = _openmeteo_fetch(lat, lon, model=None)
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
        print(f"  Standardmodellen feilet for ({lat},{lon}), bruker bare GFS Wave: {e}")
        fallback = {}
    if not primary and not fallback:
        raise RuntimeError("Både GFS Wave og standardmodellen feilet")
    out = {}
    gfs_swell_series = {}       # bare timer med ekte GFS-svell, til ratio_blend_correction()
    standard_swell_series = {}  # bare timer med ekte standardmodell-svell
    for k in sorted(set(primary) | set(fallback)):
        p, f = primary.get(k, {}), fallback.get(k, {})
        if _has_real_swell(p):
            gfs_swell_series[k] = p["swell_height"]
        if _has_real_swell(f):
            standard_swell_series[k] = f["swell_height"]
        if _has_real_swell(p):
            src, model = p, "gfs"
        elif _has_real_swell(f):
            src, model = f, "standard"
        else:
            src, model = p, None
        height = p.get("height")
        if not height:  # None eller 0.0 - GFS har ikke gyldig dekning i punktet (se _has_real_swell)
            height = f.get("height")
        if model is None:
            # 06.10.2026, Theodors rettelse: INGEN ekte svellfelt - bruk
            # totalhøyden/-retningen/-perioden (samlet sjøtilstand) som
            # reserve i stedet for GFS sine egne, potensielt 0/0/0 "svell"-
            # felt (se modul-docstringen). total_dir/total_period kommer fra
            # samme kilde `height` allerede falt tilbake til over.
            total_dir = p.get("total_dir") if p.get("height") else None
            total_period = p.get("total_period") if p.get("height") else None
            if total_dir is None:
                total_dir, total_period = f.get("total_dir"), f.get("total_period")
            if height:  # har i det minste en totalhøyde å bruke som reserve
                out[k] = {
                    "height": height, "swell_height": height, "dir": total_dir, "period": total_period,
                    "peak_period": None,  # ingen topperiode for en TOTALHØYDE-reserve - se energy_period()
                    "swell_model": "total_fallback",
                    "secondary_swell_height": None, "secondary_swell_dir": None, "secondary_swell_period": None,
                }
            else:  # ingenting i det hele tatt for dette punktet/timen - ekte None, ikke 0
                out[k] = {
                    "height": None, "swell_height": None, "dir": None, "period": None, "peak_period": None,
                    "swell_model": None,
                    "secondary_swell_height": None, "secondary_swell_dir": None, "secondary_swell_period": None,
                }
            continue
        out[k] = {
            "height": height,
            "swell_height": src.get("swell_height"),
            "dir": src.get("swell_dir"),
            "period": src.get("swell_period"),
            # 07.10.2026, Theodors oppgave: topperiode, BARE til energy_kj()
            # (se rating.energy_period()) - ALDRI til surfehøyde-formelen
            # eller selve "Periode"-visningen (period, over, uendret).
            "peak_period": src.get("swell_peak_period"),
            "swell_model": model,
            "secondary_swell_height": src.get("secondary_swell_height"),
            "secondary_swell_dir": src.get("secondary_swell_dir"),
            "secondary_swell_period": src.get("secondary_swell_period"),
        }
    # 07.10.2026, Theodors instruks (bekreftet etter fysikk-kontrollørens
    # funn samme dag): korriger GFS sin svellhøyde etter at standardmodellen
    # sin EGEN dekning tar slutt for godt, til samme skala som standardmodellen
    # viste der de to overlappet (ratio_blend_correction()) - SAMME metode
    # som Lyngen sin krysspunkt-bruk (fetch.py), for ALLE spots, "så alt
    # følger én regel" (Theodors ord). Kontrollørens funn (at GFS i praksis
    # vises 86-99 % av tiden FØR skjøten også, så de faktiske hoppene
    # Theodor så trolig er spredte standardmodell-hull FØR skjøten, ikke noe
    # denne mekanismen dekker) endrer ikke selve valget - Theodor har sett
    # det og valgt likevel. Se STATUS.md.
    #
    # `blend_from_series` = den FAKTISK VISTE serien (ikke nødvendigvis
    # standardmodellens egen, skjulte verdi) i skjøtetimen - fysikk-
    # kontrollørens andre funn (glidningen startet fra feil verdi, ga et
    # kunstig dykk når GFS vant selv i skjøtetimen). Bygget fra `out` (det
    # som faktisk endte opp i resultatet) rett før denne korreksjonen, derfor
    # alltid den EGENTLIG viste verdien uansett hvilken modell som vant hver
    # time.
    # 07.10.2026, fysikk-kontrollørens funn (tredje runde): hopp over HELE
    # dette for offshore_longrange-punktet (fetch.py sender
    # apply_ratio_correction=False DIT) - uten dette ville punktet fått sin
    # EGEN samme-punkt-korreksjon her, FØR fetch.py sin krysspunkt-korreksjon
    # (samme mekanisme, mot hovedpunktet) deler på et ANNET forhold en gang
    # til - dobbel korreksjon (opptil +53 % i glidningsvinduet, målt live).
    if apply_ratio_correction:
        displayed_swell_series = {k: v["swell_height"] for k, v in out.items() if v.get("swell_model") is not None}
        corrected_gfs, ratio, seam = ratio_blend_correction(
            standard_swell_series, gfs_swell_series, blend_from_series=displayed_swell_series)
        if ratio is not None:
            for k, v in corrected_gfs.items():
                if k > seam and out.get(k, {}).get("swell_model") == "gfs":
                    out[k]["swell_height"] = round(v, 3)
            out["_meta"] = {"gfs_standard_ratio": round(ratio, 3), "ratio_seam": seam}
    return out


# ---------- Kartverket (tidevann) ----------

def kartverket_tide(lat, lon, start: dt.datetime, end: dt.datetime):
    """Flo og fjære. Liste med {time, type, cm}. Tom liste hvis noe feiler."""
    try:
        r = _get(
            "https://vannstand.kartverket.no/tideapi.php",
            {
                "lat": lat,
                "lon": lon,
                "fromtime": start.strftime("%Y-%m-%dT%H:%M"),
                "totime": end.strftime("%Y-%m-%dT%H:%M"),
                "datatype": "tab",
                "refcode": "cd",
                "lang": "nb",
                "tide_request": "locationdata",
            },
        )
        root = ET.fromstring(r.content)
        out = []
        for wl in root.iter("waterlevel"):
            out.append(
                {
                    "time": parse_iso(wl.get("time")).astimezone(dt.timezone.utc).isoformat(),
                    "type": "flo" if wl.get("flag") == "high" else "fjære",
                    "cm": round(float(wl.get("value"))),
                }
            )
        return out
    except Exception as e:  # tidevann er fint å ha, ikke kritisk
        print(f"  tidevann feilet: {e}")
        return []


# ---------- BarentsWatch ----------

_bw_token = None


def barentswatch_token():
    global _bw_token
    if _bw_token:
        return _bw_token
    cid = os.environ.get("BW_CLIENT_ID")
    secret = os.environ.get("BW_CLIENT_SECRET")
    if not cid or not secret:
        return None
    r = requests.post(
        "https://id.barentswatch.no/connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": secret,
            "scope": "api",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    _bw_token = r.json()["access_token"]
    return _bw_token


def barentswatch_point(lat, lon):
    """Bølgehøyde, retning, periode og maks bølgehøyde fra BarentsWatch for
    et punkt, i tretimersteg opp til ca 60 timer frem.
    {time: {"height","dir","period","max_height"}}

    Bruker /v1/waveforecastpoint/nearest/all (se Waveforecast OpenAPI doc,
    schema BwRasterWavePoint). BW_POINT_URL (se README) må ha ?x={lon}&y={lat}
    - x er lengdegrad, y er breddegrad. Uten BW_POINT_URL/token brukes
    reservemodellen.

    Maks bølgehøyde (feltet expectedMaximumWaveHeight, bekreftet mot
    BarentsWatch sin OpenAPI-spec 26.09.2026) er bare til VISNING - den skal
    ALDRI brukes i rangeringen eller kalibreringen, som begge bygger på
    signifikant høyde (samme mål brukes gjennomgående, ellers sammenligner
    man epler og pærer mellom spots og mellom BarentsWatch og Open-Meteo).

    Retning: totalMeanWaveDirection er retningen bølgene GÅR MOT (samme
    konvensjon som pilene på BarentsWatch sitt eget kart) - konverteres her
    til "fra", som resten av appen (met.no, Open-Meteo) bruker.

    Historikk (27.09.2026, andre runde - se CLAUDE.md sine faste
    observasjoner og STATUS.md for hele sporet): en mellomliggende runde
    (26.09.2026) konkluderte feilaktig at feltet allerede var "fra" og
    fjernet konverteringen, ut fra et tall (296 grader) som viste seg å
    komme fra en SENERE, allerede konvertert kilde, ikke fra selve API-et.
    Fasiten kom fra en lagret, garantert rå logg (fra en diagnose-kjøring
    26.09.2026 kl. 12:59 UTC, FØR noen konvertering i det hele tatt fantes i
    koden): Unstad, tidsverdien 2026-09-26T15:00Z (kl. 17:00 norsk tid),
    totalMeanWaveDirection = 116 grader, rått fra API-et. Konvertert
    (+180) gir 296 grader, som treffer Unstad sin `facing` (294,8 grader)
    nesten blink, og stemmer med video fra Lofoten Surfsenter samme time
    som viste bølger rett inn mot stranda. UKONVERTERT (116) er 179 grader
    fra facing - stikk motsatt av virkeligheten.

    Dette forklarer også et mønster oppdaget 27.09.2026: uten konvertering
    ble retningen ved spoter der svellet treffer nesten rett på (Unstad,
    Grøtfjord, Ersfjordstranda) snudd ca. 180 grader og fanget av
    sikkerhetsgrensen i rating.spot_direction_factor() (se der). Ved
    spoter der svellet treffer skrått (Russelv, Lenangsøyra, Steinkrøssa)
    ble feilen bare 90-150 grader - fortsatt feil retning, men under
    grensen som utløser sikringen, så den var vanskeligere å oppdage.

    IKKE konverter dette om igjen andre steder, "dir" i returverdien
    herfra er allerede "fra".
    """
    url = os.environ.get("BW_POINT_URL")
    token = barentswatch_token()
    if not url or not token:
        return {}
    r = requests.get(
        url.format(lat=lat, lon=lon),
        headers={**HEADERS, "Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    if os.environ.get("BW_DEBUG"):
        print(f"  DEBUG bw {lat},{lon}: status={r.status_code} body={r.text[:400]!r}")
    if r.status_code == 204:  # ingen data for dette punktet
        return {}
    r.raise_for_status()
    data = r.json()
    rows = data if isinstance(data, list) else data.get("forecast") or data.get("data") or []
    out = {}
    for row in rows:
        if "totalMeanWaveDirection" in row and row.get("totalMeanWaveDirection") is None:
            continue  # modellen har ingen data for denne timen (sett som h=0.0, dir=None, period~1.2s)
        t = row.get("forecastTime") or row.get("time") or row.get("validTime")
        h = next(
            (
                row[k]
                for k in ("totalSignificantWaveHeight", "significantWaveHeight", "waveHeight", "hs", "value")
                if row.get(k) is not None
            ),
            None,
        )  # 0.0 (flatt hav) er en gyldig verdi, ikke "mangler" - "or" ville feilaktig hoppet videre
        if t is None or h is None:
            continue
        d = row.get("totalMeanWaveDirection")
        d_from = (float(d) + 180) % 360 if d is not None else None  # mot -> fra, se docstring
        p = row.get("totalPeakPeriod")
        hmax = row.get("expectedMaximumWaveHeight")
        out[hour_key(parse_iso(t))] = {
            "height": float(h),
            "dir": d_from,
            "period": float(p) if p is not None else None,
            "max_height": float(hmax) if hmax is not None else None,
            # 27.09.2026: hvilken BarentsWatch-kilde/fil dette punktet faktisk
            # kom fra - permanent sjekk, se ROADMAP og STATUS.md ("test
            # source/fileSource-hypotesen med data"). Bare til rapportering,
            # brukes ALDRI til å velge eller endre selve verdiene.
            "source": row.get("source"),
            "file_source": row.get("fileSource"),
            # Rå (ukonvertert) retning, bare til plausibilitetssjekken i
            # fetch.py - "dir" over er det eneste som brukes i ratingen.
            "dir_raw": float(d) if d is not None else None,
        }
    return out


def _lerp(a, b, frac):
    if a is None or b is None:
        return None
    return a + (b - a) * frac


def _lerp_circular(a, b, frac):
    """Korteste vei rundt 0/360 grader, f.eks 350 -> 10 midt mellom gir 0, ikke 180."""
    if a is None or b is None:
        return None
    diff = ((b - a + 180) % 360) - 180
    return (a + diff * frac) % 360


def bw_interpolate(raw):
    """Fyller BarentsWatch sine tretimerspunkter (fra barentswatch_point) til
    én verdi per hele time. Høyde, periode og maks høyde: lineær interpolasjon.
    Retning: sirkulær. Interpolerer bare mellom punkter maks 3 timer fra
    hverandre - mangler et punkt midt i serien, står timene i hullet uten
    BarentsWatch. Ekstrapolerer aldri forbi første/siste punkt.
    {time: {height,dir,period,max_height,interpolated}}
    """
    if not raw:
        return {}
    times = sorted(raw)
    out = {t: {**raw[t], "interpolated": False} for t in times}
    for t0, t1 in zip(times, times[1:]):
        d0, d1 = parse_iso(t0), parse_iso(t1)
        gap = round((d1 - d0).total_seconds() / 3600)
        if not (0 < gap <= 3):
            continue  # hull i serien - ikke fyll, og ikke ekstrapoler
        v0, v1 = raw[t0], raw[t1]
        for step in range(1, gap):
            frac = step / gap
            tk = hour_key(d0 + dt.timedelta(hours=step))
            out[tk] = {
                "height": _lerp(v0.get("height"), v1.get("height"), frac),
                "dir": _lerp_circular(v0.get("dir"), v1.get("dir"), frac),
                "period": _lerp(v0.get("period"), v1.get("period"), frac),
                "max_height": _lerp(v0.get("max_height"), v1.get("max_height"), frac),
                "dir_raw": _lerp_circular(v0.get("dir_raw"), v1.get("dir_raw"), frac),
                "interpolated": True,
            }
    return out


def weather_interpolate(raw):
    """Fyller met.no Locationforecast (metno_weather) sine timer til én verdi
    per hele time. 27.09.2026: live sjekk viste at Locationforecast bare gir
    ekte TIMESoppløsning ca. 51 timer fram (2026-09-27T15:00Z til
    2026-09-29T18:00Z i den sjekken) - deretter hver 6. time, resten av
    horisonten (til ca. 10 døgn). Uten interpolasjon mangler fem av seks
    timer vind helt der, og fikk datafeil-straffen for ukjent vind (se
    rating.wind_penalty()), selv om vinden i praksis endrer seg jevnt mellom
    to kjente punkter. Vindstyrke, kast og lufttemperatur: lineær. Retning:
    sirkulær (samme prinsipp som bw_interpolate()). Interpolerer bare mellom
    punkter maks 6 timer fra hverandre (met.no sitt eget steg her - videre
    enn BarentsWatch sine 3 timer). Ekstrapolerer aldri forbi siste punkt.
    Sjekket: met.no Oceanforecast og Open-Meteo Marine har IKKE samme problem
    (begge jevn timesoppløsning hele sin egen horisont, sjekket live samme
    dag) - trenger derfor ingen tilsvarende interpolering.
    {time: {wind_speed,wind_dir,gust,air_temp,wind_interpolated}}
    """
    if not raw:
        return {}
    times = sorted(raw)
    out = {t: {**raw[t], "wind_interpolated": False} for t in times}
    for t0, t1 in zip(times, times[1:]):
        d0, d1 = parse_iso(t0), parse_iso(t1)
        gap = round((d1 - d0).total_seconds() / 3600)
        if not (0 < gap <= 6):
            continue  # hull i serien - ikke fyll, og ikke ekstrapoler
        v0, v1 = raw[t0], raw[t1]
        for step in range(1, gap):
            frac = step / gap
            tk = hour_key(d0 + dt.timedelta(hours=step))
            out[tk] = {
                "wind_speed": _lerp(v0.get("wind_speed"), v1.get("wind_speed"), frac),
                "wind_dir": _lerp_circular(v0.get("wind_dir"), v1.get("wind_dir"), frac),
                "gust": _lerp(v0.get("gust"), v1.get("gust"), frac),
                "air_temp": _lerp(v0.get("air_temp"), v1.get("air_temp"), frac),
                "wind_interpolated": True,
            }
    return out


# ---------- Open-Meteo GFS-vind (langtid, ROADMAP oppgave B) ----------

OPENMETEO_WIND_MODEL = "gfs_seamless"


def openmeteo_wind(lat, lon):
    """06.10.2026, ROADMAP oppgave B: vind 16 dager frem fra Open-Meteo sin
    GFS-kjede, SAMME dict-form som metno_weather() (wind_speed i m/s,
    wind_dir "fra", gust, air_temp) så den kan skjøtes rett på met.no der
    met.no slutter - se merge_wind(). Live sjekket 06.10.2026: 384 timer,
    alle felt satt, m/s bekreftet via wind_speed_unit=ms.
    {time: {wind_speed, wind_dir, gust, air_temp}}"""
    key = _om_key("wind", lat, lon, OPENMETEO_WIND_MODEL)
    if key in _OM_CACHE:
        return _OM_CACHE[key]
    r = _get(OPENMETEO_WIND_URL, _wind_params([lat], [lon]), timeout=OPENMETEO_TIMEOUT, pauses=OPENMETEO_SINGLE_PAUSES)
    out = _parse_wind_hourly(r.json()["hourly"])
    _OM_CACHE[key] = out
    return out


def _wind_params(lats, lons):
    return {
        "latitude": ",".join(str(x) for x in lats),
        "longitude": ",".join(str(x) for x in lons),
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m,temperature_2m",
        "wind_speed_unit": "ms",
        "timezone": "GMT",
        "forecast_days": 16,
        "models": OPENMETEO_WIND_MODEL,
    }


def _parse_wind_hourly(h):
    out = {}
    for i, t in enumerate(h["time"]):
        key = t + "Z" if len(t) == 16 else t
        key = key[:13] + ":00Z"
        out[key] = {
            "wind_speed": h["wind_speed_10m"][i],
            "wind_dir": h["wind_direction_10m"][i],
            "gust": h["wind_gusts_10m"][i],
            "air_temp": h["temperature_2m"][i],
        }
    return out


def _unique_points(points):
    """Unike punkt (nøkkel på 4 desimaler), men med det FØRSTE ORIGINALE
    koordinatparet - samlekallet skal spørre om nøyaktig samme punkt som
    enkeltkallet (fysikk-kontrollør 10.10.2026: avrunding flytter et
    vindpunkt opptil 5 m, og Open-Meteo kan velge celle/høyde ut fra det)."""
    seen, out = set(), []
    for lat, lon in points:
        k = (round(float(lat), 4), round(float(lon), 4))
        if k not in seen:
            seen.add(k); out.append((lat, lon))
    return out


def openmeteo_prefetch(marine_points, wind_points, batch=None):
    """Samlekall: henter alle havpunkt (GFS Wave + standardmodellen) og alle
    vindpunkt (GFS-vind) i kall med inntil `batch` punkter hver, og legger
    svarene i mellomlageret som _openmeteo_fetch()/openmeteo_wind() leser
    fra. Returnerer tall til kilderapporten: {"points", "calls", "failed",
    "cached"}. Et samlekall som feiler (alle fire forsøk) gir bare at
    punktene hentes enkeltvis etterpå - aldri at noe blir 0 eller tomt.
    Open-Meteo svarer med en liste (én post per punkt, samme rekkefølge og
    med location_id) når flere koordinater sendes, og med én post når det
    bare er ett punkt."""
    batch = batch or OPENMETEO_BATCH
    stats = {"points": 0, "jobs": 0, "calls": 0, "failed": 0, "cached": 0}
    jobs = []
    um, uw = _unique_points(marine_points), _unique_points(wind_points)
    for lat, lon in um:
        for model in (OPENMETEO_SWELL_MODEL, None):
            jobs.append(("marine", lat, lon, model))
    for lat, lon in uw:
        jobs.append(("wind", lat, lon, OPENMETEO_WIND_MODEL))
    stats["points"] = len(um) + len(uw)   # unike punkt
    stats["jobs"] = len(jobs)             # punkt × modell (det som faktisk hentes)
    # grupper per (kilde, modell), så per chunk
    groups = {}
    for kind, lat, lon, model in jobs:
        key = _om_key(kind, lat, lon, model)
        if key in _OM_CACHE:
            stats["cached"] += 1
            continue
        groups.setdefault((kind, model), []).append((lat, lon))
    for (kind, model), pts in groups.items():
        for i in range(0, len(pts), batch):
            chunk = pts[i:i + batch]
            lats, lons = [p[0] for p in chunk], [p[1] for p in chunk]
            stats["calls"] += 1
            try:
                if kind == "marine":
                    r = _get(OPENMETEO_MARINE_URL, _marine_params(lats, lons, model), timeout=OPENMETEO_BATCH_TIMEOUT, pauses=OPENMETEO_PAUSES)
                else:
                    r = _get(OPENMETEO_WIND_URL, _wind_params(lats, lons), timeout=OPENMETEO_BATCH_TIMEOUT, pauses=OPENMETEO_PAUSES)
                data = r.json()
                arr = data if isinstance(data, list) else [data]
                if len(arr) != len(chunk):
                    raise ValueError(f"samlekall ga {len(arr)} poster for {len(chunk)} punkt")
                parsed_all = []
                for j, loc in enumerate(arr):
                    idx = int(loc.get("location_id", j))
                    lat, lon = chunk[idx]
                    # svaret SKAL gjelde punktet vi spurte om (innenfor én
                    # rutenettcelle, 0,3°) - ellers kastes hele samlekallet og
                    # punktene hentes enkeltvis (fysikk-kontrollør 10.10.2026)
                    if abs(float(loc.get("latitude", 999)) - float(lat)) > 0.3 or abs(float(loc.get("longitude", 999)) - float(lon)) > 0.3:
                        raise ValueError(f"samlekall svarte for ({loc.get('latitude')},{loc.get('longitude')}) der vi spurte om ({lat},{lon})")
                    parsed_all.append((lat, lon, _parse_marine_hourly(loc["hourly"]) if kind == "marine" else _parse_wind_hourly(loc["hourly"])))
                for lat, lon, parsed in parsed_all:   # først når ALLE postene er kontrollert
                    _OM_CACHE[_om_key(kind, lat, lon, model)] = parsed
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError, KeyError, IndexError, TypeError) as e:
                stats["failed"] += 1
                print(f"  Open-Meteo samlekall ({kind}, {model or 'standard'}, {len(chunk)} punkt) feilet, punktene hentes enkeltvis: {e}")
    return stats


def merge_wind(metno_hourly, openmeteo_hourly):
    """met.no først (finere, lokal modell) så langt den rekker - inkludert de
    interpolerte timene fra weather_interpolate() - deretter Open-Meteo GFS
    for timer met.no ikke har. Hver time merkes med wind_source ("metno"
    eller "openmeteo") så appen kan vise kilden. Timer uten vind i noen av
    dem utelates (rating.wind_penalty() gir da "ukjent vind"-straffen som
    før)."""
    out = {}
    for t, v in (metno_hourly or {}).items():
        if v.get("wind_speed") is not None:
            out[t] = {**v, "wind_source": "metno"}
    for t, v in (openmeteo_hourly or {}).items():
        if t not in out and v.get("wind_speed") is not None:
            out[t] = {**v, "wind_interpolated": False, "wind_source": "openmeteo"}
    return out


# ---------- Loggene dine (privat GitHub-repo) ----------

def github_logs():
    """Leser logs.json fra det private repoet appen synker til. Tom liste hvis ikke satt opp."""
    repo = os.environ.get("LOGS_REPO")
    token = os.environ.get("LOGS_TOKEN")
    if not repo or not token:
        return []
    r = requests.get(
        f"https://api.github.com/repos/{repo}/contents/logs.json",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json",
                 "User-Agent": HEADERS["User-Agent"]},
        timeout=TIMEOUT,
    )
    if r.status_code == 404:
        return []
    r.raise_for_status()
    data = r.json()
    deleted = set(data.get("deleted", []))
    return [l for l in data.get("logs", []) if l.get("id") not in deleted]
