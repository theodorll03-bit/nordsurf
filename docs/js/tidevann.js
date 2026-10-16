/* Nordsurf: tidevannskortet på spotsiden (Theodor 16.10.2026, fasit: prototypen i privat/design/).

   Tegnes i ekte piksler: viewBox = beholderens faktiske bredde (ResizeObserver tegner på nytt ved endring),
   fast høyde og font-size i px - 12 px tekst er 12 px både på mobil og PC (feilen før: tekst i en SVG med fast
   viewBox som ble skalert til kortets bredde).

   Data: Kartverkets flo og fjære (s.tide_events, høyde over sjøkartnull). Henteren lagrer bare ekstremene, så
   kurven mellom dem er en cosinus (samme regel som henteren bruker for vannstanden time for time, fetcher/tide.py)
   - det står i kortet. Mangler tidevann for dagen: «Tidevann mangler», aldri 0 (grunnregelen).

   Foretrukket vannstand: s.tide_regel fra publish.py - nøyaktig samme regel og terskler som ratingen
   (rating._tide_prefer, tide.state_at: lav < lav_maks, høy > hoy_min av veien fra fjære til flo). Ingen tall her.

   Valgt tidspunkt er sidens tilstand (S.idx + S.tideMin i spot.js) - kortet har ingen egen. Dra/trykk i grafen
   flytter det i kvarter-steg (live mens man drar, lagres når man slipper), piltaster når grafen har fokus.
   Ren visning: ratingen røres ikke. */
(function(){
  const H = 200, T = 34, B = 158, PAD = 6, MINI_H = 96;
  const DAY = 864e5, MIN = 6e4;
  const animert = new Set();          // kortet animeres bare første gang det kommer inn i bildet (per spot)
  const forrigeX = {};                // markøren glir fra forrige posisjon ved timebytte
  const reduser = ()=> matchMedia("(prefers-reduced-motion: reduce)").matches;
  const f1 = (cm)=> (cm/100).toFixed(1).replace(".", ",");
  const HM = new Intl.DateTimeFormat("nb-NO", {hour:"2-digit", minute:"2-digit", timeZone: TZ});
  const hm = (ms)=> HM.format(new Date(ms));

  function offset(ms){ return window.Spot && Spot.tzOffsetMs ? Spot.tzOffsetMs(new Date(ms)) : 0; }
  function dagen(ms){
    // norsk døgn rundt ms: [midnatt, neste midnatt) i UTC-ms (25 eller 23 timer ved sommertidsskifte)
    const lokal = new Date(ms + offset(ms));
    const y = lokal.getUTCFullYear(), m = lokal.getUTCMonth(), d = lokal.getUTCDate();
    const start = (dd)=>{ const g = Date.UTC(y, m, dd); return g - offset(g - offset(g)); };
    return [start(d), start(d + 1)];
  }
  function hendelser(s){
    return (s.tide_events || []).filter(e=> e && e.cm!=null && e.time).map(e=>({ms: new Date(e.time).getTime(), cm: e.cm, type: e.type}))
      .sort((a, b)=> a.ms - b.ms);
  }
  function nivaa(ev, ms){
    // cosinus mellom to motsatte ekstremer (som fetcher/tide.py) - null utenfor dataene
    for(let i = 0; i < ev.length - 1; i++){
      const a = ev[i], b = ev[i+1];
      if(ms >= a.ms && ms <= b.ms && a.type !== b.type){
        const f = (1 - Math.cos(Math.PI * (ms - a.ms) / (b.ms - a.ms))) / 2;
        return {cm: a.cm + (b.cm - a.cm) * f, stiger: b.type === "flo", a, b};
      }
    }
    return null;
  }
  function nesteEkstrem(ev, ms){ return ev.find(e=> e.ms > ms) || null; }
  function omTekst(ms){ const m = Math.max(0, Math.round(ms / MIN)), t = Math.floor(m / 60); return `om ${t ? t + " t " : ""}${m % 60} min`; }
  const PIL = (opp)=> `<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M7 ${opp?11:3}V${opp?3:11}M3.5 ${opp?6.5:7.5}L7 ${opp?3:11}l3.5 ${opp?3.5:-3.5}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  function prefTekst(s){
    const r = s.tide_regel;
    if(!r || !r.prefer || !r.prefer.length) return STR.tidePref(null);
    const rekke = ["lav", "middels", "høy"].filter(x=> r.prefer.includes(x));
    const til = rekke.length === 2 && Math.abs(["lav", "middels", "høy"].indexOf(rekke[0]) - ["lav", "middels", "høy"].indexOf(rekke[1])) === 1;
    return `${s.name} er best på ${rekke.length === 1 ? rekke[0] : til ? rekke[0] + " til " + rekke[1] : rekke.join(" og ")} vannstand`;
  }
  function intervaller(r){
    // spotens foretrukne nivåer (0 = fjære, 1 = flo) som sammenhengende intervaller, fra regelens terskler
    const del = {lav: [0, r.lav_maks], middels: [r.lav_maks, r.hoy_min], "høy": [r.hoy_min, 1]};
    const iv = ["lav", "middels", "høy"].filter(x=> r.prefer.includes(x)).map(x=> del[x].slice());
    const ut = [];
    for(const v of iv){ if(ut.length && Math.abs(ut[ut.length-1][1] - v[0]) < 1e-9) ut[ut.length-1][1] = v[1]; else ut.push(v); }
    return ut;
  }

  /* ---------- toppen av kortet ---------- */
  function lesHtml(s, ev, ms, nowMs, erNa){
    const lv = nivaa(ev, ms);
    if(!lv) return `<div class="tv-les"><span class="tv-h">–</span><span class="tv-neste">Tidevann mangler</span></div>`;
    const nx = nesteEkstrem(ev, ms);
    const neste = !nx ? "" : erNa
      ? `<b>${cap(nx.type)} ${hm(nx.ms)}</b> · <span class="num">${f1(nx.cm)} m</span> · ${omTekst(nx.ms - nowMs)}`
      : `Neste: <b>${cap(nx.type)} ${hm(nx.ms)}</b> · <span class="num">${f1(nx.cm)} m</span>`;
    return `<div class="tv-les"><span class="tv-h num">${f1(lv.cm)}<small>m</small></span>
      <span class="tv-trend">${PIL(lv.stiger)}${lv.stiger ? "Stiger" : "Synker"}</span><span class="tv-neste">${neste}</span></div>`;
  }
  function ariaTekst(ev, ms){
    const lv = nivaa(ev, ms);
    return lv ? `${hm(ms)}, ${f1(lv.cm)} meter, ${lv.stiger ? "stiger" : "synker"}` : `${hm(ms)}, tidevann mangler`;
  }

  /* ---------- kortet (HTML-skallet; SVG-en tegnes av mount() når bredden er kjent) ---------- */
  function html(s, ms, nowMs, erNa){
    const ev = hendelser(s); const [d0, d1] = dagen(ms);
    const harDag = ev.some(e=> e.ms <= d0) && ev.some(e=> e.ms >= d1) || !!nivaa(ev, ms);
    if(!ev.length || !harDag) return `<div class="kort tide" id="tideKort"><div class="k">Tidevann</div><p class="tv-mangler">Tidevann mangler</p></div>`;
    const pref = s.tide_regel && s.tide_regel.prefer && s.tide_regel.prefer.length;
    return `<div class="kort tide" id="tideKort"><div class="k">Tidevann</div>
      ${lesHtml(s, ev, ms, nowMs, erNa)}
      <div class="tv-graf" id="tideGraf" role="slider" tabindex="0" aria-label="Tidspunkt i tidevannsgrafen" aria-valuemin="0" aria-valuemax="24"
        aria-valuenow="${((ms - d0) / 36e5).toFixed(2)}" aria-valuetext="${esc(ariaTekst(ev, ms))}"></div>
      <div class="tv-fot"><span>${pref ? `<span class="tv-sw" aria-hidden="true"></span>` : ""}${esc(prefTekst(s))}</span><span>Kilde: Kartverket · høyde over sjøkartnull · beregnet kurve (cosinus) mellom flo og fjære</span></div></div>`;
  }

  /* ---------- tegningen ---------- */
  function tegn(el, s, ms, nowMs, mini){
    const ev = hendelser(s); const [d0, d1] = dagen(ms);
    const W = Math.max(240, Math.round(el.clientWidth || 0)); const Hh = mini ? MINI_H : H;
    const top = mini ? 18 : T, bunn = mini ? Hh - 22 : B;
    const L = PAD, R = W - PAD;
    const X = (t)=> L + (R - L) * (t - d0) / (d1 - d0);
    const pts = []; for(let i = 0; i <= 240; i++){ const t = d0 + (d1 - d0) * i / 240; const lv = nivaa(ev, t); pts.push(lv ? [t, lv.cm, lv] : null); }
    const ok = pts.filter(Boolean);
    if(ok.length < 2){ el.innerHTML = `<p class="tv-mangler">Tidevann mangler</p>`; return null; }
    const dagEv = ev.filter(e=> e.ms >= d0 && e.ms <= d1);
    const cms = ok.map(p=> p[1]).concat(dagEv.map(e=> e.cm));
    const lo = Math.min(...cms) - 12, hi = Math.max(...cms) + 12;
    const Y = (cm)=> bunn - (bunn - top) * (cm - lo) / (hi - lo);
    let d = "", pen = false;
    for(const p of pts){ if(!p){ pen = false; continue; } d += `${pen ? "L" : "M"}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`; pen = true; }
    const forste = ok[0], siste = ok[ok.length - 1];
    const omraade = `${d}L${X(siste[0]).toFixed(1)} ${bunn + 10}L${X(forste[0]).toFixed(1)} ${bunn + 10}Z`;
    // foretrukket vannstand (Theodor 16.10): selve kurven tegnes tykkere der vannstanden er innenfor spotens preferanse -
    // ikke et bånd. Andelen av veien fra fjære til flo regnes per halvsyklus (som tide.state_at), så grensen følger kurven.
    let dPref = "";
    const r = s.tide_regel;
    if(!mini && r && r.prefer && r.prefer.length){
      const iv = intervaller(r);
      const inne = (p)=>{
        const lv = p[2], fj = lv.a.type === "fjære" ? lv.a : lv.b, fl = lv.a.type === "flo" ? lv.a : lv.b;
        if(fl.cm === fj.cm) return false;
        const f = (p[1] - fj.cm) / (fl.cm - fj.cm);
        return iv.some(([l0, l1])=> f >= l0 - 1e-9 && f <= l1 + 1e-9);
      };
      let penP = false;
      for(const p of pts){
        if(!p || !inne(p)){ penP = false; continue; }
        dPref += `${penP ? "L" : "M"}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`; penP = true;
      }
    }
    const smal = W < 520 || mini;
    const etiketter = mini ? "" : dagEv.map((e, i)=>{
      const x = X(e.ms), y = Y(e.cm), opp = e.type === "flo", kant = smal ? 48 : 64;
      const anker = x < kant ? "start" : x > W - kant ? "end" : "middle";
      const lx = anker === "start" ? Math.max(L, x - 6) : anker === "end" ? Math.min(R, x + 6) : x;
      const tekst = smal ? `${hm(e.ms)}<tspan class="t"> ${f1(e.cm)}</tspan>` : `${cap(e.type)} <tspan class="t">${hm(e.ms)} · ${f1(e.cm)} m</tspan>`;
      return `<g class="tv-ext" style="animation-delay:${(.7 + i * .12).toFixed(2)}s"><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5"/>`
        + `<text class="tv-lbl" x="${lx.toFixed(1)}" y="${(opp ? y - 12 : y + 20).toFixed(1)}" text-anchor="${anker}">${tekst}</text></g>`;
    }).join("");
    const akse = [0, 6, 12, 18, 24].map((t, k)=>`<text class="tv-ax" x="${X(d0 + t * 36e5).toFixed(1)}" y="${Hh - 4}" text-anchor="${k === 0 ? "start" : k === 4 ? "end" : "middle"}">${String(t).padStart(2, "0")}</text>`).join("")
      + [0, 3, 6, 9, 12, 15, 18, 21, 24].map((t)=>`<line class="tv-tick" x1="${X(d0 + t * 36e5).toFixed(1)}" x2="${X(d0 + t * 36e5).toFixed(1)}" y1="${bunn + 10}" y2="${bunn + 15}"/>`).join("");
    // delen av dagen som har gått dempes - bare i dag
    const iDag = nowMs >= d0 && nowMs < d1;
    const gatt = iDag ? `<rect class="tv-past" x="0" y="0" width="${Math.max(0, X(nowMs)).toFixed(1)}" height="${bunn + 10}"/>` : "";
    const id = `${esc(s.id)}${mini ? "-m" : ""}`;
    el.innerHTML = `<svg class="tv-svg${mini ? " mini" : ""}" viewBox="0 0 ${W} ${Hh}" width="${W}" height="${Hh}" aria-hidden="true">
      <defs><linearGradient id="tvWg-${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" class="tv-g0"/><stop offset="1" class="tv-g1"/></linearGradient></defs>
      <path class="tv-area" d="${omraade}" fill="url(#tvWg-${id})"/>
      <path class="tv-curve" d="${d}"/>
      ${dPref ? `<path class="tv-pref" d="${dPref}"/>` : ""}
      ${gatt}
      <g>${etiketter}</g><g>${akse}</g>
      <g class="tv-marker"><line class="tv-mline" x1="0" x2="0" y1="${top - 14}" y2="${bunn + 10}"/><circle class="tv-ring" r="${mini ? 5 : 7}"/><circle class="tv-dot" r="${mini ? 5 : 7}"/></g>
    </svg>`;
    const curve = el.querySelector(".tv-curve"); if(curve && curve.getTotalLength) curve.style.setProperty("--len", Math.ceil(curve.getTotalLength()));
    return {ev, X, Y, d0, d1, L, R};
  }
  function plasserMarkor(el, g, ms, glid){
    const m = el.querySelector(".tv-marker"); if(!m || !g) return;
    const lv = nivaa(g.ev, ms);
    m.style.display = lv ? "" : "none"; if(!lv) return;
    const x = g.X(ms), y = g.Y(lv.cm);
    m.querySelectorAll("circle").forEach(c=> c.setAttribute("cy", y.toFixed(1)));
    m.style.transition = glid ? "" : "none";
    m.setAttribute("transform", `translate(${x.toFixed(1)} 0)`);
  }

  /* ---------- montering på spotsiden ---------- */
  function mount(root, s, ms, opts){
    const o = opts || {};
    const nowMs = o.nowMs != null ? o.nowMs : Date.now();
    // kompakt kurve i timegrafen (samme regel og data, uten etiketter)
    root.querySelectorAll(".tv-mini[data-t]").forEach(el=>{
      const t = +el.dataset.t; const draw = ()=>{ const g = tegn(el, s, t, nowMs, true); plasserMarkor(el, g, t, false); };
      draw(); if(window.ResizeObserver){ const ro = new ResizeObserver(()=>{ if(!el.isConnected){ ro.disconnect(); return; } draw(); }); ro.observe(el); }
    });
    const el = root.querySelector("#tideGraf"); if(!el) return;
    const kort = root.querySelector("#tideKort");
    let g = null, cur = ms;
    const intro = !animert.has(s.id) && !reduser();
    const draw = ()=>{
      g = tegn(el, s, cur, nowMs, false); if(!g) return;
      const svg = el.querySelector("svg");
      if(intro && !animert.has(s.id)) svg.classList.add("intro");
      const fra = forrigeX[s.id];
      if(fra != null && !reduser() && Math.abs(fra - g.X(cur)) > 0.5){ const lv0 = nivaa(g.ev, cur);
        const mk = el.querySelector(".tv-marker"); mk.style.transition = "none"; mk.setAttribute("transform", `translate(${fra.toFixed(1)} 0)`);
        if(lv0) mk.querySelectorAll("circle").forEach(c=> c.setAttribute("cy", g.Y(lv0.cm).toFixed(1)));
        requestAnimationFrame(()=> requestAnimationFrame(()=> plasserMarkor(el, g, cur, true)));
      } else plasserMarkor(el, g, cur, false);
      forrigeX[s.id] = g.X(cur);
    };
    draw();
    if(window.ResizeObserver){ const ro = new ResizeObserver(()=>{ if(!el.isConnected){ ro.disconnect(); return; } const w = el.clientWidth; if(w && g && Math.abs(w - (g.R + PAD)) > 1) draw(); }); ro.observe(el); }
    if(intro && window.IntersectionObserver){
      const io = new IntersectionObserver((ents)=>{ if(ents.some(e=> e.isIntersecting)){ io.disconnect(); animert.add(s.id); const svg = el.querySelector("svg"); if(svg) svg.classList.add("go"); } }, {threshold: .35});
      io.observe(el);
    } else animert.add(s.id);
    // samhandling: dra/trykk (kvarter-steg, live) og piltaster - valgt tid er sidens tilstand (o.onSelect)
    const oppdater = (t)=>{
      cur = t; plasserMarkor(el, g, t, false); forrigeX[s.id] = g ? g.X(t) : null;
      const les = kort && kort.querySelector(".tv-les"); if(les) les.outerHTML = lesHtml(s, hendelser(s), t, nowMs, false);
      el.setAttribute("aria-valuenow", ((t - g.d0) / 36e5).toFixed(2)); el.setAttribute("aria-valuetext", ariaTekst(hendelser(s), t));
    };
    const tFra = (x)=>{ const r = el.getBoundingClientRect(); const f = Math.max(0, Math.min(1, ((x - r.left) - g.L) / (g.R - g.L)));
      const t = g.d0 + f * (g.d1 - g.d0); return Math.min(g.d1 - 15 * MIN, Math.round(t / (15 * MIN)) * 15 * MIN); };
    let drar = false;
    el.addEventListener("pointerdown", (e)=>{ if(!g || (e.pointerType === "mouse" && e.button !== 0)) return; drar = true; try{ el.setPointerCapture(e.pointerId); }catch(_){} oppdater(tFra(e.clientX)); });
    el.addEventListener("pointermove", (e)=>{ if(drar) oppdater(tFra(e.clientX)); });
    const slipp = ()=>{ if(!drar) return; drar = false; if(o.onSelect) o.onSelect(cur, false); };
    el.addEventListener("pointerup", slipp); el.addEventListener("pointercancel", slipp);
    el.addEventListener("keydown", (e)=>{
      if(!g) return;
      const steg = e.key === "ArrowRight" || e.key === "ArrowUp" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowDown" ? -1 : 0;
      if(!steg) return; e.preventDefault();
      const t = Math.max(g.d0, Math.min(g.d1 - 15 * MIN, Math.round(cur / (15 * MIN)) * 15 * MIN + steg * 15 * MIN));
      oppdater(t); if(o.onSelect) o.onSelect(t, true);
    });
  }

  window.Tidevann = { html, mount, tegn, nivaa, hendelser, dagen, prefTekst, intervaller };
})();
