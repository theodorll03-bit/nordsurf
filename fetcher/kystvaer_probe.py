"""Oppgave 2 (skyøkt 07.10.2026), steg a: SONDERING av KystVær/Kystdatahuset
sitt API for vindmålinger. Skyøkten har ikke nett mot kystdatahuset.no
(egress-policy), så dette kjøres i GitHub Actions (.github/workflows/
kystvaer_probe.yml) og skriver det som ble funnet til data/wind_obs/probe.md.

Prøver kjente/gjettede inngangspunkter uten nøkkel og rapporterer status,
innholdstype og de første tegnene av svaret - ALDRI mer enn det som trengs
for å finne riktig endepunkt og se om det krever registrering. Leser bare.
"""
import datetime as dt
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "wind_obs" / "probe.md"
UA = {"User-Agent": f"nordsurf-kystvaer-probe ({os.environ.get('UA_CONTACT', 'ukjent-kontakt')})", "Accept": "application/json, text/html;q=0.5, */*;q=0.1"}

CANDIDATES = [
    # Kystdatahuset sine kjente tjenester (swagger/OpenAPI først - de lister resten)
    "https://kystdatahuset.no/ws/swagger/index.html",
    "https://kystdatahuset.no/ws/swagger/v1/swagger.json",
    "https://kystdatahuset.no/ws/swagger.json",
    "https://kystdatahuset.no/ws/api/swagger.json",
    "https://kystdatahuset.no/ws/",
    "https://kystdatahuset.no/ws/api/",
    # gjett på vær/vind-ruter
    "https://kystdatahuset.no/ws/api/vaer",
    "https://kystdatahuset.no/ws/api/vaer/stasjoner",
    "https://kystdatahuset.no/ws/api/vaer/stations",
    "https://kystdatahuset.no/ws/api/kystvaer",
    "https://kystdatahuset.no/ws/api/kystvaer/stations",
    "https://kystdatahuset.no/ws/api/kystvaer/stasjoner",
    "https://kystdatahuset.no/ws/api/weather/stations",
    "https://kystdatahuset.no/ws/api/wind/stations",
    "https://kystdatahuset.no/ws/api/windstations",
    # KystVær-appen sin egen backend (kjente domener fra appen/nettsiden)
    "https://kystvaer.kystverket.no/",
    "https://kystvaer.kystverket.no/api/",
    "https://kystvaer.kystverket.no/api/stations",
    "https://kystvaer.kystverket.no/api/v1/stations",
    "https://kystvaer.kystverket.no/api/observations",
    "https://kystvar.kystverket.no/",
    "https://www.kystverket.no/sjovegen/vartjenester/kystvar/",
    "https://kystinfo.no/",
    "https://kystverket.avadaptive.no/api/core/swagger/index.html",
    "https://kystverket.avadaptive.no/api/core/swagger/v1/swagger.json",
    # met.no Frost (krever client-id - sjekker bare at det faktisk er slik)
    "https://frost.met.no/sources/v0.jsonld?types=SensorSystem&country=NO&municipality=TROMS%C3%98",
    "https://frost.met.no/api.html",
]


def probe(url):
    try:
        r = requests.get(url, headers=UA, timeout=25, allow_redirects=True)
    except Exception as e:
        return {"url": url, "status": "FEIL", "detail": str(e)[:160]}
    ctype = r.headers.get("content-type", "")
    body = r.text or ""
    snippet = re.sub(r"\s+", " ", body[:600])
    links = []
    if "json" in ctype:
        try:
            data = r.json()
            if isinstance(data, dict):
                links = [f"paths: {list(data.get('paths', {}).keys())[:60]}"] if "paths" in data else [f"keys: {list(data.keys())[:30]}"]
            elif isinstance(data, list):
                links = [f"liste med {len(data)} elementer, første: {json.dumps(data[0], ensure_ascii=False)[:300] if data else ''}"]
        except Exception:
            pass
    else:
        hrefs = re.findall(r'href="([^"]+)"', body)
        links = [h for h in hrefs if any(k in h.lower() for k in ("api", "swagger", "vaer", "vind", "wind", "kystv", "station", "stasjon", "doc"))][:40]
    return {"url": url, "status": r.status_code, "final_url": r.url, "ctype": ctype[:60], "len": len(body),
            "snippet": snippet, "links": links,
            "auth_hint": "ja" if r.status_code in (401, 403) or re.search(r"api[-_ ]?key|client[-_ ]?id|unauthorized|forbidden|registrer", body[:3000], re.I) else "nei"}


SWAGGER = "https://kystdatahuset.no/ws/swagger/v1/swagger.json"
KEYWORDS = ("wind", "vind", "weather", "vaer", "vær", "kystv", "meteo", "sensor", "station", "stasjon", "observ", "measure", "maaling", "måling")


def probe_swagger():
    """Andre runde (07.10.2026): hele OpenAPI-spesifikasjonen, filtrert på
    vær/vind - ruter, parametre, om de krever innlogging (security), og et
    forsøk på GET uten parametre der det går."""
    lines = ["## Swagger: vær/vind-ruter i Kystdatahuset Open API", ""]
    try:
        spec = requests.get(SWAGGER, headers=UA, timeout=60).json()
    except Exception as e:
        return lines + [f"- FEIL: {e}"]
    servers = spec.get("servers")
    global_sec = spec.get("security")
    lines.append(f"- servers: {servers}, global security: {global_sec}, securitySchemes: {list((spec.get('components') or {}).get('securitySchemes', {}).keys())}")
    lines.append(f"- antall ruter totalt: {len(spec.get('paths', {}))}")
    hits = []
    for path, ops in spec.get("paths", {}).items():
        blob = (path + " " + json.dumps(ops, ensure_ascii=False)[:3000]).lower()
        if any(k in blob for k in KEYWORDS):
            hits.append((path, ops))
    lines.append(f"- ruter som matcher vær/vind-nøkkelord: {len(hits)}")
    base = "https://kystdatahuset.no/ws"
    for path, ops in hits:
        for method, op in ops.items():
            if method.lower() not in ("get", "post"):
                continue
            params = [(p.get("name"), p.get("in"), p.get("required"), (p.get("schema") or {}).get("type")) for p in op.get("parameters", [])]
            body = "ja" if op.get("requestBody") else "nei"
            lines.append(f"### {method.upper()} {path}")
            lines.append(f"- tags {op.get('tags')}, summary: {str(op.get('summary') or op.get('description') or '')[:200]}")
            lines.append(f"- parametre: {params}, body: {body}, security: {op.get('security', 'arver global')}")
            if method.lower() == "get" and not any(req for _, _, req, _ in params) and "{" not in path:
                try:
                    r = requests.get(base + path, headers=UA, timeout=30)
                    snippet = re.sub(r"\s+", " ", (r.text or "")[:500])
                    lines.append(f"- GET uten parametre: status {r.status_code}, {r.headers.get('content-type','')[:40]}, {len(r.text or '')} tegn: `{snippet}`")
                except Exception as e:
                    lines.append(f"- GET feilet: {str(e)[:120]}")
    return lines


def main():
    results = [probe(u) for u in CANDIDATES]
    lines = [f"# KystVær/Kystdatahuset-sondering, {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    for r in results:
        lines.append(f"## {r['url']}")
        if r["status"] == "FEIL":
            lines.append(f"- FEIL: {r['detail']}")
        else:
            lines.append(f"- status {r['status']}, {r['ctype']}, {r['len']} tegn, endte på {r['final_url']}, nøkkel/innlogging antydet: {r['auth_hint']}")
            if r["links"]:
                lines.append(f"- lenker/nøkler: {r['links']}")
            lines.append(f"- utdrag: `{r['snippet'][:400]}`")
        lines.append("")
    lines = probe_swagger() + [""] + lines
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
