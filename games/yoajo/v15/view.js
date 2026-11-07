// Yöajo: the drive drawn in 3D with the site's shared three.js (#99). index.html imports the
// library and calls init3d(); draw3d() is called every frame. Nothing here changes the game.

let THREE = null, V3 = null, no3d = false;

function init3d() {
  const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('g'), antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(62, 1, 0.1, 900);
  // Moonlight under clouds: just enough to tell the forest from the sky. The headlights do the rest.
  const moon = new THREE.HemisphereLight(0x3a4a66, 0x101216, 0.6);
  // The player's headlights: one spot for both, aimed further and narrower on high beams.
  const beam = new THREE.SpotLight(0xfff2d8, 1, 60, 0.5, 0.55, 1);
  // The nearest oncoming car lights the road in front of it too.
  const other = new THREE.SpotLight(0xfff2d8, 0, 70, 0.45, 0.6, 1);
  scene.add(moon, beam, beam.target, other, other.target);
  const glow = glowTexture();
  const mats = {
    glowW: new THREE.SpriteMaterial({ map: glow, color: 0xfff4dc, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }),
    glowR: new THREE.SpriteMaterial({ map: glow, color: 0xff2a1a, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }),
    glowO: new THREE.SpriteMaterial({ map: glow, color: 0xffa21a, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }),
    glowY: new THREE.SpriteMaterial({ map: glow, color: 0xffd27a, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }),
    glowB: new THREE.SpriteMaterial({ map: glow, color: 0x2f62ff, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }),
    glowGreen: new THREE.SpriteMaterial({ map: glow, color: 0x2aff6a, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }),
    lampW: new THREE.MeshBasicMaterial({ color: 0xfff6e0 }),
    lampR: new THREE.MeshBasicMaterial({ color: 0xff3020 }),
    tyre: new THREE.MeshLambertMaterial({ color: 0x111111 }),
    glass: new THREE.MeshLambertMaterial({ color: 0x1a2330 }),
    grey: new THREE.MeshLambertMaterial({ color: 0x8a8d92 }),
    dark: new THREE.MeshLambertMaterial({ color: 0x2c2f33 }),
  };
  const geo = { box: new THREE.BoxGeometry(1, 1, 1), wheel: new THREE.CylinderGeometry(1, 1, 1, 12).rotateZ(Math.PI / 2), ball: new THREE.SphereGeometry(1, 10, 8), pole: new THREE.CylinderGeometry(1, 1, 1, 6), plate: new THREE.PlaneGeometry(1, 1) };
  V3 = { renderer, scene, camera, moon, beam, other, glow, mats, geo, world: null, built: null, meshes: new Map(), w: 0, h: 0, carMesh: null, weather: null, signs: [], camMeshes: [] };
  V3.carMesh = carMesh(0xb8c4d0, true);
  scene.add(V3.carMesh);
}

// A soft round light: headlights, tail lights and beacons are drawn with it, always bright.
function glowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d'), r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.18, 'rgba(255,255,255,0.85)'); r.addColorStop(0.45, 'rgba(255,255,255,0.22)'); r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function sprite(mat, size) { const s = new THREE.Sprite(mat.clone()); s.scale.set(size, size, 1); s.userData.size = size; return s; }
function part(g, mat, sx, sy, sz, x, y, z) { const m = new THREE.Mesh(g, mat); m.scale.set(sx, sy, sz); m.position.set(x, y, z); return m; }
const lam = hex => new THREE.MeshLambertMaterial({ color: hex });
const CAR_COLOURS = [0x9a1f1f, 0x2b4f86, 0xcfd3d6, 0x262626, 0x6e7378];

// A car facing -z (forwards), its middle at the origin on the ground.
function carMesh(colour, mine) {
  const { geo, mats } = V3, g = new THREE.Group(), body = lam(colour);
  g.add(part(geo.box, body, 1.8, 0.62, 4.4, 0, 0.55, 0));
  g.add(part(geo.box, mats.glass, 1.56, 0.5, 2.1, 0, 1.1, 0.25));
  g.add(part(geo.box, body, 1.6, 0.06, 2.0, 0, 1.38, 0.25));
  for (const [x, z] of [[-0.82, -1.4], [0.82, -1.4], [-0.82, 1.4], [0.82, 1.4]]) g.add(part(geo.wheel, mats.tyre, 0.32, 0.22, 0.32, x, 0.32, z));
  for (const x of [-0.62, 0.62]) { g.add(part(geo.box, mats.lampW, 0.36, 0.14, 0.05, x, 0.68, -2.21)); g.add(part(geo.box, mats.lampR, 0.34, 0.12, 0.05, x, 0.72, 2.21)); }
  const f = [], r = [];
  for (const x of [-0.62, 0.62]) {
    const a = sprite(mats.glowW, 0.9); a.position.set(x, 0.68, -2.35); g.add(a); f.push(a);
    const b = sprite(mats.glowR, mine ? 0.55 : 0.75); b.position.set(x, 0.72, 2.3); g.add(b); r.push(b);
  }
  g.userData = { front: f, rear: r };
  if (mine) {
    f.forEach(s => s.visible = false);   // the player's own beam is the spot light
    // v14 (#440): the blinkers, front and back at each corner, orange: [left, right].
    g.userData.blink = [-1, 1].map(side => [-2.3, 2.3].map(z => { const o = sprite(V3.mats.glowO, 0.8); o.position.set(side * 0.86, 0.72, z); o.visible = false; g.add(o); return o; }));
  }
  return g;
}
function truckMesh() {
  const { geo, mats } = V3, g = new THREE.Group();
  g.add(part(geo.box, lam(0x9b2a22), 2.5, 2.6, 2.4, 0, 1.9, -7.2));
  g.add(part(geo.box, mats.glass, 2.3, 0.9, 0.08, 0, 2.6, -8.42));
  g.add(part(geo.box, lam(0xd9dde2), 2.55, 3.1, 13.4, 0, 2.3, 1.0));
  for (const z of [-7.6, -2, 0.5, 5.5, 7]) for (const x of [-1.15, 1.15]) g.add(part(geo.wheel, mats.tyre, 0.52, 0.32, 0.52, x, 0.52, z));
  const f = [], r = [], side = [];
  for (const x of [-0.95, 0.95]) {
    const a = sprite(mats.glowW, 1.1); a.position.set(x, 0.9, -8.5); g.add(a); f.push(a);
    const b = sprite(mats.glowR, 0.8); b.position.set(x, 0.9, 7.75); g.add(b); r.push(b);
  }
  for (let z = -5; z <= 7; z += 3) for (const x of [-1.32, 1.32]) { const o = sprite(mats.glowO, 0.35); o.position.set(x, 0.85, z); g.add(o); side.push(o); }
  for (const x of [-1.1, -0.4, 0.4, 1.1]) { const o = sprite(mats.glowO, 0.3); o.position.set(x, 3.95, -8.3); g.add(o); side.push(o); }
  g.userData = { front: f, rear: r };
  return g;
}
function tractorMesh() {
  const { geo, mats } = V3, g = new THREE.Group(), red = lam(0xa8241d);
  g.add(part(geo.box, red, 1.3, 1.0, 2.6, 0, 1.2, -1.6));
  g.add(part(geo.box, mats.glass, 1.6, 1.3, 1.5, 0, 2.2, 0.1));
  g.add(part(geo.box, red, 1.7, 0.1, 1.7, 0, 2.9, 0.1));
  g.add(part(geo.wheel, mats.tyre, 0.8, 0.5, 0.8, -1.0, 0.8, 0.3)); g.add(part(geo.wheel, mats.tyre, 0.8, 0.5, 0.8, 1.0, 0.8, 0.3));
  g.add(part(geo.wheel, mats.tyre, 0.48, 0.32, 0.48, -0.85, 0.48, -2.4)); g.add(part(geo.wheel, mats.tyre, 0.48, 0.32, 0.48, 0.85, 0.48, -2.4));
  // A trailer of firewood behind.
  g.add(part(geo.box, lam(0x5b4630), 2.3, 1.1, 3.6, 0, 1.25, 2.9));
  g.add(part(geo.wheel, mats.tyre, 0.45, 0.3, 0.45, -1.05, 0.45, 3.0)); g.add(part(geo.wheel, mats.tyre, 0.45, 0.3, 0.45, 1.05, 0.45, 3.0));
  // The slow-vehicle triangle at the back: orange, reflective.
  const tri = new THREE.Mesh(new THREE.CircleGeometry(0.42, 3).rotateZ(Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff6a1a }));
  tri.position.set(0, 1.2, 4.72); g.add(tri);
  const r = [], f = [];
  for (const x of [-0.95, 0.95]) { const b = sprite(mats.glowR, 0.55); b.position.set(x, 0.9, 4.75); g.add(b); r.push(b); }
  for (const x of [-0.5, 0.5]) { const a = sprite(mats.glowW, 0.7); a.position.set(x, 1.3, -2.95); g.add(a); f.push(a); }
  const beacon = sprite(mats.glowO, 1.6); beacon.position.set(0, 3.15, 0.1); g.add(beacon);
  g.userData = { front: f, rear: r, beacon, tri };
  return g;
}
// v12 (#440): a Finnish police car: white, a blue and yellow chequered band down each side, and
// a light bar on the roof whose blue lamps flash when its `blue` is on.
function policeMesh() {
  const { geo, mats } = V3, g = carMesh(0xeef1f4), blue = lam(0x1f4fb8), yellow = lam(0xe8c21c);
  for (const x of [-0.91, 0.91]) for (let k = 0; k < 8; k++) g.add(part(geo.box, k % 2 ? yellow : blue, 0.04, 0.26, 0.5, x, 0.6, -1.75 + k * 0.5));
  g.add(part(geo.box, mats.dark, 1.2, 0.12, 0.3, 0, 1.47, 0.1));
  const lamps = [];
  for (const x of [-0.42, 0.42]) {
    g.add(part(geo.box, blue, 0.36, 0.13, 0.28, x, 1.49, 0.1));
    const b = sprite(mats.glowB, 1.4); b.position.set(x, 1.55, 0.1); b.visible = false; g.add(b); lamps.push(b);
  }
  g.userData.blue = lamps;
  return g;
}
// v13 (#440, tie.js): an ambulance: a yellow and white van, a light bar of blue lamps, a green
// and yellow chequered band.
function ambulanceMesh() {
  const { geo, mats } = V3, g = new THREE.Group(), white = lam(0xf2f0e6), yellow = lam(0xf0d020), green = lam(0x2c9a4a);
  g.add(part(geo.box, white, 2.1, 1.9, 4.2, 0, 1.45, 0.6));
  g.add(part(geo.box, yellow, 2.0, 0.9, 1.7, 0, 0.95, -2.3));
  g.add(part(geo.box, mats.glass, 1.8, 0.6, 0.9, 0, 1.75, -1.7));
  for (const x of [-1.06, 1.06]) for (let k = 0; k < 8; k++) g.add(part(geo.box, k % 2 ? yellow : green, 0.04, 0.3, 0.5, x, 1.0, -1.2 + k * 0.5));
  for (const [x, z] of [[-0.9, -2.2], [0.9, -2.2], [-0.9, 1.9], [0.9, 1.9]]) g.add(part(geo.wheel, mats.tyre, 0.36, 0.24, 0.36, x, 0.36, z));
  const f = [], r = [], lamps = [];
  for (const x of [-0.7, 0.7]) {
    const a = sprite(mats.glowW, 0.9); a.position.set(x, 0.8, -3.2); g.add(a); f.push(a);
    const b = sprite(mats.glowR, 0.7); b.position.set(x, 0.9, 2.75); g.add(b); r.push(b);
    for (const z of [-1.4, 2.6]) { const l = sprite(mats.glowB, 1.4); l.position.set(x, 2.5, z); l.visible = false; g.add(l); lamps.push(l); }
  }
  g.userData = { front: f, rear: r, blue: lamps };
  return g;
}
// A wide load: a low trailer behind a tractor unit, carrying a house half a lane wider than the
// lane, orange lamps along its sides and an orange beacon on the cab.
function loadMesh(t) {
  const { geo, mats } = V3, g = new THREE.Group(), wid = t.wid;
  g.add(part(geo.box, lam(0x2d6b3a), 2.5, 2.6, 2.4, 0, 1.9, -6.6));
  g.add(part(geo.box, mats.glass, 2.3, 0.9, 0.08, 0, 2.6, -7.82));
  g.add(part(geo.box, mats.dark, 2.5, 0.4, 11, 0, 0.9, 0.9));
  g.add(part(geo.box, lam(0xb8a07a), wid, 2.8, 9.5, 0, 2.6, 1.2));
  g.add(part(geo.box, lam(0x5a2a22), wid + 0.4, 0.3, 10, 0, 4.15, 1.2));
  g.add(part(geo.box, lam(0xf0d020), wid, 0.5, 0.06, 0, 1.4, -3.6));
  for (const z of [-6.8, -2, 4, 5.5]) for (const x of [-1.1, 1.1]) g.add(part(geo.wheel, mats.tyre, 0.52, 0.32, 0.52, x, 0.52, z));
  const f = [], side = [];
  for (const x of [-0.95, 0.95]) { const a = sprite(mats.glowW, 1.1); a.position.set(x, 0.9, -7.9); g.add(a); f.push(a); }
  for (let z = -3.5; z <= 6; z += 2.4) for (const x of [-wid / 2, wid / 2]) { const o = sprite(mats.glowO, 0.5); o.position.set(x, 1.3, z); g.add(o); side.push(o); }
  const beacon = sprite(mats.glowO, 1.6); beacon.position.set(0, 3.4, -6.6); g.add(beacon);
  g.userData = { front: f, rear: [], beacon };
  return g;
}
// A snowplough: an orange lorry, a wide blade in front, two orange beacons on the cab.
function ploughMesh() {
  const { geo, mats } = V3, g = new THREE.Group(), orange = lam(0xe0761c);
  g.add(part(geo.box, orange, 2.5, 2.6, 2.4, 0, 1.9, -2.9));
  g.add(part(geo.box, mats.glass, 2.3, 0.9, 0.08, 0, 2.6, -4.12));
  g.add(part(geo.box, lam(0x6a6d72), 2.5, 1.6, 5.4, 0, 1.6, 1.4));
  g.add(part(geo.box, lam(0xd8dde2), 3.2, 1.0, 0.25, 0, 0.6, -4.7));
  for (const z of [-3, 1, 3]) for (const x of [-1.15, 1.15]) g.add(part(geo.wheel, mats.tyre, 0.52, 0.32, 0.52, x, 0.52, z));
  const f = [], r = [];
  for (const x of [-0.95, 0.95]) {
    const a = sprite(mats.glowW, 1.1); a.position.set(x, 1.2, -4.3); g.add(a); f.push(a);
    const b = sprite(mats.glowR, 0.8); b.position.set(x, 0.9, 4.15); g.add(b); r.push(b);
  }
  const beacon = sprite(mats.glowO, 1.6); beacon.position.set(-0.8, 3.35, -2.9); g.add(beacon);
  const beacon2 = sprite(mats.glowO, 1.6); beacon2.position.set(0.8, 3.35, -2.9); g.add(beacon2);
  g.userData = { front: f, rear: r, beacon, beacon2 };
  return g;
}
// The roadworks (tie.js): cones from the edge line in to the centre and along it, a light at
// each end, red and green; each light's lamps are switched every frame in draw3d.
function worksMesh(w) {
  const g = new THREE.Group(), cone = new THREE.ConeGeometry(0.2, 0.75, 10), orange = lam(0xff5a14), band = lam(0xe8e8e8);
  for (let s = w.s0 - TAPER + 4; s <= w.s1; s += s < w.s0 ? 4 : 7) {
    const p = worldAt(s, conesAt(w, s) + 0.2, 0.38);
    g.add(part(cone, orange, 1, 1, 1, p[0], p[1], p[2]));
    g.add(part(V3.geo.pole, band, 0.13, 0.08, 0.13, p[0], p[1] + 0.05, p[2]));
  }
  // A digger and a heap of gravel in the shut lane.
  const dp = worldAt(w.s0 + WORK_LEN * 0.5, 2.0, 0), dig = new THREE.Group();
  dig.add(part(V3.geo.box, lam(0xe8b41c), 2.2, 1.6, 3.2, 0, 1.4, 0), part(V3.geo.box, V3.mats.glass, 1.4, 1.0, 1.4, 0, 2.6, -0.3), part(V3.geo.box, lam(0xe8b41c), 0.3, 0.3, 3.4, -0.6, 2.0, -2.6));
  dig.position.set(...dp); dig.rotation.y = -headingAt(w.s0 + WORK_LEN * 0.5) + 0.6; g.add(dig);
  const hp = worldAt(w.s0 + WORK_LEN * 0.25, 2.2, 0);
  const heap = new THREE.Mesh(new THREE.ConeGeometry(1.6, 1.2, 12), lam(0x6e6458)); heap.position.set(hp[0], hp[1] + 0.6, hp[2]); g.add(heap);
  const lights = [];
  for (const [s, lat, mine] of [[w.stop, EDGE + 0.8, true], [w.far, -EDGE - 0.8, false]]) {
    const p = worldAt(s, lat, 0);
    g.add(part(V3.geo.pole, V3.mats.grey, 0.06, 2.6, 0.06, p[0], p[1] + 1.3, p[2]));
    const box = part(V3.geo.box, V3.mats.dark, 0.4, 1.0, 0.3, p[0], p[1] + 2.9, p[2]); box.rotation.y = -headingAt(s); g.add(box);
    const red = sprite(V3.mats.glowR, 1.3), green = sprite(V3.mats.glowGreen, 1.3);
    red.position.set(p[0], p[1] + 3.2, p[2]); green.position.set(p[0], p[1] + 2.65, p[2]); g.add(red, green);
    lights.push({ red, green, mine });
  }
  g.userData = { w, lights };
  return g;
}
// The broken-down car's warning triangle, a red reflecting frame on the road's edge.
function triangleMesh(b) {
  const g = new THREE.Group(), p = worldAt(b.s - TRIANGLE, BROKEN_LAT + 0.4, 0);
  const tri = new THREE.Mesh(new THREE.RingGeometry(0.22, 0.34, 3).rotateZ(Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0xff2a1a, side: THREE.DoubleSide }));
  tri.position.set(p[0], p[1] + 0.32, p[2]); tri.rotation.y = -headingAt(b.s - TRIANGLE); g.add(tri);
  g.userData = { s: b.s - TRIANGLE, lat: BROKEN_LAT + 0.4, tri };
  return g;
}
// Black ice: a dark, glossy patch across the road that the headlights catch.
function iceMesh(x) {
  const pts = [], idx = [];
  for (let s = x.s0, i = 0; s <= x.s1; s += 2, i++) {
    for (const lat of [-EDGE, EDGE]) { const p = worldAt(s, lat, groundAt(s, lat, false) + 0.02); pts.push(...p); }
    if (i) idx.push(2 * i - 2, 2 * i - 1, 2 * i, 2 * i - 1, 2 * i + 1, 2 * i);
  }
  const geom = new THREE.BufferGeometry(); geom.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3)); geom.setIndex(idx); geom.computeVertexNormals();
  return new THREE.Mesh(geom, new THREE.MeshPhongMaterial({ color: 0x1a2430, specular: 0xd8ecff, shininess: 90, transparent: true, opacity: 0.85, side: THREE.DoubleSide }));
}
// The officer at a police check: a dark uniform with a yellow vest, and a red baton light.
function officerMesh() {
  const { geo, mats } = V3, g = walkerMesh({ reflector: true });
  g.add(part(geo.pole, lam(0xd9e23a), 0.235, 0.36, 0.235, 0, 1.25, 0));
  g.add(part(geo.ball, lam(0x1b2433), 0.14, 0.06, 0.14, 0, 1.78, 0));
  const beacon = sprite(mats.glowR, 0.7); beacon.position.set(-0.32, 1.25, -0.1); g.add(beacon);
  g.userData.beacon = beacon;
  return g;
}
// The police check's cones along the edge line, white bands catching the headlights.
function checkCones(c) {
  const g = new THREE.Group(), cone = new THREE.ConeGeometry(0.18, 0.7, 10), orange = lam(0xff5a14), band = lam(0xe8e8e8);
  for (let s = c.s - 70; s <= c.s - 6; s += 8) {
    const p = worldAt(s, EDGE - 0.15, 0.36);
    g.add(part(cone, orange, 1, 1, 1, p[0], p[1], p[2]));
    g.add(part(V3.geo.pole, band, 0.12, 0.08, 0.12, p[0], p[1] + 0.05, p[2]));
  }
  return g;
}
function walkerMesh(t) {
  const { geo, mats } = V3, g = new THREE.Group(), coat = lam(t.reflector ? 0x56606e : 0x4a4640);
  g.add(part(geo.pole, coat, 0.22, 0.75, 0.22, 0, 1.12, 0));
  g.add(part(geo.ball, lam(0xd9b59a), 0.12, 0.13, 0.12, 0, 1.64, 0));
  g.add(part(geo.ball, lam(0x30343a), 0.13, 0.08, 0.13, 0, 1.74, 0));
  const legs = [part(geo.pole, lam(0x34404f), 0.07, 0.75, 0.07, -0.09, 0.38, 0), part(geo.pole, lam(0x34404f), 0.07, 0.75, 0.07, 0.09, 0.38, 0)];
  legs.forEach(l => g.add(l));
  let refl = null;
  if (t.reflector) { refl = sprite(mats.glowW, 0.32); refl.position.set(0.18, 0.95, 0); g.add(refl); }
  g.userData = { legs, refl };
  return g;
}
function deerMesh(poro) {
  const { geo, mats } = V3, g = new THREE.Group(), fur = lam(poro ? 0x8d8a82 : 0x3b2a1e), dark = lam(poro ? 0x5d584f : 0x24190f);
  const k = poro ? 0.62 : 1;
  g.add(part(geo.box, fur, 0.75 * k, 0.95 * k, 2.3 * k, 0, 1.75 * k, 0));
  g.add(part(geo.box, fur, 0.65 * k, 0.6 * k, 0.6 * k, 0, 2.15 * k, -1.15 * k));          // the hump and shoulders
  g.add(part(geo.box, fur, 0.32 * k, 0.4 * k, 0.9 * k, 0, 2.2 * k, -1.55 * k));            // neck
  g.add(part(geo.box, dark, 0.34 * k, 0.4 * k, 0.75 * k, 0, 2.25 * k, -2.05 * k));         // head
  for (const x of [-0.25, 0.25]) for (const z of [-0.85, 0.85]) g.add(part(geo.box, dark, 0.14 * k, 1.35 * k, 0.14 * k, x * k, 0.67 * k, z * k));
  // Antlers: a bull moose's broad palms, a reindeer's tall branches.
  const horn = lam(poro ? 0xbfae94 : 0x8a7457);
  for (const x of [-1, 1]) {
    if (poro) { g.add(part(geo.box, horn, 0.05, 0.7, 0.05, x * 0.18, 2.75 * k + 0.2, -1.9 * k)); g.add(part(geo.box, horn, 0.05, 0.05, 0.4, x * 0.2, 2.75 * k + 0.4, -1.75 * k)); }
    else g.add(part(geo.box, horn, 0.75, 0.08, 0.38, x * 0.48, 2.5, -1.95));
  }
  const eyes = [];
  for (const x of [-0.14, 0.14]) { const e = sprite(V3.mats.glowY, 0.16); e.position.set(x * k, 2.33 * k, -2.42 * k); g.add(e); eyes.push(e); }
  g.userData = { eyes };
  return g;
}

// Frees what a removed world or vehicle made for itself on the GPU: its own geometries,
// materials and textures, but never the shared shapes, materials and the glow picture.
function dispose(root) {
  const geos = new Set(Object.values(V3.geo)), mats = new Set(Object.values(V3.mats));
  root.traverse(o => {
    if (o.geometry && !geos.has(o.geometry)) o.geometry.dispose();
    for (const m of [].concat(o.material || [])) {
      if (mats.has(m)) continue;
      if (m.map && m.map !== V3.glow) m.map.dispose();
      m.dispose();
    }
  });
}

// ---- Building a leg's world: the road, the forest, signs ----
function buildWorld() {
  const old = V3.world;
  if (old) { V3.scene.remove(old); dispose(old); }
  for (const m of V3.meshes.values()) { V3.scene.remove(m); dispose(m); }
  V3.meshes.clear();
  const w = new THREE.Group(); V3.world = w; V3.built = road; V3.scene.add(w);
  const wx = leg.weather, snowy = wx === 'lumi' || wx === 'pyry', wet = wx === 'sade';
  // The night: overcast or clear, the fog closing in faster in snow and rain.
  const sky = snowy ? 0x0b0f16 : wet ? 0x06080c : 0x04060c;
  V3.scene.background = new THREE.Color(sky);
  V3.scene.fog = new THREE.Fog(sky, 25, wx === 'pyry' ? 160 : snowy ? 230 : wet ? 300 : 420);
  V3.fogBase = { far: V3.scene.fog.far, colour: new THREE.Color(sky) };
  V3.moon.intensity = snowy ? 1.1 : 0.55;
  w.add(groundMesh(snowy, wet));
  // v14 (#440): the road straight on at each turn, and a crossroads' crossing road.
  for (const J of road.turns || []) for (const a of J.arms) w.add(armMesh(J, a, snowy, wet, wx === 'pyry'));
  // v8: in a blizzard too, where only the junctions' no-overtaking lines show (v1–v7: no lines at all).
  w.add(markings(snowy, wx === 'pyry'));
  w.add(trees(snowy));
  w.add(posts(snowy));
  V3.signs = road.signs.map(signMesh); V3.signs.forEach(m => w.add(m));
  V3.camMeshes = road.cams.map(c => cameraMesh(c)); V3.camMeshes.forEach(m => w.add(m));
  // v7 (#266): each pothole lies on the road's surface, with a pale rim of broken asphalt that the
  // headlights catch. v1–v6 drew a black disc at a flat 3 cm, under the crowned road for every
  // hole within 1.25 m of the centre line, so those were not seen at all.
  const holeMat = new THREE.MeshLambertMaterial({ color: snowy ? 0x3a3e45 : 0x050506 });
  const rimMat = new THREE.MeshLambertMaterial({ color: snowy ? 0x9aa1aa : 0xb4b6ba, emissive: snowy ? 0x000000 : 0x1c1c1e });
  for (const h of road.holes) {
    const p = worldAt(h.s, h.lat, groundAt(h.s, h.lat, false) + 0.012);
    const rim = new THREE.Mesh(new THREE.RingGeometry(h.r, h.r + 0.22, 14).rotateX(-Math.PI / 2), rimMat);
    rim.position.set(p[0], p[1] + 0.004, p[2]); w.add(rim);
    const m = new THREE.Mesh(new THREE.CircleGeometry(h.r, 12).rotateX(-Math.PI / 2), holeMat);
    m.position.set(...p); w.add(m);
  }
  for (const b of road.bays) w.add(restStop(b, snowy));
  for (const J of road.junctions) w.add(junctionLamp(J));
  for (const c of road.checks) w.add(checkCones(c));
  // v13 (#440): the road events' fixed parts.
  V3.works = road.works.map(worksMesh); V3.works.forEach(m => w.add(m));
  V3.triangles = road.broken.map(triangleMesh); V3.triangles.forEach(m => w.add(m));
  for (const x of road.ice) w.add(iceMesh(x));
  // v14: the level crossings.
  V3.rails = road.rail.map(railMesh); V3.rails.forEach(m => w.add(m));
  w.add(townLights());
  if (wx !== 'kuiva') w.add(V3.weather = weatherMesh(wx));
  else { V3.weather = null; w.add(starField()); }
}

// v14 (#440): the roads at a turn (risteys.js). A road from one end of a drawn line to the other:
// asphalt, gravel shoulders, edge lines and a dashed yellow middle, left out where it lies on the
// route itself.
function armMesh(J, [x0, z0, x1, z1], snowy, wet, buried) {
  const pos = [], col = [], C = hex => new THREE.Color(hex), len = Math.hypot(x1 - x0, z1 - z0);
  const fx = (x1 - x0) / len, fz = (z1 - z0) / len, rx = -fz, rz = fx, y = J.y;
  const asphalt = C(snowy ? '#7c838d' : wet ? '#1b1c1f' : '#2c2d30'), gravel = C(snowy ? '#b9c2cc' : '#4a443b'), white = C('#e8e8e2'), yellow = C('#e7b723');
  const quad = (a0, a1, l0, l1, up, c) => {
    const P4 = [[a0, l0], [a0, l1], [a1, l0], [a1, l1]].map(([a, l]) => [x0 + fx * a + rx * l, y + up, z0 + fz * a + rz * l]);
    pos.push(...P4[0], ...P4[1], ...P4[2], ...P4[1], ...P4[3], ...P4[2]);   // facing up
    for (let k = 0; k < 6; k++) col.push(c.r, c.g, c.b);
  };
  for (let a = 0; a < len; a += 4) {
    const b = Math.min(len, a + 4), mx = x0 + fx * (a + 2), mz = z0 + fz * (a + 2);
    const onRoute = routeNear(mx, mz, null, 3.2);
    quad(a, b, -EDGE - 1.1, EDGE + 1.1, -0.01, gravel);
    quad(a, b, -EDGE, EDGE, 0.02, asphalt);
    if (onRoute || buried) continue;
    if (!snowy) for (const l of [-EDGE + 0.1, EDGE - 0.1]) quad(a, b, l - 0.06, l + 0.06, 0.05, white);
    if (!snowy && a % 12 < 4) quad(a, a + 3, -0.06, 0.06, 0.05, yellow);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.computeVertexNormals();
  return new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 }));
}
// Whether a point is within d metres of the route's middle, away from route place s (null: anywhere
// near a turn). Only near turns, where the route comes round.
function routeNear(x, z, s, d) {
  for (const J of road.turns || []) {
    if (s !== null && (s < J.a0 - 260 || s > J.a1 + 260)) continue;
    for (let q = J.a0 - 200; q <= J.a1 + 200; q += 2) {
      if (s !== null && Math.abs(q - s) < 30) continue;
      const p = worldAt(q, 0); if (Math.hypot(p[0] - x, p[2] - z) < d + EDGE) return true;
    }
  }
  return false;
}
// The flat field round a turn: { y, w } (w = 1 within 24 m of its roads, none past 44), or null.
function turnFlat(x, z) {
  for (const J of road.turns || []) {
    if (Math.hypot(x - J.x, z - J.z) > ARM_LEN + 120) continue;
    const d = armDist(x, z);
    if (d < 44) return { y: J.y, w: clamp((44 - d) / 20, 0, 1) };
  }
  return null;
}
// A ground column at a turn: on the inside of its bend no wider than its radius (else the rows fold
// over the middle), widening again with the distance from the bend.
function turnCol(s, lat) {
  for (const J of road.turns || []) {
    const d = s < J.a0 ? J.a0 - s : s > J.a1 ? s - J.a1 : 0;
    if (d < 80 && lat * J.dir > 0) return Math.sign(lat) * Math.min(Math.abs(lat), Math.max(J.R * 0.85, d));
  }
  return lat;
}

// v14: how level the ground is for a railway across the road here, 0..1.
function railFlat(s) { let w = 0; for (const x of road.rail) w = Math.max(w, clamp((16 - Math.abs(s - x.s)) / 6, 0, 1)); return w; }
// A level crossing: the railway across the road, St Andrew's crosses with their red lights, a
// barrier on each side over the lane coming in, and the train. Drawn in the crossing's own frame:
// x across the road (as lat), z along it (towards the start).
function railMesh(x) {
  const g = new THREE.Group(), { geo, mats } = V3, p = worldAt(x.s, 0), far = RAIL_FROM + RAIL_TRAIN_LEN + 20;
  g.position.set(...p); g.rotation.y = -headingAt(x.s);
  const steel = new THREE.MeshLambertMaterial({ color: 0x9aa0a8, emissive: 0x15171a }), stone = lam(0x55524c), wood = lam(0x3a2a1c);
  for (const side of [-1, 1]) g.add(part(geo.box, stone, far - 4.6, 0.3, 3.2, side * (far + 4.6) / 2, -0.05, 0));
  g.add(part(geo.box, lam(0x25262a), 9.4, 0.06, 2.6, 0, 0.04, 0));
  for (const z of [-0.72, 0.72]) g.add(part(geo.box, steel, far * 2, 0.12, 0.08, 0, 0.14, z));
  const n = Math.floor((far - 5) / 0.9) * 2, sl = new THREE.InstancedMesh(geo.box, wood, n), m = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(0.24, 0.1, 2.4);
  let i = 0;
  for (let a = 5; a < far && i < n; a += 0.9) for (const side of [-1, 1]) if (i < n) m.compose(new THREE.Vector3(side * a, 0.06, 0), q, sc), sl.setMatrixAt(i++, m);
  g.add(sl);
  // A cross and a barrier on each side: right of the road before the rails for the player, left of
  // it past the rails for the oncoming. The barrier turns about its post, up at 1.45 rad.
  const lamps = [], bars = [], white = new THREE.MeshLambertMaterial({ color: 0xf2f2ee, emissive: 0x202020 }), red = lam(0xd42a1e);
  for (const side of [1, -1]) {
    const z = side * 5, cx = side * 5.8, face = side > 0 ? 0 : Math.PI;
    const cross = new THREE.Group(); cross.position.set(cx, 0, z); cross.rotation.y = face; g.add(cross);
    cross.add(part(geo.pole, mats.grey, 0.05, 3.0, 0.05, 0, 1.5, 0));
    for (const r of [0.6, -0.6]) { const b = part(geo.box, side > 0 ? white : white, 1.5, 0.2, 0.04, 0, 2.75, -0.06); b.rotation.z = r; cross.add(b); const e = part(geo.box, red, 1.52, 0.06, 0.05, 0, 2.75, -0.07); e.rotation.z = r; cross.add(e); }
    for (const lx of [-0.3, 0.3]) { const l = sprite(mats.glowR, 0.9); l.position.set(lx, 2.05, -0.12); l.visible = false; cross.add(l); lamps.push(l); }
    const piv = new THREE.Group(); piv.position.set(side * 5.0, 1.0, z + side * 0.6); g.add(piv);
    g.add(part(geo.box, mats.grey, 0.25, 1.1, 0.25, side * 5.0, 0.55, z + side * 0.6));
    for (let k = 0; k < 4; k++) piv.add(part(geo.box, k % 2 ? red : white, 1.0, 0.1, 0.08, -side * (0.5 + k), 0, 0));
    const bl = sprite(mats.glowR, 0.4); bl.position.set(-side * 3.8, 0.1, 0); piv.add(bl);
    piv.userData.side = side; bars.push(piv);
  }
  // The train: a locomotive and four cars, RAIL_TRAIN_LEN metres, lit windows, a headlight.
  const train = new THREE.Group(), carLen = RAIL_TRAIN_LEN / 5, win = new THREE.MeshBasicMaterial({ color: 0xffd98a });
  for (let k = 0; k < 5; k++) {
    const c = new THREE.Group(); c.position.x = -(k + 0.5) * carLen;
    c.add(part(geo.box, lam(k ? 0x3c5a8a : 0xb8262a), carLen - 0.8, 3.4, 3.1, 0, 2.3, 0));
    c.add(part(geo.box, lam(0x1a1a1a), carLen - 4, 0.6, 2.6, 0, 0.5, 0));
    if (k) for (const z of [-1.56, 1.56]) c.add(part(geo.box, win, carLen - 3, 0.7, 0.04, 0, 2.8, z));
    train.add(c);
  }
  const head = sprite(mats.glowW, 4); head.position.set(0.3, 2.0, 0); train.add(head);
  train.visible = false; g.add(train);
  g.userData = { x, lamps, bars, train };
  return g;
}
// The crossing as it is now (from draw3d).
function railFrame(g, time) {
  const { x, lamps, bars, train } = g.userData, b = railBarrier(x), on = (time % 1.1) < 0.55;
  lamps.forEach((l, i) => { l.visible = x.on && (i % 2 ? on : !on); });
  bars.forEach(p => { p.rotation.z = -p.userData.side * (1 - b) * 1.45; });
  const h = railTrain(x);
  train.visible = h !== null && h < RAIL_FROM + RAIL_TRAIN_LEN;
  if (train.visible) { train.position.x = x.dir * h; train.rotation.y = x.dir > 0 ? 0 : Math.PI; }
}

// The ground across the road: the road (slightly crowned), gravel shoulders, ditches, then the
// forest floor rising away. One mesh, coloured by vertex.
// v8 (#306): a column at the rest area's outer edge (11.5), so its paving ends there.
const COLS = [-70, -36, -18, -10, -7.4, -6.2, -5.6, -4.6, -3.5, -1.75, 0, 1.75, 3.5, 4.6, 5.6, 6.2, 7.4, 10, 11.5, 18, 36, 70];
// The side roads a row of the ground crosses (v8, #306): -1 left, 1 right.
function sideRoads(s) {
  const out = [];
  for (const J of road.junctions) if (Math.abs(s - J.s) <= 4.5) { out.push(J.side); if (J.both) out.push(-J.side); }
  return out;
}
// bay: how wide the rest area's paving is here beyond the edge line (v8; v1–v7 true or false);
// sides: the side roads here, flat and paved out to the forest.
function paved(lat, bay, sides) { const a = Math.abs(lat); return a > 3.5 && ((bay && lat > 0 && lat <= 3.5 + bay + 0.01) || (sides && sides.includes(Math.sign(lat)))); }
function groundAt(s, lat, bay, sides) {
  const a = Math.abs(lat);
  if (paved(lat, bay, sides)) return 0;
  if (a <= 3.5) return 0.04 - a * 0.008;
  if (a <= 4.6) return -0.03;
  if (a <= 5.6) return -0.45;
  if (a <= 6.2) return -0.85;
  if (a <= 7.4) return -0.35;
  return (a - 7.4) * 0.08 + Math.sin(s * 0.013 + lat * 0.07) * Math.min(1, (a - 7.4) / 10) * 1.5;
}
function groundMesh(snowy, wet) {
  const rows = Math.ceil(road.total / 4), n = COLS.length, pos = new Float32Array((rows + 1) * n * 3), col = new Float32Array((rows + 1) * n * 3), ix = [];
  const C = hex => new THREE.Color(hex);
  const asphalt = C(snowy ? '#7c838d' : wet ? '#1b1c1f' : '#2c2d30'), rut = C(snowy ? '#3b3f45' : wet ? '#141517' : '#262729');
  const gravel = C(snowy ? '#b9c2cc' : '#4a443b'), ditch = C(snowy ? '#c7d0da' : '#23281d'), forest = C(snowy ? '#d4dce6' : '#1d2318');
  const t = new THREE.Color();
  for (let r = 0; r <= rows; r++) {
    const s = r * 4, bay = bayWidth(s), sides = sideRoads(s);
    for (let j = 0; j < n; j++) {
      const lat = turnCol(s, COLS[j]), p = worldAt(s, lat), o = (r * n + j) * 3, a = Math.abs(lat);
      p[1] += groundAt(s, lat, bay, sides);
      // v14: flat fields round a turn, level with the roads that meet there.
      const fl = turnFlat(p[0], p[2]);
      if (fl && a > 4.6) p[1] = lerp(p[1], fl.y - 0.12, fl.w);
      // ...and level along a railway.
      const rf = railFlat(s);
      if (rf && a > 4.6) p[1] = lerp(p[1], p[1] - groundAt(s, lat, bay, sides) - 0.12, rf);
      pos[o] = p[0]; pos[o + 1] = p[1]; pos[o + 2] = p[2];
      if (a === 1.75) t.copy(rut);                               // wheel tracks worn darker
      else if (a <= 3.5 || paved(lat, bay, sides)) t.copy(asphalt);
      else if (a <= 4.6) t.copy(gravel);
      else if (a <= 7.4) t.copy(ditch);
      else t.copy(forest);
      col[o] = t.r; col[o + 1] = t.g; col[o + 2] = t.b;
      if (r < rows && j < n - 1) { const q = r * n + j; ix.push(q, q + 1, q + n, q + 1, q + n + 1, q + n); }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.setIndex(ix); g.computeVertexNormals();
  return new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true }));
}
// Painted lines: white edges, a yellow dashed middle (Finnish roads part the two directions in
// yellow). Under snow only the edges show here and there; in a blizzard (buried) only the
// junctions' solid lines, here and there.
function markings(snowy, buried) {
  const pos = [], col = [], white = new THREE.Color('#e8e8e2'), yellow = new THREE.Color('#e7b723');
  function strip(s0, s1, lat, w, c) {
    for (let s = s0; s < s1; s += 4) {
      const e = Math.min(s + 4, s1), a = worldAt(s, lat - w / 2, 0.06), b = worldAt(s, lat + w / 2, 0.06), d = worldAt(e, lat - w / 2, 0.06), f = worldAt(e, lat + w / 2, 0.06);
      pos.push(...a, ...b, ...d, ...b, ...f, ...d);
      for (let k = 0; k < 6; k++) col.push(c.r, c.g, c.b);
    }
  }
  // A line across the road, from lat0 to lat1, w long (the rest area's parking places).
  function bar(s, lat0, lat1, w, c) {
    const a = worldAt(s, lat0, 0.06), b = worldAt(s, lat1, 0.06), d = worldAt(s + w, lat0, 0.06), f = worldAt(s + w, lat1, 0.06);
    pos.push(...a, ...b, ...d, ...b, ...f, ...d);
    for (let k = 0; k < 6; k++) col.push(c.r, c.g, c.b);
  }
  // v8 (#306): no edge line across a side road's mouth or along the rest area's lane; there the
  // lane is parted from the road by a dashed line, and the paving has its own edge line.
  // v14: none where the road straight on or a crossing road leaves it either.
  const open = (s, side) => road.junctions.some(J => Math.abs(s + 6 - J.s) < 9 && (J.side === side || J.both)) || (side > 0 && bayWidth(s + 6) > 0) ||
    ((road.turns || []).some(J => s > J.a0 - 30 && s < J.a1 + 30) && [0, 4, 8, 12].some(d => { const q = worldAt(s + d, side * EDGE); return armDist(q[0], q[2]) < EDGE + 0.6; }));
  const r = rng(5);
  for (let s = 0; s < road.total; s += 12) {
    if (buried) { if (noPass(s + 6) && r() < 0.6) strip(s, s + 12, 0, 0.14, yellow); continue; }
    if (!snowy || r() < 0.3) for (const side of [-1, 1]) {
      if (!open(s, side)) strip(s, s + 12, side * (EDGE - 0.1), 0.12, white);
      else if (side > 0 && bayWidth(s + 6) > 0) strip(s, s + 4, EDGE - 0.1, 0.12, white);
    }
    // The centre line: dashed, solid through a junction (no overtaking there, v8).
    if (!snowy) strip(s, s + (noPass(s + 6) ? 12 : 3), 0, 0.12, yellow);
    else if (noPass(s + 6) && r() < 0.5) strip(s, s + 12, 0, 0.12, yellow);
  }
  for (const b of buried ? [] : road.bays) {
    for (let s = b.s0 - BAY_IN; s < b.s1 + BAY_IN; s += 2) strip(s, s + 2, EDGE + bayWidth(s + 1) - 0.25, 0.12, white);
    for (let s = b.s0 + 6; s < b.s1 - 6; s += 3.2) bar(s, 8.3, 11.2, 0.12, white);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true, emissive: 0x111111 }));
  m.userData.markings = true;
  return m;
}
// Inside a turn's corner, where the camera looks across while the car turns: open ground (v14).
function inCorner(x, z) {
  return road.turns.some(J => { const c = worldAt(J.a0, J.dir * J.R); return Math.hypot(x - c[0], z - c[2]) < J.R + 6; });
}
// Spruces, a few thousand, one draw.
function trees(snowy) {
  const r = rng(9), spots = [];
  for (let s = -40; s < road.total; s += 3.2) for (const side of [-1, 1]) {
    if (r() < 0.25) continue;
    const near = 10 + Math.pow(r(), 1.6) * 55;
    if (side > 0 && road.bays.some(b => s > b.s0 - 40 && s < b.s1 + 40) && near < 22) continue;
    if (s > road.len - 380 && near < 24) continue;                   // the town at the end
    if (road.junctions.some(J => Math.abs(s - J.s) < 10 && (J.side === side || J.both))) continue;   // a side road (v8)
    // v14: none on the roads at a turn, nor on the route where it comes back past itself.
    if (road.rail.some(x => Math.abs(s - x.s) < 9)) continue;   // v14: the railway
    if (road.turns && road.turns.length) { const q = worldAt(s, side * near); if (armDist(q[0], q[2]) < 10 || routeNear(q[0], q[2], s, 9) || inCorner(q[0], q[2])) continue; }
    spots.push([s, side * near, 0.7 + r() * 0.8, r() * TAU]);
  }
  const parts = [], g1 = new THREE.CylinderGeometry(0.12, 0.16, 1.4, 5).translate(0, 0.7, 0);
  parts.push([g1, '#2a1e14']);
  const green = snowy ? '#203628' : '#14261a';
  for (const [y, rad, h] of [[1.2, 1.9, 3.4], [2.8, 1.45, 3.0], [4.4, 0.95, 2.6]]) parts.push([new THREE.ConeGeometry(rad, h, 7).translate(0, y + h / 2, 0), green]);
  if (snowy) for (const [y, rad, h] of [[2.9, 1.2, 1.2], [4.5, 0.8, 1.0], [6.1, 0.42, 0.9]]) parts.push([new THREE.ConeGeometry(rad, h, 7).translate(0, y + h / 2, 0), '#e6edf3']);
  const mesh = new THREE.InstancedMesh(merge(parts), new THREE.MeshLambertMaterial({ vertexColors: true }), spots.length);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);
  spots.forEach(([s, lat, k, a], i) => {
    const p = worldAt(s, lat); p[1] += groundAt(s, lat, false) - 0.1;
    m.compose(new THREE.Vector3(...p), q.setFromAxisAngle(up, a), new THREE.Vector3(k, k * (0.9 + (i % 5) * 0.08), k));
    mesh.setMatrixAt(i, m);
  });
  return mesh;
}
// Edge posts with reflectors every 50 m (and in winter the red and white snow poles between).
function posts(snowy) {
  const g = new THREE.Group(), list = [];
  for (let s = 20; s < road.total; s += snowy ? 25 : 50) for (const side of [-1, 1]) {
    // v8: none on the rest area's paving or in a side road's mouth.
    if (side > 0 && bayWidth(s) > 0 || road.junctions.some(J => Math.abs(s - J.s) < 8 && (J.side === side || J.both))) continue;
    // v14: none across the mouth of the road straight on or a crossing road.
    if (road.rail.some(x => Math.abs(s - x.s) < 6)) continue;
    if (road.turns && road.turns.length) { const q = worldAt(s, side * 5); if (armDist(q[0], q[2]) < 7 || routeNear(q[0], q[2], s, 6)) continue; }
    list.push([s, side]);
  }
  const pole = new THREE.InstancedMesh(V3.geo.box, new THREE.MeshLambertMaterial({ color: snowy ? 0xd8423a : 0xe6e6e0 }), list.length);
  const refl = new THREE.InstancedMesh(V3.geo.box, new THREE.MeshLambertMaterial({ color: 0xffffff, emissive: 0x222222 }), list.length);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);
  list.forEach(([s, side], i) => {
    const lat = side * 5.0, p = worldAt(s, lat), h = snowy ? 1.8 : 1.0;
    q.setFromAxisAngle(up, -headingAt(s));
    m.compose(new THREE.Vector3(p[0], p[1] + h / 2 - 0.4, p[2]), q, new THREE.Vector3(0.1, h, 0.1)); pole.setMatrixAt(i, m);
    m.compose(new THREE.Vector3(p[0], p[1] + 0.45, p[2]), q, new THREE.Vector3(0.13, 0.14, 0.13)); refl.setMatrixAt(i, m);
  });
  g.add(pole, refl);
  return g;
}
function merge(parts) {
  const geos = parts.map(([g, hex]) => {
    g = g.index ? g.toNonIndexed() : g; const c = new THREE.Color(hex), n = g.attributes.position.count, a = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { a[i * 3] = c.r; a[i * 3 + 1] = c.g; a[i * 3 + 2] = c.b; }
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

// ---- Signs: drawn once on a canvas each, bright when the headlights reach them ----
function signCanvas(sg) {
  const c = document.createElement('canvas'), wide = sg.kind === 'kamera' || sg.kind === 'levahdys' || sg.kind === 'kaupunki' || sg.kind === 'poliisi' || sg.kind === 'suunta';
  c.width = wide ? 256 : 128; c.height = 128;
  const g = c.getContext('2d');
  if (sg.kind === 'suunta') {
    // v14 (#440): a blue direction sign: the turn's way with an arrow, the road number in a red
    // box, and under it where the road straight on goes.
    g.fillStyle = '#1d55a8'; g.fillRect(0, 0, 256, 128); g.strokeStyle = '#fff'; g.lineWidth = 5; g.strokeRect(5, 5, 246, 118);
    g.fillStyle = '#fff'; g.strokeStyle = '#fff'; g.textBaseline = 'middle';
    const right = sg.dir > 0, ax = right ? 226 : 30;
    g.lineWidth = 7; g.lineCap = 'round'; g.beginPath();
    if (sg.ramp) { g.moveTo(ax - 10 * sg.dir, 58); g.lineTo(ax + 4 * sg.dir, 30); } else { g.moveTo(right ? ax - 20 : ax + 20, 44); g.lineTo(ax, 44); }
    g.stroke(); g.beginPath();
    if (sg.ramp) { g.moveTo(ax + 12 * sg.dir, 22); g.lineTo(ax - 6 * sg.dir, 24); g.lineTo(ax + 8 * sg.dir, 40); }
    else { g.moveTo(ax + 6 * sg.dir, 44); g.lineTo(ax - 8 * sg.dir, 32); g.lineTo(ax - 8 * sg.dir, 56); }
    g.closePath(); g.fill();
    g.font = 'bold 34px system-ui,sans-serif'; g.textAlign = right ? 'right' : 'left';
    const tx = right ? 186 : 70; g.fillText(sg.to, tx, 46);
    const nw = 30, nx = right ? 22 : 204;
    g.fillStyle = '#d42a1e'; g.fillRect(nx, 30, nw, 30); g.fillStyle = '#fff'; g.font = 'bold 24px system-ui,sans-serif'; g.textAlign = 'center'; g.fillText('4', nx + nw / 2, 46);
    g.font = 'bold 26px system-ui,sans-serif'; g.fillText(`↑ ${sg.on}`, 128, 94);
  } else if (sg.kind === 'tasoristeys') {
    // v14: a level crossing: the warning triangle with a gate.
    g.fillStyle = '#d42a1e'; g.beginPath(); g.moveTo(64, 4); g.lineTo(124, 118); g.lineTo(4, 118); g.closePath(); g.fill();
    g.fillStyle = '#f7c81b'; g.beginPath(); g.moveTo(64, 24); g.lineTo(110, 108); g.lineTo(18, 108); g.closePath(); g.fill();
    g.fillStyle = '#111'; g.fillRect(36, 70, 56, 8); g.fillRect(36, 84, 56, 8); g.fillRect(40, 66, 6, 36); g.fillRect(82, 66, 6, 36);
  } else if (sg.kind === 'poliisi') {
    // v12 (#440): before a police check, a portable sign: POLIISI over STOP.
    g.fillStyle = '#1d3f8f'; g.fillRect(0, 0, 256, 128); g.strokeStyle = '#f2d21a'; g.lineWidth = 8; g.strokeRect(6, 6, 244, 116);
    g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.font = 'bold 46px system-ui,sans-serif'; g.fillText('POLIISI', 128, 48);
    g.fillStyle = '#ff5a4a'; g.font = 'bold 34px system-ui,sans-serif'; g.fillText('STOP', 128, 94);
  } else if (sg.kind === 'pnuoli') {
    // v8 (#306): where the lane into the rest area begins: P and an arrow up and to the right.
    g.fillStyle = '#1d55a8'; g.fillRect(0, 0, 128, 128);
    g.strokeStyle = '#fff'; g.lineWidth = 6; g.strokeRect(5, 5, 118, 118);
    g.fillStyle = '#fff'; g.font = 'bold 64px system-ui,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('P', 44, 70);
    g.lineWidth = 10; g.lineCap = 'round'; g.beginPath(); g.moveTo(80, 100); g.lineTo(80, 60); g.quadraticCurveTo(80, 40, 100, 32); g.stroke();
    g.beginPath(); g.moveTo(88, 22); g.lineTo(112, 28); g.lineTo(98, 48); g.closePath(); g.fill();
  } else if (sg.kind === 'ohituskielto') {
    // v8 (#306): no overtaking: a red ring, a black car beside a red one.
    g.fillStyle = '#d42a1e'; g.beginPath(); g.arc(64, 64, 62, 0, TAU); g.fill();
    g.fillStyle = '#ffffff'; g.beginPath(); g.arc(64, 64, 48, 0, TAU); g.fill();
    for (const [x0, c] of [[32, '#d42a1e'], [68, '#111']]) {
      g.fillStyle = c; g.fillRect(x0, 50, 28, 26); g.fillRect(x0 + 4, 40, 20, 12);
      g.fillStyle = '#111'; g.fillRect(x0 + 2, 76, 7, 8); g.fillRect(x0 + 19, 76, 7, 8);
    }
  } else if (sg.kind === 'raja') {
    g.fillStyle = '#d42a1e'; g.beginPath(); g.arc(64, 64, 62, 0, TAU); g.fill();
    g.fillStyle = '#ffffff'; g.beginPath(); g.arc(64, 64, 46, 0, TAU); g.fill();
    g.fillStyle = '#111'; g.font = 'bold 50px system-ui,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(String(sg.v), 64, 68);
  } else if (sg.kind === 'kamera' || sg.kind === 'levahdys' || sg.kind === 'kaupunki') {
    g.fillStyle = sg.kind === 'kaupunki' ? '#ffffff' : '#1d55a8'; g.fillRect(0, 0, 256, 128);
    g.strokeStyle = sg.kind === 'kaupunki' ? '#111' : '#ffffff'; g.lineWidth = 6; g.strokeRect(5, 5, 246, 118);
    g.fillStyle = sg.kind === 'kaupunki' ? '#111' : '#ffffff'; g.textAlign = 'center'; g.textBaseline = 'middle';
    if (sg.kind === 'kamera') {
      g.fillRect(40, 44, 70, 42); g.fillRect(108, 56, 18, 18); g.beginPath(); g.arc(75, 65, 15, 0, TAU); g.fillStyle = '#1d55a8'; g.fill();
      g.fillStyle = '#fff'; g.font = 'bold 22px system-ui,sans-serif'; g.fillText('VALVONTA', 190, 64);
    } else if (sg.kind === 'levahdys') {
      g.font = 'bold 72px system-ui,sans-serif'; g.fillText('P', 60, 68);
      g.font = 'bold 26px system-ui,sans-serif'; g.fillText('☕ Kahvi', 170, 50); g.fillText(sg.text || '100 m', 170, 88);
    } else { g.font = `bold ${sg.text.length > 8 ? 34 : 42}px system-ui,sans-serif`; g.fillText(sg.text, 128, 66); }
  } else {
    // Finnish warning signs: a yellow triangle in a red border.
    g.fillStyle = '#d42a1e'; g.beginPath(); g.moveTo(64, 4); g.lineTo(124, 118); g.lineTo(4, 118); g.closePath(); g.fill();
    g.fillStyle = '#f7c81b'; g.beginPath(); g.moveTo(64, 24); g.lineTo(110, 108); g.lineTo(18, 108); g.closePath(); g.fill();
    g.fillStyle = '#111'; g.strokeStyle = '#111'; g.lineWidth = 4;
    if (sg.kind === 'hirvi' || sg.kind === 'poro') {
      g.fillRect(44, 72, 34, 14); g.fillRect(76, 62, 10, 16); g.fillRect(82, 58, 14, 8);
      for (const x of [46, 52, 70, 75]) g.fillRect(x, 84, 4, 18);
      g.fillRect(76, 50, 3, 10); g.fillRect(84, 50, 3, 10); g.fillRect(72, 48, 18, 3);
    } else if (sg.kind === 'kuoppa') {
      g.beginPath(); g.moveTo(26, 98); g.quadraticCurveTo(42, 78, 54, 98); g.quadraticCurveTo(66, 78, 78, 98); g.quadraticCurveTo(90, 78, 102, 98); g.stroke();
    } else if (sg.kind === 'risteys') {
      // v8 (#306): a junction with a side road: the main road a thick line up, the side road thin.
      g.fillRect(58, 46, 12, 58);
      if (sg.side <= 0) g.fillRect(36, 70, 24, 6);
      if (sg.side >= 0) g.fillRect(68, 70, 24, 6);
    } else if (sg.kind === 'tietyo') {
      // v13: road works: a worker with a shovel by a heap.
      g.beginPath(); g.arc(58, 52, 7, 0, TAU); g.fill();
      g.beginPath(); g.moveTo(56, 60); g.lineTo(50, 82); g.lineTo(42, 102); g.moveTo(50, 82); g.lineTo(60, 102); g.moveTo(54, 66); g.lineTo(70, 76); g.stroke();
      g.beginPath(); g.moveTo(66, 70); g.lineTo(82, 96); g.stroke();
      g.beginPath(); g.moveTo(76, 104); g.quadraticCurveTo(92, 82, 104, 104); g.closePath(); g.fill();
    } else if (sg.kind === 'liukas') {
      g.fillRect(50, 58, 28, 14); g.beginPath(); g.moveTo(40, 100); g.bezierCurveTo(54, 84, 60, 108, 72, 90); g.stroke();
      g.beginPath(); g.moveTo(68, 100); g.bezierCurveTo(80, 84, 86, 108, 96, 90); g.stroke();
    }
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function signMesh(sg) {
  const g = new THREE.Group(), wide = sg.kind === 'kamera' || sg.kind === 'levahdys' || sg.kind === 'kaupunki' || sg.kind === 'poliisi' || sg.kind === 'suunta';
  const mat = new THREE.MeshBasicMaterial({ map: signCanvas(sg), transparent: true, color: 0x111111 });
  const plate = new THREE.Mesh(V3.geo.plate, mat); plate.scale.set(wide ? 1.8 : 0.9, 0.9, 1); plate.position.y = 2.2;
  const post = part(V3.geo.pole, V3.mats.grey, 0.04, 2.2, 0.04, 0, 1.1, 0);
  g.add(plate, post);
  // v8: beside the rest area's paving, not on it.
  // v14: a direction sign for a left turn stands on the left.
  const lat = (sg.kind === 'suunta' && sg.dir < 0 ? -1 : 1) * Math.max(5.4, EDGE + bayWidth(sg.s) + 1.2), p = worldAt(sg.s, lat); g.position.set(...p); g.rotation.y = -headingAt(sg.s);
  g.userData = { s: sg.s, lat, mat };
  return g;
}
function cameraMesh(c) {
  const g = new THREE.Group(), p = worldAt(c.s, 6.0);
  g.add(part(V3.geo.pole, V3.mats.grey, 0.08, 3.4, 0.08, 0, 1.7, 0));
  g.add(part(V3.geo.box, lam(0x4a4f57), 0.45, 0.5, 0.8, 0, 3.4, 0));
  const f = sprite(V3.mats.glowW, 9); f.position.set(-0.2, 3.4, -0.4); f.visible = false; g.add(f);
  g.position.set(...p); g.rotation.y = -headingAt(c.s);
  g.userData = { flash: f, s: c.s };
  return g;
}
// The rest area: a lane to the right, a small kiosk with warm windows, and (v8, #306) a tall lit
// P sign that shows from far off.
function restStop(b, snowy) {
  const g = new THREE.Group(), s = (b.s0 + b.s1) / 2, p = worldAt(s, 16);
  {
    const c = document.createElement('canvas'); c.width = c.height = 128;
    const x = c.getContext('2d');
    x.fillStyle = '#1d55a8'; x.fillRect(0, 0, 128, 128); x.strokeStyle = '#fff'; x.lineWidth = 8; x.strokeRect(6, 6, 116, 116);
    x.fillStyle = '#fff'; x.font = 'bold 96px system-ui,sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('P', 64, 70);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
    const pole = new THREE.Group(), q = worldAt(b.s0, 13);
    const plate = new THREE.Mesh(V3.geo.plate, new THREE.MeshBasicMaterial({ map: t, color: 0xb0b0b0 })); plate.scale.set(2, 2, 1); plate.position.y = 6;
    pole.add(plate, part(V3.geo.pole, V3.mats.grey, 0.08, 6, 0.08, 0, 3, 0));
    pole.position.set(...q); pole.rotation.y = -headingAt(b.s0);
    g.add(pole);
  }
  const house = new THREE.Group();
  house.add(part(V3.geo.box, lam(0x7b3b2a), 8, 3, 5, 0, 1.5, 0));
  house.add(part(V3.geo.box, lam(snowy ? 0xe6edf3 : 0x2f2f33), 8.6, 0.3, 5.6, 0, 3.15, 0));
  for (const x of [-2.4, 0, 2.4]) { house.add(part(V3.geo.box, new THREE.MeshBasicMaterial({ color: 0xffc66b }), 1.4, 1.0, 0.05, x, 1.6, -2.53)); const l = sprite(V3.mats.glowY, 2.2); l.position.set(x, 1.6, -2.8); house.add(l); }
  house.position.set(...p); house.rotation.y = -headingAt(s) + Math.PI / 2;
  g.add(house);
  for (const sx of [b.s0, b.s1]) { const q = worldAt(sx, 9.5), l = sprite(V3.mats.glowY, 3.2); l.position.set(q[0], q[1] + 6, q[2]); g.add(l); g.add(part(V3.geo.pole, V3.mats.grey, 0.06, 6, 0.06, q[0], q[1] + 3, q[2])); }
  return g;
}
// v8 (#306): a street light over each side road's mouth, as on the main roads, so the junction
// shows from afar; its pool of light falls on the side road and the car waiting there.
function junctionLamp(J) {
  const g = new THREE.Group();
  for (const side of J.both ? [-1, 1] : [J.side]) {
    const q = worldAt(J.s + 7, side * 6.6), l = sprite(V3.mats.glowY, 4); l.position.set(q[0], q[1] + 7, q[2]); g.add(l);
    g.add(part(V3.geo.pole, V3.mats.grey, 0.07, 7, 0.07, q[0], q[1] + 3.5, q[2]));
    const pool = new THREE.PointLight(0xffc477, 18, 26, 1.2), p = worldAt(J.s, side * 6.5, 6.5); pool.position.set(...p); g.add(pool);
  }
  return g;
}
// The town at the end: street lights and lit windows.
function townLights() {
  const g = new THREE.Group();
  // v4: the villages (the 60 stretches) have street lights too, so high beams are not needed there.
  const lit = [];
  for (let s = 0; s < road.len - 300; s += 38) if (streetLit(s)) lit.push(s);
  for (let s = road.len - 300; s < road.total; s += 38) lit.push(s);
  for (const s of lit) for (const side of [-1, 1]) {
    const q = worldAt(s, side * 6.6); const l = sprite(V3.mats.glowY, 4); l.position.set(q[0], q[1] + 7, q[2]); g.add(l);
    g.add(part(V3.geo.pole, V3.mats.grey, 0.07, 7, 0.07, q[0], q[1] + 3.5, q[2]));
  }
  const r = rng(3);
  for (let s = road.len - 200; s < road.total; s += 22) for (const side of [-1, 1]) {
    if (r() < 0.35) continue;
    const q = worldAt(s, side * (22 + r() * 30)), l = sprite(V3.mats.glowY, 1.4 + r()); l.position.set(q[0], q[1] + 1.5 + r() * 4, q[2]); g.add(l);
  }
  return g;
}
function starField() {
  const r = rng(4), n = 500, a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { const th = r() * TAU, ph = 0.1 + r() * 1.3; a[i * 3] = Math.cos(th) * Math.cos(ph) * 650; a[i * 3 + 1] = Math.sin(ph) * 650; a[i * 3 + 2] = Math.sin(th) * Math.cos(ph) * 650; }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(a, 3));
  const p = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xb8c4e0, size: 1.6, sizeAttenuation: false, fog: false }));
  p.userData.sky = true; return p;
}
// Rain streaks or snowflakes in a box that moves with the car.
function weatherMesh(wx) {
  const snow = wx !== 'sade', n = wx === 'pyry' ? 2600 : snow ? 1600 : 900, r = rng(6);
  const a = new Float32Array(n * (snow ? 3 : 6));
  const box = { w: 26, h: 14, d: 70 };
  for (let i = 0; i < n; i++) {
    const x = (r() - 0.5) * box.w * 2, y = r() * box.h, z = -r() * box.d + 6;
    if (snow) { a[i * 3] = x; a[i * 3 + 1] = y; a[i * 3 + 2] = z; }
    else { a.set([x, y, z, x + 0.05, y + 0.6, z + 0.25], i * 6); }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(a, 3));
  const m = snow ? new THREE.Points(g, new THREE.PointsMaterial({ color: 0xdfe6ef, map: V3.glow, size: 0.16, transparent: true, opacity: 0.75, depthWrite: false }))
    : new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0x8c99aa, transparent: true, opacity: 0.4, depthWrite: false }));
  m.userData = { box, snow, base: a.slice(), wind: wx === 'pyry' ? 4.5 : 1.2, fall: snow ? 1.6 : 13 };
  m.frustumCulled = false;
  return m;
}

// ---- Every frame ----
// How brightly the player's headlights light a point (0..1). Reflectors and signs shine back from
// further: `far` > 1.
function lit(s, lat, far) {
  const d = s - P.s;
  if (d < 1) return 0;
  const reach = reachOf(P.high) * (far || 1), side = Math.abs(lat - P.lat) - (P.high ? 5 + d * 0.22 : 6 + d * 0.32);
  if (side > 0) return 0;
  return clamp(1.3 - d / reach, 0, 1);
}
function placeAt(o, s, lat, back, arm) {
  // v14: a car on the road straight on at a turn (risteys.js), along it.
  if (arm) { const p = armAt(arm, s - arm.a0, lat); o.position.set(...p); o.rotation.y = -arm.th + (back ? Math.PI : 0); return; }
  const p = worldAt(s, lat); o.position.set(...p); o.rotation.y = -headingAt(s) + (back ? Math.PI : 0);
}
function meshFor(t) {
  let m = V3.meshes.get(t.id);
  if (m) return m;
  if (t.police) m = policeMesh();
  else if (t.kind === 'konstaapeli') m = officerMesh();
  else if (t.kind === 'rekka' || (t.kind === 'vastaan' && t.truck)) m = truckMesh();
  else if (t.kind === 'traktori') m = tractorMesh();
  else if (t.kind === 'kavelija') m = walkerMesh(t);
  else if (t.kind === 'hirvi' || t.kind === 'poro') m = deerMesh(t.kind === 'poro');
  else if (t.kind === 'ambulanssi') m = ambulanceMesh();
  else if (t.kind === 'erikois') m = loadMesh(t);
  else if (t.kind === 'aura') m = ploughMesh();
  else if (t.escort || t.broken) {
    // v13: an escort car with an orange beacon on its roof; a broken-down car's hazard lights.
    m = carMesh(CAR_COLOURS[(t.colour || 0) % CAR_COLOURS.length]);
    if (t.escort) { const b = sprite(V3.mats.glowO, 1.4); b.position.set(0, 1.6, 0.25); m.add(b); m.userData.beacon = b; }
    else { const hz = []; for (const [x, z] of [[-0.85, -2.3], [0.85, -2.3], [-0.85, 2.3], [0.85, 2.3]]) { const o = sprite(V3.mats.glowO, 0.7); o.position.set(x, 0.7, z); m.add(o); hz.push(o); } m.userData.hazard = hz; m.userData.front.forEach(f => f.visible = false); }
  }
  else m = carMesh(CAR_COLOURS[(t.colour || 0) % CAR_COLOURS.length]);
  V3.meshes.set(t.id, m); V3.scene.add(m);
  return m;
}
let BEAM = 350, CAM_BACK = 11, CAM_UP = 4.6, CAM_LOOK = 34;
function draw3d(now) {
  if (!V3 || !road || !P) return;
  if (V3.built !== road) buildWorld();
  const { renderer, scene, camera, beam, other } = V3, R = renderer, el = R.domElement;
  const w = el.clientWidth || innerWidth, h = el.clientHeight || innerHeight;
  if (w !== V3.w || h !== V3.h) { V3.w = w; V3.h = h; R.setSize(w, h, false); camera.aspect = w / h; camera.fov = w < h ? 74 : 58; camera.updateProjectionMatrix(); }
  const time = (now || performance.now()) / 1000;

  // The player's car, turned a little with its sideways speed.
  const car = V3.carMesh, yaw = Math.atan2(P.vl, Math.max(P.v, 3));
  { const p = carAt(P.s, P.lat); car.position.set(...p); car.rotation.y = -carHeading(P.s) - yaw; }
  // v14 (#440): the blinker, BLINK_T s on and off.
  const blinkOn = P.signal && mode === 'drive' && (time % (BLINK_T * 2)) < BLINK_T;
  car.userData.blink.forEach((pair, i) => pair.forEach(o => { o.visible = blinkOn && (i ? P.signal > 0 : P.signal < 0); }));
  car.userData.rear.forEach(s => { s.material.opacity = input.brake && mode === 'drive' ? 1 : 0.55; s.scale.setScalar(input.brake ? 0.95 : 0.55); });
  // Camera behind and above, shaken by potholes and the shoulder.
  // v14: through a tight turn the camera looks less far ahead, at the bend and not across its corner.
  const inTurn = (road.turns || []).some(J => P.s + CAM_LOOK > J.a0 && P.s - 10 < J.a1) && !P.wrong;
  const look = inTurn ? CAM_LOOK / (1 + 2.5 * Math.abs(headingAt(P.s + CAM_LOOK) - headingAt(P.s))) : CAM_LOOK;
  const sh = shake * 0.12, cp = carAt(P.s - CAM_BACK, P.lat * 0.85, CAM_UP), ct = carAt(P.s + look, P.lat * 0.6, 0);
  camera.position.set(cp[0] + (Math.random() - 0.5) * sh, cp[1] + (Math.random() - 0.5) * sh, cp[2]);
  camera.lookAt(ct[0], ct[1], ct[2]);

  // Headlights: a spot for both, reaching far and narrow on high beams.
  const reach = reachOf(P.high), bp = carAt(P.s + 2.2, P.lat, 0.75), bt = carAt(P.s + (P.high ? 70 : 26), P.lat + P.vl * 0.6, P.high ? 0.6 : -0.3);
  beam.position.set(...bp); beam.target.position.set(...bt);
  beam.distance = reach * 1.3; beam.angle = P.high ? 0.5 : 0.62; beam.intensity = BEAM * (P.high ? 2.2 : 1); beam.decay = 1;

  // Others: placed, lights by their own beams, the nearest oncoming one lighting the road ahead of it.
  const seen = new Set(); let near = null;
  for (const t of things) {
    const m = meshFor(t); seen.add(t.id);
    const back = t.v < 0 || (t.kind === 'kavelija' && t.v < 0) || ((t.kind === 'hirvi' || t.kind === 'poro') ? false : false);
    placeAt(m, t.s, t.lat, back, t.arm);
    if (t.yaw) m.rotation.y += t.yaw;   // v8: a car at a side road faces the road, then turns onto it
    const u = m.userData;
    if (t.kind === 'hirvi' || t.kind === 'poro') {
      m.rotation.y += t.dir > 0 ? -Math.PI / 2 : Math.PI / 2;
      const b = lit(t.s, t.lat, 1.7); u.eyes.forEach(e => { e.material.opacity = b; e.visible = b > 0.02; });
    } else if (t.kind === 'kavelija') {
      const ph = time * 5 + t.id; u.legs[0].rotation.x = Math.sin(ph) * 0.4; u.legs[1].rotation.x = -Math.sin(ph) * 0.4;
      if (u.refl) { const b = lit(t.s, t.lat, 2.8); u.refl.material.opacity = b; u.refl.visible = b > 0.02; }
    } else {
      const d = Math.abs(t.s - P.s), k = 1.4 + d * 0.012;
      (u.front || []).forEach(s => s.scale.setScalar(s.userData.size * k * (t.high ? 3.2 : 1)));
      (u.rear || []).forEach(s => s.scale.setScalar(s.userData.size * k));
      if (u.beacon) { const on = (Math.sin(time * 8 + (t.beacon || 0)) + 1) / 2; u.beacon.material.opacity = 0.3 + on * 0.7; u.beacon.scale.setScalar(1.6 * k * (0.6 + on * 0.6)); }
      if (u.beacon2) { const on = (Math.sin(time * 8 + (t.beacon || 0) + Math.PI) + 1) / 2; u.beacon2.material.opacity = 0.3 + on * 0.7; u.beacon2.scale.setScalar(1.6 * k * (0.6 + on * 0.6)); }
      // v13: hazard lights, about once a second.
      if (u.hazard) { const on = (time % 0.9) < 0.45; u.hazard.forEach(o => { o.visible = on; o.scale.setScalar(0.7 * k); }); }
      // v12: the police light bar, its two blue lamps in turn.
      if (u.blue) u.blue.forEach((b, i) => { const on = t.blue && Math.sin(time * 13 + i * Math.PI) > 0; b.visible = on; if (on) b.scale.setScalar(1.4 * k); });
      if (u.tri) u.tri.material.color.setScalar(0.12 + 0.88 * lit(t.s + 4, t.lat, 2.5)).multiply(new THREE.Color(0xff6a1a));
      if (t.v < 0 && !t.arm && t.s > P.s && t.s - P.s < 220 && (!near || t.s < near.s)) near = t;
    }
  }
  for (const [id, m] of V3.meshes) if (!seen.has(id)) { scene.remove(m); dispose(m); V3.meshes.delete(id); }
  if (near) {
    const op = worldAt(near.s - near.len / 2, near.lat, 0.8), ot = worldAt(near.s - 40, near.lat, 0);
    other.position.set(...op); other.target.position.set(...ot); other.distance = near.high ? 120 : 60; other.decay = 0.6;
  }
  // v8 (#306 "ruutu välähtää"): its light on the road comes up and goes down over a few tenths of a
  // second (v1–v7: on and off at once, a flash over the whole road as a truck came within 220 m).
  const dtv = Math.min(0.1, Math.max(0, time - (V3.lt || time))); V3.lt = time;
  other.intensity += ((near ? (near.high ? 9 : 5) : 0) - other.intensity) * Math.min(1, dtv * 4);

  // v13: the roadworks' lights, red or green for each way; the triangles catch the headlights.
  for (const wm of V3.works || []) for (const l of wm.userData.lights) {
    const go = l.mine ? worksGreen(wm.userData.w) : worksOpen(wm.userData.w);
    l.red.visible = !go; l.green.visible = go;
  }
  for (const rm of V3.rails || []) railFrame(rm, time);
  for (const tm of V3.triangles || []) { const u = tm.userData; u.tri.material.color.setScalar(0.1 + 0.9 * lit(u.s, u.lat, 2.8)).multiply(new THREE.Color(0xff2a1a)); }
  // Fog in a dip: the view closes in, and lights up grey on high beams.
  if (V3.fogBase) {
    const f = fogAt(P.s), fg = scene.fog;
    fg.far = lerp(V3.fogBase.far, P.high ? 40 : 60, f); fg.near = lerp(25, 4, f);
    fg.color.copy(V3.fogBase.colour).lerp(new THREE.Color(P.high ? 0x8a929c : 0x2a2f36), f);
    if (!scene.background.equals(fg.color)) scene.background.copy(fg.color);
  }
  // Signs and cameras shine back when the beam reaches them.
  for (const sgn of V3.signs) { const u = sgn.userData, b = lit(u.s, u.lat, 2.6); u.mat.color.setScalar(0.07 + 0.93 * b); }
  for (const cm of V3.camMeshes) cm.userData.flash.visible = flash > 0.05 && Math.abs(cm.userData.s - P.s) < 40;
  for (const cm of V3.camMeshes) if (cm.userData.flash.visible) cm.userData.flash.material.opacity = flash;

  // Weather moves with the car; in snow, high beams light the flakes up into a wall.
  const wm = V3.weather;
  if (wm) {
    const u = wm.userData, a = wm.geometry.attributes.position.array, base = u.base, n = base.length / (u.snow ? 3 : 6);
    const fall = (time * u.fall), go = P.s * 1.0, drift = time * u.wind;
    for (let i = 0; i < n; i++) {
      const o = i * (u.snow ? 3 : 6);
      const y = ((base[o + 1] - fall) % u.box.h + u.box.h) % u.box.h;
      const z = (((base[o + 2] + go - 6) % u.box.d) + u.box.d) % u.box.d - u.box.d + 6;
      const x = (((base[o] + drift + u.box.w) % (u.box.w * 2)) + u.box.w * 2) % (u.box.w * 2) - u.box.w;
      if (u.snow) { a[o] = x; a[o + 1] = y; a[o + 2] = z; }
      else { a[o] = x; a[o + 1] = y; a[o + 2] = z; a[o + 3] = x + 0.05; a[o + 4] = y + 0.7; a[o + 5] = z + 0.6; }
    }
    wm.geometry.attributes.position.needsUpdate = true;
    const p = carAt(P.s, P.lat, 0); wm.position.set(p[0], p[1], p[2]); wm.rotation.y = -carHeading(P.s);
    if (u.snow) wm.material.opacity = P.high ? 0.95 : 0.6;
  }
  V3.world.children.forEach(o => { if (o.userData.sky) o.position.copy(camera.position); });
  R.render(scene, camera);
}

// The screen point of a spot on the road, for the glare of oncoming high beams. null if behind.
function screenOf(s, lat, up) {
  if (!V3) return null;
  const v = new THREE.Vector3(...worldAt(s, lat, up)).project(V3.camera);
  if (v.z > 1) return null;
  return { x: (v.x + 1) / 2 * W, y: (1 - v.y) / 2 * H };
}

// A slow phone runs short of pixels: step the pixel ratio down while the first seconds are slow.
function tune(ms) {
  if (!V3 || V3.tuned || mode !== 'drive' || ms > 500) return;
  V3.tt = (V3.tt || 0) + ms; V3.tn = (V3.tn || 0) + 1;
  if (V3.tt < 2500) return;
  const fps = 1000 * V3.tn / V3.tt, R = V3.renderer, pr = R.getPixelRatio();
  V3.tt = V3.tn = 0;
  if (V3.warm !== true) { V3.warm = true; return; }
  if (fps >= 27) V3.tuned = true;
  else if (pr > 1.01) { R.setPixelRatio(Math.max(1, pr - 0.5)); V3.w = 0; }
  else V3.tuned = true;
}
