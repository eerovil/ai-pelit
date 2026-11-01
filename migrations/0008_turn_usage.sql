-- The voice relay's use this month (#322): Cloudflare's TURN service is free up to 1000 GB a
-- month and billed after, with no cap of its own. The host's hourly check
-- (scripts/turn_usage.py) asks Cloudflare and writes it here; /api/voice/ice hands out relay
-- credentials only while the month's bytes are under the cap and the check is recent.
-- `month` is 'YYYY-MM' (UTC), `checked_at` an ISO time.
-- IF NOT EXISTS: it was first applied as 0007_turn_usage.sql, before 0007_playing.sql took the number.
CREATE TABLE IF NOT EXISTS turn_usage (
  month TEXT PRIMARY KEY,
  bytes INTEGER NOT NULL,
  checked_at TEXT NOT NULL
);
