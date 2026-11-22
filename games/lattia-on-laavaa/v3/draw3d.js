'use strict';
// Lattia on laavaa v3: the room drawn in 3D (#488; Koko talo's three floors, #526). three.js renders the room, the furniture, the
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
    // Koko talo's lava sea once the house goes under (#526): wide, to the horizon.
    const seaTex = lavaTex.clone(); seaTex.needsUpdate = true; seaTex.repeat.set(11, 11);
    const seaM = lavaM.clone(); seaM.map = seaM.emissiveMap = seaTex; seaM.transparent = false;
    const sea = new T.Mesh(new T.PlaneGeometry(90, 90), seaM);
    sea.rotation.x = -Math.PI / 2; sea.receiveShadow = true; sea.visible = false; scene.add(sea);
    const SKY = new T.Color('#f2a27a');
    const SILL_Y = 1.7, SILL_Z = Z0 + 0.22;
    function buildRoom(lv) {
      if (roomG) scene.remove(roomG);
      roomG = new T.Group(); roomLv = lv; scene.add(roomG);
      const R = ROOMS[lv - 1];
      floorG = null; doors = []; skyG = null; balloon = null;
      if (R.floors) return buildHouse(R);
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

    // ---- Koko talo (#526): three floors, each a group the cut-away hides when the followed kid is
    // below it, like a doll's house. The steps, floors, stair walls and doors are talo.js's statics.
    let floorG = null, doors = [], skyG = null, balloon = null, houseBg = null;
    const BALLOON = { x: 0, y: 8.4, z: Z0 - 2.4 };
    function window3d(par, y0) {
      part(par, box, '#9fd4ff', 0, y0 + SILL_Y + 0.75, Z0 + 0.02, 4.2, 1.4, 0.02, { emissive: '#7fc4ff', emissiveIntensity: 0.6 });
      for (const x of [-2.15, 0, 2.15]) part(par, box, '#f6f1e6', x, y0 + SILL_Y + 0.75, Z0 + 0.05, 0.1, 1.5, 0.06);
      part(par, box, '#f6f1e6', 0, y0 + SILL_Y + 1.5, Z0 + 0.05, 4.4, 0.1, 0.06);
      part(par, box, '#f6f1e6', 0, y0 + SILL_Y - 0.04, SILL_Z - 0.02, 4.6, 0.08, 0.44);
    }
    function buildHouse(R) {
      houseBg = new T.Color(R.wall).multiplyScalar(0.5);
      scene.background = houseBg;
      floorG = R.floors.map(() => { const g = new T.Group(); roomG.add(g); return g; });
      const woodM = R.floors.map(F => new T.MeshStandardMaterial({ color: F.floorWood, map: floorTex, roughness: 0.8 }));
      const floor = new T.Mesh(new T.PlaneGeometry(ROOM_W, ROOM_D), woodM[0]);
      floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; floorG[0].add(floor);
      // Each floor's walls (back, left, right), skirting and window; the roof has a low railing.
      for (let f = 0; f < 2; f++) {
        const g = floorG[f], y0 = f * FLOOR_H, H = FLOOR_H, wm = mat(R.floors[f].wall, { roughness: 0.95 });
        part(g, box, wm, 0, y0 + H / 2, Z0 - 0.1, ROOM_W + 0.4, H, 0.2).castShadow = false;
        part(g, box, wm, X0 - 0.1, y0 + H / 2, 0, 0.2, H, ROOM_D + 0.2).castShadow = false;
        part(g, box, wm, X1 + 0.1, y0 + H / 2, 0, 0.2, H, ROOM_D + 0.2).castShadow = false;
        part(g, box, '#5a3a22', 0, y0 + 0.08, Z0 + 0.01, ROOM_W, 0.16, 0.04);
        window3d(g, y0);
      }
      // Downstairs: the TV and a picture; upstairs: posters and a star.
      part(floorG[0], box, '#16181c', 4.0, 1.55, Z0 + 0.03, 1.7, 0.95, 0.05);
      part(floorG[0], box, '#c49a6c', -4.0, 2.2, Z0 + 0.03, 1.2, 0.8, 0.04);
      part(floorG[0], box, '#6aa3c9', -4.0, 2.2, Z0 + 0.06, 1.0, 0.6, 0.02);
      part(floorG[1], box, '#ffcf5a', -4.0, FLOOR_H + 2.2, Z0 + 0.03, 1.0, 1.1, 0.03);
      part(floorG[1], box, '#ff7aa8', 4.2, FLOOR_H + 2.2, Z0 + 0.03, 1.2, 0.9, 0.03);
      const roofY = FLOOR_H * 2;
      for (const [x, z, w, d] of [[0, Z0 + 0.05, ROOM_W, 0.1], [0, Z1 - 0.05, ROOM_W, 0.1], [X0 + 0.05, 0, 0.1, ROOM_D], [X1 - 0.05, 0, 0.1, ROOM_D]]) {
        part(floorG[2], box, '#d8dde2', x, roofY + 0.9, z, w, 0.08, d);
        const n = Math.round(Math.max(w, d) / 1.2);
        for (let i = 0; i <= n; i++) {
          const t = i / n - 0.5;
          part(floorG[2], box, '#c3c9cf', w > d ? x + t * w : x, roofY + 0.45, w > d ? z : z + t * d, 0.06, 0.9, 0.06);
        }
      }
      // The outer walls under the roof's edge, so the house reads as a house from the roof.
      for (const f of [0, 1]) part(floorG[2], box, '#c86b4a', 0, f * FLOOR_H + FLOOR_H - 0.1, Z0 - 0.21, ROOM_W + 0.6, 0.2, 0.02).castShadow = false;
      // The statics: steps, stair walls (split at the floor above), doors and the floors' slabs.
      for (const st of houseStatics()) {
        if (st.kind === 'step') {
          const g = floorG[st.floor];
          slab(g, '#9a6a3c', st.x, st.top, st.z, st.w, st.top - st.bot, st.d);
          slab(g, '#c79a68', st.x, st.top + 0.005, st.z + st.d / 2 - 0.04, st.w, 0.03, 0.08);   // the nose
        } else if (st.kind === 'rail') {
          const mid = st.bot + FLOOR_H - SLAB;
          slab(floorG[st.floor], '#f3ede0', st.x, mid, st.z, st.w, mid - st.bot, st.d);
          slab(floorG[st.floor + 1], '#f3ede0', st.x, st.top, st.z, st.w, st.top - mid - SLAB, st.d);
          slab(floorG[st.floor + 1], '#8a5a34', st.x, st.top + 0.04, st.z, st.w + 0.06, 0.08, st.d);
        } else if (st.kind === 'door') {
          // Hinged on the wall side; swings out into the room when it opens.
          const left = st.stair === 0, piv = new T.Group(), hx = left ? st.x - st.w / 2 : st.x + st.w / 2;
          piv.position.set(hx, st.bot, st.z); floorG[st.floor].add(piv);
          const s = left ? 1 : -1, h = st.top - st.bot;
          part(piv, box, '#b5793f', s * st.w / 2, h / 2, 0, st.w, h, st.d);
          part(piv, box, '#8e5c2c', s * st.w / 2, h * 0.72, st.d / 2 + 0.005, st.w - 0.25, h * 0.3, 0.01);
          part(piv, box, '#8e5c2c', s * st.w / 2, h * 0.3, st.d / 2 + 0.005, st.w - 0.25, h * 0.38, 0.01);
          part(piv, ball, '#e6c24a', s * (st.w - 0.15), h * 0.48, st.d / 2 + 0.04, 0.05, 0.05, 0.05);
          doors.push({ piv, at: st.openAt, s: left ? -1 : 1 });
          // The frame.
          const fx0 = st.x - st.w / 2, fx1 = st.x + st.w / 2;
          for (const fx of [fx0, fx1]) part(floorG[st.floor], box, '#efe6d2', fx, st.bot + h / 2, st.z + st.d / 2, 0.08, h, 0.16);
        } else {
          const g = floorG[st.floor], th = st.top - st.bot;
          part(g, box, mat('#e9e3d6', { roughness: 0.9 }), st.x, st.bot + th / 2 - 0.01, st.z, st.w, th - 0.02, st.d).castShadow = false;
          const top = new T.Mesh(new T.PlaneGeometry(st.w, st.d), woodM[st.floor]);
          top.rotation.x = -Math.PI / 2; top.position.set(st.x, st.top, st.z); top.receiveShadow = true; g.add(top);
        }
      }
      // The sky stage: rooftops of other houses sticking out of the lava sea, far off.
      skyG = new T.Group(); skyG.visible = false; roomG.add(skyG);
      const r = rng(526);
      for (let i = 0; i < 14; i++) {
        const a = (i / 14) * TAU + r() * 0.3, dist = 20 + r() * 18, x = Math.cos(a) * dist, z = Math.sin(a) * dist - 6;
        const w = 4 + r() * 5, d = 3 + r() * 4, top = roofY + 0.6 + r() * 2.4, c = ['#c86b4a', '#7d8a96', '#a85a3c', '#5f6b52'][i % 4];
        const g = new T.Group(); g.position.set(x, 0, z); g.rotation.y = r() * TAU; skyG.add(g);
        part(g, box, '#e8dcc6', 0, top - 1.2, 0, w, 2.4, d).castShadow = false;
        const roof = part(g, box, c, 0, top + 0.35, 0, w + 0.3, 0.7, d * 0.75); roof.castShadow = false;
        if (r() < 0.6) part(g, box, '#8a4b35', w * 0.25, top + 0.9, 0, 0.5, 1.0, 0.5).castShadow = false;
      }
      // The rescue balloon behind the house, where kids that fell watch from once the roof is lava.
      balloon = new T.Group(); balloon.position.set(BALLOON.x, BALLOON.y, BALLOON.z); balloon.visible = false; roomG.add(balloon);
      part(balloon, box, '#a8743f', 0, 0, 0, 2.8, 0.7, 1.1);
      part(balloon, box, '#7a5233', 0, 0.36, 0, 2.9, 0.06, 1.2);
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) part(balloon, box, '#5a3a22', sx * 1.3, 1.5, sz * 0.5, 0.03, 2.4, 0.03);
      part(balloon, ball, '#e64a3a', 0, 4.4, 0, 2.3, 2.6, 2.3);
      for (let i = 0; i < 6; i++) { const a = i / 6 * TAU; part(balloon, ball, '#ffd23f', Math.cos(a) * 1.6, 4.4, Math.sin(a) * 1.6, 0.9, 2.0, 0.9).scale.set(0.9, 2.4, 0.9); }
    }

    // ---- Furniture: each piece a group whose top is the piece's top ----
    const COL = {
      sofa: '#3f7f8c', sofaback: '#356f7b', armchair: '#b8574a', tvbench: '#6b4a32', table: '#8a5a34', shelf: '#7a5233',
      pouf: '#e0a040', cushion: '#d95d75', sidetable: '#a0703e', stool: '#c08a50', chest: '#7b4f2c',
      bed: '#5b7fc2', wardrobe: '#f2efe6', desk: '#e9d6b0', chair: '#e46c4a', toybox: '#4bb07a', beanbag: '#9b6be0',
      blocks: '#f2c230', horse: '#c8783c', counter: '#f5f2ea', fridge: '#e8eef2', ktable: '#b9895a', basket: '#c9a46a',
      dogbed: '#8b5a3c', cupboard: '#d9cfb6',
      chimney: '#a5473a', skylight: '#9fd4ff', tank: '#c3c9cf', vent: '#8f969d', planter: '#7a5233', bench: '#9a6a3c',
      deckbox: '#5e7a4a', pot: '#c8744a',
    };
    function legs(g, w, d, top, th, c) {
      const lw = 0.07, lh = top - th;
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) part(g, box, c, sx * (w / 2 - 0.08), lh / 2, sz * (d / 2 - 0.08), lw, lh, lw);
    }
    function pieceModel(p) {
      const g = new T.Group(), inner = new T.Group(); g.add(inner);
      // A piece upstairs or on the roof is drawn from its own floor (bot) up.
      const { w, d } = p, h = p.h0 - (p.bot || 0), c = COL[p.kind] || '#999';
      inner.position.y = p.bot || 0;
      switch (p.kind) {
        case 'chimney': slab(inner, c, 0, h, 0, w, h, d); slab(inner, '#6e2f26', 0, h + 0.08, 0, w + 0.12, 0.1, d + 0.12);
          for (let y = 0.25; y < h; y += 0.25) slab(inner, '#8a3a2f', 0, y, d / 2 + 0.005, w, 0.03, 0.01); break;
        case 'skylight': slab(inner, '#d8dde2', 0, h - 0.06, 0, w, h - 0.06, d);
          slab(inner, c, 0, h, 0, w - 0.12, 0.06, d - 0.12, { emissive: '#7fc4ff', emissiveIntensity: 0.4, roughness: 0.2 }); break;
        case 'tank': part(inner, cyl, c, 0, h / 2, 0, w / 2, h, d / 2); part(inner, cyl, '#a9b0b7', 0, h - 0.02, 0, w / 2 - 0.04, 0.05, d / 2 - 0.04); break;
        case 'pot': part(inner, cyl, c, 0, h * 0.35, 0, w / 2, h * 0.7, d / 2); part(inner, ball, '#4f9a4a', 0, h * 0.78, 0, w / 2, h * 0.3, d / 2); break;
        case 'planter': slab(inner, c, 0, h - 0.08, 0, w, h - 0.08, d);
          for (let i = 0; i < 3; i++) part(inner, ball, '#5aa84f', (i - 1) * w / 3, h - 0.06, 0, w / 7, 0.1, d / 3); break;
        case 'bench': slab(inner, c, 0, h, 0, w, 0.08, d); legs(inner, w, d, h, 0.08, '#4a4f55'); break;
        case 'vent': slab(inner, c, 0, h, 0, w, h, d);
          for (let i = 0; i < 3; i++) slab(inner, '#5c6369', 0, h * (0.3 + i * 0.2), d / 2 + 0.005, w - 0.15, 0.04, 0.01); break;
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
      else if (f.kind === 'raft') {
        for (let i = 0; i < 5; i++) part(g, cyl, '#9a6a3c', 0, -0.12, (i - 2) * f.d / 5, 0.13, f.w, 0.13).rotation.z = Math.PI / 2;
        for (const x of [-0.35, 0.35]) slab(g, '#6b4a2a', x * f.w, 0.02, 0, 0.12, 0.05, f.d);
      } else if (f.kind === 'boat') {
        part(g, ball, '#ff7a1a', 0, -0.12, 0, f.w / 2, 0.2, f.d / 2);
        part(g, ball, '#ffd23f', 0, -0.02, 0, f.w / 2 - 0.15, 0.06, f.d / 2 - 0.15);
      } else if (f.kind === 'door') {
        slab(g, '#b5793f', 0, 0, 0, f.w, 0.12, f.d);
        slab(g, '#8e5c2c', -f.w * 0.2, 0.005, 0, f.w * 0.45, 0.01, f.d - 0.2);
        slab(g, '#8e5c2c', f.w * 0.27, 0.005, 0, f.w * 0.35, 0.01, f.d - 0.2);
        part(g, ball, '#e6c24a', f.w / 2 - 0.15, 0.03, f.d / 2 - 0.12, 0.05, 0.05, 0.05);
      } else if (f.kind === 'bigcushion') { part(g, ball, '#6fb7e8', 0, -0.12, 0, f.w / 2, 0.16, f.d / 2); part(g, ball, '#ffffff', 0, 0.02, 0, 0.12, 0.03, 0.12); }
      else if (f.kind === 'log') { const l = part(g, cyl, '#7a5233', 0, -0.12, 0, f.d / 2, f.w, f.d / 2); l.rotation.z = Math.PI / 2;
        for (const s of [-1, 1]) { const e = part(g, cyl, '#d9b27a', s * f.w / 2, -0.12, 0, f.d / 2 - 0.03, 0.02, f.d / 2 - 0.03); e.rotation.z = Math.PI / 2; } }
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
    // The kid the camera follows: the phone's own, else the first still in.
    function followed(w, me) {
      let f = me && !me.out ? me : null;
      if (!f && w.kids.length && w.ph !== 'count') f = w.kids.filter(k => !k.out).sort((a, b) => a.i - b.i)[0] || null;
      return f && (me || w.ph !== 'count') ? f : null;
    }
    function camera(w, me, clock) {
      const dt = Math.min(0.1, Math.max(0, clock - lastClock)); lastClock = clock;
      const land = glc.clientWidth > glc.clientHeight;
      const f = followed(w, me);
      if (f) {
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
    function poseKid(g, k, rt, clock, w, cut) {
      const u = g.userData, P = u.parts, L = lavaAt(rt, w);
      let x = k.dx, y = k.dy, z = k.dz, face = k.df, sit = false;
      if (k.out) {
        const t = rt - k.outRt;
        if (t < 0.9) { x = k.fellX; z = k.fellZ; y = L - t * 1.2; }
        else {
          // Out: on the windowsill, watching the rest. In the house, on the sill of the floor on
          // screen while the lava is below it, and in the rescue balloon once it is not (#526).
          const outs = w.kids.filter(o => o.out && rt - o.outRt >= 0.9).sort((a, b) => a.outRt - b.outRt);
          const n = outs.indexOf(k), m = outs.length;
          x = (n - (m - 1) / 2) * 0.5; y = SILL_Y - 0.42; z = SILL_Z + 0.1; face = Math.PI / 2; sit = true;
          if (w.house) {
            const fy = cut * FLOOR_H;
            if (cut < 2 && fy + SILL_Y > L + 0.25) y += fy;
            else { x = BALLOON.x + (n - (m - 1) / 2) * 0.42; y = BALLOON.y + 0.39 - 0.42; z = BALLOON.z + 0.35; }
          }
        }
      }
      g.visible = y > L - 1.1 && y < (cut < 2 ? (cut + 1) * FLOOR_H - SLAB : Infinity);
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
      const rt = w.rt, L = lavaAt(rt, w), on = rt >= 0;
      // Koko talo: the floors above the followed kid's are cut away (the menu shows downstairs).
      let cut = 2;
      if (w.house) {
        const f = followed(w, me);
        cut = !w.kids.length || (w.ph === 'count' && !f) ? 0 : f ? floorOfY(f.dy + 0.05) : 2;
        if (floorG) floorG.forEach((g, i) => { g.visible = i <= cut; });
        for (const d of doors) d.piv.rotation.y = d.s * Math.min(1, Math.max(0, rt - d.at) / 0.7) * 1.7;
      }
      L3D.cutY = w.house && cut < 2 ? (cut + 1) * FLOOR_H - SLAB : Infinity;
      const seaOn = !!(w.house && (cut === 2 || L > FLOOR_H * 2 - 0.2) && on);
      sea.visible = seaOn; lava.position.y = L;
      if (skyG) skyG.visible = seaOn;
      if (balloon) balloon.visible = seaOn || L > FLOOR_H + SILL_Y - 0.3;
      if (w.house) scene.background = seaOn ? SKY : houseBg;
      // The lava: comes up through the floor at the start, then rises and moves slowly.
      const fade = on ? Math.min(1, rt / 0.6) : 0;
      lava.visible = fade > 0 && !seaOn; lavaM.opacity = fade;
      sea.position.y = L; seaTex.offset.set(clock * 0.015, Math.sin(clock * 0.2) * 0.03);
      lavaTex.offset.set(clock * 0.015, Math.sin(clock * 0.2) * 0.03);
      lavaM.emissiveIntensity = 1.1 + Math.sin(clock * 2.2) * 0.15;
      glow.intensity = fade * (14 + Math.sin(clock * 3) * 2);
      glow.position.y = L + 0.5;
      // Furniture: sinking, and shaking while it wobbles.
      w.pieces.forEach((p, i) => {
        const g = pieces[i]; if (!g) return;
        const top = topOf(p, rt), wob = wobbleOf(p, rt), inner = g.userData.inner;
        g.position.y = top - p.h0;
        g.visible = top > L - 2.5 && (p.floor || 0) <= cut;
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
        poseKid(g, k, rt, clock, w, cut); ids.add(k.id);
      }
      for (const [id, g] of kids) if (!ids.has(id)) { scene.remove(g); kids.delete(id); }
      meMark.visible = !!(me && !me.out && w.kids.length > 1);
      if (meMark.visible) meMark.position.set(me.dx, me.dy + KID_H + 0.32 + Math.sin(clock * 5) * 0.05, me.dz);
      camera(w, me, clock);
      sun.target.position.set(look.x, look.y, look.z); sun.position.set(look.x - 5, look.y + 14, look.z + 8);
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
