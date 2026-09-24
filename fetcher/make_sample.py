"""Lager eksempeldata for å se på appen uten ekte API-kall. Kjør: python fetcher/make_sample.py
Ett felles værscenario for hele regionen, ratet med den ekte ratinglogikken per spot."""
import json, math, datetime as dt
from pathlib import Path
from rating import rate, angle_diff, window_sectors, in_sector
import sun, tide as tidemod

ROOT = Path(__file__).resolve().parent.parent
spots = [s for s in json.loads((ROOT / "spots.json").read_text())["spots"] if s.get("enabled")]
now = dt.datetime(2026, 9, 24, 12, tzinfo=dt.timezone.utc)

def scenario(i):
    """Svell dreier fra VNV mot NNØ over tre døgn, vokser og legger seg. Vind: sørøst, så nordvest."""
    swell_dir = (296 + i * 1.2) % 360
    swell_h = 1.2 + 1.6 * math.sin(min(i, 60) / 60 * math.pi)
    period = 9 + 5 * math.sin(min(i, 50) / 50 * math.pi)
    wind_dir = 150 if i < 40 else (320 if i < 58 else 200)
    wind = 3 + (5 if 40 <= i < 58 else 0) + 1.5 * math.sin(i / 5)
    return swell_dir, swell_h, period, wind_dir, wind

def hour(spot, i, t):
    sd, sh, p, wd, ws = scenario(i)
    inside = any(in_sector(sd, s) for s in window_sectors(spot))
    turn = 6 if inside else 30
    h = {"t": t.strftime("%Y-%m-%dT%H:00Z"), "height_offshore": round(sh, 1),
         "height_spot_model": round(sh * (0.85 if inside else 0.9), 1), "bw_height": None,
         "swell_offshore": round(sh * 0.75, 1),
         "dir_offshore": round(sd), "dir_spot": round((sd + turn) % 360), "turn": turn,
         "period": round(p, 1), "water_temp": 8.2, "wind_speed": round(ws, 1),
         "wind_dir": wd, "gust": round(ws * 1.6), "air_temp": 6.8,
         "light": sun.light(spot["spot"]["lat"], spot["spot"]["lon"], t)}
    h["daylight"] = h["light"] != "mørkt"
    h["tide"] = tidemod.state_at(TIDES, t + dt.timedelta(minutes=30))
    h.update(rate(h, spot))
    return h

def tide():
    t0 = now - dt.timedelta(hours=3, minutes=20)
    return [{"time": (t0 + dt.timedelta(minutes=372.5 * k)).isoformat(),
             "type": "flo" if k % 2 == 0 else "fjære", "cm": 245 if k % 2 == 0 else 55} for k in range(15)]
TIDES = tide()

out_spots = []
for s in spots:
    pub = {k: v for k, v in s.items() if not k.startswith("_")}
    hrs = [hour(s, i, now + dt.timedelta(hours=i)) for i in range(72)]
    out_spots.append({**pub, "hours": hrs, "tide_events": TIDES, "calibration": {},
                      "light_days": sun.light_days(s["spot"]["lat"], s["spot"]["lon"], now)})

out = ROOT / "docs" / "data" / "forecast.json"
out.write_text(json.dumps({"generated": now.isoformat(), "sample": True, "spots": out_spots,
                               "notify": {"min_stars": 3, "hours_ahead": 36, "spots": []}}, ensure_ascii=False))
for s in out_spots:
    print(f"{s['name']:<16}", " ".join(f"{h['stars']}{'+'+str(h['faded']) if h['faded'] else ''}" for h in s["hours"][::6]))
