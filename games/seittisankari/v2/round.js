'use strict';
// Seittisankari v1 (#529): the round. v1 is the free city (Eero's choice): no clock, no goal, the
// whole city to climb and swing through. The missions of the prototype wait for v2.

// The downtown, the old 6 × 6 middle of the city: LX and BX count its lots.
const LX = k => lotX(C0 + k), BX = (i, j) => boxAt(C0 + i, C0 + j);
const T_BOX = boxAt(TOWER.i, TOWER.j);            // the tower, the race's goal in a room
const START = { x: LX(2) + 20, z: LX(2) + 20 };   // a street crossing beside the tower

function newWorld() {
  const w = { t: 0, flag: null, hero: newHero(START.x, 0, START.z, 0) };
  return w;
}
function stepRound(w, dt) { w.t += dt; }
