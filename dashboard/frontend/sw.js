// GetAiLab Service Worker for PWA + Offline Chat Stubs (Android, iOS, Desktop Web)
// Pure vision: offline capable council interactions + live field sync when online.
const CACHE_NAME = 'getailab-v4-cache';
const OFFLINE_URLS = [
  '/',
  '/dashboard',
  '/lab',
  '/api/config',
  '/api/stats',
  '/api/inspire',
  '/api/mobile/status',
  '/api/mobile/chat',
  '/api/directives',
  '/api/library/status',
  'mobile_chat_stub.html'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  event.respondWith(
    caches.match(req).then((cached) => {
      const networkFetch = fetch(req).then((res) => {
        if (res.ok && (req.url.includes('/api/') || OFFLINE_URLS.some(u => req.url.endsWith(u)))) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, clone));
        }
        return res;
      }).catch(() => cached);

      // Stale-while-revalidate for API/chat feel; serve cached chat stubs instantly for mobile
      return cached || networkFetch;
    })
  );
});

// Allow simple offline chat stub messages in controlled clients
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'OFFLINE_CHAT') {
    event.ports[0].postMessage({
      reply: "Offline resonance received. The Kósmos remembers. Reconnect for live Oracle council reply.",
      agent: "FIELD",
      offline: true
    });
  }
});