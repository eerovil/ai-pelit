'use strict';
// Lentokone v1 (#533): the world and the plane as plain numbers. Nothing here draws, so the tests
// drive it directly (`step(p, dt)`).
//
// World: x metres east, z metres south (three.js's own axes), y metres up. A heading is in radians
// clockwise from north: 0 north (-z), PI/2 east (+x).

const G = 9.81, TAU = Math.PI * 2, DEG = Math.PI / 180, DT = 1 / 120;
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
function smooth(u) { u = clamp(u, 0, 1); return u * u * (3 - 2 * u); }
function lerp(a, b, t) { return a + (b - a) * t; }
function wrapAngle(a) { while (a > Math.PI) a -= TAU; while (a < -Math.PI) a += TAU; return a; }
function rng(seed) {
  let s = (seed >>> 0) || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}
function hash2(i, j) { let h = (i * 374761393 + j * 668265263) >>> 0; h = (h ^ (h >>> 13)) * 1274126177 >>> 0; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; }
const dirX = h => Math.sin(h), dirZ = h => -Math.cos(h);

// ---- The plane: a small single-engine high-wing plane ----
const PLANE = {
  m: 1000, S: 16, rho: 1.225,
  cl0: 0.35, cla: 5.2, aoaStall: 0.24,          // lift: CL = cl0 + cla * aoa, up to the stall
  flapCl: [0, 0.3, 0.6], flapCd: [0, 0.02, 0.05],
  cd0: 0.03, k: 0.05, gearCd: 0.012,
  thrust: 3600, vMaxThrust: 105,                 // N at a standstill, falling to 0 at 105 m/s
  pitchRate: 0.55, bankRate: 1.1, maxBank: 60 * DEG,
  vRotate: 20,                                   // the nose wheel may lift from here (m/s)
  brake: 4.5, roll: 0.03,
};
const VR_KMH = 100;   // told to the player: pull back at about this speed

// ---- The airfields: one chain of six, each route flies from one to the next ----
// A runway: its threshold (x, z), the heading it is landed and taken off along, length, width, height.
const FIELDS = [
  { name: 'Kotikenttä', x: 0, z: 0, hdg: 0, len: 1000, wid: 30, elev: 20 },
  { name: 'Järvikenttä', x: 0, z: -7000, hdg: 0, len: 1000, wid: 30, elev: 15 },
  { name: 'Saarikenttä', x: 5200, z: -11800, hdg: 90 * DEG, len: 900, wid: 30, elev: 8 },
  { name: 'Peltokenttä', x: 13600, z: -9800, hdg: 120 * DEG, len: 1100, wid: 30, elev: 25 },
  { name: 'Kaupunkikenttä', x: 18200, z: -2400, hdg: 180 * DEG, len: 1200, wid: 35, elev: 18 },
  { name: 'Tunturikenttä', x: 13000, z: 7400, hdg: 240 * DEG, len: 500, wid: 25, elev: 120 },
];
// Wind: the way it blows to (a heading) and its speed, m/s; gusts add up to `gust`.
const ROUTES = [
  { name: 'Ensilento', from: 0, to: 1, guide: true, note: 'Suoraan pohjoiseen, tyyni sää' },
  { name: 'Saarelle', from: 1, to: 2, guide: true, note: 'Käännös itään, kenttä järven saaressa' },
  { name: 'Sivutuuli', from: 2, to: 3, wind: { to: 180 * DEG, v: 6, gust: 2 }, note: 'Tuuli pohjoisesta työntää sivulle' },
  { name: 'Iltalento', from: 3, to: 4, dusk: true, note: 'Hämärässä, kiitoradan valot' },
  { name: 'Tunturiin', from: 4, to: 5, wind: { to: 60 * DEG, v: 3, gust: 1.5 }, note: 'Lyhyt kiitorata tunturien välissä' },
];
const APPROACH = 3000;     // the approach point is this far out on the runway's line
const GLIDE = 3 * DEG;     // the glide path the lights beside the runway show
const BOUNDS = { x0: -5000, x1: 23000, z0: -16000, z1: 13000 };
const WATER = 0;

// Along and across a runway: a metres from the threshold along its heading, c metres to its right.
function onRunway(f, x, z) {
  const dx = x - f.x, dz = z - f.z, ax = dirX(f.hdg), az = dirZ(f.hdg);
  return { a: dx * ax + dz * az, c: dx * -az + dz * ax };
}
function approachPoint(f) { return { x: f.x - dirX(f.hdg) * APPROACH, z: f.z - dirZ(f.hdg) * APPROACH }; }

// ---- The ground ----
// Rolling forest land with lakes (below 0 m), a big lake round Saarikenttä, fells round
// Tunturikenttä. Each runway is flat at its height, and the land under each route's approach
// and climb-out stays low, so every route can be flown.
function natural(x, z) {
  let h = 22 + 14 * Math.sin(x / 900) * Math.cos(z / 1100) + 9 * Math.sin((x + z) / 530) + 5 * Math.sin(x / 210 + 1.3) * Math.sin(z / 260)
    + 3 * Math.sin(x / 97 - z / 131);
  const dl = Math.hypot(x - 5700, z + 11800);         // the big lake round Saarikenttä
  h -= 46 * smooth(1 - dl / 2600);
  const df = Math.hypot(x - 10500, z - 8800);       // the fells
  h += 300 * Math.exp(-((df / 3200) ** 2)) * (0.75 + 0.25 * Math.sin(x / 420) * Math.cos(z / 380));
  return h;
}
function heightAt(x, z) {
  let h = natural(x, z);
  for (let i = 0; i < FIELDS.length; i++) {
    const f = FIELDS[i], r = onRunway(f, x, z);
    // Approach (before the threshold) and climb-out (past the end): the land stays under a slope.
    const out = r.a < 0 ? -r.a : r.a > f.len ? r.a - f.len : 0;
    const halfW = 350 + out * 0.08;
    if (out < 7000 && Math.abs(r.c) < halfW + 300) {
      const cap = f.elev - 4 + out * (r.a < 0 ? 0.03 : 0.045);
      const k = smooth((halfW + 300 - Math.abs(r.c)) / 300) * smooth((7000 - out) / 800);
      if (h > cap) h = lerp(h, cap, k);
    }
    // The airfield itself: flat round the runway, blending into the land over 500 m.
    const da = Math.max(0, -r.a - 60, r.a - f.len - 60), dc = Math.max(0, Math.abs(r.c) - 90);
    const d = Math.hypot(da, dc);
    if (d < 500) h = lerp(h, f.elev, smooth(1 - d / 500));
  }
  return h;
}
const groundAt = (x, z) => Math.max(WATER, heightAt(x, z));
const isWater = (x, z) => heightAt(x, z) < WATER;
// Which runway (index) a point is on, or -1.
function runwayAt(x, z, margin) {
  for (let i = 0; i < FIELDS.length; i++) {
    const f = FIELDS[i], r = onRunway(f, x, z);
    if (r.a >= -margin && r.a <= f.len + margin && Math.abs(r.c) <= f.wid / 2 - 1.2 + margin) return i;
  }
  return -1;
}
// Trees stand on a 55 m grid where the land is dry and away from runways and approaches; nothing hits them.
function treeAt(i, j) {
  const r = hash2(i, j);
  if (r > 0.62) return null;
  const x = (i + hash2(j, i) - 0.5) * 55, z = (j + hash2(i + 7, j - 3) - 0.5) * 55;
  const h = heightAt(x, z);
  if (h < 2.5 || h > 330) return null;
  for (const f of FIELDS) {
    const q = onRunway(f, x, z);
    if (q.a > -1500 && q.a < f.len + 300 && Math.abs(q.c) < 160 + Math.max(0, -q.a) * 0.08) return null;
    if (q.a > -400 && q.a < f.len + 400 && Math.abs(q.c) < 420) return null;
  }
  return { x, z, y: h, s: 0.7 + hash2(i * 3, j * 5) * 0.7, birch: hash2(i + 1, j + 2) < 0.25 };
}

// ---- The plane's state ----
function newPlane(route) {
  const f = FIELDS[route.from];
  return {
    x: f.x + dirX(f.hdg) * 40, z: f.z + dirZ(f.hdg) * 40, y: f.elev,
    hdg: f.hdg, pit: 0, bank: 0, gam: 0, v: 0, aoa: 0,
    thr: 0, flaps: 1, gear: true, brake: false, sx: 0, sy: 0,
    ground: true, airborne: false, stall: false, t: 0,
    touch: null,       // the touchdown on the target runway: { sink, c, a, bank }
    over: null,        // the end: { ok, why, ... }
    maxAgl: 0, events: [],
  };
}
// The retry from the approach: 5 km out on the target runway's line, on the glide path.
function approachPlane(route) {
  const f = FIELDS[route.to], d = 5000;
  const p = newPlane(route);
  Object.assign(p, {
    x: f.x - dirX(f.hdg) * d, z: f.z - dirZ(f.hdg) * d, y: f.elev + (d + aimAt(f)) * Math.tan(GLIDE),
    hdg: f.hdg, v: 42, thr: 0.35, flaps: 0, gear: false, ground: false, airborne: true,
  });
  p.gam = -GLIDE * 0.5; p.pit = p.gam + trimAoa(p);
  return p;
}
// The angle of attack that holds the plane up at its speed.
function trimAoa(p) {
  const q = 0.5 * PLANE.rho * p.v * p.v * PLANE.S;
  return clamp((PLANE.m * G / q - PLANE.cl0 - PLANE.flapCl[p.flaps]) / PLANE.cla, -0.1, PLANE.aoaStall - 0.02);
}

function windOf(route, t) {
  const w = route && route.wind;
  if (!w) return { x: 0, z: 0 };
  const v = w.v + w.gust * (0.6 * Math.sin(t * 0.37) + 0.4 * Math.sin(t * 1.13 + 1));
  return { x: dirX(w.to) * v, z: dirZ(w.to) * v };
}

function forces(p) {
  const q = 0.5 * PLANE.rho * p.v * p.v * PLANE.S;
  let cl = PLANE.cl0 + PLANE.cla * p.aoa + PLANE.flapCl[p.flaps];
  const clMax = PLANE.cl0 + PLANE.cla * PLANE.aoaStall + PLANE.flapCl[p.flaps];
  if (p.aoa > PLANE.aoaStall) cl = clMax - (p.aoa - PLANE.aoaStall) * 6;
  if (p.aoa < -0.25) cl = PLANE.cl0 + PLANE.cla * -0.25 + PLANE.flapCl[p.flaps];
  const cd = PLANE.cd0 + PLANE.k * cl * cl + PLANE.flapCd[p.flaps] + (p.gear ? PLANE.gearCd : 0);
  const T = PLANE.thrust * p.thr * Math.max(0, 1 - p.v / PLANE.vMaxThrust);
  return { L: q * cl, D: q * cd, T };
}

// One step of the flight. `route` gives the wind and the target runway.
function step(p, dt, route) {
  if (p.over && p.over.stopped) return;
  p.t += dt;
  const m = PLANE.m;
  if (p.ground) groundStep(p, dt, route, m);
  else airStep(p, dt, route, m);
  p.maxAgl = Math.max(p.maxAgl, p.y - groundAt(p.x, p.z));
}

function airStep(p, dt, route, m) {
  // The stick: pitch and bank rates; let go and the wings slowly level.
  p.pit += p.sy * PLANE.pitchRate * dt;
  if (Math.abs(p.sx) > 0.05) p.bank += p.sx * PLANE.bankRate * dt;
  else p.bank -= Math.sign(p.bank) * Math.min(Math.abs(p.bank), 0.12 * dt);
  p.bank = clamp(p.bank, -PLANE.maxBank, PLANE.maxBank);
  p.aoa = p.pit - p.gam;
  // A stall: the nose falls by itself until the wing flies again.
  p.stall = p.aoa > PLANE.aoaStall;
  if (p.stall) p.pit -= (0.5 + (p.aoa - PLANE.aoaStall) * 4) * dt;
  // The nose cannot be held far from where the plane goes.
  p.pit = clamp(p.pit, p.gam - 0.25, p.gam + 0.45);
  p.pit = clamp(p.pit, -40 * DEG, 40 * DEG);
  p.aoa = p.pit - p.gam;
  const { L, D, T } = forces(p);
  const v = Math.max(p.v, 3);
  p.v += ((T * Math.cos(p.aoa) - D) / m - G * Math.sin(p.gam)) * dt;
  p.v = Math.max(0.5, p.v);
  p.gam += ((L * Math.cos(p.bank) + T * Math.sin(p.aoa) - m * G * Math.cos(p.gam)) / (m * v)) * dt;
  p.gam = clamp(p.gam, -1.3, 1.3);
  p.hdg = wrapAngle(p.hdg + (L * Math.sin(p.bank)) / (m * v * Math.max(0.3, Math.cos(p.gam))) * dt);
  const w = windOf(route, p.t), hv = p.v * Math.cos(p.gam);
  p.x += (dirX(p.hdg) * hv + w.x) * dt;
  p.z += (dirZ(p.hdg) * hv + w.z) * dt;
  p.y += p.v * Math.sin(p.gam) * dt;
  const gnd = groundAt(p.x, p.z);
  if (p.y - gnd > 3) p.airborne = true;
  if (p.y <= gnd) touchDown(p, gnd, route);
}

// The wheels meet the ground: a landing, a bounce along a runway, or the end of the flight.
function touchDown(p, gnd, route) {
  const sink = -p.v * Math.sin(p.gam), rw = runwayAt(p.x, p.z, 0);
  p.y = gnd;
  let why = null;
  if (isWater(p.x, p.z)) why = 'Järveen';
  else if (rw < 0) why = p.stall ? 'Sakkaus maahan' : 'Ohi kiitoradan';
  else if (!p.gear) why = 'Telineet ylhäällä';
  else if (p.stall && sink > 3) why = 'Sakkaus maahan';
  else if (sink > 3) why = 'Liian kova lasku';
  else if (Math.abs(p.bank) > 10 * DEG) why = 'Siipi maahan';
  else if (p.pit < -5 * DEG) why = 'Nokka edellä maahan';
  if (why) { crash(p, why); return; }
  // Rolling: the wheels follow the runway, a crab angle is straightened out.
  p.ground = true; p.gam = 0; p.bank = 0; p.stall = false;
  p.events.push('touch');
  const f = FIELDS[route.to];
  if (rw >= 0) { const fh = FIELDS[rw].hdg, off = wrapAngle(p.hdg - fh), back = Math.abs(off) > Math.PI / 2;
    const want = back ? wrapAngle(fh + Math.PI) : fh, left = wrapAngle(p.hdg - want);
    if (Math.abs(left) < 20 * DEG) p.hdg = want; }
  if (rw === route.to && p.airborne && !p.touch) {
    const r = onRunway(f, p.x, p.z);
    p.touch = { sink, c: r.c, a: r.a };
  }
}
function crash(p, why) {
  p.over = { ok: false, why, stopped: true };
  p.v = 0; p.thr = 0;
  p.events.push('crash');
}

function groundStep(p, dt, route, m) {
  // Pitch on the wheels: only with speed the nose wheel lifts; with the stick let go it settles.
  const want = p.v > PLANE.vRotate ? clamp(p.sy, 0, 1) * 0.22 : 0;
  p.pit += clamp(want - p.pit, -0.3 * dt, 0.35 * dt);
  p.pit = Math.max(0, p.pit);
  p.gam = 0; p.aoa = p.pit; p.bank = 0; p.stall = false;
  const { L, D, T } = forces(p);
  const normal = Math.max(0, m * G - L);
  let a = (T - D) / m - PLANE.roll * normal / m;
  if (p.brake) a -= PLANE.brake * (normal / (m * G));
  p.v = Math.max(0, p.v + a * dt);
  p.hdg = wrapAngle(p.hdg + p.sx * 0.35 * Math.min(1, p.v / 8) * dt);
  p.x += dirX(p.hdg) * p.v * dt;
  p.z += dirZ(p.hdg) * p.v * dt;
  const gnd = groundAt(p.x, p.z);
  p.y = gnd;
  // Lift-off: the wing carries the plane.
  if (L > m * G * 1.01 && p.v > 15 && (!p.touch || p.sy > 0.1)) {
    p.ground = false; p.gam = 0.02; p.y = gnd + 0.05;
    if (p.touch && !p.over) p.touch = null;   // a touch-and-go: the next touchdown counts
    p.events.push('liftoff');
    return;
  }
  const rw = runwayAt(p.x, p.z, 25);
  if (rw < 0 || isWater(p.x, p.z)) {
    // Off the runway on the wheels.
    if (p.touch) { finishLanding(p, route, false); return; }
    if (p.v > 6) { crash(p, 'Ulos kiitoradalta'); return; }
  }
  if (p.v < 0.5 && (p.thr < 0.05 || p.touch)) {
    p.v = 0;
    if (p.touch) finishLanding(p, route, true);
    else if (p.airborne && !p.over) {
      p.over = { ok: false, why: rw === route.from ? 'Palasit lähtökentälle' : 'Pysähdyit väärälle kentälle', stopped: true };
      p.events.push('wrong');
    }
  }
}

function finishLanding(p, route, onRunwayStop) {
  const f = FIELDS[route.to];
  const sc = landingScore(p.touch, f, onRunwayStop);
  p.over = { ok: true, stopped: true, ...sc };
  p.v = 0; p.thr = 0;
  p.events.push('landed');
}

// Points for a landing: softness, the centre line, the touchdown point, stopping on the runway.
function landingScore(t, f, stopped) {
  const soft = Math.round(400 * clamp((3 - t.sink) / 2.5, 0, 1));
  const line = Math.round(300 * clamp(1 - Math.abs(t.c) / (f.wid / 2), 0, 1));
  const zoneLo = f.len < 700 ? 60 : 150, zoneHi = f.len < 700 ? 180 : 300;
  const off = t.a < zoneLo ? zoneLo - t.a : t.a > zoneHi ? t.a - zoneHi : 0;
  const spot = Math.round(200 * clamp(1 - off / (f.len * 0.4), 0, 1));
  const stop = stopped ? 100 : 0;
  const points = soft + line + spot + stop;
  const stars = points >= 850 ? 3 : points >= 600 ? 2 : 1;
  return { soft, line, spot, stop, points, stars, sink: t.sink };
}

// ---- What the screen tells the pilot ----
// The way to fly: to the approach point first, then down the runway's line to the threshold.
function guidance(p, route) {
  const f = FIELDS[route.to], r = onRunway(f, p.x, p.z), ap = approachPoint(f);
  const lined = r.a > -APPROACH - 2500 && r.a < f.len && Math.abs(r.c) < 250 + Math.max(0, -r.a) * 0.12
    && Math.abs(wrapAngle(p.hdg - f.hdg)) < 60 * DEG;
  const tx = lined ? f.x : ap.x, tz = lined ? f.z : ap.z;
  const dist = Math.hypot(tx - p.x, tz - p.z);
  const brg = Math.atan2(tx - p.x, -(tz - p.z));
  return {
    lined, dist, rel: wrapAngle(brg - p.hdg), runwayDist: Math.max(0, -r.a), a: r.a, c: r.c,
    // The glide path's height here, above the runway.
    glideH: f.elev + Math.max(0, aimAt(f) - r.a) * Math.tan(GLIDE),
    out: p.x < BOUNDS.x0 || p.x > BOUNDS.x1 || p.z < BOUNDS.z0 || p.z > BOUNDS.z1,
    lost: p.x < BOUNDS.x0 - 6000 || p.x > BOUNDS.x1 + 6000 || p.z < BOUNDS.z0 - 6000 || p.z > BOUNDS.z1 + 6000,
  };
}
// The four lights beside a runway (PAPI): each is white when the plane is above its angle.
const PAPI_ANGLES = [3.5, 3.17, 2.83, 2.5].map(a => a * DEG);
// They stand at the aim point, inside the touchdown zone `landingScore` rewards; the glide path meets the ground there.
const aimAt = f => f.len < 700 ? 110 : 220;
function papi(p, f) {
  const r = onRunway(f, p.x, p.z), d = aimAt(f) - r.a;
  if (d <= 0) return null;
  const ang = Math.atan2(p.y - f.elev, d);
  return PAPI_ANGLES.map(a => ang > a);
}
