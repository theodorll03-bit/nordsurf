/* Nordsurf: spotsiden (Theodor 14.10.2026, punkt 4 + HIG 9; design B 4.0 fra 16.11.2026).

   Mobil (SPEC §6B): renderMobil() - kornfoto, dom, time, timestripe og retningsskive.
   Nettsiden fra 1024 px (SPEC §6C, B4 steg 6): renderWeb() - samme deler i et 12-kolonners rutenett, med
   «Neste 7 dager», timestripa som tabell, minikartet («Spotten») og «Om spotten».

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
  function sikkerhet(h){
    if(!h) return "–";
    const c = h.confidence;
    // 24.11.2026 (feiljegeren, funn 4): høyden er svell ute × andelen gjennom gapet (andelsHoyde() i app.js), ikke
    // kystmodellens tall. Da står «Usikkert varsel» (når rating.py har merket timen usikker) og «havmodell».
    const andel = andelsHoyde(h);
    const ord = andel && h.uncertain ? STR.notice.uncertain : c==null ? null : c >= 80 ? "Høy sikkerhet" : c >= 55 ? "Middels sikkerhet" : "Lav sikkerhet";
    const sone = andel && h.zone!=="langtid" ? "havmodell" : h.zone==="barentswatch" ? "kystmodell 100 m" : h.zone==="reserve" ? "havmodell" : h.zone==="langtid" ? "langtidsmodell" : null;
    return [ord, sone].filter(Boolean).join(" · ") || "–";
  }

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

  /* ---------- minikartet (PC: «Spotten», SPEC §6C punkt 6) ---------- */
  function minikartHtml(s, h){
    const kyst = kystCache[s.id] && kystCache[s.id].land ? kystCache[s.id] : null;
    const vt = vinduTekst(h, s);
    const svg = Minikart.markup(s, h, kyst, {still: matchMedia("(prefers-reduced-motion: reduce)").matches, hit: vt ? vt.ikon=="ja" : null, vinduTekst: vt ? vt.txt : null});
    return `<figure class="spw-fig" id="miniKort">${svg}${!kyst ? `<p class="kredit">${s.id in kystCache ? "Kystlinje mangler for denne spoten" : "Henter kystlinjen …"}</p>` : ""}
      <figcaption class="kredit">${esc(STR.web.fig(1, s.name))} ${esc(STR.web.kartOsm)}.</figcaption></figure>`;
  }
  function hvorforHtml(h){
    if(!h || !h.breakdown) return "";
    const ex = ratingWordExplain(h);
    return `<details class="hvorfor" id="hvorfor"><summary aria-expanded="false">Hvorfor denne vurderingen?<svg class="chev" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="m3 6 5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></summary>
      <div class="body">${ex ? `<p class="bd-note"><b>${esc(ratingWord(h))}</b>: ${esc(ex)}</p>` : ""}${breakdownTabellHtml(h.breakdown)}</div></details>`;
  }

  /* ---------- mobil (design B 4.0, SPEC §6B) ---------- */
  // Rekkefølge: kornfoto med tilbake- og favorittknapp, navn, metalinje, dagvelgeren (står fast øverst når siden rulles,
  // designrevisjonen fase 2 punkt 4), dagens dom, faktalinje, valgt time (svell stort, så surf, vind og tidevann),
  // time for time, retningsskiva, «Hvorfor», logg og kilder.
  // Ren visning som resten av fila. Nettsiden (renderWeb, lenger ned) bruker de samme delene.
  const midtPaa = (key)=> new Date(key + "T11:00:00Z");
  // Krediteringen under bildet: kortformen på én linje, med lisensnavnet som lenke (fotoKreditHtml i app.js).
  // Hele henvisningen står under Kilder nederst (mobil: siste avsnitt, nettsiden: bunnen).
  const kreditHtml = ()=> fotoKreditHtml(false);
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
      // samme regel som publish.best_hour() og bestOfDay: ved likt tall og lik høyde går en time der vinden får skylda først (S26)
      if(!best || betterDayHour(h, s.hours[best.i])) best = {i, st: H.stars(h)};
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
    // timene i dagens beste vindu (streken over kolonnene i timestripa); ingen når dagen ikke har surf,
    // og ingen når vinduet er over - samme regel som «Best» i dommen (domHtml)
    if(b.st==null || b.st < 1 || !b.start || !H.fsApent(b)) return new Set();
    const a = Date.parse(b.start), z = Date.parse(b.slutt || b.start);
    return new Set(d.idxs.filter(i=>{ const ms = Date.parse(s.hours[i].t); return ms >= a && ms <= z; }));
  }
  const domOrd = (b)=> b.cls==="forbud" ? STR.hjem.forbud : b.cls==="dark" ? STR.hjem.morktOrd : b.cls==="over" ? STR.hjem.over : b.cls==="miss" ? STR.hjem.mangler : ratingWord(b.h);
  function domHtml(s, d, b){
    const n = b.st!=null ? Math.min(5, b.st) : null;
    // beste vindu som klokkeslett; dager med seks timer mellom varslene har bare tidspunktet
    // et vindu som er over, er ikke et råd (fysikk-kontrolløren 19.11.2026) - samme regel som favorittradene og forsiden
    const vindu = n!=null && n >= 1 && H.fsApent(b) ? (d.step===1 ? H.vinduKl(b.start, b.slutt).join("–") : fmtHour.format(new Date(b.h.t))) : null;
    const setn = H.favSetning(s, b, true);
    return `<div class="dom r-${n!=null ? n : 0}">
        <div class="dom-v">${n!=null ? `<span class="t-tall" role="img" aria-label="${esc(starsAriaLost(n, b.h))}">${n}</span>` : ""}<span class="dom-ord"><b>${esc(domOrd(b))}</b><span class="etikett">${esc(relDay(midtPaa(d.key)))}</span></span></div>
        ${vindu ? `<div class="dom-h"><span class="etikett">${esc(STR.spot.best)}</span><span class="t-vindu">${esc(vindu)}</span></div>` : ""}
      </div>${setn ? `<p class="dom-setn">${esc(setn)}</p>` : ""}`;
  }
  function faktaHtml(s, h, t){
    const f = faktaDeler(s, h, t);
    return f.length ? `<p class="fakta-linje">${f.map(x=> `<span>${esc(x)}</span>`).join("")}</p>` : "";
  }
  function faktaDeler(s, h, t){
    // bare det vi har data for (SPEC §6B punkt 5)
    const f = [], ld = (s.light_days || {})[dayKey(t)];
    if(ld) f.push(ld.start ? `${STR.spot.lys} ${fmtTime.format(new Date(ld.start))}–${fmtTime.format(new Date(ld.end))}` : STR.lightNone);
    if(h && h.air_temp!=null) f.push(`${STR.spot.luft} ${nf0.format(h.air_temp)}°`);
    if(h && h.water_temp!=null) f.push(`${STR.spot.vann} ${nf0.format(h.water_temp)}°`);
    if(DATA.generated){ const g = new Date(DATA.generated); f.push(`${STR.spot.oppdatert} ${dayKey(g)===dayKey(new Date()) ? "" : relDay(g) + " "}${fmtTime.format(g)}`); }
    return f;
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
    // hvert tap med sitt stiplede poeng: vind i korall, tidevann i blekk (S33 c). Eldre varsel uten delingen: bare «−1».
    const tapt = lostParts(h).map(p=> `<span class="tapt"><i${p.hva === "tidevann" ? ' class="tv"' : ""} aria-hidden="true"></i>${esc(p.tekst)}</span>`).join("");
    return `<p class="sub tdom r-${st}">${tapt}<span class="rute r-${st}" role="img" aria-label="${esc(STR.starsAria(st, 0))}">${st}</span><span class="to">${esc(ratingWord(h))}</span></p>`;
  }
  function timeHtml(s, h, t, ev){
    const hh = fmtHour.format(t);
    const maal = (ikon, k, v, enhet, sub, under)=> `<div class="maal"><span class="etikett">${ikon}${esc(k)}</span><span class="mv">${v}${enhet ? `<small>${enhet}</small>` : ""}</span><span class="mu">${sub || ""}</span>${under ? `<span class="mu-pref">${esc(under)}</span>` : ""}</div>`;
    const dir = h && h.dir_offshore!=null ? h.dir_offshore : null;
    const inne = dir!=null && visVindu(s) ? inSwellWindow(dir, s) : false;
    const sub = !h ? "" : h.period!=null && dir!=null ? STR.spot.svellSub(nf0.format(h.period), compass(dir), Math.round(dir))
      : [h.period!=null ? `${nf0.format(h.period)} s` : null, dir!=null ? `${STR.fromDir(compass(dir))} ${Math.round(dir)}°` : null].filter(Boolean).join(" · ");
    const svell = `<div class="svell"><div class="etikett">${PIL("sv" + (inne ? " inne" : ""), dir, IK_SVELL)}${esc(STR.spot.svell)}</div>
        ${h && h.swell_offshore!=null ? `<div class="t-svell">${desTall(nf1.format(h.swell_offshore))}<small>m</small></div>` : `<div class="svell-sub">${esc(cap(STR.spot.mangler))}</div>`}
        ${sub ? `<div class="svell-sub">${esc(sub)}</div>` : ""}</div>`;
    const rader = [];
    // surf: høyden som vises og settene (regel (c), visHoyde); ordet når tallet er kjent, men ikke pålitelig
    const hoyde = H.heightText(h), vh = visHoyde(h);
    if(hoyde) rader.push(maal(PIL("", null, IK_SURF), STR.spot.surf, esc(hoyde), "m", esc(kroppshoyde(h) || "")));
    else if(h && h.surf_height!=null && (!vh || vh.a <= 0)) rader.push(maal(PIL("", null, IK_SURF), STR.spot.surf, `<span class="ordv">${esc(ratingWord(h))}</span>`, "", ""));
    if(h && h.wind_speed!=null){
      const fra = h.wind_dir!=null ? `${STR.fromDir(compass(h.wind_dir))} ${Math.round(h.wind_dir)}°` : "";
      rader.push(maal(PIL("", h.wind_dir, h.wind_dir!=null ? IK_VIND : ""), STR.spot.vind, windMsText(h), "m/s",
        esc([[windLabel(h), fra].filter(Boolean).join(" "), h.gust!=null ? STR.gust(nf0.format(h.gust)) : null].filter(Boolean).join(" · "))));
    }
    const lv = window.Tidevann ? Tidevann.nivaa(ev, t.getTime()) : null;
    if(lv){
      // nivået over sjøkartnull og hvor det er på vei: mot neste flo/fjære, eller «snur» nær ekstremen
      const naer = [lv.a, lv.b].find(e=> Math.abs(e.ms - t.getTime()) <= 40 * 6e4);
      const vei = naer ? `${esc(STR.spot.snur)} ${fmtTime.format(new Date(naer.ms))}`
        : `<span aria-hidden="true">${lv.stiger ? "↑" : "↓"}</span><span class="sr">${esc(lv.stiger ? STR.spot.stiger : STR.spot.synker)}, </span> ${esc(lv.stiger ? STR.spot.hoy : STR.spot.lav)} ${fmtTime.format(new Date(lv.b.ms))}`;
      // Spotens tidevannsregel på mobil (S33 a, svar.md 23.11.2026 kl. 14.00): en kort setning på egen linje under raden
      // («Best på lav til middels vannstand», Tidevann.prefKort - bygger på Tidevann.prefTekst og s.tide_regel.prefer).
      // Spots uten regel har ingen linje. På nettsiden står setningen i «Om spotten».
      const pref = !H.isDesktop() && window.Tidevann && Tidevann.prefKort ? Tidevann.prefKort(s) : "";
      rader.push(maal(PIL("", null, IK_TIDE), STR.spot.tidevann, nf1.format(lv.cm / 100), "m", vei, pref));
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
    const foto = !!(window.Skive && Skive.harBilde(s.id));
    const timen = ()=>{ const h = idx!=null ? s.hours[idx] || null : null; return {h, t: h ? new Date(h.t) : new Date()}; };
    const over = ()=>{ const {h, t} = timen(); return faktaHtml(s, h, t) + timeHtml(s, h, t, ev); };
    const under = ()=>{
      const {h, t} = timen(), hh = fmtHour.format(t), sikk = h ? sikkerhet(h) : "–";
      return `<div class="sek-spot"><h2 class="h2">${esc(STR.spot.retning(hh))}</h2></div>${window.Skive ? Skive.html(s, h, hh) : ""}${hvorforHtml(h)}
        <div class="logg-her"><button type="button" class="primary" id="loggHer">Logg en økt her</button></div>
        <p class="kilder">${sikk!=="–" ? esc(sikk) + ". " : ""}Varsel fra ${esc(relDay(new Date(DATA.generated)))} kl. ${fmtTime.format(new Date(DATA.generated))}. Kilder: BarentsWatch (kystmodell 100 m), MET Norge, Open-Meteo og Kartverket.</p>${foto ? `<p class="kilder foto">${esc(STR.spot.bildet)}: ${fotoKreditHtml(true)}</p>` : ""}`;
    };
    const id = encodeURIComponent(s.id);
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
        ${foto ? `<p class="kredit linje">${kreditHtml()}</p>` : ""}
        ${dagvelgerHtml(s, dager, d)}
        ${domHtml(s, d, b)}
        <div id="spOver">${over()}</div>
        <div class="sek-spot"><h2 class="h2">${esc(STR.spot.timeForTime)}</h2>${morkeKol ? `<p class="sub">${esc(STR.lightOnly)}</p>` : ""}</div>
        <div id="spStripe">${Timestripe.html(s, d, idx, best, H)}</div>
        <div class="sp-tilbakena" id="spTilbakeNa">${tilbakeNa()}</div>
        <div id="spUnder">${under()}</div>
      </div>`;
    const heleSiden = (etter, visDom)=>{
      // nytt valg som bytter dag: tegn alt på nytt uten å hoppe i siden eller i dagrekka
      const y = window.scrollY, dv = $(".dagvelger", root), x = dv ? dv.scrollLeft : 0;
      renderMobil(root, s, S);
      const dv2 = $(".dagvelger", root); if(dv2) dv2.scrollLeft = x;
      window.scrollTo(0, y);
      // Dagbytte (designrevisjonen fase 2 punkt 4): dagvelgeren står fast øverst. Er dommen for den nye dagen rullet ut
      // over den, rulles siden så dommen står rett under dagvelgeren - dag, dom og time synes sammen.
      // Står timen (KL.-blokka) under fanelinja, rulles siden ned så langt det går uten at dommen går under dagvelgeren.
      const dom = visDom && dv2 ? $(".dom", root) : null, time = $("#spOver", root), fane = document.querySelector(".tabbar");
      if(dom){
        const hoyde = dv2.getBoundingClientRect().height, feste = parseFloat(getComputedStyle(dv2).top) || 0;
        const ledig = dom.getBoundingClientRect().top - (feste + hoyde + 8);   // så mye kan siden rulles før dommen når dagvelgeren
        const synlig = fane && fane.getBoundingClientRect().height ? fane.getBoundingClientRect().top : window.innerHeight;
        const under = time ? time.getBoundingClientRect().bottom + 8 - synlig : 0;
        // mangler det bare noen piksler, får dommen stå 4 px under dagvelgeren i stedet for 8
        if(ledig < 0) window.scrollBy(0, ledig); else if(under > 0) window.scrollBy(0, Math.min(under, ledig + 4));
      }
      if(etter) etter();
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
      heleSiden(()=>{ const k2 = $(`.dagknapp[data-day="${nd.key}"]`, root); if(k2) k2.focus({preventScroll: true}); }, true);
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

  /* ---------- nettsiden fra 1024 px (design B 4.0 steg 6, SPEC §6C) ---------- */
  // Samme valg av dag og time, dom, time, timestripe og skive som på mobil - og samme id-er (#spOver, #spUnder, #tstripe,
  // .dagknapp, #tilbakeNa), så timevalget og testene er felles. Lagt ut i et 12-kolonners rutenett: kornfoto 420 px med
  // navneplate, dom | kl. hh | skive, «Neste 7 dager», «Time for time» som tabell med etikettkolonne (hold musa over en
  // time for å velge den), «Spotten» (minikartet i kartstilen) og «Om spotten». Ren visning som resten av fila.
  function dagKolHtml(s, x, valgt){
    // én stor kolonne i «Neste 7 dager»: dato, dagens tall (48 px) og ord, beste vindu, svell og vind i den beste timen
    const b = dagsdom(s, x), at = midtPaa(x.key), n = b.st!=null ? Math.min(5, b.st) : null, h = b.h;
    const vindu = n!=null && n >= 1 && H.fsApent(b) ? (x.step===1 ? H.vinduKl(b.start, b.slutt).join("–") : fmtHour.format(new Date(h.t))) : null;   // som i domHtml: et vindu som er over, vises ikke
    const svell = h && h.swell_offshore!=null ? `${nf1.format(h.swell_offshore)} m${h.period!=null ? ` · ${nf0.format(h.period)} s` : ""}` : "";
    const vind = h && h.wind_speed!=null ? windLabel(h) : "";
    const aria = `${cap(fmtDato.format(at))}: ${n!=null ? STR.starsAria(n, 0) + ", " + domOrd(b) : domOrd(b).toLowerCase()}${vindu ? `, ${STR.spot.best.toLowerCase()} ${vindu}` : ""}`;
    return `<button type="button" class="dagknapp stor r-${n!=null ? n : 0}${n==null ? " " + b.cls : ""}" data-day="${x.key}" aria-pressed="${x.key===valgt}" aria-label="${esc(aria)}">
        <span class="ud">${esc(ukedagKort(at))} ${x.key.slice(8, 10)}.${x.key.slice(5, 7)}</span>
        <span class="dk-v">${n!=null ? `<span class="dk-tall">${n}</span>` : ""}<span class="dk-ord">${esc(domOrd(b))}</span></span>
        <span class="dk-best">${vindu ? `${esc(STR.spot.best)} ${esc(vindu)}` : "–"}</span>
        <span class="dk-sub">${esc(svell)}</span><span class="dk-sub">${esc(vind)}</span></button>`;
  }
  function omSpottenHtml(s, h){
    // det spoten selv har i spots.json, og sikkerheten for timen som er valgt - ingen beskrivelse finnes i dataene
    const sek = (w)=> !w ? [] : Array.isArray(w[0]) ? w : [w];
    const rad = (k, v)=> v ? `<div><dt class="etikett">${esc(k)}</dt><dd>${esc(v)}</dd></div>` : "";
    const sikk = h ? sikkerhet(h) : "–";
    return `<dl class="spw-om">
        ${rad(STR.spot.vindu, sek(visVindu(s)).map(([a, b])=> `${a}–${b}°`).join(", "))}
        ${rad(cap(STR.wind.offshore), sek(s.offshore_wind).map(([a, b])=> `${a}–${b}°`).join(", "))}
        ${rad(STR.web.om.vender, s.facing!=null ? `${compass(s.facing)} ${Math.round(s.facing)}°` : "")}
        ${rad(STR.spot.tidevann, window.Tidevann ? Tidevann.prefTekst(s) : "")}
        ${rad(STR.web.om.hoyde, s.ideal_height ? `${nf1.format(s.ideal_height[0])}–${nf1.format(s.ideal_height[1])} m` : "")}
        ${rad(STR.web.om.data, `${sikk!=="–" ? sikk + ". " : ""}${STR.web.varselFra(relDay(new Date(DATA.generated)), fmtTime.format(new Date(DATA.generated)))}. ${STR.web.usikre}.`)}
      </dl>`;
  }
  function renderWeb(root, s, S){
    const {dager, d, idx: idx0} = valgMobil(s, S); let idx = idx0;
    S.tideMin = 0;
    const b = dagsdom(s, d), best = besteSett(s, d, b);
    const ev = window.Tidevann ? Tidevann.hendelser(s) : [];
    const timen = ()=>{ const h = idx!=null ? s.hours[idx] || null : null; return {h, t: h ? new Date(h.t) : new Date()}; };
    const foto = !!(window.Skive && Skive.harBilde(s.id)), id = encodeURIComponent(s.id);
    const K = window.KJORETID, kj = H.kjoreText(s.id), at = midtPaa(d.key), reg = H.regionOf(s);
    const meta = ()=>{ const {h, t} = timen();
      return [kj && K ? STR.hjem.kjoreAria(kj, K.fra.navn) : null, `${ukedagKort(at)} ${d.key.slice(8, 10)}.${d.key.slice(5, 7)}`, ...faktaDeler(s, h, t)].filter(Boolean).map(x=> `<span>${esc(x)}</span>`).join(" "); };   // mellomrom: skjermleseren leser delene hver for seg
    const over = ()=>{ const {h, t} = timen(); return timeHtml(s, h, t, ev); };
    const under = ()=>{ const {h, t} = timen(), hh = fmtHour.format(t); return `<h2 class="sr">${esc(STR.spot.retning(hh))}</h2>${window.Skive ? Skive.html(s, h, hh, {stor: true}) : ""}`; };
    const hvorfor = ()=> hvorforHtml(timen().h);
    const merker = H.merker(s);
    const morkeKol = Timestripe.kolonner(s, d, idx, H).some(c=> c.i >= 0 && H.mork(s.hours[c.i]));
    const tilbakeNa = ()=> S.idx!=null ? `<button type="button" class="tilbakena" id="tilbakeNa">${esc(STR.spot.tilbakeNa)}</button>` : "";
    const fav = isFavSpot(s.id);
    const sju = dager.slice(0, 7), resten = dager.slice(7);
    root.innerHTML = `${typeof staleBanner==="function" ? staleBanner() : ""}<div class="spw">
      <div class="spw-hode${foto ? "" : " uten"}">
        ${foto ? `<img class="sp-foto trykk" src="img/spots/${id}-trykk.jpg" alt="${esc(STR.spot.bildeAlt(s.name))}" decoding="async"><img class="sp-foto lodd" src="img/spots/${id}-lodd.jpg" alt="${esc(STR.spot.bildeAlt(s.name))}" decoding="async">` : ""}
        <div class="spw-plate"><a class="etikett spw-reg" href="#utforsk" id="spotRegion">${esc(reg)} <span aria-hidden="true">›</span></a>
          <h1 class="t-hero${lengsteOrd(s.name) > 8 ? " lang" : ""}" style="--n:${lengsteOrd(s.name)}">${esc(s.name)}</h1></div>
      </div>
      <div class="spw-inn">
        <p class="fakta-linje spw-meta" id="spMeta">${meta()}</p>${merker.length ? `<p class="etikett sp-merker">${esc(merker.join(" · "))}</p>` : ""}
        ${foto ? `<p class="kredit linje">${kreditHtml()}</p>` : ""}
        <div class="spw-grid">
          <div class="spw-dom">${domHtml(s, d, b)}
            <div class="spw-knapper"><button type="button" class="fav-btn knapp1" data-fav="${esc(s.id)}" aria-pressed="${fav}">${esc(fav ? STR.web.fjernFav : STR.web.lagreFav)}</button><button type="button" class="knapp2" id="loggHer">${esc(STR.logSession)}</button></div></div>
          <div class="spw-time" id="spOver">${over()}</div>
          <div class="spw-skive" id="spUnder">${under()}</div>
        </div>
        <div class="sek-spot"><h2 class="h2">${esc(STR.web.neste7)}</h2><p class="sub">${esc(STR.web.usikre)}</p></div>
        <div class="dagvelger sju" role="group" aria-label="${esc(STR.spot.velgDag)}">${sju.map(x=> dagKolHtml(s, x, d.key)).join("")}</div>
        ${resten.length ? `<div class="uke2"><p class="etikett">${esc(STR.web.uke2)}</p>${dagvelgerHtml(s, resten, d)}</div>` : ""}
        <div class="sek-spot"><h2 class="h2">${esc(STR.web.timeForTime(cap(fmtWd.format(at))))}</h2><p class="sub">${esc([morkeKol ? STR.lightOnly : null, STR.web.holdMusa].filter(Boolean).join(" · "))}</p></div>
        <div id="spStripe">${Timestripe.html(s, d, idx, best, H, {bred: true})}</div>
        <div class="sp-tilbakena" id="spTilbakeNa">${tilbakeNa()}</div>
        <div id="spHvorfor">${hvorfor()}</div>
        <div class="spw-to">
          <section><div class="sek-spot"><h2 class="h2">${esc(STR.web.spotten)}</h2></div>${minikartHtml(s, timen().h)}</section>
          <section><div class="sek-spot"><h2 class="h2">${esc(STR.web.omSpotten)}</h2></div><div id="spOm">${omSpottenHtml(s, timen().h)}</div></section>
        </div>
      </div></div>`;
    const heleSiden = (etter)=>{ const y = window.scrollY; renderWeb(root, s, S); window.scrollTo(0, y); if(etter) etter(); };
    const kobleTilbakeNa = ()=>{ const tn = $("#tilbakeNa", root); if(tn) tn.onclick = ()=>{ S.idx = null; heleSiden(); }; };
    const kobleHvorfor = ()=>{ const hv = $("#hvorfor", root); if(hv) hv.addEventListener("toggle", ()=> hv.querySelector("summary").setAttribute("aria-expanded", String(hv.open))); };
    $("#loggHer", root).onclick = ()=> openSheet(s.id, timen().t);
    $("#spotRegion", root).onclick = ()=>{ S.utforskView = reg; S.utforskViewSatt = true; };   // Utforsk åpner på spotens region
    wireFavButtons(); kobleTilbakeNa(); kobleHvorfor();
    $$(".dagknapp", root).forEach(kn=> kn.onclick = ()=>{
      const nd = dager.find(x=> x.key===kn.dataset.day); if(!nd || nd.key===d.key || !nd.idxs.length) return;
      const n = H.nowIdx(s);
      S.idx = nd.key===dayKey(new Date()) && nd.idxs.includes(n) && H.usable(s.hours[n]) ? null : SpotGraf.bestOfDay(s, nd);
      heleSiden(()=>{ const k2 = $(`.dagknapp[data-day="${nd.key}"]`, root); if(k2) k2.focus({preventScroll: true}); });
    });
    Timestripe.mount(root, s, d, idx, best, H, (i)=>{
      // timevalg i samme dag (dra, trykk, piltaster eller musa over en time): bytt bare det som hører til timen
      const hv = $("#hvorfor", root), open = hv ? hv.open : false;
      idx = i; S.idx = i;
      $("#spMeta", root).innerHTML = meta(); $("#spOver", root).innerHTML = over(); $("#spUnder", root).innerHTML = under();
      $("#spHvorfor", root).innerHTML = hvorfor(); $("#spOm", root).innerHTML = omSpottenHtml(s, timen().h); $("#spTilbakeNa", root).innerHTML = tilbakeNa();
      const mk = $("#miniKort", root); if(mk) mk.outerHTML = minikartHtml(s, timen().h);
      kobleTilbakeNa(); kobleHvorfor();
      const hv2 = $("#hvorfor", root); if(hv2 && open) hv2.open = true;
    });
    if(!(s.id in kystCache)){
      kystLoading[s.id] = kystLoading[s.id] || fetch(`data/minikart/${encodeURIComponent(s.id)}.json`, {cache:"force-cache"}).then(r=> r.ok ? r.json() : {}).catch(()=>({}));
      kystLoading[s.id].then(k=>{ kystCache[s.id] = k || {}; const el = $("#miniKort", root); if(el && S.view==="spot" && S.spotId===s.id) el.outerHTML = minikartHtml(s, timen().h); });
    }
  }

  /* ---------- render ---------- */
  function render(root, s, S, helpers){
    H = helpers;
    return H.isDesktop() ? renderWeb(root, s, S) : renderMobil(root, s, S);
  }
  window.Spot = { render, kroppshoyde, visHoyde, energiOrd, energiGrenser, vinduTekst, sikkerhet, tideLevel, tzOffsetMs };
})();
