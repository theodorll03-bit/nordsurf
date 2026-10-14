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
   bw_confirms eller spot_direction_factor.

   Rolig kart (Theodor 13.10.2026): lapp bare for spots med stjerner,
   favoritter og valgt spot - 0 stjerner er en liten grå prikk. Ingen streker
   fra prikk til lapp. Kantpiler bare for favoritter og spots med stjerner.
   Vindlaget bare når en spot er valgt. Er alle spots i utsnittet 0 stjerner,
   står én diskret tekst på kartet (teksten lages i front.js). */
(function(){
  const VW = 1000, VH = 844;           // kartrommets størrelse (coast.json sin viewBox)
  const EASE = "cubic-bezier(.2,.8,.2,1)";
  const COL = { 0:"#617480", 1:"#EC6A43", 2:"#EFBA45", 3:"#47C88E", 4:"#2DC3D3", 5:"#9A88FF" };
  const WINDOW_COL = "#9FE3EE";
  const R_WEDGE = 64;                  // kilens radius i kartenheter
  const merc = (lat) => Math.log(Math.tan(Math.PI/4 + lat*Math.PI/360));

  let root, mapLayer, svg, gridG, wedgeG, windLayer, windSvg, night, markersEl, noteEl;
  let coast = null, spots = [], proj = null;
  let state = { view:"nord", spotId:null, idx:0, area:{x:0,y:0,w:390,h:844}, sheetMode:"peek" };
  let cur = { cx:0, cy:0, sc:1 };
  let onPick = ()=>{};
  let onCluster = ()=>{};
  let clusters = [];   // klyngepiler («N spots») - farges på nytt ved hvert timebytte
  let crisp = false;   // true når kartet står stille og SVG-en er tegnet skarpt via viewBox
  let hourOf = (spot, idx)=>spot.hours[idx];
  let labelOf = (h)=>"";
  let ariaOf = (spot, h)=>spot.name;
  let isFav = (id)=>false;
  let noteOf = ()=>null;
  let lastOuts = [];   // spots utenfor skjermen ved siste plassering - kantpilene velges på nytt ved hvert timebytte
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
    onCluster = opts.onCluster || onCluster;
    hourOf = opts.hourOf || hourOf;
    labelOf = opts.labelOf || labelOf;
    ariaOf = opts.ariaOf || ariaOf;
    isFav = opts.isFav || isFav;
    noteOf = opts.noteOf || noteOf;
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
      <div class="markers" id="markersLayer"></div>
      <p class="map-note" id="mapNote" hidden></p>`;
    mapLayer = root.querySelector("#mapLayer"); svg = root.querySelector("#mapSvg");
    gridG = root.querySelector("#mapGrid"); wedgeG = root.querySelector("#wedgeG");
    windLayer = root.querySelector("#windLayer"); windSvg = root.querySelector("#windSvg");
    night = root.querySelector("#nightLayer"); markersEl = root.querySelector("#markersLayer");
    noteEl = root.querySelector("#mapNote");
    drawGrid(); makeWind(); buildMarkers();
    // Etter at zoom-animasjonen er ferdig: tegn kartet skarpt på nytt (viewBox
    // i stedet for CSS-skalering - Theodors punkt 5, 09.10.2026).
    mapLayer.addEventListener("transitionend", (e)=>{ if(e.target===mapLayer && e.propertyName==="transform") crispen(); });
  }
  function hexMix(a, b, t){
    const pa = [1,3,5].map(i=>parseInt(a.slice(i,i+2),16)), pb = [1,3,5].map(i=>parseInt(b.slice(i,i+2),16));
    return "#" + pa.map((v,i)=>Math.round(v + (pb[i]-v)*t).toString(16).padStart(2,"0")).join("");
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
  let windAngle = null;  // akkumulert vinkel, så overgangen alltid tar korteste vei (ingen nesten-hel runde ved 0/360)
  function setWind(h){
    const ws = h && h.wind_speed!=null ? h.wind_speed : null;
    const wd = h && h.wind_dir!=null ? h.wind_dir : null;
    if(ws==null || wd==null){ windLayer.style.opacity = "0"; return; }
    const travel = (wd + 180) % 360;                       // "fra" -> dit vinden går
    const target = travel - 90;
    if(windAngle==null) windAngle = target;
    else { let d = ((target - windAngle) % 360 + 540) % 360 - 180; windAngle += d; }
    const dur = Math.max(1.1, Math.min(6, 5.6 - ws*0.42)); // fart etter styrke
    const op = ws < 0.6 ? 0.18 : Math.min(0.95, 0.35 + ws*0.06);
    windLayer.style.setProperty("--wd", dur.toFixed(2)+"s");
    windLayer.style.opacity = op.toFixed(2);
    windLayer.style.transform = `rotate(${windAngle.toFixed(1)}deg)`;
  }
  function lightOf(h){
    // ukjent lys er ukjent (null) - aldri "dag" (grunnregelen: mangler er ikke et svar)
    if(!h) return null;
    if(h.light) return h.light;
    if(h.daylight===false) return "mørkt";
    if(h.daylight===true) return "dag";
    return null;
  }
  function setNight(h){
    const light = lightOf(h);
    const o = light==="mørkt" ? 0.42 : light==="skumring" ? 0.2 : 0;
    night.style.opacity = String(o);
    // nattlaget mørkner alt likt - løft landet tilsvarende, så det alltid
    // ligger tydelig lysere enn havet (skissen: land #15252E, hav #0A1822)
    const coastPath = svg.querySelector(".coast");
    coastPath.style.fill = hexMix("#15252E", "#2E4A59", o);
    coastPath.style.stroke = hexMix("#3B5866", "#5E8597", o);
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
  // Spotene et utsnitt viser (og rammer inn). Samme sett brukes av svarlinja
  // og teksten på kartet i front.js («området i utsnittet»).
  function viewPoints(view){
    const on = spots.filter(p=>!p.offMap);
    const lof = on.filter(p=>/lofoten/i.test(p.area));
    const nord = on.filter(p=>!/lofoten/i.test(p.area));
    if(view==="lofoten" && lof.length) return lof;
    if(view==="alle") return on;
    return nord.length ? nord : on;
  }
  function viewSpotIds(view){ return new Set(viewPoints(view).map(p=>p.id)); }
  function viewFor(view){
    const padW = Math.min(120, state.area.w*0.18);
    return fit(viewPoints(view), padW);
  }
  let prevT = null;  // forrige CSS-transform (translate/scale) - utgangspunkt for neste animasjon
  function cssTransform(){
    const a = state.area, ox = a.x + a.w/2, oy = a.y + a.h/2;
    return { tx: ox - cur.cx*cur.sc, ty: oy - cur.cy*cur.sc, sc: cur.sc };
  }
  function uncrispen(){
    // tilbake til CSS-transform-modus (full 1000×844-SVG) uten overgang
    if(!crisp) return;
    crisp = false;
    svg.setAttribute("viewBox", `0 0 ${VW} ${VH}`); svg.setAttribute("width", VW); svg.setAttribute("height", VH);
    mapLayer.style.width = VW+"px"; mapLayer.style.height = VH+"px";
    mapLayer.style.transition = "none";
    const t = prevT || cssTransform();
    mapLayer.style.transform = `translate(${t.tx.toFixed(1)}px, ${t.ty.toFixed(1)}px) scale(${t.sc.toFixed(4)})`;
    void mapLayer.offsetWidth;  // tving ny layout før overgangen settes
  }
  function crispen(){
    // skarp tegning: SVG-en dekker hele scenen 1:1, utsnittet ligger i viewBox
    const t = cssTransform();
    const W = root.clientWidth || window.innerWidth, H = root.clientHeight || window.innerHeight;
    crisp = true;
    mapLayer.style.transition = "none";
    mapLayer.style.transform = "none";
    mapLayer.style.width = W+"px"; mapLayer.style.height = H+"px";
    svg.setAttribute("width", W); svg.setAttribute("height", H);
    svg.setAttribute("viewBox", `${(-t.tx/t.sc).toFixed(3)} ${(-t.ty/t.sc).toFixed(3)} ${(W/t.sc).toFixed(3)} ${(H/t.sc).toFixed(3)}`);
  }
  const reduced = ()=> matchMedia("(prefers-reduced-motion: reduce)").matches;
  function applyTransform(animate){
    const t = cssTransform();
    const same = prevT && Math.abs(prevT.tx-t.tx) < 0.5 && Math.abs(prevT.ty-t.ty) < 0.5 && Math.abs(prevT.sc-t.sc) < 1e-4;
    if(animate && !reduced() && !same){
      uncrispen();
      mapLayer.style.transition = `transform 1s ${EASE}`;
      mapLayer.style.transform = `translate(${t.tx.toFixed(1)}px, ${t.ty.toFixed(1)}px) scale(${t.sc.toFixed(4)})`;
    } else {
      prevT = t; crispen();
    }
    prevT = t;
    placeMarkers(animate && !reduced());
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
      <button type="button" class="mk bare" data-id="${p.id}" aria-label="">
        <span class="mk-dot-wrap"><span class="rip"></span><span class="rip rip2"></span><span class="mk-dot"></span></span>
        <span class="mk-pill"><span class="mk-name">${esc(p.name)}</span><span class="mk-label"></span></span>
      </button>
      <button type="button" class="mk-edge" data-id="${p.id}" aria-label="" hidden>
        <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" class="mk-arrow"><path d="M2 7h9M7.5 3.2 11.3 7 7.5 10.8"/></svg>
        <span class="mk-dot small"></span><span class="mk-name">${esc(p.name)}</span><span class="mk-label"></span>
      </button>`).join("");
    markersEl.querySelectorAll(".mk, .mk-edge").forEach(b=>b.onclick = ()=>onPick(b.dataset.id));
  }
  const PH = 30, GAP = 15;     // pillens høyde, avstand prikksentrum -> pillekant (prikk 5,5 + luft)
  function pillWidth(mk){ return 30 + mk.querySelector(".mk-name").textContent.length*7.4 + mk.querySelector(".mk-label").textContent.length*7.2; }
  // Tall i Geist Mono, navn og ord i Geist (Theodor 13.10.2026): bare sifrene pakkes inn.
  function labelHtml(t){ return esc(t).replace(/\d[\d,.–]*/g, m=>`<span class="num">${m}</span>`); }
  function obstacles(){
    // områder kantpiler aldri skal ligge i: topplinjas knapper/regionvalg/tidspille, fargeforklaringen og teksten på kartet
    const out = [];
    document.querySelectorAll(".top-bar .icon-btn, .top-bar .seg, .top-bar .brand, .top-bar .tctl, .legend, .map-note").forEach(el=>{
      const r = el.getBoundingClientRect(); if(r.width && r.height && !el.hidden && getComputedStyle(el).display!=="none") out.push({x:r.left-8, y:r.top-8, w:r.width+16, h:r.height+16});
    });
    return out;
  }
  const prio = (mk)=> (mk._sel ? 1000 : 0) + (mk._fav ? 100 : 0) + (mk._st || 0);
  const hitRect = (r, list)=> list.some(q=> r.x < q.x+q.w && r.x+r.w > q.x && r.y < q.y+q.h && r.y+r.h > q.y);
  function layoutPills(){
    // Lapp bare for spots som skal ha det (_wantLabel: stjerner, favoritt
    // eller valgt - Theodor 13.10.2026 - og «–» når tallet mangler, så det
    // aldri ser ut som en kjent 0); de andre er en prikk uten lapp
    // (klassen «bare»). Lappen står rett ved prikken: høyre eller venstre
    // side, litt opp/ned (høyst 24 px), eller rett over/under prikken - alltid
    // under 12 px unna, og aldri med strek. Et lite søk finner en plassering
    // uten konflikt for alle lappene samlet (alle prikker i utsnittet er
    // hindre, og hver lapp skal ligge nærmere sin egen prikk enn noen annen).
    // Går det ikke (svært tette prikker, f.eks. «Alle» på mobil), får de
    // viktigste lapp (valgt, favoritt, flest stjerner) og resten står som
    // prikk uten lapp - lista har dem uansett.
    const a = state.area;
    const inside = [...markersEl.querySelectorAll(".mk")].filter(m=>m._inside);
    inside.forEach(m=>{ m.classList.toggle("bare", !m._wantLabel); m.dataset.label = m._wantLabel ? "shown" : "rule"; });
    const mks = inside.filter(m=>m._wantLabel).sort((x, y)=> prio(y) - prio(x));
    const dots = inside.map(m=>({id: m.dataset.id, x: m._sx-6, y: m._sy-6, w: 12, h: 12}));
    // Avstand fra et punkt (en prikk) til nærmeste kant av et rektangel (en lapp)
    const distRP = (r, x, y)=> Math.hypot(Math.max(r.x - x, 0, x - (r.x + r.w)), Math.max(r.y - y, 0, y - (r.y + r.h)));
    const cands = mks.map(mk=>{
      const w = pillWidth(mk);
      let preferLeft = mk._sx > a.x + a.w*0.62;
      // Prikker som ligger tett (Grøtfjord/Tromvik, Theodor 09.10.2026): den
      // vestligste får lappen på venstre side, den østligste på høyre - lappen
      // peker bort fra naboen.
      const near = dots.filter(d=> d.id!==mk.dataset.id && Math.abs(d.y + 6 - mk._sy) < PH + 12 && Math.abs(d.x + 6 - mk._sx) < w + 2*GAP + 12);
      if(near.length){
        const east = near.some(d=>d.x + 6 > mk._sx), west = near.some(d=>d.x + 6 < mk._sx);
        if(east && !west) preferLeft = true; else if(west && !east) preferLeft = false;
      }
      const sides = preferLeft ? ["left","right"] : ["right","left"];
      const out = [];
      for(const dy of [0, -14, 14, -24, 24]) for(const side of sides){
        const x = side==="right" ? mk._sx + GAP : mk._sx - GAP - w;
        if(x < a.x + 4 || x + w > a.x + a.w - 4) continue;
        out.push({side, dy, r:{x, y: mk._sy - PH/2 + dy, w, h: PH}});
      }
      // Rett over eller under prikken, midtstilt (to prikker helt inntil
      // hverandre ved kartkanten, f.eks. Steinkrøssa/Ersfjordstranda).
      for(const dy of [-(PH/2 + 12), PH/2 + 12]){
        const x = Math.max(a.x + 4, Math.min(a.x + a.w - 4 - w, mk._sx - w/2));
        out.push({side:"vert", dy, vert:true, r:{x, y: mk._sy - PH/2 + dy, w, h: PH}});
      }
      return out;
    });
    const chosen = new Array(mks.length).fill(null);
    let nodes = 0;
    const ok = (i, c)=>{
      const others = dots.filter(d=>d.id!==mks[i].dataset.id);
      if(hitRect(c.r, others)) return false;
      const own = distRP(c.r, mks[i]._sx, mks[i]._sy);
      if(others.some(d=> distRP(c.r, d.x + 6, d.y + 6) <= own)) return false;
      for(let j=0;j<i;j++) if(chosen[j] && hitRect(c.r, [chosen[j].r])) return false;
      return true;
    };
    const dfs = (i)=>{
      if(i === mks.length) return true;
      for(const c of cands[i]){
        if(++nodes > 20000) return false;
        if(!ok(i, c)) continue;
        chosen[i] = c;
        if(dfs(i+1)) return true;
        chosen[i] = null;
      }
      return false;
    };
    let pass = mks.length ? "strict" : "none";
    if(mks.length && !dfs(0)){
      // for tett: de viktigste først, en lapp som ikke får plass blir borte
      pass = "dense"; chosen.fill(null);
      for(let i=0;i<mks.length;i++) chosen[i] = cands[i].find(c=>ok(i, c)) || null;
    }
    markersEl.dataset.pills = pass;
    inside.forEach(m=>{ m._pill = null; });
    mks.forEach((mk, i)=>{
      const c = chosen[i];
      mk._pill = c ? c.r : null;   // lappens endelige plass (kantpilene legger seg utenom)
      if(!c){ mk.classList.add("bare"); mk.classList.remove("left","vert"); mk.dataset.label = "dense"; return; }
      mk.classList.toggle("left", c.side==="left");
      mk.classList.toggle("vert", !!c.vert);
      if(c.vert){
        // lappen posisjoneres fra prikkens senter (--lx/--ly = lappens øvre venstre hjørne)
        mk.style.setProperty("--lx", (c.r.x - mk._sx).toFixed(1)+"px");
        mk.style.setProperty("--ly", (c.r.y - mk._sy).toFixed(1)+"px");
      } else {
        mk.style.removeProperty("--lx");
        mk.style.setProperty("--ly", c.dy+"px");
      }
    });
    inside.filter(m=>!m._wantLabel).forEach(m=>m.classList.remove("left","vert"));
  }
  function updateNote(){
    // Én diskret tekst øverst på kartet når alle spots i utsnittet er 0
    // stjerner (teksten lages i front.js). Ikke når en spot er valgt eller
    // kartet ligger skjult bak lista.
    const text = state.sheetMode==="spot" || state.sheetMode==="list" ? null : noteOf();
    if(!text){ noteEl.hidden = true; noteEl.textContent = ""; return; }
    noteEl.hidden = false; noteEl.textContent = text;
    const a = state.area;
    let ctrlBottom = 0;
    document.querySelectorAll(".top-bar .ctrl, .top-bar .brand, .top-bar .top-btns").forEach(el=>{ const r = el.getBoundingClientRect(); if(r.height) ctrlBottom = Math.max(ctrlBottom, r.bottom); });
    const y = Math.max(a.y + 22, ctrlBottom + 30);
    noteEl.style.transform = `translate3d(${(a.x + a.w/2).toFixed(1)}px, ${y.toFixed(1)}px, 0) translate(-50%,-50%)`;
  }
  function placeMarkers(animate){
    const a = state.area;
    const ox = a.x + a.w/2, oy = a.y + a.h/2;
    const hideAll = state.sheetMode==="list";
    const outs = [];
    spots.forEach(p=>{
      const mk = markersEl.querySelector(`.mk[data-id="${p.id}"]`);
      const sx = ox + (p.x - cur.cx)*cur.sc, sy = oy + (p.y - cur.cy)*cur.sc;
      const inside = !p.offMap && sx >= a.x+12 && sx <= a.x+a.w-12 && sy >= a.y+12 && sy <= a.y+a.h-12;
      mk.hidden = hideAll || !inside;
      mk.style.transition = animate ? `transform 1s ${EASE}` : "none";
      mk.style.transform = `translate3d(${sx.toFixed(1)}px, ${sy.toFixed(1)}px, 0)`;
      mk._sx = sx; mk._sy = sy; mk._inside = inside && !hideAll;
      if(!inside && !hideAll && state.sheetMode!=="spot") outs.push({p, sx, sy});
    });
    lastOuts = outs;
    layoutPills();
    updateNote();
    placeEdges(outs, animate);
  }
  // Kantpil bare for favoritter og spots med stjerner i valgt time (Theodor 13.10.2026)
  function qualifies(p){ const h = hourOf(p.s, state.idx); return !!(h && (h.stars||0) >= 1) || isFav(p.id); }
  function placeEdges(outs, animate){
    // Spots utenfor skjermen: pil i kanten som peker dit. Flere enn to i
    // omtrent samme retning slås sammen til én pil («6 spots», beste rating
    // som farge) - trykk zoomer ut. Aldri i topplinja eller bak forklaringen.
    // animate: true/false fra en ny plassering av kartet; null fra et
    // timebytte - da beholder piler som allerede står sin overgang, og nye
    // piler dukker bare opp der de skal stå.
    const a = state.area, ox = a.x + a.w/2, oy = a.y + a.h/2;
    const wasShown = new Set([...markersEl.querySelectorAll(".mk-edge:not(.cluster)")].filter(e=>!e.hidden).map(e=>e.dataset.id));
    markersEl.querySelectorAll(".mk-edge").forEach(e=>{ e.hidden = true; });
    markersEl.querySelectorAll(".mk-edge.cluster").forEach(e=>e.remove());
    clusters = [];
    const items = outs.filter(o=>qualifies(o.p)).map(o=>{
      const ang = o.p.offMap ? 215 : (Math.atan2(o.sy-oy, o.sx-ox)*180/Math.PI + 360) % 360;   // utenfor kartet: sørvest
      return {...o, ang};
    }).sort((u,v)=>u.ang-v.ang);
    // grupper etter retning (innenfor 30 grader)
    const groups = [];
    items.forEach(it=>{
      const g = groups.find(gr=> Math.abs(((it.ang - gr.ang + 540) % 360) - 180) < 30);
      if(g){ g.items.push(it); g.ang = (g.ang*(g.items.length-1) + it.ang)/g.items.length; } else groups.push({ang: it.ang, items:[it]});
    });
    // hindre: knappene, forklaringen og teksten på kartet - og spotene i utsnittet
    // (prikken og lappen), så en kantpil aldri dekker en spot (Theodor 13.10.2026)
    const obs = obstacles().concat(...[...markersEl.querySelectorAll(".mk")].filter(m=>m._inside).map(m=>
      [{x: m._sx - 9, y: m._sy - 9, w: 18, h: 18}, ...(m._pill ? [m._pill] : [])]));
    const placed = [];
    const rectAt = (x, y, w)=>({x: x - w/2, y: y - 22, w, h: 44});
    const findSpot = (ex, ey, w)=>{
      // Mobil (sideOnly): kartets underkant er toppen av arket, midt på skjermen. En spot
      // som ligger under kartet får pila langs en SIDEKANT i stedet for midt i kartet like
      // over arket (Theodor 13.10.2026): nærmeste side først, nedenfra og opp, så den andre
      // siden - første ledige plass. Pila peker fortsatt mot spoten.
      if(a.sideOnly && ey > a.y + a.h - 24){
        const lo = a.x + w/2 + 6, hi = a.x + a.w - w/2 - 6, top = a.y + 24, bot = a.y + a.h - 24;
        const sides = ex < ox ? [lo, hi] : [hi, lo];
        for(const x of sides) for(let y = bot; y >= top; y -= 46){
          const r = rectAt(x, y, w);
          if(!hitRect(r, obs) && !hitRect(r, placed)){ placed.push(r); return [x, y]; }
        }
        placed.push(rectAt(sides[0], bot, w));   // alt opptatt: nederst ved nærmeste side
        return [sides[0], bot];
      }
      ex = Math.max(a.x + w/2 + 6, Math.min(a.x + a.w - w/2 - 6, ex));
      ey = Math.max(a.y + 24, Math.min(a.y + a.h - 24, ey));
      const r = ()=>({x: ex - w/2, y: ey - 22, w, h: 44});
      let guard = 0;
      while(guard++ < 30 && (hitRect(r(), obs) || hitRect(r(), placed))){
        const ob = obs.find(q=>hitRect(r(), [q]));
        if(ob){ ey = (ob.y + ob.h/2 < (a.y + a.h/2)) ? ob.y + ob.h + 24 : ob.y - 24; }
        else ey -= 46;
        ey = Math.max(a.y + 24, Math.min(a.y + a.h - 24, ey));
        if(hitRect(r(), obs) && guard > 15) ex += (ex < a.x + a.w/2 ? 1 : -1) * 60;
      }
      placed.push(r());
      return [ex, ey];
    };
    groups.forEach(g=>{
      if(g.items.length > 2){
        const el = document.createElement("button");
        el.type = "button"; el.className = "mk-edge cluster";
        el.innerHTML = `<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" class="mk-arrow"><path d="M2 7h9M7.5 3.2 11.3 7 7.5 10.8"/></svg><span class="mk-dot small"></span><span class="mk-name">${g.items.length} spots</span><span class="mk-label"></span>`;
        el.onclick = ()=>onCluster(g.items.map(it=>it.p.id));
        markersEl.appendChild(el);
        const c = {el, items: g.items}; clusters.push(c); colorCluster(c);
        const rad = g.ang*Math.PI/180, w = el.offsetWidth || 150;   // målt bredde: pila ligger helt inntil kanten
        const [ex, ey] = findSpot(ox + Math.cos(rad)*a.w, oy + Math.sin(rad)*a.h, w);
        el.style.transform = `translate3d(${ex.toFixed(1)}px, ${ey.toFixed(1)}px, 0) translate(-50%,-50%)`;
        // pila peker fra der den står mot spotenes midtpunkt (som enkeltpilene) - også når
        // mobilregelen har flyttet den til en sidekant (fysikk-kontrollør 14.10.2026)
        const pts = g.items.filter(it=>!it.p.offMap && Number.isFinite(it.sx) && Number.isFinite(it.sy));
        const ang = pts.length ? Math.atan2(pts.reduce((v, it)=>v + it.sy, 0)/pts.length - ey, pts.reduce((v, it)=>v + it.sx, 0)/pts.length - ex)*180/Math.PI : g.ang;
        el.querySelector(".mk-arrow").style.transform = `rotate(${ang.toFixed(0)}deg)`;
      } else g.items.forEach(it=>{
        const ed = markersEl.querySelector(`.mk-edge[data-id="${it.p.id}"]`);
        ed.hidden = false;   // synlig før målingen (samme oppgave - ingen tegning i mellom)
        const w = ed.offsetWidth || (60 + it.p.name.length*7.2 + ed.querySelector(".mk-label").textContent.length*7.2);
        // utenfor kystkartet (sørvest): nederst til høyre på PC; på mobil som en spot under
        // kartet mot venstre (langs sidekanten, se findSpot)
        let ex = it.p.offMap ? (a.sideOnly ? a.x : a.x + a.w - 110) : it.sx, ey = it.p.offMap ? (a.sideOnly ? a.y + a.h + 100 : a.y + a.h - 44) : it.sy;
        [ex, ey] = findSpot(ex, ey, w);
        const ang = it.p.offMap ? 135 : Math.atan2(it.sy-ey, it.sx-ex)*180/Math.PI;
        if(animate === true) ed.style.transition = `transform 1s ${EASE}`;
        else if(animate === false || !wasShown.has(it.p.id)) ed.style.transition = "none";
        ed.style.transform = `translate3d(${ex.toFixed(1)}px, ${ey.toFixed(1)}px, 0) translate(-50%,-50%)`;
        ed.querySelector(".mk-arrow").style.transform = `rotate(${ang.toFixed(0)}deg)`;
      });
    });
  }
  // Klyngepil: beste rating i VALGT time gir farge og etikett («beste 3★»).
  // 0 stjerner: «flatt» bare når ALLE timene er ekte flate (samme regel som
  // flatInfo i front.js), ellers «ingen surf» - og «–» hvis noen mangler
  // (manglende tall er aldri flatt).
  function clusterInfo(items){
    // Ordene kommer fra ratingWord() i app.js (samme ord overalt, «Smått» inkludert).
    // 0 stjerner: «smått» hvis alle er Flatt/Smått og minst én Smått, «flatt»
    // hvis alle er Flatt (samme regel som flatInfo i front.js), ellers
    // «ingen surf» (grøtete, blåst ut, treffer ikke, stormsjø ...).
    let best = 0, top = 0, missing = false;
    items.forEach(it=>{
      const h = hourOf(it.p.s, state.idx);
      if(!h || (h.surf_height==null && !h.low_reason)){ missing = true; return; }
      best = Math.max(best, h.stars||0);
      const k = ZERO_WORDS.indexOf(ratingWord(h));
      top = k < 0 ? -1 : (top < 0 ? -1 : Math.max(top, k));
    });
    const zw = top < 0 ? "ingen surf" : ZERO_WORDS[top].toLowerCase();
    const label = best ? `beste ${best}★` : missing ? "–" : zw;
    const aria = best ? `beste: ${best} ${best===1?"stjerne":"stjerner"} (${STR.starWords[Math.min(5,best)]})` : missing ? "noen timer mangler data" : zw;
    return {best, label, aria};
  }
  function colorCluster(c){
    const {best, label, aria} = clusterInfo(c.items);
    c.el.className = `mk-edge cluster r-${Math.min(5,best)}${best?" lit":""}`;
    c.el.style.setProperty("--mc", COL[Math.min(5,best)]);
    c.el.querySelector(".mk-label").innerHTML = labelHtml(label);
    c.el.setAttribute("aria-label", `${c.items.length} spots utenfor kartet: ${c.items.map(it=>it.p.name).join(", ")}. ${aria}. Trykk for å zoome ut`);
  }
  function colorMarkers(){
    const idx = state.idx;
    spots.forEach(p=>{
      const h = hourOf(p.s, idx);
      const st = h ? (h.stars||0) : 0;
      const col = COL[Math.min(5, st)];
      const label = h ? labelOf(h) : "–";
      const aria = h ? ariaOf(p.s, h) : `${p.name}, tallet mangler`;
      const isSel = state.spotId===p.id;
      const fav = isFav(p.id);
      // Tallet mangler (ingen time, eller 0 stjerner uten grunn og uten høyde):
      // ALDRI den grå 0-prikken - stiplet prikk og lappen «–» (grunnregelen).
      const missing = !h || (!h.stars && !h.low_reason && h.surf_height==null);
      const mk = markersEl.querySelector(`.mk[data-id="${p.id}"]`);
      for(const el of [mk, markersEl.querySelector(`.mk-edge[data-id="${p.id}"]`)]){
        const edge = el.classList.contains("mk-edge");
        // left/vert/bare eies av layoutPills (kjøres rett under)
        el.className = (edge ? "mk-edge" : "mk") + ` r-${Math.min(5,st)}` + (st>=1 ? " lit" : "") + (isSel ? " sel" : "") + (fav ? " fav" : "") + (missing ? " miss" : "");
        el.style.setProperty("--mc", col);
        // roligere puls ved lang periode
        const per = h && h.period!=null ? h.period : 10;
        el.style.setProperty("--pulse", Math.max(1.8, Math.min(4.2, per*0.24)).toFixed(2)+"s");
        el.querySelector(".mk-label").innerHTML = labelHtml(label);
        el.setAttribute("aria-label", aria + (edge ? ", utenfor kartet" : "") + (fav ? ", favoritt" : ""));
      }
      mk._st = st; mk._sel = isSel; mk._fav = fav;
      mk._wantLabel = st >= 1 || fav || isSel || missing;
    });
    layoutPills();          // hvem som har lapp, og pillens bredde, følger timen
    updateNote();
    placeEdges(lastOuts, null);   // kantpiler følger stjernene i valgt time
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
    if(!h || h.dir_offshore==null || h.directness==null) return "svellretning ukjent";
    const miss = h.directness!=null && h.directness < 0.667;
    return miss ? "svellet treffer ikke vinduet" : "svellet treffer vinduet";
  }
  // Én felles klassifisering for kilen på kartet OG skiva i spotarket
  // (front.js kaller Kart.hitClass) - test_map_disc.py leser disse linjene.
  function hitClass(h){
    if(!h) return "miss";
    const missing = h.dir_offshore==null;
    const dn = h.directness;
    const cls = missing || dn==null || dn < 0.667 ? "miss" : dn >= 0.999 ? "" : "edge";
    return cls;
  }
  function wedgeMarkup(p, h){
    const win = p.s.swell_window; if(!win || !h) return "";
    const st = h.stars||0;
    const col = st>=1 ? COL[Math.min(5,st)] : WINDOW_COL;
    const missing = h.dir_offshore==null;
    const cls = hitClass(h);
    const per = h.period!=null ? h.period : 10;
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
    if(h.height_source==="barentswatch" && h.bw_dir!=null){
      const noHit = h.spot_direction_factor===0;
      const q = pt(h.bw_dir, 44);
      spotSwellMarkup = `<line class="disc-spot-swell${noHit?" miss":""}" x1="${q[0].toFixed(2)}" y1="${q[1].toFixed(2)}" x2="0" y2="0"/>`;
    }
    return `<g class="wedge ${cls}" transform="translate(${p.x.toFixed(2)} ${p.y.toFixed(2)})" aria-label="${esc(wedgeAriaLabel(h))}">
      <path class="wedge-fill" d="${wedgePath(win, R_WEDGE)}" style="fill:${cls==="miss"?WINDOW_COL:col};stroke:${cls==="miss"?WINDOW_COL:col}"/>
      ${spotSwellMarkup}
      <circle r="1.4" class="wedge-c"/>
      <g class="swell-rot" transform="rotate(${dir})">${swell}</g>
    </g>`;
  }
  function drawWedge(){
    const p = state.spotId ? spots.find(q=>q.id===state.spotId) : null;
    if(!p || p.offMap || state.sheetMode!=="spot"){ wedgeG.innerHTML = ""; return; }
    // S2: spotens detaljfil er ikke lastet ennå (oversikten har ikke retningen) - ingen kile,
    // ikke en grå «bom»-kile som ville sett ut som et svar
    if(p.s._full === false){ wedgeG.innerHTML = ""; return; }
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
    // Vindstrekene bare når en spot er valgt - da gjelder vinden den spoten
    // (Theodor 13.10.2026: animasjon bare der det er noe å vise).
    setWind(state.sheetMode==="spot" && state.spotId ? h : null);
    setNight(h); colorMarkers(); drawWedge();
  }
  function setSpot(id, mode, animate){
    state.spotId = id; state.sheetMode = mode;
    recenter(animate!==false); colorMarkers(); drawWedge(); setHour(state.idx);
  }
  function setMode(mode, animate){ state.sheetMode = mode; recenter(animate!==false); drawWedge(); }
  function esc(s){ return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
  function spotInfo(id){ return spots.find(p=>p.id===id) || null; }

  window.Kart = { init, setArea, setView, setHour, setSpot, setMode, spotInfo, viewSpotIds, COL, focusSpot, hitClass, lightOf, relayout: ()=>placeMarkers(false) };
})();
