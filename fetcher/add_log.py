"""Legg inn en logg i logs.json i det private loggrepoet (Theodor 15.10.2026,
Farstadsanden «Holy portugal»): samme fil og format som appen synker til
(docs/js/app.js syncLogs(): {"logs": [...], "deleted": [...]}), så loggen
teller i kalibrering (calibrate.py) og testlaben (backtest.py) som en ekte
observasjon.

Kjøres fra workflowen «Legg inn logg» (LOGS_REPO/LOGS_TOKEN finnes bare i
Actions). Slår sammen med en eksisterende logg for samme spot innen 2 timer
(Theodor kan ha logget økta selv) i stedet for å lage en duplikat: felt som
mangler i den eksisterende fylles inn, felt som finnes beholdes. Skriver aldri
ut nøkkelen. Alle kall har frist.

Kjør: python fetcher/add_log.py '<json for loggen>'   (eller LOGG-miljøvariabelen)"""
import base64
import datetime as dt
import json
import os
import sys

import requests

TIMEOUT = 30


def main():
    repo, token = os.environ.get("LOGS_REPO"), os.environ.get("LOGS_TOKEN")
    if not repo or not token:
        print("LOGS_REPO/LOGS_TOKEN mangler - ingenting skrevet.")
        return 1
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LOGG", "")
    entry = json.loads(raw)
    for k in ("id", "spot", "t", "stars", "type"):
        assert k in entry, f"loggen mangler {k}"
    url = f"https://api.github.com/repos/{repo}/contents/logs.json"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "nordsurf-add-log"}
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    sha, data = None, {"logs": [], "deleted": []}
    if r.status_code == 200:
        j = r.json(); sha = j["sha"]
        data = json.loads(base64.b64decode(j["content"]).decode("utf-8"))
    elif r.status_code != 404:
        r.raise_for_status()
    logs = data.get("logs", [])
    t = dt.datetime.fromisoformat(entry["t"].replace("Z", "+00:00"))
    merged_into = None
    for l in logs:
        if l.get("spot") != entry["spot"] or not l.get("t"):
            continue
        lt = dt.datetime.fromisoformat(l["t"].replace("Z", "+00:00"))
        if abs((lt - t).total_seconds()) <= 2 * 3600:
            for k, v in entry.items():
                if k == "id":
                    continue
                if l.get(k) in (None, "") and v not in (None, ""):
                    l[k] = v
            note = entry.get("source")
            if note and note not in (l.get("source") or ""):
                l["source"] = ((l.get("source") or "") + " | " + note).strip(" |")
            merged_into = l["id"]
            break
    if merged_into:
        print(f"Slått sammen med eksisterende logg {merged_into} (samme spot innen 2 timer).")
    else:
        logs.append(entry)
        print(f"Ny logg {entry['id']} lagt til ({entry['spot']} {entry['t']}, {entry['stars']} stjerner).")
    data["logs"] = logs
    body = json.dumps(data, ensure_ascii=False, indent=1)
    payload = {"message": "Legg inn logg (fetcher/add_log.py)", "content": base64.b64encode(body.encode("utf-8")).decode("ascii")}
    if sha:
        payload["sha"] = sha
    put = requests.put(url, headers=headers, json=payload, timeout=TIMEOUT)
    put.raise_for_status()
    print(f"logs.json oppdatert: {len(logs)} logger.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
