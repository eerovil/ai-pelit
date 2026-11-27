'use strict';
// Seittisankari v2 (#529): the round. The free city with missions (Eero: "mene tänne", and an
// arrow shows where): one marked roof at a time, a flag and a light over it; standing on it
// counts it and marks the next one.
// v4 (#561): robbers to catch with the web, in a fixed order of five missions: a roof, robbers on
// a roof, a getaway car, the tower's top, a getaway helicopter (the approved spec). A web hit
// catches one; nothing ever gets away.
// v5 (#565): the story (story.js) gives its own list of missions per chapter, two new kinds
// (pelasta: reach a window cleaner hanging on a wall; boss: Varjo's helicopter, three hits) and,
// in chapters 5–8, a time limit per mission; when it runs out the mission starts again.

// The downtown, the old 6 × 6 middle of the city: LX and BX count its lots.
const LX = k => lotX(C0 + k), BX = (i, j) => boxAt(C0 + i, C0 + j);
const T_BOX = boxAt(TOWER.i, TOWER.j);            // the tower, the city's tallest
const START = { x: LX(2) + 20, z: LX(2) + 20 };   // a street crossing beside the tower
const GOAL_NEAR = 120, GOAL_FAR = 300;            // how far the next roof is from the hero, m
const KINDS = ['katto', 'rosvot', 'auto', 'torni', 'heli'];
const kindFor = done => KINDS[((done | 0) % KINDS.length + KINDS.length) % KINDS.length];
const isCrook = k => k === 'rosvot' || k === 'auto' || k === 'heli' || k === 'pelasta' || k === 'boss' || k === 'pakenevat' || k === 'putoava';
// Missions of several marked roofs in a row (v5, #565): Varjo's three bombs, and the money bag
// picked up from one roof and carried to another.
const ROOFS_N = { pommit: 3, paketti: 2 };
// The time limits of the story's later chapters, s (#565: at least twice a measured run, rule 9).
// No clock on a getaway car: the test bot missed it in 2 of 5 runs within 120 s (#565).
const LIMITS = { rosvot: 120, heli: 150, pelasta: 90, boss: 240, pakenevat: 150, pommit: 150, putoava: 90, auto: 400 };
// The mission now: in the story its chapter's step, else v4's cycle by the count.
function missionFor(w) {
  if (w.story && typeof STORY !== 'undefined') {
    const ch = STORY[w.story.ch], st = ch && ch.steps[w.story.step];
    if (st) return Object.assign({ lim: ch.lim && LIMITS[st.k] || 0 }, st);
  }
  return { k: kindFor(w.done), lim: 0 };
}

// Standing on a building's roof (a hero, or another phone's hero as the host sees it).
const onTop = (h, b) => h.st === 'ground' && h.y >= b.h - 0.1 && h.x > b.x0 - 1 && h.x < b.x1 + 1 && h.z > b.z0 - 1 && h.z < b.z1 + 1;

function newWorld() {
  return { t: 0, flag: null, goal: -1, gt: 0, done: 0, got: 0, kind: null, crooks: [], gone: null, goneT: 0,
    story: null, ct: 0, lim: 0, fail: null, chDone: false, radio: null, seq: 0, part: null, hero: newHero(START.x, 0, START.z, 0) };
}
// The next roof: the tower on its turn however far (spec D1, review on #563), else a building of
// 20–150 m 120–300 m from the hero, inside the city's edge. `r` is a random number source
// (Math.random in play). Never the roof just reached, so one landing counts once.
// The story's first chapter (#565) asks for a low roof close by (o.near) and a high one (o.high).
function pickTarget(w, r, tower, o) {
  const h = w.hero, far = b => { const t = roofTop(b); return Math.hypot(t.x - h.x, t.z - h.z); };
  o = o || {};
  const dMin = o.near ? 30 : GOAL_NEAR, dMax = o.near ? 110 : GOAL_FAR;
  const hMin = o.high ? 90 : 20, hMax = o.near ? 45 : 150;
  // Not while the hero already stands on its top: a car caught from up there is no free tower.
  if (tower && T_BOX.id !== w.goal && !onTop(h, T_BOX)) return T_BOX.id;
  const ok = [];
  let near = -1, nearD = Infinity;
  for (const b of CITY) {
    if (b.tower || b.h < hMin || b.h > hMax || b.id === w.goal || (o.not && o.not.includes(b.id))) continue;
    const t = roofTop(b), d = far(b);
    if (d >= dMin && d <= dMax && Math.max(Math.abs(t.x), Math.abs(t.z)) < EDGE - 20) ok.push(b.id);
    if (d >= (o.near ? dMin : GOAL_NEAR) && d < nearD) { near = b.id; nearD = d; }
  }
  if (ok.length) return ok[Math.floor(r() * ok.length)];
  return near >= 0 ? near : (T_BOX.id !== w.goal ? T_BOX.id : CITY.find(b => b.id !== w.goal).id);
}
function setGoal(w, id) {
  w.goal = id; w.gt = 0;
  w.flag = CITY[id] ? roofTop(CITY[id]) : null;
}
// The mission for `w.done` (done % 5 in KINDS), or the story's step: a roof to stand on, or
// crooks to catch (or window cleaners to reach).
function startMission(w, r) {
  r = r || Math.random;
  const m = missionFor(w);
  w.kind = m.k; w.gt = 0; w.lim = m.lim; w.fail = null; w.seq = 0; w.part = null; w.used = null;
  if (w.story && m.say) w.radio = { who: m.say[0], text: m.say[1], t: 6 };
  if (!isCrook(w.kind)) { w.crooks = []; setGoal(w, pickTarget(w, r, w.kind === 'torni', m)); return; }
  const last = w.goal;
  w.goal = -1; w.flag = null;
  if (w.kind === 'rosvot' || w.kind === 'pakenevat') {
    // Three robbers on a roof picked like a mission roof; the flag and its light mark the roof.
    const b = CITY[pickTarget(Object.assign({}, w, { goal: last }), r, false)];
    w.crooks = [0, 1, 2].map(() => newRobber(b, r));
    if (w.kind === 'pakenevat') for (const k of w.crooks) { k.flee = true; k.cd = 0; }
    w.flag = roofTop(b); w.crookBox = b.id;
  } else if (w.kind === 'auto') w.crooks = [newCar(w.hero, r)];
  else if (w.kind === 'pelasta') w.crooks = [newCleaner(w.hero, r)];
  else if (w.kind === 'putoava') w.crooks = [newFaller(w.hero, r)];
  else if (w.kind === 'boss') w.crooks = [newBoss(w.hero, r)];
  else w.crooks = [newHeli(w.hero, r)];
}
// One step: the clock, the crooks, and the roof reached or the last crook caught. Returns true
// when the mission was done in this step; 'fail' when its time limit ran out first (v5, #565:
// done wins a step that also crosses the limit, rule 8). Nothing moves after a fail or the
// story chapter's end until the game starts the next one.
function stepRound(w, dt, r) {
  r = r || Math.random;
  if (w.fail) return false;
  if (w.chDone) {   // the chapter is over: only the caught ones settle, and its "done" shows
    if (w.gone) for (const k of w.gone) stepCrook(k, w.hero, dt, r);
    if (w.got && (w.got.show -= dt) <= 0) w.got = 0;
    return false;
  }
  w.t += dt;
  if (!w.kind || (!isCrook(w.kind) && !CITY[w.goal])) startMission(w, r);
  w.gt += dt; w.ct += dt;
  if (w.radio && (w.radio.t -= dt) <= 0) w.radio = null;
  for (const k of w.crooks) stepCrook(k, w.hero, dt, r);
  for (const k of w.crooks) if (k.type === 'apu' && !k.caught && reachCleaner(w.hero, k)) rescue(k);
  if (w.gone) { for (const k of w.gone) stepCrook(k, w.hero, dt, r); if ((w.goneT -= dt) <= 0) w.gone = null; }
  if (w.got && (w.got.show -= dt) <= 0) w.got = 0;
  if (w.part && (w.part.show -= dt) <= 0) w.part = null;
  // A falling person reached the street (v5): the police net took him, and the mission starts again.
  if (w.crooks.some(k => k.lost)) { w.fail = { kind: w.kind }; w.crooks = []; w.flag = null; w.goal = -1; w.radio = null; return 'fail'; }
  // A roof of several in a row: the next one, under the same clock.
  if (ROOFS_N[w.kind] && w.seq < ROOFS_N[w.kind] - 1 && onTop(w.hero, CITY[w.goal])) {
    // A roof not used yet in this row, and the clock goes on.
    const gt = w.gt, used = (w.used || []).concat(w.goal);
    w.seq++; w.part = { kind: w.kind, show: 2 }; w.used = used;
    setGoal(w, pickTarget(w, r, false, { not: used })); w.gt = gt;
  }
  const done = isCrook(w.kind) ? w.crooks.length > 0 && w.crooks.every(k => k.caught) : onTop(w.hero, CITY[w.goal]);
  if (!done) {
    if (w.lim && w.gt >= w.lim) { w.fail = { kind: w.kind }; w.crooks = []; w.flag = null; w.goal = -1; w.radio = null; return 'fail'; }
    return false;
  }
  w.got = { t: w.gt, kind: w.kind, tower: w.kind === 'torni' && !!CITY[w.goal] && !!CITY[w.goal].tower, show: 2.5 };
  // The caught ones stay a moment, the last mission's ones too when it ended under 10 s ago.
  if (isCrook(w.kind)) { w.gone = (w.gone || []).concat(w.crooks); w.goneT = 10; w.crooks = []; }
  if (w.story) {
    // The story: its next step, or the chapter's end (the game shows its closing card).
    w.story.step++;
    if (!STORY[w.story.ch] || w.story.step >= STORY[w.story.ch].steps.length) { w.chDone = true; w.flag = null; w.goal = -1; w.kind = null; return true; }
  } else w.done++;
  startMission(w, r);
  return true;
}
// After a fail (v5, #565): the same mission again, fresh, its clock from zero; the chapter's clock goes on.
function retryMission(w, r) { w.fail = null; w.gone = null; startMission(w, r); }

// ---- The crooks. Each is { id, type, x, y, z, yaw, caught, ct (seconds since caught) } ----
let crookN = 0;
const ROB_SPEED = 1.6, ROB_EDGE = 1.5;
const CAR_SPEED = 20, CAR_NEAR = 150, CAR_FAR = 250, STREET = LOT;   // streets every 40 m, at x = 40k
const HELI_SPEED = 15, HELI_LOW = 70, HELI_HIGH = 90, HELI_CLEAR = 8, HELI_AREA = 700;
// How big each is to the web: the aim hits it this far from its middle (D3: 1.5 m past its body).
const CROOK_R = { rosvo: 0.4 + 1.5, auto: 2.2 + 1.5, heli: 4 + 1.5, boss: 6 + 1.5, putoava: 0.4 + 1.5 };
const CROOK_MID = { rosvo: 0.9, auto: 0.8, heli: 1.5, apu: 0.9, boss: 2.2, putoava: 0.9 };
const BOSS_HITS = 3, RESCUE_R = 3;

function newRobber(b, r) {
  const x0 = b.x0 + ROB_EDGE, x1 = b.x1 - ROB_EDGE, z0 = b.z0 + ROB_EDGE, z1 = b.z1 - ROB_EDGE;
  const k = { id: ++crookN, type: 'rosvo', box: b.id, x: x0 + r() * (x1 - x0), y: b.h, z: z0 + r() * (z1 - z0), yaw: r() * TAU,
    vx: 0, vz: 0, caught: false, ct: 0, wx: 0, wz: 0, wait: r() * 2 };
  return k;
}
// Getaway car: on the street lines, crossing to crossing. A crossing is (a, c) at x = 40a, z = 40c.
const CROSS_MAX = Math.floor((EDGE - 30) / STREET);
function newCar(h, r) {
  const opts = [];
  for (let a = -CROSS_MAX; a <= CROSS_MAX; a++) for (let c = -CROSS_MAX; c <= CROSS_MAX; c++) {
    const d = Math.hypot(a * STREET - h.x, c * STREET - h.z);
    if (d >= CAR_NEAR && d <= CAR_FAR) opts.push([a, c]);
  }
  const [a, c] = opts.length ? opts[Math.floor(r() * opts.length)] : [0, 0];
  const k = { id: ++crookN, type: 'auto', a, c, da: 0, dc: 0, s: 0, x: a * STREET, y: 0, z: c * STREET, yaw: 0, v: CAR_SPEED, caught: false, ct: 0 };
  carTurn(k, h, r);
  return k;
}
// At a crossing: never back the way it came (unless it must), and mostly the way away from the hero.
function carTurn(k, h, r) {
  const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]].filter(([da, dc]) =>
    Math.abs(k.a + da) <= CROSS_MAX && Math.abs(k.c + dc) <= CROSS_MAX && !(da === -k.da && dc === -k.dc && (k.da || k.dc)));
  const away = [k.x - h.x, k.z - h.z];
  let pick;
  if (r() < 0.7) pick = dirs.reduce((p, d) => d[0] * away[0] + d[1] * away[1] > p[0] * away[0] + p[1] * away[1] ? d : p, dirs[0]);
  else pick = dirs[Math.floor(r() * dirs.length)];
  if (!pick) pick = [-k.da, -k.dc];
  k.da = pick[0]; k.dc = pick[1]; k.s = 0;
}
// Getaway helicopter: straight flights between waypoints at 70–90 m, each checked clear of every
// building (HELI_CLEAR under it); it turns on the spot before each flight, as a helicopter can.
function newHeli(h, r) {
  let x = 0, z = 0;
  for (let i = 0; i < 60; i++) {
    const a = r() * TAU, d = CAR_NEAR + r() * (CAR_FAR - CAR_NEAR);
    x = clamp(h.x + Math.sin(a) * d, -HELI_AREA, HELI_AREA); z = clamp(h.z + Math.cos(a) * d, -HELI_AREA, HELI_AREA);
    if (supportAt(x, z, HELI_CLEAR) < HELI_LOW - HELI_CLEAR) break;
  }
  const y = HELI_LOW + r() * (HELI_HIGH - HELI_LOW);
  const k = { id: ++crookN, type: 'heli', x, y, z, yaw: r() * TAU, caught: false, ct: 0, from: null, to: null, s: 0, len: 0, v: 0 };
  heliLeg(k, r);
  return k;
}
// The nearest roof (not the tower) below a caught helicopter that it can fly over to at its own
// height; null when there is none, and it comes down where it is.
function heliRoof(k) {
  let best = null, bestD = Infinity;
  eachNear(k.x, k.z, 160, b => {
    if (b.tower || b.h > k.y - HELI_CLEAR) return;
    const t = roofTop(b), d = Math.hypot(t.x - k.x, t.z - k.z);
    if (d < bestD && heliClear(k.x, k.y, k.z, t.x, k.y, t.z)) { best = b; bestD = d; }
  });
  return best;
}
function heliClear(x0, y0, z0, x1, y1, z1) {
  const n = Math.ceil(Math.hypot(x1 - x0, z1 - z0) / 4);
  for (let i = 0; i <= n; i++) {
    const f = i / (n || 1);
    if (supportAt(x0 + (x1 - x0) * f, z0 + (z1 - z0) * f, HELI_CLEAR) > Math.min(y0, y1) - HELI_CLEAR) return false;
  }
  return true;
}
function heliLeg(k, r) {
  k.from = { x: k.x, y: k.y, z: k.z }; k.to = null; k.s = 0; k.v = 0;
  for (let i = 0; i < 40 && !k.to; i++) {
    const a = r() * TAU, d = 120 + r() * 230;
    const x = clamp(k.x + Math.sin(a) * d, -HELI_AREA, HELI_AREA), z = clamp(k.z + Math.cos(a) * d, -HELI_AREA, HELI_AREA);
    const y = HELI_LOW + r() * (HELI_HIGH - HELI_LOW);
    if (Math.hypot(x - k.x, z - k.z) > 40 && heliClear(k.x, k.y, k.z, x, y, z)) k.to = { x, y, z };
  }
  k.len = k.to ? Math.hypot(k.to.x - k.x, k.to.y - k.y, k.to.z - k.z) : 0;
}
// ---- v5 (#565): window cleaners on walls, and Varjo's helicopter ----
// A cleaner hangs on a wall of a building at least 40 m high, 120–300 m from the hero, 20–60 m up,
// facing out of the wall (nx, nz). Reaching within RESCUE_R m saves him: the web lifts him onto the roof.
function newCleaner(h, r) {
  const ok = CITY.filter(b => !b.tower && b.h >= 40 && Math.max(Math.abs(b.x0), Math.abs(b.x1), Math.abs(b.z0), Math.abs(b.z1)) < EDGE - 20 &&
    (d => d >= GOAL_NEAR && d <= GOAL_FAR)(Math.hypot((b.x0 + b.x1) / 2 - h.x, (b.z0 + b.z1) / 2 - h.z)));
  const b = ok.length ? ok[Math.floor(r() * ok.length)] : T_BOX;
  const f = Math.floor(r() * 4), u = r(), y = 20 + r() * (Math.min(60, b.h - 6) - 20);
  const [nx, nz] = [[1, 0], [-1, 0], [0, 1], [0, -1]][f];
  const x = nx ? (nx > 0 ? b.x1 + 0.45 : b.x0 - 0.45) : b.x0 + 2 + u * (b.x1 - b.x0 - 4);
  const z = nz ? (nz > 0 ? b.z1 + 0.45 : b.z0 - 0.45) : b.z0 + 2 + u * (b.z1 - b.z0 - 4);
  return { id: ++crookN, type: 'apu', box: b.id, x, y, z, nx, nz, yaw: Math.atan2(-nx, -nz), caught: false, ct: 0 };
}
const reachCleaner = (h, k) => Math.hypot(h.x - k.x, h.y - k.y, h.z - k.z) < RESCUE_R;
function rescue(k) {
  const b = CITY[k.box];
  k.caught = true; k.ct = 0;
  k.x = clamp(k.x - k.nx * 2, b.x0 + 1, b.x1 - 1); k.z = clamp(k.z - k.nz * 2, b.z0 + 1, b.z1 - 1); k.y = b.h;
  k.yaw = Math.atan2(k.nx, k.nz);
}
// A fleeing robber (v5): with the hero within FLEE_NEAR m, he leaps to a roof nearby (its middle
// FLEE_MIN–FLEE_MAX m off, at most FLEE_DH m higher or lower, the one farthest from the hero), and
// rests FLEE_REST s before he can flee again. A leap takes LEAP_T s; a web hit in the air counts.
const FLEE_NEAR = 25, FLEE_MIN = 15, FLEE_MAX = 50, FLEE_DH = 25, FLEE_REST = 5, LEAP_T = 1.2;
function fleeFrom(k, h, r) {
  if (k.cd > 0) return false;
  if (Math.hypot(h.x - k.x, h.z - k.z) > FLEE_NEAR || Math.abs(h.y - k.y) > 15) return false;
  const cur = CITY[k.box];
  let best = null, bd = -1;
  eachNear(k.x, k.z, FLEE_MAX + 20, b => {
    if (b === cur || b.tower || b.h < 15 || Math.abs(b.h - cur.h) > FLEE_DH) return;
    const t = roofTop(b), d = Math.hypot(t.x - k.x, t.z - k.z);
    if (d < FLEE_MIN || d > FLEE_MAX) return;
    const away = Math.hypot(t.x - h.x, t.z - h.z);
    if (away > bd) { bd = away; best = b; }
  });
  if (!best) { k.cd = 1; return false; }
  const t = roofTop(best);
  const x1 = clamp(t.x + (r() - 0.5) * 4, best.x0 + ROB_EDGE, best.x1 - ROB_EDGE), z1 = clamp(t.z + (r() - 0.5) * 4, best.z0 + ROB_EDGE, best.z1 - ROB_EDGE);
  k.jump = { x0: k.x, y0: k.y, z0: k.z, x1, y1: best.h, z1, t: 0, box: best.id };
  k.yaw = Math.atan2(x1 - k.x, z1 - k.z); k.vx = k.vz = 0;
  return true;
}
function stepLeap(k, dt) {
  const j = k.jump;
  j.t = Math.min(1, j.t + dt / LEAP_T);
  k.x = j.x0 + (j.x1 - j.x0) * j.t; k.z = j.z0 + (j.z1 - j.z0) * j.t;
  k.y = j.y0 + (j.y1 - j.y0) * j.t + Math.sin(j.t * Math.PI) * (6 + Math.abs(j.y1 - j.y0) * 0.3);
  if (j.t >= 1) { k.box = j.box; k.y = j.y1; k.jump = null; k.cd = FLEE_REST; k.wx = k.wz = 0; k.wait = 0.3; }
}
// A falling person (v5): hangs from a roof's edge (a building 50–150 m high, 120–300 m from the
// hero) until the hero is within FALL_NEAR m, then slides down the wall at FALL_V m/s. A web on
// him while he falls catches him, and the web lets him down to the street. At the street first:
// `lost`, the police net (the mission starts again).
const FALL_NEAR = 70, FALL_V = 5;
function newFaller(h, r) {
  const ok = CITY.filter(b => !b.tower && b.h >= 50 && b.h <= 150 && Math.max(Math.abs(b.x0), Math.abs(b.x1), Math.abs(b.z0), Math.abs(b.z1)) < EDGE - 20 &&
    (d => d >= GOAL_NEAR && d <= GOAL_FAR)(Math.hypot((b.x0 + b.x1) / 2 - h.x, (b.z0 + b.z1) / 2 - h.z)));
  const b = ok.length ? ok[Math.floor(r() * ok.length)] : T_BOX;
  // The side facing the hero, so he sees him fall.
  const t = roofTop(b), dx = h.x - t.x, dz = h.z - t.z;
  const [nx, nz] = Math.abs(dx) > Math.abs(dz) ? [Math.sign(dx) || 1, 0] : [0, Math.sign(dz) || 1];
  const x = nx ? (nx > 0 ? b.x1 + 0.45 : b.x0 - 0.45) : t.x, z = nz ? (nz > 0 ? b.z1 + 0.45 : b.z0 - 0.45) : t.z;
  return { id: ++crookN, type: 'putoava', box: b.id, x, y: b.h - 1.9, z, nx, nz, yaw: Math.atan2(-nx, -nz), caught: false, ct: 0, falling: false, lost: false };
}
function stepFaller(k, h, dt) {
  if (k.caught) { k.y = Math.max(0, k.y - 3 * dt); return; }
  if (!k.falling) { if (Math.hypot(h.x - k.x, h.z - k.z) < FALL_NEAR) k.falling = true; return; }
  k.y = Math.max(0, k.y - FALL_V * dt);
  if (k.y <= 0.5) k.lost = true;
}
// Varjo's helicopter: v4's helicopter, bigger, with three hits to take. After the first two it
// breaks free and flies 150–250 m off at once.
// Varjo's helicopter takes off from above the tower's top (BOSS_UP m over it) and flies its
// first 150–250 m leg away at once, as after each hit.
// Its legs start high over the tower, so each is checked at the height it flies at each point.
const BOSS_UP = 30;
function heliClearDown(x0, y0, z0, x1, y1, z1) {
  const n = Math.ceil(Math.hypot(x1 - x0, z1 - z0) / 4);
  for (let i = 0; i <= n; i++) {
    const f = i / (n || 1);
    if (supportAt(x0 + (x1 - x0) * f, z0 + (z1 - z0) * f, HELI_CLEAR) > y0 + (y1 - y0) * f - HELI_CLEAR) return false;
  }
  return true;
}
function newBoss(h, r) {
  const k = newHeli(h, r), t = CITY.find(b => b.tower);
  k.type = 'boss'; k.hp = BOSS_HITS; k.hitT = 0;
  if (t) { const p = roofTop(t); k.x = p.x; k.y = t.h + BOSS_UP; k.z = p.z; bossLeg(k, r); }
  return k;
}
function bossLeg(k, r) {
  k.from = { x: k.x, y: k.y, z: k.z }; k.to = null; k.s = 0; k.v = HELI_SPEED;
  for (let i = 0; i < 60 && !k.to; i++) {
    const a = r() * TAU, d = 150 + r() * 100;
    const x = clamp(k.x + Math.sin(a) * d, -HELI_AREA, HELI_AREA), z = clamp(k.z + Math.cos(a) * d, -HELI_AREA, HELI_AREA);
    const y = HELI_LOW + r() * (HELI_HIGH - HELI_LOW);
    if (Math.hypot(x - k.x, z - k.z) > 140 && heliClearDown(k.x, k.y, k.z, x, y, z)) k.to = { x, y, z };
  }
  if (!k.to) return heliLeg(k, r);
  k.yaw = Math.atan2(k.to.x - k.x, k.to.z - k.z);   // it turns away at once, so the flight starts now
  k.len = Math.hypot(k.to.x - k.x, k.to.y - k.y, k.to.z - k.z);
}
function stepCrook(k, h, dt, r) {
  if (k.caught) k.ct += dt;
  if (k.type === 'apu') return;
  if (k.hitT > 0) k.hitT -= dt;
  if (k.type === 'putoava') return stepFaller(k, h, dt);
  if (k.type === 'rosvo') {
    if (k.cd > 0) k.cd -= dt;               // the rest after a leap runs out
    if (k.jump) return stepLeap(k, dt);       // mid-jump to the next roof, caught or not
    if (k.caught) return;
    if (k.flee && fleeFrom(k, h, r)) return;
    const b = CITY[k.box];
    if (k.wait > 0) { k.wait -= dt; k.vx = k.vz = 0; return; }
    const dx = k.wx - k.x, dz = k.wz - k.z, d = Math.hypot(dx, dz);
    if (!k.wx && !k.wz || d < 0.3) {       // a new spot on the roof, after a short stop
      k.wx = b.x0 + ROB_EDGE + r() * (b.x1 - b.x0 - 2 * ROB_EDGE); k.wz = b.z0 + ROB_EDGE + r() * (b.z1 - b.z0 - 2 * ROB_EDGE);
      if (d < 0.3) k.wait = 0.5 + r() * 1.5;
      return;
    }
    k.vx = dx / d * ROB_SPEED; k.vz = dz / d * ROB_SPEED; k.yaw = Math.atan2(dx, dz);
    k.x = clamp(k.x + k.vx * dt, b.x0 + ROB_EDGE, b.x1 - ROB_EDGE); k.z = clamp(k.z + k.vz * dt, b.z0 + ROB_EDGE, b.z1 - ROB_EDGE);
    k.y = b.h;
  } else if (k.type === 'auto') {
    if (k.caught) k.v = Math.max(0, k.v - CAR_SPEED * 1.2 * dt);   // skids to a stop on its street
    k.s += k.v * dt;
    while (k.s >= STREET) { k.s -= STREET; k.a += k.da; k.c += k.dc; if (!k.caught) carTurn(k, h, r); else { k.s = 0; k.v = 0; } }
    k.x = (k.a + k.da * k.s / STREET) * STREET; k.z = (k.c + k.dc * k.s / STREET) * STREET;
    k.yaw = Math.atan2(k.da, k.dc);
  } else {
    if (k.caught) {                          // tied down: flown over the nearest roof below it, then set down (D6)
      if (!('land' in k)) k.land = heliRoof(k);
      const b = k.land, t = b && roofTop(b), d = t ? Math.hypot(t.x - k.x, t.z - k.z) : 0;
      if (d > 0.05) { const m = Math.min(d, 12 * dt); k.x += (t.x - k.x) / d * m; k.z += (t.z - k.z) / d * m; return; }
      if (t) { k.x = t.x; k.z = t.z; }
      k.y = Math.max(supportAt(k.x, k.z, 3), k.y - 12 * dt);
      return;
    }
    if (!k.to) { heliLeg(k, r); return; }
    const dx = k.to.x - k.from.x, dz = k.to.z - k.from.z, want = Math.atan2(dx, dz);
    const turn = Math.atan2(Math.sin(want - k.yaw), Math.cos(want - k.yaw));
    k.yaw += clamp(turn, -1.5 * dt, 1.5 * dt);
    const face = Math.abs(turn) < 0.3;
    k.v = face ? Math.min(HELI_SPEED, k.v + 6 * dt, Math.sqrt(2 * 6 * Math.max(0, k.len - k.s)) + 0.5) : 0;
    k.s = Math.min(k.len, k.s + k.v * dt);
    const f = k.len ? k.s / k.len : 1;
    k.x = k.from.x + dx * f; k.y = k.from.y + (k.to.y - k.from.y) * f; k.z = k.from.z + dz * f;
    if (k.s >= k.len) heliLeg(k, r);
  }
}
// The crook the aim would web: on the aim line within PULL_MAX, nearer than the building it hits
// (a robber standing on a roof wins over the roof under his feet). Null when none.
function aimCrook(h, yaw, pitch, crooks) {
  if (!crooks || !crooks.length) return null;
  const r = aimRay(h, yaw, pitch), wall = aimPull(h, yaw, pitch);
  const wallT = wall ? Math.hypot(wall.x - r.ox, wall.y - r.oy, wall.z - r.oz) : Infinity;
  let best = null, bt = Infinity;
  for (const k of crooks) {
    if (k.caught || k.type === 'apu') continue;   // a window cleaner is reached, never webbed
    if (k.type === 'putoava' && !k.falling) continue;   // a person still holding on is not webbed off
    const cx = k.x - r.ox, cy = k.y + CROOK_MID[k.type] - r.oy, cz = k.z - r.oz;
    const t = cx * r.dx + cy * r.dy + cz * r.dz, rad = CROOK_R[k.type];
    if (t <= 0 || t > PULL_MAX) continue;
    const off = Math.hypot(cx - r.dx * t, cy - r.dy * t, cz - r.dz * t);
    if (off > rad || t > wallT + rad || t >= bt) continue;
    best = k; bt = t;
  }
  return best;
}
function catchCrook(k, r) {
  if (!k || k.caught || k.type === 'apu' || (k.type === 'putoava' && !k.falling)) return false;
  if (k.type === 'boss' && k.hp > 1) { k.hp--; k.hitT = 1.2; bossLeg(k, r || Math.random); return true; }
  if (k.type === 'boss') k.hp = 0;
  k.caught = true; k.ct = 0; return true;
}
