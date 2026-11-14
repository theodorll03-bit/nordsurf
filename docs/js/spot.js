/* Nordsurf: spotsiden (Theodor 14.10.2026, punkt 4 + HIG 9).

   Rekkefølge: vurdering, fire kort (surf, svell, vind, energi), langtidsvarsel
   med dagfaner og timegraf, minikart, tidevann, vær, «Hvorfor denne
   vurderingen?», «Logg en økt her», kilder.

   Ren visning: ingen tall regnes - alt kommer fra spots/<id>.json. Tekstene
   som tolker tall (kroppshøyde, energiord, sikkerhetsord, innenfor/utenfor
   vinduet) står her og er gjennomgått av fysikk-kontrolløren. Grunnregelen:
   tall som mangler vises som «–», aldri 0. */
(function(){
  const $ = (s, r)=> (r||document).querySelector(s);
  const $$ = (s, r)=> [...(r||document).querySelectorAll(s)];
  const fmtDato = new Intl.DateTimeFormat("nb-NO", {weekday:"long", day:"numeric", month:"long", timeZone:TZ});
  const fmtWd = new Intl.DateTimeFormat("nb-NO", {weekday:"long", timeZone:TZ});
  const fmtWdShort = new Intl.DateTimeFormat("nb-NO", {weekday:"short", timeZone:TZ});
  const fmtDayNum = new Intl.DateTimeFormat("nb-NO", {day:"numeric", timeZone:TZ});
  const fmtHM = new Intl.DateTimeFormat("nb-NO", {hour:"2-digit", minute:"2-digit", timeZone:TZ, hour12:false});
  // minikart: én fil per spot (data/minikart/<id>.json, Tillegg 2) - hentes når spoten åpnes
  const kystCache = {}, kystLoading = {};
  let H = null;   // hjelpere fra ui.js (nowIdx, usable, mork, known, stars, dkOf, heightText, regionOf, close, isDesktop)

  /* ---------- tekster som tolker tall ---------- */
  function visHoyde(h){
    // Theodors regel (c) 05.10.2026 (app.js heightMForDisplay): «Blåst ut» viser surfehøyden hvis
    // den er reell, ellers BarentsWatch sin totalhøyde; «Stormsjø» ALLTID totalhøyden; Flatt/Treffer
    // ikke har ikke noe pålitelig tall. Settene (1,27 × Hb) hører bare til surfehøyden.
    if(!h || h._forbud) return null;   // forbudsperiode: ingen høyde (Theodor 16.10.2026)
    const v = heightMForDisplay(h);
    if(v==null) return null;
    const sets = (!h.low_reason || (h.low_reason==="blown_out" && h.surf_height!=null && h.surf_height > 0)) && h.surf_height_sets!=null ? h.surf_height_sets : null;
    return {a: v, b: sets};
  }
  function kroppshoyde(h){
    // midtpunktet mellom høyden som vises og settene (Theodors tabell 14.10.2026)
    const v = visHoyde(h);
    if(!v) return null;
    const m = v.b!=null ? (v.a + v.b) / 2 : v.a;
    if(m < 0.3) return "Nesten flatt";
    if(m < 0.6) return "Ankel- til knehøyt";
    if(m < 0.9) return "Kne- til hoftehøyt";
    if(m < 1.2) return "Hofte- til brysthøyt";
    if(m < 1.5) return "Bryst- til skulderhøyt";
    if(m < 1.8) return "Skulder- til hodehøyt";
    if(m < 2.4) return "Hodehøyt og litt over";
    if(m < 3.4) return "Godt over hodet";
    return "Over dobbel hodehøyde";
  }
  // Energiordet beskriver SVELLET ute, ikke spotens behov: universelle grenser 500 / 2 000 / 10 000 kJ
  // (fysikk-kontrollør 15.10.2026: local_rules.min_energy_kj er spotens krav i rating.energy_factor(),
  // og Unstad sine 400/200 er i gammel skala - de passer ikke som ord på tallet. Spotens egne grenser
  // på stolpen venter til de er regnet om, se ROADMAP).
  const ENERGI_GRENSER = [500, 2000, 10000];
  function energiGrenser(){ return ENERGI_GRENSER; }
  function energiOrd(kj){
    if(kj==null) return null;
    if(kj < ENERGI_GRENSER[0]) return "Svakt";
    if(kj < ENERGI_GRENSER[1]) return "Middels kraft";
    if(kj < ENERGI_GRENSER[2]) return "Kraftig";
    return "Svært kraftig";
  }
  // Vinduet sies fra vinduet (inSwellWindow = rating.in_sector), graden av treff fra eksponeringen
  // (h.directness, som i directionHitText i app.js) - en hake alene ville motsagt «Treffer ikke»
  // for svell i vinduet men skjermet, og et kryss alene 2-3 stjerner bekreftet ved spoten.
  // (regelen bor i app.js vinduStatus - samme funksjon tegner svellkilen på Utforsk)
  function vinduTekst(h, s){
    const v = vinduStatus(h, s);
    return v ? {ikon: v.ikon, txt: v.txt} : null;
  }
  const logPos = (kj)=> Math.max(0, Math.min(1, Math.log10(Math.max(1, kj) / 100) / 3));   // log-skala 100–100 000 kJ
  function sikkerhet(h){
    if(!h) return "–";
    const c = h.confidence;
    const ord = c==null ? null : c >= 80 ? "Høy sikkerhet" : c >= 55 ? "Middels sikkerhet" : "Lav sikkerhet";
    const sone = h.zone==="barentswatch" ? "kystmodell 100 m" : h.zone==="reserve" ? "havmodell" : h.zone==="langtid" ? "langtidsmodell" : null;
    return [ord, sone].filter(Boolean).join(" · ") || "–";
  }
  // hardt mellomrom bare i den lille teksten («kraftig fra 2 000»); det store tallet må kunne brekke ved 200 % tekst
  const kjFmt = (kj, hard)=> kj==null ? "–" : nf0.format(Math.round(kj)).replace(/[ \u00a0\u202f]/g, hard ? "\u00a0" : " ");
  const lysOrd = (h)=>{ const l = h && (h.light || (h.daylight===false ? "mørkt" : h.daylight===true ? "dag" : null)); return l==="mørkt" ? "mørkt" : l==="skumring" ? "skumring" : l==="dag" ? "dagslys" : "–"; };

  /* ---------- tidevann (bare visning: cosinus mellom to hendelser) ---------- */
  function tideLevel(events, t){
    const ms = t.getTime(); let prev = null, next = null;
    for(const e of events){ const em = new Date(e.time).getTime(); if(em <= ms) prev = e; else { next = e; break; } }
    if(!prev || !next || prev.cm==null || next.cm==null || prev.type===next.type) return null;
    const t0 = new Date(prev.time).getTime(), t1 = new Date(next.time).getTime();
    const f = (1 - Math.cos(Math.PI * (ms - t0) / (t1 - t0))) / 2;
    return {cm: prev.cm + (next.cm - prev.cm) * f, rising: next.cm > prev.cm, next};
  }
  function tzOffsetMs(d){
    // Europe/Oslo sin forskyvning for et tidspunkt (sommertid slutter 25.10) - via Intl, ingen egne tabeller
    const p = new Intl.DateTimeFormat("en-US", {timeZone:TZ, hour12:false, year:"numeric", month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit"}).formatToParts(d);
    const g = (k)=> +p.find(x=>x.type===k).value;
    const local = Date.UTC(g("year"), g("month")-1, g("day"), g("hour") % 24, g("minute"));
    return local - d.getTime();
  }

  /* ---------- kortene ---------- */
  const CHECK = `<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="m6.5 10 2.5 2.5 4.5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const TILDE = `<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 9c2-4 4-4 6 0s4 4 6 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`;
  const CROSS = `<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="m7 7 6 6m0-6-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
  function vindPil(dir){
    // peker dit vinden blåser (wind_dir + 180)
    return `<svg class="vindpil" viewBox="0 0 20 20" aria-hidden="true" style="transform:rotate(${((dir + 180) % 360).toFixed(0)}deg)"><path d="M10 2 15 17 10 13 5 17z" fill="currentColor"/></svg>`;
  }
  function kortHtml(s, h){
    const hoyde = H.heightText(h); const vh = visHoyde(h);
    // tallet er kjent, men regel (c) sier «ikke noe pålitelig tall» (flat-sperren, «Treffer ikke» - også med
    // surfehøyde 0,2-0,4 m): ordet vises. «–» er bare for tall som mangler (surf_height null).
    const ekteNull = !!(h && h.surf_height!=null && (!vh || vh.a <= 0));
    const kh = kroppshoyde(h);
    const ideal = s.ideal_height ? `Best her ${nf1.format(s.ideal_height[0])}–${nf1.format(s.ideal_height[1])} m` : "";
    const vt = vinduTekst(h, s);
    const g = energiGrenser(); const kj = h ? h.energy_swell_kj : null; const eo = energiOrd(kj);
    const ticks = g.slice(0, 2).map(v=>`<span class="tick" style="left:${(logPos(v)*100).toFixed(1)}%"></span>`).join("");
    return `<div class="kort4">
      <div class="kort"><div class="k">Surf</div><div class="v">${ekteNull ? `<span style="font-family:var(--body);font-size:1.375rem;font-weight:700">${esc(ratingWord(h))}</span>` : hoyde ? `<span class="tall">${esc(hoyde)}</span><small>m</small>` : "–"}</div><div class="l">${ekteNull ? "" : esc(kh || "–")}</div><div class="m">${esc(ideal)}</div></div>
      <div class="kort"><div class="k">Svell ute</div><div class="v">${h && h.swell_offshore!=null ? `<span class="tall">${nf1.format(h.swell_offshore)}</span><small>m</small>` : "–"}${h && h.period!=null ? `<span class="sep">·</span><span class="tall">${nf0.format(h.period)}</span><small>s</small>` : ""}</div>
        <div class="l">${h && h.dir_offshore!=null ? `fra ${esc(compass(h.dir_offshore))} ${Math.round(h.dir_offshore)}°` : "retning mangler"}</div>
        <div class="m">${!vt ? "" : `<span class="vindu-${vt.ikon}">${vt.ikon==="ja" ? CHECK : vt.ikon==="nei" ? CROSS : TILDE}${esc(vt.txt)}</span>`}</div></div>
      <div class="kort"><div class="k">Vind</div><div class="v">${h && h.wind_speed!=null ? `${h.wind_dir!=null ? vindPil(h.wind_dir) : ""}<span class="tall">${nf0.format(h.wind_speed)}</span><small>m/s</small>` : "–"}</div>
        <div class="l">${h && h.wind_speed!=null ? `<b>${esc(cap(windLabel(h)))}</b>${h.wind_dir!=null ? ` fra ${esc(compass(h.wind_dir))} ${Math.round(h.wind_dir)}°` : ""}` : "–"}</div>
        <div class="m">${h && h.gust!=null ? `Kast ${nf0.format(h.gust)} m/s` : ""}</div></div>
      <div class="kort"><div class="k">Energi</div><div class="v">${kj!=null ? `<span class="num tall">${kjFmt(kj)}</span><small>kJ</small>` : "–"}</div><div class="l">${esc(eo || "–")}</div>
        <div class="m"><div class="energi-bar" aria-hidden="true">${kj!=null ? `<div class="fyll" style="width:${(logPos(kj)*100).toFixed(1)}%"></div>` : ""}${ticks}</div><div class="energi-txt"><span>svak</span><span>kraftig fra ${kjFmt(g[1], true)}</span></div></div></div>
    </div>`;
  }
  function minikartHtml(s, h){
    const inside = h && h.dir_offshore!=null && s.swell_window ? inSwellWindow(h.dir_offshore, s) : null;
    const kyst = kystCache[s.id] && kystCache[s.id].land ? kystCache[s.id] : null;
    const vt = vinduTekst(h, s);
    const svg = Minikart.markup(s, h, kyst, {still: matchMedia("(prefers-reduced-motion: reduce)").matches, hit: vt ? vt.ikon=="ja" : null, vinduTekst: vt ? vt.txt : null});
    return `<div class="kort mini" id="miniKort"><div>${svg}${!kyst ? `<p class="muted" style="text-align:center;font-size:var(--fs-caption);margin:6px 0 0">${s.id in kystCache ? "Kystlinje mangler for denne spoten" : "Henter kystlinjen …"}</p>` : ""}</div>
      <div class="forkl">
        <div><span class="ikon" aria-hidden="true"><svg viewBox="0 0 14 14" width="14" height="14"><path d="M1 9q3-5 6-2t6-2" fill="none" stroke="currentColor" stroke-width="1.6"/></svg></span>Svell<b>${h && h.swell_offshore!=null ? `${nf1.format(h.swell_offshore)} m` : "–"}${h && h.dir_offshore!=null ? ` fra ${esc(compass(h.dir_offshore))} ${Math.round(h.dir_offshore)}°` : ""}</b>${vt ? esc(vt.txt) : ""}</div>
        <div><span class="ikon" aria-hidden="true"><svg viewBox="0 0 14 14" width="14" height="14"><path d="M1 7h10m-3-3 3 3-3 3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg></span>Vind<b>${h && h.wind_speed!=null ? `${nf0.format(h.wind_speed)} m/s${h.wind_dir!=null ? ` fra ${esc(compass(h.wind_dir))} ${Math.round(h.wind_dir)}°` : ""}` : "–"}</b>${h && h.wind_speed!=null ? esc(cap(windLabel(h))) : ""}</div>
        <div><span class="ikon" aria-hidden="true"><svg viewBox="0 0 14 14" width="14" height="14"><path d="M7 7 2 2.5A6.5 6.5 0 0 1 12 2.5z" fill="currentColor" opacity=".3"/><path d="M7 7 2 2.5A6.5 6.5 0 0 1 12 2.5z" fill="none" stroke="currentColor" stroke-dasharray="2 2"/></svg></span>Vindu<b>${s.swell_window ? esc(windowText(s).replace("Vindu ", "")) : "–"}</b></div>
      </div></div>`;
  }
  function tideHtml(s, ms, nowMs, erNa){
    // tidevannskortet (docs/js/tidevann.js); grafen tegnes i ekte piksler av Tidevann.mount() etter render
    return window.Tidevann ? Tidevann.html(s, ms, nowMs, erNa) : "";
  }
  function vaerHtml(s, t, h){
    const lys = lightText(s, t);
    return `<div class="kort vaer"><div><div class="k">Luft</div><div class="v">${h && h.air_temp!=null ? `${nf0.format(h.air_temp)}°` : "–"}</div></div><div><div class="k">Vann</div><div class="v">${h && h.water_temp!=null ? `${nf0.format(h.water_temp)}°` : "–"}</div></div><div><div class="k">Dagslys</div><div class="v" style="font-size:1.125rem">${esc(lys.v)}</div></div></div>`;
  }
  function hvorforHtml(h){
    if(!h || !h.breakdown) return "";
    const ex = ratingWordExplain(h);
    return `<details class="hvorfor" id="hvorfor"><summary aria-expanded="false">Hvorfor denne vurderingen?<svg class="chev" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="m3 6 5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></summary>
      <div class="body">${ex ? `<p class="bd-note"><b>${esc(ratingWord(h))}</b> – ${esc(ex)}</p>` : ""}${h.breakdown.map((line, i)=>breakdownRowHtml(line, i===h.breakdown.length-1)).join("")}</div></details>`;
  }

  /* ---------- render ---------- */
  function render(root, s, S, helpers){
    H = helpers;
    const n = H.nowIdx(s); const idx = S.idx!=null ? Math.max(0, Math.min(s.hours.length-1, S.idx)) : n;
    const h = s.hours[idx] || null; const t = h ? new Date(h.t) : new Date();
    // valgt tidspunkt i tidevannskortet: valgt time + kvarter-forskyvning (S.tideMin, satt ved dra/piltaster i
    // tidevannsgrafen). På «nå» uten forskyvning er det klokka nå (nedtellingen til neste flo/fjære).
    const nowMs = Date.now(); const tideMin = S.tideMin || 0;
    const tideNa = idx===n && !tideMin;
    const tideMs = tideNa ? nowMs : t.getTime() + tideMin * 6e4;
    const atNow = idx===n && !tideMin;   // flyttet i tidevannsgrafen: ikke «nå» lenger (overskriften viser minuttene)
    const tid = `${atNow ? "Nå · " : ""}${esc(fmtWd.format(t))} kl. ${tideMin ? fmtHM.format(new Date(tideMs)) : fmtHour.format(t)} · ${esc(lysOrd(h))}`;
    const st = H.stars(h);
    const pc = H.isDesktop();
    const topp = `${typeof staleBanner==="function" ? staleBanner() : ""}<div class="spot-topp"><button type="button" class="back" id="spotBack" aria-label="Tilbake"><svg viewBox="0 0 18 18" aria-hidden="true"><path d="M11 3 5 9l6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>${pc ? "Tilbake" : ""}</button>
        <div class="tittel"><h1>${esc(s.name)}</h1><div class="omr">${esc(H.stedText(s))}</div></div>${favBtnHtml(s.id, false)}</div>
      <div class="naa"><span>${tid}</span>${atNow ? "" : `<button type="button" class="tilbakena" id="tilbakeNa">Tilbake til nå</button>`}</div>`;
    // Theodor 16.10.2026: i forbudsperioden «Surfing forbudt nå» og perioden i stedet for tall og ord (bare visning)
    const fb = H.forbudInfo ? H.forbudInfo(s, t.getTime()) : null;
    // tapte poeng skrives ut med grunnen (SPEC §5): «−1 tidevann», «−2 vind» (tallene fra rating.py, faded_wind/faded_tide)
    const taptTxt = h ? [h.faded_wind ? `−${h.faded_wind} vind` : null, h.faded_tide ? `−${h.faded_tide} tidevann` : null].filter(Boolean) : [];
    if(h && h.faded && !taptTxt.length) taptTxt.push(`−${h.faded}`);   // eldre varsel uten delingen
    const tapt = taptTxt.length ? `<div class="etikett tapt">${esc(taptTxt.join(" · "))}</div>` : "";
    const vurdering = fb
      ? `<div class="vurdering"><div class="forbud"><div class="ord">${esc(fb.tittel)}</div><div class="periode">${esc(fb.periode)}${fb.r.verneomrade ? " · " + esc(fb.r.verneomrade) : ""}</div></div></div>`
      : H.known(h) && H.mork(h)
      // mørk time: ingen vurdering på skjermen (SPEC §5) - bare ordet «Mørkt» og hvorfor; kortene under viser tallene som før
      ? `<div class="vurdering"><div class="r-0"><div class="ord r-0">Mørkt</div><div class="etikett lyse">${esc(STR.lightOnly)}</div></div><div class="sikker">${esc(sikkerhet(h))}</div></div>`
      : `<div class="vurdering"><div class="r-${Math.min(5,st)}">${H.known(h) ? tallHtml(st, h.faded||0, true) : ""}<div class="ord r-${Math.min(5,st)}">${esc(h ? ratingWord(h) : "–")}</div>${tapt}</div><div class="sikker">${esc(sikkerhet(h))}</div></div>`;   // linja om forbudet står i overskriften (stedText)
    const venstre = `${vurdering}${kortHtml(s, h)}`;
    // åpnet på «nå» (S.idx null): grafen viser i dag bare hvis det er minst 2 lyse timer igjen, ellers i morgen -
    // kortene øverst viser fortsatt nå (Theodor 15.10, punkt 3)
    const grafDag = S.idx==null && window.SpotGraf ? SpotGraf.defaultDay(s, n, H) : null;
    const langtid = `<div class="sek-spot"><h2 class="h2">Langtidsvarsel</h2><p class="sub">16 dager</p></div><div id="langtid">${window.SpotGraf ? SpotGraf.html(s, idx, H, grafDag) : ""}</div>`;
    const resten = `${minikartHtml(s, h)}${tideHtml(s, tideMs, nowMs, tideNa)}${vaerHtml(s, t, h)}${hvorforHtml(h)}
      <div class="logg-her"><button type="button" class="primary" id="loggHer">Logg en økt her</button></div>
      <p class="kilder">Varsel fra ${esc(relDay(new Date(DATA.generated)))} kl. ${fmtTime.format(new Date(DATA.generated))}. Kilder: BarentsWatch (kystmodell 100 m), MET Norge, Open-Meteo og Kartverket. Kart: © OpenStreetMap-bidragsytere.</p>`;
    root.innerHTML = pc
      ? `${topp}<div class="spot-venstre">${venstre}${minikartHtml(s, h)}${tideHtml(s, tideMs, nowMs, tideNa)}${vaerHtml(s, t, h)}</div><div class="spot-hoyre">${langtid}${hvorforHtml(h)}<div class="logg-her"><button type="button" class="primary" id="loggHer">Logg en økt her</button></div><p class="kilder">Varsel fra ${esc(relDay(new Date(DATA.generated)))} kl. ${fmtTime.format(new Date(DATA.generated))}. Kilder: BarentsWatch (kystmodell 100 m), MET Norge, Open-Meteo og Kartverket. Kart: © OpenStreetMap-bidragsytere.</p></div>`
      : `${topp}${venstre}${langtid}${resten}`;
    $("#spotBack").onclick = H.close;
    const tn = $("#tilbakeNa"); if(tn) tn.onclick = ()=>{ S.idx = null; S.tideMin = 0; render(root, s, S, H); };
    $("#loggHer").onclick = ()=> openSheet(s.id, t);
    const hv = $("#hvorfor"); if(hv) hv.addEventListener("toggle", ()=> hv.querySelector("summary").setAttribute("aria-expanded", String(hv.open)));
    wireFavButtons();
    if(window.SpotGraf) SpotGraf.wire(root, s, S, H, (i)=>{
      // timevalg oppdaterer alt over grafen - uten å hoppe i siden eller lukke «Hvorfor»
      const y = window.scrollY, hv = $("#hvorfor", root), open = hv ? hv.open : false;
      S.idx = i; S.tideMin = 0; render(root, s, S, H);
      window.scrollTo(0, y); const hv2 = $("#hvorfor", root); if(hv2 && open) hv2.open = true;
    });
    if(window.Tidevann) Tidevann.mount(root, s, tideMs, {nowMs, onSelect: (ms, fokus)=>{
      // dra/piltaster i tidevannsgrafen: samme tilstand som timegrafen (S.idx) + kvarter-resten (S.tideMin)
      let i = 0; for(let k = 0; k < s.hours.length; k++){ if(new Date(s.hours[k].t).getTime() <= ms) i = k; else break; }
      const y = window.scrollY, hv = $("#hvorfor", root), open = hv ? hv.open : false;
      S.idx = i; S.tideMin = Math.round((ms - new Date(s.hours[i].t).getTime()) / 6e4);
      render(root, s, S, H);
      window.scrollTo(0, y); const hv2 = $("#hvorfor", root); if(hv2 && open) hv2.open = true;
      if(fokus){ const g = $("#tideGraf", root); if(g) g.focus({preventScroll: true}); }
    }});
    if(!(s.id in kystCache)){
      kystLoading[s.id] = kystLoading[s.id] || fetch(`data/minikart/${encodeURIComponent(s.id)}.json`, {cache:"force-cache"}).then(r=> r.ok ? r.json() : {}).catch(()=>({}));
      kystLoading[s.id].then(k=>{ kystCache[s.id] = k || {}; const el = $("#miniKort", root); if(el && S.view==="spot" && S.spotId===s.id){ el.outerHTML = minikartHtml(s, h); } });
    }
    if(!pc) root.scrollTop = 0;
  }
  window.Spot = { render, kroppshoyde, visHoyde, energiOrd, energiGrenser, vinduTekst, sikkerhet, tideLevel, tzOffsetMs };
})();
