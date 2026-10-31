'use strict';
// The chart screen in the navigation room and the autopilot set from it (v9, #160).
// ---------- the chart screen (v9, #160) ----------
// Opened only in the navigation room. Drag to move, pinch or +/− to zoom; a tap on a contact tells what is known of it
// and offers the autopilot. The game goes on behind it for everyone else; this phone's person stands still.
const CV = { x: 0, y: 0, z: 1, sel: null, ptrs: new Map(), moved: 0, pinch: 0 };
function chartFit() { const c = $('chartC'); return Math.min(c.clientWidth / 4600, (c.clientHeight - 90) / 1500); }
function openChart() {
  show('chart', true);
  G.paused = true; G.card = 'chart';
  const c = $('chartC'), w = c.clientWidth;
  // first about 450 m across upright (700 m sideways), on SISU
  CV.z = Math.max(w / 700, c.clientHeight / 900); CV.x = sub.x; CV.y = sub.y; CV.sel = null;
  drawChart();
  if (!G.s.flags.merikartta && !G.chartSaid) {
    G.chartSaid = true;
    if (!net || net.host) { G.s.flags.merikartta = true; save(); }
    card('🗺️ Merikartta', [
      { t: 'Kartta piirtyy sitä mukaa kuin tutkit: pingit, SISUn valonheitin ja sukellukset tuovat siihen merenpohjaa ja jäävuoren luolia.' },
      { t: '❓ sonar kuuli jotain · ◆ ping tunnisti sen · ● näit sen läheltä', c: 'msg' },
      { t: 'Napauta tunnistettua kohdetta: 🧭 autopilotti vie SISUn sinne, ja sillä välin voit liikkua veneessä.', c: 'small' }],
    [{ label: 'Selvä', cls: 'go', fn: () => { closeCard(); G.paused = true; G.card = 'chart'; } }]);
  }
}
function closeChart() { show('chart', false); G.paused = false; G.card = ''; }
function chartZoom(f, cx, cy) {
  const c = $('chartC'), w = c.clientWidth, h = c.clientHeight, z = Math.max(chartFit(), Math.min(9, CV.z * f));
  if (cx != null) { CV.x += (cx - w / 2) / CV.z - (cx - w / 2) / z; CV.y += (cy - h / 2) / CV.z - (cy - h / 2) / z; }
  CV.z = z; drawChart();
}
// What the chart knows of a contact: 0 nothing, 1 heard, 2 known (its kind), 3 seen (its name).
function knowOf(c) { const s = G.s; return s.seen[c.id] ? 3 : s.known[c.id] ? 2 : s.heard[c.id] ? 1 : 0; }
function chartContacts() { return contacts().filter(c => knowOf(c) > 0); }
function drawChart() {
  if (!G.s || $('chart').classList.contains('hidden')) return;
  const cv2 = $('chartC'), w = cv2.clientWidth, h = cv2.clientHeight, dpr = DPR, c = cv2.getContext('2d');
  if (cv2.width !== Math.round(w * dpr) || cv2.height !== Math.round(h * dpr)) { cv2.width = Math.round(w * dpr); cv2.height = Math.round(h * dpr); }
  // keep the view on the sea
  const z = CV.z = Math.max(chartFit(), Math.min(9, CV.z));
  CV.x = Math.max(Math.min(w / 2 / z, 2250), Math.min(WORLD_W - Math.min(w / 2 / z, 2250), CV.x));
  CV.y = Math.max(-80 - 70 / z + Math.min(h / 2 / z, 760), Math.min(1440 - Math.min(h / 2 / z, 760), CV.y));
  const ox = w / 2 - CV.x * z, oy = h / 2 - CV.y * z, X0 = -ox / z, X1 = (w - ox) / z, Y0 = -oy / z, Y1 = (h - oy) / z;
  const P = (x, y) => [ox + x * z, oy + y * z];
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.fillStyle = '#07131d'; c.fillRect(0, 0, w, h);
  c.save(); c.translate(ox, oy); c.scale(z, z);
  // sky, water by depth, the sea floor and the glacier
  c.fillStyle = '#1a2a3c'; c.fillRect(0, -80, WORLD_W, 80);
  const g = c.createLinearGradient(0, 0, 0, 1400); g.addColorStop(0, '#1f5576'); g.addColorStop(0.3, '#123a55'); g.addColorStop(1, '#081d2e');
  c.fillStyle = g; c.fillRect(0, 0, WORLD_W, 1460);
  c.fillStyle = '#5b4a35'; c.strokeStyle = '#a08560'; c.lineWidth = 1.6 / z;
  c.beginPath(); c.moveTo(0, 1460); FLOOR.forEach(([x, y]) => c.lineTo(x, y)); c.lineTo(WORLD_W, 1460); c.closePath(); c.fill();
  c.beginPath(); FLOOR.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y)); c.stroke();
  c.fillStyle = '#cfe6f2';
  c.beginPath(); c.moveTo(0, -20); for (let y = 0; y <= 110; y += 10) c.lineTo(glacierX(y), y); c.lineTo(0, 110); c.closePath(); c.fill();
  c.fillRect(0, -3, SHELF_X, 3 + SHELF_Y);
  c.fillStyle = '#b25a3a'; c.fillRect(STATION.x0, STATION.roof, STATION.x1 - STATION.x0, STATION.floor - STATION.roof);
  // the sea ice, broken by the openings
  c.fillStyle = '#e4f2fa';
  for (let x = SHELF_X; x < WORLD_W; x += 2) if (underIce(x)) c.fillRect(x, ICE_TOP, 2.2, ICE_Y - ICE_TOP + 1.5);
  // the iceberg, its caves as far as they are mapped, and the places seen up close
  c.fillStyle = '#e8f3fa'; polyPath(c, BERG.top); c.fill();
  c.fillStyle = '#8fc6e2'; polyPath(c, BERG.poly); c.fill();
  drawCaveLines(c, X0, X1, Y0, Y1, Math.max(0.35, 1.4 / z), '#0b3550');
  for (const st of SITES) {
    if (!G.s.seen[st.id] || st.x > X1 || st.x + st.w * C < X0) continue;
    c.fillStyle = st.shell === 'rv' ? '#9fb4c4' : st.color || '#c9a070';
    for (let j = 0; j < st.h; j++) for (let i = 0; i < st.w; i++) if (st.cells[j][i] === '#') c.fillRect(st.x + i * C, st.y + j * C, C, C);
  }
  c.restore();
  // the unexplored sea under fog: only the squares reached so far show through
  const fog = CV.fog || (CV.fog = document.createElement('canvas')), f = fog.getContext('2d');
  if (fog.width !== cv2.width || fog.height !== cv2.height) { fog.width = cv2.width; fog.height = cv2.height; }
  f.setTransform(dpr, 0, 0, dpr, 0, 0); f.globalCompositeOperation = 'source-over';
  f.clearRect(0, 0, w, h); f.fillStyle = '#0b1823'; f.fillRect(0, 0, w, h);
  f.strokeStyle = 'rgba(127,224,255,.07)'; f.lineWidth = 1;
  const step = CH.s * z * Math.max(1, Math.round(40 / (CH.s * z)));
  for (let x = ((ox % step) + step) % step; x < w; x += step) { f.beginPath(); f.moveTo(x, 0); f.lineTo(x, h); f.stroke(); }
  for (let y = ((oy % step) + step) % step; y < h; y += step) { f.beginPath(); f.moveTo(0, y); f.lineTo(w, y); f.stroke(); }
  f.globalCompositeOperation = 'destination-out'; f.fillStyle = '#000';
  const ci0 = Math.max(0, Math.floor((X0 - CH.x0) / CH.s) - 1), ci1 = Math.min(CH.w - 1, Math.floor((X1 - CH.x0) / CH.s) + 1);
  const cj0 = Math.max(0, Math.floor((Y0 - CH.y0) / CH.s) - 1), cj1 = Math.min(CH.h - 1, Math.floor((Y1 - CH.y0) / CH.s) + 1);
  f.beginPath();
  for (let j = cj0; j <= cj1; j++) for (let i = ci0; i <= ci1; i++) if (chartSeen[i + j * CH.w]) {
    const [px, py] = P(CH.x0 + (i + 0.5) * CH.s, CH.y0 + (j + 0.5) * CH.s), r = CH.s * 0.78 * z;
    f.moveTo(px + r, py); f.arc(px, py, r, 0, 7);
  }
  f.fill();
  c.setTransform(1, 0, 0, 1, 0, 0); c.drawImage(fog, 0, 0); c.setTransform(dpr, 0, 0, dpr, 0, 0);
  // depth marks at the left edge, and a scale
  c.font = '600 11px ui-monospace, monospace'; c.textBaseline = 'middle'; c.textAlign = 'left'; c.fillStyle = 'rgba(207,230,242,.75)';
  const dStep = [50, 100, 200, 500].find(v => v * z > 46) || 500;
  for (let y = Math.ceil(Y0 / dStep) * dStep; y < Y1; y += dStep) if (y >= 0) { const py = oy + y * z; if (py > 70) c.fillText(y + ' m', 6, py); }
  const bar = [10, 20, 50, 100, 200, 500, 1000].find(v => v * z > 60) || 1000;
  c.fillRect(10, h - 22, bar * z, 3); c.fillText(bar + ' m', 14 + bar * z, h - 21);
  // the contacts, by how much is known of each; the current goal in gold
  const target = goalNow().target, placed = [];
  c.textBaseline = 'middle';
  for (const k of chartContacts()) {
    const [px, py] = P(k.x, k.y);
    if (px < -40 || px > w + 40 || py < -20 || py > h + 20) continue;
    const kn = knowOf(k), hot = k.id === target, sel = k.id === CV.sel;
    const col = hot ? '#ffd65a' : kn === 3 ? '#9fffd0' : kn === 2 ? '#7fe0ff' : '#ffb870';
    c.fillStyle = col; c.strokeStyle = '#04121f'; c.lineWidth = 2;
    if (kn === 1) {
      c.beginPath(); c.arc(px, py, 8, 0, 7); c.fill(); c.stroke();
      c.fillStyle = '#2b1d00'; c.font = '800 12px system-ui'; c.textAlign = 'center'; c.fillText('?', px, py + 0.5);
    } else if (kn === 2) {
      c.beginPath(); c.moveTo(px, py - 7); c.lineTo(px + 7, py); c.lineTo(px, py + 7); c.lineTo(px - 7, py); c.closePath(); c.fill(); c.stroke();
    } else { c.beginPath(); c.arc(px, py, 6, 0, 7); c.fill(); c.stroke(); }
    if (sel) { c.strokeStyle = '#fff'; c.lineWidth = 2; c.beginPath(); c.arc(px, py, 13, 0, 7); c.stroke(); }
    if (kn < 2) continue;
    const label = kn === 3 ? k.name : k.kind;
    c.font = (kn === 3 ? '700 12px' : '700 10px ui-monospace,') + ' system-ui'; c.textAlign = 'left';
    const tw = c.measureText(label).width, lx = px + 10 + tw > w - 66 ? px - 10 - tw : px + 10, ly = py - 9;
    if (!sel && placed.some(r => lx < r[0] + r[2] && r[0] < lx + tw && Math.abs(ly - r[1]) < 13)) continue;
    placed.push([lx, ly, tw]);
    c.fillStyle = 'rgba(4,18,31,.7)'; c.fillRect(lx - 3, ly - 7, tw + 6, 14);
    c.fillStyle = col; c.fillText(label, lx, ly);
  }
  // SISU, and the autopilot's way
  if (G.auto && G.auto.pts) {
    c.strokeStyle = 'rgba(255,214,90,.8)'; c.setLineDash([6, 5]); c.lineWidth = 2; c.beginPath();
    c.moveTo(...P(sub.x, sub.y)); for (let k = G.auto.i; k < G.auto.pts.length; k++) c.lineTo(...P(...G.auto.pts[k])); c.stroke(); c.setLineDash([]);
  }
  const [sx, sy] = P(sub.x, sub.y);
  c.save(); c.translate(sx, sy); c.scale(sub.dir, 1);
  c.fillStyle = '#ffd65a'; c.strokeStyle = '#2b1d00'; c.lineWidth = 1.5;
  c.beginPath(); c.ellipse(0, 0, 13, 4.5, 0, 0, 7); c.fill(); c.stroke(); c.fillRect(-2, -8, 6, 4);
  c.restore();
  c.font = '800 11px system-ui'; c.textAlign = 'center'; c.fillStyle = '#ffd65a'; c.fillText('SISU', sx, sy + 14);
  // the autopilot's line under the title
  const a = G.auto, line = a ? `🧭 Autopilotti → ${a.name}` + (a.left != null ? ` · ${Math.round(a.left)} m` : '') : '';
  if ($('chartAuto').textContent !== line) $('chartAuto').textContent = line;
  show('chartAuto', !!a);
  pickPanel();
}
// The panel for the contact tapped: what it is, how far and deep, and the autopilot.
function pickPanel() {
  const k = CV.sel && chartContacts().find(c => c.id === CV.sel);
  show('chartPick', !!k);
  if (!k) return;
  const kn = knowOf(k), d = Math.round(Math.hypot(k.x - sub.x, k.y - sub.y));
  $('pickName').textContent = kn === 3 ? k.name : kn === 2 ? k.kind : '❓ Tuntematon kontakti';
  $('pickTxt').textContent = `${d} m SISUsta · syvyys ${Math.round(Math.max(0, k.y))} m` + (kn === 1 ? ' · pingaa 📡 lähempää, niin sonar tunnistaa sen' : '');
  const go = $('pickGo'), why = autoWhy(k);
  go.textContent = G.auto && G.auto.id === k.id ? '⏹ Pysäytä autopilotti' : why || '🧭 Autopilotti tänne';
  go.disabled = !!why && !(G.auto && G.auto.id === k.id);
}
// Why the autopilot cannot take SISU to a contact; '' when it can.
function autoWhy(k) {
  if (knowOf(k) < 2) return '🧭 Tunnista ensin';
  if (k.spot[1] > RATING[G.s.up.hull] - 4) return `🧭 Liian syvällä: runko ${RATING[G.s.up.hull]} m`;
  if (Math.hypot(k.spot[0] - sub.x, k.spot[1] - sub.y) < 8) return '🧭 SISU on jo täällä';
  return '';
}
$('pickGo').addEventListener('click', () => {
  audio();
  const k = CV.sel && chartContacts().find(c => c.id === CV.sel);
  if (!k) return;
  if (G.auto && G.auto.id === k.id) act('autostop'); else if (!autoWhy(k)) act('auto', k.id);
  drawChart();
});
$('chartX').addEventListener('click', () => { audio(); closeChart(); });
$('zIn').addEventListener('click', () => chartZoom(2));
$('zOut').addEventListener('click', () => chartZoom(0.5));
$('zSisu').addEventListener('click', () => { CV.x = sub.x; CV.y = sub.y; drawChart(); });
(() => {
  const cv2 = $('chartC');
  cv2.addEventListener('pointerdown', e => { cv2.setPointerCapture(e.pointerId); CV.ptrs.set(e.pointerId, [e.clientX, e.clientY]); CV.moved = 0; CV.pinch = 0; });
  cv2.addEventListener('pointermove', e => {
    const p = CV.ptrs.get(e.pointerId);
    if (!p) return;
    if (CV.ptrs.size === 1) {
      CV.x -= (e.clientX - p[0]) / CV.z; CV.y -= (e.clientY - p[1]) / CV.z;
      CV.moved += Math.abs(e.clientX - p[0]) + Math.abs(e.clientY - p[1]);
      CV.ptrs.set(e.pointerId, [e.clientX, e.clientY]); drawChart();
    } else {
      const [a, b] = [...CV.ptrs.values()], d0 = Math.hypot(a[0] - b[0], a[1] - b[1]);
      CV.ptrs.set(e.pointerId, [e.clientX, e.clientY]);
      const [a2, b2] = [...CV.ptrs.values()], d1 = Math.hypot(a2[0] - b2[0], a2[1] - b2[1]), r = cv2.getBoundingClientRect();
      if (d0 > 0) chartZoom(d1 / d0, (a2[0] + b2[0]) / 2 - r.left, (a2[1] + b2[1]) / 2 - r.top);
      CV.moved = 99; CV.pinch = 1;
    }
  });
  const up = e => {
    if (!CV.ptrs.has(e.pointerId)) return;
    CV.ptrs.delete(e.pointerId);
    if (CV.moved > 8 || CV.pinch || e.type !== 'pointerup') return;
    // a tap: the nearest contact within reach of the finger
    const r = cv2.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    const ox = r.width / 2 - CV.x * CV.z, oy = r.height / 2 - CV.y * CV.z;
    let best = null, bd = 26;
    for (const k of chartContacts()) { const d = Math.hypot(ox + k.x * CV.z - x, oy + k.y * CV.z - y); if (d < bd) { bd = d; best = k.id; } }
    CV.sel = best; audio(); drawChart();
  };
  cv2.addEventListener('pointerup', up); cv2.addEventListener('pointercancel', up);
  addEventListener('resize', () => drawChart());
})();

// ---------- the autopilot (v9, #160) ----------
// Set from the chart, run on the host (or alone): SISU finds its own way to a known contact's spot, in real time,
// while everyone inside walks, eats or works. It keeps above the hull's limit, waits while someone is out, and stops
// on arrival, when someone takes the helm, or from the chart.
const AP = { s: 4 };
// Does SISU fit at (x, y)? Open water far from everything is answered at once; near anything the hull is tested.
function subFits(x, y) {
  const busy = y > Math.min(floorY(x - 16), floorY(x), floorY(x + 16)) - 8 || y < ICE_Y + 7 || x < SHELF_X + 40 || x > 4000 || (x > 2040 && x < 2450 && y < 215)
    || SITES.some(s => x > s.x - 18 && x < s.x + s.w * C + 18 && y > s.y - 10 && y < s.y + s.h * C + 10);
  // near anything, with a few metres to spare all round, so SISU's swing through a turn does not scrape
  return !busy || [[0, 0], [4, 0], [-4, 0], [0, 3], [0, -3]].every(([a, b]) => !subHits(x + a, y + b) || (b < 0 && y + b < ICE_Y + 6 && !subHits(x + a, y)));
}
// The way from SISU to (tx, ty): a search over 4 m squares no deeper than the hull bears; null when there is none.
function autoRoute(tx, ty) {
  const S = AP.s, maxY = RATING[G.s.up.hull] - 4, cw = Math.ceil(WORLD_W / S), chh = Math.ceil(maxY / S) + 1;
  const cell = new Int8Array(cw * chh), cost = new Float32Array(cw * chh).fill(Infinity), from = new Int32Array(cw * chh).fill(-1);
  const fits = n => { if (!cell[n]) { const i = n % cw, j = (n - i) / cw; cell[n] = subFits(i * S, Math.max(SURF, j * S)) ? 1 : 2; } return cell[n] === 1; };
  const near = (x, y) => {
    const i0 = Math.round(x / S), j0 = Math.round(y / S);
    for (let r = 0; r < 6; r++) for (let dj = -r; dj <= r; dj++) for (let di = -r; di <= r; di++) {
      const i = i0 + di, j = j0 + dj;
      if (i >= 0 && j >= 0 && i < cw && j < chh && fits(i + j * cw)) return i + j * cw;
    }
    return -1;
  };
  const a = near(sub.x, sub.y), b = near(tx, Math.min(ty, maxY));
  if (a < 0 || b < 0) return null;
  const bi = b % cw, bj = (b - bi) / cw, H = n => { const i = n % cw; return Math.hypot(i - bi, (n - i) / cw - bj) * 1.3; };
  // a small binary heap of [priority, square]
  const heap = [[H(a), a]];
  const push = e => { heap.push(e); let k = heap.length - 1; while (k) { const p = (k - 1) >> 1; if (heap[p][0] <= heap[k][0]) break; [heap[p], heap[k]] = [heap[k], heap[p]]; k = p; } };
  const pop = () => { const t = heap[0], l = heap.pop(); if (heap.length) { heap[0] = l; let k = 0; for (;;) { const L = 2 * k + 1, R = L + 1; let m = k; if (L < heap.length && heap[L][0] < heap[m][0]) m = L; if (R < heap.length && heap[R][0] < heap[m][0]) m = R; if (m === k) break; [heap[m], heap[k]] = [heap[k], heap[m]]; k = m; } } return t; };
  cost[a] = 0;
  for (let it = 0; heap.length && it < 200000; it++) {
    const [, n] = pop();
    if (n === b) break;
    const i = n % cw, j = (n - i) / cw;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      const p = i + di, q = j + dj;
      if (p < 0 || q < 0 || p >= cw || q >= chh) continue;
      const m = p + q * cw;
      if (!fits(m) || (di && dj && !(fits(p + j * cw) && fits(i + q * cw)))) continue;
      const c = cost[n] + (di && dj ? 1.414 : 1);
      if (c < cost[m]) { cost[m] = c; from[m] = n; push([c + H(m), m]); }
    }
  }
  if (from[b] < 0 && a !== b) return null;
  const pts = [];
  for (let n = b; n >= 0; n = from[n]) { const i = n % cw; pts.unshift([i * S, Math.max(SURF, (n - i) / cw * S)]); if (n === a) break; }
  if (!subHits(tx, ty) && ty <= maxY + 4) pts.push([tx, ty]);
  // straightened: from each point on to the farthest one in plain sight
  const clear = (p, q) => { const L = Math.hypot(q[0] - p[0], q[1] - p[1]), n = Math.ceil(L / 2); for (let k = 1; k < n; k++) if (!subFits(p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n)) return false; return true; };
  const out = [pts[0]];
  for (let k = 0; k < pts.length - 1;) {
    let m = Math.min(pts.length - 1, k + 40);
    while (m > k + 1 && !clear(pts[k], pts[m])) m--;
    out.push(pts[m]); k = m;
  }
  return out;
}
function startAuto(id) {
  const k = contacts().find(c => c.id === id);
  if (!k) return { say: 'Kohdetta ei löydy', snd: 'no' };
  const why = autoWhy(k);
  if (why) return { say: why.replace('🧭 ', ''), snd: 'no' };
  const pts = autoRoute(k.spot[0], k.spot[1]);
  if (!pts) return { say: 'Autopilotti ei löydä reittiä sinne', snd: 'no', sec: 2.2 };
  const name = knowOf(k) === 3 ? k.name : k.kind;
  G.auto = { id, name, pts, i: 1, left: null, best: Infinity, stuckT: 0, tries: 0 };
  if (net) { net.helm = null; net.subT = null; }
  return { say: '🧭 Autopilotti: kohti ' + name, snd: 'up', sec: 2.2 };
}
// Every way the autopilot ends goes through here (owner's choice on #160: glide to a stop): SISU brakes smoothly
// until it stands still (`G.coast`, see `stepCoast`), so no speed is left over to drift with later.
function stopAuto(say) {
  G.auto = null; G.coast = true;
  if (say) { toast(say, 2.4); tone(...SND.home); if (net && net.host) R.send({ t: 're', say, sec: 2.4 }); }
}
// The glide after the autopilot, on the host (or alone) while nobody drives: the stick let go until SISU is still.
function stepCoast(dt) {
  stepSub(dt, { x: 0, y: 0 });
  if (Math.hypot(sub.vx, sub.vy) < 0.3) { sub.vx = sub.vy = 0; G.coast = false; save(); }  // where it came to rest
}
// One step of the autopilot: steer at the next point, slow down for the last, and give up if stuck.
function stepAuto(dt) {
  const A = G.auto, end = A.pts[A.pts.length - 1];
  const out = people().some(p => p.mode === 'dive' || p.mode === 'ice');
  while (A.i < A.pts.length - 1 && Math.hypot(A.pts[A.i][0] - sub.x, A.pts[A.i][1] - sub.y) < 7) A.i++;
  const [px, py] = A.pts[A.i], dx = px - sub.x, dy = py - sub.y, last = A.i === A.pts.length - 1;
  // the way still to go, along the route
  A.left = Math.hypot(dx, dy);
  for (let k = A.i; k < A.pts.length - 1; k++) A.left += Math.hypot(A.pts[k + 1][0] - A.pts[k][0], A.pts[k + 1][1] - A.pts[k][1]);
  // to an opening, all the way up until SISU lies surfaced in it
  const up = A.id.startsWith('railo');
  if (up ? surfaced() && holeAt(sub.x) === +A.id.slice(5) : last && A.left < 3 && Math.hypot(sub.vx, sub.vy) < 3) {
    // by now it may have been seen on the way: then by its name
    const k = contacts().find(c => c.id === A.id);
    stopAuto('🧭 Perillä: ' + (k && knowOf(k) === 3 ? k.name : A.name)); stepSub(dt, { x: 0, y: 0 }); return;
  }
  // Along the line to the next point: SISU rises and dives slower than it runs, so on a steep line it runs slower too.
  // Slower into a sharp turn and at the end, so it does not scrape past a corner.
  const far = Math.max(0.01, Math.hypot(dx, dy)), ux = dx / far, uy = dy / far, vxm = SUB_SPEED * lab('vesi', 1.1), vym = 7;
  const fit = Math.min(Math.abs(ux) > 1e-3 ? 1 / Math.abs(ux) : 1e9, Math.abs(uy) > 1e-3 ? (vym / vxm) / Math.abs(uy) : 1e9);
  let slow = last ? Math.min(1, 0.15 + A.left / 50) : 1;
  if (!last && far < 30) {
    const [qx, qy] = A.pts[A.i + 1], L = Math.hypot(qx - px, qy - py) || 1, turn = ux * (qx - px) / L + uy * (qy - py) / L;
    slow = Math.min(slow, 0.45 + 0.55 * Math.max(0, turn) + far / 60);
  }
  const inp = out ? { x: 0, y: 0 } : { x: Math.max(-1, Math.min(1, ux * fit * slow)), y: Math.max(-1, Math.min(1, uy * fit * vxm / vym * slow)) };
  if (!out && Math.abs(dy) < 3) inp.y = Math.max(-1, Math.min(1, dy / 3));
  if (!out && up && last && Math.abs(dx) < 3) { inp.x = 0; inp.y = -1; }
  stepSub(dt, inp);
  if (out) return;
  if (A.left < A.best - 2) { A.best = A.left; A.stuckT = 0; } else if ((A.stuckT += dt) > 6) {
    const pts = A.tries < 2 && autoRoute(end[0], end[1]);
    if (pts) { Object.assign(A, { pts, i: 1, best: Infinity, stuckT: 0, tries: A.tries + 1 }); } else stopAuto('🧭 Autopilotti: reitti tukossa');
  }
}

function radio() { act('radio'); }
// The radio as it is, when pressing it changes nothing: the host's `doAct('radio')` plays the card or ends chapter 1.
function radioCard() {
  const s = G.s, i = s.inv;
  if (s.flags.end2) {
    card('📻 Lyra', [{ t: '»...tässä Lyra. Syvänteessä on valoa. Jos kuulet tämän, et ole yksin...»', c: 'log' },
      { t: 'Muistikortti soi yhä uudelleen. Jossain syvällä yhdeksän ihmistä jatkaa matkaa.' }],
    [{ label: 'Takaisin', cls: 'go', fn: closeCard }]);
  } else if (s.flags.end) {
    card('📻 4,2 MHz', [{ t: '»...tässä Nordlys. Meitä on yhdeksän. Mannerrinteen alla, yhdeksänsadassa metrissä. Jos kuulet, vastaa...»', c: 'log' },
      { t: 'Viesti toistuu tunnin välein. Joku jaksaa yhä lähettää sitä.' }],
    [{ label: 'Takaisin', cls: 'go', fn: closeCard }]);
  } else {
    card('📻 Radio', [{ t: 'Radio on rikki: vahvistin puuttuu ja antenni on katkennut. Kohinan seasta kuulet välillä jotain – vai kuvitteletko?' },
      { t: `Vahvistin ${i.vahvistin ? '✓' : '✗'} · Antenni ${i.antenni ? '✓' : '✗'}`, c: 'msg' }],
    [{ label: 'Takaisin', cls: 'go', fn: closeCard }]);
  }
}
