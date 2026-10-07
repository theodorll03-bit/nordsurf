"""Inndata-arkiv for testlaben (skyøkt 07.10.2026, oppgave 1): en kompakt
kopi av INNDATAENE per time i docs/data/forecast.json (ikke resultatet -
det ligger i data/forecast_archive/), så en benchmark eller logg for et
tidspunkt kan re-rates med andre varianter senere. Leser bare forecast.json
og skriver data/backtest/inputs/<generert>.json. Kjøres av
.github/workflows/backtest.yml (og kan kjøres lokalt).

Bare de første INPUT_HOURS timene per spot lagres (benchmarks/logger gjelder
nær nåtid; langtidsrader er anslag uansett)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORECAST = ROOT / "docs" / "data" / "forecast.json"
OUT_DIR = ROOT / "data" / "backtest" / "inputs"
INPUT_HOURS = 72
INPUT_KEYS = ("bw_height", "bw_dir", "bw_period", "bw_height_max", "bw_interpolated", "swell_offshore", "height_offshore",
              "dir_offshore", "period", "swell_model", "secondary_swell_height", "secondary_swell_dir", "secondary_swell_period",
              "height_spot_model", "turn", "wind_speed", "wind_dir", "gust", "wind_source", "tide", "light", "daylight")


def main():
    fc = json.loads(FORECAST.read_text(encoding="utf-8"))
    out = {"generated": fc["generated"], "spots": {}}
    for s in fc["spots"]:
        out["spots"][s["id"]] = {h["t"]: {k: h.get(k) for k in INPUT_KEYS if h.get(k) is not None} for h in s["hours"][:INPUT_HOURS]}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = fc["generated"][:13].replace(":", "")
    path = OUT_DIR / f"{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Skrev {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
