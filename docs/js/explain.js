/* Nordsurf: felles forklaringsbibliotek (ROADMAP oppgave D, "Trykk for
   forklaring"). ÉN fil med alle tekstene, brukt av lista, detaljsiden og
   kartet. Hver forklaring har tre deler, i samme rekkefølge som ROADMAP
   ber om: (a) hva det betyr, kort og enkelt, med et eksempel; (b) tallene
   for akkurat denne spoten og timen; (c) hvordan det er regnet ut, og
   hvilke kilder. Vanlig <script>, ikke modul - index.html og map.js bruker
   EXPLAIN/openExplain() rett fra samme vindu.

   Tallene (b) og regnekjeden (c) leses fra samme felt som rating.py skriver
   til forecast.json - ingen egne beregninger her, bare visning (samme
   regel som breakdown-arket: appen regner ALDRI stjerner selv). Mangler et
   felt, vises "mangler" - aldri 0 (CLAUDE.md sin grunnregel). */
(function(){
  const nf1 = new Intl.NumberFormat("nb-NO",{maximumFractionDigits:1, minimumFractionDigits:1});
  const nf0 = new Intl.NumberFormat("nb-NO",{maximumFractionDigits:0});
  const m = v => v==null ? "mangler" : `${nf1.format(v)} m`;
  const s = v => v==null ? "mangler" : `${nf0.format(v)} s`;
  const pct = v => v==null ? "mangler" : `${nf0.format(v*100)} %`;
  const deg = v => v==null ? "mangler" : `${Math.round(v)}°`;
  const kj = v => v==null ? "mangler" : `${nf0.format(v)} kJ`;
  const compass = (d) => {
    if(d==null) return "–";
    const n=["N","NNØ","NØ","ØNØ","Ø","ØSØ","SØ","SSØ","S","SSV","SV","VSV","V","VNV","NV","NNV"];
    return n[Math.round(((d%360)+360)%360/22.5)%16];
  };
  const WIND_WORD = {offshore:"offshore", side:"sidevind", sideonshore:"side-onshore", onshore:"onshore"};
  const SOURCE_WORD = {barentswatch:"BarentsWatch (kystmodell, 100 m)", svell_ute:"reservemodellen (svell ute × transfer × eksponering)", metno_korrigert:"met.no sin totalhøyde på spoten, justert"};

  // low_reason-ordet som i resten av appen (LOW_REASON_WORD i app.js), aldri "blown out"
  const lowWord = (k) => (typeof LOW_REASON_WORD !== "undefined" && LOW_REASON_WORD[k]) || k;
  const EXPLAIN = {
    surf_height: {
      title: "Surfehøyde",
      what: "Høyden der bølgene brekker - det du faktisk ser fra stranda. Langt svell reiser seg mye mer på grunt vann enn kort svell med samme høyde ute. Eksempel: 0,9 m signifikant høyde med 15 s periode gir rundt 1,7 m med formelen alene; med Unstads surf-faktor (ca. 1,4, lært fra observasjonene) rundt 2,4 m (Unstad 26.09.2026, over hodet).",
      numbers: (h) => [
        ["Surfehøyde", h.surf_height!=null ? m(h.surf_height) : (h.low_reason ? "ikke beregnet (" + lowWord(h.low_reason) + ")" : "mangler")],
        ["Sett", m(h.surf_height_sets)],
        ["Signifikant høyde på spoten", m(h.height)],
        ["Periode ute", s(h.period)],
        ["Surf-faktor", h.surf_factor!=null ? nf1.format(h.surf_factor) : "mangler"],
      ],
      how: (h) => [
        "Hb = 0,39 × g^(1/5) × (T × H²)^(2/5) (Komar og Gaughan, 1972), ganget med spotens surf-faktor (lært fra loggene dine, ellers startverdi).",
        "Sett = 1,27 × Hb. Under 0,35 m signifikant høyde på spoten regnes det som flatt.",
        `H er ${SOURCE_WORD[h.height_source] || "ukjent kilde"}, T er svellets periode ute (Open-Meteo, GFS Wave).`,
      ],
    },
    hs: {
      title: "Signifikant høyde",
      what: "Gjennomsnittet av den høyeste tredjedelen av bølgene ute i vannet - tallet bølgemodeller oppgir. Ikke det samme som surfehøyden: 1,0 m signifikant med lang periode kan gi hodehøye bølger på stranda.",
      numbers: (h) => [
        ["På spoten", m(h.height)],
        ["BarentsWatch ved punktet", m(h.bw_height)],
        ["BarentsWatch maks", h.bw_height_max!=null ? m(h.bw_height_max) + " (vises, brukes aldri i ratingen)" : "mangler"],
        ["Kilde", SOURCE_WORD[h.height_source] || "mangler"],
      ],
      how: (h) => h.height_source==="barentswatch"
        ? ["BarentsWatch sin totalhøyde ved punktet, justert for svellandel, kort periode og retning skrått på stranda (bare det leddet som faktisk trekker ned).",
           "Sannhetshierarkiet: observasjoner > BarentsWatch > reservemodellen > geometri."]
        : ["Svell ute × transfer × eksponering (reservemodellen). BarentsWatch dekker bare de første ca. 60 timene."],
    },
    swell: {
      title: "Svell ute",
      what: "Det ekte, lange svellet ute på havet, skilt fra den lokale vindsjøen. Det er svellet som gir surfbare bølger. Eksempel: 1,6 m svell med 13 s periode er en god dag, 1,6 m vindsjø med 5 s er rot.",
      numbers: (h) => [
        ["Svell ute", m(h.swell_offshore)],
        ["Fra", h.dir_offshore!=null ? `${compass(h.dir_offshore)} (${deg(h.dir_offshore)})` : "mangler"],
        ["Periode", s(h.period)],
        ["Totalhøyde ute", m(h.height_offshore)],
        ["Svellandel", h.swell_model==="total_fallback" ? "ikke skilt ut (bruker total, dempet)" : pct(h.swell_share)],
        ["Sekundært svell (Open-Meteo)", h.secondary_swell_height!=null ? `${m(h.secondary_swell_height)} fra ${compass(h.secondary_swell_dir)}, ${s(h.secondary_swell_period)}` : "mangler"],
      ],
      how: () => ["Open-Meteo, GFS Wave-modellen, på spotens havpunkt. Høyde, retning og periode kommer alltid fra samme modell.",
                  "Mangler svellfeltet, brukes totalhøyden som tydelig merket reserve - aldri stille, aldri 0."],
    },
    period: {
      title: "Periode",
      what: "Sekunder mellom hver bølge. Lang periode (12 s og mer) betyr at svellet har reist langt, bærer mye energi og reiser seg høyt på grunt vann. Kort periode (under 8 s) gir svake, rotete bølger selv ved samme høyde.",
      numbers: (h) => [["Periode ute", s(h.period)], ["BarentsWatch-periode ved punktet", s(h.bw_period)]],
      how: () => ["Universell kurve i ratingen: 6 s eller kortere 0,4 · 8 s 0,65 · 10 s 0,85 · 12 s 0,95 · 14 s eller lengre 1,0.",
                  "Perioden i surfehøyde-formelen er svellets periode ute (GFS Wave), ikke BarentsWatch sin ved kysten."],
    },
    energy: {
      title: "Energi (kJ)",
      what: "Energi i bølgene ute. Lang periode gir mye mer energi og kraft, selv med samme høyde. Eksempel: 3 m med 11 s topperiode er ca. 2 100 kJ, 3 m med 14 s ca. 3 500 kJ.",
      numbers: (h) => [["Svellenergi", kj(h.energy_swell_kj)], ["Energi med totalhøyde", kj(h.energy_total_kj)]],
      how: () => ["E = ρ g² H² T² / (16π) ≈ 1,96 × H² × T² kJ per meter bølgefront, samme mål som surf-forecast. T er topperioden; mangler den (GFS Wave gir den ikke), brukes middelperioden × 1,25 - derfor gir «11 s» i appen rundt 3 300 kJ ved 3 m, ikke 2 100.",
                  "Ratingen bruker alltid svellenergien (ekte svell), aldri totalhøyden med vindsjø. Full uttelling fra 2 000 kJ, gradvis ned til 500 kJ (spots med lokale regler har egne grenser)."],
    },
    direction: {
      title: "Retningstreff",
      what: "Hvor godt svellets retning passer spotens vindu - sektoren av retninger med fri linje fra stranda til åpent hav. Svell rett i vinduet når inn med full høyde; svell utenfor må bøye seg rundt land (diffraksjon) og mister det meste. Eksempel: Grøtfjord 25.09.2026, svell 3 grader utenfor vinduet, helt flatt.",
      numbers: (h, spot) => [
        ["Retningstreff", pct(h.directness)],
        ["Svell fra", h.dir_offshore!=null ? `${compass(h.dir_offshore)} (${deg(h.dir_offshore)})` : "mangler"],
        ["Spotens vindu", spot && spot.swell_window ? (Array.isArray(spot.swell_window[0]) ? spot.swell_window : [spot.swell_window]).map(w=>`${w[0]}–${w[1]}°`).join(", ") : "mangler"],
        ["Ved punktet (BarentsWatch)", h.bw_dir!=null ? `fra ${compass(h.bw_dir)}, ${h.spot_direction_diff!=null ? h.spot_direction_diff + "° skrått" : ""}` : "mangler"],
        ["BarentsWatch bekrefter treff", h.bw_confirms==null ? "mangler" : (h.bw_confirms ? "ja" : "nei")],
      ],
      how: () => ["Eksponering per retning fra kystlinjedata (GSHHS, 300 m toleranse), glattet, og lært fra BarentsWatch der det finnes par.",
                  "Alle retninger er \"fra\"-retninger, 0 = nord. BarentsWatch sin retning regnes om fra \"mot\" med +180.",
                  "Svell som bare når spoten ved diffraksjon (rå eksponering 0) dempes ekstra i surfehøyden."],
    },
    exposure: {
      title: "Eksponering",
      what: "Andelen av svellet ute som når spoten for en gitt retning, når geometri (odder, øyer, bukter) er tatt hensyn til. 1,0 midt i vinduet, under 0,67 utenfor.",
      numbers: (h) => [["Eksponering denne timen", pct(h.directness)], ["Transfer (direkte treff)", h.transfer!=null ? pct(h.transfer) : "mangler"]],
      how: () => ["Geometrisk kurve per 10 grader (del C), blandet med lært kurve fra BarentsWatch (del B) der det finnes nok par.",
                  "Transfer er hvor mye av svellet ute som når stranda ved direkte treff - modell mot modell, lært fra BarentsWatch, aldri fra loggene."],
    },
    wind: {
      title: "Vind",
      what: "Offshore (fra land) holder bølgene rene og glatte; onshore (fra havet) bryter dem ned. Sidevind er midt imellom. Eksempel: Unstad 28.09.2026, lett offshore - lange, rene linjer.",
      numbers: (h) => [
        ["Vind", h.wind_speed!=null ? `${nf0.format(h.wind_speed)} m/s fra ${compass(h.wind_dir)} (${deg(h.wind_dir)})` : "mangler"],
        ["Kast", h.gust!=null ? `${nf0.format(h.gust)} m/s` : "mangler"],
        ["Type", WIND_WORD[h.wind_type] || "mangler"],
        ["Stjerner tapt på vind", h.faded_wind!=null ? String(h.faded_wind) : (h.faded!=null ? String(h.faded) : "mangler")],
        ["Kilde", h.wind_source==="openmeteo" ? "Open-Meteo GFS (langtid)" : h.wind_source==="metno" ? "met.no" + (h.wind_interpolated ? ", jevnet ut mellom 6-timersverdier" : "") : "mangler"],
      ],
      how: () => ["Offshore avgjøres av spotens offshore-sektor. Side/side-onshore/onshore måles fra spotens facing: innenfor 45° er onshore, 45–80° side-onshore, over 80° side.",
                  "Vindtabellen trekker stjerner etter styrke og type - vist som blasse stjerner."],
    },
    tide: {
      title: "Tidevann",
      what: "Flo og fjære flytter hvor og hvordan bølgene brekker. Noen spots liker lavvann (Farstadsanden, ifølge lokale surfere), andre tåler alt.",
      numbers: (h, spot) => [
        ["Nå", h.tide ? `${h.tide.rising?"stigende":"fallende"}, ${h.tide.state}${h.tide.level!=null?` (${nf1.format(h.tide.level)})`:""}` : "mangler"],
        ["Spoten", spot && spot.tide && spot.tide.length ? `liker ${spot.tide.join(" og ")} vann` : "tåler alt tidevann"],
        ["Stjerner tapt på tidevann", h.faded_tide!=null ? String(h.faded_tide) : "mangler"],
      ],
      how: () => ["Kartverket sin tidevannsvarsel for nærmeste punkt. Lokale regler (med navngitt kilde) kan trekke én stjerne ved feil tidevann, dempet med regelens vekt."],
    },
    confidence: {
      title: "Sikkerhet",
      what: "Hvor sannsynlig det er at stjernene treffer innenfor én stjerne. Startverdier per antall dager frem, erstattet av målt treffsikkerhet når spoten har nok sammenligninger. Varsler sendes bare for timer med minst 70 %.",
      numbers: (h) => [["Sikkerhet", h.confidence!=null ? `${h.confidence} %` : "mangler"], ["Grunnlag", h.confidence_source==="målt" ? "målt" : "anslag"], ["Dager frem", h.day!=null ? String(h.day) : "mangler"], ["Sone", h.zone==="langtid" ? "langtid (dag 8–16, GFS)" : h.zone==="reserve" ? "reservemodell" : "BarentsWatch"]],
      how: () => ["Hver kjøring arkiveres og sammenlignes med varselet laget under 6 timer før, og med loggene dine. Fra 30 sammenligninger brukes målt prosent."],
    },
    stars: {
      title: "Stjerner",
      what: "0 flatt, 1 dårlig, 2 ok, 3 bra, 4 veldig bra, 5 rått. Ved 0 stjerner sier ordet hvor mye som faktisk er der: «Flatt» under 0,3 m surfehøyde, «Smått» fra 0,3 m (litt bølger, for lite til en stjerne). Fra 0,8 m sier ordet hva som trekker mest: «Grøtete» (kort periode eller lite energi), «Blåst ut» (vinden), «Feil tidevann», «For lite svell» (lokal regel, kilden nevnes), eller «Ikke surfbart nå» når ingen enkelt ting er hovedårsaken. Trykk på ratingen for forklaringen. Blasse stjerner er det vind og tidevann tar fra svellets potensial.",
      numbers: (h) => [["Stjerner", h.stars!=null ? String(h.stars) : "mangler"], ["Tapt", h.faded!=null ? String(h.faded) : "mangler"], ["Grunn for 0–1", h.low_reason ? (typeof ratingWord === "function" ? ratingWord(h) : lowWord(h.low_reason)) : "–"]],
      how: () => ["Surfehøyde mot spotens idealhøyde × periode × energi × retningstreff gir potensialet; vind og tidevann trekker fra. Trykk på stjernene for hele regnestykket."],
    },
    sources: {
      title: "Kilder",
      what: "BarentsWatch (kystmodell, 100 m) de første ca. 60 timene, deretter reservemodellen (svell ute fra Open-Meteo/GFS Wave × transfer × eksponering) til dag 7, så langtid dag 8–16 merket \"anslag\". Vind fra met.no, så GFS. Tidevann fra Kartverket.",
      numbers: (h, spot) => [["Høyde denne timen", SOURCE_WORD[h.height_source] || "mangler"], ["BarentsWatch til", spot && spot.bw_until ? spot.bw_until.replace("T"," kl. ").replace("Z"," UTC") : "mangler"], ["Sone", h.zone || "mangler"]],
      how: () => ["Observasjoner fra loggene slår alt. Når en modell motsier en observasjon, er det modellen som er feil."],
    },
    windsea: {
      title: "Svellandel og sekundært svell",
      what: "Svellandelen er hvor mye av totalhøyden ute som er ekte svell (har reist langt); resten er vindsjø, korte og rotete bølger laget av vinden her og nå. Mye vindsjø i forhold til svell gjør bølgene urene selv om totalhøyden er stor. Det sekundære svellet er Open-Meteo sitt eget felt for et svell nummer to, ikke vindsjøen.",
      numbers: (h) => [
        ["Sekundært svell ute", h.secondary_swell_height!=null ? `${m(h.secondary_swell_height)} fra ${compass(h.secondary_swell_dir)}, ${s(h.secondary_swell_period)}` : "mangler"],
        ["Svellandel", h.swell_model==="total_fallback" ? "ikke skilt ut" : pct(h.swell_share)],
        ["Totalhøyde ute", m(h.height_offshore)],
      ],
      how: () => ["Svellandel = svell ute / totalhøyde ute, aldri under 0,2 (20 %). 1,0 brukes bare når en av høydene mangler.",
                  "BarentsWatch måler totalhøyde (svell og vindsjø sammen), så svellandelen brukes til å anslå hvor mye av den som er ekte svell."],
    },
    notice: {
      title: "Hva betyr varselet?",
      what: "En kort linje øverst sier fra når tallene er mer usikre enn vanlig. Trykk for å se hvorfor.",
      numbers: (h) => [
        ["Kildene uenige", h.sources_disagree ? (h.sources_disagree_reason || "ja") : "nei"],
        ["Grunn for lav rating", h.low_reason ? (typeof ratingWord === "function" ? ratingWord(h).toLowerCase() : h.low_reason) : "–"],
        ["Usikker time", h.uncertain ? "ja" : "nei"],
        ["Jevnet ut mellom målepunkter", h.bw_interpolated ? "ja" : "nei"],
        ["Dager frem", h.day!=null ? String(h.day) : "mangler"],
        ["Sikkerhet", h.confidence!=null ? `${h.confidence} %` : "mangler"],
      ],
      how: () => ["\"Kildene er uenige\": BarentsWatch viser høyde ved punktet, men svellet ute treffer ikke vinduet eller er mest vindsjø - da er timen usikker og rates forsiktig.",
                  "\"Blåst ut\": vinden tar stjernene. \"Stormsjø\": mye av totalhøyden er vindsjø, ikke svell. \"Treffer ikke\": svellet ute kommer fra en retning uten fri linje til stranda.",
                  "Langt frem i tid (dag 8-16) er alt et anslag fra den globale modellen - derfor \"usikkert så langt frem\"."],
    },
    shelter: {
      title: "Skjerming",
      what: "Hvor åpen spoten er mot havet, før noe er lært fra BarentsWatch eller loggene dine. Lang periode bøyer seg bedre rundt odder og inn fjorder enn kort periode, så skjermingen teller mindre for langt svell.",
      numbers: (h, spot) => [["Skjerming", spot && spot.shelter_label ? spot.shelter_label : "ikke beregnet"], ["Transfer brukt", h.transfer!=null ? pct(h.transfer) : "mangler"]],
      how: () => ["Geometrisk startverdi for reservemodellens transfer (ROADMAP oppgave I). Bare brukt når ingenting er lært."],
    },
  };

  function rowsHtml(rows){
    return rows.map(([k,v])=>`<div class="ex-row"><span class="ex-k">${esc(k)}</span><span class="ex-v">${esc(v)}</span></div>`).join("");
  }
  function esc(x){ return String(x).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

  let lastFocus = null;
  function openExplain(key, h, spot){
    const e = EXPLAIN[key];
    if(!e) return;
    lastFocus = document.activeElement;
    const sheet = document.getElementById("exSheet"), scrim = document.getElementById("exScrim");
    document.getElementById("exTitle").textContent = e.title;
    const numbers = h ? rowsHtml(e.numbers(h, spot)) : `<p class="ex-p">Ingen time valgt.</p>`;
    document.getElementById("exBody").innerHTML = `
      <p class="ex-p">${esc(e.what)}</p>
      <h3 class="ex-h">${esc(window.STR ? STR.thisHour : "Denne timen")}</h3>
      <div class="ex-rows">${numbers}</div>
      <h3 class="ex-h">${esc(window.STR ? STR.howComputed : "Slik regnes det ut")}</h3>
      ${(h ? e.how(h, spot) : e.how({}, spot)).map(t=>`<p class="ex-p">${esc(t)}</p>`).join("")}`;
    sheet.classList.add("open"); scrim.classList.add("open"); sheet.setAttribute("aria-hidden","false");
    document.getElementById("exClose").focus();
  }
  function closeExplain(){
    const sheet = document.getElementById("exSheet"), scrim = document.getElementById("exScrim");
    sheet.classList.remove("open"); scrim.classList.remove("open"); sheet.setAttribute("aria-hidden","true");
    if(lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function wireExplain(root, h, spot){
    (root || document).querySelectorAll("[data-explain]").forEach(el=>{
      el.onclick = (ev)=>{ ev.stopPropagation(); openExplain(el.dataset.explain, h, spot); };
      if(el.tagName !== "BUTTON"){
        el.setAttribute("role","button"); el.setAttribute("tabindex","0");
        el.onkeydown = (ev)=>{ if(ev.key==="Enter" || ev.key===" "){ ev.preventDefault(); openExplain(el.dataset.explain, h, spot); } };
      }
    });
  }
  document.addEventListener("DOMContentLoaded", ()=>{
    const c = document.getElementById("exClose"), s = document.getElementById("exScrim");
    if(c) c.onclick = closeExplain;
    if(s) s.onclick = closeExplain;
    document.addEventListener("keydown", (ev)=>{ if(ev.key==="Escape" && document.getElementById("exSheet").classList.contains("open")) closeExplain(); });
  });
  window.EXPLAIN = EXPLAIN;
  window.openExplain = openExplain;
  window.closeExplain = closeExplain;
  window.wireExplain = wireExplain;
})();
