## Posisjonsrunden og gjennomgangen 10.11.2026

Hele svaret fra spotansvarlig ligger i `salten-gjennomgang.csv` (én linje per spot): **0 godkjent, 1 rett, 3 avvis.** Ingenting i spots.json eller appen er endret. Salten har ingen spots i appen fra før.

- **Rett (1):** seines. Posisjonen er godkjent (sikkerhet B) og spoten er bygget. Facing og offshore-vind er rettet, se under.
- **Avvis (3):** monumentet og storvika er bygget, men parkert fordi vinduet er under ca. 15°. lop venter på lokalkunnskap og er ikke bygget.

## seines (point break)

Snittet ble hentet 10.11 kl. 11:35Z (0 til 3 km langs 316,3°, 18 tidspunkter, hver 3. time fra 10.11 kl. 06Z til 12.11 kl. 09Z, `data/bw_point_search/result_2026-11-10T1135_kandidater.json`).

- **Facing er rettet fra 316,3° til 295°.** 316,3° er kystnormalen på spissen. Bølgene ved punktet kom fra 292–298° (400–500 m ut) i de fire tidspunktene regelen fant et punkt, mens svellet ute kom fra 275–281°. Offshore-vinden følger med: 70–160°.
- **295° ligger 10° utenfor hovedsektoren i vinduet (263–285°).** Spotansvarlig godtar det for en point break.
- **BarentsWatch-punktet 500 m ut (8,5 m) er beholdt.** Hs er flat 0,45–0,47 m fra 500 m til 3 km kl. 12Z, og retningen der er 292–294°. Nytt snitt langs 295° tas neste gang snittet kjøres.
- **Lavere sikkerhet:** grunnlaget er fire tidspunkter med lite svell (0,4–0,9 m ute). Ett av dem er vindsjø (2,3 s), så det reelle grunnlaget ved 500 m er tre svelltimer (6,1–6,7 s). Ved 400 m er det åtte timer med 6,2–6,9 s og retning 296–298°, og det styrker 295°. Ellers viser BarentsWatch her mest vindsjø (periode 2–3 s).
- **Virkningen er liten for bølgene:** retningene som er sett ved punktet (292–298° og 317°) ligger under 30° fra både gammel og ny facing. Det som endres i praksis, er at vindsektoren dreies 21°. Facing 295° er ikke bekreftet av en observasjon eller en lokal kilde.
- **Høydene mangler.** Fabrikken setter ikke ideal_height og max_height for point break. Spotansvarlig anbefaler standarden [0,8, 2,0] og maks 3,5 merket ubekreftet til det finnes observasjoner. Det er Theodors avgjørelse.
- **Vern:** spoten ligger inne i Seinesodden naturreservat. Forskriften har ikke ferdselsforbud. Motorferdsel og brettseiling er forbudt hele året, og surfebrett er ikke nevnt. Vi leser brettseiling som seilbrett, så appen viser ikke «Forbud nå». Leser Theodor det annerledes, settes forbudet inn før spoten publiseres. Straumøya naturreservat ligger 1 168 m unna og har de samme bestemmelsene.

## Parkert

| Spot | Hvorfor |
|---|---|
| monumentet | Fri linje til åpent hav er bare ca. 13° (317–329°), og midten av vinduet ligger 46–55° fra kystnormalen (facing 18,4°). Spoten ville nesten alltid vist «Treffer ikke». OSM gir 33° sammenhengende vindu ut til 50 km, så det er kravet om 150 km og avviket fra facing som avgjør. |
| storvika | Stranda ligger innerst i ei lang, smal bukt med fri linje til havet bare gjennom 268–281°, og facing 261,6° ligger utenfor vinduet. Posisjonen er flyttet 3,9 km fra listepinnen. EMODnet gir 12,4 m dybde på selve posisjonen, og det er ikke forklart. |

Begrunnelsene står i `data/kandidater/status_overstyring.json`. BarentsWatch-snitt er ikke kjørt for de to, så punktene deres er foreløpige (bare dybde).

## Hva som skal til

| Spot | Hva som mangler | Hvem |
|---|---|---|
| seines | Theodors ja til regionen og til høydene. Da settes spoten inn i spots.json (`tools/godkjenn_spot.py`), og det kjøres én prøvehenting før merge. | Theodor |
| monumentet, storvika | Lokalkunnskap om hvor bølgen brekker, eller en modell for wrap og innaskjærs vindbølger. | Senere |
| lop | Bukta ligger innaskjærs med 7° vindu. Noen må vite hvor og når det brekker. | Lokalkunnskap |

## Ikke sjekket

- Flyfotoene er ikke sett på nytt etter posisjonsrunden. Gjennomgangen bygger på minikart, OSM-kyst og snittet.
- EMODnet og BarentsWatch bruker ikke samme bunn, så 8 m-kravet er testet mot en annen bunn enn Hs-profilen.
