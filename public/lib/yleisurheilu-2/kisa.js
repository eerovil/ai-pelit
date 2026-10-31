// The athletics meet, shared by the field events (#165): the field of twelve, the turns, the
// standings, the results board, the saves, the end of the meet, and playing it with friends
// through rooms.js. The event itself (the run-up, the throw or jump, the drawing) stays in the
// game. Load it as a classic script before the game's own:
//
//   <script src="../../../rooms.js" data-game="<slug>" data-min="2" data-max="8"></script>
//   <script src="../../../lib/yleisurheilu-2/kisa.js"></script>
//
// A published library folder never changes (AGENTS.md, "3D games"): a fix or a new feature goes
// in yleisurheilu-3/. A new meet format may be added beside this file as a new file.
//
// New in yleisurheilu-2 (#176): the medal ceremony. At the end of the meet the top three hop onto
// the podium, an official hangs the bronze, the silver and the gold around their necks, they
// cheer, and the final standings show under it. The game draws it with K.drawPodium(ctx, box)
// in place of K.drawBoard(ctx, true, box), and may give `look: row => palette` (the outfit
// palette of outfits.js: skin, hair, top, bottom, shoe, head) and `chime: i => {}` (a sound as
// medal i, 0 the gold, goes on). The end screen stays up longer (PODIUM_END seconds); alone, a
// tap first finishes the ceremony, the next leaves it.
//
//   const K = AiPelitKisa.meet({
//     slug: 'pituushyppy',                       // saves: ai-pelit:<slug>:taso, voitot, kisat, ennatys, kesken
//     format: AiPelitKisa.rounds(),              // three rounds, the best eight three more
//     foes: [...names], skill: lv => metres,     // the player's level sets the computer's skill
//     spread: [0.25, 0.12, ...], jitter: 0.2,    // the computer's skills around it
//     cpu: (t, comp) => mark,                    // the computer's result for one turn (-1 a foul)
//     turn: (t, mine, seq) => { ... },           // a new turn: the game sets up its own attempt
//     clear: () => { ... },                      // the turn is gone (a new meet, back to the menu)
//     live: ['p', 'rel'], watch: m => { ... },   // the turn's own messages, passed on by the host
//     menu: (text, cls) => { ... },              // show the game's menu, with the meet's result
//     none: 'ei hyväksyttyä hyppyä',             // the end text when no mark counted
//     look: row => ({ skin, top, ... }),         // optional: how a medallist looks on the podium
//     chime: i => { ... },                       // optional: a sound as medal i is hung (0 gold)
//   });
//
// The game calls K.solo() or K.solo(K.kept()), K.step(dt) each frame (true while the results
// show), K.report(seq, mark) when its player's turn is measured, K.send(msg) for its live
// messages, K.drawBoard(ctx, false, box) between turns, K.drawPodium(ctx, box) at the end, and
// K.record(mark) when its player sets a record.
// Message types c, res, end and fit belong to the library.
(function () {
  'use strict';
  const COLORS = ['#e2574c', '#3f8ad8', '#3fa65a', '#e0a526', '#9a5cc6', '#e07ab0', '#2bb3b1', '#f08a3c',
    '#7d8c99', '#b5651d', '#5c6bc0', '#8bc34a'];
  function gauss() { return Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random()); }
  function shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
  const medal = i => ['🥇', '🥈', '🥉'][i] || '';
  const metres = m => m === undefined || m === null ? '–' : m < 0 ? 'X' : m.toFixed(2).replace('.', ',') + ' m';
  function fit(x, s, w) { if (x.measureText(s).width <= w) return s; while (s.length > 1 && x.measureText(s + '…').width > w) s = s.slice(0, -1); return s + '…'; }
  function rr(x, x0, y0, w, h, r) { x.beginPath(); x.roundRect(x0, y0, w, h, r); }

  // ---------- Rounds: the throws and the long jump ----------
  // Rounds 1–3 go in a drawn order; after round 3 the best eight take three more, the last in the
  // standings first. A competitor's `marks` hold one result per round, -1 a foul. The standings
  // are the best mark, then the second best, and so on (the real rule).
  function rounds(o) {
    o = o || {};
    const FINAL = o.final || 8, ROUNDS = o.rounds || 6, CUT = o.cut || 3;
    const sorted = t => t.marks.filter(m => m >= 0).sort((a, b) => b - a);
    const F = {
      FINAL, ROUNDS, CUT,
      blank: () => ({ throwers: [], order: [], turn: 0, round: 1 }),
      setup(c) {
        const order = shuffle(c.throwers.map(t => t.id));
        Object.assign(c, { round: 1, turn: 0, order0: order, order: order.slice(), final: null });
      },
      current: c => c.turn < c.order.length ? c.throwers.find(t => t.id === c.order[c.turn]) : null,
      standings(c) {
        return c.throwers.slice().sort((a, b) => {
          const sa = sorted(a), sb = sorted(b);
          for (let i = 0; i < Math.max(sa.length, sb.length); i++) {
            const d = (sb[i] === undefined ? -1 : sb[i]) - (sa[i] === undefined ? -1 : sa[i]);
            if (d) return d;
          }
          return c.throwers.indexOf(a) - c.throwers.indexOf(b);
        });
      },
      placeOf: (c, t) => F.standings(c).indexOf(t) + 1,
      bestOf: t => Math.max(-2, ...t.marks.filter(m => m !== undefined && m !== null)),
      valid: m => typeof m === 'number' && isFinite(m),
      // Takes the computer's turns up to the next player on a phone; true when the meet is over.
      advance(c, cpu, human) {
        for (;;) {
          if (c.turn >= c.order.length) {
            if (c.round === CUT) c.final = F.standings(c).slice(0, FINAL).map(t => t.id);
            if (c.round >= ROUNDS) return true;
            c.round++; c.turn = 0;
            c.order = c.round <= CUT ? c.order0.slice() : F.standings(c).filter(t => c.final.includes(t.id)).reverse().map(t => t.id);
            // No player on a phone left in the final: the rest is done at once.
            if (!c.order.some(id => human(c.throwers.find(t => t.id === id)))) {
              for (; c.round <= ROUNDS; c.round++) c.order.forEach(id => { const t = c.throwers.find(u => u.id === id); t.marks[c.round - 1] = cpu(t); c.seq++; });
              c.round = ROUNDS; c.turn = c.order.length;
              return true;
            }
          }
          const t = F.current(c);
          if (human(t)) return false;
          t.marks[c.round - 1] = cpu(t);
          c.recent.push(t.id);
          c.turn++; c.seq++;
        }
      },
      take(c, t, mark) {
        t.marks[c.round - 1] = mark;
        c.recent = [t.id];
        c.turn++; c.seq++;
      },
      results: c => F.standings(c).map((t, i) => ({ id: t.id, p: t.p, name: t.name, col: t.col, best: F.bestOf(t), place: i + 1,
        marks: t.marks.slice(), fin: !c.final || c.final.includes(t.id), fit: t.fit || null })),
      endText(e, K) {
        if (e.at < 0) return 'Kisa päättyi';
        if (!e.fin) return e.place + '. sija · ei finaaliin' + (e.mark > 0 ? ' · ' + K.fmt(e.mark) : '');
        const m = e.mark > 0 ? K.fmt(e.mark) : K.none;
        return e.place === 1 ? '🥇 Voitit kisan! ' + m : (medal(e.place - 1) ? medal(e.place - 1) + ' ' : '') + e.place + '. sija · ' + m;
      },
      title: c => c.round > CUT ? 'Finaali · kierros ' + c.round + '/' + ROUNDS : 'Kierros ' + c.round + '/' + ROUNDS,
      // The standings: between turns (the latest mark and the best), and at the end with the medals.
      board(x, K, final, box) {
        const c = K.comp, rows = final ? K.ending.res : F.results(c), W = box.w;
        const head = final ? 50 : 62, foot = final ? 0 : 26;
        const avail = box.bottom - box.top - head - foot - 8;
        const rowH = Math.min(24, Math.floor(avail / rows.length));
        const h = head + rowH * rows.length + foot + 8;
        const y0 = box.middle ? Math.max(box.top, (box.top + box.bottom - h) / 2) : box.top;
        x.fillStyle = 'rgba(10,20,40,.92)'; rr(x, 12, y0, W - 24, h, 14); x.fill();
        x.textAlign = 'center'; x.fillStyle = '#ffd166'; x.font = '900 19px system-ui';
        x.fillText(final ? 'Lopputulokset' : F.title(c), W / 2, y0 + 30);
        const fs = Math.min(15, rowH - 7), right = W - 26, lastW = 74;
        if (!final) {
          x.font = '700 11px system-ui'; x.fillStyle = '#8fa5bb'; x.textAlign = 'right';
          x.fillText('VIIMEISIN', right - lastW - 6, y0 + 52); x.fillText('PARAS', right, y0 + 52);
        }
        rows.forEach((r, i) => {
          const y = y0 + head + i * rowH + rowH * 0.7, mine = r.p === K.me;
          if (i === FINAL && (final || c.round <= CUT)) {
            x.strokeStyle = 'rgba(255,255,255,.35)'; x.setLineDash([4, 4]); x.lineWidth = 1;
            x.beginPath(); x.moveTo(24, y - rowH * 0.7); x.lineTo(W - 24, y - rowH * 0.7); x.stroke(); x.setLineDash([]);
          }
          if (mine) { x.fillStyle = 'rgba(255,209,102,.18)'; x.fillRect(16, y - rowH * 0.72, W - 32, rowH); }
          x.globalAlpha = r.fin ? 1 : 0.55;
          x.fillStyle = r.col; x.beginPath(); x.arc(46, y - fs * 0.33, Math.max(3, fs * 0.33), 0, 7); x.fill();
          x.font = '700 ' + fs + 'px system-ui'; x.textAlign = 'right'; x.fillStyle = '#b9cfe0';
          x.fillText((final && medal(i)) || (i + 1) + '.', 38, y);
          x.textAlign = 'left'; x.font = (mine ? '900 ' : '600 ') + fs + 'px system-ui'; x.fillStyle = mine ? '#ffd166' : '#fff';
          const name = mine && K.isNet() ? 'Sinä' : r.name;
          const last = r.marks.length ? r.marks[r.marks.length - 1] : undefined;
          const recent = !final && c.recent.includes(r.id);
          x.fillText(fit(x, name, right - lastW - 74 - 56), 56, y);
          x.textAlign = 'right'; x.font = '900 ' + fs + 'px system-ui'; x.fillStyle = mine ? '#ffd166' : '#fff';
          x.fillText(r.best > 0 ? K.fmt(r.best) : r.marks.length ? 'X' : '–', right, y);
          if (!final) {
            x.font = (recent ? '800 ' : '600 ') + (fs - 2) + 'px system-ui'; x.fillStyle = recent ? (last < 0 ? '#ff9a8b' : '#8ecae6') : 'rgba(185,207,224,.7)';
            x.fillText(K.fmt(last), right - lastW - 6, y);
          }
          x.globalAlpha = 1;
        });
        if (!final) {
          const t = F.current(c);
          x.textAlign = 'center'; x.font = '700 14px system-ui'; x.fillStyle = '#b9cfe0';
          const who = t && (t.p === K.me ? 'Seuraavaksi: sinä' : 'Seuraavaksi: ' + t.name);
          x.fillText(c.round <= CUT ? who + ' · ' + FINAL + ' parasta jatkaa' : who, W / 2, y0 + h - 14);
        }
        return { x: 12, y: y0, w: W - 24, h, rowH };
      },
    };
    return F;
  }

  // ---------- The medal ceremony (#176) ----------
  // Seconds from the end of the meet: the bronze, the silver and the gold hop up in turn, then an
  // official hangs their medals in the same order, and at CHEER they raise their arms. Index 0 is
  // the winner throughout.
  const HOP_T = [1.5, 1.0, 0.5], HOP = 0.55, MEDAL_T = [4.6, 3.5, 2.4], HANG = 0.9, CHEER = 5.7;
  const PODIUM_DONE = 6.4, PODIUM_END = 11;
  const MEDAL = [['#f6c445', '#a87a0c'], ['#dde3ea', '#7f8b98'], ['#dd8d4c', '#8a4b1c']];
  const SKINS = ['#f1c7a3', '#e0ac69', '#c98a62', '#8d5a3b', '#f4d1b5', '#b97a56'];
  const clamp01 = v => v < 0 ? 0 : v > 1 ? 1 : v;
  const ease = v => { v = clamp01(v); return v * v * (3 - 2 * v); };
  const mix = (a, b, e) => a + (b - a) * e;
  // How a competitor looks: the game's own palette, else its colour on a plain kit.
  function lookOf(o, r) {
    const g = (o.look && o.look(r)) || {};
    let h = 0; for (const ch of String(r.id)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return { skin: g.skin || SKINS[h % SKINS.length], hair: g.hair || ['#2b1d12', '#5a3a1e', '#d8b25a', '#1a1a1a'][h % 4],
      top: g.top || r.col, bottom: g.bottom || '#1b1b2f', shoe: g.shoe || '#f1faee', cape: g.cape || null, head: g.head || null };
  }
  // A figure from the front, its feet at (fx, fy), h tall; up: 0 arms down … 1 arms up.
  function front(x, fx, fy, h, L, up) {
    const lw = Math.max(2, h * 0.085), hip = fy - h * 0.47, sh = fy - h * 0.77, hw = h * 0.15;
    x.lineCap = 'round'; x.lineJoin = 'round';
    if (L.cape) { x.fillStyle = L.cape; x.beginPath(); x.moveTo(fx - hw, sh); x.lineTo(fx + hw, sh); x.lineTo(fx + hw * 1.3, hip + h * 0.12); x.lineTo(fx - hw * 1.3, hip + h * 0.12); x.fill(); }
    x.strokeStyle = L.skin; x.lineWidth = lw;
    [-1, 1].forEach(d => { x.beginPath(); x.moveTo(fx + d * h * 0.06, hip); x.lineTo(fx + d * h * 0.085, fy - h * 0.04); x.stroke(); });
    x.fillStyle = L.shoe; [-1, 1].forEach(d => { x.beginPath(); x.ellipse(fx + d * h * 0.1, fy - h * 0.02, h * 0.06, h * 0.03, 0, 0, 7); x.fill(); });
    x.fillStyle = L.bottom; rr(x, fx - h * 0.13, hip - h * 0.04, h * 0.26, h * 0.15, h * 0.03); x.fill();
    x.fillStyle = L.top; rr(x, fx - hw, sh - h * 0.02, hw * 2, hip - sh + h * 0.03, h * 0.05); x.fill();
    // Arms: down at the sides, or up in a V.
    x.strokeStyle = L.skin; x.lineWidth = lw * 0.9;
    [-1, 1].forEach(d => {
      const ex = fx + d * mix(h * 0.2, h * 0.24, up), ey = mix(sh + h * 0.14, sh - h * 0.12, up);
      const hx = fx + d * mix(h * 0.2, h * 0.3, up), hy = mix(fy - h * 0.48, sh - h * 0.3, up);
      x.beginPath(); x.moveTo(fx + d * (hw - lw * 0.3), sh + lw * 0.4); x.lineTo(ex, ey); x.lineTo(hx, hy); x.stroke();
    });
    const hy = fy - h * 0.89, hr = h * 0.105;
    x.strokeStyle = L.skin; x.lineWidth = lw; x.beginPath(); x.moveTo(fx, sh); x.lineTo(fx, hy + hr * 0.6); x.stroke();
    if (L.head && window.AiPelitOutfits && window.AiPelitOutfits.head) { window.AiPelitOutfits.head(x, L.head, fx, hy, hr, 1); return; }
    x.fillStyle = L.skin; x.beginPath(); x.arc(fx, hy, hr, 0, 7); x.fill();
    x.fillStyle = L.hair; x.beginPath(); x.arc(fx, hy - hr * 0.15, hr * 1.02, Math.PI * 1.02, Math.PI * 1.98); x.fill();
    x.fillStyle = 'rgba(0,0,0,.6)'; [-1, 1].forEach(d => { x.beginPath(); x.arc(fx + d * hr * 0.38, hy + hr * 0.1, Math.max(1, hr * 0.12), 0, 7); x.fill(); });
    x.strokeStyle = 'rgba(0,0,0,.55)'; x.lineWidth = Math.max(1, hr * 0.12);
    x.beginPath(); x.arc(fx, hy + hr * 0.3, hr * 0.35, 0.2 * Math.PI, 0.8 * Math.PI); x.stroke();
  }
  // A medal on its ribbon: the ribbon's two ends at (fx ± w, ty), the disc below them.
  function medalAt(x, i, fx, ty, w, drop, r, swing) {
    const dx = fx + swing, dy = ty + drop;
    x.strokeStyle = '#2f6fd6'; x.lineWidth = Math.max(2, r * 0.55);
    x.beginPath(); x.moveTo(fx - w, ty); x.lineTo(dx, dy - r * 0.8); x.lineTo(fx + w, ty); x.stroke();
    x.fillStyle = MEDAL[i][0]; x.strokeStyle = MEDAL[i][1]; x.lineWidth = Math.max(1, r * 0.22);
    x.beginPath(); x.arc(dx, dy, r, 0, 7); x.fill(); x.stroke();
    if (r > 5) { x.fillStyle = MEDAL[i][1]; x.font = '900 ' + Math.round(r * 1.2) + 'px system-ui'; x.textAlign = 'center'; x.fillText(i + 1, dx, dy + r * 0.42); }
  }
  function podium(x, K, o, box) {
    const e = K.ending, t = e.t, res = e.res, BW = box.w, BH = box.bottom - box.top;
    const side = BW > BH * 1.3;
    // The podium's part of the box, and the standings' part.
    const pa = side ? { l: box.left, t: box.top, w: Math.round(BW * 0.56), h: BH }
      : { l: box.left, t: box.top, w: BW, h: Math.round(Math.min(300, Math.max(210, BH * 0.5))) };
    const la = side ? { l: box.left + pa.w + 8, t: box.top, w: BW - pa.w - 8, h: BH }
      : { l: box.left, t: box.top + pa.h + 8, w: BW, h: BH - pa.h - 8 };
    // The stadium behind the podium.
    x.save();
    rr(x, pa.l, pa.t, pa.w, pa.h, 14); x.clip();
    const sky = x.createLinearGradient(0, pa.t, 0, pa.t + pa.h);
    sky.addColorStop(0, '#16284a'); sky.addColorStop(0.62, '#2d4f86'); sky.addColorStop(0.63, '#3f8a4c'); sky.addColorStop(1, '#2f6e3a');
    x.fillStyle = sky; x.fillRect(pa.l, pa.t, pa.w, pa.h);
    // The crowd: dots in the stand.
    for (let i = 0; i < 70; i++) {
      const u = (i * 0.618034) % 1, v = (i * 0.3819 + 0.11) % 1;
      x.fillStyle = K.COLORS[i % K.COLORS.length]; x.globalAlpha = 0.35;
      x.beginPath(); x.arc(pa.l + u * pa.w, pa.t + pa.h * (0.3 + 0.28 * v) + (t > CHEER ? Math.sin(t * 9 + i) * 2 : 0), 2.5, 0, 7); x.fill();
    }
    x.globalAlpha = 1;
    x.textAlign = 'center'; x.fillStyle = '#ffd166'; x.font = '900 19px system-ui';
    x.fillText('Palkintojenjako', pa.l + pa.w / 2, pa.t + 28);
    // The blocks, 2 – 1 – 3, and the figures' size from what fits.
    const gy = pa.t + pa.h - 40, bw = Math.min(100, pa.w / 3.3), cx = pa.l + pa.w / 2;
    const bh = [0.24, 0.17, 0.11].map(k => Math.round(pa.h * k));
    const fh = Math.min(bw * 1.35, (gy - bh[0] - pa.t - 44) / 1.08);
    const bx = [cx, cx - bw, cx + bw];
    const top = i => gy - bh[i];
    // Where each medallist is now: hopping up from the ground, then on the block.
    const there = [0, 1, 2].map(i => {
      const r = res[i];
      if (!r || !(r.best > 0)) return null;
      const k = clamp01((t - HOP_T[i]) / HOP);
      if (k <= 0) return null;
      return { r, i, fx: bx[i], fy: mix(gy + 6, top(i), ease(k)) - Math.sin(Math.PI * k) * fh * 0.35, k, L: lookOf(o, r) };
    });
    // The official walks over the podium from medal to medal, standing on the block beside the
    // medallist's (the gold one for the bronze and the silver, the silver one for the gold).
    const SPOT = [[cx - bw * 0.58, top(1)], [cx - bw * 0.42, top(0)], [cx + bw * 0.42, top(0)]];
    const offAt = () => {
      const seq = [2, 1, 0].filter(i => there[i]);
      if (!seq.length || t < MEDAL_T[seq[0]] - 0.4 || t > MEDAL_T[seq[seq.length - 1]] + HANG + 0.5) return null;
      let [ox, oy] = SPOT[seq[0]], now = null;
      seq.forEach(i => {
        const k = ease((t - (MEDAL_T[i] - 0.5)) / 0.45);
        if (k > 0) { ox = mix(ox, SPOT[i][0], k); oy = mix(oy, SPOT[i][1], k); }
        if (t >= MEDAL_T[i] && t < MEDAL_T[i] + HANG) now = i;
      });
      const last = seq[seq.length - 1], away = ease((t - (MEDAL_T[last] + HANG)) / 0.5);
      const come = ease((t - (MEDAL_T[seq[0]] - 0.4)) / 0.3);
      return { ox, oy, now, a: Math.min(come, 1 - away) };
    };
    const off = offAt();
    const OFF = { skin: '#e6b994', hair: '#d9d9d9', top: '#1f2f55', bottom: '#5b6270', shoe: '#222', cape: null, head: null };
    [1, 0, 2].forEach(i => {
      const y0 = top(i);
      x.fillStyle = '#c9d3e0'; x.fillRect(bx[i] - bw / 2, y0, bw, bh[i]);
      x.fillStyle = '#eef3f8'; x.fillRect(bx[i] - bw / 2, y0, bw, Math.max(4, bh[i] * 0.16));
      x.strokeStyle = 'rgba(0,0,0,.25)'; x.lineWidth = 1; x.strokeRect(bx[i] - bw / 2 + 0.5, y0 + 0.5, bw - 1, bh[i] - 1);
      x.fillStyle = MEDAL[i][1]; x.font = '900 ' + Math.round(Math.min(28, bh[i] * 0.6)) + 'px system-ui'; x.textAlign = 'center';
      x.fillText(String(i + 1), bx[i], y0 + bh[i] * 0.5 + Math.min(28, bh[i] * 0.6) * 0.38);
    });
    if (off) { x.globalAlpha = off.a; front(x, off.ox, off.oy, fh * 1.02, OFF, 0); x.globalAlpha = 1; }
    there.forEach(p => {
      if (!p) return;
      const up = p.i === 0 ? ease((t - CHEER) / 0.3) : ease((t - CHEER - 0.15) / 0.3);
      const jump = p.i === 0 && t > CHEER + 0.3 ? Math.abs(Math.sin((t - CHEER - 0.3) * 5)) * fh * 0.08 : 0;
      // The medal: carried over the head on its ribbon, lowered to the neck, then it swings still.
      const u = (t - MEDAL_T[p.i]) / HANG, neck = p.fy - jump - fh * 0.8, r = Math.max(4, fh * 0.055);
      const hi = Math.min(fh * 0.55, neck - pa.t - 36), lift = u < 0.45 ? mix(hi, hi * 0.8, ease(u / 0.45)) : mix(hi * 0.8, 0, ease((u - 0.45) / 0.35));
      const w = mix(fh * 0.13, fh * 0.065, ease((u - 0.6) / 0.3)), drop = mix(fh * 0.24, fh * 0.19, ease((u - 0.6) / 0.3));
      // The official's arms reach behind the medallist; the hands hold the ribbon's ends until it is on.
      const hands = off && off.now === p.i && u > 0 && u < 0.85;
      if (hands) {
        x.strokeStyle = OFF.top; x.lineWidth = Math.max(2, fh * 0.07); x.lineCap = 'round';
        [-1, 1].forEach(d => { x.beginPath(); x.moveTo(off.ox + d * fh * 0.11, off.oy - fh * 0.74); x.lineTo(p.fx + d * w, neck - lift); x.stroke(); });
      }
      x.globalAlpha = clamp01(p.k * 3);
      front(x, p.fx, p.fy - jump, fh, p.L, up);
      x.globalAlpha = 1;
      if (u > 0) {
        const swing = u > 0.8 ? Math.sin((u - 0.8) * 14) * fh * 0.04 * Math.max(0, 1 - (u - 0.8) * 1.2) : 0;
        medalAt(x, p.i, p.fx, neck - lift, w, drop, r, swing);
        if (hands) {
          x.fillStyle = OFF.skin;
          [-1, 1].forEach(d => { x.beginPath(); x.arc(p.fx + d * w, neck - lift, Math.max(2, fh * 0.045), 0, 7); x.fill(); });
        }
      }
      // The name and the mark under the block.
      const mine = p.r.p === K.me;
      x.textAlign = 'center'; x.font = (mine ? '900 ' : '700 ') + '13px system-ui'; x.fillStyle = mine ? '#ffd166' : '#fff';
      x.fillText(fit(x, mine && K.isNet() ? 'Sinä' : p.r.name, bw - 4), bx[p.i], gy + 16);
      x.font = '800 12px system-ui'; x.fillStyle = '#d6e4f0';
      x.fillText(K.fmt(p.r.best), bx[p.i], gy + 31);
    });
    // Confetti once all the medals are on.
    if (t > CHEER) {
      for (let i = 0; i < 46; i++) {
        const u = (i * 0.618034) % 1, sp = 50 + (i * 37 % 60), yy = ((t - CHEER) * sp + (i * 53 % 120)) % (pa.h + 20) - 20;
        x.fillStyle = K.COLORS[i % K.COLORS.length];
        x.save(); x.translate(pa.l + u * pa.w + Math.sin(t * 3 + i) * 8, pa.t + yy); x.rotate(t * 4 + i);
        x.fillRect(-3, -1.5, 6, 3); x.restore();
      }
    }
    x.restore();
    // The standings, every competitor.
    x.fillStyle = 'rgba(10,20,40,.92)'; rr(x, la.l, la.t, la.w, la.h, 14); x.fill();
    x.textAlign = 'center'; x.fillStyle = '#ffd166'; x.font = '900 17px system-ui';
    x.fillText('Lopputulokset', la.l + la.w / 2, la.t + 24);
    const hint = !K.isNet() && t > PODIUM_DONE ? 18 : 0;
    const rowH = Math.max(12, Math.min(24, Math.floor((la.h - 36 - 6 - hint) / res.length))), fs = Math.min(15, rowH - 4);
    const right = la.l + la.w - 14;
    res.forEach((r, i) => {
      const y = la.t + 36 + i * rowH + rowH * 0.72, mine = r.p === K.me;
      if (mine) { x.fillStyle = 'rgba(255,209,102,.18)'; x.fillRect(la.l + 6, y - rowH * 0.74, la.w - 12, rowH); }
      x.globalAlpha = r.fin === false ? 0.55 : 1;
      x.font = '700 ' + fs + 'px system-ui'; x.textAlign = 'right'; x.fillStyle = '#b9cfe0';
      x.fillText((r.best > 0 && medal(i)) || r.place + '.', la.l + 34, y);
      x.fillStyle = r.col; x.beginPath(); x.arc(la.l + 44, y - fs * 0.33, Math.max(3, fs * 0.3), 0, 7); x.fill();
      x.textAlign = 'right'; x.font = '900 ' + fs + 'px system-ui'; x.fillStyle = mine ? '#ffd166' : '#fff';
      const mark = r.best > 0 ? K.fmt(r.best) : r.marks && r.marks.length ? 'X' : '–';
      x.fillText(mark, right, y);
      const mw = x.measureText(mark).width;
      x.textAlign = 'left'; x.font = (mine ? '900 ' : '600 ') + fs + 'px system-ui';
      x.fillText(fit(x, mine && K.isNet() ? 'Sinä' : r.name, right - mw - 10 - (la.l + 54)), la.l + 54, y);
      x.globalAlpha = 1;
    });
    if (hint) { x.textAlign = 'center'; x.font = '700 12px system-ui'; x.fillStyle = '#8fa5bb'; x.fillText('Napauta jatkaaksesi', la.l + la.w / 2, la.t + la.h - 8); }
  }

  // ---------- The meet ----------
  function meet(o) {
    const R = window.AiPelitRooms;
    const F = o.format, FIELD = o.field || 12, KEY = 'ai-pelit:' + o.slug + ':';
    const load = (k, d) => { try { const v = localStorage.getItem(KEY + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } };
    const save = (k, v) => { try { localStorage.setItem(KEY + k, JSON.stringify(v)); } catch (e) {} };
    const drop = k => { try { localStorage.removeItem(KEY + k); } catch (e) {} };
    const K = {
      F, comp: null, ending: null, me: 'me', shown: null, box: null,
      level: load('taso', 1), wins: load('voitot', 0), comps: load('kisat', 0), best: load('ennatys', null),
      fmt: o.fmt || metres, none: o.none || 'ei hyväksyttyä tulosta',
      load, save, drop, gauss, shuffle, COLORS,
    };
    const isNet = K.isNet = () => !!(K.comp && K.comp.mode === 'net');
    K.isHost = () => !isNet() || R.isHost;
    const human = t => !!t && t.p !== null && !t.bot;
    K.human = human;
    K.thrower = id => K.comp.throwers.find(t => t.id === id);
    K.current = () => K.comp && !K.comp.over ? F.current(K.comp) : null;
    K.standings = () => F.standings(K.comp);
    K.placeOf = t => F.placeOf(K.comp, t);
    K.bestOf = t => F.bestOf(t);
    K.results = () => F.results(K.comp);
    K.mine = () => K.comp && K.comp.throwers.find(t => t.p === K.me);

    function newComp(mode, humans, lv) {
      const base = o.skill(lv), spread = o.spread || [0];
      const ts = humans.map((h, i) => ({ id: 'h' + i, name: h.name, p: h.p, bot: false, skill: base, col: COLORS[i % COLORS.length], marks: [] }));
      humans.forEach((h, i) => { if (h.fit) ts[i].fit = h.fit; });
      for (let k = 0; ts.length < FIELD; k++) {
        ts.push({ id: 'c' + k, name: o.foes[(lv - 1 + k) % o.foes.length], p: null, bot: false, col: COLORS[ts.length % COLORS.length],
          skill: base + spread[k % spread.length] + (Math.random() - 0.5) * (o.jitter || 0), marks: [] });
      }
      const c = { mode, level: lv, throwers: ts, seq: 0, recent: [] };
      F.setup(c);
      if (o.init) o.init(c);
      return c;
    }
    function advance() { if (F.advance(K.comp, t => o.cpu(t, K.comp), human)) over(); }
    function clearTurn() { K.shown = null; if (o.clear) o.clear(); }
    // Each phone takes up the turn the meet is at, once per turn.
    function follow() {
      const c = K.comp;
      if (!c || c.over) return;
      const t = F.current(c);
      if (!t || K.shown === c.seq) return;
      K.shown = c.seq; K.shownId = t.id;
      o.turn(t, isNet() ? t.p === R.me : true, c.seq);
    }
    K.follow = follow;
    // A player's turn, measured: recorded by the host (or alone), then on to the next.
    function take(seq, mark) {
      const c = K.comp, t = K.current();
      if (!c || c.over || seq !== c.seq || !t || !F.valid(mark)) return;
      F.take(c, t, mark);
      advance();
      if (c.mode === 'solo' && !c.over) save('kesken', c);
      if (isNet() && !c.over) R.send({ t: 'c', round: c.room, c });
      follow();
    }
    K.take = take;
    K.report = (seq, mark) => {
      if (!isNet() || R.isHost) take(seq, mark);
      else R.send({ t: 'res', round: K.comp.room, seq, mark });
    };
    // The turn's own messages: the host adds whose turn it is and sends them to every phone.
    K.send = m => {
      m.round = K.comp.room;
      if (R.isHost) R.send(Object.assign({ id: K.shownId }, m)); else R.send(m);
    };
    // A new record for this phone's player, saved at once; true when it is one.
    K.record = mark => {
      if (!(mark > 0) || (K.best !== null && mark <= K.best)) return false;
      K.best = mark; save('ennatys', mark);
      return true;
    };

    // ---------- Alone ----------
    K.kept = () => { const k = load('kesken', null); return k && k.throwers && k.mode === 'solo' && !k.over ? k : null; };
    K.solo = saved => {
      K.comp = saved || newComp('solo', [{ name: 'Sinä', p: 'me', fit: o.fit && o.fit() }], K.level);
      K.me = 'me'; K.ending = null; clearTurn();
      if (!saved) { advance(); save('kesken', K.comp); }
      follow();
    };
    K.quit = () => { K.comp = null; K.ending = null; clearTurn(); };

    // ---------- Playing with friends ----------
    // The host keeps the meet and takes the computer's turns; the phone whose turn it is runs its
    // own attempt, sends the game's live messages and the measured mark (res). The host passes the
    // live messages on to the others, who draw the same attempt, and sends the meet (c).
    if (R) {
      R.on('start', s => {
        K.ending = null; K.me = R.me; clearTurn();
        if (R.isHost && !s.over) {
          K.comp = newComp('net', s.players.map(p => ({ name: p.name, p: p.id, fit: p.id === R.me && o.fit ? o.fit() : null })), K.level);
          K.comp.room = s.round;
          advance();
          R.send({ t: 'c', round: s.round, c: K.comp });
          follow();
        } else {
          K.comp = Object.assign(F.blank(), { mode: 'net', room: s.round, seq: -1, recent: [], wait: true });
          if (o.fit) R.send({ t: 'fit', round: s.round, f: o.fit() });
        }
        if (o.started) o.started();
      });
      R.on('message', (m, from) => {
        const c = K.comp;
        if (!c || !isNet() || m.round !== c.room) return;
        const live = (o.live || []).includes(m.t);
        if (R.isHost) {
          // A guest's outfit, whenever it is its turn or not.
          if (m.t === 'fit') {
            const g = c.throwers.find(t => t.p === from);
            if (g && typeof m.f === 'string' && g.fit !== m.f) { g.fit = m.f.slice(0, 20); if (!c.over) R.send({ t: 'c', round: c.room, c }); }
            return;
          }
          const t = K.current();
          if (!t || t.p !== from) return;   // only the phone whose turn it is
          if (live) { const f = Object.assign({}, m, { id: t.id }); R.send(f); o.watch(f); }
          if (m.t === 'res') take(m.seq, m.mark);
          return;
        }
        if (m.t === 'c') { K.comp = Object.assign(m.c, { room: c.room }); follow(); }
        else if (m.t === 'end') end(m.res);
        else if (live) o.watch(m);
      });
      R.on('hello', id => { const c = K.comp; if (c && isNet() && R.isHost && !c.over) R.send({ t: 'c', round: c.room, c }, id); });
      // The computer takes the turns of a phone that is away, and gives them back when it returns.
      R.on('continue', ids => {
        const c = K.comp;
        if (!c || !R.isHost) return;
        c.throwers.forEach(t => { if (ids.includes(t.p)) t.bot = true; });
        const t = K.current();
        if (t && t.bot) { clearTurn(); advance(); if (!c.over) R.send({ t: 'c', round: c.room, c }); follow(); }
      });
      R.on('back', id => {
        const c = K.comp;
        if (!c || !R.isHost) return;
        c.throwers.forEach(t => { if (t.p === id) t.bot = false; });
        R.send({ t: 'c', round: c.room, c });
      });
      R.on('lobby', () => K.quit());
      R.on('leave', () => { K.quit(); o.menu(); });
      R.on('menu', () => { K.quit(); o.menu(); });
    }

    // ---------- The end ----------
    function over() {
      const c = K.comp;
      c.over = true;
      const res = F.results(c);
      if (isNet()) { R.deliver({ t: 'end', round: c.room, res }); R.endRound(); }
      end(res);
    }
    function end(res) {
      if (K.ending) return;
      clearTurn();
      const at = res.findIndex(r => r.p === K.me), me = res[at];
      K.ending = { t: 0, res, at, place: me ? me.place : 0, mark: me ? me.best : null, fin: me ? me.fin !== false : true };
      const counted = !isNet() || R.once(K.comp.room);
      if (counted && me) {
        K.comps++;
        if (!isNet() && me.place === 1 && me.best > 0) { K.wins++; K.level++; }
        save('kisat', K.comps); save('voitot', K.wins); save('taso', K.level);
        if (me.best > 0) {
          K.record(me.best);
          if (window.AiPelitScores) window.AiPelitScores.submit(me.best);
        }
      }
      if (!isNet()) drop('kesken');
      if (K.comp) K.comp.over = true;
    }
    K.endText = e => F.endText(e, K);
    // The results show for a few seconds, then the menu (alone) or the room (with friends).
    K.step = dt => {
      const e = K.ending;
      if (!e) return false;
      const was = e.t;
      e.t += dt;
      // A chime as each medal goes on (not when a tap skips past it).
      if (o.chime) MEDAL_T.forEach((m, i) => { const at = m + HANG * 0.8; if (was < at && e.t >= at && e.t - at < 0.3 && e.res[i] && e.res[i].best > 0) o.chime(i); });
      if (e.t > PODIUM_END) {
        K.ending = null;
        const win = e.place === 1 && e.mark > 0 ? 'win' : 'lose';
        if (isNet()) {
          R.note(e.res.slice(0, 8).map(r => r.place + '. ' + (r.p === R.me ? 'Sinä' : r.name) + ' ' + K.fmt(r.best)).join(' · '));
          K.comp = null;
          R.backToRoom(K.endText(e), win);
        } else {
          K.comp = null;
          o.menu(K.endText(e), win);
        }
      }
      return true;
    };
    // Alone, a tap finishes the ceremony, and the next one leaves the results.
    K.skip = () => { const e = K.ending; if (e && !isNet()) e.t = e.t < PODIUM_DONE ? PODIUM_DONE : 99; };
    // box: {w, top, bottom, middle}; middle centres the board between top and bottom.
    K.drawBoard = (x, final, box) => (K.box = F.board(x, K, final, box));
    // box: {left, top, w, bottom}: the whole end screen, the podium and the standings under it
    // (beside it on a phone on its side).
    K.drawPodium = (x, box) => { if (K.ending) podium(x, K, o, box); };
    return K;
  }

  window.AiPelitKisa = { meet, rounds, COLORS, gauss, shuffle, metres, PODIUM_DONE, PODIUM_END };
})();
