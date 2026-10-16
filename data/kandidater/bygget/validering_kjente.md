# Spotfabrikken mot de 8 kjente (ROADMAP K del C.2) - ny facing-regel 16.10.2026

`python tools/bygg_spot.py --kjent …` bygger hver av de 8 fra posisjonen i spots.json (ikke listepinnen) og sammenligner med spots.json. spots.json er ikke endret.

**Regel (Theodor 16.10):** facing = strandas normal der bølgene brekker, fra OSM-kystlinja ±150 m langs kysten fra nærmeste kystpunkt til nålen (holmer/skjær under 2 ha og innsjøbredder regnes ikke som stranda); vinduet regnes for seg (som før); offshore_wind standard = motsatt av facing ±45°.

Grenser: facing ±15°, vindusoverlapp minst 70 % (andel av spots.json-vinduet fabrikken også har; ekstra grader i parentes). «Innenfor» = begge.

| Spot | facing fabrikk / spots.json (Δ) | Vindu fabrikk / spots.json | Overlapp (ekstra) | Offshore-vind fabrikk / spots.json (overlapp) | BW-punkt Δ (foreløpig, bare dybde) | Havpunkt Δ | Tidevannssted | Innenfor |
|---|---|---|---|---|---|---|---|---|
| grotfjord | 296.5 / 295 (2°) | [286, 315] / [286, 310] | 100% (+5) | [72, 162] / [76, 166] (96%) | 150 m | 0.0 km | Andenes | ja |
| tromvik | 329.3 / 330 (1°) | [314, 349] / [314, 349] | 100% (+0) | [104, 194] / [105, 195] (99%) | 151 m | 0.0 km | Andenes | ja |
| ersfjordstranda | 294.1 / 315 (21°) | [289, 320] / [294, 320] | 100% (+5) | [69, 159] / [90, 180] (77%) | 96 m | 0.7 km | Andenes | **nei** |
| russelv | 314.3 / 315 (1°) | [[5, 14], [349, 356]] / [[5, 15], [349, 356]] | 95% (+0) | [89, 179] / [90, 180] (99%) | 351 m | 1.1 km | Hammerfest | ja |
| lenangsoyra | 345.5 / 19 (34°) | [15, 23] / [15, 23] | 100% (+0) | [120, 210] / [155, 245] (62%) | 76 m | 0.0 km | Hammerfest | **nei** |
| steinkrossa | 38.3 / 45 (7°) | [315, 16] / [315, 16] | 100% (+0) | [173, 263] / [175, 265] (98%) | 60 m | 0.7 km | Andenes | ja |
| unstad | 297.9 / 294.8 (3°) | [253, 336] / [253, 335] | 100% (+1) | [73, 163] / [70, 232] (56%) | 451 m | 0.1 km | Andenes | ja |
| farstadsanden | 249.4 / 310 (61°) | [284, 327] / [284, 326] | 100% (+1) | [24, 114] / [85, 200] (26%) | – m | 0.1 km | Kristiansund | **nei** |

**Resultat: 5 av 8 innenfor - kravet på minst 6 av 8 er fortsatt ikke oppfylt.** De samme fem som med forrige regel (strandnormal over 500 m): Grøtfjord, Tromvik, Russelv, Steinkrøssa og Unstad; Ersfjordstranda, Lenangsøyra og Farstadsanden er utenfor begge gangene. Ingen spot bygges uansett før Theodor har godkjent posisjonene for en region (svar 6).

## Med den nye regelen
- **Treffer godt der stranda er rett:** Grøtfjord 1,5° (var 7°), Tromvik 0,7° (var 13°), Russelv 0,7° (var 5°), Steinkrøssa 6,7° (var 8°), Unstad 3,1° (var 1° - litt dårligere).
- **Lenangsøyra 34°:** ventet - spots.json bruker midten av vinduet [15,23] der.
- **Ersfjordstranda 21°:** nærmeste kyststrekning vender mot 294°, spots.json har 315°.
- **Farstadsanden 61°:** nålen står i hjørnet av en buet strand - nærmeste kystpunkt ligger 153 m nordøst, på østsiden av bukta, og den kyststrekningen vender mot sørvest (249°). Regelen gjør det den sier; nålen står ikke foran midten av stranda (KONVENSJON.md: kyst→nål 237°). Fabrikken varsler nå slike tilfeller (facing over 45° fra midten av vinduet OG nærmeste kystpunkt over 100 m unna) - av de 8 slår varselet bare til for Farstadsanden. Ingen snittpunkt langs 249° når 8 m dyp innen 1,5 km, så BarentsWatch-punktet mangler (flagget, aldri 0).
- **Vinduet:** uendret - 7 av 8 dekker hele spots.json-vinduet; Grøtfjord +5 (311-315, kartdata-hullet) og Ersfjordstranda +5 ekstra grader som spots.json har tatt bort med vilje.
- **offshore_wind ±45°:** overlapp med spots.json 96-99 % der facing treffer (Unstad 56 % fordi Unstad sin sektor er utvidet for S/SSV-vind etter observasjoner).
- **Tidevannssted:** samme referansested, forsinkelse og faktor som henteren bruker for alle 8 (sjekket mot henterens eget oppslag 16.10).

Minikart per spot: `data/kandidater/bygget/<id>.png` (kyst © OpenStreetMap-bidragsytere).
