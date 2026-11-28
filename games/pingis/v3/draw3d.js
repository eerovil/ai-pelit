'use strict';
// Pingis v1: the hall, the table, the bats and the ball in 3D (three.js, the site's shared copy,
// #99). It only reads the game (world.js) and the bats. index.html imports three.js and calls
// init3d(THREE); a phone that cannot draw 3D plays on a flat table drawn by ui.js (draw2d()).
// World units are metres: the table top is y = 0, side 0 plays at the +z end. The camera sits
// behind the end of the side this phone plays (`view`), so turning it is only the camera.

let THREE = null, V3 = null, no3d = false;

function init3d(T) {
  THREE = T;
  const gl = document.getElementById('g');
  const renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#1c2a44');
  scene.fog = new THREE.Fog(0x1c2a44, 9, 22);
  const camera = new THREE.PerspectiveCamera(60, 1, 0.05, 60);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x3a3020, 1.5));
  const sun = new THREE.DirectionalLight(0xfff4e0, 1.4);
  sun.position.set(1.5, 6, 2);
  scene.add(sun);
  V3 = { renderer, scene, camera, w: 0, h: 0, view: -1, t: 0, frames: 0, ms: 0, tuned: false, v: new THREE.Vector3(), ray: new THREE.Raycaster(), plane: null };
  V3.down = new THREE.Vector3(0, -1, 0);
  V3.plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -0.12);
  hall(scene);
  scene.add(table());
  V3.bats = [batRig('#d8282f'), batRig('#2c5fd0')];
  V3.figs = [null, null];
  for (const b of V3.bats) scene.add(b.g);
  const ballMat = new THREE.MeshLambertMaterial({ color: new THREE.Color('#ffa63d'), emissive: new THREE.Color('#5a3000') });
  V3.ball = new THREE.Mesh(new THREE.SphereGeometry(0.03, 16, 12), ballMat);
  V3.trail = [0, 1, 2, 3, 4].map(k => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.026 - k * 0.003, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffc070, transparent: true, opacity: 0.35 - k * 0.06, depthWrite: false }));
    scene.add(m); return m;
  });
  V3.shadow = new THREE.Mesh(new THREE.CircleGeometry(0.03, 16), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.4, depthWrite: false }));
  V3.shadow.rotation.x = -Math.PI / 2;
  scene.add(V3.ball, V3.shadow);
  V3.past = [];
}
const lambert = hex => new THREE.MeshLambertMaterial({ color: new THREE.Color(hex) });

// A floor of boards, dark walls with a light stripe, a few lamps.
function hall(scene) {
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), lambert('#a5683a'));
  floor.rotation.x = -Math.PI / 2; floor.position.y = FLOOR;
  scene.add(floor);
  const lines = lambert('#8e5630');
  for (let k = -14; k <= 14; k += 0.6) {
    const l = new THREE.Mesh(new THREE.PlaneGeometry(0.02, 30), lines);
    l.rotation.x = -Math.PI / 2; l.position.set(k, FLOOR + 0.001, 0); scene.add(l);
  }
  const wall = lambert('#2a3c63'), stripe = lambert('#e8c34a');
  for (const [x, z, ry] of [[0, -8, 0], [0, 8, Math.PI], [-6, 0, Math.PI / 2], [6, 0, -Math.PI / 2]]) {
    const w = new THREE.Mesh(new THREE.PlaneGeometry(16, 6), wall);
    w.position.set(x, FLOOR + 3, z); w.rotation.y = ry; scene.add(w);
    const s = new THREE.Mesh(new THREE.PlaneGeometry(16, 0.18), stripe);
    s.position.set(x * 0.999, FLOOR + 1.2, z * 0.999); s.rotation.y = ry; scene.add(s);
  }
  // Low barriers round the court.
  const bar = lambert('#c8283a');
  for (const [x, z, w, d] of [[0, -4.2, 6, 0.04], [0, 4.2, 6, 0.04], [-3, 0, 0.04, 8.4], [3, 0, 0.04, 8.4]]) {
    const b = new THREE.Mesh(new THREE.BoxGeometry(w, 0.5, d), bar);
    b.position.set(x, FLOOR + 0.25, z); scene.add(b);
  }
}
// The table: a blue top with white lines, the net on its posts, four legs.
function table() {
  const g = new THREE.Group(), white = lambert('#f4f4f0');
  const top = new THREE.Mesh(new THREE.BoxGeometry(HW * 2, 0.03, HL * 2), lambert('#1f5aa8'));
  top.position.y = -0.015; g.add(top);
  const line = (w, d, x, z) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, 0.002, d), white); m.position.set(x, 0.001, z); g.add(m); };
  line(0.02, HL * 2, -HW + 0.01, 0); line(0.02, HL * 2, HW - 0.01, 0);
  line(HW * 2, 0.02, 0, -HL + 0.01); line(HW * 2, 0.02, 0, HL - 0.01);
  line(0.006, HL * 2, 0, 0);
  const net = new THREE.Mesh(new THREE.PlaneGeometry(HW * 2 + 0.3, NET_H), new THREE.MeshLambertMaterial({ color: 0x222831, transparent: true, opacity: 0.55, side: THREE.DoubleSide }));
  net.position.y = NET_H / 2; g.add(net);
  const tape = new THREE.Mesh(new THREE.BoxGeometry(HW * 2 + 0.3, 0.015, 0.01), white);
  tape.position.y = NET_H; g.add(tape);
  for (const x of [-HW - 0.15, HW + 0.15]) {
    const p = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, NET_H + 0.03, 8), lambert('#1a1a1a'));
    p.position.set(x, NET_H / 2, 0); g.add(p);
  }
  const leg = lambert('#30343c');
  for (const x of [-HW + 0.15, HW - 0.15]) for (const z of [-HL + 0.25, HL - 0.25]) {
    const l = new THREE.Mesh(new THREE.BoxGeometry(0.05, -FLOOR, 0.05), leg);
    l.position.set(x, FLOOR / 2 - 0.02, z); g.add(l);
  }
  return g;
}
// A bat: a round blade with coloured rubber and a wooden handle, its face towards the net.
function batRig(col) {
  const g = new THREE.Group();
  const blade = new THREE.Mesh(new THREE.CylinderGeometry(0.078, 0.078, 0.014, 24), lambert(col));
  blade.rotation.x = Math.PI / 2; blade.position.y = 0.06;
  const edge = new THREE.Mesh(new THREE.TorusGeometry(0.078, 0.005, 6, 24), lambert('#d8b080'));
  edge.position.y = 0.06;
  const handle = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.1, 0.022), lambert('#c08a50'));
  handle.position.y = -0.03;
  g.add(blade, edge, handle);
  return { g, blade };
}
// A player behind their bat, dressed in an outfit of the 3D games' shared set (v3, #573:
// lib/asut3d-1, the person of AiPelitAsut3d.figure(): 1.8 tall, feet at y 0, facing +z). `g` is
// turned to face the net and stands on the floor; `id` is the outfit it wears. Without the
// library it is v2's simple figure in the outfit's top colour.
function dressFig(side, o) {
  const id = o ? o.id : null, old = V3.figs[side];
  if (old && old.id === id) return old;
  if (old) V3.scene.remove(old.g);
  const g = new THREE.Group();
  let J = null;
  if (window.AiPelitAsut3d && o) {
    const p = AiPelitAsut3d.figure(THREE, o);
    J = p.userData.joints;
    J.armL.rotation.x = -0.5; J.elbL.rotation.x = -0.6;   // the free hand up a little
    g.add(p);
  } else {
    const col = (o && o.top) || (side === 0 ? '#e8463a' : '#3a74e8');
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.2, 0.62, 12), lambert(col));
    body.position.y = 1.15;
    const legs = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.13, 0.84, 10), lambert('#2a2a36'));
    legs.position.y = 0.42;
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.13, 14, 10), lambert('#f0c8a0'));
    head.position.y = 1.6;
    g.add(body, legs, head);
  }
  const f = { g, J, id, side };
  V3.figs[side] = f;
  V3.scene.add(g);
  return f;
}
// The bat arm (armR, at x 0.33 of a figure that faces +z) points at the bat.
const SHOULDER = { x: 0.33, y: 1.38 };
function poseFig(f, b) {
  const s = sgn(f.side), face = f.side === 0 ? Math.PI : 0;   // side 0 (+z end) looks towards -z
  // The bat arm's shoulder in world x, turned with the figure.
  const sx = f.side === 0 ? -SHOULDER.x : SHOULDER.x;
  f.g.position.set((b.x - sx) * 0.85, FLOOR, b.z + s * 0.48);
  f.g.rotation.y = face;
  if (!f.J) return;
  // The bat in the figure's own frame (it is only turned about y), from the shoulder.
  const wx = b.x - f.g.position.x, wy = b.y - FLOOR - SHOULDER.y, wz = b.z - f.g.position.z;
  const c = Math.cos(face), sn = Math.sin(face);
  const lx = c * wx - sn * wz, lz = sn * wx + c * wz;
  const d = V3.v.set(lx - SHOULDER.x, wy, lz).normalize();
  f.J.armR.quaternion.setFromUnitVectors(V3.down, d);
  f.J.elbR.rotation.x = -0.15;
}

// The camera behind `side`'s end, far enough back that the near end of the table fits the width.
function placeCamera(side, aspect) {
  const cam = V3.camera, s = sgn(side), land = aspect > 1;
  cam.fov = land ? 48 : 62; cam.aspect = aspect; cam.updateProjectionMatrix();
  const hf = Math.atan(Math.tan(cam.fov * Math.PI / 360) * aspect);
  const back = clamp((HW + 0.08) / Math.tan(hf) - 0.2, 1.5, 3.4);
  cam.position.set(0, land ? 0.95 : 1.15, s * (HL + back));
  cam.lookAt(0, -0.1, -s * (land ? 0.55 : 0.35));
}

function render3d(st, dt) {
  const R = V3.renderer, cv = R.domElement, cw = cv.clientWidth || innerWidth, ch = cv.clientHeight || innerHeight;
  V3.t += dt;
  if (cw !== V3.w || ch !== V3.h || V3.view !== st.view || V3.menu !== !!st.menu) {
    V3.w = cw; V3.h = ch; V3.view = st.view; V3.menu = !!st.menu; R.setSize(cw, ch, false);
    placeCamera(st.view, cw / ch);
    // The menu (#573) shows my player at the far end above its buttons: the picture slides up
    // (portrait) or left (sideways), into the room the menu leaves free.
    if (st.menu) V3.camera.setViewOffset(cw, ch, cw > ch ? cw * 0.3 : 0, cw > ch ? 0 : ch * 0.2, cw, ch);
    else V3.camera.clearViewOffset();
  }
  const ball = st.ball;
  [0, 1].forEach(side => {
    const b = st.bats[side], rig = V3.bats[side], s = sgn(side);
    rig.g.position.set(b.x, b.y, b.z);
    // The face looks at the net, tilted by the swing.
    rig.g.rotation.set(-s * 0.25 - clamp(b.swing || 0, -1, 1) * 0.5 * s, side === 0 ? 0 : Math.PI, clamp(-b.vx * 0.15, -0.5, 0.5));
    // Each player wears their outfit (st.outfits); the one behind the camera is not drawn.
    const fig = dressFig(side, st.outfits[side]), show = side !== st.view;
    fig.g.visible = show;
    if (show) poseFig(fig, b);
  });
  V3.ball.visible = V3.shadow.visible = !!ball;
  if (ball) {
    V3.ball.position.set(ball.x, ball.y, ball.z);
    const onTable = Math.abs(ball.x) < HW && Math.abs(ball.z) < HL;
    const gy = onTable ? 0.002 : FLOOR + 0.002;
    V3.shadow.position.set(ball.x, gy, ball.z);
    V3.shadow.scale.setScalar(clamp(1 - (ball.y - gy) * 0.4, 0.4, 1.2));
    V3.past.unshift([ball.x, ball.y, ball.z]);
  } else V3.past.length = 0;
  if (V3.past.length > 12) V3.past.length = 12;
  V3.trail.forEach((m, k) => {
    const p = V3.past[2 + k * 2];
    m.visible = !!p && !!ball && st.moving;
    if (m.visible) m.position.set(p[0], p[1], p[2]);
  });
  R.render(V3.scene, V3.camera);
}
// Screen px of a world point (the tests put a finger on the bat and the ball with it).
function project3d(x, y, z) {
  const v = V3.v.set(x, y, z).project(V3.camera);
  return { x: (v.x + 1) / 2 * V3.w, y: (1 - v.y) / 2 * V3.h, behind: v.z > 1 };
}
// The table point (x, z) under a finger at screen px, on the plane a little over the table, or
// null when the finger points above the horizon.
function unproject3d(px, py) {
  if (!V3.w) return null;
  const nd = { x: px / V3.w * 2 - 1, y: 1 - py / V3.h * 2 };
  V3.ray.setFromCamera(nd, V3.camera);
  const hit = V3.ray.ray.intersectPlane(V3.plane, V3.v);
  return hit ? { x: hit.x, z: hit.z } : null;
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
