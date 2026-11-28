# Online extras: scores, play counts, outfits, feedback, friends, the API

Read when a game or change uses the site's `/api/`, a shared script under `public/`, the database or `npm test`. Rooms are in [rooms.md](rooms.md), athletics meets in [athletics.md](athletics.md).

Moved here unchanged from `AGENTS.md` (#558), which keeps a short form and links here. "Rule N" means the numbered rules in [rules.md](rules.md); a section named in quotes is listed in [AGENTS.md](../../AGENTS.md).

## Online extras

The site runs on Cloudflare Pages, so `/api/` on the same address is Pages Functions
(`functions/api/[[path]].js` → `server/api.js`) over a D1 database (`migrations/`). First use:
high-score lists (#25), then play counts (#26).

- **High scores.** A version opts in with
  `<script src="../../../scores.js" data-game="<slug>" data-order="high|low" data-corner="bottom-right"></script>`
  and calls `AiPelitScores.submit(score)` when a round ends; `AiPelitScores.board(id, label)`
  picks a per-course list. Everything else about a game's list lives outside the game, so a
  change to it needs no new version: `GAMES` in `public/scores.js` (how a score reads, and
  where the game saves its level, which is sent with each score and shown beside it) and
  `GAMES` in `server/api.js` (which way is better, which lists). Scores wait on the phone while
  offline, and a round that beats neither the score nor the level is not sent. A game's page in the
  shelf shows its top 10 (`data-shelf`); the shelf's rows show no score (#523). Nicknames are one
  per phone, and show on lists only once approved at `/yllapito/`. A live check on the real site
  names its phones "Testi", "Testi1", "Testi A"... ("Testi" and up to 8 more letters, digits or
  spaces, #380): the server keeps such names off `/yllapito/` and out of the spam limits, and
  deletes them, with their scores and friends, a day after they were made (`isTestName()` in
  `server/api.js`).
- **Play counts.** `back.js` sends `POST /api/plays` once each time a version opens, and the
  shelf shows each game's all-time total from `GET /api/plays` (#26). Anonymous: only game,
  version, day and a number are kept. A game needs nothing to be counted.

- **Outfits (#158).** A version whose player has a figure to dress opts in with
  `<script src="../../../outfits.js" data-game="<slug>"></script>` before its own script, calls
  `AiPelitOutfits.setup({ outfits, draw, change })` with its own everyday outfits (the first is the
  default) and a "👕 Asu" menu button that calls `AiPelitOutfits.open()`. The six Halloween
  costumes are added by the library, always available, first in the picker around Halloween;
  `AiPelitOutfits.head()` draws their heads. The five Christmas costumes (#473) are in the picker
  only in November and December, first from 3 November, and not in Orava (Eero's choice); a saved
  one waits out the rest of the year while the game's default is worn. An outfit is a palette (`skin`, `hair`, `top`,
  `bottom`, `cape`, `head`) the game's own drawing reads. The choice is saved per game
  (`ai-pelit:_asut:<slug>`); in a room, send `current().id` with the player and draw others with
  `get(id)`. Trampoliini v6 is the model. An athletics event adds
  `data-share="yleisurheilu"` and passes `outfits: AiPelitOutfits.yleisurheilu` (#311): one
  choice and one set of kits for every event; Pituushyppy v10 is the model. From #469 such a
  game's picker shows the shared front-facing figure (`AiPelitOutfits.figure()`) and a moving
  preview; other games' pickers show their own `draw`. `AiPelitOutfits.headPose(state, t)`
  gives an event's side-view head its tilt for `run`, `takeoff`, `air`, `land`, `cheer` and `idle`,
  and `sideHead()` draws it (Pituushyppy v18 is the model).
  A 3D game adds `data-share="3d"` and dresses its player through `lib/asut3d-1` (#568): one
  choice for every 3D game (`ai-pelit:_asut:3d`, taking over a Pulkkamäki rider's pick) and one
  set, `AiPelitOutfits.kolmiD` (Pulkkamäki's winter wear and Seittisankari's two hero suits, with
  the costumes); see "Outfits in a 3D game" in [3d-games.md](3d-games.md).

- **Feedback (#184).** Each game's page in the shelf has "💬 Anna palautetta": a player whose
  nickname the admin approved writes what to fix, and `POST /api/feedback` keeps it (private,
  shown on `/yllapito/`, never on GitHub). A game needs nothing for it. Once a day at 17.00 the host's
  `ai-pelit-palautteet.timer` (`scripts/systemd/`) runs `scripts/feedback_issue.py` from
  `origin/main`, which files the new ones as one "Palautteet" issue (see "What a request means").
- **Friends (#324).** Two phones become friends in a game room: `rooms.js` shows "➕ Kaveriksi"
  beside each other player who has a nickname, and the other phone accepts. `public/kaverit.js`
  (loaded by `back.js` in every game, and by the shelf) tells the server what a phone with
  friends plays every 30 s while a page is on screen, shows invites ("Liity") and requests as a
  banner, and the room screen's "📨 Kutsu kaveri" invites a friend into the room. The shelf has
  the friends page at `#/kaverit`; pending invites and friend requests are on the shelf's
  front page, and friends' game activity appears only on the friends page (#354). A game needs
  nothing for it. Phones know each other only by a friend id, a hash of the secret player id
  (`pidOf()` in `server/api.js`), which a phone with a nickname sends to the room as `fid`.
  An invite also comes as a phone notification (#367), with the site closed, once the phone has
  switched on "🔔 Ilmoitukset kutsuista" on the friends page (on iPhone only in the installed app):
  the server sends an empty web push (`push_subs`, signed with the `VAPID_PRIVATE_KEY` secret,
  whose public half is in `server/api.js` and `kaverit.js`; the pair is kept on this host in
  `~/.local/share/ai-pelit/vapid.env`), and `public/sw.js` asks `GET /api/push/pending` what it was.

- `public/scores.js`, `public/rooms.js`, `public/kaverit.js` and `public/outfits.js` are shared by every version that uses them: change them
  only in ways every one of them keeps working with.
- A schema change is a new `migrations/<NNNN>_<what>.sql`. Apply it with
  `python3 scripts/cloudflare_setup.py` (needs `CLOUDFLARE_API_TOKEN` and
  `CLOUDFLARE_ACCOUNT_ID`; on this host they are in `~/.local/share/ruokalista/cloudflare.env`)
  once review has passed, right before the change merges: nothing in CI applies it, a merge deploys
  at once, and the code still live must keep working on the changed schema. It also binds `DB` and `ADMIN_KEY` on the Pages project; the
  admin key is kept in `~/.local/share/ai-pelit/admin-key`.
- `npm test` (Node 22) runs `server/api.js` on SQLite with the migrations. To try the real thing,
  deploy a preview: `npx wrangler pages deploy _site --project-name ai-pelit --branch <branch>`
  serves `https://<branch>.ai-pelit.pages.dev` on the `ai-pelit-preview` database. There is no
  Node on this host; run it in `podman run … docker.io/library/node:22`.
