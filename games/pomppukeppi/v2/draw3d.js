'use strict';
// Pomppukeppi v2: the board and the hares in 3D (three.js, the site's shared copy, #99). It only
// reads the world (world.js). index.html imports three.js and calls init3d(THREE); a phone that
// cannot draw 3D plays on a flat board drawn by ui.js (draw2d()).
// Board square (x, y) is world (x - (n - 1) / 2, 0, y - (n - 1) / 2): x to the right, y towards
// the camera. The camera never turns, so "up" on the stick is always up the screen.

let THREE = null, V3 = null, no3d = false;

function init3d(T) {
  THREE = T;
  const gl = document.getElementById('g');
  const renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#9fd6f2');
  scene.fog = new THREE.Fog(0x9fd6f2, 22, 60);
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 120);
  const hemi = new THREE.HemisphereLight(0xffffff, 0x5a7a3a, 1.6);
  const sun = new THREE.DirectionalLight(0xfff2d8, 1.5);
  sun.position.set(-4, 10, 6);
  scene.add(hemi, sun);
  V3 = { renderer, scene, camera, board: null, n: 0, tiles: null, tileCol: [], flash: null, hares: [], cash: null, qbox: null,
    marker: null, arrow: null, w: 0, h: 0, t: 0, frames: 0, ms: 0, tuned: false, col: new THREE.Color(), v: new THREE.Vector3() };
  scene.add(meadow());
  V3.cash = crate('#f2b632', '#a8700e', '💰'); V3.qbox = crate('#3d7ee8', '#1d4fa8', '?');
  scene.add(V3.cash, V3.qbox);
  V3.marker = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.05, 6, 28), new THREE.MeshBasicMaterial({ color: 0xffe14a }));
  V3.marker.rotation.x = -Math.PI / 2;
  V3.arrow = new THREE.Mesh(new THREE.ConeGeometry(0.14, 0.28, 12), new THREE.MeshLambertMaterial({ color: 0xffe14a, emissive: 0x806a10 }));
  V3.arrow.rotation.x = Math.PI;
  scene.add(V3.marker, V3.arrow);
  // Snowballs and their puffs of snow (#492): a few meshes made once and reused.
  const snow = new THREE.MeshLambertMaterial({ color: 0xffffff, emissive: 0x6a7a88 });
  V3.balls = [0, 1, 2].map(() => {
    const b = new THREE.Mesh(new THREE.SphereGeometry(0.21, 16, 12), snow);
    const sh = new THREE.Mesh(new THREE.CircleGeometry(0.17, 14), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.22, depthWrite: false }));
    sh.rotation.x = -Math.PI / 2; b.visible = sh.visible = false;
    scene.add(b, sh);
    return { b, sh };
  });
  const bit = new THREE.SphereGeometry(0.13, 8, 6);
  V3.puffs = [0, 1].map(() => {
    const g = new THREE.Group();
    for (let k = 0; k < 9; k++) g.add(new THREE.Mesh(bit, new THREE.MeshLambertMaterial({ color: 0xffffff, emissive: 0x6a7a88, transparent: true })));
    g.visible = false; scene.add(g);
    return g;
  });
}

const lambert = hex => new THREE.MeshLambertMaterial({ color: new THREE.Color(hex) });

// Grass all round, a few spruces and birches, flowers.
function meadow() {
  const g = new THREE.Group();
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(140, 140), lambert('#6fb04a'));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.22;
  g.add(ground);
  const r = rng(17), trunk = lambert('#6b4a2a'), green = lambert('#2f7a3a'), birch = lambert('#f2f0e8'), leaf = lambert('#7cc04a');
  const cone = new THREE.ConeGeometry(0.9, 2.6, 8), stem = new THREE.CylinderGeometry(0.12, 0.16, 0.8, 6), ball = new THREE.SphereGeometry(0.9, 8, 6);
  for (let k = 0; k < 26; k++) {
    const a = r() * TAU, d = 8.5 + r() * 9, x = Math.cos(a) * d, z = Math.sin(a) * d - 3;
    if (z > 6) continue;   // keep the near side, under the camera, open
    const t = new THREE.Group();
    if (r() < 0.6) { const s = new THREE.Mesh(stem, trunk); s.position.y = 0.2; const c = new THREE.Mesh(cone, green); c.position.y = 1.7; t.add(s, c); }
    else { const s = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, 2, 6), birch); s.position.y = 0.8; const c = new THREE.Mesh(ball, leaf); c.position.y = 2.1; t.add(s, c); }
    t.position.set(x, -0.22, z); t.scale.setScalar(0.8 + r() * 0.6);
    g.add(t);
  }
  const petals = ['#ffffff', '#ffd84a', '#f07ab0', '#b08af0'].map(lambert), fl = new THREE.SphereGeometry(0.07, 5, 4);
  for (let k = 0; k < 90; k++) {
    const x = (r() - 0.5) * 26, z = (r() - 0.5) * 22;
    if (Math.abs(x) < 5.6 && Math.abs(z) < 5.6) continue;
    const f = new THREE.Mesh(fl, petals[k % 4]); f.position.set(x, -0.18, z); g.add(f);
  }
  return g;
}
function labelTexture(bg, edge, text) {
  const cv = document.createElement('canvas'); cv.width = cv.height = 128;
  const x = cv.getContext('2d');
  x.fillStyle = bg; x.fillRect(0, 0, 128, 128);
  x.strokeStyle = edge; x.lineWidth = 12; x.strokeRect(6, 6, 116, 116);
  x.fillStyle = '#fff'; x.font = '900 80px system-ui,sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText(text, 64, 70);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
function crate(bg, edge, text) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.52, 0.52), new THREE.MeshLambertMaterial({ map: labelTexture(bg, edge, text) }));
  m.visible = false;
  return m;
}

// The board: a wooden frame, one tile per square (an instanced mesh, coloured per square), rocks
// and holes.
function buildBoard(w) {
  if (V3.board) { V3.scene.remove(V3.board); V3.board.traverse(o => { if (o.geometry) o.geometry.dispose(); }); }
  const n = w.n, g = new THREE.Group(), half = (n - 1) / 2;
  const frame = new THREE.Mesh(new THREE.BoxGeometry(n + 0.5, 0.3, n + 0.5), lambert('#a8743a'));
  frame.position.y = -0.2; g.add(frame);
  const tiles = new THREE.InstancedMesh(new THREE.BoxGeometry(0.92, 0.16, 0.92), new THREE.MeshLambertMaterial({ color: 0xffffff }), n * n);
  const m = new THREE.Matrix4();
  for (let k = 0; k < n * n; k++) {
    m.makeTranslation(k % n - half, -0.02, ((k / n) | 0) - half);
    tiles.setMatrixAt(k, m); tiles.setColorAt(k, V3.col.set('#ece4cc'));
  }
  g.add(tiles);
  const rock = new THREE.DodecahedronGeometry(0.38, 0), rockM = lambert('#8a8f96'), holeM = new THREE.MeshBasicMaterial({ color: 0x2a1c10 });
  for (let k = 0; k < n * n; k++) {
    const x = k % n - half, z = ((k / n) | 0) - half;
    if (w.tiles[k] === ROCK) { const r = new THREE.Mesh(rock, rockM); r.position.set(x, 0.22, z); r.rotation.set(k, k * 2, 0); r.scale.y = 0.8; g.add(r); }
    if (w.tiles[k] === HOLE) { const h = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 0.04, 20), holeM); h.position.set(x, 0.07, z); g.add(h); }
  }
  V3.scene.add(g);
  V3.board = g; V3.n = n; V3.boardN = w.board; V3.tiles = tiles; V3.tileCol = new Array(n * n).fill(null); V3.tileHex = new Array(n * n).fill(null); V3.flash = new Float32Array(n * n);
}

// A hare on a pogo stick, facing +z. Its colour is its jumper and the stick's spring.
function hareRig(col) {
  const g = new THREE.Group(), fur = lambert('#f4efe4'), own = lambert(COLORS[col]), dark = lambert('#222222'), pink = lambert('#f2a0b0'), steel = lambert('#b8c0c8');
  const add = (geo, mat, x, y, z, parent) => { const o = new THREE.Mesh(geo, mat); o.position.set(x, y, z); (parent || g).add(o); return o; };
  const stick = new THREE.Group(); g.add(stick);
  add(new THREE.CylinderGeometry(0.035, 0.035, 0.9, 8), steel, 0, 0.5, 0.1, stick);
  add(new THREE.CylinderGeometry(0.07, 0.07, 0.2, 10), own, 0, 0.2, 0.1, stick);          // the spring
  add(new THREE.BoxGeometry(0.34, 0.04, 0.08), steel, 0, 0.34, 0.1, stick);                // foot pegs
  add(new THREE.CylinderGeometry(0.03, 0.03, 0.3, 6), dark, 0, 0.92, 0.1, stick).rotation.z = Math.PI / 2;   // handles
  const body = new THREE.Group(); g.add(body);
  add(new THREE.SphereGeometry(0.08, 8, 6), fur, -0.11, 0.38, 0.06, body);                // feet on the pegs
  add(new THREE.SphereGeometry(0.08, 8, 6), fur, 0.11, 0.38, 0.06, body);
  const torso = add(new THREE.SphereGeometry(0.24, 14, 10), own, 0, 0.66, 0, body); torso.scale.set(1, 1.15, 0.9);
  add(new THREE.SphereGeometry(0.15, 10, 8), fur, 0, 0.64, 0.13, body).scale.set(1, 1.2, 0.6);   // the belly
  add(new THREE.SphereGeometry(0.06, 8, 6), fur, -0.15, 0.86, 0.12, body);                // paws on the handles
  add(new THREE.SphereGeometry(0.06, 8, 6), fur, 0.15, 0.86, 0.12, body);
  add(new THREE.SphereGeometry(0.1, 8, 6), fur, 0, 0.5, -0.2, body);                      // the tail
  const head = new THREE.Group(); head.position.set(0, 1.0, 0.02); body.add(head);
  add(new THREE.SphereGeometry(0.19, 14, 10), fur, 0, 0, 0, head);
  add(new THREE.SphereGeometry(0.03, 6, 4), dark, -0.075, 0.04, 0.16, head);
  add(new THREE.SphereGeometry(0.03, 6, 4), dark, 0.075, 0.04, 0.16, head);
  add(new THREE.SphereGeometry(0.03, 6, 4), pink, 0, -0.03, 0.185, head);
  const ears = [];
  for (const s of [-1, 1]) {
    const ear = new THREE.Group(); ear.position.set(s * 0.08, 0.14, -0.02); head.add(ear);
    add(new THREE.CylinderGeometry(0.035, 0.055, 0.34, 8), fur, 0, 0.17, 0, ear);
    add(new THREE.CylinderGeometry(0.02, 0.03, 0.26, 6), pink, 0, 0.17, 0.03, ear);
    ear.rotation.z = -s * 0.18; ears.push(ear);
  }
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.32, 20), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.25, depthWrite: false }));
  shadow.rotation.x = -Math.PI / 2;
  g.scale.setScalar(1.3);   // read well on a small phone (a hare is about one square tall)
  V3.scene.add(g, shadow);
  return { g, body, head, ears, shadow, yaw: 0, col };
}

// Fit the board in the view: the camera looks down at a fixed slant from the near side, far
// enough for the whole board, with room left at the top for the scores.
function placeCamera(n, land) {
  const cam = V3.camera, pitch = land ? 0.98 : 0.92, half = n / 2 + 0.45;
  const vf = cam.fov * Math.PI / 360, hf = Math.atan(Math.tan(vf) * cam.aspect);
  const d = Math.max(half / Math.tan(hf) + half * Math.cos(pitch) * 0.4, half * (land ? 1.06 : 1.25) / Math.tan(vf)) * 1.02;
  const tz = land ? 0.15 : -0.45;
  cam.position.set(0, Math.sin(pitch) * d, tz + Math.cos(pitch) * d);
  cam.lookAt(0, 0, tz);
}

function render3d(w, me, dt) {
  const R = V3.renderer, cv = R.domElement, cw = cv.clientWidth || innerWidth, ch = cv.clientHeight || innerHeight;
  V3.t += dt;
  if (cw !== V3.w || ch !== V3.h || V3.n !== w.n) {
    V3.w = cw; V3.h = ch; R.setSize(cw, ch, false); V3.camera.aspect = cw / ch; V3.camera.updateProjectionMatrix();
    if (V3.n !== w.n || V3.boardN !== w.board) buildBoard(w);
    placeCamera(w.n, cw > ch);
  }
  if (V3.boardN !== w.board) { buildBoard(w); placeCamera(w.n, cw > ch); }
  const n = w.n, half = (n - 1) / 2, tiles = V3.tiles, m = new THREE.Matrix4();
  let dirtyC = false, dirtyM = false;
  for (let k = 0; k < n * n; k++) {
    const t = w.tiles[k];
    // Redrawn when the owner changes (with a flash) or the owner's colour does (a room may swap a
    // computer hare's colour with a phone's).
    const base = t >= 0 ? COLORS[w.hares[t] ? w.hares[t].col : t] : t === BLANK ? ((k % n + ((k / n) | 0)) % 2 ? '#e6ddc2' : '#f0e9d4') : '#5f9a3e';
    if (t !== V3.tileCol[k] || base !== V3.tileHex[k]) {
      if (t !== V3.tileCol[k] && V3.tileCol[k] !== null && t >= 0) V3.flash[k] = 0.25;
      V3.tileCol[k] = t; V3.tileHex[k] = base;
      tiles.setColorAt(k, V3.col.set(base)); dirtyC = true;
    }
    if (V3.flash[k] > 0) {
      V3.flash[k] = Math.max(0, V3.flash[k] - dt);
      const up = Math.sin(V3.flash[k] / 0.25 * Math.PI) * 0.1;
      m.makeTranslation(k % n - half, -0.02 + up, ((k / n) | 0) - half); tiles.setMatrixAt(k, m); dirtyM = true;
    }
  }
  if (dirtyC) tiles.instanceColor.needsUpdate = true;
  if (dirtyM) tiles.instanceMatrix.needsUpdate = true;
  // The hares.
  while (V3.hares.length > w.hares.length) { const r = V3.hares.pop(); V3.scene.remove(r.g, r.shadow); }
  w.hares.forEach((h, i) => {
    let r = V3.hares[i];
    if (!r || r.col !== h.col) { if (r) V3.scene.remove(r.g, r.shadow); r = V3.hares[i] = hareRig(h.col); }
    const p = harePos(h), x = p.x - half, z = p.y - half;
    r.g.position.set(x, 0.06 + p.z, z);
    if (h.x !== h.fx || h.y !== h.fy) r.yaw = Math.atan2(h.x - h.fx, h.y - h.fy);
    const turn = ((r.yaw - r.g.rotation.y + Math.PI) % TAU + TAU) % TAU - Math.PI;
    r.g.rotation.y += turn * Math.min(1, dt * 14);
    // Squash on the ground, stretch in the air; the ears flop behind.
    const ground = Math.max(0, 1 - Math.min(p.p, 1 - p.p) * 7), sq = 1 - ground * 0.16;
    r.body.scale.set(1 + (1 - sq) * 0.7, sq, 1 + (1 - sq) * 0.7);
    r.body.position.y = -ground * 0.08;
    r.ears.forEach((e, k) => { e.rotation.x = -0.25 - Math.cos(Math.PI * p.p) * 0.35; e.rotation.z = (k ? -1 : 1) * 0.18; });
    // Stunned: rocking; fast: leaning in.
    r.g.rotation.z = h.stun > 0 ? Math.sin(V3.t * 18) * 0.25 : 0;
    r.g.rotation.x = h.fast > 0 ? 0.12 : 0;
    r.shadow.position.set(x, 0.075, z);
    r.shadow.scale.setScalar(1 - p.z * 0.35);
    if (h === me) {
      V3.marker.position.set(x, 0.08, z);
      V3.arrow.position.set(x, 0.06 + p.z + 2.1 + Math.sin(V3.t * 5) * 0.06, z);
    }
  });
  V3.marker.visible = V3.arrow.visible = !!me && w.ph !== 'over';
  for (const [mesh, b] of [[V3.cash, w.cash], [V3.qbox, w.qbox]]) {
    mesh.visible = !!b;
    if (b) { mesh.position.set(b.x - half, 0.42 + Math.sin(V3.t * 3) * 0.06, b.y - half); mesh.rotation.y = V3.t * 1.4; }
  }
  // Snowballs in the air, with a shadow under each.
  V3.balls.forEach((m, k) => {
    const b = w.balls[k];
    m.b.visible = m.sh.visible = !!b;
    if (!b) return;
    const p = ballPos(w, b);
    m.b.position.set(p.x - half, 0.06 + p.z, p.y - half);
    m.b.rotation.x += dt * 9;
    m.sh.position.set(p.x - half, 0.075, p.y - half);
  });
  // Puffs: the bits fly out and fade (ui.js keeps the list and their times).
  V3.puffs.forEach((g, k) => {
    const f = puffs[k];
    g.visible = !!f;
    if (!f) return;
    const q = f.t / PUFF_T;
    g.position.set(f.x - half, 0.06 + f.z, f.y - half);
    g.children.forEach((o, j) => {
      const a = j / g.children.length * TAU, up = (j % 3 - 1) * 0.5;
      o.position.set(Math.cos(a) * 0.75 * q, up * q - q * q * 0.3, Math.sin(a) * 0.75 * q);
      o.scale.setScalar(1.3 - q * 0.6);
      o.material.opacity = Math.min(1, 2 * (1 - q));
    });
  });
  R.render(V3.scene, V3.camera);
}
// Screen px of a board point (x, y, height): the names and pop-ups ui.js writes on the 2D canvas.
function project3d(x, y, z) {
  const half = (V3.n - 1) / 2, v = V3.v.set(x - half, z, y - half).project(V3.camera);
  return { x: (v.x + 1) / 2 * V3.w, y: (1 - v.y) / 2 * V3.h };
}
// A slow phone: fewer pixels, at most twice in the first seconds of play (Hiihto v7's tune()).
function tune(ms) {
  if (!V3 || V3.tuned || ms > 500) return;
  V3.frames++; V3.ms += ms;
  if (V3.frames < 90) return;
  const fps = 1000 / (V3.ms / V3.frames), pr = V3.renderer.getPixelRatio();
  V3.frames = 0; V3.ms = 0;
  if (fps < 40 && pr > 1) { V3.renderer.setPixelRatio(Math.max(1, pr - 0.5)); V3.w = 0; }
  else V3.tuned = true;
}
