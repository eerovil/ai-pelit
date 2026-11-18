'use strict';
// Shakki's drawing: the board, the pieces (drawn as shapes, so no font decides how they look),
// highlights and the captured pieces. Draws only when asked (askDraw), never every frame.

var canvas = document.getElementById('c'), ctx = canvas.getContext('2d');
var view = { w: 0, h: 0, dpr: 1, x: 0, y: 0, s: 0, cell: 0, land: false };
var COLORS = { light: '#efdcb6', dark: '#b88a5c', last: 'rgba(246, 214, 79, 0.55)', sel: 'rgba(110, 200, 120, 0.6)',
  dot: 'rgba(28, 52, 34, 0.38)', check: 'rgba(230, 50, 40, 0.85)' };

// ---- Pieces, in a 100 × 100 box ----
function piecePath(c, u) {
  c.beginPath();
  if (u === 'P') {
    c.arc(50, 30, 13, 0, Math.PI * 2);
    c.moveTo(39, 44); c.quadraticCurveTo(50, 38, 61, 44); c.lineTo(66, 72); c.lineTo(34, 72); c.closePath();
    c.moveTo(24, 74); c.lineTo(76, 74); c.lineTo(78, 86); c.lineTo(22, 86); c.closePath();
  } else if (u === 'R') {
    c.moveTo(27, 16); c.lineTo(37, 16); c.lineTo(37, 24); c.lineTo(45, 24); c.lineTo(45, 16); c.lineTo(55, 16);
    c.lineTo(55, 24); c.lineTo(63, 24); c.lineTo(63, 16); c.lineTo(73, 16); c.lineTo(73, 34); c.lineTo(66, 40);
    c.lineTo(67, 70); c.lineTo(33, 70); c.lineTo(34, 40); c.lineTo(27, 34); c.closePath();
    c.moveTo(24, 73); c.lineTo(76, 73); c.lineTo(79, 86); c.lineTo(21, 86); c.closePath();
  } else if (u === 'N') {
    c.moveTo(30, 84); c.lineTo(31, 70); c.quadraticCurveTo(34, 58, 46, 52); c.quadraticCurveTo(38, 52, 30, 58);
    c.lineTo(22, 52); c.quadraticCurveTo(26, 36, 40, 26); c.lineTo(42, 14); c.lineTo(50, 22);
    c.quadraticCurveTo(70, 22, 76, 46); c.quadraticCurveTo(80, 64, 74, 84); c.closePath();
  } else if (u === 'B') {
    c.arc(50, 15, 6, 0, Math.PI * 2);
    c.moveTo(50, 22); c.bezierCurveTo(30, 34, 32, 58, 42, 64); c.lineTo(58, 64); c.bezierCurveTo(68, 58, 70, 34, 50, 22); c.closePath();
    c.moveTo(38, 66); c.lineTo(62, 66); c.lineTo(66, 74); c.lineTo(34, 74); c.closePath();
    c.moveTo(24, 76); c.lineTo(76, 76); c.lineTo(78, 87); c.lineTo(22, 87); c.closePath();
  } else if (u === 'Q') {
    c.moveTo(22, 30); c.lineTo(34, 56); c.lineTo(38, 22); c.lineTo(50, 52); c.lineTo(62, 22); c.lineTo(66, 56);
    c.lineTo(78, 30); c.lineTo(70, 70); c.lineTo(30, 70); c.closePath();
    [[22, 27], [38, 18], [50, 14], [62, 18], [78, 27]].forEach(function (p) { c.moveTo(p[0] + 5, p[1]); c.arc(p[0], p[1], 5, 0, Math.PI * 2); });
    c.moveTo(25, 73); c.lineTo(75, 73); c.lineTo(78, 86); c.lineTo(22, 86); c.closePath();
  } else if (u === 'K') {
    c.moveTo(46, 6); c.lineTo(54, 6); c.lineTo(54, 13); c.lineTo(61, 13); c.lineTo(61, 20); c.lineTo(54, 20); c.lineTo(54, 28);
    c.lineTo(46, 28); c.lineTo(46, 20); c.lineTo(39, 20); c.lineTo(39, 13); c.lineTo(46, 13); c.closePath();
    c.moveTo(50, 32); c.bezierCurveTo(34, 26, 16, 34, 24, 52); c.lineTo(32, 70); c.lineTo(68, 70); c.lineTo(76, 52);
    c.bezierCurveTo(84, 34, 66, 26, 50, 32); c.closePath();
    c.moveTo(25, 73); c.lineTo(75, 73); c.lineTo(78, 86); c.lineTo(22, 86); c.closePath();
  }
}
function pieceDetails(c, u) {
  c.beginPath();
  if (u === 'N') { c.arc(57, 36, 3.5, 0, Math.PI * 2); c.moveTo(50, 24); c.quadraticCurveTo(64, 44, 60, 84); }
  if (u === 'B') { c.moveTo(48, 36); c.lineTo(56, 46); }
  if (u === 'Q' || u === 'K') { c.moveTo(32, 62); c.lineTo(68, 62); }
  if (u === 'R') { c.moveTo(34, 40); c.lineTo(66, 40); }
}
var pieceCache = {};
// A piece drawn once at size px (device pixels), kept as its own canvas.
function pieceImage(p, px) {
  var key = p + px;
  if (pieceCache[key]) return pieceCache[key];
  var img = document.createElement('canvas'); img.width = img.height = px;
  var c = img.getContext('2d'), u = p.toUpperCase(), white = p === u;
  c.scale(px / 100, px / 100);
  c.lineJoin = 'round'; c.lineCap = 'round';
  piecePath(c, u);
  c.fillStyle = white ? '#fbf6ea' : '#2b2622'; c.fill();
  c.lineWidth = 3.4; c.strokeStyle = white ? '#2b2622' : '#0d0b0a'; c.stroke();
  pieceDetails(c, u);
  c.lineWidth = 2.6; c.strokeStyle = white ? '#2b2622' : '#e8dcc6'; c.stroke();
  pieceCache[key] = img;
  return img;
}
function drawPiece(c, p, x, y, size) {
  var px = Math.max(8, Math.round(size * view.dpr));
  c.drawImage(pieceImage(p, px), x, y, size, size);
}

// ---- Layout ----
// The board fills what the panels leave; the panels are the DOM's (#pa, #pb), placed here.
function layout() {
  var r = canvas.getBoundingClientRect(), w = Math.round(r.width), h = Math.round(r.height);
  var dpr = Math.min(window.devicePixelRatio || 1, 3);
  if (!w || !h) return false;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  }
  var land = w > h, s, x, y, pa = document.getElementById('pa'), pb = document.getElementById('pb');
  if (land) {
    s = Math.min(h - 16, w - 2 * 150); s = Math.floor(s / 8) * 8;
    x = Math.round((w - s) / 2); y = Math.round((h - s) / 2);
    place(pa, 0, 0, x - 6, h); place(pb, x + s + 6, 0, w - x - s - 6, h);
  } else {
    // The top keeps the back chip, a name and the taken pieces; the bottom also the buttons.
    s = Math.min(w - 12, h - 108 - 162); s = Math.floor(s / 8) * 8;
    x = Math.round((w - s) / 2); y = Math.max(108, Math.round((h - s) * 0.42));
    place(pa, 0, 0, w, y - 4); place(pb, 0, y + s + 4, w, h - y - s - 4);
  }
  document.body.classList.toggle('land', land);
  view = { w: w, h: h, dpr: dpr, x: x, y: y, s: s, cell: s / 8, land: land };
  return true;
}
function place(el, x, y, w, h) {
  el.style.left = x + 'px'; el.style.top = y + 'px'; el.style.width = Math.max(0, w) + 'px'; el.style.height = Math.max(0, h) + 'px';
}

// Board square <-> screen. The player's own colour sits at the bottom.
function flipped() { return bottomColor() === 'b'; }
function squareXY(sq) {
  var f = sq & 7, r = sq >> 3;
  if (flipped()) { f = 7 - f; r = 7 - r; }
  return [view.x + f * view.cell, view.y + r * view.cell];
}
function squareAt(px, py) {
  var f = Math.floor((px - view.x) / view.cell), r = Math.floor((py - view.y) / view.cell);
  if (f < 0 || f > 7 || r < 0 || r > 7) return -1;
  if (flipped()) { f = 7 - f; r = 7 - r; }
  return r * 8 + f;
}

// ---- Drawing ----
var drawQueued = false;
function askDraw() {
  if (drawQueued) return;
  drawQueued = true;
  requestAnimationFrame(function () { drawQueued = false; draw(); });
}
function draw() {
  if (!view.s && !layout()) return;
  var c = ctx, cell = view.cell, now = performance.now();
  c.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
  c.clearRect(0, 0, view.w, view.h);
  // Frame around the board.
  c.fillStyle = '#5a3d27'; roundRect(c, view.x - 5, view.y - 5, view.s + 10, view.s + 10, 6); c.fill();
  var g = current(), pos = g ? g.pos : parseFen(START_FEN), last = g && g.moves.length ? g.moves[g.moves.length - 1] : null;
  var targets = selected >= 0 ? movesFrom(selected) : [];
  var checkSq = g && !gameOver() && inCheck(pos) ? kingSq(pos, pos.turn) : (g && result && result.why === 'matti' ? kingSq(pos, pos.turn) : -1);
  for (var sq = 0; sq < 64; sq++) {
    var xy = squareXY(sq), light = ((sq & 7) + (sq >> 3)) % 2 === 0;
    c.fillStyle = light ? COLORS.light : COLORS.dark; c.fillRect(xy[0], xy[1], cell, cell);
    if (last && (sq === last.from || sq === last.to)) { c.fillStyle = COLORS.last; c.fillRect(xy[0], xy[1], cell, cell); }
    if (sq === selected) { c.fillStyle = COLORS.sel; c.fillRect(xy[0], xy[1], cell, cell); }
    if (sq === checkSq) {
      var grd = c.createRadialGradient(xy[0] + cell / 2, xy[1] + cell / 2, cell * 0.1, xy[0] + cell / 2, xy[1] + cell / 2, cell * 0.7);
      grd.addColorStop(0, COLORS.check); grd.addColorStop(1, 'rgba(230,50,40,0)');
      c.fillStyle = grd; c.fillRect(xy[0], xy[1], cell, cell);
    }
  }
  // Coordinates on the edge squares, small, in the other square colour.
  c.font = '600 ' + Math.max(8, Math.round(cell * 0.2)) + 'px system-ui, sans-serif';
  for (var i = 0; i < 8; i++) {
    var fileSq = flipped() ? 7 - i : i, rankSq = flipped() ? 7 - i : i;
    c.fillStyle = i % 2 ? COLORS.light : COLORS.dark;
    c.textAlign = 'right'; c.textBaseline = 'bottom';
    c.fillText(FILES[fileSq], view.x + (i + 1) * cell - 2, view.y + view.s - 1);
    c.fillStyle = i % 2 ? COLORS.dark : COLORS.light;
    c.textAlign = 'left'; c.textBaseline = 'top';
    c.fillText(String(8 - rankSq), view.x + 2, view.y + i * cell + 2);
  }
  // Pieces; the moving one is drawn last, on its way.
  var moving = anim && now < anim.t0 + anim.dur ? anim : null;
  for (sq = 0; sq < 64; sq++) {
    var p = pos.b[sq]; if (!p) continue;
    if (moving && sq === moving.to) continue;
    if (drag && drag.moved && sq === drag.from) continue;
    xy = squareXY(sq); drawPiece(c, p, xy[0], xy[1], cell);
  }
  // Where the selected piece can go: a dot on an empty square, a ring around a piece.
  targets.forEach(function (m) {
    var t = squareXY(m.to), cx = t[0] + cell / 2, cy = t[1] + cell / 2;
    c.fillStyle = c.strokeStyle = COLORS.dot;
    if (m.cap && m.flag !== 'ep') { c.lineWidth = cell * 0.08; c.beginPath(); c.arc(cx, cy, cell * 0.44, 0, Math.PI * 2); c.stroke(); }
    else { c.beginPath(); c.arc(cx, cy, cell * 0.15, 0, Math.PI * 2); c.fill(); }
  });
  if (moving) {
    var k = Math.min(1, (now - moving.t0) / moving.dur), e = k * (2 - k);
    var a = squareXY(moving.from), b = squareXY(moving.to);
    drawPiece(c, pos.b[moving.to], a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, cell);
    askDraw();
  } else anim = null;
  if (drag && drag.moved && pos.b[drag.from]) drawPiece(c, pos.b[drag.from], drag.x - cell * 0.6, drag.y - cell * 0.9, cell * 1.2);
  drawCaptured(c, g);
}
function roundRect(c, x, y, w, h, r) {
  c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath();
}

// The pieces each side has taken, beside its name, with the material lead: read from the moves
// played, so a promoted pawn that is taken later counts as the piece it became.
function capturedBy(g) {
  var out = { w: [], b: [] }, order = 'QRBNP';
  if (g) g.moves.forEach(function (m) { if (m.cap) out[other(colorOf(m.cap))].push(m.cap); });
  ['w', 'b'].forEach(function (c) {
    out[c].sort(function (x, y) { return order.indexOf(x.toUpperCase()) - order.indexOf(y.toUpperCase()); });
  });
  return out;
}
function material(list) { return list.reduce(function (n, p) { return n + VALUE[p.toUpperCase()]; }, 0); }
function drawCaptured(c, g) {
  var caps = capturedBy(g), me = bottomColor(), them = other(me);
  var lead = Math.round((material(caps[me]) - material(caps[them])) / 100);
  var boxes = capturedBoxes();
  drawCapRow(c, caps[them], boxes.top, lead < 0 ? '+' + -lead : '');
  drawCapRow(c, caps[me], boxes.bottom, lead > 0 ? '+' + lead : '');
}
function capturedBoxes() {
  var cell = view.cell;
  if (view.land) {
    var pw = view.x - 18;
    return { top: { x: 10, y: 92, w: pw, size: Math.min(22, pw / 8) },
      bottom: { x: view.x + view.s + 14, y: 92, w: view.w - view.x - view.s - 24, size: Math.min(22, pw / 8) } };
  }
  return { top: { x: view.x, y: view.y - 30, w: view.s, size: 22 }, bottom: { x: view.x, y: view.y + view.s + 8, w: view.s, size: 22 } };
}
function drawCapRow(c, list, box, lead) {
  var size = box.size, step = size * 0.62, spots = [], x = box.x, y = box.y, last = '', right = box.x;
  list.forEach(function (p) {
    if (last && last !== p) x += size * 0.28;
    if (x + size > box.x + box.w) { x = box.x; y += size + 2; }
    spots.push([p, x, y]); right = Math.max(right, x + size); x += step; last = p;
  });
  // A light strip behind them, so a black piece shows on the dark table.
  if (list.length) {
    c.fillStyle = 'rgba(239, 220, 182, 0.22)';
    roundRect(c, box.x - 3, box.y - 2, right - box.x + 6, y - box.y + size + 4, 6); c.fill();
  }
  spots.forEach(function (s) { drawPiece(c, s[0], s[1], s[2], size); });
  if (lead) {
    c.fillStyle = '#f1e6cf'; c.font = '700 13px system-ui, sans-serif'; c.textAlign = 'left'; c.textBaseline = 'middle';
    c.fillText(lead, right + 8, y + size / 2);
  }
}
