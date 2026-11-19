# Spotbilder

Legg et eget bilde av spoten her som `<spot-id>.jpg` (samme id som i spots.json,
f.eks. `unstad.jpg`). Appen viser det øverst på detaljsiden og som et lite
bilde i lista. Mangler fila, vises ingenting - ingen plassholder, ingen
arkivbilder. Bruk bare egne bilder (eller bilder med tydelig tillatelse).

Anbefalt: liggende format, ca. 1600 px bredt, under 300 kB.

## Kornfoto (laget av verktøyet)

`<spot-id>-trykk.jpg`, `<spot-id>-lodd.jpg` og de to `-skive.jpg`-filene er laget av
`tools/spotbilder.py` fra Kartverkets skyfrie Sentinel-2-mosaikk (CC BY 4.0) og skal ikke
redigeres for hånd. `kilder.json` sier hvor hvert bilde kommer fra, og `docs/js/spotbilder.js`
(også skrevet av verktøyet) sier hvilke spots som har bilde og hva som står i krediteringen.

- Trykk er dagversjonen (lyst tema), Lodd er mørketidsversjonen (mørkt tema).
- `-skive` er det kvadratiske utsnittet under retningsskiva på spotsiden.
- Krediteringen må stå under bildet der det vises. Den fulle teksten står på spotsiden,
  kortformen under skiva.
- Ny spot: `python3 tools/spotbilder.py <spot-id> --varianter header,skive`. Hemmelige spots
  lages aldri.
- Andre kilder er ikke lov her: verken EOxCloudless (CC BY-NC-SA) eller Norge i bilder.
