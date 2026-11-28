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
// The Christmas costumes (#473: Joulupukki, Tonttu, Poro, Lumiukko, Piparkakku; outfit.joulu) are
// offered only in November and December, first from 3 November (pass `joulu: false` to leave them
// out; Orava gets none unless it passes `joulu: true`, as its v6 squirrel draws no costume head for
// them). Outside the season current() wears the game's default instead, but the saved choice is
// kept, so the costume is back next November; get(id) finds them all year, for a friend in a room.
//
// The choice is saved per game on the phone (ai-pelit:_asut:<slug>), so every version of a game
// shares it. AiPelitOutfits.current() is the outfit now; .get(id) is any outfit by id (for a
// friend's figure in a room: send current().id with the player); .open() shows the picker.
//
// Shared choice (#311): with data-share="<group>" on the script tag, the choice is one for every
// game of that group (ai-pelit:_asut:<group>), so the athletics events and Ottelu wear the same
// outfit. The first time a phone opens one of them, the choice made before in one game of the
// group (an older version, its own key) becomes the group's: the first found in SHARED_FROM's
// fixed order, so every game shows the same one, whichever is opened first. A pick is saved to
// both keys, so the game's older versions (which read only their own) follow it too.
// AiPelitOutfits.yleisurheilu is the athletics events' common everyday set: pass it as `outfits`,
// so an id picked in one event is found in every other.
//
// The 3D games (#568) share one choice with data-share="3d" and pass AiPelitOutfits.kolmiD (their
// common everyday set, Pulkkamäki's winter wear and two masked hero suits; head 'naamio' is the hero
// mask), usually through AiPelitAsut3d.setup() in lib/asut3d-*/, which also builds the 3D pieces.
// A pick that could not be saved (full or blocked storage) is still worn for the page's life.
// Later versions load this same file, so it must stay compatible with every version that uses it.
(function () {
  'use strict';
  var script = document.currentScript;
  var GAME = (script && script.getAttribute('data-game')) || '';
  var SHARE = (script && script.getAttribute('data-share')) || '';
  // The athletics events (#469) show the shared front figure in the picker; other games their own.
  var FIGURE = SHARE === 'yleisurheilu' || SHARE === '3d';
  var OWN = 'ai-pelit:_asut:' + GAME;
  var KEY = SHARE ? 'ai-pelit:_asut:' + SHARE : OWN;
  // The games whose own earlier choice a group takes over, in order (#311): those that had
  // outfits before the group shared one, the longest-dressed first.
  var SHARED_FROM = { yleisurheilu: ['keihas', 'aitajuoksu', 'kuula'], '3d': ['pulkkamaki'] };
  function adopt() {
    if (!SHARE || load(KEY, null) !== null) return;
    var from = (SHARED_FROM[SHARE] || []).concat([GAME]);
    for (var i = 0; i < from.length; i++) {
      var o = byId(load('ai-pelit:_asut:' + from[i], ''));
      // Storage full: still worn on this page, as a pick that could not be saved is.
      if (o) { if (!save(KEY, o.id)) unsaved = o; return; }
    }
  }
  function load(k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }

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

  // ---- The Christmas costumes (#473), in the picker in November and December ----
  var JOULU = [
    { id: 'joulupukki', name: 'Joulupukki', emoji: '🎅', skin: '#f3c9a8', hair: '#f4f4f4', top: '#c8202f', bottom: '#c8202f', shoe: '#1a1a1a', cape: null, head: 'pukki' },
    { id: 'tonttu', name: 'Tonttu', emoji: '🧝', skin: '#f3c9a8', hair: '#8a5a2b', top: '#d42a2a', bottom: '#6f6f78', shoe: '#3a2a1a', cape: null, head: 'tonttu' },
    { id: 'poro', name: 'Poro', emoji: '🦌', skin: '#8a5a36', hair: '#6b4428', top: '#8a5a36', bottom: '#6b4428', shoe: '#2a1d12', cape: null, head: 'poro' },
    { id: 'lumiukko', name: 'Lumiukko', emoji: '⛄', skin: '#f6f8fc', hair: '#f6f8fc', top: '#f6f8fc', bottom: '#e6ebf4', shoe: '#d6dde9', cape: null, head: 'lumiukko', stripe: '#d42a2a' },
    { id: 'piparkakku', name: 'Piparkakku', emoji: '🍪', skin: '#b8733a', hair: '#b8733a', top: '#b8733a', bottom: '#a8652f', shoe: '#ffffff', cape: null, head: 'pipari', stripe: '#ffffff' },
  ];
  JOULU.forEach(function (o) { o.joulu = true; });

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

  // ---- The athletics events' everyday kits (#311), one set for all of them ----
  // 'perus' leaves the shirt (top: null) to the game, which gives it the competitor's own colour.
  // The ids are those the events had on their own (Keihäs, Kuula, Aitajuoksu), so a choice made
  // there is found here too.
  var YLEISURHEILU = [
    { id: 'perus', name: 'Perus', skin: '#c98a62', hair: 'rgba(0,0,0,.25)', top: null, bottom: '#1b1b2f', shoe: '#ffffff', cape: null, head: null },
    { id: 'suomi', name: 'Sinivalkoinen', skin: '#e8b48f', hair: '#e2c27a', top: '#f4f6fa', bottom: '#1f4fa8', shoe: '#1f4fa8', stripe: '#1f4fa8', cape: null, head: null },
    { id: 'musta', name: 'Musta', skin: '#8d5a3b', hair: '#111111', top: '#1e1e22', bottom: '#1e1e22', shoe: '#f2c230', cape: null, head: null },
    { id: 'punainen', name: 'Punainen', skin: '#f0c5a0', hair: '#5a3418', top: '#d23a2f', bottom: '#f4f6fa', shoe: '#d23a2f', cape: null, head: null },
    { id: 'vihrea', name: 'Vihreä', skin: '#f0c5a0', hair: '#9a4a22', top: '#27a35a', bottom: '#f4f6fa', shoe: '#27a35a', cape: null, head: null },
    { id: 'kulta', name: 'Kulta', skin: '#e0a98a', hair: '#6b3e26', top: '#e3b23c', bottom: '#f4f1e8', shoe: '#e3b23c', cape: null, head: null },
    { id: 'neon', name: 'Neon', skin: '#8d5a3b', hair: '#161616', top: '#1a1a1a', bottom: '#1a1a1a', shoe: '#c8ff2e', stripe: '#c8ff2e', cape: null, head: null },
  ];

  // ---- The 3D games' everyday set (#568), one for all of them ----
  // Pulkkamäki's winter wear first (the ids it had on its own, so its riders keep their pick), then
  // the hero suits, whose head is the mask ('naamio': `mask` the mask, `mitt` the gloves). `pipo` and
  // `tupsu` are a beanie and its bobble; a game without a beanie ignores them.
  var KOLMID = [
    { id: 'haalari', name: 'Toppahaalari', skin: '#f0c8a0', hair: '#5a3418', top: '#2f6fd0', bottom: '#2f6fd0', shoe: '#1a1a22', pipo: '#d42a2a', tupsu: '#ffffff', stripe: '#ffd23a', cape: null, head: null },
    { id: 'punainen', name: 'Punainen', skin: '#e8b48f', hair: '#2a1a10', top: '#d42a2a', bottom: '#2a2a33', shoe: '#2a2a33', pipo: '#ffffff', tupsu: '#d42a2a', cape: null, head: null },
    { id: 'vihrea', name: 'Vihreä', skin: '#c98a62', hair: '#111111', top: '#27a35a', bottom: '#1b3a2a', shoe: '#111', pipo: '#ffd23a', tupsu: '#27a35a', stripe: '#ffffff', cape: null, head: null },
    { id: 'liila', name: 'Liila', skin: '#f6d4bb', hair: '#d4611c', top: '#8a4ad4', bottom: '#f4f6fa', shoe: '#8a4ad4', pipo: '#f4f6fa', tupsu: '#8a4ad4', cape: null, head: null },
    { id: 'musta', name: 'Musta', skin: '#8d5a3b', hair: '#161616', top: '#1e1e22', bottom: '#1e1e22', shoe: '#c8ff2e', pipo: '#c8ff2e', tupsu: '#1e1e22', stripe: '#c8ff2e', cape: null, head: null },
    { id: 'sankari', name: 'Sankari', emoji: '🕸️', skin: '#e2b48c', hair: '#1b1f2e', top: '#1fb5a8', bottom: '#26324a', shoe: '#f4f4f4', mitt: '#f4f4f4', mask: '#1b1f2e', cape: null, head: 'naamio' },
    { id: 'yosankari', name: 'Yösankari', emoji: '🌙', skin: '#e2b48c', hair: '#2a2a30', top: '#22222a', bottom: '#2a2a30', shoe: '#ffd23a', mitt: '#ffd23a', mask: '#2a2a30', stripe: '#ffd23a', cape: null, head: 'naamio' },
  ];

  // Around Halloween (20 October to 2 November) the costumes come first.
  function season(d) {
    d = d || new Date();
    var m = d.getMonth() + 1, day = d.getDate();
    return (m === 10 && day >= 20) || (m === 11 && day <= 2);
  }

  // The Christmas season (#473): November and December, by the phone's own date.
  function jouluSeason(d) {
    d = d || new Date();
    var m = d.getMonth() + 1;
    return m === 11 || m === 12;
  }

  var outfits = [], drawFn = null, changeFn = null;
  // A pick whose save failed (#568): worn until the page closes. A pick that was saved clears it, so
  // an open page always follows the saved key, which another game may have changed since.
  var unsaved = null;
  function byId(id) {
    for (var i = 0; i < outfits.length; i++) if (outfits[i].id === id) return outfits[i];
    return null;
  }
  // A Christmas costume is worn only in its season; the saved choice stays for the next one.
  function current() {
    var o = unsaved || byId(load(KEY, ''));
    if (o && o.joulu && !jouluSeason()) o = null;
    return o || outfits[0] || null;
  }

  // ---- Costume heads: drawn at (x, y), radius r, the face towards +x (or -x when face < 0) ----
  // face 'front' draws it seen from the front (frontHead); tilt turns it (radians, #469).
  function head(ctx, kind, x, y, r, face, tilt) {
    if (face === 'front') { frontHead(ctx, { head: kind }, x, y, r, { tilt: tilt || 0 }); return; }
    var f = face < 0 ? -1 : 1;
    ctx.save();
    ctx.translate(x, y);
    if (tilt) ctx.rotate(tilt);
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
    } else if (kind === 'pukki') {
      // Joulupukki: a red cap with a white trim, its tip and bobble hanging back, a white beard.
      circle(0, 0, r, '#f3c9a8');
      c.fillStyle = '#f4f4f4'; c.beginPath(); c.moveTo(-r * 0.2, r * 0.05); c.quadraticCurveTo(r * 0.2, r * 1.6, r * 1.05, r * 0.15); c.lineTo(r * 0.6, r * 0.3); c.closePath(); c.fill();
      circle(r * 0.5, -r * 0.1, Math.max(1, r * 0.12), '#2a1e14');
      circle(r * 0.95, r * 0.12, r * 0.17, '#e07a6a');
      c.fillStyle = '#c8202f'; c.beginPath(); c.moveTo(-r * 0.95, -r * 0.35); c.quadraticCurveTo(-r * 0.1, -r * 1.75, r * 0.95, -r * 0.35); c.closePath(); c.fill();
      tri([-r * 0.6, -r * 1.05], [-r * 0.05, -r * 1.25], [-r * 1.3, -r * 0.55], '#c8202f');
      circle(-r * 1.3, -r * 0.5, r * 0.24, '#f4f4f4');
      c.fillStyle = '#f4f4f4'; c.beginPath(); c.ellipse(0, -r * 0.38, r * 1.02, r * 0.2, -0.05, 0, 7); c.fill();
    } else if (kind === 'tonttu') {
      // Tonttu: a tall pointed red cap leaning back, rosy cheeks.
      circle(0, 0, r, '#f3c9a8');
      circle(r * 0.5, -r * 0.08, Math.max(1, r * 0.12), '#2a1e14');
      circle(r * 0.45, r * 0.32, r * 0.18, 'rgba(230,90,90,.55)');
      c.fillStyle = '#8a5a2b'; c.fillRect(-r * 0.95, -r * 0.35, r * 0.55, r * 0.75);
      tri([-r * 0.95, -r * 0.4], [r * 0.9, -r * 0.4], [-r * 0.9, -r * 2.3], '#d42a2a');
      circle(-r * 0.9, -r * 2.3, r * 0.22, '#f4f4f4');
      c.fillStyle = '#f4f4f4'; c.fillRect(-r * 1.0, -r * 0.55, r * 1.95, r * 0.22);
    } else if (kind === 'poro') {
      // Poro: a brown head with a long muzzle, a red nose, an ear and branching antlers.
      c.strokeStyle = '#d8c39a'; c.lineWidth = Math.max(1, r * 0.16); c.lineCap = 'round';
      c.beginPath();
      c.moveTo(-r * 0.1, -r * 0.8); c.lineTo(-r * 0.4, -r * 1.9); c.moveTo(-r * 0.25, -r * 1.35); c.lineTo(r * 0.15, -r * 1.75);
      c.moveTo(-r * 0.35, -r * 1.7); c.lineTo(-r * 0.85, -r * 2.0); c.stroke();
      circle(0, 0, r, '#8a5a36');
      c.fillStyle = '#9c6a42'; c.beginPath(); c.ellipse(r * 0.75, r * 0.25, r * 0.6, r * 0.42, 0.1, 0, 7); c.fill();
      circle(r * 1.3, r * 0.2, r * 0.24, '#e0242a');
      circle(r * 0.35, -r * 0.2, Math.max(1, r * 0.12), '#1a120c');
      c.fillStyle = '#6b4428'; c.beginPath(); c.ellipse(-r * 0.55, -r * 0.6, r * 0.18, r * 0.38, -0.7, 0, 7); c.fill();
    } else if (kind === 'lumiukko') {
      // Lumiukko: a snowball head, coal eye, a carrot nose and a black top hat.
      circle(0, 0, r, '#f6f8fc');
      circle(r * 0.45, -r * 0.15, Math.max(1, r * 0.13), '#1a1a1a');
      tri([r * 0.8, r * 0.0], [r * 0.8, r * 0.3], [r * 1.6, r * 0.15], '#f07a1a');
      [0.3, 0.5, 0.7].forEach(function (k) { circle(r * k, r * 0.55 - Math.abs(k - 0.5) * r * 0.3, Math.max(0.6, r * 0.07), '#1a1a1a'); });
      c.fillStyle = '#1a1a1a'; c.fillRect(-r * 1.0, -r * 0.82, r * 2.0, r * 0.2);
      c.fillRect(-r * 0.62, -r * 1.85, r * 1.24, r * 1.08);
      c.fillStyle = '#d42a2a'; c.fillRect(-r * 0.62, -r * 1.0, r * 1.24, r * 0.18);
    } else if (kind === 'pipari') {
      // Piparkakku: a gingerbread head with white icing: an eye and a smile, a wavy edge.
      circle(0, 0, r, '#b8733a');
      circle(r * 0.5, -r * 0.15, Math.max(1, r * 0.13), '#ffffff');
      c.strokeStyle = '#ffffff'; c.lineWidth = Math.max(1, r * 0.1); c.lineCap = 'round';
      c.beginPath(); c.arc(r * 0.4, r * 0.05, r * 0.42, 0.1 * Math.PI, 0.6 * Math.PI); c.stroke();
      c.beginPath(); c.arc(0, 0, r * 0.84, 0, 7); c.setLineDash([r * 0.18, r * 0.14]); c.stroke(); c.setLineDash([]);
      circle(r * 0.62, r * 0.32, r * 0.1, '#e0242a');
    } else if (kind === 'naamio') {
      // The hero mask (#568): a dark head, the hood's edge behind it, a white lens.
      circle(-r * 0.2, 0, r * 1.02, '#1fb5a8');
      circle(0, 0, r, '#1b1f2e');
      c.fillStyle = '#ffffff'; c.beginPath(); c.ellipse(r * 0.5, -r * 0.1, r * 0.26, r * 0.17, -0.2, 0, 7); c.fill();
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
  // ---- Seen from the front (#469): heads with poses, and a whole athlete ----
  // A head seen from the front at (x, y), radius r. opt: tilt (radians), lx -1…1 (turned left …
  // right), ly -1…1 (looking up … down), mouth 'smile' | 'open' | 'o'.
  function frontHead(ctx, L, x, y, r, opt) {
    opt = opt || {};
    var kind = L.head || null, c = ctx;
    var fx = (opt.lx || 0) * r * 0.3, fy = (opt.ly || 0) * r * 0.22;
    c.save(); c.translate(x, y); if (opt.tilt) c.rotate(opt.tilt);
    function circle(cx, cy, rr, col) { c.fillStyle = col; c.beginPath(); c.arc(cx, cy, rr, 0, 7); c.fill(); }
    function ell(cx, cy, rx, ry, col) { c.fillStyle = col; c.beginPath(); c.ellipse(cx, cy, rx, ry, 0, 0, 7); c.fill(); }
    function tri(a, b, cc, col) { c.fillStyle = col; c.beginPath(); c.moveTo(a[0], a[1]); c.lineTo(b[0], b[1]); c.lineTo(cc[0], cc[1]); c.closePath(); c.fill(); }
    function eyes(col, s, dy) {
      var er = Math.max(1, r * (s || 0.12));
      [-1, 1].forEach(function (d) {
        circle(fx + d * r * 0.36, fy - r * 0.05 + (dy || 0), er, col);
        if (er > 2) circle(fx + d * r * 0.36 + er * 0.35 + (opt.lx || 0) * er * 0.3, fy - r * 0.05 - er * 0.35 + (dy || 0), er * 0.35, 'rgba(255,255,255,.8)');
      });
    }
    function mouth(col) {
      var m = opt.mouth || 'smile';
      if (m === 'open') { ell(fx, fy + r * 0.42, r * 0.22, r * 0.17, '#5a1f1f'); ell(fx, fy + r * 0.5, r * 0.12, r * 0.06, '#e07a7a'); return; }
      if (m === 'o') { ell(fx, fy + r * 0.45, r * 0.1, r * 0.12, '#5a1f1f'); return; }
      c.strokeStyle = col || 'rgba(0,0,0,.55)'; c.lineWidth = Math.max(1, r * 0.1); c.lineCap = 'round';
      c.beginPath(); c.arc(fx, fy + r * 0.18, r * 0.32, 0.2 * Math.PI, 0.8 * Math.PI); c.stroke();
    }
    if (kind === 'pumpkin') {
      ell(0, 0, r * 1.25, r * 1.1, '#e8711a');
      c.strokeStyle = '#b8520c'; c.lineWidth = Math.max(1, r * 0.1);
      [-0.45, 0, 0.45].forEach(function (k) { c.beginPath(); c.ellipse(r * k + fx * 0.3, 0, r * 0.42, r * 1.05, 0, 0, 7); c.stroke(); });
      c.fillStyle = '#3f6b22'; c.fillRect(-r * 0.12, -r * 1.4, r * 0.24, r * 0.4);
      [-1, 1].forEach(function (d) { tri([fx + d * r * 0.2, fy - r * 0.05], [fx + d * r * 0.65, fy - r * 0.05], [fx + d * r * 0.42, fy - r * 0.45], '#ffd23f'); });
      c.fillStyle = '#ffd23f'; c.beginPath();
      c.moveTo(fx - r * 0.6, fy + r * 0.25); c.lineTo(fx + r * 0.6, fy + r * 0.25); c.lineTo(fx + r * 0.45, fy + r * 0.62);
      c.lineTo(fx + r * 0.2, fy + r * 0.45); c.lineTo(fx, fy + r * 0.64); c.lineTo(fx - r * 0.2, fy + r * 0.45); c.lineTo(fx - r * 0.45, fy + r * 0.62);
      c.closePath(); c.fill();
    } else if (kind === 'witch') {
      c.fillStyle = '#2a2a2a'; c.fillRect(-r * 1.05, -r * 0.3, r * 2.1, r * 1.35);
      circle(0, 0, r, '#9fd17a');
      eyes('#1b1b1b', 0.13);
      tri([fx, fy + r * 0.0], [fx - r * 0.13, fy + r * 0.32], [fx + r * 0.13, fy + r * 0.32], '#86bf5e');
      mouth('#3d5a26');
      ell(0, -r * 0.62, r * 1.6, r * 0.24, '#1b1426');
      tri([-r * 0.75, -r * 0.65], [r * 0.75, -r * 0.65], [r * 0.25, -r * 2.5], '#1b1426');
      c.fillStyle = '#8a4fd1'; c.fillRect(-r * 0.68, -r * 1.0, r * 1.36, r * 0.28);
    } else if (kind === 'ghost') {
      circle(0, 0, r * 1.08, '#f4f4f8');
      [-1, 1].forEach(function (d) { ell(fx + d * r * 0.36, fy - r * 0.2, r * 0.16, r * 0.26, '#1b1b24'); });
      ell(fx, fy + r * 0.42, r * 0.15, r * 0.2, '#1b1b24');
    } else if (kind === 'skull') {
      circle(0, -r * 0.08, r, '#ece6d6');
      c.fillStyle = '#ece6d6'; c.fillRect(-r * 0.5, r * 0.35, r * 1.0, r * 0.55);
      [-1, 1].forEach(function (d) { circle(fx + d * r * 0.38, fy - r * 0.1, r * 0.26, '#141414'); });
      tri([fx, fy + r * 0.15], [fx - r * 0.12, fy + r * 0.38], [fx + r * 0.12, fy + r * 0.38], '#141414');
      c.strokeStyle = '#141414'; c.lineWidth = Math.max(1, r * 0.07); c.beginPath();
      for (var i = 0; i < 5; i++) { var tx = fx + r * (-0.36 + i * 0.18); c.moveTo(tx, r * 0.55); c.lineTo(tx, r * 0.86); }
      c.stroke();
    } else if (kind === 'vampire') {
      [-1, 1].forEach(function (d) { tri([d * r * 0.7, r * 0.6], [d * r * 1.45, -r * 0.45], [d * r * 0.4, r * 1.0], '#9b1024'); });
      circle(0, 0, r, '#e8e0ec');
      c.fillStyle = '#121212'; c.beginPath(); c.arc(0, -r * 0.05, r * 1.04, Math.PI * 1.0, Math.PI * 2.0);
      c.lineTo(r * 0.85, -r * 0.3); c.lineTo(0, -r * 0.45); c.lineTo(-r * 0.85, -r * 0.3); c.closePath(); c.fill();
      eyes('#c4102a', 0.13);
      c.strokeStyle = '#7a0d1c'; c.lineWidth = Math.max(1, r * 0.08);
      c.beginPath(); c.moveTo(fx - r * 0.3, fy + r * 0.45); c.lineTo(fx + r * 0.3, fy + r * 0.45); c.stroke();
      [-1, 1].forEach(function (d) { tri([fx + d * r * 0.08, fy + r * 0.47], [fx + d * r * 0.22, fy + r * 0.47], [fx + d * r * 0.15, fy + r * 0.7], '#fff'); });
    } else if (kind === 'mummy') {
      circle(0, 0, r, '#e9dfc4');
      c.strokeStyle = '#bfae86'; c.lineWidth = Math.max(1, r * 0.12);
      c.save(); c.beginPath(); c.arc(0, 0, r, 0, 7); c.clip(); c.beginPath();
      for (var k = -3; k <= 3; k++) { c.moveTo(-r * 1.2, k * r * 0.32 - r * 0.2); c.lineTo(r * 1.2, k * r * 0.32 + r * 0.1); }
      c.stroke(); c.restore();
      c.fillStyle = '#2a2018'; c.fillRect(fx - r * 0.7, fy - r * 0.2, r * 1.4, r * 0.28);
      eyes('#e8ff6a', 0.09, r * 0.04);
    } else if (kind === 'pukki') {
      circle(0, 0, r, '#f3c9a8');
      eyes('#2a1e14', 0.11);
      c.fillStyle = '#f4f4f4'; c.beginPath(); c.moveTo(-r * 0.92, r * 0.05); c.quadraticCurveTo(fx, r * 1.75, r * 0.92, r * 0.05);
      c.quadraticCurveTo(fx, r * 0.55, -r * 0.92, r * 0.05); c.fill();
      ell(fx - r * 0.18, fy + r * 0.3, r * 0.22, r * 0.1, '#f4f4f4'); ell(fx + r * 0.18, fy + r * 0.3, r * 0.22, r * 0.1, '#f4f4f4');
      circle(fx, fy + r * 0.18, r * 0.15, '#e07a6a');
      c.fillStyle = '#c8202f'; c.beginPath(); c.moveTo(-r * 0.95, -r * 0.4); c.quadraticCurveTo(0, -r * 1.7, r * 0.95, -r * 0.4); c.closePath(); c.fill();
      tri([r * 0.1, -r * 1.05], [r * 0.6, -r * 0.85], [r * 1.25, -r * 0.35], '#c8202f');
      circle(r * 1.25, -r * 0.3, r * 0.22, '#f4f4f4');
      ell(0, -r * 0.42, r * 1.05, r * 0.2, '#f4f4f4');
    } else if (kind === 'tonttu') {
      [-1, 1].forEach(function (d) { circle(d * r * 0.95 - fx * 0.4, r * 0.08, r * 0.2, '#f3c9a8'); });
      circle(0, 0, r, '#f3c9a8');
      [-1, 1].forEach(function (d) { circle(fx + d * r * 0.5, fy + r * 0.25, r * 0.16, 'rgba(230,90,90,.5)'); });
      eyes('#2a1e14', 0.11);
      mouth('#9a4a3a');
      tri([-r * 0.95, -r * 0.45], [r * 0.95, -r * 0.45], [r * 0.55, -r * 2.35], '#d42a2a');
      circle(r * 0.55, -r * 2.35, r * 0.22, '#f4f4f4');
      c.fillStyle = '#f4f4f4'; c.fillRect(-r * 1.0, -r * 0.6, r * 2.0, r * 0.22);
    } else if (kind === 'poro') {
      c.strokeStyle = '#d8c39a'; c.lineWidth = Math.max(1, r * 0.15); c.lineCap = 'round';
      [-1, 1].forEach(function (d) {
        c.beginPath(); c.moveTo(d * r * 0.4, -r * 0.75); c.lineTo(d * r * 0.85, -r * 1.85);
        c.moveTo(d * r * 0.6, -r * 1.25); c.lineTo(d * r * 1.2, -r * 1.4); c.moveTo(d * r * 0.75, -r * 1.6); c.lineTo(d * r * 0.4, -r * 2.0); c.stroke();
        c.fillStyle = '#6b4428'; c.beginPath(); c.ellipse(d * r * 1.0, -r * 0.35, r * 0.4, r * 0.17, d * 0.4, 0, 7); c.fill();
      });
      circle(0, 0, r, '#8a5a36');
      ell(fx, fy + r * 0.4, r * 0.55, r * 0.42, '#9c6a42');
      eyes('#1a120c', 0.12, -r * 0.08);
      circle(fx, fy + r * 0.28, r * 0.24, '#e0242a');
      if (r > 6) circle(fx + r * 0.07, fy + r * 0.21, r * 0.07, 'rgba(255,255,255,.7)');
      mouth('#3a2414');
    } else if (kind === 'lumiukko') {
      circle(0, 0, r, '#f6f8fc');
      eyes('#1a1a1a', 0.12);
      tri([fx - r * 0.1, fy + r * 0.08], [fx + r * 0.1, fy + r * 0.08], [fx + r * 0.05, fy + r * 0.6], '#f07a1a');
      [-0.3, -0.1, 0.1, 0.3].forEach(function (k) { circle(fx + r * k, fy + r * (0.62 - Math.abs(k) * 0.4), Math.max(0.6, r * 0.06), '#1a1a1a'); });
      c.fillStyle = '#1a1a1a'; c.fillRect(-r * 1.05, -r * 0.85, r * 2.1, r * 0.2);
      c.fillRect(-r * 0.65, -r * 1.9, r * 1.3, r * 1.1);
      c.fillStyle = '#d42a2a'; c.fillRect(-r * 0.65, -r * 1.02, r * 1.3, r * 0.18);
    } else if (kind === 'pipari') {
      circle(0, 0, r, '#b8733a');
      c.strokeStyle = '#ffffff'; c.lineWidth = Math.max(1, r * 0.09); c.lineCap = 'round';
      c.beginPath(); c.arc(0, 0, r * 0.84, 0, 7); c.setLineDash([r * 0.18, r * 0.14]); c.stroke(); c.setLineDash([]);
      eyes('#ffffff', 0.12);
      mouth('#ffffff');
      [-1, 1].forEach(function (d) { circle(fx + d * r * 0.55, fy + r * 0.25, r * 0.1, '#e0242a'); });
    } else if (kind === 'naamio') {
      // The hero mask (#568): the hood in the suit's colour, the dark mask, two white lenses.
      circle(0, r * 0.05, r * 1.12, L.top || '#1fb5a8');
      circle(fx * 0.3, 0, r, L.mask || '#1b1f2e');
      [-1, 1].forEach(function (d) { c.fillStyle = '#ffffff'; c.beginPath(); c.ellipse(fx + d * r * 0.38, fy - r * 0.08, r * 0.28, r * 0.19, d * 0.35, 0, 7); c.fill(); });
    } else if (kind === 'harry' || kind === 'ron' || kind === 'hermione') {
      var skin = { harry: '#f1c9a5', ron: '#f6d4bb', hermione: '#efc39e' }[kind];
      var hair = { harry: '#1d1712', ron: '#d4611c', hermione: '#6b3f1f' }[kind];
      if (kind === 'hermione') [[-0.85, -0.2, 0.6], [0.85, -0.2, 0.6], [-0.95, 0.5, 0.55], [0.95, 0.5, 0.55], [-0.5, -0.75, 0.55], [0.5, -0.75, 0.55], [0, -0.9, 0.5]].forEach(function (p) { circle(r * p[0], r * p[1], r * p[2], hair); });
      else circle(0, -r * 0.12, r * 1.04, hair);
      c.fillStyle = '#9b1b1b'; c.fillRect(-r * 0.7, r * 0.82, r * 1.4, r * 0.32);
      c.fillStyle = '#e8b730'; c.fillRect(-r * 0.7, r * 0.93, r * 1.4, r * 0.08);
      circle(0, r * 0.04, r * 0.92, skin);
      c.fillStyle = hair; c.beginPath(); c.arc(0, -r * 0.05, r * 0.98, Math.PI * 1.05, Math.PI * 1.95);
      c.lineTo(r * 0.5, -r * 0.45); c.lineTo(r * 0.1, -r * 0.55); c.lineTo(-r * 0.3, -r * 0.4); c.closePath(); c.fill();
      if (kind === 'harry') for (var j = 0; j < 5; j++) { var a = Math.PI * (1.1 + j * 0.2); tri([Math.cos(a) * r * 0.75, Math.sin(a) * r * 0.75], [Math.cos(a + 0.3) * r * 0.85, Math.sin(a + 0.3) * r * 0.85], [Math.cos(a + 0.1) * r * 1.25, Math.sin(a + 0.1) * r * 1.25], hair); }
      eyes('#2a1e14', 0.11);
      mouth('#9a4a3a');
      if (kind === 'harry') {
        c.strokeStyle = '#1a1a1a'; c.lineWidth = Math.max(1, r * 0.08);
        [-1, 1].forEach(function (d) { c.beginPath(); c.arc(fx + d * r * 0.36, fy - r * 0.05, r * 0.24, 0, 7); c.stroke(); });
        c.beginPath(); c.moveTo(fx - r * 0.12, fy - r * 0.07); c.lineTo(fx + r * 0.12, fy - r * 0.07); c.stroke();
        c.strokeStyle = '#c0392b'; c.lineWidth = Math.max(1, r * 0.07);
        c.beginPath(); c.moveTo(fx + r * 0.1, -r * 0.62); c.lineTo(fx - r * 0.02, -r * 0.5); c.lineTo(fx + r * 0.1, -r * 0.47); c.lineTo(fx - r * 0.02, -r * 0.34); c.stroke();
      } else if (kind === 'ron') {
        [-1, 1].forEach(function (d) { for (var q = 0; q < 3; q++) circle(fx + d * r * (0.42 + q * 0.1), fy + r * (0.18 + (q % 2) * 0.08), Math.max(0.6, r * 0.05), '#c47a4a'); });
      }
    } else {
      // A plain head: ears, the face, hair on top and down the sides.
      var sk = L.skin || '#f0c5a0';
      [-1, 1].forEach(function (d) { circle(d * r * 0.95 - fx * 0.4, r * 0.08, r * 0.2, sk); });
      circle(0, 0, r, sk);
      if (L.hair) {
        c.fillStyle = L.hair; c.beginPath(); c.arc(0, 0, r * 1.04, Math.PI * 0.97, Math.PI * 2.03);
        c.quadraticCurveTo(r * 0.7, -r * 0.55, fx * 0.5 + r * 0.1, -r * 0.5); c.quadraticCurveTo(-r * 0.6, -r * 0.6, -r * 1.02, -r * 0.05); c.closePath(); c.fill();
      }
      eyes('rgba(20,20,30,.85)', 0.11);
      mouth();
    }
    c.restore();
  }
  // An outfit as the front figure wears it: the athletics 'perus' kit has no top of its own (each
  // event colours it), so the figure gets a red singlet and brown hair.
  function dress(o) { return o.top ? o : Object.assign({}, o, { top: '#e63946', hair: '#3b2a1a' }); }
  // A whole figure from the front, feet at (fx, fy), h tall. L: the outfit's palette (skin, hair,
  // top, bottom, shoe, cape, head, stripe, bones, halloween). p: up 0…1 (arms down … up in a V),
  // step -1…1, look { lx, ly, tilt, mouth } for frontHead, wave (one arm waving, its phase),
  // reach [[x, y], [x, y]] (the left and the right hand held at those points, elbows bent out).
  function figure(x, L, fx, fy, h, p) {
    p = p || {};
    var up = p.up || 0, step = p.step || 0, mix = function (a, b, k) { return a + (b - a) * k; };
    var lw = Math.max(2, h * 0.075), hr = h * 0.125, hy = fy - h + hr;
    var sh = fy - h * 0.72, hip = fy - h * 0.43, hw = h * 0.14;
    var legSkin = L.halloween ? L.bottom : L.skin;
    x.save(); x.lineCap = 'round'; x.lineJoin = 'round';
    if (L.cape) { x.fillStyle = L.cape; x.beginPath(); x.moveTo(fx - hw * 0.9, sh); x.lineTo(fx + hw * 0.9, sh); x.lineTo(fx + hw * 1.45, fy - h * 0.12); x.quadraticCurveTo(fx, fy - h * 0.08, fx - hw * 1.45, fy - h * 0.12); x.closePath(); x.fill(); }
    var lift = function (d) { return Math.max(0, step * d) * h * 0.08; };
    [-1, 1].forEach(function (d) {
      x.strokeStyle = legSkin; x.lineWidth = lw * 1.15;
      x.beginPath(); x.moveTo(fx + d * h * 0.065, hip); x.lineTo(fx + d * h * 0.08, fy - h * 0.05 - lift(d)); x.stroke();
      if (L.bones) { x.strokeStyle = L.skin; x.lineWidth = Math.max(1, lw * 0.3); x.stroke(); }
      x.fillStyle = L.shoe; x.beginPath(); x.ellipse(fx + d * h * 0.095, fy - h * 0.025 - lift(d), h * 0.065, h * 0.032, 0, 0, 7); x.fill();
    });
    // Shorts, then the shirt: wider at the shoulders.
    x.fillStyle = L.bottom; x.beginPath();
    x.moveTo(fx - h * 0.125, hip - h * 0.04); x.lineTo(fx + h * 0.125, hip - h * 0.04); x.lineTo(fx + h * 0.14, hip + h * 0.1); x.lineTo(fx + h * 0.01, hip + h * 0.1); x.lineTo(fx, hip + h * 0.05); x.lineTo(fx - h * 0.01, hip + h * 0.1); x.lineTo(fx - h * 0.14, hip + h * 0.1); x.closePath(); x.fill();
    x.fillStyle = L.top; x.beginPath();
    x.moveTo(fx - hw, sh + h * 0.02); x.quadraticCurveTo(fx - hw, sh - h * 0.015, fx - hw * 0.6, sh - h * 0.02); x.lineTo(fx + hw * 0.6, sh - h * 0.02);
    x.quadraticCurveTo(fx + hw, sh - h * 0.015, fx + hw, sh + h * 0.02); x.lineTo(fx + h * 0.12, hip + h * 0.01); x.lineTo(fx - h * 0.12, hip + h * 0.01); x.closePath(); x.fill();
    if (L.stripe) { x.fillStyle = L.stripe; x.fillRect(fx - h * 0.02, sh - h * 0.02, h * 0.04, hip - sh + h * 0.03); }
    if (L.bones) { x.strokeStyle = L.skin; x.lineWidth = Math.max(1, lw * 0.3); x.beginPath(); x.moveTo(fx, sh); x.lineTo(fx, hip); for (var k = 0; k < 3; k++) { var ry = sh + (hip - sh) * (0.25 + k * 0.2); x.moveTo(fx - hw * 0.6, ry); x.lineTo(fx + hw * 0.6, ry); } x.stroke(); }
    // The neck, then the arms (down, up in a V, or one waving).
    x.strokeStyle = L.skin; x.lineWidth = lw * 1.1; x.beginPath(); x.moveTo(fx, sh); x.lineTo(fx, hy + hr * 0.7); x.stroke();
    [-1, 1].forEach(function (d) {
      var u = p.wave && d === 1 ? 1 : up, wv = p.wave && d === 1 ? Math.sin(p.wave) * 0.35 : 0;
      var ex = fx + d * mix(h * 0.2, h * 0.25, u), ey = mix(sh + h * 0.15, sh - h * 0.1, u);
      var hx = fx + d * mix(h * 0.21, h * 0.32 + wv * h * 0.2, u), hy2 = mix(fy - h * 0.46, sh - h * 0.3, u);
      if (p.reach) {
        var rh = p.reach[d < 0 ? 0 : 1], ax = fx + d * (hw - lw * 0.4), ay = sh + lw * 0.3;
        hx = rh[0]; hy2 = rh[1]; ex = (ax + hx) / 2 + d * h * 0.03; ey = (ay + hy2) / 2 + h * 0.05;
      }
      x.strokeStyle = L.skin; x.lineWidth = lw;
      x.beginPath(); x.moveTo(fx + d * (hw - lw * 0.4), sh + lw * 0.3); x.lineTo(ex, ey); x.lineTo(hx, hy2); x.stroke();
      if (L.bones) { x.strokeStyle = '#1a1a1e'; x.lineWidth = Math.max(1, lw * 0.25); x.stroke(); }
      x.fillStyle = L.skin; x.beginPath(); x.arc(hx, hy2, lw * 0.75, 0, 7); x.fill();
    });
    x.restore();
    frontHead(x, L, fx, hy, hr, p.look);
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

  // A head seen from the side at (x, y), radius r, face towards +x (or -x when face < 0), turned by
  // tilt (radians, #469): the outfit's costume head, or a plain one with hair, an eye, an ear and a
  // nose, so the turn shows. L: the palette (skin, hair, head).
  function sideHead(ctx, L, x, y, r, face, tilt) {
    if (L.head) { head(ctx, L.head, x, y, r, face, tilt); return; }
    var c = ctx, f = face < 0 ? -1 : 1, sk = L.skin || '#f0c5a0';
    c.save(); c.translate(x, y); if (tilt) c.rotate(tilt); c.scale(f, 1);
    c.fillStyle = sk; c.beginPath(); c.arc(0, 0, r, 0, 7); c.fill();
    c.beginPath(); c.arc(r * 0.95, r * 0.12, r * 0.17, 0, 7); c.fill();
    c.fillStyle = L.hair || 'rgba(0,0,0,.25)'; c.beginPath(); c.arc(-r * 0.2, -r * 0.3, r, Math.PI * 0.9, Math.PI * 1.9); c.fill();
    c.fillStyle = 'rgba(0,0,0,.12)'; c.beginPath(); c.arc(-r * 0.12, r * 0.08, r * 0.2, 0, 7); c.fill();
    c.fillStyle = 'rgba(20,20,30,.85)'; c.beginPath(); c.arc(r * 0.5, -r * 0.08, Math.max(0.8, r * 0.12), 0, 7); c.fill();
    c.restore();
  }

  // How a head seen from the side moves (#469), as a tilt in radians for a face towards +x (negate
  // it for a face towards -x): a small bob with the stride on the run-up, chin up at take-off, the
  // head back in the air, chin down on landing, and a cheer that rocks. t: seconds, for the motion.
  function headPose(state, t) {
    t = t || 0;
    if (state === 'run') return { tilt: Math.sin(t * 9) * 0.07 };
    if (state === 'takeoff') return { tilt: -0.18 };
    if (state === 'air') return { tilt: -0.3 };
    if (state === 'land') return { tilt: 0.32 };
    if (state === 'cheer') return { tilt: -0.28 + Math.sin(t * 6) * 0.14 };
    return { tilt: Math.sin(t * 1.3) * 0.05 };
  }

  var BTN = 'border:0;border-radius:10px;padding:10px 14px;font:600 15px system-ui,sans-serif;touch-action:manipulation;box-shadow:none;transform:none;text-shadow:none;';

  // The outfit now, big and alive (#469), at the top of the picker. The athletics events' figure
  // looks around, cheers, tilts its head and waves; a game with its own figure (Orava's squirrel)
  // has it hop. It stops when the picker closes.
  function preview() {
    // position:static: a game's own canvas{position:fixed} (Mäkihyppy, Voimistelu) must not lift it
    // out of the picker, where it lay over the ready button (#473).
    var pv = el('canvas', 'position:static;width:100%;height:150px;display:block;border-radius:12px;flex:none;background:linear-gradient(#2d4f86,#3f8a4c)');
    pv.id = 'ai-pelit-asut-esikatselu';
    var t0 = performance.now();
    function frame() {
      if (!panel || !pv.isConnected) return;
      var dpr = Math.min(window.devicePixelRatio || 1, 3), w = pv.clientWidth || 300, h = 150;
      if (pv.width !== Math.round(w * dpr)) { pv.width = Math.round(w * dpr); pv.height = Math.round(h * dpr); }
      var g = pv.getContext('2d');
      if (!g) return;
      g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
      var t = (performance.now() - t0) / 1000, o = current(), ph = t % 6;
      try {
        if (FIGURE) {
          var look = ph < 1.5 ? { lx: Math.sin(t * 2) * 0.8, mouth: 'smile' } : ph < 3 ? { ly: -0.7, tilt: Math.sin(t * 3) * 0.2, mouth: 'open' }
            : ph < 4.5 ? { tilt: 0.3, lx: 0.4, mouth: 'o' } : { ly: 0.5, lx: -0.5, mouth: 'smile' };
          figure(g, dress(o), w / 2, h - 8, h - 22, { up: ph >= 1.5 && ph < 3 ? 1 : 0, wave: ph >= 4.5 ? t * 9 : 0, look: look });
        } else if (o) {
          var hop = Math.abs(Math.sin(t * 3.2)) * 14;
          g.translate(w / 2 - 72 * 0.85, h - 6 - 80 * 1.7 - hop); g.scale(1.7, 1.7);
          drawFn(g, o, 72, 80);
        }
      } catch (e) {}
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    return pv;
  }

  // A low sideways screen whose cards would not fit gets smaller ones (#473: the athletics' seven
  // kits and four groups in the Christmas season).
  var tight = false;
  function card(o, picked, grid) {
    var b = el('button', 'box-shadow:none;transform:none;text-shadow:none;margin:0;height:auto;width:auto;display:flex;flex-direction:column;align-items:center;gap:2px;border:3px solid ' + (picked ? '#ffd45c' : 'transparent') +
      ';border-radius:12px;background:' + (o.halloween ? '#2b2140' : o.joulu ? '#1f4030' : '#2a3358') + ';color:#fff;padding:4px 2px 6px;font:600 13px system-ui,sans-serif;touch-action:manipulation;min-width:0');
    b.className = 'asu' + (picked ? ' valittu' : '');
    b.setAttribute('data-asu', o.id);
    // A low, wide screen gets smaller cards, so every group fits without scrolling.
    var cw = innerHeight < 500 ? (tight ? 44 : 52) : 72, ch = innerHeight < 500 ? (tight ? 38 : 50) : (FIGURE ? 70 : 80);
    var cv = el('canvas', 'position:static;width:' + cw + 'px;height:' + ch + 'px;display:block');
    var dpr = Math.min(window.devicePixelRatio || 1, 3);
    cv.width = Math.round(cw * dpr); cv.height = Math.round(ch * dpr);
    var ctx = cv.getContext('2d');
    if (ctx && (FIGURE || drawFn)) {
      ctx.scale(dpr, dpr);
      try {
        if (FIGURE) figure(ctx, dress(o), cw / 2, ch * 0.96, ch * 0.88, { look: { lx: 0.3, mouth: 'smile' } });
        else drawFn(ctx, o, cw, ch);
      } catch (e) {}
    }
    b.appendChild(cv);
    b.appendChild(el('span', 'max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap' + (innerHeight < 500 ? ';font-size:11px' : ''), (o.emoji && innerHeight >= 500 ? o.emoji + ' ' : '') + o.name));
    b.onclick = function () {
      unsaved = save(KEY, o.id) ? null : o;
      if (KEY !== OWN) save(OWN, o.id);
      if (changeFn) { try { changeFn(o); } catch (e) {} }
      fill(grid);
    };
    return b;
  }

  function fill(grid) {
    grid.textContent = '';
    var now = current(), own = [], costumes = [], school = [], xmas = [];
    outfits.forEach(function (o) { (o.halloween ? costumes : o.tylypahka ? school : o.joulu ? xmas : own).push(o); });
    var joulu = ['🎄 Joulu', jouluSeason() ? xmas : []];
    // 1–2 November are in both seasons: Halloween keeps its last two days first (#473).
    var groups = season() ? [['🎃 Halloween', costumes], joulu, ['Tavalliset', own], ['⚡ Tylypahka', school]]
      : jouluSeason() ? [joulu, ['Tavalliset', own], ['⚡ Tylypahka', school], ['🎃 Halloween', costumes]]
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
    else if (jouluSeason() && innerHeight >= 500 && outfits.some(function (o) { return o.joulu; })) box.appendChild(el('div', 'color:#9fe0a8;font-size:13px', 'Hyvää joulua! Pukeudu joulupukiksi, tontuksi tai poroksi.'));
    var low = innerHeight < 500;
    if (!low && (FIGURE || drawFn)) box.appendChild(preview());
    tight = false;
    function columns() { grid.style.gridTemplateColumns = 'repeat(auto-fill,minmax(' + (low ? (tight ? 50 : 58) : 82) + 'px,1fr))'; }
    var grid = el('div', 'display:grid;gap:' + (low ? 4 : 6) + 'px;overflow:auto;min-height:0');
    columns();
    box.appendChild(grid);
    fill(grid);
    panel.onclick = function (e) { if (e.target === panel) close(); };
    document.body.appendChild(panel);
    if (low && grid.scrollHeight > grid.clientHeight + 1) { tight = true; columns(); fill(grid); }
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
      // Orava v6's squirrel draws costume heads only for Halloween ones, so it gets none (#473, Eero's choice).
      if (opts.joulu === true || (opts.joulu !== false && GAME !== 'orava')) outfits = outfits.concat(JOULU);
      if (opts.tylypahka !== false) outfits = outfits.concat(TYLYPAHKA);
      drawFn = opts.draw || null;
      changeFn = opts.change || null;
      adopt();
      return current();
    },
    current: current,
    get: function (id) { return byId(id) || outfits[0] || null; },
    list: function () { return outfits.slice(); },
    open: open,
    close: close,
    isOpen: function () { return !!panel; },
    halloween: HALLOWEEN,
    joulu: JOULU,
    jouluSeason: jouluSeason,
    yleisurheilu: YLEISURHEILU,
    kolmiD: KOLMID,
    tylypahka: TYLYPAHKA,
    season: season,
    head: head,
    frontHead: frontHead,
    figure: figure,
    dress: dress,
    headPose: headPose,
    sideHead: sideHead,
  };
})();
