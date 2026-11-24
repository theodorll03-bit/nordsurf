/* Nordsurf: skallet - Hjem, søk, ruter, spotvisning (Theodor 14.10.2026; Tillegg 2 15.10.2026).

   Tillegg 2: forsiden laster ikke timer. oversikt.json (oversikt-2, fetcher/publish.py) har
   per spot bare meta, «naa» (nå-timen og de tre neste) og «dager» (dagssammendrag for 7 døgn:
   beste time i dagslys etter publish.best_hour(), spennet, mangler/mørkt). Hjem, søk, Utforsk
   og nett-tabellen leser bare det; spots/<id>.json (hele meta + alle timene) lastes når en
   spot åpnes (app.js ensureSpot). Regioner (navn, rekkefølge, utsnitt) kommer fra
   oversikt.regions (spots.json) - ingen lister i JS.

   Ren visning: ord og tall fra ratingWord()/varselets felt; «–» når tallet mangler. */
(function(){
  const $ = (s, r)=> (r||document).querySelector(s);
  const $$ = (s, r)=> [...(r||document).querySelectorAll(s)];
  const S = { view:"hjem", from:"hjem", spotId:null, idx:null, tIso:null, q:"", utforskDay:null, utforskView:null, picked:null, now:null, visAlle:{}, region:null, sokFlere:false, fsDag:0, fsRegion:null, fsAlle:false };
  window.__S = S;
  let started = false;

  /* ---------- data (oversikt-2) ---------- */
  const regionOf = (s)=> s.region || s.area || "";
  /* ROADMAP K del C.4 (bare visning, ratingen røres ikke): nye spots (status «forelopig», tools/godkjenn_spot.py)
     har merkelappen «Foreløpig» og er ikke med i «Beste økt» de første 14 dagene; spots med ferdsels- eller
     surfeforbud (fra verneforskriften, data/kandidater/vern.json) vises med «Forbud nå» i perioden og er aldri
     med i «Beste økt» da. Mangler forelopig_fra regnes spoten som ny (ikke anbefalt før datoen er kjent).
     23.11.2026 (bw_tillit, svar.md 23.11.2026 kl. 14.00 og 14.05): en spot der andelen er satt uten observasjon
     (andel_forelopig i spots.json) har samme merkelapp. Den er med i «Beste økt» som før (nyForelopig() ser bare på status). */
  const FORELOPIG_DAGER = 14;
  const MD_FMT = new Intl.DateTimeFormat("en-CA", {month:"2-digit", day:"2-digit", timeZone:TZ});   // én gang - kalles per spot per bilde
  const osloMD = (t)=>{ const p = MD_FMT.formatToParts(new Date(t)); return `${p.find(x=>x.type==="month").value}-${p.find(x=>x.type==="day").value}`; };
  function forbudNa(s, t){
    if(!s.restriksjoner || !s.restriksjoner.length) return false;   // de fleste spots: ingen datoregning
    const md = osloMD(t==null ? Date.now() : t);
    return (s.restriksjoner || []).some(r=> ["ferdselsforbud", "surfeforbud"].includes(r.type) && ["sjø", "strand", "begge"].includes(r.gjelder)
      && (!r.fra || !r.til || (r.fra <= r.til ? md >= r.fra && md <= r.til : md >= r.fra || md <= r.til)));
  }
  // Theodor 16.10.2026: i forbudsperioden erstattes stjerner og ord med «Surfing forbudt nå» og perioden
  // («1. okt–31. mars, fuglefredning»); utenfor perioden vises spoten vanlig, med en linje om forbudet.
  const MND = ["jan", "feb", "mars", "april", "mai", "juni", "juli", "aug", "sep", "okt", "nov", "des"];
  const mdTekst = (md)=>{ const [m, d] = md.split("-").map(Number); return `${d}. ${MND[m-1]}`; };
  const forbudRestr = (s)=> (s.restriksjoner || []).filter(r=> ["ferdselsforbud", "surfeforbud"].includes(r.type) && ["sjø", "strand", "begge"].includes(r.gjelder));
  const periodeTekst = (r)=> `${r.fra && r.til ? `${mdTekst(r.fra)}–${mdTekst(r.til)}` : "hele året"}${r.grunn ? ", " + r.grunn : ""}`;
  function forbudInfo(s, t){
    if(!s.restriksjoner || !s.restriksjoner.length) return null;
    const md = osloMD(t==null ? Date.now() : t);
    const r = forbudRestr(s).find(r=> !r.fra || !r.til || (r.fra <= r.til ? md >= r.fra && md <= r.til : md >= r.fra || md <= r.til));
    return r ? {tittel: "Surfing forbudt nå", periode: periodeTekst(r), r} : null;
  }
  const forbudLinje = (s)=>{ const rs = forbudRestr(s); return rs.length ? rs.map(r=> `${r.type==="surfeforbud" ? "Surfing" : "Ferdsel"} forbudt ${periodeTekst(r)}`).join(" · ") : null; };
  // nå-visningen i lister og kort: i forbudsperioden ingen vurdering, ordet «Surfing forbudt nå», ingen høyde.
  // `rute` sier hvorfor ruta er tom: «forbud», «miss» (tallet mangler) eller «mork» (mørk time: sola under −6°,
  // ingen vurdering på skjermen - SPEC §5; høyden står, ordet er «Mørkt»). Ellers null, og ruta viser tallet.
  function naaVisning(s, h){
    if(forbudNa(s)) return {st: 0, rute: "forbud", oh: {ord: "Surfing forbudt nå", hoyde: null, forbud: true}};
    if(!known(h)) return {st: 0, rute: "miss", oh: ordOgHoyde(h)};
    if(mork(h)) return {st: 0, rute: "mork", oh: {ord: "Mørkt", hoyde: ordOgHoyde(h).hoyde}};
    return {st: stars(h), rute: null, oh: ordOgHoyde(h)};
  }
  // spotsiden: timene i forbudsperioden merkes (_forbud) i en kopi - grafen, dagfanene og kortene viser da ingen
  // stjerner, ordet «Surfing forbudt» og ingen høyde. Selve varselet (og ratingen) er urørt.
  function forbudKopi(s){
    if(!forbudRestr(s).length || !s.hours) return s;
    return {...s, hours: s.hours.map(h=> h && forbudInfo(s, Date.parse(h.t)) ? {...h, stars: 0, faded: 0, _forbud: true} : h)};
  }
  const nyForelopig = (s)=> s.status==="forelopig" && !(s.forelopig_fra && Date.now() - Date.parse(s.forelopig_fra) >= FORELOPIG_DAGER*864e5);
  const iBesteOkt = (s, t)=> !nyForelopig(s) && !forbudNa(s, t);
  const merker = (s)=> [s.status==="forelopig" || s.andel_forelopig ? STR.forelopig : null, forbudRestr(s).length ? forbudLinje(s) : null].filter(Boolean);
  const omrMerker = (s)=> [s.area, ...merker(s)].filter(Boolean).join(" · ");
  const stedText = (s)=>{ const r = regionOf(s); return [s.area && s.area!==r ? `${s.area} · ${r}` : (s.area || r), ...merker(s)].join(" · "); };
  const regions = ()=> (DATA.regions || []).map(r=>r.name);
  const REGION_KEY = "nordsurf.region";
  function chosenRegion(){
    // Innstillinger -> Område; standard Troms (ellers første region). Aldri hele Norge.
    const rs = regions();
    try{ const v = localStorage.getItem(REGION_KEY); if(v && rs.includes(v)) return v; }catch(e){}
    return rs.includes("Troms") ? "Troms" : (rs[0] || "");
  }
  function setRegion(r){ try{ localStorage.setItem(REGION_KEY, r); }catch(e){} S.region = r; }
  // nå-timen: klokkas time blant de publiserte (fire om dagen - henteren kjører hver 3. time; sju etter kveldens siste
  // kjøring, fram til den neste kl. 03 UTC - publish.py naa_hours), ellers den siste
  // dekker ingen av dem klokka (oversikten er over 4 t gammel, 7 om natta - henteren har feilet): null → «–», aldri en time
  // som er over vist som «nå» (fysikk-kontrollør 15.10.2026); staleBanner() øverst på Hjem sier fra
  const naaOf = (s)=>{ const list = s.naa || []; const now = Date.now(); const h = list.find(h=> new Date(h.t).getTime() + 36e5 > now); if(h) return h; const last = list[list.length-1]; return last && now - new Date(last.t).getTime() < 36e5 ? last : null; };
  const stars = (h)=> h ? (h.stars||0) : 0;
  const known = (h)=> !!h && !(!h.stars && !h.low_reason && h.surf_height==null);
  const lightOf = (h)=> h ? (h.light || (h.daylight===false ? "mørkt" : h.daylight===true ? "dag" : null)) : null;
  const usable = (h)=>{ const l = lightOf(h); return l==="dag" || l==="skumring"; };
  const mork = (h)=> lightOf(h)==="mørkt";   // mørk time: vises uten vurdering (SPEC §5); modellen regner som før
  // spotsiden (hele timelista): klokkas time
  const nowIdx = (s)=> s.hours && s.hours.length ? Math.max(0, Math.min(s.hours.length-1, currentHour(s))) : 0;
  const fmtDato = new Intl.DateTimeFormat("nb-NO", {weekday:"long", day:"numeric", month:"long", timeZone:TZ});
  const DK = new Map();
  const dkOf = (t)=>{ let k = DK.get(t); if(k===undefined){ k = dayKey(new Date(t)); DK.set(t, k); } return k; };
  const isDesktop = ()=> matchMedia("(min-width: 1024px)").matches;
  const norm = (s)=> String(s||"").toLowerCase().replace(/æ/g,"ae").replace(/ø/g,"o").replace(/å/g,"a").normalize("NFD").replace(/[̀-ͯ]/g,"");
  const spotById = (id)=> DATA.spots.find(x=>x.id===id);
  const numHtml = (t)=> esc(t).replace(/\d[\d,.–]*/g, m=>`<span class="num">${m}</span>`);
  const min5 = (n)=> Math.min(5, n||0);
  function heightText(h){
    // «1,6–2,1 m» (høyden som vises–settene); regel (c) via Spot.visHoyde; tallet mangler → null
    const v = window.Spot ? Spot.visHoyde(h) : (h && h.surf_height!=null ? {a: h.surf_height, b: h.surf_height_sets} : null);
    if(!v) return null;
    const a = nf1.format(v.a), b = v.b!=null ? nf1.format(v.b) : null;
    return b!=null && b!==a ? `${a}–${b}` : a;
  }
  function ordOgHoyde(h){
    if(!h) return {ord:"–", hoyde:null};
    const ord = ratingWord(h);
    const v = window.Spot ? Spot.visHoyde(h) : null;
    const show = v!=null && (stars(h) >= 1 || v.a >= 0.3);
    return {ord, hoyde: show ? heightText(h) : null};
  }
  function windText(h){
    if(!h || h.wind_speed==null) return null;
    return `${windMsText(h)} m/s${h.wind_type ? " " + windLabel(h) : ""}`;
  }
  // Dagens lys er over (Theodor 15.10, PR #12 punkt c): «over» fra henteren, eller klokka har passert
  // siste lyse time (lys_til) siden oversikten ble laget. Da vises ingenting for dagen.
  const dayOver = (d)=> !!d && (d.status==="over" || (!!d.lys_til && Date.now() >= new Date(d.lys_til).getTime() + 36e5));
  const UKE_DAGER = 7;
  function weekDays(){
    // 7 døgn fra i dag (norsk tid); er dagens lys over for alle spots, starter ukeradene på i morgen
    const base = (DATA.spots[0] && DATA.spots[0].dager) || [];
    const skip = base.length > UKE_DAGER && DATA.spots.every(s=> dayOver((s.dager || [])[0])) ? 1 : 0;
    return base.slice(skip, skip + UKE_DAGER).map((d, j)=>{ const k = j + skip; const at = new Date(d.d + "T11:00:00Z"); return {key: d.d, kort: fmtDayShort.format(at).replace(/\.$/, "").slice(0, 2).toLowerCase(), dato: at.getUTCDate(), lang: fmtDay.format(at), idag: k===0}; });
  }
  function dayBest(s, key){
    // dagssammendraget fra publish.best_hour(): «miss» = tallet/lyset mangler, «dark» = mørkt hele dagen, «over» = dagens lys er over
    const d = (s.dager || []).find(x=>x.d===key);
    if(dayOver(d)) return {cls:"over", st:null, h:null, t:null};
    if(forbudInfo(s, Date.parse(key + "T12:00:00Z"))) return {cls:"forbud", st:null, h:null, t:null};   // surfing forbudt den dagen
    if(d && d.status==="dark") return {cls:"dark", st:null, h:null, t:null};   // før !d.h - en mørk dag har ingen time
    if(!d || d.status==="miss" || !d.h) return {cls:"miss", st:null, h:null, t:null};
    const st = stars(d.h);
    return {cls:`r-${min5(st)}`, st, h:d.h, t:d.h.t, start:d.start || d.h.t, slutt:d.slutt || d.h.t, lo:d.lo, hi:d.hi};
  }
  function ukeHtml(s, days, withLetters){
    const cells = days.map(d=>{ const b = dayBest(s, d.key); const n = b.st!=null ? b.st : ""; const title = b.cls==="forbud" ? `${d.lang}: surfing forbudt` : b.cls==="over" ? `${d.lang}: dagens lys er over` : b.cls==="miss" ? `${d.lang}: mangler data` : b.cls==="dark" ? `${d.lang}: mørkt` : `${d.lang}: ${STR.starsAria(b.st, 0)}`; return `<i class="${b.cls}" title="${esc(title)}">${n}</i>`; }).join("");
    // withLetters: true = dagnavnene over rutene, "under" = under (favorittradene på Hjem, SPEC §6A)
    const letters = withLetters ? days.map((d, k)=>`<b class="${d.idag?"idag":""}">${esc(d.kort)}</b>`).join("") : "";
    return `<span class="uke" aria-hidden="true">${withLetters===true ? letters : ""}${cells}${withLetters==="under" ? letters : ""}</span>`;
  }
  function ukeAria(s, days){
    return days.map(d=>{ const b = dayBest(s, d.key); return b.cls==="forbud" ? `${cap(d.lang)}: surfing forbudt` : b.cls==="over" ? `${cap(d.lang)}: dagens lys er over` : b.cls==="miss" ? `${cap(d.lang)} mangler data` : b.cls==="dark" ? `${cap(d.lang)} mørkt` : `${cap(d.lang)} ${STR.starsAria(b.st, 0)}`; }).join(", ");
  }
  function bestNow(s){ const h = naaOf(s); const f = forbudNa(s); return {st: f ? 0 : stars(h), hh: f || !h ? 0 : (h.surf_height||0)}; }
  const byRatingNow = (a, b)=>{ const x = bestNow(a), y = bestNow(b); return y.st - x.st || y.hh - x.hh || a.name.localeCompare(b.name, "nb"); };

  /* ---------- hvem bryr brukeren seg om (Tillegg 2, punkt 3) ---------- */
  function scope(){
    // favorittene og regionene de ligger i; uten favoritter: regionen fra Innstillinger -> Område
    const favs = DATA.spots.filter(s=>isFavSpot(s.id));
    if(favs.length){ const regs = new Set(favs.map(regionOf)); return {spots: DATA.spots.filter(s=> regs.has(regionOf(s))), txt: regs.size===1 ? [...regs][0] : "favorittene og områdene deres", favs: true}; }
    const r = S.region || chosenRegion();
    return {spots: DATA.spots.filter(s=> regionOf(s)===r), txt: r, favs: false};
  }

  // vinduet som klokkeslett: første time og timen etter den siste («10» og «13» for timene 10, 11 og 12)
  function vinduKl(start, slutt){
    const end = (+fmtHour.format(new Date(slutt)) + 1) % 24;
    return [fmtHour.format(new Date(start)), String(end).padStart(2, "0")];
  }
  /* ---------- Hjem på mobil (design B 4.0, SPEC §6A): topplinje, overskrift, favorittrader ---------- */
  // Brukbart lys i dag ved startstedet (KJORETID.fra): sola over −6°, samme regnestykke og 10-minutters rutenett som
  // fetcher/sun.py (elevation, light_days). Oversikten har ikke light_days, så topplinja regner selv. Bare visning.
  function solhoyde(lat, lon, ms){
    const rad = Math.PI / 180, n = ms / 864e5 + 2440587.5 - 2451545.0;
    const L = (280.460 + 0.9856474 * n) % 360, g = ((357.528 + 0.9856003 * n) % 360) * rad;
    const lam = (L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * rad, eps = (23.439 - 0.0000004 * n) * rad;
    const ra = Math.atan2(Math.cos(eps) * Math.sin(lam), Math.cos(lam)), dec = Math.asin(Math.sin(eps) * Math.sin(lam));
    const gmst = (18.697374558 + 24.06570982441908 * n) % 24;
    const ha = (gmst * 15 + lon) * rad - ra, la = lat * rad;
    return Math.asin(Math.sin(la) * Math.sin(dec) + Math.cos(la) * Math.cos(dec) * Math.cos(ha)) / rad;
  }
  function lysIDag(lat, lon, now){
    // {start, end} i ms (første og siste 10-minutter med brukbart lys), begge null når det er mørkt hele dagen;
    // hele = lyst hele døgnet (midnattssol)
    const key = dayKey(new Date(now==null ? Date.now() : now)), utc = Date.parse(key + "T00:00:00Z");
    const t0 = [1, 2].map(o=> utc - o * 36e5).find(t=> dayKey(new Date(t))===key && +fmtHour.format(new Date(t))===0);   // lokal midnatt
    if(t0==null) return null;
    let start = null, end = null, lyse = 0;
    for(let m = 0; m < 1440; m += 10){ const t = t0 + m * 6e4; if(solhoyde(lat, lon, t) > -6){ if(start==null) start = t; end = t; lyse++; } }
    return {start, end, hele: lyse===144};
  }
  function topplinjeHtml(){
    const K = window.KJORETID, now = new Date(), key = dayKey(now);
    const dato = `${cap(fmtDayShort.format(now).replace(/\.$/, ""))} ${key.slice(8, 10)}.${key.slice(5, 7)}`;
    const l = K ? lysIDag(K.fra.lat, K.fra.lon) : null;
    const lys = !l ? null : l.start==null ? STR.lightNone : l.hele ? STR.hjem.lysHele : STR.hjem.lys(fmtTime.format(new Date(l.start)), fmtTime.format(new Date(l.end)));
    return `<div class="hjem-linje"><p class="etikett">${esc([dato, lys].filter(Boolean).join(" · "))}</p>${K ? `<p class="etikett">${esc(STR.hjem.fra(K.fra.navn))}</p>` : ""}</div>`;
  }
  const dagOrd = (d)=> relDay(new Date(d.key + "T11:00:00Z"));   // «i dag», «i morgen» eller ukedagen
  // Overskriften: to korte setninger av de samme dagstallene (dayBest) som ukerutene og favorittradene viser, så den
  // aldri sier noe annet enn lista (SPEC §8). Første setning er dagen lista starter på, andre er vinduet eller neste
  // bedre dag. En rad uten tall (mangler data) regnes aldri som «ingen surf»: da sier overskriften at data mangler,
  // eller ingenting. `egne` = brukerens egne favoritter: alle rader teller. Ellers holdes nye spots og spots med
  // forbud utenfor som i «Beste økt», men bare så lenge en av de andre er surfbar.
  function overskrift(spots, days, egne){
    const H = STR.hjem;
    if(!days.length || !spots.length) return [];
    const rader = (d)=> spots.map(s=> ({s, b: dayBest(s, d.key)}));
    const ordAv = (h)=> ratingWord(h).replace(/\s+nå$/, "");   // «Ikke surfbart nå» gjelder en time, ikke en dag
    const sorter = (rs)=> rs.slice().sort((x, y)=> y.b.st - x.b.st || (y.b.h.surf_height||0) - (x.b.h.surf_height||0) || x.s.name.localeCompare(y.s.name, "nb"))[0] || null;
    const topp = (rs)=>{
      const med = rs.filter(r=> r.b.st!=null), a = egne ? null : sorter(med.filter(r=> iBesteOkt(r.s, r.b.t)));
      return a && a.b.st >= 1 ? a : sorter(med);
    };
    const alle = (rs, cls)=> rs.every(r=> r.b.cls===cls), noen = (rs, cls)=> rs.some(r=> r.b.cls===cls);
    const d0 = days[0], r0 = rader(d0), t0 = topp(r0), st0 = t0 ? t0.b.st : 0, dag0 = dagOrd(d0);
    let s1;
    if(t0 && st0 >= 1) s1 = H.ordSpot(ordAv(t0.b.h), t0.s.name, dag0);
    else if(noen(r0, "miss")) s1 = alle(r0, "miss") ? `${STR.bestNoLight}.` : H.manglerDag(dag0);
    else if(alle(r0, "over")) s1 = `${H.over}.`;
    else if(alle(r0, "forbud")) s1 = H.ord(H.forbud, dag0);
    else if(alle(r0, "dark")) s1 = H.morkt(dag0);
    else {
      // ingen surfbar: ett felles ord bare når alle radene har tall og samme ord, ellers «Ingen surf»
      const ord = new Set(r0.map(r=> r.b.st!=null ? ordAv(r.b.h) : null)), o = ord.size===1 ? [...ord][0] : null;
      // er lyset over for noen av dem, vet vi ikke hvordan dagen var der: da gjelder setningen bare resten av dagen
      s1 = noen(r0, "over") ? H.ingenRest : o && o!=="–" ? H.ord(o, dag0) : H.ingen(dag0);
    }
    const rest = days.slice(1).map(d=> ({d, rs: rader(d)}));
    // dagen med høyest tall resten av uka, men bare fra 2 poeng (Theodor 16.11.2026): en dag med 1 («Blåst ut på X
    // lørdag») er ikke verdt en setning. Den er likevel surf, så «Ingen surf de neste …» sies ikke da.
    let neste = null, surfSenere = false;
    for(const {d, rs} of rest){ const t = topp(rs); if(!t || t.b.st < 1) continue; surfSenere = true; if(t.b.st >= 2 && (!neste || t.b.st > neste.t.b.st)) neste = {t, d}; }
    const apent = !!t0 && st0 >= 1 && new Date(t0.b.slutt).getTime() + 36e5 > Date.now();   // dagens vindu er ikke over
    let s2 = null;
    if(apent && (!neste || neste.t.b.st <= st0)) s2 = H.best(...vinduKl(t0.b.start, t0.b.slutt));
    else if(neste) s2 = H.ordSpot(ordAv(neste.t.b.h), neste.t.s.name, dagOrd(neste.d));
    else if(st0 < 1 && !surfSenere && rest.length && rest.every(x=> !noen(x.rs, "miss"))) s2 = rest.length===1 ? H.ingen(dagOrd(rest[0].d)) : H.ingenNeste(rest.length);
    return [s1, s2].filter((l, i, a)=> l && a.indexOf(l)===i);
  }
  function overskriftHtml(spots, days, egne){
    const linjer = overskrift(spots, days, egne);
    return linjer.length ? `<h1 class="t-overskrift hjem-overskrift">${linjer.map(l=>`<span>${esc(l)}</span>`).join("")}</h1>` : "";
  }
  function kjoreText(id){
    // «ca. 45 min», «ca. 1 t 20 min», «ca. 7 t»; null når spoten ikke står i tabellen (js/kjoretid.js).
    // «ca.» fordi tallene er anslag fra skissene (svar 16.11.2026)
    const m = window.KJORETID && KJORETID.min[id]; if(!m) return null;
    const t = Math.floor(m / 60), r = m % 60;
    return `${STR.hjem.ca} ${t ? `${t} t${r ? ` ${r} min` : ""}` : `${r} min`}`;
  }
  function favSetning(s, b, utenVindu){
    // én setning om dagens beste time: tallene for en surfbar time, forklaringen bak ordet for en 0-time.
    // utenVindu: spotsiden viser vinduet stort ved siden av, så «Best kl. …» sies ikke en gang til
    const h = b.h;
    if(b.cls==="forbud") return forbudLinje(s);
    if(b.cls==="dark") return STR.lightOnly + ".";
    if(!h) return null;
    if(b.st < 1){
      const e = ratingWordExplain(h);
      if(e) return e.replace(/\s+[–-] se regnestykket under\.?$/, ".");
      return lowReasonNotice(h);
    }
    const hoyde = heightText(h);
    const deler = [hoyde ? `${hoyde} m` : null, h.period!=null ? `${nf0.format(h.period)} s${h.dir_offshore!=null ? " " + STR.fromDir(compass(h.dir_offshore)) : ""}` : null, windText(h)].filter(Boolean);
    // et vindu som er over, er ikke et råd (fysikk-kontrolløren 19.11.2026): da står bare tallene, som i fsApent på PC-forsiden
    if(utenVindu || !fsApent(b)) return deler.length ? cap(deler.join(", ")) + "." : null;
    return `${deler.length ? cap(deler.join(", ")) + ". " : ""}${STR.hjem.best(...vinduKl(b.start, b.slutt))}`;
  }
  function favObs(s){
    // siste egne logg på spoten de siste 7 dagene (lokale logger har ingen fritekst - bare feltene fra loggarket)
    const now = Date.now();
    const l = loadLogs().filter(l=> l.spot===s.id && l.t && Date.parse(l.t) <= now && now - Date.parse(l.t) < 7 * 864e5).sort((a, b)=> Date.parse(b.t) - Date.parse(a.t))[0];
    if(!l) return null;
    const t = new Date(l.t);
    return [`${STR.hjem.obs} ${fmtDayShort.format(t).replace(/\.$/, "")} ${fmtTime.format(t)}`, l.stars!=null ? STR.starsAria(l.stars, 0) : null, l.size, STR.logWind[l.wind] || l.wind].filter(Boolean).join(" · ");
  }
  function favLinjeHtml(s, days, rediger){
    const d0 = days[0], b = dayBest(s, d0.key), h = b.h, K = window.KJORETID;
    const dag = d0.idag ? "" : `${cap(dagOrd(d0))}: `;
    const H = STR.hjem, ord = b.cls==="forbud" ? H.forbud : b.cls==="dark" ? H.morktOrd : b.cls==="over" ? H.over : b.cls==="miss" ? H.mangler : ratingWord(h);
    const tapt = h && b.st!=null ? (lostParts(h).map(p=> p.tekst).join(" · ") || null) : null;
    const sted = s.area || regionOf(s), kj = kjoreText(s.id), setn = favSetning(s, b), obs = favObs(s);
    const aria = [`${s.name}, ${[sted, kj && K ? STR.hjem.kjoreAria(kj, K.fra.navn) : null].filter(Boolean).join(", ")}`,
      `${dag}${b.st!=null ? STR.starsAria(b.st, lostAll(h)) + ", " : ""}${ord}`, setn ? setn.replace(/\.$/, "") : null, obs, ukeAria(s, days)].filter(Boolean).join(". ");
    const inni = `<span class="t-listetall" aria-hidden="true">${b.st!=null ? b.st : ""}</span>
      <span class="favtekst"><span class="t-navn${s.name.length > 12 ? " lang" : ""}">${esc(s.name)}</span>
        <span class="etikett">${esc([sted, kj, dag + ord, tapt].filter(Boolean).join(" · "))}</span>
        ${setn ? `<span class="setn">${numHtml(setn)}</span>` : ""}
        ${obs ? `<span class="etikett obs">${esc(obs)}</span>` : ""}
        ${ukeHtml(s, days, "under")}</span>`;
    const cls = `favlinje ${b.st!=null ? `r-${min5(b.st)}` : "r-0"}`;
    if(rediger) return `<div class="${cls}" role="group" aria-label="${esc(aria)}">${inni}<button type="button" class="ghost" data-fjern="${esc(s.id)}" aria-label="${esc(STR.hjem.fjernAria(s.name))}">${esc(STR.hjem.fjern)}</button></div>`;
    return `<a class="${cls}" href="#spot=${esc(s.id)}" aria-label="${esc(`${aria}. ${H.apne}`)}">${inni}</a>`;
  }
  function favListeHtml(favs, days){
    // mobil: rader uten streker (SPEC §6A punkt 4). «Rediger» viser «Fjern» på hver rad og «Legg til spot» (søket).
    const H = STR.hjem, red = !!S.favRediger;
    return `<section class="sek"><h2 class="h2">Favoritter</h2><button type="button" class="sekknapp" id="favRediger" aria-pressed="${red}">${esc(red ? H.ferdig : H.rediger)}</button></section>
      <div class="favliste">${favs.map(s=> favLinjeHtml(s, days, red)).join("")}</div>${red ? `<p class="favleggtil"><a class="ghost" href="#sok">${esc(H.leggTil)}</a></p>` : ""}`;
  }

  /* ---------- Hjem ---------- */
  function favHtml(days){
    const favs = DATA.spots.filter(s=>isFavSpot(s.id));
    if(!favs.length){ S.favRediger = false; return ""; }
    return favListeHtml(favs, days);
  }
  function groups(){
    const by = new Map();
    for(const s of DATA.spots){ const r = regionOf(s); if(!by.has(r)) by.set(r, []); by.get(r).push(s); }
    const order = regions();
    return [...by.keys()].sort((a, b)=> (order.indexOf(a)+1 || 99) - (order.indexOf(b)+1 || 99) || a.localeCompare(b, "nb")).map(r=>({region: r, spots: by.get(r)}));
  }
  function radHtml(s, days){
    const h = naaOf(s), {st, oh} = naaVisning(s, h);
    // ordet og høyden gjelder nå-timen, ukerutene ved siden av er dagens beste (Theodor S15 b, 17.11.2026): «Nå» står foran
    const ord = oh.ord.replace(/\s+nå$/, ""), naa = ord==="–" ? "" : STR.spot.naa;   // uten time er det ikke noe ord å merke
    return `<a class="rad r-${min5(st)}" href="#spot=${esc(s.id)}" aria-label="${esc(`Åpne ${s.name}: ${naa ? naa.toLowerCase() + " " : ""}${ord.toLowerCase()}${oh.hoyde ? ", " + oh.hoyde + " m" : ""}. ${ukeAria(s, days)}`)}">
      <span class="nm"><b>${esc(s.name)}</b><small>${esc(omrMerker(s))}</small><span class="na">${naa ? `<span class="na-tid">${esc(naa)}</span> ` : ""}${esc(ord)}${oh.hoyde ? ` <span class="num">${esc(oh.hoyde)} m</span>` : ""}</span></span>
      ${ukeHtml(s, days, false)}</a>`;
  }
  function regionChips(current, onPickAttr){
    return `<div class="chips regionvelger" role="group" aria-label="Region">${regions().map(r=>`<button type="button" class="chip" data-${onPickAttr}="${esc(r)}" aria-pressed="${r===current}">${esc(r)}</button>`).join("")}</div>`;
  }
  function gruppeHtml(g, days){
    const n = g.spots.length, all = S.visAlle[g.region] || n <= 8;
    const sorted = [...g.spots].sort(byRatingNow);
    const shown = all ? sorted : sorted.slice(0, 5);
    const id = "reg-" + norm(g.region).replace(/[^a-z0-9]+/g, "-");
    return `<section class="gruppe" id="${id}"><div class="gruppe-topp"><h3>${esc(g.region)}<small>${n} ${n===1?"spot":"spots"}</small></h3><span class="uke" aria-hidden="true">${days.map(d=>`<b class="${d.idag?"idag":""}">${esc(d.kort)}</b>`).join("")}</span></div>
      <div class="rader">${shown.map(s=>radHtml(s, days)).join("")}</div>
      ${!all ? `<button type="button" class="ghost visalle" data-region="${esc(g.region)}">Vis alle ${n}</button>` : ""}</section>`;
  }
  function regionHtml(days){
    // mobil: «Spots i <region>» med regionvelger; over 8 spots: de 5 beste nå og «Vis alle N»
    const r = S.region || chosenRegion();
    const g = groups().find(x=>x.region===r) || {region: r, spots: []};
    return `<section class="sek"><h2 class="h2">Spots i ${esc(r)}</h2></section>${regionChips(r, "region")}${g.spots.length ? gruppeHtml(g, days) : `<p class="muted">Ingen spots i ${esc(r)} ennå.</p>`}`;
  }
  /* ---------- Nettsiden: forsiden «Beste i dag» (design B 4.0 steg 6, SPEC §6D) ---------- */
  // Datolinje, overskrift av to setninger (samme overskrift() som mobil, på spotene og dagen filtrene viser - så den aldri
  // sier noe annet enn tabellen), I DAG / I MORGEN og regionfaner, hovedbildet med dagens beste, «Beste i dag» som tabell
  // med tidsstripa 06-18 (dagssammendragets «timer», publish.py) og «Neste 7 dager» som matrise uten bokser.
  // Samme dagstall (dayBest) overalt. Ren visning: «–» når tallet mangler, aldri 0.
  const FS_RADER = 10;   // surfbare rader før «Vis alle»
  const fsRang = (b)=> b.st!=null ? b.st : -1;
  function fsRader(spots, key){
    // samme rekkefølge som overskriften (flest poeng, så høyest surf, så navnet)
    return spots.map(s=> ({s, b: dayBest(s, key)})).sort((x, y)=> fsRang(y.b) - fsRang(x.b) || ((y.b.h && y.b.h.surf_height)||0) - ((x.b.h && x.b.h.surf_height)||0) || x.s.name.localeCompare(y.s.name, "nb"));
  }
  function fsHelt(rader){
    // dagens beste med samme regel som overskriften: nye spots og spots med forbud bare når ingen andre er surfbare
    const med = rader.filter(r=> r.b.st!=null && r.b.st >= 1);
    return med.find(r=> iBesteOkt(r.s, r.b.t)) || med[0] || null;
  }
  const fsOrd = (b)=> b.cls==="forbud" ? STR.hjem.forbud : b.cls==="dark" ? STR.hjem.morktOrd : b.cls==="over" ? STR.hjem.over : b.cls==="miss" ? STR.hjem.mangler : ratingWord(b.h).replace(/\s+nå$/, "");
  const fsTapt = (h)=> !h ? "" : lostParts(h).map(p=> p.tekst).join(" · ");
  const fsSvell = (h)=> h && h.swell_offshore!=null ? `${nf1.format(h.swell_offshore)} m${h.period!=null ? ` · ${nf0.format(h.period)} s` : ""}` : "–";
  // «Best hh–hh» vises bare mens vinduet er åpent (fysikk-kontrolløren 15.10 og 16.11.2026) - samme test som «apent»
  // i overskrift(): et vindu som er over, er ikke et råd
  const fsApent = (b)=> !!b.slutt && new Date(b.slutt).getTime() + 36e5 > Date.now();
  function fsStripe(s, key, b){
    // 13 ruter for kl. 06-18 fra «timer» (publish.py): tallet som farge (SPEC §5), «m» mørkt, «x» mangler, «.» over.
    // Timer som har gått siden oversikten ble laget, er også over (blanke) - ellers viser stripa farger for i formiddag
    const d = (s.dager || []).find(x=> x.d===key);
    if(!d || !d.timer || b.cls==="forbud") return "";
    const naaKl = key===dayKey(new Date()) ? +fmtHour.format(new Date()) : -1;
    return `<span class="fs-stripe">${[...d.timer].map((c, i)=> `<i class="${6 + i < naaKl ? "vaert" : /[0-5]/.test(c) ? "r-" + c : c==="m" ? "mork" : c==="x" ? "miss" : "vaert"}"></i>`).join("")}</span>`;
  }
  function fsRadHtml(r, nr, key){
    const {s, b} = r, h = b.h, n = b.st!=null ? min5(b.st) : null, kj = kjoreText(s.id);
    const vindu = n!=null && n >= 1 && fsApent(b) ? vinduKl(b.start, b.slutt).join("–") : "–";
    const href = `#spot=${encodeURIComponent(s.id)}${b.t ? "&t=" + encodeURIComponent(b.t) : ""}`;
    const aria = [`${s.name}, ${[regionOf(s), kj].filter(Boolean).join(", ")}`, `${n!=null ? STR.starsAria(n, lostAll(h)) + ", " : ""}${fsOrd(b)}`, vindu!=="–" ? `${STR.spot.best} ${vindu}` : null, h && h.swell_offshore!=null ? `${STR.spot.svell} ${fsSvell(h)}` : null].filter(Boolean).join(". ");
    return `<tr class="s r-${n!=null ? n : 0}" data-spot="${esc(s.id)}" data-href="${esc(href)}">
      <td class="fs-nr">${esc(STR.web.nr(nr))}</td>
      <td class="fs-nm"><a class="t-navn${s.name.length > 12 ? " lang" : ""}" href="${esc(href)}" aria-label="${esc(aria)}">${esc(s.name)}</a><span class="etikett">${esc([regionOf(s), kj, ...merker(s)].filter(Boolean).join(" · "))}</span></td>
      <td class="fs-dom">${n!=null ? `<span class="t-listetall">${n}</span>` : ""}<span class="ord"><b>${esc(fsOrd(b))}</b>${fsTapt(h) && n!=null ? `<span class="etikett">${esc(fsTapt(h))}</span>` : ""}</span></td>
      <td class="fs-bst">${esc(vindu)}</td>
      <td class="fs-sv">${esc(n!=null ? fsSvell(h) : "–")}</td>
      <td class="fs-tim">${fsStripe(s, key, b)}</td></tr>`;
  }
  function fsHeltHtml(r, dag){
    const {s, b} = r, h = b.h, n = min5(b.st), foto = !!(window.Skive && Skive.harBilde(s.id)), id = encodeURIComponent(s.id), kj = kjoreText(s.id), K = window.KJORETID;
    const vindu = fsApent(b) ? vinduKl(b.start, b.slutt).join("–") : "";   // vinduet er over: ingen «Best», ingen ring
    const fakta = [fsSvell(h), h && h.wind_speed!=null ? windLabel(h) : null].filter(x=> x && x!=="–").join(" · ");
    const linje = [STR.web.nr(1), STR.web.bestDag(dag), regionOf(s), kj && K ? STR.hjem.kjoreAria(kj, K.fra.navn) : null].filter(Boolean).join(" · ");
    // den håndtegnede ringen rundt beste vindu (SPEC §6D punkt 3) - bare når dagen har 4 eller 5, i korall. Ellers ren tekst
    const ring = n < 4 ? "" : `<svg class="fs-ring" viewBox="0 0 200 64" preserveAspectRatio="none" aria-hidden="true"><path d="M30 12 C70 2 150 2 182 14 C204 24 196 50 150 58 C100 66 30 62 10 46 C-4 34 12 18 46 9"/></svg>`;
    return `<a class="fs-helt r-${n}${foto ? "" : " uten"}" href="#spot=${id}&t=${encodeURIComponent(b.t)}" aria-label="${esc(`${linje}. ${s.name}: ${STR.starsAria(n, lostAll(h))}, ${fsOrd(b)}. ${vindu ? `${STR.spot.best} ${vindu}. ` : ""}${STR.hjem.apne}`)}">
        ${foto ? `<img class="sp-foto trykk" src="img/spots/${id}-trykk.jpg" alt="" decoding="async"><img class="sp-foto lodd" src="img/spots/${id}-lodd.jpg" alt="" decoding="async">` : ""}
        <span class="fs-plate"><span class="etikett">${esc(linje)}</span><span class="t-hero fs-navn${lengste(s.name) > 8 ? " lang" : ""}">${esc(s.name)}</span>
          <span class="fs-rad"><span class="fs-tall">${n}</span><b class="fs-ord">${esc(fsOrd(b))}</b>${fakta ? `<span class="fs-fakta">${esc(fakta)}</span>` : ""}${vindu ? `<span class="fs-best${ring ? " medring" : ""}">${esc(STR.spot.best)} ${esc(vindu)}${ring}</span>` : ""}</span></span></a>
      ${foto ? `<p class="kredit linje">${fotoKreditHtml(false)}</p>` : ""}`;
  }
  const lengste = (navn)=> Math.max(...String(navn).split(/[\s-]+/).map(o=> o.length), 1);
  function fsMatrise(spots, days, perSpot){
    // «Neste 7 dager» (SPEC §6D punkt 5): beste tall per region og dag, eller per spot når en region er valgt.
    // Fra 4 stort i korall, 3 mellomstort i blekk, 0-2 lite og dempet; «–» når ingen av spotene har tall den dagen.
    const rader = perSpot ? spots.slice().sort((a, b)=> a.name.localeCompare(b.name, "nb")).map(s=> ({navn: s.name, spots: [s]}))
      : groups().map(g=> ({navn: g.region, spots: g.spots}));
    const celle = (r, d)=>{
      const bs = r.spots.map(s=> dayBest(s, d.key)), med = bs.filter(b=> b.st!=null);
      if(!med.length){
        const ord = bs.every(b=> b.cls==="dark") ? STR.hjem.morktOrd : bs.every(b=> b.cls==="over") ? "" : bs.every(b=> b.cls==="forbud") ? STR.hjem.forbud : "–";
        return `<td class="tom">${esc(ord)}</td>`;
      }
      const n = min5(Math.max(...med.map(b=> b.st)));
      return `<td class="r-${n}"><span class="mx${n >= 4 ? " hoy" : n===3 ? " tre" : ""}">${n}</span></td>`;
    };
    const dagTxt = (d)=>{ const at = new Date(d.key + "T11:00:00Z"); return `${fmtDayShort.format(at).replace(/\.$/, "")} ${d.dato}`; };
    return `<section class="sek"><h2 class="h2">${esc(STR.web.neste7)}</h2><p class="sub">${esc(perSpot ? STR.web.perSpot : STR.web.perRegion)}</p></section>
      <table class="fs-matrise"><thead><tr><th scope="col">${esc(perSpot ? STR.web.kol.spot : STR.web.kol.region)}</th>${days.map(d=> `<th scope="col"${d.idag ? ' class="idag"' : ""}>${esc(dagTxt(d))}</th>`).join("")}</tr></thead>
      <tbody>${rader.map(r=> `<tr><th scope="row">${esc(r.navn)}</th>${days.map(d=> celle(r, d)).join("")}</tr>`).join("")}</tbody></table>`;
  }
  function renderForside(root, days){
    const now = new Date(), key = dayKey(now), gen = new Date(DATA.generated), K = window.KJORETID;
    const valg = Math.min(S.fsDag || 0, Math.max(0, days.length - 1)), dag = days[valg];
    // regionfanen starter på regionen fra Innstillinger -> Område (som «Beste økt» før: aldri hele Norge uten at man
    // ber om det); «Alle» er et valg (S.fsRegion = "")
    const regs = regions(), fv = S.fsRegion==null ? chosenRegion() : S.fsRegion, reg = fv && regs.includes(fv) ? fv : null;
    const spots = DATA.spots.filter(s=> !reg || regionOf(s)===reg);
    const l = K ? lysIDag(K.fra.lat, K.fra.lon) : null;
    const lys = !l ? null : l.start==null ? STR.lightNone : l.hele ? STR.hjem.lysHele : STR.hjem.lys(fmtTime.format(new Date(l.start)), fmtTime.format(new Date(l.end)));
    const dato = [`${cap(fmtDay.format(now))} ${key.slice(8, 10)}.${key.slice(5, 7)}`, lys, K ? STR.hjem.fra(K.fra.navn) : null,
      `${STR.spot.oppdatert} ${dayKey(gen)===key ? "" : relDay(gen) + " "}${fmtTime.format(gen)}`, STR.web.antall(DATA.spots.length)].filter(Boolean).join(" · ");
    const dagNavn = (d)=> cap(relDay(new Date(d.key + "T11:00:00Z")));
    // «Beste i dag», «Beste i morgen» eller «Beste fredag» etter dagen som er valgt (Theodor S20 b, 20.11.2026, og S25, 22.11.2026)
    const rd = dag ? relDay(new Date(dag.key + "T11:00:00Z")) : "i dag";
    const besteTittel = STR.web.bestDag(rd);
    const rader = dag ? fsRader(spots, dag.key) : [], helt = fsHelt(rader);
    const resten = rader.filter(r=> r!==helt), surf = resten.filter(r=> r.b.st!=null && r.b.st >= 1);
    const vis = S.fsAlle ? resten : surf.length ? surf.slice(0, FS_RADER) : resten.slice(0, 5);
    const tegn = `<p class="fs-tegn etikett"><span><i class="r-4"></i>${esc(STR.web.tegn.hoy)}</span><span><i class="r-3"></i>${esc(STR.web.tegn.tre)}</span><span><i class="r-1"></i>${esc(STR.web.tegn.lav)}</span><span><i class="r-0"></i>${esc(STR.web.tegn.null)}</span><span><i class="mork"></i>${esc(STR.hjem.morktOrd)}</span><span><i class="miss"></i>${esc(STR.hjem.mangler)}</span></p>`;
    root.innerHTML = `${typeof staleBanner==="function" ? staleBanner() : ""}<div id="forside">
      <p class="etikett fs-dato">${esc(dato)}</p>
      ${dag ? overskriftHtml(spots, days.slice(valg), false) : ""}
      <div class="fs-filter">
        <div class="fs-seg" role="group" aria-label="${esc(STR.web.dag)}">${days.slice(0, 2).map((d, i)=> `<button type="button" data-fsdag="${i}" aria-pressed="${i===valg}">${esc(dagNavn(d))}</button>`).join("")}</div>
        <div class="fs-faner" role="group" aria-label="${esc(STR.web.region)}"><button type="button" data-fsreg="" aria-pressed="${!reg}">${esc(STR.web.alle)} <span>${DATA.spots.length}</span></button>${regs.map(r=> `<button type="button" data-fsreg="${esc(r)}" aria-pressed="${r===reg}">${esc(r)} <span>${DATA.spots.filter(s=> regionOf(s)===r).length}</span></button>`).join("")}</div>
      </div>
      ${helt && dag ? fsHeltHtml(helt, relDay(new Date(dag.key + "T11:00:00Z"))) : ""}
      <section class="sek"><h2 class="h2">${esc(besteTittel)}</h2><p class="sub">${esc(`${STR.web.tallFra} · ${STR.web.bareLyse}`)}</p></section>
      <table class="fs-tabell"><thead><tr><th scope="col" class="fs-nr">${esc(STR.web.kol.nr)}</th><th scope="col">${esc(STR.web.kol.spot)}</th><th scope="col">${esc(dag ? dagNavn(dag) : "")}</th><th scope="col">${esc(STR.web.kol.best)}</th><th scope="col">${esc(STR.web.kol.svell)}</th><th scope="col" class="fs-tim">${esc(STR.web.kol.timer)}</th></tr></thead>
        <tbody>${vis.map((r, i)=> fsRadHtml(r, i + (helt ? 2 : 1), dag.key)).join("")}</tbody></table>
      <div class="fs-bunn">${tegn}<div class="fs-knapper">${vis.length < resten.length ? `<button type="button" class="knapp2" id="fsAlle">${esc(STR.web.visAlle(spots.length))}</button>` : ""}<a class="knapp1" href="#utforsk">${esc(STR.web.apneKart)} <span aria-hidden="true">→</span></a></div></div>
      ${fsMatrise(spots, days, !!reg)}
    </div>`;
    $$("[data-fsdag]", root).forEach(b=> b.onclick = ()=>{ S.fsDag = +b.dataset.fsdag; S.fsAlle = false; renderHome(); });
    $$("[data-fsreg]", root).forEach(b=> b.onclick = ()=>{ S.fsRegion = b.dataset.fsreg; S.fsAlle = false; renderHome(); });
    const alle = $("#fsAlle", root); if(alle) alle.onclick = ()=>{ S.fsAlle = true; renderHome(); };
    // hele raden er trykkflate; lenka på navnet er den tastaturet og skjermleseren bruker
    $$("table.fs-tabell tr.s", root).forEach(tr=> tr.onclick = (e)=>{ if(!e.target.closest("a")) location.hash = tr.dataset.href; });
  }
  function renderHome(){
    const root = $("#viewHjem"); const days = weekDays(); const gen = new Date(DATA.generated);
    if(isDesktop()) return renderForside(root, days);
    // mobil (SPEC §6A): topplinje, overskrift av to setninger, kompakt kart (220 pt), favorittene som rader.
    // «Beste økt» er tatt bort på mobil (Theodors svar 16.11.2026, punkt 3b). Søk ligger i fanelinja, Innstillinger nederst.
    const sc = scope();
    const kilder = "Varsel fra BarentsWatch, MET Norge, Open-Meteo og Kartverket.";
    const favs = DATA.spots.filter(s=> isFavSpot(s.id));
    const kart = window.Utforsk && Utforsk.hjemKart && days.length ? Utforsk.hjemKart(favs.length ? favs : sc.spots, days[0].key, document.documentElement.clientWidth || 390) : "";
    root.innerHTML = `
      ${typeof staleBanner==="function" ? staleBanner() : ""}
      ${topplinjeHtml()}
      ${overskriftHtml(favs.length ? favs : sc.spots, days, favs.length > 0)}
      ${kart ? `<a class="hjemkart" href="#utforsk" aria-label="Utforsk kartet">${kart}</a><p class="hjemkart-kilde">${esc(STR.hjem.kartKilde)}</p>` : ""}
      ${favHtml(days)}
      ${regionHtml(days)}
      <p class="kilder">${kilder} ${esc(STR.updated(relDay(gen), fmtTime.format(gen)))}.</p>
      <p class="hjem-bunn"><a class="ghost" href="#innstillinger">${esc(STR.hjem.innstillinger)}</a></p>`;
    // ny tegning etter Rediger/Ferdig/Fjern: fokus tilbake på knappen (eller overskriften når siste favoritt er fjernet)
    const fokusRediger = ()=>{ const k = $("#favRediger", root) || $(".hjem-overskrift", root); if(k){ if(!k.matches("button")) k.tabIndex = -1; k.focus(); } };
    const red = $("#favRediger", root); if(red) red.onclick = ()=>{ S.favRediger = !S.favRediger; renderHome(); fokusRediger(); };
    $$("[data-fjern]", root).forEach(b=> b.onclick = ()=> toggleFavoriteUI(b.dataset.fjern).then(()=>{ if(S.view==="hjem"){ renderHome(); fokusRediger(); } }));
    $$(".visalle", root).forEach(b=> b.onclick = ()=>{ S.visAlle[b.dataset.region] = true; renderHome(); });
    $$("[data-region]", root).forEach(b=>{ if(b.classList.contains("chip")) b.onclick = ()=>{ setRegion(b.dataset.region); renderHome(); }; });
    // valgt regionbrikke alltid synlig (PR #12 punkt a): rull brikkeraden sidelengs, aldri siden
    $$(".regionvelger", root).forEach(row=>{ const c = row.querySelector('[aria-pressed="true"]'); if(c && row.scrollWidth > row.clientWidth){ row.scrollLeft = Math.max(0, c.offsetLeft - row.offsetLeft - (row.clientWidth - c.offsetWidth) / 2); } });
  }

  /* ---------- nettsiden: temaknappen og bunnen (B4 steg 6, SPEC §6C punkt 1 og 7) ---------- */
  // «Mørketid» velger temaet selv i stedet for systemet (html[data-theme], lagret i nettleseren). Uten lagret valg følger
  // siden systemet som før. Knappen er trykket når mørketid vises.
  const TEMA_KEY = "nordsurf.tema";
  try{ const t = localStorage.getItem(TEMA_KEY); if(t==="dark" || t==="light") document.documentElement.dataset.theme = t; }catch(e){}
  const erMork = ()=>{ const t = document.documentElement.dataset.theme; return t ? t==="dark" : matchMedia("(prefers-color-scheme: dark)").matches; };
  function temaKnapp(){
    const b = $("#temaKnapp"); if(!b) return;
    b.textContent = STR.web.morketid; b.setAttribute("aria-pressed", String(erMork()));
    if(b.dataset.koblet) return; b.dataset.koblet = "1";
    b.onclick = ()=>{ const ny = erMork() ? "light" : "dark"; document.documentElement.dataset.theme = ny; try{ localStorage.setItem(TEMA_KEY, ny); }catch(e){} temaKnapp(); };
    const mq = matchMedia("(prefers-color-scheme: dark)"); (mq.addEventListener ? mq.addEventListener("change", temaKnapp) : mq.addListener(temaKnapp));
  }
  function bunnHtml(){
    const W = STR.web, B = window.SPOTBILDER;
    // hele krediteringen for kornfotoene står her (under bildene står bare kortformen), med lisensen som lenke
    const kilder = [...W.kildeListe, W.kartOsm].map(esc).concat(B ? [fotoKreditHtml(true)] : []);
    return `<div class="bunn-inn"><div><span class="wm" aria-hidden="true">${typeof wordmarkSvg==="function" ? wordmarkSvg() : ""}</span><p>${esc(W.bunn)}</p></div>
      <div><h2 class="bunn-tittel">${esc(W.kilder)}</h2><ul>${kilder.map(k=> `<li>${k}</li>`).join("")}</ul></div>
      <div><a href="#innstillinger">${esc(STR.hjem.innstillinger)}</a></div></div>`;
  }

  /* ---------- Søk (ett sted: søkesiden på mobil, nedtrekkslista på nett) ---------- */
  const SOK_MAKS = 20;
  function search(q){
    // navn, område, region og alias (spots.json aliases); navn-prefiks først, så best vurdering nå
    const nq = norm(q.trim()); if(!nq) return [];
    const hit = (s)=> norm(s.name).includes(nq) || norm(s.area).includes(nq) || norm(regionOf(s)).includes(nq) || (s.aliases||[]).some(a=> norm(a).includes(nq));
    const pre = (s)=> norm(s.name).startsWith(nq) || (s.aliases||[]).some(a=> norm(a).startsWith(nq)) ? 0 : 1;
    return DATA.spots.filter(hit).sort((a, b)=> pre(a) - pre(b) || byRatingNow(a, b));
  }
  function sradHtml(s){
    const h = naaOf(s), {st, rute, oh} = naaVisning(s, h);
    return `<a class="srad r-${min5(st)}" href="#spot=${esc(s.id)}" role="option">${ruteHtml(st, rute)}<span class="nm"><b>${esc(s.name)}</b><small>${esc(stedText(s))}</small></span><span class="na">${esc(oh.ord)}${oh.hoyde ? `<span class="num">${esc(oh.hoyde)} m</span>` : ""}</span></a>`;
  }
  function resultsHtml(q){
    const r = search(q);
    if(!q.trim()) return forslagHtml();
    if(!r.length) return `<p class="ingen-treff" role="status">Ingen spots heter «${esc(q.trim())}». Prøv et område, som Senja eller Lofoten.</p>`;
    if(r.length <= 8) return `<div class="alfa" role="listbox">${r.map(sradHtml).join("")}</div>`;
    // mange treff: gruppert per region, maks 20 før «Vis flere»
    const shown = S.sokFlere ? r : r.slice(0, SOK_MAKS);
    const by = new Map(); for(const s of shown){ const k = regionOf(s); if(!by.has(k)) by.set(k, []); by.get(k).push(s); }
    const order = regions();
    const html = [...by.keys()].sort((a, b)=> (order.indexOf(a)+1 || 99) - (order.indexOf(b)+1 || 99)).map(k=>`<h3>${esc(k)} <small>${by.get(k).length}</small></h3><div class="alfa" role="listbox">${by.get(k).map(sradHtml).join("")}</div>`).join("");
    return `<div class="sokgrupper">${html}${shown.length < r.length ? `<button type="button" class="ghost visflere" id="sokFlere">Vis flere (${r.length - shown.length})</button>` : ""}</div>`;
  }
  function forslagHtml(){
    const favs = DATA.spots.filter(s=>isFavSpot(s.id));
    const areas = [...new Set(DATA.spots.map(s=>s.area).filter(Boolean))];
    const regs = regions();
    const alpha = [...DATA.spots].sort((a, b)=>a.name.localeCompare(b.name, "nb"));
    return `<div class="forslag">
      ${favs.length ? `<h3>Favoritter</h3><div class="chips">${favs.map(s=>`<a class="chip" href="#spot=${esc(s.id)}">${esc(s.name)}</a>`).join("")}</div>` : ""}
      <h3>Områder</h3><div class="chips">${[...regs, ...areas.filter(a=>!regs.includes(a))].map(a=>`<button type="button" class="chip" data-q="${esc(a)}">${esc(a)}</button>`).join("")}</div>
      <h3>Alle spots <small>${alpha.length}</small></h3><div class="alfa lang" role="listbox">${alpha.map(sradHtml).join("")}</div></div>`;
  }
  function wireResults(root){
    $$("[data-q]", root).forEach(b=> b.onclick = ()=>{ S.q = b.dataset.q; S.sokFlere = false; const inp = $("#sokM") || $("#sokPC"); if(inp){ inp.value = S.q; } if($("#sokM")) renderSok(); else renderDrop(); });
    const more = $("#sokFlere", root); if(more) more.onclick = ()=>{ S.sokFlere = true; if($("#sokM")) renderSok(); else renderDrop(); };
  }
  function renderSok(){
    const root = $("#viewSok");
    root.innerHTML = `<div class="soktopp"><label class="sok-field" for="sokM"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12.8 12.8 17 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><span class="sr">Søk etter spot eller område</span><input id="sokM" type="search" placeholder="Søk etter spot eller område" autocomplete="off" value="${esc(S.q)}"></label><button type="button" class="avbryt" id="sokAvbryt">Avbryt</button></div><div id="sokRes">${resultsHtml(S.q)}</div>`;
    const inp = $("#sokM", root);
    inp.oninput = ()=>{ S.q = inp.value; S.sokFlere = false; $("#sokRes", root).innerHTML = resultsHtml(S.q); wireResults(root); };
    $("#sokAvbryt", root).onclick = ()=>{ S.q = ""; go(S.from==="sok" ? "hjem" : S.from); };
    wireResults(root);
    if(!S.q) inp.focus();
  }
  function renderDrop(){
    const drop = $("#sokDrop"), inp = $("#sokPC"); if(!drop || !inp) return;
    const q = inp.value; S.q = q;
    drop.innerHTML = resultsHtml(q); drop.hidden = false; inp.setAttribute("aria-expanded", "true");
    wireResults(drop);
  }
  function closeDrop(){ const drop = $("#sokDrop"), inp = $("#sokPC"); if(drop){ drop.hidden = true; } if(inp) inp.setAttribute("aria-expanded", "false"); }
  function wireTopSearch(){
    const inp = $("#sokPC"); if(!inp) return;
    inp.addEventListener("input", ()=>{ S.sokFlere = false; renderDrop(); });
    inp.addEventListener("focus", renderDrop);
    inp.addEventListener("keydown", (e)=>{ if(e.key==="Escape"){ closeDrop(); inp.blur(); } });
    document.addEventListener("pointerdown", (e)=>{ if(!e.target.closest(".topsok")) closeDrop(); });
    window.addEventListener("hashchange", closeDrop);
  }

  /* ---------- ruter ---------- */
  function parseRoute(){
    const h = location.hash || "";
    let m;
    if((m = h.match(/^#spot=([^&]+)(?:&t=([^&]+))?/)) || (m = h.match(/^#\/spot\/([^/?#&]+)/))){
      const id = decodeURIComponent(m[1]);
      if(spotById(id)){
        if(S.view!=="spot") S.from = S.view==="sok" ? (S.from||"hjem") : S.view;   // lenke eller fram/tilbake i nettleseren: tilbakeknappen følger stakken da også
        S.spotId = id; S.view = "spot"; S.idx = null; S.tIso = null; S.tideMin = 0;
        const t = m[2]!=null ? decodeURIComponent(m[2]) : null;
        if(t!=null){ if(/^\d+$/.test(t)) S.idx = +t; else S.tIso = t; }   // tidsstempel (fra oversikten) eller timeindeks (gamle lenker)
        return;
      }
    }
    if(/^#(utforsk|\/utforsk)/.test(h)) S.view = "utforsk";
    else if(/^#(logger|\/logger)/.test(h)) S.view = "logger";
    else if(/^#(innstillinger|\/innstillinger)/.test(h)) S.view = "innstillinger";
    else if(/^#sok/.test(h)) S.view = "sok";
    else S.view = "hjem";
    if(S.view!=="spot") S.spotId = null;
  }
  function routeFor(view){ return view==="spot" ? `#spot=${encodeURIComponent(S.spotId)}` : `#${view}`; }
  function go(view, replace){
    const hash = routeFor(view);
    if(location.hash !== hash){ if(replace) history.replaceState(history.state, "", hash); else location.hash = hash; }
    else render();
  }
  /* Tilbake og rulling (designrevisjonen 21.11.2026, fase 1 punkt 8). Hver oppføring i nettleserens historikk som appen
     har laget, får et løpenummer i history.state ({ns}). Appen husker hvilken rute hvert nummer hadde (i minnet), og hvor
     langt ned hver visning var rullet. Da kan tilbakeknappen på spotsiden gå ett steg tilbake i stedet for å legge et nytt
     steg oppå, og siden man kommer tilbake til, står der man forlot den. */
  const hist = {idx: 0, ruter: {}, rull: {}, tilbake: false, venter: null};
  const normRute = (h)=> !h || h==="#" || h==="#/" ? "#hjem" : h;
  const rullKey = ()=> S.view==="spot" ? `spot=${S.spotId}` : S.view;
  function histMerk(){
    // kalles ved oppstart og ved hver hashchange: ny oppføring får neste nummer, en gammel (fram/tilbake) har sitt eget
    const st = history.state, forrige = hist.idx;
    if(st && typeof st.ns==="number") hist.idx = st.ns;
    else { hist.idx = forrige + 1; try{ history.replaceState({...(st || {}), ns: hist.idx}, ""); }catch(e){} }
    hist.ruter[hist.idx] = normRute(location.hash);
    return hist.idx < forrige;   // sant når brukeren gikk bakover i historikken
  }
  function closeSpot(){
    const view = S.from && S.from!=="spot" ? S.from : "hjem", hash = routeFor(view);
    // forrige oppføring er appens egen og er siden knappen lover: gå ett steg tilbake (ikke et nytt steg oppå)
    if(hist.idx > 0 && hist.ruter[hist.idx - 1]===hash){
      // history.back() er asynkron: et nytt trykk før hashendringen er kommet ville gått ett steg til, ut av appen
      // (feiljegeren 24.11.2026). Nye trykk ses bort fra til hashendringen kommer, eller til en kort reservefrist er ute
      if(hist.venter) return;
      hist.venter = setTimeout(()=>{ hist.venter = null; }, 1000);
      history.back(); return;
    }
    // ellers (lenke rett til spoten, eller siden er lastet på nytt): bytt ut oppføringen, så «tilbake» i nettleseren
    // ikke går til spoten igjen
    history.replaceState(history.state, "", hash);
    hist.ruter[hist.idx] = normRute(hash);
    parseRoute(); render();
  }
  function openSpot(id, t, opts){
    // t: tidsstempel («2026-10-17T08:00Z») fra oversikten, eller timeindeks (spotsiden selv)
    const s = spotById(id); if(!s) return;
    if(S.view!=="spot") S.from = S.view==="sok" ? (S.from||"hjem") : S.view;
    S.spotId = id; S.tideMin = 0; S.idx = typeof t==="number" ? t : null; S.tIso = typeof t==="string" ? t : null;
    S.view = "spot";
    const hash = `#spot=${encodeURIComponent(id)}${t!=null ? "&t=" + encodeURIComponent(t) : ""}`;
    if(location.hash !== hash) location.hash = hash; else render();
  }
  function show(view){
    const map = {hjem:"viewHjem", sok:"viewSok", utforsk:"viewUtforsk", logger:"viewSide", innstillinger:"viewSide", spot:"viewSpot"};
    $$("#main .view").forEach(v=>{ v.hidden = v.id !== map[view]; });
    const navView = view==="spot" ? S.from : view==="innstillinger" || view==="sok" ? "hjem" : view;
    $$("[data-nav]").forEach(a=>{ if(a.dataset.nav===navView) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    document.body.dataset.view = view;
    // ved «tilbake» ruller render() til der visningen sto sist. Ellers til toppen
    if(!hist.tilbake) window.scrollTo(0, 0);
  }
  function renderSide(){
    const bar = $("#pageBar");
    if(S.view==="logger"){
      bar.innerHTML = "";
      renderLogs();
      if(!loadLogs().length){
        $("#detailPane").insertAdjacentHTML("afterbegin", `<header class="top"><h1>Logger</h1></header><div class="kort tom"><h3>Ingen økter logget ennå</h3><p>Når du logger hvordan det faktisk var, lærer varselet spotene dine bedre.</p><button type="button" class="primary" id="loggForste">Logg en økt</button></div>`);
        const first = $("#detailPane header.top + .kort.tom + header.top"); if(first) first.remove();
        $("#loggForste").onclick = ()=> openSheet();
      }
    } else {
      bar.innerHTML = `<button type="button" class="back" id="sideBack"><svg viewBox="0 0 18 18" aria-hidden="true"><path d="M11 3 5 9l6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>Hjem</button>`;
      $("#sideBack").onclick = ()=> go("hjem");
      renderSettings();
    }
  }
  function renderSpotView(){
    const root = $("#viewSpot"), s = spotById(S.spotId);
    if(!s){ go("hjem", true); return; }
    if(!spotIsFull(s)){
      root.innerHTML = `<div class="spot-topp"><button type="button" class="back" id="spotBack" aria-label="Tilbake"><svg viewBox="0 0 18 18" aria-hidden="true"><path d="M11 3 5 9l6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button><div class="tittel"><h1>${esc(s.name)}</h1><div class="omr">${esc(stedText(s))}</div></div></div>
        <p class="muted" role="status" id="spotLaster">${s._loadErr ? `Fikk ikke hentet detaljene for ${esc(s.name)}. Sjekk at du er på nett, og prøv igjen.` : "Henter detaljene …"}</p>${s._loadErr ? `<button type="button" class="ghost" id="spotRetry">Prøv igjen</button>` : ""}`;
      $("#spotBack").onclick = closeSpot;
      const rb = $("#spotRetry"); if(rb) rb.onclick = ()=>{ s._loadErr = false; renderSpotView(); };
      if(!s._loadErr) ensureSpot(s.id).then(()=>{ if(S.view==="spot" && S.spotId===s.id) renderSpotView(); }).catch((e)=>{ console.error(e); s._loadErr = true; if(S.view==="spot" && S.spotId===s.id) renderSpotView(); });
      return;
    }
    if(S.tIso){ const i = s.hours.findIndex(h=>h.t===S.tIso); S.idx = i >= 0 ? i : null; S.tIso = null; }
    Spot.render(root, forbudKopi(s), S, {regionOf, stedText, forbudInfo, forbudLinje, close: closeSpot, nowIdx, usable, mork, known, stars, dkOf, heightText, isDesktop, dayBest, favSetning, kjoreText, vinduKl, merker, fsApent});
  }
  function render(behold){
    if(!DATA) return;
    show(S.view);
    document.title = S.view==="spot" && spotById(S.spotId) ? `${spotById(S.spotId).name} – Nordsurf` : "Nordsurf";
    if(S.view==="hjem") renderHome();
    else if(S.view==="sok") renderSok();
    else if(S.view==="utforsk") Utforsk.render(S, behold);
    else if(S.view==="logger" || S.view==="innstillinger") renderSide();
    else if(S.view==="spot") renderSpotView();
    if(hist.tilbake){ hist.tilbake = false; window.scrollTo(0, hist.rull[rullKey()] || 0); }
  }
  // felt brukeren skriver i: bare disse får teksten satt tilbake (glidebryteren i timestripa og tallfelt styrer siden selv)
  const SKRIVEFELT = new Set(["text", "email", "search", "url", "tel", "password", "textarea"]);
  const dagrekke = (dv)=> dv ? [".dagknapp[data-day]", '.dagknapp[aria-pressed="true"]'].map(q=> ($(q, dv) || {dataset: {}}).dataset.day).join("|") : "";
  function redraw(behold){
    // tegn det som står framme på nytt uten å flytte brukeren (ny time, ny bredde, økt logget): render() går til toppen
    // som ved navigasjon, så rullingen settes tilbake, og en åpen «Hvorfor» på spotsiden står åpen.
    // behold = kartet på Utforsk står der brukeren la det (ny time, innlogging, synk ferdig), se utforsk.js
    const main = $("#main"), y = window.scrollY, hv = S.view==="spot" ? $("#viewSpot #hvorfor") : null, apen = !!(hv && hv.open);
    // tekst som ikke er lagret, fokus og dagrekka på spotsiden står også (feiljegeren 19.11.2026). Teksten settes bare tilbake
    // når feltet ellers ville fått samme verdi som før: etter lagring, inn- og utlogging vinner den nye verdien
    const felt = $$("input[id], textarea[id]", main).filter(f=> SKRIVEFELT.has(f.type) && f.value!==f.defaultValue).map(f=>({id: f.id, v: f.value, d: f.defaultValue}));
    const ae = document.activeElement, inne = ae && ae!==main && main.contains(ae);
    const fokus = !inne ? null : ae.id ? "#" + CSS.escape(ae.id) : ae.matches(".dagknapp[data-day]") ? `.dagknapp[data-day="${ae.dataset.day}"]` : null;
    let merket = null; if(fokus && SKRIVEFELT.has(ae.type)){ try{ merket = [ae.selectionStart, ae.selectionEnd]; }catch(e){} }
    const dv = S.view==="spot" ? $("#viewSpot .dagvelger") : null, x = dv ? dv.scrollLeft : 0, rekke = dagrekke(dv);
    render(behold);
    if(apen){ const hv2 = $("#viewSpot #hvorfor"); if(hv2) hv2.open = true; }
    felt.forEach(g=>{ const f = main.querySelector("#" + CSS.escape(g.id)); if(f && SKRIVEFELT.has(f.type) && f.defaultValue===g.d) f.value = g.v; });
    // ved midnatt faller første dag bort: da ruller spotsiden til valgt dag som ved vanlig tegning
    const dv2 = dv && $("#viewSpot .dagvelger"); if(dv2 && dagrekke(dv2)===rekke) dv2.scrollLeft = x;
    // fokus settes ikke tilbake hvis noe utenfor siden har tatt det i mellomtiden (et ark, søket i topplinja)
    const na = document.activeElement, f2 = fokus && (na===document.body || main.contains(na)) ? main.querySelector(fokus) : null;
    if(f2 && f2!==na && !f2.closest("[hidden]")){ f2.focus({preventScroll: true}); if(merket && merket[0]!=null){ try{ f2.setSelectionRange(merket[0], merket[1]); }catch(e){} } }
    window.scrollTo(0, y);
  }
  // nøkkelen for «ny time» er klokketimen, ikke nå-timen til første spot: mangler den spoten «nå» (hentingen feilet i regionen),
  // ble siden ellers aldri tegnet på nytt (fysikk-kontrolløren 19.11.2026)
  const klokketime = ()=> Math.floor(Date.now() / 36e5);
  function tickNow(){
    // ny time mens appen står åpen / kommer tilbake fra bakgrunnen: nå-timen flytter seg
    if(document.hidden || !DATA) return;
    const n = klokketime(); if(n===S.now) return; S.now = n;
    // Søk og Innstillinger viser ingenting som følger klokka, og tegnes de på nytt, mister brukeren teksten de holder på
    // å skrive (feiljegeren 19.11.2026)
    if(S.view==="sok" || S.view==="innstillinger") return;
    redraw(true);
  }

  /* ---------- oppstart (kalles fra app.js start()) ---------- */
  async function start(data){
    S.now = klokketime();
    S.region = chosenRegion();
    $("#loading").hidden = true;
    wireTopSearch(); temaKnapp();
    const bunn = $("#bunn"); if(bunn) bunn.innerHTML = bunnHtml();
    const retry = $("#feilRetry"); if(retry) retry.onclick = ()=> location.reload();
    // rullingen styres her (se «Tilbake og rulling» over), ikke av nettleseren: innholdet tegnes på nytt ved hver rute
    try{ history.scrollRestoration = "manual"; }catch(e){}
    const st0 = history.state;
    if(st0 && typeof st0.ns==="number") hist.idx = st0.ns; else { try{ history.replaceState({...(st0 || {}), ns: 0}, ""); }catch(e){} }
    hist.ruter[hist.idx] = normRute(location.hash);
    // husk hvor langt ned hver visning er rullet (nøkkelen er visningen som står framme når rullingen skjer)
    window.addEventListener("scroll", ()=>{ if(DATA && started) hist.rull[rullKey()] = window.scrollY; }, {passive: true});
    window.addEventListener("hashchange", ()=>{ if(hist.venter){ clearTimeout(hist.venter); hist.venter = null; } hist.tilbake = histMerk(); parseRoute(); render(); hist.tilbake = false; });
    // spotsiden velger mobil- eller PC-oppsett når den tegnes (spot.js render): tegn på nytt når bredden krysser 1024 px
    // (et nettbrett som snus), ellers står mobiloppsettet under PC-stilene (feiljegeren 19.11.2026)
    // Hjem tegnes bare når bredden endrer seg: på mobil endrer høyden seg hver gang adresselinja glir inn og ut.
    // Utforsk flytter kartet selv ved ny størrelse (utforsk.js) og tegnes bare på nytt når oppsettet byttes
    let bred = isDesktop(), bredde = window.innerWidth;
    window.addEventListener("resize", ()=>{
      const b = isDesktop(), byttet = b!==bred, w = window.innerWidth, nyBredde = w!==bredde; bred = b; bredde = w;
      if((nyBredde && S.view==="hjem") || (byttet && (S.view==="spot" || S.view==="utforsk"))) redraw();
    });
    document.addEventListener("visibilitychange", tickNow);
    setInterval(tickNow, 60e3);
    parseRoute();
    render();
    started = true;
  }
  function refresh(){ if(DATA && started && S.view!=="sok") redraw(true); }
  function goLegacy(mode){ const map = {home:"hjem", list:"hjem", peek:"hjem", half:"hjem", map:"utforsk", logger:"logger", innstillinger:"innstillinger"}; go(map[mode] || "hjem"); }
  window.Front = { start, refresh, openSpot, go: goLegacy, state: S, closeSpot, helpers: {lysIDag, kjoreText, vinduKl, regionOf, stedText, forbudNa, forbudInfo, forbudLinje, naaVisning, iBesteOkt, nowIdx, usable, mork, known, stars, lightOf, dayBest, overskrift, heightText, ordOgHoyde, windText, weekDays, search, norm, byRatingNow, dkOf, isDesktop, naaOf, regions, chosenRegion, setRegion, scope} };
  window.start();
})();
