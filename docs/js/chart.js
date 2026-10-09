/* Nordsurf: grafen på detaljsiden (designrunde 1, punkt 4). Søyler per
   time: høyden er surfehøyde, fargen er rating (ratingskalaen i app.css),
   en tynn strek over søylen er settene. Flate timer får en lav grå strek,
   så dagen har en form. Bakgrunnen viser dag, skumring og mørke. Skillet
   der BarentsWatch slutter og der langtid begynner tegnes diskret. Trykk
   eller hold på en søyle viser verdiene (på PC: hover), piltaster flytter.

   Ren visning: leser bare feltene rating.py skrev til forecast.json.
   Vanlig <script>, ikke modul - app.js kaller Chart.render(). */
(function(){
  const COL = 26;          // bredde per time (px)
  const PAD_L = 8, PAD_R = 8, TOP = 30, H = 150, BOTTOM = 22;
  const MAX_H = 3.5;        // meter som fyller hele høyden (over dette klippes søylen)
  const FLAT_PX = 3;

  function dayKey(d, tz){ return new Intl.DateTimeFormat("sv-SE",{timeZone:tz}).format(d); }

  function build(spot, sel, opts){
    const tz = opts.tz, fmtHour = opts.fmtHour, relDay = opts.relDay, nf1 = opts.nf1;
    const hours = spot.hours;
    const n = hours.length;
    const width = PAD_L + n*COL + PAD_R;
    const total = TOP + H + BOTTOM;
    const bw = spot.bw_until;
    let bands = "", bars = "", labels = "", breaks = "", selMark = "";
    let lastDay = null, dayStartX = 0;
    const y0 = TOP + H;
    const scale = (m) => Math.min(H, (m/MAX_H)*H);
    hours.forEach((h, i)=>{
      const x = PAD_L + i*COL;
      const t = new Date(h.t);
      const k = dayKey(t, tz);
      const light = h.light || (h.daylight===false ? "mørkt" : "dag");
      const cls = light==="mørkt" ? "dark" : light==="skumring" ? "dusk" : "";
      bands += `<rect class="band ${cls}" x="${x}" y="${TOP-4}" width="${COL}" height="${H+4}"/>`;
      if(k!==lastDay){
        lastDay = k;
        labels += `<text class="day-lbl" x="${x+4}" y="14">${esc(cap(relDay(t)))}</text>`;
        if(i>0) breaks += `<line class="brk" x1="${x}" y1="${TOP-4}" x2="${x}" y2="${y0}"/>`;
      }
      // timetall hver tredje time
      const hourNum = +fmtHour.format(t).replace(/^0/,"");
      if(hourNum % 6 === 0) labels += `<text class="hour-lbl" x="${x+COL/2}" y="${y0+16}" text-anchor="middle">${hourNum}</text>`;
      const isReserve = !!(bw && h.t > bw) || h.zone==="reserve" || h.zone==="langtid";
      const isLang = h.zone==="langtid";
      if(bw && i>0 && hours[i-1].t <= bw && h.t > bw){
        breaks += `<line class="brk" x1="${x}" y1="${TOP-4}" x2="${x}" y2="${y0}"/><text class="brk-lbl" x="${x+3}" y="${TOP+8}">anslag</text>`;
      }
      if(isLang && (i===0 || hours[i-1].zone!=="langtid")){
        breaks += `<line class="brk" x1="${x}" y1="${TOP-4}" x2="${x}" y2="${y0}"/><text class="brk-lbl" x="${x+3}" y="${TOP+8}">langtid</text>`;
      }
      const stars = h.stars||0;
      // Søylehøyden er ALLTID det samme tallet som teksten viser
      // (opts.heightOf = heightMForDisplay i app.js: surfehøyden, eller
      // BarentsWatch sin totalhøyde ved blåst ut/stormsjø), fargen er
      // ALLTID ratingen (r-0 grå ved 0 stjerner, også når høyden er reell).
      // Grå lav strek bare når høyden faktisk er 0/ikke beregnet (flatt,
      // treffer ikke). Mangler tallet helt (null): INGEN søyle, bare en
      // stiplet "mangler"-markør - aldri en strek som ser ut som "flatt"
      // (grunnregelen i CLAUDE.md; fysikk-kontrollør 09.10.2026).
      const m = opts.heightOf ? opts.heightOf(h) : h.surf_height;
      const missing = m==null && !h.low_reason;
      const flat = !missing && (m==null || m<=0);
      const hpx = missing ? 0 : flat ? FLAT_PX : Math.max(4, scale(m));
      const bx = x+5, bwid = COL-10;
      const zone = isLang ? " langtid" : (isReserve ? " reserve" : "");
      const title = opts.barTitle ? `<title>${esc(opts.barTitle(h))}</title>` : "";
      // hit-flate først (bak), så søyle (så :hover + .bar virker)
      bars += `<rect class="hit" x="${x}" y="${TOP-4}" width="${COL}" height="${H+4}" data-i="${i}" tabindex="-1">${title}</rect>`;
      if(missing) bars += `<line class="miss" x1="${bx}" y1="${y0-1}" x2="${bx+bwid}" y2="${y0-1}"/>`;
      else bars += `<rect class="bar r-${stars}${flat?" flat":""}${zone}" x="${bx}" y="${y0-hpx}" width="${bwid}" height="${hpx}" rx="2"/>`;
      if(!missing && !flat && h.surf_height_sets!=null && h.surf_height_sets>m){
        const sy = y0 - Math.min(H, scale(h.surf_height_sets));
        bars += `<line class="set r-${stars}" x1="${bx}" y1="${sy}" x2="${bx+bwid}" y2="${sy}"/>`;
      }
      if(i===sel){
        selMark = `<rect class="sel-mark" x="${x+1.5}" y="${TOP-2}" width="${COL-3}" height="${H+1}"/><circle class="sel-top" cx="${x+COL/2}" cy="${TOP-9}" r="3"/>`;
      }
    });
    const svg = `<svg class="chart" width="${width}" height="${total}" viewBox="0 0 ${width} ${total}" role="img" aria-label="${esc(opts.aria)}">
      <g>${bands}</g><g>${breaks}</g><g>${bars}</g><g>${selMark}</g><g>${labels}</g></svg>`;
    return {svg, width, colX: (i)=>PAD_L + i*COL + COL/2};
  }

  function esc(s){ return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
  function cap(s){ return s.charAt(0).toUpperCase()+s.slice(1); }

  /* Tegner inn i container (.chart-wrap med .chart-scroll inni), kobler
     trykk/hover/tastatur. onSelect(i) kalles når brukeren velger en time. */
  function render(container, spot, sel, opts, onSelect, tipHtml){
    const built = build(spot, sel, opts);
    const scroll = container.querySelector(".chart-scroll");
    const keepX = scroll ? scroll.scrollLeft : null;
    scroll.innerHTML = built.svg;
    let tip = container.querySelector(".chart-tip");
    if(!tip){ tip = document.createElement("div"); tip.className="chart-tip"; tip.hidden = true; container.appendChild(tip); }
    const svg = scroll.querySelector("svg");
    const hits = svg.querySelectorAll(".hit");
    const showTip = (i, el)=>{
      const h = spot.hours[i];
      tip.innerHTML = tipHtml(h);
      tip.hidden = false;
      const r = el.getBoundingClientRect(), c = container.getBoundingClientRect();
      const left = Math.max(70, Math.min(c.width-70, r.left - c.left + r.width/2));
      tip.style.left = left+"px"; tip.style.top = (r.top - c.top + 4)+"px";
    };
    const hideTip = ()=>{ tip.hidden = true; };
    hits.forEach(el=>{
      const i = +el.dataset.i;
      el.addEventListener("click", ()=>{ onSelect(i); });
      el.addEventListener("mouseenter", ()=>showTip(i, el));
      el.addEventListener("mouseleave", hideTip);
      el.addEventListener("touchstart", ()=>showTip(i, el), {passive:true});
      el.addEventListener("touchend", ()=>setTimeout(hideTip, 1200), {passive:true});
    });
    svg.tabIndex = 0;
    svg.addEventListener("keydown", (ev)=>{
      if(ev.key==="ArrowRight" || ev.key==="ArrowLeft"){
        ev.preventDefault();
        const next = Math.max(0, Math.min(spot.hours.length-1, sel + (ev.key==="ArrowRight"?1:-1)));
        if(next!==sel) onSelect(next, true);
      }
    });
    if(keepX!=null && !opts.scrollToSel) scroll.scrollLeft = keepX;
    if(opts.scrollToSel){
      const target = built.colX(sel) - scroll.clientWidth/2;
      scroll.scrollLeft = Math.max(0, target);
    }
    if(opts.focus) svg.focus({preventScroll:true});
    return built;
  }

  window.Chart = {render, COL};
})();
