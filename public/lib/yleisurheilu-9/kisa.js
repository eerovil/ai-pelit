// The athletics meet, shared by the field events (#165): the field of twelve, the turns, the
// standings, the results board, the saves, the end of the meet, and playing it with friends
// through rooms.js. The event itself (the run-up, the throw or jump, the drawing) stays in the
// game. Load it as a classic script before the game's own:
//
//   <script src="../../../rooms.js" data-game="<slug>" data-min="2" data-max="8"></script>
//   <script src="../../../lib/yleisurheilu-9/kisa.js"></script>
//
// A published library folder never changes (AGENTS.md, "3D games"): a fix or a new feature goes
// in yleisurheilu-10/. A new meet format may be added beside this file as a new file; the bar-height
// format is korkeus.js beside it.
//
// New in yleisurheilu-9 (#395): nobody runs any more. With box.scroll the whole row of spectators
// only slides with the background, a little slower than it (PARALLAX), and stops when it stops.
// Legs move only on a walk a tap started (Eero's choice).
//
// New in yleisurheilu-8 (#373): with box.scroll, spectators jog after the scrolling background;
// tap a spectator to climb onto their shoulders (up to four high). Without scroll the row stays put.
//
// New in yleisurheilu-7 (#341): the spectators stay in the background. The game calls
// K.drawFans(ctx, {..., walk: true}) early in its scene, before the athlete (in a stadium behind the
// boards, which hide their legs), and passes a tap on its scene to K.tapFans(px): a spectator's tap
// walks its own figure there along the row on every phone (message go, the spot as a share of the
// row, so phones of any width agree). Nobody walks unless their phone taps (Eero's choice). With
// walk the name is over the head, not under the feet. Without walk, K.drawFans draws as before.
//
// New in yleisurheilu-6 (#330): the cheer sounds as a short "yay!" from a few people (aanet-3
// jee) instead of four seconds of a shouting crowd, which Eero found awful. Load aanet-3.
//
// New in yleisurheilu-5 (#297): with friends, the meet waits only for the phone whose turn it is
// (rooms.js turns()). A phone that is away, or leaves, keeps its competitor: the meet goes on
// without stopping while it is someone else's turn, and when its own turn comes everyone waits,
// the host's "Ohita vuoro" recording a missed attempt (the format's `missed`, else -1). The computer never
// takes over a friend. Coming back (rooms.js "Palaa kierrokseen") picks the meet up where it is.
// The friends not on turn stand at the side as spectators: the game draws them with
// K.drawFans(ctx, box) during an attempt, and a "📣 Kannusta" button on their phones makes their
// figure jump with a cheer ("Hyvä Aino!") on every phone, with a sound (yleisurheilu-6: aanet-3 jee).
// Options: `cheerAt` (the button's CSS place, default bottom right) and `cheerSound` (instead of
// that sound).
//
// New in yleisurheilu-3 (#176): the podium stays until the player leaves it. It no longer goes
// to the menu or the room by itself; a tap during the ceremony finishes it (alone), and a tap
// after it leaves, alone and with friends alike.
//
// New in yleisurheilu-4 (#176): medals go by place, not by order. In the bar-height format a full
// countback tie shares the place, so two jumpers sharing the 1st both get gold (and no silver goes
// out), in the standings and on the podium, where everyone placed 1st–3rd stands on their place's
// block, a shared place side by side, however many share it. In the rounds format places never tie,
// so it ends as in yleisurheilu-3.
//
// New in yleisurheilu-2 (#176): the medal ceremony. At the end of the meet the top three hop onto
// the podium, an official hangs the bronze, the silver and the gold around their necks, they
// cheer, and the final standings show under it. The game draws it with K.drawPodium(ctx, box)
// in place of K.drawBoard(ctx, true, box), and may give `look: row => palette` (the outfit
// palette of outfits.js: skin, hair, top, bottom, shoe, head) and `chime: i => {}` (a sound as
// medal i, 0 the gold, goes on).
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
// K.drawFans(ctx, box) draws the spectators (box: {left, right, bottom, h}: the row's ends, the
// line their feet stand on, a figure's height; walk: true and optional scroll: background px left since rest, which slides the row (#395)), and
// K.tapFans(px, py) takes a tap on the scene (true when it walked this phone's spectator there).
// Message types c, res, end, fit, cheer and go belong to the library.
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
      missed: -1, // a turn skipped while its phone is away (#297): a foul
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
  const PODIUM_DONE = 6.4;
  const MEDAL = [['#f6c445', '#a87a0c'], ['#dde3ea', '#7f8b98'], ['#dd8d4c', '#8a4b1c']];
  const SKINS = ['#f1c7a3', '#e0ac69', '#c98a62', '#8d5a3b', '#f4d1b5', '#b97a56'];
  const clamp01 = v => v < 0 ? 0 : v > 1 ? 1 : v;
  // A result's medal by its place (0 gold, 1 silver, 2 bronze), -1 none: a shared place shares it.
  const medalOf = r => r && r.best > 0 && r.place >= 1 && r.place <= 3 ? r.place - 1 : -1;
  const ease = v => { v = clamp01(v); return v * v * (3 - 2 * v); };
  const mix = (a, b, e) => a + (b - a) * e;
  // How a competitor looks: the game's own palette, else its colour on a plain kit.
  function lookOf(o, r) {
    const g = (o.look && o.look(r)) || {};
    let h = 0; for (const ch of String(r.id)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return { skin: g.skin || SKINS[h % SKINS.length], hair: g.hair || ['#2b1d12', '#5a3a1e', '#d8b25a', '#1a1a1a'][h % 4],
      top: g.top || r.col, bottom: g.bottom || '#1b1b2f', shoe: g.shoe || '#f1faee', cape: g.cape || null, head: g.head || null };
  }
  // A figure from the front, its feet at (fx, fy), h tall; up: 0 arms down … 1 arms up; step -1…1
  // lifts one foot or the other as it walks (yleisurheilu-7).
  function front(x, fx, fy, h, L, up, step = 0) {
    const lw = Math.max(2, h * 0.085), hip = fy - h * 0.47, sh = fy - h * 0.77, hw = h * 0.15;
    x.lineCap = 'round'; x.lineJoin = 'round';
    if (L.cape) { x.fillStyle = L.cape; x.beginPath(); x.moveTo(fx - hw, sh); x.lineTo(fx + hw, sh); x.lineTo(fx + hw * 1.3, hip + h * 0.12); x.lineTo(fx - hw * 1.3, hip + h * 0.12); x.fill(); }
    x.strokeStyle = L.skin; x.lineWidth = lw;
    const lift = d => Math.max(0, step * d) * h * 0.09;
    [-1, 1].forEach(d => { x.beginPath(); x.moveTo(fx + d * h * 0.06, hip); x.lineTo(fx + d * h * 0.085, fy - h * 0.04 - lift(d)); x.stroke(); });
    x.fillStyle = L.shoe; [-1, 1].forEach(d => { x.beginPath(); x.ellipse(fx + d * h * 0.1, fy - h * 0.02 - lift(d), h * 0.06, h * 0.03, 0, 0, 7); x.fill(); });
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
    // Everyone placed 1st–3rd stands on that place's block (a shared place shares the step, side
    // by side and a little smaller), hopping up from the ground, then on the block. Index i is the
    // block: 0 gold, 1 silver, 2 bronze; j a medallist's spot on it, n how many share it.
    const groups = [[], [], []];
    res.forEach(r => { const m = medalOf(r); if (m >= 0) groups[m].push(r); });
    const there = [];
    groups.forEach((g, i) => g.forEach((r, j) => {
      const n = g.length, k = clamp01((t - HOP_T[i] - j * 0.12) / HOP);
      if (k <= 0) return;
      const sh = n === 1 ? fh : fh * Math.max(0.5, 1.25 / n), gap = Math.min(bw / n, sh * 0.62);
      there.push({ r, i, j, n, sh, fx: bx[i] + (j - (n - 1) / 2) * gap,
        fy: mix(gy + 6, top(i), ease(k)) - Math.sin(Math.PI * k) * sh * 0.35, k, L: lookOf(o, r) });
    }));
    // The official walks over the podium from block to block, standing on the block beside the
    // medallists' (the gold one for the bronze and the silver, the silver one for the gold), and
    // hangs the medals of a shared place one after another within the block's time.
    const SPOT = [[cx - bw * 0.58, top(1)], [cx - bw * 0.42, top(0)], [cx + bw * 0.42, top(0)]];
    const offAt = () => {
      const seq = [2, 1, 0].filter(i => groups[i].length);
      if (!seq.length || t < MEDAL_T[seq[0]] - 0.4 || t > MEDAL_T[seq[seq.length - 1]] + HANG + 0.5) return null;
      let [ox, oy] = SPOT[seq[0]], now = null;
      seq.forEach(i => {
        const k = ease((t - (MEDAL_T[i] - 0.5)) / 0.45);
        if (k > 0) { ox = mix(ox, SPOT[i][0], k); oy = mix(oy, SPOT[i][1], k); }
        if (t >= MEDAL_T[i] && t < MEDAL_T[i] + HANG) now = [i, Math.floor((t - MEDAL_T[i]) / HANG * groups[i].length)];
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
      const fh = p.sh;
      const up = p.i === 0 ? ease((t - CHEER) / 0.3) : ease((t - CHEER - 0.15) / 0.3);
      const jump = p.i === 0 && t > CHEER + 0.3 ? Math.abs(Math.sin((t - CHEER - 0.3) * 5)) * fh * 0.08 : 0;
      // The medal: carried over the head on its ribbon, lowered to the neck, then it swings still.
      // A shared place's medals go on one after another, each in its share of the block's time.
      const u = ((t - MEDAL_T[p.i]) / HANG) * p.n - p.j, neck = p.fy - jump - fh * 0.8, r = Math.max(4, fh * 0.055);
      const hi = Math.min(fh * 0.55, neck - pa.t - 36), lift = u < 0.45 ? mix(hi, hi * 0.8, ease(u / 0.45)) : mix(hi * 0.8, 0, ease((u - 0.45) / 0.35));
      const w = mix(fh * 0.13, fh * 0.065, ease((u - 0.6) / 0.3)), drop = mix(fh * 0.24, fh * 0.19, ease((u - 0.6) / 0.3));
      // The official's arms reach behind the medallist; the hands hold the ribbon's ends until it is on.
      const hands = off && off.now && off.now[0] === p.i && off.now[1] === p.j && u > 0 && u < 0.85;
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
    });
    // The names and the mark under each block; a shared place lists its medallists together.
    groups.forEach((g, i) => {
      if (!g.length || !there.some(p => p.i === i)) return;
      const mine = g.some(r => r.p === K.me), name = r => r.p === K.me && K.isNet() ? 'Sinä' : r.name;
      x.textAlign = 'center'; x.font = (mine ? '900 ' : '700 ') + (g.length > 1 ? '11px' : '13px') + ' system-ui'; x.fillStyle = mine ? '#ffd166' : '#fff';
      x.fillText(fit(x, g.map(name).join(' · '), bw - 4), bx[i], gy + 16);
      x.font = '800 12px system-ui'; x.fillStyle = '#d6e4f0';
      x.fillText(K.fmt(g[0].best), bx[i], gy + 31);
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
    const hint = t >= PODIUM_DONE ? 18 : 0;
    const rowH = Math.max(12, Math.min(24, Math.floor((la.h - 36 - 6 - hint) / res.length))), fs = Math.min(15, rowH - 4);
    const right = la.l + la.w - 14;
    res.forEach((r, i) => {
      const y = la.t + 36 + i * rowH + rowH * 0.72, mine = r.p === K.me;
      if (mine) { x.fillStyle = 'rgba(255,209,102,.18)'; x.fillRect(la.l + 6, y - rowH * 0.74, la.w - 12, rowH); }
      x.globalAlpha = r.fin === false ? 0.55 : 1;
      x.font = '700 ' + fs + 'px system-ui'; x.textAlign = 'right'; x.fillStyle = '#b9cfe0';
      x.fillText((medalOf(r) >= 0 && medal(medalOf(r))) || r.place + '.', la.l + 34, y);
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
    const human = t => !!t && t.p !== null; // a friend is never the computer's (#297)
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
      const ts = humans.map((h, i) => ({ id: 'h' + i, name: h.name, p: h.p, skill: base, col: COLORS[i % COLORS.length], marks: [] }));
      humans.forEach((h, i) => { if (h.fit) ts[i].fit = h.fit; });
      for (let k = 0; ts.length < FIELD; k++) {
        ts.push({ id: 'c' + k, name: o.foes[(lv - 1 + k) % o.foes.length], p: null, col: COLORS[ts.length % COLORS.length],
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
    function take(seq, mark, skipped) {
      const c = K.comp, t = K.current();
      if (!c || c.over || seq !== c.seq || !t || !(skipped || F.valid(mark))) return;
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
    K.quit = () => { K.comp = null; K.ending = null; clearTurn(); K.spot = {}; K.on = {}; walkX = {}; hopAt = {}; dropAt = {}; lastRow = null; };

    // ---------- Playing with friends ----------
    // The host keeps the meet and takes the computer's turns; the phone whose turn it is runs its
    // own attempt, sends the game's live messages and the measured mark (res). The host passes the
    // live messages on to the others, who draw the same attempt, and sends the meet (c).
    if (R) {
      R.on('start', s => {
        K.ending = null; K.me = R.me; clearTurn(); K.cheers = {}; K.spot = {}; K.on = {}; walkX = {}; hopAt = {}; dropAt = {}; lastRow = null;
        if (window.AiPelitAanet && !o.cheerSound) window.AiPelitAanet.load(['jee']);
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
          // A spectator's cheer, passed on to every phone.
          if (m.t === 'cheer') {
            const g = c.throwers.find(t => t.p === from);
            if (g && !c.over) { R.send({ t: 'cheer', round: c.room, id: g.id, w: m.w }); cheered(g.id, m.w); }
            return;
          }
          // A spectator walked to a new spot (#341), passed on to every phone and kept for one that
          // comes back.
          if (m.t === 'go') {
            const g = c.throwers.find(t => t.p === from), s = spotOf(m.s);
            if (g && s !== null && !c.over && K.fans().includes(g)) hostGo(g.id, s, m.on);
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
        // Its own cheer this phone showed at the tap: the host's echo of it is not played again.
        else if (m.t === 'cheer' && !(K.mine() && K.mine().id === m.id)) cheered(m.id, m.w);
        // Where the spectators stand: one that walked (its own walk this phone made at the tap, so the
        // late echo is not taken), or all of them, its own too, for a phone that came back.
        else if (m.t === 'go') {
          if (m.spots && typeof m.spots === 'object') {
            Object.keys(m.spots).forEach(id => { const s = spotOf(m.spots[id]); if (s !== null) K.spot[id] = s; });
            K.on = {};
            if (m.ons && typeof m.ons === 'object') Object.keys(m.ons).forEach(id => {
              if (typeof m.ons[id] === 'string') K.on[id] = m.ons[id];
            });
          } else {
            const s = spotOf(m.s);
            if (s !== null && m.id) applyGo(m.id, s, typeof m.on === 'string' ? m.on : null);
          }
        }
        else if (live) o.watch(m);
      });
      // The meet needs a phone only for its own turn (#297): rooms.js waits for no one else.
      R.turns(id => {
        const c = K.comp;
        if (!c || !isNet() || c.over) return true;
        const t = F.current(c);
        return !!t && t.p === id;
      });
      // The host skips the turn of a phone that is away: a missed attempt, and on to the next.
      R.on('skip', ids => {
        const c = K.comp, t = K.current();
        if (!c || !R.isHost || !t || !ids.includes(t.p)) return;
        clearTurn();
        take(c.seq, F.missed !== undefined ? F.missed : -1, true);
      });
      R.on('hello', id => {
        const c = K.comp;
        if (!c || !isNet() || !R.isHost || c.over) return;
        R.send({ t: 'c', round: c.room, c }, id);
        if (Object.keys(K.spot).length || Object.keys(K.on).length)
          R.send({ t: 'go', round: c.room, spots: K.spot, ons: K.on }, id);
      });
      R.on('lobby', () => K.quit());
      R.on('leave', () => { K.quit(); o.menu(); });
      R.on('menu', () => { K.quit(); o.menu(); });
    }

    // ---------- The spectators (#297) ----------
    // With friends, the others in the meet stand at the side while one is on turn; a tap on
    // "📣 Kannusta" makes this phone's figure jump with a cheer on every phone.
    const CHEERS = ['Hyvä {n}!', 'Tsemppiä {n}!', 'Anna mennä {n}!', 'Hienoa {n}!'], CHEER_T = 1.8;
    K.cheers = {};
    function cheered(id, w) {
      if (!K.comp || !K.comp.throwers.some(t => t.id === id)) return;
      const t = K.current();
      w = Math.abs(Math.floor(+w || 0)) % CHEERS.length;
      K.cheers[id] = { at: performance.now(), text: CHEERS[w].replace('{n}', t ? t.name : '') };
      if (o.cheerSound) o.cheerSound();
      else if (window.AiPelitAanet) window.AiPelitAanet.play('jee', { vol: 0.4, rate: 0.95 + Math.random() * 0.1 });
    }
    function cheer() {
      const c = K.comp, me = K.mine();
      if (!c || !isNet() || c.over || !me || !K.current() || K.current().p === me.p) return;
      const w = Math.floor(Math.random() * CHEERS.length);
      if (R.isHost) { R.send({ t: 'cheer', round: c.room, id: me.id, w }); cheered(me.id, w); }
      else { R.send({ t: 'cheer', round: c.room, w }); cheered(me.id, w); }
      lastCheer = performance.now();
    }
    K.cheer = cheer;
    // The spectators: every friend in the meet but the one on turn, faded while their phone is away.
    K.fans = () => {
      const c = K.comp, t = K.current();
      if (!c || !isNet() || c.over || K.ending || !t) return [];
      const fans = c.throwers.filter(u => human(u) && u.p !== t.p);
      pruneColumns(fans);
      return fans;
    };
    K.drawFans = (x, box) => {
      const fans = K.fans();
      K.fanSpots = [];
      if (!fans.length) return;
      if (box.walk) return drawWalkers(x, box, fans);
      const on = {}, now = performance.now(), h = box.h, fs = Math.max(10, Math.round(h * 0.3));
      (R.members || []).forEach(m => { if (m.on) on[m.id] = true; });
      const gap = Math.min(h * 1.7, (box.right - box.left) / fans.length);
      // The cheers going on: the newest over its figure, older ones above it, so two at once never
      // cover each other.
      const live = fans.filter(f => K.cheers[f.id] && now - K.cheers[f.id].at < CHEER_T * 1000)
        .sort((a, b) => K.cheers[a.id].at - K.cheers[b.id].at);
      x.save();
      const spots = fans.map((f, i) => {
        const fx = box.left + gap * (i + 0.5), ch = K.cheers[f.id], age = ch ? (now - ch.at) / 1000 : 9;
        const going = age < CHEER_T, hop = going ? Math.abs(Math.sin(age * Math.PI * 2.2)) * h * 0.28 * (1 - age / CHEER_T) : 0;
        x.fillStyle = 'rgba(0,0,0,.22)'; x.beginPath(); x.ellipse(fx, box.bottom, h * 0.24, h * 0.06, 0, 0, 7); x.fill();
        x.globalAlpha = f.p === R.me || on[f.p] ? 1 : 0.45;
        front(x, fx, box.bottom - hop, h, lookOf(o, f), going ? 1 : 0);
        x.globalAlpha = 1;
        x.textAlign = 'center'; x.font = '800 ' + fs + 'px system-ui';
        x.lineWidth = 3; x.strokeStyle = 'rgba(0,0,0,.6)'; x.fillStyle = f.p === R.me ? '#ffd166' : '#fff';
        const nm = fit(x, f.p === R.me ? 'Sinä' : f.name, gap - 4);
        x.strokeText(nm, fx, box.bottom + fs + 1); x.fillText(nm, fx, box.bottom + fs + 1);
        return { f, fx, age, hop };
      });
      // The cheers in speech bubbles over the figures, kept inside the row's ends.
      x.font = '800 ' + Math.max(12, Math.round(h * 0.34)) + 'px system-ui';
      const bh = Math.max(20, Math.round(h * 0.56));
      live.forEach((f, k) => {
        const sp = spots.find(q => q.f === f), ch = K.cheers[f.id];
        const tw = x.measureText(ch.text).width + 16, up = (live.length - 1 - k) * (bh + 4);
        const bx = Math.max(box.left, Math.min(box.right - tw, sp.fx - tw / 2)), by = box.bottom - h * 1.3 - bh - 4 - up;
        x.globalAlpha = Math.min(1, (CHEER_T - sp.age) * 3);
        x.fillStyle = '#fff'; rr(x, bx, by, tw, bh, bh / 2); x.fill();
        if (!up) { x.beginPath(); x.moveTo(sp.fx - 5, by + bh - 1); x.lineTo(sp.fx + 5, by + bh - 1); x.lineTo(sp.fx, by + bh + 6); x.fill(); }
        x.fillStyle = '#c4432f'; x.textAlign = 'center'; x.fillText(ch.text, bx + tw / 2, by + bh * 0.7);
        x.globalAlpha = 1;
      });
      x.restore();
    };
    // ---------- Spectators in the background (#341) ----------
    // Each spectator stands on a spot along the row, a share of its width (0 … 1), until its phone
    // taps the scene; then it walks there. The untapped spot is by the friend's place among all the
    // friends in the meet, not among those watching now, so it stays put as the turn moves on. K.spot holds the spots that were tapped,
    // walkX where each figure is drawn now (also a share), so a new spot is walked to, not jumped to.
    K.spot = {}; K.on = {}; K.fanSpots = [];
    let walkX = {}, hopAt = {}, dropAt = {};
    const WALK = 1.2; // Figure heights per second (#373).
    const PARALLAX = 0.8; // The row's speed on the screen, as a share of the background's (#395).
    let lastRow = null, lastWalk = 0, lastGo = -1e9;
    const spotOf = v => typeof v === 'number' && isFinite(v) ? Math.max(0, Math.min(1, v)) : null;

    function pruneColumns(fans) {
      const ids = new Set(fans.map(f => f.id));
      Object.keys(K.on).forEach(id => {
        const seen = new Set([id]);
        let below = K.on[id], valid = ids.has(id);
        while (below && valid) {
          if (!ids.has(below) || seen.has(below)) valid = false;
          else { seen.add(below); below = K.on[below]; }
        }
        if (!valid) { dropAt[id] = { at: performance.now(), depth: depthOf(id) }; delete K.on[id]; }
      });
    }
    function stackable(id, below) {
      if (!below || id === below) return false;
      const ids = new Set(K.fans().map(f => f.id));
      if (!ids.has(id) || !ids.has(below)) return false;
      const seen = new Set([id]);
      let depth = 0;
      while (below) {
        if (!ids.has(below) || seen.has(below)) return false;
        seen.add(below); below = K.on[below]; depth++;
      }
      return depth < 4;
    }
    function depthOf(id) {
      let depth = 0, seen = new Set();
      while (K.on[id] && !seen.has(id)) { seen.add(id); id = K.on[id]; depth++; }
      return depth;
    }
    function applyGo(id, s, below) {
      // Moving any part of a column drops everybody standing above it (#373).
      const above = Object.keys(K.on).filter(other => {
        let lower = K.on[other], hops = 0;
        while (lower && hops++ < 8) {
          if (lower === id) return true;
          lower = K.on[lower];
        }
        return false;
      });
      const fallen = above.map(other => ({ id: other, depth: depthOf(other) }));
      fallen.forEach(f => { delete K.on[f.id]; dropAt[f.id] = { at: performance.now(), depth: f.depth }; });
      if (below) { K.on[id] = below; hopAt[id] = -1; delete dropAt[id]; }
      else {
        if (K.on[id]) dropAt[id] = { at: performance.now(), depth: depthOf(id) };
        delete K.on[id];
      }
      K.spot[id] = s;
    }
    function hostGo(id, s, below) {
      const top = below ? topOf(below) : null;
      const valid = stackable(id, top);
      // A fifth spectator stands alongside the column, not inside it.
      if (below && !valid) s = spotOf(s + (s < 0.5 ? 0.12 : -0.12));
      applyGo(id, s, valid ? top : null);
      R.send({ t: 'go', round: K.comp.room, id, s, ...(valid ? { on: top } : {}) });
    }
    function topOf(id) {
      const seen = new Set();
      while (!seen.has(id)) {
        seen.add(id);
        const next = Object.keys(K.on).find(k => K.on[k] === id);
        if (!next) break;
        id = next;
      }
      return id;
    }
    function rootOf(id) {
      const seen = new Set();
      while (K.on[id] && !seen.has(id)) { seen.add(id); id = K.on[id]; }
      return id;
    }
    function drawWalkers(x, box, fans) {
      const online = {}, now = performance.now(), h = box.h, fs = Math.max(9, Math.round(h * 0.28));
      const dt = Math.min(0.1, Math.max(0, (now - lastWalk) / 1000)); lastWalk = now;
      (R.members || []).forEach(m => { if (m.on) online[m.id] = true; });
      const l = box.left + h * 0.4, r = box.right - h * 0.4, w = Math.max(1, r - l);
      // The whole row slides as one with the background (#395): nobody runs or catches up.
      const shift = PARALLAX * (Number.isFinite(box.scroll) ? box.scroll : 0);
      const all = K.comp.throwers.filter(human);
      const byId = Object.fromEntries(fans.map(f => [f.id, f]));
      lastRow = { l, r, h, shift };
      const live = fans.filter(f => K.cheers[f.id] && now - K.cheers[f.id].at < CHEER_T * 1000)
        .sort((a, b) => K.cheers[a.id].at - K.cheers[b.id].at);
      x.save();

      fans.forEach(f => {
        const want = K.spot[f.id] !== undefined ? K.spot[f.id] : (all.indexOf(f) + 0.5) / all.length;
        if (walkX[f.id] === undefined) walkX[f.id] = want;
        const wd = want - walkX[f.id], stepMax = WALK * h * dt / w;
        walkX[f.id] = Math.abs(wd) <= stepMax ? want : walkX[f.id] + Math.sign(wd) * stepMax;
      });
      const placed = {};
      function place(f) {
        if (placed[f.id]) return placed[f.id];
        const below = K.on[f.id] && byId[K.on[f.id]];
        const age = K.cheers[f.id] ? (now - K.cheers[f.id].at) / 1000 : 9;
        const going = age < CHEER_T, cheerHop = going ? Math.abs(Math.sin(age * Math.PI * 2.2)) * h * 0.28 * (1 - age / CHEER_T) : 0;
        const walking = Math.abs((K.spot[f.id] !== undefined ? K.spot[f.id] : (all.indexOf(f) + 0.5) / all.length) - walkX[f.id]) > 1e-4;
        const ph = walking ? Math.sin(now / 1000 * Math.PI * 2 * 1.8) : 0;
        const bob = Math.abs(ph) * h * 0.03;
        if (below) {
          const want = K.spot[f.id] !== undefined ? K.spot[f.id] : (all.indexOf(f) + 0.5) / all.length;
          // Reach the other spectator at walking speed before climbing (#373).
          if (Math.abs(want - walkX[f.id]) > 1e-4) {
            return placed[f.id] = { f, fx: l + walkX[f.id] * w - shift,
              bottom: box.bottom, depth: 0, age, going, cheerHop, ph, bob };
          }
          const lower = place(below), depth = lower.depth + 1;
          if (hopAt[f.id] === -1) hopAt[f.id] = now;
          const rise = hopAt[f.id] === undefined ? 1 : Math.min(1, (now - hopAt[f.id]) / 300);
          return placed[f.id] = { f, fx: lower.fx, bottom: lower.bottom - h * 0.82 * rise,
            depth, age, going, cheerHop, ph, bob };
        }
        let bottom = box.bottom;
        if (dropAt[f.id] !== undefined) {
          const falling = (now - dropAt[f.id].at) / 300;
          if (falling >= 1) delete dropAt[f.id];
          else bottom -= h * 0.82 * dropAt[f.id].depth * (1 - falling);
        }
        return placed[f.id] = { f, fx: l + walkX[f.id] * w - shift,
          bottom, depth: 0, age, going, cheerHop, ph, bob };
      }
      const spots = fans.map(place);
      // Draw the base first, then the ones on its shoulders; off-row figures don't render.
      spots.slice().sort((a, b) => a.depth - b.depth).forEach(sp => {
        if (sp.fx < box.left - h || sp.fx > box.right + h) return;
        const f = sp.f;
        x.globalAlpha = f.p === R.me || online[f.p] ? 1 : 0.45;
        front(x, sp.fx, sp.bottom - sp.cheerHop - sp.bob, h, lookOf(o, f), sp.going ? 1 : 0, sp.ph);
        x.globalAlpha = 1;
        K.fanSpots.push({ id: f.id, x: sp.fx, y: sp.bottom, depth: sp.depth, step: sp.ph });
      });
      // Names over the heads, beside a column where possible. No labels off the row.
      x.textAlign = 'center'; x.font = '800 ' + fs + 'px system-ui'; x.lineWidth = 3; x.strokeStyle = 'rgba(0,0,0,.6)';
      const names = [];
      spots.filter(sp => sp.fx >= box.left - h && sp.fx <= box.right + h)
        .slice().sort((a, b) => a.fx - b.fx).forEach(sp => {
          const f = sp.f, nm = fit(x, f.p === R.me ? 'Sinä' : f.name, Math.max(h * 1.6, 40));
          const tw = x.measureText(nm).width, nx = sp.fx + (sp.depth ? h * 0.4 : 0);
          let y = sp.bottom - sp.cheerHop - h - 3;
          while (names.some(q => Math.abs(q.y - y) < fs && Math.abs(q.x - nx) < (q.w + tw) / 2 + 4)) y -= fs + 1;
          names.push({ x: nx, y, w: tw }); sp.top = y;
          x.fillStyle = f.p === R.me ? '#ffd166' : '#fff';
          x.strokeText(nm, nx, y); x.fillText(nm, nx, y);
        });
      // A cheer stays at the edge after its spectator has run off-screen. Its tail points out.
      x.font = '800 ' + Math.max(12, Math.round(h * 0.3)) + 'px system-ui';
      const bh = Math.max(20, Math.round(h * 0.5));
      live.forEach((f, k) => {
        const sp = placed[f.id], ch = K.cheers[f.id], tw = x.measureText(ch.text).width + 16;
        const up = (live.length - 1 - k) * (bh + 4);
        const bx = Math.max(box.left, Math.min(box.right - tw, sp.fx - tw / 2));
        const by = (sp.top === undefined ? sp.bottom - h - 3 : sp.top) - fs - bh - 4 - up;
        x.globalAlpha = Math.min(1, (CHEER_T - sp.age) * 3);
        x.fillStyle = '#fff'; rr(x, bx, by, tw, bh, bh / 2); x.fill();
        if (!up) {
          x.beginPath();
          if (sp.fx < box.left) {
            x.moveTo(bx + 2, by + bh * 0.4); x.lineTo(bx + 2, by + bh * 0.7); x.lineTo(bx - 7, by + bh * 0.55);
          } else if (sp.fx > box.right) {
            x.moveTo(bx + tw - 2, by + bh * 0.4); x.lineTo(bx + tw - 2, by + bh * 0.7); x.lineTo(bx + tw + 7, by + bh * 0.55);
          } else {
            x.moveTo(sp.fx - 5, by + bh - 1); x.lineTo(sp.fx + 5, by + bh - 1); x.lineTo(sp.fx, by + bh + 6);
          }
          x.fill();
        }
        x.fillStyle = '#c4432f'; x.textAlign = 'center'; x.fillText(ch.text, bx + tw / 2, by + bh * 0.68);
        x.globalAlpha = 1;
      });
      x.restore();
    }
    // A spectator's tap walks to the rest-row position, or climbs onto another spectator (#373).
    K.tapFans = (px, py) => {
      const c = K.comp, me = K.mine();
      if (!c || !isNet() || c.over || !me || !lastRow || R.paused) return false;
      if (!K.fans().some(f => f.p === R.me)) return false;
      const now = performance.now();
      if (now - lastGo < 300) return true;
      lastGo = now;
      const w = lastRow.r - lastRow.l;
      const hits = K.fanSpots.filter(sp => sp.id !== me.id && Math.abs(sp.x - px) <= lastRow.h * 0.5
        && (py === undefined || Math.abs(sp.y - lastRow.h * 0.5 - py) <= lastRow.h));
      const hit = hits.sort((a, b) => b.depth - a.depth)[0];
      const below = hit ? topOf(hit.id) : null;
      const base = below && rootOf(below);
      const all = K.comp.throwers.filter(human);
      const target = base ? (K.spot[base] !== undefined ? K.spot[base]
        : (all.findIndex(f => f.id === base) + 0.5) / all.length) : null;
      const s = spotOf(base ? target : (px + lastRow.shift - lastRow.l) / w);
      if (s === null) return false;
      if (R.isHost) hostGo(me.id, s, below);
      else {
        applyGo(me.id, s, below);
        R.send({ t: 'go', round: c.room, s, ...(below ? { on: below } : {}) });
      }
      return true;
    };
    // The button: on a spectator's phone while someone else is on turn, never over the room's screens.
    let button = null, lastCheer = -1e9, buttonShown = null;
    function cheerButton() {
      if (!R) return;
      const fan = K.fans().some(f => f.p === R.me) && !R.paused;
      const room = document.getElementById('aipr');
      const want = fan && !(room && !room.hidden);
      if (want && !button) {
        button = document.createElement('button');
        button.id = 'kisa-cheer'; button.textContent = '📣 Kannusta';
        Object.assign(button.style, { position: 'fixed', zIndex: 50, font: '800 16px system-ui,sans-serif', padding: '10px 14px',
          border: '0', borderRadius: '14px', background: '#f2c94c', color: '#2b2416', boxShadow: '0 4px 0 #b08a1c',
          touchAction: 'manipulation', right: 'calc(env(safe-area-inset-right,0px) + 12px)', bottom: 'calc(env(safe-area-inset-bottom,0px) + 14px)' },
          o.cheerAt || {});
        ['pointerdown', 'pointerup', 'pointermove', 'touchstart', 'touchend', 'touchmove', 'mousedown', 'mouseup', 'click']
          .forEach(type => button.addEventListener(type, ev => ev.stopPropagation(), { passive: true }));
        button.addEventListener('click', () => { if (performance.now() - lastCheer > 1200) cheer(); });
        document.body.appendChild(button);
      }
      if (button && want !== buttonShown) { buttonShown = want; button.hidden = !want; button.style.display = want ? '' : 'none'; }
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
    // The podium shows until the player taps it away (K.skip), then the menu (alone) or the room
    // (with friends).
    K.step = dt => {
      cheerButton();
      const e = K.ending;
      if (!e) return false;
      const was = e.t;
      e.t += dt;
      // A chime as each medal goes on (not when a tap skips past it): a shared place's medals go
      // on one after another in their block's time, as podium() hangs them, each with its chime.
      if (o.chime) {
        const seen = [0, 0, 0], all = [0, 0, 0];
        e.res.forEach(r => { const m = medalOf(r); if (m >= 0) all[m]++; });
        e.res.forEach(r => {
          const m = medalOf(r);
          if (m < 0) return;
          const at = MEDAL_T[m] + HANG * (seen[m]++ + 0.8) / all[m];
          if (was < at && e.t >= at && e.t - at < 0.3) o.chime(m);
        });
      }
      if (e.leave) {
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
    // A tap during the ceremony finishes it (alone; with friends every phone plays it all), and a
    // tap after it leaves the podium for the menu or the room. Nothing leaves it by itself.
    K.skip = () => {
      const e = K.ending;
      if (!e) return;
      if (e.t >= PODIUM_DONE) e.leave = true;
      else if (!isNet()) e.t = PODIUM_DONE;
    };
    // box: {w, top, bottom, middle}; middle centres the board between top and bottom.
    K.drawBoard = (x, final, box) => (K.box = F.board(x, K, final, box));
    // box: {left, top, w, bottom}: the whole end screen, the podium and the standings under it
    // (beside it on a phone on its side).
    K.drawPodium = (x, box) => { if (K.ending) podium(x, K, o, box); };
    return K;
  }

  window.AiPelitKisa = { meet, rounds, COLORS, gauss, shuffle, metres, PODIUM_DONE };
})();
