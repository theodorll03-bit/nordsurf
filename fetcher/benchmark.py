"""07.10.2026, Theodors oppgave: samler sammenligninger mot surf-forecast/
Surfline (data/benchmark/comparisons.json) og rapporterer om det er nok
(minst 10) til å kalibrere PEAK_PERIOD_FACTOR_DEFAULT (rating.py sin
energy_period()) på nytt. Kalibrerer IKKE automatisk - skriver bare ut hva
en ny verdi VILLE blitt, så Theodor kan velge å sette den selv.

Fremtidige skjermbilder legges i data/benchmark/inbox/ - Claude leser dem
med Read-verktøyet (støtter bilder) og legger en ny rad inn i
comparisons.json for hånd, samme format som den første raden (fra tekst,
07.10.2026).

Kjør: python fetcher/benchmark.py"""
import json
import statistics
from pathlib import Path

import rating

ROOT = Path(__file__).resolve().parent.parent
COMPARISONS = ROOT / "data" / "benchmark" / "comparisons.json"
MIN_FOR_CALIBRATION = 10


def main():
    data = json.loads(COMPARISONS.read_text(encoding="utf-8"))
    rows = data.get("comparisons", [])
    ratios = [r["tp_tm_ratio"] for r in rows if r.get("tp_tm_ratio")]
    print(f"{len(rows)} sammenligning(er) i {COMPARISONS.relative_to(ROOT)} ({len(ratios)} med et Tp/Tm-forhold).")
    for r in rows:
        print(f"  {r['date']} {r.get('time_local', '?')} {r['spot']}: "
              f"app {r['app'].get('period_s')} s ({r['app'].get('period_type')}) vs. "
              f"{r['benchmark_source']} {r['benchmark'].get('period_s')} s ({r['benchmark'].get('period_type')})"
              + (f" -> Tp/Tm {r['tp_tm_ratio']}" if r.get("tp_tm_ratio") else ""))
    if len(ratios) < MIN_FOR_CALIBRATION:
        print(f"\nFor få til kalibrering ennå ({len(ratios)}/{MIN_FOR_CALIBRATION}) - "
              f"PEAK_PERIOD_FACTOR_DEFAULT (rating.py) står uendret.")
        return
    median_ratio = statistics.median(ratios)
    current = f"{rating.PEAK_PERIOD_FACTOR_DEFAULT:.2f}".replace(".", ",")
    print(f"\n{len(ratios)} forhold samlet - median Tp/Tm = {median_ratio:.3f}. "
          f"Dagens PEAK_PERIOD_FACTOR_DEFAULT er {current} (rating.py). "
          f"Vurder å sette den til {median_ratio:.2f} - IKKE gjort automatisk, krever Theodors ja.")


if __name__ == "__main__":
    main()
