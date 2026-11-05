'use strict';

// The board rules deliberately have no DOM or animation.  This makes a level reproducible from
// its saved seed and lets the tests play thousands of swaps without waiting for the screen.
var Marjakori = (function () {
  var SIZE = 7;
  function rng(seed) { var s = seed >>> 0; return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
  function clone(v) { var copy = JSON.parse(JSON.stringify(v)); if (v.random) copy.random = v.random; return copy; }
  function at(i) { return { x: i % SIZE, y: Math.floor(i / SIZE) }; }
  function adjacent(a, b) { var p = at(a), q = at(b); return Math.abs(p.x - q.x) + Math.abs(p.y - q.y) === 1; }
  function levelSpec(n) {
    n = Math.max(1, Math.floor(n || 1));
    return { kinds: n < 4 ? 5 : 6, moves: Math.max(16, 20 - Math.floor((n - 1) / 5)),
      target: (n - 1) % (n < 4 ? 5 : 6), need: 10 + Math.min(n, 30) * 2,
      moss: n < 5 ? 0 : Math.min(12, 2 + Math.floor(n / 2)) };
  }
  function cell(kind, moss) { return { kind: kind, moss: !!moss, special: '' }; }
  function runs(board) {
    var found = [], x, y, i, j, kind;
    for (y = 0; y < SIZE; y++) for (x = 0; x < SIZE;) {
      i = y * SIZE + x; kind = board[i].kind; j = x + 1;
      while (j < SIZE && board[y * SIZE + j].kind === kind) j++;
      if (j - x >= 3) found.push({ cells: range(i, y * SIZE + j), horizontal: true });
      x = j;
    }
    for (x = 0; x < SIZE; x++) for (y = 0; y < SIZE;) {
      i = y * SIZE + x; kind = board[i].kind; j = y + 1;
      while (j < SIZE && board[j * SIZE + x].kind === kind) j++;
      if (j - y >= 3) { var cells = []; for (var yy = y; yy < j; yy++) cells.push(yy * SIZE + x); found.push({ cells: cells, horizontal: false }); }
      y = j;
    }
    return found;
  }
  function range(a, b) { var r = []; for (var i = a; i < b; i++) r.push(i); return r; }
  function matched(board) { var s = new Set(); runs(board).forEach(function (r) { r.cells.forEach(function (i) { s.add(i); }); }); return s; }
  function swap(board, a, b) { var c = board[a]; board[a] = board[b]; board[b] = c; }
  function hasMove(board) {
    for (var i = 0; i < board.length; i++) for (var d of [1, SIZE]) {
      var q = i + d, p = at(i); if (q >= board.length || (d === 1 && p.x === SIZE - 1)) continue;
      if (board[i].special || board[q].special) return true;
      swap(board, i, q); var yes = matched(board).size > 0; swap(board, i, q); if (yes) return true;
    }
    return false;
  }
  function fresh(level, seed) {
    var spec = levelSpec(level), random = rng(seed), board = [];
    for (var i = 0; i < SIZE * SIZE; i++) {
      var choices = range(0, spec.kinds); var p = at(i);
      if (p.x >= 2 && board[i - 1].kind === board[i - 2].kind) choices = choices.filter(function (k) { return k !== board[i - 1].kind; });
      if (p.y >= 2 && board[i - SIZE].kind === board[i - 2 * SIZE].kind) choices = choices.filter(function (k) { return k !== board[i - SIZE].kind; });
      board.push(cell(choices[Math.floor(random() * choices.length)], false));
    }
    var moss = range(0, board.length).sort(function () { return random() - .5; }).slice(0, spec.moss);
    moss.forEach(function (i) { board[i].moss = true; });
    while (matched(board).size || !hasMove(board)) board.sort(function () { return random() - .5; });
    return { level: level, seed: seed >>> 0, random: random, board: board, moves: spec.moves,
      target: spec.target, left: spec.need, mossLeft: spec.moss, score: 0, chain: 0, phase: 'play' };
  }
  function newLevel(level, seed) { return fresh(level, seed == null ? (Date.now() >>> 0) : seed); }
  function specialFor(board, hit, place) {
    var rs = runs(board), long = rs.some(function (r) { return r.cells.length >= 5; });
    var crosses = 0; rs.forEach(function (r) { if (r.cells.indexOf(place) >= 0) crosses++; });
    if (long || crosses >= 2) return 'kimallus';
    return rs.some(function (r) { return r.cells.length === 4 && r.cells.indexOf(place) >= 0; }) ? 'puuska' : '';
  }
  function explodeSpecial(board, clear) {
    var more = true;
    while (more) { more = false; Array.from(clear).forEach(function (i) {
      var c = board[i]; if (!c || !c.special) return;
      var add = []; if (c.special === 'puuska') { var p = at(i); add = range(p.y * SIZE, p.y * SIZE + SIZE); }
      else { for (var j = 0; j < board.length; j++) if (board[j].kind === c.kind) add.push(j); }
      c.special = ''; add.forEach(function (j) { if (!clear.has(j)) { clear.add(j); more = true; } });
    }); }
  }
  function fall(s) {
    var random = s.random, kinds = levelSpec(s.level).kinds;
    for (var x = 0; x < SIZE; x++) { var kept = [];
      for (var y = SIZE - 1; y >= 0; y--) { var c = s.board[y * SIZE + x]; if (c) kept.push(c); }
      for (var yy = SIZE - 1, k = 0; yy >= 0; yy--, k++) s.board[yy * SIZE + x] = kept[k] || cell(Math.floor(random() * kinds), false);
    }
  }
  function resolve(s, placed) {
    var wave = 0, total = 0;
    while (true) {
      var clear = matched(s.board); if (!clear.size) break;
      var special = wave === 0 ? specialFor(s.board, clear, placed) : '';
      explodeSpecial(s.board, clear);
      clear.forEach(function (i) { var c = s.board[i]; if (c.kind === s.target) s.left = Math.max(0, s.left - 1); if (c.moss) s.mossLeft = Math.max(0, s.mossLeft - 1); s.board[i] = null; });
      var n = clear.size; total += (n >= 5 ? 100 : n === 4 ? 60 : 30) * Math.min(5, wave + 1) + (s.mossLeft < levelSpec(s.level).moss ? 10 : 0);
      fall(s); wave++;
      if (special) { s.board[placed].special = special; break; }
    }
    s.chain = Math.max(0, wave - 1); s.score += total;
  }
  function trySwap(s, a, b) {
    if (s.phase !== 'play' || !adjacent(a, b)) return { ok: false };
    var first = s.board[a], second = s.board[b], special = first.special || second.special;
    swap(s.board, a, b);
    if (!special && !matched(s.board).size) { swap(s.board, a, b); return { ok: false }; }
    s.moves--; if (special) { var clear = new Set([a, b]); explodeSpecial(s.board, clear); clear.forEach(function (i) { var c = s.board[i]; if (c.kind === s.target) s.left = Math.max(0, s.left - 1); if (c.moss) s.mossLeft = Math.max(0, s.mossLeft - 1); s.board[i] = null; }); fall(s); s.score += clear.size * 30; }
    else resolve(s, b);
    if (!hasMove(s.board)) shuffle(s);
    if (s.left === 0 && s.mossLeft === 0) { s.score += s.moves * 50; s.phase = 'win'; }
    else if (s.moves <= 0) s.phase = 'lose';
    return { ok: true, phase: s.phase, chain: s.chain };
  }
  function shuffle(s) { var r = s.random, attempts = 0; do { s.board.sort(function () { return r() - .5; }); attempts++; } while ((matched(s.board).size || !hasMove(s.board)) && attempts < 80); return s; }
  function legalMoves(s) { var out = []; for (var i = 0; i < s.board.length; i++) for (var d of [1, SIZE]) { var b = i + d, p = at(i); if (b >= s.board.length || (d === 1 && p.x === SIZE - 1)) continue; var t = clone(s); if (trySwap(t, i, b).ok) out.push([i, b]); } return out; }
  return { SIZE: SIZE, newLevel: newLevel, levelSpec: levelSpec, runs: runs, matched: matched, hasMove: hasMove, trySwap: trySwap, shuffle: shuffle, legalMoves: legalMoves, clone: clone };
}());
