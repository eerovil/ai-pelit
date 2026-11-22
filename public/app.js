// The shelf: lists every game from catalog.json and every version of one game.
// Routes are the hash: "" or "#/" is the shelf, "#/<slug>" is one game; a category's key (an old
// group page) opens the shelf with that category's button on.
(function () {
  'use strict';

  var view = document.getElementById('view');
  var statusEl = document.getElementById('status');
  var catalog = null;

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) node.appendChild(c); });
    return node;
  }

  function fiDate(iso) {
    var p = iso.split('-');
    return Number(p[2]) + '.' + Number(p[1]) + '.' + p[0];
  }

  function playUrl(slug, n) { return 'games/' + slug + '/v' + n + '/'; }

  function latest(game) { return game.versions[game.versions.length - 1]; }

  function setStatus(text) {
    statusEl.textContent = text || '';
    statusEl.hidden = !text;
  }

  // The game's picture (#33), a mid-play screenshot the build names in the catalog.
  function thumb(game, cls, w, h) {
    if (!game.thumb) return null;
    return el('img', { class: cls, src: game.thumb, alt: cls === 'thumb' ? '' : game.title, width: String(w), height: String(h) });
  }

  // The version and how many plays, under the game's name. Only the newest is kept (#346), so
  // how many there have been is the game page's history, not a count here.
  function metaLine(game) {
    var v = latest(game);
    return el('p', { class: 'muted meta' }, [
      document.createTextNode('v' + v.n),
      el('span', { class: 'plays', text: playsText(game.slug) }),
      nowBadge(game.slug),
    ]);
  }

  // The shelf (#523): every game is one short row, athletics events too. Above the rows, the
  // games this phone played last, a search box and buttons: Kaikki, Uudet, Päivitetyt, then the
  // categories (CATEGORIES in scripts/build.py). Everything runs on the phone from catalog.json.
  function shelfRow(game) {
    var v = latest(game);
    return el('li', { class: 'shelf-row', 'data-slug': game.slug }, [
      el('a', { class: 'shelf-row-main', href: '#/' + game.slug }, [
        thumb(game, 'thumb small', 36, 48),
        el('div', {}, [el('h2', { text: game.title }), metaLine(game)]),
      ]),
      el('a', { class: 'button play', href: playUrl(game.slug, v.n), 'aria-label': 'Pelaa ' + game.title, text: '▶' }),
    ]);
  }

  function isCategory(slug) {
    return (catalog.categories || []).some(function (c) { return c.slug === slug; });
  }

  // The buttons: two orders over every game, then one per category, which lists most played first.
  var NEW = 'uudet', UPDATED = 'paivitetyt';
  function shelfButtons() {
    return [['', 'Kaikki'], [NEW, 'Uudet'], [UPDATED, 'Päivitetyt']].concat(
      (catalog.categories || []).map(function (c) { return [c.slug, c.title]; }));
  }

  // The search text and the button last until the app closes, so back from a game finds the
  // same list and a new start shows every game.
  var FIND_KEY = 'ai-pelit:_hylly:haku';
  var find = { q: '', cat: '' };
  try {
    var savedFind = JSON.parse(sessionStorage.getItem(FIND_KEY));
    if (savedFind && typeof savedFind.q === 'string' && typeof savedFind.cat === 'string') find = savedFind;
  } catch (e) {}
  function keepFind() {
    try { sessionStorage.setItem(FIND_KEY, JSON.stringify(find)); } catch (e) {}
  }

  function playCount(slug) { return plays[slug] || 0; }

  // The games the chosen button shows, in its order: Uudet by release (the first version, not an
  // update), Päivitetyt by the newest version (the catalog's own order, scripts/build.py), and
  // the rest most played first. Ties keep the catalog's order.
  function shelfGames() {
    var at = {};
    catalog.games.forEach(function (g, i) { at[g.slug] = i; });
    var q = find.q.trim().toLocaleLowerCase('fi');
    var games = catalog.games.filter(function (g) {
      if (find.cat && find.cat !== NEW && find.cat !== UPDATED && g.category !== find.cat) return false;
      return !q || (g.title + ' ' + g.description).toLocaleLowerCase('fi').indexOf(q) >= 0;
    });
    return games.sort(function (a, b) {
      if (find.cat === NEW) {
        var r = (b.released || 0) - (a.released || 0);
        if (r) return r;
      } else if (find.cat !== UPDATED) {
        var d = playCount(b.slug) - playCount(a.slug);
        if (d) return d;
      }
      return at[a.slug] - at[b.slug];
    });
  }

  function fillShelf(list) {
    var games = shelfGames();
    list.replaceChildren.apply(list, games.length ? games.map(shelfRow)
      : [el('li', { class: 'muted no-hits', text: 'Ei osumia.' })]);
  }

  // The games this phone opened last (#523), newest first: public/back.js keeps the list.
  var RECENT_KEY = 'ai-pelit:_hylly:viimeksi';
  function recentRow() {
    var slugs = [];
    try { slugs = JSON.parse(localStorage.getItem(RECENT_KEY)) || []; } catch (e) {}
    var tiles = (Array.isArray(slugs) ? slugs : []).map(gameOf).filter(Boolean).slice(0, 8).map(function (g) {
      return el('a', { class: 'recent', href: playUrl(g.slug, latest(g).n), 'data-slug': g.slug, 'aria-label': 'Pelaa ' + g.title }, [
        el('span', { class: 'recent-pic' }, [thumb(g, 'thumb', 92, 123), el('span', { class: 'recent-play', text: '▶' })]),
        el('span', { class: 'recent-name', text: g.title }),
      ]);
    });
    if (!tiles.length) return null;
    return el('section', { class: 'recent-games' }, [
      el('h2', { text: 'Viimeksi pelatut' }),
      el('div', { class: 'recent-row' }, tiles),
    ]);
  }

  function renderShelf() {
    document.title = 'AI-pelit';
    if (find.cat && !shelfButtons().some(function (b) { return b[0] === find.cat; })) find.cat = '';
    var list = el('ul', { class: 'shelf-rows' });
    var search = el('input', { class: 'shelf-search', type: 'search', placeholder: '🔍 Etsi peliä', 'aria-label': 'Etsi peliä', enterkeyhint: 'search', autocomplete: 'off' });
    search.value = find.q;
    search.addEventListener('input', function () { find.q = search.value; keepFind(); fillShelf(list); });
    // Enter only closes the keyboard: the list already shows the hits.
    search.addEventListener('keydown', function (e) { if (e.key === 'Enter') search.blur(); });
    var buttons = el('div', { class: 'shelf-buttons' });
    shelfButtons().forEach(function (b) {
      var btn = el('button', { type: 'button', class: 'shelf-button', 'data-cat': b[0], 'aria-pressed': String(find.cat === b[0]), text: b[1] });
      btn.addEventListener('click', function () {
        find.cat = b[0];
        keepFind();
        Array.prototype.forEach.call(buttons.children, function (o) { o.setAttribute('aria-pressed', String(o === btn)); });
        fillShelf(list);
      });
      buttons.appendChild(btn);
    });
    fillShelf(list);
    var rooms = el('section', { class: 'open-rooms', hidden: '' });
    var playing = el('section', { class: 'friends-playing', hidden: '' });
    view.replaceChildren.apply(view, [playing, rooms].concat(catalog.games.length
      ? [recentRow(), search, buttons, list].filter(Boolean)
      : [el('p', { class: 'muted', text: 'Ei vielä pelejä.' })]));
    // The chosen button in sight, when it is far along the row.
    var on = buttons.querySelector('[aria-pressed="true"]');
    if (on && on.offsetLeft + on.offsetWidth > buttons.clientWidth) buttons.scrollLeft = on.offsetLeft - 16;
    drawPlaying();
    showRooms(rooms);
    showWaitingNames();
    loadPlays();
    loadPlaying();
  }

  // Every game's public rooms on the shelf (#203): the rooms whose host switched 🌍 Julkinen on
  // and that wait for players (rooms/worker.js), from GET /api/rooms, read while the shelf shows
  // and again every 10 seconds. A tap opens the room's own game version with ?huone=, which joins
  // it (public/rooms.js). Hidden while there are none or no answer, so offline nothing shows.
  var openRooms = [], roomsTimer = 0;
  function roomRow(r) {
    var game = catalog.games.filter(function (g) { return g.slug === r.game; })[0];
    if (!game || !/^[A-Z]{4}$/.test(r.code)) return null;
    // Only a room on the game's newest version (#346): an older one's host has an old copy, and its
    // address leads to the newest, which says so. One newer than this phone's catalog waits too.
    if (r.v !== latest(game).n) return null;
    return el('li', { class: 'room', 'data-code': r.code }, [
      thumb(game, 'thumb small', 36, 48),
      el('div', {}, [
        el('h3', { text: game.title }),
        el('p', { class: 'muted meta', text: 'v' + r.v + ' · koodi ' + r.code + ' · ' + r.n + '/' + r.max + ' pelaajaa' }),
      ]),
      el('a', { class: 'button', href: playUrl(game.slug, r.v) + '?huone=' + r.code, text: 'Liity' }),
    ]);
  }
  function drawRooms(box) {
    var rows = openRooms.map(roomRow).filter(Boolean);
    box.hidden = !rows.length;
    box.replaceChildren(el('h2', { text: 'Avoimet huoneet' }), el('ul', { class: 'rooms' }, rows));
  }
  function showRooms(box) {
    clearTimeout(roomsTimer);
    drawRooms(box);
    if (!window.fetch) return;
    fetch('api/rooms', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      // No answer (offline, an error) hides the list: an old room may be gone by now.
      .then(function (b) { openRooms = b && Array.isArray(b.rooms) ? b.rooms : []; })
      .catch(function () { openRooms = []; })
      .then(function () {
        // Only while this same shelf is still on screen; another page drops it.
        if (!box.isConnected) return;
        drawRooms(box);
        roomsTimer = setTimeout(function () {
          if (box.isConnected && document.visibilityState === 'visible') showRooms(box);
        }, 10000);
      });
  }

  var scores = window.AiPelitScores;

  // A game's page: its top 10, and the player's own place under it. Hiihto has a list per course,
  // Tikanheitto named lists (Mökkitikka first, then Pistekisa) picked with a button each.
  function scoreSection(slug) {
    if (!scores || !scores.games[slug]) return null;
    var box = el('div', { class: 'scores' });
    var picker = null;
    var course = 1;
    var lists = scores.games[slug].lists, listId = lists ? lists[0][0] : 'main';
    if (lists) {
      var buttons = lists.map(function (l) {
        var b = el('button', { type: 'button', class: 'secondary board-list', 'data-board': l[0], text: l[1] });
        b.addEventListener('click', function () {
          listId = l[0];
          buttons.forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
          fill();
        });
        b.setAttribute('aria-pressed', String(l[0] === listId));
        return b;
      });
      picker = el('div', { class: 'board-picker' }, buttons);
    } else if (scores.games[slug].boards) {
      // Any course, not just the ones this phone has reached: ‹ Taso N ›, or type the number.
      var input = el('input', { class: 'board', type: 'number', min: '1', max: '999', inputmode: 'numeric', value: '1', 'aria-label': 'Rata' });
      var go = function (n) {
        course = Math.min(999, Math.max(1, Math.floor(n) || 1));
        input.value = String(course);
        fill();
      };
      var prev = el('button', { type: 'button', class: 'secondary board-prev', 'aria-label': 'Edellinen rata', text: '‹' });
      var next = el('button', { type: 'button', class: 'secondary board-next', 'aria-label': 'Seuraava rata', text: '›' });
      prev.addEventListener('click', function () { go(course - 1); });
      next.addEventListener('click', function () { go(course + 1); });
      input.addEventListener('change', function () { go(Number(input.value)); });
      picker = el('div', { class: 'board-picker' }, [el('span', { text: 'Taso ' }), prev, input, next]);
    }
    var asked = 0; // only the newest request may fill the box: an older one can answer last
    function fill() {
      var mine = ++asked;
      box.replaceChildren(el('p', { class: 'muted', text: 'Haetaan…' }));
      var prefix = scores.games[slug].boardPrefix || 'taso-';
      scores.list(slug, lists ? listId : picker ? prefix + course : 'main').then(function (b) {
        if (mine !== asked) return;
        var rows = b.rows.map(function (r) { return scores.row(slug, r, r.me); });
        if (b.mine && !b.rows.some(function (r) { return r.me; })) {
          if (rows.length) rows.push(el('div', { class: 'muted', text: '⋯' }));
          rows.push(scores.row(slug, b.mine, true));
        }
        if (!rows.length) rows.push(el('p', { class: 'muted', text: 'Listalla ei ole vielä ketään.' }));
        box.replaceChildren.apply(box, rows);
      }).catch(function () {
        if (mine !== asked) return;
        box.replaceChildren(el('p', { class: 'muted', text: 'Tuloksia ei saatu: ei verkkoyhteyttä.' }));
      });
    }
    fill();
    return el('section', { class: 'score-list' }, [el('h2', { text: '🏆 Tulokset' }), picker, box]);
  }

  // Feedback (#184): a player whose nickname the admin approved writes what to fix or add. Only the
  // admin sees it; once a day the host files the new ones in a "Palautteet" issue, and its agent
  // asks Eero which to fix. The box opens from one button, so the page stays as short as it was.
  function feedbackSection(game) {
    if (!scores || !scores.me) return null;
    var box = el('div', { class: 'feedback-box' });
    // What the player wrote, kept while the name is asked again (the admin rejected or the name
    // changed between opening the box and sending), so it is there when the form comes back,
    // on this page or after leaving it, until the tab closes.
    var FEEDBACK_MAX = 5000; // FEEDBACK_MAX in server/api.js
    var DRAFT = 'ai-pelit:_palaute:' + game.slug;
    var draft = '';
    try { draft = sessionStorage.getItem(DRAFT) || ''; } catch (e) {}
    function keep(v) {
      draft = v;
      try { if (v) sessionStorage.setItem(DRAFT, v); else sessionStorage.removeItem(DRAFT); } catch (e) {}
    }
    var open = el('button', { type: 'button', class: 'secondary feedback-open', text: '💬 Anna palautetta' });
    open.addEventListener('click', function () { open.remove(); show(); });

    function nameForm(text, value) {
      var input = el('input', { class: 'feedback-name', maxlength: '16', placeholder: 'Nimimerkki', 'aria-label': 'Nimimerkki' });
      input.value = value || '';
      var save = el('button', { type: 'button', class: 'button', text: 'Tallenna' });
      save.addEventListener('click', function () {
        if (!input.value.trim()) return;
        save.disabled = true;
        scores.setName(input.value).then(show, show);
      });
      box.replaceChildren(el('p', { class: 'muted', text: text }), el('div', { class: 'feedback-row' }, [input, save]));
    }

    function form(name) {
      var text = el('textarea', { class: 'feedback-text', rows: '6', placeholder: 'Mitä korjaisit tai lisäisit?', 'aria-label': 'Palaute' });
      text.value = draft;
      // How much room is left, shown only near the end (#351).
      var left = el('p', { class: 'muted feedback-left', 'aria-live': 'polite' });
      // Counted in characters as the server counts them (an emoji is one), not in the UTF-16
      // units a maxlength counts (an emoji is two). Past the limit, only what was just typed or
      // pasted is cut, found by comparing with the text before it, so nothing written earlier is
      // lost wherever the cursor was.
      var prev = '';
      function count() {
        var chars = Array.from(text.value);
        if (chars.length > FEEDBACK_MAX) {
          var old = Array.from(prev), a = 0, b = 0;
          while (a < old.length && a < chars.length && old[a] === chars[a]) a++;
          while (b < old.length - a && b < chars.length - a && old[old.length - 1 - b] === chars[chars.length - 1 - b]) b++;
          var added = chars.slice(a, chars.length - b).slice(0, Math.max(0, FEEDBACK_MAX - a - b));
          chars = chars.slice(0, a).concat(added, chars.slice(chars.length - b)).slice(0, FEEDBACK_MAX);
          text.value = chars.join('');
          text.selectionStart = text.selectionEnd = Math.min(chars.slice(0, a + added.length).join('').length, text.value.length);
        }
        prev = text.value;
        var n = FEEDBACK_MAX - chars.length;
        left.textContent = n <= 500 ? 'Merkkejä jäljellä ' + n + '.' : '';
      }
      text.addEventListener('input', function () { count(); keep(text.value); });
      count();
      var send = el('button', { type: 'button', class: 'button', text: 'Lähetä' });
      var note = el('p', { class: 'muted feedback-note', role: 'status' });
      send.addEventListener('click', function () {
        if (send.disabled) return; // a second tap while the first is on its way sends nothing
        if (!text.value.trim()) { note.textContent = 'Kirjoita ensin palaute.'; return; }
        send.disabled = true;
        note.textContent = 'Lähetetään…';
        fetch('api/feedback', {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ player: scores.id(), game: game.slug, version: latest(game).n, text: text.value }),
        }).then(function (r) {
          send.disabled = false;
          if (r.ok) { text.value = ''; keep(''); count(); note.textContent = 'Kiitos, ' + name + '! Palaute meni perille.'; return; }
          if (r.status === 403) { keep(text.value); show(); return; }
          note.textContent = r.status === 429 ? 'Olet antanut tänään jo paljon palautetta. Jatka huomenna.' : 'Palautetta ei saatu lähetettyä. Yritä uudelleen.';
        }).catch(function () {
          send.disabled = false;
          note.textContent = 'Ei verkkoyhteyttä. Yritä uudelleen, kun verkko toimii.';
        });
      });
      box.replaceChildren(
        el('p', { class: 'muted', text: 'Nimimerkillä ' + name + '. Vain ylläpitäjä näkee palautteen.' }),
        text,
        left,
        el('div', { class: 'feedback-row' }, [note, send])
      );
      text.focus();
    }

    function show() {
      box.replaceChildren(el('p', { class: 'muted', text: 'Haetaan…' }));
      scores.me().then(function (me) {
        if (me.status === 'approved') form(me.name);
        else if (!me.name) nameForm('Palautetta voi antaa hyväksytyllä nimimerkillä. Valitse nimimerkki: ylläpitäjä hyväksyy sen, ja se näkyy myös tuloslistoilla.');
        else if (me.status === 'rejected' || me.status === 'taken') nameForm('Nimimerkkiä ' + me.name + (me.status === 'taken' ? ' käyttää jo joku muu.' : ' ei hyväksytty.') + ' Valitse toinen.', '');
        else box.replaceChildren(el('p', { class: 'muted feedback-waiting', text: 'Nimimerkkisi ' + me.name + ' odottaa ylläpitäjän hyväksyntää. Sen jälkeen voit antaa palautetta.' }));
      });
    }
    return el('section', { class: 'feedback' }, [open, box]);
  }

  // Play counts (#26): how many times each game has been opened, all versions together, on
  // every phone. The last answer is kept on the phone, so the shelf shows it at once and offline.
  var PLAYS_KEY = 'ai-pelit:_pelikerrat:yhteensa';
  var plays = {};
  try { plays = JSON.parse(localStorage.getItem(PLAYS_KEY)) || {}; } catch (e) {}

  function playsText(slug) {
    var n = playCount(slug);
    if (!n) return '';
    return ' · pelattu ' + n + (n === 1 ? ' kerran' : ' kertaa');
  }

  function loadPlays() {
    fetch('api/plays', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (b) {
        if (!b || !b.games) return;
        var changed = JSON.stringify(b.games) !== JSON.stringify(plays);
        plays = b.games;
        try { localStorage.setItem(PLAYS_KEY, JSON.stringify(plays)); } catch (e) {}
        // New counts can change the most-played order: the shelf follows them.
        // Only the list is redrawn, so the search box keeps its text and the keyboard.
        var list = view.querySelector('.shelf-rows');
        if (changed && list && catalog) {
          var before = Array.prototype.map.call(list.children, function (c) { return c.getAttribute('data-slug'); }).join();
          if (shelfGames().map(function (g) { return g.slug; }).join() !== before) {
            fillShelf(list);
            return;
          }
        }
        Array.prototype.forEach.call(view.querySelectorAll('[data-slug] .plays'), function (span) {
          span.textContent = playsText(span.closest('[data-slug]').getAttribute('data-slug'));
        });
      })
      .catch(function () {});
  }

  // Playing right now (#325): how many have each game open on screen at this moment, only the
  // number, beside the play count. back.js tells the server while a game page shows; read here
  // with the page and again every 20 seconds while it shows. Not kept on the phone: an old
  // number would be wrong, so offline nothing shows.
  var playing = {}, playingTimer = 0;
  function nowCount(slug) {
    return playing[slug] || 0;
  }
  function nowBadge(slug) {
    var n = nowCount(slug);
    var badge = el('span', { class: 'now', 'data-now': slug, text: n ? '● ' + n : '' });
    if (n) badge.setAttribute('aria-label', n + ' pelaa nyt');
    return badge;
  }
  function loadPlaying() {
    clearTimeout(playingTimer);
    if (!window.fetch) return;
    fetch('api/playing', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (b) { playing = b && b.games && typeof b.games === 'object' ? b.games : {}; })
      .catch(function () { playing = {}; })
      .then(function () {
        var badges = view.querySelectorAll('[data-now]');
        Array.prototype.forEach.call(badges, function (old) { old.replaceWith(nowBadge(old.getAttribute('data-now'))); });
        if (!badges.length) return;
        playingTimer = setTimeout(function () {
          if (document.visibilityState === 'visible') loadPlaying();
        }, 20000);
      });
  }

  // On the admin's phone only (it holds the key yllapito/ saved): how many nicknames wait.
  function showWaitingNames() {
    var key = null;
    try { key = localStorage.getItem('ai-pelit:_yllapito:avain'); } catch (e) {}
    if (!key) return;
    fetch('api/admin/players', { headers: { 'x-admin-key': key } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (b) {
        var n = b ? b.players.filter(function (p) { return p.status === 'pending'; }).length : 0;
        if (!n || /^#\/[a-z0-9-]/.test(location.hash) || view.querySelector('.waiting-names')) return;
        view.insertBefore(el('a', { class: 'button big waiting-names', href: 'yllapito/', text: n + (n === 1 ? ' nimimerkki odottaa' : ' nimimerkkiä odottaa') + ' hyväksyntää' }), view.firstChild);
      })
      .catch(function () {});
  }

  function renderGame(slug) {
    var game = catalog.games.filter(function (g) { return g.slug === slug; })[0];
    if (!game) {
      view.replaceChildren(el('p', { text: 'Peliä ei löytynyt.' }), el('a', { href: '#/', text: '‹ Kaikki pelit' }));
      return;
    }
    document.title = game.title + ' · AI-pelit';
    var v = latest(game);
    // Every version's note as the game's history; only the newest is kept and played (#346).
    var versions = el('ol', { class: 'versions', reversed: '' });
    game.versions.slice().reverse().forEach(function (ver) {
      versions.appendChild(el('li', { class: 'version', 'data-n': String(ver.n) }, [
        el('div', {}, [
          el('strong', { text: 'v' + ver.n }),
          el('span', { class: 'muted', text: ' · ' + fiDate(ver.date) }),
          el('p', { text: ver.note }),
        ]),
        ver === v ? el('a', { class: 'button secondary', href: playUrl(game.slug, ver.n), text: 'Pelaa' }) : null,
      ].filter(Boolean)));
    });
    view.replaceChildren.apply(view, [
      el('a', { class: 'back', href: '#/', text: '‹ Kaikki pelit' }),
      el('div', { class: 'game-head' }, [
        thumb(game, 'thumb big', 120, 160),
        el('div', {}, [el('h1', { text: game.title }), el('p', { text: game.description }), metaLine(game)]),
      ]),
      el('a', { class: 'button big', href: playUrl(game.slug, v.n), text: 'Pelaa uusinta (v' + v.n + ')' }),
      scoreSection(game.slug),
      feedbackSection(game),
      el('h2', { text: 'Versiohistoria' }),
      versions,
    ].filter(Boolean));
    loadPlaying();
  }

  function render() {
    if (!catalog) return;
    var m = location.hash.match(/^#\/([a-z0-9-]+)/);
    // An old address of a shelf group or a category (#/yleisurheilu, #523) is the shelf with
    // that button on, in the old page's place.
    if (m && isCategory(m[1]) && !gameOf(m[1])) {
      find = { q: '', cat: m[1] };
      keepFind();
      history.replaceState(history.state, '', '#/');
      m = null;
    }
    // The friends page reads every 10 s. The front page of a phone with a nickname but no friends
    // yet reads every 30 s, so the first request shows there too; with friends, the "now playing"
    // message every 30 s brings requests already.
    if (friends) {
      // Requests show on the front page and the friends page themselves; on a game's page they
      // come as kaverit.js's banner.
      friends.quietRequests = !m || m[1] === 'kaverit';
      friends.quietInvites = !m || m[1] === 'kaverit';
      friends.drawBanner();
      if (m && m[1] === 'kaverit') friends.watch(true);
      else friends.watch(!m && !!friends.name(), 30e3, true);
    }
    if (m && m[1] === 'kaverit' && friends) return renderFriends();
    pushNow = null; pushError = ''; // the friends page reads the notification switch again
    if (m) renderGame(m[1]); else renderShelf();
  }

  // Friends (#324), from public/kaverit.js: the friends page (#/kaverit), and on the shelf's
  // front page the friends playing right now. Friends are made in a game room; this page shows
  // them, the requests waiting for this phone, and removes a friend.
  var friends = window.AiPelitKaverit || null;
  function gameOf(slug) { return catalog.games.filter(function (g) { return g.slug === slug; })[0]; }
  function friendRow(f, extra) {
    var game = f.now && f.game && gameOf(f.game);
    return el('li', { class: 'friend' + (f.now && f.game ? ' in-game' : ''), 'data-pid': f.pid }, [
      game ? thumb(game, 'thumb small', 36, 48) : el('span', { class: 'friend-face', text: '👤' }),
      el('div', {}, [el('h3', { text: f.name }), el('p', { class: 'muted meta', text: friends.doing(f) })]),
      extra,
    ]);
  }
  function requestRow(q) {
    var yes = el('button', { type: 'button', class: 'button', text: 'Hyväksy' });
    var no = el('button', { type: 'button', class: 'secondary', text: 'Ei' });
    yes.addEventListener('click', function () { yes.disabled = no.disabled = true; friends.answer(q.pid, true).then(answered); });
    no.addEventListener('click', function () { yes.disabled = no.disabled = true; friends.answer(q.pid, false).then(answered); });
    return el('li', { class: 'friend ask', 'data-pid': q.pid }, [
      el('span', { class: 'friend-face', text: '👋' }),
      el('div', {}, [el('h3', { text: q.name }), el('p', { class: 'muted meta', text: 'haluaa kaveriksi' })]),
      el('div', { class: 'friend-buttons' }, [no, yes]),
    ]);
  }
  function inviteRow(inv) {
    var yes = el('button', { type: 'button', class: 'button', text: 'Liity' });
    var no = el('button', { type: 'button', class: 'secondary', text: 'Ei' });
    yes.addEventListener('click', function () {
      yes.disabled = no.disabled = true;
      friends.acceptInvite(inv).then(function (r) {
        if (!r.ok) { friendsNote = 'Kutsuun liittyminen ei onnistunut.'; friends.refresh(); }
      });
    });
    no.addEventListener('click', function () {
      yes.disabled = no.disabled = true;
      friends.declineInvite(inv).then(function (r) {
        if (!r.ok) friendsNote = 'Kutsun hylkääminen ei onnistunut.';
      });
    });
    return el('li', { class: 'friend ask', 'data-invite': String(inv.id) }, [
      el('span', { class: 'friend-face', text: '📨' }),
      el('div', {}, [
        el('h3', { text: inv.name + ' kutsuu' }),
        el('p', { class: 'muted meta', text: friends.title(inv.game) }),
      ]),
      el('div', { class: 'friend-buttons' }, [no, yes]),
    ]);
  }
  // The front page: pending room invites and friend requests, no playing-status duplicates.
  function drawPlaying() {
    var box = view.querySelector('.friends-playing');
    if (!box || !friends) return;
    var st = friends.state, invites = st ? st.invites : [], asks = st ? st.requests : [];
    box.hidden = !invites.length && !asks.length;
    box.replaceChildren.apply(box, [
      invites.length ? el('h2', { text: 'Kutsut' }) : null,
      invites.length ? el('ul', { class: 'friends' }, invites.map(inviteRow)) : null,
      asks.length ? el('h2', { text: 'Kaveripyynnöt' }) : null,
      asks.length ? el('ul', { class: 'friends' }, asks.map(requestRow)) : null,
    ].filter(Boolean));
  }
  var friendsNote = '', nameError = '';
  // The nickname form (#431): while a finger or mouse is down on it, a redraw (a friends-list answer) waits
  // until the release, so the tap's "Tallenna" button is not swapped for a new one between press
  // and release (the click would then go nowhere). A redraw while a save is under way keeps the
  // form, with what was typed and its button disabled, until the server has answered.
  var namePress = false, nameRedraw = false, nameSaving = false;
  function nameRelease() {
    if (!namePress) return;
    // After the click: pointerup, mouseup and click come in one go, so wait one turn.
    setTimeout(function () {
      namePress = false;
      if (nameRedraw && location.hash === '#/kaverit') { nameRedraw = false; renderFriends(); }
      nameRedraw = false;
    });
  }
  window.addEventListener('pointerup', nameRelease, true);
  window.addEventListener('pointercancel', nameRelease, true);
  // Invites as phone notifications (#367): the switch, its state read once per visit to the page.
  var pushNow = null, pushError = '', pushBusy = false;
  // An answer about the switch redraws only its own row (#443): redrawing the whole page swapped the
  // nickname form under a finger about to tap "Tallenna", and took the focus from a nickname being typed.
  function drawPushRow() {
    var row = location.hash === '#/kaverit' && view.querySelector('.push-row');
    if (row) row.replaceWith(pushRow());
  }
  function pushRow() {
    if (pushNow === null) {
      pushNow = 'wait';
      friends.push.state().then(function (st) { pushNow = st; drawPushRow(); });
    }
    var on = pushNow === 'on', can = pushNow === 'on' || pushNow === 'off';
    var sw = el('button', { type: 'button', role: 'switch', class: 'push-switch' + (on ? ' on' : ''), 'aria-checked': on ? 'true' : 'false',
      'aria-label': 'Ilmoitukset kutsuista', text: on ? 'Päällä' : 'Pois' });
    sw.disabled = pushBusy || !can;
    sw.addEventListener('click', function () {
      pushBusy = true; pushError = '';
      drawPushRow();
      friends.push.set(!on).then(function (r) {
        pushBusy = false; pushNow = r.state; pushError = r.error;
        drawPushRow();
      });
    });
    var problem = pushError || friends.push.note(pushNow);
    var note = problem ||
      (on ? 'Puhelin ilmoittaa, kun kaveri kutsuu sinut pelaamaan, vaikka pelit olisivat kiinni.' : 'Saat ilmoituksen, kun kaveri kutsuu sinut pelaamaan, vaikka pelit olisivat kiinni.');
    return el('div', { class: 'push-row' }, [
      el('span', { class: 'friend-face', text: '🔔' }),
      el('div', {}, [el('h3', { text: 'Ilmoitukset kutsuista' }), el('p', { class: 'muted meta push-note' + (problem ? ' warn' : ''), role: 'status', text: note })]),
      sw,
    ]);
  }
  function renderFriends() {
    // Every redraw waits while the nickname form is pressed (see namePress).
    if (namePress) { nameRedraw = true; return; }
    document.title = 'Kaverit · AI-pelit';
    var st = friends.state, parts = [
      el('a', { class: 'back', href: '#/', text: '‹ Kaikki pelit' }),
      el('h1', { text: '👫 Kaverit' }),
    ];
    // The nickname field while there is none, or the kept one is taken or rejected; it stays
    // until the server takes a name.
    var problem = friends.nameNote();
    // A save under way keeps it too: the name is kept on the phone before the server answers.
    if (!friends.name() || problem || nameError || nameSaving) {
      var input = el('input', { class: 'friends-name', maxlength: '16', placeholder: 'Nimimerkki', 'aria-label': 'Nimimerkki' });
      // A redraw (the friends list refreshing) keeps what was typed: a tap on "Tallenna" just as
      // the page is drawn again would otherwise save nothing (a flaky CI run on #389).
      var typed = view.querySelector('.friends-name');
      if (typed) input.value = typed.value;
      var save = el('button', { type: 'button', class: 'button', text: 'Tallenna' });
      save.disabled = nameSaving;
      save.addEventListener('click', function () {
        var v = input.value.trim();
        if (!v || nameSaving) return;
        nameSaving = save.disabled = true;
        function done() { nameSaving = false; renderFriends(); }
        friends.setName(v).then(function (r) {
          nameError = friends.nameError(r, v);
          return friends.refresh();
        }).then(done, done);
      });
      var form = el('div', { class: 'friends-form' }, [input, save]);
      form.addEventListener('pointerdown', function () { namePress = true; });
      parts.push(el('p', { class: 'muted', text: problem || 'Valitse nimimerkki, niin kaverit tunnistavat sinut.' }), form);
      if (nameError) parts.push(el('p', { class: 'friends-note friends-name-error', role: 'status', text: nameError }));
    }
    parts.push(el('p', { class: 'muted', text: 'Kaveriksi pääsee pelihuoneessa: napauta ➕ Kaveriksi toisen pelaajan nimen vieressä, ja hän hyväksyy. Kaverit näkevät, mitä pelaat, ja voivat kutsua sinut huoneeseensa.' }));
    if (friendsNote) parts.push(el('p', { class: 'friends-note', role: 'status', text: friendsNote }));
    if (!st) {
      parts.push(el('p', { class: 'muted friends-wait', text: 'Haetaan kavereita…' }));
    } else {
      if (st.invites.length) {
        parts.push(el('h2', { text: 'Kutsut' }), el('ul', { class: 'friends' }, st.invites.map(inviteRow)));
      }
      if (st.requests.length) {
        parts.push(el('h2', { text: 'Kaveripyynnöt' }), el('ul', { class: 'friends' }, st.requests.map(requestRow)));
      }
      parts.push(el('h2', { text: st.friends.length ? 'Kaverisi (' + st.friends.length + ')' : 'Kaverisi' }));
      if (!st.friends.length) parts.push(el('p', { class: 'muted friends-none', text: 'Ei vielä kavereita.' }));
      else parts.push(el('ul', { class: 'friends' }, st.friends.map(function (f) {
        var x = el('button', { type: 'button', class: 'secondary friend-remove', 'aria-label': 'Poista ' + f.name + ' kavereista', text: '✕' });
        x.addEventListener('click', function () {
          if (!window.confirm('Poistetaanko ' + f.name + ' kavereista?')) return;
          x.disabled = true;
          friends.remove(f.pid).then(answered);
        });
        return friendRow(f, x);
      })));
      parts.push(pushRow());
    }
    view.replaceChildren.apply(view, parts);
  }
  function answered(r) {
    friendsNote = friends.friendError(r);
    if (location.hash === '#/kaverit') renderFriends(); else drawPlaying();
  }
  if (friends) {
    friends.quietRequests = true; // until render() knows the page
    friends.on(function () {
      if (!catalog) return;
      if (location.hash === '#/kaverit') {
        // Not while a nickname is being typed: drawing the page again would drop it.
        if (!document.activeElement || !document.activeElement.classList.contains('friends-name')) renderFriends();
      } else drawPlaying();
    });
    // Only a phone with a nickname can have friends or requests: no request for the others.
    if (friends.name()) friends.refresh();
  }

  // Network first, every time the shelf is opened or comes back on screen, so a new
  // game shows without reinstalling. The service worker answers from its cache offline.
  var catalogReady = null;
  function loadCatalog() {
    return fetch('catalog.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        var changed = JSON.stringify(data) !== JSON.stringify(catalog);
        catalog = data;
        setStatus('');
        if (changed) render();
      })
      .catch(function () {
        if (!catalog) view.replaceChildren(el('p', { text: 'Pelilistaa ei saatu. Tarkista verkko ja yritä uudelleen.' }));
        else setStatus('Ei verkkoa');
      });
  }

  window.addEventListener('hashchange', function () { render(); window.scrollTo(0, 0); });

  // The phone's back always goes up (#68): game → its page → the shelf → out of the app. Going
  // down adds one entry marked { up: true } over its parent; going up steps back to that parent,
  // or, with no parent below (opened from a link), takes this entry's place instead of adding one.
  function goDown(hash) {
    history.pushState({ up: true }, '', hash);
    render();
    window.scrollTo(0, 0);
  }
  // The whole page, so the header's "AI-pelit" link goes up the same way.
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    var href = a.getAttribute('href');
    var game = href.match(/^games\/([a-z0-9-]+)\/v\d+\/(\?huone=[A-Z]{4})?$/);
    if (href === '#/' || a.hasAttribute('data-up')) {
      // Up: back to the page below when this one was opened from it, else in this page's place.
      e.preventDefault();
      if (history.state && history.state.up) history.back();
      else location.replace(href);
    } else if (/^#\/[a-z0-9-]+$/.test(href)) {
      e.preventDefault();
      goDown(href);
    } else if (game) {
      e.preventDefault();
      var url = new URL(href, location.href);
      // A game opened from the shelf gets its own page between them, so back
      // from it goes there.
      if (location.hash !== '#/' + game[1]) goDown('#/' + game[1]);
      // back.js reads this and steps back here from the chip instead of opening the page anew.
      try { sessionStorage.setItem('ai-pelit:_ylos', url.pathname); } catch (err) {}
      location.assign(url.href);
    }
  });
  // A room code typed in game A that belongs to game B (rooms.js) steps back here to A's page and
  // leaves this note: A's page becomes B's, and B opens over it, so back from B goes to B's page.
  // Every game's page is right over the shelf (#523: no group pages any more).
  function openFromRoom() {
    var to = null;
    try {
      to = JSON.parse(sessionStorage.getItem('ai-pelit:_avaa'));
      sessionStorage.removeItem('ai-pelit:_avaa');
    } catch (err) {}
    if (!to || to.from !== location.hash || !/^#\/[a-z0-9-]+$/.test(to.page)) return;
    var url = new URL(to.game, location.href);
    if (url.origin !== location.origin) return;
    // The page draws from the catalog, which may still be on its way.
    (catalogReady || (catalogReady = loadCatalog())).then(function () {
      if (!catalog) return;
      history.replaceState({ up: true }, '', to.page);
      render();
      try { sessionStorage.setItem('ai-pelit:_ylos', url.pathname); } catch (err) {}
      location.assign(url.href);
    });
  }
  window.addEventListener('pageshow', function (e) { if (e.persisted) { openFromRoom(); render(); } });
  // Only once the page has loaded: a page still loading would open the game in place of B's page.
  if (document.readyState === 'complete') openFromRoom();
  else window.addEventListener('load', function () { setTimeout(openFromRoom); });

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState !== 'visible') return;
    loadCatalog();
    // The open rooms change by the minute: read them again on coming back to the shelf.
    var rooms = view.querySelector('.open-rooms');
    if (rooms) showRooms(rooms);
    loadPlaying();
    if (navigator.serviceWorker) navigator.serviceWorker.getRegistration().then(function (r) { if (r) r.update(); });
  });

  // Ask the browser to keep this site's storage (games' saves) even when space runs low.
  if (navigator.storage && navigator.storage.persist) navigator.storage.persist();

  if ('serviceWorker' in navigator) {
    var hadController = !!navigator.serviceWorker.controller;
    // A new worker takes over at once; only the shelf reloads for it. A game page never
    // listens for this, so a game in progress is never reloaded.
    navigator.serviceWorker.addEventListener('controllerchange', function () {
      if (hadController) location.reload();
      hadController = true;
    });
    navigator.serviceWorker.register('sw.js').catch(function () {});
  }

  if (!catalogReady) catalogReady = loadCatalog();
})();
