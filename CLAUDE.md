# Nordsurf: regler for Claude Code

## Hva dette er
Surfevarsel for Nord-Norge (og Unstad, Farstadsanden). PWA i docs/, henter i fetcher/ som kjører i GitHub Actions hver tredje time. Én bruker (Theodor) foreløpig. All tekst i appen på norsk.

## Sannhetshierarki
1. Observasjoner fra loggene (egne økter og "Observert") slår alt.
2. BarentsWatch ved spoten (fysisk kystmodell, 100 m).
3. Reservemodellen (svell ute × transfer × eksponering).
4. Geometri fra kystlinjedata (GSHHS). Mangler små øyer og skjær.
Når en modell motsier en observasjon, er det modellen som er feil.

## Faste observasjoner (skal alltid være tester, og alltid bestå)
- Grøtfjord 24.09.2026: helt flatt. met.no 1,9 m, BarentsWatch 0,3 m, Windy 1,7 m fra ca. 267 grader.
- Grøtfjord 25.09.2026: helt flatt, svell ute fra ca. 313 grader.
- Grøtfjord 26.09.2026: helt flatt.
- Lenangsøyra 26.09.2026: ikke surfbart. Mest vindsjø, bølgene i Ullsfjorden kom fra vest.
- Unstad 26.09.2026 ca. kl. 14:45: over hodet, sett nær dobbelt over hodet, tønner, offshore. 4 stjerner. Appen viste Hs 0,9 m, 15 s.

## Konvensjoner (ikke endre)
- Alle retninger internt er "fra"-retninger, 0 = nord.
- BarentsWatch totalMeanWaveDirection i API-et er retningen bølgene går MOT, samme som pilene på kartet. Regnes om til "fra" ved å legge til 180. Bevis: rå logg fra 26.09 kl. 15:00Z, Unstad, 116 grader, mens bølgene kom inn fra 296.
- Svell ute: GFS Wave via Open-Meteo. ECMWF gir ikke svellfelt der. Høyde, retning og periode for svellet skal alltid komme fra samme modell.
- Periode i surfehøyde-formelen: svellets periode ute (gjennomsnitt fra GFS Wave), ikke BarentsWatch sin periode ved kysten.
- Surfehøyde: Komar og Gaughan (1972), Hb = 0,39 × g^(1/5) × (T × H²)^(2/5). Sett = 1,27 × Hb. Flat-sperre: Hs ved spoten under 0,35 m gir 0.
- Svell som bare når spoten ved diffraksjon rundt land (rå eksponering 0) dempes ekstra i surfehøyden. Empirisk grunnlag: Grøtfjord 25.09.2026, 3 grader utenfor vinduet, helt flatt.
- To kalibreringer som ikke skal blandes: transfer (Hs mot Hs, modell mot modell) og surf_factor (surfehøyde mot logger).
- Maks bølgehøyde vises, men brukes aldri i ratingen.
- Retning mer enn 150 grader fra facing betyr at bølgene ved BarentsWatch-punktet faktisk går ut fra land (typisk vindsjø fra land, ikke svell inn). Kjent retning, ikke ukjent: gir retningsfaktor 0 (ordinær straff), gjør IKKE timen usikker og utløser ikke "kildene uenige" alene. Hvis mer enn halvparten av timene med ekte svell ute mot vinduet i en kjøring havner over 150 grader for en spot, varsles det øverst i kilderapporten som en mulig feil i konvensjonen - ratingen endres aldri automatisk av det.

## Krever Theodors ja (stopp og spør)
- Endringer i svellvinduer, havpunkter, barentswatch_point, facing, offshorevind, exposure_override, ideal_height, max_height, SHADOW_CURVE, DEFAULT_TRANSFER, vindtabellen eller stjernegrenser.
- Alt som gjør at en av de faste observasjonene over ikke lenger stemmer.
- Hvis en endring flytter stjernene med 2 eller mer for noen spot i noen time de neste 48 timene i dagens varsel: vis tabell før og etter, og stopp.
- Nye eksterne tjenester, kontoer, kostnader eller hemmeligheter.
- Sletting av data (logger, kalibreringsfiler).
- Når en oppgave i ROADMAP.md er merket "Venter på Theodor".

## Arbeidsmåte
- Én oppgave av gangen fra ROADMAP.md, i rekkefølge.
- Små steg. Alle tester (fetcher/test_rating.py og fetcher/test_pipeline.py) skal passere før commit.
- Før hver commit: la subagenten fysikk-kontrollor gå gjennom endringen. Rett det den finner, eller skriv i STATUS.md hvorfor du er uenig.
- Commit per ferdig delsteg, med tydelig norsk melding. Push når en oppgave er ferdig.
- Oppdater STATUS.md etter hver oppgave: hva som ble gjort, tall før og etter, hva kontrolløren fant, og hva som gjenstår.
- Aldri skriv ut, logg eller commit hemmeligheter.
- Kan du trigge en GitHub-workflow selv (gh workflow run) fordi gh er innlogget, gjør det i stedet for å be Theodor om det.
