// The "‹ Pelit" chip every game version includes. It sits in its own corner element and stops
// its own touches, so a game listening on the whole window never sees a tap on it.
(function () {
  'use strict';
  // back.js sits in the shelf's own folder.
  var shelf = new URL('./', document.currentScript.src).href;
  var parts = location.pathname.split('/').filter(Boolean);
  var slug = parts[parts.length - 2] || '';
  var a = document.createElement('a');
  a.href = shelf + '#/' + slug;
  a.textContent = '‹ Pelit';
  a.setAttribute('aria-label', 'Takaisin pelilistaan');
  a.id = 'ai-pelit-back';
  a.style.cssText = [
    'position:fixed', 'z-index:2147483647',
    'top:calc(env(safe-area-inset-top, 0px) + 6px)', 'left:calc(env(safe-area-inset-left, 0px) + 6px)',
    'padding:6px 10px', 'border-radius:999px', 'background:rgba(0,0,0,.45)', 'color:#fff',
    'font:600 13px/1 system-ui,sans-serif', 'text-decoration:none', 'touch-action:manipulation',
  ].join(';');
  ['pointerdown', 'touchstart', 'mousedown'].forEach(function (type) {
    a.addEventListener(type, function (e) { e.stopPropagation(); }, { passive: true });
  });
  a.addEventListener('click', function (e) { e.stopPropagation(); });
  function add() { document.body.appendChild(a); }
  if (document.body) add(); else document.addEventListener('DOMContentLoaded', add);
})();
