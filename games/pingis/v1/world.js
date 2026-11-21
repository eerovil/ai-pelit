'use strict';
// Pingis v1: the table, the ball and the rules, in plain numbers. Nothing here draws or listens.
//
// Metres and seconds of "game time" (real time × SLOW: a real rally is too quick for a thumb).
// The table top is y = 0, the net at z = 0. Side 0 plays at the +z end, side 1 at the -z end;
// alone you are side 0, with friends the host is side 0 and the guest side 1. A phone's camera
// sits behind its own end, so the world is the same on both phones and only the view turns.
//
// A flight is one launch (a serve or a hit) until it is hit back or ends a point. It is stepped
// in fixed steps from its launch state, rounded the same way on both phones, so one launch gives
// the same bounces everywhere. Only the phone the ball flies towards judges it (net.js).

const TAU = Math.PI * 2;
const HL = 1.37, HW = 0.7625, NET_H = 0.1525, BR = 0.02;   // half length, half width, net, ball radius
const G = 9.8, E = 0.88, FLOOR = -0.76, SLOW = 0.56, STEP = 1 / 240;
const REACH = 0.36;            // how far from the bat's middle (sideways) a ball still meets it
const DEPTH = 0.4;             // how far past the bat's line a ball just bounced still meets it
const CPU_REACH = 0.26;        // the computer's bat is narrower: the wider one is for a thumb
const POINTS = 11;
const LEVELS = [
  { name: 'Helppo', note: 'Kone palauttaa rauhassa', react: 0.3, speed: 1.5, err: 0.24, miss: 0.15, aim: 0.35, smash: 0.42, drive: 0.15 },
  { name: 'Keskitaso', note: 'Kone tähtää kulmiin', react: 0.2, speed: 2.1, err: 0.11, miss: 0.045, aim: 0.55, smash: 0.33, drive: 0.4 },
  { name: 'Vaikea', note: 'Kone lyö kovaa', react: 0.12, speed: 2.8, err: 0.05, miss: 0.012, aim: 0.8, smash: 0.24, drive: 0.85 },
];
const sgn = side => side === 0 ? 1 : -1;          // which way is "my end" for a side
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const r4 = v => Math.round(v * 1e4) / 1e4;
function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}
function gauss(r) { return (r() + r() + r() - 1.5) / 0.5; }   // about -3..3, mostly -1..1

// ---- The ball ----
// A launch: [x, y, z, vx, vy, vz, sp], rounded, sp the topspin (+) or backspin (-).
function launchOf(b) { return [b.x, b.y, b.z, b.vx, b.vy, b.vz, b.sp].map(r4); }
function ballFrom(a) { return { x: a[0], y: a[1], z: a[2], vx: a[3], vy: a[4], vz: a[5], sp: a[6], t: 0, dead: false }; }
// One fixed step. Returns what happened: 'bounce0' / 'bounce1' (on that side's half), 'net',
// 'floor', or null.
function ballStep(b) {
  if (b.dead) return null;
  const h = STEP, pz = b.z;
  b.vy -= G * h;
  b.x += b.vx * h; b.y += b.vy * h; b.z += b.vz * h; b.t += h;
  let ev = null;
  // The net: crossing z = 0 below the tape stops the ball; clipping the tape slows it.
  if ((pz > 0) !== (b.z > 0) && Math.abs(b.x) < HW + 0.15 && b.y < NET_H + BR) {
    if (b.y < NET_H - 0.025) { b.z = pz > 0 ? BR : -BR; b.vz *= -0.12; b.vx *= 0.3; b.vy = Math.min(b.vy, 0); }
    else { b.vz *= 0.55; b.vy = Math.abs(b.vy) * 0.6 + 0.4; }
    ev = 'net';
  }
  // The table top.
  if (b.y < BR && b.vy < 0 && Math.abs(b.x) <= HW + BR && Math.abs(b.z) <= HL + BR) {
    b.y = BR; b.vy = -b.vy * E;
    b.vz *= 1 + 0.16 * b.sp; b.vx *= 0.96; b.sp *= 0.5;
    ev = b.z > 0 ? 'bounce0' : 'bounce1';
  }
  if (b.y < FLOOR + BR || b.t > 5) { b.dead = true; ev = 'floor'; }
  return ev;
}

// ---- A flight and its judge ----
function newFlight(n, by, serve, launch) {
  return { n, by, serve, launch, ball: ballFrom(launch), bBy: 0, bR: 0, over: null, hit: false, held: false };
}
// What an event means for the flight: { w: side that won the point } or null. The judge is the
// receiving side, 1 - f.by, and only that phone calls this to decide (others only draw).
function judge(f, ev) {
  if (!ev || ev === 'net' || f.over) return null;
  const by = f.by, R = 1 - by;
  if (ev === 'floor') return { w: f.bR >= 1 ? by : R };
  const s = ev === 'bounce0' ? 0 : 1;
  if (f.serve && f.bBy === 0 && f.bR === 0) {
    if (s === by) { f.bBy = 1; return null; }
    return { w: R };                         // a serve must bounce on the server's side first
  }
  if (s === R) { f.bR++; return f.bR >= 2 ? { w: by } : null; }
  return { w: R };                           // back on the hitter's side (off the net)
}
// The receiver may hit it: once bounced on their half, flying towards their end.
const hittable = f => !f.over && f.bR === 1 && f.ball.vz * sgn(1 - f.by) > 0 && !f.ball.dead;
// Does the ball meet the bat now? It has bounced on the bat's half (`hittable`) and is at or just
// past the bat's line: a bat held over the table, in front of where the ball bounced, still meets
// it right after the bounce (Eero on v1's preview: too hard to hit).
function meets(f, bat, reach = REACH) {
  const s = sgn(1 - f.by), b = f.ball, past = (b.z - bat.z) * s;
  return past >= 0 && past < DEPTH && Math.abs(b.x - bat.x) < reach && b.y > -0.35 && b.y < 1.0;
}

// ---- Shots ----
// A shot from where the ball is to a spot on the other half, in flight time T (game seconds),
// without spin in the air: v straight from the parabola. Lifted until it clears the net, unless
// `low` (a smash at a low ball may go into the net).
function aimAt(from, tx, tz, T, low) {
  for (let k = 0; k < 12; k++) {
    const vx = (tx - from.x) / T, vz = (tz - from.z) / T, vy = (BR - from.y + G * T * T / 2) / T;
    const tn = -from.z / vz;                       // when it crosses the net
    const yn = from.y + vy * tn - G * tn * tn / 2;
    if (low || !(tn > 0 && tn < T) || yn > NET_H + BR + 0.025) return { vx, vy, vz };
    T *= 1.08;
  }
  const vx = (tx - from.x) / T, vz = (tz - from.z) / T;
  return { vx, vy: (BR - from.y + G * T * T / 2) / T, vz };
}
// A hit by `side`: kind 'block' | 'drive' | 'smash', aim -1..1 across the other half, off 0..1
// (how far from the bat's middle it met), r the random source. Returns the launch.
function shotLaunch(ball, side, kind, aim, off, r) {
  const s = sgn(side), low = ball.y < 0.14;
  const T = kind === 'smash' ? 0.34 : kind === 'drive' ? 0.5 : 0.72;
  const depth = kind === 'smash' ? 1.0 : kind === 'drive' ? 0.95 : 0.75;
  // The risk: a ball met off the bat's middle, a fast ball coming in, a hard swing.
  const pace = Math.max(0, Math.hypot(ball.vz, ball.vy) - 2.5);
  let err = 0.03 + off * 0.28 + pace * 0.08;
  err *= kind === 'smash' ? 2.0 : kind === 'drive' ? 1.4 : 1;
  if (kind === 'smash' && low) err += 0.25;
  const tx = clamp(aim, -1, 1) * 0.62 + gauss(r) * err * 0.6;
  const tz = -s * (depth + gauss(r) * err);
  const v = aimAt(ball, tx, tz, T, kind === 'smash' && low && r() < 0.5);
  const sp = kind === 'drive' ? 0.7 : kind === 'smash' ? 0.3 : -0.25;
  return launchOf({ x: ball.x, y: ball.y, z: ball.z, vx: v.vx, vy: v.vy, vz: v.vz, sp });
}
// A serve from the bat: first bounce on the server's half, then on the other, aim -1..1.
// Solved hop by hop: the second hop peaks at h2 (well over the net), its length sets the speed,
// and the first hop's start height follows. The toss is near the end line, whatever the bat.
function serveLaunch(bat, side, aim, r) {
  const s = sgn(side);
  const z0 = s * clamp(Math.abs(bat.z), HL + 0.05, HL + 0.35), x0 = clamp(bat.x, -HW - 0.1, HW + 0.1);
  const z1 = s * HL * 0.55, tz = -s * (0.85 + gauss(r) * 0.06), tx = clamp(aim, -1, 1) * 0.55 + gauss(r) * 0.04;
  const h2 = 0.24 + r() * 0.05, vy1 = Math.sqrt(2 * G * h2), T2 = 2 * vy1 / G;
  const vz = (tz - z1) / T2, T1 = (z1 - z0) / vz;
  const y0 = BR + vy1 / E * T1 - G * T1 * T1 / 2, vy = G * T1 - vy1 / E;
  const vx = (tx - x0) / (T1 + 0.96 * T2);
  return launchOf({ x: x0, y: y0, z: z0, vx, vy, vz, sp: 0 });
}

// ---- The game: one game to 11, two clear ----
function newGame(names) {
  return { sc: [0, 0], sv: 0, r: 0, names, flight: null, n: -1, ph: 'serve', wait: 1.2, over: false, winner: -1 };
}
// Who serves at this score: two serves each, one each from 10–10.
function serverAt(sc, first) {
  const t = sc[0] + sc[1];
  const k = t >= 2 * (POINTS - 1) ? t : Math.floor(t / 2);
  return (first + k) % 2;
}
function winnerOf(sc) {
  for (const s of [0, 1]) if (sc[s] >= POINTS && sc[s] - sc[1 - s] >= 2) return s;
  return -1;
}
// A point to side w. Returns true when the game is over.
function addPoint(g, w) {
  g.sc[w]++;
  g.winner = winnerOf(g.sc);
  g.over = g.winner >= 0;
  g.sv = serverAt(g.sc, g.first || 0);
  g.ph = g.over ? 'over' : 'point';
  g.wait = 1.3;
  if (g.flight) g.flight.over = { w };
  return g.over;
}
