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
//   GET  /api/rooms                                          -> {rooms: [{code, game, v, n, max}]}, every game's (#203)
//   POST /api/feedback         {player, game, version?, text} -> {ok}, approved nicknames only (#184)
//   GET  /api/admin/feedback?new=1|issue= (X-Admin-Key)      -> {feedback}
//   POST /api/admin/feedback   (X-Admin-Key) {ids, issue}    -> {ok}, filed in a "Palautteet" issue
//   GET  /api/friends?player=                                -> {friends, requests, asked, invites} (#324)
//   POST /api/presence         {player, game?, version?}     -> the same, and "now playing" kept
//   POST /api/friends/requests {player, to}                  -> {ok, friends}, a friend request (to: a pid)
//   POST /api/friends/requests/answer {player, from, yes}    -> {ok}
//   DELETE /api/friends        {player, pid}                 -> {ok}
//   POST /api/invites          {player, to, game, version, room} -> {ok}, an invite into a room
//   POST /api/invites/<id>/answer {player}                   -> {ok}
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
  makihyppy: { order: 'high', boards: /^(main|viikko)$/, first: 'viikko' }, // most points in a ski-jumping week of four hills (v2, 'viikko'), or a meet of two jumps (v1, 'main')
  moukari: { order: 'high', boards: /^main$/ }, // longest hammer throw in metres
  kuula: { order: 'high', boards: /^main$/ }, // longest shot put in metres
  seivashyppy: { order: 'high', boards: /^main$/ }, // highest pole vault cleared in metres
  korkeushyppy: { order: 'high', boards: /^main$/ }, // highest bar cleared in a meet, metres
  ottelu: { order: 'high', boards: /^lajit-[2-7]$/, first: 'lajit-5' }, // most combined-event points, one list per number of events
  yoajo: { order: 'high', boards: /^osa-[1-9]$/, first: 'osa-1' }, // most points on one leg of the night drive ('osa-N')
  vuoristorata: { order: 'low', boards: /^taso-[1-9][0-9]{0,2}$/, first: 'taso-1' }, // fastest ride per level, seconds
  pilkki: { order: 'high', boards: /^main$/ }, // biggest catch in a five-minute ice-fishing contest, grams
};

const ID = /^[a-f0-9]{32}$/;
const NAME_MAX = 16;
export const NEW_PER_DAY = 5;
export const PENDING_MAX = 30;
const BODY_MAX = 4000; // room for 1000 characters of feedback (#184), emoji and all
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
    `INSERT INTO players (id, name, status, created_at, updated_at, source, pid) VALUES (?, ?, 'pending', ?, ?, ?, ?)
     ON CONFLICT (id) DO UPDATE SET name = excluded.name, status = 'pending', updated_at = excluded.updated_at, pid = excluded.pid`
  ).bind(id, name, t, t, source, await pidOf(id)).run();
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

// Feedback on a game (#184). Only a player whose current nickname the admin approved may write,
// so it needs no moderation of its own; at most FEEDBACK_PER_DAY a day per player. Private: no
// route shows it to players.
export const FEEDBACK_MAX = 1000;
export const FEEDBACK_PER_DAY = 10;

// Like cleanName(), but keeps line breaks (at most two in a row).
export function cleanText(text) {
  if (typeof text !== 'string') return '';
  const s = text.replace(/\r\n?/g, '\n').replace(/[\u0000-\u0009\u000b-\u001f\u007f]/g, '')
    .replace(/[ \t]+/g, ' ').replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  return [...s].length <= FEEDBACK_MAX ? s : '';
}

async function addFeedback(env, url, body) {
  const player = String(body.player || ''), game = String(body.game || ''), text = cleanText(body.text);
  const version = body.version === undefined || body.version === null ? null : Number(body.version);
  if (!ID.test(player)) return fail(400, 'bad player');
  if (!SLUG.test(game)) return fail(400, 'bad game');
  if (version !== null && (!Number.isInteger(version) || version < 1 || version > 999)) return fail(400, 'bad version');
  if (!text) return fail(400, `feedback is 1–${FEEDBACK_MAX} characters`);
  const known = await knownVersions(env, url);
  if (!known) return fail(503, 'no catalog');
  if (known !== 'any' && !(known.get(game) && (version === null || known.get(game).has(version)))) return fail(404, 'no such game');
  const p = await env.DB.prepare('SELECT name, status FROM players WHERE id = ?').bind(player).first();
  if (!p || p.status !== 'approved') return fail(403, 'approved nickname needed');
  // The count and the insert are one statement, so posts at once cannot pass the limit together.
  const day = new Date(Date.now() - 864e5).toISOString();
  const res = await env.DB.prepare(
    `INSERT INTO feedback (player, name, game, version, text, at)
     SELECT ?, ?, ?, ?, ?, ? WHERE (SELECT COUNT(*) FROM feedback WHERE player = ? AND at > ?) < ?`
  ).bind(player, p.name, game, version, text, now(), player, day, FEEDBACK_PER_DAY).run();
  if (!res.meta.changes) return fail(429, 'too much feedback today');
  return json({ ok: true });
}

// The newest first; with ?new=1 only those not yet filed in an issue, and with ?issue=<n> those
// filed in issue n (what its agent reads), both oldest first.
async function adminFeedback(env, url) {
  const fresh = url.searchParams.get('new') === '1', issue = Number(url.searchParams.get('issue'));
  const where = fresh ? 'WHERE issue IS NULL ORDER BY id ASC' : issue > 0 ? 'WHERE issue = ? ORDER BY id ASC' : 'ORDER BY id DESC';
  let q = env.DB.prepare(`SELECT id, name, game, version, text, at, issue FROM feedback ${where} LIMIT 200`);
  if (!fresh && issue > 0) q = q.bind(issue);
  const { results } = await q.all();
  return json({ feedback: results });
}

async function adminFiled(env, body) {
  const ids = body.ids, issue = Number(body.issue);
  if (!Array.isArray(ids) || !ids.length || ids.length > 200 || !ids.every((i) => Number.isInteger(i) && i > 0)) return fail(400, 'bad ids');
  if (!Number.isInteger(issue) || issue < 1) return fail(400, 'bad issue');
  for (const id of ids) {
    await env.DB.prepare('UPDATE feedback SET issue = ? WHERE id = ? AND issue IS NULL').bind(issue, id).run();
  }
  return json({ ok: true });
}

// Friends (#324). Two phones become friends in a game room: one asks, the other accepts. Each
// phone is known to the others only by its pid (pidOf), never by its secret player id. A phone
// with friends tells what it plays every 30 s (public/kaverit.js), and may invite a friend into
// the room it is in. Friends need a nickname that is not rejected; a pending one shows to them,
// as it already does to room-mates.
export const FRIENDS_MAX = 50;
export const ASKS_PER_HOUR = 30;
export const INVITES_PER_HOUR = 30;
export const PLAYING_FOR = 90e3; // a "now playing" message older than this: not playing now
const REQUEST_FOR = 7 * 864e5;
const INVITE_FOR = 10 * 60e3;
const ROOM = /^[A-Z]{4}$/;

// A player's public friend id: the first 32 hex digits of SHA-256 of its secret id.
export async function pidOf(id) {
  const hash = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(id)));
  return [...hash.slice(0, 16)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

const ago = (ms) => new Date(Date.now() - ms).toISOString();

// The player as friends see it, its pid filled on first use (players from before #324 have none).
async function friendSelf(env, id) {
  const p = await env.DB.prepare('SELECT name, status, pid FROM players WHERE id = ?').bind(id).first();
  if (p && !p.pid) {
    p.pid = await pidOf(id);
    await env.DB.prepare('UPDATE players SET pid = ? WHERE id = ?').bind(p.pid, id).run();
  }
  return p;
}

const pair = (x, y) => (x < y ? [x, y] : [y, x]);

async function areFriends(env, x, y) {
  const [a, b] = pair(x, y);
  return !!(await env.DB.prepare('SELECT 1 FROM friends WHERE a = ? AND b = ?').bind(a, b).first());
}

async function friendCount(env, id) {
  return (await env.DB.prepare('SELECT COUNT(*) AS n FROM friends WHERE a = ? OR b = ?').bind(id, id).first()).n;
}

// Everything a phone shows about its friends: the friends with what each plays, the requests
// waiting for it, the pids it has asked, and its open invites. Old requests and invites go first.
async function friendState(env, id) {
  await env.DB.prepare('DELETE FROM friend_requests WHERE at < ?').bind(ago(REQUEST_FOR)).run();
  await env.DB.prepare('DELETE FROM invites WHERE at < ?').bind(ago(INVITE_FOR)).run();
  const pid = await pidOf(id), since = ago(PLAYING_FOR);
  const { results: rows } = await env.DB.prepare(
    `SELECT p.pid, p.name, x.game, x.version, x.at FROM friends f
     JOIN players p ON p.id = CASE WHEN f.a = ? THEN f.b ELSE f.a END
     LEFT JOIN presence x ON x.player = p.id
     WHERE (f.a = ? OR f.b = ?) AND p.status != 'rejected' AND p.pid IS NOT NULL
     ORDER BY p.name COLLATE NOCASE`
  ).bind(id, id, id).all();
  const friends = rows.map((r) => ({ pid: r.pid, name: r.name, game: r.game, version: r.version, at: r.at, now: !!r.at && r.at > since }));
  // Playing a game first, then browsing the shelf, then the rest; by name within each.
  const rank = (f) => (f.now ? (f.game ? 0 : 1) : 2);
  friends.sort((x, y) => rank(x) - rank(y));
  const { results: asking } = await env.DB.prepare(
    `SELECT p.pid, p.name FROM friend_requests r JOIN players p ON p.id = r.sender
     WHERE r.receiver = ? AND r.declined = 0 AND p.status != 'rejected' AND p.pid IS NOT NULL ORDER BY r.at DESC`
  ).bind(pid).all();
  const { results: asked } = await env.DB.prepare('SELECT receiver FROM friend_requests WHERE sender = ?').bind(id).all();
  const { results: invites } = await env.DB.prepare(
    `SELECT i.id, p.pid AS sender, p.name, i.game, i.version, i.room FROM invites i JOIN players p ON p.id = i.sender
     WHERE i.receiver = ? AND p.status != 'rejected' ORDER BY i.at DESC`
  ).bind(id).all();
  return {
    pid,
    friends,
    requests: asking.map((r) => ({ pid: r.pid, name: r.name })),
    asked: asked.map((r) => r.receiver),
    invites: invites.map((r) => ({ id: r.id, from: r.sender, name: r.name, game: r.game, version: r.version, room: r.room })),
  };
}

async function getFriends(env, url) {
  const player = url.searchParams.get('player') || '';
  if (!ID.test(player)) return fail(400, 'bad player');
  await friendSelf(env, player);
  return json(await friendState(env, player));
}

// "Now playing": a game and version the site has, or none (the shelf).
async function presence(env, url, body) {
  const player = String(body.player || '');
  if (!ID.test(player)) return fail(400, 'bad player');
  let game = null, version = null;
  if (body.game !== undefined && body.game !== null) {
    game = String(body.game);
    version = Number(body.version);
    if (!SLUG.test(game)) return fail(400, 'bad game');
    if (!Number.isInteger(version) || version < 1 || version > 999) return fail(400, 'bad version');
    const known = await knownVersions(env, url);
    if (known && known !== 'any' && !(known.get(game) && known.get(game).has(version))) game = version = null;
  }
  if (!(await friendSelf(env, player))) return fail(404, 'unknown player');
  await env.DB.prepare(
    `INSERT INTO presence (player, game, version, at) VALUES (?, ?, ?, ?)
     ON CONFLICT (player) DO UPDATE SET game = excluded.game, version = excluded.version, at = excluded.at`
  ).bind(player, game, version, now()).run();
  return json(await friendState(env, player));
}

const usable = (p) => p && p.status !== 'rejected';

// Counts one send of `kind` ('ask' or 'invite') against the player's hourly limit. False when the
// limit is reached. The count and the insert are one statement, so sends at once cannot pass the
// limit together; what was sent stays counted after it is accepted, answered or replaced.
async function countSend(env, player, kind, most) {
  const hour = ago(3600e3);
  await env.DB.prepare('DELETE FROM friend_sends WHERE at < ?').bind(hour).run();
  const res = await env.DB.prepare(
    `INSERT INTO friend_sends (player, kind, at)
     SELECT ?, ?, ? WHERE (SELECT COUNT(*) FROM friend_sends WHERE player = ? AND kind = ? AND at > ?) < ?`
  ).bind(player, kind, now(), player, kind, hour, most).run();
  return res.meta.changes > 0;
}

async function befriend(env, x, y) {
  const [a, b] = pair(x, y);
  await env.DB.prepare('INSERT INTO friends (a, b, at) VALUES (?, ?, ?) ON CONFLICT (a, b) DO NOTHING').bind(a, b, now()).run();
  await env.DB.prepare('DELETE FROM friend_requests WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)')
    .bind(x, await pidOf(y), y, await pidOf(x)).run();
}

async function askFriend(env, body) {
  const player = String(body.player || ''), to = String(body.to || '');
  if (!ID.test(player)) return fail(400, 'bad player');
  if (!ID.test(to)) return fail(400, 'bad friend');
  const me = await friendSelf(env, player);
  if (!usable(me)) return fail(403, 'nickname needed');
  if (to === me.pid) return fail(400, 'not yourself');
  const other = await env.DB.prepare('SELECT id, status FROM players WHERE pid = ?').bind(to).first();
  if (other && (await areFriends(env, player, other.id))) return json({ ok: true, friends: true });
  if ((await friendCount(env, player)) >= FRIENDS_MAX) return fail(409, 'too many friends');
  // Asked already (and maybe declined, which the asker is never told): nothing new is sent.
  if (await env.DB.prepare('SELECT 1 FROM friend_requests WHERE sender = ? AND receiver = ?').bind(player, to).first()) {
    return json({ ok: true, friends: false });
  }
  if (!(await countSend(env, player, 'ask', ASKS_PER_HOUR))) return fail(429, 'too many requests');
  // Both asked: they are friends at once.
  if (usable(other) && (await env.DB.prepare('SELECT 1 FROM friend_requests WHERE sender = ? AND receiver = ?').bind(other.id, me.pid).first())) {
    if ((await friendCount(env, other.id)) >= FRIENDS_MAX) return fail(409, 'too many friends');
    await befriend(env, player, other.id);
    return json({ ok: true, friends: true });
  }
  await env.DB.prepare('INSERT INTO friend_requests (sender, receiver, at) VALUES (?, ?, ?) ON CONFLICT (sender, receiver) DO NOTHING')
    .bind(player, to, now()).run();
  return json({ ok: true, friends: false });
}

async function answerFriend(env, body) {
  const player = String(body.player || ''), from = String(body.from || '');
  if (!ID.test(player)) return fail(400, 'bad player');
  if (!ID.test(from)) return fail(400, 'bad friend');
  const me = await friendSelf(env, player), pid = me ? me.pid : await pidOf(player);
  const other = await env.DB.prepare('SELECT id, status FROM players WHERE pid = ?').bind(from).first();
  const asked = other && (await env.DB.prepare('SELECT 1 FROM friend_requests WHERE sender = ? AND receiver = ?').bind(other.id, pid).first());
  if (!asked) return fail(404, 'no such request');
  if (body.yes === true) {
    if (!usable(me)) return fail(403, 'nickname needed');
    if (!usable(other)) return fail(404, 'no such request');
    if ((await friendCount(env, player)) >= FRIENDS_MAX || (await friendCount(env, other.id)) >= FRIENDS_MAX) return fail(409, 'too many friends');
    await befriend(env, player, other.id);
  } else {
    // Kept until it is old, so the asking phone still sees "Pyydetty" and never a "no".
    await env.DB.prepare('UPDATE friend_requests SET declined = 1 WHERE sender = ? AND receiver = ?').bind(other.id, pid).run();
  }
  return json({ ok: true });
}

async function removeFriend(env, body) {
  const player = String(body.player || ''), pid = String(body.pid || '');
  if (!ID.test(player)) return fail(400, 'bad player');
  if (!ID.test(pid)) return fail(400, 'bad friend');
  const other = await env.DB.prepare('SELECT id FROM players WHERE pid = ?').bind(pid).first();
  if (other) {
    const [a, b] = pair(player, other.id);
    await env.DB.prepare('DELETE FROM friends WHERE a = ? AND b = ?').bind(a, b).run();
    await env.DB.prepare('DELETE FROM invites WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)')
      .bind(player, other.id, other.id, player).run();
  }
  return json({ ok: true });
}

async function invite(env, url, body) {
  const player = String(body.player || ''), to = String(body.to || ''), game = String(body.game || '');
  const version = Number(body.version), room = String(body.room || '');
  if (!ID.test(player)) return fail(400, 'bad player');
  if (!ID.test(to)) return fail(400, 'bad friend');
  if (!SLUG.test(game) || !Number.isInteger(version) || version < 1 || version > 999) return fail(400, 'bad game');
  if (!ROOM.test(room)) return fail(400, 'bad room');
  const known = await knownVersions(env, url);
  if (known && known !== 'any' && !(known.get(game) && known.get(game).has(version))) return fail(404, 'no such version');
  const me = await friendSelf(env, player);
  const other = await env.DB.prepare('SELECT id FROM players WHERE pid = ?').bind(to).first();
  if (!usable(me) || !other || !(await areFriends(env, player, other.id))) return fail(403, 'friends only');
  if (!(await countSend(env, player, 'invite', INVITES_PER_HOUR))) return fail(429, 'too many invites');
  // One open invite per pair: a new one replaces the old.
  await env.DB.prepare('DELETE FROM invites WHERE sender = ? AND receiver = ?').bind(player, other.id).run();
  await env.DB.prepare('INSERT INTO invites (sender, receiver, game, version, room, at) VALUES (?, ?, ?, ?, ?, ?)')
    .bind(player, other.id, game, version, room, now()).run();
  return json({ ok: true });
}

async function answerInvite(env, id, body) {
  const player = String(body.player || '');
  if (!ID.test(player)) return fail(400, 'bad player');
  await env.DB.prepare('DELETE FROM invites WHERE id = ? AND receiver = ?').bind(id, player).run();
  return json({ ok: true });
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
  if (path === '/api/feedback' && method === 'POST') {
    const body = await readBody(request);
    return body ? addFeedback(env, url, body) : fail(400, 'bad body');
  }
  if (path === '/api/friends' && method === 'GET') return getFriends(env, url);
  if (path === '/api/presence' && method === 'POST') {
    const body = await readBody(request);
    return body ? presence(env, url, body) : fail(400, 'bad body');
  }
  if (path === '/api/friends/requests' && method === 'POST') {
    const body = await readBody(request);
    return body ? askFriend(env, body) : fail(400, 'bad body');
  }
  if (path === '/api/friends/requests/answer' && method === 'POST') {
    const body = await readBody(request);
    return body ? answerFriend(env, body) : fail(400, 'bad body');
  }
  if (path === '/api/friends' && method === 'DELETE') {
    const body = await readBody(request);
    return body ? removeFriend(env, body) : fail(400, 'bad body');
  }
  if (path === '/api/invites' && method === 'POST') {
    const body = await readBody(request);
    return body ? invite(env, url, body) : fail(400, 'bad body');
  }
  const inv = path.match(/^\/api\/invites\/([1-9][0-9]{0,15})\/answer$/);
  if (inv && method === 'POST') {
    const body = await readBody(request);
    return body ? answerInvite(env, Number(inv[1]), body) : fail(400, 'bad body');
  }
  if (path === '/api/admin/feedback') {
    if (!isAdmin(request, env)) return fail(403, 'admin key needed');
    if (method === 'GET') return adminFeedback(env, url);
    if (method === 'POST') {
      const body = await readBody(request);
      return body ? adminFiled(env, body) : fail(400, 'bad body');
    }
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

// The public rooms of one game (#50), or with no game every game's (the shelf, #203), from the one
// object that keeps the list (rooms/worker.js). Only this GET reaches it from outside; the rooms
// themselves tell it what is listed.
function publicRooms(request, env) {
  if (!env.ROOMS) return fail(503, 'no rooms');
  if (request.method !== 'GET') return fail(405, 'GET only');
  const game = new URL(request.url).searchParams.get('game');
  if (game !== null && !/^[a-z0-9-]{1,40}$/.test(game)) return fail(400, 'bad game');
  const q = game === null ? '' : `?${new URLSearchParams({ game })}`;
  return env.ROOMS.get(env.ROOMS.idFromName('lobby')).fetch(new Request(`https://rooms/lobby${q}`));
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
