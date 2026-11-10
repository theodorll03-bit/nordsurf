# T2: kilden til svellretningen (`pick()`), før og etter

Kjøring 2026-11-10T06:00:00+00:00. De første 48 timene der både varselet og met.no har retning, fra 2026-11-10T12:00Z. 22 spots, 1056 timer. Laget av `tools/pick_rekkefolge_rapport.py`. Ingenting er endret.

## Kort svar

- **Byttet er allerede gjort.** Siden 25.09.2026 (0fe002b) kommer `dir_offshore` bare fra Open-Meteo sitt svellfelt. met.no sin samlede sjøtilstand (svell og vindsjø blandet) brukes ikke lenger til svellretning. Det er ingenting igjen å bytte.
- De faste observasjonene fra og med 26.09 og alt som er kalibrert siden, er gjort med dagens rekkefølge. Bare Grøtfjord 24.09 er eldre enn byttet.
- Tabellen viser hva den gamle rekkefølgen (met.no først) ville gitt nå: retningen avviker median 23° (største 95°), 10 av 1056 timer ville hatt et annet stjernetall, og 2 ville flyttet seg 2 eller mer.
- Lenger ut, der BarentsWatch ikke rekker, betyr byttet mye: 667 av 2640 timer ville hatt et annet stjernetall (589 færre i dag, 78 flere), og 197 flytter seg 2 eller mer. met.no-retningen blander inn vindsjø og gir oftere treff i svellvinduet.
- **Anbefaling: la det stå som i dag.** Svellfeltet er den riktige kilden (samme felt som Windy viser som svell 1). Ingen avgjørelse trengs.

## Før (met.no først) mot etter (svellfeltet, i bruk i dag)

«Færre i dag» betyr at dagens kode gir færre stjerner enn den gamle rekkefølgen ville gitt. «Lyse timer» er timer med lys og minst 1 stjerne.

| Spot | Timer | Med BW | Avvik i retning, median | Største | Færre i dag | Likt | Flere i dag | Flyttet 2+ | Lyse timer før | Lyse timer i dag |
|---|---|---|---|---|---|---|---|---|---|---|
| Steinkrøssa | 48 | 40 | 15° | 85° | 0 | 39 | 9 | 2 | 0 | 0 |
| Horseid | 48 | 48 | 24° | 44° | 1 | 47 | 0 | 0 | 3 | 2 |
| Grøtfjord | 48 | 48 | 11° | 90° | 0 | 48 | 0 | 0 | 0 | 0 |
| Tromvik | 48 | 48 | 29° | 95° | 0 | 48 | 0 | 0 | 0 | 0 |
| Ersfjordstranda | 48 | 48 | 20° | 87° | 0 | 48 | 0 | 0 | 0 | 0 |
| Russelv | 48 | 48 | 28° | 53° | 0 | 48 | 0 | 0 | 0 | 0 |
| Lenangsøyra | 48 | 48 | 25° | 54° | 0 | 48 | 0 | 0 | 0 | 0 |
| Unstad | 48 | 48 | 24° | 51° | 0 | 48 | 0 | 0 | 0 | 0 |
| Farstadsanden | 48 | 48 | 14° | 80° | 0 | 48 | 0 | 0 | 2 | 2 |
| Bleik | 48 | 48 | 18° | 88° | 0 | 48 | 0 | 0 | 13 | 13 |
| Bunes | 48 | 48 | 24° | 45° | 0 | 48 | 0 | 0 | 4 | 4 |
| Ducks | 48 | 48 | 23° | 93° | 0 | 48 | 0 | 0 | 13 | 13 |
| Eggum | 48 | 48 | 23° | 43° | 0 | 48 | 0 | 0 | 7 | 7 |
| Haukland | 48 | 48 | 23° | 39° | 0 | 48 | 0 | 0 | 0 | 0 |
| Høyvika | 48 | 48 | 22° | 94° | 0 | 48 | 0 | 0 | 0 | 0 |
| Kvalnes | 48 | 48 | 24° | 45° | 0 | 48 | 0 | 0 | 8 | 8 |
| Kvalvika | 48 | 48 | 25° | 44° | 0 | 48 | 0 | 0 | 2 | 2 |
| Skagsanden | 48 | 48 | 23° | 44° | 0 | 48 | 0 | 0 | 5 | 5 |
| Stave | 48 | 48 | 19° | 92° | 0 | 48 | 0 | 0 | 1 | 1 |
| The Frog | 48 | 48 | 27° | 48° | 0 | 48 | 0 | 0 | 0 | 0 |
| Utakleiv | 48 | 48 | 24° | 52° | 0 | 48 | 0 | 0 | 0 | 0 |
| Vikten | 48 | 48 | 23° | 44° | 0 | 48 | 0 | 0 | 5 | 5 |
| **Alle** | 1056 | 1048 | 23° | 95° | 1 | 1046 | 9 | 2 | 63 | 62 |

## Lenger ut, uten BarentsWatch

1048 av de 1056 timene over har BarentsWatch-høyde, og der betyr svellretningen lite. Uten BarentsWatch styrer retningen høyden direkte. For timene etter de første 48, så langt met.no rekker og uten BarentsWatch (2640 timer, alle spots): retningen avviker median 14°, dagens kode gir færre stjerner i 589 timer, likt i 1973 og flere i 78. 197 timer flytter seg 2 eller mer.

## Forbehold

- Kontroll: dagens kode gir samme stjernetall som det publiserte varselet i 1056 av 1056 timer.
- met.no-retningen er hentet i dag, varselet er fra kjøringen over. Retningene er derfor ikke fra nøyaktig samme modellkjøring.
- «Før» bytter bare `dir_offshore`. Den gamle koden regnet også `turn` fra met.no-retningen, og `turn` påvirker kappingen ved usikkert varsel i timene uten BarentsWatch. Tallene lenger ut er derfor omtrentlige.
- Ett utsnitt på 48 timer. Hvor mye byttet betyr, avhenger av hvor mye vindsjø det er: jo mer vindsjø, jo lenger fra svellretningen ligger met.no-tallet.
