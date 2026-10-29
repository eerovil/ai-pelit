// rooms/worker.js (the live game room) against stand-ins for Cloudflare's Durable Object state
// and WebSockets: node --test tests/server/
import test from 'node:test';
import assert from 'node:assert/strict';

class FakeSocket {
  constructor() { this.sent = []; this.closed = null; this.att = null; }
  send(text) { if (this.closed) throw new Error('closed'); this.sent.push(JSON.parse(text)); }
  close(code, reason) { this.closed = { code, reason }; if (this.peer && !this.peer.closed) this.peer.close(code, reason); }
  accept() {}
  serializeAttachment(a) { this.att = a; }
  deserializeAttachment() { return this.att; }
  last(t) { return this.sent.filter((m) => m.t === t).at(-1); }
}
globalThis.WebSocketPair = class {
  constructor() { this[0] = new FakeSocket(); this[1] = new FakeSocket(); this[0].peer = this[1]; this[1].peer = this[0]; }
};
// Node's Response refuses status 101; Cloudflare's takes it with the client end of the socket.
globalThis.Response = class { constructor(body, init = {}) { this.status = init.status ?? 200; this.webSocket = init.webSocket; } };

const { Room, MAX_PLAYERS, IDLE, publicId } = await import('../../rooms/worker.js');
const { handle } = await import('../../server/api.js');

function fakeCtx() {
  const sockets = [], store = new Map();
  const ctx = {
    alarm: null,
    acceptWebSocket(ws) { sockets.push(ws); },
    getWebSockets() { return sockets.filter((ws) => !ws.closed); },
    storage: {
      get: async (k) => structuredClone(store.get(k)),
      put: async (k, v) => { store.set(k, structuredClone(v)); },
      delete: async (k) => store.delete(k),
      deleteAll: async () => store.clear(),
      setAlarm: async (t) => { ctx.alarm = t; },
      deleteAlarm: async () => { ctx.alarm = null; },
    },
    store,
  };
  return ctx;
}

// Each phone's secret key, and the public id the room makes of it.
const key = (c) => c.repeat(32);
const K = { H: key('a'), A: key('b'), B: key('c') };
const H = await publicId(K.H), A = await publicId(K.A), B = await publicId(K.B);
const keyOf = { [H]: K.H, [A]: K.A, [B]: K.B };
const id = async (c) => { const k = key(c), i = await publicId(k); keyOf[i] = k; return i; };

function setup() {
  const ctx = fakeCtx(), room = new Room(ctx, {});
  // Joins and returns the server end of the socket (what the room sees); `.client` is the phone's.
  const join = async (who, name, host = false, code = 'KISA') => {
    const q = new URLSearchParams({ key: keyOf[who], name });
    if (host) q.set('host', '1');
    const res = await room.fetch(new Request(`https://pelit.test/api/rooms/${code}?${q}`, { headers: { upgrade: 'websocket' } }));
    assert.equal(res.status, 101);
    const client = res.webSocket, server = ctx.getWebSockets().find((s) => s.att?.id === who && !s.closed);
    // A refused join comes back as a socket closed at once with a reason.
    return { client, server, refused: client.closed || (server ? null : { code: 'closed' }) };
  };
  return { ctx, room, join };
}

test('the host makes a room, others join, and everyone hears who is in', async () => {
  const { room, join } = setup();
  const h = await join(H, 'Eero', true);
  assert.equal(h.refused, null);
  const a = await join(A, 'Aino');
  assert.deepEqual(h.server.last('peers'), {
    t: 'peers', host: H,
    members: [{ id: H, name: 'Eero', on: true }, { id: A, name: 'Aino', on: true }],
  });
  assert.deepEqual(a.server.last('peers'), h.server.last('peers'));
  // Without a host nobody can make a room by joining it (each code is its own room object).
  const lost = await setup().join(B, 'Iida', false, 'XXXX');
  assert.equal(lost.client.closed.code, 4004);
  assert.equal(lost.client.closed.reason, 'Huonetta ei löydy');
  void room;
});

test('the host speaks to all or to one; the others speak only to the host', async () => {
  const { room, join } = setup();
  const h = await join(H, 'Eero', true), a = await join(A, 'Aino'), b = await join(B, 'Iida');
  await room.webSocketMessage(h.server, JSON.stringify({ t: 's', n: 1 }));
  assert.deepEqual([a.server.last('s'), b.server.last('s'), h.server.last('s')], [{ t: 's', n: 1 }, { t: 's', n: 1 }, undefined]);
  await room.webSocketMessage(h.server, JSON.stringify({ t: 'start', to: B }));
  assert.equal(a.server.last('start'), undefined);
  assert.deepEqual(b.server.last('start'), { t: 'start', to: B });
  await room.webSocketMessage(a.server, JSON.stringify({ t: 'me', x: 3, from: B }));
  assert.deepEqual(h.server.last('me'), { t: 'me', x: 3, from: A }); // `from` cannot be faked
  assert.equal(b.server.last('me'), undefined);
  // Junk is dropped.
  await room.webSocketMessage(a.server, 'not json');
  await room.webSocketMessage(a.server, 'x'.repeat(20000));
});

test('a room takes five phones; one that drops off keeps its place and can come back', async () => {
  const { room, join } = setup();
  const h = await join(H, 'Eero', true);
  const ids = [A, B, await id('d'), await id('e')];
  const socks = [];
  for (const [i, who] of ids.entries()) socks.push(await join(who, `P${i}`));
  assert.equal(MAX_PLAYERS, 5);
  const sixth = await join(await id('f'), 'Kuudes');
  assert.equal(sixth.client.closed.code, 4001);
  // Aino's phone drops off: the host sees her as off, and her place is kept.
  socks[0].server.close(1006, '');
  await room.webSocketClose(socks[0].server);
  assert.deepEqual(h.server.last('peers').members.find((m) => m.id === A), { id: A, name: 'P0', on: false });
  const back = await join(A, 'P0');
  assert.equal(back.refused, null);
  assert.equal(h.server.last('peers').members.find((m) => m.id === A).on, true);
});

test('a phone hears its own public id, never a key; a copied id makes a new phone', async () => {
  const { join } = setup();
  const h = await join(H, 'Eero', true);
  assert.deepEqual(h.server.sent[0], { t: 'you', id: H });
  assert.notEqual(H, K.H);
  assert.ok(!JSON.stringify(h.server.sent).includes(K.H));
  // A guest who sends the host's public id as its key gets an id of its own, and is not the host.
  keyOf.fake = H;
  const fake = await join('fake', 'Eero');
  const mine = fake.client.peer.sent.find((m) => m.t === 'you').id;
  assert.notEqual(mine, H);
  assert.equal(h.server.closed, null);
  assert.equal(h.server.last('peers').host, H);
});

test('the same phone joining again replaces its old socket', async () => {
  const { join } = setup();
  await join(H, 'Eero', true);
  const first = await join(A, 'Aino'), second = await join(A, 'Aino');
  assert.equal(first.server.closed.code, 4000);
  assert.equal(second.server.closed, null);
});

test('leaving with bye frees the place; a code in use is refused to another host', async () => {
  const { room, join, ctx } = setup();
  const h = await join(H, 'Eero', true), a = await join(A, 'Aino');
  await room.webSocketMessage(a.server, JSON.stringify({ t: 'bye' }));
  assert.deepEqual(h.server.last('peers').members.map((m) => m.id), [H]);
  const other = await join(B, 'Iida', true);
  assert.equal(other.client.closed.code, 4009);
  // Once everyone has gone, the code is free for a new host, and the empty room is forgotten later.
  h.server.close(1000, '');
  await room.webSocketClose(h.server);
  assert.ok(ctx.alarm >= Date.now() + IDLE - 1000);
  const fresh = await join(B, 'Iida', true);
  assert.equal(fresh.refused, null);
  assert.equal(ctx.alarm, null);
  assert.deepEqual(fresh.server.last('peers'), { t: 'peers', host: B, members: [{ id: B, name: 'Iida', on: true }] });
  fresh.server.close(1000, '');
  await room.webSocketClose(fresh.server);
  await room.alarm();
  assert.equal(ctx.store.size, 0);
});

test('bad codes, ids and names are refused before the room', async () => {
  const { room } = setup();
  const res = await room.fetch(new Request('https://pelit.test/api/rooms/KISA?key=nope&name=Eero&host=1', { headers: { upgrade: 'websocket' } }));
  assert.equal(res.status, 400);
});

test('/api/rooms/<code> goes on to the room named by its code', async () => {
  const asked = [];
  const ROOMS = {
    idFromName: (name) => `obj:${name}`,
    get: (obj) => ({ fetch: async (req) => { asked.push([obj, new URL(req.url).search]); return new Response(null, { status: 101 }); } }),
  };
  const ws = { headers: { upgrade: 'websocket' } };
  const r = await handle(new Request('https://pelit.test/api/rooms/kisa?id=x', ws), { ROOMS });
  assert.equal(r.status, 101);
  assert.deepEqual(asked, [['obj:KISA', '?id=x']]);
  assert.equal((await handle(new Request('https://pelit.test/api/rooms/KIS4', ws), { ROOMS })).status, 400);
  assert.equal((await handle(new Request('https://pelit.test/api/rooms/KISA'), { ROOMS })).status, 426);
  assert.equal((await handle(new Request('https://pelit.test/api/rooms/KISA', ws), {})).status, 503);
});
