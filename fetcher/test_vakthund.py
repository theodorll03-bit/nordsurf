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
# 4. åpen issue: innen 6 t ingen ny kommentar; etter 6 t kommentar (aldri en ny issue)
assert v.vakt(gh, gammel, to_feil, now + dt.timedelta(hours=5))[0] == "dedupe" and len(gh.logg) == 1
assert v.vakt(gh, gammel, to_feil, now + dt.timedelta(hours=6))[0] == "kommentert" and gh.logg[-1][0] == "kommentar" and gh.logg[-1][1] == nr
assert sum(1 for x in gh.logg if x[0] == "ny") == 1
# 5. ferskt igjen: kommentar og lukking
senere = now + dt.timedelta(hours=9)
assert v.vakt(gh, {"generated": (senere - dt.timedelta(hours=1)).isoformat()}, ok, senere) == ("lukket", nr)
assert [x[0] for x in gh.logg[-2:]] == ["kommentar", "lukk"] and gh.apen is None
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
assert v.ntfy(["x"], now + dt.timedelta(hours=5), st, post) is False and len(sendt) == 1
assert v.ntfy(["x"], now + dt.timedelta(hours=6), st, post) is True and len(sendt) == 2
os.environ.pop("NTFY_TOPIC", None)
print("6: ntfy bare med NTFY_TOPIC, maks hver 6. time - OK")
print("Alle tester ok")
