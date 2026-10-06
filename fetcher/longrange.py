"""Langtidsvarsel 16 dager med sikkerhet i prosent (ROADMAP oppgave B, 06.10.2026).

Tre soner per time (se zone_for()): "barentswatch" (ekte kystmodell, til
bw_until), "reserve" (reservemodellen svell ute x transfer x eksponering, til
og med dag 7) og "langtid" (dag 8-16, bare GFS Wave og GFS-vind). Dag 8-16
lagres hver 6. time (keep_row()) - timesverdier for 16 dager x 8 spots ville
gitt ca. 5,9 MB forecast.json mot 1,6 MB i dag (målt 06.10.2026); hver 6.
time holder den rundt 2,2 MB.

Sikkerheten er SANNSYNLIGHETEN FOR TREFF INNENFOR ÉN STJERNE for et antall
dager frem, i prosent - den kapper ALDRI stjernene (Theodor: "sikkerhet i
prosent per dag, ikke kapping av stjerner"). Startverdiene (CONFIDENCE_START,
merket "anslag") byttes ut med målt treffprosent ("målt") for en spot så
snart den har minst MIN_SCORED sammenligninger for det antallet dager frem.

Målingen (score_runs()): hver kjøring arkiveres (write_archive(), små filer:
bare stjerner og surfehøyde per rad). "Fasit" for en time T er varselet laget
under 6 timer før T - i praksis denne kjøringens egne rader i vinduet
[forrige scoring-grense, nå + 3 timer), siden henteren kjører hver 3. time -
pluss loggene (Theodors egne stjerner, den beste fasiten der de finnes).
Hvert arkivert varsel laget minst SCORE_SLOT_HOURS (3) timer før T sammenlignes
mot fasiten og telles i bøtta for riktig antall dager frem - den grensa er bare
der for å hindre at en kjøring teller sitt EGET, nettopp skrevne arkiv mot seg
selv (alltid under SCORE_SLOT_HOURS unna egne rader), ikke for å utelate dag 1
(0-24 t, se day_index()) - en tidligere versjon brukte 24 t her, som gjorde dag
1 umulig å måle (06.10.2026, fysikk-kontrollør sitt funn, se STATUS.md).
last_scored_until sørger for at ingen (arkiv, time)-par telles to ganger. Arkiv
eldre enn ARCHIVE_DAYS slettes.
"""
import json
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT / "data" / "forecast_archive"
LEDGER = ROOT / "data" / "forecast_accuracy.json"

DAYS = 16
HOURS = DAYS * 24
RESERVE_LAST_DAY = 7      # dag 8 og utover er "langtid"
LONGRANGE_STEP_HOURS = 6  # dag 8-16 lagres bare hver 6. time
MIN_SCORED = 30           # minst så mange sammenligninger før "målt" brukes
HIT_WITHIN_STARS = 1
NOTIFY_MIN_CONFIDENCE = 70  # varsler bare for timer med minst dette (notify.py)
ARCHIVE_DAYS = DAYS + 1
SCORE_SLOT_HOURS = 3      # henteren kjører hver 3. time - fasit-vinduet per kjøring

# Theodors startverdier: sannsynlighet for treff innenfor én stjerne.
CONFIDENCE_START = {1: 90, 2: 85, 3: 80, 4: 70, 5: 65, 6: 55, 7: 55,
                    8: 40, 9: 40, 10: 40, 11: 30, 12: 30, 13: 30, 14: 30, 15: 30, 16: 30}


def day_index(now, t):
    """1 for de første 24 timene fra nå, 2 for de neste 24, osv."""
    return int((t - now).total_seconds() // 3600 // 24) + 1


def zone_for(height_source, day):
    if height_source == "barentswatch":
        return "barentswatch"
    return "reserve" if day <= RESERVE_LAST_DAY else "langtid"


def keep_row(t, day):
    """Timesverdier til og med dag 7, deretter bare hver 6. time (00/06/12/18Z)."""
    return day <= RESERVE_LAST_DAY or t.hour % LONGRANGE_STEP_HOURS == 0


def start_confidence(day):
    return CONFIDENCE_START.get(day, CONFIDENCE_START[DAYS])


def confidence_for(ledger, spot_id, day):
    """(prosent, 'målt' eller 'anslag'). Målt bare med minst MIN_SCORED
    sammenligninger for akkurat dette antallet dager frem."""
    b = (ledger.get("spots", {}).get(spot_id, {}) or {}).get(str(day))
    if b:
        n, hits = b.get("n", 0) + b.get("n_logs", 0), b.get("hits", 0) + b.get("hits_logs", 0)
        if n >= MIN_SCORED:
            return round(100 * hits / n), "målt"
    return start_confidence(day), "anslag"


def load_ledger(path=None):
    p = path or LEDGER
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"last_scored_until": None, "scored_logs": [], "spots": {}}


def save_ledger(ledger, path=None):
    p = path or LEDGER
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")


def run_key(now):
    return now.strftime("%Y-%m-%dT%H")


def write_archive(now, spots, archive_dir=None):
    """Liten fil per kjøring: {spot: {t: [stjerner, surfehøyde]}}."""
    d = archive_dir or ARCHIVE_DIR
    d.mkdir(parents=True, exist_ok=True)
    payload = {"issued": now.isoformat(), "spots": {
        s["id"]: {h["t"]: [h["stars"], h.get("surf_height")] for h in s["hours"]} for s in spots}}
    (d / f"{run_key(now)}.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def prune_archives(now, archive_dir=None):
    d = archive_dir or ARCHIVE_DIR
    if not d.exists():
        return 0
    removed = 0
    for f in d.glob("*.json"):
        try:
            issued = dt.datetime.strptime(f.stem, "%Y-%m-%dT%H").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        if now - issued > dt.timedelta(days=ARCHIVE_DAYS):
            f.unlink()
            removed += 1
    return removed


def _load_archives(archive_dir):
    out = []
    if not archive_dir.exists():
        return out
    for f in sorted(archive_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            issued = dt.datetime.fromisoformat(data["issued"])
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
        out.append((issued, data["spots"]))
    return out


def _bump(ledger, spot_id, day, hit, from_log=False):
    b = ledger.setdefault("spots", {}).setdefault(spot_id, {}).setdefault(str(day), {"n": 0, "hits": 0, "n_logs": 0, "hits_logs": 0})
    if from_log:
        b["n_logs"] += 1
        b["hits_logs"] += int(hit)
    else:
        b["n"] += 1
        b["hits"] += int(hit)


def _parse_t(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00"))


def score_runs(now, spots, logs, ledger, archive_dir=None):
    """Sammenlign eldre arkiverte varsel mot (a) denne kjøringens rader i
    fasit-vinduet og (b) loggene. Oppdaterer ledger på plass, returnerer
    antall nye sammenligninger (a, b)."""
    archives = _load_archives(archive_dir or ARCHIVE_DIR)
    if not archives:
        return 0, 0
    scored_a = scored_b = 0

    # (a) fasit = denne kjøringens rader, vinduet [forrige grense, nå + 3 t)
    prev = ledger.get("last_scored_until")
    start = max(now, dt.datetime.fromisoformat(prev)) if prev else now
    end = now + dt.timedelta(hours=SCORE_SLOT_HOURS)
    truth = {s["id"]: {h["t"]: h["stars"] for h in s["hours"] if start <= _parse_t(h["t"]) < end} for s in spots}
    for issued, arch_spots in archives:
        for sid, rows in truth.items():
            arch = arch_spots.get(sid) or {}
            for t, stars_now in rows.items():
                tt = _parse_t(t)
                # 06.10.2026, fysikk-kontrollør sitt funn: vakten her skal
                # bare hindre at DENNE kjøringens eget arkiv (skrevet rett
                # før dette kalles, issued==now) telles mot seg selv - IKKE
                # kreve et helt døgns avstand. Et døgn er logisk disjunkt
                # fra dag 1 sin egen definisjon (0-24 t, se day_index()):
                # ingen (issued, tt) kunne noensinne være BÅDE under 24 t
                # (for å telle som dag 1) OG minst 24 t (for å passere
                # vakten) - dag 1 kunne derfor ALDRI bli "målt", uansett
                # hvor mye data som samlet seg. SCORE_SLOT_HOURS (samme 3 t
                # som henteren sin egen kjøretakt) er nok til å skille denne
                # kjøringens FERSKE arkiv (alltid under SCORE_SLOT_HOURS
                # unna egne sannhets-rader) fra et EKTE, eldre arkiv (minst
                # én kjøring gammelt) - uten å spise opp hele dag 1.
                if tt - issued < dt.timedelta(hours=SCORE_SLOT_HOURS) or t not in arch:
                    continue
                day = day_index(issued, tt)
                if 1 <= day <= DAYS:
                    _bump(ledger, sid, day, abs(arch[t][0] - stars_now) <= HIT_WITHIN_STARS)
                    scored_a += 1
    ledger["last_scored_until"] = end.isoformat()

    # (b) fasit = loggene (Theodors egne stjerner), hver logg telles én gang
    scored_ids = set(ledger.get("scored_logs", []))
    for log in logs or []:
        lid, sid, stars = log.get("id"), log.get("spot"), log.get("stars")
        if not lid or lid in scored_ids or stars is None or not log.get("t"):
            continue
        try:
            tt = _parse_t(log["t"]).replace(minute=0, second=0, microsecond=0)
        except ValueError:
            continue
        key = tt.strftime("%Y-%m-%dT%H:00Z")
        matched = False
        for issued, arch_spots in archives:
            # Samme rettelse som i (a) over - se kommentaren der.
            if tt - issued < dt.timedelta(hours=SCORE_SLOT_HOURS):
                continue
            row = (arch_spots.get(sid) or {}).get(key)
            if row is None:
                continue
            day = day_index(issued, tt)
            if 1 <= day <= DAYS:
                _bump(ledger, sid, day, abs(row[0] - stars) <= HIT_WITHIN_STARS, from_log=True)
                scored_b += 1
                matched = True
        if matched or tt < now - dt.timedelta(days=ARCHIVE_DAYS):
            scored_ids.add(lid)  # ferdig, eller for gammel til noen gang å matche
    ledger["scored_logs"] = sorted(scored_ids)
    return scored_a, scored_b


def accuracy_table(ledger, spot_id):
    """Til Logger-fanen: én rad per antall dager frem."""
    rows = []
    for day in range(1, DAYS + 1):
        pct, src = confidence_for(ledger, spot_id, day)
        b = (ledger.get("spots", {}).get(spot_id, {}) or {}).get(str(day), {})
        rows.append({"day": day, "pct": pct, "source": src,
                     "n": b.get("n", 0) + b.get("n_logs", 0), "n_logs": b.get("n_logs", 0)})
    return rows
