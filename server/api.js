// The online parts of AI-pelit: high-score lists and the nicknames on them (#25).
//
// Every game still plays fully offline; these routes are an extra that public/scores.js talks
// to when it can. `env.DB` is the D1 database (migrations/), `env.ADMIN_KEY` the admin's secret.
//
//   POST /api/players          {id, name}                    -> {name, status}
//   GET  /api/players/<id>                                   -> {name, status}
//   POST /api/scores           {player, game, board, version, score} -> {best, rank}
//   GET  /api/scores?game=&board=&player=                    -> {rows, mine}
//   GET  /api/admin/players    (X-Admin-Key)                 -> {players}
//   POST /api/admin/players    (X-Admin-Key) {id, status}    -> {name, status}
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
  puhelinkoppi: { order: 'high', boards: /^main$/ }, // highest level reached
  hiihto: { order: 'low', boards: /^taso-[1-9][0-9]{0,2}$/ }, // fastest time per course, seconds
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

// 1 + how many approved players beat this score on the list.
async function rankOf(env, game, board, score) {
  const better = GAMES[game].order === 'low' ? '<' : '>';
  const r = await env.DB.prepare(
    `SELECT COUNT(*) AS n FROM scores s JOIN players p ON p.id = s.player
     WHERE s.game = ? AND s.board = ? AND p.status = 'approved' AND s.score ${better} ?`
  ).bind(game, board, score).first();
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
  const known = await env.DB.prepare('SELECT 1 FROM players WHERE id = ?').bind(player).first();
  if (!known) return fail(404, 'unknown player');
  const better = GAMES[game].order === 'low' ? '<' : '>';
  // Keep only the player's best on each list.
  await env.DB.prepare(
    `INSERT INTO scores (game, board, player, score, version, at) VALUES (?, ?, ?, ?, ?, ?)
     ON CONFLICT (game, board, player) DO UPDATE
       SET score = excluded.score, version = excluded.version, at = excluded.at
       WHERE excluded.score ${better} scores.score`
  ).bind(game, board, player, score, version, now()).run();
  const best = await env.DB.prepare('SELECT score FROM scores WHERE game = ? AND board = ? AND player = ?')
    .bind(game, board, player).first();
  return json({ best: best.score, rank: await rankOf(env, game, board, best.score) });
}

async function list(env, url) {
  const game = url.searchParams.get('game') || '', board = url.searchParams.get('board') || 'main';
  const player = url.searchParams.get('player') || '';
  if (!Object.hasOwn(GAMES, game)) return fail(400, 'no list for this game');
  if (!GAMES[game].boards.test(board)) return fail(400, 'bad board');
  const order = GAMES[game].order === 'low' ? 'ASC' : 'DESC';
  // Player ids are each phone's secret: never sent back, only "is this row mine".
  const { results } = await env.DB.prepare(
    `SELECT p.name, s.score, s.version, s.at, s.player = ? AS me
     FROM scores s JOIN players p ON p.id = s.player
     WHERE s.game = ? AND s.board = ? AND p.status = 'approved'
     ORDER BY s.score ${order}, s.at ASC LIMIT ${LIST}`
  ).bind(player, game, board).all();
  const rows = results.map((r, i) => ({ rank: i + 1, name: r.name, score: r.score, version: r.version, at: r.at, me: !!r.me }));
  let mine = null;
  if (ID.test(player)) {
    const m = await env.DB.prepare(
      `SELECT p.name, p.status, s.score, s.version, s.at FROM scores s JOIN players p ON p.id = s.player
       WHERE s.game = ? AND s.board = ? AND s.player = ?`
    ).bind(game, board, player).first();
    if (m) {
      mine = { name: m.name, status: m.status, score: m.score, version: m.version, at: m.at };
      if (m.status === 'approved') mine.rank = await rankOf(env, game, board, m.score);
    }
  }
  return json({ rows, mine });
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
  const id = String(body.id || ''), status = body.status;
  if (!ID.test(id)) return fail(400, 'bad id');
  if (status !== 'approved' && status !== 'rejected') return fail(400, 'status is approved or rejected');
  const p = await env.DB.prepare('SELECT name FROM players WHERE id = ?').bind(id).first();
  if (!p) return fail(404, 'unknown player');
  if (status === 'approved') {
    // An approved name is locked to this phone for good. A rejected player's name was freed,
    // and another phone may hold it now: then it cannot be approved.
    const key = nameKey(p.name);
    if (!(await claim(env, key, id, 1))) return fail(409, 'name taken by another player');
    await env.DB.prepare('UPDATE names SET locked = 1 WHERE name_key = ?').bind(key).run();
  } else {
    // Rejecting the player frees every name it held.
    await env.DB.prepare('DELETE FROM names WHERE player = ?').bind(id).run();
  }
  await env.DB.prepare('UPDATE players SET status = ?, updated_at = ? WHERE id = ?').bind(status, now(), id).run();
  return json({ name: p.name, status });
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
  if (path === '/api/scores' && method === 'POST') {
    const body = await readBody(request);
    return body ? addScore(env, body) : fail(400, 'bad body');
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

export async function handle(request, env) {
  if (!env.DB) return fail(503, 'no database');
  try {
    return await route(request, env);
  } catch (e) {
    console.error(e);
    return fail(500, 'server error');
  }
}
