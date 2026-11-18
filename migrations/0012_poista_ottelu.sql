-- Ottelu, the athletics match, was removed from the site (#469, Eero's choice), and its high
-- scores with it. Safe to run again: it is run once more after the deploy, for any score the
-- old site took in between.
DELETE FROM scores WHERE game = 'ottelu';
