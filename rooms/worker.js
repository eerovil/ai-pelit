// Live game rooms (#27): one Durable Object per 4-letter room code, holding the phones of one
// game together over WebSockets. Phones reach it through the site's own address:
// pelit.vilpponen.fi/api/rooms/<CODE>?key=<key>&name=<name>[&host=1] (server/api.js forwards it).
//
// `key` is the phone's own secret. The room never shows it: a phone's public id is a hash of its
// key, sent back to it alone as {t: 'you', id}, and everyone else knows it only by that id. So
// nobody can take another phone's place (or the host's) by copying an id from `peers`.
//
// The room is only a relay with a member list. The phone that made the room (the host) runs the
// game; the room passes the host's messages on to the others (all of them, or the one named in
// `to`), and everyone else's messages to the host, with `from` set to the sender's id. Whenever
// someone comes or goes, everyone gets {t: 'peers', host, members: [{id, name, on}]}.
//
// A refused join is a WebSocket closed at once with a code and a Finnish reason the game shows:
// 4004 no such room, 4001 room full, 4009 code in use, 4000 the same phone joined again.
// Sockets use the hibernation API, so a quiet room costs nothing while it waits.

const CODE = /^[A-Z]{4}$/;
const KEY = /^[a-f0-9]{32}$/;
export const MAX_PLAYERS = 5;
export const IDLE = 6 * 3600e3; // an empty room is forgotten after this long
const MSG_MAX = 16000;

// A phone's public id: the first 32 hex digits of SHA-256 of its secret key.
export async function publicId(key) {
  const hash = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(key)));
  return [...hash.slice(0, 16)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export function cleanName(name) {
  if (typeof name !== 'string') return '';
  const s = name.replace(/[\u0000-\u001f\u007f]/g, '').replace(/\s+/g, ' ').trim();
  return [...s].length <= 16 ? s : '';
}

export class Room {
  constructor(ctx, env) {
    this.ctx = ctx;
    this.env = env;
    this.room = undefined; // {host, members: {id: name}}, read from storage on first use
  }

  async load() {
    if (this.room === undefined) this.room = (await this.ctx.storage.get('room')) || null;
    return this.room;
  }

  async store(room) {
    this.room = room;
    if (room) await this.ctx.storage.put('room', room);
    else await this.ctx.storage.delete('room');
  }

  // The open sockets, with who is on each; `except` is one closing just now.
  open(except) {
    return this.ctx.getWebSockets()
      .filter((ws) => ws !== except)
      .map((ws) => ({ ws, ...(ws.deserializeAttachment() || {}) }));
  }

  async fetch(request) {
    if (request.headers.get('upgrade') !== 'websocket') return new Response('websocket only', { status: 426 });
    const url = new URL(request.url);
    const code = (url.pathname.split('/').pop() || '').toUpperCase();
    const key = url.searchParams.get('key') || '', name = cleanName(url.searchParams.get('name'));
    const wantsHost = url.searchParams.get('host') === '1';
    if (!CODE.test(code) || !KEY.test(key) || !name) return new Response('bad code, key or name', { status: 400 });
    const id = await publicId(key);

    let room = await this.load();
    const open = this.open();
    if (wantsHost && (!room || (room.host !== id && !open.length))) {
      room = { host: id, members: {} }; // a new room, or one everyone has left
    } else if (wantsHost && room.host !== id) {
      return refuse(4009, 'Koodi on jo käytössä');
    } else if (!room) {
      return refuse(4004, 'Huonetta ei löydy');
    }
    if (!Object.hasOwn(room.members, id) && Object.keys(room.members).length >= MAX_PLAYERS) {
      return refuse(4001, 'Huone on täynnä');
    }
    room.members[id] = name;
    await this.store(room);
    await this.ctx.storage.deleteAlarm();

    // The same phone again (a reload, a new connection): only the newest socket stays.
    for (const o of open) if (o.id === id) try { o.ws.close(4000, 'Avattu toisaalla'); } catch (e) { /* gone */ }

    const pair = new WebSocketPair();
    this.ctx.acceptWebSocket(pair[1]);
    pair[1].serializeAttachment({ id, host: id === room.host });
    send(pair[1], JSON.stringify({ t: 'you', id }));
    await this.peers();
    return new Response(null, { status: 101, webSocket: pair[0] });
  }

  async webSocketMessage(ws, data) {
    if (typeof data !== 'string' || data.length > MSG_MAX) return;
    let msg;
    try { msg = JSON.parse(data); } catch (e) { return; }
    if (!msg || typeof msg !== 'object') return;
    const me = ws.deserializeAttachment() || {};
    const room = await this.load();
    if (!room) return;
    if (msg.t === 'bye') { // leaving for good, not dropping off
      delete room.members[me.id];
      await this.store(room);
      try { ws.close(1000, 'Poistuit'); } catch (e) { /* gone */ }
      await this.peers(ws);
      await this.maybeEmpty(ws);
      return;
    }
    const open = this.open();
    if (me.host) {
      for (const o of open) if (o.id !== me.id && (!msg.to || o.id === msg.to)) send(o.ws, data);
    } else {
      msg.from = me.id;
      const text = JSON.stringify(msg);
      for (const o of open) if (o.host) send(o.ws, text);
    }
  }

  async webSocketClose(ws) {
    await this.peers(ws);
    await this.maybeEmpty(ws);
  }

  async webSocketError(ws) {
    await this.webSocketClose(ws);
  }

  async maybeEmpty(closing) {
    if (!this.open(closing).length) await this.ctx.storage.setAlarm(Date.now() + IDLE);
  }

  async alarm() {
    if (!this.open().length) {
      this.room = null;
      await this.ctx.storage.deleteAll();
    }
  }

  // Tells everyone who is in the room and who is connected right now. After hibernation the
  // object wakes up new, so the room is read from storage first.
  async peers(closing) {
    const room = await this.load();
    if (!room) return;
    const open = this.open(closing), on = new Set(open.map((o) => o.id));
    const text = JSON.stringify({
      t: 'peers',
      host: room.host,
      members: Object.entries(room.members).map(([id, name]) => ({ id, name, on: on.has(id) })),
    });
    for (const o of open) send(o.ws, text);
  }
}

function send(ws, text) {
  try { ws.send(text); } catch (e) { /* closing */ }
}

function refuse(code, reason) {
  const pair = new WebSocketPair();
  pair[1].accept();
  pair[1].close(code, reason);
  return new Response(null, { status: 101, webSocket: pair[0] });
}

// The Worker has no address of its own (workers_dev = false); this answers anything that asks.
export default {
  fetch() {
    return new Response('ai-pelit rooms: use /api/rooms/<code> on pelit.vilpponen.fi', { status: 404 });
  },
};
