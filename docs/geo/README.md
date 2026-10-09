# Kystlinje for kartet

`coast.json` er en forenklet kystlinje for Nord-Norge (fra GSHHS, Global
Self-consistent Hierarchical High-resolution Shorelines, Wessel og Smith,
LGPL), levert av Theodor sammen med designskissen «kart først» (09.10.2026,
se docs/design/kart-forst/). Feltene: `bbox` [vest, sør, øst, nord] i grader,
`vw`/`vh` kartrommets størrelse (1000 × 844), `d` én SVG-sti (Mercator
innenfor bbox). Appen projiserer spotene inn i samme rom (js/kart.js).

Kartet virker uten nett (fila ligger i sw.js sin precache). Kartfliser fra
Kartverket kan komme tilbake som valg senere. En versjon med høyere
oppløsning kan lages fra GSHHS med samme format.
