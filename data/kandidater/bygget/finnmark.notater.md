## Posisjonsrunden og gjennomgangen 10.11.2026

Hele svaret fra spotansvarlig ligger i `finnmark-gjennomgang.csv` (én linje per spot): **2 godkjent, 3 avvis.** Ingenting i spots.json eller appen er endret. Finnmark har ingen spots i appen fra før.

- **Godkjent (2):** berlevag-sandfjorden og persfjord. Begge har posisjon med sikkerhet A og er bygget med spotfabrikken uten rettelser.
- **Avvis (3):** porsangvika, skallelv og skallneset venter på lokalkunnskap og er ikke bygget.

## BarentsWatch-snittet

Snittet ble hentet 10.11 kl. 11:35Z (0 til 3 km langs facing, 18 tidspunkter, hver 3. time fra 10.11 kl. 06Z til 12.11 kl. 09Z, `data/bw_point_search/result_2026-11-10T1135_kandidater.json`).

| Spot | Punkt | Hs ved punktet (median) | Retning ved punktet | Regelen fant punktet i |
|---|---|---|---|---|
| berlevag-sandfjorden | 500 m ut, 8,0 m | 0,86 m | 5° (31° i valgt time) | 12 av 18 tidspunkter (2 av 5 med svell i vinduet) |
| persfjord | 900 m ut, 8,8 m | 1,13 m | 350° | 9 av 18 tidspunkter (8 av 13 med svell i vinduet) |

- **berlevag-sandfjorden, nordkanten av vinduet har lavere sikkerhet.** Svellet ute kom mest fra 5–34° i snittet. Nordlig svell (5–12°, utenfor vinduet 32–105°) nådde likevel punktet med 0,7–1,2 m. OSM-kysten gir vindu 13–107°. Vinduet er ikke rettet, for det finnes ingen observasjoner. 10 av de 12 tidspunktene regelen fant punktet i, hadde svell ute fra 349–12°, altså utenfor vinduet. I de to med svell i vinduet var perioden ved punktet 3,6–4,5 s, altså vindsjø. Appen vil trolig vise «Treffer ikke» når svellet kommer rett fra nord.
- **berlevag-sandfjorden:** EMODnet gir land på selve posisjonen og 100 m ut (−2,3 m og −0,3 m). Det skyldes det grove rutenettet.
- **persfjord:** EMODnet gir −4,3 m på selve posisjonen. Posisjonen ligger 91 m fra OSM-kysten, så det skyldes det grove rutenettet. Første punkt med 8 m ligger 900 m ut.
- Høydene [0,8, 2,0] og maks 3,5 er fabrikkens standard for strand, ukalibrert. Offshore-vinden er standard (motsatt av facing ±45°), ubekreftet. Tidevannet følger Vardø.

## Vern

- **berlevag-sandfjorden** ligger inne i Sandfjorden landskapsvernområde. Forskriften begrenser bare motorisert ferdsel.
- **persfjord** ligger 375 m utenfor Persfjorden-Syltefjorden landskapsvernområde. Der kreves bare varsom ferdsel.

## Hva som skal til

| Spot | Hva som mangler | Hvem |
|---|---|---|
| berlevag-sandfjorden, persfjord | Theodors ja til regionen. Da settes spotene inn i spots.json (`tools/godkjenn_spot.py`), og det kjøres én prøvehenting før merge. | Theodor |
| porsangvika | Posisjonen er god, men vinduet mot åpent hav er bare 5° (GSHHS) til 10° (OSM). Noen må vite om dønningen når inn. | Lokalkunnskap |
| skallelv | Usikkert hvilken strand det surfes på. Osen og stranda nord for odden gir helt ulike spots, og GSHHS legger osen på land. | Lokalkunnskap |
| skallneset | Revet er ikke funnet på flyfoto, og GSHHS legger posisjonen på land. | Lokalkunnskap |

## Ikke sjekket

- Flyfotoene er ikke sett på nytt etter posisjonsrunden. Gjennomgangen bygger på minikart, OSM-kyst og snittet.
- EMODnet og BarentsWatch bruker ikke samme bunn, så 8 m-kravet er testet mot en annen bunn enn Hs-profilen.
- Snittet dekker to døgn med svell mest fra nord til nordøst (349–38° ute). Østlig svell er ikke sett.
