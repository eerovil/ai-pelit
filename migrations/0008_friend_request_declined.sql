-- A declined friend request (#324) stays, unseen by the phone that declined it, until it is
-- 7 days old: the asking phone keeps seeing "Pyydetty", so a "no" is never shown to it.
ALTER TABLE friend_requests ADD COLUMN declined INTEGER NOT NULL DEFAULT 0;
