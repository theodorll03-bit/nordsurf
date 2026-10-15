/* Nordsurf: søk først, Utforsk og spotside (Theodor 14.10.2026, skissen i
   docs/design/spotside/skisse/ + HIG-gjennomgangen samme dag).

   Hjem: ordmerke og dato, søk, «Beste økt» de neste tre dagene, favoritter,
   alle spots per region med 7 små ruter (tallet 1-5 i ruten, 0 = tom rute
   med kant, mangler = stiplet). Utforsk er kartet (utforsk.js), spotsiden
   ligger over fanen du kom fra (spot.js). Søk finnes på ett sted: søkesiden
   (mobil) / nedtrekkslista i topplinja (nett).

   Ren visning: ingen tall regnes her - bare varselets felter (oversikt.json
   for Hjem/Utforsk, spots/<id>.json når en spot åpnes - app.js ensureSpot).
   Grunnregelen: tall som mangler vises som «–», aldri 0. */
(function(){
  const $ = (s, r)=> (r||document).querySelector(s);
  const $$ = (s, r)=> [...(r||document).querySelectorAll(s)];
  // region per område - til S5 kommer et eget felt i spots.json (bare visning)
  const REGION_OF = {"Kvaløya":"Troms", "Senja":"Troms", "Lyngen":"Troms", "Lofoten":"Lofoten", "Hustadvika":"Møre og Romsdal"};
  const regionOf = (s)=> s.region || REGION_OF[s.area] || s.area || "";
  // «område · region» - én gang når de er like (Unstad: Lofoten)
  const stedText = (s)=>{ const r = regionOf(s); return s.area && s.area!==r ? `${s.area} · ${r}` : (s.area || r); };
  const REGION_ORDER = ["Troms", "Lofoten", "Møre og Romsdal"];
  const SNARVEIER = ["Unstad", "Senja", "Lyngen", "Kvaløya"];
  const S = { view:"hjem", from:"hjem", spotId:null, idx:null, q:"", utforskDay:null, utforskView:"nord", picked:null, now:-1, visAlle:{} };
  window.__S = S;
  let started = false;

  /* ---------- hjelpere ---------- */
  const stars = (h)=> h ? (h.stars||0) : 0;
  const known = (h)=> !!h && !(!h.stars && !h.low_reason && h.surf_height==null);
  const lightOf = (h)=> h ? (h.light || (h.daylight===false ? "mørkt" : h.daylight===true ? "dag" : null)) : null;
  // «timer med lys»: dag eller skumring - ukjent lys teller aldri (grunnregelen)
  const usable = (h)=>{ const l = lightOf(h); return l==="dag" || l==="skumring"; };
  const hourAt = (s, i)=> (s && s.hours[i]) || null;
  const nowIdx = (s)=> Math.max(0, Math.min(s.hours.length-1, currentHour(s)));
  const fmtDato = new Intl.DateTimeFormat("nb-NO", {weekday:"long", day:"numeric", month:"long", timeZone:TZ});
  const fmtDagDato = new Intl.DateTimeFormat("nb-NO", {weekday:"short", day:"numeric", timeZone:TZ});
  const DK = new Map();
  const dkOf = (t)=>{ let k = DK.get(t); if(k===undefined){ k = dayKey(new Date(t)); DK.set(t, k); } return k; };
  const isDesktop = ()=> matchMedia("(min-width: 900px)").matches;
  const norm = (s)=> String(s||"").toLowerCase().replace(/æ/g,"ae").replace(/ø/g,"o").replace(/å/g,"a").normalize("NFD").replace(/[̀-ͯ]/g,"");
  const spotById = (id)=> DATA.spots.find(x=>x.id===id);
  const numHtml = (t)=> esc(t).replace(/\d[\d,.–]*/g, m=>`<span class="num">${m}</span>`);
  function heightText(h){
    // «1,6–2,1 m» (høyden som vises–surf_height_sets); tallet mangler → «–». Høyden følger
    // Theodors regel (c) 05.10.2026 (app.js heightMForDisplay via Spot.visHoyde): «Blåst ut»
    // viser surfehøyden hvis reell, ellers BarentsWatch sin totalhøyde; «Stormsjø» alltid totalhøyden.
    const v = window.Spot ? Spot.visHoyde(h) : (h && h.surf_height!=null ? {a: h.surf_height, b: h.surf_height_sets} : null);
    if(!v) return null;
    const a = nf1.format(v.a), b = v.b!=null ? nf1.format(v.b) : null;
    return b!=null && b!==a ? `${a}–${b}` : a;
  }
  function ordOgHoyde(h){
    // «ord · høyde» nå: ordet alltid (ratingWord), høyden når det er noe å vise
    if(!h) return {ord:"–", hoyde:null};
    const ord = ratingWord(h);
    const v = window.Spot ? Spot.visHoyde(h) : null;
    const show = v!=null && (stars(h) >= 1 || v.a >= 0.3);
    return {ord, hoyde: show ? heightText(h) : null};
  }
  function windText(h){
    if(!h || h.wind_speed==null) return null;
    return `${nf0.format(h.wind_speed)} m/s${h.wind_type ? " " + windLabel(h) : ""}`;
  }
  function weekDays(){
    // 7 kalenderdager fra i dag, norsk tid (kl. 11 UTC er samme dato i Oslo hele året)
    const [y, m, d] = dayKey(new Date()).split("-").map(Number);
    return Array.from({length:7}, (_, k)=>{ const at = new Date(Date.UTC(y, m-1, d+k, 11)); return {key: dayKey(at), kort: fmtDayShort.format(at).replace(/\.$/, "").slice(0, 2).toLowerCase(), dato: at.getUTCDate(), lang: fmtDay.format(at)}; });
  }
  function dayBest(s, key){
    // beste stjerner i lyse timer den dagen (i dag: fra nå). «miss»: tallet eller lyset
    // mangler, «dark»: kjent mørke resten av dagen. Aldri 0 for noe som mangler.
    let any = false, light = false, unk = false, miss = false, best = -1, bestH = null, bestIdx = -1;
    for(let i = nowIdx(s); i < s.hours.length; i++){
      const h = s.hours[i], k = dkOf(h.t);
      if(k > key) break;
      if(k !== key) continue;
      any = true;
      const l = lightOf(h);
      if(l==null){ unk = true; if(!known(h) || stars(h) >= 1) miss = true; continue; }
      if(l!=="dag" && l!=="skumring") continue;
      light = true;
      if(!known(h)){ miss = true; continue; }
      const st = stars(h);
      if(st > best || (st===best && (h.surf_height||0) > (bestH && bestH.surf_height||0))){ best = st; bestH = h; bestIdx = i; }
    }
    if(!any) return {cls:"miss", st:null, h:null, idx:-1};
    if(best >= 1) return {cls:`r-${Math.min(5, best)}`, st:best, h:bestH, idx:bestIdx};
    if(miss || (!light && unk)) return {cls:"miss", st:null, h:null, idx:-1};
    if(!light) return {cls:"dark", st:null, h:null, idx:-1};
    return {cls:"r-0", st:0, h:bestH, idx:bestIdx};
  }
  function ukeHtml(s, days, withLetters){
    const cells = days.map(d=>{ const b = dayBest(s, d.key); const n = b.st!=null && b.st>=1 ? b.st : ""; const title = b.cls==="miss" ? `${d.lang}: mangler data` : b.cls==="dark" ? `${d.lang}: mørkt` : `${d.lang}: ${b.st} ${b.st===1?"stjerne":"stjerner"}`; return `<i class="${b.cls}" title="${esc(title)}">${n}</i>`; }).join("");
    const letters = withLetters ? days.map((d, k)=>`<b class="${k===0?"idag":""}">${esc(d.kort)}</b>`).join("") : "";
    return `<span class="uke" aria-hidden="true">${letters}${cells}</span>`;
  }
  function ukeAria(s, days){
    return days.map(d=>{ const b = dayBest(s, d.key); return b.cls==="miss" ? `${cap(d.lang)} mangler data` : b.cls==="dark" ? `${cap(d.lang)} mørkt` : `${cap(d.lang)} ${b.st} ${b.st===1?"stjerne":"stjerner"}`; }).join(", ");
  }
  function bestNow(s){ const h = hourAt(s, nowIdx(s)); return {st: stars(h), hh: h ? (h.surf_height||0) : 0}; }

  /* ---------- «Beste økt» de neste tre dagene (Theodor 14.10.2026, 2c) ---------- */
  function bestSession(spots){
    // blant timer med lys de neste 72 timene: flest stjerner, ved likt høyest surf_height
    let best = null;
    for(const s of spots){
      const n = nowIdx(s), t0 = new Date(s.hours[n].t).getTime();
      for(let i=n; i<s.hours.length; i++){
        const h = s.hours[i]; if(new Date(h.t).getTime() - t0 > 72*36e5) break;
        if(!usable(h) || !known(h) || stars(h) < 1) continue;
        const c = {s, i, st: stars(h), hh: h.surf_height||0};
        if(!best || c.st > best.st || (c.st===best.st && c.hh > best.hh)) best = c;
      }
    }
    if(!best) return null;
    // tidsvindu: sammenhengende timer samme dag med samme antall stjerner
    const s = best.s, key = dkOf(s.hours[best.i].t); let a = best.i, b = best.i;
    while(a-1 >= nowIdx(s) && dkOf(s.hours[a-1].t)===key && usable(s.hours[a-1]) && stars(s.hours[a-1])===best.st) a--;
    while(b+1 < s.hours.length && dkOf(s.hours[b+1].t)===key && usable(s.hours[b+1]) && stars(s.hours[b+1])===best.st) b++;
    return {...best, a, b};
  }
  function nextPossibility(spots){
    // første lyse time med minst 1 stjerne, uansett hvor langt frem oversikten rekker
    let first = null;
    for(const s of spots) for(let i=nowIdx(s); i<s.hours.length; i++){
      const h = s.hours[i]; if(!usable(h) || !known(h) || stars(h) < 1) continue;
      const t = new Date(h.t).getTime(); if(!first || t < first.t) first = {s, i, t}; break;
    }
    return first;
  }
  function spanText(s, a, b){
    const ta = new Date(s.hours[a].t), tb = new Date(s.hours[b].t);
    const end = (+fmtHour.format(tb) + 1) % 24;
    return `${cap(relDay(ta))} kl. ${fmtHour.format(ta)}–${String(end).padStart(2, "0")}`;
  }
  function bestHtml(){
    const best = bestSession(DATA.spots);
    if(!best){
      const n = nextPossibility(DATA.spots);
      return `<div class="kort best ingen r-0" id="bestKort"><div class="navn">Ingen gode økter de neste tre dagene</div>${n ? `<div class="fakta">Neste mulighet: ${esc(cap(relDay(new Date(n.t))))} · <b>${esc(n.s.name)}</b></div>` : ""}</div>`;
    }
    const s = best.s, h = s.hours[best.i], st = best.st;
    const fakta = [h.period!=null ? `${nf0.format(h.period)} s` : null, kjText(h), windText(h)].filter(Boolean).join(" · ");
    const hoyde = heightText(h);
    return `<a class="kort best tap r-${Math.min(5,st)}" id="bestKort" href="#spot=${esc(s.id)}&t=${best.a}" aria-label="${esc(`Beste økt: ${s.name}, ${spanText(s, best.a, best.b)}, ${STR.starsAria(st, 0)}, ${ratingWord(h)}${hoyde ? ", " + hoyde + " m" : ""}. Åpne spoten`)}">
      <div class="rad"><div><div class="navn">${esc(s.name)}</div><div class="omr">${esc(stedText(s))}</div></div><span class="tid">${esc(spanText(s, best.a, best.b))}</span></div>
      <div class="vurd"><div>${starsSVG(st, 0)}<div class="ord">${esc(ratingWord(h))}</div></div>${hoyde ? `<div class="hoyde">${esc(hoyde)}<small>m</small></div>` : ""}</div>
      ${fakta ? `<div class="fakta">${numHtml(fakta)}</div>` : ""}</a>`;
  }

  /* ---------- Hjem ---------- */
  function favHtml(days){
    const favs = DATA.spots.filter(s=>isFavSpot(s.id));
    if(!favs.length) return "";
    return `<section class="sek"><h2 class="h2">Favoritter</h2></section><div class="favrad">${favs.map(s=>{
      const h = hourAt(s, nowIdx(s)), st = stars(h), oh = ordOgHoyde(h), vind = windText(h);
      return `<a class="kort tap favkort r-${Math.min(5,st)}" href="#spot=${esc(s.id)}" aria-label="${esc(`${s.name}: ${oh.ord}${oh.hoyde ? ", " + oh.hoyde + " m" : ""}${vind ? ", " + vind : ""}. ${ukeAria(s, days)}. Åpne spoten`)}">
        <div class="navn">${esc(s.name)}</div><div class="omr">${esc(s.area||"")} · nå</div>
        <div class="vurd"><div>${st ? starsSVG(st, 0) : ""}<div class="ord">${esc(oh.ord)}</div></div>${oh.hoyde ? `<div class="hoyde">${esc(oh.hoyde)}<small>m</small></div>` : ""}</div>
        ${vind ? `<div class="vind">${numHtml(vind)}</div>` : ""}
        <div class="uke">${ukeHtml(s, days, false)}</div></a>`; }).join("")}</div>`;
  }
  function groups(){
    const by = new Map();
    for(const s of DATA.spots){ const r = regionOf(s); if(!by.has(r)) by.set(r, []); by.get(r).push(s); }
    const order = [...by.keys()].sort((a, b)=> (REGION_ORDER.indexOf(a)+1 || 99) - (REGION_ORDER.indexOf(b)+1 || 99) || a.localeCompare(b, "nb"));
    return order.map(r=>({region: r, spots: by.get(r)}));
  }
  const byRatingNow = (a, b)=>{ const x = bestNow(a), y = bestNow(b); return y.st - x.st || y.hh - x.hh || a.name.localeCompare(b.name, "nb"); };
  function radHtml(s, days){
    const h = hourAt(s, nowIdx(s)), st = stars(h), oh = ordOgHoyde(h);
    return `<a class="rad r-${Math.min(5,st)}" href="#spot=${esc(s.id)}" aria-label="${esc(`Åpne ${s.name}: ${oh.ord}${oh.hoyde ? ", " + oh.hoyde + " m" : ""}. ${ukeAria(s, days)}`)}">
      <span class="nm"><b>${esc(s.name)}</b><small>${esc(s.area||"")}</small><span class="na">${esc(oh.ord)}${oh.hoyde ? `<span class="num">${esc(oh.hoyde)} m</span>` : ""}</span></span>
      ${ukeHtml(s, days, false)}</a>`;
  }
  function groupsHtml(days){
    return groups().map(g=>{
      const n = g.spots.length, all = S.visAlle[g.region] || n <= 8;
      const sorted = [...g.spots].sort(byRatingNow);
      const shown = all ? sorted : sorted.slice(0, 5);
      const id = "reg-" + norm(g.region).replace(/[^a-z0-9]+/g, "-");
      return `<section class="gruppe" id="${id}"><div class="gruppe-topp"><h3>${esc(g.region)}<small>${n} ${n===1?"spot":"spots"}</small></h3>${ukeHtml({hours:[]}, [], false).replace('<span class="uke" aria-hidden="true"></span>', "")}<span class="uke" aria-hidden="true">${days.map((d, k)=>`<b class="${k===0?"idag":""}">${esc(d.kort)}</b>`).join("")}</span></div>
        <div class="rader">${shown.map(s=>radHtml(s, days)).join("")}</div>
        ${!all ? `<button type="button" class="ghost visalle" data-region="${esc(g.region)}">Vis alle ${n}</button>` : ""}</section>`;
    }).join("");
  }
  function tabellHtml(days){
    // nett: Spot | Nå | 7 dager - hver dagcelle: dagens høyeste surf i dagslys, farget etter vurdering, med stjernetall
    const head = `<thead><tr><th>Spot</th><th>Nå</th>${days.map((d, k)=>`<th class="dag">${k===0 ? "I dag" : esc(cap(d.kort))}<small>${d.dato}.</small></th>`).join("")}</tr></thead>`;
    const body = groups().map(g=>`<tr class="g"><td colspan="${2+days.length}">${esc(g.region)} <small>· ${g.spots.length} ${g.spots.length===1?"spot":"spots"}</small></td></tr>` +
      [...g.spots].sort(byRatingNow).map(s=>{
        const h = hourAt(s, nowIdx(s)), st = stars(h), oh = ordOgHoyde(h);
        const cells = days.map(d=>{ const b = dayBest(s, d.key);
          if(b.cls==="miss") return `<td class="c"><span class="celle miss" title="${esc(d.lang)}: mangler data">–</span></td>`;
          if(b.cls==="dark") return `<td class="c"><span class="celle miss" title="${esc(d.lang)}: mørkt">–</span></td>`;
          const hh = b.h && b.h.surf_height!=null ? nf1.format(b.h.surf_height) : "–";
          return `<td class="c"><span class="celle r-${Math.min(5,b.st)}" title="${esc(`${d.lang}: ${b.st} ${b.st===1?"stjerne":"stjerner"}, ${hh} m`)}">${esc(hh)}${b.st>=1 ? `<small>★${b.st}</small>` : ""}</span></td>`; }).join("");
        return `<tr class="s r-${Math.min(5,st)}" data-spot="${esc(s.id)}" tabindex="0" aria-label="${esc(`Åpne ${s.name}: ${oh.ord}${oh.hoyde ? ", " + oh.hoyde + " m" : ""}. ${ukeAria(s, days)}`)}"><td class="nm"><b>${esc(s.name)}</b><small>${esc(stedText(s))}</small></td><td class="na">${esc(oh.ord)}${oh.hoyde ? `<span class="num">${esc(oh.hoyde)} m</span>` : ""}</td>${cells}</tr>`;
      }).join("")).join("");
    return `<div class="tabellboks"><table class="spots">${head}<tbody>${body}</tbody></table></div>`;
  }
  function renderHome(){
    const root = $("#viewHjem"); const days = weekDays(); const gen = new Date(DATA.generated); const pc = isDesktop();
    const dato = `${cap(fmtDato.format(new Date()))} · oppdatert ${fmtTime.format(gen)}`;
    const regions = groups();
    root.innerHTML = `
      <div class="hjem-topp"><div>${pc ? `<h1 class="h1">Hvor skal du surfe?</h1>` : `<a class="wm" href="#hjem" aria-label="Nordsurf">${wordmarkSvg()}</a>`}<p class="dato">${esc(dato)}</p></div>
        ${pc ? `<div class="chips" aria-label="Områder"><span class="muted" style="align-self:center;font-size:var(--fs-caption)">Områder</span>${regions.map(g=>`<a class="chip" href="#reg-${norm(g.region).replace(/[^a-z0-9]+/g, "-")}">${esc(g.region)}</a>`).join("")}</div>` : `<a class="iconbtn" href="#innstillinger" aria-label="Innstillinger"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7zm8.6 4.8-1.9-.3a7 7 0 0 1-.6 1.5l1.1 1.6-1.7 1.7-1.6-1.1a7 7 0 0 1-1.5.6l-.3 1.9h-2.4l-.3-1.9a7 7 0 0 1-1.5-.6l-1.6 1.1-1.7-1.7 1.1-1.6a7 7 0 0 1-.6-1.5l-1.9-.3v-2.4l1.9-.3a7 7 0 0 1 .6-1.5L5.6 7.3l1.7-1.7 1.6 1.1a7 7 0 0 1 1.5-.6l.3-1.9h2.4l.3 1.9a7 7 0 0 1 1.5.6l1.6-1.1 1.7 1.7-1.1 1.6a7 7 0 0 1 .6 1.5l1.9.3z"/></svg></a>`}</div>
      <a class="sokfelt" href="#sok" role="button"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12.8 12.8 17 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>Søk etter spot eller område</a>
      <div class="${pc ? "hjem-grid" : ""}">
        <div><section class="sek"><h2 class="h2">Beste økt</h2><p class="sub">De neste tre dagene, i dagslys</p></section>${bestHtml()}</div>
        ${pc ? `<div><section class="sek"><h2 class="h2">Utforsk</h2><p class="sub">${DATA.spots.length} spots, farget etter vurdering nå</p></section><a class="kort tap utforskkort" href="#utforsk" aria-label="Utforsk kartet">${window.Utforsk && Utforsk.thumb ? Utforsk.thumb() : ""}<span class="primary knapp" aria-hidden="true">Åpne kartet</span></a></div>` : ""}
      </div>
      ${favHtml(days)}
      <section class="sek"><h2 class="h2">Alle spots</h2>${pc ? `<p class="sub">Høyeste surf i dagslys per dag, med beste antall stjerner</p>` : ""}</section>
      ${pc ? tabellHtml(days) : groupsHtml(days)}
      <p class="kilder">Varsel fra BarentsWatch, MET Norge, Open-Meteo og Kartverket.</p>`;
    $$(".visalle", root).forEach(b=> b.onclick = ()=>{ S.visAlle[b.dataset.region] = true; renderHome(); });
    $$("table.spots tr.s", root).forEach(tr=>{ tr.onclick = ()=> openSpot(tr.dataset.spot); tr.onkeydown = (e)=>{ if(e.key==="Enter" || e.key===" "){ e.preventDefault(); openSpot(tr.dataset.spot); } }; });
  }

  /* ---------- Søk (ett sted: søkesiden på mobil, nedtrekkslista på nett) ---------- */
  function search(q){
    const nq = norm(q.trim()); if(!nq) return [];
    const hits = DATA.spots.filter(s=> norm(s.name).includes(nq) || norm(s.area).includes(nq) || norm(regionOf(s)).includes(nq));
    return hits.sort((a, b)=>{ const pa = norm(a.name).startsWith(nq) ? 0 : 1, pb = norm(b.name).startsWith(nq) ? 0 : 1; return pa - pb || byRatingNow(a, b); });
  }
  function sradHtml(s){
    const h = hourAt(s, nowIdx(s)), st = stars(h), oh = ordOgHoyde(h);
    return `<a class="srad r-${Math.min(5,st)}" href="#spot=${esc(s.id)}" role="option"><span class="prikk" aria-hidden="true"></span><span class="nm"><b>${esc(s.name)}</b><small>${esc(stedText(s))}</small></span><span class="na">${esc(oh.ord)}${oh.hoyde ? `<span class="num">${esc(oh.hoyde)} m</span>` : ""}</span></a>`;
  }
  function resultsHtml(q){
    const r = search(q);
    if(!q.trim()) return forslagHtml();
    if(!r.length) return `<p class="ingen-treff" role="status">Ingen spots heter «${esc(q.trim())}». Prøv et område, som Senja eller Lofoten.</p>`;
    return `<div class="alfa" role="listbox">${r.map(sradHtml).join("")}</div>`;
  }
  function forslagHtml(){
    const favs = DATA.spots.filter(s=>isFavSpot(s.id));
    const areas = [...new Set(DATA.spots.map(s=>s.area).filter(Boolean))];
    const regs = [...new Set(DATA.spots.map(regionOf))];
    const alpha = [...DATA.spots].sort((a, b)=>a.name.localeCompare(b.name, "nb"));
    return `<div class="forslag">
      ${favs.length ? `<h3>Favoritter</h3><div class="chips">${favs.map(s=>`<a class="chip" href="#spot=${esc(s.id)}">${esc(s.name)}</a>`).join("")}</div>` : ""}
      <h3>Områder</h3><div class="chips">${[...regs, ...areas.filter(a=>!regs.includes(a))].map(a=>`<button type="button" class="chip" data-q="${esc(a)}">${esc(a)}</button>`).join("")}</div>
      <h3>Alle spots</h3><div class="alfa" role="listbox">${alpha.map(sradHtml).join("")}</div></div>`;
  }
  function renderSok(){
    const root = $("#viewSok");
    root.innerHTML = `<div class="soktopp"><label class="sok-field" for="sokM"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12.8 12.8 17 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><span class="sr">Søk etter spot eller område</span><input id="sokM" type="search" placeholder="Søk etter spot eller område" autocomplete="off" value="${esc(S.q)}"></label><button type="button" class="avbryt" id="sokAvbryt">Avbryt</button></div><div id="sokRes">${resultsHtml(S.q)}</div>`;
    const inp = $("#sokM", root);
    inp.oninput = ()=>{ S.q = inp.value; $("#sokRes", root).innerHTML = resultsHtml(S.q); wireSokChips(root); };
    $("#sokAvbryt", root).onclick = ()=>{ S.q = ""; go(S.from==="sok" ? "hjem" : S.from); };
    wireSokChips(root);
    setTimeout(()=>{ try{ inp.focus(); }catch(e){} }, 50);
  }
  function wireSokChips(root){
    $$(".chip[data-q]", root).forEach(b=> b.onclick = ()=>{ S.q = b.dataset.q; const inp = $("#sokM", root) || $("#sokPC"); if(inp) inp.value = S.q; if(root.id==="viewSok"){ $("#sokRes", root).innerHTML = resultsHtml(S.q); wireSokChips(root); } else renderDrop(); });
  }
  function renderDrop(){
    const drop = $("#sokDrop"), inp = $("#sokPC"); if(!drop) return;
    const open = document.activeElement===inp || S.q.trim().length > 0;
    drop.hidden = !open; inp.setAttribute("aria-expanded", String(open));
    if(open){ drop.innerHTML = resultsHtml(S.q); wireSokChips(drop); }
  }
  function wireTopSearch(){
    const inp = $("#sokPC"); if(!inp) return;
    inp.oninput = ()=>{ S.q = inp.value; renderDrop(); };
    inp.onfocus = ()=> renderDrop();
    inp.onkeydown = (e)=>{ if(e.key==="Escape"){ inp.blur(); $("#sokDrop").hidden = true; inp.setAttribute("aria-expanded", "false"); } };
    document.addEventListener("pointerdown", (e)=>{ if(!e.target.closest(".topsok")){ $("#sokDrop").hidden = true; inp.setAttribute("aria-expanded", "false"); } }, true);
    $("#sokDrop").addEventListener("click", (e)=>{ if(e.target.closest("a")){ $("#sokDrop").hidden = true; inp.value = ""; S.q = ""; } });
  }

  /* ---------- ruter og visninger ---------- */
  function parseRoute(){
    const h = location.hash || "";
    let m;
    if((m = h.match(/^#spot=([^&]+)(?:&t=(\d+))?/)) || (m = h.match(/^#\/spot\/([^/?#&]+)/))){
      const id = decodeURIComponent(m[1]); if(spotById(id)){ S.spotId = id; S.idx = m[2]!=null ? +m[2] : null; S.view = "spot"; return; }
    }
    if(/^#(utforsk|\/utforsk)/.test(h)) S.view = "utforsk";
    else if(/^#(logger|\/logger)/.test(h)) S.view = "logger";
    else if(/^#(innstillinger|\/innstillinger)/.test(h)) S.view = "innstillinger";
    else if(/^#sok/.test(h)) S.view = "sok";
    else S.view = "hjem";   // «#/», «#/liste», «#hjem» og tomt
    if(S.view!=="spot") S.spotId = null;
  }
  function routeFor(view){ return view==="spot" ? `#spot=${encodeURIComponent(S.spotId)}` : `#${view}`; }
  function go(view, replace){
    const hash = routeFor(view);
    if(location.hash !== hash){ if(replace) history.replaceState(null, "", hash); else location.hash = hash; }
    else render();
  }
  function openSpot(id, idx, opts){
    const s = spotById(id); if(!s) return;
    if(S.view!=="spot") S.from = S.view==="sok" ? (S.from||"hjem") : S.view;
    S.spotId = id; S.idx = idx!=null ? idx : null;
    S.view = "spot";
    const hash = `#spot=${encodeURIComponent(id)}${idx!=null ? "&t=" + idx : ""}`;
    if(location.hash !== hash) location.hash = hash; else render();
  }
  function closeSpot(){ go(S.from && S.from!=="spot" ? S.from : "hjem"); }
  function show(view){
    const map = {hjem:"viewHjem", sok:"viewSok", utforsk:"viewUtforsk", logger:"viewSide", innstillinger:"viewSide", spot:"viewSpot"};
    $$("#main .view").forEach(v=>{ v.hidden = v.id !== map[view]; });
    const navView = view==="spot" ? S.from : view==="innstillinger" || view==="sok" ? "hjem" : view;
    $$("[data-nav]").forEach(a=>{ if(a.dataset.nav===navView) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    document.body.dataset.view = view;
    window.scrollTo(0, 0);
  }
  function renderSide(){
    const bar = $("#pageBar");
    if(S.view==="logger"){
      bar.innerHTML = "";
      renderLogs();
      if(!loadLogs().length){
        // tom tilstand (HIG 11)
        $("#detailPane").insertAdjacentHTML("afterbegin", `<header class="top"><h1>Logger</h1></header><div class="kort tom"><h3>Ingen økter logget ennå</h3><p>Når du logger hvordan det faktisk var, lærer varselet spotene dine bedre.</p><button type="button" class="primary" id="loggForste">Logg en økt</button></div>`);
        const first = $("#detailPane header.top + .kort.tom + header.top"); if(first) first.remove();
        $("#loggForste").onclick = ()=> openSheet();
      }
    } else {
      bar.innerHTML = `<button type="button" class="back" id="sideBack"><svg viewBox="0 0 18 18" aria-hidden="true"><path d="M11 3 5 9l6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>Hjem</button>`;
      $("#sideBack").onclick = ()=> go("hjem");
      renderSettings();
    }
  }
  function renderSpotView(){
    const root = $("#viewSpot"), s = spotById(S.spotId);
    if(!s){ go("hjem", true); return; }
    if(!spotIsFull(s)){
      root.innerHTML = `<div class="spot-topp"><button type="button" class="back" id="spotBack" aria-label="Tilbake"><svg viewBox="0 0 18 18" aria-hidden="true"><path d="M11 3 5 9l6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button><div class="tittel"><h1>${esc(s.name)}</h1><div class="omr">${esc(stedText(s))}</div></div></div>
        <p class="muted" role="status" id="spotLaster">${s._loadErr ? `Fikk ikke hentet detaljene for ${esc(s.name)}. Sjekk at du er på nett, og prøv igjen.` : "Henter detaljene …"}</p>${s._loadErr ? `<button type="button" class="ghost" id="spotRetry">Prøv igjen</button>` : ""}`;
      $("#spotBack").onclick = closeSpot;
      const rb = $("#spotRetry"); if(rb) rb.onclick = ()=>{ s._loadErr = false; renderSpotView(); };
      if(!s._loadErr) ensureSpot(s.id).then(()=>{ if(S.view==="spot" && S.spotId===s.id) renderSpotView(); }).catch((e)=>{ console.error(e); s._loadErr = true; if(S.view==="spot" && S.spotId===s.id) renderSpotView(); });
      return;
    }
    Spot.render(root, s, S, {regionOf, stedText, close: closeSpot, nowIdx, usable, known, stars, dkOf, heightText, isDesktop});
  }
  function render(){
    if(!DATA) return;
    show(S.view);
    document.title = S.view==="spot" && spotById(S.spotId) ? `${spotById(S.spotId).name} – Nordsurf` : "Nordsurf";
    if(S.view==="hjem") renderHome();
    else if(S.view==="sok") renderSok();
    else if(S.view==="utforsk") Utforsk.render(S);
    else if(S.view==="logger" || S.view==="innstillinger") renderSide();
    else if(S.view==="spot") renderSpotView();
  }
  function tickNow(){
    // ny time mens appen står åpen / kommer tilbake fra bakgrunnen: tegn på nytt (nå-timen flytter seg)
    if(document.hidden || !DATA) return;
    const n = nowIdx(DATA.spots[0]); if(n===S.now) return; S.now = n;
    if(S.view==="sok") return;
    render();
  }

  /* ---------- oppstart (kalles fra app.js start()) ---------- */
  async function start(data){
    S.now = nowIdx(data.spots[0]);
    $("#loading").hidden = true;
    wireTopSearch();
    const retry = $("#feilRetry"); if(retry) retry.onclick = ()=> location.reload();
    window.addEventListener("hashchange", ()=>{ parseRoute(); render(); });
    window.addEventListener("resize", ()=>{ if(S.view==="hjem" || S.view==="utforsk") render(); });
    document.addEventListener("visibilitychange", tickNow);
    setInterval(tickNow, 60e3);
    parseRoute();
    render();
    started = true;
  }
  function refresh(){ if(DATA && started && S.view!=="sok") render(); }
  function goLegacy(mode){ const map = {home:"hjem", list:"hjem", peek:"hjem", half:"hjem", map:"utforsk", logger:"logger", innstillinger:"innstillinger"}; go(map[mode] || "hjem"); }
  window.Front = { start, refresh, openSpot, go: goLegacy, state: S, closeSpot, helpers: {regionOf, stedText, nowIdx, usable, known, stars, dayBest, heightText, ordOgHoyde, windText, weekDays, search, norm, bestSession, byRatingNow, dkOf, isDesktop} };
  window.start();
})();
