/* Nordsurf: forsiden («kart først» 09.10.2026, «oversikt» 13.10.2026).

   Theodors hovedregel (13.10.2026): appen skal svare på «hvor og når bør jeg
   surfe?» på to sekunder - kartet støtter svaret, det er ikke svaret.
   Arket (mobil) og panelet (PC) har svarlinja øverst («Neste gode økt: …»
   eller «Ingen surf de neste 3 dagene i …»), så favorittene og lista med
   ukeoversikt (7 dager, farget etter dagens beste rating i lyse timer).
   Mobil: arket starter i halv høyde - dras ned for mer kart, opp for mer
   liste. Tiden er en liten pille i topplinja («Nå» / «Tor 17:00»); trykk
   åpner glidebryter og play, og står tiden ikke på nå, vises «Tilbake til nå».
   Logg, Logger og Innstillinger er knapper i toppen. Alt fra designrunde 1
   som fortsatt brukes (forklaringsarkene, Detaljer-rutenettet, loggarket,
   breakdown, advarslene) kommer fra app.js/explain.js.

   Ren visning: ingen rating regnes her - bare forecast.json sine felter. */
(function(){
  const $ = (s, r)=> (r||document).querySelector(s);
  const S = { idx:0, mode:"home", sheet:"half", spotId:null, view:"nord", playing:false, timeOpen:false,
              maxIdx:0, now:-1, w0:0, w1:0, w3:0, days:[], fullTop:110, back:null };
  let timer = null, coastReady = false, justDragged = false;

  const COL = (st)=> (window.Kart ? Kart.COL : {})[Math.min(5, st||0)] || "#617480";
  const T = (i)=> DATA.spots[0].hours[i] ? new Date(DATA.spots[0].hours[i].t) : null;
  const hourAt = (spot, i)=> spot.hours[i] || null;
  const stars = (h)=> h ? (h.stars||0) : 0;
  const lightOf = (h)=> window.Kart ? Kart.lightOf(h) : (h && h.light) || null;   // null = ukjent, aldri "dag"
  const lightWord = (l)=> l==="mørkt" ? "Mørkt" : l==="skumring" ? "Skumring" : l==="dag" ? "Dagslys" : "–";
  // Brukbart lys = dag eller skumring (samme som henterens `daylight`, fetch.py) - ukjent lys teller ikke.
  const usable = (h)=>{ const l = lightOf(h); return l==="dag" || l==="skumring"; };
  // Tallet finnes (ikke «–»): samme regel som ratingWord() i app.js. Mangler er aldri 0.
  const known = (h)=> !!h && !(!h.stars && !h.low_reason && h.surf_height==null);
  const tileHeight = (h)=>{
    // Flisa: "1,3–1,7 m" (kort form, får alltid plass). Ordet («Flatt»,
    // «Treffer ikke» ...) når surfehøyden er 0 eller low_reason mangler tall -
    // "–" betyr at tallet MANGLER (Theodors punkt 6). 0 stjerner med reell
    // høyde viser tallet (ratinglinja sier da ordet).
    if(!h) return "–";
    if(h.low_reason){ const m = heightMForDisplay(h); return m!=null ? `${nf1.format(m)} m` : ratingWord(h); }
    if(h.surf_height==null) return "–";
    if(h.surf_height<=0) return STR.starWords[0];   // 0 → «Flatt» (ratingWord gir «Smått» fra 0,3 m og årsaksordet fra 0,8 m, men da står tallet her)
    const a = nf1.format(h.surf_height), b = h.surf_height_sets!=null ? nf1.format(h.surf_height_sets) : null;
    return b!=null && b!==a ? `${a}–${b} m` : `${a} m`;
  };
  const markLabel = (h)=> stars(h) >= 1 && h.surf_height!=null ? `${nf1.format(h.surf_height)} m` : ratingWord(h);
  const markAria = (s, h)=> `${s.name}, ${!known(h) ? "tallet mangler" : stars(h) ? STR.starsAria(h.stars, h.faded) + ", " + markLabel(h) : ratingWord(h)}`;
  const timeText = (i)=>{ const t = T(i); return t ? `${cap(relDay(t))} ${fmtHour.format(t)}:00` : ""; };
  const pillText = (i)=>{ const t = T(i); return t ? `${cap(relDayShort(t))} ${fmtHour.format(t)}:00` : ""; };
  const starsRow = (st, big)=> starsSVG(st, 0, big);
  const fmtWd = new Intl.DateTimeFormat("nb-NO", {weekday:"short", timeZone:TZ});
  // Tall i Geist Mono, ord i Geist (Theodor 13.10.2026): bare sifrene pakkes inn
  const numHtml = (t)=> esc(t).replace(/\d[\d,.–]*/g, m=>`<span class="num">${m}</span>`);
  const segName = (view)=>{ const b = document.querySelector(`.seg button[data-view="${view}"]`); return b ? b.textContent.trim() : view; };
  const nowIdx = ()=> Math.max(0, Math.min(S.maxIdx, currentHour(DATA.spots[0])));
  const DK = new Map();
  const dkOf = (t)=>{ let k = DK.get(t); if(k===undefined){ k = dayKey(new Date(t)); DK.set(t, k); } return k; };
  const isDesktop = ()=> matchMedia("(min-width: 900px)").matches;

  /* ---------- tidsvinduer: alltid fra NÅTIMEN, ikke henterens kjøretid ---------- */
  function refreshWindows(){
    const n = nowIdx(); if(n===S.now) return false;
    S.now = n; S.w0 = n;
    const H = DATA.spots[0].hours, t0 = new Date(H[n].t).getTime();
    const firstAt = (ms)=>{ for(let i=n+1;i<H.length;i++) if(new Date(H[i].t).getTime() >= ms) return i; return H.length; };
    S.w1 = firstAt(t0 + 48*36e5);   // 48 timer: søylene i spotarket
    S.w3 = firstAt(t0 + 72*36e5);   // «de neste 3 dagene»: svarlinja og sorteringen av lista
    // ukeoversikten: 7 kalenderdager fra i dag, norsk tid (kl. 11 UTC er samme dato i Oslo hele året)
    const [y, m, d] = dayKey(new Date()).split("-").map(Number);
    S.days = Array.from({length:7}, (_, k)=>{
      const at = new Date(Date.UTC(y, m-1, d+k, 11));
      return {key: dayKey(at), letter: fmtDayShort.format(at).charAt(0).toUpperCase(), name: fmtDay.format(at)};
    });
    return true;
  }

  /* ---------- oppstart ---------- */
  async function start(data){
    // tidsakse: glidebryteren dekker de første 7 døgnene
    const H = data.spots[0].hours; const t0 = new Date(H[0].t).getTime();
    S.maxIdx = 0;
    H.forEach((h,i)=>{ const dt = new Date(h.t).getTime() - t0; if(dt <= 7*24*3600e3) S.maxIdx = i; });
    S.now = -1; refreshWindows();
    S.idx = S.w0;
    let coast = window.__COAST__;
    if(!coast){ try{ coast = await (await fetch("geo/coast.json",{cache:"force-cache"})).json(); }catch(e){ coast = null; } }
    if(coast){
      Kart.init($("#kart"), data, coast, { onPick: (id)=>openSpot(id), hourOf: hourAt, labelOf: markLabel, ariaOf: markAria,
        isFav: (id)=>isFavSpot(id), noteOf: mapNote,
        onCluster: ()=>{ S.view = "alle"; S.spotId = null; S.mode = "home"; renderAll(); } });
      coastReady = true;
    }
    $("#loading").hidden = true;
    // eldre nettlesere uten overflow:clip: scenen og arket skal aldri scrolles (bare lista inni arket)
    for(const el of [$("#stage"), $("#ark")]) el.addEventListener("scroll", ()=>{ if(el.scrollTop || el.scrollLeft){ el.scrollTop = 0; el.scrollLeft = 0; } });
    wireTop(); wireSheet(); wireTime();
    parseRoute();
    renderAll();
    window.addEventListener("hashchange", ()=>{ parseRoute(); renderAll(); });
    window.addEventListener("resize", ()=>{ layout(false); if(S.timeOpen) positionPanel(); });
    // nåtimen flytter seg mens appen står åpen eller ligger i bakgrunnen
    document.addEventListener("visibilitychange", tickNow);
    setInterval(tickNow, 60e3);
    document.addEventListener("keydown", (e)=>{
      if(e.key!=="Escape") return;
      if(S.timeOpen){ setTimeOpen(false); return; }
      if(S.mode==="spot") closeSpot();
    });
  }

  function tickNow(){
    // Ny time (eller appen kommer tilbake fra bakgrunnen): svarlinja, uka, sorteringen
    // og «Nå» regnes fra den nye nåtimen. Sto tiden på nå, følger den med; har brukeren
    // flyttet tiden, blir den stående. Lista beholder scrollen, og Logger/Innstillinger
    // tegnes ikke på nytt (et skjema der skal ikke miste det som er skrevet).
    if(document.hidden || !DATA || $("#ark").classList.contains("dragging")) return;
    const was = S.now;
    if(nowIdx() === was) return;
    const follow = S.idx === was && !S.playing;
    if(S.mode !== "home"){
      refreshWindows(); if(follow) setIdx(S.now); else renderTime();
      $("#banners").innerHTML = `${sampleBanner()}${staleBanner()}`;   // «gammelt varsel» følger klokka i alle moduser
      return;
    }
    if(follow) S.idx = nowIdx();
    const sc = $("#ark .ark-scroll"), top = sc.scrollTop;
    renderAll();
    sc.scrollTop = top;
  }

  /* ---------- ruter ---------- */
  function setRoute(){
    let hash = "#/";
    if(S.mode==="spot" && S.spotId) hash = `#/spot/${S.spotId}`;
    else if(S.mode==="logger" || S.mode==="innstillinger") hash = `#/${S.mode}`;
    else if(S.mode==="home" && S.sheet==="full" && !isDesktop()) hash = "#/liste";
    if(location.hash !== hash) history.replaceState(null, "", hash);
  }
  function parseRoute(){
    const m = location.hash.match(/^#\/(spot\/([^/?#]+)|liste|logger|innstillinger)?/);
    if(!m || !m[1]){ if(S.mode!=="home") S.mode = "home"; return; }
    if(m[2]){ const id = decodeURIComponent(m[2]); if(DATA.spots.some(s=>s.id===id)){ S.spotId = id; S.mode = "spot"; } }
    else if(m[1]==="liste"){ S.mode = "home"; S.sheet = "full"; }
    else S.mode = m[1];
  }

  /* ---------- arkets høyde (mobil) og kartets synlige område ---------- */
  function mapPeek(){
    // kartmodus: bare håndtaket, «Tilbake til nå» og svarlinja stikker opp
    const ans = $("#answer");
    return ans.hidden ? 140 : ans.offsetTop + ans.offsetHeight + 12;
  }
  function sheetTops(){
    const H = window.innerHeight, full = S.fullTop;
    const half = Math.max(full, Math.round(H * 0.5));   // Theodor 13.10.2026: arket starter i halv høyde
    return { full, half, map: Math.max(half, H - mapPeek()), spot: Math.max(full, H - Math.min(620, Math.round(H*0.72))) };
  }
  function sheetTop(){
    const t = sheetTops();
    if(S.mode==="spot") return t.spot;
    if(S.mode!=="home") return t.full;
    return t[S.sheet] ?? t.half;
  }
  function layout(animate){
    if(!coastReady) return;
    const W = window.innerWidth, H = window.innerHeight;
    const ark = $("#ark");
    if(isDesktop()){
      ark.style.removeProperty("--sheet-y");
      Kart.setArea({x:0, y:0, w: W - 420 - 32, h: H}, animate);
      return;
    }
    const ctrl = $(".top-bar .ctrl").getBoundingClientRect();
    S.fullTop = Math.round(ctrl.bottom) + 10;
    ark.style.setProperty("--sheet-top", S.fullTop + "px");
    const top = sheetTop();
    ark.style.setProperty("--sheet-y", (top - S.fullTop) + "px");
    const mapTop = Math.round(ctrl.bottom) + 8;   // under topplinja (merke, knapper, område, tid)
    Kart.setArea({x:0, y: mapTop, w: W, h: Math.max(120, top - mapTop)}, animate);
  }
  const kartMode = ()=> isDesktop() ? "peek" : (S.mode==="home" && S.sheet!=="full") ? "peek" : "list";   // «list»: kartet ligger bak arket

  /* ---------- hendelser ---------- */
  function wireTop(){
    document.querySelectorAll(".seg button[data-view]").forEach(b=>b.onclick = ()=>{
      S.view = b.dataset.view; S.spotId = null; S.mode = "home";
      // mobil: et nytt område skal synes - lista i full høyde senkes til halv (kartmodus står)
      if(!isDesktop() && S.sheet==="full") S.sheet = "half";
      if(coastReady) Kart.setView(S.view, true);
      renderAll();
    });
    $("#btnLogg").onclick = ()=> openSheet(S.spotId || DATA.spots[0].id, T(S.idx) || new Date());
    $("#btnLogger").onclick = ()=>{ S.mode = "logger"; renderAll(); };
    $("#btnSettings").onclick = ()=>{ S.mode = "innstillinger"; renderAll(); };
  }
  function wireTime(){
    $("#play").onclick = ()=> setPlaying(!S.playing);
    $("#tid").oninput = (e)=>{ setIdx(+e.target.value); };
    $("#timePill").onclick = ()=> setTimeOpen(!S.timeOpen);
    document.querySelectorAll(".backnow").forEach(b=> b.onclick = ()=>{ if(!justDragged) backToNow(); });
    // trykk utenfor panelet lukker det (avspillingen fortsetter)
    document.addEventListener("pointerdown", (e)=>{ if(S.timeOpen && !e.target.closest("#timePanel, #timePill")) setTimeOpen(false); }, true);
  }
  function setTimeOpen(on){
    S.timeOpen = on;
    $("#timePanel").hidden = !on;
    $("#timePill").setAttribute("aria-expanded", String(on));
    renderTime();
    if(on) positionPanel();
  }
  function positionPanel(){
    // PC: panelet henger under pillen (aldri inn under sidepanelet); mobil: full bredde (CSS)
    const p = $("#timePanel");
    if(!isDesktop()){ p.style.removeProperty("--tp-left"); return; }
    const bar = $(".top-bar").getBoundingClientRect(), pill = $("#timePill").getBoundingClientRect();
    const maxLeft = window.innerWidth - (420 + 16) - 16 - 420 - bar.left;
    p.style.setProperty("--tp-left", Math.max(0, Math.min(pill.left - bar.left, maxLeft)) + "px");
  }
  function setPlaying(on){
    if(timer){ clearInterval(timer); timer = null; }
    S.playing = on;
    if(on) timer = setInterval(()=>{ setIdx(S.idx >= S.maxIdx ? nowIdx() : S.idx + 1); }, 240);  // starter på nytt fra nåtimen
    renderTime();
  }
  function setIdx(i){
    S.idx = Math.max(0, Math.min(S.maxIdx, i));
    if(coastReady) Kart.setHour(S.idx);
    renderTime();
    // under avspilling oppdateres bare det som endrer seg: merker (i Kart), tid, og ratingen nå
    if(S.mode==="spot") renderSpot(true);
    else if(S.mode==="home") renderListLite();
  }
  function backToNow(){ setPlaying(false); setIdx(nowIdx()); }
  function openSpot(id, idx){
    const s = DATA.spots.find(x=>x.id===id); if(!s) return;
    S.spotId = id; S.mode = "spot";
    // fra svarlinja: spoten åpnes på svarets time, og kartet viser samme time
    if(idx!=null) S.idx = Math.max(0, Math.min(S.maxIdx, idx));
    if(S.timeOpen) setTimeOpen(false);
    renderAll();
  }
  function closeSpot(){ S.spotId = null; S.mode = "home"; renderAll(); }

  /* ---------- arket dras med fingeren (mobil): kart / halv / liste ---------- */
  function wireSheet(){
    const ark = $("#ark");
    const ZONES = ".ark-handle, #banners, #backNowM, #answer, #spot .spot-head";
    let startY = 0, baseTop = 0, curTop = 0, moved = false, active = false;
    ark.addEventListener("pointerdown", (e)=>{
      if(isDesktop() || !e.target.closest(ZONES)) return;
      if(e.pointerType==="mouse" && e.button!==0) return;
      startY = e.clientY; baseTop = sheetTop(); curTop = baseTop; moved = false; active = true;
    });
    window.addEventListener("pointermove", (e)=>{
      if(!active) return;
      const dy = e.clientY - startY;
      if(!moved && Math.abs(dy) < 6) return;
      if(!moved){ moved = true; ark.classList.add("dragging"); }
      curTop = Math.max(S.fullTop, Math.min(window.innerHeight - 80, baseTop + dy));
      ark.style.setProperty("--sheet-y", (curTop - S.fullTop) + "px");
    });
    const end = ()=>{
      if(!active) return;
      active = false;
      if(!moved) return;
      ark.classList.remove("dragging");
      // et drag skal ikke også bli et trykk på det det startet på
      justDragged = true; setTimeout(()=>{ justDragged = false; }, 60);
      const t = sheetTops();
      const cands = [["full", t.full], ["half", t.half], ["map", t.map]];
      if(S.mode==="spot") cands.push(["spot", t.spot]);
      cands.sort((a, b)=> Math.abs(a[1]-curTop) - Math.abs(b[1]-curTop));
      const next = cands[0][0];
      if(next==="spot"){ layout(true); return; }
      S.spotId = null; S.mode = "home"; S.sheet = next;
      renderAll();
    };
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
    ark.addEventListener("click", (e)=>{ if(justDragged){ e.stopPropagation(); e.preventDefault(); } }, true);
    ark.querySelector(".ark-handle").addEventListener("click", ()=>{
      if(isDesktop()) return;
      if(S.mode!=="home"){ S.spotId = null; S.mode = "home"; S.sheet = "half"; }
      else S.sheet = S.sheet==="half" ? "full" : "half";
      renderAll();
    });
  }

  /* ---------- rendering ---------- */
  function renderAll(){
    refreshWindows();
    setRoute();
    const home = S.mode==="home", side = S.mode==="logger" || S.mode==="innstillinger";
    document.querySelectorAll(".seg button[data-view]").forEach(b=>b.setAttribute("aria-pressed", String(S.view===b.dataset.view && S.mode!=="spot")));
    $("#stage").dataset.mode = S.mode;
    for(const p of document.querySelectorAll(".page")) p.classList.toggle("on", p.dataset.page === (side ? "side" : S.mode));
    const ark = $("#ark");
    ark.classList.toggle("side", side);
    ark.dataset.mode = S.mode; ark.dataset.sheet = home ? S.sheet : "";
    ark.querySelector(".ark-handle").setAttribute("aria-label", home && S.sheet==="full" ? "Vis mer av kartet" : "Vis mer av lista");
    $("#banners").innerHTML = `${sampleBanner()}${staleBanner()}`;
    $("#answer").hidden = !home;
    if(home){ renderAnswer(); renderList(); }
    else if(S.mode==="spot") renderSpot(false);
    else if(S.mode==="logger"){ renderPageBar("Logger"); renderLogs(); }
    else if(S.mode==="innstillinger"){ renderPageBar("Innstillinger"); renderSettings(); }
    if(coastReady){
      if(S.mode==="spot" && S.spotId) Kart.setSpot(S.spotId, "spot", true);
      else { Kart.setSpot(null, kartMode(), true); Kart.setView(S.view, true); }
      Kart.setHour(S.idx);
    }
    renderTime();
    layout(true);
    if(S.mode!=="spot") $("#ark .ark-scroll").scrollTop = 0;
  }
  function renderPageBar(title){
    $("#pageBar").innerHTML = `<button type="button" class="back" id="pageBack"><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M8.5 3 4.5 7l4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>Kartet</button>`;
    $("#pageBack").onclick = ()=>{ S.mode = "home"; renderAll(); };
  }
  function renderTime(){
    const f = coastReady ? Kart.focusSpot() : null;
    const h = f ? hourAt(f.s, S.idx) : hourAt(DATA.spots[0], S.idx);
    const atNow = S.idx === nowIdx();
    $("#timePillT").textContent = atNow ? "Nå" : pillText(S.idx);
    const pill = $("#timePill");
    pill.classList.toggle("away", !atNow);
    pill.setAttribute("aria-label", `Tidspunkt: ${atNow ? "nå" : timeText(S.idx)}. ${S.timeOpen ? "Trykk for å lukke" : "Trykk for å velge tid og spille av"}`);
    const back = !atNow && (S.mode==="home" || S.mode==="spot");
    document.querySelectorAll(".backnow").forEach(b=>{ b.hidden = !back; });
    $("#timeT").textContent = timeText(S.idx);
    $("#timeNow").hidden = !atNow;
    $("#timeL").textContent = lightWord(lightOf(h));
    const tid = $("#tid"); tid.max = S.maxIdx; if(+tid.value !== S.idx) tid.value = S.idx;
    tid.setAttribute("aria-valuetext", timeText(S.idx));
    $("#play").setAttribute("aria-label", S.playing ? "Stopp avspilling" : "Spill av varselet");
    $("#play").innerHTML = S.playing
      ? `<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="2" width="3.5" height="12" rx="1" fill="currentColor"/><rect x="9.5" y="2" width="3.5" height="12" rx="1" fill="currentColor"/></svg>`
      : `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9.5-5.5z" fill="currentColor"/></svg>`;
    if(!$("#ticks").dataset.done){
      const H = DATA.spots[0].hours; let out = "", last = null;
      H.forEach((hh,i)=>{ if(i > S.maxIdx) return; const d = dayKey(new Date(hh.t)); if(last!==null && d!==last && i>0) out += `<span style="left:calc(12px + (100% - 24px) * ${(i/S.maxIdx).toFixed(4)})">${esc(fmtWd.format(new Date(hh.t)).replace(/\.$/,""))}</span>`; last = d; });
      $("#ticks").innerHTML = out; $("#ticks").dataset.done = "1";
    }
    // «Tilbake til nå» i arket (mobil) endrer hvor mye som stikker opp i kartmodus
    if(back !== S.back){ S.back = back; if(coastReady && !isDesktop()) layout(true); }
  }

  /* ---------- svarlinja: «hvor og når bør jeg surfe?» ---------- */
  function regionSpots(view){
    // «området i utsnittet»: de samme spotene som kartets utsnitt rammer inn;
    // «Alle» er alle spots, også de som ligger utenfor kystkartet
    if(view==="alle" || !coastReady) return DATA.spots;
    const ids = Kart.viewSpotIds(view);
    return DATA.spots.filter(s=>ids.has(s.id));
  }
  function sessionAt(s, i){
    // fra time i og fremover så lenge stjernene er de samme og lyset brukbart
    // (samme regel som det gamle «Beste»-kortet) - spoten åpnes på time i
    const st = stars(s.hours[i]); let j = i;
    while(j+1 <= S.maxIdx && s.hours[j+1] && usable(s.hours[j+1]) && stars(s.hours[j+1])===st) j++;
    return {s, i, j, st};
  }
  function firstHour(spots, lo, hi, minSt){
    // første (tidligste) time med minst minSt stjerner i brukbart lys; samme
    // time hos flere spots: flest stjerner, så favoritt, så rekkefølgen i spots.json
    for(let i=lo; i<hi; i++){
      let best = null;
      for(const s of spots){
        const h = s.hours[i]; if(!h || !usable(h) || stars(h) < minSt) continue;
        const c = {s, st: stars(h), fav: isFavSpot(s.id)};
        if(!best || c.st > best.st || (c.st===best.st && c.fav && !best.fav)) best = c;
      }
      if(best) return sessionAt(best.s, i);
    }
    return null;
  }
  function answer(){
    // Theodor 13.10.2026: finnes en time med 2 stjerner eller mer i dagslys de
    // neste 3 dagene (72 t fra nå) i området i utsnittet, er det neste gode økt;
    // ellers «Ingen surf …» og den neste dagen med stjerner, hvis den finnes
    const spots = regionSpots(S.view), hi = Math.min(S.w3, S.maxIdx + 1);
    const good = firstHour(spots, S.w0, hi, 2);
    if(good) return {kind:"good", ...good};
    return {kind:"none", next: firstHour(spots, S.w0, S.maxIdx + 1, 1), gaps: windowGaps(spots, S.w0, hi)};
  }
  function windowGaps(spots, lo, hi){
    // Grunnregelen (fysikk-kontrollør 13.10.2026): «Ingen surf …» er en påstand om
    // HELE vinduet. Den holder ikke hvis en time som kan være lys mangler tallet,
    // en time med 2 stjerner eller mer har ukjent lys, eller varselet slutter før
    // 72 timer - da sier svarlinja i tillegg at noen timer mangler data.
    if(hi < S.w3 || S.w3 >= DATA.spots[0].hours.length) return true;
    for(const s of spots) for(let i=lo; i<hi; i++){
      const h = s.hours[i];
      if(!h) return true;
      const l = lightOf(h);
      if(l==="mørkt") continue;
      if(!known(h)) return true;                    // lys eller ukjent lys, og tallet mangler
      if(l==null && stars(h) >= 2) return true;     // stjerner, men vi vet ikke om det er lyst
    }
    return false;
  }
  function spanText(s, i, j){
    // «17–19»; går økta over midnatt (midnattssol), står sluttdagen med: «22–fre 03»
    const a = new Date(s.hours[i].t), b = new Date(s.hours[j].t);
    const end = String((+fmtHour.format(b) + 1) % 24).padStart(2, "0");
    if(dkOf(s.hours[i].t) === dkOf(s.hours[j].t)) return `${fmtHour.format(a)}–${end}`;
    return `${fmtHour.format(a)}–${relDayShort(new Date(b.getTime() + 36e5))} ${end}`;
  }
  const CHEV = `<svg class="ans-chev" viewBox="0 0 14 14" aria-hidden="true"><path d="M5 3l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  function answerHtml(){
    const a = answer();
    if(a.kind==="good"){
      const day = cap(relDay(new Date(a.s.hours[a.i].t))), span = spanText(a.s, a.i, a.j);
      const aria = `Neste gode økt: ${a.s.name}, ${day} ${span}, ${STR.starsAria(a.st, 0)}. Trykk for å åpne`;
      return `<button type="button" class="ans r-${Math.min(5, a.st)}" id="ansBtn" data-spot="${esc(a.s.id)}" data-idx="${a.i}" aria-label="${esc(aria)}">
        <span class="ans-txt"><span class="ans-k">Neste gode økt</span><span class="ans-n">${esc(a.s.name)}</span><span class="ans-w">${esc(day)} ${numHtml(span)}${a.s.area ? ` · ${esc(a.s.area)}` : ""}</span></span>
        <span class="ans-r">${starsRow(a.st)}${CHEV}</span></button>`;
    }
    const head = `Ingen surf de neste 3 dagene ${S.view==="alle" ? "på noen spot" : `i ${segName(S.view)}`}`;
    // mangler noen timer data, står det rett under påstanden (stiplet = mangler, som i uka)
    const q = a.gaps ? `<span class="ans-q"><i aria-hidden="true"></i>Noen timer mangler data</span>` : "";
    const headAria = head + (a.gaps ? ", men noen timer mangler data" : "");
    if(!a.next) return `<div class="ans none r-0" id="ansBtn"><span class="ans-txt"><span class="ans-k">Neste gode økt</span><span class="ans-n none">${esc(head)}</span>${q}</span></div>`;
    const n = a.next, where = `${relDay(new Date(n.s.hours[n.i].t))} · ${n.s.name}`;
    const aria = `${headAria}. Neste dag med stjerner: ${where}, ${STR.starsAria(n.st, 0)}. Trykk for å åpne`;
    return `<button type="button" class="ans none r-0" id="ansBtn" data-spot="${esc(n.s.id)}" data-idx="${n.i}" aria-label="${esc(aria)}">
      <span class="ans-txt"><span class="ans-k">Neste gode økt</span><span class="ans-n none">${esc(head)}</span>${q}<span class="ans-w">Neste dag med stjerner: <span class="nw">${esc(where)} ${miniStars(n.st)}</span></span></span>
      <span class="ans-r">${CHEV}</span></button>`;
  }
  function miniStars(st){
    // bare de fylte stjernene, i ratingfargen - til tekstlinjer der fem stjerner ikke får plass
    let out = ""; for(let k=0;k<st;k++) out += `<svg viewBox="0 0 24 24" aria-hidden="true"><path class="st" d="${STAR_PATH}"/></svg>`;
    return `<span class="stars mini r-${Math.min(5, st)}" aria-hidden="true">${out}</span>`;
  }
  function renderAnswer(){
    $("#answer").innerHTML = answerHtml();
    const b = $("#answer").querySelector("button.ans");
    if(b) b.onclick = ()=>{ if(!justDragged) openSpot(b.dataset.spot, +b.dataset.idx); };
  }

  /* ---------- teksten på kartet når hele utsnittet er 0 stjerner ---------- */
  function mapNote(){
    if(S.mode!=="home") return null;
    const spots = regionSpots(S.view); if(!spots.length) return null;
    let top = 0;
    for(const s of spots){
      const h = hourAt(s, S.idx);
      if(!known(h) || stars(h) >= 1) return null;   // et tall som mangler gir ingen påstand
      const k = ZERO_WORDS.indexOf(ratingWord(h));
      top = (k < 0 || top < 0) ? -1 : Math.max(top, k);
    }
    // samme regel som klyngepila: «Flatt» bare når alle er ekte flate
    const word = top < 0 ? "Ingen surf" : top===1 ? "Bare smått" : "Flatt";
    const where = S.view==="alle" ? "på alle spots" : `i hele ${segName(S.view)}`;
    const t = T(S.idx);
    const when = S.idx===nowIdx() ? "nå" : `${relDayShort(t)} ${fmtHour.format(t)}:00`;
    return `${word} ${where} ${when}`;
  }

  /* ---------- ukeoversikten: 7 dager, beste rating i lyse timer ---------- */
  function dayBest(s, day){
    // i dag: bare timene fra nå. «dark»: kjent mørke hele resten av dagen;
    // «miss»: tallet mangler (stiplet ramme) - aldri tolket som 0 stjerner.
    // Ukjent lys er ikke mørkt: en time med ukjent lys og stjerner eller uten
    // tall gjør dagen usikker, og en dag med bare ukjent lys er «miss».
    let any = false, light = false, unk = false, miss = false, best = -1;
    for(let i = S.w0; i < s.hours.length; i++){
      const h = s.hours[i], k = dkOf(h.t);
      if(k > day.key) break;
      if(k !== day.key) continue;
      any = true;
      const l = lightOf(h);
      if(l==null){ unk = true; if(!known(h) || stars(h) >= 1) miss = true; continue; }
      if(l!=="dag" && l!=="skumring") continue;
      light = true;
      if(!known(h)){ miss = true; continue; }
      best = Math.max(best, stars(h));
    }
    if(!any) return {cls:"miss", st:null};
    if(best >= 1) return {cls:`r-${Math.min(5, best)}`, st:best};
    if(miss || (!light && unk)) return {cls:"miss", st:null};
    if(!light) return {cls:"dark", st:null};
    return {cls:"r-0", st:0};
  }
  function weekText(week){
    const st = week.filter(w=>w.st>=1).map(w=>`${w.d.name} ${w.st}`);
    const miss = week.filter(w=>w.cls==="miss").map(w=>w.d.name);
    return (st.length ? `Stjerner i uka: ${st.join(", ")}` : "Ingen stjerner i uka") + (miss.length ? `. Mangler data: ${miss.join(", ")}` : "");
  }

  /* ---------- lista: favoritter øverst, så beste de neste 3 dagene ---------- */
  function best3(s){
    let mx = -1;
    for(let i=S.w0; i<S.w3 && i<s.hours.length; i++){ const h = s.hours[i]; if(usable(h) && known(h)) mx = Math.max(mx, stars(h)); }
    return mx;
  }
  function rowsSorted(){
    const order = (arr)=> arr.map((s, k)=>({s, k, b: best3(s)})).sort((x, y)=> y.b - x.b || x.k - y.k).map(x=>x.s);
    return { favs: order(DATA.spots.filter(s=>isFavSpot(s.id))), rest: order(DATA.spots.filter(s=>!isFavSpot(s.id))) };
  }
  function rtHtml(h){
    // ratingen nå: stjerner og høyde, eller ordet ved 0 stjerner
    const st = stars(h);
    return `${st ? starsRow(st) : ""}<span class="lb">${numHtml(markLabel(h))}</span>`;
  }
  function rowHtml(s){
    const h = hourAt(s, S.idx); const st = stars(h);
    const kj = kjText(h);
    const week = S.days.map(d=>({d, ...dayBest(s, d)}));
    const wt = weekText(week);
    return `<button type="button" class="row r-${Math.min(5, st)}${st?" lit":""}" data-spot="${esc(s.id)}" data-week="${esc(wt)}" aria-label="${esc(`Åpne ${s.name}: ${markAria(s, h)}. ${wt}`)}">
      <span class="nm"><b>${esc(s.name)}</b><small>${esc(s.area||"")}${isDesktop() && kj ? ` · ${numHtml(kj)}` : ""}</small></span>
      <span class="week" aria-hidden="true">${week.map(w=>`<span class="wd" data-day="${w.d.key}"><i class="wc ${w.cls}"></i><b>${esc(w.d.letter)}</b></span>`).join("")}</span>
      <span class="rt">${rtHtml(h)}</span></button>`;
  }
  function renderList(){
    const {favs, rest} = rowsSorted();
    let out = "";
    if(favs.length) out += `<div class="rows-head"><span>Favoritter</span></div>${favs.map(rowHtml).join("")}`;
    out += `<div class="rows-head"><span>${favs.length ? "Andre spots" : "Alle spots"}</span></div>${rest.map(rowHtml).join("")}`;
    $("#list").innerHTML = out;
    $("#list").querySelectorAll(".row").forEach(b=>b.onclick = ()=>openSpot(b.dataset.spot));
  }
  function renderListLite(){
    // under avspilling: bare ratingen nå per rad - uka og rekkefølgen regnes fra nå
    $("#list").querySelectorAll(".row").forEach(b=>{
      const s = DATA.spots.find(x=>x.id===b.dataset.spot); const h = hourAt(s, S.idx); const st = stars(h);
      b.className = `row r-${Math.min(5, st)}${st?" lit":""}`;
      b.querySelector(".rt").innerHTML = rtHtml(h);
      b.setAttribute("aria-label", `Åpne ${s.name}: ${markAria(s, h)}. ${b.dataset.week}`);
    });
  }

  /* ---------- spot ---------- */
  function pt(bearing, r){ const a = bearing*Math.PI/180; return [r*Math.sin(a), -r*Math.cos(a)]; }
  function segs(win){ return Array.isArray(win[0]) ? win : [win]; }
  function wedgePath(win, r){ return segs(win).map(([a,b])=>{ const span=(b-a+360)%360, p1=pt(a,r), p2=pt(b,r); return `M0,0L${p1[0].toFixed(1)},${p1[1].toFixed(1)}A${r},${r} 0 ${span>180?1:0} 1 ${p2[0].toFixed(1)},${p2[1].toFixed(1)}Z`; }).join(""); }
  function winText(win){ return segs(win).map(([a,b])=>`${a}–${b}°`).join(" og "); }
  function discSvg(s, h){
    const st = stars(h); const col = st>=1 ? COL(st) : "#9FE3EE";
    const sd = h ? h.dir_offshore : null;
    const cls = Kart.hitClass(h);   // samme regel som kilen på kartet (bare h.directness)
    const per = h && h.period!=null ? h.period : 10; const dur = Math.max(1.8, Math.min(4.4, per*0.26));
    const f = pt(s.facing||0, 52);
    let arcs = "";
    if(sd!=null && cls!=="miss"){ for(let i=0;i<4;i++) arcs += `<path class="arc ${cls}" d="M-15,-54 Q0,-59 15,-54" style="stroke:${col};animation-duration:${dur.toFixed(2)}s;animation-delay:-${(dur*i/4).toFixed(2)}s"/>`; }
    else if(sd!=null) arcs = `<line class="arc-miss" x1="0" y1="-58" x2="0" y2="-10"/>`;
    // vindpila står på fra-siden og peker INN mot sentrum - dit vinden går
    // (som vindlaget på kartet og pila i lista; fysikk-kontrollør 09.10.2026)
    const wind = h && h.wind_dir!=null ? `<g transform="rotate(${h.wind_dir})"><path class="windp" d="M0,-64 L5,-74 L-5,-74 Z"/></g>` : "";
    return `<svg class="disc" viewBox="-64 -64 128 128" role="img" aria-label="Svellvindu ${esc(winText(s.swell_window||[0,0]))}, ${sd==null || (h && h.directness==null) ? "svellretning ukjent" : `svell fra ${Math.round(sd)} grader, ${cls==="miss"?"treffer ikke":"treffer"}`}">
      <circle class="ring" r="58"/><path class="wedge-fill" d="${wedgePath(s.swell_window||[0,0], 56)}" style="fill:${cls==="miss"?"#9FE3EE":col};stroke:${cls==="miss"?"#9FE3EE":col}"/>
      <line class="facing" x1="0" y1="0" x2="${f[0].toFixed(1)}" y2="${f[1].toFixed(1)}"/>
      <g transform="rotate(${sd==null?0:sd})">${arcs}</g>${wind}<circle class="c" r="3"/></svg>`;
  }
  function flatInfo(win, start, total){
    // Er alle timene i grafen 0 stjerner: kompakt visning med «Flatt de neste
    // X timene» (bare når alle er EKTE flate) eller «Ingen surf ...» - samme
    // regel som grafen i designrunde 1 (manglende tall er ikke flatt).
    if(!win.length || win.some(x=>(x.stars||0) > 0)) return null;
    // Alle timene «Flatt»/«Smått» (ordet fra ratingWord, samme regel som
    // klyngepila i kart.js): «Smått» hvis minst én er smått, ellers «Flatt».
    // Alt annet (grøtete, blåst ut, treffer ikke, stormsjø ...) → «Ingen surf».
    let top = 0;
    for(const x of win){
      if(x.surf_height==null && !x.low_reason) return null;
      const k = ZERO_WORDS.indexOf(ratingWord(x));
      if(k < 0){ top = -1; break; }
      top = Math.max(top, k);
    }
    const T = top < 0 ? STR.noSurf : top===1 ? STR.small : STR.flat;
    const n = win.length;
    if(start + n >= total) return T.rest;
    return n >= 48 ? T.next(n) : T.allDay;
  }
  function barsHtml(s){
    const start = S.idx < S.w0 + 40 ? S.w0 : Math.max(S.w0, S.idx - 8);
    const win = s.hours.slice(start, start + 48);
    const flat = flatInfo(win, start, s.hours.length);
    if(flat){
      // kompakt: ingen dagnavn (de kolliderte med teksten - Theodor 09.10.2026)
      return `<span class="flat-lbl">${esc(flat)}</span>` + win.map((x,k)=>{
        const i = start + k, d = new Date(x.t);
        return `<button type="button" class="hbar flat${i===S.idx?" sel":""}" data-i="${i}" aria-label="${esc(cap(relDay(d)))} ${fmtHour.format(d)}:00, ${esc(ratingWord(x))}"><span class="b" style="height:3px;--rc:rgba(234,242,244,.22)"></span></button>`;
      }).join("");
    }
    const maxS = Math.max(2, ...win.map(x=>x.surf_height_sets || x.surf_height || 0));
    let lastDay = null;
    return win.map((x,k)=>{
      const i = start + k, s2 = stars(x), m = heightMForDisplay(x);
      // Mangler tallet helt (ingen surfehøyde, ingen low_reason): INGEN søyle,
      // bare en stiplet «mangler»-markør - aldri en strek som ser ut som flatt.
      const missing = m==null && !x.low_reason;
      const bh = m ? Math.max(3, Math.round(m / maxS * 80)) : 3, th = x.surf_height_sets ? Math.round(x.surf_height_sets / maxS * 80) : 0;
      const d = new Date(x.t), dk = dayKey(d), newDay = dk!==lastDay; lastDay = dk;
      const l = lightOf(x);
      return `<button type="button" class="hbar${l==="mørkt"?" night":l==="skumring"?" dusk":""}${i===S.idx?" sel":""}${missing?" miss":""} r-${s2}" data-i="${i}" aria-label="${esc(cap(relDay(d)))} ${fmtHour.format(d)}:00, ${missing ? "mangler data" : esc(x.stars ? STR.starsAria(x.stars, x.faded) : ratingWord(x))}${heightRangeText(x)?", "+esc(heightRangeText(x)):""}" title="${esc(tipHtml(x).replace(/<[^>]+>/g," "))}">
        ${missing ? `<span class="miss-mk" aria-hidden="true"></span>` : `<span class="b" style="height:${bh}px;${s2?"":"--rc:rgba(234,242,244,.22)"};animation-delay:${k*14}ms"></span>`}
        ${th ? `<span class="tk" style="bottom:${th}px"></span>` : ""}
        ${newDay ? `<span class="d">${esc(relDay(d))}</span>` : ""}</button>`;
    }).join("");
  }
  function renderSpot(lite){
    const s = DATA.spots.find(x=>x.id===S.spotId); if(!s) return;
    const h = hourAt(s, S.idx); const t = T(S.idx) || new Date();
    const st = stars(h);
    const info = coastReady ? Kart.spotInfo(s.id) : null;
    const root = $("#spot");
    if(lite && root.dataset.spot===s.id){
      // avspilling/glidebryter: oppdater bare tallene, ikke hele arket
      root.querySelector(".spot-head .s").textContent = `${s.area||""} · ${timeText(S.idx)} · ${lightWord(lightOf(h)).toLowerCase()}`;
      root.querySelector(".rating-line").innerHTML = ratingLine(h);
      root.querySelector("#tHeight .v").textContent = tileHeight(h);
      root.querySelector("#tPeriod .v").textContent = h && h.period!=null ? `${nf0.format(h.period)} s` : "–";
      root.querySelector("#tKj .v").textContent = kjText(h) || "–";
      root.querySelector("#tKjSmall").textContent = kjText(h) || "–";
      root.querySelector(".disc-box").innerHTML = discBox(s, h);
      root.querySelectorAll(".hbar").forEach(b=>b.classList.toggle("sel", +b.dataset.i===S.idx));
      root.querySelector("#details").innerHTML = `<summary>${esc(STR.details)}<span class="chev" aria-hidden="true">⌄</span></summary>${detailsGrid(s, h, t)}`;
      if(window.wireExplain) wireExplain(root, h, s);
      return;
    }
    const notice = h ? noticeFor(h) : null;
    root.dataset.spot = s.id;
    root.innerHTML = `
      <div class="spot-head rise">
        <div><div class="n">${esc(s.name)}</div><div class="s">${esc(s.area||"")} · ${esc(timeText(S.idx))} · ${esc(lightWord(lightOf(h)).toLowerCase())}</div></div>
        <div class="spot-tools">${favBtnHtml(s.id, false)}<button type="button" class="btn ghost pc-only" id="logBtn">${esc(STR.log)}</button><button type="button" class="close" id="closeSpot" aria-label="Lukk spot"><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></button></div>
      </div>
      <button type="button" class="now rise" id="bdOpen" aria-label="${esc(STR.whyRating)}" style="animation-delay:60ms"><span class="rating-line">${ratingLine(h)}</span></button>
      <div class="tiles rise" style="animation-delay:110ms">
        <button type="button" class="tile" id="tHeight" data-explain="surf_height"><span class="k">Surfehøyde</span><span class="v">${esc(tileHeight(h))}</span></button>
        <button type="button" class="tile" id="tPeriod" data-explain="period"><span class="k"><span class="pc-hide">Periode · energi</span><span class="pc-only">Periode</span></span><span class="v">${h && h.period!=null ? `${nf0.format(h.period)} s` : "–"}</span><span class="s pc-hide" id="tKjSmall">${esc(kjText(h) || "–")}</span></button>
        <button type="button" class="tile pc-only" id="tKj" data-explain="energy"><span class="k">Energi</span><span class="v">${esc(kjText(h) || "–")}</span></button>
      </div>
      <div class="disc-box rise" style="animation-delay:160ms">${discBox(s, h)}</div>
      ${notice ? `<button type="button" class="notice${notice.warn?"":" info"} rise" data-explain="${notice.key}"><span class="t">${esc(notice.text)}</span><span class="chev" aria-hidden="true">›</span></button>` : ""}
      <div class="rise" style="animation-delay:210ms">
        <div class="bars-head"><span>Neste 48 timer</span><small>Trykk for å velge time</small></div>
        <div class="bars${flatInfo(s.hours.slice(S.idx < S.w0 + 40 ? S.w0 : Math.max(S.w0, S.idx - 8), (S.idx < S.w0 + 40 ? S.w0 : Math.max(S.w0, S.idx - 8)) + 48), S.idx < S.w0 + 40 ? S.w0 : Math.max(S.w0, S.idx - 8)) ? " compact" : ""}" id="bars">${barsHtml(s)}</div>
      </div>
      ${info && info.offMap ? `<div class="note">Ligger utenfor kartutsnittet. Kartet viser Nord-Norge.</div>` : ""}
      <div class="spot-tools pc-hide"><button type="button" class="btn ghost" id="logBtnBottom">${esc(STR.log)}</button></div>
      <details class="details" id="details"><summary>${esc(STR.details)}<span class="chev" aria-hidden="true">⌄</span></summary>${detailsGrid(s, h, t)}</details>`;
    $("#closeSpot").onclick = closeSpot;
    $("#bdOpen").onclick = ()=> h && openBreakdown(h);
    $("#logBtn").onclick = ()=> openSheet(s.id, t);
    $("#logBtnBottom").onclick = ()=> openSheet(s.id, t);
    root.querySelectorAll(".hbar").forEach(b=>b.onclick = ()=>setIdx(+b.dataset.i));
    wireFavButtons();
    if(window.wireExplain) wireExplain(root, h, s);
    $("#ark .ark-scroll").scrollTop = 0;
  }
  function ratingLine(h){
    const st = stars(h);
    if(!st) return `<span class="word big">${esc(ratingWord(h))}</span>`;
    return `${starsRow(st)}<span class="word r-${st}">${esc(ratingWord(h))}</span>`;
  }
  function discBox(s, h){
    const sd = h ? h.dir_offshore : null;
    const cls = Kart.hitClass(h);
    const hit = cls!=="miss";
    const fromTxt = sd!=null ? ` fra ${compass(sd)} (${Math.round(sd)}°)` : "";   // ingen grader når retningen mangler
    const swell = h && h.swell_offshore!=null ? `${nf1.format(h.swell_offshore)} m${fromTxt}` : (h && h.height_offshore!=null ? `${nf1.format(h.height_offshore)} m totalt${fromTxt}` : "Ingen svelldata");
    // samme ord som Retningstreff-cellen (app.js directionHitText: "" når tallet mangler)
    const dh = h ? directionHitText(h) : "";
    const hitText = dh ? `${dh}${cls!=="" ? ` ${winText(s.swell_window||[0,0])}` : ""}` : "";
    const wind = h && h.wind_speed!=null ? `${nf0.format(h.wind_speed)} m/s ${windLabel(h)} fra ${compass(h.wind_dir)}` : "–";
    return `${discSvg(s, h)}<div class="disc-txt">
      <button type="button" class="tap" data-explain="direction" style="all:unset;cursor:pointer;display:flex;flex-direction:column;gap:1px"><span class="k">Svell</span><span class="v">${esc(swell)}</span><span class="h${hit?" hit":""}">${esc(hitText)}</span></button>
      <button type="button" class="tap" data-explain="wind" style="all:unset;cursor:pointer;display:flex;flex-direction:column;gap:1px"><span class="k">Vind</span><span class="v">${esc(wind)}</span></button></div>`;
  }

  function go(mode){
    // «list»/«peek» fra før: hjemmesiden med arket helt oppe / i halv høyde
    if(mode==="list"){ S.mode = "home"; S.sheet = "full"; }
    else if(mode==="peek" || mode==="half"){ S.mode = "home"; S.sheet = "half"; }
    else if(mode==="map"){ S.mode = "home"; S.sheet = "map"; }
    else S.mode = mode;
    renderAll();
  }
  function refresh(){ if(DATA) renderAll(); }
  window.Front = { start, openSpot, setIdx, go, refresh, backToNow, state: S };
  // app.js sin start() (global) kjøres først nå, når kartmotoren og fronten er lastet
  window.start();
})();
