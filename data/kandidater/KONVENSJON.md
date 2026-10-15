# Konvensjon for spot-koordinaten (ROADMAP K del A2 punkt 0, målt 16.10.2026)

Målt på de 8 nålene i spots.json mot OSM-kystlinja (landpolygoner fra osmdata.openstreetmap.de; i Norge i stor grad importert fra Kartverkets N50) og OSM-strender (natural=beach/sand).

| Spot | Land/sjø | Fra vannkanten | Retning kyst → nål | facing | Hvor på stranda |
|---|---|---|---|---|---|
| grotfjord | sjø | 143 m | 287° | 295 | 20 % langs sjøkanten (619 m) |
| tromvik | sjø | 98 m | 3° | 330 | ingen OSM-strand innen 600 m |
| ersfjordstranda | sjø | 127 m | 294° | 315 | 81 % langs sjøkanten (1 400 m, «Ersfjord beach») |
| russelv | sjø | 24 m | 338° | 315 | ingen OSM-strand innen 600 m |
| lenangsoyra | sjø | 115 m | 314° | 19 | ingen OSM-strand innen 600 m |
| steinkrossa | sjø | 30 m | 39° | 45 | ingen OSM-strand innen 600 m |
| unstad | sjø | 28 m | 289° | 294,8 | ingen OSM-strand innen 600 m |
| farstadsanden | sjø | 153 m | 237° | 310 | 46 % langs sjøkanten (1 293 m, «Farstadsanden») |

**Konvensjonen, slik tallene viser den:** nålen står **i sjøen, ut fra stranda der man padler ut** - ikke i strandkanten. Avstanden fra vannkanten er 24-153 m (median ca. 105 m), i to grupper: tett inntil (Russelv, Steinkrøssa, Unstad: 24-30 m) og ca. 100-150 m ut (de fem andre). Retningen fra kysten til nålen ligger stort sett nær facing (unntak Lenangsøyra og Farstadsanden, der nålen står skrått ut fra en buet strand). Hvor langs stranda varierer (20 %, 46 %, 81 %) - nålen står ved hovedtoppen, ikke midt på stranda.

Per type (Theodors regel 15.10, uendret):
- **beachbreak:** der hovedtoppen er; ukjent → midt på den surfbare delen av sandstranda, ca. 100 m ut fra vannkanten
- **pointbreak:** take-off ved tuppen av odden
- **reef:** over revet der bølgene brekker
- **elveos:** utenfor osen, på sandbanken
- Flere spots på samme strand (f.eks. unstad og unstad-right, hoddevik-left og hoddevik-right) får hvert sitt punkt der hver bølge faktisk er.

`tools/koordinatjakt.py` bruker 100 m ut fra vannkanten (`OFFSET_M`). NB: konvensjonen er målt på de samme 8 som valideringen kjøres på (planen ba om det), så avstanden ut er ikke uavhengig av valideringen.
