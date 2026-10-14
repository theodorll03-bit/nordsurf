"""S2: de delte datafilene (fetcher/publish.py) - ren omforming av varselet.

Sjekker på den faste testfila fetcher/fixtures/forecast.json (ekte varsel
14.10.2026 kl. 19Z - fast, så testen ikke avhenger av dagens data):

1. Oversikten har alle spots (unntatt «hemmelig») med ALLE spotfeltene
   uendret, og timene i forsidens rekkevidde med bare HOME_HOUR_FIELDS -
   verdiene byte for byte like varselets.
2. Detaljfila per spot har ALLE timene med alle felt unntatt DETAIL_EXCLUDE,
   verdiene uendret, og samme timer i samme rekkefølge som oversikten
   (indeks i i oversikten = indeks i i detaljfila).
3. Et felt som mangler i varselet, mangler fortsatt (aldri 0/None lagt til -
   grunnregelen).
4. docs/js leser ingen av feltene i DETAIL_EXCLUDE (ellers ville appen savnet
   dem stille i spotarket).
5. «hemmelig» publiseres aldri - verken i oversikten, som detaljfil eller i
   forecast.json (artifacten i et offentlig repo kan lastes ned av alle).
8. Alle filene har samme «run» (fingeravtrykk av varselet), og det endres når
   varselet endres - appen blander aldri to kjøringer i samme time.
6. write() bytter inn filene atomisk: ingen rester av den midlertidige
   mappa, gamle detaljfiler for spots som er borte, fjernes.
7. Oversikten er mye mindre enn hele varselet (det er hele poenget).

Kjør: python fetcher/test_publish.py   (ingen nett, under 5 s)."""
import copy
import gzip
import json
import re
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))
import publish  # noqa: E402

FIXTURE = ROOT / "fetcher" / "fixtures" / "forecast.json"


def t_of(h):
    return datetime.fromisoformat(h["t"].replace("Z", "+00:00"))


def main():
    fc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    before = copy.deepcopy(fc)
    overview, details = publish.split(fc)
    assert fc == before, "split() skal ikke endre varselet"

    # 1. oversikten
    assert [s["id"] for s in overview["spots"]] == [s["id"] for s in fc["spots"]], "alle spots i samme rekkefølge"
    assert overview["generated"] == fc["generated"] and overview.get("notify") == fc.get("notify")
    n_home = 0
    for o, s in zip(overview["spots"], fc["spots"]):
        assert {k: v for k, v in o.items() if k != "hours"} == {k: v for k, v in s.items() if k != "hours"}, f"{s['id']}: spotfeltene skal være uendret"
        horizon = t_of(s["hours"][0]) + timedelta(days=publish.HOME_DAYS)
        want = [h for h in s["hours"] if t_of(h) <= horizon]
        assert len(o["hours"]) == len(want), f"{s['id']}: {len(o['hours'])} timer i oversikten, forventet {len(want)}"
        for oh, h in zip(o["hours"], want):
            assert set(oh) <= set(publish.HOME_HOUR_FIELDS), f"{s['id']} {h['t']}: ekstra felt i oversikten {set(oh) - set(publish.HOME_HOUR_FIELDS)}"
            assert oh == {k: h[k] for k in publish.HOME_HOUR_FIELDS if k in h}, f"{s['id']} {h['t']}: verdiene i oversikten skal være varselets"
        n_home = len(o["hours"])
    # forsidens glidebryter (7 døgn) får plass i oversikten
    s0 = fc["spots"][0]["hours"]
    max_idx = max(i for i, h in enumerate(s0) if t_of(h) - t_of(s0[0]) <= timedelta(days=7))
    assert n_home > max_idx, f"oversikten ({n_home} timer) skal dekke glidebryteren (til indeks {max_idx})"
    print(f"1: oversikten har {len(overview['spots'])} spots, spotfeltene uendret, {n_home} timer per spot med {len(publish.HOME_HOUR_FIELDS)} felt (glidebryteren til indeks {max_idx}) - OK")

    # 2. detaljfilene
    for s in fc["spots"]:
        d = details[s["id"]]
        assert d["generated"] == fc["generated"] and d["id"] == s["id"] and d["run"] == overview["run"]
        assert len(d["hours"]) == len(s["hours"]), f"{s['id']}: alle timene i detaljfila"
        for dh, h in zip(d["hours"], s["hours"]):
            assert dh == {k: v for k, v in h.items() if k not in publish.DETAIL_EXCLUDE}, f"{s['id']} {h['t']}: detaljfila skal ha alle felt unntatt de utelatte"
        o = next(x for x in overview["spots"] if x["id"] == s["id"])
        assert [h["t"] for h in o["hours"]] == [h["t"] for h in d["hours"][:len(o["hours"])]], f"{s['id']}: samme timer i samme rekkefølge"
    print(f"2: {len(details)} detaljfiler med alle {len(fc['spots'][0]['hours'])} timer, alle felt unntatt {len(publish.DETAIL_EXCLUDE)} utelatte, samme indekser som oversikten - OK")

    # 3. et felt som mangler, mangler fortsatt
    fc3 = copy.deepcopy(fc)
    h3 = fc3["spots"][0]["hours"][2]
    for k in ("surf_height", "stars", "light", "energy_swell_kj"):
        h3.pop(k, None)
    ov3, de3 = publish.split(fc3)
    for k in ("surf_height", "stars", "light", "energy_swell_kj"):
        assert k not in ov3["spots"][0]["hours"][2] and k not in de3[fc3["spots"][0]["id"]]["hours"][2], f"{k} mangler i varselet og skal mangle i filene (ikke 0/None)"
    print("3: felt som mangler i varselet, mangler fortsatt i oversikten og detaljfila (grunnregelen) - OK")

    # 4. docs/js leser ingen utelatte felt
    src = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "docs" / "js").glob("*.js")))
    read = [k for k in publish.DETAIL_EXCLUDE if re.search(r"(\.|\[\s*[\"'])" + re.escape(k) + r"\b", src) or re.search(r"[\"']" + re.escape(k) + r"[\"']", src)]
    assert not read, f"docs/js leser felt som ikke publiseres i detaljfila: {read} - fjern dem fra publish.DETAIL_EXCLUDE"
    keys = set()
    for s in fc["spots"]:
        for h in s["hours"]:
            keys |= set(h)
    print(f"4: docs/js leser ingen av de {len(publish.DETAIL_EXCLUDE)} utelatte feltene ({len(keys) - len(publish.DETAIL_EXCLUDE)} av {len(keys)} timefelt publiseres) - OK")

    # 5. hemmelig publiseres aldri
    fc5 = copy.deepcopy(fc)
    secret = copy.deepcopy(fc5["spots"][1]); secret["id"] = "hemmelig_test"; secret["name"] = "Hemmelig"; secret["status"] = "hemmelig"
    fc5["spots"].append(secret)
    with tempfile.TemporaryDirectory() as tmp:
        ov5, de5 = publish.write(fc5, tmp)
        assert "hemmelig_test" not in [s["id"] for s in ov5["spots"]] and "hemmelig_test" not in de5
        assert not (Path(tmp) / "spots" / "hemmelig_test.json").exists()
        assert "Hemmelig" not in (Path(tmp) / "oversikt.json").read_text(encoding="utf-8")
        pub = json.loads((Path(tmp) / "forecast.json").read_text(encoding="utf-8"))
        assert "hemmelig_test" not in [s["id"] for s in pub["spots"]] and len(pub["spots"]) == len(fc["spots"]), "forecast.json skal være uten hemmelige spots"
    print("5: en spot med status «hemmelig» står verken i oversikten, som detaljfil eller i forecast.json - OK")

    # 6. atomisk innbytting, og gamle detaljfiler fjernes
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "spots").mkdir()
        (tmp / "spots" / "gammel_spot.json").write_text("{}", encoding="utf-8")
        publish.write(fc, tmp)
        files = sorted(p.name for p in (tmp / "spots").iterdir())
        assert files == sorted(f"{s['id']}.json" for s in fc["spots"]), f"detaljfilene etter innbytting: {files}"
        assert not (tmp / ".publish-tmp").exists(), "den midlertidige mappa skal være borte"
        ov = json.loads((tmp / "oversikt.json").read_text(encoding="utf-8"))
        assert ov == json.loads(json.dumps(overview)), "oversikt.json på disk = split()"
        assert (tmp / "oversikt.json").stat().st_mtime >= max(p.stat().st_mtime for p in (tmp / "spots").iterdir()), "oversikten skrives sist"
        assert (tmp / "forecast.json").read_bytes() == FIXTURE.read_bytes(), "uten hemmelige spots er forecast.json byte for byte den henteren skrev"
        raw_ov, raw_fc = (tmp / "oversikt.json").read_bytes(), FIXTURE.read_bytes()
        gz_ov, gz_fc = len(gzip.compress(raw_ov)), len(gzip.compress(raw_fc))
        gz_det = [len(gzip.compress(p.read_bytes())) for p in (tmp / "spots").iterdir()]
    print("6: filene byttes inn atomisk, oversikten sist, gamle detaljfiler fjernes, forecast.json byte for byte henterens - OK")

    # 7. størrelsen
    assert gz_ov * 3 < gz_fc, f"oversikten ({gz_ov // 1024} KiB gzip) skal være langt mindre enn hele varselet ({gz_fc // 1024} KiB)"
    print(f"7: åpning laster {gz_ov // 1024} KiB gzip ({len(raw_ov) // 1024} KiB rå) i stedet for {gz_fc // 1024} KiB ({len(raw_fc) // 1024} KiB rå); "
          f"en spot {sum(gz_det) // len(gz_det) // 1024} KiB gzip når den åpnes - OK")
    # 8. samme «run» i alle filene, og det følger innholdet
    fc8 = copy.deepcopy(fc)
    ov_same, _ = publish.split(copy.deepcopy(fc))
    fc8["spots"][0]["hours"][3]["stars"] = (fc8["spots"][0]["hours"][3].get("stars") or 0) + 1
    ov8, de8 = publish.split(fc8)
    assert ov_same["run"] == overview["run"], "samme varsel gir samme run"
    assert ov8["run"] != overview["run"] and all(d["run"] == ov8["run"] for d in de8.values()), "et annet varsel gir et annet run, likt i alle filene"
    assert ov8["generated"] == overview["generated"], "testen dekker nettopp tilfellet der generated er likt (to kjøringer i samme time)"
    print(f"8: «run» ({overview['run']}) er likt i oversikten og alle detaljfilene og endres når varselet endres (også med samme «generated») - OK")
    print("Alle tester ok")


if __name__ == "__main__":
    main()
