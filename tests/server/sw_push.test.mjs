// Invites as phone notifications (#367): public/sw.js's push and notificationclick handlers, run
// in a stand-in for the service worker's global scope.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const SCOPE = 'https://pelit.test/';
const ENDPOINT = 'https://fcm.googleapis.com/fcm/send/testi';
const SOURCE = readFileSync(new URL('../../public/sw.js', import.meta.url), 'utf8');

function worker({ invite = null, subscribed = true, windows = [] } = {}) {
  const handlers = {}, shown = [], fetched = [], opened = [];
  const self = {
    addEventListener: (type, fn) => { handlers[type] = fn; },
    registration: {
      scope: SCOPE,
      pushManager: { getSubscription: async () => (subscribed ? { endpoint: ENDPOINT } : null) },
      showNotification: async (title, options) => { shown.push({ title, options }); },
    },
    clients: {
      matchAll: async () => windows,
      openWindow: async (url) => { opened.push(url); return null; },
    },
  };
  const fetch = async (url, init) => {
    fetched.push({ url: String(url), init });
    return new Response(JSON.stringify(String(url).includes('pending') ? { invite } : { ok: true }), { status: 200 });
  };
  vm.runInNewContext(SOURCE, { self, fetch, URL, Response, Promise, JSON, encodeURIComponent, caches: {}, console });
  // Runs one event and waits for everything it handed to waitUntil.
  const fire = async (type, extra = {}) => {
    const jobs = [];
    handlers[type]({ waitUntil: (p) => jobs.push(p), ...extra });
    await Promise.all(jobs);
  };
  return { fire, shown, fetched, opened };
}

const INVITE = { id: 7, name: 'Aino', title: 'Pilkkiminen', url: 'games/pilkki/v4/?huone=ABCD' };

test('a push shows the newest invite, asked for by this phone\'s endpoint', async () => {
  const w = worker({ invite: INVITE });
  await w.fire('push');
  assert.equal(w.fetched[0].url, '/api/push/pending?endpoint=' + encodeURIComponent(ENDPOINT));
  assert.equal(w.shown.length, 1);
  assert.equal(w.shown[0].title, 'Aino kutsuu sinut pelaamaan: Pilkkiminen');
  assert.equal(JSON.stringify(w.shown[0].options.actions.map((a) => a.title)), '["Liity"]');
  assert.equal(w.shown[0].options.data.url, SCOPE + 'games/pilkki/v4/?huone=ABCD');
});

test('with nothing open, or no subscription, nothing shows', async () => {
  const none = worker();
  await none.fire('push');
  assert.equal(none.shown.length, 0);
  const off = worker({ invite: INVITE, subscribed: false });
  await off.fire('push');
  assert.deepEqual([off.shown.length, off.fetched.length], [0, 0]);
});

test('a tap answers the invite and opens the room\'s game', async () => {
  const w = worker();
  let closed = false;
  const notification = { data: { id: 7, url: SCOPE + 'games/pilkki/v4/?huone=ABCD' }, close: () => { closed = true; } };
  await w.fire('notificationclick', { notification, action: 'liity' });
  assert.ok(closed);
  assert.deepEqual(w.opened, [SCOPE + 'games/pilkki/v4/?huone=ABCD']);
  const answer = w.fetched.find((f) => f.url === '/api/invites/7/answer');
  assert.equal(answer.init.method, 'POST');
  assert.deepEqual(JSON.parse(answer.init.body), { endpoint: ENDPOINT });
});

test('a tap with the site already open takes that window to the room', async () => {
  const went = [];
  const win = { url: SCOPE + '#/kaverit', focus: async () => win, navigate: async (u) => { went.push(u); return win; } };
  const w = worker({ windows: [win] });
  await w.fire('notificationclick', { notification: { data: { id: 7, url: SCOPE + 'games/pilkki/v4/?huone=ABCD' }, close() {} } });
  assert.deepEqual(went, [SCOPE + 'games/pilkki/v4/?huone=ABCD']);
  assert.deepEqual(w.opened, []);
});
