// Enkel offline-støtte: appen fra cache, varseldata alltid ferskt når nett finnes.
// CACHE-navnet må bumpes hver gang shell-filene endres (ny fane, nye
// js/css-filer) - ellers oppdager ikke nettleseren at sw.js-scriptet er
// likt som før og lar være å hente nytt innhold, sjøl om siden er pushet.
const CACHE = "nordsurf-v2";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon.svg", "js/map.js", "css/map.css"];
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
