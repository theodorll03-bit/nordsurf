/* Nordsurf: spotsiden (Theodor 14.10.2026, punkt 4 + HIG 9).

   Rekkefølge: vurdering, fire kort (surf, svell, vind, energi), langtidsvarsel
   med dagfaner og timegraf, minikart, tidevann, vær, «Hvorfor denne
   vurderingen?», «Logg en økt her», kilder.
   På mobil (design B 4.0, SPEC §6B) tegner renderMobil() siden: kornfoto, dom, time, timestripe og skive.

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

  /* ---------- mobil (design B 4.0, SPEC §6B) ---------- */
  // Rekkefølge: kornfoto med tilbake- og favorittknapp, navn, metalinje, dagens dom, faktalinje, valgt time
  // (svell stort, så surf, vind og tidevann), time for time, retningsskiva, «Hvorfor», logg og kilder.
  // Ren visning som resten av fila. PC-oppsettet i render() er urørt til steg 6.
  const midtPaa = (key)=> new Date(key + "T11:00:00Z");
  // Krediteringen under bildet, med lisensnavnet som lenke (CC BY 4.0 krever lenke til lisensen der det er praktisk mulig)
  function kreditHtml(){
    const B = window.SPOTBILDER, i = B.lisens && B.lisens_url ? B.kredit.indexOf(B.lisens) : -1;
    if(i < 0) return esc(B.kredit);
    return `${esc(B.kredit.slice(0, i))}<a href="${esc(B.lisens_url)}" target="_blank" rel="noopener license">${esc(B.lisens)}</a>${esc(B.kredit.slice(i + B.lisens.length))}`;
  }
  const lengsteOrd = (navn)=> Math.max(...String(navn).split(/[\s-]+/).map(o=> o.length), 1);
  const ukedagKort = (at)=> fmtWdShort.format(at).replace(/\.$/, "");
  const stegAv = (s, idxs)=> idxs.length >= 2 && (Date.parse(s.hours[idxs[1]].t) - Date.parse(s.hours[idxs[0]].t)) >= 2 * 36e5 ? 6 : 1;
  function valgMobil(s, S){
    // dagen og timen siden viser. Åpnet på «nå» (S.idx null): i dag og timen nå så lenge den er lys, ellers
    // dagens beste time - og i morgen når det er under to lyse timer igjen (SpotGraf.defaultDay, Theodor 15.10).
    const n = H.nowIdx(s), idag = dayKey(new Date());
    const std = SpotGraf.defaultDay(s, n, H);   // setter også hjelperne SpotGraf.days() og bestOfDay() bruker
    const dager = SpotGraf.days(s);
    let idx = S.idx!=null && s.hours.length ? Math.max(0, Math.min(s.hours.length - 1, S.idx)) : null;
    const key = idx!=null ? H.dkOf(s.hours[idx].t) : (std || idag);
    let d = dager.find(x=> x.key===key);
    if(!d){   // dagen står ikke i rekka: i dag etter at lyset er over
      const idxs = []; s.hours.forEach((h, i)=>{ if(H.dkOf(h.t)===key) idxs.push(i); });
      d = {key, idxs, step: stegAv(s, idxs)};
    }
    if(idx==null && d.idxs.length) idx = key===idag && d.idxs.includes(n) && H.usable(s.hours[n]) ? n : SpotGraf.bestOfDay(s, d);
    return {n, dager: dager.some(x=> x.key===d.key) ? dager : [d, ...dager], d, idx};
  }
  function dagsdom(s, d){
    // Dagens tall. Så lenge dagen står i dagssammendragene er det samme tall som Hjem og ukeoversikten viser
    // (H.dayBest). Lenger ut leses det av dagens timer med samme regel som publish.best_hour() og day_summary():
    // beste lyse time, «miss» når tall eller lys mangler, «dark» når hele dagen er mørk.
    if((s.dager || []).some(x=> x.d===d.key)) return H.dayBest(s, d.key);
    const tom = (cls)=> ({cls, st: null, h: null, t: null});
    if(H.forbudInfo && H.forbudInfo(s, Date.parse(d.key + "T12:00:00Z"))) return tom("forbud");
    let best = null, miss = false, lys = false, ukjent = false;
    for(const i of d.idxs){
      const h = s.hours[i];
      if(H.mork(h)) continue;
      if(!H.usable(h)){ ukjent = true; if(!H.known(h) || H.stars(h) >= 1) miss = true; continue; }
      lys = true;
      if(!H.known(h)){ miss = true; continue; }
      const c = {i, st: H.stars(h), hh: h.surf_height || 0};
      if(!best || c.st > best.st || (c.st===best.st && c.hh > best.hh)) best = c;
    }
    if(!(best && best.st >= 1)){
      if(miss || (!lys && ukjent)) return tom("miss");
      if(!lys) return tom("dark");
    }
    if(!best) return tom("miss");
    // vinduet: timene på rad rundt den beste med samme tall
    const k = d.idxs.indexOf(best.i); let a = k, z = k;
    const lik = (j)=>{ const h = s.hours[d.idxs[j]]; return H.usable(h) && H.known(h) && H.stars(h)===best.st; };
    while(a > 0 && lik(a - 1)) a--;
    while(z < d.idxs.length - 1 && lik(z + 1)) z++;
    const h = s.hours[best.i];
    return {cls: `r-${Math.min(5, best.st)}`, st: best.st, h, t: h.t, start: s.hours[d.idxs[a]].t, slutt: s.hours[d.idxs[z]].t};
  }
  function besteSett(s, d, b){
    // timene i dagens beste vindu (streken over kolonnene i timestripa); ingen når dagen ikke har surf
    if(b.st==null || b.st < 1 || !b.start) return new Set();
    const a = Date.parse(b.start), z = Date.parse(b.slutt || b.start);
    return new Set(d.idxs.filter(i=>{ const ms = Date.parse(s.hours[i].t); return ms >= a && ms <= z; }));
  }
  const domOrd = (b)=> b.cls==="forbud" ? STR.hjem.forbud : b.cls==="dark" ? STR.hjem.morktOrd : b.cls==="over" ? STR.hjem.over : b.cls==="miss" ? STR.hjem.mangler : ratingWord(b.h);
  function domHtml(s, d, b){
    const n = b.st!=null ? Math.min(5, b.st) : null;
    // beste vindu som klokkeslett; dager med seks timer mellom varslene har bare tidspunktet
    const vindu = n!=null && n >= 1 ? (d.step===1 ? H.vinduKl(b.start, b.slutt).join("–") : fmtHour.format(new Date(b.h.t))) : null;
    const setn = H.favSetning(s, b, true);
    return `<div class="dom r-${n!=null ? n : 0}">
        <div class="dom-v">${n!=null ? `<span class="t-tall" role="img" aria-label="${esc(STR.starsAria(n, (b.h && b.h.faded) || 0))}">${n}</span>` : ""}<span class="dom-ord"><b>${esc(domOrd(b))}</b><span class="etikett">${esc(relDay(midtPaa(d.key)))}</span></span></div>
        ${vindu ? `<div class="dom-h"><span class="etikett">${esc(STR.spot.best)}</span><span class="t-vindu">${esc(vindu)}</span></div>` : ""}
      </div>${setn ? `<p class="dom-setn">${esc(setn)}</p>` : ""}`;
  }
  function faktaHtml(s, h, t){
    // bare det vi har data for (SPEC §6B punkt 5)
    const f = [], ld = (s.light_days || {})[dayKey(t)];
    if(ld) f.push(ld.start ? `${STR.spot.lys} ${fmtTime.format(new Date(ld.start))}–${fmtTime.format(new Date(ld.end))}` : STR.lightNone);
    if(h && h.air_temp!=null) f.push(`${STR.spot.luft} ${nf0.format(h.air_temp)}°`);
    if(h && h.water_temp!=null) f.push(`${STR.spot.vann} ${nf0.format(h.water_temp)}°`);
    if(DATA.generated){ const g = new Date(DATA.generated); f.push(`${STR.spot.oppdatert} ${dayKey(g)===dayKey(new Date()) ? "" : relDay(g) + " "}${fmtTime.format(g)}`); }
    return f.length ? `<p class="fakta-linje">${f.map(x=> `<span>${esc(x)}</span>`).join("")}</p>` : "";
  }
  const PIL = (cls, deg, inni)=> `<svg class="ik ${cls}" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"${deg!=null ? ` style="transform:rotate(${Math.round(deg)}deg)"` : ""}>${inni}</svg>`;
  const IK_SVELL = `<path d="M12 2 V13" fill="none" stroke="currentColor" stroke-width="3"/><polygon points="12,21 7.5,13 16.5,13" fill="currentColor"/>`;
  const IK_VIND = `<path d="M12 3 V19 M7.5 14.5 L12 20 L16.5 14.5" fill="none" stroke="currentColor" stroke-width="2.4"/>`;
  const IK_TIDE = `<path d="M2 18 C8 18 10 6 22 6" fill="none" stroke="currentColor" stroke-width="2"/><circle class="pk" cx="9.75" cy="12" r="3.5" stroke="currentColor" stroke-width="2"/>`;
  const IK_SURF = `<path d="M2 18 C7 18 8 7 14 7 C18.5 7 18.5 12.5 15 13.5" fill="none" stroke="currentColor" stroke-width="2.4"/>`;
  function timeDomHtml(s, h, t){
    // timens tall og ord til høyre i seksjonsstarten, med tapte poeng skrevet ut (SPEC §5: «−1 tidevann»).
    // Tallet står i ruta fra ukeoversikten: korall er aldri liten tekst, ruta bærer fargen fra 4.
    if((h && h._forbud) || (H.forbudInfo && H.forbudInfo(s, t.getTime()))) return `<p class="sub">${esc(STR.hjem.forbud)}</p>`;
    if(!h || !H.known(h)) return `<p class="sub">${esc(STR.hjem.mangler)}</p>`;
    if(H.mork(h)) return `<p class="sub">${esc(STR.lightOnly)}</p>`;
    const st = Math.min(5, H.stars(h));
    const tapt = [h.faded_wind ? STR.hjem.taptVind(h.faded_wind) : null, h.faded_tide ? STR.hjem.taptTide(h.faded_tide) : null].filter(Boolean);
    if(h.faded && !tapt.length) tapt.push(`−${h.faded}`);   // eldre varsel uten delingen
    return `<p class="sub tdom r-${st}">${tapt.length ? `<span class="tapt"><i aria-hidden="true"></i>${esc(tapt.join(" · "))}</span>` : ""}<span class="rute r-${st}" role="img" aria-label="${esc(STR.starsAria(st, 0))}">${st}</span><span class="to">${esc(ratingWord(h))}</span></p>`;
  }
  function timeHtml(s, h, t, ev){
    const hh = fmtHour.format(t);
    const maal = (ikon, k, v, enhet, sub)=> `<div class="maal"><span class="etikett">${ikon}${esc(k)}</span><span class="mv">${v}${enhet ? `<small>${enhet}</small>` : ""}</span><span class="mu">${sub || ""}</span></div>`;
    const dir = h && h.dir_offshore!=null ? h.dir_offshore : null;
    const inne = dir!=null && s.swell_window ? inSwellWindow(dir, s) : false;
    const sub = !h ? "" : h.period!=null && dir!=null ? STR.spot.svellSub(nf0.format(h.period), compass(dir), Math.round(dir))
      : [h.period!=null ? `${nf0.format(h.period)} s` : null, dir!=null ? `${STR.fromDir(compass(dir))} ${Math.round(dir)}°` : null].filter(Boolean).join(" · ");
    const svell = `<div class="svell"><div class="etikett">${PIL("sv" + (inne ? " inne" : ""), dir, IK_SVELL)}${esc(STR.spot.svell)}</div>
        ${h && h.swell_offshore!=null ? `<div class="t-svell">${nf1.format(h.swell_offshore)}<small>m</small></div>` : `<div class="svell-sub">${esc(cap(STR.spot.mangler))}</div>`}
        ${sub ? `<div class="svell-sub">${esc(sub)}</div>` : ""}</div>`;
    const rader = [];
    // surf: høyden som vises og settene (regel (c), visHoyde); ordet når tallet er kjent, men ikke pålitelig
    const hoyde = H.heightText(h), vh = visHoyde(h);
    if(hoyde) rader.push(maal(PIL("", null, IK_SURF), STR.spot.surf, esc(hoyde), "m", esc(kroppshoyde(h) || "")));
    else if(h && h.surf_height!=null && (!vh || vh.a <= 0)) rader.push(maal(PIL("", null, IK_SURF), STR.spot.surf, `<span class="ordv">${esc(ratingWord(h))}</span>`, "", ""));
    if(h && h.wind_speed!=null){
      const fra = h.wind_dir!=null ? `${STR.fromDir(compass(h.wind_dir))} ${Math.round(h.wind_dir)}°` : "";
      rader.push(maal(PIL("", h.wind_dir, h.wind_dir!=null ? IK_VIND : ""), STR.spot.vind, nf0.format(h.wind_speed), "m/s",
        esc([[windLabel(h), fra].filter(Boolean).join(" "), h.gust!=null ? STR.gust(nf0.format(h.gust)) : null].filter(Boolean).join(" · "))));
    }
    const lv = window.Tidevann ? Tidevann.nivaa(ev, t.getTime()) : null;
    if(lv){
      // nivået over sjøkartnull og hvor det er på vei: mot neste flo/fjære, eller «snur» nær ekstremen
      const naer = [lv.a, lv.b].find(e=> Math.abs(e.ms - t.getTime()) <= 40 * 6e4);
      const vei = naer ? `${esc(STR.spot.snur)} ${fmtTime.format(new Date(naer.ms))}`
        : `<span aria-hidden="true">${lv.stiger ? "↑" : "↓"}</span><span class="sr">${esc(lv.stiger ? STR.spot.stiger : STR.spot.synker)}, </span> ${esc(lv.stiger ? STR.spot.hoy : STR.spot.lav)} ${fmtTime.format(new Date(lv.b.ms))}`;
      rader.push(maal(PIL("", null, IK_TIDE), STR.spot.tidevann, nf1.format(lv.cm / 100), "m", vei));
    }
    return `<div class="sek-spot"><h2 class="h2">${esc(STR.spot.kl(hh))}</h2>${timeDomHtml(s, h, t)}</div>${svell}${rader.length ? `<div class="maalene">${rader.join("")}</div>` : ""}`;
  }
  function dagvelgerHtml(s, dager, d){
    // én knapp per dag i varselet: ukedag, dagens tall i en rute (som ukeoversikten) og datoen
    return `<div class="dagvelger" role="group" aria-label="${esc(STR.spot.velgDag)}">${dager.map(x=>{
      const b = dagsdom(s, x), at = midtPaa(x.key), n = b.st!=null ? Math.min(5, b.st) : null;
      const cls = n!=null ? `r-${n}` : b.cls==="dark" ? "mork" : b.cls;
      const aria = `${cap(fmtDato.format(at))}: ${n!=null ? STR.starsAria(n, 0) : domOrd(b).toLowerCase()}`;
      return `<button type="button" class="dagknapp" data-day="${x.key}" aria-pressed="${x.key===d.key}" aria-label="${esc(aria)}"><span class="ud">${esc(ukedagKort(at))}</span><span class="rute ${cls}">${n!=null ? n : ""}</span><span class="dt">${at.getUTCDate()}</span></button>`;
    }).join("")}</div>`;
  }
  function renderMobil(root, s, S){
    const {dager, d, idx: idx0} = valgMobil(s, S); let idx = idx0;
    S.tideMin = 0;   // kvarter-forskyvningen hører til tidevannskortet på PC
    const b = dagsdom(s, d), best = besteSett(s, d, b);
    const ev = window.Tidevann ? Tidevann.hendelser(s) : [];
    const timen = ()=>{ const h = idx!=null ? s.hours[idx] || null : null; return {h, t: h ? new Date(h.t) : new Date()}; };
    const over = ()=>{ const {h, t} = timen(); return faktaHtml(s, h, t) + timeHtml(s, h, t, ev); };
    const under = ()=>{
      const {h, t} = timen(), hh = fmtHour.format(t), sikk = h ? sikkerhet(h) : "–";
      return `<div class="sek-spot"><h2 class="h2">${esc(STR.spot.retning(hh))}</h2></div>${window.Skive ? Skive.html(s, h, hh) : ""}${hvorforHtml(h)}
        <div class="logg-her"><button type="button" class="primary" id="loggHer">Logg en økt her</button></div>
        <p class="kilder">${sikk!=="–" ? esc(sikk) + ". " : ""}Varsel fra ${esc(relDay(new Date(DATA.generated)))} kl. ${fmtTime.format(new Date(DATA.generated))}. Kilder: BarentsWatch (kystmodell 100 m), MET Norge, Open-Meteo og Kartverket.</p>`;
    };
    const foto = !!(window.Skive && Skive.harBilde(s.id)), id = encodeURIComponent(s.id);
    const fra = STR.spot.fra[S.from] || null, K = window.KJORETID, kj = H.kjoreText(s.id);
    const at = midtPaa(d.key), omr = s.area || H.regionOf(s);
    const meta = [omr, kj && K ? STR.hjem.kjoreAria(kj, K.fra.navn) : null, `${ukedagKort(at)} ${d.key.slice(8, 10)}.${d.key.slice(5, 7)}`].filter(Boolean).join(" · ");
    const merker = H.merker(s);
    const morkeKol = Timestripe.kolonner(s, d, idx, H).some(c=> c.i >= 0 && H.mork(s.hours[c.i]));
    const tilbakeNa = ()=> S.idx!=null ? `<button type="button" class="tilbakena" id="tilbakeNa">${esc(STR.spot.tilbakeNa)}</button>` : "";
    root.innerHTML = `${typeof staleBanner==="function" ? staleBanner() : ""}<div class="sp-hode${foto ? "" : " uten"}">
        ${foto ? `<img class="sp-foto trykk" src="img/spots/${id}-trykk.jpg" alt="${esc(STR.spot.bildeAlt(s.name))}" loading="lazy" decoding="async"><img class="sp-foto lodd" src="img/spots/${id}-lodd.jpg" alt="${esc(STR.spot.bildeAlt(s.name))}" loading="lazy" decoding="async">` : ""}
        <div class="sp-knapper"><button type="button" class="sp-tilbake" id="spotBack" aria-label="${esc(fra ? STR.spot.tilbakeTil(fra) : STR.spot.tilbake)}"><span><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M15 5 L8 12 L15 19" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="square"/></svg>${esc(fra || STR.spot.tilbake)}</span></button><span class="sp-fav">${favBtnHtml(s.id, false)}</span></div>
        <div class="sp-navn"><h1 class="t-hero${lengsteOrd(s.name) > 8 ? " lang" : ""}" style="--n:${lengsteOrd(s.name)}">${esc(s.name)}</h1></div>
      </div>
      <div class="sp-inn">
        <p class="etikett sp-meta">${esc(meta)}</p>${merker.length ? `<p class="etikett sp-merker">${esc(merker.join(" · "))}</p>` : ""}
        ${foto ? `<p class="kredit">${kreditHtml()}</p>` : ""}
        ${domHtml(s, d, b)}
        <div id="spOver">${over()}</div>
        <div class="sek-spot"><h2 class="h2">${esc(STR.spot.timeForTime)}</h2>${morkeKol ? `<p class="sub">${esc(STR.lightOnly)}</p>` : ""}</div>
        ${dagvelgerHtml(s, dager, d)}
        <div id="spStripe">${Timestripe.html(s, d, idx, best, H)}</div>
        <div class="sp-tilbakena" id="spTilbakeNa">${tilbakeNa()}</div>
        <div id="spUnder">${under()}</div>
      </div>`;
    const heleSiden = (etter)=>{
      // nytt valg som bytter dag: tegn alt på nytt uten å hoppe i siden eller i dagrekka
      const y = window.scrollY, dv = $(".dagvelger", root), x = dv ? dv.scrollLeft : 0;
      renderMobil(root, s, S);
      const dv2 = $(".dagvelger", root); if(dv2) dv2.scrollLeft = x;
      window.scrollTo(0, y); if(etter) etter();
    };
    const kobleTilbakeNa = ()=>{ const tn = $("#tilbakeNa", root); if(tn) tn.onclick = ()=>{ S.idx = null; heleSiden(); }; };
    const kobleUnder = ()=>{
      $("#loggHer", root).onclick = ()=> openSheet(s.id, timen().t);
      const hv = $("#hvorfor", root); if(hv) hv.addEventListener("toggle", ()=> hv.querySelector("summary").setAttribute("aria-expanded", String(hv.open)));
    };
    $("#spotBack", root).onclick = H.close;
    wireFavButtons(); kobleUnder(); kobleTilbakeNa();
    $$(".dagknapp", root).forEach(kn=> kn.onclick = ()=>{
      const nd = dager.find(x=> x.key===kn.dataset.day); if(!nd || nd.key===d.key || !nd.idxs.length) return;
      const n = H.nowIdx(s);
      // i dag med lys nå: tilbake til «nå»; ellers dagens beste lyse time
      S.idx = nd.key===dayKey(new Date()) && nd.idxs.includes(n) && H.usable(s.hours[n]) ? null : SpotGraf.bestOfDay(s, nd);
      heleSiden(()=>{ const k2 = $(`.dagknapp[data-day="${nd.key}"]`, root); if(k2) k2.focus({preventScroll: true}); });
    });
    const valgt = $('.dagknapp[aria-pressed="true"]', root), dv = $(".dagvelger", root);
    if(valgt && dv) dv.scrollLeft = Math.max(0, valgt.offsetLeft - dv.offsetLeft - 16);
    Timestripe.mount(root, s, d, idx, best, H, (i)=>{
      // timevalg i samme dag: bytt bare det som hører til timen, og hold stripa i ro under fingeren
      const stripe = $("#spStripe", root), y0 = stripe.getBoundingClientRect().top;
      const hv = $("#hvorfor", root), open = hv ? hv.open : false;
      idx = i; S.idx = i;
      $("#spOver", root).innerHTML = over(); $("#spUnder", root).innerHTML = under(); $("#spTilbakeNa", root).innerHTML = tilbakeNa();
      kobleUnder(); kobleTilbakeNa();
      const hv2 = $("#hvorfor", root); if(hv2 && open) hv2.open = true;
      const dy = stripe.getBoundingClientRect().top - y0; if(dy) window.scrollBy(0, dy);
    });
  }

  /* ---------- render ---------- */
  function render(root, s, S, helpers){
    H = helpers;
    if(!H.isDesktop() && window.Timestripe && window.SpotGraf) return renderMobil(root, s, S);
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
