-- Spam limits (#25): which network a name came from, as a salted hash (never the address
-- itself), so one network can make only a few names a day.
ALTER TABLE players ADD COLUMN source TEXT;
CREATE INDEX players_source ON players (source, created_at);

-- A name the admin approved stays that phone's, even after it changes to another name, so
-- nobody else can take it and pose as them (Eero's rule). Rejecting the player frees it.
CREATE TABLE locked_names (
  name_key TEXT PRIMARY KEY,
  player TEXT NOT NULL REFERENCES players (id),
  at TEXT NOT NULL
);
