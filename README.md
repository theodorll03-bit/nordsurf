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
med ok, tom eller feil. Se særlig etter:
- "Open-Meteo svellhøyde: tom". Da har havpunktet ingen svelldata, og spoten faller tilbake til met.no
- "Kartverket tidevann: feil". Da virker ikke tidevannet
- "BarentsWatch: feil" eller "tom"

Send meg rapporten, så fikser vi det som feiler.

## Nye spots

Tegn svellvinduet, og sjekk det med:

    pip install basemap basemap-data-hires shapely
    python fetcher/check_spot.py <lat> <lon> <fra_grad> <til_grad>

Verktøyet finner hvilke retninger i vinduet som har rett, fri linje til åpent hav uten øyer
eller odder i veien, og foreslår et havpunkt med minst 10 km åpent hav rundt seg.
Kystlinja er GSHHS i full oppløsning. Små skjær kan mangle, så sjekk trange gap selv.

## Bølgehøyde

Høyden på spoten hentes slik, i rekkefølge:
1. BarentsWatch, når den er koblet på
2. Bare svellet ute fra Open-Meteo (uten vindsjø), ganget med spotens `transfer` og dreiningsregelen
3. Reserve: total bølgehøyde fra met.no på spoten, med dreiningsregelen

`transfer` er hvor stor del av svellet ute som faktisk når stranda. Starter på 0,7.
Logg størrelse på øktene dine, så regner Logger-fanen ut riktig verdi etter 5 økter.
Legg den inn i `spots.json`, f.eks. `"transfer": 0.42`.

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
de kjente dagene fortsatt blir riktige.

## Ting jeg ikke har kunnet teste

Sandkassen jeg bygde dette i har ikke nettilgang til værtjenestene. Ratingen, appen og
eksempeldata er testet. Selve API-kallene er skrevet etter dokumentasjonen, men første
ekte kjøring i Actions er den reelle testen. Feiler en kilde, fortsetter resten, og
feilen står i loggen til Actions-kjøringen.
