'use strict';
// Pomppukeppi v1 (#482): the rules, in plain numbers. Four hares on pogo sticks hop over a tile
// board, one square per hop. Each landing paints the square in the hare's colour; a hop onto the
// cash-in box turns all of the hare's squares into points and clears them. After ERA_T seconds the
// most points wins the erä, and WINS_TO erät win the match. Nothing here draws or touches the
// page, so the tests and the host in a room run the same rules.
//
// A hare always bounces: while it is in the air it goes from (fx, fy) to (x, y), with p from 0 to 1;
// a hop in place has the same from and to. On landing it reads `want` (0 right, 1 down, 2 left,
// 3 up, -1 none) and starts its next hop. The square it is hopping to is claimed by it; a square
// is free only when no other hare is hopping to it or is still on it (the first half of its hop).

const TAU = Math.PI * 2;
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

const HOP_T = 0.32, FAST_HOP_T = 0.2, FAST_T = 5, STUN_T = 1.5;
const COUNT_T = 3, ERA_T = 60, ERA_PAUSE = 2.6, WINS_TO = 2;
const CASH_GAP = 3, QBOX_FIRST = 8, QBOX_GAP = 12, QBOX_LIFE = 9;
const DIRS = [[1, 0], [0, 1], [-1, 0], [0, -1]];
const BLANK = -1, ROCK = -2, HOLE = -3;
const COLORS = ['#e8323f', '#2f74e8', '#f2c21a', '#27a84c'];
const COLOR_NAMES = ['Punainen', 'Sininen', 'Keltainen', 'Vihreä'];

// The boards (spec D9). `rocks` and `holes` block a hop; on Aitaus a closed ring fills.
// `cpu`: the computer's skill there (ai.js).
const BOARDS = [
  { name: 'Niitty', note: 'Tasainen niitty', n: 8, rocks: [], holes: [], fill: false,
    cpu: { cashAt: [7, 12], err: 0.16, react: 0.34 } },
  { name: 'Kivikko', note: 'Kiviä ja kuoppia', n: 8, rocks: [[2, 2], [5, 5], [5, 2]], holes: [[2, 5], [3, 3], [4, 4]], fill: false,
    cpu: { cashAt: [8, 13], err: 0.1, react: 0.26 } },
  { name: 'Aitaus', note: 'Saarra alue, se täyttyy', n: 9, rocks: [[4, 4]], holes: [], fill: true,
    cpu: { cashAt: [10, 16], err: 0.07, react: 0.2 } },
];

function newWorld(boardN, players, seed) {
  const B = BOARDS[boardN - 1], n = B.n;
  const w = {
    board: boardN, n, fill: B.fill, seed, rand: rng(seed),
    tiles: new Array(n * n).fill(BLANK),
    hares: [], ph: 'count', cd: COUNT_T, t: 0, era: 1, pause: 0,
    cash: null, cashT: 1.2, qbox: null, qT: QBOX_FIRST, eraWin: null, winner: null, over: false,
  };
  for (const [x, y] of B.rocks) w.tiles[y * n + x] = ROCK;
  for (const [x, y] of B.holes) w.tiles[y * n + x] = HOLE;
  players.slice(0, 4).forEach((p, i) => w.hares.push({
    i, id: p.id, name: p.name, kind: p.kind, col: p.col == null ? i : p.col, own: 0,
    x: 0, y: 0, fx: 0, fy: 0, p: 1, hopT: HOP_T, want: -1,
    pts: 0, wins: 0, best: 0, fast: 0, stun: 0, hopN: 0, bumpN: 0, cashN: 0, lastCash: 0, got: 0, gotK: '', helped: false,
  }));
  resetEra(w);
  return w;
}
const CORNERS = n => [[0, 0], [n - 1, n - 1], [n - 1, 0], [0, n - 1]];
// A new erä: a clean board, everyone in their corner, the countdown. Wins are kept.
function resetEra(w) {
  const n = w.n, B = BOARDS[w.board - 1];
  w.tiles.fill(BLANK);
  for (const [x, y] of B.rocks) w.tiles[y * n + x] = ROCK;
  for (const [x, y] of B.holes) w.tiles[y * n + x] = HOLE;
  w.hares.forEach((h, k) => {
    const [x, y] = CORNERS(n)[k];
    h.x = h.fx = x; h.y = h.fy = y; h.p = 1; h.want = -1; h.pts = 0; h.fast = 0; h.stun = 0; h.hopT = HOP_T;
    w.tiles[y * n + x] = h.i;
  });
  w.ph = 'count'; w.cd = COUNT_T; w.t = 0; w.pause = 0; w.eraWin = null;
  w.cash = null; w.cashT = 1.2; w.qbox = null; w.qT = QBOX_FIRST;
}

const inside = (w, x, y) => x >= 0 && y >= 0 && x < w.n && y < w.n;
const tileAt = (w, x, y) => w.tiles[y * w.n + x];
const passable = (w, x, y) => inside(w, x, y) && tileAt(w, x, y) > ROCK;
// Is the square taken by another hare: its target, or the square it is leaving (first half).
function taken(w, h, x, y) {
  for (const o of w.hares) {
    if (o === h) continue;
    if (o.x === x && o.y === y) return true;
    if (o.fx === x && o.fy === y && o.p < 0.5) return true;
  }
  return false;
}
function canHop(w, h, d) {
  if (d < 0 || d > 3) return false;
  const x = h.x + DIRS[d][0], y = h.y + DIRS[d][1];
  return passable(w, x, y) && !taken(w, h, x, y);
}
// Start the next hop from where the hare has just landed.
function startHop(w, h) {
  h.fx = h.x; h.fy = h.y; h.p = 0; h.hopN++;
  h.hopT = h.fast > 0 ? FAST_HOP_T : HOP_T;
  if (h.stun > 0 || w.ph !== 'play' || h.want < 0) return;
  if (canHop(w, h, h.want)) { h.x += DIRS[h.want][0]; h.y += DIRS[h.want][1]; }
  else h.bumpN++;   // blocked: a bounce in place
}
function land(w, h) {
  const k = h.y * w.n + h.x;
  if (w.ph !== 'play') return;
  w.tiles[k] = h.i;
  if (w.fill) fillEnclosed(w, h);
  if (w.cash && w.cash.x === h.x && w.cash.y === h.y) cashIn(w, h);
  if (w.qbox && w.qbox.x === h.x && w.qbox.y === h.y) takeQ(w, h);
}
function ownCount(w, h) { let n = 0; for (const t of w.tiles) if (t === h.i) n++; return n; }
function cashIn(w, h) {
  let n = 0;
  for (let k = 0; k < w.tiles.length; k++) if (w.tiles[k] === h.i) { w.tiles[k] = BLANK; n++; }
  h.pts += n; h.cashN++; h.lastCash = n;
  w.cash = null; w.cashT = CASH_GAP;
}
function takeQ(w, h) {
  w.qbox = null; w.qT = QBOX_GAP;
  h.got++;
  // Lumipallo only when someone else has points to lose; otherwise Pikajousi.
  const others = w.hares.filter(o => o !== h);
  const lead = others.reduce((a, o) => (!a || o.pts > a.pts ? o : a), null);
  if (lead && lead.pts > 0 && w.rand() < 0.5) { h.gotK = 'lumi'; lead.stun = STUN_T; }
  else { h.gotK = 'jousi'; h.fast = FAST_T; }
}
// Aitaus: the squares that are not this hare's split into areas; once there are two or more, every
// area with no other hare in it (standing or on its way) turns this hare's colour, however big
// (spec D9). Rocks and holes are part of no area. So a line across the board, against its edges,
// fills the side the others are not on.
function fillEnclosed(w, h) {
  const n = w.n, seen = new Uint8Array(n * n), areas = [];
  // A square another hare stands on or hops from is open ground even when it is this hare's, so
  // a hare on one of my squares inside the ring keeps it from filling.
  const occ = new Uint8Array(n * n);
  for (const o of w.hares) if (o !== h) { occ[o.y * n + o.x] = 1; occ[o.fy * n + o.fx] = 1; }
  const wall = k => (w.tiles[k] === h.i && !occ[k]) || w.tiles[k] <= ROCK;
  for (let k = 0; k < n * n; k++) {
    if (seen[k] || wall(k)) continue;
    const cells = [k], free = { cells, other: false };
    seen[k] = 1;
    for (let q = 0; q < cells.length; q++) {
      const c = cells[q], x = c % n, y = (c / n) | 0;
      for (const [dx, dy] of DIRS) {
        const nx = x + dx, ny = y + dy;
        if (!inside(w, nx, ny)) continue;
        const nk = ny * n + nx;
        if (seen[nk] || wall(nk)) continue;
        seen[nk] = 1; cells.push(nk);
      }
    }
    for (const o of w.hares) if (o !== h && (cells.includes(o.y * n + o.x) || cells.includes(o.fy * n + o.fx))) free.other = true;
    areas.push(free);
  }
  // Nothing is cut off until the open ground is in two or more parts (a hare alone on my square
  // is not a part).
  if (areas.filter(a => a.cells.some(k => w.tiles[k] !== h.i)).length < 2) return 0;
  let filled = 0;
  for (const a of areas) {
    if (a.other) continue;
    for (const k of a.cells) { w.tiles[k] = h.i; filled++; }
  }
  return filled;
}
function freeSquare(w) {
  const spots = [];
  for (let k = 0; k < w.tiles.length; k++) {
    const x = k % w.n, y = (k / w.n) | 0;
    if (w.tiles[k] !== BLANK || taken(w, null, x, y)) continue;
    if (w.cash && w.cash.x === x && w.cash.y === y) continue;
    if (w.qbox && w.qbox.x === x && w.qbox.y === y) continue;
    spots.push({ x, y });
  }
  if (!spots.length) return null;
  return spots[Math.floor(w.rand() * spots.length)];
}

// One step of the world. The order of the hares' landings is fewest points first, then lowest
// index, so two hops for one square in the same step go to the hare with fewer points (design).
function step(w, dt) {
  if (w.over) return;
  if (w.ph === 'count') {
    w.cd -= dt;
    if (w.cd <= 0) { w.ph = 'play'; w.cd = 0; w.t = 0; }
  } else if (w.ph === 'play') {
    w.t += dt;
    if (!w.cash) { w.cashT -= dt; if (w.cashT <= 0) { w.cash = freeSquare(w); if (!w.cash) w.cashT = 0.5; } }
    if (w.qbox) { w.qbox.life -= dt; if (w.qbox.life <= 0) { w.qbox = null; w.qT = QBOX_GAP; } }
    else { w.qT -= dt; if (w.qT <= 0) { const q = freeSquare(w); if (q) { q.life = QBOX_LIFE; w.qbox = q; } w.qT = q ? QBOX_GAP : 1; } }
    if (w.t >= ERA_T) return endEra(w);
  } else if (w.ph === 'erä') {
    w.pause -= dt;
    if (w.pause <= 0) {
      if (w.hares.some(h => h.wins >= WINS_TO)) { w.ph = 'over'; w.over = true; return; }
      w.era++; resetEra(w);
      return;
    }
  }
  for (const h of w.hares) { if (h.fast > 0) h.fast = Math.max(0, h.fast - dt); if (h.stun > 0) h.stun = Math.max(0, h.stun - dt); }
  const order = w.hares.slice().sort((a, b) => a.pts - b.pts || a.i - b.i);
  for (const h of order) {
    h.p += dt / h.hopT;
    if (h.p >= 1) { h.p = 1; land(w, h); startHop(w, h); }
  }
}
function endEra(w) {
  const top = Math.max(...w.hares.map(h => h.pts));
  const leaders = w.hares.filter(h => h.pts === top);
  for (const h of w.hares) h.best = Math.max(h.best, h.pts);
  w.ph = 'erä'; w.pause = ERA_PAUSE; w.t = ERA_T;
  if (leaders.length === 1 && top > 0) {
    const win = leaders[0];
    win.wins++; w.eraWin = win.id;
    if (win.wins >= WINS_TO) w.winner = win.id;
  } else w.eraWin = null;   // a tie: the erä is played again
}
// Where a hare is drawn: board x, y, and height over the board (0 on landing).
function harePos(h) {
  if (h.draw) return h.draw;   // another phone's hare in a room, gliding (net.js)
  const p = clamp(h.p, 0, 1);
  return { x: h.fx + (h.x - h.fx) * p, y: h.fy + (h.y - h.fy) * p, z: Math.sin(Math.PI * p) * (h.hopT < HOP_T ? 0.6 : 0.85), p };
}
