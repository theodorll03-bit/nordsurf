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
print("Alle tester ok")
