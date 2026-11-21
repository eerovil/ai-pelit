'use strict';
// Pomppukeppi v1: the computer's hares. A brain reads the world and writes only its hare's `want`
// (the next hop's direction), so the host in a room drives them by the same rules as alone.
//
// Once per hop, a moment before it lands (later on easier boards), it picks a goal: the cash-in
// box once it holds enough squares (a number it draws again after each cash-in), a "?" box that
// is near, or else the nearest square that is not its own (others' squares a little before blank
// ones). It walks there by the shortest way round rocks and holes. Now and then (`err`) it hops a
// wrong way instead, so it can be beaten.

const CPU_NAMES = ['Jussi', 'Pupu', 'Hoppa', 'Vipeltäjä', 'Loikka', 'Ruska', 'Pomppu'];

function cpuBrain(skill, seed) {
  const r = rng(seed);
  const b = { skill, rand: r, hop: -1, goal: 0 };
  b.goal = drawGoal(b);
  return b;
}
function drawGoal(b) { const [a, c] = b.skill.cashAt; return a + Math.floor(b.rand() * (c - a + 1)); }

// The shortest way from (x, y) to every square, round rocks, holes and the squares next to it that
// another hare holds right now. Returns the first hop towards each square.
function routes(w, h) {
  const n = w.n, first = new Int8Array(n * n).fill(-1), dist = new Int16Array(n * n).fill(-1);
  const q = [h.y * n + h.x];
  dist[q[0]] = 0;
  for (let i = 0; i < q.length; i++) {
    const c = q[i], x = c % n, y = (c / n) | 0;
    for (let d = 0; d < 4; d++) {
      const nx = x + DIRS[d][0], ny = y + DIRS[d][1];
      if (!passable(w, nx, ny)) continue;
      const k = ny * n + nx;
      if (dist[k] >= 0) continue;
      if (i === 0 && taken(w, h, nx, ny)) continue;
      dist[k] = dist[c] + 1; first[k] = i === 0 ? d : first[c];
      q.push(k);
    }
  }
  return { first, dist };
}
function cpuThink(w, h, b) {
  if (w.ph !== 'play') { h.want = -1; return; }
  // A cash-in since last time: aim for a new amount.
  if (h.cashN !== b.cashSeen) { b.cashSeen = h.cashN; b.goal = drawGoal(b); }
  // Decide once per hop, `react` (in parts of a hop) before landing.
  if (h.hopN === b.hop || h.p < 1 - b.skill.react * 1.4) return;
  b.hop = h.hopN;
  const n = w.n, { first, dist } = routes(w, h);
  if (b.rand() < b.skill.err) {
    const ok = [0, 1, 2, 3].filter(d => canHop(w, h, d));
    h.want = ok.length ? ok[Math.floor(b.rand() * ok.length)] : -1;
    return;
  }
  const held = ownCount(w, h);
  const go = (x, y) => { const k = y * n + x; h.want = dist[k] > 0 ? first[k] : -1; return dist[k] > 0; };
  if (w.cash) {
    const dc = dist[w.cash.y * n + w.cash.x];
    // Enough squares, or the box right by it and something to cash, or the erä nearly over.
    if (dc > 0 && (held >= b.goal || (dc <= 2 && held >= b.goal / 2) || (ERA_T - w.t < 6 && held >= 3)) && go(w.cash.x, w.cash.y)) return;
  }
  if (w.qbox) { const dq = dist[w.qbox.y * n + w.qbox.x]; if (dq > 0 && dq <= 3 && go(w.qbox.x, w.qbox.y)) return; }
  let best = -1, bestS = Infinity;
  for (let k = 0; k < n * n; k++) {
    if (dist[k] <= 0 || w.tiles[k] === h.i) continue;
    const s = dist[k] - (w.tiles[k] >= 0 ? 0.4 : 0) + b.rand() * 0.6;
    if (s < bestS) { bestS = s; best = k; }
  }
  h.want = best >= 0 ? first[best] : -1;
}
