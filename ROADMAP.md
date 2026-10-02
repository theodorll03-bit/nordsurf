# Nordsurf: oppgavekø

Jobb ovenfra og ned. Hopp over oppgaver merket "Venter på Theodor", og ta neste.

## 1. Unstad for lav høyde - FERDIG, Theodor sa ja
Tre observasjoner (26.09 kl. 14:45, 27.09 morgen/Instagram) viste at Unstad rates for lavt. Retningsfaktor-fiksen (ja, også for Steinkrøssa - 51 grader skrått er normalt der svellet bøyer seg rundt en odde). Theodor avviste forslaget om å senke `ideal_height` (skjuler årsaken) - i stedet: nytt `surf_factor_prior`-felt i spots.json (startverdi 1,45 for Unstad, fra de to observasjonene, til det finnes nok logger), og `ideal_height` senket til [1,2, 3,5] (en ren, brysthøy dag er god surf på Unstad). Fysikk-kontrollør fant en reell feil under review (overstyringen slo inn på `exposure()` sin "ukjent retning"-nøytralverdi 0,7 når `dir_offshore` manglet, ikke bare på bekreftet god eksponering) - rettet, ny regresjonstest 9.3c. Se STATUS.md.

## 2. Vinden forsvinner fra onsdag kl. 12 - FERDIG
met.no Locationforecast gir timesdata bare de første ca. 60 timene, deretter hver 6. time. Rettet med interpolering (`sources.weather_interpolate()`). Se STATUS.md.

## 3. Vindpila på spot-skiva ser rotete ut - PARKERT (gren wind-arrow-wip)
Den gikk tvers gjennom hele skiva, stakk ut på én side, og pilhodet havnet under ratingringen. Delvis rettet (vindpil utenfor ringen, klippesti for animasjonen, firehjørners plassering for etiketten), men ikke ferdig re-verifisert. Unstad (oppgave 1) går foran - tas opp igjen når den er avklart.
a. Flytt vinden ut på kanten: en liten pil (vindvimpel) UTENFOR ratingringen, plassert på siden vinden kommer FRA, pekende inn mot sentrum i vindens retning. Vindstyrke og type (f.eks. "7 m/s offshore") som liten tekst ved pila.
b. Vindanimasjonen (strømmende streker) skal holdes innenfor skiva med en klippesti (clipPath), og aldri tegnes over ratingringen eller etikettene. Diskret, lav opasitet, så den ikke konkurrerer med svellet.
c. Rekkefølge fra bunn til topp: kart, eksponeringskile, vindanimasjon, svelllinjer, ratingring, vindpil og etiketter.
d. Når vinden mangler: ingen pil, og "vind mangler" i liten tekst.
e. prefers-reduced-motion: ingen vindanimasjon, bare pila.
f. Ta skjermbilder i mobilvisning, lys og mørk modus, med vind fra fire ulike retninger (N, Ø, S, V), og sjekk at ingenting stikker ut eller havner under ringen.

## 4. Grøtfjord: skill "blåst ut" fra ekte flatt - FERDIG
Se STATUS.md.

## 5. Test source/fileSource-hypotesen med data
a/b: FERDIG - se STATUS.md. c (vente på konsekvent avvik i en ekte Actions-kjøring og stoppe for ja hvis funnet): venter fortsatt på nok ekte data.

## 6. Rett exposure_baseline.py (del C) - FERDIG
Se STATUS.md.

## 7. Koble del C inn i ratingen - FERDIG
Se STATUS.md.

## 8. Kysttoleranse i check_spot.py (oppfølging av Steinkrøssa-funnet i oppgave 7) - FERDIG, RAPPORT
Ingen swell_window endret. Se STATUS.md.

## 9. Del B: eksponering lært fra BarentsWatch - FERDIG
Se STATUS.md.

## 10. Unstad: hvor ligger BarentsWatch sitt rutepunkt?
Trigg diagnose-workflowen (gh workflow run) hvis mulig, les ut punktet BarentsWatch valgte for Unstad, og regn avstand og retning fra punktet vi ba om. Bare rapporter, ikke flytt. Sannsynligvis unødvendig nå - oppgave 1 sin `surf_factor_prior`/`ideal_height`-justering løste Unstad (se STATUS.md).

## Venter på Theodor
- Steinkrøssa: BarentsWatch-retningen ved punktet avviker ofte 30-60 grader fra facing (rimelig for en spot der svellet bøyer seg rundt en odde, ikke en feilmåling) - trenger observasjon for å bekrefte ratingen stemmer når retningsfaktoren overstyres der.
- Unstad: vinden appen beregner (met.no) stemmer ikke med videoene to ganger nå (26.09: video viste offshore, appen sa sidevind; 27.09: video viste nesten vindstille, appen beregnet 5-8 m/s side-onshore). Én gang til, så ser vi på vindmodellen ved Unstad spesielt.
- Farstadsanden: vindu og pinne fra lokal surfer.
- Tromvik: offshorevinden (105-195) er utledet fra facing, ikke bekreftet lokalt eller fra satellittbilde ennå.
- Grøtfjord: om exposure_override kan fjernes, når del B har lært noe.
- Ersfjordstranda: fri sektor (300 m kysttoleranse) er [288, 320], men swell_window er satt til [294, 320] - 6 grader smalere i underkant enn det som faktisk har fri linje til åpent hav. Mulig forslag: utvid vinduet til 288. Ikke gjort - krever Theodors ja (se oppgave 8 i STATUS.md).
