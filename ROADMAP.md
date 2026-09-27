# Nordsurf: oppgavekø

Jobb ovenfra og ned. Hopp over oppgaver merket "Venter på Theodor", og ta neste.

## 1. Vinden forsvinner fra onsdag kl. 12
met.no Locationforecast gir timesdata bare de første ca. 60 timene, deretter hver 6. time. Henteren matcher på eksakt time, så fem av seks timer mangler vind etter det. Det gir også feil rating, fordi ukjent vind trekker en stjerne.
a. Interpoler vind mellom tidspunktene: lineært for vindstyrke og kast, sirkulært (korteste vei rundt) for retning. Samme prinsipp som BarentsWatch-interpoleringen, men tillat opptil 6 timer mellom punktene for met.no. Aldri ekstrapoler forbi siste punkt.
b. Merk interpolerte vindtimer (wind_interpolated), og vis "vind jevnet ut" i liten tekst på detaljsiden.
c. Sjekk de andre kildene (met.no Oceanforecast, Open-Meteo, lufttemperatur, vanntemperatur) for samme problem, og rett det der også.
d. Sjekk kilderapporten: vis horisonten for hver kilde og hvor tidssteget endrer seg.
e. Tester: vind hver 6. time gir verdier alle timer imellom, retning 350 til 10 gir 0 midt mellom, og ingen verdier etter siste punkt.
f. Vis stjernetabell før og etter for timene etter 60 timer. Her forventes endringer opp, fordi straffen for ukjent vind forsvinner. Stoppregelen på 2 stjerner gjelder ikke for timer der vinden før var ukjent, men vis dem likevel.

## 2. Vindpila på spot-skiva ser rotete ut
Den går tvers gjennom hele skiva, stikker ut på én side, og pilhodet havner under ratingringen.
a. Flytt vinden ut på kanten: en liten pil (vindvimpel) UTENFOR ratingringen, plassert på siden vinden kommer FRA, pekende inn mot sentrum i vindens retning. Vindstyrke og type (f.eks. "7 m/s offshore") som liten tekst ved pila.
b. Vindanimasjonen (strømmende streker) skal holdes innenfor skiva med en klippesti (clipPath), og aldri tegnes over ratingringen eller etikettene. Diskret, lav opasitet, så den ikke konkurrerer med svellet.
c. Rekkefølge fra bunn til topp: kart, eksponeringskile, vindanimasjon, svelllinjer, ratingring, vindpil og etiketter.
d. Når vinden mangler: ingen pil, og "vind mangler" i liten tekst.
e. prefers-reduced-motion: ingen vindanimasjon, bare pila.
f. Ta skjermbilder i mobilvisning, lys og mørk modus, med vind fra fire ulike retninger (N, Ø, S, V), og sjekk at ingenting stikker ut eller havner under ringen.

## 3. Grøtfjord: skill "blåst ut" fra ekte flatt
Grøtfjord tirsdag kl. 14: appen viste "Trolig flatt"/0,0 m, men svell ute var 0,9 av 5,9 m totalt (84 % vindsjø) og vinden 14 m/s side-onshore, kast 21. Blåst ut, ikke flatt.
- Flatt: lite energi totalt (Hs ved spoten under flat-sperren og lite totalhøyde ute).
- Blåst ut / stormsjø: mye totalhøyde, lav svellandel og/eller sterk onshore eller side-onshore vind.
Vis "Blåst ut" og en kort forklaring ("Mye vindsjø og sterk vind, ikke surfbart") i stedet for "Trolig flatt", og vis BarentsWatch-høyden i stedet for 0,0 m. Stjernene skal fortsatt være 0. Legg til test.

## 4. Test source/fileSource-hypotesen med data
Detaljsiden viste bølgene ved spoten fra Ø, 145 grader fra facing, mens vinden var 14 m/s fra VSV - vindsjø ved spoten bør komme omtrent fra vindretningen. Tyder på at retningen er snudd for noen punkter eller tidspunkter. Hypotesen om at source/fileSource i BarentsWatch bruker ulik retningskonvensjon ble tidligere avvist på resonnement, aldri testet med data.
a. Permanent sjekk i henteren: for hver BarentsWatch-verdi, lagre source og fileSource i timedataene, og skriv i kilderapporten per spot hvilke kilder som ble brukt.
b. Plausibilitetssjekk: i timer med vind over 10 m/s og lav svellandel (under 30 %) bør BarentsWatch-retningen ("fra", etter omregning) ligge innenfor ca. 60 grader av vindretningen. Tell opp per spot og per source/fileSource hvor ofte det stemmer, med og uten omregningen (+180). Skriv tabellen i STATUS.md etter neste Actions-kjøring.
c. Hvis én kilde konsekvent passer uten omregning og en annen med: vis tallene og stopp. Ikke endre konvensjonen uten Theodors ja.

## 5. Rett exposure_baseline.py (del C)
- Glatting: hard kant mot fastland skal gi ca. 0,5 på kanten og ca. 0,16 ti grader utenfor. Finn ut hvorfor Unstad og Ersfjordstranda gir 1,0 helt ut til kantene.
- Hindringer: bruk bredden på tvers sett fra spoten. Skyggelengde L = W² / λ, λ = 225 m. Spot nærmere hindringen enn L gir rå eksponering 0 for retningen, lenger bak øker den gradvis mot 1.
- Toleranse ved kysten: 300 m, ikke 2 km. Linja må starte på land i et sammenhengende stykke fra spoten og nå vann innen 300 m.
Ferdig når: Grøtfjord 311 til 330 grader gir lav eksponering av geometrien alene (uten exposure_override), Grøtfjord 285 til 310 gir 1,0 rå, Steinkrøssa rett under 315 er blokkert, Lenangsøyra sine lave verdier i det smale gapet er beholdt, og tabellen mot skyggekurven for alle spots ligger i STATUS.md.

## 6. Koble del C inn i ratingen
- Reservemodellen og Hb-dempingen for reservemodellen bruker glattet eksponering (med exposure_override som tak) i stedet for vindu og skyggekurve.
- sources_disagree bruker eksponering i stedet for directness, samme grense 0,667.
- fetch.py skriver advarsel i kilderapporten når sjekksummen i exposure_baseline.json ikke stemmer med spots.json.
- BarentsWatch-timer uendret.
Ferdig når: alle faste observasjoner holder, og tabell før og etter for dagens varsel ligger i STATUS.md. Stoppregelen på 2 stjerner i CLAUDE.md gjelder.

## 7. Kysttoleranse i check_spot.py (oppfølging av Steinkrøssa-funnet i oppgave 6)
Steinkrøssa sitt stjernefall (324 grader, oppgave 6) reiste spørsmålet om check_spot.py sin gamle 2 km-kysttoleranse ga for brede svellvinduer noen steder (linja kan ha krysset tuppen av en odde nær spoten, som en strengere toleranse ville fanget opp).
1. Oppdater check_spot.py til samme kysttoleranse som exposure_baseline.py (300 m, sammenhengende land fra spoten).
2. Regn fri sektor på nytt for alle spots (Grøtfjord, Ersfjordstranda, Steinkrøssa, Russelv, Lenangsøyra, Unstad og Farstadsanden hvis den er lagt inn). Vis en tabell: dagens swell_window, ny fri sektor, og for blokkerte retninger hvor langt unna og hvor bred hindringen er.
3. For Steinkrøssa spesielt: vis hvilke retninger mellom 315 og 16 grader som faktisk krysser land, og hvor.
4. Ikke endre noen swell_window. Det krever Theodors ja. Skriv forslagene i STATUS.md og stopp.

## 8. Del B: eksponering lært fra BarentsWatch
- 10-graders bøtter, glatting mellom nabobøtter.
- Par: ren BarentsWatch-verdi, svell ute minst 0,5 m, swell_share minst 0,7, sources_disagree usann. Lagres i data/exposure.json, 120 døgn, ett par per spot og tidspunkt.
- Lært bøtte: minst 6 par over minst 2 døgn. Normalisering krever minst 3 lærte bøtter i samme periodegruppe (kort under 10 s, lang 10 s og over). Kort kan låne fra lang, ikke omvendt.
- Transfer = medianforholdet i de samme bøttene kurven normaliseres mot, når eksponering er lært.
- Blanding med geometri: vekt lært = par / (par + 10).
- exposure_override: foreslå fjerning i Logger-fanen når lært verdi ligger under taket. Aldri fjern automatisk.
- Figur per spot i Logger-fanen: eksponering per retning, antall par per bøtte, og loggene mine som merker på retningen svellet ute kom fra, farget etter stjerner.
Ferdig når: testene dekker alle reglene over, og STATUS.md viser hvor mye som er lært per spot.

## 9. Unstad: hvor ligger BarentsWatch sitt rutepunkt?
Trigg diagnose-workflowen (gh workflow run) hvis mulig, les ut punktet BarentsWatch valgte for Unstad, og regn avstand og retning fra punktet vi ba om. Bare rapporter, ikke flytt.

## Venter på Theodor
- Farstadsanden: vindu og pinne fra lokal surfer.
- Unstad: offshorevinden. Videoen 26.09 viste offshore, appen sa sidevind. Trenger flere observasjoner før noe endres.
- Tromvik: offshorevinden (105-195) er utledet fra facing, ikke bekreftet lokalt eller fra satellittbilde ennå.
- Grøtfjord: om exposure_override kan fjernes, når del B har lært noe.
- Ersfjordstranda: fri sektor (300 m kysttoleranse) er [288, 320], men swell_window er satt til [294, 320] - 6 grader smalere i underkant enn det som faktisk har fri linje til åpent hav. Mulig forslag: utvid vinduet til 288. Ikke gjort - krever Theodors ja (se oppgave 7 i STATUS.md).
