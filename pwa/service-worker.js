// Minimal service worker. This app needs a live connection to Streamlit's
// backend (WebSocket), so there's no meaningful offline mode — this worker
// only exists to satisfy browser "installable PWA" criteria, and passes
// every request straight through to the network.
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
