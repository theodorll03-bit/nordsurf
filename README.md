# Nordsurf V1

Surfevarsel for Nord-Norge med ærlige stjerner i Magicseaweed-stil.
Hele stjerner = hvor bra det blir. Stiplede stjerner = det vinden tar fra deg.

## Slik henger det sammen

- `spots.json` – spotene dine: koordinater, svellvindu, offshorevind, ideell høyde
- `fetcher/` – Python som henter data og regner ut stjerner
  - `sources.py` – met.no, Open-Meteo, Kartverket, BarentsWatch
  - `rating.py` – ratingen, inkludert dreiningsregelen din
  - `test_rating.py` – sjekker ratingen mot det du faktisk har sett (Grøtfjord 24.09 osv.)
  - `fetch.py` – kjører alt og skriver `docs/data/forecast.json`
- `docs/` – selve appen. GitHub Pages serverer denne mappa
- `.github/workflows/forecast.yml` – henter nytt varsel hver tredje time, gratis

Loggene lagres på telefonen og synkes til et privat GitHub-repo (steg 5).

## Oppsett, i små steg

**Steg 1: Repo (10 min)**
1. Lag en gratis GitHub-konto og et nytt repo, f.eks. `nordsurf`
2. Last opp alle filene i denne mappa (dra og slipp i nettleseren går fint)

**Steg 2: Kontaktinfo til met.no (2 min)**
met.no krever at du sier hvem du er.
Settings → Secrets and variables → Actions → New repository secret:
- `UA_CONTACT` = e-posten din

**Steg 3: Skru på appen (5 min)**
1. Settings → Pages → Source: "Deploy from a branch", branch `main`, mappe `/docs`
2. Actions-fanen → "Hent varsel" → "Run workflow"
3. Etter et par minutter ligger appen på `https://<brukernavn>.github.io/nordsurf/`
4. Åpne i Safari → Del → "Legg til på Hjem-skjerm"

**Steg 4: BarentsWatch (15 min, kan tas senere)**
1. Lag bruker på barentswatch.no/minside og registrer en API-klient (type API)
2. Legg inn secrets `BW_CLIENT_ID` og `BW_CLIENT_SECRET`
3. Åpne "Waveforecast OpenAPI doc" fra developer.barentswatch.no/docs/waveforecast,
   finn endepunktet for punktvarsel og legg det inn som secret `BW_POINT_URL`,
   med `{lat}` og `{lon}` der koordinatene skal stå
4. Innloggingen er ferdig kodet. Selve svarformatet fra punktendepunktet har jeg ikke
   fått sett ennå, så send meg et eksempelsvar første gang, så låser vi parseren

Til BarentsWatch er på plass brukes met.no med dreiningsregelen. Den ga 0,28 m for
Grøtfjord 24.09, mot 0,3 m fra BarentsWatch, så den er et godt fallback.

**Steg 5: Sikkerhetskopi av logger (10 min, gjør dette tidlig)**
1. Lag et nytt **privat** repo, f.eks. `nordsurf-logger`. Det skal være privat, fordi loggene viser når og hvor du surfer
2. Lag en fine-grained token: GitHub → Settings → Developer settings → Fine-grained tokens.
   Gi den bare tilgang til `nordsurf-logger`, med Contents: Read and write
3. I appen: Innstillinger → Sikkerhetskopi. Skriv `brukernavn/nordsurf-logger` og lim inn tokenet
4. Legg samme repo og token inn som secrets `LOGS_REPO` og `LOGS_TOKEN` i nordsurf-repoet.
   Da lærer varselet av loggene automatisk hver tredje time

Tokenet ligger bare på telefonen din og i GitHub-secrets. Gi det utløpsdato og bytt det av og til.

**Steg 6: Varsler (5 min)**
1. Installer ntfy-appen (gratis, iPhone og Android)
2. Finn på et langt, hemmelig emnenavn, f.eks. `nordsurf-theodor-8k2p9x`. Alle som kjenner navnet kan lese varslene
3. Abonner på emnet i ntfy-appen
4. Legg samme navn inn som secret `NTFY_TOPIC`, og appens adresse som `APP_URL`
5. Juster grensen i `notify.json`: `min_stars` (standard 3), `hours_ahead` (standard 36), og eventuelt hvilke spots

Du får ett varsel per spot per dag, og et nytt bare hvis det blir bedre.

## Første kjøring

Etter hver kjøring står det en **kilderapport** nederst i Actions-kjøringen: hver kilde for hver spot,
med ok, tom eller feil, samt "BarentsWatch periode" (første/siste tidspunkt og `bw_until`) og
"Horisont" (hvor mange timer frem denne kjøringen faktisk dekker). Se særlig etter:
- "Open-Meteo svellhøyde: tom". Da har havpunktet ingen svelldata, og spoten faller tilbake til met.no
- "Kartverket tidevann: feil". Da virker ikke tidevannet
- "BarentsWatch (250 m)" eller "BarentsWatch (150 m)": "feil" eller "tom"
- "BarentsWatch 250 m: feil - ingen data - bruker 150 m-punktet i ratingen for dette spotet". Selve ratingen fungerer fortsatt (150 m-punktet brukes), men verdt å sjekke om 250 m-punktet ligger på land eller utenfor dekningen

Send meg rapporten, så fikser vi det som feiler.

## Nye spots

Tegn svellvinduet, og sjekk det med:

    pip install basemap basemap-data-hires shapely
    python fetcher/check_spot.py <lat> <lon> <fra_grad> <til_grad>

Verktøyet finner hvilke retninger i vinduet som har rett, fri linje til åpent hav uten øyer
eller odder i veien, og foreslår et havpunkt med minst 10 km åpent hav rundt seg.
Kystlinja er GSHHS i full oppløsning. Små skjær kan mangle, så sjekk trange gap selv.

## Bølgehøyde

BarentsWatch er hovedkilden når den er koblet på: den har sin egen finmaskede
kystmodell som allerede tar hensyn til skjerming bak odder og øyer, og brukes
**uten** noen faktor. Hver spot har to BarentsWatch-punkter i `spots.json`:
- `barentswatch_point` (ca 250 m ut fra stranda) - dette er punktet ratingen
  og kalibreringen faktisk bruker (`bw_height` i timedataene).
- `barentswatch_point_near` (ca 150 m ut, det opprinnelige punktet) - hentes
  også, men bare til sammenligning (`bw_height_near`). Brukes ALDRI i
  ratingen. Logger-fanen viser, når du har logget minst 5 økter med størrelse
  for en spot, hvilket av de to punktene som faktisk lå nærmest det du
  observerte (gjennomsnittlig avvik i meter) - punktet byttes aldri
  automatisk, det er bare til orientering.

Gir 250 m-punktet ingen data en gitt kjøring, faller henteren tilbake til
150 m-punktet for RATINGEN også (for det spotet, den kjøringen) - det logges
som egen linje i kilderapporten.

BarentsWatch kommer i tretimerssteg (ca 58-60 timer
frem) - henteren fyller inn hver time i mellom med interpolasjon (rett linje
for høyde og periode, korteste vei rundt kompasset for retning), men
ekstrapolerer aldri forbi siste ekte punkt. Hver spot har et felt `bw_until`
i `forecast.json`: siste time med ekte BarentsWatch-data. I appen vises
timene etter det bruddet nedtonet, med "(anslag)" på beste vindu hvis det
treffer der.

### Maks bølgehøyde

Når BarentsWatch-svaret har feltet `expectedMaximumWaveHeight` (bekreftet
mot BarentsWatch sin OpenAPI-spec for `/v1/waveforecastpoint/nearest/all`,
schema `BwRasterWavePoint`), lagres den som `bw_height_max` og vises på
detaljsiden og på høydeplata på kartet som "BarentsWatch venter opp til
X m". Den brukes **aldri** i rangeringen eller kalibreringen - begge bygger
på signifikant høyde (`bw_height`), som er det eneste målet som er
sammenlignbart mellom BarentsWatch, Open-Meteo og loggene dine. Dette er
BarentsWatch sitt EGET, uavhengige maks-anslag - ikke det samme som
`surf_height_sets` (1,27 × surfehøyde, se "Surfehøyde" under), som er
appens egen, formelbaserte anslag på settene. Begge vises der de er
relevante, til sammenligning.

### Ekte svell fra vindsjø, og retning ved spoten

`totalSignificantWaveHeight` fra BarentsWatch er **total** bølgehøyde ute -
svell og vindsjø slått sammen, uten skille. Høy totalhøyde kan altså komme
fra ren vindsjø, som ikke oppfører seg som surfbare bølger og som ikke
nødvendigvis går inn mot akkurat denne stranda. Henteren regner derfor ut,
for hver time BarentsWatch brukes, hvor mye av totalhøyden som trolig er
ekte svell, og om det svellet faktisk er på vei inn mot spoten:

- **Svellandel** `swell_share = svell_offshore / høyde_offshore` (fra
  Open-Meteo, samme punkt som resten av retningslogikken), avgrenset til
  0,2-1,0. Ukjent (mangler en av verdiene) gir 1,0, altså ingen straff.
- **BarentsWatch-periodefaktor**, fra `totalPeakPeriod` (bekreftet
  toppperiode, ikke middelperiode, direkte fra feltnavnet i BarentsWatch sin
  OpenAPI-spec - trenger derfor ingen justering av terskler):

  | Toppperiode | Faktor |
  |---|---|
  | Under 6 s | 0,3 |
  | 6-8 s | lineær 0,3 → 1,0 |
  | 8 s eller mer | 1,0 |

  Ukjent periode gir 1,0.
- Disse to slås sammen med **minimum**, ikke produkt - begge er uavhengige
  signaler på "er dette vindsjø", og skal ikke straffe samme ting to ganger.
- **Retning ved spoten**: BarentsWatch sin `totalMeanWaveDirection` oppgis
  som "mot" (bekreftet empirisk mot ekte data fra Open-Meteo GFS Wave, median
  vinkelavvik 137-149° - se `fetcher/diagnose_bw_direction.py` og
  `.github/workflows/diagnose_bw.yml` for selve målingen), og gjøres om til
  "fra" med `(retning + 180) % 360` før den sammenlignes med spotens felt
  `facing` i `spots.json` (grader, normalen rett ut fra stranda):

  | Vinkel mellom bølgeretning og `facing` | Retningsfaktor |
  |---|---|
  | 0-30° | 1,0 |
  | 30-60° | lineær 1,0 → 0,3 |
  | over 60° | 0 |

  Mangler retning fra BarentsWatch settes faktoren til 1,0, men timen merkes
  usikker (`uncertain`).

Høyden BarentsWatch faktisk bidrar med er
`bw_height × min(svellandel, periodefaktor) × retningsfaktor`. Reservemodellen
(svell ute × transfer × retningstreff) er upåvirket av dette - endringen
gjelder bare når BarentsWatch er kilden.

### Kilder uenige (`sources_disagree`)

Når BarentsWatch viser minst 0,5 m, men minst ett av tegnene over sier
"dette er nok ikke ekte surfbart svell mot akkurat denne stranda" -
retningstreff ute under 67 %, svellandel under 50 %, eller retningsfaktor
ved spoten under 50 % - settes `sources_disagree` til sann for timen.
Ratingen kappes da til maks 1 stjerne (strengere enn den vanlige
usikkerhetskappingen på 3 stjerner), og timen merkes usikker. Detaljsiden
viser en advarsel øverst med årsaken, og lista/kommende dager kan aldri
velge en slik time som "beste time" for dagen hvis det finnes andre timer
uten konflikt. `notify.py` sender aldri varsel for disse timene, og
kalibreringen mot BarentsWatch (`bw_pairs_for_run()`) hopper over dem, samt
alle timer med retningsfaktor under 0,7. Logger-fanen viser, per spot, hvor
mange av disse timene som faktisk ble logget som surfbare (2 stjerner eller
mer) - mange treff der er et tegn på at regelen er for streng.

`likely_flat` (under 0,35 m) er upåvirket av alt dette og gjelder uansett
kilde.

Etter `bw_until`, og for spots uten BarentsWatch i det hele tatt, brukes
reservemodellen:
1. Bare svellet ute fra Open-Meteo (uten vindsjø), ganget med spotens
   `transfer` og hvor direkte svellet treffer spoten (se under).
2. Reserve: total bølgehøyde fra met.no på spoten, med dreiningsregelen.

Horisonten er normalt 120 timer (5 døgn), men stopper ved hvilken som helst
kilde som har kortere data (Open-Meteo eller met.no vind) - det står i
kilderapporten som "Horisont: X timer" per spot.

### Surfehøyde

26.09.2026: appen viser nå **surfehøyde** (høyden der bølgene brekker), ikke
**Hs** (signifikant høyde, gjennomsnittet ute i vannet før bølgene treffer
grunnen). Bakgrunnen var en konkret observasjon: appen viste 0,9 m/15 s for
Unstad mens video fra Lofoten Surfsenter samme time viste bølger godt over
hodet, tønner og offshore-sprøyt. 0,9 m var ikke feil - det var riktig Hs -
men Hs er ikke det man ser eller logger fra stranda. Langt svell reiser seg
mye mer enn kort svell med samme Hs når det treffer grunt vann.

Formelen (Komar og Gaughan, 1972), for høyden der bølgene brekker:

    Hb = 0,39 × g^(1/5) × (T × H²)^(2/5)

der H er Hs ved spoten (etter alle justeringer: BarentsWatch med svellandel
og retningsfaktor, eller reservemodellen) og T er svellets periode **ute**
(Open-Meteo sitt `swell_wave_period`, IKKE BarentsWatch sin periode ved
spoten - se under). Settene (de største bølgene man venter på) er ca 1,27 ×
Hb. Formelen er **empirisk og laget for rette, jevne sandstrender** -
pointbreak og revbrekk kan avvike, derfor læres `surf_factor` per spot fra
loggene dine (se under), i stedet for å stole blindt på formelen alene.

**Perioden er gjennomsnittsperiode, ikke toppperiode.** Open-Meteo sin
`swell_wave_peak_period` finnes i API-et, men GFS Wave (modellen appen
bruker for selve svellet, se under) returnerer ingen verdi for det feltet -
bare `swell_wave_period` (gjennomsnitt) er tilgjengelig for den modellen.
Gjennomsnittsperiode er typisk ca 80 % av toppperioden, og formelen har T
opphøyd i 0,4 - det gir omtrent 9 % lavere Hb enn med ekte toppperiode. Det
er akseptabelt: feilen er jevn (samme retning hver gang), og `surf_factor`
lærer den bort per spot fra loggene dine. Høyde, retning og periode for
svellet kommer alltid fra samme modell (GFS Wave) - aldri blandet med en
annen modell, selv om den skulle gi topperiode, siden de kan beskrive
forskjellige svell.

**BarentsWatch sin egen periode ved spoten** (`totalPeakPeriod`) brukes
**ikke** i formelen - den var 10,5 s ved Unstad mens svellet ute var 15 s,
trolig fordi et kystpunkt også fanger opp lokal småsjø. Den beholdes bare
som informasjon og i vindsjø-sjekken (`bw_period_factor`, se over).

**Demping for svell i kanten av eller utenfor vinduet.** Komar og Gaughan
sin formel er laget for åpen kyst og vet ikke om svellet har bøyd seg rundt
en odde (diffraksjon) - et slikt svell har bredere retningsspredning og
mindre samlet energi, og bygger seg ikke opp som et rent svell. Uten
demping ga formelen 3 stjerner for Grøtfjord 25.09.2026 (svell 3 grader
utenfor vinduet, observert helt flatt). Bruddhøyden (Hb) dempes derfor med
samme `directness` som allerede reduserer Hs for `svell_ute` - godt
innenfor vinduet (directness 1,0) endres ingenting.

**Flat-sperre.** Under 0,35 m Hs ved spoten er det uansett flatt i praksis -
formelen gjør små bølger urealistisk store ved lang periode (0,3 m/11 s gir
Hb ca 0,6 m), og Grøtfjord var helt flatt tre dager på rad (24.-26.09.2026)
med rundt 0,3 m fra BarentsWatch. Under grensen settes surfehøyden til 0 og
stjernene til 0, uansett hva formelen ellers ville gitt.

**`ideal_height` og `max_height` i `spots.json` er nå surfehøyde**, ikke Hs.
Tromsø-spotene beholder samme tall som før ([0,8, 2,0] / 3,5 m) - bare
tolkningen er ny. Unstad er justert opp ([1,5, 3,5] / 5,5 m, tåler mer).

#### `surf_factor`: lært fra loggene og observasjonene dine

`surf_factor` er hvor godt formelen stemmer med det du faktisk ser på denne
spesifikke spoten - `surfehøyde = Hb × surf_factor`. Læres som medianen av
`(logget størrelse i meter) / Hb` på loggtidspunktet, avgrenset til
0,5-1,6, standardverdi 1,0 til det finnes minst 5 logger. Bare logger der
Hs ved spoten var minst 0,35 m (uten det kan ikke Hb regnes ut) og
`directness` var minst 0,667 (retning godt innenfor vinduet - ellers ville
en logg fra feil retning feilaktig lære ned faktoren for hele spoten, se
demping over) telles med. Observasjoner (se "Loggetyper" under) teller likt
som egne økter.

Dette er en **egen, adskilt** læring fra `transfer` (se under) - de to skal
ikke blandes, siden de måler forskjellige ting (surfehøyde mot det du ser,
versus Hs mot Hs). `transfer` læres derfor **ikke lenger** fra loggene dine:

1. Automatisk fra BarentsWatch (se under)
2. Verdien satt i `spots.json`, f.eks. `"transfer": 0.42`
3. Standardverdien 0,6

Logger-fanen viser begge tallene per spot, med kilde.

#### Loggetyper: egen økt eller observasjon

Loggearket har et valg øverst: **Egen økt** (du surfet selv) eller
**Observert** (du så forholdene selv, eller via en pålitelig kilde, uten å
surfe - f.eks. en video fra et surfesenter). Observasjoner kan ha et
valgfritt **kilde**-felt (f.eks. "Instagram, Lofoten Surfsenter"), og teller
likt som egne økter i `surf_factor`, stjerne-bias og tidevann.

#### Størrelser

| Størrelse | Surfehøyde |
|---|---|
| Flatt | 0 m |
| Knehøy | 0,5 m |
| Hoftehøy | 0,9 m |
| Brysthøy | 1,3 m |
| Hodehøy | 1,8 m |
| Over hodet | 2,4 m |
| Dobbelt over hodet | 3,6 m |

26.09.2026: Hodehøy og Dobbelt over hodet er nye, Over hodet endret fra
2,0 til 2,4 m. Gamle logger beholder etiketten sin, men får den nye
meterverdien. Samme tabell i `docs/index.html` og `fetcher/calibrate.py` -
`test_pipeline.py` sjekker at de er like (ingen bundler til å dele en
felles fil mellom app og henter).

### Automatisk kalibrering mot BarentsWatch

For spots med BarentsWatch bygger henteren, ved hver kjøring, et forhold
`bw_height / (svell_ute × directness)` for hver time der svellet ute klart
dominerer bildet (minst 0,3 m, retningstreff minst 0,3, og svellet er minst
70 % av total bølgehøyde ute) - bare ekte, ikke interpolerte, BarentsWatch-
timer telles. Disse forholdene lagres i `data/bw_calibration.json` (ett
tidsstemplet par per time, forkastes etter 30 døgn). Når det finnes minst 40
par spredt over minst 3 forskjellige døgn, brukes medianen (avgrenset til
0,05-1,2) som `transfer` for reservemodellen, helt uavhengig av loggene dine.
Dette gir en fornuftig faktor selv for spots du aldri har logget økter på.

### Retning: skyggen bak odder og øyer

De fleste spotene ligger i le av en odde eller en øy, og svellet må bøye seg
(diffraksjon) for å nå stranda når det ikke treffer rett i svellvinduet.
Jo lenger fra vinduet, jo mindre høyde blir det igjen, og fallet er raskest
rett utenfor kanten:

| Retning | Andel av høyden ved direkte treff | Høyde med transfer 0,6 |
|---|---|---|
| Godt innenfor vinduet (5° eller mer fra kanten) | 100 % | 0,6 |
| Akkurat på kanten | 67 % | 0,4 |
| 5° utenfor | 33 % | 0,2 |
| 10° utenfor | 17 % | 0,1 |
| 20° utenfor | 5 % | 0,03 |
| 30° eller mer utenfor | 0 % | 0 |

Kantverdien (67 %) bygger på kystteknikk: langs skyggegrensen bak en odde er
bølgehøyden omtrent 70 % av høyden ute for uregelmessige bølger fra flere
retninger. Resten av kurven er et anslag - diffraksjon kan ikke beregnes
presist for en surfespot uten mye mer detaljerte data. Denne kurven (og
`transfer`) læres aldri fra loggene - se "Surfehøyde" over for hva loggene
dine faktisk lærer (`surf_factor`).

## Vind

Vindtype settes ut fra vinkelen mellom vindretningen og midten av spotens
`offshore_wind`-sektor:

| Vinkel fra offshore-sentrum | Type |
|---|---|
| 0-45° | offshore |
| 45-100° | side (sidevind) |
| 100-135° | side-onshore |
| 135-180° | onshore |

Kast som er kraftigere enn middelvinden teller med: **effektiv vind**
`= vind + 0,3 × (kast − vind)` når kast > vind, ellers bare middelvinden.
4 m/s med kast 12 m/s gir altså effektiv vind 6,4 m/s.

Straffen (i stjerner) etter effektiv vind og type:

| Effektiv vind | offshore | side | side-onshore | onshore |
|---|---|---|---|---|
| 0-3 m/s | 0 | 0 | 0 | 0 |
| 3-5 m/s | 0 | 0 | −1 | −1 |
| 5-8 m/s | 0 | −1 | −1 | −2 |
| 8-11 m/s | 0 (−1 over 10) | −2 | −2 | −3 |
| over 11 m/s | −1 (−2 over 14) | −3 | −3 | −4 |

Straffen kan aldri bli større enn stjernene svellet i seg selv er verdt.
Under 1,5 m/s vises teksten "blankt", 1,5-3 m/s "nesten blankt", ellers
vindtypen.

## Forklaring av ratingen

Trykk på stjernene på detaljsiden (eller på ratingringen i kart-arket) for å
åpne en forklaring av hvert ledd som påvirket ratingen for den valgte timen:
signifikant høyde, bruddhøyde (Hb) og surf-faktor (bare for BarentsWatch:
også svellandel, BarentsWatch-periode og retning ved spoten), surfehøyde,
periode, retning, vind og tidevann, samt totalen og hvor mange stjerner det
ville blitt uten vind. `rate()` i `fetcher/rating.py` returnerer dette som
et eget felt `breakdown` (en liste med ferdigformaterte linjer) - appen viser
bare det henteren faktisk regnet ut, den regner ikke selv.

## Tidevann per spot

Sett hvilke tidevann spoten liker i `spots.json`, f.eks. `"tide": ["lav", "middels"]`.
Utenfor det mister spoten én stjerne (endres med `"tide_penalty": 2`). Uten `tide` tåler spoten alt.

## Lys og mørketid

Appen bruker brukbart lys, altså fra borgerlig tussmørke om morgenen til tussmørke om kvelden.
I mørketida finnes det fortsatt noen timer rundt middag, og appen finner vinduer der.
Solhøyden regnes ut lokalt, uten eksterne kall.

## Kalibrering

Verdiene i `spots.json` er startverdier. Etter 10–15 logger per spot viser Logger-fanen
om varselet over- eller undervurderer. Juster `ideal_height` (surfehøyde, ikke Hs -
se "Surfehøyde" over), `swell_window` og `offshore_wind` ut fra det, og kjør
`python fetcher/test_rating.py` for å sjekke at de kjente dagene fortsatt blir riktige.
`transfer` trenger du normalt ikke justere selv lenger - se "Automatisk kalibrering mot
BarentsWatch" over. `surf_factor` justerer du heller ikke selv - den læres automatisk
fra loggene og observasjonene dine.

## Varsler og BarentsWatch

Spots med BarentsWatch varsler bare på timer der høyden faktisk kommer fra BarentsWatch
(ekte eller interpolerte punkter) - aldri på reservemodellen etter `bw_until`, den er
for usikker til å sende varsel på. Spots uten BarentsWatch varsler som før, på alle timene.

## Ting jeg ikke har kunnet teste

Sandkassen jeg bygde dette i har ikke nettilgang til værtjenestene. Ratingen, appen og
eksempeldata er testet. Selve API-kallene er skrevet etter dokumentasjonen, men første
ekte kjøring i Actions er den reelle testen. Feiler en kilde, fortsetter resten, og
feilen står i loggen til Actions-kjøringen.
