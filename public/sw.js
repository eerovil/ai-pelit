// AI-pelit service worker. The build replaces the id below with a hash of the shell and the
// catalog, so every deploy that changes either is a new worker and phones pick it up.
'use strict';

var BUILD = '__BUILD_ID__';
var SHELL_CACHE = 'ai-pelit-shell-' + BUILD;
// Version folders never change once published, so they keep one cache across builds. Only each
// game's newest is kept (#346): a new worker drops the files of the versions before it.
var GAMES_CACHE = 'ai-pelit-games';
// Game pictures (#33) are named by their content, so they too keep one cache across builds.
var THUMBS_CACHE = 'ai-pelit-thumbs';
// Shared libraries (three.js, #99) live in folders named after their release and never change,
// so they keep one cache across builds too. Filled on first use: a phone that never opens a game
// using one never downloads it.
var LIB_CACHE = 'ai-pelit-lib';
// The shelf is cached as './' only: Cloudflare Pages redirects index.html to './', and a
// redirected response cannot answer a page load.
var SHELL = [
  './',
  'app.js',
  'app.css',
  'back.js',
  'scores.js',
  'rooms.js',
  'outfits.js',
  'kaverit.js',
  'catalog.json',
  'manifest.webmanifest',
  'icons/icon-192.png',
  'icons/icon-512.png',
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(function (cache) {
        return cache.addAll(SHELL.map(function (u) { return new Request(u, { cache: 'no-cache' }); }))
          .then(function () { return cache.match('catalog.json'); })
          .then(function (r) { return r.json(); })
          .then(cacheThumbs);
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
      .then(pruneGames)
      .then(function () { return self.clients.claim(); })
  );
});

// The cached files of a version that is no longer its game's newest (#346): the site has sent
// its address on to the newest since, so the copy would only keep the phone on an old game.
function pruneGames() {
  return caches.open(SHELL_CACHE)
    .then(function (shell) { return shell.match('catalog.json'); })
    .then(function (r) { return r ? r.json() : null; })
    .then(function (catalog) {
      if (!catalog) return;
      var newest = {};
      catalog.games.forEach(function (g) { newest[g.slug] = g.versions[g.versions.length - 1].n; });
      return caches.open(GAMES_CACHE).then(function (cache) {
        return cache.keys().then(function (keys) {
          return Promise.all(keys.map(function (req) {
            var m = new URL(req.url).pathname.slice(GAMES_PREFIX.length).match(/^([^/]+)\/v(\d+)\//);
            if (m && newest[m[1]] !== undefined && Number(m[2]) !== newest[m[1]]) return cache.delete(req);
          }));
        });
      });
    })
    .catch(function () { /* a cache left as it was is still a working one */ });
}

// Every game's picture, so the whole shelf shows offline; pictures no game uses any more go.
// A picture that fails to load now is fetched when the shelf shows it.
function cacheThumbs(catalog) {
  var wanted = catalog.games.map(function (g) { return new URL(g.thumb, self.registration.scope).href; });
  return caches.open(THUMBS_CACHE).then(function (cache) {
    return cache.keys().then(function (have) {
      var had = have.map(function (r) { return r.url; });
      return Promise.all(
        have.filter(function (r) { return wanted.indexOf(r.url) < 0; }).map(function (r) { return cache.delete(r); })
          .concat(wanted.filter(function (u) { return had.indexOf(u) < 0; }).map(function (u) {
            return cache.add(u).catch(function () {});
          }))
      );
    });
  });
}

var GAMES_PREFIX = new URL('games/', self.registration.scope).pathname;
var THUMBS_PREFIX = new URL('thumbs/', self.registration.scope).pathname;
var LIB_PREFIX = new URL('lib/', self.registration.scope).pathname;
// The online parts (high scores, #25) are live data: straight to the network, never cached.
var API_PREFIX = new URL('api/', self.registration.scope).pathname;

// A version folder, a picture or a library: cache first, filled the first time it is used.
function cachedFile(request, name) {
  return caches.open(name).then(function (cache) {
    return cache.match(request, { ignoreSearch: true }).then(function (hit) {
      if (hit) return hit;
      return fetch(request).then(function (response) {
        if (response.ok) cache.put(request, response.clone());
        return response;
      });
    });
  });
}

// An older version's page goes to the game's newest (#346), as the site's _redirects does, but from
// the cached catalog, so an old home-screen shortcut opens the newest offline too. The query
// (?huone=) goes along.
function gameFile(request, url) {
  var m = url.pathname.slice(GAMES_PREFIX.length).match(/^([^/]+)\/v(\d+)\/(index\.html)?$/);
  if (!m || request.mode !== 'navigate') return cachedFile(request, GAMES_CACHE);
  return caches.open(SHELL_CACHE)
    .then(function (shell) { return shell.match('catalog.json'); })
    .then(function (r) { return r ? r.json() : null; })
    .catch(function () { return null; })
    .then(function (catalog) {
      var game = catalog && catalog.games.filter(function (g) { return g.slug === m[1]; })[0];
      var newest = game && game.versions[game.versions.length - 1].n;
      if (newest && Number(m[2]) < newest) {
        return Response.redirect(GAMES_PREFIX + m[1] + '/v' + newest + '/' + url.search, 302);
      }
      return cachedFile(request, GAMES_CACHE);
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
          if (request.mode === 'navigate') return cache.match('./');
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
  if (url.pathname.indexOf(API_PREFIX) === 0) return;
  if (url.pathname.indexOf(GAMES_PREFIX) === 0) event.respondWith(gameFile(request, url));
  else if (url.pathname.indexOf(THUMBS_PREFIX) === 0) event.respondWith(cachedFile(request, THUMBS_CACHE));
  else if (url.pathname.indexOf(LIB_PREFIX) === 0) event.respondWith(cachedFile(request, LIB_CACHE));
  else event.respondWith(shellFile(request));
});

// A friend's invite into a room, as a notification (#367). The push carries nothing: the site is
// asked what it was about, by this phone's push address, which only this phone knows. With
// nothing open (the invite was answered, or it is old) nothing shows.
self.addEventListener('push', function (event) {
  event.waitUntil(
    self.registration.pushManager.getSubscription()
      .then(function (sub) {
        if (!sub) return null;
        return fetch(API_PREFIX + 'push/pending?endpoint=' + encodeURIComponent(sub.endpoint), { cache: 'no-store' })
          .then(function (r) { return r.ok ? r.json() : null; });
      })
      .then(function (got) {
        var inv = got && got.invite;
        if (!inv) return;
        return self.registration.showNotification(inv.name + ' kutsuu sinut pelaamaan: ' + inv.title, {
          body: 'Napauta, niin liityt huoneeseen.',
          icon: new URL('icons/icon-192.png', self.registration.scope).href,
          tag: 'ai-pelit-kutsu',
          renotify: true,
          data: { id: inv.id, url: new URL(inv.url, self.registration.scope).href },
          actions: [{ action: 'liity', title: 'Liity' }],
        });
      })
      .catch(function () {})
  );
});

// A tap joins the room: the invite is answered (so no banner asks again), and the room's game
// opens with ?huone=, in a window of this site already open when there is one.
self.addEventListener('notificationclick', function (event) {
  var data = event.notification.data || {};
  event.notification.close();
  if (!data.url) return;
  var answered = self.registration.pushManager.getSubscription().then(function (sub) {
    if (!sub || !data.id) return;
    return fetch(API_PREFIX + 'invites/' + data.id + '/answer', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ endpoint: sub.endpoint }),
    });
  }).catch(function () {});
  var opened = self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (wins) {
    var win = wins.filter(function (w) { return w.url.indexOf(self.registration.scope) === 0; })[0];
    if (win && win.navigate) {
      return win.focus().then(function (w) { return (w || win).navigate(data.url); }).catch(function () { return self.clients.openWindow(data.url); });
    }
    return self.clients.openWindow(data.url);
  });
  event.waitUntil(Promise.all([answered, opened]));
});
