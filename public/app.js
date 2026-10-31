// The shelf: lists every game from catalog.json and every version of one game.
// Routes are the hash: "" or "#/" is the shelf, "#/<slug>" is one game or one group of games.
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

  // Version, how many versions and how many plays, under the game's name.
  function metaLine(game) {
    var v = latest(game);
    return el('p', { class: 'muted meta' }, [
      document.createTextNode('v' + v.n + (game.versions.length > 1 ? ' · ' + game.versions.length + ' versiota' : '')),
      el('span', { class: 'plays', text: playsText(game.slug) }),
    ]);
  }

  function gameCard(game) {
    var v = latest(game);
    return el('li', { class: 'card', 'data-slug': game.slug }, [
      el('a', { class: 'card-main', href: '#/' + game.slug }, [
        thumb(game, 'thumb', 72, 96),
        el('div', {}, [
          el('h2', { text: game.title }),
          el('p', { class: 'desc', text: game.description }),
          metaLine(game),
          el('p', { class: 'top-score', 'data-top': game.slug, text: topText(game.slug) }),
        ]),
      ]),
      el('a', { class: 'button play', href: playUrl(game.slug, v.n), 'aria-label': 'Pelaa ' + game.title, text: '▶' }),
    ]);
  }

  // Shelf groups (#153): one card on the shelf, where its newest game would be, opens a page of
  // its games. The build lists only groups that have games (scripts/build.py GROUPS).
  function findGroup(slug) {
    return (catalog.groups || []).filter(function (g) { return g.slug === slug; })[0];
  }

  function members(slug) {
    return catalog.games.filter(function (g) { return g.group === slug; });
  }

  function groupCard(group) {
    var games = members(group.slug);
    return el('li', { class: 'card group', 'data-slug': group.slug }, [
      el('a', { class: 'card-main', href: '#/' + group.slug }, [
        thumb(games[0], 'thumb stack', 72, 96),
        el('div', {}, [
          el('h2', { text: group.title }),
          el('p', { class: 'desc', text: games.map(function (g) { return g.title; }).join(', ') }),
          el('p', { class: 'muted meta' }, [
            document.createTextNode(games.length + ' peliä'),
            el('span', { class: 'plays', text: playsText(group.slug) }),
          ]),
        ]),
      ]),
      el('a', { class: 'button play open', href: '#/' + group.slug, 'aria-label': 'Avaa ' + group.title, text: '›' }),
    ]);
  }

  function renderShelf() {
    document.title = 'AI-pelit';
    var list = el('ul', { class: 'cards' });
    var shown = {};
    catalog.games.forEach(function (game) {
      var group = game.group && findGroup(game.group);
      if (!group) { list.appendChild(gameCard(game)); return; }
      if (shown[group.slug]) return;
      shown[group.slug] = true;
      list.appendChild(groupCard(group));
    });
    view.replaceChildren(catalog.games.length ? list : el('p', { class: 'muted', text: 'Ei vielä pelejä.' }));
    showWaitingNames();
    loadPlays();
    loadTops();
  }

  function renderGroup(group) {
    document.title = group.title + ' · AI-pelit';
    view.replaceChildren(
      el('a', { class: 'back', href: '#/', text: '‹ Kaikki pelit' }),
      el('h1', { text: group.title }),
      el('p', { class: 'group-desc', text: group.description }),
      el('ul', { class: 'cards' }, members(group.slug).map(gameCard))
    );
    loadPlays();
    loadTops();
  }

  // High scores outside the games (#25): each card shows its game's no. 1, all from one request,
  // kept on the phone like the play counts. public/scores.js knows how each game's score reads.
  var TOPS_KEY = 'ai-pelit:_tulokset:ykkoset';
  var tops = {};
  try { tops = JSON.parse(localStorage.getItem(TOPS_KEY)) || {}; } catch (e) {}
  var scores = window.AiPelitScores;

  function topText(slug) {
    var t = tops[slug];
    if (!t || !scores) return '';
    var g = scores.games[slug];
    // A game with named lists (Tikanheitto) shows its first list's no. 1 with the list's name.
    if (g && g.lists) {
      var named = g.lists.filter(function (l) { return l[0] === t.board; })[0];
      return named ? '🏆 ' + named[1] + ': ' + t.name + ' · ' + scores.scoreText(slug, t.score) : '';
    }
    // A no. 1 kept from a list the shelf no longer shows (Puhelinkoppi's withdrawn streak list,
    // #9) is not shown as this one's.
    if (!(g && g.boards) && t.board && t.board !== 'main') return '';
    return '🏆 ' + (g && g.boards ? 'Taso ' + t.board.slice(5) + ': ' : '') + t.name + ' · ' + scores.scoreText(slug, t.score);
  }

  function loadTops() {
    if (!scores) return;
    scores.top().then(function (b) {
      tops = b.games || {};
      try { localStorage.setItem(TOPS_KEY, JSON.stringify(tops)); } catch (e) {}
      Array.prototype.forEach.call(view.querySelectorAll('.top-score[data-top]'), function (p) {
        p.textContent = topText(p.getAttribute('data-top'));
      });
    }).catch(function () {});
  }

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
      scores.list(slug, lists ? listId : picker ? 'taso-' + course : 'main').then(function (b) {
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
      var versions = el('select', { class: 'feedback-version', 'aria-label': 'Versio' });
      game.versions.slice().reverse().forEach(function (ver, i) {
        versions.appendChild(el('option', { value: String(ver.n), text: 'v' + ver.n + (i ? '' : ' (uusin)') }));
      });
      var text = el('textarea', { class: 'feedback-text', rows: '4', maxlength: '1000', placeholder: 'Mitä korjaisit tai lisäisit?', 'aria-label': 'Palaute' });
      text.value = draft;
      text.addEventListener('input', function () { keep(text.value); });
      var send = el('button', { type: 'button', class: 'button', text: 'Lähetä' });
      var note = el('p', { class: 'muted feedback-note', role: 'status' });
      send.addEventListener('click', function () {
        if (send.disabled) return; // a second tap while the first is on its way sends nothing
        if (!text.value.trim()) { note.textContent = 'Kirjoita ensin palaute.'; return; }
        send.disabled = true;
        note.textContent = 'Lähetetään…';
        fetch('api/feedback', {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ player: scores.id(), game: game.slug, version: Number(versions.value), text: text.value }),
        }).then(function (r) {
          send.disabled = false;
          if (r.ok) { text.value = ''; keep(''); note.textContent = 'Kiitos, ' + name + '! Palaute meni perille.'; return; }
          if (r.status === 403) { keep(text.value); show(); return; }
          note.textContent = r.status === 429 ? 'Olet antanut tänään jo paljon palautetta. Jatka huomenna.' : 'Palautetta ei saatu lähetettyä. Yritä uudelleen.';
        }).catch(function () {
          send.disabled = false;
          note.textContent = 'Ei verkkoyhteyttä. Yritä uudelleen, kun verkko toimii.';
        });
      });
      box.replaceChildren(
        el('p', { class: 'muted', text: 'Nimimerkillä ' + name + '. Vain ylläpitäjä näkee palautteen.' }),
        el('div', { class: 'feedback-row' }, [el('span', { text: 'Versio' }), versions]),
        text,
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
    // A group's card counts all its games together.
    var n = catalog && findGroup(slug)
      ? members(slug).reduce(function (sum, g) { return sum + (plays[g.slug] || 0); }, 0)
      : plays[slug];
    if (!n) return '';
    return ' · pelattu ' + n + (n === 1 ? ' kerran' : ' kertaa');
  }

  function loadPlays() {
    fetch('api/plays', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (b) {
        if (!b || !b.games) return;
        plays = b.games;
        try { localStorage.setItem(PLAYS_KEY, JSON.stringify(plays)); } catch (e) {}
        Array.prototype.forEach.call(view.querySelectorAll('.card[data-slug] .plays'), function (span) {
          span.textContent = playsText(span.closest('.card').getAttribute('data-slug'));
        });
      })
      .catch(function () {});
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
    // A game in a group goes up to the group's page, the others to the shelf.
    var group = game.group && findGroup(game.group);
    var versions = el('ol', { class: 'versions', reversed: '' });
    game.versions.slice().reverse().forEach(function (ver) {
      versions.appendChild(el('li', { class: 'version', 'data-n': String(ver.n) }, [
        el('div', {}, [
          el('strong', { text: 'v' + ver.n }),
          el('span', { class: 'muted', text: ' · ' + fiDate(ver.date) }),
          el('p', { text: ver.note }),
        ]),
        el('a', { class: 'button secondary', href: playUrl(game.slug, ver.n), text: 'Pelaa' }),
      ]));
    });
    view.replaceChildren.apply(view, [
      group
        ? el('a', { class: 'back', href: '#/' + group.slug, 'data-up': '', text: '‹ ' + group.title })
        : el('a', { class: 'back', href: '#/', text: '‹ Kaikki pelit' }),
      el('div', { class: 'game-head' }, [
        thumb(game, 'thumb big', 120, 160),
        el('div', {}, [el('h1', { text: game.title }), el('p', { text: game.description }), metaLine(game)]),
      ]),
      el('a', { class: 'button big', href: playUrl(game.slug, v.n), text: 'Pelaa uusinta (v' + v.n + ')' }),
      scoreSection(game.slug),
      feedbackSection(game),
      el('h2', { text: 'Versiot' }),
      versions,
    ].filter(Boolean));
  }

  function render() {
    if (!catalog) return;
    var m = location.hash.match(/^#\/([a-z0-9-]+)/);
    var group = m && findGroup(m[1]);
    if (group) renderGroup(group); else if (m) renderGame(m[1]); else renderShelf();
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
    var game = href.match(/^games\/([a-z0-9-]+)\/v\d+\/$/);
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
      // A game opened from the shelf or a group's page gets its own page between them, so back
      // from it goes there.
      if (location.hash !== '#/' + game[1]) goDown('#/' + game[1]);
      // back.js reads this and steps back here from the chip instead of opening the page anew.
      try { sessionStorage.setItem('ai-pelit:_ylos', url.pathname); } catch (err) {}
      location.assign(url.href);
    }
  });
  // A room code typed in game A that belongs to game B (rooms.js) steps back here to A's page and
  // leaves this note: A's page becomes B's, and B opens over it, so back from B goes to B's page.
  // When B's page belongs under another parent than A's (a shelf group, #153), the history below
  // it is made B's own: shelf → B's group → B's page, or shelf → B's page.
  function parentOf(hash) {
    var game = catalog.games.filter(function (g) { return '#/' + g.slug === hash; })[0];
    return game && game.group && findGroup(game.group) ? '#/' + game.group : '#/';
  }

  function openFromRoom() {
    var to = null;
    try {
      to = JSON.parse(sessionStorage.getItem('ai-pelit:_avaa'));
      sessionStorage.removeItem('ai-pelit:_avaa');
    } catch (err) {}
    if (!to || to.from !== location.hash || !/^#\/[a-z0-9-]+$/.test(to.page)) return;
    var url = new URL(to.game, location.href);
    if (url.origin !== location.origin) return;
    function open() {
      render();
      try { sessionStorage.setItem('ai-pelit:_ylos', url.pathname); } catch (err) {}
      location.assign(url.href);
    }
    // Over the page below, which is the shelf: B's group's page first, when it has one.
    function onShelf(dest) {
      if (dest === '#/') history.replaceState({ up: true }, '', to.page);
      else { history.replaceState({ up: true }, '', dest); history.pushState({ up: true }, '', to.page); }
      open();
    }
    // The groups come from the catalog, which may still be on its way.
    (catalogReady || (catalogReady = loadCatalog())).then(function () {
      if (!catalog) return;
      var from = parentOf(to.from), dest = parentOf(to.page);
      if (from === dest) {
        history.replaceState({ up: true }, '', to.page);
        open();
      } else if (from === '#/') {
        onShelf(dest);
      } else if (history.state && history.state.up) {
        // A's group page is just below: step back to it, and build B's way up over the shelf.
        window.addEventListener('popstate', function once() {
          window.removeEventListener('popstate', once);
          onShelf(dest);
        });
        history.back();
      } else {
        // Nothing of ours below: B's page takes A's place, and its back link goes up by address.
        history.replaceState({ up: false }, '', to.page);
        open();
      }
    });
  }
  window.addEventListener('pageshow', function (e) { if (e.persisted) { openFromRoom(); render(); } });
  // Only once the page has loaded: a page still loading would open the game in place of B's page.
  if (document.readyState === 'complete') openFromRoom();
  else window.addEventListener('load', function () { setTimeout(openFromRoom); });

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState !== 'visible') return;
    loadCatalog();
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
