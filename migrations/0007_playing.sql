-- Who is playing right now (#325): one row per open game page, kept only while it says it is
-- still there. The id is random per page open and lives only in that page's memory, so like
-- plays nothing here tells one phone from another; rows older than PLAYING_KEEP are deleted.
CREATE TABLE playing (
  id TEXT PRIMARY KEY,
  game TEXT NOT NULL,
  seen INTEGER NOT NULL
);
CREATE INDEX playing_seen ON playing (seen);
