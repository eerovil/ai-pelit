'use strict';
// Lattia on laavaa v1: the room drawn in 3D (#488). three.js renders the room, the furniture, the
// lava, the floats and the kids on the WebGL canvas #g under the 2D canvas #c, which keeps the
// HUD, the stick and the buttons (ui.js). This only reads the world each frame; nothing here
// changes how the round plays. A phone that cannot draw WebGL gets L3D.failed and a Finnish note.
window.L3D = { failed: false, build() {}, draw() {}, resize() {}, project() { return null; } };
(function () {
  const glc = document.getElementById('g');
  let pending = null;
  L3D.build = w => { pending = w; };
  (window.L3D_LIB || Promise.reject(new Error('no three'))).then(T => {
    let rd;
    try { rd = new T.WebGLRenderer({ canvas: glc, antialias: true }); } catch (e) { L3D.failed = true; return; }
    let pr = Math.min(devicePixelRatio || 1, 1.5);
    rd.setPixelRatio(pr);
    rd.shadowMap.enabled = true; rd.shadowMap.type = T.PCFSoftShadowMap;
    const scene = new T.Scene();
    scene.background = new T.Color('#1a0a06');
    const cam = new T.PerspectiveCamera(60, 1, 0.2, 80);
    const hemi = new T.HemisphereLight('#fff4e6', '#5a2a14', 1.6);
    scene.add(hemi);
    const sun = new T.DirectionalLight('#fff0dc', 1.9);
    sun.position.set(-5, 14, 8); sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024); sun.shadow.bias = -0.0008;
    Object.assign(sun.shadow.camera, { left: -9, right: 9, top: 8, bottom: -8, near: 2, far: 40 });
    scene.add(sun, sun.target);
    const glow = new T.PointLight('#ff6a1a', 0, 22, 1.4);   // the lava's light from below
    glow.position.set(0, 0.6, 0); scene.add(glow);

    // ---- Shared shapes and materials ----
    const box = new T.BoxGeometry(1, 1, 1);
    const ball = new T.SphereGeometry(1, 18, 12);
    const cyl = new T.CylinderGeometry(1, 1, 1, 20);
    const mats = new Map();
    const mat = (c, o) => {
      const key = c + JSON.stringify(o || {});
      if (!mats.has(key)) mats.set(key, new T.MeshStandardMaterial(Object.assign({ color: c, roughness: 0.75 }, o || {})));
      return mats.get(key);
    };
    function part(par, geo, c, x, y, z, sx, sy, sz, o) {
      const m = new T.Mesh(geo, typeof c === 'string' ? mat(c, o) : c);
      m.position.set(x, y, z); m.scale.set(sx, sy, sz); m.castShadow = true; m.receiveShadow = true;
      par.add(m); return m;
    }
    // A slab with a top at y: x/z centred, from y - h to y.
    const slab = (par, c, x, top, z, w, h, d, o) => part(par, box, c, x, top - h / 2, z, w, h, d, o);

    // ---- Textures drawn here (no files, no network) ----
    function canvasTex(n, paint) {
      const cv = document.createElement('canvas'); cv.width = cv.height = n;
      paint(cv.getContext('2d'), n);
      const t = new T.CanvasTexture(cv); t.wrapS = t.wrapT = T.RepeatWrapping; t.colorSpace = T.SRGBColorSpace;
      return t;
    }
    const lavaTex = canvasTex(256, (g, n) => {
      g.fillStyle = '#c81e00'; g.fillRect(0, 0, n, n);
      const r = rng(7);
      for (let i = 0; i < 70; i++) {
        const x = r() * n, y = r() * n, s = 10 + r() * 38;
        for (const [dx, dy] of [[0, 0], [n, 0], [-n, 0], [0, n], [0, -n]]) {
          const gr = g.createRadialGradient(x + dx, y + dy, 0, x + dx, y + dy, s);
          gr.addColorStop(0, i % 3 ? 'rgba(255,170,30,.9)' : 'rgba(255,240,120,.9)'); gr.addColorStop(1, 'rgba(255,80,0,0)');
          g.fillStyle = gr; g.beginPath(); g.arc(x + dx, y + dy, s, 0, TAU); g.fill();
        }
      }
      g.strokeStyle = 'rgba(120,20,0,.3)'; g.lineWidth = 2;
      for (let i = 0; i < 10; i++) { g.beginPath(); let x = r() * n, y = r() * n; g.moveTo(x, y); for (let k = 0; k < 4; k++) { x += (r() - 0.5) * 60; y += (r() - 0.5) * 60; g.lineTo(x, y); } g.stroke(); }
    });
    lavaTex.repeat.set(2, 1.5);
    const floorTex = canvasTex(256, (g, n) => {
      g.fillStyle = '#fff'; g.fillRect(0, 0, n, n);
      const r = rng(3);
      for (let i = 0; i < 8; i++) {
        g.fillStyle = `rgba(0,0,0,${0.04 + r() * 0.1})`; g.fillRect(0, i * n / 8, n, n / 8);
        g.fillStyle = 'rgba(0,0,0,.28)'; g.fillRect(0, i * n / 8, n, 2);
        const cut = r() * n; g.fillRect(cut, i * n / 8, 2, n / 8);
      }
    });
    floorTex.repeat.set(3, 3);

    // ---- The room: walls, floor, window and sill, a lamp; rebuilt for each room ----
    let roomG = null, roomLv = 0;
    const lavaM = new T.MeshStandardMaterial({ color: '#3a0800', emissive: '#ff5a10', emissiveMap: lavaTex, emissiveIntensity: 1.25, map: lavaTex, roughness: 0.5, transparent: true });
    const lava = new T.Mesh(new T.PlaneGeometry(ROOM_W, ROOM_D), lavaM);
    lava.rotation.x = -Math.PI / 2; lava.receiveShadow = true; scene.add(lava);
    const SILL_Y = 1.7, SILL_Z = Z0 + 0.22;
    function buildRoom(lv) {
      if (roomG) scene.remove(roomG);
      roomG = new T.Group(); roomLv = lv; scene.add(roomG);
      const R = ROOMS[lv - 1];
      const floorM = new T.MeshStandardMaterial({ color: R.floorWood, map: floorTex, roughness: 0.8 });
      const floor = new T.Mesh(new T.PlaneGeometry(ROOM_W, ROOM_D), floorM);
      floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; roomG.add(floor);
      const wallM = mat(R.wall, { roughness: 0.95 });
      const H3 = 7;
      scene.background = new T.Color(R.wall).multiplyScalar(0.5);
      part(roomG, box, wallM, 0, H3 / 2, Z0 - 0.1, ROOM_W + 0.4, H3, 0.2).castShadow = false;
      part(roomG, box, wallM, X0 - 0.1, H3 / 2, 0, 0.2, H3, ROOM_D + 0.2).castShadow = false;
      part(roomG, box, wallM, X1 + 0.1, H3 / 2, 0, 0.2, H3, ROOM_D + 0.2).castShadow = false;
      // Skirting, darker.
      part(roomG, box, '#5a3a22', 0, 0.08, Z0 + 0.01, ROOM_W, 0.16, 0.04);
      // The window, where kids that fell sit and watch.
      part(roomG, box, '#9fd4ff', 0, SILL_Y + 0.75, Z0 + 0.02, 4.2, 1.4, 0.02, { emissive: '#7fc4ff', emissiveIntensity: 0.6 });
      for (const x of [-2.15, 0, 2.15]) part(roomG, box, '#f6f1e6', x, SILL_Y + 0.75, Z0 + 0.05, 0.1, 1.5, 0.06);
      part(roomG, box, '#f6f1e6', 0, SILL_Y + 1.5, Z0 + 0.05, 4.4, 0.1, 0.06);
      part(roomG, box, '#f6f1e6', 0, SILL_Y - 0.04, SILL_Z - 0.02, 4.6, 0.08, 0.44);
      // Something on the walls for each room.
      if (lv === 1) {
        part(roomG, box, '#16181c', 4.0, 1.55, Z0 + 0.03, 1.7, 0.95, 0.05);   // the TV, beside the window
        part(roomG, box, '#c49a6c', -4.6, 2.2, Z0 + 0.03, 1.2, 0.8, 0.04);
        part(roomG, box, '#6aa3c9', -4.6, 2.2, Z0 + 0.06, 1.0, 0.6, 0.02);
      } else if (lv === 2) {
        part(roomG, box, '#ffcf5a', -4.0, 2.3, Z0 + 0.03, 1.0, 1.3, 0.03);
        part(roomG, box, '#ff7aa8', 4.2, 2.2, Z0 + 0.03, 1.2, 0.9, 0.03);
        part(roomG, ball, '#ffe066', 4.6, 2.8, Z0 + 0.05, 0.25, 0.25, 0.03);
      } else {
        for (const x of [-4.2, -1.6, 1.0]) part(roomG, box, '#e9e2d0', x, 2.55, Z0 + 0.25, 2.3, 0.8, 0.5);
        part(roomG, box, '#2b2b2b', -1.6, 0.92, -4.6, 0.6, 0.04, 0.4);   // hob
      }
      // The ceiling lamp's glow.
      part(roomG, ball, '#fff2c8', 0, 3.0, -0.6, 0.35, 0.2, 0.35, { emissive: '#ffe2a0', emissiveIntensity: 1 });
    }

    // ---- Furniture: each piece a group whose top is the piece's top ----
    const COL = {
      sofa: '#3f7f8c', sofaback: '#356f7b', armchair: '#b8574a', tvbench: '#6b4a32', table: '#8a5a34', shelf: '#7a5233',
      pouf: '#e0a040', cushion: '#d95d75', sidetable: '#a0703e', stool: '#c08a50', chest: '#7b4f2c',
      bed: '#5b7fc2', wardrobe: '#f2efe6', desk: '#e9d6b0', chair: '#e46c4a', toybox: '#4bb07a', beanbag: '#9b6be0',
      blocks: '#f2c230', horse: '#c8783c', counter: '#f5f2ea', fridge: '#e8eef2', ktable: '#b9895a', basket: '#c9a46a',
      dogbed: '#8b5a3c', cupboard: '#d9cfb6',
    };
    function legs(g, w, d, top, th, c) {
      const lw = 0.07, lh = top - th;
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) part(g, box, c, sx * (w / 2 - 0.08), lh / 2, sz * (d / 2 - 0.08), lw, lh, lw);
    }
    function pieceModel(p) {
      const g = new T.Group(), inner = new T.Group(); g.add(inner);
      const { w, d } = p, h = p.h0, c = COL[p.kind] || '#999';
      switch (p.kind) {
        case 'sofa': slab(inner, c, 0, h - 0.18, 0, w, h - 0.18, d); slab(inner, '#4f97a5', 0, h, 0.03, w - 0.1, 0.18, d - 0.12);
          for (const s of [-1, 1]) slab(inner, c, s * (w / 2 - 0.12), h + 0.15, 0, 0.24, h + 0.15, d); break;
        case 'sofaback': slab(inner, c, 0, h, 0, w, h, d); break;
        case 'armchair': slab(inner, c, 0, h - 0.15, 0, w, h - 0.15, d); slab(inner, '#cf6c5e', 0, h, 0.05, w - 0.3, 0.15, d - 0.3);
          for (const s of [-1, 1]) slab(inner, c, s * (w / 2 - 0.12), h + 0.18, 0, 0.24, h + 0.18, d);
          slab(inner, c, 0, h + 0.55, -d / 2 + 0.15, w, h + 0.55, 0.3); break;
        case 'table': case 'ktable': case 'desk': case 'sidetable':
          slab(inner, c, 0, h, 0, w, 0.08, d); legs(inner, w, d, h, 0.08, p.kind === 'desk' ? '#c9b48c' : '#5e3b20'); break;
        case 'stool': case 'chair':
          slab(inner, c, 0, h, 0, w, 0.07, d); legs(inner, w, d, h, 0.07, '#6b4426'); break;
        case 'pouf': part(inner, cyl, c, 0, h / 2, 0, w / 2, h, d / 2); part(inner, cyl, '#f0c070', 0, h - 0.01, 0, w / 2 - 0.05, 0.03, d / 2 - 0.05); break;
        case 'cushion': case 'dogbed': part(inner, ball, c, 0, h / 2, 0, w / 2, h / 2, d / 2);
          if (p.kind === 'dogbed') part(inner, ball, '#e8d2b0', 0, h * 0.8, 0, w / 2 - 0.15, h / 3, d / 2 - 0.15); break;
        case 'beanbag': part(inner, ball, c, 0, h / 2, 0, w / 2, h / 2, d / 2); break;
        case 'bed': slab(inner, '#7a5233', 0, h - 0.22, 0, w, h - 0.22, d); slab(inner, '#ffffff', 0, h - 0.05, 0, w - 0.1, 0.17, d - 0.1);
          slab(inner, c, 0.3, h, 0, w * 0.65, 0.06, d - 0.06); slab(inner, '#fff', -w / 2 + 0.4, h + 0.04, 0, 0.5, 0.1, d * 0.6);
          slab(inner, '#7a5233', -w / 2 + 0.06, h + 0.55, 0, 0.12, h + 0.55, d); break;
        case 'shelf': case 'wardrobe': case 'fridge': case 'cupboard':
          slab(inner, c, 0, h, 0, w, h, d);
          if (p.kind === 'shelf') for (let y = 0.4; y < h - 0.1; y += 0.45) {
            slab(inner, '#5e3b20', 0, y + 0.03, 0, w + 0.02, 0.05, d + 0.02);
            for (let i = 0; i < 4; i++) slab(inner, ['#c0392b', '#2e86c1', '#f1c40f', '#27ae60'][i], w / 2 + 0.005, y + 0.3, -d / 2 + 0.35 + i * 0.5, 0.02, 0.26, 0.12);
          } else {
            slab(inner, '#888', w / 2 + 0.01, h * 0.62, d * 0.15, 0.02, 0.3, 0.04);
            slab(inner, '#cfcfcf', w / 2 + 0.005, h * 0.5, 0, 0.01, 0.02, d - 0.05);
          }
          break;
        case 'counter': slab(inner, c, 0, h - 0.05, 0, w, h - 0.05, d); slab(inner, '#5a5f66', 0, h, 0, w + 0.04, 0.05, d + 0.04);
          for (let i = 0; i < 3; i++) slab(inner, '#e0dccf', -w / 3 + i * w / 3, h * 0.5, d / 2 + 0.01, w / 3 - 0.06, h - 0.2, 0.02); break;
        case 'tvbench': case 'chest': case 'toybox': case 'basket':
          slab(inner, c, 0, h, 0, w, h, d);
          slab(inner, p.kind === 'toybox' ? '#ffd23f' : '#3b2414', 0, h + 0.01, 0, w - 0.06, 0.02, d - 0.06); break;
        case 'blocks': {
          const cs = ['#e74c3c', '#3498db', '#2ecc71', '#f1c40f'];
          slab(inner, cs[p.i % 4], 0, h / 2, 0, w, h / 2, d); slab(inner, cs[(p.i + 1) % 4], 0, h, 0, w * 0.9, h / 2, d * 0.9); break;
        }
        case 'horse': slab(inner, c, 0, h, 0, w, 0.32, d * 0.7); slab(inner, '#9b5a2a', w / 2 - 0.1, h + 0.35, 0, 0.25, 0.5, 0.25);
          part(inner, box, '#9b5a2a', 0, 0.06, 0, w + 0.2, 0.08, d); for (const s of [-1, 1]) slab(inner, c, s * (w / 2 - 0.15), h - 0.32, 0, 0.08, h - 0.38, d * 0.5); break;
        default: slab(inner, c, 0, h, 0, w, h, d);
      }
      g.position.set(p.x, 0, p.z);
      g.userData.inner = inner;
      return g;
    }
    // Floats: their top at y 0, hanging down.
    const FCOL = { fcushion: '#e05a7a', book: '#2e6fd0', fbasket: '#c9a46a', tray: '#c0c6cc', duck: '#ffd23f' };
    function floatModel(f) {
      const g = new T.Group(), c = FCOL[f.kind] || '#ccc';
      if (f.kind === 'fcushion') part(g, ball, c, 0, -0.1, 0, f.w / 2, 0.12, f.d / 2);
      else if (f.kind === 'book') { slab(g, c, 0, 0, 0, f.w, 0.18, f.d); slab(g, '#fffbe8', 0.02, -0.03, 0, f.w - 0.04, 0.12, f.d + 0.01); }
      else if (f.kind === 'duck') { part(g, ball, c, 0, -0.12, 0, f.w / 2, 0.2, f.d / 2); part(g, ball, c, f.w * 0.3, 0.1, 0, 0.16, 0.16, 0.16); part(g, ball, '#ff8a1a', f.w * 0.3 + 0.15, 0.08, 0, 0.08, 0.04, 0.06); }
      else slab(g, c, 0, 0, 0, f.w, 0.2, f.d);
      scene.add(g);
      return g;
    }

    // ---- Kids ----
    function kidModel(col) {
      const g = new T.Group(), body = new T.Group(); g.add(body);
      const shirt = KID_COLORS[col % KID_COLORS.length], hair = HAIR[col % HAIR.length];
      const skin = '#f2c9a0', pants = '#33415c';
      const leg = s => { const piv = new T.Group(); piv.position.set(0, 0.42, s * 0.1); body.add(piv); part(piv, box, pants, 0, -0.2, 0, 0.13, 0.42, 0.13); part(piv, box, '#222', 0.03, -0.4, 0, 0.18, 0.06, 0.14); return piv; };
      const arm = s => { const piv = new T.Group(); piv.position.set(0, 0.72, s * 0.22); body.add(piv); part(piv, box, shirt, 0, -0.14, 0, 0.1, 0.3, 0.1); part(piv, ball, skin, 0, -0.32, 0, 0.06, 0.06, 0.06); return piv; };
      const parts = { ll: leg(-1), lr: leg(1), al: arm(-1), ar: arm(1) };
      part(body, box, shirt, 0, 0.58, 0, 0.24, 0.34, 0.36);
      part(body, ball, skin, 0, 0.86, 0, 0.16, 0.16, 0.16);
      part(body, ball, hair, -0.03, 0.92, 0, 0.165, 0.12, 0.165);
      part(body, ball, '#1a1a1a', 0.14, 0.88, -0.06, 0.025, 0.03, 0.025);
      part(body, ball, '#1a1a1a', 0.14, 0.88, 0.06, 0.025, 0.03, 0.025);
      scene.add(g);
      g.userData = { body, parts };
      return g;
    }
    const meMark = new T.Mesh(new T.ConeGeometry(0.12, 0.22, 12), new T.MeshBasicMaterial({ color: '#ffd84a' }));
    meMark.rotation.x = Math.PI; scene.add(meMark);
    // Bubbles on the lava.
    const bubbles = [];
    for (let i = 0; i < 14; i++) { const b = part(scene, ball, '#ffb020', 0, -5, 0, 0.1, 0.1, 0.1, { emissive: '#ff7a10', emissiveIntensity: 1.2 }); b.castShadow = false; bubbles.push(b); }

    // ---- What is built for the world on screen ----
    let built = null, pieces = [], floats = new Map(), kids = new Map();
    let camInit = false, lastClock = 0;
    const look = new T.Vector3(), want = new T.Vector3(), wantLook = new T.Vector3();
    function build(w) {
      if (built === w) return;
      built = w;
      if (roomLv !== w.level) buildRoom(w.level);
      for (const g of pieces) scene.remove(g);
      pieces = w.pieces.map(p => { const g = pieceModel(p); scene.add(g); return g; });
      for (const g of floats.values()) scene.remove(g);
      floats = new Map();
      for (const g of kids.values()) scene.remove(g);
      kids = new Map();
      camInit = false;
    }
    L3D.build = build;
    if (pending) build(pending);

    // ---- The camera: behind and above the kid it follows, the same way round always ----
    function camera(w, me, clock) {
      const dt = Math.min(0.1, Math.max(0, clock - lastClock)); lastClock = clock;
      const land = glc.clientWidth > glc.clientHeight;
      let f = me && !me.out ? me : null;
      if (!f && w.kids.length && w.ph !== 'count') f = w.kids.filter(k => !k.out).sort((a, b) => a.i - b.i)[0] || null;
      if (f && (me || w.ph !== 'count')) {
        wantLook.set(clamp(f.dx, X0 + 3, X1 - 3), Math.max(0, f.dy) + 0.4, clamp(f.dz - 0.9, Z0 + 2.6, Z1 - 1.5));
        if (land) { cam.fov = 50; want.set(wantLook.x, wantLook.y + 6.2, wantLook.z + 5.4); }
        else { cam.fov = 62; want.set(wantLook.x, wantLook.y + 9.6, wantLook.z + 6.2); }
      } else {
        // The whole room: the menu, the countdown alone with no kid, or nobody left.
        wantLook.set(0, 0.3, -0.8);
        if (land) { cam.fov = 50; want.set(Math.sin(clock * 0.15) * 1.5, 9, 9); }
        else { cam.fov = 64; want.set(Math.sin(clock * 0.15) * 1.2, 14.5, 10.5); }
      }
      const k = camInit ? 1 - Math.exp(-dt * 5) : 1;
      cam.position.lerp(want, k); look.lerp(wantLook, k);
      cam.lookAt(look);
      cam.updateProjectionMatrix();
      camInit = true;
    }

    // ---- Each frame ----
    function poseKid(g, k, rt, clock, w) {
      const u = g.userData, P = u.parts;
      let x = k.dx, y = k.dy, z = k.dz, face = k.df, sit = false;
      if (k.out) {
        const t = rt - k.outRt;
        if (t < 0.9) { x = k.fellX; z = k.fellZ; y = lavaAt(rt) - t * 1.2; }
        else {
          // Out: on the windowsill, watching the rest.
          const outs = w.kids.filter(o => o.out && rt - o.outRt >= 0.9).sort((a, b) => a.outRt - b.outRt);
          const n = outs.indexOf(k), m = outs.length;
          x = (n - (m - 1) / 2) * 0.5; y = SILL_Y - 0.42; z = SILL_Z + 0.1; face = Math.PI / 2; sit = true;
        }
      }
      g.visible = y > lavaAt(rt) - 1.1;
      g.position.set(x, y, z);
      g.rotation.y = -face;
      const sp = Math.hypot(k.vx, k.vz), air = !k.ground && !k.out && Math.abs(k.vy) > 0.3;
      const ph = clock * 14, sw = air ? 0 : Math.min(1, sp / RUN) * 0.8;
      if (sit) {
        P.ll.rotation.z = P.lr.rotation.z = Math.PI / 2 - 0.2 + Math.sin(clock * 3 + k.i) * 0.15;
        P.al.rotation.x = -0.3; P.ar.rotation.x = 0.3; P.al.rotation.z = P.ar.rotation.z = Math.sin(clock * 5 + k.i) * 0.6 + 0.4;
      } else if (air) {
        P.ll.rotation.z = 0.6; P.lr.rotation.z = -0.3;
        P.al.rotation.z = P.ar.rotation.z = 0; P.al.rotation.x = -2.4; P.ar.rotation.x = 2.4;
      } else {
        P.ll.rotation.z = Math.sin(ph) * sw; P.lr.rotation.z = -Math.sin(ph) * sw;
        P.al.rotation.x = -0.15; P.ar.rotation.x = 0.15;
        P.al.rotation.z = -Math.sin(ph) * sw; P.ar.rotation.z = Math.sin(ph) * sw;
      }
      if (k.dash > 0 && !k.out) { P.al.rotation.z = P.ar.rotation.z = 1.5; u.body.rotation.z = -0.25; }
      else u.body.rotation.z = k.stun > 0 && !k.out ? Math.sin(clock * 30) * 0.25 : 0;
      // Sinking into the lava: flailing.
      u.body.rotation.x = k.out && !sit ? Math.sin(clock * 20) * 0.3 : 0;
    }
    let tuneT = 0, tuneN = 0, tuned = 0, frameN = 0;
    function tune(dt) {
      // A slow phone: first fewer pixels, then no shadows (the pixels decide a cheap phone's speed).
      if (tuned >= 2 || dt <= 0) return;
      tuneT += dt; tuneN++;
      if (tuneT < 2.5) return;
      const fps = tuneN / tuneT; tuneT = 0; tuneN = 0;
      if (fps > 45) { tuned = 2; return; }
      if (tuned === 0 && pr > 1) { pr = 1; rd.setPixelRatio(pr); resize(); tuned = 1; return; }
      rd.shadowMap.enabled = false; sun.castShadow = false;
      scene.traverse(o => { if (o.material) o.material.needsUpdate = true; });
      tuned = 2;
    }
    function resize() {
      const w = glc.clientWidth || innerWidth, h = glc.clientHeight || innerHeight;
      rd.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix();
    }
    L3D.resize = resize; resize();
    let prevClock = 0;
    L3D.draw = (w, me, clock) => {
      if (built !== w) build(w);
      const dt = clock - prevClock; prevClock = clock;
      // The menu draws at half rate: it only drifts.
      frameN++;
      if (!w.kids.length && frameN % 2) return;
      tune(dt);
      const rt = w.rt, L = lavaAt(rt), on = rt >= 0;
      // The lava: comes up through the floor at the start, then rises and moves slowly.
      const fade = on ? Math.min(1, rt / 0.6) : 0;
      lava.visible = fade > 0; lavaM.opacity = fade;
      lava.position.y = L;
      lavaTex.offset.set(clock * 0.015, Math.sin(clock * 0.2) * 0.03);
      lavaM.emissiveIntensity = 1.1 + Math.sin(clock * 2.2) * 0.15;
      glow.intensity = fade * (14 + Math.sin(clock * 3) * 2);
      glow.position.y = L + 0.5;
      // Furniture: sinking, and shaking while it wobbles.
      w.pieces.forEach((p, i) => {
        const g = pieces[i]; if (!g) return;
        const top = topOf(p, rt), wob = wobbleOf(p, rt), inner = g.userData.inner;
        g.position.y = top - p.h0;
        g.visible = top > L - 2.5;
        const s = rt < p.sinkAt ? wob : 1;
        // A sinking piece tips over its long side as it goes under (tipOf in world.js).
        const tip = tipOf(p, rt), long = p.w >= p.d;
        inner.rotation.z = Math.sin(clock * 19 + i) * 0.035 * s + (long ? 0 : tip);
        inner.rotation.x = Math.cos(clock * 17 + i * 2) * 0.03 * s + (long ? tip : 0);
        inner.position.x = Math.sin(clock * 23 + i) * 0.02 * s;
      });
      // Floats.
      const list = w.kids.length ? floatsAt(w, rt) : [], seenF = new Set();
      for (const f of list) {
        let g = floats.get(f.k);
        if (!g) { g = floatModel(f); floats.set(f.k, g); }
        g.position.set(f.x, f.top, f.z); g.rotation.y = Math.sin(clock + f.k) * 0.1; seenF.add(f.k);
      }
      for (const [k, g] of floats) if (!seenF.has(k)) { scene.remove(g); floats.delete(k); }
      // Bubbles: popping up at spots drawn from time.
      bubbles.forEach((b, i) => {
        const T2 = 1.6, t = (clock + i * 0.37) % T2, n = Math.floor((clock + i * 0.37) / T2) * 14 + i;
        const r = rng(n * 977 + 13);
        b.visible = on && fade >= 1;
        b.position.set(X0 + 0.5 + r() * (ROOM_W - 1), L + 0.02, Z0 + 0.5 + r() * (ROOM_D - 1));
        const s = Math.sin(Math.min(1, t / T2) * Math.PI) * (0.06 + r() * 0.12);
        b.scale.set(s, s * 0.6, s);
      });
      // Kids.
      const ids = new Set();
      for (const k of w.kids) {
        let g = kids.get(k.id);
        if (!g || g.userData.col !== k.col) { if (g) scene.remove(g); g = kidModel(k.col); g.userData.col = k.col; kids.set(k.id, g); }
        poseKid(g, k, rt, clock, w); ids.add(k.id);
      }
      for (const [id, g] of kids) if (!ids.has(id)) { scene.remove(g); kids.delete(id); }
      meMark.visible = !!(me && !me.out && w.kids.length > 1);
      if (meMark.visible) meMark.position.set(me.dx, me.dy + KID_H + 0.32 + Math.sin(clock * 5) * 0.05, me.dz);
      camera(w, me, clock);
      sun.target.position.set(look.x, 0, look.z); sun.position.set(look.x - 5, 14, look.z + 8);
      rd.render(scene, cam);
    };
    const v = new T.Vector3();
    L3D.tilt = i => pieces[i] ? [pieces[i].userData.inner.rotation.x, pieces[i].userData.inner.rotation.z] : null;
    L3D.project = (x, y, z) => {
      v.set(x, y, z).project(cam);
      if (v.z > 1 || v.z < -1) return null;
      return [(v.x + 1) / 2 * (glc.clientWidth || innerWidth), (1 - v.y) / 2 * (glc.clientHeight || innerHeight)];
    };
  }).catch(() => { L3D.failed = true; });
})();
