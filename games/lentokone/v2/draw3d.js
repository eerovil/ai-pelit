'use strict';
// Lentokone v2 (#547; v1 #533): the world and the planes in 3D (three.js, the site's shared copy, #99). It only
// reads world.js's numbers. index.html imports three.js and calls init3d(THREE); a phone that cannot
// draw 3D says so in the HUD.

let THREE = null, V3 = null, no3d = false, camView = 'chase';   // 'chase' behind, 'cockpit' inside
// Looking around (#547, Eero's ask): a finger drag turns the view by `yaw` (around the plane, radians)
// and `pitch` (up); `held` while the finger is down. A moment after it lifts, the view glides back.
const LOOK = { yaw: 0, pitch: 0, held: false, idle: 0 };
const LOOK_BACK = 1.2;   // s after the finger lifts before the view turns back
function lookStep(dt) {
  if (LOOK.held) { LOOK.idle = 0; return; }
  LOOK.idle += dt;
  if (LOOK.idle < LOOK_BACK) return;
  const k = Math.min(1, dt * 2.5);
  LOOK.yaw -= LOOK.yaw * k; LOOK.pitch -= LOOK.pitch * k;
  if (Math.abs(LOOK.yaw) < 1e-3) LOOK.yaw = 0;
  if (Math.abs(LOOK.pitch) < 1e-3) LOOK.pitch = 0;
}
function lookReset() { LOOK.yaw = LOOK.pitch = 0; LOOK.held = false; LOOK.idle = 0; }

const TER_N = 160, TER_CELL = 60;           // the land: 9.6 km square round the plane, rebuilt as it flies
const TREE_R = 2600, TREE_MAX = 3200;       // trees within this distance

function init3d(T) {
  THREE = T;
  const gl = document.getElementById('g');
  // Edge smoothing only on a coarse screen: a phone's dense one hardly shows the steps and is short of
  // pixels, and on this host's card it drew specks along the fogged horizon.
  const renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: (window.devicePixelRatio || 1) < 1.5, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, 1, 0.4, 9000);
  const hemi = new THREE.HemisphereLight(0xcfe4ff, 0x4a5a3a, 1.6);
  const sun = new THREE.DirectionalLight(0xfff2dc, 1.6);
  scene.add(hemi, sun, sun.target);
  scene.fog = new THREE.Fog(0xb8d4ee, 1200, 3800);
  V3 = { renderer, scene, camera, hemi, sun, w: 0, h: 0, t: 0, cx: NaN, cz: NaN, cam: null, route: null, look: 'day', v: new THREE.Vector3() };
  V3.sky = skyDome(); scene.add(V3.sky);
  V3.water = new THREE.Mesh(new THREE.PlaneGeometry(14000, 14000), new THREE.MeshLambertMaterial({ color: 0x3f6f9a }));
  V3.water.rotation.x = -Math.PI / 2; V3.water.position.y = WATER + 0.25; scene.add(V3.water);
  V3.land = landMesh(); scene.add(V3.land);
  V3.trees = treeMeshes(); scene.add(V3.trees.spruce, V3.trees.birch);
  V3.fields = FIELDS.map((f, i) => { const g = airfield(f, i); scene.add(g); return g; });
  V3.town = town(); scene.add(V3.town);
  V3.planes = { pieni: planeModel(), iso: airlinerModel() };
  scene.add(V3.planes.pieni, V3.planes.iso);
  V3.plane = V3.planes.pieni;
  V3.pax = paxGroup(); scene.add(V3.pax);
  V3.shadow = new THREE.Mesh(new THREE.CircleGeometry(5, 20), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.25, depthWrite: false }));
  V3.shadow.rotation.x = -Math.PI / 2; scene.add(V3.shadow);
  V3.guide = new THREE.Group(); scene.add(V3.guide);
}

// Vertex colours are linear: fill them from THREE.Color('#hex').
function merge(parts) {
  const c = new THREE.Color();
  const geos = parts.map(([g, hex]) => {
    g = g.index ? g.toNonIndexed() : g;
    const n = g.attributes.position.count, a = new Float32Array(n * 3);
    c.set(hex); for (let i = 0; i < n; i++) { a[i * 3] = c.r; a[i * 3 + 1] = c.g; a[i * 3 + 2] = c.b; }
    g.setAttribute('color', new THREE.BufferAttribute(a, 3)); return g;
  });
  const out = new THREE.BufferGeometry();
  for (const name of ['position', 'normal', 'color']) {
    const n = geos.reduce((s, g) => s + g.attributes[name].array.length, 0), a = new Float32Array(n);
    let o = 0; for (const g of geos) { a.set(g.attributes[name].array, o); o += g.attributes[name].array.length; }
    out.setAttribute(name, new THREE.BufferAttribute(a, 3));
  }
  return out;
}
const lambert = () => new THREE.MeshLambertMaterial({ vertexColors: true });
function box(parts, w, h, d, x, y, z, col, rx, ry, rz) {
  const g = new THREE.BoxGeometry(w, h, d);
  if (rx) g.rotateX(rx); if (ry) g.rotateY(ry); if (rz) g.rotateZ(rz);
  g.translate(x, y, z); parts.push([g, col]);
}

function skyDome() {
  const g = new THREE.SphereGeometry(8000, 24, 12);
  g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 3), 3));
  const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false, depthWrite: false }));
  m.renderOrder = -2;
  return m;
}
function paintSky(top, low) {
  const g = V3.sky.geometry, p = g.attributes.position, c = new THREE.Color(), t = new THREE.Color(top), l = new THREE.Color(low);
  for (let i = 0; i < p.count; i++) { c.copy(l).lerp(t, clamp(p.getY(i) / 2500, 0, 1)); g.attributes.color.setXYZ(i, c.r, c.g, c.b); }
  g.attributes.color.needsUpdate = true;
}
// Day or dusk (route 4): the sky, the light, the fog, the runway lights.
function setLook(dusk) {
  const look = dusk ? 'dusk' : 'day';
  if (V3.look === look && V3.painted) return;
  V3.look = look; V3.painted = true;
  if (dusk) {
    paintSky('#1c2346', '#e0835a'); V3.scene.fog.color.set('#5a4a5e'); V3.scene.fog.near = 800; V3.scene.fog.far = 3500;
    V3.hemi.intensity = 0.55; V3.hemi.color.set('#8a90c0'); V3.sun.intensity = 0.5; V3.sun.color.set('#ff9a6a');
  } else {
    paintSky('#4f8fd8', '#cfe2f4'); V3.scene.fog.color.set('#c4dbef'); V3.scene.fog.near = 1200; V3.scene.fog.far = 3800;
    V3.hemi.intensity = 1.6; V3.hemi.color.set('#cfe4ff'); V3.sun.intensity = 1.6; V3.sun.color.set('#fff2dc');
  }
  for (const f of V3.fields) for (const l of f.userData.lights) l.material.color.set(dusk ? '#fff3b0' : '#c8c0a0');
  for (const f of V3.fields) f.userData.approach.visible = dusk;
}

// ---- The land: one grid round the plane, rebuilt when it has flown 800 m ----
function landMesh() {
  const g = new THREE.PlaneGeometry(TER_N * TER_CELL, TER_N * TER_CELL, TER_N, TER_N);
  g.rotateX(-Math.PI / 2);
  g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 3), 3));
  const m = new THREE.Mesh(g, lambert());
  m.frustumCulled = false;
  return m;
}
const LAND_COLS = { sand: '#cdbb8a', grass: '#6f9a48', forest: '#3f6a34', dark: '#2f5530', heath: '#8a8a5a', rock: '#8d8a80', field: '#8fb25a' };
function buildLand(cx, cz) {
  const g = V3.land.geometry, p = g.attributes.position, col = g.attributes.color, c = new THREE.Color(), half = TER_N * TER_CELL / 2;
  const C = {}; for (const k in LAND_COLS) C[k] = new THREE.Color(LAND_COLS[k]);
  let i = 0;
  for (let r = 0; r <= TER_N; r++) for (let q = 0; q <= TER_N; q++, i++) {
    const x = cx - half + q * TER_CELL, z = cz - half + r * TER_CELL, h = heightAt(x, z);
    // Under water the land is drawn deeper, so far away it never flickers through the water's surface.
    p.setXYZ(i, x, h < WATER ? h * 3 - 6 : h, z);
    const n = hash2(Math.round(x / TER_CELL), Math.round(z / TER_CELL));
    if (h < 1.5) c.copy(C.sand);
    else if (h > 230) c.copy(C.rock).lerp(C.heath, n);
    else if (h > 150) c.copy(C.heath).lerp(C.forest, n * 0.6);
    else c.copy(C.forest).lerp(n < 0.5 ? C.dark : C.grass, Math.abs(n - 0.5) * 1.6);
    // Mown grass round each airfield.
    for (const f of FIELDS) { const o = onRunway(f, x, z); if (o.a > -250 && o.a < f.len + 250 && Math.abs(o.c) < 200) c.lerp(C.field, 0.85); }
    col.setXYZ(i, c.r, c.g, c.b);
  }
  p.needsUpdate = true; col.needsUpdate = true; g.computeVertexNormals();
  V3.cx = cx; V3.cz = cz;
  placeTrees(cx, cz);
}

function treeMeshes() {
  const sp = [], bi = [];
  const cone = (r, h, y, col) => { const g = new THREE.ConeGeometry(r, h, 7); g.translate(0, y, 0); sp.push([g, col]); };
  const trunk = new THREE.CylinderGeometry(0.4, 0.5, 3, 5); trunk.translate(0, 1.5, 0); sp.push([trunk, '#5a3a22']);
  cone(4.2, 8, 6, '#24502a'); cone(3.2, 6.5, 10, '#2a5c30'); cone(2, 5, 13.5, '#316836');
  const bt = new THREE.CylinderGeometry(0.35, 0.45, 9, 5); bt.translate(0, 4.5, 0); bi.push([bt, '#e8e4dc']);
  const crown = new THREE.IcosahedronGeometry(3.6, 0); crown.scale(1, 1.3, 1); crown.translate(0, 10, 0); bi.push([crown, '#d0a83a']);
  const spruce = new THREE.InstancedMesh(merge(sp), lambert(), TREE_MAX);
  const birch = new THREE.InstancedMesh(merge(bi), lambert(), Math.round(TREE_MAX / 2));
  spruce.frustumCulled = birch.frustumCulled = false;
  spruce.count = birch.count = 0;
  return { spruce, birch };
}
function placeTrees(cx, cz) {
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), v = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
  const T = V3.trees; let ns = 0, nb = 0;
  const n = Math.ceil(TREE_R / 55), i0 = Math.round(cx / 55), j0 = Math.round(cz / 55);
  for (let j = j0 - n; j <= j0 + n; j++) for (let i = i0 - n; i <= i0 + n; i++) {
    if ((i - i0) ** 2 + (j - j0) ** 2 > n * n) continue;
    const t = treeAt(i, j);
    if (!t) continue;
    q.setFromAxisAngle(up, hash2(i, j + 9) * TAU); s.setScalar(t.s); v.set(t.x, t.y - 0.5, t.z);
    m.compose(v, q, s);
    if (t.birch) { if (nb < T.birch.instanceMatrix.count) T.birch.setMatrixAt(nb++, m); }
    else if (ns < TREE_MAX) T.spruce.setMatrixAt(ns++, m);
  }
  T.spruce.count = ns; T.birch.count = nb;
  T.spruce.instanceMatrix.needsUpdate = T.birch.instanceMatrix.needsUpdate = true;
}

// ---- An airfield: the runway with its markings and lights, a hangar, a tower, the windsock ----
function airfield(f, idx) {
  const grp = new THREE.Group(), parts = [], len = f.len, wid = f.wid;
  // In the runway's own frame: x across (right +), z along (-z from the threshold onwards).
  box(parts, wid, 0.3, len, 0, 0.05, -len / 2, '#4a4c50');
  for (let a = 60; a < len - 40; a += 50) box(parts, 0.9, 0.32, 24, 0, 0.06, -a - 12, '#f2f2f0');
  for (const end of [0, len]) for (let k = -3; k <= 3; k++) if (k) box(parts, 1.6, 0.32, 26, k * (wid / 8), 0.06, end ? -len + 16 : -16, '#f2f2f0');
  box(parts, 0.6, 0.32, len, -wid / 2 + 1, 0.06, -len / 2, '#e8e8e4'); box(parts, 0.6, 0.32, len, wid / 2 - 1, 0.06, -len / 2, '#e8e8e4');
  // Touchdown zone bars.
  for (const a of [len < 700 ? 120 : 220]) for (const sx of [-1, 1]) box(parts, 4, 0.32, 40, sx * wid / 4, 0.06, -a, '#f2f2f0');
  // Hangar and tower beside the runway's start.
  const side = wid / 2 + 70;
  box(parts, 30, 10, 26, side + 10, 5, -len * 0.25, '#9aa2aa'); box(parts, 30.4, 1.2, 26.4, side + 10, 10.4, -len * 0.25, '#7a2a2a');
  box(parts, 5, 14, 5, side - 10, 7, -len * 0.45, '#d8d4c8'); box(parts, 7, 3.4, 7, side - 10, 15.6, -len * 0.45, '#3a6a8a');
  const runway = new THREE.Mesh(merge(parts), lambert());
  grp.add(runway);
  // Edge lights, both sides every 60 m, and the threshold's green bar.
  const lights = [], lm = new THREE.MeshBasicMaterial({ color: 0xc8c0a0 });
  const lg = new THREE.BoxGeometry(0.8, 0.8, 0.8);
  const edges = new THREE.InstancedMesh(lg, lm, Math.ceil(len / 60 + 1) * 2);
  let k = 0; const mm = new THREE.Matrix4();
  for (let a = 0; a <= len; a += 60) for (const sx of [-1, 1]) { mm.makeTranslation(sx * (wid / 2 + 2), 0.6, -a); edges.setMatrixAt(k++, mm); }
  edges.count = k; grp.add(edges); lights.push(edges);
  // Approach lights before the threshold (shown at dusk).
  const appr = new THREE.InstancedMesh(lg, new THREE.MeshBasicMaterial({ color: 0xfff6c0 }), 60);
  k = 0;
  for (let a = 60; a <= 600; a += 60) for (let s = -2; s <= 2; s++) { mm.makeTranslation(s * 3, 1, a); appr.setMatrixAt(k++, mm); }
  appr.count = k; appr.visible = false; grp.add(appr);
  // The glide-path lights (PAPI) left of the runway, 250 m on.
  const papiG = new THREE.BoxGeometry(2.2, 1.4, 1.4), papiM = [];
  for (let i = 0; i < 4; i++) { const pm = new THREE.Mesh(papiG, new THREE.MeshBasicMaterial({ color: 0xffffff, fog: false })); pm.position.set(-wid / 2 - 12 - i * 9, 1, -aimAt(f)); grp.add(pm); papiM.push(pm); }
  // The windsock.
  const sock = new THREE.Group();
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 7, 5), new THREE.MeshLambertMaterial({ color: 0xdddddd })); pole.position.y = 3.5; sock.add(pole);
  const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.9, 4, 8, 1, true), new THREE.MeshLambertMaterial({ color: 0xff6a1a, side: THREE.DoubleSide }));
  cone.rotation.x = Math.PI / 2; cone.position.set(0, 0, 2); const arm = new THREE.Group(); arm.position.y = 7; arm.add(cone); sock.add(arm);
  sock.position.set(side - 30, 0, -120); grp.add(sock);
  grp.position.set(f.x, f.elev, f.z);
  grp.rotation.y = -f.hdg;
  grp.userData = { lights: [edges, appr], approach: appr, papi: papiM, sock: arm, idx };
  return grp;
}

// Houses round Kaupunkikenttä, and a few by the other fields.
function town() {
  const parts = [], r = rng(31), cols = ['#c94a3a', '#e8d8b0', '#f2f0ea', '#d8b84a', '#7a8aa0'];
  const put = (cx, cz, n, spread) => {
    for (let i = 0; i < n; i++) {
      const x = cx + (r() - 0.5) * spread, z = cz + (r() - 0.5) * spread;
      if (runwayAt(x, z, 160) >= 0 || isWater(x, z)) continue;
      const h = heightAt(x, z), w = 8 + r() * 10, d = 8 + r() * 8, tall = r() < 0.15 ? 14 + r() * 20 : 5 + r() * 3;
      box(parts, w, tall, d, x, h + tall / 2, z, cols[Math.floor(r() * cols.length)]);
      box(parts, w + 1, 1.2, d + 1, x, h + tall + 0.6, z, '#4a3a3a');
    }
  };
  put(19600, -1200, 220, 2200);
  for (const f of FIELDS) put(f.x + dirZ(f.hdg) * -260, f.z + dirX(f.hdg) * 260, 8, 300);
  return new THREE.Mesh(merge(parts), lambert());
}

// ---- The plane: built facing -z, wheels at y = 0 ----
function planeModel() {
  const grp = new THREE.Group(), body = [], W = '#f4f4f0', R = '#c8202f', D = '#2a2e36';
  box(body, 1.3, 1.4, 6.2, 0, 1.75, 0.2, W);            // fuselage
  box(body, 1.32, 0.3, 6.22, 0, 1.6, 0.2, R);           // stripe
  box(body, 0.8, 0.9, 2.4, 0, 1.95, 4.4, W);            // tail cone
  box(body, 1.2, 1.0, 0.8, 0, 1.75, -3.2, '#d8d8d4');   // engine cowl
  box(body, 1.22, 0.62, 1.6, 0, 2.55, -1.2, '#4a6a8a');  // windows
  box(body, 0.14, 1.9, 1.4, 0, 3.0, 5.2, R);            // fin
  box(body, 3.8, 0.12, 1.1, 0, 2.2, 5.2, W);            // tailplane
  box(body, 11, 0.18, 1.6, 0, 2.95, -0.8, W);            // wing
  box(body, 0.6, 0.2, 1.62, 5.2, 2.95, -0.8, R); box(body, 0.6, 0.2, 1.62, -5.2, 2.95, -0.8, R);
  for (const sx of [-1, 1]) box(body, 0.1, 1.5, 0.12, sx * 1.9, 2.3, -0.8, '#bbbbbb', 0, 0, sx * 0.95);
  const fuse = new THREE.Mesh(merge(body), lambert());
  grp.add(fuse);
  // Flaps hinge at the wing's back edge, inside the struts.
  const flapG = new THREE.BoxGeometry(3, 0.1, 0.5); flapG.translate(0, 0, 0.25);
  const flaps = [-1, 1].map(sx => { const f = new THREE.Mesh(flapG, new THREE.MeshLambertMaterial({ color: 0xe8e8e4 })); f.position.set(sx * 2.4, 2.86, 0); grp.add(f); return f; });
  // Gear: fixed legs that fold up (a game plane may).
  const gp = [];
  for (const [x, z] of [[-1.3, 0.2], [1.3, 0.2], [0, -2.6]]) {
    box(gp, 0.12, 1.1, 0.12, x, 0.85, z, '#999999');
    const wh = new THREE.CylinderGeometry(0.35, 0.35, 0.22, 10); wh.rotateZ(Math.PI / 2); wh.translate(x, 0.35, z); gp.push([wh, D]);
  }
  const gear = new THREE.Mesh(merge(gp), lambert()); grp.add(gear);
  const prop = new THREE.Group(), blade = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.18, 0.06), new THREE.MeshLambertMaterial({ color: 0x222222 }));
  prop.add(blade); prop.position.set(0, 1.75, -3.65); grp.add(prop);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(1.0, 20), new THREE.MeshBasicMaterial({ color: 0x888888, transparent: true, opacity: 0.18, depthWrite: false, side: THREE.DoubleSide }));
  disc.position.copy(prop.position); disc.position.z -= 0.04; grp.add(disc);
  grp.rotation.order = 'YXZ';
  grp.userData = { fuse, flaps, gear, prop, disc };
  return grp;
}

// ---- The passenger jet (#547): built facing -z, wheels at y = 0, about 40 m long ----
// Its front door is on the left (x = -2) at DOOR_Z, its sill at SILL (passengers.js).
function airlinerModel() {
  const grp = new THREE.Group(), body = [], W = '#f4f4f2', R = '#c8202f', B = '#1e4e9a', D = '#2a2e36', G = '#c8ccd0';
  const cyl = (r1, r2, len, z, y, col) => { const g = new THREE.CylinderGeometry(r1, r2, len, 18); g.rotateX(Math.PI / 2); g.translate(0, y, z); body.push([g, col]); };
  cyl(2, 2, 30, 0, 4.4, W);                                         // the cabin
  const nose = new THREE.SphereGeometry(2, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2); nose.rotateX(-Math.PI / 2); nose.scale(1, 1, 1.7); nose.translate(0, 4.4, -15); body.push([nose, W]);
  cyl(0.55, 2, 8, 19, 4.9, W);                                      // the tail cone (wide end forward)
  box(body, 4.06, 0.5, 30, 0, 3.2, 0, G);                           // a grey belly
  for (const sx of [-1, 1]) {
    box(body, 0.08, 0.32, 30, sx * 2.0, 3.95, 0, B);                // the cheat line
    for (let z = -12.5; z <= 12.5; z += 1.15) if (Math.abs(z - DOOR_Z) > 1) box(body, 0.08, 0.42, 0.34, sx * 2.0, 4.95, z, D);   // windows
    box(body, 0.9, 0.5, 0.5, sx * 0.75, 5.25, -17.0, D, -0.5);      // cockpit windows
  }
  // The fin and the tailplane, swept back.
  box(body, 0.35, 6.5, 4.6, 0, 8.6, 20.6, R, 0.5);
  box(body, 0.37, 1.0, 3.0, 0, 11.2, 22.0, W, 0.5);
  for (const sx of [-1, 1]) box(body, 5.6, 0.28, 2.4, sx * 3.2, 5.2, 20.6, W, 0, sx * -0.45);
  // The wings, low and swept, and the engines under them.
  for (const sx of [-1, 1]) {
    box(body, 15.5, 0.45, 4.2, sx * 9.4, 3.1, 1.6, W, 0, sx * -0.42, sx * 0.06);
    box(body, 1.0, 0.5, 1.6, sx * 16.8, 3.6, 5.2, R, 0, sx * -0.42);   // the wing tips
    const eng = new THREE.CylinderGeometry(1.15, 1.0, 4.4, 16); eng.rotateX(Math.PI / 2); eng.translate(sx * 6.4, 1.9, -1.6); body.push([eng, '#d8dce0']);
    const fan = new THREE.CircleGeometry(1.0, 16); fan.rotateY(Math.PI); fan.translate(sx * 6.4, 1.9, -3.82); body.push([fan, '#30343a']);
    box(body, 0.4, 1.1, 2.6, sx * 6.4, 2.9, -0.8, G);                 // pylon
  }
  const fuse = new THREE.Mesh(merge(body), lambert());
  grp.add(fuse);
  // The front door: shut it sits in the side; open it swings forward along the side.
  const doorFrame = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.9, 1.0), new THREE.MeshLambertMaterial({ color: 0x1a1c20 }));
  doorFrame.position.set(-1.99, SILL + 0.95, DOOR_Z); grp.add(doorFrame);
  const door = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.9, 1.0), new THREE.MeshLambertMaterial({ color: 0xe8e8e6 }));
  door.position.set(-2.04, SILL + 0.95, DOOR_Z); grp.add(door);
  // Gear: two-wheel legs, folding up.
  const gp = [];
  for (const [x, z, h] of [[0, -13, 2.6], [-3.0, 2.6, 2.4], [3.0, 2.6, 2.4]]) {
    box(gp, 0.25, h, 0.25, x, h / 2 + 0.5, z, '#999999');
    for (const dx of [-0.35, 0.35]) { const wh = new THREE.CylinderGeometry(0.55, 0.55, 0.35, 12); wh.rotateZ(Math.PI / 2); wh.translate(x + dx, 0.55, z); gp.push([wh, D]); }
  }
  const gear = new THREE.Mesh(merge(gp), lambert()); grp.add(gear);
  grp.rotation.order = 'YXZ';
  grp.userData = { fuse, flaps: [], gear, prop: null, disc: null, door, doorFrame, big: true };
  grp.visible = false;
  return grp;
}

// Rings on the glide path of a route that has a guide line (routes 1 and 2).
function buildGuide(route) {
  const g = V3.guide;
  while (g.children.length) { const c = g.children.pop(); c.geometry.dispose(); }
  if (!route.guide) return;
  const f = FIELDS[route.to], m = new THREE.MeshBasicMaterial({ color: 0xffd23a, transparent: true, opacity: 0.55 }), geo = new THREE.TorusGeometry(14, 0.6, 6, 24);
  for (let d = 300; d <= APPROACH; d += 300) {
    const r = new THREE.Mesh(geo, m);
    r.position.set(f.x - dirX(f.hdg) * d, f.elev + 14 + (d + aimAt(f)) * Math.tan(GLIDE), f.z - dirZ(f.hdg) * d);
    r.rotation.y = -f.hdg;
    g.add(r);
  }
}

// ---- Each frame ----
function render3d(p, route, dt, still, pax) {
  if (!V3) return false;
  const R = V3.renderer, cv = R.domElement, w = cv.clientWidth || innerWidth, h = cv.clientHeight || innerHeight;
  if (w !== V3.w || h !== V3.h) { V3.w = w; V3.h = h; R.setSize(w, h, false); V3.camera.aspect = w / h; V3.camera.updateProjectionMatrix(); }
  if (V3.route !== route) { V3.route = route; buildGuide(route); setLook(!!route.dusk); V3.cam = null; }
  if (!(Math.abs(p.x - V3.cx) < 800 && Math.abs(p.z - V3.cz) < 800)) buildLand(Math.round(p.x / TER_CELL) * TER_CELL, Math.round(p.z / TER_CELL) * TER_CELL);
  V3.t += dt;
  const want = V3.planes[p.kind] || V3.planes.pieni;
  if (V3.plane !== want) { V3.plane.visible = false; V3.plane = want; }
  const P = V3.plane, u = P.userData;
  P.visible = true;
  P.position.set(p.x, p.y, p.z);
  P.rotation.set(p.pit, -p.hdg, -p.bank);
  if (p.over && !p.over.ok) P.rotation.z = -p.bank + 0.5;   // a crash leaves it on one wing
  u.gear.visible = p.gear;
  for (const f of u.flaps) f.rotation.x = -p.flaps * 0.35;
  if (u.prop && !still) u.prop.rotation.z += dt * (6 + p.thr * 60);
  if (u.disc) u.disc.material.opacity = 0.06 + p.thr * 0.2;
  if (u.door) { const o = pax ? pax.door : 0; u.door.position.set(-2.04 - o * 0.35, SILL + 0.95, DOOR_Z - o * 1.05); }
  drawPax(V3.pax, p, pax);
  const gnd = groundAt(p.x, p.z), agl = p.y - gnd;
  V3.shadow.position.set(p.x, gnd + 0.35, p.z);
  V3.shadow.scale.setScalar(u.big ? 3.4 : 1);
  V3.shadow.material.opacity = (u.big ? 0.16 : 0.28) * clamp(1 - agl / (u.big ? 160 : 80), 0, 1);
  V3.shadow.visible = agl < 80 && !isWater(p.x, p.z) || agl < 2;
  // The glide-path lights and the windsock of each field.
  const wind = windOf(route, p.t);
  for (const g of V3.fields) {
    const f = FIELDS[g.userData.idx], lit = papi(p, f);
    g.userData.papi.forEach((m, i) => m.material.color.set(!lit ? '#ffffff' : lit[i] ? '#ffffff' : '#ff2a2a'));
    const ws = Math.hypot(wind.x, wind.z);
    g.userData.sock.rotation.y = Math.atan2(wind.x, wind.z) + f.hdg;
    g.userData.sock.rotation.x = (Math.PI / 2 - 0.15) * (1 - clamp(ws / 8, 0, 1)) * 0.9;
  }
  const cam = V3.camera;
  if (!still && !pax) lookStep(dt);
  if (pax) paxCamera(p, cam);
  else if (camView === 'cockpit') cockpitCamera(p, cam);
  else chaseCamera(p, cam, dt, still);
  V3.sky.position.copy(cam.position);
  V3.water.position.x = cam.position.x; V3.water.position.z = cam.position.z;
  V3.sun.position.set(cam.position.x + 800, cam.position.y + 1200, cam.position.z + 400); V3.sun.target.position.copy(cam.position);
  R.render(V3.scene, cam);
  return true;
}

// Behind the plane, along its heading, a little above; the horizon tilts a little with the bank.
function chaseCamera(p, cam, dt, still) {
  const u = V3.plane.userData, big = u.big ? 2.5 : 1;
  u.fuse.visible = true; if (u.prop) u.prop.visible = true;
  const back = (LAND ? 27 : 34) * big, up = (LAND ? 6.5 : 8.5) * big;
  // Looking around turns the camera about the plane: `h` the way it looks, the pitch raising it.
  const h = p.hdg + LOOK.yaw, flat = back * Math.cos(p.gam) * Math.cos(LOOK.pitch);
  const want = [p.x - dirX(h) * flat, p.y + up - Math.sin(p.gam) * back + Math.sin(LOOK.pitch) * back, p.z - dirZ(h) * flat];
  want[1] = Math.max(want[1], groundAt(want[0], want[2]) + 2);
  if (!V3.cam) { V3.cam = want.slice(); V3.look3 = null; }
  const k = still ? 1 : Math.min(1, dt * (LOOK.held || LOOK.yaw ? 10 : 4));
  for (let i = 0; i < 3; i++) V3.cam[i] += (want[i] - V3.cam[i]) * k;
  cam.position.set(...V3.cam);
  cam.up.set(Math.cos(p.hdg) * Math.sin(p.bank * 0.35), Math.cos(p.bank * 0.35), Math.sin(p.hdg) * Math.sin(p.bank * 0.35));
  // Where it looks follows as smoothly, so the view turns from the passengers' scene to the flight.
  const look = [p.x + dirX(h) * 30 * big, p.y + 3 * big + Math.sin(p.gam) * 30 * big, p.z + dirZ(h) * 30 * big];
  if (!V3.look3) V3.look3 = look.slice();
  for (let i = 0; i < 3; i++) V3.look3[i] += (look[i] - V3.look3[i]) * k;
  cam.lookAt(...V3.look3);
  cam.fov = LAND ? 55 : 66; cam.updateProjectionMatrix();
}
// From the pilot's seat: the view turns and tilts with the plane; the wing is above.
function cockpitCamera(p, cam) {
  // The fuselage and the blade would fill the view; the spinning disc stays, faint.
  const u = V3.plane.userData;
  u.fuse.visible = false; if (u.prop) u.prop.visible = false;
  V3.plane.updateMatrixWorld(true);
  if (u.big) cam.position.set(0, 5.3, -16.5); else cam.position.set(0, 2.45, -1.0);
  cam.position.applyMatrix4(V3.plane.matrixWorld);
  cam.quaternion.setFromEuler(V3.plane.rotation);
  cam.rotateX(-0.06);
  // Turning the head: around the plane's own up, then up or down.
  cam.rotateY(-LOOK.yaw); cam.rotateX(LOOK.pitch);
  cam.up.set(0, 1, 0);
  cam.fov = LAND ? 62 : 75; cam.updateProjectionMatrix();
  V3.cam = V3.look3 = null;
}
// The passengers' scene (#547): from ahead and left of the plane, over the bus and the stairs. The
// chase camera takes over from here when the flight starts.
const PAX_CAM = { port: [-30, 15, -50], land: [-25, 9, -33], at: [-10, 2.2, -9] };
function paxCamera(p, cam) {
  const u = V3.plane.userData;
  u.fuse.visible = true; if (u.prop) u.prop.visible = true;
  const toW = ([lx, ly, lz]) => [p.x + lx * Math.cos(p.hdg) - lz * Math.sin(p.hdg), p.y + ly, p.z + lx * Math.sin(p.hdg) + lz * Math.cos(p.hdg)];
  // Looking around circles the camera about the stairs, and raises it.
  const [ox, oy, oz] = LAND ? PAX_CAM.land : PAX_CAM.port, [ax, , az] = PAX_CAM.at;
  const cy = Math.cos(LOOK.yaw), sy = Math.sin(LOOK.yaw), dx = ox - ax, dz = oz - az, r = Math.hypot(dx, dz);
  const lx = ax + (dx * cy - dz * sy) * Math.cos(LOOK.pitch), lz = az + (dx * sy + dz * cy) * Math.cos(LOOK.pitch);
  const pos = toW([lx, oy + Math.sin(LOOK.pitch) * r, lz]), at = toW(PAX_CAM.at);
  pos[1] = Math.max(pos[1], groundAt(pos[0], pos[2]) + 3);
  cam.position.set(...pos); cam.up.set(0, 1, 0); cam.lookAt(...at);
  cam.fov = LAND ? 55 : 62; cam.updateProjectionMatrix();
  V3.cam = pos; V3.look3 = at;
}

// A slow phone: measured over the first seconds of a flight, below 27 frames a second it draws fewer
// pixels, half a step at a time down to one per screen pixel (Hiihto v7's `tune()`).
function tune(ms) {
  if (!V3 || V3.tuned || ms > 500) return;
  V3.tt = (V3.tt || 0) + ms; V3.tn = (V3.tn || 0) + 1;
  if (V3.tt < 2500) return;
  const fps = 1000 * V3.tn / V3.tt, R = V3.renderer, pr = R.getPixelRatio();
  V3.tt = V3.tn = 0;
  if (V3.warm !== true) { V3.warm = true; return; }
  if (fps >= 27) V3.tuned = true;
  else if (pr > 1.01) { R.setPixelRatio(Math.max(1, pr - 0.5)); V3.w = 0; }
  else V3.tuned = true;
}
