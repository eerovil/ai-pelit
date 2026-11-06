import test from 'node:test';
import assert from 'node:assert/strict';
import { handle } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

test('Frisbeegolf accepts under-par rounds and keeps the lowest score on its main board', async () => {
  const env = { DB: makeD1(), ADMIN_KEY: 'test' }, player = 'f'.repeat(32);
  const call = async (method, path, body) => {
    const result = await handle(new Request('https://pelit.test/api/' + path, {
      method, headers: { 'content-type': 'application/json' },
      ...(body ? { body: JSON.stringify(body) } : {}),
    }), env);
    return { status: result.status, body: await result.json() };
  };
  await call('POST', 'players', { id: player, name: 'Testi338' });
  const score = { player, game: 'frisbeegolf', board: 'main', version: 1 };
  for (const n of [5, 0, -2, 1]) assert.equal((await call('POST', 'scores', { ...score, score: n })).status, 200);
  const list = await call('GET', 'scores?game=frisbeegolf&player=' + player);
  assert.equal(list.body.mine.score, -2);
  assert.equal((await call('POST', 'scores', { ...score, board: 'other', score: -3 })).status, 400);
});
