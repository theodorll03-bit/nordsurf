/* Nordsurf: minikartet på spotsiden (Theodor 14.10.2026, punkt 4c).

   En sirkel med den lokale kystlinjen rundt spoten (radius 3,5 km, nord opp),
   svellvinduet som stiplet kile, svellpilen fra randen inn mot spoten (tre
   buer ruller sakte innover når svellet er innenfor vinduet, ellers stiplet og
   grå), vindpilen fra randen i vindretningen, gradstreker hver 15° og
   himmelretninger utenfor. Kystlinjen kommer fra docs/data/minikart.json
   (tools/lag_minikart.py, OpenStreetMap), lastes bare på spotsiden.

   Ren visning: ingen tall regnes - retningene og vinduet er varselets egne.
   «Innenfor vinduet» er NØYAKTIG samme test som rating.py (inSwellWindow i
   app.js = rating.in_sector). */
(function(){
  const R = 100;
  const COMPASS = [["N",0],["NØ",45],["Ø",90],["SØ",135],["S",180],["SV",225],["V",270],["NV",315]];
  function pt(bearing, r){ const a = bearing*Math.PI/180; return [r*Math.sin(a), -r*Math.cos(a)]; }
  function f(v){ return (Math.round(v*10)/10).toString(); }
  function wedge(win, r){
    const secs = Array.isArray(win[0]) ? win : [win];
    return secs.map(([a,b])=>{ const span=(b-a+360)%360, p1=pt(a,r), p2=pt(b,r); return `M0,0L${f(p1[0])},${f(p1[1])}A${r},${r} 0 ${span>180?1:0} 1 ${f(p2[0])},${f(p2[1])}Z`; }).join("");
  }
  function arrowFromRim(bearing, len, cls, extra){
    // fra randen (retningen svellet/vinden kommer FRA) inn mot spoten
    const from = pt(bearing, R - 6), to = pt(bearing, R - 6 - len);
    const dirx = (to[0]-from[0]), diry = (to[1]-from[1]); const L = Math.hypot(dirx, diry) || 1;
    const ux = dirx/L, uy = diry/L; const hx = to[0] - ux*9, hy = to[1] - uy*9;
    const px = -uy, py = ux;
    return `<g class="${cls}"${extra||""}><line x1="${f(from[0])}" y1="${f(from[1])}" x2="${f(hx)}" y2="${f(hy)}"/><path d="M${f(to[0])},${f(to[1])}L${f(hx+px*5)},${f(hy+py*5)}L${f(hx-px*5)},${f(hy-py*5)}Z"/></g>`;
  }
  function arcs(bearing){
    // tre buer som ruller innover langs svellretningen (CSS-animasjon, slås av med prefers-reduced-motion)
    let out = "";
    for(let i=0;i<3;i++){
      out += `<path class="bue" style="animation-delay:-${(i*1.4).toFixed(1)}s" d="M-16,-62Q0,-70 16,-62"/>`;
    }
    return `<g class="buer" transform="rotate(${f(bearing)})">${out}</g>`;
  }
  /* kyst: {land: [sti...], coast: [sti...]} i viewBox -100..100 (tools/lag_minikart.py) */
  function markup(spot, h, kyst, opts){
    const o = opts || {};
    const inside = h && h.dir_offshore!=null && spot.swell_window ? inSwellWindow(h.dir_offshore, spot) : null;
    // buene ruller bare når svellet faktisk treffer (i vinduet OG ikke skjermet - opts.hit fra spot.js sin vinduTekst)
    const hit = opts && opts.hit!=null ? opts.hit : inside;
    const hasSwell = h && h.dir_offshore!=null;
    const hasWind = h && h.wind_dir!=null;
    const ticks = [];
    for(let d=0; d<360; d+=15){ const a = pt(d, R), b = pt(d, R - (d%45===0 ? 7 : 4)); ticks.push(`<line x1="${f(a[0])}" y1="${f(a[1])}" x2="${f(b[0])}" y2="${f(b[1])}"/>`); }
    const labels = COMPASS.map(([t,d])=>{ const p = pt(d, R+13); return `<text x="${f(p[0])}" y="${f(p[1])}" text-anchor="middle" dominant-baseline="middle">${t}</text>`; }).join("");
    const land = kyst && kyst.land ? kyst.land.map(d=>`<path class="land" d="${d}"/>`).join("") : "";
    const coast = kyst && kyst.coast ? kyst.coast.map(d=>`<path class="coast" d="${d}"/>`).join("") : "";
    const aria = [
      `Minikart rundt ${spot.name}, 3,5 km radius, nord opp.`,
      hasSwell ? `Svell fra ${compass(h.dir_offshore)} ${Math.round(h.dir_offshore)} grader, ${opts && opts.vinduTekst ? opts.vinduTekst.toLowerCase().replace("vinduet", "svellvinduet") : inside==null ? "" : inside ? "innenfor svellvinduet" : "utenfor svellvinduet"}.` : "Svellretning mangler.",
      hasWind ? `Vind fra ${compass(h.wind_dir)} ${Math.round(h.wind_dir)} grader.` : "Vindretning mangler.",
      spot.swell_window ? `Svellvindu ${windowText(spot).replace("Vindu ", "")}.` : "",
    ].join(" ");
    return `<svg class="minikart${o.still ? " still" : ""}" viewBox="-118 -118 236 236" role="img" aria-label="${esc(aria)}">
      <defs><clipPath id="mkClip-${esc(spot.id)}"><circle r="${R}"/></clipPath></defs>
      <circle class="sjo" r="${R}"/>
      <g clip-path="url(#mkClip-${esc(spot.id)})">${land}${coast}</g>
      ${spot.swell_window ? `<path class="vindu" d="${wedge(spot.swell_window, R)}"/>` : ""}
      <g class="ticks">${ticks.join("")}</g>
      <circle class="rand" r="${R}"/>
      ${hasSwell ? (hit ? arcs(h.dir_offshore) : "") + arrowFromRim(h.dir_offshore, 40, hit ? "svell" : "svell miss") : ""}
      ${hasWind ? arrowFromRim(h.wind_dir, 26, "vind") : ""}
      <circle class="spot" r="3.2"/>
      <g class="komp">${labels}</g>
    </svg>`;
  }
  window.Minikart = { markup };
})();
