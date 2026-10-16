# Nordsurf sitt fotavtrykk på GitHub - tall og forslag

*Skrevet 16.10.2026, etter at GitHub-kontoen ble suspendert (anke sendt samme dag). Dette er bare et FORSLAG: ingen workflow-fil er endret. Alt under krever Theodors ja før det bygges, se siste del.*

Målet er at repoet ser ut og oppfører seg som et vanlig, lite hobbyprosjekt: få commits fra automatikk, få og samlede PR-er, få Actions-kjøringer og lite trafikk mot GitHub sitt API, uten å miste varselkvalitet eller læringsdata.

## 1. Hva som er telt og hva som er anslått

- **Telt** (fra lokal git, `git log --all`, alle lokale grener og `origin/*`-refs slik de sto ved siste henting 16.10 kl. 13:33): commits per døgn, forfatter og melding, merge-commits og PR-numre i meldingene. Døgnene er norsk tid (Europe/Oslo), 03.10-16.10.2026 (14 døgn).
- **Telt, men bare for 15.-16.10:** push fra denne maskinen (reflog for `refs/remotes/origin/*`, «update by push»). Klonen er fra 15.10, så eldre push (fra skyøkter og andre maskiner) finnes ikke lokalt.
- **Anslått:** Actions-kjøringer. Planlagte kjøringer er regnet fra cron-uttrykkene i `.github/workflows/*.yml` og datoen workflowen kom inn på main. Push-utløste kjøringer er anslått fra antall push. Den ekte kjøringslista ligger bare hos GitHub og er ikke tilgjengelig nå.
- **Ikke med:** commits som aldri er hentet lokalt (f.eks. bot-commits etter 16.10 kl. 13:33) og commits i det private loggrepoet.
- Bot-commits er gjenkjent på forfatteren `nordsurf-bot` og meldingene «Nytt varsel», «Nytt varsel (læringsdata)», «Finn BarentsWatch-punkt: nytt søk», «Testlab: ny kjøring», «KystVær-sondering: resultat», «WAM800-utforsking: ny rapport», «Vindmålinger (Frost): ny henting» og «Steinkrøssa: nytt BarentsWatch-snitt på en svelldag». Alt annet regnes som «for hånd» (Theodor, Claude-økter og squash-merger i GitHub sitt nettgrensesnitt).

## 2. Tallene

### Commits per døgn (alle refs, telt)

| Døgn | Totalt | Bot | herav «Nytt varsel» | Bot om natten (23-06) | For hånd | Merget PR (squash) | Andre merge-commits («Synk main inn i …») |
|---|---:|---:|---:|---:|---:|---|---:|
| 03.10 | 6 | 5 | 5 | 2 | 1 | - | 0 |
| 04.10 | 8 | 5 | 5 | 3 | 3 | - | 0 |
| 05.10 | 14 | 7 | 7 | 3 | 7 | - | 0 |
| 06.10 | 15 | 9 | 7 | 2 | 6 | - | 0 |
| 07.10 | 73 | 24 | 10 | 5 | 49 | - | 0 |
| 08.10 | 10 | 8 | 8 | 3 | 2 | - | 0 |
| 09.10 | 28 | 9 | 9 | 4 | 19 | #2, #3 | 2 |
| 10.10 | 14 | 9 | 9 | 3 | 5 | - | 0 |
| 11.10 | 8 | 8 | 8 | 3 | 0 | - | 0 |
| 12.10 | 9 | 9 | 8 | 3 | 0 | - | 0 |
| 13.10 | 9 | 8 | 8 | 3 | 1 | - | 0 |
| 14.10 | 30 | 11 | 10 | 4 | 19 | #4, #6 | 3 |
| 15.10 | 56 | 7 | 6 | 2 | 49 | #7, #8 (antatt: «Legg inn logg», uten nummer i meldingen), #9, #10, #11, #12, #13, #14 | 8 |
| 16.10 | 114 | 8 | 3 | 0 | 106 | #15-#21, #24 | 14 |
| **Sum** | **394** | **127** | **103** | **40** | **267** | **20 PR-er** | **27** |

Merknader:
- «Nytt varsel» ligger fast på ca. 8 per døgn (én per «Hent varsel»-kjøring) helt til S2 (14.10). Etter S2 committes ikke varselet lenger, men læringsdataene committes fortsatt i hver kjøring («Nytt varsel (læringsdata)») - altså fortsatt ca. 8 bot-commits per døgn. Lave tall 15.-16.10 skyldes at «Hent varsel» feilet 15.10 kl. 19Z-16.10 ca. 09Z (PR #19) og at lokal git ikke har noe etter 13:33.
- Andre bot-commits på 14 døgn: «Finn BarentsWatch-punkt» 9 (5 av dem 16.10), Testlab 7, KystVær-sondering 5, WAM800 2, Steinkrøssa-snitt 1.
- PR-numre som er nevnt i meldinger i perioden: #2-#4, #6, #7, #9-#28 (25 numre). 8 PR-er ble merget både 15.10 og 16.10.
- **Direkte commits på main for hånd** (første forelder, uten bot): 07.10: 30, 06.10: 15, 15.10: 11, 16.10: 26. Mye av arbeidet har gått rett på main, i små biter (STATUS-oppdateringer, rettelser).
- Forfattere i perioden: Theodor Lund 187 (185 av dem med e-post `<bruker>@<maskinnavn>.local`, som ikke er koblet til noen GitHub-konto), nordsurf-bot 135, Claude 62 (som forfatter, ikke bare medforfatter), theodorll03-bit 20 (squash-merger i nettgrensesnittet).

### Push (telt, bare 15.-16.10 fra denne maskinen)

| Døgn | Push totalt | herav til main | Grener det ble pushet til |
|---|---:|---:|---:|
| 15.10 | 8 | - | - |
| 16.10 | 70 | 21 | 18 (15.-16.10 samlet) |

Mest pushet 16.10: main 21, region/lofoten-vesteralen 12, s3/maplibre 9, spotfabrikken/s6/drift-vakthund 5 hver. Det finnes 34 grener på origin.

### Actions-kjøringer (anslått)

Planlagte kjøringer fra cron (UTC):

| Workflow | Cron | Kjøringer per døgn | På main siden | Kjøringer 03.-16.10 (anslag) |
|---|---|---:|---|---:|
| forecast.yml («Hent varsel») | `17 */3 * * *` | 8 (fra 16.10: 6 jobber per kjøring - forjobb, 3 regioner, samle, publiser) | 24.09 | 112 |
| vakthund.yml | `47 1-23/3 * * *` | 8 | 16.10 | høyst 8 |
| backtest.yml | `17 7 * * *` + `41 5 * * 1` | 1 + 1 per uke | 07.10 (daglig fra 15.10) | ca. 3 |
| wind_obs.yml | `23 3 * * *` | 1 | 07.10 | ca. 9 |
| **Sum planlagt** | | **ca. 18 per døgn i dag** | | **ca. 130** |

Push-utløste kjøringer:

| Workflow | Utløser | Anslag |
|---|---|---|
| test.yml | **hver push til hver gren** og i tillegg hver PR-oppdatering (`push` + `pull_request` - samme commit testes to ganger når grenen har en åpen PR). Ca. 5-8 min med Playwright og full klon (`fetch-depth: 0`, ca. 110 MB) | 16.10: ca. 70 push-kjøringer + anslagsvis 30-40 PR-kjøringer, altså ca. 100-110 kjøringer på ett døgn. Bot-push med `GITHUB_TOKEN` utløser ikke nye kjøringer. |
| publiser.yml | push til main som endrer `docs/**` | 16.10: 5 av 30 commits på main rørte docs/ utenom data, så ca. 5 |
| provehent.yml (bare på region/lofoten-vesteralen, ikke på main) | push til `region/**` som endrer spots.json | hver slik push = en full henting mot met.no, BarentsWatch og Open-Meteo |
| kystvaer_probe.yml | push til sky/testlab | 5 (telt via bot-commits) |
| Manuelle (find_bw_point, testlab, wam800 m.fl.) | workflow_dispatch | minst 9 + 7 + 2 (telt via bot-commits) |

Rolig døgn (11.-13.10): ca. 9-10 kjøringer, 8-9 commits, ingen PR. Travelt døgn (16.10): ca. 120-140 kjøringer, 114 commits, 70 push, 8 PR-er merget. Det er de travle døgnene som skiller seg ut, ikke henteren.

### Størrelsen på repoet (telt)

`git count-objects -vH`: 136 MiB i pakken + 124 MiB løse objekter, `.git` er 270 MB lokalt (ca. 110 MB å klone). Fordelt på stier i historikken (størrelse på disk etter komprimering og delta):

| Del av historikken | Objekter | Rå størrelse | På disk | Andel |
|---|---:|---:|---:|---:|
| docs/design/ (skjermbilder fra nettlesertestene og designrundene) | ca. 950 | | ca. 170 MB | ca. 63 % |
| docs/geo/*.pmtiles (kartfliser) | 4 | | ca. 61 MB | ca. 23 % |
| docs/data/forecast.json (181 versjoner, til S2) | 181 | 340 MB | 16,7 MB | 6 % |
| data/ i alt (kandidater 8 MB, resten under 1 MB) | ca. 550 | ca. 24 MB | ca. 8,8 MB | 3 % |
| herav data/forecast_archive, bw_calibration, forecast_accuracy, exposure | ca. 310 | 5,6 MB | under 0,3 MB | 0,1 % |
| fetcher/, tools/, rot-filer, trær og commits | | | ca. 7 MB | 3 % |

Konklusjon: de automatiske datafilene er små og komprimerer godt. Det er **skjermbildene** og **kartflisene** som gjør repoet stort, og de kommer fra commits for hånd, ikke fra henteren.

## 3. Forslag

### (a) Varselet som Pages-artefakt i stedet for committet JSON

**Status: allerede gjort for selve varselet** (S2, PR #6, 14.10). `forecast.yml` laster opp `docs/data/forecast.json`, `oversikt.json` og `spots/` som artifact «varsel» (7 dager), og `publiser.yml` bygger Pages med `actions/upload-pages-artifact@v3` + `actions/deploy-pages@v4`. Verktøyene som trenger varselet (testlab, vindmålinger, diagnoser) henter det med `fetcher/hent_varsel.sh`.

Det som fortsatt committes i hver kjøring, er læringsdataene i `data/` (steget «Lagre læringsdataene (data/) i git» i jobbene `samle` og `sekvensiell`): `notified.json`, `bw_calibration.json`, `exposure.json`, en ny fil i `forecast_archive/` per kjøring, og `forecast_accuracy.json`. Disse leses av neste kjøring (`longrange.score_runs()`, kalibreringen, varsel-dedup), så de kan ikke bare fjernes. Se (d).

Ulempe som allerede er kjøpt med S2: git-historikken har ikke lenger hvert varsel. Backtester som før leste `docs/data/forecast.json` fra historikken (f.eks. 5-stjerners-backtesten 15.10) må nå bruke `data/forecast_archive/` (bare stjerner og surfehøyde, 17 døgn).

### (b) Færre kjøringer om natten

Forslag: hent hver 6. time i stedet for hver 3. mellom 21 og 05 norsk tid. Cron går i UTC, og norsk tid er UTC+2 til 25.10, deretter UTC+1. Kjøringene i dag (UTC) er 00, 03, 06, … 21. Den eneste kjøringen som ligger helt inne i natta begge halvårene, er **00:17 UTC** (02:17/01:17 norsk tid). Fjernes den, blir det 21:17 → 03:17 UTC, altså 6 timer.

Endring:
- `forecast.yml`: `cron: "17 */3 * * *"` → `cron: "17 3-21/3 * * *"` (03, 06, 09, 12, 15, 18, 21 UTC - 7 per døgn).
- `vakthund.yml`: `cron: "47 1-23/3 * * *"` → `cron: "47 4-22/3 * * *"` (fjerner 01:47, som ellers ville sjekket uten at noe nytt har kommet). `MAKS_ALDER_T = 7` holder fortsatt: lengste gap blir 6 timer + kjøretid.

Sparer 2 kjøringer og 1 bot-commit per døgn (ca. 11 %).

Hva det koster i varselkvalitet:
- Nesten ingenting for modellene: GFS/GFS Wave sin 18Z-kjøring er tilgjengelig hos Open-Meteo rundt 22-23 UTC, og neste (00Z) først rundt 04 UTC. 03:17-kjøringen får uansett det 00:17-kjøringen ville fått, pluss mer. met.no og BarentsWatch oppdateres sjeldnere enn hver 3. time om natten.
- Morgenvarselet (det som brukes til «dawn patrol») kommer fortsatt 03:17 UTC, 05:17 eller 04:17 norsk tid.
- **Sjekk før bygging:** `longrange.score_runs()` regner «fasit» for en time som varselet laget under 6 timer før, med vinduer på 3 timer (`SCORE_SLOT_HOURS = 3`). Med 6 timers gap om natten kan timene 00-03 UTC miste fasit og telles sjeldnere i treffsikkerheten. Det er nattetimer (mørkt) og påvirker ikke stjernene, men koden må sjekkes (og trolig få `SCORE_SLOT_HOURS` til å følge faktisk gap). Det er en endring i fetcher/ og skal til fysikk-kontrolløren.
- ntfy-varsler for 5 stjerner kommer ikke kl. 02 om natten - det er bare en fordel.

Videre (ikke anbefalt nå): bare 4 kjøringer per døgn (00, 06, 12, 18 + 3 t) ville matche GFS-syklusene, men mister 3-timers-oppdateringen av BarentsWatch og met.no på dagtid, som er det appen er best på.

### (c) Samle små PR-er

Det som skiller seg ut, er 15.-16.10: 16 PR-er på to døgn, 70 push på ett døgn, 21 push rett til main og 14 «Synk main inn i …»-merger. Hver push gir én eller to fulle testkjøringer med Playwright.

Forslag (arbeidsmåte, ingen kodeendring):
1. Høyst 2-3 PR-er per døgn. Flere små oppgaver som hører sammen, samles i én gren og én PR.
2. Push når en oppgave er ferdig (som CLAUDE.md allerede sier), ikke etter hver delcommit. Commit lokalt per delsteg som før.
3. Ikke commit rett på main, heller ikke STATUS.md - la STATUS-oppdateringen følge PR-en den hører til. Unntak: driftsrettelser etter regelen 16.10.
4. Synk main inn i en gren bare rett før merge, ikke etter hver endring på main.
5. Slett grener etter merge (34 grener på origin i dag).

Endringer i workflow-filene som gjør dette billigere:
- `test.yml`: `on: push:` → `on: push: branches: [main]` + `pull_request:` (en gren med åpen PR testes én gang per push, ikke to). Grener uten PR kan testes med «Run workflow» (`workflow_dispatch:` legges til).
- `test.yml`: legg til `concurrency: { group: test-${{ github.ref }}, cancel-in-progress: true }` - en ny push avbryter testen av den forrige på samme gren.
- `test.yml`: `paths-ignore: ["STATUS.md", "ROADMAP.md", "CLAUDE.md"]` på både push og pull_request (rene tekstendringer utenfor docs/ trenger ikke Playwright). NB: filer i docs/ må IKKE ignoreres - de endrer sw.js-hashen.
- `test.yml`: `fetch-depth: 0` → `fetch-depth: 0` + `filter: blob:none` (partiell klon: hele historikken for merge-base, men bare de filene som trengs - i stedet for ca. 110 MB per kjøring).
- CLAUDE.md sier i dag at testene kjøres «på push/PR» - teksten oppdateres samtidig.

### (d) Læringsdata og logger uten tusenvis av commits

I dag: én bot-commit per kjøring (ca. 8 per døgn, ca. 2 900 per år), alle på main. Dataene er små (under 0,3 MB i hele historikken), så problemet er antallet commits, ikke størrelsen.

| Alternativ | Fordeler | Ulemper | Vurdering |
|---|---|---|---|
| Artefakter med lang levetid (`retention-days: 90`, offentlig repo maks 90) | ingen commits | data borte etter 90 dager uten ny kjøring; avhenger av Actions-API-et (suspensjonen viste at det kan forsvinne over natta); artifacts er **offentlige** i dette repoet; ikke i lokal git, så testlab/backtest lokalt trenger `gh` | Nei, ikke som eneste lager |
| `actions/cache` | ingen commits | kan kastes når som helst (7 dager ubrukt, 10 GB-tak), ikke ment som lager | Nei |
| **Én samle-commit per døgn** | 8 → 1 bot-commit per døgn; dataene ligger fortsatt i git (sikkerhetskopi, lesbar lokalt, lik i alle verktøy) | tilstanden mellom kjøringene i døgnet må bæres i en artifact; mister høyst et døgn med læring hvis kjeden brytes; litt mer kode i workflowen | **Anbefalt** |
| Egen datagren (`data`, foreldreløs) | main blir ren; samme kode som i dag med annen gren | like mange commits og push som før (bare et annet sted); to grener å holde i synk; Pages/tester må lese fra en annen gren | Bare sammen med samle-commit, hvis main skal være helt fri for bot-commits |
| Releases som lager (en release per døgn/uke med vedlagte filer) | ingen commits | feil bruk av releases, mange API-kall, vanskelig å lese/endre; ser mer bot-aktig ut, ikke mindre | Nei |
| Det private loggrepoet (`LOGS_REPO`) | main ren | flytter bare fotavtrykket; samme konto | Nei |

Anbefaling, konkret for `forecast.yml` (jobbene `samle` og `sekvensiell`):
1. Nytt steg først i `samle`: last ned artifact «laering» fra siste vellykkede kjøring på main (samme mønster som `fetcher/hent_varsel.sh`, nytt skript `fetcher/hent_laering.sh`, trenger `permissions: actions: read`). Finnes den ikke, eller er den eldre enn det som ligger i git, brukes `data/` fra git som i dag.
2. Nytt steg etter «Lag appens datafiler»: last opp `data/notified.json`, `bw_calibration.json`, `exposure.json`, `forecast_archive/`, `forecast_accuracy.json` som artifact «laering» (`retention-days: 7`). Ingen loggfiler eller hemmelige spots (de skal ikke i offentlige artifacts - samme regel som i dag).
3. Steget «Lagre læringsdataene (data/) i git» får `if:` som bare slår til i én kjøring per døgn (f.eks. når `date -u +%H` er 21, eller ved `workflow_dispatch`), og melding «Læringsdata for <dato>».
4. Samme behandling for `wind_obs.yml` sin daglige commit: kan legges inn i samme døgnlige commit, eller beholdes (1 per døgn).

Viktig: `notified.json` hindrer at samme ntfy-varsel sendes to ganger. Det MÅ bæres mellom kjøringene (via artifacten), ellers kommer dobbeltvarsler. Testene i `test_pipeline.py`/`test_matrise.py` må dekke at samle-steget leser artifacten når den er nyere enn git.

Gevinst: ca. 8 → 1 bot-commit per døgn (ca. 2 900 → 365 per år), uten å miste noe av læringen.

### (e) Andre ting

1. **Logger fra appen committer ved hver åpning.** `syncLogs()` i `docs/js/app.js` kjøres hver gang varselet er lastet (og ved hver ny/slettet logg), og gjør alltid en `PUT` mot `contents/logs.json` i loggrepoet - også når ingenting er endret. Det gir trolig en commit «Oppdater logger» per åpning av appen (ikke telt - loggrepoet er ikke tilgjengelig lokalt). Forslag: sammenlign det sammenslåtte innholdet med det som kom fra GitHub, og hopp over `PUT` når det er likt. Liten endring i docs/ (krever sw.js-oppdatering og nettlesertest).
2. **Commit-identitet.** 185 commits for hånd har e-posten `<bruker>@<maskinnavn>.local`, som ikke er koblet til kontoen, og 62 har «Claude» som forfatter. Forslag: `git config --global user.email` til kontoens noreply-adresse (`<id>+theodorll03-bit@users.noreply.github.com`), Theodor som forfatter på alle commits for hånd, og Claude bare som `Co-Authored-By`. Botene: `nordsurf-bot <actions@users.noreply.github.com>` er ikke en ekte konto - bruk GitHub sin egen identitet `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>` i forecast.yml, backtest.yml, find_bw_point.yml, wind_obs.yml, kystvaer_probe.yml og wam800.yml.
3. **find_bw_point.yml committer hvert søk til main** (9 på 14 døgn, 5 av dem 16.10). Forslag: last opp `data/bw_point_search/` som artifact og la resultatet bli med i spotens PR for hånd. Fjern `git add`/`commit`/`push` i workflowen og sett `permissions: contents: read`.
4. **provehent.yml (bare på region/lofoten-vesteralen):** kjører en full henting mot met.no, BarentsWatch og Open-Meteo ved hver push til `region/**` som rører spots.json (12 push til den grenen 16.10). Push-utløseren står der bare fordi `workflow_dispatch` krever at fila finnes på main. Forslag: når den merges, fjern `push:`-delen og behold bare `workflow_dispatch` - én prøvehenting per region, startet med vilje.
5. **vakthund.yml** kjører 8 ganger per døgn bare for å sjekke. Den kan ikke flyttes inn i forecast.yml (den skal oppdage at forecast.yml står stille), men hver 6. time holder: `cron: "47 4-22/6 * * *"` (04:47, 10:47, 16:47, 22:47 UTC). Alarmen kommer da høyst 3 timer senere. Issuene den åpner (og kommentarer høyst hver 6. time) er greie - de kommer bare når noe faktisk står stille. Men: når kontoen er tilbake og henteren har stått stille i dager, åpner den en issue med én gang. Lukk/rydd den for hånd.
6. **backtest.yml** sin daglige jobb (`17 7 * * *`, Steinkrøssa-snittet) starter en kjøring hver dag selv om den bare gjør noe på en svelldag. Kan heller kjøres som et steg i den første «Hent varsel» etter 06 UTC, eller bli ukentlig. Testlaben sin ukentlige commit er grei.
7. **Skjermbildene i docs/design/** er 63 % av historikken. Nettlesertestene skriver nye PNG-er i `docs/design/*/etter/` hver gang, og de committes. test.yml laster dem allerede opp som artifact «design-screenshots». Forslag: `docs/design/*/etter/` i `.gitignore`, og bare noen få referansebilder i git. Historikken krymper ikke uten omskriving (force push), som IKKE foreslås.
8. **kartflisene (docs/geo/*.pmtiles, 61 MB):** hver nye versjon legger til ca. 30-60 MB. Git LFS ville flyttet dem ut, men er en ny tjeneste med egen kvote - krever ja, og er ikke nødvendig så lenge de sjelden endres.
9. **kystvaer_probe.yml** (push til `sky/testlab`), **wam800.yml**, **measure_*.yml**, **diagnose_*.yml**: engangsverktøy. De som er ferdige, kan slettes fra main (de ligger i historikken).

## 4. Anbefalt rekkefølge

| # | Tiltak | Effekt | Risiko | Krever Theodors ja |
|---|---|---|---|---|
| 1 | Arbeidsmåte (c 1-5): færre push, færre PR-er, ikke rett på main, grener slettes | størst - de travle døgnene er 90 % av fotavtrykket | ingen | Ja (endrer CLAUDE.md sin arbeidsmåte) |
| 2 | Commit-identitet (e 2) | commits kobles til kontoen og ser ut som en person + GitHub sin egen bot | ingen | Ja (lite) |
| 3 | test.yml: push bare på main + PR, concurrency, paths-ignore, `filter: blob:none` (c) | ca. halvparten av testkjøringene og nesten all klon-trafikk borte | lav - må sjekke at test_display_only fortsatt finner merge-base | Ja |
| 4 | find_bw_point uten commit, provehent uten push-utløser, vakthund hver 6. time (e 3-5) | -4 kjøringer per døgn, -5-10 bot-commits per uke | lav | Ja |
| 5 | Samle-commit for læringsdata én gang per døgn (d) | 8 → 1 bot-commit per døgn | middels - må bære notified.json, ellers dobbeltvarsler; trenger tester og fysikk-kontrollør | Ja |
| 6 | Natt hver 6. time (b) | -1 henting, -1 vakt per døgn | lav for stjernene; treffsikkerhetsmålingen om natten må sjekkes | Ja (rører varselet og longrange) |
| 7 | Logger: ingen PUT uten endring (e 1) | færre commits i loggrepoet | lav; docs/-endring | Ja |
| 8 | Skjermbilder ut av git (e 7) | stopper veksten i repoet | lav | Ja |

Alle tiltakene krever ja: ingen av dem er en driftsrettelse for noe som står stille (regelen fra 16.10), og flere rører docs/, fetcher/ eller arbeidsmåten i CLAUDE.md. Ingen av dem rører ratingen, spots.json eller de faste observasjonene. Første gang kontoen er tilbake: push det som venter lokalt i få, samlede omganger - ikke 20 grener på én gang.

Med 1-6 gjennomført er et vanlig døgn ca. 7 hentinger + 4 vakter + 1 vindhenting, 1-2 bot-commits, og et arbeidsdøgn 2-3 PR-er og 10-20 testkjøringer i stedet for 100+.
