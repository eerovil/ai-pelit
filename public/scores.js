// Online high-score lists for a game version (#25). A version opts in with
//
//   <script src="../../../scores.js" data-game="<slug>" data-order="high|low" data-corner="bottom-right"></script>
//
// and calls AiPelitScores.submit(score) when a round ends (plus .board(id, label) when it keeps a
// list per course). It draws a "🏆" chip that opens the list. The shelf loads it with
// `data-shelf`: no chip, and AiPelitScores.list()/.top()/.row() draw the lists outside the games.
//
// What a list shows lives in GAMES below, not in the games: how a score reads, and the highest
// level reached, which this script reads from the game's own save on the phone and sends with
// each score. So a change to a list is a change here and in server/api.js, never a new version.
//
// Everything here is an extra: the game never waits for it, and with no network a score waits
// on the phone (ai-pelit:_tulokset:jono) and is sent the next time the game is open online.
// The nickname is one per phone, for every game (ai-pelit:_pelaaja:*), and shows on the lists
// only once the admin has approved it. Later versions load this same file, so it must stay
// compatible with every version that uses it.
(function () {
  'use strict';
  var script = document.currentScript;
  var API = new URL('api/', script.src).href;
  var GAME = script.getAttribute('data-game') || '';
  var ORDER = script.getAttribute('data-order') === 'low' ? 'low' : 'high';
  var SHELF = script.hasAttribute('data-shelf');
  var corner = (script.getAttribute('data-corner') || 'bottom-right').split('-');
  var vertical = corner[0] === 'top' ? 'top' : 'bottom';
  var horizontal = corner[1] === 'left' ? 'left' : 'right';
  var vm = location.pathname.match(/\/v(\d+)\//);
  var VERSION = vm ? +vm[1] : 1;

  var K = 'ai-pelit:_pelaaja:', QUEUE = 'ai-pelit:_tulokset:jono';
  // What the server already has from this phone, per list: {score, level}. A round that beats
  // neither is not sent, which saves the site's daily request quota.
  var SENT = 'ai-pelit:_tulokset:lahetetyt';
  function load(k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

  // ---- What each game's list shows ----
  function fixed(n, d) { return n.toFixed(d).replace('.', ','); }
  function minutes(t) { var m = Math.floor(t / 60), s = t - 60 * m; return m + '.' + (s < 10 ? '0' : '') + fixed(Math.floor(s * 10) / 10, 1); }
  // A number the game keeps in its own save (ai-pelit:<slug>:<name>); read only, never written.
  function saved(slug, name) { var v = Math.floor(Number(load('ai-pelit:' + slug + ':' + name, 0))); return isFinite(v) ? v : 0; }
  var GAMES = {
    // Highest ollie; level: the level the player is on (saved as 'level').
    sormiskeitti: { order: 'high', score: function (s) { return s + ' cm'; }, level: function () { return saved('sormiskeitti', 'level'); } },
    // Best routine total; level: 'taso'.
    voimistelu: { order: 'high', score: function (s) { return fixed(s, 3); }, level: function () { return saved('voimistelu', 'taso'); } },
    // The shelf shows the longest streak (v3 on, list 'putki'); v2's level list ('main') is kept
    // but only v2's own 🏆 shows it.
    puhelinkoppi: { order: 'high', list: 'putki', score: function (s) { return 'putki ' + s; } },
    // Fastest time, one list per course; level: courses passed ('taso' is the first unpassed one).
    hiihto: {
      order: 'low', score: minutes, boards: true,
      level: function () { return saved('hiihto', 'taso') - 1; },
      levelText: function (n) { return n + (n === 1 ? ' rata' : ' rataa') + ' läpi'; },
    },
    // Most points in one game; level: the highest level reached (saved as 'taso').
    piano: { order: 'high', score: function (s) { return s + ' p'; }, level: function () { return saved('piano', 'taso'); } },
    // Fastest 100 m in seconds; level: 'taso', the level the player is on.
    aitajuoksu: { order: 'low', score: function (s) { return fixed(s, 2) + ' s'; }, level: function () { return saved('aitajuoksu', 'taso'); } },
    // Fastest run through the obstacle course in seconds; level: 'taso', the level the player is on.
    kaaosrata: { order: 'low', score: function (s) { return fixed(s, 2) + ' s'; }, level: function () { return saved('kaaosrata', 'taso'); } },
  };
  if (GAMES[GAME]) ORDER = GAMES[GAME].order;
  function scoreText(game, s) { return GAMES[game] ? GAMES[game].score(s) : String(s); }
  function levelText(game, n) { var c = GAMES[game]; return c && c.levelText ? c.levelText(n) : 'taso ' + n; }
  function levelOf(game) { var c = GAMES[game], n = c && c.level ? c.level() : 0; return n >= 1 ? n : null; }

  function playerId() {
    var id = load(K + 'id', '');
    if (!/^[a-f0-9]{32}$/.test(id)) {
      var b = new Uint8Array(16);
      crypto.getRandomValues(b);
      id = Array.prototype.map.call(b, function (n) { return (n < 16 ? '0' : '') + n.toString(16); }).join('');
      save(K + 'id', id);
    }
    return id;
  }

  var board = 'main', boardLabel = '', fmt = function (s) { return scoreText(GAME, s); };
  var better = function (a, b) { return ORDER === 'low' ? a < b : a > b; };

  // ---- Sending: one best score per list waits in the queue until the server has it ----
  var sending = false;
  function post(path, body) {
    return fetch(API + path, {
      keepalive: true, // still sent when the player leaves the game right after the round
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
    }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (b) { b.httpStatus = r.status; return b; }); });
  }

  // Make sure the server knows this phone's current name. Resolves true when it does.
  function register() {
    var name = load(K + 'nimi', '');
    if (!name) return Promise.resolve(false);
    if (load(K + 'lahetetty', '') === name) return Promise.resolve(true);
    return post('players', { id: playerId(), name: name }).then(function (b) {
      if (b.httpStatus === 200) { save(K + 'lahetetty', name); save(K + 'tila', b.status); return true; }
      if (b.httpStatus === 409) save(K + 'tila', 'taken');
      if (b.httpStatus === 429) save(K + 'tila', 'busy'); // spam limit: tried again later
      return false;
    });
  }

  var again = false; // a flush was asked for while one was running: run once more after it
  function flush() {
    if (sending) { again = true; return Promise.resolve(); }
    if (!load(K + 'nimi', '')) return Promise.resolve();
    sending = true; again = false;
    return register().then(function (ok) {
      if (!ok) return;
      var queue = load(QUEUE, {});
      var keys = Object.keys(queue);
      return keys.reduce(function (p, key) {
        return p.then(function (go) {
          if (!go) return false;
          var q = queue[key], lvl = levelOf(q.game) || 0, had = load(SENT, {})[key];
          var qBetter = GAMES[q.game] && GAMES[q.game].order === 'low' ? function (a, b) { return a < b; } : function (a, b) { return a > b; };
          if (had && !qBetter(q.score, had.score) && lvl <= (had.level || 0)) {
            // Nothing new for the server: neither a better score nor a higher level than it has.
            var left = load(QUEUE, {});
            if (left[key] && left[key].score === q.score) { delete left[key]; save(QUEUE, left); }
            return true;
          }
          // The level as the game's save has it now (it only ever rises); exactly this one is
          // recorded as the server's once it answers, whatever the game saves meanwhile.
          var sentLevel = lvl || null;
          return post('scores', { player: playerId(), game: q.game, board: q.board, version: q.version, score: q.score, level: sentLevel })
            .then(function (b) {
              if (b.httpStatus === 404) { save(K + 'lahetetty', ''); return false; } // server forgot us: register again
              // Kept for later unless the server took it. Only a 400 (a score it can never take)
              // is dropped, so one bad item cannot block the queue for good.
              if (b.httpStatus !== 400 && (b.httpStatus < 200 || b.httpStatus > 299)) return false;
              // Done with the item, unless a better score or a higher level came in while it was
              // on its way: then it stays, and goes again.
              var now = load(QUEUE, {});
              if (now[key] && now[key].score === q.score && (b.httpStatus === 400 || (levelOf(q.game) || 0) <= (sentLevel || 0))) {
                delete now[key]; save(QUEUE, now);
              }
              if (b.httpStatus !== 400) {
                var sent = load(SENT, {}), was = sent[key];
                var keep = was && !qBetter(q.score, was.score);
                sent[key] = { score: keep ? was.score : q.score, level: Math.max(sentLevel || 0, (was && was.level) || 0) };
                save(SENT, sent);
              }
              return true;
            });
        });
      }, Promise.resolve(true));
    }).catch(function () {}).then(function () {
      sending = false;
      if (again) return flush();
    });
  }

  function submit(score) {
    if (!GAME || typeof score !== 'number' || !isFinite(score)) return;
    var queue = load(QUEUE, {}), key = GAME + '|' + board, old = queue[key];
    // Whether the round brings anything new (a better score, or a higher level) is decided when it
    // is sent, not here: a game may save its new level only after this call (Sormiskeitti v5 does).
    if (!old || better(score, old.score)) {
      queue[key] = { game: GAME, board: board, version: VERSION, score: score };
      save(QUEUE, queue);
    }
    if (!load(K + 'nimi', '') && !load(K + 'kysytty', false)) {
      // The first score on this phone asks for a nickname, once.
      save(K + 'kysytty', true);
      open();
      return;
    }
    flush();
  }

  // ---- The list ----
  var panel = null;
  // One row: place, name, score, the level reached and the version it came from.
  function rowEl(game, r, mine, format) {
    var d = el('div', 'display:flex;gap:8px;padding:5px 8px;border-radius:8px;' + (mine ? 'background:#3a4570;font-weight:700' : ''));
    d.className = 'tulos';
    d.appendChild(el('span', 'width:2.2em;text-align:right;color:#b8c2e0', r.rank ? r.rank + '.' : '–'));
    d.appendChild(el('span', 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap', r.name));
    d.appendChild(el('span', 'font-variant-numeric:tabular-nums', (format || function (s) { return scoreText(game, s); })(r.score)));
    // Always there, empty without a level, so the scores line up.
    d.appendChild(el('span', 'min-width:3.6em;color:#b8c2e0;font-size:12px;align-self:center;white-space:nowrap', r.level ? levelText(game, r.level) : ''));
    d.appendChild(el('span', 'width:2.4em;color:#8f9ac0;font-size:12px;align-self:center', 'v' + r.version));
    return d;
  }
  function el(tag, css, text) {
    var e = document.createElement(tag);
    if (css) e.style.cssText = css;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  // Like back.js: the game never sees a touch or a key meant for the list.
  function shield(e) {
    ['pointerdown', 'pointerup', 'pointermove', 'touchstart', 'touchend', 'touchmove', 'mousedown', 'mouseup', 'click', 'keydown', 'keyup']
      .forEach(function (type) { e.addEventListener(type, function (ev) { ev.stopPropagation(); }, { passive: true }); });
  }
  var BTN = 'border:0;border-radius:10px;padding:10px 14px;font:600 15px system-ui,sans-serif;touch-action:manipulation;';

  function close() { if (panel) { panel.remove(); panel = null; } }

  function open() {
    close();
    panel = el('div', 'position:fixed;inset:0;z-index:2147483646;background:rgba(10,14,30,.82);display:flex;align-items:center;justify-content:center;padding:calc(env(safe-area-inset-top,0px) + 12px) 12px calc(env(safe-area-inset-bottom,0px) + 12px);font:15px/1.35 system-ui,sans-serif;color:#fff;touch-action:manipulation');
    panel.id = 'ai-pelit-tulokset';
    shield(panel);
    var box = el('div', 'background:#1c2340;border-radius:16px;padding:16px;width:100%;max-width:340px;max-height:100%;overflow:auto;box-shadow:0 8px 30px rgba(0,0,0,.5)');
    panel.appendChild(box);
    box.appendChild(el('div', 'font-weight:800;font-size:19px', '🏆 Tulokset' + (boardLabel ? ' · ' + boardLabel : '')));
    var nameRow = el('div', 'margin:10px 0;color:#cfd6ee');
    var listBox = el('div', 'margin:8px 0');
    var note = el('div', 'color:#b8c2e0;font-size:13px;min-height:1em');
    box.appendChild(nameRow); box.appendChild(listBox); box.appendChild(note);
    var closeBtn = el('button', BTN + 'background:#3a4570;color:#fff;width:100%;margin-top:12px', 'Sulje');
    closeBtn.onclick = close;
    box.appendChild(closeBtn);
    document.body.appendChild(panel);

    function showName(editing) {
      nameRow.textContent = '';
      var name = load(K + 'nimi', ''), status = load(K + 'tila', '');
      if (editing || !name) {
        nameRow.appendChild(el('div', 'margin-bottom:6px', name ? 'Uusi nimimerkki:' : 'Mikä on nimimerkkisi? Se näkyy kaikkien pelien tuloslistoilla, kun ylläpitäjä on hyväksynyt sen.'));
        var row = el('div', 'display:flex;gap:8px');
        var input = el('input', 'flex:1;min-width:0;border:0;border-radius:10px;padding:10px;font:16px system-ui,sans-serif');
        input.maxLength = 16; input.value = name; input.placeholder = 'Nimimerkki'; input.id = 'ai-pelit-nimi';
        var ok = el('button', BTN + 'background:#ffd45c;color:#222', 'Tallenna');
        ok.onclick = function () {
          var v = input.value.replace(/\s+/g, ' ').trim();
          if (!v) return;
          save(K + 'nimi', v); save(K + 'tila', 'pending');
          showName(false);
          flush().then(afterSend);
        };
        row.appendChild(input); row.appendChild(ok);
        nameRow.appendChild(row);
        setTimeout(function () { try { input.focus(); } catch (e) {} }, 50);
        return;
      }
      var text = { pending: ' (odottaa hyväksyntää)', rejected: ' — nimeä ei hyväksytty, valitse toinen', taken: ' — nimi on jo käytössä, valitse toinen', busy: ' — ei voitu vielä tallentaa, yritetään myöhemmin' }[status] || '';
      nameRow.appendChild(el('span', '', 'Nimimerkki: '));
      nameRow.appendChild(el('b', 'color:#fff', name));
      nameRow.appendChild(el('span', status === 'pending' || status === 'busy' ? '' : 'color:#ff9a8a', text));
      var change = el('button', BTN + 'background:transparent;color:#ffd45c;padding:4px 8px', 'Vaihda');
      change.onclick = function () { showName(true); };
      nameRow.appendChild(change);
    }

    function row(r, mine) { return rowEl(GAME, r, mine, fmt); }

    function refresh() {
      if (!panel) return;
      var url = API + 'scores?game=' + encodeURIComponent(GAME) + '&board=' + encodeURIComponent(board) + '&player=' + playerId();
      note.textContent = 'Haetaan…';
      fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (b) {
        if (!panel) return;
        listBox.textContent = '';
        b.rows.forEach(function (r) { listBox.appendChild(row(r, r.me)); });
        var inTop = b.rows.some(function (r) { return r.me; });
        if (b.mine && !inTop) {
          if (b.rows.length) listBox.appendChild(el('div', 'text-align:center;color:#8f9ac0', '⋯'));
          listBox.appendChild(row({ rank: b.mine.rank, name: b.mine.name, score: b.mine.score, level: b.mine.level, version: b.mine.version }, true));
        }
        if (!b.rows.length && !b.mine) listBox.appendChild(el('div', 'color:#b8c2e0', 'Listalla ei ole vielä ketään.'));
        var waiting = Object.keys(load(QUEUE, {})).length;
        note.textContent = b.mine && b.mine.status === 'pending' ? 'Tuloksesi näkyy muille, kun nimimerkki on hyväksytty.'
          : waiting && load(K + 'nimi', '') ? 'Tuloksia odottaa lähetystä.' : '';
      }).catch(function () {
        if (!panel) return;
        listBox.textContent = '';
        note.textContent = 'Ei verkkoyhteyttä. Tuloksesi lähtevät, kun peli on taas auki verkossa.';
      });
    }

    // Sending may have changed the name's state (taken, busy): show it, unless it is being edited.
    function afterSend() {
      if (panel && !nameRow.querySelector('input')) showName(false);
      refresh();
    }

    // The admin may have approved or rejected the name since last time.
    function checkName() {
      var name = load(K + 'nimi', '');
      if (!name || load(K + 'lahetetty', '') !== name) return;
      fetch(API + 'players/' + playerId()).then(function (r) { return r.ok ? r.json() : null; }).then(function (p) {
        if (!p || p.name !== name || p.status === load(K + 'tila', '')) return;
        save(K + 'tila', p.status);
        if (panel && !nameRow.querySelector('input')) showName(false);
      }).catch(function () {});
    }

    showName(false);
    flush().then(function () { afterSend(); checkName(); });
  }

  // ---- The chip ----
  var chip = el('button', [
    'position:fixed', 'z-index:2147483645',
    vertical + ':calc(env(safe-area-inset-' + vertical + ', 0px) + 6px)',
    horizontal + ':calc(env(safe-area-inset-' + horizontal + ', 0px) + 6px)',
    'padding:6px 10px', 'border:0', 'border-radius:999px', 'background:rgba(0,0,0,.45)', 'color:#fff',
    'font:600 13px/1 system-ui,sans-serif', 'touch-action:manipulation',
  ].join(';'), '🏆 Tulokset');
  chip.id = 'ai-pelit-tulokset-nappi';
  chip.setAttribute('aria-label', 'Tuloslista');
  shield(chip);
  chip.onclick = function () { open(); };
  function add() { document.body.appendChild(chip); }
  if (!SHELF) { if (document.body) add(); else document.addEventListener('DOMContentLoaded', add); }

  addEventListener('online', function () { flush(); });
  flush();

  window.AiPelitScores = {
    submit: submit,
    open: function () { open(); },
    board: function (id, label) { board = id; boardLabel = label || ''; },
    format: function (f) { fmt = f; },
    // For the shelf: which games keep lists, and their lists.
    games: GAMES,
    list: function (game, b) {
      return fetch(API + 'scores?game=' + encodeURIComponent(game) + '&board=' + encodeURIComponent(b || 'main') + '&player=' + playerId())
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    },
    top: function () {
      return fetch(API + 'scores/top').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    },
    row: function (game, r, mine) { return rowEl(game, r, mine); },
    scoreText: scoreText,
  };
})();
