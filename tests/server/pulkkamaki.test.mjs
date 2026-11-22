import test from 'node:test';
import assert from 'node:assert/strict';
import { handle } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

function setup() {
  const env = { DB: makeD1(), ADMIN_KEY: 'test' };
  const call = async (method, path, body) => {
    const result = await handle(new Request('https://pelit.test/api/' + path, {
      method, headers: { 'content-type': 'application/json' },
      ...(body ? { body: JSON.stringify(body) } : {}),
    }), env);
    return { status: result.status, body: await result.json() };
  };
  return { env, call };
}

// Pulkkamäki v4 (#517) adds two hills, each with its own list, and v6 two more: maki-1 to maki-7, nothing past them.
test('Pulkkamäki takes a score on each of its seven hills', async () => {
  const { call } = setup(), player = 'e'.repeat(32);
  await call('POST', 'players', { id: player, name: 'Testi517' });
  const score = { player, game: 'pulkkamaki', version: 4, score: 1200 };
  for (let n = 1; n <= 7; n++) {
    assert.equal((await call('POST', 'scores', { ...score, board: 'maki-' + n })).status, 200, 'maki-' + n);
    assert.equal((await call('GET', 'scores?game=pulkkamaki&board=maki-' + n + '&player=' + player)).body.mine.score, 1200);
  }
  for (const board of ['maki-0', 'maki-8', 'main']) {
    assert.equal((await call('POST', 'scores', { ...score, board })).status, 400, board);
  }
});
