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
- Unstad 26.09.2026 ca. kl. 14:45: over hodet, sett nær dobbelt over hodet, tønner, offshore. 4 stjerner. Appen viste Hs 0,9 m, 15 s. Surfehøyde skal være ca. 2,4 m (med surf_factor_prior, se spots.json).
- Unstad 27.09.2026 morgen (Instagram, Lofoten Surfsenter, "decent morning"): rene linjer, brysthøyt til hodehøyt, ca. 3 stjerner. Kl. 06-08 skal gi minst 2 stjerner. Vinden appen beregnet (5-8 m/s side-onshore) stemmer ikke med videoen (nesten vindstille) - se "Venter på Theodor".
- Unstad 28.09.2026 ca. kl. 13 (Instagram, Lofoten Surfsenter, "Safe to say it's firing"): lange, rene linjer, offshore-sprøyt, 4 til 5 stjerner. Svellet ute var 3-5 grader utenfor vinduet (eksponering 62-66 %), men BarentsWatch ved spoten selv bekreftet treff (1 grad fra facing). Kl. 12-15 skal gi minst 3 stjerner.

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

## Lokalkunnskap (myke regler, ikke harde sperrer)
Lokale surfere kjenner spoten bedre enn noen modell. Denne kunnskapen skal justere ratingen som en "klype salt" - aldri som en hard sperre som overstyrer alt annet. Lagres i spots.json sitt valgfrie `local_rules`-felt (se `rating.local_energy_factor()`/`local_rules_penalty()`), med en `weight` (0-1) som demper EFFEKTEN av hele regelsettet, ikke terskelverdiene selv - weight 0 gir alltid null effekt, weight 1 gir rå effekt ublandet. Én persons erfaring er fortsatt bare én persons erfaring: sett weight lavere enn 1,0 med mindre flere lokale kilder er enige.

- **Farstadsanden (06.10.2026), Magnus, lokal surfer (Molde):** "Bra når det er lavvann, minst 3000 kJ energi (surf-forecast sitt tall), offshorevind og minst 3 m på yr. Noe annet har alltid vært bomtur." Martin (annen lokal surfer) er enig i at lavvann er best, men ga ingen egne tall - bare Magnus sine terskler er lagt inn. weight 0,7 ("klype salt" - Theodors egen formulering, ikke tallfestet strengere enn det). Se spots.json sin `_local_rules`-kommentar for nøyaktige tall.
- Loggene kan foreslå å MYKE OPP en regel (se `renderLogs()` sin regel-forslag-sjekk i docs/index.html) når minst 3 logger med 3 stjerner eller mer bryter den samme regelen - det er et tegn på at terskelen er for streng. Forslaget vises bare, det endrer ALDRI `local_rules` automatisk - bare Theodor kan stramme inn eller løsne en terskel.
- Legg til lokalkunnskap for andre spots etter samme mønster: `local_rules` i spots.json, kilden navngitt her (ikke anonymt "en lokal sa"), og en `weight` som reflekterer hvor sikker kilden er.

## Krever Theodors ja (stopp og spør)
- Endringer i svellvinduer, havpunkter, barentswatch_point, facing, offshorevind, exposure_override, ideal_height, max_height, SHADOW_CURVE, DEFAULT_TRANSFER, vindtabellen eller stjernegrenser.
- Alt som gjør at en av de faste observasjonene over ikke lenger stemmer.
- Hvis en endring flytter stjernene med 2 eller mer for noen spot i noen time de neste 48 timene i dagens varsel: vis tabell før og etter, og stopp. Unntak (lagt til 04.10.2026, etter Unstad 28.09): hvis ALLE slike timer for spoten går i SAMME RETNING som en fast observasjon for den spoten (f.eks. opp, etter observasjoner som viser at spoten rates for lavt), og alle faste observasjoner fortsatt holder - ikke stopp. Commit, push, og skriv tabellen i STATUS.md i stedet. Stopp fortsatt hvis noen time går MOTSATT vei av observasjonene, eller hvis spoten ikke har noen faste observasjoner å sammenligne retningen mot.
  - Tillegg (06.10.2026, etter Farstadsanden/Magnus): `local_rules` som Theodor har godkjent, med navngitt kilde (se "Lokalkunnskap"), teller som faste observasjoner for den spoten i denne regelen. Endringer i SAMME retning som reglene trekker (f.eks. ned i en uke der energien ligger under kildens grense) skal da committes og rapporteres i STATUS.md i stedet for å stoppe. Endringer i MOTSATT retning av reglene stopper fortsatt.
- Nye eksterne tjenester, kontoer, kostnader eller hemmeligheter.
- Sletting av data (logger, kalibreringsfiler).
- Når en oppgave i ROADMAP.md er merket "Venter på Theodor".

## Arbeidsmåte
- Én oppgave av gangen fra ROADMAP.md, i rekkefølge.
- Små steg. Alle tester (fetcher/test_rating.py, fetcher/test_pipeline.py, fetcher/test_exposure_learn.py, fetcher/test_docs_cache.py) skal passere før commit.
- Endrer du noe i docs/ (utenom docs/data/): kjør `python fetcher/update_sw_cache.py` før commit, og ta docs/sw.js med i samme commit. Cache-versjonen der er en hash av docs/ sitt innhold, ikke en manuelt telt streng (lagt til 04.10.2026, etter at ni commits 26.09-03.10.2026 endret PWA-shellet uten at installerte PWA-er oppdaget det - se STATUS.md) - test_docs_cache.py feiler hvis den er utdatert, så dette fanges av "alle tester skal passere" over uansett om du glemmer scriptet.
- Før hver commit: la subagenten fysikk-kontrollor gå gjennom endringen. Rett det den finner, eller skriv i STATUS.md hvorfor du er uenig.
- Commit per ferdig delsteg, med tydelig norsk melding. Push når en oppgave er ferdig.
- Oppdater STATUS.md etter hver oppgave: hva som ble gjort, tall før og etter, hva kontrolløren fant, og hva som gjenstår.
- Aldri skriv ut, logg eller commit hemmeligheter.
- Kan du trigge en GitHub-workflow selv (gh workflow run) fordi gh er innlogget, gjør det i stedet for å be Theodor om det.
