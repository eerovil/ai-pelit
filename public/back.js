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
  // open, and lost when offline. The game never waits for it.
  var version = location.pathname.match(/\/games\/[^/]+\/v(\d+)\//);
  if (slug && version && /^https?:$/.test(location.protocol)) {
    try {
      var body = JSON.stringify({ game: slug, version: Number(version[1]) });
      var sent = navigator.sendBeacon && navigator.sendBeacon(shelf + 'api/plays', new Blob([body], { type: 'application/json' }));
      if (!sent) fetch(shelf + 'api/plays', { method: 'POST', body: body, headers: { 'content-type': 'application/json' }, keepalive: true }).catch(function () {});
    } catch (e) {}
  }
  var a = document.createElement('a');
  a.href = shelf + (slug ? '#/' + slug : '');
  a.textContent = '‹ Pelit';
  a.setAttribute('aria-label', 'Takaisin pelilistaan');
  a.id = 'ai-pelit-back';
  a.style.cssText = [
    'position:fixed', 'z-index:2147483647',
    vertical + ':calc(env(safe-area-inset-' + vertical + ', 0px) + 6px)',
    horizontal + ':calc(env(safe-area-inset-' + horizontal + ', 0px) + 6px)',
    'padding:6px 10px', 'border-radius:999px', 'background:rgba(0,0,0,.45)', 'color:#fff',
    'font:600 13px/1 system-ui,sans-serif', 'text-decoration:none', 'touch-action:manipulation',
  ].join(';');
  ['pointerdown', 'pointerup', 'touchstart', 'touchend', 'mousedown', 'mouseup', 'click'].forEach(function (type) {
    a.addEventListener(type, function (e) { e.stopPropagation(); }, { passive: true });
  });
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
    if (e.defaultPrevented) return;
    e.preventDefault();
    if (history.state && history.state.aiPelitUp) history.back();
    else location.replace(a.href);
  });
  // Play full screen: the installed app already is (manifest "display": "fullscreen"); in a browser
  // tab, or an app installed before that, the first tap asks for it. Only a pointerup, touchend or
  // click lets a page go full screen, and a tap after the player left full screen asks again.
  var root = document.documentElement;
  function fullScreen(e) {
    if (e.target === a || document.fullscreenElement || !root.requestFullscreen) return;
    if (window.matchMedia && matchMedia('(display-mode: fullscreen)').matches) return;
    var asked = root.requestFullscreen({ navigationUI: 'hide' });
    if (asked && asked.catch) asked.catch(function () {});
  }
  ['pointerup', 'touchend', 'click'].forEach(function (type) {
    window.addEventListener(type, fullScreen, { capture: true, passive: true });
  });
  function add() { document.body.appendChild(a); }
  if (document.body) add(); else document.addEventListener('DOMContentLoaded', add);
})();
