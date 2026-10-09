/* Nordsurf: alle tekster i appen samlet (designrunde 1, punkt 6). Vanlig
   språk i standardvisningen, fagbegrepene bak forklaring ved trykk
   (js/explain.js) og under "Detaljer". Vanlig <script>, ikke modul -
   index.html (js/app.js) og js/map.js leser STR rett fra samme vindu.

   Ingen tall regnes her - bare ord. Tallene kommer alltid fra forecast.json
   slik fetcher/rating.py skrev dem. */
(function(){
  const STR = {
    app: "Nordsurf",
    tabs: {varsel:"Varsel", kart:"Kart", logger:"Logger", innstillinger:"Innstillinger"},
    loading: "Henter varsel…",
    noData: "Fant ikke varseldata. Kjør henteren (fetcher/fetch.py) eller vent på neste automatiske kjøring.",
    sample: "Oppdiktet vær, ikke dagens varsel. Dette er bare for å vise hvordan appen ser ut.",
    updated: (day, time) => `Oppdatert ${day} kl. ${time}`,
    stale: (day, time) => `Varselet er ikke oppdatert siden ${day} kl. ${time}`,
    staleMore: "Henteren har trolig feilet. Tallene kan være utdaterte.",
    exampleSub: "Eksempel, ikke ekte data",

    /* rating: ord for 0-5 stjerner, og de fire ordene for 0-1 stjerne */
    starWords: ["Flatt","Dårlig","Ok","Bra","Veldig bra","Rått"],
    pickWords: ["Flatt","Dårlig","Ok","Bra","Topp","Rått"],
    lowReason: {flat:"Flatt", blown_out:"Blåst ut", stormsjo:"Stormsjø", treffer_ikke:"Treffer ikke"},
    starsAria: (n, faded) => `${n} av 5 stjerner` + (faded ? `, ${faded} tapt på vind eller tidevann` : ""),
    whyRating: "Hvorfor denne ratingen? Trykk for forklaring",
    lostTo: (wind, tide) => {
      const parts = [];
      if(wind) parts.push(`vinden tar ${wind}`);
      if(tide) parts.push(`tidevannet tar ${tide}`);
      return parts.join(" og ");
    },
    worth: (n) => `Svellet er verdt ${n}, men `,

    /* høyde, vind */
    height: (a, b) => b!=null && b!==a ? `${a} til ${b} m` : `${a} m`,
    heightSets: "surfehøyde og sett",
    noHeight: "–",
    wind: {offshore:"offshore", side:"sidevind", sideonshore:"side-onshore", onshore:"onshore"},
    windCalm: "blankt", windNearCalm: "nesten blankt",
    windAria: (speed, dir, type) => `vind ${speed} meter per sekund fra ${dir}, ${type}`,

    /* dagbrikker */
    daysAria: "Kommende dager",
    dayChipAria: (day, word) => `${day}: ${word}`,
    darkAll: "mørkt hele dagen",

    /* detaljside */
    backToList: "Varsel",
    log: "Logg",
    logSession: "Logg økt",
    fromPhoto: "Fra bilde",
    details: "Detaljer",
    chartTitle: "Surfehøyde time for time",
    chartHelp: "Slik leser du grafen",
    chartHelpText: "Hver søyle er én time. Høyden er surfehøyden (ved blåst ut eller stormsjø: totalhøyden ved spoten), fargen er ratingen (grå 0 stjerner, rød dårlig, gul ok, grønn bra, turkis veldig bra, blå rått). Den tynne streken over søylen er settene. En lav grå strek er en flat time, en stiplet strek betyr at tallet mangler. Bakgrunnen viser dag, skumring og mørke. Lyse søyler lenger ut er anslag fra reservemodellen og langtidsvarselet. Trykk på en søyle for tallene for den timen. Piltastene flytter mellom timer.",
    transferSub: "andel av svellhøyden ute som når spoten ved direkte treff",
    kjUnderOne: "under 1 kJ",
    flatAllDay: "Flatt hele døgnet",
    flatNext: (n)=>`Flatt de neste ${n} timene`,
    flatRest: "Flatt resten av varselet",
    kjEstimateSub: "anslag: svellet er ikke skilt ut, regnet fra totalhøyden",
    reports: "Rapporter fra andre",
    bestNone: "Ingen brukbare vinduer de neste tre dagene",
    bestNoLight: "Ingen data i lyse timer",
    best: (day, from, to, n) => `Best ${day} ${from}–${to}, ${n} ${n===1?"stjerne":"stjerner"}`,
    estimate: "anslag", longrange: "langtid", confident: (p) => `${p} % sikker`,

    /* advarsler i vanlig språk (én linje, forklaring ved trykk) */
    notice: {
      disagree: "Kildene er uenige, usikkert varsel",
      blown_out: "Sterk vind ødelegger bølgene",
      stormsjo: "Mest vindsjø, lite ekte svell",
      treffer_ikke: "Svellet kommer fra feil retning",
      lowEnergy: "For lite energi i svellet",
      edge: "Svellet kommer i kanten av vinduet",
      uncertain: "Usikkert varsel",
      farAhead: "Usikkert så langt frem",
      bwLee: "BarentsWatch-punktet ligger i le",
      interpolated: "Timen er jevnet ut mellom to målepunkter",
      stale: "Varselet er ikke oppdatert",
    },

    /* celler under Detaljer */
    cell: {
      surf:"Surfehøyde", hs:"Høyde på spoten", swell:"Svell ute", energy:"Energi", share:"Svellandel", direction:"Retningstreff",
      exposure:"Transfer", windsea:"Sekundært svell", period:"Periode", wind:"Vind", tide:"Tidevann", light:"Lys", temps:"Vann og luft",
      sources:"Kilder", confidence:"Sikkerhet", shelter:"Skjerming", localRules:"Lokale regler", calibration:"Kalibrering",
    },
    fromDir: (c) => `fra ${c}`,
    ofTotal: (m, pct) => `av ${m} m totalt (${pct} %)`,
    totalFallback: "svell ikke skilt ut, bruker total",
    inWindow: "Midt i vinduet", edgeWindow: "I kanten av vinduet", outWindow: "Utenfor vinduet",
    window: (w) => `Vindu ${w}`,
    tideNow: (rising, state) => `${rising?"Stigende":"Fallende"}, ${state}`,
    tideNext: (type, time) => `${type} kl. ${time}`,
    tidePref: (list) => list && list.length ? `Spoten liker ${list.join(" og ")} vann` : "Spoten tåler alt tidevann",
    lightNone: "Mørkt hele dagen", lightSub: (sun) => sun ? "Fra skumring til skumring" : "Mørketid, bare skumring", lightUsable: "Brukbart lys",
    temps: (water, air) => `${water} i vannet, ${air} i lufta`,
    notThisFar: "ikke tilgjengelig så langt frem",
    confidenceSub: (measured, day, zone) => `${measured?"Målt treff innenfor én stjerne":"Anslag"}, ${day} ${day===1?"dag":"dager"} frem · ${zone}`,
    zone: {langtid:"langtid (GFS)", reserve:"reservemodell", barentswatch:"BarentsWatch"},
    gust: (g) => `kast ${g}`,
    windSmoothed: "vind jevnet ut", windGfs: "GFS-vind (langtid)",
    bwMax: (m) => `BarentsWatch venter opp til ${m} m`,
    interpolated: "jevnet ut",
    missing: "mangler",

    /* loggark */
    sheet: {title:"Logg økt", cancel:"Avbryt", spot:"Spot", when:"Når", type:"Type", own:"Egen økt", observed:"Observert",
      source:"Kilde (valgfritt)", sourcePh:"f.eks. Instagram, Lofoten Surfsenter", howGood:"Hvor bra var det?", size:"Størrelse (valgfritt)",
      wind:"Vind (valgfritt)", save:"Lagre økt", photoHint:"Velg et bilde, så fylles tidspunktet inn fra bildet.", photoBtn:"Hent tidspunkt fra bilde"},
    toast: {logged:"Økt logget", logFail:"Kunne ikke lagre. Sjekk at nettleseren tillater lagring.", loginForFav:"Logg inn for å lagre favoritter", login:"Logg inn",
      favFail:(m)=>`Kunne ikke lagre favoritt: ${m}`, photoNoDate:"Fant ikke tidspunkt i bildet - sett tidspunktet selv.", photoDate:(d)=>`Tidspunkt hentet fra bildet: ${d}`},
    witness: {title:"Var du der?", skip:"Ikke jeg", sub:(spot, day, hour, stars)=>`${spot}, ${day} kl. ${hour} - varselet viste ${stars} av 5 stjerner.`, thanks:"Takk! Lagret som økt."},
    breakdownTitle: "Hvorfor denne ratingen?",
    explainClose: "Lukk",
    thisHour: "Denne timen", howComputed: "Slik regnes det ut",
  };
  window.STR = STR;
})();
