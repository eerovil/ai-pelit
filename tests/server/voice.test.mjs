// GET /api/voice/ice (#322): the servers a phone's voice call may use, and the monthly cap on the
// TURN relay. node --test tests/server/
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeD1 } from './d1.mjs';

const { handle, STUN, TURN_CAP, TURN_STALE, forgetTurn } = await import('../../server/api.js');

const ADMIN = 'k'.repeat(24);
const req = (path, init = {}) => new Request(`https://pelit.test${path}`, init);
const ice = (env, headers = { 'sec-fetch-site': 'same-origin' }) => handle(req('/api/voice/ice', { headers }), env);
const usage = (env, body, key = ADMIN) => handle(req('/api/admin/turn-usage', {
  method: 'POST', headers: { 'x-admin-key': key, 'content-type': 'application/json' }, body: JSON.stringify(body),
}), env);
const month = () => new Date().toISOString().slice(0, 7);
const SERVERS = [{ urls: ['stun:stun.cloudflare.com:3478'] }, { urls: ['turn:turn.cloudflare.com:3478?transport=udp'], username: 'u', credential: 'c' }];

function turnEnv(t) {
  forgetTurn();
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({ iceServers: SERVERS }), { status: 201 });
  });
  return { env: { DB: makeD1(), ADMIN_KEY: ADMIN, TURN_KEY_ID: 'kid', TURN_KEY_TOKEN: 'tok' }, calls };
}

test('without the TURN key only the public STUN server is given', async () => {
  forgetTurn();
  const res = await ice({}, { 'sec-fetch-site': 'same-origin' });
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { iceServers: [STUN] });
});

test('another site\'s page is refused, and only GET is taken', async () => {
  assert.equal((await ice({}, { 'sec-fetch-site': 'cross-site' })).status, 403);
  assert.equal((await handle(req('/api/voice/ice', { method: 'POST' }), {})).status, 405);
});

test('under the month\'s cap, Cloudflare\'s credentials are asked for once in a while and passed on', async (t) => {
  const { env, calls } = turnEnv(t);
  assert.deepEqual(await (await usage(env, { month: month(), bytes: 5e9 })).json(), { ok: true });
  assert.deepEqual(await (await ice(env)).json(), { iceServers: SERVERS });
  assert.deepEqual(await (await ice(env)).json(), { iceServers: SERVERS });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://rtc.live.cloudflare.com/v1/turn/keys/kid/credentials/generate-ice-servers');
  assert.equal(calls[0].init.headers.authorization, 'Bearer tok');
  assert.equal(JSON.parse(calls[0].init.body).ttl, 2 * 3600);
});

test('at the cap, with no check this month, or a check too old, only STUN is given', async (t) => {
  const { env, calls } = turnEnv(t);
  assert.deepEqual(await (await ice(env)).json(), { iceServers: [STUN] }); // never checked
  forgetTurn();
  await usage(env, { month: month(), bytes: TURN_CAP });
  assert.deepEqual(await (await ice(env)).json(), { iceServers: [STUN] });
  forgetTurn();
  const old = new Date(Date.now() - TURN_STALE - 1000).toISOString();
  await env.DB.prepare('UPDATE turn_usage SET bytes = 1, checked_at = ? WHERE month = ?').bind(old, month()).run();
  assert.deepEqual(await (await ice(env)).json(), { iceServers: [STUN] });
  assert.equal(calls.length, 0);
});

test('the usage is written only with the admin key, and only as a month and a whole number', async (t) => {
  const { env } = turnEnv(t);
  assert.equal((await usage(env, { month: month(), bytes: 1 }, 'wrong')).status, 403);
  assert.equal((await usage(env, { month: 'nov', bytes: 1 })).status, 400);
  assert.equal((await usage(env, { month: month(), bytes: -1 })).status, 400);
  assert.equal((await usage(env, { month: month(), bytes: 1.5 })).status, 400);
  await usage(env, { month: month(), bytes: 7 });
  await usage(env, { month: month(), bytes: 9 });
  const row = await env.DB.prepare('SELECT bytes FROM turn_usage WHERE month = ?').bind(month()).first();
  assert.equal(row.bytes, 9);
});

test('when Cloudflare does not answer, the STUN server is still given', async (t) => {
  const { env } = turnEnv(t);
  await usage(env, { month: month(), bytes: 0 });
  t.mock.method(globalThis, 'fetch', async () => { throw new Error('offline'); });
  t.mock.method(console, 'error', () => {});
  assert.deepEqual(await (await ice(env)).json(), { iceServers: [STUN] });
});

test('relay credentials go only to this site\'s own pages; anything else gets STUN alone', async (t) => {
  const { env, calls } = turnEnv(t);
  await usage(env, { month: month(), bytes: 0 });
  for (const headers of [{}, { 'sec-fetch-site': 'none' }, { 'sec-fetch-site': 'same-site' }]) {
    const res = await ice(env, headers);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { iceServers: [STUN] }, JSON.stringify(headers));
  }
  assert.equal((await ice(env, { 'sec-fetch-site': 'cross-site' })).status, 403);
  assert.equal(calls.length, 0);
  assert.deepEqual(await (await ice(env)).json(), { iceServers: SERVERS });
});
