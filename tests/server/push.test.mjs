// Invites as phone notifications (#367): server/api.js on SQLite with the migrations, the push
// services stubbed.
import test from 'node:test';
import assert from 'node:assert/strict';
import { handle, pidOf, pushEndpoint, PUSH_TTL, PUSH_PER_PLAYER, VAPID_PUBLIC } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

const A = 'a'.repeat(32), B = 'b'.repeat(32);
const PA = await pidOf(A), PB = await pidOf(B);
const FCM = 'https://fcm.googleapis.com/fcm/send/abc123';
const APPLE = 'https://web.push.apple.com/QGx-yz';

const b64url = (b) => Buffer.from(b).toString('base64url');

// A key pair of the tests' own, as VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY.
async function vapidPair() {
  const pair = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  const jwk = await crypto.subtle.exportKey('jwk', pair.privateKey);
  const raw = new Uint8Array(await crypto.subtle.exportKey('raw', pair.publicKey));
  return { d: jwk.d, pub: b64url(raw), verify: pair.publicKey };
}

async function setup({ vapid = true } = {}) {
  const keys = await vapidPair();
  const env = { DB: makeD1(), ADMIN_KEY: 'avain' };
  if (vapid) Object.assign(env, { VAPID_PRIVATE_KEY: keys.d, VAPID_PUBLIC_KEY: keys.pub });
  const call = async (method, path, body, ctx) => {
    const init = { method, headers: { 'content-type': 'application/json' } };
    if (body !== undefined) init.body = JSON.stringify(body);
    const res = await handle(new Request('https://pelit.test' + path, init), env, ctx);
    return { status: res.status, body: await res.json() };
  };
  // Aino and Bertta, friends.
  await call('POST', '/api/players', { id: A, name: 'Aino' });
  await call('POST', '/api/players', { id: B, name: 'Bertta' });
  await call('POST', '/api/friends/requests', { player: A, to: PB });
  await call('POST', '/api/friends/requests/answer', { player: B, from: PA, yes: true });
  return { env, call, keys };
}

// Every push the server sends, answered with `status`.
function stubPush(status = 201) {
  const sent = [], real = globalThis.fetch;
  globalThis.fetch = async (url, init) => { sent.push({ url: String(url), init }); return new Response(null, { status: typeof status === 'function' ? status(String(url)) : status }); };
  return { sent, restore: () => { globalThis.fetch = real; } };
}

const inviteB = (call, ctx) => call('POST', '/api/invites', { player: A, to: PB, game: 'pilkki', version: 4, room: 'ABCD' }, ctx);

test('only the browsers\' push services are taken as endpoints', () => {
  assert.equal(pushEndpoint(FCM), FCM);
  assert.equal(pushEndpoint(APPLE), APPLE);
  assert.equal(pushEndpoint('https://updates.push.services.mozilla.com/wpush/v2/x'), 'https://updates.push.services.mozilla.com/wpush/v2/x');
  for (const bad of ['http://fcm.googleapis.com/x', 'https://evil.test/x', 'https://fcm.googleapis.com.evil.test/x',
    'https://fcm.googleapis.com:8443/x', 'nope', 42, 'https://fcm.googleapis.com/' + 'x'.repeat(1000)]) {
    assert.equal(pushEndpoint(bad), '', String(bad));
  }
  assert.match(VAPID_PUBLIC, /^B[A-Za-z0-9_-]{86}$/);
});

test('a phone subscribes, and pending tells its service worker the newest invite', async () => {
  const { call } = await setup({ vapid: false });
  assert.equal((await call('POST', '/api/push', { player: B, endpoint: 'https://evil.test/x' })).status, 400);
  assert.equal((await call('POST', '/api/push', { player: 'c'.repeat(32), endpoint: FCM })).status, 404);
  assert.deepEqual((await call('POST', '/api/push', { player: B, endpoint: FCM })).body, { ok: true });
  const pending = () => call('GET', '/api/push/pending?endpoint=' + encodeURIComponent(FCM));
  assert.deepEqual((await pending()).body, { invite: null });
  await inviteB(call);
  const inv = (await pending()).body.invite;
  assert.deepEqual({ ...inv, id: 0 }, { id: 0, name: 'Aino', title: 'pilkki', url: 'games/pilkki/v4/?huone=ABCD' });
  // An unknown endpoint learns nothing.
  assert.deepEqual((await call('GET', '/api/push/pending?endpoint=' + encodeURIComponent(APPLE))).body, { invite: null });
  // Tapping the notification answers the invite by the endpoint: it no longer shows anywhere.
  assert.equal((await call('POST', `/api/invites/${inv.id}/answer`, { endpoint: FCM })).status, 200);
  assert.deepEqual((await pending()).body, { invite: null });
  assert.deepEqual((await call('GET', `/api/friends?player=${B}`)).body.invites, []);
  // Switched off: gone.
  await inviteB(call);
  assert.deepEqual((await call('DELETE', '/api/push', { player: B, endpoint: FCM })).body, { ok: true });
  assert.deepEqual((await pending()).body, { invite: null });
});

test('an invite sends an empty push signed with VAPID to each of the friend\'s phones', async () => {
  const { call, keys } = await setup();
  await call('POST', '/api/push', { player: B, endpoint: FCM });
  await call('POST', '/api/push', { player: B, endpoint: APPLE });
  await call('POST', '/api/push', { player: A, endpoint: 'https://fcm.googleapis.com/fcm/send/aino' });
  const push = stubPush();
  try {
    const later = [];
    const res = await inviteB(call, { waitUntil: (p) => later.push(p) });
    assert.deepEqual(res.body, { ok: true });
    assert.equal(later.length, 1, 'the push goes on after the answer');
    await Promise.all(later);
  } finally {
    push.restore();
  }
  assert.deepEqual(push.sent.map((s) => s.url).sort(), [APPLE, FCM].sort());
  for (const { url, init } of push.sent) {
    assert.equal(init.method, 'POST');
    assert.equal(init.body, undefined);
    assert.equal(init.headers.ttl, String(PUSH_TTL));
    const m = init.headers.authorization.match(/^vapid t=([^.]+)\.([^.]+)\.([^,]+), k=(.+)$/);
    assert.ok(m, init.headers.authorization);
    assert.equal(m[4], keys.pub);
    assert.deepEqual(JSON.parse(Buffer.from(m[1], 'base64url')), { typ: 'JWT', alg: 'ES256' });
    const claims = JSON.parse(Buffer.from(m[2], 'base64url'));
    assert.equal(claims.aud, new URL(url).origin);
    assert.ok(claims.exp > Date.now() / 1000 && claims.exp <= Date.now() / 1000 + 24 * 3600);
    assert.match(claims.sub, /^https:\/\//);
    const ok = await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, keys.verify,
      Buffer.from(m[3], 'base64url'), new TextEncoder().encode(`${m[1]}.${m[2]}`));
    assert.ok(ok, 'the signature checks with the public key');
  }
});

test('a phone the push service says is gone (404, 410) is forgotten; others are kept', async () => {
  const { call } = await setup();
  const gone = 'https://fcm.googleapis.com/fcm/send/gone', lost = 'https://fcm.googleapis.com/fcm/send/lost';
  for (const e of [FCM, gone, lost]) await call('POST', '/api/push', { player: B, endpoint: e });
  const push = stubPush((u) => (u === gone ? 410 : u === lost ? 404 : 500));
  try {
    assert.deepEqual((await inviteB(call)).body, { ok: true });
  } finally {
    push.restore();
  }
  const pending = async (e) => (await call('GET', '/api/push/pending?endpoint=' + encodeURIComponent(e))).body.invite;
  assert.ok(await pending(FCM), 'a 500 keeps the phone');
  assert.equal(await pending(gone), null);
  assert.equal(await pending(lost), null);
});

test('a failing push service or no key never fails the invite', async () => {
  const { call } = await setup();
  await call('POST', '/api/push', { player: B, endpoint: FCM });
  const real = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('down'); };
  const err = console.error;
  console.error = () => {};
  try {
    assert.deepEqual((await inviteB(call)).body, { ok: true });
  } finally {
    globalThis.fetch = real;
    console.error = err;
  }
  const none = await setup({ vapid: false });
  await none.call('POST', '/api/push', { player: B, endpoint: FCM });
  const push = stubPush();
  try {
    assert.deepEqual((await inviteB(none.call)).body, { ok: true });
  } finally {
    push.restore();
  }
  assert.equal(push.sent.length, 0);
});

test('a player keeps its newest few phones', async () => {
  const { call, env } = await setup({ vapid: false });
  for (let i = 0; i < PUSH_PER_PLAYER + 2; i++) {
    await call('POST', '/api/push', { player: B, endpoint: `https://fcm.googleapis.com/fcm/send/p${i}` });
    await new Promise((r) => setTimeout(r, 2));
  }
  const rows = env.DB.raw.prepare('SELECT endpoint FROM push_subs WHERE player = ? ORDER BY at').all(B).map((r) => r.endpoint);
  assert.equal(rows.length, PUSH_PER_PLAYER);
  assert.equal(rows.at(-1), `https://fcm.googleapis.com/fcm/send/p${PUSH_PER_PLAYER + 1}`);
  // An endpoint moving to another player (the phone's player id changed) goes with it.
  await call('POST', '/api/push', { player: A, endpoint: rows[0] });
  assert.equal(env.DB.raw.prepare('SELECT player FROM push_subs WHERE endpoint = ?').get(rows[0]).player, A);
});

test('two invites at once: pending names the newest; an old one or one already answered, none', async () => {
  const { call, env } = await setup({ vapid: false });
  const C = 'c'.repeat(32), PC = await pidOf(C);
  await call('POST', '/api/players', { id: C, name: 'Ceci' });
  await call('POST', '/api/friends/requests', { player: C, to: PB });
  await call('POST', '/api/friends/requests/answer', { player: B, from: PC, yes: true });
  await call('POST', '/api/push', { player: B, endpoint: FCM });
  const pending = async () => (await call('GET', '/api/push/pending?endpoint=' + encodeURIComponent(FCM))).body.invite;
  await inviteB(call);
  await call('POST', '/api/invites', { player: C, to: PB, game: 'kirkkis', version: 9, room: 'WXYZ' });
  const newest = await pending();
  assert.deepEqual([newest.name, newest.url], ['Ceci', 'games/kirkkis/v9/?huone=WXYZ']);
  // Answered on the phone's banner before the push arrived: the older one is shown instead.
  await call('POST', `/api/invites/${newest.id}/answer`, { player: B });
  assert.equal((await pending()).name, 'Aino');
  // A tap on a notification whose invite is already gone changes nothing and fails nothing.
  assert.equal((await call('POST', `/api/invites/${newest.id}/answer`, { endpoint: FCM })).status, 200);
  assert.equal((await call('POST', '/api/invites/1/answer', { endpoint: 'https://fcm.googleapis.com/fcm/send/nobody' })).status, 200);
  // Past its ten minutes, nothing.
  env.DB.raw.prepare('UPDATE invites SET at = ?').run(new Date(Date.now() - 11 * 60e3).toISOString());
  assert.equal(await pending(), null);
});
