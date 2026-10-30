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
  var HERE = 'ai-pelit:_huone:nyt'; // sessionStorage: the room this tab is in, to rejoin after a reload
  var COUNTED = 'ai-pelit:_huone:kierros'; // sessionStorage: rounds whose result this tab saved

  function load(k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function sload(k, d) { try { var v = sessionStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
  function ssave(k, v) { try { if (v === null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function hex(n) { return Array.prototype.map.call(crypto.getRandomValues(new Uint8Array(n)), function (b) { return (b < 16 ? '0' : '') + b.toString(16); }).join(''); }
  function cleanName(s) { return String(s || '').replace(/[\u0000-\u001f\u007f]/g, '').replace(/\s+/g, ' ').trim().slice(0, 16); }

  var myKey = load(KEY, '') || (function () { var k = hex(16); save(KEY, k); return k; })();
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

  // ---- The connection ----
  function connect() {
    clearTimeout(net.timer);
    var u = new URL(net.code, API);
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
    var q = { key: myKey, name: myName() };
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
    net.on = true; net.host = host; net.code = code; net.joined = false; net.tries = 0; net.pub = !!(host && pub); listed = null;
    net.hostId = host ? net.me : ''; net.members = []; net.online = {}; net.wait = false; net.error = '';
    net.round = null; net.released = {}; net.owed = {}; net.got = {}; net.pz = []; net.played = false;
    net.result = ''; net.resultClass = ''; net.note = ''; lastPz = '';
    show(true);
    connect();
  }

  // Leaves the room. With a reason (the room closed, a refused join) the room screen stays open on
  // its first page with the reason; without one (the player left) the game gets its screen back.
  function leave(why) {
    if (!net.on) return;
    var ws = net.ws;
    if (net.host) sendRaw({ t: '_close' });
    sendRaw({ t: 'bye' });
    net.on = false; net.ws = null; net.connected = false; clearTimeout(net.timer);
    if (ws) try { ws.close(1000, 'Poistui'); } catch (e) { /* gone */ }
    ssave(HERE, null);
    net.round = null; net.pz = [];
    update();
    fire('leave', why || '');
    if (why) { net.error = why; show(true); } else { show(false); fire('menu'); }
  }

  function onMessage(m) {
    // Every new connection: the room says who this phone is, and a guest says hello to the host,
    // which sends the round back if this phone is in it (after a reload or a dropped connection).
    // Until the host answers, a guest does not know whether it is in the round, so it hears none
    // of the game's messages: a phone that is not in the round never sees the round's messages.
    if (m.t === 'you') { net.me = m.id; if (net.host) net.hostId = m.id; else { net.listening = false; sendRaw({ t: 'hello' }); } return; }
    if (m.t === 'peers') return onPeers(m);
    if (net.host) {
      if (m.t === 'hello') return onHello(m.from);
      if (m.t === '_got') return onGot(m.from, m.n);
      if (m.t && m.t.charAt(0) !== '_') fire('message', m, m.from);
      return;
    }
    if (m.t === '_start') return onStart(m);
    if (m.t === '_lobby') {
      net.wait = false; net.listening = false;
      if (net.round) { net.round = null; net.pz = []; net.result = ''; fire('lobby'); show(true); }
      return render();
    }
    if (m.t === '_wait') { net.wait = true; net.listening = false; return render(); }
    if (m.t === '_pz') { net.pz = Array.isArray(m.names) ? m.names : []; return update(); }
    if (m.t === '_close') return leave('Huone suljettiin.');
    if (!net.listening || !m.t || m.t.charAt(0) === '_') return;
    // A delivered message (deliver()): confirm it, and pass it on only the first time.
    if (m._d) {
      var key = m._r + ':' + m._d, first = !net.got[key];
      net.got[key] = true;
      sendRaw({ t: '_got', n: m._d });
      if (!first) return;
      m = Object.assign({}, m);
      delete m._d; delete m._r; delete m.to;
    }
    fire('message', m, net.hostId);
  }

  function onPeers(m) {
    net.members = Array.isArray(m.members) ? m.members : [];
    net.hostId = m.host;
    net.online = {};
    net.members.forEach(function (x) { if (x.on) net.online[x.id] = true; });
    if (!net.joined) {
      // A room that does not say its game was made by a game from before this file (Kirkkis v2),
      // whose messages this game does not speak: leave it, and say why.
      if (!net.host && (!m.game || !m.v)) return leave('Huone on toisessa pelissä.');
      // A room made in another game or version: open that one, in this room.
      if (!net.host && (m.game !== GAME || m.v !== VERSION)) {
        var to = new URL('../../' + m.game + '/v' + m.v + '/?huone=' + net.code, location.href);
        net.on = false; sendRaw({ t: 'bye' }); ssave(HERE, null);
        location.replace(to.href);
        return;
      }
      net.joined = true;
      keepHere();
      // A host that comes back without its round (a reload) sends everyone back to the room. Only
      // then: after an ordinary round each phone goes back on its own, keeping its result.
      if (net.host && !net.round) sendRaw({ t: '_lobby' });
    }
    if (net.host) {
      // Someone who left the room for good is the computer's from now on.
      if (racing()) {
        var gone = net.round.players.filter(function (p) {
          return p.id !== net.me && !net.released[p.id] && !net.members.some(function (x) { return x.id === p.id; });
        }).map(function (p) { return p.id; });
        if (gone.length) { gone.forEach(function (id) { net.released[id] = true; }); fire('continue', gone); }
      }
    } else if (!net.members.some(function (x) { return x.id === net.hostId; })) {
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
    return net.round.players.filter(function (p) { return p.id !== net.me && !net.online[p.id] && !net.released[p.id]; })
      .map(function (p) { return p.name; });
  }
  function isPaused() {
    if (!net.on || !racing()) return false;
    return !net.connected || (!net.host && !hostOn()) || waitingFor().length > 0;
  }
  function update() {
    if (net.host && net.on) {
      var pz = JSON.stringify(waitingFor());
      if (pz !== lastPz) { lastPz = pz; sendRaw({ t: '_pz', names: JSON.parse(pz) }); }
      tellList();
    }
    render();
  }
  function goOn() {
    if (!net.host || !racing()) return;
    var ids = net.round.players.filter(function (p) { return p.id !== net.me && !net.online[p.id] && !net.released[p.id]; })
      .map(function (p) { return p.id; });
    ids.forEach(function (id) { net.released[id] = true; });
    if (ids.length) fire('continue', ids);
    update();
  }

  // ---- The screen ----
  var root = null, el = {};
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
    '#aipr label.sw{flex-direction:row;gap:8px;font-size:15px;color:#2b2416}',
    '#aipr input[type=checkbox]{width:22px;height:22px;padding:0;margin:0;accent-color:#3f8ad8}',
    '#aipr-pause{position:fixed;left:16px;right:16px;top:40%;z-index:2147483641;display:flex;flex-direction:column;align-items:center;gap:10px;padding:16px;border-radius:16px;background:rgba(30,20,40,.88);color:#fff;text-align:center;font:700 17px/1.35 system-ui,sans-serif;touch-action:manipulation}',
    '#aipr-pause p{margin:0}',
    '#aipr-pause button{font:800 16px system-ui,sans-serif;padding:9px 16px;border:0;border-radius:12px;background:#f2c94c;color:#2b2416}',
  ].join('\n');
  var HTML =
    '<h2>👥 Kavereiden kanssa</h2>' +
    '<div class="v" id="aipr-join">' +
      '<label>Nimesi <input id="aipr-name" maxlength="16" autocomplete="off" enterkeyhint="done"></label>' +
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
      '<p id="aipr-info"></p>' +
      '<label class="sw" id="aipr-pubRow" hidden><input type="checkbox" id="aipr-pub">🌍 Julkinen: kuka tahansa voi liittyä</label>' +
      '<button id="aipr-start" hidden>Aloita kierros</button>' +
    '</div>' +
    '<p id="aipr-err"></p>' +
    '<button id="aipr-back" class="plain">Takaisin</button>';

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
    ['join', 'name', 'create', 'codeIn', 'joinBtn', 'open', 'rooms', 'none', 'pubRow', 'pub', 'room', 'result', 'code', 'qr', 'members', 'info', 'start', 'err', 'back', 'pauseText', 'goOn']
      .forEach(function (k) { el[k] = document.getElementById('aipr-' + k); });
    el.pause = pause;
    el.create.addEventListener('click', function () { takeName(); enter(newCode(), true); });
    el.joinBtn.addEventListener('click', joinTyped);
    el.codeIn.addEventListener('keydown', function (e) { if (e.key === 'Enter') joinTyped(); });
    el.start.addEventListener('click', startRound);
    el.pub.addEventListener('change', function () { net.pub = el.pub.checked; if (net.joined) keepHere(); tellList(); render(); });
    el.back.addEventListener('click', function () { if (net.on) leave(); else { show(false); fire('menu'); } });
    el.goOn.addEventListener('click', goOn);
  }
  function takeName() {
    var n = cleanName(el.name.value);
    if (n && n !== myName()) save(NAME, n);
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
    root.hidden = !on;
    if (on) el.name.value = myName();
    render();
    readList();
    tellList();
  }
  function joinLink() { return location.origin + location.pathname + '?huone=' + net.code; }

  function render() {
    if (!root) return;
    renderPause();
    if (!shown) return;
    el.join.hidden = net.on;
    el.room.hidden = !net.on;
    el.back.textContent = net.on ? 'Poistu huoneesta' : 'Takaisin';
    el.err.textContent = net.on ? '' : net.error;
    if (!net.on) return renderList();
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
      el.members.appendChild(li);
    });
    var online = net.members.filter(function (m) { return m.on; }).length, info;
    if (!net.connected) info = 'Yhdistetään…';
    else if (net.host) {
      info = online < MIN ? 'Odotetaan kavereita…'
        : online < MAX ? online + ' pelaajaa.'
        : MAX + ' pelaajaa – huone on täynnä.';
    } else info = net.wait ? 'Kierros on käynnissä – pääset mukaan seuraavaan.' : 'Odotetaan, että ' + hostName() + ' aloittaa kierroksen…';
    if (net.note) info += ' ' + net.note;
    el.info.textContent = info;
    el.pubRow.hidden = !net.host;
    el.pub.checked = net.pub;
    el.start.hidden = !net.host;
    el.start.disabled = online < MIN || !net.connected;
    el.start.textContent = net.played ? 'Uusi kierros' : 'Aloita kierros';
  }
  var pauseShown = '';
  function renderPause() {
    if (!root) return; // nothing drawn yet: the room screen has not been opened on this page
    var text = '', canGoOn = false;
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
    // computer had is back), 'lobby' (the host lost the round; stop it), 'leave' (reason; out of
    // the room), 'menu' (the room screen is closed; show the game's menu).
    on: function (type, fn) { (handlers[type] = handlers[type] || []).push(fn); return this; },
    open: function () { if (!net.on) net.error = ''; show(true); },
    leave: function () { if (net.on) leave(); else if (shown) { show(false); fire('menu'); } },
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
      net.result = text || ''; net.resultClass = className || '';
      show(true);
    },
    // A line of the game's own under the player list ("Seuraavaksi etsii Aino.").
    note: function (text) { net.note = text || ''; render(); },
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
    // Host: the players the computer moves now (let go with "Jatka ilman heitä", or left the room).
    isReleased: function (id) { return !!net.released[id]; },
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
    if (q && /^[A-Za-z]{4}$/.test(q) && !(back && back.code === q.toUpperCase() && back.host)) enter(q.toUpperCase(), false);
    else if (back && /^[A-Z]{4}$/.test(back.code)) enter(back.code, !!back.host, !!back.pub);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(autoJoin); });
  else setTimeout(autoJoin);
  setInterval(renderPause, 250);
  setInterval(function () { readList(); tellList(); }, 5000);
})();
