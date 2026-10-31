// The online parts of AI-pelit: high-score lists and the nicknames on them (#25).
//
// Every game still plays fully offline; these routes are an extra that public/scores.js talks
// to when it can. `env.DB` is the D1 database (migrations/), `env.ADMIN_KEY` the admin's secret.
//
//   POST /api/players          {id, name}                    -> {name, status}
//   GET  /api/players/<id>                                   -> {name, status}
//   POST /api/scores           {player, game, board, version, score, level?} -> {best, rank}
//   GET  /api/scores?game=&board=&player=                    -> {rows, mine}
//   GET  /api/scores/top                                     -> {games: {<slug>: {board, name, score, level, version}}}
//   GET  /api/admin/players    (X-Admin-Key)                 -> {players}
//   POST /api/admin/players    (X-Admin-Key) {id, name, status} -> {name, status}
//   POST /api/plays            {game, version}               -> {ok}
//   GET  /api/plays                                          -> {games: {<slug>: total}}
//   GET  /api/rooms/<CODE>     (WebSocket)                   -> a live game room (#27, rooms/worker.js)
//   GET  /api/rooms?game=                                    -> {rooms: [{code, v, n, max}]}, public rooms (#50)
//
// A new or changed nickname is 'pending' and shows on no list (except to its own phone) until
// the admin approves it; from then on that name is locked to that phone. Each name has one owner
// in the `names` table, whose primary key settles two phones asking at once. Scores are taken
// as sent: there is no cheat check (Eero's choice).
// Against spam: each game has a fixed set of lists, one network makes at most NEW_PER_DAY names
// a day, and while PENDING_MAX names wait for the admin no new one is taken.

// Which games keep lists, which way is better, and which lists ('boards') each has.
// A game or list not here gets a 400.
export const GAMES = {
  sormiskeitti: { order: 'high', boards: /^main$/ }, // highest ollie, cm
  voimistelu: { order: 'high', boards: /^main$/ }, // best routine total
  // Highest level reached ('main'). 'putki' (the streak list of the withdrawn v3 and v4, #9) is
  // still taken from phones that kept those versions, but no longer shown.
  puhelinkoppi: { order: 'high', boards: /^(main|putki)$/ },
  hiihto: { order: 'low', boards: /^(taso|luistelu)-[1-9][0-9]{0,2}$/, first: 'taso-1' }, // fastest time per course and style (classic 'taso-N', skating 'luistelu-N'), seconds
  piano: { order: 'high', boards: /^main$/ }, // most points in one game
  // Fastest time, seconds: 'main' is 100 m hurdles (v1-v2), the rest are v3's '<200|400>-aidat' and
  // '<100|200|400>-tasainen' (no hurdles).
  aitajuoksu: { order: 'low', boards: /^(main|(200|400)-aidat|(100|200|400)-tasainen)$/ },
  kaaosrata: { order: 'low', boards: /^main$/ }, // fastest obstacle course, seconds
  trampoliini: { order: 'high', boards: /^main$/ }, // most points in one go at a level
  orava: { order: 'high', boards: /^main$/ }, // most points in one go at a level
  skuutti: { order: 'high', boards: /^main$/ }, // most points in one minute's run
  // Most points in 10 rounds: Mökkitikka 'mokki' (v2's main mode, the shelf's), Pistekisa 'main' (v1 on).
  tikka: { order: 'high', boards: /^(main|mokki)$/, first: 'mokki' },
  keihas: { order: 'high', boards: /^main$/ }, // longest javelin throw in metres
  pituushyppy: { order: 'high', boards: /^main$/ }, // longest legal long jump in metres
};

const ID = /^[a-f0-9]{32}$/;
const NAME_MAX = 16;
export const NEW_PER_DAY = 5;
export const PENDING_MAX = 30;
const BODY_MAX = 2000;
const LIST = 10;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
  });
}

const fail = (status, error) => json({ error }, status);

async function readBody(request) {
  const text = await request.text();
  if (text.length > BODY_MAX) return null;
  try {
    const body = JSON.parse(text);
    return body && typeof body === 'object' && !Array.isArray(body) ? body : null;
  } catch (e) {
    return null;
  }
}

// Trim, squeeze inner spaces, drop control characters; 1..16 characters.
export function cleanName(name) {
  if (typeof name !== 'string') return '';
  const s = name.replace(/[\u0000-\u001f\u007f]/g, '').replace(/\s+/g, ' ').trim();
  return [...s].length <= NAME_MAX ? s : '';
}

const now = () => new Date().toISOString();

// What makes two names the same: Unicode NFKC, lower case ('ÄITI' is 'äiti').
export const nameKey = (name) => name.normalize('NFKC').toLowerCase();

// Takes `key` for `player` unless another player owns it. True when the player owns it now.
async function claim(env, key, player, locked) {
  await env.DB.prepare('INSERT INTO names (name_key, player, locked, at) VALUES (?, ?, ?, ?) ON CONFLICT (name_key) DO NOTHING')
    .bind(key, player, locked, now()).run();
  const owner = await env.DB.prepare('SELECT player FROM names WHERE name_key = ?').bind(key).first();
  return owner.player === player;
}

// The caller's network as a hash salted with the admin key: enough to count, nothing to read.
async function sourceOf(request, env) {
  const ip = request.headers.get('cf-connecting-ip') || '';
  const data = new TextEncoder().encode(`${env.ADMIN_KEY || ''}|${ip}`);
  const hash = new Uint8Array(await crypto.subtle.digest('SHA-256', data));
  return [...hash.slice(0, 12)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function setName(request, env, body) {
  const id = String(body.id || ''), name = cleanName(body.name);
  if (!ID.test(id)) return fail(400, 'bad id');
  if (!name) return fail(400, `a name is 1–${NAME_MAX} characters`);
  const key = nameKey(name);
  const owner = await env.DB.prepare('SELECT player FROM names WHERE name_key = ?').bind(key).first();
  if (owner && owner.player !== id) return fail(409, 'name taken');
  const old = await env.DB.prepare('SELECT name, status FROM players WHERE id = ?').bind(id).first();
  if (old && old.name === name) return json({ name, status: old.status });
  const waiting = await env.DB.prepare("SELECT COUNT(*) AS n FROM players WHERE status = 'pending'").first();
  if (waiting.n >= PENDING_MAX) return fail(429, 'too many names waiting');
  const source = await sourceOf(request, env), t = now();
  if (!old) {
    const day = new Date(Date.now() - 864e5).toISOString();
    const made = await env.DB.prepare('SELECT COUNT(*) AS n FROM players WHERE source = ? AND created_at > ?')
      .bind(source, day).first();
    if (made.n >= NEW_PER_DAY) return fail(429, 'too many new names from here today');
  }
  if (!(await claim(env, key, id, 0))) return fail(409, 'name taken');
  // The name it had before is free again, unless the admin approved it (locked).
  await env.DB.prepare('DELETE FROM names WHERE player = ? AND locked = 0 AND name_key != ?').bind(id, key).run();
  // Every new nickname, and every change of one, waits for the admin again.
  await env.DB.prepare(
    `INSERT INTO players (id, name, status, created_at, updated_at, source) VALUES (?, ?, 'pending', ?, ?, ?)
     ON CONFLICT (id) DO UPDATE SET name = excluded.name, status = 'pending', updated_at = excluded.updated_at`
  ).bind(id, name, t, t, source).run();
  return json({ name, status: 'pending' });
}

async function getPlayer(env, id) {
  if (!ID.test(id)) return fail(400, 'bad id');
  const p = await env.DB.prepare('SELECT name, status FROM players WHERE id = ?').bind(id).first();
  return p ? json({ name: p.name, status: p.status }) : fail(404, 'unknown player');
}

// The place of a score made at `at` on the list: 1 + how many approved players are ahead of it,
// in the list's own order (better score first, then the earlier one on a tie).
async function rankOf(env, game, board, score, at) {
  const better = GAMES[game].order === 'low' ? '<' : '>';
  const r = await env.DB.prepare(
    `SELECT COUNT(*) AS n FROM scores s JOIN players p ON p.id = s.player
     WHERE s.game = ? AND s.board = ? AND p.status = 'approved'
       AND (s.score ${better} ? OR (s.score = ? AND s.at < ?))`
  ).bind(game, board, score, score, at).first();
  return r.n + 1;
}

async function addScore(env, body) {
  const { player, game, board } = body;
  const version = Number(body.version), score = Number(body.score);
  if (!ID.test(String(player || ''))) return fail(400, 'bad player');
  if (!Object.hasOwn(GAMES, game)) return fail(400, 'no list for this game');
  if (!GAMES[game].boards.test(String(board || ''))) return fail(400, 'bad board');
  if (!Number.isInteger(version) || version < 1) return fail(400, 'bad version');
  if (!Number.isFinite(score)) return fail(400, 'bad score');
  // The level reached, shown beside the score; optional, as older versions do not send it.
  const level = body.level === undefined || body.level === null ? null : Number(body.level);
  if (level !== null && !(Number.isInteger(level) && level >= 1 && level <= 100000)) return fail(400, 'bad level');
  const known = await env.DB.prepare('SELECT 1 FROM players WHERE id = ?').bind(player).first();
  if (!known) return fail(404, 'unknown player');
  const better = GAMES[game].order === 'low' ? '<' : '>';
  // Keep the player's best score on each list, and the highest level they have reached, which
  // may rise in a round that does not beat the best score.
  const beats = `excluded.score ${better} scores.score`;
  await env.DB.prepare(
    `INSERT INTO scores (game, board, player, score, version, at, level) VALUES (?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT (game, board, player) DO UPDATE SET
       score = CASE WHEN ${beats} THEN excluded.score ELSE scores.score END,
       version = CASE WHEN ${beats} THEN excluded.version ELSE scores.version END,
       at = CASE WHEN ${beats} THEN excluded.at ELSE scores.at END,
       level = NULLIF(MAX(COALESCE(scores.level, 0), COALESCE(excluded.level, 0)), 0)`
  ).bind(game, board, player, score, version, now(), level).run();
  const best = await env.DB.prepare('SELECT score, at FROM scores WHERE game = ? AND board = ? AND player = ?')
    .bind(game, board, player).first();
  return json({ best: best.score, rank: await rankOf(env, game, board, best.score, best.at) });
}

// A row's level is the player's highest in the whole game, from any of its lists: in Hiihto,
// passing course 2 shows on the course 1 list too, with no replay.
const GAME_LEVEL = '(SELECT MAX(l.level) FROM scores l WHERE l.game = s.game AND l.player = s.player)';

// Each game's no. 1 for the shelf cards, in one request: its 'main' list, or its `first` one.
async function tops(env) {
  const games = {};
  for (const [game, g] of Object.entries(GAMES)) {
    const board = g.first || 'main';
    const r = await env.DB.prepare(
      `SELECT p.name, s.score, ${GAME_LEVEL} AS level, s.version FROM scores s JOIN players p ON p.id = s.player
       WHERE s.game = ? AND s.board = ? AND p.status = 'approved'
       ORDER BY s.score ${g.order === 'low' ? 'ASC' : 'DESC'}, s.at ASC LIMIT 1`
    ).bind(game, board).first();
    if (r) games[game] = { board, name: r.name, score: r.score, level: r.level, version: r.version };
  }
  return json({ games });
}

async function list(env, url) {
  const game = url.searchParams.get('game') || '', board = url.searchParams.get('board') || 'main';
  const player = url.searchParams.get('player') || '';
  if (!Object.hasOwn(GAMES, game)) return fail(400, 'no list for this game');
  if (!GAMES[game].boards.test(board)) return fail(400, 'bad board');
  const order = GAMES[game].order === 'low' ? 'ASC' : 'DESC';
  // Player ids are each phone's secret: never sent back, only "is this row mine".
  const { results } = await env.DB.prepare(
    `SELECT p.name, s.score, s.version, s.at, ${GAME_LEVEL} AS level, s.player = ? AS me
     FROM scores s JOIN players p ON p.id = s.player
     WHERE s.game = ? AND s.board = ? AND p.status = 'approved'
     ORDER BY s.score ${order}, s.at ASC LIMIT ${LIST}`
  ).bind(player, game, board).all();
  const rows = results.map((r, i) => ({ rank: i + 1, name: r.name, score: r.score, level: r.level, version: r.version, at: r.at, me: !!r.me }));
  let mine = null;
  if (ID.test(player)) {
    const m = await env.DB.prepare(
      `SELECT p.name, p.status, s.score, ${GAME_LEVEL} AS level, s.version, s.at FROM scores s JOIN players p ON p.id = s.player
       WHERE s.game = ? AND s.board = ? AND s.player = ?`
    ).bind(game, board, player).first();
    if (m) {
      mine = { name: m.name, status: m.status, score: m.score, level: m.level, version: m.version, at: m.at };
      if (m.status === 'approved') mine.rank = await rankOf(env, game, board, m.score, m.at);
    }
  }
  return json({ rows, mine });
}

// Play counts (#26): back.js sends one count each time a game version opens. Anonymous by
// Eero's choice: a row is game, version, UTC day and a number, nothing about the phone.
const SLUG = /^[a-z0-9][a-z0-9-]{0,39}$/;
const CATALOG_TTL = 60e3;
let catalog = null, catalogAt = 0;

// The games and versions the site has, from its own catalog.json, so a made-up game gets no
// row. Without env.ASSETS (the tests) any well-formed slug and version is taken. When the
// catalog cannot be read, the last one read is used; with none yet, null and no count is taken.
async function knownVersions(env, url) {
  if (!env.ASSETS) return 'any';
  if (!catalog || Date.now() - catalogAt > CATALOG_TTL) {
    try {
      const res = await env.ASSETS.fetch(new URL('/catalog.json', url));
      if (!res.ok) return catalog;
      const data = await res.json();
      catalog = new Map(data.games.map((g) => [g.slug, new Set(g.versions.map((v) => v.n))]));
      catalogAt = Date.now();
    } catch (e) {
      return catalog;
    }
  }
  return catalog;
}

async function addPlay(env, url, body) {
  const game = String(body.game || ''), version = Number(body.version);
  if (!SLUG.test(game)) return fail(400, 'bad game');
  if (!Number.isInteger(version) || version < 1 || version > 999) return fail(400, 'bad version');
  const known = await knownVersions(env, url);
  if (!known) return fail(503, 'no catalog');
  if (known !== 'any' && !(known.get(game) && known.get(game).has(version))) return fail(404, 'no such version');
  await env.DB.prepare(
    `INSERT INTO plays (game, version, day, n) VALUES (?, ?, ?, 1)
     ON CONFLICT (game, version, day) DO UPDATE SET n = n + 1`
  ).bind(game, version, now().slice(0, 10)).run();
  return json({ ok: true });
}

async function playTotals(env) {
  const { results } = await env.DB.prepare('SELECT game, SUM(n) AS n FROM plays GROUP BY game').all();
  const games = {};
  for (const r of results) games[r.game] = r.n;
  return json({ games });
}

function isAdmin(request, env) {
  const key = request.headers.get('x-admin-key') || '';
  return !!env.ADMIN_KEY && key === env.ADMIN_KEY;
}

async function adminPlayers(env) {
  // Waiting names first, then the newest.
  const { results } = await env.DB.prepare(
    `SELECT id, name, status, updated_at FROM players
     ORDER BY status = 'pending' DESC, updated_at DESC LIMIT 200`
  ).all();
  return json({ players: results });
}

async function adminDecide(env, body) {
  const id = String(body.id || ''), status = body.status, expected = body.name;
  if (!ID.test(id)) return fail(400, 'bad id');
  if (status !== 'approved' && status !== 'rejected') return fail(400, 'status is approved or rejected');
  // The name the admin saw: a decision on a name the phone has since changed is refused, so no
  // name is ever approved unseen.
  if (typeof expected !== 'string') return fail(400, 'name needed');
  const p = await env.DB.prepare('SELECT name FROM players WHERE id = ?').bind(id).first();
  if (!p) return fail(404, 'unknown player');
  if (p.name !== expected) return fail(409, 'name changed');
  const t = now();
  if (status === 'rejected') {
    const res = await env.DB.prepare("UPDATE players SET status = 'rejected', updated_at = ? WHERE id = ? AND name = ?")
      .bind(t, id, expected).run();
    if (!res.meta.changes) return fail(409, 'name changed');
    // Rejecting the player frees every name it held.
    await env.DB.prepare('DELETE FROM names WHERE player = ?').bind(id).run();
    return json({ name: expected, status });
  }
  // An approved name is locked to this phone for good. A rejected player's name was freed, and
  // another phone may hold it now: then it cannot be approved. The lock is taken before the
  // status changes, and undone if the phone changed name in between.
  const key = nameKey(expected);
  const before = await env.DB.prepare('SELECT player, locked FROM names WHERE name_key = ?').bind(key).first();
  if (!(await claim(env, key, id, 1))) return fail(409, 'name taken by another player');
  await env.DB.prepare('UPDATE names SET locked = 1 WHERE name_key = ? AND player = ?').bind(key, id).run();
  const res = await env.DB.prepare("UPDATE players SET status = 'approved', updated_at = ? WHERE id = ? AND name = ?")
    .bind(t, id, expected).run();
  if (!res.meta.changes) {
    if (!before) await env.DB.prepare('DELETE FROM names WHERE name_key = ? AND player = ?').bind(key, id).run();
    else if (!before.locked) await env.DB.prepare('UPDATE names SET locked = 0 WHERE name_key = ? AND player = ?').bind(key, id).run();
    return fail(409, 'name changed');
  }
  return json({ name: expected, status });
}

async function route(request, env) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, '');
  const method = request.method;
  if (path === '/api/players' && method === 'POST') {
    const body = await readBody(request);
    return body ? setName(request, env, body) : fail(400, 'bad body');
  }
  const m = path.match(/^\/api\/players\/([^/]+)$/);
  if (m && method === 'GET') return getPlayer(env, m[1]);
  if (path === '/api/scores' && method === 'GET') return list(env, url);
  if (path === '/api/scores/top' && method === 'GET') return tops(env);
  if (path === '/api/scores' && method === 'POST') {
    const body = await readBody(request);
    return body ? addScore(env, body) : fail(400, 'bad body');
  }
  if (path === '/api/plays' && method === 'GET') return playTotals(env);
  if (path === '/api/plays' && method === 'POST') {
    const body = await readBody(request);
    return body ? addPlay(env, url, body) : fail(400, 'bad body');
  }
  if (path === '/api/admin/players') {
    if (!isAdmin(request, env)) return fail(403, 'admin key needed');
    if (method === 'GET') return adminPlayers(env);
    if (method === 'POST') {
      const body = await readBody(request);
      return body ? adminDecide(env, body) : fail(400, 'bad body');
    }
  }
  return fail(404, 'no such route');
}

// A live game room: the WebSocket goes on to the room's Durable Object in the ai-pelit-rooms
// Worker, bound to the Pages project as ROOMS. One object per code, so a room's phones meet.
function room(request, env, code) {
  if (!env.ROOMS) return fail(503, 'no rooms');
  if (!/^[A-Z]{4}$/.test(code)) return fail(400, 'bad room code');
  if (request.headers.get('upgrade') !== 'websocket') return fail(426, 'websocket only');
  return env.ROOMS.get(env.ROOMS.idFromName(code)).fetch(request);
}

// The public rooms of one game (#50), from the one object that keeps the list (rooms/worker.js).
// Only this GET reaches it from outside; the rooms themselves tell it what is listed.
function publicRooms(request, env) {
  if (!env.ROOMS) return fail(503, 'no rooms');
  if (request.method !== 'GET') return fail(405, 'GET only');
  const game = new URL(request.url).searchParams.get('game') || '';
  if (!/^[a-z0-9-]{1,40}$/.test(game)) return fail(400, 'bad game');
  const q = new URLSearchParams({ game });
  return env.ROOMS.get(env.ROOMS.idFromName('lobby')).fetch(new Request(`https://rooms/lobby?${q}`));
}

export async function handle(request, env) {
  if (/^\/api\/rooms\/?$/.test(new URL(request.url).pathname)) return publicRooms(request, env);
  const rooms = new URL(request.url).pathname.match(/^\/api\/rooms\/([^/]*)$/);
  if (rooms) return room(request, env, rooms[1].toUpperCase());
  if (!env.DB) return fail(503, 'no database');
  try {
    return await route(request, env);
  } catch (e) {
    console.error(e);
    return fail(500, 'server error');
  }
}
