// GET /api/voice/ice (#322): the servers a phone's voice call may use. node --test tests/server/
import test from 'node:test';
import assert from 'node:assert/strict';

const { handle, STUN, forgetTurn } = await import('../../server/api.js');

const get = (headers = {}) => handle(new Request('https://pelit.test/api/voice/ice', { headers }), {});
const ice = (env, headers = {}) => handle(new Request('https://pelit.test/api/voice/ice', { headers }), env);

test('without the TURN key only the public STUN server is given', async () => {
  const res = await get({ 'sec-fetch-site': 'same-origin' });
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { iceServers: [STUN] });
});

test('another site\'s page is refused, and only GET is taken', async () => {
  assert.equal((await get({ 'sec-fetch-site': 'cross-site' })).status, 403);
  const post = await handle(new Request('https://pelit.test/api/voice/ice', { method: 'POST' }), {});
  assert.equal(post.status, 405);
});

test('with the TURN key, Cloudflare\'s credentials are asked for once an hour and passed on', async (t) => {
  forgetTurn();
  const calls = [];
  const servers = [{ urls: ['stun:stun.cloudflare.com:3478'] }, { urls: ['turn:turn.cloudflare.com:3478?transport=udp'], username: 'u', credential: 'c' }];
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({ iceServers: servers }), { status: 201 });
  });
  const env = { TURN_KEY_ID: 'kid', TURN_KEY_TOKEN: 'tok' };
  assert.deepEqual(await (await ice(env)).json(), { iceServers: servers });
  assert.deepEqual(await (await ice(env)).json(), { iceServers: servers });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://rtc.live.cloudflare.com/v1/turn/keys/kid/credentials/generate-ice-servers');
  assert.equal(calls[0].init.headers.authorization, 'Bearer tok');
  assert.equal(JSON.parse(calls[0].init.body).ttl, 4 * 3600);
});

test('when Cloudflare does not answer, the STUN server is still given', async (t) => {
  forgetTurn();
  t.mock.method(globalThis, 'fetch', async () => { throw new Error('offline'); });
  t.mock.method(console, 'error', () => {});
  const res = await ice({ TURN_KEY_ID: 'kid', TURN_KEY_TOKEN: 'tok' });
  assert.deepEqual(await res.json(), { iceServers: [STUN] });
});
