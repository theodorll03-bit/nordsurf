/* Nordsurf: appens logikk (flyttet ut av index.html i designrunde 1, 09.10.2026).
   Ren visning: ALLE tall kommer fra docs/data/forecast.json slik fetcher/rating.py
   skrev dem - appen regner aldri stjerner eller høyder selv. Tekster i js/strings.js,
   forklaringer i js/explain.js, grafen i js/chart.js. Vanlig <script>, ikke modul -
   js/map.js bruker flere av funksjonene her (starsSVG, heightMForDisplay, openSheet ...). */
/* ---------- Oppsett ---------- */
const TZ = "Europe/Oslo";
const LOG_KEY = "nordsurf.logs.v1";
const SIZES = ["Flatt","Knehøy","Hoftehøy","Brysthøy","Hodehøy","Over hodet","Dobbelt over hodet"];
const WINDS = ["Offshore","Onshore","Rotete","Blankt"];
// Surfehøyde i meter (høyden der bølgene brekker), ikke Hs. 26.09.2026:
// Hodehøy er ny, Over hodet endret fra 2,0 til 2,4, Dobbelt over hodet er
// ny. Samme tabell i fetcher/calibrate.py - test_pipeline.py sjekker at de
// er like.
const SIZE_M = {"Flatt":0, "Knehøy":0.5, "Hoftehøy":0.9, "Brysthøy":1.3, "Hodehøy":1.8, "Over hodet":2.4, "Dobbelt over hodet":3.6};
// Samme formel som fetcher/rating.py sin breaking_height() - brukt her bare
// til BarentsWatch-punkt-sammenligningen i Logger-fanen (SIZE_M er nå
// surfehøyde, bwHeight/bwHeightNear er fortsatt Hs, så de må regnes om
// før de kan sammenlignes mot det du har logget).
function breakingHeight(h, period){
  if(h==null || period==null || h<=0) return null;
  return 0.39 * Math.pow(9.81, 0.2) * Math.pow(period * h * h, 0.4);
}
const MIN_SIZE_LOGS = 5;
const STAR_WORDS = STR.starWords;
const PICK_WORDS = STR.pickWords;
const WIND_WORD = STR.wind;
// "sidevind" inneholder allerede "vind" - "sidevind"+"vinden" ville gitt
// "sidevindvinden". De andre (offshore/side-onshore/onshore) er låneord uten
// "vind" i seg, og tåler "vinden" rett på (offshorevinden, onshorevinden,
// side-onshorevinden er alle riktige som de er).
function windNoun(type){
  const w = WIND_WORD[type];
  if(!w) return "vinden";
  return w.endsWith("vind") ? w+"en" : w+"vinden";
}
function windLabel(h){
  // "blankt"/"nesten blankt" under 1,5/3 m/s, ellers vindtypen - se
  // fetcher/rating.py sin wind_label() (samme grenser, regnet ut server-side
  // for breakdown, men grid-cellen her trenger den uavhengig av breakdown).
  if(h.wind_speed==null) return "";
  if(h.wind_speed<1.5) return STR.windCalm;
  if(h.wind_speed<3) return STR.windNearCalm;
  return WIND_WORD[h.wind_type]||"";
}

// 05.10.2026 (Theodors rettelse, Grøtfjord kl. 11-17 - se STATUS.md): samme
// fire ord for 0 og 1 stjerne overalt - detaljside, liste, dagbrikker og
// kartets høydeplate (js/map.js, vanlig <script> i samme vindu, ikke en
// modul - bruker disse to globalt, se kommentaren øverst der). Speiler
// fetcher/rating.classify_low_rating().
const LOW_REASON_WORD = STR.lowReason;
function heightMForDisplay(h){
  // Tallet å vise ved siden av low_reason sitt ord. Flatt/Treffer ikke har
  // ikke noe pålitelig tall å vise fram. Blåst ut/Stormsjø skal vise den
  // ekte høyden i stedet for å gjemme den bak ordet alene (Theodors
  // rettelse 05.10.2026, punkt c) - men de to betyr ulike tall:
  // - blåst ut: surfehøyden hvis den er reell (nær BarentsWatch sin egen
  //   totalhøyde uansett - det er VINDEN som tok stjernene, ikke lav
  //   svellandel), ellers BarentsWatch sin totalhøyde (surfehøyden er
  //   tvunget til 0 av flat-sperren i den gamle, lav-høyde-drevne
  //   "blåst ut"-saken, se is_blown_out()).
  // - stormsjø: ALLTID BarentsWatch sin totalhøyde, aldri surfehøyden -
  //   lav svellandel betyr nettopp at surfehøyden (justert for akkurat
  //   den andelen) er et lite, misvisende tall ved siden av "Stormsjø".
  //   "mye totalhøyde" (Theodors egen begrunnelse, punkt a) er bw_height,
  //   ikke surfehøyden. Funnet av fysikk-kontrollør 05.10.2026 (en ekte
  //   stormsjø-time har ALLTID surf_height>0 - low_hs ville ellers gjort
  //   den til "flat" først, se classify_low_rating()).
  if(!h) return null;
  if(!h.low_reason) return h.surf_height;
  if(h.low_reason==="blown_out") return (h.surf_height!=null && h.surf_height>0) ? h.surf_height : h.bw_height;
  if(h.low_reason==="stormsjo") return h.bw_height!=null ? h.bw_height : h.surf_height;
  return null;
}
const $ = s => document.querySelector(s);
const nf1 = new Intl.NumberFormat("nb-NO",{maximumFractionDigits:1, minimumFractionDigits:1});
const nf0 = new Intl.NumberFormat("nb-NO",{maximumFractionDigits:0});
const fmtHour = new Intl.DateTimeFormat("nb-NO",{hour:"2-digit",timeZone:TZ});
const fmtTime = new Intl.DateTimeFormat("nb-NO",{hour:"2-digit",minute:"2-digit",timeZone:TZ});
const fmtDay = new Intl.DateTimeFormat("nb-NO",{weekday:"long",timeZone:TZ});
const fmtDayShort = new Intl.DateTimeFormat("nb-NO",{weekday:"short",timeZone:TZ});
const fmtDate = new Intl.DateTimeFormat("nb-NO",{weekday:"short",day:"numeric",month:"short",timeZone:TZ});
const dayKey = d => new Intl.DateTimeFormat("sv-SE",{timeZone:TZ}).format(d);

let DATA = null, state = {tab:"varsel", spot:null, sel:0}, logDraft = {};

function compass(deg){
  if(deg==null) return "–";
  const n=["N","NNØ","NØ","ØNØ","Ø","ØSØ","SØ","SSØ","S","SSV","SV","VSV","V","VNV","NV","NNV"];
  return n[Math.round(((deg%360)+360)%360/22.5)%16];
}
function relDay(d){
  const today = dayKey(new Date()), k = dayKey(d);
  const tmr = dayKey(new Date(Date.now()+864e5));
  if(k===today) return "i dag";
  if(k===tmr) return "i morgen";
  return fmtDay.format(d);
}
function relDayShort(d){
  const r = relDay(d);
  if(r==="i dag") return r;
  return fmtDayShort.format(d).replace(/\.$/,"");
}
function cap(s){ return s.charAt(0).toUpperCase()+s.slice(1); }
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}


/* ---------- Rating: ord eller stjerner (punkt 2) ---------- */
// Samme ord overalt (liste, detaljside, dagbrikker, kartets høydeplate):
// 0 stjerner viser ORDET i dempet ratingfarge, 1 og mer viser stjernene i
// ratingfargen. Farge er aldri eneste informasjon - ordet/stjernene står
// alltid der. Tallene kommer fra forecast.json (rating.py) - aldri regnet her.
const STAR_PATH = "M12 2.8l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 16.8l-5.4 2.9 1-6.1L3.2 9.3l6.1-.9z";
function ratingClass(h){ const n = h && h.stars ? Math.min(5, h.stars) : 0; return `r-${n}`; }
// Ordet ved 0 stjerner med årsak «flat» (low_reason flat, eller 0 stjerner
// uten annen grunn), etter surfehøyden (Theodors ja 09.10.2026, to runder):
// under 0,3 m «Flatt», 0,3 til under 0,8 m «Smått», 0,8 m eller mer
// «Grøtete» (bølgene er der, men kort periode og lite energi gjør dem svake).
// Bare visningsordet - stjernene, low_reason og tallene er uendret. Blåst ut/
// Treffer ikke/Stormsjø uendret. Samme ord overalt via ratingWord().
const SMALL_SURF_MIN_M = 0.3, MUSHY_SURF_MIN_M = 0.8, MUSHY_PERIOD_MAX_S = 9;
const ZERO_WORDS = [STR.starWords[0], STR.wordSmall];   // «Flatt» < «Smått» - ordene den kompakte grafen/klyngepila slår sammen
let _hourSpot = null;
function spotOfHour(h){
  // spoten en time-post hører til (samme objekt som i DATA) - til lokale regler
  if(!_hourSpot || _hourSpot.data!==DATA){
    const m = new WeakMap(); (DATA.spots||[]).forEach(s=>(s.hours||[]).forEach(x=>m.set(x, s)));
    _hourSpot = {data: DATA, map: m};
  }
  return _hourSpot.map.get(h) || null;
}
// Fra 0,8 m (Theodors regel 09.10.2026, tredje runde): ordet følger det som
// faktisk trekker MEST, fra henterens egen bokføring `zero_losses` (hver
// faktor målt ALENE mot potensialet før energifaktoren - se rating.rate();
// eldre forecast.json uten feltet: faded_wind/faded_tide/local stars_lost,
// energi og kapping ukjent = 0). Bare visning, stjernene regnes ikke her:
// - periode under 9 s, eller energifaktoren er det største fradraget: «Grøtete»
//   (energigrense fra en LOKAL regel: «For lite svell», kilden nevnes)
// - vindstraffen størst: «Blåst ut»; tidevannsstraffen størst: «Feil tidevann»
// - lokale regler størst: ordet etter regelen (tidevann → «Feil tidevann»,
//   vind → «Blåst ut»), forklaringen nevner kilden
// - kappingen ved «kildene uenige» er minst like stor som det største
//   fradraget: «Usikkert» («Kildene er uenige om svellet når inn til spoten.»)
// - ingen tydelig hovedårsak (alt 0, uavgjort, eller kappingen ved usikkert
//   varsel - se rating.py sin `uncertain` - er minst like stor): «Ikke surfbart nå»
// Kilden til en lokal regel skrives slik spots.json har den (STR.localSourceText),
// aldri som en person når den ikke er det (Theodor 09.10.2026, fjerde runde).
function localSourceText(spot, h){
  const src = (spot && spot.local_rules && spot.local_rules.source) || (h.local_rules && h.local_rules.source) || null;
  if(!src) return "Lokal regel";
  return (STR.localSourceText && STR.localSourceText[src]) || STR.localSourceFallback(src);
}
function zeroCause(h){
  const per = h.period;
  const shortPer = per!=null && per < MUSHY_PERIOD_MAX_S;
  const mushy = {word: STR.wordMushy, explain: shortPer ? STR.mushyShort : STR.mushyLong};
  if(shortPer) return mushy;
  const lr = h.local_rules || null, src = lr && lr.source ? lr.source : null;
  const spot = spotOfHour(h);
  const localEnergy = !!(spot && spot.local_rules && spot.local_rules.min_energy_kj);
  const srcText = localSourceText(spot, h);
  const z = h.zero_losses || null;
  const c = z ? {energy: z.energy||0, wind: z.wind||0, tide: z.tide||0, local: z.local||0}
              : {energy: 0, wind: h.faded_wind||0, tide: h.faded_tide||0, local: lr ? (lr.stars_lost||0) : 0};
  const cap = z ? (z.cap||0) : 0;
  const max = Math.max(c.energy, c.wind, c.tide, c.local);
  const winners = Object.keys(c).filter(k=>c[k]===max && max > 0);
  const notNow = {word: STR.wordNotNow, explain: STR.wordExplain[STR.wordNotNow]};
  if(max===0 && cap===0) return {word: STR.wordNotNow, explain: STR.notNowLow};
  if(cap >= max) return h.sources_disagree ? {word: STR.wordUncertain, explain: STR.wordExplain[STR.wordUncertain]} : {word: STR.wordNotNow, explain: STR.notNowCap};
  if(winners.length!==1) return notNow;
  const w = winners[0];
  if(w==="energy"){
    if(localEnergy){
      const full = spot.local_rules.min_energy_kj.full, kj = h.energy_swell_kj!=null ? nf0.format(h.energy_swell_kj) : "–";
      return {word: STR.wordLittleSwell, explain: `${srcText}: ${STR.localEnergyExplain(kj, nf0.format(full))}`};
    }
    return mushy;
  }
  if(w==="wind") return {word: LOW_REASON_WORD.blown_out, explain: STR.wordExplain[LOW_REASON_WORD.blown_out]};
  if(w==="tide") return {word: STR.wordTide, explain: STR.wordExplain[STR.wordTide]};
  // lokale regler: linjene som faktisk trakk (inneholder «−»)
  const pen = (lr.lines||[]).filter(l=>/−/.test(l));
  if(pen.length!==1) return notNow;
  const line = pen[0], rest = line.charAt(0).toLowerCase() + line.slice(1);
  if(/^Tidevann/.test(line)) return {word: STR.wordTide, explain: `${srcText}: ${rest}`};
  if(/^Vind/.test(line)){
    // «Vind 5 m/s sidevind: strengere lokal grense …» → spoten trenger offshore, nå 5 m/s sidevind
    const now = line.split(":")[0].replace(/^Vind\s*/, "").trim();
    return {word: LOW_REASON_WORD.blown_out, explain: `${srcText}: ${STR.localWindExplain(spot ? spot.name : "spoten", now)}`};
  }
  return notNow;
}
function zeroWord(h){
  // null når regelen ikke gjelder (stjerner, annen low_reason, eller tallet mangler)
  if(!h || h.stars || !(h.low_reason==="flat" || !h.low_reason) || h.surf_height==null) return null;
  if(h.surf_height >= MUSHY_SURF_MIN_M) return zeroCause(h).word;
  return h.surf_height >= SMALL_SURF_MIN_M ? STR.wordSmall : STR.starWords[0];
}
function ratingWord(h){
  if(!h) return "–";
  // 0 stjerner uten grunn OG uten surfehøyde: tallet mangler - aldri «Flatt»
  // (grunnregelen; fysikk-kontrollør 09.10.2026, 0 slike timer i dag)
  if(!(h.stars) && !h.low_reason && h.surf_height==null) return "–";
  const z = zeroWord(h); if(z!=null) return z;
  if(h.low_reason) return LOW_REASON_WORD[h.low_reason] || STAR_WORDS[0];
  return STAR_WORDS[Math.min(5, h.stars||0)];
}
// Forklaringen bak ordet (vises øverst i «Hvorfor denne ratingen?»)
function ratingWordExplain(h){
  if(h && !h.stars && (h.low_reason==="flat" || !h.low_reason) && h.surf_height!=null && h.surf_height >= MUSHY_SURF_MIN_M) return zeroCause(h).explain;
  const w = ratingWord(h); return (STR.wordExplain && STR.wordExplain[w]) || null;
}
function starsSVG(solid, faded, big){
  let out = "";
  for(let i=0;i<5;i++){
    const cls = i<solid ? "st" : i<solid+faded ? "st f" : "st e";
    out += `<svg viewBox="0 0 24 24" aria-hidden="true"><path class="${cls}" d="${STAR_PATH}"/></svg>`;
  }
  return `<span class="stars${big?" big":""} r-${Math.min(5,solid||0)}" role="img" aria-label="${STR.starsAria(solid, faded)}">${out}</span>`;
}
function ratingHtml(h, big){
  // 0 stjerner: ordet alene (stort, dempet), ingen stjerner, aldri punktum.
  // 1-5 stjerner: stjernene i ratingfargen. Har timen 1 stjerne OG en
  // low_reason ("Blåst ut", "Treffer ikke" ...), står ordet under stjernen
  // - Theodors regel 05.10.2026 ("samme fire ord for 0 og 1 stjerne
  // overalt") gjelder fortsatt (fysikk-kontrollør 09.10.2026).
  if(!h) return `<span class="word r-0${big?" big":""}">–</span>`;
  if(!h.stars) return `<span class="word r-0${big?" big":""}">${esc(ratingWord(h))}</span>`;
  const stars = starsSVG(h.stars, h.faded, big);
  if(h.low_reason) return `<span class="lr${big?" big":""}">${stars}<span class="word lrw ${ratingClass(h)}" aria-hidden="true">${esc(ratingWord(h))}</span></span>`;
  return stars;
}
function windArrowHtml(h){
  if(!h || h.wind_dir==null) return "";
  // pila peker dit vinden BLÅSER (fra-retning + 180), som værpiler flest
  return `<span class="wind-arrow" aria-hidden="true"><svg viewBox="0 0 24 24" style="--rot:${Math.round(h.wind_dir+180)}deg"><path d="M12 3l5 7h-3v11h-4V10H7z"/></svg></span>`;
}
function windShort(h){
  if(!h || h.wind_speed==null) return "";
  const type = windLabel(h);
  return `${nf0.format(h.wind_speed)} m/s${type?` ${type}`:""}`;
}
function windShorter(h){
  // Kortversjon til kortene i lista (Theodor 09.10.2026, småfiks 2): "3 m/s
  // blankt", "4 m/s side-on" - så vind og kJ alltid får plass på én linje og
  // alle kort er like høye. Full tekst står i aria-label og på detaljsiden.
  if(!h || h.wind_speed==null) return "";
  const type = windLabel(h);
  const short = STR.windShort[type] || type;
  return `${nf0.format(h.wind_speed)} m/s${short?` ${short}`:""}`;
}
function kjText(h){
  // Energien ute, samme tall som Energi-cellen i Detaljer: svellenergien når
  // svellfeltet finnes, ellers energien med totalhøyde (reserve). Mangler
  // tallet, returneres null - aldri "0 kJ". Theodors svar på PR #2
  // (09.10.2026): kJ tilbake i hovedlinja, grafens verdier, kartplata og
  // lista på PC (ikke mobil, ikke dagbrikkene).
  // Reserve (fysikk-kontrollør 09.10.2026): når svellfeltet mangler, setter
  // henteren svell = totalhøyde × fast andel (swell_model "total_fallback",
  // 22 langtidstimer i dag) - energien er da et ANSLAG og merkes "ca.",
  // aldri vist som et vanlig tall. Samme hvis bare totalenergien finnes.
  // Avrundet 0 kJ er et ekte, ørlite tall, ikke manglende - vises som "under 1 kJ".
  if(!h) return null;
  const reserve = h.swell_model==="total_fallback" || h.swell_offshore==null;
  const kj = h.swell_offshore!=null ? h.energy_swell_kj : h.energy_total_kj;
  if(kj==null) return null;
  if(kj===0) return STR.kjUnderOne;
  return `${reserve?"ca. ":""}${nf0.format(kj)} kJ`;
}
function heightRangeText(h){
  // "0,8 til 1,1 m": surfehøyde og sett. 0 stjerner: ordet alene (ikke et
  // tall som ser ut som en måling), unntatt blåst ut/stormsjø som viser den
  // ekte høyden ved siden av ordet (Theodors rettelse 05.10.2026).
  if(!h) return STR.noHeight;
  if(h.low_reason){
    const m = heightMForDisplay(h);
    return m!=null ? `${nf1.format(m)} m` : "";
  }
  if(h.surf_height==null) return STR.noHeight;
  const a = nf1.format(h.surf_height);
  const b = h.surf_height_sets!=null ? nf1.format(h.surf_height_sets) : null;
  return STR.height(a, b);
}

/* ---------- Beste vindu, kort tekst ---------- */

/* ---------- Dagbrikker: ukedag + farget prikk, ingen tall (punkt 1) ---------- */

/* ---------- Visninger ---------- */
const isDesktop = () => matchMedia("(min-width: 900px)").matches;
function wordmarkSvg(){ return window.WORDMARK_SVG || `<svg viewBox="0 0 10 10"></svg>`; }
function sampleBanner(){
  return DATA.sample ? `<p class="banner sample"><b>${esc(STR.sample)}</b></p>` : "";
}
// ROADMAP oppgave G (overvåking av henteren): henteren kjører hver tredje
// time - er varselet eldre enn STALE_HOURS, har en kjøring feilet.
const STALE_HOURS = 6;
function isStale(){
  if(DATA.sample || !DATA.generated) return false;
  return Date.now() - new Date(DATA.generated).getTime() > STALE_HOURS*36e5;
}
function staleBanner(){
  if(!isStale()) return "";
  const gen = new Date(DATA.generated);
  return `<p class="banner stale" role="alert"><b>${esc(STR.stale(relDay(gen), fmtTime.format(gen)))}.</b> ${esc(STR.staleMore)}</p>`;
}
function spotImg(id){ return `img/spots/${encodeURIComponent(id)}.jpg`; }


/* ---------- Detaljside (punkt 3-6): viktigst først ---------- */
function noticeFor(h){
  // Én kort linje i vanlig språk, første som gjelder. Forklaring ved trykk.
  // Bare EKTE advarsler står øverst (Theodors tilbakemelding 09.10.2026,
  // punkt 4): gammelt varsel, kildene uenige, BarentsWatch-punktet i le,
  // usikkert, og usikkert langt frem. "Timen er jevnet ut mellom to
  // målepunkter" er ikke en advarsel - den står under Detaljer (Kilder-
  // cellen). low_reason-ordene (Blåst ut osv.) står allerede som rating-
  // ordet, og "kanten av vinduet" ligger i Retningstreff-cellen.
  if(isStale()) return {key:"notice", text: STR.notice.stale, warn:true};
  if(h.sources_disagree) return {key:"notice", text: STR.notice.disagree, warn:true};
  // "BarentsWatch-punktet ligger i le" finnes i dag BARE i henterens
  // kilderapport (fetch.bw_point_in_lee_warning(), per spot og kjøring),
  // ikke i forecast.json - ingen time/spot-felt å lese. Legges til her når
  // henteren eksporterer det (eget delsteg, krever egen fysikk-kontroll).
  if(h.uncertain) return {key:"notice", text: STR.notice.uncertain, warn:true};
  if(h.zone==="langtid") return {key:"notice", text: STR.notice.farAhead, warn:true};
  return null;
}
function tipHtml(h){
  const t = new Date(h.t);
  const range = heightRangeText(h);
  const line = [range, h.period!=null?`${nf0.format(h.period)} s`:null, kjText(h), windShort(h)].filter(Boolean).join(" · ");
  return `<b>${esc(cap(relDay(t)))} kl. ${fmtHour.format(t)}</b> · ${esc(h.stars ? `${h.stars} ${h.stars===1?"stjerne":"stjerner"}` : ratingWord(h))}<br>${esc(line)}`;
}
function tapCell(key, k, v, n){
  return `<button type="button" class="cell tap" data-explain="${key}"><div class="k">${esc(k)}</div><div class="v">${v}</div>${n?`<div class="n">${n}</div>`:""}</button>`;
}
function detailsGrid(s, h, t){
  const tide = nextTide(s,t);
  const lt = lightText(s,t);
  const tideNow = h.tide ? STR.tideNow(h.tide.rising, h.tide.state) : "–";
  const swellV = h.swell_offshore!=null ? `${nf1.format(h.swell_offshore)} m` : (h.height_offshore!=null ? `${nf1.format(h.height_offshore)} m` : "–");
  const swellN = `${esc(STR.fromDir(compass(h.dir_offshore)))}${h.dir_offshore!=null?` (${Math.round(h.dir_offshore)}°)`:""}${h.period!=null?`, ${nf0.format(h.period)} s`:""}`;
  const shareV = h.swell_model==="total_fallback" ? "–" : (h.swell_share!=null ? `${nf0.format(h.swell_share*100)} %` : "–");
  const shareN = h.swell_model==="total_fallback" ? esc(STR.totalFallback) : (h.height_offshore!=null ? esc(`av ${nf1.format(h.height_offshore)} m totalt`) : "");
  const dirV = h.directness!=null ? `${nf0.format(h.directness*100)} %` : "–";
  const dirN = h.height_source==="barentswatch" ? esc([uteDirectionText(h,s), vedSpotenDirectionText(h)].filter(Boolean).join(" ")) : esc(`${directionHitText(h)}${directionHitText(h)?" · ":""}${windowText(s)}`);
  const windN = `${esc(windLabel(h))} ${esc(STR.fromDir(compass(h.wind_dir)))}${h.gust!=null?`, ${esc(STR.gust(nf0.format(h.gust)))}`:""}${h.wind_interpolated?` · ${esc(STR.windSmoothed)}`:""}${h.wind_source==="openmeteo"?` · ${esc(STR.windGfs)}`:""}`;
  const hsN = `${esc(surfSubtext(h))}${h.bw_height_max!=null?` · ${esc(STR.bwMax(nf1.format(h.bw_height_max)))}`:""}${surfAdjustmentLine(h)?`<br>${esc(surfAdjustmentLine(h))}`:""}`;
  const confN = h.confidence!=null ? esc(STR.confidenceSub(h.confidence_source==="målt", h.day, STR.zone[h.zone]||STR.zone.barentswatch)) : "";
  const water = h.water_temp!=null ? `${nf0.format(h.water_temp)} °C` : (h.zone==="langtid" ? STR.notThisFar : "–");
  const air = h.air_temp!=null ? `${nf0.format(h.air_temp)} °C` : "–";
  const cal = s.calibration || {};
  // Mangler tallet, vises "–" - aldri en standardverdi som ser ut som ekte (fysikk-kontrollør 09.10.2026).
  const trV = (cal.transfer_used ?? h.transfer); const sfV = (cal.surf_factor_used ?? h.surf_factor);
  const calV = `${trV!=null?`${nf0.format(trV*100)} %`:"–"} · ${sfV!=null?nf1.format(sfV):"–"}`;
  const calN = "transfer og surf-faktor";
  return `<div class="grid">
    ${tapCell("surf_height", STR.cell.surf, esc(surfHeadline(h)), "")}
    ${tapCell("hs", STR.cell.hs, h.height!=null?`${nf1.format(h.height)} m`:"–", hsN)}
    ${tapCell("swell", STR.cell.swell, swellV, swellN)}
    ${tapCell("energy", STR.cell.energy, kjText(h)||"–", h.swell_model==="total_fallback" ? esc(STR.kjEstimateSub) : (h.swell_offshore!=null?"svellenergi":"med totalhøyde, anslag"))}
    ${tapCell("windsea", STR.cell.share, shareV, shareN)}
    ${tapCell("direction", STR.cell.direction, dirV, dirN)}
    ${tapCell("exposure", STR.cell.exposure, h.transfer!=null?`${nf0.format(h.transfer*100)} %`:"–", STR.transferSub)}
    ${tapCell("windsea", STR.cell.windsea, h.secondary_swell_height!=null?`${nf1.format(h.secondary_swell_height)} m`:"–", h.secondary_swell_height!=null?`${esc(STR.fromDir(compass(h.secondary_swell_dir)))}${h.secondary_swell_period!=null?`, ${nf0.format(h.secondary_swell_period)} s`:""}`:"")}
    ${tapCell("period", STR.cell.period, h.period!=null?`${nf0.format(h.period)} s`:"–", h.bw_period!=null?`BarentsWatch ${nf0.format(h.bw_period)} s ved punktet`:"")}
    ${tapCell("wind", STR.cell.wind, h.wind_speed!=null?`${nf0.format(h.wind_speed)} m/s`:"–", windN)}
    ${tapCell("tide", STR.cell.tide, esc(tideNow), `${tide?esc(STR.tideNext(tide.type, fmtTime.format(new Date(tide.time))))+". ":""}${esc(STR.tidePref(s.tide))}`)}
    ${tapCell("sources", lt.k, esc(lt.v), esc(lt.n))}
    ${tapCell("sources", STR.cell.temps, esc(STR.temps(water, air)), "")}
    ${tapCell("sources", STR.cell.sources, h.height_source==="barentswatch"?"BarentsWatch":(h.zone==="langtid"?"Langtid (GFS)":"Reservemodell"), h.bw_interpolated?esc(STR.notice.interpolated):"")}
    ${tapCell("confidence", STR.cell.confidence, h.confidence!=null?`${h.confidence} %`:"–", confN)}
    ${s.shelter_label ? tapCell("shelter", STR.cell.shelter, esc(cap(s.shelter_label)), "") : ""}
    ${tapCell("exposure", STR.cell.calibration, calV, calN)}
    ${localRulesHtml(h)}
  </div>`;
}

/* ---------- Hjelpere for Detaljer (fra før, uendret logikk) ---------- */
// 26.09.2026: surfehøyde (der bølgene brekker) er nå det man ser først -
// "height" (Hs, signifikant høyde ute) er bare forklaringen bak tallet, se
// README "Surfehøyde".
function surfHeadline(h){
  // 05.10.2026 (Theodors rettelse, Grøtfjord kl. 11-17 - se STATUS.md): ett
  // samlende felt (low_reason) i stedet for å sjekke blown_out/likely_flat
  // hver for seg - se fetcher/rating.classify_low_rating(). Viser den ekte
  // høyden ved siden av ordet for blåst ut/stormsjø (punkt c), ikke bare
  // "Trolig flatt" som før.
  if(h.low_reason){
    const m = heightMForDisplay(h);
    return m!=null ? `${ratingWord(h)} (${nf1.format(m)} m)` : ratingWord(h);
  }
  if(h.surf_height==null) return h.height!=null ? `${nf1.format(h.height)} m` : "–";
  const sets = h.surf_height_sets!=null ? `, sett ${nf1.format(h.surf_height_sets)} m` : "";
  return `${nf1.format(h.surf_height)} m${sets}`;
}
function surfSubtext(h){
  if(h.height==null) return "Ingen data";
  const period = h.period!=null ? `${nf0.format(h.period)} s` : "ukjent periode";
  if(h.height_source==="barentswatch"){
    const interp = h.bw_interpolated ? " (interpolert)" : "";
    // 27.09.2026 (Theodors rettelse, Unstad for lav - se STATUS.md): tallet
    // vi viser i "v" over (surfHeadline) er justert (svellandel, periode,
    // retning ved punktet) - skal ALDRI kalles "signifikant" alene, det
    // begrepet gjelder BarentsWatch sin EGNE totalhøyde (bw_height). Selve
    // justeringen vises i en egen linje, se surfAdjustmentLine().
    return h.bw_height!=null
      ? `BarentsWatch ${nf1.format(h.bw_height)} m signifikant, ${period}${interp}`
      : `${nf1.format(h.height)} m, ${period}, BarentsWatch${interp}`;
  }
  return `${nf1.format(h.height)} m signifikant, ${period}, anslag`;
}
function bwPeriodFactor(period){
  // Speiler rating.bw_period_factor() - bare til å avgjøre HVILKET ledd
  // (svellandel eller periode) som faktisk er det begrensende i min()
  // under, til visning. Endrer aldri noe tall selv.
  if(period==null) return 1.0;
  if(period<6) return 0.3;
  if(period<8) return 0.3+0.3*(period-6)/2;
  return 1.0;
}
function surfAdjustmentLine(h){
  // 27.09.2026 (Theodors rettelse): egen linje for selve justeringen fra
  // BarentsWatch sin totalhøyde til den brukte høyden - bare leddene som
  // FAKTISK trekker ned (min(svellandel, periodefaktor) - bare den minste
  // av de to er den reelle årsaken, og retningen bare hvis den ikke er 1,0).
  if(h.height_source!=="barentswatch" || h.bw_height==null || h.height==null) return "";
  const share = h.swell_share, pf = bwPeriodFactor(h.bw_period), dirfac = h.spot_direction_factor;
  const shareOk = share==null || share>=0.999, pfOk = pf>=0.999, dirOk = dirfac==null || dirfac>=0.999;
  if(shareOk && pfOk && dirOk) return "";
  const reasons = [];
  if(!shareOk && (pfOk || share<=pf)) reasons.push(`svellandel ${Math.round(share*100)} %`);
  else if(!pfOk) reasons.push("kort BarentsWatch-periode");
  if(!dirOk) reasons.push(h.spot_direction_diff!=null ? `retning ${Math.round(h.spot_direction_diff)}° skrått ved punktet` : "retning ved punktet");
  return `Etter justering ${nf1.format(h.height)} m (${reasons.join(", ")})`;
}
const SURF_HEIGHT_EXPLAINER = "Surfehøyde er høyden der bølgene brekker, regnet ut fra bølgehøyde og periode (Komar og Gaughan, 1972). Signifikant høyde er gjennomsnittet ute i vannet - langt svell reiser seg mer når det treffer grunnen.";
// 06.10.2026, Theodors oppgave (andre runde): samme tekst Theodor selv
// formulerte, ordrett - erstatter den første versjonen av denne teksten.
const ENERGY_EXPLAINER = "Energi i bølgene ute. Lang periode gir mye mer energi og kraft, selv med samme høyde.";
// ROADMAP oppgave I (skjerming), 06.10.2026 natt: statisk per spot (ikke per
// time) - hvor åpen spoten er mot havet, før noe er lært fra BarentsWatch
// eller loggene dine. Vises bare for spots der fetch.py sin resolve_shelter()
// stolte på målingen (s.shelter_label er null ellers, se der).
const SHELTER_EXPLAINER = "Hvor åpen spoten er mot havet, før noe er lært fra BarentsWatch eller loggene dine. Lang periode diffrakterer (bøyer seg) bedre rundt odder og inn fjorder enn kort periode, så skjermingen teller mindre for langt svell.";
function localRulesHtml(h){
  // 06.10.2026, Theodors oppgave (Magnus, lokal surfer - se CLAUDE.md sin
  // "Lokalkunnskap"): egen, tydelig merket celle under Detaljer - IKKE i den
  // vanlige stjerne-forklaringen (openBreakdown). Tom (ingen linjer, ingen
  // stjerner trukket) vises ikke i det hele tatt.
  const lr = h.local_rules;
  if(!lr || (!(lr.lines||[]).length && !lr.stars_lost)) return "";
  const lost = lr.stars_lost;
  return `<div class="cell wide"><div class="k">${esc(STR.cell.localRules)} (${esc(lr.source||"lokalkunnskap")})</div>
      ${(lr.lines||[]).map(l=>`<div class="n">${esc(l)}</div>`).join("")}
      ${lost ? `<div class="n"><b>Trekker ${lost} stjerne${lost===1?"":"r"} fra tidevann/vind-reglene.</b></div>` : ""}
    </div>`;
}
function energyText(h){
  // Samme høyde som selve "v"-tallet i cella viser (swell_offshore, ellers
  // height_offshore) - energien skal alltid matche TALLET den står ved
  // siden av, se rating.energy_kj() sin docstring for hvorfor de to kJ-
  // feltene (svell/total) kan avvike.
  const t = kjText(h);  // samme tekst og samme reserve-merking som hovedlinja
  return t ? ` · ${t}` : "";
}
function windowText(spot){
  const w = spot.swell_window;
  if(!w) return "";
  const secs = Array.isArray(w[0]) ? w : [w];
  return "Vindu " + secs.map(([a,b])=>`${a}–${b}°`).join(", ");
}
function directionHitText(h){
  if(h.directness==null) return "";
  if(h.directness < 0.667) return "Utenfor vinduet";
  if(h.directness >= 0.999) return "Midt i vinduet";
  return "I kanten av vinduet";
}
function offshoreShareText(h){
  if(h.swell_offshore==null || !(h.height_offshore>0)) return "";
  // 06.10.2026, Theodors rettelse (manglende svelldata, se CLAUDE.md): ingen
  // kilde hadde et ekte, utskilt svellfelt denne timen - swell_offshore er
  // et forsiktig ANSLAG fra totalhøyden (se fetch.build_spot()), ikke en
  // ekte prosent å vise som om den var målt.
  if(h.swell_model==="total_fallback") return ", av " + nf1.format(h.height_offshore) + " m totalt (svell ikke skilt ut, bruker total)";
  const pct = nf0.format(h.swell_offshore/h.height_offshore*100);
  return `, av ${nf1.format(h.height_offshore)} m totalt (${pct} %, resten vindsjø)`;
}
function uteDirectionText(h, spot){
  const hit = directionHitText(h);
  if(!hit) return "";
  const deg = h.dir_offshore!=null ? Math.round(h.dir_offshore)+"°" : "";
  return `Ute: ${hit.toLowerCase()}${deg?` (${deg}, ${windowText(spot).toLowerCase()})`:""}.`;
}
function vedSpotenDirectionText(h){
  if(h.height_source!=="barentswatch" || h.bw_dir==null || h.spot_direction_diff==null) return "";
  return `Ved spoten: bølgene kommer fra ${compass(h.bw_dir)}, ${h.spot_direction_diff}° skrått på stranda.`;
}
function nextTide(spot, t){
  const after = (spot.tide_events||spot.tide||[]).filter(x=>new Date(x.time) >= t);
  return after[0] || null;
}
function lightClass(x){
  const l = x.light || (x.daylight===false ? "mørkt" : "dag");
  return l==="mørkt" ? " dark" : l==="skumring" ? " dusk" : "";
}
function lightText(spot, t){
  const d = (spot.light_days||{})[dayKey(t)];
  if(!d) return {k:"Lys", v:"–", n:""};
  if(!d.start) return {k:"Lys", v:"Mørkt hele dagen", n:"Ingen brukbart lys"};
  return {k:"Brukbart lys", v:`${fmtTime.format(new Date(d.start))}–${fmtTime.format(new Date(d.end))}`,
    n: d.sun ? "Fra skumring til skumring" : "Mørketid, bare skumring"};
}

function favIconSvg(active){
  return `<svg viewBox="0 0 24 24" aria-hidden="true"><path class="${active?"fav-solid":"fav-outline"}" d="${STAR_PATH}"/></svg>`;
}
function isFavSpot(id){
  return !!(window.Auth && Auth.state.favorites && Auth.state.favorites.has(id));
}
function favBtnHtml(id, wrap){
  const active = isFavSpot(id);
  const inner = `<button type="button" class="fav-btn" data-fav="${esc(id)}" aria-pressed="${active}" aria-label="${active?"Fjern fra favoritter":"Legg til favoritter"}">${favIconSvg(active)}</button>`;
  return wrap ? `<div class="fav-btn-wrap">${inner}</div>` : inner;
}
async function toggleFavoriteUI(spotId){
  if(!window.Auth || !Auth.state.user){
    toast("Logg inn for å lagre favoritter", "Logg inn", ()=>{ Front.go("innstillinger"); });
    return;
  }
  try{ await Auth.toggleFavorite(spotId); }
  catch(e){ toast("Kunne ikke lagre favoritt: " + e.message); }
}
function wireFavButtons(){
  document.querySelectorAll(".fav-btn").forEach(b=>b.onclick=()=>toggleFavoriteUI(b.dataset.fav));
}

/* ---------- Beste vindu ---------- */
function bestWindow(spot){
  const hrs = spot.hours.filter(h => h.daylight !== false && new Date(h.t) >= new Date(Date.now()-36e5));
  if(!hrs.length) return null;
  // Timer der kildene er uenige (BarentsWatch-høyde, men trolig vindsjø
  // eller feil retning) skal ikke bli "beste time" hvis det finnes andre
  // timer uten den konflikten - bare fall tilbake til dem om ALT er usikkert.
  const clean = hrs.filter(h=>!h.sources_disagree);
  const pool = clean.length ? clean : hrs;
  const max = Math.max(...pool.map(h=>h.stars));
  if(max < 2) return {none:true};
  let start=null, end=null;
  for(const h of pool){
    const gap = end ? new Date(h.t) - new Date(end.t) : 0;
    if(h.stars===max && (!start || gap<=36e5)){ if(!start) start=h; end=h; }
    else if(start) break;
  }
  return {stars:max, start:new Date(start.t), end:new Date(new Date(end.t).getTime()+36e5),
    // ROADMAP oppgave B: sikkerhet (prosent) og sone for vinduets første time
    confidence: start.confidence, confidenceSource: start.confidence_source, zone: start.zone};
}
function toHourKey(d){ return d.toISOString().slice(0,13)+":00Z"; }
function currentHour(spot){
  const now = Date.now();
  let idx = spot.hours.findIndex(h => new Date(h.t).getTime() + 36e5 > now);
  return Math.max(0, idx);
}

/* ---------- Rapporter ---------- */
const WIND_IMPRESSION_WORD = {offshore:"Offshore", onshore:"Onshore", side:"Sidevind", stille:"Stille"};
function reportItemHtml(r){
  const mine = !!(window.Auth && Auth.state.user && r.user_id === Auth.state.user.id);
  const name = r.profiles && r.profiles.display_name ? esc(r.profiles.display_name) : "Ukjent";
  const d = new Date(r.created_at);
  const extras = [
    r.wave_height_m!=null ? `${nf1.format(r.wave_height_m)} m` : null,
    r.wind_impression ? WIND_IMPRESSION_WORD[r.wind_impression] : null,
  ].filter(Boolean).join(" · ");
  return `<div class="report">
    <div class="report-head">
      <b>${name}</b>
      <span class="report-time">${relDay(d)} kl. ${fmtTime.format(d)}</span>
      ${mine?`<button type="button" class="report-del" data-id="${esc(r.id)}">Slett</button>`:""}
    </div>
    ${extras?`<p class="report-extras">${esc(extras)}</p>`:""}
    <p class="report-text">${esc(r.text)}</p>
  </div>`;
}
function reportFormHtml(){
  const a = window.Auth && Auth.state;
  if(!a || !a.user){
    return `<p style="color:var(--muted);padding:14px 0">Logg inn for å se og skrive rapporter.</p>`;
  }
  if(!a.profile){
    return `<p style="color:var(--muted);padding:14px 0">Sett et visningsnavn i <a href="#" id="gotoKonto">Innstillinger</a> før du kan skrive rapporter.</p>`;
  }
  return `<div class="report-form">
    <textarea id="reportText" maxlength="500" rows="3" placeholder="Hvordan var det i vannet?"></textarea>
    <div class="report-form-row">
      <label for="reportWave">Bølgehøyde</label>
      <input type="number" id="reportWave" step="0.1" min="0" max="10" placeholder="m">
      <label for="reportWind">Vind</label>
      <select id="reportWind">
        <option value="">Ikke oppgitt</option>
        <option value="offshore">Offshore</option>
        <option value="onshore">Onshore</option>
        <option value="side">Sidevind</option>
        <option value="stille">Stille</option>
      </select>
    </div>
    <div class="row-btns"><button class="primary" id="reportSend" style="min-height:44px">Del rapport</button></div>
  </div>`;
}
async function loadReportsUI(spotId){
  const el = $("#reportsSection");
  if(!el) return;
  const a = window.Auth && Auth.state;
  if(!a || !a.ready){ el.innerHTML = `<p style="color:var(--muted);padding:14px 0">Laster…</p>`; return; }
  let listHtml = "";
  if(a.user){
    const reports = await Auth.listReports(spotId);
    listHtml = reports.length ? reports.map(reportItemHtml).join("") : `<p style="color:var(--muted);padding:14px 0">Ingen rapporter ennå.</p>`;
  }
  if($("#reportsSection") !== el) return; // spot byttet mens vi ventet
  el.innerHTML = listHtml + reportFormHtml();
  const gk = $("#gotoKonto");
  if(gk) gk.onclick = (e)=>{ e.preventDefault(); Front.go("innstillinger"); };
  const send = $("#reportSend");
  if(send) send.onclick = async ()=>{
    const text = $("#reportText").value.trim();
    if(!text) return;
    const wave = $("#reportWave").value ? parseFloat($("#reportWave").value) : null;
    const wind = $("#reportWind").value || null;
    send.disabled = true;
    try{ await Auth.postReport(spotId, text, wave, wind); await loadReportsUI(spotId); toast("Rapport delt"); }
    catch(e){ toast("Kunne ikke dele rapport: " + e.message); send.disabled = false; }
  };
  document.querySelectorAll(".report-del").forEach(b=>b.onclick=async ()=>{
    if(!confirm("Slette denne rapporten?")) return;
    try{ await Auth.deleteReport(b.dataset.id); await loadReportsUI(spotId); }
    catch(e){ toast("Kunne ikke slette: " + e.message); }
  });
}

/* ---------- Logger ---------- */
function loadLogs(){ try{ return JSON.parse(localStorage.getItem(LOG_KEY)) || []; }catch(e){ return []; } }
function saveLogs(l){ try{ localStorage.setItem(LOG_KEY, JSON.stringify(l)); return true; }catch(e){ return false; } }

// Del B (ROADMAP oppgave 4): eksponering per retning, lært fra BarentsWatch
// og blandet med den geometriske kurven fra del C - se fetcher/exposure_learn.py.
// Fargeskala 0-5 stjerner, uavhengig av rav-fargen (--star) som ellers
// betyr "stjerner" i appen - her trengs en skala, ikke en enkeltfarge.
const STAR_SCALE = ["#c0392b","#e0672c","#e0a72c","#c9c22b","#7fbf3f","#2f9e44"];
function exposureChartSVG(spotId, curve, logs){
  if(!curve) return "";
  const W = 380, H = 130, padL = 26, padR = 8, padT = 6, plotH = 84, axisY = padT + plotH;
  const bx = i => padL + (i + 0.5) * (W - padL - padR) / 36;
  const by = v => axisY - v * plotH;
  const path = (key) => curve.map((c,i)=>c[key]!=null ? `${bx(i)},${by(c[key])}` : null).filter(Boolean);
  const geoPts = curve.map((c,i)=>`${bx(i)},${by(c.geometric)}`).join(" ");
  const langPts = path("learned_lang");
  const kortPts = path("learned_kort");
  const maxPairs = Math.max(1, ...curve.map(c=>Math.max(c.pairs_lang||0, c.pairs_kort||0)));
  const bars = curve.map((c,i)=>{
    const n = Math.max(c.pairs_lang||0, c.pairs_kort||0);
    if(!n) return "";
    const h = 14 * Math.min(1, n / maxPairs);
    const w = (W - padL - padR) / 36 - 2;
    return `<rect x="${bx(i)-w/2}" y="${H-14+ (14-h)}" width="${w}" height="${h}" fill="var(--muted)" opacity=".35"/>`;
  }).join("");
  const dots = (pts, color) => pts.map(p=>`<circle cx="${p.split(",")[0]}" cy="${p.split(",")[1]}" r="2.6" fill="${color}"/>`).join("");
  const marks = (logs||[]).filter(l=>l.spot===spotId && l.dirOffshore!=null && l.stars!=null).map(l=>{
    const i = Math.floor((l.dirOffshore % 360) / 10);
    return `<circle cx="${bx(i)}" cy="${axisY+6}" r="3" fill="${STAR_SCALE[Math.max(0,Math.min(5,l.stars))]}"><title>${l.stars} stjerner</title></circle>`;
  }).join("");
  const ticks = [0,90,180,270].map(d=>{
    const i = d/10;
    return `<text x="${bx(i)}" y="${H-1}" font-size="9" fill="var(--muted)" text-anchor="middle">${d}°</text>`;
  }).join("");
  const yTicks = [0,0.5,1].map(v=>`<text x="${padL-4}" y="${by(v)+3}" font-size="9" fill="var(--muted)" text-anchor="end">${v}</text>`).join("");
  return `<svg class="expo-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Eksponering per retning">
    <line x1="${padL}" y1="${axisY}" x2="${W-padR}" y2="${axisY}" stroke="var(--line)"/>
    ${bars}
    <polyline points="${geoPts}" fill="none" stroke="var(--muted)" stroke-width="1.4" stroke-dasharray="3 2"/>
    ${langPts.length>1 ? `<polyline points="${langPts.join(" ")}" fill="none" stroke="#2f6fed" stroke-width="1.8"/>` : ""}
    ${dots(langPts, "#2f6fed")}
    ${dots(kortPts, "#e08b2f")}
    ${marks}
    ${ticks}${yTicks}
  </svg>`;
}

function forecastAt(spotId, t){
  const s = DATA.spots.find(x=>x.id===spotId); if(!s) return null;
  const key = new Date(Math.floor(t.getTime()/36e5)*36e5).toISOString().slice(0,13)+":00Z";
  return s.hours.find(h=>h.t===key) || null;
}

function renderLogs(){
  const logs = loadLogs().sort((a,b)=>b.t.localeCompare(a.t));
  const calib = DATA.spots.map(s=>{
    const withF = logs.filter(l=>l.spot===s.id && l.forecastStars!=null);
    if(!withF.length) return `<div class="calib"><div class="t">${esc(s.name)}</div><p>Ingen logger med varsel å sammenligne mot ennå.</p></div>`;
    const hits = withF.filter(l=>Math.abs(l.stars-l.forecastStars)<=1).length;
    const bias = withF.reduce((a,l)=>a+(l.stars-l.forecastStars),0)/withF.length;
    const dir = Math.abs(bias)<0.5 ? "Varselet ligger omtrent riktig." : bias>0 ? `Varselet undervurderer med ${nf1.format(bias)} stjerner i snitt.` : `Varselet overvurderer med ${nf1.format(-bias)} stjerner i snitt.`;
    return `<div class="calib"><div class="t">${esc(s.name)}: traff ${hits} av ${withF.length}</div><p>${dir} Treff betyr innenfor én stjerne.</p></div>`;
  }).join("");
  // 26.09.2026: transfer (modell mot modell, reserven mot BarentsWatch -
  // læres ALDRI fra loggene lenger) og surf_factor (loggene/observasjonene
  // dine mot Komar og Gaughan sin bruddhøyde-formel) er to adskilte tall,
  // som ikke skal blandes - se README "Surfehøyde".
  const heightCal = DATA.spots.map(s=>{
    const cal = s.calibration || {};
    const transferPct = nf0.format((cal.transfer_used ?? (s.hours[0]||{}).transfer ?? 0.6) * 100);
    const transferSrcTxt = cal.transfer_source==="eksponering" ? `Lært fra eksponeringen per retning (del B, ${cal.exposure_buckets_learned_lang} bøtter)`
      : cal.transfer_source==="barentswatch" ? `Lært fra BarentsWatch (${cal.bw_pairs} par over ${cal.bw_days} døgn)`
      : cal.transfer_source==="spots.json" ? "Satt i spots.json"
      : cal.transfer_source==="logs" ? "Lært fra loggene dine"
      : cal.transfer_source==="skjerming" ? "Geometrisk startverdi fra skjerming (ROADMAP oppgave I), ikke lært ennå"
      : "Standardverdi";
    const surfFactor = cal.surf_factor_used ?? 1.0;
    const surfLogs = cal.surf_factor_logs ?? 0;
    const surfSrcTxt = cal.surf_factor_source==="logs"
      ? `Lært fra ${surfLogs} logger/observasjoner du har lagt inn`
      : cal.surf_factor_source==="prior"
      ? `Startverdi${cal.surf_factor_prior_n!=null?` fra ${cal.surf_factor_prior_n} observasjoner`:""} (ikke lært fra logger ennå - ${Math.max(0,MIN_SIZE_LOGS-surfLogs)} til med størrelse og retning rett inn så overstyrer det)`
      : `Standardverdi (${Math.max(0,MIN_SIZE_LOGS-surfLogs)} til med størrelse og retning rett inn før den læres automatisk)`;
    return `<div class="calib"><div class="t">${esc(s.name)}</div>
      <p><b>Transfer ${transferPct} %</b>: hvor mye av svellet ute som når stranda ved direkte treff, modell mot modell (reservemodellen mot BarentsWatch). ${transferSrcTxt}.</p>
      <p><b>Surf-faktor ${nf1.format(surfFactor)}</b>: hvor godt Komar og Gaughan sin bruddhøyde-formel stemmer med det du faktisk ser her. ${surfSrcTxt}.</p></div>`;
  }).join("");
  // Del B (ROADMAP oppgave 4): eksponering lært fra BarentsWatch, per
  // 10-graders bøtte, blandet med den geometriske kurven fra del C. Grå
  // stiplet linje er geometrien alene (uendret), blå er lært for lang
  // periode (10 s og over), oransje prikker lært for kort periode - se
  // fetcher/exposure_learn.py sin modul-docstring for hele metoden.
  const exposureCal = DATA.spots.map(s=>{
    const cal = s.calibration || {};
    const curve = cal.exposure_curve;
    if(!curve){
      return `<div class="calib"><div class="t">${esc(s.name)}</div><p>Ingen geometrisk eksponeringsdata bygget ennå (fetcher/exposure_baseline.py må kjøres manuelt).</p></div>`;
    }
    const pairs = cal.exposure_pairs ?? 0;
    const bucketsLang = cal.exposure_buckets_learned_lang ?? 0;
    const bucketsKort = cal.exposure_buckets_learned_kort ?? 0;
    const sugg = (cal.exposure_override_suggestions || []).map(o=>
      `<div class="sugg">Retning ${o.from}-${o.to}°: lært eksponering (${nf1.format(o.learned_max)}) ligger allerede under taket (${nf1.format(o.cap)}) i spots.json. Vurder å fjerne exposure_override for denne sektoren - fjernes aldri automatisk.</div>`
    ).join("");
    return `<div class="calib"><div class="t">${esc(s.name)}: ${pairs} par, ${bucketsLang} bøtter lært (lang periode), ${bucketsKort} (kort)</div>
      <p>Eksponering per retning - hvor mye av svellet ute som når spoten. Stiplet grå: geometrien alene (del C). Blå linje/prikker: lært for lang periode. Oransje prikker: lært for kort periode. Prikkene langs bunnen er dine egne logger, farget etter stjerner.</p>
      ${exposureChartSVG(s.id, curve, logs)}
      <div class="expo-legend">
        <span><i style="background:var(--muted);opacity:.6"></i>Geometri</span>
        <span><i style="background:#2f6fed"></i>Lært, lang periode</span>
        <span><i style="background:#e08b2f"></i>Lært, kort periode</span>
      </div>
      ${sugg}</div>`;
  }).join("");
  // Hvilket BarentsWatch-punkt (250 m, brukt i varselet, eller 150 m, det
  // opprinnelige) som faktisk ligger nærmest det du har logget. Bytter
  // ALDRI punkt selv - bare til orientering.
  const bwCompare = DATA.spots.map(s=>{
    const withSize = logs.filter(l=>l.spot===s.id && l.size && SIZE_M[l.size]!=null);
    if(withSize.length < MIN_SIZE_LOGS){
      const left = MIN_SIZE_LOGS - withSize.length;
      return `<div class="calib"><div class="t">${esc(s.name)}</div><p>Trenger ${left} økt${left===1?"":"er"} til med størrelse valgt for å sammenligne BarentsWatch-punktene.</p></div>`;
    }
    const withBoth = withSize.filter(l=>l.bwHeight!=null && l.bwHeightNear!=null && l.forecastPeriod!=null);
    if(!withBoth.length){
      return `<div class="calib"><div class="t">${esc(s.name)}</div><p>Ingen av de ${withSize.length} øktene med størrelse har data fra begge punktene ennå.</p></div>`;
    }
    const avg = arr => arr.reduce((a,b)=>a+b,0)/arr.length;
    const dev250 = avg(withBoth.map(l=>Math.abs(SIZE_M[l.size]-breakingHeight(l.bwHeight,l.forecastPeriod))));
    const dev150 = avg(withBoth.map(l=>Math.abs(SIZE_M[l.size]-breakingHeight(l.bwHeightNear,l.forecastPeriod))));
    const better = dev250<=dev150 ? "250 m" : "150 m";
    return `<div class="calib"><div class="t">${esc(s.name)}: ${better}-punktet ligger nærmest det du har logget</div>
      <p>Snittavvik fra ${withBoth.length} økter: 250 m-punktet ${nf1.format(dev250)} m, 150 m-punktet ${nf1.format(dev150)} m. Varselet bruker fortsatt 250 m-punktet - bytt manuelt i spots.json om du vil.</p></div>`;
  }).join("");
  // Hvor ofte timer der kildene var uenige (BarentsWatch-høyde, men trolig
  // vindsjø eller feil retning ved spoten - kappet til maks 1 stjerne)
  // faktisk ble logget som surfbare. Mange treff her tyder på at regelen
  // er for streng.
  const disagreeStats = DATA.spots.map(s=>{
    const flagged = logs.filter(l=>l.spot===s.id && l.sourcesDisagree);
    if(!flagged.length){
      return `<div class="calib"><div class="t">${esc(s.name)}</div><p>Ingen økter logget når kildene var uenige ennå.</p></div>`;
    }
    const surfable = flagged.filter(l=>l.stars>=2).length;
    return `<div class="calib"><div class="t">${esc(s.name)}: ${surfable} av ${flagged.length} var surfbare likevel</div>
      <p>Gjelder økter logget mens BarentsWatch-høyden trolig var mest vindsjø eller ikke traff stranda. Mange treff her betyr at regelen kanskje er for streng.</p></div>`;
  }).join("");
  // 06.10.2026, Theodors oppgave (Magnus, lokal surfer - se CLAUDE.md
  // "Lokalkunnskap"): foreslå å myke opp en lokal regel når minst 3 gode
  // logger (3 stjerner eller mer) BRYTER den samme regelen - det er et tegn
  // på at terskelen er strengere enn det du faktisk opplever. Samme mønster
  // som disagreeStats over (og exposure_override_suggestions): bare et
  // forslag, ENDRER ALDRI spots.json sin local_rules selv. Eldre logger uten
  // tideState/energyTotalKj telles bare ikke med (samme mønster som
  // dirOffshore - "figuren viser dem bare ikke").
  const LOCAL_RULE_SUGGEST_MIN = 3;
  const localRuleStats = DATA.spots.filter(s=>s.local_rules).map(s=>{
    const lr = s.local_rules, good = logs.filter(l=>l.spot===s.id && l.stars>=3);
    const items = [];
    const zero = lr.min_energy_kj && lr.min_energy_kj.zero;
    if(zero!=null){
      // 06.10.2026, andre runde: energy_factor() sammenlignes nå mot
      // SVELLenergien (energySwellKj), ikke totalhøyden - rettet her også
      // (var energyTotalKj, samme feil som selve regelen hadde).
      const broke = good.filter(l=>l.energySwellKj!=null && l.energySwellKj < zero);
      if(broke.length >= LOCAL_RULE_SUGGEST_MIN){
        items.push(`<div class="sugg">${broke.length} gode økter (3+ stjerner) hadde under ${nf0.format(zero)} kJ svellenergi - under "zero"-grensen i den lokale energiregelen. Vurder å senke den. Endres aldri automatisk.</div>`);
      }
    }
    if(lr.tide_prefer && lr.tide_penalty_high!=null){
      const broke = good.filter(l=>l.tideState!=null && !lr.tide_prefer.includes(l.tideState));
      if(broke.length >= LOCAL_RULE_SUGGEST_MIN){
        items.push(`<div class="sugg">${broke.length} gode økter (3+ stjerner) var utenfor tidevannet den lokale regelen favoriserer (${lr.tide_prefer.join("/")}) . Vurder å myke opp tidevanns-straffen. Endres aldri automatisk.</div>`);
      }
    }
    if(!items.length) return "";
    return `<div class="calib"><div class="t">${esc(s.name)}: lokale regler (${esc(lr.source||"lokalkunnskap")})</div>${items.join("")}</div>`;
  }).join("");
  // 06.10.2026, Theodors oppgave (andre runde, punkt 2e): foreslå
  // energy_factor() sine grenser PER SPOT ut fra loggene dine, for ALLE
  // spots (ikke bare de med local_rules fra før) - når en spot har minst
  // ENERGY_LEARN_MIN_LOGS logger med kjent svellenergi, finn energien der
  // loggene går fra flatt/dårlig (0-1 stjerner) til surfbart (2+): "zero" =
  // beste dårlige økt, "full" = dårligste gode økt. Bare et forslag, viser
  // dagens faktiske grenser (standard eller en egen regel) ved siden av -
  // ENDRER ALDRI spots.json selv, samme mønster som alle andre forslag her.
  const ENERGY_LEARN_MIN_LOGS = 8;
  const energyLearnStats = DATA.spots.map(s=>{
    const withE = logs.filter(l=>l.spot===s.id && l.energySwellKj!=null);
    if(withE.length < ENERGY_LEARN_MIN_LOGS) return "";
    const bad = withE.filter(l=>l.stars<=1).map(l=>l.energySwellKj);
    const good = withE.filter(l=>l.stars>=2).map(l=>l.energySwellKj);
    if(!bad.length || !good.length) return "";
    const zero = Math.max(...bad), full = Math.min(...good);
    if(zero >= full) return "";  // ingen tydelig overgang å foreslå - dårlig og god energi overlapper
    const lr = s.local_rules && s.local_rules.min_energy_kj ? s.local_rules.min_energy_kj : null;
    const curTxt = lr ? `${esc(s.name)} sin egen regel (full ${nf0.format(lr.full)}, zero ${nf0.format(lr.zero)})`
                       : `standardgrensene (full 2000, zero 500)`;
    return `<div class="calib"><div class="t">${esc(s.name)}: energiterskel fra ${withE.length} logger</div>
      <p>Dårligste gode økt (2+ stjerner): ${nf0.format(full)} kJ svellenergi. Beste dårlige økt (0-1 stjerne): ${nf0.format(zero)} kJ. Dagens grenser er ${curTxt}. Vurder full ~${nf0.format(full)}, zero ~${nf0.format(zero)}. Endres aldri automatisk.</p></div>`;
  }).join("");
  // ROADMAP oppgave B: treffprosent per antall dager frem, per spot - målt
  // av henteren selv (eldre varsel mot nyeste varsel og mot loggene dine),
  // startverdier ("anslag") til det finnes minst 30 sammenligninger.
  const accuracyStats = DATA.spots.map(s=>{
    const acc = (s.calibration||{}).accuracy;
    if(!acc) return "";
    const measured = acc.filter(a=>a.source==="målt").length;
    const cells = acc.map(a=>`<span class="acc${a.source==="målt"?" malt":""}" title="${a.day} dager frem: ${a.pct} % (${a.source}, ${a.n} sammenligninger)">${a.day}d ${a.pct}%</span>`).join("");
    return `<div class="calib"><div class="t">${esc(s.name)}: ${measured} av 16 dager frem er målt</div>
      <p>Sannsynlighet for treff innenfor én stjerne, per antall dager frem. Uthevet = målt fra dine logger og henterens egne sammenligninger (minst 30), ellers startverdi.</p>
      <div class="accrow">${cells}</div></div>`;
  }).join("");
  const rows = logs.map(l=>{
    const s = DATA.spots.find(x=>x.id===l.spot); const d = new Date(l.t);
    const extra = [l.size,l.wind].filter(Boolean).join(", ");
    const fc = l.forecastStars!=null ? `Varsel: ${l.forecastStars}` : "Uten varsel";
    const obs = l.type==="observed" ? `Observert${l.source?` (${esc(l.source)})`:""}. ` : "";
    return `<div class="logrow"><span><b>${esc(s?s.name:l.spot)}</b> ${starsSVG(l.stars,0)}</span>
      <button class="del" data-id="${l.id}" aria-label="Slett økt ${fmtDate.format(d)}">Slett</button>
      <span class="m">${obs}${fmtDate.format(d)} kl. ${fmtTime.format(d)}. ${fc}${extra?`. ${esc(extra)}`:""}</span></div>`;
  }).join("");
  $("#detailPane").innerHTML = `<header class="top"><h1>Logger</h1><p class="sub">Hver logg gjør varselet ærligere.</p></header>
    <h2 class="sec">Treffsikkerhet</h2>${calib}
    <h2 class="sec">Bølgehøyde</h2>${heightCal}
    <h2 class="sec">Eksponering per retning</h2>${exposureCal}
    <h2 class="sec">BarentsWatch-punkt</h2>${bwCompare}
    <h2 class="sec">Uenige kilder</h2>${disagreeStats}
    ${accuracyStats ? `<h2 class="sec">Treffsikkerhet per dager frem</h2>${accuracyStats}` : ""}
    ${localRuleStats ? `<h2 class="sec">Forslag til lokale regler</h2>${localRuleStats}` : ""}
    ${energyLearnStats ? `<h2 class="sec">Forslag til energiterskler</h2>${energyLearnStats}` : ""}
    <h2 class="sec">Økter</h2>
    <div class="list">${rows || `<p class="empty">Ingen økter ennå. Åpne en spot og trykk Logg økt etter neste tur.</p>`}</div>
    <div style="display:flex;gap:10px;flex-wrap:wrap"><button class="ghost" id="newLog">Logg økt</button></div>`;
  document.querySelectorAll(".del").forEach(b=>b.onclick=()=>{
    const all = loadLogs(); const removed = all.find(l=>l.id===b.dataset.id);
    saveLogs(all.filter(l=>l.id!==b.dataset.id)); markDeleted(b.dataset.id); renderLogs(); syncLogs();
    toast("Økt slettet", "Angre", ()=>{ unmarkDeleted(removed.id); saveLogs([...loadLogs(), removed]); renderLogs(); syncLogs(); });
  });
  $("#newLog").onclick = ()=>openSheet();
}

/* ---------- Synk til privat GitHub-repo ---------- */
const SYNC_KEY = "nordsurf.sync.v1", DEL_KEY = "nordsurf.deleted.v1";
function loadSync(){ try{ return JSON.parse(localStorage.getItem(SYNC_KEY)) || {}; }catch(e){ return {}; } }
function saveSync(s){ try{ localStorage.setItem(SYNC_KEY, JSON.stringify(s)); }catch(e){} }
function loadDeleted(){ try{ return JSON.parse(localStorage.getItem(DEL_KEY)) || []; }catch(e){ return []; } }
function markDeleted(id){ try{ localStorage.setItem(DEL_KEY, JSON.stringify([...new Set([...loadDeleted(), id])])); }catch(e){} }
function unmarkDeleted(id){ try{ localStorage.setItem(DEL_KEY, JSON.stringify(loadDeleted().filter(x=>x!==id))); }catch(e){} }
const b64 = s => btoa(unescape(encodeURIComponent(s)));
const unb64 = s => decodeURIComponent(escape(atob(s.replace(/\n/g,""))));
let syncing = false;
async function syncLogs(manual){
  const cfg = loadSync();
  if(!cfg.repo || !cfg.token){ if(manual) toast("Legg inn repo og nøkkel først"); return; }
  if(syncing) return; syncing = true;
  const url = `https://api.github.com/repos/${cfg.repo}/contents/logs.json`;
  const headers = {Authorization:`Bearer ${cfg.token}`, Accept:"application/vnd.github+json"};
  try{
    let remote = {logs:[], deleted:[]}, sha;
    const r = await fetch(url,{headers, cache:"no-store"});
    if(r.ok){ const j = await r.json(); sha = j.sha; remote = JSON.parse(unb64(j.content)); }
    else if(r.status!==404) throw new Error(r.status===401?"Nøkkelen er ugyldig eller utløpt":`GitHub svarte ${r.status}`);
    const deleted = [...new Set([...(remote.deleted||[]), ...loadDeleted()])];
    const byId = {};
    [...(remote.logs||[]), ...loadLogs()].forEach(l=>byId[l.id]=l);
    const merged = Object.values(byId).filter(l=>!deleted.includes(l.id));
    const body = JSON.stringify({logs:merged, deleted}, null, 1);
    const put = await fetch(url,{method:"PUT", headers, body: JSON.stringify({message:"Oppdater logger", content:b64(body), ...(sha?{sha}:{})})});
    if(!put.ok) throw new Error(put.status===409?"Konflikt, prøv igjen":`Lagring feilet (${put.status})`);
    saveLogs(merged);
    saveSync({...cfg, last:new Date().toISOString(), error:null});
    if(manual) toast(`Synket ${merged.length} økter`);
  }catch(e){
    saveSync({...cfg, error:e.message});
    if(manual) toast(`Synk feilet: ${e.message}`);
  }finally{
    syncing = false;
    Front.refresh();
  }
}

function accountSectionHtml(){
  const a = window.Auth && window.Auth.state;
  if(!a || !a.ready){
    return `<h2 class="sec">Konto</h2><div class="form"><p style="color:var(--muted)">Kobler til...</p></div>`;
  }
  if(!a.user){
    return `<h2 class="sec">Konto</h2>
      <div class="form">
        <p>Logg inn for å lagre favoritter og skrive kommentarer på spots.</p>
        <label for="authEmail">E-post</label>
        <input type="email" id="authEmail" placeholder="deg@eksempel.no" autocapitalize="off" autocorrect="off" spellcheck="false" autocomplete="email">
        <p id="authMsg" style="color:var(--muted);display:none"></p>
        <div class="row-btns"><button class="primary" id="authSend" style="min-height:44px">Send innloggingslenke</button></div>
      </div>`;
  }
  const name = a.profile ? a.profile.display_name : "";
  return `<h2 class="sec">Konto</h2>
    <div class="form">
      <p>Innlogget som ${esc(a.user.email)}.</p>
      <label for="authName">Visningsnavn</label>
      <input type="text" id="authName" maxlength="30" placeholder="Kari" value="${esc(name)}">
      <div class="row-btns"><button class="primary" id="authSaveName" style="min-height:44px">Lagre navn</button></div>
      <div class="row-btns"><button class="ghost" id="authLogout" style="min-height:44px">Logg ut</button></div>
      <div class="row-btns"><button class="ghost" id="authDelete" style="min-height:44px">Slett konto</button></div>
    </div>`;
}
function wireAccountSection(){
  const a = window.Auth && window.Auth.state;
  if(!a || !a.ready) return;
  if(!a.user){
    const send = $("#authSend");
    if(send) send.onclick = async ()=>{
      const email = $("#authEmail").value.trim();
      const msg = $("#authMsg");
      if(!email){ return; }
      send.disabled = true;
      try{
        await Auth.sendLoginLink(email);
        msg.textContent = "Sjekk e-posten din for innloggingslenke.";
        msg.style.display = "block";
      }catch(e){
        msg.textContent = "Kunne ikke sende lenke: " + e.message;
        msg.style.display = "block";
      }finally{ send.disabled = false; }
    };
    return;
  }
  const saveBtn = $("#authSaveName");
  if(saveBtn) saveBtn.onclick = async ()=>{
    const name = $("#authName").value.trim();
    if(!name) return;
    saveBtn.disabled = true;
    try{ await Auth.saveDisplayName(name); toast("Navn lagret"); }
    catch(e){ toast("Kunne ikke lagre navn: " + e.message); }
    finally{ saveBtn.disabled = false; }
  };
  const logoutBtn = $("#authLogout");
  if(logoutBtn) logoutBtn.onclick = ()=>Auth.signOut();
  const delBtn = $("#authDelete");
  if(delBtn) delBtn.onclick = async ()=>{
    if(!confirm("Slette kontoen din? Dette kan ikke angres.")) return;
    delBtn.disabled = true;
    try{ await Auth.deleteAccount(); toast("Kontoen er slettet"); }
    catch(e){ toast("Sletting feilet: " + e.message); delBtn.disabled = false; }
  };
}
window.addEventListener("authchange", ()=>{
  if(!DATA || !window.Front) return; // ikke lastet ferdig ennå
  Front.refresh();
});

function renderSettings(){
  const cfg = loadSync(), n = DATA.notify || {};
  const status = cfg.error ? `Siste synk feilet: ${esc(cfg.error)}`
    : cfg.last ? `Sist synket ${relDay(new Date(cfg.last))} kl. ${fmtTime.format(new Date(cfg.last))}` : "Ikke synket ennå";
  $("#detailPane").innerHTML = `<header class="top"><h1>Innstillinger</h1></header>
    ${accountSectionHtml()}
    <h2 class="sec">Varsler</h2>
    <div class="form">
      <p>Du får varsel når en spot får <b>${n.min_stars??3} stjerner eller mer</b> i brukbart lys, inntil <b>${n.hours_ahead??36} timer</b> frem. ${n.spots&&n.spots.length?`Gjelder ${n.spots.map(esc).join(", ")}.`:"Gjelder alle spots."}</p>
      <p>Varslene kommer i ntfy-appen. Grensen endres i notify.json.</p>
    </div>
    <h2 class="sec">Sikkerhetskopi av logger</h2>
    <div class="form">
      <p>Loggene lagres i et privat GitHub-repo. Da mister du dem ikke, og varselet lærer av dem automatisk.</p>
      <label for="syncRepo">Repo</label><input type="text" id="syncRepo" placeholder="brukernavn/nordsurf-logger" value="${esc(cfg.repo||"")}" autocapitalize="off" autocorrect="off" spellcheck="false">
      <label for="syncToken">Tilgangsnøkkel</label><input type="password" id="syncToken" placeholder="github_pat_..." value="${esc(cfg.token||"")}" autocomplete="off">
      <p>${status}</p>
      <div class="row-btns"><button class="primary" id="saveSync" style="min-height:44px">Lagre og synk</button></div>
    </div>
    <h2 class="sec">Eksport</h2>
    <div class="form"><p>${loadLogs().length} økter på denne telefonen.</p>
      <div class="row-btns"><button class="ghost" id="export">Eksporter logger</button></div></div>`;
  $("#saveSync").onclick = ()=>{
    saveSync({...loadSync(), repo:$("#syncRepo").value.trim(), token:$("#syncToken").value.trim(), error:null});
    syncLogs(true);
  };
  $("#export").onclick = ()=>{
    const blob = new Blob([JSON.stringify(loadLogs(),null,2)],{type:"application/json"});
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "nordsurf-logger.json"; a.click();
  };
  wireAccountSection();
}

/* ---------- Loggeark ---------- */
function updateLogTimeText(){
  // Norsk, 24-timers visning av valgt tidspunkt under feltet - selve
  // <input type="datetime-local"> følger nettleserens språk, ikke sidens
  // lang="nb", så dette er garantien for norsk format (punkt 6, 09.10.2026).
  // Formateres i ENHETENS tidssone (samme som feltet og som lagringen
  // tolker verdien i), ikke Europe/Oslo - ellers viser teksten en annen
  // time enn feltet utenfor norsk tid (fysikk-kontrollør 09.10.2026).
  const el = $("#logTimeText"); if(!el) return;
  const v = $("#logTime").value; const d = v ? new Date(v) : null;
  el.textContent = d && !isNaN(d) ? cap(new Intl.DateTimeFormat("nb-NO",{weekday:"long",day:"numeric",month:"long",hour:"2-digit",minute:"2-digit",hour12:false}).format(d)) : "";
}
function localInputValue(d){
  const p = new Intl.DateTimeFormat("sv-SE",{timeZone:TZ,year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"}).format(d);
  return p.replace(" ","T");
}
function openSheet(spotId, time){
  // ROADMAP oppgave F: kalt uten argumenter fra verktøylinjens "Logg økt"
  // (nåværende spot/nå, som før) - kalt MED fra kartets trykk-og-hold
  // (map.js) og fra "Logg fra bilde" (bildets foreslåtte tidspunkt).
  logDraft = {spot: spotId || (Front.state.spotId || DATA.spots[0].id), stars:null, size:null, wind:null, type:"own", source:null};
  $("#logSpot").innerHTML = DATA.spots.map(s=>`<option value="${s.id}"${s.id===logDraft.spot?" selected":""}>${esc(s.name)}</option>`).join("");
  $("#logTime").value = localInputValue(time || new Date());
  $("#logTime").oninput = updateLogTimeText;  // følger også tid endret for hånd
  updateLogTimeText();
  $("#starPick").innerHTML = [0,1,2,3,4,5].map(n=>`<button aria-pressed="false" data-n="${n}"><b>${n}</b>${PICK_WORDS[n]}</button>`).join("");
  document.querySelector('[data-group="size"]').innerHTML = SIZES.map(v=>`<button aria-pressed="false">${v}</button>`).join("");
  document.querySelector('[data-group="wind"]').innerHTML = WINDS.map(v=>`<button aria-pressed="false">${v}</button>`).join("");
  // Type: egen økt eller observert (sett selv, eller via en pålitelig kilde
  // uten å surfe). Eksklusivt valg (alltid ett av de to), ikke en valgfri
  // av/på-brikke som størrelse/vind - derfor egen håndtering under, ikke
  // den generiske .chips-logikken (chips-en har klassen "excl" for det).
  document.querySelector('[data-group="type"]').innerHTML = ["Egen økt","Observert"].map((v,i)=>`<button aria-pressed="${i===0}">${v}</button>`).join("");
  $("#sourceField").hidden = true;
  $("#logSource").value = "";
  document.querySelector('[data-group="type"]').querySelectorAll("button").forEach((b,i)=>b.onclick=()=>{
    document.querySelector('[data-group="type"]').querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed","false"));
    b.setAttribute("aria-pressed","true");
    logDraft.type = i===0 ? "own" : "observed";
    $("#sourceField").hidden = logDraft.type !== "observed";
  });
  $("#saveLog").disabled = true;
  $("#starPick").querySelectorAll("button").forEach(b=>b.onclick=()=>{
    $("#starPick").querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed","false"));
    b.setAttribute("aria-pressed","true"); logDraft.stars = +b.dataset.n; $("#saveLog").disabled = false;
  });
  document.querySelectorAll(".chips:not(.excl)").forEach(g=>g.querySelectorAll("button").forEach(b=>b.onclick=()=>{
    const on = b.getAttribute("aria-pressed")==="true";
    g.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed","false"));
    b.setAttribute("aria-pressed", on ? "false" : "true");
    logDraft[g.dataset.group] = on ? null : b.textContent;
  }));
  $("#sheet").classList.add("open"); $("#scrim").classList.add("open"); $("#sheet").setAttribute("aria-hidden","false");
  setTimeout(()=>$("#starPick button").focus(), 50);
}
window.openSheet = openSheet;
function closeSheet(){
  $("#sheet").classList.remove("open"); $("#scrim").classList.remove("open"); $("#sheet").setAttribute("aria-hidden","true");
}
$("#cancelLog").onclick = closeSheet; $("#scrim").onclick = closeSheet;
document.addEventListener("keydown", e=>{ if(e.key==="Escape"){ closeSheet(); closeBreakdown(); } });

/* ---------- "Logg fra bilde" (ROADMAP oppgave F) ----------
   Bildet lastes ALDRI opp eller lagres noe sted - bare lest i minnet her
   (ArrayBuffer) for å finne et tidspunkt, så kastes referansen (selve
   input-elementets value nullstilles etter bruk). Bare loggen (tall, ikke
   bildet) lagres, akkurat som en vanlig økt. */
function parseExifDate(buf){
  // EXIF sitt DateTimeOriginal (helst) eller DateTime, fra JPEG sin APP1-
  // seksjon. Returnerer en lokal Date, eller null (ikke JPEG, ingen EXIF,
  // eller feltet mangler - svært vanlig for skjermbilder, som sjelden har
  // EXIF i det hele tatt).
  try{
    const view = new DataView(buf);
    if(view.getUint16(0) !== 0xFFD8) return null;
    let offset = 2;
    while(offset + 4 <= view.byteLength){
      if(view.getUint8(offset) !== 0xFF) break;
      const marker = view.getUint8(offset+1);
      if(marker === 0xD8 || marker === 0x01 || (marker >= 0xD0 && marker <= 0xD9)){ offset += 2; continue; }
      const segLen = view.getUint16(offset+2);
      if(marker === 0xE1 && view.getUint32(offset+4) === 0x45786966 && view.getUint16(offset+8) === 0){
        const d = parseExifTiff(view, offset+10);
        if(d) return d;
      }
      if(marker === 0xDA) break; // start of scan - EXIF kommer alltid før dette
      offset += 2 + segLen;
    }
  }catch(e){}
  return null;
}
function parseExifTiff(view, tiffStart){
  const little = view.getUint16(tiffStart) === 0x4949;
  const g16 = o => view.getUint16(o, little), g32 = o => view.getUint32(o, little);
  function readIFD(ifdOffset){
    const n = g16(ifdOffset), tags = {};
    for(let i=0;i<n;i++){
      const e = ifdOffset + 2 + i*12;
      tags[g16(e)] = {count: g32(e+4), valueOffset: e+8};
    }
    return tags;
  }
  function readAscii(entry){
    let start = entry.valueOffset;
    if(entry.count > 4) start = tiffStart + g32(entry.valueOffset);
    let s = "";
    for(let i=0;i<entry.count-1;i++) s += String.fromCharCode(view.getUint8(start+i));
    return s;
  }
  const ifd0 = readIFD(tiffStart + g32(tiffStart+4));
  let s = null;
  if(ifd0[0x8769]){
    const exifIfd = readIFD(tiffStart + g32(ifd0[0x8769].valueOffset));
    s = (exifIfd[0x9003] && readAscii(exifIfd[0x9003])) || (exifIfd[0x9004] && readAscii(exifIfd[0x9004])) || null;
  }
  if(!s && ifd0[0x0132]) s = readAscii(ifd0[0x0132]);
  if(!s) return null;
  const m = s.match(/^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
  if(!m) return null;
  const d = new Date(+m[1], +m[2]-1, +m[3], +m[4], +m[5], +m[6]);
  return isNaN(d.getTime()) ? null : d;
}
function parseFilenameDate(name){
  // Reserve når EXIF mangler: vanlige filnavn-mønstre fra telefon-kameraer
  // og skjermbilder (f.eks. IMG_20261006_143022.jpg, Screenshot_2026-10-06-
  // 14-30-22.png, 2026-10-06 14.30.22.jpg).
  const m = name.match(/(\d{4})-?(\d{2})-?(\d{2})[ _T-](\d{2})[.:-]?(\d{2})[.:-]?(\d{2})/);
  if(!m) return null;
  const d = new Date(+m[1], +m[2]-1, +m[3], +m[4], +m[5], +m[6]);
  return isNaN(d.getTime()) ? null : d;
}
$("#logFromPhotoBtn").onclick = ()=>$("#logPhotoInput").click();
$("#logPhotoInput").onchange = async ()=>{
  const input = $("#logPhotoInput");
  const file = input.files && input.files[0];
  if(!file) return;
  let when = null;
  try{
    const buf = await file.arrayBuffer();
    when = parseExifDate(buf);
  }catch(e){}
  if(!when) when = parseFilenameDate(file.name);
  if(!when) when = new Date(file.lastModified);
  input.value = ""; // bildet er ferdig lest - ingen referanse beholdes
  if(!$("#sheet").classList.contains("open")) openSheet(null, when);
  else $("#logTime").value = localInputValue(when);
  updateLogTimeText();
  toast(STR.toast.photoDate(`${relDay(when)} kl. ${fmtTime.format(when)}`));
  const typeBtns = document.querySelector('[data-group="type"]').querySelectorAll("button");
  if(typeBtns[1]) typeBtns[1].click(); // "Observert"
  $("#logSource").value = "Bilde";
};

/* ---------- Forklaring av ratingen ---------- */
function breakdownRowHtml(line, isTotal){
  const idx = line.indexOf(": ");
  if(idx<0) return `<div class="row${isTotal?" total":""}"><span class="lead">${esc(line)}</span></div>`;
  return `<div class="row${isTotal?" total":""}"><span class="lead">${esc(line.slice(0,idx))}</span><span class="eff">${esc(line.slice(idx+2))}</span></div>`;
}
function openBreakdown(h){
  if(!h.breakdown || !h.breakdown.length) return;
  const ex = ratingWordExplain(h);
  $("#bdBody").innerHTML = (ex ? `<p class="bd-note"><b>${esc(ratingWord(h))}</b> – ${esc(ex)}</p>` : "") + h.breakdown.map((line,i)=>breakdownRowHtml(line, i===h.breakdown.length-1)).join("");
  $("#bdSheet").classList.add("open"); $("#bdScrim").classList.add("open"); $("#bdSheet").setAttribute("aria-hidden","false");
}
function closeBreakdown(){
  $("#bdSheet").classList.remove("open"); $("#bdScrim").classList.remove("open"); $("#bdSheet").setAttribute("aria-hidden","true");
}
$("#bdClose").onclick = closeBreakdown; $("#bdScrim").onclick = closeBreakdown;
$("#saveLog").onclick = ()=>{
  const spot = $("#logSpot").value;
  const t = new Date($("#logTime").value);
  const f = forecastAt(spot, t);
  const entry = {id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()), spot, t: t.toISOString(),
    stars: logDraft.stars, size: logDraft.size, wind: logDraft.wind,
    // Egen økt eller observert (sett selv/pålitelig kilde uten å surfe) -
    // teller likt i surf_factor/bias/tidevann, vises ulikt i Økter-lista.
    type: logDraft.type, source: logDraft.type==="observed" ? ($("#logSource").value.trim() || null) : null,
    forecastStars: f ? f.stars : null, forecastFaded: f ? f.faded : null,
    forecastHeight: f ? f.height : null, swellOffshore: f ? f.swell_offshore : null,
    // Perioden ute (Open-Meteo) på loggtidspunktet - trengs sammen med
    // forecastHeight for å regne ut Hb (surf_factor-læringen).
    forecastPeriod: f ? f.period : null,
    directness: f ? f.directness : null,
    // Retningen svellet ute kom fra på loggtidspunktet - til eksponerings-
    // figuren i Logger-fanen (del B, ROADMAP oppgave 4), som merker loggene
    // dine på retningen de gjelder for. Eldre logger mangler dette feltet -
    // figuren viser dem bare ikke.
    dirOffshore: f ? f.dir_offshore : null,
    // BarentsWatch 250 m (brukt i varselet) og 150 m (bare sammenligning),
    // slik de sto på tidspunktet du logget - se "hvilket punkt treffer best"
    // i Logger-fanen.
    bwHeight: f ? f.bw_height : null, bwHeightNear: f ? f.bw_height_near : null,
    // Hvor mye av BarentsWatch-høyden som er reelt svell og hvor godt det
    // traff stranda, slik at Logger-fanen kan vise om sources_disagree-
    // regelen er for streng eller for snill.
    swellShare: f ? f.swell_share : null, spotDirectionFactor: f ? f.spot_direction_factor : null,
    bwPeriod: f ? f.bw_period : null, bwDir: f ? f.bw_dir : null,
    sourcesDisagree: f ? !!f.sources_disagree : false,
    // 06.10.2026, Theodors oppgave: tidevannstilstand og totalenergi slik de
    // sto på loggtidspunktet - trengs for å sjekke loggene dine mot myke
    // lokale regler (local_rules, se CLAUDE.md "Lokalkunnskap") i etterkant,
    // se localRuleSuggestions() i Logger-fanen. Eldre logger mangler dette
    // feltet - forslaget hopper da bare over dem, samme mønster som
    // dirOffshore over.
    // 06.10.2026, andre runde: energy_factor() bruker nå SVELLenergien
    // (energySwellKj), ikke totalhøyden - lagrer begge (totalen vises andre
    // steder, f.eks. "Svell ute"-cella når svell_offshore mangler).
    tideState: f && f.tide ? f.tide.state : null, energyTotalKj: f ? f.energy_total_kj : null,
    energySwellKj: f ? f.energy_swell_kj : null};
  const ok = saveLogs([...loadLogs(), entry]);
  closeSheet();
  toast(ok ? "Økt logget" : "Kunne ikke lagre. Sjekk at nettleseren tillater lagring.");
  syncLogs();
  Front.refresh();
};

let toastTimer;
function toast(msg, action, fn, duration){
  const el = $("#toast"); el.innerHTML = esc(msg);
  if(action){ el.style.pointerEvents="auto"; const b=document.createElement("button"); b.className="link"; b.style.color="inherit"; b.style.textDecoration="underline"; b.textContent=action; b.onclick=()=>{fn(); el.classList.remove("show");}; el.append(" ", b); }
  else el.style.pointerEvents="none";
  el.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(()=>el.classList.remove("show"), duration||4000);
}



/* ---------- Oppstart ---------- */
async function start(){
  // Kart først (09.10.2026): forsiden er kartet (js/kart.js + js/front.js).
  // app.js er biblioteket: loggarket, logger, innstillinger, breakdown,
  // forklaringer, Detaljer-rutenettet og formateringen.
  const wm = $("#wordmark"); if(wm) wm.innerHTML = wordmarkSvg();
  try{
    DATA = window.__FORECAST__ || await (await fetch("data/forecast.json",{cache:"no-cache"})).json();
    if(!DATA.spots || !DATA.spots.length) throw new Error("tom");
    const gen = new Date(DATA.generated);
    $("#updated").textContent = DATA.sample ? STR.exampleSub : STR.updated(relDay(gen), fmtTime.format(gen));
    await Front.start(DATA);
    syncLogs();
    recordWitness();
    maybeShowWitnessPrompt();
  }catch(e){
    console.error(e);
    $("#loading").textContent = STR.noData; $("#loading").hidden = false;
  }
}
// start() kalles fra js/front.js når kartmotoren er lastet (kart først, 09.10.2026).
if("serviceWorker" in navigator && location.protocol==="https:" && !window.__FORECAST__) navigator.serviceWorker.register("sw.js").catch(()=>{});

/* ---------- "Var du der?" (ROADMAP oppgave F) ----------
   Appen er statisk og har ingen egen historikk-API - s.hours fra
   forecast.json inneholder ALDRI timer før "nå" på hente-tidspunktet (se
   fetch.py sin build_spot(), loopen starter alltid på now). Derfor bygges
   en LITEN, egen "vitne"-logg i localStorage, fylt på hver gang appen
   laster et nytt varsel og en favoritt sin nåværende time er ny - en
   TILNÆRMING (fanger bare vinduer som skjedde mens appen faktisk var åpnet
   en gang nær tidspunktet), ikke en fullstendig historikk. */
const WITNESS_KEY = "nordsurf.witness.v1";
const WITNESS_ASKED_KEY = "nordsurf.witnessAsked.v1";
const WITNESS_MIN_STARS = 3;
const WITNESS_MAX_AGE_H = 30; // hvor lenge et vitnet godt vindu fortsatt kan spørres om
function loadWitness(){ try{ return JSON.parse(localStorage.getItem(WITNESS_KEY)) || []; }catch(e){ return []; } }
function loadWitnessAsked(){ try{ return JSON.parse(localStorage.getItem(WITNESS_ASKED_KEY)) || []; }catch(e){ return []; } }
function recordWitness(){
  if(!DATA || !DATA.spots) return;
  const favs = (window.Auth && Auth.state && Auth.state.favorites) || new Set();
  if(!favs.size) return;
  const w = loadWitness();
  const seen = new Set(w.map(x=>x.spot+"|"+x.t));
  let changed = false;
  for(const s of DATA.spots){
    if(!favs.has(s.id)) continue;
    // Bare timer som allerede har startet (nåværende time og evt. én til som
    // fortsatt henger med fra forrige kjøring) - aldri fremtidige anslag.
    for(const h of s.hours.slice(0,2)){
      if(new Date(h.t).getTime() > Date.now()) continue;
      const key = s.id+"|"+h.t;
      if(seen.has(key)) continue;
      seen.add(key); changed = true;
      w.push({spot:s.id, t:h.t, stars:h.stars, daylight: h.daylight!==false});
    }
  }
  const cutoff = Date.now() - WITNESS_MAX_AGE_H*3600e3;
  const pruned = w.filter(x=>new Date(x.t).getTime() >= cutoff);
  if(changed || pruned.length!==w.length) try{ localStorage.setItem(WITNESS_KEY, JSON.stringify(pruned)); }catch(e){}
}
function pendingWitness(){
  const askedSet = new Set(loadWitnessAsked());
  const cand = loadWitness().filter(x=>x.stars>=WITNESS_MIN_STARS && x.daylight && !askedSet.has(x.spot+"|"+x.t));
  if(!cand.length) return null;
  cand.sort((a,b)=>b.t.localeCompare(a.t));
  return cand[0];
}
function markWitnessAsked(entry){
  try{
    const asked = loadWitnessAsked();
    asked.push(entry.spot+"|"+entry.t);
    localStorage.setItem(WITNESS_ASKED_KEY, JSON.stringify(asked.slice(-200)));
  }catch(e){}
}
function maybeShowWitnessPrompt(){
  const entry = pendingWitness();
  if(!entry) return;
  const spot = DATA.spots.find(s=>s.id===entry.spot);
  if(!spot) return;
  const when = new Date(entry.t);
  $("#witnessSub").textContent = `${spot.name}, ${relDay(when)} kl. ${fmtHour.format(when)} - varselet viste ${entry.stars} av 5 stjerner.`;
  $("#witnessPick").innerHTML = PICK_WORDS.map((w,n)=>`<button data-n="${n}"><b>${n}</b>${w}</button>`).join("");
  $("#witnessPick").querySelectorAll("button").forEach(b=>b.onclick=()=>{
    const stars = +b.dataset.n;
    const f = forecastAt(entry.spot, when);
    const log = {id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()), spot: entry.spot, t: when.toISOString(),
      stars, size: null, wind: null, type: "observed", source: "Var du der?",
      forecastStars: entry.stars, forecastFaded: f ? f.faded : null, forecastHeight: f ? f.height : null,
      swellOffshore: f ? f.swell_offshore : null, forecastPeriod: f ? f.period : null, directness: f ? f.directness : null,
      dirOffshore: f ? f.dir_offshore : null, bwHeight: f ? f.bw_height : null, bwHeightNear: f ? f.bw_height_near : null,
      swellShare: f ? f.swell_share : null, spotDirectionFactor: f ? f.spot_direction_factor : null,
      bwPeriod: f ? f.bw_period : null, bwDir: f ? f.bw_dir : null, sourcesDisagree: f ? !!f.sources_disagree : false,
      tideState: f && f.tide ? f.tide.state : null, energyTotalKj: f ? f.energy_total_kj : null, energySwellKj: f ? f.energy_swell_kj : null};
    saveLogs([...loadLogs(), log]);
    markWitnessAsked(entry);
    closeWitness();
    toast("Takk! Lagret som økt.");
    syncLogs();
    Front.refresh();
  });
  $("#witnessSheet").classList.add("open"); $("#witnessScrim").classList.add("open"); $("#witnessSheet").setAttribute("aria-hidden","false");
}
function closeWitness(){
  $("#witnessSheet").classList.remove("open"); $("#witnessScrim").classList.remove("open"); $("#witnessSheet").setAttribute("aria-hidden","true");
}
$("#witnessSkip").onclick = ()=>{ const e = pendingWitness(); if(e) markWitnessAsked(e); closeWitness(); };
$("#witnessScrim").onclick = closeWitness;

