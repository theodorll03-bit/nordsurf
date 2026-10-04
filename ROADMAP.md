# Nordsurf: oppgavekø

Jobb ovenfra og ned. Hopp over oppgaver merket "Venter på Theodor", og ta neste.

## 1. Unstad for lav høyde - FERDIG, Theodor sa ja
Fire observasjoner (26.09 kl. 14:45, 27.09 morgen, 28.09 kl. 13/"Safe to say it's firing") viste at Unstad rates for lavt, av to ulike årsaker. Først: retningsfaktor-fiksen (ja, også for Steinkrøssa - 51 grader skrått er normalt der svellet bøyer seg rundt en odde) og `surf_factor_prior`/`ideal_height`-justering i stedet for å senke `ideal_height` (ville skjult årsaken). Deretter (28.09): `sources_disagree` kappet stjernene når svellet ute var rett under 0,667 i eksponering, selv når BarentsWatch ved SPOTEN selv bekreftet treff - ny `bw_confirms` (retning innenfor 30 grader av facing OG høyde minst 0,35 m uten retningsfaktor) overstyrer nå det også. Fysikk-kontrollør fant en reell feil under review (overstyringen slo inn på `exposure()` sin "ukjent retning"-nøytralverdi 0,7 når `dir_offshore` manglet) - rettet, ny regresjonstest 9.3c. Stjernetabell viste 9 timer opp på Unstad (seks med 3 stjerner) i dagens live varsel - samme mønster som observasjonen, Theodors ja. Samtidig lagt til unntak i CLAUDE.md sin 2-stjerners stoppregel (retning som matcher faste observasjoner) og automatisk cache-versjonering for docs/sw.js (var ikke bumpet siden 26.09, ni commits). Se STATUS.md.

## 2. Vinden forsvinner fra onsdag kl. 12 - FERDIG
met.no Locationforecast gir timesdata bare de første ca. 60 timene, deretter hver 6. time. Rettet med interpolering (`sources.weather_interpolate()`). Se STATUS.md.

## 3. Vindpila på spot-skiva ser rotete ut - FERDIG
Den gikk tvers gjennom hele skiva, stakk ut på én side, og pilhodet havnet under ratingringen. Rettet: vindpil (vindvimpel) utenfor ratingringen, vindanimasjon klippet til skiva og lagt lavt i z-rekkefølgen, etikett (vindstyrke+type) låst til fire trygge hjørnesoner (ringens radius er for nær skivas egen kant til at en etikett kan følge vindretningen kontinuerlig uten enten å overlappe ringen eller stikke langt utenfor - målt empirisk). Tre runder fysikk-kontrollør: struktur/geometri, pilrotasjon som lekket inn i etiketten + "vind mangler" kunne kollidere med svellets retningsetikett, og et gjenstående smalt kollisjonsvindu i den fiksen. Alle rettet og empirisk re-verifisert. Merget til main. Se STATUS.md.

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
