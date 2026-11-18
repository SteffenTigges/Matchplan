// Matchplan Service Worker: App-Hülle aus dem Speicher, Daten immer zuerst frisch aus dem Netz.
const CACHE = "matchplan-v1";
const SHELL = ["./", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin) return;
  const put = (res) => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
    return res;
  };
  if (url.pathname.includes("/data/")) {
    e.respondWith(fetch(e.request).then(put).catch(() => caches.match(e.request)));
  } else {
    e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then(put)));
  }
});
