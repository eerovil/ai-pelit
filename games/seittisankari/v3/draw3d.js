'use strict';
// Seittisankari v1 (#529): the city drawn in 3D with the shared three.js, on the WebGL canvas #g
// under the 2D canvas #c (HUD, stick, buttons in ui.js). This only reads the world and the
// camera; nothing here changes how the game plays. A phone that cannot draw WebGL gets
// L3D.failed and a Finnish note.
window.L3D = { failed: false, ready: false, draw() {}, resize() {}, project() { return null; } };
(function () {
  const glc = document.getElementById('g');
  (window.S3D_LIB || Promise.reject(new Error('no three'))).then(T => {
    let rd;
    try { rd = new T.WebGLRenderer({ canvas: glc, antialias: true }); } catch (e) { L3D.failed = true; return; }
    let pr = Math.min(devicePixelRatio || 1, 1.5);
    rd.setPixelRatio(pr);
    const SKY = new T.Color('#a9d6ff');
    const scene = new T.Scene();
    scene.background = SKY;
    scene.fog = new T.Fog(SKY, 140, 620);
    const cam = new T.PerspectiveCamera(70, 1, 0.2, 800);
    scene.add(new T.HemisphereLight('#eef6ff', '#6a6a72', 1.7));
    const sun = new T.DirectionalLight('#fff3dc', 1.6);
    sun.position.set(-120, 260, -80); scene.add(sun);

    const box = new T.BoxGeometry(1, 1, 1), ball = new T.SphereGeometry(1, 16, 12), cyl = new T.CylinderGeometry(1, 1, 1, 14);
    const mats = new Map();
    const mat = (c, o) => { const k = c + JSON.stringify(o || {}); if (!mats.has(k)) mats.set(k, new T.MeshStandardMaterial(Object.assign({ color: c, roughness: 0.8 }, o || {}))); return mats.get(k); };
    function part(par, geo, c, x, y, z, sx, sy, sz, o) {
      const m = new T.Mesh(geo, typeof c === 'string' ? mat(c, o) : c);
      m.position.set(x, y, z); m.scale.set(sx, sy, sz); par.add(m); return m;
    }
    function canvasTex(w, h, paint) {
      const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
      paint(cv.getContext('2d'), w, h);
      const t = new T.CanvasTexture(cv); t.wrapS = t.wrapT = T.RepeatWrapping; t.colorSpace = T.SRGBColorSpace;
      t.anisotropy = 4; return t;
    }
    // One tile of a facade: 4 windows across, 3 floors (8 m × 10.5 m).
    const FAC = ['#c9b8a0', '#8c97a8', '#b07a5e', '#d8d4cc'];
    const facades = FAC.map((base, k) => canvasTex(128, 168, (g, w, h) => {
      g.fillStyle = base; g.fillRect(0, 0, w, h);
      const r = rng(11 + k);
      for (let fy = 0; fy < 3; fy++) for (let fx = 0; fx < 4; fx++) {
        const lit = r() < 0.25;
        g.fillStyle = lit ? '#ffe9a8' : k === 1 ? '#3d5a7a' : '#4a6380';
        g.fillRect(fx * 32 + 6, fy * 56 + 12, 20, 34);
        g.fillStyle = 'rgba(255,255,255,.25)'; g.fillRect(fx * 32 + 6, fy * 56 + 12, 20, 4);
      }
      g.fillStyle = 'rgba(0,0,0,.12)'; g.fillRect(0, h - 4, w, 4);
    }));
    const wallM = facades.map(t => new T.MeshStandardMaterial({ map: t, roughness: 0.85 }));
    const roofM = mat('#6b6e75'), roofEdge = mat('#4c4f55');
    // The street: asphalt with a dashed line down the middle of each street, one tile per lot.
    const streetTex = canvasTex(512, 512, (g, w, h) => {
      g.fillStyle = '#55585e'; g.fillRect(0, 0, w, h);
      const r = rng(5);
      for (let i = 0; i < 2500; i++) { g.fillStyle = `rgba(${r() < 0.5 ? '0,0,0' : '255,255,255'},.05)`; g.fillRect(r() * w, r() * h, 2, 2); }
      g.fillStyle = '#e8e2c4';
      const px = w / LOT;                              // pixels per metre
      for (let k = 0; k < 5; k++) {                    // 3.5 m dashes every 8 m
        g.fillRect(w / 2 - px * 0.13, k * 8 * px, px * 0.26, 3.5 * px);
        g.fillRect(k * 8 * px, h / 2 - px * 0.13, 3.5 * px, px * 0.26);
      }
    });
    const SPAN = LOT * (GRID + 4);                     // a multiple of 40, centred on a street line
    streetTex.repeat.set(SPAN / LOT, SPAN / LOT); streetTex.offset.set(0.5, 0.5);

    const city = new T.Group(); scene.add(city);
    const ground = new T.Mesh(new T.PlaneGeometry(SPAN, SPAN), new T.MeshStandardMaterial({ map: streetTex, roughness: 1 }));
    ground.rotation.x = -Math.PI / 2; city.add(ground);
    const far = new T.Mesh(new T.PlaneGeometry(6000, 6000), mat('#4f6a4a', { roughness: 1 }));   // land past the city
    far.rotation.x = -Math.PI / 2; far.position.y = -0.05; city.add(far);

    // The buildings, merged into one mesh per chunk of 7 × 7 lots: 1700 buildings as separate
    // meshes would be thousands of draw calls a frame. Each chunk has five parts: four facade
    // textures, and everything plain (roofs, sidewalks, low walls, water towers) in vertex colours.
    const plainM = new T.MeshStandardMaterial({ vertexColors: true, roughness: 0.85 });
    const CH = 7, cBox = new T.BoxGeometry(1, 1, 1), cCyl = new T.CylinderGeometry(1, 1, 1, 10), cCone = new T.ConeGeometry(1, 1, 10);
    const mx = new T.Matrix4(), q0 = new T.Quaternion(), vS = new T.Vector3(), vP = new T.Vector3(), nm = new T.Matrix3();
    const pv3 = new T.Vector3(), nv3 = new T.Vector3(), colr = new T.Color();
    const PARK = new T.Color('#5d8a4e'), TREE = new T.Color('#3f6b38'), TRUNK = new T.Color('#6a4a32');
    function bucket() { return { p: [], n: [], u: [], c: [] }; }
    // Copy a geometry's triangles (moved by mx) into a bucket. `uvf(i)` may change a vertex's uv.
    function put(bk, geo, color, uvf, groupMat, matIdx) {
      const P = geo.attributes.position, N = geo.attributes.normal, U = geo.attributes.uv, I = geo.index;
      nm.getNormalMatrix(mx);
      const groups = geo.groups.length ? geo.groups : [{ start: 0, count: I ? I.count : P.count, materialIndex: 0 }];
      for (const gr of groups) {
        const tgt = groupMat ? groupMat(gr.materialIndex) : bk;
        if (!tgt) continue;
        for (let k = gr.start; k < gr.start + gr.count; k++) {
          const i = I ? I.getX(k) : k;
          pv3.fromBufferAttribute(P, i).applyMatrix4(mx); nv3.fromBufferAttribute(N, i).applyMatrix3(nm).normalize();
          tgt.p.push(pv3.x, pv3.y, pv3.z); tgt.n.push(nv3.x, nv3.y, nv3.z);
          const uv = uvf ? uvf(i, gr.materialIndex) : [U.getX(i), U.getY(i)];
          tgt.u.push(uv[0], uv[1]);
          tgt.c.push(color.r, color.g, color.b);
        }
      }
    }
    const at = (x, y, z, sx, sy, sz) => mx.compose(vP.set(x, y, z), q0, vS.set(sx, sy, sz));
    const C_SIDE = new T.Color('#9a9a96'), C_ROOF = new T.Color('#6b6e75'), C_EDGE = new T.Color('#4c4f55'),
      C_WOOD = new T.Color('#8a5a3a'), C_CONE = new T.Color('#6a4630'), C_LEG = new T.Color('#333333'), C_MAST = new T.Color('#c8c8cc');
    for (let ci = 0; ci < GRID; ci += CH) for (let cj = 0; cj < GRID; cj += CH) {
      const walls = [bucket(), bucket(), bucket(), bucket()], plain = bucket();
      for (let i = ci; i < Math.min(GRID, ci + CH); i++) for (let j = cj; j < Math.min(GRID, cj + CH); j++) {
        const b = boxAt(i, j);
        if (!b) {   // a park: grass and a few trees
          const x = lotX(i), z = lotX(j), r = rng(i * 97 + j);
          at(x, 0.06, z, 32, 0.12, 32); put(plain, cBox, PARK);
          for (let t = 0; t < 7; t++) {
            const tx = x + (r() - 0.5) * 26, tz = z + (r() - 0.5) * 26, th = 4 + r() * 4;
            at(tx, th * 0.3, tz, 0.3, th * 0.6, 0.3); put(plain, cCyl, TRUNK);
            at(tx, th * 0.75, tz, 2 + r(), th * 0.8, 2 + r()); put(plain, cCone, TREE);
          }
          continue;
        }
        const w = b.x1 - b.x0, d = b.z1 - b.z0, cx = (b.x0 + b.x1) / 2, cz = (b.z0 + b.z1) / 2;
        at(cx, b.h / 2, cz, w, b.h, d);
        // Facade texture in metres: a tile is 8 m wide and 10.5 m tall. Box faces: 0,1 ±x, 2,3 ±y, 4,5 ±z.
        put(null, cBox, C_ROOF, (i, mi) => {
          const U = cBox.attributes.uv;
          return mi === 2 || mi === 3 ? [U.getX(i), U.getY(i)] : [U.getX(i) * (mi < 2 ? d : w) / 8, U.getY(i) * b.h / 10.5];
        }, mi => mi === 2 || mi === 3 ? plain : walls[b.col]);
        at(cx, 0.08, cz, w + 6, 0.16, d + 6); put(plain, cBox, C_SIDE);
        for (const [x, z, sx, sz] of [[0, -d / 2, w, 0.3], [0, d / 2, w, 0.3], [-w / 2, 0, 0.3, d], [w / 2, 0, 0.3, d]]) { at(cx + x, b.h + 0.3, cz + z, sx, 0.6, sz); put(plain, cBox, C_EDGE); }
        if (b.water && !b.tower) {
          const wx = b.x0 + 4, wz = b.z1 - 4;
          at(wx, b.h + 3.5, wz, 2, 3, 2); put(plain, cCyl, C_WOOD);
          at(wx, b.h + 5.6, wz, 2.2, 1.2, 2.2); put(plain, cCone, C_CONE);
          for (const [ox, oz] of [[-1.3, -1.3], [1.3, -1.3], [-1.3, 1.3], [1.3, 1.3]]) { at(wx + ox, b.h + 1, wz + oz, 0.2, 2, 0.2); put(plain, cBox, C_LEG); }
        }
        if (b.tower) {
          at(cx, b.h + 15, cz, 0.5, 30, 0.5); put(plain, cCyl, C_MAST);
          part(city, ball, '#ff3030', cx, b.h + 30.5, cz, 0.8, 0.8, 0.8, { emissive: '#ff2020', emissiveIntensity: 1 });
        }
      }
      const geo = new T.BufferGeometry(), all = [...walls, plain], P = [], N = [], U = [], C = [];
      let start = 0;
      all.forEach((bk, k) => {
        const n = bk.p.length / 3; if (!n) return;
        for (const [o, f] of [[P, bk.p], [N, bk.n], [U, bk.u], [C, bk.c]]) for (let k2 = 0; k2 < f.length; k2++) o.push(f[k2]);
        geo.addGroup(start, n, k); start += n;
      });
      if (!start) continue;
      geo.setAttribute('position', new T.Float32BufferAttribute(P, 3));
      geo.setAttribute('normal', new T.Float32BufferAttribute(N, 3));
      geo.setAttribute('uv', new T.Float32BufferAttribute(U, 2));
      geo.setAttribute('color', new T.Float32BufferAttribute(C, 3));
      geo.computeBoundingSphere(); geo.computeBoundingBox();
      city.add(new T.Mesh(geo, [...wallM, plainM]));
    }

    // ---- The hero (and friends' heroes): hoodie, mask, white gloves; built once per colour ----
    function makeHero(col) {
      const g = new T.Group(), body = new T.Group(); g.add(body);
      const P = {};
      part(body, box, col, 0, 1.12, 0, 0.5, 0.62, 0.3);
      part(body, box, '#26324a', 0, 0.86, 0, 0.46, 0.14, 0.28);             // belt and hips
      part(body, ball, col, 0, 1.48, -0.1, 0.24, 0.12, 0.16);               // hood behind the head
      part(body, ball, '#1b1f2e', 0, 1.56, 0, 0.2, 0.22, 0.2);               // masked head
      part(body, ball, '#ffffff', -0.08, 1.6, 0.16, 0.06, 0.04, 0.03);       // mask eyes
      part(body, ball, '#ffffff', 0.08, 1.6, 0.16, 0.06, 0.04, 0.03);
      // Joints: shoulder → elbow → glove, hip → knee → shoe. Each is a group turned by the pose.
      const joint = (par, x, y) => { const j = new T.Group(); j.position.set(x, y, 0); par.add(j); return j; };
      for (const [k, x] of [['L', -0.33], ['R', 0.33]]) {
        const sh = joint(body, x, 1.38); part(sh, box, col, 0, -0.14, 0, 0.14, 0.3, 0.16);
        const el = joint(sh, 0, -0.27); part(el, box, col, 0, -0.12, 0, 0.12, 0.26, 0.14);
        P['hand' + k] = part(el, ball, '#f4f4f4', 0, -0.29, 0, 0.09, 0.09, 0.09);
        P['arm' + k] = sh; P['elb' + k] = el;
        const hip = joint(body, x * 0.42, 0.84); part(hip, box, '#26324a', 0, -0.21, 0, 0.2, 0.44, 0.22);
        const kn = joint(hip, 0, -0.42); part(kn, box, '#26324a', 0, -0.2, 0, 0.18, 0.42, 0.2); part(kn, box, '#f4f4f4', 0, -0.42, 0.05, 0.19, 0.08, 0.3);
        P['leg' + k] = hip; P['knee' + k] = kn;
      }
      const shadow = new T.Mesh(new T.CircleGeometry(0.5, 20), new T.MeshBasicMaterial({ color: '#000', transparent: true, opacity: 0.3, depthWrite: false }));
      shadow.rotation.x = -Math.PI / 2; scene.add(shadow);
      const web = new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(), new T.Vector3()]), new T.LineBasicMaterial({ color: '#ffffff' }));
      web.frustumCulled = false; scene.add(web);
      scene.add(g);
      return { g, body, P, shadow, web, phase: 0, tgt: {} };
    }
    const heroes = new Map();
    const up = new T.Vector3(0, 1, 0), tmpA = new T.Vector3(), tmpB = new T.Vector3(), tmpC = new T.Vector3(), basis = new T.Matrix4();
    const JOINTS = ['armL', 'armR', 'elbL', 'elbR', 'legL', 'legR', 'kneeL', 'kneeR'];
    // The pose: a target angle (x, y, z) for each joint; the joints turn toward it, so a change of
    // state (a web caught, a wall grabbed) blends in a moment instead of snapping.
    // Signs: a joint's +x turns its limb backward; a leg forward and up is -x, a knee bends with +x.
    const FLIP_T = 0.7;
    function poseHero(m, h, dt) {
      m.g.visible = true;
      m.g.position.set(h.x, h.y, h.z);
      const sp = Math.hypot(h.vx, h.vz);
      const P = m.P, J = m.tgt;
      const set = (k, x, y, z) => { J[k] = [x, y || 0, z || 0]; };
      let bodyX = 0, bodyZ = 0, bodyY = 0, bodyPz = 0, rate = 12;
      if ((h.st === 'swing' || h.st === 'pull') && h.anchor) {
        // Along the rope, the web hand up to it, legs pulled up under the body (Eero, #529).
        tmpA.set(h.anchor.x - h.x, h.anchor.y - h.y - 1, h.anchor.z - h.z).normalize();
        tmpB.set(h.vx, 0, h.vz); if (tmpB.lengthSq() < 0.01) tmpB.set(Math.sin(h.yaw), 0, Math.cos(h.yaw));
        tmpB.addScaledVector(tmpA, -tmpB.dot(tmpA)).normalize();
        tmpC.crossVectors(tmpA, tmpB);
        basis.makeBasis(tmpC, tmpA, tmpB); m.g.quaternion.setFromRotationMatrix(basis);
        const v = Math.hypot(h.vx, h.vy, h.vz), k = clamp(0.55 + v / 35, 0.55, 1);   // faster, tighter tuck
        m.phase += dt * 2.2;
        const kick = Math.sin(m.phase) * 0.12;
        set('armR', Math.PI, 0, -0.05); set('elbR', 0.05);
        set('armL', -0.5, 0, -1.1); set('elbL', -0.7);
        set('legL', -0.7 - 0.9 * k + kick, 0, -0.12); set('kneeL', 0.9 + 1.1 * k);
        set('legR', -0.5 - 0.9 * k - kick, 0, 0.12); set('kneeR', 1.1 + 1.0 * k);
        bodyX = -0.2;
      } else {
        m.g.quaternion.setFromAxisAngle(up, h.yaw);
        if (h.st === 'wall') {
          // Climbing: hands and feet in turn, knees out to the sides, the body rocking with the steps.
          const moving = Math.hypot(h.vx, h.vy, h.vz);
          m.phase += dt * moving * 1.3;
          const s = Math.sin(m.phase), c = Math.cos(m.phase), still = moving < 0.3;
          const a = still ? 0.15 : 0.5;
          // Arms up and forward onto the wall (-x), hands bent in toward it (Eero, #529).
          set('armL', -(Math.PI * 0.8 + s * a), 0, -0.25); set('elbL', 0.5 - s * 0.45);
          set('armR', -(Math.PI * 0.8 - s * a), 0, 0.25); set('elbR', 0.5 + s * 0.45);
          set('legL', -0.95 - s * a * 0.9, 0, -0.55); set('kneeL', 1.4 + s * a);
          set('legR', -0.95 + s * a * 0.9, 0, 0.55); set('kneeR', 1.4 - s * a);
          bodyPz = 0.05; bodyY = -0.15 + Math.abs(c) * (still ? 0 : 0.06); bodyZ = still ? 0 : s * 0.08;
          rate = 18;
        } else if (h.st === 'ground') {
          m.phase += dt * sp * 1.1;
          const r = Math.min(1, sp / 6), s = Math.sin(m.phase) * r;
          set('legL', s * 0.8); set('kneeL', Math.max(0, -Math.cos(m.phase)) * 1.3 * r + 0.05);
          set('legR', -s * 0.8); set('kneeR', Math.max(0, Math.cos(m.phase)) * 1.3 * r + 0.05);
          set('armL', -s * 0.7, 0, -0.08); set('elbL', -0.3 - r * 0.9);
          set('armR', s * 0.7, 0, 0.08); set('elbR', -0.3 - r * 0.9);
          bodyX = r * 0.15; bodyY = Math.abs(Math.cos(m.phase)) * 0.05 * r;
        } else {
          // In the air: knees up going up, arms and legs out coming down.
          const up_ = clamp(h.vy / 10, -1, 1);
          if (up_ > 0) {
            set('legL', -1.2 * up_, 0, -0.1); set('kneeL', 1.6 * up_ + 0.2);
            set('legR', -0.6 * up_, 0, 0.1); set('kneeR', 1.2 * up_ + 0.3);
          } else {
            set('legL', 0.2, 0, -0.35); set('kneeL', 0.5);
            set('legR', -0.4, 0, 0.35); set('kneeR', 0.9);
          }
          set('armL', -2.2, 0, -0.6); set('elbL', -0.3);
          set('armR', -2.2, 0, 0.6); set('elbR', -0.3);
          bodyX = clamp(-h.vy / 40, -0.5, 0.5);
        }
      }
      // Let go of the web: a backflip with the jump (Eero, #560). Read from the state change alone,
      // so friends' heroes flip on every phone too.
      if (m.lastSt === 'swing' && h.st === 'air') m.flip = 0;
      if (h.st !== 'air') m.flip = -1;
      m.lastSt = h.st;
      const flipping = m.flip >= 0;
      if (flipping) {                         // tucked: knees to the chest, arms round the shins
        set('legL', -1.6, 0, -0.1); set('kneeL', 2.3); set('legR', -1.6, 0, 0.1); set('kneeR', 2.3);
        set('armL', -1.2, 0, -0.2); set('elbL', -0.8); set('armR', -1.2, 0, 0.2); set('elbR', -0.8);
        rate = 20;
      }
      const f = Math.min(1, dt * rate);
      for (const k of JOINTS) {
        const t = J[k] || [0, 0, 0], r = P[k].rotation;
        r.set(r.x + (t[0] - r.x) * f, r.y + (t[1] - r.y) * f, r.z + (t[2] - r.z) * f);
      }
      const br = m.body.rotation, bp = m.body.position;
      // The body's own pose blends in m.b (the flip is laid on top, so it never blends away).
      const B = m.b || (m.b = { x: 0, z: 0, py: 0, pz: 0 });
      B.x += (bodyX - B.x) * f; B.z += (bodyZ - B.z) * f; B.py += (bodyY - B.py) * f; B.pz += (bodyPz - B.pz) * f;
      br.set(B.x, 0, B.z); bp.set(0, B.py, B.pz);
      if (flipping) {
        m.flip += dt;
        const p = Math.min(1, m.flip / FLIP_T), e = p * p * (3 - 2 * p), a = -TAU * e, c = 0.9;   // round the hips, head back first
        br.x += a; bp.y += c - c * Math.cos(a); bp.z -= c * Math.sin(a);
        if (p >= 1) m.flip = -1;
      }
      // Shadow on whatever is under the hero.
      const s = supportAt(h.x, h.z, 0);
      m.shadow.visible = h.st !== 'wall';
      m.shadow.position.set(h.x, s + 0.05, h.z);
      const hgt = h.y - s; m.shadow.scale.setScalar(clamp(1 - hgt / 40, 0.3, 1)); m.shadow.material.opacity = clamp(0.35 - hgt / 120, 0.08, 0.35);
      m.web.visible = (h.st === 'swing' || h.st === 'pull') && !!h.anchor;
      if (m.web.visible) {
        const p = m.web.geometry.attributes.position;
        // The web leaves the hero's right glove (Eero, #529).
        m.g.updateMatrixWorld(true); m.P.handR.getWorldPosition(tmpA);
        p.setXYZ(0, tmpA.x, tmpA.y, tmpA.z); p.setXYZ(1, h.anchor.x, h.anchor.y, h.anchor.z); p.needsUpdate = true;
      }
    }

    // ---- The race's roof: a flag, and a tall light over it that shows from across the city ----
    const things = new T.Group(); scene.add(things);
    const flag = new T.Group(); part(flag, cyl, '#ddd', 0, 2, 0, 0.08, 4, 0.08); part(flag, box, '#ff3b3b', 0.7, 3.5, 0, 1.4, 0.9, 0.05, { emissive: '#ff2020', emissiveIntensity: 0.4 }); things.add(flag);
    const beam = new T.Mesh(new T.CylinderGeometry(2.5, 2.5, 400, 16, 1, true), new T.MeshBasicMaterial({ color: '#ffd166', transparent: true, opacity: 0.35, depthWrite: false, side: T.DoubleSide, fog: false }));
    beam.position.y = 200; flag.add(beam);

    // ---- The camera: behind the hero, kept out of the buildings ----
    const camPos = new T.Vector3(), look = new T.Vector3();
    const inside = (x, y, z) => insideCity(x, y, z, 0.3);
    let camDist = 7, aimK = 0;
    // Aiming with Veto (#560): closer, and over the right shoulder, so the crosshair is clear.
    function place(h, cv, dt, aiming) {
      aimK += ((aiming ? 1 : 0) - aimK) * Math.min(1, dt * 10);
      const wantD = aiming ? 4.5 : h.st === 'wall' ? 8.5 : h.st === 'swing' || h.st === 'pull' ? 9 : 7;
      camDist += (wantD - camDist) * Math.min(1, dt * (aiming ? 8 : 3));
      const p = cv.pitch, cp = Math.cos(p);
      const e = aimEye(h, cv.yaw, aimK);
      look.set(e.x, h.y + 1.5, e.z);
      let d = camDist;
      const dx = -Math.sin(cv.yaw) * cp, dy = Math.sin(p), dz = -Math.cos(cv.yaw) * cp;
      // Stop in front of a wall, not in it: from close by, in small steps (#560: aiming on a wall).
      for (let s = 0.2; s <= camDist; s += 0.2) if (inside(look.x + dx * s, look.y + dy * s, look.z + dz * s)) { d = Math.max(0.1, s - 0.2); break; }
      camPos.set(look.x + dx * d, look.y + dy * d, look.z + dz * d);
      cam.position.copy(camPos); cam.lookAt(look.x, look.y + 0.4, look.z);
    }

    let tuneT = 0, tuneN = 0, tuneSum = 0;
    function resize() {
      const w = glc.clientWidth || innerWidth, h = glc.clientHeight || innerHeight;
      rd.setSize(w, h, false); cam.aspect = w / h; cam.fov = w > h ? 62 : 72; cam.updateProjectionMatrix();
    }
    L3D.resize = resize; resize();
    L3D.camAt = () => [camPos.x, camPos.y, camPos.z];   // for the tests
    const pv = new T.Vector3();
    L3D.project = (x, y, z) => {
      pv.set(x, y, z).project(cam);
      if (pv.z > 1 || pv.z < -1) return null;
      return [(pv.x + 1) / 2 * glc.clientWidth, (1 - pv.y) / 2 * glc.clientHeight];
    };
    L3D.draw = (s, dt) => {
      // s = { w, hero, heroes: [{h, col, id}], cam, playing }
      const seen = new Set();
      for (const o of s.heroes) {
        let m = heroes.get(o.id);
        if (!m) { m = makeHero(o.col); heroes.set(o.id, m); }
        poseHero(m, o.h, dt); seen.add(o.id);
      }
      for (const [id, m] of heroes) if (!seen.has(id)) { m.g.visible = false; m.shadow.visible = false; m.web.visible = false; }
      const w = s.w, now = performance.now() / 1000;
      flag.visible = !!(w && w.flag); if (flag.visible) { flag.position.set(w.flag.x, w.flag.y, w.flag.z); flag.children[1].rotation.y = Math.sin(now * 3) * 0.3; }
      const h = s.hero;
      if (h) place(h, s.cam, dt, !!s.aiming);
      rd.render(scene, cam);
      L3D.ready = true;
      // A slow phone: fewer pixels (#103's lesson).
      if (tuneT < 6 && s.playing) {
        tuneT += dt; tuneN++; tuneSum += dt;
        if (tuneT > 2.5 && tuneN > 20 && tuneSum / tuneN > 1 / 40 && pr > 0.75) { pr = Math.max(0.75, pr - 0.35); rd.setPixelRatio(pr); resize(); tuneT = 0; tuneN = 0; tuneSum = 0; }
      }
    };
  }).catch(() => { L3D.failed = true; });
})();
