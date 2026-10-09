// Enkel offline-støtte: appen fra cache, varseldata alltid ferskt når nett finnes.
// CACHE-navnet er en hash av docs/ sitt innhold (utenom docs/data/), satt
// automatisk av fetcher/update_sw_cache.py - ALDRI rediger denne linja for
// hånd. Må stemme med filene, ellers oppdager ikke nettleseren at
// sw.js-scriptet er likt som før og lar være å hente nytt innhold, sjøl om
// siden er pushet (se CLAUDE.md sin arbeidsmåte og STATUS.md, 26.09-03.10.2026).
const CACHE = "nordsurf-3aa116de65f3";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon.svg",
  "css/app.css", "css/kart.css",
  "js/strings.js", "js/wordmark.js", "js/explain.js", "js/app.js", "js/kart.js", "js/front.js", "js/auth.js",
  "geo/coast.json",
  "fonts/bricolage-grotesque-latin-wght.woff2", "fonts/inter-latin-wght.woff2", "fonts/geist-latin-wght.woff2", "fonts/geist-mono-latin-wght.woff2",
  "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon-180.png", "icons/icon-maskable-512.png"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
  self.skipWaiting();  // ikke vent på at alle gamle faner lukkes før oppdateringen tas i bruk
});
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim())  // ta kontroll over allerede åpne faner med en gang
));
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.pathname.endsWith("forecast.json")) {
    e.respondWith(fetch(e.request).then(r => { const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); return r; }).catch(() => caches.match(e.request)));
    return;
  }
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
