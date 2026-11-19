'use strict';
// Shakki's rules and computer player. Plain functions over a position object, no drawing, so the
// tests can play whole games through them.
//
// A position: {b: 64 squares ('' or a piece letter, upper case white: PNBRQK), turn: 'w'|'b',
// castle: 'KQkq' subset, ep: en passant target square or -1, half: half-move clock, full: move
// number}. Square 0 is a8, 7 is h8, 56 is a1, 63 is h1 (row 0 is the 8th rank).
// A move: {from, to, promo ('' or 'q','r','b','n'), cap: captured piece or '', flag: '' | 'ep' |
// 'k' (castle king side) | 'q' (queen side) | 'pp' (pawn two steps)}.

var START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
var FILES = 'abcdefgh';

function colorOf(p) { return !p ? '' : p === p.toUpperCase() ? 'w' : 'b'; }
function other(c) { return c === 'w' ? 'b' : 'w'; }
function sqName(s) { return FILES[s & 7] + (8 - (s >> 3)); }
function sqIndex(n) { return (8 - Number(n[1])) * 8 + FILES.indexOf(n[0]); }

function parseFen(fen) {
  var parts = fen.trim().split(/\s+/), rows = parts[0].split('/'), b = [];
  rows.forEach(function (r) {
    for (var i = 0; i < r.length; i++) {
      var ch = r[i];
      if (/[1-8]/.test(ch)) for (var k = 0; k < Number(ch); k++) b.push('');
      else b.push(ch);
    }
  });
  return { b: b, turn: parts[1] || 'w', castle: parts[2] && parts[2] !== '-' ? parts[2] : '',
    ep: parts[3] && parts[3] !== '-' ? sqIndex(parts[3]) : -1,
    half: Number(parts[4] || 0), full: Number(parts[5] || 1) };
}

function boardFen(pos) {
  var s = '', run = 0;
  for (var i = 0; i < 64; i++) {
    if (pos.b[i]) { if (run) s += run; run = 0; s += pos.b[i]; } else run++;
    if ((i & 7) === 7) { if (run) s += run; run = 0; if (i < 63) s += '/'; }
  }
  return s + ' ' + pos.turn + ' ' + (pos.castle || '-');
}
// True when the side to move has a legal en passant capture (its king safe after it).
function epLegal(pos) {
  if (pos.ep < 0) return false;
  var c = pos.turn;
  return pseudoMoves(pos, true).some(function (m) {
    if (m.flag !== 'ep') return false;
    var u = makeMove(pos, m), ok = !inCheck(pos, c);
    unmakeMove(pos, m, u);
    return ok;
  });
}
// Equal keys are the same position for the repetition rule: the board, turn, castling, and the
// en passant square only when that capture can really be made (a pawn's double step alone
// changes nothing).
function posKey(pos) { return boardFen(pos) + ' ' + (epLegal(pos) ? sqName(pos.ep) : '-'); }
function toFen(pos) { return boardFen(pos) + ' ' + (pos.ep >= 0 ? sqName(pos.ep) : '-') + ' ' + pos.half + ' ' + pos.full; }
function clonePos(pos) {
  return { b: pos.b.slice(), turn: pos.turn, castle: pos.castle, ep: pos.ep, half: pos.half, full: pos.full };
}

var KNIGHT = [[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]];
var KING = [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]];
var ROOK_D = [[1, 0], [-1, 0], [0, 1], [0, -1]];
var BISHOP_D = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
function at(f, r) { return f < 0 || f > 7 || r < 0 || r > 7 ? -1 : r * 8 + f; }

// Is square sq attacked by side `by`?
function attacked(pos, sq, by) {
  var b = pos.b, f = sq & 7, r = sq >> 3, i, t, p, up = by === 'w';
  // Pawns: a white pawn attacks upwards (to a smaller row).
  var pr = up ? r + 1 : r - 1, pawn = up ? 'P' : 'p';
  if ((t = at(f - 1, pr)) >= 0 && b[t] === pawn) return true;
  if ((t = at(f + 1, pr)) >= 0 && b[t] === pawn) return true;
  var n = up ? 'N' : 'n', k = up ? 'K' : 'k';
  for (i = 0; i < 8; i++) {
    if ((t = at(f + KNIGHT[i][0], r + KNIGHT[i][1])) >= 0 && b[t] === n) return true;
    if ((t = at(f + KING[i][0], r + KING[i][1])) >= 0 && b[t] === k) return true;
  }
  var rq = up ? 'RQ' : 'rq', bq = up ? 'BQ' : 'bq';
  for (i = 0; i < 4; i++) {
    for (var s = 1; ; s++) {
      t = at(f + ROOK_D[i][0] * s, r + ROOK_D[i][1] * s); if (t < 0) break;
      p = b[t]; if (p) { if (rq.indexOf(p) >= 0) return true; break; }
    }
    for (s = 1; ; s++) {
      t = at(f + BISHOP_D[i][0] * s, r + BISHOP_D[i][1] * s); if (t < 0) break;
      p = b[t]; if (p) { if (bq.indexOf(p) >= 0) return true; break; }
    }
  }
  return false;
}
function kingSq(pos, c) { var k = c === 'w' ? 'K' : 'k'; return pos.b.indexOf(k); }
function inCheck(pos, c) { var k = kingSq(pos, c || pos.turn); return k >= 0 && attacked(pos, k, other(c || pos.turn)); }

function pseudoMoves(pos, capturesOnly) {
  var b = pos.b, c = pos.turn, out = [], i, t, p, s, d;
  function add(from, to, flag) {
    var cap = flag === 'ep' ? (c === 'w' ? 'p' : 'P') : b[to];
    if (capturesOnly && !cap && !((b[from] === 'P' && to < 8) || (b[from] === 'p' && to >= 56))) return;
    if ((b[from] === 'P' && to < 8) || (b[from] === 'p' && to >= 56)) {
      ['q', 'r', 'b', 'n'].forEach(function (q) { out.push({ from: from, to: to, promo: q, cap: cap, flag: '' }); });
    } else out.push({ from: from, to: to, promo: '', cap: cap, flag: flag || '' });
  }
  for (var sq = 0; sq < 64; sq++) {
    p = b[sq]; if (!p || colorOf(p) !== c) continue;
    var f = sq & 7, r = sq >> 3, u = p.toUpperCase();
    if (u === 'P') {
      var dir = c === 'w' ? -1 : 1, start = c === 'w' ? 6 : 1;
      t = at(f, r + dir);
      if (t >= 0 && !b[t]) {
        add(sq, t);
        var t2 = at(f, r + 2 * dir);
        if (!capturesOnly && r === start && !b[t2]) add(sq, t2, 'pp');
      }
      for (d = -1; d <= 1; d += 2) {
        t = at(f + d, r + dir); if (t < 0) continue;
        if (b[t] && colorOf(b[t]) !== c) add(sq, t);
        else if (t === pos.ep) add(sq, t, 'ep');
      }
    } else if (u === 'N' || u === 'K') {
      var steps = u === 'N' ? KNIGHT : KING;
      for (i = 0; i < 8; i++) {
        t = at(f + steps[i][0], r + steps[i][1]);
        if (t >= 0 && colorOf(b[t]) !== c) add(sq, t);
      }
      if (u === 'K' && !capturesOnly) {
        var home = c === 'w' ? 60 : 4, opp = other(c);
        if (sq === home && !attacked(pos, home, opp)) {
          var ks = c === 'w' ? 'K' : 'k', qs = c === 'w' ? 'Q' : 'q', rook = c === 'w' ? 'R' : 'r';
          if (pos.castle.indexOf(ks) >= 0 && !b[home + 1] && !b[home + 2] && b[home + 3] === rook &&
              !attacked(pos, home + 1, opp) && !attacked(pos, home + 2, opp)) add(sq, home + 2, 'k');
          if (pos.castle.indexOf(qs) >= 0 && !b[home - 1] && !b[home - 2] && !b[home - 3] && b[home - 4] === rook &&
              !attacked(pos, home - 1, opp) && !attacked(pos, home - 2, opp)) add(sq, home - 2, 'q');
        }
      }
    } else {
      var dirs = u === 'R' ? ROOK_D : u === 'B' ? BISHOP_D : ROOK_D.concat(BISHOP_D);
      for (i = 0; i < dirs.length; i++) {
        for (s = 1; ; s++) {
          t = at(f + dirs[i][0] * s, r + dirs[i][1] * s); if (t < 0) break;
          if (!b[t]) { add(sq, t); continue; }
          if (colorOf(b[t]) !== c) add(sq, t);
          break;
        }
      }
    }
  }
  return out;
}

var CASTLE_LOSS = { 60: 'KQ', 56: 'Q', 63: 'K', 4: 'kq', 0: 'q', 7: 'k' };
function dropRights(castle, sq) {
  var lose = CASTLE_LOSS[sq]; if (!lose || !castle) return castle;
  for (var i = 0; i < lose.length; i++) castle = castle.replace(lose[i], '');
  return castle;
}

// Plays m on pos in place and returns what unmakeMove needs to take it back.
function makeMove(pos, m) {
  var b = pos.b, u = { castle: pos.castle, ep: pos.ep, half: pos.half, full: pos.full, moved: b[m.from], took: b[m.to] };
  var p = b[m.from], c = pos.turn;
  b[m.to] = m.promo ? (c === 'w' ? m.promo.toUpperCase() : m.promo) : p;
  b[m.from] = '';
  if (m.flag === 'ep') b[m.to + (c === 'w' ? 8 : -8)] = '';
  if (m.flag === 'k') { b[m.to - 1] = b[m.to + 1]; b[m.to + 1] = ''; }
  if (m.flag === 'q') { b[m.to + 1] = b[m.to - 2]; b[m.to - 2] = ''; }
  pos.castle = dropRights(dropRights(pos.castle, m.from), m.to);
  pos.ep = m.flag === 'pp' ? (m.from + m.to) / 2 : -1;
  pos.half = p.toUpperCase() === 'P' || m.cap ? 0 : pos.half + 1;
  if (c === 'b') pos.full++;
  pos.turn = other(c);
  return u;
}
function unmakeMove(pos, m, u) {
  var b = pos.b;
  pos.turn = other(pos.turn);
  b[m.from] = u.moved; b[m.to] = u.took;
  if (m.flag === 'ep') b[m.to + (pos.turn === 'w' ? 8 : -8)] = m.cap;
  if (m.flag === 'k') { b[m.to + 1] = b[m.to - 1]; b[m.to - 1] = ''; }
  if (m.flag === 'q') { b[m.to - 2] = b[m.to + 1]; b[m.to + 1] = ''; }
  pos.castle = u.castle; pos.ep = u.ep; pos.half = u.half; pos.full = u.full;
}

function legalMoves(pos, capturesOnly) {
  var c = pos.turn;
  return pseudoMoves(pos, capturesOnly).filter(function (m) {
    var u = makeMove(pos, m), ok = !inCheck(pos, c);
    unmakeMove(pos, m, u);
    return ok;
  });
}

function moveUci(m) { return sqName(m.from) + sqName(m.to) + (m.promo || ''); }
function findMove(pos, uci) {
  if (typeof uci !== 'string') return null;
  var ms = legalMoves(pos);
  for (var i = 0; i < ms.length; i++) if (moveUci(ms[i]) === uci) return ms[i];
  return null;
}

function attackersOf(pos, sq, by) {
  // Every square of `by`'s pieces that attacks sq: a piece moved onto sq one by one.
  var out = [], keep = pos.b[sq], turn = pos.turn, ep = pos.ep;
  pos.b[sq] = by === 'w' ? 'p' : 'P'; pos.turn = by; pos.ep = -1;
  pseudoMoves(pos, true).forEach(function (m) { if (m.to === sq && out.indexOf(m.from) < 0) out.push(m.from); });
  pos.b[sq] = keep; pos.turn = turn; pos.ep = ep;
  return out;
}
// Why the piece on `from` cannot go to `to`, when the reason is the king's safety (#465 v2): the
// piece would leave its king attacked, the king is in check, or the king would step onto or
// across an attacked square. { text, shake: [the enemy pieces to blame], king } or null: a move
// against a piece's own way of moving needs no reason (Eero's choice), and a legal one none.
// Practice mode (#465 v3): who threatens a piece and who guards it. Attackers are the other side's
// pieces that could take it now, defenders its own side's pieces that could take back (pins ignored).
function guardInfo(pos, sq) {
  var p = pos.b[sq]; if (!p) return null;
  var c = colorOf(p);
  return { attackers: attackersOf(pos, sq, other(c)), defenders: attackersOf(pos, sq, c) };
}
// What the side to move wins by taking the piece on sq, both sides then taking back on sq with
// their cheapest legal piece and each free to stop (0: taking it does not pay). Legal moves only,
// so a pinned attacker does not count, and a piece behind another joins once the first has taken.
function captureGain(pos, sq) {
  var p = pos.b[sq]; if (!p) return 0;
  var c = pos.turn, best = null;
  pseudoMoves(pos, true).forEach(function (m) {
    if (m.to !== sq || m.flag === 'ep' || (m.promo && m.promo.toUpperCase() !== 'Q')) return;
    var q = pos.b[m.from].toUpperCase(), v = q === 'K' ? 1e5 : VALUE[q];
    if (best && v >= best.v) return;
    var u = makeMove(pos, m), ok = !inCheck(pos, c); unmakeMove(pos, m, u);
    if (ok) best = { m: m, v: v };
  });
  if (!best) return 0;
  var u = makeMove(pos, best.m), g = VALUE[p.toUpperCase()] - captureGain(pos, sq); unmakeMove(pos, best.m, u);
  return Math.max(0, g);
}
// A piece the other side wins material by taking now (not just one with more attackers than
// defenders: a pawn attacked by a rook and a queen and guarded by a pawn is safe).
function hanging(pos, sq) {
  var p = pos.b[sq]; if (!p || p.toUpperCase() === 'K') return false;
  var turn = pos.turn, ep = pos.ep; pos.turn = other(colorOf(p)); pos.ep = -1;
  var g = captureGain(pos, sq); pos.turn = turn; pos.ep = ep;
  return g > 0;
}
// The mover's own pieces (not the king, not the moved one) that m leaves hanging when they were
// not before (the defence the move takes away), and whether the moved piece itself is lost at once.
function exposedBy(pos, m) {
  var c = pos.turn, before = [], out = [];
  for (var sq = 0; sq < 64; sq++) {
    var p = pos.b[sq];
    if (p && colorOf(p) === c && p.toUpperCase() !== 'K' && sq !== m.from && !hanging(pos, sq)) before.push(sq);
  }
  var u = makeMove(pos, m);
  before.forEach(function (sq) { if (sq !== m.to && pos.b[sq] && hanging(pos, sq)) out.push(sq); });
  var bad = landsBadly(pos, m.to, u.took);
  unmakeMove(pos, m, u);
  return { others: out, self: bad };
}
// The moved piece on its new square (the other side to move): taking it wins them more than the
// move itself took.
function landsBadly(pos, sq, took) {
  var p = pos.b[sq]; if (!p || p.toUpperCase() === 'K') return false;
  return captureGain(pos, sq) > (took ? VALUE[took.toUpperCase()] : 0);
}
function whyIllegal(pos, from, to) {
  var b = pos.b, p = b[from], c = pos.turn, opp = other(c);
  if (!p || colorOf(p) !== c || from === to) return null;
  if (b[to] && colorOf(b[to]) === c) return null;
  if (legalMoves(pos).some(function (m) { return m.from === from && m.to === to; })) return null;
  var u = p.toUpperCase(), king = kingSq(pos, c), checked = inCheck(pos, c);
  function res(text, shake, k) { return { text: text, shake: shake, king: k }; }
  var pseudo = pseudoMoves(pos).filter(function (m) { return m.from === from && m.to === to; })[0];
  if (pseudo) {
    var undo = makeMove(pos, pseudo), att = attackersOf(pos, kingSq(pos, c), opp);
    unmakeMove(pos, pseudo, undo);
    if (u === 'K') return res('Kuningas ei voi mennä uhatulle ruudulle.', att, to);
    if (checked) return res('Shakki! Torju se ensin.', attackersOf(pos, king, opp), king);
    return res('Nappula on sidottu: kuningas jäisi uhatuksi.', att, king);
  }
  // Castling refused because of an attack (the other castling rules are the king's own moves).
  var home = c === 'w' ? 60 : 4, df = (to & 7) - (from & 7);
  if (u === 'K' && from === home && to >> 3 === home >> 3 && Math.abs(df) === 2) {
    var right = df > 0 ? 'k' : 'q', rookSq = df > 0 ? home + 3 : home - 4;
    if (c === 'w') right = right.toUpperCase();
    var path = df > 0 ? [home + 1, home + 2] : [home - 1, home - 2, home - 3];
    if (pos.castle.indexOf(right) < 0 || b[rookSq] !== (c === 'w' ? 'R' : 'r') || path.some(function (s) { return b[s]; })) return null;
    if (checked) return res('Shakissa ei voi linnoittautua.', attackersOf(pos, home, opp), home);
    // The square the king crosses, then the one it lands on: the first one attacked is to blame.
    var pass = df > 0 ? home + 1 : home - 1, crossed = attackersOf(pos, pass, opp);
    if (crossed.length) return res('Linnoitus ei käy: kuningas kulkisi uhatun ruudun yli.', crossed, pass);
    return res('Linnoitus ei käy: kuningas päätyisi uhatulle ruudulle.', attackersOf(pos, to, opp), to);
  }
  return null;
}

// Short algebraic notation with the Finnish piece letters (K kuningas, D daami, T torni,
// L lähetti, R ratsu), as Finnish chess books write it.
var FI_LETTER = { K: 'K', Q: 'D', R: 'T', B: 'L', N: 'R', P: '' };
function moveText(pos, m) {
  if (m.flag === 'k') return 'O-O' + checkMark(pos, m);
  if (m.flag === 'q') return 'O-O-O' + checkMark(pos, m);
  var p = pos.b[m.from].toUpperCase(), s = FI_LETTER[p];
  if (p === 'P') { if (m.cap) s += FILES[m.from & 7]; }
  else {
    var same = legalMoves(pos).filter(function (o) { return o.to === m.to && o.from !== m.from && pos.b[o.from] === pos.b[m.from]; });
    if (same.length) {
      if (same.every(function (o) { return (o.from & 7) !== (m.from & 7); })) s += FILES[m.from & 7];
      else if (same.every(function (o) { return (o.from >> 3) !== (m.from >> 3); })) s += 8 - (m.from >> 3);
      else s += sqName(m.from);
    }
  }
  if (m.cap) s += 'x';
  s += sqName(m.to);
  if (m.promo) s += '=' + FI_LETTER[m.promo.toUpperCase()];
  return s + checkMark(pos, m);
}
function checkMark(pos, m) {
  var u = makeMove(pos, m), mark = '';
  if (inCheck(pos)) mark = legalMoves(pos).length ? '+' : '#';
  unmakeMove(pos, m, u);
  return mark;
}

// A game: the moves from the start, and everything derived from them.
function playGame(moves, startFen) {
  var pos = parseFen(startFen || START_FEN), keys = [posKey(pos)], played = [], texts = [];
  for (var i = 0; i < (moves || []).length; i++) {
    var m = findMove(pos, moves[i]);
    if (!m) return null;
    texts.push(moveText(pos, m));
    makeMove(pos, m); keys.push(posKey(pos)); played.push(m);
  }
  return { pos: pos, keys: keys, moves: played, uci: played.map(moveUci), texts: texts };
}

function insufficient(pos) {
  var minors = [], light = [];
  for (var i = 0; i < 64; i++) {
    var p = pos.b[i]; if (!p) continue;
    var u = p.toUpperCase();
    if (u === 'K') continue;
    if (u === 'B' || u === 'N') { minors.push(u); light.push(((i & 7) + (i >> 3)) & 1); continue; }
    return false;
  }
  if (minors.length <= 1) return true;
  // Only bishops, all on squares of one colour.
  return minors.every(function (u) { return u === 'B'; }) && light.every(function (x) { return x === light[0]; });
}

// {over, result: '1-0' | '0-1' | '½-½', why: 'matti' | 'patti' | 'toisto' | '50' | 'materiaali'}
function gameStatus(game) {
  var pos = game.pos, ms = legalMoves(pos);
  if (!ms.length) {
    if (inCheck(pos)) return { over: true, result: pos.turn === 'w' ? '0-1' : '1-0', why: 'matti', winner: other(pos.turn) };
    return { over: true, result: '½-½', why: 'patti', winner: '' };
  }
  if (insufficient(pos)) return { over: true, result: '½-½', why: 'materiaali', winner: '' };
  if (pos.half >= 100) return { over: true, result: '½-½', why: '50', winner: '' };
  var last = game.keys[game.keys.length - 1];
  if (game.keys.filter(function (k) { return k === last; }).length >= 3) return { over: true, result: '½-½', why: 'toisto', winner: '' };
  return { over: false, check: inCheck(pos), result: '', why: '', winner: '' };
}

// ---- The computer player ----

var VALUE = { P: 100, N: 320, B: 330, R: 500, Q: 900, K: 0 };
// Piece-square tables from white's side, row 0 = 8th rank (the well-known simplified tables).
var PST = {
  P: [0, 0, 0, 0, 0, 0, 0, 0, 50, 50, 50, 50, 50, 50, 50, 50, 10, 10, 20, 30, 30, 20, 10, 10, 5, 5, 10, 25, 25, 10, 5, 5,
    0, 0, 0, 20, 20, 0, 0, 0, 5, -5, -10, 0, 0, -10, -5, 5, 5, 10, 10, -20, -20, 10, 10, 5, 0, 0, 0, 0, 0, 0, 0, 0],
  N: [-50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0, 0, 0, 0, -20, -40, -30, 0, 10, 15, 15, 10, 0, -30, -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30, -30, 5, 10, 15, 15, 10, 5, -30, -40, -20, 0, 5, 5, 0, -20, -40, -50, -40, -30, -30, -30, -30, -40, -50],
  B: [-20, -10, -10, -10, -10, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10, -10, 0, 5, 10, 10, 5, 0, -10, -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 10, 10, 10, 10, 0, -10, -10, 10, 10, 10, 10, 10, 10, -10, -10, 5, 0, 0, 0, 0, 5, -10, -20, -10, -10, -10, -10, -10, -10, -20],
  R: [0, 0, 0, 0, 0, 0, 0, 0, 5, 10, 10, 10, 10, 10, 10, 5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, 0, 0, 0, 5, 5, 0, 0, 0],
  Q: [-20, -10, -10, -5, -5, -10, -10, -20, -10, 0, 0, 0, 0, 0, 0, -10, -10, 0, 5, 5, 5, 5, 0, -10, -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5, -10, 5, 5, 5, 5, 5, 0, -10, -10, 0, 5, 0, 0, 0, 0, -10, -20, -10, -10, -5, -5, -10, -10, -20],
  K: [-30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20, -10, -20, -20, -20, -20, -20, -20, -10, 20, 20, 0, 0, 0, 0, 20, 20, 20, 30, 10, 0, 0, 10, 30, 20],
  KE: [-50, -40, -30, -20, -20, -30, -40, -50, -30, -20, -10, 0, 0, -10, -20, -30, -30, -10, 20, 30, 30, 20, -10, -30, -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30, -30, -10, 20, 30, 30, 20, -10, -30, -30, -30, 0, 0, 0, 0, -30, -30, -50, -30, -30, -30, -30, -30, -30, -50]
};

// Score from the side to move's view, in centipawns.
function evaluate(pos) {
  var b = pos.b, score = 0, heavy = 0, i, p;
  for (i = 0; i < 64; i++) { p = b[i]; if (p && 'QqRr'.indexOf(p) >= 0) heavy += VALUE[p.toUpperCase()]; }
  var endgame = heavy <= 1300;
  for (i = 0; i < 64; i++) {
    p = b[i]; if (!p) continue;
    var u = p.toUpperCase(), white = p === u, table = u === 'K' && endgame ? PST.KE : PST[u];
    var v = VALUE[u] + table[white ? i : (7 - (i >> 3)) * 8 + (i & 7)];
    score += white ? v : -v;
  }
  return pos.turn === 'w' ? score : -score;
}

var MATE = 100000;
// The levels the player picks, easiest first. depth: whole moves searched (plus captures to the
// end); noise: random centipawns added to each first move, so lower levels make human mistakes;
// blunder: the chance of playing a random legal move instead.
var LEVELS = [
  { name: 'Aloittelija', depth: 1, noise: 260, blunder: 0.25, ms: 300 },
  { name: 'Helppo', depth: 1, noise: 110, blunder: 0.08, ms: 400 },
  { name: 'Keskitaso', depth: 2, noise: 40, blunder: 0, ms: 700 },
  { name: 'Vaikea', depth: 3, noise: 12, blunder: 0, ms: 1200 },
  { name: 'Mestari', depth: 5, noise: 0, blunder: 0, ms: 1600 }
];

function orderMoves(pos, ms, first) {
  ms.forEach(function (m) {
    m.sort = (m.cap ? 10 * VALUE[m.cap.toUpperCase()] - VALUE[pos.b[m.from].toUpperCase()] / 10 + 1000 : 0) + (m.promo === 'q' ? 900 : 0);
    if (first && m.from === first.from && m.to === first.to && m.promo === first.promo) m.sort = 1e9;
  });
  ms.sort(function (a, b) { return b.sort - a.sort; });
  return ms;
}

function Search(deadline) { this.deadline = deadline; this.nodes = 0; this.stopped = false; }
Search.prototype.timeUp = function () {
  if ((++this.nodes & 1023) === 0 && Date.now() > this.deadline) this.stopped = true;
  return this.stopped;
};
Search.prototype.quiesce = function (pos, alpha, beta, qdepth) {
  if (this.timeUp()) return 0;
  var stand = evaluate(pos);
  if (stand >= beta) return stand;
  if (stand > alpha) alpha = stand;
  if (qdepth > 6) return stand;
  var ms = orderMoves(pos, pseudoMoves(pos, true)), c = pos.turn;
  for (var i = 0; i < ms.length; i++) {
    var m = ms[i], u = makeMove(pos, m);
    if (inCheck(pos, c)) { unmakeMove(pos, m, u); continue; }
    var s = -this.quiesce(pos, -beta, -alpha, qdepth + 1);
    unmakeMove(pos, m, u);
    if (this.stopped) return 0;
    if (s >= beta) return s;
    if (s > alpha) alpha = s;
  }
  return alpha;
};
Search.prototype.negamax = function (pos, depth, alpha, beta, ply, keys) {
  if (this.timeUp()) return 0;
  // A repeated position or the 50-move rule is a draw for the search.
  if (ply > 0 && (pos.half >= 100 || keys.indexOf(posKey(pos)) >= 0)) return 0;
  var check = inCheck(pos);
  if (check) depth++;
  if (depth <= 0) return this.quiesce(pos, alpha, beta, 0);
  var ms = orderMoves(pos, pseudoMoves(pos)), c = pos.turn, any = false, best = -MATE;
  var key = posKey(pos);
  keys.push(key);
  for (var i = 0; i < ms.length; i++) {
    var m = ms[i], u = makeMove(pos, m);
    if (inCheck(pos, c)) { unmakeMove(pos, m, u); continue; }
    any = true;
    var s = -this.negamax(pos, depth - 1, -beta, -alpha, ply + 1, keys);
    unmakeMove(pos, m, u);
    if (this.stopped) { keys.pop(); return 0; }
    if (s > best) best = s;
    if (s > alpha) alpha = s;
    if (alpha >= beta) break;
  }
  keys.pop();
  if (!any) return check ? -MATE + ply : 0;
  return best;
};

// The computer's move for the side to move. history: the game's position keys so far (for
// repetition). rand: a function returning [0, 1), Math.random by default.
function computerMove(pos, level, history, rand) {
  rand = rand || Math.random;
  var L = LEVELS[Math.max(0, Math.min(LEVELS.length - 1, level | 0))];
  var work = clonePos(pos), ms = legalMoves(work);
  if (!ms.length) return null;
  if (ms.length === 1) return ms[0];
  if (L.blunder && rand() < L.blunder) return ms[Math.floor(rand() * ms.length)];
  var search = new Search(Date.now() + L.ms), keys = (history || []).slice(0, -1);
  var noise = ms.map(function () { return (rand() * 2 - 1) * L.noise; });
  var scores = null, best = null, prevBest = null;
  for (var d = 1; d <= L.depth; d++) {
    orderMoves(work, ms, prevBest);
    var these = [], alpha = -MATE * 2;
    for (var i = 0; i < ms.length; i++) {
      var m = ms[i], u = makeMove(work, m);
      // With noise every first move needs its own score, so no cut at the root.
      var s = -search.negamax(work, d - 1, -MATE * 2, L.noise ? MATE * 2 : -alpha, 1, keys.concat([posKey(pos)]));
      unmakeMove(work, m, u);
      if (search.stopped) break;
      these.push({ m: m, s: s });
      if (s > alpha) alpha = s;
    }
    if (search.stopped && scores) break;
    scores = these;
    if (search.stopped) break;
    var top = scores.reduce(function (a, b) { return b.s > a.s ? b : a; });
    prevBest = top.m;
    if (top.s > MATE - 100) break;
  }
  if (!scores || !scores.length) return ms[0];
  scores.forEach(function (x) { x.n = x.s + noise[ms.indexOf(x.m)] * (Math.abs(x.s) > MATE - 1000 ? 0 : 1); });
  best = scores.reduce(function (a, b) { return b.n > a.n ? b : a; });
  return best.m;
}

if (typeof module !== 'undefined') module.exports = { START_FEN: START_FEN, parseFen: parseFen, toFen: toFen, legalMoves: legalMoves, playGame: playGame, gameStatus: gameStatus, computerMove: computerMove };
