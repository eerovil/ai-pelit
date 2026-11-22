'use strict';
// Pulkkamäki v1: the hill on a Christmas evening, in 3D (three.js, the site's shared copy, #99).
// It only reads the hill and the sleds (world.js). index.html imports three.js and calls
// init3d(THREE); a phone that cannot draw 3D plays on with the HUD over a plain picture.
// A hill place (s, x, y) is world (centreX(s) + x, y, -s).

let THREE = null, V3 = null, no3d = false, camView = 'fp';   // 'fp' through the eyes, 'back' behind

function init3d(T) {
  THREE = T;
  const gl = document.getElementById('g');
  const renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(64, 1, 0.05, 900);
  // An evening: blue light from the sky, a moon low ahead, the lights warm and bright.
  const hemi = new THREE.HemisphereLight(0xb4c8f0, 0x34406a, 1.9);
  const moon = new THREE.DirectionalLight(0xdfe8ff, 1.3);
  scene.add(hemi, moon, moon.target);
  scene.fog = new THREE.Fog(0x22325a, 50, 330);
  const sky = skyDome();
  scene.add(sky);
  V3 = { renderer, scene, camera, moon, sky, hill: null, world: null, rigs: new Map(), w: 0, h: 0, v: new THREE.Vector3(), cam: null, snow: null, santa: null, t: 0, view: camView };
  V3.snow = snowfall(); scene.add(V3.snow);
  V3.santa = santaSleigh(); scene.add(V3.santa);
}

// Vertex colours are linear: fill them from THREE.Color('#hex').
function colorArray(n, pick) {
  const a = new Float32Array(n * 3), c = new THREE.Color();
  for (let i = 0; i < n; i++) { c.set(pick(i)); a[i * 3] = c.r; a[i * 3 + 1] = c.g; a[i * 3 + 2] = c.b; }
  return a;
}
// Several shapes in one geometry with a colour each, so a spruce is one draw for all of them.
function merge(parts) {
  const geos = parts.map(([g, hex]) => { g = g.index ? g.toNonIndexed() : g; g.setAttribute('color', new THREE.BufferAttribute(colorArray(g.attributes.position.count, () => hex), 3)); return g; });
  const out = new THREE.BufferGeometry();
  for (const name of ['position', 'normal', 'color']) {
    const n = geos.reduce((s, g) => s + g.attributes[name].array.length, 0), a = new Float32Array(n);
    let o = 0; for (const g of geos) { a.set(g.attributes[name].array, o); o += g.attributes[name].array.length; }
    out.setAttribute(name, new THREE.BufferAttribute(a, 3));
  }
  return out;
}
const lambert = () => new THREE.MeshLambertMaterial({ vertexColors: true });

function skyDome() {
  const g = new THREE.SphereGeometry(700, 24, 12), p = g.attributes.position, c = new THREE.Color(), top = new THREE.Color('#0d1534'), low = new THREE.Color('#5a5f9a');
  g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(p.count * 3), 3));
  for (let i = 0; i < p.count; i++) { c.copy(low).lerp(top, clamp(p.getY(i) / 260, 0, 1)); g.attributes.color.setXYZ(i, c.r, c.g, c.b); }
  const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false, depthWrite: false }));
  m.renderOrder = -2;
  // Stars and the moon.
  const r = rng(5), n = 260, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const a = r() * TAU, e = 0.12 + r() * 1.3, d = 650;
    pos[i * 3] = Math.cos(e) * Math.sin(a) * d; pos[i * 3 + 1] = Math.sin(e) * d; pos[i * 3 + 2] = Math.cos(e) * Math.cos(a) * d;
  }
  const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  m.add(new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xffffff, size: 2.2, sizeAttenuation: false, fog: false, depthWrite: false })));
  const moonDisc = new THREE.Mesh(new THREE.CircleGeometry(16, 24), new THREE.MeshBasicMaterial({ color: 0xf6f1d8, fog: false, depthWrite: false }));
  moonDisc.position.set(-180, 170, -620); moonDisc.lookAt(0, 0, 0);
  m.add(moonDisc);
  return m;
}

// Snow falling round the camera: the flakes wrap round a box that moves with it.
function snowfall() {
  const n = 700, pos = new Float32Array(n * 3), r = rng(9);
  for (let i = 0; i < n; i++) { pos[i * 3] = (r() - 0.5) * 50; pos[i * 3 + 1] = r() * 26; pos[i * 3 + 2] = -r() * 70; }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const p = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 0.13, transparent: true, opacity: 0.9, depthWrite: false }));
  p.frustumCulled = false;
  return p;
}

// Santa's sleigh and reindeer, a dark shape crossing the sky now and then, Rudolf's nose lit.
function santaSleigh() {
  const parts = [], box = (w, h, d, x, y, z, col) => { const g = new THREE.BoxGeometry(w, h, d); g.translate(x, y, z); parts.push([g, col]); };
  box(3, 1.4, 1.6, 0, 0, 0, '#3a1420'); box(3.6, 0.2, 0.2, 0.2, -0.9, 0.6, '#2a2030'); box(3.6, 0.2, 0.2, 0.2, -0.9, -0.6, '#2a2030');
  box(1.2, 1.3, 1, -0.4, 1.0, 0, '#2a2030');
  for (let i = 0; i < 4; i++) { box(1.8, 0.8, 0.6, 4 + i * 2.6, 0.3 + (i % 2) * 0.3, (i % 2 ? 0.6 : -0.6), '#2c2226'); box(0.4, 0.8, 0.3, 4.9 + i * 2.6, 1.0 + (i % 2) * 0.3, (i % 2 ? 0.6 : -0.6), '#2c2226'); }
  const m = new THREE.Mesh(merge(parts), new THREE.MeshBasicMaterial({ vertexColors: true, fog: false }));
  const nose = new THREE.Mesh(new THREE.SphereGeometry(0.35, 8, 6), new THREE.MeshBasicMaterial({ color: 0xff2a2a, fog: false }));
  nose.position.set(13.1, 1.5, 0.6); m.add(nose);
  m.visible = false; m.scale.setScalar(1.6);
  return m;
}

// ---- The hill ----
function hillPoint(hill, s, x, y) { return [centreX(hill, s) + x, y, -s]; }
// The way a sled heading `yaw` from the course really goes in the world (v6): s and x are not
// square to each other where the course bends, so on a sharp bend this differs from course + yaw.
function worldDir(hill, s, yaw) {
  const c = (centreX(hill, s + 0.6) - centreX(hill, s - 0.6)) / 1.2;
  return Math.atan2(c * Math.cos(yaw) + Math.sin(yaw), Math.cos(yaw));
}
// Hill place a world distance `d` from (s, x) along world heading `dir`.
function hillAhead(hill, s, x, dir, d) {
  const s2 = s + Math.cos(dir) * d;
  return [s2, centreX(hill, s) + x + Math.sin(dir) * d - centreX(hill, s2)];
}

function buildWorld(hill) {
  if (V3.world) { V3.scene.remove(V3.world); V3.world.traverse(o => { if (o.geometry) o.geometry.dispose(); }); }
  const world = new THREE.Group();
  world.add(terrain(hill), oldTracks(hill), kickers(hill), spruces(hill), rocksAndSnowmen(hill), lanterns(hill), finishArch(hill), tunnels(hill));
  V3.gifts = gifts(hill); world.add(V3.gifts);
  V3.scene.add(world);
  V3.world = world; V3.hill = hill; V3.trails = new Map();
}

// The snow (#475): soft, uneven, with no pattern that repeats or shimmers (a tiled stripe pattern
// looked bad on the phone); the tracks are real lines laid down the hill (oldTracks, layTrail).
// The texture is drawn once on a canvas: large soft patches of light and shade, and a fine grain.
function snowTexture(groomed) {
  const n = 512, cv = document.createElement('canvas'); cv.width = cv.height = n;
  const g = cv.getContext('2d'), r = rng(groomed ? 7 : 11);
  g.fillStyle = '#ffffff'; g.fillRect(0, 0, n, n);
  // Soft patches, drawn three times over with wrapping so the tile has no edges.
  for (let k = 0; k < (groomed ? 60 : 90); k++) {
    const x = r() * n, y = r() * n, rad = 30 + r() * 90, dark = r() < 0.5;
    for (const ox of [-n, 0, n]) for (const oy of [-n, 0, n]) {
      const gr = g.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, rad);
      gr.addColorStop(0, dark ? `rgba(185,198,230,${groomed ? 0.16 : 0.26})` : 'rgba(255,255,255,.3)');
      gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = gr; g.fillRect(x + ox - rad, y + oy - rad, rad * 2, rad * 2);
    }
  }
  for (let k = 0; k < 4000; k++) {
    const v = 232 + Math.floor(r() * 23);
    g.fillStyle = `rgba(${v - 6},${v - 3},${v},.5)`;
    g.fillRect(r() * n, r() * n, 2, 2);
  }
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = Math.min(8, V3 ? V3.renderer.capabilities.getMaxAnisotropy() : 4);
  return t;
}

// Grooves in the snow: for each runner a dark line with a bright rim beside it, along a path of
// [s, x, yaw] points. Returns positions for an indexed strip, four points across per path point.
function groovePoint(hill, pos, k, S0, X0, yaw, w) {
  for (let r = 0; r < 2; r++) for (let e = 0; e < 2; e++) {
    const o = (r ? 1 : -1) * 0.27 + (e ? w : -w), X = X0 + o * Math.cos(yaw), S = S0 - o * Math.sin(yaw);
    const p = hillPoint(hill, S, X, groundAt(hill, S, X) + 0.025), q = (k * 4 + r * 2 + e) * 3;
    pos[q] = p[0]; pos[q + 1] = p[1]; pos[q + 2] = p[2];
  }
}
function grooveIndex(n) {
  const idx = [];
  for (let i = 0; i < n - 1; i++) for (let r = 0; r < 2; r++) {
    const a = i * 4 + r * 2, b = a + 4;
    idx.push(a, b, a + 1, a + 1, b, b + 1);
  }
  return idx;
}
const grooveMat = (op) => new THREE.MeshBasicMaterial({ color: 0x7a8ec0, transparent: true, opacity: op, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, side: THREE.DoubleSide });

// Earlier sledders' tracks: long, gently wandering lines down the whole track, none alike.
function oldTracks(hill) {
  const r = rng(hill.n * 977 + 5), paths = [];
  for (let t = 0; t < 14; t++) {
    const x0 = (r() * 2 - 1) * (hill.width / 2 - 1.5), a1 = 1 + r() * 3, k1 = 0.02 + r() * 0.04, p1 = r() * TAU;
    const a2 = r() * 1.2, k2 = 0.08 + r() * 0.1, p2 = r() * TAU, s0 = r() * hill.len * 0.5, s1 = s0 + hill.len * (0.3 + r() * 0.7);
    const xAt = s => clamp(x0 + a1 * Math.sin(s * k1 + p1) + a2 * Math.sin(s * k2 + p2), -hill.width / 2 + 0.5, hill.width / 2 - 0.5);
    const pts = [];
    for (let s = s0; s < Math.min(s1, hill.len + 40); s += 1) pts.push([s, xAt(s), Math.atan(xAt(s + 0.5) - xAt(s - 0.5))]);
    if (pts.length > 2) paths.push(pts);
  }
  const total = paths.reduce((a, p) => a + p.length, 0), pos = new Float32Array(total * 12), idx = [];
  let k = 0;
  for (const p of paths) {
    const base = k;
    p.forEach(([S, X, yaw], i) => groovePoint(hill, pos, k++, S, X, yaw, i === 0 || i === p.length - 1 ? 0 : 0.05));
    for (const v of grooveIndex(p.length)) idx.push(v + base * 4);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setIndex(idx);
  return new THREE.Mesh(g, grooveMat(0.32));
}

// The track packed smooth, the banks rising beside it, deep snow beyond.
function terrain(hill) {
  const xs = [];
  for (let x = -70; x <= 70; x += x < -14 || x > 14 ? 5 : 1) xs.push(x);
  const s0 = -40, s1 = hill.total, ds = 2, rows = Math.floor((s1 - s0) / ds) + 1, cols = xs.length;
  const pos = new Float32Array(rows * cols * 3), col = new Float32Array(rows * cols * 3), uv = new Float32Array(rows * cols * 2);
  const c = new THREE.Color(), track = new THREE.Color('#eef3ff'), soft = new THREE.Color('#cfdaf4'), under = new THREE.Color('#8a97c0');
  const TILE = 14;   // metres one texture tile covers
  for (let i = 0; i < rows; i++) {
    const s = s0 + i * ds, cx = centreX(hill, s), b = baseAt(hill, Math.max(0, s)) + (s < 0 ? -s * 0.1 : 0);
    for (let j = 0; j < cols; j++) {
      const x = xs[j], k = (i * cols + j) * 3;
      pos[k] = cx + x; pos[k + 1] = b + bankAt(hill, x) * (Math.abs(x) > 30 ? 0.6 : 1) + bermAt(hill, Math.max(0, s), x); pos[k + 2] = -s;
      c.copy(track).lerp(soft, clamp((Math.abs(x) - hill.width / 2) / 4, 0, 1));
      if (Math.abs(x) <= hill.width / 2 + WALL + 1 && tunnelAt(hill, s)) c.lerp(under, 0.55);   // in a tunnel's shade (v6)
      col[k] = c.r; col[k + 1] = c.g; col[k + 2] = c.b;
      uv[(i * cols + j) * 2] = x / TILE; uv[(i * cols + j) * 2 + 1] = s / TILE;
    }
  }
  // Two groups: the groomed track (with its banks) and the deep snow, each with its own texture.
  const groomed = [], deep = [], edge = hill.width / 2 + 3;
  for (let i = 0; i < rows - 1; i++) for (let j = 0; j < cols - 1; j++) {
    const a = i * cols + j, b = a + 1, d = a + cols, e = d + 1;
    (Math.max(Math.abs(xs[j]), Math.abs(xs[j + 1])) <= edge ? groomed : deep).push(a, b, d, b, e, d);   // wound to face up
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  g.setIndex(groomed.concat(deep));
  g.addGroup(0, groomed.length, 0); g.addGroup(groomed.length, deep.length, 1);
  g.computeVertexNormals();
  if (!V3.snowTex) V3.snowTex = [snowTexture(true), snowTexture(false)];
  const mats = V3.snowTex.map(t => new THREE.MeshLambertMaterial({ vertexColors: true, map: t }));
  return new THREE.Mesh(g, mats);
}

// Each sled's own runner tracks in the snow behind it, as long as the run.
const TRAIL_MAX = 1400, TRAIL_STEP = 0.5;
function trailFor(sl) {
  let tr = V3.trails.get(sl.id);
  if (!tr) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(TRAIL_MAX * 12), 3));
    g.setIndex(grooveIndex(TRAIL_MAX)); g.setDrawRange(0, 0);
    const m = new THREE.Mesh(g, grooveMat(0.6));
    m.frustumCulled = false;
    tr = { mesh: m, n: 0, last: null, gap: false };
    V3.trails.set(sl.id, tr); V3.world.add(m);
  }
  return tr;
}
function layTrail(hill, sl) {
  const tr = trailFor(sl);
  if (sl.air || sl.s < 1 || sl.fin && sl.v < 0.5) { tr.gap = true; return; }
  if (!tr.gap && tr.last && Math.hypot(sl.s - tr.last[0], sl.x - tr.last[1]) < TRAIL_STEP) return;
  if (tr.n >= TRAIL_MAX - 3) return;
  const pos = tr.mesh.geometry.attributes.position.array;
  // Over a gap (a jump), the old end and the new start are laid again with no width, so the
  // pieces across the gap have no area.
  if (tr.gap && tr.last) { groovePoint(hill, pos, tr.n++, ...tr.last, 0); groovePoint(hill, pos, tr.n++, sl.s, sl.x, sl.yaw, 0); }
  tr.gap = false;
  groovePoint(hill, pos, tr.n++, sl.s, sl.x, sl.yaw, 0.06);
  tr.last = [sl.s, sl.x, sl.yaw];
  const g = tr.mesh.geometry;
  g.attributes.position.needsUpdate = true;
  g.setDrawRange(0, Math.max(0, tr.n - 1) * 12);
}

// A jump: a ramp of snow rising as u², its sides and its lip, with a row of lights on the lip.
function kickers(hill) {
  const pos = [], col = [], c = new THREE.Color(), lights = [];
  const tri = (a, b, d, hex) => { c.set(hex); for (const p of [a, b, d]) { pos.push(...p); col.push(c.r, c.g, c.b); } };
  const quad = (a, b, d, e, hex) => { tri(a, b, d, hex); tri(b, e, d, hex); };
  for (const k of hill.kicks) {
    const N = 10, L = k.x - k.w / 2, R = k.x + k.w / 2;
    const top = (u, x) => { const s = k.s + u * k.len; return hillPoint(hill, s, x, snowAt(hill, s, x) + k.h * u * u); };
    const bot = (u, x) => { const s = k.s + u * k.len; return hillPoint(hill, s, x, snowAt(hill, s, x) - 0.05); };
    for (let i = 0; i < N; i++) {
      const u0 = i / N, u1 = (i + 1) / N;
      quad(top(u0, L), top(u0, R), top(u1, L), top(u1, R), '#f4f8ff');
      quad(bot(u0, L), top(u0, L), bot(u1, L), top(u1, L), '#b7c6e8');
      quad(top(u0, R), bot(u0, R), top(u1, R), bot(u1, R), '#b7c6e8');
    }
    quad(top(1, L), top(1, R), bot(1, L), bot(1, R), '#9fb0d8');
    for (let i = 0; i <= 6; i++) lights.push(top(1, L + (R - L) * i / 6).map((v, j) => j === 1 ? v + 0.12 : v));
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
  g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(col), 3));
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide }));
  m.add(glowPoints(lights, i => ['#ff4848', '#ffd23a', '#48ff7a', '#4aa8ff'][i % 4], 0.5));
  return m;
}

// Little lights that glow: a bright dot with a soft halo.
function glowPoints(pts, colour, size) {
  const n = pts.length, pos = new Float32Array(n * 3);
  pts.forEach((p, i) => pos.set(p, i * 3));
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(colorArray(n, colour), 3));
  const grp = new THREE.Group();
  grp.add(new THREE.Points(g, new THREE.PointsMaterial({ vertexColors: true, size, fog: false })));
  grp.add(new THREE.Points(g, new THREE.PointsMaterial({ vertexColors: true, size: size * 3.2, transparent: true, opacity: 0.28, blending: THREE.AdditiveBlending, depthWrite: false, fog: false })));
  return grp;
}

function spruceGeometry() {
  const parts = [];
  const trunk = new THREE.CylinderGeometry(0.18, 0.25, 1, 6); trunk.translate(0, 0.5, 0); parts.push([trunk, '#4a3222']);
  [[2.2, 2.2, 1.6], [1.8, 2.0, 2.6], [1.3, 1.8, 3.6], [0.8, 1.6, 4.5]].forEach(([r, h, y], i) => {
    const g = new THREE.ConeGeometry(r, h, 8); g.translate(0, y, 0); parts.push([g, i % 2 ? '#1f5a3e' : '#24664a']);
    const sn = new THREE.ConeGeometry(r * 0.72, h * 0.32, 8); sn.translate(0, y + h * 0.36, 0); parts.push([sn, '#e8eefc']);
  });
  return merge(parts);
}

// Spruces: thick beyond the banks, a few on the track to steer round. Some carry string lights.
function spruces(hill) {
  const r = rng(hill.n * 101), list = [];
  for (const o of hill.obst) if (o.kind === 'kuusi') list.push([o.s, o.x, 1]);
  const mound = (s, x) => (hill.tunnels || []).some(t => s > t.s - 3 && s < t.s + t.len + 3 && Math.abs(x) < hill.width / 2 + MOUND + 2) ||
    (bermAt(hill, s, x) > 0.2 && Math.abs(x) < hill.width / 2 + 14);   // and none up a berm, where a sled may ride (v6)
  for (let s = -30; s < hill.total; s += 3) {
    // x is measured straight across, so on a bend the same x is nearer the track: further out there (v6).
    const wide = 1 / Math.cos(courseDir(hill, s));
    for (const side of [-1, 1]) {
      if (r() < 0.55) list.push([s + r() * 3, side * (hill.width / 2 + 3 + r() * 6) * wide, 0.8 + r() * 0.6]);
      if (r() < 0.5) list.push([s + r() * 3, side * (hill.width / 2 + 10 + r() * 50) * wide, 0.9 + r() * 0.9]);
    }
  }
  for (let i = list.length - 1; i >= 0; i--) if (list[i][2] !== 1 && mound(list[i][0], list[i][1])) list.splice(i, 1);
  const m = new THREE.InstancedMesh(spruceGeometry(), lambert(), list.length), o = new THREE.Object3D(), lights = [];
  list.forEach(([s, x, k], i) => {
    const [X, Y, Z] = hillPoint(hill, s, x, baseAt(hill, Math.max(0, s)) + bankAt(hill, x) * (Math.abs(x) > 30 ? 0.6 : 1) + bermAt(hill, Math.max(0, s), x) - 0.1);
    o.position.set(X, Y, Z); o.scale.setScalar(k); o.rotation.y = r() * TAU; o.updateMatrix(); m.setMatrixAt(i, o.matrix);
    if (Math.abs(x) < 26 && r() < 0.45) {
      for (let j = 0; j < 14; j++) {
        const h = 1.2 + j * 0.24, a = j * 2.1, rad = (2.2 - j * 0.12) * k * 0.95;
        lights.push([X + Math.cos(a) * rad, Y + h * k, Z + Math.sin(a) * rad]);
      }
    }
  });
  const g = new THREE.Group();
  g.add(m, glowPoints(lights, i => ['#ff5050', '#ffd84a', '#5cff8a', '#5ab4ff', '#ff8af0'][(i * 7) % 5], 0.32));
  return g;
}

function rocksAndSnowmen(hill) {
  const parts = [];
  for (const o of hill.obst) {
    const y = snowAt(hill, o.s, o.x), [X, , Z] = hillPoint(hill, o.s, o.x, 0);
    if (o.kind === 'kivi') {
      const g = new THREE.DodecahedronGeometry(0.9); g.scale(1, 0.65, 1); g.translate(X, y + 0.35, Z); parts.push([g, '#5d6475']);
      const cap = new THREE.SphereGeometry(0.75, 8, 4, 0, TAU, 0, Math.PI / 2); cap.scale(1, 0.4, 1); cap.translate(X, y + 0.7, Z); parts.push([cap, '#eef3ff']);
    } else if (o.kind === 'lumiukko') {
      [[0.55, 0.5], [0.42, 1.2], [0.3, 1.75]].forEach(([r, h]) => { const g = new THREE.SphereGeometry(r, 10, 8); g.translate(X, y + h, Z); parts.push([g, '#f6f9ff']); });
      const nose = new THREE.ConeGeometry(0.06, 0.32, 6); nose.rotateX(Math.PI / 2); nose.translate(X, y + 1.78, Z + 0.4); parts.push([nose, '#ff7a1a']);
      const hat = new THREE.CylinderGeometry(0.22, 0.22, 0.34, 10); hat.translate(X, y + 2.15, Z); parts.push([hat, '#1a1a22']);
      const brim = new THREE.CylinderGeometry(0.34, 0.34, 0.04, 12); brim.translate(X, y + 1.98, Z); parts.push([brim, '#1a1a22']);
      const sc = new THREE.TorusGeometry(0.33, 0.07, 6, 12); sc.rotateX(Math.PI / 2); sc.translate(X, y + 1.5, Z); parts.push([sc, '#d42a2a']);
    }
  }
  return parts.length ? new THREE.Mesh(merge(parts), lambert()) : new THREE.Group();
}

// Lanterns along both edges every 24 m: a post and a warm light.
function lanterns(hill) {
  const parts = [], lights = [];
  for (let s = 10; s < hill.len + 40; s += 24) {
    if ((hill.tunnels || []).some(t => s > t.s - 3 && s < t.s + t.len + 3)) continue;   // the tunnel has its own lamps
    for (const side of [-1, 1]) {
      if (bermAt(hill, s, side * (hill.width / 2 + 1.2)) > 0.3) continue;   // nor up a berm (v6)
      const x = side * (hill.width / 2 + 1.2), y = snowAt(hill, s, x), [X, , Z] = hillPoint(hill, s, x, 0);
      const g = new THREE.CylinderGeometry(0.06, 0.08, 1.6, 6); g.translate(X, y + 0.8, Z); parts.push([g, '#2a2a33']);
      const b = new THREE.BoxGeometry(0.3, 0.36, 0.3); b.translate(X, y + 1.75, Z); parts.push([b, '#3a3a44']);
      lights.push([X, y + 1.75, Z]);
    }
  }
  const g = new THREE.Group();
  g.add(new THREE.Mesh(merge(parts), lambert()), glowPoints(lights, () => '#ffc85a', 0.7));
  return g;
}

// The finish: two posts and a banner, "MAALI", with lights.
function finishArch(hill) {
  const s = hill.len, y = baseAt(hill, s), half = hill.width / 2 + 0.5, parts = [], lights = [];
  for (const side of [-1, 1]) {
    const [X, , Z] = hillPoint(hill, s, side * half, 0), g = new THREE.CylinderGeometry(0.18, 0.18, 5, 8); g.translate(X, y + 2.5, Z); parts.push([g, '#b02030']);
  }
  const grp = new THREE.Group();
  grp.add(new THREE.Mesh(merge(parts), lambert()));
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 96;
  const cx = cv.getContext('2d');
  cx.fillStyle = '#b02030'; cx.fillRect(0, 0, 512, 96);
  cx.fillStyle = '#fff'; cx.font = '700 64px system-ui,sans-serif'; cx.textAlign = 'center'; cx.textBaseline = 'middle'; cx.fillText('MAALI', 256, 52);
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const banner = new THREE.Mesh(new THREE.PlaneGeometry(half * 2, half * 2 * 96 / 512), new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide, fog: false }));
  const [X, , Z] = hillPoint(hill, s, 0, 0);
  banner.position.set(X, y + 4.6, Z); grp.add(banner);
  for (let i = 0; i <= 16; i++) lights.push([X - half + i * half / 8, y + 5.35, Z + 0.05]);
  grp.add(glowPoints(lights, i => (i % 2 ? '#ffd84a' : '#ffffff'), 0.4));
  return grp;
}

// The tunnels (v6): a vault through a mound of snow. Inside, straight walls and a round roof of
// dark rock with lamps along its top; outside, the snowy mound; at each mouth, the face between
// them with a ring of lights. Its walls and roof are where world.js stops the sled (WALL, ROOF).
const MOUND = 8, WALL_UP = 2.6;
function tunnels(hill) {
  const grp = new THREE.Group();
  if (!(hill.tunnels || []).length) return grp;
  const pos = [], col = [], c = new THREE.Color(), lights = [], rim = [];
  const tri = (a, b, d, hex) => { c.set(hex); for (const p of [a, b, d]) { pos.push(...p); col.push(c.r, c.g, c.b); } };
  const quad = (a, b, d, e, hex) => { tri(a, b, d, hex); tri(b, e, d, hex); };
  const W = hill.width / 2 + WALL, N = 14;
  // The inside's cross-section, left foot to right foot: up the wall, over the roof, down the wall.
  const inner = [[-W, 0], [-W, WALL_UP / 2]];
  for (let i = 0; i <= N; i++) { const a = Math.PI * i / N; inner.push([-W * Math.cos(a), WALL_UP + (ROOF - WALL_UP) * Math.sin(a)]); }
  inner.push([W, WALL_UP / 2], [W, 0]);
  // The mound's, as many points, over the banks.
  const O = W + MOUND, outer = inner.map((_, i) => {
    const x = -O * Math.cos(Math.PI * i / (inner.length - 1)), m = Math.cos(Math.PI / 2 * x / O);
    return [x, bankAt(hill, x) + (ROOF + 2.2) * m * m - 0.2];
  });
  const at = (s, [x, y]) => hillPoint(hill, s, x, baseAt(hill, s) + y);
  for (const t of hill.tunnels) {
    const s1 = t.s + t.len, rows = [];
    for (let s = t.s; s < s1; s += 2) rows.push(s);
    rows.push(s1);
    for (let r = 0; r < rows.length - 1; r++) {
      const a = rows[r], b = rows[r + 1], dark = r % 2 ? '#7484ab' : '#6a7aa2';
      for (let i = 0; i < inner.length - 1; i++) {
        quad(at(a, inner[i]), at(a, inner[i + 1]), at(b, inner[i]), at(b, inner[i + 1]), i < 2 || i > inner.length - 3 ? '#5d6b92' : dark);
        quad(at(a, outer[i]), at(a, outer[i + 1]), at(b, outer[i]), at(b, outer[i + 1]), '#e6edfb');
      }
    }
    for (const s of [t.s, s1]) {
      for (let i = 0; i < inner.length - 1; i++) quad(at(s, inner[i]), at(s, inner[i + 1]), at(s, outer[i]), at(s, outer[i + 1]), '#8d9abb');
      for (let i = 1; i < inner.length - 1; i++) rim.push(at(s, [inner[i][0] * 1.02, inner[i][1] + 0.15]));
    }
    for (let s = t.s + 6; s < s1 - 2; s += 10) lights.push(at(s, [0, ROOF - 0.15]));
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
  g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(col), 3));
  g.computeVertexNormals();
  grp.add(new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide })));
  grp.add(glowPoints(lights, () => '#ffd27a', 0.35), glowPoints(rim, i => ['#ff4848', '#ffd23a', '#48ff7a', '#4aa8ff'][i % 4], 0.3));
  return grp;
}

// Presents: a wrapped box with a ribbon, floating and turning. Each phone hides those it took.
function gifts(hill) {
  const grp = new THREE.Group(), cols = ['#d42a2a', '#2a7ad4', '#2aa85a', '#d4a82a', '#a82ad4'];
  grp.userData.byId = {};
  for (const gf of hill.gifts) {
    const k = gf.big ? 1.4 : 0.9, col = cols[gf.id % cols.length], parts = [];
    const b = new THREE.BoxGeometry(0.7 * k, 0.6 * k, 0.7 * k); parts.push([b, col]);
    const r1 = new THREE.BoxGeometry(0.72 * k, 0.62 * k, 0.14 * k); parts.push([r1, '#fff3c0']);
    const r2 = new THREE.BoxGeometry(0.14 * k, 0.62 * k, 0.72 * k); parts.push([r2, '#fff3c0']);
    const bow = new THREE.TorusGeometry(0.14 * k, 0.05 * k, 6, 10); bow.translate(0, 0.38 * k, 0); parts.push([bow, '#fff3c0']);
    const m = new THREE.Mesh(merge(parts), new THREE.MeshLambertMaterial({ vertexColors: true, emissive: 0x222222 }));
    const [X, , Z] = hillPoint(hill, gf.s, gf.x, 0);
    m.position.set(X, snowAt(hill, gf.s, gf.x) + gf.up, Z);
    m.userData.y0 = m.position.y; m.userData.ph = gf.id * 1.7;
    grp.add(m); grp.userData.byId[gf.id] = m;
  }
  return grp;
}

// ---- A sled and its rider ----
// The pulkka is a red plastic sled; the rider sits in it, dressed in the outfit's palette.
function makeRig(o) {
  const rig = new THREE.Group(), pivot = new THREE.Group(), lean = new THREE.Group(), sled = new THREE.Group(), rider = new THREE.Group();
  rig.rotation.order = 'YXZ';   // heading first, then the slope, so a turned sled still tips along itself
  rig.add(pivot); pivot.add(lean); lean.add(sled, rider);
  const mat = hex => new THREE.MeshLambertMaterial({ color: new THREE.Color(hex) });
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.14, 1.15), mat('#d0202c')); body.position.y = 0.07; sled.add(body);
  const nose = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.32, 0.18), mat('#d0202c')); nose.position.set(0, 0.2, -0.6); nose.rotation.x = -0.5; sled.add(nose);
  for (const sx of [-1, 1]) { const rail = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.18, 1.1), mat('#a8141f')); rail.position.set(sx * 0.31, 0.17, 0); sled.add(rail); }
  const rope = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.02, 4, 10, Math.PI), mat('#f2e3b0')); rope.position.set(0, 0.36, -0.68); sled.add(rope);
  // Rider: legs forward along the sled, the body upright, arms to the sides holding on.
  const P = {};
  P.legs = new THREE.Group(); rider.add(P.legs);
  for (const sx of [-1, 1]) {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.085, 0.09, 0.72, 7), mat(o.bottom)); leg.rotation.x = Math.PI / 2; leg.position.set(sx * 0.12, 0.25, -0.18); P.legs.add(leg);
    const boot = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.16, 0.2), mat(o.shoe || '#222')); boot.position.set(sx * 0.12, 0.27, -0.58); P.legs.add(boot);
  }
  P.torso = new THREE.Group(); P.torso.position.set(0, 0.22, 0.22); rider.add(P.torso);
  const t = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.21, 0.55, 9), mat(o.top || '#2f6fd0')); t.position.y = 0.3; P.torso.add(t);
  if (o.stripe) { const st = new THREE.Mesh(new THREE.CylinderGeometry(0.195, 0.205, 0.08, 9), mat(o.stripe)); st.position.y = 0.2; P.torso.add(st); }
  P.arms = [];
  for (const sx of [-1, 1]) {
    const arm = new THREE.Group(); arm.position.set(sx * 0.21, 0.52, 0); P.torso.add(arm);
    const a = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.5, 6), mat(o.top || '#2f6fd0')); a.position.y = -0.25; arm.add(a);
    const mitt = new THREE.Mesh(new THREE.SphereGeometry(0.075, 7, 5), mat(o.mitt || o.stripe || '#e8e8e8')); mitt.position.y = -0.52; arm.add(mitt);
    arm.rotation.z = sx * 0.35; arm.rotation.x = -0.2;
    P.arms.push(arm);
  }
  P.head = new THREE.Group(); P.head.position.y = 0.72; P.torso.add(P.head);
  dressHead(P.head, o, mat);
  rig.userData = { pivot, lean, sled, rider, P, outfit: o.id };
  // A soft dark shadow under the sled, on the snow, so the height of a jump shows.
  const sh = new THREE.Mesh(new THREE.CircleGeometry(0.75, 16), new THREE.MeshBasicMaterial({ color: 0x0a1030, transparent: true, opacity: 0.35, depthWrite: false }));
  sh.rotation.x = -Math.PI / 2; rig.userData.shadow = sh;
  return rig;
}
// The head: a face and a beanie, or the costume's own (the Christmas costumes, #473).
function dressHead(h, o, mat) {
  const face = new THREE.Mesh(new THREE.SphereGeometry(0.15, 12, 9), mat(o.skin || '#f0c8a0')); h.add(face);
  const eye = new THREE.MeshBasicMaterial({ color: 0x1a1a1a });
  for (const sx of [-1, 1]) { const e = new THREE.Mesh(new THREE.SphereGeometry(0.018, 5, 4), eye); e.position.set(sx * 0.055, 0.02, -0.14); h.add(e); }
  const cap = (col, r, y) => { const c = new THREE.Mesh(new THREE.SphereGeometry(r, 12, 6, 0, TAU, 0, Math.PI / 2), mat(col)); c.position.y = y; h.add(c); return c; };
  const kind = o.head;
  if (kind === 'pukki' || kind === 'tonttu') {
    cap('#ffffff', 0.165, 0.02).scale.y = 0.35;
    const cone = new THREE.Mesh(new THREE.ConeGeometry(0.15, kind === 'tonttu' ? 0.42 : 0.3, 10), mat('#d42a2a')); cone.position.set(0, 0.2, 0.03); cone.rotation.x = 0.35; h.add(cone);
    const bob = new THREE.Mesh(new THREE.SphereGeometry(0.05, 6, 5), mat('#ffffff')); bob.position.set(0, kind === 'tonttu' ? 0.4 : 0.33, 0.1); h.add(bob);
    if (kind === 'pukki') { const beard = new THREE.Mesh(new THREE.SphereGeometry(0.13, 10, 7, 0, TAU, Math.PI / 2, Math.PI / 2), mat('#f4f4f4')); beard.position.set(0, -0.04, -0.05); beard.scale.set(1, 1.4, 0.9); h.add(beard); }
  } else if (kind === 'poro') {
    for (const sx of [-1, 1]) {
      const a = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.025, 0.28, 5), mat('#5a3a1e')); a.position.set(sx * 0.1, 0.22, 0); a.rotation.z = -sx * 0.4; h.add(a);
      const b = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.02, 0.14, 5), mat('#5a3a1e')); b.position.set(sx * 0.17, 0.3, 0); b.rotation.z = sx * 0.6; h.add(b);
    }
    const n = new THREE.Mesh(new THREE.SphereGeometry(0.04, 7, 5), new THREE.MeshBasicMaterial({ color: 0xff2020 })); n.position.set(0, -0.02, -0.16); h.add(n);
  } else if (kind === 'lumiukko') {
    const brim = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.025, 12), mat('#1a1a22')); brim.position.y = 0.12; h.add(brim);
    const hat = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.2, 12), mat('#1a1a22')); hat.position.y = 0.23; h.add(hat);
    const n = new THREE.Mesh(new THREE.ConeGeometry(0.03, 0.14, 6), mat('#ff7a1a')); n.rotation.x = -Math.PI / 2; n.position.set(0, -0.01, -0.2); h.add(n);
  } else if (kind === 'pipari') {
    const sm = new THREE.Mesh(new THREE.TorusGeometry(0.06, 0.012, 4, 10, Math.PI), mat('#ffffff')); sm.rotation.z = Math.PI; sm.position.set(0, -0.04, -0.14); h.add(sm);
  } else {
    cap(o.pipo || o.hair || '#d42a2a', 0.16, 0.02);
    const bob = new THREE.Mesh(new THREE.SphereGeometry(0.055, 6, 5), mat(o.tupsu || '#ffffff')); bob.position.y = 0.18; h.add(bob);
  }
}

// Places a sled's rig: its place and heading on the hill, then the trick's turn, the lean, the pose.
function poseRig(rig, hill, sl, look) {
  const u = rig.userData;
  const [X, Y, Z] = hillPoint(hill, sl.s, sl.x, sl.y);
  rig.position.set(X, Y, Z);
  // The course's own heading here, and the sled's yaw from it.
  rig.rotation.set(0, 0, 0);
  rig.rotation.y = -worldDir(hill, sl.s, sl.yaw);
  // Nose follows the snow's slope on the ground; in the air the flight's.
  const slope = sl.air ? Math.atan2(sl.vy, Math.max(1, sl.v)) * 0.6 : Math.atan(groundAt(hill, sl.s + 0.5, sl.x) - groundAt(hill, sl.s - 0.5, sl.x));
  u.slope = (u.slope === undefined ? slope : u.slope + (slope - u.slope) * 0.25);
  rig.rotation.x = u.slope;
  // Sideways on a berm (v6) the sled leans with the snow.
  const side = sl.air ? 0 : Math.atan((groundAt(hill, sl.s, sl.x + 0.3) - groundAt(hill, sl.s, sl.x - 0.3)) / 0.6) * Math.cos(sl.yaw);
  u.side = (u.side === undefined ? side : u.side + (side - u.side) * 0.25);
  rig.rotation.z = u.side;
  u.pivot.position.y = 0.45; u.lean.position.y = -0.45;
  u.pivot.rotation.set(-sl.flip, sl.spin, sl.tilt + sl.roll);   // a front flip takes the nose down
  const P = u.P, grab = sl.grab;
  // Teräsmies: the rider lies stretched out over the sled, arms forward holding its nose.
  const gk = (u.gk || 0) + ((grab ? 1 : 0) - (u.gk || 0)) * 0.3; u.gk = gk;
  P.torso.rotation.x = -1.35 * gk; P.torso.position.y = 0.22 + 0.3 * gk; P.torso.position.z = 0.22 - 0.1 * gk;
  P.legs.rotation.x = 0.0; P.legs.position.y = 0.32 * gk; P.legs.position.z = 0.5 * gk;
  // A hand push (#517): both arms reach down to the snow and back.
  const push = sl.pushT > 0 ? Math.sin((1 - sl.pushT / 0.35) * Math.PI) : 0;
  P.arms.forEach((a, i) => { const sx = i ? 1 : -1; a.rotation.x = -0.2 - 2.6 * gk + (sl.air && !grab ? -0.9 : 0) + 1.1 * push; a.rotation.z = sx * (0.35 - 0.2 * gk + 0.25 * push); });
  // Shadow: on the snow under the sled.
  const gy = groundAt(hill, sl.s, sl.x), sh = u.shadow;
  sh.position.set(X, gy + 0.04, Z);
  const k = clamp(1 - (sl.y - gy) / 8, 0.3, 1); sh.scale.setScalar(k); sh.material.opacity = 0.35 * k;
}

function rigFor(sl) {
  let rig = V3.rigs.get(sl.id);
  const o = sl.outfit || {};
  if (rig && rig.userData.outfit !== o.id) { V3.scene.remove(rig, rig.userData.shadow); V3.rigs.delete(sl.id); rig = null; }
  if (!rig) { rig = makeRig(o); V3.scene.add(rig, rig.userData.shadow); V3.rigs.set(sl.id, rig); }
  return rig;
}

// ---- Each frame ----
function render3d(hill, sleds, me, dt, still) {
  if (!V3) return false;
  const R = V3.renderer, cv = R.domElement, w = cv.clientWidth || innerWidth, h = cv.clientHeight || innerHeight;
  if (w !== V3.w || h !== V3.h) { V3.w = w; V3.h = h; R.setSize(w, h, false); V3.camera.aspect = w / h; V3.camera.updateProjectionMatrix(); }
  if (V3.hill !== hill) { buildWorld(hill); V3.cam = null; }
  V3.t += dt;
  const live = new Set();
  for (const sl of sleds) { layTrail(hill, sl); const rig = rigFor(sl); poseRig(rig, hill, sl); rig.visible = rig.userData.shadow.visible = true; live.add(sl.id); }
  for (const [id, rig] of V3.rigs) if (!live.has(id)) { V3.scene.remove(rig, rig.userData.shadow); V3.rigs.delete(id); }
  // Presents this phone has taken are gone; the rest bob and turn.
  for (const id in V3.gifts.userData.byId) {
    const m = V3.gifts.userData.byId[id];
    m.visible = !me || !me.gifts.includes(+id);
    if (!still) { m.rotation.y = V3.t * 1.2 + m.userData.ph; m.position.y = m.userData.y0 + Math.sin(V3.t * 2 + m.userData.ph) * 0.12; }
  }
  const cam = V3.camera;
  let dir;
  if (me && V3.view === 'fp') dir = eyeCamera(hill, me, cam);
  else dir = chaseCamera(hill, me, cam, dt, still);
  // A present right by the camera would fill the screen: it is left out until the camera has passed.
  for (const id in V3.gifts.userData.byId) { const m = V3.gifts.userData.byId[id]; if (m.visible && m.getWorldPosition(V3.v).distanceTo(cam.position) < (V3.view === 'fp' ? 1.2 : 4.5)) m.visible = false; }
  V3.sky.position.copy(cam.position);
  V3.moon.position.set(cam.position.x - 60, cam.position.y + 80, cam.position.z - 120); V3.moon.target.position.copy(cam.position);
  // Snow: falls and drifts, wrapping round a box in front of the camera.
  if (!still) {
    const p = V3.snow.geometry.attributes.position, a = p.array;
    for (let i = 0; i < a.length; i += 3) {
      a[i + 1] -= dt * (1.4 + (i % 7) * 0.12); a[i] += Math.sin(V3.t + i) * dt * 0.3;
      if (a[i + 1] < -6) a[i + 1] += 30;
    }
    p.needsUpdate = true;
  }
  V3.snow.visible = !V3.inTunnel;   // no snow falls under a tunnel's roof
  V3.snow.position.set(cam.position.x, cam.position.y - 8, cam.position.z + 8);
  V3.snow.rotation.y = -dir;
  // Santa crosses the sky every 25 s or so, far ahead.
  const st = V3.t % 26, sa = V3.santa;
  sa.visible = st < 12;
  if (sa.visible) {
    const f = st / 12;
    sa.position.set(cam.position.x + 320 - f * 640, cam.position.y + 95 + Math.sin(f * 9) * 4, cam.position.z - 380);
    sa.rotation.y = Math.PI;
  }
  R.render(V3.scene, cam);
  return true;
}

// The camera behind the sled along its heading (not turning with a spin or flip), a little above.
function chaseCamera(hill, me, cam, dt, still) {
  if (me) showRider(me, true);
  const d = me || { s: 0, x: 0, y: baseAt(hill, 0), yaw: 0, air: false };
  const dir = worldDir(hill, d.s, d.yaw * 0.6);
  const back = LAND ? 6.4 : 8.6, up = LAND ? 2.6 : 3.7;
  const [bs, bx0] = hillAhead(hill, d.s, d.x, dir, -back);
  // On a sharp bend the place behind the sled is off the track, among the spruces (v6): the camera
  // stays over the track, or no further out than the sled itself.
  const side = Math.max(Math.abs(d.x), hill.width / 2 + 0.8), bx = clamp(bx0, -side, side);
  const want = hillPoint(hill, bs, bx, Math.max(d.y, groundAt(hill, d.s, d.x)) + up);
  want[1] = Math.max(want[1], groundAt(hill, bs, bx) + 1.4);
  if (!V3.cam) V3.cam = want.slice();
  const k = still ? 1 : Math.min(1, dt * 6);
  // Height follows softly, but the faster the further off it is (#517: down a drop or a steep
  // stretch the sled falls metres in a moment, and a slow camera lost it under the screen's edge).
  const ky = still ? 1 : Math.min(1, dt * (3.5 + 1.5 * Math.abs(want[1] - V3.cam[1])));
  for (let i = 0; i < 3; i++) V3.cam[i] += (want[i] - V3.cam[i]) * (i === 1 ? ky : k);
  // In a tunnel or at its mouth the camera stays under the roof and inside the walls (v6).
  const cs = -V3.cam[2], tn = (hill.tunnels || []).find(t => cs > t.s - 6 && cs < t.s + t.len + 1);
  if (tn) {
    const lim = hill.width / 2 + WALL - 1.2, cx = centreX(hill, cs);
    V3.cam[0] = cx + clamp(V3.cam[0] - cx, -lim, lim);
    V3.cam[1] = Math.min(V3.cam[1], baseAt(hill, clamp(cs, tn.s, tn.s + tn.len)) + ROOF - 0.9);
  }
  V3.inTunnel = !!tn;
  cam.position.set(...V3.cam);
  const [ls, lx] = hillAhead(hill, d.s, d.x, dir, 9);
  cam.lookAt(...hillPoint(hill, ls, lx, Math.max(d.y - 1.5, groundAt(hill, ls, lx)) + 0.6));
  cam.fov = LAND ? 58 : 66; cam.updateProjectionMatrix();
  return dir;
}

// Through the rider's own eyes (#475): the camera sits in the head and turns with the sled, so a
// flip turns the whole view over and a spin round. The rider's body is hidden; the legs, the boots
// and the sled's nose stay in sight. A fall only shakes the view, not rolls it.
function eyeCamera(hill, me, cam) {
  const rig = rigFor(me), u = rig.userData;
  showRider(me, false);
  u.pivot.rotation.z = me.tilt * 0.6 + (me.fallT > 0 ? Math.sin(me.fallT * 18) * 0.12 : 0);
  rig.updateMatrixWorld(true);
  u.P.head.getWorldPosition(cam.position);
  u.pivot.getWorldQuaternion(cam.quaternion);
  cam.translateY(0.22); cam.translateZ(0.12);
  cam.rotateX(-0.26);   // eyes a little down the track
  cam.fov = LAND ? 64 : 78; cam.updateProjectionMatrix();
  V3.cam = null;   // the chase camera starts afresh when the view changes back
  V3.inTunnel = !!tunnelAt(hill, me.s);
  return worldDir(hill, me.s, me.yaw);
}
function showRider(sl, on) {
  const P = rigFor(sl).userData.P;
  P.torso.visible = on;
}

// A slow phone: measured over the first seconds of a run, below 27 frames a second it draws fewer
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

// Where a hill point shows on the screen, for the names over friends' sleds; null behind the camera.
function screenOf(hill, s, x, y) {
  if (!V3 || !V3.w) return null;
  const v = V3.v.set(...hillPoint(hill, s, x, y));
  const d = V3.camera.position.distanceTo(v);
  v.project(V3.camera);
  return v.z > 1 ? null : { x: (v.x + 1) / 2 * W, y: (1 - v.y) / 2 * H, d };
}
