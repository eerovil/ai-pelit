'use strict';
// Raketti v3 (#548): a small, friendly Earth–Moon system instead of v2's real one.
// SI units in an Earth-centred frame: +x east of the launch pad, +y up from it.
// Angles run clockwise from +y. Earth stays put; the Moon and the rock circle it.
const G0 = 9.80665, TAU = Math.PI * 2;
// Every body is one entry here, so a later version can add the Sun and Mars (owner's wish, #548).
// near5 / near100: within that height above the surface time runs at most ×5 / ×100.
const BODIES = [
  { id: 'earth', name: 'Maa', radius: 500000, mu: 9.8 * 500000 ** 2,
    air: { top: 40000, rho: 1.2, scale: 4500 }, near5: 20000, near100: 300000 },
  { id: 'moon', name: 'Kuu', radius: 80000, mu: 1.4 * 80000 ** 2,
    orbit: { r: 5000000, phase: 2.75 }, sphere: 530000, near5: 5000, near100: 100000 },
  { id: 'rock', name: 'Pikkukivi', radius: 3000, mu: 0.03 * 3000 ** 2,
    orbit: { r: 2000000, phase: 2.2 }, sphere: 30000, near5: 2000, near100: 30000 }
];
const EARTH = BODIES[0], MOON = BODIES[1], ROCK = BODIES[2];
const EARTH_R = EARTH.radius;
for (const b of BODIES) if (b.orbit) b.orbit.n = Math.sqrt(EARTH.mu / b.orbit.r ** 3);
const STATION_R = EARTH_R + 100000;
const STATION_N = Math.sqrt(EARTH.mu / STATION_R ** 3);
// One stage. The engine never pushes harder than 2 g, so a light, nearly empty ship
// is as easy to fly as a full one; full tanks hold about 7.5 km/s.
const SHIP = { dry: 4000, fuel: 26000, thrust: 540000, isp: 380, length: 12, accCap: 20,
  rcsAcc: 0.3, rcsDv: 300, dragArea: 5, chuteArea: 3000 };
const VE = SHIP.isp * G0;
// Landing limits (D9): down, sideways, total speed, tilt.
const LANDING = {
  earth: { down: 3, side: 2, tilt: 15, chute: 10 },
  moon: { down: 3, side: 2, tilt: 15 },
  rock: { speed: 1, tilt: 25 }
};
const DOCK = { range: 3, speed: 0.5, align: 10 };
const CHUTE = { height: 20000, speed: 400 };
const TURN_SLOW = 15 * Math.PI / 180, TURN_FAST = 60 * Math.PI / 180, POINT_RATE = 90 * Math.PI / 180;
const SAVE_KEY = 'ai-pelit:raketti:matka', STARS_KEY = 'ai-pelit:raketti:tahdet';
var ship = null, held = { turn: 0, forward: 0, side: 0, turnFor: 0 };
var warp = 1, paused = true, view = 'flight', stars = {};
function wrap(a) { return Math.atan2(Math.sin(a), Math.cos(a)); }
function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
function body(id) { return BODIES.find(b => b.id === id); }
function mass(s = ship) { return SHIP.dry + s.fuel; }
function deltaV(s = ship) { return VE * Math.log(mass(s) / SHIP.dry); }
function fuelForDeltaV(dv) { return SHIP.dry * (Math.exp(dv / VE) - 1); }
function bodyAt(b, t) {
  if (!b.orbit) return { x: 0, y: 0, vx: 0, vy: 0 };
  const a = b.orbit.phase + b.orbit.n * t, r = b.orbit.r, v = r * b.orbit.n;
  return { x: r * Math.sin(a), y: r * Math.cos(a), vx: v * Math.cos(a), vy: -v * Math.sin(a), a };
}
function freshFlight(trip = 'kiertorata', from = 'pad') {
  const s = { x: 0, y: EARTH_R + SHIP.length / 2, vx: 0, vy: 0, angle: 0, omega: 0,
    fuel: SHIP.fuel, rcs: SHIP.rcsDv, throttle: 0, t: 0, real: 0, trip, from,
    stationPhase: -0.12, phase: 'flight', landedOn: 'earth', landAngle: 0, chute: 'packed',
    point: null, visited: [], touch: null, reason: '', note: '', stars: 0 };
  if (from === 'orbit') {
    // A ready, round 80 km orbit with the fuel a typical launch leaves (D8).
    const r = EARTH_R + 80000, moon = bodyAt(MOON, 0), at = wrap(moon.a - 150 * Math.PI / 180);
    const v = Math.sqrt(EARTH.mu / r);
    Object.assign(s, { x: r * Math.sin(at), y: r * Math.cos(at), vx: v * Math.cos(at), vy: -v * Math.sin(at),
      angle: wrap(at + Math.PI / 2), landedOn: null, fuel: fuelForDeltaV(4300),
      stationPhase: wrap(at + 30 * Math.PI / 180) });
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
// The body whose numbers the player reads: the Moon or the rock once close, else Earth.
function refBody(s = ship) {
  for (const b of BODIES) {
    if (!b.sphere) continue;
    const p = bodyAt(b, s.t);
    if (Math.hypot(s.x - p.x, s.y - p.y) < b.sphere) return b;
  }
  return EARTH;
}
function relative(b, s = ship) {
  const p = bodyAt(b, s.t);
  return { x: s.x - p.x, y: s.y - p.y, vx: s.vx - p.vx, vy: s.vy - p.vy };
}
// Osculating two-body orbit around one body.
function orbitAround(b, s = ship) {
  const q = relative(b, s), mu = b.mu;
  const r = Math.hypot(q.x, q.y), v2 = q.vx ** 2 + q.vy ** 2;
  const h = q.x * q.vy - q.y * q.vx, energy = v2 / 2 - mu / r;
  const ecc = Math.sqrt(Math.max(0, 1 + 2 * energy * h * h / (mu * mu)));
  const a = energy < 0 ? -mu / (2 * energy) : Infinity;
  const peri = (h * h / mu) / (1 + ecc) - b.radius;
  const apo = Number.isFinite(a) ? a * (1 + ecc) - b.radius : Infinity;
  const vr = (q.x * q.vx + q.y * q.vy) / r, vt = (q.y * q.vx - q.x * q.vy) / r;
  let toApo = Infinity;
  if (a > 0 && Number.isFinite(a) && ecc > 1e-6 && ecc < 1) {
    const cosE = clamp((1 - r / a) / ecc, -1, 1);
    let E = Math.acos(cosE); if (vr < 0) E = TAU - E;
    toApo = ((Math.PI - (E - ecc * Math.sin(E)) + TAU) % TAU) / Math.sqrt(mu / a ** 3);
  }
  return { body: b, r, altitude: r - b.radius, vr, vt, speed: Math.sqrt(v2), peri, apo, a, ecc, h, energy, toApo };
}
function orbit(s = ship) { return orbitAround(refBody(s), s); }
function approach(s = ship) {
  const p = station(s), length = SHIP.length / 2;
  const nx = s.x + Math.sin(s.angle) * length, ny = s.y + Math.cos(s.angle) * length;
  const nvx = s.vx + Math.cos(s.angle) * length * s.omega, nvy = s.vy - Math.sin(s.angle) * length * s.omega;
  const dx = nx - p.px, dy = ny - p.py, dvx = nvx - p.pvx, dvy = nvy - p.pvy;
  return { p, range: Math.hypot(dx, dy), speed: Math.hypot(dvx, dvy),
    along: dx * p.tx + dy * p.ty, cross: dx * p.rx + dy * p.ry,
    closing: -(dvx * p.tx + dvy * p.ty), lateral: dvx * p.rx + dvy * p.ry,
    alignment: wrap(s.angle - p.angle) };
}
function airDensity(x, y) {
  const altitude = Math.hypot(x, y) - EARTH_R;
  return altitude < EARTH.air.top ? EARTH.air.rho * Math.exp(-Math.max(0, altitude) / EARTH.air.scale) : 0;
}
function gravity(x, y, t) {
  let ax = 0, ay = 0;
  for (const b of BODIES) {
    const p = bodyAt(b, t), dx = x - p.x, dy = y - p.y, r = Math.hypot(dx, dy);
    ax -= b.mu * dx / r ** 3; ay -= b.mu * dy / r ** 3;
  }
  return { x: ax, y: ay };
}
function acceleration(x, y, vx, vy, t, m, chute) {
  const g = gravity(x, y, t), rho = airDensity(x, y);
  if (!rho) return g;
  // Still air around a still Earth: drag opposes the ship's own velocity.
  const k = 0.5 * rho * Math.hypot(vx, vy) * (chute ? SHIP.chuteArea : SHIP.dragArea) / m;
  return { x: g.x - k * vx, y: g.y - k * vy };
}
// The frame the pointing buttons use: the station when close, else the reference body.
function pointFrame(s = ship) {
  const p = station(s);
  if (Math.hypot(s.x - p.x, s.y - p.y) < 20000) return { x: s.x - p.x, y: s.y - p.y, vx: s.vx - p.vx, vy: s.vy - p.vy, station: true };
  return relative(refBody(s), s);
}
function pointTarget(s = ship) {
  if (!s.point) return null;
  const q = pointFrame(s);
  if (s.point === 'up') return q.station ? null : Math.atan2(q.x, q.y);
  if (Math.hypot(q.vx, q.vy) < 0.05) return null;
  const pro = Math.atan2(q.vx, q.vy);
  return s.point === 'pro' ? pro : wrap(pro + Math.PI);
}
// The nose holds its direction (D4): buttons turn it, letting go stops it.
function steer(s, dt) {
  if (held.turn) {
    s.point = null; held.turnFor += dt;
    s.omega = held.turn * (held.turnFor < 0.4 ? TURN_SLOW : TURN_FAST);
  } else {
    held.turnFor = 0;
    const target = pointTarget(s);
    if (target === null) s.omega = 0;
    else {
      const err = wrap(target - s.angle);
      s.omega = dt > 0 ? clamp(err / dt, -POINT_RATE, POINT_RATE) : 0;
    }
  }
  s.angle = wrap(s.angle + s.omega * dt);
}
function surfaceClearance(s = ship) {
  let best = { body: EARTH, clearance: Infinity };
  for (const b of BODIES) {
    const p = bodyAt(b, s.t), c = Math.hypot(s.x - p.x, s.y - p.y) - b.radius - SHIP.length / 2;
    if (c < best.clearance) best = { body: b, clearance: c };
  }
  return best;
}
// Only wall-clock speed changes; forces, fuel and integration steps do not (D11).
function maxWarp() {
  if (!ship || ship.phase !== 'flight') return 1;
  if (ship.landedOn) return ship.throttle ? 1 : 5;
  const near = surfaceClearance(), st = station(), dStation = Math.hypot(ship.x - st.x, ship.y - st.y);
  if (near.clearance < Math.min(500, near.body.radius * 0.2) || approach().range < 50) return 1;
  // Under an open parachute there is nothing to do but wait for the ground.
  if (ship.chute === 'open' && ship.throttle === 0) return near.clearance > 300 ? 100 : near.clearance > 50 ? 5 : 1;
  const quiet = ship.throttle === 0 && !held.turn && !held.forward && !held.side && Math.abs(ship.omega) < 0.02;
  if (!quiet || near.clearance < near.body.near5 || dStation < 5000) return 5;
  if (near.clearance < near.body.near100) return 100;
  return 1000;
}
function canWarp(rate = 10) { return maxWarp() >= rate; }
function limitWarp() { warp = Math.min(warp, maxWarp()); }
function clearHeld() { held.turn = held.forward = held.side = 0; held.turnFor = 0; }
function endFlight(reason, success = false) {
  ship.phase = success ? 'done' : 'crashed'; ship.reason = reason;
  ship.throttle = 0; warp = 1; clearHeld();
  if (success) {
    ship.stars = tripStars(ship);
    const best = stars[ship.trip] || 0;
    if (ship.stars > best) { stars[ship.trip] = ship.stars; saveStars(); }
  }
  saveFlight();
}
function saveStars() {
  try { localStorage.setItem(STARS_KEY, JSON.stringify(stars)); } catch (_) { /* Private browsing can deny storage. */ }
}
function readStars() {
  stars = {};
  try {
    const a = JSON.parse(localStorage.getItem(STARS_KEY));
    if (a && typeof a === 'object') for (const t of TRIPS) if ([1, 2, 3].includes(a[t.id])) stars[t.id] = a[t.id];
  } catch (_) { /* Keep the empty record. */ }
}
function saveFlight() {
  if (!ship) return;
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(ship)); } catch (_) { /* Flight still works without storage. */ }
}
function validFlight(s) {
  if (!s || !['flight', 'done', 'crashed'].includes(s.phase) || !TRIPS.some(t => t.id === s.trip)) return false;
  if (!['x', 'y', 'vx', 'vy', 'angle', 'omega', 'fuel', 'rcs', 'throttle', 't', 'real', 'stationPhase', 'landAngle']
    .every(k => Number.isFinite(s[k]))) return false;
  if (s.landedOn !== null && !BODIES.some(b => b.id === s.landedOn)) return false;
  if (![null, 'pro', 'retro', 'up'].includes(s.point) || !['packed', 'open', 'torn'].includes(s.chute)) return false;
  if (!Array.isArray(s.visited) || !s.visited.every(v => BODIES.some(b => b.id === v))) return false;
  if (!['pad', 'orbit'].includes(s.from) || typeof s.reason !== 'string' || s.reason.length > 300) return false;
  return Math.hypot(s.x, s.y) >= EARTH_R - 100 && Math.hypot(s.x, s.y) < 1e9 &&
    Math.hypot(s.vx, s.vy) < 50000 && Math.abs(s.angle) <= Math.PI + 0.001 &&
    s.fuel >= 0 && s.fuel <= SHIP.fuel && s.rcs >= 0 && s.rcs <= SHIP.rcsDv &&
    s.throttle >= 0 && s.throttle <= 1 && s.t >= 0 && s.t < 1e9 && s.real >= 0;
}
function loadFlight() {
  try { const s = JSON.parse(localStorage.getItem(SAVE_KEY)); return validFlight(s) ? s : null; }
  catch (_) { return null; }
}
// The parachute opens only low and slow enough; faster, it tears (D9).
function openChute() {
  const s = ship;
  if (!s || paused || s.phase !== 'flight' || s.chute !== 'packed') return '';
  const altitude = Math.hypot(s.x, s.y) - EARTH_R;
  if (altitude > CHUTE.height || s.landedOn) return 'Laskuvarjo aukeaa vasta alle 20 km korkeudessa.';
  s.chute = Math.hypot(s.vx, s.vy) > CHUTE.speed ? 'torn' : 'open';
  s.point = null; saveFlight();
  return s.chute === 'torn' ? 'Laskuvarjo repesi: vauhti oli yli 400 m/s.' : 'Laskuvarjo auki.';
}
function liftOff(s, b, ax, ay) {
  const p = bodyAt(b, s.t), ux = Math.sin(s.landAngle), uy = Math.cos(s.landAngle);
  const r = b.radius + SHIP.length / 2, g = b.mu / r ** 2;
  if (ax * ux + ay * uy <= g) return false;
  s.landedOn = null; s.x = p.x + ux * r; s.y = p.y + uy * r; s.vx = p.vx; s.vy = p.vy;
  return true;
}
function stayLanded(s, b) {
  const p = bodyAt(b, s.t), r = b.radius + SHIP.length / 2;
  s.x = p.x + Math.sin(s.landAngle) * r; s.y = p.y + Math.cos(s.landAngle) * r;
  s.vx = p.vx; s.vy = p.vy;
}
function touchdown(s, b) {
  const p = bodyAt(b, s.t), dx = s.x - p.x, dy = s.y - p.y, r = Math.hypot(dx, dy);
  const ux = dx / r, uy = dy / r, rvx = s.vx - p.vx, rvy = s.vy - p.vy;
  const down = -(rvx * ux + rvy * uy), side = Math.abs(rvx * uy - rvy * ux), speed = Math.hypot(rvx, rvy);
  const tilt = Math.abs(wrap(s.angle - Math.atan2(ux, uy))) * 180 / Math.PI;
  const lim = LANDING[b.id];
  let ok, soft, why = '';
  if (b.id === 'rock') {
    ok = speed <= lim.speed && tilt <= lim.tilt; soft = speed <= lim.speed / 2;
    if (!ok) why = speed > lim.speed ? `Liian kova vauhti: ${speed.toFixed(1)} m/s (raja ${lim.speed} m/s).` : `Alus kallistui ${tilt.toFixed(0)}° (raja ${lim.tilt}°).`;
  } else if (b.id === 'earth' && s.chute === 'open') {
    ok = speed <= lim.chute; soft = speed <= lim.chute / 2;
    if (!ok) why = `Laskuvarjolla liian kova vauhti: ${speed.toFixed(1)} m/s (raja ${lim.chute} m/s).`;
  } else {
    ok = down <= lim.down && side <= lim.side && tilt <= lim.tilt;
    soft = down <= lim.down / 2 && side <= lim.side / 2;
    if (down > lim.down) why = `Liian kova vauhti alas: ${down.toFixed(1)} m/s (raja ${lim.down} m/s).`;
    else if (side > lim.side) why = `Liian kova sivuvauhti: ${side.toFixed(1)} m/s (raja ${lim.side} m/s).`;
    else if (tilt > lim.tilt) why = `Alus kallistui ${tilt.toFixed(0)}° (raja ${lim.tilt}°). Paina Pystyyn ennen kosketusta.`;
  }
  if (!ok) { endFlight(`Törmäys: ${b.name}. ${why}`); return; }
  s.landedOn = b.id; s.landAngle = Math.atan2(ux, uy); s.throttle = 0; s.point = null;
  s.angle = s.landAngle; s.omega = 0; s.touch = { body: b.id, soft, speed };
  if (!s.visited.includes(b.id)) s.visited.push(b.id);
  stayLanded(s, b);
  s.note = `Laskeuduit: ${b.name}, ${speed.toFixed(1)} m/s.`;
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
  const half = SHIP.length / 2;
  return [-half, 0, half].map(offset => {
    const dx = s.x + Math.sin(s.angle) * offset - p.x, dy = s.y + Math.cos(s.angle) * offset - p.y;
    return { x: dx * p.tx + dy * p.ty, y: dx * p.rx + dy * p.ry };
  });
}
function stationContact(before, after) {
  // Station solids inflated by the 2 m body radius; the port has its own capture ring.
  const boxes = [[0, 0, 37, 10], [-15, 0, 7, 54], [15, 0, 7, 54], [-45, 0, 1, 5]];
  return boxes.some(([x, y, w, h]) => {
    if (segmentBox(after[0].x, after[0].y, after[2].x, after[2].y, x, y, w, h)) return true;
    return before.some((a, i) => segmentBox(a.x, a.y, after[i].x, after[i].y, x, y, w, h));
  });
}
function tick(dt) {
  const s = ship;
  if (s.phase !== 'flight') return;
  steer(s, dt);
  const m0 = mass(s);
  let thrust = Math.min(SHIP.thrust, m0 * SHIP.accCap) * s.throttle;
  const burn = Math.min(s.fuel, thrust / VE * dt);
  thrust = dt > 0 ? burn * VE / dt : 0;
  s.fuel = Math.max(0, s.fuel - burn);
  if (!s.fuel) s.throttle = 0;
  const command = Math.abs(held.forward) + Math.abs(held.side);
  let rcsScale = 0;
  if (command && s.rcs > 0) {
    const want = command * SHIP.rcsAcc * dt;
    rcsScale = Math.min(1, s.rcs / want); s.rcs = Math.max(0, s.rcs - want);
  }
  const m = (m0 + mass(s)) / 2;
  const forward = thrust / m + held.forward * SHIP.rcsAcc * rcsScale, side = held.side * SHIP.rcsAcc * rcsScale;
  const fx = Math.sin(s.angle) * forward + Math.cos(s.angle) * side;
  const fy = Math.cos(s.angle) * forward - Math.sin(s.angle) * side;
  if (s.landedOn) {
    const b = body(s.landedOn);
    if (!liftOff(s, b, fx, fy)) { s.t += dt; stayLanded(s, b); return; }
    s.note = '';
  }
  const near = approach(s), oldPoints = vehiclePoints(s, near.p);
  const chute = s.chute === 'open';
  const a = acceleration(s.x, s.y, s.vx, s.vy, s.t, m, chute);
  // Velocity Verlet with the thrust held over the step.
  const vxh = s.vx + (a.x + fx) * dt / 2, vyh = s.vy + (a.y + fy) * dt / 2;
  s.x += vxh * dt; s.y += vyh * dt; s.t += dt;
  const b2 = acceleration(s.x, s.y, vxh, vyh, s.t, m, chute);
  s.vx = vxh + (b2.x + fx) * dt / 2; s.vy = vyh + (b2.y + fy) * dt / 2;
  if (chute) { const up = Math.atan2(s.x, s.y); s.angle = up; s.omega = 0; }
  const ground = surfaceClearance(s);
  if (ground.clearance <= 0) {
    touchdown(s, ground.body);
    if (s.phase !== 'flight') return;
    if (ground.body === EARTH && !tripFinished(s)) {
      endFlight('Laskeuduit takaisin Maahan. Matkan tavoite jäi kesken.'); return;
    }
  }
  const d = approach(s);
  // A capture ring, not a magnet: distance, relative speed and nose all matter (D10).
  if (s.trip === 'asema' && d.range < DOCK.range && d.speed <= DOCK.speed &&
      Math.abs(d.alignment) <= DOCK.align * Math.PI / 180 && d.along <= 0.5) {
    s.touch = { body: 'station', soft: d.speed <= DOCK.speed / 2, speed: d.speed };
    endFlight('Telakointi onnistui. Lukot kiinni — tervetuloa asemalle!', true); return;
  }
  if (Math.hypot(s.x - d.p.x, s.y - d.p.y) < 200 && stationContact(oldPoints, vehiclePoints(s, d.p))) {
    endFlight('Törmäys asemaan. Kohdista nokka porttiin ja hidasta alle 0,5 m/s.'); return;
  }
  if (tripFinished(s)) endFlight(TRIP[s.trip].done, true);
  else limitWarp();
}
// Step size follows the nearest body's time scale: small near surfaces and under
// thrust, up to 5 s far out, so ×1000 still integrates the same flight.
function flightStepLimit(s = ship) {
  if (s.throttle > 0 || held.turn || held.forward || held.side || s.landedOn || s.point && Math.abs(s.omega) > 0.02) return 0.02;
  if (approach(s).range < 2000) return 0.02;
  // Parachute drag is strong; a step must stay short against its slowing rate, or it overshoots.
  if (s.chute === 'open' && airDensity(s.x, s.y) > 0) {
    const k = 0.5 * airDensity(s.x, s.y) * Math.hypot(s.vx, s.vy) * SHIP.chuteArea / mass(s);
    return clamp(0.3 / Math.max(k, 1e-9), 0.002, 0.1);
  }
  let scale = Infinity;
  for (const b of BODIES) {
    const p = bodyAt(b, s.t), d = Math.hypot(s.x - p.x, s.y - p.y) - b.radius;
    const v = Math.max(1, Math.hypot(s.vx - p.vx, s.vy - p.vy));
    scale = Math.min(scale, Math.max(d, 0) / v, Math.hypot(s.x - p.x, s.y - p.y) / v);
  }
  return clamp(scale * 0.01, 0.02, 5);
}
function step(seconds) {
  if (!ship || paused || ship.phase !== 'flight' || !Number.isFinite(seconds) || seconds <= 0) return;
  let left = seconds;
  while (left > 1e-9 && ship.phase === 'flight') {
    const dt = Math.min(left, flightStepLimit()); tick(dt); left -= dt;
  }
}
// Consume wall time a substep at a time, so a warp cut takes effect at once.
function advanceFlight(realSeconds) {
  if (!Number.isFinite(realSeconds) || realSeconds <= 0 || paused) return;
  let left = realSeconds;
  while (left > 1e-9 && ship && ship.phase === 'flight') {
    limitWarp();
    const rate = warp, simulated = Math.min(left * rate, flightStepLimit());
    step(simulated);
    ship.real += simulated / rate;
    left -= simulated / rate;
  }
}
// The path ahead with the engine off, in the same physics (D6). Returns Earth-frame
// points with their times, and the closest approach to each moving body.
function predictPath(s = ship, horizon = 30000, maxSteps = 1500) {
  const p = { x: s.x, y: s.y, vx: s.vx, vy: s.vy, t: s.t };
  const out = [{ x: p.x, y: p.y, t: p.t }], closest = {};
  if (s.landedOn || s.phase !== 'flight') return { points: out, closest, hit: null };
  const m = mass(s);
  let hit = null;
  for (let i = 0; i < maxSteps && p.t - s.t < horizon; i++) {
    let scale = Infinity;
    for (const b of BODIES) {
      const q = bodyAt(b, p.t), r = Math.hypot(p.x - q.x, p.y - q.y);
      scale = Math.min(scale, r / Math.max(1, Math.hypot(p.vx - q.vx, p.vy - q.vy)));
    }
    const dt = clamp(scale * 0.04, 0.5, 400);
    const a = acceleration(p.x, p.y, p.vx, p.vy, p.t, m, s.chute === 'open');
    const vxh = p.vx + a.x * dt / 2, vyh = p.vy + a.y * dt / 2;
    p.x += vxh * dt; p.y += vyh * dt; p.t += dt;
    const b2 = acceleration(p.x, p.y, vxh, vyh, p.t, m, s.chute === 'open');
    p.vx = vxh + b2.x * dt / 2; p.vy = vyh + b2.y * dt / 2;
    out.push({ x: p.x, y: p.y, t: p.t });
    for (const b of BODIES) {
      const q = bodyAt(b, p.t), d = Math.hypot(p.x - q.x, p.y - q.y) - b.radius;
      if (!closest[b.id] || d < closest[b.id].d) closest[b.id] = { d, t: p.t, x: p.x, y: p.y };
      if (d <= 0) { hit = { body: b, t: p.t }; break; }
    }
    if (hit) break;
  }
  return { points: out, closest, hit };
}
