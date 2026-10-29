// /api/plays checks each count against the site's catalog.json. Its own file, so its process
// starts with no catalog read yet, as a cold Cloudflare isolate does.
import test from 'node:test';
import assert from 'node:assert/strict';
import { handle } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

test('plays: only games and versions in the site catalog count, and none without a catalog', async () => {
  const catalog = { games: [{ slug: 'hiihto', versions: [{ n: 1 }, { n: 2 }] }] };
  let assets = 'down';
  const env = {
    DB: makeD1(),
    ASSETS: {
      fetch: async () => {
        if (assets === 'throws') throw new Error('no assets');
        return assets === 'down' ? new Response('', { status: 500 }) : new Response(JSON.stringify(catalog));
      },
    },
  };
  const call = async (method, body) => {
    const init = { method, headers: { 'content-type': 'application/json' } };
    if (body) init.body = JSON.stringify(body);
    const res = await handle(new Request('https://pelit.test/api/plays', init), env);
    return { status: res.status, body: await res.json() };
  };

  // Cold, and the catalog does not load: nothing is counted.
  assert.equal((await call('POST', { game: 'keksitty', version: 1 })).status, 503);
  assets = 'throws';
  assert.equal((await call('POST', { game: 'hiihto', version: 1 })).status, 503);
  assert.deepEqual((await call('GET')).body, { games: {} });

  assets = 'up';
  assert.equal((await call('POST', { game: 'hiihto', version: 2 })).status, 200);
  assert.equal((await call('POST', { game: 'hiihto', version: 3 })).status, 404);
  assert.equal((await call('POST', { game: 'keksitty', version: 1 })).status, 404);
  assert.deepEqual((await call('GET')).body, { games: { hiihto: 1 } });
});
