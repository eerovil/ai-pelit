-- Invites as phone notifications (#367): each phone that switched on "🔔 Ilmoitukset kutsuista"
-- keeps its web push subscription here. `endpoint` is the push service's address for that phone,
-- secret to it, so it also names the phone when its service worker asks what the push was about.
CREATE TABLE push_subs (
  player TEXT NOT NULL,
  endpoint TEXT NOT NULL UNIQUE,
  at TEXT NOT NULL
);
CREATE INDEX push_subs_player ON push_subs (player);
