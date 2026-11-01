'use strict';
// v12 (#300): drawing the crates, the weather station and the nomads' camp.
// ---------- crates ----------
// A crate: a wooden box with a stripe in its contents' colour and their sign; junk is plain grey wood.
function drawBox(c, x, y, flip) {
  ctx.save(); ctx.translate(x, y);
  const k = CRATE[c.k], w = BOX_W, h = BOX_H;
  ctx.fillStyle = c.k === 'romu' ? '#6d6256' : '#8a6a42'; ctx.fillRect(-w / 2, -h, w, h);
  ctx.fillStyle = 'rgba(0,0,0,.28)'; ctx.fillRect(-w / 2, -h, w, 0.06); ctx.fillRect(-w / 2, -0.06, w, 0.06);
  ctx.fillRect(-w / 2, -h, 0.06, h); ctx.fillRect(w / 2 - 0.06, -h, 0.06, h);
  ctx.strokeStyle = 'rgba(0,0,0,.22)'; ctx.lineWidth = 0.04; ctx.beginPath(); ctx.moveTo(-w / 2, -h); ctx.lineTo(w / 2, 0); ctx.stroke();
  ctx.fillStyle = k.col; ctx.fillRect(-w / 2 + 0.06, -h * 0.62, w - 0.12, h * 0.3);
  if (flip) ctx.scale(-1, 1);
  if (c.k !== 'romu') { ctx.font = '0.3px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(ICON[c.k], 0, -h * 0.47); }
  ctx.restore();
}
// Is this person (this phone's own, or a friend's as drawn) carrying a crate?
function holding(c) {
  if (!G.s) return false;
  if (c === crew || c === walker || c === diver) return !!myCrate();
  return !!(net && G.s.crates.some(k => k.w === 'held' && net.others[k.by] === c));
}
// The crates in the sea and on the ice, in world metres: seen as far as a lamp reaches (on the ice, by daylight; in a
// building, only from inside it). A crate in hands is drawn there.
function drawCrates(X0, X1, Y0, Y1) {
  const ice = G.mode === 'ice', eye = G.mode === 'dive' ? diver : ice ? walker : sub;
  const reach = G.mode === 'dive' ? 13 * LAMP[G.s.up.lamp] : 26, inB = ice && bldAt(walker.x);
  for (const c of G.s.crates) {
    let x = c.x, y = c.y, w = c.w;
    if (w === 'held') { const h = handsOf(c.by); if (!h || h[0] === 'sub') continue; [w, x, y] = h; y += BOX_H / 2; }
    if (w !== 'sea' && w !== 'ice') continue;
    if (x < X0 - 2 || x > X1 + 2 || y < Y0 - 2 || y > Y1 + 2) continue;
    let vis = 1;
    if (w === 'ice') { const b = bldAt(x); if (b && b !== inB) continue; }
    else if (c.w !== 'held') vis = Math.min(1, 1.5 - Math.hypot(x - eye.x, y - eye.y) / reach);
    if (vis <= 0) continue;
    ctx.globalAlpha = vis; drawBox(c, x, y); ctx.globalAlpha = 1;
  }
}
// Inside SISU (hull coordinates, drawn mirrored when SISU faces left): the shelf's crates, the loose ones on the decks,
// and those in someone's hands.
function drawSubCrates() {
  const flip = sub.face < 0;
  for (const c of G.s.crates) {
    if (c.w === 'shelf') drawBox(c, ...SHELF[c.slot], flip);
    else if (c.w === 'sub') drawBox(c, c.x, c.y, flip);
    else if (c.w === 'held' && G.mode === 'home') {
      const h = handsOf(c.by);
      if (h && h[0] === 'sub' && (c.by === me() || (net && net.others[c.by] && net.others[c.by].mode === 'home'))) drawBox(c, h[1], h[2] + BOX_H / 2, flip);
    }
  }
}

// ---------- the weather station ----------
// Two floors on skids east of the iceberg, a lattice mast with a spinning anemometer and a radar dome. Seen from inside
// (this phone's person in it) the wall comes off and the rooms show, the ladder between the floors.
function drawSaa() {
  const S = SAA, [f0, f1] = S.floors, r = S.roof, open = G.mode === 'ice' && bldAt(walker.x) === S;
  // the mast and its anemometer, the dome
  const mx = S.x1 - 5;
  ctx.strokeStyle = '#4b555c'; ctx.lineWidth = 0.25;
  ctx.beginPath(); ctx.moveTo(mx - 1, r); ctx.lineTo(mx, r - 14); ctx.lineTo(mx + 1, r);
  for (let y = r - 2; y > r - 13; y -= 2.2) { ctx.moveTo(mx - 0.9 + (r - y) * 0.07, y); ctx.lineTo(mx + 0.9 - (r - y) * 0.07, y - 1.1); }
  ctx.stroke();
  const a = G.t * 6;
  ctx.strokeStyle = '#2a3036'; ctx.lineWidth = 0.12; ctx.beginPath();
  for (let k = 0; k < 3; k++) { const t = a + k * 2.1; ctx.moveTo(mx, r - 14.6); ctx.lineTo(mx + Math.cos(t) * 1.1, r - 14.6 + Math.sin(t) * 0.35); }
  ctx.stroke();
  ctx.fillStyle = '#e8eef2'; ctx.beginPath(); ctx.arc(S.x0 + 9, r, 2.2, Math.PI, 0); ctx.fill();
  ctx.fillStyle = '#3a454c'; for (let x = S.x0 + 2; x < S.x1; x += 12) ctx.fillRect(x, f0, 1.4, 0.3);  // skids
  if (!open) {
    ctx.fillStyle = '#5f7486'; ctx.fillRect(S.x0, r, S.x1 - S.x0, f0 - r);
    ctx.fillStyle = '#4c5f6e'; ctx.fillRect(S.x0, f1, S.x1 - S.x0, 0.35);
    ctx.fillStyle = '#b8402e'; ctx.fillRect(S.x0, r + 0.5, S.x1 - S.x0, 0.45);
    ctx.fillStyle = '#1c2429';
    for (const fy of [f1 - 2.4, f0 - 2.4]) for (let x = S.x0 + 4; x < S.x1 - 2; x += 5.5) ctx.fillRect(x, fy, 2.2, 1.2);
    ctx.fillStyle = '#c8d6de'; ctx.fillRect(S.x0 + 0.4, f0 - 2.7, 1.6, 2.7);  // the door, facing the opening
    ctx.fillStyle = '#e8d7a8'; ctx.font = '700 1.1px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('SÄÄASEMA', (S.x0 + S.x1) / 2, r + 1.7);
  } else {
    for (const rm of S.rooms) {
      const top = rm.fl ? r : f1, bot = S.floors[rm.fl];
      ctx.fillStyle = rm.id === walker.room ? '#3f4a52' : '#333d45'; ctx.fillRect(rm.x0, top, rm.x1 - rm.x0, bot - top);
      const g = ctx.createRadialGradient((rm.x0 + rm.x1) / 2, top + 0.4, 0, (rm.x0 + rm.x1) / 2, top + 0.4, (rm.x1 - rm.x0) * 0.6);
      g.addColorStop(0, 'rgba(220,235,255,.2)'); g.addColorStop(1, 'rgba(220,235,255,0)');
      ctx.fillStyle = g; ctx.fillRect(rm.x0, top, rm.x1 - rm.x0, bot - top);
      ctx.fillStyle = '#1a2025'; if (rm.x0 > S.x0) ctx.fillRect(rm.x0 - 0.1, top, 0.2, 1.1);  // walls, open doorways below
    }
    ctx.fillStyle = '#1a2025';
    ctx.fillRect(S.x0, r, S.x1 - S.x0, 0.25); ctx.fillRect(S.x0, f1 - 0.05, S.x1 - S.x0, 0.3); ctx.fillRect(S.x0, f0 - 0.1, S.x1 - S.x0, 0.12);
    ctx.fillRect(S.x1 - 0.4, r, 0.4, f0 - r); ctx.fillRect(S.x0, r, 0.4, f1 - r + 1.2);
    ctx.fillStyle = 'rgba(200,225,240,.35)'; ctx.fillRect(S.x0, f1 + 1.2, 0.4, f0 - f1 - 1.2);  // the open door
    // the hatch in the upper floor and the ladder through it
    ctx.fillStyle = '#333d45'; ctx.fillRect(S.ladder - 0.5, f1 - 0.05, 1, 0.3);
    ctx.strokeStyle = '#c09050'; ctx.lineWidth = 0.08; ctx.beginPath();
    ctx.moveTo(S.ladder - 0.32, f1 - 1.2); ctx.lineTo(S.ladder - 0.32, f0); ctx.moveTo(S.ladder + 0.32, f1 - 1.2); ctx.lineTo(S.ladder + 0.32, f0); ctx.stroke();
    for (let y = f1 - 1; y < f0; y += 0.4) { ctx.beginPath(); ctx.moveTo(S.ladder - 0.32, y); ctx.lineTo(S.ladder + 0.32, y); ctx.stroke(); }
    // frost on the walls
    ctx.fillStyle = 'rgba(230,245,255,.18)'; for (let x = S.x0 + 1; x < S.x1; x += 3.1) ctx.fillRect(x, r + 0.25, 1.2, 0.18 + (x * 7 % 3) * 0.1);
    // downstairs: coats in the hall; store shelves; the generator with its fuel cans
    for (let n = 0; n < 2; n++) { ctx.fillStyle = ['#2f6f8f', '#c9b23a'][n]; ctx.fillRect(S.x0 + 2 + n * 1.6, f0 - 2.6, 0.9, 1.5); }
    ctx.fillStyle = '#6b5236'; for (const y of [f0 - 2.2, f0 - 1.2]) ctx.fillRect(6296, y, 5, 0.1);
    ctx.fillStyle = '#4c5458'; ctx.fillRect(6305, f0 - 1.6, 4.4, 1.6); ctx.fillStyle = '#3a4246'; ctx.fillRect(6306, f0 - 2.1, 1.4, 0.5);
    ctx.fillStyle = '#a03a2a'; for (let n = 0; n < 3; n++) ctx.fillRect(6311 + n * 0.8, f0 - 0.7, 0.6, 0.7);
    // upstairs: the instrument desk, a barograph, the radio; bunks with frozen blankets
    ctx.fillStyle = '#6b5236'; ctx.fillRect(6280, f1 - 1.1, 8, 0.18); ctx.fillRect(6280.3, f1 - 0.95, 0.15, 0.95); ctx.fillRect(6287.5, f1 - 0.95, 0.15, 0.95);
    ctx.fillStyle = '#2b3236'; ctx.fillRect(6281, f1 - 2.3, 2.6, 1.2);
    ctx.fillStyle = '#e8eef2'; ctx.fillRect(6284.4, f1 - 1.7, 1.6, 0.6);
    ctx.strokeStyle = '#c0392b'; ctx.lineWidth = 0.05; ctx.beginPath(); ctx.moveTo(6284.5, f1 - 1.4);
    for (let x = 6284.5; x < 6286; x += 0.15) ctx.lineTo(x, f1 - 1.4 - Math.sin(x * 9) * 0.12 - (x - 6284.5) * 0.08); ctx.stroke();
    ctx.fillStyle = '#5a4a3a'; for (const x of [6299, 6306]) { ctx.fillRect(x, f1 - 0.6, 4.5, 0.16); ctx.fillRect(x, f1 - 2, 4.5, 0.16); }
    ctx.fillStyle = '#8fa4b4'; for (const x of [6299, 6306]) { ctx.fillRect(x + 0.1, f1 - 0.85, 4.2, 0.25); ctx.fillRect(x + 0.1, f1 - 2.25, 4.2, 0.25); }
    // room names along each ceiling
    ctx.font = '700 0.62px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    for (const rm of S.rooms) {
      const top = rm.fl ? r : f1 + 0.25, w = ctx.measureText(rm.name).width, cx = (rm.x0 + rm.x1) / 2;
      ctx.fillStyle = 'rgba(10,14,18,.6)'; ctx.fillRect(cx - w / 2 - 0.12, top + 0.32, w + 0.24, 0.7);
      ctx.fillStyle = '#e6f2ff'; ctx.fillText(rm.name, cx, top + 0.36);
    }
  }
  ctx.fillStyle = '#eef6fb'; ctx.fillRect(S.x0 - 0.4, r - 0.45, S.x1 - S.x0 + 0.8, 0.5);  // snow on the roof
}

// ---------- the nomads' camp ----------
// Three tents of hide on poles, a fire, a sled and its dogs, and the people: the elder by the fire, two others.
function drawCamp() {
  const g = ICE_TOP;
  // the sled and the dogs lying in the snow
  ctx.fillStyle = '#6b4a2a'; ctx.fillRect(CAMP.x0, g - 0.5, 3.4, 0.12); ctx.fillRect(CAMP.x0 + 0.2, g - 0.9, 0.1, 0.4); ctx.fillRect(CAMP.x0 + 3.1, g - 0.9, 0.1, 0.4);
  ctx.strokeStyle = '#4a3a2a'; ctx.lineWidth = 0.08; ctx.beginPath(); ctx.moveTo(CAMP.x0 - 0.3, g - 0.05); ctx.quadraticCurveTo(CAMP.x0 + 1.7, g + 0.15, CAMP.x0 + 3.8, g - 0.15); ctx.stroke();
  for (let n = 0; n < 3; n++) {
    const x = CAMP.x0 + 5 + n * 1.6, t = Math.sin(G.t * 2 + n) * 0.06;
    ctx.fillStyle = ['#d8d0c4', '#7a6a5a', '#3a3632'][n]; ctx.beginPath(); ctx.ellipse(x, g - 0.25, 0.55, 0.25, 0, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(x + 0.5, g - 0.45 + t, 0.18, 0, 7); ctx.fill();
    polyPath(ctx, [[x + 0.45, g - 0.6 + t], [x + 0.55, g - 0.8 + t], [x + 0.62, g - 0.58 + t]]); ctx.fill();
  }
  // the tents
  for (const [x, col] of [[CAMP.x0 + 14, '#8a6a4a'], [CAMP.fire + 18, '#7a5a3a'], [CAMP.x1 - 8, '#96785a']]) {
    ctx.fillStyle = col; polyPath(ctx, [[x - 3.4, g], [x, g - 6], [x + 3.4, g]]); ctx.fill();
    ctx.fillStyle = 'rgba(0,0,0,.18)'; polyPath(ctx, [[x, g - 6], [x + 3.4, g], [x + 1.2, g]]); ctx.fill();
    ctx.fillStyle = '#2a1d13'; polyPath(ctx, [[x - 0.7, g], [x, g - 1.8], [x + 0.7, g]]); ctx.fill();
    ctx.strokeStyle = '#4a3a2a'; ctx.lineWidth = 0.1; ctx.beginPath();
    ctx.moveTo(x - 0.5, g - 6.8); ctx.lineTo(x + 0.4, g - 5.6); ctx.moveTo(x + 0.5, g - 6.8); ctx.lineTo(x - 0.4, g - 5.6); ctx.stroke();
    ctx.fillStyle = '#f4f9fc'; polyPath(ctx, [[x - 3.4, g], [x - 2.6, g - 1.4], [x - 1.8, g]]); ctx.fill();
  }
  // the fire: logs, flames, sparks and its warm light on the snow
  const f = CAMP.fire, fl = 0.8 + Math.sin(G.t * 11) * 0.12 + Math.sin(G.t * 7.3) * 0.1;
  const lg = ctx.createRadialGradient(f, g - 0.5, 0, f, g - 0.5, 6);
  lg.addColorStop(0, 'rgba(255,170,80,.35)'); lg.addColorStop(1, 'rgba(255,170,80,0)');
  ctx.fillStyle = lg; ctx.beginPath(); ctx.arc(f, g - 0.5, 6, 0, 7); ctx.fill();
  ctx.fillStyle = '#4a3020'; ctx.save(); ctx.translate(f, g - 0.12); ctx.rotate(0.25); ctx.fillRect(-0.8, -0.08, 1.6, 0.16); ctx.rotate(-0.5); ctx.fillRect(-0.8, -0.08, 1.6, 0.16); ctx.restore();
  ctx.fillStyle = '#ff7a2a'; polyPath(ctx, [[f - 0.5, g - 0.15], [f - 0.1, g - 1.1 * fl], [f + 0.1, g - 0.6], [f + 0.25, g - 1.35 * fl], [f + 0.5, g - 0.15]]); ctx.fill();
  ctx.fillStyle = '#ffd65a'; polyPath(ctx, [[f - 0.25, g - 0.15], [f, g - 0.75 * fl], [f + 0.25, g - 0.15]]); ctx.fill();
  ctx.fillStyle = 'rgba(255,200,120,.8)';
  for (let k = 0; k < 4; k++) { const a = (G.t * 0.7 + k / 4) % 1; ctx.fillRect(f + Math.sin(G.t * 3 + k * 2) * 0.4, g - 1 - a * 3, 0.07, 0.07); }
  // the people in fur: the elder sitting by the fire, two standing
  nomad(CAMP.elder, g, true, '#6a4a32');
  nomad(f - 3.5, g, false, '#5a3e2a', 1);
  nomad(CAMP.fire + 11, g, false, '#7a5636', 1);
}
function nomad(x, g, sit, col, dir = -1) {
  ctx.save(); ctx.translate(x, g); ctx.scale(dir * 1.1, 1.1);
  if (sit) {
    ctx.fillStyle = '#4a3a2a'; ctx.fillRect(-0.4, -0.35, 0.8, 0.35);  // a log to sit on
    ctx.fillStyle = col; polyPath(ctx, [[-0.32, -0.35], [-0.24, -1.2], [0.24, -1.2], [0.32, -0.35]]); ctx.fill();
    ctx.fillRect(0, -0.5, 0.55, 0.16);
    ctx.fillStyle = '#e8dcc8'; ctx.beginPath(); ctx.arc(0, -1.42, 0.27, 0, 7); ctx.fill();  // the fur hood
    ctx.fillStyle = '#c89a78'; ctx.beginPath(); ctx.arc(0.06, -1.4, 0.15, 0, 7); ctx.fill();
  } else {
    ctx.fillStyle = '#3a2a1a'; ctx.fillRect(-0.16, -0.75, 0.13, 0.75); ctx.fillRect(0.04, -0.75, 0.13, 0.75);
    ctx.fillStyle = col; polyPath(ctx, [[-0.36, -0.6], [-0.24, -1.5], [0.24, -1.5], [0.36, -0.6]]); ctx.fill();
    ctx.fillStyle = '#e8dcc8'; ctx.beginPath(); ctx.arc(0, -1.72, 0.28, 0, 7); ctx.fill();
    ctx.fillStyle = '#c89a78'; ctx.beginPath(); ctx.arc(0.06, -1.7, 0.15, 0, 7); ctx.fill();
  }
  ctx.restore();
}
