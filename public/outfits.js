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
// them out), and come first in the picker around Halloween. The Tylypahka costumes (#321: Harry,
// Ron and Hermione in school robes) follow them (pass `tylypahka: false` to leave them out). Every outfit is a plain palette the
// game's own drawing reads: `skin`, `hair`, `top`, `bottom`, `shoe`, `cape` (a colour or null) and
// `head` (null, or a costume head that head() draws). A game reads what it needs and ignores the
// rest; outfit.halloween is true for a Halloween costume, outfit.tylypahka for a Tylypahka one.
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

  // ---- The Tylypahka costumes (#321): a black school robe (the cape) over the house jumper ----
  // `scarf`, `fur`, `tail`, `belly` and `leg` are for Orava's squirrel, whose fur takes each one's
  // hair colour; head() draws the hair, glasses and scarf in the games with a person.
  var TYLYPAHKA = [
    { id: 'harry', name: 'Harry', emoji: '⚡', skin: '#f1c9a5', hair: '#1d1712', top: '#7f0909', bottom: '#26262c', shoe: '#141414', cape: '#18181e', scarf: '#9b1b1b', head: 'harry',
      fur: '#2e2724', tail: '#241e1b', belly: '#5a4c44', leg: '#1d1816' },
    { id: 'ron', name: 'Ron', emoji: '🐀', skin: '#f6d4bb', hair: '#d4611c', top: '#8a3b2a', bottom: '#26262c', shoe: '#141414', cape: '#18181e', scarf: '#9b1b1b', head: 'ron',
      fur: '#d4611c', tail: '#c4501f', belly: '#f3e1c0', leg: '#a33e15' },
    { id: 'hermione', name: 'Hermione', emoji: '📚', skin: '#efc39e', hair: '#6b3f1f', top: '#6e7480', bottom: '#26262c', shoe: '#141414', cape: '#18181e', scarf: '#9b1b1b', head: 'hermione',
      fur: '#7a4a2a', tail: '#6b3f1f', belly: '#e8d2b4', leg: '#5c3519' },
  ];
  TYLYPAHKA.forEach(function (o) { o.tylypahka = true; });

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
    } else if (kind === 'harry' || kind === 'ron' || kind === 'hermione') {
      wizard(c, kind, r, circle, tri);
    } else {
      circle(0, 0, r, '#f4c7a1');
    }
    ctx.restore();
  }

  // A Tylypahka head, drawn like the costume heads above: the house scarf at the neck, the hair
  // behind and over the face, an eye, a mouth; Harry's round glasses and scar, Ron's freckles,
  // Hermione's bushy hair down past the shoulders.
  function wizard(c, kind, r, circle, tri) {
    var skin = { harry: '#f1c9a5', ron: '#f6d4bb', hermione: '#efc39e' }[kind];
    var hair = { harry: '#1d1712', ron: '#d4611c', hermione: '#6b3f1f' }[kind];
    var i;
    // The scarf: a red band with gold stripes round the neck, its end hanging at the back.
    c.fillStyle = '#9b1b1b';
    c.fillRect(-r * 0.6, r * 0.78, r * 1.15, r * 0.32);
    c.fillRect(-r * 0.62, r * 0.85, r * 0.3, r * 0.95);
    c.fillStyle = '#e8b730';
    c.fillRect(-r * 0.6, r * 0.9, r * 1.15, r * 0.08);
    c.fillRect(-r * 0.62, r * 1.3, r * 0.3, r * 0.1);
    c.fillRect(-r * 0.62, r * 1.55, r * 0.3, r * 0.1);
    if (kind === 'hermione') {
      // Bushy hair behind the head, down past the neck.
      var puffs = [[-0.55, -0.55, 0.6], [-0.75, 0, 0.62], [-0.65, 0.55, 0.58], [-0.2, 0.75, 0.5], [0, -0.8, 0.55], [0.45, -0.7, 0.45], [-0.95, 0.85, 0.42]];
      for (i = 0; i < puffs.length; i++) circle(r * puffs[i][0], r * puffs[i][1], r * puffs[i][2], hair);
    } else {
      circle(-r * 0.3, -r * 0.2, r * 0.85, hair); // the back of the head
    }
    circle(r * 0.05, r * 0.02, r * 0.92, skin);
    c.fillStyle = hair;
    c.beginPath(); c.arc(0, 0, r * 1.02, Math.PI * 0.95, Math.PI * 1.75); c.lineTo(r * 0.1, -r * 0.35); c.closePath(); c.fill();
    if (kind === 'harry') {
      // Messy black tufts on top and a fringe over the forehead.
      for (i = 0; i < 5; i++) {
        var a = Math.PI * (1.05 + i * 0.17), x = Math.cos(a) * r * 0.95, y = Math.sin(a) * r * 0.95;
        tri([x - r * 0.2, y + r * 0.1], [x + r * 0.2, y + r * 0.1], [x + Math.cos(a) * r * 0.35, y + Math.sin(a) * r * 0.35 - r * 0.05], hair);
      }
      tri([r * 0.05, -r * 0.8], [r * 0.6, -r * 0.75], [r * 0.25, -r * 0.4], hair);
      tri([r * 0.45, -r * 0.8], [r * 0.85, -r * 0.55], [r * 0.7, -r * 0.42], hair);
    } else if (kind === 'ron') {
      // A longer red fringe, and hair down over the ear.
      tri([r * 0.0, -r * 0.85], [r * 0.85, -r * 0.6], [r * 0.45, -r * 0.35], hair);
      circle(-r * 0.5, r * 0.02, r * 0.42, hair);
    } else {
      tri([r * 0.0, -r * 0.9], [r * 0.9, -r * 0.55], [r * 0.5, -r * 0.3], hair);
    }
    circle(r * 0.55, -r * 0.05, Math.max(1, r * 0.11), '#2a1e14'); // the eye
    c.strokeStyle = '#9a4a3a'; c.lineWidth = Math.max(1, r * 0.07);
    c.beginPath(); c.moveTo(r * 0.45, r * 0.48); c.lineTo(r * 0.75, r * 0.45); c.stroke(); // the mouth
    if (kind === 'harry') {
      // The round glasses, their arm back to the ear, and the lightning scar.
      c.strokeStyle = '#1a1a1a'; c.lineWidth = Math.max(1, r * 0.08);
      c.beginPath(); c.arc(r * 0.55, -r * 0.05, r * 0.25, 0, 7); c.stroke();
      c.beginPath(); c.moveTo(r * 0.3, -r * 0.08); c.lineTo(-r * 0.25, -r * 0.15); c.stroke();
      c.strokeStyle = '#c0392b'; c.lineWidth = Math.max(1, r * 0.07);
      c.beginPath(); c.moveTo(r * 0.42, -r * 0.62); c.lineTo(r * 0.3, -r * 0.48); c.lineTo(r * 0.44, -r * 0.46); c.lineTo(r * 0.32, -r * 0.32); c.stroke();
    } else if (kind === 'ron') {
      for (i = 0; i < 4; i++) circle(r * (0.3 + (i % 2) * 0.18 + i * 0.05), r * (0.2 + (i % 2) * 0.1), Math.max(0.6, r * 0.05), '#c47a4a');
    }
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
    // A low, wide screen gets smaller cards, so every group fits without scrolling.
    var cw = innerHeight < 500 ? 52 : 72, ch = innerHeight < 500 ? 50 : 80;
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
    var now = current(), own = [], costumes = [], school = [];
    outfits.forEach(function (o) { (o.halloween ? costumes : o.tylypahka ? school : own).push(o); });
    var groups = season() ? [['🎃 Halloween', costumes], ['Tavalliset', own], ['⚡ Tylypahka', school]]
      : [['Tavalliset', own], ['⚡ Tylypahka', school], ['🎃 Halloween', costumes]];
    groups.forEach(function (g) {
      if (!g[1].length) return;
      // On a low screen the group's name is a cell before its cards, not a row of its own (#321:
      // a third group's row pushed the last cards off a sideways phone).
      grid.appendChild(innerHeight < 500
        ? el('div', 'display:flex;align-items:center;justify-content:center;text-align:center;font-weight:700;font-size:12px;color:#cfd6ee', g[0])
        : el('div', 'grid-column:1/-1;font-weight:700;color:#cfd6ee;margin-top:4px', g[0]));
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
    var grid = el('div', 'display:grid;grid-template-columns:repeat(auto-fill,minmax(' + (low ? 64 : 82) + 'px,1fr));gap:' + (low ? 4 : 6) + 'px;overflow:auto;min-height:0');
    box.appendChild(grid);
    fill(grid);
    panel.onclick = function (e) { if (e.target === panel) close(); };
    document.body.appendChild(panel);
  }

  // Turning the phone with the picker open lays it out again for the new shape.
  var wasWide = innerWidth > innerHeight;
  addEventListener('resize', function () {
    var wide = innerWidth > innerHeight;
    if (panel && wide !== wasWide) open();
    wasWide = wide;
  });

  window.AiPelitOutfits = {
    setup: function (opts) {
      opts = opts || {};
      outfits = (opts.outfits || []).slice();
      if (opts.halloween !== false) outfits = outfits.concat(HALLOWEEN);
      if (opts.tylypahka !== false) outfits = outfits.concat(TYLYPAHKA);
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
    tylypahka: TYLYPAHKA,
    season: season,
    head: head,
  };
})();
