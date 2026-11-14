# T2a: vinden på Unstad de siste 30 dagene (laget 10.11.2026)

Kilde for påstanden: Lofoten Surfsenter, 09.11.2026: «Surfline tar alltid ned ratingen for vinden på Unstad, men det er som oftest offshore der, og offshore er bra på Unstad.»

Modellen i dag: fralandssektor [70, 232] (facing 294.8°), fralandskurve ((10, 0), (14, 1), (18, 2)) (effektiv vind i m/s, straff i stjerner). Effektiv vind er middelvind + 30 % av forskjellen opp til kastene, høyst 2 m/s. En straff koster først en hel stjerne når den er over 0,5 (rate() runder til slutt).

## Kort svar

- Fralandsvind under 10 m/s tar aldri en stjerne på Unstad: 0 av 286 rekonstruerte timer og 0 av 147 publiserte timer med surf. 55 timer fikk en straff mellom 0 og 0,5 fordi kastene løftet effektiv vind over 10 m/s. Den rundes bort så lenge ingen annen brøkstraff kommer i tillegg (Unstad har ingen tidevannsregel i dag; se T2c).
- «Som oftest offshore» stemmer også hos oss: 64 % av de lyse timene er fralands med sektoren [70, 232].
- Vi trekker ned når fralandsvinden er sterk: 64 av 195 lyse fralandstimer (33 %) ville kostet 1–2 stjerner i vindfradrag, alle med middelvind på 10 m/s eller mer. Det følger kurven fra 15.10 og er ikke en feil i koden. Om sterk fralandsvind (liten kuling og opp) også er bra på Unstad, sier ikke sitatet noe om.
- Under 10 m/s trekker vi bare ned for vind utenfor sektoren (vest til nord): 46 lyse timer.
- Kanten ved 232°: vind fra 232–250° (27 lyse timer) regnes som side-pålands eller pålands og straffes fra 3 m/s, mens 231° er fralands og fri til 10 m/s. Sektoren slutter der observasjonene slutter (193–227° er bekreftet fralands). Verdt å spørre Surfsenteret om sørvest.
- Ingen endring foreslått.

## Grunnlaget, og hva som mangler

- `data/forecast_archive` kan ikke brukes alene: filene har bare stjerner og surfehøyde (ingen vind), og de ryddes etter 8 dager (tre filer igjen: 05.11, 09.11, 10.11).
- Kontoen var stengt 16.10–05.11, så det finnes ikke noe publisert varsel for de dagene.
- Del 1 er derfor en rekonstruksjon: MET Nordic-vind (Open-Meteo `metno_seamless`, 734 timer fra 11.10 til 10.11 kl. 13) gjennom dagens vindkode. Den viser vindstraffen, ikke stjernene.
- Del 2 er det vi faktisk publiserte 24.09–14.10 (144 kjøringer i git-historikken), re-ratet med dagens kode. Del 3 er varselet som ligger ute nå.

## Del 1: rekonstruksjon 11.10–10.11

**Alle timer** (734 timer)

| Vindtype | Timer | Andel | Median vind (m/s) | Timer under 10 m/s | ... av dem med straff over 0 | ... av dem som koster minst 1 stjerne | Timer 10 m/s eller mer | ... som koster minst 1 stjerne |
|---|---|---|---|---|---|---|---|---|
| fralands | 434 | 59 % | 7,8 | 286 | 55 | 0 | 148 | 146 |
| sidevind | 4 | 1 % | 2,8 | 4 | 0 | 0 | 0 | 0 |
| side-pålands | 82 | 11 % | 10,4 | 39 | 37 | 33 | 43 | 43 |
| pålands | 214 | 29 % | 10,1 | 102 | 102 | 98 | 112 | 112 |

**Lyse timer (lys eller skumring, som i appen)** (305 timer)

| Vindtype | Timer | Andel | Median vind (m/s) | Timer under 10 m/s | ... av dem med straff over 0 | ... av dem som koster minst 1 stjerne | Timer 10 m/s eller mer | ... som koster minst 1 stjerne |
|---|---|---|---|---|---|---|---|---|
| fralands | 195 | 64 % | 8,1 | 129 | 30 | 0 | 66 | 64 |
| sidevind | 0 | 0 % | – | 0 | 0 | 0 | 0 | 0 |
| side-pålands | 27 | 9 % | 10,0 | 13 | 13 | 12 | 14 | 14 |
| pålands | 83 | 27 % | 10,3 | 37 | 37 | 34 | 46 | 46 |

Fralandstimene i lyset, etter effektiv vind:

| Effektiv vind | Timer | Straff | Koster stjerne |
|---|---|---|---|
| under 10 m/s | 99 | 0 | nei |
| 10–12 m/s | 32 | 0–0,5 | nei |
| 12–16 m/s | 51 | 0,5–1,5 | 1 stjerne |
| over 16 m/s | 13 | over 1,5 | 2 stjerner |

Fralandstimer med middelvind under 10 m/s som likevel fikk straff over 0 (kastene løftet effektiv vind over 10): 30 lyse timer, 55 i alt. Ingen av dem koster en stjerne: 0.

### Hvor vinden kom fra (lyse timer)

| Vind fra | Timer | Vår vindtype | Median vind (m/s) | Snitt straff | Timer som koster minst 1 stjerne | ... av dem under 10 m/s |
|---|---|---|---|---|---|---|
| 0–30° | 0 | – | – | – | – | – |
| 30–60° | 0 | – | – | – | – | – |
| 60–90° | 0 | – | – | – | – | – |
| 90–120° | 4 | fralands 4 | 6,9 | 0,00 | 0 | 0 |
| 120–150° | 53 | fralands 53 | 5,1 | 0,07 | 3 | 0 |
| 150–180° | 40 | fralands 40 | 6,5 | 0,21 | 8 | 0 |
| 180–210° | 54 | fralands 54 | 10,1 | 0,54 | 28 | 0 |
| 210–240° | 54 | fralands 44, side-pålands 10 | 10,7 | 1,08 | 35 | 5 |
| 240–270° | 59 | pålands 43, side-pålands 16 | 11,3 | 3,10 | 58 | 15 |
| 270–300° | 12 | pålands 12 | 7,4 | 2,44 | 11 | 6 |
| 300–330° | 27 | pålands 27 | 7,9 | 2,50 | 25 | 18 |
| 330–360° | 2 | side-pålands 1, pålands 1 | 6,9 | 1,59 | 2 | 2 |

### Dag for dag (lyse timer)

| Dato | Lyse timer | Fralands | Sidevind | Side-pålands | Pålands | Vind median / maks (m/s) | Størst effektiv vind i fralands | Fralandstimer med straff over 0 | Fralandstimer som koster stjerne | Andre timer som koster stjerne | ... av dem under 10 m/s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11.10 | 12 | 12 | 0 | 0 | 0 | 4,2 / 5,0 | 6,3 | 0 | 0 | 0 | 0 |
| 12.10 | 12 | 12 | 0 | 0 | 0 | 4,3 / 5,0 | 6,2 | 0 | 0 | 0 | 0 |
| 13.10 | 12 | 12 | 0 | 0 | 0 | 10,3 / 13,0 | 15,0 | 11 | 8 | 0 | 0 |
| 14.10 | 12 | 12 | 0 | 0 | 0 | 11,7 / 12,9 | 14,9 | 12 | 11 | 0 | 0 |
| 15.10 | 11 | 11 | 0 | 0 | 0 | 12,4 / 14,4 | 16,4 | 11 | 11 | 0 | 0 |
| 16.10 | 11 | 1 | 0 | 4 | 6 | 12,5 / 13,7 | 15,7 | 1 | 1 | 10 | 0 |
| 17.10 | 11 | 3 | 0 | 2 | 6 | 7,7 / 10,8 | 12,8 | 2 | 1 | 8 | 8 |
| 18.10 | 11 | 7 | 0 | 4 | 0 | 9,0 / 11,5 | 13,5 | 6 | 4 | 4 | 4 |
| 19.10 | 11 | 11 | 0 | 0 | 0 | 18,6 / 19,0 | 21,0 | 11 | 11 | 0 | 0 |
| 20.10 | 11 | 11 | 0 | 0 | 0 | 7,3 / 10,0 | 11,8 | 5 | 0 | 0 | 0 |
| 21.10 | 10 | 10 | 0 | 0 | 0 | 3,8 / 6,2 | 7,5 | 0 | 0 | 0 | 0 |
| 22.10 | 10 | 10 | 0 | 0 | 0 | 6,4 / 6,8 | 8,2 | 0 | 0 | 0 | 0 |
| 23.10 | 10 | 10 | 0 | 0 | 0 | 8,3 / 9,5 | 11,5 | 6 | 0 | 0 | 0 |
| 24.10 | 10 | 10 | 0 | 0 | 0 | 7,7 / 8,8 | 10,6 | 3 | 0 | 0 | 0 |
| 25.10 | 10 | 10 | 0 | 0 | 0 | 9,6 / 10,3 | 12,3 | 8 | 3 | 0 | 0 |
| 26.10 | 10 | 10 | 0 | 0 | 0 | 5,7 / 7,4 | 9,1 | 0 | 0 | 0 | 0 |
| 27.10 | 10 | 10 | 0 | 0 | 0 | 4,3 / 7,1 | 8,6 | 0 | 0 | 0 | 0 |
| 28.10 | 10 | 10 | 0 | 0 | 0 | 10,2 / 12,2 | 14,2 | 9 | 8 | 0 | 0 |
| 29.10 | 10 | 10 | 0 | 0 | 0 | 8,6 / 10,3 | 12,3 | 6 | 2 | 0 | 0 |
| 30.10 | 10 | 3 | 0 | 1 | 6 | 3,3 / 4,0 | 4,6 | 0 | 0 | 3 | 3 |
| 31.10 | 9 | 4 | 0 | 2 | 3 | 11,8 / 13,2 | 15,2 | 4 | 4 | 5 | 2 |
| 01.11 | 9 | 1 | 0 | 2 | 6 | 7,4 / 9,4 | 11,2 | 1 | 0 | 8 | 8 |
| 02.11 | 9 | 0 | 0 | 0 | 9 | 10,6 / 11,3 | – | 0 | 0 | 9 | 2 |
| 03.11 | 9 | 5 | 0 | 1 | 3 | 4,5 / 7,5 | 9,0 | 0 | 0 | 4 | 4 |
| 04.11 | 9 | 0 | 0 | 0 | 9 | 13,4 / 15,4 | – | 0 | 0 | 9 | 0 |
| 05.11 | 9 | 0 | 0 | 0 | 9 | 10,5 / 12,3 | – | 0 | 0 | 9 | 2 |
| 06.11 | 8 | 0 | 0 | 7 | 1 | 10,1 / 10,9 | – | 0 | 0 | 8 | 3 |
| 07.11 | 8 | 0 | 0 | 0 | 8 | 11,8 / 13,3 | – | 0 | 0 | 8 | 0 |
| 08.11 | 8 | 0 | 0 | 4 | 4 | 12,1 / 12,3 | – | 0 | 0 | 8 | 0 |
| 09.11 | 8 | 0 | 0 | 0 | 8 | 8,9 / 15,0 | – | 0 | 0 | 8 | 5 |
| 10.11 | 5 | 0 | 0 | 0 | 5 | 6,1 / 6,3 | – | 0 | 0 | 5 | 5 |

### Kontroll av rekonstruksjonen

Mot vinden vi faktisk publiserte (met.no Locationforecast, del 2 og 3):

102 overlappende timer (10.10–10.11): fart avviker i snitt 0,0 m/s (median 0,0), retning i snitt 3° (median 3°), samme vindtype i 102 av 102 timer (100 %).

Med GFS-vind i stedet (modellen appen bruker fra ca. dag 3) blir fordelingen i de lyse timene: fralands 64 %, sidevind 0 %, side-pålands 9 %, pålands 27 %. 19 lyse timer får en annen vindtype enn med MET Nordic, men de jevner seg ut.

## Del 2: det vi faktisk publiserte 24.09–14.10, med dagens kode

**Alle timer**: 443 timer med vind, 256 av dem med minst 1 stjerne før vind.

| Vindtype | Timer med surf | Vind under 10 m/s | ... trukket ned av vind | Vind 10 m/s eller mer | ... trukket ned av vind | Stjerner tatt av vind i alt |
|---|---|---|---|---|---|---|
| fralands | 170 | 147 | 0 | 23 | 23 | 23 |
| sidevind | 0 | 0 | 0 | 0 | 0 | 0 |
| side-pålands | 15 | 13 | 9 | 2 | 2 | 16 |
| pålands | 71 | 63 | 62 | 8 | 8 | 139 |

Den gangen (koden og sektoren som gjaldt da varselet ble laget): 178 av 443 timer ble kalt fralands, og vinden tok 303 stjerner i alt. Med dagens kode: 317 timer fralands og 178 stjerner. 141 timer har byttet vindtype, 139 av dem til fralands (sektoren ble utvidet til [70, 232] 06.10).

**Lyse timer**: 235 timer med vind, 137 av dem med minst 1 stjerne før vind.

| Vindtype | Timer med surf | Vind under 10 m/s | ... trukket ned av vind | Vind 10 m/s eller mer | ... trukket ned av vind | Stjerner tatt av vind i alt |
|---|---|---|---|---|---|---|
| fralands | 100 | 89 | 0 | 11 | 11 | 11 |
| sidevind | 0 | 0 | 0 | 0 | 0 | 0 |
| side-pålands | 4 | 4 | 2 | 0 | 0 | 2 |
| pålands | 33 | 25 | 25 | 8 | 8 | 67 |

Fralandstimer under 10 m/s der vinden likevel tok en stjerne: 0.

## Del 3: varselet som ligger ute nå

Kjøring 2026-11-10T06:00Z, de første 48 timene.

**Alle timer**: 48 timer med vind, 9 av dem med minst 1 stjerne før vind.

| Vindtype | Timer med surf | Vind under 10 m/s | ... trukket ned av vind | Vind 10 m/s eller mer | ... trukket ned av vind | Stjerner tatt av vind i alt |
|---|---|---|---|---|---|---|
| fralands | 0 | 0 | 0 | 0 | 0 | 0 |
| sidevind | 0 | 0 | 0 | 0 | 0 | 0 |
| side-pålands | 0 | 0 | 0 | 0 | 0 | 0 |
| pålands | 9 | 9 | 9 | 0 | 0 | 9 |

| Tid (norsk) | Vind (m/s) | Kast | Fra | Vindtype | Effektiv | Stjerner uten vind | Stjerner | Tatt av vind |
|---|---|---|---|---|---|---|---|---|
| 10.11 kl. 08 | 6,3 | 12,0 | 322° | pålands | 8,0 | 0 | 0 | 0 |
| 10.11 kl. 09 | 6,0 | 12,6 | 311° | pålands | 8,0 | 0 | 0 | 0 |
| 10.11 kl. 10 | 6,6 | 12,3 | 303° | pålands | 8,3 | 0 | 0 | 0 |
| 10.11 kl. 11 | 5,5 | 10,7 | 308° | pålands | 7,1 | 1 | 0 | 1 |
| 10.11 kl. 12 | 6,9 | 13,3 | 293° | pålands | 8,8 | 1 | 0 | 1 |
| 10.11 kl. 13 | 5,6 | 11,4 | 311° | pålands | 7,3 | 1 | 0 | 1 |
| 10.11 kl. 14 | 3,9 | 11,3 | 313° | pålands | 5,9 | 1 | 0 | 1 |
| 10.11 kl. 15 | 5,1 | 10,3 | 291° | pålands | 6,7 | 1 | 0 | 1 |
| 11.11 kl. 08 | 3,1 | 5,4 | 153° | fralands | 3,8 | 0 | 0 | 0 |
| 11.11 kl. 09 | 2,2 | 5,1 | 154° | fralands | 3,1 | 0 | 0 | 0 |
| 11.11 kl. 10 | 2,3 | 4,0 | 93° | fralands | 2,8 | 0 | 0 | 0 |
| 11.11 kl. 11 | 1,3 | 3,8 | 111° | fralands | 2,0 | 0 | 0 | 0 |
| 11.11 kl. 12 | 1,1 | 2,4 | 180° | fralands | 1,5 | 0 | 0 | 0 |
| 11.11 kl. 13 | 1,8 | 3,3 | 148° | fralands | 2,2 | 0 | 0 | 0 |
| 11.11 kl. 14 | 1,4 | 2,9 | 113° | fralands | 1,8 | 0 | 0 | 0 |
| 11.11 kl. 15 | 1,3 | 2,3 | 77° | fralands | 1,6 | 0 | 0 | 0 |

