// The outfit picker (#158). A version whose player has a figure to dress opts in with
//
//   <script src="../../../outfits.js" data-game="<slug>"></script>
//
// before its own script, and then
//
//   AiPelitOutfits.setup({
//     outfits: [{ id: 'perus', name: 'Perus', top: '#ee6c4d', ... }, ...], // the game's own, first is the default
//     draw: function (ctx, outfit, w, h) { ... },  // the figure in this outfit, for the picker's cards
//     change: function (outfit) { ... },           // the player picked another one
//   });
//
// The Halloween costumes below are added after the game's own (pass `halloween: false` to leave
// them out), and come first in the picker around Halloween. Every outfit is a plain palette the
// game's own drawing reads: `skin`, `hair`, `top`, `bottom`, `shoe`, `cape` (a colour or null) and
// `head` (null, or a costume head that head() draws). A game reads what it needs and ignores the
// rest; outfit.halloween is true for a costume.
//
// The choice is saved per game on the phone (ai-pelit:_asut:<slug>), so every version of a game
// shares it. AiPelitOutfits.current() is the outfit now; .get(id) is any outfit by id (for a
// friend's figure in a room: send current().id with the player); .open() shows the picker.
// Later versions load this same file, so it must stay compatible with every version that uses it.
(function () {
  'use strict';
  var script = document.currentScript;
  var GAME = (script && script.getAttribute('data-game')) || '';
  var KEY = 'ai-pelit:_asut:' + GAME;
  function load(k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

  // ---- The Halloween costumes, the same in every game ----
  var HALLOWEEN = [
    { id: 'kurpitsa', name: 'Kurpitsa', emoji: '🎃', skin: '#f4c7a1', hair: '#3b2a1a', top: '#f07a1a', bottom: '#2d4a1e', shoe: '#1d2a12', cape: null, head: 'pumpkin' },
    { id: 'noita', name: 'Noita', emoji: '🧙', skin: '#9fd17a', hair: '#2a2a2a', top: '#4a2775', bottom: '#1e1b2a', shoe: '#111', cape: '#2b1745', head: 'witch' },
    { id: 'haamu', name: 'Haamu', emoji: '👻', skin: '#f4f4f8', hair: '#f4f4f8', top: '#f4f4f8', bottom: '#e4e4ee', shoe: '#d8d8e4', cape: '#ffffff', head: 'ghost' },
    { id: 'luuranko', name: 'Luuranko', emoji: '💀', skin: '#ece6d6', hair: '#ece6d6', top: '#1a1a1e', bottom: '#1a1a1e', shoe: '#0c0c0e', cape: null, head: 'skull', bones: true },
    { id: 'vampyyri', name: 'Vampyyri', emoji: '🧛', skin: '#e8e0ec', hair: '#121212', top: '#151515', bottom: '#151515', shoe: '#000', cape: '#9b1024', head: 'vampire' },
    { id: 'muumio', name: 'Muumio', emoji: '🩹', skin: '#e9dfc4', hair: '#e9dfc4', top: '#e2d6b6', bottom: '#d6c9a6', shoe: '#c4b690', cape: null, head: 'mummy' },
  ];
  HALLOWEEN.forEach(function (o) { o.halloween = true; });

  // Around Halloween (20 October to 2 November) the costumes come first.
  function season(d) {
    d = d || new Date();
    var m = d.getMonth() + 1, day = d.getDate();
    return (m === 10 && day >= 20) || (m === 11 && day <= 2);
  }

  var outfits = [], drawFn = null, changeFn = null;
  function byId(id) {
    for (var i = 0; i < outfits.length; i++) if (outfits[i].id === id) return outfits[i];
    return null;
  }
  function current() { return byId(load(KEY, '')) || outfits[0] || null; }

  // ---- Costume heads: drawn at (x, y), radius r, the face towards +x (or -x when face < 0) ----
  function head(ctx, kind, x, y, r, face) {
    var f = face < 0 ? -1 : 1;
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(f, 1);
    var c = ctx;
    function circle(cx, cy, rr, col) { c.fillStyle = col; c.beginPath(); c.arc(cx, cy, rr, 0, 7); c.fill(); }
    function tri(a, b, cc, col) { c.fillStyle = col; c.beginPath(); c.moveTo(a[0], a[1]); c.lineTo(b[0], b[1]); c.lineTo(cc[0], cc[1]); c.closePath(); c.fill(); }
    if (kind === 'pumpkin') {
      // A carved pumpkin, a little wider than a head, ribbed, with a stem and a lit face.
      c.fillStyle = '#e8711a';
      c.beginPath(); c.ellipse(0, 0, r * 1.25, r * 1.1, 0, 0, 7); c.fill();
      c.strokeStyle = '#b8520c'; c.lineWidth = Math.max(1, r * 0.1);
      c.beginPath(); c.ellipse(-r * 0.35, 0, r * 0.45, r * 1.05, 0, 0, 7); c.stroke();
      c.beginPath(); c.ellipse(r * 0.35, 0, r * 0.45, r * 1.05, 0, 0, 7); c.stroke();
      c.fillStyle = '#3f6b22'; c.fillRect(-r * 0.12, -r * 1.4, r * 0.24, r * 0.4);
      tri([r * 0.15, -r * 0.1], [r * 0.45, -r * 0.1], [r * 0.3, -r * 0.45], '#ffd23f');
      tri([r * 0.6, -r * 0.1], [r * 0.95, -r * 0.1], [r * 0.78, -r * 0.45], '#ffd23f');
      c.fillStyle = '#ffd23f'; c.beginPath();
      c.moveTo(r * 0.1, r * 0.25); c.lineTo(r * 1.0, r * 0.25); c.lineTo(r * 0.85, r * 0.6);
      c.lineTo(r * 0.7, r * 0.45); c.lineTo(r * 0.55, r * 0.62); c.lineTo(r * 0.4, r * 0.45); c.lineTo(r * 0.25, r * 0.6);
      c.closePath(); c.fill();
    } else if (kind === 'witch') {
      circle(0, 0, r, '#9fd17a');
      circle(r * 0.55, -r * 0.05, Math.max(1, r * 0.14), '#1b1b1b');
      tri([r * 0.85, r * 0.05], [r * 1.35, r * 0.25], [r * 0.85, r * 0.35], '#86bf5e'); // the nose
      c.fillStyle = '#2a2a2a'; c.fillRect(-r * 1.0, -r * 0.2, r * 0.6, r * 1.1);    // hair at the back
      c.fillStyle = '#1b1426'; c.beginPath(); c.ellipse(0, -r * 0.55, r * 1.55, r * 0.22, -0.05, 0, 7); c.fill();
      tri([-r * 0.8, -r * 0.6], [r * 0.8, -r * 0.6], [-r * 0.6, -r * 2.5], '#1b1426');
      c.fillStyle = '#8a4fd1'; c.fillRect(-r * 0.75, -r * 0.95, r * 1.45, r * 0.28);
    } else if (kind === 'ghost') {
      circle(0, 0, r * 1.08, '#f4f4f8');
      c.fillStyle = '#1b1b24';
      c.beginPath(); c.ellipse(r * 0.3, -r * 0.2, r * 0.16, r * 0.26, 0, 0, 7); c.fill();
      c.beginPath(); c.ellipse(r * 0.75, -r * 0.2, r * 0.14, r * 0.24, 0, 0, 7); c.fill();
      c.beginPath(); c.ellipse(r * 0.55, r * 0.42, r * 0.15, r * 0.2, 0, 0, 7); c.fill();
    } else if (kind === 'skull') {
      circle(0, -r * 0.05, r, '#ece6d6');
      c.fillStyle = '#ece6d6'; c.fillRect(r * 0.05, r * 0.4, r * 0.8, r * 0.5);
      circle(r * 0.5, -r * 0.1, r * 0.24, '#141414');
      circle(-r * 0.15, -r * 0.1, r * 0.2, '#141414');
      tri([r * 0.78, r * 0.18], [r * 0.95, r * 0.38], [r * 0.7, r * 0.38], '#141414');
      c.strokeStyle = '#141414'; c.lineWidth = Math.max(1, r * 0.07);
      c.beginPath();
      for (var i = 0; i < 4; i++) { c.moveTo(r * (0.18 + i * 0.2), r * 0.55); c.lineTo(r * (0.18 + i * 0.2), r * 0.88); }
      c.stroke();
    } else if (kind === 'vampire') {
      circle(0, 0, r, '#e8e0ec');
      c.fillStyle = '#121212'; c.beginPath();
      c.arc(-r * 0.05, -r * 0.05, r * 1.04, Math.PI * 0.95, Math.PI * 1.85); c.lineTo(r * 0.35, -r * 0.45); c.closePath(); c.fill();
      circle(r * 0.55, -r * 0.08, Math.max(1, r * 0.14), '#c4102a');
      c.strokeStyle = '#7a0d1c'; c.lineWidth = Math.max(1, r * 0.08);
      c.beginPath(); c.moveTo(r * 0.35, r * 0.48); c.lineTo(r * 0.9, r * 0.45); c.stroke();
      tri([r * 0.5, r * 0.48], [r * 0.64, r * 0.48], [r * 0.57, r * 0.72], '#fff');
      tri([r * 0.72, r * 0.47], [r * 0.86, r * 0.47], [r * 0.79, r * 0.7], '#fff');
      c.fillStyle = '#9b1024'; c.beginPath(); // the high collar behind the head
      c.moveTo(-r * 0.9, r * 0.5); c.lineTo(-r * 1.25, -r * 0.35); c.lineTo(-r * 0.55, r * 0.9); c.closePath(); c.fill();
    } else if (kind === 'mummy') {
      circle(0, 0, r, '#e9dfc4');
      c.strokeStyle = '#bfae86'; c.lineWidth = Math.max(1, r * 0.12);
      c.save(); c.beginPath(); c.arc(0, 0, r, 0, 7); c.clip();
      c.beginPath();
      for (var k = -3; k <= 3; k++) { c.moveTo(-r * 1.2, k * r * 0.32 - r * 0.25); c.lineTo(r * 1.2, k * r * 0.32 + r * 0.15); }
      c.stroke(); c.restore();
      c.fillStyle = '#2a2018'; c.fillRect(r * 0.2, -r * 0.3, r * 0.8, r * 0.26);
      circle(r * 0.55, -r * 0.17, Math.max(1, r * 0.1), '#e8ff6a');
    } else {
      circle(0, 0, r, '#f4c7a1');
    }
    ctx.restore();
  }

  // ---- The picker ----
  var panel = null;
  function el(tag, css, text) {
    var e = document.createElement(tag);
    if (css) e.style.cssText = css;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  // Like back.js: the game never sees a touch meant for the picker.
  function shield(e) {
    ['pointerdown', 'pointerup', 'pointermove', 'touchstart', 'touchend', 'touchmove', 'mousedown', 'mouseup', 'click', 'keydown', 'keyup']
      .forEach(function (type) { e.addEventListener(type, function (ev) { ev.stopPropagation(); }, { passive: true }); });
  }
  function close() { if (panel) { panel.remove(); panel = null; } }
  var BTN = 'border:0;border-radius:10px;padding:10px 14px;font:600 15px system-ui,sans-serif;touch-action:manipulation;box-shadow:none;transform:none;text-shadow:none;';

  function card(o, picked, grid) {
    var b = el('button', 'box-shadow:none;transform:none;text-shadow:none;margin:0;height:auto;width:auto;display:flex;flex-direction:column;align-items:center;gap:2px;border:3px solid ' + (picked ? '#ffd45c' : 'transparent') +
      ';border-radius:12px;background:' + (o.halloween ? '#2b2140' : '#2a3358') + ';color:#fff;padding:4px 2px 6px;font:600 13px system-ui,sans-serif;touch-action:manipulation;min-width:0');
    b.className = 'asu' + (picked ? ' valittu' : '');
    b.setAttribute('data-asu', o.id);
    // A low, wide screen gets smaller cards, so both rows fit without scrolling.
    var cw = innerHeight < 500 ? 52 : 72, ch = innerHeight < 500 ? 58 : 80;
    var cv = el('canvas', 'width:' + cw + 'px;height:' + ch + 'px;display:block');
    var dpr = Math.min(window.devicePixelRatio || 1, 3);
    cv.width = Math.round(cw * dpr); cv.height = Math.round(ch * dpr);
    var ctx = cv.getContext('2d');
    if (ctx && drawFn) {
      ctx.scale(dpr, dpr);
      try { drawFn(ctx, o, cw, ch); } catch (e) {}
    }
    b.appendChild(cv);
    b.appendChild(el('span', 'max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap', (o.emoji && innerHeight >= 500 ? o.emoji + ' ' : '') + o.name));
    b.onclick = function () {
      save(KEY, o.id);
      if (changeFn) { try { changeFn(o); } catch (e) {} }
      fill(grid);
    };
    return b;
  }

  function fill(grid) {
    grid.textContent = '';
    var now = current(), own = [], costumes = [];
    outfits.forEach(function (o) { (o.halloween ? costumes : own).push(o); });
    var groups = season() ? [['🎃 Halloween', costumes], ['Tavalliset', own]] : [['Tavalliset', own], ['🎃 Halloween', costumes]];
    groups.forEach(function (g) {
      if (!g[1].length) return;
      grid.appendChild(el('div', 'grid-column:1/-1;font-weight:700;color:#cfd6ee;margin-top:4px', g[0]));
      g[1].forEach(function (o) { grid.appendChild(card(o, now && o.id === now.id, grid)); });
    });
  }

  function open() {
    close();
    if (!outfits.length) return;
    panel = el('div', 'position:fixed;inset:0;z-index:2147483646;background:rgba(10,14,30,.82);display:flex;align-items:center;justify-content:center;padding:calc(env(safe-area-inset-top,0px) + 44px) calc(env(safe-area-inset-right,0px) + 10px) calc(env(safe-area-inset-bottom,0px) + 10px) calc(env(safe-area-inset-left,0px) + 10px);box-sizing:border-box;font:15px/1.35 system-ui,sans-serif;color:#fff;touch-action:manipulation');
    panel.id = 'ai-pelit-asut';
    shield(panel);
    var box = el('div', 'background:#1c2340;border-radius:16px;padding:12px;width:100%;max-width:360px;max-height:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:8px;box-shadow:0 8px 30px rgba(0,0,0,.5)');
    if (innerWidth > innerHeight) box.style.maxWidth = '700px';
    // Sideways the picker goes beside the corner chips, not under them, and keeps the height.
    if (innerWidth > innerHeight && innerHeight < 500) {
      panel.style.padding = 'calc(env(safe-area-inset-top,0px) + 8px) calc(env(safe-area-inset-right,0px) + 96px) calc(env(safe-area-inset-bottom,0px) + 8px) calc(env(safe-area-inset-left,0px) + 84px)';
    }
    panel.appendChild(box);
    var top = el('div', 'display:flex;align-items:center;gap:8px');
    top.appendChild(el('div', 'font-weight:800;font-size:19px;flex:1', '👕 Valitse asu'));
    var done = el('button', BTN + 'background:#ffd45c;color:#222', 'Valmis');
    done.id = 'ai-pelit-asut-valmis';
    done.onclick = close;
    top.appendChild(done);
    box.appendChild(top);
    if (season() && innerHeight >= 500) box.appendChild(el('div', 'color:#ffb35c;font-size:13px', 'Hyvää Halloweenia! Pukeudu kurpitsaksi, noidaksi tai haamuksi.'));
    var low = innerHeight < 500;
    var grid = el('div', 'display:grid;grid-template-columns:repeat(auto-fill,minmax(' + (low ? 74 : 82) + 'px,1fr));gap:' + (low ? 4 : 6) + 'px;overflow:auto;min-height:0');
    box.appendChild(grid);
    fill(grid);
    panel.onclick = function (e) { if (e.target === panel) close(); };
    document.body.appendChild(panel);
  }

  window.AiPelitOutfits = {
    setup: function (opts) {
      opts = opts || {};
      outfits = (opts.outfits || []).slice();
      if (opts.halloween !== false) outfits = outfits.concat(HALLOWEEN);
      drawFn = opts.draw || null;
      changeFn = opts.change || null;
      return current();
    },
    current: current,
    get: function (id) { return byId(id) || outfits[0] || null; },
    list: function () { return outfits.slice(); },
    open: open,
    close: close,
    isOpen: function () { return !!panel; },
    halloween: HALLOWEEN,
    season: season,
    head: head,
  };
})();
