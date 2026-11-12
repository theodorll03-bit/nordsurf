## Posisjonsrunden og gjennomgangen 10.11.2026

Hele svaret fra spotansvarlig ligger i `troms-gjennomgang.csv` (én linje per spot): **6 godkjent, 1 rett, 2 avvis.** Ingenting i spots.json eller appen er endret.

- **Godkjent (6):** de seks som alt er live (ersfjordstranda, grotfjord, lenangsoyra, russelv, steinkrossa, tromvik). Ingen endring i dem.
- **Rett (1):** bovaer. Posisjonen er godkjent (sikkerhet B) og spoten er bygget med spotfabrikken. BarentsWatch-punktet er rettet, se under.
- **Avvis (2):** laukvika-senja og hamn-senja venter på lokalkunnskap og er ikke bygget.

## bovaer: BarentsWatch-punktet

Snittet ble hentet 10.11 kl. 11:35Z (0 til 3 km langs facing, 18 tidspunkter, hver 3. time fra 10.11 kl. 06Z til 12.11 kl. 09Z, `data/bw_point_search/result_2026-11-10T1135_kandidater.json`).

| Avstand ut | EMODnet-dybde | Hs (median) | Retning |
|---|---|---|---|
| 100–700 m | 4,0–8,5 m | 0,60–0,67 m | 285–326° |
| 800–900 m | 0 m (skjær) | ingen data | – |
| 1 000–1 400 m | 4,3–6,3 m | 0,78–1,05 m | 309–328° |
| 1 500 m | 12,9 m | 0,79 m | 315° |
| 3 000 m | ikke hentet | 1,44 m | 339° |

- Punktvelgeren tok 1 500 m. Spotansvarlig rettet til **400 m ut (8,5 m)**, fordi stranda ligger i le av skjæret ved 800–900 m. Ved 1 500 m er Hs 1,3–1,5 ganger høyere enn ved 400 m (1,6–2,3 ganger ved 1 000–1 400 m), og vinduet (GSHHS) ser ikke skjæret, så ingenting i modellen ville trukket ned for det.
- **Lavere sikkerhet:** 400 m ligger i en lomme i EMODnet (5,3 m innenfor, 7,7 m utenfor) og oppfyller regelen fra 15.10 i 2 av 9 tidspunkter med svell i vinduet (1 500 m i 4). Punktet er retningsavhengig: Hs ved 400 og 600 m er like (under 10 % forskjell) bare når Hs ved punktet er minst ca. 0,5 m, det vil si i 3 av de 9 tidspunktene. Når svellet dreier mot nordvest (fra 11.11 kl. 12Z) faller Hs ved 400 m til 0,06–0,42 m, retningen går til 321–340° (31–50° fra facing), og 600 m har 1,6–3 ganger mer.
- Høydene [0,8, 2,0] og maks 3,5 er fabrikkens standard for strand, ukalibrert. Offshore-vinden er standard (motsatt av facing ±45°), ubekreftet.

## Breivikeidet 12.11.2026 (egen liten PR, Theodors ja til å bygge den)

Ny spot fra Theodor (ikke i lista 15.10): Sandbukta ved Breivikeidet, Tromsø kommune, innerst i Ullsfjorden. Theodor har bare hørt at den er bra og har ikke surfet der. Kilden er ikke navngitt, så spoten er **ubekreftet** (feltet `_ubekreftet` i spots.json) og ligger inne som `forelopig`. Spotansvarligs svar står i `troms-gjennomgang.csv` (rett: BarentsWatch-punktet).

- **Posisjon:** 69.659992, 19.664974. Det er 235 m fra Theodors pinne, midt på den NNØ-vendte delen av en ca. 1,1 km lang sand- og grusstrand, 100 m fra OSM-kystlinja. Ingen bølger er synlige i flyfotoet. Sikkerhet B.
- **Facing og vindu:** facing 17,3° (OSM 13–28°, flyfoto 14–18°). Vinduet er 20–25° (6°), det eneste med fri linje til åpent hav gjennom gapet mellom Vanna og Arnøya. 10–19° treffer Reinøya/Vanna 31–51 km ut, og 26–29° treffer Arnøya 55–64 km ut.
- **Offshorevind:** [152, 242], standard og ubekreftet.
- **Vern:** Sandbukta naturreservat dekker stranda og sjøen innerst i bukta. Forskriften har ikke ferdsels- eller surfeforbud, bare forbud mot motorferdsel på land.

### BarentsWatch-snittet

Snittet ble hentet 12.11 kl. 18:27Z (19 tidspunkter, hver 3. time fra 12.11 kl. 12Z til 14.11 kl. 18Z, `data/bw_point_search/result_2026-11-12T1827_kandidater.json`). BarentsWatch har data helt inn i bukta.

| Avstand ut | EMODnet-dybde | Hs (median, min–maks) | Retning (median) |
|---|---|---|---|
| 0 m | 2,0 m | 0,14 m (0,07–0,22) | 81° |
| 100 m | 8,8 m | 0,19 m (0,09–0,28) | 88° |
| 300 m | 30,8 m | 0,24 m (0,13–0,30) | 95° |
| 800–1 500 m | 55–79 m | 0,29–0,30 m (0,19–0,35) | 103–104° |

- Svellet ute var 0,8–1,4 m fra 11–27°, men BarentsWatch viste kort krappsjø fra øst (Tp 2–3 s) i 17 av 19 timer.
- I de to roligste timene (12.11 kl. 18Z og 13.11 kl. 00Z) var det 0,09 m fra 9° med Tp 7,5 s ved 100 m. Det er ca. 7 % av svellet ute, som da kom fra 12–18°, altså like utenfor vinduet.
- Regelen fra 15.10 fant derfor ikke noe punkt. Velgeren prøver bare timer der svellet ute kommer fra innenfor vinduet (20–25°), og det gjaldt 12 av 19 timer. I alle de 12 var retningen ved 100 m 69–88°, altså 46–66° fra svellet ute. De to svelltimene (svell ute fra 12–18°) ble ikke prøvd.
- Punktet ble satt til første punkt med minst 8 m dyp og data: **100 m ut (8,8 m)**, med lavere sikkerhet. Hs øker utover til ca. 800 m. Det er le bak Breivikneset for østlig krappsjø, ikke en brytesone (8,8 m er dypt vann for 3 s-bølger).

### Spørsmål til Theodor

1. **Havpunkt og langtidsdager:** fabrikkens havpunkt (70.3284, 20.4562) ligger 1,0 km fra Lenangsøyras, i den samme landmaskerte GFS-cellen, og spoten har ingen `offshore_longrange`. Anbefaling: bruk Lenangsøyras havpunkt og `offshore_longrange` 70.5/20.5. Det gir samme svelldata og ingen nye kall.
2. **Vinduet er 6°, ikke 15–30°:** nye spots har ingen geometrisk grunnlinje (`data/exposure_baseline.json`), så reserven bruker vindu og skyggekurve. Hvis grunnlinjen lages senere, gir den 0,38–0,48 over 10–30°, fordi øyene regnes som smale. Anbefaling: godta 20–25° som foreløpig uten `exposure_override`. Første observasjon og BarentsWatch blir fasiten.
3. **Vindsjø i fjorden:** med vind fra NNØ er det 31–65 km fetch, og det gir trolig 1–1,5 m med ca. 5 s, onshore. BarentsWatch tar med lokal vindsjø, men surfehøyden bruker GFS-perioden. Anbefaling: lag et forslag med før/etter som merker timer med kort periode hos BarentsWatch som vindsjø. Ingen endring nå.
4. **Hopp ved overgangen til reservesonen (dag 4 til ca. 8):** reserven regner transfer 0,6 × eksponering 0,67–0,85, det vil si 0,40–0,51 av svellet ute. BarentsWatch viste høyst ca. 15 % (svell i vinduet) og 7 % (svell fra 12–18°). Uten vind gir svell ute 1,0 m fra 25° (9 s) 1 stjerne, 1,4 m fra 21° (12 s) 2 stjerner og 2,0 m fra 22° (12 s) 3 stjerner. Med BarentsWatch er det 0 stjerner. Valg: (i) `exposure_override`-tak på ca. 0,2–0,25, (ii) egen transfer 0,15–0,2, eller (iii) la kalibreringen lære. Ulempen med (iii) er at parene blir krappsjø fra øst. Anbefaling: (i) som foreløpig tak til det finnes en observasjon. Grunnlaget er bare én kjøring på 19 timer.

## Hva som skal til

| Spot | Hva som mangler | Hvem |
|---|---|---|
| bovaer | Theodors ja til regionen. Da settes spoten inn i spots.json (`tools/godkjenn_spot.py`), og det kjøres én prøvehenting før merge. | Theodor |
| laukvika-senja | Ligger 635 m fra bovaer mot samme hav og ville fått nesten de samme tallene. Noen må bekrefte at det er en egen bølge, ellers avvises den som duplikat. | Lokalkunnskap |
| hamn-senja | Listepinnen står i havna mellom holmene, med bare smale åpninger mot vest. Trolig feil sted. Bergsøyan landskapsvernområde med dyrelivsfredning ligger 629 m unna (ferdselsforbudet på land 15.4–31.7 gjelder bare enkelte øyer). | Lokalkunnskap |

## Sett i de som alt er live (ingen endring i denne PR-en)

- **ersfjordstranda:** OSM-normalen er 287–295°, altså 20–28° fra facing 315°. Kjent fra før, og hører sammen med vindusspørsmålet som står i ROADMAP.
- **russelv:** vinduet er 8° + 11°, og facing 315° ligger 34° utenfor. En ny spot med dette vinduet ville blitt parkert.
- **lenangsoyra:** vinduet er 8°, men spoten har observasjon og Theodors overstyring.
- **steinkrossa:** facing 45° er strandnormalen, og vinduet (315–16°) ligger 29° utenfor.
- BarentsWatch-punktene til alle seks ligger ca. 250 m ut med ukjent dybde. Alle har skyggepunkt.

## Ikke sjekket

- Flyfotoene er ikke sett på nytt etter posisjonsrunden. Gjennomgangen bygger på minikart, OSM-kyst og snittet.
- EMODnet og BarentsWatch bruker ikke samme bunn, så 8 m-kravet er testet mot en annen bunn enn Hs-profilen. Det gjelder særlig lomma ved 400 m.
- Naboene (steinkrossa, ersfjordstranda) er sammenlignet bare mot arkivet fra 10.11 kl. 06Z.
