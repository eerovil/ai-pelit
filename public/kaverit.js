// Friends (#324), shared by the shelf and every game version. back.js loads this file in every
// game; the shelf loads it itself. Two phones become friends in a game room (rooms.js draws
// "➕ Kaveriksi" beside each player, the other phone accepts). A phone with friends tells the
// server what it plays every 30 s while a page is on screen, and the answer brings back what its
// friends play, friend requests and invites into rooms; an invite shows as a banner here, in any
// game, with "Liity" opening that game's room.
//
// Phones know each other only by a friend id (pid), a hash of the secret player id
// (server/api.js pidOf). The player id and nickname are the high-score lists' own
// (ai-pelit:_pelaaja:*), so a phone has one name everywhere. Everything here is an extra: with no
// network nothing shows, and no game waits for it.
//
//   AiPelitKaverit.state       {pid, friends, requests, asked, invites} or null before the first answer
//   .refresh()                 reads it now; .watch(on) reads it every 10 s while on (a room screen);
//                              .watch(on, ms, lonely) every ms, and with lonely only while this
//                              phone has no friends (with friends, the 30 s "now playing" brings it)
//   .on(fn)                    fn() after every change
//   .status(pid)               'me', 'friend', 'asked', 'asks' (they asked this phone) or ''
//   .ask(pid) .answer(pid, yes) .remove(pid) .invite(pid, {game, version, room}) -> Promise of {ok, status}
//   .name() .setName(name)     the phone's nickname ('' when none)
//   .doing(friend)             "Pelaa: Pilkkiminen", "Selaa pelejä", "Nähty 5 min sitten"…
(function () {
  'use strict';
  if (window.AiPelitKaverit) return;
  var script = document.currentScript;
  var ROOT = new URL('./', script ? script.src : location.href);
  var API = new URL('api/', ROOT);
  var K = 'ai-pelit:_pelaaja:';
  var ON = 'ai-pelit:_kaverit:on'; // this phone has friends: tell what it plays
  var PING_MS = 30e3, WATCH_MS = 10e3;

  function load(k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

  // The same id scores.js makes, made here when this phone has none yet.
  function playerId() {
    var id = load(K + 'id', '');
    if (!/^[a-f0-9]{32}$/.test(id)) {
      var b = new Uint8Array(16);
      crypto.getRandomValues(b);
      id = Array.prototype.map.call(b, function (n) { return (n < 16 ? '0' : '') + n.toString(16); }).join('');
      save(K + 'id', id);
    }
    return id;
  }
  function name() { return String(load(K + 'nimi', '') || ''); }

  function call(method, path, body) {
    var init = { method: method, cache: 'no-store' };
    if (body) { init.headers = { 'content-type': 'application/json' }; init.body = JSON.stringify(body); }
    return fetch(new URL(path, API), init).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (b) { return { ok: r.ok, status: r.status, body: b }; });
    }).catch(function () { return { ok: false, status: 0, body: {} }; });
  }

  // Tells the server this phone's nickname, as scores.js does (same keys, so it is told once).
  function register() {
    var n = name();
    if (!n) return Promise.resolve(false);
    if (load(K + 'lahetetty', '') === n) return Promise.resolve(true);
    return call('POST', 'players', { id: playerId(), name: n }).then(function (r) {
      if (r.status === 200) { save(K + 'lahetetty', n); save(K + 'tila', r.body.status); return true; }
      if (r.status === 409) save(K + 'tila', 'taken');
      if (r.status === 429) save(K + 'tila', 'busy');
      return false;
    });
  }
  function setName(n) {
    n = String(n || '').replace(/[\u0000-\u001f\u007f]/g, '').replace(/\s+/g, ' ').trim().slice(0, 16);
    if (!n) return Promise.resolve(false);
    save(K + 'nimi', n); save(K + 'tila', 'pending');
    return register();
  }

  // ---- The state, and who hears about it ----
  var state = null, listeners = [];
  function take(r) {
    if (!r.ok || !r.body || !Array.isArray(r.body.friends)) return state;
    state = r.body;
    var had = load(ON, false);
    save(ON, state.friends.length > 0);
    if (state.friends.length || state.invites.length) readTitles();
    if (!had && state.friends.length) ping();
    listeners.slice().forEach(function (fn) { try { fn(); } catch (e) { setTimeout(function () { throw e; }); } });
    drawBanner();
    return state;
  }
  function refresh() {
    if (!window.fetch) return Promise.resolve(state);
    return call('GET', 'friends?player=' + playerId()).then(take);
  }
  function status(pid) {
    if (!state || !pid) return '';
    if (pid === state.pid) return 'me';
    if (state.friends.some(function (f) { return f.pid === pid; })) return 'friend';
    if (state.requests.some(function (f) { return f.pid === pid; })) return 'asks';
    if (state.asked.indexOf(pid) >= 0) return 'asked';
    return '';
  }

  // ---- What this page plays, every 30 s while it is on screen ----
  var here = location.pathname.match(/\/games\/([a-z0-9-]+)\/v(\d+)\//);
  var pingTimer = 0;
  function ping() {
    clearTimeout(pingTimer);
    if (!load(ON, false) || !load(K + 'id', '') || document.visibilityState === 'hidden' || !window.fetch) return;
    var body = { player: playerId() };
    if (here) { body.game = here[1]; body.version = +here[2]; }
    call('POST', 'presence', body).then(function (r) {
      if (r.status === 404) save(K + 'lahetetty', ''); // the server does not know this phone
      take(r);
    });
    pingTimer = setTimeout(ping, PING_MS);
  }
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible') ping(); else clearTimeout(pingTimer); });

  var watchTimer = 0, watching = false;
  function watch(on, ms, lonely) {
    clearTimeout(watchTimer);
    watching = !!on;
    if (!watching) return;
    (function tick() {
      if (!watching) return;
      if (document.visibilityState !== 'hidden' && !(lonely && load(ON, false))) refresh();
      watchTimer = setTimeout(tick, ms || WATCH_MS);
    })();
  }

  // ---- Asking, answering, inviting ----
  function after(r) { return refresh().then(function () { return { ok: r.ok, status: r.status }; }); }
  function ask(pid) {
    return register().then(function (ok) {
      if (!ok) return { ok: false, status: 403 };
      return call('POST', 'friends/requests', { player: playerId(), to: pid }).then(after);
    });
  }
  function answer(pid, yes) {
    var go = function () { return call('POST', 'friends/requests/answer', { player: playerId(), from: pid, yes: !!yes }).then(after); };
    if (!yes) return go();
    return register().then(function (ok) { return ok ? go() : { ok: false, status: 403 }; });
  }
  function remove(pid) { return call('DELETE', 'friends', { player: playerId(), pid: pid }).then(after); }
  function invite(pid, where) {
    return call('POST', 'invites', { player: playerId(), to: pid, game: where.game, version: where.version, room: where.room })
      .then(function (r) { return { ok: r.ok, status: r.status }; });
  }

  // ---- Game names, from the shelf's catalog ----
  var titles = null;
  function readTitles() {
    if (titles || !window.fetch) return;
    titles = {};
    fetch(new URL('catalog.json', ROOT)).then(function (r) { return r.ok ? r.json() : null; }).then(function (c) {
      if (!c || !Array.isArray(c.games)) return;
      c.games.forEach(function (g) { titles[g.slug] = g.title; });
      listeners.slice().forEach(function (fn) { try { fn(); } catch (e) {} });
      drawBanner();
    }).catch(function () {});
  }
  function title(slug) { readTitles(); return (titles && titles[slug]) || slug; }

  function ago(iso) {
    var min = Math.max(1, Math.round((Date.now() - Date.parse(iso)) / 60e3));
    if (min < 60) return min + ' min sitten';
    var h = Math.round(min / 60);
    if (h < 24) return h + ' t sitten';
    var d = Math.round(h / 24);
    return d + (d === 1 ? ' päivä' : ' päivää') + ' sitten';
  }
  function doing(f) {
    if (f.now) return f.game ? 'Pelaa: ' + title(f.game) : 'Selaa pelejä';
    return f.at ? 'Nähty ' + ago(f.at) : 'Ei vielä nähty';
  }

  // ---- The banner: an invite, or a friend request on a page with no room screen showing ----
  var BANNER_CSS =
    '#aipk{position:fixed;left:50%;transform:translateX(-50%);top:calc(env(safe-area-inset-top,0px) + 44px);z-index:2147483646;' +
    'width:min(340px,calc(100vw - 20px));box-sizing:border-box;display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:10px 12px;' +
    'border-radius:14px;background:#2b2140;color:#fff;box-shadow:0 6px 24px rgba(0,0,0,.35);font:600 15px/1.3 system-ui,sans-serif;touch-action:manipulation}' +
    '#aipk p{margin:0;flex:1 1 100%}#aipk b{color:#ffd166}' +
    '#aipk button{font:800 15px system-ui,sans-serif;padding:8px 14px;border:0;border-radius:10px;background:#4f9a3a;color:#fff}' +
    '#aipk button.no{background:rgba(255,255,255,.16)}#aipk .sp{flex:1}';
  var banner = null, dismissed = {}, busy = false;
  function roomScreenShowing() { var r = document.getElementById('aipr'); return !!(r && !r.hidden); }
  function drawBanner() {
    if (!document.body) return;
    var inv = state && state.invites.filter(function (i) { return !dismissed['i' + i.id]; })[0];
    // The shelf shows requests on its own page (app.js sets quietRequests), a room screen in its list.
    var req = !inv && state && !roomScreenShowing() && !window.AiPelitKaverit.quietRequests &&
      state.requests.filter(function (q) { return !dismissed['r' + q.pid]; })[0];
    var key = inv ? 'i' + inv.id + title(inv.game) : req ? 'r' + req.pid : '';
    if (banner && banner.getAttribute('data-k') === key) return;
    if (banner) { banner.remove(); banner = null; }
    if (!key) return;
    if (!document.getElementById('aipk-css')) {
      var st = document.createElement('style'); st.id = 'aipk-css'; st.textContent = BANNER_CSS; document.head.appendChild(st);
    }
    banner = document.createElement('div');
    banner.id = 'aipk'; banner.setAttribute('data-k', key); banner.setAttribute('role', 'alert');
    var p = document.createElement('p'), who = document.createElement('b');
    who.textContent = (inv || req).name;
    p.appendChild(who);
    p.appendChild(document.createTextNode(inv ? ' kutsuu sinut pelaamaan: ' + title(inv.game) : ' haluaa kaveriksi'));
    var spacer = document.createElement('span'); spacer.className = 'sp';
    var yes = document.createElement('button'), no = document.createElement('button');
    yes.textContent = inv ? 'Liity' : 'Hyväksy';
    no.className = 'no'; no.textContent = inv ? 'Ei nyt' : 'Ei';
    banner.appendChild(p); banner.appendChild(spacer); banner.appendChild(no); banner.appendChild(yes);
    ['pointerdown', 'pointerup', 'touchstart', 'touchend', 'mousedown', 'mouseup', 'click', 'keydown', 'keyup'].forEach(function (type) {
      banner.addEventListener(type, function (e) { e.stopPropagation(); }, { passive: true });
    });
    yes.addEventListener('click', function () {
      if (busy) return;
      busy = true;
      if (inv) {
        dismissed['i' + inv.id] = true;
        var url = new URL('games/' + inv.game + '/v' + inv.version + '/?huone=' + inv.room, ROOT).href;
        call('POST', 'invites/' + inv.id + '/answer', { player: playerId() }).then(function () { busy = false; location.assign(url); });
      } else {
        dismissed['r' + req.pid] = true;
        answer(req.pid, true).then(function () { busy = false; drawBanner(); });
      }
    });
    no.addEventListener('click', function () {
      if (inv) { dismissed['i' + inv.id] = true; call('POST', 'invites/' + inv.id + '/answer', { player: playerId() }); }
      else { dismissed['r' + req.pid] = true; answer(req.pid, false); }
      drawBanner();
    });
    document.body.appendChild(banner);
  }
  window.addEventListener('hashchange', drawBanner);

  window.AiPelitKaverit = {
    get state() { return state; },
    id: playerId,
    name: name,
    setName: setName,
    refresh: refresh,
    watch: watch,
    on: function (fn) { listeners.push(fn); },
    status: status,
    ask: ask,
    answer: answer,
    remove: remove,
    invite: invite,
    doing: doing,
    title: title,
    get titles() { return titles ? Object.keys(titles).length : 0; }, // game names read so far
    drawBanner: drawBanner,
  };
  // rooms.js may be waiting for this file: tell it it is here.
  try { window.dispatchEvent(new Event('aipelitkaverit')); } catch (e) {}
  ping();
})();
