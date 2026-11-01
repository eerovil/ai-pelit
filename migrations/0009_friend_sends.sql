-- What each phone sent in the last hour (#324): a friend request ('ask') or an invite ('invite').
-- The hourly limits count these, not the open requests and invites, which go away when they are
-- accepted, answered or replaced. Rows older than an hour are deleted as new ones come.
CREATE TABLE friend_sends (
  player TEXT NOT NULL,
  kind TEXT NOT NULL,
  at TEXT NOT NULL
);
CREATE INDEX friend_sends_player ON friend_sends (player, kind, at);
CREATE INDEX friend_sends_at ON friend_sends (at);
