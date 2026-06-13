const CACHE_NAME = 'petomania-v1';

// Fisiere statice de cacheat
const STATIC_ASSETS = [
    '/static/css/site.css',
    '/static/css/petomania.css',
    '/static/css/battle.css',
    '/static/imagini/sigla.png',
    '/static/imagini/dacoin.png',
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Nu cachea API calls sau autentificare
    if (url.pathname.startsWith('/joc/petomania/api') ||
        url.pathname.startsWith('/joc/petomania/login') ||
        url.pathname.startsWith('/joc/petomania/callback')) {
        return;
    }

    // Cache-first pentru statice, network-first pentru pagini
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(cached => {
                return cached || fetch(event.request).then(response => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return response;
                });
            })
        );
    } else {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
    }
});
