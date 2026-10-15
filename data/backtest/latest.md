# Testlab for treffsikkerhet - 2026-10-15 16:44 UTC

Saker: 15 (15 faste observasjoner, 0 logger, 0 benchmarks). WW3-arkiv: 395 spot-timer. Vindmålinger: 0 spot-timer.

## Forbehold: faste observasjoner er justeringsgrunnlag, ikke en uavhengig test

De 15 faste observasjonene (CLAUDE.md) er de samme sakene dagens rating er JUSTERT mot - surf_factor_prior for Unstad, offshore-sektoren, Nordneset-regelen og Unstads energiterskler ble satt for at nettopp disse skulle stemme. At grunnlinja holder alle sier derfor lite om nye dager; det sier bare at ingenting er ødelagt. Bare UAVHENGIGE saker (logger som er skrevet etter justeringene, og benchmarks) kan vise om en variant treffer bedre på nye dager. Uavhengige saker i denne kjøringen: 0 - INGEN, så tabellen 'Uavhengige saker' er tom og ingen variant kan vinne eller tape ennå.

## Uavhengige saker (logger og benchmarks) - det som teller for nye dager

| Variant | Evaluert | Faste obs. holder | Surfehøyde-feil (m, snitt) | Treff ±1 stjerne | Stjerneavvik (snitt, fortegn) | Benchmark-avvik (stjerner / m / kJ) | Grunnlinje på SAMME saker (holder / feil m / treff ±1) |
|---|---|---|---|---|---|---|---|
| grunnlinje | 0 | – | – | – | – | – | – |

## Faste observasjoner (justeringsgrunnlag - skal holde, beviser ingenting nytt)

| Variant | Evaluert | Faste obs. holder | Surfehøyde-feil (m, snitt) | Treff ±1 stjerne | Stjerneavvik (snitt, fortegn) | Benchmark-avvik (stjerner / m / kJ) | Grunnlinje på SAMME saker (holder / feil m / treff ±1) |
|---|---|---|---|---|---|---|---|
| grunnlinje | 15 | 15/15 | 0,05 (n=9) | 8/8 (100 %) | -0,38 (n=8) | – / – / – (n=0) | 15/15 / 0,05 / 8/8 |

Ikke evaluert per variant: grunnlinje 0

## grunnlinje - Dagens rating, uendret

| Sak | Forventet | Stjerner | Surfehøyde | Ord | Holder | Feil (m) | ±1 |
|---|---|---|---|---|---|---|---|
| Grøtfjord 24.09 (met.no 1,9 m) - helt flatt | stars_max=0, size_m=0.0 | 0 | 0,00 | flat | ja | 0,00 | – |
| Grøtfjord 24.09 (BarentsWatch 0,3 m) - helt flatt | stars_max=0, size_m=0.0 | 0 | 0,00 | flat | ja | 0,00 | – |
| Grøtfjord 24.09 kl. 09 (Windy 1,7 m fra 267°) - helt flatt | stars_max=0, size_m=0.0 | 0 | 0,10 | flat | ja | 0,10 | – |
| Grøtfjord 25.09 (3° utenfor vinduet) - helt flatt | stars_max=0, size_m=0.0 | 0 | 0,00 | treffer_ikke | ja | 0,00 | – |
| Grøtfjord 26.09 (BarentsWatch 0,33 m) - helt flatt | stars_max=0, size_m=0.0 | 0 | 0,00 | flat | ja | 0,00 | – |
| Lenangsøyra 26.09 - ikke surfbart (vindsjø på tvers) | stars_max=1 | 0 | 0,00 | blown_out | ja | – | – |
| Unstad 26.09 kl. 14:45 - over hodet, 4 stjerner | stars_min=3, surf_m=2.4, size_m=2.4, stars_obs=4 | 4 | 2,42 |  | ja | 0,02 | ja |
| Unstad 27.09 kl. 06 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 | 1,48 |  | ja | 0,07 | ja |
| Unstad 27.09 kl. 07 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 | 1,34 |  | ja | 0,21 | ja |
| Unstad 27.09 kl. 08 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 4 | 1,49 |  | ja | 0,06 | ja |
| Unstad 28.09 kl. 12 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 | 1,21 |  | ja | – | ja |
| Unstad 28.09 kl. 13 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 | 1,17 |  | ja | – | ja |
| Unstad 28.09 kl. 14 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 | 1,15 |  | ja | – | ja |
| Unstad 28.09 kl. 15 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 | 1,11 |  | ja | – | ja |
| Farstadsanden, svell fra 338° over Nordneset - treffer ikke | stars_max=1, low_reason=treffer_ikke | 0 | 1,28 | treffer_ikke | ja | – | – |

## Merknader

- Faste observasjoner har inndata rekonstruert fra ekte kjøringer (samme som test_rating.py). Logger bruker inndataene loggen selv lagret (uten vind/tidevann - merket [delvis]).
- Varianter som trenger WW3 eller vindmålinger for en time uten data hopper over saken (telles under 'Ikke evaluert'). Sammenlign bare varianter på samme saker.
- Saker merket retningsbundet (Grøtfjord 25.09 '3° utenfor vinduet', Farstadsanden 338° over Nordneset) tester en geometriregel for ÉN bestemt inndata-retning; variantene som bytter retningen mot WW3 hopper over dem (en annen modells retning gjør forventningen meningsløs, ikke feil). Syntetiske saker (tenkte inndata, Farstadsanden 338°) hoppes over av ALLE varianter som henter eksterne data for klokkeslettet.
- ww3_svell/ww3_begge tester TRE ting samtidig: WW3 i stedet for GFS, WW3 sin TOPPPERIODE (ptp1) der ratingen ellers bruker gjennomsnittsperioden (Komar og Gaughan, period_score, p(T)), og uten surf_factor_prior. Transfer-kalibreringen (reservemodellen) er lært mot GFS-skalaen og brukes urørt på WW3-svellet.
- Observerte stjerner kan være et intervall ('4-5'): treff ±1 og stjerneavviket måles mot nærmeste ende. Stjerneavviket har fortegn (negativt = appen rater lavere enn observert).
- Kolonnen 'Grunnlinje på SAMME saker' er dagens rating regnet på nøyaktig de sakene varianten evaluerte - sammenlign den, ikke grunnlinjeraden øverst, når varianten hopper over saker.
- Dekning: WW3-arkivet ('fersk', 48 t) og inndata-bildet (72 t) tas bare ukentlig - logger/benchmarks i dagene imellom får 'ikke evaluert' i variantene som trenger dem.
- Benchmarks: fyll data/benchmarks.json (format i fila) med tall fra surf-forecast/Surfline; inndataene for timen hentes fra data/backtest/inputs/ (skrives av workflowen hver uke og kan kjøres oftere).
- laert_eksponering: del B kjører i SKYGGEMODUS i produksjonen (Theodor 14.10.2026) - varianten viser hva ratingen ville blitt med læringen koblet inn. Lærte bøtter lang/kort (par) per spot: grotfjord 0/0 (1 par), tromvik 0/0 (4 par), ersfjordstranda 0/0 (7 par), russelv 0/0 (11 par), lenangsoyra 0/0 (10 par), steinkrossa 0/0 (7 par), unstad 0/0 (12 par), farstadsanden 0/0 (6 par). Uten lærte bøtter er varianten identisk med grunnlinja.
- Testlaben endrer aldri spots.json eller ratingen.
