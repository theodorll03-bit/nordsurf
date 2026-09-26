/* ---------- Kart ----------
   Bruker DATA, $, esc, nf1, nf0, fmtHour, fmtTime, relDay, dayKey, compass,
   WIND_WORD, windLabel, lightClass, starsSVG, STAR_PATH, TZ, openBreakdown
   fra hovedskriptet (samme dokument, lastet før dette). Ikke en modul -
   vanlig <script> med tilgang til de samme globalene. */
(function(){
"use strict";

const D2R = Math.PI/180;
const EXPLAIN_KEY = "nordsurf.mapExplainSeen.v1";
const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- Geometri ---------- */
function polar(cx, cy, r, bearingDeg){
  const rad = bearingDeg*D2R;
  return {x: cx + r*Math.sin(rad), y: cy - r*Math.cos(rad)};
}
function norm360(d){ return ((d%360)+360)%360; }
function shortestDelta(from, to){
  let d = norm360(to) - norm360(from);
  if(d > 180) d -= 360;
  if(d < -180) d += 360;
  return d;
}
function sectorPath(cx, cy, r, a, b){
  let start = norm360(a), end = norm360(b);
  if(end <= start) end += 360;
  const large = (end-start) > 180 ? 1 : 0;
  const p0 = polar(cx,cy,r,start), p1 = polar(cx,cy,r,end);
  return `M${cx},${cy} L${p0.x.toFixed(2)},${p0.y.toFixed(2)} A${r},${r} 0 ${large} 1 ${p1.x.toFixed(2)},${p1.y.toFixed(2)} Z`;
}
function windowSectors(spot){
  const w = spot.swell_window; if(!w) return [];
  return Array.isArray(w[0]) ? w : [w];
}
function windowText(spot){
  const secs = windowSectors(spot);
  return secs.map(([a,b])=>`${a}–${b}°`).join(", ");
}
function arcPath(cx, cy, r, a, b){
  const p0 = polar(cx,cy,r,a), p1 = polar(cx,cy,r,b);
  const large = (b-a) > 180 ? 1 : 0;
  return `M${p0.x.toFixed(2)},${p0.y.toFixed(2)} A${r},${r} 0 ${large} 1 ${p1.x.toFixed(2)},${p1.y.toFixed(2)}`;
}
function ringSegments(cx, cy, r, stars, faded, clsPrefix){
  const n = 5, gap = 7, step = 360/n;
  let out = "";
  for(let i=0;i<n;i++){
    const a = i*step + gap/2, b = (i+1)*step - gap/2;
    const cls = i < stars ? "solid" : i < stars+faded ? "faded" : "empty";
    out += `<path class="${clsPrefix} ${cls}" d="${arcPath(cx,cy,r,a,b)}"/>`;
  }
  return out;
}
function crestArc(cx, cy, bearingDeg, halfWidth){
  const perpRad = (bearingDeg+90)*D2R;
  const px = Math.sin(perpRad)*halfWidth, py = -Math.cos(perpRad)*halfWidth;
  const x1=cx-px, y1=cy-py, x2=cx+px, y2=cy+py;
  const bulge = halfWidth*0.7;
  const bx = Math.sin(bearingDeg*D2R)*bulge, by = -Math.cos(bearingDeg*D2R)*bulge;
  return `M${x1.toFixed(2)},${y1.toFixed(2)} Q${(cx+bx).toFixed(2)},${(cy+by).toFixed(2)} ${x2.toFixed(2)},${y2.toFixed(2)}`;
}
function inwardVec(bearingDeg, d){
  return {dx: -d*Math.sin(bearingDeg*D2R), dy: d*Math.cos(bearingDeg*D2R)};
}
function arrowHead(baseX, baseY, bearingDeg, len){
  const tip = {x: baseX+len*Math.sin(bearingDeg*D2R), y: baseY-len*Math.cos(bearingDeg*D2R)};
  const back = len*0.65;
  const c1 = {x: baseX+back*Math.sin((bearingDeg+150)*D2R), y: baseY-back*Math.cos((bearingDeg+150)*D2R)};
  const c2 = {x: baseX+back*Math.sin((bearingDeg-150)*D2R), y: baseY-back*Math.cos((bearingDeg-150)*D2R)};
  return `M${tip.x.toFixed(2)},${tip.y.toFixed(2)} L${c1.x.toFixed(2)},${c1.y.toFixed(2)} L${baseX.toFixed(2)},${baseY.toFixed(2)} L${c2.x.toFixed(2)},${c2.y.toFixed(2)} Z`;
}

/* ---------- Delt tidslinje ---------- */
let TIMELINE = [];
function buildTimeline(){
  let longest = DATA.spots[0];
  for(const s of DATA.spots) if(s.hours.length > longest.hours.length) longest = s;
  TIMELINE = longest.hours.map(h=>h.t);
}
function hourAt(spot, idx){
  const t = TIMELINE[idx];
  if(!t) return null;
  return spot.hours.find(h=>h.t===t) || null;
}
function defaultIdx(){
  const now = Date.now();
  let idx = TIMELINE.findIndex(t => new Date(t).getTime() + 36e5 > now);
  return Math.max(0, idx);
}
function globalBwUntil(){
  const vals = DATA.spots.map(s=>s.bw_until).filter(Boolean);
  return vals.length ? vals.sort()[0] : null;
}

/* ---------- Tilstand ---------- */
const mapState = { idx: 0, spotId: null, sheetOpen: false, explainOpen: false, inited: false };
let map, markersLayer, discLayer, discMarker;

/* ---------- Leaflet-kart ---------- */
function initMap(){
  if(mapState.inited) return;
  mapState.inited = true;
  buildTimeline();
  mapState.idx = defaultIdx();

  // Vanlig Leaflet har ingen kompassretning å rotere - nord er alltid opp uten noe eget oppsett.
  map = L.map($("#mapEl"), {
    zoomControl: true,
    attributionControl: true,
    worldCopyJump: true,
  });
  L.tileLayer("https://cache.kartverket.no/v1/wmts/1.0.0/topograatone/default/webmercator/{z}/{y}/{x}.png", {
    maxZoom: 18, minZoom: 4, tileSize: 256,
    attribution: '&copy; <a href="https://www.kartverket.no" target="_blank" rel="noopener">Kartverket</a>',
  }).addTo(map);

  markersLayer = L.layerGroup().addTo(map);
  discLayer = L.layerGroup().addTo(map);

  const bounds = L.latLngBounds(DATA.spots.map(s=>[s.spot.lat, s.spot.lon]));
  map.fitBounds(bounds, {padding:[56,56]});

  map.on("moveend zoomend", renderMarkers);
  map.on("click", onMapBackgroundClick);

  buildTimeSlider();
  renderMarkers();
  maybeShowExplainAuto();
}

function onMapBackgroundClick(){
  // Leaflet-markører har bubblingMouseEvents:false som standard, så klikk
  // på et merke/skive når aldri hit - bare et faktisk tomt kart gjør det.
  if(mapState.sheetOpen){ closeMapSheet(); return; }
  if(mapState.spotId != null){ selectSpot(null); }
}

/* ---------- Merker og samling ---------- */
function dist(a,b){ return Math.hypot(a.x-b.x, a.y-b.y); }

function computeGroups(){
  const pts = DATA.spots.map((s,i)=>({s,i,pt: map.latLngToContainerPoint([s.spot.lat, s.spot.lon])}));
  const THRESH = 60;
  const used = new Array(pts.length).fill(false);
  const groups = [];
  for(let i=0;i<pts.length;i++){
    if(used[i]) continue;
    const group=[pts[i]]; used[i]=true;
    let grew = true;
    while(grew){
      grew = false;
      for(let j=0;j<pts.length;j++){
        if(used[j]) continue;
        if(group.some(g=>dist(g.pt, pts[j].pt) < THRESH)){ group.push(pts[j]); used[j]=true; grew=true; }
      }
    }
    groups.push(group);
  }
  return groups;
}

function heightText(h){
  if(!h) return "–";
  if(h.likely_flat) return "Flatt";
  if(h.height==null) return "–";
  return nf1.format(h.height)+" m";
}

function markerLabel(spot, h){
  const stars = h ? h.stars : 0;
  const heightTxt = h ? heightText(h) : "ingen data";
  return `${spot.name}, ${stars} av 5 stjerner, ${heightTxt}`;
}

const MOON = `<svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path fill="var(--muted)" d="M12 2a10 10 0 1 0 9.8 12A8 8 0 0 1 12 2z"/></svg>`;

function soloMarkerHtml(spot, h, showName){
  const stars = h ? h.stars : 0, faded = h ? h.faded : 0;
  const night = h && (h.light==="mørkt" || h.daylight===false);
  const good = stars >= 3;
  const r = good ? 16 : 14, size = good ? 36 : 32, cx = size/2, cy = size/2;
  const ring = `<svg class="ring" viewBox="0 0 ${size} ${size}">${ringSegments(cx,cy,r-3, stars, faded, "mm-seg")}<text x="${cx}" y="${cy+4}" text-anchor="middle" font-size="12" font-weight="700" fill="var(--ink)">${stars}</text></svg>`;
  const cls = ["spot-mark", good?"good":"", night?"night":"", showName?"show-name":""].filter(Boolean).join(" ");
  return `<button type="button" class="${cls}" aria-label="${esc(markerLabel(spot,h))}" tabindex="0">
    <span class="plate" style="position:relative">${night?MOON:""}${ring}<span class="mm-h">${esc(heightText(h))}</span></span>
    <span class="name">${esc(spot.name)}</span>
  </button>`;
}
function clusterMarkerHtml(group){
  const hs = group.map(g=>hourAt(g.s, mapState.idx));
  const best = Math.max(0, ...hs.map(h=>h?h.stars:0));
  const n = group.length;
  return `<button type="button" class="cluster-mark" aria-label="${n} spots, beste ${best} av 5 stjerner. Trykk for å zoome inn." tabindex="0">
    <span class="plate"><svg class="ring" viewBox="0 0 26 26">${ringSegments(13,13,10,best,0,"mm-seg")}</svg>${n} spots</span>
  </button>`;
}

function shouldShowNames(){
  const z = map.getZoom();
  return z >= 9;
}

function renderMarkers(){
  if(!map) return;
  markersLayer.clearLayers();
  const groups = computeGroups();
  const showNames = shouldShowNames();
  const selected = mapState.spotId;
  const selectedLatLng = selected!=null ? DATA.spots.find(s=>s.id===selected) : null;
  const selPt = selectedLatLng ? map.latLngToContainerPoint([selectedLatLng.spot.lat, selectedLatLng.spot.lon]) : null;

  for(const group of groups){
    if(group.length > 1){
      const anyIsSelected = selected!=null && group.some(g=>g.s.id===selected);
      if(anyIsSelected){
        // selected spot ble alene igjen (zoomet inn) - tegn den solo i stedet, se under
      } else {
        const centroid = group.reduce((a,g)=>[a[0]+g.s.spot.lat/group.length, a[1]+g.s.spot.lon/group.length], [0,0]);
        const m = L.marker(centroid, {
          icon: L.divIcon({html: clusterMarkerHtml(group), className:"cluster-icon", iconSize:[0,0], iconAnchor:[0,0]}),
          keyboard:false, interactive:true,
        }).addTo(markersLayer);
        const clusterEl = m.getElement().querySelector(".cluster-mark");
        clusterEl.onclick = (ev)=>{
          ev.stopPropagation();
          const b = L.latLngBounds(group.map(g=>[g.s.spot.lat, g.s.spot.lon]));
          map.flyToBounds(b, {padding:[70,70], duration: reduceMotion()?0:0.5});
        };
        continue;
      }
    }
    for(const g of group){
      const spot = g.s, h = hourAt(spot, mapState.idx);
      const isSelected = selected === spot.id;
      if(isSelected) continue; // eget merke skjules mens skiva er åpen
      const pt = map.latLngToContainerPoint([spot.spot.lat, spot.spot.lon]);
      const SAFE_DIST = 150; // skivas radius (~100px) + luft + eget merke
      const gapToDisc = selPt ? dist(pt, selPt) : Infinity;
      const nearSelected = gapToDisc < SAFE_DIST;
      const m = L.marker([spot.spot.lat, spot.spot.lon], {
        icon: L.divIcon({html: soloMarkerHtml(spot, h, showNames), className:"spot-icon", iconSize:[0,0], iconAnchor:[0,0]}),
        keyboard:false,
      }).addTo(markersLayer);
      const el = m.getElement().querySelector(".spot-mark");
      if(selected!=null) el.classList.add("dim");
      if(nearSelected && gapToDisc > 0){
        // For tett på skiva - flytt merket radielt utover i stedet for å skjule
        // det, så man fortsatt ser at det ikke overlapper. Klem til synlig
        // kartflate, så det ikke havner utenfor skjermen i trange hjørner.
        const ux = (pt.x-selPt.x)/gapToDisc, uy = (pt.y-selPt.y)/gapToDisc;
        const size = map.getSize();
        const margin = 30;
        const targetX = Math.min(size.x-margin, Math.max(margin, selPt.x+ux*SAFE_DIST));
        const targetY = Math.min(size.y-margin, Math.max(margin, selPt.y+uy*SAFE_DIST));
        el.style.setProperty("--push-x", (targetX-pt.x).toFixed(1)+"px");
        el.style.setProperty("--push-y", (targetY-pt.y).toFixed(1)+"px");
      }
      el.onclick = (ev)=>{ ev.stopPropagation(); selectSpot(spot.id); };
    }
  }
}

/* ---------- Skive ---------- */
function discAriaLabel(spot, h, t){
  if(!h) return `${spot.name}. Ingen data for valgt tidspunkt.`;
  const dir = h.dir_offshore;
  const miss = h.directness!=null && h.directness < 0.667;
  const swellTxt = dir==null ? "Retning ukjent." : `Svell ${h.swell_offshore!=null?nf1.format(h.swell_offshore)+" meter":""} fra ${compass(dir)}, ${Math.round(dir)} grader, ${miss?"treffer ikke":"treffer"} vinduet ${windowText(spot)} grader.`;
  const windTxt = h.wind_speed!=null ? `Vind ${nf0.format(h.wind_speed)} meter per sekund fra ${compass(h.wind_dir)}, ${windLabel(h)}.` : "";
  const flatTxt = h.likely_flat ? " Trolig flatt." : "";
  return `${spot.name} kl. ${fmtHour.format(t)}. ${swellTxt} ${windTxt} ${h.stars} av 5 stjerner.${flatTxt}`;
}

function discSvgMarkup(spot, h){
  const cx=100, cy=100;
  const secs = windowSectors(spot);
  const windowPaths = secs.map(([a,b])=>`<path class="disc-window" d="${sectorPath(cx,cy,84,a,b)}"/>`).join("");

  let swellMarkup = "";
  if(h){
    const dir = h.dir_offshore;
    const dn = h.directness;
    const missing = dir==null;
    const cls = missing || dn==null || dn < 0.667 ? "miss" : dn >= 0.999 ? "" : "edge";
    const bearing = missing ? 0 : dir;
    const rEdge = 96, rInner = 18;
    const p0 = polar(cx,cy,rEdge,bearing), p1 = polar(cx,cy,rInner,bearing);
    const period = h.period || 10;
    const height = h.swell_offshore || h.height_offshore || 0;
    const spacing = Math.max(9, Math.min(22, period*1.4));
    const len = Math.hypot(p1.x-p0.x, p1.y-p0.y);
    const count = Math.max(2, Math.round(len/spacing));
    const unitIn = {x: -Math.sin(bearing*D2R), y: Math.cos(bearing*D2R)};
    let crests = "";
    for(let i=1;i<=count+1;i++){
      const px = p0.x+unitIn.x*spacing*i, py = p0.y+unitIn.y*spacing*i;
      crests += `<path class="disc-swell-crest ${cls}" d="${crestArc(px,py,bearing, 5+Math.min(6,height*3))}"/>`;
    }
    const roll = inwardVec(bearing, spacing);
    const crestGroup = `<g class="disc-crests ${cls}" style="--dx:${roll.dx.toFixed(2)}px;--dy:${roll.dy.toFixed(2)}px;animation-duration:${Math.max(0.6,Math.min(3,period/8))}s">${crests}</g>`;
    const line = missing
      ? `<line class="disc-swell miss" x1="${cx}" y1="${cy-96}" x2="${cx}" y2="${cy-18}"/>`
      : `<line class="disc-swell ${cls}" x1="${p0.x.toFixed(2)}" y1="${p0.y.toFixed(2)}" x2="${p1.x.toFixed(2)}" y2="${p1.y.toFixed(2)}"/>`;
    const below = bearing>90 && bearing<270;
    // Alltid retning i grader og kompassretning ved svellinja, så det er lett
    // å sammenligne med f.eks. Windy - uansett om svellet treffer eller ikke.
    const dirLabel = missing ? "" : `<text class="disc-dir-label" x="${p0.x.toFixed(2)}" y="${(p0.y+(below?14:-8)).toFixed(2)}" text-anchor="middle">fra ${compass(dir)}, ${Math.round(dir)}°</text>`;
    const missLabel = (!missing && cls==="miss") ? `<text class="disc-miss-label" x="${p0.x.toFixed(2)}" y="${(p0.y+(below?28:-22)).toFixed(2)}" text-anchor="middle">Treffer ikke</text>` : "";
    swellMarkup = `<g class="disc-swellgroup" data-bearing="${bearing}">${line}${missing?"":crestGroup}${dirLabel}${missLabel}</g>`;
  }

  let windMarkup = "";
  if(h && h.wind_speed!=null){
    const toBearing = norm360((h.wind_dir||0)+180);
    const fromPt = polar(cx,cy,92,norm360(toBearing+180));
    const toPt = polar(cx,cy,72,toBearing);
    const w = Math.max(2, Math.min(6, 2+h.wind_speed*0.35));
    const dur = Math.max(0.4, Math.min(2.2, 3/(h.wind_speed||1)));
    const tickSpacing = 14, tickLen = 6;
    const totalLen = Math.hypot(toPt.x-fromPt.x, toPt.y-fromPt.y);
    const tickCount = Math.max(2, Math.round(totalLen/tickSpacing));
    const unitDown = {x: Math.sin(toBearing*D2R), y: -Math.cos(toBearing*D2R)};
    let ticks = "";
    for(let i=0;i<=tickCount+1;i++){
      const px = fromPt.x+unitDown.x*tickSpacing*i, py = fromPt.y+unitDown.y*tickSpacing*i;
      const tx = px+unitDown.x*tickLen, ty = py+unitDown.y*tickLen;
      ticks += `<line class="disc-wind-tick" x1="${px.toFixed(2)}" y1="${py.toFixed(2)}" x2="${tx.toFixed(2)}" y2="${ty.toFixed(2)}" stroke-width="${w}"/>`;
    }
    windMarkup = `<g class="disc-windgroup" data-bearing="${toBearing}">
      <line class="disc-wind-base" x1="${fromPt.x.toFixed(2)}" y1="${fromPt.y.toFixed(2)}" x2="${toPt.x.toFixed(2)}" y2="${toPt.y.toFixed(2)}" stroke-width="1.5" opacity=".35"/>
      <g class="disc-wind-ticks" style="--dx:${(unitDown.x*tickSpacing).toFixed(2)}px;--dy:${(unitDown.y*tickSpacing).toFixed(2)}px;animation-duration:${dur}s">${ticks}</g>
      <path class="disc-wind-head" d="${arrowHead(toPt.x, toPt.y, toBearing, 10)}"/>
    </g>`;
  }

  const ring = ringSegments(cx,cy,94, h?h.stars:0, h?h.faded:0, "disc-ring-seg");

  return `<svg viewBox="0 0 200 200">
    <g class="disc-windowgroup">${windowPaths}</g>
    ${swellMarkup}
    ${windMarkup}
    <g>${ring}</g>
  </svg>`;
}

function discPlateMarkup(spot, h){
  const flat = h && h.likely_flat;
  const big = h ? (flat ? "Trolig flatt" : (h.height!=null?nf1.format(h.height)+" m":"–")) : "–";
  const period = h && h.period!=null ? `${nf0.format(h.period)} s` : "";
  const night = h && (h.light==="mørkt" || h.daylight===false);
  const src = h ? (h.height_source==="barentswatch" ? "BarentsWatch" : "anslag") : "";
  const max = h && h.bw_height_max!=null ? `<div class="max">Sett opp til ${nf1.format(h.bw_height_max)} m</div>` : "";
  return `<div class="big">${esc(big)}</div>
    <div class="mid">${[period, night?"Mørkt":""].filter(Boolean).join(" · ")}</div>
    ${max}
    <div class="src">${esc(src)} <span class="chev" aria-hidden="true">›</span></div>`;
}

function selectSpot(spotId){
  mapState.spotId = spotId;
  if(spotId == null){
    if(discMarker){ discLayer.removeLayer(discMarker); discMarker = null; }
    closeMapSheet();
    renderMarkers();
    return;
  }
  const spot = DATA.spots.find(s=>s.id===spotId);
  const h = hourAt(spot, mapState.idx);
  const t = new Date(TIMELINE[mapState.idx]);

  const html = `<div style="position:relative;pointer-events:none">
      <div class="disc-wrap hit disc-enter" tabindex="0" role="button" aria-label="${esc(discAriaLabel(spot,h,t))}">${discSvgMarkup(spot,h)}</div>
      <div class="disc-plate" style="top:110px">${discPlateMarkup(spot,h)}</div>
    </div>`;

  if(discMarker) discLayer.removeLayer(discMarker);
  discMarker = L.marker([spot.spot.lat, spot.spot.lon], {
    icon: L.divIcon({html, className:"disc-icon", iconSize:[0,0], iconAnchor:[0,0]}),
    zIndexOffset: 1000, keyboard:false,
  }).addTo(discLayer);
  {
    const el = discMarker.getElement();
    el.querySelector(".disc-wrap").onclick = (ev)=>{ ev.stopPropagation(); openMapSheet(spot.id); };
    el.querySelector(".disc-plate").onclick = (ev)=>{ ev.stopPropagation(); openMapSheet(spot.id); };
    if(reduceMotion()) el.querySelector(".disc-wrap").classList.remove("disc-enter");
  }

  const targetZoom = Math.max(map.getZoom(), 10);
  const targetPoint = map.project([spot.spot.lat, spot.spot.lon], targetZoom).subtract([0, mapState.sheetOpen ? 90 : 40]);
  const targetLatLng = map.unproject(targetPoint, targetZoom);
  map.flyTo(targetLatLng, targetZoom, {duration: reduceMotion()?0:0.5});

  renderMarkers();
  maybeShowExplainAuto();
  if(mapState.sheetOpen) fillMapSheet(spot, h);
}

function updateDiscForTime(){
  if(mapState.spotId == null || !discMarker) return;
  const spot = DATA.spots.find(s=>s.id===mapState.spotId);
  const h = hourAt(spot, mapState.idx);
  const t = new Date(TIMELINE[mapState.idx]);
  const el = discMarker.getElement();
  const wrap = el.querySelector(".disc-wrap");
  const oldSwell = wrap.querySelector(".disc-swellgroup");
  const oldWind = wrap.querySelector(".disc-windgroup");
  const oldSwellBearing = oldSwell ? parseFloat(oldSwell.dataset.bearing) : null;
  const oldWindBearing = oldWind ? parseFloat(oldWind.dataset.bearing) : null;
  wrap.innerHTML = discSvgMarkup(spot, h);
  wrap.setAttribute("aria-label", discAriaLabel(spot,h,t));
  if(!reduceMotion()){
    const ns = wrap.querySelector(".disc-swellgroup");
    if(ns && oldSwellBearing!=null){
      const newB = parseFloat(ns.dataset.bearing);
      const delta = shortestDelta(oldSwellBearing, newB);
      ns.style.transformOrigin = "100px 100px";
      ns.animate([{transform:`rotate(${(-delta).toFixed(2)}deg)`},{transform:"rotate(0deg)"}], {duration:400, easing:"ease"});
    }
    const nw = wrap.querySelector(".disc-windgroup");
    if(nw && oldWindBearing!=null){
      const newB = parseFloat(nw.dataset.bearing);
      const delta = shortestDelta(oldWindBearing, newB);
      nw.style.transformOrigin = "100px 100px";
      nw.animate([{transform:`rotate(${(-delta).toFixed(2)}deg)`},{transform:"rotate(0deg)"}], {duration:400, easing:"ease"});
    }
  }
  el.querySelector(".disc-plate").innerHTML = discPlateMarkup(spot, h);
  if(mapState.sheetOpen) fillMapSheet(spot, h);
}

/* ---------- Tidsvelger ---------- */
function lightCls(h){
  if(!h) return "";
  const l = h.light || (h.daylight===false ? "mørkt" : "dag");
  return l==="mørkt" ? "dark" : l==="skumring" ? "dusk" : "";
}
function buildTimeSlider(){
  const bw = globalBwUntil();
  const refSpot = DATA.spots.reduce((a,s)=>s.hours.length>a.hours.length?s:a, DATA.spots[0]);
  const track = TIMELINE.map((t,i)=>{
    const h = refSpot.hours.find(x=>x.t===t);
    const cls = [lightCls(h)];
    if(bw && t > bw && (i===0 || TIMELINE[i-1] <= bw)) cls.push("bwbreak");
    return `<span class="${cls.filter(Boolean).join(" ")}"></span>`;
  }).join("");
  $("#mapTimeTrack").innerHTML = track;
  const slider = $("#mapSlider");
  slider.min = 0; slider.max = TIMELINE.length-1; slider.value = mapState.idx;
  updateTimeLabel();
  updateThumb();
}
function updateTimeLabel(){
  const t = new Date(TIMELINE[mapState.idx]);
  $("#mapTimeLabel").textContent = `${relDay(t)} kl. ${fmtHour.format(t)}`;
  $("#mapNowBtn").hidden = mapState.idx === defaultIdx();
}
function updateThumb(){
  const pct = TIMELINE.length<=1 ? 0 : mapState.idx/(TIMELINE.length-1);
  $("#mapThumb").style.left = (pct*100)+"%";
}
function onSliderInput(){
  mapState.idx = +$("#mapSlider").value;
  updateTimeLabel(); updateThumb();
  renderMarkers();
  updateDiscForTime();
}

/* ---------- Ark ---------- */
function fillMapSheet(spot, h){
  const t = new Date(TIMELINE[mapState.idx]);
  $("#mSheetTitle").textContent = spot.name;
  const tideNow = h && h.tide ? `${h.tide.rising?"Stigende":"Fallende"}, ${h.tide.state}` : "–";
  $("#mSheetBody").innerHTML = `
    <button type="button" class="now" id="mSheetStars" aria-label="Hvorfor denne ratingen? Trykk for forklaring">${starsSVG(h?h.stars:0, h?h.faded:0, true)}</button>
    <p class="sub">${relDay(t)} kl. ${fmtHour.format(t)}</p>
    <div class="grid">
      <div class="cell"><div class="k">Høyde</div><div class="v">${heightText(h)}</div>${h&&h.bw_height_max!=null?`<div class="n">Sett opp til ${nf1.format(h.bw_height_max)} m</div>`:""}</div>
      <div class="cell"><div class="k">Periode</div><div class="v">${h&&h.period!=null?nf0.format(h.period)+" s":"–"}</div></div>
      <div class="cell"><div class="k">Vind</div><div class="v">${h&&h.wind_speed!=null?nf0.format(h.wind_speed)+" m/s":"–"}</div><div class="n">${h?windLabel(h):""}</div></div>
      <div class="cell"><div class="k">Tidevann</div><div class="v">${tideNow}</div></div>
    </div>
    <div class="row-btns" style="margin-top:16px">
      <button class="primary" id="mSheetDetail" style="min-height:44px">Åpne detaljside</button>
    </div>`;
  if(h && h.breakdown && h.breakdown.length) $("#mSheetStars").onclick = ()=>openBreakdown(h);
  $("#mSheetDetail").onclick = ()=>{
    closeMapSheet();
    state.tab = "varsel"; state.spot = DATA.spots.indexOf(spot); state.sel = spot.hours.indexOf(h) >=0 ? spot.hours.indexOf(h) : 0;
    render(); window.scrollTo(0,0);
  };
}
function openMapSheet(spotId){
  mapState.sheetOpen = true;
  if(mapState.explainOpen){ mapState.explainOpen = false; $("#mapExplain").hidden = true; }
  const spot = DATA.spots.find(s=>s.id===spotId);
  const h = hourAt(spot, mapState.idx);
  fillMapSheet(spot, h);
  $("#mScrim").classList.add("open");
  $("#mSheet").classList.add("open");
  $("#mSheet").setAttribute("aria-hidden","false");
  selectSpot(spotId);
}
function closeMapSheet(){
  mapState.sheetOpen = false;
  $("#mScrim").classList.remove("open");
  $("#mSheet").classList.remove("open");
  $("#mSheet").setAttribute("aria-hidden","true");
}

/* ---------- Forklaring ---------- */
function explainHtml(){
  return `<button class="close" id="mExplainClose" aria-label="Lukk forklaring">×</button>
    <div class="erow"><i class="sw" style="background:var(--window-fill);border:1.5px solid var(--window)"></i>Grønt: hvor svellet må komme fra</div>
    <div class="erow"><i class="sw" style="background:var(--swell)"></i>Linja med bølger: hvor svellet kommer fra</div>
    <div class="erow"><i class="sw" style="background:var(--wind)"></i>Blå pil: vind</div>
    <div class="erow"><i class="sw" style="background:var(--star)"></i>Ringen: rating</div>`;
}
function showExplain(){
  mapState.explainOpen = true;
  $("#mapExplain").innerHTML = explainHtml();
  $("#mapExplain").hidden = false;
  $("#mExplainClose").onclick = hideExplain;
}
function hideExplain(){
  mapState.explainOpen = false;
  $("#mapExplain").hidden = true;
  try{ localStorage.setItem(EXPLAIN_KEY,"1"); }catch(e){}
}
function maybeShowExplainAuto(){
  if(mapState.spotId==null || mapState.sheetOpen) return;
  let seen = false;
  try{ seen = localStorage.getItem(EXPLAIN_KEY)==="1"; }catch(e){}
  if(!seen) showExplain();
}

/* ---------- Min posisjon ---------- */
let meMarker = null;
function locate(){
  const btn = $("#mapLocate");
  if(!navigator.geolocation){ return; }
  btn.setAttribute("aria-pressed","true");
  navigator.geolocation.getCurrentPosition(pos=>{
    btn.setAttribute("aria-pressed","false");
    const ll = [pos.coords.latitude, pos.coords.longitude];
    if(meMarker) discLayer.removeLayer(meMarker);
    const windColor = getComputedStyle(document.documentElement).getPropertyValue("--wind").trim() || "#1C5FD6";
    meMarker = L.circleMarker(ll, {radius:8, color:windColor, fillColor:windColor, fillOpacity:.9, weight:2}).addTo(discLayer);
    map.flyTo(ll, Math.max(map.getZoom(),11), {duration: reduceMotion()?0:0.5});
  }, ()=>{ btn.setAttribute("aria-pressed","false"); }, {enableHighAccuracy:true, timeout:8000});
}

/* ---------- Vis/skjul ved fanebytte ---------- */
let rootBuilt = false;
function buildRoot(){
  if(rootBuilt) return; rootBuilt = true;
  $("#mapRoot").innerHTML = `<div id="mapEl" aria-label="Kart over surfespots"></div>`;

  // map-top/map-time/map-explain/ark ligger rett under <body>, ikke i
  // #mapRoot: Leaflet sine egne paner (som også ligger i #mapRoot) kan ende
  // opp over dem etter en zoom/pan i enkelte nettlesere sjøl med lavere
  // z-index på Leaflet-siden - egne overlegg utenfor #mapRoot er upåvirket
  // av det, samme mønster som loggarket allerede brukte.
  document.body.insertAdjacentHTML("beforeend", `
    <div class="map-top" id="mapTop" hidden>
      <button class="map-round" id="mapLocate" aria-label="Min posisjon" aria-pressed="false">
        <svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2a1 1 0 0 1 1 1v1.06A8.01 8.01 0 0 1 19.94 11H21a1 1 0 1 1 0 2h-1.06A8.01 8.01 0 0 1 13 19.94V21a1 1 0 1 1-2 0v-1.06A8.01 8.01 0 0 1 4.06 13H3a1 1 0 1 1 0-2h1.06A8.01 8.01 0 0 1 11 4.06V3a1 1 0 0 1 1-1zm0 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 3.5A2.5 2.5 0 1 1 9.5 12 2.5 2.5 0 0 1 12 9.5z"/></svg>
      </button>
      <button class="map-round" id="mapHelp" aria-label="Vis forklaring">
        <svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 15.5a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5zm1.6-6.2c-.7.5-.9.8-.9 1.5v.4h-2v-.5c0-1.2.5-1.9 1.4-2.6.7-.5 1.1-.9 1.1-1.5 0-.7-.6-1.2-1.4-1.2-.8 0-1.4.4-1.9 1.1L8.4 7.4C9.1 6.2 10.3 5.3 12 5.3c2 0 3.4 1.2 3.4 2.9 0 1.2-.6 1.9-1.8 2.7z"/></svg>
      </button>
    </div>
    <div class="map-time" id="mapTimeEl" hidden>
      <div class="map-time-head"><span class="lbl" id="mapTimeLabel"></span><button class="map-now" id="mapNowBtn">Nå</button></div>
      <div class="map-slider-wrap">
        <div class="map-slider-track" id="mapTimeTrack"></div>
        <div class="map-slider-thumb" id="mapThumb"></div>
        <input type="range" class="map-slider" id="mapSlider" aria-label="Velg tidspunkt">
      </div>
    </div>
    <div class="map-explain" id="mapExplain" hidden></div>
    <div class="scrim" id="mScrim"></div>
    <section class="sheet map-sheet" id="mSheet" role="dialog" aria-modal="true" aria-labelledby="mSheetTitle" aria-hidden="true">
      <div class="grabber" aria-hidden="true"></div>
      <div class="sheet-head"><span style="width:60px"></span><h2 id="mSheetTitle"></h2>
        <button class="link" id="mSheetClose" aria-label="Lukk">Lukk</button></div>
      <div id="mSheetBody"></div>
    </section>`);
  $("#mapLocate").onclick = locate;
  $("#mapHelp").onclick = ()=> mapState.explainOpen ? hideExplain() : showExplain();
  $("#mapSlider").addEventListener("input", onSliderInput);
  $("#mapNowBtn").onclick = ()=>{ mapState.idx = defaultIdx(); $("#mapSlider").value = mapState.idx; updateTimeLabel(); updateThumb(); renderMarkers(); updateDiscForTime(); };
  $("#mSheetClose").onclick = closeMapSheet;
  $("#mScrim").onclick = closeMapSheet;
}

const SurfMap = {
  show(){
    if(!DATA || !DATA.spots || !DATA.spots.length){
      $("#mapRoot").innerHTML = `<p style="padding:16px;padding-top:calc(16px + env(safe-area-inset-top,0px))">Henter varsel…</p>`;
      return;
    }
    buildRoot();
    initMap();
    $("#mapTop").hidden = false;
    $("#mapTimeEl").hidden = false;
    setTimeout(()=>{ if(map) map.invalidateSize(); }, 0);
  },
  hide(){
    // Animasjoner (CSS) stopper naturlig når elementet får display:none, men
    // map-top/map-time/ark/forklaring ligger nå utenfor #mapRoot og må
    // skjules for seg sjøl når man bytter bort fra kartfanen.
    if(!rootBuilt) return;
    $("#mapTop").hidden = true;
    $("#mapTimeEl").hidden = true;
    $("#mapExplain").hidden = true;
    mapState.explainOpen = false;
    closeMapSheet();
  },
};
window.SurfMap = SurfMap;
})();
