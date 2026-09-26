# Nordsurf: status

## Oppsummering (sist oppdatert 27.09.2026, under arbeid)

- **Oppgave 1 (ROADMAP)** ferdig: `exposure_baseline.py` bruker nå bredde-på-tvers/skyggelengde-fysikk og 300 m kysttoleranse. Tre av fire "ferdig når"-kriterier oppfylt fullt ut; det fjerde (Grøtfjord 311-330° lav eksponering fra geometri alene) er bare DELVIS oppfylt - se eget avsnitt.
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

## Gjenstår (ROADMAP.md)
- Oppgave 2 (koble del C inn i ratingen): ikke startet.
- Oppgave 3 (del B, lært eksponering): ikke startet.
- Oppgave 4 (Unstad sitt BarentsWatch-rutepunkt): ikke startet.
- Venter på Theodor-avsnittet: uendret, ingen av de tre punktene er rørt.
