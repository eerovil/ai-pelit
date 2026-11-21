'use strict';
// Jäälautta drawn in 3D (v2, #478). three.js renders the sea, the floe and the seals on a WebGL
// canvas under the game's own 2D canvas, which keeps the HUD, the stick and the button. The game's
// world (world.js) is unchanged: this only reads it each frame. A phone that cannot draw
// WebGL (J3D.failed) keeps playing on the 2D drawing in ui.js.
window.J3D = { ready: false, failed: false };
(function () {
  const glc = document.getElementById('g');
  window.J3D_LIB.then(T => {
    let rd;
    try { rd = new T.WebGLRenderer({ canvas: glc, antialias: true }); } catch (e) { J3D.failed = true; return; }
    rd.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
    rd.shadowMap.enabled = true; rd.shadowMap.type = T.PCFSoftShadowMap;
    const scene = new T.Scene();
    scene.background = new T.Color('#0b2f55');
    scene.fog = new T.Fog('#0b2f55', 45, 110);
    const cam = new T.PerspectiveCamera(38, 1, 0.5, 300);
    scene.add(new T.HemisphereLight('#e4f4ff', '#123a66', 1.5));
    const sun = new T.DirectionalLight('#fff4e0', 2.4);
    sun.position.set(-10, 28, 12); sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024); sun.shadow.bias = -0.0008;
    Object.assign(sun.shadow.camera, { left: -18, right: 18, top: 18, bottom: -18, near: 5, far: 80 });
    scene.add(sun, sun.target);

    // ---- The sea: a gently moving faceted plane ----
    const SEA_Y = -0.35;
    const seaG = new T.PlaneGeometry(160, 160, 64, 64); seaG.rotateX(-Math.PI / 2);
    const seaP = seaG.attributes.position, seaX = Float32Array.from({ length: seaP.count }, (_, i) => seaP.getX(i)), seaZ = Float32Array.from({ length: seaP.count }, (_, i) => seaP.getZ(i));
    const sea = new T.Mesh(seaG, new T.MeshStandardMaterial({ color: '#155a96', roughness: 0.3, metalness: 0.15, flatShading: true }));
    sea.position.y = SEA_Y; sea.receiveShadow = true; scene.add(sea);
    function waves(t) {
      for (let i = 0; i < seaP.count; i++) seaP.setY(i, Math.sin(seaX[i] * 0.45 + t * 1.1) * 0.07 + Math.cos(seaZ[i] * 0.5 + t * 1.4) * 0.06);
      seaP.needsUpdate = true;
    }

    // ---- The floe: each part an extruded outline, rebuilt when its edge changes ----
    const ICE_D = 0.9, BEV = 0.14;
    const capM = new T.MeshStandardMaterial({ color: '#eef8ff', roughness: 0.55 });
    const sideM = new T.MeshStandardMaterial({ color: '#8cc4e8', roughness: 0.25, metalness: 0.05 });
    const floes = [];
    function floeGeo(p) {
      const sh = new T.Shape();
      for (let k = 0; k < 72; k++) {
        const a = k / 72 * TAU, r = Math.max(0.05, edgeAt(p, a) - BEV);
        const x = p.x + Math.cos(a) * r, y = -(p.y + Math.sin(a) * r);
        k ? sh.lineTo(x, y) : sh.moveTo(x, y);
      }
      const g = new T.ExtrudeGeometry(sh, { depth: ICE_D, bevelEnabled: true, bevelThickness: BEV, bevelSize: BEV, bevelSegments: 2, curveSegments: 1 });
      g.rotateX(-Math.PI / 2); g.translate(0, -ICE_D, 0);
      return g;
    }
    function drawFloes(w) {
      w.parts.forEach((p, i) => {
        const sig = p.r.map(r => r.toFixed(3)).join(',') + p.x + p.y;
        let f = floes[i];
        if (!f) { f = floes[i] = new T.Mesh(undefined, [capM, sideM]); f.receiveShadow = true; f.castShadow = true; scene.add(f); }
        f.visible = p.r.some(r => r > 0.05);
        if (f.sig !== sig && f.visible) { if (f.geometry) f.geometry.dispose(); f.geometry = floeGeo(p); f.sig = sig; }
      });
      for (let i = w.parts.length; i < floes.length; i++) floes[i].visible = false;
    }

    // ---- Per-frame bits: cracks, holes, the gull's ring, snowballs ----
    const tmp = new T.Group(); scene.add(tmp);
    const crackM = [new T.LineBasicMaterial({ color: '#2a6fa8' }), new T.LineBasicMaterial({ color: '#7fb8e0' })];
    const holeM = new T.MeshStandardMaterial({ color: '#0d3a66', roughness: 0.2 });
    const holeG = new T.CylinderGeometry(1, 1, 0.06, 32);
    const ringM = new T.MeshStandardMaterial({ color: '#ffcc33', emissive: '#ffaa00', emissiveIntensity: 1.2 });
    const ringG = new T.TorusGeometry(1, 0.09, 8, 48); ringG.rotateX(Math.PI / 2);
    const glowM = new T.MeshBasicMaterial({ color: '#fff0a0', transparent: true, opacity: 0.35, depthWrite: false });
    const glowG = new T.CircleGeometry(1, 40); glowG.rotateX(-Math.PI / 2);
    const snowM = new T.MeshStandardMaterial({ color: '#ffffff', roughness: 0.9 });
    const snowG = new T.IcosahedronGeometry(1, 2);
    const whiteM = new T.MeshStandardMaterial({ color: '#ffffff', roughness: 0.6 });
    const lampM = new T.MeshStandardMaterial({ color: '#ffd84a', emissive: '#ffb000', emissiveIntensity: 1.5 });
    const ball = new T.SphereGeometry(1, 16, 12);
    const box = new T.BoxGeometry(1, 1, 1);
    function line(pts, m) { const g = new T.BufferGeometry().setFromPoints(pts.map(([x, y, z]) => new T.Vector3(x, y, z))); tmp.add(new T.Line(g, m)); }
    function clearTmp() { for (const o of [...tmp.children]) { if (o.geometry && o.geometry !== holeG && o.geometry !== ringG && o.geometry !== glowG && o.geometry !== snowG && o.geometry !== ball && o.geometry !== box) o.geometry.dispose(); tmp.remove(o); } }
    function mesh(g, m, x, y, z, sx, sy, sz) { const o = new T.Mesh(g, m); o.position.set(x, y, z); o.scale.set(sx, sy === undefined ? sx : sy, sz === undefined ? sx : sz); tmp.add(o); return o; }
    function drawBits(w, clock) {
      clearTmp();
      const flash = Math.floor(clock * 8) % 2;
      for (const b of w.warn) {
        const p = w.parts[b.p], a0 = (b.i - 1) / WEDGES * TAU, a1 = (b.i + 2) / WEDGES * TAU;
        const rIn = edgeAt(p, (a0 + a1) / 2) - 1.6 * w.scale, pts = [];
        for (let k = 0; k <= 8; k++) { const a = a0 + (a1 - a0) * k / 8, r = rIn + (k % 2 ? 0.25 : -0.2); pts.push([p.x + Math.cos(a) * r, 0.03, p.y + Math.sin(a) * r]); }
        line(pts, crackM[flash]);
      }
      for (const o of w.holes) {
        if (o.open > 0) mesh(holeG, holeM, o.x, -0.01, o.y, o.r, 1, o.r);
        else for (let k = 0; k < 5; k++) { const a = k * 1.3; line([[o.x, 0.03, o.y], [o.x + Math.cos(a) * o.r, 0.03, o.y + Math.sin(a) * o.r]], crackM[flash]); }
      }
      const r = w.ring;
      if (r) {
        const k = r.come > 0 ? r.come / RING_COME : 0;
        if (r.come <= 0) {
          const pulse = 0.75 + Math.sin(clock * 6) * 0.25;
          mesh(ringG, ringM, r.x, 0.05, r.y, RING_R);
          const gl = mesh(glowG, glowM, r.x, 0.02, r.y, RING_R * 1.4); gl.material = glowM; glowM.opacity = 0.3 * pulse;
          const q = mesh(ball, lampM, r.x, 0.5 + Math.sin(clock * 3) * 0.12, r.y, 0.22);
        }
        // The gull with its lantern, flying in from the side and hovering above the ring.
        const gx = r.x - k * 14, gy = 3.4 + k * 5, gz = r.y - 1 - k * 4, fl = Math.sin(clock * 10) * 0.5;
        const wl = mesh(box, whiteM, gx - 0.45, gy, gz, 0.9, 0.05, 0.3); wl.rotation.z = 0.35 + fl;
        const wr = mesh(box, whiteM, gx + 0.45, gy, gz, 0.9, 0.05, 0.3); wr.rotation.z = -0.35 - fl;
        mesh(ball, whiteM, gx, gy, gz, 0.2, 0.18, 0.32);
        line([[gx, gy, gz], [gx, gy - 0.7, gz]], crackM[1]);
        mesh(ball, lampM, gx, gy - 0.8, gz, 0.14);
      }
      for (const s of w.snow) { const o = mesh(snowG, snowM, s.x, s.r, s.y, s.r); o.rotation.x = s.roll; o.castShadow = true; }
    }

    // ---- The seals ----
    const seals = new Map();
    function sealModel(hatC) {
      const g = new T.Group(), parts = {};
      const bodyM = new T.MeshStandardMaterial({ color: '#8a93a3', roughness: 0.45 });
      const darkM = new T.MeshStandardMaterial({ color: '#666d7b', roughness: 0.6 });
      const blackM = new T.MeshStandardMaterial({ color: '#1a1a1a', roughness: 0.3 });
      const hatM = new T.MeshStandardMaterial({ color: hatC, roughness: 0.7 });
      const add = (geo, m, x, y, z, sx, sy, sz, par) => { const o = new T.Mesh(geo, m); o.position.set(x, y, z); o.scale.set(sx, sy, sz); o.castShadow = true; (par || g).add(o); return o; };
      parts.body = add(ball, bodyM, -0.15, 0.55, 0, 1.08, 0.6, 0.82);
      add(ball, bodyM, 0.62, 0.88, 0, 0.55, 0.52, 0.55);                 // head
      add(ball, blackM, 1.08, 1.0, -0.22, 0.08, 0.09, 0.08);              // eyes
      add(ball, blackM, 1.08, 1.0, 0.22, 0.08, 0.09, 0.08);
      add(ball, blackM, 1.17, 0.86, 0, 0.08, 0.06, 0.08);                 // nose
      const hat = new T.SphereGeometry(1, 16, 8, 0, TAU, 0, Math.PI / 2);
      add(hat, hatM, 0.56, 1.18, 0, 0.42, 0.36, 0.42);                    // beanie
      add(ball, whiteM, 0.56, 1.58, 0, 0.13, 0.13, 0.13);                 // pompom
      for (const s of [-1, 1]) {
        const tail = add(ball, darkM, -1.2, 0.18, s * 0.3, 0.38, 0.07, 0.18); tail.rotation.y = s * 0.5;
        const piv = new T.Group(); piv.position.set(0.15, 0.4, s * 0.7); g.add(piv);
        const fl = add(ball, darkM, 0, 0, s * 0.25, 0.18, 0.07, 0.38, piv);
        parts[s < 0 ? 'fl' : 'fr'] = piv;
      }
      parts.bodyM = bodyM;
      const root = new T.Group(); root.add(g); root.userData = { g, parts };
      return root;
    }
    const meM = new T.MeshBasicMaterial({ color: '#ffd84a', transparent: true, opacity: 0.9 });
    const meG = new T.TorusGeometry(1, 0.09, 6, 40); meG.rotateX(Math.PI / 2);
    const meRing = new T.Mesh(meG, meM); scene.add(meRing);
    const splashM = new T.MeshBasicMaterial({ color: '#dff2ff', transparent: true, depthWrite: false });
    const cloudM = new T.MeshStandardMaterial({ color: '#5a6070', roughness: 1 });
    const iceM = new T.MeshStandardMaterial({ color: '#bfe6ff', roughness: 0.15, transparent: true, opacity: 0.85 });
    const LOOK = 1.25, TOP = BEV;  // seals drawn a little larger than their hit circle; the ice's top
    const qa = new T.Quaternion(), qb = new T.Quaternion(), up = new T.Vector3(0, 1, 0), ax = new T.Vector3();
    function drawSeals(w, clock, me) {
      const seen = new Set();
      meRing.visible = false;
      for (const sl of w.seals) {
        seen.add(sl);
        let m = seals.get(sl);
        if (!m) { m = sealModel(HATS[sl.hat % HATS.length].c); seals.set(sl, m); scene.add(m); }
        const { g, parts } = m.userData, R = radiusOf(sl);
        m.scale.setScalar(R * LOOK);
        if (sl.out) {
          // In the water: only the head and hat above the waves, bobbing, with rings spreading.
          const t = sl.out;
          m.position.set(sl.outX, SEA_Y - 0.75 * R * LOOK + Math.sin(clock * 3 + sl.i) * 0.06, sl.outY);
          m.quaternion.setFromAxisAngle(up, -sl.face);
          for (let k = 0; k < 3; k++) {
            const rr = ((t * 1.5 + k * 0.6) % 2.5) + 0.3, o = mesh(ringG, splashM, sl.outX, SEA_Y + 0.1, sl.outY, rr, 1, rr * 0.9);
            o.material = splashM; splashM.opacity = Math.max(0, 0.7 - t * 0.3);
          }
          continue;
        }
        const tee = sl.teeter > 0, rock = tee ? Math.sin(clock * 9 + sl.i) : 0;
        m.position.set(sl.x + Math.cos(sl.ta) * rock * 0.12, TOP, sl.y + Math.sin(sl.ta) * rock * 0.12);
        qa.setFromAxisAngle(up, -sl.face);
        if (tee) {
          // Tipping over the edge towards the water, rocking.
          ax.set(Math.sin(sl.ta), 0, -Math.cos(sl.ta)).normalize();
          qb.setFromAxisAngle(ax, -(0.35 + rock * 0.2)); m.quaternion.copy(qb).multiply(qa);
        } else m.quaternion.copy(qa);
        // A lunge stretches it forwards; a stun greys it.
        g.scale.set(sl.lungeT > 0 ? 1.18 : 1, sl.lungeT > 0 ? 0.92 : 1, 1);
        parts.bodyM.color.set(sl.stun > 0 ? '#c3c9d6' : '#8a93a3');
        const fl = Math.sin(clock * 12 + sl.i) * (tee ? 0.9 : Math.hypot(sl.vx, sl.vy) > 0.5 ? 0.35 : 0.05);
        parts.fl.rotation.x = fl; parts.fr.rotation.x = -fl;
        if (sl === me) { meRing.visible = true; meRing.position.set(sl.x, TOP + 0.03, sl.y); meRing.scale.setScalar(R * LOOK * 1.35); }
        if (sl.fuse) {
          const h = TOP + R * LOOK * 2.1 + 0.6;
          if (sl.fuse.k === 'ukko') for (const [dx, rr] of [[-0.5, 0.45], [0, 0.62], [0.5, 0.45]]) mesh(ball, cloudM, sl.x + dx, h + Math.sin(clock * 2) * 0.05, sl.y, rr, rr * 0.75, rr);
          else { const s = 0.55 + (LOHK_T - sl.fuse.t) * 0.07, o = mesh(box, iceM, sl.x, h, sl.y, s); o.rotation.y = clock; o.castShadow = true; }
        }
      }
      for (const [sl, m] of seals) if (!seen.has(sl)) { scene.remove(m); seals.delete(sl); }
    }

    // ---- Camera: the play box's middle on the floe's middle, the whole floe in view ----
    const v3 = new T.Vector3();
    let lastW = 0, lastH = 0;
    J3D.render = function (w, clock, box, me) {
      const Wd = innerWidth, Hd = innerHeight;
      if (Wd !== lastW || Hd !== lastH) { rd.setSize(Wd, Hd, false); lastW = Wd; lastH = Hd; }
      let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
      for (const p of w.parts) { bx0 = Math.min(bx0, p.x - p.r0); bx1 = Math.max(bx1, p.x + p.r0); by0 = Math.min(by0, p.y - p.r0); by1 = Math.max(by1, p.y + p.r0); }
      const cxw = (bx0 + bx1) / 2, cyw = (by0 + by1) / 2, hw = (bx1 - bx0) / 2 + 1.2, hh = (by1 - by0) / 2 + 1.2;
      const elev = 60 * Math.PI / 180;   // a steep look from the south (the owner picked it over a low one)
      const bw = box.x1 - box.x0, bh = box.y1 - box.y0;
      // Pixels per world unit at the target, so the floe's width and foreshortened depth fit the box.
      const s = Math.min(bw / 2 / hw, bh / 2 / (hh * Math.sin(elev) + 1.6 * Math.cos(elev))) * 0.9;
      const tanF = Math.tan(cam.fov * Math.PI / 360), d = (Hd / 2) / (s * tanF);
      cam.aspect = Wd / Hd;
      cam.position.set(cxw, d * Math.sin(elev), cyw + d * Math.cos(elev));
      cam.lookAt(cxw, 0, cyw);
      scene.fog.near = d + 15; scene.fog.far = d + 90;
      cam.setViewOffset(Wd, Hd, Wd / 2 - (box.x0 + box.x1) / 2, Hd / 2 - (box.y0 + box.y1) / 2, Wd, Hd);
      cam.updateProjectionMatrix();
      sun.target.position.set(cxw, 0, cyw); sun.position.set(cxw - 10, 28, cyw + 12);
      waves(clock);
      drawFloes(w); drawBits(w, clock); drawSeals(w, clock, me);
      rd.render(scene, cam);
    };
    // A world point (x, height, y) on the screen, in CSS pixels.
    J3D.project = function (x, h, y) { v3.set(x, h, y).project(cam); return [(v3.x + 1) / 2 * lastW, (1 - v3.y) / 2 * lastH]; };
    J3D.show = on => { glc.style.display = on ? 'block' : 'none'; };
    J3D.ready = true;
    if (window.wake) wake();
  }).catch(() => { J3D.failed = true; });
})();
