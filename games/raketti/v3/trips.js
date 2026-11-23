'use strict';
// The trips (#548). Each opens the next, and gives a star for arriving, one for fuel left over
// `fuel` (a share of a full tank) and one for a soft finish.
const TRIPS = [
  { id: 'kiertorata', name: 'Kiertoradalle', goal: 'Kierrä Maata', fuel: 0.7 },
  { id: 'asema', name: 'Avaruusasemalle', goal: 'Telakoidu asemaan', fuel: 0.6 },
  { id: 'kuu-kierto', name: 'Kuun kiertoradalle', goal: 'Kierrä Kuuta', fuel: 0.6 },
  { id: 'kuuhun', name: 'Kuuhun', goal: 'Laskeudu Kuuhun', fuel: 0.5 },
  { id: 'kotiin', name: 'Kuusta kotiin', goal: 'Kuuhun ja takaisin Maahan', fuel: 0.1 },
  { id: 'kivi', name: 'Pikkukivelle', goal: 'Laskeudu Pikkukivelle', fuel: 0.6 },
  // The Moon base (#548): a part a trip, landed in the base on top of the Moon.
  { id: 'paneeli', name: 'Aurinkopaneeli Kuuhun', goal: 'Vie aurinkopaneeli Kuun tukikohtaan', fuel: 0.5, rocket: 'kiitaja', part: true },
  { id: 'tankki', name: 'Polttoainetankki Kuuhun', goal: 'Vie tankki Kuun tukikohtaan', fuel: 0.4, rocket: 'rahti', part: true },
  { id: 'tehdas', name: 'Polttoainetehdas Kuuhun', goal: 'Vie tehdas Kuun tukikohtaan', fuel: 0.4, rocket: 'rahti', part: true },
  // Mars (#548): a part-full tank from Earth, filled at the Moon base, then minutes round the Sun.
  { id: 'mars', name: 'Marsiin', goal: 'Tankkaa Kuussa ja laskeudu Marsiin', fuel: 0.5, tank: 0.4, far: true },
];
const TRIP = Object.fromEntries(TRIPS.map(t => [t.id, t]));
// An orbit counts once its lowest point is this high and its highest this low (heights in m).
const ORBIT_GOAL = { earth: { peri: 10, apo: 150 }, moon: { peri: 3, apo: 80 } };

// The parts built so far: a part trip flown once.
function baseBuilt(id) { return (stars[id] || 0) >= 1; }
function baseReady() { return TRIPS.every(t => !t.part || baseBuilt(t.id)); }
function atBase(a) { return Math.abs(wrap(a - BASE.a)) < BASE.zone; }
// Where on the Moon this trip should land, if anywhere in particular.
function landingAim(s) { return TRIP[s.trip].part || (TRIP[s.trip].far && !s.tanked) ? BASE.a : undefined; }
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
    case 'paneeli': case 'tankki': case 'tehdas':
      return !!s.landedOn && s.landedOn.id === 'moon' && atBase(s.landedOn.a);
    case 'mars': return !!s.landedOn && s.landedOn.id === 'mars';
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
function landingPush(b, s, aim) {
  const p = bodyAt(b, s.t), x = s.x - p.x, y = s.y - p.y, r = Math.hypot(x, y), ux = x / r, uy = y / r;
  const alt = r - b.radius, g = b.mu / (r * r);
  // Fall as fast as half the engine's spare push can still stop, so little fuel is lost holding
  // the ship up against gravity; the last metres slow to a gentle touch.
  const want = -(b.land / 6 + Math.sqrt(2 * 0.2 * (SHIP.acc - g) * Math.max(0, alt - 3)));
  // Toward the spot to land at, if any: a sideways speed that shrinks as the spot comes near.
  const side = aim === undefined ? 0 : clamp(wrap(aim - angleOf(x, y)) * b.radius * 0.35, -4, 4);
  const vx = s.vx - p.vx, vy = s.vy - p.vy;
  let ax = (ux * want + uy * side - vx) * 2.5 + ux * g, ay = (uy * want - ux * side - vy) * 2.5 + uy * g;
  // Never push toward the ground (#548): gravity speeds the fall for free, so only the sideways
  // part of a push that points down is kept.
  const down = ax * ux + ay * uy;
  if (down < 0) { ax -= ux * down; ay -= uy * down; }
  return { dir: angleOf(ax, ay), power: clamp(Math.hypot(ax, ay) / SHIP.acc, 0, 1) };
}
// The fastest the ship may move this high above b and still stop gently with part of its push.
function landingLimit(b, alt) {
  const g = b.mu / (b.radius + Math.max(0, alt)) ** 2;
  return b.land / 6 + Math.sqrt(2 * 0.3 * (SHIP.acc - g) * Math.max(0, alt - 3));
}
// When the last gentle push toward the ground was shown (flight seconds).
var descentAt = -1;
// Landing on b. Falling costs nothing, so the hint waits while the ship is slow enough for its
// height and brakes only once it is not (#548: braking early wasted fuel), marking on the path
// where the braking starts. A path that misses b is first bent down to it.
function landingHint(b, s, path, aim) {
  const p = bodyAt(b, s.t), x = s.x - p.x, y = s.y - p.y, alt = Math.hypot(x, y) - b.radius;
  const vx = s.vx - p.vx, vy = s.vy - p.vy, speed = Math.hypot(vx, vy), limit = landingLimit(b, alt);
  const braking = s.thrust > 0 && speed > limit * 0.75;
  // Once the gentle way down has begun, it goes on to the ground (#548: "Hiljaa alas", "Jarruta"
  // and "Kohti tukikohtaa" took turns several times a second near the base).
  // Toward a spot, only once above it: before that the path's end is steered to it.
  const above = aim === undefined || Math.abs(wrap(aim - angleOf(x, y))) < BASE.zone;
  // A push too small to bother with is left out, with a gap between starting and stopping
  // (#548: on the rock the push needed sat at the line and the word changed every frame).
  const least = currentWord === 'Hiljaa alas' || currentWord === 'Kohti tukikohtaa' ? 0.005 : 0.03;
  if (above && alt < 25 && s.t >= descentAt && s.t - descentAt < 1.5) {
    const push = landingPush(b, s, aim);
    if (push.power < least) return { word: 'Odota', speed: b };
    descentAt = s.t;
    return { word: 'Hiljaa alas', dir: push.dir, power: push.power, speed: b, base: aim !== undefined };
  }
  const hits = path && path.frame === b && path.hit && path.hit.body === b.id;
  // Once braking to come down, go on until the path meets the ground steeply, not just grazes it
  // (#548: a grazing path made "Jarruta" and "Odota" take turns).
  const grazes = hits && currentWord === 'Jarruta' && (() => {
    const q = path.points.filter(q => q.vx !== undefined).pop();
    if (!q) return false;
    const rx = q.x - p.x, ry = q.y - p.y, rr = Math.hypot(rx, ry);
    return -(rx * q.vx + ry * q.vy) / rr < 0.3 * Math.hypot(q.vx, q.vy);
  })();
  const pushingDown = (currentWord === 'Hiljaa alas' || currentWord === 'Kohti tukikohtaa') && alt < 25;
  if (alt > 3 && path && path.frame === b && (!hits || grazes) && !braking && !pushingDown) {
    return { word: 'Jarruta', dir: angleOf(vx, vy) + Math.PI, power: 0.4, speed: b };
  }
  // Falling where it should not: steer toward the spot (a sideways push) rather than wait.
  const err = aim !== undefined && hits ? wrap(aim - angleOf(path.hit.x - p.x, path.hit.y - p.y)) : 0;
  const off = Math.abs(err) > BASE.zone * (currentWord === 'Kohti tukikohtaa' ? 0.25 : 0.5);
  if (off) {
    // A push along the ground moves where the ship comes down; close to the ground, partly up too.
    const left = Math.max(0.5, path.hit.t - s.t), up = angleOf(x, y), sign = Math.sign(err);
    return { word: 'Kohti tukikohtaa', dir: up + sign * (left < 2.5 ? 0.7 : Math.PI / 2), power: clamp(Math.abs(err) * b.radius / left / SHIP.acc * 2, 0.1, 1), speed: b, base: true };
  }
  if (alt > 3 && speed < limit && !braking && !off) {
    const f = bodyAt(b, s.t);
    // Where on the path the speed passes the limit, found between the path's points so the mark
    // stays put while the ship flies on (#548: snapping to a point made it shake).
    const over = q => Math.hypot(q.vx, q.vy) - landingLimit(b, Math.hypot(q.x - f.x, q.y - f.y) - b.radius);
    let start = null;
    if (hits) {
      const pts = path.points.filter(q => q.vx !== undefined);
      for (let i = 0; i < pts.length; i++) {
        const e = over(pts[i]);
        if (e <= 0) continue;
        if (i === 0) { start = pts[0]; break; }
        const e0 = over(pts[i - 1]);
        start = mixPoints(pts[i - 1], pts[i], -e0 / (e - e0));
        break;
      }
    }
    if (start) return { word: 'Odota', mark: start, wait: Math.max(0, start.t - s.t), speed: b };
    return { word: 'Odota', speed: b };
  }
  const push = landingPush(b, s, aim);
  if (push.power < least && !braking) return { word: 'Odota', speed: b };
  descentAt = s.t;
  // Still beside the spot, the gentle way down keeps the word of the steer toward it.
  return { word: above ? 'Hiljaa alas' : 'Kohti tukikohtaa', dir: push.dir, power: push.power, speed: b, base: aim !== undefined };
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
  const o = orbitAround(EARTH, s), side = sideOf(o), R = EARTH.radius;
  const pro = angleOf(o.vx, o.vy), c = path && path.closest[id];
  const last = path && path.points.length ? path.points[path.points.length - 1].t : s.t;
  // A pass is coming when the path's nearest point to the target is a real low point, not the
  // path's end (#548: a target always just past the end kept the hint switching).
  const pass = c && c.t < last - (currentWord === 'Korjaa' ? 0.5 : 8) && c.d < Math.min(close * 12, 200);
  if (pass && c.d < close) return { word: 'Odota', mark: { x: c.x, y: c.y }, ghost: { id, t: c.t } };
  const left = c ? c.t - s.t : 0;
  const correcting = currentWord === 'Korjaa';
  // Correct only a clear miss, and once begun, until well inside (#548: starting and stopping at
  // the same distance made "Korjaa" and "Odota" take turns without end).
  if (pass && left > 2 && o.apo + R > r2 * 0.85 && (c.d > close * 2 || correcting) && c.d > close * 0.5
    && currentWord !== 'Kiihdytä' && currentWord !== 'Jarruta') {
    const dx = c.at.x - c.x, dy = c.at.y - c.y, miss = c.d - close * 0.4;
    return { word: 'Korjaa', dir: angleOf(dx, dy), power: clamp(miss / left / SHIP.acc * 4, 0.05, 1), ghost: { id, t: c.t } };
  }
  const boosting = currentWord === 'Kiihdytä' && o.apo + R < r2;
  if (pass && !boosting && o.apo + R > r2 * 0.85) return { word: 'Odota', mark: { x: c.x, y: c.y }, ghost: { id, t: c.t } };
  if (o.apo + R < r2 * 0.92 || boosting) {
    const wait = ((aheadOf(target, s, side) - transferLead(o.r, r2, n2)) % TAU + TAU) % TAU;
    if (wait < 0.12 || boosting) {
      return { word: 'Kiihdytä', dir: pro, power: clamp((r2 - o.apo - R) / 60, 0.15, 1) };
    }
    return { word: 'Odota', target: id, wait: wait / Math.abs(Math.sqrt(EARTH.mu / o.r ** 3) - n2) };
  }
  // Up at the target's height with no pass coming: brake at the high point so the low point
  // drops, the ship goes round faster and meets the target at the high point a few rounds on.
  const top = pathExtreme(path, true), atTop = o.alt > o.apo - 12 || (o.closed && o.e < 0.05);
  // Braking at the high point makes the ship's own spot the high point.
  const want = phasingPeri(s, o, atTop || currentWord === 'Jarruta' ? { x: s.x, y: s.y, t: s.t } : top, BODY[id], n2);
  if (want && o.peri + R > want + (currentWord === 'Jarruta' ? 1 : 6) && (atTop || currentWord === 'Jarruta')) {
    return { word: 'Jarruta', dir: pro + Math.PI, power: clamp((o.peri + R - want) / 100, 0.05, 0.4) };
  }
  if (want && o.peri + R > want + 6) return { word: 'Odota', mark: top, target: id };
  return { word: 'Odota', target: id, wait: meetWait(s, o, path, BODY[id], close) };
}
// The low point (distance from Earth's middle) that makes the ship's rounds just as long that,
// a whole number of rounds on, it is back at its high point as the target gets there.
function phasingPeri(s, o, top, b, n2) {
  if (!top || top.t === undefined || !o.closed) return null;
  const R = EARTH.radius, rTop = Math.max(o.apo + R, Math.hypot(top.x, top.y)), low = Math.max(R + 20, rTop * 0.3);
  const tq = bodyAt(b, top.t), side = sideOf(o);
  const gap = ((side * wrap(angleOf(top.x, top.y) - angleOf(tq.x, tq.y))) % TAU + TAU) % TAU;
  const pMin = TAU * Math.sqrt(((low + rTop) / 2) ** 3 / EARTH.mu), pTop = TAU * Math.sqrt(rTop ** 3 / EARTH.mu);
  let best = null;
  for (let m = 0; m < 4; m++) {
    const reach = (gap + m * TAU) / n2; // when the target gets to the high point, after top.t
    for (let k = 1; k <= 4; k++) {
      const p = reach / k;
      if (p >= pMin && p <= pTop && (!best || reach < best.reach)) best = { reach, p };
    }
  }
  if (!best) return low;
  const a = Math.cbrt(EARTH.mu * (best.p / TAU) ** 2);
  return 2 * a - rTop;
}
// Seconds until a round when the ship at its high point and the target are close, if one
// comes within a dozen rounds.
function meetWait(s, o, path, b, close) {
  if (!o.closed) return undefined;
  const top = pathExtreme(path, true);
  if (!top || top.t === undefined) return undefined;
  const a = (o.peri + o.apo) / 2 + EARTH.radius, period = TAU * Math.sqrt(a ** 3 / EARTH.mu);
  let best = null;
  for (let k = 0; k < 12; k++) {
    const t = top.t + k * period, q = bodyAt(b, t), d = Math.hypot(q.x - top.x, q.y - top.y);
    if (!best || d < best.d) best = { d, t };
    if (d < close * 4) break;
  }
  return Math.max(0, best.t - s.t);
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
// The word of the hint before this one, so a burn once begun goes on to its end.
var currentWord = '';
function hint(s = ship, path = null) {
  const h = nextMove(s, path);
  currentWord = h.word;
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
  for (let i = 1; i < pts.length; i++) {
    if (pts[i].t >= t) return pts[i - 1].t <= t ? mixPoints(pts[i - 1], pts[i], (t - pts[i - 1].t) / (pts[i].t - pts[i - 1].t)) : null;
  }
  return null;
}
// A point part way (k from 0 to 1) between two path points.
function mixPoints(a, b, k) {
  const m = (u, v) => u === undefined || v === undefined ? undefined : u + (v - u) * k;
  return { x: m(a.x, b.x), y: m(a.y, b.y), t: m(a.t, b.t), vx: m(a.vx, b.vx), vy: m(a.vy, b.vy) };
}
function nextMove(s, path) {
  if (!s) return { word: '' };
  if (s.phase === 'done') return { word: 'Valmis!' };
  if (s.phase === 'crashed') return { word: 'Rysähti!' };
  if (s.landedOn && s.refuel && s.dv < SHIP.dv) return { word: 'Tankataan', fuel: true };
  // Landed beside the base: a hop toward it.
  if (s.landedOn && s.landedOn.id === 'moon' && landingAim(s) !== undefined && !atBase(s.landedOn.a)) {
    return { word: 'Hyppää', dir: s.landedOn.a + Math.sign(wrap(landingAim(s) - s.landedOn.a)) * 0.6, power: 1, base: true };
  }
  if (TRIP[s.trip].far && s.tanked && s.landedOn && s.landedOn.id === 'moon') {
    const wait = marsWait(s.t);
    if (wait > 0) return { word: 'Odota', wait, window: true };
  }
  if (s.landedOn) return { word: 'Vedä ylös', dir: s.landedOn.a, power: 1 };
  if (TRIP[s.trip].far && (s.tanked || refBody(s) === SUN || refBody(s) === MARS)) return marsHint(s, path);
  // Passing the rock on another trip is just part of the way round Earth.
  const trip = s.trip, ref = refBody(s) === ROCK && trip !== 'kivi' ? EARTH : refBody(s), home = trip === 'kotiin' && s.visited.includes('moon');
  if (trip !== 'kivi' && path && path.hit && path.hit.body === 'rock' && path.hit.t - s.t > 2) {
    // About to hit the rock on the way elsewhere: a small push to the side misses it.
    const o = orbitAround(EARTH, s);
    return { word: 'Korjaa', dir: angleOf(o.vx, o.vy) + Math.PI / 2, power: 0.3 };
  }
  if (ref === EARTH && home) {
    const c = path && path.closest.earth;
    if (orbitAround(EARTH, s).alt < 80 || (path && path.hit && path.hit.body === 'earth')) return landingHint(EARTH, s, path);
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
  if (ref === ROCK) return landingHint(ROCK, s, path);
  // Near the Moon.
  const o = orbitAround(MOON, s), pro = angleOf(o.vx, o.vy), low = pathExtreme(path, false);
  if (home) {
    const c = path && path.closest.earth;
    if (o.alt < 4) return { word: 'Ylös', dir: angleOf(o.x, o.y), power: 1 };
    if (c && c.d < 20) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t } };
    const m = bodyAt(MOON, s.t);
    return { word: 'Kohti Maata', dir: angleOf(-m.vx, -m.vy), power: 1 };
  }
  const aim = landingAim(s);
  if (aim !== undefined) return baseHint(s, path, o, aim);
  // A long oval counts too, but the hint brakes on at the low point until it is round enough for
  // the star (#548: stopping at a fixed height made a near-round orbit brake in short bursts).
  if (trip === 'kuu-kierto' && orbitReady(MOON, s) && (o.e <= 0.2 || (o.alt > o.peri + 6 && currentWord !== 'Jarruta'))) return { word: s.thrust > 0 ? 'Päästä irti' : 'Odota' };
  if (trip !== 'kuu-kierto' && (o.alt < 25 || (o.closed && o.apo <= ORBIT_GOAL.moon.apo))) return landingHint(MOON, s, path);
  if (o.peri < ORBIT_GOAL.moon.peri + (s.thrust > 0 ? 4 : 0) && o.alt > 15 && trip === 'kuu-kierto') {
    return { word: 'Sivulle', dir: angleOf(o.x, o.y) + sideOf(o) * Math.PI / 2, power: 0.5 };
  }
  // A brake begun near the low point goes on past it (#548: stopping as soon as the orbit closed
  // made it brake in bursts, each one moving the low point a little lower).
  if (o.alt < o.peri + 6 || o.alt < 10 || (currentWord === 'Jarruta' && o.alt < o.peri + 20)) return { word: 'Jarruta', dir: pro + Math.PI, power: 1 };
  return { word: 'Odota', mark: low };
}
// To the Moon base: into a low orbit first, then down when the base lies the right way ahead,
// steering the last metres into it.
function baseHint(s, path, o, aim) {
  const pro = angleOf(o.vx, o.vy), hits = path && path.hit && path.hit.body === 'moon';
  if (hits || o.alt < 6 || (o.closed && o.apo < 8)) return landingHint(MOON, s, path, aim);
  if (!orbitReady(MOON, s)) {
    if (o.peri < ORBIT_GOAL.moon.peri + (s.thrust > 0 ? 4 : 0) && o.alt > 15) {
      return { word: 'Sivulle', dir: angleOf(o.x, o.y) + sideOf(o) * Math.PI / 2, power: 0.5 };
    }
    // A brake begun at the low point goes on until the orbit is round enough.
    if (o.alt < o.peri + 6 || o.alt < 10 || (currentWord === 'Jarruta' && o.alt < o.peri + 20)) return { word: 'Jarruta', dir: pro + Math.PI, power: 1 };
    return { word: 'Odota', mark: pathExtreme(path, false) };
  }
  // How far round the base is, the way the ship goes.
  const side = sideOf(o), ahead = ((side * wrap(aim - angleOf(o.x, o.y))) % TAU + TAU) % TAU;
  const from = BASE_LEAD + 0.5, to = BASE_LEAD - 0.5;
  if ((ahead < from && ahead > to) || (s.thrust > 0 && ahead > 0.6)) return { word: 'Jarruta', dir: pro + Math.PI, power: 1, base: true };
  const rate = Math.abs(o.h) / (o.r * o.r);
  return { word: 'Odota', base: true, wait: ((ahead - from) % TAU + TAU) % TAU / rate };
}
// How far ahead of the ship (radians round the Moon) the base is when a full brake from a low
// orbit should start, so the ship comes down about on it.
const BASE_LEAD = 1.9;
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

// ---- Mars (#548) ----
// Mars ahead of Earth round the Sun (radians) when the ship should lift off from the Moon base:
// a half-ellipse from Earth's circle to Mars's, started DEPART seconds later, out of Earth's sphere.
const DEPART = 70;
const MARS_LEAD = (() => {
  const a = (AU + MARS.helio.r) / 2, t = Math.PI * Math.sqrt(a ** 3 / SUN.mu);
  return ((Math.PI - MARS.helio.n * t + (EARTH_HELIO.n - MARS.helio.n) * DEPART) % TAU + TAU) % TAU;
})();
// Seconds until the window opens; 0 while it is open (a few seconds past the best moment).
function marsWait(t) {
  const ahead = MARS.helio.phase + MARS.helio.n * t - EARTH_HELIO.phase - EARTH_HELIO.n * t;
  const early = ((ahead - MARS_LEAD) % TAU + TAU) % TAU;
  if (TAU - early < 0.06) return 0;
  return early / (EARTH_HELIO.n - MARS.helio.n);
}
// How far from the Sun the path will reach once out of Earth's sphere.
function exitReach(path) {
  if (!path || !path.exit) return null;
  return orbitAround(SUN, path.exit).apo + SUN.radius;
}
// The speed past Earth's circle round the Sun (m/s) that reaches Mars's circle.
const MARS_SPEED = Math.sqrt(SUN.mu * (2 / AU - 2 / (AU + MARS.helio.r)));
// How fast the ship will leave Earth (and the Moon first, when near it), from its energy now: it
// changes smoothly while the engine burns, unlike the path, which leaves Earth only once it is fast
// enough (#548: waiting for the path made the push overshoot).
function leavingSpeed(s) {
  let v = Math.hypot(s.vx, s.vy), r = Math.hypot(s.x, s.y);
  if (refBody(s) === MOON) {
    const o = orbitAround(MOON, s), m = bodyAt(MOON, s.t), out = Math.sqrt(Math.max(0, o.speed ** 2 - 2 * MOON.mu / o.r));
    v = Math.hypot(m.vx + o.vx / o.speed * out, m.vy + o.vy / o.speed * out); r = MOON.orbit.r;
  }
  return Math.sqrt(Math.max(0, v * v - 2 * EARTH.mu / r));
}
// Off the Moon and out of Earth's sphere along Earth's own way round the Sun, so the ship swings
// out to Mars's circle; then small corrections until the path passes Mars, and down onto it.
function marsHint(s, path) {
  const ref = refBody(s), close = 150;
  if (ref === MARS) return landingHint(MARS, s, path);
  const c = path && path.closest.mars, last = path && path.points.length ? path.points[path.points.length - 1].t : s.t;
  // The push still missing: from the estimate while pushing, from the path after it.
  const vE = EARTH_HELIO.r * EARTH_HELIO.n, sun = ref === SUN ? orbitAround(SUN, s) : null;
  // Out round the Sun a path that already passes Mars is only corrected, not pushed further.
  const near = c && c.t < last - 1 && c.d < 3000;
  const need = ref === SUN ? (sun.apo + SUN.radius < MARS.helio.r * 0.97 && !near ? MARS.helio.r : 0)
    : MARS_SPEED - vE - leavingSpeed(s);
  const real = exitReach(path);
  const pushing = ref !== SUN && (currentWord === 'Kohti Marsia' ? need > 0 : need > 4 && !(real && real > MARS.helio.r * 0.95));
  if (pushing || (ref === SUN && need > 0)) {
    // Along Earth's way round the Sun as it will be when the ship leaves Earth's sphere.
    const out = path && path.exit ? path.exit.t : s.t + DEPART, e = bodyAt(SUN, out);
    let dir = sun ? angleOf(sun.vx, sun.vy) : angleOf(-e.vx, -e.vy);
    if (ref === MOON) {
      // Never into the Moon: near it, only the sideways part of a downward push.
      const o = orbitAround(MOON, s), up = angleOf(o.x, o.y);
      if (o.alt < 2) return { word: 'Ylös', dir: up, power: 0.5 };
      if (o.alt < 40 && Math.cos(wrap(dir - up)) < 0.3) dir = up + Math.sign(wrap(dir - up)) * (o.alt < 8 ? 1 : 1.27);
    }
    return { word: 'Kohti Marsia', dir, power: sun ? 0.5 : clamp(need / SHIP.acc * 2, 0.1, 1), far: true };
  }
  // Corrections only out round the Sun: near Earth a push bends the way out too much to judge.
  const pass = c && c.t < last - 1;
  const left = c ? c.t - s.t : 0, correcting = currentWord === 'Korjaa';
  if (ref !== SUN) return { word: 'Odota', far: true, wait: path && path.exit ? path.exit.t - s.t : undefined };
  if (pass && c.d < close) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t }, ghost: { id: 'mars', t: c.t } };
  if (pass && left > 8 && (c.d > close * 2 || correcting) && c.d > close * 0.5) {
    const miss = c.d - close * 0.4;
    return { word: 'Korjaa', dir: angleOf(c.at.x - c.x, c.at.y - c.y), power: clamp(miss / left / SHIP.acc * 1.5, 0.05, 0.6), ghost: { id: 'mars', t: c.t } };
  }
  if (pass) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t }, ghost: { id: 'mars', t: c.t } };
  return { word: 'Odota', far: true };
}
