"""Inndata-arkiv for testlaben (skyøkt 07.10.2026, oppgave 1): en kompakt
kopi av INNDATAENE per time i docs/data/forecast.json (ikke resultatet -
det ligger i data/forecast_archive/), så en benchmark eller logg for et
tidspunkt kan re-rates med andre varianter senere. Leser bare forecast.json
og skriver data/backtest/inputs/<generert>.json. Kjøres av
.github/workflows/backtest.yml (og kan kjøres lokalt).

S40 (svar.md 24.11.2026 kl. 22.25): lagres også hver dag. «Hent varsel»
(.github/workflows/forecast.yml) kjører `backtest_inputs.py --daglig` etter
publish.py: døgnets første varsel (UTC) lagres, senere kjøringer samme døgn
gjør ingenting. Fila følger med i den commiten boten uansett lager
(«Nytt varsel (læringsdata)»), så det blir ingen ekstra commit. Før lå bare
mandagens bilde i git, og en hendelse som Unstad lørdag 21.11.2026 var ikke
med. Spots med status «hemmelig» lagres aldri her (forecast.json er uten dem
etter publish.py, og main() hopper over dem uansett).

Bare de første INPUT_HOURS timene per spot lagres (benchmarks/logger gjelder
nær nåtid; langtidsrader er anslag uansett)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORECAST = ROOT / "docs" / "data" / "forecast.json"
OUT_DIR = ROOT / "data" / "backtest" / "inputs"
INPUT_HOURS = 72
INPUT_KEYS = ("bw_height", "bw_dir", "bw_period", "bw_height_max", "bw_interpolated", "swell_offshore", "height_offshore",
              "dir_offshore", "period", "swell_model", "secondary_swell_height", "secondary_swell_dir", "secondary_swell_period",
              "height_spot_model", "turn", "wind_speed", "wind_dir", "gust", "wind_source", "tide", "light", "daylight",
              # S29 c del 1 (24.11.2026): samlet sjø og vindsjø-del ute, så regelen for lang sjø kan prøves bakover
              "total_model", "bw_period_real_max_3h", "total_height_offshore", "total_dir_offshore", "total_period_offshore",
              "wind_wave_height_offshore", "wind_wave_dir_offshore", "wind_wave_period_offshore",
              # K3 (fysikk-kontrolløren 25.11.2026): regelen for lang sjø hopper over timer der svellet er glattet (M3).
              # Uten merket ville en avspilling av arkivet regnet slike timer annerledes enn henteren gjorde.
              "swell_despiked")


def snapshot(fc):
    """Inndata-bildet av et varsel: de første INPUT_HOURS timene per spot, bare INPUT_KEYS, og bare verdier som
    finnes (None lagres ikke, så «mangler» blir aldri et tall). Spots med status «hemmelig» er aldri med."""
    # time_axis_verified: timene er varselets egne («t» i forecast.json, UTC), ikke et oppslag i en modellfil.
    # backtest.load_inputs_archive() leser bare filer med merket (K3: uten det ble arkivet aldri lest av testlaben).
    out = {"generated": fc["generated"], "time_axis_verified": True, "spots": {}}
    for s in fc["spots"]:
        if s.get("status") == "hemmelig":
            continue
        out["spots"][s["id"]] = {h["t"]: {k: h.get(k) for k in INPUT_KEYS if h.get(k) is not None} for h in s["hours"][:INPUT_HOURS]}
    return out


def has_day(out_dir, generated):
    """Finnes det allerede et bilde fra samme døgn (UTC) som dette varselet?"""
    return any(Path(out_dir).glob(f"{generated[:10]}T*.json"))


def main(argv=None, forecast_path=FORECAST, out_dir=OUT_DIR):
    """Skriver bildet og returnerer stien. Med --daglig: ingenting (None) når døgnet allerede har et bilde."""
    argv = sys.argv[1:] if argv is None else argv
    fc = json.loads(Path(forecast_path).read_text(encoding="utf-8"))
    out_dir = Path(out_dir)
    if "--daglig" in argv and has_day(out_dir, fc["generated"]):
        print(f"Døgnet {fc['generated'][:10]} har allerede et inndata-bilde, skriver ikke et nytt")
        return None
    out = snapshot(fc)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = fc["generated"][:13].replace(":", "")
    path = out_dir / f"{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Skrev {path} ({path.stat().st_size // 1024} KB)")
    return path


if __name__ == "__main__":
    main()
