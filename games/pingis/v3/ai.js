'use strict';
// Pingis v1: the computer's bat. It reads the flight like a player: a moment after the ball
// leaves the other bat (its reaction time) it guesses where the ball will cross its hitting
// line, with an error, and moves there no faster than its top speed. A high ball is smashed.

function cpuBrain(level, seed) {
  return { L: LEVELS[level] || LEVELS[1], r: rng(seed), forN: -1, wait: 0, tx: 0, tz: 0, kind: 'drive', aim: 0, serveT: -1 };
}
// Where flight f will cross depth `d` behind `side`'s end after bouncing there, or null.
function predict(f, side, d) {
  const b = Object.assign({}, f.ball), s = sgn(side);
  let bounced = f.bR > 0;
  for (let k = 0; k < 1600 && !b.dead; k++) {
    const pz = b.z, ev = ballStep(b);
    if (ev === (side === 0 ? 'bounce0' : 'bounce1')) bounced = true;
    if (bounced && (pz * s - HL - d) < 0 && (b.z * s - HL - d) >= 0) return { x: b.x, y: b.y, z: b.z };
  }
  return null;
}
// One frame for the computer's bat on `side`. `foe` is the other bat (it aims away from it).
function cpuThink(g, side, bat, brain, foe, dt) {
  const L = brain.L, s = sgn(side), f = g.flight;
  let tx = 0, tz = s * (HL + 0.5);
  if (f && !f.over && f.by !== side && !f.ball.dead) {
    if (brain.forN !== f.n || brain.forR !== g.r) {
      brain.forN = f.n; brain.forR = g.r; brain.wait = L.react * (0.8 + brain.r() * 0.4);
      const d = 0.22 + brain.r() * 0.2, p = predict(f, side, d);
      // Off the bat's middle by its error; now and then it misjudges the ball altogether.
      const slip = brain.r() < L.miss ? (brain.r() < 0.5 ? -1 : 1) * (CPU_REACH + 0.05) : 0;
      brain.plan = p ? { x: p.x + gauss(brain.r) * L.err * 0.6 + slip, z: s * (HL + d), y: p.y } : null;
      const high = p && p.y > L.smash;
      brain.kind = high ? 'smash' : brain.r() < L.drive ? 'drive' : 'block';
      // Away from the other bat, with a wobble.
      brain.aim = clamp(-Math.sign(foe.x || brain.r() - 0.5) * L.aim + gauss(brain.r) * 0.3, -1, 1);
    }
    if (brain.wait > 0) brain.wait -= dt;
    else if (brain.plan) { tx = brain.plan.x; tz = brain.plan.z; }
    else { tx = bat.x; tz = bat.z; }
    if (brain.wait > 0) { tx = bat.x; tz = bat.z; }
  } else if (g.ph === 'serve' && g.sv === side) { tx = 0.25 * s; tz = s * (HL + 0.3); }
  const mx = L.speed * dt, dx = tx - bat.x, dz = tz - bat.z, d = Math.hypot(dx, dz);
  const k = d > mx ? mx / d : 1;
  bat.x += dx * k; bat.z += dz * k;
}
// The computer serves a moment after it may.
function cpuServes(g, side, brain, dt) {
  if (g.ph !== 'serve' || g.sv !== side || g.wait > 0) { brain.serveT = -1; return false; }
  if (brain.serveT < 0) brain.serveT = 0.5 + brain.r() * 0.5;
  brain.serveT -= dt;
  return brain.serveT <= 0;
}
