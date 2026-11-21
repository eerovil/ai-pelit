'use strict';
// Jäälautta v1: the match with friends, 2–8 phones on one floe (#478).
//
// The host phone runs the only real world (world.js): every seal, the computer's too, every hit,
// fall, pick-up and pass. It sends the whole state 15 times a second. A guest sends only its
// input 20 times a second (stick, and a lunge counter) and draws the host's state, moving the
// others on by their speed between messages; its own seal moves at once with its own finger
// (prediction) and is eased back to where the host has it. A guest decides nothing.
//
// v3 (#480): a guest draws the other seals from lib/sulava-1, gliding between the host's states a
// moment back, instead of carrying each one on at its speed until the next state (v2). Each state
// carries the host's own clock (`st`, AiPelitSulava.now()); the host moves every seal itself, so
// every spot a guest hears is on that one clock and none is forwarded with a friend's stamp. The
// seals keep the newest spot between frames (the guest's own seal and the HUD read it); only the
// picture swaps the drawn spot in (asDrawn() and putBack(), around draw() in ui.js). A guest judges
// no bump, so no rule needs the drawn spot.
//
// Order (design review, #478): a guest keeps only states of the round it last heard `start` for
// (rooms.js's round id, compared only for equality) and, within it, only a `seq` above the last it
// kept. The host's `seq` is one counter for the whole life of its page and never goes back.
//
// Who drives a seal: each has a take-over counter `own`, raised by the host on `continue` (the
// computer takes it), on `back` (the phone has it again) and on `hello` (the phone came back).
// The host takes a phone's input only with the seal's current `own`, and counts a lunge only when
// its count is above the seal's `lunges`; a phone takes both from the host's state whenever `own`
// rises, and only counts up from there. A room match saves nothing lasting: wins, opened floes and
// the high-score list are only for matches alone.
const RM = window.AiPelitRooms;
const MAX_SEALS = 8, FILL_TO = 4;
let lastEnd = null, hostSeq = 0;   // `net` is declared in ui.js: its loop may run before this file

const r2 = n => Math.round(n * 100) / 100;
const recOf = id => net && net.recs.find(r => r.id === id);
// A seal as sent. `out` is never rounded down to 0, so a seal just in is in on the guests too.
function pack(sl, rec) {
  return [sl.id, sl.name, sl.hat, sl.kind === 'cpu' ? 1 : 0, sl.own, sl.lunges, r2(sl.x), r2(sl.y), r2(sl.vx), r2(sl.vy), r2(sl.face),
    r2(sl.cd), r2(sl.lungeT), r2(sl.stun), sl.out ? Math.max(0.01, r2(sl.out)) : 0, r2(sl.outX), r2(sl.outY),
    sl.size ? sl.size.k : '', sl.size ? r2(sl.size.t) : 0, sl.fuse ? sl.fuse.k : '', sl.fuse ? r2(sl.fuse.t) : 0, sl.fuse ? sl.fuse.from || '' : '',
    sl.stars, sl.hit, sl.got, sl.gotK || '', sl.crushed ? 1 : 0, rec && rec.helped ? 1 : 0,
    sl.teeter > 0 ? Math.max(0.01, r2(sl.teeter)) : 0, sl.mash, r2(sl.ta), sl.saved];
}
function unpack(sl, a, mine) {
  sl.name = a[1]; sl.hat = a[2]; sl.kind = a[3] ? 'cpu' : 'net'; sl.own = a[4];
  if (!mine) {
    sl.lunges = sl.want = a[5];
    sl.x = a[6]; sl.y = a[7]; sl.vx = a[8]; sl.vy = a[9]; sl.face = a[10]; sl.cd = a[11]; sl.lungeT = a[12];
  }
  sl.stun = a[13]; sl.out = a[14]; sl.outX = a[15]; sl.outY = a[16];
  sl.size = a[17] ? { k: a[17], t: a[18] } : null;
  sl.fuse = a[19] ? { k: a[19], t: a[20], from: a[21] || null } : null;
  sl.stars = a[22]; sl.hit = a[23]; sl.got = a[24]; sl.gotK = a[25] || null; sl.crushed = !!a[26]; sl.helped = !!a[27];
  sl.teeter = a[28] || 0; sl.mash = a[29] || 0; sl.ta = a[30] || 0; sl.saved = a[31] || 0;
}
function hostState() {
  const w = world;
  return {
    t: 's', round: net.round, seq: ++hostSeq, st: AiPelitSulava.now(), f: w.floe, ph: w.ph, cd: r2(w.cd), era: w.era, tt: r2(w.t), pause: r2(w.pause),
    win: w.winner, ew: w.eraWin,
    parts: w.parts.map(p => p.r.map(r2)),
    warn: w.warn.map(b => [b.p, b.i, r2(b.t)]),
    ring: w.ring ? [r2(w.ring.x), r2(w.ring.y), r2(w.ring.come), r2(w.ring.open)] : null,
    snow: w.snow.map(s => [r2(s.x), r2(s.y), r2(s.vx), r2(s.vy), r2(s.r), r2(s.roll)]),
    holes: w.holes.map(o => [r2(o.x), r2(o.y), r2(o.r), r2(o.warn), r2(o.open)]),
    sk: w.seals.map((sl, i) => pack(sl, net.recs[i])),
  };
}

// ---- The start ----
function netStart(s) {
  net = { round: s.round, lastSeq: -1, recs: [], res: null, sendT: 0, myOwn: -1, myL: 0, hx: 0, hy: 0 };
  hideAll();
  world = null; me = null; brains = []; result = null; stick = null; seen = null;
  if (s.host && !s.over) {
    const people = s.players.slice(0, MAX_SEALS), taken = [];
    const players = people.map((p, i) => {
      const mine = p.id === RM.me, h = mine ? hat : hatFor(taken.concat(hat), i);
      taken.push(h);
      return { id: p.id, name: p.name, hat: h, kind: mine ? 'me' : 'net' };
    });
    for (let b = 0; players.length < FILL_TO; b++) {
      const h = hatFor(taken.concat(hat), players.length + b * 3); taken.push(h);
      players.push({ id: 'cpu' + b, name: CPU_NAMES[(b + floeN * 2) % CPU_NAMES.length], hat: h, kind: 'cpu' });
    }
    world = newWorld(floeN, players, (Date.now() % 1e9) >>> 0);
    const F = FLOES[floeN - 1];
    net.recs = world.seals.map(sl => ({ id: sl.id, kind: sl.kind, drive: false, helped: false, inT: performance.now() }));
    brains = world.seals.map((sl, i) => sl.kind === 'cpu' ? cpuBrain(F.cpu, world.seed + i * 31) : null);
    me = world.seals.find(sl => sl.id === RM.me) || null;
    mode = 'netplay';
    RM.send(hostState());
  } else mode = 'netwait';
  wake();
}

// ---- A guest hears the host ----
function guestState(m) {
  if (net.res) return;
  if (!(m.seq > net.lastSeq)) return;   // an older state of this round, overtaken
  net.lastSeq = m.seq;
  if (!world || world.floe !== m.f || world.seals.length !== m.sk.length) {
    world = newWorld(m.f, m.sk.map(a => ({ id: a[0], name: a[1], hat: a[2], kind: a[3] ? 'cpu' : 'net' })), 1);
    me = world.seals.find(sl => sl.id === RM.me) || null;
    if (me) me.kind = 'me';
  }
  const w = world;
  // v3 (#480): a new erä puts every seal back in its ring at once; no glide from where it was.
  const newEra = w.era !== m.era, st = Number.isFinite(m.st) ? m.st : null;
  w.ph = m.ph; w.cd = m.cd; w.era = m.era; w.t = m.tt; w.pause = m.pause; w.winner = m.win; w.eraWin = m.ew;
  w.over = m.ph === 'over';
  m.parts.forEach((rs, i) => { if (w.parts[i]) w.parts[i].r = rs; });
  w.warn = m.warn.map(([p, i, t]) => ({ p, i, t }));
  w.ring = m.ring ? { x: m.ring[0], y: m.ring[1], come: m.ring[2], open: m.ring[3] } : null;
  w.snow = m.snow.map(([x, y, vx, vy, r, roll]) => ({ x, y, vx, vy, r, roll }));
  w.holes = m.holes.map(([x, y, r, warn, open]) => ({ x, y, r, warn, open }));
  m.sk.forEach((a, i) => {
    const sl = w.seals[i];
    if (sl !== me) { const saved = sl.saved; unpack(sl, a, false); heardSpot(sl, st, newEra || sl.saved > saved); return; }
    // My own seal: the host's word on everything but where it is, which is eased to the host's.
    if (a[4] !== net.myOwn) {
      // The host has handed it to me (start, my hello, back): count on from its numbers.
      net.myOwn = a[4]; net.myL = a[5];
      unpack(sl, a, false);
      sl.kind = 'me';
      return;
    }
    // The host counted a press it would not use (between erät): count on from there.
    if (a[5] > net.myL) net.myL = a[5];
    const wasOut = sl.out, wasTeeter = sl.teeter > 0;
    unpack(sl, a, true);
    sl.kind = 'me';
    // Outside play no press is pending: whatever I sent is used up, so none lunges in the next erä
    // on my own copy either (#479 review; the host already drops them).
    if (w.ph !== 'play') sl.lunges = sl.want = net.myL;
    // Wobbling on the edge: the host's word on where, and on the presses (none of them lunge).
    if (sl.teeter > 0) sl.lunges = sl.want = net.myL;
    if (sl.out || wasOut || w.ph !== 'play' || sl.teeter > 0 || wasTeeter) { sl.x = a[6]; sl.y = a[7]; sl.vx = a[8]; sl.vy = a[9]; sl.face = a[10]; sl.cd = a[11]; sl.lungeT = a[12]; return; }
    const ex = a[6] - sl.x, ey = a[7] - sl.y;
    if (Math.hypot(ex, ey) > 2.5) { sl.x = a[6]; sl.y = a[7]; sl.vx = a[8]; sl.vy = a[9]; }
    else { sl.x += ex * 0.35; sl.y += ey * 0.35; sl.vx += (a[8] - sl.vx) * 0.5; sl.vy += (a[9] - sl.vy) * 0.5; }
    // A lunge the host had and I did not (my state was behind): take its cooldown.
    if (a[11] > sl.cd + 0.15) { sl.cd = a[11]; sl.lungeT = a[12]; }
  });
  if (!me) return;   // not in this match (joined late): the room says so
  if (mode === 'netwait') { mode = 'netplay'; stick = null; }
  wake();
}
// v3 (#480): another seal's spot just heard (already unpacked into it), on the host's clock `st`
// (null from a host without it: the track uses the arrival here). `jump` is a move the game knows
// of: a new erä, or a wobbling seal mashed back onto the ice (`saved` rose). A move of over 8 units
// between two states is a jump too: the fastest throw (about 30 units/s, a lunge into a small seal)
// covers 5 in a late state's gap of 0.17 s, and a floe is 16-20 units across.
const SEAL_JUMP = 8;
function heardSpot(sl, st, jump) {
  const spot = { x: sl.x, y: sl.y, face: sl.face };
  if (!sl.tr) sl.tr = AiPelitSulava.track({ keys: ['x', 'y', 'face'], angles: ['face'], jump: SEAL_JUMP });
  if (jump) sl.tr.snap(st, spot); else sl.tr.push(st, spot);
}
// Every other seal at the spot its track draws, for the picture only; putBack() restores the newest.
// A seal in the water is drawn at outX, outY and is left alone.
function asDrawn() {
  if (!net || RM.isHost || !world) return [];
  const kept = [];
  for (const sl of world.seals) {
    if (sl === me || sl.out || !sl.tr || !sl.tr.size()) continue;
    const o = sl.tr.at();
    if (!o) continue;
    kept.push([sl, sl.x, sl.y, sl.face]);
    sl.x = o.x; sl.y = o.y; sl.face = o.face;
  }
  return kept;
}
function putBack(kept) { for (const [sl, x, y, face] of kept) { sl.x = x; sl.y = y; sl.face = face; } }
function netLunge() {
  if (!net || !me || !world || world.ph !== 'play') return;   // only while the erä is on
  if (RM.isHost) { me.want = me.lunges + 1; return; }
  net.myL++;
  me.want = net.myL;   // shown at once; the host decides whether it hit anything
}

// ---- Each frame, in a room ----
function netTick(dt) {
  if (!net || net.res || !world) return;
  if (RM.paused) return;   // a phone in the match is away: everyone waits, the host's world too
  const w = world;
  if (RM.isHost) {
    const now = performance.now();
    if (me) { const [ix, iy] = stickInput(); me.ix = ix; me.iy = iy; }
    w.seals.forEach((sl, i) => {
      const rec = net.recs[i];
      if (brains[i] && (rec.kind === 'cpu' || rec.drive)) cpuThink(w, sl, brains[i], dt);
      // A phone silent for half a second: its stick counts as let go until it talks again.
      else if (rec.kind === 'net' && now - rec.inT > 500) { sl.ix = sl.iy = 0; }
    });
    step(w, dt);
    if (w.over) return hostEnd();
    net.sendT -= dt;
    if (net.sendT <= 0) { net.sendT = 1 / 15; RM.send(hostState()); }
    return;
  }
  // A guest: the countdown runs, my own seal moves with my finger. v3 (#480): the others stay at the
  // newest spot heard (v2 slid them on at their speed) and are drawn gliding a moment back (asDrawn()).
  if (w.ph === 'count') w.cd = Math.max(0, w.cd - dt);
  if (w.ph === 'play') {
    for (const sl of w.seals) if (sl.out) sl.out += dt;
    if (me && !me.out && !(me.teeter > 0)) {
      const [ix, iy] = stickInput();
      me.ix = ix; me.iy = iy;
      me.want = Math.max(me.want, net.myL);
      moveSeal(w, me, dt);
    }
  }
  net.sendT -= dt;
  if (me && net.myOwn >= 0 && net.sendT <= 0) {
    net.sendT = 0.05;
    const [ix, iy] = stickInput();
    RM.send({ t: 'i', round: net.round, w: net.myOwn, x: r2(ix), y: r2(iy), l: net.myL, h: hat });
  }
}

// ---- The host hears a guest ----
function hostInput(m, from) {
  const i = net.recs.findIndex(r => r.id === from);
  if (i < 0 || !world) return;
  const rec = net.recs[i], sl = world.seals[i];
  if (rec.kind !== 'net' || rec.drive || m.w !== sl.own) return;   // not driving it now, or an old take-over
  rec.inT = performance.now();
  let x = +m.x || 0, y = +m.y || 0;
  const d = Math.hypot(x, y);
  if (d > 1) { x /= d; y /= d; }
  sl.ix = x; sl.iy = y;
  if (Number.isFinite(m.l) && m.l > sl.lunges) {
    // A press that reaches the host between erät is counted but never lunges later.
    if (world.ph === 'play') sl.want = Math.max(sl.want, Math.floor(m.l));
    else sl.lunges = sl.want = Math.floor(m.l);
  }
  // The phone's own hat colour, when no other phone wears it (a computer seal swaps with it).
  const h = Math.floor(m.h);
  if (h >= 0 && h < HATS.length && h !== sl.hat) {
    const other = world.seals.find(o => o !== sl && o.hat === h);
    if (!other) sl.hat = h;
    else if (other.kind === 'cpu') { other.hat = sl.hat; sl.hat = h; }
  }
}

// ---- The end ----
function standings() {
  const w = world;
  return w.seals.map((sl, i) => ({ id: sl.id, n: sl.name, st: sl.stars, h: sl.hat, b: sl.kind === 'cpu' ? 1 : 0, m: net.recs[i] && net.recs[i].helped ? 1 : 0 }))
    .sort((a, b) => (b.id === w.winner) - (a.id === w.winner) || b.st - a.st);
}
function hostEnd() {
  const m = { t: 'end', round: net.round, win: world.winner, res: standings() };
  RM.send(hostState());
  RM.deliver(m);
  RM.endRound();
  netEnd(m);
}
// The result, on every phone: shown once (`once()`), saved nowhere.
function netEnd(m) {
  if (!net || net.res) return;
  net.res = m.res; net.win = m.win;
  if (RM.isHost) lastEnd = m;
  const row = m.res.find(o => o.id === RM.me), winRow = m.res.find(o => o.id === m.win);
  result = {
    net: true, won: !!row && m.win === RM.me, winnerName: winRow ? winRow.n : '', helped: !!(row && row.m),
    rows: m.res.map(o => ({ id: o.id, name: o.id === RM.me ? 'Sinä' : o.n, stars: o.st, hat: o.h, me: o.id === RM.me, cpu: !!o.b, helped: !!o.m })),
  };
  if (RM.once(net.round)) showEnd();
  else backRoom();   // seen already (a reload after the end): straight back to the room
}
// From the end screen back to the room, with everyone's stars under the list.
function backRoom() {
  if (!net || !net.res) return;
  const res = net.res, won = net.win === RM.me;
  RM.note(res.map(o => `${o.id === RM.me ? 'Sinä' : o.n} ${'★'.repeat(o.st) || '0'}`).join(' · '));
  const w = res.find(o => o.id === net.win);
  const text = won ? 'Voitit ottelun!' : (w ? (w.id === RM.me ? 'Sinä' : w.n) + ' voitti ottelun' : 'Ottelu päättyi');
  toSolo();
  RM.backToRoom(text, won ? 'win' : 'lose');
}
function toSolo() {
  if (!net) return;
  net = null; world = null; me = null; brains = [];
  showMenu();
  roomControls();
}

// ---- The room screen: the host picks the floe ----
let roomEl = null;
function roomControls() {
  if (!RM || !RM.extra || !RM.inRoom) return;
  if (!roomEl) {
    const css = document.createElement('style');
    css.textContent = '#jaa-room{display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin:2px 0 4px}' +
      '#aipr #jaa-room button{font-size:15px;padding:7px 12px;background:#3a6aa8;box-shadow:0 3px 0 #23477a}' +
      '#aipr #jaa-room button.on{background:#e0283a;box-shadow:0 3px 0 #9a1424}' +
      '#aipr #jaa-room button:disabled{opacity:.35}';
    document.head.appendChild(css);
    roomEl = document.createElement('div'); roomEl.id = 'jaa-room';
    roomEl.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b || !RM.isHost || net) return;
      const n = +b.dataset.f;
      if (n >= 1 && n <= open) { floeN = n; save('lautta', n); wake(); }
      roomControls();
    });
    RM.extra(roomEl);
  }
  if (RM.isHost) {
    roomEl.innerHTML = FLOES.map((F, i) => `<button data-f="${i + 1}"${i + 1 === floeN ? ' class="on"' : ''}${i + 1 > open ? ' disabled' : ''}>${i + 1 > open ? '🔒 ' : ''}${F.name}</button>`).join('');
  } else {
    const h = (RM.members || []).find(m => m.id === RM.hostId);
    roomEl.innerHTML = `<p class="small">Huoneen tekijä${h ? ' (' + esc(h.name) + ')' : ''} valitsee lautan.</p>`;
  }
}

if (RM) {
  RM.on('start', netStart);
  RM.on('message', (m, from) => {
    if (!net || !m || m.round !== net.round) return;   // another round's message: dropped, never compared by size
    if (RM.isHost) { if (m.t === 'i') hostInput(m, from); return; }
    if (m.t === 's') guestState(m);
    if (m.t === 'end') netEnd(m);
  });
  RM.on('hello', id => {
    if (net && !net.res && world) {
      // The phone is back (a reload or a drop): it takes its seal again from the next state.
      const i = net.recs.findIndex(r => r.id === id);
      if (i >= 0 && net.recs[i].kind === 'net' && !net.recs[i].drive) { world.seals[i].own++; net.recs[i].inT = performance.now(); }
      RM.send(hostState(), id);
    }
    // A phone back after an end it already confirmed: the library does not send it again.
    else if (lastEnd && lastEnd.round === RM.round) RM.send(lastEnd, id);
  });
  RM.on('continue', ids => {
    if (!net || net.res || !world) return;
    const F = FLOES[world.floe - 1];
    net.recs.forEach((rec, i) => {
      if (!ids.includes(rec.id) || rec.kind !== 'net' || rec.drive) return;
      rec.drive = true; rec.helped = true; world.seals[i].own++;
      brains[i] = cpuBrain(F.cpu, world.seed + i * 31 + 7);
    });
  });
  RM.on('back', id => {
    const i = net && world ? net.recs.findIndex(r => r.id === id) : -1;
    if (i < 0 || !net.recs[i].drive) return;
    net.recs[i].drive = false; net.recs[i].inT = performance.now(); world.seals[i].own++;
    world.seals[i].ix = world.seals[i].iy = 0;
  });
  RM.on('lobby', toSolo);
  RM.on('leave', () => { toSolo(); });
  RM.on('menu', () => { if (net) toSolo(); else showMenu(); });
  RM.on('peers', roomControls);
}
