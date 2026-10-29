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
  function add() { document.body.appendChild(a); }
  if (document.body) add(); else document.addEventListener('DOMContentLoaded', add);
})();
