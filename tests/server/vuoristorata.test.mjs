import test from 'node:test';
import assert from 'node:assert/strict';
import { handle } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

function setup() {
  const env = { DB: makeD1(), ADMIN_KEY: 'test' };
  const call = async (method, path, body) => {
    const response = await handle(new Request('https://pelit.test/api/' + path, {
      method, headers: { 'content-type': 'application/json' }, ...(body ? { body: JSON.stringify(body) } : {}),
    }), env);
    return { status: response.status, body: await response.json() };
  };
  return { env, call };
}

test('Vuoristorata keeps old low times and ranks v5 thrill points high', async () => {
  const { env, call } = setup(), a = 'a'.repeat(32), b = 'b'.repeat(32);
  for (const [id, name] of [[a, 'Testi459A'], [b, 'Testi459B']]) {
    await call('POST', 'players', { id, name });
    env.DB.raw.prepare("UPDATE players SET status='approved' WHERE id=?").run(id);
  }
  const old = { game: 'vuoristorata', board: 'taso-1', version: 4 };
  assert.equal((await call('POST', 'scores', { ...old, player: a, score: 70 })).status, 200);
  assert.equal((await call('POST', 'scores', { ...old, player: a, score: 65 })).status, 200);
  assert.equal((await call('GET', 'scores?game=vuoristorata&board=taso-1&player=' + a)).body.mine.score, 65);

  const fresh = { game: 'vuoristorata', board: 'elamys-1', version: 5 };
  assert.equal((await call('POST', 'scores', { ...fresh, player: a, score: 420 })).status, 200);
  assert.equal((await call('POST', 'scores', { ...fresh, player: a, score: 510 })).status, 200);
  assert.equal((await call('POST', 'scores', { ...fresh, player: b, score: 480 })).status, 200);
  const list = await call('GET', 'scores?game=vuoristorata&board=elamys-1&player=' + a);
  assert.deepEqual(list.body.rows.map(r => r.score), [510, 480]);
  assert.equal((await call('GET', 'scores/top')).body.games.vuoristorata.score, 510);
  assert.equal((await call('GET', 'scores/top')).body.games.vuoristorata.board, 'elamys-1');

  for (const body of [
    { ...old, player: a, version: 5, score: 60 },
    { ...fresh, player: a, version: 4, score: 999 },
  ]) {
    const response = await call('POST', 'scores', body);
    assert.equal(response.status, 400);
    assert.equal(response.body.error, 'wrong version for this board');
  }

  const malformed = await call('POST', 'scores', { ...fresh, player: a, board: ['elamys-1'], score: 999 });
  assert.equal(malformed.status, 400);
  assert.equal(malformed.body.error, 'bad board');
});
