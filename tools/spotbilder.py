"""Kornfoto per spot (design B 4.0 «Papir», docs/design/b4/SPEC.md §7; Theodor 12.11.2026): henter et utsnitt
rundt spoten fra Kartverkets skyfrie Sentinel-2-mosaikk og lager «Trykk» (dag, varm) og «Lodd» (mørketid, blå)
med samme korn som designskissene. Lagres som docs/img/spots/<id>-trykk.jpg og <id>-lodd.jpg, og kilden for
hvert bilde skrives til docs/img/spots/kilder.json. Appen leser docs/js/spotbilder.js (hvilke spots som har bilde,
og krediteringen som står under bildet), som skrives her når bildene går til standardmappa.
<id>.jpg i samme mappe er fortsatt satt av til Theodors egne bilder (README.md der).

Kilde: «Satellittdata - Sentinel-2 - Skyfritt opptak Norge <år>» (Kartverket), åpne data, CC BY 4.0
(kartkatalog.geonorge.no, sjekket 12.11.2026), hentet fra WMS-en wms.geonorge.no/skwms1/wms.sentinel2
(åpne data, ett lag per år). Metadataene krever henvisningen i KREDIT under. Kartverkets vilkår
(kartverket.no/api-og-data/vilkar-for-bruk): gratisproduktene er CC BY 4.0, også til kommersiell bruk.
ANDRE kilder er ikke lov her: EOxCloudless (CC BY-NC-SA) og Norge i bilder/Geovekst skal aldri i git eller docs/.

Behandlingen (rekkefølgen er poenget, SPEC §7):
1. gråtone (luminans), 2. strekk mellom 1. og 99. persentil med gamma 0,85, 3. korn FØR fargekartet
(normalfordelt støy i lav oppløsning, skalert opp bilineært: «film»-kornet), 4. fargekart (rampe).
Aldri korall i bildene og aldri tekst på dem.

Utsnitt: nord opp, spoten i midten. Ett WMS-kall per spot (5,66 x 4,25 km i 800x600 px, ca. 7 m per piksel som i
skissene); variantene skjæres ut av det. Hemmelige spots (status «hemmelig») lages aldri, og verktøyet leser bare
spots.json. Hvert kall har frist, og det er en pause mellom kallene.

Kjør: python3 tools/spotbilder.py unstad grotfjord        (bare disse)
      python3 tools/spotbilder.py --alle                  (alle påslåtte spots i spots.json)
      --ut <mappe> (standard docs/img/spots), --raa <mappe> (rå utsnitt, gjenbrukes; standard en midlertidig mappe),
      --aar 2025, --varianter header,web,skive,kart (standard header)
      python3 tools/spotbilder.py --js                    (bare docs/js/spotbilder.js på nytt fra kilder.json, uten nett)"""
import argparse
import datetime as dt
import io
import json
import math
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
UT = ROOT / "docs" / "img" / "spots"
JS = ROOT / "docs" / "js" / "spotbilder.js"
WMS = "https://wms.geonorge.no/skwms1/wms.sentinel2"
UA = "nordsurf-spotbilder (tools/spotbilder.py, github.com/theodorll03-bit/nordsurf)"
AAR = 2025
FRIST_S = 60
PAUSE_S = 2.0
LISENS = "CC BY 4.0"
LISENS_URL = "https://creativecommons.org/licenses/by/4.0/"


def kredit(aar):
    """Henvisningen metadataene i Geonorge krever, pluss lisens og at bildet er endret (CC BY 4.0 punkt 3a)."""
    return (f"Laget av Sentinel-2 ({aar}) bilder fra Copernicus-programmet til EU, bearbeidet av Kartverket, "
            f"basert på metoder utviklet fra CESBIO og CNES. {LISENS}. Farger og korn: Nordsurf.")


def kredit_kort(aar):
    """Kortformen ved skiva og på Hjem (Theodor 16.11.2026). Den fulle henvisningen står under toppbildet på spotsiden."""
    return f"Sentinel-2 ({aar}), Copernicus/Kartverket · {LISENS}"


# Rått utsnitt: 800 x 600 px, 7,075 m per piksel (som skissene), spoten i midten.
RAA_PX = (800, 600)
M_PER_PX = 7.075

TRYKK = [(0.0, "#1F2A30"), (0.35, "#5C5A53"), (0.7, "#B9B2A4"), (1.0, "#F2EFE8")]   # dag
LODD = [(0.0, "#00131F"), (0.3, "#002941"), (0.9, "#B6DFED"), (1.0, "#F2EFE8")]     # mørketid

# Variantene fra privat/design-b4/foto (behandle.py og trykk.py), med boksen flyttet så spoten står i midten.
# boks = (venstre, topp, høyre, bunn) i det rå utsnittet; maks = (Trykk, Lodd).
VARIANTER = {
    "header": dict(boks=(140, 141, 660, 459), size=(1179, 720), maks=(0.93, 0.82), sigma=0.07, partikkel=2.5, navn=""),
    "web": dict(boks=(0, 200, 800, 400), size=(1440, 360), maks=(0.93, 0.82), sigma=0.07, partikkel=1.6, navn="-web"),
    "skive": dict(boks=(315, 215, 485, 385), size=(336, 336), maks=(1.0, 1.0), sigma=0.06, partikkel=2.0, navn="-skive"),
    "kart": dict(boks=(250, 200, 550, 400), size=(720, 480), maks=(0.95, 1.0), sigma=0.06, partikkel=1.8, navn="-kart"),
}
KVALITET = {"trykk": 88, "lodd": 84}


def hx(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def fargekart(L, stops):
    out = np.zeros(L.shape + (3,), dtype=np.float32)
    xs = [s[0] for s in stops]
    cols = [hx(s[1]) for s in stops]
    for c in range(3):
        out[..., c] = np.interp(L, xs, [col[c] for col in cols])
    return np.clip(out, 0, 255).astype(np.uint8)


def luminans(img):
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def korn(shape, sigma, partikkel, seed):
    rng = np.random.default_rng(seed)
    h, w = shape
    sh, sw = max(1, int(h / partikkel)), max(1, int(w / partikkel))
    n = rng.normal(0, 1, (sh, sw)).astype(np.float32)
    n_img = Image.fromarray(((n * 0.15 + 0.5).clip(0, 1) * 255).astype(np.uint8))
    n_img = n_img.resize((w, h), Image.BILINEAR)
    n2 = (np.asarray(n_img, dtype=np.float32) / 255.0 - 0.5) / 0.15
    return n2 * sigma


def behandle(src, boks, size, stops, maks=1.0, sigma=0.06, gamma=0.85, partikkel=2.0, seed=7):
    """Samme behandling som privat/design-b4/foto/behandle.py: lysstyrke -> korn -> fargekart."""
    crop = src.crop(boks).resize(size, Image.LANCZOS)
    L = luminans(crop)
    lo, hi = np.percentile(L, 1), np.percentile(L, 99)
    L = np.clip((L - lo) / max(hi - lo, 1e-6), 0, 1) ** gamma
    L = np.clip(L + korn(L.shape, sigma, partikkel, seed), 0, 1)
    L = L * maks
    return Image.fromarray(fargekart(L, stops))


def bbox(lat, lon, bredde_m=RAA_PX[0] * M_PER_PX, hoyde_m=RAA_PX[1] * M_PER_PX):
    """(vest, sør, øst, nord) i grader for et utsnitt med spoten i midten. Lengdegradene strekkes med 1/cos(lat),
    så bildet blir nord opp og like langt i meter per piksel begge veier (lokal sylinderprojeksjon)."""
    dlat = hoyde_m / 2 / 110_574.0
    dlon = bredde_m / 2 / (111_320.0 * math.cos(math.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def wms_url(lat, lon, aar):
    q = {"SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap", "LAYERS": str(aar), "STYLES": "",
         "SRS": "EPSG:4326", "BBOX": ",".join(f"{v:.6f}" for v in bbox(lat, lon)),
         "WIDTH": str(RAA_PX[0]), "HEIGHT": str(RAA_PX[1]), "FORMAT": "image/png"}
    return WMS + "?" + urllib.parse.urlencode(q)


def hent_raa(spot, aar, raa_dir):
    """Rått utsnitt (PNG) for spoten. Gjenbruker fila i raa_dir hvis den finnes (ett kall per spot og år)."""
    f = raa_dir / f"{spot['id']}_{aar}.png"
    if not f.is_file():
        # curl som i tools/lag_minikart.py (Pythons LibreSSL på macOS sliter med enkelte verter); frist på hvert kall
        r = subprocess.run(["curl", "-sS", "--fail", "--max-time", str(FRIST_S), "-A", UA, "-w", "%{content_type}", "-o", str(f) + ".part",
                            wms_url(spot["spot"]["lat"], spot["spot"]["lon"], aar)], capture_output=True, text=True, timeout=FRIST_S + 10)
        tmp = Path(str(f) + ".part")
        data = tmp.read_bytes() if tmp.is_file() else b""
        tmp.unlink(missing_ok=True)
        if r.returncode != 0 or not r.stdout.startswith("image/"):
            raise RuntimeError(f"{spot['id']}: WMS svarte ikke med et bilde ({r.stdout or r.stderr.strip()}): {data[:200]!r}")
        f.write_bytes(data)
        time.sleep(PAUSE_S)
    img = Image.open(io.BytesIO(f.read_bytes())).convert("RGB")
    if img.size != RAA_PX:
        raise RuntimeError(f"{spot['id']}: uventet størrelse {img.size}")
    if np.asarray(img).std() < 2:
        raise RuntimeError(f"{spot['id']}: utsnittet er tomt (ensfarget) - mosaikken dekker ikke stedet")
    return img


def velg_spots(spots, ids, alle):
    """Spots det er lov å lage bilde av: aldri «hemmelig». --alle tar bare påslåtte."""
    lov = [s for s in spots if s.get("status") != "hemmelig"]
    if alle:
        return [s for s in lov if s.get("enabled", True)]
    by_id = {s["id"]: s for s in lov}
    ukjent = [i for i in ids if i not in by_id]
    if ukjent:
        raise SystemExit(f"finner ikke (eller har ikke lov til å lage bilde av) spot: {', '.join(ukjent)}")
    return [by_id[i] for i in ids]


def lag(spot, aar, ut, raa_dir, varianter):
    src = hent_raa(spot, aar, raa_dir)
    filer = []
    for v in varianter:
        kw = VARIANTER[v]
        for tema, stops, maks in (("trykk", TRYKK, kw["maks"][0]), ("lodd", LODD, kw["maks"][1])):
            im = behandle(src, kw["boks"], kw["size"], stops, maks=maks, sigma=kw["sigma"], partikkel=kw["partikkel"])
            f = ut / f"{spot['id']}-{tema}{kw['navn']}.jpg"
            im.save(f, quality=KVALITET[tema], optimize=True)
            filer.append(f)
    return filer


def skriv_kilder(ut, spots, aar):
    """kilder.json: én oppføring per spot med kilde, år, lisens og krediteringen appen skal vise under bildet."""
    f = ut / "kilder.json"
    kilder = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    for s in spots:
        v, so, o, n = bbox(s["spot"]["lat"], s["spot"]["lon"])
        kilder[s["id"]] = {"kilde": f"Satellittdata - Sentinel-2 - Skyfritt opptak Norge {aar} (Kartverket)", "aar": aar,
                           "lisens": LISENS, "lisens_url": LISENS_URL, "kreditering": kredit(aar),
                           "utsnitt": [round(v, 5), round(so, 5), round(o, 5), round(n, 5)],
                           "hentet": dt.date.today().isoformat()}
    f.write_text(json.dumps(dict(sorted(kilder.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def skriv_js(ut, js, hemmelige=()):
    """docs/js/spotbilder.js: hvilke spots som har kornfoto, og krediteringen. Leses av appen (spot.js, skive.js).
    Bare id-er som står i kilder.json, og aldri en hemmelig spot."""
    kilder = json.loads((ut / "kilder.json").read_text(encoding="utf-8"))
    ids = sorted(i for i in kilder if i not in set(hemmelige))
    aar = sorted({kilder[i]["aar"] for i in ids})
    if len(aar) != 1:
        raise SystemExit(f"kilder.json har bilder fra {aar or 'ingen år'} - appen viser én kreditering, lag alle fra samme år")
    data = {"aar": aar[0], "ids": ids, "kredit": kredit(aar[0]), "kort": kredit_kort(aar[0]),
            "lisens": LISENS, "lisens_url": LISENS_URL}   # appen lenker lisensnavnet i krediteringen (CC BY 4.0 punkt 3a)
    js.write_text("// Skrevet av tools/spotbilder.py - ikke rediger for hånd. Hvilke spots som har kornfoto i img/spots/, og krediteringen.\n"
                  f"window.SPOTBILDER = {json.dumps(data, ensure_ascii=False, indent=1)};\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Kornfoto per spot fra Kartverkets skyfrie Sentinel-2-mosaikk (CC BY 4.0)")
    ap.add_argument("spots", nargs="*", help="spot-id-er fra spots.json")
    ap.add_argument("--alle", action="store_true", help="alle påslåtte spots")
    ap.add_argument("--ut", type=Path, default=UT)
    ap.add_argument("--raa", type=Path, default=Path(tempfile.gettempdir()) / "nordsurf-spotbilder")
    ap.add_argument("--aar", type=int, default=AAR)
    ap.add_argument("--varianter", default="header")
    ap.add_argument("--js", action="store_true", help="skriv bare docs/js/spotbilder.js på nytt fra kilder.json")
    a = ap.parse_args()
    alle_spots = json.loads(SPOTS.read_text(encoding="utf-8"))["spots"]
    hemmelige = [s["id"] for s in alle_spots if s.get("status") == "hemmelig"]
    if a.js:
        skriv_js(UT, JS, hemmelige)
        print(f"{JS.relative_to(ROOT)} skrevet")
        return
    if not a.spots and not a.alle:
        ap.error("oppgi spot-id-er eller --alle")
    varianter = [v for v in a.varianter.split(",") if v]
    if any(v not in VARIANTER for v in varianter):
        ap.error(f"ukjent variant (lov: {', '.join(VARIANTER)})")
    spots = velg_spots(alle_spots, a.spots, a.alle)
    a.ut.mkdir(parents=True, exist_ok=True)
    a.raa.mkdir(parents=True, exist_ok=True)
    ferdige, feil = [], []
    for s in spots:
        try:
            for f in lag(s, a.aar, a.ut, a.raa, varianter):
                print(f"{f.name}  {f.stat().st_size // 1024} kB")
            ferdige.append(s)
        except Exception as e:   # én spot som feiler skal ikke stoppe resten; feilen skrives ut og gir exit 1
            feil.append(f"{s['id']}: {e}")
    skriv_kilder(a.ut, ferdige, a.aar)
    if a.ut.resolve() == UT.resolve():
        skriv_js(UT, JS, hemmelige)
    if feil:
        print("FEIL:\n  " + "\n  ".join(feil))
        sys.exit(1)
    print(f"{len(ferdige)} spots. Kreditering: {kredit(a.aar)}")


if __name__ == "__main__":
    main()
