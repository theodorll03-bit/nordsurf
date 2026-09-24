"""Tidevann time for time, interpolert mellom flo og fjære fra Kartverket."""
import math
import datetime as dt


def _p(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def state_at(events, t: dt.datetime):
    """Returnerer {'level': 0..1 (0 = fjære, 1 = flo), 'state': 'lav'/'middels'/'høy', 'rising': bool} eller None."""
    ev = sorted(events, key=lambda e: e["time"])
    for a, b in zip(ev, ev[1:]):
        ta, tb = _p(a["time"]), _p(b["time"])
        if ta <= t <= tb and a["type"] != b["type"]:
            frac = (t - ta) / (tb - ta)
            s = (1 - math.cos(math.pi * frac)) / 2
            level = s if a["type"] == "fjære" else 1 - s
            state = "lav" if level < 1 / 3 else ("høy" if level > 2 / 3 else "middels")
            return {"level": round(level, 2), "state": state, "rising": b["type"] == "flo"}
    return None
