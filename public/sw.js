// AI-pelit service worker. The build replaces the id below with a hash of the shell and the
// catalog, so every deploy that changes either is a new worker and phones pick it up.
'use strict';

var BUILD = '__BUILD_ID__';
var SHELL_CACHE = 'ai-pelit-shell-' + BUILD;
// Version folders never change once published, so they keep one cache across builds.
var GAMES_CACHE = 'ai-pelit-games';
var SHELL = [
  './',
  'index.html',
  'app.js',
  'app.css',
  'back.js',
  'catalog.json',
  'manifest.webmanifest',
  'icons/icon-192.png',
  'icons/icon-512.png',
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(function (cache) {
        return cache.addAll(SHELL.map(function (u) { return new Request(u, { cache: 'no-cache' }); }));
      })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.map(function (k) {
          if (k.indexOf('ai-pelit-shell-') === 0 && k !== SHELL_CACHE) return caches.delete(k);
        }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

var GAMES_PREFIX = new URL('games/', self.registration.scope).pathname;

// A version folder: cache first, filled the first time it is played.
function gameFile(request) {
  return caches.open(GAMES_CACHE).then(function (cache) {
    return cache.match(request, { ignoreSearch: true }).then(function (hit) {
      if (hit) return hit;
      return fetch(request).then(function (response) {
        if (response.ok) cache.put(request, response.clone());
        return response;
      });
    });
  });
}

// The shell and the catalog: network first (revalidating past the HTTP cache), cache offline.
function shellFile(request) {
  return caches.open(SHELL_CACHE).then(function (cache) {
    return fetch(request, { cache: 'no-cache' })
      .then(function (response) {
        if (response.ok) cache.put(request, response.clone());
        return response;
      })
      .catch(function () {
        return cache.match(request, { ignoreSearch: true }).then(function (hit) {
          if (hit) return hit;
          if (request.mode === 'navigate') return cache.match('index.html');
          return Response.error();
        });
      });
  });
}

self.addEventListener('fetch', function (event) {
  var request = event.request;
  if (request.method !== 'GET') return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin || url.href.indexOf(self.registration.scope) !== 0) return;
  event.respondWith(url.pathname.indexOf(GAMES_PREFIX) === 0 ? gameFile(request) : shellFile(request));
});
