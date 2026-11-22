'use strict';
// Lattia on laavaa v3: Koko talo (#526), the fourth room. One round climbs the whole house: the
// living room downstairs, a staircase up the left wall to a child's room upstairs, a second one up
// the right wall to the flat roof, and once the house is under the lava, rafts, boats, doors and
// logs drifting across the lava sea. Each staircase is shut by a door until a moment before the
// lava starts up it, so the round starts downstairs like the other rooms.
//
// The three floors stack in the same 14 x 10 m box as the other rooms (world.js): downstairs at
// 0 m, upstairs at 3 m, the roof at 6 m. A floor is a slab 0.2 m thick with a hole over its
// staircase; the steps, the floors, the stair walls and the doors are `statics`, solids that never
// sink: the lava covers them. Everything is still a function of rt and the seed alone.
const FLOOR_H = 3, SLAB = 0.2;
// When each staircase's door opens and when the lava starts up it, s (#526: about two minutes to
// the roof, Eero's choice). The lava climbs at RISE, and creeps at CREEP in between.
const HOUSE = { open: [35, 95], climb: [40, 100], rise: 0.08, creep: 0.005 };
const STAIR_X = [-6.4, 6.4], STAIR_W = 1.2, STEPS = 11, STEP_RISE = 0.25, STEP_RUN = 0.6;
const STAIR_Z1 = 3.0;                                    // the front edge of the bottom step
const STAIR_Z0 = STAIR_Z1 - STEPS * STEP_RUN;            // the back edge of the top step (-3.6)
const DOOR_D = 0.12, RAIL_W = 0.1, RAIL_H = 0.9;
// What drifts across the lava sea at the end: [kind, w, d], bigger than the rooms' floats.
const HOUSE_FLOATS = [['raft', 1.6, 1.4], ['boat', 1.5, 1.0], ['door', 1.9, 0.9], ['bigcushion', 1.2, 1.2], ['log', 2.0, 0.6]];

ROOMS.push({
  name: 'Koko talo', wall: '#e6d7bd', floorWood: '#a8743f', floatAt: 135, cpu: 1,
  floors: [
    { y: 0, start: 10, gap: 2.6, keep: 3, wall: '#e6d7bd', floorWood: '#a8743f' },
    { y: FLOOR_H, start: 76, gap: 2.8, keep: 3, wall: '#b9d8e8', floorWood: '#c99a62' },
    { y: FLOOR_H * 2, start: 134, gap: 2.4, wall: null, floorWood: '#8d8f94' },
  ],
  // [kind, x, z, w, d, h (above its floor), order, floor]. On a floor with a staircase up, pieces
  // of order `keep` and over never sink by themselves: the lava climbing to the next floor takes
  // them. So a way to the stairs is still there when the door opens: downstairs the sofa, the table,
  // a pouf, the chest and the stool to the pouf in front of the stairs (order 4); upstairs the bed,
  // the toy boxes, the desk and its chair and a beanbag, from the landing to the second staircase.
  pieces: [
    ['sofa', -3.4, -3.7, 4.0, 1.3, 0.75, 3, 0], ['sofaback', -3.4, -4.6, 4.0, 0.5, 1.35, 3, 0],
    ['armchair', 3.4, -3.6, 1.4, 1.3, 0.75, 2, 0], ['tvbench', 0.6, -4.5, 2.2, 0.7, 0.55, 2, 0],
    ['table', 0, -1.0, 2.2, 1.2, 0.6, 3, 0], ['shelf', 6.2, -2.2, 0.9, 2.6, 1.6, 2, 0],
    ['pouf', -2.2, 1.0, 0.9, 0.9, 0.5, 3, 0], ['pouf', 2.4, 1.2, 0.9, 0.9, 0.5, 1, 0],
    ['chest', -5.2, -0.9, 0.8, 1.4, 0.6, 3, 0], ['cushion', -0.2, 2.6, 1.0, 1.0, 0.25, 0, 0],
    ['cushion', 4.6, 2.8, 1.0, 1.0, 0.25, 0, 0], ['sidetable', 5.3, 0.6, 0.8, 0.8, 0.65, 1, 0],
    ['stool', -4.6, 1.6, 0.7, 0.7, 0.55, 3, 0], ['pouf', 1.8, 3.6, 0.8, 0.8, 0.45, 0, 0],
    ['pouf', -6.35, 4.1, 1.0, 1.0, 0.45, 4, 0],
    ['bed', -3.4, -3.6, 3.2, 1.6, 0.6, 3, 1], ['wardrobe', 4.4, -4.4, 1.2, 1.0, 1.6, 2, 1],
    ['desk', 2.2, -4.3, 1.6, 0.8, 0.75, 3, 1], ['chair', 2.2, -3.2, 0.6, 0.6, 0.45, 3, 1],
    ['toybox', -0.2, -4.3, 1.2, 0.8, 0.55, 3, 1], ['beanbag', -1.0, -1.0, 1.2, 1.2, 0.45, 1, 1],
    ['beanbag', 2.4, -0.8, 1.2, 1.2, 0.45, 3, 1], ['blocks', -4.0, 0.0, 0.7, 0.7, 0.35, 0, 1],
    ['blocks', 0.6, 2.2, 0.7, 0.7, 0.35, 0, 1], ['horse', -2.6, 2.6, 1.2, 0.6, 0.7, 1, 1],
    ['toybox', 4.4, 1.6, 1.4, 0.8, 0.55, 3, 1], ['cushion', -4.6, 3.6, 1.0, 1.0, 0.25, 0, 1],
    ['blocks', 3.6, 3.4, 0.7, 0.7, 0.35, 0, 1], ['pouf', 6.35, 4.1, 1.0, 1.0, 0.45, 4, 1],
    ['chimney', -2.5, -3.2, 1.0, 1.0, 1.2, 3, 2], ['skylight', 1.5, -1.5, 1.4, 1.0, 0.35, 1, 2],
    ['skylight', -1.8, 1.6, 1.4, 1.0, 0.35, 1, 2], ['tank', 3.4, -3.6, 1.4, 1.4, 0.9, 3, 2],
    ['vent', 0.6, 2.6, 0.8, 0.8, 0.5, 2, 2], ['planter', -4.8, -1.0, 1.2, 0.6, 0.5, 2, 2],
    ['planter', 3.6, 1.2, 1.2, 0.6, 0.5, 2, 2], ['bench', -0.6, -3.8, 2.0, 0.6, 0.45, 2, 2],
    ['deckbox', -4.6, 3.4, 1.0, 0.8, 0.6, 1, 2], ['pot', 2.4, 3.8, 0.6, 0.6, 0.55, 0, 2],
  ],
});
const HOUSE_LV = ROOMS.length;

// The lava in the house: the floor until 20 s, creeping up to 0.12 m by 40 s, then up the first
// staircase to the upstairs floor (about 76 s), creeping again, and from 100 s up the second to
// the roof (about 136 s); from there it creeps on over the roof, a sea round the house.
function houseLava(rt) {
  if (rt < 20) return 0.02;
  if (rt < HOUSE.climb[0]) return 0.02 + (rt - 20) * HOUSE.creep;
  let h = 0.02 + (HOUSE.climb[0] - 20) * HOUSE.creep;
  const up = (from, t0, to) => {
    const t1 = t0 + (to - from) / HOUSE.rise;
    return rt < t1 ? [from + (rt - t0) * HOUSE.rise, null] : [null, t1];
  };
  let [v, t1] = up(h, HOUSE.climb[0], FLOOR_H + 0.02);
  if (v !== null) return v;
  if (rt < HOUSE.climb[1]) return FLOOR_H + 0.02 + (rt - t1) * HOUSE.creep;
  h = FLOOR_H + 0.02 + (HOUSE.climb[1] - t1) * HOUSE.creep;
  [v, t1] = up(h, HOUSE.climb[1], FLOOR_H * 2 + 0.02);
  if (v !== null) return v;
  return FLOOR_H * 2 + 0.02 + (rt - t1) * HOUSE.creep;
}
// The first rt at which the lava reaches height h (Infinity when it never does): the rising lava
// is what ends a step or a floor, and the computer's kids reckon with it.
function lavaWhen(w, h) {
  if (lavaAt(1e4, w) < h) return Infinity;
  let a = -COUNT, b = 1e4;
  for (let i = 0; i < 40; i++) { const m = (a + b) / 2; if (lavaAt(m, w) >= h) b = m; else a = m; }
  return b;
}

// ---- The house's steps, floors, stair walls and doors ----
// Each: {id, kind, x, z, w, d, top, bot, vx, vz, stair, floor, wall?, openAt?}. Made once.
let STATICS = null;
function houseStatics() {
  if (STATICS) return STATICS;
  const L = [];
  const add = (kind, x0, x1, z0, z1, bot, top, more) => L.push(Object.assign({
    id: 's' + L.length, kind, x: (x0 + x1) / 2, z: (z0 + z1) / 2, w: x1 - x0, d: z1 - z0, top, bot, vx: 0, vz: 0,
  }, more));
  for (let n = 0; n < 2; n++) {
    const y = n * FLOOR_H, sx = STAIR_X[n], sx0 = sx - STAIR_W / 2, sx1 = sx + STAIR_W / 2;
    const inner = n ? sx0 : sx1;                        // the stair's open side, towards the room
    // The steps, solid blocks from the floor up, the bottom one at the front.
    for (let i = 1; i <= STEPS; i++) {
      const z1 = STAIR_Z1 - (i - 1) * STEP_RUN;
      add('step', sx0, sx1, z1 - STEP_RUN, z1, y, y + i * STEP_RISE, { stair: n, step: i, floor: n });
    }
    // The wall along the stair's open side, from the floor below to a rail over the floor above,
    // so the way up is through the door and nobody falls into the stairwell from upstairs.
    const rx0 = n ? inner - RAIL_W : inner, rx1 = rx0 + RAIL_W;
    add('rail', rx0, rx1, STAIR_Z0, STAIR_Z1, y, y + FLOOR_H + RAIL_H, { stair: n, wall: true, floor: n });
    // The door in front of the bottom step, open from HOUSE.open[n].
    add('door', sx0, sx1, STAIR_Z1, STAIR_Z1 + DOOR_D, y, y + FLOOR_H - SLAB, { stair: n, wall: true, openAt: HOUSE.open[n], floor: n });
  }
  // The floors above: everything but the hole over the staircase below.
  for (let f = 1; f <= 2; f++) {
    const top = f * FLOOR_H, bot = top - SLAB, sx = STAIR_X[f - 1], sx0 = sx - STAIR_W / 2, sx1 = sx + STAIR_W / 2;
    if (f === 1) add('floor', sx1, X1, Z0, Z1, bot, top, { floor: f });
    else add('floor', X0, sx0, Z0, Z1, bot, top, { floor: f });
    add('floor', sx0, sx1, Z0, STAIR_Z0, bot, top, { floor: f });
    add('floor', sx0, sx1, STAIR_Z1, Z1, bot, top, { floor: f });
    // A rail across the hole's front edge too, so the strip in front of it is no way down.
    add('guard', sx0, sx1, STAIR_Z1 - RAIL_W, STAIR_Z1, top, top + RAIL_H, { wall: true, floor: f });
  }
  STATICS = L;
  return L;
}
// Which floor a height is on: 0 downstairs, 1 upstairs, 2 the roof.
const floorOfY = y => y < FLOOR_H - 0.1 ? 0 : y < FLOOR_H * 2 - 0.1 ? 1 : 2;
