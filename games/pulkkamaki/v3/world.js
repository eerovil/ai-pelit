'use strict';
// Pulkkamäki v1 (#475): the hills and the sleds as plain numbers. Nothing here draws or talks to
// the network, so the tests drive it directly (`step(sled, dt)`).
//
// A place on a hill is (s, x): s metres down the hill along its centre line, x metres across it
// (right is +). y is the height in metres. The world drawn in 3D puts it at X = centreX(s) + x,
// Y = y, Z = -s.

const G = 9.81, TAU = Math.PI * 2;
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
function rng(seed) {
  let s = (seed >>> 0) || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}

// ---- The tricks ----
// A flip turns the sled round its sideways axis, a spin round its upright one; each takes `dur`
// seconds in the air. The grab (Teräsmies) scores while it is held.
const TRICKS = {
  front: { name: 'Etuvoltti', pts: 300, dur: 0.72 },
  back: { name: 'Takavoltti', pts: 300, dur: 0.76 },
  spinL: { name: 'Piruetti', pts: 200, dur: 0.6 },
  spinR: { name: 'Piruetti', pts: 200, dur: 0.6 },
  grab: { name: 'Teräsmies', pts: 100 },
};
const GRAB_PER_S = 200, GRAB_MIN = 0.2;
// A trick at least this far done when the sled lands counts as done (docs/making-games.md: "Be
// generous with timing"): the sled snaps the rest of the way round.
const LAND_DONE = 0.8;
const GIFT_PTS = 50, BIG_GIFT_PTS = 100;
const FALL_T = 1.1;

// ---- The three hills ----
// Each is fixed, so a record on it compares with every other run on it. `kick`: jumps as
// [s, x, height, length, width]; `open`: points needed on the hill before it to open this one.
const HILLS = [
  {
    name: 'Kotimäki', len: 640, grad: 0.21, wave: 0.05, width: 18, open: 0, seed: 11,
    bend: [[60, 0.0042, 0.3], [14, 0.011, 1.7]],
    kick: [[90, 0, 1.2, 6, 6], [190, -3, 1.4, 6, 6], [285, 3, 1.5, 6.5, 6], [380, 0, 1.6, 6.5, 7], [470, -2, 1.8, 7, 6], [560, 2, 2.0, 7, 7]],
    trees: 18, rocks: 6, snowmen: 6, gifts: 18,
  },
  {
    name: 'Kuusikko', len: 800, grad: 0.24, wave: 0.06, width: 16, open: 2500, seed: 23,
    bend: [[70, 0.005, 1.1], [18, 0.013, 0.2]],
    kick: [[85, 2, 1.4, 6, 6], [170, -3, 1.6, 6.5, 6], [255, 3, 1.8, 7, 6], [290, 3, 1.4, 6, 6], [380, -2, 2.0, 7, 6],
      [470, 2, 2.1, 7.5, 6], [505, 2, 1.6, 6.5, 6], [600, -3, 2.2, 7.5, 6], [700, 0, 2.4, 8, 7]],
    trees: 34, rocks: 9, snowmen: 8, gifts: 24,
  },
  {
    name: 'Tunturi', len: 950, grad: 0.27, wave: 0.07, width: 14, open: 4000, seed: 37,
    bend: [[80, 0.006, 2.1], [22, 0.016, 0.9]],
    kick: [[90, -2, 1.8, 7, 5], [180, 2, 2.2, 7.5, 5], [270, -3, 2.4, 8, 5], [355, 2, 2.6, 8, 5], [440, -2, 2.4, 8, 5],
      [475, -2, 1.8, 7, 5], [560, 3, 2.8, 8.5, 5], [650, -2, 2.6, 8, 5], [740, 2, 3.0, 9, 5], [840, 0, 3.2, 9, 6]],
    trees: 46, rocks: 14, snowmen: 8, gifts: 28,
  },
];
const RUNOUT = 90;   // the flat at the bottom, past the finish line

// Builds a hill's numbers once: the height along the centre line every metre, and the trees,
// rocks, snowmen and presents, placed by the hill's own seed so they are the same every time.
function buildHill(n) {
  const H = HILLS[n - 1], r = rng(H.seed * 7919);
  const total = H.len + RUNOUT + 40;
  const base = new Float32Array(total + 1);
  let h = 0;
  for (let s = 0; s <= total; s++) {
    base[s] = h;
    // Steeper and gentler stretches; the run-out flattens out and rises a little to stop the sleds.
    let g = H.grad + H.wave * Math.sin(s * 0.017 + H.seed);
    if (s < 30) g *= 0.5 + s / 60;
    if (s > H.len) g = g * Math.max(0, 1 - (s - H.len) / 30) - 0.03 * Math.min(1, (s - H.len) / 40);
    h -= g;
  }
  const kicks = H.kick.map(([s, x, ht, len, w], i) => ({ i, s, x, h: ht, len, w }));
  const hill = { n, name: H.name, len: H.len, width: H.width, open: H.open, bend: H.bend, base, total, kicks, obst: [], gifts: [] };
  // Keep the jumps' run-ups and landings clear.
  const clear = (s, x) => kicks.some(k => s > k.s - 28 && s < k.s + k.len + 26 && Math.abs(x - k.x) < k.w / 2 + 3);
  const place = (count, kind, rad) => {
    for (let i = 0, tries = 0; i < count && tries < 2000; tries++) {
      const s = 40 + r() * (H.len - 60), x = (r() * 2 - 1) * (H.width / 2 - 1.5);
      if (clear(s, x) || hill.obst.some(o => Math.hypot(o.s - s, o.x - x) < 9)) continue;
      hill.obst.push({ id: hill.obst.length, kind, s, x, r: rad }); i++;
    }
  };
  place(H.trees, 'kuusi', 0.9);
  place(H.rocks, 'kivi', 0.8);
  place(H.snowmen, 'lumiukko', 0.6);
  // Presents: a big one over the landing of every jump, the rest on the snow along the track.
  for (const k of kicks) hill.gifts.push({ id: hill.gifts.length, s: k.s + k.len + 9, x: k.x, up: 2.6 + k.h * 0.6, big: true });
  for (let i = 0, tries = 0; i < H.gifts && tries < 2000; tries++) {
    const s = 50 + r() * (H.len - 80), x = (r() * 2 - 1) * (H.width / 2 - 2);
    if (hill.obst.some(o => Math.hypot(o.s - s, o.x - x) < 4) || hill.gifts.some(g => Math.hypot(g.s - s, g.x - x) < 6)) continue;
    hill.gifts.push({ id: hill.gifts.length, s, x, up: 0.5, big: false }); i++;
  }
  return hill;
}

// Which way the course itself heads at `s` (radians from straight down the s axis).
function courseDir(hill, s) { return Math.atan2(centreX(hill, s + 0.6) - centreX(hill, s - 0.6), 1.2); }
function centreX(hill, s) { let v = 0; for (const [a, k, p] of hill.bend) v += a * Math.sin(s * k + p); return v; }
function baseAt(hill, s) {
  const b = hill.base, i = clamp(Math.floor(s), 0, hill.total - 1), f = clamp(s - i, 0, 1);
  return b[i] + (b[i + 1] - b[i]) * f;
}
// The banks: the snow rises beside the track, so a sled that leaves it slows and slides back.
function bankAt(hill, x) { const e = Math.abs(x) - hill.width / 2; return e > 0 ? e * e * 0.09 : 0; }
// A jump's ramp: it rises as u² along its length, so it gets steeper towards the lip, and ends in
// a drop. Its sides are straight down.
function kickAt(hill, s, x) {
  for (const k of hill.kicks) {
    const u = (s - k.s) / k.len;
    if (u >= 0 && u <= 1 && Math.abs(x - k.x) <= k.w / 2) return k.h * u * u;
  }
  return 0;
}
function groundAt(hill, s, x) { return baseAt(hill, s) + bankAt(hill, x) + kickAt(hill, s, x); }

// ---- A sled ----
function newSled(id, name, opts) {
  return Object.assign({
    id, name, s: 2, x: 0, y: 0, v: 0, yaw: 0, vy: 0, vxb: 0, air: false, airT: 0,
    steer: 0, flip: 0, spin: 0, roll: 0, tilt: 0,
    trick: null, queue: null, grab: false, grabT: 0, jump: [], points: 0, streak: 0,
    fallT: 0, hitWait: {}, gifts: [], fin: false, t: 0, pop: null,
  }, opts || {});
}
function placeSled(hill, sl, lane) {
  sl.s = 2; sl.x = lane; sl.y = groundAt(hill, sl.s, sl.x); sl.v = 3;
}

// Starts a trick in the air ('front', 'back', 'spinL', 'spinR'); one more may wait for it.
function startTrick(sl, type) {
  if (!sl.air || sl.fallT > 0 || sl.fin || sl.grab) return false;
  if (sl.trick) { if (!sl.queue) sl.queue = type; return true; }
  sl.trick = { type, t: 0 };
  return true;
}
function setGrab(sl, on) {
  if (on && (!sl.air || sl.trick || sl.fallT > 0 || sl.fin)) return false;
  if (!on && sl.grab && sl.air) {
    if (sl.grabT >= GRAB_MIN) sl.jump.push({ type: 'grab', pts: Math.round((TRICKS.grab.pts + GRAB_PER_S * sl.grabT) / 10) * 10 });
    sl.grabT = 0;
  }
  sl.grab = on;
  return true;
}

// A sled changes hands (a phone back after a reload or a drop, the computer taking an away phone's
// sled, or giving it back): a grab belongs to the finger holding it, so it is let go here. A grab
// held long enough counts like any finished trick; the jump's other tricks are kept, and a flip
// or spin still turning finishes by itself. Safe to repeat: a released sled is left as it is.
function handOver(sl) {
  if (sl.grab) setGrab(sl, false);
  sl.grab = false; sl.grabT = 0;
}

function trickDone(sl) {
  const tr = sl.trick, T = TRICKS[tr.type];
  sl.jump.push({ type: tr.type, pts: T.pts });
  sl.flip = 0; sl.spin = 0;
  sl.trick = null;
  if (sl.queue) { sl.trick = { type: sl.queue, t: 0 }; sl.queue = null; }
}

function fall(sl, why) {
  sl.fallT = FALL_T; sl.v *= 0.35; sl.streak = 0;
  sl.trick = null; sl.queue = null; sl.grab = false; sl.grabT = 0; sl.jump = [];
  sl.flip = 0; sl.spin = 0;
  sl.pop = { text: why || 'Kaatuminen!', bad: true, t: 0 };
  if (sl.onEvent) sl.onEvent('fall');
}

// The sled lands: a trick at least LAND_DONE done counts, a held grab or a trick less done is a fall.
function land(hill, sl) {
  sl.air = false;
  sl.vy = 0;
  if (sl.grab) { fall(sl, 'Päästä irti ennen alastuloa!'); return; }
  if (sl.trick) {
    if (sl.trick.t / TRICKS[sl.trick.type].dur >= LAND_DONE) trickDone(sl);
    else { fall(sl); return; }
    if (sl.trick) { sl.trick = null; sl.queue = null; }   // the queued one had not begun
  }
  sl.queue = null;
  sl.flip = 0; sl.spin = 0;
  sl.v *= 0.96;
  if (sl.jump.length) {
    const n = sl.jump.length, sum = sl.jump.reduce((a, j) => a + j.pts, 0);
    sl.streak++;
    const mult = (1 + 0.5 * (n - 1)) * Math.min(3, 1 + 0.25 * (sl.streak - 1));
    const got = Math.round(sum * mult / 10) * 10;
    sl.points += got;
    const names = sl.jump.map(j => TRICKS[j.type].name).join(' + ');
    sl.pop = { text: names, pts: got, mult: n > 1 ? n : 0, streak: sl.streak, t: 0 };
    if (sl.onEvent) sl.onEvent('trick', got);
  } else if (sl.onEvent) sl.onEvent('land');
  sl.jump = [];
}

// The sled's turn for the trick going on; returns how far it has gone, 0 to 1.
function trickPose(sl) {
  const T = TRICKS[sl.trick.type], p = Math.min(1, sl.trick.t / T.dur), e = p * p * (3 - 2 * p);
  sl.flip = sl.trick.type === 'front' ? e * TAU : sl.trick.type === 'back' ? -e * TAU : 0;
  sl.spin = sl.trick.type === 'spinL' ? e * TAU : sl.trick.type === 'spinR' ? -e * TAU : 0;
  return p;
}
const DT = 1 / 120;
const TURN_RATE = 1.4, MAX_YAW = 1.3;   // rad/s at the finger's full reach; the widest heading
// One step of a sled: gravity down the slope, the snow's friction, steering, the jumps, the air.
function step(hill, sl, dt) {
  sl.t += dt;
  if (sl.pop) sl.pop.t += dt;
  if (sl.fallT > 0) sl.fallT = Math.max(0, sl.fallT - dt);
  const steer = sl.fin || sl.fallT > 0 ? 0 : sl.steer;
  for (const id in sl.hitWait) if ((sl.hitWait[id] -= dt) <= 0) delete sl.hitWait[id];

  // The sled keeps its own heading (#475, Eero's choice: no steering by itself). `yaw` is measured
  // from the course, so where the course bends the yaw changes by as much the other way.
  const cd0 = courseDir(hill, sl.s);
  if (sl.air) {
    sl.airT += dt;
    sl.vy -= G * dt;
    sl.v = Math.max(0, sl.v - 0.0016 * sl.v * sl.v * dt);
    sl.s += sl.v * Math.cos(sl.yaw) * dt;
    sl.x += sl.v * Math.sin(sl.yaw) * dt;
    sl.y += sl.vy * dt;
    if (sl.trick) {
      sl.trick.t += dt;
      if (trickPose(sl) >= 1) trickDone(sl);
    }
    if (sl.grab) sl.grabT += dt;
    const gy = groundAt(hill, sl.s, sl.x);
    if (sl.y <= gy) { sl.y = gy; land(hill, sl); }
  } else {
    // Steering: the finger turns the sled, as fast as it is drawn aside, and the sled keeps the way
    // it was turned to when the finger lifts. After a fall it is set pointing down the course again.
    if (sl.fallT > 0) sl.yaw *= Math.max(0, 1 - dt * 3);
    else sl.yaw = clamp(sl.yaw + steer * TURN_RATE * dt, -MAX_YAW, MAX_YAW);
    // Slopes measured behind the sled, so a lip just ahead does not count as a drop yet.
    const e = 0.15, g0 = groundAt(hill, sl.s, sl.x);
    const gs = (g0 - groundAt(hill, sl.s - e, sl.x)) / e;
    const gx = (groundAt(hill, sl.s, sl.x + 0.05) - groundAt(hill, sl.s, sl.x - 0.05)) / 0.1;
    const along = gs * Math.cos(sl.yaw) + gx * Math.sin(sl.yaw);
    const th = Math.atan(-along);
    const off = Math.abs(sl.x) > hill.width / 2;
    const mu = off ? 0.2 : sl.fallT > 0 ? 0.35 : 0.045;
    const a = G * Math.sin(th) - mu * G * Math.cos(th) - 0.0045 * sl.v * sl.v - 0.9 * Math.abs(sl.yaw) * Math.abs(steer) - (sl.fin ? 2.5 : 0);
    sl.v = Math.max(sl.fin ? 0 : 0.6, sl.v + a * dt);
    // The banks push a sled back towards the track.
    sl.vxb += -gx * G * 0.8 * dt; sl.vxb *= Math.max(0, 1 - dt * 2.5);
    const py = sl.y;
    sl.s += sl.v * Math.cos(sl.yaw) * dt;
    sl.x += (sl.v * Math.sin(sl.yaw) + sl.vxb) * dt;
    const gy = groundAt(hill, sl.s, sl.x);
    // Off a lip: the ground drops away from under the sled, which flies on as it was going.
    if (gy < g0 - Math.max(0.12, sl.v * dt * 0.6) && sl.v > 2) {
      const climb = along;   // the ramp's slope just before the lip
      const ang = Math.atan(-climb), sp = sl.v;
      sl.v = sp * Math.cos(Math.atan(climb));
      sl.vy = sp * Math.sin(-ang);
      sl.air = true; sl.airT = 0; sl.y = py + sl.vy * dt; sl.jump = []; sl.grabT = 0;
      if (sl.onEvent) sl.onEvent('jump');
    } else {
      sl.y = gy;
    }
  }
  sl.yaw -= courseDir(hill, sl.s) - cd0;
  // The trees, rocks and snowmen: low enough to hit them is a fall.
  if (sl.fallT <= 0 && !sl.fin) {
    for (const o of hill.obst) {
      if (Math.abs(o.s - sl.s) > 2 || sl.hitWait[o.id]) continue;
      const tall = o.kind === 'kuusi' ? 4 : o.kind === 'lumiukko' ? 1.8 : 0.9;
      if (sl.y - baseAt(hill, o.s) - bankAt(hill, o.x) > tall) continue;
      if (Math.hypot(o.s - sl.s, o.x - sl.x) < o.r + 0.45) {
        sl.hitWait[o.id] = 2;
        sl.x += (sl.x >= o.x ? 1 : -1) * 0.6;
        if (sl.air) { sl.air = false; sl.y = groundAt(hill, sl.s, sl.x); }
        fall(sl, o.kind === 'kuusi' ? 'Kuusi!' : o.kind === 'kivi' ? 'Kivi!' : 'Lumiukko!');
        break;
      }
    }
  }
  // Presents: each sled takes its own.
  for (const gf of hill.gifts) {
    if (Math.abs(gf.s - sl.s) > 1.6 || sl.gifts.includes(gf.id)) continue;
    const gy = baseAt(hill, gf.s) + bankAt(hill, gf.x) + gf.up;
    if (Math.hypot(gf.s - sl.s, gf.x - sl.x, (gy - (sl.y + 0.6)) * 0.8) < (gf.big ? 1.7 : 1.3)) {
      sl.gifts.push(gf.id);
      const p = gf.big ? BIG_GIFT_PTS : GIFT_PTS;
      sl.points += p;
      if (sl.onEvent) sl.onEvent('gift', p);
    }
  }
  if (!sl.fin && sl.s >= hill.len) { sl.fin = true; if (sl.onEvent) sl.onEvent('finish'); }
  // The lean shown in the drawing: into the turn on the snow, a roll while falling.
  sl.tilt += ((sl.air ? 0 : -steer * 0.25) - sl.tilt) * Math.min(1, dt * 6);
  sl.roll = sl.fallT > 0 ? (1 - sl.fallT / FALL_T) * TAU * 1.5 : 0;
}
// Steps a sled by `dt`, in fixed steps.
function advance(hill, sl, dt) {
  sl.acc = (sl.acc || 0) + Math.min(dt, 0.25);
  while (sl.acc >= DT) { step(hill, sl, DT); sl.acc -= DT; }
}

// When the sled would land if nothing changed: a short flight on its own numbers.
function timeToLand(hill, sl) {
  let s = sl.s, x = sl.x, y = sl.y, vy = sl.vy, t = 0;
  const d = 1 / 30;
  while (t < 4) {
    vy -= G * d; s += sl.v * Math.cos(sl.yaw) * d; x += sl.v * Math.sin(sl.yaw) * d; y += vy * d; t += d;
    if (y <= groundAt(hill, s, x)) return t;
  }
  return t;
}

// ---- The computer's sledders ----
// One aims at the jumps ahead, steers round what is in its way, and in the air does a trick when
// it thinks there is time; it misjudges now and then (`err`), and falls like anyone.
function cpuBrain(skill, seed) { return { skill, r: rng(seed), aim: 0, aimFor: -1, think: 0 }; }
function cpuDrive(hill, sl, dt) {
  const b = sl.cpu;
  if (sl.air) {
    if (!sl.trick && !sl.grab && sl.jump.length < b.skill.max) {
      b.think -= dt;
      if (b.think <= 0) {
        b.think = 0.12;
        const left = timeToLand(hill, sl) * (1 + (b.r() < b.skill.err ? 0.5 : 0) - 0.05);
        const types = ['front', 'back', 'spinL', 'spinR'];
        const type = types[Math.floor(b.r() * 4)];
        if (left > TRICKS[type].dur * 1.05) startTrick(sl, type);
      }
    }
    return;
  }
  // Aim: the next jump within reach, else the middle of the track, then dodge what is ahead.
  const k = hill.kicks.find(k => k.s > sl.s + 4 && k.s < sl.s + 110);
  if (k && b.aimFor !== k.i) { b.aimFor = k.i; b.aim = k.x + (b.r() * 2 - 1) * (k.w / 2 - 1.2) * (1 - b.skill.aim); }
  let tx = k ? b.aim : clamp(sl.x * 0.98, -hill.width / 2 + 2, hill.width / 2 - 2);
  for (const o of hill.obst) {
    const ds = o.s - sl.s;
    if (ds < 0 || ds > 26) continue;
    const xAt = sl.x + Math.tan(sl.yaw) * ds;
    if (Math.abs(xAt - o.x) < o.r + 1.4) { tx = o.x + (sl.x >= o.x ? 1 : -1) * (o.r + 2.4); break; }
  }
  // The computer steers like a player: towards a heading that takes it to its line, and back.
  const want = clamp((tx - sl.x) / 6, -0.6, 0.6);
  sl.steer = clamp((want - sl.yaw) * 3, -1, 1);
}
const CPU_SKILL = [
  { max: 1, err: 0.22, aim: 0.6 },
  { max: 2, err: 0.16, aim: 0.75 },
  { max: 2, err: 0.1, aim: 0.85 },
];
const CPU_NAMES = ['Tonttu-Topi', 'Elli', 'Pakkas-Pekka', 'Lumi', 'Ukko-Petteri'];
