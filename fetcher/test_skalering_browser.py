"""Tillegg 2 (Theodor 15.10.2026): appen skal tåle 100+ spots. Nettlesertest med 100 syntetiske
spots spredt langs hele kysten (fetcher/synthetic_spots.py på testfila fetcher/fixtures/forecast.json),
publisert som oversikt-2 + detaljfiler (fetcher/publish.py), servert slik appen får dem, fast klokke:

1. oversikt.json under 60 KiB gzip ved 100 spots (måles på det som faktisk serveres);
2. Hjem (mobil og PC), søk på «a», Utforsk (hele kartet og én region) og nett-tabellen rendres
   uten JavaScript-feil - skjermbilder i docs/design/skalering/etter/;
3. ingen overlappende merkelapper på kartet (bounding boxes for .mk-pill og klynger);
4. Hjem laster bare oversikt.json (ingen spots/<id>.json før en spot åpnes); å åpne en spot laster
   nøyaktig én detaljfil;
5. søk på «a» grupperer per region og viser maks 20 før «Vis flere»;
6. «Beste økt» gjelder bare valgt region (Innstillinger -> Område, standard Troms), aldri alle 100;
7. første visning av Hjem under 1,5 s på simulert 4G (CDP: 9 Mbit/s ned, 150 ms latens) - målt fra
   navigasjonsstart til #bestKort er synlig;
8. nett-tabellen: regionfilter og «Vis alle» per gruppe, overskriftsraden står fast (sticky).

Tidsgrenser (CLAUDE.md): hvert Playwright-steg maks 15 s, hele fila maks 5 minutter (hardkill),
testserveren stoppes uansett utfall. Kjør: python fetcher/test_skalering_browser.py"""
import datetime as dt
import gzip
import http.server
import json
import os
import socket
import sys
import threading
import time
from functools import partial
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SHOT_DIR = DOCS / "design" / "skalering" / "etter"
SHOT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "fetcher"))
import publish  # noqa: E402
import testserver  # noqa: E402
import synthetic_spots  # noqa: E402

ELEMENT_TIMEOUT_MS = 15_000
FILE_TIMEOUT_S = 300
FIXTURE = ROOT / "fetcher" / "fixtures" / "forecast.json"
FORECAST = json.loads(FIXTURE.read_text(encoding="utf-8"))
T0 = (dt.datetime.fromisoformat(FORECAST["generated"].replace("Z", "+00:00")) + dt.timedelta(minutes=70)).astimezone(dt.timezone.utc)
N_SPOTS = 100


def _watchdog():
    def _kill():
        print(f"TIDSAVBRUDD: test_skalering_browser.py brukte over {FILE_TIMEOUT_S}s - avbrutt (se CLAUDE.md).", file=sys.stderr, flush=True)
        os._exit(124)
    t = threading.Timer(FILE_TIMEOUT_S, _kill); t.daemon = True; t.start(); return t


def serve():
    # S3: med HTTP Range (206) som GitHub Pages - PMTiles-kartet trenger det (fetcher/testserver.py)
    return testserver.serve(DOCS)


def main():
    watchdog = _watchdog()
    srv, port = serve()
    big, regions_cfg = synthetic_spots.make(FORECAST, N_SPOTS)
    # ROADMAP K del C.4: dagens «Beste økt» i Troms (test078) blir en ny, foreløpig spot, og test079 får et
    # surfeforbud som gjelder nå (1.10-31.3) - begge skal få merkelapp og holdes utenfor «Beste økt»
    by_id = {s["id"]: s for s in big["spots"]}
    by_id["test078"].update(status="forelopig", forelopig_fra=T0.date().isoformat())
    by_id["test079"]["restriksjoner"] = [{"type": "surfeforbud", "fra": "10-01", "til": "03-31", "gjelder": "sjø"}]
    overview, details = publish.split(big, regions_cfg=regions_cfg)
    OV_BODY = json.dumps(overview, ensure_ascii=False, separators=(",", ":"))
    DET_BODY = {sid: json.dumps(d, ensure_ascii=False, separators=(",", ":")) for sid, d in details.items()}
    gz = len(gzip.compress(OV_BODY.encode("utf-8")))
    assert gz < 60 * 1024, f"oversikt.json med {N_SPOTS} spots er {gz / 1024:.1f} KiB gzip"
    print(f"1: oversikt.json med {N_SPOTS} spots i {len(overview['regions'])} regioner: {gz / 1024:.1f} KiB gzip ({len(OV_BODY) // 1024} KiB rå) - OK")
    errors = []
    try:
        with sync_playwright() as p:
            exe = os.environ.get("NORDSURF_CHROMIUM")
            nb_env = {**os.environ, "LANG": "nb_NO.UTF-8", "LANGUAGE": "nb_NO", "LC_ALL": "nb_NO.UTF-8"}
            browser = p.chromium.launch(args=["--lang=nb-NO", *testserver.WEBGL_ARGS], env=nb_env, **({"executable_path": exe} if exe else {}))
            for label, vp in (("mobil", (390, 844)), ("pc", (1440, 900))):
                mobile = vp[0] < 900
                ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]}, color_scheme="light", locale="nb-NO", timezone_id="Europe/Oslo",
                                          device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile)
                page = ctx.new_page(); page.set_default_timeout(ELEMENT_TIMEOUT_MS)
                page.clock.set_fixed_time(T0)
                page.on("pageerror", lambda e, label=label: errors.append(f"{label}: {e}"))
                page.on("console", lambda m, label=label: errors.append(f"{label} console: {m.text}") if m.type == "error" and "ERR_FAILED" not in m.text and "404" not in m.text else None)
                for pat in ("https://cdn.jsdelivr.net/**", "https://*.supabase.co/**", "https://fonts.googleapis.com/**", "https://fonts.gstatic.com/**"):
                    page.route(pat, lambda r, req: r.abort())
                loaded = {"ov": 0, "det": []}
                def data_route(rt, req):
                    path = req.url.split("?")[0]
                    if path.endswith("/data/oversikt.json"):
                        loaded["ov"] += 1
                        return rt.fulfill(status=200, content_type="application/json", body=OV_BODY, headers={"content-encoding": "identity"})
                    sid = path.rsplit("/", 1)[-1][:-5]
                    loaded["det"].append(sid)
                    rt.fulfill(status=200, content_type="application/json", body=DET_BODY.get(sid, "{}"))
                page.route("**/data/oversikt.json", data_route)
                page.route("**/data/spots/*.json", data_route)
                page.route("**/data/minikart/*.json", lambda rt, req: rt.fulfill(status=404, body=""))
                # 7. simulert 4G (CDP) for første visning
                cdp = ctx.new_cdp_session(page)
                cdp.send("Network.enable")
                cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150, "downloadThroughput": 9 * 1024 * 1024 / 8, "uploadThroughput": 3 * 1024 * 1024 / 8})
                t_start = time.monotonic()
                page.goto(f"http://127.0.0.1:{port}/index.html#hjem")
                page.wait_for_selector("#viewHjem:not([hidden]) #bestKort")
                first_paint = time.monotonic() - t_start
                cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
                assert first_paint < 1.5, f"første visning av Hjem tok {first_paint:.2f} s på simulert 4G ({label})"
                assert loaded["ov"] >= 1 and not loaded["det"], f"Hjem skal bare laste oversikten: {loaded}"
                print(f"7/4 ({label}): første visning av Hjem {first_paint:.2f} s på simulert 4G, bare oversikten lastet - OK")

                def shot(name):
                    page.screenshot(path=str(SHOT_DIR / f"{name}_{label}.png"), full_page=False)
                def go(hash_, sel):
                    page.evaluate(f"location.hash = '{hash_}'"); page.wait_for_selector(sel); page.wait_for_timeout(300)

                # 6. Hjem: «Beste økt» bare i valgt region (Troms er standard), «Spots i Troms»
                sub = page.text_content("#viewHjem .sek .sub")
                assert "Troms" in sub, sub
                n_rows = page.evaluate("document.querySelectorAll('#viewHjem .rader .rad, #viewHjem table.spots tr.s').length")
                troms = sum(1 for s in overview["spots"] if s["region"] == "Troms")
                if mobile:
                    assert n_rows == min(troms, 5) or n_rows == troms, (n_rows, troms)
                    assert page.text_content("#viewHjem").count("Spots i Troms") == 1
                # PR #12 punkt a: valgt regionbrikke synlig, rekkefølge som oversikt.regions (spots.json, nord til sør)
                chip = page.evaluate("""() => { const row = document.querySelector('#viewHjem .regionvelger'); const c = row && row.querySelector('[aria-pressed="true"]');
                    if(!c) return null; const r = row.getBoundingClientRect(), b = c.getBoundingClientRect();
                    return {txt: c.textContent.trim(), inside: b.left >= r.left - 1 && b.right <= r.right + 1,
                            order: [...row.querySelectorAll('.chip')].map(x => x.textContent.trim()).filter(t => t !== 'Alle')}; }""")
                assert chip and (mobile and chip["txt"] == "Troms" or not mobile) and chip["inside"], f"valgt regionbrikke ikke synlig ({label}): {chip}"
                assert chip["order"] == [r["name"] for r in overview["regions"]] and chip["order"][0] == "Finnmark", chip["order"]
                # PR #12 punkt b/c: aldri «0,0» i ukerutene/tabellen; dagens lys er over kl. 22:10 → ingen «I dag»-kolonne
                txt = page.evaluate("[...document.querySelectorAll('#viewHjem .uke i, #viewHjem .celle, #viewHjem .rad .na, #viewHjem td.na')].map(e => e.textContent.trim())")
                assert not any(t in ("0,0", "0") or t.startswith("0,0") for t in txt), [t for t in txt if t.startswith("0")][:5]
                heads = page.evaluate("[...document.querySelectorAll('#viewHjem table.spots thead th.dag, #viewHjem .gruppe-topp .uke b')].map(e => e.textContent.trim())")
                assert heads and not any(h.startswith("I dag") for h in heads) and not page.query_selector("#viewHjem .uke b.idag, #viewHjem .uke i.over"), heads[:8]
                print(f"PR #12 a-c ({label}): valgt brikke «{chip['txt']}» synlig, rekkefølge nord-sør, ingen «0,0», tabellen starter på i morgen etter mørket - OK")
                # ROADMAP K del C.4: «Foreløpig»/«Forbud nå» ved navnet, og ikke i «Beste økt»
                best_name = page.text_content("#bestKort .navn").strip()
                assert best_name not in ("Testspot 078", "Testspot 079"), f"foreløpig/forbudt spot i Beste økt: {best_name}"
                lbl = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#viewHjem a.rad, #viewHjem table.spots tr.s')]
                    .map(r => [r.querySelector('b').textContent.trim(), r.textContent]).filter(([n]) => n === 'Testspot 078' || n === 'Testspot 079'))""")
                if lbl:   # radene vises (mobil: 5 beste; nett: tabellen)
                    assert all(("Foreløpig" in t) if n == "Testspot 078" else ("Forbud nå" in t) for n, t in lbl.items()), lbl
                f79 = page.evaluate("""() => { const H = Front.helpers, s = DATA.spots.find(x => x.id === 'test079'), n = DATA.spots.find(x => x.id === 'test000');
                    return [H.forbudNa(s), H.stedText(s), H.forbudNa(s, Date.parse('2026-05-01T12:00:00Z')), H.forbudNa(n), H.iBesteOkt(s, Date.parse('2026-05-01T12:00:00Z'))]; }""")
                assert f79[0] is True and "Forbud nå" in f79[1] and f79[2] is False and f79[3] is False and f79[4] is True, f79
                print(f"C.4 ({label}): Beste økt = {best_name}, merkelapper {sorted(lbl)}, Forbud nå 1.10-31.3 (ikke 1.5) - OK")
                shot("hjem")
                # 8. nett-tabellen: regionfilter, «Vis alle», sticky
                if not mobile:
                    assert page.evaluate("getComputedStyle(document.querySelector('table.spots thead th')).position") == "sticky"
                    page.click("[data-tabellregion='Troms']"); page.wait_for_timeout(200)
                    heads = page.evaluate("[...document.querySelectorAll('table.spots tr.g td')].map(td => td.textContent.trim().split(' ')[0])")
                    assert heads == ["Troms"], heads
                    page.click("[data-tabellregion='']"); page.wait_for_timeout(200)
                    page.click("table.spots .visalle"); page.wait_for_timeout(200)
                    shot("tabell")
                # 5. søk på «a»
                if mobile:
                    page.click(".sokknapp"); page.wait_for_selector("#sokM"); page.fill("#sokM", "a"); page.wait_for_selector("#sokRes .srad")
                    root = "#sokRes"
                else:
                    page.fill("#sokPC", "a"); page.wait_for_selector("#sokDrop:not([hidden]) .srad")
                    root = "#sokDrop"
                n_hits = page.evaluate(f"document.querySelectorAll('{root} .srad').length")
                n_groups = page.evaluate(f"document.querySelectorAll('{root} h3').length")
                assert n_hits <= 20 and n_groups >= 2 and page.query_selector(f"{root} #sokFlere"), (n_hits, n_groups)
                shot("sok-a")
                page.click(f"{root} #sokFlere"); page.wait_for_timeout(200)
                assert page.evaluate(f"document.querySelectorAll('{root} .srad').length") > 20
                if mobile:
                    page.click("#sokAvbryt"); page.wait_for_selector("#viewHjem:not([hidden])")
                else:
                    page.fill("#sokPC", ""); page.keyboard.press("Escape")
                # 2/3. Utforsk: hele kartet og én region, ingen overlappende lapper
                go("#utforsk", "#viewUtforsk:not([hidden]) .mk, #viewUtforsk:not([hidden]) .klynge")
                def pills_ok(where):
                    bad = page.evaluate("""() => { const b = el => el.getBoundingClientRect();
                        const els = [...document.querySelectorAll('.mk:not(.bare) .mk-pill, .klynge .ring')].map(e => ({r: b(e), id: (e.closest('.mk')||e.closest('.klynge')).dataset.id || 'klynge'}));
                        const out = []; for(let i=0;i<els.length;i++) for(let j=i+1;j<els.length;j++){ const a = els[i].r, c = els[j].r;
                          if(a.left < c.right - 2 && a.right > c.left + 2 && a.top < c.bottom - 2 && a.bottom > c.top + 2) out.push([els[i].id, els[j].id]); } return out; }""")
                    assert not bad, f"overlappende merkelapper ({label}, {where}): {bad[:6]}"
                # dagbrikkene etter mørket (T0 kl. 22:10): «Nå» først, så «I morgen» = dagen etter oversiktens første dag
                dchips = page.evaluate("[...document.querySelectorAll('#dagChips .chip')].map(b => [b.textContent.trim(), b.dataset.day])")
                d1 = overview["spots"][0]["dager"][1]["d"]
                assert dchips[0] == ["Nå", ""] and dchips[1] == ["I morgen", d1] and len(dchips) == 8, dchips
                page.click("#utforskChips [data-view='']"); page.wait_for_timeout(900); pills_ok("hele kartet"); shot("utforsk-hele")
                n_cl = int(page.evaluate("document.querySelector('#markersLayer').dataset.clusters || '0'"))
                reg_chip = page.query_selector("#utforskChips [data-view='Troms']")
                assert reg_chip, "regionbrikken Troms mangler"
                reg_chip.click(); page.wait_for_timeout(900); pills_ok("Troms"); shot("utforsk-troms")
                print(f"2/3 ({label}): Utforsk hele kartet ({n_cl} klynger) og Troms uten overlappende lapper - OK")
                # 4. åpne en spot laster nøyaktig én detaljfil
                first = overview["spots"][0]["id"] if any(s["region"] == "Troms" for s in overview["spots"]) else overview["spots"][0]["id"]
                troms_id = next(s["id"] for s in overview["spots"] if s["region"] == "Troms")
                go(f"#spot={troms_id}", "#viewSpot:not([hidden]) .vurdering .ord")
                assert loaded["det"] == [troms_id], loaded["det"]
                ctx.close()
            browser.close()
    finally:
        srv.shutdown()
        watchdog.cancel()
    assert not errors, "JavaScript-feil: " + "\n".join(errors[:8])
    print(f"OK: test_skalering_browser ({N_SPOTS} spots, {len(list(SHOT_DIR.glob('*.png')))} skjermbilder i {SHOT_DIR.relative_to(ROOT)})")


if __name__ == "__main__":
    main()
