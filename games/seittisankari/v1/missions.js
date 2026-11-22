'use strict';
// Seittisankari v1 (#529): the missions. Each one sets up the hero and its things in the city,
// and says each step whether it is done. Plain numbers, like world.js.

// Buildings the missions use, picked from the city once (the city is the same on every phone).
// The missions play in the downtown, the old 6 × 6 middle of the city: LX and BX count its lots.
const LX = k => lotX(C0 + k), BX = (i, j) => boxAt(C0 + i, C0 + j);
const lowest = list => list.reduce((a, b) => b.h < a.h ? b : a);
const M_WALL = lowest([0, 1, 2, 3, 4, 5].map(i => BX(i, 0)).filter(b => b.h > 22));   // a low first wall
const M_ROOFS = [1, 2, 3, 4].map(i => BX(i, 4));                           // a row of roofs to swing along
const M_THIEF = [BX(1, 1), BX(2, 1), BX(2, 2), BX(1, 2)];                 // the thief's loop
const T_BOX = boxAt(TOWER.i, TOWER.j);

const BALLOON_COLS = ['#ff4d6d', '#ffd166', '#4dd2ff', '#7cff6b', '#c77dff'];
function balloonsNear(cx, cz, n, seed, spread, top) {
  const r = rng(seed), out = [];
  while (out.length < n) {
    const x = cx + (r() - 0.5) * spread, z = cz + (r() - 0.5) * spread, y = top ? 6 + r() * (top - 6) : 12 + r() * 60;
    // In the open air: not inside or touching a building.
    if (eachNear(x, z, 3, b => x > b.x0 - 3 && x < b.x1 + 3 && z > b.z0 - 3 && z < b.z1 + 3 && y < b.h + 3)) continue;
    out.push({ x, y, z, col: BALLOON_COLS[out.length % BALLOON_COLS.length], got: false });
  }
  return out;
}
// The point on the side of a box facing the street, for starts at the foot of a wall.
const footOf = (b, side) => side === 's' ? { x: (b.x0 + b.x1) / 2, z: b.z0 - 4 } : { x: b.x0 - 4, z: (b.z0 + b.z1) / 2 };

const MISSIONS = [
  { name: 'Ensimmäinen seinä', note: 'Kiipeä talon katolle', limit: 0,
    goal: 'Kiipeä katolle lipulle',
    setup(w) { const f = footOf(M_WALL, 's'); w.hero = newHero(f.x, 0, f.z, 0); w.flag = roofTop(M_WALL); w.hint = 'wall'; },
    done(w) { return near(w.hero, w.flag, 3); } },
  { name: 'Ensimmäinen heilahdus', note: 'Katolta katolle seitillä', limit: 0,
    goal: 'Heilu katoille lipulle',
    setup(w) { const s = roofTop(M_ROOFS[0]); w.hero = newHero(s.x, s.y, s.z, Math.PI / 2); w.flag = roofTop(M_ROOFS[3]); w.hint = 'web'; },
    done(w) { return near(w.hero, w.flag, 4); } },
  { name: 'Kissa tornissa', note: 'Pelasta kissa tornin katolta', limit: 180,
    goal: 'Hae kissa tornin katolta',
    goal2: 'Vie kissa kadulle',
    setup(w) { const f = footOf(T_BOX, 'w'); w.hero = newHero(f.x - 30, 0, f.z, Math.PI / 2); w.cat = { x: T_BOX.x1 - 3, y: T_BOX.h, z: T_BOX.z0 + 3, held: false }; },
    done(w) {
      if (!w.cat.held && near(w.hero, w.cat, 2.5)) { w.cat.held = true; w.ev.push('cat'); }
      return w.cat.held && w.hero.y < 0.5;
    } },
  { name: 'Ilmapallot', note: 'Kerää 10 ilmapalloa', limit: 120,
    goal: 'Kerää ilmapallot',
    setup(w) { w.hero = newHero(LX(1) + 20, 0, LX(3) + 20, 0); w.balloons = balloonsNear(LX(1) + 20, LX(3) + 20, 10, 41, 110, 28); },
    done(w) { return w.balloons.every(b => b.got); } },
  { name: 'Varas katoilla', note: 'Ota varas kiinni seitillä', limit: 120,
    goal: 'Ota varas kiinni: lähellä Seitti',
    setup(w) { const s = roofTop(M_THIEF[0]); w.hero = newHero(LX(0) - 6, 0, LX(0) - 6, Math.PI / 4); w.thief = { path: M_THIEF.map(roofTop), t: 0, x: s.x, y: s.y, z: s.z, caught: false }; },
    done(w) { return w.thief.caught; } },
  { name: 'Karanneet dronet', note: 'Ota kolme dronea kiinni', limit: 180,
    goal: 'Ota dronet kiinni: lähellä Seitti',
    setup(w) {
      w.hero = newHero(LX(4) + 20, 0, LX(4) + 20, Math.PI);
      w.drones = [[LX(4) + 20, 30, LX(2) + 20, 14], [LX(2) + 20, 55, LX(4) + 20, 18], [LX(0) + 20, 80, LX(3) + 20, 16]]
        .map(([x, y, z, r], k) => ({ cx: x, cy: y, cz: z, r, a: k * 2, x, y, z, caught: false }));
    },
    done(w) { return w.drones.every(d => d.caught); } },
  { name: 'Tornin huipulle', note: 'Kadulta tornin katolle', limit: 180,
    goal: 'Tornin katolle!',
    setup(w) { w.hero = newHero(LX(5) + 20, 0, LX(0) - 12, -Math.PI / 4); w.flag = roofTop(T_BOX); },
    done(w) { return near(w.hero, w.flag, 9) && w.hero.y >= T_BOX.h - 0.1; } },
];
const FREE_N = 90;   // balloons over the whole city
const FREE = { name: 'Vapaa kaupunki', note: 'Ei kelloa, ei tehtävää', limit: 0, goal: '',
  setup(w) { w.hero = newHero(LX(2) + 20, 0, LX(2) + 20, 0); w.balloons = balloonsNear(0, 0, FREE_N, 7, 2 * EDGE - 20); },
  done() { return false; } };

const near = (h, p, d) => Math.hypot(h.x - p.x, h.y + 0.8 - p.y, h.z - p.z) < d;
const CATCH = 7;

function newWorld(n) {
  const M = n === 0 ? FREE : MISSIONS[n - 1];
  const w = { n, M, t: 0, done: false, failed: false, ev: [], flag: null, cat: null, balloons: null, thief: null, drones: null };
  M.setup(w);
  return w;
}
// The thing a press of Seitti would catch, if one is close.
function catchable(w) {
  const h = w.hero;
  if (w.thief && !w.thief.caught && near(h, w.thief, CATCH)) return w.thief;
  if (w.drones) for (const d of w.drones) if (!d.caught && near(h, d, CATCH + 1)) return d;
  return null;
}
// One step of the mission's things, then the check.
function stepMission(w, dt) {
  if (w.done || w.failed) return;
  w.t += dt;
  const h = w.hero;
  if (w.balloons) for (const b of w.balloons) {
    if (b.got && b.back && w.t >= b.back) { b.got = false; b.back = 0; }   // free city: back after 20 s
    if (!b.got && near(h, b, 2.4)) { b.got = true; w.ev.push('balloon'); if (w.n === 0) b.back = w.t + 20; }
  }
  if (w.thief && !w.thief.caught) {
    // Round the loop of roofs at a run, an arc over each street.
    const th = w.thief, P = th.path, legT = 4.5;
    th.t += dt;
    const k = Math.floor(th.t / legT) % P.length, f = (th.t % legT) / legT;
    const a = P[k], b = P[(k + 1) % P.length];
    th.x = a.x + (b.x - a.x) * f; th.z = a.z + (b.z - a.z) * f;
    th.y = a.y + (b.y - a.y) * f + Math.sin(f * Math.PI) * 10;
    th.yaw = Math.atan2(b.x - a.x, b.z - a.z);
  }
  if (w.drones) for (const d of w.drones) if (!d.caught) {
    d.a += dt * 0.45;
    d.x = d.cx + Math.cos(d.a) * d.r; d.z = d.cz + Math.sin(d.a) * d.r; d.y = d.cy + Math.sin(d.a * 2) * 3;
  }
  if (w.M.done(w)) { w.done = true; w.ev.push('done'); return; }
  if (w.M.limit && w.t >= w.M.limit) { w.failed = true; w.ev.push('fail'); }
}
// Seitti pressed near a thief or a drone: wrap it.
function tryCatch(w) {
  const c = catchable(w);
  if (!c) return false;
  c.caught = true; w.ev.push('caught');
  return true;
}
