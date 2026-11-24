"""Test av vakthunden (fetcher/vakthund.py) uten nett - GitHub-API-et og ntfy er falske. Kjør: python fetcher/test_vakthund.py"""
import datetime as dt
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vakthund as v  # noqa: E402

now = dt.datetime(2026, 10, 16, 12, 0, tzinfo=dt.timezone.utc)
fersk = {"generated": (now - dt.timedelta(hours=2)).isoformat()}
gammel = {"generated": (now - dt.timedelta(hours=8)).isoformat()}
ok = [{"conclusion": "success"}, {"conclusion": "success"}]
en_feil = [{"conclusion": "failure", "html_url": "u1"}, {"conclusion": "success"}]
to_feil = [{"conclusion": "failure", "html_url": "https://x/runs/2"}, {"conclusion": "failure", "html_url": "https://x/runs/1"}]

# 1. når er det et problem
assert v.problemer(fersk, ok, now) == []
assert len(v.problemer(gammel, ok, now)) == 1 and "8 timer" in v.problemer(gammel, ok, now)[0]
assert v.problemer(fersk, en_feil, now) == [], "én feil er ikke nok"
assert "2 ganger på rad" in v.problemer(fersk, to_feil, now)[0]
assert v.problemer(None, None, now) and v.problemer({}, None, now), "uleselig/manglende generated er et problem"
assert v.problemer(fersk, None, now) == [], "kjøringene ukjent: ingen falsk alarm"
print("1: ferskt/8 t gammelt/én feil/to feil på rad/uleselig - OK")

# 1b. fotavtrykk 10.11.2026: «Hent varsel» kl. 03:17-21:17 UTC hver 3. time (ingen kl. 00:17), vakthunden kl. 04:47,
# 10:47, 16:47 og 22:47 UTC. «generated» er rundet ned til hel time. Alarm etter TO uteblitte kjøringer, aldri én -
# heller ikke over natthullet 21:17 → 03:17.
def kl(dag, time, minutt=0):
    return dt.datetime(2026, 11, dag, time, minutt, tzinfo=dt.timezone.utc)
def gml(gen, na):
    return v.problemer({"generated": gen.isoformat()}, ok, na)
assert v.maks_alder(kl(10, 21), kl(11, 4, 47)) == 10 and v.maks_alder(kl(10, 3), kl(10, 10, 47)) == 7
assert v.maks_alder(kl(10, 21), kl(11, 0, 16)) == 7 and v.maks_alder(kl(10, 21), kl(11, 0, 17)) == 10, "hullet er kl. 00:17 UTC"
assert v.maks_alder(kl(11, 0), kl(11, 0, 30)) == 10 and v.maks_alder(kl(11, 1), kl(11, 12)) == 7, "manuell kjøring rundt midnatt"
for gen, na in ((kl(10, 21), kl(10, 22, 47)), (kl(11, 3), kl(11, 4, 47)), (kl(11, 9), kl(11, 10, 47)), (kl(11, 15), kl(11, 16, 47))):
    assert gml(gen, na) == [], f"alt gikk: ingen alarm ({gen:%H} → {na:%H:%M})"
for gen, na in ((kl(10, 21), kl(11, 4, 47)), (kl(10, 21), kl(11, 6, 30)), (kl(11, 6), kl(11, 10, 47)), (kl(11, 12), kl(11, 16, 47)), (kl(11, 18), kl(11, 22, 47))):
    assert gml(gen, na) == [], f"én uteblitt kjøring: ingen alarm ({gen:%H} → {na:%H:%M})"
for gen, na, timer in ((kl(10, 18), kl(11, 4, 47), "11 timer"), (kl(10, 21), kl(11, 10, 47), "14 timer"), (kl(11, 3), kl(11, 10, 47), "8 timer"),
                       (kl(11, 9), kl(11, 16, 47), "8 timer"), (kl(11, 15), kl(11, 22, 47), "8 timer")):
    assert len(gml(gen, na)) == 1 and timer in gml(gen, na)[0], f"to uteblitte kjøringer: alarm ({gen:%H} → {na:%H:%M}): {gml(gen, na)}"
print("1b: natthullet (ingen «Hent varsel» kl. 00:17 UTC) gir ikke alarm etter én uteblitt kjøring, men etter to - OK")


class FalskGitHub:
    def __init__(self, apen=None):
        self.apen, self.logg, self.nr = apen, [], 41

    def apen_issue(self):
        return self.apen

    def ny_issue(self, body):
        self.nr += 1
        self.logg.append(("ny", self.nr, body))
        self.apen = {"number": self.nr, "title": v.TITTEL, "created_at": now.isoformat(), "updated_at": now.isoformat()}
        return {"number": self.nr}

    def kommenter(self, nr, body):
        self.logg.append(("kommentar", nr, body))

    def lukk(self, nr):
        self.logg.append(("lukk", nr, None))
        self.apen = None


# 2. ingen issue når alt er ferskt
gh = FalskGitHub()
assert v.vakt(gh, fersk, ok, now) == ("i orden", None) and gh.logg == []
# 3. ny issue ved gammelt varsel, med alder og lenke til siste feilede kjøring
gh = FalskGitHub()
assert v.vakt(gh, gammel, to_feil, now)[0] == "ny"
kind, nr, body = gh.logg[0]
assert kind == "ny" and "8 timer gammelt" in body and "https://x/runs/2" in body, body
# 4. åpen issue: innen DEDUPE_T (5 t) ingen ny kommentar; ved neste sjekk (6 t etter, om cron er litt tidlig eller
# sen) kommentar (aldri en ny issue)
assert v.vakt(gh, gammel, to_feil, now + dt.timedelta(hours=4, minutes=59))[0] == "dedupe" and len(gh.logg) == 1
assert v.vakt(gh, gammel, to_feil, now + dt.timedelta(hours=5, minutes=50))[0] == "kommentert" and len(gh.logg) == 2
gh.logg.pop()
assert v.vakt(gh, gammel, to_feil, now + dt.timedelta(hours=6))[0] == "kommentert" and gh.logg[-1][0] == "kommentar" and gh.logg[-1][1] == nr
assert sum(1 for x in gh.logg if x[0] == "ny") == 1
# 5. ferskt igjen: kommentar og lukking
senere = now + dt.timedelta(hours=9)
assert v.vakt(gh, {"generated": (senere - dt.timedelta(hours=1)).isoformat()}, ok, senere) == ("lukket", nr)
assert [x[0] for x in gh.logg[-2:]] == ["kommentar", "lukk"] and gh.apen is None
# 5b. kjøringene ukjente (API-feil): et ferskt varsel lukker IKKE en åpen issue (kontrollør 16.10)
apen = {"number": 7, "title": v.TITTEL, "created_at": now.isoformat(), "updated_at": now.isoformat()}
gh = FalskGitHub(apen=dict(apen))
assert v.vakt(gh, fersk, None, now) == ("ukjent", 7) and gh.logg == [] and gh.apen is not None
assert v.vakt(FalskGitHub(), fersk, None, now) == ("ukjent", None)
# ugyldig «generated» er et problem, ikke en krasj
assert "ugyldig «generated»" in v.problemer({"generated": "i går"}, ok, now)[0]
# ett nytt forsøk før «kunne ikke leses»
kall = []
def get_feil_en_gang(url, params=None, headers=None, timeout=None):
    kall.append(1)
    if len(kall) == 1:
        raise v.requests.ConnectionError("nede")
    return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: fersk})()
assert v.les_oversikt(now, get=get_feil_en_gang, sleep=lambda s: None) == fersk and len(kall) == 2
kall.clear()
def get_alltid_feil(url, params=None, headers=None, timeout=None):
    kall.append(1)
    raise v.requests.ConnectionError("nede")
assert v.les_oversikt(now, get=get_alltid_feil, sleep=lambda s: None) is None and len(kall) == 2
print("5b: ukjente kjøringer lukker ikke, ugyldig generated, nytt forsøk før «kunne ikke leses» - OK")
# test-merket issue
gh = FalskGitHub()
v.vakt(gh, gammel, ok, now, test=True)
assert "TEST" in gh.logg[0][2]
print("2-5: ingen issue når ferskt, ny issue med alder og lenke, kommentar (maks hver 6. t), lukking når ferskt - OK")

# 6. ntfy bare med NTFY_TOPIC, maks hver 6. time
sendt = []
post = lambda url, json=None, timeout=None: sendt.append(json) or type("R", (), {"raise_for_status": lambda s: None})()
os.environ.pop("NTFY_TOPIC", None)
st = {}
assert v.ntfy(["x"], now, st, post) is False and not sendt
os.environ["NTFY_TOPIC"] = "test"
assert v.ntfy(["x"], now, st, post) is True and len(sendt) == 1
assert v.ntfy(["x"], now + dt.timedelta(hours=4, minutes=59), st, post) is False and len(sendt) == 1
assert v.ntfy(["x"], now + dt.timedelta(hours=6), st, post) is True and len(sendt) == 2
os.environ.pop("NTFY_TOPIC", None)
print("6: ntfy bare med NTFY_TOPIC, maks hver 6. time - OK")
# 7. «Lyngen henger sammen» (svar.md 23.11.2026 kl. 14.05): Breivikeidet med minst 2 poeng mens Russelv eller
# Lenangsøyra viser «Flatt» eller «Treffer ikke» i samme time gir en egen issue. Bare varsel.
assert (v.LYNGEN_ANKER, v.LYNGEN_FOLGER, v.LYNGEN_MIN_POENG) == ("breivikeidet", ("russelv", "lenangsoyra"), 2)
assert v.LYNGEN_TITTEL != v.TITTEL and v.LIVE_SPOT.format(id="russelv") == "https://theodorll03-bit.github.io/nordsurf/data/spots/russelv.json"
# 7.1: ordet, som appen viser det (ratingWord(), zeroWord() og calmWindWord() i docs/js/app.js)
Z0 = {"energy": 0, "wind": 0, "tide": 0, "local": 0, "cap": 0}
def time(**kw):
    return {"stars": 0, "low_reason": None, "surf_height": 0.1, "zero_losses": dict(Z0), "faded_wind": 0, "wind_speed": 3.0, "gust": 5.0,
            "wind_type": "onshore", **kw}
ord_ = [
    (time(low_reason="flat"), "Flatt"), (time(), "Flatt"), (time(surf_height=0.29), "Flatt"),
    (time(surf_height=0.3), None), (time(low_reason="flat", surf_height=0.5), None),          # «Smått»
    (time(surf_height=None), None),                                                           # «–»: tallet mangler, aldri alarm
    (time(low_reason="flat", surf_height=None), "Flatt"), (time(low_reason="flat", stars=1, surf_height=0.5), "Flatt"),
    (time(low_reason="treffer_ikke"), "Treffer ikke"), (time(low_reason="treffer_ikke", stars=1, surf_height=0.6), "Treffer ikke"),
    (time(low_reason="treffer_ikke", surf_height=None), "Treffer ikke"),
    (time(low_reason="blown_out"), "Flatt"),                                                  # svak vind uten poengtap, under 0,3 m
    (time(low_reason="blown_out", surf_height=0.3), None), (time(low_reason="blown_out", surf_height=None), None),
    (time(low_reason="blown_out", zero_losses=dict(Z0, wind=1)), None), (time(low_reason="blown_out", faded_wind=1), None),
    (time(low_reason="blown_out", wind_speed=8.0), None), (time(low_reason="blown_out", wind_speed=7.0, gust=12.0), None),   # sterk med kast
    (time(low_reason="blown_out", wind_speed=None), None),                                    # vindstyrken mangler: ukjent
    (time(low_reason="blown_out", wind_speed=11.0, gust=None, wind_type="offshore"), "Flatt"), (time(low_reason="blown_out", wind_speed=12.0, wind_type="offshore"), None),
    (time(low_reason="blown_out", wind_speed=9.0, gust=14.0, wind_calm_ms=14.0), "Flatt"),    # egen vindkurve: middelvinden mot spotens grense
    (time(low_reason="stormsjo"), None), (time(stars=2, surf_height=0.8), None), (time(stars=1, surf_height=0.2), None),
]
for h, venter in ord_:
    assert v.lyngen_ord(h) == venter, (h, v.lyngen_ord(h), venter)
# 7.2: sammenlikningen time for time
def fil(navn, timer, run="abc123"):
    return {"id": navn.lower(), "name": navn, "run": run, "format": "spot-2", "hours": [dict(h, t=t) for t, h in timer]}
na = dt.datetime(2026, 11, 26, 4, 47, tzinfo=dt.timezone.utc)
T = lambda time_: f"2026-11-26T{time_:02d}:00Z"
bre = fil("Breivikeidet", [(T(3), time(stars=2, surf_height=0.7)), (T(4), time(stars=1, surf_height=0.6)), (T(5), time(stars=2, surf_height=0.7)),
                           (T(6), time(stars=3, surf_height=0.8)), (T(7), time(stars=None, surf_height=None)), (T(8), time(stars=2, surf_height=0.7))])
rus = fil("Russelv", [(T(3), time(low_reason="flat")), (T(4), time(low_reason="flat")), (T(5), time(stars=0, low_reason="blown_out", surf_height=0.7, wind_speed=9.0)),
                      (T(6), time(low_reason="treffer_ikke", surf_height=0.2)), (T(7), time(low_reason="flat"))])
len_ = fil("Lenangsøyra", [(T(5), time(low_reason="flat")), (T(6), time(stars=1, surf_height=0.7)), (T(8), time(surf_height=None))])
avvik, ukjente = v.lyngen_avvik({"breivikeidet": bre, "russelv": rus, "lenangsoyra": len_}, na)
# kl. 03Z er passert, kl. 04Z har Breivikeidet 1 poeng, kl. 07Z mangler Breivikeidets poeng, kl. 08Z mangler tallet hos Lenangsøyra
assert ukjente == [] and [(a["t"], a["spot"], a["ord"]) for a in avvik] == [(T(5), "lenangsoyra", "Flatt"), (T(6), "russelv", "Treffer ikke")], avvik
assert avvik[1]["anker_poeng"] == 3 and avvik[1]["navn"] == "Russelv" and avvik[1]["surf_height"] == 0.2 and avvik[1]["poeng"] == 0
# blåst ut med bølger (0,7 m) og 1 poeng er ikke avvik: poengene kan vinden ta
assert not any(a["t"] == T(5) and a["spot"] == "russelv" for a in avvik)
# alt i orden: ingen avvik, ingen ukjente
godt = fil("Russelv", [(T(5), time(stars=1, surf_height=0.7)), (T(6), time(stars=0, low_reason="blown_out", surf_height=0.7, wind_speed=9.0))])
assert v.lyngen_avvik({"breivikeidet": bre, "russelv": godt, "lenangsoyra": godt}, na) == ([], [])
# ukjent er aldri et avvik: fil som mangler, fil uten timer, fil fra en annen kjøring, og Breivikeidet selv
assert v.lyngen_avvik({"breivikeidet": bre, "russelv": None, "lenangsoyra": godt}, na) == ([], ["russelv"])
assert v.lyngen_avvik({"breivikeidet": bre, "russelv": dict(rus, hours=[]), "lenangsoyra": godt}, na) == ([], ["russelv"])
assert v.lyngen_avvik({"breivikeidet": bre, "russelv": dict(rus, run="annen"), "lenangsoyra": godt}, na) == ([], ["russelv"])
assert v.lyngen_avvik({"breivikeidet": None, "russelv": rus, "lenangsoyra": len_}, na) == ([], ["russelv", "lenangsoyra"])
assert v.lyngen_avvik({}, na) == ([], ["russelv", "lenangsoyra"])
# den ene ukjent, den andre med avvik: avviket meldes
a2, u2 = v.lyngen_avvik({"breivikeidet": bre, "russelv": rus, "lenangsoyra": None}, na)
assert u2 == ["lenangsoyra"] and [x["spot"] for x in a2] == ["russelv"]
# 7.2b (24.11.2026, feiljegeren funn 5): mørke timer telles ikke. Appen viser «Mørkt» og ikke ordet der. Lysfeltet er
# «light» i detaljfila, med «daylight» som reserve (lightClass() i docs/js/app.js). Uten lysfelt telles timen som før.
for lys, morkt in (({"light": "mørkt"}, True), ({"light": "skumring"}, False), ({"light": "dag"}, False), ({"daylight": False}, True),
                   ({"daylight": True}, False), ({}, False), ({"light": None, "daylight": None}, False), ({"light": "dag", "daylight": False}, False)):
    assert v.lyngen_morkt(time(**lys)) is morkt, lys
bre_l = fil("Breivikeidet", [(T(t_), time(stars=2, surf_height=0.7)) for t_ in (5, 6, 7, 8, 9)])
rus_l = fil("Russelv", [(T(5), time(low_reason="flat", light="mørkt")), (T(6), time(low_reason="treffer_ikke", light="skumring")),
                        (T(7), time(low_reason="flat", light="dag")), (T(8), time(low_reason="flat", daylight=False)), (T(9), time(low_reason="flat"))])
len_l = fil("Lenangsøyra", [(T(5), time(low_reason="treffer_ikke", light="mørkt")), (T(6), time(stars=1, surf_height=0.7, light="skumring"))])
a_l, u_l = v.lyngen_avvik({"breivikeidet": bre_l, "russelv": rus_l, "lenangsoyra": len_l}, na)
assert u_l == [] and [(a["t"], a["spot"], a["ord"]) for a in a_l] == [(T(6), "russelv", "Treffer ikke"), (T(7), "russelv", "Flatt"), (T(9), "russelv", "Flatt")], a_l
# bare mørke avvik: ingen avvik, og en åpen sak lukkes som når avviket er borte
bare_morkt = fil("Russelv", [(T(5), time(low_reason="flat", light="mørkt"))])
assert v.lyngen_avvik({"breivikeidet": bre_l, "russelv": bare_morkt, "lenangsoyra": bare_morkt}, na) == ([], [])
print("7.1-7.2: ordet som i appen, avvik bare i samme time fra nå, minst 2 poeng på Breivikeidet, ukjent er aldri avvik, mørke timer telles ikke - OK")


class FalskGitHub2(FalskGitHub):
    """Flere issuer, én per tittel (som det ekte API-et: apen_issue(tittel) og ny_issue(body, tittel))."""

    def __init__(self, apne=None):
        super().__init__()
        self.apne = dict(apne or {})

    def apen_issue(self, tittel=v.TITTEL):
        return self.apne.get(tittel)

    def ny_issue(self, body, tittel=v.TITTEL):
        self.nr += 1
        self.logg.append(("ny", self.nr, body, tittel))
        self.apne[tittel] = {"number": self.nr, "title": tittel, "created_at": na.isoformat(), "updated_at": na.isoformat()}
        return {"number": self.nr}

    def lukk(self, nr):
        self.logg.append(("lukk", nr, None))
        self.apne = {t: i for t, i in self.apne.items() if i["number"] != nr}


# 7.3: issuen. Ny med egen tittel og timene i teksten, høyst én kommentar i døgnet, lukkes når avviket er borte,
# og blir stående når sjekken ikke kunne gjøres. Issuen «Varselet står stille» røres ikke.
staar = {"number": 7, "title": v.TITTEL, "created_at": na.isoformat(), "updated_at": na.isoformat()}
gh = FalskGitHub2({v.TITTEL: dict(staar)})
assert v.vakt_lyngen(gh, [], [], na) == ("i orden", None) and gh.logg == []
assert v.vakt_lyngen(gh, [], ["russelv"], na) == ("ukjent", None) and gh.logg == []
assert v.vakt_lyngen(gh, avvik, [], na, run="abc123") == ("ny", 42)
kind, nr, body, tittel = gh.logg[0]
assert tittel == v.LYNGEN_TITTEL and "26.11 kl. 06Z: Breivikeidet 3 poeng (0,8 m), Russelv «Treffer ikke» (0 poeng, 0,2 m)" in body, body
assert "26.11 kl. 05Z: Breivikeidet 2 poeng (0,7 m), Lenangsøyra «Flatt» (0 poeng, 0,1 m)" in body and "abc123" in body and "endrer ikke ratingen" in body
assert v.vakt_lyngen(gh, avvik, [], na + dt.timedelta(hours=18)) == ("dedupe", 42) and len(gh.logg) == 1
assert v.vakt_lyngen(gh, avvik, [], na + dt.timedelta(hours=24)) == ("kommentert", 42) and gh.logg[-1][0] == "kommentar" and gh.logg[-1][1] == 42
assert sum(1 for x in gh.logg if x[0] == "ny") == 1
# ukjent lukker ikke, heller ikke når den andre spoten er i orden
assert v.vakt_lyngen(gh, [], ["lenangsoyra"], na + dt.timedelta(hours=30)) == ("ukjent", 42) and v.LYNGEN_TITTEL in gh.apne
assert v.vakt_lyngen(gh, [], [], na + dt.timedelta(hours=36)) == ("lukket", 42)
assert [x[0] for x in gh.logg[-2:]] == ["kommentar", "lukk"] and v.LYNGEN_TITTEL not in gh.apne
assert gh.apne == {v.TITTEL: staar} and not any(x[1] == 7 for x in gh.logg), "«Varselet står stille» er ikke rørt"
# mange timer: høyst LYNGEN_MAKS_LINJER linjer, resten telles
mange = [dict(avvik[0], t=f"2026-11-26T{t:02d}:00Z") for t in range(5, 23)]
assert v.lyngen_tekst(mange, na).count("\n- ") == v.LYNGEN_MAKS_LINJER + 1 and "og 6 time(r) til" in v.lyngen_tekst(mange, na)
# vakt() bruker fortsatt sin egen tittel og ser ikke Lyngen-issuen
gh = FalskGitHub2({v.LYNGEN_TITTEL: {"number": 9, "title": v.LYNGEN_TITTEL, "created_at": na.isoformat(), "updated_at": na.isoformat()}})
assert v.vakt(gh, {"generated": (na - dt.timedelta(hours=1)).isoformat()}, ok, na) == ("i orden", None) and gh.logg == []
print("7.3: egen issue «Lyngen henger ikke sammen», én kommentar i døgnet, lukkes når avviket er borte, ukjent lukker ikke - OK")

# 7.4: lesingen. Tre detaljfiler, ett forsøk hver. En fil som feiler er ukjent (None), de andre leses.
hentet = []
def get_spot(url, params=None, headers=None, timeout=None):
    hentet.append((url, timeout))
    if url.endswith("/russelv.json"):
        raise v.requests.ConnectionError("nede")
    navn = url.rsplit("/", 1)[1][:-5]
    return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: {"breivikeidet": bre, "lenangsoyra": len_}[navn]})()
les = v.les_lyngen(na, get=get_spot)
assert [u for u, _ in hentet] == [v.LIVE_SPOT.format(id=i) for i in ("breivikeidet", "russelv", "lenangsoyra")] and all(t <= 15 for _, t in hentet)
assert les == {"breivikeidet": bre, "russelv": None, "lenangsoyra": len_}
a4, u4 = v.lyngen_avvik(les, na)
assert u4 == ["russelv"] and [(x["t"], x["spot"]) for x in a4] == [(T(5), "lenangsoyra")]
print("7.4: detaljfilene leses én gang hver, en fil som feiler er ukjent - OK")
# 7.5: main() kjører Lyngen-sjekken til slutt, bare når live-siden svarte, og en feil i den stopper ikke vakthunden.
import tempfile
ekte = (v.GitHub, v.les_oversikt, v.les_lyngen, list(sys.argv))
os.environ.update(GITHUB_REPOSITORY="x/y", GITHUB_TOKEN="t")
os.environ.pop("VAKTHUND_TEST_ALDER_T", None)
gh_main = FalskGitHub2()
gh_main.kjoringer = lambda: ok
v.GitHub = lambda repo, token: gh_main
naa = dt.datetime.now(dt.timezone.utc)
om1t = (naa + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00Z")
filer = {"breivikeidet": fil("Breivikeidet", [(om1t, time(stars=2, surf_height=0.7))]), "russelv": fil("Russelv", [(om1t, time(low_reason="flat"))]),
         "lenangsoyra": fil("Lenangsøyra", [(om1t, time(stars=1, surf_height=0.7))])}
lest = []
v.les_oversikt = lambda now: {"generated": now.isoformat()}
v.les_lyngen = lambda now, get=None: lest.append(1) or filer
with tempfile.TemporaryDirectory() as mappe:
    sys.argv = ["vakthund.py", os.path.join(mappe, "tilstand.json")]
    v.main()
    assert [(x[0], x[3]) for x in gh_main.logg] == [("ny", v.LYNGEN_TITTEL)] and "Russelv «Flatt»" in gh_main.logg[0][2], gh_main.logg
    # live-siden svarte ikke: «Varselet står stille» meldes som før, og Lyngen-sjekken kjøres ikke (ukjent, ingen alarm)
    gh_main.logg.clear(); gh_main.apne.clear(); lest.clear()
    v.les_oversikt = lambda now: None
    v.main()
    assert lest == [] and [(x[0], x[3]) for x in gh_main.logg] == [("ny", v.TITTEL)], gh_main.logg
    # en feil i sjekken stopper ikke vakthunden
    gh_main.logg.clear(); gh_main.apne.clear()
    v.les_oversikt = lambda now: {"generated": now.isoformat()}
    def les_krasj(now, get=None):
        raise RuntimeError("uventet")
    v.les_lyngen = les_krasj
    v.main()
    assert gh_main.logg == []
v.GitHub, v.les_oversikt, v.les_lyngen, sys.argv = ekte[0], ekte[1], ekte[2], ekte[3]
os.environ.pop("GITHUB_REPOSITORY", None); os.environ.pop("GITHUB_TOKEN", None)
print("7.5: main() kjører Lyngen-sjekken, ikke når live-siden er nede, og en feil i den stopper ikke vakthunden - OK")
print("Alle tester ok")
