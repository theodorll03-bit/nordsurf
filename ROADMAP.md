# Nordsurf: oppgavekø

Jobb ovenfra og ned. Hopp over oppgaver merket "Venter på Theodor", og ta neste.

## 1. Rett exposure_baseline.py (del C)
- Glatting: hard kant mot fastland skal gi ca. 0,5 på kanten og ca. 0,16 ti grader utenfor. Finn ut hvorfor Unstad og Ersfjordstranda gir 1,0 helt ut til kantene.
- Hindringer: bruk bredden på tvers sett fra spoten. Skyggelengde L = W² / λ, λ = 225 m. Spot nærmere hindringen enn L gir rå eksponering 0 for retningen, lenger bak øker den gradvis mot 1.
- Toleranse ved kysten: 300 m, ikke 2 km. Linja må starte på land i et sammenhengende stykke fra spoten og nå vann innen 300 m.
Ferdig når: Grøtfjord 311 til 330 grader gir lav eksponering av geometrien alene (uten exposure_override), Grøtfjord 285 til 310 gir 1,0 rå, Steinkrøssa rett under 315 er blokkert, Lenangsøyra sine lave verdier i det smale gapet er beholdt, og tabellen mot skyggekurven for alle spots ligger i STATUS.md.

## 2. Koble del C inn i ratingen
- Reservemodellen og Hb-dempingen for reservemodellen bruker glattet eksponering (med exposure_override som tak) i stedet for vindu og skyggekurve.
- sources_disagree bruker eksponering i stedet for directness, samme grense 0,667.
- fetch.py skriver advarsel i kilderapporten når sjekksummen i exposure_baseline.json ikke stemmer med spots.json.
- BarentsWatch-timer uendret.
Ferdig når: alle faste observasjoner holder, og tabell før og etter for dagens varsel ligger i STATUS.md. Stoppregelen på 2 stjerner i CLAUDE.md gjelder.

## 3. Del B: eksponering lært fra BarentsWatch
- 10-graders bøtter, glatting mellom nabobøtter.
- Par: ren BarentsWatch-verdi, svell ute minst 0,5 m, swell_share minst 0,7, sources_disagree usann. Lagres i data/exposure.json, 120 døgn, ett par per spot og tidspunkt.
- Lært bøtte: minst 6 par over minst 2 døgn. Normalisering krever minst 3 lærte bøtter i samme periodegruppe (kort under 10 s, lang 10 s og over). Kort kan låne fra lang, ikke omvendt.
- Transfer = medianforholdet i de samme bøttene kurven normaliseres mot, når eksponering er lært.
- Blanding med geometri: vekt lært = par / (par + 10).
- exposure_override: foreslå fjerning i Logger-fanen når lært verdi ligger under taket. Aldri fjern automatisk.
- Figur per spot i Logger-fanen: eksponering per retning, antall par per bøtte, og loggene mine som merker på retningen svellet ute kom fra, farget etter stjerner.
Ferdig når: testene dekker alle reglene over, og STATUS.md viser hvor mye som er lært per spot.

## 4. Unstad: hvor ligger BarentsWatch sitt rutepunkt?
Trigg diagnose-workflowen (gh workflow run) hvis mulig, les ut punktet BarentsWatch valgte for Unstad, og regn avstand og retning fra punktet vi ba om. Bare rapporter, ikke flytt.

## Venter på Theodor
- Farstadsanden: vindu og pinne fra lokal surfer.
- Unstad: offshorevinden. Videoen 26.09 viste offshore, appen sa sidevind. Trenger flere observasjoner før noe endres.
- Grøtfjord: om exposure_override kan fjernes, når del B har lært noe.
