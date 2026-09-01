const CACHE = 'noticias-laborales-18792b63c2ae';
const CORE = ['./', './index.html', './styles.css', './app.js', './manifest.webmanifest', './data/noticias.json', './icons/icon.svg'];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    for (const url of CORE) {
      try {
        await cache.add(url);
      } catch (err) {
        console.warn('sw skip', url, err);
      }
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

async function networkFirst(request) {
  try {
    const res = await fetch(request, { cache: 'no-store' });
    const copy = res.clone();
    caches.open(CACHE).then((c) => c.put(request, copy));
    return res;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw new Error('offline');
  }
}

async function staleWhileRevalidate(request) {
  const cached = await caches.match(request);
  const network = fetch(request).then((res) => {
    caches.open(CACHE).then((c) => c.put(request, res.clone()));
    return res;
  }).catch(() => cached);
  return cached || network;
}

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  const url = event.request.url;
  if (url.includes('/data/noticias.json')) {
    event.respondWith(networkFirst(event.request));
    return;
  }
  event.respondWith(staleWhileRevalidate(event.request));
});
