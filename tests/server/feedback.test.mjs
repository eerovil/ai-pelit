// Feedback on the games (#184): server/api.js on SQLite with the migrations.
import test from 'node:test';
import assert from 'node:assert/strict';
import { handle, FEEDBACK_MAX, FEEDBACK_PER_DAY, cleanText } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

const ADMIN_KEY = 'avain';
const A = 'a'.repeat(32), B = 'b'.repeat(32);
const ADMIN = { 'x-admin-key': ADMIN_KEY };

function setup() {
  const env = { DB: makeD1(), ADMIN_KEY };
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
  return { env, call, player };
}

test('only an approved nickname may write feedback', async () => {
  const { call, player } = setup();
  const send = (id) => call('POST', '/api/feedback', { player: id, game: 'hiihto', version: 9, text: 'Liian vaikea rata 3' });
  assert.equal((await send(A)).status, 403); // no name at all
  await player(A, 'Aino');
  assert.equal((await send(A)).status, 403); // waiting
  await player(B, 'Bertta', 'rejected');
  assert.equal((await send(B)).status, 403);
  await call('POST', '/api/admin/players', { id: A, name: 'Aino', status: 'approved' }, ADMIN);
  assert.deepEqual((await send(A)).body, { ok: true });
  // A changed name waits again, and so does its feedback.
  await call('POST', '/api/players', { id: A, name: 'Aino2' });
  assert.equal((await send(A)).status, 403);
});

test('the admin reads it, and the daily check files it once', async () => {
  const { call, player } = setup();
  await player(A, 'Aino', 'approved');
  await call('POST', '/api/feedback', { player: A, game: 'hiihto', version: 9, text: 'Eka' });
  await call('POST', '/api/feedback', { player: A, game: 'piano', text: '  Toka\r\n\r\n\r\nrivi  ' });
  assert.equal((await call('GET', '/api/admin/feedback')).status, 403);
  let fresh = (await call('GET', '/api/admin/feedback?new=1', undefined, ADMIN)).body.feedback;
  assert.deepEqual(fresh.map((f) => [f.name, f.game, f.version, f.text, f.issue]),
    [['Aino', 'hiihto', 9, 'Eka', null], ['Aino', 'piano', null, 'Toka\n\nrivi', null]]);
  // No player id is ever sent, not even to the admin.
  assert.equal(JSON.stringify(fresh).includes(A), false);
  assert.equal((await call('POST', '/api/admin/feedback', { ids: [fresh[0].id], issue: 190 })).status, 403);
  assert.equal((await call('POST', '/api/admin/feedback', { ids: [fresh[0].id], issue: 190 }, ADMIN)).status, 200);
  assert.equal((await call('POST', '/api/admin/feedback', { ids: ['x'], issue: 190 }, ADMIN)).status, 400);
  fresh = (await call('GET', '/api/admin/feedback?new=1', undefined, ADMIN)).body.feedback;
  assert.deepEqual(fresh.map((f) => f.text), ['Toka\n\nrivi']);
  // Filed once: a second issue does not take it over.
  const all = (await call('GET', '/api/admin/feedback', undefined, ADMIN)).body.feedback;
  await call('POST', '/api/admin/feedback', { ids: all.map((f) => f.id), issue: 191 }, ADMIN);
  const issues = (await call('GET', '/api/admin/feedback', undefined, ADMIN)).body.feedback.map((f) => [f.text, f.issue]);
  assert.deepEqual(issues, [['Toka\n\nrivi', 191], ['Eka', 190]]);
});

test('feedback is 1 to 1000 characters, about a real game, and limited per day', async () => {
  const { env, call, player } = setup();
  await player(A, 'Aino', 'approved');
  const send = (body) => call('POST', '/api/feedback', { player: A, game: 'hiihto', text: 'ok', ...body });
  assert.equal((await send({ text: '   ' })).status, 400);
  assert.equal((await send({ text: 'x'.repeat(FEEDBACK_MAX + 1) })).status, 400);
  assert.equal((await send({ text: '😀'.repeat(FEEDBACK_MAX) })).status, 200);
  assert.equal((await send({ game: 'Ei peli' })).status, 400);
  assert.equal((await send({ version: 0 })).status, 400);
  // With the site's catalog, only its games and versions.
  env.ASSETS = { fetch: async () => new Response(JSON.stringify({ games: [{ slug: 'hiihto', versions: [{ n: 1 }, { n: 2 }] }] })) };
  assert.equal((await send({ game: 'keksitty' })).status, 404);
  assert.equal((await send({ version: 3 })).status, 404);
  assert.equal((await send({ version: 2 })).status, 200);
  delete env.ASSETS;
  for (let i = 2; i < FEEDBACK_PER_DAY; i++) assert.equal((await send({})).status, 200);
  assert.equal((await send({})).status, 429);
});

test('cleanText keeps line breaks and drops control characters', () => {
  assert.equal(cleanText(' a\u0007b \t c\n\n\n\nd '), 'ab c\n\nd');
  assert.equal(cleanText(42), '');
});
