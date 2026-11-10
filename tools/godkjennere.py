"""Hvem som kan godkjenne posisjoner og bygde spots i spotfabrikken (én liste for bygg_spot, godkjenn_spot og
importer_godkjenning).

- «theodor»: setter posisjoner selv i koordinatsjekk; en CSV kan aldri skrive hans navn.
- CLAUDE: gjennomgangen av Lofoten og Vesterålen var delegert til Claude i chatten (Theodor 16.10.2026, punkt 8).
  Beholdt for historikken i posisjoner.json.
- SPOTANSVARLIG: fra 10.11.2026 går subagenten spotansvarlig gjennom nye spots før hver region-PR (CLAUDE.md,
  «Arbeidsmåte»). Theodor beholder ja/nei til merge av region-PR-ene."""
CLAUDE = "claude (delegert av Theodor 16.10.2026)"
SPOTANSVARLIG = "spotansvarlig (agent, Theodor 10.11.2026)"
FRA_CSV = {CLAUDE, SPOTANSVARLIG}          # det en CSV kan gi som satt_av
GODKJENNERE = {"theodor"} | FRA_CSV
