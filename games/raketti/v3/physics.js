'use strict';
// Raketti v3 (#548, rethought on 2026-11-23): a toy Earth–Moon system small enough that a whole
// orbit fits on a phone's screen, flown with one finger. Units are game metres and seconds; nothing
// is to real scale. One Earth orbit takes about 20 s and the Moon is about a minute away; Mars,
// the last trip, about five minutes. A wait can be skipped (the hint button runs time faster).
const TAU = Math.PI * 2;
function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
function wrap(a) { a = (a + Math.PI) % TAU; if (a < 0) a += TAU; return a - Math.PI; }

// Every body is in this one list. g is the surface gravity, so mu = g × radius². Moons move on
// fixed circles around Earth, Earth and Mars on fixed circles around the Sun (#548: the Mars trip);
// the world is drawn and counted from Earth's middle, so the Sun moves round Earth. `sphere` is how
// far out a body pulls: inside it, that body alone (and the pull that carries the body itself).
const AU = 8000, YEAR = 420; // Earth's distance from the Sun and its year, in game metres and seconds
const BODIES = [
  { id: 'earth', name: 'Maa', radius: 60, g: 14, sphere: 1100, land: 6 },
  { id: 'moon', name: 'Kuu', radius: 16, g: 9.5, sphere: 125, land: 5, orbit: { r: 420, phase: 2.2 } },
  { id: 'rock', name: 'Pikkukivi', radius: 4, g: 0.5, sphere: 24, land: 3, orbit: { r: 250, phase: 4.4 } },
  { id: 'sun', name: 'Aurinko', radius: 320, g: 0, sphere: Infinity, land: 0 },
  { id: 'mars', name: 'Mars', radius: 30, g: 7, sphere: 500, land: 5, helio: { r: AU * 1.524, phase: 0 } },
];
const BODY = {};
for (const b of BODIES) { b.mu = b.g * b.radius ** 2; BODY[b.id] = b; }
const EARTH = BODY.earth, MOON = BODY.moon, ROCK = BODY.rock, SUN = BODY.sun, MARS = BODY.mars;
SUN.mu = TAU * TAU * AU ** 3 / YEAR ** 2; SUN.g = SUN.mu / SUN.radius ** 2;
// Earth round the Sun: the Sun sits below Earth at the start.
const EARTH_HELIO = { r: AU, phase: 0, n: TAU / YEAR };
for (const b of BODIES) if (b.orbit) b.orbit.n = Math.sqrt(EARTH.mu / b.orbit.r ** 3);
for (const b of BODIES) if (b.helio) b.helio.n = Math.sqrt(SUN.mu / b.helio.r ** 3);
// Where Mars starts, ahead of Earth round the Sun: its window opens about 150 s in.
MARS.helio.phase = 2.32;
// The station circles 40 m above Earth; touching it slowly docks.
const STATION = { r: 100, phase: 0.9, dock: 3, speed: 3 };
STATION.n = Math.sqrt(EARTH.mu / STATION.r ** 3);
// The rockets: engine push (m/s²; Earth pulls 14), fuel as Δv (m/s), how fast the nose turns
// toward the finger (rad/s) and how far its legs reach from its middle. Each trip names its
// rocket; a cargo rocket carrying a big part of the Moon base pushes and turns slower (#548).
const ROCKETS = {
  raketti: { name: 'Raketti', acc: 32, dv: 340, turn: 14, size: 0.8 },
  kiitaja: { name: 'Kiitäjä', acc: 38, dv: 340, turn: 18, size: 0.7 },
  rahti: { name: 'Rahtiraketti', acc: 21, dv: 400, turn: 5, size: 1.1 },
};
// The rocket of the flight on screen.
const SHIP = Object.assign({}, ROCKETS.raketti);
function useRocket(id) { Object.assign(SHIP, ROCKETS[id] || ROCKETS.raketti); }
// The Moon base stands on top of the Moon (the Moon never turns), in a zone this wide (radians).
const BASE = { a: 0, zone: 0.4 };
const REFUEL = 120; // m/s of Δv a second while the ship stands at a finished base
var turnScale = 1;
const STEP = 1 / 120;
const SAVE_KEY = 'ai-pelit:raketti:matka', STARS_KEY = 'ai-pelit:raketti:tahdet';

var ship = null, stick = { on: false, angle: 0, power: 0 }, paused = true, stars = {};

// A circle's spot and speed at time t.
function onCircle(c, t) {
  const a = c.phase + c.n * t, r = c.r, w = r * c.n;
  return { x: r * Math.sin(a), y: r * Math.cos(a), vx: w * Math.cos(a), vy: -w * Math.sin(a), ax: -c.n * c.n * r * Math.sin(a), ay: -c.n * c.n * r * Math.cos(a) };
}
// Where a body is (and how it moves) as seen from Earth's middle.
function bodyAt(b, t) {
  if (b.orbit) return onCircle(b.orbit, t);
  if (b === EARTH) return { x: 0, y: 0, vx: 0, vy: 0, ax: 0, ay: 0 };
  const e = onCircle(EARTH_HELIO, t);
  if (b === SUN) return { x: -e.x, y: -e.y, vx: -e.vx, vy: -e.vy, ax: -e.ax, ay: -e.ay };
  const h = onCircle(b.helio, t);
  return { x: h.x - e.x, y: h.y - e.y, vx: h.vx - e.vx, vy: h.vy - e.vy, ax: h.ax - e.ax, ay: h.ay - e.ay };
}
function stationAt(t) {
  const a = STATION.phase + STATION.n * t, r = STATION.r, w = r * STATION.n;
  return { x: r * Math.sin(a), y: r * Math.cos(a), vx: w * Math.cos(a), vy: -w * Math.sin(a) };
}
// One body pulls at a time (#548: an orbit must not drift by itself). Inside the Moon's, the
// rock's or Mars's sphere the ship falls around it as if it stood still, carried along with it;
// inside Earth's sphere only Earth pulls; further out only the Sun.
function pull(b, x, y) {
  const r2 = x * x + y * y, k = -b.mu / (r2 * Math.sqrt(r2));
  return { ax: k * x, ay: k * y };
}
// The small bodies whose sphere the ship can be in, nearest first in the list.
const SMALL = BODIES.filter(b => b !== EARTH && b !== SUN);
function gravity(x, y, t) {
  const b = refAt(x, y, t), p = bodyAt(b, t), own = pull(b, x - p.x, y - p.y);
  return { ax: own.ax + p.ax, ay: own.ay + p.ay };
}
function refAt(x, y, t) {
  for (const b of SMALL) {
    const p = bodyAt(b, t), dx = x - p.x, dy = y - p.y;
    if (dx * dx + dy * dy < b.sphere * b.sphere) return b;
  }
  return x * x + y * y < EARTH.sphere * EARTH.sphere ? EARTH : SUN;
}
// The body whose numbers count: the one whose sphere the ship is in.
function refBody(s = ship) { return refAt(s.x, s.y, s.t); }
// The body whose surface is nearest, and the height above it.
function nearestSurface(s = ship) {
  let best = { body: EARTH, alt: Infinity };
  for (const b of BODIES) {
    if (b === SUN) continue;
    const p = bodyAt(b, s.t), alt = Math.hypot(s.x - p.x, s.y - p.y) - b.radius;
    if (alt < best.alt) best = { body: b, alt };
  }
  return best;
}
// The two-body orbit around b: heights of its lowest and highest points above the surface.
function orbitAround(b, s = ship) {
  const p = bodyAt(b, s.t), x = s.x - p.x, y = s.y - p.y, vx = s.vx - p.vx, vy = s.vy - p.vy;
  const r = Math.hypot(x, y), v2 = vx * vx + vy * vy, energy = v2 / 2 - b.mu / r, h = x * vy - y * vx;
  const e = Math.sqrt(Math.max(0, 1 + 2 * energy * h * h / (b.mu * b.mu)));
  const closed = energy < 0, a = closed ? -b.mu / (2 * energy) : Infinity;
  const peri = closed ? a * (1 - e) : h * h / (b.mu * (1 + e));
  return { r, alt: r - b.radius, x, y, vx, vy, speed: Math.sqrt(v2), vr: (x * vx + y * vy) / r, h, e, closed,
    peri: peri - b.radius, apo: closed ? a * (1 + e) - b.radius : Infinity };
}
// The ship's motion against the nearest body: speed toward its surface and along it.
function relative(b, s = ship) {
  const o = orbitAround(b, s);
  return { alt: o.alt, speed: o.speed, down: -o.vr, side: Math.abs(o.h) / o.r };
}
function stationRelative(s = ship) {
  const st = stationAt(s.t), dx = st.x - s.x, dy = st.y - s.y, vx = s.vx - st.vx, vy = s.vy - st.vy;
  return { dist: Math.hypot(dx, dy), dx, dy, vx, vy, speed: Math.hypot(vx, vy) };
}

function freshFlight(trip = 'kiertorata') {
  // The pad stands on top of Earth; the ship stands on it with its nose up.
  const r = ROCKETS[TRIP[trip].rocket || 'raketti'], dv = r.dv * (TRIP[trip].tank || 1);
  return { trip, t: 0, x: 0, y: EARTH.radius + r.size, vx: 0, vy: 0, angle: 0, dv, refuel: false, tanked: false,
    thrust: 0, coast: 0, phase: 'flight', landedOn: { id: 'earth', a: 0 }, visited: ['earth'],
    touch: null, reason: '', stars: 0, docked: false };
}

// Sitting on a body: the ship rides along with it until the engine pushes it off.
function sitOn(s, b, a) {
  const p = bodyAt(b, s.t), r = b.radius + SHIP.size;
  s.x = p.x + r * Math.sin(a); s.y = p.y + r * Math.cos(a); s.vx = p.vx; s.vy = p.vy;
}
function contact(s) {
  for (const b of BODIES) {
    const p = bodyAt(b, s.t), dx = s.x - p.x, dy = s.y - p.y, r = Math.hypot(dx, dy);
    if (r > b.radius + SHIP.size) continue;
    const speed = Math.hypot(s.vx - p.vx, s.vy - p.vy), a = Math.atan2(dx, dy);
    s.touch = { body: b.id, speed, soft: speed <= b.land / 2 };
    if (speed > b.land) {
      endFlight(`Liian kova lasku: ${speed.toFixed(1)} m/s (raja ${b.land}).`);
      return;
    }
    s.landedOn = { id: b.id, a }; s.angle = a;
    // A finished base fills the tank of a ship that lands in it.
    if (b === MOON && atBase(a) && baseReady()) s.refuel = true;
    if (!s.visited.includes(b.id)) s.visited.push(b.id);
    sitOn(s, b, a);
    return;
  }
  const st = stationRelative(s);
  if (s.trip === 'asema' && st.dist < STATION.dock) {
    s.touch = { body: 'station', speed: st.speed, soft: st.speed <= 1.5 };
    if (st.speed > STATION.speed) endFlight(`Törmäsit asemaan: ${st.speed.toFixed(1)} m/s (raja ${STATION.speed}).`);
    else s.docked = true;
  }
}

// One fixed step of 1/120 s. The finger sets where the nose should point and how hard to burn;
// the engine pushes only once the nose is within 60° of that, and less the further off it is.
function step(dt = STEP) {
  const s = ship;
  if (!s || s.phase !== 'flight') return;
  let thrust = 0;
  // The nose follows the finger as soon as it moves, before the engine starts, and turns as fast
  // on the screen however slow time runs (turnScale, set by the frame loop).
  const aiming = stick.power > 0 || (stick.on && Math.hypot(stick.dx || 0, stick.dy || 0) > 3);
  if (aiming) {
    const err = wrap(stick.angle - s.angle), turn = SHIP.turn * turnScale * dt;
    s.angle = wrap(s.angle + clamp(err, -turn, turn));
  }
  if (stick.power > 0) {
    const off = Math.abs(wrap(stick.angle - s.angle));
    if (s.dv > 0 && off < Math.PI / 3) thrust = SHIP.acc * stick.power * Math.cos(off);
  }
  if (thrust > 0) { const use = Math.min(s.dv, thrust * dt); thrust = use / dt; s.dv -= use; }
  s.thrust = thrust;
  s.coast = thrust > 0 ? 0 : s.coast + dt;
  const tx = thrust * Math.sin(s.angle), ty = thrust * Math.cos(s.angle);
  if (s.landedOn) {
    const b = BODY[s.landedOn.id], up = s.landedOn.a;
    s.t += dt;
    if (s.refuel) {
      if (s.dv < SHIP.dv) { s.dv = Math.min(SHIP.dv, s.dv + REFUEL * dt); s.coast = 0; }
      if (s.dv >= SHIP.dv) s.tanked = true;
    }
    if (tx * Math.sin(up) + ty * Math.cos(up) > b.g) {
      s.landedOn = null; s.refuel = false;
      const p = bodyAt(b, s.t), r = b.radius + SHIP.size + 0.05;
      s.x = p.x + r * Math.sin(up); s.y = p.y + r * Math.cos(up);
      s.vx = p.vx + Math.sin(up) * 0.5; s.vy = p.vy + Math.cos(up) * 0.5;
    } else sitOn(s, b, up);
    return;
  }
  // Velocity Verlet with the thrust held over the step.
  const g0 = gravity(s.x, s.y, s.t);
  s.x += s.vx * dt + 0.5 * (g0.ax + tx) * dt * dt;
  s.y += s.vy * dt + 0.5 * (g0.ay + ty) * dt * dt;
  s.t += dt;
  const g1 = gravity(s.x, s.y, s.t);
  s.vx += (0.5 * (g0.ax + g1.ax) + tx) * dt;
  s.vy += (0.5 * (g0.ay + g1.ay) + ty) * dt;
  contact(s);
}

// The path ahead with the engine off, in the same physics. Points are drawn in the frame of the
// body the ship is near (its motion taken out), so an orbit around the Moon shows as a loop, and
// so are the closest passes. Out round the Sun the steps are longer and the path goes further
// (#548: the Mars trip takes minutes); `exit` is where it first leaves Earth's sphere.
function predictPath(s = ship, horizon = 90, dt = 0.05) {
  const frame = refBody(s), f0 = bodyAt(frame, s.t);
  const out = { frame, points: [], hit: null, closest: {}, exit: null };
  if (!s || s.landedOn || s.phase !== 'flight') return out;
  if (TRIP[s.trip].far && (s.tanked || frame === SUN || frame === MARS)) horizon = 600;
  let x = s.x, y = s.y, vx = s.vx, vy = s.vy, t = s.t, n = 0;
  const end = s.t + horizon;
  while (t < end) {
    const g0 = gravity(x, y, t), ref = refAt(x, y, t), h = ref === SUN ? 0.5 : dt;
    x += vx * h + 0.5 * g0.ax * h * h; y += vy * h + 0.5 * g0.ay * h * h; t += h;
    const g1 = gravity(x, y, t);
    vx += 0.5 * (g0.ax + g1.ax) * h; vy += 0.5 * (g0.ay + g1.ay) * h;
    const f = bodyAt(frame, t), px = x - f.x + f0.x, py = y - f.y + f0.y;
    if (n++ % 2 === 0 || ref === SUN) out.points.push({ x: px, y: py, t, vx: vx - f.vx, vy: vy - f.vy });
    if (!out.exit && x * x + y * y >= EARTH.sphere * EARTH.sphere) out.exit = { x, y, vx, vy, t };
    for (const b of BODIES) {
      if (b === SUN) continue;
      const p = bodyAt(b, t), d = Math.hypot(x - p.x, y - p.y) - b.radius;
      const c = out.closest[b.id];
      if (!c || d < c.d) out.closest[b.id] = { d, t, x: px, y: py, at: { x: p.x - f.x + f0.x, y: p.y - f.y + f0.y } };
      if (d < SHIP.size) {
        out.hit = { body: b.id, x: px, y: py, t };
        out.points.push({ x: px, y: py, t });
        return out;
      }
    }
  }
  return out;
}
function fuelShare(s = ship) { return s.dv / SHIP.dv; }
function endFlight(reason, success = false) {
  const s = ship;
  s.phase = success ? 'done' : 'crashed'; s.reason = reason; s.thrust = 0;
  stick.on = false; stick.power = 0;
  if (success) {
    s.stars = tripStars(s);
    if (s.stars > (stars[s.trip] || 0)) { stars[s.trip] = s.stars; saveStars(); }
  }
  saveFlight();
}
function saveStars() {
  try { localStorage.setItem(STARS_KEY, JSON.stringify(stars)); } catch (_) { /* Private browsing can deny storage. */ }
}
function readStars() {
  try {
    const v = JSON.parse(localStorage.getItem(STARS_KEY) || '{}'), out = {};
    for (const t of TRIPS) if (Number.isInteger(v[t.id]) && v[t.id] >= 1 && v[t.id] <= 3) out[t.id] = v[t.id];
    return out;
  } catch (_) { return {}; }
}
function saveFlight() {
  try {
    if (ship && ship.phase === 'flight') localStorage.setItem(SAVE_KEY, JSON.stringify(ship));
    else localStorage.removeItem(SAVE_KEY);
  } catch (_) { /* Private browsing can deny storage. */ }
}
// A saved flight is resumed only when every number in it makes sense.
function readFlight() {
  try {
    const s = JSON.parse(localStorage.getItem(SAVE_KEY) || 'null');
    if (!s || typeof s !== 'object' || !TRIP[s.trip] || s.phase !== 'flight') return null;
    for (const k of ['t', 'x', 'y', 'vx', 'vy', 'angle', 'dv', 'coast']) if (!Number.isFinite(s[k])) return null;
    const rocket = ROCKETS[TRIP[s.trip].rocket || 'raketti'];
    if (s.t < 0 || s.dv < 0 || s.dv > rocket.dv || Math.hypot(s.x, s.y) > 40000) return null;
    if (!Array.isArray(s.visited) || s.visited.some(v => !BODY[v])) return null;
    if (s.landedOn !== null && !(s.landedOn && BODY[s.landedOn.id] && Number.isFinite(s.landedOn.a))) return null;
    return Object.assign(freshFlight(s.trip), s, { thrust: 0, refuel: !!s.refuel, tanked: !!s.tanked });
  } catch (_) { return null; }
}
