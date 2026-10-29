-- High-score lists (#25). A player is one phone: a random id it keeps in localStorage, and a
-- nickname that is hidden from every list until the admin approves it.
CREATE TABLE players (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX players_status ON players (status);

-- Each player's best score per list. A list is a game's board: 'main', or e.g. 'taso-3' when a
-- game keeps one list per course.
CREATE TABLE scores (
  game TEXT NOT NULL,
  board TEXT NOT NULL,
  player TEXT NOT NULL REFERENCES players (id),
  score REAL NOT NULL,
  version INTEGER NOT NULL,
  at TEXT NOT NULL,
  PRIMARY KEY (game, board, player)
);
CREATE INDEX scores_list ON scores (game, board, score);
