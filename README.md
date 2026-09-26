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
detaljsiden og på høydeplata på kartet som "Sett opp til X m". Den brukes
**aldri** i rangeringen eller kalibreringen - begge bygger på signifikant
høyde (`bw_height`), som er det eneste målet som er sammenlignbart mellom
BarentsWatch, Open-Meteo og loggene dine.

Etter `bw_until`, og for spots uten BarentsWatch i det hele tatt, brukes
reservemodellen:
1. Bare svellet ute fra Open-Meteo (uten vindsjø), ganget med spotens
   `transfer` og hvor direkte svellet treffer spoten (se under).
2. Reserve: total bølgehøyde fra met.no på spoten, med dreiningsregelen.

Horisonten er normalt 120 timer (5 døgn), men stopper ved hvilken som helst
kilde som har kortere data (Open-Meteo eller met.no vind) - det står i
kilderapporten som "Horisont: X timer" per spot.

### Periode: lang periode bygger seg høyere opp

Langt svell (lang periode) bygger seg høyere opp når det treffer grunnen enn
kort svell med samme signifikante høyde ute. Ranger derfor rangeringen
(`height_score`) mot en **effektiv høyde**: `høyde × periodefaktor`.

| Periode | Periodefaktor |
|---|---|
| 8 s eller kortere | 0,9 |
| 10 s | 1,0 |
| 13 s | 1,15 |
| 16 s eller lengre | 1,3 |

(Lineær interpolasjon mellom punktene.) Dette er **bare** til rangeringen -
høyden du ser i appen, og høyden kalibreringen (`transfer` mot BarentsWatch
og loggene dine) læres mot, er fortsatt den ekte signifikante høyden,
urørt av periodefaktoren. Perioden straffer dermed ikke lenger dobbelt:
`period_score` (i selve stjerneregnestykket) er gjort mildere og straffer nå
bare KORT periode, ikke lenger ekstra uttelling for lang periode - den jobben
gjør periodefaktoren i stedet.

`transfer` er hvor stor del av svellet ute som når stranda ved et **direkte**
treff (rett inn i midten av svellvinduet). Den læres i denne rekkefølgen:
1. Fra loggene dine (Logg størrelse på øktene, minst 5 med størrelse valgt)
2. Automatisk fra BarentsWatch (se under)
3. Verdien satt i `spots.json`, f.eks. `"transfer": 0.42`
4. Standardverdien 0,6

Bare det første treffet i rekkefølgen brukes - Logger-fanen viser hvilken
kilde som gjelder for hver spot akkurat nå.

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
presist for en surfespot uten mye mer detaljerte data. Loggene dine justerer
bare `transfer` (toppfaktoren ved direkte treff), aldri selve kurven.

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
høyde (med "føles som" hvis periodefaktoren gjør en reell forskjell),
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
om varselet over- eller undervurderer. Juster `ideal_height`, `swell_window` og
`offshore_wind` ut fra det, og kjør `python fetcher/test_rating.py` for å sjekke at
de kjente dagene fortsatt blir riktige. `transfer` trenger du normalt ikke justere selv
lenger - se "Automatisk kalibrering mot BarentsWatch" over.

## Varsler og BarentsWatch

Spots med BarentsWatch varsler bare på timer der høyden faktisk kommer fra BarentsWatch
(ekte eller interpolerte punkter) - aldri på reservemodellen etter `bw_until`, den er
for usikker til å sende varsel på. Spots uten BarentsWatch varsler som før, på alle timene.

## Ting jeg ikke har kunnet teste

Sandkassen jeg bygde dette i har ikke nettilgang til værtjenestene. Ratingen, appen og
eksempeldata er testet. Selve API-kallene er skrevet etter dokumentasjonen, men første
ekte kjøring i Actions er den reelle testen. Feiler en kilde, fortsetter resten, og
feilen står i loggen til Actions-kjøringen.
