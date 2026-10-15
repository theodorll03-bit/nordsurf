/* Nordsurf: kartmotoren for Utforsk (Theodor 14.10.2026, punkt 3; bygget om
   fra «kart først» 09.10.2026).

   Vektorkyst (docs/geo/coast.json, forenklet GSHHS for Nord-Norge - MapLibre
   og Kartverkets/OSM-kyst hører til S3) tegnet som SVG i ett lag som flyttes/
   zoomes med CSS-transform. Merkene ligger i skjermrommet som ekte knapper:
   hele merket (prikk og lapp) er én 44 px høy knapp, lappen «Navn Ord» er
   28 px. Lappene kolliderer ikke (venstre/høyre/forskjøvet per spot); blir det
   trangt, vises bare prikker - valgt spot beholder navnet.

   Ren visning: fargen og ordet per merke kommer fra utforsk.js (valgt dag),
   aldri regnet her. Mangler tallet: stiplet prikk og «–». */
(function(){
  const VW = 1000, VH = 844;
  const EASE = "cubic-bezier(.2,.8,.2,1)";
  const merc = (lat)=> Math.log(Math.tan(Math.PI/4 + lat*Math.PI/360));
  const PH = 28, GAP = 14;   // lappens høyde, avstand prikksentrum -> lappekant
  let root, mapLayer, svg, markersEl;
  let coast = null, spots = [], proj = null;
  let state = { view:"nord", selected:null, area:{x:0, y:0, w:390, h:600} };
  let cur = { cx:0, cy:0, sc:1 }, prevT = null, crisp = false;
  let valueOf = (p)=>({st:0, word:"", miss:false, aria:p.name});
  let onPick = ()=>{};
  const esc = (s)=> String(s).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const reduced = ()=> matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- projeksjon og utsnitt ---------- */
  function makeProj(c){
    const [w0, s0, e0, n0] = c.bbox, mN = merc(n0), mS = merc(s0);
    return { x: (lon)=> (lon - w0) / (e0 - w0) * c.vw, y: (lat)=> (mN - merc(lat)) / (mN - mS) * c.vh, bbox: c.bbox };
  }
  const onMap = (p)=> p.x >= 0 && p.x <= VW && p.y >= 0 && p.y <= VH;
  function fit(points, pad){
    const xs = points.map(p=>p.x), ys = points.map(p=>p.y);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const a = state.area, w = Math.max(60, x1 - x0), hgt = Math.max(60, y1 - y0);
    const sc = Math.min((a.w - 2*pad) / w, (a.h - 2*pad) / hgt);
    return { cx: (x0+x1)/2, cy: (y0+y1)/2, sc: Math.max(0.3, Math.min(8, sc)) };
  }
  function viewPoints(view){
    const on = spots.filter(p=>!p.offMap);
    const lof = on.filter(p=>/lofoten/i.test(p.area)), nord = on.filter(p=>!/lofoten/i.test(p.area));
    if(view==="lofoten" && lof.length) return lof;
    if(view==="alle") return on;
    return nord.length ? nord : on;
  }
  const viewSpotIds = (view)=> new Set(viewPoints(view).map(p=>p.id));
  const viewFor = (view)=> fit(viewPoints(view), Math.min(120, state.area.w*0.18));
  function cssTransform(){ const a = state.area, ox = a.x + a.w/2, oy = a.y + a.h/2; return { tx: ox - cur.cx*cur.sc, ty: oy - cur.cy*cur.sc, sc: cur.sc }; }
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
    // skarp tegning når kartet står stille: utsnittet i viewBox i stedet for CSS-skalering
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
      mapLayer.style.transition = `transform .9s ${EASE}`;
      mapLayer.style.transform = `translate(${t.tx.toFixed(1)}px, ${t.ty.toFixed(1)}px) scale(${t.sc.toFixed(4)})`;
    } else { prevT = t; crispen(); }
    prevT = t;
    placeMarkers(animate && !reduced());
  }

  /* ---------- oppsett ---------- */
  function init(el, data, coastJson, o){
    root = el; coast = coastJson; proj = makeProj(coast);
    valueOf = o.valueOf || valueOf; onPick = o.onPick || onPick;
    spots = data.spots.map(s=>{
      const lat = s.spot && s.spot.lat, lon = s.spot && s.spot.lon;
      const p = { s, id:s.id, name:s.name, area:s.area||"", x: lon!=null ? proj.x(lon) : -9999, y: lat!=null ? proj.y(lat) : -9999 };
      p.offMap = !(lat!=null && lon!=null && onMap(p));
      return p;
    });
    root.innerHTML = `<div class="map-layer" id="mapLayer"><svg id="mapSvg" width="${VW}" height="${VH}" viewBox="0 0 ${VW} ${VH}" aria-hidden="true" style="overflow:visible;display:block"><path class="coast" d="${coast.d}"/></svg></div><div class="markers" id="markersLayer"></div>`;
    mapLayer = root.querySelector("#mapLayer"); svg = root.querySelector("#mapSvg"); markersEl = root.querySelector("#markersLayer");
    markersEl.innerHTML = spots.filter(p=>!p.offMap).map(p=>`<button type="button" class="mk bare" data-id="${esc(p.id)}" aria-label="${esc(p.name)}"><span class="mk-dot"></span><span class="mk-pill"><span class="nm">${esc(p.name)}</span><span class="ord"></span></span></button>`).join("");
    markersEl.querySelectorAll(".mk").forEach(b=> b.onclick = ()=> onPick(b.dataset.id));
    mapLayer.addEventListener("transitionend", (e)=>{ if(e.target===mapLayer && e.propertyName==="transform") crispen(); });
  }
  function setArea(area, animate){ state.area = area; recenter(animate); }
  function setView(view, animate){ state.view = view; recenter(animate); }
  function recenter(animate){ cur = viewFor(state.view); applyTransform(animate!==false); }
  function setSelected(id){ state.selected = id; recolor(); }

  /* ---------- merkene ---------- */
  function recolor(){
    spots.forEach(p=>{
      const mk = markersEl.querySelector(`.mk[data-id="${p.id}"]`); if(!mk) return;
      const v = valueOf(p);
      const sel = state.selected===p.id;
      mk.classList.remove("r-0","r-1","r-2","r-3","r-4","r-5");
      mk.classList.add(`r-${Math.min(5, v.st||0)}`);
      mk.classList.toggle("miss", !!v.miss);
      mk.classList.toggle("sel", sel);
      mk.querySelector(".ord").textContent = v.miss ? "–" : (v.word || "");
      mk.setAttribute("aria-label", v.aria || p.name);
      mk.setAttribute("aria-pressed", String(sel));
      mk._st = v.st||0; mk._sel = sel;
    });
    layoutPills();
  }
  const prio = (mk)=> (mk._sel ? 1000 : 0) + (mk._st || 0);
  const hitRect = (r, list)=> list.some(q=> r.x < q.x+q.w && r.x+r.w > q.x && r.y < q.y+q.h && r.y+r.h > q.y);
  const pillWidth = (mk)=> 22 + mk.querySelector(".nm").textContent.length*7.6 + Math.max(0, mk.querySelector(".ord").textContent.length*6.6 + 6);
  function layoutPills(){
    // alle merker vil ha lapp; et lite søk finner en plassering uten kollisjon for alle samlet
    // (andre prikker er hindre, lappen nærmere egen prikk enn noen annen). Går det ikke:
    // de viktigste først (valgt, flest stjerner), resten som prikk uten lapp.
    const a = state.area;
    const inside = [...markersEl.querySelectorAll(".mk")].filter(m=>m._inside);
    const mks = [...inside].sort((x, y)=> prio(y) - prio(x));
    const dots = inside.map(m=>({id: m.dataset.id, x: m._sx-7, y: m._sy-7, w: 14, h: 14}));
    const distRP = (r, x, y)=> Math.hypot(Math.max(r.x - x, 0, x - (r.x + r.w)), Math.max(r.y - y, 0, y - (r.y + r.h)));
    const cands = mks.map(mk=>{
      const w = pillWidth(mk);
      let preferLeft = mk._sx > a.x + a.w*0.62;
      const near = dots.filter(d=> d.id!==mk.dataset.id && Math.abs(d.y + 7 - mk._sy) < PH + 12 && Math.abs(d.x + 7 - mk._sx) < w + 2*GAP + 12);
      if(near.length){ const east = near.some(d=>d.x + 7 > mk._sx), west = near.some(d=>d.x + 7 < mk._sx); if(east && !west) preferLeft = true; else if(west && !east) preferLeft = false; }
      const sides = preferLeft ? ["left","right"] : ["right","left"];
      const out = [];
      for(const dy of [0, -14, 14, -24, 24]) for(const side of sides){
        const x = side==="right" ? mk._sx + GAP : mk._sx - GAP - w;
        if(x < a.x + 4 || x + w > a.x + a.w - 4) continue;
        out.push({side, r:{x, y: mk._sy - PH/2 + dy, w, h: PH}});
      }
      for(const dy of [-(PH/2 + 12), PH/2 + 12]){ const x = Math.max(a.x + 4, Math.min(a.x + a.w - 4 - w, mk._sx - w/2)); out.push({side:"vert", r:{x, y: mk._sy - PH/2 + dy, w, h: PH}}); }
      return out;
    });
    const chosen = new Array(mks.length).fill(null); let nodes = 0;
    const ok = (i, c)=>{
      const others = dots.filter(d=>d.id!==mks[i].dataset.id);
      if(hitRect(c.r, others)) return false;
      const own = distRP(c.r, mks[i]._sx, mks[i]._sy);
      if(others.some(d=> distRP(c.r, d.x + 7, d.y + 7) <= own)) return false;
      for(let j=0;j<i;j++) if(chosen[j] && hitRect(c.r, [chosen[j].r])) return false;
      return true;
    };
    const dfs = (i)=>{ if(i===mks.length) return true; for(const c of cands[i]){ if(++nodes > 20000) return false; if(!ok(i, c)) continue; chosen[i] = c; if(dfs(i+1)) return true; chosen[i] = null; } return false; };
    let pass = mks.length ? "strict" : "none";
    if(mks.length && !dfs(0)){ pass = "dense"; chosen.fill(null); for(let i=0;i<mks.length;i++) chosen[i] = cands[i].find(c=>ok(i, c)) || (mks[i]._sel ? cands[i][0] : null); }
    markersEl.dataset.pills = pass;
    mks.forEach((mk, i)=>{
      const c = chosen[i];
      mk.classList.toggle("bare", !c);
      mk.classList.toggle("left", !!c && c.side==="left");
      mk.classList.toggle("vert", !!c && c.side==="vert");
      if(c){ mk.style.setProperty("--lx", (c.r.x - (mk._sx - 22)).toFixed(1)+"px"); mk.style.setProperty("--ly", (c.r.y - (mk._sy - 22)).toFixed(1)+"px"); }
    });
  }
  function placeMarkers(animate){
    const a = state.area, ox = a.x + a.w/2, oy = a.y + a.h/2;
    spots.forEach(p=>{
      const mk = markersEl.querySelector(`.mk[data-id="${p.id}"]`); if(!mk) return;
      const sx = ox + (p.x - cur.cx)*cur.sc, sy = oy + (p.y - cur.cy)*cur.sc;
      const inside = sx >= a.x+12 && sx <= a.x+a.w-12 && sy >= a.y+12 && sy <= a.y+a.h-12;
      mk.hidden = !inside;
      mk.style.transition = animate ? `transform .9s ${EASE}` : "none";
      mk.style.transform = `translate3d(${(sx-22).toFixed(1)}px, ${(sy-22).toFixed(1)}px, 0)`;
      mk._sx = sx; mk._sy = sy; mk._inside = inside;
    });
    layoutPills();
  }
  const screenOf = (id)=>{ const mk = markersEl && markersEl.querySelector(`.mk[data-id="${id}"]`); return mk ? {x: mk._sx, y: mk._sy, inside: mk._inside} : null; };
  const spotInfo = (id)=> spots.find(p=>p.id===id) || null;
  const offMapSpots = ()=> spots.filter(p=>p.offMap);
  // lite oversiktskart til Hjem på nett: kysten og prikkene i ratingfargen nå
  function thumb(colorOf){
    if(!coast) return "";
    const pts = spots.filter(p=>!p.offMap);
    const xs = pts.map(p=>p.x), ys = pts.map(p=>p.y);
    const x0 = Math.min(...xs) - 90, x1 = Math.max(...xs) + 90, y0 = Math.min(...ys) - 70, y1 = Math.max(...ys) + 70;
    return `<svg viewBox="${x0.toFixed(0)} ${y0.toFixed(0)} ${(x1-x0).toFixed(0)} ${(y1-y0).toFixed(0)}" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><path class="coast" d="${coast.d}"/>${pts.map(p=>`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="6" class="r-${Math.min(5, colorOf(p))}" style="fill:var(--rc);stroke:var(--raised);stroke-width:2"/>`).join("")}</svg>`;
  }
  window.Kart = { init, setArea, setView, setSelected, recolor, viewSpotIds, spotInfo, screenOf, offMapSpots, thumb, relayout: ()=>placeMarkers(false) };
})();
