'use strict';
// SI units, Earth-centred inertial frame: +x east at launch, +y up.
// Angles clockwise from +y. A spherical, rotating Earth; no lift or other bodies.
const EARTH = 6371000, MU = 3.986004418e14, G0 = 9.80665;
const SPIN = 7.2921159e-5, STATION_R = EARTH + 400000;
const STATION_N = Math.sqrt(MU / STATION_R ** 3);
const STAGES = [
  { dry: 35000, fuel: 295000, thrust: 7000000, isp: 300, length: 52 },
  { dry: 29000, fuel: 140000, thrust: 1900000, isp: 450, length: 16 }
];
const RCS_FULL = 1000, RCS_FORCE = 2200, RCS_ISP = 230;
const SAVE_KEY = 'ai-pelit:raketti:lento', RECORD_KEY = 'ai-pelit:raketti:saavutukset';
const TAU = Math.PI * 2;
var ship = null, held = { turn: 0, forward: 0, side: 0 };
var warp = 1, paused = true, view = 'flight', achieved = { orbit: false, dock: false };
function wrap(a) { return Math.atan2(Math.sin(a), Math.cos(a)); }
function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
function mass(s = ship) {
  return STAGES[1].dry + s.fuel[1] + s.rcs +
    (s.stage === 0 ? STAGES[0].dry + s.fuel[0] : 0);
}
function freshFlight(kind = 'launch') {
  const s = { x: 0, y: EARTH + 26, vx: SPIN * (EARTH + 26), vy: 0,
    angle: 0, omega: SPIN, fuel: [295000, 140000], rcs: RCS_FULL, stage: 0,
    throttle: 0, t: 0, stationPhase: -0.20336, phase: 'pad', practice: kind !== 'launch',
    orbited: false, reason: '', maxQ: 0 };
  if (kind !== 'launch') {
    s.stage = 1; s.fuel = [0, 18000]; s.phase = 'flight';
    if (kind === 'orbit') {
      s.y = EARTH + 250000; s.vx = Math.sqrt(MU / s.y); s.angle = Math.PI / 2;
      s.omega = s.vx / s.y; s.stationPhase = 0.08; s.orbited = true;
    } else {
      s.stationPhase = 0; const p = station(s);
      // Start 80 m behind the port, on its approach axis, with matched velocity.
      s.x = p.px - 80; s.y = p.py; s.vx = p.pvx; s.vy = p.pvy;
      s.angle = Math.PI / 2; s.omega = STATION_N; s.orbited = true;
    }
  }
  return s;
}
function station(s = ship) {
  const a = s.stationPhase + STATION_N * s.t;
  const rx = Math.sin(a), ry = Math.cos(a), tx = Math.cos(a), ty = -Math.sin(a);
  const x = STATION_R * rx, y = STATION_R * ry;
  const vx = STATION_R * STATION_N * tx, vy = STATION_R * STATION_N * ty;
  return { x, y, vx, vy, rx, ry, tx, ty, angle: a + Math.PI / 2,
    px: x - 45 * tx, py: y - 45 * ty,
    pvx: vx + 45 * STATION_N * rx, pvy: vy + 45 * STATION_N * ry };
}
function orbit(s = ship) {
  const r = Math.hypot(s.x, s.y), v2 = s.vx ** 2 + s.vy ** 2;
  const h = s.x * s.vy - s.y * s.vx;
  const energy = v2 / 2 - MU / r;
  const ecc = Math.sqrt(Math.max(0, 1 + 2 * energy * h * h / (MU * MU)));
  const a = energy < 0 ? -MU / (2 * energy) : Infinity;
  const peri = (h * h / MU) / (1 + ecc) - EARTH;
  const apo = Number.isFinite(a) ? a * (1 + ecc) - EARTH : Infinity;
  const vr = (s.x * s.vx + s.y * s.vy) / r;
  const vt = (s.y * s.vx - s.x * s.vy) / r;
  let toApo = Infinity;
  if (a > 0 && Number.isFinite(a) && ecc > 1e-6 && ecc < 1) {
    const cosE = clamp((1 - r / a) / ecc, -1, 1);
    let E = Math.acos(cosE); if (vr < 0) E = TAU - E;
    toApo = ((Math.PI - (E - ecc * Math.sin(E)) + TAU) % TAU) / Math.sqrt(MU / a ** 3);
  }
  return { r, altitude: r - EARTH, vr, vt, speed: Math.sqrt(v2), peri, apo, a, ecc, h, toApo };
}
function approach(s = ship) {
  const p = station(s), length = STAGES[s.stage].length / 2;
  const nx = s.x + Math.sin(s.angle) * length;
  const ny = s.y + Math.cos(s.angle) * length;
  const nvx = s.vx + Math.cos(s.angle) * length * s.omega;
  const nvy = s.vy - Math.sin(s.angle) * length * s.omega;
  const dx = nx - p.px, dy = ny - p.py;
  const dvx = nvx - p.pvx, dvy = nvy - p.pvy;
  return { p, range: Math.hypot(dx, dy), speed: Math.hypot(dvx, dvy),
    along: dx * p.tx + dy * p.ty, cross: dx * p.rx + dy * p.ry,
    closing: -(dvx * p.tx + dvy * p.ty), lateral: dvx * p.rx + dvy * p.ry,
    alignment: wrap(s.angle - p.angle), spin: s.omega - STATION_N };
}
function atmosphere(x, y, vx, vy) {
  const altitude = Math.hypot(x, y) - EARTH;
  // Exponential scale-height model, truncated above 150 km. Air co-rotates.
  const rho = altitude < 150000 ? 1.225 * Math.exp(-Math.max(0, altitude) / 8500) : 0;
  const ax = vx - SPIN * y, ay = vy + SPIN * x;
  return { rho, ax, ay, speed: Math.hypot(ax, ay), q: 0.5 * rho * (ax * ax + ay * ay) };
}
function canWarp() {
  if (!ship || ship.phase !== 'flight') return false;
  return Math.hypot(ship.x, ship.y) > EARTH + 150000 && ship.throttle === 0 &&
    !held.turn && !held.forward && !held.side && Math.abs(ship.omega) < 0.01 && approach().range > 5000;
}
function clearHeld() { held.turn = held.forward = held.side = 0; }
function endFlight(reason, success = false) {
  ship.phase = success ? 'docked' : 'crashed'; ship.reason = reason;
  ship.throttle = 0; warp = 1; clearHeld();
  if (success && !ship.practice) { achieved.dock = true; saveRecords(); }
  saveFlight();
}
function saveRecords() {
  try { localStorage.setItem(RECORD_KEY, JSON.stringify(achieved)); } catch (_) { /* Private browsing can deny storage. */ }
}
function readRecords() {
  try { const a = JSON.parse(localStorage.getItem(RECORD_KEY));
    if (a) achieved = { orbit: a.orbit === true, dock: a.dock === true };
  } catch (_) { /* Keep valid defaults. */ }
}
function saveFlight() {
  if (!ship) return;
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(ship)); } catch (_) { /* Flight still works without storage. */ }
}
function validFlight(s) {
  if (!s || !['pad', 'flight', 'docked', 'crashed'].includes(s.phase) || ![0, 1].includes(s.stage)) return false;
  if (!['x', 'y', 'vx', 'vy', 'angle', 'omega', 'rcs', 'throttle', 't', 'stationPhase', 'maxQ'].every(k => Number.isFinite(s[k]))) return false;
  if (!Array.isArray(s.fuel) || s.fuel.length !== 2 || !s.fuel.every((f, i) => Number.isFinite(f) && f >= 0 && f <= STAGES[i].fuel)) return false;
  return Math.hypot(s.x, s.y) >= EARTH - 100 && Math.hypot(s.x, s.y) < 1e10 &&
    Math.hypot(s.vx, s.vy) < 100000 && Math.abs(s.omega) < 10 && Math.abs(s.angle) <= Math.PI + 0.001 &&
    s.rcs >= 0 && s.rcs <= RCS_FULL && s.throttle >= 0 && s.throttle <= 1 && s.t >= 0 && s.t < 1e9 &&
    typeof s.practice === 'boolean' && typeof s.orbited === 'boolean' && typeof s.reason === 'string' &&
    s.reason.length < 300 && Math.abs(s.stationPhase) < TAU && s.maxQ >= 0 &&
    (s.stage !== 1 || s.fuel[0] === 0) &&
    (s.phase !== 'pad' || (s.stage === 0 && s.t === 0));
}
function loadFlight() {
  try { const s = JSON.parse(localStorage.getItem(SAVE_KEY)); return validFlight(s) ? s : null; }
  catch (_) { return null; }
}
function stageRocket() {
  if (!ship || paused || ship.phase !== 'flight' || ship.stage !== 0) return false;
  if (orbit().altitude < 1000) return false;
  ship.fuel[0] = 0; ship.stage = 1; ship.throttle = 0; warp = 1;
  saveFlight(); return true;
}
function acceleration(x, y, vx, vy, fx, fy, m, s) {
  const r = Math.hypot(x, y), air = atmosphere(x, y, vx, vy);
  const length = STAGES[s.stage].length;
  const relative = wrap(s.angle - Math.atan2(air.ax, air.ay));
  const area = 12.6 + length * 4 * Math.abs(Math.sin(relative));
  const drag = 0.5 * 0.3 * area * air.rho * air.speed;
  return { x: -MU * x / r ** 3 + (fx - drag * air.ax) / m,
    y: -MU * y / r ** 3 + (fy - drag * air.ay) / m };
}
// Segment/rectangle clipping for the full vehicle and its swept endpoints.
function segmentBox(ax, ay, bx, by, cx, cy, hx, hy) {
  let lo = 0, hi = 1;
  for (const [a, b, c, half] of [[ax, bx, cx, hx], [ay, by, cy, hy]]) {
    const delta = b - a;
    if (Math.abs(delta) < 1e-12) { if (Math.abs(a - c) > half) return false; continue; }
    const first = (c - half - a) / delta, last = (c + half - a) / delta;
    lo = Math.max(lo, Math.min(first, last)); hi = Math.min(hi, Math.max(first, last));
    if (lo > hi) return false;
  }
  return true;
}
function vehiclePoints(s, p) {
  const half = STAGES[s.stage].length / 2;
  return [-half, 0, half].map(offset => {
    const dx = s.x + Math.sin(s.angle) * offset - p.x;
    const dy = s.y + Math.cos(s.angle) * offset - p.y;
    return { x: dx * p.tx + dy * p.ty, y: dx * p.rx + dy * p.ry };
  });
}
function stationContact(before, after) {
  // Inflate solids by the 2 m body radius. The port has its own narrow capture ring.
  const boxes = [[0, 0, 37, 10], [-15, 0, 7, 54], [15, 0, 7, 54], [-45, 0, 1, 5]];
  return boxes.some(([x, y, w, h]) => {
    if (segmentBox(after[0].x, after[0].y, after[2].x, after[2].y, x, y, w, h)) return true;
    return before.some((a, i) => segmentBox(a.x, a.y, after[i].x, after[i].y, x, y, w, h));
  });
}
function tick(dt) {
  const s = ship;
  const before = orbit(s), near = approach(s);
  if (s.phase !== 'flight') return;
  const oldPoints = vehiclePoints(s, near.p);
  const st = STAGES[s.stage], m0 = mass(s);
  let thrust = st.thrust * s.throttle;
  // First-stage exhaust gains specific impulse as ambient pressure falls.
  const isp = st.isp + (s.stage === 0 ? 35 * (1 - Math.exp(-Math.max(0, before.altitude) / 8500)) : 0);
  const burn = Math.min(s.fuel[s.stage], thrust / (isp * G0) * dt);
  thrust = burn * isp * G0 / dt;
  s.fuel[s.stage] = Math.max(0, s.fuel[s.stage] - burn);
  if (!s.fuel[s.stage]) s.throttle = 0;
  const inertia = m0 * st.length ** 2 / 12;
  const command = Math.abs(held.turn) + Math.abs(held.forward) + Math.abs(held.side);
  const requestedRcs = command * RCS_FORCE / (RCS_ISP * G0) * dt;
  const rcsUse = Math.min(s.rcs, requestedRcs);
  const rcsScale = requestedRcs ? rcsUse / requestedRcs : 0;
  s.rcs = Math.max(0, s.rcs - rcsUse);
  // Engine gimbal plus a manual RCS couple. No attitude hold or damping in vacuum.
  const torque = held.turn * (thrust * st.length * 0.35 * Math.sin(0.7 * Math.PI / 180) +
    RCS_FORCE * st.length * 0.4 * rcsScale);
  let alpha = torque / inertia;
  const air = atmosphere(s.x, s.y, s.vx, s.vy);
  // Passive aerodynamic weathercock stability; disappears with air density.
  if (air.speed > 5 && air.rho > 0) {
    const slip = wrap(Math.atan2(air.ax, air.ay) - s.angle);
    alpha += (air.q * 1.2 * st.length * Math.sin(slip) - air.q * st.length * 4 * s.omega) / inertia;
  }
  const midAngle = s.angle + s.omega * dt / 2 + alpha * dt * dt / 8;
  const forward = thrust + held.forward * RCS_FORCE * rcsScale;
  const side = held.side * RCS_FORCE * rcsScale;
  const fx = Math.sin(midAngle) * forward + Math.cos(midAngle) * side;
  const fy = Math.cos(midAngle) * forward - Math.sin(midAngle) * side;
  const m = (m0 + mass(s)) / 2;
  const a = acceleration(s.x, s.y, s.vx, s.vy, fx, fy, m, s);
  // Velocity Verlet: substeps stay small even at 100x, never skip the flight.
  const vxh = s.vx + a.x * dt / 2, vyh = s.vy + a.y * dt / 2;
  s.x += vxh * dt; s.y += vyh * dt;
  const b = acceleration(s.x, s.y, vxh, vyh, fx, fy, m, s);
  s.vx = vxh + b.x * dt / 2; s.vy = vyh + b.y * dt / 2;
  s.angle = wrap(s.angle + s.omega * dt + alpha * dt * dt / 2);
  s.omega += alpha * dt; s.t += dt; s.maxQ = Math.max(s.maxQ, air.q);
  const o = orbit(s);
  if (o.peri > 150000 && o.apo < 2000000 && !s.orbited) {
    s.orbited = true;
    if (!s.practice) { achieved.orbit = true; saveRecords(); }
    saveFlight();
  }
  if (o.altitude < st.length / 2) {
    endFlight('Raketti osui maahan. Pidä alussa teho täysillä ja nokka lähes pystyssä.'); return;
  }
  if (air.q > 130000) {
    endFlight('Ilmanpaineen kuormitus rikkoi raketin. Vähennä tehoa tiheässä ilmakehässä.'); return;
  }
  if (air.q * air.speed > 7e7) {
    endFlight('Alus kuumeni liikaa paluussa ilmakehään. Tällä aluksella ei ole lämpökilpeä.'); return;
  }
  const d = approach(s), p = d.p;
  // A capture ring, not a magnet: position, relative velocity, nose and spin all matter.
  if (s.stage === 1 && d.range < 1.2 && d.speed <= 0.25 &&
      Math.abs(d.alignment) <= 5 * Math.PI / 180 && Math.abs(d.spin) <= 0.01 && d.along <= 0.5) {
    endFlight('Telakointi onnistui. Lukot kiinni — tervetuloa asemalle!', true); return;
  }
  if (stationContact(oldPoints, vehiclePoints(s, p))) {
    endFlight('Törmäys asemaan. Kohdista nokka porttiin ja hidasta alle 0,25 m/s.');
  }
  if (before.altitude > 0 && near.range < 5000) warp = 1;
}
function step(seconds) {
  if (!ship || paused || ship.phase !== 'flight' || !Number.isFinite(seconds) || seconds <= 0) return;
  let left = seconds;
  while (left > 1e-9 && ship.phase === 'flight') {
    const limit = approach().range < 1000 || ship.throttle > 0 || held.turn || held.forward || held.side ? 0.02 : 0.25;
    const dt = Math.min(left, limit); tick(dt); left -= dt;
  }
}

// Consume wall time a substep at a time, so a warp cancellation takes effect
// immediately rather than after the rest of an already accelerated frame.
function advanceFlight(realSeconds) {
  if (!Number.isFinite(realSeconds) || realSeconds <= 0 || paused) return;
  let left = realSeconds;
  while (left > 1e-9 && ship && ship.phase === 'flight') {
    if (warp !== 1 && !canWarp()) warp = 1;
    const rate = warp;
    const simulated = Math.min(left * rate, 0.25);
    step(simulated);
    left -= simulated / rate;
  }
}
