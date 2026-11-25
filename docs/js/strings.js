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
    staleHours: (n) => `Varselet er ${n} ${n === 1 ? "time" : "timer"} gammelt`,
    staleFormat: "Varselet har et eldre format enn appen.",
    staleFormatMore: "Henteren har trolig feilet etter en oppdatering - tallene vises når neste varsel er hentet.",
    exampleSub: "Eksempel, ikke ekte data",

    /* rating: ord for 0-5 stjerner, og de fire ordene for 0-1 stjerne */
    starWords: ["Flatt","Dårlig","Ok","Bra","Veldig bra","Rått"],
    poeng: "poeng",   // ordet for vurderingen i «Hvorfor» (henteren skriver «stjerner» i regnestykket, appen sier poeng)
    pickWords: ["Flatt","Dårlig","Ok","Bra","Topp","Rått"],
    lowReason: {flat:"Flatt", blown_out:"Blåst ut", stormsjo:"Stormsjø", treffer_ikke:"Treffer ikke"},
    // 0 stjerner med årsak «flat» (Theodors ja 09.10.2026, begge runder): ordet
    // etter surfehøyden - under 0,3 m «Flatt», 0,3 til under 0,8 m «Smått»,
    // 0,8 m eller mer «Grøtete». Bare visningsordet, aldri stjernene.
    wordSmall: "Smått",
    // Fra 0,8 m (Theodors regel 09.10.2026, tredje runde): ordet følger det
    // som faktisk trekker mest - se zeroWord() i app.js.
    wordMushy: "Grøtete",
    wordTide: "Feil tidevann",
    wordLittleSwell: "For lite svell",
    wordNotNow: "Ikke surfbart nå",
    wordUncertain: "Usikkert",
    // Sterk fralandsvind som tar poengene heter ikke «Blåst ut» (Theodor S15 a, 17.11.2026) - se windLossWord() i app.js
    wordTooMuchWind: "For mye vind",
    wordExplain: {
      "Smått": "Litt bølger, men for lite til ett poeng.",
      // Grøtete har to tekster etter perioden (Theodor 09.10.2026, fjerde runde), se mushyShort/mushyLong
      "Grøtete": "Bølgene er der, men kort periode og lite energi gjør dem svake.",
      "Usikkert": "Kildene er uenige om svellet når inn til spoten.",
      "Blåst ut": "Bølgene er der, men vinden ødelegger dem.",
      // egen forklaring (Theodor S21 b, 20.11.2026). Ikke «Fralandsvinden …»: ordet brukes også når retningen er ukjent
      "For mye vind": "Vinden er for sterk.",
      "Feil tidevann": "Bølgene er der, men tidevannet passer ikke spoten nå.",
      "Ikke surfbart nå": "Bølgene er der, men flere ting trekker ned uten én tydelig hovedårsak. Se regnestykket under.",
    },
    mushyShort: "Bølgene er der, men kort periode og lite energi gjør dem svake.",
    mushyLong: "Bølgene er der, men for lite energi i svellet til å gi kraft.",
    notNowCap: "Bølgene er der, men varselet er usikkert (f.eks. ingen BarentsWatch-retning, svell utenfor vinduet, stor dreining eller svellet anslått fra totalhøyden), så ratingen er kappet. Se regnestykket under.",
    notNowLow: "Bølgene er der, men svellet gir for lite til ett poeng. Se regnestykket under.",
    // Kilden til en lokal regel, slik den står i spots.json (local_rules.source),
    // omskrevet til forklaringstekst. En kilde som ikke er en person skal aldri
    // skrives som en person (Theodor 09.10.2026).
    localSourceText: {
      "Magnus, lokal surfer (Molde)": "Ifølge Magnus, lokal surfer",
      "Observasjoner 26.09-05.10.2026": "Grense satt ut fra observasjonene 26.09 til 05.10",
      "Lofoten Surfsenter, 09.11.2026": "Ifølge Lofoten Surfsenter",
      "Observasjoner 17.11 og 22.11.2026": "Grense satt ut fra observasjonene 17.11 og 22.11",
    },
    // overskriften til «Lokale regler» når tidevannsregelen har egen kilde (local_rules.tide_source)
    localSourcesBoth: (src, tideSrc)=>`${src}; tidevann: ${tideSrc}`,
    localSourceFallback: (src)=> /observasjon|logg|kalibrer|grense/i.test(src) ? `Grense satt ut fra ${src.charAt(0).toLowerCase()}${src.slice(1)}` : `Ifølge ${src}`,
    localEnergyExplain: (kj, full)=>`for lite svellenergi ute (${kj} kJ, full uttelling fra ${full} kJ).`,
    localWindExplain: (spotName, now)=>`${spotName} trenger fralandsvind. Nå ${now}.`,
    starsAria: (n, faded) => `${n} av 5` + (faded ? `, ${faded} tapt på vind eller tidevann` : ""),
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
    // fralands, pålands og sidevind (SPEC §8, Theodor 16.11.2026). Skrå pålandsvind (45–80° fra stranda) heter «skrått pålands»
    // overalt, også i «Hvorfor» (S42 b, svar.md 24.11.2026 kl. 22.25; før sto den som «pålands»). Samme ord som
    // WIND_TYPE_WORD i fetcher/rating.py.
    wind: {offshore:"fralands", side:"sidevind", sideonshore:"skrått pålands", onshore:"pålands"},
    // loggene lagrer fortsatt «Offshore»/«Onshore» (gamle økter skal leses likt); bare ordet på skjermen er byttet
    logWind: {"Offshore":"Fralands", "Onshore":"Pålands"},
    reportWind: {offshore:"Fralands", onshore:"Pålands", side:"Sidevind", stille:"Stille"},
    windCalm: "blankt", windNearCalm: "nesten blankt",
    windShort: {"nesten blankt":"lett", "sidevind":"side"},  // kortene i lista - "lett" (1,5-3 m/s) er ikke "blankt" (fysikk-kontrollør 09.10.2026)
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
    chartHelpText: "Hver søyle er én time. Høyden er surfehøyden (ved blåst ut eller stormsjø: totalhøyden ved spoten), tallet over søylen er vurderingen fra 0 til 5 (korall fra 4). Mørke timer er skygget og får ikke tall. Den tynne streken over søylen er settene. En lav grå strek er en flat time, en stiplet strek betyr at tallet mangler. Bakgrunnen viser dag, skumring og mørke. Lyse søyler lenger ut er anslag fra reservemodellen og langtidsvarselet. Trykk på en søyle for tallene for den timen. Piltastene flytter mellom timer.",
    transferSub: "andel av svellhøyden ute som når spoten ved direkte treff",
    // merkelappen ved navnet: ny spot (status «forelopig») eller en andel som er satt uten observasjon (andel_forelopig)
    forelopig: "Foreløpig",
    kjUnderOne: "under 1 kJ",
    flat:   { allDay: "Flatt hele døgnet", next: (n)=>`Flatt de neste ${n} timene`, rest: "Flatt resten av varselet" },
    small:  { allDay: "Smått hele døgnet", next: (n)=>`Smått de neste ${n} timene`, rest: "Smått resten av varselet" },
    noSurf: { allDay: "Ingen surf hele døgnet", next: (n)=>`Ingen surf de neste ${n} timene`, rest: "Ingen surf resten av varselet" },
    kjEstimateSub: "anslag: svellet er ikke skilt ut, regnet fra totalhøyden",
    reports: "Rapporter fra andre",
    bestNone: "Ingen brukbare vinduer de neste tre dagene",
    bestNoLight: "Ingen data i lyse timer",
    best: (day, from, to, n) => `Best ${day} ${from}–${to}, ${n} poeng`,
    estimate: "anslag", longrange: "langtid", confident: (p) => `${p} % sikker`,

    /* Hjem på mobil (design B 4.0, SPEC §6A): topplinja, overskriften av to korte setninger og favorittradene.
       Setningene settes sammen av vurderingsordet (ratingWord), spotnavnet og dagen - samme dagstall som lista viser.
       Malene er godkjent av Theodor 16.11.2026. */
    hjem: {
      lys: (a, b) => `Lys ${a}–${b}`, lysHele: "Lys hele døgnet",   // midnattssol (Theodor 16.11.2026)
      fra: (sted) => `Fra ${sted}`,
      ordSpot: (ord, spot, dag) => `${ord} på ${spot} ${dag}.`,
      // S40 (feiljegeren 25.11.2026, V1): en time regnet med lang sjø (long_sea) er usikker. Ordet følger med ut av
      // spotsiden: «Bra på Unstad i dag, usikkert.», «Nå Bra, usikkert», og «Usikkert varsel.» etter tallene i setningen.
      usikkert: "usikkert",
      ord: (ord, dag) => `${ord} ${dag}.`,
      ingen: (dag) => `Ingen surf ${dag}.`,
      ingenNeste: (n) => `Ingen surf de neste ${n} dagene.`,
      morktNeste: (n) => `Mørkt de neste ${n} dagene.`,   // mørketid: dagene har ingen lyse timer, så «ingen surf» er ikke kjent
      ingenRest: "Ingen surf resten av dagen.",
      morkt: (dag) => `Mørkt ${dag}.`,
      manglerDag: (dag) => `Mangler data ${dag}.`,
      best: (a, b) => `Best kl. ${a}–${b}.`,
      obs: "Obs", rediger: "Rediger", ferdig: "Ferdig", fjern: "Fjern", leggTil: "Legg til spot",
      fjernAria: (spot) => `Fjern ${spot} fra favoritter`,
      kjoreAria: (tid, sted) => `${tid} fra ${sted}`,
      ca: "ca.",   // foran kjøretiden: tallene er anslag (Theodors stedfortreder 16.11.2026)
      kartKilde: "Kart: GSHHS",   // kystlinja i det kompakte kartet (docs/geo/coast.json)
      innstillinger: "Innstillinger",
      // «FRA TROMSØ ▾» øverst på mobil-Hjem åpner Innstillinger (designrevisjonen fase 2 punkt 5): det skjermleseren sier
      fraAria: (sted) => `Fra ${sted}. Innstillinger`,
      // lyset er over for alle spotene i lista: lista viser i morgen, og det står én gang over den (fase 2 punkt 1)
      morktNa: "Mørkt nå. Tallene gjelder i morgen.",
      spotsI: (region) => `Spots i ${region}`, ingenSpots: (region) => `Ingen spots i ${region} ennå.`, region: "Region",
      // ordet i metalinja når dagen ikke har noe tall, og det som er tapt på vind og tidevann
      forbud: "Surfing forbudt", morktOrd: "Mørkt", over: "Dagens lys er over", mangler: "Mangler data",
      taptVind: (n) => `−${n} vind`, taptTide: (n) => `−${n} tidevann`, apne: "Åpne spoten",
    },

    /* Spotsiden på mobil (design B 4.0, SPEC §6B). Etikettene settes i versaler av CSS. De siste linjene er
       VoiceOver-tekstene til timestripa (aria-valuetext), tidevannskurven og skiva (SPEC: «ta dem med»). */
    spot: {
      tilbake: "Tilbake", tilbakeTil: (sted) => `Tilbake til ${sted}`, fra: {hjem: "Hjem", utforsk: "Utforsk", logger: "Logger"},
      bildeAlt: (spot) => `Satellittbilde av ${spot} ovenfra, nord opp`,
      best: "Best", lys: "Lys", luft: "Luft", vann: "Vann", oppdatert: "Oppdatert",
      bildet: "Bildet",   // foran hele krediteringen for kornfotoet, nederst under Kilder
      // «Svell ute» og ikke «Svell»: tallet er svellet ute (swell_offshore), ikke bølgene på stranda (Theodor S20 a, 20.11.2026)
      kl: (hh) => `Kl. ${hh}`, svell: "Svell ute", surf: "Surf", vind: "Vind", tidevann: "Tidevann",
      // S40 (svar.md 24.11.2026): timer der ratingen har regnet lang sjø som svell (feltet long_sea, i dag bare Unstad).
      // Tallet er da den lange sjøen værmodellen kaller vindsjø, ikke svell-delen. Timen er usikker (høyst 3 poeng).
      langSjo: "Lang sjø ute", langSjoFra: "Lang sjø fra", langSjoNote: "Regnet som svell. Usikkert varsel.",
      timeLangSjo: (m) => `Lang sjø ute ${m} m, regnet som svell, usikkert`,
      mangler: "mangler data", hoy: "høy", lav: "lav", snur: "snur",
      svellSub: (s, retning, grader) => `${s} s · fra ${retning} ${grader}°`,
      timeForTime: "Time for time", naa: "Nå", velgTime: "Velg time", velgDag: "Velg dag", tilbakeNa: "Tilbake til nå",
      retning: (hh) => `Retning kl. ${hh}`, svellFra: "Svell fra", vindFra: "Vind fra", vindu: "Vindu",
      timeAria: (hh, dom, rest) => `kl. ${hh}, ${dom}${rest ? ". " + rest : ""}`,
      timeTall: (n, tapt) => `${n} av 5${tapt ? ", " + tapt : ""}`,
      timeTapt: (n, hva) => `${n} tapt på ${hva}`, timeMork: "mørkt, ingen vurdering", timeMangler: "mangler data", timeBest: "beste vindu",
      timeSvell: (m) => `Svell ute ${m} m`, timeVind: (ms, ord) => `vind ${ms}${ord ? " " + ord : ""}`,
      stiger: "stigende", synker: "synkende",
      timeTide: (m, stiger) => `tidevann ${m} ${stiger ? "stigende" : "synkende"}`,
      tideAria: (deler, pref) => `Tidevann: ${deler.join(", ")}.${pref ? " " + pref + "." : ""}`,
      tideLav: (kl, m) => `lavvann ${kl}, ${m} meter`, tideHoy: (kl, m) => `høyvann ${kl}, ${m} meter`,
      skiveAria: (spot, hh, svell, vind) => `${spot} kl. ${hh}: ${svell}.${vind ? " " + vind + "." : ""}`,
      // S40: timen er regnet med lang sjø (long_sea) - skjermleseren skal ikke kalle den svell
      skiveLangSjo: (grader, inne, vindu) => `lang sjø fra ${grader} grader, regnet som svell, ${inne ? "innenfor" : "utenfor"} svellvinduet ${vindu}`,
      langSjoRegnet: "Regnet som svell", langSjoRegnetV: "ja, usikkert (høyst 3 poeng)", langSjoGfs: "Svelldelen i værmodellen",
      langSjoHow: "Værmodellen (GFS Wave) kaller denne sjøen vindsjø. Den er lang, kommer fra havsiden, og kystmodellen ved stranda viser lange bølger rett inn. Derfor er den regnet som svell her. Det er et anslag, så timen er usikker.",
      skiveSvell: (grader, inne, vindu) => `svell fra ${grader} grader, ${inne ? "innenfor" : "utenfor"} svellvinduet ${vindu}`,
      skiveSvellMangler: "svell mangler data", skiveVind: (retning, ord) => `Vind fra ${retning}${ord ? ", " + ord : ""}`,
      vinduTil: (a, b) => `${a} til ${b}`,
    },

    /* Nettsiden fra 1024 px (design B 4.0 steg 6, SPEC §6C spotsiden og §6D forsiden «Beste i dag»).
       FORELØPIG: ordene i denne blokka er tatt fra skissene eller foreslått av Claude, og venter på Theodors ja
       (lista står i privat/design-b4/steg-6/nettside-steg6.md, «Ord som mangler»). Ord som fantes fra før
       (Svell fra, Vind, Tidevann, Lys, Oppdatert, Best, Mørkt …) hentes fra STR.spot og STR.hjem. */
    web: {
      morketid: "Mørketid",                      // temaknappen i toppen (SPEC §6C punkt 1)
      lagreFav: "Lagre som favoritt", fjernFav: "Fjern fra favoritter",
      neste7: "Neste 7 dager", usikre: "Dag 4–7 er usikre",
      uke2: "Uke 2 · usikker",                   // etiketten foran dag 8 og utover på spotsiden (designrevisjonen 21.11.2026)
      timeForTime: (dag) => `${dag} time for time`, holdMusa: "Hold musa over en time",
      rader: {kl: "Kl.", vurdering: "Vurdering", tideSub: "over sjøkartnull"},
      spotten: "Spotten", omSpotten: "Om spotten",
      fig: (n, navn) => `Fig. ${n} · ${navn}, nord opp.`,
      kartOsm: "Kart: © OpenStreetMap-bidragsytere",
      om: {vender: "Vender mot", hoyde: "Best høyde", data: "Data"},
      varselFra: (dag, kl) => `Varsel fra ${dag} kl. ${kl}`,
      antall: (n) => `${n} ${n === 1 ? "spot" : "spots"}`,
      tallFra: "Tall fra 0 til 5", bareLyse: "Bare lyse timer",
      kol: {nr: "#", spot: "Spot", best: "Best", svell: "Svell ute", timer: "06–18", region: "Region"},
      nr: (n) => String(n).padStart(2, "0"),
      // overskriften over tabellen og linja på hovedbildet følger dagen som er valgt (Theodor S20 b, 20.11.2026): tallene er
      // dagens beste, ikke nå-timen. «Beste» for alle dager, også «Beste fredag» (Theodor S25, 22.11.2026).
      bestDag: (dag) => `Beste ${dag}`,
      visAlle: (n) => `Vis alle ${n}`, apneKart: "Åpne kartet",
      alle: "Alle", dag: "Dag", region: "Region",
      perRegion: "Beste tall per region og dag", perSpot: "Beste tall per spot og dag",
      tegn: {hoy: "4–5", tre: "3", lav: "1–2", null: "0"},
      bunn: "Surfevarsel for norskekysten. Laget i Tromsø.", kilder: "Kilder",
      kildeListe: ["BarentsWatch (kystmodell 100 m)", "MET Norge", "Open-Meteo", "Kartverket"],   // samme kilder som linja nederst på spotsiden
    },

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
    inWindow: "Innenfor vinduet", edgeWindow: "I kanten av vinduet", outWindow: "Utenfor vinduet",
    window: (w) => `Vindu ${w}`,
    tideNow: (rising, state) => `${rising?"Stigende":"Fallende"}, ${state}`,
    tideNext: (type, time) => `${type} kl. ${time}`,
    tidePref: (list) => list && list.length ? `Spoten liker ${list.join(" og ")} vann` : "Spoten tåler alt tidevann",
    tideLowBest: "Best på lavt vann",   // spoten har en regel på vannstanden: jo lavere, jo bedre (local_rules.tide_level, Theodor 23.11.2026, S28)
    lightOnly: "Bare lyse timer får tall",
    lightNone: "Mørkt hele dagen", lightSub: (sun) => sun ? "Fra skumring til skumring" : "Mørketid, bare skumring", lightUsable: "Brukbart lys",
    temps: (water, air) => `${water} i vannet, ${air} i lufta`,
    notThisFar: "ikke tilgjengelig så langt frem",
    confidenceSub: (measured, day, zone) => `${measured?"Målt treff innenfor ett poeng":"Anslag"}, ${day} ${day===1?"dag":"dager"} frem · ${zone}`,
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
    witness: {title:"Var du der?", skip:"Ikke jeg", sub:(spot, day, hour, stars)=>`${spot}, ${day} kl. ${hour} - varselet viste ${stars} av 5 poeng.`, thanks:"Takk! Lagret som økt."},
    // Logger (designrevisjonen fase 2 punkt 3): tom tilstand står én gang per seksjon. Gjelder setningen bare noen av
    // spotene, står navnene (eller antallet) foran
    logger: {noen: (navn) => `${navn}:`, antall: (n) => `${n} spots:`},
    breakdownTitle: "Hvorfor denne ratingen?",
    explainClose: "Lukk",
    thisHour: "Denne timen", howComputed: "Slik regnes det ut",
    // S37 (svar.md 24.11.2026 kl. 10.25): timer der høyden er svell ute × andelen gjennom gapet (fjord-spots, share_height).
    // gapHow er «Slik regnes det ut» for høyden (ordrett fra svaret), gapAndel står etter andelen under «Eksponering denne timen»
    gapHow: "Svell ute × andelen som kommer gjennom gapet. Anslag, ikke kystmodellens tall.",
    gapAndel: "andel gjennom gapet",
  };
  window.STR = STR;
})();
