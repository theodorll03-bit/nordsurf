/* Nordsurf: forsiden «kart først» (09.10.2026, Theodors skisse i
   docs/design/kart-forst/). Kartet er forsiden; arket (mobil: kikk/liste/
   spot, dras med fingeren) eller panelet (PC) viser tid, «Beste neste 48
   timer», lista med minigrafer og spotdetaljene. Logg, Logger og
   Innstillinger er knapper i toppen, ikke faner. Alt fra designrunde 1 som
   fortsatt brukes (forklaringsarkene, Detaljer-rutenettet, loggarket,
   breakdown, advarslene) kommer fra app.js/explain.js.

   Ren visning: ingen rating regnes her - bare forecast.json sine felter. */
(function(){
  const $ = (s, r)=> (r||document).querySelector(s);
  const S = { idx:0, mode:"peek", spotId:null, view:"nord", playing:false, maxIdx:0, h48:0, drag:null };
  let timer = null, coastReady = false;

  const COL = (st)=> (window.Kart ? Kart.COL : {})[Math.min(5, st||0)] || "#617480";
  const T = (i)=> DATA.spots[0].hours[i] ? new Date(DATA.spots[0].hours[i].t) : null;
  const hourAt = (spot, i)=> spot.hours[i] || null;
  const stars = (h)=> h ? (h.stars||0) : 0;
  const lightOf = (h)=> window.Kart ? Kart.lightOf(h) : (h && h.light) || null;   // null = ukjent, aldri "dag"
  const lightWord = (l)=> l==="mørkt" ? "Mørkt" : l==="skumring" ? "Skumring" : l==="dag" ? "Dagslys" : "–";
  const markLabel = (h)=> stars(h) >= 1 && h.surf_height!=null ? `${nf1.format(h.surf_height)} m` : ratingWord(h);
  const markAria = (s, h)=> `${s.name}, ${stars(h) ? STR.starsAria(h.stars, h.faded) + ", " + markLabel(h) : ratingWord(h)}`;
  const timeText = (i)=>{ const t = T(i); return t ? `${cap(relDay(t))} ${fmtHour.format(t)}:00` : ""; };
  const starsRow = (st, big)=> starsSVG(st, 0, big);
  const fmtWd = new Intl.DateTimeFormat("nb-NO", {weekday:"short", timeZone:TZ});

  /* ---------- oppstart ---------- */
  async function start(data){
    // tidsakse: glidebryteren dekker de første 7 døgnene, "48 timer" lista/søylene
    const H = data.spots[0].hours; const t0 = new Date(H[0].t).getTime();
    S.maxIdx = 0;
    H.forEach((h,i)=>{ const dt = new Date(h.t).getTime() - t0; if(dt <= 7*24*3600e3) S.maxIdx = i; });
    // «Neste 48 timer» regnes fra NÅTIMEN (ikke henterens kjøretid, som kan
    // ligge opptil 3-6 timer bak - fysikk-kontrollør 09.10.2026): w0..w1
    S.w0 = Math.max(0, Math.min(S.maxIdx, currentHour(data.spots[0])));
    const tw = new Date(H[S.w0].t).getTime();
    S.w1 = H.length; H.forEach((h,i)=>{ if(i > S.w0 && S.w1===H.length && new Date(h.t).getTime() >= tw + 48*3600e3) S.w1 = i; });
    S.idx = S.w0;
    let coast = window.__COAST__;
    if(!coast){ try{ coast = await (await fetch("geo/coast.json",{cache:"force-cache"})).json(); }catch(e){ coast = null; } }
    if(coast){
      Kart.init($("#kart"), data, coast, { onPick: (id)=>openSpot(id), hourOf: hourAt, labelOf: markLabel, ariaOf: markAria });
      coastReady = true;
    }
    $("#loading").hidden = true;
    wireTop(); wireSheet(); wireTime();
    parseRoute();
    if(isDesktop() && S.mode==="peek") S.mode = "list";
    layout(false);
    renderAll();
    window.addEventListener("hashchange", ()=>{ parseRoute(); renderAll(); });
    window.addEventListener("resize", ()=>layout(false));
    document.addEventListener("keydown", (e)=>{ if(e.key==="Escape" && S.mode==="spot") closeSpot(); });
  }

  /* ---------- ruter ---------- */
  function setRoute(){
    let hash = "#/";
    if(S.mode==="spot" && S.spotId) hash = `#/spot/${S.spotId}`;
    else if(S.mode==="logger" || S.mode==="innstillinger") hash = `#/${S.mode}`;
    else if(S.mode==="list") hash = "#/liste";
    if(location.hash !== hash) history.replaceState(null, "", hash);
  }
  function parseRoute(){
    const m = location.hash.match(/^#\/(spot\/([^/?#]+)|liste|logger|innstillinger)?/);
    if(!m || !m[1]){ if(S.mode!=="peek" && S.mode!=="list") S.mode = "peek"; return; }
    if(m[2]){ const id = decodeURIComponent(m[2]); if(DATA.spots.some(s=>s.id===id)){ S.spotId = id; S.mode = "spot"; } }
    else if(m[1]==="liste") S.mode = "list";
    else S.mode = m[1];
  }

  /* ---------- oppsett av kartets synlige område ---------- */
  const isDesktop = ()=> matchMedia("(min-width: 900px)").matches;
  function sheetY(){
    // mobil: hvor langt ned arket er skjøvet (px) per tilstand
    const H = window.innerHeight, top = 110, h = H - top;
    if(S.mode==="list" || S.mode==="logger" || S.mode==="innstillinger") return 0;
    if(S.mode==="spot") return Math.max(0, h - Math.min(620, Math.round(H*0.72)));
    return Math.max(0, h - 300);  // kikk
  }
  function layout(animate){
    if(!coastReady) return;
    const W = window.innerWidth, H = window.innerHeight;
    if(isDesktop()){
      Kart.setArea({x:0, y:0, w: W - 420 - 32, h: H}, animate);
    } else {
      const y = sheetY();
      $("#ark").style.setProperty("--sheet-y", y+"px");
      const visBottom = 110 + y;
      Kart.setArea({x:0, y:96, w: W, h: Math.max(120, visBottom - 96)}, animate);
    }
  }

  /* ---------- hendelser ---------- */
  function wireTop(){
    document.querySelectorAll(".seg button[data-view]").forEach(b=>b.onclick = ()=>{ S.view = b.dataset.view; S.spotId = null; S.mode = isDesktop() ? "list" : "peek"; if(coastReady) Kart.setView(S.view, true); renderAll(); });
    $("#btnLogg").onclick = ()=> openSheet(S.spotId || DATA.spots[0].id, T(S.idx) || new Date());
    $("#btnLogger").onclick = ()=>{ S.mode = "logger"; renderAll(); };
    $("#btnSettings").onclick = ()=>{ S.mode = "innstillinger"; renderAll(); };
  }
  function wireTime(){
    $("#play").onclick = ()=> setPlaying(!S.playing);
    $("#tid").oninput = (e)=>{ setIdx(+e.target.value); };
  }
  function setPlaying(on){
    if(timer){ clearInterval(timer); timer = null; }
    S.playing = on;
    if(on) timer = setInterval(()=>{ setIdx(S.idx >= S.maxIdx ? S.w0 : S.idx + 1); }, 240);  // starter på nytt fra nåtimen
    renderTime();
  }
  function setIdx(i){
    S.idx = Math.max(0, Math.min(S.maxIdx, i));
    if(coastReady) Kart.setHour(S.idx);
    renderTime();
    // under avspilling oppdateres bare det som endrer seg: merker (i Kart), tid, og spotens tall
    if(S.mode==="spot") renderSpot(true);
    else if(S.mode==="list" || S.mode==="peek") renderListLite();
  }
  function openSpot(id, idx){
    const s = DATA.spots.find(x=>x.id===id); if(!s) return;
    S.spotId = id; S.mode = "spot";
    if(idx!=null) S.idx = idx;
    renderAll();
  }
  function closeSpot(){ S.spotId = null; S.mode = isDesktop() ? "list" : "peek"; renderAll(); }

  /* ---------- arket dras med fingeren (mobil) ---------- */
  function wireSheet(){
    const ark = $("#ark");
    const handle = ark.querySelector(".ark-handle"), head = ark.querySelector(".ark-head");
    let startY = 0, baseY = 0, curY = 0, moved = false;
    const onDown = (e)=>{
      if(isDesktop() || e.pointerType==="mouse" && e.target.closest("input,button:not(.ark-handle)")) return;
      startY = e.clientY; baseY = sheetY(); curY = baseY; moved = false;
      ark.classList.add("dragging");
      (e.currentTarget).setPointerCapture && e.currentTarget.setPointerCapture(e.pointerId);
    };
    const onMove = (e)=>{
      if(!ark.classList.contains("dragging")) return;
      const dy = e.clientY - startY; if(Math.abs(dy) > 4) moved = true;
      const H = window.innerHeight - 110;
      curY = Math.max(0, Math.min(H - 80, baseY + dy));
      ark.style.setProperty("--sheet-y", curY+"px");
    };
    const onUp = ()=>{
      if(!ark.classList.contains("dragging")) return;
      ark.classList.remove("dragging");
      if(!moved){ layout(true); return; }
      // snapp til nærmeste tilstand
      const H = window.innerHeight - 110;
      const cands = [["list", 0], ["peek", Math.max(0, H - 300)]];
      if(S.spotId) cands.push(["spot", Math.max(0, H - Math.min(620, Math.round(window.innerHeight*0.72)))]);
      cands.sort((a,b)=>Math.abs(a[1]-curY) - Math.abs(b[1]-curY));
      const next = cands[0][0];
      if(next!==S.mode){ S.mode = next; if(next!=="spot") { /* beholder spotId for å kunne dra tilbake */ } renderAll(); }
      else layout(true);
    };
    for(const el of [handle, head]){
      el.addEventListener("pointerdown", onDown);
      el.addEventListener("pointermove", onMove);
      el.addEventListener("pointerup", onUp);
      el.addEventListener("pointercancel", onUp);
    }
    handle.onclick = ()=>{ if(moved) return; S.mode = S.mode==="peek" ? "list" : "peek"; renderAll(); };
  }

  /* ---------- rendering ---------- */
  function renderAll(){
    setRoute();
    document.querySelectorAll(".seg button[data-view]").forEach(b=>b.setAttribute("aria-pressed", String(S.view===b.dataset.view && S.mode!=="spot")));
    if(coastReady){
      if(S.mode==="spot" && S.spotId) Kart.setSpot(S.spotId, "spot", true);
      else { Kart.setSpot(null, (isDesktop() && S.mode==="list") ? "peek" : S.mode, true); Kart.setView(S.view, true); }  // PC: lista er i panelet, merkene står
      Kart.setHour(S.idx);
    }
    layout(true);
    for(const p of document.querySelectorAll(".page")) p.classList.toggle("on", p.dataset.page === (S.mode==="logger"||S.mode==="innstillinger" ? "side" : S.mode));
    $("#ark").querySelector(".ark-handle").setAttribute("aria-label", S.mode==="peek" ? "Vis alle spots" : "Vis kartet");
    $("#ark").classList.toggle("side", S.mode==="logger" || S.mode==="innstillinger");
    $("#ark").dataset.mode = S.mode;
    $("#banners").innerHTML = `${sampleBanner()}${staleBanner()}`;
    renderTime();
    if(S.mode==="peek") renderPeek();
    else if(S.mode==="list") renderList();
    else if(S.mode==="spot") renderSpot(false);
    else if(S.mode==="logger"){ renderPageBar("Logger"); renderLogs(); }
    else if(S.mode==="innstillinger"){ renderPageBar("Innstillinger"); renderSettings(); }
    if(S.mode!=="spot") $("#ark .ark-scroll").scrollTop = 0;
  }
  function renderPageBar(title){
    $("#pageBar").innerHTML = `<button type="button" class="back" id="pageBack"><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M8.5 3 4.5 7l4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>Kartet</button>`;
    $("#pageBack").onclick = ()=>{ S.mode = isDesktop() ? "list" : "peek"; renderAll(); };
  }
  function renderTime(){
    const t = T(S.idx);
    const f = coastReady ? Kart.focusSpot() : null;
    const h = f ? hourAt(f.s, S.idx) : hourAt(DATA.spots[0], S.idx);
    $("#timeT").textContent = timeText(S.idx);
    $("#timeNow").hidden = S.idx !== currentHour(DATA.spots[0]);
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
  }

  /* beste neste 48 timer: høyeste stjerner i lyse timer */
  function best48(){
    let best = null;
    DATA.spots.forEach(s=>{ for(let i=S.w0;i<S.w1;i++){ const h = s.hours[i]; if(!h || lightOf(h)==="mørkt") continue; const st = stars(h); if(!best || st > best.st) best = {s, i, st}; } });
    if(!best || best.st < 1) return null;
    let j = best.i; while(j+1 < S.w1 && stars(best.s.hours[j+1])===best.st && lightOf(best.s.hours[j+1])!=="mørkt") j++;
    const a = new Date(best.s.hours[best.i].t), b = new Date(best.s.hours[j].t);
    return { ...best, when: `${cap(relDay(a))} ${fmtHour.format(a)}–${String((+fmtHour.format(b)+1)%24).padStart(2,"0")} · ${best.s.area||""}` };
  }
  function bestCard(){
    const b = best48(); if(!b) return `<div class="note">${esc(STR.bestNone)}</div>`;
    const h = b.s.hours[b.i];
    return `<button type="button" class="best r-${b.st} rise" data-spot="${b.s.id}" data-idx="${b.i}" aria-label="Beste neste 48 timer: ${esc(b.s.name)}, ${esc(STR.starsAria(b.st, 0))}">
      <span class="l"><span class="k">Beste neste 48 timer</span><br><span class="n">${esc(b.s.name)}</span><br><span class="w">${esc(b.when)}</span></span>
      <span class="r">${starsRow(b.st)}<span class="h">${esc(heightRangeText(h))}</span></span></button>`;
  }
  function renderPeek(){
    $("#peek").innerHTML = `${bestCard()}<button type="button" class="btn-row" id="openList"><span>Alle spots</span><span class="m">${DATA.spots.length} steder<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 9 7 5.5 10.5 9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span></button>`;
    $("#openList").onclick = ()=>{ S.mode = "list"; renderAll(); };
    wireBest($("#peek"));
  }
  function wireBest(root){ const b = root.querySelector(".best"); if(b) b.onclick = ()=>openSpot(b.dataset.spot, +b.dataset.idx); }
  function rowsSorted(){
    return DATA.spots.map(s=>{ let mx = 0; for(let i=S.w0;i<S.w1;i++) mx = Math.max(mx, stars(s.hours[i])); return {s, mx}; }).sort((a,b)=>b.mx - a.mx);
  }
  function rowHtml(s, k){
    const h = hourAt(s, S.idx); const st = stars(h);
    let spark = "";
    for(let i=S.w0;i<S.w1;i+=2){ const x = s.hours[i]; const s2 = stars(x); spark += `<i style="height:${s2 ? 6 + s2*4 : 2}px;${s2?`--sc:${COL(s2)}`:""}"></i>`; }
    const kj = kjText(h);
    return `<button type="button" class="row r-${st}${st?" lit":""} rise" data-spot="${s.id}" style="animation-delay:${k*40}ms" aria-label="Åpne ${esc(s.name)}: ${esc(markAria(s, h))}">
      <span class="dot"></span>
      <span class="nm"><b>${esc(s.name)}</b><small>${esc(s.area||"")}${isDesktop() && kj ? ` · ${esc(kj)}` : ""}</small></span>
      <span class="spark" aria-hidden="true">${spark}</span>
      <span class="rt"><span class="lb">${esc(markLabel(h))}</span><small>${esc(windShorter(h))}</small></span></button>`;
  }
  function renderList(){
    const rows = rowsSorted();
    $("#list").innerHTML = `${isDesktop() ? bestCard() : ""}<div class="rows-head"><span>Alle spots</span><small>Neste 48 timer</small></div>${rows.map((r,k)=>rowHtml(r.s, k)).join("")}`;
    $("#list").querySelectorAll(".row").forEach(b=>b.onclick = ()=>openSpot(b.dataset.spot));
    wireBest($("#list"));
  }
  function renderListLite(){
    // under avspilling: bare etikett, farge og vind per rad
    $("#list").querySelectorAll(".row").forEach(b=>{
      const s = DATA.spots.find(x=>x.id===b.dataset.spot); const h = hourAt(s, S.idx); const st = stars(h);
      b.className = `row r-${st}${st?" lit":""}`;
      b.querySelector(".lb").textContent = markLabel(h); b.querySelector(".rt small").textContent = windShorter(h);
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
  function barsHtml(s){
    const start = S.idx < S.w0 + 40 ? S.w0 : Math.max(S.w0, S.idx - 8);
    const win = s.hours.slice(start, start + 48);
    const maxS = Math.max(2, ...win.map(x=>x.surf_height_sets || x.surf_height || 0));
    let lastDay = null;
    return win.map((x,k)=>{
      const i = start + k, s2 = stars(x), m = heightMForDisplay(x);
      const bh = m ? Math.max(3, Math.round(m / maxS * 80)) : 3, th = x.surf_height_sets ? Math.round(x.surf_height_sets / maxS * 80) : 0;
      const d = new Date(x.t), dk = dayKey(d), newDay = dk!==lastDay; lastDay = dk;
      const l = lightOf(x);
      return `<button type="button" class="hbar${l==="mørkt"?" night":l==="skumring"?" dusk":""}${i===S.idx?" sel":""} r-${s2}" data-i="${i}" aria-label="${esc(cap(relDay(d)))} ${fmtHour.format(d)}:00, ${esc(x.stars ? STR.starsAria(x.stars, x.faded) : ratingWord(x))}${heightRangeText(x)?", "+esc(heightRangeText(x)):""}" title="${esc(tipHtml(x).replace(/<[^>]+>/g," "))}">
        <span class="b" style="height:${bh}px;${s2?"":"--rc:rgba(234,242,244,.22)"};animation-delay:${k*14}ms"></span>
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
      root.querySelector("#tHeight .v").textContent = heightRangeText(h) || "–";
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
        <div class="spot-tools">${favBtnHtml(s.id, false)}<button type="button" class="close" id="closeSpot" aria-label="Lukk spot"><svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></button></div>
      </div>
      <button type="button" class="now rise" id="bdOpen" aria-label="${esc(STR.whyRating)}" style="animation-delay:60ms"><span class="rating-line">${ratingLine(h)}</span></button>
      <div class="tiles rise" style="animation-delay:110ms">
        <button type="button" class="tile" id="tHeight" data-explain="surf_height"><span class="k">Surfehøyde</span><span class="v">${esc(heightRangeText(h) || "–")}</span></button>
        <button type="button" class="tile" id="tPeriod" data-explain="period"><span class="k"><span class="pc-hide">Periode · energi</span><span class="pc-only">Periode</span></span><span class="v">${h && h.period!=null ? `${nf0.format(h.period)} s` : "–"}</span><span class="s pc-hide" id="tKjSmall">${esc(kjText(h) || "–")}</span></button>
        <button type="button" class="tile pc-only" id="tKj" data-explain="energy"><span class="k">Energi</span><span class="v">${esc(kjText(h) || "–")}</span></button>
      </div>
      <div class="disc-box rise" style="animation-delay:160ms">${discBox(s, h)}</div>
      ${notice ? `<button type="button" class="notice${notice.warn?"":" info"} rise" data-explain="${notice.key}"><span class="t">${esc(notice.text)}</span><span class="chev" aria-hidden="true">›</span></button>` : ""}
      <div class="rise" style="animation-delay:210ms">
        <div class="bars-head"><span>Neste 48 timer</span><small>Trykk for å velge time</small></div>
        <div class="bars" id="bars">${barsHtml(s)}</div>
      </div>
      ${info && info.offMap ? `<div class="note">Ligger utenfor kartutsnittet. Kartet viser Nord-Norge.</div>` : ""}
      <div class="spot-tools"><button type="button" class="btn ghost" id="logBtn">${esc(STR.log)}</button></div>
      <details class="details" id="details"><summary>${esc(STR.details)}<span class="chev" aria-hidden="true">⌄</span></summary>${detailsGrid(s, h, t)}</details>`;
    $("#closeSpot").onclick = closeSpot;
    $("#bdOpen").onclick = ()=> h && openBreakdown(h);
    $("#logBtn").onclick = ()=> openSheet(s.id, t);
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

  function go(mode){ S.mode = mode; renderAll(); }
  function refresh(){ if(DATA) renderAll(); }
  window.Front = { start, openSpot, setIdx, go, refresh, state: S };
  // app.js sin start() (global) kjøres først nå, når kartmotoren og fronten er lastet
  window.start();
})();
