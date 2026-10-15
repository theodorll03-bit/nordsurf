/* Nordsurf: Utforsk - kartet (Theodor 14.10.2026, punkt 3 + HIG 7).

   Kartet fyller skjermen (mobil) / ligger til venstre i 10:7 med lista til
   høyre (nett). Øverst brikker for Troms / Lofoten / Hele kartet og en
   brikke for spots utenfor utsnittet (Farstadsanden ↓). Nederst dagbrikker:
   Nå, I morgen og så ukedag med dato, 7 dager. Markørene farges etter beste
   dagslystime den valgte dagen. Trykk på en markør åpner et kort nederst.
   Søket ligger ikke her (HIG 7: søk på ett sted).

   Ren visning: bare oversikt.json sine timer, ingen tall regnes. */
(function(){
  const $ = (s, r)=> (r||document).querySelector(s);
  const $$ = (s, r)=> [...(r||document).querySelectorAll(s)];
  const fmtWd = new Intl.DateTimeFormat("nb-NO", {weekday:"short", timeZone:TZ});
  const fmtDayNum = new Intl.DateTimeFormat("nb-NO", {day:"numeric", timeZone:TZ});
  const fmtWdLong = new Intl.DateTimeFormat("nb-NO", {weekday:"long", timeZone:TZ});
  let coast = null, coastLoading = null, inited = false, S = null;
  const H = ()=> Front.helpers;

  function dayChips(){
    const days = H().weekDays();
    return days.map((d, k)=>({key: k===0 ? null : d.key, label: k===0 ? "Nå" : k===1 ? "I morgen" : `${cap(fmtWd.format(new Date(d.key + "T11:00:00Z")).replace(/\.$/, ""))} ${d.dato}.`, lang: d.lang}));
  }
  // verdi per spot for valgt dag: nå = timen nå; ellers beste dagslystime den dagen
  function valueFor(s, dayKeyOrNull){
    const h = dayKeyOrNull==null ? s.hours[H().nowIdx(s)] : H().dayBest(s, dayKeyOrNull).h;
    if(dayKeyOrNull!=null){
      const b = H().dayBest(s, dayKeyOrNull);
      if(b.cls==="miss") return {st:0, word:"–", miss:true, h:null, idx:-1, aria:`${s.name}: tallet mangler`};
      if(b.cls==="dark") return {st:0, word:"Mørkt", miss:false, h:null, idx:-1, aria:`${s.name}: mørkt hele dagen`};
      return {st:b.st, word: b.h ? ratingWord(b.h) : "–", miss:false, h:b.h, idx:b.idx, aria:`${s.name}: ${b.h ? ratingWord(b.h) : "–"}${b.st ? ", " + STR.starsAria(b.st, 0) : ""}`};
    }
    if(!H().known(h)) return {st:0, word:"–", miss:true, h, idx:H().nowIdx(s), aria:`${s.name}: tallet mangler`};
    return {st:H().stars(h), word: ratingWord(h), miss:false, h, idx:H().nowIdx(s), aria:`${s.name}: ${ratingWord(h)}${H().stars(h) ? ", " + STR.starsAria(H().stars(h), 0) : ""}`};
  }
  function ensureInit(){
    if(inited) return true;
    if(!coast){
      coastLoading = coastLoading || fetch("geo/coast.json", {cache:"force-cache"}).then(r=>r.json()).then(c=>{ coast = c; if(S && S.view==="utforsk") render(S); else if(window.Front) Front.refresh(); }).catch(e=>console.error(e));
      return false;
    }
    Kart.init($("#kart"), DATA, coast, { valueOf: (p)=> valueFor(p.s, S.utforskDay), onPick: (id)=>{ S.picked = S.picked===id ? null : id; renderKort(); Kart.setSelected(S.picked); } });
    inited = true;
    return true;
  }
  function area(){
    const el = $("#kart"); const r = el.getBoundingClientRect();
    if(H().isDesktop()) return {x:0, y:0, w:r.width, h:r.height};
    // mobil: kartet fyller skjermen; brikkene øverst og nederst er hindre - hold merkene mellom dem
    const top = $("#utforskChips").getBoundingClientRect().bottom + 8 - r.top;
    const bottom = r.height - (r.bottom - $("#dagChips").getBoundingClientRect().top) - 8;
    return {x:0, y:top, w:r.width, h:Math.max(120, bottom - top)};
  }
  function renderChips(){
    const views = [["nord","Troms"],["lofoten","Lofoten"],["alle","Hele kartet"]];
    const off = Kart.offMapSpots();
    $("#utforskChips").innerHTML = views.map(([v, t])=>`<button type="button" class="chip" data-view="${v}" aria-pressed="${S.utforskView===v}">${t}</button>`).join("")
      + off.map(p=>`<button type="button" class="chip dashed" data-off="${esc(p.id)}" aria-label="${esc(p.name)}, utenfor kartet - vis kortet"><span aria-hidden="true">↓</span> ${esc(p.name)}</button>`).join("");
    $$("#utforskChips [data-view]").forEach(b=> b.onclick = ()=>{ S.utforskView = b.dataset.view; S.picked = null; renderChips(); Kart.setView(S.utforskView, true); Kart.setSelected(null); renderKort(); renderListe(); });
    $$("#utforskChips [data-off]").forEach(b=> b.onclick = ()=>{ S.picked = b.dataset.off; renderKort(); });
    const chips = dayChips();
    $("#dagChips").innerHTML = chips.map(c=>`<button type="button" class="chip" data-day="${c.key||""}" aria-pressed="${(S.utforskDay||"")===(c.key||"")}" aria-label="${esc(c.key ? cap(c.lang) : "Nå")}">${esc(c.label)}</button>`).join("");
    $$("#dagChips .chip").forEach(b=> b.onclick = ()=>{ S.utforskDay = b.dataset.day || null; $$("#dagChips .chip").forEach(x=>x.setAttribute("aria-pressed", String(x===b))); Kart.recolor(); renderKort(); renderListe(); });
  }
  function kortHtml(s){
    const v = valueFor(s, S.utforskDay); const h = v.h;
    const t = h ? new Date(h.t) : null;
    const tid = S.utforskDay==null ? "nå" : t ? `${fmtWdLong.format(t)} kl. ${fmtHour.format(t)}` : cap(fmtWdLong.format(new Date(S.utforskDay + "T11:00:00Z")));
    const hoyde = H().ordOgHoyde(h).hoyde;
    return `<div class="topp"><div><div class="navn">${esc(s.name)}</div><div class="omr">${esc(H().stedText(s))} · ${esc(tid)}</div></div><button type="button" class="iconbtn lukk" id="kortLukk" aria-label="Lukk"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button></div>
      <div class="vurd r-${Math.min(5,v.st)}">${v.st ? starsSVG(v.st, 0) : ""}<span class="ord">${esc(v.word)}</span>${hoyde ? `<span class="num">${esc(hoyde)} m</span>` : ""}</div>
      <div class="fakta"><div>Surf<b>${hoyde ? `${esc(hoyde)} m` : h && h.surf_height!=null ? esc(Spot.kroppshoyde(h) || ratingWord(h)) : "–"}</b></div><div>Svell ute<b>${h && h.swell_offshore!=null ? `${nf1.format(h.swell_offshore)} m${h.period!=null ? ` · ${nf0.format(h.period)} s` : ""}${h.dir_offshore!=null ? ` fra ${esc(compass(h.dir_offshore))}` : ""}` : "–"}</b></div><div>Vind<b>${h && h.wind_speed!=null ? `${nf0.format(h.wind_speed)} m/s ${esc(windLabel(h))}` : "–"}</b></div></div>
      <button type="button" class="primary" id="kortApne">Se hele varselet</button>`;
  }
  function renderKort(){
    const el = $("#kartKort"); const s = S.picked && DATA.spots.find(x=>x.id===S.picked);
    el.hidden = !s;
    if(!s){ el.innerHTML = ""; return; }
    el.innerHTML = kortHtml(s);
    const v = valueFor(s, S.utforskDay);
    $("#kortLukk", el).onclick = ()=>{ S.picked = null; Kart.setSelected(null); renderKort(); };
    $("#kortApne", el).onclick = ()=> Front.openSpot(s.id, v.idx >= 0 ? v.idx : null);
  }
  function renderListe(){
    const el = $("#utforskListe"); if(!el || !H().isDesktop()) return;
    const ids = S.utforskView==="alle" ? null : Kart.viewSpotIds(S.utforskView);
    const spots = DATA.spots.filter(s=> !ids || ids.has(s.id) || Kart.spotInfo(s.id).offMap).map(s=>({s, v: valueFor(s, S.utforskDay)}))
      .sort((a, b)=> b.v.st - a.v.st || ((b.v.h && b.v.h.surf_height)||0) - ((a.v.h && a.v.h.surf_height)||0) || a.s.name.localeCompare(b.s.name, "nb"));
    const dag = S.utforskDay==null ? "nå" : cap(fmtWdLong.format(new Date(S.utforskDay + "T11:00:00Z")));
    el.innerHTML = `<div class="kort"><h2 class="h2" style="margin-bottom:8px">Beste først</h2><p class="sub" style="margin:0 0 8px">${esc(dag)}</p><div class="alfa" role="list">${spots.map(({s, v})=>{ const hoyde = H().ordOgHoyde(v.h).hoyde;
      return `<a class="srad r-${Math.min(5, v.st)}" href="#spot=${esc(s.id)}${v.idx >= 0 ? "&t=" + v.idx : ""}" role="listitem" aria-label="${esc(v.aria)}"><span class="prikk${v.miss ? " miss" : ""}" aria-hidden="true"></span><span class="nm"><b>${esc(s.name)}</b><small>${esc(H().stedText(s))}</small></span><span class="na">${esc(v.word)}${hoyde ? `<span class="num">${esc(hoyde)} m</span>` : ""}</span></a>`; }).join("")}</div></div>`;
  }
  function render(state){
    S = state;
    if(!ensureInit()){ $("#utforskChips").innerHTML = `<span class="muted">Henter kartet …</span>`; return; }
    renderChips();
    Kart.setArea(area(), false);
    Kart.setView(S.utforskView, false);
    Kart.setSelected(S.picked);
    renderKort(); renderListe();
  }
  function thumb(){
    // Hjem på nett: kartet bygges (uten utsnitt) så snart kysten er hentet - første
    // tegning før den er her gir tomt kort, og Front.refresh() tegner på nytt etterpå
    if(!ensureInit()) return "";
    return Kart.thumb((p)=> valueFor(p.s, null).st);
  }
  window.addEventListener("resize", ()=>{ if(inited && S && S.view==="utforsk") Kart.setArea(area(), false); });
  window.Utforsk = { render, thumb, valueFor };
})();
