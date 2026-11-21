'use strict';
// Kaaosrata drawn in 3D (v10, #493). three.js renders the course, the obstacles and the runners on a
// WebGL canvas under the game's own 2D canvas, which keeps the HUD, the names, the stick, the jump
// button and the results. It only reads the game's state (index.html, radat.js) each frame and never
// changes it. A phone that cannot draw WebGL (K3D.failed) keeps playing on v9's 2D drawing.
// The game's x runs across, y up the course and z is height; in three.js that is (x, z, -y).
window.K3D = { ready: false, failed: false };
(function () {
  const glc = document.getElementById('g');
  window.K3D_LIB.then(T => {
    let rd;
    try { rd = new T.WebGLRenderer({ canvas: glc, antialias: true }); } catch (e) { K3D.failed = true; return; }
    let ratio = Math.min(window.devicePixelRatio || 1, 1.5);
    rd.setPixelRatio(ratio);
    rd.shadowMap.enabled = true; rd.shadowMap.type = T.PCFSoftShadowMap;
    const SKY = '#2e1862';
    const scene = new T.Scene();
    scene.background = new T.Color(SKY);
    scene.fog = new T.Fog(SKY, 28, 75);
    const cam = new T.PerspectiveCamera(70, 1, 0.3, 200);
    scene.add(new T.HemisphereLight('#f4ecff', '#3b2a6b', 1.6));
    const sun = new T.DirectionalLight('#fff1dc', 2.2);
    sun.castShadow = true; sun.shadow.mapSize.set(1024, 1024); sun.shadow.bias = -0.0006;
    Object.assign(sun.shadow.camera, { left: -15, right: 15, top: 15, bottom: -15, near: 2, far: 70 });
    scene.add(sun, sun.target);

    // ---- Shared shapes and paint ----
    const box = new T.BoxGeometry(1, 1, 1), ball = new T.SphereGeometry(1, 20, 14);
    const cyl = new T.CylinderGeometry(1, 1, 1, 36);
    const std = (color, o) => new T.MeshStandardMaterial(Object.assign({ color, roughness: 0.6 }, o || {}));
    function canvasTex(w, h, paint) {
      const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
      paint(cv.getContext('2d'), w, h);
      const tx = new T.CanvasTexture(cv); tx.colorSpace = T.SRGBColorSpace; tx.anisotropy = 4;
      return tx;
    }
    const stripeTex = canvasTex(8, 64, (g, w, h) => { g.fillStyle = '#fff'; g.fillRect(0, 0, w, h); g.fillStyle = '#d8eef2'; g.fillRect(0, 0, w, 10); });
    // A plane lying on the course, its local +y up the course.
    const flat = (w, d) => { const g = new T.PlaneGeometry(w, d); g.rotateX(-Math.PI / 2); return g; };

    // ---- The course: built once per course ----
    const world = new T.Group(); scene.add(world);
    let built = null, moving = null;
    const THICK = 2.5; // how far a surface's column reaches down, to show the steps as solid blocks
    function slab(x0, x1, y0, y1, top, mats) {
      const g = new T.BoxGeometry(x1 - x0, 1, y1 - y0), p = g.attributes.position, cy = (y0 + y1) / 2;
      for (let i = 0; i < p.count; i++) {
        const h = top(cy - p.getZ(i));
        p.setY(i, p.getY(i) > 0 ? h : h - THICK - h * 0.4);
      }
      g.computeVertexNormals();
      const m = new T.Mesh(g, mats);
      m.position.set((x0 + x1) / 2, 0, -cy); m.castShadow = true; m.receiveShadow = true;
      return m;
    }
    const sideOf = (top, side) => [side, side, top, side, side, side];
    // Text or a pattern lying on the ground at (x, y), tilted with a ramp.
    function onGround(mesh, x, y, lift) {
      let grade = 0;
      for (const f of STATIC) if (inRect(f, x, y) && f.h1 !== undefined) grade = (f.h1 - (f.h || 0)) / (f.y1 - f.y0);
      mesh.position.set(x, baseAt(x, y) + (lift || 0.03), -y); mesh.rotation.x = Math.atan(grade);
      world.add(mesh); return mesh;
    }
    function label(text, w, d, color) {
      const tx = canvasTex(512, Math.round(512 * d / w), (g, cw, ch) => {
        g.font = '900 ' + Math.round(ch * 0.8) + 'px system-ui,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillStyle = color; g.fillText(text, cw / 2, ch / 2);
      });
      return new T.Mesh(flat(w, d), new T.MeshBasicMaterial({ map: tx, transparent: true, depthWrite: false, fog: true }));
    }
    function clear() {
      // Free what the last course made on the graphics card; the shared shapes stay.
      const keep = new Set([box, ball, cyl]), mats = new Set();
      for (const o of [...world.children]) {
        world.remove(o);
        o.traverse(n => { if (n.geometry && !keep.has(n.geometry)) n.geometry.dispose(); [].concat(n.material || []).forEach(m => mats.add(m)); });
      }
      for (const m of mats) { if (m.map) m.map.dispose(); m.dispose(); }
    }
    function build() {
      clear();
      moving = { belts: [], tiles: [], discs: [], sweepers: [], pushers: [], hammers: [], mov: null };
      const floorSide = std('#5f8fb0'), stoneSide = std('#c98f1b'), stoneTop = std('#ffd166');
      for (const f of FLOORS) {
        if (f.stone) { world.add(slab(f.x0, f.x1, f.y0, f.y1, py => topOf(f, py), sideOf(stoneTop, stoneSide))); continue; }
        const tex = stripeTex.clone(); tex.wrapS = tex.wrapT = T.RepeatWrapping; tex.repeat.set(1, (f.y1 - f.y0) / 3); tex.needsUpdate = true;
        // Higher floors are a little lighter, so a step reads at a glance.
        const top = new T.Color(course.id === 'main' && f.y0 >= 112 && f.y0 < 130 ? '#ff99c8' : '#a0e7e5').lerp(new T.Color('#ffffff'), Math.min(0.35, (f.h || 0) * 0.09));
        world.add(slab(f.x0, f.x1, f.y0, f.y1, py => topOf(f, py), sideOf(std(top, { map: tex }), floorSide)));
      }
      for (const b of BELTS) {
        const tx = canvasTex(64, 64, (g) => {
          g.fillStyle = '#314d69'; g.fillRect(0, 0, 64, 64);
          g.translate(32, 32); g.rotate(Math.atan2(-b.vy, b.vx) + Math.PI / 2);
          g.strokeStyle = '#ffd166'; g.lineWidth = 9; g.lineCap = 'round';
          g.beginPath(); g.moveTo(-16, 8); g.lineTo(0, -10); g.lineTo(16, 8); g.stroke();
        });
        tx.wrapS = tx.wrapT = T.RepeatWrapping; tx.repeat.set((b.x1 - b.x0) / 1.6, (b.y1 - b.y0) / 1.8);
        const m = onGround(new T.Mesh(flat(b.x1 - b.x0, b.y1 - b.y0), new T.MeshStandardMaterial({ map: tx, roughness: 0.8 })), (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2, 0.02);
        m.receiveShadow = true;
        moving.belts.push({ b, tx });
      }
      for (const tile of TILES) {
        const mat = std('#90e6a0'), m = slab(tile.x0 + 0.04, tile.x1 - 0.04, tile.y0 + 0.04, tile.y1 - 0.04, () => tile.h || 0, sideOf(mat, std('#366d68')));
        world.add(m); moving.tiles.push({ tile, m, mat });
      }
      if (MOV) {
        const m = new T.Mesh(box, sideOf(std('#ff9f1c'), std('#b0630b')));
        m.scale.set(MOV.hw * 2, 0.8, MOV.y1 - MOV.y0); m.castShadow = m.receiveShadow = true; world.add(m);
        moving.mov = m;
      }
      for (const d of DISCS) {
        const g = new T.Group(), top = std('#c3a6ff'), side = std('#6a4bb3');
        const body = new T.Mesh(cyl, [side, top, side]); body.scale.set(d.r, 0.8, d.r); body.position.y = -0.4;
        body.castShadow = body.receiveShadow = true; g.add(body);
        for (let k = 0; k < 2; k++) { const s = new T.Mesh(box, std('#ffffff')); s.scale.set(d.r * 1.8, 0.04, 0.16); s.rotation.y = k * Math.PI / 2; s.position.y = 0.02; g.add(s); }
        g.position.set(d.x, d.h || 0, -d.y); world.add(g); moving.discs.push({ d, g });
      }
      const red = std('#e63946'), white = std('#ffffff'), hubM = std('#9d0208');
      for (const s of SWEEPERS) {
        const g = new T.Group(), hub = new T.Mesh(cyl, hubM);
        hub.scale.set(0.55, BAR_H + 0.25, 0.55); hub.position.y = (BAR_H + 0.25) / 2; hub.castShadow = true; g.add(hub);
        for (let k = 0; k < 10; k++) {
          const seg = new T.Mesh(box, k % 2 ? white : red), l = s.len / 5;
          seg.scale.set(l, 0.3, 0.3); seg.position.set(-s.len + l * (k + 0.5), BAR_H * 0.6, 0); seg.castShadow = true; g.add(seg);
        }
        g.position.set(s.x, s.base, -s.y); world.add(g); moving.sweepers.push({ s, g });
      }
      const wallM = sideOf(std('#ff5ca8'), std('#d0006f'));
      for (const p of PUSHERS) for (let k = 0; k < 2; k++) {
        const m = new T.Mesh(box, wallM); m.scale.set(BLOCK_HW * 2, 2.2, BLOCK_HD * 2); m.castShadow = m.receiveShadow = true;
        world.add(m); moving.pushers.push({ p, k, m });
      }
      for (const b of BUMPERS) {
        const m = new T.Mesh(cyl, [std('#8a5a00'), std('#ffb703'), std('#8a5a00')]); m.scale.set(0.6, 0.7, 0.6);
        m.position.set(b.x, b.base + 0.35, -b.y); m.castShadow = true; world.add(m);
        const under = baseAt(b.x, b.y);
        if (b.base > under + 0.1) { const p = new T.Mesh(box, std('#555566')); p.scale.set(0.2, b.base - under, 0.2); p.position.set(b.x, (b.base + under) / 2, -b.y); world.add(p); }
      }
      const ham = std('#9b4dde', { roughness: 0.35 }), post = std('#555566'), rope = new T.LineBasicMaterial({ color: '#333333' });
      for (const h of HAMMERS) {
        for (const sx of [-5.6, 5.6]) { const m = new T.Mesh(box, post); m.scale.set(0.3, 4.8, 0.3); m.position.set(sx, h.base + 2.4, -h.y); m.castShadow = true; world.add(m); }
        const bar = new T.Mesh(box, post); bar.scale.set(11.5, 0.25, 0.25); bar.position.set(0, h.base + 4.7, -h.y); world.add(bar);
        const m = new T.Mesh(ball, ham); m.scale.setScalar(HAM_R); m.castShadow = true; world.add(m);
        const lg = new T.BufferGeometry().setFromPoints([new T.Vector3(), new T.Vector3()]), line = new T.Line(lg, rope); world.add(line);
        moving.hammers.push({ h, m, line });
      }
      // Section names and the checkpoints painted on the floor, the finish line and its arch.
      SECTIONS.forEach(([y, s]) => onGround(label(s, 8, 1.2, 'rgba(40,20,90,.45)'), 0, y - 1.2));
      const dash = canvasTex(64, 8, (g) => { g.fillStyle = 'rgba(126,224,129,.95)'; g.fillRect(0, 0, 36, 8); });
      dash.wrapS = T.RepeatWrapping; dash.repeat.set(20, 1);
      CPS.slice(1, -1).forEach(y => onGround(new T.Mesh(flat(10, 0.3), new T.MeshBasicMaterial({ map: dash, transparent: true, depthWrite: false })), 0, y - 1.2));
      const check = canvasTex(160, 16, (g) => { for (let i = 0; i < 20; i++) for (let j = 0; j < 2; j++) { g.fillStyle = (i + j) % 2 ? '#111' : '#fff'; g.fillRect(i * 8, j * 8, 8, 8); } });
      check.magFilter = T.NearestFilter;
      onGround(new T.Mesh(flat(10, 1), new T.MeshBasicMaterial({ map: check })), 0, FIN);
      const fb = baseAt(0, FIN + 0.5), archM = std('#ffd166');
      for (const sx of [-5.2, 5.2]) { const m = new T.Mesh(box, archM); m.scale.set(0.35, 3.6, 0.35); m.position.set(sx, fb + 1.8, -FIN); m.castShadow = true; world.add(m); }
      const sign = new T.Mesh(new T.PlaneGeometry(10.8, 1.1), new T.MeshBasicMaterial({ map: canvasTex(512, 52, (g, w, h) => {
        g.fillStyle = '#b5179e'; g.fillRect(0, 0, w, h); g.font = '900 40px system-ui,sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillStyle = '#ffd166'; g.fillText('MAALI', w / 2, h / 2 + 2);
      }), side: T.DoubleSide }));
      sign.position.set(0, fb + 3.6, -FIN); world.add(sign);
      built = course;
    }

    // ---- The runners: jellybeans with eyes, and a round shadow on the ground under them ----
    const bodies = new Map();
    const bodyG = new T.CapsuleGeometry(0.36, 0.5, 6, 16), eyeM = std('#ffffff', { roughness: 0.3 }), pupilM = std('#111111');
    const shadowG = new T.CircleGeometry(RAD, 24); shadowG.rotateX(-Math.PI / 2);
    const shadowM = new T.MeshBasicMaterial({ color: '#000000', transparent: true, opacity: 0.32, depthWrite: false });
    const meRing = new T.Mesh(new T.TorusGeometry(0.5, 0.05, 8, 32).rotateX(Math.PI / 2), new T.MeshBasicMaterial({ color: '#ffd166' }));
    scene.add(meRing);
    function bodyOf(r) {
      let o = bodies.get(r);
      if (o && o.color === r.color) return o;
      if (o) scene.remove(o.g, o.sh);
      const g = new T.Group(), tilt = new T.Group(); g.add(tilt);
      const b = new T.Mesh(bodyG, std(r.color, { roughness: 0.4 })); b.position.y = 0.61; b.castShadow = true; tilt.add(b);
      const eyes = [];
      for (const ex of [-0.14, 0.14]) {
        const e = new T.Mesh(ball, eyeM); e.scale.set(0.11, 0.13, 0.08); e.position.set(ex, 0.86, -0.3); tilt.add(e);
        const p = new T.Mesh(ball, pupilM); p.scale.setScalar(0.055); p.position.set(ex, 0.86, -0.38); tilt.add(p); eyes.push(p);
      }
      const sh = new T.Mesh(shadowG, shadowM);
      scene.add(g, sh);
      o = { g, tilt, sh, eyes, color: r.color, head: 0 };
      bodies.set(r, o);
      return o;
    }
    function drawRunners(t) {
      const seen = new Set();
      meRing.visible = false;
      if (race) for (const r of race.runners) {
        const o = bodyOf(r); seen.add(r);
        const fall = r.fall > 0, s = fall ? Math.max(0.05, 1 - r.fall * 0.85) : 1;
        o.g.position.set(r.x, r.z, -r.y); o.g.scale.setScalar(s);
        const v = Math.hypot(r.vx, r.vy);
        if (v > 0.4) {
          const want = Math.atan2(-r.vx, r.vy);
          let d = want - o.head; d = Math.atan2(Math.sin(d), Math.cos(d)); o.head += d * 0.25;
        }
        o.g.rotation.y = o.head;
        o.tilt.rotation.z = r.stun > 0 ? Math.sin(r.ph * 3 + r.stun * 30) * 0.3 : Math.sin(r.ph) * 0.06;
        o.tilt.rotation.x = -Math.min(0.25, v * 0.03);
        for (const p of o.eyes) p.scale.set(0.055, r.stun > 0 ? 0.015 : 0.055, 0.055);
        const g = fall ? null : groundAt(r.x, r.y, t, r.z);
        o.sh.visible = !!g;
        if (g) { o.sh.position.set(r.x, g.h + 0.02, -r.y); o.sh.scale.setScalar(1 / (1 + (r.z - g.h) * 0.4)); }
        if (r === me && !fall && g) { meRing.visible = true; meRing.position.set(r.x, g.h + 0.04, -r.y); }
      }
      for (const [r, o] of bodies) if (!seen.has(r)) { scene.remove(o.g, o.sh); bodies.delete(r); }
    }

    // ---- Each frame ----
    function animate(t) {
      for (const { b, tx } of moving.belts) tx.offset.set(-b.vx * t / 1.6, -b.vy * t / 1.8);
      for (const { tile, m, mat } of moving.tiles) {
        m.visible = tileOn(tile, t);
        const flash = tilePhase(tile, t) > tile.on - 0.6;
        mat.color.set(flash ? (Math.floor(t * 10) % 2 ? '#ff695c' : '#ffbd69') : '#90e6a0');
      }
      if (moving.mov) moving.mov.position.set(movX(t), (MOV.h || 0) - 0.4, -(MOV.y0 + MOV.y1) / 2);
      for (const { d, g } of moving.discs) g.rotation.y = d.w * t;
      for (const { s, g } of moving.sweepers) g.rotation.y = s.w * t + s.ph;
      for (const { p, k, m } of moving.pushers) m.position.set(blockX(p, t, k), p.base + 1.1, -p.y);
      for (const { h, m, line } of moving.hammers) {
        const hx = hamX(h, t); m.position.set(hx, h.base + 1.0, -h.y);
        const a = line.geometry.attributes.position; a.setXYZ(0, 0, h.base + 4.7, -h.y); a.setXYZ(1, hx, h.base + 1.0 + HAM_R * 0.9, -h.y); a.needsUpdate = true;
      }
    }

    // The camera: behind and above the followed runner, always looking up the course.
    let cx = 0, ch = 0, lastW = 0, lastH = 0;
    function place(follow, w, h) {
      const wideView = w > h;
      const tx = follow ? (follow.fall > 0 ? 0 : follow.x * 0.55) : 0;
      const th = follow ? (follow.fall > 0 ? baseAt(0, CPS[follow.cp]) : Math.max(follow.z, baseAt(follow.x, follow.y) - 0.5)) : 0;
      cx += (tx - cx) * 0.1; ch += (th - ch) * 0.08;
      cam.fov = wideView ? 52 : 74;
      const back = wideView ? 7.5 : 7, up = wideView ? 5.2 : 6.6;
      cam.position.set(cx, ch + up, -(camY - back));
      cam.lookAt(cx * 0.8, ch + 0.6, -(camY + (wideView ? 6 : 5)));
      sun.position.set(cx - 8, ch + 22, -(camY - 4)); sun.target.position.set(cx, ch, -(camY + 4));
    }

    // A slow phone runs short of pixels, not of shapes (Hiihto v7): watch the first seconds of a race
    // and step the pixel ratio down, then the shadows off.
    let tuneN = 0, tuneSum = 0, tuneStep = 0, prevNow = 0;
    function tune(now) {
      const dt = prevNow ? now - prevNow : 16; prevNow = now;
      if (!race || race.phase !== 'run' || tuneStep > 3 || dt > 200) return;
      tuneN++; tuneSum += dt;
      if (tuneN < 90) return;
      const slow = tuneSum / tuneN > 24; tuneN = 0; tuneSum = 0;
      if (!slow) { tuneStep = 4; return; }
      if (ratio > 1) ratio = 1; else if (ratio > 0.75) ratio = 0.75; else { rd.shadowMap.enabled = false; sun.castShadow = false; tuneStep = 3; }
      rd.setPixelRatio(ratio); lastW = 0; tuneStep++;
    }

    K3D.render = function (t, follow) {
      if (built !== course) build();
      const w = glc.clientWidth || innerWidth, h = glc.clientHeight || innerHeight;
      if (w !== lastW || h !== lastH) { rd.setSize(w, h, false); lastW = w; lastH = h; }
      cam.aspect = w / h;
      place(follow, w, h);
      cam.updateProjectionMatrix();
      animate(t);
      drawRunners(t);
      rd.render(scene, cam);
      tune(performance.now());
    };
    // Where a point of the course shows on the screen, in CSS pixels (null behind the camera).
    const v3 = new T.Vector3();
    K3D.project = function (x, z, y) {
      v3.set(x, z, -y).project(cam);
      if (v3.z > 1) return null;
      return { x: (v3.x + 1) / 2 * lastW, y: (1 - v3.y) / 2 * lastH };
    };
    K3D.ready = true;
  }, () => { K3D.failed = true; });
})();
