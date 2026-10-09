/* Nordsurf: kartmotoren (design «kart først», 09.10.2026 - se
   docs/design/kart-forst/ for Theodors godkjente skisse).

   Vektorkyst (docs/geo/coast.json, forenklet GSHHS for Nord-Norge) tegnet som
   SVG i ett lag som flyttes/zoomes med CSS-transform - kartet tegnes aldri på
   nytt under avspilling, bare merkenes farge/tekst, vindlagets retning/fart
   og nattlagets dekning endres. Merkene ligger i skjermrommet (absolutt
   posisjon, egen transition), så de kan være ekte knapper.

   Ren visning: leser bare feltene rating.py skrev til forecast.json. Treff/
   bom for svellkilen leses ALLTID fra h.directness (samme regel og samme
   grenser som skiva hadde, se fetcher/test_map_disc.py) - aldri fra
   bw_confirms eller spot_direction_factor. */
(function(){
  const VW = 1000, VH = 844;           // kartrommets størrelse (coast.json sin viewBox)
  const EASE = "cubic-bezier(.2,.8,.2,1)";
  const COL = { 0:"#617480", 1:"#EC6A43", 2:"#EFBA45", 3:"#47C88E", 4:"#2DC3D3", 5:"#9A88FF" };
  const WINDOW_COL = "#9FE3EE";
  const R_WEDGE = 64;                  // kilens radius i kartenheter
  const merc = (lat) => Math.log(Math.tan(Math.PI/4 + lat*Math.PI/360));

  let root, mapLayer, svg, gridG, wedgeG, windLayer, windSvg, night, markersEl;
  let coast = null, spots = [], proj = null;
  let state = { view:"nord", spotId:null, idx:0, area:{x:0,y:0,w:390,h:844}, sheetMode:"peek" };
  let cur = { cx:0, cy:0, sc:1 };
  let onPick = ()=>{};
  let hourOf = (spot, idx)=>spot.hours[idx];
  let labelOf = (h)=>"";
  let ariaOf = (spot, h)=>spot.name;
  let windLines = [];

  /* ---------- projeksjon ---------- */
  function makeProj(c){
    const [w0, s0, e0, n0] = c.bbox;
    const mN = merc(n0), mS = merc(s0);
    return {
      x: (lon)=> (lon - w0) / (e0 - w0) * c.vw,
      y: (lat)=> (mN - merc(lat)) / (mN - mS) * c.vh,
      bbox: c.bbox,
    };
  }
  function onMap(p){ return p.x >= 0 && p.x <= VW && p.y >= 0 && p.y <= VH; }

  /* ---------- oppsett ---------- */
  function init(el, data, coastJson, opts){
    root = el; coast = coastJson; proj = makeProj(coast);
    onPick = opts.onPick || onPick;
    hourOf = opts.hourOf || hourOf;
    labelOf = opts.labelOf || labelOf;
    ariaOf = opts.ariaOf || ariaOf;
    spots = data.spots.map(s=>{
      const lat = s.spot && s.spot.lat, lon = s.spot && s.spot.lon;
      const p = { s, id:s.id, name:s.name, area:s.area||"", x: lon!=null ? proj.x(lon) : -9999, y: lat!=null ? proj.y(lat) : -9999 };
      p.offMap = !(lat!=null && lon!=null && onMap(p));
      return p;
    });
    root.innerHTML = `
      <div class="map-layer" id="mapLayer">
        <svg id="mapSvg" width="${VW}" height="${VH}" viewBox="0 0 ${VW} ${VH}" aria-hidden="true" style="overflow:visible;display:block">
          <g class="grid" id="mapGrid"></g>
          <path class="coast-glow" d="${coast.d}"/>
          <path class="coast" d="${coast.d}"/>
          <g id="wedgeG"></g>
        </svg>
      </div>
      <div class="wind" id="windLayer" aria-hidden="true"><svg id="windSvg"></svg></div>
      <div class="night" id="nightLayer" aria-hidden="true"></div>
      <div class="markers" id="markersLayer"></div>`;
    mapLayer = root.querySelector("#mapLayer"); svg = root.querySelector("#mapSvg");
    gridG = root.querySelector("#mapGrid"); wedgeG = root.querySelector("#wedgeG");
    windLayer = root.querySelector("#windLayer"); windSvg = root.querySelector("#windSvg");
    night = root.querySelector("#nightLayer"); markersEl = root.querySelector("#markersLayer");
    drawGrid(); makeWind(); buildMarkers();
  }

  function drawGrid(){
    const [w0, s0, e0, n0] = proj.bbox;
    let out = "";
    for(let lat = Math.ceil(s0*2)/2; lat <= n0; lat += 0.5){ const y = proj.y(lat).toFixed(1); out += `<line x1="-600" y1="${y}" x2="1600" y2="${y}"/>`; }
    for(let lon = Math.ceil(w0); lon <= e0; lon += 1){ const x = proj.x(lon).toFixed(1); out += `<line x1="${x}" y1="-600" x2="${x}" y2="1500"/>`; }
    gridG.innerHTML = out;
  }

  /* ---------- vind: faste streker, retning/fart via CSS ---------- */
  function makeWind(){
    // Fast, gjentakbart mønster (samme hver gang), lagt i et stort lag som
    // roteres mot vindretningen. Strekene selv animeres bare med CSS
    // (translateX i det roterte rommet) - ingen JS per bilde.
    let seed = 11; const rnd = ()=>{ seed = (seed*9301 + 49297) % 233280; return seed/233280; };
    const n = 150, W = 2000, H = 2000;
    windLines = [];
    let out = "";
    for(let i=0;i<n;i++){
      const len = 16 + rnd()*36, x = rnd()*(W-60), y = rnd()*H;
      const w = (0.8 + rnd()*1.2).toFixed(2), a = (0.12 + rnd()*0.3).toFixed(2);
      out += `<line x1="${x.toFixed(0)}" y1="${y.toFixed(0)}" x2="${(x+len).toFixed(0)}" y2="${y.toFixed(0)}" style="stroke:rgba(214,238,244,${a});stroke-width:${w};animation-delay:-${(rnd()*6).toFixed(2)}s;animation-duration:calc(var(--wd) * ${(0.7+rnd()*0.7).toFixed(2)})"/>`;
    }
    windSvg.setAttribute("width", W); windSvg.setAttribute("height", H);
    windSvg.innerHTML = out;
  }
  function setWind(h){
    const ws = h && h.wind_speed!=null ? h.wind_speed : null;
    const wd = h && h.wind_dir!=null ? h.wind_dir : null;
    if(ws==null || wd==null){ windLayer.style.opacity = "0"; return; }
    const travel = (wd + 180) % 360;                       // "fra" -> dit vinden går
    const dur = Math.max(1.1, Math.min(6, 5.6 - ws*0.42)); // fart etter styrke
    const op = ws < 0.6 ? 0.18 : Math.min(0.95, 0.35 + ws*0.06);
    windLayer.style.setProperty("--wd", dur.toFixed(2)+"s");
    windLayer.style.opacity = op.toFixed(2);
    windLayer.style.transform = `rotate(${travel - 90}deg)`;
  }
  function setNight(h){
    const light = h ? (h.light || (h.daylight===false ? "mørkt" : "dag")) : "dag";
    night.style.opacity = light==="mørkt" ? ".42" : light==="skumring" ? ".2" : "0";
  }

  /* ---------- utsnitt ---------- */
  function fit(points, pad){
    // senter + skala som får alle punktene inn i synlig område, med luft
    const xs = points.map(p=>p.x), ys = points.map(p=>p.y);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const a = state.area;
    const w = Math.max(60, x1 - x0), hgt = Math.max(60, y1 - y0);
    const sc = Math.min((a.w - 2*pad) / w, (a.h - 2*pad) / hgt);
    return { cx: (x0+x1)/2, cy: (y0+y1)/2, sc: Math.max(0.3, Math.min(8, sc)) };
  }
  function viewFor(view){
    const on = spots.filter(p=>!p.offMap);
    const lof = on.filter(p=>/lofoten/i.test(p.area));
    const nord = on.filter(p=>!/lofoten/i.test(p.area));
    const padW = Math.min(120, state.area.w*0.18);
    if(view==="lofoten" && lof.length) return fit(lof, padW);
    if(view==="alle") return fit(on, padW);
    return fit(nord.length ? nord : on, padW);
  }
  function applyTransform(animate){
    const a = state.area;
    const ox = a.x + a.w/2, oy = a.y + a.h/2;
    mapLayer.style.transition = animate ? `transform 1s ${EASE}` : "none";
    mapLayer.style.transform = `translate(${(ox - cur.cx*cur.sc).toFixed(1)}px, ${(oy - cur.cy*cur.sc).toFixed(1)}px) scale(${cur.sc.toFixed(4)})`;
    placeMarkers(animate);
  }
  function setArea(area, animate){ state.area = area; recenter(animate); }
  function setView(view, animate){ state.view = view; recenter(animate); }
  function recenter(animate){
    const sel = state.spotId ? spots.find(p=>p.id===state.spotId) : null;
    if(sel && !sel.offMap && state.sheetMode==="spot"){
      cur = { cx: sel.x, cy: sel.y, sc: Math.min(6.4, Math.max(2.6, state.area.w/125)) };
    } else cur = viewFor(state.view);
    applyTransform(animate!==false);
  }

  /* ---------- merker ---------- */
  function buildMarkers(){
    markersEl.innerHTML = spots.map(p=>`
      <button type="button" class="mk" data-id="${p.id}" aria-label="">
        <span class="mk-dot-wrap"><span class="rip"></span><span class="rip rip2"></span><span class="mk-dot"></span></span>
        <span class="mk-pill"><span class="mk-name">${esc(p.name)}</span><span class="mk-label"></span></span>
      </button>
      <button type="button" class="mk-edge" data-id="${p.id}" aria-label="" hidden>
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" class="mk-arrow"><path d="M2 7h9M7.5 3.2 11.3 7 7.5 10.8"/></svg>
        <span class="mk-dot small"></span><span class="mk-name">${esc(p.name)}</span><span class="mk-label"></span>
      </button>`).join("");
    markersEl.querySelectorAll(".mk, .mk-edge").forEach(b=>b.onclick = ()=>onPick(b.dataset.id));
  }
  function placeMarkers(animate){
    const a = state.area;
    const ox = a.x + a.w/2, oy = a.y + a.h/2;
    const placed = [];
    spots.forEach(p=>{
      const mk = markersEl.querySelector(`.mk[data-id="${p.id}"]`);
      const ed = markersEl.querySelector(`.mk-edge[data-id="${p.id}"]`);
      const sx = ox + (p.x - cur.cx)*cur.sc, sy = oy + (p.y - cur.cy)*cur.sc;
      const inside = !p.offMap && sx >= a.x+12 && sx <= a.x+a.w-12 && sy >= a.y+12 && sy <= a.y+a.h-12;
      const hideAll = state.sheetMode==="list";
      mk.hidden = hideAll || !inside;
      mk.style.transition = animate ? `transform 1s ${EASE}` : "none";
      mk.style.transform = `translate3d(${sx.toFixed(1)}px, ${sy.toFixed(1)}px, 0)`;
      const showEdge = !hideAll && !inside && state.sheetMode!=="spot";
      ed.hidden = !showEdge;
      if(showEdge){
        // utenfor skjermen (eller utenfor kartet): pil i kanten som peker dit
        let ex = Math.max(a.x+70, Math.min(a.x+a.w-70, sx)), ey = Math.max(a.y+112, Math.min(a.y+a.h-40, sy));
        if(p.offMap){ ex = a.x+a.w-100; ey = a.y+a.h-44; }
        while(placed.some(q=>Math.abs(q.x-ex) < 150 && Math.abs(q.y-ey) < 38)) ey -= 40;
        placed.push({x:ex, y:ey});
        const ang = p.offMap ? 135 : Math.atan2(sy-ey, sx-ex)*180/Math.PI;
        ed.style.transition = animate ? `transform 1s ${EASE}` : "none";
        ed.style.transform = `translate3d(${ex.toFixed(1)}px, ${ey.toFixed(1)}px, 0) translate(-50%,-50%)`;
        ed.querySelector(".mk-arrow").style.transform = `rotate(${ang.toFixed(0)}deg)`;
      }
      // pille til venstre for spots nær høyre kant
      mk.classList.toggle("left", sx > a.x + a.w*0.62);
      mk._sx = sx; mk._sy = sy; mk._inside = inside && !hideAll;
    });
    // Piller som ville ligget oppå hverandre (spots som ligger tett, f.eks.
    // Grøtfjord/Tromvik) forskyves nedover, én linje om gangen - prikken
    // står alltid på spoten, bare pillen flyttes.
    const rects = [];
    [...markersEl.querySelectorAll(".mk")].filter(m=>m._inside).sort((m1,m2)=>m1._sy-m2._sy).forEach(mk=>{
      const w = 70 + mk.querySelector(".mk-name").textContent.length*7.5 + mk.querySelector(".mk-label").textContent.length*7;
      const left = mk.classList.contains("left") ? mk._sx - w : mk._sx;
      let dy = 0;
      const hit = ()=> rects.some(r=> left < r.x + r.w && left + w > r.x && mk._sy + dy < r.y + 30 && mk._sy + dy + 30 > r.y);
      while(hit() && dy < 150) dy += 30;
      rects.push({x:left, y:mk._sy + dy, w});
      mk.style.setProperty("--ly", dy ? dy+"px" : "0px");
    });
  }
  function colorMarkers(){
    const idx = state.idx;
    spots.forEach(p=>{
      const h = hourOf(p.s, idx);
      const st = h ? (h.stars||0) : 0;
      const col = COL[Math.min(5, st)];
      const label = h ? labelOf(h) : "–";
      const aria = h ? ariaOf(p.s, h) : p.name;
      const isSel = state.spotId===p.id;
      for(const el of [markersEl.querySelector(`.mk[data-id="${p.id}"]`), markersEl.querySelector(`.mk-edge[data-id="${p.id}"]`)]){
        el.className = (el.classList.contains("mk-edge") ? "mk-edge" : "mk") + ` r-${Math.min(5,st)}` + (st>=1 ? " lit" : "") + (isSel ? " sel" : "") + (el.classList.contains("left") ? " left" : "");
        el.style.setProperty("--mc", col);
        // roligere puls ved lang periode
        const per = h && h.period!=null ? h.period : 10;
        el.style.setProperty("--pulse", Math.max(1.8, Math.min(4.2, per*0.24)).toFixed(2)+"s");
        el.querySelector(".mk-label").textContent = label;
        el.setAttribute("aria-label", aria + (el.classList.contains("mk-edge") ? ", utenfor kartet" : ""));
      }
    });
  }

  /* ---------- svellkilen ved valgt spot ---------- */
  function pt(bearing, r){ const a = bearing*Math.PI/180; return [r*Math.sin(a), -r*Math.cos(a)]; }
  function segs(win){ return Array.isArray(win[0]) ? win : [win]; }
  function wedgePath(win, r){
    return segs(win).map(([a,b])=>{
      const span = (b - a + 360) % 360, p1 = pt(a, r), p2 = pt(b, r);
      return `M0,0L${p1[0].toFixed(1)},${p1[1].toFixed(1)}A${r},${r} 0 ${span>180?1:0} 1 ${p2[0].toFixed(1)},${p2[1].toFixed(1)}Z`;
    }).join("");
  }
  // Samme klassifisering som skiva hadde (test_map_disc.py leser disse
  // linjene): treff/bom KUN fra h.directness - aldri bw_confirms/
  // spot_direction_factor. Grensene speiler rating.SPOT_DIRECTION_OVERRIDE_EXPOSURE.
  function wedgeAriaLabel(h){
    const miss = h.directness!=null && h.directness < 0.667;
    return miss ? "svellet treffer ikke vinduet" : "svellet treffer vinduet";
  }
  function wedgeMarkup(p, h){
    const win = p.s.swell_window; if(!win) return "";
    const st = h ? (h.stars||0) : 0;
    const col = st>=1 ? COL[Math.min(5,st)] : WINDOW_COL;
    const missing = !h || h.dir_offshore==null;
    const dn = h.directness;
    const cls = missing || dn==null || dn < 0.667 ? "miss" : dn >= 0.999 ? "" : "edge";
    const per = h && h.period!=null ? h.period : 10;
    const dur = Math.max(1.8, Math.min(4.4, per*0.26));        // bølgefrontenes fart etter perioden
    const dir = missing ? 0 : h.dir_offshore;
    let swell = "";
    if(!missing && cls!=="miss"){
      const n = cls==="edge" ? 3 : 4;
      for(let i=0;i<n;i++) swell += `<path class="arc ${cls}" d="M-17,-60 Q0,-66 17,-60" style="stroke:${col};animation-duration:${dur.toFixed(2)}s;animation-delay:-${(dur*i/4).toFixed(2)}s"/>`;
    } else if(!missing){
      swell = `<line class="arc-miss" x1="0" y1="-64" x2="0" y2="-8"/>`;
    }
    // BarentsWatch sin egen retning ved punktet (tynn linje), som på skiva
    let spotSwellMarkup = "";
    if(h && h.bw_dir!=null){
      const noHit = h.spot_direction_factor===0;
      const q = pt(h.bw_dir, 44);
      spotSwellMarkup = `<line class="disc-spot-swell${noHit?" miss":""}" x1="${q[0].toFixed(2)}" y1="${q[1].toFixed(2)}" x2="0" y2="0"/>`;
    }
    return `<g class="wedge ${cls}" transform="translate(${p.x.toFixed(2)} ${p.y.toFixed(2)})" aria-label="${esc(wedgeAriaLabel(h||{}))}">
      <path class="wedge-fill" d="${wedgePath(win, R_WEDGE)}" style="fill:${cls==="miss"?WINDOW_COL:col};stroke:${cls==="miss"?WINDOW_COL:col}"/>
      ${spotSwellMarkup}
      <circle r="1.4" class="wedge-c"/>
      <g class="swell-rot" transform="rotate(${dir})">${swell}</g>
    </g>`;
  }
  function drawWedge(){
    const p = state.spotId ? spots.find(q=>q.id===state.spotId) : null;
    if(!p || p.offMap || state.sheetMode!=="spot"){ wedgeG.innerHTML = ""; return; }
    wedgeG.innerHTML = wedgeMarkup(p, hourOf(p.s, state.idx));
  }

  /* ---------- offentlig ---------- */
  function focusSpot(){
    const sel = state.spotId ? spots.find(p=>p.id===state.spotId) : null;
    if(sel) return sel;
    const on = spots.filter(p=>!p.offMap);
    return (state.view==="lofoten" ? on.find(p=>/lofoten/i.test(p.area)) : on.find(p=>!/lofoten/i.test(p.area))) || on[0] || spots[0];
  }
  function setHour(idx){
    state.idx = idx;
    const f = focusSpot(); const h = f ? hourOf(f.s, idx) : null;
    setWind(h); setNight(h); colorMarkers(); drawWedge();
  }
  function setSpot(id, mode, animate){
    state.spotId = id; state.sheetMode = mode;
    recenter(animate!==false); colorMarkers(); drawWedge(); setHour(state.idx);
  }
  function setMode(mode, animate){ state.sheetMode = mode; recenter(animate!==false); drawWedge(); }
  function esc(s){ return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
  function spotInfo(id){ return spots.find(p=>p.id===id) || null; }

  window.Kart = { init, setArea, setView, setHour, setSpot, setMode, spotInfo, COL, focusSpot };
})();
