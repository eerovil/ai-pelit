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
//   .name()                    the phone's nickname ('' when none)
//   .setName(name)             -> Promise of {ok, status}: kept only once the server took it (or
//                              there was no network, when it is sent later); a name taken by
//                              another phone (409) or refused for now (429) leaves the old one
//   .nameError(r, name)        what went wrong, in Finnish, for a setName answer
//   .friendError(r)            the same for ask(), answer(), remove() and invite()
//   .nameNote()                what is wrong with the kept nickname ('' when nothing): taken,
//                              rejected by the admin, or not yet sent
//   .doing(friend)             "Pelaa: Pilkkiminen", "Selaa pelejä", "Nähty 5 min sitten"…
//   .push.state()              -> Promise of invites as phone notifications (#367): 'on', 'off',
//                              'blocked' (denied in the phone's settings), 'install' (an iPhone
//                              outside the installed app) or 'none' (the browser cannot)
//   .push.set(on)              -> Promise of {ok, state, error}: asks permission and subscribes, or
//                              unsubscribes; error is in Finnish ('' when none)
//   .push.note(state)          what a state means, in Finnish ('' for 'on' and 'off')
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
  function registerName() {
    var n = name();
    if (!n) return Promise.resolve({ ok: false, status: 400 });
    if (load(K + 'lahetetty', '') === n) return Promise.resolve({ ok: true, status: 200 });
    return call('POST', 'players', { id: playerId(), name: n }).then(function (r) {
      if (r.status === 200) { save(K + 'lahetetty', n); save(K + 'tila', r.body.status); return { ok: true, status: 200 }; }
      if (r.status === 409) save(K + 'tila', 'taken');
      if (r.status === 429) save(K + 'tila', 'busy');
      return { ok: false, status: r.status };
    });
  }
  function register() { return registerName().then(function (r) { return r.ok; }); }
  function setName(n) {
    n = String(n || '').replace(/[\u0000-\u001f\u007f]/g, '').replace(/\s+/g, ' ').trim().slice(0, 16);
    if (!n) return Promise.resolve({ ok: false, status: 400 });
    var before = { nimi: load(K + 'nimi', null), tila: load(K + 'tila', null) };
    save(K + 'nimi', n); save(K + 'tila', 'pending');
    return registerName().then(function (r) {
      // Taken by another phone, or too many new names for now: the old name stays.
      if (r.status === 409 || r.status === 429) {
        ['nimi', 'tila'].forEach(function (k) {
          if (before[k] === null) { try { localStorage.removeItem(K + k); } catch (e) {} } else save(K + k, before[k]);
        });
      }
      return r;
    });
  }
  function nameError(r, n) {
    if (r.ok) return '';
    if (r.status === 409) return 'Nimimerkki ' + n + ' on jo käytössä. Valitse toinen.';
    if (r.status === 429) return 'Uusia nimimerkkejä tulee juuri nyt liikaa. Yritä myöhemmin.';
    if (r.status === 0) return 'Ei yhteyttä. Nimimerkki lähetetään, kun verkko toimii.';
    return 'Nimimerkkiä ei saatu tallennettua. Yritä uudelleen.';
  }
  function nameNote() {
    var n = name(), t = load(K + 'tila', '');
    if (!n) return '';
    if (t === 'taken') return 'Nimimerkkiä ' + n + ' käyttää jo joku muu. Valitse toinen.';
    if (t === 'rejected') return 'Ylläpitäjä ei hyväksynyt nimimerkkiä ' + n + '. Valitse toinen.';
    return '';
  }

  // ---- The state, and who hears about it ----
  var state = null, listeners = [];
  function take(r) {
    if (!r.ok || !r.body || !Array.isArray(r.body.friends)) return state;
    state = r.body;
    // The server's word on this phone's nickname, the one place it is read for friends: rejected
    // later by the admin, or forgotten (sent again on the next request).
    var n = name();
    if (n && state.me && state.me.name === n) save(K + 'tila', state.me.status);
    else if (n && !state.me && load(K + 'lahetetty', '') === n) save(K + 'lahetetty', '');
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
  // A 403 means the nickname is not (or no longer) usable: the refresh brings the server's word.
  function after(r) { return refresh().then(function () { return { ok: r.ok, status: r.status }; }); }
  // The nickname is sent first; when the server does not take it, the answer says why
  // (`name: true` with its status: 409 taken, 429 too many new names for now, 0 no network).
  function nameFirst(go) {
    return registerName().then(function (r) {
      return r.ok ? go() : { ok: false, status: r.status, name: true };
    });
  }
  function ask(pid) {
    return nameFirst(function () { return call('POST', 'friends/requests', { player: playerId(), to: pid }).then(after); });
  }
  function answer(pid, yes) {
    var go = function () { return call('POST', 'friends/requests/answer', { player: playerId(), from: pid, yes: !!yes }).then(after); };
    return yes ? nameFirst(go) : go();
  }
  // What went wrong with ask(), answer(), remove() or invite(), in Finnish ('' when nothing).
  function friendError(r) {
    if (r.ok) return '';
    if (r.name) return nameError(r, name());
    if (r.status === 403) return 'Nimimerkkiäsi ei hyväksytty: valitse toinen.';
    if (r.status === 409) return 'Kavereita on jo niin monta kuin mahtuu.';
    if (r.status === 429) return 'Liian monta pyyntöä. Yritä myöhemmin.';
    return 'Ei yhteyttä. Yritä uudelleen.';
  }
  function remove(pid) { return call('DELETE', 'friends', { player: playerId(), pid: pid }).then(after); }
  function invite(pid, where) {
    return call('POST', 'invites', { player: playerId(), to: pid, game: where.game, version: where.version, room: where.room })
      .then(function (r) { return { ok: r.ok, status: r.status }; });
  }

  // ---- Invites as phone notifications (#367) ----
  // A phone that switches them on gives the server its web push subscription; an invite to it
  // then wakes the site's service worker (sw.js), which asks the server what it was about and
  // shows it. The server's public signing key (server/api.js VAPID_PUBLIC):
  var VAPID = 'BBJL6kHsqkvq19Du_1GPSNscDuQIokodz5TgsdHR60ClQa4-mMJ3jgn2sGKjMfQdvTTyUVr_MVCNF2tFBynQ1ko';
  // The day the subscription was last told to the server; 'kesken' while the first telling has not
  // gone through (no network, a server error), so the next page tries again.
  var PUSH = 'ai-pelit:_kaverit:ilmoitukset';
  function iPhone() { return /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1); }
  function installed() { return navigator.standalone === true || (window.matchMedia && matchMedia('(display-mode: standalone)').matches); }
  function pushReg() {
    if (!('serviceWorker' in navigator) || !window.PushManager || !window.Notification) return Promise.resolve(null);
    // The site's own worker, which app.js registers; a game page is in its scope too.
    return Promise.race([
      navigator.serviceWorker.ready,
      new Promise(function (ok) { setTimeout(ok, 5000, null); }),
    ]).then(function (reg) { return reg && reg.pushManager ? reg : null; }, function () { return null; });
  }
  function pushState() {
    if (iPhone() && !installed() && !window.PushManager) return Promise.resolve('install');
    return pushReg().then(function (reg) {
      if (!reg) return iPhone() && !installed() ? 'install' : 'none';
      if (Notification.permission === 'denied') return 'blocked';
      return reg.pushManager.getSubscription().then(function (sub) {
        return sub && Notification.permission === 'granted' ? 'on' : 'off';
      });
    }).catch(function () { return 'none'; });
  }
  function pushNote(st) {
    if (st === 'blocked') return 'Ilmoitukset on estetty puhelimen asetuksista.';
    if (st === 'install') return 'iPhonessa ilmoitukset toimivat, kun pelit on lisätty kotivalikkoon.';
    if (st === 'none') return 'Tämä selain ei osaa näyttää ilmoituksia.';
    return '';
  }
  function keyBytes() {
    var s = atob(VAPID.replace(/-/g, '+').replace(/_/g, '/'));
    var b = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) b[i] = s.charCodeAt(i);
    return b;
  }
  function tellPush(sub) {
    return call('POST', 'push', { player: playerId(), endpoint: sub.endpoint }).then(function (r) {
      if (r.status === 404) save(K + 'lahetetty', ''); // the server does not know this phone
      if (r.ok) save(PUSH, new Date().toISOString().slice(0, 10));
      return r;
    });
  }
  function pushSet(on) {
    var done = function (ok, error) { return pushState().then(function (st) { return { ok: ok, state: st, error: error || pushNote(st) }; }); };
    return pushReg().then(function (reg) {
      if (!reg) return done(false);
      if (!on) {
        try { localStorage.removeItem(PUSH); } catch (e) {}
        return reg.pushManager.getSubscription().then(function (sub) {
          if (!sub) return done(true);
          var endpoint = sub.endpoint;
          return sub.unsubscribe().catch(function () {}).then(function () {
            return call('DELETE', 'push', { player: playerId(), endpoint: endpoint });
          }).then(function () { return done(true); });
        });
      }
      return nameFirst(function () {
        return Promise.resolve(Notification.permission === 'granted' ? 'granted' : Notification.requestPermission()).then(function (perm) {
          if (perm !== 'granted') return done(false);
          return reg.pushManager.getSubscription().then(function (sub) {
            return sub || reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes() });
          }).then(function (sub) { save(PUSH, 'kesken'); return tellPush(sub); }).then(function (r) {
            return done(r.ok, r.ok ? '' : 'Ilmoituksia ei saatu päälle. Yritä uudelleen.');
          });
        });
      }).then(function (r) {
        // nameFirst answers {ok:false, name:true} when the nickname could not be sent.
        return r && r.name ? done(false, name() ? nameError(r, name()) : 'Valitse ensin nimimerkki.') : r;
      }, function () { return done(false, 'Ilmoituksia ei saatu päälle. Yritä uudelleen.'); });
    });
  }
  // Once a day the subscription is told again, in case the browser renewed it or the server lost it.
  function pushSync() {
    var day = load(PUSH, '');
    if (!day || day === new Date().toISOString().slice(0, 10) || !window.Notification || Notification.permission !== 'granted') return;
    pushReg().then(function (reg) { return reg && reg.pushManager.getSubscription(); }).then(function (sub) {
      if (sub) tellPush(sub);
    }).catch(function () {});
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
    '#aipk button.no{background:rgba(255,255,255,.16)}#aipk .sp{flex:1}' +
    // On the shelf the top holds its links ("‹ Kaikki pelit"), so the banner sits at the bottom.
    '#aipk.low{top:auto;bottom:calc(env(safe-area-inset-bottom,0px) + 14px)}';
  var banner = null, dismissed = {}, busy = false;
  // Opens the invited game's room so that back still goes up (#68): game → its page → the shelf,
  // never back into the game this phone was playing. The same handoff as rooms.js uses when a
  // room code belongs to another game.
  function openInvite(slug, path) {
    var to = new URL(path, ROOT);
    // Leave the room this phone is in first, as "Poistu huoneesta" does: the others see it go
    // (a host's room closes), and the tab no longer rejoins it (rooms.js leave()).
    try { if (window.AiPelitRooms && AiPelitRooms.inRoom) AiPelitRooms.leave(); } catch (e) {}
    if (!here) {
      // On the shelf: as a tap on a game link there (app.js puts the game's page below it).
      var a = document.createElement('a');
      a.setAttribute('href', path);
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      a.remove();
      return;
    }
    var up = history.state && history.state.aiPelitUp;
    try {
      // Another version of this game: the same page stays below, and back.js marks it.
      if (up && slug === here[1]) sessionStorage.setItem('ai-pelit:_ylos', to.pathname);
      // Another game: back to this game's page, which app.js turns into that game's page before
      // it opens the game over it.
      if (up && slug !== here[1]) {
        sessionStorage.setItem('ai-pelit:_avaa', JSON.stringify({ from: '#/' + here[1], page: '#/' + slug, game: to.href }));
        history.back();
        return;
      }
    } catch (e) {}
    // Nothing of ours below: the invited game takes this page's place.
    location.replace(to.href);
  }
  function acceptInvite(inv) {
    if (!inv || !inv.id || !inv.game || !/^[A-Z]{4}$/.test(inv.room)) return Promise.resolve({ ok: false });
    return call('POST', 'invites/' + inv.id + '/answer', { player: playerId() }).then(function (r) {
      if (r.ok) openInvite(inv.game, 'games/' + inv.game + '/v' + inv.version + '/?huone=' + inv.room);
      return r;
    });
  }
  function declineInvite(inv) {
    if (!inv || !inv.id) return Promise.resolve({ ok: false });
    return call('POST', 'invites/' + inv.id + '/answer', { player: playerId() })
      .then(function (r) { return refresh().then(function () { return r; }); });
  }
  function roomScreenShowing() { var r = document.getElementById('aipr'); return !!(r && !r.hidden); }
  function drawBanner() {
    if (!document.body) return;
    var inv = !window.AiPelitKaverit.quietInvites && state &&
      state.invites.filter(function (i) { return !dismissed['i' + i.id]; })[0];
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
    if (!here) banner.className = 'low';
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
        var url = 'games/' + inv.game + '/v' + inv.version + '/?huone=' + inv.room;
        call('POST', 'invites/' + inv.id + '/answer', { player: playerId() }).then(function () { busy = false; openInvite(inv.game, url); });
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
    nameError: nameError,
    friendError: friendError,
    nameNote: nameNote,
    refresh: refresh,
    watch: watch,
    on: function (fn) { listeners.push(fn); },
    status: status,
    ask: ask,
    answer: answer,
    remove: remove,
    invite: invite,
    acceptInvite: acceptInvite,
    declineInvite: declineInvite,
    quietInvites: false,
    doing: doing,
    title: title,
    get titles() { return titles ? Object.keys(titles).length : 0; }, // game names read so far
    drawBanner: drawBanner,
    push: { state: pushState, set: pushSet, note: pushNote },
  };
  // rooms.js may be waiting for this file: tell it it is here.
  try { window.dispatchEvent(new Event('aipelitkaverit')); } catch (e) {}
  ping();
  pushSync();
})();
