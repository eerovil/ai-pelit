// The bar-height meet format for the shared athletics library (#165): high jump and pole vault.
// Load it after kisa.js and pass it as the meet's format:
//
//   <script src="../../../lib/yleisurheilu-1/kisa.js"></script>
//   <script src="../../../lib/yleisurheilu-1/korkeus.js"></script>
//   AiPelitKisa.meet({ format: AiPelitKisa.heights({ heights: lv => [...], plan: (t, c) => {...} }), ... })
//
// The real rules: the bar rises through `heights`; at each height everyone still in takes a first
// attempt in the drawn order, then those who failed a second, then a third. A competitor may pass
// a height ('-'), even after failing at it; three failures in a row, at one height or over several,
// and they are out. The last one in who leads may stop ('S'). A competitor keeps `rec`: per height
// index its attempts as on a real result sheet ('O' cleared, 'X' failed, '-' passed), `run` (failures
// in a row) and `out`. The computer starts at `first` and passes the heights in `skip`, set by
// `plan(t, comp)`. The standings go by the best height, then fewer failures at it, then fewer
// failures in all up to it (the countback); a full tie shares the place.
//
// Like kisa.js, this file never changes once published: a fix goes in yleisurheilu-2/.
(function () {
  'use strict';
  const K0 = window.AiPelitKisa;
  const medal = p => ['🥇', '🥈', '🥉'][p - 1] || '';
  function fit(x, s, w) { if (x.measureText(s).width <= w) return s; while (s.length > 1 && x.measureText(s + '…').width > w) s = s.slice(0, -1); return s + '…'; }
  function rr(x, x0, y0, w, h, r) { x.beginPath(); x.roundRect(x0, y0, w, h, r); }
  const xs = r => ((r || '').match(/X/g) || []).length;

  function heights(o) {
    const TRIES = o.tries || 3;
    const byId = (c, id) => c.throwers.find(t => t.id === id);
    // Does this competitor take an attempt now, in round `att` at height `hi`?
    function due(t, hi, att) {
      if (t.out) return false;
      if (t.p === null && (hi < (t.first || 0) || (t.skip || []).includes(hi))) return false;
      const r = t.rec[hi] || '';
      return !/[O-]/.test(r) && r.length === att - 1;
    }
    function score(c, t) {
      let b = -1;
      t.rec.forEach((r, i) => { if (r && r.includes('O')) b = i; });
      let total = 0;
      for (let i = 0; i <= b; i++) total += xs(t.rec[i]);
      return { b, h: b >= 0 ? c.heights[b] : -1, at: b >= 0 ? xs(t.rec[b]) : 0, total };
    }
    const better = (a, b) => a.h !== b.h ? a.h > b.h : a.at !== b.at ? a.at < b.at : a.total < b.total;
    const tied = (a, b) => a.h === b.h && a.at === b.at && a.total === b.total;
    function mark(c, t, m) {
      if (m === 'S') { t.out = true; t.stop = true; return; }
      t.rec[c.hi] = (t.rec[c.hi] || '') + m;
      if (m === 'O') t.run = 0;
      if (m === 'X' && ++t.run >= TRIES) t.out = true;
    }
    const F = {
      TRIES,
      blank: () => ({ throwers: [], order: [], heights: [], hi: 0, att: 1, turn: 0 }),
      setup(c) {
        c.heights = o.heights(c.level);
        c.hi = 0; c.att = 1; c.turn = 0;
        c.order = K0.shuffle(c.throwers.map(t => t.id));
        c.throwers.forEach(t => {
          t.rec = []; t.run = 0; t.out = false;
          if (t.p === null && o.plan) o.plan(t, c);
        });
      },
      due,
      current(c) {
        if (!c.order || c.turn >= c.order.length) return null;
        const t = byId(c, c.order[c.turn]);
        return t && due(t, c.hi, c.att) ? t : null;
      },
      score: (c, t) => score(c, t),
      standings(c) {
        const sc = new Map(c.throwers.map(t => [t, score(c, t)]));
        return c.throwers.slice().sort((a, b) => {
          const sa = sc.get(a), sb = sc.get(b);
          if (!tied(sa, sb)) return better(sa, sb) ? -1 : 1;
          return c.throwers.indexOf(a) - c.throwers.indexOf(b);
        });
      },
      placeOf(c, t) { const s = score(c, t); return 1 + c.throwers.filter(u => u !== t && better(score(c, u), s)).length; },
      // The best height cleared (a height, -1 none); bestOf takes the competitor only, so it reads
      // the meet from the competitor's `rec` and the heights kept on it by `setup` of the meet.
      bestOf(t) { let b = -1; (t.rec || []).forEach((r, i) => { if (r && r.includes('O')) b = i; }); return b >= 0 && F.c ? F.c.heights[b] : -1; },
      valid: m => typeof m === 'string' && /^[OX\-S]$/.test(m),
      bar: c => c.heights[c.hi],
      // The last one still in, everyone else out.
      lastIn: (c, t) => !!t && !t.out && c.throwers.every(u => u === t || u.out),
      // The last one in who also leads (by countback too): they have won, and may stop.
      soleWinner: (c, t) => F.lastIn(c, t) && score(c, t).h > 0 && F.placeOf(c, t) === 1,
      // Takes the computer's turns up to the next player on a phone; true when the meet is over.
      advance(c, cpu, human) {
        F.c = c;
        for (let guard = 0; guard < 5000; guard++) {
          if (!c.throwers.some(t => !t.out) || c.hi >= c.heights.length) return true;
          if (c.turn >= c.order.length) {
            c.turn = 0;
            if (++c.att > TRIES || !c.order.some(id => due(byId(c, id), c.hi, c.att))) { c.hi++; c.att = 1; }
            continue;
          }
          const t = byId(c, c.order[c.turn]);
          if (!due(t, c.hi, c.att)) { c.turn++; continue; }
          if (human(t)) return false;
          mark(c, t, cpu(t));
          c.recent.push(t.id);
          c.turn++; c.seq++;
        }
        return true;
      },
      take(c, t, m) {
        F.c = c;
        mark(c, t, m);
        c.recent = [t.id];
        c.turn++; c.seq++;
      },
      results(c) {
        F.c = c;
        return F.standings(c).map(t => {
          const s = score(c, t);
          return { id: t.id, p: t.p, name: t.name, col: t.col, best: s.h, at: s.at, total: s.total, place: F.placeOf(c, t), out: t.out, fin: true, marks: [] };
        });
      },
      endText(e, K) {
        if (e.at < 0) return 'Kisa päättyi';
        const m = e.mark > 0 ? K.fmt(e.mark) : K.none;
        if (!(e.mark > 0)) return e.place + '. sija · ' + m;
        return e.place === 1 ? '🥇 Voitit kisan! ' + m : (medal(e.place) ? medal(e.place) + ' ' : '') + e.place + '. sija · ' + m;
      },
      // The standings: between turns the attempts at this height and the best, at the end the
      // failures that settle a tie and the result, with the medals.
      board(x, K, final, box) {
        const c = K.comp, rows = final ? K.ending.res : F.results(c), W = box.w;
        F.c = c;
        const head = final ? 50 : 62, foot = final ? 0 : 26;
        const avail = box.bottom - box.top - head - foot - 8;
        const rowH = Math.min(24, Math.floor(avail / rows.length));
        const h = head + rowH * rows.length + foot + 8;
        const y0 = box.middle ? Math.max(box.top, (box.top + box.bottom - h) / 2) : box.top;
        x.fillStyle = 'rgba(10,20,40,.92)'; rr(x, 12, y0, W - 24, h, 14); x.fill();
        x.textAlign = 'center'; x.fillStyle = '#ffd166'; x.font = '900 19px system-ui';
        x.fillText(final ? 'Lopputulokset' : 'Rima ' + K.fmt(F.bar(c)), W / 2, y0 + 30);
        const fs = Math.min(15, rowH - 7), right = W - 26, lastW = 62;
        x.font = '700 11px system-ui'; x.fillStyle = '#8fa5bb'; x.textAlign = 'right';
        if (!final) { x.fillText('NYT', right - lastW - 6, y0 + 52); x.fillText('PARAS', right, y0 + 52); }
        else { x.fillText('PUDOTUKSET', right - lastW - 10, y0 + 44); x.fillText('TULOS', right, y0 + 44); }
        rows.forEach((r, i) => {
          const y = y0 + head + i * rowH + rowH * 0.7, mine = r.p === K.me, t = !final && byId(c, r.id);
          if (mine) { x.fillStyle = 'rgba(255,209,102,.18)'; x.fillRect(16, y - rowH * 0.72, W - 32, rowH); }
          x.globalAlpha = !final && r.out ? 0.5 : 1;
          x.fillStyle = r.col; x.beginPath(); x.arc(46, y - fs * 0.33, Math.max(3, fs * 0.33), 0, 7); x.fill();
          x.font = '700 ' + fs + 'px system-ui'; x.textAlign = 'right'; x.fillStyle = '#b9cfe0';
          x.fillText((final && medal(r.place)) || r.place + '.', 38, y);
          x.textAlign = 'left'; x.font = (mine ? '900 ' : '600 ') + fs + 'px system-ui'; x.fillStyle = mine ? '#ffd166' : '#fff';
          x.fillText(fit(x, mine && K.isNet() ? 'Sinä' : r.name, right - lastW - 64 - 56), 56, y);
          x.textAlign = 'right'; x.font = '900 ' + fs + 'px system-ui'; x.fillStyle = mine ? '#ffd166' : '#fff';
          x.fillText(r.best > 0 ? K.fmt(r.best) : '–', right, y);
          x.font = '800 ' + (fs - 2) + 'px system-ui';
          if (final) {
            x.fillStyle = 'rgba(185,207,224,.8)';
            // Failures at the best height, then in all up to it: the countback for a tie.
            if (r.best > 0) x.fillText(r.at + ' / ' + r.total, right - lastW - 10, y);
          } else {
            const now = t ? (t.rec[c.hi] || '').replace(/-/g, '–') : '';
            const recent = c.recent.includes(r.id);
            const waiting = t && t.p === null && (c.hi < (t.first || 0) || (t.skip || []).includes(c.hi));
            x.fillStyle = r.out ? '#ff9a8b' : /X$/.test(now) ? '#ff9a8b' : recent ? '#8ecae6' : 'rgba(185,207,224,.85)';
            x.fillText(r.out && !now.includes('O') ? (now ? now + ' ulos' : 'ulos') : waiting ? '' : now, right - lastW - 6, y);
          }
          x.globalAlpha = 1;
        });
        if (!final) {
          const t = F.current(c);
          x.textAlign = 'center'; x.font = '700 14px system-ui'; x.fillStyle = '#b9cfe0';
          const n = t ? (t.rec[c.hi] || '').length + 1 : 1;
          x.fillText(t ? (t.p === K.me ? 'Seuraavaksi: sinä' : 'Seuraavaksi: ' + fit(x, t.name, W - 160)) + ' · ' + n + '. yritys' : '', W / 2, y0 + h - 14);
        }
        return { x: 12, y: y0, w: W - 24, h, rowH };
      },
    };
    return F;
  }
  K0.heights = heights;
})();
