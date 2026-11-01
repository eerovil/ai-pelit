'use strict';
// v12 (#300): crates, the stores and their shelf, the bag, and the nomads' trade.
// ---------- crates ----------
// A crate (`G.s.crates`) is in one of five places (`w`): 'sea' (world metres, sinking slowly in the water), 'ice' (world
// metres, on the ice or a building's floor), 'sub' (SISU's own coordinates, so it goes along with SISU and never
// slides), 'shelf' (in a slot of SISU's storage shelf, `slot`), or 'held' in someone's hands (`by`; `hw` is where they
// are). `x` is its middle, `y` its bottom. A crate that has nothing under it falls (`f`) until it lands on a floor, the
// sea floor, a wreck's plate or another crate: so crates pile up. Only the host (or a phone alone) moves them.
function crateById(id) { return G.s && G.s.crates.find(c => c.id === id); }
function myCrate() { return G.s ? G.s.crates.find(c => c.w === 'held' && c.by === me()) || null : null; }
function heldBy(who) { return G.s.crates.find(c => c.w === 'held' && c.by === who) || null; }
function crateLabel(c) { return c.k === 'romu' ? c.junk || 'ROMUA' : CRATE[c.k].label; }
function crateText(c) { return c.k === 'romu' ? '📦 ' + crateLabel(c) : `📦 ${CRATE[c.k].label} ${ICON[c.k]}${c.n}`; }
// The floors in SISU at x (hull coordinates): the lower deck everywhere, the upper deck but for the ladder's hatch.
function subFloors(x) {
  const f = [];
  if (x > -8.5 && x < 10 && Math.abs(x - LADDER) > 0.5) f.push(UP);
  f.push(LOW);
  return f;
}
// The ground at x out on the ice for something whose bottom is at y: a building's floor below it, the shelf, the
// sea ice; null over open water.
function iceGround(x, y) {
  const b = bldAt(x);
  if (b) return b.floors.filter(f => f >= y - 0.01).sort((p, q) => p - q)[0];
  if (x < SHELF_X) return STATION.floor;
  if (x < SHELF_X + 6) return STATION.floor + (x - SHELF_X) / 6 * (ICE_TOP - STATION.floor);
  if (holeAt(x) >= 0 || (x > BERG_X[0] && x < BERG_X[1])) return null;
  return ICE_TOP;
}
// Where a crate falling from where it is comes to rest within `max` metres, or null if nothing stops it that soon.
function restBelow(c, max) {
  let best = null;
  const top = (l) => { if (l >= c.y - 0.001 && l <= c.y + max && (best == null || l < best)) best = l; };
  for (const o of G.s.crates) if (o !== c && o.w === c.w && Math.abs(o.x - c.x) < BOX_W * 0.95 && o.y > c.y - 0.001 && !o.f) top(o.y - BOX_H);
  if (c.w === 'sub') for (const f of subFloors(c.x)) top(f);
  else if (c.w === 'ice') { const g = iceGround(c.x, c.y); if (g != null) top(g); }
  else if (c.w === 'sea') {
    for (let d = 0; d <= max + 0.001; d += 0.05) {
      const y = c.y + d;
      if ([-0.38, 0, 0.38].some(dx => solid(c.x + dx, y + 0.01))) { top(y); break; }
    }
  }
  return best;
}
// The crates that stood on one that was lifted fall now, as the ones beside it check again.
function wake(w, x) { for (const c of G.s.crates) if (c.w === w && Math.abs(c.x - x) < BOX_W * 1.4) c.f = 1; }
// Where `who`'s hands are: [place, x, y]. This phone's own person from its own state; a friend from what their phone says.
// (The middle of the crate in their arms: under a swimmer, at a walker's waist.)
function handsOf(who) {
  if (who === me()) {
    if (G.mode === 'dive') return ['sea', diver.x + diver.dir * 0.75, diver.y + 0.55];
    if (G.mode === 'ice') return ['ice', walker.x + walker.dir * 0.6, walker.y - 1.0];
    return ['sub', crew.x + crew.dir * 0.55, crew.y - 0.95];
  }
  const o = net && net.others[who];
  if (!o) return null;
  if (o.mode === 'dive') return ['sea', o.x + o.dir * 0.75, o.y + 0.55];
  if (o.mode === 'ice') return ['ice', o.x + o.dir * 0.6, o.y - 1.0];
  return ['sub', o.x + o.dir * 0.55, o.y - 0.95];
}
// Every frame on the host (or alone): held crates follow their holder, the others fall until they land.
function stepCrates(dt) {
  for (const c of G.s.crates) {
    if (c.w === 'held') {
      const h = handsOf(c.by);
      if (!h || (c.by !== me() && !present(c.by))) { dropCrate(c, c.hw || 'sub', c.x, c.y); continue; }
      [c.hw, c.x, c.y] = h; c.y += BOX_H / 2;
      continue;
    }
    if (!c.f) continue;
    // in water it sinks slowly; in the air it falls
    c.vy = c.w === 'sea' ? Math.min(1.6, (c.vy || 0) + dt * 3) : Math.min(14, (c.vy || 0) + dt * 9.8);
    const dy = c.vy * dt, r = restBelow(c, dy);
    if (r != null) {
      c.y = r; c.f = 0; c.vy = 0;
      if (c.w === 'sea' || c.w === 'ice') sfx('metalli', 0.25);
      save();
    } else {
      c.y += dy;
      // off the ice into an opening: on down into the sea
      if (c.w === 'ice' && c.y > 0.4) c.w = 'sea';
      if (c.w === 'sea' && c.y > floorY(c.x) + 1) { c.y = floorY(c.x); c.f = 0; c.vy = 0; save(); }
      if (c.w === 'sub' && c.y > LOW) { c.y = LOW; c.f = 0; c.vy = 0; }
    }
  }
}
function dropCrate(c, w, x, y) {
  delete c.by;
  c.w = w; c.f = 1; c.vy = 0;
  c.x = w === 'sub' ? Math.max(-13.6, Math.min(14, x)) : x; c.y = y;
}
// Host: every crate in someone's hands goes down where they are (fainting, the hull giving way).
function dropAll() { for (const c of G.s.crates) if (c.w === 'held') dropCrate(c, c.hw || 'sub', c.x, c.y); }
// The crate this phone's person could lift now: within reach and the top one of its pile.
function nearCrate() {
  if (!G.s) return null;
  const at = G.mode === 'dive' ? ['sea', diver.x, diver.y + 0.6, 1.4] : G.mode === 'ice' ? ['ice', walker.x, walker.y, 1.1]
    : G.mode === 'home' ? ['sub', crew.x, crew.y, 1.0] : null;
  if (!at) return null;
  let best = null;
  for (const c of G.s.crates) {
    if (c.w !== at[0] || c.f) continue;
    const dx = Math.abs(c.x - at[1]);
    // on foot: the pile on the floor where the person stands, up to two crates high; swimming: any crate near
    const ok = at[0] === 'sea' ? dx < at[3] && Math.abs(c.y - BOX_H / 2 - at[2]) < 1.6 : dx < at[3] && c.y <= at[2] + 0.05 && c.y > at[2] - 1.6;
    if (ok && (!best || c.y < best.y)) best = c;
  }
  return best;
}
// Where a crate let go of goes: in front of the person, from the height of their hands.
function dropSpot() {
  if (G.mode === 'dive') return ['sea', diver.x + diver.dir * 0.75, diver.y + 0.2];
  if (G.mode === 'ice') return ['ice', walker.x + walker.dir * 0.6, walker.y - 1.35];
  const [a, b] = DECK_X[crew.y > 1 ? 1 : 0];
  return ['sub', Math.max(a - 2.4, Math.min(b + 2.4, crew.x + crew.dir * 0.8)), crew.y - 1.3];
}
// SISU's storage shelf (in the stores, lower deck): four crates a row, two rows. A crate on it is out of the way.
const SHELF = [[-0.3, LOW], [0.65, LOW], [1.6, LOW], [2.55, LOW], [-0.3, 1.2], [0.65, 1.2], [1.6, 1.2], [2.55, 1.2]];
function shelfFree() { const used = G.s.crates.filter(c => c.w === 'shelf').map(c => c.slot); return SHELF.findIndex((_, n) => !used.includes(n)); }
function shelved() { return G.s.crates.filter(c => c.w === 'shelf'); }
// A loose crate on the deck stands in the way: walking from x0 towards x1 on the deck at `deck` stops at its side.
function crateBlock(x0, x1, deck) {
  if (!G.s) return x1;
  for (const c of G.s.crates) {
    if (c.w !== 'sub' || c.y > deck + 0.01 || c.y < deck - 2) continue;
    const a = c.x - BOX_W / 2 - 0.22, b = c.x + BOX_W / 2 + 0.22;
    if (x1 > x0 && x0 <= a + 1e-6 && x1 > a) x1 = a;
    else if (x1 < x0 && x0 >= b - 1e-6 && x1 < b) x1 = b;
  }
  return x1;
}

// ---------- the stores ----------
// How many of a kind SISU has: the loose ones and the shelved crates' contents (Eero's choice on #300). Using one takes
// it from the shelved crate with least left, so a crate empties and leaves the shelf soonest; then from the loose ones.
function stock(k) { return (G.s.inv[INV[k] || k] || 0) + shelved().filter(c => c.k === k).reduce((n, c) => n + c.n, 0); }
function use(k, n = 1) {
  if (stock(k) < n) return false;
  const s = G.s;
  while (n > 0) {
    const c = shelved().filter(c => c.k === k && c.n > 0).sort((p, q) => p.n - q.n)[0];
    if (c) { c.n--; if (!c.n) s.crates.splice(s.crates.indexOf(c), 1); } else s.inv[INV[k] || k]--;
    n--;
  }
  return true;
}

// ---------- the bag ----------
// The small finds a person carries (`G.carry`, at most BAG); what is taken from the stores to trade is 'pack:<kind>:<n>'.
function bagFull() { return G.carry.length >= BAG; }
function heldCount(who) { return Object.values(G.held).filter(w => w === who).length; }

// ---------- the nomads (v12, #300) ----------
// Their camp is on the ice by the second opening. They want food, medicine and supplies, one trade at a time, and give
// in return what they know: where to look next (`HINTS`).
const TRADES = [
  { want: { laake: 1, ruoka: 1 }, hint: 'hylyt', ask: 'Lapsella on kuumetta, ja ruoka on vähissä.',
    tell: 'Vanhin piirtää lumeen: hylkykenttä on idässä, kahden laivan hylyt lähellä toisiaan. Alue on nyt merikartalla.' },
  { want: { ruoka: 3 }, hint: 'aurora', ask: 'Talvi on pitkä. Tuo ruokaa, niin kerron kalastajista.',
    tell: '»Kalastusalus Aurora upposi hylkykentän takana. Sen väki tuli meidän mukaamme.» Alue on nyt merikartalla.' },
  { want: { tarvike: 2 }, hint: 'saa', ask: 'Pakkanen puree. Tarvitsemme lämpimiä vaatteita tai peitteitä.',
    tell: '»Jäävuoren itäpuolella, railon luona, on autio sääasema. Kaksi kerrosta, paljon tavaraa.» Railo on nyt merikartalla.' },
  { want: { laake: 2 }, hint: 'kontit', ask: 'Vanhuksemme yskii. Lääkkeitä, jos sinulla on.',
    tell: '»Kontteja putosi laivoista pohjaan: pino hylkykentällä ja yksi syvässä hauta-aukossa.» Alueet ovat nyt merikartalla.' },
  { want: { ruoka: 2, tarvike: 2 }, hint: 'rinne', ask: 'Lähdemme pian etelään. Ruokaa ja tarvikkeita matkaan.',
    tell: '»Rinteen reunalla, Sagan takana, on vielä kontteja.» Alue on nyt merikartalla.' },
];
const GOODS = ['ruoka', 'laake', 'tarvike'];
// What `who` carries that the nomads want: the bag's finds and packed goods, and the crate in their hands.
function goodsOf(who) {
  const g = { ruoka: 0, laake: 0, tarvike: 0 };
  for (const [id, w] of Object.entries(G.held)) { const it = w === who && itemById(id); if (it && it.k in g) g[it.k]++; }
  const c = heldBy(who);
  if (c && c.k in g) g[c.k] += c.n;
  return g;
}
function wantText(want) { return Object.entries(want).map(([k, n]) => ICON[k] + ' ' + n).join('  '); }
// Host: the trade itself. Goods come from the bag first, then from the crate in hand (an emptied crate stays with them).
function trade(who) {
  const s = G.s, t = TRADES[s.trade || 0];
  if (!t) return { say: 'Nomadeilla ei ole enää kerrottavaa.', snd: 'no' };
  const have = goodsOf(who);
  if (Object.entries(t.want).some(([k, n]) => have[k] < n)) return { say: 'Heille ei riitä: ' + wantText(t.want), snd: 'no' };
  const gone = [];
  for (const [k, need] of Object.entries(t.want)) {
    let n = need;
    for (const [id, w] of Object.entries(G.held)) {
      if (!n) break;
      const it = w === who && itemById(id);
      if (!it || it.k !== k) continue;
      delete G.held[id]; gone.push(id); n--;
      if (id.startsWith('pack:')) s.pack[k] = Math.max(0, (s.pack[k] || 0) - 1);
      else { s.got[id] = true; if (it.site && it.site !== 'find') s.flags[it.site] = true; }
    }
    const c = n && heldBy(who);
    if (c) { c.n -= n; if (c.n <= 0) s.crates.splice(s.crates.indexOf(c), 1); }
  }
  s.finds = s.finds.filter(f => !s.got[f.id]);
  learn(t.hint);
  s.trade = (s.trade || 0) + 1;
  save();
  return { traded: s.trade - 1, gone, snd: 'up' };
}
function nearElder() { return G.mode === 'ice' && Math.abs(walker.x - CAMP.elder) < 3.2 && !walker.climbing; }
function campCard(msg) {
  const s = G.s, t = TRADES[s.trade || 0], have = goodsOf(me());
  if (!s.flags.leiri) {
    // the first visit, once: who they are
    if (!net || net.host) { s.flags.leiri = true; save(); }
  }
  const paras = [];
  if (msg) paras.push({ t: msg, c: 'msg' });
  if (!t) {
    paras.push({ t: 'Vanhin hymyilee. »Kerroimme kaiken, mitä tiedämme. Meri on sinun.»' });
    card('🔥 Nomadien leiri', paras, [{ label: 'Takaisin', cls: 'go', fn: closeCard }]);
    return;
  }
  if (!s.trade && !msg) paras.push({ t: 'Tulen ääressä istuu turkkeihin pukeutunut vanhin. Koirat haukkuvat. »Meri antaa ja ottaa. Mitä sinä tuot?»' });
  paras.push({ t: '»' + t.ask + '»', c: 'log' }, { t: 'He haluavat: ' + wantText(t.want), c: 'msg' },
    { t: 'Sinulla: ' + GOODS.map(k => ICON[k] + ' ' + have[k]).join('  ') + ' (reppu ja laatikko käsissä)', c: 'small' });
  const ok = Object.entries(t.want).every(([k, n]) => have[k] >= n);
  card('🔥 Nomadien leiri', paras, [{ label: '🤝 Anna: ' + wantText(t.want), off: !ok, fn: () => act('trade') },
    { label: 'Takaisin', cls: 'go', fn: closeCard }]);
  G.card = 'camp';
}
// What the nomads told, on the phone that traded.
function toldCard(n) {
  const t = TRADES[n];
  card('🔥 Nomadit kertovat', [{ t: t.tell, c: 'log' }, { t: 'Aja alueelle autopilotilla navigointihuoneesta ja etsi kohde sonarilla 📡.', c: 'small' }],
    [{ label: 'Kiitos', cls: 'go', fn: closeCard }]);
}

// ---------- the stores' card ----------
// In SISU's storage: what is in the stores, the shelf's crates (one can be taken down), and goods into the bag to trade.
function storeCard(msg) {
  const s = G.s, paras = [];
  if (msg) paras.push({ t: msg, c: 'msg' });
  paras.push({ t: `Varastossa: 🥫 ${stock('ruoka')}  💊 ${stock('laake')}  ⚙️ ${stock('osa')}  🧥 ${stock('tarvike')}`, c: 'msg' },
    { t: `Hyllyssä ${shelved().length}/${SHELF.length} laatikkoa · reppu ${G.carry.length}/${BAG}`, c: 'small' });
  const hold = !!myCrate();
  const btns = GOODS.map(k => ({ label: `🎒 Reppuun ${ICON[k]}`, off: !stock(k) || bagFull(), fn: () => act('pack', k) }));
  for (const c of shelved().sort((p, q) => p.slot - q.slot)) btns.push({ label: '⬇️ ' + crateText(c), off: hold || crew.harp, fn: () => { closeCard(); act('unshelf', c.id); } });
  btns.push({ label: 'Takaisin', cls: 'go', fn: closeCard });
  card('🗄️ Varasto', paras, btns, true);
  G.card = 'store';
}
