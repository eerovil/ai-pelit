// Playing with friends: a live room for 2-8 phones (#34), shared by every game that has one. A
// version opts in with
//
//   <script src="../../../rooms.js" data-game="<slug>" data-min="2" data-max="5"></script>
//
// placed before the game's own script, and a button that calls AiPelitRooms.open(). This file
// draws the room screen (make a room, join by code, QR link or the list of public rooms, who is in,
// the host's "Julkinen huone" switch, "Aloita kierros"),
// keeps the connection, comes back to the room after a reload, and pauses the round while a phone
// in it is away. The game keeps the game: the phone that made the room (the host) runs the round
// and sends it to the others with send(); the others' messages go to the host. See "Live rooms"
// in AGENTS.md for the whole API.
//
// The room itself is a relay on this site's /api/rooms/<CODE> (rooms/worker.js). This file's own
// messages have a `t` starting with "_"; the room's are you, peers, hello and bye. A game uses any
// other `t`. Later versions load this same file, so it must stay compatible with every version
// that uses it. With no connection the game still plays alone.
//
// A game played in turns (the athletics meets, #297) calls turns(id => …) to say which phones the
// round needs right now. The round then waits only for an away phone whose turn it is, a phone
// that leaves the room keeps its player (the computer never takes it), the host's button skips
// the turn ('skip'), and the phone remembers the round so its room screen offers
// "Palaa kierrokseen".
//
// Voice (#322): in a room, every phone has a 🎤 chip; while it is held, the others in the room hear
// that phone. The sound goes straight between the phones (WebRTC), each phone connected to each
// other one; the room only passes on the calls' setup (`_rtc` messages, to one phone each), and
// Cloudflare's TURN relay (GET /api/voice/ice) passes the sound on when two phones cannot reach
// each other directly. Each phone may switch voice off on the room screen, and mute a player.
// A version may move the chip with data-voice-corner="left|top-left|top-right|bottom-left|
// bottom-right" (default: the right edge, a little above the middle) or leave voice out with
// data-voice="off". Without a microphone, permission or connection the game plays the same.
//
// Friends (#324): a phone with a nickname joins with its friend id (`fid`, a hash of its secret
// player id), and the room passes it on in `peers`. With public/kaverit.js on the page (back.js
// loads it), the room screen shows "➕ Kaveriksi" beside each other player who has one, the
// requests sent to this phone ("Hyväksy" / "Ei"), and "📨 Kutsu kaveri", which invites a friend
// into this room.
(function () {
  'use strict';
  var script = document.currentScript;
  var GAME = script.getAttribute('data-game') || '';
  var MIN = Math.max(2, +script.getAttribute('data-min') || 2);
  var MAX = Math.min(8, Math.max(MIN, +script.getAttribute('data-max') || 5));
  var vm = location.pathname.match(/\/v(\d+)\//);
  var VERSION = vm ? +vm[1] : 1;
  var API = new URL('api/rooms/', script.src);
  var LIST = new URL('../rooms?game=' + encodeURIComponent(GAME), API); // this game's public rooms (#50)

  var LETTERS = 'ABCDEFGHJKLMNPRSTUVY'; // easy to read aloud: no I, O, Q, W, X, Z
  var NICKS = ['Siili', 'Orava', 'Kettu', 'Jänis', 'Pöllö', 'Ilves', 'Hirvi', 'Majava'];
  var COLORS = ['#e2574c', '#3f8ad8', '#3fa65a', '#e0a526', '#9a5cc6', '#e07ab0', '#2bb3b1', '#8a6a4a'];
  var NAME = 'ai-pelit:_pelaaja:nimi'; // the phone's one nickname, shared with scores.js
  var PICKED = 'ai-pelit:_huone:nimi'; // an animal name picked for a phone with no nickname
  var KEY = 'ai-pelit:_huone:avain'; // this phone's secret key, never shown to the others
  var HERE = 'ai-pelit:_huone:nyt';
  var ISANTA = 'ai-pelit:_isanta'; // short-lived handoff while the host switches games (#354) // sessionStorage: the room this tab is in, to rejoin after a reload
  var COUNTED = 'ai-pelit:_huone:kierros'; // sessionStorage: rounds whose result this tab saved
  var AWAY = 'ai-pelit:_huone:kesken'; // a turns() game's round this phone is in, to come back to
  var AWAY_MS = 6 * 3600e3; // forgotten after this long

  function load(k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function sload(k, d) { try { var v = sessionStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
  function ssave(k, v) { try { if (v === null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function hex(n) { return Array.prototype.map.call(crypto.getRandomValues(new Uint8Array(n)), function (b) { return (b < 16 ? '0' : '') + b.toString(16); }).join(''); }
  function cleanName(s) { return String(s || '').replace(/[\u0000-\u001f\u007f]/g, '').replace(/\s+/g, ' ').trim().slice(0, 16); }

  var myKey = load(KEY, '') || (function () { var k = hex(16); save(KEY, k); return k; })();

  // ---- Friends (#324) ----
  // This phone's friend id: the first 32 hex digits of SHA-256 of its player id (the high-score
  // lists' own, made here as scores.js makes it). Only a phone with a nickname tells it.
  var PLAYER = 'ai-pelit:_pelaaja:id';
  // The hash takes a moment: connect() waits for it (fidWait), so even the first join (a room
  // link, or a name typed on the room screen just now) carries it.
  var myFid = '', fidFor = '', fidWait = null;
  function findFid() {
    if (!cleanName(load(NAME, '')) || !window.crypto || !crypto.subtle) return;
    var id = load(PLAYER, '');
    if (!/^[a-f0-9]{32}$/.test(id)) { id = hex(16); save(PLAYER, id); }
    if (fidFor === id) return;
    fidFor = id;
    var wait = fidWait = crypto.subtle.digest('SHA-256', new TextEncoder().encode(id)).then(function (h) {
      myFid = Array.prototype.map.call(new Uint8Array(h).slice(0, 16), function (b) { return (b < 16 ? '0' : '') + b.toString(16); }).join('');
    }).catch(function () { fidFor = ''; }).then(function () { if (fidWait === wait) fidWait = null; });
  }
  findFid();
  function friendsLib() { return window.AiPelitKaverit || null; }
  // A name picked here is kept, so it stays the same after a reload or a QR join. It is not the
  // nickname, so the high-score list still asks for a real one.
  function myName() {
    return cleanName(load(NAME, '')) || load(PICKED, '') || (function () {
      var n = NICKS[Math.floor(Math.random() * NICKS.length)]; save(PICKED, n); return n;
    })();
  }

  // ---- What the game sees ----
  var handlers = {};
  function fire(type) {
    var args = Array.prototype.slice.call(arguments, 1);
    (handlers[type] || []).slice().forEach(function (fn) { try { fn.apply(null, args); } catch (e) { setTimeout(function () { throw e; }); } });
  }

  var net = {
    on: false, host: false, code: '', ws: null, connected: false, joined: false, tries: 0, timer: 0,
    me: '', hostId: '', members: [], online: {}, pub: false, wait: false, listening: false, error: '', result: '', resultClass: '', note: '',
    // The round as this phone knows it: {id, players: [{id, name}], over}. Kept after it ends, so
    // a phone that was away gets it back.
    round: null, released: {}, owed: {}, pz: [], played: false, sent: 0, got: {},
  };
  function sendRaw(m) { if (net.ws && net.ws.readyState === 1) net.ws.send(JSON.stringify(m)); }
  function hostOn() { return !!net.online[net.hostId]; }
  function hostName() { var h = net.members.filter(function (m) { return m.id === net.hostId; })[0]; return h ? h.name : 'huoneen tekijä'; }
  function inRound(id) { return !!(net.round && net.round.players.some(function (p) { return p.id === id; })); }
  function racing() { return !!(net.round && !net.round.over); }

  // ---- A game played in turns (#297) ----
  var needs = null; // id => true while the round needs that phone; null: it needs every phone
  function needed(id) { try { return !needs || !!needs(id); } catch (e) { return true; } }
  // The round this phone is in, kept while it lasts, so the phone can come back to it even after
  // closing the game. Only for a guest: the host keeps the round and cannot leave it.
  function keepAway() {
    if (needs && net.on && !net.host && racing()) save(AWAY, { game: GAME, v: VERSION, code: net.code, round: net.round.id, at: Date.now() });
  }
  function forgetAway(code) {
    var a = load(AWAY, null);
    if (a && (!code || a.code === code)) try { localStorage.removeItem(AWAY); } catch (e) {}
  }
  function awayRound() {
    var a = load(AWAY, null);
    if (!needs || !a || a.game !== GAME || a.v !== VERSION || !/^[A-Z]{4}$/.test(a.code) || !(Date.now() - a.at < AWAY_MS)) return null;
    return a;
  }

  // ---- The connection ----
  function connect() {
    clearTimeout(net.timer);
    findFid();
    if (fidWait) {
      render();
      fidWait.then(function () { if (net.on && !net.ws) connect(); });
      return;
    }
    var u = new URL(net.code, API);
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
    var q = { key: myKey, name: myName() };
    if (myFid && cleanName(load(NAME, ''))) q.fid = myFid;
    if (net.host) { q.host = '1'; q.game = GAME; q.v = VERSION; q.max = MAX; }
    u.search = new URLSearchParams(q);
    var ws;
    try { ws = new WebSocket(u); } catch (e) { return; }
    net.ws = ws;
    ws.onopen = function () { if (net.ws === ws) { net.connected = true; listed = null; render(); } };
    ws.onmessage = function (e) {
      if (net.ws !== ws) return;
      var m;
      try { m = JSON.parse(e.data); } catch (err) { return; }
      if (m && typeof m === 'object') onMessage(m);
    };
    ws.onclose = function (e) {
      if (net.ws !== ws) return;
      net.ws = null; net.connected = false;
      if (!net.on) return;
      // A code someone else is using: a new room gets a new code.
      if (e.code === 4009 && net.host && !net.joined) { net.code = newCode(); return connect(); }
      if (e.code === 4004) forgetAway(net.code); // the room is gone
      if (e.code >= 4000 && e.code < 4100) return leave(e.reason || 'Yhteys katkesi.');
      if (!net.joined && ++net.tries >= 3) return leave('Ei yhteyttä. Kokeile hetken päästä uudelleen.');
      net.timer = setTimeout(connect, Math.min(4000, 700 * (net.tries + 1)));
      update();
    };
    render();
  }
  function newCode() { var c = ''; for (var i = 0; i < 4; i++) c += LETTERS[Math.floor(Math.random() * LETTERS.length)]; return c; }

  function enter(code, host, pub) {
    clearTimeout(net.timer);
    choosing = false;
    net.on = true; net.host = host; net.code = code; net.joined = false; net.tries = 0; net.pub = !!(host && pub); listed = null;
    net.hostId = host ? net.me : ''; net.members = []; net.online = {}; net.wait = false; net.error = '';
    net.round = null; net.released = {}; net.owed = {}; net.got = {}; net.pz = []; net.played = false;
    net.result = ''; net.resultClass = ''; net.note = ''; lastPz = ''; net.rejoin = false;
    voiceReset();
    show(true);
    connect();
  }

  // Leaves the room. With a reason (the room closed, a refused join) the room screen stays open on
  // its first page with the reason; without one (the player left) the game gets its screen back.
  function leave(why) {
    if (!net.on) return;
    var ws = net.ws;
    if (net.host) sendRaw({ t: '_close' });
    // A guest leaving a game played in turns mid-round keeps its seat (no bye): the room stays
    // full for a newcomer, so "Palaa kierrokseen" always gets back in (#297).
    if (net.host || !needs || !racing()) sendRaw({ t: 'bye' });
    net.on = false; net.ws = null; net.connected = false; clearTimeout(net.timer);
    if (ws) try { ws.close(1000, 'Poistui'); } catch (e) { /* gone */ }
    ssave(HERE, null);
    net.round = null; net.pz = [];
    voiceReset();
    update();
    fire('leave', why || '');
    if (why) { net.error = why; show(true); } else { show(false); fire('menu'); }
  }

  function onMessage(m) {
    // Every new connection: the room says who this phone is, and a guest says hello to the host,
    // which sends the round back if this phone is in it (after a reload or a dropped connection).
    // Until the host answers, a guest does not know whether it is in the round, so it hears none
    // of the game's messages: a phone that is not in the round never sees the round's messages.
    if (m.t === '_rtc') return onRtc(m);
    if (m.t === 'you') { net.me = m.id; voiceAgain(); if (net.host) net.hostId = m.id; else { net.listening = false; sendRaw({ t: 'hello' }); } return; }
    if (m.t === 'peers') return onPeers(m);
    if (net.host) {
      if (m.t === 'hello') return onHello(m.from);
      if (m.t === '_got') return onGot(m.from, m.n);
      if (m.t && m.t.charAt(0) !== '_') fire('message', m, m.from);
      return;
    }
    if (m.t === '_start') return onStart(m);
    if (m.t === '_lobby') {
      forgetAway(net.code);
      net.wait = false; net.listening = false;
      if (net.round) { net.round = null; net.pz = []; net.result = ''; fire('lobby'); show(true); }
      return render();
    }
    if (m.t === '_wait') { forgetAway(net.code); net.wait = true; net.listening = false; return render(); }
    if (m.t === '_pz') { net.pz = Array.isArray(m.names) ? m.names : []; return update(); }
    if (m.t === '_close') { forgetAway(net.code); return leave('Huone suljettiin.'); }
    if (!net.listening || !m.t || m.t.charAt(0) === '_') return;
    // A delivered message (deliver()): confirm it, and pass it on only the first time.
    if (m._d) {
      var key = m._r + ':' + m._d, first = !net.got[key];
      net.got[key] = true;
      sendRaw({ t: '_got', n: m._d });
      if (!first) return;
      m = Object.assign({}, m);
      delete m._d; delete m._r; delete m.to;
      // Back through "Palaa kierrokseen" after the round ended: its end shows in the game, not
      // behind the room screen (the game goes back to the room after it, with backToRoom()).
      if (net.rejoin && net.round && net.round.over && String(key.split(':')[0]) === net.round.id) { net.rejoin = false; show(false); }
    }
    fire('message', m, net.hostId);
  }

  var moving = false; // this page is on its way to the room's own game or version
  function moveRoom(game, v) {
    if (moving || !/^[a-z0-9-]{1,40}$/.test(game) || !Number.isInteger(Number(v))) return;
    var to = new URL('../../' + game + '/v' + v + '/?huone=' + net.code, location.href);
    moving = true;
    // No bye: this same player remains a member while changing pages and rejoins
    // with the same secret identity. A bye would delete the room if the host was alone.
    var ws = net.ws;
    net.on = false; net.ws = null; net.connected = false;
    clearTimeout(net.timer);
    if (ws) try { ws.close(1000, 'Vaihdetaan peliä'); } catch (e) {}
    ssave(HERE, null);
    voiceReset();
    // The existing shelf handoff keeps back going to the new game's own page.
    var up = history.state && history.state.aiPelitUp;
    try {
      if (up && game === GAME) sessionStorage.setItem('ai-pelit:_ylos', to.pathname);
      if (up && game !== GAME) {
        sessionStorage.setItem('ai-pelit:_avaa', JSON.stringify({ from: '#/' + GAME, page: '#/' + game, game: to.href }));
        history.back();
        return;
      }
    } catch (e) {}
    location.replace(to.href);
  }
  function switchGame(game) {
    if (!net.host || !net.on || !net.connected || racing() || !shown || !game ||
        !game.room || game.room.max < net.members.length) return;
    var v = game.versions && game.versions[game.versions.length - 1];
    if (!v || (game.slug === GAME && v.n === VERSION)) return;
    ssave(ISANTA, { code: net.code, at: Date.now(), pub: net.pub });
    moveRoom(game.slug, v.n);
  }
  function onPeers(m) {
    // A second peers message before the page has gone must not step back twice (#68).
    if (moving) return;
    net.members = Array.isArray(m.members) ? m.members : [];
    net.hostId = m.host;
    net.online = {};
    net.members.forEach(function (x) { if (x.on) net.online[x.id] = true; });
    if (!net.joined) {
      // A room that does not say its game was made by a game from before this file (Kirkkis v2),
      // whose messages this game does not speak: leave it, and say why.
      if (!net.host && (!m.game || !m.v)) return leave('Huone on toisessa pelissä.');
      // A room made in an older version of this game: only the newest is kept (#346), so its
      // address would bring this phone straight back here. The host's phone has an old copy.
      if (!net.host && m.game === GAME && Number(m.v) < Number(VERSION)) {
        return leave('Huone on pelin vanhemmassa versiossa. Pyydä huoneen tekijää avaamaan peli hyllyltä uudelleen.');
      }
      net.joined = true;
      keepHere();
      // A host that comes back without its round (a reload) sends everyone back to the room. Only
      // then: after an ordinary round each phone goes back on its own, keeping its result.
      if (net.host && !net.round) sendRaw({ t: '_lobby' });
    }
    // A host can change games after everyone has joined. Move guests already in
    // the room as well as newcomers; all keep their member identity (#354).
    if (!net.host && m.game && m.v && (m.game !== GAME || Number(m.v) !== VERSION)) {
      return moveRoom(m.game, m.v);
    }
    if (net.host) {
      // Someone who left the room for good is the computer's from now on (in a game played in
      // turns, it keeps its player and may come back).
      if (racing() && !needs) {
        var gone = net.round.players.filter(function (p) {
          return p.id !== net.me && !net.released[p.id] && !net.members.some(function (x) { return x.id === p.id; });
        }).map(function (p) { return p.id; });
        if (gone.length) { gone.forEach(function (id) { net.released[id] = true; }); fire('continue', gone); }
      }
    } else if (!net.members.some(function (x) { return x.id === net.hostId; })) {
      forgetAway(net.code);
      return leave('Huone suljettiin.');
    }
    fire('peers', net.members.slice());
    update();
  }

  // ---- On the host ----
  // A phone connected (again): one in the round gets the round as it is, and anything delivered
  // to it that it has not confirmed; one that is not waits for the next round. A round always
  // reaches it before its messages, so a reloaded page knows the round before it hears how it
  // ended. Earlier rounds first, so the phone ends up in the latest one.
  function onHello(id) {
    var owed = net.owed[id] || [], started = {}, cur = net.round && net.round.id;
    sendRaw({ t: '_pz', to: id, names: waitingFor() });
    if (!net.round) { sendRaw({ t: '_lobby', to: id }); return; }
    function resend(o) {
      if (!started[o.round]) {
        started[o.round] = true;
        sendRaw({ t: '_start', to: id, round: o.round, players: o.players, over: true });
      }
      sendRaw(Object.assign({}, o.msg, { to: id, _d: o.n, _r: o.round }));
    }
    owed.filter(function (o) { return o.round !== cur; }).forEach(resend);
    var mine = inRound(id);
    if (mine) {
      if (net.released[id]) { delete net.released[id]; fire('back', id); }
      sendRaw({ t: '_start', to: id, round: cur, players: net.round.players, over: net.round.over });
      started[cur] = true;
    }
    owed.filter(function (o) { return o.round === cur; }).forEach(resend);
    if (mine) fire('hello', id);
    else if (racing()) sendRaw({ t: '_wait', to: id });
    update();
  }
  // A phone confirmed a delivered message: it is not sent again.
  function onGot(id, n) {
    if (!net.owed[id]) return;
    net.owed[id] = net.owed[id].filter(function (o) { return o.n !== n; });
    if (!net.owed[id].length) delete net.owed[id];
  }

  function keepHere() { ssave(HERE, { game: GAME, v: VERSION, code: net.code, host: net.host, pub: net.pub }); }

  // A public room is on the list while it waits in the room between rounds, its screen showing
  // on the host, not while the game's own end screen is up (the room adds: with space, and the
  // host connected). The host says so when that changes, and every minute while listed, which
  // keeps it there.
  var listed = null, listedAt = 0;
  function tellList() {
    if (!net.on || !net.host || !net.joined || !net.connected) return;
    var want = net.pub && !racing() && shown;
    if (want === listed && (!want || Date.now() - listedAt < 60e3)) return;
    listed = want; listedAt = Date.now();
    sendRaw({ t: '_list', on: want });
  }

  function startRound() {
    if (!net.host || !net.connected) return;
    var players = net.members.filter(function (m) { return m.on; }).slice(0, MAX)
      .map(function (m) { return { id: m.id, name: m.name }; });
    if (players.length < MIN) return;
    choosing = false;
    net.round = { id: hex(5), players: players, over: false };
    net.released = {}; net.pz = []; net.played = true; net.result = '';
    sendRaw({ t: '_start', round: net.round.id, players: players, over: false });
    show(false);
    fire('start', { round: net.round.id, players: players.slice(), host: true, over: false });
    update();
  }

  // ---- On a guest ----
  function onStart(m) {
    if (!Array.isArray(m.players)) return;
    if (!m.players.some(function (p) { return p.id === net.me; })) {
      // A round without this phone (it joined too late): it waits for the next one.
      if (!m.over) { net.wait = true; net.listening = false; render(); }
      return;
    }
    net.listening = true;
    var same = net.round && net.round.id === m.round;
    net.round = { id: String(m.round), players: m.players, over: !!m.over };
    net.wait = false;
    if (m.over) forgetAway(net.code); else { keepAway(); net.rejoin = false; }
    if (same) return update();
    net.played = true;
    if (!m.over) { net.result = ''; show(false); }
    fire('start', { round: net.round.id, players: m.players.slice(), host: false, over: !!m.over });
    update();
  }

  // ---- The pause ----
  // The host waits for the phones in the round that are away (unless it let the computer take
  // them); a guest waits for the host, and for the phones the host says it waits for.
  var lastPz = '';
  function waitingFor() {
    if (!net.on || !racing()) return [];
    if (!net.host) return net.pz.slice();
    return net.round.players.filter(function (p) { return p.id !== net.me && !net.online[p.id] && !net.released[p.id] && needed(p.id); })
      .map(function (p) { return p.name; });
  }
  function isPaused() {
    if (!net.on || !racing()) return false;
    return !net.connected || (!net.host && !hostOn()) || waitingFor().length > 0;
  }
  function update() {
    if (net.host && net.on) { tellPause(); tellList(); }
    voiceSync();
    render();
  }
  // The host tells the others whom the round waits for, when that changes. In a game played in
  // turns it changes with the turn too, so it is looked at every 250 ms as well.
  function tellPause() {
    var pz = JSON.stringify(waitingFor());
    if (pz !== lastPz) { lastPz = pz; sendRaw({ t: '_pz', names: JSON.parse(pz) }); }
  }
  function goOn() {
    if (!net.host || !racing()) return;
    var ids = net.round.players.filter(function (p) { return p.id !== net.me && !net.online[p.id] && !net.released[p.id] && needed(p.id); })
      .map(function (p) { return p.id; });
    // A game played in turns skips the turn; the player stays theirs.
    if (needs) { if (ids.length) fire('skip', ids); update(); return; }
    ids.forEach(function (id) { net.released[id] = true; });
    if (ids.length) fire('continue', ids);
    update();
  }


  // ---- Voice (#322) ----
  var VOICE_KEY = 'ai-pelit:_huone:puhe'; // false: this phone has switched voice off
  var VOICE_AT = script.getAttribute('data-voice-corner') || 'right';
  var ICE = new URL('api/voice/ice', script.src);
  var STUN = [{ urls: 'stun:stun.cloudflare.com:3478' }];
  var RTC = script.getAttribute('data-voice') !== 'off' && !!(window.RTCPeerConnection && navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  var voice = {
    on: RTC && load(VOICE_KEY, true) !== false,
    sid: hex(6), // this page's own: a phone that reloaded is called again
    peers: {}, // id -> {greet, on, sid, pc, early, audio, talking, talkAt, fails, retryAt}
    muted: {}, // id -> true: not heard on this phone, while in this room
    stream: null, track: null, pressed: false, talking: false, ice: null, iceAt: 0, err: '', errAt: 0,
  };
  var STUCK = 20e3;
  function vpeer(id) { return voice.peers[id] || (voice.peers[id] = { early: [], fails: 0, retryAt: 0 }); }
  function sendRtc(to, m) { m.t = '_rtc'; m.to = to; sendRaw(m); }
  // Says to a phone whether this one takes calls; r asks it to say the same back.
  function greet(id, r) { sendRtc(id, { k: 'hi', on: voice.on, sid: voice.sid, r: r }); }
  function others() { return net.members.filter(function (m) { return m.on && m.id !== net.me; }); }
  function sender(pc) { var t = pc.getTransceivers()[0]; return t ? t.sender : null; }
  function eachPc(fn) { Object.keys(voice.peers).forEach(function (id) { var p = voice.peers[id]; if (p.pc) try { fn(p.pc, id, p); } catch (e) {} }); }
  function live(p) { return !!(p.pc && p.pc.connectionState === 'connected'); }

  function getIce() {
    if (voice.ice && Date.now() - voice.iceAt < 1800e3) return Promise.resolve(voice.ice); // the site's last 2 h
    return fetch(ICE, { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      voice.ice = d && Array.isArray(d.iceServers) ? d.iceServers : STUN;
      voice.iceAt = Date.now();
      return voice.ice;
    }).catch(function () { return STUN; });
  }

  // After this phone's own connection came back: everyone is greeted again.
  function voiceAgain() { Object.keys(voice.peers).forEach(function (id) { voice.peers[id].greet = false; }); }
  function voiceReset() {
    release();
    Object.keys(voice.peers).forEach(function (id) { hang(id); });
    voice.peers = {}; voice.muted = {};
    renderVoice();
  }

  // Greets the phones that came (back), hangs up on those that left the room, and calls those this
  // phone should call: the one with the smaller id calls, when both take calls.
  function voiceSync() {
    if (!RTC || !net.on || !net.me || !net.connected) return renderVoice();
    var here = {};
    net.members.forEach(function (m) { if (m.id !== net.me) here[m.id] = m.on; });
    Object.keys(voice.peers).forEach(function (id) {
      if (!(id in here)) { hang(id); delete voice.peers[id]; }
      else if (!here[id]) voice.peers[id].greet = false; // greeted again once back
    });
    others().forEach(function (m) {
      var p = vpeer(m.id);
      // Greeted when it comes (back), and again while no call is up with it: a lost message or a
      // call made in the middle of a reconnect heals by itself.
      var nocall = voice.on && !live(p) && !p.dialing;
      if (!p.greet || (nocall && Date.now() - (p.greetAt || 0) > 10e3)) { p.greet = true; p.greetAt = Date.now(); greet(m.id, true); }
      var pc = p.pc, broken = !pc || pc.sid !== p.sid || pc.connectionState === 'failed' || pc.connectionState === 'closed';
      // A call not up within 20 s is made again (#333): its offer or answer may have been lost
      // while a phone was away, and then neither phone ever hears of it failing.
      if (pc && live(p)) pc.upAt = Date.now();
      else if (pc && !broken && net.me < m.id && Date.now() - pc.upAt > STUCK) {
        hang(m.id);
        p.retryAt = Date.now() + Math.min(30e3, 1000 * Math.pow(2, p.fails++));
        broken = true;
      }
      if (voice.on && p.on && net.me < m.id && broken && !p.dialing && Date.now() >= p.retryAt) dial(m.id);
    });
    renderVoice();
  }

  function newPc(id, p, c, servers) {
    var pc = new RTCPeerConnection({ iceServers: servers });
    pc.c = c; pc.upAt = Date.now();
    p.pc = pc;
    pc.onicecandidate = function (e) { if (e.candidate && p.pc === pc) sendRtc(id, { k: 'ice', c: c, ice: e.candidate.toJSON() }); };
    pc.ontrack = function (e) { if (p.pc === pc) hear(id, p, e.streams && e.streams[0] || new MediaStream([e.track])); };
    pc.onconnectionstatechange = function () {
      if (p.pc !== pc) return;
      if (pc.connectionState === 'connected') p.fails = 0;
      if (pc.connectionState === 'failed') {
        // Try again later, waiting longer each time (a network that lets no call through).
        hang(id);
        p.retryAt = Date.now() + Math.min(30e3, 1000 * Math.pow(2, p.fails++));
        setTimeout(voiceSync, Math.min(30e3, 1000 * Math.pow(2, p.fails - 1)) + 50);
      }
      renderVoice();
    };
    return pc;
  }
  function flushIce(p, pc) {
    var early = p.early; p.early = [];
    early.forEach(function (e) { if (e.c === pc.c) pc.addIceCandidate(e.ice).catch(function () {}); });
  }
  function dial(id) {
    var p = vpeer(id);
    p.dialing = true;
    getIce().then(function (servers) {
      p.dialing = false;
      if (!voice.on || !net.on || !p.on || voice.peers[id] !== p) return; // it left meanwhile
      hang(id);
      var pc = newPc(id, p, hex(4), servers);
      pc.sid = p.sid;
      pc.addTransceiver(voice.talking && voice.track ? voice.track : 'audio', { direction: 'sendrecv' });
      pc.createOffer().then(function (o) { return pc.setLocalDescription(o); }).then(function () {
        if (p.pc === pc) sendRtc(id, { k: 'offer', c: pc.c, sdp: pc.localDescription.sdp });
      }).catch(function () { if (p.pc === pc) hang(id); });
    });
  }
  function pickUp(id, m) {
    var p = vpeer(id);
    if (!voice.on || typeof m.sdp !== 'string' || (p.pc && p.pc.c === m.c)) return;
    getIce().then(function (servers) {
      if (!voice.on || !net.on || voice.peers[id] !== p) return;
      // Candidates for this offer that came while the servers were read wait through the reset,
      // and are added once the offer is in (flushIce()).
      var early = p.early.filter(function (e) { return e.c === m.c; });
      hang(id);
      p.early = early;
      var pc = newPc(id, p, m.c, servers);
      pc.setRemoteDescription({ type: 'offer', sdp: m.sdp }).then(function () {
        var t = pc.getTransceivers()[0];
        if (t) { t.direction = 'sendrecv'; if (voice.talking && voice.track) t.sender.replaceTrack(voice.track); }
        flushIce(p, pc);
        return pc.createAnswer();
      }).then(function (a) { return pc.setLocalDescription(a); }).then(function () {
        if (p.pc === pc) sendRtc(id, { k: 'answer', c: pc.c, sdp: pc.localDescription.sdp });
      }).catch(function () { if (p.pc === pc) hang(id); });
    });
  }
  function hang(id) {
    var p = voice.peers[id];
    if (!p) return;
    if (p.pc) { try { p.pc.close(); } catch (e) {} p.pc = null; }
    if (p.audio) { p.audio.srcObject = null; p.audio.remove(); p.audio = null; }
    p.talking = false; p.early = [];
  }

  function onRtc(m) {
    // A room from before voice passes the host's messages on without `from`: on a guest, a message
    // that names no sender is the host's.
    var id = m.from || (net.host ? '' : net.hostId);
    if (!RTC || !net.on || typeof id !== 'string' || id === net.me) return;
    var p = vpeer(id);
    if (m.k === 'hi') {
      var was = p.on;
      p.on = m.on === true; p.sid = String(m.sid || '');
      if (m.r) greet(id, false);
      if (!p.on && was) hang(id);
      voiceSync();
      return render(); // the mute button beside the name

    }
    if (m.k === 'offer') return pickUp(id, m);
    if (m.k === 'answer') {
      var pc = p.pc;
      if (pc && pc.c === m.c && pc.signalingState === 'have-local-offer' && typeof m.sdp === 'string')
        pc.setRemoteDescription({ type: 'answer', sdp: m.sdp }).then(function () { flushIce(p, pc); }).catch(function () {});
      return;
    }
    if (m.k === 'ice' && m.ice) {
      if (p.pc && p.pc.c === m.c && p.pc.remoteDescription) p.pc.addIceCandidate(m.ice).catch(function () {});
      else if (p.early.length < 60) p.early.push({ c: m.c, ice: m.ice });
      return;
    }
    if (m.k === 'talk') { p.talking = m.on === true; p.talkAt = Date.now(); renderVoice(); }
  }

  // Another phone's sound: its own hidden player, silent while muted here.
  function hear(id, p, stream) {
    if (!p.audio) {
      p.audio = document.createElement('audio');
      p.audio.autoplay = true; p.audio.setAttribute('playsinline', '');
      p.audio.style.display = 'none';
      document.body.appendChild(p.audio);
    }
    p.audio.srcObject = stream;
    p.audio.muted = !!voice.muted[id];
    p.audio.play().catch(function () {});
  }
  // A phone may block sound that starts by itself: the next tap anywhere starts it. Coming back
  // from another app, Android has paused it: it starts again.
  function replay() {
    Object.keys(voice.peers).forEach(function (id) { var a = voice.peers[id].audio; if (a && a.paused) a.play().catch(function () {}); });
  }
  document.addEventListener('pointerdown', replay, true);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) replay(); });

  // ---- Push to talk ----
  function press() {
    if (voice.pressed || !voice.on || !net.on) return;
    // Nobody to hear it yet: the microphone stays off (and is not even asked for).
    if (!Object.keys(voice.peers).some(function (id) { return live(voice.peers[id]); })) {
      voice.err = 'Kukaan ei kuule vielä.'; voice.errAt = Date.now();
      return renderVoice();
    }
    voice.pressed = true; voice.pressAt = Date.now(); voice.err = ''; voice.errAt = 0;
    renderVoice();
    navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } }).then(function (s) {
      if (voice.stream) voice.stream.getTracks().forEach(function (t) { t.stop(); });
      voice.stream = s; voice.track = s.getAudioTracks()[0] || null;
      if (!voice.pressed || !voice.track) return dropMic();
      voice.talking = true;
      eachPc(function (pc) { var sn = sender(pc); if (sn) sn.replaceTrack(voice.track); });
      tellTalk(true);
      renderVoice();
    }).catch(function () {
      voice.pressed = false;
      voice.err = 'Mikrofoni ei ole sallittu.'; voice.errAt = Date.now();
      renderVoice();
    });
  }
  function release() {
    if (!voice.pressed) return;
    voice.pressed = false;
    // A quick tap: say how the chip works.
    if (Date.now() - voice.pressAt < 400 && Date.now() - voice.errAt > 3000) { voice.err = 'Pidä pohjassa ja puhu.'; voice.errAt = Date.now(); }
    if (voice.talking) { voice.talking = false; tellTalk(false); }
    dropMic();
    renderVoice();
  }
  // The microphone is stopped between presses, so the phone's microphone light goes off.
  function dropMic() {
    eachPc(function (pc) { var sn = sender(pc); if (sn) sn.replaceTrack(null); });
    if (voice.stream) voice.stream.getTracks().forEach(function (t) { t.stop(); });
    voice.stream = null; voice.track = null;
  }
  function tellTalk(on) { eachPc(function (pc, id) { sendRtc(id, { k: 'talk', on: on }); }); }
  document.addEventListener('visibilitychange', function () { if (document.hidden) release(); });

  function setVoice(on) {
    if (!RTC || on === voice.on) return;
    voice.on = on;
    save(VOICE_KEY, on);
    if (!on) { release(); Object.keys(voice.peers).forEach(function (id) { hang(id); }); }
    if (net.on && net.connected) others().forEach(function (m) { greet(m.id, false); });
    voiceSync();
    render();
  }
  function toggleMute(id) {
    if (voice.muted[id]) delete voice.muted[id]; else voice.muted[id] = true;
    var p = voice.peers[id];
    if (p && p.audio) p.audio.muted = !!voice.muted[id];
    render();
  }
  function speakers() {
    return net.members.filter(function (m) {
      var p = voice.peers[m.id];
      return p && p.talking && live(p) && !voice.muted[m.id] && Date.now() - p.talkAt < 60e3;
    }).map(function (m) { return m.name; });
  }

  // The chip and, beside it, who is talking.
  var vel = null, vShown = '';
  function voiceUI() {
    if (vel) return;
    build();
    var side = /left/.test(VOICE_AT) ? 'left' : 'right';
    var vert = /^top/.test(VOICE_AT) ? 'top' : /^bottom/.test(VOICE_AT) ? 'bottom' : 'mid';
    var chip = document.createElement('button'), bubble = document.createElement('div');
    chip.id = 'aipr-mic'; chip.type = 'button'; chip.textContent = '🎤'; chip.hidden = true;
    chip.setAttribute('aria-label', 'Pidä pohjassa ja puhu');
    bubble.id = 'aipr-talk'; bubble.hidden = true;
    var edge = 'calc(env(safe-area-inset-' + side + ',0px) + 8px)';
    chip.style[side] = edge;
    bubble.style[side] = 'calc(env(safe-area-inset-' + side + ',0px) + 68px)';
    if (vert === 'mid') { chip.style.top = '38%'; bubble.style.top = 'calc(38% + 12px)'; }
    if (vert === 'top') { chip.style.top = 'calc(env(safe-area-inset-top,0px) + 56px)'; bubble.style.top = 'calc(env(safe-area-inset-top,0px) + 68px)'; }
    if (vert === 'bottom') { chip.style.bottom = 'calc(env(safe-area-inset-bottom,0px) + 72px)'; bubble.style.bottom = 'calc(env(safe-area-inset-bottom,0px) + 84px)'; }
    document.body.appendChild(chip);
    document.body.appendChild(bubble);
    shield(chip);
    chip.addEventListener('pointerdown', function (e) {
      e.preventDefault();
      try { chip.setPointerCapture(e.pointerId); } catch (err) {}
      press();
    });
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function (type) { chip.addEventListener(type, release); });
    chip.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    vel = { chip: chip, bubble: bubble };
  }
  function renderVoice() {
    if (!RTC) return;
    var on = net.on && voice.on;
    if (!on && !vel) return;
    voiceUI();
    var calls = Object.keys(voice.peers).some(function (id) { return live(voice.peers[id]); });
    var cls = voice.talking ? 'live' : voice.pressed ? 'wait' : calls ? '' : 'none';
    var text = voice.err && Date.now() - voice.errAt < 3000 ? voice.err : '';
    if (!text && on) {
      var who = speakers();
      // The phone held the sound back (no tap on this page yet): a tap anywhere lets it play.
      // The hint goes on its own line, so a narrow phone shows it whole (#333).
      var held = Object.keys(voice.peers).some(function (id) { var a = voice.peers[id].audio; return a && a.paused && voice.peers[id].talking; });
      if (who.length) text = '🔊 ' + who.join(', ') + (held ? '\nNapauta ruutua' : '');
    }
    var k = on + cls + text;
    if (k === vShown) return;
    vShown = k;
    vel.chip.hidden = !on;
    var mid = /^(right|left)$/.test(VOICE_AT) ? 'mid' : '';
    vel.chip.className = cls + (mid ? ' ' + mid : '');
    vel.bubble.className = mid;
    vel.bubble.hidden = !text;
    vel.bubble.textContent = text;
  }

  // ---- The screen ----
  var root = null, el = {};
  var catalogGames = null, loadingGames = false, choosing = false;
  function readGames() {
    if (!shown || !net.host || !net.on || catalogGames || loadingGames || !window.fetch) return;
    loadingGames = true;
    fetch(new URL('catalog.json', script.src), { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { catalogGames = d && Array.isArray(d.games) ? d.games : []; })
      .catch(function () { catalogGames = []; })
      .then(function () { loadingGames = false; render(); });
  }
  function eligibleGames() {
    return (catalogGames || []).filter(function (g) {
      return g.room && g.room.max >= net.members.length && g.versions && g.versions.length;
    });
  }
  function renderGames() {
    el.games.hidden = !choosing || !net.host || racing();
    if (el.games.hidden) return;
    el.gameList.textContent = '';
    eligibleGames().forEach(function (g) {
      var v = g.versions[g.versions.length - 1], current = g.slug === GAME && v.n === VERSION;
      var b = document.createElement('button');
      b.type = 'button';
      b.disabled = current;
      b.textContent = g.title + (current ? ' (nyt)' : '');
      b.addEventListener('click', function () { switchGame(g); });
      el.gameList.appendChild(b);
    });
  }
  var CSS = [
    '#aipr{position:fixed;inset:0;z-index:2147483640;display:flex;flex-direction:column;align-items:center;justify-content:safe center;gap:6px;padding:calc(env(safe-area-inset-top,0px) + 40px) 22px calc(env(safe-area-inset-bottom,0px) + 18px);box-sizing:border-box;background:#f6f1e6;color:#2b2416;font:16px/1.35 system-ui,sans-serif;text-align:center;touch-action:manipulation;overflow-y:auto}',
    '#aipr[hidden],#aipr [hidden],#aipr-pause[hidden]{display:none!important}',
    '#aipr h2{margin:0;font-size:24px;color:#6b3a86}',
    '#aipr .v{display:flex;flex-direction:column;align-items:center;gap:8px}',
    '#aipr label{font-size:14px;font-weight:700;color:#6a5638;display:flex;flex-direction:column;gap:4px;align-items:center}',
    '#aipr input{font:800 20px system-ui,sans-serif;padding:8px 10px;border:2px solid #c9b48a;border-radius:12px;width:200px;text-align:center;background:#fff;color:#2b2416;box-sizing:border-box}',
    '#aipr-codeIn{width:110px!important;letter-spacing:4px;text-transform:uppercase}',
    '#aipr .row{display:flex;gap:10px;align-items:center}',
    '#aipr .row .small{max-width:160px}',
    '#aipr button{font:800 18px system-ui,sans-serif;padding:11px 18px;border:0;border-radius:14px;color:#fff;background:#4f9a3a;box-shadow:0 4px 0 #2f6a22}',
    '#aipr button:active{transform:translateY(3px);box-shadow:none}',
    '#aipr button:disabled{background:#b8ad95;box-shadow:none}',
    '#aipr button.plain{background:none;box-shadow:none;color:#7d6a4c;font-size:15px;text-decoration:underline;padding:6px}',
    '#aipr .small{margin:0;font-size:13px;color:#8a7658}',
    '#aipr-code{margin:0 0 4px;font:900 40px/1.1 system-ui,sans-serif;letter-spacing:6px}',
    '#aipr canvas{width:124px;height:124px;flex:none;image-rendering:pixelated;background:#fff;border-radius:8px}',
    '#aipr ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:3px;min-width:220px}',
    '#aipr li{display:flex;align-items:center;gap:8px;font-size:16px;font-weight:700;background:rgba(255,255,255,.75);border-radius:10px;padding:3px 10px}',
    '#aipr li.off{opacity:.5}',
    '#aipr li i{width:14px;height:14px;border-radius:50%;display:inline-block;flex:none}',
    '#aipr-result{margin:0;font-size:20px;font-weight:800}',
    '#aipr-result:empty,#aipr-err:empty{display:none}',
    '#aipr-result.win{color:#3f8a3a}#aipr-result.lose{color:#c4432f}',
    '#aipr-info,#aipr-err{margin:0;font-size:14px;font-weight:600;color:#6a5638;max-width:300px}',
    '#aipr-err{color:#c4432f}',
    '#aipr-open{gap:6px;margin-top:6px}',
    '#aipr-rooms{display:flex;flex-direction:column;gap:6px}',
    '#aipr-rooms button{font-size:16px;padding:8px 16px;background:#3f8ad8;box-shadow:0 4px 0 #2a5f99}',
    '#aipr #aipr-again{background:#3f8ad8;box-shadow:0 4px 0 #2a5f99;margin-bottom:6px}',
    '#aipr label.sw{flex-direction:row;gap:8px;font-size:15px;color:#2b2416}',
    '#aipr .sws{display:flex;flex-wrap:wrap;justify-content:center;gap:4px 16px}',
    '#aipr input[type=checkbox]{width:22px;height:22px;padding:0;margin:0;accent-color:#3f8ad8}',
    // A phone on its side (#95): the room in two columns, the code and QR left and everything to
    // tap right, so "Aloita kierros" shows without scrolling even with a full room.
    '@media (orientation:landscape) and (max-height:500px){' +
      '#aipr{gap:4px;padding:calc(env(safe-area-inset-top,0px) + 8px) calc(env(safe-area-inset-right,0px) + 16px) calc(env(safe-area-inset-bottom,0px) + 6px) calc(env(safe-area-inset-left,0px) + 16px)}' +
      '#aipr h2{font-size:20px}' +
      '#aipr-room:not([hidden]){display:grid;grid-template-columns:auto auto;column-gap:28px;row-gap:0;align-items:center;justify-items:center}' +
      '#aipr-room>*{grid-column:2;margin-top:6px}' +
      '#aipr-room>.row{grid-column:1;grid-row:1/span 7;flex-direction:column;gap:2px;margin:0}' +
      '#aipr-room>.row .small{max-width:180px}' +
      '#aipr canvas{width:96px;height:96px}' +
      '#aipr-code{font-size:32px;margin:0}' +
      '#aipr ul{display:grid;grid-template-columns:repeat(2,minmax(150px,1fr));gap:3px 6px}' +
      '#aipr li{font-size:15px;padding:2px 8px}' +
      '#aipr button.plain{padding:2px 6px}' +
    '}',
    '#aipr-mic{position:fixed;z-index:2147483642;width:52px;height:52px;padding:0;border:0;border-radius:50%;background:rgba(40,30,50,.75);color:#fff;font-size:24px;line-height:52px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.35);touch-action:none;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;-webkit-tap-highlight-color:transparent}',
    '#aipr-mic[hidden],#aipr-talk[hidden]{display:none}',
    '#aipr-mic.none{opacity:.45}',
    '#aipr-mic.wait{background:#e0a526}',
    '#aipr-mic.live{background:#d33b2c;transform:scale(1.15)}',
    '#aipr-talk{position:fixed;z-index:2147483642;max-width:60vw;white-space:pre-line;overflow-wrap:anywhere;padding:5px 12px;border-radius:14px;background:rgba(40,30,50,.85);color:#fff;font:700 15px/1.3 system-ui,sans-serif;pointer-events:none}',
    // On its side the athletics events' action buttons fill both edges: the chip goes to the top
    // bar instead, right of the middle, where the games' scores are not.
    '@media (orientation:landscape) and (max-height:500px){' +
      '#aipr-mic.mid{top:calc(env(safe-area-inset-top,0px) + 4px)!important;left:calc(50% + 120px)!important;right:auto!important;width:44px;height:44px;line-height:44px;font-size:20px}' +
      '#aipr-talk.mid{top:calc(env(safe-area-inset-top,0px) + 54px)!important;left:auto!important;right:calc(50% - 164px)!important}' +
    '}',
    '#aipr li button.mute{margin-left:auto;padding:0 2px;background:none;box-shadow:none;font-size:18px;line-height:1}',
    // Friends (#324): a small button on each player's row, the requests above the list, and the
    // invite list over the whole room screen.
    '#aipr li .fr{margin-left:auto;font:800 13px system-ui,sans-serif;padding:4px 9px;border-radius:9px;background:#3f8ad8;box-shadow:0 2px 0 #2a5f99;white-space:nowrap}',
    '#aipr li .fr.ok{background:#4f9a3a;box-shadow:0 2px 0 #2f6a22}',
    '#aipr li .fr+button.mute,#aipr li .frs+button.mute{margin-left:6px}',
    '#aipr li .frs{margin-left:auto;font-size:13px;font-weight:700;color:#8a7658;white-space:nowrap}',
    '#aipr-friends{display:flex;flex-direction:column;align-items:center;gap:6px}',
    '#aipr-friends:empty{display:none}',
    '#aipr .ask{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:center;background:#e8def5;border-radius:12px;padding:6px 10px;font-size:15px;font-weight:700;max-width:320px}',
    '#aipr .ask .who{flex:1 1 auto;text-align:left;min-width:0}',
    '#aipr .ask button{font-size:14px;padding:6px 10px;box-shadow:0 3px 0 #2f6a22}',
    '#aipr-friends>button{font-size:15px;padding:7px 12px}',
    '#aipr .ask button.no{background:#b8ad95;box-shadow:0 3px 0 #8a8270}',
    '#aipr-friends>button{background:#9a5cc6;box-shadow:0 4px 0 #6b3a86}',
    '#aipr-inv,#aipr-games{position:fixed;inset:0;z-index:2;display:flex;flex-direction:column;align-items:center;gap:8px;padding:calc(env(safe-area-inset-top,0px) + 40px) 18px calc(env(safe-area-inset-bottom,0px) + 14px);box-sizing:border-box;background:#f6f1e6;overflow-y:auto}',
    '#aipr-games button{width:min(320px,100%);font-size:16px;padding:9px 12px}',
    '#aipr-gameList{display:flex;flex-direction:column;gap:8px;width:min(320px,100%)}',
    '#aipr-inv ul{width:min(340px,100%)}',
    '#aipr-inv li{justify-content:space-between;text-align:left;padding:6px 10px}',
    '#aipr-inv li div{min-width:0}',
    '#aipr-inv li small{display:block;font-size:13px;font-weight:600;color:#8a7658}',
    '#aipr-inv li button{font-size:15px;padding:7px 12px;flex:none}',
    '#aipr-pause{position:fixed;left:16px;right:16px;top:40%;z-index:2147483641;display:flex;flex-direction:column;align-items:center;gap:10px;padding:16px;border-radius:16px;background:rgba(30,20,40,.88);color:#fff;text-align:center;font:700 17px/1.35 system-ui,sans-serif;touch-action:manipulation}',
    '#aipr-pause p{margin:0}',
    '#aipr-pause button{font:800 16px system-ui,sans-serif;padding:9px 16px;border:0;border-radius:12px;background:#f2c94c;color:#2b2416}',
  ].join('\n');
  var HTML =
    '<h2>👥 Kavereiden kanssa</h2>' +
    '<div class="v" id="aipr-join">' +
      '<label>Nimesi <input id="aipr-name" maxlength="16" autocomplete="off" enterkeyhint="done"></label>' +
      '<button id="aipr-again" hidden></button>' +
      '<button id="aipr-create">Luo huone</button>' +
      '<p class="small">tai liity kaverin huoneeseen koodilla</p>' +
      '<div class="row"><input id="aipr-codeIn" maxlength="4" placeholder="KOOD" autocapitalize="characters" autocomplete="off" enterkeyhint="go"><button id="aipr-joinBtn">Liity</button></div>' +
      '<div class="v" id="aipr-open" hidden><p class="small"><b>Avoimet huoneet</b></p><div id="aipr-rooms"></div>' +
        '<p class="small" id="aipr-none">Ei avoimia huoneita juuri nyt.</p></div>' +
    '</div>' +
    '<div class="v" id="aipr-room" hidden>' +
      '<p id="aipr-result"></p>' +
      '<div class="row"><canvas id="aipr-qr" width="300" height="300"></canvas>' +
        '<div><p class="small"><b>Huoneen koodi</b></p><p id="aipr-code"></p>' +
        '<p class="small">Kaverit liittyvät koodilla tai skannaamalla kuvan.</p></div></div>' +
      '<ul id="aipr-members"></ul>' +
      '<div id="aipr-friends"></div>' +
      '<p id="aipr-info"></p>' +
      '<div id="aipr-extra"></div>' +
      '<div class="sws"><label class="sw" id="aipr-pubRow" hidden><input type="checkbox" id="aipr-pub">🌍 Julkinen: kuka tahansa voi liittyä</label>' +
      '<label class="sw" id="aipr-voiceRow" hidden><input type="checkbox" id="aipr-voice">🎤 Puhe</label></div>' +
      '<button id="aipr-switchGame" hidden>🎲 Vaihda peliä</button>' +
      '<button id="aipr-start" hidden>Aloita kierros</button>' +
    '</div>' +
    '<p id="aipr-err"></p>' +
    '<button id="aipr-back" class="plain">Takaisin</button>' +
    '<div id="aipr-inv" hidden><h2>📨 Kutsu kaveri</h2><p class="small">Kutsu tulee kaverin puhelimeen, vaikka hän pelaisi toista peliä.</p>' +
      '<ul id="aipr-invList"></ul><p class="small" id="aipr-invNone"></p><button id="aipr-invClose">Valmis</button></div>' +
    '<div id="aipr-games" hidden><h2>🎲 Vaihda peliä</h2><p class="small">Huone ja kaverit pysyvät mukana. Valitse seuraava peli.</p>' +
      '<div id="aipr-gameList"></div><button id="aipr-gamesClose" class="plain">Takaisin</button></div>';

  // Like back.js: the game never sees a touch or a key meant for the room screen.
  function shield(e) {
    ['pointerdown', 'pointerup', 'pointermove', 'touchstart', 'touchend', 'touchmove', 'mousedown', 'mouseup', 'click', 'keydown', 'keyup']
      .forEach(function (type) { e.addEventListener(type, function (ev) { ev.stopPropagation(); }, { passive: true }); });
  }
  function build() {
    if (root) return;
    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);
    root = document.createElement('div');
    root.id = 'aipr'; root.hidden = true; root.innerHTML = HTML;
    var pause = document.createElement('div');
    pause.id = 'aipr-pause'; pause.hidden = true;
    pause.innerHTML = '<p id="aipr-pauseText"></p><button id="aipr-goOn" hidden>Jatka ilman heitä</button>';
    document.body.appendChild(root);
    document.body.appendChild(pause);
    shield(root); shield(pause);
    ['join', 'name', 'again', 'create', 'codeIn', 'joinBtn', 'open', 'rooms', 'none', 'pubRow', 'pub', 'voiceRow', 'voice', 'room', 'result', 'code', 'qr', 'members', 'friends', 'info', 'extra', 'start', 'switchGame', 'games', 'gameList', 'gamesClose', 'err', 'back', 'pauseText', 'goOn', 'inv', 'invList', 'invNone', 'invClose']
      .forEach(function (k) { el[k] = document.getElementById('aipr-' + k); });
    el.pause = pause;
    el.create.addEventListener('click', function () { takeName(); enter(newCode(), true); });
    el.joinBtn.addEventListener('click', joinTyped);
    el.again.addEventListener('click', function () { var a = awayRound(); if (a) { takeName(); enter(a.code, false); net.rejoin = true; } });
    el.codeIn.addEventListener('keydown', function (e) { if (e.key === 'Enter') joinTyped(); });
    el.start.addEventListener('click', startRound);
    el.switchGame.addEventListener('click', function () { choosing = true; render(); });
    el.gamesClose.addEventListener('click', function () { choosing = false; render(); });
    el.pub.addEventListener('change', function () { net.pub = el.pub.checked; if (net.joined) keepHere(); tellList(); render(); });
    el.back.addEventListener('click', function () { if (net.on) leave(); else { show(false); fire('menu'); } });
    el.goOn.addEventListener('click', goOn);
    el.voice.addEventListener('change', function () { setVoice(el.voice.checked); });
    el.invClose.addEventListener('click', function () { inviting = false; render(); });
  }
  function takeName() {
    var n = cleanName(el.name.value);
    if (n && n !== myName()) save(NAME, n);
    findFid();
  }
  function joinTyped() {
    takeName();
    var code = el.codeIn.value.trim().toUpperCase();
    if (!/^[A-Z]{4}$/.test(code)) { el.err.textContent = 'Koodissa on neljä kirjainta.'; return; }
    enter(code, false);
  }

  // The public rooms of this game, read while the first page of the room screen is open. Until
  // the first answer (or with no connection) the list is not shown at all.
  var openRooms = null, reading = false;
  function readList() {
    if (!shown || net.on || reading || !GAME || !window.fetch) return;
    reading = true;
    fetch(LIST, { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { reading = false; if (d && Array.isArray(d.rooms)) { openRooms = d.rooms; render(); } })
      .catch(function () { reading = false; });
  }
  function renderList() {
    el.open.hidden = !openRooms;
    if (!openRooms) return;
    el.rooms.textContent = '';
    openRooms.forEach(function (r) {
      if (!r || !/^[A-Z]{4}$/.test(r.code)) return;
      // A room on an older version would only say so when joined (#346): leave it off the list.
      if (Number(r.v) < VERSION) return;
      var b = document.createElement('button');
      b.textContent = r.code + ' · ' + r.n + '/' + r.max + ' pelaajaa';
      b.addEventListener('click', function () { takeName(); enter(r.code, false); });
      el.rooms.appendChild(b);
    });
    el.none.hidden = el.rooms.childNodes.length > 0;
  }

  var shown = false;
  function show(on) {
    build();
    shown = on;
    if (!on) { inviting = false; choosing = false; }
    root.hidden = !on;
    if (on) el.name.value = myName();
    render();
    readList();
    tellList();
  }
  function joinLink() { return location.origin + location.pathname + '?huone=' + net.code; }

  function render() {
    renderVoice();
    if (!root) return;
    hookFriends();
    renderPause();
    if (!shown) return;
    readGames();
    renderGames();
    el.join.hidden = net.on;
    el.room.hidden = !net.on;
    el.back.textContent = net.on ? 'Poistu huoneesta' : 'Takaisin';
    el.err.textContent = net.on ? '' : net.error;
    if (!net.on) { var a = awayRound(); el.again.hidden = !a; if (a) el.again.textContent = '↩ Palaa kierrokseen ' + a.code; return renderList(); }
    if (el.code.textContent !== net.code) { el.code.textContent = net.code; drawQR(el.qr, joinLink()); }
    el.result.textContent = net.result;
    el.result.className = net.resultClass || '';
    el.members.textContent = '';
    net.members.forEach(function (m, i) {
      var li = document.createElement('li'), dot = document.createElement('i');
      dot.style.background = COLORS[i % COLORS.length];
      li.appendChild(dot);
      li.appendChild(document.createTextNode((m.id === net.hostId ? '👑 ' : '') + m.name + (m.id === net.me ? ' (sinä)' : '') + (m.on ? '' : ' – ei yhteyttä')));
      if (!m.on) li.className = 'off';
      var fb = friendButton(m);
      if (fb) li.appendChild(fb);
      // A player whose voice this phone can hear: a tap mutes them here (#322).
      var vp = voice.peers[m.id];
      if (voice.on && vp && vp.on && m.id !== net.me) {
        var mute = document.createElement('button');
        mute.className = 'mute'; mute.type = 'button';
        mute.textContent = voice.muted[m.id] ? '🔇' : '🔊';
        mute.setAttribute('aria-label', voice.muted[m.id] ? 'Kuuntele' : 'Mykistä');
        mute.addEventListener('click', function () { toggleMute(m.id); });
        li.appendChild(mute);
      }
      el.members.appendChild(li);
    });
    renderFriends();
    var online = net.members.filter(function (m) { return m.on; }).length, info;
    if (!net.connected) info = 'Yhdistetään…';
    else if (net.host) {
      info = online < MIN ? 'Odotetaan kavereita…'
        : online < MAX ? online + ' pelaajaa.'
        : MAX + ' pelaajaa – huone on täynnä.';
    } else info = net.wait ? 'Kierros on käynnissä – pääset mukaan seuraavaan.' : 'Huoneen tekijä valitsee seuraavan pelin. Odotetaan, että ' + hostName() + ' aloittaa kierroksen…';
    if (net.note) info += ' ' + net.note;
    el.info.textContent = info;
    el.pubRow.hidden = !net.host;
    el.pub.checked = net.pub;
    el.voiceRow.hidden = !RTC;
    el.voice.checked = voice.on;
    el.switchGame.hidden = !net.host || !net.connected || racing() || eligibleGames().length < 2;
    el.start.hidden = !net.host;
    el.start.disabled = online < MIN || !net.connected;
    el.start.textContent = net.played ? 'Uusi kierros' : 'Aloita kierros';
  }
  // ---- Friends on the room screen (#324) ----
  var INVITE_MS = 10 * 60e3;
  var inviting = false, invited = {}, askName = '', askRow = null, friendNote = '', friendsSig = '';
  function friendButton(m) {
    var F = friendsLib();
    if (!F || !m.fid || m.id === net.me) return null;
    var st = F.status(m.fid);
    if (st === 'me') return null;
    // A request from this player is answered in its own row under the list.
    if (st === 'friend' || st === 'asked' || st === 'asks') {
      var s = document.createElement('span');
      s.className = 'frs';
      s.textContent = st === 'friend' ? '👫 Kaveri' : st === 'asked' ? 'Pyydetty' : 'Pyytää kaveriksi';
      return s;
    }
    var b = document.createElement('button');
    b.className = 'fr';
    b.textContent = '➕ Kaveriksi';
    b.addEventListener('click', function () {
      if (!cleanName(load(NAME, '')) || F.nameNote()) { askName = m.fid; friendNote = ''; return render(); }
      b.disabled = true;
      F.ask(m.fid).then(function (r) { r.pid = m.fid; friendResult(r); });
    });
    return b;
  }
  // A phone that took a nickname in the room joins again on a new connection, so the room
  // learns its friend id (and nickname) and the others get "➕ Kaveriksi" for it. The room keeps
  // only the newest connection of a phone; the old one's close is ignored (net.ws has moved on).
  function rejoinWithFid() {
    findFid();
    (fidWait || Promise.resolve()).then(function () { if (net.on && net.ws && myFid) { net.ws = null; connect(); } });
  }
  function friendResult(r) {
    // The nickname is not usable (rejected meanwhile): open the row for a new one.
    var F = friendsLib();
    // (Or taken by another phone: the same.)
    if ((r.status === 403 || r.name) && F && F.nameNote()) { askName = r.pid || true; askRow = null; friendNote = ''; return render(); }
    friendNote = F ? F.friendError(r) : '';
    render();
  }
  function renderFriends() {
    var box = el.friends, F = friendsLib();
    el.inv.hidden = !(inviting && F && F.state);
    var st = F && net.on ? F.state : null;
    // Drawn again only when something in it changed, so a half-typed nickname keeps its focus.
    var sig = JSON.stringify([!!F && net.on, F && F.titles, askName, friendNote, st && st.requests, st && st.friends.length, inviting && st && st.friends, invitesNow(), net.code,
      net.members.map(function (m) { return m.fid || ''; })]);
    if (sig === friendsSig) return;
    friendsSig = sig;
    box.textContent = '';
    if (!F || !net.on) return;
    if (askName) {
      // Kept between draws, so what is typed stays while the screen redraws.
      if (!askRow) {
        var input = document.createElement('input'), ok = document.createElement('button');
        askRow = document.createElement('div');
        askRow.className = 'ask';
        // A rejected or taken nickname says so; with none, the row only asks for one.
        askRow.appendChild(document.createTextNode(F.nameNote() || 'Nimimerkkisi kavereille:'));
        input.maxLength = 16; input.placeholder = 'Nimimerkki'; input.style.width = '150px';
        ok.textContent = 'Pyydä';
        ok.addEventListener('click', function () {
          if (!cleanName(input.value)) return;
          var pid = askName;
          ok.disabled = true;
          var v = cleanName(input.value);
          // Only once the server took the name: then join again with the friend id, and ask.
          F.setName(v).then(function (r) {
            if (!r.ok) { ok.disabled = false; friendNote = F.nameError(r, v); render(); return; }
            askName = ''; askRow = null; friendNote = '';
            rejoinWithFid();
            return pid === true ? render() : F.ask(pid).then(friendResult);
          });
        });
        askRow.appendChild(input); askRow.appendChild(ok);
      }
      box.appendChild(askRow);
    }
    if (friendNote) {
      var n = document.createElement('p'); n.className = 'small'; n.textContent = friendNote; box.appendChild(n);
    }
    if (!st) return;
    st.requests.forEach(function (q) {
      var row = document.createElement('div'), yes = document.createElement('button'), no = document.createElement('button');
      row.className = 'ask';
      var who = document.createElement('span'); who.className = 'who'; who.textContent = q.name + ' haluaa kaveriksi';
      yes.textContent = 'Hyväksy'; no.textContent = 'Ei'; no.className = 'no';
      yes.addEventListener('click', function () { yes.disabled = no.disabled = true; F.answer(q.pid, true).then(friendResult); });
      no.addEventListener('click', function () { yes.disabled = no.disabled = true; F.answer(q.pid, false).then(friendResult); });
      row.appendChild(who); row.appendChild(yes); row.appendChild(no);
      box.appendChild(row);
    });
    if (st.friends.length && GAME) {
      var b = document.createElement('button');
      b.textContent = '📨 Kutsu kaveri';
      b.addEventListener('click', function () { inviting = true; render(); F.refresh(); });
      box.appendChild(b);
    }
    if (inviting) renderInvites(F, st);
  }
  function invitesNow() {
    var out = {};
    Object.keys(invited).forEach(function (k) {
      var at = invited[k];
      out[k] = typeof at === 'number' ? Date.now() - at < INVITE_MS : at;
    });
    return out;
  }
  function renderInvites(F, st) {
    var here = {};
    net.members.forEach(function (m) { if (m.fid) here[m.fid] = true; });
    el.invList.textContent = '';
    var left = st.friends.filter(function (f) { return !here[f.pid]; });
    left.forEach(function (f) {
      var li = document.createElement('li'), d = document.createElement('div'), b = document.createElement('button');
      d.textContent = f.name;
      var small = document.createElement('small'); small.textContent = F.doing(f); d.appendChild(small);
      var key = net.code + f.pid, at = invited[key];
      // An invite lives 10 minutes on the server; after that the friend may be invited again.
      var live = at === 'sending' || (typeof at === 'number' && Date.now() - at < INVITE_MS);
      b.textContent = at === 'sending' ? 'Kutsutaan…' : live ? 'Kutsuttu ✓' : at === 'failed' ? 'Ei onnistunut' : 'Kutsu';
      b.disabled = live;
      b.addEventListener('click', function () {
        invited[key] = 'sending'; render();
        F.invite(f.pid, { game: GAME, version: VERSION, room: net.code }).then(function (r) { invited[key] = r.ok ? Date.now() : 'failed'; render(); });
      });
      li.appendChild(d); li.appendChild(b);
      el.invList.appendChild(li);
    });
    el.invNone.textContent = left.length ? '' : 'Kaikki kaverisi ovat jo tässä huoneessa.';
  }
  // Read the friends while the room screen shows a room, every 10 s; and draw again when
  // kaverit.js has loaded or has news.
  var watchingFriends = false, hooked = false;
  function hookFriends() {
    var F = friendsLib();
    if (!F) return;
    if (!hooked) { hooked = true; F.on(render); }
    var want = !!(shown && net.on);
    if (want !== watchingFriends) { watchingFriends = want; F.watch(want); }
  }
  window.addEventListener('aipelitkaverit', function () { hookFriends(); render(); });

  var pauseShown = '';
  function renderPause() {
    if (!root) return; // nothing drawn yet: the room screen has not been opened on this page
    var text = '', canGoOn = false;
    if (needs && net.host && net.on) tellPause();
    if (net.on && racing() && !shown) {
      var names = waitingFor();
      if (!net.connected) text = 'Yhteys katkesi – yhdistetään…';
      else if (!net.host && !hostOn()) text = '⏸ Odotetaan, että ' + hostName() + ' palaa…';
      else if (names.length) { text = '⏸ Odotetaan: ' + names.join(', '); canGoOn = net.host; }
    }
    var k = text + canGoOn;
    if (k === pauseShown) return;
    pauseShown = k;
    el.pause.hidden = !text;
    el.pauseText.textContent = text;
    el.goOn.hidden = !canGoOn;
    el.goOn.textContent = needs ? 'Ohita vuoro' : 'Jatka ilman heitä';
  }

  // ---- A QR code of the join link, drawn here (byte mode, error correction M, versions 1-9) ----
  function qrMatrix(text) {
    var ECC = [0, 10, 16, 26, 18, 24, 16, 18, 22, 22], BLOCKS = [0, 1, 1, 1, 2, 2, 4, 4, 4, 5];
    function rawModules(v) { var r = (16 * v + 128) * v + 64; if (v >= 2) { var n = Math.floor(v / 7) + 2; r -= (25 * n - 10) * n - 55; if (v >= 7) r -= 36; } return r; }
    function bit(x, i) { return ((x >>> i) & 1) !== 0; }
    function mul(x, y) { var z = 0; for (var i = 7; i >= 0; i--) { z = (z << 1) ^ ((z >>> 7) * 0x11d); z ^= ((y >>> i) & 1) * x; } return z; }
    var bytes = Array.prototype.slice.call(new TextEncoder().encode(text));
    var v = 1;
    while (v <= 9 && 12 + bytes.length * 8 > (Math.floor(rawModules(v) / 8) - ECC[v] * BLOCKS[v]) * 8) v++;
    if (v > 9) return null;
    var nData = Math.floor(rawModules(v) / 8) - ECC[v] * BLOCKS[v];
    var bits = [];
    function put(val, n) { for (var i = n - 1; i >= 0; i--) bits.push((val >>> i) & 1); }
    put(4, 4); put(bytes.length, 8); bytes.forEach(function (b) { put(b, 8); });
    put(0, Math.min(4, nData * 8 - bits.length)); put(0, (8 - bits.length % 8) % 8);
    for (var pad = 0xec; bits.length < nData * 8; pad ^= 0xec ^ 0x11) put(pad, 8);
    var data = [], i, j;
    for (i = 0; i < bits.length; i += 8) { var b = 0; for (j = 0; j < 8; j++) b = b << 1 | bits[i + j]; data.push(b); }
    // Reed-Solomon error correction, block by block, then interleaved.
    var ecl = ECC[v], nb = BLOCKS[v], raw = Math.floor(rawModules(v) / 8), nShort = nb - raw % nb, shortLen = Math.floor(raw / nb);
    var div = [], root2, k;
    for (i = 0; i < ecl; i++) div.push(0);
    div[ecl - 1] = 1;
    for (i = 0, root2 = 1; i < ecl; i++) { for (j = 0; j < ecl; j++) { div[j] = mul(div[j], root2); if (j + 1 < ecl) div[j] ^= div[j + 1]; } root2 = mul(root2, 2); }
    var blocks = [];
    for (i = 0, k = 0; i < nb; i++) {
      var d = data.slice(k, k += shortLen - ecl + (i < nShort ? 0 : 1)), rem = [];
      for (j = 0; j < ecl; j++) rem.push(0);
      d.forEach(function (byte) { var f = byte ^ rem.shift(); rem.push(0); div.forEach(function (c, jj) { rem[jj] ^= mul(c, f); }); });
      if (i < nShort) d.push(0);
      blocks.push(d.concat(rem));
    }
    var all = [];
    for (i = 0; i < blocks[0].length; i++) blocks.forEach(function (bl, jj) { if (i !== shortLen - ecl || jj >= nShort) all.push(bl[i]); });
    // The modules: finders, timing, alignment, version and format, then the data in a zigzag.
    var size = v * 4 + 17, m = [], fn = [], y, x;
    for (y = 0; y < size; y++) { m.push(new Array(size).fill(false)); fn.push(new Array(size).fill(false)); }
    function set(x, y, dark) { m[y][x] = dark; fn[y][x] = true; }
    for (i = 0; i < size; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); }
    [[3, 3], [size - 4, 3], [3, size - 4]].forEach(function (c) {
      for (var dy = -4; dy <= 4; dy++) for (var dx = -4; dx <= 4; dx++) {
        var dd = Math.max(Math.abs(dx), Math.abs(dy)), xx = c[0] + dx, yy = c[1] + dy;
        if (xx >= 0 && xx < size && yy >= 0 && yy < size) set(xx, yy, dd !== 2 && dd !== 4);
      }
    });
    var ap = [];
    if (v > 1) { var n = Math.floor(v / 7) + 2, stepA = Math.ceil((v * 4 + 4) / (n * 2 - 2)) * 2; ap.push(6); for (var p = v * 4 + 10; ap.length < n; p -= stepA) ap.splice(1, 0, p); }
    for (i = 0; i < ap.length; i++) for (j = 0; j < ap.length; j++) {
      if ((i === 0 && j === 0) || (i === 0 && j === ap.length - 1) || (i === ap.length - 1 && j === 0)) continue;
      for (var dy = -2; dy <= 2; dy++) for (var dx = -2; dx <= 2; dx++) set(ap[i] + dx, ap[j] + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
    }
    function format(mask) {
      var r = mask, ii; for (ii = 0; ii < 10; ii++) r = (r << 1) ^ ((r >>> 9) * 0x537);
      var fb = (mask << 10 | r) ^ 0x5412; // level M is 00
      for (ii = 0; ii <= 5; ii++) set(8, ii, bit(fb, ii));
      set(8, 7, bit(fb, 6)); set(8, 8, bit(fb, 7)); set(7, 8, bit(fb, 8));
      for (ii = 9; ii < 15; ii++) set(14 - ii, 8, bit(fb, ii));
      for (ii = 0; ii < 8; ii++) set(size - 1 - ii, 8, bit(fb, ii));
      for (ii = 8; ii < 15; ii++) set(8, size - 15 + ii, bit(fb, ii));
      set(8, size - 8, true);
    }
    format(0);
    if (v >= 7) {
      var r = v; for (i = 0; i < 12; i++) r = (r << 1) ^ ((r >>> 11) * 0x1f25);
      var vb = v << 12 | r;
      for (i = 0; i < 18; i++) { var a = size - 11 + i % 3, cc = Math.floor(i / 3); set(a, cc, bit(vb, i)); set(cc, a, bit(vb, i)); }
    }
    for (var right = size - 1, ib = 0; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (var vert = 0; vert < size; vert++) for (j = 0; j < 2; j++) {
        x = right - j; y = ((right + 1) & 2) === 0 ? size - 1 - vert : vert;
        if (!fn[y][x] && ib < all.length * 8) { m[y][x] = bit(all[ib >>> 3], 7 - (ib & 7)); ib++; }
      }
    }
    // Pick the mask that leaves the fewest long runs, 2×2 blocks and imbalance.
    var MASKS = [
      function (x, y) { return (x + y) % 2 === 0; }, function (x, y) { return y % 2 === 0; },
      function (x) { return x % 3 === 0; }, function (x, y) { return (x + y) % 3 === 0; },
      function (x, y) { return (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0; }, function (x, y) { return x * y % 2 + x * y % 3 === 0; },
      function (x, y) { return (x * y % 2 + x * y % 3) % 2 === 0; }, function (x, y) { return ((x + y) % 2 + x * y % 3) % 2 === 0; }];
    function flip(mk) { for (var yy = 0; yy < size; yy++) for (var xx = 0; xx < size; xx++) if (!fn[yy][xx] && MASKS[mk](xx, yy)) m[yy][xx] = !m[yy][xx]; }
    function penalty() {
      var pen = 0, dark = 0, aa, bb, yy, xx;
      for (aa = 0; aa < size; aa++) [true, false].forEach(function (horiz) {
        var run = 1;
        for (bb = 1; bb <= size; bb++) {
          var same = bb < size && (horiz ? m[aa][bb] === m[aa][bb - 1] : m[bb][aa] === m[bb - 1][aa]);
          if (same) run++; else { if (run >= 5) pen += run - 2; run = 1; }
        }
      });
      for (yy = 0; yy < size; yy++) for (xx = 0; xx < size; xx++) {
        if (m[yy][xx]) dark++;
        if (xx < size - 1 && yy < size - 1 && m[yy][xx] === m[yy][xx + 1] && m[yy][xx] === m[yy + 1][xx] && m[yy][xx] === m[yy + 1][xx + 1]) pen += 3;
      }
      return pen + Math.floor(Math.abs(dark * 20 - size * size * 10) / (size * size)) * 10;
    }
    var best = 0, bestP = Infinity;
    for (var mk = 0; mk < 8; mk++) { flip(mk); format(mk); var pp = penalty(); if (pp < bestP) { bestP = pp; best = mk; } flip(mk); }
    flip(best); format(best);
    return m;
  }
  function drawQR(cv, text) {
    var m = qrMatrix(text), g = cv.getContext('2d');
    g.fillStyle = '#fff'; g.fillRect(0, 0, cv.width, cv.height);
    if (!m) return;
    var n = m.length + 8, k = Math.floor(cv.width / n), o = Math.floor((cv.width - k * n) / 2) + 4 * k;
    g.fillStyle = '#000';
    m.forEach(function (row, y) { row.forEach(function (d, x) { if (d) g.fillRect(o + x * k, o + y * k, k, k); }); });
  }

  // ---- The API ----
  window.AiPelitRooms = {
    // on(type, fn): 'start' ({round, players: [{id, name}], host, over}), 'message' (msg, fromId),
    // 'peers' (members), 'hello' (id; host: a phone in the round is back, send it the round),
    // 'continue' (ids; host: the computer takes these players), 'back' (id; host: a player the
    // computer had is back), 'skip' (ids; host, a game played in turns: skip the turn of these
    // away players), 'lobby' (the host lost the round; stop it), 'leave' (reason; out of
    // the room), 'menu' (the room screen is closed; show the game's menu).
    on: function (type, fn) { (handlers[type] = handlers[type] || []).push(fn); return this; },
    open: function () { if (!net.on) net.error = ''; show(true); },
    leave: function () { if (net.on) leave(); else if (shown) { show(false); fire('menu'); } },
    // Going up to the shelf is an intentional departure only when this phone is alone.
    leaveIfAlone: function () {
      if (net.on && net.members.length === 1 && net.members[0].id === net.me) leave();
    },
    // Host: to every other phone, or to one id. A guest: to the host.
    send: function (msg, to) { var m = Object.assign({}, msg); if (to && net.host) m.to = to; sendRaw(m); },
    // Host: to every phone in the round, and only to them. Each phone confirms it; one that has
    // not (away, or a page reloading just now) gets it again when it says hello.
    deliver: function (msg) {
      if (!net.host || !net.round) return;
      var o = { round: net.round.id, players: net.round.players, msg: msg, n: ++net.sent };
      net.round.players.forEach(function (p) {
        if (p.id === net.me) return;
        (net.owed[p.id] = net.owed[p.id] || []).push(o);
        if (net.online[p.id]) sendRaw(Object.assign({}, msg, { to: p.id, _d: o.n, _r: o.round }));
      });
    },
    // Host: the round is over. Phones in it that come back later still get it (as over).
    endRound: function () { if (net.host && net.round) { net.round.over = true; update(); } },
    // After the game's own end screen: the room screen again, with a result line if given.
    backToRoom: function (text, className) {
      if (!net.on) return;
      if (net.round) net.round.over = true;
      forgetAway(net.code);
      net.result = text || ''; net.resultClass = className || '';
      show(true);
    },
    // A line of the game's own under the player list ("Seuraavaksi etsii Aino.").
    note: function (text) { net.note = text || ''; render(); },
    // The game's own element under the player list, shown while this phone is in a room (Hiihto
    // v3's course and style); null takes it away. The game keeps it up to date.
    extra: function (node) { build(); el.extra.textContent = ''; if (node) el.extra.appendChild(node); },
    // True the first time it is asked for this round on this tab, so a result heard twice (or
    // again after a reload) is saved once.
    once: function (round) {
      var key = net.code + ':' + round, seen = sload(COUNTED, []);
      if (seen.indexOf(key) >= 0) return false;
      seen.push(key); ssave(COUNTED, seen.slice(-20));
      return true;
    },
    qr: drawQR,
    get inRoom() { return net.on; },
    get isHost() { return net.on && net.host; },
    get connected() { return net.connected; },
    get me() { return net.me; },
    get hostId() { return net.hostId; },
    get code() { return net.code; },
    get members() { return net.members.slice(); },
    get players() { return net.round ? net.round.players.slice() : []; },
    get round() { return net.round ? net.round.id : ''; },
    // The round should stand still: a phone in it, or the host, or this phone's connection is away.
    get paused() { return isPaused(); },
    get waiting() { return waitingFor(); },
    // A game played in turns (#297): fn(id) is true while the round needs that phone (its turn).
    // Then the round waits only for those, a phone that leaves keeps its player, the host's
    // button is "Ohita vuoro" and fires 'skip' (ids), and the phone can come back to the round.
    turns: function (fn) { needs = typeof fn === 'function' ? fn : null; },
    // Host: the players the computer moves now (let go with "Jatka ilman heitä", or left the room).
    isReleased: function (id) { return !!net.released[id]; },
    // Voice (#322): whether it is on on this phone, this phone talking, who is heard now, and how
    // many phones a call is up with.
    get voice() {
      return { on: RTC && voice.on, talking: voice.talking, speakers: speakers(),
        calls: Object.keys(voice.peers).filter(function (id) { return live(voice.peers[id]); }).length };
    },
    name: myName,
    game: GAME, version: VERSION, min: MIN, max: MAX,
  };

  // A join link (?huone=KOOD) joins at once; a reload goes back to the room this tab was in. After
  // the game's own script has run, so its handlers hear it.
  function autoJoin() {
    var q = new URLSearchParams(location.search).get('huone');
    var back = sload(HERE, null);
    if (back && (back.game !== GAME || back.v !== VERSION)) back = null;
    if (q) history.replaceState(history.state, '', location.pathname);
    var handoff = sload(ISANTA, null);
    if (q && /^[A-Za-z]{4}$/.test(q) && handoff && handoff.code === q.toUpperCase() &&
        handoff.at && Date.now() - handoff.at >= 0 && Date.now() - handoff.at < 60000) {
      ssave(ISANTA, null);
      enter(q.toUpperCase(), true, !!handoff.pub);
    } else if (q && /^[A-Za-z]{4}$/.test(q) && !(back && back.code === q.toUpperCase() && back.host)) {
      enter(q.toUpperCase(), false);
    } else if (back && /^[A-Z]{4}$/.test(back.code)) enter(back.code, !!back.host, !!back.pub);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(autoJoin); });
  else setTimeout(autoJoin);
  setInterval(function () { renderPause(); renderVoice(); }, 250);
  setInterval(voiceSync, 3000);
  setInterval(function () { readList(); tellList(); }, 5000);
})();
