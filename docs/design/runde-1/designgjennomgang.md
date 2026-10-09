# Designgjennomgang, runde 1 (09.10.2026)

Gjennomgått med apple-design-sjekklista (Apples Human Interface Guidelines, lest fra
`accessibility.md`, `layout.md`, `typography.md`, `color.md`, `designing-for-ios.md`,
`designing-for-macos.md`, `tab-bars.md`, `sidebars.md`, `sheets.md`, `charting-data.md`,
`dark-mode.md`, `branding.md`, `app-icons.md` og `cross-platform.md`). Nordsurf er en PWA,
så plattformkonvensjonene gjelder som prinsipper, ikke som krav om native komponenter.
Skjermbildene det vises til ligger i samme mappe (`*_mobil_*.png`, `*_pc_*.png`,
«før» i `for/`).

## Oppsummering

Appen har fått én tydelig tese: **ratingen først, i farge og ord, og alt annet bak ett trykk.**
Det som vil huskes er ordmerket i Bricolage Grotesque, den varme råhvite flata og
stolpegrafen der høyde, rating og lys leses i ett blikk. Vurdering: **God.** Ingen kritiske
funn etter rettelsene under; to middels funn står igjen og er notert for runde 2.

## Linse 1: tilgjengelighet (målt, ikke anslått)

Kontrast, regnet fra hex-verdiene i `docs/css/app.css`:

| Par | Verdier | Kontrast |
|---|---|---|
| Brødtekst, lys | #1E1B16 på #F6F1E8 | 15,3:1 |
| Dempet tekst, lys | #5B554B på #F6F1E8 | 6,6:1 |
| Ratingord 1-5, lys (`--rc-ink`) | #B33F15 / #7A5600 / #1E7A42 / #0F7272 / #4343B5 på #F6F1E8 | 5,1 / 5,9 / 4,8 / 5,1 / 6,9:1 |
| Brødtekst, mørk | #F2ECE1 på #16130F | 15,7:1 |
| Dempet tekst, mørk | #ADA396 på #16130F | 7,5:1 |
| Ratingord 1-5, mørk | #F07A50 / #F2C24F / #5FCB8C / #4FC9C9 / #9090F2 på #16130F | 6,7 / 11,1 / 9,2 / 9,3 / 6,6:1 |

Alle over 4,5:1 (`accessibility.md › Vision`: «Strive to meet color contrast minimum
standards»). axe-core (color-contrast) kjøres i `fetcher/test_design_browser.py` på alle
sju skjermer, fire visninger: ingen brudd.

- **Trykkflater:** testen måler hver synlig knapp, minst 44 × 44 px (`accessibility.md ›
  Mobility`: «Offer sufficiently sized controls»). Funn under gjennomgangen: «?»-knappen
  ved grafen var 28 px. **Rettet:** 44 px treffflate med 28 px synlig ring.
- **Farge aldri alene** (`color.md › Inclusive color`): ratingen bæres av ord eller stjerner,
  dagbrikkene har ordet i `aria-label`/`title` og lengden på streken, kartmerkene viser ord
  eller stjerner pluss høyde.
- **Skjermleser:** hvert kort er én knapp med samlet `aria-label` (navn, rating, høyde, vind);
  stjerner har `aria-label` «n av 5 stjerner»; grafen har `role="img"` med tekstlig
  oppsummering og piltaster.
- **Tekststørrelser:** 13 / 15 / 17 / 22 / 32 px, aldri under 13 px (Apple: minimum 11 pt på
  mobil, 10 pt på PC - `typography.md › Ensuring legibility`). Ingen tynne vekter.
- **Bevegelse og gjennomsiktighet:** alle overganger ligger bak `prefers-reduced-motion:
  no-preference`; tabbarens blur slås av ved `prefers-reduced-transparency: reduce`.
- **Tastatur på PC:** alle kort, brikker, celler og knapper er ekte `<button>`; global
  `:focus-visible`-ring; grafen tar piltaster.

## Linse 2: plattformkonvensjoner

- **Tabbar** med fire faner, ett ord hver, alltid synlig, bare navigasjon
  (`tab-bars.md › Best practices`: «Use a tab bar to support navigation, not to provide
  actions»). «Logg» er flyttet fra en svevende verktøylinje til detaljsidens hode - en
  handling på innholdet, ikke en fane.
- **PC:** tabbaren blir en sidekolonne (84 px) med liste 400 px og detalj til høyre
  (`sidebars.md › Best practices`, «show no more than two levels»). Ingen kritisk handling
  nederst i kolonnen (`layout.md › Platform considerations`: «Avoid placing controls or
  critical information at the bottom of a window»).
- **Ark:** ett om gangen, gripefelt øverst, «Avbryt» ved siden av «Lagre økt»
  (`sheets.md › Best practices`: «Provide an alternative to the Done button»). På PC
  sentreres arket (560 px), som et skjema-ark.
  - *Middels, ikke gjort:* sveip ned for å lukke (`sheets.md › Mobile`: «Support swiping to
    dismiss a sheet»). Lukkes med «Avbryt»/«Lukk», bakgrunnstrykk og Escape. Runde 2.
- **Mørk modus** følger systemet, ingen egen bryter i appen (`dark-mode.md › Best
  practices`: «Avoid offering an app-specific appearance setting»).

## Linse 3: visuelt og håndverk

- **Én farge, én betydning:** ratingskalaen 0-5 brukes identisk i liste, dagbrikker,
  detalj, graf, kartmerker, klynger og skivas ring. Ingen annen bruk av disse fargene.
- **To skrifter:** Bricolage Grotesque (navn, ordmerke, ratingord) og Inter (alt annet,
  tabulære tall for høyder og klokkeslett). `typography.md › Conveying hierarchy`:
  «Minimize the number of typefaces».
- **Er det en mal?** Den varme kremflata med terrakotta-aksent er en kjent «generert» look.
  Her er den begrunnet: Theodors brief ba om varm råhvit, og terrakotta er ikke aksent, men
  ratingfargen for 1 stjerne, bundet til data. Aksentfargen brukes ikke på knapper eller
  navigasjon (`branding.md › Best practices`: «Apply your app's accent color judiciously»).
  Ordmerket viser seg én gang (toppen av lista) pluss som lite merke i PC-sidekolonnen -
  ikke gjentatt ellers («Resist the temptation to display your logo throughout your app»).
- **Fjern ett tilbehør:** «Best torsdag 09-10 …»-linja under varslingslinja er den eneste
  kandidaten. Beholdt fordi den svarer på spørsmålet «når bør jeg dra», men den kan flyttes
  inn i grafen i runde 2 (*lavt*).
- **Funn, rettet:** den valgte timens prikk over grafen kolliderte med dagnavnet («I dag»).
  Grafen har fått 8 px mer luft over stolpene.

## Linse 4: samhandling

- Grafen svarer på trykk/hold (mobil), hover (PC) og piltaster; valgt time vises med ramme
  og prikk, aldri bare farge.
- Varsler (gammelt varsel, blåst ut, treffer ikke, kildene uenige, kanten av vinduet …)
  er én linje med ikon og forklaring ved trykk - ingen alert-dialoger.
- Bilder: spotbilde vises bare hvis `docs/img/spots/<id>.jpg` finnes, ellers ingenting
  (ingen plassholder, ingen arkivbilder - Theodors regel).

## Linse 5: språk

Alle strenger i `docs/js/strings.js`, norsk, vanlig språk («Surfehøyde og sett», «Timen er
jevnet ut mellom to målepunkter»). Fagord (Hs, transfer, directness, kJ) ligger bak
«Detaljer» og forklaringsarkene.

## Står igjen (runde 2)

1. Sveip-for-å-lukke på arkene (middels).
2. «Best …»-linja kan bli en markering i grafen (lavt).
3. Dagnavnene på kartets tidslinje kan gjenta samme ukedag (to lørdager over 14 dager) -
   vurder dato ved gjentak (lavt).
4. Skjermbildene i denne mappa er tatt uten karttiler (Kartverket er ikke tilgjengelig fra
   testmiljøet) - kartets bakgrunn vises bare som flate.
