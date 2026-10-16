// Enkel offline-støtte: appen fra cache, varseldata alltid ferskt når nett finnes.
// CACHE-navnet er en hash av docs/ sitt innhold (utenom docs/data/), satt
// automatisk av fetcher/update_sw_cache.py - ALDRI rediger denne linja for
// hånd. Må stemme med filene, ellers oppdager ikke nettleseren at
// sw.js-scriptet er likt som før og lar være å hente nytt innhold, sjøl om
// siden er pushet (se CLAUDE.md sin arbeidsmåte og STATUS.md, 26.09-03.10.2026).
const CACHE = "nordsurf-676c1f246025";
const TILES = CACHE + "-fliser";   // detaljflisene (range-biter), eget tak - byttes sammen med CACHE
const TILES_MAX_ENTRIES = 600;      // ca. 600 range-biter à 1-60 KB: under ca. 15 MB
// S3 (16.10.2026): listen hadde to filer som ikke finnes (css/kart.css, js/front.js) - da feiler
// cache.addAll(), og en ny sw.js blir aldri installert. Nå bare filer som finnes (test_docs_cache sjekker det).
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon.svg",
  "css/app.css", "css/ui.css",
  "js/strings.js", "js/wordmark.js", "js/explain.js", "js/app.js", "js/kart.js", "js/minikart.js", "js/spotgraf.js",
  "js/spot.js", "js/utforsk.js", "js/ui.js", "js/auth.js",
  "vendor/maplibre-gl-5.24.0.js", "vendor/maplibre-gl-5.24.0.css", "vendor/pmtiles-4.5.0.js",
  "geo/coast.json", "geo/norge-oversikt.pmtiles",
  "fonts/bricolage-grotesque-latin-wght.woff2", "fonts/inter-latin-wght.woff2", "fonts/geist-latin-wght.woff2", "fonts/geist-mono-latin-wght.woff2",
  "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon-180.png", "icons/icon-maskable-512.png"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
  self.skipWaiting();  // ikke vent på at alle gamle faner lukkes før oppdateringen tas i bruk
});
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE && k !== TILES).map(k => caches.delete(k))))
    .then(() => self.clients.claim())  // ta kontroll over allerede åpne faner med en gang
));

/* ---------- kartflisene (PMTiles, HTTP Range) ----------
   PMTiles leser fila i biter med Range-forespørsler. Cache API kan ikke lagre 206-svar, og et helt
   200-svar må aldri leveres der nettleseren ba om en bit. Derfor:
   - norge-oversikt.pmtiles ligger hel i SHELL (precache): biten skjæres ut og leveres som 206.
   - norge-detalj.pmtiles: hver bit hentes fra nett (206) og lagres som et 200-svar under en egen nøkkel
     (<url>?r=<fra>-<til>) i TILES, med tak på antall (eldste ut først). Uten nett: lagret bit eller feil. */
function parseRange(h) { const m = /bytes=(\d+)-(\d*)/.exec(h || ""); return m ? [Number(m[1]), m[2] === "" ? null : Number(m[2])] : null; }
function partial(buf, range, type, etag) {
  const size = buf.byteLength, start = range[0], end = range[1] === null ? size - 1 : Math.min(range[1], size - 1);
  if (start >= size) return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
  const body = buf.slice(start, end + 1), h = { "Content-Type": type || "application/octet-stream", "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": String(body.byteLength), "Accept-Ranges": "bytes" };
  if (etag) h.ETag = etag;
  return new Response(body, { status: 206, headers: h });
}
async function rangeFromWhole(req, range) {
  const hit = await caches.match(req.url, { ignoreSearch: true });
  if (!hit) return fetch(req);
  return partial(await hit.arrayBuffer(), range, hit.headers.get("Content-Type"), hit.headers.get("ETag"));
}
async function rangeCached(req, range) {
  const key = `${req.url.split("?")[0]}?r=${range[0]}-${range[1] === null ? "" : range[1]}`;
  const c = await caches.open(TILES);
  const hit = await c.match(key);
  const cached = async () => new Response(await hit.arrayBuffer(), { status: 206, headers: new Headers(hit.headers) });
  // PMTiles ber om cache: "reload" etter et ETag-avvik (fila er byttet), og om "no-store" i Chrome på Windows - da
  // prøves nettet først, men uten nett brukes den lagrede biten likevel (ellers virker kartet aldri uten nett der)
  const fresh = req.cache === "reload" || req.cache === "no-store";
  if (hit && !fresh) return cached();
  let r;
  try { r = await fetch(req); }
  catch (e) { if (hit) return cached(); throw e; }
  if (r.status === 206) {
    const buf = await r.clone().arrayBuffer(), h = new Headers(r.headers);
    h.delete("Content-Encoding");
    c.put(key, new Response(buf, { status: 200, headers: h })).then(() => c.keys()).then(ks => {
      const extra = ks.length - TILES_MAX_ENTRIES;
      return extra > 0 ? Promise.all(ks.slice(0, extra).map(k => c.delete(k))) : null;
    }).catch(() => {});
  }
  return r;
}

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  // varseldata (S2: data/oversikt.json og data/spots/<id>.json): alltid ferskt når nett finnes, cache som reserve
  if (url.pathname.includes("/data/")) {
    e.respondWith(fetch(e.request).then(r => { const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); return r; }).catch(() => caches.match(e.request)));
    return;
  }
  if (url.pathname.endsWith(".pmtiles")) {
    const range = parseRange(e.request.headers.get("Range"));
    if (!range) { e.respondWith(caches.match(e.request).then(r => r || fetch(e.request))); return; }
    e.respondWith(url.pathname.endsWith("norge-oversikt.pmtiles") ? rangeFromWhole(e.request, range) : rangeCached(e.request, range));
    return;
  }
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
