import test from 'node:test';
import assert from 'node:assert/strict';
import { handle } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

// Yöajo v15 (#440) drives on into Lapland: legs 10 and 11 get their own lists ('osa-10', 'osa-11').
test('Yöajo takes a score on each of its eleven legs and no other', async () => {
  const env = { DB: makeD1(), ADMIN_KEY: 'test' };
  const call = async (method, path, body) => {
    const r = await handle(new Request('https://pelit.test/api/' + path, {
      method, headers: { 'content-type': 'application/json' }, ...(body ? { body: JSON.stringify(body) } : {}),
    }), env);
    return { status: r.status, body: await r.json() };
  };
  const player = 'e'.repeat(32);
  await call('POST', 'players', { id: player, name: 'Testi440' });
  for (const board of ['osa-1', 'osa-9', 'osa-10', 'osa-11']) {
    assert.equal((await call('POST', 'scores', { player, game: 'yoajo', board, version: 15, score: 500 })).status, 200, board);
  }
  for (const board of ['osa-0', 'osa-12', 'osa-19', 'main']) {
    assert.equal((await call('POST', 'scores', { player, game: 'yoajo', board, version: 15, score: 500 })).status, 400, board);
  }
  assert.equal((await call('GET', 'scores?game=yoajo&board=osa-11&player=' + player)).body.mine.score, 500);
});
