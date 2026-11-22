'use strict';
// Seittisankari v1 (#529): the city and the hero's movement, in plain numbers (no three.js), so
// tests can drive the game frame by frame. Metres and seconds; y is up, the street is y = 0.
// Buildings are boxes, so every wall is one flat face and a roof is one flat top.

const TAU = Math.PI * 2;
const STEP = 1 / 120;
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}

// ---- The city: a 42 × 42 grid of lots (about 1.7 km across), streets between ----
// Eero asked for a city about 50 times bigger (#529). The old 6 × 6 downtown sits in the middle,
// built first from the same seed, so its tower and the missions' buildings stay as they were;
// the rest thins out toward the edge, with a few smaller clusters of high-rises and some parks.
const LOT = 40, GRID = 42, EDGE = LOT * GRID / 2 - 6;
const C0 = (GRID - 6) / 2;                         // the downtown's first lot
const lotX = i => (i - (GRID - 1) / 2) * LOT;
const lotOf = x => Math.round(x / LOT + (GRID - 1) / 2);
const TOWER = { i: C0 + 3, j: C0 + 2 };
const CLUSTERS = [[7, 9, 75], [33, 8, 60], [31, 33, 85], [9, 32, 55], [20, 36, 45]];   // lot i, lot j, extra height
const LOTS = new Array(GRID * GRID).fill(null);   // the building on each lot, or null (a park)
function makeCity() {
  const boxes = [];
  const add = (i, j, hw, hd, h, ox, oz, col, water) => {
    const cx = lotX(i), cz = lotX(j);
    const b = { id: boxes.length, i, j, x0: cx + ox - hw, x1: cx + ox + hw, z0: cz + oz - hd, z1: cz + oz + hd, h,
      col, tower: i === TOWER.i && j === TOWER.j, water };
    boxes.push(b); LOTS[i * GRID + j] = b;
  };
  let r = rng(529);
  for (let a = 0; a < 6; a++) for (let c = 0; c < 6; c++) {
    const mid = Math.max(Math.abs(a - 2.5), Math.abs(c - 2.5));       // 0.5 in the middle, 2.5 at the edge
    let hw = 9 + r() * 4, hd = 9 + r() * 4, h;
    const i = C0 + a, j = C0 + c;
    if (i === TOWER.i && j === TOWER.j) { hw = hd = 12; h = 220; }
    else h = Math.round(18 + (2.6 - mid) * 26 + r() * r() * 70);
    const ox = (r() - 0.5) * (13 - hw) * 0.8, oz = (r() - 0.5) * (13 - hd) * 0.8;
    add(i, j, hw, hd, h, ox, oz, Math.floor(r() * 4), r() < 0.35);
  }
  r = rng(5290);
  const c = (GRID - 1) / 2;
  for (let i = 0; i < GRID; i++) for (let j = 0; j < GRID; j++) {
    if (i >= C0 && i < C0 + 6 && j >= C0 && j < C0 + 6) continue;
    const d = Math.max(Math.abs(i - c), Math.abs(j - c)) - 2.5;          // lots out from the downtown
    let extra = 0;
    for (const [ci, cj, eh] of CLUSTERS) extra = Math.max(extra, eh * Math.exp(-((i - ci) ** 2 + (j - cj) ** 2) / 8));
    if (d > 1 && extra < 15 && r() < 0.08) { r(); r(); r(); continue; }   // a park
    const hw = 8 + r() * 5, hd = 8 + r() * 5;
    const h = Math.round(12 + 62 * Math.exp(-d / 5) + extra * (0.6 + r() * 0.5) + r() * r() * 45);
    const ox = (r() - 0.5) * (13 - hw) * 0.8, oz = (r() - 0.5) * (13 - hd) * 0.8;
    add(i, j, hw, hd, h, ox, oz, Math.floor(r() * 4), r() < 0.3);
  }
  return boxes;
}
const CITY = makeCity();
const boxAt = (i, j) => LOTS[i * GRID + j];
const roofTop = b => ({ x: (b.x0 + b.x1) / 2, y: b.h, z: (b.z0 + b.z1) / 2 });
// Every building that may reach within `r` of (x, z): only the lots around it, not the whole city.
// A building stays inside its own lot, at most 17 m from the lot's middle.
function eachNear(x, z, r, fn) {
  const k = Math.ceil((r + 17) / LOT - 0.5) + 1;
  const i0 = Math.max(0, lotOf(x) - k), i1 = Math.min(GRID - 1, lotOf(x) + k);
  const j0 = Math.max(0, lotOf(z) - k), j1 = Math.min(GRID - 1, lotOf(z) + k);
  for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) { const b = LOTS[i * GRID + j]; if (b && fn(b) === true) return true; }
  return false;
}

// The highest roof under a point (with the hero's radius), or the street.
function supportAt(x, z, r) {
  let s = 0;
  eachNear(x, z, r, b => { if (x > b.x0 - r && x < b.x1 + r && z > b.z0 - r && z < b.z1 + r && b.h > s) s = b.h; });
  return s;
}

// ---- The hero ----
const R = 0.4, HERO_H = 1.7;
const RUN = 10, CLIMB = 6, JUMP = 10.5, G = 28, WEB_MAX = 45, ROPE_MIN = 5, VMAX = 48, REEL_LOW = 20, LOW_ARC = 8,
  ROPE_K = 9, ROPE_DAMP = 1.2, ROPE_STRETCH = 30;   // the web gives a little, like a stiff bungee (Eero, #529)
function newHero(x, y, z, yaw) {
  return { x, y, z, vx: 0, vy: 0, vz: 0, st: 'ground', yaw: yaw || 0, nx: 0, nz: 0, box: null,
    anchor: null, rope: 0, wallCd: 0, jumped: false, webbed: 0, steps: 0 };
}

// Where a web shot now would stick: a point high on a building's side ahead of the camera.
// `fx, fz` is the direction the player looks (or flies). Null when nothing is in reach.
// Where a web sticks: up in the sky ahead of where the camera looks, like the old 3D hero games
// (Eero's choice on #529). No building is needed, so a swing always goes the way the camera
// points. On a wall the web goes out from it, never into it.
const SKY_AHEAD = 45, SKY_UP = 180, SKY_MIN = 280, SKY_NEAR = 70, SKY_OVER = 160;   // far up in the sky (Eero, #529)
function aimAnchor(h, fx, fz) {
  const fm = Math.hypot(fx, fz) || 1; fx /= fm; fz /= fm;
  if (h.st === 'wall' && fx * h.nx + fz * h.nz < 0.2) {
    // Looking at the wall: the web goes out from it, a little toward where the camera looks.
    fx = h.nx + fx * 0.4; fz = h.nz + fz * 0.4;
    const m = Math.hypot(fx, fz) || 1; fx /= m; fz /= m;
  }
  const x = clamp(h.x + fx * SKY_AHEAD, -EDGE, EDGE), z = clamp(h.z + fz * SKY_AHEAD, -EDGE, EDGE);
  // The sky has a ceiling: a little above the tallest building near, so chained swings cannot
  // climb for ever. Too high over the roofs, there is nothing to hang from: no web.
  let top = SKY_MIN;
  eachNear(x, z, SKY_NEAR, b => {
    const dx = Math.max(b.x0 - x, 0, x - b.x1), dz = Math.max(b.z0 - z, 0, z - b.z1);
    if (dx * dx + dz * dz < SKY_NEAR * SKY_NEAR) top = Math.max(top, b.h + SKY_OVER);
  });
  const y = Math.min(h.y + SKY_UP, top);
  if (y < h.y + 6) return null;
  return { x, y, z, box: -1, fx, fz };
}

// The input for one step: stick (ix right, iy down, -1..1), held buttons, the camera's yaw.
// in = { ix, iy, jump (pressed this step), web (held), yaw }
function stepHero(h, inp, dt) {
  h.steps++;
  const fx = Math.sin(inp.yaw), fz = Math.cos(inp.yaw);   // camera forward
  const rx = -fz, rz = fx;                                // camera right
  const mx = rx * inp.ix - fx * inp.iy, mz = rz * inp.ix - fz * inp.iy;   // wanted move, length ≤ 1
  const mm = Math.hypot(mx, mz);
  if (h.wallCd > 0) h.wallCd -= dt;

  // Web pressed: start a swing (from any state) when there is a point to stick to.
  if (inp.web && h.st !== 'swing' && !h.webbed) {
    const a = aimAnchor(h, fx, fz);
    h.webbed = 1;
    if (a) {
      h.anchor = a; h.rope = Math.hypot(a.x - h.x, a.y - h.y, a.z - h.z);
      // Nothing is added: the swing keeps the hero's own speed and gravity does the rest (Eero, #529).
      if (h.st === 'wall') h.wallCd = 0.3;
      if (h.st === 'ground') h.vy = Math.max(h.vy, 6);    // off the street
      h.yaw = Math.atan2(a.fx, a.fz);
      h.st = 'swing'; h.box = null;
    }
  }
  if (!inp.web) h.webbed = 0;
  if (h.st === 'swing' && !inp.web) {
    h.st = 'air'; h.anchor = null;
  }

  if (h.st === 'wall') return stepWall(h, inp, dt, mx, mz);

  if (h.st === 'ground') {
    // Run: speed follows the stick quickly; a fast landing keeps some of its speed.
    const k = Math.min(1, dt * (mm > 0.1 ? 8 : 10));
    h.vx += (mx * RUN - h.vx) * k; h.vz += (mz * RUN - h.vz) * k;
    if (mm > 0.1) h.yaw = Math.atan2(mx, mz);
    if (inp.jump) { h.vy = JUMP; h.st = 'air'; h.jumped = true; }
  } else {
    h.vy -= G * dt;
    // A little steering in the air, more while swinging (pumping).
    const a = h.st === 'swing' ? 3.5 : 2.5;   // heavy: little steering in the air (Eero, #529)
    h.vx += mx * a * dt; h.vz += mz * a * dt;
    if (mm > 0.1) h.yaw = Math.atan2(h.vx, h.vz);
  }
  const sp = Math.hypot(h.vx, h.vy, h.vz);
  if (sp > VMAX) { h.vx *= VMAX / sp; h.vy *= VMAX / sp; h.vz *= VMAX / sp; }
  h.x += h.vx * dt; h.y += h.vy * dt; h.z += h.vz * dt;

  if (h.st === 'swing') {
    const a = h.anchor;
    // Reel in only while the swing's lowest point would scrape the street, so a web from the
    // street lifts the hero into a swing. Otherwise the rope keeps its length: reeling in lifts
    // the hero, which made speed out of nothing (Eero, #529).
    if (a.y - h.rope < supportAt(h.x, h.z, R) + LOW_ARC) h.rope = Math.max(ROPE_MIN, h.rope - REEL_LOW * dt);
    const dx = h.x - a.x, dy = h.y - a.y, dz = h.z - a.z, d = Math.hypot(dx, dy, dz);
    if (d > h.rope) {
      // An elastic web: past its length it pulls back like a spring, so a fall stretches it and
      // carries on down a while before the web swings the hero out (Eero, #529). A hard stop
      // only at ROPE_STRETCH, so nothing tunnels.
      const ux = dx / d, uy = dy / d, uz = dz / d, vr = h.vx * ux + h.vy * uy + h.vz * uz;
      const pull = ROPE_K * (d - h.rope) + ROPE_DAMP * vr;
      if (pull > 0) { h.vx -= ux * pull * dt; h.vy -= uy * pull * dt; h.vz -= uz * pull * dt; }
      if (d > h.rope + ROPE_STRETCH) {
        const m = h.rope + ROPE_STRETCH;
        h.x = a.x + ux * m; h.y = a.y + uy * m; h.z = a.z + uz * m;
        const v2 = h.vx * ux + h.vy * uy + h.vz * uz;
        if (v2 > 0) { h.vx -= ux * v2; h.vy -= uy * v2; h.vz -= uz * v2; }
      }
    }
  }
  collide(h, mx, mz, mm);
  // The city's edge stops the hero, and its speed out that way (a swing kept gaining speed there).
  if (Math.abs(h.x) > EDGE) { h.x = clamp(h.x, -EDGE, EDGE); if (h.vx * h.x > 0) h.vx = 0; }
  if (Math.abs(h.z) > EDGE) { h.z = clamp(h.z, -EDGE, EDGE); if (h.vz * h.z > 0) h.vz = 0; }
}

// Walls and roofs. A wall touched in the air (or run into on the ground) is grabbed.
function collide(h, mx, mz, mm) {
  const nb = [];
  eachNear(h.x, h.z, R + 1, b => { nb.push(b); });
  for (const b of nb) {
    if (h.y >= b.h - 0.001 || h.y + HERO_H <= 0) continue;
    if (h.x <= b.x0 - R || h.x >= b.x1 + R || h.z <= b.z0 - R || h.z >= b.z1 + R) continue;
    const pen = [h.x - (b.x0 - R), (b.x1 + R) - h.x, h.z - (b.z0 - R), (b.z1 + R) - h.z];
    const top = b.h - h.y;
    const m = Math.min(...pen);
    if (top < 0.7 && h.vy <= 0.5 && top <= m + 0.5) {      // landed on the roof
      h.y = b.h; if (h.vy < 0) h.vy = 0;
      if (h.st !== 'ground') land(h);
      continue;
    }
    const nx = m === pen[0] ? -1 : m === pen[1] ? 1 : 0, nz = nx ? 0 : m === pen[2] ? -1 : 1;
    if (nx) h.x = nx < 0 ? b.x0 - R : b.x1 + R; else h.z = nz < 0 ? b.z0 - R : b.z1 + R;
    const into = h.vx * nx + h.vz * nz;
    if (into < 0) { h.vx -= nx * into; h.vz -= nz * into; }
    const pushes = mm > 0.3 && (mx * nx + mz * nz) / mm < -0.5;
    if (h.wallCd <= 0 && (h.st === 'air' || h.st === 'swing' || pushes)) grabWall(h, b, nx, nz);
  }
  if (h.st !== 'wall') {
    const s = supportAt(h.x, h.z, R * 0.5);
    if (h.y <= s && (h.st !== 'ground')) { h.y = s; if (h.vy < 0) h.vy = 0; land(h); }
    else if (h.st === 'ground' && h.y > s + 0.05) h.st = 'air';
    else if (h.st === 'ground') h.y = s;
  }
}
function land(h) { h.st = 'ground'; h.anchor = null; h.vy = 0; h.lands = (h.lands || 0) + 1; }
function grabWall(h, b, nx, nz) {
  h.st = 'wall'; h.box = b; h.nx = nx; h.nz = nz; h.anchor = null;
  h.vx = h.vy = h.vz = 0;
  h.yaw = Math.atan2(-nx, -nz);
}

function stepWall(h, inp, dt, mx, mz) {
  const b = h.box;
  if (inp.jump) {                      // push off the wall, away and up
    h.st = 'air'; h.vx = h.nx * 8; h.vz = h.nz * 8; h.vy = JUMP; h.wallCd = 0.35; h.box = null; h.jumped = true;
    return;
  }
  // Up the wall with the stick's up, along it with the stick's side (as the camera sees it).
  const tx = -h.nz, tz = h.nx;          // along the face
  const fx = Math.sin(inp.yaw), fz = Math.cos(inp.yaw), rx = -fz, rz = fx;
  const side = (tx * rx + tz * rz) >= 0 ? 1 : -1;
  h.y += -inp.iy * CLIMB * dt;
  h.x += tx * side * inp.ix * CLIMB * dt; h.z += tz * side * inp.ix * CLIMB * dt;
  h.vx = tx * side * inp.ix * CLIMB; h.vz = tz * side * inp.ix * CLIMB; h.vy = -inp.iy * CLIMB;
  if (Math.abs(inp.ix) > 0.2 || Math.abs(inp.iy) > 0.2) h.climbT = (h.climbT || 0) + dt;
  // Round a corner onto the next face.
  if (h.nx) {
    if (h.z > b.z1) { h.nx = 0; h.nz = 1; h.z = b.z1 + R; h.x = h.x < (b.x0 + b.x1) / 2 ? b.x0 + 0.01 : b.x1 - 0.01; }
    else if (h.z < b.z0) { h.nx = 0; h.nz = -1; h.z = b.z0 - R; h.x = h.x < (b.x0 + b.x1) / 2 ? b.x0 + 0.01 : b.x1 - 0.01; }
  } else {
    if (h.x > b.x1) { h.nz = 0; h.nx = 1; h.x = b.x1 + R; h.z = h.z < (b.z0 + b.z1) / 2 ? b.z0 + 0.01 : b.z1 - 0.01; }
    else if (h.x < b.x0) { h.nz = 0; h.nx = -1; h.x = b.x0 - R; h.z = h.z < (b.z0 + b.z1) / 2 ? b.z0 + 0.01 : b.z1 - 0.01; }
  }
  if (h.nx) h.x = h.nx < 0 ? b.x0 - R : b.x1 + R; else h.z = h.nz < 0 ? b.z0 - R : b.z1 + R;
  h.yaw = Math.atan2(-h.nx, -h.nz);
  // Over the top onto the roof.
  if (h.y >= b.h - 0.3) {
    h.y = b.h; h.x -= h.nx * (R + 0.6); h.z -= h.nz * (R + 0.6);
    h.st = 'ground'; h.box = null; h.vx = h.vz = h.vy = 0; h.wallCd = 0.2;
    return;
  }
  // Down to the street.
  if (h.y <= 0) { h.y = 0; h.st = 'ground'; h.box = null; h.x += h.nx * 0.05; h.z += h.nz * 0.05; h.wallCd = 0.4; return; }
  // Another building's roof right under the hero (a low neighbour): stand on it.
}
