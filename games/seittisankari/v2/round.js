'use strict';
// Seittisankari v2 (#529): the round. The free city with missions (Eero: "mene tänne", and an
// arrow shows where): one marked roof at a time, a flag and a light over it; standing on it
// counts it and marks the next one. Every fifth is the tower's top.

// The downtown, the old 6 × 6 middle of the city: LX and BX count its lots.
const LX = k => lotX(C0 + k), BX = (i, j) => boxAt(C0 + i, C0 + j);
const T_BOX = boxAt(TOWER.i, TOWER.j);            // the tower, the city's tallest
const START = { x: LX(2) + 20, z: LX(2) + 20 };   // a street crossing beside the tower
const GOAL_NEAR = 120, GOAL_FAR = 300;            // how far the next roof is from the hero, m

// Standing on a building's roof (a hero, or another phone's hero as the host sees it).
const onTop = (h, b) => h.st === 'ground' && h.y >= b.h - 0.1 && h.x > b.x0 - 1 && h.x < b.x1 + 1 && h.z > b.z0 - 1 && h.z < b.z1 + 1;

function newWorld() {
  const w = { t: 0, flag: null, goal: -1, gt: 0, done: 0, got: 0, hero: newHero(START.x, 0, START.z, 0) };
  return w;
}
// The next roof: every fifth the tower, else a building of 20–150 m 120–300 m from the hero,
// inside the city's edge. `r` is a random number source (Math.random in play).
function pickTarget(w, r) {
  if ((w.done + 1) % 5 === 0 && T_BOX !== CITY[w.goal]) return T_BOX.id;
  const h = w.hero, ok = [];
  for (const b of CITY) {
    if (b.tower || b.h < 20 || b.h > 150 || b.id === w.goal) continue;
    const t = roofTop(b), d = Math.hypot(t.x - h.x, t.z - h.z);
    if (d >= GOAL_NEAR && d <= GOAL_FAR && Math.max(Math.abs(t.x), Math.abs(t.z)) < EDGE - 20) ok.push(b.id);
  }
  return ok.length ? ok[Math.floor(r() * ok.length)] : T_BOX.id;
}
function setGoal(w, id) {
  w.goal = id; w.gt = 0;
  w.flag = CITY[id] ? roofTop(CITY[id]) : null;
}
// One step: the clock on this roof, and the roof reached.
function stepRound(w, dt, r) {
  w.t += dt;
  if (!CITY[w.goal]) setGoal(w, pickTarget(w, r || Math.random));
  w.gt += dt;
  if (onTop(w.hero, CITY[w.goal])) {
    w.done++;
    w.got = { t: w.gt, tower: !!CITY[w.goal].tower, show: 2.5 };
    setGoal(w, pickTarget(w, r || Math.random));
    return true;
  }
  if (w.got && (w.got.show -= dt) <= 0) w.got = 0;
  return false;
}
