// The "‹ Pelit" chip every game version includes. It sits in its own corner element and stops
// its own touches, so a game listening on the whole window never sees a tap on it.
(function () {
  'use strict';
  // back.js sits in the shelf's own folder.
  var script = document.currentScript;
  var shelf = new URL('./', script.src).href;
  // A game whose own buttons are in the top-left asks for another corner with data-corner.
  var corner = (script.getAttribute('data-corner') || 'top-left').split('-');
  var vertical = corner[0] === 'bottom' ? 'bottom' : 'top';
  var horizontal = corner[1] === 'right' ? 'right' : 'left';
  // Both /games/<slug>/v<N>/ and /games/<slug>/v<N>/index.html.
  var match = location.pathname.match(/\/games\/([^/]+)\/v\d+\//);
  var slug = match ? match[1] : '';
  // One play of this version for the shelf's play counts (#26): anonymous, sent once per page
  // open, and lost when offline. The game never waits for it. A game that reloads its own page to
  // go on (Ottelu v3 between events, #168) marks it in sessionStorage first: that load is the same
  // play, not a new one.
  var version = location.pathname.match(/\/games\/[^/]+\/v(\d+)\//);
  var again = false;
  try {
    again = sessionStorage.getItem('ai-pelit:_jatkuu') === location.pathname;
    if (again) sessionStorage.removeItem('ai-pelit:_jatkuu');
  } catch (e) {}
  if (slug && version && !again && /^https?:$/.test(location.protocol)) {
    try {
      var body = JSON.stringify({ game: slug, version: Number(version[1]) });
      var sent = navigator.sendBeacon && navigator.sendBeacon(shelf + 'api/plays', new Blob([body], { type: 'application/json' }));
      if (!sent) fetch(shelf + 'api/plays', { method: 'POST', body: body, headers: { 'content-type': 'application/json' }, keepalive: true }).catch(function () {});
    } catch (e) {}
  }
  // Playing right now (#325): while this page is on screen it says so every 45 seconds, and says it
  // left when it is hidden, so the shelf can show how many play each game now. The id is random
  // per page open, kept only in this page. A game inside another page's frame is not counted
  // apart: the page the player opened is (Ottelu already drops back.js from its events' frames).
  var framed = true;
  try { framed = window.top !== window.self; } catch (e) {}
  if (slug && !framed && /^https?:$/.test(location.protocol)) {
    // From crypto, not Math.random(): a game's tests seed Math.random(), and an id drawn from it
    // here shifted every number the game drew after it (#330).
    var pageId = '';
    try {
      var bytes = new Uint8Array(12);
      crypto.getRandomValues(bytes);
      for (var i = 0; i < bytes.length; i++) pageId += (bytes[i] % 36).toString(36);
    } catch (e) { pageId = String(Date.now()) + String(performance.now()).replace(/\D/g, ''); }
    pageId = pageId.slice(0, 16);
    var beat = 0;
    var tell = function (gone) {
      try {
        var msg = JSON.stringify(gone ? { id: pageId, gone: true } : { id: pageId, game: slug });
        var told = navigator.sendBeacon && navigator.sendBeacon(shelf + 'api/playing', new Blob([msg], { type: 'application/json' }));
        if (!told) fetch(shelf + 'api/playing', { method: 'POST', body: msg, headers: { 'content-type': 'application/json' }, keepalive: true }).catch(function () {});
      } catch (e) {}
    };
    var onScreen = function () {
      clearInterval(beat);
      if (document.visibilityState === 'hidden') { tell(true); return; }
      tell(false);
      beat = setInterval(function () { tell(false); }, 45000);
    };
    document.addEventListener('visibilitychange', onScreen);
    window.addEventListener('pagehide', function () { clearInterval(beat); tell(true); });
    window.addEventListener('pageshow', function (e) { if (e.persisted) onScreen(); });
    onScreen();
  }
  // Game volume (#336, Eero's choices): one volume for every game, set from the 🔊 chip beside
  // "‹ Pelit". Every game plays through Web Audio, so a gain put between each audio context and its
  // speaker turns down the game's effects, beeps and music alike, in published versions too. The
  // friends' voice in a room (rooms.js) plays through <audio> elements and stays as it is.
  var LEVEL = 'ai-pelit:_aani:voimakkuus', MUTE = 'ai-pelit:_aani:mykistetty';
  var level = 100, muted = false;
  function readSound() {
    try {
      var n = Number(localStorage.getItem(LEVEL));
      level = localStorage.getItem(LEVEL) === null || !isFinite(n) ? 100 : Math.max(0, Math.min(100, Math.round(n)));
      muted = localStorage.getItem(MUTE) === '1';
    } catch (e) {}
  }
  readSound();
  // The slider's percent squared: the ear hears loudness that way, so 50 % sounds about half.
  function gainNow() { return muted ? 0 : (level / 100) * (level / 100); }
  var gains = [];
  function applyGain() {
    var v = gainNow();
    // Set at once: a glide (setTargetAtTime) waits on a context whose clock stands still, before
    // the first tap or while no sound plays, and the slider moves in 5 % steps anyway.
    gains.forEach(function (g) { g.gain.value = v; });
  }
  // Any node connected to a context's speaker is connected to that context's gain instead. The
  // patch is on the window's AudioNode, so contexts made before or after it both follow, and so do
  // the nodes the sound library (lib/aanet-*) and a game's own code connect after the page loaded.
  function installSound(win) {
    var Node = win && win.AudioNode, Dest = win && win.AudioDestinationNode;
    if (!Node || !Dest || Node.prototype.__aiPelitAani) return;
    var connect = Node.prototype.connect, disconnect = Node.prototype.disconnect;
    var Offline = win.OfflineAudioContext || win.webkitOfflineAudioContext;
    var byContext = typeof WeakMap === 'function' ? new WeakMap() : null;
    function gainFor(dest) {
      if (!byContext || !(dest instanceof Dest)) return null;
      var ctx = dest.context;
      if (!ctx || (Offline && ctx instanceof Offline)) return null;
      var g = byContext.get(ctx);
      if (!g) {
        try { g = ctx.createGain(); } catch (e) { return null; }
        g.gain.value = gainNow();
        connect.call(g, dest);
        byContext.set(ctx, g);
        gains.push(g);
      }
      return g;
    }
    Node.prototype.connect = function (to) {
      var g = to && gainFor(to);
      if (!g || this === g) return connect.apply(this, arguments);
      var args = Array.prototype.slice.call(arguments);
      args[0] = g;
      connect.apply(this, args);
      return to;
    };
    Node.prototype.disconnect = function (to) {
      var g = to && byContext && to instanceof Dest && byContext.get(to.context);
      if (!g || this === g) return disconnect.apply(this, arguments);
      var args = Array.prototype.slice.call(arguments);
      args[0] = g;
      return disconnect.apply(this, args);
    };
    Object.defineProperty(Node.prototype, '__aiPelitAani', { value: true });
  }
  installSound(window);
  // Ottelu plays its events in a frame without back.js; each frame that loads follows this page.
  function watchFrame(f) {
    if (f.__aiPelitAani) return;
    f.__aiPelitAani = true;
    var put = function () { try { installSound(f.contentWindow); } catch (e) {} };
    f.addEventListener('load', put);
    put();
  }
  Array.prototype.forEach.call(document.querySelectorAll('iframe'), watchFrame);
  if (typeof MutationObserver === 'function') {
    new MutationObserver(function (list) {
      list.forEach(function (m) {
        Array.prototype.forEach.call(m.addedNodes, function (n) {
          if (n.tagName === 'IFRAME') watchFrame(n);
          else if (n.querySelectorAll) Array.prototype.forEach.call(n.querySelectorAll('iframe'), watchFrame);
        });
      });
    }).observe(document.documentElement, { childList: true, subtree: true });
  }
  // Another tab, or the same game open twice, keeps to the one setting.
  window.addEventListener('storage', function (e) {
    if (e.key !== LEVEL && e.key !== MUTE) return;
    readSound(); applyGain(); drawSound();
  });
  // The chip and the 🔊 chip sit together in the corner, the 🔊 one on the inner side.
  var box = document.createElement('div');
  box.id = 'ai-pelit-kulma';
  box.style.cssText = [
    'position:fixed', 'z-index:2147483647', 'display:flex', 'gap:6px', 'align-items:center',
    'flex-direction:' + (horizontal === 'right' ? 'row-reverse' : 'row'),
    vertical + ':calc(env(safe-area-inset-' + vertical + ', 0px) + 6px)',
    horizontal + ':calc(env(safe-area-inset-' + horizontal + ', 0px) + 6px)',
  ].join(';');
  // all:unset first: a game's own button and link styles must not reach these.
  var CHIP = [
    'all:unset', 'box-sizing:border-box', 'display:inline-block', 'padding:6px 10px', 'border-radius:999px', 'background:rgba(0,0,0,.45)', 'color:#fff',
    'font:600 13px/1 system-ui,sans-serif', 'text-decoration:none', 'touch-action:manipulation',
  ];
  var a = document.createElement('a');
  a.href = shelf + (slug ? '#/' + slug : '');
  a.textContent = '‹ Pelit';
  a.setAttribute('aria-label', 'Takaisin pelilistaan');
  a.id = 'ai-pelit-back';
  a.style.cssText = CHIP.join(';');
  var sound = document.createElement('button');
  sound.type = 'button';
  sound.id = 'ai-pelit-aani';
  sound.setAttribute('aria-expanded', 'false');
  sound.style.cssText = CHIP.concat(['padding:6px 8px', 'cursor:pointer']).join(';');
  // The setting: a slider and a mute, opened from the 🔊 chip, below it (above it at the bottom).
  var panel = document.createElement('div');
  panel.id = 'ai-pelit-aani-paneeli';
  panel.style.cssText = [
    'all:unset', 'display:none', 'position:fixed', 'z-index:2147483647', 'box-sizing:border-box', 'width:230px', 'padding:12px 14px',
    'border-radius:14px', 'background:#16181f', 'color:#fff', 'box-shadow:0 6px 24px rgba(0,0,0,.4)',
    'font:14px/1.3 system-ui,sans-serif', 'touch-action:manipulation',
    vertical + ':calc(env(safe-area-inset-' + vertical + ', 0px) + 44px)',
    horizontal + ':calc(env(safe-area-inset-' + horizontal + ', 0px) + 6px)',
  ].join(';');
  panel.innerHTML =
    '<div style="display:flex;margin:0;justify-content:space-between;font-weight:700"><span>Pelin äänet</span><span id="ai-pelit-aani-luku"></span></div>' +
    '<input id="ai-pelit-aani-liuku" type="range" min="0" max="100" step="5" aria-label="Pelin äänenvoimakkuus" ' +
    'style="display:block;box-sizing:border-box;width:100%;margin:12px 0;padding:0;border:0;box-shadow:none;background:none;accent-color:#7cc4ff;height:28px">' +
    '<button id="ai-pelit-aani-mykista" type="button" style="all:unset;box-sizing:border-box;display:block;text-align:center;cursor:pointer;width:100%;padding:9px;border:0;border-radius:10px;' +
    'background:rgba(255,255,255,.14);color:#fff;font:600 14px system-ui,sans-serif"></button>' +
    '<div style="margin:8px 0 0;font-size:12px;opacity:.75">Kavereiden puhe ei hiljene.</div>';
  box.appendChild(a);
  box.appendChild(sound);
  [box, panel].forEach(function (el) {
    ['pointerdown', 'pointerup', 'pointermove', 'touchstart', 'touchmove', 'touchend', 'mousedown', 'mouseup', 'click'].forEach(function (type) {
      el.addEventListener(type, function (e) { e.stopPropagation(); }, { passive: true });
    });
  });
  var slider = panel.querySelector('#ai-pelit-aani-liuku');
  var muteBtn = panel.querySelector('#ai-pelit-aani-mykista');
  function drawSound() {
    var off = muted || level === 0;
    sound.textContent = off ? '🔇' : level < 50 ? '🔉' : '🔊';
    sound.setAttribute('aria-label', off ? 'Pelin äänet: pois' : 'Pelin äänet: ' + level + ' %');
    slider.value = String(level);
    panel.querySelector('#ai-pelit-aani-luku').textContent = muted ? 'Mykistetty' : level + ' %';
    muteBtn.textContent = muted ? '🔊 Äänet päälle' : '🔇 Mykistä';
  }
  function saveSound() {
    try {
      localStorage.setItem(LEVEL, String(level));
      if (muted) localStorage.setItem(MUTE, '1'); else localStorage.removeItem(MUTE);
    } catch (e) {}
    applyGain(); drawSound();
  }
  slider.addEventListener('input', function () {
    level = Number(slider.value);
    // Moving the slider is wanting sound: it lifts the mute.
    muted = false;
    saveSound();
  });
  muteBtn.addEventListener('click', function () {
    muted = !muted;
    if (!muted && level === 0) level = 50;
    saveSound();
  });
  function openPanel(open) {
    panel.style.display = open ? 'block' : 'none';
    sound.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  sound.addEventListener('click', function () { openPanel(panel.style.display === 'none'); });
  // A tap anywhere else closes it.
  window.addEventListener('pointerdown', function (e) {
    if (panel.style.display !== 'none' && !box.contains(e.target) && !panel.contains(e.target)) openPanel(false);
  }, { capture: true, passive: true });
  // A tap inside a frame (Ottelu's events) never reaches this window; it only takes the focus.
  window.addEventListener('blur', function () { openPanel(false); });
  drawSound();
  // The chip and the phone's own back both go up, to the game's page, never back into a game
  // (#68). When the shelf opened this game it left the game's page just below it in the history
  // (app.js marks that in sessionStorage), so the chip steps back to it. Otherwise (a link, a
  // home-screen shortcut, a reload into a room) the chip takes this page's place, so back from
  // the game's page never comes here again.
  var UP = 'ai-pelit:_ylos';
  try {
    if (sessionStorage.getItem(UP) === location.pathname.replace(/index\.html$/, '')) {
      sessionStorage.removeItem(UP);
      var state = history.state && typeof history.state === 'object' ? history.state : {};
      state.aiPelitUp = true;
      history.replaceState(state, '');
    }
  } catch (e) {}
  a.addEventListener('click', function (e) {
    // A new tab (Ctrl, Cmd, Shift, middle button) opens the link as it is.
    if (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    if (history.state && history.state.aiPelitUp) history.back();
    else location.replace(a.href);
  });
  // Play full screen: the installed app already is (manifest "display": "fullscreen"); in a browser
  // tab, or an app installed before that, the first tap asks for it. Only a pointerup, touchend or
  // click lets a page go full screen, and a tap after the player left full screen asks again.
  var root = document.documentElement;
  function fullScreen(e) {
    if (box.contains(e.target) || panel.contains(e.target) || document.fullscreenElement || !root.requestFullscreen) return;
    if (window.matchMedia && matchMedia('(display-mode: fullscreen)').matches) return;
    var asked = root.requestFullscreen({ navigationUI: 'hide' });
    if (asked && asked.catch) asked.catch(function () {});
  }
  ['pointerup', 'touchend', 'click'].forEach(function (type) {
    window.addEventListener(type, fullScreen, { capture: true, passive: true });
  });
  function add() { document.body.appendChild(box); document.body.appendChild(panel); }
  if (document.body) add(); else document.addEventListener('DOMContentLoaded', add);
  // Friends (#324): what this game is, for the friend list, and invites into rooms, in every game.
  if (/^https?:$/.test(location.protocol) && !window.AiPelitKaverit) {
    var friends = document.createElement('script');
    friends.src = shelf + 'kaverit.js';
    friends.async = true;
    (document.head || document.documentElement).appendChild(friends);
  }
})();
