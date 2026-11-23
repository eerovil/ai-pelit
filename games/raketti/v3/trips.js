'use strict';
// The six trips (#548). Each opens the next, and gives a star for arriving, one for fuel left over
// `fuel` (a share of a full tank) and one for a soft finish.
const TRIPS = [
  { id: 'kiertorata', name: 'Kiertoradalle', goal: 'Kierrä Maata', fuel: 0.7 },
  { id: 'asema', name: 'Avaruusasemalle', goal: 'Telakoidu asemaan', fuel: 0.6 },
  { id: 'kuu-kierto', name: 'Kuun kiertoradalle', goal: 'Kierrä Kuuta', fuel: 0.6 },
  { id: 'kuuhun', name: 'Kuuhun', goal: 'Laskeudu Kuuhun', fuel: 0.5 },
  { id: 'kotiin', name: 'Kuusta kotiin', goal: 'Kuuhun ja takaisin Maahan', fuel: 0.1 },
  { id: 'kivi', name: 'Pikkukivelle', goal: 'Laskeudu Pikkukivelle', fuel: 0.6 },
];
const TRIP = Object.fromEntries(TRIPS.map(t => [t.id, t]));
// An orbit counts once its lowest point is this high and its highest this low (heights in m).
const ORBIT_GOAL = { earth: { peri: 10, apo: 150 }, moon: { peri: 3, apo: 80 } };

function tripOpen(id) {
  const i = TRIPS.findIndex(t => t.id === id);
  return i === 0 || (i > 0 && (stars[TRIPS[i - 1].id] || 0) >= 1);
}
function orbitReady(b, s) {
  if (refBody(s) !== b || s.landedOn) return false;
  const o = orbitAround(b, s), g = ORBIT_GOAL[b.id];
  return o.closed && o.peri >= g.peri && o.apo <= g.apo;
}
function goalMet(s = ship) {
  switch (s.trip) {
    case 'kiertorata': return s.coast >= 1 && orbitReady(EARTH, s);
    case 'kuu-kierto': return s.coast >= 1 && orbitReady(MOON, s);
    case 'asema': return s.docked;
    case 'kuuhun': return !!s.landedOn && s.landedOn.id === 'moon';
    case 'kotiin': return !!s.landedOn && s.landedOn.id === 'earth' && s.visited.includes('moon');
    case 'kivi': return !!s.landedOn && s.landedOn.id === 'rock';
  }
  return false;
}
function softFinish(s) {
  if (s.trip === 'kiertorata') return orbitAround(EARTH, s).e <= 0.25;
  if (s.trip === 'kuu-kierto') return orbitAround(MOON, s).e <= 0.25;
  return !!(s.touch && s.touch.soft);
}
function starParts(s) {
  return [true, fuelShare(s) >= TRIP[s.trip].fuel, softFinish(s)];
}
function tripStars(s) { return starParts(s).filter(Boolean).length; }

// ---- Hints: a word or two, a direction to drag and how hard, and a spot to watch. ----
// Angles are clockwise from straight up on the screen, as the finger's drag is.
function angleOf(x, y) { return Math.atan2(x, y); }
// The direction the ship moves around b (clockwise is +1), from its motion, else clockwise.
function sideOf(o) { return Math.abs(o.h) > 1e-6 && o.speed > 2 ? (o.h < 0 ? 1 : -1) : 1; }
// How far ahead target (angle around Earth) is of the ship, along the ship's way round.
function aheadOf(target, s, side) {
  return ((side * wrap(angleOf(target.x, target.y) - angleOf(s.x, s.y))) % TAU + TAU) % TAU;
}
// Where the target must be, ahead of the ship, when a half-ellipse from r1 to r2 starts.
function transferLead(r1, r2, n2) {
  const t = Math.PI * Math.sqrt(((r1 + r2) / 2) ** 3 / EARTH.mu);
  return ((Math.PI - n2 * t) % TAU + TAU) % TAU;
}
// Bring the ship down on b: a speed toward the ground that shrinks with height, and the push
// (against gravity too) that gets it there.
function landingPush(b, s) {
  const p = bodyAt(b, s.t), x = s.x - p.x, y = s.y - p.y, r = Math.hypot(x, y), ux = x / r, uy = y / r;
  const alt = r - b.radius, g = b.mu / (r * r);
  // Fall as fast as half the engine's spare push can still stop, so little fuel is lost holding
  // the ship up against gravity; the last metres slow to a gentle touch.
  const want = -(b.land / 6 + Math.sqrt(2 * 0.2 * (SHIP.acc - g) * Math.max(0, alt - 3)));
  const vx = s.vx - p.vx, vy = s.vy - p.vy;
  const ax = (ux * want - vx) * 2.5 + ux * g, ay = (uy * want - vy) * 2.5 + uy * g;
  return { dir: angleOf(ax, ay), power: clamp(Math.hypot(ax, ay) / SHIP.acc, 0, 1) };
}
function landingHint(b, s) {
  const push = landingPush(b, s);
  return { word: 'Hiljaa alas', dir: push.dir, power: push.power, speed: b };
}
// The path's next lowest or highest point, in the frame it is drawn in.
function pathExtreme(path, high) {
  if (!path || !path.points.length) return null;
  const f = bodyAt(path.frame, ship ? ship.t : 0);
  let best = null, bestR = high ? -Infinity : Infinity;
  for (const p of path.points) {
    const r = Math.hypot(p.x - f.x, p.y - f.y);
    if (high ? r > bestR : r < bestR) { bestR = r; best = p; }
    else if (Math.abs(r - bestR) > 0.5) break; // the first high (or low) point, not one rounds later
  }
  return best;
}
// From an orbit around Earth to a moving target on a circle of radius r2.
function transferHint(s, path, target, r2, n2, close, id) {
  const o = orbitAround(EARTH, s), side = sideOf(o);
  const pro = angleOf(o.vx, o.vy), c = path && path.closest[id];
  if (c && c.d < close) return { word: 'Odota', mark: { x: c.x, y: c.y }, ghost: { id, t: c.t } };
  const left = c ? c.t - s.t : 0;
  if (c && c.d < Math.min(close * 12, 120) && left > 2 && o.apo + EARTH.radius > r2 * 0.85 && !(s.thrust > 0 && o.apo + EARTH.radius < r2)) {
    // On the way but missing: nudge the path toward where the target will be.
    const dx = c.at.x - c.x, dy = c.at.y - c.y, miss = c.d - close * 0.4;
    return { word: 'Korjaa', dir: angleOf(dx, dy), power: clamp(miss / left / SHIP.acc * 4, 0.05, 1), ghost: { id, t: c.t } };
  }
  if (o.apo + EARTH.radius < r2 * 0.92 || (s.thrust > 0 && o.apo + EARTH.radius < r2 && o.alt < o.peri + 15)) {
    const wait = ((aheadOf(target, s, side) - transferLead(o.r, r2, n2)) % TAU + TAU) % TAU;
    if (wait < 0.12 || s.thrust > 0 && o.apo > 60) {
      return { word: 'Kiihdytä', dir: pro, power: clamp((r2 - o.apo - EARTH.radius) / 60, 0.15, 1) };
    }
    return { word: 'Odota', target: id, wait: wait / Math.abs(Math.sqrt(EARTH.mu / o.r ** 3) - n2) };
  }
  // Far off: lower the high point again at the low point and wait for the next window.
  if (o.alt < o.peri + 10) return { word: 'Jarruta', dir: pro + Math.PI, power: 0.5 };
  return { word: 'Odota', target: id };
}
// From the pad into a low orbit around Earth.
function ascentHint(s, path) {
  const o = orbitAround(EARTH, s), up = angleOf(o.x, o.y), side = sideOf(o);
  if (o.alt < 5 && o.apo < 25) return { word: 'Ylös', dir: up, power: 1 };
  if (o.apo < 40) return { word: 'Vinosti ylös', dir: up + side * 1.05, power: 1 };
  if (o.vr < 1.5 || o.alt > o.apo - 3 || (s.thrust > 0 && o.alt > o.apo - 12)) return { word: 'Sivulle', dir: up + side * Math.PI / 2, power: 1 };
  return { word: 'Odota', mark: pathExtreme(path, true) };
}
// The hint, and for a wait, how many seconds until the next thing to do (when that is known:
// a window opening, the path's high or low point, the closest pass). A tap on "Odota" skips it.
function hint(s = ship, path = null) {
  const h = nextMove(s, path);
  if (h.word === 'Odota' && h.wait === undefined) {
    const t = h.ghost ? h.ghost.t : h.mark ? h.mark.t : undefined;
    if (t !== undefined) h.wait = Math.max(0, t - s.t);
  }
  // Mark on the drawn path where the ship will be when the wait ends.
  if (h.word === 'Odota' && h.wait !== undefined && !h.mark && path) h.mark = pathPointAt(s, path, s.t + h.wait);
  return h;
}
// The path's point at time t; past its end, on a closed orbit, a whole round earlier.
function pathPointAt(s, path, t) {
  const pts = path.points;
  if (!pts.length) return null;
  if (t > pts[pts.length - 1].t && path.frame === EARTH) {
    const o = orbitAround(EARTH, s);
    if (!o.closed) return null;
    const a = (o.peri + o.apo) / 2 + EARTH.radius, period = TAU * Math.sqrt(a ** 3 / EARTH.mu);
    t = s.t + ((t - s.t) % period);
  }
  let best = null;
  for (const q of pts) if (!best || Math.abs(q.t - t) < Math.abs(best.t - t)) best = q;
  return best && Math.abs(best.t - t) < 1 ? best : null;
}
function nextMove(s, path) {
  if (!s) return { word: '' };
  if (s.phase === 'done') return { word: 'Valmis!' };
  if (s.phase === 'crashed') return { word: 'Rysähti!' };
  if (s.landedOn) return { word: 'Vedä ylös', dir: s.landedOn.a, power: 1 };
  const ref = refBody(s), trip = s.trip, home = trip === 'kotiin' && s.visited.includes('moon');
  if (ref === EARTH && home) {
    const c = path && path.closest.earth;
    if (orbitAround(EARTH, s).alt < 80 || (path && path.hit && path.hit.body === 'earth')) return landingHint(EARTH, s);
    if (c && c.d < 20) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t } };
    const o = orbitAround(EARTH, s);
    return { word: 'Jarruta', dir: angleOf(o.vx, o.vy) + Math.PI, power: 0.6 };
  }
  const nearStation = trip === 'asema' && stationRelative(s).dist < 30;
  if (ref === EARTH && !nearStation && orbitAround(EARTH, s).peri < ORBIT_GOAL.earth.peri) return ascentHint(s, path);
  if (ref === EARTH) {
    if (trip === 'kiertorata') return { word: s.thrust > 0 ? 'Päästä irti' : 'Odota' };
    if (trip === 'asema') return stationHint(s, path);
    if (trip === 'kivi') return transferHint(s, path, bodyAt(ROCK, s.t), ROCK.orbit.r, ROCK.orbit.n, 6, 'rock');
    return transferHint(s, path, bodyAt(MOON, s.t), MOON.orbit.r, MOON.orbit.n, 25, 'moon');
  }
  if (ref === ROCK) return landingHint(ROCK, s);
  // Near the Moon.
  const o = orbitAround(MOON, s), pro = angleOf(o.vx, o.vy), low = pathExtreme(path, false);
  if (home) {
    const c = path && path.closest.earth;
    if (o.alt < 4) return { word: 'Ylös', dir: angleOf(o.x, o.y), power: 1 };
    if (c && c.d < 20) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t } };
    const m = bodyAt(MOON, s.t);
    return { word: 'Kohti Maata', dir: angleOf(-m.vx, -m.vy), power: 1 };
  }
  // A long oval counts too, but the hint brakes on at the low point for a rounder one.
  if (trip === 'kuu-kierto' && orbitReady(MOON, s) && (o.apo < 35 || o.alt > o.peri + 6)) return { word: s.thrust > 0 ? 'Päästä irti' : 'Odota' };
  if (trip !== 'kuu-kierto' && (o.alt < 25 || (o.closed && o.apo <= ORBIT_GOAL.moon.apo))) return landingHint(MOON, s);
  if (o.peri < ORBIT_GOAL.moon.peri + (s.thrust > 0 ? 4 : 0) && o.alt > 15 && trip === 'kuu-kierto') {
    return { word: 'Sivulle', dir: angleOf(o.x, o.y) + sideOf(o) * Math.PI / 2, power: 0.5 };
  }
  if (o.alt < o.peri + 6 || o.alt < 10) return { word: 'Jarruta', dir: pro + Math.PI, power: 1 };
  return { word: 'Odota', mark: low };
}
// Station: a transfer to its height, then close in slowly with the arrow.
function stationHint(s, path) {
  const d = stationRelative(s);
  if (d.dist < 30) {
    const want = Math.min(2.4, 0.2 * d.dist + 0.3);
    const ax = d.dx / d.dist * want - d.vx, ay = d.dy / d.dist * want - d.vy, need = Math.hypot(ax, ay);
    if (need < (s.thrust > 0 ? 0.1 : 0.7)) return { word: 'Odota', station: true };
    return { word: 'Kohti asemaa', dir: angleOf(ax, ay), power: clamp(need / 6, 0.05, 1), station: true };
  }
  const o = orbitAround(EARTH, s), st = stationAt(s.t), side = sideOf(o);
  if (o.apo + EARTH.radius < STATION.r - 2) {
    const wait = ((aheadOf(st, s, side) - transferLead(o.r, STATION.r, STATION.n)) % TAU + TAU) % TAU;
    if (wait < 0.12 || s.thrust > 0) return { word: 'Kiihdytä', dir: angleOf(o.vx, o.vy), power: 0.3 };
    return { word: 'Odota', station: true, wait: wait / Math.abs(Math.sqrt(EARTH.mu / o.r ** 3) - STATION.n) };
  }
  if (o.apo + EARTH.radius > STATION.r + 6 && o.alt < o.peri + 6) {
    return { word: 'Jarruta', dir: angleOf(o.vx, o.vy) + Math.PI, power: 0.3 };
  }
  return { word: 'Odota', station: true, mark: pathExtreme(path, true) };
}
