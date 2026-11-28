'use strict';
// Lattia on laavaa v2: the round with friends, 2–8 phones in one room (#488, design on the issue).
//
// The host's phone runs the round: its clock `rt`, the computer's kids, every shove, and who is
// out. Each phone moves its own kid itself (so the stick and the jump answer at once) and sends
// where it is 15 times a second, stamped with its own AiPelitSulava.now(); the host sends the
// whole room 15 times a second, every kid with the stamp of the phone that moved it, and every
// phone draws the kids other phones move through lib/sulava-1.
//
// One round clock: the pieces, the lava and the floats are functions of `rt` and the seed, and
// `rt` moves only while the round is not paused, on every phone. A guest runs its own `rt` on
// between the host's snapshots and eases to the host's (jumps when more than 0.3 s off).
//
// Who decides a fall: a connected guest's own phone judges its own kid and sends the time of its
// fall in every spot after it; the host takes it as it is. The host judges its own kid, the
// computer's, a kid the computer has taken over, and a guest kid whose phone has sent nothing for
// 1 s of running round (it then runs that kid on with no stick). The snapshot carries every
// kid's fall time, and a phone whose own kid is out in it stops driving at once.
//
// Who drives a kid: each has a hand-over counter `own`. The host raises it on `continue` (the
// computer takes it), on `back` and on every `hello` (the phone has it again, a reload too), and
// takes a guest's spot only with the kid's current `own` and while the computer does not drive it.
// A guest takes its kid's spot from the snapshot whenever `own` rises past the one it drives with,
// and only then drives on from there with the new count; while the snapshot says the computer
// drives it, it only draws it.
//
// The end: decide() in world.js, once a tick on the host, waits GRACE in rt for late falls, then
// the last standing wins (or the latest fall; the same instant is a draw); the host deliver()s it.
const RM = window.AiPelitRooms;
const MAX_KIDS = 8;
const SHOVE_SLACK = 0.25;   // s the host forgives a guest's shove for arriving early
let lastEnd = null, hostSeq = 0;
let netRoom = 0;   // the host's pick of room for friends; 0 is the room picked alone
const r3 = n => Math.round(n * 1000) / 1000;
const SU = window.AiPelitSulava;
const stampNow = () => SU ? SU.now() : performance.now() / 1000;
// An outfit id from another phone: a short string or none (draw3d.js dresses only a known id).
const outfitStr = v => typeof v === 'string' ? v.slice(0, 40) : '';

// ---- Smooth drawing of the kids other phones move ----
const tracks = new Map();
function trackOf(id) {
  let t = tracks.get(id);
  if (!t && SU) { t = SU.track({ keys: ['x', 'z', 'y', 'f'], angles: ['f'], jump: 3 }); tracks.set(id, t); }
  return t;
}
// The spot to draw a kid at, or null for its own (a kid this phone moves itself).
function drawnSpot(k) {
  if (!net || !world || runsHere(k) || k.out) return null;
  const t = trackOf(k.id);
  return t ? t.at() : null;
}
// Kids this phone moves itself: its own; on the host also the computer's and those it took over.
function runsHere(k) {
  if (k === me && !(net && net.cpuMine)) return true;
  if (!RM || !RM.isHost || !net) return false;
  const rec = net.recs.get(k.id);
  return !!rec && (rec.kind === 'cpu' || rec.drive || rec.hand || rec.silent);
}

// ---- The host's snapshot ----
// A kid as sent: [id, name, col, who (0 phone, 1 computer, 2 taken over), own, stamp, x, y, z,
// vx, vy, vz, face, outRt, stun, dash, shoves, jumps, outfit id ('' none; v4, #572)].
function pack(k) {
  const rec = net.recs.get(k.id);
  return [k.id, k.name, k.col, rec.kind === 'cpu' ? 1 : rec.drive ? 2 : 0, k.own, r3(k.stamp || 0), r3(k.x), r3(k.y), r3(k.z),
    r3(k.vx), r3(k.vy), r3(k.vz), r3(k.face), k.out ? r3(k.outRt) : -1, r3(k.stun), r3(k.dash), k.shoves, k.jumps || 0, k.o || ''];
}
function hostState() {
  const w = world;
  return { t: 's', round: net.round, seq: ++hostSeq, lv: w.level, seed: w.seed, rt: r3(w.rt), ph: w.ph, kids: w.kids.map(pack) };
}

// ---- The start ----
function netStart(s) {
  net = { round: s.round, lastSeq: -1, recs: new Map(), res: null, sendT: 0, h: -1, cpuMine: false };
  hideAll();
  tracks.clear();
  world = null; me = null; brains = []; result = null; stick = null; jumpPtr = null; seen = null;
  if (s.host && !s.over) {
    const people = s.players.slice(0, MAX_KIDS);
    const players = people.map((p, i) => ({ id: p.id, name: p.name, kind: p.id === RM.me ? 'me' : 'net', col: i, o: p.id === RM.me ? outfitId() : '' }));
    for (let b = 0; players.length < FILL_TO; b++) players.push({ id: 'cpu' + b, name: CPU_NAMES[b % CPU_NAMES.length], kind: 'cpu', col: players.length });
    world = newWorld(netRoom || roomN, players, (Date.now() % 1e9) >>> 0);
    const lvl = ROOMS[world.level - 1].cpu;
    world.kids.forEach((k, i) => {
      net.recs.set(k.id, { kind: k.kind === 'cpu' ? 'cpu' : k.kind, drive: false, hand: false, silent: false, helped: false, inT: performance.now() });
      brains[i] = k.kind === 'cpu' ? cpuBrain(lvl, world.seed + i * 31) : null;
    });
    me = world.kids.find(k => k.id === RM.me) || null;
    mode = 'netplay';
    if (window.L3D && L3D.build) L3D.build(world);
    RM.send(hostState());
  } else mode = 'netwait';
}

// ---- A guest hears the host ----
function guestState(m) {
  if (net.res || !(m.seq > net.lastSeq)) return;   // an older snapshot of this round, overtaken
  net.lastSeq = m.seq;
  if (!world || world.seed !== m.seed || world.level !== m.lv || world.kids.length !== m.kids.length) {
    world = newWorld(m.lv, m.kids.map(a => ({ id: a[0], name: a[1], col: a[2], kind: a[3] === 1 ? 'cpu' : 'net', o: outfitStr(a[18]) })), m.seed);
    world.rt = m.rt;
    me = world.kids.find(k => k.id === RM.me) || null;
    net.h = -1;
    if (window.L3D && L3D.build) L3D.build(world);
  }
  const w = world;
  // The round clock: eased to the host's, or taken when far off.
  const d = m.rt - w.rt;
  if (Math.abs(d) > 0.3) w.rt = m.rt; else w.rt += d * 0.15;
  if (w.ph === 'count' && m.ph !== 'count') w.ph = m.ph;
  if (m.ph === 'over') w.ph = 'over';
  m.kids.forEach((a, i) => {
    const k = w.kids[i];
    if (!k || k.id !== a[0]) return;
    k.name = a[1]; k.col = a[2]; k.kind = a[3] === 1 ? 'cpu' : 'net';
    const outRt = a[13];
    // A friend's outfit as the host has it; my own kid wears my pick, here at once.
    k.o = k === me ? outfitId() : outfitStr(a[18]);
    if (k === me) {
      net.cpuMine = a[3] === 2;
      if (a[4] > net.h || net.cpuMine) {
        // The host hands my kid to me (the start, my reload, back from the computer), or the
        // computer drives it: its spot is the host's.
        if (!net.cpuMine) net.h = a[4];
        Object.assign(k, { x: a[6], y: a[7], z: a[8], vx: a[9], vy: a[10], vz: a[11], face: a[12], stun: a[14], dash: a[15], ground: false });
        k.shoves = Math.max(k.shoves, a[16]); k.jumps = Math.max(k.jumps || 0, a[17]);
      }
      // While the computer drives it, my kid is drawn smoothly like the others'.
      if (net.cpuMine) { const t = trackOf(k.id); if (t) t.push(a[5], { x: a[6], z: a[8], y: a[7], f: a[12] }); }
      // The host says I fell (it judged me, or I had told it): out at once, never alive again.
      if (outRt >= 0 && !k.out) fall(w, k, outRt);
      return;
    }
    if (outRt >= 0 && !k.out) fall(w, k, outRt);
    if (outRt < 0 && k.out) { k.out = false; k.outRt = -1; }
    Object.assign(k, { x: a[6], y: a[7], z: a[8], vx: a[9], vy: a[10], vz: a[11], face: a[12], stun: a[14], dash: a[15], shoves: a[16], jumps: a[17] });
    const t = trackOf(k.id);
    if (t) t.push(a[5], { x: a[6], z: a[8], y: a[7], f: a[12] });
  });
  if (mode === 'netwait') { mode = 'netplay'; stick = null; }
}
// My shove: the dash at once on my phone; the host decides whom it hit.
function netShove() {
  if (!net || !me || me.out || !world || world.ph !== 'play') return;
  if (RM.isHost) { doShove(me); return; }
  if (net.cpuMine || net.h < 0 || !startShove(me)) return;
  RM.send({ t: 'sh', round: net.round, h: net.h, f: r3(me.face) });
}
// The host pushes a kid another phone moves: by a message to that phone. True when it did.
function pushRemote(o, imp) {
  if (!RM.isHost || runsHere(o)) return false;
  o.stun = STUN;   // shown at once on the host; the pushed phone moves it
  RM.send({ t: 'push', round: net.round, h: o.own, imp: imp.map(r3) }, o.id);
  return true;
}

// ---- Each frame, in a room ----
function netTick(dt) {
  if (!net || net.res || !world) return;
  const w = world, now = performance.now();
  if (RM.paused) {
    // Everyone waits, the clock too; a phone's silence while paused does not count.
    if (RM.isHost) for (const rec of net.recs.values()) rec.inT = now;
    return;
  }
  acc += dt;
  let steps = 0;
  while (acc >= STEP && steps++ < 24) {
    acc -= STEP;
    if (RM.isHost) hostStep(STEP, now);
    else guestStep(STEP);
    if (net.res) return;
  }
  if (acc > STEP) acc = 0;
  net.sendT -= dt;
  if (net.sendT > 0) return;
  net.sendT = 1 / 15;
  if (RM.isHost) RM.send(hostState());
  else if (me && net.h >= 0 && !net.cpuMine) {
    RM.send({ t: 'p', round: net.round, h: net.h, s: r3(stampNow()), x: r3(me.x), y: r3(me.y), z: r3(me.z), vx: r3(me.vx), vy: r3(me.vy), vz: r3(me.vz),
      f: r3(me.face), st: r3(me.stun), da: r3(me.dash), sh: me.shoves, j: me.jumps || 0, o: me.out ? r3(me.outRt) : -1, w: outfitId() });
  }
}
function hostStep(dt, now) {
  const w = world;
  if (me) { const [ix, iz] = stickInput(); me.ix = ix; me.iz = iz; me.jump = !!jumpPtr; }
  const run = [];
  const sol = w.ph === 'play' ? solids(w, w.rt) : null;
  w.kids.forEach((k, i) => {
    const rec = net.recs.get(k.id);
    // A phone silent for a second of running round: the host runs its kid on, stick let go.
    rec.silent = rec.kind === 'net' && !rec.drive && !rec.hand && now - rec.inT > 1000;
    if (rec.silent) { k.ix = k.iz = 0; k.jump = false; }
    if (runsHere(k)) run.push(k);
    if (sol && brains[i] && (rec.kind === 'cpu' || rec.drive || rec.hand) && cpuThink(w, k, brains[i], dt, sol)) doShove(k);
  });
  stepWorld(w, dt, run);
  for (const k of run) { k.stamp = stampNow(); if (w.ph === 'play' && inLava(w, k)) fall(w, k); }
  if (decide(w)) hostEnd();
}
function guestStep(dt) {
  const w = world;
  const run = me && net.h >= 0 && !net.cpuMine && !me.out ? [me] : [];
  if (run.length) { const [ix, iz] = stickInput(); me.ix = ix; me.iz = iz; me.jump = !!jumpPtr; }
  if (w.ph === 'over') return;
  stepWorld(w, dt, run);
  if (run.length && w.ph === 'play' && inLava(w, me)) fall(w, me);
}

// A pick while the computer drives my kid (no spots go then): told to the host on its own (v4).
function sendOutfit() {
  if (RM && net && !net.res && !RM.isHost && world) RM.send({ t: 'o', round: net.round, w: outfitId() });
}

// ---- The host hears a guest ----
function hostSpot(m, from) {
  const k = world.kids.find(o => o.id === from), rec = net.recs.get(from);
  if (!k || !rec || rec.kind !== 'net' || rec.drive || m.h !== k.own) return;   // not its now, or an old hand-over
  rec.inT = performance.now(); rec.silent = false; rec.hand = false;   // the phone has its kid now
  const n = v => Number.isFinite(+v) ? +v : 0;
  Object.assign(k, { x: clamp(n(m.x), X0, X1), y: n(m.y), z: clamp(n(m.z), Z0, Z1), vx: n(m.vx), vy: n(m.vy), vz: n(m.vz), face: n(m.f), stun: n(m.st), dash: n(m.da) });
  k.shoves = Math.max(k.shoves, Math.floor(n(m.sh))); k.jumps = Math.max(k.jumps || 0, Math.floor(n(m.j)));
  k.stamp = n(m.s);
  k.o = outfitStr(m.w);   // the guest's outfit, sent on to everyone in the snapshot
  const t = trackOf(k.id);
  if (t) t.push(k.stamp, { x: k.x, z: k.z, y: k.y, f: k.face });
  // The phone's own word that its kid fell, with when: taken as it is (never later than now).
  if (n(m.o) >= 0 && !k.out && world.ph === 'play') fall(world, k, Math.min(world.rt, n(m.o)));
}
function hostShove(m, from) {
  const k = world.kids.find(o => o.id === from), rec = net.recs.get(from);
  if (!k || !rec || rec.drive || m.h !== k.own || k.out || world.ph !== 'play') return;
  // The cooldown is the host's to keep, on its own round clock (a reload keeps it: recs live the
  // whole round). A little slack for messages that arrive bunched; the phone itself waits SHOVE_CD.
  if (rec.shT !== undefined && world.rt - rec.shT < SHOVE_CD - SHOVE_SLACK) return;
  rec.shT = world.rt;
  // Checked where every kid is in the host's view, in the order the host hears the shoves.
  const o = shoveTarget(world, k, +m.f || 0);
  if (!o) return;
  o.pushedAt = world.rt;
  const imp = pushOf(k, o);
  if (!pushRemote(o, imp)) applyPush(o, imp);
}

// ---- The end ----
function hostEnd() {
  const w = world;
  const m = { t: 'end', round: net.round, win: w.winner, draw: w.draw,
    res: standingsOf(w).map(k => ({ id: k.id, n: k.name, c: k.col, t: k.out ? r3(k.outRt) : null, b: k.kind === 'cpu' ? 1 : 0, m: net.recs.get(k.id).helped ? 1 : 0 })) };
  RM.send(hostState());
  RM.deliver(m);
  RM.endRound();
  netEnd(m);
}
// The result, on every phone: shown once (`once()`), saved nowhere.
function netEnd(m) {
  if (!net || net.res) return;
  net.res = m.res; net.win = m.win; net.draw = !!m.draw;
  if (RM.isHost) lastEnd = m;
  const row = m.res.find(o => o.id === RM.me), winRow = m.res.find(o => o.id === m.win);
  result = {
    net: true, won: !!row && m.win === RM.me, draw: !!m.draw, winnerName: winRow ? winRow.n : '', helped: !!(row && row.m),
    time: row ? row.t : null,
    rows: m.res.map(o => ({ id: o.id, name: o.id === RM.me ? 'Sinä' : o.n, col: o.c, t: o.t, me: o.id === RM.me, cpu: !!o.b, helped: !!o.m, win: o.id === m.win })),
  };
  if (RM.once(net.round)) showEnd();
  else backRoom();   // seen already (a reload after the end): straight back to the room
}
function backRoom() {
  if (!net || !net.res) return;
  const won = net.win === RM.me, w = net.res.find(o => o.id === net.win);
  const text = net.draw ? 'Tasapeli!' : won ? 'Voitit kierroksen!' : (w ? w.n + ' voitti kierroksen' : 'Kierros päättyi');
  RM.note(net.res.filter(o => o.id === net.win).map(o => '🏆 ' + (o.id === RM.me ? 'Sinä' : o.n)).join(''));
  toSolo();
  RM.backToRoom(text, won ? 'win' : 'lose');
}
function toSolo() {
  if (!net) return;
  net = null; world = null; me = null; brains = []; tracks.clear();
  showMenu();
  roomControls();
}

// ---- The room screen: the host picks the room of the home ----
let roomEl = null;
function roomControls() {
  if (!RM || !RM.extra || !RM.inRoom) return;
  if (!roomEl) {
    const css = document.createElement('style');
    css.textContent = '#lol-room{display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin:2px 0 4px}' +
      '#aipr #lol-room button{font-size:15px;padding:7px 12px;background:#8a3a18;box-shadow:0 3px 0 #5a2008}' +
      '#aipr #lol-room button.on{background:#ff5a1f;box-shadow:0 3px 0 #a8300a}' +
      '#aipr #lol-asu{font-size:15px;padding:7px 14px;margin:2px 0 4px}';
    document.head.appendChild(css);
    roomEl = document.createElement('div'); roomEl.id = 'lol-room';
    roomEl.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b || !RM.isHost || net) return;
      const n = +b.dataset.r;
      // With friends every room is open: nothing is saved from a room round.
      if (n >= 1 && n <= ROOMS.length) netRoom = n;
      roomControls();
    });
    // v4 (#572): the outfit can be changed in the room too; the next snapshot carries it.
    const box = document.createElement('div');
    box.appendChild(roomEl);
    if (outfit && window.AiPelitOutfits) {
      const ab = document.createElement('button');
      ab.id = 'lol-asu'; ab.type = 'button'; ab.textContent = '👕 Asu';
      ab.addEventListener('click', () => AiPelitOutfits.open());
      box.appendChild(ab);
    }
    RM.extra(box);
  }
  const pick = netRoom || roomN;
  if (RM.isHost) roomEl.innerHTML = ROOMS.map((R, i) => `<button data-r="${i + 1}"${i + 1 === pick ? ' class="on"' : ''}>${R.name}</button>`).join('');
  else {
    const h = (RM.members || []).find(m => m.id === RM.hostId);
    roomEl.innerHTML = `<p class="small">Huoneen tekijä${h ? ' (' + esc(h.name) + ')' : ''} valitsee huoneen.</p>`;
  }
}

if (RM) {
  RM.on('start', netStart);
  RM.on('message', (m, from) => {
    if (!net || !m || m.round !== net.round) return;   // another round's message
    if (RM.isHost) {
      if (!world || net.res) return;
      if (m.t === 'p') hostSpot(m, from);
      else if (m.t === 'sh') hostShove(m, from);
      else if (m.t === 'o') { const k = world.kids.find(o => o.id === from); if (k) k.o = outfitStr(m.w); }
      return;
    }
    if (m.t === 's') guestState(m);
    else if (m.t === 'push') { if (me && m.h === net.h && !net.cpuMine && Array.isArray(m.imp)) applyPush(me, m.imp.map(v => +v || 0)); }
    else if (m.t === 'end') netEnd(m);
  });
  // A phone is back (a reload, or a dropped connection): it takes its kid from where the host has
  // it, with a new hand-over count, from the snapshot sent to it now (design review notes, #488).
  RM.on('hello', id => {
    if (net && !net.res && world) {
      const k = world.kids.find(o => o.id === id), rec = net.recs.get(id);
      if (k && rec && rec.kind === 'net' && !k.out) { rec.drive = false; rec.hand = true; rec.silent = false; k.own++; k.ix = k.iz = 0; k.jump = false; rec.inT = performance.now(); }
      RM.send(hostState(), id);
    } else if (lastEnd && lastEnd.round === RM.round) RM.send(lastEnd, id);
  });
  RM.on('continue', ids => {
    if (!net || net.res || !world) return;
    const lvl = ROOMS[world.level - 1].cpu;
    world.kids.forEach((k, i) => {
      const rec = net.recs.get(k.id);
      if (!ids.includes(k.id) || !rec || rec.kind !== 'net' || rec.drive) return;
      // From now on the host ignores that phone's spots and falls still on their way.
      rec.drive = true; rec.hand = false; rec.helped = true; k.own++;
      brains[i] = cpuBrain(lvl, world.seed + i * 31 + 7);
    });
  });
  RM.on('back', id => {
    if (!net || !world) return;
    const k = world.kids.find(o => o.id === id), rec = net.recs.get(id);
    if (!k || !rec || !rec.drive) return;
    // The computer runs the kid on until the phone's first spot with the new count (design review).
    rec.drive = false; rec.hand = true; rec.inT = performance.now(); k.own++;
    RM.send(hostState(), id);
  });
  RM.on('lobby', toSolo);
  RM.on('leave', () => { toSolo(); });
  RM.on('menu', () => { if (net) toSolo(); else showMenu(); });
  RM.on('peers', roomControls);
}
