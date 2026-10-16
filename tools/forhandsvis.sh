#!/usr/bin/env bash
# Forhåndsvisning lokalt (Theodor 16.10.2026, mens GitHub-kontoen er suspendert):
# kjører en prøvehenting som «Prøvehenting (gren)»-workflowen (fetch.py + publish.py, ingen varsler, ingen
# commit, ingen issue) og serverer appen på http://127.0.0.1:<port>.
#
# Alt havner i forhandsvis/ (gitignorert):
#   forhandsvis/kopi/   midlertidig kopi av repoet (git-sporede filer slik de står i arbeidstreet) - henteren
#                       kjører HER, så data/ og docs/data/ i arbeidstreet røres aldri
#   forhandsvis/side/   docs/ fra kopien + de ferske datafilene - det som serveres
#   forhandsvis/henting.log
#
# Nøkler brukes ALDRI lokalt: BW_*, NTFY_TOPIC, APP_URL, LOGS_* fjernes fra miljøet før henteren starter.
# Uten BarentsWatch-nøkler mangler BarentsWatch-feltene (None, vises som manglende - aldri 0), og ratingen
# bruker reservemodellen (svell ute × transfer × eksponering). Loggene (privat repo) hentes heller ikke.
#
# Bruk:
#   bash tools/forhandsvis.sh                 hent (maks 20 min) og server på port 8780
#   bash tools/forhandsvis.sh --port 8790     annen port
#   bash tools/forhandsvis.sh --bare-server   hopp over hentingen, server forrige henting
#   bash tools/forhandsvis.sh --bare-hent     hent, men ikke start serveren
# Miljø: FORHANDSVIS_TIDSGRENSE (sekunder, standard 1200), NORDSURF_PYTHON (standard python3),
#        UA_CONTACT (kontakt i User-Agent mot met.no, valgfri).
# Ctrl-C stopper serveren.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UT="$ROOT/forhandsvis"
PORT=8780
HENT=1
SERVER=1
TIDSGRENSE="${FORHANDSVIS_TIDSGRENSE:-1200}"
PY="${NORDSURF_PYTHON:-python3}"

while [ $# -gt 0 ]; do
  case "$1" in
    --bare-server) HENT=0 ;;
    --bare-hent) SERVER=0 ;;
    --port) PORT="${2:?--port trenger et tall}"; shift ;;
    --port=*) PORT="${1#--port=}" ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "Ukjent valg: $1 (se --help)" >&2; exit 2 ;;
  esac
  shift
done

# kjør en kommando med tidsgrense (macOS har ikke timeout(1)); exit 142 = tidsgrensen nådd
med_tidsgrense() { local s="$1"; shift; perl -e 'alarm shift @ARGV; exec @ARGV or die "kan ikke starte: $!\n"' "$s" "$@"; }

if [ "$HENT" = 1 ]; then
  if ! git -C "$ROOT" check-ignore -q "$UT/x"; then
    echo "FEIL: forhandsvis/ er ikke gitignorert - stopper for ikke å skitne til arbeidstreet." >&2
    exit 1
  fi
  echo "== Forhåndsvisning: kopierer repoet til forhandsvis/kopi (git-sporede filer) =="
  rm -rf "$UT/kopi" "$UT/side.ny"
  mkdir -p "$UT/kopi"
  (cd "$ROOT" && git ls-files -z | tar --null -T - -cf -) | tar -xf - -C "$UT/kopi"
  # ferske datafiler skal komme fra denne hentingen, ikke fra noe som lå igjen
  rm -rf "$UT/kopi/docs/data/forecast.json" "$UT/kopi/docs/data/oversikt.json" "$UT/kopi/docs/data/spots"

  echo "== Henter varselet (tidsgrense ${TIDSGRENSE} s, ingen nøkler, ingen varsler) - logg: forhandsvis/henting.log =="
  start=$(date +%s)
  set +e
  (cd "$UT/kopi" && env -u BW_CLIENT_ID -u BW_CLIENT_SECRET -u BW_POINT_URL -u BW_DEBUG \
       -u NTFY_TOPIC -u APP_URL -u LOGS_REPO -u LOGS_TOKEN \
       -u GITHUB_OUTPUT -u GITHUB_STEP_SUMMARY -u GITHUB_ACTIONS -u NORDSURF_NOW \
       PYTHONWARNINGS=ignore \
       perl -e 'alarm shift @ARGV; exec @ARGV or die "kan ikke starte: $!\n"' "$TIDSGRENSE" \
       "$PY" fetcher/fetch.py) >"$UT/henting.log" 2>&1
  rc=$?
  set -e
  tid=$(( $(date +%s) - start ))
  if [ "$rc" = 142 ]; then
    echo "FEIL: hentingen nådde tidsgrensen på ${TIDSGRENSE} s og ble stoppet. Se forhandsvis/henting.log." >&2
    tail -n 20 "$UT/henting.log" >&2; exit 1
  elif [ "$rc" != 0 ]; then
    echo "FEIL: henteren feilet (kode $rc) etter ${tid} s. Siste linjer fra forhandsvis/henting.log:" >&2
    tail -n 30 "$UT/henting.log" >&2; exit 1
  fi
  echo "Hentingen tok ${tid} s."

  echo "== Lager appens datafiler (publish.py) =="
  if ! (cd "$UT/kopi" && med_tidsgrense 300 "$PY" fetcher/publish.py) >>"$UT/henting.log" 2>&1; then
    echo "FEIL: publish.py feilet. Se forhandsvis/henting.log." >&2; tail -n 20 "$UT/henting.log" >&2; exit 1
  fi

  cp -R "$UT/kopi/docs" "$UT/side.ny"
  rm -rf "$UT/side"; mv "$UT/side.ny" "$UT/side"

  echo "== Hva som mangler uten nøkler =="
  "$PY" - "$UT/kopi/docs/data/forecast.json" <<'PYEOF'
import json, sys
f = json.load(open(sys.argv[1], encoding="utf-8"))
spots = f.get("spots", [])
timer = [h for s in spots for h in s.get("hours", [])]
bw = sum(1 for h in timer if h.get("bw_height") is not None)
print(f"Varsel laget {f.get('generated')}: {len(spots)} spots, {len(timer)} timer.")
if bw == 0:
    print("BarentsWatch: MANGLER for alle spots (ingen nøkler lokalt). Feltene er tomme (None) og vises som")
    print("  manglende i appen - ratingen bruker reservemodellen (svell ute x transfer x eksponering).")
else:
    print(f"BarentsWatch: {bw} av {len(timer)} timer har data.")
print("Loggene (privat repo, LOGS_REPO) hentes ikke lokalt - ingen nye logger i læringen.")
print("Ingen varsler (ntfy) sendt, ingenting committet.")
PYEOF
fi

if [ "$SERVER" = 0 ]; then exit 0; fi
if [ ! -s "$UT/side/data/oversikt.json" ]; then
  echo "FEIL: ingen tidligere henting i forhandsvis/side - kjør uten --bare-server først." >&2; exit 1
fi
echo
echo "Forhåndsvisning: http://127.0.0.1:${PORT}/   (Ctrl-C stopper serveren)"
exec "$PY" -m http.server "$PORT" --bind 127.0.0.1 --directory "$UT/side"
