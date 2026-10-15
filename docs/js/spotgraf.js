/* Nordsurf: langtidsvarselet på spotsiden - dagfaner (16 dager) og dagsgraf
   for valgt dag (Theodor 14.10.2026, punkt 4f/4g + HIG 5/6).

   Ren visning: ingen tall regnes - bare varselets timer. Grunnregelen:
   mangler en time (6-timers steg uten nærmeste time innen 4 timer), vises
   feltet stiplet, aldri 0. Samme høydeskala for alle dager på samme spot
   (største sets i varselet, minst 1,5 m), så dagene kan sammenlignes. */
(function(){
  const $ = (s, r)=> (r||document).querySelector(s);
  const $$ = (s, r)=> [...(r||document).querySelectorAll(s)];
  const fmtWd = new Intl.DateTimeFormat("nb-NO", {weekday:"short", timeZone:TZ});
  const fmtWdLong = new Intl.DateTimeFormat("nb-NO", {weekday:"long", timeZone:TZ});
  const fmtDato = new Intl.DateTimeFormat("nb-NO", {weekday:"long", day:"numeric", month:"long", timeZone:TZ});
  const fmtDayNum = new Intl.DateTimeFormat("nb-NO", {day:"numeric", timeZone:TZ});
  const fmtHM = new Intl.DateTimeFormat("nb-NO", {hour:"2-digit", minute:"2-digit", timeZone:TZ, hour12:false});
  const osloHour = (t)=> +fmtHour.format(t);   // klokketime i Europe/Oslo (sommertid slutter 25.10 - Intl ordner det)
  let H = null;

  function days(s){
    // dagene i varselet i rekkefølge, med timene som hører til hver dag (norsk tid)
    const by = new Map();
    s.hours.forEach((h, i)=>{ const k = H.dkOf(h.t); if(!by.has(k)) by.set(k, []); by.get(k).push(i); });
    const today = dayKey(new Date());
    return [...by.entries()].filter(([key])=> key >= today).map(([key, idxs])=>({key, idxs, step: idxs.length >= 20 ? 1 : 6}));
  }
  function dayOf(s, idx){ return H.dkOf(s.hours[idx].t); }
  function bestOfDay(s, d){
    // beste time i dagslys: flest stjerner, ved likt høyest surf_height; ellers kl. 12 (nærmeste), ellers første
    let best = null;
    for(const i of d.idxs){ const h = s.hours[i]; if(!H.usable(h) || !H.known(h)) continue; const c = {i, st: H.stars(h), hh: h.surf_height||0}; if(!best || c.st > best.st || (c.st===best.st && c.hh > best.hh)) best = c; }
    if(best) return best.i;
    let noon = d.idxs[0], bd = 99;
    for(const i of d.idxs){ const dd = Math.abs(osloHour(new Date(s.hours[i].t)) - 12); if(dd < bd){ bd = dd; noon = i; } }
    return noon;
  }
  function spanOfDay(s, d){
    // surfespennet i dagslys: laveste surf_height til høyeste sets (eller ordet hvis 0)
    let lo = null, hi = null, word = null, wst = -1;
    for(const i of d.idxs){ const h = s.hours[i]; if(!H.usable(h) || !H.known(h) || h.surf_height==null) continue;
      lo = lo==null ? h.surf_height : Math.min(lo, h.surf_height);
      const top = h.surf_height_sets!=null ? h.surf_height_sets : h.surf_height; hi = hi==null ? top : Math.max(hi, top);
      const st = H.stars(h); if(st > wst || (st===wst && word==null)){ wst = st; word = ratingWord(h); } }
    if(lo==null) return {txt: null, word: null};
    if(hi <= 0) return {txt: null, word};
    const a = nf1.format(lo), b = nf1.format(hi);
    return {txt: a===b ? `${a} m` : `${a}–${b} m`, word};
  }
  function slotBest(s, d, from, to){
    // beste stjerner i dagslys i timeintervallet [from, to); 6-timers dager: nærmeste time innen 4 timer
    const inSlot = d.idxs.filter(i=>{ const hh = osloHour(new Date(s.hours[i].t)); return hh >= from && hh < to; });
    let cand = inSlot;
    if(!cand.length && d.step===6){
      const mid = (from + to) / 2; let bi = -1, bd = 99;
      for(const i of d.idxs){ const dd = Math.abs(osloHour(new Date(s.hours[i].t)) - mid); if(dd < bd){ bd = dd; bi = i; } }
      cand = bd <= 4 ? [bi] : [];
    }
    let best = null, anyLight = false, anyKnown = false;
    for(const i of cand){ const h = s.hours[i]; if(!H.usable(h)) continue; anyLight = true; if(!H.known(h)) continue; anyKnown = true; const st = H.stars(h); if(best==null || st > best) best = st; }
    if(!cand.length) return {cls:"miss", st:null};
    if(!anyLight) return {cls:"dark", st:null};
    if(!anyKnown) return {cls:"miss", st:null};
    return {cls:`r-${Math.min(5,best)}`, st:best};
  }
  function nearestTo(s, d, hour){
    let bi = -1, bd = 99;
    for(const i of d.idxs){ const dd = Math.abs(osloHour(new Date(s.hours[i].t)) - hour); if(dd < bd){ bd = dd; bi = i; } }
    return bd <= 4 ? bi : -1;
  }
  const ARROW = (deg, cls)=> deg==null ? "" : `<svg class="${cls||""}" viewBox="0 0 16 16" aria-hidden="true" style="transform:rotate(${(((deg + 180) % 360)).toFixed(0)}deg)"><path d="M8 2 12 13 8 10 4 13z" fill="currentColor"/></svg>`;   // peker dit det går (fra + 180)

  function tabsHtml(s, selIdx){
    const selKey = dayOf(s, selIdx); const today = dayKey(new Date());
    return `<div class="dagfaner" role="tablist" aria-label="Dager">${days(s).map((d, k)=>{
      const t = new Date(s.hours[d.idxs[0]].t); const span = spanOfDay(s, d);
      const felt = [[6,10],[10,14],[14,19]].map(([a,b])=>{ const r = slotBest(s, d, a, b); return `<i class="${r.cls}" title="${a}–${b}: ${r.st!=null ? r.st + " stjerner" : r.cls==="dark" ? "mørkt" : "mangler"}"></i>`; }).join("");
      const noon = nearestTo(s, d, 12); const hn = noon >= 0 ? s.hours[noon] : null;
      const usikker = d.idxs.every(i=> s.hours[i].zone==="langtid");
      const wordCls = (()=>{ const i = bestOfDay(s, d); return `r-${Math.min(5, H.stars(s.hours[i]))}`; })();
      const navn = d.key===today ? "I dag" : k===1 && d.key===dayKey(new Date(Date.now()+864e5)) ? "I morgen" : cap(fmtWd.format(t).replace(/\.$/, ""));
      const aria = `${cap(fmtDato.format(t))}: ${span.txt || span.word || "–"}${usikker ? ", usikker (langtidsmodell)" : ""}`;
      return `<button type="button" class="dagfane${usikker ? " usikker" : ""}" role="tab" data-day="${d.key}" aria-pressed="${d.key===selKey}" aria-selected="${d.key===selKey}" aria-label="${esc(aria)}">
        <span class="d"><span>${esc(navn)}</span><small>${fmtDayNum.format(t)}.</small></span>
        <span class="h">${span.txt ? esc(span.txt).replace(" m", "<small>m</small>") : (span.word ? "–" : "–")}</span>
        <span class="o ${wordCls}">${esc(span.word || "–")}</span>
        <span class="felt" aria-hidden="true">${felt}</span>
        <span class="piler" aria-hidden="true">${hn && hn.dir_offshore!=null ? ARROW(hn.dir_offshore) : ""}${hn && hn.wind_dir!=null ? ARROW(hn.wind_dir) : ""}${usikker ? `<span class="us">Usikker</span>` : ""}</span></button>`; }).join("")}</div>`;
  }

  function grafHtml(s, selIdx){
    const key = dayOf(s, selIdx); const d = days(s).find(x=>x.key===key) || days(s)[0]; if(!d) return "";
    const t0 = new Date(s.hours[d.idxs[0]].t);
    // kolonner: 24 timer (timer som har vært i dag står tomme) eller 4 ved 6-timers steg
    const cols = d.step===1 ? Array.from({length:24}, (_, hh)=>({hh, i: d.idxs.find(i=> osloHour(new Date(s.hours[i].t))===hh) ?? -1})) : d.idxs.map(i=>({hh: osloHour(new Date(s.hours[i].t)), i}));
    const scaleMax = Math.max(1.5, ...s.hours.map(h=> Math.max(h.surf_height_sets||0, h.surf_height||0)));
    const bestI = bestOfDay(s, d); const bh = s.hours[bestI];
    const topTxt = H.usable(bh) && H.known(bh) && H.stars(bh) >= 1
      ? `Best kl. ${fmtHour.format(new Date(bh.t))}: <b class="r-${Math.min(5,H.stars(bh))}">${esc(ratingWord(bh))}</b>${H.heightText(bh) ? `, ${esc(H.heightText(bh))} m` : ""}`
      : `Ingen surfbare timer${bh && ratingWord(bh) ? ` · ${esc(ratingWord(bh).toLowerCase())}` : ""}`;
    const n = cols.length; const H_PX = 120;
    const kol = cols.map(c=>{
      const h = c.i >= 0 ? s.hours[c.i] : null; const st = H.stars(h); const known = H.known(h);
      const l = h ? (h.light || null) : null; const natt = l==="mørkt" ? " natt" : l==="skumring" ? " skum" : "";
      const hs = h && h.surf_height!=null ? h.surf_height : 0, sets = h && h.surf_height_sets!=null ? Math.max(0, h.surf_height_sets - hs) : 0;
      const bar = !h ? "" : !known ? `<span class="b miss" style="height:3px"></span>`
        : `<span class="b r-${Math.min(5,st)}" style="height:${Math.max(hs>0?3:2, hs/scaleMax*H_PX).toFixed(1)}px">${sets>0 ? `<span class="sets" style="height:${(sets/scaleMax*H_PX).toFixed(1)}px"></span>` : ""}${c.i===selIdx || (c.i===bestI && hs>0) ? `<span class="tall">${nf1.format(h.surf_height_sets!=null ? h.surf_height_sets : hs)}</span>` : ""}</span>`;
      const rs = !h ? `<span class="rs tom"></span>` : !known ? `<span class="rs miss" title="mangler"></span>` : `<span class="rs r-${Math.min(5,st)}" aria-hidden="true">${st||""}</span>`;
      const aria = h ? `${fmtHour.format(new Date(h.t))}:00, ${known ? (st ? STR.starsAria(st, h.faded||0) + ", " : "") + ratingWord(h) + (H.heightText(h) ? ", " + H.heightText(h) + " m" : "") : "tallet mangler"}` : `${String(c.hh).padStart(2,"0")}:00, har vært`;
      return `<div class="kol${natt}${c.i===selIdx ? " valgt" : ""}${!h ? " tom" : ""}" data-i="${c.i}" data-hh="${c.hh}">${rs}<button type="button" class="soyle" data-i="${c.i}" aria-label="${esc(aria)}"${!h ? " disabled" : ""}${c.i===selIdx ? ' aria-pressed="true"' : ""}>${bar}</button></div>`; }).join("");
    const axis = cols.map(c=>`<span>${d.step===1 ? (c.hh % 3===0 ? String(c.hh).padStart(2,"0") : "") : String(c.hh).padStart(2,"0")}</span>`).join("");
    const every3 = cols.filter((c, k)=> d.step===6 || c.hh % 3===0);
    const vind = every3.map(c=>{ const h = c.i>=0 ? s.hours[c.i] : null; return `<div style="grid-column:span ${d.step===1 ? 3 : 1}">${h && h.wind_speed!=null ? `${ARROW(h.wind_dir)}<span class="b">${nf0.format(h.wind_speed)}</span>` : "<small>–</small>"}</div>`; }).join("");
    const svell = every3.map(c=>{ const h = c.i>=0 ? s.hours[c.i] : null; return `<div style="grid-column:span ${d.step===1 ? 3 : 1}">${h && h.swell_offshore!=null ? `${ARROW(h.dir_offshore)}<span class="b">${nf1.format(h.swell_offshore)}</span><small>${h.period!=null ? nf0.format(h.period) + "s" : "–"}</small>` : "<small>–</small>"}</div>`; }).join("");
    const tide = (s.tide_events||[]).length ? Spot.tideSvg(s.tide_events, new Date(s.hours[selIdx].t), true) : "";
    return `<div class="kort graf" id="graf" data-day="${key}" data-n="${n}">
      <div class="graf-topp"><h3>${esc(cap(fmtDato.format(t0)))}</h3><span class="best">${topTxt}</span></div>
      <div class="plot" style="grid-template-columns:repeat(${n},minmax(0,1fr))">${kol}</div>
      <div class="akse" style="grid-template-columns:repeat(${n},minmax(0,1fr))">${axis}</div>
      <div class="grafrad"><div class="k">Vind <small>m/s</small></div><div class="celler" style="grid-template-columns:repeat(${n},minmax(0,1fr))">${vind}</div></div>
      <div class="grafrad"><div class="k">Svell ute <small>m og s</small></div><div class="celler" style="grid-template-columns:repeat(${n},minmax(0,1fr))">${svell}</div></div>
      ${tide ? `<div class="grafrad"><div class="k">Tidevann</div>${tide}</div>` : ""}
    </div>`;
  }
  function html(s, selIdx, helpers){ H = helpers; return tabsHtml(s, selIdx) + grafHtml(s, selIdx); }

  function wire(root, s, S, helpers, onPick){
    H = helpers;
    $$(".dagfane", root).forEach(b=> b.onclick = ()=>{ const d = days(s).find(x=>x.key===b.dataset.day); if(d) onPick(bestOfDay(s, d), true); });
    const plot = $(".plot", root); if(!plot) return;
    $$(".soyle", plot).forEach(b=> b.onclick = ()=>{ const i = +b.dataset.i; if(i >= 0) onPick(i, false); });
    // hele plottområdet tar imot pointerdown/move og velger nærmeste time (touch-action: pan-y)
    let down = false;
    const pick = (x)=>{ const cols = $$(".kol", plot); const r = plot.getBoundingClientRect(); const k = Math.max(0, Math.min(cols.length-1, Math.floor((x - r.left) / (r.width / cols.length)))); const i = +cols[k].dataset.i; if(i >= 0 && i !== S.idx) onPick(i, false); };
    plot.addEventListener("pointerdown", (e)=>{ if(e.pointerType==="mouse" && e.button!==0) return; down = true; pick(e.clientX); });
    plot.addEventListener("pointermove", (e)=>{ if(down) pick(e.clientX); });
    const up = ()=>{ down = false; };
    plot.addEventListener("pointerup", up); plot.addEventListener("pointercancel", up); plot.addEventListener("pointerleave", up);
    const sel = $(".dagfane[aria-pressed='true']", root); if(sel && sel.scrollIntoView) sel.scrollIntoView({block:"nearest", inline:"center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"});
  }
  window.SpotGraf = { html, wire, days, bestOfDay, spanOfDay, slotBest };
})();
