/* Nordsurf: kartlaget og merkene for Utforsk (Tillegg 2, Theodor 15.10.2026; S3 16.10.2026).

   Kartlaget ligger bak et lite grensesnitt (Kart.lag): init, setExtent(ramme), toScreen(lat, lon),
   extent(), drawCoast(), covers(lat, lon). S3 (ROADMAP K del B): MapLibre GL JS 5.24.0
   (docs/vendor/, selvhostet) med land og kyst for hele Norge fra docs/geo/norge-*.pmtiles
   (tools/lag_kartfliser.py, OpenStreetMap, ODbL). MapLibre tegner bare land/hav/kyst - merker,
   klynger, lapper og kort er HTML over kartet som før (ingen tekst i kartstilen, ingen glyph-filer).
   Ingen rotasjon eller tilt; maxBounds rundt Norge, zoom 4-12 (MAX_ZOOM); fargene følger systemtemaet live.

   Merker: prikk + lapp «Navn Ord», lappen prøver høyre, venstre, over og under - er det ikke
   plass, bare prikken. Klynging: merker nærmere hverandre enn CLUSTER_PX på skjermen slås
   sammen til én sirkel med antall og farge etter beste vurdering; trykk zoomer inn. Bare merker
   i utsnittet tegnes, og klyngene regnes på nytt høyst én gang per bilde (requestAnimationFrame).
   Ren visning: verdi/ord per spot kommer fra utforsk.js.

   Miniatyren på Hjem (PC) bruker fortsatt docs/geo/coast.json (SVG, Nord-Norge). */
(function(){
  const CLUSTER_PX = 48, PH = 28, GAP = 12;
  const BOUNDS = [[1.0, 56.3], [34.0, 72.3]];          // maxBounds: fastlands-Norge med luft
  // flisene dekker mer enn maxBounds (tools/lag_kartfliser.py, ramme -1..36 Ø, 55..73,5 N), så hele det synlige kartet har land
  const COVER = {s: BOUNDS[0][1], w: BOUNDS[0][0], n: BOUNDS[1][1], e: BOUNDS[1][0]};
  // Theodor 16.10: kysten er grov helt inne på en spot. Detaljflisene går til z12 (forenklet til en halv piksel der) -
  // over z12 forstørres de bare, så maks zoom settes dit dataene faktisk har detaljer. Finere kyst rundt spotene: ROADMAP S3.
  const MAX_ZOOM = 12;
  const OVERSIKT_MAX = 7;                                 // norge-oversikt.pmtiles z0-7, norge-detalj.pmtiles z8+
  const merc = (lat)=> Math.log(Math.tan(Math.PI/4 + lat*Math.PI/360));
  const esc = (s)=> String(s).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const reduced = ()=> matchMedia("(prefers-reduced-motion: reduce)").matches;
  let root, markersEl, map = null, coast = null, thumbProj = null;
  let area = {x:0, y:0, w:390, h:600};
  let spots = [], valueOf = ()=>({st:0, word:"", miss:false, aria:""}), onPick = ()=>{}, onCluster = ()=>{};
  let selected = null, rafId = 0;

  function cssVar(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function colors(){ return {land: cssVar("--land") || "#F2EDE2", sea: cssVar("--sea") || "#B7D3DF", coast: cssVar("--coast") || "#8F8268"}; }
  function style(){
    const c = colors(), abs = (f)=> "pmtiles://" + new URL("geo/" + f, location.href).href;
    return {
      version: 8,
      sources: {
        lav: {type: "vector", url: abs("norge-oversikt.pmtiles"), attribution: '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap-bidragsytere</a>'},
        hoy: {type: "vector", url: abs("norge-detalj.pmtiles"), attribution: '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap-bidragsytere</a>'},
      },
      layers: [
        {id: "hav", type: "background", paint: {"background-color": c.sea}},
        // oversikten (precachet) til og med z7. Fra z8: detaljflisene finnes bare der det er kyst innen 1 km; inne på land
        // fyller oversiktens «kjerne» (landet krympet 600 m innover, tools/lag_kartfliser.py) - den når aldri ut i sjøen.
        {id: "land-lav", type: "fill", source: "lav", "source-layer": "land", maxzoom: OVERSIKT_MAX + 1, paint: {"fill-color": c.land}},
        {id: "kjerne-lav", type: "fill", source: "lav", "source-layer": "kjerne", minzoom: OVERSIKT_MAX + 1, paint: {"fill-color": c.land}},
        {id: "land-hoy", type: "fill", source: "hoy", "source-layer": "land", minzoom: OVERSIKT_MAX + 1, paint: {"fill-color": c.land}},
        {id: "kyst-lav", type: "line", source: "lav", "source-layer": "kyst", maxzoom: OVERSIKT_MAX + 1, paint: {"line-color": c.coast, "line-width": 1}},
        {id: "kyst-hoy", type: "line", source: "hoy", "source-layer": "kyst", minzoom: OVERSIKT_MAX + 1, paint: {"line-color": c.coast, "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1, 14, 1.6]}},
      ],
    };
  }
  function applyColors(){
    if(!map) return;
    // isStyleLoaded() er usann mens fliser lastes - prøv igjen når kartet er ferdig, ellers blir et temabytte borte
    if(!map.isStyleLoaded()){ map.once("idle", applyColors); return; }
    const c = colors();
    map.setPaintProperty("hav", "background-color", c.sea);
    for(const id of ["land-lav", "kjerne-lav", "land-hoy"]) map.setPaintProperty(id, "fill-color", c.land);
    for(const id of ["kyst-lav", "kyst-hoy"]) map.setPaintProperty(id, "line-color", c.coast);
  }
  // MapLibre (1 MB) og PMTiles lastes først når Utforsk åpnes - Hjem skal ikke vente på dem
  const LIB = ["vendor/maplibre-gl-5.24.0.js", "vendor/pmtiles-4.5.0.js"], LIB_CSS = "vendor/maplibre-gl-5.24.0.css";
  let libP = null;
  function loadLib(){
    if(window.maplibregl && window.pmtiles) return Promise.resolve();
    if(libP) return libP;
    if(!document.querySelector(`link[href="${LIB_CSS}"]`)){ const l = document.createElement("link"); l.rel = "stylesheet"; l.href = LIB_CSS; document.head.appendChild(l); }
    const one = (src)=> new Promise((ok, fail)=>{ const sc = document.createElement("script"); sc.src = src; sc.onload = ok; sc.onerror = ()=> fail(new Error("kunne ikke laste " + src)); document.head.appendChild(sc); });
    libP = Promise.all(LIB.map(one)).catch(e=>{ libP = null; throw e; });
    return libP;
  }
  function setCoast(c){
    coast = c;
    if(!coast) return;
    const [w0, s0, e0, n0] = coast.bbox, mN = merc(n0), mS = merc(s0);
    thumbProj = { x: (lon)=> (lon - w0) / (e0 - w0) * coast.vw, y: (lat)=> (mN - merc(lat)) / (mN - mS) * coast.vh, bbox: coast.bbox };
  }
  function schedule(){ if(!rafId) rafId = requestAnimationFrame(()=>{ rafId = 0; draw(); }); }

  /* ---------- kartlaget (grensesnittet S3 byttet ut) ---------- */
  const Lag = {
    init(el, coastJson){
      root = el; if(coastJson) setCoast(coastJson);
      root.innerHTML = `<div class="ml-kart" id="mlKart" aria-hidden="true"></div><div class="markers" id="markersLayer"></div>`;
      markersEl = root.querySelector("#markersLayer");
      if(!window.maplibregl || !window.pmtiles){ console.error("MapLibre/PMTiles mangler"); return; }
      if(!Lag._proto){ Lag._proto = new pmtiles.Protocol(); maplibregl.addProtocol("pmtiles", Lag._proto.tile); }
      const tGl = performance.now();
      map = new maplibregl.Map({
        container: root.querySelector("#mlKart"), style: style(), bounds: [[4, 57.5], [31.5, 71.3]],
        maxBounds: BOUNDS, minZoom: 4, maxZoom: MAX_ZOOM, maxPitch: 0, pitchWithRotate: false, dragRotate: false, touchPitch: false,
        renderWorldCopies: false, attributionControl: false, fadeDuration: 0, keyboard: true,
      });
      window.__kartOppsettMs = performance.now() - tGl;   // WebGL-kontekst og shadere (testene skiller dette ut)
      map.touchZoomRotate.disableRotation();
      map.keyboard.disableRotation();
      map.addControl(new maplibregl.AttributionControl({compact: true}), "bottom-left");
      map.on("move", schedule);
      map.on("resize", schedule);
      map.on("load", ()=>{ applyColors(); schedule(); });
      const mq = matchMedia("(prefers-color-scheme: dark)");
      (mq.addEventListener ? mq.addEventListener("change", applyColors) : mq.addListener(applyColors));
      new MutationObserver(applyColors).observe(document.documentElement, {attributes: true, attributeFilter: ["data-theme"]});
      window.__kart = map;   // testene leser kameraet herfra
    },
    covers(lat, lon){ return lat >= COVER.s && lat <= COVER.n && lon >= COVER.w && lon <= COVER.e; },
    // ramme [latMin, lonMin, latMax, lonMax] -> utsnitt som fyller det synlige området (med kant)
    setExtent(ext, animate){
      if(!map) return;
      const W = root.clientWidth || 390, Hh = root.clientHeight || 600, pad = Math.min(60, area.w * 0.08);
      // ekstra luft nederst til kildemerket (© OpenStreetMap-bidragsytere), så ingen spot havner under det
      const attr = root.querySelector(".maplibregl-ctrl-bottom-left"), aH = attr ? attr.getBoundingClientRect().height : 30;
      const padding = {top: area.y + pad, bottom: Math.max(pad, Hh - (area.y + area.h) + pad) + aH, left: area.x + pad, right: Math.max(pad, W - (area.x + area.w) + pad)};
      map.fitBounds([[ext[1], ext[0]], [ext[3], ext[2]]], {padding, duration: animate && !reduced() ? 700 : 0, maxZoom: MAX_ZOOM});
    },
    toScreen(lat, lon){ if(!map) return {x: -1e4, y: -1e4}; const p = map.project([lon, lat]); return {x: p.x, y: p.y}; },
    extent(){ if(!map) return null; const b = map.getBounds(); return [b.getSouth(), b.getWest(), b.getNorth(), b.getEast()]; },
    resize(){ if(map) map.resize(); },
    zoomIn(lat, lon){ if(map) map.easeTo({center: [lon, lat], zoom: Math.min(MAX_ZOOM, map.getZoom() + 2), duration: reduced() ? 0 : 500}); },
    drawCoast(){ /* MapLibre tegner kysten selv (flisene) */ },
    thumbSvg(points, colorOf){
      if(!coast || !thumbProj) return "";
      const [w0, s0, e0, n0] = thumbProj.bbox;
      const pts = points.filter(p=> p.lat >= s0 && p.lat <= n0 && p.lon >= w0 && p.lon <= e0).map(p=>({...p, x: thumbProj.x(p.lon), y: thumbProj.y(p.lat)}));
      if(!pts.length) return "";
      const xs = pts.map(p=>p.x), ys = pts.map(p=>p.y);
      const x0 = Math.min(...xs) - 90, x1 = Math.max(...xs) + 90, y0 = Math.min(...ys) - 70, y1 = Math.max(...ys) + 70;
      return `<svg viewBox="${x0.toFixed(0)} ${y0.toFixed(0)} ${(x1-x0).toFixed(0)} ${(y1-y0).toFixed(0)}" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><path class="coast" d="${coast.d}"/>${pts.map(p=>`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="6" class="r-${Math.min(5, colorOf(p))}" style="fill:var(--rc);stroke:var(--raised);stroke-width:2"/>`).join("")}</svg>`;
    },
  };

  /* ---------- merker og klynger ---------- */
  function init(el, coastJson, list, o){
    Lag.init(el, coastJson);
    spots = list.map(s=>({s, id: s.id, name: s.name, lat: s.spot && s.spot.lat, lon: s.spot && s.spot.lon}))
      .map(p=>({...p, offMap: !(p.lat!=null && p.lon!=null && Lag.covers(p.lat, p.lon))}));
    valueOf = o.valueOf || valueOf; onPick = o.onPick || onPick; onCluster = o.onCluster || onCluster;
  }
  function setArea(a){ area = a; Lag.resize(); }
  function setSelected(id){ selected = id; draw(); }
  const offMapSpots = ()=> spots.filter(p=>p.offMap);
  const screenOf = (id)=>{ const p = spots.find(x=>x.id===id); return p && !p.offMap ? Lag.toScreen(p.lat, p.lon) : null; };
  function clusters(){
    // greedy klynging som før (merker innenfor CLUSTER_PX slås sammen), men med et rutenett av
    // CLUSTER_PX-celler så hver ny prikk bare sjekker klyngene i nabocellene (500 spots: O(n))
    const inside = [];
    const x0 = area.x + 10, x1 = area.x + area.w - 10, y0 = area.y + 10, y1 = area.y + area.h - 10;
    for(const p of spots){
      if(p.offMap) continue;
      const sc = Lag.toScreen(p.lat, p.lon);
      if(sc.x < x0 || sc.x > x1 || sc.y < y0 || sc.y > y1) continue;
      inside.push({p, x: sc.x, y: sc.y, v: valueOf(p)});
    }
    const groups = [], grid = new Map();
    const key = (cx, cy)=> cx * 100003 + cy;
    for(const m of inside){
      const cx = Math.floor(m.x / CLUSTER_PX), cy = Math.floor(m.y / CLUSTER_PX);
      let g = null;
      for(let dx = -1; dx <= 1 && !g; dx++) for(let dy = -1; dy <= 1 && !g; dy++){
        const list = grid.get(key(cx + dx, cy + dy));
        if(list) g = list.find(g=> Math.hypot(g.x - m.x, g.y - m.y) < CLUSTER_PX) || null;
      }
      if(g){ g.members.push(m); g.sx += m.x; g.sy += m.y; g.x = g.sx / g.members.length; g.y = g.sy / g.members.length; }
      else { g = {x: m.x, y: m.y, sx: m.x, sy: m.y, members: [m]}; groups.push(g); const k = key(cx, cy); if(!grid.has(k)) grid.set(k, []); grid.get(k).push(g); }
    }
    return groups;
  }
  const OVERLAY_SEL = ".maplibregl-ctrl-attrib, .maplibregl-ctrl, #viewUtforsk button, #viewUtforsk a, #viewUtforsk [data-kart-hinder]";
  function overlays(){
    // boksene (i markørlagets koordinater, med 4 px luft) til alt som ligger over kartet og ikke er merker/klynger
    const base = markersEl.getBoundingClientRect(), out = [];
    for(const e of document.querySelectorAll(OVERLAY_SEL)){
      if(markersEl.contains(e)) continue;
      const r = e.getBoundingClientRect();
      if(!r.width || !r.height || r.right <= base.left || r.left >= base.right || r.bottom <= base.top || r.top >= base.bottom) continue;
      out.push({x: r.left - base.left - 4, y: r.top - base.top - 4, w: r.width + 8, h: r.height + 8});
    }
    return out;
  }
  function draw(){
    if(!markersEl) return;
    const t0 = performance.now();
    const groups = clusters();
    const html = [];
    const placed = [];   // lapper plassert, til kollisjonssjekk
    // hindre for lappene: prikker (14 px) og klyngeringer (34 px), og det som ligger over kartet - kildemerket,
    // tids- og regionbrikkene og andre knapper (Theodor 16.10: kildemerket kolliderte med Farstadsanden-lappen på PC)
    const dots = groups.map(g=> g.members.length > 1 ? {x: g.x - 17, y: g.y - 17, w: 34, h: 34} : {x: g.x - 7, y: g.y - 7, w: 14, h: 14});
    dots.push(...overlays());
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
    markersEl.dataset.ms = (performance.now() - t0).toFixed(1);   // testene måler klyngetiden her
  }
  function extentOf(ids){
    const pts = spots.filter(p=> ids.includes(p.id) && !p.offMap);
    if(!pts.length) return null;
    const la = pts.map(p=>p.lat), lo = pts.map(p=>p.lon);
    const dl = Math.max(0.03, (Math.max(...la) - Math.min(...la)) * 0.6), dn = Math.max(0.08, (Math.max(...lo) - Math.min(...lo)) * 0.6);
    return [Math.min(...la) - dl, Math.min(...lo) - dn, Math.max(...la) + dl, Math.max(...lo) + dn];
  }
  // miniatyren på Hjem (PC): bare coast.json (SVG), ingen MapLibre
  function thumb(colorOf, list){
    const pts = (list || []).map(s=>({s, id: s.id, lat: s.spot && s.spot.lat, lon: s.spot && s.spot.lon})).filter(p=> p.lat!=null && p.lon!=null);
    return Lag.thumbSvg(pts, (p)=> colorOf(p));
  }
  // åpnes appen rett på Utforsk, lastes MapLibre parallelt med varseldataene i stedet for etter dem
  if(/^#utforsk/.test(location.hash)) loadLib().catch(()=>{});
  window.addEventListener("hashchange", ()=>{ if(/^#utforsk/.test(location.hash)) loadLib().catch(()=>{}); });
  window.Kart = { lag: Lag, init, loadLib, setCoast, setArea, setExtent: (e, a)=> Lag.setExtent(e, a), setSelected, redraw: ()=> draw(), offMapSpots, screenOf, extentOf, thumb, covers: (la, lo)=> Lag.covers(la, lo) };
})();
