// Pesis v1 (#504): the match engine. The field, the 18 players, the ball and the rules, in plain
// numbers stepped 1/60 s at a time, with no drawing, so tests can drive a whole match. index.html
// draws it, reads the controls and runs the room. This file's names are global (a classic script),
// so the page and the tests reach them.
//
// The field, seen from above, in metres: x across (−FW..FW), y from the home base (0) out to the
// back line (FL). The runners go home → 1st (left) → 2nd (right) → 3rd (left) → home, the
// zigzag of real pesis, made smaller to fit a phone.
'use strict';

const FW = 15, FL = 60, FRONT = 4;           // half the width, the back line, the front line a hit must pass
const BASES = [{ x: 0, y: 0 }, { x: -7, y: 5 }, { x: 7, y: 12 }, { x: -7, y: 19 }, { x: 0, y: 0 }];
const BASE_R = 1.4;                          // a fielder with the ball this near a base holds it
const G = 9.8, Z0 = 1.0, IDEAL = 0.0;        // the toss starts at hand height; IDEAL: the best tap's offset
const HIT_WIN = 0.2;                         // a tap this far (s) from the best moment still hits
const LATE_OK = 0.5;                         // a friend's tap is waited for this long after the pitch ends
const THROW_V = 19, CATCH_R = 1.0, PR = 0.55;
const RUN_MAX = 10, STEP_V = 1.4, RUN_DRAG = 0.33;  // the feet: each step on the other foot adds speed
const TRIES = 3, OUTS = 3, PLAY_MAX = 25;
const READY_T = 1.0, DEAD_T = 1.8, CHANGE_T = 2.6;

// The nine fielding places: 0 is the lukkari (always the computer's), 1–3 guard the bases, 4–5 the
// polttajat, 6 the sieppari, 7–8 the kopparit deep. FIX: the order phones get fixed places in.
const POS = [
  { x: 1.2, y: 1.2, n: 'Lukkari' },
  { x: -9.5, y: 6.5, n: 'Ykkösvahti', base: 1 }, { x: 9.5, y: 13.5, n: 'Kakkosvahti', base: 2 }, { x: -9.5, y: 20.5, n: 'Kolmosvahti', base: 3 },
  { x: 5, y: 21, n: 'Kakkospolttaja' }, { x: -4, y: 28, n: 'Kolmospolttaja' },
  { x: 2, y: 38, n: 'Sieppari' }, { x: -8, y: 50, n: 'Vasen koppari' }, { x: 9, y: 54, n: 'Oikea koppari' },
];
const FIX = [6, 4, 5, 7, 8, 2, 3, 1];
const NAMES = [['Ville', 'Aino', 'Onni', 'Siiri', 'Eetu', 'Helmi', 'Leevi', 'Venla', 'Toivo'],
               ['Kalle', 'Iida', 'Niilo', 'Elli', 'Aaro', 'Lumi', 'Veikko', 'Hilla', 'Arvo']];

const hyp = Math.hypot;
const segLen = a => hyp(BASES[a + 1].x - BASES[a].x, BASES[a + 1].y - BASES[a].y);

// ---------- The state ----------
let players = [], ball = null, runners = [], score = [0, 0], inn = 0, bt = 0, outs = 0, tries = 0, batter = -1;
let queue = [], state = 'menu', stT = 0, pitch = null, playN = 0, playT = 0, events = [], evN = 0, level = 1;
let first = 1;          // the team that bats first
let ctrls = [];         // the phones: { id, t, slots (batting order places), fix (a fielding place, -1 = follow the ball), act, away }
let saved = null;       // the runners before a hit, put back when it was foul
let tossN = 0;          // pitch numbers, counted by the host
let onToss = null;      // the page's hook: a new toss to send to the room
let rnd = Math.random;  // tests may seed it

function mkPlayer(t, k, name, lvl) {
  const l = Math.min(Math.max(lvl, 1), 9) - 1;
  return { t, k, name, ctl: '', x: POS[k].x, y: POS[k].y, v: 0, foot: 0, fx: 0, fy: 1, steps: 0,
    speed: Math.min(8.6, 7.2 + 0.16 * l), react: Math.max(0.15, 0.45 - 0.035 * l), err: Math.max(0.05, 0.13 - 0.009 * l),
    think: 0, out: false, home: false };
}
const P = i => players[i];
const fielders = () => players.filter(p => p.t !== bt);
function idx(p) { return players.indexOf(p); }

// A new match: two teams of nine. lv: the computer's level (alone), or the room's level for all.
function newGame(lvTeams, names) {
  players = [];
  for (const t of [0, 1]) for (let k = 0; k < 9; k++) players.push(mkPlayer(t, k, (names && names[t] && names[t][k]) || NAMES[t][k], lvTeams[t]));
  score = [0, 0]; inn = 0; events = []; evN = 0; tossN = 0; playN = 0;
  startInning(first);
}
function startInning(t) {
  bt = t; outs = 0; tries = 0; runners = []; batter = -1; saved = null;
  for (const p of players) { p.out = false; p.home = false; }
  queue = []; for (let k = 0; k < 9; k++) queue.push(t * 9 + k);
  nextBatter();
  ready();
}
function nextBatter() {
  tries = 0;
  batter = queue.length ? queue.shift() : -1;
  if (batter < 0) return;
  // The phone that owns this place in the batting order now plays this batter.
  const ord = batter - bt * 9;
  for (const k of ctrls) if (k.t === bt && k.slots.includes(ord)) k.act = batter;
}
// Everyone to their places before a pitch: fielders to theirs, runners on their bases.
function ready() {
  state = 'ready'; stT = 0; pitch = null;
  ball = { x: 0.4, y: 0.4, z: Z0, vx: 0, vy: 0, vz: 0, held: idx(lukkari()), fly: false, th: null, landed: false };
  for (const p of players) {
    p.v = 0; p.goal = null; p.holdT = 0;
    if (p.t !== bt) { p.x = POS[p.k].x; p.y = POS[p.k].y; p.fx = 0; p.fy = -1; }
    else { p.x = -14 + (p.k % 5) * 1.3; p.y = -1.6 - Math.floor(p.k / 5) * 1.3; p.fx = 1; p.fy = 0; }  // the bench, left of home
  }
  for (const r of runners) { const b = BASES[r.at]; P(r.i).x = b.x; P(r.i).y = b.y; r.run = false; r.d = 0; }
  if (batter >= 0) { P(batter).x = -0.9; P(batter).y = -0.5; P(batter).fx = 1; P(batter).fy = 0; }
}
const lukkari = () => players[(1 - bt) * 9];

// ---------- The pitch ----------
// The lukkari tosses the ball straight up over the plate. Its height over time is fixed by the
// apex alone, so every phone plays the same toss from the same number.
const tossV = ap => Math.sqrt(2 * G * (ap - Z0));
const tossZ = (ap, t) => Z0 + tossV(ap) * t - G * t * t / 2;
const bestT = ap => 2 * tossV(ap) / G;                                    // back at hand height, falling
const tossEnd = ap => { const v = tossV(ap); return (v + Math.sqrt(v * v + 2 * G * Z0)) / G; };  // on the plate
function toss() {
  tossN++;
  pitch = { n: tossN, ap: 2.6 + rnd() * 0.8, t: 0, tapped: false, done: false, cpuAt: null };
  state = 'pitch'; stT = 0;
  ball.held = -1; ball.x = 0; ball.y = 0.3; ball.z = Z0;
  // The computer's batter picks its moment, a little off.
  if (batter >= 0 && !P(batter).ctl) pitch.cpuAt = bestT(pitch.ap) + (rnd() - 0.5) * HIT_WIN * 1.2 + gauss() * P(batter).err;
  if (onToss) onToss(pitch);
}
// A pitch a pause or the batter's rejoin cut short is not judged: it is thrown again, new number.
function retoss() { if (state === 'pitch' && pitch && !pitch.done) { state = 'ready'; stT = READY_T - 0.5; pitch = null; } }
function gauss() { return (rnd() + rnd() + rnd() - 1.5) * 1.15; }

// The judge of a bat tap, for every batter alike: the pitch it was meant for and the time since
// the toss on the phone that tapped. Returns what happened, or null when it does not count.
function batTap(n, ph) {
  if (state !== 'pitch' || !pitch || pitch.n !== n || pitch.tapped || pitch.done) return null;
  if (!(ph >= 0) || pitch.t > tossEnd(pitch.ap) + LATE_OK) return null;
  pitch.tapped = true;
  const off = ph - bestT(pitch.ap) - IDEAL, z = tossZ(pitch.ap, ph);
  if (Math.abs(off) > HIT_WIN || z < 0.1) { say(0, 1, 'Huti', '#fff', 'huti'); return 'huti'; }
  hit(off);
  return 'hit';
}
// A hit: early goes left, late right; the nearer the best moment the harder. The height is luck.
function hit(off) {
  const q = 1 - Math.abs(off) / HIT_WIN;
  const ang = (off / HIT_WIN) * 0.8 + (rnd() - 0.5) * 0.12;
  const sp = 11 + 11 * q + rnd() * 2;
  // Most go low and bounce before the fielders get there; the rest fly, and a fly can be caught.
  const ele = rnd() < 0.7 ? -0.12 + rnd() * 0.2 : 0.3 + rnd() * 0.55;
  const h = sp * Math.cos(ele);
  saved = { runners: runners.map(r => ({ ...r })), batter };
  playN++; playT = 0;
  ball = { x: 0, y: 0.5, z: 0.9, vx: Math.sin(ang) * h, vy: Math.cos(ang) * h, vz: sp * Math.sin(ele), held: -1, fly: true, th: null, landed: false };
  pitch.done = true;
  state = 'play'; stT = 0;
  // The batter must run; the runners on the bases choose.
  runners.push({ i: batter, at: 0, run: true, d: 0, bat: true, wait: 0, cpuGo: true });
  P(batter).v = 3;
  batter = -1;
  // The computer's runners on the bases wait to see whether a fly is caught, then choose.
  for (const r of runners) if (!r.bat) { r.cpuGo = false; r.seen = false; r.wait = 0; }
  say(0, 2, 'Lyönti!', '#ffe08a', 'lyonti');
}
// A pitch over with no hit: one try spent; the third ends the batter's turn as a palo.
function pitchOver(what) {
  pitch.done = true;
  tries++;
  if (what === 'ohi') say(0, 1, 'Ei lyöntiä', '#fff', 'ohi');
  if (tries >= TRIES) { outs++; say(0, 1, 'Kolme lyöntiä: palo', '#ff8a80', 'palo'); P(batter).out = true; batter = -1; }
  dead();
}

// ---------- Running ----------
// A step: the other foot than last time adds speed, the same foot twice loses some.
function step(i, foot) {
  const p = P(i);
  if (foot !== p.foot) p.v = Math.min(RUN_MAX, p.v + STEP_V * (1 - p.v / RUN_MAX)); else p.v = Math.max(0, p.v - 0.3);
  p.foot = foot; p.steps++;
}
// A foot press from a phone, for its player (a runner or a fielder chasing the ball).
function footPress(i, foot) {
  if (state !== 'play') return false;
  const r = runners.find(q => q.i === i);
  if (r) {
    if (!r.run) {
      if (r.wait > 0 || r.at >= 4) return false;
      r.run = true; r.d = 0; P(i).v = 2.5; P(i).foot = foot; P(i).steps++;
      return true;
    }
    step(i, foot);
    return true;
  }
  if (P(i).t !== bt) { step(i, foot); return true; }
  return false;
}
// Would the computer run from here? When the ball is far from the next base and nobody has it.
function cpuRuns(r) {
  if (r.at >= 4) return false;
  const nb = BASES[r.at + 1], mine = segLen(r.at) / (P(r.i).speed - 0.6);
  const lv = Math.min(level, 9);
  return ballEta(nb) > mine * (0.95 - lv * 0.02) + (rnd() - 0.5) * 0.4;
}
// How soon the fielders could have the ball on a spot.
function ballEta(spot) {
  if (ball.held >= 0) { const h = P(ball.held); return 0.35 + hyp(h.x - spot.x, h.y - spot.y) / THROW_V; }
  const land = landing(), f = nearestFielder(land.x, land.y, true);
  const reach = f ? Math.max(land.t, hyp(f.x - land.x, f.y - land.y) / f.speed) : 9;
  return reach + 0.9 + hyp(land.x - spot.x, land.y - spot.y) / THROW_V;
}
// Where a loose ball will be when it can be picked up: its landing spot, or a little ahead of it rolling.
function landing() {
  if (ball.th) return { x: ball.th.x, y: ball.th.y, t: 0.3 };
  if (ball.z > 0.05 && ball.vz > -50) {
    const t = (ball.vz + Math.sqrt(ball.vz * ball.vz + 2 * G * Math.max(0, ball.z - 0.4))) / G;
    return { x: ball.x + ball.vx * t, y: ball.y + ball.vy * t, t };
  }
  const v = hyp(ball.vx, ball.vy), stop = Math.min(0.6, v / 6);
  return { x: ball.x + ball.vx * stop, y: ball.y + ball.vy * stop, t: 0 };
}
function nearestFielder(x, y, noLukkari) {
  let best = null, bd = Infinity;
  for (const p of fielders()) {
    if (noLukkari && p.k === 0) continue;
    const d = hyp(p.x - x, p.y - y) / p.speed;
    if (d < bd) { bd = d; best = p; }
  }
  return best;
}
function runnerSpot(r) {
  const a = BASES[r.at], b = BASES[Math.min(4, r.at + 1)], L = segLen(Math.min(3, r.at)), f = Math.min(1, r.d / L);
  return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, dx: (b.x - a.x) / L, dy: (b.y - a.y) / L };
}
function stepRunners(dt) {
  for (const r of runners.slice()) {
    const p = P(r.i);
    r.wait = Math.max(0, r.wait - dt);
    if (!r.run && !p.ctl && !r.seen && !ball.fly && r.wait <= 0) { r.seen = true; r.cpuGo = cpuRuns(r); }
    if (!r.run) { if (!p.ctl && r.cpuGo && r.wait <= 0 && state === 'play') { r.run = true; r.d = 0; p.v = 2.5; } else { p.v = 0; continue; } }
    if (!p.ctl) p.v = Math.min(p.speed, p.v + 6 * dt);
    else p.v = Math.max(0, p.v - p.v * RUN_DRAG * dt);
    r.d += p.v * dt;
    const s = runnerSpot(r); p.x = s.x; p.y = s.y; p.fx = s.dx; p.fy = s.dy;
    if (r.d >= segLen(r.at)) arrive(r);
  }
}
function arrive(r) {
  const p = P(r.i);
  r.at++; r.d = 0; r.run = false; p.v = 0; r.wait = p.ctl ? 0.6 : 0.35;
  if (r.at >= 4) {
    score[bt]++;
    runners.splice(runners.indexOf(r), 1);
    p.home = true;
    const kun = r.bat;
    say(0, 1.5, kun ? 'Kunnari!' : 'Juoksu!', '#7ee081', 'juoksu', r.i);
    p.x = 8 + (p.k % 5) * 1.3; p.y = -1.6 - Math.floor(p.k / 5) * 1.3;  // home: the right of the plate
    return;
  }
  const b = BASES[r.at]; p.x = b.x; p.y = b.y;
  // The computer goes on when it is safe; a phone's runner waits for its next press.
  r.cpuGo = false; r.seen = false;
}

// ---------- The ball in play ----------
function stepBall(dt) {
  if (ball.held >= 0) { const h = P(ball.held); ball.x = h.x + 0.3; ball.y = h.y + 0.2; ball.z = 1; ball.vx = ball.vy = ball.vz = 0; return; }
  ball.x += ball.vx * dt; ball.y += ball.vy * dt;
  if (ball.th) {
    // A throw flies straight at its receiver, a little arc over the head.
    const th = ball.th; th.t += dt;
    const f = Math.min(1, th.t / th.T); ball.z = 1.2 + Math.sin(f * Math.PI) * th.arc;
    if (f >= 1) { ball.th = null; ball.vz = -2; }
  } else if (ball.z > 0 || ball.vz > 0) {
    ball.vz -= G * dt; ball.z += ball.vz * dt;
    if (ball.z <= 0) {
      ball.z = 0;
      if (ball.fly) { ball.fly = false; ball.landed = true; if (state === 'play' && foulAt(ball.x, ball.y)) { foul(); return; } }
      ball.vz = -ball.vz * 0.35; if (ball.vz < 1) ball.vz = 0;
      ball.vx *= 0.6; ball.vy *= 0.6;
    }
  } else {
    const v = hyp(ball.vx, ball.vy), s = Math.max(0, v - 6 * dt);
    if (v > 0) { ball.vx *= s / v; ball.vy *= s / v; }
  }
  // A fly over the back line or the sides comes down outside: foul. A grounder stops at the fence.
  if (!ball.fly) {
    if (Math.abs(ball.x) > FW + 3) { ball.x = Math.sign(ball.x) * (FW + 3); ball.vx = 0; }
    if (ball.y > FL + 3) { ball.y = FL + 3; ball.vy = 0; }
    if (ball.y < -6) { ball.y = -6; ball.vy = 0; }
  }
}
const foulAt = (x, y) => Math.abs(x) > FW || y > FL || y < FRONT;
function foul() {
  say(ball.x, ball.y, 'Laiton lyönti', '#ffd166', 'laiton');
  runners = saved ? saved.runners.map(r => ({ ...r })) : [];
  if (saved) batter = saved.batter;
  ball.vx = ball.vy = ball.vz = 0;
  tries++;
  if (tries >= TRIES) { outs++; P(batter).out = true; say(0, 1, 'Kolme lyöntiä: palo', '#ff8a80', 'palo'); batter = -1; }
  dead();
}
// A fielder near a loose ball low enough takes it; caught before it landed, it is a koppi.
function pickUp() {
  if (ball.held >= 0 || ball.z > 2.1) return;
  // Just off the bat the ball is still at home: nobody there catches it (the lukkari stands beside the plate).
  if (ball.fly && ball.y < FRONT) return;
  // A hard grounder is hard to stop: it has to come almost straight at the fielder.
  const fast = !ball.fly && !ball.th && hyp(ball.vx, ball.vy) > 9;
  let best = null, bd = fast ? 0.45 : CATCH_R;
  for (const p of fielders()) {
    if (ball.th && ball.th.from === idx(p)) continue;
    const d = hyp(p.x - ball.x, p.y - ball.y);
    if (d < bd) { bd = d; best = p; }
  }
  if (!best) return;
  const koppi = ball.fly;
  ball.held = idx(best); ball.th = null; ball.fly = false; best.think = best.react + 0.25; best.holdT = 0;
  if (koppi) {
    // Kiinni: the batter and every runner off a base leave the field, with no palo.
    say(best.x, best.y, 'Koppi!', '#ffe08a', 'koppi');
    for (const r of runners.slice()) if (r.run || r.bat) { P(r.i).out = true; runners.splice(runners.indexOf(r), 1); }
    batter = -1;
    dead();
    return;
  }
  say(best.x, best.y, '', '', 'kiinni');
  checkBases();
}
// The ball held on a base before the runner coming to it: palo. Held by the lukkari on the
// plate, the play is over: see stopPlay.
function checkBases() {
  if (ball.held < 0 || state !== 'play') return;
  const h = P(ball.held);
  if (h.k === 0 && hyp(h.x, h.y) < 2.2) {
    stopPlay();
    return;
  }
  for (let b = 1; b <= 3; b++) {
    if (hyp(h.x - BASES[b].x, h.y - BASES[b].y) > BASE_R) continue;
    for (const r of runners.slice()) if (r.run && r.at + 1 === b) burn(r);
  }
}
// The play stops (the lukkari has the ball on the plate): a runner past half the way makes the next
// base, one short of it goes back. The batter short of the first base has nowhere to go back to:
// palo, as is the ball beating a runner to a base.
function stopPlay() {
  for (const r of runners.slice()) {
    if (!r.run) continue;
    if (r.d >= segLen(r.at) / 2) arrive(r);
    else if (r.at === 0) burn(r);
    else { r.run = false; r.d = 0; const b = BASES[r.at]; P(r.i).x = b.x; P(r.i).y = b.y; P(r.i).v = 0; }
  }
  dead();
}
function burn(r) {
  outs++; P(r.i).out = true;
  runners.splice(runners.indexOf(r), 1);
  const p = P(r.i);
  say(p.x, p.y, 'Palo!', '#ff8a80', 'palo', r.i);
}
// A throw to a base (1–3) or home (4, to the lukkari). The receiver is the fielder nearest the base.
function throwTo(b) {
  if (ball.held < 0 || state !== 'play') return false;
  const h = P(ball.held), spot = BASES[b];
  const rec = b === 4 ? lukkari() : nearestTo(spot, h);
  if (!rec || rec === h) {
    // Already on that base: run there.
    h.goal = spot; return true;
  }
  const tx = b === 4 ? 0.4 : spot.x, ty = b === 4 ? 0.4 : spot.y;
  const d = hyp(tx - h.x, ty - h.y), T = Math.max(0.15, d / THROW_V);
  ball.held = -1; ball.fly = false;
  ball.x = h.x; ball.y = h.y; ball.vx = (tx - h.x) / T; ball.vy = (ty - h.y) / T; ball.vz = 0;
  ball.th = { from: idx(h), to: idx(rec), b, x: tx, y: ty, t: 0, T, arc: Math.min(3, d * 0.06) };
  rec.goal = { x: tx, y: ty };
  say(h.x, h.y, '', '', 'heitto');
  return true;
}
function nearestTo(spot, not) {
  let best = null, bd = Infinity;
  for (const p of fielders()) { if (p === not || p.k === 0) continue; const d = hyp(p.x - spot.x, p.y - spot.y); if (d < bd) { bd = d; best = p; } }
  return best;
}

// ---------- The computer's fielders ----------
function cpuField(dt) {
  const land = landing();
  // The chasers: the one who gets to the ball first, and a second on a long ball.
  const order = fielders().filter(p => p.k !== 0).sort((a, b) => hyp(a.x - land.x, a.y - land.y) / a.speed - hyp(b.x - land.x, b.y - land.y) / b.speed);
  const loose = ball.held < 0 && !ball.th;
  for (const p of fielders()) {
    if (p.ctl) continue;
    // Off the bat each fielder needs a moment to see where the ball goes.
    if (state === 'play' && playT < p.react && ball.held < 0) continue;
    let tx = POS[p.k].x, ty = POS[p.k].y, sp = p.speed;
    if (p.k === 0) { tx = 0.4; ty = 0.4; if (loose && hyp(land.x, land.y) < 6) { tx = land.x; ty = land.y; } }
    else if (ball.th && ball.th.to === idx(p)) { tx = ball.th.x; ty = ball.th.y; }
    else if (loose && (order[0] === p || (order[1] === p && land.y > 25))) { tx = land.x; ty = land.y; }
    else if (POS[p.k].base && (ball.held >= 0 || ball.th || state === 'play')) { tx = BASES[POS[p.k].base].x; ty = BASES[POS[p.k].base].y; if (loose && order[0] && POS[order[0].k].base === POS[p.k].base) { tx = POS[p.k].x; ty = POS[p.k].y; } }
    if (ball.held === idx(p) && p.k !== 0) { tx = p.goal ? p.goal.x : p.x; ty = p.goal ? p.goal.y : p.y; }
    goTo(p, tx, ty, sp, dt);
    if (ball.held === idx(p) && p.k !== 0) cpuThrow(p, dt);
  }
}
function cpuThrow(p, dt) {
  p.think -= dt;
  if (p.think > 0) return;
  // To a base where the throw beats a runner coming to it; else back to the lukkari.
  let best = 4, gain = 0;
  for (const r of runners) {
    if (!r.run || r.at + 1 > 3) continue;
    const b = r.at + 1, left = (segLen(r.at) - r.d) / Math.max(4, P(r.i).v);
    const rec = nearestTo(BASES[b], p), d = rec === null ? 99 : hyp(BASES[b].x - p.x, BASES[b].y - p.y);
    const there = rec && hyp(rec.x - BASES[b].x, rec.y - BASES[b].y) < 3;
    const tt = d / THROW_V + 0.1;
    if (there && left - tt > gain) { gain = left - tt; best = b; }
  }
  // The lukkari's plate ends the play: everyone running then is palo, so it is the throw when
  // the runners are far from their bases too.
  throwTo(best);
}
function goTo(p, tx, ty, sp, dt) {
  const dx = tx - p.x, dy = ty - p.y, d = hyp(dx, dy);
  if (d < 0.1) { p.v = 0; return; }
  const v = Math.min(sp, d * 5);
  p.x += dx / d * v * dt; p.y += dy / d * v * dt; p.v = v;
  if (d > 0.3) { p.fx = dx / d; p.fy = dy / d; }
}
// A phone's fielder: its feet's speed, towards the ball while it is loose; otherwise the computer
// walks it (to its base for a throw, back to its place).
function phoneField(p, dt) {
  const loose = ball.held < 0 && !ball.th;
  if (ball.held === idx(p)) { p.holdT = (p.holdT || 0) + dt; p.v = 0; if (p.holdT > 4) { throwTo(4); } return; }
  if (loose) {
    const land = landing();
    p.v = Math.max(0, p.v - p.v * RUN_DRAG * dt);
    const dx = land.x - p.x, dy = land.y - p.y, d = hyp(dx, dy);
    if (d > 0.05) { const m = Math.min(d, p.v * dt); p.x += dx / d * m; p.y += dy / d * m; p.fx = dx / d; p.fy = dy / d; }
    return;
  }
  let tx = POS[p.k].x, ty = POS[p.k].y;
  if (ball.th && ball.th.to === idx(p)) { tx = ball.th.x; ty = ball.th.y; }
  else if (POS[p.k].base) { tx = BASES[POS[p.k].base].x; ty = BASES[POS[p.k].base].y; }
  goTo(p, tx, ty, p.speed * 0.8, dt);
}
function separate() {
  const f = fielders();
  for (let i = 0; i < f.length; i++) for (let j = i + 1; j < f.length; j++) {
    const a = f[i], b = f[j], dx = b.x - a.x, dy = b.y - a.y, d = hyp(dx, dy);
    if (d > 0 && d < PR * 2) { const m = (PR * 2 - d) / 2; a.x -= dx / d * m; a.y -= dy / d * m; b.x += dx / d * m; b.y += dy / d * m; }
  }
}

// ---------- The match's flow ----------
function dead() { state = 'dead'; stT = 0; if (pitch) pitch.done = true; }
function say(x, y, s, c, kind, who) { evN++; events.push({ id: evN, x, y, s, c, k: kind || '', w: who === undefined ? -1 : who, t: 1.4 }); }

// One step of the match on the phone that runs it (alone, or the room's host).
function stepGame(dt) {
  stT += dt;
  for (const e of events) e.t -= dt;
  events = events.filter(e => e.t > 0);
  if (state === 'ready') { if (stT >= READY_T) { if (batter < 0) endInning(); else toss(); } return; }
  if (state === 'pitch') {
    pitch.t += dt;
    if (pitch.cpuAt !== null && !pitch.tapped && pitch.t >= pitch.cpuAt) batTap(pitch.n, pitch.t);
    if (state !== 'pitch') return;
    const end = tossEnd(pitch.ap), wait = batterRemote() ? LATE_OK : 0;
    if (pitch.t >= end + wait) pitchOver(pitch.tapped ? 'huti' : 'ohi');
    ball.z = Math.max(0, tossZ(pitch.ap, Math.min(pitch.t, end)));
    return;
  }
  if (state === 'play') {
    playT += dt;
    const n = 4, h = dt / n;
    for (let s = 0; s < n && state === 'play'; s++) {
      stepRunners(h);
      cpuField(h);
      for (const p of fielders()) if (p.ctl) phoneField(p, h);
      separate();
      stepBall(h);
      if (state !== 'play') break;
      pickUp();
      checkBases();
    }
    if (state === 'play' && playT > PLAY_MAX) stopPlay();
    return;
  }
  if (state === 'dead' && stT >= DEAD_T) afterPlay();
  else if (state === 'change' && stT >= CHANGE_T) { if (inn === 0) { inn = 1; startInning(1 - first); } else { state = 'over'; stT = 0; } }
}
// Whose phone, if any, bats now: a friend's means the host waits a moment for its tap.
let batterRemote = () => false;
function afterPlay() {
  for (const r of runners) { r.run = false; r.d = 0; r.bat = false; }
  if (outs >= OUTS) { endInning(); return; }
  if (batter < 0) nextBatter();
  if (batter < 0) { endInning(); return; }
  ready();
}
function endInning() {
  state = 'change'; stT = 0;
  say(0, 10, inn === 0 ? 'Vuoro vaihtuu' : 'Ottelu päättyi', '#fff', 'vaihto');
}

// Who a phone steers now; the rest are the computer's. Alone ('me' follows the ball in the field).
function assignCtl() {
  for (const p of players) p.ctl = '';
  for (const k of ctrls) {
    if (k.away) continue;
    if (k.t === bt) {
      const p = k.act >= 0 ? P(k.act) : null;
      if (p && !p.out && !p.home && (k.act === batter || runners.some(r => r.i === k.act))) p.ctl = k.id;
    } else if (k.fix > 0) players[k.t * 9 + k.fix].ctl = k.id;
    else {
      // Following the ball: the holder, else the fielder nearest where it will be.
      let p = ball.held >= 0 && P(ball.held).t === k.t && P(ball.held).k !== 0 ? P(ball.held) : null;
      if (!p && state === 'play') { const land = landing(); p = nearestFielder(land.x, land.y, true); }
      if (!p) p = players[k.t * 9 + FIX[0]];
      if (k.follow && k.follow !== p && state === 'play' && ball.held < 0) {
        const land = landing(), a = hyp(k.follow.x - land.x, k.follow.y - land.y), b = hyp(p.x - land.x, p.y - land.y);
        if (a < b + 3) p = k.follow;
      }
      k.follow = p; if (!p.ctl) p.ctl = k.id;
    }
  }
}
