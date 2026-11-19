"""Kornfotoene (tools/spotbilder.py, docs/design/b4/SPEC.md §7): behandlingen, utsnittet, kilden og at hemmelige
spots aldri får bilde. Ingen nett. Trenger numpy og Pillow (som verktøyet), så den kjøres lokalt før commit og
står ikke i .github/workflows/test.yml.

Kjør: python fetcher/test_spotbilder.py"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import spotbilder as sb   # noqa: E402

# 1. rampene: endepunktene og stoppene fra SPEC §7
assert sb.TRYKK == [(0.0, "#1F2A30"), (0.35, "#5C5A53"), (0.7, "#B9B2A4"), (1.0, "#F2EFE8")], sb.TRYKK
assert sb.LODD == [(0.0, "#00131F"), (0.3, "#002941"), (0.9, "#B6DFED"), (1.0, "#F2EFE8")], sb.LODD
for stops in (sb.TRYKK, sb.LODD):
    ender = sb.fargekart(np.array([[0.0, 1.0]], dtype=np.float32), stops)
    assert tuple(ender[0, 0]) == tuple(int(v) for v in sb.hx(stops[0][1])) and tuple(ender[0, 1]) == tuple(int(v) for v in sb.hx(stops[-1][1]))
assert sb.VARIANTER["header"]["maks"] == (0.93, 0.82) and sb.VARIANTER["skive"]["maks"][1] == 1.0
assert all(0.06 <= v["sigma"] <= 0.07 and 1.6 <= v["partikkel"] <= 2.5 for v in sb.VARIANTER.values())

# 2. behandlingen: lik hver gang (fast frø), kornet ligger FØR fargekartet (hver piksel står på rampen), aldri
#    lysere enn «maks», og aldri korall (rødt over grønt og blått)
rng = np.random.default_rng(1)
src = Image.fromarray(rng.integers(0, 255, (sb.RAA_PX[1], sb.RAA_PX[0], 3), dtype=np.uint8))
for navn, v in sb.VARIANTER.items():
    assert v["boks"][0] >= 0 and v["boks"][1] >= 0 and v["boks"][2] <= sb.RAA_PX[0] and v["boks"][3] <= sb.RAA_PX[1], navn
    assert ((v["boks"][0] + v["boks"][2]) / 2, (v["boks"][1] + v["boks"][3]) / 2) == (sb.RAA_PX[0] / 2, sb.RAA_PX[1] / 2), f"{navn}: spoten står ikke i midten"
    for stops, maks in ((sb.TRYKK, v["maks"][0]), (sb.LODD, v["maks"][1])):
        a = np.asarray(sb.behandle(src, v["boks"], v["size"], stops, maks=maks, sigma=v["sigma"], partikkel=v["partikkel"]))
        b = np.asarray(sb.behandle(src, v["boks"], v["size"], stops, maks=maks, sigma=v["sigma"], partikkel=v["partikkel"]))
        assert a.shape == (v["size"][1], v["size"][0], 3) and (a == b).all(), navn
        rampe = sb.fargekart(np.linspace(0, maks, 2048, dtype=np.float32)[None, :], stops)[0].astype(np.int16)
        pix = np.unique(a.reshape(-1, 3), axis=0).astype(np.int16)
        avstand = np.abs(pix[:, None, :] - rampe[None, :, :]).sum(axis=2).min(axis=1)
        assert avstand.max() <= 3, f"{navn}: {int(avstand.max())} fra rampen - kornet er lagt på etter fargekartet?"
        assert not ((pix[:, 0] > pix[:, 1] + 25) & (pix[:, 0] > pix[:, 2] + 25)).any(), f"{navn}: rødlig piksel"
# kornet: null i snitt, sigma som bedt om (innen 25 %), og lavoppløst (naboer henger sammen)
k = sb.korn((400, 600), 0.07, 2.5, 7)
assert abs(float(k.mean())) < 0.01 and 0.035 < float(k.std()) < 0.0875, (float(k.mean()), float(k.std()))
assert float(np.corrcoef(k[:, :-1].ravel(), k[:, 1:].ravel())[0, 1]) > 0.3

# 3. utsnittet: spoten i midten, nord opp, 4:3 i meter
for lat, lon in ((68.2692, 13.5808), (62.9852, 7.1508), (70.9, 28.0)):
    v, s, o, n = sb.bbox(lat, lon)
    assert abs((v + o) / 2 - lon) < 1e-9 and abs((s + n) / 2 - lat) < 1e-9
    bredde = (o - v) * 111_320.0 * math.cos(math.radians(lat)); hoyde = (n - s) * 110_574.0
    assert abs(bredde - 5660) < 1 and abs(hoyde - 4245) < 1, (bredde, hoyde)

# 4. kilden: bare Kartverkets Sentinel-2-mosaikk, med henvisningen metadataene krever
url = sb.wms_url(68.2692, 13.5808, 2025)
assert url.startswith("https://wms.geonorge.no/skwms1/wms.sentinel2?") and "LAYERS=2025" in url and "WIDTH=800" in url and "HEIGHT=600" in url, url
kred = sb.kredit(2025)
assert "Laget av Sentinel-2 (2025) bilder fra Copernicus-programmet til EU, bearbeidet av Kartverket, basert på metoder utviklet fra CESBIO og CNES" in kred
assert "CC BY 4.0" in kred and "Nordsurf" in kred   # lisensen og at bildet er endret
kode = (ROOT / "tools" / "spotbilder.py").read_text(encoding="utf-8")
assert kode.count("https://") == 2 and "norgeibilder" not in kode.lower() and "tiles.maps.eox" not in kode, "bare wms.geonorge.no og lisenslenka er lov"

# 5. hemmelige spots får aldri bilde - verken med --alle eller ved navn
spots = [{"id": "a", "enabled": True}, {"id": "b", "status": "hemmelig", "enabled": True}, {"id": "c", "status": "forelopig", "enabled": False}]
assert [s["id"] for s in sb.velg_spots(spots, [], True)] == ["a"]
assert [s["id"] for s in sb.velg_spots(spots, ["c", "a"], False)] == ["c", "a"]
for ids in (["b"], ["a", "finnes-ikke"]):
    try:
        sb.velg_spots(spots, ids, False)
        raise AssertionError(f"{ids} skulle vært nektet")
    except SystemExit:
        pass

# 6. docs/js/spotbilder.js: bare id-er fra kilder.json, aldri en hemmelig, og begge krediteringene
import json, tempfile   # noqa: E402
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    (d / "kilder.json").write_text(json.dumps({"a": {"aar": 2025}, "b": {"aar": 2025}}), encoding="utf-8")
    sb.skriv_js(d, d / "spotbilder.js", hemmelige=["b"])
    js = (d / "spotbilder.js").read_text(encoding="utf-8")
    data = json.loads(js[js.index("{"):js.rindex("}") + 1])
    assert data["ids"] == ["a"] and data["kredit"] == sb.kredit(2025) and data["kort"] == "Sentinel-2 (2025), Copernicus/Kartverket · CC BY 4.0", data
    assert data["lisens"] == "CC BY 4.0" and data["lisens"] in data["kredit"] and data["lisens_url"] == sb.LISENS_URL, data   # lenka appen viser
# det som ligger i docs/ stemmer med kilder.json, og hvert bilde appen ber om, finnes
js_fil, kilder_fil = ROOT / "docs" / "js" / "spotbilder.js", ROOT / "docs" / "img" / "spots" / "kilder.json"
if js_fil.is_file():
    js = js_fil.read_text(encoding="utf-8")
    data = json.loads(js[js.index("{"):js.rindex("}") + 1])
    assert data["ids"] == sorted(json.loads(kilder_fil.read_text(encoding="utf-8"))), "kjør python3 tools/spotbilder.py --js"
    hemmelige = {s["id"] for s in json.loads((ROOT / "spots.json").read_text(encoding="utf-8"))["spots"] if s.get("status") == "hemmelig"}
    assert not hemmelige & set(data["ids"])
    for i in data["ids"]:
        for navn in (f"{i}-trykk.jpg", f"{i}-lodd.jpg", f"{i}-trykk-skive.jpg", f"{i}-lodd-skive.jpg"):
            assert (kilder_fil.parent / navn).is_file(), f"mangler {navn}"

print("OK: test_spotbilder (ramper, korn før fargekart, utsnitt, kilde og kreditering, hemmelige nektes)")
