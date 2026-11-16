/* Nordsurf: retningsskiva på spotsiden (design B 4.0, SPEC §6B punkt 8).

   Kornfotoet av spoten ovenfra (nord opp) ligger svakt under hele skiva og i full styrke i svellvinduet.
   Ringen er brutt der vinduet er, buen utenfor viser hvor vinden er fralands, og pilene peker dit svellet og
   vinden kommer FRA og inn mot spoten. Svellpila er korall bare når retningen ligger i vinduet.

   Ren visning: vinduet og fralandssektoren er spotens egne (spots.json), retningene er timens. */
(function(){
  const R = Math.PI / 180;
  const pkt = (grader, r)=> [80 + r * Math.sin(grader * R), 80 - r * Math.cos(grader * R)];
  const f = (v)=> v.toFixed(2);
  const sektorer = (w)=> !w ? [] : Array.isArray(w[0]) ? w : [w];
  const bredde = ([a, b])=> ((b - a + 360) % 360) || 360;
  function bue(a, b, r){
    // sirkelbue med klokka fra a til b (grader fra nord)
    const [x0, y0] = pkt(a, r), [x1, y1] = pkt(b, r);
    return `M${f(x0)} ${f(y0)} A${r} ${r} 0 ${bredde([a, b]) > 180 ? 1 : 0} 1 ${f(x1)} ${f(y1)}`;
  }
  function klipp(vinduer){
    // clip-path for bildet: kakestykket(-ene) vinduet dekker, i prosent av bildets boks
    const p = [];
    for(const [a, b] of vinduer){
      const w = bredde([a, b]); p.push("50% 50%");
      for(let v = 0; v <= w + 1e-9; v += Math.min(10, w / Math.max(1, Math.ceil(w / 10)))){
        const g = (a + Math.min(v, w)) * R; p.push(`${(50 + 72 * Math.sin(g)).toFixed(2)}% ${(50 - 72 * Math.cos(g)).toFixed(2)}%`);
      }
    }
    return `polygon(${p.join(", ")})`;
  }
  const harBilde = (id)=> !!(window.SPOTBILDER && window.SPOTBILDER.ids.includes(id));

  function html(s, h, hh, o){
    // o.stor: nettsiden (SPEC §6C, 300 px) - teksten i skiva holdes på 12 px av svgtekst.js (data-tekst-px)
    const stor = !!(o && o.stor), px = stor ? 300 : 168;
    const vinduer = sektorer(s.swell_window);
    const svell = h && h.dir_offshore!=null ? h.dir_offshore : null, vind = h && h.wind_speed!=null && h.wind_dir!=null ? h.wind_dir : null;
    const iVindu = svell!=null ? inSwellWindow(svell, s) : null;
    const vinduTxt = vinduer.map(([a, b])=> STR.spot.vinduTil(a, b)).join(" og ");
    const vindOrd = h ? windLabel(h) : "";
    const etikett = STR.spot.skiveAria(s.name, hh,
      svell!=null ? (vinduer.length ? STR.spot.skiveSvell(Math.round(svell), !!iVindu, vinduTxt) : `svell fra ${Math.round(svell)} grader`) : STR.spot.skiveSvellMangler,
      vind!=null ? STR.spot.skiveVind(compass(vind), vindOrd) : "");
    const id = encodeURIComponent(s.id);
    // bildet ligger svakt under hele skiva; kopien i full styrke er klippet til vinduet (og mangler uten vindu)
    const bilde = (tema)=> `<img class="b ${tema}" src="img/spots/${id}-${tema}-skive.jpg" alt="" loading="lazy" decoding="async">${vinduer.length ? `<img class="b ${tema} iv" src="img/spots/${id}-${tema}-skive.jpg" alt="" loading="lazy" decoding="async" style="clip-path:${klipp(vinduer)}">` : ""}`;
    // ringen er hel uten vindu, ellers tegnet mellom vinduene; to radier per vindu
    let ring = "", radier = "";
    if(!vinduer.length) ring = `<circle class="rg" cx="80" cy="80" r="60"/>`;
    else vinduer.forEach(([a, b], i)=>{
      const neste = vinduer[(i + 1) % vinduer.length][0];
      if(bredde([a, b]) < 360) ring += `<path class="rg" d="${bue(b, neste, 60)}"/>`;
      radier += `M80 80 L${pkt(a, 60).map(f).join(" ")} M80 80 L${pkt(b, 60).map(f).join(" ")} `;
    });
    const fra = sektorer(s.offshore_wind).map(([a, b])=> `<path class="fl" d="${bue(a, b, 67)}"/>`).join("");
    const svg = `<svg width="${px}" height="${px}" viewBox="0 0 160 160" aria-hidden="true"${stor ? ' data-tekst-px="12"' : ""}>
        ${ring}${radier ? `<path class="rd" d="${radier}"/>` : ""}<circle class="tk" cx="80" cy="80" r="64"/>${fra}
        ${svell!=null ? `<g class="sv${iVindu ? " inne" : ""}" style="transform:rotate(${Math.round(svell)}deg)"><path class="u" d="M80 16 L80 42"/><polygon points="80,52 74,42 86,42"/><path class="p" d="M80 16 L80 42"/></g>` : ""}
        ${vind!=null ? `<g class="vd" style="transform:rotate(${Math.round(vind)}deg)"><path class="u" d="M80 54 L80 69 M75 64 L80 71 L85 64"/><path class="p" d="M80 54 L80 69 M75 64 L80 71 L85 64"/></g>` : ""}
        <circle class="m0" cx="80" cy="80" r="4.5"/><circle class="m1" cx="80" cy="80" r="3"/>
        <g class="hr"><text x="80" y="9">N</text><text x="155" y="84">Ø</text><text x="80" y="159">S</text><text x="5" y="84">V</text></g>
      </svg>`;
    const vs = h ? vinduStatus(h, s) : null;
    const linje = (k, v, sub)=> `<span><span class="etikett">${esc(k)}</span><span class="v">${v}</span>${sub ? `<span class="u">${esc(sub)}</span>` : ""}</span>`;
    const forkl = [
      linje(STR.spot.svellFra, svell!=null ? `${esc(compass(svell))} ${Math.round(svell)}°` : esc(STR.spot.mangler), vs ? vs.txt : ""),
      linje(STR.spot.vindFra, vind!=null ? `${esc(compass(vind))} ${Math.round(vind)}°` : esc(STR.spot.mangler), vind!=null ? vindOrd : ""),
      vinduer.length ? linje(STR.spot.vindu, esc(vinduer.map(([a, b])=> `${a}–${b}°`).join(", ")), "") : "",
    ].join("");
    return `<div class="skive-rad${stor ? " stor" : ""}"><div class="skive" role="img" aria-label="${esc(etikett)}">${harBilde(s.id) ? bilde("trykk") + bilde("lodd") : ""}${svg}</div><div class="skive-forkl">${forkl}</div></div>
      ${harBilde(s.id) ? `<p class="kredit liten">${esc(window.SPOTBILDER.kort)}</p>` : ""}`;
  }
  window.Skive = { html, harBilde };
})();
