'use strict';
// Out on the ice, playing with friends, every frame's step, the hose and the harpoon.
// ---------- out on the ice (v6, #143) ----------
// SISU is surfaced when it lies centred in an opening with its back out of the water.
// v15 (#329): in a small opening only the tower comes up, its hull still under the ice (`holeSurf()`).
function surfaced() { const n = holeAt(sub.x); return n >= 0 && sub.y < holeSurf(n) + 0.6 && Math.abs(sub.x - holeMid(n)) < 1.5; }
function smallUp() { const n = holeAt(sub.x); return n >= 0 && !!HOLES[n][2] && surfaced(); }
// v15: the tower's top in the world, [west end, east end], where a person stands on it in a small opening
function towerSpan() { const a = sub.x + sub.face * -2.2 * SS, b = sub.x + sub.face * 3.6 * SS; return [Math.min(a, b), Math.max(a, b)]; }
// v8: the hatch is on the tower's top, right over the ladder.
function hatchX() { return sub.x + sub.face * LADDER * SS; }
// v13: the tower's top and SISU's back, in the world
function towerTop() { return sub.y - 5.2 * SS; }
function subBack() { return sub.y - 2.3 * SS; }
// Where the feet stand at x on the ice: a building's floor (v12: `fl`, the floor the person is on), the shelf, a drift
// up onto it, the sea ice, and SISU's back across its opening (with planks to the edges); null for open water.
function groundAt(x, fl = 0) {
  const b = bldAt(x);
  // v13: the floor of Aurora's dock has the moon pool in it: SISU's back across it, or open water
  if (b && b.pool != null && !fl && holeAt(x) === b.pool) return surfaced() && holeAt(sub.x) === b.pool ? subBack() : null;
  if (b) return b.floors[Math.min(fl, b.floors.length - 1)];
  if (x < SHELF_X) return STATION.floor;
  if (x < SHELF_X + 6) return STATION.floor + (x - SHELF_X) / 6 * (ICE_TOP - STATION.floor);
  const n = holeAt(x);
  if ((x > BERG_X[0] && x < BERG_X[1]) || smallBerg(x)) return null;  // an iceberg's wall: no way up it
  if (n < 0) return ICE_TOP;
  if (!(surfaced() && holeAt(sub.x) === n)) return null;
  if (!HOLES[n][2]) return subBack();
  // v15: in a small opening, the tower's top, and a plank from it to each edge of the opening
  const [t0, t1] = towerSpan(), top = towerTop(), [h0, h1] = HOLES[n];
  if (x >= t0 && x <= t1) return top;
  return x < t0 ? top + (ICE_TOP - top) * (t0 - x) / Math.max(0.1, t0 - h0) : top + (ICE_TOP - top) * (x - t1) / Math.max(0.1, h1 - t1);
}
function atHatch() { return !walker.climbing && Math.abs(walker.x - hatchX()) < 2.2 && holeAt(walker.x) === holeAt(sub.x) && !walker.fl; }
function goIce() {
  if (!surfaced()) { toast('SISU ei ole pinnalla'); return; }
  // v8: the person comes up out of the hatch from where they stood inside, then down the tower's side onto SISU's back.
  Object.assign(walker, { x: hatchX(), y: sub.y + Math.min(crew.y, UP) * SS, dir: sub.face < 0 ? -1 : 1, to: null, warm: 100, moving: false,
    climbing: true, rise: true, riseTo: towerTop(), inn: '', suit: crew.suit, kit: crew.kit, walkT: 0, room: '', fl: 0, toFl: 0 });
  crew.to = null;
  // v12: the bag goes out as it is: goods packed for the nomads stay in it
  G.asked = {}; G.mode = 'ice';
  sfx('metalli', 0.6, 500, 300, 0.4, 'triangle', 0.05);  // the hatch
  save();
  if (!G.s.flags.jaa && !G.iceSeen) {
    G.iceSeen = true; G.s.flags.jaa = true; save();
    card('Jäällä', [
      { t: 'Pakkasta on kolmekymmentä astetta. 🥶 laskee ulkona ja täyttyy taas sisällä – asemalla, nuotiolla tai SISUssa.' },
      { t: 'Takaisin SISUun tornin luukusta.', c: 'msg' },
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
    act('lost', ['ice', r2(walker.x), r2(walker.y - 0.5)]);
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
// v12 (#300): a tap on the ice: walk there, and in a building to the floor tapped (by its ladder).
function tapIce(x, y) {
  const b = bldAt(x);
  walker.to = x;
  // the floor whose room the tap is in: the highest floor still under the tap (v13: any number of floors)
  walker.toFl = b ? Math.max(0, b.floors.reduce((f, fy, n) => fy >= y - 0.3 ? n : f, 0)) : 0;
  if (b !== bldAt(walker.x)) walker.toFl = walker.fl;
}
function stepIce(dt) {
  const w = walker, x0 = w.x, y0 = w.y, b = bldAt(w.x);
  if (w.inn === 'walk') {
    const hx = hatchX();
    w.x += Math.sign(hx - w.x) * Math.min(WALK * dt, Math.abs(hx - w.x));
    if (Math.abs(hx - w.x) < 1e-3) { w.x = hx; w.inn = 'up'; w.climbing = true; }
  } else if (w.inn === 'up') {
    w.x = hatchX();
    w.y = Math.max(towerTop(), w.y - CLIMB * dt);
    if (w.y <= towerTop() + 1e-3) { w.inn = 'down'; sfx('metalli', 0.6); }  // the hatch (v11)
  } else if (w.inn === 'down') {
    w.x = hatchX();
    w.y = Math.min(sub.y + TOP * SS, w.y + CLIMB * dt);
    if (w.y >= sub.y + TOP * SS - 1e-3) { w.inn = ''; w.climbing = false; endIce(false); return; }
  } else if (w.rise) {
    // v8: up through the open hatch onto the tower's top.
    w.y = Math.max(w.riseTo, w.y - CLIMB * dt);
    if (w.y <= w.riseTo + 1e-3) w.rise = false;
  } else if (w.ladder != null) {
    // v12: on a building's ladder, up or down to the next floor (the stick, or a tap on the other floor)
    const goal = b.floors[w.ladder];
    w.x = w.lx;
    w.y += Math.sign(goal - w.y) * Math.min(CLIMB * dt, Math.abs(goal - w.y));
    if (Math.abs(goal - w.y) < 1e-3) { w.y = goal; w.fl = w.ladder; w.ladder = null; w.climbing = false; }
  } else if (w.climbing) {
    // Down the tower's outside ladder onto SISU's back.
    const g = groundAt(w.x);
    w.y = Math.min(g == null ? w.y : g, w.y + CLIMB * dt);
    if (g == null || w.y >= g - 1e-3) w.climbing = false;
  } else {
    if (input.x) w.to = null;  // the stick takes over from a tap
    // v12: by a building's ladder the stick up or down climbs it; a tap on the other floor walks to the ladder first.
    // v13: a building may have several ladders (`ladders`: [the floor below, x]), one floor at a time.
    const lads = b && b.floors.length > 1 ? b.ladders : [];
    const ladUp = lads.find(([f]) => f === w.fl), ladDown = lads.find(([f]) => f === w.fl - 1);
    const vert = Math.abs(input.y) > 0.5 && Math.abs(input.y) > Math.abs(input.x);
    const at = l => l && Math.abs(w.x - l[1]) < 0.6;
    const goal = w.to != null && w.toFl !== w.fl ? (w.toFl > w.fl ? ladUp : ladDown) : null;
    if (vert && input.y < 0 && at(ladUp)) { w.ladder = w.fl + 1; w.lx = ladUp[1]; w.climbing = true; w.to = null; }
    else if (vert && input.y > 0 && at(ladDown)) { w.ladder = w.fl - 1; w.lx = ladDown[1]; w.climbing = true; w.to = null; }
    else if (goal) {
      const d = goal[1] - w.x;
      w.x += Math.sign(d) * Math.min(WALK * dt, Math.abs(d));
      if (Math.abs(d) < 1e-3) { w.x = goal[1]; w.lx = goal[1]; w.ladder = w.fl + Math.sign(w.toFl - w.fl); w.climbing = true; }
    } else {
      const vx = w.to != null ? Math.sign(w.to - w.x) * Math.min(WALK, Math.abs(w.to - w.x) / dt) : input.x * WALK;
      let nx = w.x + vx * dt;
      // the buildings' walls: from inside, the wall without the door (upstairs both walls); from outside, that wall
      if (b && (b.door !== 'x0' || w.fl)) nx = Math.max(b.x0 + 0.6, nx);
      if (b && (b.door !== 'x1' || w.fl)) nx = Math.min(b.x1 - 0.6, nx);
      const nb = !b && bldAt(nx);
      if (nb) nx = nb.door !== 'x1' && w.x >= nb.x1 ? nb.x1 + 0.3 : nb.door !== 'x0' && w.x <= nb.x0 ? nb.x0 - 0.3 : nx;
      nx = Math.max(36, Math.min(WORLD_W - 10, nx));
      const g = groundAt(nx, bldAt(nx) === b ? w.fl : 0);
      if (g == null) {
        w.to = null;
        if (G.iceCd <= 0) { toast((nx > BERG_X[0] && nx < BERG_X[1]) || smallBerg(nx) ? 'Jäävuoren seinä: tästä ei pääse' : 'Railo: avovettä edessä', 1.2); G.iceCd = 1; }  // stays up while the stick pushes
      } else { w.x = nx; w.y = g; if (!bldAt(nx)) w.fl = 0; }
      if (w.to != null && Math.abs(w.to - w.x) < 0.02) w.to = null;
    }
  }
  const dx = w.x - x0;
  if (Math.abs(dx) > 1e-4) w.dir = Math.sign(dx);
  w.moving = Math.abs(dx) > 1e-4 || Math.abs(w.y - y0) > 1e-4;
  w.walkT += Math.abs(dx) + Math.abs(w.y - y0);
  // v11 (#221): steps in the snow out on the ice, one a metre or so; the ladders and the buildings' rooms are quiet.
  if (!w.climbing && !w.inn && Math.abs(dx) > 1e-4 && !inStation(w.x) && (w.stepT = (w.stepT || 0) + Math.abs(dx)) > 1.1) {
    w.stepT = 0; sfx('lumi', 0.18);  // v13: softer
  }
  // The cold outside; the buildings keep the wind off and (v12) the nomads' fire warms.
  const inside = inStation(w.x) || nearFire(w.x);
  // v8: coming up through the hatch the person is still in the tower, out of the wind.
  w.warm = inside || w.rise || w.inn === 'down' ? Math.min(100, w.warm + dt * WARMUP) : w.warm - dt * 100 / WARM;
  // v15 (#329): the first time in the dark Aurora: what is wrong with it
  if (b === AUR && !G.s.flags.sahko && !G.s.flags.pimea && !G.pimeaSaid && !w.climbing) {
    G.pimeaSaid = true;
    if (!net || net.host) { G.s.flags.pimea = 1; save(); }
    card('Aurora', [{ t: 'Asema on pimeä, kylmä ja tyhjä. Ketään ei ole täällä – vain tuuli ulvoo seinissä.' },
      { t: 'Sähkökeskus on telakan länsipäässä. Katso, mikä siinä on vialla.', c: 'msg' }],
    [{ label: 'Selvä', cls: 'go', fn: closeCard }]);
    return;
  }
  const r = inStation(w.x) ? stationRoom(w.x, w.fl) : null, rid = r ? r.id : '';
  if (rid !== w.room) {
    w.room = rid;
    if (rid === 'aeteinen' && x0 <= SAA.x0) toast('Sisällä: täällä lämpenee', 1.6);
  }
  // the first time by the nomads' fire: who they are
  if (Math.abs(w.x - CAMP.fire) < 30 && !G.s.flags.leiri && !G.s.flags.suoja && !G.campSaid) {
    G.campSaid = true; toast('🔥 Nomadien leiri – vanhin istuu nuotion ääressä', 2.6);
  }
  if (inStation(w.x) && !w.climbing) for (const it of ICE_ITEMS) {
    if (it.site === 'pinta' && !G.s.flags.sahko) continue;  // v15: nothing to find in the dark
    if (!itemHere(it) || G.asked[it.id] || Math.abs(it.x - w.x) > 1.1 || Math.abs(it.y - w.y) > 1.6) continue;
    if (it.k !== 'loki' && bagFull()) { if (G.bagCd <= 0) { toast('🎒 Reppu on täynnä', 1.4); G.bagCd = 3; } continue; }
    G.asked[it.id] = true;
    act('take', it.id);
    if (G.paused) return;  // a note's card
  }
  if (w.warm <= 0) endIce(true);
  else if (w.warm < 25 && G.warnCd <= 0) { toast('Kylmä! Mene sisälle'); G.warnCd = 4; sfx('halytys', 0.5, 400, 300, 0.3, 'square', 0.05); }
}

// The night, on the host (or alone) once everyone is in the bunk room; every phone gets the new day's card.
// v15 (#329): with the autopilot set and a meal eaten today, the night takes SISU all the way there (Eero: "autopilotin
// pikamatkustus nukkumalla, kun on ensin syönyt"): along the way the lamps map the sea and the sonar hears what it passes.
function sleep(trip) {
  const s = G.s;
  if (trip && G.auto) {
    const A = G.auto, pts = [[sub.x, sub.y]].concat(A.pts.slice(A.i)), end = pts[pts.length - 1];
    const heard = [];
    for (let k = 0; k + 1 < pts.length; k++) {
      const [ax, ay] = pts[k], [bx, by] = pts[k + 1], n = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) / 20));
      for (let m = 0; m <= n; m++) {
        const x = ax + (bx - ax) * m / n, y = ay + (by - ay) * m / n;
        chartSee(x, y, 30);
        for (const c of contacts()) if (!s.heard[c.id] && Math.hypot(c.x - x, c.y - y) < HEAR) { s.heard[c.id] = 1; heard.push([c, x, y]); }
      }
    }
    sub.x = end[0]; sub.y = end[1]; sub.vx = sub.vy = 0;
    if (A.id.startsWith('railo')) { const h = +A.id.slice(5); sub.x = holeMid(h); sub.y = holeSurf(h); }
    G.auto = null; G.coast = false; G.mapNew = true;
    if (net) { net.helm = null; net.subT = null; }
    for (const [c, x, y] of heard.slice(0, 3)) heardNew(c, x, y);
    if (heard.length > 3) heardNew({ id: '', kind: '', x: 0, y: 0 }, 0, 0, `📡 Yöllä sonar kuuli ${heard.length} uutta kaikua: ne ovat merikartalla`);
    trip = A.name;
  } else trip = null;
  s.day++;
  s.caught = {};  // v8: the schools are whole again
  s.m.food = Math.max(0, s.m.food - 12);
  s.m.health = Math.min(100, s.m.health + 15);
  newFinds();
  save();
  story('day', trip ? { trip } : undefined);
}
// Small random finds the current brings each night: a crate, a buoy, a lost bag.
function newFinds() {
  // v12 (#300): anywhere in the sea (no hull limit any more), and mostly near SISU, where the sonar can hear them
  const s = G.s;
  for (let tries = 0; s.finds.length < 3 && tries < 40; tries++) {
    // Rounded before the checks: on the steep slope a find moved half a metre after them could end up in the rock.
    const x = Math.round(Math.max(260, Math.min(WORLD_W - 300, sub.x + (Math.random() - 0.5) * 2400))), y = Math.floor((floorY(x) - 0.9) * 10) / 10;
    if (siteAt(x, y) || siteAt(x, y - 6) || diverHits(x, y)) continue;
    const r = Math.random(), deep = x > WX(2450) ? 0.15 : 0;  // the slope's finds are more often spare parts
    // v13: food and medicine only in crates, so the current brings parts and supplies
    s.finds.push({ id: 'f' + (s.findN++), k: r < 0.55 + deep ? 'osa' : 'tarvike', x, y });
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
// v12: the hose no longer wears, so its first two numbers are always 0.
function hosePack() { return [0, 0].concat(...hose.pts.map(p => [Math.round(p[0] * 10) / 10, Math.round(p[1] * 10) / 10])); }
// v12: the eighth number says whether the harpoon is in hand.
function mine() {
  const d = G.mode === 'dive', b = d ? diver : G.mode === 'ice' ? walker : crew;
  return [G.mode, r2(b.x), r2(b.y), b.dir, crew.suit ? (crew.kit === 'hose' ? 2 : 1) : 0, d ? r2(diver.ang) : 0,
    d && diver.kit === 'hose' ? hosePack() : 0, crew.harp ? 1 : 0];
}
function subPack() { return [r2(sub.x), r2(sub.y), sub.dir, r2(sub.vx), r2(sub.vy)]; }
function setOther(id, p) {
  const o = net.others[id];
  if (!o || !Array.isArray(p)) return;
  const jump = o.mode !== p[0];
  [o.mode, o.tx, o.ty, o.dir, o.suit, o.ang] = [String(p[0]), +p[1] || 0, +p[2] || 0, p[3] < 0 ? -1 : 1, !!p[4], +p[5] || 0];
  o.kit = p[4] === 2 ? 'hose' : 'tank';
  o.hose = Array.isArray(p[6]) ? p[6].slice(0, 122).map(Number) : null;
  o.harp = !!p[7];
  if (jump) { o.x = o.tx; o.y = o.ty; }
}
function sendState(to) { if (net && net.host && G.s) { R.send({ t: 's', s: G.s }, to); if (!to) net.dirty = false; } }
function snapshot() {
  const ps = { [R.me]: mine() };
  for (const [id, o] of Object.entries(net.others)) ps[id] = [o.mode, o.tx, o.ty, o.dir, o.suit ? (o.kit === 'hose' ? 2 : 1) : 0, o.ang, o.hose || 0, o.harp ? 1 : 0];
  const m = G.s.m;
  const A = G.auto;
  return { t: 'f', sub: subPack(), helm: net.helm, held: G.held, m: [r2(m.food), r2(m.health), r2(m.hull)], ps,
    auto: A ? [A.id, A.name, Math.round(A.left || 0), A.pts.slice(A.i).flat().map(Math.round)] : 0,
    // v12: the crates on the move (falling, or in someone's hands) as they are now; the rest come with the game ('s')
    cr: G.s.crates.filter(c => c.f || c.w === 'held').map(c => [c.id, c.w, r2(c.x), r2(c.y), c.hw || 0, c.by || 0]) };
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
    const b = o.mode === 'ice' && bldAt(o.x), g = o.mode === 'ice' && !b ? groundAt(o.x) : null;
    o.climbing = o.mode === 'home' ? o.y > UP + 0.05 && o.y < LOW - 0.05 : b ? !b.floors.some(f => Math.abs(o.y - f) < 0.3) : g != null && o.y < g - 0.3;
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
  net = null; G.mode = 'menu'; G.carry = []; G.held = {}; G.auto = null; G.coast = false; sub.vx = sub.vy = 0; G.sonarQ = [];  // v9: a trip ends with the round
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
    if (Array.isArray(m.cr)) for (const [id, w, x, y, hw, by] of m.cr) {
      const c = crateById(id);
      if (c) Object.assign(c, { w, x: +x, y: +y, hw: hw || undefined, by: by || undefined, f: w === 'held' ? 0 : 1 });
    }
    for (const [id, p] of Object.entries(m.ps || {})) if (id !== R.me) setOther(id, p);
    if (G.mode !== 'sub') net.subT = m.sub;
  }
  if (m.t === 're') answer(m);
  if (m.t === 'sonar' && m.say) G.sonarQ.push(String(m.say));  // v15
  if (m.t === 'card') showStory(m);
  if (m.t === 'end') { quiet(); R.backToRoom('Retki jatkuu, kun huoneen tekijä aloittaa kierroksen.'); }
});
// Host: a friend's phone is back (a reload): its person starts again in the control room, its haul lost.
function letGo(id) {
  // v12: goods they took from the stores into their bag go back into the stores
  for (const k of Object.keys(G.held)) if (G.held[k] === id) { if (k.startsWith('pack:') || k.startsWith('tuore:')) unpackGood(k); delete G.held[k]; }
  const c = heldBy(id);
  if (c) dropCrate(c, c.hw || 'sub', c.x, c.y);  // v12: their crate falls where they were
  save();
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
// On the ice the view is a little wider than inside SISU: about 19 m across the narrow side.
function iceScale() { return Math.min(W, H) / 19; }
function homeScale() { return (W > H ? Math.min((W - 30) / 30, (H - 150) / 8) : W / 14) / SS; }
function needs(dt) {
  const m = G.s.m;
  m.food = Math.max(0, m.food - dt * 100 / 720 * lab('bakteeri', 0.8));  // v12: the mat slows hunger
  if (m.food <= 0) m.health -= dt * 0.4;
  if (m.health <= 0) faint();
  if (m.hull <= 0) breach();
}
// Fainting and the hull giving way happen on the host (or alone); every phone gets the card and what it does to
// its own person (`showStory`).
function faint() {
  const s = G.s;
  s.day++; s.m.health = 35; s.m.food = Math.max(s.m.food, 25);
  G.held = {}; s.pack = {}; s.tuore = 0; dropAll(); if (net) { net.helm = null; stopSub(); }
  save();
  story('faint');
}
function breach() {
  const s = G.s;
  s.m.hull = 25; s.m.health = Math.max(10, s.m.health - 15);
  G.held = {}; s.pack = {}; s.tuore = 0; dropAll();  // every diver's haul is lost, and v12's crates in hand fall
  if (net && net.helm && net.helm !== me()) net.helm = present(net.helm) ? net.helm : null;
  // v12 (#300): with no depth limit any more, the emergency ballast lifts SISU 40 m, clear of what it hit.
  sub.y = Math.max(10, sub.y - 40); sub.vx = sub.vy = 0;
  while (subHits(sub.x, sub.y) && sub.y > 10) sub.y -= 4;
  while (subHits(sub.x, sub.y) && sub.x > 300) sub.x -= 10;
  save();
  story('breach', { sub: [sub.x, sub.y] });
}
// `steer` (v9): the autopilot's stick instead of the player's.
function stepSub(dt, steer) {
  // v12 (#300): the autopilot cruises up to three times as fast in open water (`steer.boost`), the sea being wider
  const k = subBoost() * (steer && steer.boost || 1);
  // v13 (#300): a finger on the sea at the helm steers SISU towards it, as a tap inside walks the person; the stick
  // takes over from it.
  if (!steer && (input.x || input.y)) G.subTo = null;
  if (!steer && G.subTo) {
    const dx = G.subTo.x - sub.x, dy = G.subTo.y - sub.y;
    if (!G.subTo.hold && (Math.hypot(dx, dy) < 3 || G.t - G.subTo.t > 30)) G.subTo = null;  // there, or given up
    else steer = { x: Math.max(-1, Math.min(1, dx / 25)), y: Math.max(-1, Math.min(1, dy / 8)) };
  }
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
  const hole = holeAt(sub.x), ny = Math.max(hole >= 0 ? holeSurf(hole) : 4, sub.y + sub.vy * dt);
  if (subHits(sub.x, ny)) {
    // v6: the ice overhead stops SISU softly, and says where the way up is.
    if (sub.vy < 0 && onlyIce(sub.x, ny)) {
      if (G.iceCd <= 0) { toast('Jää yläpuolella – pintaan pääsee vain railoista 📡', 2.2); G.iceCd = 4; sfx('jaa', 0.6, 160, 120, 0.3, 'triangle', 0.05); }
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
  const d = Math.hypot(bx - ax, by - ay);
  // v12: in a wreck the walls are thin plates, so the steps there are short
  for (let t = 0.25; t < d - 0.25; t += siteAt(ax + (bx - ax) * t / d, ay + (by - ay) * t / d) ? 0.1 : 0.4) {
    const x = ax + (bx - ax) * t / d, y = ay + (by - ay) * t / d;
    if (blocks(x, y)) return false;
  }
  return true;
}
// Lying along a wall or grazing a corner is clear: only a point inside rock or ice all round blocks the line, or
// (v12) one well inside a wreck's plate.
function blocks(x, y) {
  const s = siteAt(x, y);
  if (s && cellAt(s, x, y) === '#' && wallAt(s, x, y, WALL / 2 - 0.05)) return true;
  return solid(x, y) && solid(x + 0.2, y) && solid(x - 0.2, y) && solid(x, y + 0.2) && solid(x, y - 0.2);
}
function hoseLen(x, y, pts = hose.pts) {
  const a = airlock();
  let L = 0, px = a.x, py = a.y;
  for (const p of pts) { L += Math.hypot(p[0] - px, p[1] - py); px = p[0]; py = p[1]; }
  return L + Math.hypot(x - px, y - py);
}
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
    if (Math.hypot(q[0] - b[0], q[1] - b[1]) > 0.5) { ps.push([q[0], q[1]]); tidyHose(); }
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
// ---------- the harpoon (v8, #151) ----------
// One spear at a time, along the way the diver swims (or faces, when still), turned onto a fish just off that line;
// it flies SPEAR.range metres, stops in a wall or the ice, and a fish it meets is the diver's to carry home.
function fire() {
  if (G.mode !== 'dive' || !diver.harp || G.harpCd > 0 || G.paused) return;  // v12: only with the harpoon along
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
      sfx('osuma', 0.8);  // v11 (#221)
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
  // The first school near a diver: what the harpoon is for (v12: taken along from the suit room).
  if (!G.parviSaid && !(G.s.flags.parvi) && fishNow().some(f => Math.hypot(f.x - diver.x, f.y - diver.y) < 14)) {
    G.parviSaid = true;
    if (!net || net.host) { G.s.flags.parvi = true; save(); }
    toast(diver.harp ? 'Kalaparvi! 🔱 Harppuunalla saat ruokaa' : 'Kalaparvi! Ota 🔱 harppuuna mukaan sukelluspukuhuoneesta', 2.4);
  }
  // v12: the first crate near a diver: how crates go
  if (!G.crateSaid && !G.s.flags.laatikko && nearCrate()) {
    G.crateSaid = true;
    if (!net || net.host) { G.s.flags.laatikko = true; save(); }
    toast('📦 Laatikko: nosta se ja vie SISUn varaston hyllyyn', 2.6);
  }
  diver.vx += (input.x * DIVER_SPEED - diver.vx) * Math.min(1, dt * 3);
  diver.vy += (input.y * DIVER_SPEED - diver.vy) * Math.min(1, dt * 3);
  if (Math.abs(diver.vx) > 0.3) diver.dir = Math.sign(diver.vx);
  const onHose = diver.kit === 'hose';
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
    if (G.warnCd <= 0) { toast('Säiliöpuku ei kestä syvemmälle', 1.4); G.warnCd = 2.5; sfx('narina', 0.8, 90, 70, 0.4, 'triangle', 0.05); }
  } else diver.y = ny;
  if (held && G.warnCd <= 0) { toast('Letku on lopussa (' + max + ' m). Aja SISU lähemmäs tai pidennä letkua.', 2.2); G.warnCd = 2.5; sfx('virhe', 0.6, 260, 200, 0.2, 'triangle', 0.05); }
  diver.ang += ((Math.hypot(diver.vx, diver.vy) > 0.5 ? Math.atan2(diver.vy, Math.abs(diver.vx)) * 0.6 : 0) - diver.ang) * Math.min(1, dt * 5);
  if (onHose) {
    // The move counts only if the hose, caught on any new corner, still reaches: else the diver and the corners
    // stay where they were. v12 (#300): the hose no longer wears on the corners.
    const before = hose.pts.map(p => p.slice());
    hoseFollow(px, py);
    if (hoseLen(diver.x, diver.y) > max && hoseLen(diver.x, diver.y) > L0 + 1e-6) {
      hose.pts = before; diver.x = px; diver.y = py; diver.vx = diver.vy = 0;
      if (G.warnCd <= 0) { toast('Letku on lopussa (' + max + ' m). Aja SISU lähemmäs tai pidennä letkua.', 2.2); G.warnCd = 2.5; sfx('virhe', 0.6, 260, 200, 0.2, 'triangle', 0.05); }
    }
    hose.len = hoseLen(diver.x, diver.y);
  } else diver.air -= dt;
  for (let n = 0; n < FISH.length && G.fishCd <= 0; n++) {
    const f = fishAt(n, G.t), d = Math.hypot(f.x - diver.x, f.y - diver.y);
    if (d < 2.8) {
      G.fishCd = 3;
      diver.vx = (diver.x - f.x) / d * 6 * lab('suomu', 0.5); diver.vy = (diver.y - f.y) / d * 6 * lab('suomu', 0.5);
      tone(220, 140, 0.3, 'square', 0.05);
      // A glowing fish bumps the diver away; from a tank it costs air (8 s, never the last second). v12: no hose bites.
      if (!onHose) { const n = 8 * lab('suomu', 0.5); diver.air = Math.max(1, diver.air - n); toast(`Valokala tönäisi! −${n} s happea`, 1.6); }
      else toast('Valokala tönäisi!', 1.2);
    }
  }
  if (Math.random() < dt * 2.5) bubbles.push({ x: diver.x + diver.dir * 0.5, y: diver.y - 0.4, t: 0 });
  for (const it of allItems()) {
    if (!itemHere(it) || Math.hypot(it.x - diver.x, it.y - diver.y) > 1.7) continue;
    if (it.k === 'ilma') {
      // An air pocket fills a tank; the hose suit breathes from the hose.
      const full = TANK[G.s.up.tank];
      if (diver.kit === 'tank' && diver.air < full - 1) { diver.air = full; toast('Ilmatasku: happi täyttyy'); sfx('kuplat', 0.6, 600, 900, 0.3, 'sine', 0.06); }
      continue;
    }
    // Each find is asked for once a dive; with friends the host gives it to whoever asked first. v12: only into a bag
    // with room (a log is read on the spot).
    if (G.asked[it.id]) continue;
    if (it.k !== 'loki' && bagFull()) { if (G.bagCd <= 0) { toast('🎒 Reppu on täynnä (' + BAG + ')', 1.4); G.bagCd = 3; } continue; }
    G.asked[it.id] = true;
    act('take', it.id);
    if (G.paused) return;  // a log's card
  }
  if (diver.kit === 'hose') return;
  if (diver.air <= 0) endDive(true);
  else if (diver.air < 12 && G.warnCd <= 0) { toast('Happi vähissä!'); G.warnCd = 4; sfx('halytys', 0.6, 400, 300, 0.3, 'square', 0.05); }
}
function step(dt) {
  G.t += dt;
  if (G.mode !== 'sub') G.subTo = null;
  syncMaps();
  G.hitCd -= dt; G.warnCd -= dt; G.fishCd -= dt; G.iceCd -= dt; G.bagCd -= dt; G.pingCd = Math.max(0, G.pingCd - dt);
  G.harpCd = Math.max(0, G.harpCd - dt);
  if (G.toastT > 0 && (G.toastT -= dt) <= 0) show('toast', false);
  // v15: the sonar's news, one at a time under the goal, each with a soft echo
  if ((G.sonarT -= dt) <= 0) {
    if (G.sonarQ.length && G.mode !== 'menu') {
      $('sonarMsg').textContent = G.sonarQ.shift(); show('sonarMsg', true); G.sonarT = 3.2;
      tone(1500, 1450, 0.18, 'sine', 0.035); tone(1500, 1450, 0.18, 'sine', 0.02, 0.22);
    } else show('sonarMsg', false);
  }
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
  // v9: alone, an open card or chart stops only the person; while the autopilot drives (or SISU glides after it), the sea, hunger,
  // saving and the chart go on. v12 (#300): no pressure on the hull any more.
  if (playing && (net ? !away : !G.paused || G.auto || G.coast)) {
    if (!net || net.host) {
      stepCrates(dt);  // v12
      // Saved every 4 s in every mode (v4): damage on a dive or inside must survive a reload too.
      G.saveCd -= dt;
      if (G.saveCd <= 0) { save(); G.saveCd = 4; }
      if ((G.mapT = (G.mapT || 0) - dt) <= 0) { G.mapT = 0.1; mapStep(); }
      // Hunger runs while someone is at the helm or out diving; inside SISU time stands still.
      if (G.auto || people().some(p => p.mode === 'sub' || p.mode === 'dive' || p.mode === 'ice')) { needs(dt); G.s.t += dt; }
    }
  }
  sub.face += (sub.dir - sub.face) * Math.min(1, dt * 4);
  for (const p of [diver, crew, walker]) p.face = (p.face ?? p.dir) + (p.dir - (p.face ?? p.dir)) * Math.min(1, dt * 10);  // v13
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
  if (home) { ty += H * (W > H ? 0.07 : 0.08) / G.sc; if (W <= H) tx = sub.x + sub.face * Math.max(-7.3, Math.min(7.7, crew.x)) * SS; }
  // v8: up the tower the view rises with the person, so the tower's top shows under the goal bar sideways too.
  if (home && crew.y < UP) ty += crew.y * 0.6 * SS;
  if (G.mode === 'sub') tx += sub.vx * 1.2;
  if (!home && !ice) ty = Math.max(ty, (H * 0.3) / G.sc);
  // v13 (#300): inside, the view eases towards the person as seen from SISU, and moves with SISU at once: on the
  // autopilot's cruise the person stays in view.
  if (G.subX0 == null) { G.subX0 = sub.x; G.subY0 = sub.y; }
  if (home && G.homeT > 0.5) {
    G.cx = sub.x + (G.cx - G.subX0) + (tx - sub.x - (G.cx - G.subX0)) * Math.min(1, dt * 4);
    G.cy = sub.y + (G.cy - G.subY0) + (ty - sub.y - (G.cy - G.subY0)) * Math.min(1, dt * 4);
  } else {
    G.cx += (tx - G.cx) * Math.min(1, dt * 4);
    G.cy += (ty - G.cy) * Math.min(1, dt * 4);
  }
  G.subX0 = sub.x; G.subY0 = sub.y;
  soundStep(dt);
  if (G.s) drawHud();
}
