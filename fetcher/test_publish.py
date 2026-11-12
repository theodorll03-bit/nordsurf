"""S2 (14.10.2026) og Tillegg 2 (15.10.2026): de delte datafilene.

oversikt-2: docs/data/oversikt.json har per spot bare meta (publish.META_FIELDS), «naa»
(nå-timen og de tre neste, kompakte) og «dager» (dagssammendrag for 7 døgn) - ingen timer.
Regelen for «beste time» (flest stjerner, ved likhet høyest surf_height, bare timer der lyset
ikke er «mørkt», ukjent lys teller ikke) ligger i publish.best_hour() og testes her, så appen
og forsiden alltid er enige (appen regner den ikke selv lenger for oversikten).
spots/<id>.json har spotens hele meta og alle timene unntatt DETAIL_EXCLUDE.

Mål: oversikt.json under 60 KiB gzip ved 100 spots (syntetiske, fetcher/synthetic_spots.py).
Kjør: python fetcher/test_publish.py (ingen nett, under 10 s)."""
import copy
import datetime as dt
import gzip
import json
import re
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetcher"))
import publish  # noqa: E402
import synthetic_spots  # noqa: E402

FIXTURE = ROOT / "fetcher" / "fixtures" / "forecast.json"
OSLO = ZoneInfo("Europe/Oslo")


def t_of(h):
    return dt.datetime.fromisoformat(h["t"].replace("Z", "+00:00"))


def main():
    fc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    before = copy.deepcopy(fc)
    overview, details = publish.split(fc)
    assert fc == before, "split() skal ikke endre varselet"
    now = t_of({"t": fc["generated"]})

    # 1. oversikten: meta, nå-timene og dagene - ingen timer
    assert overview["format"] == "oversikt-2" and [s["id"] for s in overview["spots"]] == [s["id"] for s in fc["spots"]]
    for o, s in zip(overview["spots"], fc["spots"]):
        assert "hours" not in o, f"{s['id']}: oversikten skal ikke ha timer"
        assert set(o) - {"naa", "dager"} <= set(publish.META_FIELDS), f"{s['id']}: ekstra meta i oversikten {set(o) - {'naa', 'dager'} - set(publish.META_FIELDS)}"
        if isinstance(s.get("calibration"), dict):
            assert "transfer_used" in o["calibration"] and "exposure_curve" not in o["calibration"], "kalibreringen uten kurven i oversikten"
        assert o.get("local_rules") == s.get("local_rules")
        assert o["region"] and o["spot"]["lat"] and o["name"] == s["name"]
        # nå-timen = den første timen som ikke er over ved «generated», og de tre neste (seks etter kveldens siste kjøring)
        want = [h for h in s["hours"] if t_of(h) + dt.timedelta(hours=1) > now][:publish.naa_hours(now)]
        assert [h["t"] for h in o["naa"]] == [h["t"] for h in want], f"{s['id']}: naa {[h['t'] for h in o['naa']]}"
        for oh, h in zip(o["naa"], want):
            assert set(oh) <= set(publish.NAA_FIELDS) | {"bw_height"}, f"{s['id']}: ekstra felt {set(oh) - set(publish.NAA_FIELDS)}"
            assert oh["stars"] == h["stars"] and oh.get("low_reason") == h.get("low_reason") and oh["light"] == h["light"]
            if h.get("surf_height") is not None:
                assert abs(oh["surf_height"] - h["surf_height"]) < 0.006, "surfehøyden avrundet til 2 desimaler, ikke endret"
            assert ("bw_height" in oh) == (h.get("low_reason") in publish.BW_WHEN and h.get("bw_height") is not None), "bw_height bare der regel (c) krever det"
            assert "daylight" not in oh or oh.get("light") is None
        assert all(("local_rules" in oh) == (h.get("local_rules") is not None) for oh, h in zip(o["naa"], want)), "local_rules følger nå-timen når den finnes (ordet ved 0 stjerner)"
        assert len(o["dager"]) == publish.SUMMARY_DAYS and o["dager"][0]["d"] == now.astimezone(OSLO).date().isoformat()
    print(f"1: oversikt-2 med {len(overview['spots'])} spots: meta ({len(publish.META_FIELDS)} felt), {publish.naa_hours(now)} nå-timer og {publish.SUMMARY_DAYS} dager per spot, ingen timer - OK")

    # 1b. fotavtrykk 10.11.2026: «Hent varsel» kl. 03:17-21:17 UTC hver 3. time, ikke kl. 00:17 - nå-timene dekker
    # alltid fram til og med timen den neste planlagte kjøringen starter i (klokkas time finnes også om natta)
    U = lambda time, dag=10: dt.datetime(2026, 11, dag, time, tzinfo=dt.timezone.utc)
    assert [publish.naa_hours(U(h)) for h in (3, 6, 9, 12, 15, 18)] == [4] * 6, "om dagen: nå-timen + de tre neste"
    assert publish.naa_hours(U(21)) == 7, "kveldens siste kjøring: 21, 22, 23, 00, 01, 02 og 03 UTC"
    assert [publish.naa_hours(U(h)) for h in (22, 23, 0, 1, 2)] == [6, 5, 4, 4, 4], "manuell kjøring om natta: fram til kl. 03, aldri færre enn 4"
    assert publish.naa_hours(dt.datetime(2026, 11, 10, 22, tzinfo=OSLO)) == 7, "regnes i UTC, ikke i lokal tid (22 norsk vintertid = 21 UTC)"
    natt = [{"t": (U(21) + dt.timedelta(hours=i)).isoformat(), "stars": 0, "surf_height": 0.5, "light": "mørkt"} for i in range(-2, 30)]
    naa_natt = publish.summarise(natt, U(21))["naa"]
    assert [h["t"] for h in naa_natt] == [(U(21) + dt.timedelta(hours=i)).isoformat() for i in range(7)]
    for klokka in (U(21) + dt.timedelta(minutes=30), U(0, 11), U(3, 11) + dt.timedelta(minutes=59)):
        assert any(t_of(h) <= klokka < t_of(h) + dt.timedelta(hours=1) for h in naa_natt), f"klokkas time mangler kl. {klokka:%H:%M} UTC"
    assert len(publish.summarise(natt, U(18))["naa"]) == 4
    print("1b: nå-timene dekker natthullet (7 timer etter kjøringen kl. 21 UTC, ellers 4) - OK")

    # 2. regelen for beste time (samme som appen brukte: flest stjerner, likt -> høyest surf, bare lys, ukjent lys teller ikke)
    H = lambda t, st, surf, light="dag", **k: dict({"t": t, "stars": st, "surf_height": surf, "light": light}, **k)
    b, st = publish.best_hour([H("a", 2, 1.0), H("b", 3, 0.8), H("c", 3, 1.2), H("d", 4, 2.0, light="mørkt")])
    assert b["t"] == "c" and st == "ok", (b, st)                       # 3 stjerner, høyest surf; 4 i mørket teller ikke
    b, st = publish.best_hour([H("a", 0, 0.0), H("b", 0, 0.2)])
    assert b["t"] == "b" and st == "ok", "alle 0: beste er den med høyest surf (ekte 0 = kjent)"
    b, st = publish.best_hour([H("a", 0, None), H("b", 1, 0.9, light="skumring")])
    assert b["t"] == "b", "skumring teller som lys; en lys time uten tall gjør ikke dagen «miss» når det finnes en time med stjerner"
    b, st = publish.best_hour([H("a", 0, None), H("b", 0, 0.1)])
    assert b is None and st == "miss", "lys time uten tall og ingen stjerner -> miss (aldri 0)"
    b, st = publish.best_hour([H("a", 3, 1.0, light=None), H("b", 0, 0.0)])
    assert b is None and st == "miss", "ukjent lys med stjerner -> miss, ikke dagslys"
    b, st = publish.best_hour([H("a", 3, 1.0, light="mørkt"), H("b", 2, 1.0, light="mørkt")])
    assert b is None and st == "dark"
    b, st = publish.best_hour([H("a", 0, 0.1, light=None), H("b", 0, 0.2, light=None)])
    assert b is None and st == "miss", "bare ukjent lys hele dagen er «mangler», ikke «mørkt»"
    d2 = publish.day_summary([H("a", 3, 1.0), H("b", 3, 1.2), H("c", 3, 1.1), H("d", 2, 0.9)])
    assert d2["h"]["t"] == "b" and d2["start"] == "a" and d2["slutt"] == "c", "vinduet går både bakover og fremover fra beste time"
    d = publish.day_summary([H("a", 1, 0.0), H("b", 2, 1.0, surf_height_sets=1.3), H("c", 2, 0.9, surf_height_sets=1.1), H("d", 1, 1.4, surf_height_sets=1.8), H("e", 3, 0.5, light="mørkt")])
    assert d["status"] == "ok" and d["h"]["t"] == "b" and d["slutt"] == "c" and d["lo"] == 0.9 and d["hi"] == 1.8, d
    d0 = publish.day_summary([H("a", 0, 0.0), H("b", 0, 0.0)])
    assert d0["status"] == "ok" and "lo" not in d0 and "hi" not in d0, "alle timene 0: ingen spenn (aldri «0,0–x»)"
    # samme regel som dayBest i ui.js hadde: sjekk mot testfila for alle spots og dager
    for o, s in zip(overview["spots"], fc["spots"]):
        for day in o["dager"]:
            hs = [h for h in s["hours"] if t_of(h).astimezone(OSLO).date().isoformat() == day["d"] and t_of(h) + dt.timedelta(hours=1) > now]
            b, st = publish.best_hour(hs) if hs else (None, "miss")
            if day["status"] == "over":   # dagens lys er over (PR #12 punkt c): bare i dag, ingen lyse timer igjen, lys i morgen
                assert day["d"] == o["dager"][0]["d"] and st == "dark" and o["dager"][1]["status"] != "dark", (s["id"], day)
                continue
            assert day["status"] == st and (b is None or day["h"]["t"] == b["t"]), (s["id"], day["d"], st, b and b["t"])
    over = sum(1 for o in overview["spots"] if o["dager"][0]["status"] == "over")
    assert over == len(overview["spots"]), f"varselet starter kl. 21 norsk tid 14.10 - dagens lys er over for alle spots ({over})"
    # mørketid: ingen lys i dag eller i morgen → «dark», ikke «over»
    dark_fc = {**fc, "spots": [{**fc["spots"][0], "hours": [{**h, "light": "mørkt", "daylight": False} for h in fc["spots"][0]["hours"]]}]}
    d0dark = publish.summarise(dark_fc["spots"][0]["hours"], now)["dager"][0]
    assert d0dark["status"] == "dark", d0dark
    # hull eller ukjent lys resten av dagen er «miss», aldri «over» (grunnregelen)
    unk_hours = [{**h, "light": None, "daylight": None} if t_of(h).astimezone(OSLO).date() == now.astimezone(OSLO).date() else h for h in fc["spots"][0]["hours"]]
    assert publish.summarise(unk_hours, now)["dager"][0]["status"] == "miss"
    gap_hours = [h for h in fc["spots"][0]["hours"] if t_of(h).astimezone(OSLO).date() != now.astimezone(OSLO).date()]
    assert publish.summarise(gap_hours, now)["dager"][0]["status"] == "miss"
    print("2b: dagens lys er over → «over» (alle spots kl. 21), mørketid → «dark» - OK")
    print("2: best_hour()/day_summary() - flest stjerner, likt -> høyest surf, bare lys, ukjent lys teller ikke, miss/dark, spenn bare fra timer over 0 - OK")

    # 3. detaljfilene: hele meta + alle timene
    for s in fc["spots"]:
        d = details[s["id"]]
        assert d["format"] == "spot-2" and d["generated"] == fc["generated"] and d["id"] == s["id"] and d["run"] == overview["run"]
        assert d["swell_window"] == s["swell_window"] and d.get("tide_events") == s.get("tide_events") and d["ideal_height"] == s["ideal_height"], "spotens meta ligger i detaljfila"
        assert len(d["hours"]) == len(s["hours"])
        for dh, h in zip(d["hours"], s["hours"]):
            assert dh == {k: v for k, v in h.items() if k not in publish.DETAIL_EXCLUDE}
    print(f"3: {len(details)} detaljfiler med hele meta og alle {len(fc['spots'][0]['hours'])} timer unntatt {len(publish.DETAIL_EXCLUDE)} utelatte - OK")

    # 4. et felt som mangler, mangler fortsatt (aldri 0/None lagt til)
    fc4 = copy.deepcopy(fc)
    h4 = fc4["spots"][0]["hours"]
    first_now = next(i for i, h in enumerate(h4) if t_of(h) + dt.timedelta(hours=1) > now)
    for k in ("surf_height", "energy_swell_kj", "wind_speed"):
        h4[first_now].pop(k, None)
    ov4, de4 = publish.split(fc4)
    for k in ("surf_height", "energy_swell_kj", "wind_speed"):
        assert k not in ov4["spots"][0]["naa"][0] and k not in de4[fc4["spots"][0]["id"]]["hours"][first_now], f"{k} mangler og skal mangle"
    print("4: felt som mangler i varselet, mangler i nå-timen og detaljfila (grunnregelen) - OK")

    # 5. docs/js leser ingen utelatte felt
    src = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "docs" / "js").glob("*.js")))
    read = [k for k in publish.DETAIL_EXCLUDE if re.search(r"(\.|\[\s*[\"'])" + re.escape(k) + r"\b", src) or re.search(r"[\"']" + re.escape(k) + r"[\"']", src)]
    assert not read, f"docs/js leser felt som ikke publiseres i detaljfila: {read}"
    print(f"5: docs/js leser ingen av de {len(publish.DETAIL_EXCLUDE)} utelatte feltene - OK")

    # 6. hemmelig publiseres aldri
    fc6 = copy.deepcopy(fc)
    secret = copy.deepcopy(fc6["spots"][1]); secret["id"] = "hemmelig_test"; secret["name"] = "Hemmelig"; secret["status"] = "hemmelig"
    fc6["spots"].append(secret)
    with tempfile.TemporaryDirectory() as tmp:
        ov6, de6 = publish.write(fc6, tmp)
        assert "hemmelig_test" not in [s["id"] for s in ov6["spots"]] and "hemmelig_test" not in de6
        assert not (Path(tmp) / "spots" / "hemmelig_test.json").exists()
        assert "Hemmelig" not in (Path(tmp) / "oversikt.json").read_text(encoding="utf-8")
        pub = json.loads((Path(tmp) / "forecast.json").read_text(encoding="utf-8"))
        assert "hemmelig_test" not in [s["id"] for s in pub["spots"]] and len(pub["spots"]) == len(fc["spots"])
    print("6: «hemmelig» står verken i oversikten, som detaljfil eller i forecast.json - OK")

    # 7. atomisk innbytting, gamle detaljfiler fjernes, forecast.json byte for byte
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "spots").mkdir()
        (tmp / "spots" / "gammel_spot.json").write_text("{}", encoding="utf-8")
        publish.write(fc, tmp)
        files = sorted(p.name for p in (tmp / "spots").iterdir())
        assert files == sorted(f"{s['id']}.json" for s in fc["spots"]), files
        assert not (tmp / ".publish-tmp").exists()
        ov = json.loads((tmp / "oversikt.json").read_text(encoding="utf-8"))
        assert ov == json.loads(json.dumps(overview))
        assert (tmp / "forecast.json").read_bytes() == FIXTURE.read_bytes()
        raw_ov, raw_fc = (tmp / "oversikt.json").read_bytes(), FIXTURE.read_bytes()
        gz_ov, gz_fc = len(gzip.compress(raw_ov)), len(gzip.compress(raw_fc))
        gz_det = [len(gzip.compress(p.read_bytes())) for p in (tmp / "spots").iterdir()]
    print(f"7: filene byttes inn atomisk; åpning laster {gz_ov / 1024:.1f} KiB gzip ({len(raw_ov) // 1024} KiB rå) i stedet for {gz_fc // 1024} KiB; en spot {sum(gz_det) // len(gz_det) // 1024} KiB gzip - OK")

    # 8. samme «run» i alle filene, og det følger innholdet
    ov_same, _ = publish.split(copy.deepcopy(fc))
    fc8 = copy.deepcopy(fc); fc8["spots"][0]["hours"][3]["stars"] = (fc8["spots"][0]["hours"][3].get("stars") or 0) + 1
    ov8, de8 = publish.split(fc8)
    assert ov_same["run"] == overview["run"] and ov8["run"] != overview["run"] and all(d["run"] == ov8["run"] for d in de8.values())
    print(f"8: «run» ({overview['run']}) er likt i alle filene og endres når varselet endres - OK")

    # 9. regioner: navn og rekkefølge fra spots.json, utsnitt rundt spotene med margin
    regs = [r["name"] for r in overview["regions"]]
    assert regs == ["Troms", "Lofoten", "Møre og Romsdal"], regs
    tr = next(r for r in overview["regions"] if r["name"] == "Troms")
    assert tr["n"] == 6 and tr["extent"][0] < 69.49 and tr["extent"][2] > 69.95 and tr["extent"][1] < 17.26 and tr["extent"][3] > 20.22, tr
    assert all(s["region"] in regs for s in overview["spots"]) and next(s for s in overview["spots"] if s["id"] == "unstad").get("aliases") == ["Unstadbukta"]
    print(f"9: {len(regs)} regioner i spots.json sin rekkefølge med utsnitt og antall; region/aliases hentet fra spots.json for varsel uten dem - OK")

    # 10. 100 syntetiske spots langs kysten: oversikten under 60 KiB gzip
    big, regs_cfg = synthetic_spots.make(fc, 100)
    ov100, de100 = publish.split(big, regions_cfg=regs_cfg)
    raw100 = json.dumps(ov100, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    gz100 = len(gzip.compress(raw100))
    assert len(ov100["spots"]) == 100 and len(de100) == 100 and len(ov100["regions"]) >= 8
    assert gz100 < 60 * 1024, f"oversikten med 100 spots er {gz100 / 1024:.1f} KiB gzip (grense 60)"
    print(f"10: 100 syntetiske spots i {len(ov100['regions'])} regioner: oversikt.json {gz100 / 1024:.1f} KiB gzip ({len(raw100) // 1024} KiB rå) - under 60 KiB - OK")

    # 11. tidevannskortets foretrukne vannstand (Theodor 16.10.2026): samme regel og terskler som ratingen
    import math
    import tide as tidemod
    assert details["farstadsanden"]["tide_regel"]["prefer"] == ["lav", "middels"] and details["unstad"]["tide_regel"] is None
    tr = publish.tide_terskler()
    t0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    ev = [{"time": t0.isoformat(), "type": "fjære"}, {"time": (t0 + dt.timedelta(hours=6)).isoformat(), "type": "flo"}]
    for k in range(1, 360):   # hvert minutt fra fjære til flo: nivået mot tersklene gir samme ord som tide.state_at
        lv = (1 - math.cos(math.pi * k / 360)) / 2
        want = tidemod.state_at(ev, t0 + dt.timedelta(minutes=k))["state"]
        got = "lav" if lv < tr["lav_maks"] - 1e-4 else "høy" if lv > tr["hoy_min"] + 1e-4 else "middels" if tr["lav_maks"] + 1e-4 < lv < tr["hoy_min"] - 1e-4 else want
        assert got == want, (k, lv, got, want, tr)
    print(f"11: tide_regel i detaljfila (Farstadsanden lav+middels, Unstad ingen) med tersklene fra tide.state_at {tr} - OK")
    print("Alle tester ok")


if __name__ == "__main__":
    main()
