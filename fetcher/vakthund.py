"""Vakthund for varselet (Theodor 16.10.2026, punkt 1b): kjøres hver 6. time fra .github/workflows/vakthund.yml
(fotavtrykk 10.11.2026; før hver 3.), 1,5 t etter en «Hent varsel». Varsler hvis

  - varselet på live-siden (docs/data/oversikt.json, «generated») er eldre enn MAKS_ALDER_T timer (pluss
    NATT_TILLEGG_T over natthullet, se maks_alder()), eller
  - «Hent varsel» (forecast.yml) har feilet to ganger på rad (de to siste fullførte kjøringene).

Varselet er en GitHub-issue «Varselet står stille» (Theodor 16.10: NTFY_TOPIC settes ikke nå) med alderen og lenke
til siste feilede kjøring. Finnes det alt en åpen issue med den tittelen, kommenteres den i stedet. Høyst ett
varsel/kommentar per sjekk (hver 6. time; DEDUPE_T målt mot issuens siste aktivitet). Når varselet er ferskt igjen og «Hent
varsel» ikke feiler, lukker vakthunden issuen selv med en kommentar. ntfy sendes i tillegg bare hvis NTFY_TOPIC
finnes (da med en liten tilstandsfil for 6-timersgrensen, som workflowen tar vare på med actions/cache).

Bakgrunn: 15.10 kl. 19Z-16.10 ca. 09Z feilet «Hent varsel» uten at noen merket det (PR #19).

«Lyngen henger sammen» (svar.md 23.11.2026 kl. 14.05): i samme kjøring leser vakthunden detaljfilene for
Breivikeidet, Russelv og Lenangsøyra fra live-siden. Har Breivikeidet minst 2 poeng i en time der Russelv eller
Lenangsøyra viser «Flatt» eller «Treffer ikke», åpner den en egen issue, «Lyngen henger ikke sammen» (se
lyngen_avvik() og vakt_lyngen()). Mørke timer telles ikke (appen viser «Mørkt» der). Bare varsel: ratingen endres aldri herfra.

Testing (bare utenfor main): VAKTHUND_TEST_ALDER_T=<timer> later som varselet er så gammelt (workflow_dispatch-
input «test_alder_timer»), og issuen merkes som test.

  python fetcher/vakthund.py [tilstandsfil]   (env: GITHUB_TOKEN, GITHUB_REPOSITORY, NTFY_TOPIC, RUN_URL)"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

LIVE = "https://theodorll03-bit.github.io/nordsurf/data/oversikt.json"
MAKS_ALDER_T = 7       # «generated» er rundet ned til hel time: to uteblitte kjøringer på rad (3 t mellom hver) gir 7-8 t
# Fotavtrykk (Theodor 10.11.2026): «Hent varsel» kjører 03:17-21:17 UTC (forecast.yml: 17 3-21/3) - kjøringen
# kl. 00:17 UTC finnes ikke lenger, så om natta går det 6 timer. Ligger det hullet mellom «generated» og nå,
# tåles 3 timer til - ellers ville ÉN uteblitt kjøring kl. 03:17 gitt alarm kl. 04:47 (før: først etter to).
NATT_HULL_UTC = (0, 17)
NATT_TILLEGG_T = 3
DEDUPE_T = 5           # sjekkene går hver 6. time (± forsinkelsen i GitHub sin cron): 5 gir én kommentar per sjekk, aldri annenhver
FEIL_PA_RAD = 2
TITTEL = "Varselet står stille"
UA = {"User-Agent": "nordsurf-vakthund/1.0 (github.com/theodorll03-bit/nordsurf)"}


def maks_alder(gen, now):
    """Timer varselet kan være gammelt før det er et problem: MAKS_ALDER_T, pluss NATT_TILLEGG_T når natthullet
    (kl. 00:17 UTC, kjøringen som ikke finnes) ligger mellom «generated» og nå."""
    hull = gen.astimezone(dt.timezone.utc).replace(hour=NATT_HULL_UTC[0], minute=NATT_HULL_UTC[1], second=0, microsecond=0)
    if hull <= gen:
        hull += dt.timedelta(days=1)
    return MAKS_ALDER_T + (NATT_TILLEGG_T if hull <= now else 0)


def problemer(oversikt, kjoringer, now):
    """Liste med problemer (tom = alt i orden). oversikt: dict eller None (ikke lest); kjoringer: siste fullførte
    «Hent varsel»-kjøringer, nyeste først, [{"conclusion", "created_at", "html_url"}] eller None (ukjent)."""
    out = []
    if oversikt is None:
        out.append("fant ikke varselet på live-siden (oversikt.json kunne ikke leses)")
    else:
        gen = oversikt.get("generated")
        if not gen:
            out.append("varselet på live-siden mangler «generated»")
        else:
            try:
                t = dt.datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
                alder, grense = (now - t).total_seconds() / 3600, maks_alder(t, now)
            except (ValueError, TypeError):
                out.append(f"varselet på live-siden har ugyldig «generated» ({gen!r})")
            else:
                if alder > grense:
                    out.append(f"varselet er {alder:.0f} timer gammelt (generert {gen})")
    if kjoringer:
        siste = kjoringer[:FEIL_PA_RAD]
        if len(siste) == FEIL_PA_RAD and all(k.get("conclusion") == "failure" for k in siste):
            out.append(f"«Hent varsel» har feilet {FEIL_PA_RAD} ganger på rad - siste: {siste[0].get('html_url') or siste[0].get('created_at')}")
    return out


def siste_feilede(kjoringer):
    return next((k for k in (kjoringer or []) if k.get("conclusion") == "failure"), None)


class GitHub:
    """Det lille av GitHub-API-et vakthunden trenger (issues). Byttes ut med en falsk i testen."""

    def __init__(self, repo, token, session=None):
        self.repo, self.s = repo, session or requests.Session()
        self.h = {**UA, "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    def _url(self, p):
        return f"https://api.github.com/repos/{self.repo}/{p}"

    def kjoringer(self):
        r = self.s.get(self._url("actions/workflows/forecast.yml/runs"), params={"status": "completed", "per_page": 5, "branch": "main"}, headers=self.h, timeout=30)
        r.raise_for_status()
        return [{"conclusion": k.get("conclusion"), "created_at": k.get("created_at"), "html_url": k.get("html_url")} for k in r.json().get("workflow_runs", [])]

    def apen_issue(self, tittel=TITTEL):
        r = self.s.get(self._url("issues"), params={"state": "open", "per_page": 50}, headers=self.h, timeout=30)
        r.raise_for_status()
        return next((i for i in r.json() if i.get("title") == tittel and "pull_request" not in i), None)

    def ny_issue(self, body, tittel=TITTEL):
        r = self.s.post(self._url("issues"), json={"title": tittel, "body": body, "labels": ["vakthund"]}, headers=self.h, timeout=30)
        r.raise_for_status()
        return r.json()

    def kommenter(self, nr, body):
        self.s.post(self._url(f"issues/{nr}/comments"), json={"body": body}, headers=self.h, timeout=30).raise_for_status()

    def lukk(self, nr):
        self.s.patch(self._url(f"issues/{nr}"), json={"state": "closed", "state_reason": "completed"}, headers=self.h, timeout=30).raise_for_status()


def tekst(probs, kjoringer, now, test=False):
    f = siste_feilede(kjoringer)
    linjer = [f"**{now:%d.%m.%Y kl. %H:%M} UTC** - vakthunden fant:", ""] + [f"- {p}" for p in probs]
    if f:
        linjer += ["", f"Siste feilede «Hent varsel»: {f.get('html_url') or f.get('created_at')}"]
    if test:
        linjer += ["", "_TEST: alderen er kunstig (VAKTHUND_TEST_ALDER_T, kjørt utenfor main) - lukkes ved neste ferske kjøring._"]
    linjer += ["", "Vakthunden kommenterer høyst hver 6. time og lukker issuen selv når varselet er ferskt igjen."]
    return "\n".join(linjer)


def iso(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00"))


def vakt(gh, oversikt, kjoringer, now, test=False):
    """Hovedlogikken for issuen. Returnerer (hva, nr): «ny», «kommentert», «dedupe», «lukket», «ukjent» (ferskt
    varsel, men kjøringene kunne ikke leses - issuen blir stående) eller «i orden»."""
    probs = problemer(oversikt, kjoringer, now)
    issue = gh.apen_issue()
    if not probs and kjoringer is None:
        # kjøringene kunne ikke leses: ikke bevis for at alt er i orden - la en åpen issue stå (kontrollør 16.10)
        print("Vakthund: varselet er ferskt, men «Hent varsel»-kjøringene er ukjente - lar issuen stå")
        return "ukjent", issue["number"] if issue else None
    if not probs:
        if issue:
            gh.kommenter(issue["number"], f"**{now:%d.%m.%Y kl. %H:%M} UTC** - varselet er ferskt igjen og «Hent varsel» feiler ikke. Lukker.")
            gh.lukk(issue["number"])
            print(f"Vakthund: alt i orden igjen - lukket issue #{issue['number']}")
            return "lukket", issue["number"]
        print("Vakthund: alt i orden")
        return "i orden", None
    if issue:
        sist = iso(issue.get("updated_at") or issue["created_at"])
        if now - sist < dt.timedelta(hours=DEDUPE_T):
            print(f"Vakthund: problem, men issue #{issue['number']} er oppdatert siste {DEDUPE_T} t - hopper over: {'; '.join(probs)}")
            return "dedupe", issue["number"]
        gh.kommenter(issue["number"], tekst(probs, kjoringer, now, test))
        print(f"Vakthund: kommenterte issue #{issue['number']}: {'; '.join(probs)}")
        return "kommentert", issue["number"]
    ny = gh.ny_issue(tekst(probs, kjoringer, now, test))
    print(f"Vakthund: opprettet issue #{ny.get('number')}: {'; '.join(probs)}")
    return "ny", ny.get("number")


def ntfy(probs, now, state, post=None):
    """Tillegg når NTFY_TOPIC finnes: ett ntfy-varsel, høyst ett per 6 t (state). Uten NTFY_TOPIC: bare logget."""
    post = post or requests.post
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("Vakthund: NTFY_TOPIC ikke satt - bare issue/logg")
        return False
    sist = state.get("sendt")
    if sist and now - dt.datetime.fromisoformat(sist) < dt.timedelta(hours=DEDUPE_T):
        return False
    msg = {"topic": topic, "title": "Nordsurf: varselet står stille", "message": "; ".join(probs), "tags": ["warning"], "priority": 4}
    if os.environ.get("RUN_URL"):
        msg["click"] = os.environ["RUN_URL"]
    try:
        post("https://ntfy.sh/", json=msg, timeout=20).raise_for_status()
    except Exception as e:  # noqa: BLE001 - vakthunden skal aldri feile selv
        print(f"Vakthund: ntfy feilet: {e}")
        return False
    state["sendt"] = now.isoformat()
    return True


def les_oversikt(now, forsok=2, pause_s=10, get=None, sleep=None):
    """oversikt.json fra live-siden; ett nytt forsøk etter noen sekunder før «kunne ikke leses» regnes som et problem."""
    get, sleep = get or requests.get, sleep or __import__("time").sleep
    for i in range(forsok):
        try:
            r = get(LIVE, params={"v": int(now.timestamp()) + i}, headers=UA, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"Kunne ikke lese {LIVE} (forsøk {i + 1} av {forsok}): {e}")
            if i + 1 < forsok:
                sleep(pause_s)
    return None


# ---------- «Lyngen henger sammen» ----------
# svar.md 23.11.2026 kl. 14.05 (Theodor: «Hvis det er surf på Breivikeidet er det så å si alltid bølger på de to andre
# spottene i Lyngen»; kilder: observasjon 17.11.2026 og 22.11.2026, Theodor): Breivikeidet ligger innerst i samme fjord som
# Russelv og Lenangsøyra. Svell som gir bølger på Breivikeidet har passert de to andre. Sjekken varsler når varselet
# likevel sier noe annet. Den endrer ingenting selv.
LIVE_SPOT = "https://theodorll03-bit.github.io/nordsurf/data/spots/{id}.json"
LYNGEN_ANKER = "breivikeidet"
LYNGEN_FOLGER = ("russelv", "lenangsoyra")
LYNGEN_MIN_POENG = 2          # Breivikeidet må ha minst så mange poeng i timen
LYNGEN_TITTEL = "Lyngen henger ikke sammen"
LYNGEN_DEDUPE_T = 23          # samme avvik står i varselet i dagevis: høyst én kommentar i døgnet (sjekkene går hver 6. time)
LYNGEN_MAKS_LINJER = 12       # timer som listes i issuen, resten telles
SMALL_SURF_MIN_M = 0.3        # under dette heter en time uten poeng «Flatt» (samme grense som docs/js/app.js)


def lyngen_ord(h):
    """«Flatt» eller «Treffer ikke» når appen viser det ordet for timen (ratingWord() i docs/js/app.js, med
    zeroWord() og calmWindWord()), ellers None. Mangler tallet (0 poeng uten grunn og uten surfehøyde), viser
    appen «–»: det er ukjent og gir None (manglende data er aldri 0)."""
    stars, grunn, surf = h.get("stars") or 0, h.get("low_reason"), h.get("surf_height")
    if not stars and grunn in (None, "", "flat") and surf is not None:
        return "Flatt" if surf < SMALL_SURF_MIN_M else None          # zeroWord(): fra 0,3 m heter timen noe annet
    if grunn == "blown_out":
        # calmWindWord(): svak vind uten poengtap og under 0,3 m heter «Flatt». Ellers får vinden ordet.
        if stars or surf is None or surf >= SMALL_SURF_MIN_M:
            return None
        tapt = max((h.get("zero_losses") or {}).get("wind") or 0, h.get("faded_wind") or 0)
        if tapt > 0:
            return None
        import rating  # ligger ved siden av denne fila, bare standardbiblioteket
        sterk = rating.blown_out_wind_strong(h.get("wind_speed"), h.get("gust"), h.get("wind_type"), h.get("wind_calm_ms"))
        return "Flatt" if sterk is False else None
    if grunn == "flat":
        return "Flatt"
    if grunn == "treffer_ikke":
        return "Treffer ikke"
    return None


def lyngen_morkt(h):
    """Sann når timen er mørk i dataene (lysfeltet «light» er "mørkt", eller det mangler og «daylight» er False, som
    lightClass() i docs/js/app.js). Appen viser «Mørkt» og ikke ordet i slike timer. Mangler begge feltene, er lyset
    ukjent, og timen regnes ikke som mørk."""
    lys = h.get("light")
    return lys == "mørkt" if lys is not None else h.get("daylight") is False


def lyngen_avvik(detaljer, now):
    """(avvik, ukjente). detaljer: {spot_id: detaljfila fra live-siden, eller None når den ikke kunne leses}.
    avvik: timer fra og med denne timen der Breivikeidet har minst LYNGEN_MIN_POENG poeng mens Russelv eller
    Lenangsøyra viser «Flatt» eller «Treffer ikke» (lyngen_ord()). ukjente: spotene som ikke kunne sjekkes,
    fordi fila mangler, er uten timer eller er fra en annen kjøring («run») enn Breivikeidets. Ukjent er
    aldri et avvik. En time som mangler hos den ene, eller poeng som mangler, hoppes over.
    24.11.2026 (feiljegeren, funn 5): mørke timer hos Russelv eller Lenangsøyra telles ikke (lyngen_morkt()). Appen
    viser «Mørkt» der og ikke «Flatt» eller «Treffer ikke». Timer uten lysfelt telles som før."""
    anker = detaljer.get(LYNGEN_ANKER)
    if not anker or not anker.get("hours"):
        return [], list(LYNGEN_FOLGER)
    fra = now.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:00Z")
    gode = {h.get("t"): h for h in anker["hours"]
            if h.get("t") and h["t"] >= fra and isinstance(h.get("stars"), int) and h["stars"] >= LYNGEN_MIN_POENG}
    avvik, ukjente = [], []
    for spot_id in LYNGEN_FOLGER:
        d = detaljer.get(spot_id)
        if not d or not d.get("hours") or d.get("run") != anker.get("run"):
            ukjente.append(spot_id)
            continue
        for h in d["hours"]:
            a = gode.get(h.get("t"))
            ordet = lyngen_ord(h) if a and not lyngen_morkt(h) else None
            if ordet:
                avvik.append({"t": h["t"], "spot": spot_id, "navn": d.get("name") or spot_id, "ord": ordet, "poeng": h.get("stars") or 0,
                              "surf_height": h.get("surf_height"), "anker_poeng": a["stars"], "anker_surf_height": a.get("surf_height")})
    return sorted(avvik, key=lambda x: (x["t"], x["spot"])), ukjente


def _m(v):
    return "ukjent høyde" if v is None else f"{v:.1f}".replace(".", ",") + " m"


def lyngen_tekst(avvik, now, run=None):
    linjer = [f"**{now:%d.%m.%Y kl. %H:%M} UTC** - vakthunden fant {len(avvik)} time(r) der Breivikeidet har minst {LYNGEN_MIN_POENG} poeng "
              "mens Russelv eller Lenangsøyra viser «Flatt» eller «Treffer ikke»:", ""]
    for a in avvik[:LYNGEN_MAKS_LINJER]:
        linjer.append(f"- {a['t'][8:10]}.{a['t'][5:7]} kl. {a['t'][11:13]}Z: Breivikeidet {a['anker_poeng']} poeng ({_m(a['anker_surf_height'])}), "
                      f"{a['navn']} «{a['ord']}» ({a['poeng']} poeng, {_m(a['surf_height'])})")
    if len(avvik) > LYNGEN_MAKS_LINJER:
        linjer.append(f"- og {len(avvik) - LYNGEN_MAKS_LINJER} time(r) til")
    linjer += ["", "Regelen (Theodor 23.11.2026): når Breivikeidet har surf, er det så å si alltid bølger på Russelv og Lenangsøyra. "
               "Dette er bare et varsel. Vakthunden endrer ikke ratingen." + (f" Varselet er fra kjøring {run}." if run else ""),
               "", "Vakthunden kommenterer høyst én gang i døgnet og lukker issuen selv når varselet ikke lenger har slike timer."]
    return "\n".join(linjer)


def vakt_lyngen(gh, avvik, ukjente, now, run=None):
    """Issuen «Lyngen henger ikke sammen», samme gang som vakt(). Returnerer (hva, nr): «ny», «kommentert»,
    «dedupe», «lukket», «ukjent» (ingen avvik funnet, men minst én spot kunne ikke sjekkes: en åpen issue blir
    stående) eller «i orden»."""
    issue = gh.apen_issue(LYNGEN_TITTEL)
    nr = issue["number"] if issue else None
    if not avvik:
        if ukjente:
            print(f"Vakthund: Lyngen-sjekken kunne ikke gjøres for {', '.join(ukjente)} - ingen alarm, lar en åpen issue stå")
            return "ukjent", nr
        if issue:
            gh.kommenter(nr, f"**{now:%d.%m.%Y kl. %H:%M} UTC** - varselet har ikke lenger timer der Breivikeidet har minst {LYNGEN_MIN_POENG} poeng "
                             "mens Russelv eller Lenangsøyra viser «Flatt» eller «Treffer ikke». Lukker.")
            gh.lukk(nr)
            print(f"Vakthund: Lyngen henger sammen igjen - lukket issue #{nr}")
            return "lukket", nr
        print("Vakthund: Lyngen henger sammen")
        return "i orden", None
    kort = f"{len(avvik)} time(r), første {avvik[0]['t']} ({avvik[0]['navn']} «{avvik[0]['ord']}»)"
    if issue:
        sist = iso(issue.get("updated_at") or issue["created_at"])
        if now - sist < dt.timedelta(hours=LYNGEN_DEDUPE_T):
            print(f"Vakthund: Lyngen henger ikke sammen, men issue #{nr} er oppdatert siste {LYNGEN_DEDUPE_T} t - hopper over: {kort}")
            return "dedupe", nr
        gh.kommenter(nr, lyngen_tekst(avvik, now, run))
        print(f"Vakthund: kommenterte issue #{nr} (Lyngen): {kort}")
        return "kommentert", nr
    ny = gh.ny_issue(lyngen_tekst(avvik, now, run), LYNGEN_TITTEL)
    print(f"Vakthund: opprettet issue #{ny.get('number')} (Lyngen): {kort}")
    return "ny", ny.get("number")


def les_lyngen(now, get=None):
    """Detaljfilene for de tre spotene fra live-siden: {spot_id: dict eller None}. Ett forsøk per fil med kort
    tidsgrense (workflowen gir vakthunden 120 s i alt). En fil som ikke kan leses er ukjent, ikke et avvik."""
    get, ut = get or requests.get, {}
    for spot_id in (LYNGEN_ANKER,) + LYNGEN_FOLGER:
        url = LIVE_SPOT.format(id=spot_id)
        try:
            r = get(url, params={"v": int(now.timestamp())}, headers=UA, timeout=15)
            r.raise_for_status()
            ut[spot_id] = r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"Kunne ikke lese {url}: {e}")
            ut[spot_id] = None
    return ut


def main():
    sti = Path(sys.argv[1] if len(sys.argv) > 1 else "vakthund_state.json")
    state = json.loads(sti.read_text(encoding="utf-8")) if sti.exists() else {}
    now = dt.datetime.now(dt.timezone.utc)
    oversikt = les_oversikt(now)
    test_alder = os.environ.get("VAKTHUND_TEST_ALDER_T")
    if test_alder and oversikt is not None:
        oversikt = {**oversikt, "generated": (now - dt.timedelta(hours=float(test_alder))).isoformat()}
        print(f"Vakthund: TEST - later som varselet er {test_alder} timer gammelt")
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    kj = None
    if repo and token:
        gh = GitHub(repo, token)
        try:
            kj = gh.kjoringer()
        except (requests.RequestException, ValueError) as e:
            print(f"Kunne ikke lese «Hent varsel»-kjøringene: {e}")
        try:
            vakt(gh, oversikt, kj, now, test=bool(test_alder))
        except (requests.RequestException, ValueError) as e:
            print(f"Vakthund: GitHub-issue feilet: {e}")
    else:
        print("GITHUB_REPOSITORY/GITHUB_TOKEN ikke satt - ingen issue, bare logg")
    probs = problemer(oversikt, kj, now)
    if probs:
        ntfy(probs, now, state)
        sti.write_text(json.dumps(state), encoding="utf-8")
    # «Lyngen henger sammen»: til slutt, og bare når live-siden svarte. En feil her skal aldri stoppe vakthunden.
    if repo and token and oversikt is not None:
        try:
            detaljer = les_lyngen(now)
            avvik, ukjente = lyngen_avvik(detaljer, now)
            vakt_lyngen(gh, avvik, ukjente, now, run=(detaljer.get(LYNGEN_ANKER) or {}).get("run"))
        except Exception as e:  # noqa: BLE001 - vakthunden skal aldri feile selv
            print(f"Vakthund: Lyngen-sjekken feilet: {e}")


if __name__ == "__main__":
    main()
