"""Flytter en bygget spot inn i spots.json (ROADMAP K del C.4, 16.10.2026). LAGET, IKKE KJØRT - bare Theodor
kjører den, én spot (eller én region) av gangen, med sitt ja.

    python tools/godkjenn_spot.py <id> [--tørr] [--overstyr "<kommentar>" [--av "claude (delegert av Theodor 16.10.2026)"]]

Leser data/kandidater/bygget/<id>.json (tools/bygg_spot.py) og legger spoten til i spots.json med
  status "forelopig", forelopig_fra (dagens dato), region, kilde «liste 15.10 + spotfabrikken» og
  restriksjoner fra verneforskriften (data/kandidater/vern.json: ferdsels-/surfeforbud for sjø eller strand
  i et verneområde innen 200 m av spoten, ikke stedsbundne).
Appen viser da merkelappen «Foreløpig», holder spoten utenfor «Beste økt» de første 14 dagene, og viser
«Forbud nå» (aldri i «Beste økt») i forbudsperioden. Henteren henter og rater spoten som alle andre - ratingen
røres ikke. Regionen legges i spots.json sin «regions» først når den første spoten i regionen kommer inn
(rekkefølge nord til sør etter regionforslagene i data/kandidater/kandidater.json).

Stopper (endrer ingenting) hvis: id-en allerede finnes; posisjonen ikke er godkjent av Theodor (satt_av «theodor»);
kandidaten venter på Theodor; BarentsWatch-punktet fortsatt er foreløpig (snittet
må kjøres i Actions først); ideal_height/max_height mangler (point/reef - Theodor setter dem); facing,
vindu eller havpunkt mangler. Har fabrikken flagget spoten (buet strand, facing utenfor vinduet, BarentsWatch uten
data), kreves --overstyr med Theodors kommentar (lagres i _overstyrt). spots.json er håndformatert - spoten settes inn som tekst, og resten av fila
sjekkes uendret etterpå. Etter innlegging: fysikk-kontrollør, alle tester, og CLAUDE.md sin stopp-regel.
NB: vindu, havpunkt, BarentsWatch-punkt og offshorevind er felt som krever Theodors ja (CLAUDE.md) - å kjøre
skriptet ER det ja-et for den ene spoten, og offshore_wind (±45°, «standard, ubekreftet») bør sjekkes mot kart
eller lokale før kjøring."""
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
BYGGET = ROOT / "data" / "kandidater" / "bygget"
POS = ROOT / "data" / "kandidater" / "posisjoner.json"
KAND = ROOT / "data" / "kandidater" / "kandidater.json"
VERN = ROOT / "data" / "kandidater" / "vern.json"
VERN_NEAR_M = 200
KILDE = "liste 15.10 + spotfabrikken"
# Theodor 16.10.2026 (punkt 8): gjennomgangen av posisjoner og bygde spots er delegert til Claude (chatten);
# Theodor beholder ja/nei til merge av region-PR-ene
GODKJENNERE = {"theodor", "claude (delegert av Theodor 16.10.2026)"}


def grunn(navn):
    """Kort grunn til visningen («1. okt-31. mars, fuglefredning») ut fra verneområdets navn."""
    n = (navn or "").lower()
    for nokkel, ord_ in (("fuglefred", "fuglefredning"), ("dyrelivsfred", "dyrelivsfredning"), ("plantefred", "plantefredning"),
                         ("naturreservat", "naturreservat"), ("nasjonalpark", "nasjonalpark"), ("landskapsvern", "landskapsvern"),
                         ("marin", "marint verneområde")):
        if nokkel in n:
            return ord_
    return navn


def restriksjoner(sid):
    if not VERN.exists():
        return []
    out = []
    for h in json.loads(VERN.read_text(encoding="utf-8")).get("kandidater", {}).get(sid, []):
        if h.get("avstand_m") is None or h["avstand_m"] > VERN_NEAR_M:
            continue
        for r in h.get("restriksjoner") or []:
            if r.get("stedsbundet") or r.get("gjelder") not in ("sjø", "strand", "begge"):
                continue
            if r.get("type") in ("ferdselsforbud", "surfeforbud"):
                out.append({"type": r["type"], "fra": r.get("fra"), "til": r.get("til"), "gjelder": r["gjelder"],
                            "grunn": grunn(h["navn"]), "verneomrade": h["navn"], "kilde": r.get("kilde")})
    return out


def check(sid, b, spots, pos, kand):
    """(stopp, flagg): «stopp» kan aldri overstyres; «flagg» er fabrikkens egne varsler (buet strand, facing utenfor
    vinduet, BarentsWatch uten data …) og krever --overstyr "<Theodors kommentar>" (Theodor 16.10.2026)."""
    s = b["spot"]
    why = []
    if any(x["id"] == sid for x in spots["spots"]):
        why.append("id-en finnes alt i spots.json")
    p = pos.get(sid, {})
    if not (p.get("satt_av") in GODKJENNERE and p.get("vurdering") == "godkjent"):
        why.append("posisjonen er ikke godkjent (satt_av «theodor» eller Claude delegert av Theodor, vurdering «godkjent» i data/kandidater/posisjoner.json)")
    elif p.get("spot") != s.get("spot"):
        why.append("posisjonen i bygget-fila er ikke lik den Theodor godkjente - bygg på nytt (python tools/bygg_spot.py <id>)")
    if kand.get(sid, {}).get("status") != "kandidat":
        why.append(f"kandidaten har status «{kand.get(sid, {}).get('status')}»")
    if kand.get(sid, {}).get("venter_pa_theodor"):
        why.append(kand[sid]["venter_pa_theodor"])
    if "FORELØPIG" in (s.get("_barentswatch") or "") or not s.get("_barentswatch_snitt") or not (ROOT / s["_barentswatch_snitt"]).exists():
        why.append("BarentsWatch-snittet er ikke kjørt/valgt - kjør find_bw_point.yml med kandidater og tools/velg_bw_punkt.py først")
    if s.get("ideal_height") is None or s.get("max_height") is None:
        why.append("ideal_height/max_height mangler - Theodor setter dem i bygget-fila")
    for f in ("facing", "swell_window", "offshore", "offshore_wind"):
        if s.get(f) is None or s.get(f) in ([], {}):
            why.append(f"{f} mangler")
    flagg = list(b.get("flagg") or [])
    if not s.get("barentswatch_point") and s.get("_barentswatch_snitt") and not any("BarentsWatch" in f for f in flagg):
        flagg.append("BarentsWatch uten data i snittet - spoten får ikke barentswatch_point (reservemodellen brukes)")
    return why, flagg


def insert_text(text, spots, entry, new_region):
    """Sett inn spoten sist i «spots» (og evt. regionen i «regions») som tekst; resten av fila uendret."""
    body = json.dumps(entry, ensure_ascii=False, indent=2)
    body = "\n".join("    " + ln for ln in body.splitlines())
    tail = "\n  ]\n}"
    assert text.rstrip().endswith(tail.strip()) and text.rstrip()[: -len(tail.strip())].rstrip().endswith("}")
    head = text.rstrip()[: -len(tail.strip())].rstrip()
    out = head + ",\n" + body + tail + "\n"
    if new_region:
        mark = '  "regions": ['
        i = out.index(mark)
        j = out.index("\n  ],", i)
        out = out[:j] + ",\n    " + json.dumps(new_region, ensure_ascii=False) + out[j:]
    return out


def main():
    argv = sys.argv[1:]
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i > 0 and argv[i - 1] in ("--overstyr", "--av"))]
    dry = "--tørr" in sys.argv or "--torr" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    sid = args[0]
    bf = BYGGET / f"{sid}.json"
    if not bf.exists():
        sys.exit(f"Fant ikke {bf} - kjør python tools/bygg_spot.py {sid} først")
    b = json.loads(bf.read_text(encoding="utf-8"))
    text = SPOTS.read_text(encoding="utf-8")
    spots = json.loads(text)
    pos = json.loads(POS.read_text(encoding="utf-8"))["kandidater"] if POS.exists() else {}
    kand_doc = json.loads(KAND.read_text(encoding="utf-8"))
    kand = {k["id"]: k for k in kand_doc["kandidater"]}
    why, flagg = check(sid, b, spots, pos, kand)
    if why:
        sys.exit(f"{sid}: legges IKKE inn:\n  - " + "\n  - ".join(why))
    overstyr = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--overstyr" and i + 1 < len(sys.argv)), None)
    av = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--av" and i + 1 < len(sys.argv)), "theodor")
    if av not in GODKJENNERE:
        sys.exit(f"--av må være en av {sorted(GODKJENNERE)}")
    if flagg and not (overstyr and overstyr.strip()):
        sys.exit(f"{sid}: legges IKKE inn - fabrikken har flagget den:\n  - " + "\n  - ".join(flagg)
                 + '\nTheodor kan overstyre: python tools/godkjenn_spot.py ' + sid + ' --overstyr "<kommentar>"')
    s = dict(b["spot"])
    s.pop("tidevann", None)   # henteren slår opp tidevann fra posisjonen selv; referansestedet står i bygget-fila
    s.update(status="forelopig", forelopig_fra=dt.date.today().isoformat(), kilde=KILDE)
    if flagg:
        s["_overstyrt"] = {"kommentar": overstyr.strip(), "flagg": flagg, "dato": dt.date.today().isoformat(), "av": av}
    rs = restriksjoner(sid)
    if rs:
        s["restriksjoner"] = rs
    new_region = None
    if s.get("region") and s["region"] not in [r["name"] for r in spots["regions"]]:
        forslag = kand_doc.get("regioner_forslag", [])
        known = [r["name"] for r in spots["regions"]]
        order = sorted(known + [s["region"]], key=lambda n: forslag.index(n) if n in forslag else 99)
        new_region = {"name": s["region"], "order": order.index(s["region"]) + 1}
        if new_region["order"] <= len(known):
            sys.exit(f"{sid}: legges IKKE inn - regionen {s['region']} hører hjemme midt i rekkefølgen (order {new_region['order']}); "
                     "flytt order for regionene etter i spots.json for hånd først (nord til sør), og kjør på nytt")
    out = insert_text(text, spots, s, new_region)
    new = json.loads(out)
    assert new["spots"][:-1] == spots["spots"] and new["spots"][-1]["id"] == sid, "de eksisterende spotene ble endret"
    if dry:
        print(f"TØRRKJØRING - spots.json er ikke endret. Ville lagt inn:\n{json.dumps(s, ensure_ascii=False, indent=2)}")
        if new_region:
            print(f"og regionen {new_region}")
        return
    SPOTS.write_text(out, encoding="utf-8")
    print(f"{sid} lagt inn i spots.json som «forelopig» ({len(rs)} restriksjoner{', ny region ' + s['region'] if new_region else ''}). "
          "Neste: fysikk-kontrollør og alle tester før commit.")


if __name__ == "__main__":
    main()
