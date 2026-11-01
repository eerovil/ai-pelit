-- Friends (#324). Two phones become friends in a game room: one asks ("➕ Kaveriksi"), the other
-- accepts. Phones know each other only by a public friend id, `pid`: the first 32 hex digits of
-- SHA-256 of the secret player id, made in server/api.js pidOf() (SQLite has no SHA-256, so it is
-- filled there, for an existing player on its first friends request).
ALTER TABLE players ADD COLUMN pid TEXT;
CREATE UNIQUE INDEX players_pid ON players (pid);

-- A request waits for the asked phone. `receiver` is its pid: the asked phone may not have told
-- the server its nickname yet.
CREATE TABLE friend_requests (
  sender TEXT NOT NULL,
  receiver TEXT NOT NULL,
  at TEXT NOT NULL,
  PRIMARY KEY (sender, receiver)
);
CREATE INDEX friend_requests_receiver ON friend_requests (receiver);
CREATE INDEX friend_requests_at ON friend_requests (at);

-- One row per pair of friends, both secret player ids, a < b.
CREATE TABLE friends (
  a TEXT NOT NULL,
  b TEXT NOT NULL,
  at TEXT NOT NULL,
  PRIMARY KEY (a, b)
);
CREATE INDEX friends_b ON friends (b);

-- What each phone with friends plays right now: its last "now playing" message, sent every 30 s
-- while a game or the shelf is on screen. `game` NULL is the shelf.
CREATE TABLE presence (
  player TEXT PRIMARY KEY,
  game TEXT,
  version INTEGER,
  at TEXT NOT NULL
);

-- An invite into a room, for ten minutes, until the friend answers.
CREATE TABLE invites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sender TEXT NOT NULL,
  receiver TEXT NOT NULL,
  game TEXT NOT NULL,
  version INTEGER NOT NULL,
  room TEXT NOT NULL,
  at TEXT NOT NULL
);
CREATE INDEX invites_receiver ON invites (receiver);
CREATE INDEX invites_sender ON invites (sender, at);
