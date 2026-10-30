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
//
// The shared client (public/rooms.js, #34) also says which game and version the host is playing
// (`game`, `v`) and how many phones the game takes (`max`, 2-8). The room keeps them from the
// host's join and sends `game` and `v` in every `peers`, so a guest on another game or version can
// move to the right one. A join without them (Kirkkis v2) works as before: 5 phones.
//
// Public rooms (#50): the host may list its room for anyone playing the same game. It sends
// {t: '_list', on} (not passed on to anyone): on while the room is public and waits between rounds.
// The room is listed only while that is on, the host is connected and there is space. The list is
// one more object of this same class, named LOBBY (no room code can be that name); each room tells
// it its state, and phones read it with GET /api/rooms?game=<slug> (server/api.js). A listing not
// refreshed for LISTED_FOR is dropped, so a room that vanished without saying so leaves the list.

const CODE = /^[A-Z]{4}$/;
const KEY = /^[a-f0-9]{32}$/;
const GAME = /^[a-z0-9-]{1,40}$/;
export const MAX_PLAYERS = 5; // when the host does not say
export const MOST_PLAYERS = 8; // the most a host may ask for
export const IDLE = 6 * 3600e3; // an empty room is forgotten after this long
const MSG_MAX = 16000;
export const LOBBY = 'lobby'; // the name of the object that keeps the list of public rooms
export const LISTED_FOR = 3 * 60e3; // the host refreshes its listing every minute (public/rooms.js)
const LISTED_MOST = 10;

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

// What the host says about its game: {game, v, max}, each only when it is valid.
export function gameOf(params) {
  const out = {}, game = params.get('game') || '', v = +params.get('v'), max = +params.get('max');
  if (GAME.test(game)) out.game = game;
  if (Number.isInteger(v) && v >= 1 && v <= 999) out.v = v;
  if (Number.isInteger(max) && max >= 2) out.max = Math.min(MOST_PLAYERS, max);
  return out;
}

export class Room {
  constructor(ctx, env) {
    this.ctx = ctx;
    this.env = env;
    this.room = undefined; // {host, members: {id: name}, code, game?, v?, max?, listed?, told?}, read from storage on first use
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
    const url = new URL(request.url);
    if (url.pathname === '/lobby') return this.lobby(request, url);
    if (request.headers.get('upgrade') !== 'websocket') return new Response('websocket only', { status: 426 });
    const code = (url.pathname.split('/').pop() || '').toUpperCase();
    const key = url.searchParams.get('key') || '', name = cleanName(url.searchParams.get('name'));
    const wantsHost = url.searchParams.get('host') === '1';
    if (!CODE.test(code) || !KEY.test(key) || !name) return new Response('bad code, key or name', { status: 400 });
    const id = await publicId(key);

    let room = await this.load();
    const open = this.open();
    if (wantsHost && (!room || (room.host !== id && !open.length))) {
      // A new room, or one everyone has left. `told` makes it clear any old listing of this code.
      room = { host: id, members: {}, code, told: true, ...gameOf(url.searchParams) };
    } else if (wantsHost && room.host !== id) {
      return refuse(4009, 'Koodi on jo käytössä');
    } else if (!room) {
      return refuse(4004, 'Huonetta ei löydy');
    }
    if (!Object.hasOwn(room.members, id) && Object.keys(room.members).length >= (room.max || MAX_PLAYERS)) {
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
    await this.tell();
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
      await this.tell(ws);
      await this.maybeEmpty(ws);
      return;
    }
    if (msg.t === '_list') { // the host lists its room, or takes it off the list
      if (!me.host) return;
      room.listed = msg.on === true;
      await this.store(room);
      await this.tell();
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
    await this.tell(ws);
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
      const room = await this.load();
      if (room) await this.tell(null, true);
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
      ...(room.game ? { game: room.game } : {}),
      ...(room.v ? { v: room.v } : {}),
      members: Object.entries(room.members).map(([id, name]) => ({ id, name, on: on.has(id) })),
    });
    for (const o of open) send(o.ws, text);
  }

  // Tells the list whether this room is on it: public, waiting between rounds, its host here, and
  // space left. A listed room says so every time (that keeps it on the list); one that is not says
  // so once.
  async tell(closing, gone = false) {
    const room = await this.load();
    if (!room || !room.code || !this.env.ROOMS) return;
    const n = Object.keys(room.members).length, max = room.max || MAX_PLAYERS;
    const hostOn = this.open(closing).some((o) => o.id === room.host);
    const listed = !gone && !!room.listed && !!room.game && hostOn && n < max;
    if (!listed && !room.told) return;
    const entry = listed ? { game: room.game, v: room.v || 1, n, max } : null;
    try {
      const lobby = this.env.ROOMS.get(this.env.ROOMS.idFromName(LOBBY));
      await lobby.fetch(new Request('https://rooms/lobby', { method: 'POST', body: JSON.stringify({ code: room.code, entry }) }));
    } catch (e) { return; /* the list is an extra; it catches up on the next refresh */ }
    if (room.told !== listed && !gone) { room.told = listed; await this.store(room); }
  }

  // The list of public rooms (only in the LOBBY object): POST {code, entry} from a room puts it on
  // the list or (entry null) takes it off; GET ?game= reads one game's rooms, newest first.
  async lobby(request, url) {
    const now = Date.now();
    const list = ((await this.ctx.storage.get('lobby')) || []).filter((r) => now - r.at < LISTED_FOR);
    if (request.method === 'POST') {
      let body;
      try { body = await request.json(); } catch (e) { return new Response('bad body', { status: 400 }); }
      if (!body || !CODE.test(body.code)) return new Response('bad code', { status: 400 });
      // A room new on the list goes first; one already there keeps its place.
      const e = body.entry, at = list.findIndex((r) => r.code === body.code);
      const entry = e && GAME.test(e.game) && { code: body.code, game: e.game, v: e.v, n: e.n, max: e.max, at: now };
      if (at >= 0) list.splice(at, 1, ...(entry ? [entry] : []));
      else if (entry) list.unshift(entry);
      await this.ctx.storage.put('lobby', list.slice(0, 200));
      return new Response(null, { status: 204 });
    }
    const game = url.searchParams.get('game') || '';
    const rooms = list.filter((r) => r.game === game).slice(0, LISTED_MOST)
      .map((r) => ({ code: r.code, v: r.v, n: r.n, max: r.max }));
    return new Response(JSON.stringify({ rooms }), {
      headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
    });
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
