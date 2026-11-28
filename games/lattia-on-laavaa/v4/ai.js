'use strict';
// Lattia on laavaa v3: the computer's kids (#488). In Koko talo (#526) they also go up the stairs
// once a staircase's door opens: to the piece in front of it, onto the bottom step, and up.
// v2: Each looks round every so often (its reaction
// time), picks the piece that will last longest within a jump, runs at it and jumps at the edge.
// It aims a little off (its error), and now and then shoves a kid in front of it.
const SKILL = [
  // v2 (#505): slower and less exact, and they shove less (v1: 0.55/0.35/0.12, 0.4/0.25/0.25, 0.3/0.16/0.45).
  { react: 0.85, err: 0.7, shove: 0.06, look: 2.2 },    // Olohuone
  { react: 0.5, err: 0.32, shove: 0.15, look: 2.6 },    // Lastenhuone
  { react: 0.38, err: 0.22, shove: 0.3, look: 2.8 },    // Keittiö
];
function cpuBrain(level, seed) {
  const s = SKILL[clamp(level, 0, SKILL.length - 1)];
  return { ...s, r: rng(seed), t: 0, target: null, oldSc: 0, ox: 0, oz: 0, jumpT: 0 };
}
// How long a thing to stand on will still be there, s.
function lifeLeft(w, s, rt) {
  // A step or a floor of the house lasts until the lava reaches its top.
  if (s.id[0] === 's') return Math.max(0, lavaWhen(w, s.top - 0.03) - rt);
  if (s.id[0] === 'p') {
    const p = w.pieces[+s.id.slice(1)];
    // In the house the rising lava may come first.
    const drown = w.house ? Math.max(0, lavaWhen(w, p.h0 - 0.03) - rt) : Infinity;
    if (rt < p.wobAt) return Math.min(drown, p.wobAt - rt + WOBBLE + 1);
    return Math.min(drown, Math.max(0, (topOf(p, rt) - lavaAt(rt, w)) / SINK_V + Math.max(0, p.sinkAt - rt)));
  }
  const f = floatOf(w, +s.id.slice(1));
  return Math.max(0, f.life - 2 - (rt - f.t0));
}
// The nearest gap from the kid to a box, along the floor.
function gapTo(k, s) {
  const dx = Math.max(0, Math.abs(k.x - s.x) - s.w / 2), dz = Math.max(0, Math.abs(k.z - s.z) - s.d / 2);
  return Math.hypot(dx, dz);
}
// The gap between two boxes, along the floor.
function boxGap(a, s) {
  const dx = Math.max(0, Math.abs(a.x - s.x) - (a.w + s.w) / 2), dz = Math.max(0, Math.abs(a.z - s.z) - (a.d + s.d) / 2);
  return Math.hypot(dx, dz);
}
// One frame of thinking: sets the kid's stick and jump. Returns true when it wants to shove.
function cpuThink(w, k, b, dt, sol) {
  k.jump = false;
  if (k.out || w.ph !== 'play') { k.ix = k.iz = 0; return false; }
  const rt = w.rt;
  const cur = k.ground ? sol.find(s => s.id === k.gpId) : null;
  b.t -= dt;
  // Up the stairs in the house: on a step, walk on up; on the way, the route picks the target.
  const route = w.house ? stairRoute(w, k, b, cur, sol) : null;
  if (route && route.walk) {
    const dx = route.x - k.x, dz = route.z - k.z, d = Math.hypot(dx, dz) || 1;
    k.ix = dx / d; k.iz = dz / d;
    return false;
  }
  if (route) b.t = Math.max(b.t, 0.05);
  if (b.t <= 0) {
    b.t = b.react * (0.7 + b.r() * 0.6);
    const curLife = cur ? lifeLeft(w, cur, rt) : 0;
    let best = null, bs = -Infinity;
    for (const s of sol) {
      if (cur && s.id === cur.id) continue;
      // Walls and doors are never stood on; steps are only for the way up (stairRoute()).
      if (s.wall || s.kind === 'step') continue;
      // Never back down a floor of the house: the way down is shut by the stair walls.
      if (w.house && floorOfY(s.top - 0.05) < floorOfY(k.y + 0.05)) continue;
      const gap = gapTo(k, s), rise = s.top - k.y;
      if (rise > 1.25) continue;
      // Out of a jump's reach: only as a place to head for, its edge first (see below).
      if (gap > b.look && !(cur && curLife < 8)) continue;
      const crowd = w.kids.filter(o => o !== k && !o.out && inside(s, o.x, o.z, 0.1)).length;
      const area = Math.min(1.5, s.w * s.d);
      const sc = Math.min(12, lifeLeft(w, s, rt)) - gap * 0.8 - (gap > b.look ? 4 : 0) - crowd * 1.2 * area ** -0.5 + area * 0.5 + (b.r() - 0.5) * b.err * 6;
      if (sc > bs) { bs = sc; best = s; }
    }
    // Stay put while where it stands lasts well and nothing is much better; once on the way to a
    // target, keep it unless it is going or something is clearly better (no turning at an edge).
    const old = b.target ? sol.find(s => s.id === b.target) : null;
    if (old && lifeLeft(w, old, rt) > 3 && best && best.id !== old.id && bs < b.oldSc + 2) best = old;
    if (cur && curLife > 5 && !old && (!best || bs < Math.min(12, curLife) + 1.5)) b.target = null;
    else if (best) { b.target = best.id; if (best !== old) b.oldSc = bs; }
    b.ox = (b.r() - 0.5) * b.err; b.oz = (b.r() - 0.5) * b.err;
  }
  let tgt = b.target ? sol.find(s => s.id === b.target) : null;
  if (b.target && !tgt) b.target = null;
  if (tgt && cur && tgt.id === cur.id) { b.target = null; tgt = null; }
  let ax, az;
  // A target out of reach: wait on the edge of where it stands nearest to it.
  const far = tgt && cur && gapTo(k, tgt) > b.look;
  if (far) {
    const m = 0.28;
    ax = clamp(tgt.x, cur.x - cur.w / 2 + m, cur.x + cur.w / 2 - m); az = clamp(tgt.z, cur.z - cur.d / 2 + m, cur.z + cur.d / 2 - m);
  } else if (tgt) {
    // Lead a moving float by where it will be on landing.
    ax = tgt.x + tgt.vx * 0.5 + b.ox; az = tgt.z + tgt.vz * 0.5 + b.oz;
  } else if (cur) {
    // Idle near the middle of where it stands, a little off it, never at the edge.
    ax = cur.x + b.ox * cur.w * 0.5; az = cur.z + b.oz * cur.d * 0.5;
  } else { ax = k.x; az = k.z; }
  const dx = ax - k.x, dz = az - k.z, d = Math.hypot(dx, dz);
  if (d > 0.12) { const sp = tgt || !cur ? 1 : Math.min(1, d * 1.5); k.ix = dx / d * sp; k.iz = dz / d * sp; }
  else { k.ix = k.iz = 0; }
  if (cur && cur.vx) { k.ix += cur.vx / RUN * (tgt ? 0 : 1); }
  // Never run off an edge with nothing to jump to: back towards the middle.
  if (cur && k.ground && (!tgt || far) && !inside(cur, k.x + k.vx * 0.15, k.z + k.vz * 0.15, -0.05)) {
    const bx = cur.x - k.x, bz = cur.z - k.z, bd = Math.hypot(bx, bz) || 1;
    k.ix = bx / bd; k.iz = bz / bd;
  }
  // Jump: at the edge of where it stands, on the way to the target, or at a taller piece close by.
  if (tgt && k.ground && !far) {
    const ahead = !inside(cur || tgt, k.x + k.vx * 0.12, k.z + k.vz * 0.12, 0);
    const tall = tgt.top - k.y > STEP_UP && gapTo(k, tgt) < 0.7;
    if (ahead || tall || !cur) b.jumpT = 0.18;
  }
  if (b.jumpT > 0) { b.jumpT -= dt; k.jump = true; }
  // In the air, keep the jump held while rising: a full jump goes furthest.
  if (!k.ground && tgt && k.vy > 0) k.jump = true;
  // A shove, at a kid in front and close.
  if (rt > 4 && k.cd <= 0 && k.ground && b.r() < b.shove * dt * 2) {
    // Only where its own dash (about 1.6 m) would still end on what it stands on. The dash now
    // stops at the edge anyway (#505); kept, so they never shove from a small piece: easier.
    const ex = k.x + Math.cos(k.face) * SHOVE_V * SHOVE_T, ez = k.z + Math.sin(k.face) * SHOVE_V * SHOVE_T;
    const o = cur && inside(cur, ex, ez, -0.1) ? shoveTarget(w, k, k.face) : null;
    if (o) return true;
  }
  return false;
}

// The way up in Koko talo (#526): once the door of the staircase on this kid's floor is open,
// head for the piece in front of it (the last of its floor to sink), jump onto the bottom step,
// then walk up to the landing. Returns null when there is no way up to take, {walk, x, z} on the
// stairs, or {} after setting the brain's target.
function stairRoute(w, k, b, cur, sol) {
  const n = floorOfY(k.y + 0.05);
  if (n > 1 || w.rt < HOUSE.open[n]) return null;
  const sx = STAIR_X[n];
  // On the stairs (or right over them): straight up to the landing; the steps are walked.
  if (cur && cur.kind === 'step' && cur.stair === n) return { walk: true, x: sx, z: (Z0 + STAIR_Z0) / 2 };
  // The lowest step the lava has left: the bottom ones go under first.
  const step1 = sol.filter(s => s.kind === 'step' && s.stair === n).sort((a, b) => a.step - b.step)[0];
  // In the air on the way to the stairs: keep heading for what it jumped at.
  if (!cur && b.target && sol.some(s => s.id === b.target)) return {};
  const front = sol.find(s => s.id[0] === 'p' && w.pieces[+s.id.slice(1)].order === 4 && w.pieces[+s.id.slice(1)].floor === n);
  let goal = cur && front && cur.id === front.id ? step1 : front || step1;
  if (!goal) return null;
  // Out of a jump's reach: hop to whatever is nearest the goal and nearer than here (within a
  // jump of the edge of where it stands; cpuThink() runs to that edge first).
  const reach = s => cur ? Math.min(gapTo(k, s), boxGap(cur, s)) : gapTo(k, s);
  if (reach(goal) > b.look) {
    const dist = s => Math.hypot(s.x - goal.x, s.z - goal.z);
    const here = cur ? dist(cur) : Math.hypot(k.x - goal.x, k.z - goal.z);
    let best = null, bd = here - 0.3;
    for (const s of sol) {
      if (s === cur || s.wall || s.kind === 'step' || s.top - k.y > 1.25 || floorOfY(s.top - 0.05) !== n) continue;
      if (reach(s) > b.look || lifeLeft(w, s, w.rt) < 1.5 || dist(s) >= bd) continue;
      best = s; bd = dist(s);
    }
    if (!best) return null;
    goal = best;
  }
  b.target = goal.id;
  return {};
}
