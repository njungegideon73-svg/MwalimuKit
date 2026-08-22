import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'MwalimuKit',
        short_name: 'MwalimuKit',
        description: 'CBC assessment platform for Kenyan teachers',
        theme_color: '#0E7C66',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait-primary',
        start_url: '/',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          // Static, rarely-changing reference data: cache-first.
          {
            urlPattern: /^https?:\/\/.*\/api\/v1\/curriculum\/catalogue/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'curriculum-catalogue',
              expiration: { maxEntries: 4, maxAgeSeconds: 7 * 24 * 3600 },
              cacheableResponse: { statuses: [200] },
            },
          },
          // Live assessment data and auth: never serve from cache. Workbox
          // route handlers are GET-only by default; NetworkOnly makes the
          // intent explicit and guarantees no stale scores on shared devices.
          {
            urlPattern: /^https?:\/\/.*\/api\/v1\/(assessments|scores|runs|auth)(\/|$)/,
            handler: 'NetworkOnly',
          },
          // Moderately dynamic school data: network-first with a short TTL
          // so offline fallbacks exist but stale data ages out fast.
          {
            urlPattern: /^https?:\/\/.*\/api\/v1\/(classes|learners)(\/|$)/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-school-data',
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
              networkTimeoutSeconds: 3,
              cacheableResponse: { statuses: [200] },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
