"""Varsler via ntfy når en spot får et godt vindu i brukbart lys.

Oppsett: installer ntfy-appen, abonner på et hemmelig emnenavn, og legg samme navn inn
som secret NTFY_TOPIC. Innstillinger i notify.json.
"""
import os
import json
import datetime as dt
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "notified.json"
TZ_OFFSET_NOTE = "Europe/Oslo"


def load_settings():
    p = ROOT / "notify.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def notifiable_hours(spot):
    """Spots med BarentsWatch skal bare varsle på ekte BarentsWatch-timer -
    reservemodellen (etter bw_until) er for usikker til å varsle på. Spots
    uten BarentsWatch i det hele tatt bruker alle timene, som før."""
    if spot.get("bw_until"):
        return [h for h in spot["hours"] if h.get("height_source") == "barentswatch"]
    return spot["hours"]


def windows(spot, min_stars, hours_ahead, now):
    """Sammenhengende timer i brukbart lys med minst min_stars. Beste vindu først."""
    out, cur = [], None
    for h in notifiable_hours(spot):
        t = dt.datetime.fromisoformat(h["t"].replace("Z", "+00:00"))
        if t > now + dt.timedelta(hours=hours_ahead):
            break
        good = h["stars"] >= min_stars and h.get("daylight") is not False
        if good and cur and t - cur["end"] <= dt.timedelta(hours=1):
            cur["end"] = t
            cur["best"] = max(cur["best"], h["stars"])
            cur["hours"].append(h)
        elif good:
            cur = {"start": t, "end": t, "best": h["stars"], "hours": [h]}
            out.append(cur)
        else:
            cur = None
    return sorted(out, key=lambda w: (-w["best"], w["start"]))


def local(t):
    # Norsk tid: UTC+1 om vinteren, UTC+2 om sommeren (siste søndag i mars til siste søndag i oktober)
    y = t.year
    def last_sunday(m):
        d = dt.datetime(y, m, 31, 1, tzinfo=dt.timezone.utc)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    off = 2 if last_sunday(3) <= t < last_sunday(10) else 1
    return t + dt.timedelta(hours=off)


def describe(spot, w, now):
    s, e = local(w["start"]), local(w["end"] + dt.timedelta(hours=1))
    day = {0: "i dag", 1: "i morgen"}.get((s.date() - local(now).date()).days, ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"][s.weekday()])
    top = max(w["hours"], key=lambda h: h["stars"])
    parts = [f"{top['height']:.1f} m".replace(".", ",") if top.get("height") is not None else None,
             f"{top['period']:.0f} s" if top.get("period") else None,
             top.get("wind_type")]
    return f"{spot['name']}: {w['best']} stjerner {day} {s:%H}–{e:%H}", ", ".join(p for p in parts if p)


def run(forecast, now):
    topic = os.environ.get("NTFY_TOPIC")
    cfg = load_settings()
    if not topic:
        print("Varsler: NTFY_TOPIC er ikke satt, hopper over.")
        return
    min_stars, ahead = cfg.get("min_stars", 3), cfg.get("hours_ahead", 36)
    only = set(cfg.get("spots") or [])
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    # glem gamle varsler
    state = {k: v for k, v in state.items() if dt.datetime.fromisoformat(v["end"]) > now - dt.timedelta(days=1)}
    for spot in forecast["spots"]:
        if only and spot["id"] not in only:
            continue
        ws = windows(spot, min_stars, ahead, now)
        if not ws:
            continue
        w = ws[0]
        key = f"{spot['id']}:{w['start'].date().isoformat()}"
        prev = state.get(key)
        if prev and prev["best"] >= w["best"]:
            continue  # allerede varslet om dette, og det har ikke blitt bedre
        title, body = describe(spot, w, now)
        msg = {"topic": topic, "title": title, "message": body, "tags": ["ocean"],
               "priority": 4 if w["best"] >= 4 else 3}
        if os.environ.get("APP_URL"):
            msg["click"] = os.environ["APP_URL"]
        try:
            requests.post("https://ntfy.sh/", json=msg, timeout=20).raise_for_status()
            print(f"Varslet: {title}")
            state[key] = {"best": w["best"], "end": w["end"].isoformat()}
        except Exception as e:
            print(f"Varsel feilet: {e}")
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1))
