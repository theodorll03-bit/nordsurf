/* Nordsurf: tekst i SVG-er med fast viewBox i ekte piksler (Theodor 16.10.2026).
   En SVG med fast koordinatsystem (minikartets kompass, eksponeringsgrafen) skaleres til beholderens bredde - da
   skaleres teksten også (17 enheter ble 11,7 px på mobil og større på PC). Merk SVG-en med data-tekst-px="12":
   tekstens font-size settes da i SVG-enheter = 12 × viewBox-bredde / faktisk bredde, og regnes på nytt når
   bredden endres (ResizeObserver) - så teksten er 12 px uansett skjerm. Nye SVG-er fanges av en MutationObserver.
   Tidevannskortet trenger ikke dette: der er viewBox = faktisk bredde (docs/js/tidevann.js). */
(function(){
  const fulgt = new WeakSet();
  const ro = window.ResizeObserver ? new ResizeObserver((ents)=> ents.forEach(e=> fest(e.target))) : null;
  function fest(svg){
    const vb = svg.viewBox && svg.viewBox.baseVal, w = svg.getBoundingClientRect().width;
    if(!vb || !vb.width || !w) return;
    const px = parseFloat(svg.dataset.tekstPx) || 12, enh = (px * vb.width / w).toFixed(2) + "px";
    svg.querySelectorAll("text").forEach(t=>{ if(t.style.fontSize !== enh) t.style.fontSize = enh; });
  }
  function finn(root){
    const svgs = root.matches && root.matches("svg[data-tekst-px]") ? [root] : root.querySelectorAll ? root.querySelectorAll("svg[data-tekst-px]") : [];
    svgs.forEach(svg=>{ fest(svg); if(ro && !fulgt.has(svg)){ fulgt.add(svg); ro.observe(svg); } });
  }
  new MutationObserver((ms)=> ms.forEach(m=> m.addedNodes.forEach(n=>{ if(n.nodeType === 1) finn(n); }))).observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener("DOMContentLoaded", ()=> finn(document));
  window.SvgTekst = { fest, finn };
})();
