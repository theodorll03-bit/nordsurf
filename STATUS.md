# Nordsurf: status

## Oppsummering (sist oppdatert 27.09.2026, under arbeid)

- **Oppgave 1 (ROADMAP)** ferdig: `exposure_baseline.py` bruker nå bredde-på-tvers/skyggelengde-fysikk og 300 m kysttoleranse. Tre av fire "ferdig når"-kriterier oppfylt fullt ut; det fjerde (Grøtfjord 311-330° lav eksponering fra geometri alene) er bare DELVIS oppfylt - se eget avsnitt.
- **HASTER-oppgave** (utenom kø, på direkte beskjed): Unstad i morgen kl. 10 viste feilaktig 0,0 m/"Kildene er uenige". Rotårsak ikke fastslått med sikkerhet, men en konkret sikring er bygget og testet. **Fysikk-kontrollør svarte SPØR THEODOR på denne** - se eget avsnitt, venter på beskjed før jeg går videre i køen.
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

### Et bekymringsfullt mønster (ikke bare denne ene timen)
Fant samme avvik i en ALLEREDE EKSISTERENDE, fast test (Grøtfjord 26.09, ekte data): `bw_dir=114` mot `facing=295`, ca. 179 grader avvik - praktisk talt identisk mønster.

| Time | Avvik fra facing | Svellandel (swell_share) |
|---|---|---|
| Unstad 26.09 kl. 17 (etablerte "fra"-konvensjonen) | ≈1° | 94 % (nesten ren svell) |
| Grøtfjord 26.09 (fast test) | ≈179° | 44 % (mye vindsjø) |
| Unstad i morgen kl. 10 | ≈180° | 70 % (en del vindsjø) |

**Uverifisert hypotese**: BarentsWatch sin `totalMeanWaveDirection` kan bruke en annen konvensjon (eller ha en datakvalitetsfeil) for den kombinerte sjøtilstanden når vindsjøandelen er stor nok til å dominere - bare 2 datapunkter, ikke bevist.

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

## Gjenstår (ROADMAP.md)
- Oppgave 2 (koble del C inn i ratingen): ikke startet.
- Oppgave 3 (del B, lært eksponering): ikke startet.
- Oppgave 4 (Unstad sitt BarentsWatch-rutepunkt): delvis forsøkt (høyde sammenlignet mot nettsiden, matcher godt), men IKKE fullført - kunne ikke fastslå nøyaktig hvilket rutepunkt API-et velger eller avstand/retning fra punktet vi ba om, uten `gh`/API-tilgang.
- Venter på Theodor-avsnittet: uendret, ingen av de tre punktene er rørt.
