/* Nordsurf: spotsiden (Theodor 14.10.2026, punkt 4). Fylles i steg 3 og 4. */
(function(){
  window.Spot = {
    render(root, s, S){
      root.innerHTML = `<div class="spot-topp"><button type="button" class="back" id="spotBack"><svg viewBox="0 0 18 18" aria-hidden="true"><path d="M11 3 5 9l6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        <div class="tittel"><h1>${esc(s.name)}</h1><div class="omr">${esc(s.area||"")}</div></div>${favBtnHtml(s.id, false)}</div>
        <p class="muted">Spotsiden kommer i steg 3.</p>`;
      wireFavButtons();
    },
  };
})();
