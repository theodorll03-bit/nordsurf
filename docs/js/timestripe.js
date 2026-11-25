/* Nordsurf: timestripa på spotsiden (design B 4.0, SPEC §6B punkt 7).

   Én kolonne per time: strek over de beste timene, fem segmenter (fylt opp til timens tall - blekk til og med
   3, korall fra 4 som SPEC §5 sier), surfehøyden ved spoten som stolpe, vindpil og vindstyrke, og under hele stripa
   tidevannskurven med spotens foretrukne nivå som bånd og stiplet der tidevannet koster poeng. Mørke timer og timer
   i en forbudsperiode har ingen segmenter (SPEC §5), og timer uten data er skravert - aldri 0.

   Designrevisjonen fase 3 punkt 4: stolpene har fast skala per spot, fra 0 til spotens max_height (spots.json, i
   detaljfila), og en tynn linje ved nedre grense i ideal_height, med tallet i margen utenfor stolpene. Høyden er den samme som det store tallet i KL.-blokka
   (hoydeVist i ui.js): Flatt og Treffer ikke har ingen stolpe, bare grunnlinja. Mangler høyden i dataene, er stolpeplassen skravert. Tapte poeng stiples i blekk, ikke korall,
   og bare for valgt time (klassen «valgt» på kolonnen, flyttes av velg()). Teksten («−2 vind») står i KL.-blokka.

   Ren visning: ingen tall regnes. Timen velges ved å dra eller trykke i stripa, eller med piltaster og
   VoiceOver gjennom den skjulte glidebryteren.

   Nettsiden (B4 steg 6, SPEC §6C punkt 5, valget {bred: true}): samme stripe som tabell med en etikettkolonne
   (144 px) og en rad til - retningen svellet kommer fra -, surfehøyden med tallet over stolpen, alle timene merket i
   KL.-raden, vind hver time, og timen velges også ved å holde musa over den. */
(function(){
  const $ = (s, r)=> (r||document).querySelector(s);
  const osloHour = (t)=> +fmtHour.format(t);
  const TIME = 36e5, TIDE_H = 52, TIDE_H_BRED = 64, SURF_H = 48;   // stolpene for surfehøyden: 48 px = max_height
  const f1 = (cm)=> nf1.format(cm / 100);
  let cur = null;   // {root, s, d, cols, H, best, onPick, ned}

  function kolonner(s, d, sel, H){
    // kolonnene for dagen: 06-18 (utvidet når lyse timer eller valgt time ligger utenfor), eller bare timene
    // varselet har når steget er 6 timer. i = -1: timen har vært (i dag, før varselet starter).
    const alle = d.idxs.map(i=>{ const t = new Date(s.hours[i].t); return {i, hh: osloHour(t), ms: t.getTime()}; });
    if(d.step !== 1 || !alle.length) return alle;
    const lyse = alle.filter(c=> H.usable(s.hours[c.i])).map(c=> c.hh);
    const valgt = alle.find(c=> c.i === sel);
    const lo = Math.min(6, ...lyse, valgt ? valgt.hh : 6), hi = Math.max(18, ...lyse, valgt ? valgt.hh : 18);
    const cols = alle.filter(c=> c.hh >= lo && c.hh <= hi);
    if(!cols.length) return alle;
    for(let hh = cols[0].hh - 1, ms = cols[0].ms - TIME; hh >= lo; hh--, ms -= TIME) cols.unshift({i: -1, hh, ms});
    return cols;
  }
  const steg = (cols)=> cols.length >= 2 ? cols[1].ms - cols[0].ms : TIME;
  function xAv(cols, ms){
    // brøk av bredden (0-1) for et tidspunkt: kolonnen står midt på sin time, rett linje mellom midtpunktene
    const n = cols.length; if(!n) return 0;
    let k = 0; while(k < n - 1 && cols[k+1].ms <= ms) k++;
    const w = k < n - 1 ? cols[k+1].ms - cols[k].ms : steg(cols.slice(-2));
    return (k + 0.5 + (ms - cols[k].ms) / w) / n;
  }
  const spenn = (cols)=> cols.length ? [cols[0].ms - steg(cols) / 2, cols[cols.length-1].ms + steg(cols.slice(-2)) / 2] : [0, 0];

  function tapt(h){
    const ut = [h.faded_wind ? STR.spot.timeTapt(h.faded_wind, "vind") : null, tideLost(h) ? STR.spot.timeTapt(tideLost(h), "tidevann") : null].filter(Boolean);
    return ut.join(", ");
  }
  function ariaTime(s, c, H, best, ev){
    const h = s.hours[c.i]; const hh = String(c.hh).padStart(2, "0");
    const dom = h._forbud ? STR.hjem.forbud.toLowerCase() : !H.known(h) ? STR.spot.timeMangler : H.mork(h) ? STR.spot.timeMork : STR.spot.timeTall(H.stars(h), tapt(h));
    const lv = window.Tidevann ? Tidevann.nivaa(ev, c.ms) : null;
    const surf = !h._forbud && H.known(h) && H.heightText && H.heightText(h) ? STR.spot.timeSurf(H.heightText(h)) : null;
    const rest = [surf, h.swell_offshore!=null ? (h.long_sea ? STR.spot.timeLangSjo : STR.spot.timeSvell)(nf1.format(h.swell_offshore)) : null,
      h.wind_speed!=null ? STR.spot.timeVind(windMsText(h), windLabel(h)) : null,
      lv ? STR.spot.timeTide(f1(lv.cm), lv.stiger) : null].filter(Boolean).join(", ");
    return STR.spot.timeAria(hh, dom + (best.has(c.i) ? ", " + STR.spot.timeBest : ""), rest ? rest.charAt(0).toUpperCase() + rest.slice(1) : "");
  }

  function html(s, d, sel, best, H, o){
    const bred = !!(o && o.bred);
    const cols = kolonner(s, d, sel, H); const n = cols.length;
    if(!n) return "";
    const ev = window.Tidevann ? Tidevann.hendelser(s) : [];
    const naa = Date.now(); const [t0, t1] = spenn(cols);
    const harNaa = d.key === dayKey(new Date()) && naa >= t0 && naa <= t1;
    const kNaa = harNaa ? Math.min(n - 1, Math.floor(xAv(cols, naa) * n)) : -1;
    const hvert = bred || d.step !== 1 ? 1 : n > 14 ? 2 : 1;   // mange kolonner på mobil: vind annenhver time
    const xNaa = harNaa ? xAv(cols, naa) * n : -9;
    const tikk = cols.map((c, k)=>{
      // mobil: hver 3. time og ingen ved siden av «NÅ»; nettsiden: alle timene unntatt den «NÅ» står over
      const vis = bred ? Math.abs(k + 0.5 - xNaa) >= 0.5 : (d.step !== 1 || c.hh % 3 === 0) && (kNaa < 0 || Math.abs(k - kNaa) > 1);
      return `<span>${vis ? String(c.hh).padStart(2, "0") : ""}</span>`;
    }).join("");
    // surfehøyden som stolpe med fast skala: 0 til spotens max_height. Mangler den, skaleres det mot den høyeste
    // surfehøyden i varselet for spoten (aldri mot dagens egen topp, så dagene kan sammenlignes). Over skalaen: full stolpe.
    const hoydeAv = (h)=>{ const v = h && !h._forbud && H.known(h) ? H.hoydeVist(h) : null; return v ? v.a : null; };
    const maks = s.max_height > 0 ? s.max_height : Math.max(1, ...s.hours.map(h=> hoydeAv(h) || 0));
    const ideal = Array.isArray(s.ideal_height) && s.ideal_height[0] > 0 && s.ideal_height[0] < maks ? s.ideal_height[0] : null;
    const px = (v)=> Math.max(2, Math.round(Math.min(1, v / maks) * SURF_H));
    const skygge = cols.map(c=>{ const h = c.i >= 0 ? s.hours[c.i] : null; return `<i class="${h && h.light==="mørkt" ? "natt" : h && h.light==="skumring" ? "skum" : ""}"></i>`; }).join("");
    const kol = cols.map((c, k)=>{
      const h = c.i >= 0 ? s.hours[c.i] : null;
      const mork = !!h && H.mork(h), kjent = !!h && H.known(h), forbud = !!h && !!h._forbud;   // forbudsperiode: ingen vurdering, aldri «0»
      const st = kjent && !mork && !forbud ? Math.min(5, H.stars(h)) : 0, lost = kjent && !mork && !forbud ? Math.min(5 - st, lostAll(h)) : 0;
      // tidevannets poeng står nærmest de hele (vinden bokføres først, øverst) og er stiplet i blekk, som vindens (fase 3 punkt 4)
      const lostTv = Math.min(lost, kjent ? tideLost(h) : 0);
      let seg = "";
      if(!h) seg = `<div class="segs vaert"></div>`;
      else if(mork || forbud) seg = `<div class="segs${forbud ? " forbud" : ""}"></div>`;
      else if(!kjent) seg = `<div class="segs miss"></div>`;
      else { for(let nivaa = 5; nivaa >= 1; nivaa--) seg += `<i class="${nivaa <= st ? "pa" : nivaa <= st + lostTv ? "tapt tv" : nivaa <= st + lost ? "tapt" : ""}"></i>`; seg = `<div class="segs r-${st}">${seg}</div>`; }
      // stolpen: høyden som vises (regel (c)); tallet over stolpen på nettsiden. Mangler data: skravur, aldri en lav stolpe
      const v = hoydeAv(h);
      const surf = `<div class="srf">${bred ? `<b>${v!=null ? esc(nf1.format(v)) : h && !forbud && kjent ? "–" : ""}</b>` : ""}<span class="sbx${h && (!kjent || H.hoydeMangler(h)) ? " miss" : ""}">${v!=null ? `<i style="height:${px(v)}px"></i>` : ""}</span></div>`;
      const visVind = h && h.wind_speed!=null && (c.hh % hvert === 0 || d.step !== 1);
      // retning som mangler gir ingen pil (aldri nordavind som standard), bare tallet
      const pil = visVind && h.wind_dir!=null ? `<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true" style="transform:rotate(${(Math.round(h.wind_dir) + 180) % 360}deg)"><path d="M12 2 L19.5 20 L12 15.5 L4.5 20 Z" fill="${h.wind_type==="offshore" ? "currentColor" : "none"}" stroke="currentColor" stroke-width="2" stroke-linejoin="miter"/></svg>` : "";
      const vind = visVind ? `${pil}<b>${windMsText(h)}</b>`
        : h && h.wind_speed==null && c.hh % hvert === 0 ? "<b>–</b>" : "";
      let ekstra = "";
      if(bred){
        // retningen svellet kommer FRA som pil mot spoten - fylt når den er i vinduet
        const dir = h && h.dir_offshore!=null ? h.dir_offshore : null;
        const inne = dir!=null && visVindu(s) ? inSwellWindow(dir, s) : false;
        ekstra = `<div class="sfr">${dir!=null ? `<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true" style="transform:rotate(${(Math.round(dir) + 180) % 360}deg)"><path d="M12 2 L19.5 20 L12 15.5 L4.5 20 Z" fill="${inne ? "currentColor" : "none"}" stroke="currentColor" stroke-width="2" stroke-linejoin="miter"/></svg>` : h ? "<b>–</b>" : ""}</div>`;
      }
      return `<div class="tk${mork ? " mork" : ""}${!h ? " vaert" : ""}${c.i === sel ? " valgt" : ""}" data-k="${k}" data-i="${c.i}" data-hh="${String(c.hh).padStart(2, "0")}"><div class="bst${h && best.has(c.i) ? " pa" + (st >= 4 ? " k" : "") : ""}"></div>${seg}${surf}${ekstra}<div class="vnd">${vind}</div></div>`;
    }).join("");
    const valgbare = cols.map((c, k)=> c.i >= 0 ? k : -1).filter(k=> k >= 0);
    const kSel = Math.max(0, cols.findIndex(c=> c.i === sel));
    const rute = `grid-template-columns:repeat(${n},minmax(0,1fr))`;
    const inni = `<div class="tikk" style="${rute}" aria-hidden="true">${tikk}${harNaa ? `<em style="left:${(xAv(cols, naa) * 100).toFixed(2)}%">${esc(STR.spot.naa)}</em>` : ""}</div>
      <div class="skygge" style="${rute}" aria-hidden="true">${skygge}</div>
      <div class="kolonner" style="${rute}" aria-hidden="true">${kol}${ideal!=null ? `<div class="ideal" style="--y:${px(ideal)}px"><span>${esc(nf1.format(ideal))} m</span></div>` : ""}</div>
      <div class="tide"></div>
      <div class="ring" aria-hidden="true" style="left:${(kSel / n * 100).toFixed(3)}%;width:${(100 / n).toFixed(3)}%"></div>
      ${harNaa ? `<div class="naalinje" aria-hidden="true" style="left:${(xAv(cols, naa) * 100).toFixed(2)}%"></div>` : ""}`;
    const R = STR.web ? STR.web.rader : null;
    const etiketter = bred && R ? `<div class="tetik" aria-hidden="true"><span>${esc(R.kl)}</span><span>${esc(R.vurdering)}</span><span>${esc(STR.spot.surf)} <small class="enhet">m</small></span>
      <span>${esc(STR.spot.svellFra)}</span><span>${esc(STR.spot.vind)} <small class="enhet">m/s</small></span><span>${esc(STR.spot.tidevann)}<small class="u">${esc(R.tideSub)}</small></span></div>` : "";
    return `<div class="tstripe${bred ? " bred" : ""}${ideal!=null ? " med-ideal" : ""}" id="tstripe" data-day="${d.key}" data-n="${n}">
      ${etiketter}<div class="tflate">${inni}</div>
      <label class="sr" for="tstripeVelg">${esc(STR.spot.velgTime)}</label>
      <input class="sr" type="range" id="tstripeVelg" min="${valgbare[0]}" max="${valgbare[valgbare.length-1]}" step="1" value="${kSel}" aria-valuetext="${esc(ariaTime(s, cols[kSel], H, best, ev))}">
    </div>`;
  }

  function tegnTide(){
    // tidevannskurven i ekte piksler (bredden er kjent først når stripa står i siden)
    const {root, s, cols, H} = cur; const boks = $("#tstripe .tide", root); if(!boks || !window.Tidevann) return;
    const TH = cur.bred ? TIDE_H_BRED : TIDE_H;
    const ev = Tidevann.hendelser(s); const [t0, t1] = spenn(cols);
    const W = Math.round(boks.clientWidth); if(!W || ev.length < 2){ boks.innerHTML = ""; return; }
    const pkt = [];
    for(let ms = t0; ms <= t1 + 1; ms += 6e5){ const lv = Tidevann.nivaa(ev, ms); if(lv) pkt.push({ms, cm: lv.cm}); }
    if(pkt.length < 2){ boks.innerHTML = ""; return; }
    const inne = ev.filter(e=> e.ms >= t0 && e.ms <= t1);
    const cms = pkt.map(p=> p.cm).concat(inne.map(e=> e.cm));
    let lo = Math.min(...cms), hi = Math.max(...cms); if(hi - lo < 20){ const m = (hi + lo) / 2; lo = m - 10; hi = m + 10; }
    const Y0 = cur.bred ? 22 : 17, Y1 = cur.bred ? 46 : 35;
    const x = (ms)=> xAv(cols, ms) * W, y = (cm)=> Y1 - (cm - lo) / (hi - lo) * (Y1 - Y0);
    // båndet: nivåene spoten liker, per halve syklus (tersklene er brøker mellom fjære og flo)
    let band = "";
    const r = s.tide_regel;
    if(r && r.prefer && r.prefer.length){
      const iv = Tidevann.intervaller(r);
      for(let i = 0; i < ev.length - 1; i++){
        const a = ev[i], b = ev[i+1]; if(a.type === b.type || b.ms < t0 || a.ms > t1) continue;
        const fj = a.type === "fjære" ? a : b, fl = a.type === "fjære" ? b : a;
        const xa = Math.max(0, x(Math.max(a.ms, t0))), xb = Math.min(W, x(Math.min(b.ms, t1)));
        for(const [f0, f1v] of iv){
          const yTopp = f1v >= 1 ? 0 : Math.max(0, y(fj.cm + f1v * (fl.cm - fj.cm))), yBunn = f0 <= 0 ? TH : Math.min(TH, y(fj.cm + f0 * (fl.cm - fj.cm)));
          if(yBunn > yTopp && xb > xa) band += `<rect class="bnd" x="${xa.toFixed(1)}" y="${yTopp.toFixed(1)}" width="${(xb - xa).toFixed(1)}" height="${(yBunn - yTopp).toFixed(1)}"/>`;
        }
      }
    }
    // kurven i to strøk: hel, og stiplet (i blekk, S33 c) over timene der tidevannet koster poeng (tideLost(): faded_tide og den lokale tidevannsregelen)
    const koster = (ms)=>{ const c = cols.reduce((n, k)=> Math.abs(k.ms - ms) < Math.abs(n.ms - ms) ? k : n, cols[0]); const h = c.i >= 0 ? s.hours[c.i] : null; return !!h && !h._forbud && !H.mork(h) && H.known(h) && tideLost(h) > 0; };
    const strok = {false: "", true: ""};
    for(let i = 0; i < pkt.length - 1; i++){
      const k = koster((pkt[i].ms + pkt[i+1].ms) / 2);
      strok[k] += `M${x(pkt[i].ms).toFixed(1)} ${y(pkt[i].cm).toFixed(1)}L${x(pkt[i+1].ms).toFixed(1)} ${y(pkt[i+1].cm).toFixed(1)}`;
    }
    const merker = inne.map(e=>{
      const ex = x(e.ms), ey = y(e.cm), lav = e.type === "fjære";
      const anker = ex < 34 ? "start" : ex > W - 34 ? "end" : "middle";
      return `<circle class="eks" cx="${ex.toFixed(1)}" cy="${ey.toFixed(1)}" r="2.5"/><text x="${ex.toFixed(1)}" y="${(lav ? ey + 15 : ey - 7).toFixed(1)}" text-anchor="${anker}">${esc(lav ? STR.spot.lav : STR.spot.hoy)} ${fmtTime.format(new Date(e.ms))}</text>`;
    }).join("");
    const deler = inne.map(e=> e.type === "fjære" ? STR.spot.tideLav(fmtTime.format(new Date(e.ms)), f1(e.cm)) : STR.spot.tideHoy(fmtTime.format(new Date(e.ms)), f1(e.cm)));
    const etikett = STR.spot.tideAria(deler.length ? deler : [STR.spot.tidevann.toLowerCase()], (r && r.prefer && r.prefer.length) || tideLowBest(s) ? Tidevann.prefTekst(s) : "");   // også «Best på lavt vann» (regel på vannstanden, feiljegeren V1 24.11.2026)
    boks.innerHTML = `<svg class="tsvg" viewBox="0 0 ${W} ${TH}" width="${W}" height="${TH}" role="img" aria-label="${esc(etikett)}">${band}
      <path class="linje" d="${strok[false]}"/>${strok[true] ? `<path class="koster" d="${strok[true]}"/>` : ""}${merker}<circle class="valgt" r="4.5"/></svg>`;
    cur.geo = {x, y, ev};
    flyttTide();
  }
  function flyttTide(){
    const c = cur.cols[cur.k], g = cur.geo, m = $("#tstripe .tsvg .valgt", cur.root); if(!m || !g || !c) return;
    const lv = Tidevann.nivaa(g.ev, c.ms);
    if(!lv){ m.style.display = "none"; return; }
    m.style.display = ""; m.setAttribute("cx", g.x(c.ms).toFixed(1)); m.setAttribute("cy", g.y(lv.cm).toFixed(1));
  }

  function velg(k){
    // flytter ringen, sirkelen på kurven og glidebryteren til kolonne k - uten å tegne stripa på nytt
    if(!cur) return; const n = cur.cols.length; cur.k = k;
    const ring = $("#tstripe .ring", cur.root); if(ring) ring.style.left = (k / n * 100).toFixed(3) + "%";
    // tapte poeng vises bare for valgt time (fase 3 punkt 4)
    cur.root.querySelectorAll("#tstripe .tk.valgt").forEach(e=> e.classList.remove("valgt"));
    const tk = $(`#tstripe .tk[data-k="${k}"]`, cur.root); if(tk) tk.classList.add("valgt");
    const inp = $("#tstripeVelg", cur.root);
    if(inp){ inp.value = String(k); inp.setAttribute("aria-valuetext", ariaTime(cur.s, cur.cols[k], cur.H, cur.best, cur.geo ? cur.geo.ev : (window.Tidevann ? Tidevann.hendelser(cur.s) : []))); }
    flyttTide();
  }

  function mount(root, s, d, sel, best, H, onPick){
    const el = $("#tstripe", root); if(!el) return;
    const cols = kolonner(s, d, sel, H);
    const bred = el.classList.contains("bred"), flate = $(".tflate", el) || el;   // nettsiden: kolonnene står til høyre for etikettene
    cur = {root, s, d, cols, H, best, onPick, k: Math.max(0, cols.findIndex(c=> c.i === sel)), ned: false, geo: null, bred};
    const meg = cur;
    tegnTide();
    const pick = (clientX)=>{
      const r = flate.getBoundingClientRect(); const n = cols.length;
      let k = Math.max(0, Math.min(n - 1, Math.floor((clientX - r.left) / (r.width / n))));
      while(k < n - 1 && cols[k].i < 0) k++;   // «har vært» kan ikke velges: nærmeste time med varsel
      if(cols[k].i < 0 || k === meg.k) return;
      velg(k); onPick(cols[k].i);
    };
    flate.addEventListener("pointerdown", (e)=>{ if(e.pointerType==="mouse" && e.button!==0) return; if(e.target.closest("input")) return; meg.ned = true; pick(e.clientX); });
    // nettsiden: musa over en time velger den (SPEC §6C punkt 5); ellers bare mens fingeren eller knappen er nede
    flate.addEventListener("pointermove", (e)=>{ if(meg.ned || (bred && e.pointerType==="mouse")) pick(e.clientX); });
    const opp = ()=>{ meg.ned = false; };
    flate.addEventListener("pointerup", opp); flate.addEventListener("pointercancel", opp); flate.addEventListener("pointerleave", opp);
    const inp = $("#tstripeVelg", root);
    if(inp) inp.addEventListener("input", ()=>{ const k = +inp.value; if(cols[k] && cols[k].i >= 0 && k !== meg.k){ velg(k); onPick(cols[k].i); } });
    if(!mount.lytter){
      mount.lytter = true; let vent = 0;
      window.addEventListener("resize", ()=>{ clearTimeout(vent); vent = setTimeout(()=>{ if(cur && document.contains($("#tstripe", cur.root))) tegnTide(); }, 120); });
    }
  }

  window.Timestripe = { html, mount, velg, kolonner };
})();
