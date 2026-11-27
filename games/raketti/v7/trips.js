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
  // The Mars base (v6): each part flies the Mars trip in the big rocket, down into the base on top
  // of Mars. The finished base fills the tank for the way home.
  { id: 'asunto', name: 'Asuinmoduuli Marsiin', goal: 'Vie asuinmoduuli Marsin tukikohtaan', fuel: 0.4, tank: 0.4, far: true, rocket: 'jatti', part: true, on: 'mars' },
  { id: 'kasvihuone', name: 'Kasvihuone Marsiin', goal: 'Vie kasvihuone Marsin tukikohtaan', fuel: 0.4, tank: 0.4, far: true, rocket: 'jatti', part: true, on: 'mars' },
  { id: 'marstehdas', name: 'Polttoainetehdas Marsiin', goal: 'Vie tehdas Marsin tukikohtaan', fuel: 0.4, tank: 0.4, far: true, rocket: 'jatti', part: true, on: 'mars' },
  { id: 'marsista', name: 'Marsista kotiin', goal: 'Tankkaa Marsissa ja laskeudu Maahan', fuel: 0.3, tank: 0.1, far: true, rocket: 'jatti', fromMars: true },
];
const TRIP = Object.fromEntries(TRIPS.map(t => [t.id, t]));
// An orbit counts once its lowest point is this high and its highest this low (heights in m).
// Mars's (v6) is where its parts circle before coming down into its base.
const ORBIT_GOAL = { earth: { peri: 10, apo: 150 }, moon: { peri: 3, apo: 80 }, mars: { peri: 5, apo: 80 } };

// The parts built so far: a part trip flown once. A part goes to the Moon base, or `on` Mars.
function baseBuilt(id) { return (stars[id] || 0) >= 1; }
function partOn(t) { return t.part ? t.on || 'moon' : null; }
function baseReady(on = 'moon') { return TRIPS.every(t => partOn(t) !== on || baseBuilt(t.id)); }
function atBase(a) { return Math.abs(wrap(a - BASE.a)) < BASE.zone; }
function atMarsBase(a) { return Math.abs(wrap(a - MARS_BASE.a)) < MARS_BASE.zone; }
// Where on the Moon this trip should land, if anywhere in particular: a Moon part's base, or the
// Moon base's fuel on the way to Mars.
function landingAim(s) { return partOn(TRIP[s.trip]) === 'moon' || (TRIP[s.trip].far && !TRIP[s.trip].fromMars && !s.tanked) ? BASE.a : undefined; }
// Where on Mars: the Mars base, for its parts, and on the trip home until the tank is full.
function marsAim(s) { return partOn(TRIP[s.trip]) === 'mars' || (TRIP[s.trip].fromMars && !s.tanked) ? MARS_BASE.a : undefined; }
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
    case 'mars': return !!s.landedOn && s.landedOn.id === 'mars' && s.tanked; // the goal says: fill up at the base first
    case 'asunto': case 'kasvihuone': case 'marstehdas':
      return !!s.landedOn && s.landedOn.id === 'mars' && s.tanked && atMarsBase(s.landedOn.a);
    case 'marsista': return !!s.landedOn && s.landedOn.id === 'earth';
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
// The speed at distance r from b's middle, flying level, whose orbit's other end is rOther away.
function apseSpeed(b, r, rOther) { return Math.sqrt(b.mu * Math.max(0, 2 / r - 2 / (r + rOther))); }
// What a brake near the Moon still has to take off its speed (m/s): down to an orbit the trip
// takes, round enough for the Moon-orbit trip, within its highest point for a landing.
function moonBrakeGap(o, trip, b = MOON) {
  // Mars's brake aims well inside its goal (v6): one aimed at the goal's edge ended there, and the
  // next turn round needed another short brake, and another.
  const apo = b === MARS ? ORBIT_GOAL.mars.apo * 0.7 : ORBIT_GOAL[b.id].apo;
  const want = trip === 'kuu-kierto' ? Math.sqrt(MOON.mu * 1.2 / o.r) : apseSpeed(b, o.r, apo + b.radius);
  return o.speed - want;
}
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
    return { word: 'Jarruta', dir: angleOf(vx, vy) + Math.PI, power: 0.4, speed: b, gap: Math.abs(x * vy - y * vx) / (alt + b.radius) - apseSpeed(b, alt + b.radius, b.radius) };
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
// With `ahead`, the next one the ship comes to, not the one it is just leaving (v7: on the
// station trip, rising from the low point, "Odota" waited for that low point, 0 s away, so the
// game stayed in slow motion and the wait could not be skipped).
function pathExtreme(path, high, ahead = false) {
  if (!path || !path.points.length) return null;
  const f = bodyAt(path.frame, ship ? ship.t : 0);
  let best = null, bestR = high ? -Infinity : Infinity, leaving = ahead, lastR;
  for (const p of path.points) {
    const r = Math.hypot(p.x - f.x, p.y - f.y);
    if (leaving) {
      if (lastR === undefined || (high ? r < lastR : r > lastR)) { lastR = r; continue; }
      leaving = false;
    }
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
    return { word: 'Korjaa', dir: angleOf(dx, dy), power: clamp(miss / left / SHIP.acc * 4, 0.05, 1), ghost: { id, t: c.t }, gap: c.d - close, metres: true };
  }
  // Far higher than the target goes, with no pass coming: down to a low orbit, and from there again.
  // A brake begun near the low point (only this one is) goes on until the orbit is round.
  if (!pass && o.closed && (o.apo + R > r2 * 1.12 || (currentWord === 'Jarruta' && o.alt < o.peri + 20 && o.alt < o.apo - 12))) {
    const h = startOverHint(s, path, o, id);
    if (o.apo + R > r2 * 1.12 || h.word === 'Jarruta') return h;
  }
  const boosting = currentWord === 'Kiihdytä' && o.apo + R < r2;
  if (pass && !boosting && o.apo + R > r2 * 0.85) return { word: 'Odota', mark: { x: c.x, y: c.y }, ghost: { id, t: c.t } };
  if (o.apo + R < r2 * 0.92 || boosting) {
    const wait = ((aheadOf(target, s, side) - transferLead(o.r, r2, n2)) % TAU + TAU) % TAU;
    if (wait < 0.12 || boosting) {
      return { word: 'Kiihdytä', dir: pro, power: clamp((r2 - o.apo - R) / 60, 0.15, 1), gap: apseSpeed(EARTH, o.r, r2) - o.speed };
    }
    return { word: 'Odota', target: id, wait: wait / Math.abs(Math.sqrt(EARTH.mu / o.r ** 3) - n2) };
  }
  // Up at the target's height with no pass coming: brake at the high point so the low point
  // drops, the ship goes round faster and meets the target at the high point a few rounds on.
  const top = pathExtreme(path, true), atTop = o.alt > o.apo - 12 || (o.closed && o.e < 0.05);
  // Braking at the high point makes the ship's own spot the high point.
  const want = phasingPeri(s, o, atTop || currentWord === 'Jarruta' ? { x: s.x, y: s.y, t: s.t } : top, BODY[id], n2);
  if (want && o.peri + R > want + (currentWord === 'Jarruta' ? 1 : 6) && (atTop || currentWord === 'Jarruta')) {
    return { word: 'Jarruta', dir: pro + Math.PI, power: clamp((o.peri + R - want) / 100, 0.05, 0.4), gap: o.peri + R - want - 1, metres: true };
  }
  if (want && o.peri + R > want + 6) return { word: 'Odota', mark: top, target: id };
  // No meeting within a dozen rounds, and the low point too low to brake for one (#548: after a far
  // climb the ship waited for a meeting that never came): down to a low orbit, and from there again.
  const meet = meetAhead(s, o, path, BODY[id], close);
  if (meet && meet.d > close * 4 && !pass) return startOverHint(s, path, o, id);
  return { word: 'Odota', target: id, wait: meet ? Math.max(0, meet.t - s.t) : undefined };
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
// The round (its time t and the distance d) when the ship at its high point and the target come
// closest, within a dozen rounds.
function meetAhead(s, o, path, b, close) {
  if (!o.closed) return null;
  const top = pathExtreme(path, true);
  if (!top || top.t === undefined) return null;
  const a = (o.peri + o.apo) / 2 + EARTH.radius, period = TAU * Math.sqrt(a ** 3 / EARTH.mu);
  let best = null;
  for (let k = 0; k < 12; k++) {
    const t = top.t + k * period, q = bodyAt(b, t), d = Math.hypot(q.x - top.x, q.y - top.y);
    if (!best || d < best.d) best = { d, t };
    if (d < close * 4) break;
  }
  return best;
}
// Seconds until a closed orbit round Earth is at its low point.
function untilLow(o) {
  const a = (o.peri + o.apo) / 2 + EARTH.radius, e = o.e;
  if (!o.closed || !(e > 1e-3)) return 0;
  const n = Math.sqrt(EARTH.mu / a ** 3), E = Math.acos(clamp((1 - o.r / a) / e, -1, 1)), M = E - e * Math.sin(E);
  return o.vr < 0 ? M / n : (TAU - M) / n;
}
// Brake at an end of the orbit until its other end is rOther from Earth's middle: at the high
// point while the low point is above rOther (lowering it), else at the low point. Otherwise wait
// for that end. The wait comes from the orbit, as the end may lie past the path's end (#548: the
// wait then read as the path's length and did not count down). Braking at an end keeps the ship
// at that end, so the burn holds until it is done.
function brakeAtLow(s, path, o, rOther, extra) {
  const gap = o.speed - apseSpeed(EARTH, o.r, rOther), atHigh = o.peri + EARTH.radius > rOther + 15;
  const near = atHigh ? o.alt > o.apo - 6 : o.alt < o.peri + 6 || (currentWord === 'Jarruta' && o.alt < o.peri + 20);
  if (gap > 0 && near) return { word: 'Jarruta', dir: angleOf(o.vx, o.vy) + Math.PI, power: 0.5, gap };
  let wait = untilLow(o);
  if (atHigh && o.closed) {
    const a = (o.peri + o.apo) / 2 + EARTH.radius, period = TAU * Math.sqrt(a ** 3 / EARTH.mu);
    wait = (wait + period / 2) % period;
  }
  const last = path && path.points.length ? path.points[path.points.length - 1].t - s.t : 0;
  return Object.assign({ word: 'Odota', wait, mark: wait < last - 1 ? pathExtreme(path, atHigh) : undefined }, extra);
}
// Off the way to a target (#548): down to a low point 40 m up, and there round, from where the
// timed push toward the target starts again.
function startOverHint(s, path, o, id) {
  return brakeAtLow(s, path, o, Math.min(o.r, EARTH.radius + 40), { target: id });
}
// From the pad into a low orbit around Earth.
function ascentHint(s, path) {
  // The way round the station and the Moon go, except on the first trip, where any orbit counts
  // (#548: an orbit the wrong way round never met them).
  const o = orbitAround(EARTH, s), up = angleOf(o.x, o.y), side = s.trip === 'kiertorata' ? sideOf(o) : 1;
  if (o.alt < 5 && o.apo < 25) return { word: 'Ylös', dir: up, power: 1 };
  if (o.apo < 40) return { word: 'Vinosti ylös', dir: up + side * 1.05, power: 1 };
  if (o.vr < 1.5 || o.alt > o.apo - 3 || (s.thrust > 0 && o.alt > o.apo - 12)) return { word: 'Sivulle', dir: up + side * Math.PI / 2, power: 1, gap: apseSpeed(EARTH, o.r, ORBIT_GOAL.earth.peri + EARTH.radius) + side * o.h / o.r };
  return { word: 'Odota', mark: pathExtreme(path, true) };
}
// ---- Back on the way (#548: an orbit the wrong way round, or a push so hard the ship flew off,
// left the hint saying "Odota" for ever). ----
// The speed round Earth (m/s) the ship has the right way, clockwise as the station and the Moon go.
function rightWay(o) { return -o.h / o.r; }
// A push toward a speed (vx, vy round Earth): the hint turns the ship and pushes until it has it.
function matchHint(word, s, vx, vy) {
  const dx = vx - s.vx, dy = vy - s.vy, gap = Math.hypot(dx, dy);
  return { word, dir: angleOf(dx, dy), power: clamp(gap / SHIP.acc * 2, 0.15, 1), gap };
}
// Flying the wrong way round Earth: turn round into a circle the right way at this height.
// Low down it climbs too while it turns, as the ship falls while its speed round is gone (#548:
// the slow cargo rocket hit the ground turning at 15 m); it never pushes down.
function turnRoundHint(s) {
  const o = orbitAround(EARTH, s), v = Math.sqrt(EARTH.mu / o.r), up = Math.max(o.vr, clamp((40 - o.alt) * 0.5, 0, 12));
  return matchHint('Käänny', s, o.y / o.r * v + up * o.x / o.r, -o.x / o.r * v + up * o.y / o.r);
}
// Flying away from Earth: a speed that falls back to a low point 40 m up, the right way round, and
// from outside Earth's pull (which does not reach out there) toward Earth too.
function comeBackHint(s) {
  const o = orbitAround(EARTH, s), r = o.r, rp = EARTH.radius + 40, out = r > EARTH.sphere * 0.85;
  // The first trip takes either way round: keep the ship's own.
  const way = s.trip === 'kiertorata' ? sideOf(o) : 1;
  // Keep the fall it already has (#548: aiming for none, a ship falling home hovered until its tank
  // was empty); out past 85 % of the pull, fall at 8 m/s at least.
  const k = Math.max(out ? 8 : 0, -o.vr), vt = r > rp ? rp * Math.sqrt((k * k + 2 * EARTH.mu * (1 / rp - 1 / r)) / (r * r - rp * rp)) : Math.sqrt(EARTH.mu / r);
  return matchHint(r > EARTH.sphere ? 'Kohti Maata' : 'Jarruta', s, -k * o.x / r + way * vt * o.y / r, -k * o.y / r - way * vt * o.x / r);
}
function lostHint(s, ref) {
  if (ref !== EARTH && ref !== SUN) return null;
  const o = orbitAround(EARTH, s), R = EARTH.radius, far = EARTH.sphere * 0.85;
  // Away: past Earth's pull, or on a way that does not come back, or comes back only from beyond it.
  if (o.r > far || (o.vr > 0 && (!o.closed || o.apo + R > far))) {
    const h = comeBackHint(s);
    if (h.gap > (currentWord === h.word ? 0.3 : 1)) return h;
    if (ref === SUN) return { word: 'Odota' };
  }
  // Either way round is fine on the first trip, and on the way home, which only lands.
  const home = s.trip === 'kotiin' && s.visited.includes('moon');
  if (ref === EARTH && s.trip !== 'kiertorata' && !home && o.speed > 2 && (rightWay(o) < -1 || currentWord === 'Käänny')) {
    const h = turnRoundHint(s);
    if (rightWay(o) < -1 || h.gap > 0.5) return h;
  }
  return null;
}
// The hint, and for a wait, how many seconds until the next thing to do (when that is known:
// a window opening, the path's high or low point, the closest pass). A tap on "Odota" skips it.
// The word of the hint before this one, so a burn once begun goes on to its end.
var currentWord = '';
// The burn under way: its word and how far it had to go when it began (#548: players could not
// tell a burn was nearly done and pushed past its end).
var burn = null;
// The game seconds of push the burn's rate is measured over.
const RATE_SPAN = 0.1;
function hint(s = ship, path = null) {
  const h = nextMove(s, path);
  currentWord = h.word;
  // How much of a burn is left, from 1 when it begins to 0 at its end. Each burn hint gives `gap`,
  // what it still has to do in its own measure (m/s of push where it can, else metres).
  // How fast the gap has closed over the last moment of push gives the game seconds until the
  // burn ends at the push held now. Over a moment, not a frame, as a gap read off the path moves
  // only when the path is drawn again (#548: rates from frame to frame made a correction crawl).
  // A burn asked for once its gap is already closed (a hint holding on) shows no bar.
  if (h.dir !== undefined && Number.isFinite(h.gap) && (h.gap > 0 || (burn && burn.word === h.word))) {
    if (!burn || burn.word !== h.word || h.gap > burn.gap) burn = { word: h.word, gap: h.gap, seen: [] };
    if (!(s.thrust > 0)) burn.seen = [];
    else {
      burn.seen.push({ t: s.t, gap: h.gap });
      while (burn.seen.length > 2 && s.t - burn.seen[1].t > RATE_SPAN) burn.seen.shift();
    }
    // Until the gap has moved, a push in m/s per second closes a gap in m/s at that rate; a gap in
    // metres waits for a measured rate.
    const f = burn.seen[0], seen = f && s.t > f.t ? (f.gap - h.gap) / (s.t - f.t) : 0, rate = seen > 0 ? seen : h.metres ? 0 : s.thrust;
    h.left = clamp(h.gap / burn.gap, 0, 1);
    if (rate > 0) h.ends = Math.max(0, h.gap) / rate;
  } else burn = null;
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
  if (s.landedOn && s.landedOn.id === 'mars' && marsAim(s) !== undefined && !atMarsBase(s.landedOn.a)) {
    return { word: 'Hyppää', dir: s.landedOn.a + Math.sign(wrap(MARS_BASE.a - s.landedOn.a)) * 0.6, power: 1, base: true };
  }
  if (TRIP[s.trip].far && s.tanked && s.landedOn && s.landedOn.id === 'moon') {
    const wait = marsWait(s.t);
    if (wait > 0) return { word: 'Odota', wait, window: true };
  }
  if (TRIP[s.trip].fromMars && s.tanked && s.landedOn && s.landedOn.id === 'mars') {
    const wait = homeWait(s.t);
    if (wait > 0) return { word: 'Odota', wait, window: true };
  }
  if (s.landedOn) return { word: 'Vedä ylös', dir: s.landedOn.a, power: 1 };
  // Off Mars before the tank is full: back down into the base to fill up.
  if (TRIP[s.trip].fromMars) return s.tanked || refBody(s) !== MARS ? homeHint(s, path) : marsHint(s, path);
  if (!(TRIP[s.trip].far && s.tanked) && !(s.trip === 'kotiin' && refBody(s) === MOON)) {
    const lost = lostHint(s, refBody(s) === ROCK && s.trip !== 'kivi' ? EARTH : refBody(s));
    if (lost) return lost;
  }
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
    // Only the speed round Earth goes, so the ship keeps falling; once its orbit comes down to the
    // ground it waits (#548: braking the fall too, a ship far out, whose 90 s path does not reach
    // Earth, stopped and hovered until its tank was empty).
    const o = orbitAround(EARTH, s);
    if (o.peri < 10 && o.vr < 0) return { word: 'Odota', mark: pathExtreme(path, false) };
    const out = o.vr / o.r;
    return { word: 'Jarruta', dir: angleOf(-(o.vx - out * o.x), -(o.vy - out * o.y)), power: 0.6 };
  }
  const nearStation = trip === 'asema' && stationClose(s);
  // Up at the station's height, a low point under the orbit goal is the station hint's to raise
  // (v7: a brake past its aim handed the ship to the climb's "Sivulle", which pushed it back up,
  // and the station hint braked again, over and over). A climb already under way goes on.
  const eo = ref === EARTH ? orbitAround(EARTH, s) : null;
  const stationHigh = trip === 'asema' && !!eo && eo.closed && eo.apo + EARTH.radius > STATION.r - 8 && (eo.peri > 2 || eo.alt > eo.apo - 4) && !['Sivulle', 'Vinosti ylös', 'Ylös'].includes(currentWord);
  if (ref === EARTH && !nearStation && !stationHigh && eo.peri < ORBIT_GOAL.earth.peri) return ascentHint(s, path);
  if (ref === EARTH) {
    if (trip === 'kiertorata') {
      // Too high for the goal: brake at the low point until the high point is low enough.
      const o = orbitAround(EARTH, s), top = ORBIT_GOAL.earth.apo + EARTH.radius - 15;
      if (o.closed && o.apo > ORBIT_GOAL.earth.apo) return brakeAtLow(s, path, o, top);
      return { word: s.thrust > 0 ? 'Päästä irti' : 'Odota' };
    }
    if (trip === 'asema') return stationHint(s, path);
    if (trip === 'kivi') return transferHint(s, path, bodyAt(ROCK, s.t), ROCK.orbit.r, ROCK.orbit.n, 6, 'rock');
    return transferHint(s, path, bodyAt(MOON, s.t), MOON.orbit.r, MOON.orbit.n, 25, 'moon');
  }
  if (ref === ROCK) return landingHint(ROCK, s, path);
  // Near the Moon.
  const o = orbitAround(MOON, s), pro = angleOf(o.vx, o.vy), low = pathExtreme(path, false);
  if (home) {
    const c = path && path.closest.earth;
    // Up clear of the ground first (#548: turning toward Earth 4 m up, the ship fell back on the Moon).
    if (o.alt < 4 || (currentWord === 'Ylös' && o.alt < 15)) return { word: 'Ylös', dir: angleOf(o.x, o.y), power: 1 };
    if (c && c.d < 20) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t } };
    // Against the Moon's way round; low down, never into the ground (#548: from a landing on the
    // Moon's far side, that push took the ship straight back down).
    const m = bodyAt(MOON, s.t), mv = Math.hypot(m.vx, m.vy), ux = -m.vx / mv, uy = -m.vy / mv;
    const rx = o.x / o.r, ry = o.y / o.r, lift = o.alt < 30 ? Math.max(0, 0.5 - (ux * rx + uy * ry)) : 0;
    return { word: 'Kohti Maata', dir: angleOf(ux + lift * rx, uy + lift * ry), power: 1 };
  }
  const aim = landingAim(s);
  if (aim !== undefined) return baseHint(s, path, o, aim);
  // A long oval counts too, but the hint brakes on at the low point until it is round enough for
  // the star (#548: stopping at a fixed height made a near-round orbit brake in short bursts).
  if (trip === 'kuu-kierto' && orbitReady(MOON, s) && (o.e <= 0.2 || (o.alt > o.peri + 6 && currentWord !== 'Jarruta'))) return { word: s.thrust > 0 ? 'Päästä irti' : 'Odota' };
  if (trip !== 'kuu-kierto' && (o.alt < 25 || (o.closed && o.apo <= ORBIT_GOAL.moon.apo))) return landingHint(MOON, s, path);
  // Low down and already slow, a brake only hovers (#548: a ship that came in low braked on until
  // its fuel ran out): sideways then too, at full push.
  const slow = moonBrakeGap(o, trip) <= 0;
  if (o.peri < ORBIT_GOAL.moon.peri + (s.thrust > 0 ? 4 : 0) && (o.alt > 15 || slow) && trip === 'kuu-kierto') {
    return { word: 'Sivulle', dir: angleOf(o.x, o.y) + sideOf(o) * Math.PI / 2, power: o.alt > 15 ? 0.5 : 1, gap: ORBIT_GOAL.moon.peri + 4 - o.peri, metres: true };
  }
  // A brake begun near the low point goes on past it (#548: stopping as soon as the orbit closed
  // made it brake in bursts, each one moving the low point a little lower).
  if (o.alt < o.peri + 6 || o.alt < 10 || (currentWord === 'Jarruta' && o.alt < o.peri + 20)) return { word: 'Jarruta', dir: pro + Math.PI, power: 1, gap: moonBrakeGap(o, trip) };
  return { word: 'Odota', mark: low };
}
// To the Moon base: into a low orbit first, then down when the base lies the right way ahead,
// steering the last metres into it.
// The same way down into the Mars base (v6), with b = MARS.
function baseHint(s, path, o, aim, b = MOON) {
  const pro = angleOf(o.vx, o.vy), hits = path && path.hit && path.hit.body === b.id;
  // Mars's low orbit may pass 5 m up (v6): its base brake, not the landing, starts there.
  if (hits || o.alt < (b === MARS ? 3 : 6) || (b === MARS && o.peri < 0) || (o.closed && o.apo < 8)) return landingHint(b, s, path, aim);
  const pro0 = pro + Math.PI, down = Math.abs(o.h) / o.r - apseSpeed(b, o.r, b.radius);
  // Mars's base brake begins from an orbit only just above its lowest (v6): it goes on to its end,
  // not back to the low orbit's own checks as soon as the lowest point dips.
  if (b === MARS && currentWord === 'Jarruta' && s.t - baseBrakeAt < 0.2 && down > 0) {
    baseBrakeAt = s.t;
    return { word: 'Jarruta', dir: pro0, power: 1, base: true, gap: down };
  }
  // Mars's capture brake, aimed inside the goal, runs to its end even once the goal is met.
  const capture = b === MARS && currentWord === 'Jarruta' && s.thrust > 0 && s.t - baseBrakeAt > 0.2 && o.alt > 10;
  if (!orbitReady(b, s) || (capture && moonBrakeGap(o, s.trip, b) > 0)) {
    const slow = moonBrakeGap(o, s.trip, b) <= 0;
    // The margin holds only for a push already going sideways: a brake's own thrust must not turn
    // it into "Sivulle" and back each frame (#548).
    const g = ORBIT_GOAL[b.id];
    if (o.peri < g.peri + (s.thrust > 0 && currentWord === 'Sivulle' ? 4 : 0) && (o.alt > 15 || slow)) {
      return { word: 'Sivulle', dir: angleOf(o.x, o.y) + sideOf(o) * Math.PI / 2, power: o.alt > 15 ? 0.5 : 1, gap: g.peri + 4 - o.peri, metres: true };
    }
    // A brake begun at the low point goes on until the orbit is round enough.
    // Mars's arrival comes in slowly from high above it (v6): a brake begun before the low point
    // only moves the low point further down and on, so it waits for the low point itself; once
    // begun, the ship's spot is the new high point, and the brake goes on in one burn.
    const going = currentWord === 'Jarruta' && (o.alt < o.peri + 20 || (b === MARS && o.alt > o.apo - 20));
    const low = o.alt < o.peri + 6 && (b !== MARS || o.vr > -0.3);
    // Mars's last trims are a few tenths of a m/s: a gentler push, so they do not end in a frame.
    const gap = moonBrakeGap(o, s.trip, b), power = b === MARS ? clamp(gap / SHIP.acc * 3, 0.1, 1) : 1;
    if (!slow && (low || o.alt < 10 || going)) return { word: 'Jarruta', dir: pro + Math.PI, power, gap };
    return { word: 'Odota', mark: pathExtreme(path, false) };
  }
  // How far round the base is, the way the ship goes.
  const side = sideOf(o), ahead = ((side * wrap(aim - angleOf(o.x, o.y))) % TAU + TAU) % TAU;
  const lead = b === MARS ? MARS_BASE_LEAD : BASE_LEAD, from = lead + 0.5, to = lead - 0.5;
  if ((ahead < from && ahead > to) || (b === MOON && s.thrust > 0 && ahead > 0.6)) {
    baseBrakeAt = s.t;
    return { word: 'Jarruta', dir: pro0, power: 1, base: true, gap: down };
  }
  const rate = Math.abs(o.h) / (o.r * o.r);
  return { word: 'Odota', base: true, wait: ((ahead - from) % TAU + TAU) % TAU / rate };
}
// How far ahead of the ship (radians round the Moon) the base is when a full brake from a low
// orbit should start, so the ship comes down about on it.
const BASE_LEAD = 1.9, MARS_BASE_LEAD = 1.9;
let baseBrakeAt = -Infinity;
// Station: a transfer to its height, then close in slowly with the arrow.
// Close enough to aim at the station: within 30 m, or 45 m while an aimed push's flight to it is
// under way.
function stationClose(s) {
  const d = stationRelative(s).dist;
  return d < 30 || (!!approach && approach.tArr > s.t - 1 && d < 45);
}
function crossesStation(o) {
  const R = EARTH.radius;
  return o.peri + R < STATION.r + 8 && (!o.closed || o.apo + R > STATION.r - 8);
}
// The last metres to the station: one push in one direction that sends the ship falling to the
// station, slowly enough to dock, then a wait while it gets there. A few tens of metres up here
// curve the ship's way a lot, so "straight at the station" turned while the push was held (v7:
// "Kohti asemaa" changed direction in the middle of a push, and passing over the station it threw
// the orbit 65 m up). The push is worked out on the ship's own falling path, and its direction
// stays put until it is done; a push held too long or let go of early is mended by one more.
let approach = null;
const APPROACH = { times: [4, 5, 6, 8, 10, 13, 16], arrive: 1.8, settle: 1.5, done: 0.03 };
function approachHint(s) {
  const going = !!approach && currentWord === 'Kohti asemaa' && approach.tArr > s.t + 0.3
    && (approach.pushed || s.t - approach.t0 < 0.4);
  if (going) {
    if (s.thrust > 0) approach.pushed = true;
    const p = interceptPush(s, approach.tArr);
    const gap = p ? p.ux * Math.sin(approach.dir) + p.uy * Math.cos(approach.dir) : 0;
    if (gap > APPROACH.done) return { word: 'Kohti asemaa', dir: approach.dir, power: clamp(gap / 8, 0.05, 1), gap, station: true };
    approach.ended = s.t;
  }
  const dock = coastDock(s);
  if (dock && dock.speed < STATION.speed - 0.4) return { word: 'Odota', station: true, wait: dock.t - s.t };
  // Just after a push, while it is being let go of: no new one at once.
  if (approach && (s.t - approach.ended < APPROACH.settle || (s.thrust > 0 && !going))) {
    return { word: 'Odota', station: true, wait: Math.max(0, approach.tArr - s.t) };
  }
  let best = null;
  for (const T of APPROACH.times) {
    const p = interceptPush(s, s.t + T);
    if (!p) continue;
    const score = p.dv + 0.1 * T + (p.arrive > APPROACH.arrive ? 10 + p.arrive : 0);
    if (!best || score < best.score) best = Object.assign(p, { T, score });
  }
  if (!best) return { word: 'Odota', station: true };
  approach = { tArr: s.t + best.T, dir: angleOf(best.ux, best.uy), t0: s.t, pushed: false, ended: -Infinity };
  if (best.dv < 0.15) { approach.ended = s.t; return { word: 'Odota', station: true, wait: best.T }; }
  return { word: 'Kohti asemaa', dir: approach.dir, power: clamp(best.dv / 8, 0.05, 1), gap: best.dv, station: true };
}
// Falling round Earth from (x, y) at (vx, vy) for T game seconds; `each` sees every step and may
// stop it by returning true.
function coast(x, y, vx, vy, t, T, each) {
  const n = Math.max(1, Math.round(T * 60)), dt = T / n;
  for (let k = 0; k < n; k++) {
    let a = pull(EARTH, x, y);
    vx += a.ax * dt / 2; vy += a.ay * dt / 2; x += vx * dt; y += vy * dt;
    a = pull(EARTH, x, y); vx += a.ax * dt / 2; vy += a.ay * dt / 2; t += dt;
    if (each && each(x, y, vx, vy, t)) break;
  }
  return { x, y, vx, vy, t };
}
// When (and how fast) the ship, left alone, reaches the station within `T` game seconds.
function coastDock(s, T = 20) {
  let hit = null;
  coast(s.x, s.y, s.vx, s.vy, s.t, T, (x, y, vx, vy, t) => {
    const q = stationAt(t);
    if (Math.hypot(x - q.x, y - q.y) < STATION.dock - 0.3) hit = { t, speed: Math.hypot(vx - q.vx, vy - q.vy) };
    return !!hit;
  });
  return hit;
}
// The push (m/s across, ux, and up, uy) after which the ship falls to the station's middle at
// game time tArr, its size, and how fast the ship then meets the station.
function interceptPush(s, tArr) {
  const T = tArr - s.t, q = stationAt(tArr);
  if (T <= 0) return null;
  const end = (ux, uy) => coast(s.x, s.y, s.vx + ux, s.vy + uy, s.t, T);
  let ux = 0, uy = 0;
  for (let i = 0; i < 4; i++) {
    const e = end(ux, uy), ex = e.x - q.x, ey = e.y - q.y;
    if (Math.hypot(ex, ey) < 0.05) break;
    const h = 0.1, a = end(ux + h, uy), b = end(ux, uy + h);
    const j11 = (a.x - e.x) / h, j21 = (a.y - e.y) / h, j12 = (b.x - e.x) / h, j22 = (b.y - e.y) / h, det = j11 * j22 - j12 * j21;
    if (Math.abs(det) < 1e-9) return null;
    ux -= (j22 * ex - j12 * ey) / det; uy -= (j11 * ey - j21 * ex) / det;
  }
  const e = end(ux, uy);
  if (Math.hypot(e.x - q.x, e.y - q.y) > 0.5) return null;
  return { ux, uy, dv: Math.hypot(ux, uy), arrive: Math.hypot(e.vx - q.vx, e.vy - q.vy) };
}
function stationHint(s, path) {
  if (stationClose(s)) return approachHint(s);
  const o = orbitAround(EARTH, s), st = stationAt(s.t), side = sideOf(o);
  if (o.apo + EARTH.radius < STATION.r - 2) {
    // Just under the station's height, both go round about as fast, so the moment for a timed
    // climb can be minutes away and drifts (v7: "Odota" for ever, an orbit a few metres under the
    // station's): climb now, and the meeting is lined up from up there.
    const near = o.apo + EARTH.radius > STATION.r - 14;
    const wait = ((aheadOf(st, s, side) - transferLead(o.r, STATION.r, STATION.n)) % TAU + TAU) % TAU;
    if (near && (o.alt < o.peri + 4 || currentWord === 'Kiihdytä' || o.e < 0.05)) return { word: 'Kiihdytä', dir: angleOf(o.vx, o.vy), power: 0.15, gap: STATION.r - 2 - (o.apo + EARTH.radius), metres: true };
    if (near) return stationWait(s, path, pathExtreme(path, false, true));
    if (wait < 0.12 || s.thrust > 0) {
      const gap = apseSpeed(EARTH, o.r, STATION.r - 2) - o.speed;
      return { word: 'Kiihdytä', dir: angleOf(o.vx, o.vy), power: clamp(gap / 6, 0.05, 0.3), gap };
    }
    return { word: 'Odota', station: true, wait: wait / Math.abs(Math.sqrt(EARTH.mu / o.r ** 3) - STATION.n) };
  }
  const R = EARTH.radius, hiOff = Math.abs(o.apo + R - STATION.r), loOff = Math.abs(o.peri + R - STATION.r);
  // Neither the high nor the low point at the station's height: at the low point, brake the high
  // point down to it.
  if (hiOff > 6 && loOff > 6) {
    // As strong as the brake is big (v7: 0.3 m/s asked for at 0.3, let go of a little late, put
    // the low point under the ground).
    // A brake under way goes on to its end, though it already moved the low point (v7: from a
    // far round orbit each brake stopped at once, the next came half a round later, and the ship
    // drifted into the Moon's pull).
    const gap = o.speed - apseSpeed(EARTH, o.r, STATION.r + 2);
    if ((o.alt < o.peri + 6 && gap > 0.05) || (currentWord === 'Jarruta' && gap > 0)) {
      return { word: 'Jarruta', dir: angleOf(o.vx, o.vy) + Math.PI, power: clamp(gap / 6, 0.05, 0.3), gap };
    }
    return stationWait(s, path, pathExtreme(path, false, true));
  }
  // One end of the orbit at the station's height, the station elsewhere on its circle (#548: an
  // orbit like the station's never meets it): there, brake or push to make the other end lower or
  // higher, so the ship goes round just as much slower or faster that, a whole number of rounds
  // on, it is back there as the station gets there. The meeting is worked out afresh each time
  // from the orbit as it is, so a push held too long or let go late only picks another meeting
  // (v7: a brake past its aim left a low point no meeting fitted, and the hints went round in a
  // loop until the tank was empty).
  const high = hiOff <= loOff, end = pathExtreme(path, high, true);
  const going = !!phaseBurn && phaseBurn.word === currentWord && s.t - phaseBurn.t < 0.5;
  const there = (high ? o.alt > o.apo - 4 : o.alt < o.peri + 4) || (o.closed && o.e < 0.05);
  const at = there || going ? { x: s.x, y: s.y, t: s.t } : end, plan = stationMeetings(o, high, at);
  // A meeting counts only on an orbit of the kind they are planned on (v7: a brake from 540 m up
  // stopped half way, at a far end that met the station by chance minutes later, and the ship
  // waited until the Moon pulled it away).
  const miss = plan && plan.other >= R + STATION_MEET.below - 1 && plan.other <= STATION.r + STATION_MEET.above + 1 ? plan.miss : Infinity;
  if (going && (!plan || miss < STATION_MEET.end)) { phaseBurn = null; phaseEnd = s.t; }
  if (!plan || miss < (going ? STATION_MEET.end : STATION_MEET.start)) return stationWait(s, path, end, plan ? at.t + plan.when : undefined);
  // Not straight after a burn, while the push is still being let go of (v7: a burn ended, and a
  // late let-go asked at once for one back the other way, and so on).
  // One burn at each pass (on a round orbit, each part of a round), unless the low point is too
  // low for comfort.
  // Too low a low point gets only the short pause (v7: with none, a brake pushed twice as hard as
  // asked was answered at once by a push back, again twice too hard, and so on).
  const round = o.peri > ORBIT_GOAL.earth.peri ? TAU / 3 * Math.sqrt(((o.peri + o.apo) / 2 + R) ** 3 / EARTH.mu) : 0;
  const settleEnd = phaseEnd + Math.max(STATION_MEET.settle, round);
  const settling = s.t < settleEnd || (s.thrust > 0 && !going);
  if (!going && !there) return stationWait(s, path, end);
  if (!going && settling) return stationWait(s, path, end, s.thrust > 0 ? undefined : settleEnd);
  // A burn under way keeps its way, lower or higher, and aims at the best meeting that way.
  const down = going ? phaseBurn.word === 'Jarruta' : null;
  let best = null;
  for (const c of plan.meets) {
    if (down === true && c.other > plan.other - 0.5 || down === false && c.other < plan.other + 0.5) continue;
    if (!best || c.cost < best.cost) best = c;
  }
  if (!best) { phaseBurn = null; phaseEnd = s.t; return { word: 'Odota', station: true, mark: end }; }
  const brake = best.other < plan.other, gap = Math.abs(plan.other - best.other);
  phaseBurn = { word: brake ? 'Jarruta' : 'Kiihdytä', t: s.t };
  return { word: phaseBurn.word, dir: angleOf(o.vx, o.vy) + (brake ? Math.PI : 0), power: clamp(gap / 100, 0.05, 0.4), gap: gap - 0.5, metres: true, station: true };
}
// The phasing burn under way on the station trip (its word and when it was last asked for), and
// when the last one ended.
let phaseBurn = null, phaseEnd = -Infinity;
// How close (metres along the station's circle) a coming meeting must be for the hint to wait
// for it: closer than `start` before a burn, and a burn goes on until it is closer than `end`.
// After a burn, the next waits `settle` game seconds and a third of a round at least.
// Waiting on the station trip: until the ship comes within reach of the station on its drawn
// path (on an orbit that comes to the station's height; passing over or under it is no meeting), else until `until` (game seconds) or the point `mark`. Never a wait of a moment that
// never passes (v7: on a round orbit the next high point is always "now", so the game ran in slow
// motion, the wait could not be skipped, and a meeting minutes away looked like nothing happening).
function stationWait(s, path, mark, until) {
  if (path && crossesStation(orbitAround(EARTH, s))) {
    for (const p of path.points) {
      const q = stationAt(p.t);
      if (Math.hypot(p.x - q.x, p.y - q.y) < 25) return { word: 'Odota', station: true, wait: Math.max(0, p.t - s.t), mark: p };
    }
  }
  if (until !== undefined && until > s.t) return { word: 'Odota', station: true, wait: until - s.t };
  if (mark && mark.t !== undefined && mark.t - s.t > 1) return { word: 'Odota', station: true, mark };
  return { word: 'Odota', station: true };
}
const STATION_MEET = { start: 12, end: 3, settle: 1.5, above: 40, below: 35, round: 4 };
// The meetings with the station from the ship's end of the orbit at the station's height (high
// end or low end; at the point `at`). `other`, how far the other end is from Earth's middle now;
// `when`, game seconds from `at` to that closest meeting; `meets`, the other ends (`other`) that bring ship and station back there together a whole
// number of rounds on, with a `cost` (metres of change, and `round` more for each round); `miss`,
// how far apart the two get there on the orbit as it is now, within its next four rounds.
function stationMeetings(o, high, at) {
  if (!at || at.t === undefined || !o.closed) return null;
  const R = EARTH.radius, n = STATION.n, rAt = high ? o.apo + R : o.peri + R, other = high ? o.peri + R : o.apo + R;
  const q = stationAt(at.t), side = sideOf(o);
  const gap = ((side * wrap(angleOf(at.x, at.y) - angleOf(q.x, q.y))) % TAU + TAU) % TAU;
  const period = a => TAU * Math.sqrt(a ** 3 / EARTH.mu);
  const pMin = period((R + STATION_MEET.below + rAt) / 2), pMax = period(rAt + STATION_MEET.above / 2);
  const pNow = period((o.peri + o.apo) / 2 + R), meets = [];
  let miss = Infinity, when;
  for (let k = 1; k <= 4; k++) {
    const d = STATION.r * Math.abs(wrap(n * k * pNow - gap));
    if (d < miss) { miss = d; when = k * pNow; }
    for (let m = 0; m <= 4; m++) {
      const p = (gap + m * TAU) / n / k;
      if (p < pMin || p > pMax) continue;
      const c = 2 * Math.cbrt(EARTH.mu * (p / TAU) ** 2) - rAt;
      meets.push({ other: c, cost: Math.abs(c - other) + STATION_MEET.round * k });
    }
  }
  return { miss, when, meets, other };
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
  if (ref === MARS) return marsAim(s) === undefined ? landingHint(MARS, s, path) : baseHint(s, path, orbitAround(MARS, s), marsAim(s), MARS);
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
    return { word: 'Kohti Marsia', dir, power: sun ? 0.5 : clamp(need / SHIP.acc * 2, 0.1, 1), far: true,
      gap: sun ? MARS.helio.r * 0.97 - sun.apo - SUN.radius : need, metres: !!sun };
  }
  // Corrections only out round the Sun: near Earth a push bends the way out too much to judge.
  const pass = c && c.t < last - 1;
  const left = c ? c.t - s.t : 0, correcting = currentWord === 'Korjaa';
  if (ref !== SUN) return { word: 'Odota', far: true, wait: path && path.exit ? path.exit.t - s.t : undefined };
  if (pass && c.d < close) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t }, ghost: { id: 'mars', t: c.t } };
  if (pass && left > 8 && (c.d > close * 2 || correcting) && c.d > close * 0.5) {
    const miss = c.d - close * 0.4;
    return { word: 'Korjaa', dir: angleOf(c.at.x - c.x, c.at.y - c.y), power: clamp(miss / left / SHIP.acc * 1.5, 0.05, 0.6), ghost: { id: 'mars', t: c.t }, gap: c.d - close, metres: true };
  }
  if (pass) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t }, ghost: { id: 'mars', t: c.t } };
  return { word: 'Odota', far: true };
}

// ---- From Mars home (v6) ----
// Earth ahead of Mars round the Sun (radians) when the ship should lift off from the Mars base: a
// half-ellipse from Mars's circle in to Earth's, started HOME_DEPART seconds later, out of Mars's sphere.
const HOME_DEPART = 45;
const HOME_TIME = Math.PI * Math.sqrt(((AU + MARS.helio.r) / 2) ** 3 / SUN.mu);
const EARTH_LEAD = ((Math.PI + MARS.helio.n * HOME_DEPART - EARTH_HELIO.n * (HOME_DEPART + HOME_TIME)) % TAU + TAU) % TAU;
// The speed (m/s) the ship must leave Mars with, against Mars's way round the Sun, to fall in to
// Earth's circle.
const HOME_SPEED = MARS.helio.r * MARS.helio.n - Math.sqrt(SUN.mu * (2 / MARS.helio.r - 2 / (AU + MARS.helio.r)));
function earthAhead(t) {
  return ((EARTH_HELIO.phase + EARTH_HELIO.n * t - MARS.helio.phase - MARS.helio.n * t - EARTH_LEAD) % TAU + TAU) % TAU;
}
// Seconds until the window home opens; 0 while it is open (a few seconds past the best moment).
function homeWait(t) {
  const late = earthAhead(t);
  if (late < 0.06) return 0;
  return (TAU - late) / (EARTH_HELIO.n - MARS.helio.n);
}
// The trip home starts this long before its window opens: time to fill the tank.
const HOME_LEAD_TIME = 20;
function homeStart() { return homeWait(0) + (homeWait(0) < HOME_LEAD_TIME ? TAU / (EARTH_HELIO.n - MARS.helio.n) : 0) - HOME_LEAD_TIME; }
// How fast the ship will leave Mars, from its energy now.
function leavingMars(s) {
  const o = orbitAround(MARS, s);
  return Math.sqrt(Math.max(0, o.speed ** 2 - 2 * MARS.mu / o.r));
}
// Up off Mars and out of its sphere against its way round the Sun, so the ship falls in to Earth's
// circle; then small corrections until the path passes Earth, and down onto it as from the Moon.
function homeHint(s, path) {
  // Aimed at Earth's sphere, not at Earth: inside it Earth's pull bends the path so much that the
  // closest pass jumps (a path that hits Earth ends there), and the landing hints take over there.
  const ref = refBody(s), close = 600;
  const c = path && path.closest.earth, last = path && path.points.length ? path.points[path.points.length - 1].t : s.t;
  if (ref === MARS) {
    const o = orbitAround(MARS, s), up = angleOf(o.x, o.y), need = HOME_SPEED - leavingMars(s);
    if (need > (currentWord === 'Kohti Maata' ? 0 : 1)) {
      // Against Mars's way round the Sun; near the ground, never into it.
      const m = onCircle(MARS.helio, s.t);
      let dir = angleOf(-m.vx, -m.vy);
      if (o.alt < 3) return { word: 'Ylös', dir: up, power: 1 };
      if (o.alt < 40 && Math.cos(wrap(dir - up)) < 0.3) dir = up + Math.sign(wrap(dir - up)) * (o.alt < 10 ? 1 : 1.27);
      return { word: 'Kohti Maata', dir, power: clamp(need / SHIP.acc * 2, 0.1, 1), far: true, gap: need };
    }
    return { word: 'Odota', far: true };
  }
  if (ref === EARTH) {
    if (orbitAround(EARTH, s).alt < 80 || (path && path.hit && path.hit.body === 'earth')) return landingHint(EARTH, s, path);
    if (c && c.d < 20) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t } };
    const o = orbitAround(EARTH, s);
    if (o.peri < 10 && o.vr < 0) return { word: 'Odota', mark: pathExtreme(path, false) };
    // Only the speed round Earth goes, so the ship keeps falling in (as from the Moon).
    const out = o.vr / o.r;
    return { word: 'Jarruta', dir: angleOf(-(o.vx - out * o.x), -(o.vy - out * o.y)), power: 0.6 };
  }
  // Round the Sun: down to Earth's circle first, then corrections until the path passes Earth.
  // A path that meets Earth ends there: it passes Earth all the same.
  const onEarth = path && path.hit && path.hit.body === 'earth';
  if (onEarth) return { word: 'Odota', mark: { x: path.hit.x, y: path.hit.y, t: path.hit.t }, ghost: { id: 'earth', t: path.hit.t } };
  const sun = orbitAround(SUN, s), near = c && c.t < last - 1 && c.d < 3000;
  const high = sun.peri + SUN.radius - AU * 1.03;
  // Once the path passes Earth, corrections go on until it does again: no flipping back.
  if (!near && currentWord !== 'Korjaa' && (high > 0 || (currentWord === 'Kohti Maata' && high > -AU * 0.02))) {
    return { word: 'Kohti Maata', dir: angleOf(-sun.vx, -sun.vy), power: 0.5, far: true, gap: high + AU * 0.02, metres: true };
  }
  const pass = c && c.t < last - 1, left = c ? c.t - s.t : 0, correcting = currentWord === 'Korjaa';
  if (pass && c.d < close) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t }, ghost: { id: 'earth', t: c.t } };
  if (pass && left > 8 && (c.d > close * 2 || correcting) && c.d > close * 0.5) {
    const miss = c.d - close * 0.4;
    return { word: 'Korjaa', dir: angleOf(c.at.x - c.x, c.at.y - c.y), power: clamp(miss / left / SHIP.acc * 1.5, 0.05, 0.6), ghost: { id: 'earth', t: c.t }, gap: c.d - close, metres: true };
  }
  if (pass) return { word: 'Odota', mark: { x: c.x, y: c.y, t: c.t }, ghost: { id: 'earth', t: c.t } };
  return { word: 'Odota', far: true };
}
