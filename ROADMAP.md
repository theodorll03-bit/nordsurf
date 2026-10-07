# Nordsurf: oppgavekø

Jobb ovenfra og ned. Hopp over oppgaver merket "Venter på Theodor", og ta neste.

## 0. Grøtfjord "Flatt" med 2 166 kJ ute (Theodor, 07.10.2026) - FERDIG, begge punkter på main
Grøtfjord om ca. 10 dager: svell ute 2,3 m, 15 s, 2166 kJ, fra 271 grader (15 grader utenfor vinduet, bak Tromvik-halvøya), offshore 5 m/s. Appen viser "Flatt", 0,1 m.
1. Ordet er feil: med 2166 kJ og 2,3 m svell ute er det ikke flatt. Når årsaken til lav høyde er retningen (svell ute utenfor vinduet med lav eksponering), og energien ute er høy, skal ordet være "Treffer ikke", ikke "Flatt". "Flatt" bare når energien ute også er lav. Rett i klassifiseringen og test. **FERDIG (main): `rating.classify_low_rating()`, test 23, 144 av 1608 timer i dagens varsel bytter ord (0 stjerner endret).**
2. Diffraksjonsdempingen (ekstra demping av Hb når rå eksponering er 0) skal avhenge av perioden: langt svell bøyer seg bedre rundt land. Bruk samme p(T)-kurve som skjermingen i oppgave I (full demping ved 8 s eller kortere, 60 prosent av dempingen ved 14 s eller lengre). Kontroller at Grøtfjord 24. og 25.09 (kortere periode) fortsatt gir 0 stjerner, og vis hva denne timen blir. **FERDIG (main, via gren `natt/diffraksjon`): fysikk-kontrollør godkjent, stoppregelen slo ikke inn (8 av 1 608 timer opp, ingen 2+ innen 48 t), denne timen uendret (flat-sperren først). Kontrollørens spørsmål om Grøtfjord 279-284° står i STATUS.md.**
3. Stoppregelen gjelder: Grøtfjord har faste observasjoner med kortere periode, så dette er ikke samme tilfelle. Legg endringen i punkt 2 på egen gren med tabell og anbefaling hvis den slår inn. Punkt 1 kan gå på main.

## A. Energi (kJ) på alle spots, og myke lokale regler for Farstadsanden - FERDIG, Theodor sa ja - committet (se STATUS.md)
Energi = ρ g² H² T² / (16π), ρ = 1025, g = 9,81, altså ca. 1,96 × H² × T² kJ. Samme mål som surf-forecast. Kontroll for Farstad: 2,4 m 11 s = 1427, 3 m 11 s = 1981, 3 m 14 s = 3500, 4 m 15 s = 7400, 5,5 m 16 s = 14396, innenfor 5 prosent. Regn fra svell ute og svellperiode. Vis også energien med totalhøyde ute. Vis kJ for alle spots, i lista, på detaljsiden og i timestripa. Farstadsanden: myke lokale regler fra Magnus med "klype salt" (weight 0,7): energi full fra 3000 kJ, gradvis ned til 1500 kJ; høyvann koster 1 stjerne; offshore_strict. Loggene kan foreslå å myke opp reglene, aldri automatisk. Ferdig når: testene for formel og regler passerer, og kJ vises overalt.

## B. Langtidsvarsel 16 dager med sikkerhet i prosent - FERDIG, Theodor sa ja (committet sammen med Nordneset-fiksen)
Svell: Open-Meteo GFS Wave med forecast_days 16. Vind: met.no så langt den rekker, deretter Open-Meteo GFS-vind. Merk kilden. Tre soner: BarentsWatch til bw_until, reservemodell til dag 7, langtid dag 8 til 16 (3- eller 6-timers verdier hvis forecast.json blir for stor). Sikkerhet i prosent per dag, ikke kapping av stjerner. Startverdier (sannsynlighet for treff innenfor én stjerne): dag 1: 90, dag 2: 85, dag 3: 80, dag 4: 70, dag 5: 65, dag 6 og 7: 55, dag 8 til 10: 40, dag 11 til 16: 30. Merket "anslag". Mål treffsikkerheten selv: arkiver varselet hver kjøring (data/forecast_archive/, små filer), sammenlign med varselet laget under 6 timer før og med loggene. Når en spot har minst 30 sammenligninger for et antall dager frem, bruk målt prosent ("målt"). Varsler bare for timer med sikkerhet 70 prosent eller mer. Logger-fanen: treffprosent per antall dager frem per spot. Ferdig når: Farstadsanden fredag 16. og lørdag 17. oktober vises med sikkerhet, og testene for soner, prosent og varsler passerer.

## C. Ny visuell design, inspirert av Surfline - KREVER DESIGNPLAN MED SKJERMBILDER FØR BYGGING
Mål: appen skal se ut og føles som en ordentlig surfeapp: mer farge, tydelige grafer, rask å lese. Inspirert av Surfline sitt oppsett, men ikke kopi av deres logo, navn eller grafiske profil.
1. Fargeskala for rating, brukt overalt (stjerner, ringen på skiva, kartmerker, søyler, dagbrikker): 0 grå, 1 rød-oransje, 2 gul, 3 grønn, 4 turkis, 5 blå eller lilla. Tokens for lys og mørk modus, sjekket kontrast. Farge aldri eneste bærer av informasjon - tall eller stjerner alltid ved siden av.
2. Forsiden (lista): hvert spot som et kort med fargestripe for dagens beste rating, surfehøyde ("1,2 til 1,6 m"), kJ, vind med pil og type, og en mini-graf for de neste dagene.
3. Detaljsiden, ovenfra og ned: (a) overskrift med nåværende rating i farge, surfehøyde og ett ord; (b) surfehøyde-graf over 16 dager (søyler per time de første 7 dagene, per dag etterpå, farget etter rating, sett-høyde som tynnere søyle over, langtidsdager skravert/blekere, trykk velger tidspunkt); (c) svell (hovedsvell og vindsjø hver for seg, retning som pil, høyde, periode, kJ); (d) vind (piler farget etter type, styrke, kast); (e) tidevann (kurve over dagen, flo/fjære, nåtid); (f) lys (dag/skumring/mørke som bakgrunn i grafene); (g) lokale regler og kalibrering lenger ned.
4. Kartet: merkene farget etter rating, skiva beholdes med ringen i ratingfargen.
5. Lys og mørk modus, mobil først, iOS-kjent navigasjon, minst 44 pt trykkflater, prefers-reduced-motion.
6. Lite grafbibliotek fra cdnjs (fast versjon) eller egen SVG, ingen bundler.
**Vis designplan med skjermbilder av forsiden, detaljsiden og kartet, i lys og mørk modus, FØR bygging.** Ferdig når Theodor har sagt ja og alt er bygget og testet.

## D. Trykk for forklaring
Alle tall og begreper skal kunne trykkes: surfehøyde, sett, signifikant høyde, svell ute, vindsjø, periode, kJ, retningstreff, eksponering, vindtype, tidevann, sikkerhet, stjerner, kilder (BarentsWatch, anslag, langtid). Trykk åpner et ark nederfra med: (a) hva det betyr, kort og enkelt, med et eksempel; (b) tallene for akkurat denne spoten og timen; (c) hvordan det er regnet ut (samme kjede som breakdown), og hvilke kilder. Fjern de små "i"-ikonene der arket erstatter dem. Ett felles forklaringsbibliotek (én fil med tekstene), så samme forklaring brukes overalt. Skjermleservennlig, fungerer med tastatur. Bygges sammen med C.

## E. Sjekk BarentsWatch-punktene for alle spots - KJØRT 06.10.2026 og 06.10.2026 (ny, fersk kjøring), ingen flytting foreslått, venter fortsatt på en svelldag for prosent-metoden
Utvid workflowen "Finn BarentsWatch-punkt" til alle spots: 150, 250, 500 og 1000 m ut i retning facing, og facing ± 20 grader, pluss dagens punkter. Sammenlign med totalhøyde ute. Flagg spots der dagens punkt gir under 25 prosent av totalhøyden ute på dager der svellet ute kommer inn i vinduet. Foreslå nye punkter med lenker. Ikke endre uten Theodors ja. Theodors presisering: kandidater over 100 % avvises ikke, merkes "høy, sjekk"; for spots med observasjoner (Unstad, Grøtfjord, Lenangsøyra) velges punktet som passer observasjonene best. **Status:** workflow utvidet og kjørt (`gh`), `fetcher/bw_point_report.py` leser resultatet. Observasjons-metoden kan ikke rangere kandidater (sirkulær, se STATUS.md), men viser at Unstad sitt 05.10-avvik ikke er et punktproblem; Grøtfjord/Lenangsøyra holder flate dager flate, Farstadsanden sitt nye punkt gir 52 % av totalhøyden ute (le-problemet ser løst ut). Ingen kandidat "høy, sjekk". Prosent-metoden fikk nesten ingen svell i vinduene denne perioden - **kjør workflowen på nytt en dag med svell i vinduene** (Farstadsanden først). **Oppfølging 06.10.2026 (Nordneset-saken):** en fersk kjøring viste at ALLE kandidatpunkter (150-1000 m) gir 0,6-1,8 m for Farstadsanden sine retninger 330-356 grader, uansett avstand - et BarentsWatch-MODELLHULL (ser ikke Nordneset sin skygge i det hele tatt), ikke noe en punktflytting kan løse. Se "HASTER: Nordneset"-avsnittet i STATUS.md.

## F. Enklere logging - FERDIG (06.10.2026 natt), committet til main
Etter hvert gode vindu (3 stjerner eller mer i dagslys) for en favoritt: et "Var du der?"-spørsmål neste gang Theodor åpner appen, med ett trykk for flatt, dårlig, ok, bra og rått. "Logg fra bilde": velg et skjermbilde, appen foreslår tidspunkt (fra bildets metadata eller filnavn), og Theodor velger spot, stjerner og størrelse. Lagres som Observert med kilde. Bildet lagres ikke, bare loggen. Logg rett fra kartet: trykk og hold på skiva for å logge for den spoten og tiden.

## G. Overvåking av henteren - FERDIG (skyøkt 07.10.2026), committet til main
Appen viser "Varselet er ikke oppdatert siden ..." øverst på lista og detaljsiden når forecast.json er over 6 timer gammel. Workflowen sender ntfy-varsel (curl, uavhengig av Python) hvis kjøringen feiler, og `fetch.health_check()` sender ett driftsvarsel per problem (en kilde mangler for alle spots, for få timer, ugyldige tall), høyst én gang per døgn per problem. Helsesjekk-rader i kilderapporten. Se STATUS.md.
Appen: vis tydelig advarsel øverst hvis forecast.json er mer enn 6 timer gammel ("Varselet er ikke oppdatert siden kl. X"). Workflowen: send ntfy-varsel til Theodor hvis henteren feiler, eller hvis en kilde (BarentsWatch, met.no, Open-Meteo, Kartverket) mangler for alle spots i en kjøring. En enkel helsesjekk i kilderapporten: alle spots har data, ingen tomme eller ugyldige tall, horisont som forventet.

## H. Mørketid i praksis - FERDIG (skyøkt 07.10.2026), committet til main
Lys for 15.11/21.12/15.01 for alle spots tabellført i STATUS.md (4-6 t skumring midt på dagen selv 21.12, aldri "mørkt hele dagen"). Beste vindu, dagbrikker og varsler bruker skumringstimene riktig. Rettet: timestripa skilte ikke skumring fra mørkt visuelt (nytt `--dusk`-token i begge moduser). Ny test (test_pipeline 12).
Kjør lysberegningen for alle spots for 15. november, 21. desember og 15. januar. Vis brukbart lys per dag og sjekk at timestripa, dagbrikkene, beste vindu og varsler oppfører seg riktig når det bare er skumring. Rett det som ikke fungerer.

## I. Skjerming: hvor langt inn i en bukt ligger spoten - PARKERT 07.10.2026 (Theodors avgjørelse), IKKE merget
Geometrien (`lokal/uferdig`, algebra-feilen rettet) og de ekte BarentsWatch-kalibreringsparene **rangerer spotene MOTSATT av hverandre**: geometrien sier Grøtfjord/Ersfjordstranda/Tromvik er blant de MEST åpne (høydefaktor 0,80-0,85), mens BarentsWatch sine egne, målte par sier de er de MEST skjermede (lært transfer 0,09-0,30 - lavest av alle åtte spots). Lenangsøyra og Unstad stemmer bedre (hhv. 0,55/0,764 og 0,57/1,0). Så lenge geometrien og den ekte målingen peker motsatt vei for tre av seks spots, har ikke modellen noe å stå på - en startverdi som er feil vei er verre enn ingen startverdi. Se STATUS.md "Oppgave I" for tallene og fysikk-kontrollørens fulle vurdering.

**Skjerming læres i stedet fra data, som før:** transfer fra BarentsWatch sine egne par (`calibrate.bw_transfer()`, krever minst 40 par over minst 3 døgn) og surf_factor fra loggene dine (`calibrate.learn()`) - begge allerede i drift, ingen endring trengs. Reservemodellen bruker `DEFAULT_TRANSFER` (0,6) som startverdi for alle spots til nok BarentsWatch-par er samlet inn, akkurat som før oppgave I startet.

Gren `lokal/uferdig` ligger urørt (IKKE merget, IKKE slettet) - alt arbeidet er der hvis BarentsWatch sine par en gang samler seg i SAMME rekkefølge som geometrien (verdt å sjekke igjen når en spot som Grøtfjord har fått flere enn de 3-11 parene den har i dag), eller hvis en annen geometrisk metode (f.eks. forankret i swell_window i stedet for facing, eller en som ikke overlapper med del C sin eksponeringskurve - se fysikk-kontrollørens punkt A) gir en rangering som faktisk stemmer med målingene.

Opprinnelig oppgavetekst (for referanse, ikke lenger i arbeid):
Grøtfjord ligger flere km inne i en bukt med smal åpning, Unstad rett ut mot havet. BarentsWatch tar hensyn til dette de første ca. 60 timene, men reservemodellen bruker samme startverdi for transfer (0,6) for alle spots til en egen verdi er lært. Gi hver spot en startverdi ut fra geometrien.
1. Beregn for hver spot (offline, GSHHS, samme regler som check_spot.py - 300 m kysttoleranse, 150 m klaring): (a) avstand til åpent hav d_open - gå ut i retning facing (og facing ± 20, bruk kortest) til hele halvsirkelen (180°) sentrert på facing har fri linje; (b) åpning ved spoten - andel av halvsirkelen med fri linje fra spoten selv; (c) bredde på åpningen B ved punktet i a, vinkelrett på facing; (d) andel energi gjennom åpningen f = B / (B + 2 × d_open × tan(20°)), høydefaktor = √f.
2. Periode straffer kort mer enn langt: skjermingsfaktor = 1 − (1 − høydefaktor) × p(T), p(T) = 1,0 ved 8 s eller kortere, 0,6 ved 14 s eller lengre, lineært imellom.
3. transfer_prior = DEFAULT_TRANSFER × skjermingsfaktor, normalisert så en åpen spot (Unstad) får ca. 1,0. Bare reservemodellen, bare når transfer ikke er lært. Rekkefølge: lært fra logger > lært fra BarentsWatch > transfer i spots.json > transfer_prior fra skjerming > DEFAULT_TRANSFER.
4. Lagre per spot i data/shelter.json med sjekksum (koordinater, vindu, facing) som exposure_baseline.json. Kilderapporten varsler ved sjekksum-avvik.
5. Tabell i STATUS.md for alle spots: d_open, åpning, B, f, høydefaktor, skjermingsfaktor ved 8/14 s, lært BarentsWatch-transfer der den finnes. Forventet rekkefølge åpen til skjermet: Unstad/Farstadsanden åpne, Grøtfjord/Tromvik/Ersfjordstranda i midten, Lenangsøyra mest skjermet (~40 km inn). Si fra ved avvik og hvorfor. Der BarentsWatch-transfer er lært: sammenlign med skjermingsfaktoren - henger de ikke sammen, foreslå justering, ikke endre uten Theodors ja.
6. Visning: detaljsiden "Skjerming: åpen / delvis skjermet / skjermet", forklaring ved trykk (del av D) - hva det betyr, tallene for spoten, at langt svell bøyer seg bedre inn.
7. Tester: rett kyst gir f nær 1; smal dyp bukt gir lav f; kort periode straffes mer enn lang; rekkefølgen for transfer i punkt 3; alle faste observasjoner holder (særlig Grøtfjord 24-26.09 og Unstad).
8. Stoppregelen gjelder for endringer i reservetimene. Vis stjernetabell før og etter for alle spots.

Etter hver oppgave (A-I): oppdater STATUS.md, kjør fysikk-kontrollør (for A og B), commit og push.

## J. met.no sin bølgemodell som kilde for svell langs kysten - OMDØPT 07.10.2026: WAM800 lagt ned, retter seg nå mot WAVEWATCH III 4 km (PLAN FØRST)
WAM800 (opprinnelig mål) er offisielt lagt ned - bekreftet direkte mot thredds.met.no: står under "Discontinued" → "Waves", "Production ends Oct. 1. 2025", stemmer med filenes egen "Last Modified" (siste filer 2025-10-07/08). Gren `natt/wam800` (utforskingen, J.1-J.3 for WAM800) ligger urørt, ikke bygget videre på.

**Ny retning (Theodors oppfølging samme dag): met.no sin WAVEWATCH III 4 km regionale modell** - aktiv drift (siste fil samme morgen), dekker hele norskekysten med god margin, deler svell og vindsjø i egne partisjoner (bekreftet fra variablenes `standard_name`), og bruker ALLEREDE "fra"-retningskonvensjon (ingen +180 nødvendig, enklere enn WAM800/BarentsWatch). Punktsøk for alle åtte spots og en første sammenligning (Unstad/Grøtfjord/Farstadsanden mot BarentsWatch og GFS Wave) er gjort - se STATUS.md for tallene og en ærlig, ikke-konkludert lesning (WW3 sin svellhøyde er gjennomgående høyere enn begge de andre kildene for alle tre; retningen stemmer bedre med BarentsWatch enn GFS Wave for to av tre, omvendt for den tredje). **Ingenting koblet inn i ratingen.** Verktøy: `fetcher/ww3_explore.py` (nytt, bare `requests`, OPeNDAP-tekstgrensesnitt). Neste steg, ikke gjort: sammenligning mot de navngitte observasjonsdagene (krever at WW3 sin "Archive Files"-katalog dekker datoene - ikke sjekket ennå), og et forslag til hvordan den skal brukes (samme type plan som WAM800 hadde: a-d i tidligere versjon av denne oppgaven). Vent på Theodors ja før noe av dette bygges videre.
Bakgrunn: BarentsWatch (ST-wave, 100 m, laget for farleder) gir bare total bølgehøyde og snittretning for svell og vindsjø sammen. I skjermede områder dominerer vindsjøen, så ekte svell forsvinner i tallet. Vi har sett det ved Lenangsøyra (vindsjø som så ut som bølger), Unstad (konsekvent for lav) og Farstadsanden (blind for Nordneset). Met.no anbefalte selv i en rapport fra 2017 å kalibrere BarentsWatch mot WAM800 og bruke WAM800 direkte der oppløsningen er god nok.
WAM800 (MyWave WAM, 800 m) dekker kysten og deler bølgene i svell og vindsjø med egen høyde, periode og retning.

1. Finn datasettene på thredds.met.no (katalogen for WAM800 / MyWave 800 m), hvilke regioner som dekker hver spot, variabelnavn for total, svell og vindsjø (høyde, periode, retning, og retningskonvensjon), horisont og hvor ofte de oppdateres. Hent bare punktene vi trenger (OPeNDAP eller tilsvarende), ikke hele filer.
2. For hver spot: velg nærmeste vått rutepunkt som ligger åpent foran spoten (typisk 1 til 2 km ut i retning facing, ikke inne i le). Vis koordinater og avstand.
3. Hent WAM800 for alle spots og vis en tabell for neste 48 timer: svell (høyde, periode, retning), vindsjø, total, sammenlignet med BarentsWatch ved spoten og Open-Meteo/GFS svell ute.
4. Hvis det finnes arkivdata for datoene med observasjoner: sammenlign kildene mot observasjonene (Unstad 26.09, 27.09, 28.09, 05.10, Grøtfjord 24. til 26.09, Lenangsøyra 26.09). Hvilken kilde forklarer observasjonene best?
5. Foreslå hvordan WAM800 skal brukes, f.eks.:
   a. Svellretning og periode fra WAM800 i stedet for GFS når WAM800 finnes (bedre oppløsning nær kysten), også for vindu, eksponering og "kildene er uenige".
   b. Svellandel ved kysten fra WAM800 i stedet for anslaget fra Open-Meteo ute.
   c. Svellhøyde fra WAM800 direkte for åpne spots (Unstad, Farstadsanden), og BarentsWatch fortsatt for skjermede spots der 800 m er for grovt.
   d. Hvilken kilde som brukes per spot kan bestemmes av treffsikkerhetsmålingen over tid.
6. Vis planen og tabellene, og vent på ja før noe kobles inn i ratingen. Legg WAM800 i kilderapporten.

## K. Mindre info i appen, mer ved trykk
Appen viser for mye på en gang. Standard skal være enkelt, og detaljer skal komme når man trykker.
1. Lista: per spot bare navn, rating (farge og stjerner), surfehøyde, og vind som pil med type. Ingenting mer.
2. Detaljsiden, øverst: stjerner med ett ord ("Bra", "Blåst ut", "Treffer ikke"), surfehøyde, periode og vind. Så timestripa eller grafen.
3. Alt annet (svell ute, svellandel, energi, retningstreff, eksponering, tidevann, lys, vann og luft, kilder, lokale regler, sikkerhet) samles under én seksjon "Detaljer" som er lukket som standard og åpnes ved trykk.
4. Hvert tall eller begrep åpner forklaring ved trykk (oppgave D), med tallene for spoten og hvordan det er regnet ut.
5. Kartet: merke med farge og stjerner. Skiva og høydeplata som i dag, men høydeplata bare med surfehøyde og periode. Mer ved trykk.
6. Advarsler (kildene er uenige, BarentsWatch i le, gammel data) vises som én kort linje øverst, med forklaring ved trykk.
7. Bygges sammen med oppgave C (design) og D. Vis skjermbilder i mobilvisning før og etter.

## L. Testlab for treffsikkerhet (Theodor, skyøkt 07.10.2026) - BYGGET på gren `sky/testlab`, IKKE merget
`fetcher/backtest.py` re-rater alle tidspunkter med observasjoner (faste observasjoner fra CLAUDE.md, logger når LOGS_REPO finnes, benchmarks fra data/benchmarks.json) med varianter av ratingen, og skriver én tabell per variant pluss en samlet tabell til data/backtest/ (ukentlig workflow `.github/workflows/backtest.yml`, mandag 05:41 UTC, pluss manuelt). Varianter: grunnlinje, WW3-svell i stedet for GFS (uten surf_factor_prior for Unstad), energi med toppperiode (WW3 ptp1 eller gjennomsnitt × 1,25), begge WW3-svellene (beste teller), og vind rettet med målinger (oppgave M). WW3-arkivet (`fetcher/ww3_archive.py`, data/ww3/archive/) vokser hver uke. Leser og rapporterer bare - endrer aldri spots.json eller ratingen. Resultat og anbefaling: se STATUS.md ("Skyøkt (dag) 07.10.2026").

## M. Vindmålinger fra KystVær/Kystdatahuset i skyggemodus (Theodor, skyøkt 07.10.2026) - HOPPET OVER, ingen åpen kilde funnet
Fire sonderingsrunder i GitHub Actions (`fetcher/kystvaer_probe.py`, resultat i data/wind_obs/probe.md): Kystdatahuset sitt Open API (142 ruter) har ingen vær-/vindruter (bare AIS, skip, seilaser, ankring, los m.m.), KystVær-datasettet ligger bak en JS-portal uten lesbart endepunkt, og met.no Frost krever registrert client-id (ny konto = krever Theodors ja). Strukturen står klar (variant `vind_korr` i testlaben, filformat data/wind_obs/obs_*.json) hvis en kilde dukker opp. Kandidat-stasjoner per spot (ikke verifisert) i STATUS.md.

## 1. Unstad for lav høyde - FERDIG, Theodor sa ja
Fire observasjoner (26.09 kl. 14:45, 27.09 morgen, 28.09 kl. 13/"Safe to say it's firing") viste at Unstad rates for lavt, av to ulike årsaker. Først: retningsfaktor-fiksen (ja, også for Steinkrøssa - 51 grader skrått er normalt der svellet bøyer seg rundt en odde) og `surf_factor_prior`/`ideal_height`-justering i stedet for å senke `ideal_height` (ville skjult årsaken). Deretter (28.09): `sources_disagree` kappet stjernene når svellet ute var rett under 0,667 i eksponering, selv når BarentsWatch ved SPOTEN selv bekreftet treff - ny `bw_confirms` (retning innenfor 30 grader av facing OG høyde minst 0,35 m uten retningsfaktor) overstyrer nå det også. Fysikk-kontrollør fant en reell feil under review (overstyringen slo inn på `exposure()` sin "ukjent retning"-nøytralverdi 0,7 når `dir_offshore` manglet) - rettet, ny regresjonstest 9.3c. Stjernetabell viste 9 timer opp på Unstad (seks med 3 stjerner) i dagens live varsel - samme mønster som observasjonen, Theodors ja. Samtidig lagt til unntak i CLAUDE.md sin 2-stjerners stoppregel (retning som matcher faste observasjoner) og automatisk cache-versjonering for docs/sw.js (var ikke bumpet siden 26.09, ni commits). Se STATUS.md.

## 2. Vinden forsvinner fra onsdag kl. 12 - FERDIG
met.no Locationforecast gir timesdata bare de første ca. 60 timene, deretter hver 6. time. Rettet med interpolering (`sources.weather_interpolate()`). Se STATUS.md.

## 3. Vindpila på spot-skiva ser rotete ut - FERDIG
Den gikk tvers gjennom hele skiva, stakk ut på én side, og pilhodet havnet under ratingringen. Rettet: vindpil (vindvimpel) utenfor ratingringen, vindanimasjon klippet til skiva og lagt lavt i z-rekkefølgen, etikett (vindstyrke+type) låst til fire trygge hjørnesoner (ringens radius er for nær skivas egen kant til at en etikett kan følge vindretningen kontinuerlig uten enten å overlappe ringen eller stikke langt utenfor - målt empirisk). Tre runder fysikk-kontrollør: struktur/geometri, pilrotasjon som lekket inn i etiketten + "vind mangler" kunne kollidere med svellets retningsetikett, og et gjenstående smalt kollisjonsvindu i den fiksen. Alle rettet og empirisk re-verifisert. Merget til main. Se STATUS.md.

## 4. Grøtfjord: skill "blåst ut" fra ekte flatt - FERDIG
Oppfølging 05.10.2026: fire-delt grunn for 0/1 stjerne (Flatt/Blåst ut/Stormsjø/Treffer ikke), samme ord overalt i appen, vind-dominans fanges nå uavhengig av flat-sperren. Se STATUS.md.

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
- **Unstad, tredje gang - trigger nådd (05.10.2026, se STATUS.md):** vinden appen beregner (met.no) stemmer ikke med observasjonene TRE ganger nå (26.09: video viste offshore, appen sa sidevind; 27.09: video viste nesten vindstille, appen beregnet 5-8 m/s side-onshore; 05.10 kl. 09-12: Instagram-observasjon "offshore-sprøyt", appen beregnet 9-10 m/s SIDEVIND fra ca. 200-206 grader, ca. 90 grader fra offshore-sektorens senter). Samme dag viste surfehøyden (1,0-1,1 m, "middels") også for lavt mot observasjonen ("over hodet", ca. 2,4 m) - mulig fjerde runde med samme mønster som `surf_factor_prior` ble satt for (26-27.09), eller et eget problem. IKKE lagt til som fast observasjon ennå (stjernene er 0, ikke de minst 3 observasjonen viste). **Theodors forslag `offshore_wind` [70,215]: sjekket mot alle fem observasjoner, dekker IKKE alle fire problemtimene (46,5-84,5 grader fra ny senterposisjon, over 45-gradersgrensen for "offshore") - bare 28.09 (allerede riktig) havner innenfor. Ingen endring gjort, se STATUS.md punkt 14 for full tabell og et alternativt senter (~187 grader) som ville dekket alle ti enkelttimer.** Venter på Theodors neste steg.
- Farstadsanden (lagt til 05.10.2026 med foreløpige verdier, se STATUS.md og spots.json): offshore_wind [85,175] skal bekreftes av lokal surfer. **06.10.2026: Theodor flyttet pinnen ~200 m nordvest** (mistanke: gamle pinnen lå innerst i en bukt, forklarer trolig den implausible BarentsWatch-høyden under) og ga nye verdier for spot/swell_window [284,326]/facing (310)/havpunkt/barentswatch_point (valgt manuelt i BarentsWatch sitt kart, rettet én gang samme dag) - alt uavhengig bekreftet (check_spot.py, geodesiberegninger, GSHHS, Open-Meteo), se STATUS.md. **Fortsatt uavklart: ekte BarentsWatch-tall for det nye punktet ikke hentet (ingen nøkler/gh lokalt) - venter på at Theodor trigger workflowen "Finn BarentsWatch-punkt" (grid for Unstad og Farstadsanden, 150/250/500 m-punktene for Farstadsanden inkludert), så et punkt kan velges med ekte tall.**
- Tromvik: offshorevinden (105-195) er utledet fra facing, ikke bekreftet lokalt eller fra satellittbilde ennå.
- Grøtfjord: om exposure_override kan fjernes, når del B har lært noe.
- Ersfjordstranda: fri sektor (300 m kysttoleranse) er [288, 320], men swell_window er satt til [294, 320] - 6 grader smalere i underkant enn det som faktisk har fri linje til åpent hav. Mulig forslag: utvid vinduet til 288. Ikke gjort - krever Theodors ja (se oppgave 8 i STATUS.md).
