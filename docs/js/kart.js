/* Nordsurf: kartlaget og merkene for Utforsk (Tillegg 2, Theodor 15.10.2026).

   Kartlaget ligger bak et lite grensesnitt (Kart.lag): setExtent(ramme), toScreen(lat, lon),
   drawCoast(). I dag: vektorkysten i docs/geo/coast.json (GSHHS, Nord-Norge) som SVG, flyttet
   og zoomet med CSS-transform. S3 kan bytte laget til MapLibre/PMTiles for hele Norge uten å
   røre merker, klynger og kort (Kart.markers bruker bare toScreen/extent).

   Merker: prikk + lapp «Navn Ord», lappen prøver høyre, venstre, over og under - er det ikke
   plass, bare prikken. Klynging: merker nærmere hverandre enn CLUSTER_PX på skjermen slås
   sammen til én sirkel med antall og farge etter beste vurdering; trykk zoomer inn. Bare merker
   i utsnittet tegnes. Ren visning: verdi/ord per spot kommer fra utforsk.js. */
(function(){
  const VW = 1000, VH = 844;
  const EASE = "cubic-bezier(.2,.8,.2,1)";
  const CLUSTER_PX = 48, PH = 28, GAP = 12;
  const merc = (lat)=> Math.log(Math.tan(Math.PI/4 + lat*Math.PI/360));
  const esc = (s)=> String(s).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const reduced = ()=> matchMedia("(prefers-reduced-motion: reduce)").matches;
  let root, mapLayer, svg, markersEl, coast = null, proj = null;
  let area = {x:0, y:0, w:390, h:600}, cur = {cx:0, cy:0, sc:1}, prevT = null, crisp = false;
  let spots = [], valueOf = ()=>({st:0, word:"", miss:false, aria:""}), onPick = ()=>{}, onCluster = ()=>{};
  let selected = null;

  /* ---------- kartlaget (grensesnittet S3 bytter ut) ---------- */
  const Lag = {
    init(el, coastJson){
      root = el; coast = coastJson;
      const [w0, s0, e0, n0] = coast.bbox, mN = merc(n0), mS = merc(s0);
      proj = { x: (lon)=> (lon - w0) / (e0 - w0) * coast.vw, y: (lat)=> (mN - merc(lat)) / (mN - mS) * coast.vh,
               lon: (x)=> w0 + x / coast.vw * (e0 - w0), lat: (y)=> Math.atan(Math.sinh(mN - y / coast.vh * (mN - mS))) * 180 / Math.PI };
      root.innerHTML = `<div class="map-layer" id="mapLayer"><svg id="mapSvg" width="${VW}" height="${VH}" viewBox="0 0 ${VW} ${VH}" aria-hidden="true" style="overflow:visible;display:block"><path class="coast" d="${coast.d}"/></svg></div><div class="markers" id="markersLayer"></div>`;
      mapLayer = root.querySelector("#mapLayer"); svg = root.querySelector("#mapSvg"); markersEl = root.querySelector("#markersLayer");
      mapLayer.addEventListener("transitionend", (e)=>{ if(e.target===mapLayer && e.propertyName==="transform") crispen(); });
    },
    covers(lat, lon){ const [w0, s0, e0, n0] = coast.bbox; return lat >= s0 && lat <= n0 && lon >= w0 && lon <= e0; },
    // ramme [latMin, lonMin, latMax, lonMax] -> utsnitt som fyller det synlige området (med kant)
    setExtent(ext, animate){
      const x0 = proj.x(ext[1]), x1 = proj.x(ext[3]), y0 = proj.y(ext[2]), y1 = proj.y(ext[0]);
      const pad = Math.min(60, area.w * 0.08);
      const w = Math.max(40, x1 - x0), h = Math.max(40, y1 - y0);
      cur = { cx: (x0+x1)/2, cy: (y0+y1)/2, sc: Math.max(0.3, Math.min(12, Math.min((area.w - 2*pad) / w, (area.h - 2*pad) / h))) };
      applyTransform(animate);
    },
    toScreen(lat, lon){ const ox = area.x + area.w/2, oy = area.y + area.h/2; return {x: ox + (proj.x(lon) - cur.cx)*cur.sc, y: oy + (proj.y(lat) - cur.cy)*cur.sc}; },
    extent(){ // synlig ramme i lat/lon
      const ox = area.x + area.w/2, oy = area.y + area.h/2;
      const px = (sx)=> cur.cx + (sx - ox)/cur.sc, py = (sy)=> cur.cy + (sy - oy)/cur.sc;
      return [proj.lat(py(area.y + area.h)), proj.lon(px(area.x)), proj.lat(py(area.y)), proj.lon(px(area.x + area.w))];
    },
    drawCoast(){ /* kysten ligger alt i SVG-en - S3 tegner fliser her */ },
    thumbSvg(points, colorOf){
      if(!coast) return "";
      const pts = points.filter(p=> Lag.covers(p.lat, p.lon)).map(p=>({...p, x: proj.x(p.lon), y: proj.y(p.lat)}));
      if(!pts.length) return "";
      const xs = pts.map(p=>p.x), ys = pts.map(p=>p.y);
      const x0 = Math.min(...xs) - 90, x1 = Math.max(...xs) + 90, y0 = Math.min(...ys) - 70, y1 = Math.max(...ys) + 70;
      return `<svg viewBox="${x0.toFixed(0)} ${y0.toFixed(0)} ${(x1-x0).toFixed(0)} ${(y1-y0).toFixed(0)}" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><path class="coast" d="${coast.d}"/>${pts.map(p=>`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="6" class="r-${Math.min(5, colorOf(p))}" style="fill:var(--rc);stroke:var(--raised);stroke-width:2"/>`).join("")}</svg>`;
    },
  };
  function cssTransform(){ const ox = area.x + area.w/2, oy = area.y + area.h/2; return { tx: ox - cur.cx*cur.sc, ty: oy - cur.cy*cur.sc, sc: cur.sc }; }
  function uncrispen(){
    if(!crisp) return;
    crisp = false;
    svg.setAttribute("viewBox", `0 0 ${VW} ${VH}`); svg.setAttribute("width", VW); svg.setAttribute("height", VH);
    mapLayer.style.width = VW+"px"; mapLayer.style.height = VH+"px"; mapLayer.style.transition = "none";
    const t = prevT || cssTransform();
    mapLayer.style.transform = `translate(${t.tx.toFixed(1)}px, ${t.ty.toFixed(1)}px) scale(${t.sc.toFixed(4)})`;
    void mapLayer.offsetWidth;
  }
  function crispen(){
    const t = cssTransform(), W = root.clientWidth || 390, H = root.clientHeight || 600;
    crisp = true;
    mapLayer.style.transition = "none"; mapLayer.style.transform = "none";
    mapLayer.style.width = W+"px"; mapLayer.style.height = H+"px";
    svg.setAttribute("width", W); svg.setAttribute("height", H);
    svg.setAttribute("viewBox", `${(-t.tx/t.sc).toFixed(3)} ${(-t.ty/t.sc).toFixed(3)} ${(W/t.sc).toFixed(3)} ${(H/t.sc).toFixed(3)}`);
  }
  function applyTransform(animate){
    const t = cssTransform();
    const same = prevT && Math.abs(prevT.tx-t.tx) < 0.5 && Math.abs(prevT.ty-t.ty) < 0.5 && Math.abs(prevT.sc-t.sc) < 1e-4;
    if(animate && !reduced() && !same){
      uncrispen();
      mapLayer.style.transition = `transform .7s ${EASE}`;
      mapLayer.style.transform = `translate(${t.tx.toFixed(1)}px, ${t.ty.toFixed(1)}px) scale(${t.sc.toFixed(4)})`;
    } else { prevT = t; crispen(); }
    prevT = t;
    draw(animate && !reduced());
  }

  /* ---------- merker og klynger ---------- */
  function init(el, coastJson, list, o){
    Lag.init(el, coastJson);
    spots = list.map(s=>({s, id: s.id, name: s.name, lat: s.spot && s.spot.lat, lon: s.spot && s.spot.lon}))
      .map(p=>({...p, offMap: !(p.lat!=null && p.lon!=null && Lag.covers(p.lat, p.lon))}));
    valueOf = o.valueOf || valueOf; onPick = o.onPick || onPick; onCluster = o.onCluster || onCluster;
  }
  function setArea(a){ area = a; }
  function setSelected(id){ selected = id; draw(false); }
  const offMapSpots = ()=> spots.filter(p=>p.offMap);
  const screenOf = (id)=>{ const p = spots.find(x=>x.id===id); return p && !p.offMap ? Lag.toScreen(p.lat, p.lon) : null; };
  function clusters(){
    // enkel greedy klynging: merker innenfor CLUSTER_PX av hverandre på skjermen slås sammen
    const inside = [];
    for(const p of spots){
      if(p.offMap) continue;
      const sc = Lag.toScreen(p.lat, p.lon);
      if(sc.x < area.x + 10 || sc.x > area.x + area.w - 10 || sc.y < area.y + 10 || sc.y > area.y + area.h - 10) continue;
      inside.push({p, x: sc.x, y: sc.y, v: valueOf(p)});
    }
    const groups = [];
    for(const m of inside){
      let g = groups.find(g=> Math.hypot(g.x - m.x, g.y - m.y) < CLUSTER_PX);
      if(g){ g.members.push(m); g.x = g.members.reduce((a, b)=>a + b.x, 0) / g.members.length; g.y = g.members.reduce((a, b)=>a + b.y, 0) / g.members.length; }
      else groups.push({x: m.x, y: m.y, members: [m]});
    }
    return groups;
  }
  function draw(animate){
    if(!markersEl) return;
    const groups = clusters();
    const html = [];
    const placed = [];   // lapper plassert, til kollisjonssjekk
    const dots = groups.map(g=>({x: g.x - 7, y: g.y - 7, w: 14, h: 14}));
    const hit = (r)=> placed.some(q=> r.x < q.x+q.w && r.x+r.w > q.x && r.y < q.y+q.h && r.y+r.h > q.y) || dots.some(q=> r.x < q.x+q.w && r.x+r.w > q.x && r.y < q.y+q.h && r.y+r.h > q.y);
    // valgt først (beholder lappen), så flest stjerner
    const order = groups.map((g, i)=>({g, i})).sort((a, b)=> (b.g.members.some(m=>m.p.id===selected) ? 1 : 0) - (a.g.members.some(m=>m.p.id===selected) ? 1 : 0) || Math.max(...b.g.members.map(m=>m.v.st||0)) - Math.max(...a.g.members.map(m=>m.v.st||0)));
    for(const {g} of order){
      if(g.members.length > 1){
        const best = g.members.reduce((a, b)=> (b.v.st||0) > (a.v.st||0) ? b : a);
        const ids = g.members.map(m=>m.p.id).join(",");
        html.push(`<button type="button" class="klynge r-${Math.min(5, best.v.st||0)}" style="transform:translate3d(${(g.x-22).toFixed(1)}px,${(g.y-22).toFixed(1)}px,0)" data-ids="${esc(ids)}" aria-label="${esc(`${g.members.length} spots, beste ${best.v.word || "–"}. Zoom inn`)}"><span class="ring"><b>${g.members.length}</b></span></button>`);
        continue;
      }
      const m = g.members[0], sel = m.p.id===selected;
      const txt = `${m.p.name} ${m.v.miss ? "–" : (m.v.word || "")}`.trim();
      const w = 22 + txt.length * 7.4;
      const cands = [["right", m.x + GAP, m.y - PH/2], ["left", m.x - GAP - w, m.y - PH/2], ["over", m.x - w/2, m.y - GAP - PH - 2], ["under", m.x - w/2, m.y + GAP + 2]];
      let pos = null;
      for(const [side, x, y] of cands){
        const r = {x, y, w, h: PH};
        if(x < area.x + 4 || x + w > area.x + area.w - 4 || y < area.y + 2 || y + PH > area.y + area.h - 2) continue;
        if(hit(r)) continue;
        pos = {side, r}; break;
      }
      if(!pos && sel) pos = {side: "right", r: {x: Math.max(area.x + 4, Math.min(area.x + area.w - 4 - w, m.x + GAP)), y: m.y - PH/2, w, h: PH}};
      if(pos) placed.push(pos.r);
      html.push(`<button type="button" class="mk r-${Math.min(5, m.v.st||0)}${m.v.miss ? " miss" : ""}${sel ? " sel" : ""}${pos ? "" : " bare"}" style="transform:translate3d(${(m.x-22).toFixed(1)}px,${(m.y-22).toFixed(1)}px,0)" data-id="${esc(m.p.id)}" aria-label="${esc(m.v.aria || m.p.name)}" aria-pressed="${sel}">
        <span class="mk-dot"></span>${pos ? `<span class="mk-pill" style="left:${(pos.r.x - (m.x-22)).toFixed(1)}px;top:${(pos.r.y - (m.y-22)).toFixed(1)}px"><span class="nm">${esc(m.p.name)}</span><span class="ord">${esc(m.v.miss ? "–" : (m.v.word || ""))}</span></span>` : ""}</button>`);
    }
    markersEl.innerHTML = html.join("");
    markersEl.querySelectorAll(".mk").forEach(b=> b.onclick = ()=> onPick(b.dataset.id));
    markersEl.querySelectorAll(".klynge").forEach(b=> b.onclick = ()=> onCluster(b.dataset.ids.split(",")));
    markersEl.dataset.clusters = String(groups.filter(g=>g.members.length > 1).length);
  }
  function extentOf(ids){
    const pts = spots.filter(p=> ids.includes(p.id) && !p.offMap);
    if(!pts.length) return null;
    const la = pts.map(p=>p.lat), lo = pts.map(p=>p.lon);
    const dl = Math.max(0.03, (Math.max(...la) - Math.min(...la)) * 0.6), dn = Math.max(0.08, (Math.max(...lo) - Math.min(...lo)) * 0.6);
    return [Math.min(...la) - dl, Math.min(...lo) - dn, Math.max(...la) + dl, Math.max(...lo) + dn];
  }
  function thumb(colorOf){ return Lag.thumbSvg(spots.filter(p=>!p.offMap), (p)=> colorOf(p)); }
  window.Kart = { lag: Lag, init, setArea, setExtent: (e, a)=> Lag.setExtent(e, a), setSelected, redraw: ()=> draw(false), offMapSpots, screenOf, extentOf, thumb, covers: (la, lo)=> Lag.covers(la, lo) };
})();
