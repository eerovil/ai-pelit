-- The highest level a player has reached in a game, shown next to their score on each list
-- (#25 follow-up). NULL when the game version did not send one.
ALTER TABLE scores ADD COLUMN level INTEGER;
