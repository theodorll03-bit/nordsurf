"""Delt, avhengighetsfri kjerne for eksponering per retning (del C, 27.09.2026,
oppgave 2). Ingen basemap/shapely her - den tunge geometribyggingen skjer bare
i exposure_baseline.py (kjøres sjelden, manuelt). Denne fila importeres BÅDE
derfra (for spot_checksum, samme hash begge veier) og av fetch.py (som kjører
i hver GitHub Actions-runde og derfor ikke kan dra inn de tunge avhengighetene)."""
import json
import hashlib


def spot_checksum(spot):
    """Hash av det som faktisk brukes til baseline - endres et av feltene i
    spots.json, blir denne ugyldig (se fetch.py sin advarsel i kilderapporten)."""
    key = {"spot": spot["spot"], "swell_window": spot["swell_window"], "facing": spot.get("facing")}
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:16]
