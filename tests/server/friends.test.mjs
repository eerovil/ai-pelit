// Friends (#324): server/api.js on SQLite with the migrations.
import test from 'node:test';
import assert from 'node:assert/strict';
import { handle, pidOf, FRIENDS_MAX, ASKS_PER_HOUR, PLAYING_FOR } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

const ADMIN = { 'x-admin-key': 'avain' };
const A = 'a'.repeat(32), B = 'b'.repeat(32), C = 'c'.repeat(32);
const PA = await pidOf(A), PB = await pidOf(B), PC = await pidOf(C);

function setup() {
  const env = { DB: makeD1(), ADMIN_KEY: 'avain' };
  const call = async (method, path, body, headers = {}) => {
    const init = { method, headers: { 'content-type': 'application/json', ...headers } };
    if (body !== undefined) init.body = JSON.stringify(body);
    const res = await handle(new Request('https://pelit.test' + path, init), env);
    return { status: res.status, body: await res.json() };
  };
  const player = async (id, name, status) => {
    await call('POST', '/api/players', { id, name });
    if (status) await call('POST', '/api/admin/players', { id, name, status }, ADMIN);
  };
  const state = async (id) => (await call('GET', `/api/friends?player=${id}`)).body;
  const ask = (id, to) => call('POST', '/api/friends/requests', { player: id, to });
  const answer = (id, from, yes) => call('POST', '/api/friends/requests/answer', { player: id, from, yes });
  return { env, call, player, state, ask, answer };
}

test('a pid is a hash of the secret id, and no answer carries a secret id', async () => {
  assert.match(PA, /^[a-f0-9]{32}$/);
  assert.notEqual(PA, A);
  const { player, state, ask, answer, call } = setup();
  await player(A, 'Aino'); await player(B, 'Bertta');
  await ask(A, PB); await answer(B, PA, true);
  await call('POST', '/api/presence', { player: B, game: 'pilkki', version: 2 });
  for (const s of [await state(A), await state(B)]) {
    const text = JSON.stringify(s);
    assert.equal(text.includes(A) || text.includes(B), false);
  }
});

test('one asks, the other accepts, and both are friends; or declines and nothing is left', async () => {
  const { player, state, ask, answer, call } = setup();
  await player(A, 'Aino'); await player(B, 'Bertta');
  assert.deepEqual((await ask(A, PB)).body, { ok: true, friends: false });
  assert.deepEqual((await state(A)).asked, [PB]);
  assert.deepEqual((await state(B)).requests, [{ pid: PA, name: 'Aino' }]);
  assert.equal((await answer(B, PA, true)).status, 200);
  const a = await state(A), b = await state(B);
  assert.deepEqual(a.friends.map((f) => [f.pid, f.name, f.now]), [[PB, 'Bertta', false]]);
  assert.deepEqual(b.friends.map((f) => f.name), ['Aino']);
  assert.deepEqual([a.asked, b.requests], [[], []]);
  // Asking a friend again changes nothing.
  assert.deepEqual((await ask(B, PA)).body, { ok: true, friends: true });
  // Removed both ways.
  await call('DELETE', '/api/friends', { player: B, pid: PA });
  assert.deepEqual([(await state(A)).friends, (await state(B)).friends], [[], []]);
  // Declined: Bertta no longer sees it, and Aino still sees only "asked", even when she asks again.
  await ask(A, PB);
  await answer(B, PA, false);
  assert.deepEqual([(await state(A)).asked, (await state(B)).requests, (await state(B)).friends], [[PB], [], []]);
  assert.deepEqual((await ask(A, PB)).body, { ok: true, friends: false });
  assert.deepEqual((await state(B)).requests, []);
  // If Bertta changes her mind and asks Aino herself, they are friends at once.
  assert.deepEqual((await ask(B, PA)).body, { ok: true, friends: true });
  assert.deepEqual([(await state(A)).asked, (await state(A)).friends.map((f) => f.name)], [[], ['Bertta']]);
});

test('two phones asking each other are friends at once', async () => {
  const { player, state, ask } = setup();
  await player(A, 'Aino'); await player(B, 'Bertta');
  await ask(A, PB);
  assert.deepEqual((await ask(B, PA)).body, { ok: true, friends: true });
  assert.deepEqual((await state(A)).friends.map((f) => f.name), ['Bertta']);
});

test('a request may wait for a phone the server does not know yet', async () => {
  const { player, state, ask, answer } = setup();
  await player(A, 'Aino');
  await ask(A, PC);
  assert.deepEqual((await state(C)).requests, [{ pid: PA, name: 'Aino' }]);
  assert.equal((await answer(C, PA, true)).status, 403); // C has no nickname yet
  await player(C, 'Ceci');
  assert.equal((await answer(C, PA, true)).status, 200);
  assert.deepEqual((await state(A)).friends.map((f) => f.name), ['Ceci']);
});

test('friends need a nickname that is not rejected; a pending one is fine', async () => {
  const { player, state, ask, answer } = setup();
  assert.equal((await ask(A, PB)).status, 403);
  await player(A, 'Aino', 'rejected');
  assert.equal((await ask(A, PB)).status, 403);
  await player(B, 'Bertta');
  assert.equal((await ask(B, PB)).status, 400); // not yourself
  await ask(B, PA);
  assert.deepEqual((await state(A)).requests, [{ pid: PB, name: 'Bertta' }]);
  assert.equal((await answer(A, PB, true)).status, 403);
  // A rejected player's requests and friendship do not show.
  await player(C, 'Ceci');
  await ask(C, PB); await answer(B, PC, true);
  await player(C, 'Ceci', 'rejected');
  assert.deepEqual((await state(B)).friends, []);
});

test('limits: asks an hour, friends per phone', async () => {
  const { player, ask, env } = setup();
  await player(A, 'Aino');
  for (let i = 0; i < ASKS_PER_HOUR; i++) assert.equal((await ask(A, await pidOf(String(i).padStart(32, "0")))).status, 200);
  assert.equal((await ask(A, PB)).status, 429);
  env.DB.raw.exec('DELETE FROM friend_requests');
  for (let i = 0; i < FRIENDS_MAX; i++) env.DB.raw.prepare('INSERT INTO friends (a, b, at) VALUES (?, ?, ?)').run(A, String(i + 100).padStart(32, 'f'), 'x');
  assert.equal((await ask(A, PB)).status, 409);
});

test('now playing: what a friend plays, and when it was last seen', async () => {
  const { player, state, ask, answer, call, env } = setup();
  await player(A, 'Aino'); await player(B, 'Bertta');
  assert.equal((await call('POST', '/api/presence', { player: C })).status, 404);
  assert.equal((await call('POST', '/api/presence', { player: B, game: 'Pilkki', version: 2 })).status, 400);
  await ask(A, PB); await answer(B, PA, true);
  const got = (await call('POST', '/api/presence', { player: B, game: 'pilkki', version: 2 })).body;
  assert.deepEqual(got.friends.map((f) => f.name), ['Aino']); // the answer is the phone's own state
  let f = (await state(A)).friends[0];
  assert.deepEqual([f.game, f.version, f.now], ['pilkki', 2, true]);
  await call('POST', '/api/presence', { player: B });
  f = (await state(A)).friends[0];
  assert.deepEqual([f.game, f.version, f.now], [null, null, true]); // on the shelf
  env.DB.raw.prepare('UPDATE presence SET at = ?').run(new Date(Date.now() - PLAYING_FOR - 1000).toISOString());
  f = (await state(A)).friends[0];
  assert.equal(f.now, false);
  assert.ok(f.at);
});

test('invites go only to a friend, one per pair, and go away when answered or old', async () => {
  const { player, state, ask, answer, call, env } = setup();
  await player(A, 'Aino'); await player(B, 'Bertta'); await player(C, 'Ceci');
  const inv = (id, to, room = 'KISA') => call('POST', '/api/invites', { player: id, to, game: 'pilkki', version: 2, room });
  assert.equal((await inv(A, PB)).status, 403);
  await ask(A, PB); await answer(B, PA, true);
  assert.equal((await inv(A, PB, 'kisa')).status, 400);
  assert.equal((await inv(A, PB)).status, 200);
  assert.equal((await inv(A, PB, 'LAMA')).status, 200);
  const got = (await call('POST', '/api/presence', { player: B })).body.invites;
  assert.equal(got.length, 1);
  assert.deepEqual({ ...got[0], id: 0 }, { id: 0, from: PA, name: 'Aino', game: 'pilkki', version: 2, room: 'LAMA' });
  // Someone else cannot answer it.
  await call('POST', `/api/invites/${got[0].id}/answer`, { player: C });
  assert.equal((await state(B)).invites.length, 1);
  await call('POST', `/api/invites/${got[0].id}/answer`, { player: B });
  assert.deepEqual((await state(B)).invites, []);
  await inv(A, PB);
  env.DB.raw.prepare('UPDATE invites SET at = ?').run(new Date(Date.now() - 11 * 60e3).toISOString());
  assert.deepEqual((await state(B)).invites, []);
});

test('a declined request goes away after a week, and can then be asked again', async () => {
  const { player, state, ask, answer, env } = setup();
  await player(A, 'Aino'); await player(B, 'Bertta');
  await ask(A, PB); await answer(B, PA, false);
  env.DB.raw.prepare('UPDATE friend_requests SET at = ?').run(new Date(Date.now() - 8 * 864e5).toISOString());
  assert.deepEqual((await state(A)).asked, []);
  await ask(A, PB);
  assert.deepEqual((await state(B)).requests, [{ pid: PA, name: 'Aino' }]);
});

test('accepting twice at once, or answering a request already answered, is harmless', async () => {
  const { player, state, ask, answer } = setup();
  await player(A, 'Aino'); await player(B, 'Bertta');
  await ask(A, PB);
  const both = await Promise.all([answer(B, PA, true), answer(B, PA, true)]);
  assert.ok(both.some((r) => r.status === 200));
  assert.ok(both.every((r) => r.status === 200 || r.status === 404));
  assert.deepEqual((await state(A)).friends.map((f) => f.name), ['Bertta']);
  assert.equal((await answer(B, PA, false)).status, 404);
  assert.deepEqual((await state(A)).friends.map((f) => f.name), ['Bertta']);
});
