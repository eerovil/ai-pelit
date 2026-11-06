-- Owner explicitly requested removal of Frisbeegolf v1/v2 leaderboard scores in #338.
-- v3 has harder aiming and a separate board; every other game and version is preserved.
DELETE FROM scores WHERE game = 'frisbeegolf' AND version IN (1, 2);
