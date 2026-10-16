"""Test av vakthunden (fetcher/vakthund.py) uten nett. Kjør: python fetcher/test_vakthund.py"""
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
en_feil = [{"conclusion": "failure", "created_at": "x"}, {"conclusion": "success"}]
to_feil = [{"conclusion": "failure", "created_at": "x"}, {"conclusion": "failure", "created_at": "y"}]

assert v.problemer(fersk, ok, now) == [], "ferskt varsel skal ikke gi varsel"
assert len(v.problemer(gammel, ok, now)) == 1 and "8 timer" in v.problemer(gammel, ok, now)[0]
assert v.problemer(fersk, en_feil, now) == [], "én feil skal ikke gi varsel"
assert len(v.problemer(fersk, to_feil, now)) == 1 and "2 ganger på rad" in v.problemer(fersk, to_feil, now)[0]
assert v.problemer(None, None, now) and v.problemer({}, None, now), "uleselig/manglende generated er et problem, aldri «i orden»"
assert v.problemer(fersk, None, now) == [], "kjøringene ukjent: ingen falsk alarm"
print("1: ferskt/8 t gammelt/én feil/to feil på rad/uleselig - OK")

sendt = []
post = lambda url, json=None, timeout=None: sendt.append(json) or type("R", (), {"raise_for_status": lambda s: None})()
os.environ.pop("NTFY_TOPIC", None)
state = {}
assert v.varsle(["x"], now, state, post) is False and not sendt and "sendt" not in state, "uten NTFY_TOPIC: bare logget"
os.environ["NTFY_TOPIC"] = "test"
assert v.varsle(["x"], now, state, post) is True and len(sendt) == 1 and state.get("sendt")
assert v.varsle(["x"], now + dt.timedelta(hours=5), state, post) is False and len(sendt) == 1, "innen 6 t: ikke på nytt"
assert v.varsle(["x"], now + dt.timedelta(hours=6), state, post) is True and len(sendt) == 2, "etter 6 t: på nytt"
feil = lambda url, json=None, timeout=None: (_ for _ in ()).throw(RuntimeError("ntfy nede"))
st2 = {}
assert v.varsle(["x"], now, st2, feil) is False and "sendt" not in st2, "sendefeil: ingen tilstand, prøv igjen neste gang"
os.environ.pop("NTFY_TOPIC", None)
print("2: dedupe 6 t, ingen NTFY_TOPIC → bare logg, sendefeil gir ingen tilstand - OK")
print("Alle tester ok")
