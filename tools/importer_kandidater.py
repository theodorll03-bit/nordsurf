"""Kandidatimport fra Theodors spot-liste (15.10.2026, ROADMAP K del A punkt 1-3).

Leser privat/kandidater/surfespots_norge.json (aldri i git - inneholder tekst fra andre nettsider og
en hemmelig spot) og skriver data/kandidater/kandidater.json med BARE feltene under. Beskrivelse,
adkomst og farer tas IKKE med (tekst fra andre nettsider - appens tekst skrives av oss senere).
Står det forbud, vern eller militært område i hazards/access, settes bare `vern_mistanke: true`.

Den hemmelige spoten i lista skal ikke stå noe sted i repoet, heller ikke som id. Den kjennes igjen
på SHA-256 av id eller navn (HEMMELIGE_SHA256) og hoppes over; til slutt sjekkes det at verken id
eller navn finnes i utdata. Kjøringen stopper hvis den ikke finnes i lista (da er lista endret, og
utelukkelsen må sjekkes på nytt).

Ingenting her publiseres i appen, og ingen spot legges inn i spots.json.

Kjør: python tools/importer_kandidater.py   (sti til lista: NORDSURF_PRIVAT, standard privat/)"""
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVAT = Path(os.environ.get("NORDSURF_PRIVAT") or ROOT / "privat")
SRC = PRIVAT / "kandidater" / "surfespots_norge.json"
OUT = ROOT / "data" / "kandidater" / "kandidater.json"

# sha256 av id og navn (små bokstaver) for spoten Theodor holder hemmelig - aldri skriv klarteksten her
HEMMELIGE_SHA256 = {
    "58e28d08733f9d5b4e0b508a6ccd6ab988b865726c756bed3c2e48ac7474e2d6",
    "2007adaed5630bd1ec35ab1211417b572bada24910b55f70bd22997eff56c27e",
}
# Theodor 16.10.2026: to kandidater er hemmelige - bygges ikke, og ingen id, navn eller koordinater i git. De kjennes
# igjen på SHA-256 av id/navn (som den utelatte over) og skrives bare til privat/kandidater/hemmelige.json.
HEMMELIG_SHA256 = {
    "ba1d1270c59cfc646104d71135cfafa674f187058bba6ba75b9adf639f3a5f1b",
    "e909f8cfab26c651456268a168823d319782afdf23afc92897de2e430369578f",
    "dd170ec624305a0d560682111e40f417b5a90a8d67c15c17fff1de6d6a00f022",
}
HEMMELIGE_FIL = PRIVAT / "kandidater" / "hemmelige.json"
# Theodor 16.10.2026: vanlig kandidat, men lavest prioritet
LAV_PRIORITET = {"vetvika"}
VENTER_PA_SVAR = {}
VURDERING = {}

# lista sitt id → spots.json sin id for de 8 vi har fra før (røres ikke)
KJENTE = {"unstad-beach": "unstad"}

# Regionforslag (Theodor godkjenner senere; legges i spots.json først når første spot i regionen bygges)
# Theodors ja 16.10.2026: forslaget pluss «Hordaland» (Øygarden og andre uten region); nord til sør
REGIONER = ["Finnmark", "Troms", "Vesterålen", "Lofoten", "Salten", "Møre og Romsdal", "Stad og Nordfjord",
            "Hordaland", "Karmøy", "Jæren", "Dalane og Lista", "Sørlandet", "Østlandet"]
REGION_FRA_LISTA = {
    "Finnmark": "Finnmark", "Varanger": "Finnmark",
    "Troms": "Troms", "Senja": "Troms",
    "Vesterålen": "Vesterålen", "Lofoten": "Lofoten", "Salten": "Salten",
    "Sunnmøre": "Møre og Romsdal", "Romsdal/Hustadvika": "Møre og Romsdal",
    "Stad": "Stad og Nordfjord", "Nordfjord/Sunnfjord-kysten": "Stad og Nordfjord", "Sogn og Fjordane / Kinn": "Stad og Nordfjord",
    "Hordaland / Øygarden": "Hordaland",
    "Karmøy": "Karmøy", "Jæren": "Jæren",
    "Dalane": "Dalane og Lista", "Lista": "Dalane og Lista",
    "Lindesnes": "Sørlandet", "Sørlandet": "Sørlandet",
    "Bamble": "Østlandet", "Larvik": "Østlandet", "Vestfold": "Østlandet", "Oslofjorden": "Østlandet",
    "Oslofjorden / Moss": "Østlandet", "Sandefjord / Vesterøya": "Østlandet", "Østfold/Hvaler": "Østlandet",
}
# regioner i lista som ikke passer i noen av forslagene - region null + merknad (spørsmål til Theodor)
REGION_MERKNAD = {
    "Sogn og Fjordane / Kinn": "Kinn (Florø) er Sunnfjord, lagt i Stad og Nordfjord som nærmeste forslag",
    "Nordfjord/Sunnfjord-kysten": "Sunnfjord-kysten lagt i Stad og Nordfjord som nærmeste forslag",
}

VERN_ORD = re.compile(r"forbud|forbudt|ferdselsforbud|vern|verne|fredning|fredet|reservat|ramsar|militær|skytefelt|adgang forbudt", re.I)
HINT_FELT = ["break_type", "bottom", "best_swell_dir", "best_wind_dir", "skill_level"]


def sha(v):
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


def is_secret(s):
    return sha(s["id"]) in HEMMELIG_SHA256 or sha(s["name"].lower()) in HEMMELIG_SHA256


def is_hidden(s):
    return sha(s["id"]) in HEMMELIGE_SHA256 or sha(s["name"].lower()) in HEMMELIGE_SHA256


def haversine_m(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def split_list(v):
    return [x.strip() for x in re.split(r"[;,]", v or "") if x.strip()]


def urls(v):
    return [u.rstrip(").,;") for u in re.findall(r"https?://\S+", v or "")]


def main():
    if not SRC.exists():
        sys.exit(f"Fant ikke {SRC} (lista ligger bare lokalt hos Theodor, i privat/)")
    raw = json.loads(SRC.read_text(encoding="utf-8"))
    hidden = [s for s in raw if is_hidden(s)]
    if len(hidden) != 1:
        sys.exit(f"Forventet nøyaktig én hemmelig spot i lista, fant {len(hidden)} - sjekk utelukkelsen før import")
    spots_cfg = {s["id"]: s for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"]}
    global VURDERING
    vf = ROOT / "data" / "kandidater" / "vern_vurdering.json"
    VURDERING = json.loads(vf.read_text(encoding="utf-8"))["kandidater"] if vf.exists() else {}

    out = []
    for s in raw:
        if is_hidden(s):
            continue
        reg_liste = s["region"]
        region = REGION_FRA_LISTA.get(reg_liste)
        known_id = None
        if s.get("i_nordsurf") == "ja":
            known_id = KJENTE.get(s["id"], s["id"])
            assert known_id in spots_cfg, f"{s['id']} er merket i_nordsurf, men {known_id} finnes ikke i spots.json"
        rec = {
            "id": s["id"],
            "name": s["name"],
            "aliases": [a for a in split_list(s.get("alt_names")) if a != s["name"]],
            "fylke": s.get("fylke"),
            "kommune": s.get("kommune"),
            "region": region,
            "pin_liste": {"lat": s["lat"], "lon": s["lon"]},
            "coord_confidence": s.get("coord_confidence"),
            "hint": {**{k: s.get(k) for k in HINT_FELT}, "_kilde": "fra lista, ubekreftet"},
            "source_count": s.get("source_count"),
            "sources": urls(s.get("sources")),
            "dokumentasjon": s.get("dokumentasjon"),
            "status": "i_nordsurf" if known_id else "hemmelig" if is_secret(s) else "kandidat",
        }
        if s["id"] in LAV_PRIORITET:
            rec["prioritet"] = "lav"
        vv = VURDERING.get(s["id"])
        if vv:   # Theodor 16.10: bølgen i verneområdet → «forbudt»; ellers en linje om verneområdet
            if vv.get("status") == "forbudt" and rec["status"] == "kandidat":
                rec["status"] = "forbudt"
            if vv.get("merknad"):
                rec["vern_merknad"] = vv["merknad"]
        if REGION_MERKNAD.get(reg_liste):
            rec["region_merknad"] = REGION_MERKNAD[reg_liste]
        if VERN_ORD.search((s.get("hazards") or "") + " " + (s.get("access") or "")):
            rec["vern_mistanke"] = True
        if s["id"] in VENTER_PA_SVAR:
            rec["venter_pa_theodor"] = VENTER_PA_SVAR[s["id"]]
        if known_id:
            pin = spots_cfg[known_id]["spot"]
            rec["nordsurf_id"] = known_id
            rec["avstand_pinne_nal_m"] = round(haversine_m(rec["pin_liste"], pin))
        out.append(rec)

    hemmelige = [r for r in out if r["status"] == "hemmelig"]
    out = [r for r in out if r["status"] != "hemmelig"]
    if len(hemmelige) != 2:
        sys.exit(f"Forventet to hemmelige kandidater, fant {len(hemmelige)} - sjekk HEMMELIG_SHA256 før import")
    HEMMELIGE_FIL.parent.mkdir(parents=True, exist_ok=True)
    HEMMELIGE_FIL.write_text(json.dumps({"_info": "Hemmelige kandidater (Theodor 16.10.2026) - aldri i git.", "kandidater": hemmelige},
                                        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    doc = {"_info": "Kandidater fra Theodors liste 15.10.2026 (ROADMAP K del A). Bare posisjon, kommune og hint - "
                    "ingen tekst fra lista. Hint og pin_liste er ubekreftet. Ikke publisert i appen; ingen spot i spots.json herfra. "
                    "Regionene er forslag til Theodor.",
           "regioner_forslag": REGIONER,
           "antall": len(out),
           "kandidater": out}
    text = json.dumps(doc, ensure_ascii=False, indent=1)
    for h in hidden + [x for x in raw if is_secret(x)]:
        assert h["id"] not in text and h["name"].lower() not in text.lower(), "en hemmelig spot lekket inn i utdata"
        assert f'"lat": {h["lat"]}' not in text, "koordinatene til en hemmelig spot lekket inn i utdata"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text + "\n", encoding="utf-8")
    kj = [r for r in out if r["status"] == "i_nordsurf"]
    print(f"Skrev {OUT.relative_to(ROOT)}: {len(out)} spots ({len(kj)} i Nordsurf fra før, {len(out) - len(kj)} kandidater), "
          f"{sum(1 for r in out if r.get('vern_mistanke'))} med vern_mistanke, {sum(1 for r in out if r['region'] is None)} uten region, "
          f"{len(hemmelige)} hemmelige skrevet til privat/")
    for r in kj:
        print(f"  {r['id']:16} → {r['nordsurf_id']:16} pinne-nål {r['avstand_pinne_nal_m']} m")


if __name__ == "__main__":
    main()
