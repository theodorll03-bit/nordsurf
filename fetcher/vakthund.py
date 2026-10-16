"""Vakthund for varselet (Theodor 16.10.2026, punkt 1b): kjøres hver 3. time fra .github/workflows/vakthund.yml,
forskjøvet fra «Hent varsel». Varsler hvis

  - varselet på live-siden (docs/data/oversikt.json, «generated») er eldre enn MAKS_ALDER_T timer, eller
  - «Hent varsel» (forecast.yml) har feilet to ganger på rad (de to siste fullførte kjøringene).

Varselet er en GitHub-issue «Varselet står stille» (Theodor 16.10: NTFY_TOPIC settes ikke nå) med alderen og lenke
til siste feilede kjøring. Finnes det alt en åpen issue med den tittelen, kommenteres den i stedet. Høyst ett
varsel/kommentar per DEDUPE_T timer (målt mot issuens siste aktivitet). Når varselet er ferskt igjen og «Hent
varsel» ikke feiler, lukker vakthunden issuen selv med en kommentar. ntfy sendes i tillegg bare hvis NTFY_TOPIC
finnes (da med en liten tilstandsfil for 6-timersgrensen, som workflowen tar vare på med actions/cache).

Bakgrunn: 15.10 kl. 19Z-16.10 ca. 09Z feilet «Hent varsel» uten at noen merket det (PR #19).

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
MAKS_ALDER_T = 7
DEDUPE_T = 6
FEIL_PA_RAD = 2
TITTEL = "Varselet står stille"
UA = {"User-Agent": "nordsurf-vakthund/1.0 (github.com/theodorll03-bit/nordsurf)"}


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
            alder = (now - dt.datetime.fromisoformat(gen.replace("Z", "+00:00"))).total_seconds() / 3600
            if alder > MAKS_ALDER_T:
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

    def apen_issue(self):
        r = self.s.get(self._url("issues"), params={"state": "open", "per_page": 50}, headers=self.h, timeout=30)
        r.raise_for_status()
        return next((i for i in r.json() if i.get("title") == TITTEL and "pull_request" not in i), None)

    def ny_issue(self, body):
        r = self.s.post(self._url("issues"), json={"title": TITTEL, "body": body, "labels": ["vakthund"]}, headers=self.h, timeout=30)
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
    """Hovedlogikken for issuen. Returnerer (hva, nr): «ny», «kommentert», «dedupe», «lukket» eller «i orden»."""
    probs = problemer(oversikt, kjoringer, now)
    issue = gh.apen_issue()
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


def les_oversikt(now):
    try:
        r = requests.get(LIVE, params={"v": int(now.timestamp())}, headers=UA, timeout=30)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"Kunne ikke lese {LIVE}: {e}")
        return None


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
        except requests.RequestException as e:
            print(f"Kunne ikke lese «Hent varsel»-kjøringene: {e}")
        try:
            vakt(gh, oversikt, kj, now, test=bool(test_alder))
        except requests.RequestException as e:
            print(f"Vakthund: GitHub-issue feilet: {e}")
    else:
        print("GITHUB_REPOSITORY/GITHUB_TOKEN ikke satt - ingen issue, bare logg")
    probs = problemer(oversikt, kj, now)
    if probs:
        ntfy(probs, now, state)
        sti.write_text(json.dumps(state), encoding="utf-8")


if __name__ == "__main__":
    main()
