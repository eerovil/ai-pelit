// server/api.js against a real SQLite with the migrations applied: node --test tests/server/
import test from 'node:test';
import assert from 'node:assert/strict';
import { handle, NEW_PER_DAY, PENDING_MAX } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

const ADMIN_KEY = 'avain';
const A = 'a'.repeat(32), B = 'b'.repeat(32), C = 'c'.repeat(32);

function api(env) {
  return async (method, path, body, headers = {}) => {
    const init = { method, headers: { 'content-type': 'application/json', ...headers } };
    if (body !== undefined) init.body = typeof body === 'string' ? body : JSON.stringify(body);
    const res = await handle(new Request('https://pelit.test' + path, init), env);
    return { status: res.status, body: await res.json() };
  };
}

function setup() {
  const env = { DB: makeD1(), ADMIN_KEY };
  const call = api(env);
  // Decides on the player's current name, as the admin page shows it.
  const admin = async (id, status) => {
    const name = env.DB.raw.prepare('SELECT name FROM players WHERE id = ?').get(id)?.name ?? '';
    return call('POST', '/api/admin/players', { id, name, status }, { 'x-admin-key': ADMIN_KEY });
  };
  return { env, call, admin };
}

test('a new name waits for the admin and shows only to its own phone', async () => {
  const { call, admin } = setup();
  assert.deepEqual((await call('POST', '/api/players', { id: A, name: '  Eero  ' })).body, { name: 'Eero', status: 'pending' });
  await call('POST', '/api/scores', { player: A, game: 'sormiskeitti', board: 'main', version: 5, score: 120 });

  let list = (await call('GET', `/api/scores?game=sormiskeitti&player=${A}`)).body;
  assert.deepEqual(list.rows, []);
  assert.equal(list.mine.status, 'pending');
  assert.equal(list.mine.score, 120);

  assert.equal((await admin(A, 'approved')).status, 200);
  list = (await call('GET', `/api/scores?game=sormiskeitti&player=${A}`)).body;
  assert.equal(list.rows.length, 1);
  assert.deepEqual([list.rows[0].name, list.rows[0].score, list.rows[0].version, list.rows[0].me], ['Eero', 120, 5, true]);
  assert.equal(list.mine.rank, 1);
  // Someone else's view: the row is not theirs, and no player id is ever sent.
  list = (await call('GET', '/api/scores?game=sormiskeitti')).body;
  assert.equal(list.rows[0].me, false);
  assert.equal(JSON.stringify(list).includes(A), false);
});

test('a changed name waits again; a rejected one is hidden', async () => {
  const { call, admin } = setup();
  await call('POST', '/api/players', { id: A, name: 'Eero' });
  await admin(A, 'approved');
  assert.equal((await call('POST', '/api/players', { id: A, name: 'Eero' })).body.status, 'approved');
  assert.equal((await call('POST', '/api/players', { id: A, name: 'Iskä' })).body.status, 'pending');
  await admin(A, 'rejected');
  assert.deepEqual((await call('GET', `/api/players/${A}`)).body, { name: 'Iskä', status: 'rejected' });
  await call('POST', '/api/scores', { player: A, game: 'voimistelu', board: 'main', version: 3, score: 12.5 });
  assert.deepEqual((await call('GET', '/api/scores?game=voimistelu')).body.rows, []);
});

test('names are unique, case-insensitively, and 1 to 16 characters', async () => {
  const { call } = setup();
  await call('POST', '/api/players', { id: A, name: 'Eero' });
  assert.equal((await call('POST', '/api/players', { id: B, name: 'eero' })).status, 409);
  assert.equal((await call('POST', '/api/players', { id: B, name: '   ' })).status, 400);
  assert.equal((await call('POST', '/api/players', { id: B, name: 'x'.repeat(17) })).status, 400);
  assert.equal((await call('POST', '/api/players', { id: B, name: 'ö'.repeat(16) })).status, 200);
  assert.equal((await call('POST', '/api/players', { id: 'short', name: 'Joku' })).status, 400);
});

test('each player keeps their best, and the list sorts the game\'s way', async () => {
  const { call, admin } = setup();
  for (const [id, name] of [[A, 'Aino'], [B, 'Bertta'], [C, 'Cecilia']]) {
    await call('POST', '/api/players', { id, name });
    await admin(id, 'approved');
  }
  const post = (player, game, board, score) => call('POST', '/api/scores', { player, game, board, version: 2, score });
  // Hiihto: lower time is better, one list per course.
  assert.deepEqual((await post(A, 'hiihto', 'taso-1', 95.5)).body, { best: 95.5, rank: 1 });
  assert.deepEqual((await post(A, 'hiihto', 'taso-1', 120)).body, { best: 95.5, rank: 1 });
  assert.deepEqual((await post(B, 'hiihto', 'taso-1', 80)).body, { best: 80, rank: 1 });
  await post(C, 'hiihto', 'taso-2', 60);
  let rows = (await call('GET', '/api/scores?game=hiihto&board=taso-1')).body.rows;
  assert.deepEqual(rows.map((r) => [r.rank, r.name, r.score]), [[1, 'Bertta', 80], [2, 'Aino', 95.5]]);
  // Puhelinkoppi: higher is better.
  await post(A, 'puhelinkoppi', 'main', 4);
  await post(B, 'puhelinkoppi', 'main', 9);
  await post(B, 'puhelinkoppi', 'main', 7);
  rows = (await call('GET', '/api/scores?game=puhelinkoppi')).body.rows;
  assert.deepEqual(rows.map((r) => [r.name, r.score]), [['Bertta', 9], ['Aino', 4]]);
  // Phones that kept the withdrawn v3/v4 may still send their streak list; it is taken, not shown.
  await post(A, 'puhelinkoppi', 'putki', 12);
  rows = (await call('GET', '/api/scores?game=puhelinkoppi&board=putki')).body.rows;
  assert.deepEqual(rows.map((r) => [r.name, r.score]), [['Aino', 12]]);
  assert.equal((await post(A, 'puhelinkoppi', 'taso-1', 3)).status, 400);
  // Aitajuoksu: 100 m hurdles is 'main', each other race its own list, lower time first.
  await post(A, 'aitajuoksu', '400-tasainen', 58.2);
  await post(B, 'aitajuoksu', '400-tasainen', 55.1);
  await post(A, 'aitajuoksu', 'main', 15.3);
  rows = (await call('GET', '/api/scores?game=aitajuoksu&board=400-tasainen')).body.rows;
  assert.deepEqual(rows.map((r) => [r.name, r.score]), [['Bertta', 55.1], ['Aino', 58.2]]);
  rows = (await call('GET', '/api/scores?game=aitajuoksu&board=main')).body.rows;
  assert.deepEqual(rows.map((r) => [r.name, r.score]), [['Aino', 15.3]]);
  for (const b of ['200-aidat', '100-tasainen']) assert.equal((await post(C, 'aitajuoksu', b, 30)).status, 200);
  for (const b of ['100-aidat', '800-tasainen', '400-aidat-x']) assert.equal((await post(C, 'aitajuoksu', b, 30)).status, 400);
});

test('bad scores and unknown players are refused', async () => {
  const { call } = setup();
  await call('POST', '/api/players', { id: A, name: 'Aino' });
  const ok = { player: A, game: 'sormiskeitti', board: 'main', version: 5, score: 10 };
  assert.equal((await call('POST', '/api/scores', ok)).status, 200);
  assert.equal((await call('POST', '/api/scores', { ...ok, player: B })).status, 404);
  assert.equal((await call('POST', '/api/scores', { ...ok, game: 'areena' })).status, 400);
  assert.equal((await call('POST', '/api/scores', { ...ok, board: 'Iso Lista' })).status, 400);
  // Each game has a fixed set of lists, so nobody can make up new ones.
  assert.equal((await call('POST', '/api/scores', { ...ok, board: 'taso-1' })).status, 400);
  assert.equal((await call('POST', '/api/scores', { ...ok, game: 'hiihto', board: 'taso-12' })).status, 200);
  assert.equal((await call('POST', '/api/scores', { ...ok, game: 'hiihto', board: 'taso-0' })).status, 400);
  // Hiihto v3's skating times have lists of their own (#61).
  assert.equal((await call('POST', '/api/scores', { ...ok, game: 'hiihto', board: 'luistelu-3' })).status, 200);
  assert.equal((await call('POST', '/api/scores', { ...ok, game: 'hiihto', board: 'luistelu-0' })).status, 400);
  assert.equal((await call('GET', '/api/scores?game=hiihto&board=main')).status, 400);
  assert.equal((await call('POST', '/api/scores', { ...ok, score: 'paljon' })).status, 400);
  assert.equal((await call('POST', '/api/scores', { ...ok, version: 0 })).status, 400);
  assert.equal((await call('POST', '/api/scores', 'ei jsonia')).status, 400);
  assert.equal((await call('GET', '/api/scores?game=areena')).status, 400);
  assert.equal((await call('GET', '/api/ei-ole')).status, 404);
});

test('the admin routes need the key', async () => {
  const { call } = setup();
  await call('POST', '/api/players', { id: A, name: 'Aino' });
  assert.equal((await call('GET', '/api/admin/players')).status, 403);
  assert.equal((await call('GET', '/api/admin/players', undefined, { 'x-admin-key': 'väärä' })).status, 403);
  const { body } = await call('GET', '/api/admin/players', undefined, { 'x-admin-key': ADMIN_KEY });
  assert.deepEqual(body.players.map((p) => [p.id, p.name, p.status]), [[A, 'Aino', 'pending']]);
  const noKey = api({ DB: makeD1() });
  assert.equal((await noKey('GET', '/api/admin/players', undefined, { 'x-admin-key': '' })).status, 403);
});

const hex = (n) => n.toString(16).padStart(32, '0');

test('one network makes only a few new names a day', async () => {
  const { call } = setup();
  const from = (ip) => ({ 'cf-connecting-ip': ip });
  for (let i = 0; i < NEW_PER_DAY; i++) {
    assert.equal((await call('POST', '/api/players', { id: hex(i), name: `Nimi ${i}` }, from('1.2.3.4'))).status, 200);
  }
  assert.equal((await call('POST', '/api/players', { id: hex(99), name: 'Vielä yksi' }, from('1.2.3.4'))).status, 429);
  assert.equal((await call('POST', '/api/players', { id: hex(99), name: 'Vielä yksi' }, from('5.6.7.8'))).status, 200);
  // Renaming an existing player is not a new name.
  assert.equal((await call('POST', '/api/players', { id: hex(0), name: 'Uusi nimi' }, from('1.2.3.4'))).status, 200);
});

test('no new name is taken while too many wait for the admin', async () => {
  const { env, call, admin } = setup();
  for (let i = 0; i < PENDING_MAX; i++) {
    assert.equal((await call('POST', '/api/players', { id: hex(i), name: `Nimi ${i}` }, { 'cf-connecting-ip': `10.0.0.${i}` })).status, 200);
  }
  assert.equal((await call('POST', '/api/players', { id: hex(500), name: 'Odottaja' })).status, 429);
  await admin(hex(0), 'rejected');
  assert.equal((await call('POST', '/api/players', { id: hex(500), name: 'Odottaja' })).status, 200);
  // The network is stored only as a hash.
  const row = env.DB.raw.prepare('SELECT source FROM players WHERE id = ?').get(hex(1));
  assert.match(row.source, /^[a-f0-9]{24}$/);
});

test('an approved name stays locked to its phone, even after it changes name', async () => {
  const { call, admin } = setup();
  await call('POST', '/api/players', { id: A, name: 'Aino' });
  await admin(A, 'approved');
  assert.equal((await call('POST', '/api/players', { id: A, name: 'Aino-Maria' })).status, 200);
  // Another phone cannot pose as Aino, in any case.
  assert.equal((await call('POST', '/api/players', { id: B, name: 'AINO' })).status, 409);
  // The phone that owns it can go back to it.
  assert.equal((await call('POST', '/api/players', { id: A, name: 'Aino' })).status, 200);
  // A name that was never approved is not locked: rejecting frees it, and so does rejecting the player.
  await call('POST', '/api/players', { id: C, name: 'Cecilia' });
  await admin(C, 'rejected');
  assert.equal((await call('POST', '/api/players', { id: B, name: 'Cecilia' })).status, 200);
  await admin(A, 'rejected');
  assert.equal((await call('POST', '/api/players', { id: C, name: 'Aino' })).status, 200);
});

test('two phones asking for one name at once: only one gets it', async () => {
  const { call } = setup();
  const both = await Promise.all([
    call('POST', '/api/players', { id: A, name: 'Aino' }),
    call('POST', '/api/players', { id: B, name: 'aino' }),
  ]);
  assert.deepEqual(both.map((r) => r.status).sort(), [200, 409]);
});

test('names differing only by Finnish letter case are the same name', async () => {
  const { call, admin } = setup();
  assert.equal((await call('POST', '/api/players', { id: A, name: 'ÄITI' })).status, 200);
  assert.equal((await call('POST', '/api/players', { id: B, name: 'äiti' })).status, 409);
  assert.equal((await call('POST', '/api/players', { id: B, name: 'Öljy' })).status, 200);
  await admin(B, 'approved');
  assert.equal((await call('POST', '/api/players', { id: C, name: 'ÖLJY' })).status, 409);
  // Composed and decomposed ä are one name too.
  assert.equal((await call('POST', '/api/players', { id: C, name: 'Pa\u0308ivi' })).status, 200);
  assert.equal((await call('POST', '/api/players', { id: A, name: 'P\u00e4ivi' })).status, 409);
});

test('a rejected player whose name another phone took cannot be approved back into it', async () => {
  const { call, admin } = setup();
  await call('POST', '/api/players', { id: A, name: 'Aino' });
  await admin(A, 'rejected');
  assert.equal((await call('POST', '/api/players', { id: B, name: 'Aino' })).status, 200);
  await admin(B, 'approved');
  assert.equal((await admin(A, 'approved')).status, 409);
  assert.deepEqual((await call('GET', `/api/players/${A}`)).body, { name: 'Aino', status: 'rejected' });
  // Once A picks a free name, it can be approved.
  await call('POST', '/api/players', { id: A, name: 'Aino K' });
  assert.equal((await admin(A, 'approved')).status, 200);
});

test('on a tie the earlier score is ahead, and the own row says the same place as the list', async () => {
  const { call, admin } = setup();
  const ids = Array.from({ length: 11 }, (_, i) => hex(1000 + i));
  for (const [i, id] of ids.entries()) {
    await call('POST', '/api/players', { id, name: `Pelaaja ${i}` }, { 'cf-connecting-ip': `10.1.0.${i}` });
    await admin(id, 'approved');
    const { body } = await call('POST', '/api/scores', { player: id, game: 'puhelinkoppi', board: 'main', version: 2, score: 5 });
    assert.equal(body.rank, i + 1);
    await new Promise((r) => setTimeout(r, 2)); // a later time for the next score
  }
  const list = (await call('GET', `/api/scores?game=puhelinkoppi&player=${ids[10]}`)).body;
  assert.deepEqual(list.rows.map((r) => r.rank), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  assert.equal(list.rows.some((r) => r.me), false);
  assert.equal(list.mine.rank, 11);
});

test('a decision on a name the phone has since changed is refused', async () => {
  const { call, env } = setup();
  const decide = (id, name, status) => call('POST', '/api/admin/players', { id, name, status }, { 'x-admin-key': ADMIN_KEY });
  await call('POST', '/api/players', { id: A, name: 'Aino' });
  // The admin's page shows Aino; meanwhile the phone changes to a name the admin never saw.
  await call('POST', '/api/players', { id: A, name: 'Rumanimi' });
  assert.equal((await decide(A, 'Aino', 'approved')).status, 409);
  assert.equal((await decide(A, 'Aino', 'rejected')).status, 409);
  assert.deepEqual((await call('GET', `/api/players/${A}`)).body, { name: 'Rumanimi', status: 'pending' });
  assert.deepEqual(env.DB.raw.prepare('SELECT name_key, locked FROM names WHERE player = ?').all(A).map((r) => [r.name_key, r.locked]), [['rumanimi', 0]]);
  assert.equal((await decide(A, 'Rumanimi', 'approved')).status, 200);
  assert.equal((await call('POST', '/api/admin/players', { id: A, status: 'approved' }, { 'x-admin-key': ADMIN_KEY })).status, 400);
});

test('plays: each open counts one, totals are per game, and nothing is kept per phone', async () => {
  const { env, call } = setup();
  for (const version of [1, 2, 2]) assert.deepEqual((await call('POST', '/api/plays', { game: 'hiihto', version })).body, { ok: true });
  await call('POST', '/api/plays', { game: 'kirkkis', version: 1 });
  assert.deepEqual((await call('GET', '/api/plays')).body, { games: { hiihto: 3, kirkkis: 1 } });
  // One row per game, version and day: no phone, no address.
  const rows = env.DB.raw.prepare('SELECT * FROM plays ORDER BY game, version').all();
  assert.deepEqual(rows.map((r) => Object.keys(r).sort()), Array(3).fill(['day', 'game', 'n', 'version']));
  assert.deepEqual(rows.map((r) => r.n), [1, 2, 1]);
});

test('plays: a bad game or version is refused', async () => {
  const { call } = setup();
  assert.equal((await call('POST', '/api/plays', { game: 'Hiihto!', version: 1 })).status, 400);
  assert.equal((await call('POST', '/api/plays', { game: 'hiihto', version: 0 })).status, 400);
  assert.equal((await call('POST', '/api/plays', { game: 'hiihto', version: 1.5 })).status, 400);
  assert.equal((await call('POST', '/api/plays', 'not json')).status, 400);
  assert.deepEqual((await call('GET', '/api/plays')).body, { games: {} });
});

test('each row carries the highest level reached, which can rise without a better score', async () => {
  const { call, admin } = setup();
  await call('POST', '/api/players', { id: A, name: 'Aino' });
  await admin(A, 'approved');
  const post = (score, level) => call('POST', '/api/scores', { player: A, game: 'sormiskeitti', board: 'main', version: 5, score, level });
  assert.equal((await post(40, 3)).status, 200);
  assert.equal((await post(30, 5)).status, 200); // a lower ollie, but a later level
  assert.equal((await post(35, 2)).status, 200); // a level lower than before does not lower it
  let { rows, mine } = (await call('GET', `/api/scores?game=sormiskeitti&player=${A}`)).body;
  assert.deepEqual([rows[0].score, rows[0].level], [40, 5]);
  assert.equal(mine.level, 5);
  // An older version sends no level: the score counts, the level stays.
  assert.equal((await call('POST', '/api/scores', { player: A, game: 'sormiskeitti', board: 'main', version: 5, score: 50 })).status, 200);
  rows = (await call('GET', '/api/scores?game=sormiskeitti')).body.rows;
  assert.deepEqual([rows[0].score, rows[0].level], [50, 5]);
  for (const level of [0, 1.5, 'kolme', -2]) assert.equal((await post(10, level)).status, 400);
  // No level ever sent: null.
  await call('POST', '/api/scores', { player: A, game: 'voimistelu', board: 'main', version: 3, score: 12 });
  assert.equal((await call('GET', '/api/scores?game=voimistelu')).body.rows[0].level, null);
});

test('the shelf gets every game\'s no. 1 in one request', async () => {
  const { call, admin } = setup();
  for (const [id, name] of [[A, 'Aino'], [B, 'Bertta'], [C, 'Cecilia']]) {
    await call('POST', '/api/players', { id, name });
    if (id !== C) await admin(id, 'approved');
  }
  const post = (player, game, board, score, level) => call('POST', '/api/scores', { player, game, board, version: 2, score, level });
  await post(A, 'sormiskeitti', 'main', 40, 3);
  await post(B, 'sormiskeitti', 'main', 55, 2);
  await post(C, 'sormiskeitti', 'main', 90); // waiting for approval: not shown
  await post(A, 'hiihto', 'taso-1', 80.5, 2);
  await post(B, 'hiihto', 'taso-2', 60);
  await post(A, 'puhelinkoppi', 'main', 30); // the level list is the shelf's again
  await post(B, 'puhelinkoppi', 'putki', 60); // the withdrawn streak list: not on the shelf
  const { body } = await call('GET', '/api/scores/top');
  assert.deepEqual(body.games, {
    sormiskeitti: { board: 'main', name: 'Bertta', score: 55, level: 2, version: 2 },
    puhelinkoppi: { board: 'main', name: 'Aino', score: 30, level: null, version: 2 },
    hiihto: { board: 'taso-1', name: 'Aino', score: 80.5, level: 2, version: 2 },
  });
});

test('a row shows the player\'s highest level in the whole game, from any list', async () => {
  const { call, admin } = setup();
  await call('POST', '/api/players', { id: A, name: 'Aino' });
  await admin(A, 'approved');
  const post = (board, score, level) => call('POST', '/api/scores', { player: A, game: 'hiihto', board, version: 2, score, level });
  await post('taso-1', 80, 1);
  await post('taso-2', 95, 2); // passing course 2 must show on course 1's list without replaying it
  const one = (await call('GET', `/api/scores?game=hiihto&board=taso-1&player=${A}`)).body;
  assert.equal(one.rows[0].level, 2);
  assert.equal(one.mine.level, 2);
  assert.equal((await call('GET', '/api/scores/top')).body.games.hiihto.level, 2);
});

test('Tikanheitto keeps Mökkitikka and Pistekisa apart, and its shelf no. 1 is Mökkitikka\'s', async () => {
  const { call, admin } = setup();
  for (const [id, name] of [[A, 'Aino'], [B, 'Bertta']]) {
    await call('POST', '/api/players', { id, name });
    await admin(id, 'approved');
  }
  const post = (player, board, score, version) => call('POST', '/api/scores', { player, game: 'tikka', board, version, score });
  assert.equal((await post(A, 'mokki', 254, 2)).status, 200);
  assert.equal((await post(B, 'main', 412, 1)).status, 200);
  assert.equal((await post(A, 'darts', 10, 2)).status, 400);
  assert.deepEqual((await call('GET', '/api/scores?game=tikka&board=mokki')).body.rows.map(r => r.name), ['Aino']);
  assert.deepEqual((await call('GET', '/api/scores?game=tikka&board=main')).body.rows.map(r => r.name), ['Bertta']);
  assert.deepEqual((await call('GET', '/api/scores/top')).body.games.tikka, { board: 'mokki', name: 'Aino', score: 254, level: null, version: 2 });
});
