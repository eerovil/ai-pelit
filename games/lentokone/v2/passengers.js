'use strict';
// Lentokone v2 (#547): the passenger jet's passengers. Before the take-off a bus brings them beside the
// plane and they walk up the stairs into its front door; after a landing the stairs and the bus come
// back and they walk down and into the bus, which drives away.
//
// The first half is plain numbers (`paxScene()`), so the tests read it without WebGL. Everything is in
// the plane's own frame, as its 3D model is built: x to its right, y up from the wheels, z towards its
// tail (its nose points to -z). The second half draws it with three.js (draw3d.js calls it).

const PAX = {
  n: 16,          // passengers
  gap: 0.28,      // s between two passengers
  walk: 3.4,      // m/s on the apron (a game's quick walk)
  climb: 1.8,     // s up the stairs
  inside: 0.4,    // s from the stairs' top through the door
  vehicles: 2.5,  // s for the bus and the stairs to drive in or away
  door: 0.5,      // s for the door to open or close
};
// The way from the bus's door to the plane's front door, on the plane's left side.
const DOOR_Z = -11, BUS_X = -22, BUS_Z = -10, STAIRS_FOOT = -9.6, STAIRS_TOP = -3.0, SILL = 3.5;
const PAX_PATH = [
  { x: BUS_X + 1.6, y: 0, z: BUS_Z - 3.6 },      // out of the bus's front door
  { x: STAIRS_FOOT, y: 0, z: DOOR_Z },           // the foot of the stairs
  { x: STAIRS_TOP, y: SILL, z: DOOR_Z },         // the top
  { x: -0.9, y: SILL, z: DOOR_Z },               // in through the door
];
// Seconds spent on each leg of the way, and the whole way.
const PAX_LEGS = [Math.hypot(PAX_PATH[1].x - PAX_PATH[0].x, PAX_PATH[1].z - PAX_PATH[0].z) / PAX.walk, PAX.climb, PAX.inside];
const PAX_WAY = PAX_LEGS[0] + PAX_LEGS[1] + PAX_LEGS[2];

// Where a passenger is `u` seconds after leaving the bus. `i` gives each their own little wander on
// the apron (which ends at the stairs). Returns null before the start and after the door.
function paxAt(i, u) {
  if (u < 0 || u > PAX_WAY) return null;
  let leg = 0, t = u;
  while (leg < 2 && t > PAX_LEGS[leg]) { t -= PAX_LEGS[leg]; leg++; }
  const a = PAX_PATH[leg], b = PAX_PATH[leg + 1], k = clamp(t / PAX_LEGS[leg], 0, 1);
  let x = lerp(a.x, b.x, k), y = lerp(a.y, b.y, k), z = lerp(a.z, b.z, k);
  if (leg === 0) z += Math.sin(k * Math.PI) * (hash2(i, 5) - 0.5) * 3.2;
  return { x, y, z, leg, dx: b.x - a.x, dz: b.z - a.z, dist: leg === 0 ? k * PAX_LEGS[0] * PAX.walk : 0 };
}

// The scene at time `t` of the boarding ('board') or the leaving ('deplane'):
//   pax: one entry per passenger, null when not to be seen; aboard: how many are in the plane;
//   bus / stairs: how far each has still to drive (m, 0 = parked); door: 0 shut .. 1 open; done.
// A passenger walking down goes the same way backwards, facing the way they walk.
function paxScene(kind, t) {
  const n = PAX.n, last = (n - 1) * PAX.gap + PAX_WAY;
  const s = { pax: [], aboard: 0, bus: 0, busOn: true, stairs: 0, door: 1, done: false, t };
  if (kind === 'board') {
    const t0 = 0.6, allIn = t0 + last, go = clamp((t - allIn - PAX.door) / PAX.vehicles, 0, 1);
    for (let i = 0; i < n; i++) {
      const u = t - t0 - i * PAX.gap, q = paxAt(i, u);
      s.pax.push(q);
      if (u > PAX_WAY) s.aboard++;
    }
    s.door = 1 - clamp((t - allIn) / PAX.door, 0, 1);
    s.bus = -70 * go * go;                       // drives away ahead of the plane
    s.stairs = -16 * smooth(go);                 // pulled back away from the door
    s.busOn = go < 1;
    s.done = t >= allIn + PAX.door + PAX.vehicles;
    return s;
  }
  // Leaving: the bus comes from behind the plane and stops, the stairs come to the door.
  const come = clamp(t / PAX.vehicles, 0, 1), t0 = PAX.vehicles + PAX.door, allOut = t0 + last;
  s.bus = 60 * (1 - come) * (1 - come);
  s.stairs = -16 * (1 - smooth(come));
  s.door = clamp((t - PAX.vehicles) / PAX.door, 0, 1);
  s.aboard = n;
  for (let i = 0; i < n; i++) {
    const u = t - t0 - i * PAX.gap, q = paxAt(n - 1 - i, PAX_WAY - u);
    if (q) { q.dx = -q.dx; q.dz = -q.dz; }
    s.pax.push(q);
    if (u >= 0) s.aboard--;
  }
  const go = clamp((t - allOut - 0.3) / PAX.vehicles, 0, 1);
  if (go > 0) s.bus = -70 * go * go;
  s.busOn = go < 1;
  s.done = t >= allOut + 0.3 + PAX.vehicles;
  return s;
}

// ---- Drawing it (three.js; THREE, merge(), box() and lambert() are draw3d.js's) ----
const PAX_COLS = ['#d8443a', '#3a6ad8', '#3aa860', '#e0b030', '#8a4ad0', '#e07a2a', '#2aa0b0', '#c84a8a', '#5a5a6a', '#f0f0e8'];
const PAX_HAIR = ['#2a1e14', '#6a4422', '#c8a050', '#1a1a1a', '#8a8a8a'];
function paxGroup() {
  const grp = new THREE.Group(), people = [];
  for (let i = 0; i < PAX.n; i++) {
    const man = new THREE.Group(), body = [];
    const top = PAX_COLS[Math.floor(hash2(i, 1) * PAX_COLS.length)], hair = PAX_HAIR[Math.floor(hash2(i, 2) * PAX_HAIR.length)];
    box(body, 0.5, 0.65, 0.3, 0, 1.2, 0, top);                    // body
    box(body, 0.14, 0.6, 0.16, -0.32, 1.18, 0, top); box(body, 0.14, 0.6, 0.16, 0.32, 1.18, 0, top);   // arms
    box(body, 0.3, 0.32, 0.3, 0, 1.72, 0, '#e8b890');             // head
    box(body, 0.32, 0.12, 0.32, 0, 1.9, 0.02, hair);
    if (hash2(i, 3) < 0.6) { box(body, 0.42, 0.55, 0.22, 0, 0.42, 0.75, hash2(i, 4) < 0.5 ? '#2a2a34' : '#a8303a'); box(body, 0.04, 0.5, 0.04, 0, 0.95, 0.66, '#888888'); }   // a suitcase rolled behind
    man.add(new THREE.Mesh(merge(body), lambert()));
    const legs = [-0.13, 0.13].map(x => {
      const g = new THREE.BoxGeometry(0.18, 0.88, 0.2); g.translate(0, -0.44, 0);
      const leg = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ color: hash2(i, 6) < 0.5 ? 0x2a3450 : 0x4a4038 }));
      leg.position.set(x, 0.88, 0); man.add(leg); return leg;
    });
    man.userData = { legs };
    man.visible = false;
    grp.add(man); people.push(man);
  }
  grp.userData.people = people;
  // The bus: its door side faces the plane.
  const bp = [];
  box(bp, 2.6, 2.7, 12, 0, 1.75, 0, '#f2c230');
  box(bp, 2.64, 0.9, 10.4, 0, 2.35, 0.4, '#2a3a4a');            // windows
  box(bp, 2.64, 0.35, 12.04, 0, 0.75, 0, '#2a5aa0');            // stripe
  box(bp, 0.1, 2.2, 1.2, 1.32, 1.5, -3.6, '#3a4a5a');           // its door
  box(bp, 2.4, 1.0, 0.1, 0, 2.4, -6.02, '#2a3a4a');             // windscreen
  for (const [x, z] of [[-1.2, -4], [1.2, -4], [-1.2, 4], [1.2, 4]]) {
    const w = new THREE.CylinderGeometry(0.5, 0.5, 0.35, 12); w.rotateZ(Math.PI / 2); w.translate(x, 0.5, z); bp.push([w, '#1e1e22']);
  }
  const bus = new THREE.Mesh(merge(bp), lambert());
  bus.position.set(BUS_X, 0, BUS_Z); grp.add(bus);
  // The stairs on wheels, pushed by a little tug.
  const sp = [], run = STAIRS_TOP - STAIRS_FOOT, len = Math.hypot(run, SILL), ang = Math.atan2(SILL, run);
  for (let k = 0; k < 12; k++) {
    const u = (k + 0.5) / 12;
    box(sp, run / 12 + 0.05, 0.12, 1.5, STAIRS_FOOT + run * u, SILL * u - 0.06, 0, '#c8ccd0');
  }
  for (const zz of [-0.8, 0.8]) {
    box(sp, len, 0.3, 0.08, (STAIRS_FOOT + STAIRS_TOP) / 2, SILL / 2 - 0.2, zz, '#e8e8e8', 0, 0, ang);
    box(sp, len, 0.06, 0.06, (STAIRS_FOOT + STAIRS_TOP) / 2, SILL / 2 + 0.9, zz, '#d8d8d8', 0, 0, ang);
    box(sp, 0.08, 4.0, 0.08, STAIRS_TOP - 0.2, SILL / 2 + 0.2, zz, '#bbbbbb');
    box(sp, 0.08, 0.9, 0.08, STAIRS_TOP - 0.2, SILL + 0.45, zz, '#d8d8d8');
  }
  box(sp, 1.4, 0.15, 1.7, STAIRS_TOP + 0.3, SILL - 0.07, 0, '#c8ccd0');                // the top
  box(sp, 6.4, 0.5, 1.2, (STAIRS_FOOT + STAIRS_TOP) / 2, 0.55, 0, '#3a3e44');             // its frame
  for (const x of [STAIRS_FOOT + 0.6, STAIRS_TOP - 0.6]) for (const zz of [-0.7, 0.7]) {
    const w = new THREE.CylinderGeometry(0.3, 0.3, 0.2, 10); w.rotateX(Math.PI / 2); w.translate(x, 0.3, zz); sp.push([w, '#1e1e22']);
  }
  box(sp, 2.4, 1.3, 1.8, STAIRS_FOOT - 1.8, 0.95, 0, '#e86a1a');                         // the tug
  box(sp, 1.0, 0.7, 1.7, STAIRS_FOOT - 1.4, 1.95, 0, '#2a3a4a');
  const stairs = new THREE.Mesh(merge(sp), lambert());
  stairs.position.set(0, 0, DOOR_Z); grp.add(stairs);
  grp.userData.bus = bus; grp.userData.stairs = stairs;
  grp.rotation.order = 'YXZ';
  grp.visible = false;
  return grp;
}
// Puts the scene beside the plane (on the ground, turned as it is) and each passenger in place.
function drawPax(grp, p, s) {
  grp.visible = !!s;
  if (!s) return;
  grp.position.set(p.x, p.y, p.z);
  grp.rotation.set(0, -p.hdg, 0);
  const u = grp.userData;
  u.bus.position.z = BUS_Z + s.bus; u.bus.visible = s.busOn;
  u.stairs.position.x = s.stairs;
  u.people.forEach((man, i) => {
    const q = s.pax[i];
    man.visible = !!q;
    if (!q) return;
    man.position.set(q.x, q.y, q.z);
    man.rotation.y = Math.atan2(-q.dx, -q.dz);
    // Legs swing with the steps on the apron, step up on the stairs.
    const sw = q.leg === 0 ? Math.sin(q.dist * 3.4) * 0.6 : q.leg === 1 ? Math.sin(s.t * 12 + i) * 0.45 : 0;
    man.userData.legs[0].rotation.x = sw; man.userData.legs[1].rotation.x = -sw;
  });
}
