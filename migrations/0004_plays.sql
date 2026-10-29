-- Play counts (#26): how many times each game version was opened, per UTC day. Anonymous by
-- Eero's choice: nothing here tells one phone from another.
CREATE TABLE plays (
  game TEXT NOT NULL,
  version INTEGER NOT NULL,
  day TEXT NOT NULL,
  n INTEGER NOT NULL,
  PRIMARY KEY (game, version, day)
);
