# Nordsurf design B 4.0 «Papir»

Godkjent av Theodor 09.11.2026 («Det ser veldig bra ut»). Laget i samtale med Claude etter fire runder med designagenter. Denne fila er fasiten for utseendet. Skissene ligger i `skjermer/` (PNG) og `kilde/` (HTML-maler). Bildene i skjermer/ og foto/ inneholder EOxCloudless-satellittbilder med lisens CC BY-NC-SA. De skal ALDRI inn i git eller docs/. Bruk dem bare som referanse.

## 1. Seks regler

1. **Papir først.** Om dagen er bakgrunnen Skum (#F2EFE8), og marineblå (#002941) er blekk: tekst, land på kartet, streker og knapper. Det mørke temaet heter **mørketid**. Det er det samme designet med marineblå bakgrunn. Appen følger systemets lys/mørk-innstilling.
2. **Korall betyr god surf, og bare det.** Korall brukes på tall fra 4 og opp, beste vindu og svell inne i vinduet. Det brukes aldri på tekst under 24 px i dagtema, og aldri i bilder.
3. **Lyseblått (#B6DFED) er vann og data.** Det brukes på grunnvannsbåndet langs kysten på kartet og på tidevannsbåndet. Det er aldri tekstfarge.
4. **Sekundærtekst er varm grå,** ikke blå.
5. **Stor forskjell i størrelse.** Hver skjerm har ett stort tall eller navn. Etiketter er små (11–12 px). Mellomstørrelsene er tatt bort.
6. **Ingen bokser.** Det er ingen kort og ingen omrissede merkelapper, og listene på mobil har ingen streker mellom radene. Seksjoner skilles med en dobbel strek som i en tidevannstabell. Tabeller på web har tynne radlinjer.

## 2. Farger (tokens)

| Token | Dag (papir) | Mørketid |
|---|---|---|
| bg | #F2EFE8 | #002941 |
| ink (tekst, land, streker) | #002941 | #F2EFE8 |
| muted (sekundærtekst) | #5E5A51 | #B5B0A6 |
| hair (tynne linjer) | #D8D2C6 | #244D63 |
| outline (ruter, tomme felt) | #B9B2A4 | #5D6F78 |
| signal (korall) | #C05151 | #FD6E6E |
| on-signal (tall i korallrute) | #F2EFE8 | #002941 |
| data/vann | #B6DFED | #B6DFED |
| tidevannsbånd, opasitet | 0,55 | 0,16 |
| kartland | #002941 | #E3D3B0 (sand) |
| stedsnavn på land | #F2EFE8 | #002941 |
| mørk time, skygge | rgba(0,41,65,.12) | rgba(0,0,0,.38) |
| skumring, skygge | rgba(0,41,65,.05) | rgba(0,0,0,.18) |
| ikke nådd stjernesegment | rgba(0,41,65,.07) | rgba(242,239,232,.10) |
| skravur (data mangler) | rgba(0,41,65,.35) | rgba(242,239,232,.35) |
| tekst/pil i mørk time | #8A8478 | #7E8A8F |
| svell utenfor vinduet (pil) | #8A8478 | #8C9AA0 |

Kontrast (WCAG): ink på bg 13,1:1. Muted på bg er 5,98:1 om dagen og 6,98:1 i mørketid. #C05151 på Skum er 4,03:1, så det holder bare for stor tekst (minst 24 px fet) og grafikk. Liten tekst i korall er ikke lov i dagtema. Sand er aldri bakgrunn for tekst i en annen farge enn navy (10,2:1).

## 3. Skrift

- **Martian Mono** (variabel: bredde 75–112,5, vekt 100–800) brukes til tall, klokkeslett, spotnavn, etiketter og faner. Store navn og tall har font-stretch 87,5 %. Navn over 12–13 tegn får 75 %.
- **Familjen Grotesk** (400/500/600) brukes til setninger, overskrifter og forklaringer.
- Begge har OFL-lisens og kan ligge selv i docs/fonts.

| Rolle | App | Web | Spesifikasjon |
|---|---|---|---|
| Spotnavn, hero | 60/54 | 144/124 | Martian 800, VERSALER, stretch 87,5 % |
| Stort tall (dagens tall) | 76/64 | 128/104 | Martian 800, stretch 87,5 %, tabulære tall |
| Beste vindu («10–13») | 44/40 | 64/56 | Martian 800, signal |
| Svellhøyde | 56/52 | 96/88 | Martian 800 |
| Overskrift | 30/34 | 60/64 | Familjen 600, −0,02 em, én setning per linje |
| Brødtekst / dom | 16–18/22–26 | 18/27 | Familjen 400 |
| Liste: navn | 20/22 | 26 | Martian 800, VERSALER |
| Liste: tall | 44/40 | 44/38 | Martian 800 |
| Etikett | 11/14 | 12/16 | Martian 500, VERSALER, 0,04 em, muted |
| Seksjonstittel | 11 | 12 | Martian 700, VERSALER, ink |

Høyst rundt 8 etiketter med versaler per mobilskjerm. Minste tekst er 11 px.

## 4. Avstand og seksjoner

- Avstandsskala: 4, 8, 16, 24, 40, 64. På web kommer 96 og 144 i tillegg.
- **Seksjonsstart:** 2 px ink-strek, 3 px luft, 0,75 px ink-strek, 8–10 px luft, så tittelen (venstre) og eventuelt en kommentar i muted (høyre).
- **Lister på mobil:** ingen streker mellom radene, men 20–24 px luft.
- **Tabeller på web:** 1 px hair mellom radene.
- **Knapper:** primærknappen er massiv ink med bg-farget tekst. Sekundærknappen har 2 px ink-kant. Trykkflater er minst 44 pt.

## 5. Vurderingen på skjermen

- **Tall fra 0 til 5 i stedet for stjerneikoner** i lister, på kart og i ukeoversikter. Tallet er det samme som dagens stjerner, så ingenting i modellen endres. Ordet etter tallet hentes fra ordene appen allerede har i strings.js. Ordene i skissene (FLATT, KNAPT, SURFBART, BRA, VELDIG BRA, TA FRI) er bare plassholdere, og Theodor velger.
- **Korall fra 4 og opp:** tallet, ruta i ukeoversikten, ringen på kartet og beste vindu. Fra 0 til 3 er det ink.
- **Tapte poeng:** stiplet korall-omriss i timestripa, og grunnen skrevet ut som tekst («−1 TIDEVANN», «−2 VIND»).
- **Data mangler:** skravur.
- **Mørke timer** (sola lavere enn −6°, borgerlig skumring) får ingen vurdering på skjermen. Kolonnen skygges, piler og tall blir grå, og overskriften sier «BARE LYSE TIMER FÅR TALL». Modellen kan regne som før, dette er bare visning.
- **Ukeoversikt per spot:**
  - 7 ruter på 24 pt med tallet inni.
  - Korall fylt fra 4 og opp. Ellers 1 px outline og ink-tall, og 0 skrives i muted.
  - 12 pt ekstra luft etter dag 3, fordi dag 4–7 er usikre.
  - Dagnavn (LØ SØ MA …) står under rutene, og i dag er fet.
- **Timestripa på forsiden (web):** 13 ruter for 06–18. Korall betyr 4–5, ink 3, outline-farge fylt 1–2, tomt omriss 0 og skygge mørkt. Forklaringen står under tabellen.

## 6. Skjermene

### A. App, Hjem (`skjermer/1-app-hjem-dag.png`, `2-app-hjem-morketid.png`, kilde `kilde/B4-hjem-app.dc.html`)

1. **Topplinje (44 pt):**
   - Til venstre: «LØR 14.11 · LYS 07:45–15:10» (etikett).
   - Til høyre: «Fra Tromsø ▾». Det er utgangspunktet for kjøretid, og brukeren kan bytte det eller bruke posisjon med tillatelse.
2. **Overskrift:** to korte setninger, én per linje, laget av dataene. Den MÅ stemme med lista under. Hvis lista sier at vinden ødelegger, skal overskriften ikke si «flatt».
3. **Kart, 220 pt, kant til kant:**
   - MapLibre-kartet (PR #15) med ny stil:
     - Hav = bg.
     - Land = kartland.
     - Et grunnvannsbånd på 6–7 px i #B6DFED tegnes som linje under landfyllet.
     - Stedsnavn står på land i Martian 11, versaler, 0,2 em sperring.
   - **Spotmarkør = Vinduet-merket i liten utgave:**
     - En ring på 18 pt med 3 pt strek.
     - Åpningen (84°) peker mot midten av spotens svellvindu.
     - Ringen er korall fra 4 og opp, ellers ink.
     - Bak ringen ligger en bg-farget skive på 26 pt.
     - Etiketten er Martian 12/800, versaler, med tallet etter, og har en bg-farget glorie.
   - Markører nærmere enn 24 pt slås sammen (for eksempel «TROMVIK · GRØTFJORD 2»).
   - Lag markørene og svellkilen som ekte MapLibre-lag (symbol, line og fill), ikke som HTML-overlegg oppå kartet. Da virker de også når kartet vippes i 3D senere (privat/ideer/3d-kart.md).
   - Kreditering under kartet: «Kart: Kartverket», eller kilden som faktisk brukes.
4. **FAVORITTER** (seksjonsstart, til høyre står «REDIGER»). Hver rad:
   - Tallkolonne på 44 pt.
   - NAVN.
   - Metalinje: «REGION · KJØRETID · ORD · −N ÅRSAK».
   - Setning i Familjen 16/22, ink (ikke muted), laget av forklaringen (explain.js).
   - Valgfri OBS-linje med siste observasjon fra loggene, yngre enn 7 dager: «OBS 08:50 «Krapp og rotete …»».
   - Ukeoversikt.
   - Den første favoritten med 4 eller mer får et kornfoto på 120 pt over navnet.
5. **Fanelinje:** HJEM / UTFORSK / LOGGER i Martian 11. Den aktive fanen er fet og ink, med fylt ikon.

### B. App, spotside under Utforsk (`3-app-spot-dag.png`, `4-app-spot-morketid.png`, kilde `kilde/B4-app.dc.html`)

1. **Kornfoto, 220 pt.**
   - Tilbakeknapp på en bg-farget plate: «‹ UTFORSK», eller «‹ HJEM» når man kom fra Hjem. Navigasjonsstakken skal bevares.
   - Favorittknapp.
2. **Navneplate** i bg-farge uten kant, som overlapper bildet med 34 pt. Navnet står i 60 px.
3. **Metalinje:** «LOFOTEN · 7 T FRA TROMSØ · LØR 14.11».
4. **Dom:**
   - Til venstre: dagens tall (76 px) + ord + «I DAG».
   - Til høyre: «BEST» over vinduet i 44 px korall.
   - Under: setning i Familjen 18/26.
5. **Faktalinje:** LYS · LUFT · FØLES · VANN · OPPDATERT. Vis bare det vi har data for.
6. **KL. hh** (seksjonsstart, til høyre timens tall + ord + grunn):
   - Svell stort: «1,7 m» + «12 s · fra VNV 301°».
   - Under står to linjer: VIND (tall + «fralands · kast 7») og TIDEVANN (tall + «↑ høy 16:44»), med små piler og symboler.
7. **TIME FOR TIME** (06–18). Samme interaksjon som i dag: dra, piltaster og skjult range-input for VoiceOver.
   - Bar på 4 px over beste timer.
   - Fem segmenter per time.
   - Vindpil og styrke.
   - Tidevannskurve med spotens foretrukne bånd og stiplet korall der tidevannet koster.
   - NÅ-linje.
   - Mørke timer som i punkt 5 over.
8. **RETNING KL. hh:**
   - Skive på 168 pt med kornfoto: hele skiva på 30–35 % opasitet, og vinduets sektor i full styrke.
   - Ringen er brutt ved vinduet, og offshore-buen er markert.
   - Svellpila er korall når svellet er i vinduet.
   - Forklaring til høyre: SVELL FRA / VIND FRA / VINDU.
9. **Kilder** i ett avsnitt i muted.

### C. Web, spotside (`5-web-spot.png`, kilde `kilde/B4-web.dc.html`)

1. **Topp:** logo, HJEM / UTFORSK / LOGGER, søkefelt med 2 px understrek og knappen «MØRKETID».
2. **Kornfoto 420 px** med navneplate i 144 px som overlapper med 64 px.
3. **12-kolonners rutenett:**
   - Dom i kolonne 1–5.
   - KL. hh i kolonne 7–9, med svellhøyde i 96 px.
   - Skive på 300 px i kolonne 10–12.
4. **NESTE 7 DAGER:**
   - 7 kolonner med store tall (48 px), ord, beste vindu og svell.
   - Valgt dag har en 4 px ink-strek over seg, de andre har hair.
5. **TIME FOR TIME:**
   - Tabell for 06–19 med etikettkolonne på 144 px.
   - Rader: KL / VURDERING / SVELL m (stolper i outline-farge) / SVELL FRA / VIND / TIDEVANN.
   - Hold musa over en time for å velge den.
6. **SPOTTEN:**
   - Kartfigur med svellvindu, fralandssektor, svellpil og TOPP.
   - Bildetekst: «FIG. 1 · UNSTAD, NORD OPP. Flyfoto: …».
   - Ved siden av: OM SPOTTEN-liste.
7. **Bunn:** seksjonsstrek, logo, kilder og lenker.

### D. Web, forside «Beste i dag» (het «Beste nå» i skissa, `6-web-forside.png`, kilde `kilde/B4-hjem-web.dc.html`)

1. **Datolinje og overskrift** (60/64), som må stemme med tabellen.
2. **Filtre:** I DAG / I MORGEN (segmentert, aktiv er fylt ink) og regioner som tekstfaner med 3 px understrek.
3. **Hovedbilde 1296 × 440** med papirplate:
   - «01 · BEST I DAG · …», spotnavnet i 120 px, tall, ord, svell og «BEST 10–13».
   - BEST-vinduet har en håndtegnet korall-ring rundt seg. Det er det eneste håndtegnede elementet i hele produktet.
4. **BESTE NÅ:** tabell med #, SPOT (navn + region · kjøretid), I DAG (tall + ord + grunn), BEST, SVELL og 06–18.
5. **NESTE 7 DAGER, matrise uten bokser:**
   - Tall fra 4 og opp: 48 px korall.
   - Tallet 3: 30 px ink.
   - 0–2: 18 px muted.

## 7. Bilder: «Trykk» om dagen, «Lodd» i mørketid

Theodor liker kornet godt, og det skal beholdes som det er. Behandlingen er beskrevet i `foto/behandle.py` (blå) og `foto/trykk.py` (varm):

1. Gjør bildet om til gråtone.
2. Strekk mellom 1. og 99. persentil, med gamma 0,85.
3. Legg på korn FØR fargekartet: sigma 0,06–0,07. Partikkelstørrelsen er 1,6–2,5, og kornet skaleres opp bilineært. Det er dette som gir «film»-kornet.
4. Legg på fargekart (rampe):
   - Dag «Trykk»: #1F2A30 → #5C5A53 (0,35) → #B9B2A4 (0,7) → #F2EFE8. Maks 0,93.
   - Mørketid «Lodd»: #00131F → #002941 (0,3) → #B6DFED (0,9) → #F2EFE8. Maks 0,82 i header, ellers 1,0.

Øvrige regler:
- Aldri korall i bilder, og aldri tekst rett på bilder. Bruk plater.
- Skissene bruker EOxCloudless (kun ikke-kommersielt). I appen skal bildene komme fra Kartverkets skyfrie Sentinel-2-mosaikk (CC BY 4.0) eller Theodors egne bilder og dronebilder.
- Norge i bilder/Geovekst kan vises, men ikke kopieres, committes eller precaches.
- Bildetekst med fotograf og kilde står under bildet, i Martian 10–11.

## 8. Tilgjengelighet og tekst

- Farge er aldri eneste bærer av mening. Tallene står i rutene, og grunnen står som tekst.
- VoiceOver-etiketter finnes i malene: skiva, timestripa, ukeoversikten og tidevannet. Ta dem med.
- Tekst i appen er på norsk. Enheter skrives med små bokstaver (1,7 m · 12 s · 5 m/s).
- Vinden beskrives som fralands, pålands, skrått pålands eller sidevind, med de samme ordene i «Hvorfor» (S42 b, svar.md 24.11.2026 kl. 22.25).
- Ingen pseudo-presise ord («MODELL 00Z» bare under Data/Kilder).
- Overskrifter og setninger lages av dataene og skal aldri si noe som lista motsier.

## 9. Endringer etter designrevisjonen 21.11.2026

Fase 1 (24.11.2026, plan i `privat/designrevisjon-2026-11-21/PLAN.md`). Der dette avsnittet og resten av fila spriker, gjelder dette.

- **Toppbildet er kortere.** Mobil 160 px (§6B sa 220). Web 260 px (§6C sa 420), og spotnavnet på web er 96/84 (§3 sa 144/124). Dommen skal stå i første skjermbilde.
- **Under toppbildet står én linje:** «Sentinel-2 · Copernicus/Kartverket · CC BY 4.0», med lisensen som lenke (44 px trykkflate). Hele krediteringen står under Kilder nederst.
- **Fyllet for 1 og 2** er et eget token, `--lav`: #8A8478 om dagen (3,24:1 mot papiret) og #8FA0A8 i mørketid (5,57:1). Før var det outline-fargen (1,83:1). Tallet oppå fyllet er `--paa-lav`.
- **Nullene** står i muted med vekt 500 og tynn ramme (hair). Aldri strek, for strek betyr «mangler».
- **Ringen rundt «Best»** på forsiden tegnes bare når dagen har 4 eller 5, i korall. Ellers ren tekst.
- **Etiketter** er 12/16 også på mobil (§3 sa 11/14), med sperring 0,02 em (§3 sa 0,04). 11 px brukes bare til kreditt.
- **Faktalinja** (LYS, LUFT, VANN) og datoene i dagvelgeren står i ink.
- **«Hvorfor»** er en tabell med etikett, verdi og virkning, og sier «poeng», ikke «stjerner».
- **Dag 8 og utover** på web-spotsiden har etiketten «UKE 2 · USIKKER» og stiplede ruter.
- **I mørketid** har toppbildene en 1 px kant i hair.
- **Desimalkommaet** i store mono-tall står i `.des`, som trekker sifrene sammen.

Fase 2 (24.11.2026, «B 4.0 ferdig på mobil»). Der dette avsnittet og resten av fila spriker, gjelder dette.

- **Topplinja på mobil-Hjem (§6A punkt 1)** har to linjer: ordmerket (21 px høyt) til venstre og «FRA TROMSØ» med en vinkel ned til høyre, og datoen og lyset på linja under. «FRA TROMSØ» åpner Innstillinger, der området velges. Startstedet kan ikke byttes der ennå.
- **Under favorittene på mobil-Hjem** står «SPOTS I <REGION>» (§6A har bare favoritter): regionene som tekstfaner med 3 px strek under den valgte, og spotene som favorittraden uten setning. Radene står etter dagens tall, så kjøretid.
- **Er dagens lys over** for spotene mobil-Hjem viser, viser radene i morgen, og over lista står én linje: «Mørkt nå. Tallene gjelder i morgen.»
- **Fanelinja (§6A punkt 5)** har fire faner: HJEM, UTFORSK, LOGGER og SØK. Den valgte er fet med 3 px blekkstrek under ordet. Ikonene er ikke fylt for den valgte.
- **Én knappefamilie (§4):** primær er massiv blekk, sekundær har 2 px blekk-kant, begge med rette hjørner og Martian i versaler. Valg av én (dag og utsnitt på Utforsk, størrelse og vind i loggarket) er brikker i samme form, og den valgte er fylt. Regioner er tekstfaner.
- **Valgt** er 3 px blekkstrek under for faner og dager, også i «Neste 7 dager» på web (§6C punkt 4 sa 4 px over). Segmentet I DAG / I MORGEN og brikkene er fortsatt fylt når de er valgt (§6D punkt 2).
- **Tilstander:** musa over toner flaten (`--hover`) eller gir 1 px strek under tekstknapper og faner. Trykk toner sterkere (`--trykk`). Den fylte knappen snus når musa er over. Fokus er én ring, 2 px blekk med 2 px luft.
- **Dagvelgeren på mobil-spotsiden (§6B)** står under krediteringslinja og over dommen, ikke under «Time for time» (§6B punkt 7). Den blir stående øverst når siden rulles, med 0,75 px blekkstrek under.
- **Listeraden** i Søk, Utforsk og lista utenfor kartet: tallet i ruta, NAVN i Martian, stedet som etikett og ordet til høyre. Ingen streker mellom radene på mobil (regel 6), 1 px hair på web.
- **Flaten over kartet** for valgt spot på Utforsk starter med seksjonsstreken og går kant til kant. Den har ingen ramme.
- **Skjemafelt** (Innstillinger, loggarket) har 2 px blekkstrek under, som søkefeltet, og ingen boks.
- **Tidevannsregelen på mobil-spotsiden:** en kort setning på egen linje under TIDEVANN-raden i KL.-blokka («Best på lav til middels vannstand»). Spots uten regel har ingen linje.
- **Ikonet** (`docs/icon.svg` og PNG-ene i `docs/icons/`) bruker tokenene #F2EFE8 og #002941.
- **Lave skjermer (under 700 px i høyden) på mobil-spotsiden:** luften mellom dom, faktalinje og KL.-blokk er 4, 8 og 16 px, og setningen under dommen er 16/22 (§3 sier 16–18/22–26). Da får dag, dom og time plass over fanelinja etter dagbytte på 360 × 640 og 390 × 663. Høyere skjermer har luften fra §6B.
- **Nedtrekkslister** tegnes av appen (44 px, 2 px strek under, vinkel i blekk), ikke med nettleserens egen form.
- **Metalinja i radene på mobil-Hjem** er «STED · FORELØPIG · KJØRETID · ORD · −N ÅRSAK» (§6A sier «REGION · KJØRETID · ORD · −N ÅRSAK»): merkene «Foreløpig» og forbudet står etter stedet, i favorittene og i regionradene. Linja brytes bare mellom leddene.
- **Regionradene på mobil-Hjem har «Nå» sist i metalinja** (S38 1 b, svar.md 24.11.2026 kl. 22.25): «STED · FORELØPIG · KJØRETID · NÅ ORD HØYDE», for eksempel «Kvaløya · ca. 45 min · Nå Smått 0,6–0,8 m». Ordet og høyden gjelder nå-timen, tallet til venstre er dagens. Er nå-timen mørk, står «Nå Mørkt» uten tall. Leddet erstatter dagens ord og «−N årsak» i regionradene. Favorittradene er som før. Viser lista i morgen («Mørkt nå. Tallene gjelder i morgen.» over lista), står dagens ord uten «Nå».
