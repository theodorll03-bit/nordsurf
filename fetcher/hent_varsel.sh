#!/usr/bin/env bash
# S2 (14.10.2026): varselet ligger ikke lenger i git. Hver «Hent varsel»-kjøring
# laster det opp som artifact «varsel» (forecast.json, oversikt.json, spots/ -
# 7 dagers levetid) og publiserer det via GitHub Pages. Verktøyene som leser
# docs/data/forecast.json (testlaben, vindmålingene, diagnosene) henter det
# NYESTE varselet herfra før de kjører.
#
# Trenger gh med GH_TOKEN (i Actions: github.token med permissions: actions: read).
# Kjør: bash fetcher/hent_varsel.sh   (lokalt: gh må være innlogget)
set -euo pipefail
repo="${GITHUB_REPOSITORY:-theodorll03-bit/nordsurf}"
# bare varsler fra main - en «Hent varsel» kjørt på en annen gren skal aldri ut (fysikk-kontrollør 14.10.2026)
run_id=$(gh api "repos/$repo/actions/artifacts?name=varsel&per_page=50" \
  -q '[.artifacts[] | select(.expired == false and .workflow_run.head_branch == "main")] | .[0].workflow_run.id // empty')
if [ -z "$run_id" ]; then
  echo "Fant ingen artifact «varsel» som ikke er utløpt - har «Hent varsel» lyktes de siste 7 dagene?" >&2
  exit 1
fi
mkdir -p docs/data
rm -rf docs/data/spots docs/data/forecast.json docs/data/oversikt.json
gh run download "$run_id" --repo "$repo" --name varsel --dir docs/data
test -s docs/data/forecast.json && test -s docs/data/oversikt.json
echo "Hentet varselet fra kjøring $run_id ($(python3 -c 'import json; print(json.load(open("docs/data/forecast.json"))["generated"])'))"
