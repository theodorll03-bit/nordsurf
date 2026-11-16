# T2c: tidevann på Unstad (Lofoten Surfsenter, 09.11.2026)

Laget av `tools/unstad_tidevann_rapport.py`. Bare rapport: ingenting i appen er endret.

Påstanden fra Lofoten Surfsenter: «Lofoten er best på lavvann.»

## Kort svar

- **To av de fire faste observasjonene var gode økter på høyvann:** 26.09 (4 stjerner, 75–93 % av flo) og 28.09 («firing», 4 til 5 stjerner, 75–100 %). 05.10 gikk fra høyvann til middels. Bare 27.09 var på lavvann. Regelen må derfor være myk.
- En regel etter Farstadsanden-mønsteret (V1 eller V2, vektet fradrag 0,7) tar alltid en hel stjerne på høyvann. Den ville tatt 26.09 fra 4 til 3 stjerner i varselet som lå ute, og fjernet 8 til 14 av de 23 lyse timene med 4 stjerner eller mer 24.09–14.10.
- Den myke varianten (V3, lav og middels foretrukket, vektet fradrag 0,35) lar 26.09 stå på 4. Den koster bare en stjerne når noe annet også trekker litt ned.
- Ingen time flytter seg 2 eller mer i noen variant, verken de neste 48 timene eller bakover.
- **Anbefaling: V3, hvis regelen skal inn nå.** Ingenting er endret. Se forslaget nederst.

## Slik deler tide.py inn

Nivået regnes fra 0 (fjære) til 1 (flo) mellom to nabovendepunkter. Under en tredel er «lav», over to tredeler «høy», ellers «middels». En tidevannssyklus er ca. 12,4 timer, så hver tilstand varer omtrent like lenge: rundt en tredel av døgnet hver.

Unstad har i dag ingen tidevannsregel («spoten tåler alt»). Varianter som er regnet (vekt 0,7, den Unstads lokale regler har fra før):

- **V1:** bare lav er foretrukket, fradrag 1. Vektet fradrag 0,7 stjerne utenfor det foretrukne.
- **V2:** lav og middels er foretrukket, fradrag 1 (som Farstadsanden). Vektet fradrag 0,7 stjerne utenfor det foretrukne.
- **V3:** lav og middels er foretrukket, fradrag 0,5 (myk). Vektet fradrag 0,35 stjerne utenfor det foretrukne.

Fradraget legges sammen med vind og andre fradrag før avrunding (0,5 rundes opp). Et fradrag på 0,7 koster derfor alltid en stjerne. Et fradrag på 0,35 koster ingenting alene, men en stjerne sammen med et lite vindfradrag (over 0,15). En femte stjerne krever uansett foretrukket tidevann når spoten har en slik regel (`five_star_losses`).

## 1. Tidevannet ved de faste observasjonene

Timene er hentet fra varselet som lå ute da (siste kjøring før timen), og stjernene er regnet på nytt med dagens kode.

| Observasjon | Time (norsk tid) | Tidevann | Stjerner i dag | V1 | V2 | V3 |
|---|---|---|---|---|---|---|
| 26.09 ca. kl. 14:45: over hodet, tønner, offshore. 4 stjerner | 14:00 | høy (93 %, faller) | 4 | 3 | 3 | 4 |
| 26.09 ca. kl. 14:45: over hodet, tønner, offshore. 4 stjerner | 15:00 | høy (75 %, faller) | 4 | 3 | 3 | 4 |
| 27.09 morgen: rene linjer, bryst- til hodehøyt. Ca. 3 stjerner | 06:00 | lav (11 %, faller) | 3 | 3 | 3 | 3 |
| 27.09 morgen: rene linjer, bryst- til hodehøyt. Ca. 3 stjerner | 07:00 | lav (1 %, faller) | 3 | 3 | 3 | 3 |
| 27.09 morgen: rene linjer, bryst- til hodehøyt. Ca. 3 stjerner | 08:00 | lav (2 %, stiger) | 3 | 3 | 3 | 3 |
| 27.09 morgen: rene linjer, bryst- til hodehøyt. Ca. 3 stjerner | 09:00 | lav (16 %, stiger) | 3 | 3 | 3 | 3 |
| 28.09 ca. kl. 13: «Safe to say it's firing». 4 til 5 stjerner | 12:00 | høy (75 %, stiger) | 0 | 0 | 0 | 0 |
| 28.09 ca. kl. 13: «Safe to say it's firing». 4 til 5 stjerner | 13:00 | høy (93 %, stiger) | 0 | 0 | 0 | 0 |
| 28.09 ca. kl. 13: «Safe to say it's firing». 4 til 5 stjerner | 14:00 | høy (100 %, stiger) | 0 | 0 | 0 | 0 |
| 28.09 ca. kl. 13: «Safe to say it's firing». 4 til 5 stjerner | 15:00 | høy (94 %, faller) | 0 | 0 | 0 | 0 |
| 05.10 kl. 09–12 | 09:00 | høy (98 %, faller) | 1 | 0 | 0 | 0 |
| 05.10 kl. 09–12 | 10:00 | høy (86 %, faller) | 2 | 1 | 1 | 1 |
| 05.10 kl. 09–12 | 11:00 | middels (64 %, faller) | 2 | 1 | 2 | 2 |
| 05.10 kl. 09–12 | 12:00 | middels (39 %, faller) | 2 | 1 | 2 | 2 |

Observasjoner med minst én time på høyvann: 05.10, 26.09, 28.09. Med minst én time på lavvann: 27.09.

Om 28.09: varselet som lå ute gir 0 stjerner i disse timene, også med dagens kode. Det er ikke vindstraffen (den trekker 0 stjerner, selv med 14–18 m/s fraland). Nullen kommer av at BarentsWatch-punktet viste 0,7–0,8 m og svellandelen var 0,20–0,37. Høyden ved spoten havner da under flat-grensa på 0,35 m, og timen merkes «blåst ut» på grunn av lav svellandel. Den faste observasjonen i testene bruker egne inndata og er ikke berørt. Tidevannet står fast: det fyrte på høyvann. Funnet er verdt å merke seg for seg selv: en økt som var god, sto som 0 i varselet. Det er samme BarentsWatch-punkt som i T2b (250 m ut).

## 2. Før og etter

### De neste 48 timene (kjøringen 2026-11-10T06:00Z)

48 timer, 48 med kjent tidevann: 18 lav, 11 middels, 19 høy. Timer med minst 1 stjerne i dag: 3 (lyse: 0).

| Variant | Timer som mister 1 stjerne | ... av dem lyse | Timer som flytter seg 2 eller mer | Lyse timer med 3+ stjerner før → etter | Lyse timer med 4+ før → etter |
|---|---|---|---|---|---|
| V1 | 2 | 0 | 0 | 0 → 0 | 0 → 0 |
| V2 | 2 | 0 | 0 | 0 → 0 | 0 → 0 |
| V3 | 0 | 0 | 0 | 0 → 0 | 0 → 0 |

Timer som går opp i noen variant: 0 (regelen kan bare trekke ned).

### 14 dager tilbake med inndata (30.09–14.10.2026)

336 timer, 336 med kjent tidevann: 134 lav, 70 middels, 132 høy. Timer med minst 1 stjerne i dag: 166 (lyse: 86).

| Variant | Timer som mister 1 stjerne | ... av dem lyse | Timer som flytter seg 2 eller mer | Lyse timer med 3+ stjerner før → etter | Lyse timer med 4+ før → etter |
|---|---|---|---|---|---|
| V1 | 95 | 54 | 0 | 44 → 28 | 16 → 7 |
| V2 | 64 | 35 | 0 | 44 → 34 | 16 → 12 |
| V3 | 14 | 10 | 0 | 44 → 42 | 16 → 16 |

Timer som går opp i noen variant: 0 (regelen kan bare trekke ned).

### Alle publiserte timer 24.09–14.10

444 timer, 444 med kjent tidevann: 176 lav, 93 middels, 175 høy. Timer med minst 1 stjerne i dag: 231 (lyse: 119).

| Variant | Timer som mister 1 stjerne | ... av dem lyse | Timer som flytter seg 2 eller mer | Lyse timer med 3+ stjerner før → etter | Lyse timer med 4+ før → etter |
|---|---|---|---|---|---|
| V1 | 128 | 69 | 0 | 68 → 49 | 23 → 9 |
| V2 | 84 | 43 | 0 | 68 → 58 | 23 → 15 |
| V3 | 19 | 11 | 0 | 68 → 66 | 23 → 23 |

Timer som går opp i noen variant: 0 (regelen kan bare trekke ned).

## Forslag (krever Theodors ja, ingenting er gjort)

1. **V3 for Unstad:** `tide_prefer: ["lav", "middels"]`, `tide_penalty_high: 0.5`, i Unstads `local_rules` (vekt 0,7 som i dag, vektet fradrag 0,35). Kilden «Lofoten Surfsenter, 09.11.2026» føres opp i CLAUDE.md under «Lokalkunnskap» og i `source`-feltet ved siden av dagens kilde.
2. **Bivirkning å kjenne til:** med en slik regel kan en time på høyvann aldri få den femte stjernen. 28.09 («4 til 5 stjerner») var på høyvann. Skal femte stjerne fortsatt være mulig på høyvann, må `five_star_losses` få et unntak for myke regler. Det er en kodeendring som ikke er gjort.
3. **Én vekt per spot:** `local_rules` har ett `weight`-felt. Unstads energiterskler og tidevannsregelen deler derfor vekten 0,7. Skal Surfsenterets regel ha egen vekt, må koden få vekt per regel.
4. **Testene fanger ikke forskjellen:** `test_rating.py` og `test_backtest.py` er grønne med alle tre variantene (kjørt 10.11 mot en kopi av spots.json per variant). Forskjellen mellom dem vises bare i varselet som lå ute, som i tabellene over. Kommer regelen inn, bør 26.09 kl. 14:45 med høyvann inn som egen test.
5. **Spørsmål til deg:** skal regelen gjelde flere Lofoten-spots? Surfsenteret sa «Lofoten», ikke «Unstad». For Unstad taler to av fire gode økter imot en hard regel. For de andre Lofoten-spotene finnes ingen observasjoner ennå.

