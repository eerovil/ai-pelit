'use strict';
// Shakki's game: the menu, a game against the computer, a game with a friend in a room, saves.
var R = window.AiPelitRooms, S = window.AiPelitAanet;
var $ = function (id) { return document.getElementById(id); };

// The game being played, or null in the menu.
//   moves: the moves from the start (UCI strings, the one truth; the rest is derived)
//   white, black: {id, name}; mine: this phone's colour ('w' | 'b')
//   level: the computer's level (solo); result: null or {result, why, winner}
var game = null, derived = null, result = null;
var online = false, roomRound = 0, roomHost = '';
var selected = -1, drag = null, anim = null, thinking = false, aiTimer = 0, pendingPromo = null;
var resignArmed = 0, endHidden = false, notice = '', ended = false, opened = -1;
// Why the last tried move was refused, when it was the king's safety (#465 v2):
// { text, shake, king, at, t0 } or null. The pieces to blame shake, the text shows under the board.
var why = null, whyTimer = 0, WHY_MS = 4000, SHAKE_MS = 700;
// Practice mode (#465 v3): game.practice is true; a tapped piece's threats show (inspect = its square).
var inspect = -1;
// PROTOTYPE: how the threats show. 'a' badges on every threatened piece, 'b' lines on a tapped piece, 'c' both.
var infoStyle = (location.hash.match(/tyyli=([abc])/) || [])[1] || 'c';

if (S) S.load(['puu', 'osuma', 'valinta', 'naksu', 'voitto', 'tappio', 'onnistui', 'virhe']);
function sound(name, vol) { if (S) S.play(name, { vol: vol }); }

function load(key, fallback) { try { var x = localStorage.getItem('ai-pelit:shakki:' + key); return x === null ? fallback : JSON.parse(x); } catch (e) { return fallback; } }
function save(key, v) { try { localStorage.setItem('ai-pelit:shakki:' + key, JSON.stringify(v)); } catch (e) {} }
function forget(key) { try { localStorage.removeItem('ai-pelit:shakki:' + key); } catch (e) {} }

function current() { return derived; }
function gameOver() { return !!result; }
function bottomColor() { return game ? game.mine : (load('vari', 'w') === 'b' ? 'b' : 'w'); }
function sideOf(color) { return game ? (color === 'w' ? game.white : game.black) : null; }
function myTurn() {
  return !!(game && derived && !result && derived.pos.turn === game.mine && !thinking && (!online || !R.paused));
}
function movesFrom(sq) {
  if (!derived || !myTurn()) return [];
  return legalMoves(derived.pos).filter(function (m) { return m.from === sq; });
}

// ---- Starting, saving, ending ----
// Only Aloittelija is open at first; a win against a level opens the next one.
function unlocked(l) {
  if (l === 0) return true;
  var s = load('tilasto:' + (l - 1), null);
  return !!(s && Number(s.v) > 0);
}
function topUnlocked() { var l = 0; while (l + 1 < LEVELS.length && unlocked(l + 1)) l++; return l; }
function levelNow() {
  var l = load('taso', 0);
  if (!Number.isInteger(l) || l < 0 || l >= LEVELS.length) l = 0;
  return unlocked(l) ? l : topUnlocked();
}
function newSoloGame(practice) {
  var pick = load('vari', 'w'), mine = pick === 'arvo' ? (Math.random() < 0.5 ? 'w' : 'b') : pick === 'b' ? 'b' : 'w';
  var level = levelNow(), cpu = { id: 'kone', name: 'Kone · ' + LEVELS[level].name }, me = { id: 'solo', name: 'Sinä' };
  var g = { moves: [], mine: mine, level: level, white: mine === 'w' ? me : cpu, black: mine === 'b' ? me : cpu };
  if (practice === true) g.practice = true;
  startGame(g, false);
}
function validSave(s) {
  return s && Array.isArray(s.moves) && (s.mine === 'w' || s.mine === 'b') && Number.isInteger(s.level) &&
    s.level >= 0 && s.level < LEVELS.length && s.white && s.black && playGame(s.moves) !== null;
}
function resumeSolo() {
  var s = load('peli', null);
  if (!validSave(s)) { forget('peli'); menu(); return; }
  startGame(s, false);
}
function startGame(g, isOnline) {
  clearTimeout(aiTimer); thinking = false;
  online = isOnline; game = g; derived = playGame(g.moves); result = null;
  selected = -1; drag = null; anim = null; pendingPromo = null; endHidden = false; notice = ''; resignArmed = 0; ended = false; opened = -1;
  why = null; clearTimeout(whyTimer); inspect = -1;
  if (!derived) { game.moves = []; derived = playGame([]); }
  if (g.result) result = g.result;
  else { var st = gameStatus(derived); if (st.over) result = st; }
  showPlay();
  if (result) finish(true); else { keepSolo(); maybeComputer(); }
}
function keepSolo() {
  if (online || !game) return;
  if (result) forget('peli');
  else save('peli', { moves: derived.uci, mine: game.mine, level: game.level, white: game.white, black: game.black, practice: !!game.practice });
}

// A move by either side, from a tap, the computer or the host's state.
function play(m, quiet) {
  var before = derived.pos;
  var text = moveText(before, m), cap = !!m.cap;
  game.moves = derived.uci.concat([moveUci(m)]);
  derived = playGame(game.moves);
  anim = { from: m.from, to: m.to, t0: performance.now(), dur: 170 };
  selected = -1; drag = null; resignArmed = 0; why = null; clearTimeout(whyTimer); inspect = -1; showWhy();
  if (!quiet) { sound(cap ? 'osuma' : 'puu', 0.3); if (/[+#]$/.test(text)) sound('naksu', 0.2); }
  var st = gameStatus(derived);
  if (st.over) result = st;
  return text;
}

// A move the rules refuse: say why, and show what stands in the way.
function explain(from, to) {
  var r = whyIllegal(derived.pos, from, to);
  if (!r) return false;
  r.at = to; r.t0 = performance.now(); why = r;
  sound('virhe', 0.1);
  clearTimeout(whyTimer);
  whyTimer = setTimeout(clearWhy, WHY_MS);
  showWhy(); askDraw();
  return true;
}
function clearWhy() { if (!why) return; why = null; clearTimeout(whyTimer); showWhy(); askDraw(); }
function showWhy() { updateHUD(); }

function tryMove(m) {
  if (!myTurn()) return false;
  if (m.promo) { askPromotion(m); return true; }
  return submitMove(m);
}
function submitMove(m) {
  if (!myTurn()) return false;
  var ply = derived.uci.length;
  play(m);
  if (online) {
    if (R.isHost) afterHostMove();
    else R.send({ t: 'move', round: roomRound, ply: ply, m: moveUci(m) });
  } else {
    keepSolo();
    if (result) finish(); else maybeComputer();
  }
  updateHUD(); askDraw();
  return true;
}

// The computer answers after the move's slide has been seen.
function maybeComputer() {
  if (online || !game || result || derived.pos.turn === game.mine) { thinking = false; return; }
  thinking = true; updateHUD();
  var token = game, ply = derived.uci.length;
  clearTimeout(aiTimer);
  aiTimer = setTimeout(function () { computerTurn(token, ply); }, 380);
}
function computerTurn(token, ply) {
  if (game !== token || !derived || derived.uci.length !== ply || result) { thinking = false; return; }
  var m = computerMove(derived.pos, game.level, derived.keys);
  thinking = false;
  if (!m) return;
  play(m); keepSolo();
  if (result) finish();
  updateHUD(); askDraw();
}

// ---- The end of a game ----
function resultText(r, mine) {
  if (!r) return { title: '', sub: '', kind: '' };
  var win = r.winner === mine, why = r.why;
  if (why === 'matti') return { title: win ? 'Voitit!' : 'Hävisit', sub: 'Shakkimatti.', kind: win ? 'win' : 'lose' };
  if (why === 'luovutus') return { title: win ? 'Voitit!' : 'Hävisit', sub: win ? 'Vastustaja luovutti.' : 'Luovutit.', kind: win ? 'win' : 'lose' };
  var subs = { patti: 'Patti: siirtovuorossa olevalla ei ole laillista siirtoa.', toisto: 'Sama asema toistui kolmesti.',
    '50': '50 siirtoa ilman lyöntiä tai sotilaan siirtoa.', materiaali: 'Kummallakaan ei riitä nappuloita mattiin.' };
  return { title: 'Tasapeli', sub: subs[why] || '', kind: 'draw' };
}
// Records the result once, then shows the end card. again: an ended game opened from a save.
function finish(again) {
  clearTimeout(aiTimer); thinking = false; ended = true;
  var t = resultText(result, game.mine);
  if (online) {
    if (R.isHost) { game.result = result; sendState(); R.deliver({ t: 'result', round: roomRound, g: snapshot() }); R.endRound(); }
    if (R.once(roomRound)) bump('kaverit', t.kind);
  } else if (game.practice) keepSolo();
  else if (!again) {
    var next = game.level + 1, opens = t.kind === 'win' && next < LEVELS.length && !unlocked(next);
    bump('tilasto:' + game.level, t.kind);
    if (opens) { opened = next; save('taso', next); }
    keepSolo();
  } else keepSolo();
  if (!again) sound(t.kind === 'win' ? 'voitto' : t.kind === 'lose' ? 'tappio' : 'onnistui', t.kind === 'draw' ? 0.2 : 0.3);
  showEnd();
}
function bump(key, kind) {
  var s = load(key, null); if (!s || typeof s !== 'object') s = { v: 0, h: 0, t: 0 };
  var k = kind === 'win' ? 'v' : kind === 'lose' ? 'h' : 't';
  s[k] = (Number(s[k]) || 0) + 1; save(key, s);
}
function statsText(s) {
  if (!s || !(s.v + s.h + s.t)) return 'Ei vielä pelattuja pelejä.';
  return s.v + ' voittoa · ' + s.h + ' tappiota · ' + s.t + ' tasapeliä';
}
function resign() {
  if (!game || result) return;
  if (online && !R.isHost) { R.send({ t: 'resign', round: roomRound }); return; }
  result = { over: true, result: game.mine === 'w' ? '0-1' : '1-0', why: 'luovutus', winner: other(game.mine) };
  keepSolo(); finish(); updateHUD(); askDraw();
}

// ---- Screens ----
function menu() {
  clearTimeout(aiTimer); thinking = false;
  if (R) R.extra(null);
  game = null; derived = null; result = null; online = false; selected = -1; drag = null; anim = null; pendingPromo = null;
  why = null; clearTimeout(whyTimer); inspect = -1;
  $('menu').classList.remove('hidden'); $('end').classList.add('hidden'); $('promo').classList.add('hidden');
  $('pa').classList.add('hidden'); $('pb').classList.add('hidden');
  var lv = levelNow(), col = load('vari', 'w');
  Array.prototype.forEach.call(document.querySelectorAll('#levels button'), function (b) {
    var l = Number(b.dataset.l);
    b.classList.toggle('on', l === lv); b.classList.toggle('locked', !unlocked(l));
  });
  Array.prototype.forEach.call(document.querySelectorAll('#colors button'), function (b) { b.classList.toggle('on', b.dataset.c === col); });
  $('levelInfo').textContent = LEVELS[lv].name + ': ' + statsText(load('tilasto:' + lv, null));
  var s = load('peli', null);
  $('resume').classList.toggle('hidden', !validSave(s));
  if (validSave(s)) $('resume').textContent = (s.practice ? 'Jatka harjoitusta · ' : 'Jatka peliä · ') + LEVELS[s.level].name + ' · siirto ' + (Math.floor(s.moves.length / 2) + 1);
  askDraw();
}
function showPlay() {
  $('menu').classList.add('hidden'); $('end').classList.add('hidden'); $('promo').classList.add('hidden');
  $('pa').classList.remove('hidden'); $('pb').classList.remove('hidden');
  $('toMenu').classList.toggle('hidden', online);
  layout(); updateHUD(); askDraw();
}
function updateHUD() {
  if (!game) return;
  var opp = sideOf(other(game.mine)), me = sideOf(game.mine);
  $('oppoName').textContent = (game.mine === 'w' ? '⚫ ' : '⚪ ') + opp.name;
  $('meName').textContent = (game.mine === 'w' ? '⚪ ' : '⚫ ') + me.name;
  var st = '', pos = derived.pos;
  if (result) st = resultText(result, game.mine).title + ' · ' + resultText(result, game.mine).sub;
  else if (online && R.paused) st = 'Peli odottaa…';
  else if (thinking) st = 'Kone miettii…';
  else if (pos.turn === game.mine) st = inCheck(pos) ? 'Shakki! Sinun vuorosi' : 'Sinun vuorosi';
  else st = (inCheck(pos) ? 'Shakki! ' : '') + (online ? opp.name + ' miettii…' : 'Vastustajan vuoro');
  $('status').textContent = st;
  $('status').classList.toggle('check', !result && inCheck(pos) && pos.turn === game.mine);
  var n = derived.texts.length;
  var whyLine = why && !result;
  $('lastMove').classList.toggle('why', !!whyLine);
  var info = !whyLine && game.practice && inspect >= 0 && pos.b[inspect] ? infoText(pos, inspect) : '';
  $('lastMove').classList.toggle('info', !!info);
  $('lastMove').textContent = whyLine ? '⚠ ' + why.text : info || notice || (n ? 'Edellinen: ' + Math.ceil(n / 2) + '.' + (n % 2 ? ' ' : ' … ') + derived.texts[n - 1] : 'Valkea aloittaa.');
  // Sideways the status sits in the left panel, under the opponent.
  var a = document.createElement('div'), b = document.createElement('div');
  a.className = $('status').className; a.textContent = $('status').textContent; b.textContent = $('lastMove').textContent;
  a.id = 'paStatusText'; b.className = whyLine ? 'lastMove why' : info ? 'lastMove info' : 'lastMove'; $('paStatus').replaceChildren(a, b);
  $('resign').textContent = resignArmed > Date.now() ? 'Varmasti?' : 'Luovuta';
  $('resign').classList.toggle('hidden', !!result || !!game.practice);
  $('undo').classList.toggle('hidden', !game.practice);
  $('undo').disabled = !canUndo();
  $('meName').textContent += game.practice ? ' · 🎓 Harjoitus' : '';
  $('showEnd').classList.toggle('hidden', !result || !endHidden);
}
function showEnd() {
  if (!result || !game) return;
  var t = resultText(result, game.mine);
  $('endTitle').textContent = t.title; $('endSub').textContent = t.sub;
  $('endTitle').className = t.kind;
  $('endStats').textContent = game.practice ? 'Harjoituspeli: ei tilastoihin eikä avaa tasoja.' : online ? 'Kaveripelit: ' + statsText(load('kaverit', null))
    : LEVELS[game.level].name + ': ' + statsText(load('tilasto:' + game.level, null)) +
      (opened >= 0 ? '\n🔓 Uusi taso auki: ' + LEVELS[opened].name + '!' : '');
  $('again').textContent = online ? 'Takaisin huoneeseen' : 'Uusi peli';
  $('endMenu').classList.toggle('hidden', online);
  $('endUndo').classList.toggle('hidden', !game.practice);
  $('end').classList.toggle('hidden', endHidden);
  $('promo').classList.add('hidden');
  updateHUD(); askDraw();
}

// ---- Promotion ----
function askPromotion(m) {
  pendingPromo = m;
  var box = $('promoPieces'); box.replaceChildren();
  ['q', 'r', 'b', 'n'].forEach(function (q) {
    var b = document.createElement('button'), cv = document.createElement('canvas'), p = game.mine === 'w' ? q.toUpperCase() : q;
    cv.width = cv.height = 96; cv.getContext('2d').drawImage(pieceImage(p, 96), 0, 0);
    b.append(cv); b.dataset.p = q; b.setAttribute('aria-label', { q: 'Daami', r: 'Torni', b: 'Lähetti', n: 'Ratsu' }[q]);
    b.onclick = function () {
      var want = pendingPromo; pendingPromo = null; $('promo').classList.add('hidden');
      var full = legalMoves(derived.pos).filter(function (x) { return x.from === want.from && x.to === want.to && x.promo === q; })[0];
      if (full) submitMove(full);
    };
    box.append(b);
  });
  $('promo').classList.remove('hidden');
}

// ---- Touch on the board ----
function pointXY(e) { var r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
canvas.addEventListener('pointerdown', function (e) {
  if (!game) return;
  if (result) { if (endHidden) { endHidden = false; showEnd(); } return; }
  var xy = pointXY(e), sq = squareAt(xy[0], xy[1]);
  // Practice: a tap on any piece shows who threatens and guards it; the opponent's piece is only looked at.
  if (game.practice && sq >= 0) {
    var tp = derived.pos.b[sq], tgt = movesFrom(selected).some(function (m) { return m.to === sq; });
    if (tp && !tgt && !(colorOf(tp) === game.mine && myTurn())) { inspect = inspect === sq ? -1 : sq; selected = -1; if (why) clearWhy(); updateHUD(); askDraw(); return; }
    inspect = tp && !tgt ? sq : -1;
  }
  if (sq < 0 || !myTurn()) { if (sq < 0) { selected = -1; askDraw(); } return; }
  var target = movesFrom(selected).filter(function (m) { return m.to === sq; })[0];
  if (target) { tryMove(target); return; }
  var p = derived.pos.b[sq];
  if (selected >= 0 && !(p && colorOf(p) === game.mine) && explain(selected, sq)) { selected = -1; askDraw(); return; }
  if (why) clearWhy();
  if (p && colorOf(p) === game.mine) {
    selected = sq; drag = { from: sq, x: xy[0], y: xy[1], sx: xy[0], sy: xy[1], moved: false };
    try { canvas.setPointerCapture(e.pointerId); } catch (err) {}
    sound('valinta', 0.12);
    // A piece with no move at all because of its king: say why at once, there are no dots to try.
    if (!movesFrom(sq).length) {
      var held = pseudoMoves(derived.pos).filter(function (m) { return m.from === sq; })[0];
      if (held) explain(sq, held.to);
    }
  } else selected = -1;
  updateHUD(); askDraw();
});
canvas.addEventListener('pointermove', function (e) {
  if (!drag) return;
  var xy = pointXY(e);
  drag.x = xy[0]; drag.y = xy[1];
  if (Math.hypot(drag.x - drag.sx, drag.y - drag.sy) > view.cell * 0.3) drag.moved = true;
  if (drag.moved) askDraw();
});
function endDrag(e) {
  if (!drag) return;
  var d = drag; drag = null;
  if (d.moved && game && !result) {
    var xy = pointXY(e), sq = squareAt(xy[0], xy[1]);
    var target = movesFrom(d.from).filter(function (m) { return m.to === sq; })[0];
    if (target) { tryMove(target); return; }
    if (sq >= 0 && sq !== d.from && myTurn() && explain(d.from, sq)) selected = -1;
  }
  askDraw();
}
canvas.addEventListener('pointerup', endDrag);
canvas.addEventListener('pointercancel', function () { drag = null; askDraw(); });

// ---- Practice: unlimited undo, and who threatens whom ----
function canUndo() { return !!(game && game.practice && derived && undoTarget() < derived.uci.length); }
// Back to the last position where it was the player's turn before their last move.
function undoTarget() {
  var n = derived.uci.length, mineFirst = game.mine === 'w' ? 0 : 1, k = n - 1;
  while (k >= mineFirst && (k % 2) !== mineFirst) k--;
  return k < mineFirst ? n : k;
}
function undo() {
  if (!canUndo()) return;
  clearTimeout(aiTimer); thinking = false;
  game.moves = derived.uci.slice(0, undoTarget());
  derived = playGame(game.moves); result = null; ended = false; endHidden = false;
  selected = -1; drag = null; anim = null; inspect = -1; why = null; clearTimeout(whyTimer);
  $('end').classList.add('hidden');
  sound('valinta', 0.12); keepSolo(); updateHUD(); askDraw();
}
var NAME = { P: 'Sotilas', N: 'Ratsu', B: 'Lähetti', R: 'Torni', Q: 'Daami', K: 'Kuningas' };
function pieceName(pos, sq) { return NAME[pos.b[sq].toUpperCase()] + ' ' + sqName(sq); }
function shortName(pos, sq) { var u = pos.b[sq].toUpperCase(); return (u === 'P' ? '' : FI_LETTER[u]) + sqName(sq); }
// What a piece's own captures reach: the other side's pieces it could take now (pins ignored).
function targetsOf(pos, sq) {
  var keep = pos.turn, ep = pos.ep, out = [];
  pos.turn = colorOf(pos.b[sq]); pos.ep = -1;
  pseudoMoves(pos, true).forEach(function (m) { if (m.from === sq && m.cap && out.indexOf(m.to) < 0) out.push(m.to); });
  pos.turn = keep; pos.ep = ep; return out;
}
// Practice: for the selected piece, which of its moves leave which own pieces without enough defence.
var riskCache = { key: '', moves: {}, all: [] };
function risks() {
  if (!game || !game.practice || selected < 0 || !derived) return { moves: {}, all: [] };
  var key = selected + ':' + derived.uci.join();
  if (riskCache.key === key) return riskCache;
  var r = { key: key, moves: {}, all: [], self: 0 };
  movesFrom(selected).forEach(function (m) {
    var ex = exposedBy(derived.pos, m);
    if (!ex.others.length && !ex.self) return;
    r.moves[m.to] = ex;
    if (ex.self) r.self++;
    ex.others.forEach(function (s) { if (r.all.indexOf(s) < 0) r.all.push(s); });
  });
  riskCache = r; return r;
}
function infoText(pos, sq) {
  var g = guardInfo(pos, sq), list = function (a) { return a.map(function (s) { return shortName(pos, s); }).join(', '); };
  var head = pieceName(pos, sq) + (colorOf(pos.b[sq]) === game.mine ? '' : ' (vastustajan)') + ': ';
  head += g.attackers.length ? 'uhkaajia ' + g.attackers.length + ' (' + list(g.attackers) + ')' : 'ei uhattu';
  head += ', puolustajia ' + g.defenders.length + (g.defenders.length ? ' (' + list(g.defenders) + ')' : '');
  if (hanging(pos, sq)) head += colorOf(pos.b[sq]) === game.mine ? ' ⚠' : ' – voit voittaa sen';
  var t = targetsOf(pos, sq);
  head += t.length ? '. Uhkaa itse: ' + list(t) + '.' : '.';
  if (sq === selected) {
    var r = risks(), n = movesFrom(sq).length, name = NAME[pos.b[sq].toUpperCase()].toLowerCase();
    if (r.self || r.all.length) head += ' Varo punaisia ruutuja:';
    if (r.self) head += ' siellä ' + name + ' menetetään heti.';
    if (r.all.length) head += (r.self ? ' Tai' : '') + ' ' + (Object.keys(r.moves).length === n && !r.self ? 'jos ' + name + ' lähtee, ' : '') +
      list(r.all) + ' jää ilman riittävää puolustusta.';
  }
  return head;
}

// ---- Playing with a friend (rooms.js); the host's phone keeps the game ----
function snapshot() { return { moves: derived.uci, white: game.white, black: game.black, result: result }; }
function sendState(to) { if (online && R.isHost && game) R.send({ t: 'state', round: roomRound, g: snapshot() }, to); }
function sideId() { return game && derived ? sideOf(derived.pos.turn).id : ''; }
function afterHostMove() {
  sendState();
  if (result) finish();
}
function receive(m, from) {
  if (!online || !m || m.round !== roomRound) return;
  if (R.isHost) {
    if (!game) return;
    if (result) { if (m.t === 'move') sendState(from); return; }
    if (m.t === 'move') {
      // A move the host cannot take (not that phone's turn, an old ply, the round paused, not legal)
      // sends the game back as it is, so the guest drops the move it showed already.
      var mv = from === sideId() && m.ply === derived.uci.length && !R.paused ? findMove(derived.pos, m.m) : null;
      if (mv) { play(mv); afterHostMove(); updateHUD(); askDraw(); }
      else sendState(from);
    }
    if (m.t === 'resign' && (from === game.white.id || from === game.black.id)) {
      var loser = from === game.white.id ? 'w' : 'b';
      result = { over: true, result: loser === 'w' ? '0-1' : '1-0', why: 'luovutus', winner: other(loser) };
      finish(); updateHUD(); askDraw();
    }
  } else if (from === roomHost && (m.t === 'state' || m.t === 'result') && m.g) hearState(m.g);
}
// A guest takes the host's game as it is; one new move slides and sounds as if played here.
function hearState(g) {
  if (!g || !Array.isArray(g.moves) || !g.white || !g.black) return;
  var next = playGame(g.moves); if (!next) return;
  var mine = g.white.id === R.me ? 'w' : g.black.id === R.me ? 'b' : 'w';
  if (!game) { startGame({ moves: g.moves, white: g.white, black: g.black, mine: mine, result: g.result || null }, true); return; }
  var had = derived.uci, grew = next.uci.length === had.length + 1 && had.every(function (u, i) { return u === next.uci[i]; });
  game.white = g.white; game.black = g.black; game.mine = mine;
  if (grew) play(next.moves[next.moves.length - 1]);
  else if (next.uci.join() !== had.join()) { game.moves = g.moves; derived = next; selected = -1; anim = null; why = null; clearTimeout(whyTimer); }
  // A guest's own winning move ends the game here only once the host has it too.
  result = g.result || null;
  if (result && !ended) finish();
  else if (!result) { $('end').classList.add('hidden'); }
  updateHUD(); askDraw();
}
if (R) {
  R.turns(function (id) { return !!(online && game && !result && sideId() === id); });
  R.on('start', function (s) {
    R.extra(null); clearTimeout(aiTimer);
    online = true; roomRound = s.round; roomHost = R.hostId; game = null; derived = null; result = null;
    if (R.isHost) {
      // White changes from round to round: the host remembers per room who had it last.
      var a = s.players[0], b = s.players[1] || s.players[0], last = load('valkea:' + R.code, '');
      var white = last === a.id ? b : a, black = white === a ? b : a;
      save('valkea:' + R.code, white.id);
      startGame({ moves: [], white: { id: white.id, name: white.name }, black: { id: black.id, name: black.name },
        mine: white.id === R.me ? 'w' : 'b', result: null }, true);
      sendState();
    } else {
      $('menu').classList.add('hidden'); $('end').classList.add('hidden');
      $('pa').classList.remove('hidden'); $('pb').classList.remove('hidden');
      $('status').textContent = 'Odotetaan lautaa…';
    }
  });
  R.on('message', receive);
  // A friend leaving or coming back pauses the game or goes on with it.
  R.on('peers', function () { if (online && game) updateHUD(); });
  R.on('hello', function (id) { sendState(id); });
  // The host skips an away friend's turn: the computer plays one move for them.
  R.on('skip', function (ids) {
    if (!online || !R.isHost || !game || result || ids.indexOf(sideId()) < 0) return;
    var name = sideOf(derived.pos.turn).name, m = computerMove(derived.pos, 2, derived.keys);
    if (!m) return;
    play(m); notice = 'Kone siirsi pelaajan ' + name + ' puolesta.';
    afterHostMove(); updateHUD(); askDraw();
    setTimeout(function () { notice = ''; updateHUD(); }, 3000);
  });
  R.on('lobby', menu); R.on('menu', menu); R.on('leave', menu);
}

// ---- Buttons ----
Array.prototype.forEach.call(document.querySelectorAll('#levels button'), function (b) {
  b.onclick = function () {
    var l = Number(b.dataset.l);
    if (!unlocked(l)) {
      sound('virhe', 0.12);
      $('levelInfo').textContent = '🔒 ' + LEVELS[l].name + ' aukeaa, kun voitat tason ' + LEVELS[l - 1].name + '.';
      return;
    }
    save('taso', l); sound('valinta', 0.12); menu();
  };
});
Array.prototype.forEach.call(document.querySelectorAll('#colors button'), function (b) {
  b.onclick = function () { save('vari', b.dataset.c); sound('valinta', 0.12); menu(); };
});
$('play').onclick = function () { newSoloGame(false); };
$('practice').onclick = function () { newSoloGame(true); };
$('undo').onclick = undo; $('endUndo').onclick = undo;
// PROTOTYPE: the style switch.
Array.prototype.forEach.call(document.querySelectorAll('#proto button'), function (b) {
  b.classList.toggle('on', b.dataset.s === infoStyle);
  b.onclick = function () {
    infoStyle = b.dataset.s; location.hash = 'tyyli=' + infoStyle;
    Array.prototype.forEach.call(document.querySelectorAll('#proto button'), function (x) { x.classList.toggle('on', x === b); });
    askDraw();
  };
});
$('resume').onclick = resumeSolo;
$('friends').onclick = function () { if (R) R.open(); };
$('toMenu').onclick = function () { keepSolo(); menu(); };
$('resign').onclick = function () {
  if (resignArmed > Date.now()) { resignArmed = 0; resign(); return; }
  resignArmed = Date.now() + 3000; updateHUD();
  setTimeout(updateHUD, 3100);
};
$('again').onclick = function () {
  if (online) { var t = resultText(result, game.mine); R.backToRoom(t.title + ' ' + t.sub, t.kind === 'draw' ? '' : t.kind); }
  else newSoloGame(!!game.practice);
};
$('endMenu').onclick = menu;
$('peek').onclick = function () { endHidden = true; $('end').classList.add('hidden'); updateHUD(); };
$('showEnd').onclick = function () { endHidden = false; showEnd(); };
$('promoCancel').onclick = function () { pendingPromo = null; $('promo').classList.add('hidden'); };

new ResizeObserver(function () { if (layout()) askDraw(); }).observe(canvas);
window.addEventListener('pagehide', keepSolo);
layout(); menu();
