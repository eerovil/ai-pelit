'use strict';
// Jäälautta v1: the computer's seals. A brain reads the world and writes only its seal's stick and
// lunge counter, so the host in a room drives them with the same rules as alone.
//
// Every `react` seconds it decides again: back from its own edge, to the gull's ring when it is
// close, to another seal with a fuse to pass on, away from one coming with a fuse, and otherwise
// round behind the seal nearest an edge to shove it outwards. Its aim misses by up to `err`
// degrees, and now and then it slips (a short wrong stick), so it falls in by itself sometimes.

const CPU_NAMES = ['Hylje-Hessu', 'Norppa', 'Kuutti', 'Möhkäle', 'Pullukka', 'Liukas', 'Viiksi'];

function cpuBrain(skill, seed) {
  return { react: skill.react, err: skill.err * Math.PI / 180, rand: rng(seed), wait: 0, tx: 0, ty: 0, mode: 'go', slip: 0, sx: 0, sy: 0 };
}
function cpuThink(w, sl, b, dt) {
  if (sl.out || w.ph !== 'play') { sl.ix = sl.iy = 0; return; }
  if (b.slip > 0) { b.slip -= dt; sl.ix = b.sx; sl.iy = b.sy; return; }
  b.wait -= dt;
  if (b.wait <= 0) {
    b.wait = b.react * (0.7 + b.rand() * 0.6);
    decide(w, sl, b);
    if (sl.want > sl.lunges) return;   // a lunge just aimed: keep its stick this frame
  }
  // Steer to the target point, braking as it gets near.
  const dx = b.tx - sl.x, dy = b.ty - sl.y, d = Math.hypot(dx, dy);
  if (d < 0.25) { sl.ix = -sl.vx * 0.3; sl.iy = -sl.vy * 0.3; return; }
  const want = Math.min(1, d / 2);
  // Aim at where it should be going, less the speed it already has.
  let ax = dx / d * want * 5 - sl.vx, ay = dy / d * want * 5 - sl.vy;
  const m = Math.hypot(ax, ay) || 1;
  sl.ix = ax / m * Math.min(1, m / 2); sl.iy = ay / m * Math.min(1, m / 2);
}
function decide(w, sl, b) {
  const here = partOf(w, sl.x, sl.y), p = here.p;
  const others = w.seals.filter(o => o !== sl && !o.out);
  // A slip: a short push the wrong way.
  if (b.rand() < 0.06 * (b.err / 0.4 + 0.3)) {
    const a = b.rand() * TAU; b.slip = 0.25 + b.rand() * 0.3; b.sx = Math.cos(a); b.sy = Math.sin(a);
    return;
  }
  const edgeSafe = 2.2 * radiusOf(sl) / SEAL_R;
  // Too near my own edge, or a hole opening under me: back to the middle of my part.
  const hole = w.holes.find(o => Math.hypot(sl.x - o.x, sl.y - o.y) < o.r + 0.8);
  if (here.edge < edgeSafe || hole) {
    b.tx = p.x; b.ty = p.y;
    if (hole) { b.tx = sl.x + (sl.x - hole.x) * 2; b.ty = sl.y + (sl.y - hole.y) * 2; }
    return;
  }
  // I hold a fuse: to the nearest seal, to pass it on (and lunge into it).
  if (sl.fuse && others.length) {
    const o = nearest(sl, others);
    b.tx = o.x; b.ty = o.y;
    if (Math.hypot(o.x - sl.x, o.y - sl.y) < 3.5) lungeAt(sl, b, o.x, o.y);
    return;
  }
  // Someone near me holds one: away from them.
  const fz = others.find(o => o.fuse && Math.hypot(o.x - sl.x, o.y - sl.y) < 4.5);
  if (fz) {
    const dx = sl.x - fz.x, dy = sl.y - fz.y, d = Math.hypot(dx, dy) || 1;
    b.tx = sl.x + dx / d * 2.5; b.ty = sl.y + dy / d * 2.5;
    if (!onIce(w, b.tx, b.ty) || partOf(w, b.tx, b.ty).edge < edgeSafe) { b.tx = p.x; b.ty = p.y; }
    return;
  }
  // The gull's ring, when it is nearer to me than to the others.
  if (w.ring && w.ring.come <= 0) {
    const dr = Math.hypot(w.ring.x - sl.x, w.ring.y - sl.y);
    if (dr < 6 && others.every(o => Math.hypot(w.ring.x - o.x, w.ring.y - o.y) > dr * 0.8)) { b.tx = w.ring.x; b.ty = w.ring.y; return; }
  }
  if (!others.length) { b.tx = p.x; b.ty = p.y; return; }
  // The seal to shove: near me and near its edge.
  let tgt = null, best = -Infinity;
  for (const o of others) {
    const e = partOf(w, o.x, o.y).edge, d = Math.hypot(o.x - sl.x, o.y - sl.y);
    const sc = -d - e * 1.2 + (o.kind !== 'cpu' ? 0.5 : 0);
    if (sc > best) { best = sc; tgt = o; }
  }
  // Stand on the far side of it from its edge's way out, then lunge through it, outwards.
  const tp = partOf(w, tgt.x, tgt.y).p;
  let ox = tgt.x - tp.x, oy = tgt.y - tp.y;
  const ol = Math.hypot(ox, oy) || 1; ox /= ol; oy /= ol;
  const sx = tgt.x - ox * 2.4, sy = tgt.y - oy * 2.4;
  const dS = Math.hypot(sx - sl.x, sy - sl.y), dT = Math.hypot(tgt.x - sl.x, tgt.y - sl.y);
  if (dS < 1.4 || dT < 2.6) {
    b.tx = tgt.x + ox; b.ty = tgt.y + oy;
    const bx = tgt.x - sl.x, by = tgt.y - sl.y, bl = Math.hypot(bx, by) || 1;
    // Lined up, pushing outwards: lunge (its aim misses a little).
    if ((bx * ox + by * oy) / bl > 0.5 && dT < 3.2) lungeAt(sl, b, tgt.x, tgt.y);
  } else if (onIce(w, sx, sy) && partOf(w, sx, sy).edge > edgeSafe * 0.6) { b.tx = sx; b.ty = sy; }
  else { b.tx = tgt.x; b.ty = tgt.y; }
}
function nearest(sl, list) {
  let o = null, bd = Infinity;
  for (const x of list) { const d = Math.hypot(x.x - sl.x, x.y - sl.y); if (d < bd) { bd = d; o = x; } }
  return o;
}
function lungeAt(sl, b, x, y) {
  if (sl.cd > 0) return;
  const a = Math.atan2(y - sl.y, x - sl.x) + (b.rand() - 0.5) * 2 * b.err;
  sl.face = a;
  sl.ix = Math.cos(a); sl.iy = Math.sin(a);
  sl.want = sl.lunges + 1;
}
