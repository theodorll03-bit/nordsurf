# Blind validering av koordinatjakten på de 8 kjente (ROADMAP K del A2 punkt 5, 16.10.2026)

Kjørt med `python tools/koordinat_bevis.py --blind …` og `python tools/koordinatjakt.py --blind …`. Startpunktet er Kartverkets stedsnavn (hovednavnet foran aliaser, strand/sand/vik foran bygd), aldri listepinnen: for de 8 er listepinnen i praksis vår egen nål (1-5 m unna, unntatt Unstad 33 m og Farstadsanden 320 m), så den kan ikke brukes blindt. spots.json leses først når avstandene regnes ut.

**Resultat: 1 av 8 innenfor 100 m, 4 over 300 m. Kravet (minst 6 av 8 innenfor 100 m, ingen over 300 m) er IKKE oppfylt - A2 er STOPPET etter planen; de 108 er ikke kjørt.**

| Spot | Avstand til nålen | Sikkerhet | Metode | Grunnlag |
|---|---|---|---|---|
| russelv | 75 m | B | vannkant nærmest stedsnavnet | ingen strand/odde funnet - nærmeste vannkant |
| lenangsoyra | 3747 m | C | vannkant nærmest stedsnavnet | ingen strand/odde funnet - nærmeste vannkant |
| grotfjord | 128 m | B | beachbreak: midt på strandas sjøkant (OSM) → 100 m ut | OSM-strand (beach, sjøkant 619 m) |
| tromvik | 1259 m | C | vannkant nærmest stedsnavnet | ingen strand/odde funnet - nærmeste vannkant |
| steinkrossa | 1798 m | B | vannkant nærmest stedsnavnet | ingen strand/odde funnet - nærmeste vannkant |
| ersfjordstranda | 332 m | B | beachbreak: midt på strandas sjøkant (OSM) → 100 m ut | OSM-strand «Ersfjord beach» (beach, sjøkant 1400 m) |
| unstad-beach | 112 m | B | vannkant nærmest stedsnavnet | ingen strand/odde funnet - nærmeste vannkant |
| farstadsanden | 129 m | B | beachbreak: midt på strandas sjøkant (OSM) → 100 m ut | OSM-strand «Farstadsanden» (beach, sjøkant 1293 m) |

## Hva som trolig er feil
1. **Stedsnavnets punkt er ofte ikke surfestranda.** «Steinkrøssa» (Strand i sjø) har representasjonspunkt 1,8 km fra nålen; Lenangsøyra finnes bare som bygdelag (3,7 km); Tromvik som bygd/vik. Uten listepinnen er navnet alene et for grovt startpunkt.
2. **OSM mangler strandpolygoner i Troms og Lofoten.** Bare 3 av de 8 nålene har en OSM-strand (natural=beach/sand) innen 600 m - Russelv, Lenangsøyra, Tromvik, Steinkrøssa og Unstad har ingen. Da faller metoden tilbake til «nærmeste vannkant», som gir rett side av fjorden, men ikke rett strand.
3. **Hvor på stranda kan ikke avgjøres uten flyfoto.** Der OSM-stranda finnes, havner forslaget 112-332 m fra nålen: metoden tar midten av sjøkanten, mens nålene står ved hovedtoppen (20 %, 46 % og 81 % langs stranda). Norge i bilder er ikke åpent (krever innlogging), så skumlinjer og rev kan ikke ses.
4. **Avstanden ut er ikke én konvensjon** (24-153 m) - gir 50-100 m feil i seg selv.

## Forslag til Theodor
- For de 108 bør listepinnen være utgangspunktet - ikke fordi den er bevist god (at pinnen treffer for de 8 er sirkulært: der er den i praksis vår egen nål, og Farstadsanden-pinnen er 320 m unna), men fordi metoden ikke slår den. Mange av pinnene er merket «estimated» i lista. Metoden kan flytte pinnen til nærmeste vannkant/OSM-strand, men valideringen viser ikke at det er bedre - så det bør ikke gjøres automatisk.
- **Sikkerhetsgraden A/B/C er ikke validert:** Steinkrøssa (1 798 m feil) og Ersfjordstranda (332 m) fikk B, som de som traff. Retningskjennetegnet slår til også når punktet er feil.
- Raskest og sikrest: gå gjennom kandidatene med flyfoto (Norgeskart/Google-lenkene i `tools/koordinatsjekk/`) og flytt pinnen selv. Siden er bygget og trenger bare en `posisjoner.json` med listepinnene som utgangspunkt - si fra om du vil ha den laget slik.
