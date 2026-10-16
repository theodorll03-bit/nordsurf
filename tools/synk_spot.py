"""Fører rettinger fra data/kandidater/bygget/<id>.json (tools/rett_bygget.py) inn i en spot som alt ligger i spots.json
(16.10.2026, kontrollørens funn i #22 - godkjenn_spot.py legger bare inn nye spots). spots.json er håndformatert, så
bare de navngitte feltene byttes ut som tekst inne i spotens egen blokk; resten av fila sjekkes uendret etterpå.
Bare spots med status «forelopig» kan synkes - de kalibrerte spotene røres aldri herfra.

  python tools/synk_spot.py <id> facing offshore_wind barentswatch_point [_rettet] [--hold-tilbake "<grunn>"] [--tørr]

--hold-tilbake: setter enabled false (spoten hentes og publiseres ikke) med grunnen i «_holdt_tilbake».
Kontrollør 16.10: feltene som ikke finnes i bygget-fila nevnes (ikke hoppet over i det stille), og spoten selv
sjekkes for at bare de navngitte feltene (og notatfeltene deres) er endret."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "spots.json"
BYGGET = ROOT / "data" / "kandidater" / "bygget"
NOTER = {"offshore_wind": "_offshore_vind", "barentswatch_point": "_barentswatch", "ideal_height": "_ideal_height"}


def block(text, sid):
    a = text.index(f'"id": "{sid}"')
    a = text.rindex("\n    {", 0, a) + 1
    b = text.index("\n    }", a) + len("\n    }")
    return a, b


def fmt(v, ind=6):
    pad = " " * ind
    return json.dumps(v, ensure_ascii=False, indent=2).replace("\n", "\n" + pad)


def set_field(blk, key, val):
    m = re.search(rf'\n      "{re.escape(key)}": ', blk)
    if not m:
        # nytt felt: legges inn etter facing (bare for notatfelt som _rettet)
        f = re.search(r'\n      "facing": [^\n]*\n', blk)
        return blk[:f.end()] + f'      "{key}": {fmt(val)},\n' + blk[f.end():]
    start = m.end()
    dec = json.JSONDecoder()
    _, end = dec.raw_decode(blk, start)
    return blk[:start] + fmt(val) + blk[end:]


def opt_hold():
    a = sys.argv
    return next((a[i + 1] for i, x in enumerate(a) if x == "--hold-tilbake" and i + 1 < len(a)), None)


def main():
    hold = opt_hold()
    sid = sys.argv[1]
    fields = [a for a in sys.argv[2:] if not a.startswith("--") and a != hold]
    s = json.loads((BYGGET / f"{sid}.json").read_text(encoding="utf-8"))["spot"]
    text = SPOTS.read_text(encoding="utf-8")
    cur = next(x for x in json.loads(text)["spots"] if x["id"] == sid)
    if cur.get("status") != "forelopig":
        sys.exit(f"{sid} har status {cur.get('status')!r} - bare foreløpige spots synkes herfra")
    a, b = block(text, sid)
    blk = text[a:b]
    allowed = set()
    for f in fields:
        if f not in s:
            print(f"{sid}: feltet {f} finnes ikke i bygget-fila - ikke endret")
        for k in (f, NOTER.get(f)):
            if k and k in s:
                blk = set_field(blk, k, s[k])
                allowed.add(k)
    if opt_hold():
        blk = set_field(blk, "enabled", False)
        blk = set_field(blk, "_holdt_tilbake", opt_hold())
        allowed |= {"enabled", "_holdt_tilbake"}
    new = text[:a] + blk + text[b:]
    after = json.loads(new)
    before = json.loads(text)
    assert [x for x in after["spots"] if x["id"] != sid] == [x for x in before["spots"] if x["id"] != sid], "andre spots endret"
    assert {k: v for k, v in after.items() if k != "spots"} == {k: v for k, v in before.items() if k != "spots"}
    ny = next(x for x in after["spots"] if x["id"] == sid)
    diff = {k: (cur.get(k), ny.get(k)) for k in set(cur) | set(ny) if cur.get(k) != ny.get(k)}
    assert set(diff) <= allowed, f"andre felt enn de navngitte ble endret: {sorted(set(diff) - allowed)}"
    for k, (o, n) in sorted(diff.items()):
        print(f"{sid}.{k}: {json.dumps(o, ensure_ascii=False)[:120]} → {json.dumps(n, ensure_ascii=False)[:120]}")
    if "--tørr" not in sys.argv:
        SPOTS.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    main()
