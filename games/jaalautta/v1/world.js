'use strict';
// Jäälautta v1 (#478): the rules and the physics, plain numbers only, no drawing.
//
// Round seals slide on an ice floe in the sea, seen from above, and shove each other into the
// water. The last seal on the ice wins the round (erä) and a star; three stars win the match.
// A world is one match on one floe. step(w, dt) runs it in fixed STEP-long steps, so a test can
// play a whole match in a loop and the host phone in a room runs exactly the same rules.
//
// Units: the floe's start radius is about 10. A seal's input is a stick (ix, iy, length ≤ 1) and a
// lunge counter (`want`); the world lunges when `want` is above `lunges` and the cooldown allows.

const TAU = Math.PI * 2;
const STEP = 1 / 120;
const WEDGES = 24;               // a floe part's edge is 24 wedges, each with its own radius
const SEAL_R = 0.9;
const ACC = 14, DRAG = 0.6, DRAG2 = 0.29;   // stick push; ice friction; air-ish drag above walking speed
const TURN = 8;                  // how fast a seal turns to its stick, rad/s
const LUNGE_V = 9, LUNGE_T = 0.35, LUNGE_CD = 1.2, LUNGE_MASS = 2.5;
const BUMP_MIN = 1.5;            // every bump throws at least this hard (units/s along the hit)
// MIN_FRAC floors each wedge's radius at a third of the whole floe's (so the ice left can be about a
// ninth of its area): a third of its size across, as the spec's "a third" was meant to read.
const SHRINK_AT = 20, SHRINK_EVERY = 8, SHRINK_WARN = 1.5, MIN_FRAC = 1 / 3;
const RING_FIRST = 6, RING_EVERY = 10, RING_COME = 1, RING_OPEN = 4, RING_R = 1.3;
const SIZE_T = 8, UKKO_T = 5, LOHK_T = 8, PASS_GRACE = 0.5, STUN_T = 1.5;
const POWERS = ['jatti', 'pikku', 'ukko', 'lohk'];
const POWER_NAMES = { jatti: 'Jätti', pikku: 'Pikkuinen', ukko: 'Ukkonen', lohk: 'Lohkare' };
const ERA_PAUSE = 2.6, COUNT_T = 3, STARS_TO_WIN = 3;

// The five floes, opened one by one by winning a match on the one before (#478 spec).
// `parts`: [centre x, centre y, radius]; `cpu`: the computer's reaction time and aim error.
const FLOES = [
  { name: 'Iso lautta', parts: [[0, 0, 10]], wobble: 0, cpu: { react: 0.45, err: 25 } },
  { name: 'Pieni lautta', parts: [[0, 0, 8]], wobble: 0.6, cpu: { react: 0.38, err: 20 } },
  { name: 'Lumipallot', parts: [[0, 0, 9]], wobble: 0.4, snow: true, cpu: { react: 0.32, err: 15 } },
  { name: 'Railot', parts: [[0, 0, 9]], wobble: 0.5, holes: true, cpu: { react: 0.26, err: 11 } },
  { name: 'Kaksi lauttaa', parts: [[-5.6, 0, 5.3], [5.6, 0, 5.3]], wobble: 0.3, cpu: { react: 0.2, err: 8 } },
];

const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
// A small seeded random generator, so a match plays the same from the same seed (tests).
function rng(seed) {
  let a = (seed >>> 0) || 1;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}

// ---- A new match ----
// players: [{ id, name, hat, kind: 'me' | 'net' | 'cpu' }]. With seven or eight seals the floe
// starts a quarter bigger (#478, the owner's choice of eight players).
function newWorld(floeN, players, seed) {
  const F = FLOES[floeN - 1];
  const scale = players.length > 6 ? 1.25 : 1;
  const w = {
    floe: floeN, scale, seed: seed >>> 0, rand: rng(seed), t: 0, ph: 'count', cd: COUNT_T, era: 1,
    parts: [], seals: [], ring: null, ringNext: RING_FIRST, snow: [], snowNext: 5, holes: [], holeNext: 6,
    breakNext: SHRINK_AT, warn: [], winner: null, eraWin: null, pause: 0, over: false,
  };
  w.seals = players.map((p, i) => ({
    id: p.id, name: p.name, hat: p.hat, kind: p.kind, i,
    x: 0, y: 0, vx: 0, vy: 0, face: 0, ix: 0, iy: 0, want: 0, lunges: 0, own: 0,
    cd: 0, lungeT: 0, stun: 0, out: 0, outX: 0, outY: 0, size: null, fuse: null, stars: 0, hit: 0, got: 0,
  }));
  resetEra(w);
  return w;
}
// Every erä starts on a whole floe with the seals in a ring around the middle, facing in.
function resetEra(w) {
  const F = FLOES[w.floe - 1], s = w.scale;
  w.parts = F.parts.map(([x, y, r], pi) => {
    const rs = [];
    for (let i = 0; i < WEDGES; i++) rs.push(r * s * (1 + (F.wobble ? Math.sin(i * 2.1 + pi * 3 + w.era) * F.wobble * 0.05 : 0)));
    return { x: x * s, y: y * s, r0: r * s, r: rs };
  });
  w.t = 0; w.ph = 'count'; w.cd = COUNT_T; w.ring = null; w.ringNext = RING_FIRST; w.snow = []; w.snowNext = 5;
  w.holes = []; w.holeNext = 6; w.breakNext = SHRINK_AT; w.warn = []; w.eraWin = null; w.pause = 0;
  const n = w.seals.length;
  w.seals.forEach((sl, i) => {
    let x, y;
    if (w.parts.length === 2) {
      // Two floes: half the seals on each, so nobody starts alone.
      const p = w.parts[i % 2], k = Math.floor(i / 2), m = Math.ceil(n / 2), a = (k / m) * TAU + (i % 2 ? Math.PI : 0);
      x = p.x + Math.cos(a) * p.r0 * 0.5; y = p.y + Math.sin(a) * p.r0 * 0.5;
    } else {
      const a = (i / n) * TAU - Math.PI / 2, d = w.parts[0].r0 * 0.55;
      x = Math.cos(a) * d; y = Math.sin(a) * d;
    }
    Object.assign(sl, { x, y, vx: 0, vy: 0, ix: 0, iy: 0, cd: 0, lungeT: 0, stun: 0, out: 0, size: null, fuse: null, crushed: false });
    sl.face = Math.atan2(-y, -x);
  });
}

// ---- Where the ice is ----
// The edge's radius at angle a, smoothly between wedge centres.
function edgeAt(p, a) {
  const f = (((a % TAU) + TAU) % TAU) / TAU * WEDGES - 0.5;
  const i = Math.floor(f), k = f - i;
  const r0 = p.r[(i + WEDGES) % WEDGES], r1 = p.r[(i + 1) % WEDGES];
  return r0 + (r1 - r0) * k;
}
function onIce(w, x, y) {
  for (const h of w.holes) if (h.open > 0 && Math.hypot(x - h.x, y - h.y) < h.r) return false;
  for (const p of w.parts) {
    const dx = x - p.x, dy = y - p.y;
    if (Math.hypot(dx, dy) <= edgeAt(p, Math.atan2(dy, dx))) return true;
  }
  return false;
}
// The floe part a point is on (or nearest to), and how far the point is from that part's edge.
function partOf(w, x, y) {
  let best = null, bd = Infinity;
  for (const p of w.parts) {
    const d = Math.hypot(x - p.x, y - p.y) - edgeAt(p, Math.atan2(y - p.y, x - p.x));
    if (d < bd) { bd = d; best = p; }
  }
  return { p: best, edge: -bd };
}
// A random spot well inside the ice.
function spotOnIce(w, inner) {
  for (let k = 0; k < 40; k++) {
    const p = w.parts[Math.floor(w.rand() * w.parts.length)];
    const a = w.rand() * TAU, d = Math.sqrt(w.rand()) * edgeAt(p, a) * (inner || 0.65);
    const x = p.x + Math.cos(a) * d, y = p.y + Math.sin(a) * d;
    if (onIce(w, x, y)) return { x, y };
  }
  return { x: w.parts[0].x, y: w.parts[0].y };
}

// ---- A seal's own numbers ----
const alive = sl => !sl.out;
function radiusOf(sl) { return SEAL_R * (sl.size ? (sl.size.k === 'jatti' ? 1.5 : 0.65) : 1); }
function massOf(sl) {
  const m = sl.size ? (sl.size.k === 'jatti' ? 2.4 : 0.45) : 1;
  return m * (sl.lungeT > 0 ? LUNGE_MASS : 1);
}

// ---- One fixed step ----
function step(w, dt) {
  w.acc = (w.acc || 0) + dt;
  while (w.acc >= STEP) { w.acc -= STEP; tick(w, STEP); }
}
function tick(w, h) {
  if (w.over) return;
  if (w.ph === 'count') {
    w.cd -= h;
    if (w.cd <= 0) { w.ph = 'play'; w.cd = 0; }
    return;
  }
  if (w.ph === 'erä') {
    w.pause -= h;
    if (w.pause <= 0) nextEra(w);
    return;
  }
  w.t += h;
  for (const sl of w.seals) moveSeal(w, sl, h);
  collide(w);
  hazards(w, h);
  powers(w, h);
  shrink(w, h);
  for (const sl of w.seals) {
    if (sl.out) { sl.out += h; continue; }
    if (!onIce(w, sl.x, sl.y)) fall(w, sl);
  }
  const left = w.seals.filter(alive);
  if (left.length <= 1) endEra(w, left[0] || null);
}
function moveSeal(w, sl, h) {
  if (sl.out) return;
  if (sl.cd > 0) sl.cd = Math.max(0, sl.cd - h);
  if (sl.lungeT > 0) sl.lungeT = Math.max(0, sl.lungeT - h);
  if (sl.stun > 0) sl.stun = Math.max(0, sl.stun - h);
  let ix = sl.ix, iy = sl.iy;
  const m = Math.hypot(ix, iy);
  if (m > 1) { ix /= m; iy /= m; }
  if (sl.stun > 0) { ix = iy = 0; }
  // A lunge asked for: counted once, whether or not the cooldown lets it happen (design, #478).
  if (sl.want > sl.lunges) {
    sl.lunges = sl.want;
    if (sl.cd <= 0 && sl.stun <= 0) {
      if (m > 0.2) sl.face = Math.atan2(iy, ix);
      const k = sl.size && sl.size.k === 'jatti' ? 0.85 : 1;
      sl.vx += Math.cos(sl.face) * LUNGE_V * k; sl.vy += Math.sin(sl.face) * LUNGE_V * k;
      sl.lungeT = LUNGE_T; sl.cd = LUNGE_CD;
    }
  }
  const acc = ACC * (sl.size ? (sl.size.k === 'jatti' ? 0.7 : 1.1) : 1);
  sl.vx += ix * acc * h; sl.vy += iy * acc * h;
  const v = Math.hypot(sl.vx, sl.vy);
  if (v > 0) {
    const nv = Math.max(0, v - v * (DRAG + (sl.lungeT > 0 ? 0 : DRAG2 * v)) * h);
    sl.vx *= nv / v; sl.vy *= nv / v;
  }
  sl.x += sl.vx * h; sl.y += sl.vy * h;
  // It turns to the stick; with no stick, slowly to where it slides.
  const want = Math.hypot(ix, iy) > 0.15 ? Math.atan2(iy, ix) : v > 1.5 ? Math.atan2(sl.vy, sl.vx) : sl.face;
  let d = ((want - sl.face + Math.PI) % TAU + TAU) % TAU - Math.PI;
  const turn = (Math.hypot(ix, iy) > 0.15 ? TURN : 2) * h;
  sl.face += clamp(d, -turn, turn);
}
// Seals bounce like discs; a lunging seal counts heavier, so a good lunge throws the other far.
function collide(w) {
  const ss = w.seals;
  for (let i = 0; i < ss.length; i++) for (let j = i + 1; j < ss.length; j++) {
    const a = ss[i], b = ss[j];
    if (a.out || b.out) continue;
    bounce(w, a, b, radiusOf(a), radiusOf(b), massOf(a), massOf(b), true);
  }
  for (const s of w.snow) for (const sl of ss) {
    if (sl.out) continue;
    bounce(w, s, sl, s.r, radiusOf(sl), 3, massOf(sl), false);
  }
}
function bounce(w, a, b, ra, rb, ma, mb, seals) {
  const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy), min = ra + rb;
  if (d >= min || d === 0) return;
  const nx = dx / d, ny = dy / d;
  // Push apart by mass.
  const over = min - d, ia = 1 / ma, ib = 1 / mb;
  a.x -= nx * over * ia / (ia + ib); a.y -= ny * over * ia / (ia + ib);
  b.x += nx * over * ib / (ia + ib); b.y += ny * over * ib / (ia + ib);
  // A fuse passes on any touch, a slow lean too.
  if (seals) passFuse(a, b) || passFuse(b, a);
  const vn = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny;   // closing speed along the hit
  if (vn <= 0) return;
  const j = Math.max(vn * 1.9, BUMP_MIN) / (ia + ib);
  a.vx -= j * ia * nx; a.vy -= j * ia * ny;
  b.vx += j * ib * nx; b.vy += j * ib * ny;
  if (seals) { if (vn > 2) { a.hit++; b.hit++; } }
  else if (vn > 1) b.hit++;
}
// A fuse (Ukkonen, Lohkare) goes to the seal its holder touches, unless the holder only just got it.
function passFuse(from, to) {
  if (!from.fuse || to.fuse || from.fuse.g > 0) return false;
  to.fuse = { k: from.fuse.k, t: from.fuse.t, g: PASS_GRACE };
  from.fuse = null;
  return true;
}
function fall(w, sl) {
  sl.crushed = false;   // a crush sets it again right after
  sl.out = 1e-6; sl.outX = sl.x; sl.outY = sl.y;
  sl.vx = sl.vy = 0; sl.fuse = null; sl.size = null; sl.lungeT = 0;
}

// ---- Snowballs (floe 3) and cracks (floe 4) ----
function hazards(w, h) {
  const F = FLOES[w.floe - 1];
  if (F.snow) {
    w.snowNext -= h;
    if (w.snowNext <= 0) {
      w.snowNext = 7 - Math.min(3, w.t / 20);
      const R = w.parts[0].r0 + 3, a = w.rand() * TAU, off = (w.rand() - 0.5) * R * 0.8;
      const x = Math.cos(a) * R, y = Math.sin(a) * R, sp = 4.5;
      const dx = -Math.cos(a), dy = -Math.sin(a);
      w.snow.push({ x: x - dy * off, y: y + dx * off, vx: dx * sp, vy: dy * sp, r: 1.1 * w.scale, roll: 0 });
    }
    for (const s of w.snow) {
      // A snowball rolls on at its own speed; a bump turns it only a little.
      const v = Math.hypot(s.vx, s.vy) || 1, k = 4.5 / v;
      s.vx += (s.vx * k - s.vx) * h * 2; s.vy += (s.vy * k - s.vy) * h * 2;
      s.x += s.vx * h; s.y += s.vy * h; s.roll += v * h;
    }
    w.snow = w.snow.filter(s => Math.hypot(s.x, s.y) < w.parts[0].r0 + 6);
  }
  if (F.holes) {
    w.holeNext -= h;
    if (w.holeNext <= 0) {
      w.holeNext = 6 - Math.min(2.5, w.t / 25);
      const p = spotOnIce(w, 0.75);
      w.holes.push({ x: p.x, y: p.y, r: 1.5 * w.scale, warn: SHRINK_WARN, open: 0 });
    }
    for (const o of w.holes) {
      if (o.warn > 0) { o.warn -= h; if (o.warn <= 0) o.open = 4; }
      else o.open -= h;
    }
    w.holes = w.holes.filter(o => o.warn > 0 || o.open > 0);
  }
}

// ---- The gull's ring and the power-ups ----
function powers(w, h) {
  for (const sl of w.seals) {
    if (sl.out) continue;
    if (sl.size) { sl.size.t -= h; if (sl.size.t <= 0) sl.size = null; }
    if (sl.fuse) {
      sl.fuse.t -= h; if (sl.fuse.g > 0) sl.fuse.g -= h;
      if (sl.fuse.t <= 0) {
        const k = sl.fuse.k; sl.fuse = null;
        if (k === 'ukko') { for (const o of w.seals) if (o !== sl && !o.out) { o.stun = STUN_T; o.hit++; } }
        else { fall(w, sl); sl.crushed = true; }
      }
    }
  }
  if (!w.ring) {
    w.ringNext -= h;
    if (w.ringNext <= 0) { const p = spotOnIce(w, 0.6); w.ring = { x: p.x, y: p.y, come: RING_COME, open: RING_OPEN }; }
    return;
  }
  const r = w.ring;
  if (r.come > 0) { r.come -= h; return; }
  r.open -= h;
  if (r.open <= 0 || !onIce(w, r.x, r.y)) { w.ring = null; w.ringNext = RING_EVERY - RING_OPEN; return; }
  for (const sl of w.seals) {
    if (sl.out || Math.hypot(sl.x - r.x, sl.y - r.y) > RING_R + radiusOf(sl) * 0.5) continue;
    // Only one fuse on the floe at a time.
    const fuseOn = w.seals.some(o => o.fuse);
    const pool = fuseOn ? POWERS.slice(0, 2) : POWERS;
    givePower(sl, pool[Math.floor(w.rand() * pool.length)]);
    w.ring = null; w.ringNext = RING_EVERY - RING_OPEN;
    break;
  }
}
function givePower(sl, k) {
  sl.got++; sl.gotK = k;
  if (k === 'jatti' || k === 'pikku') sl.size = { k, t: SIZE_T };
  else sl.fuse = { k, t: k === 'ukko' ? UKKO_T : LOHK_T, g: PASS_GRACE };
}

// ---- The floe breaks smaller after SHRINK_AT seconds ----
function shrink(w, h) {
  for (const b of w.warn) {
    b.t -= h;
    if (b.t <= 0) {
      const p = w.parts[b.p], min = p.r0 * MIN_FRAC;
      for (let k = -1; k <= 1; k++) {
        const i = (b.i + k + WEDGES) % WEDGES;
        p.r[i] = Math.max(min, p.r[i] - (k ? 0.9 : 1.6) * w.scale);
      }
    }
  }
  w.warn = w.warn.filter(b => b.t > 0);
  if (w.t < w.breakNext) return;
  w.breakNext += SHRINK_EVERY;
  // The widest wedges go first (a random one of the widest few), on every part.
  w.parts.forEach((p, pi) => {
    const min = p.r0 * MIN_FRAC;
    const order = p.r.map((r, i) => [r, i]).filter(([r]) => r > min + 0.05).sort((a, b) => b[0] - a[0]);
    if (!order.length) return;
    const pick = order[Math.floor(w.rand() * Math.min(4, order.length))][1];
    w.warn.push({ p: pi, i: pick, t: SHRINK_WARN });
  });
}

// ---- The end of an erä, and of the match ----
function endEra(w, win) {
  w.ph = 'erä'; w.pause = ERA_PAUSE; w.eraWin = win ? win.id : '';
  if (win) { win.stars++; if (win.stars >= STARS_TO_WIN) { w.winner = win.id; } }
}
function nextEra(w) {
  if (w.winner) { w.over = true; w.ph = 'over'; return; }
  w.era++;
  resetEra(w);
}
