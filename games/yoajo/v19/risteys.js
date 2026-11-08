// Yöajo v14 (#440 "Why not also exits and intersections where you need to turn"): the route turns.
// Legs 1–2 leave the motorway by an exit ramp, and from leg 3 Valtatie 4 turns left or right at a
// crossroads. The road straight on carries on as a side road of its own: drive into it and it is
// the wrong road, which ends the leg 250 m on (Eero's choice). Blue signs 600 m and 150 m before,
// an arrow on the screen, and the blinker comes on by itself (no buttons, Eero's choice). A left
// turn crosses the lane of a car coming from the road ahead: turning within 4 s of it is unsafe.
// Everything is top-level, as in game.js.

// How many turns each leg has, legs 1–11. Legs 1–2 turn off the motorway, the rest at crossroads.
const TURNS = [1, 1, 1, 1, 2, 2, 3, 3, 1, 1, 1];   // v15: Lapland's legs 9–11
// A left crossroads has an 8 m corner inside the junction, taken at about 18 km/h.
// The wider right-hand corner turns a quarter round on a radius of 28 m: above about 40 km/h on a dry road the car
// slides wide (game.js's bend rule). An exit ramp bends 0.6 rad on 70 m: fine at 50–60.
const LEFT_RADIUS = 8, LEFT_EASE = 2, LEFT_SPEED = 18;
const TURN_KIND = { ramppi: { R: 70, angle: 0.6 }, risteys: { R: 28, angle: Math.PI / 2 } };
// The bend comes on over TURN_EASE metres; by its end the driver has turned or gone straight on.
const TURN_EASE = 8;
// Straight road before and after each turn, metres.
const TURN_BEFORE = 140, TURN_AFTER = 100;
// Signs SIGN_FAR and SIGN_NEAR metres before; the leg ends WRONG_LEN metres into the wrong road.
const SIGN_FAR = 600, SIGN_NEAR = 150, WRONG_LEN = 250;
// The straight-on road is drawn ARM_LEN metres on, the crossing road STUB_LEN metres the other way.
const ARM_LEN = 320, STUB_LEN = 70;
// A left turn within GAP_TIME s of the car coming from the road ahead is unsafe; it drives ARM_V.
const GAP_TIME = 4, ARM_V = 50 / KMH;
// The blinker blinks BLINK_T s on, as long off; it comes on within BLINK_FROM metres of the turn.
const BLINK_T = 0.4, BLINK_FROM = 150;
// Where the road straight on leads, legs 1–11: the second line of the blue signs.
const STRAIGHT_ON = ['Lahti', 'Heinola', 'Mikkeli', 'Jämsä', 'Viitasaari', 'Kokkola', 'Kemi', 'Kemijärvi', 'Pelkosenniemi', 'Kittilä', 'Karigasniemi'];

// ---- Placing the turns (from newLeg, right after makeRoad) ----
// Each turn bends the road itself: TURN_BEFORE metres made straight, the bend, TURN_AFTER metres
// straight, and the road beyond as it was. Then the road is laid out again from its bends.
// v16: a stage of the endless night says how many turns it has (leg.turns).
function turnLeg() {
  road.turns = [];
  const r = rng(leg.seed * 23 + 9), n = leg.turns != null ? leg.turns : TURNS[level - 1] || 0, kind = level <= 2 ? 'ramppi' : 'risteys', span = (leg.len - 1300) / Math.max(1, n);
  for (let k = 0; k < n; k++) {
    const a0 = Math.round((750 + span * (k + 0.4 + r() * 0.2)) / SEG) * SEG, { R, angle } = TURN_KIND[kind];
    // A ramp leaves to the right; a crossroads turns back towards where the trip heads, else by turns.
    const th = road.TH[Math.round(a0 / SEG)];
    let dir = kind === 'ramppi' ? 1 : (k + level) % 2 ? -1 : 1;
    if (kind === 'risteys' && Math.abs(th) > 0.5) dir = -Math.sign(th);
    // The old 28 m left arc crossed the opposing lane long before the cross-road mouth.
    // Keep the crossing inside that mouth, entering from the right-hand approach lane.
    const radius = kind === 'risteys' && dir < 0 ? LEFT_RADIUS : R;
    const ease = kind === 'risteys' && dir < 0 ? LEFT_EASE : TURN_EASE;
    const len = angle * radius + ease, a1 = a0 + Math.round(len / SEG) * SEG;
    for (let i = Math.round((a0 - TURN_BEFORE) / SEG); i <= Math.round((a1 + TURN_AFTER) / SEG) && i < road.n; i++) {
      const s = i * SEG, e = clamp(Math.min((s - a0) / ease, (a1 - s) / ease), 0, 1);
      road.K[i] = s > a0 && s < a1 ? dir / radius * e : 0;
    }
    // The arc's curvature sums a little short of `angle` on the grid: scale it to turn exactly.
    let sum = 0; for (let i = Math.round(a0 / SEG); i <= Math.round(a1 / SEG); i++) sum += road.K[i] * SEG;
    if (sum) for (let i = Math.round(a0 / SEG); i <= Math.round(a1 / SEG); i++) road.K[i] *= angle * dir / sum;
    // Level ground through the turn, so the roads meet flat; 60 m to blend into the hills.
    const y0 = road.Y[Math.round(a0 / SEG)], f0 = a0 - TURN_BEFORE, f1 = a1 + TURN_AFTER;
    for (let i = Math.max(0, Math.round((f0 - 60) / SEG)); i <= Math.round((f1 + 60) / SEG) && i < road.n; i++) {
      const s = i * SEG, w = clamp(Math.min((s - f0 + 60) / 60, (f1 + 60 - s) / 60), 0, 1);
      road.Y[i] = lerp(road.Y[i], y0, w * w * (3 - 2 * w));
    }
    layOut();
    road.turns.push({ a0, a1, dir, kind, R: radius, to: leg.to, on: STRAIGHT_ON[level - 1] || '', told: 0, done: false, spawned: false, waited: false, unsafe: false });
  }
  for (const J of road.turns) {
    frameTurn(J);
    // Blue direction signs SIGN_FAR and SIGN_NEAR metres before, on the side it turns to.
    for (const d of [SIGN_FAR, SIGN_NEAR]) road.signs.push({ s: J.a0 - d, kind: 'suunta', dir: J.dir, ramp: J.kind === 'ramppi', to: J.to, on: J.on });
  }
}
// After the road events are placed (tie.js): a far blue sign standing in one's stretch moves to just
// past it, or before it when that would leave it nearer the turn than 200 m.
function turnSigns() {
  for (const J of road.turns) for (const sg of road.signs) {
    if (sg.kind !== 'suunta' || sg.s !== J.a0 - SIGN_FAR) continue;
    const t = road.taken.find(([x0, x1]) => sg.s > x0 - 10 && sg.s < x1 + 10 && x1 < J.a0 - 200);
    if (t) sg.s = t[1] + 10 < J.a0 - 200 ? t[1] + 10 : t[0] - 10;
  }
}
// The road's heading and place from its bends (as in makeRoad; the heights stay).
function layOut() {
  let x = 0, z = 0, th = 0;
  for (let j = 0; j < road.n; j++) {
    road.TH[j] = th; road.X[j] = x; road.Z[j] = z;
    th += road.K[j] * SEG; x += Math.sin(th) * SEG; z -= Math.cos(th) * SEG;
  }
}
// Where a turn is in the world: the straight-on road from the turn's start along its heading, and
// for a crossroads the crossing road through the corner, `C` metres along the straight-on road.
function frameTurn(J) {
  const [x, , z] = worldAt(J.a0, 0), th = headingAt(J.a0), e = worldAt(J.a1, 0);
  Object.assign(J, { x, z, y: heightAt(J.a0), th, fx: Math.sin(th), fz: -Math.cos(th), rx: Math.cos(th), rz: Math.sin(th) });
  J.C = (e[0] - x) * J.fx + (e[2] - z) * J.fz;
  // The pieces of road to draw, each a line [x0, z0, x1, z1] in the world.
  const p = (al, lat) => { const q = armAt(J, al, lat); return [q[0], q[2]]; };
  J.arms = [[...p(0, 0), ...p(ARM_LEN, 0)]];
  if (J.kind === 'risteys') J.arms.push([...p(J.C, -J.dir * STUB_LEN), ...p(J.C, J.dir * (Math.hypot(e[0] - x, e[2] - z) * 0.75))]);
}
// A point on the straight-on road: `along` metres past the turn's start, `lat` to its right.
// Before the turn's start it is the road itself (straight there).
function armAt(J, along, lat, up) {
  const y = along < 0 ? heightAt(J.a0 + along) : J.y;
  return [J.x + J.fx * along + J.rx * lat, y + (up || 0), J.z + J.fz * along + J.rz * lat];
}
// The turn whose bend is at s (from its start to its end), or null.
function turnAt(s) { return (road.turns || []).find(J => s >= J.a0 && s <= J.a1) || null; }
// The next turn not yet behind the car.
function turnAhead() { return (road.turns || []).find(J => P.s <= J.a1) || null; }
// How far a point in the world is from the nearest drawn straight-on or crossing road (metres).
function armDist(px, pz) {
  let best = 1e9;
  for (const J of road.turns || []) for (const [x0, z0, x1, z1] of J.arms) {
    const dx = x1 - x0, dz = z1 - z0, u = clamp(((px - x0) * dx + (pz - z0) * dz) / (dx * dx + dz * dz), 0, 1);
    best = Math.min(best, Math.hypot(x0 + dx * u - px, z0 + dz * u - pz));
  }
  return best;
}
// The speed a car may take a turn at, m/s, braking towards it from where it is (cruise in game.js).
function turnCruise(s) {
  let v = 1e9;
  for (const J of road.turns || []) {
    const safe = (J.kind === 'risteys' ? (J.dir < 0 ? LEFT_SPEED : 30) : 50) / KMH * Math.min(1, WEATHER[leg.weather].grip + 0.25);
    const d = s < J.a0 ? J.a0 - s : s > J.a1 ? s - J.a1 : 0;
    v = Math.min(v, Math.sqrt(safe * safe + 2 * 2.5 * d));
  }
  return v;
}

// ---- The player at a turn (from drive in game.js) ----
// The speed the car is too fast for the turn at, km/h (for the hints).
function turnTick(dt) {
  const J = turnAhead();
  P.signal = 0;
  if (!J) return;
  const d = J.a0 - P.s, side = J.dir > 0 ? 'oikealle' : 'vasemmalle';
  // v19 (#451): the speed is on the turn pill the whole way (turnHint), not in this one message.
  if (J.told < 1 && d < SIGN_FAR) { J.told = 1; say(`Käänny ${side} ${Math.round(d / 10) * 10} m`, true); }
  // The car coming from the road ahead at a left turn, released so that it is there about when the player is.
  // It sets off as far up its road as it takes the player to reach the turn at the speed the turn
  // is taken at (turnCruise), so the two meet there unless one of them waits.
  const eta = d / Math.max(P.v, 30 / KMH) + 2;
  if (J.kind === 'risteys' && J.dir < 0 && !J.spawned && d < 200 && J.C + ARM_V * eta < ARM_LEN - 10) {
    J.spawned = true;
    add('risteava', { s: J.a0 + J.C + ARM_V * eta, lat: -LANE, v: -ARM_V, arm: J, colour: J.a0 % 5, high: false, passed: true });
  }
  // The blinker: on as the car slows for the turn or steers into it, off once round or gone past.
  const into = (P.steer || 0) * J.dir > 0.1;
  if (d < BLINK_FROM && (into || P.v * KMH < (J.kind === 'risteys' ? 60 : 80) || P.s >= J.a0)) P.signal = J.dir;
  // Waiting for the car from the road ahead to go by first.
  const coming = things.filter(t => t.arm === J && t.kind === 'risteava' && t.s - J.a0 > J.C - 2);
  if (d > -2 && d < 40 && P.v < 1 && coming.length) J.waited = true;
  if (!J.done && P.s >= J.a0 + TURN_EASE) {
    J.done = true;
    // Steered into the turn over the last stretch: round it. Otherwise straight on, the wrong road.
    if (!P.into) { P.wrong = { J, s0: P.s }; P.signal = 0; say('Väärä tie!', false); return; }
    if (J.kind === 'risteys' && J.dir < 0) {
      const close = coming.find(t => (t.s - J.a0 - J.C) / Math.max(1, -t.v) < GAP_TIME);
      if (close) {
        J.unsafe = true; close.yieldT = 3; tally.hurjastelu++;
        if (typeof honkSound === 'function') honkSound();
        score(-50, 'Käännyit vastaantulijan eteen');
        if (policeSaw('Poliisi pysäytti: vaarallinen käännös.')) return;
      } else if (J.waited) { tally.kaannos = (tally.kaannos || 0) + 1; score(20, 'Annoit tietä'); }
    }
  }
  // Whether the car has steered into the turn lately (from TURN_EASE metres before its start on).
  if (d > TURN_EASE + 25) P.into = false;
  else if (into) P.into = true;
}
// On the wrong road: the car drives on straight, the rest of the leg waits, and WRONG_LEN metres on
// the leg ends (from drive in game.js, instead of everything after the car's own move).
function wrongRoad(dt) {
  const w = P.wrong;
  for (const t of things) move(t, dt);
  for (const t of things) if (t.arm === w.J && t.s > w.J.a0 && meet(t, dt)) return;
  if (P.s - w.s0 >= WRONG_LEN) crash('Väärä tie: ajoit ohi käännöksen.');
}
// v19 (#451 "Risteykseen ajaminen menee todella herkästi ojaan"): the speed a player may take a turn
// at, km/h, in this weather (as turnCruise scales the traffic's). Shown on the
// turn pill and named on the crash screen. Rounded to the nearest 5 (down to 5 gave 20 in a
// blizzard, needlessly slow).
const TURN_SAFE = { vasen: 30, oikea: 50, ramppi: 55 };
function turnWay(J) { return J.kind === 'ramppi' ? 'ramppi' : J.dir < 0 ? 'vasen' : 'oikea'; }
function turnSafe(J) {
  return Math.round(TURN_SAFE[turnWay(J)] * Math.min(1, WEATHER[leg.weather].grip + 0.25) / 5) * 5;
}
// v19 (#451): in a crossroads bend the car is pushed wide smoothly with speed, instead of v18's
// v²/R push that slid at once past about 22 km/h in the 8 m left corner. At the safe speed the push
// matches full steering, but the bend is short: a player who steers in within half a second drifts
// about 1.5 m wide at the safe speed and still makes a dry left turn at about 35 km/h. Null outside
// a crossroads bend (ramps and the road's own bends keep the v²/R rule).
function turnPush(s, v, steerMax) {
  const J = !P.wrong && turnAt(s);
  if (!J || J.kind !== 'risteys') return null;
  const e = clamp(curveAt(s) * J.R * J.dir, 0, 1), safe = turnSafe(J) / KMH;
  return -J.dir * e * steerMax * (v / safe) * (v / safe);
}
// v19 (#451): the junction's drawn paving is road: within JUNCTION_NEAR metres of a crossroads
// bend the car is in the ditch only once it is off every road drawn there too.
const JUNCTION_NEAR = 30;
function onJunction(s, lat) {
  if (P && P.wrong) return false;
  const J = (road.turns || []).find(J => J.kind === 'risteys' && s > J.a0 - JUNCTION_NEAR && s < J.a1 + JUNCTION_NEAR);
  if (!J) return false;
  const q = worldAt(s, lat);
  return armDist(q[0], q[2]) < DITCH;
}
// Off the road in a turn's bend is too fast for it. v19: names the kind of turn (crashTurn keeps it
// for the crash screen's tip).
let crashTurn = null;
function ditchWhy() {
  const J = !P.wrong && turnAt(P.s - 4);
  crashTurn = null;
  if (!J || P.v * KMH <= turnSafe(J)) return 'Ajoit ojaan.';
  const way = turnWay(J);
  crashTurn = { way, safe: turnSafe(J) };
  return `Ajoit ojaan: liian lujaa ${way === 'ramppi' ? 'rampille' : way === 'vasen' ? 'vasempaan käännökseen' : 'oikeaan käännökseen'}.`;
}
// The car from the road ahead at a left turn (from move in game.js). It stops at the crossing
// only as an emergency response to an unsafe turn; normal oncoming traffic keeps priority.
// Once through the crossing it is an ordinary oncoming car.
function crosser(t, dt) {
  const J = t.arm, along = t.s - J.a0;
  let v = ARM_V;
  if (t.yieldT > 0) t.yieldT -= dt;
  if (t.yieldT > 0 && along > J.C + 6) v = Math.min(v, Math.sqrt(2 * 5 * Math.max(0, along - J.C - 10)));
  t.v += clamp(-v - t.v, -2.5 * dt, 6 * dt);
  t.s += t.v * dt;
  // Past the crossing it is on the player's road: no longer on the arm, so it is hit and drawn there.
  if (t.s < J.a0 - 2) { t.kind = 'vastaan'; t.arm = null; t.habit = 0; t.base = cruise(t); }
}
// What the screen shows for the next turn: { dir, d, to } from SIGN_FAR metres before, or null.
function turnHint() {
  if (P.wrong) return { wrong: true };
  const J = turnAhead();
  if (!J || J.a0 - P.s > SIGN_FAR) return null;
  return { dir: J.dir, d: Math.max(0, Math.round((J.a0 - P.s) / 10) * 10), to: J.to, kind: J.kind, safe: turnSafe(J) };
}
// Where the player's car (and the camera) is in the world: on the wrong road, along it.
function carAt(s, lat, up) { return P && P.wrong ? armAt(P.wrong.J, s - P.wrong.J.a0, lat, up) : worldAt(s, lat, up); }
function carHeading(s) { return P && P.wrong && s > P.wrong.J.a0 - TURN_BEFORE ? P.wrong.J.th : headingAt(s); }
