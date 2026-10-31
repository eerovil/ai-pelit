'use strict';
// Out on the ice, playing with friends, every frame's step, the hose and the harpoon.
// ---------- out on the ice (v6, #143) ----------
// SISU is surfaced when it lies centred in an opening with its back out of the water.
function surfaced() { const n = holeAt(sub.x); return n >= 0 && sub.y < SURF + 0.6 && Math.abs(sub.x - holeMid(n)) < 1.5; }
// v8: the hatch is on the tower's top, right over the ladder.
function hatchX() { return sub.x + sub.face * LADDER; }
// Where the feet stand at x on the ice: the shelf, a drift up onto it, the sea ice, and SISU's back across its
// opening (with planks to the edges); null for open water.
function groundAt(x) {
  if (inStation(x)) return STATION.floor - 0.3;  // the station's floor, on its skids
  if (x < SHELF_X) return STATION.floor;
  if (x < SHELF_X + 6) return STATION.floor + (x - SHELF_X) / 6 * (ICE_TOP - STATION.floor);
  const n = holeAt(x);
  if (x > BERG_X[0] && x < BERG_X[1]) return null;  // the iceberg's wall: no way up it
  if (n < 0) return ICE_TOP;
  return surfaced() && holeAt(sub.x) === n ? sub.y - 2.3 : null;
}
function atHatch() { return !walker.climbing && Math.abs(walker.x - hatchX()) < 2.2 && holeAt(walker.x) === holeAt(sub.x); }
function goIce() {
  if (!surfaced()) { toast('SISU ei ole pinnalla'); return; }
  // v8: the person comes up out of the hatch from where they stood inside, then down the tower's side onto SISU's back.
  Object.assign(walker, { x: hatchX(), y: sub.y + Math.min(crew.y, UP), dir: sub.face < 0 ? -1 : 1, to: null, warm: 100, moving: false,
    climbing: true, rise: true, inn: '', suit: crew.suit, kit: crew.kit, walkT: 0, room: '' });
  crew.to = null;
  G.carry = []; G.asked = {}; G.mode = 'ice';
  tone(500, 300, 0.4, 'triangle', 0.05);
  save();
  if (!G.s.flags.jaa && !G.iceSeen) {
    G.iceSeen = true; G.s.flags.jaa = true; save();
    card('Jäällä', [
      { t: 'Pakkasta on kolmekymmentä astetta. 🥶 laskee ulkona ja täyttyy taas sisällä – asemalla tai SISUssa.' },
      { t: 'Tutkimusasema A-3 on lahden pohjukassa, jäätikön reunalla. Takaisin SISUun tornin luukusta.', c: 'msg' },
      { t: 'Jos kylmä voittaa, horjut takaisin SISUun ja mukana olleet löydöt jäävät jäälle.', c: 'small' }],
    [{ label: 'Selvä', cls: 'go', fn: closeCard }]);
  }
}
// Back in through the tower: the person comes in at the tower's top (v8) and climbs down into the control room; the
// host counts the haul. Beaten by the cold, they are simply back in the control room.
function endIce(cold) {
  G.mode = 'home'; walker.inn = '';
  Object.assign(crew, { x: LADDER, y: cold ? UP : TOP, dir: 1, suit: walker.suit, to: cold ? null : { x: LADDER, deck: 0 },
    moving: false, climbing: false });
  enterRoom(true);
  G.carry = [];
  if (cold) {
    act('lost');
    card('Kylmä voitti', [{ t: 'Sormet eivät enää tottele. Horjut tornin luukulle ja valut tikkaita alas lämpimään.' },
      { t: 'Kaikki mukana ollut jäi jäälle. Löydöt odottavat yhä paikoillaan.', c: 'msg' }],
    [{ label: 'Jatka', cls: 'go', fn: closeCard }]);
    return;
  }
  act('home');
}
// v10 (#196): back in the way the person came out: to the tower's foot, up its outside ladder, in through the hatch
// and down into the tower, where endIce takes them on down the inside ladder.
function climbIn() { Object.assign(walker, { inn: 'walk', to: null }); }
function stepIce(dt) {
  const w = walker, x0 = w.x, y0 = w.y;
  if (w.inn === 'walk') {
    const hx = hatchX();
    w.x += Math.sign(hx - w.x) * Math.min(WALK * dt, Math.abs(hx - w.x));
    if (Math.abs(hx - w.x) < 1e-3) { w.x = hx; w.inn = 'up'; w.climbing = true; }
  } else if (w.inn === 'up') {
    w.x = hatchX();
    w.y = Math.max(sub.y - 5.2, w.y - CLIMB * dt);
    if (w.y <= sub.y - 5.2 + 1e-3) w.inn = 'down';
  } else if (w.inn === 'down') {
    w.x = hatchX();
    w.y = Math.min(sub.y + TOP, w.y + CLIMB * dt);
    if (w.y >= sub.y + TOP - 1e-3) { w.inn = ''; w.climbing = false; endIce(false); return; }
  } else if (w.rise) {
    // v8: up through the open hatch onto the tower's top.
    w.y = Math.max(sub.y - 5.2, w.y - CLIMB * dt);
    if (w.y <= sub.y - 5.2 + 1e-3) w.rise = false;
  } else if (w.climbing) {
    // Down the tower's outside ladder onto SISU's back.
    const g = groundAt(w.x);
    w.y = Math.min(g == null ? w.y : g, w.y + CLIMB * dt);
    if (g == null || w.y >= g - 1e-3) w.climbing = false;
  } else {
    if (input.x) w.to = null;  // the stick takes over from a tap
    const vx = w.to != null ? Math.sign(w.to - w.x) * Math.min(WALK, Math.abs(w.to - w.x) / dt) : input.x * WALK;
    let nx = w.x + vx * dt;
    if (inStation(w.x)) nx = Math.max(STATION.x0 + 0.6, nx);  // the station's far wall
    nx = Math.max(36, Math.min(WORLD_W - 10, nx));
    const g = groundAt(nx);
    if (g == null) {
      w.to = null;
      if (G.iceCd <= 0) { toast(nx > BERG_X[0] && nx < BERG_X[1] ? 'Jäävuoren seinä: tästä ei pääse' : 'Railo: avovettä edessä', 1.2); G.iceCd = 1; }  // stays up while the stick pushes
    } else { w.x = nx; w.y = g; }
    if (w.to != null && Math.abs(w.to - w.x) < 0.02) w.to = null;
  }
  const dx = w.x - x0;
  if (Math.abs(dx) > 1e-4) w.dir = Math.sign(dx);
  w.moving = Math.abs(dx) > 1e-4 || Math.abs(w.y - y0) > 1e-4;
  w.walkT += Math.abs(dx) + Math.abs(w.y - y0);
  // The cold outside; the station's rooms keep the wind off.
  const inside = inStation(w.x);
  // v8: coming up through the hatch the person is still in the tower, out of the wind.
  w.warm = inside || w.rise || w.inn === 'down' ? Math.min(100, w.warm + dt * WARMUP) : w.warm - dt * 100 / WARM;
  const r = inside ? stationRoom(w.x) : null, rid = r ? r.id : '';
  if (rid !== w.room) { w.room = rid; if (rid === 'seteinen' && x0 >= STATION.x1) toast('Sisällä asemalla: täällä lämpenee', 1.6); }
  if (inside) for (const it of ICE_ITEMS) {
    if (!itemHere(it) || G.asked[it.id] || Math.abs(it.x - w.x) > 1.1) continue;
    G.asked[it.id] = true;
    act('take', it.id);
    if (G.paused) return;  // a note's card
  }
  if (w.warm <= 0) endIce(true);
  else if (w.warm < 25 && G.warnCd <= 0) { toast('Kylmä! Mene sisälle'); G.warnCd = 4; tone(400, 300, 0.3, 'square', 0.05); }
}

// The night, on the host (or alone) once everyone is in the bunk room; every phone gets the new day's card.
function sleep() {
  const s = G.s;
  s.day++;
  s.caught = {};  // v8: the schools are whole again
  s.m.food = Math.max(0, s.m.food - 12);
  s.m.health = Math.min(100, s.m.health + 15);
  newFinds();
  save();
  story('day');
}
// Small random finds the current brings each night: a crate, a buoy, a lost bag.
function newFinds() {
  const s = G.s, max = [0, 820, 1640, 2700, 3100, 3640, 4440][s.up.hull];
  for (let tries = 0; s.finds.length < 3 && tries < 40; tries++) {
    // Rounded before the checks: on the steep slope a find moved half a metre after them could end up in the rock.
    const x = Math.round(260 + Math.random() * (max - 260)), y = Math.floor((floorY(x) - 0.9) * 10) / 10;
    if (y > RATING[s.up.hull] - 4 || siteAt(x, y) || siteAt(x, y - 6) || diverHits(x, y)) continue;
    const r = Math.random(), deep = x > 2450 ? 0.15 : 0;  // the slope's finds are more often spare parts
    s.finds.push({ id: 'f' + (s.findN++), k: r < 0.6 - deep ? 'ruoka' : r < 0.78 ? 'osa' : r < 0.9 ? 'laake' : 'ohjain', x, y });
  }
}

// ---------- playing with friends (v5, #138) ----------
// The phone that made the room (the host) keeps the game: its own save, SISU's stores, meters, day and story. Each
// friend has their own person, walked and swum on their own phone, which tells the host where it is ('me', ten
// times a second); whoever is at the helm drives SISU on their phone the same way. The host sends everyone the
// game when it changes ('s'), where everybody and SISU are ('f'), the story's moments ('card') and the answer to
// each thing a friend asked for ('re', see `act`). A friend's phone never saves.
const R = window.AiPelitRooms;
const COLS = ['#4fa3ff', '#3fcf7f', '#ff8a5c', '#c88aff'];
const r2 = v => Math.round(v * 100) / 100;
// Everyone in the game, this phone's player first: where they are ('sub' at the helm, 'home' inside, 'dive' out).
function people() {
  const mine = { id: me(), name: net ? nameOf(R.me) : '', mode: G.mode, room: G.mode === 'home' ? crew.room : '' };
  if (!net) return [mine];
  return [mine].concat(Object.entries(net.others).filter(([, o]) => o.mode !== 'wait').map(([id, o]) =>
    ({ id, name: o.name, mode: o.mode, room: o.mode === 'home' ? (roomOf(o.tx, o.ty) || {}).id || '' : '' })));
}
function present(id) { return id === me() || !!(net && net.others[id] && net.others[id].mode !== 'wait'); }
function nameOf(id) { return (net && net.names[id]) || 'Kaveri'; }
// v7: a diver's hose goes with it, [cut, wear %, x1, y1, x2, y2, ...], so the other phones draw it as worn as it is.
function hosePack() { return [hose.cut ? 1 : 0, Math.round(hose.wear)].concat(...hose.pts.map(p => [Math.round(p[0] * 10) / 10, Math.round(p[1] * 10) / 10])); }
function mine() {
  const d = G.mode === 'dive', b = d ? diver : G.mode === 'ice' ? walker : crew;
  return [G.mode, r2(b.x), r2(b.y), b.dir, crew.suit ? (crew.kit === 'hose' ? 2 : 1) : 0, d ? r2(diver.ang) : 0,
    d && diver.kit === 'hose' ? hosePack() : 0];
}
function subPack() { return [r2(sub.x), r2(sub.y), sub.dir, r2(sub.vx), r2(sub.vy)]; }
function setOther(id, p) {
  const o = net.others[id];
  if (!o || !Array.isArray(p)) return;
  const jump = o.mode !== p[0];
  [o.mode, o.tx, o.ty, o.dir, o.suit, o.ang] = [String(p[0]), +p[1] || 0, +p[2] || 0, p[3] < 0 ? -1 : 1, !!p[4], +p[5] || 0];
  o.kit = p[4] === 2 ? 'hose' : 'tank';
  o.hose = Array.isArray(p[6]) ? p[6].slice(0, 122).map(Number) : null;
  if (jump) { o.x = o.tx; o.y = o.ty; }
}
function sendState(to) { if (net && net.host && G.s) { R.send({ t: 's', s: G.s }, to); if (!to) net.dirty = false; } }
function snapshot() {
  const ps = { [R.me]: mine() };
  for (const [id, o] of Object.entries(net.others)) ps[id] = [o.mode, o.tx, o.ty, o.dir, o.suit ? (o.kit === 'hose' ? 2 : 1) : 0, o.ang, o.hose || 0];
  const m = G.s.m;
  const A = G.auto;
  return { t: 'f', sub: subPack(), helm: net.helm, held: G.held, m: [r2(m.food), r2(m.health), r2(m.hull)], ps,
    auto: A ? [A.id, A.name, Math.round(A.left || 0), A.pts.slice(A.i).flat().map(Math.round)] : 0 };
}
function stepNet(dt) {
  // The others glide to where their phones last said; SISU too, unless this phone drives it.
  const k = Math.min(1, dt * 10);
  for (const o of Object.values(net.others)) {
    const x0 = o.x, y0 = o.y;
    if (Math.hypot(o.tx - o.x, o.ty - o.y) > 8) { o.x = o.tx; o.y = o.ty; }
    o.x += (o.tx - o.x) * k; o.y += (o.ty - o.y) * k;
    const d = Math.abs(o.x - x0) + Math.abs(o.y - y0);
    o.moving = d > 0.002; o.walkT += d;
    const g = o.mode === 'ice' ? groundAt(o.x) : null;
    o.climbing = o.mode === 'home' ? o.y > UP + 0.05 && o.y < LOW - 0.05 : g != null && o.y < g - 0.3;
  }
  const T = net.subT;
  if (T && G.mode !== 'sub') {
    if (Math.hypot(T[0] - sub.x, T[1] - sub.y) > 40) { sub.x = T[0]; sub.y = T[1]; }
    sub.x += (T[0] - sub.x) * k; sub.y += (T[1] - sub.y) * k; sub.dir = T[2] < 0 ? -1 : 1; sub.vx = T[3]; sub.vy = T[4];
    sub.prop += dt * (2 + Math.abs(sub.vx));
  }
  if ((net.sendT -= dt) > 0) return;
  net.sendT = 0.1;
  if (net.host) { if (net.dirty) sendState(); R.send(snapshot()); }
  else if (G.s && G.mode !== 'wait') R.send(G.mode === 'sub' ? { t: 'me', p: mine(), sub: subPack() } : { t: 'me', p: mine() });
}
// A friend's phone, once the host's game has arrived: their person starts in the control room.
function guestBegin() {
  const s = G.s;
  G.carry = []; G.lastGoal = '';
  sub.x = s.sub.x; sub.y = s.sub.y; sub.dir = sub.face = s.sub.dir || 1; sub.vx = sub.vy = 0;
  G.cx = sub.x; G.cy = sub.y; G.sc = homeScale(); G.mode = 'home';
  Object.assign(crew, { x: 0.6, y: UP, dir: 1, suit: false, to: null, moving: false, climbing: false });
  enterRoom(true);
  show('menu', false); show('toast', false); G.toastT = 0;
  card('Mukana SISUssa', [
    { t: `SISU ja sen tallennus ovat huoneen tekijän (${nameOf(R.hostId)}). Sinä tulit auttamaan – omaan peliisi tämä ei koske.` },
    { t: 'Kävele huoneesta toiseen, pue puku ja sukella ilmalukosta. Ruorissa on yksi kerrallaan: kuka ehtii ensin.', c: 'msg' },
    { t: 'Löydöt lasketaan, kun tuot ne ilmalukkoon. Nukkumaan mennään yhdessä: kaikki punkkaan.', c: 'small' }],
  [{ label: 'Selvä', cls: 'go', fn: closeCard }]);
}
// Out of the game: the HUD goes, and a friend's phone forgets the host's game.
function quiet() {
  if (net && !net.host) G.s = null;
  net = null; G.mode = 'menu'; G.carry = []; G.held = {}; G.auto = null; G.coast = false; sub.vx = sub.vy = 0;  // v9: a trip ends with the round
  closeCard(); for (const id of ['hud', 'pad', 'home', 'toast', 'chart']) show(id, false);  // v9: the chart too
  CV.sel = null;
}
// The host takes everyone back to the room, where new friends can come in; "Aloita kierros" carries on the same save.
function toRoom() {
  if (!net || !net.host) return;
  save(); R.deliver({ t: 'end' }); R.endRound();
  quiet(); R.backToRoom('Retki jatkuu, kun aloitat kierroksen.');
}
R.on('start', st => {
  quiet();
  net = { host: st.host, others: {}, names: {}, cols: {}, helm: null, sendT: 0, dirty: true, subT: null };
  st.players.forEach((p, n) => {
    net.names[p.id] = p.name; net.cols[p.id] = COLS[n % COLS.length];
    if (p.id !== R.me) net.others[p.id] = { name: p.name, mode: 'wait', x: 0, y: 0, tx: 0, ty: 0, dir: 1, suit: false, ang: 0, walkT: 0 };
  });
  if (st.over) { quiet(); return; }
  if (st.host) {
    const s = load();
    if (s) begin(s); else newGame();
    net.helm = R.me; sendState();
  } else { G.s = null; G.mode = 'wait'; show('menu', false); toast('Odotetaan huoneen tekijää…', 4); }
});
R.on('message', (m, from) => {
  if (!net || !m) return;
  if (net.host) {
    if (!net.others[from] || !G.s) return;
    if (m.t === 'me') { setOther(from, m.p); if (net.helm === from && Array.isArray(m.sub) && m.p[0] === 'sub') net.subT = m.sub; }
    if (m.t === 'do') {
      setOther(from, m.p);
      const r = doAct(from, String(m.a), m.arg);
      if (net.dirty) sendState();  // the game as it is now reaches them before the answer
      if (r) R.send(Object.assign({ t: 're' }, r), from);
    }
    return;
  }
  if (m.t === 's' && m.s) { G.s = m.s; if (G.mode === 'wait') guestBegin(); return; }
  if (!G.s || G.mode === 'wait') return;
  if (m.t === 'f') {
    G.held = m.held || {}; net.helm = m.helm || null;
    // v9: the host's autopilot, shown on the chart and in the HUD of every phone
    if (Array.isArray(m.auto)) {
      const p = Array.isArray(m.auto[3]) ? m.auto[3] : [], pts = [];
      for (let k = 0; k + 1 < p.length; k += 2) pts.push([+p[k], +p[k + 1]]);
      G.auto = { id: String(m.auto[0]), name: String(m.auto[1]), left: +m.auto[2] || 0, pts, i: 0 };
    } else G.auto = null;
    if (Array.isArray(m.m)) [G.s.m.food, G.s.m.health, G.s.m.hull] = m.m;
    for (const [id, p] of Object.entries(m.ps || {})) if (id !== R.me) setOther(id, p);
    if (G.mode !== 'sub') net.subT = m.sub;
  }
  if (m.t === 're') answer(m);
  if (m.t === 'card') showStory(m);
  if (m.t === 'end') { quiet(); R.backToRoom('Retki jatkuu, kun huoneen tekijä aloittaa kierroksen.'); }
});
// Host: a friend's phone is back (a reload): its person starts again in the control room, its haul lost.
function letGo(id) {
  for (const k of Object.keys(G.held)) if (G.held[k] === id) delete G.held[k];
  if (net.helm === id) { net.helm = null; stopSub(); }
}
// Host: nobody drives now, so SISU stays where its driver left it, still (else its last speed would keep the airlock shut).
function stopSub() { if (net && net.subT) net.subT = [net.subT[0], net.subT[1], net.subT[2], 0, 0]; }
R.on('hello', id => {
  if (!net || !net.host || !net.others[id]) return;
  letGo(id); net.others[id].mode = 'wait';
  sendState(id); R.send(snapshot(), id);
});
R.on('continue', ids => { if (net && net.host) for (const id of ids) { letGo(id); delete net.others[id]; } });
R.on('back', id => {
  if (net && net.host && net.names[id]) net.others[id] = { name: net.names[id], mode: 'wait', x: 0, y: 0, tx: 0, ty: 0, dir: 1, suit: false, ang: 0, walkT: 0 };
});
R.on('lobby', () => { quiet(); });
R.on('leave', () => { quiet(); menu(); });
R.on('menu', () => { quiet(); menu(); });
$('multi').addEventListener('click', () => { audio(); R.open(); });

// ---------- every frame ----------
function subScale() { return Math.min(W, H) / 110; }
// In a big cave (the iceberg's great chamber) the view widens to show its walls; inside Nordlys a little too.
function diveScale() {
  let span = 24;
  for (const c of BERG.caves) if (c[4] >= 5 && segDist(diver.x, diver.y, c[0], c[1], c[2], c[3]) < c[4]) span = Math.max(span, c[4] * 2 + 10);
  const n = SITES.find(s => s.id === 'nordlys');
  if (diver.x > n.x && diver.x < n.x + n.w * C && diver.y > n.y && diver.y < n.y + n.h * C) span = 30;
  return Math.min(W, H) / span;
}
// Deep down SISU's engines run harder, so the long way down the slope does not drag.
function subBoost() { return Math.min(2.2, 1 + Math.max(0, sub.y - 300) / 500); }
// Cold water below COLD drains the diver's air faster, except in a hot vent's warm water.
function chill() { return diver.y > COLD && !nearVent(diver.x, diver.y, 16) ? 1 + (CHILL - 1) * lab('bakteeri', 0.45) : 1; }
// On the ice the view is a little wider than inside SISU: about 19 m across the narrow side.
function iceScale() { return Math.min(W, H) / 19; }
function homeScale() { return W > H ? Math.min((W - 30) / 30, (H - 150) / 8) : W / 14; }
function needs(dt) {
  const m = G.s.m;
  m.food = Math.max(0, m.food - dt * 100 / 720);
  if (m.food <= 0) m.health -= dt * 0.4;
  if (m.health <= 0) faint();
  if (m.hull <= 0) breach();
}
// Fainting and the hull giving way happen on the host (or alone); every phone gets the card and what it does to
// its own person (`showStory`).
function faint() {
  const s = G.s;
  s.day++; s.m.health = 35; s.m.food = Math.max(s.m.food, 25);
  G.held = {}; if (net) { net.helm = null; stopSub(); }
  save();
  story('faint');
}
function breach() {
  const s = G.s;
  s.m.hull = 25; s.m.health = Math.max(10, s.m.health - 15);
  G.held = {};  // every diver's haul is lost
  if (net && net.helm && net.helm !== me()) net.helm = present(net.helm) ? net.helm : null;
  // v2: the emergency ballast lifts SISU only into safe water, not all the way to the surface from the deep sea.
  sub.y = Math.max(10, Math.min(sub.y, RATING[s.up.hull] - 40)); sub.vx = sub.vy = 0;
  while (subHits(sub.x, sub.y) && sub.y > 10) sub.y -= 4;
  while (subHits(sub.x, sub.y) && sub.x > 300) sub.x -= 10;
  save();
  story('breach', { sub: [sub.x, sub.y] });
}
// `steer` (v9): the autopilot's stick instead of the player's.
function stepSub(dt, steer) {
  const k = subBoost();
  let inp = steer || input;
  // With friends (v5) SISU holds still while someone is out: their way home is the airlock.
  const out = net ? people().filter(p => p.mode === 'dive' || p.mode === 'ice') : [];
  if (out.length) {
    inp = { x: 0, y: 0 };
    if ((input.x || input.y) && G.warnCd <= 0) {
      toast('Odota: ' + out.map(p => p.name + (p.mode === 'ice' ? ' on jäällä' : ' sukeltaa')).join(', '), 1.6); G.warnCd = 2.5;
    }
  }
  sub.vx += (inp.x * SUB_SPEED * lab('vesi', 1.1) * k - sub.vx) * Math.min(1, dt * (inp.x ? 0.9 : 0.6));
  sub.vy += (inp.y * 7 * k - sub.vy) * Math.min(1, dt * 1.3);
  if (inp.x > 0.2) sub.dir = 1; else if (inp.x < -0.2) sub.dir = -1;
  const nx = sub.x + sub.vx * dt;
  if (subHits(nx, sub.y)) { if (!onlyIce(nx, sub.y)) bump(Math.abs(sub.vx) / k); sub.vx *= -0.3; } else sub.x = nx;
  const hole = holeAt(sub.x), ny = Math.max(hole >= 0 ? SURF : 4, sub.y + sub.vy * dt);
  if (subHits(sub.x, ny)) {
    // v6: the ice overhead stops SISU softly, and says where the way up is.
    if (sub.vy < 0 && onlyIce(sub.x, ny)) {
      if (G.iceCd <= 0) { toast('Jää yläpuolella – pintaan pääsee vain railoista 📡', 2.2); G.iceCd = 4; tone(160, 120, 0.3, 'triangle', 0.05); }
    } else bump(Math.abs(sub.vy) / k);
    sub.vy *= -0.3;
  } else sub.y = ny;
  // Under an opening SISU is drawn to its middle, so it comes up straight without scraping the edges.
  if (hole >= 0 && sub.y < ICE_Y + 8 && Math.abs(inp.x) < 0.3) {
    const nx2 = sub.x + (holeMid(hole) - sub.x) * Math.min(1, dt * 2);
    if (!subHits(nx2, sub.y)) sub.x = nx2;
  }
  if (surfaced() && !G.s.flags.pinnalla) {
    G.s.flags.pinnalla = true;
    toast('Pinnalla! 🏠 sisälle ja tikkaita ylös torniin', 3);
  }
  sub.prop += dt * (2 + Math.abs(sub.vx));
  // A glowing fish that meets SISU bumps the hull a little.
  for (let n = 0; n < FISH.length && G.fishCd <= 0; n++) {
    const f = fishAt(n, G.t);
    if (Math.abs(f.x - sub.x) < 15 && Math.abs(f.y - sub.y) < 3.5) {
      hurt(5 * lab('suomu', 0.5)); G.fishCd = 3; clang(); toast('Valokala törmäsi runkoon', 1.4);
    }
  }
}
// The sea presses on SISU wherever the player is (v4, #132): at the helm, out on a dive or walking inside. v3 and
// earlier only did this while driving, so diving out or going inside below the hull's rating saved the hull.
// With friends (v5) the host's hull takes the damage; every phone warns its own player.
function pressure(dt) {
  const s = G.s, helm = G.mode === 'sub', mine = !net || net.host;
  if (sub.y > RATING[s.up.hull]) {
    if (mine) s.m.hull -= dt * 4;
    if (G.warnCd <= 0) { toast(helm ? 'PAINE! Nouse ylemmäs' : 'PAINE! SISU on liian syvällä'); tone(70, 50, 0.8, 'sawtooth', 0.06); G.warnCd = 2.5; }
    if (mine && s.m.hull <= 0) breach();
  } else if (helm && sub.y > RATING[s.up.hull] - 25 && G.warnCd <= 0) {
    toast('Runko natisee', 1.2); tone(90, 70, 0.6, 'triangle', 0.05); G.warnCd = 5;
  }
}
// Damage SISU's driver causes: on a friend's phone it goes to the host.
function hurt(n) { if (net && !net.host) act('dmg', n); else G.s.m.hull -= n; }
function bump(v) {
  if (v < 4 || G.hitCd > 0) return;
  hurt((v - 4) * 2.2);
  G.hitCd = 0.6;
  clang(); toast('Kolahdus!', 0.8);
}
// ---------- the hose (v7, #145) ----------
// The hose runs from the airlock round the corners it has caught on (`hose.pts`) to the diver. When the straight line
// from the last corner to the diver is blocked, the hose catches on a new corner; when the diver can see the corner
// before it again, it slips off. Its length is the sum of those straight pieces.
function clearLine(ax, ay, bx, by) {
  const d = Math.hypot(bx - ax, by - ay), n = Math.ceil(d / 0.4);
  for (let k = 1; k < n; k++) {
    const t = k / n;
    if (t * d < 0.25 || (1 - t) * d < 0.25) continue;
    const x = ax + (bx - ax) * t, y = ay + (by - ay) * t;
    // Lying along a wall or grazing a corner is clear: only a point inside the wall all round blocks the line.
    if (solid(x, y) && solid(x + 0.2, y) && solid(x - 0.2, y) && solid(x, y + 0.2) && solid(x, y - 0.2)) return false;
  }
  return true;
}
function hoseLen(x, y, pts = hose.pts) {
  const a = airlock();
  let L = 0, px = a.x, py = a.y;
  for (const p of pts) { L += Math.hypot(p[0] - px, p[1] - py); px = p[0]; py = p[1]; }
  return L + Math.hypot(x - px, y - py);
}
function guided(p) { return G.s.guides.some(g => Math.hypot(g[0] - p[0], g[1] - p[1]) < GUIDE_R); }
// The hose follows the diver, who moved from (px, py): slip off corners, catch on new ones.
function hoseFollow(px, py) {
  const ps = hose.pts, a = airlock();
  while (ps.length) {
    const b = ps.length > 1 ? ps[ps.length - 2] : [a.x, a.y];
    if (!clearLine(b[0], b[1], diver.x, diver.y)) break;
    ps.pop();
  }
  const b = ps.length ? ps[ps.length - 1] : [a.x, a.y];
  if (ps.length < 60 && !clearLine(b[0], b[1], diver.x, diver.y)) {
    // The corner lies on the old line (b → where the diver was): the point on it nearest b that still sees the diver.
    let lo = 0, hi = 1;
    for (let k = 0; k < 14; k++) {
      const m = (lo + hi) / 2;
      if (clearLine(b[0] + (px - b[0]) * m, b[1] + (py - b[1]) * m, diver.x, diver.y)) hi = m; else lo = m;
    }
    const q = [b[0] + (px - b[0]) * hi, b[1] + (py - b[1]) * hi], l = Math.hypot(px - q[0], py - q[1]) || 1;
    // and just outside the wall, towards where the diver was, so the hose lies on the wall rather than in it
    for (let k = 0; k < 30 && solid(q[0], q[1]); k++) { q[0] += (px - q[0]) / l * 0.1; q[1] += (py - q[1]) / l * 0.1; }
    if (Math.hypot(q[0] - b[0], q[1] - b[1]) > 0.5) { ps.push([q[0], q[1], siteAt(q[0], q[1]) ? 1 : 0]); tidyHose(); }
  }
}
// Rounding a corner leaves a row of points close together on it: drop each one the hose runs straight past.
function tidyHose() {
  const ps = hose.pts, a = airlock();
  for (let k = ps.length - 1; k >= 0; k--) {
    const b = k ? ps[k - 1] : [a.x, a.y], c = k + 1 < ps.length ? ps[k + 1] : [diver.x, diver.y];
    if (clearLine(b[0], b[1], c[0], c[1])) ps.splice(k, 1);
  }
}
// The corners the hose rubs on: points within 1.5 m of each other are one corner, and a guided one does not rub.
function rubbing(pts = hose.pts) {
  let rub = 0, last = null;
  for (const p of pts) {
    const same = last && Math.hypot(p[0] - last[0], p[1] - last[1]) < 1.5;
    last = p;
    if (same || guided(p)) continue;
    rub += p[2] ? WEAR.metal : WEAR.ice * lab('jaa', 0.5);
  }
  return rub;
}
// An unguided corner of this diver's hose within reach, where a guide could be clamped.
function guideSpot() {
  if (G.mode !== 'dive') return null;
  let best = null, bd = 3;
  for (const p of hose.pts) {
    const d = Math.hypot(p[0] - diver.x, p[1] - diver.y);
    if (d < bd && !guided(p)) { best = p; bd = d; }
  }
  return best;
}
// v10 (#196): the clamped guide nearest the diver, within reach, to take off again.
function guideNear() {
  if (G.mode !== 'dive') return null;
  let best = null, bd = 3;
  for (const g of G.s.guides) {
    const d = Math.hypot(g[0] - diver.x, g[1] - diver.y);
    if (d < bd) { best = g; bd = d; }
  }
  return best;
}
function cutHose(why) {
  if (hose.cut) return;
  hose.cut = true; hose.wear = 100; diver.air = EMERG;
  toast(why + ' Hätähappea ' + EMERG + '\u00a0s – ui ilmalukkoon!', 2.6);
  clang(); tone(500, 200, 0.6, 'square', 0.06);
}
function wearHose(n) {
  hose.wear = Math.min(100, hose.wear + n);
  if (hose.wear >= 100) cutHose('Letku katkesi!');
}

// ---------- the harpoon (v8, #151) ----------
// One spear at a time, along the way the diver swims (or faces, when still), turned onto a fish just off that line;
// it flies SPEAR.range metres, stops in a wall or the ice, and a fish it meets is the diver's to carry home.
function fire() {
  if (G.mode !== 'dive' || G.harpCd > 0 || G.paused) return;
  G.harpCd = SPEAR.reload;
  let ang = Math.hypot(diver.vx, diver.vy) > 0.6 ? Math.atan2(diver.vy, diver.vx) : diver.dir > 0 ? 0 : Math.PI, best = null, bd = SPEAR.range;
  for (const f of fishNow()) {
    const dx = f.x - diver.x, dy = f.y - diver.y, d = Math.hypot(dx, dy);
    const off = Math.abs((Math.atan2(dy, dx) - ang + 3 * Math.PI) % (2 * Math.PI) - Math.PI);
    if (d < bd && off < 0.45 && clearLine(diver.x, diver.y, f.x, f.y)) { best = f; bd = d; }
  }
  if (best) ang = Math.atan2(best.y - diver.y, best.x - diver.x);
  diver.dir = Math.cos(ang) >= 0 ? 1 : -1;
  G.spear = { x: diver.x + Math.cos(ang) * 0.8, y: diver.y + Math.sin(ang) * 0.8, a: ang, d: 0, stuck: 0 };
  tone(240, 90, 0.18, 'square', 0.05); tone(900, 400, 0.12, 'triangle', 0.03);
}
$('harp').addEventListener('click', () => { audio(); fire(); drawHud(); });
function stepSpear(dt) {
  const p = G.spear;
  if (!p) return;
  if (p.stuck) { if ((p.stuck -= dt) <= 0) G.spear = null; return; }
  const n = Math.max(1, Math.ceil(SPEAR.speed * dt / 0.3)), st = SPEAR.speed * dt / n;
  for (let i = 0; i < n; i++) {
    p.x += Math.cos(p.a) * st; p.y += Math.sin(p.a) * st; p.d += st;
    if (solid(p.x, p.y)) { p.stuck = 0.8; tone(160, 120, 0.1, 'square', 0.03); return; }
    const f = fishNow().find(f => Math.hypot(f.x - p.x, f.y - p.y) < SPEAR.hit);
    if (f) {
      G.spear = null; G.pending[f.n + ':' + f.k] = true;
      act('fish', [f.n, f.k]);
      return;
    }
    if (p.d > SPEAR.range) { G.spear = null; return; }
  }
}
function stepDive(dt) {
  stepSpear(dt);
  // v9: the first time in the dark iceberg, what the lamp does there
  if (!G.darkSaid && bergView()) { G.darkSaid = true; toast('Pimeää: vain valokeila näyttää. Seinät piirtyvät karttaan.', 2.8); }
  // The first school near a diver: what the harpoon is for.
  if (!G.parviSaid && !(G.s.flags.parvi) && fishNow().some(f => Math.hypot(f.x - diver.x, f.y - diver.y) < 14)) {
    G.parviSaid = true;
    if (!net || net.host) { G.s.flags.parvi = true; save(); }
    toast('Kalaparvi! 🔱 Harppuunalla saat ruokaa', 2.4);
  }
  diver.vx += (input.x * DIVER_SPEED - diver.vx) * Math.min(1, dt * 3);
  diver.vy += (input.y * DIVER_SPEED - diver.vy) * Math.min(1, dt * 3);
  if (Math.abs(diver.vx) > 0.3) diver.dir = Math.sign(diver.vx);
  const onHose = diver.kit === 'hose' && !hose.cut;
  const px = diver.x, py = diver.y, L0 = onHose ? hoseLen(px, py) : 0, max = HOSE[G.s.up.hose];
  // A move that would pull the hose past its length is held back, as a wall would; the tank gear stops at its depth (v7).
  const deep = y => diver.kit === 'tank' && y > TANK_MAX && y > py;
  const taut = (x, y) => onHose && hoseLen(x, y) > max && hoseLen(x, y) > L0;
  let held = false;
  const nx = diver.x + diver.vx * dt;
  if (diverHits(nx, diver.y)) diver.vx = 0; else if (taut(nx, diver.y)) { diver.vx = 0; held = true; } else diver.x = nx;
  const ny = Math.max(1, diver.y + diver.vy * dt);
  if (diverHits(diver.x, ny)) diver.vy = 0; else if (taut(diver.x, ny)) { diver.vy = 0; held = true; }
  else if (deep(ny)) {
    diver.vy = 0;
    if (G.warnCd <= 0) { toast('Säiliöpuku ei kestä syvemmälle', 1.4); G.warnCd = 2.5; tone(90, 70, 0.4, 'triangle', 0.05); }
  } else diver.y = ny;
  if (held && G.warnCd <= 0) { toast('Letku on lopussa (' + max + ' m). Aja SISU lähemmäs tai pidennä letkua.', 2.2); G.warnCd = 2.5; tone(260, 200, 0.2, 'triangle', 0.05); }
  diver.ang += ((Math.hypot(diver.vx, diver.vy) > 0.5 ? Math.atan2(diver.vy, Math.abs(diver.vx)) * 0.6 : 0) - diver.ang) * Math.min(1, dt * 5);
  if (onHose) {
    // The move counts only if the hose, caught on any new corner, still reaches: else the diver and the corners
    // stay where they were.
    const before = hose.pts.map(p => p.slice());
    hoseFollow(px, py);
    if (hoseLen(diver.x, diver.y) > max && hoseLen(diver.x, diver.y) > L0 + 1e-6) {
      hose.pts = before; diver.x = px; diver.y = py; diver.vx = diver.vy = 0;
      if (G.warnCd <= 0) { toast('Letku on lopussa (' + max + ' m). Aja SISU lähemmäs tai pidennä letkua.', 2.2); G.warnCd = 2.5; tone(260, 200, 0.2, 'triangle', 0.05); }
    }
    hose.len = hoseLen(diver.x, diver.y);
    // The hose slides over every corner it bends round as it pays out or reels in; an unguided corner wears it,
    // sharp metal twice as fast as ice or rock. A longer hose level is also a tougher one.
    const rub = rubbing();
    if (rub) {
      const before = hose.wear;
      wearHose(Math.abs(hose.len - L0) * rub * TOUGH[G.s.up.hose]);
      if (!hose.cut && G.ropeCd <= 0 && hose.wear > before + 1e-4 && G.warnCd <= 0) {
        G.ropeCd = 6; toast(hose.wear > 60 ? 'Letku on kulunut! Kiinnitä kulmaan 📌 ohjain' : 'Letku hankaa kulmaan', 1.6);
      }
    }
  } else {
    // The tank, or a cut hose's emergency air: faster in cold water.
    diver.air -= dt * chill();
    if (chill() > 1 && !G.coldSaid) { G.coldSaid = true; toast('Kylmä vesi: happi kuluu nopeammin'); }
  }
  for (let n = 0; n < FISH.length && G.fishCd <= 0; n++) {
    const f = fishAt(n, G.t), d = Math.hypot(f.x - diver.x, f.y - diver.y);
    if (d < 2.8) {
      G.fishCd = 3;
      diver.vx = (diver.x - f.x) / d * 6; diver.vy = (diver.y - f.y) / d * 6;
      tone(220, 140, 0.3, 'square', 0.05);
      // A fish bites the hose (v7); otherwise it costs air (8 s from a tank, 5 s of emergency air), never the last second.
      if (!onHose) { const n = (diver.kit === 'hose' ? 5 : 8) * lab('suomu', 0.5); diver.air = Math.max(1, diver.air - n); toast(`Valokala tönäisi! −${n} s happea`, 1.6); }
      else {
        const bite = FISH_BITE * TOUGH[G.s.up.hose] * lab('suomu', 0.5);
        wearHose(bite);
        if (!hose.cut) toast('Valokala puri letkua! −' + Math.round(bite) + ' %', 1.6);
      }
    }
  }
  if (Math.random() < dt * 2.5) bubbles.push({ x: diver.x + diver.dir * 0.5, y: diver.y - 0.4, t: 0 });
  for (const it of allItems()) {
    if (!itemHere(it) || Math.hypot(it.x - diver.x, it.y - diver.y) > 1.7) continue;
    if (it.k === 'ilma') {
      // An air pocket fills a tank, or a cut hose's emergency air (v7); the hose suit breathes from the hose.
      const full = diver.kit === 'hose' ? EMERG : TANK[G.s.up.tank];
      if ((diver.kit === 'tank' || hose.cut) && diver.air < full - 1) { diver.air = full; toast('Ilmatasku: happi täyttyy'); tone(600, 900, 0.3, 'sine', 0.06); }
      continue;
    }
    // Each find is asked for once a dive; with friends the host gives it to whoever asked first.
    if (G.asked[it.id]) continue;
    G.asked[it.id] = true;
    act('take', it.id);
    if (G.paused) return;  // a log's card
  }
  if (diver.kit === 'hose' && !hose.cut) return;
  if (diver.air <= 0) endDive(true);
  else if (diver.air < 12 && G.warnCd <= 0) { toast('Happi vähissä!'); G.warnCd = 4; tone(400, 300, 0.3, 'square', 0.05); }
}
function step(dt) {
  G.t += dt;
  syncMaps();
  G.hitCd -= dt; G.warnCd -= dt; G.fishCd -= dt; G.iceCd -= dt; G.ropeCd -= dt; G.pingCd = Math.max(0, G.pingCd - dt);
  G.harpCd = Math.max(0, G.harpCd - dt);
  if (G.toastT > 0 && (G.toastT -= dt) <= 0) show('toast', false);
  const playing = G.mode === 'sub' || G.mode === 'dive' || G.mode === 'home' || G.mode === 'ice';
  // With friends (v5) a card stops only this phone's own person: the sea goes on for the others. The room stops
  // everything while a phone in it is away.
  const away = net && R.paused;
  if (!G.paused && !away) {
    if (G.mode === 'sub') stepSub(dt);
    else if (G.mode === 'dive') stepDive(dt);
    else if (G.mode === 'home') stepCrew(dt);
    else if (G.mode === 'ice') stepIce(dt);
  }
  // v9: the autopilot drives SISU on the host (or alone) whatever this phone's person is doing.
  if (G.auto && G.s && (!net || net.host) && !away && G.mode !== 'sub') stepAuto(dt);
  else if (G.coast && G.s && (!net || net.host) && !away) {
    // At the helm the driver's own stick takes over; let go, SISU still settles to a full stop.
    if (G.mode === 'sub') { if (input.x || input.y) G.coast = false; else if (Math.hypot(sub.vx, sub.vy) < 0.3) { sub.vx = sub.vy = 0; G.coast = false; } }
    else if (net && net.helm && present(net.helm)) G.coast = false; else stepCoast(dt);
  }
  if (net && !away) stepNet(dt);
  if (G.card === 'chart' && (G.chartT = (G.chartT || 0) - dt) <= 0) { G.chartT = 0.25; drawChart(); }
  // v9: alone, an open card or chart stops only the person; while the autopilot drives (or SISU glides after it), the sea, hunger, pressure,
  // saving and the chart go on.
  if (playing && (net ? !away : !G.paused || G.auto || G.coast)) {
    pressure(dt);
    if (!net || net.host) {
      // Saved every 4 s in every mode (v4): pressure damage on a dive or inside must survive a reload too.
      G.saveCd -= dt;
      if (G.saveCd <= 0) { save(); G.saveCd = 4; }
      if ((G.mapT = (G.mapT || 0) - dt) <= 0) { G.mapT = 0.1; mapStep(); }
      // Hunger runs while someone is at the helm or out diving; inside SISU time stands still.
      if (G.auto || people().some(p => p.mode === 'sub' || p.mode === 'dive' || p.mode === 'ice')) { needs(dt); G.s.t += dt; }
    }
  }
  sub.face += (sub.dir - sub.face) * Math.min(1, dt * 4);
  for (const b of bubbles) { b.t += dt; b.y -= dt * 1.6; b.x += Math.sin(b.t * 6) * dt * 0.3; }
  while (bubbles.length && bubbles[0].t > 3) bubbles.shift();
  const home = G.mode === 'home';
  G.homeT += ((home ? 1 : 0) - G.homeT) * Math.min(1, dt * 3);
  const ice = G.mode === 'ice';
  const sc = G.mode === 'dive' ? diveScale() : home ? homeScale() : ice ? iceScale() : subScale();
  G.sc += (sc - G.sc) * Math.min(1, dt * 2.5);
  let tx = sub.x, ty = sub.y;
  if (G.mode === 'dive') { tx = diver.x; ty = diver.y; }
  if (ice) { tx = walker.x; ty = walker.y - H * 0.1 / G.sc; }  // the ice low on the screen, the sky and station above
  // Inside: sideways the whole of SISU fits; upright the view follows the person along the hull.
  if (home) { ty += H * (W > H ? 0.07 : 0.08) / G.sc; if (W <= H) tx = sub.x + sub.face * Math.max(-7.3, Math.min(7.7, crew.x)); }
  // v8: up the tower the view rises with the person, so the tower's top shows under the goal bar sideways too.
  if (home && crew.y < UP) ty += crew.y * 0.6;
  if (G.mode === 'sub') tx += sub.vx * 1.2;
  if (!home && !ice) ty = Math.max(ty, (H * 0.3) / G.sc);
  G.cx += (tx - G.cx) * Math.min(1, dt * 4);
  G.cy += (ty - G.cy) * Math.min(1, dt * 4);
  soundStep(dt);
  if (G.s) drawHud();
}
