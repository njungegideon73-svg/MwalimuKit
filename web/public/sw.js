import { clientsClaim } from 'workbox-core';
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { StaleWhileRevalidate, NetworkFirst } from 'workbox-strategies';

declare let self: ServiceWorkerGlobalScope;
self.skipWaiting();
clientsClaim();

precacheAndRoute(self.__WB_MANIFEST);

// Stale-while-revalidate for curriculum
registerRoute(
  ({ url }) => url.pathname.includes('/api/v1/curriculum/'),
  new StaleWhileRevalidate({ cacheName: 'curriculum', plugins: [] }),
);

// Network-first for API calls
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/v1/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 3,
  }),
);

// Background Sync: listen for sync events
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-scores') {
    event.waitUntil(syncScores());
  }
});

async function syncScores() {
  // Notify the main thread to trigger a sync
  const clients = await self.clients.matchAll();
  for (const client of clients) {
    client.postMessage({ type: 'BACKGROUND_SYNC', tag: 'sync-scores' });
  }
}

// Also sync when coming back online
self.addEventListener('online', () => {
  self.clients.matchAll().then((clients) => {
    for (const client of clients) {
      client.postMessage({ type: 'BACKGROUND_SYNC', tag: 'sync-scores' });
    }
  });
});
