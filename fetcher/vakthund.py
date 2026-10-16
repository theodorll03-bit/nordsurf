"""Vakthund for varselet (Theodor 16.10.2026, punkt 1b): kjøres hver 3. time fra .github/workflows/vakthund.yml,
forskjøvet fra «Hent varsel». Sender ett ntfy-varsel til Theodor hvis

  - varselet på live-siden (docs/data/oversikt.json, «generated») er eldre enn MAKS_ALDER_T timer, eller
  - «Hent varsel» (forecast.yml) har feilet to ganger på rad (de to siste fullførte kjøringene).

Høyst ett varsel per DEDUPE_T timer (tilstanden ligger i en liten JSON-fil som workflowen tar vare på med
actions/cache - ingen commits til main, ingenting i data/). Uten NTFY_TOPIC: bare logget («NTFY_TOPIC ikke satt»),
som henteren gjør - vakthunden feiler aldri selv på det.

Bakgrunn: 15.10 kl. 19Z-16.10 ca. 09Z feilet «Hent varsel» uten at noen merket det (PR #19).

  python fetcher/vakthund.py [tilstandsfil]   (env: NTFY_TOPIC, GITHUB_TOKEN, GITHUB_REPOSITORY)"""
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
UA = {"User-Agent": "nordsurf-vakthund/1.0 (github.com/theodorll03-bit/nordsurf)"}


def problemer(oversikt, kjoringer, now):
    """Liste med problemer (tom = alt i orden). oversikt: dict eller None (ikke lest); kjoringer: siste fullførte
    «Hent varsel»-kjøringer, nyeste først, som [{"conclusion": "success"|"failure"|…, "created_at": iso}] eller None."""
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
            out.append(f"«Hent varsel» har feilet {FEIL_PA_RAD} ganger på rad (siste {siste[0].get('created_at')})")
    return out


def skal_sende(state, now):
    sist = state.get("sendt")
    return not sist or now - dt.datetime.fromisoformat(sist) >= dt.timedelta(hours=DEDUPE_T)


def les_oversikt(now):
    try:
        r = requests.get(LIVE, params={"v": int(now.timestamp())}, headers=UA, timeout=30)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"Kunne ikke lese {LIVE}: {e}")
        return None


def les_kjoringer():
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        print("GITHUB_REPOSITORY/GITHUB_TOKEN ikke satt - hopper over sjekken av «Hent varsel»-kjøringene")
        return None
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/actions/workflows/forecast.yml/runs",
                         params={"status": "completed", "per_page": 5, "branch": "main"},
                         headers={**UA, "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, timeout=30)
        r.raise_for_status()
        return [{"conclusion": k.get("conclusion"), "created_at": k.get("created_at")} for k in r.json().get("workflow_runs", [])]
    except (requests.RequestException, ValueError) as e:
        print(f"Kunne ikke lese «Hent varsel»-kjøringene: {e}")
        return None


def varsle(probs, now, state, post=None):
    """Sender (eller logger) ett varsel; oppdaterer state ved sending. Returnerer True hvis sendt."""
    post = post or requests.post
    tekst = "; ".join(probs)
    if not skal_sende(state, now):
        print(f"Vakthund: problem, men varslet siste {DEDUPE_T} t - hopper over: {tekst}")
        return False
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print(f"Vakthund: NTFY_TOPIC ikke satt, bare logget: {tekst}")
        return False
    msg = {"topic": topic, "title": "Nordsurf: varselet står stille", "message": tekst, "tags": ["warning"], "priority": 4}
    if os.environ.get("RUN_URL"):
        msg["click"] = os.environ["RUN_URL"]
    try:
        post("https://ntfy.sh/", json=msg, timeout=20).raise_for_status()
    except Exception as e:  # noqa: BLE001 - vakthunden skal aldri feile selv
        print(f"Vakthund: varselet feilet: {e}")
        return False
    state["sendt"] = now.isoformat()
    print(f"Vakthund: varsel sendt: {tekst}")
    return True


def main():
    sti = Path(sys.argv[1] if len(sys.argv) > 1 else "vakthund_state.json")
    state = json.loads(sti.read_text(encoding="utf-8")) if sti.exists() else {}
    now = dt.datetime.now(dt.timezone.utc)
    probs = problemer(les_oversikt(now), les_kjoringer(), now)
    if not probs:
        print("Vakthund: alt i orden")
        return
    varsle(probs, now, state)
    sti.write_text(json.dumps(state), encoding="utf-8")


if __name__ == "__main__":
    main()
