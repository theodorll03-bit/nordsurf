# T2b: Unstad mot Flakstad (Lofoten Surfsenter, 09.11.2026)

Laget av `tools/unstad_flakstad_rapport.py`. Bare rapport: ingenting i appen er endret.

Påstanden fra Lofoten Surfsenter: «Unstad er nesten alltid større enn Flakstad.»

## Kort svar

- Varselet sier ikke det Surfsenteret sier. I de 55 timene med BarentsWatch er Unstad aldri større enn Skagsanden (0 større, 27 like, 28 mindre). I timene der minst én av dem har surf, er Unstad større i 32 % og mindre i 60 %.
- De er ikke for like fordi de deler noe. De har hvert sitt havpunkt og hvert sitt BarentsWatch-punkt. Transfer er lik (0,6, standard), men den brukes bare uten BarentsWatch.
- Forskjellen oppstår på Unstad-siden: BarentsWatch-punktet til Unstad ligger 250 m ut på 3,9 m dyp og viser median 0,48 av det punktet 700 m ut viser. Punktet 700 m ut viser 0,89 av Skagsandens. Kystmodellen gir altså omtrent like mye sjø i de to buktene i dette været, og Unstad-tallet halveres mellom 700 m og 250 m. Om det skyldes at punktet ligger i brenningen eller i le for nordlig sjø, kan ikke denne kjøringen avgjøre. Kort periode i punktet og svært lavt forhold på små dager ligner le.
- Været i denne kjøringen er lite typisk: kort vindsjø fra nord og nordnordvest (7–9 s), som treffer Skagsanden rett på og ligger i kanten av eller utenfor Unstads vindu. At Skagsanden (vindu til 4°) er størst i nordlig sjø, er fysisk ventet. Kjøringen motsier derfor ikke Surfsenteret, og den kan ikke avgjøre hva som skjer på en vanlig vestlig svelldag.
- Uten BarentsWatch (dag 3–9) styrer vinduene alt: Unstad er større i 26 timer (svell fra vest-sørvest, utenfor Skagsandens vindu) og mindre i 23 (svell fra nord).
- **Anbefaling: ingen endring av tall nå.** Grunnlaget er én kjøring uten observasjon, og det er ikke vist at rekkefølgen er feil i dette været. Flytting av Unstads punkt (A) snur rekkefølgen, men kan ikke prøves mot de faste observasjonene, og gir nesten tre ganger så høy surf i de 93 arkivtimene med skyggetall (fire kjøringer siden 15.10, median 3,1 m mot 1,1 m). Se forslaget nederst.

## Grunnlaget (tynt)

- **Unstad mot Skagsanden:** én kjøring, 2026-11-10T06:00:00+00:00, 203 timer (55 med BarentsWatch for begge, 148 lenger fram med bare svellet ute). Skagsanden kom i arkivet først 10.11.2026 (lagt til 16.10, kontoen var stengt 16.10–05.11). Det finnes ingen eldre timer å sammenligne.
- **Ramberg** er slått av (holdt tilbake til denne oppgaven) og har aldri vært hentet i produksjon. Det finnes ingen BarentsWatch-tall for Rambergs punkt lokalt. Ramberg er derfor bare regnet for timene uten BarentsWatch, med Rambergs oppsett på Skagsandens havdata (havpunktene ligger 2,7 km fra hverandre). Det er en rekonstruksjon, ikke et varsel.
- **Backtesten** (de faste observasjonene 26.09–05.10) har bare Unstad. Flakstad-spotene fantes ikke da, og det finnes ingen observasjon fra Flakstad.
- **Hvilken strand mener Surfsenteret?** Skagsanden er stranda ved Flakstad kirke (Lofoten Beach Camp). Ramberg ligger 2,4 km lenger sørvest. Begge har `area: Flakstad`. Rapporten viser begge.

## 1. Unstad mot Skagsanden, time for time

Surfehøyde:

| Utvalg | Timer | Unstad større | Lik (±0,1 m) | Unstad mindre | Median Unstad (m) | Median Flakstad-spot (m) | Typisk forhold Unstad/Flakstad-spot (timer der begge har ≥ 0,3 m) |
|---|---|---|---|---|---|---|---|
| Alle timer | 203 | 26 (13 %) | 126 (62 %) | 51 (25 %) | 0,00 | 0,00 | 0,97 (15 t) |
| Med BarentsWatch (første 2 døgn) | 55 | 0 (0 %) | 27 (49 %) | 28 (51 %) | 0,00 | 0,80 | 0,96 (11 t) |
| Uten BarentsWatch (dag 3–9) | 148 | 26 (18 %) | 99 (67 %) | 23 (16 %) | 0,00 | 0,00 | 1,30 (4 t) |
| Bare lyse timer | 65 | 11 (17 %) | 30 (46 %) | 24 (37 %) | 0,00 | 0,00 | 0,65 (7 t) |
| Timer der minst én av dem har 0,3 m eller mer | 81 | 26 (32 %) | 6 (7 %) | 49 (60 %) | 0,00 | 0,85 | 0,97 (15 t) |
| ... av dem med BarentsWatch | 34 | 0 (0 %) | 6 (18 %) | 28 (82 %) | 0,00 | 1,17 | 0,96 (11 t) |
| ... av dem uten BarentsWatch | 47 | 26 (55 %) | 0 (0 %) | 21 (45 %) | 1,06 | 0,33 | 1,30 (4 t) |
| Svellet ute i Unstads vindu [253, 335], ikke i Skagsandens [280, 4] | 12 | 4 (33 %) | 5 (42 %) | 3 (25 %) | 0,00 | 0,00 | 5,69 (1 t) |
| Svellet ute i begge vinduene | 24 | 4 (17 %) | 10 (42 %) | 10 (42 %) | 0,00 | 0,78 | 1,07 (6 t) |
| Svellet ute i Skagsandens vindu, ikke i Unstads | 24 | 0 (0 %) | 7 (29 %) | 17 (71 %) | 0,00 | 1,21 | 0,97 (8 t) |

Stjerner:

| Utvalg | Timer | Unstad flere | Like mange | Unstad færre |
|---|---|---|---|---|
| Alle timer | 203 | 26 | 146 | 31 |
| Med BarentsWatch | 55 | 3 | 38 | 14 |
| Uten BarentsWatch | 148 | 23 | 108 | 17 |
| Bare lyse timer | 65 | 11 | 42 | 12 |

## 2. Unstad mot Ramberg (rekonstruksjon, bare timene uten BarentsWatch)

Kontroll av metoden: Skagsanden regnet på nytt lokalt avviker fra det publiserte varselet med høyst 0,00 m over 148 timer.

| Utvalg | Timer | Unstad større | Lik (±0,1 m) | Unstad mindre | Median Unstad (m) | Median Flakstad-spot (m) | Typisk forhold Unstad/Flakstad-spot (timer der begge har ≥ 0,3 m) |
|---|---|---|---|---|---|---|---|
| Ramberg som i spots.json (facing 287.7, vindu [297, 348]) | 148 | 26 (18 %) | 121 (82 %) | 1 (1 %) | 0,00 | 0,00 | 1,20 (2 t) |
| Ramberg med facing 315 (grenen region/ramberg-315) | 148 | 26 (18 %) | 121 (82 %) | 1 (1 %) | 0,00 | 0,00 | 1,20 (2 t) |

Uten BarentsWatch styres høyden av vinduet og facing spiller liten rolle. Derfor er de to radene like eller nesten like. Forskjellen mellom 287,7 og 315 viser seg først i timene med BarentsWatch, og de kan bare regnes i en prøvehenting.

## 3. Årsaken: BarentsWatch-punktene (timene med BarentsWatch)

| | Unstad, punkt i bruk (250 m ut, 3,9 m dyp) | Unstad, skyggepunkt (700 m ut, 8,5 m dyp) | Skagsanden (500 m ut, 9,3 m dyp) |
|---|---|---|---|
| BarentsWatch Hs, median (m) | 0,80 | 1,32 | 1,48 |
| BarentsWatch-periode, median (s) | 5,2 | ikke lagret | 6,5 |
| Hs ved spoten etter justering, median (m) | 0,31 | – | 0,51 |
| Surf-faktor | 1,45 (startverdi fra 2 observasjoner) | – | 1,00 |
| Surfehøyde, median (m) | 0,00 | – | 0,80 |

- Unstads punkt i bruk viser median 0,48 av det skyggepunktet viser (55 timer): 0,51 når skyggepunktet har 1 m eller mer (31 t), 0,11 når det har under 1 m (24 t).
- Mot Skagsandens punkt: Unstads punkt i bruk viser median 0,48 av Skagsandens Hs, skyggepunktet 0,89.
- Svellretningen ute i disse timene: 24 av 55 timer i Unstads vindu, 40 av 55 i Skagsandens. Median periode ute 7,3 s.

## 4. Unstad: punktet i bruk mot skyggepunktet, alle kjøringer i arkivet siden 15.10

82 kjøringer i git-historikken, men bare fire av dem har skyggetall for Unstad. 93 timer med begge tallene (hver time fra siste kjøring før timen, høyst 24 timer gammel). Kjøringer: 16.10, 05.11, 09.11, 10.11.

| Utvalg (surfehøyde fra skyggepunktet uten startverdi) | Timer | Median i bruk (m) | Median skygge med faktor 1,45 (m) | Median skygge uten (m) | Stjerner: skygge flere / like / færre |
|---|---|---|---|---|---|
| Alle | 93 | 1,13 | 3,10 | 2,14 | 25 / 40 / 28 |
| Under 1,0 m | 4 | 0,00 | 1,27 | 0,88 | 2 / 2 / 0 |
| 1,0 m eller mer | 89 | 1,14 | 3,19 | 2,20 | 23 / 38 / 28 |

## 5. Før og etter (timene med BarentsWatch i kjøringen over)

| Utvalg | Timer | Unstad større | Lik (±0,1 m) | Unstad mindre | Median Unstad (m) | Median Flakstad-spot (m) | Typisk forhold Unstad/Flakstad-spot (timer der begge har ≥ 0,3 m) |
|---|---|---|---|---|---|---|---|
| I dag | 55 | 0 (0 %) | 27 (49 %) | 28 (51 %) | 0,00 | 0,80 | 0,96 (11 t) |
| A: Unstads punkt flyttes til 700 m, startverdien 1,45 beholdes | 55 | 33 (60 %) | 21 (38 %) | 1 (2 %) | 1,07 | 0,80 | 1,46 (33 t) |
| B: som A, men uten startverdien | 55 | 0 (0 %) | 50 (91 %) | 5 (9 %) | 0,74 | 0,80 | 1,01 (33 t) |
| C: Skagsanden ganges med 0,8 (regneeksempel), Unstad som i dag | 55 | 6 (11 %) | 21 (38 %) | 28 (51 %) | 0,00 | 0,64 | 1,21 (11 t) |

Unstads stjerner med A mot i dag, 55 timer: 19 opp, 36 uendret, 0 ned. Timer som flytter seg 2 eller mer: 5.

| Time (UTC) | Svell ute (m, retning, periode) | Unstad Hs i bruk / skygge | Unstad surf i dag (★) | A (★) | B | Skagsanden Hs | Skagsanden surf (★) |
|---|---|---|---|---|---|---|---|
| 11-10 06:00 | 1,5, 271°, 9,0 s | 1,12 / 2,52 | 0,00 (0) | 2,87 (1) | 1,98 | 2,33 | 1,89 (0) |
| 11-10 09:00 | 1,7, 321°, 8,5 s | 1,14 / 2,46 | 0,00 (0) | 2,75 (1) | 1,90 | 2,44 | 1,92 (0) |
| 11-10 12:00 | 1,7, 340°, 8,2 s | 1,24 / 2,37 | 0,94 (0) | 2,18 (1) | 1,50 | 2,27 | 1,45 (0) |
| 11-10 15:00 | 1,7, 337°, 8,2 s | 1,15 / 2,17 | 0,00 (0) | 2,03 (1) | 1,40 | 2,09 | 1,36 (1) |
| 11-10 18:00 | 1,7, 337°, 8,2 s | 0,97 / 2,07 | 0,00 (0) | 1,95 (2) | 1,35 | 2,07 | 1,35 (2) |
| 11-10 21:00 | 1,5, 342°, 8,1 s | 0,94 / 1,85 | 1,14 (1) | 1,73 (1) | 1,19 | 1,74 | 1,18 (0) |
| 11-11 00:00 | 1,4, 340°, 8,1 s | 0,90 / 1,75 | 1,10 (0) | 1,65 (0) | 1,14 | 1,67 | 1,14 (0) |
| 11-11 03:00 | 1,3, 335°, 7,8 s | 0,89 / 1,72 | 0,00 (0) | 1,29 (1) | 0,89 | 1,69 | 0,88 (1) |
| 11-11 06:00 | 1,2, 331°, 7,6 s | 0,80 / 1,54 | 0,00 (0) | 1,17 (1) | 0,81 | 1,52 | 0,80 (1) |
| 11-11 09:00 | 1,1, 335°, 7,3 s | 0,84 / 1,32 | 0,00 (0) | 1,02 (0) | 0,70 | 1,48 | 0,77 (0) |
| 11-11 12:00 | 0,9, 336°, 7,1 s | 0,66 / 0,89 | 0,00 (0) | 0,94 (0) | 0,65 | 1,10 | 0,79 (0) |
| 11-11 15:00 | 0,8, 333°, 6,8 s | 0,14 / 0,51 | 0,00 (0) | 0,00 (0) | 0,00 | 0,62 | 0,00 (0) |
| 11-11 18:00 | 0,7, 328°, 6,7 s | 0,03 / 0,36 | 0,00 (0) | 0,00 (0) | 0,00 | 0,56 | 0,00 (0) |
| 11-11 21:00 | 0,6, 329°, 6,4 s | 0,07 / 0,45 | 0,00 (0) | 0,00 (0) | 0,00 | 0,55 | 0,00 (0) |
| 11-12 00:00 | 0,9, 26°, 6,8 s | 0,03 / 0,33 | 0,00 (0) | 0,00 (0) | 0,00 | 0,40 | 0,00 (0) |
| 11-12 03:00 | 1,1, 17°, 6,7 s | 0,02 / 0,32 | 0,00 (0) | 0,00 (0) | 0,00 | 0,47 | 0,00 (0) |
| 11-12 06:00 | 1,0, 15°, 6,7 s | 0,03 / 0,33 | 0,00 (0) | 0,00 (0) | 0,00 | 0,48 | 0,00 (0) |
| 11-12 09:00 | 0,9, 15°, 7,2 s | 0,03 / 0,35 | 0,00 (0) | 0,00 (0) | 0,00 | 0,51 | 0,00 (0) |
| 11-12 12:00 | 0,9, 16°, 7,2 s | 0,53 / 1,14 | 0,00 (0) | 1,39 (1) | 0,96 | 1,46 | 1,17 (1) |

## Forslag (krever Theodors ja, ingenting er gjort)

1. **Ikke skaler ned Flakstad (C).** Det er ikke vist noen feil der. Skagsandens punkt følger regelen fra 15.10 (500 m ut, 9,3 m dyp), og det finnes ingen observasjon som sier at tallene er for høye. En fast faktor ville også trekke ned Skagsanden på de dagene nordlig svell faktisk treffer best der.
2. **Unstads BarentsWatch-punkt bør flyttes ut til 700 m (A), men ikke før det er prøvd på en vestlig svelldag.** Det er samme sak som ROADMAP N. Grunnen til å vente: startverdien 1,45 er lært på det gamle punktet (26.09 og 27.09). De faste observasjonene kan ikke regnes på nytt med det nye punktet, fordi BarentsWatch-tall for 700 m-punktet ikke finnes for de dagene. I arkivtimene med skyggetall (fire kjøringer siden 15.10) gir A median 3,1 m der varselet i dag gir 1,1 m. Uten en observasjon vet vi ikke hvilket av tallene som er riktig.
3. **Neste svelldag er trolig 15.–16.11:** varselet har 2,5 m svell fra 250° med 12 s periode. Fra 13.–14.11 dekker BarentsWatch de timene. Da kan denne rapporten kjøres på nytt (ingen ekstra kall), og én størrelse fra Unstad og én fra Flakstad samme dag avgjør om det blir A (behold 1,45), B (fjern 1,45) eller noe midt imellom.
4. **Ramberg** kan ikke vurderes lokalt i timene med BarentsWatch (ingen tall for punktet). Facing 315 (grenen region/ramberg-315) må ses i en prøvehenting samme svelldag.
5. Spør Lofoten Surfsenter: mener de Skagsanden eller Ramberg med «Flakstad»? Gjelder «nesten alltid større» også når svellet kommer fra nord?

