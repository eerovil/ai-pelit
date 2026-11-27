'use strict';
// Seittisankari v2 (#529): the round. The free city with missions (Eero: "mene tänne", and an
// arrow shows where): one marked roof at a time, a flag and a light over it; standing on it
// counts it and marks the next one.
// v4 (#561): robbers to catch with the web, in a fixed order of five missions: a roof, robbers on
// a roof, a getaway car, the tower's top, a getaway helicopter (the approved spec). A web hit
// catches one; nothing ever gets away.

// The downtown, the old 6 × 6 middle of the city: LX and BX count its lots.
const LX = k => lotX(C0 + k), BX = (i, j) => boxAt(C0 + i, C0 + j);
const T_BOX = boxAt(TOWER.i, TOWER.j);            // the tower, the city's tallest
const START = { x: LX(2) + 20, z: LX(2) + 20 };   // a street crossing beside the tower
const GOAL_NEAR = 120, GOAL_FAR = 300;            // how far the next roof is from the hero, m
const TOWER_FAR = 600;                            // the tower is its turn's roof only when this near
const KINDS = ['katto', 'rosvot', 'auto', 'torni', 'heli'];
const kindFor = done => KINDS[((done | 0) % KINDS.length + KINDS.length) % KINDS.length];
const isCrook = k => k === 'rosvot' || k === 'auto' || k === 'heli';

// Standing on a building's roof (a hero, or another phone's hero as the host sees it).
const onTop = (h, b) => h.st === 'ground' && h.y >= b.h - 0.1 && h.x > b.x0 - 1 && h.x < b.x1 + 1 && h.z > b.z0 - 1 && h.z < b.z1 + 1;

function newWorld() {
  return { t: 0, flag: null, goal: -1, gt: 0, done: 0, got: 0, kind: null, crooks: [], gone: null, goneT: 0,
    hero: newHero(START.x, 0, START.z, 0) };
}
// The next roof: the tower on its turn (when it is within TOWER_FAR), else a building of
// 20–150 m 120–300 m from the hero, inside the city's edge. `r` is a random number source
// (Math.random in play). Never the roof just reached, so one landing counts once.
function pickTarget(w, r, tower) {
  const h = w.hero, far = b => { const t = roofTop(b); return Math.hypot(t.x - h.x, t.z - h.z); };
  if (tower && T_BOX.id !== w.goal && far(T_BOX) <= TOWER_FAR) return T_BOX.id;
  const ok = [];
  let near = -1, nearD = Infinity;
  for (const b of CITY) {
    if (b.tower || b.h < 20 || b.h > 150 || b.id === w.goal) continue;
    const t = roofTop(b), d = far(b);
    if (d >= GOAL_NEAR && d <= GOAL_FAR && Math.max(Math.abs(t.x), Math.abs(t.z)) < EDGE - 20) ok.push(b.id);
    if (d >= GOAL_NEAR && d < nearD) { near = b.id; nearD = d; }
  }
  if (ok.length) return ok[Math.floor(r() * ok.length)];
  return near >= 0 ? near : (T_BOX.id !== w.goal ? T_BOX.id : CITY.find(b => b.id !== w.goal).id);
}
function setGoal(w, id) {
  w.goal = id; w.gt = 0;
  w.flag = CITY[id] ? roofTop(CITY[id]) : null;
}
// The mission for `w.done` (done % 5 in KINDS): a roof to stand on, or crooks to catch.
function startMission(w, r) {
  r = r || Math.random;
  w.kind = kindFor(w.done); w.gt = 0;
  if (!isCrook(w.kind)) { w.crooks = []; setGoal(w, pickTarget(w, r, w.kind === 'torni')); return; }
  const last = w.goal;
  w.goal = -1; w.flag = null;
  if (w.kind === 'rosvot') {
    // Three robbers on a roof picked like a mission roof; the flag and its light mark the roof.
    const b = CITY[pickTarget(Object.assign({}, w, { goal: last }), r, false)];
    w.crooks = [0, 1, 2].map(() => newRobber(b, r));
    w.flag = roofTop(b); w.crookBox = b.id;
  } else if (w.kind === 'auto') w.crooks = [newCar(w.hero, r)];
  else w.crooks = [newHeli(w.hero, r)];
}
// One step: the clock, the crooks, and the roof reached or the last crook caught.
function stepRound(w, dt, r) {
  r = r || Math.random;
  w.t += dt;
  if (!w.kind || (!isCrook(w.kind) && !CITY[w.goal])) startMission(w, r);
  w.gt += dt;
  for (const k of w.crooks) stepCrook(k, w.hero, dt, r);
  if (w.gone) { for (const k of w.gone) stepCrook(k, w.hero, dt, r); if ((w.goneT -= dt) <= 0) w.gone = null; }
  if (w.got && (w.got.show -= dt) <= 0) w.got = 0;
  const done = isCrook(w.kind) ? w.crooks.length > 0 && w.crooks.every(k => k.caught) : onTop(w.hero, CITY[w.goal]);
  if (!done) return false;
  w.got = { t: w.gt, kind: w.kind, tower: w.kind === 'torni' && !!CITY[w.goal] && !!CITY[w.goal].tower, show: 2.5 };
  if (isCrook(w.kind)) { w.gone = w.crooks; w.goneT = 10; w.crooks = []; }   // the caught ones stay a moment
  w.done++;
  startMission(w, r);
  return true;
}

// ---- The crooks. Each is { id, type, x, y, z, yaw, caught, ct (seconds since caught) } ----
let crookN = 0;
const ROB_SPEED = 1.6, ROB_EDGE = 1.5;
const CAR_SPEED = 20, CAR_NEAR = 150, CAR_FAR = 250, STREET = LOT;   // streets every 40 m, at x = 40k
const HELI_SPEED = 15, HELI_LOW = 70, HELI_HIGH = 90, HELI_CLEAR = 8, HELI_AREA = 700;
// How big each is to the web: the aim hits it this far from its middle (D3: 1.5 m past its body).
const CROOK_R = { rosvo: 0.4 + 1.5, auto: 2.2 + 1.5, heli: 4 + 1.5 };
const CROOK_MID = { rosvo: 0.9, auto: 0.8, heli: 1.5 };

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
function stepCrook(k, h, dt, r) {
  if (k.caught) k.ct += dt;
  if (k.type === 'rosvo') {
    if (k.caught) return;
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
    if (k.caught) {                          // tied down: sinks onto what is under it
      const floor = supportAt(k.x, k.z, 3);
      k.y = Math.max(floor, k.y - 12 * dt);
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
    if (k.caught) continue;
    const cx = k.x - r.ox, cy = k.y + CROOK_MID[k.type] - r.oy, cz = k.z - r.oz;
    const t = cx * r.dx + cy * r.dy + cz * r.dz, rad = CROOK_R[k.type];
    if (t <= 0 || t > PULL_MAX) continue;
    const off = Math.hypot(cx - r.dx * t, cy - r.dy * t, cz - r.dz * t);
    if (off > rad || t > wallT + rad || t >= bt) continue;
    best = k; bt = t;
  }
  return best;
}
function catchCrook(k) { if (k && !k.caught) { k.caught = true; k.ct = 0; return true; } return false; }
