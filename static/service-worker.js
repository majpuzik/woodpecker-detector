// Service Worker for PWA
const CACHE_NAME = 'woodpecker-detector-v1';

self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker activated');
});

self.addEventListener('fetch', (event) => {
  // Let requests go through to server
  event.respondWith(fetch(event.request));
});
