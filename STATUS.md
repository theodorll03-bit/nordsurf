# Nordsurf: status

## Oppsummering (sist oppdatert 27.09.2026, under arbeid)

- **Oppgave 1 (ROADMAP)** ferdig: `exposure_baseline.py` bruker nå bredde-på-tvers/skyggelengde-fysikk og 300 m kysttoleranse. Tre av fire "ferdig når"-kriterier oppfylt fullt ut; det fjerde (Grøtfjord 311-330° lav eksponering fra geometri alene) er bare DELVIS oppfylt - se eget avsnitt.
- **HASTER-oppgave** (utenom kø, på direkte beskjed): Unstad i morgen kl. 10 viste feilaktig 0,0 m/"Kildene er uenige". Sikringen (150 graders grense) er bygget, testet og pushet. Fant at praktisk talt hele 48-timersvarselet for Grøtfjord, Ersfjordstranda og Unstad har samme 150-180 graders avvik.
- **Motgående vindsjø-hypotesen (offshorevind) testet mot dagens data: HOLDER IKKE.** Se eget avsnitt - bare 26 % av de anomale timene har offshorevind, og Unstad er rammet i 49 av 49 timer uavhengig av vindretning.
- **Ny hypotese (kilde/fileSource varierer): kan IKKE testes fullt ut herfra.** `diagnose_bw_direction.py` er utvidet til å hente source/fileSource, begge punkter og 48 timer, og til å sammenligne mot det som står i forecast.json - men jeg har verken `gh` CLI eller BarentsWatch-nøkler lokalt, så jeg kan ikke kjøre den selv. Fant derimot en LAGRET logg fra forrige diagnose-kjøring (26.09, i din Downloads-mappe) som gir et konkret, foreløpig funn - se eget avsnitt. Trenger deg til å trigge workflowen på nytt for de fulle tallene.
- Ikke gjort noen kodeendring i rating.py/sources.py/fetch.py - bare i diagnoseverktøyet, som instruert.
- Oppgave 2, 3, 4 i ROADMAP.md: ikke startet ennå.

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

## Gjenstår (ROADMAP.md)
- Oppgave 2 (koble del C inn i ratingen): ikke startet.
- Oppgave 3 (del B, lært eksponering): ikke startet.
- Oppgave 4 (Unstad sitt BarentsWatch-rutepunkt): delvis forsøkt (høyde sammenlignet mot nettsiden, matcher godt), men IKKE fullført - kunne ikke fastslå nøyaktig hvilket rutepunkt API-et velger eller avstand/retning fra punktet vi ba om, uten `gh`/API-tilgang.
- Venter på Theodor-avsnittet: uendret, ingen av de tre punktene er rørt.
