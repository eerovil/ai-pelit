// The shelf: lists every game from catalog.json and every version of one game.
// Routes are the hash: "" or "#/" is the shelf, "#/<slug>" is one game.
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

  function renderShelf() {
    document.title = 'AI-pelit';
    var list = el('ul', { class: 'cards' });
    catalog.games.forEach(function (game) {
      var v = latest(game);
      list.appendChild(el('li', { class: 'card', 'data-slug': game.slug }, [
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
      ]));
    });
    view.replaceChildren(catalog.games.length ? list : el('p', { class: 'muted', text: 'Ei vielä pelejä.' }));
    showWaitingNames();
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

  // A game's page: its top 10, and the player's own place under it. Hiihto has a list per course.
  function scoreSection(slug) {
    if (!scores || !scores.games[slug]) return null;
    var box = el('div', { class: 'scores' });
    var picker = null;
    var course = 1;
    if (scores.games[slug].boards) {
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
      scores.list(slug, picker ? 'taso-' + course : scores.games[slug].list || 'main').then(function (b) {
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

  // Play counts (#26): how many times each game has been opened, all versions together, on
  // every phone. The last answer is kept on the phone, so the shelf shows it at once and offline.
  var PLAYS_KEY = 'ai-pelit:_pelikerrat:yhteensa';
  var plays = {};
  try { plays = JSON.parse(localStorage.getItem(PLAYS_KEY)) || {}; } catch (e) {}

  function playsText(slug) {
    var n = plays[slug];
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
      el('a', { class: 'back', href: '#/', text: '‹ Kaikki pelit' }),
      el('div', { class: 'game-head' }, [
        thumb(game, 'thumb big', 120, 160),
        el('div', {}, [el('h1', { text: game.title }), el('p', { text: game.description }), metaLine(game)]),
      ]),
      el('a', { class: 'button big', href: playUrl(game.slug, v.n), text: 'Pelaa uusinta (v' + v.n + ')' }),
      scoreSection(game.slug),
      el('h2', { text: 'Versiot' }),
      versions,
    ].filter(Boolean));
  }

  function render() {
    if (!catalog) return;
    var m = location.hash.match(/^#\/([a-z0-9-]+)/);
    if (m) renderGame(m[1]); else renderShelf();
  }

  // Network first, every time the shelf is opened or comes back on screen, so a new
  // game shows without reinstalling. The service worker answers from its cache offline.
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
  view.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    var href = a.getAttribute('href');
    var game = href.match(/^games\/([a-z0-9-]+)\/v\d+\/$/);
    if (href === '#/') {
      e.preventDefault();
      if (history.state && history.state.up) history.back();
      else location.replace('#/');
    } else if (/^#\/[a-z0-9-]+$/.test(href)) {
      e.preventDefault();
      goDown(href);
    } else if (game) {
      e.preventDefault();
      var url = new URL(href, location.href);
      // A game opened from the shelf gets its page between them, so back from it goes there.
      if (!/^#\/[a-z0-9-]/.test(location.hash)) goDown('#/' + game[1]);
      // back.js reads this and steps back here from the chip instead of opening the page anew.
      try { sessionStorage.setItem('ai-pelit:_ylos', url.pathname); } catch (err) {}
      location.assign(url.href);
    }
  });
  // A room code typed in game A that belongs to game B (rooms.js) steps back here to A's page and
  // leaves this note: A's page becomes B's, and B opens over it, so back from B goes to B's page.
  function openFromRoom() {
    var to = null;
    try {
      to = JSON.parse(sessionStorage.getItem('ai-pelit:_avaa'));
      sessionStorage.removeItem('ai-pelit:_avaa');
    } catch (err) {}
    if (!to || to.from !== location.hash || !/^#\/[a-z0-9-]+$/.test(to.page)) return;
    var url = new URL(to.game, location.href);
    if (url.origin !== location.origin) return;
    history.replaceState({ up: true }, '', to.page);
    render();
    try { sessionStorage.setItem('ai-pelit:_ylos', url.pathname); } catch (err) {}
    location.assign(url.href);
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

  loadCatalog();
})();
