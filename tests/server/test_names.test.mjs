// Test nicknames (#380): the agents' live checks play the real site as "Testi1", "Testi2"...
// They count toward no spam limit, never show to the admin, and are deleted a day after.
import test from 'node:test';
import assert from 'node:assert/strict';
import { handle, isTestName, NEW_PER_DAY, PENDING_MAX, pidOf } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

const ADMIN_KEY = 'avain';
const id = (n) => n.toString(16).padStart(32, '0');

function setup() {
  const env = { DB: makeD1(), ADMIN_KEY };
  const call = async (method, path, body, headers = {}) => {
    const init = { method, headers: { 'content-type': 'application/json', ...headers } };
    if (body !== undefined) init.body = JSON.stringify(body);
    const res = await handle(new Request('https://pelit.test' + path, init), env);
    return { status: res.status, body: await res.json() };
  };
  const adminList = async () =>
    (await call('GET', '/api/admin/players', undefined, { 'x-admin-key': ADMIN_KEY })).body.players.map((p) => p.name);
  const age = (player, ms) => {
    const t = new Date(Date.now() - ms).toISOString();
    env.DB.raw.prepare('UPDATE players SET created_at = ?, updated_at = ? WHERE id = ?').run(t, t, player);
  };
  const count = (sql, ...args) => env.DB.raw.prepare(sql).get(...args).n;
  return { env, call, adminList, age, count };
}

test('what a test name is', () => {
  for (const n of ['Testi', 'testi2', 'Testi A', 'Testi184b', 'TESTI3', '  Testi1 ']) assert.equal(isTestName(n), true, n);
  for (const n of ['Testaaja', 'Eero', 'Testi123456789', 'Testi-1', 'Ttesti', '']) assert.equal(isTestName(n), false, n);
});

test('a test name over a day old is deleted with everything it left; a real one stays', async () => {
  const { env, call, adminList, age, count } = setup();
  const T = id(1), R = id(2), F = id(3);
  await call('POST', '/api/players', { id: T, name: 'Testi1' });
  await call('POST', '/api/players', { id: R, name: 'Aino' });
  await call('POST', '/api/players', { id: F, name: 'Pekka' });
  await call('POST', '/api/scores', { player: T, game: 'sormiskeitti', board: 'main', version: 5, score: 50 });
  const db = env.DB.raw, t = new Date().toISOString();
  db.prepare('INSERT INTO friends (a, b, at) VALUES (?, ?, ?)').run(T < F ? T : F, T < F ? F : T, t);
  db.prepare('INSERT INTO friend_requests (sender, receiver, at) VALUES (?, ?, ?)').run(F, await pidOf(T), t);
  db.prepare('INSERT INTO invites (sender, receiver, game, version, room, at) VALUES (?, ?, ?, ?, ?, ?)').run(T, F, 'kirkkis', 2, 'ABCD', t);
  db.prepare('INSERT INTO presence (player, game, version, at) VALUES (?, ?, ?, ?)').run(T, 'kirkkis', 2, t);
  db.prepare('INSERT INTO push_subs (player, endpoint, at) VALUES (?, ?, ?)').run(T, 'https://push.test/1', t);
  db.prepare("INSERT INTO friend_sends (player, kind, at) VALUES (?, 'ask', ?)").run(T, t);

  // Under a day: kept, but never on the admin's list.
  age(T, 23 * 36e5);
  age(R, 30 * 36e5);
  assert.deepEqual((await adminList()).sort(), ['Aino', 'Pekka']);
  assert.equal(count('SELECT COUNT(*) AS n FROM players WHERE id = ?', T), 1);

  // Over a day: gone at the next admin list, and the old real name stays.
  age(T, 25 * 36e5);
  assert.deepEqual((await adminList()).sort(), ['Aino', 'Pekka']);
  assert.equal(count('SELECT COUNT(*) AS n FROM players WHERE id = ?', T), 0);
  assert.equal(count('SELECT COUNT(*) AS n FROM players WHERE id = ?', R), 1);
  for (const [table, col] of [['names', 'player'], ['scores', 'player'], ['presence', 'player'], ['push_subs', 'player'], ['friend_sends', 'player'], ['invites', 'sender']]) {
    assert.equal(count(`SELECT COUNT(*) AS n FROM ${table} WHERE ${col} = ?`, T), 0, table);
  }
  assert.equal(count('SELECT COUNT(*) AS n FROM friends'), 0);
  assert.equal(count('SELECT COUNT(*) AS n FROM friend_requests'), 0);
  // The freed name can be taken again.
  assert.equal((await call('POST', '/api/players', { id: id(4), name: 'testi1' })).status, 200);
});

test('setting a name also clears old test names', async () => {
  const { call, age, count } = setup();
  await call('POST', '/api/players', { id: id(1), name: 'Testi' });
  age(id(1), 2 * 864e5);
  await call('POST', '/api/players', { id: id(2), name: 'Aino' });
  assert.equal(count('SELECT COUNT(*) AS n FROM players WHERE id = ?', id(1)), 0);
});

test('test names count toward neither spam limit', async () => {
  const { call } = setup();
  // A day's worth of test names from one network still leaves room for real ones.
  for (let i = 0; i < NEW_PER_DAY + 2; i++) {
    assert.equal((await call('POST', '/api/players', { id: id(100 + i), name: `Testi${i}` })).status, 200);
  }
  for (let i = 0; i < NEW_PER_DAY; i++) {
    assert.equal((await call('POST', '/api/players', { id: id(200 + i), name: `Pelaaja${i}` })).status, 200);
  }
  assert.equal((await call('POST', '/api/players', { id: id(300), name: 'Liikaa' })).status, 429);
});

test('waiting test names take no place among the names waiting', async () => {
  const { env, call } = setup();
  const t = new Date(Date.now() - 2 * 864e5).toISOString(), now = new Date().toISOString();
  const add = env.DB.raw.prepare("INSERT INTO players (id, name, status, created_at, updated_at, source) VALUES (?, ?, 'pending', ?, ?, 'muu')");
  // Real names waiting up to one under the cap, made long ago so no network limit applies.
  for (let i = 0; i < PENDING_MAX - 1; i++) add.run(id(500 + i), `Odottaa${i}`, t, t);
  // Fresh test names waiting too: they must not fill the last place.
  for (let i = 0; i < 5; i++) add.run(id(600 + i), `Testi${i}`, now, now);
  assert.equal((await call('POST', '/api/players', { id: id(700), name: 'Viimeinen' })).status, 200);
  assert.equal((await call('POST', '/api/players', { id: id(701), name: 'Liikaa' })).status, 429);
});

test('a real player who renames itself "Testi" keeps its scores and stays on the admin list', async () => {
  const { env, call, adminList, age, count } = setup();
  const E = id(9);
  await call('POST', '/api/players', { id: E, name: 'Eero' });
  const name = 'Eero';
  await call('POST', '/api/admin/players', { id: E, name, status: 'approved' }, { 'x-admin-key': ADMIN_KEY });
  await call('POST', '/api/scores', { player: E, game: 'sormiskeitti', board: 'main', version: 5, score: 80 });
  await call('POST', '/api/players', { id: E, name: 'Testi' });
  age(E, 30 * 864e5);
  assert.deepEqual(await adminList(), ['Testi']);
  await call('POST', '/api/players', { id: id(10), name: 'Aino' });
  assert.equal(count('SELECT COUNT(*) AS n FROM players WHERE id = ?', E), 1);
  assert.equal(count('SELECT COUNT(*) AS n FROM scores WHERE player = ?', E), 1);
  assert.equal(env.DB.raw.prepare('SELECT status FROM players WHERE id = ?').get(E).status, 'pending');
});

test('many old test players are cleaned a batch at a time, all gone after a few requests', async () => {
  const { env, adminList, count } = setup();
  const t = new Date(Date.now() - 2 * 864e5).toISOString();
  const add = env.DB.raw.prepare("INSERT INTO players (id, name, status, created_at, updated_at) VALUES (?, ?, 'rejected', ?, ?)");
  for (let i = 0; i < 120; i++) add.run(id(1000 + i), `Testi${i}`, t, t);
  for (let i = 0; i < 120; i++) {
    env.DB.raw.prepare('INSERT INTO scores (player, game, board, version, score, at) VALUES (?, ?, ?, ?, ?, ?)')
      .run(id(1000 + i), 'sormiskeitti', 'main', 5, i, t);
  }
  // One request deletes a batch of 40 in a handful of statements, far under D1's limit of 50.
  const before = env.DB.queries;
  await adminList();
  assert.ok(env.DB.queries - before <= 15, `${env.DB.queries - before} statements`);
  assert.equal(count('SELECT COUNT(*) AS n FROM players'), 80);
  assert.equal(count('SELECT COUNT(*) AS n FROM scores'), 80);
  await adminList();
  await adminList();
  assert.equal(count('SELECT COUNT(*) AS n FROM players'), 0);
  assert.equal(count('SELECT COUNT(*) AS n FROM scores'), 0);
});

test('a failing delete leaves every test player whole', async () => {
  const { env, adminList, count } = setup();
  const t = new Date(Date.now() - 2 * 864e5).toISOString();
  env.DB.raw.prepare("INSERT INTO players (id, name, status, created_at, updated_at) VALUES (?, 'Testi', 'rejected', ?, ?)").run(id(1), t, t);
  env.DB.raw.prepare("INSERT INTO names (name_key, player, locked, at) VALUES ('testi', ?, 0, ?)").run(id(1), t);
  env.DB.raw.exec("CREATE TRIGGER stop BEFORE DELETE ON players BEGIN SELECT RAISE(ABORT, 'stop'); END");
  await assert.rejects(adminList());
  assert.equal(count('SELECT COUNT(*) AS n FROM names'), 1);
  assert.equal(count('SELECT COUNT(*) AS n FROM players'), 1);
});

test('hundreds of fresh test names do not push a real waiting name off the admin list', async () => {
  const { env, call, adminList } = setup();
  await call('POST', '/api/players', { id: id(1), name: 'Aino' });
  const now = new Date(Date.now() + 1000).toISOString();
  const add = env.DB.raw.prepare("INSERT INTO players (id, name, status, created_at, updated_at) VALUES (?, ?, 'pending', ?, ?)");
  for (let i = 0; i < 450; i++) add.run(id(2000 + i), `Testi${i}`, now, now);
  // A name that only starts like a test name is a real one, and shows too.
  add.run(id(3000), 'Testi-ukko', now, now);
  add.run(id(3001), 'Testiä', now, now);
  assert.deepEqual((await adminList()).sort(), ['Aino', 'Testi-ukko']);
});
