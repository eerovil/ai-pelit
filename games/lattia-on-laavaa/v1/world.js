'use strict';
// Lattia on laavaa v1 (#488): the rules, in plain numbers, with no drawing.
//
// A room of a home seen from the front: the floor is lava, which slowly rises, and the kids
// jump from one piece of furniture to the next. Every piece wobbles, then sinks into the lava,
// in an order drawn from the round's seed; once most are gone, cushions, books and baskets float
// across the lava for the kids to ride. Touching the lava puts a kid out; the last kid standing
// wins the round.
//
// Space: x left to right, z from the back wall (negative) to the front (positive), y up, metres.
// Time: every piece, the lava and every float is a function of the round's clock `rt` (seconds,
// negative during the countdown) and the seed alone, so every phone in a room draws the same room
// from the host's `rt` without a message per piece (design, #488). `rt` stops while the round is
// paused.
const TAU = Math.PI * 2;
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const STEP = 1 / 120;           // the physics step; a frame runs whole steps
const COUNT = 3;                // the countdown before the floor turns to lava, s
const GRAV = 22, JUMP_V = 8.2;  // a jump about 1.5 m high, about 3 m long at full speed
const RUN = 4.5, ACC = 30, AIR_ACC = 16;
const KID_R = 0.3, KID_H = 1.0, STEP_UP = 0.28;
const WOBBLE = 2.6;             // seconds a piece wobbles before it starts to sink
const SINK_V = 0.45;            // how fast a sinking piece goes down, m/s
const SHOVE_CD = 1.5, SHOVE_T = 0.22, SHOVE_V = 7.5, SHOVE_REACH = 1.15, PUSH_V = 4.6, PUSH_UP = 2.8, STUN = 0.6, PUSHED_AGAIN = 0.4;
const ROOM_W = 14, ROOM_D = 10;
const X0 = -ROOM_W / 2, X1 = ROOM_W / 2, Z0 = -ROOM_D / 2, Z1 = ROOM_D / 2;
// The end of a round waits this long in `rt` for a guest's late word that it fell earlier (design
// review notes, #488): never less than how far a guest's clock may be off the host's (0.3 s).
const GRACE = 0.35;

// ---- The rooms ----
// A piece: [kind, x, z, w (along x), d (along z), h (its top), order]. `order` sorts the sinking:
// 0 goes first (cushions, small stools), 3 last (the big pieces); within one class the seed decides.
const ROOMS = [
  {
    name: 'Olohuone', wall: '#d9c7a6', floorWood: '#a8743f', start: 14, gap: 4.2, floatAt: 46, cpu: 0,
    pieces: [
      ['sofa', -3.6, -3.7, 4.0, 1.3, 0.75, 3], ['sofaback', -3.6, -4.6, 4.0, 0.5, 1.35, 3],
      ['armchair', 3.4, -3.6, 1.4, 1.3, 0.75, 2], ['tvbench', 0.4, -4.5, 2.2, 0.7, 0.55, 2],
      ['table', 0, -1.0, 2.2, 1.2, 0.6, 2], ['shelf', 6.2, -2.2, 0.9, 2.6, 1.9, 3],
      ['pouf', -2.2, 1.0, 0.9, 0.9, 0.5, 1], ['pouf', 2.4, 1.2, 0.9, 0.9, 0.5, 1],
      ['cushion', -5.4, -0.6, 1.0, 1.0, 0.25, 0], ['cushion', -0.2, 2.6, 1.0, 1.0, 0.25, 0],
      ['cushion', 4.6, 2.8, 1.0, 1.0, 0.25, 0], ['sidetable', 5.3, 0.6, 0.8, 0.8, 0.65, 1],
      ['stool', -5.0, 2.8, 0.7, 0.7, 0.55, 1], ['chest', -6.2, -2.4, 0.8, 1.6, 0.7, 2],
      ['pouf', 1.8, 3.6, 0.8, 0.8, 0.45, 0],
    ],
  },
  {
    name: 'Lastenhuone', wall: '#b9d8e8', floorWood: '#c99a62', start: 12, gap: 3.6, floatAt: 40, cpu: 1,
    pieces: [
      ['bed', -4.4, -3.6, 3.2, 1.6, 0.6, 3], ['wardrobe', 6.1, -3.8, 1.2, 1.2, 2.0, 3],
      ['desk', 3.0, -4.2, 2.0, 0.9, 0.75, 2], ['chair', 3.0, -2.9, 0.6, 0.6, 0.45, 1],
      ['toybox', -0.6, -4.3, 1.4, 0.8, 0.55, 2], ['beanbag', -1.0, -1.0, 1.2, 1.2, 0.45, 1],
      ['beanbag', 2.6, 0.2, 1.2, 1.2, 0.45, 1], ['blocks', -4.0, 0.0, 0.7, 0.7, 0.35, 0],
      ['blocks', 0.6, 2.2, 0.7, 0.7, 0.35, 0], ['horse', -2.6, 2.6, 1.2, 0.6, 0.7, 1],
      ['toybox', 5.4, 1.2, 1.4, 0.8, 0.55, 2], ['cushion', -6.0, 1.8, 1.0, 1.0, 0.25, 0],
      ['blocks', 3.8, 3.2, 0.7, 0.7, 0.35, 0], ['cushion', -1.0, 4.0, 1.0, 1.0, 0.25, 0],
    ],
  },
  {
    name: 'Keittiö', wall: '#f0e2b6', floorWood: '#8f9aa3', start: 10, gap: 3.0, floatAt: 34, cpu: 2,
    pieces: [
      ['counter', -4.2, -4.6, 2.4, 0.8, 0.9, 2], ['counter', -1.6, -4.6, 2.4, 0.8, 0.9, 3],
      ['counter', 1.0, -4.6, 2.4, 0.8, 0.9, 2], ['fridge', 3.2, -4.5, 1.0, 0.9, 1.8, 3],
      ['ktable', 0, -0.6, 2.4, 1.3, 0.75, 3], ['chair', -1.8, -0.6, 0.6, 0.6, 0.45, 1],
      ['chair', 1.8, -0.6, 0.6, 0.6, 0.45, 1], ['chair', -0.6, 0.8, 0.6, 0.6, 0.45, 0],
      ['chair', 0.6, -2.0, 0.6, 0.6, 0.45, 0], ['stool', 5.4, -1.6, 0.6, 0.6, 0.65, 1],
      ['basket', -5.4, 0.6, 0.9, 0.7, 0.5, 1], ['dogbed', 4.2, 2.6, 1.2, 1.0, 0.22, 0],
      ['stool', -3.4, 2.8, 0.6, 0.6, 0.65, 0], ['basket', 1.4, 3.6, 0.9, 0.7, 0.5, 0],
      ['cupboard', -6.3, -2.2, 0.8, 1.4, 1.1, 2],
    ],
  },
];
// Kids, by colour: the player's own is the first, the others the computer's or friends'.
const KID_COLORS = ['#e63946', '#2a7de1', '#f4b400', '#2bb24c', '#9b51e0', '#ff7a1a', '#14b8a6', '#ec4899'];
const HAIR = ['#3b2414', '#d9a441', '#1a1a1a', '#7a3b12', '#e8d08a', '#5a3a22', '#2a1a10', '#b5521b'];
const CPU_NAMES = ['Aino', 'Eetu', 'Siiri', 'Onni', 'Lilja', 'Väinö', 'Helmi', 'Toivo', 'Ella', 'Leo'];

// ---- Seeded numbers (mulberry32): the same seed gives every phone the same room ----
function rng(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// ---- A new round ----
function newWorld(level, players, seed) {
  const R = ROOMS[level - 1], r = rng(seed);
  const pieces = R.pieces.map(([kind, x, z, w, d, h, order], i) => ({ i, kind, x, z, w, d, h0: h, order, key: order + r() * 0.9 }));
  // The sinking order: by class, shuffled within it by the seed. Each starts wobbling `gap`
  // seconds after the one before, a little sooner each time.
  const order = pieces.slice().sort((a, b) => a.key - b.key);
  let t = R.start;
  order.forEach((p, k) => { p.wobAt = t; p.sinkAt = t + WOBBLE; t += Math.max(1.6, R.gap - k * 0.12); });
  const w = {
    level, seed, rt: -COUNT, kids: [], pieces, ph: 'count', over: false, winner: null, draw: false, graceAt: null,
    floatAt: R.floatAt, lastSink: t, floatsCache: { k0: 0, list: [] },
  };
  // Spawns: on the pieces that sink last, spread round them.
  const spots = order.slice().reverse().filter(p => p.h0 < 1.5);
  players.forEach((p, i) => {
    const pc = spots[i % spots.length], n = Math.floor(i / spots.length);
    const k = newKid(p, i);
    k.x = pc.x + (n % 2 ? 0.45 : -0.45) * Math.min(1, (pc.w - 0.6) / 0.9) * (n ? 1 : 0);
    k.z = pc.z + (n > 1 ? 0.3 : 0);
    k.y = pc.h0; k.face = Math.atan2(-k.z, -k.x) || 0;
    k.sx = k.x; k.sz = k.z;
    w.kids.push(k);
  });
  return w;
}
function newKid(p, i) {
  return {
    i, id: p.id, name: p.name, kind: p.kind, col: p.col === undefined ? i % KID_COLORS.length : p.col,
    x: 0, y: 0, z: 0, vx: 0, vy: 0, vz: 0, face: 0, ground: true, gp: -1,
    ix: 0, iz: 0, jump: false, jumpHeld: false, coyote: 0, buf: 0,
    cd: 0, dash: 0, stun: 0, pushedAt: -9, out: false, outRt: -1, fellX: 0, fellZ: 0, shoves: 0, own: 0,
  };
}

// ---- What the room is like at time rt ----
// The lava's height: the floor itself until 20 s, then slowly up to 0.45 m by about 80 s.
function lavaAt(rt) { return rt < 20 ? 0.02 : Math.min(0.45, 0.02 + (rt - 20) * 0.0072); }
// A piece's top at rt; 'gone' once it is under the lava.
function topOf(p, rt) { return rt < p.sinkAt ? p.h0 : p.h0 - (rt - p.sinkAt) * SINK_V; }
function wobbleOf(p, rt) { return rt >= p.wobAt ? Math.min(1, (rt - p.wobAt) / WOBBLE) : 0; }
function alive(p, rt) { return topOf(p, rt) > lavaAt(rt) + 0.03; }
// Floats: from `floatAt` on, one every few seconds from a wall, across the lava, more and quicker
// as time goes on; each is a function of its number k and the seed alone.
const FLOAT_KINDS = [['fcushion', 1.0, 1.0], ['book', 0.8, 0.6], ['fbasket', 0.9, 0.9], ['tray', 1.1, 0.7], ['duck', 0.7, 0.7]];
function floatGap(k) { return Math.max(1.3, 2.6 - k * 0.025); }
function floatStart(w, k) {
  // The sum of the gaps before k, worked out in closed form for the shrinking part.
  const n = Math.min(k, 52), base = n * 2.6 - 0.025 * n * (n - 1) / 2;
  return w.floatAt + base + Math.max(0, k - 52) * 1.3;
}
function floatOf(w, k) {
  const r = rng((w.seed ^ (k * 2654435761)) >>> 0);
  const fk = FLOAT_KINDS[Math.floor(r() * FLOAT_KINDS.length)];
  const fromLeft = r() < 0.5, lane = Z0 + 1.2 + r() * (ROOM_D - 2.4);
  const speed = 0.7 + Math.min(1.0, k * 0.02) + r() * 0.4;
  const life = (ROOM_W + 2) / speed, size = Math.max(0.62, 1 - k * 0.006);
  return { k, kind: fk[0], w: fk[1] * size, d: fk[2] * size, dir: fromLeft ? 1 : -1, x0: fromLeft ? X0 - 1 : X1 + 1, z: lane, speed, t0: floatStart(w, k), life, drift: (r() - 0.5) * 0.3 };
}
// The floats on the lava at rt, with where each is: [{k, kind, x, z, w, d, top, vx, vz, sink}].
function floatsAt(w, rt) {
  const out = [];
  if (rt < w.floatAt) return out;
  // Floats live at most about (ROOM_W + 2) / 0.7 s: start from the first that could still be up.
  let k = Math.max(0, w.floatsCache.k0);
  while (k > 0 && floatStart(w, k) > rt - 26) k--;
  while (floatStart(w, k) + 26 < rt) k++;
  w.floatsCache.k0 = k;
  for (; floatStart(w, k) <= rt; k++) {
    const f = floatOf(w, k), a = rt - f.t0;
    if (a > f.life) continue;
    const L = lavaAt(rt), bob = Math.sin(rt * 2.2 + k) * 0.03;
    // The last two seconds of its way it sinks.
    const sink = Math.max(0, a - (f.life - 2)) / 2;
    out.push({ k, kind: f.kind, x: f.x0 + f.dir * f.speed * a, z: f.z + f.drift * a, w: f.w, d: f.d, top: L + 0.18 - sink * 0.3 + bob, vx: f.dir * f.speed, vz: f.drift, sink });
  }
  return out;
}
// Everything a kid can stand on at rt: pieces and floats alike, as boxes with a top and a speed.
function solids(w, rt) {
  const L = lavaAt(rt), list = [];
  for (const p of w.pieces) {
    const top = topOf(p, rt);
    if (top <= L + 0.03) continue;
    const wob = wobbleOf(p, rt);
    // A wobbling piece shakes a little under the feet; it does not throw anyone off.
    list.push({ id: 'p' + p.i, x: p.x, z: p.z, w: p.w, d: p.d, top, vx: 0, vz: 0, wob });
  }
  for (const f of floatsAt(w, rt)) if (f.top > L + 0.03) list.push({ id: 'f' + f.k, x: f.x, z: f.z, w: f.w, d: f.d, top: f.top, vx: f.vx, vz: f.vz, wob: f.sink });
  return list;
}
const inside = (s, x, z, m) => Math.abs(x - s.x) <= s.w / 2 + m && Math.abs(z - s.z) <= s.d / 2 + m;

// ---- One kid moving, on any phone ----
// ix, iz: the stick (screen right = +x, screen up = -z), jump: the button held. `sol` is solids().
function moveKid(w, k, dt, sol) {
  if (k.out) return;
  const stun = k.stun > 0;
  k.cd = Math.max(0, k.cd - dt); k.stun = Math.max(0, k.stun - dt);
  let ix = k.ix, iz = k.iz;
  const m = Math.hypot(ix, iz);
  if (m > 1) { ix /= m; iz /= m; }
  if (stun) { ix *= 0.15; iz *= 0.15; }
  if (m > 0.15) k.face = Math.atan2(iz, ix);
  // The ground's own speed (a float) carries a kid standing on it.
  let gvx = 0, gvz = 0;
  if (k.ground && k.gp >= 0) { const g = sol.find(s => s.id === k.gpId); if (g) { gvx = g.vx; gvz = g.vz; } }
  if (k.dash > 0) {
    k.dash = Math.max(0, k.dash - dt);
  } else {
    const a = (k.ground ? ACC : AIR_ACC) * dt;
    const tx = ix * RUN + gvx, tz = iz * RUN + gvz;
    const dx = tx - k.vx, dz = tz - k.vz, d = Math.hypot(dx, dz);
    if (d <= a) { k.vx = tx; k.vz = tz; } else { k.vx += dx / d * a; k.vz += dz / d * a; }
  }
  // Jump: a press a little before landing, or a little after running off an edge, still jumps.
  if (k.jump && !k.jumpHeld) k.buf = 0.12;
  k.jumpHeld = k.jump;
  k.buf = Math.max(0, k.buf - dt);
  k.coyote = k.ground ? 0.09 : Math.max(0, k.coyote - dt);
  if (k.buf > 0 && (k.ground || k.coyote > 0) && !stun) { k.vy = JUMP_V; k.ground = false; k.coyote = 0; k.buf = 0; k.jumps = (k.jumps || 0) + 1; }
  // A short jump on an early release.
  if (!k.jump && k.vy > 3 && !k.ground && !k.pushedUp) k.vy -= 40 * dt;
  k.vy -= GRAV * dt;
  const ox = k.x, oy = k.y, oz = k.z;
  k.x += k.vx * dt; k.z += k.vz * dt; k.y += k.vy * dt;
  // Walls of the room.
  if (k.x < X0 + KID_R) { k.x = X0 + KID_R; k.vx = Math.max(0, k.vx); }
  if (k.x > X1 - KID_R) { k.x = X1 - KID_R; k.vx = Math.min(0, k.vx); }
  if (k.z < Z0 + KID_R) { k.z = Z0 + KID_R; k.vz = Math.max(0, k.vz); }
  if (k.z > Z1 - KID_R) { k.z = Z1 - KID_R; k.vz = Math.min(0, k.vz); }
  // The sides of anything taller than a step: pushed back out the way it came.
  for (const s of sol) {
    if (s.top <= oy + STEP_UP || !inside(s, k.x, k.z, KID_R * 0.8)) continue;
    if (k.y >= s.top - 0.05) continue;
    const wasX = Math.abs(ox - s.x) > s.w / 2 + KID_R * 0.8 - 0.001;
    if (wasX) { k.x = ox; k.vx = 0; } else { k.z = oz; k.vz = 0; }
  }
  // The ground: the highest top under the kid's middle (a little wider, so an edge holds).
  let best = null;
  for (const s of sol) {
    if (!inside(s, k.x, k.z, 0.12)) continue;
    if (s.top > Math.max(oy, k.y) + STEP_UP) continue;
    if (!best || s.top > best.top) best = s;
  }
  const was = k.ground;
  if (best && k.y <= best.top && k.vy <= 0.5) {
    k.y = best.top; k.vy = 0; k.ground = true; k.gpId = best.id; k.gp = 1; k.pushedUp = false;
  } else if (best && was && k.vy <= 0 && k.y - best.top < STEP_UP && k.y > best.top) {
    k.y = best.top; k.vy = 0; k.ground = true; k.gpId = best.id; k.gp = 1;   // stepping down a little
  } else {
    k.ground = false; k.gp = -1; k.gpId = null;
  }
}
// Kids bump: they cannot stand in one spot. Only `mine` are moved (the others belong to other
// phones, or are where they are drawn).
function bump(w, mine) {
  for (const a of mine) {
    if (a.out) continue;
    for (const b of w.kids) {
      if (b === a || b.out || Math.abs(a.y - b.y) > KID_H * 0.9) continue;
      const dx = a.x - b.x, dz = a.z - b.z, d = Math.hypot(dx, dz), min = KID_R * 2;
      if (d >= min || d < 1e-6) continue;
      const push = (min - d) * (mine.includes(b) ? 0.5 : 1);
      a.x += dx / d * push; a.z += dz / d * push;
    }
  }
}
// Touching the lava: is this kid out now? Its own phone asks this of its own kid.
function inLava(w, k) { return !k.out && k.y <= lavaAt(w.rt) + 0.01 && !k.ground; }
function fall(w, k, rt) {
  if (k.out) return;
  k.out = true; k.outRt = rt === undefined ? w.rt : rt; k.fellX = k.x; k.fellZ = k.z;
  k.vx = k.vz = 0; k.dash = 0;
}

// ---- The shove: a short dash; a kid in front is pushed away ----
function startShove(k) {
  if (k.out || k.cd > 0 || k.stun > 0) return false;
  k.cd = SHOVE_CD; k.dash = SHOVE_T; k.shoves++;
  const fx = Math.cos(k.face), fz = Math.sin(k.face);
  k.vx = fx * SHOVE_V; k.vz = fz * SHOVE_V;
  return true;
}
// Who a shove from `k` facing `face` hits: the nearest kid in front, within reach, not out and not
// pushed in the last moment. Checked against where every kid is before any push (design, #488).
function shoveTarget(w, k, face) {
  const fx = Math.cos(face), fz = Math.sin(face);
  let best = null, bd = Infinity;
  for (const o of w.kids) {
    if (o === k || o.out || Math.abs(o.y - k.y) > 0.9) continue;
    const dx = o.x - k.x, dz = o.z - k.z, d = Math.hypot(dx, dz);
    if (d > SHOVE_REACH || d < 1e-6) continue;
    if ((dx * fx + dz * fz) / d < 0.25) continue;
    if (w.rt - o.pushedAt < PUSHED_AGAIN) continue;
    if (d < bd) { bd = d; best = o; }
  }
  return best;
}
// The push a shove gives: away from the shover, and up.
function pushOf(k, o) {
  let dx = o.x - k.x, dz = o.z - k.z;
  const d = Math.hypot(dx, dz) || 1;
  dx /= d; dz /= d;
  return [dx * PUSH_V, PUSH_UP, dz * PUSH_V];
}
function applyPush(k, imp) {
  if (k.out) return;
  k.vx = imp[0]; k.vy = Math.max(k.vy, imp[1]); k.vz = imp[2];
  k.ground = false; k.stun = STUN; k.dash = 0.25; k.pushedUp = true;
}

// ---- The round, as the host (or the phone alone) runs it ----
// One step of rt for every kid this phone runs (`run`: those it moves itself).
function stepWorld(w, dt, run) {
  if (w.over) return;
  w.rt += dt;
  if (w.ph === 'count') {
    if (w.rt < 0) return;
    w.ph = 'play';
  }
  const sol = solids(w, w.rt);
  for (const k of run) moveKid(w, k, dt, sol);
  bump(w, run);
}
// Who has fallen, and once one (or no) kid is left standing, the one decision of how the round
// ends (design, #488): it waits GRACE in rt for late word of a fall, then the last standing wins;
// with nobody standing the latest fall wins, and falls at the same instant are a draw.
function decide(w) {
  if (w.over || w.ph !== 'play') return false;
  const standing = w.kids.filter(k => !k.out);
  if (standing.length > 1 || w.kids.length < 2) { w.graceAt = null; return false; }
  if (w.graceAt === null) w.graceAt = w.rt;
  if (w.rt < w.graceAt + GRACE) return false;
  if (standing.length === 1) { w.winner = standing[0].id; w.draw = false; }
  else {
    const last = Math.max(...w.kids.map(k => k.outRt));
    const top = w.kids.filter(k => Math.abs(k.outRt - last) < 1e-6);
    if (top.length === 1) { w.winner = top[0].id; w.draw = false; } else { w.winner = null; w.draw = true; }
  }
  w.over = true; w.ph = 'over';
  return true;
}
// How long each kid lasted, for the end list: the winner first, then by the time of the fall.
function standingsOf(w) {
  return w.kids.slice().sort((a, b) => (b.id === w.winner) - (a.id === w.winner) || (b.out ? b.outRt : 1e9) - (a.out ? a.outRt : 1e9));
}
