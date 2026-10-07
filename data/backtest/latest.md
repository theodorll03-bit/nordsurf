# Testlab for treffsikkerhet - 2026-10-07 13:50 UTC

Saker: 15 (15 faste observasjoner, 0 logger, 0 benchmarks). WW3-arkiv: 395 spot-timer. Vindmålinger: 0 spot-timer.

## Samlet

| Variant | Evaluert | Faste obs. holder | Surfehøyde-feil (m, snitt) | Treff ±1 stjerne | Stjerneavvik (snitt, fortegn) | Benchmark-avvik (stjerner / m / kJ) | Ikke evaluert | Grunnlinje på SAMME saker (holder / feil m / treff ±1) |
|---|---|---|---|---|---|---|---|---|
| grunnlinje | 15 | 15/15 | 0,05 (n=9) | 8/8 (100 %) | -0,38 (n=8) | – / – / – (n=0) | 0 | 15/15 / 0,05 / 8/8 |
| ww3_svell | 10 | 5/10 (ryker: unstad_2609, unstad_2809_12, unstad_2809_13, unstad_2809_14, unstad_2809_15) | 0,40 (n=5) | 4/8 (50 %) | -0,88 (n=8) | – / – / – (n=0) | 5 | 10/10 / 0,07 / 8/8 |
| energi_tp | 15 | 15/15 | 0,05 (n=9) | 8/8 (100 %) | -0,38 (n=8) | – / – / – (n=0) | 0 | 15/15 / 0,05 / 8/8 |
| energi_ww3 | 10 | 10/10 | 0,07 (n=5) | 8/8 (100 %) | -0,38 (n=8) | – / – / – (n=0) | 5 | 10/10 / 0,07 / 8/8 |
| ww3_begge | 10 | 5/10 (ryker: unstad_2609, unstad_2809_12, unstad_2809_13, unstad_2809_14, unstad_2809_15) | 0,40 (n=5) | 4/8 (50 %) | -0,88 (n=8) | – / – / – (n=0) | 5 | 10/10 / 0,07 / 8/8 |
| vind_korr | 0 | – | – (n=0) | – | – (n=0) | – / – / – (n=0) | 15 | – / – / – |

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

## ww3_svell - WW3-svell (phs1/pdir1/ptp1) i stedet for GFS, uten surf_factor_prior for Unstad

| Sak | Forventet | Stjerner | Surfehøyde | Ord | Holder | Feil (m) | ±1 |
|---|---|---|---|---|---|---|---|
| Grøtfjord 26.09 (BarentsWatch 0,33 m) - helt flatt | stars_max=0, size_m=0.0 | 0 | 0,00 | flat | ja | 0,00 | – |
| Lenangsøyra 26.09 - ikke surfbart (vindsjø på tvers) | stars_max=1 | 0 | 0,00 | treffer_ikke | ja | – | – |
| Unstad 26.09 kl. 14:45 - over hodet, 4 stjerner | stars_min=3, surf_m=2.4, size_m=2.4, stars_obs=4 | 4 | 1,69 |  | NEI | 0,71 | ja |
| Unstad 27.09 kl. 06 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 4 | 1,25 |  | ja | 0,30 | ja |
| Unstad 27.09 kl. 07 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 | 1,08 |  | ja | 0,47 | ja |
| Unstad 27.09 kl. 08 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 | 1,03 |  | ja | 0,52 | ja |
| Unstad 28.09 kl. 12 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 2 | 1,05 |  | NEI | – | nei |
| Unstad 28.09 kl. 13 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 2 | 1,00 |  | NEI | – | nei |
| Unstad 28.09 kl. 14 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 2 | 0,97 |  | NEI | – | nei |
| Unstad 28.09 kl. 15 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 2 | 0,88 |  | NEI | – | nei |

## energi_tp - Energi med toppperiode anslått som gjennomsnitt × 1.25 (GFS for alt)

| Sak | Forventet | Stjerner | Surfehøyde | Ord | Holder | Feil (m) | ±1 |
|---|---|---|---|---|---|---|---|
| Grøtfjord 24.09 (met.no 1,9 m) - helt flatt | stars_max=0, size_m=0.0 | 0 (Tp-faktor 1.25) | 0,00 | flat | ja | 0,00 | – |
| Grøtfjord 24.09 (BarentsWatch 0,3 m) - helt flatt | stars_max=0, size_m=0.0 | 0 (Tp-faktor 1.25) | 0,00 | flat | ja | 0,00 | – |
| Grøtfjord 24.09 kl. 09 (Windy 1,7 m fra 267°) - helt flatt | stars_max=0, size_m=0.0 | 0 (Tp-faktor 1.25) | 0,10 | flat | ja | 0,10 | – |
| Grøtfjord 25.09 (3° utenfor vinduet) - helt flatt | stars_max=0, size_m=0.0 | 0 (Tp-faktor 1.25) | 0,00 | treffer_ikke | ja | 0,00 | – |
| Grøtfjord 26.09 (BarentsWatch 0,33 m) - helt flatt | stars_max=0, size_m=0.0 | 0 (Tp-faktor 1.25) | 0,00 | flat | ja | 0,00 | – |
| Lenangsøyra 26.09 - ikke surfbart (vindsjø på tvers) | stars_max=1 | 0 (Tp-faktor 1.25) | 0,00 | blown_out | ja | – | – |
| Unstad 26.09 kl. 14:45 - over hodet, 4 stjerner | stars_min=3, surf_m=2.4, size_m=2.4, stars_obs=4 | 4 (Tp-faktor 1.25) | 2,42 |  | ja | 0,02 | ja |
| Unstad 27.09 kl. 06 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 (Tp-faktor 1.25) | 1,48 |  | ja | 0,07 | ja |
| Unstad 27.09 kl. 07 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 (Tp-faktor 1.25) | 1,34 |  | ja | 0,21 | ja |
| Unstad 27.09 kl. 08 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 4 (Tp-faktor 1.25) | 1,49 |  | ja | 0,06 | ja |
| Unstad 28.09 kl. 12 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 (Tp-faktor 1.25) | 1,21 |  | ja | – | ja |
| Unstad 28.09 kl. 13 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 (Tp-faktor 1.25) | 1,17 |  | ja | – | ja |
| Unstad 28.09 kl. 14 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 (Tp-faktor 1.25) | 1,15 |  | ja | – | ja |
| Unstad 28.09 kl. 15 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 (Tp-faktor 1.25) | 1,11 |  | ja | – | ja |
| Farstadsanden, svell fra 338° over Nordneset - treffer ikke | stars_max=1, low_reason=treffer_ikke | 0 (Tp-faktor 1.25) | 1,28 | treffer_ikke | ja | – | – |

## energi_ww3 - Energi fra WW3 (svell phs1/ptp1, total hs/tp - høyde og periode fra samme modell), ellers som i dag

| Sak | Forventet | Stjerner | Surfehøyde | Ord | Holder | Feil (m) | ±1 |
|---|---|---|---|---|---|---|---|
| Grøtfjord 26.09 (BarentsWatch 0,33 m) - helt flatt | stars_max=0, size_m=0.0 | 0 (WW3-energi av 2.3 m/16.38 s) | 0,00 | flat | ja | 0,00 | – |
| Lenangsøyra 26.09 - ikke surfbart (vindsjø på tvers) | stars_max=1 | 0 (WW3-energi av 1.11 m/11.78 s) | 0,00 | blown_out | ja | – | – |
| Unstad 26.09 kl. 14:45 - over hodet, 4 stjerner | stars_min=3, surf_m=2.4, size_m=2.4, stars_obs=4 | 4 (WW3-energi av 3.47 m/15.89 s) | 2,42 |  | ja | 0,02 | ja |
| Unstad 27.09 kl. 06 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 (WW3-energi av 2.55 m/13.7 s) | 1,48 |  | ja | 0,07 | ja |
| Unstad 27.09 kl. 07 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 (WW3-energi av 2.45 m/13.51 s) | 1,34 |  | ja | 0,21 | ja |
| Unstad 27.09 kl. 08 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 4 (WW3-energi av 2.56 m/13.39 s) | 1,49 |  | ja | 0,06 | ja |
| Unstad 28.09 kl. 12 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 (WW3-energi av 2.67 m/11.17 s) | 1,21 |  | ja | – | ja |
| Unstad 28.09 kl. 13 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 (WW3-energi av 2.56 m/11.12 s) | 1,17 |  | ja | – | ja |
| Unstad 28.09 kl. 14 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 (WW3-energi av 2.47 m/11.08 s) | 1,15 |  | ja | – | ja |
| Unstad 28.09 kl. 15 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 3 (WW3-energi av 2.36 m/11.03 s) | 1,11 |  | ja | – | ja |

## ww3_begge - Begge WW3-svellene hver for seg mot vindu/eksponering, beste teller (uten prior)

| Sak | Forventet | Stjerner | Surfehøyde | Ord | Holder | Feil (m) | ±1 |
|---|---|---|---|---|---|---|---|
| Grøtfjord 26.09 (BarentsWatch 0,33 m) - helt flatt | stars_max=0, size_m=0.0 | 0 (partisjon 1) | 0,00 | flat | ja | 0,00 | – |
| Lenangsøyra 26.09 - ikke surfbart (vindsjø på tvers) | stars_max=1 | 0 (partisjon 1) | 0,00 | treffer_ikke | ja | – | – |
| Unstad 26.09 kl. 14:45 - over hodet, 4 stjerner | stars_min=3, surf_m=2.4, size_m=2.4, stars_obs=4 | 4 (partisjon 1) | 1,69 |  | NEI | 0,71 | ja |
| Unstad 27.09 kl. 06 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 4 (partisjon 1) | 1,25 |  | ja | 0,30 | ja |
| Unstad 27.09 kl. 07 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 (partisjon 1) | 1,08 |  | ja | 0,47 | ja |
| Unstad 27.09 kl. 08 - brysthøyt til hodehøyt, ca. 3 stjerner | stars_min=2, size_m=1.55, stars_obs=3 | 3 (partisjon 1) | 1,03 |  | ja | 0,52 | ja |
| Unstad 28.09 kl. 12 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 2 (partisjon 1) | 1,05 |  | NEI | – | nei |
| Unstad 28.09 kl. 13 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 2 (partisjon 1) | 1,00 |  | NEI | – | nei |
| Unstad 28.09 kl. 14 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 2 (partisjon 1) | 0,97 |  | NEI | – | nei |
| Unstad 28.09 kl. 15 - 'firing', 4-5 stjerner | stars_min=3, stars_obs=[4, 5] | 2 (partisjon 1) | 0,88 |  | NEI | – | nei |

## vind_korr - met.no-vind erstattet med målt vind fra nærmeste KystVær-stasjon (oppgave 2e)

| Sak | Forventet | Stjerner | Surfehøyde | Ord | Holder | Feil (m) | ±1 |
|---|---|---|---|---|---|---|---|

## Merknader

- Faste observasjoner har inndata rekonstruert fra ekte kjøringer (samme som test_rating.py). Logger bruker inndataene loggen selv lagret (uten vind/tidevann - merket [delvis]).
- Varianter som trenger WW3 eller vindmålinger for en time uten data hopper over saken (telles under 'Ikke evaluert'). Sammenlign bare varianter på samme saker.
- Saker merket retningsbundet (Grøtfjord 25.09 '3° utenfor vinduet', Farstadsanden 338° over Nordneset) tester en geometriregel for ÉN bestemt inndata-retning; variantene som bytter retningen mot WW3 hopper over dem (en annen modells retning gjør forventningen meningsløs, ikke feil). Syntetiske saker (tenkte inndata, Farstadsanden 338°) hoppes over av ALLE varianter som henter eksterne data for klokkeslettet.
- ww3_svell/ww3_begge tester TRE ting samtidig: WW3 i stedet for GFS, WW3 sin TOPPPERIODE (ptp1) der ratingen ellers bruker gjennomsnittsperioden (Komar og Gaughan, period_score, p(T)), og uten surf_factor_prior. Transfer-kalibreringen (reservemodellen) er lært mot GFS-skalaen og brukes urørt på WW3-svellet.
- Observerte stjerner kan være et intervall ('4-5'): treff ±1 og stjerneavviket måles mot nærmeste ende. Stjerneavviket har fortegn (negativt = appen rater lavere enn observert).
- Kolonnen 'Grunnlinje på SAMME saker' er dagens rating regnet på nøyaktig de sakene varianten evaluerte - sammenlign den, ikke grunnlinjeraden øverst, når varianten hopper over saker.
- Dekning: WW3-arkivet ('fersk', 48 t) og inndata-bildet (72 t) tas bare ukentlig - logger/benchmarks i dagene imellom får 'ikke evaluert' i variantene som trenger dem.
- Benchmarks: fyll data/benchmarks.json (format i fila) med tall fra surf-forecast/Surfline; inndataene for timen hentes fra data/backtest/inputs/ (skrives av workflowen hver uke og kan kjøres oftere).
- Testlaben endrer aldri spots.json eller ratingen.
