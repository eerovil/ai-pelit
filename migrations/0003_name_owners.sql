-- One owner per name, kept by the primary key so two phones asking at once cannot both get it
-- (review of #25). A row is a player's current name while it is not rejected (locked = 0), or
-- a name the admin approved, which stays that phone's after it changes name (locked = 1).
-- name_key is the name in Unicode NFKC, lower case, made in server/api.js nameKey(): SQLite's
-- lower() folds only A–Z, so 'ÄITI' and 'äiti' were two names.
CREATE TABLE names (
  name_key TEXT PRIMARY KEY,
  player TEXT NOT NULL, -- a player id; no foreign key, as a new player claims its name first
  locked INTEGER NOT NULL DEFAULT 0,
  at TEXT NOT NULL
);
CREATE INDEX names_player ON names (player);
INSERT OR IGNORE INTO names (name_key, player, locked, at)
  SELECT name_key, player, 1, at FROM locked_names;
INSERT OR IGNORE INTO names (name_key, player, locked, at)
  SELECT lower(name), id, 0, updated_at FROM players WHERE status != 'rejected';
DROP TABLE locked_names;
