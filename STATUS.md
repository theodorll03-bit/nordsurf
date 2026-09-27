# Nordsurf: status

## Oppsummering (sist oppdatert 27.09.2026, under arbeid)

- **ROADMAP oppgave 2 (koble del C inn i ratingen): FERDIG, Theodor sa ja etter tre rettelser - committet.** Fysikk-kontrollør fant først at `rate()` dempet Hb med samme retningsfaktor SOM ALLEREDE lå i høyden `h` (dobbelttelling) - rettet ved å fjerne den ekstra dempingen for svell_ute/barentswatch. Theodor pekte deretter på at Ersfjordstranda sitt tilfelle (svell 4-6 grader UTENFOR vinduet OG den frie sektoren, bare når spoten via diffraksjon) er en ANNEN, ekte situasjon enn Unstad sin (fri linje) - samme fysikk som Grøtfjord 25.09.2026 (utenfor vinduet, helt flatt). Rettelse: ny `raw_exposure_zero()` - ekstra Hb-demping bare når RÅ (ikke glattet) geometrisk eksponering er nøyaktig 0. Fysikk-kontrollør fant deretter at dette ville dobbeltdempe Grøtfjord sin `exposure_override`-sone (317-330, rå eksponering også 0 der) - rettet ved å droppe den ekstra dempingen når en override dekker retningen (overriden ER allerede den kalibrerte sannheten). Endelig tabell: 13 timer med 2+ endring (Unstad opp 5, Steinkrøssa ned 1 - begge uendret fra Theodors "ja"), Ersfjordstranda og Grøtfjord helt tilbake til 0 endring. Se eget avsnitt.
- **ROADMAP oppgave 3 (kysttoleranse i check_spot.py, oppfølging av Steinkrøssa): FERDIG, ingen swell_window endret.** Theodors hypotese (gammel 2 km-toleranse ga for bredt vindu) holder IKKE for Steinkrøssa - grensa mellom blokkert (295-314°) og åpent (315-16°) er identisk med både 2 km og den nye 300 m-toleransen. Steinkrøssa sitt eksponeringsfall ved 324° skyldes i stedet Gaussian-glatting som sprer en allerede kjent, korrekt blokkering (rett ved spoten, 295-314°) 10-15 grader inn i det åpne vinduet - en bevisst modelleringsvalg, ikke en geometrifeil. Ingen av de 6 spotenes vinduer mister fri linje med den strengere toleransen. Se eget avsnitt.
- **Retningskonvensjonen er nå endelig avklart, tredje og siste runde**: `totalMeanWaveDirection` er retningen bølgene går MOT (samme som pilene på BarentsWatch sitt kart), regnes om til "fra" med +180. Bevist av en garantert rå logg (Unstad, 26.09 kl. 15:00Z, rå verdi 116 - FØR noen konverteringskode noensinne fantes - gir konvertert 296, nesten blink mot facing 294,8 og stemmer med videoen). Den mellomliggende konklusjonen ("fra, ingen konvertering", satt tidligere i denne økten) var feil - bygget på et tall som senere viste seg å være allerede konvertert, ikke rått.
- **Beviset er nå en fixture i repoet**: `fetcher/fixtures/bw_raw_unstad_2026-09-26.json`, hentet direkte fra GitHub Actions-loggen (credentials var allerede maskert med `***` i loggen selv - sjekket, ingen hemmeligheter i fixturen). Ny test 7.5c leser fixturen og bekrefter 116→296 og under 5 graders avvik fra facing (fikk 1,2 grader). Beviset er dermed sporbart for alle, ikke bare i Theodors Downloads-mappe.
- **Retningsfaktoren over 150 grader er endret fra nøytral til ekte straff** (Theodors eksplisitte instruks, punkt 2): siden konvensjonen nå er riktig, betyr et avvik over 150 grader at bølgene FAKTISK går ut fra land - en kjent, ikke en ukjent/mistenkelig retning. Gir nå retningsfaktor 0 (ordinær straff), IKKE lenger nøytral 1,0. Gjør IKKE timen usikker og utløser IKKE "kildene uenige" alene. Ny forklaringstekst på detaljsiden: "Bølgene ved spoten går ut fra land. Trolig vindsjø fra land, ikke svell inn." Feltet `spot_direction_error` er fjernet og erstattet med `spot_direction_offshore` (samme mekanikk, riktig navn for den nye betydningen).
- **Ny sikring på SPOTNIVÅ** (`fetch.py: convention_warning()`): hvis mer enn halvparten av timene med ekte svell ute mot vinduet (swell_offshore over 0,5 m og directness over 0,5) i en kjøring har BarentsWatch-retning over 150 grader for en spot, varsles det med fet skrift ØVERST i kilderapporten ("Mulig feil i BarentsWatch-retningskonvensjonen for [spot]"). Endrer aldri ratingen selv. Testet med syntetiske 60 %/20 %-scenarioer (9.6) - slår inn ved 60 %, ikke ved 20 %.
- **2-stjerners stoppregelen i CLAUDE.md er sjekket på nytt for HELE endringen** (ikke bare de 35 timene fra forrige runde), ved å kjøre den faktisk deployede koden (`a19624c`) og den nye koden mot alle 348 timer (58 timer × 6 spots) i siste tilgjengelige lokale data: maks stjerneendring er 0 for alle spots - ingen timer endrer stjerner i det hele tatt. Se eget avsnitt for tabellen (rettet av fysikk-kontrollørens andre gjennomgang, som fant at min første versjon sammenlignet feil kodeversjoner). Stoppregelen er dermed IKKE utløst.
- **Motgående vindsjø-hypotesen (offshorevind): fortsatt HOLDER IKKE** (uendret fra forrige runde - se eget avsnitt).
- **Kilde/fileSource-hypotesen: forkastet.** Det "konkrete funnet" fra forrige runde (116 vs. et antatt "296") er nå forklart fullt ut av selve retningskonvensjonen (116 rått, 296 KORREKT KONVERTERT - ikke to ulike API-svar). Ingen grunn til å tro kilden/fileSource varierer konvensjon; du trenger ikke lenger trigge den workflowen for dette spørsmålet (den kan fortsatt være nyttig for oppgave 4, rutepunkt-spørsmålet, som er uavhengig).
- Alle tester som brukte en hardkodet BarentsWatch-retning er sjekket mot git-historikken for å avgjøre om verdien var rå eller allerede konvertert, og rettet der det var rått (Grøtfjord 26.09: 114→294; Unstad 9.1/9.2: 115→295). Gamle og nye tall vist i eget avsnitt. Alle faste observasjoner i CLAUDE.md holder fortsatt.
- 48-timers nyskanning (retningsfaktor/avvik): for de tre spotene som treffer nesten rett på (Grøtfjord, Ersfjordstranda, Unstad) faller antall timer over 150° til 0, som ventet. For Lenangsøyra og Steinkrøssa øker det derimot (0→4 og 0→31) - men siden BarentsWatch-høyden i akkurat disse timene er svært lav (0,01-0,21 m), gir ikke det noen stjerneendring i praksis (se stoppregel-tabellen).
- Committet og pushet nå, på dette bevisgrunnlaget (Theodors eksplisitte "ja", punkt 3). Neste GitHub Actions-kjøring er selve kontrollen - skanningen kjøres på nytt mot ferske tall etterpå.
- **Ikke pushet et nytt `docs/data/forecast.json` fra en lokal kjøring** - det committes bare av `nordsurf-bot` (GitHub Actions, ekte nøkler), aldri manuelt; en lokal kjøring uten BarentsWatch-nøkler ville bare gitt et degradert varsel til alle spots og overskrevet den ekte, ferske dataen på siden.
- Oppgave 2, 3 i ROADMAP.md: ikke startet ennå. Oppgave 4: fortsatt bare delvis forsøkt (se tidligere avsnitt), uendret denne runden.

---

## Oppgave 1: Rett exposure_baseline.py (del C)

### Hva som ble gjort
- Byttet ut den første, rent geometriske heuristikken (bredde langs strålen) med bredde-på-tvers og skyggelengde-fysikk: `L = W² / λ`, `λ = 225 m` (Fresnel-tilnærming for en knivsegg-hindring, svell ca. 12 s periode). Under L: rå eksponering 0. Over L: vokser mot 1 som `1 - L/avstand`.
- Kysttoleranse redusert fra 2 km til 300 m: linja må nå sammenhengende vann innen 300 m fra spoten, ellers regnes retningen som blokkert fra start.
- Glattet med normalfordeling, sigma 10 grader.

### Verifisert mot en syntetisk hard kant
`gaussian_smooth()` testet mot en ren trappe-funksjon: 0,52 rett på kanten, 0,146 ti grader utenfor (teoretisk 0,5 og 0,159) - glattingen er korrekt.

### Hvorfor Unstad og Ersfjordstranda så ut til å gi 1,0 helt ut til kantene
Ikke en feil i glattingen. Begge spotenes KONFIGURERTE `swell_window` ligger nesten nøyaktig på den EKTE geometriske åpningen (innenfor 1-6 grader, siden vinduene opprinnelig ble satt med samme kystlinjedata via `check_spot.py`). Unstad sitt vindu er dessuten 82 grader bredt - med sigma 10 grader er det forventet at det meste av et så bredt vindu ligger nær 1,0 etter glatting; bare de ytterste ca. 20 gradene på hver side taper synlig.

### Grøtfjord 311-330 grader (Vengsøya-skjæret) - status
`exposure_override` sin begrunnelse var upresis (sa "opptil 0,9", fanget opp av fysikk-kontrollør, rettet til riktig tall):

| Grader | Rå (geometri alene) | Glattet |
|---|---|---|
| 311-316 | **1,0** (GSHHS har INGEN hindring her - reelt hull i kartdataene) | 0,52-0,74 |
| 317-330 | **0,0** (GSHHS finner nå faktisk en hindring: 5,6-7,6 km unna, 1,9-3,6 km bred på tvers, skyggelengde 15-57 km) | 0,10-0,48 |

Kriteriet "311 til 330 grader gir lav eksponering av geometrien alene" er dermed **delvis, ikke fullt ut oppfylt**: geometrien fanger nå opp skjæret for 317-330 grader (var ikke tilfelle før denne oppgaven), men 311-316 grader er fortsatt et blindt punkt i GSHHS. `exposure_override` (tak 0,2, hele 311-330 grader) dekker fortsatt begge deler, og er derfor fortsatt nødvendig - bare for et smalere reelt problem enn kommentaren i spots.json først ga inntrykk av.

### De tre andre kriteriene - alle oppfylt
- Grøtfjord 285-310 grader: rå eksponering 1,0 gjennomgående. ✓
- Steinkrøssa rett under 315 grader (314°): blokkert (rå 0,0). 315° og oppover: åpent. ✓
- Lenangsøyra sine lave verdier i det smale gapet (15-23°, glattet 0,55-0,59): beholdt uendret. ✓

### Full tabell mot skyggekurven, alle spots (rundt hver vinduskant)

Se `data/exposure_baseline.json` for komplette rå/glattede tall per grad. Utdrag (samplet hver 3. grad rundt kantene):

#### Grøtfjord (vindu [286, 310])
| Grader | Rå | Glattet | Skyggekurve |
|---|---|---|---|
| 271 | 0.000 | 0.087 | 0.108 |
| 280 | 0.000 | 0.326 | 0.300 |
| 286 | 1.000 | 0.560 | 0.667 |
| 298 | 1.000 | 0.881 | 0.667 |
| 310 | 1.000 | 0.739 | 0.667 |
| 316 | 1.000 | 0.520 | 0.300 |
| 322 | 0.000 | 0.293 | 0.144 |

#### Ersfjordstranda (vindu [294, 320])
| Grader | Rå | Glattet | Skyggekurve |
|---|---|---|---|
| 282 | 0.000 | 0.436 | 0.144 |
| 294 | 1.000 | 0.841 | 0.667 |
| 320 | 1.000 | 0.539 | 0.667 |
| 329 | 0.000 | 0.262 | 0.200 |

#### Russelv (vindu [[5,15],[349,356]])
| Grader | Rå | Glattet | Skyggekurve |
|---|---|---|---|
| 5 | 1.000 | 0.696 | 0.667 |
| 15 | 1.000 | 0.627 | 0.667 |
| 21 | 0.000 | 0.506 | 0.300 |
| 349 | 1.000 | 0.425 | 0.667 |
| 356 | 1.000 | 0.594 | 0.667 |

#### Lenangsøyra (vindu [15, 23])
| Grader | Rå | Glattet | Skyggekurve |
|---|---|---|---|
| 9 | 0.000 | 0.420 | 0.300 |
| 15 | 1.000 | 0.553 | 0.667 |
| 20 | 1.000 | 0.593 | 0.667 |
| 23 | 1.000 | 0.570 | 0.667 |
| 32 | 0.000 | 0.346 | 0.200 |

#### Steinkrøssa (vindu [315, 16])
| Grader | Rå | Glattet | Skyggekurve |
|---|---|---|---|
| 312 | 0.000 | 0.401 | 0.467 |
| 315 | 1.000 | 0.520 | 0.667 |
| 1 | 1.000 | 0.941 | 0.667 |
| 19 | 0.000 | 0.401 | 0.467 |

#### Unstad (vindu [253, 335])
| Grader | Rå | Glattet | Skyggekurve |
|---|---|---|---|
| 250 | 0.000 | 0.661 | 0.467 |
| 253 | 1.000 | 0.723 | 0.667 |
| 268 | 1.000 | 0.963 | 0.667 |
| 335 | 1.000 | 0.599 | 0.667 |
| 338 | 0.000 | 0.480 | 0.467 |

### Fysikk-kontrollør, oppgave 1
MÅ RETTES (alle rettet før commit):
1. Grøtfjord 311-330 ikke fullt ut lav fra geometri alene - dokumentert ærlig over, ikke skjult.
2. STATUS.md manglet helt - denne filen.
3. `_exposure_override` sin "opptil 0,9"-påstand stemte ikke (faktisk maks var 0,71) - rettet i spots.json.

Selve fysikken (bredde på tvers, skyggeformel, kysttoleranse, glatting) ble vurdert som korrekt implementert.

### Tester
`fetcher/test_rating.py` og `fetcher/test_pipeline.py`: begge grønne (`exposure_baseline.py` er fortsatt frittstående, ikke koblet inn i `rating.py`, så ingen av de faste observasjonene er i fare ennå).

---

## HASTER: Unstad i morgen kl. 10 - feilaktig retning ved spoten

### Symptomet
`docs/data/forecast.json`, Unstad, 2026-09-27T08:00Z (10:00 norsk tid): surfehøyde 0,0 m, "Kildene er uenige", til tross for at svellet ute var 2,3 m fra 255 grader (fysisk rimelig) og BarentsWatch sin egen nettside (sjekket direkte mot www.barentswatch.no/bolgevarsel for samme punkt) viste sammenlignbar signifikant høyde (0,6-0,7 m, maks 1,2-1,3 m - stemmer godt med `bw_height`/`bw_height_max` i våre data). `spot_direction_diff` var 180 grader.

### Undersøkt og utelukket
- **Ikke stale `forecast.json`**: filen er generert (26.09 21:00 UTC) av en kjøring som skjedde ETTER at forrige retningsrettelse (fjerning av +180-konverteringen) ble pushet.
- **Ikke en interpoleringsfeil**: begge de RÅ (ikke-interpolerte) BarentsWatch-punktene som omgir timen (06:00Z og 09:00Z) hadde allerede samme feilaktige retning (115°) - feilen kommer fra selve API-svaret, ikke fra `_lerp_circular()`.
- **`gh` CLI er ikke tilgjengelig** i dette miljøet (bekreftet på nytt) - kunne ikke trigge diagnose-workflowen selv, slik CLAUDE.md ber om når mulig. Kunne heller ikke slå opp hvilket rutepunkt BarentsWatch sitt API faktisk valgte som nærmeste (krever enten `gh workflow run` eller live API-nøkler, ingen av delene tilgjengelig lokalt).

### OPPDATERT ETTER PUSH: dette er ikke 2 isolerte tilfeller - det er SYSTEMATISK i hele det nåværende varselet

Etter at fiksen var committet og pushet, sjekket jeg CLAUDE.md sin egen stoppregel ("flytter stjernene med 2 eller mer... vis tabell før og etter") grundigere ved å skanne HELE 48-timersvinduet i det nåværende `docs/data/forecast.json` for alle timer med over 150 grader avvik. Resultatet er mye mer alvorlig enn de 2 tilfellene jeg først rapporterte:

**Praktisk talt ALLE timer de neste 48+ timene for Grøtfjord, Ersfjordstranda OG Unstad** (3 av 6 spots) har `bw_dir` mellom ca. 150 og 180 grader fra `facing` - ikke unntaket, men normaltilstanden i akkurat denne kjøringen:
- Grøtfjord: ca. 30 av 30+ sjekkede timer, stort sett 179°.
- Ersfjordstranda: ca. 35 av 35+ sjekkede timer, stort sett 155°.
- Unstad: praktisk talt SAMTLIGE timer i vinduet, stort sett 177-180°.
- Russelv, Lenangsøyra, Steinkrøssa: **ingen** treff i samme skann - disse 3 spotene ser ut til å være upåvirket.

Ingen av disse enkelttimene ga et 2-stjerners hopp (alle var allerede 0 stjerner, eller ble 0→1), så CLAUDE.md sin bokstavelige stoppregel (2+ stjerners endring) utløses ikke - men det er fordi høyden/vinden uansett holdt dem lave, IKKE fordi retningsfeilen er triviell. Den underliggende dataen for tre av seks spots er mistenkelig i praktisk talt hele det nåværende varselvinduet.

| Time | Avvik fra facing | Svellandel (swell_share) |
|---|---|---|
| Unstad 26.09 kl. 17 (etablerte "fra"-konvensjonen) | ≈1° | 94 % (nesten ren svell) |
| Grøtfjord, Ersfjordstranda, Unstad - hele det nåværende 48t-vinduet | 150-180°, stort sett 155-180° | Variert, ikke konsekvent knyttet til vindsjøandel ved nærmere sjekk |

**Vindsjø-hypotesen fra før svekkes** av at dette rammer så og si ALLE timer i vinduet, uavhengig av svellandel - noe mer grunnleggende enn "vindsjø forstyrrer retningsfeltet i enkelte timer" ser ut til å foregå. Mulige forklaringer jeg IKKE har kunnet undersøke uten `gh`/live API-tilgang: en modellversjon eller kjøring hos BarentsWatch som for øyeblikket har snudd konvensjonen for disse tre spotenes rutepunkter spesielt (kanskje geografisk/regionalt betinget), en feil i hvordan disse tre spotenes `barentswatch_point` treffer BarentsWatch sitt rutenett akkurat nå, eller noe helt annet. **Jeg vet ikke hvorfor akkurat disse tre spotene og ikke de tre andre.**

**Dette er større enn en "spør Theodor om terskelen skal utvides"-sak. Det reiser spørsmålet om "fra, ingen konvertering"-konklusjonen fra i går fortsatt er riktig for disse tre spotenes rutepunkter akkurat nå, eller om noe har endret seg på BarentsWatch sin side siden den ble bekreftet.** Jeg har IKKE reversert eller endret konvensjonen - bare lagt til sikringen som eksplisitt bedt om - men jeg stopper her og venter på beskjed før jeg går videre i ROADMAP-køen, siden dette er nøyaktig den typen "modell mot observasjon"-spørsmål CLAUDE.md sier skal stoppes på.

### Fiksen (som eksplisitt beskrevet av Theodor)
`rating.spot_direction_factor()`: avvik over 150 grader fra facing regnes nå som en DATAFEIL, ikke fysikk (bølger går ikke rett ut fra en strand i praksis). Gir nøytral retningsfaktor 1,0 (ikke 0), tvinger timen usikker (maks 3 stjerner), og hindrer at `sources_disagree` utløses av retningen alene. `fetch.py` varsler i kilderapporten når dette skjer, med tidspunktene.

**Unstad i morgen kl. 10, etter fiksen** (samme rådata, ny kode):
- `bw_height`: 0,61 m, `bw_dir`: 115° (fortsatt vist, men merket datafeil)
- `spot_direction_factor`: 1,0 (nøytral, var 0,0 før fiksen)
- `spot_direction_error`: sann
- `sources_disagree`: usann (var sann før fiksen)
- `uncertain`: sann (maks 3 stjerner)
- Surfehøyde: 0,7 m, sett 0,9 m (var 0,0 m før fiksen)
- Stjerner: 0 (1 uten vind) - vinden (8 m/s sidevind, kast 13) og den beskjedne høyden holder det uansett lavt, men IKKE lenger på grunn av en falsk "kildene er uenige"

### Fysikk-kontrollør: **SPØR THEODOR**
1. 150 graders grense er fysisk forsvarlig som skille (fanger bare det ekstreme området nær 180°, der en ekte "fra"-retning ville betydd bølger ut fra land), men selve tallet er valgt for å dekke de to kjente tilfellene (179-180°), ikke utledet fra noe annet. (Dette tallet var uansett gitt eksplisitt av Theodor, ikke valgt av meg.)
2. **Hovedbekymringen**: denne fiksen fanger bare det EKSTREME utslaget (>150°). Hvis hypotesen om vindsjø-korrelert feilretning stemmer, vil trolig MINDRE, ikke-ekstreme avvik (f.eks. 70-140° i vindsjøtunge timer) IKKE fanges opp av noen sikring - de ville fortsatt gi retningsfaktor 0 via den vanlige regelen, stille, uten noe "mistenkt datafeil"-flagg.
3. Nøytral faktor (1,0, ikke 0) i feilcaset ble vurdert som riktig gjort - konsistent med resten av funksjonen, og henger sammen med at timen samtidig tvinges usikker.
4. Alle faste observasjoner i CLAUDE.md holder fortsatt.

**Spørsmål til Theodor**: er den synlige rapporteringen (kilderapport-varselet) nok til å fange opp flere tilfeller over tid, eller bør BarentsWatch-retning ved spoten mistenkeliggjøres bredere (f.eks. når svellandelen er under 80-90 %, ikke bare ved >150 graders avvik) før jeg går videre? Jeg har IKKE utvidet fiksen utover det som ble eksplisitt bedt om, i påvente av svar.

### Tester
Lagt til 9.1 (Unstad, interpolert time), 9.2 (samme, rå time - bekrefter safeguarden ikke er avhengig av interpolering), 9.3 (grensetest 149/151 grader). Oppdatert kommentar på den eksisterende Grøtfjord 26.09-testen (samme mønster oppdaget der). Alle tester grønne.

### Henteren
Ikke kjørt lokalt - ingen BarentsWatch-nøkler tilgjengelig lokalt (samme begrensning som tidligere i prosjektet), så en lokal kjøring ville bare gitt degradert data. Fiksen tas i bruk av neste ordinære "Hent varsel"-kjøring i GitHub Actions (hver 3. time), som har ekte nøkler.

---

## Vindsjø-hypotesen (motgående vindsjø ved offshorevind) - testet mot dagens data

Theodor sin hypotese: BarentsWatch sin `totalMeanWaveDirection` er gjennomsnittet for all sjø ved punktet. Offshorevind lager vindsjø som går UT fra stranda; 250 m ut blandet med innkommende svell kan snittet peke mot land. Grøtfjord/Ersfjordstranda/Unstad har offshorevind fra SØ-Ø, Russelv/Lenangsøyra/Steinkrøssa fra S-SV - det passer med hvilke spots som er rammet.

### Tallene (alle 6 spots, neste 48 timer, 294 timer med både bw_dir og facing kjent)

| | Antall | Andel |
|---|---|---|
| Timer med over 150° avvik | 121 | - |
| ... av disse, offshorevind | 31 | **26 %** |
| ... av disse, offshorevind over 5 m/s | 23 | 19 % |
| Timer med offshorevind over 5 m/s | 102 | - |
| ... av disse, over 150° avvik | 23 | **23 %** |

### Per spot

| Spot | Timer sjekket | Over 150° avvik | Med offshorevind | offshore_wind-sektor | facing |
|---|---|---|---|---|---|
| Grøtfjord | 49 | 33 | 8 | [76, 166] | 295 |
| Ersfjordstranda | 49 | 39 | 17 | [90, 180] | 315 |
| Unstad | 49 | **49 (alle)** | 6 | [70, 160] | 294,8 |
| Russelv | 49 | 0 | 7 | [90, 180] | 315 |
| Lenangsøyra | 49 | 0 | 47 | [155, 245] | 0 |
| Steinkrøssa | 49 | 0 | 39 | [175, 265] | 45 |

### Konklusjon: hypotesen holder ikke

- Bare 26 % av de anomale timene har offshorevind i det hele tatt - 74 % har det IKKE. Hvis offshorevind var årsaken, skulle andelen vært høy, ikke lav.
- Av timene med offshorevind over 5 m/s er det bare 23 % som viser avviket - 77 % av offshorevind-timene er helt fine.
- **Unstad er det klareste moteksempelet**: alle 49 av 49 timer er rammet, men bare 6 av dem har offshorevind i det hele tatt. Avviket er der uansett vindretning på Unstad akkurat nå - det kan ikke være vindsjø fra offshorevind som lager det når det også er der ved side- og onshorevind.
- Et kontrollpar som svekker en geografisk/regional forklaring også: Russelv og Ersfjordstranda har IDENTISK facing (315°) og praktisk talt identisk offshore_wind-sektor ([90,180] begge), men Russelv har 0 rammede timer mot Ersfjordstranda sine 39. Samme fysiske oppsett, helt forskjellig utfall.

Jeg har ikke funnet noen alternativ forklaring som passer bedre i denne omgangen (undersøkte facing, offshore_wind-sektor og område/landsdel - ingen av dem skiller rent de tre rammede spotene fra de tre urammede). Unstad 26.09 kl. 17 (296° mot facing 294,8°, nesten nøyaktig treff) bekrefter fortsatt at "fra, ingen konvertering" er riktig konvensjon for API-feltet generelt - spørsmålet er hvorfor akkurat Grøtfjord, Ersfjordstranda og Unstad sine punkter avviker så mye akkurat nå, ikke om konvensjonen i seg selv er feil.

**Stopper her per instruks (punkt 3).** Har IKKE gjort noen av endringene i punkt 2 (a-e), siden hypotesen ikke besto testen i punkt 1.

---

## Ny hypotese: retningskonvensjonen varierer med datakilde (source/fileSource)

### Kunne ikke kjøres fullt ut herfra
Verken `gh` CLI eller BarentsWatch-nøkler er tilgjengelig i dette miljøet (bekreftet på nytt). Jeg kan derfor ikke hente rå API-data selv, slik oppdraget ber om i punkt 1. `fetcher/diagnose_bw_direction.py` er utvidet (ikke rating.py/sources.py/fetch.py) til å:
- Hente RÅ data for BEGGE punktene (`barentswatch_point` og `barentswatch_point_near`) per spot, 48 timer frem (var 24, bare ett punkt).
- Beholde `source` og `fileSource` per tidsverdi, i tillegg til punktet BarentsWatch faktisk valgte.
- Bygge en tabell per spot/punkt/kilde: antall tidsverdier, og hvor mange som har over 150 grader avvik fra facing.
- Sammenligne rå API-verdi mot det som faktisk står i det commitede `docs/data/forecast.json` for samme tidspunkt (punkt 4).

**Du må trigge "Diagnoser BarentsWatch-retning"-workflowen på nytt** (samme som sist) for at jeg skal få disse tallene - koden er pushet og klar.

### Et konkret funn fra den GAMLE, lagrede loggen (før source/fileSource ble lagt til)
Fant en lagret logg fra forrige diagnose-kjøring i din Downloads-mappe (`logs_98149256530`, kjørt 26.09.2026 kl. 12:59 UTC - FØR retningskonverteringen noen gang ble lagt til i koden, så dette er en garantert rå, utolket verdi direkte fra BarentsWatch sitt API).

For Unstad, tidsverdien 2026-09-26T15:00Z (kl. 17:00 norsk tid - SAMME time som senere ble brukt til å bekrefte "fra"-konvensjonen via videobevis): denne loggen viser **`totalMeanWaveDirection = 116`** grader, rått fra API-et.

Dette er **ikke** det samme tallet som "296" fra den tidligere samtalen. Jeg har forsøkt å rekonstruere hvorfor, ved å spore når konverteringskoden faktisk var aktiv (lagt til i commit `9785e1b`, kl. 16:54:58 UTC samme dag - over 4 timer ETTER denne loggen ble laget), men kan ikke gi et sikkert svar uten å vite nøyaktig når API-et selv ble spurt de gangene "296" kom fram tidligere i samtalen - det kan ha vært en annen, senere spørring mot API-et for samme tidsverdi, ikke bare et regnestykke på denne loggen sitt tall.

**Hvis** BarentsWatch sitt API faktisk svarte ULIKT for nøyaktig samme tidsverdi (2026-09-26T15:00Z, Unstad) ved to forskjellige spørringstidspunkt (116 rundt kl. 13:00, og et tall som senere ble regnet om fra "296" på et senere tidspunkt samme dag) - og de to tallene er nesten nøyaktig 180 grader fra hverandre (116 og 296) - er det en konkret, om enn ikke vanntett, indikasjon som peker i retning av nettopp DIN hypotese: at kilden (og dermed konvensjonen) for et gitt punkt kan endre seg mellom kjøringer. Jeg vil ikke konkludere på dette alene - den nye kjøringen med source/fileSource fanget opp vil gi et mye sikrere svar.

### Punkt 3 (Unstad kl. 17, 26.09 - source/fileSource den dagen)
Delvis besvart: fant loggen og det rå tallet (116), men DENNE versjonen av diagnoseskriptet fanget ikke opp `source`/`fileSource` ennå - de feltene ble lagt til i dag. Kan ikke svare på hvilken kilde/fileSource som var aktiv for akkurat den timen uten en ny kjøring.

### Punkt 4 (rå API-verdi vs det som står i forecast.json)
Kan ikke sjekkes uten en ny, fersk rå henting å sammenligne mot - lagt inn som en egen seksjon i diagnoseskriptet (sammenligner automatisk mot `docs/data/forecast.json` slik det ligger i repoet når workflowen kjører). Resultatet kommer med neste kjøring.

---

## Retningskonvensjonen endelig avklart, og gjenopprettet i kode

### Beviset
En garantert rå logg (i din Downloads-mappe, fra diagnose-kjøringen 26.09.2026 kl. 12:59 UTC - dette var FØR konverteringskoden noensinne eksisterte i sources.py, altså er tallet 100 % rått fra API-et) viser for Unstad, tidsverdien 2026-09-26T15:00Z: **`totalMeanWaveDirection = 116`**. Tolket som "mot" og konvertert (+180) gir **296**, som treffer Unstad sin facing (294,8°) nesten blink og stemmer med videobeviset (bølger rett inn mot stranda, over hodet, offshore). Den "296"-verdien en tidligere runde i denne økten trodde var et NYTT, uavhengig rått tall (og derfor konkluderte "fra, ingen konvertering" fra) var altså det samme tallet, bare allerede riktig konvertert - ikke et motsigende datapunkt. Kilde/fileSource-hypotesen er dermed overflødig: det var aldri to ulike API-svar, bare én verdi lest på to forskjellige stadier i regnestykket.

### Endret i kode/dokumentasjon
- `sources.py`: `d_from = (float(d) + 180) % 360` gjeninnført. Docstring skrevet om med hele beviskjeden.
- `CLAUDE.md`: konvensjonslinja rettet til den nye, beviste teksten. 150-graders-linja omformulert fra "datafeil" til "bølger som går ut fra stranda, mistenkelig, ukjent retning".
- `rating.py`: `spot_direction_factor()` sin begrunnelse omformulert samme vei. All "datafeil"/"mistenkt datafeil"-ordlyd i `barentswatch_height()`, `rate()` og `build_breakdown()` byttet til "mistenkelig" - ingen atferdsendring, bare ordlyd (nøytral faktor 1,0, `uncertain=True`, `sources_disagree` uberørt av retning alene - alt som før).
- `fetch.py`: samme ordlydsendring i kilderapport-varselet.

### Tester: gammel vs. ny verdi
Alle tester med en hardkodet BarentsWatch-retning sjekket via git-arkeologi (hvilken commit genererte forecast.json-øyeblikksbildet testen siterer, og var konverteringskoden aktiv i sources.py på det tidspunktet).

| Test | Gammel `bw_dir` | Proveniens | Ny `bw_dir` | Endring i resultat |
|---|---|---|---|---|
| 7.5 (enhetstest av konvertering) | mocket 296 | - | mocket **116** | Samme assert (`== 296`), men nå fra riktig retning (rå inn, konvertert ut) |
| Grøtfjord 26.09 (ekte data) | 114,0 | commit `04b0a52`, 15:36 UTC 26.09 - FØR konverteringen (`9785e1b`, 16:54 UTC) - rått | **294,0** | `spot_direction_error`: True → **False**. `stars` uendret (0), `likely_flat` uendret (sann) - svellandel (44 %) og lav høyde (0,1 m ute) holder det flatt uansett retning |
| 9.1 (Unstad i morgen kl. 10) | 115,0 | samme situasjon - fanget mens sources.py ikke konverterte, altså rått | **295,0** | `spot_direction_error`: True → **False**. `uncertain`: True → **False**. `surf_height` uendret (0,7 m, sett 0,9 m) - retningsfaktoren var 1,0 (nøytral) i begge tilfeller, bare av ulik grunn (feilflagg før, ekte nesten-blink-treff nå) |
| 9.2 (samme, rå time) | 115,0 | samme | **295,0** | Samme som 9.1 |
| 9.3 (grensetest 149/151°) | syntetisk (facing±149/151) | - | uendret | Ingen endring - testen bruker `spot_direction_factor()` direkte, uavhengig av noen fanget API-verdi |
| 7.1-7.4, 7.7 (Lenangsøyra) | 290/5/5/80/(ingen) | syntetiske, illustrerer allerede-"fra"-scenarioer i kommentarene sine (f.eks. "70 grader skrått på stranda"), ikke hentet fra en ekte logg | uendret | Ingen endring - `rate()` forventer alltid intern "fra", disse testene var aldri knyttet til BarentsWatch sin rå API-konvensjon |

Alle 5 faste observasjoner i CLAUDE.md er sjekket på nytt og holder. `fetcher/test_rating.py` og `fetcher/test_pipeline.py` kjører grønt.

### 48-timers nyskanning: >150° avvik fra facing, gammel vs. rettet retning
Siste lokalt tilgjengelige `docs/data/forecast.json` (generert 2026-09-26T21:00Z, FØR noen av denne øktens rettelser - bw_dir der er derfor rene rå "mot"-verdier gjennomgående) brukt til å simulere fiksen: hver rå verdi + 180, sammenlignet mot facing.

| Spot | facing | Timer m/retning | >150° FØR | >150° ETTER | Maks avvik FØR | Maks avvik ETTER |
|---|---|---|---|---|---|---|
| Grøtfjord | 295 | 58 | 34 | **0** | 179,0 | 91,0 |
| Ersfjordstranda | 315 | 58 | 48 | **0** | 155,0 | 121,0 |
| Unstad | 294,8 | 58 | 58 | **0** | 179,9 | 2,8 |
| Russelv | 315 | 58 | 0 | 0 | 125,0 | 139,0 |
| Lenangsøyra | 0 | 58 | 0 | **4** | 75,0 | 172,3 |
| Steinkrøssa | 45 | 58 | 0 | **31** | 74,0 | 177,0 |

**Ikke helt som forventet.** For de tre "rett-på"-spotene (Grøtfjord, Ersfjordstranda, Unstad) forsvinner avviket helt, som ventet - den gamle, ukonverterte koden sammenlignet en "mot"-verdi direkte mot facing, og en god, rett-på treff har "mot" ≈ facing + 180, altså nesten nøyaktig den falske "180 grader ut fra stranda"-profilen sikringen fanget opp.

For Lenangsøyra og Steinkrøssa er bildet motsatt: FØR fiksen var (den feilaktig utolkede) retningen tilfeldigvis nær facing der (74-75°), så sikringen slo aldri inn. ETTER fiksen viser den korrekt konverterte retningen derimot ofte 150-177° avvik - altså bølger som (ifølge BarentsWatch, riktig lest) beveger seg nesten rett bort fra disse to strendene i mange av timene. Dette kan være ekte (begge er fjord-spots der lokal vindsjø ofte ikke følger noe svellvindu - CLAUDE.md sin faste observasjon for Lenangsøyra 26.09 sier nettopp "bølgene i Ullsfjorden kom fra vest", ikke fra retningen som treffer stranda), men det er ikke bekreftet, og det motsier den opprinnelige antagelsen om "nær-null overalt". Tabellen er bygget på ett gammelt, lokalt øyeblikksbilde (fra FØR fiksen) med en simulert +180 lagt på etterpå - ikke ferske BarentsWatch-tall hentet med den rettede koden. Den ferske, ekte sjekken kommer først når GitHub Actions kjører på nytt med ekte nøkler.

### Unstad i morgen kl. 10 (2026-09-27T08:00Z) - kjeden med korrekt retning
Kan ikke hentes ferskt lokalt (ingen BarentsWatch-nøkler), men regnet med samme inndata som testene 9.1/9.2 over (den ekte hendelsens fangede rådata, nå riktig konvertert):

| | Før fiksen (rå 115 brukt direkte) | Etter fiksen (rett konvertert) |
|---|---|---|
| BarentsWatch-retning, rått ("mot") | 115 | 115 |
| BarentsWatch-retning, internt ("fra") | 115 (ukonvertert - feilen) | **295** |
| `spot_direction_factor` | 1,0 (nøytral, tvunget av feilflagget) | 1,0 (ekte - nesten blink mot facing 294,8) |
| `spot_direction_error` | True | **False** |
| `uncertain` | True | **False** |
| Surfehøyde | 0,7 m (sett ca. 0,9 m) | 0,7 m (sett ca. 0,9 m) - uendret tall, men nå av RIKTIG grunn |
| Stjerner | 0 (1 uten vind) | 0 (1 uten vind) - sidevinden (8 m/s, kast 13) og den beskjedne høyden holder det lavt uansett |

Den ferske, faktiske appen vil vise dette først etter neste "Hent varsel"-kjøring i GitHub Actions (hver 3. time, ekte BarentsWatch-nøkler) - lokal kjøring her ga bare tom BarentsWatch-data (samme kjente begrensning), så `docs/data/forecast.json` er IKKE endret/pushet fra denne økten.

### Fysikk-kontrollør: **SPØR THEODOR**
Kjørt før commit. Kontrolløren gravde selv videre i git-historikken (fant at `def7a59` sin begrunnelse - "Unstad kl. 17:00 UTC = 296" - med stor sannsynlighet var et allerede konvertert tall, siden `9785e1b` sin konvertering var aktiv i koden på det tidspunktet; dette styrker denne rundens konklusjon). Hovedinnvendingen: `spot_direction_factor()` gir en REELL straff (faktor 0) for 60-150 grader avvik, men 150-graders-sikringen tvinger faktoren til NØYTRAL (1,0) for alt over 150 grader - så når Lenangsøyra/Steinkrøssa sin korrekt konverterte retning nå ofte havner over 150 grader (kjent, fysisk usannsynlig retning, ikke "ukjent"), hopper faktoren fra 0 til 1,0, altså RIKTIG VEI TIL VERRE for en modell som skal reflektere fysikken. Pekte på at CLAUDE.md sin stopp-regel ("flytter stjernene med 2 eller mer ... vis tabell og stopp") ikke var sjekket for disse 35 timene - bare >150-grense-tellingen.

**Sjekket direkte, med faktiske tall (etter kontrollørens spørsmål):** kjørte `rate()` på alle 35 berørte timer (rå vs. rettet retning), med ekte forecast-inndata for hver time.

| Spot | Timer over 150° (rettet) | Stjerner FØR i noen av dem | Stjerner ETTER i noen av dem | bw_height i disse timene |
|---|---|---|---|---|
| Lenangsøyra | 4 | 0 (alle) | 0 (alle) | 0,18-0,21 m |
| Steinkrøssa | 31 | 0 (alle) | 0 (alle) | 0,01-0,12 m |

**Ingen av de 35 timene endrer stjerner i det hele tatt** (langt under CLAUDE.md sin 2-stjerners stopp-grense) - `bw_height` er så lav i akkurat disse timene (0,01-0,21 m, godt under flat-sperren på 0,35 m) at retningsfaktoren aldri får noe å virke på. Kontrollørens fysiske poeng (0→1,0-hoppet er prinsipielt feil vei for en KJENT dårlig retning) er fortsatt gyldig og bør løses senere - men det endrer ikke ratingen for noen reell time i det nåværende 48-timersvarselet.

**Ubesvarte spørsmål fra kontrolløren, til Theodor:**
1. Den rå loggen (Unstad, 2026-09-26T15:00Z, totalMeanWaveDirection=116) ligger i din Downloads-mappe, utenfor repoet - vil du at jeg legger den inn som en fixture i repoet (f.eks. `fetcher/testdata/`) slik at beviset er sporbart for alle, ikke bare deg?
2. Retningsfaktor-logikken sitt 0→1,0-hopp ved >150 grader (nøytral for "vet ikke", men brukes nå også for "vet, og det er en dårlig retning" på noen spots) - vil du at dette skal skilles fra hverandre (f.eks. en egen, lavere faktor for "kjent, men peker ut fra stranda" i stedet for nøytral 1,0)? Ikke noe hastverk siden det ikke påvirker stjernene nå, men det er en reell, prinsipiell unøyaktighet.
3. Gitt at dette er tredje reversering av samme konvensjon på under et døgn: commit nå på dette bevisgrunnlaget (rå logg + konsistent git-arkeologi + alle tester grønne + ingen stjerneendring), eller vente på en fersk BarentsWatch-henting fra neste GitHub Actions-kjøring før konvensjonen låses?

---

## Theodors svar, og implementasjonen

Theodor svarte ja på alle tre spørsmålene, med presise instrukser for punkt 2 (se under). Committer og pusher nå, per svar på punkt 3.

### 1. Fixture i repoet
`fetcher/fixtures/bw_raw_unstad_2026-09-26.json` - de rå feltene fra GitHub Actions-loggen (punkt, tidspunkt, `totalMeanWaveDirection`, høyde, periode), ingen hemmeligheter (loggen hadde allerede maskert `BW_CLIENT_ID`/`BW_CLIENT_SECRET`/`BW_POINT_URL` med `***` - dobbeltsjekket, ingenting av det havnet i fixturen). Ny test 7.5c i `fetcher/test_rating.py` leser fixturen, kjører den gjennom den ekte `sources.barentswatch_point()` (mokker bare HTTP-laget), og bekrefter 116 → 296 og avvik fra Unstad sin facing under 5 grader (fikk 1,2 grader).

### 2. Retningsfaktoren over 150 grader: fra nøytral til ekte straff
Presis instruks fra Theodor: siden konvensjonen nå er riktig, betyr >150 grader avvik at bølgene FAKTISK går ut fra land (typisk vindsjø fra land) - en kjent retning, ikke en ukjent/mistenkelig en. Endret i `fetcher/rating.py`:

- `spot_direction_factor()`: over 150 grader gir nå **0,0** (ikke 1,0). Tredje returverdi (omdøpt fra "mistenkelig" til "ut fra land", feltnavn `spot_direction_offshore` i stedet for `spot_direction_error`) er fortsatt sann i dette tilfellet, men brukes nå bare til forklaringsteksten og fetch.py sin spotnivå-sikring (se under) - ikke lenger til å nøytralisere faktoren eller tvinge usikkerhet.
- `rate()` sin `uncertain`: fjernet leddet som tvang timen usikker ved >150 grader. Usikker nå bare når retning mangler HELT (som før).
- `rate()` sin `sources_disagree`: uendret oppførsel - leddet som ekskluderer >150-tilfellet fra å utløse "kildene uenige" alene er beholdt (samme grunn som før: retningsfaktoren gjør allerede jobben via selve høyden).
- `build_breakdown()`: ny forklaringstekst nøyaktig som Theodor spesifiserte: "Bølgene ved spoten går ut fra land. Trolig vindsjø fra land, ikke svell inn."
- CLAUDE.md sin 150-graders-linje omskrevet tilsvarende.

### 2c. Ny sikring på spotnivå (`fetch.py`)
Ny, testbar funksjon `convention_warning(hours, spot, name)`: blant timene med ekte svell ute mot vinduet (swell_offshore > 0,5 m OG directness > 0,5 - "eksponering" i dagens kodebase, siden del B/C sin lærte eksponering ikke er koblet inn ennå, se oppgave 2/3), sjekkes andelen med BarentsWatch-retning over 150 grader. Over halvparten: varsel i fet skrift ØVERST i kilderapporten ("Mulig feil i BarentsWatch-retningskonvensjonen for [spot]. Ratingen er ikke endret automatisk."). Testet med syntetiske 60 %/20 %-scenarioer (test 9.6 i test_rating.py) - slår inn ved 60 %, ikke ved 20 %, akkurat som spesifisert.

### Tester
Lagt til/endret i `fetcher/test_rating.py`:
- 7.5c: fixture-basert bevis (se punkt 1).
- 9.3 (ny, syntetisk - ingen ekte logg finnes ennå med et genuint >150-graders mønster og reelt svell): >150 grader med ekte svell tilstede gir retningsfaktor 0, `spot_direction_offshore` True, `uncertain` False, `sources_disagree` False, høyde 0.
- 9.4 (ny): ingen retning fra BarentsWatch i det hele tatt - uendret oppførsel (nøytral 1,0, usikker).
- 9.5 (tidligere 9.3, grensetesten): oppdatert - 151 grader gir nå (0,0, True, True), ikke (1,0, True, True).
- 9.6 (ny): `convention_warning()` testet direkte med syntetiske timer.
- Omdøpt alle `spot_direction_error`-referanser til `spot_direction_offshore` i eksisterende tester (Grøtfjord 26.09, 9.1/9.2).

`fetcher/test_rating.py` og `fetcher/test_pipeline.py` kjører begge grønt.

### 2-stjerners stoppregelen: sjekket for HELE endringen
**Rettet av fysikk-kontrolløren sin andre gjennomgang** (se under): min første versjon av denne tabellen sammenlignet feil ting - den NYE `rate()` kjørt to ganger (rå kontra +180-konvertert retning), ikke den FAKTISK deployede koden (`a19624c`, forrige commit) mot den nye. Riktig sammenligning: lastet `a19624c` sin `rating.py` og den nye (working tree) som to separate moduler, kjørte begge på ALLE 348 timer (58 timer × 6 spots) i siste lokalt tilgjengelige `docs/data/forecast.json`, med rå BarentsWatch-retning inn i den gamle koden (slik den faktisk oppførte seg) og korrekt konvertert retning inn i den nye:

| Spot | Timer sjekket | Maks \|stjerner ny − stjerner gammel\| | Timer med endring ≥ 2 |
|---|---|---|---|
| Grøtfjord | 58 | 0 | 0 |
| Ersfjordstranda | 58 | 0 | 0 |
| Russelv | 58 | 0 | 0 |
| Lenangsøyra | 58 | 0 | 0 |
| Steinkrøssa | 58 | 0 | 0 |
| Unstad | 58 | 0 | 0 |

Ingen spot, ingen time, endrer stjerner i det hele tatt mot den faktisk deployede koden. CLAUDE.md sin stoppregel er dermed IKKE utløst - enda tryggere enn først antatt.

### Fysikk-kontrollør, andre gjennomgang (av implementasjonen av Theodors svar): **MÅ RETTES**, kun i STATUS.md
Kjørte selv `fetcher/test_rating.py` og `fetcher/test_pipeline.py` (begge grønne), og en uavhengig etterregning (a19624c sin rating.py mot den nye, på alle 348 ekte timer). Fant koden selv fysisk og logisk konsistent med Theodors instrukser: `spot_direction_error` er konsekvent omdøpt til `spot_direction_offshore` overalt (null gjenværende treff), forklaringsteksten er ordrett lik spesifikasjonen, `sources_disagree` sin logikk har ingen udekket hull (de tre disjunktene er uavhengige signaler, det ekskluderte leddet dekkes uansett av at h dempes til nesten 0 av selve faktoren), fixturen inneholder ingen hemmeligheter, og pekte i tillegg på at den gamle koden hadde et diskontinuitetsbrudd (0,0→1,0 rett ved 150/151 grader) som nå er borte (0,0 på begge sider). Fant to unøyaktigheter i STATUS.md (ikke i koden): tabellen over sammenlignet feil kodeversjoner (rettet over, riktig tall er nå 0 for alle spots), og "6 faste observasjoner" var feil telling (CLAUDE.md har 5, rettet over). Blokkerer ikke committen Theodor allerede har godkjent.

Committer og pusher nå, per Theodors svar på punkt 3.

---

## Oppgave 2: koble del C inn i ratingen - FERDIG, Theodor sa ja (etter to rettelser)

### Hva som er gjort
- **Ny fil `fetcher/exposure.py`**: avhengighetsfri (ingen basemap/shapely) kjerne med `spot_checksum()`, flyttet ut fra `exposure_baseline.py` slik at `fetch.py` kan sjekke sjekksummen uten å dra inn de tunge geometriavhengighetene i hver ordinære kjøring. `exposure_baseline.py` importerer nå funksjonen derfra i stedet for å ha sin egen kopi - ingen endring i selve hash-algoritmen, bekreftet ved at alle 6 spots sine sjekksummer fortsatt stemmer mot dagens `data/exposure_baseline.json`.
- **`rating.py`**: ny `exposure_override_cap(d, spot)` (leser spots.json sin `exposure_override`-liste) og ny `exposure(d, spot)` - bruker `spot["exposure_smoothed"]` (360 tall, satt av fetch.py) når den finnes, ellers `directness()` (vindu+skyggekurve) som reserve. Override-taket gjelder uansett hvilken av de to som brukes. `directness()` selv er UENDRET - beholdt som fallback og av exposure_baseline.py sin egen dokumentasjon.
  - `spot_height()` sin svell_ute-gren bruker nå `exposure()` i stedet for `directness()`.
  - `rate()` sin `dir_hit` (brukt til `sources_disagree` sin 0,667-grense) bruker nå `exposure()`.
  - BarentsWatch-timer uendret i selve høyden - `barentswatch_height()` bruker fortsatt bare BarentsWatch sin egen retning ved punktet, ikke eksponering.
- **`fetch.py`**: ny `resolve_exposure(spot, exposure_data, name)` - slår opp `data/exposure_baseline.json`, sjekker sjekksummen mot spots.json sitt NÅVÆRENDE innhold, og returnerer enten de glattede tallene eller en advarsel (aldri begge). Advarsel skrives i kilderapporten. Mangler data eller feil sjekksum: spoten faller automatisk tilbake til `directness()` via `exposure()` sin egen fallback.

### Fysikk-kontrollør fant en ekte, videre-rekkende feil FØR jeg rakk å committe - rettet
Etter at jeg viste deg den første før/etter-tabellen (2 timer, ≥2 stjerner) og du sa ja, kjørte jeg fysikk-kontrolløren likevel (som vanlig, før commit). Den fant en reell dobbelttelling av retning, som gjorde den tabellen jeg viste deg FEIL - jeg committer derfor IKKE på det grunnlaget, og bygger en ny, korrekt tabell under.

**Feilen**: `rate()` brukte `dir_hit` (nå `exposure()`, før `directness()`) til å dempe Hb (bruddhøyden) EN GANG TIL, etter at samme faktor allerede var brukt til å regne ut selve høyden `h` i `spot_height()` (for svell_ute: `h = swell_offshore * transfer * exposure(...)` - allerede dempet). Siden Hb ∝ H^0,8 (Komar og Gaughan), arver Hb automatisk dempingen fra h - å gange Hb med samme faktor en gang til ga effektiv eksponent ~1,8 i stedet for ~1,0. Samme feil fantes for BarentsWatch (`spot_direction_factor` dempet både `h` i `barentswatch_height()` OG `hb_damping` etterpå). Feilen har vært i koden siden lenge (med `directness()`), men var nesten usynlig fordi `directness()` stort sett er ≈1,0 midt i et vindu og `spot_direction_factor` stort sett er ≈1,0 for velfungerende, velrettede ekte hendelser - `exposure()` sin videre spennvidde MIDT i et vindu gjorde den synlig og betydelig for første gang.

**Rettelsen**: `hb_damping` er nå 1,0 (ingen ny demping) for både `svell_ute` og `barentswatch`, siden begge sine `h` allerede har riktig faktor bakt inn. Bare `metno_korrigert` (reserven sin reserve, bruker verken eksponering eller spot_direction_factor i egen `h`) dempes fortsatt med `dir_hit`. Se `rating.py` sin oppdaterte kommentar ved `hb_damping`.

### Tester
10 nye tester i `fetcher/test_rating.py` (10.1-10.6) for eksponering/override/fallback/resolve_exposure. Alle eksisterende tester kjørt på nytt etter `hb_damping`-rettelsen - ingen assert måtte endres (de faste observasjonene og synteste testene traff alle enten faktor 0, faktor 1,0, eller (for 8.2b) nettopp det tilfellet rettelsen IKKE endrer noe for). `fetcher/test_rating.py` og `fetcher/test_pipeline.py` kjører begge grønt. Alle 5 faste observasjoner i CLAUDE.md holder fortsatt.

### 2-stjerners stoppregelen: UTLØST - ny, fullstendig tabell

Rettelsen endrer resultatet for ALLE reserve-modell-timer med delvis eksponering (ikke bare de to jeg viste deg først) - både opp (tidligere dobbelt-straffede kant-svell får nå riktig, høyere verdi) og ned (Steinkrøssa sitt tilfelle, se under). Sammenlignet faktisk committet kode (`HEAD`) mot ny kode (eksponering + rettelsen sammen), alle timer i `docs/data/forecast.json`:

| Spot | Timer sjekket | Maks stjerneendring | Timer med endring ≥ 2 | Timer med endring ≥ 1 |
|---|---|---|---|---|
| Grøtfjord | 111 | 0 | 0 | 0 |
| Ersfjordstranda | 111 | 3 | **7** | 8 |
| Russelv | 111 | 1 | 0 | 2 |
| Lenangsøyra | 111 | 1 | 0 | 2 |
| Steinkrøssa | 111 | 2 | **1** | 4 |
| Unstad | 111 | 2 | **5** | 10 |

13 timer (av 666 sjekket) flytter seg 2 eller mer, alle unntatt én OPP (rettelsen fjerner en tidligere over-straff av kant-svell):

| Spot | Tid | Retning ute | Svell ute | FØR (stjerner) | ETTER (stjerner) |
|---|---|---|---|---|---|
| Ersfjordstranda | 30.09 00-06Z (7 timer) | 324-326° (vinduets ytterkant, vindu 294-320) | 2,0-2,3 m | 0 | 2-3 |
| Unstad | 30.09 00-04Z (5 timer) | 252-253° (vinduets ytterkant, vindu 253-335) | 1,7-2,0 m | 0 | 2 |
| Steinkrøssa | 29.09 21:00Z | 324° (9° inn i vinduet 315-16) | 0,66 m | 2 | 0 |

### Theodors ja med én endring, og en tredje runde på hb_damping

Theodor sa ja til at Unstad sin dobbeltstraff fjernes (fri linje, rå eksponering 1,0 - riktig at ingen ekstra demping trengs), men pekte på at Ersfjordstranda sitt tilfelle (324-326°) er en ANNEN situasjon enn Unstad sin, selv om begge lå "i kanten": Ersfjordstranda sine retninger er 4-6 grader UTENFOR både vinduet og den frie sektoren - svellet når spoten bare ved å bøye seg rundt land (diffraksjon), akkurat som Grøtfjord 25.09.2026 (3 grader utenfor, observert helt flatt). Den ekstra Hb-dempingen fanget noe EKTE der, ikke bare dobbelttelling - diffraktert svell bygger seg empirisk dårligere opp enn Komar og Gaughan sin formel (laget for åpen kyst) tror. Grøtfjord slipper unna fordi `exposure_override` (taket 0,2) uansett holder den timen flat - Ersfjordstranda har ikke noe tilsvarende tak.

**Rettelse (tredje runde)**: ny `raw_exposure_zero(d, spot)` i `rating.py` - sann når RÅ geometrisk eksponering (før glatting, fra `exposure_baseline.py` sin `raw`-liste, nå også lastet av `fetch.py` som `spot["exposure_raw"]`) er nøyaktig 0 for retningen, altså INGEN fri siktlinje finnes i det hele tatt. Mangler rådata (fallback): tilsvarer `degrees_outside(d, spot) > 0`, samme konsept i `directness()` sin egen vindu-modell. `rate()` sin `hb_damping` for `svell_ute`:
- Rå eksponering over 0 (fri eller delvis fri linje): ingen ekstra demping (1,0) - dette var selve dobbelttelling-rettelsen fra forrige runde, uendret.
- Rå eksponering nøyaktig 0 (bare diffraksjon rundt land): dempes MED eksponeringen (samme som tidligere, "gammel" oppførsel) - empirisk begrunnet av Grøtfjord 25.09.2026, nå skrevet inn i CLAUDE.md.

BarentsWatch uendret (alltid 1,0, som i forrige runde) - gjelder bare reservemodellen.

**Nye tester (11.1-11.4)**: `raw_exposure_zero()` sin fallback- og ekte-data-oppførsel, Ersfjordstranda 325° (bak odden) mot 318° (innenfor) - klart lavere surfehøyde og maks 1 stjerne, Unstad 253° (fri linje) - ingen ekstra demping.

### Endelig før/etter-tabell (etter alle tre rundene)

| Spot | Timer sjekket | Maks stjerneendring | Timer med endring ≥ 2 | Timer med endring ≥ 1 |
|---|---|---|---|---|
| Grøtfjord | 111 | 0 | 0 | 0 |
| Ersfjordstranda | 111 | **0** | 0 | 0 |
| Russelv | 111 | 1 | 0 | 2 |
| Lenangsøyra | 111 | 1 | 0 | 2 |
| Steinkrøssa | 111 | 2 | **1** | 4 |
| Unstad | 111 | 2 | **5** | 10 |

Ersfjordstranda er nå helt tilbake til 0 endring i det hele tatt (nøyaktig samme resultat som før noen av de tre rettelsene - rå eksponering 0 der gir akkurat samme demping som den gamle koden alltid ga). Unstad sine 5 timer (252-253°, opp 0→2) og Steinkrøssa sin ene time (324°, ned 2→0) er UENDRET fra forrige tabell, akkurat som Theodor forventet. Alle 5 faste observasjoner i CLAUDE.md bekreftet å holde (full testkjøring grønn). CLAUDE.md sin 2-stjerners regel treffer nå bare Steinkrøssa og Unstad, begge allerede godkjent.

### Fysikk-kontrollør fant én til - rettet før commit
Kjørt en tredje gang på denne rettelsen. Fant at Grøtfjord sin `exposure_override` (311-330, tak 0,2) overlapper med 317-330, der RÅ eksponering allerede er 0,0 (bekreftet i `data/exposure_baseline.json`) - uten et unntak ville `raw_exposure_zero()` sin ekstra Hb-demping lagt seg OPPÅ taket, samme type dobbeltstraff som runde 2 sin feil, bare i en smalere sone. Egen sjekk: Grøtfjord, 320 grader, 4 m svell/14 s - med begge dempingene stablet ga det 0 stjerner (0,16-0,24 m), med bare taket 3 stjerner (0,98 m).

**Rettelse**: `rate()` sin `svell_ute`-gren dropper nå den ekstra diffraksjons-dempingen når `exposure_override_cap()` dekker retningen - overriden ER allerede den manuelle, kalibrerte sannheten for akkurat den retningen (satt av Theodor, nettopp for grader der geometrien ikke kan stoles på), og skal ikke dempes en gang til. Ny test 11.5 (ekte tall fra `data/exposure_baseline.json`, ikke syntetisk) dekker nå kombinasjonen override + rå eksponering 0. Bekreftet at dette IKKE endrer noen av tallene i tabellen over (Grøtfjord viser fortsatt 0 endring i dagens 111-timers varsel - funnet var en LATENT feil, ikke noe som traff en reell time ennå).

**Committer og pusher nå, per Theodors instruks (punkt 6) - tallene ble som forventet.**

---

## Oppgave 3: kysttoleranse i check_spot.py - RAPPORT, ingen swell_window endret

Theodor sa ja til oppgave 2 (begge stjernefallene "fysisk rimelige, gjelder små bølger") og ba om en oppfølging: Steinkrøssa sitt fall ved 324 grader kan skyldes at check_spot.py sin gamle 2 km-kysttoleranse ga et for bredt svellvindu (linja kan ha krysset tuppen av en odde - Bøvær - nær spoten). Lagt inn som ROADMAP oppgave 3, gjort nå. **Konklusjon på forhånd: hypotesen holder IKKE for Steinkrøssa sitt spesifikke tilfelle - se under for hvorfor. Ingen swell_window er endret.**

### 1. check_spot.py oppdatert
`fetcher/check_spot.py` sin `free_distance()` bruker nå samme kysttoleranse som `exposure_baseline.py`: 300 m (var 2 km), med samme sammenhengende-land-fra-spoten-logikk (finere 0,05 km oppløsning i kystsonen, deretter vanlig 0,1 km oppløsning). Verktøyet er ikke kjørt automatisk noe sted - det er fortsatt et manuelt CLI-verktøy (`python fetcher/check_spot.py <lat> <lon> <fra> <til>`), så denne endringen påvirker ingenting før noen kjører det på nytt for hånd.

### 2. Fri sektor på nytt for alle spots (300 m toleranse)

| Spot | Dagens swell_window | Ny fri sektor (300 m) | Blokkerte retninger i dagens vindu |
|---|---|---|---|
| Grøtfjord | [286, 310] | [286, 315] | Ingen - fri sektor er faktisk BREDERE enn dagens vindu |
| Ersfjordstranda | [294, 320] | [288, 320] | Ingen - fri sektor er bredere enn dagens vindu |
| Russelv | [[5,15],[349,356]] | [[5,15],[349,356]] | Ingen - identisk |
| Lenangsøyra | [15, 23] | [15, 23] | Ingen - identisk |
| Steinkrøssa | [315, 16] | [315, 16] | Ingen - identisk |
| Unstad | [253, 335] | [253, 335] | Ingen - identisk |

**Merk: Ersfjordstranda sin frie sektor er [288, 320], men swell_window er satt til [294, 320]** - 6 grader smalere i underkant enn det som faktisk har fri linje til åpent hav (samme mønster som Grøtfjord, der fri sektor [286,315] også er bredere enn vinduet [286,310]). Ikke endret her - lagt til i ROADMAP.md sin "Venter på Theodor"-liste som et mulig forslag, krever eget ja.

**Ingen spot har noen retning i dagens svellvindu som mister fri linje til åpent hav med den strengere 300 m-toleransen.** Farstadsanden er ikke lagt inn i spots.json ennå (bekreftet), så den er ikke med i denne sjekken.

### 3. Steinkrøssa, detaljert: hvilke retninger 315-16 krysser land?

**Ingen.** Skannet hver grad fra 295 til 330 med den nye 300 m-toleransen:

| Grader | Land, avstand | Fri linje | Status |
|---|---|---|---|
| 295-311 | 0,50 km (spotens egen nærmeste kystlinje) | 0,3-0,5 km | BLOKKERT |
| 312-314 | 0,50 km | 0,5 km | BLOKKERT |
| **315-330** | ingen land innen 150 km | 150 km | **ÅPEN** |

Overgangen fra blokkert til åpen skjer brått, akkurat ved 314/315 grader, og er UENDRET av kysttoleranse-rettelsen (samme overgang med både gammel 2 km- og ny 300 m-toleranse) - dette bekrefter samme funn som allerede stod i STATUS.md fra oppgave 1 ("Steinkrøssa rett under 315 grader (314°): blokkert. 315° og oppover: åpent"). Hypotesen om at en for slapp toleranse lot linja "hoppe over" en odde stemmer altså IKKE her: grensa er den samme uansett toleranse, ikke en gradvis overgang tolerance-innstillingen kunne flyttet.

**Hva er det som faktisk blokkerer 295-314?** Land bare 0,5 km unna, funnet å være ca. 184 grader bredt på tvers sett fra spoten ved den avstanden - i praksis spotens egen, nære kystlinje (ikke en liten, fjern skjærodde). Dette er land RETT VED spoten selv i den retningen, ikke et smalt Bøvær-skjær lenger ute.

**Hvorfor faller da eksponeringen ved 324 grader, midt i det åpne vinduet?** Ikke fordi 324 selv krysser land (den gjør ikke det, verken med gammel eller ny toleranse) - `exposure_baseline.py` sin RÅ verdi ved 324 er faktisk 1,0. Det er GLATTINGEN (normalfordeling, sigma 10 grader) i `exposure_baseline.py` som sprer den ekte, allerede kjente blokkeringen ved 295-314 innover i det åpne vinduet - 324 ligger bare 10 grader fra kanten (314), rett i smøreradiusen. Glattet verdi ved 324 blir da 0,83 (rå 1,0 dratt ned av de nære, blokkerte naboretningene), ikke fordi selve linja ved 324 treffer noe.

### Om de "buede linjene" i tegningen din
Verdt å presisere: geometrien i `check_spot.py`/`exposure_baseline.py` går i RETTE linjer fra spoten (ren siktlinje mot land) - den bøyer ikke rundt noe i selve målingen. Den bøyningen du så i tegningen din tilsvarer trolig glattingen over (som ETTERPÅ sprer en skarp kant utover, en grov tilnærming til at ekte svell diffrakterer/bøyer seg rundt en odde) - ikke noe kurvet i selve sikt-sjekken.

### Konklusjon: ingen swell_window bør endres
Alle 6 vinduene har fortsatt full fri linje til åpent hav med den strengere 300 m-toleransen - toleranse-hypotesen forklarer ikke Steinkrøssa sitt stjernefall. Den reelle årsaken (Gaussian-glatting av en allerede kjent, korrekt identifisert blokkering rett ved spoten, som brer seg 10-15 grader inn i et ellers åpent vindu) er en bevisst modelleringsvalg i del C (samme glatting som ga Lenangsøyra sine lave 0,55-0,59-verdier i oppgave 1), ikke en feil i selve kystlinjegeometrien eller i check_spot.py sin vindu-beregning. **Ingen endring foreslått i noen swell_window.** Kysttoleranse-oppdateringen i check_spot.py (punkt 1) er likevel verdt å beholde for konsistens med exposure_baseline.py, selv om den ikke endret noe resultat her.

---

## Gjenstår (ROADMAP.md)
- Oppgave 2 (koble del C inn i ratingen): implementert og testet, korrigert etter fysikk-kontrollør sitt dobbelttelling-funn, venter på FORNYET "ja" fra Theodor (se eget avsnitt).
- Oppgave 3 (kysttoleranse i check_spot.py): ferdig, rapportert over. Ingen swell_window endret.
- Oppgave 4 (del B, lært eksponering): ikke startet.
- Oppgave 5 (Unstad sitt BarentsWatch-rutepunkt): delvis forsøkt (høyde sammenlignet mot nettsiden, matcher godt), men IKKE fullført - kunne ikke fastslå nøyaktig hvilket rutepunkt API-et velger eller avstand/retning fra punktet vi ba om, uten `gh`/API-tilgang.
- Venter på Theodor-avsnittet: uendret, ingen av de tre punktene er rørt.
