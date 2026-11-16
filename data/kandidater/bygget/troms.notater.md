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
