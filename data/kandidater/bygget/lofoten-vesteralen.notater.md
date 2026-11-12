## Nytt siden gjennomgangen 16.10.2026

- **#22 er merget til main (10.11.2026).** Claudes gjennomgang 16.10 ga 14 godkjent og 6 rettet (20 nye spots), og flakstad-beach-kirkesiden og rorvika parkert. eggum-ost-steinstrand ble parkert samme dag, så 19 nye ligger i spots.json. 14 av dem er publisert, og 5 holdes tilbake. Med Unstad, som lå der fra før, er 15 spots i regionene live.
- **Pakka er laget på nytt fra spots.json.** Den forrige utgaven av tabellen (16.10) viste verdiene fra før rettelsene (unstad-left 285°, soppelplassen 300°). Gjeldende verdier står i tabellene under.
- **Rettet etter gjennomgangen 16.10:** unstad-left, unstad-right og soppelplassen har Unstads facing 294,8° (kontrollørens andre runde). horseid har facing 305°. g-frame har BarentsWatch-punktet flyttet fra 1 400 m til 1 900 m ut, fordi 1 400 m lå i et grunnfelt.
- **g-frame 12.11.2026 (Theodors ja):** facing er satt til 270° som bølgeretning ved revet (ikke strandnormal, lavere sikkerhet), offshore til 45-135°, og BarentsWatch-punktet er flyttet til 500 m ut langs 270° (9,2 m dyp, snittet 12.11). Punktet er valgt på én time med Hs 0,36 m, så det bør ses igjen i neste vestsvell. Spoten er fortsatt holdt tilbake.
- **Holdt tilbake siden 16.10:** g-frame, unstad-left, unstad-right og soppelplassen (`enabled: false`).
- **Holdt tilbake 10.11:** ramberg, til T2b er avgjort (Theodors ja 10.11).
- **Parkert:** eggum-ost-steinstrand (eget snitt 16.10 fant ikke noe punkt), rorvika og flakstad-beach-kirkesiden.
- **Vern måles nå fra spotens posisjon**, ikke fra listepinnen, der Naturbase-oppslaget rundt posisjonen finnes. Bunes ligger inne i Lofotodden nasjonalpark (0 m, ikke 531 m som pakka sa før). Der er det varsom ferdsel og ikke noe forbud, så ingenting endres i appen.

## Spotansvarligs gjennomgang 10.11.2026

Hele svaret ligger i `lofoten-vesteralen-gjennomgang.csv` (én linje per spot): **17 godkjent, 3 rett, 7 avvis.** Kommentarene for eggum, eggum-ost-steinstrand og g-frame er presisert etter kontrollørens gjennomgang (retningen til reservatet, snitt i stedet for spenn, og bølgeretningen i snittet). Beslutningene er uendret.

- **Godkjent (17):** de 14 nye publiserte, Unstad, unstad-left og unstad-right. Facing ligger innenfor spennet OSM-kysten gir (±150 til ±500 m rundt spoten) for 13 av de 14 nye. Spennet er bredt for skagsanden (313-348°), haukland (210-235°) og kvalnes (337-348°). Unntaket er horseid, der 305° er satt med vilje (fabrikken gir 192-231°, langs stranda), så et nytt fabrikkbygg må ikke skrive over den.
- **Rett (3):** g-frame, ramberg og soppelplassen. Ingen av dem er live. g-frame er rettet i spots.json 12.11 (fortsatt `enabled: false`), de to andre er uendret. Se tabellen under.
- **Avvis (7):** aknes, andenes, broken-hearts og g-force venter på lokalkunnskap. eggum-ost-steinstrand, rorvika og flakstad-beach-kirkesiden blir stående parkert.

Svar på spørsmålene til gjennomgangen:

1. **De 14 nye publiserte trenger ikke ny gjennomgang av geometrien.** To ting står åpne: grensa mot Eggum naturreservat (se under), og at varselet gir Unstad mindre enn naboene (ROADMAP N og T2b).
2. **unstad-right beholder punktet foreløpig.** Bølgene ved punktet kom fra 288-310° (0-15° fra facing), og Hs er flat fra 400 m og utover. Punktet er likevel ikke valgt etter regelen (700 m ut i retning 239°, 8,6 m i en lomme mellom punkter på 7,2 og 7,3 m). Nytt snitt langs 294,8° tas når N er avgjort.
3. **Ikke ett felles punkt for de tre i Unstad-bukta.** unstad-left kan dele punkt med Unstad (samme bukt, nesten samme vindu). soppelplassen er åpnere mot nord og beholder sitt. unstad-right får eget snitt. Samme punktregel bør gjelde alle. Spotansvarlig foreslår at Unstads `surf_factor_prior` fjernes i samme commit som N, ellers flyttes bare ulikheten. Det er kalibrering, så Theodor avgjør det i T2.
4. **eggum-ost-steinstrand blir stående parkert.** Se tabellen under.

## Hva som skal til for spotene som ikke er publisert

| Spot | Hva som mangler | Hvem |
|---|---|---|
| g-frame | Rettet 12.11 (Theodors ja): facing 270° som bølgeretning ved revet, offshore 45-135°, BarentsWatch-punkt 500 m ut langs 270° (9,2 m). Bakgrunn: bølgene kom fra vest i snittet 16.10 (medianen 254-284°), og revet har ingen entydig strandnormal. I snittet 12.11 kom svellet ute fra nord (bare én av 18 timer fra vinduet), og retningen ved punktet var 299-326°, altså 29-56° fra facing. 400 m-punktet (8,9 m) ga 0,20 m når 500 m ga 0,36 m kl. 12Z, og lå lavere enn 500 m i alle 18 timene (i 8 av dem med retning fra land), så regelen valgte 500 m. Gjenstår: se punktet og retningen i neste vestsvell, og så Theodors ja til å slå på. | Theodor |
| unstad-left, unstad-right, soppelplassen | Ga 3,4-4,2 m når Unstad ga 1,6-1,8 m samme time i prøvevarselet 16.10 kl. 11Z (unstad-left ligger 250 m fra Unstad, unstad-right 485 m og soppelplassen 996 m). Unstads BarentsWatch-punkt (250 m ut) ligger trolig i brytesonen (ROADMAP N). Snittene deres ble tatt langs fabrikkens første facing (334° / 239° / 344°), ikke langs 294,8°. Når N er avgjort i T2: nye snitt langs 294,8° for unstad-left og unstad-right, og så ett samlet spørsmål til Theodor. | Theodor, etter T2 |
| soppelplassen (i tillegg) | Offshore-vinden er utvidet til 70-209° uten observasjon eller navngitt kilde. Spotansvarlig anbefaler 70-160°. Høydene [1,5, 3,5] mangler begrunnelse. Det samme gjelder høydene for g-frame, unstad-left og unstad-right («forslag fra Claude 16.10, ukalibrert»). Tas i det samlede spørsmålet etter N. | Theodor, etter T2 |
| ramberg | Venter på T2b (Unstad mot Flakstad). Posisjonen og punktet (900 m ut, 9,6 m) er godkjent av spotansvarlig. Facing 287,7° er strandnormalen, men ligger 9° utenfor eget vindu (297-348°), og bølgene ved punktet kom fra 327-330°. Facing 315° og offshore 90-180° ligger på grenen region/ramberg-315 og flytter spoten fra 0 til 2 stjerner. | Theodor, etter T2b |
| eggum-ost-steinstrand | Aldri 8 m dybde innen 1,5 km langs facing 11,5° (hylle på 6-7 m og skjær 1,2-1,4 km ut). Reserven (minst 6 m) ville valgt 600 m ut (6,2 m). Der kom bølgene fra 267-300° i snittet 16.10, altså 71-104° fra facing, og bak skjærene faller Hs til 0,1-0,7 m. Bølgene går langs kysten, så et annet punkt hjelper ikke. Blir stående parkert. | Lokalkunnskap om hvor og når det brekker |
| rorvika | Vinduet er ca. 6° mot Vestfjorden. Trenger en vindbølgemodell for innaskjærs spots. | Senere |
| flakstad-beach-kirkesiden | Bare svell som bøyer rundt odden (wrap), ingen fri linje til havet. Trenger en modell for wrap. | Senere |
| aknes, andenes, broken-hearts, g-force | Flyfotoet viser ikke sikkert hvor det surfes (sikkerhet C). Trenger noen som kjenner stedet. g-force ligger 131 m fra g-frame, og det må avklares om det er samme bølge. broken-hearts vender mot Vestfjorden, så vindusbredden må sjekkes før bygging. | Lokalkunnskap |

## Eggum og naturreservatet (til T2)

Eggum er publisert uten forbud. Eggum naturreservat (surfebrett forbudt hele året) ligger sør til sørvest for spoten (sektoren 150-225°). Nærmeste grensepunkt er 277 m unna i retning 152°, og i retning 210° er det 450 m. Langs stranda mot vest (240° og videre) er det ikke reservat innen 2 km. Grensa er ikke sjekket mot hvor bølgen faktisk brekker. Spørsmål til Lofoten Surfsenter i T2: hvor brekker bølgen på Eggum? Ligger den sør eller sørvest for pinnen, inne i reservatet, settes «Forbud nå».

## Flakstad (trengs i T2b)

- **`ramberg`** er Flakstad-stranda i T2b (Theodor 09.11.2026). Den er egen spot på 68.097007, 13.238991 med **eget BarentsWatch-punkt** 68.099482, 13.218344, 900 m ut langs 288°, 9,6 m dypt (snitt 16.10). Den har eget havpunkt og eget vindu (297-348°). Den er slått av til T2b er avgjort.
- **`skagsanden`** ligger 2,4 km nordøst for ramberg, ved Flakstad kirke, og er publisert. Den har også eget BarentsWatch-punkt (68.110503, 13.283045, 500 m ut, 9,3 m dypt), 2,9 km fra rambergs punkt. I kandidatlista har skagsanden aliasene «Flakstad Beach» og «Flakstad (Surfnerd/Breakfinder)». ramberg har ingen Flakstad-alias.
- **`flakstad-beach-kirkesiden`** ligger 1,0 km øst for skagsanden og er parkert.
- Begge strendene ved Flakstad har altså egne målepunkter. ramberg er hovedsammenligningen, fordi Theodor har sagt at Ramberg er Flakstad-stranda. skagsanden vises som egen kolonne, og Theodor velger når han ser tabellen.
- **Innspill til T2b:** i varselet 10.11 kl. 06Z er skagsanden større enn Unstad i alle de 32 timene de første to døgnene der minst én av dem har bølger (Unstad viser 0 i 21 av dem; høyeste verdi 1,14 m mot 1,92 m). Over hele varselet er tallet 57 av 83 timer. Det er motsatt av det Lofoten Surfsenter sier. ramberg kan ikke sammenlignes ennå, fordi den er slått av og mangler i varselarkivet.
