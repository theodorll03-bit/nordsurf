# Gjennomgangspakke: Troms (9 spots)

Laget 2026-11-10 av tools/region_pakke.py fra spots.json (gjelder der spoten ligger inne) og fabrikkens forslag (data/kandidater/bygget/<id>.json). 6 publisert, 1 bygget forslag, 2 venter på lokalkunnskap.

Vindu: fri linje 150 km over GSHHS f (300 m kysttoleranse). Facing: strandnormal ±150 m langs kysten. Offshore-vind: motsatt av facing ±45° når ikke annet står. BarentsWatch-punkt: snittregelen 15.10 (første punkt utover med minst 8 m dyp og flat Hs). Tidevann: Kartverkets referansested for posisjonen. Vern: Naturbase innen 2 km, målt fra spotens posisjon der oppslaget finnes (ellers fra listepinnen, og da står det), forskriften lest på Lovdata. Sikkerhet: A = navn, strandtype, synlig bølge/formasjon og retning stemmer; B = to av fire; C = resten (bygges ikke).

![Oversikt](troms-oversikt.png)

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

## Oversikt

| id | Navn | Region | Status | Sikkerhet | facing | Vindu | Offshore-vind | BarentsWatch-punkt |
|---|---|---|---|---|---|---|---|---|
| bovaer | Bøvær | Troms | bygget forslag | B | 289.8° | 251–326° | 65–155° | 69.469189, 17.217652 (400 m ut i retning 290°, 8.5 m dyp) |
| ersfjordstranda | Ersfjordstranda | Troms | publisert | ikke sjekket | 315° | 294–320° | 90–180° | 69.485517, 17.394874 (251 m ut i retning 315°, dybde ukjent) |
| grotfjord | Grøtfjord | Troms | publisert | ikke sjekket | 295° | 286–310° | 76–166° | 69.779773, 18.529373 (250 m ut i retning 295°, dybde ukjent) |
| hamn-senja | Hamn (Senja) | Troms | venter på lokalkunnskap | C (forslag, ikke godkjent) | – | – | – | – |
| laukvika-senja | Laukvika (Senja) | Troms | venter på lokalkunnskap | C (forslag, ikke godkjent) | – | – | – | – |
| lenangsoyra | Lenangsøyra | Troms | publisert | ikke sjekket | 19° | 15–23° | 155–245° | 69.849744, 19.989858 (251 m ut i retning 360°, dybde ukjent) |
| russelv | Russelv | Troms | publisert | ikke sjekket | 315° | 5–15° + 349–356° | 90–180° | 69.949979, 20.215157 (251 m ut i retning 315°, dybde ukjent) |
| steinkrossa | Steinkrøssa | Troms | publisert | ikke sjekket | 45° | 315–16° | 175–265° | 69.493305, 17.263036 (251 m ut i retning 45°, dybde ukjent) |
| tromvik | Tromvik | Troms | publisert | ikke sjekket | 330° | 314–349° | 105–195° | 69.779615, 18.431276 (251 m ut i retning 330°, dybde ukjent) |

## Holdes tilbake, parkert eller ikke bygget

| id | Status | Hvorfor |
|---|---|---|
| hamn-senja | venter på lokalkunnskap | Listepinnen sto på anlegget Hamn i Senja, i havna mellom holmene. Regnet med skjær (OSM) er det bare smale åpninger mot vest (274-279° og 290-299°, ingen sektor over 10°), og kystnormalen ved den lille stranda peker mot sør, inn i havna. Dokumentasjonen er svak (to kilder) og stedet trolig feil; uten lokalkunnskap om et annet sted bør kandidaten avvises. |
| laukvika-senja | venter på lokalkunnskap | Ei sandlomme på ca. 40 m bare 635 m nord for Bøstranda, mot samme åpne hav (GSHHS 250-304° mot 251-326° for bovaer), så den vil få nesten de samme tallene som bovaer. Kildene er bade- og turistsider uten bruddtype. Trenger noen som vet om det finnes en egen bølge her; hvis ikke, bør den avvises som duplikat av bovaer. |

## Kallbudsjett

| | Spots | Open-Meteo vektet per kjøring | per døgn (grense 10 000) | verste time (5 000) | verste minutt (600) | BarentsWatch per kjøring / døgn | met.no per kjøring | Kartverket per kjøring |
|---|---|---|---|---|---|---|---|---|
| i dag (publiserte) | 22 | 78 | 622 (6%) | 78 (2%) | 78 (13%) | 39 / 312 | 66 | 22 |
| med alle 1 ventende i regionen slått på | 23 | 81 | 649 (6%) | 81 (2%) | 81 (14%) | 40 / 320 | 69 | 23 |

Open-Meteo: vekt 1,14 per punkt (16 dager), to bølgemodeller per havpunkt og ett vindpunkt per spot, 8 kjøringer per døgn; verste minutt regner alle kall i en kjøring i samme minutt. Testen fetcher/test_kallregnskap.py holder hver grense under 50 %.

## Spotene

### Bøvær (`bovaer`) - bygget forslag

| | |
|---|---|
| Posisjon | 69.467964, 17.227291 - godkjent forslag (flyfoto), spotansvarlig (agent, Theodor 10.11.2026), 2026-11-10. 120 m fra listepinnen. Bøstranda, ca. 500 m sandstrand som vender VNV med sandbunn. Listepinnen sto på land; satt ca. 100 m utenfor vannkanten midt på stranda. Små skjær ligger ca. 110 m lenger ut. Hovedtoppen er ukjent. |
| Facing | 289.8° |
| Svellvindu | 251–326° |
| Offshore-vind | 65–155° |
| Havpunkt | 69.5024, 16.9358 (12 km ut i retning 289°) |
| BarentsWatch-punkt | 69.469189, 17.217652 (400 m ut i retning 290°, 8.5 m dyp)<br>Flyttet til 400 m ut i snittet langs 289.8° (dybde 8.5 m) - spotansvarlig 10.11.2026: stranda ligger i le av skjæret 800-900 m ut, og regelen fra 15.10 valgte 1500 m utenfor skjæret; lavere sikkerhet. Snitt langs facing (data/bw_point_search/result_2026-11-10T1135_kandidater.json), første punkt med dybde ≥ 8 m og BarentsWatch-data (retting fra gjennomgangen): snitt 400m@289.8, 400 m ut, dybde 8,5 m. |
| Eksponering | vindu 75° bredt, facing 1° fra midten; ingen geometrisk grunnlinje ennå - henteren bruker vindu og skyggekurve som reserve |
| Tidevannssted | Andenes, faktor 1.01 |
| Høyder | ideal [0.8, 2.0], maks 3.5 |
| Vern/forbud | ingen verneområder innen 2 km av spoten |
| Sikkerhet | B |
| Usikkert | offshore-vind: standard, ubekreftet (motsatt av facing ±45°)<br>barentswatch_point rettet: 400 m ut (spotansvarlig 10.11.2026: stranda ligger i le av skjæret 800-900 m ut, og regelen fra 15.10 valgte 1500 m utenfor skjæret; lavere sikkerhet) |

![bovaer](bovaer.png)

### Ersfjordstranda (`ersfjordstranda`) - publisert

| | |
|---|---|
| Posisjon | 69.483919, 17.399405 - spots.json (satt før kandidatlista) |
| Facing | 315° |
| Svellvindu | 294–320° |
| Offshore-vind | 90–180° |
| Havpunkt | 69.5764, 17.0514 (17 km ut i retning 307°) |
| BarentsWatch-punkt | 69.485517, 17.394874 (251 m ut i retning 315°, dybde ukjent) |
| Eksponering | vindu 26° bredt, facing 8° fra midten; geometrisk grunnlinje finnes (data/exposure_baseline.json) |
| Tidevannssted | slås opp av henteren (Kartverket) |
| Høyder | ideal [0.8, 2.0], maks 3.5 |
| Vern/forbud | ingen verneområder innen 2 km av listepinnen |
| Sikkerhet | ikke sjekket |
| Usikkert | – |

![ersfjordstranda](ersfjordstranda.png)

### Grøtfjord (`grotfjord`) - publisert

| | |
|---|---|
| Posisjon | 69.778818, 18.535261 - spots.json (satt før kandidatlista) |
| Facing | 295° |
| Svellvindu | 286–310° |
| Offshore-vind | 76–166° |
| Havpunkt | 69.866, 18.1098 (19 km ut i retning 301°) |
| BarentsWatch-punkt | 69.779773, 18.529373 (250 m ut i retning 295°, dybde ukjent) |
| Eksponering | exposure_override [{'from': 311, 'to': 330, 'max': 0.2}, {'from': 276, 'to': 285, 'max': 0.2}]; vindu 24° bredt, facing 3° fra midten; geometrisk grunnlinje finnes (data/exposure_baseline.json) |
| Tidevannssted | slås opp av henteren (Kartverket) |
| Høyder | ideal [0.8, 2.0], maks 3.5 |
| Vern/forbud | ingen verneområder innen 2 km av listepinnen |
| Sikkerhet | ikke sjekket |
| Usikkert | – |

![grotfjord](grotfjord.png)

### Hamn (Senja) (`hamn-senja`) - venter på lokalkunnskap

| | |
|---|---|
| Posisjon | 69.4172, 17.1641 - listepinnen (ikke kontrollert) |
| Forslag | 69.416517, 17.163551 (claude-flyfoto-2026-11-10, sikkerhet C, ikke godkjent; flyttet 79 m fra listepinnen). Listepinnen står på anlegget Hamn i Senja, i havna mellom holmene. Området ligger i le bak skjær og grunne sandflater (Bergsøyan) mot nord og nordøst og er bare åpent mot vest. Fant ingen tydelig surfestrand. Posisjonen er beste gjetning, i vannet utenfor den lille stranda ved anlegget. Trolig feil sted; trenger lokalkunnskap. |
| Sikkerhet | C (forslag, ikke godkjent) |
| Vern/forbud | Bergsøyan landskapsvernområde med dyrelivsfredning, 630 m fra forslaget (listepinnen: 554 m): ferdselsforbud (land, § 3 nr. 3) |
| Usikkert | Listepinnen sto på anlegget Hamn i Senja, i havna mellom holmene. Regnet med skjær (OSM) er det bare smale åpninger mot vest (274-279° og 290-299°, ingen sektor over 10°), og kystnormalen ved den lille stranda peker mot sør, inn i havna. Dokumentasjonen er svak (to kilder) og stedet trolig feil; uten lokalkunnskap om et annet sted bør kandidaten avvises. |

### Laukvika (Senja) (`laukvika-senja`) - venter på lokalkunnskap

| | |
|---|---|
| Posisjon | 69.4745, 17.2249 - listepinnen (ikke kontrollert) |
| Forslag | 69.473596, 17.224552 (claude-flyfoto-2026-11-10, sikkerhet C, ikke godkjent; flyttet 101 m fra listepinnen). Listepinnen sto ved bergnabben ved siden av ei lita sandlomme (ca. 40 m bred) nord i bukta. Satt ca. 75 m ut sørvest for lomma, over sandbunn. Kildene er bade- og turistsider, bruddtypen er ukjent, og bukta ligger bare ca. 600 m nord for Bøstranda (bovaer). Usikkert om dette er en egen surfespot. |
| Sikkerhet | C (forslag, ikke godkjent) |
| Vern/forbud | ingen verneområder innen 2 km av forslaget |
| Usikkert | Ei sandlomme på ca. 40 m bare 635 m nord for Bøstranda, mot samme åpne hav (GSHHS 250-304° mot 251-326° for bovaer), så den vil få nesten de samme tallene som bovaer. Kildene er bade- og turistsider uten bruddtype. Trenger noen som vet om det finnes en egen bølge her; hvis ikke, bør den avvises som duplikat av bovaer. |

### Lenangsøyra (`lenangsoyra`) - publisert

| | |
|---|---|
| Posisjon | 69.847483, 19.989858 - spots.json (satt før kandidatlista) |
| Facing | 19° |
| Svellvindu | 15–23° |
| Offshore-vind | 155–245° |
| Havpunkt | 70.3349, 20.4737 (57 km ut i retning 18°) |
| BarentsWatch-punkt | 69.849744, 19.989858 (251 m ut i retning 360°, dybde ukjent) |
| Eksponering | exposure_override [{'from': 225, 'to': 320, 'max': 0.05}]; vindu 8° bredt, facing 0° fra midten; geometrisk grunnlinje finnes (data/exposure_baseline.json) |
| Tidevannssted | slås opp av henteren (Kartverket) |
| Høyder | ideal [0.8, 2.0], maks 3.5 |
| Vern/forbud | ingen verneområder innen 2 km av listepinnen |
| Sikkerhet | ikke sjekket |
| Usikkert | – |

![lenangsoyra](lenangsoyra.png)

### Russelv (`russelv`) - publisert

| | |
|---|---|
| Posisjon | 69.94838, 20.219789 - spots.json (satt før kandidatlista) |
| Facing | 315° |
| Svellvindu | 5–15° + 349–356° |
| Offshore-vind | 90–180° |
| Havpunkt | 70.3581, 20.4291 (46 km ut i retning 10°) |
| BarentsWatch-punkt | 69.949979, 20.215157 (251 m ut i retning 315°, dybde ukjent) |
| Eksponering | vindu 17° bredt, facing 55° fra midten; geometrisk grunnlinje finnes (data/exposure_baseline.json) |
| Tidevannssted | slås opp av henteren (Kartverket) |
| Høyder | ideal [0.8, 2.0], maks 3.5 |
| Vern/forbud | Lyngsalpan landskapsvernområde/Ittugáissáid Suodjemeahcci, 1366 m fra listepinnen: forskriften ikke lest |
| Sikkerhet | ikke sjekket |
| Usikkert | facing 315° ligger 34° utenfor eget svellvindu (5–15° + 349–356°) |

![russelv](russelv.png)

### Steinkrøssa (`steinkrossa`) - publisert

| | |
|---|---|
| Posisjon | 69.491707, 17.258504 - spots.json (satt før kandidatlista) |
| Facing | 45° |
| Svellvindu | 315–16° |
| Offshore-vind | 175–265° |
| Havpunkt | 69.6125, 17.1506 (14 km ut i retning 343°) |
| BarentsWatch-punkt | 69.493305, 17.263036 (251 m ut i retning 45°, dybde ukjent) |
| Eksponering | vindu 61° bredt, facing 60° fra midten; geometrisk grunnlinje finnes (data/exposure_baseline.json) |
| Tidevannssted | slås opp av henteren (Kartverket) |
| Høyder | ideal [0.8, 2.0], maks 3.5 |
| Vern/forbud | ingen verneområder innen 2 km av listepinnen |
| Sikkerhet | ikke sjekket |
| Usikkert | facing 45° ligger 29° utenfor eget svellvindu (315–16°) |

![steinkrossa](steinkrossa.png)

### Tromvik (`tromvik`) - publisert

| | |
|---|---|
| Posisjon | 69.777657, 18.434525 - spots.json (satt før kandidatlista) |
| Facing | 330° |
| Svellvindu | 314–349° |
| Offshore-vind | 105–195° |
| Havpunkt | 69.9048, 18.2361 (16 km ut i retning 332°) |
| BarentsWatch-punkt | 69.779615, 18.431276 (251 m ut i retning 330°, dybde ukjent) |
| Eksponering | vindu 35° bredt, facing 2° fra midten; geometrisk grunnlinje finnes (data/exposure_baseline.json) |
| Tidevannssted | slås opp av henteren (Kartverket) |
| Høyder | ideal [0.8, 2.0], maks 3.5 |
| Vern/forbud | ingen verneområder innen 2 km av listepinnen |
| Sikkerhet | ikke sjekket |
| Usikkert | – |

![tromvik](tromvik.png)

Kyst © OpenStreetMap-bidragsytere og GSHHS; dybde EMODnet Bathymetry; tidevann © Kartverket; bølger BarentsWatch; vern Naturbase (Miljødirektoratet).
