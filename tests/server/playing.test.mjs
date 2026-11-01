// Who is playing right now (#325): back.js says an open game page is still there, the shelf
// reads how many per game.
import test from 'node:test';
import assert from 'node:assert/strict';
import { handle, PLAYING_NOW } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

function setup(env = {}) {
  env = { DB: makeD1(), ...env };
  const call = async (method, body) => {
    const init = { method, headers: { 'content-type': 'application/json' } };
    if (body !== undefined) init.body = typeof body === 'string' ? body : JSON.stringify(body);
    const res = await handle(new Request('https://pelit.test/api/playing', init), env);
    return { status: res.status, body: await res.json() };
  };
  return { env, call };
}

test('playing: each open page counts once, and leaving takes it off at once', async () => {
  const { call } = setup();
  for (const id of ['sivu00001', 'sivu00002', 'sivu00001']) {
    assert.deepEqual((await call('POST', { id, game: 'hiihto' })).body, { ok: true });
  }
  await call('POST', { id: 'sivu00003', game: 'kirkkis' });
  assert.deepEqual((await call('GET')).body, { games: { hiihto: 2, kirkkis: 1 } });
  assert.deepEqual((await call('POST', { id: 'sivu00002', gone: true })).body, { ok: true });
  assert.deepEqual((await call('GET')).body, { games: { hiihto: 1, kirkkis: 1 } });
});

test('playing: a page not heard from lately is no longer counted, and old rows are deleted', async () => {
  const { env, call } = setup();
  await call('POST', { id: 'vanhasivu', game: 'hiihto' });
  await call('POST', { id: 'tuoresivu', game: 'hiihto' });
  env.DB.raw.prepare('UPDATE playing SET seen = ? WHERE id = ?').run(Date.now() - PLAYING_NOW - 1000, 'vanhasivu');
  assert.deepEqual((await call('GET')).body, { games: { hiihto: 1 } });
  env.DB.raw.prepare('UPDATE playing SET seen = ? WHERE id = ?').run(Date.now() - 11 * 60e3, 'vanhasivu');
  await call('POST', { id: 'tuoresivu', game: 'hiihto' });
  assert.deepEqual(env.DB.raw.prepare('SELECT id FROM playing').all().map((r) => r.id), ['tuoresivu']);
  // Nothing about the phone is kept: the random page id, the game and when it was heard from.
  assert.deepEqual(Object.keys(env.DB.raw.prepare('SELECT * FROM playing').get()).sort(), ['game', 'id', 'seen']);
});

test('playing: a bad id, a bad game or a game the site does not have is refused', async () => {
  const catalog = { games: [{ slug: 'hiihto', versions: [{ n: 1 }] }] };
  const { call } = setup({ ASSETS: { fetch: async () => new Response(JSON.stringify(catalog)) } });
  assert.equal((await call('POST', { id: 'lyhyt', game: 'hiihto' })).status, 400);
  assert.equal((await call('POST', { id: 'ISOJAKIRJAIMIA', game: 'hiihto' })).status, 400);
  assert.equal((await call('POST', { id: 'sivu00001', game: 'Hiihto!' })).status, 400);
  assert.equal((await call('POST', { id: 'sivu00001', game: 'keksitty' })).status, 404);
  assert.equal((await call('POST', 'not json')).status, 400);
  assert.equal((await call('POST', { id: 'sivu00001', game: 'hiihto' })).status, 200);
  assert.deepEqual((await call('GET')).body, { games: { hiihto: 1 } });
});
