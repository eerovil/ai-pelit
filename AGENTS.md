# Agent guide — ai-pelit

AI-made phone games, played from one PWA at https://pelit.vilpponen.fi/. Every version
of every game stays playable. Eero asks for games as AgentDeck Works on this repository; the
issue is the request, in Finnish. Write code comments and pull requests in English; everything a
player sees is Finnish unless the request says otherwise.

## What a request means

- "Uusi peli: …" — a new game. Pick a short slug (lowercase, digits, dashes), make
  `games/<slug>/v1/index.html` and `games/<slug>/game.json`.
- "<Peli> v<N> (<slug>): …" — a new version. Copy `games/<slug>/v<N-1>/` to `games/<slug>/v<N>/`
  and change the copy. Append the version to `game.json`.
- Either way, take the game's picture for the shelf (#33): during your mid-play check at
  360 × 740, save a screenshot of a moment that shows the game well and run
  `python3 scripts/make_thumb.py <slug> <screenshot.png>`. It writes `games/<slug>/thumb.webp`.
  A new game needs one (the build refuses a game without it); retake it in a new version when the
  game looks different.

## Rules

1. **A published version never changes.** Never edit, move or delete a `games/<slug>/v<N>/` folder
   or its `game.json` entry once it is on `main`; a fix is a new version. CI runs
   `scripts/check_immutable.py` and fails a pull request that does. `games/<slug>/thumb.webp`
   is outside the version folders and may be retaken.
2. **One folder per version, self-contained.** Plain HTML, CSS and JavaScript in the folder, no
   build step, no CDN, no fonts or images from the network. It must play offline, forever. The
   only network a game may use is this site's own `/api/` (see "Online extras"), and only as an
   extra: the game never waits for it, and plays the same without it.
3. **Include the back chip.** Every version's `index.html` ends its body with
   `<script src="../../../back.js"></script>` (the build refuses one without it). It draws
   "‹ Pelit" in the top-left corner. When the game's own score or buttons are there, move the chip
   with `data-corner="top-right"`, `"bottom-left"` or `"bottom-right"` on that script tag.
4. **Phone first.** Portrait, touch only, playable on a 360 × 640 screen, no hover, no keyboard
   needed. Use `100dvh`, safe-area insets, and `touch-action: none` on the play area. Short
   sounds through Web Audio only after the first tap.
5. **Saves stay on the phone, and survive new versions.** Save only to `localStorage`, under keys
   `ai-pelit:<slug>:<name>` (keys starting `ai-pelit:_` belong to the shared scripts). All versions of a game share those keys: a new version must read
   the previous version's saved data (or migrate it in place) and never rename, reset or clear
   it. Never touch another game's keys.
6. **game.json** — `title`, one-line `description`, and per version `n` (1, 2, 3… in order),
   `date` (YYYY-MM-DD, the merge day), `note` (one Finnish sentence: what changed), `request`
   (the issue text) and `issue` (`eerovil/ai-pelit#<n>`).

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
  offline, and a round that beats neither the score nor the level is not sent. The shelf shows
  each game's no. 1 on its card and its top 10 on its page (`data-shelf`). Nicknames are one
  per phone, and show on lists only once approved at `/yllapito/`.
- **Play counts.** `back.js` sends `POST /api/plays` once each time a version opens, and the
  shelf shows each game's all-time total from `GET /api/plays` (#26). Anonymous: only game,
  version, day and a number are kept. A game needs nothing to be counted.
- **Live rooms (multiplayer).** A version opts in with
  `<script src="../../../rooms.js" data-game="<slug>" data-min="2" data-max="5"></script>` before
  its own script (#34), and a "👥 Pelaa kavereiden kanssa" button that calls
  `AiPelitRooms.open()`. Do not copy Kirkkis v2's own room code; it predates the library.
  `rooms.js` draws the room screen (code, QR link, players, "Aloita kierros"), reconnects, rejoins
  after a reload, sends a typed code from another game or version to the room's own, and pauses
  the round while a phone in it is away (with "Jatka ilman heitä" on the host). The game keeps the
  game: the phone that made the room (the host) runs the round and the others draw it.
  - `on('start', s => …)` on every phone: `s.players` (`[{id, name}]`, the connected phones in
    room order), `s.round`, `s.host`, `s.over` (a finished round sent to a phone that missed it).
  - `send(msg, to)` (host: to all or one id; a guest: to the host) and `on('message', (msg, from) => …)`.
    A message's `t` must not start with `_`; `you`, `peers`, `hello`, `bye` are taken too. A phone
    that is not in the round (it joined late) hears none of its messages. A code typed for a room
    made by Kirkkis v2 (which names no game) is refused with "Huone on toisessa pelissä.".
  - Host: `on('hello', id => …)` sends a returning phone the round as it is; `deliver(msg)` sends the
    round's end to every phone in it, now or when it is back; `endRound()`. `on('continue', ids)`
    and `on('back', id)`: the computer takes over, and gives back, a phone's player.
  - Every phone: `paused` (stop the clock while true), `once(round)` (save a result only when true),
    `backToRoom(text, 'win'|'lose')` after the game's own end screen, `note(text)`,
    `on('lobby')` (the host lost the round: stop it), `on('leave', why)` and `on('menu')` (show the
    game's menu again), `me`, `isHost`, `inRoom`.
  - The nickname is the phone's one name (`ai-pelit:_pelaaja:nimi`, as on the high-score lists).
  - The game must still play alone with no room. Tests: `tests/test_rooms_lib.py` has a `Relay`
    that plays the room in Playwright.
  - The room is `/api/rooms/<CODE>`, a WebSocket to one Durable Object per 4-letter code in the
    `ai-pelit-rooms` Worker (`rooms/`), bound to the Pages project as `ROOMS`. It only relays, and
    keeps the host's `game`, `v` and `max` (2–8). CI deploys `rooms/` before the site; a change to
    it must keep every published version's messages working.
- `public/scores.js` and `public/rooms.js` are shared by every version that uses them: change them
  only in ways every one of them keeps working with.
- A schema change is a new `migrations/<NNNN>_<what>.sql`. Apply it with
  `python3 scripts/cloudflare_setup.py` (needs `CLOUDFLARE_API_TOKEN` and
  `CLOUDFLARE_ACCOUNT_ID`; on this host they are in `~/.local/share/ruokalista/cloudflare.env`)
  before the change merges. It also binds `DB` and `ADMIN_KEY` on the Pages project; the
  admin key is kept in `~/.local/share/ai-pelit/admin-key`.
- `npm test` (Node 22) runs `server/api.js` on SQLite with the migrations. To try the real thing,
  deploy a preview: `npx wrangler pages deploy _site --project-name ai-pelit --branch <branch>`
  serves `https://<branch>.ai-pelit.pages.dev` on the `ai-pelit-preview` database. There is no
  Node on this host; run it in `podman run … docker.io/library/node:22`.

## Before you mark the pull request ready

- `python3 -m pytest -q`, `npm test` and `python3 scripts/build.py` pass. On a PR also
  `python3 scripts/check_immutable.py origin/main`.
- Play it yourself at 360 × 740 in Playwright, and attach screenshots of the shelf and the game
  mid-play to the issue, as AgentDeck's evidence rule says.
- `games/<slug>/thumb.webp` shows the current version mid-play.
- The use-case walkthrough is: open the shelf, open the game, play one round, go back.

## Running it locally

    python3 scripts/build.py && python3 -m http.server -d _site 8000

The site is served from the root of its own name, and uses only relative links.
`scripts/make_icons.py` redraws the app icons (needs Pillow); the PNGs are committed.
