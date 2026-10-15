# Spotfabrikken mot de 8 kjente (ROADMAP K del C.2, 16.10.2026)

`python tools/bygg_spot.py --kjent …` bygger hver av de 8 fra posisjonen i spots.json (ikke listepinnen) og sammenligner med det som står i spots.json. spots.json er ikke endret.

Grenser (Theodor): facing ±15°, vindusoverlapp minst 70 % (andel av spots.json-vinduet som fabrikken også har), offshore-sektor og BarentsWatch-punktets avstand rapportert. «Innenfor» = facing og vindu innenfor grensene.

| Spot | facing fabrikk / spots.json (Δ) | Vindu fabrikk / spots.json | Overlapp (ekstra grader) | Offshore-vind fabrikk / spots.json (overlapp) | BW-punkt: Δ til spots.json (foreløpig, bare dybde) | Havpunkt Δ | Tidevannssted (Kartverket) | Innenfor |
|---|---|---|---|---|---|---|---|---|
| grotfjord | 288.1 / 295 (7°) | [286, 315] / [286, 310] | 100% (+5) | [48, 168] / [76, 166] (100%) | 60 m | 0.0 km | Andenes | ja |
| tromvik | 317.2 / 330 (13°) | [314, 349] / [314, 349] | 100% (+0) | [77, 197] / [105, 195] (100%) | 155 m | 0.0 km | Andenes | ja |
| ersfjordstranda | 286.6 / 315 (28°) | [289, 320] / [294, 320] | 100% (+5) | [47, 167] / [90, 180] (86%) | 121 m | 0.7 km | Andenes | **nei** |
| russelv | 310.4 / 315 (5°) | [[5, 14], [349, 356]] / [[5, 15], [349, 356]] | 95% (+0) | [70, 190] / [90, 180] (100%) | 452 m | 1.1 km | Hammerfest | ja |
| lenangsoyra | 306.3 / 19 (73°) | [15, 23] / [15, 23] | 100% (+0) | [66, 186] / [155, 245] (35%) | 208 m | 0.0 km | Hammerfest | **nei** |
| steinkrossa | 52.9 / 45 (8°) | [315, 16] / [315, 16] | 100% (+0) | [173, 293] / [175, 265] (100%) | 63 m | 0.7 km | Andenes | ja |
| unstad | 296.1 / 294.8 (1°) | [253, 336] / [253, 335] | 100% (+1) | [56, 176] / [70, 232] (66%) | 450 m | 0.1 km | Andenes | ja |
| farstadsanden | 326.6 / 310 (17°) | [284, 327] / [284, 326] | 100% (+1) | [87, 207] / [85, 200] (98%) | 367 m | 0.1 km | Kristiansund | **nei** |

**Resultat: 5 av 8 innenfor. Kravet for å bygge Lofoten og Vesterålen i natt var minst 6 av 8 - ikke oppfylt, så del C er STOPPET for bygging** (det fantes uansett ingen kandidater med sikkerhet A og status klar: koordinatjakten (A2) ble stoppet, og A krever flyfoto).

## Hva som stemmer og ikke
- **Vinduet** er det sterke leddet: 7 av 8 dekker hele spots.json-vinduet (Russelv 95 %, to sektorer). Men fabrikken tar også med grader spots.json har tatt bort med vilje: Grøtfjord +5 (311-315, kartdata-hullet der svell fra 313° var flatt 25.09) og Ersfjordstranda +5 (289-293). Samme metode som check_spot.py (GSHHS f, 150 km, 300 m kysttoleranse) - observasjoner og kjente hull i GSHHS må fortsatt inn for hånd.
- **facing** er det svake leddet. Fabrikken regner strandas normal fra OSM-kystlinja innen 500 m. Det bommer for Ersfjordstranda (28°), Lenangsøyra (73°) og Farstadsanden (17°). spots.json bruker selv ikke én definisjon: Lenangsøyra sin facing (19) er midten av vinduet [15,23], mens Steinkrøssa sin (45) er strandas retning og ligger utenfor vinduet [315,16]. En regel for facing på nye spots bør Theodor bestemme (strandnormal eller midten av vinduet) - ikke justert mot fasiten her.
- **offshore_wind** følger facing (motsatt ±60°), så bommen på facing går rett inn i vindsektoren (Lenangsøyra 35 % overlapp). spots.json bruker ±45° og egne observasjoner (Unstad [70,232], Farstadsanden [85,200]).
- **BarentsWatch-punktet** her er bare «første snittpunkt med EMODnet-dybde ≥ 8 m» - flat Hs må hentes fra BarentsWatch i Actions (`find_bw_point.yml` med `kandidater`). Avvikene (60-452 m) sier derfor lite ennå.
- **Havpunkt** og **tidevannssted** (Kartverkets referansested: Andenes, Hammerfest, Kristiansund) finnes for alle 8. (Første kjøring fikk ingen tidevannssted - feil parameter i spørringen, funnet av kontrolløren og rettet.)

Minikart per spot: `data/kandidater/bygget/<id>.png` (vindu, facing, offshore-vind, snittpunkter, foreløpig BarentsWatch-punkt; kyst © OpenStreetMap-bidragsytere).
