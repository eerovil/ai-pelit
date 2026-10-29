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

  // Text a person pastes into AgentDeck as a new Work on eerovil/ai-pelit.
  function copyBox(label, text) {
    var area = el('textarea', { readonly: '', rows: '3', 'aria-label': label });
    area.value = text;
    var button = el('button', { type: 'button', class: 'secondary', text: 'Kopioi' });
    button.addEventListener('click', function () {
      area.select();
      var done = function () { button.textContent = 'Kopioitu'; };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () { document.execCommand('copy'); done(); });
      else { document.execCommand('copy'); done(); }
    });
    return el('section', { class: 'copy' }, [
      el('h2', { text: label }),
      el('p', { class: 'muted', text: 'Uudet pelit ja versiot tehdään AgentDeckissä: tee uusi Work repoon eerovil/ai-pelit ja liitä tämä teksti sen alkuun.' }),
      area,
      button,
    ]);
  }

  function renderShelf() {
    document.title = 'AI-pelit';
    var list = el('ul', { class: 'cards' });
    catalog.games.forEach(function (game) {
      var v = latest(game);
      list.appendChild(el('li', { class: 'card', 'data-slug': game.slug }, [
        el('a', { class: 'card-main', href: '#/' + game.slug }, [
          el('h2', { text: game.title }),
          el('p', { text: game.description }),
          el('p', { class: 'muted', text: 'v' + v.n + ' · ' + fiDate(v.date) + (game.versions.length > 1 ? ' · ' + game.versions.length + ' versiota' : '') }),
        ]),
        el('a', { class: 'button', href: playUrl(game.slug, v.n), text: 'Pelaa' }),
      ]));
    });
    var children = [catalog.games.length ? list : el('p', { class: 'muted', text: 'Ei vielä pelejä.' })];
    children.push(copyBox('Uusi peli', 'Uusi peli: '));
    view.replaceChildren.apply(view, children);
    showWaitingNames();
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
    view.replaceChildren(
      el('a', { class: 'back', href: '#/', text: '‹ Kaikki pelit' }),
      el('h1', { text: game.title }),
      el('p', { text: game.description }),
      el('a', { class: 'button big', href: playUrl(game.slug, v.n), text: 'Pelaa uusinta (v' + v.n + ')' }),
      el('h2', { text: 'Versiot' }),
      versions,
      copyBox('Tee uusi versio', game.title + ' v' + (v.n + 1) + ' (' + game.slug + '): ')
    );
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
