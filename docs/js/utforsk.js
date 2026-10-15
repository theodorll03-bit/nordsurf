/* Nordsurf: Utforsk (Theodor 14.10.2026; Tillegg 2 15.10.2026).

   Utsnittsbrikkene lages fra regionene i oversikt.json (ramme rundt spotene i regionen pluss
   margin, regnet i publish.py) - ingen lister i JS. Markørene farges etter dagens
   sammendrag («dager») eller nå-timen («naa»); klynger og lapper i kart.js. Spots utenfor
   kartlaget samles i én brikke per region. Kortet nederst viser spot, tid, stjerner/ord,
   surf, svell ute og vind for valgt dag. Søket ligger ikke her (HIG 7). */
(function(){
  const $ = (s, r)=> (r||document).querySelector(s);
  const $$ = (s, r)=> [...(r||document).querySelectorAll(s)];
  const fmtWd = new Intl.DateTimeFormat("nb-NO", {weekday:"short", timeZone:TZ});
  const fmtWdLong = new Intl.DateTimeFormat("nb-NO", {weekday:"long", timeZone:TZ});
  let coast = null, coastLoading = null, inited = false, S = null;
  const H = ()=> Front.helpers;
  const min5 = (n)=> Math.min(5, n||0);

  function dayChips(){
    return H().weekDays().map((d, k)=>({key: k===0 ? null : d.key, label: k===0 ? "Nå" : k===1 ? "I morgen" : `${cap(fmtWd.format(new Date(d.key + "T11:00:00Z")).replace(/\.$/, ""))} ${d.dato}.`, lang: d.lang}));
  }
  // verdi per spot for valgt dag: nå = nå-timen; ellers dagens beste dagslystime (publish.best_hour)
  function valueFor(s, dayKeyOrNull){
    if(dayKeyOrNull!=null){
      const b = H().dayBest(s, dayKeyOrNull);
      if(b.cls==="miss") return {st:0, word:"–", miss:true, h:null, t:null, aria:`${s.name}: tallet mangler`};
      if(b.cls==="dark") return {st:0, word:"Mørkt", miss:false, h:null, t:null, aria:`${s.name}: mørkt hele dagen`};
      const w = b.h ? ratingWord(b.h) : "–";
      return {st:b.st, word:w, miss:false, h:b.h, t:b.t, aria:`${s.name}: ${w}${b.st ? ", " + STR.starsAria(b.st, 0) : ""}`};
    }
    const h = H().naaOf(s);
    if(!H().known(h)) return {st:0, word:"–", miss:true, h, t: h ? h.t : null, aria:`${s.name}: tallet mangler`};
    const st = H().stars(h), w = ratingWord(h);
    return {st, word:w, miss:false, h, t:h.t, aria:`${s.name}: ${w}${st ? ", " + STR.starsAria(st, 0) : ""}`};
  }
  function regionsHere(){ return (DATA.regions || []).filter(r=> r.extent); }
  function ensureInit(){
    if(inited) return true;
    if(!coast){
      coastLoading = coastLoading || fetch("geo/coast.json", {cache:"force-cache"}).then(r=>r.json()).then(c=>{ coast = c; if(S && S.view==="utforsk") render(S); else if(window.Front) Front.refresh(); }).catch(e=>console.error(e));
      return false;
    }
    Kart.init($("#kart"), coast, DATA.spots, {
      valueOf: (p)=> valueFor(p.s, S.utforskDay),
      onPick: (id)=>{ S.picked = S.picked===id ? null : id; renderKort(); Kart.setSelected(S.picked); },
      onCluster: (ids)=>{ const e = Kart.extentOf(ids); if(e){ S.utforskView = null; renderChips(); Kart.setExtent(e, true); } },
    });
    inited = true;
    return true;
  }
  function area(){
    const el = $("#kart"); const r = el.getBoundingClientRect();
    if(H().isDesktop()) return {x:0, y:0, w:r.width, h:r.height};
    const top = $("#utforskChips").getBoundingClientRect().bottom + 8 - r.top;
    const bottom = r.height - (r.bottom - $("#dagChips").getBoundingClientRect().top) - 8;
    return {x:0, y:top, w:r.width, h:Math.max(120, bottom - top)};
  }
  function viewExtent(){
    // valgt region, ellers «hele kartet» = alle regioner som ligger på kartlaget
    const regs = regionsHere().filter(r=> DATA.spots.some(s=> (s.region||s.area)===r.name && s.spot && Kart.covers(s.spot.lat, s.spot.lon)));
    const pick = S.utforskView && regs.find(r=>r.name===S.utforskView);
    const list = pick ? [pick] : regs;
    if(!list.length) return null;
    return [Math.min(...list.map(r=>r.extent[0])), Math.min(...list.map(r=>r.extent[1])), Math.max(...list.map(r=>r.extent[2])), Math.max(...list.map(r=>r.extent[3]))];
  }
  function renderChips(){
    const onMap = regionsHere().filter(r=> DATA.spots.some(s=> (s.region||s.area)===r.name && s.spot && Kart.covers(s.spot.lat, s.spot.lon)));
    const off = Kart.offMapSpots();
    const offBy = new Map(); for(const p of off){ const k = H().regionOf(p.s); if(!offBy.has(k)) offBy.set(k, []); offBy.get(k).push(p); }
    $("#utforskChips").innerHTML = onMap.map(r=>`<button type="button" class="chip" data-view="${esc(r.name)}" aria-pressed="${S.utforskView===r.name}">${esc(r.name)}</button>`).join("")
      + `<button type="button" class="chip" data-view="" aria-pressed="${!S.utforskView}">Hele kartet</button>`
      + [...offBy.entries()].map(([k, ps])=>`<button type="button" class="chip dashed" data-off="${esc(k)}" aria-label="${esc(`${k}: ${ps.length} ${ps.length===1 ? "spot" : "spots"} utenfor kartet - vis lista`)}"><span aria-hidden="true">↓</span> ${esc(k)}${ps.length > 1 ? ` <span class="num">${ps.length}</span>` : ""}</button>`).join("");
    $$("#utforskChips [data-view]").forEach(b=> b.onclick = ()=>{ S.utforskView = b.dataset.view || null; S.picked = null; renderChips(); const e = viewExtent(); if(e) Kart.setExtent(e, true); Kart.setSelected(null); renderKort(); renderListe(); });
    $$("#utforskChips [data-off]").forEach(b=> b.onclick = ()=>{ S.offRegion = b.dataset.off; renderKort(); });
    const chips = dayChips();
    $("#dagChips").innerHTML = chips.map(c=>`<button type="button" class="chip" data-day="${c.key||""}" aria-pressed="${(S.utforskDay||"")===(c.key||"")}" aria-label="${esc(c.key ? cap(c.lang) : "Nå")}">${esc(c.label)}</button>`).join("");
    $$("#dagChips .chip").forEach(b=> b.onclick = ()=>{ S.utforskDay = b.dataset.day || null; $$("#dagChips .chip").forEach(x=>x.setAttribute("aria-pressed", String(x===b))); Kart.redraw(); renderKort(); renderListe(); });
  }
  function kortHtml(s){
    const v = valueFor(s, S.utforskDay); const h = v.h;
    const t = v.t ? new Date(v.t) : null;
    const tid = S.utforskDay==null ? "nå" : t ? `${fmtWdLong.format(t)} kl. ${fmtHour.format(t)}` : cap(fmtWdLong.format(new Date(S.utforskDay + "T11:00:00Z")));
    const hoyde = H().ordOgHoyde(h).hoyde;
    return `<div class="topp"><div><div class="navn">${esc(s.name)}</div><div class="omr">${esc(H().stedText(s))} · ${esc(tid)}</div></div><button type="button" class="iconbtn lukk" id="kortLukk" aria-label="Lukk"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button></div>
      <div class="vurd r-${min5(v.st)}">${v.st ? starsSVG(v.st, 0) : ""}<span class="ord">${esc(v.word)}</span>${hoyde ? `<span class="num">${esc(hoyde)} m</span>` : ""}</div>
      <div class="fakta"><div>Surf<b>${hoyde ? `${esc(hoyde)} m` : h && h.surf_height!=null ? esc(Spot.kroppshoyde(h) || ratingWord(h)) : "–"}</b></div><div>Svell ute<b>${h && h.swell_offshore!=null ? `${nf1.format(h.swell_offshore)} m${h.period!=null ? ` · ${nf0.format(h.period)} s` : ""}${h.dir_offshore!=null ? ` fra ${esc(compass(h.dir_offshore))}` : ""}` : "–"}</b></div><div>Vind<b>${h && h.wind_speed!=null ? `${nf0.format(h.wind_speed)} m/s ${esc(windLabel(h))}` : "–"}</b></div></div>
      <button type="button" class="primary" id="kortApne">Se hele varselet</button>`;
  }
  function offListeHtml(region){
    const ps = Kart.offMapSpots().filter(p=> H().regionOf(p.s)===region).map(p=>({s: p.s, v: valueFor(p.s, S.utforskDay)})).sort((a, b)=> b.v.st - a.v.st || a.s.name.localeCompare(b.s.name, "nb"));
    return `<div class="topp"><div><div class="navn">${esc(region)}</div><div class="omr">${ps.length} ${ps.length===1 ? "spot" : "spots"} utenfor kartet</div></div><button type="button" class="iconbtn lukk" id="kortLukk" aria-label="Lukk"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button></div>
      <div class="alfa offliste" role="list">${ps.map(({s, v})=>{ const hoyde = H().ordOgHoyde(v.h).hoyde; return `<a class="srad r-${min5(v.st)}" href="#spot=${esc(s.id)}${v.t ? "&t=" + esc(v.t) : ""}" role="listitem" aria-label="${esc(v.aria)}"><span class="prikk${v.miss ? " miss" : ""}" aria-hidden="true"></span><span class="nm"><b>${esc(s.name)}</b><small>${esc(H().stedText(s))}</small></span><span class="na">${esc(v.word)}${hoyde ? `<span class="num">${esc(hoyde)} m</span>` : ""}</span></a>`; }).join("")}</div>`;
  }
  function renderKort(){
    const el = $("#kartKort"); const s = S.picked && DATA.spots.find(x=>x.id===S.picked);
    const off = !s && S.offRegion;
    el.hidden = !s && !off;
    if(!s && !off){ el.innerHTML = ""; return; }
    el.innerHTML = s ? kortHtml(s) : offListeHtml(S.offRegion);
    $("#kortLukk", el).onclick = ()=>{ S.picked = null; S.offRegion = null; Kart.setSelected(null); renderKort(); };
    const ap = $("#kortApne", el); if(ap){ const v = valueFor(s, S.utforskDay); ap.onclick = ()=> Front.openSpot(s.id, v.t || null); }
  }
  function renderListe(){
    const el = $("#utforskListe"); if(!el || !H().isDesktop()) return;
    const reg = S.utforskView;
    const spots = DATA.spots.filter(s=> !reg || H().regionOf(s)===reg).map(s=>({s, v: valueFor(s, S.utforskDay)}))
      .sort((a, b)=> b.v.st - a.v.st || ((b.v.h && b.v.h.surf_height)||0) - ((a.v.h && a.v.h.surf_height)||0) || a.s.name.localeCompare(b.s.name, "nb"));
    const dag = S.utforskDay==null ? "nå" : cap(fmtWdLong.format(new Date(S.utforskDay + "T11:00:00Z")));
    const shown = S.listeAlle ? spots : spots.slice(0, 30);
    el.innerHTML = `<div class="kort"><h2 class="h2" style="margin-bottom:8px">Beste først</h2><p class="sub" style="margin:0 0 8px">${esc(dag)}${reg ? ` · ${esc(reg)}` : ""}</p><div class="alfa lang" role="list">${shown.map(({s, v})=>{ const hoyde = H().ordOgHoyde(v.h).hoyde;
      return `<a class="srad r-${min5(v.st)}" href="#spot=${esc(s.id)}${v.t ? "&t=" + esc(v.t) : ""}" role="listitem" aria-label="${esc(v.aria)}"><span class="prikk${v.miss ? " miss" : ""}" aria-hidden="true"></span><span class="nm"><b>${esc(s.name)}</b><small>${esc(H().stedText(s))}</small></span><span class="na">${esc(v.word)}${hoyde ? `<span class="num">${esc(hoyde)} m</span>` : ""}</span></a>`; }).join("")}</div>${shown.length < spots.length ? `<button type="button" class="ghost visflere" id="listeFlere">Vis alle ${spots.length}</button>` : ""}</div>`;
    const more = $("#listeFlere", el); if(more) more.onclick = ()=>{ S.listeAlle = true; renderListe(); };
  }
  function render(state){
    S = state;
    if(!ensureInit()){ $("#utforskChips").innerHTML = `<span class="muted">Henter kartet …</span>`; return; }
    if(S.utforskView===undefined || S.utforskView===null && !S.utforskViewSatt){
      // første gang: regionen fra Innstillinger -> Område (Troms) hvis den ligger på kartlaget, ellers hele kartet
      const r = H().chosenRegion(); const onMap = regionsHere().some(x=> x.name===r && DATA.spots.some(s=> (s.region||s.area)===r && s.spot && Kart.covers(s.spot.lat, s.spot.lon)));
      S.utforskView = onMap ? r : null; S.utforskViewSatt = true;
    }
    renderChips();
    Kart.setArea(area());
    const e = viewExtent(); if(e) Kart.setExtent(e, false);
    Kart.setSelected(S.picked);
    renderKort(); renderListe();
  }
  function thumb(){
    if(!ensureInit()) return "";
    return Kart.thumb((p)=> valueFor(p.s, null).st);
  }
  window.addEventListener("resize", ()=>{ if(inited && S && S.view==="utforsk"){ Kart.setArea(area()); const e = viewExtent(); if(e) Kart.setExtent(e, false); } });
  window.Utforsk = { render, thumb, valueFor };
})();
