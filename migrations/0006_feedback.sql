-- Feedback on the games (#184): written on a game's page in the shelf, only by a player whose
-- nickname the admin approved. Private: only the admin page and the host's daily check read it.
-- `name` is the nickname as it was when written. `issue` is the number of the "Palautteet" issue
-- the daily check (scripts/feedback_issue.py) filed it in; NULL until then.
CREATE TABLE feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player TEXT NOT NULL,
  name TEXT NOT NULL,
  game TEXT NOT NULL,
  version INTEGER,
  text TEXT NOT NULL,
  at TEXT NOT NULL,
  issue INTEGER
);
CREATE INDEX feedback_player ON feedback (player, at);
CREATE INDEX feedback_issue ON feedback (issue, at);
