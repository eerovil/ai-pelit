'use strict';
// Pingis v1: one game between two phones (#502). Design on the issue, with its review notes.
//
// The host is side 0 (the +z end), the guest side 1. Both phones step the same flight from the
// same rounded launch, so one launch gives the same bounces on both. Only the phone a flight
// flies towards judges it: it hits it back (and sends the new launch, `l`) or ends the point. The
// guest sends its point to the host as `pt`; the host alone keeps the score.
//
// A rally number `r`, the host's, rises at every new rally: after each point, and each time a
// rally is replayed. The host sends every new rally as `rally` (score, who serves, who plays the
// guest's bat: `g` 'p' the phone or 'c' the computer). Every launch and point carries `r`, and a
// phone drops what is not for the rally it is in, so nothing sent before a replay lands in it.
// Inside a rally each flight has a number `n` from 0 (the serve).
//
// - A guest takes a `rally` only when its `r` is above the one it is in: the same rally heard
//   twice (a drop and a `hello`) changes nothing.
// - Each rally has one serve (`served`). Either phone takes the other's serve for its current `r`
//   while that rally has none, even while its own pause after the last point still runs: the
//   two countdowns are frame-timed, so a slow phone may still be in it (#509 review). After the
//   serve, a launch or point only for its current `r`, while `g` is the phone, for the flight it
//   expects.
// - While a phone in the room is away (rooms.js `paused`) both stop. A guest that was paused is
//   stale: it neither serves nor judges until a newer rally comes, and when its pause lifts it
//   tells the host (`sync`). The host replays the rally (same server, no point) when its own
//   pause lifts, on `sync`, on `continue`, and on `hello` while a flight is in play. A replay
//   is never a continue.
// - While `g` is the computer the guest phone neither serves nor judges: the host's computer
//   plays that bat, and the guest only draws the host's launches and bats. `back` gives the bat
//   back at the next rally, never in the middle of one.
// - A host reload ends the game: rooms.js sends every phone to the room screen (`_lobby`).
// - The end goes out with `deliver`, and each phone counts its win or loss once (`once()`).
const RM = window.AiPelitRooms;
const SU = window.AiPelitSulava;
const suNow = () => SU ? SU.now() : performance.now() / 1000;
const r3 = v => Math.round(v * 1000) / 1000;

function sendRally(lw, to) {
  const g = game, m = {
    t: 'rally', round: net.round, r: net.r, p: g.sc[0] + g.sc[1], sc: g.sc.slice(), sv: g.sv, g: net.g,
    ph: g.ph, wait: r3(Math.max(0, g.wait)), lw, nm: net.names, first: g.first,
  };
  net.lastRally = m;
  RM.send(m, to);
}

// ---- The start ----
function netStart(s) {
  hideAll();
  result = null; banner = null; game = null; finger = null;
  const host = !!s.host, people = s.players.slice(0, 2);
  view = host ? 0 : 1;
  net = {
    round: s.round, host, r: -1, p: 0, g: 'p', gNext: 'p', stale: false, wasP: false, wantReplay: false,
    names: people.map(p => p.name || 'Pelaaja'), guest: people[1] ? people[1].id : null,
    res: null, served: false, sendT: 0, tracks: [null, null], helped: false, note: null, lastRally: null,
  };
  hooks = { launched: netLaunched, point: netPoint, next: netNext };
  judgeHere = side => net.host ? (side === 0 || net.g === 'c') : (side === 1 && net.g === 'p' && !net.stale);
  cpuAt = side => net.host && side === 1 && net.g === 'c';
  newBats();
  brains = [null, null];
  if (host && !s.over && people.length === 2) {
    game = newGame(net.names.slice());
    game.first = Math.random() < 0.5 ? 0 : 1;
    game.sv = serverAt(game.sc, game.first);
    net.r = 0; game.r = 0; game.wait = 1.5;
    setNames();
    sendRally(-1);
    mode = 'netplay';
  } else mode = 'netwait';
  wake();
}
function setNames() { names = net.names.slice(); names[view] = 'Sinä'; }
function netCanPlay() { return !!net && !RM.paused && !net.stale && (net.host || net.g === 'p'); }

// ---- Rallies ----
// The host's new rally after a point: the score goes up, `r` with it, and `back` takes effect.
function hostPoint(w) {
  if (!game || game.ph === 'point' || game.ph === 'over') return;
  addPoint(game, w);
  pointSound(w);
  net.r++; game.r = net.r; net.g = net.gNext; net.served = false;
  sendRally(w);
}
// The same server serves again, with no point: anything from the old rally is dropped.
function hostReplay() {
  net.wantReplay = false;
  if (!game || game.over || net.res) return;
  net.r++; game.r = net.r; net.g = net.gNext; net.served = false;
  game.flight = null; game.ph = 'serve'; game.wait = 1.0;
  sendRally(-1);
}
function guestRally(m) {
  if (net.res || !(m.r > net.r) || !Array.isArray(m.sc) || m.sc.length !== 2) return;
  net.r = m.r; net.stale = false; net.served = false; net.g = m.g === 'c' ? 'c' : 'p';
  if (Array.isArray(m.nm) && m.nm.length === 2) net.names = m.nm.map(String);
  setNames();
  if (!game) game = newGame(net.names.slice());
  game.first = m.first === 1 ? 1 : 0;
  game.sc = m.sc.slice(); game.sv = m.sv === 1 ? 1 : 0; game.r = m.r;
  game.winner = winnerOf(game.sc); game.over = game.winner >= 0;
  game.ph = game.over ? 'over' : m.ph === 'point' ? 'point' : 'serve';
  game.wait = +m.wait || 0;
  if (game.ph === 'serve') game.flight = null;
  else if (game.flight && !game.flight.over) game.flight.over = { w: m.lw };
  if (m.lw >= 0 && m.p > net.p) pointSound(m.lw);
  net.p = m.p;
  if (mode === 'netwait') mode = 'netplay';
  wake();
}

// ---- The hooks ui.js calls ----
function netLaunched(f) {
  if (f.n === 0) net.served = true;
  if (!net.host && f.by !== 1) return;
  RM.send({ t: 'l', round: net.round, r: net.r, n: f.n, by: f.by, s: f.serve ? 1 : 0, a: f.launch });
}
function netPoint(f, w) {
  if (net.host) { hostPoint(w); return; }
  // The guest's word goes to the host; the score changes only with the host's next rally.
  f.over = { w, sent: true };
  RM.send({ t: 'pt', round: net.round, r: net.r, n: f.n, w });
}
function netNext() {
  if (game.over) { if (net.host) hostEnd(); return; }
  game.ph = 'serve'; game.flight = null; game.wait = 0.35;
}

// ---- Launches heard from the other phone ----
const goodLaunch = a => Array.isArray(a) && a.length === 7 && a.every(Number.isFinite);
function takeLaunch(m) {
  if (m.n === 0) net.served = true;
  const f = newFlight(m.n, m.by, m.n === 0, m.a.slice());
  if (game.flight && !game.flight.over) game.flight.over = { hit: true };
  game.flight = f; game.ph = 'play';
  if (bats[m.by]) bats[m.by].swing = 1;
  hitSound(m.n === 0 ? 'drive' : 'block');
}
function hostHeard(m, from) {
  if (from !== net.guest || !game) return;
  if (m.t === 'b') { if (net.g === 'p' && Array.isArray(m.a)) glide(1, m.st, m.a[0], m.a[1]); return; }
  if (m.t === 'sync') {
    if (m.r >= net.r) net.wantReplay = true;
    else if (net.lastRally) RM.send(net.lastRally, from);
    return;
  }
  if (m.r !== net.r || net.g !== 'p' || net.res) return;
  const f = game.flight;
  if (m.t === 'l' && m.by === 1 && goodLaunch(m.a)) {
    if (m.n === 0) {
      if (net.served || game.over || game.sv !== 1) return;   // rally r has its serve already
    } else if (!f || f.over || f.by !== 0 || m.n !== f.n + 1) return;
    takeLaunch(m);
    return;
  }
  if (m.t === 'pt' && (m.w === 0 || m.w === 1) && f && !f.over && f.by === 0 && m.n === f.n) hostPoint(m.w);
}
function guestHeard(m) {
  if (m.t === 'rally') { guestRally(m); return; }
  if (m.t === 'end') { netEnd(m); return; }
  if (!game) return;
  if (m.t === 'b') {
    if (!Array.isArray(m.a)) return;
    glide(0, m.st, m.a[0], m.a[1]);
    if (net.g === 'c') glide(1, m.st, m.a[2], m.a[3]);
    return;
  }
  if (m.t === 'l' && m.r === net.r && !net.res && goodLaunch(m.a) && (m.by === 0 || m.by === 1)) {
    const f = game.flight;
    if (m.n === 0 ? net.served || game.over : !f || m.n <= f.n) return;
    if (m.by === 1 && net.g === 'p') return;   // my own launches are mine; the host never sends them
    takeLaunch(m);
  }
}
// The other bat glides (lib/sulava-1): drawn a moment back, between two of its spots.
function glide(side, st, x, z) {
  if (!Number.isFinite(x) || !Number.isFinite(z)) return;
  if (!SU) { bats[side].x = x; bats[side].z = z; return; }
  const tr = net.tracks[side] || (net.tracks[side] = SU.track({ keys: ['x', 'z'] }));
  if (!tr.size()) tr.snap(st, { x, z }); else tr.push(st, { x, z });
}

// ---- Each frame, in a room ----
function netTick(dt) {
  if (!net || net.res || !game || !bats) return;
  const P = !!RM.paused;
  if (net.host) { if (net.wasP && !P) net.wantReplay = true; }
  else {
    if (P && !net.wasP) net.stale = true;
    if (!P && net.wasP && net.stale) RM.send({ t: 'sync', round: net.round, r: net.r });
  }
  net.wasP = P;
  net.note = P ? 'Odotetaan kaveria…' : !net.host && net.g === 'c' ? 'Kone pelaa puolestasi' : null;
  if (P) return;
  if (net.host && net.wantReplay) hostReplay();
  // My bat follows my finger, unless the computer has it.
  const mine = net.host || net.g === 'p';
  if (mine) {
    myBat(dt);
    const b = bats[view];
    if (game.ph === 'serve' && game.sv === view && -b.vz * sgn(view) > 0.8 && netCanPlay() && finger !== null) {
      tryServe(view, clamp(b.vx / 2.2, -1, 1));
    }
  }
  // The bats this phone only draws.
  for (const side of [0, 1]) {
    if (side === view ? mine : cpuAt(side)) continue;
    const tr = net.tracks[side];
    if (tr && tr.size()) { const v = tr.at(); bats[side].x = v.x; bats[side].z = v.z; }
  }
  advance(dt * SLOW);
  batHeights(scene().ball, dt);
  net.sendT -= dt;
  if (net.sendT <= 0) {
    net.sendT = 0.05;
    const st = r3(suNow()), b0 = bats[0], b1 = bats[1];
    if (net.host) RM.send({ t: 'b', round: net.round, st, a: [r3(b0.x), r3(b0.z), r3(b1.x), r3(b1.z)] });
    else if (mine && !net.stale) RM.send({ t: 'b', round: net.round, st, a: [r3(b1.x), r3(b1.z)] });
  }
}

// ---- The end ----
function hostEnd() {
  if (net.res) return;
  const m = { t: 'end', round: net.round, sc: game.sc.slice(), nm: net.names, helped: net.helped ? 1 : 0 };
  RM.deliver(m);
  RM.endRound();
  netEnd(m);
}
function netEnd(m) {
  if (!net || net.res || !Array.isArray(m.sc)) return;
  net.res = m;
  const w = winnerOf(m.sc), nm = Array.isArray(m.nm) ? m.nm : net.names;
  result = { net: true, side: view, won: w === view, sc: m.sc.slice(), foe: nm[1 - view] || '', helped: view === 1 && !!m.helped };
  if (RM.once(net.round)) {
    // Games with friends, won and lost, counted once per game on this phone.
    const k = load('kaverit', {}), rec = k && typeof k === 'object' ? k : {};
    const key = result.won ? 'voitot' : 'haviot';
    rec[key] = (Math.floor(rec[key]) || 0) + 1;
    save('kaverit', rec);
    showEnd();
  } else backRoom();
}
function backRoom() {
  if (!net || !net.res) return;
  const r = result, me = view;
  RM.note('Sinä ' + r.sc[me] + '–' + r.sc[1 - me] + ' ' + r.foe);
  const text = r.won ? 'Voitit pelin!' : r.foe + ' voitti pelin';
  toSolo();
  RM.backToRoom(text, r.won ? 'win' : 'lose');
}
function toSolo() {
  if (!net) return;
  net = null; game = null; result = null; finger = null; view = 0;
  hooks = soloHooks; judgeHere = () => true; cpuAt = side => side === 1;
  showMenu();
}

if (RM) {
  RM.on('start', netStart);
  RM.on('message', (m, from) => {
    if (!net || !m || m.round !== net.round) return;
    if (net.host) hostHeard(m, from); else guestHeard(m);
  });
  RM.on('hello', id => {
    if (net && net.host && !net.res && game) {
      // The phone is back: it gets the latest rally; a rally in play is replayed, not continued.
      if (net.lastRally) RM.send(net.lastRally, id);
      if (game.flight && game.ph === 'play') net.wantReplay = true;
    }
  });
  RM.on('continue', ids => {
    if (!net || !net.host || net.res || !game || !ids.includes(net.guest)) return;
    net.g = 'c'; net.gNext = 'c'; net.helped = true;
    brains[1] = cpuBrain(1, (Date.now() % 1e9) >>> 0);
    net.wantReplay = true;
  });
  RM.on('back', id => {
    if (!net || !net.host || net.res || id !== net.guest) return;
    net.gNext = 'p';   // from the next rally on
  });
  RM.on('lobby', toSolo);
  RM.on('leave', () => { toSolo(); });
  RM.on('menu', () => { if (net) toSolo(); else showMenu(); });
}
