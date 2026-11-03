# Agent guide — ai-pelit

AI-made phone games, played from one PWA at https://pelit.vilpponen.fi/. Only each game's
newest version is kept and played (#346, Eero's choice); the older ones are its history. Eero asks for games as AgentDeck Works on this repository; the
issue is the request, in Finnish. Write code comments and pull requests in English; everything a
player sees is Finnish unless the request says otherwise.

## What a request means

- "Uusi peli: …" — a new game. Pick a short slug (lowercase, digits, dashes), make
  `games/<slug>/v1/index.html` and `games/<slug>/game.json`.
- "<Peli> v<N> (<slug>): …" — a new version. Move the game's one version folder to the next
  number in a commit of its own (`git mv games/<slug>/v<N-1> games/<slug>/v<N>`), then make the
  change in the next commits, so the pull request shows only what changed (#346). Move its tests
  along the same way: `git mv` each `tests/test_<slug>_v<N-1>*.py` to `_v<N>`, and change every
  `games/<slug>/v<N-1>` in the game's test files to `v<N>`. Append the version to `game.json`.
  Other games' tests name versions too (`tests/test_scores.py` names Puhelinkoppi's, Hiihto's and
  Piano's): `grep -rn "<slug>/v<N-1>" tests/` and run every file it finds before the first push,
  not only the game's own tests.
  The number is one above the game's highest ever (Puhelinkoppi went from `v2/` to `v5/`).
  If the version is past about 2000 lines in one file, split it into files (rule 2) as part of
  this version, without being asked, and say so in the pull request. Do the same for a new game
  that grows past it.
- "Palautteet <päivä>: <N> kpl" — the players' feedback (#184), filed once a day by
  `scripts/feedback_issue.py`. The feedback is private and this repository public, so the issue
  lists only each item's number and game; read the items with
  `python3 scripts/feedback_issue.py --show <this issue's number>` (it uses the admin key on this
  host). No pull request: for each item, look at the game it names, then ask Eero in the
  question box whether to fix it (quote it there, and say in one line what you would change;
  group items that ask the same). Each yes becomes a normal request issue,
  "<Peli> v<N> (<slug>): <what to change, in Finnish>", made with `gh issue create --label claude`
  (the poller's ownership label, so it starts its own Work; check its labels after). Write it in
  your own words and naming this issue: never a player's nickname or their words, on any issue
  or pull request. Post only Eero's yes or no per item number on this issue, then close it. Post his answers on the
  issue, then close it.
- Either way, take the game's picture for the shelf (#33): during your mid-play check at
  360 × 740, save a screenshot of a moment that shows the game well and run
  `python3 scripts/make_thumb.py <slug> <screenshot.png>`. It writes `games/<slug>/thumb.webp`.
  A new game needs one (the build refuses a game without it); retake it in a new version when the
  game looks different.
- A game of a kind the shelf gathers (#153; so far "yleisurheilu": athletics events, each its
  own game) adds `"group": "<key>"` to its `game.json`. The shelf then shows it inside that
  group's card. Groups are listed in `GROUPS` in `scripts/build.py`; a new one is added there.
- Ottelu (#168), the athletics match, plays its events' newest versions in a frame, unchanged
  (#303, Eero's choice), read from `catalog.json`, so a new event version joins the match with no
  new Ottelu version, and Ottelu's tests (`tests/test_ottelu_v<N>.py`) run on that version's pull
  request too. `LAJIT` in its `index.html` names fallback versions for when the catalog cannot be
  read; an old one there is sent on to the newest by the site (#346).
  A new event version must still play in the match: keep `kisa.js`'s options and the race's
  functions that Ottelu's `laji.js` and `aita.js` change, or, when it cannot, make a new Ottelu
  version in the same pull request that plays it. `"ottelu": false` no longer helps: no older
  version is left for the match to fall back on, so the build refuses it on a newest version
  (#346). Alone, each next event loads in a
  fresh page: a second frame in the same page took no taps on Eero's phone (see docs/making-games.md).

How to make a game that plays well (controls, difficulty, saves, layout, tests), from what Eero
asked to change in past versions: [docs/making-games.md](docs/making-games.md). Read it before you
start a new game or version. Its "Phone gotchas" list is what only showed on a real phone: when you
hit a new one (a layout, touch, sound or browser surprise), add one line there in the same pull
request, with the version that taught it (#181, Eero's choice).

## Rules

1. **A published version never changes; only the newest is kept.** Never edit a
   `games/<slug>/v<N>/` folder or its `game.json` entry once it is on `main`; a fix is a new
   version (#346, Eero's choice). The phone's offline cache keeps a version folder for good, so
   only a new address brings it new code. A new version moves the old folder away whole (above),
   and its `game.json` entry stays as the game's history, shown on the game's page. CI runs
   `scripts/check_immutable.py`: it fails a pull request that edits a published folder, deletes
   one in part or without a newer one, changes an entry, or reuses a number.
   `scripts/build.py` serves only the newest folder and writes `_redirects`, which sends an older
   version's address (a link, a home-screen shortcut, a room code) to the newest. `public/sw.js`
   drops a phone's cached copy of an older version. `games/<slug>/thumb.webp` is outside the
   version folders and may be retaken.
2. **One folder per game's version, self-contained.** Plain HTML, CSS and JavaScript in the folder, no
   build step, no CDN, no fonts or images from the network. It must play offline, forever. The
   only network a game may use is this site's own `/api/` (see "Online extras"), and only as an
   extra: the game never waits for it, and plays the same without it.
   Why no build step, and no TypeScript (#42): the file in the folder is the file the phone runs,
   so a published version cannot change by accident and needs no tools to keep working. A library
   a game needs is copied into its folder as one file, except a shared library under
   `public/lib/` (three.js, #99, Eero's choice), which games load from there and never copy; see
   "3D games". Think again only when the same code is copied into a third game; then propose it
   as its own Work.
   A version past about 2000 lines is split into a few plain files in its own folder (#161, Eero's
   choice, first Last Signal v9). Do it yourself in the next version, unasked: `index.html` loads
   them with classic `<script src="world.js"></script>` tags, so their functions stay global for
   the tests. Still no
   build step: each new version moves the whole folder on, and an agent reads only the files its
   change touches. Keep a `lib/three` import in `index.html` itself, because `scripts/build.py`
   and `tests/conftest.py` look for it there.
3. **Include the back chip.** Every version's `index.html` ends its body with
   `<script src="../../../back.js"></script>` (the build refuses one without it). It draws
   "‹ Pelit" in the top-left corner; a tap opens its menu (back to the shelf, the game volume). When the game's own score or buttons are there, move the chip
   with `data-corner="top-right"`, `"bottom-left"` or `"bottom-right"` on that script tag.
4. **Phone first.** Touch only, playable on a 360 × 640 screen, no hover, no keyboard
   needed. Fill the screen with a fixed box (`position:fixed; top:0; bottom:0`, or `height:100%`),
   not `100dvh`, and draw for that box as it is each frame (#181: in the installed full-screen
   app on Eero's Android phone, the bottom of Yöajo v1 was under the screen's edge until the system
   bars moved; `100dvh` keeping the old height is the likely cause, not proven). Safe-area
   insets, and `touch-action: none` on the play area. Short
   sounds through Web Audio only after the first tap. Portrait first, and sideways too (#95): the
   installed app may turn, so a new version also plays at 740 × 360 — menus and end screens fit
   without scrolling, buttons sit where thumbs rest, and turning the phone mid-round keeps the
   round.
5. **Saves stay on the phone, and survive new versions.** Save only to `localStorage`, under keys
   `ai-pelit:<slug>:<name>` (keys starting `ai-pelit:_` belong to the shared scripts). All versions of a game share those keys: a new version must read
   the previous version's saved data (or migrate it in place) and never rename, reset or clear
   it. Never touch another game's keys.
6. **game.json** — `title`, one-line `description`, optional `group`, and per version `n` (rising, never reused),
   `date` (YYYY-MM-DD, the merge day), `note` (one Finnish sentence: what changed), `request`
   (the issue text) and `issue` (`eerovil/ai-pelit#<n>`). An older entry may still carry
   `"ottelu": false` as history; a new one may not (see "What a request means").

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
  per phone, and show on lists only once approved at `/yllapito/`. A live check on the real site
  names its phones "Testi", "Testi1", "Testi A"... ("Testi" and up to 8 more letters, digits or
  spaces, #380): the server keeps such names off `/yllapito/` and out of the spam limits, and
  deletes them, with their scores and friends, a day after they were made (`isTestName()` in
  `server/api.js`).
- **Play counts.** `back.js` sends `POST /api/plays` once each time a version opens, and the
  shelf shows each game's all-time total from `GET /api/plays` (#26). Anonymous: only game,
  version, day and a number are kept. A game needs nothing to be counted.
- **Live rooms (multiplayer).** A version opts in with
  `<script src="../../../rooms.js" data-game="<slug>" data-min="2" data-max="5"></script>` before
  its own script (#34), and a "👥 Pelaa kavereiden kanssa" button that calls
  `AiPelitRooms.open()`. Do not copy Kirkkis v2's own room code; it predates the library.
  `rooms.js` draws the room screen (code, players, "Aloita kierros"), reconnects, rejoins
  after a reload, sends a typed code from another game or a newer version to the room's own (a room on an older one says so instead, #346), and pauses
  the round while a phone in it is away (with "Jatka ilman heitä" on the host). The game keeps the
  game: the phone that made the room (the host) runs the round and the others draw it.
  - The room page (#388): making or joining a room moves the phone onto `public/huone/`, which
    keeps the room's WebSocket and the voice calls (`rooms.js` with `data-shell`) and plays the
    game in a frame under a slim room bar (code, players); the game's own 🎤 chip stays where it is and works the page's calls. The game's `rooms.js` talks through
    the page's connection, so a game switch reloads only the frame and the calls stay up; leaving
    the room sends the phone to the game's own page. A game needs nothing for it. A game inside
    another frame (Ottelu's events) keeps the room in its own page, and so do the tests:
    `tests/conftest.py` sets `window.__aiPelitHuoneSivu = false` on every page
    (`ROOMS_IN_GAME`); `tests/test_huone_sivu.py` turns it on.
  - `on('start', s => …)` on every phone: `s.players` (`[{id, name}]`, the connected phones in
    room order), `s.round`, `s.host`, `s.over` (a finished round sent to a phone that missed it).
  - `send(msg, to)` (host: to all or one id; a guest: to the host) and `on('message', (msg, from) => …)`.
    A message's `t` must not start with `_`; `you`, `peers`, `hello`, `bye` are taken too. A phone
    that is not in the round (it joined late) hears none of its messages. A code typed for a room
    made by Kirkkis v2 (which names no game) is refused with "Huone on toisessa pelissä.".
  - Host: `on('hello', id => …)` sends a returning phone the round as it is; `deliver(msg)` sends the
    round's end to every phone in it; each phone confirms it, and one that has not (away, or its
    page reloading) gets it again when it is back; `endRound()`. `on('continue', ids)`
    and `on('back', id)`: the computer takes over, and gives back, a phone's player.
  - Every phone: `paused` (stop the clock while true), `once(round)` (save a result only when true),
    `backToRoom(text, 'win'|'lose')` after the game's own end screen, `note(text)`,
    `extra(node)` (the game's own controls under the player list, such as the host's choice of course),
    `on('lobby')` (the host lost or ended the round: stop it), `on('leave', why)` and `on('menu')` (show the
    game's menu again), `me`, `isHost`, `inRoom`.
  - The host can end a round still going (#392): "⏹ Lopeta kierros kaikilta" in the "‹ Pelit"
    chip's menu (`back.js`, asked twice) calls `stopRound()`, and every phone in the round,
    the host's too, hears `on('lobby')` and gets the room screen. A game needs nothing for it,
    as long as its `lobby` handler stops the round on the host as well.
  - Public rooms (#50): the host's "🌍 Julkinen" switch in the room lists it on every phone's room
    screen for the same game (any version), under "Avoimet huoneet"; one tap joins. A room is
    listed only while it waits between rounds, has space and its host is connected. The list
    shows only the code and the count, not names. The shelf's front page lists every game's open
    rooms the same way (#203, `GET /api/rooms`), and a tap opens the room's version with `?huone=`.
    A game needs nothing for it.
  - A game played in turns (#297) calls `turns(id => …)`, true while the round needs that phone
    (its turn): the round then waits only for an away phone on turn, a phone that leaves keeps its
    player, the host's button is "Ohita vuoro" (`on('skip', ids)`), and the room screen offers
    "Palaa kierrokseen" to a phone that left the round.
  - Voice (#322): every room has push to talk, with nothing for a game to do. While a phone holds
    the 🎤 chip `rooms.js` draws, the others in the room hear it; the sound goes straight between
    the phones (WebRTC), the room passes on only the calls' setup (`_rtc`), and Cloudflare's TURN
    relay (`GET /api/voice/ice`, the `TURN_KEY_*` secrets) helps where phones cannot reach each
    other. Upright the chip sits on the right edge above the middle; on its side, in the top bar
    right of the middle. A new version whose controls are there moves it with
    `data-voice-corner="left|top-left|top-right|bottom-left|bottom-right"` on its `rooms.js` tag,
    or leaves voice out with `data-voice="off"`. A call that brings no sound while the other phone talks (it says it is up, but nothing
    arrives for 3 s) is made again by itself, at most once per 10 s per pair (#386). Each phone has "🎤 Puhe" on the room screen and a
    🔊/🔇 mute beside each name. In every room, public ones too, until a friends list exists
    (Eero's choice). The relay is free up to 1000 GB a month and Cloudflare has no cap, so the site
    hands out relay credentials only under 800 GB this month (Eero's choice), as the host's hourly
    `ai-pelit-turn.timer` (`scripts/turn_usage.py`) last told it, within three days.
  - The nickname is the phone's one name (`ai-pelit:_pelaaja:nimi`, as on the high-score lists).
  - The game must still play alone with no room. Tests: `tests/test_rooms_lib.py` has a `Relay`
    that plays the room in Playwright.
  - Rare network races are the agent's to fix (#284, Eero's choice): a problem that only shows if
    a phone drops, reconnects or reloads in the instant between two messages (Pilkkiminen #271: a
    landed fish lost before the host's reply arrived). When the fix is small (a few lines and a
    test), make it without asking Eero; a reviewer finding of this kind is settled the same way.
    Ask Eero only when the fix is not small (for example, it reworks how the game keeps score or
    turns): say what the fix would change, and offer leaving it as a known limit in the pull
    request body.
  - The room is `/api/rooms/<CODE>`, a WebSocket to one Durable Object per 4-letter code in the
    `ai-pelit-rooms` Worker (`rooms/`), bound to the Pages project as `ROOMS`. It only relays, and
    keeps the host's `game`, `v` and `max` (2–8). CI deploys `rooms/` before the site; a change to
    it must keep every published version's messages working.
- **Outfits (#158).** A version whose player has a figure to dress opts in with
  `<script src="../../../outfits.js" data-game="<slug>"></script>` before its own script, calls
  `AiPelitOutfits.setup({ outfits, draw, change })` with its own everyday outfits (the first is the
  default) and a "👕 Asu" menu button that calls `AiPelitOutfits.open()`. The six Halloween
  costumes are added by the library, always available, first in the picker around Halloween;
  `AiPelitOutfits.head()` draws their heads. An outfit is a palette (`skin`, `hair`, `top`,
  `bottom`, `cape`, `head`) the game's own drawing reads. The choice is saved per game
  (`ai-pelit:_asut:<slug>`); in a room, send `current().id` with the player and draw others with
  `get(id)`. Trampoliini v6 is the model. An athletics event (and Ottelu) adds
  `data-share="yleisurheilu"` and passes `outfits: AiPelitOutfits.yleisurheilu` (#311): one
  choice and one set of kits for every event, so the match wears the same outfit throughout;
  Pituushyppy v10 is the model.
- **Athletics meets (#165).** A field event (a throw or a jump, group `yleisurheilu`) loads
  `<script src="../../../lib/yleisurheilu-8/kisa.js"></script>` (the newest folder) after `rooms.js` and calls
  `AiPelitKisa.meet({...})`: the library runs the field of twelve, the turns, the standings and
  the results board, the saves and the whole room (host, turns, rejoining, the computer taking an
  away phone's turns), so a new event gets playing with friends without room code of its own. The
  game keeps its own attempt and drawing. The options are listed at the top of `kisa.js`;
  Pituushyppy v8 is the model. At the end, `K.drawPodium(ctx, box)` draws the medal ceremony
  (#176): the top three on the podium, the medals hung around their necks, the final standings
  under it; it stays until the player taps it away (the game passes its taps to `K.skip()`).
  Like `lib/three-r*/`, a folder never changes once published: a fix goes in the next one
  (`yleisurheilu-9/`), used by the next versions. From `yleisurheilu-5/` (#297) the meet waits with
  friends only for the phone on turn (rooms.js `turns()`), a friend may leave and come back
  ("Palaa kierrokseen"), the host skips an away friend's turn, and the game draws the friends not
  on turn as cheering spectators with `K.drawFans(ctx, box)`. From `yleisurheilu-7/` (#341) they stay in
  the background: the game calls `K.drawFans(ctx, {..., walk: true})` early in its scene, before the
  athlete (in a stadium behind the boards, which hide their legs), and offers a tap on its scene to
  `K.tapFans(px)` first, which walks a spectator's own figure there on every phone; nobody walks by
  themselves (Eero's choice). From `yleisurheilu-8/` (#373) the game passes `scroll` too, how many px
  the background behind them has moved since its athlete stood at the start (0 there), and the
  friends run after it a little slower than it, catching up once it stops; a tap on another
  spectator climbs onto their shoulders (a column at most four high), so `K.tapFans(px, py)` takes
  the tap's y too. Moukarinheitto, seen from above, stays on `yleisurheilu-7/`. The bar-height format (high jump, pole vault)
  is `korkeus.js` beside `kisa.js`, loaded after it from the same folder (Korkeushyppy v2 from
  `yleisurheilu-1/`). A new format may be added beside them as a new file.
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
- **Switching games in one room (#354).** Between rounds the host can choose a new game from
  `catalog.json`; only games whose `room.max` fits every member are offered. Every phone follows
  into the new game with the same room code and friend identity (no `bye` when switching), and a
  short sessionStorage handoff tells the next page that its phone is the host. A room is deleted
  immediately when its final member deliberately leaves (including with the "‹ Pelit" chip);
  dropped connections still have six hours to rejoin. On the shelf and friends page, invitations
  are shown with Liity/Ei, not duplicated by the invitation banner.
- `public/scores.js`, `public/rooms.js`, `public/kaverit.js` and `public/outfits.js` are shared by every version that uses them: change them
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

## 3D games (three.js)

A game that wants real 3D (a camera, lights, solid shapes) uses three.js from the site's shared
folder (#99), not hand-made projection maths:

```html
<canvas id="c"></canvas>
<script type="module">
import * as THREE from '../../../lib/three-r187/three.module.js';
const c = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas: c, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
// scene, PerspectiveCamera, lights, meshes; on resize: renderer.setSize(innerWidth, innerHeight, false),
// camera.aspect = innerWidth / innerHeight, camera.updateProjectionMatrix().
renderer.setAnimationLoop(() => renderer.render(scene, camera));
</script>
```

- Use the newest `public/lib/three-r*/` folder. A published library folder never changes
  (`scripts/check_immutable.py` fails a pull request that edits one): a newer three.js goes in a
  new `three-r<N>/` folder, copied unchanged from the npm package's `build/` with its `LICENSE`
  and a `SOURCE` line, in its own pull request. Old games keep the release they were made with.
- Core three.js only. An add-on (a model loader, camera controls) is copied into the game's own
  folder as one file, with its import of `three` changed to the relative path above.
- The canvas fills the screen as a fixed box (rule 4, not `100dvh`) with `touch-action: none`; size
  the renderer from the canvas's own size (`clientWidth`, `clientHeight`). Wrap `new THREE.WebGLRenderer` in `try` and show a Finnish message when the phone
  cannot draw 3D.
- The phone downloads the library (about 420 KB compressed) the first time it opens a 3D game,
  and `sw.js` keeps it for offline play. `scripts/build.py` refuses a version that loads a
  `lib/` file that is not there.
- Turning an existing 2D game into 3D (Hiihto v7, #103): keep its classic `<script>`, so its
  functions stay global for its tests and for the inline scripts after it, and load three.js with
  `import('../../../lib/three-r187/three.module.js').then(m => …)`. Put the WebGL canvas under the
  game's own canvas (`pointer-events:none` on it) and keep drawing the menus and HUD on the 2D one,
  cleared each frame. Vertex colours are linear: fill them from `new THREE.Color('#hex')`.
- A cheap phone is short of pixels, not of shapes: on a 2017 Huawei P8 lite, shadows and the pixel
  ratio decided the frame rate, a thousand instanced spruces hardly did. Measure the first seconds of
  play and step the pixel ratio down, then the shadows off (`tune()` in Hiihto v7).
- `tests/fixtures/three-demo.html` is a complete small example (a lit, spinning cube), and
  `tests/test_lib_three.py` shows how to check a 3D game draws (headless Chromium has WebGL).

## Sound effects

Recorded sounds (#205) are a shared library like three.js: the newest `public/lib/aanet-<N>/`
(now `aanet-5/`, 68 sounds), short mono MP3s with `aanet.js` beside them. A version loads it with
a classic `<script src="../../../lib/aanet-5/aanet.js"></script>` before its own script, names the sounds
it uses once (`AiPelitAanet.load(['askel', 'hiekka'])`, so the phone downloads only those) and
plays them by name: `AiPelitAanet.play('hiekka', { vol, rate, delay })`. The names and what each
sound is are listed at the top of `aanet.js`. Sound starts only after the first tap, and `play()`
returns false when nothing played (not loaded yet, offline on the very first open, muted), so a
game may fall back to its own Web Audio beep: `S.play('hiekka') || tone(…)`. Pituushyppy v7 is the
model. A sound that goes on (an engine, wind, wheels rolling; marked LOOP in the list) is
`const m = AiPelitAanet.loop('moottori', { vol })`, then `m.set({ rate, vol })` each frame to
follow the speed, and `m.stop()` when the round ends; it starts by itself once sound is on. Sound
sleeps while the page is hidden.
No crowd noise and no loud sounds (#337, Eero's choice): `aanet-4` has no applause, crowd or cheer,
and plays its loudest files (a whistle, tyres, the winning tune...) quieter by itself (`LOUD` in
`aanet.js`). A field event passes `cheerSound` to `AiPelitKisa.meet`, so "📣 Kannusta" is a quiet
blip and not `kisa.js`'s "jee!" (Pituushyppy v12). Eero then picked by ear (#355) softer files for
the 17 sounds he still found too loud (the select blip, the success chime, the whoosh, the whistles,
the horn...), which `aanet-5` has under the same names, and halved the win and losing tunes; the
cheer plays the chime at 0.08 (Pituushyppy v14). A new sound is about as soft as these.

- Only CC0 sounds (no credit owed, the repository is public), each named with its source in the
  folder's `SOURCE`; Kenney.nl's packs and CC0-only pages on OpenGameArt.org have most of what a
  game needs. Keep a file under about 60 KB (`tests/test_lib_aanet.py` checks it).
- The folder never changes once published (`scripts/check_immutable.py`): a new or better sound
  goes in the next `aanet-<N+1>/`, a copy of the folder with the new files, used by the next
  versions. A game's music and its own tunes (Piano's notes) stay its own.
- `sw.js` keeps the files after their first use, so the game sounds the same offline.
- The player's game volume (#336) is in the menu `back.js`'s "‹ Pelit" chip opens, one setting for every
  game: it puts a gain between each audio context and the speaker by patching `AudioNode`'s
  `connect`. So connect nothing to `ctx.destination` before `back.js` has run (make the context
  and its nodes on the first tap, as every game does); a game needs no volume control of its own.
  The friends' voice in a room is not touched.

## Before you mark the pull request ready

- `python3 -m pytest -q --changed-since origin/main`, `npm test` and `python3 scripts/build.py`
  pass. On a PR also `python3 scripts/check_immutable.py origin/main`. The full browser suite
  never runs, not in CI and not by you (#65, Eero's choice): with `--changed-since` a game's own
  tests run only when the change touches `games/<slug>/` or that game's test file (#37), and a
  change outside `games/` runs only the shared tests, the ones tied to no game. So name a game's
  tests `tests/test_<slug>.py` (or `test_<slug>_<more>.py`, dashes as underscores), or mark a test
  that plays a game with `@pytest.mark.games("<slug>")`. Within a game only the test files of the
  changed versions run (#116): a file tests the `_v<N>` in its name and every `games/<slug>/v<N>`
  written in it. So a new version's tests go in `tests/test_<slug>_v<N>.py`, or name its folder
  (the moved test files of the version before, see "What a request means").
  Editing an existing test file of the game runs all of them (they import each other); a new test
  file runs only itself; a version no file names runs all of them.
  GitHub CI runs them on four workers (`-n 4 --dist loadfile -m "not alone"`, pytest-xdist). The
  tests of 3D games (versions that load `lib/three`, marked `alone` by `tests/conftest.py`) never
  run in CI (#123): on GitHub's runner they had to run one at a time and took most of the run.
  They run on the AgentDeck host, four side by side: prove each head you mark ready with
  `~/agentdeck/.venv/bin/agentdeck job submit --verification --session-token <token> --cwd <checkout> -- scripts/host-tests.sh`.
  On this host the tests' Chromium draws 3D on the graphics card, not in software on the
  processor (#248: `GPU_ARGS` in `tests/conftest.py`); a run with 3D tests ends with a
  `WebGL:` line naming the card, or SwiftShader when it fell back to software.
  When you change a shared file (`public/back.js`, `rooms.js`, `scores.js`...), play a game that
  uses it yourself.
- So that green verification job and the pull request's CI are the last checks before release:
  the deck merges only when both are green on the same head. A merge to `main` deploys at once
  (#65): the deploy job runs only `npm test` and the build (seconds), then the rooms Worker and
  the site. `main` runs no browser tests; they already passed on the pull request's head.
  To check it is live, ask the site itself, not a deployment wake-on (the deck saw no deploy for
  #207): `curl -s -o /dev/null -w '%{http_code}' "https://pelit.vilpponen.fi/<new path>?x=$RANDOM"`
  and the game's versions in `catalog.json`. A 404 right after the merge is the deploy still
  running: look again a minute later before calling it not live (#205).
- GitHub runs no pull-request CI while the pull request conflicts with `main` (#346): the push
  starts no run, so a wake-on for the `test` check never fires, and closing and reopening does not
  help. When no run appears for a pushed head, read `gh pr view <n> --json
  mergeable,mergeStateStatus` once. If it says `CONFLICTING` or `DIRTY`, merge `origin/main` into
  the branch (never rebase pushed commits), fix the conflict, push, and register the wake-on again
  for the new head. `main` moves often here (many Works at once), and another Work often takes
  the same version number, so merge `origin/main` right before you mark the pull request ready
  and again after each review pass, and on a long-running pull request before each push.
- Never put an edit (`sed -i`, a heredoc) in the same Bash call as a test run: the AgentDeck
  queue hook refuses the whole chain. Edit in one call, then run the test alone with
  `AGENTDECK_HEAVY_SLOT_HELD=1`.
- A fix for a chance-based test (a throw, a random round): run it once with a short timeout and
  measure its real range before you queue a long job on it.
- Before you add a new row to a list in `public/app.js`, grep `tests/` for that list's class
  selectors (`.friend`, `.friend .meta`) and give the new row a class of its own, so the old
  tests do not pick it up.
- Play it yourself at 360 × 740 in Playwright, and attach screenshots of the shelf and the game
  mid-play to the issue, as AgentDeck's evidence rule says.
  For a 3D game, launch Chromium with `tests/conftest.py`'s `GPU_ARGS`, so it draws on the card.
- `games/<slug>/thumb.webp` shows the current version mid-play.
- The use-case walkthrough is: open the shelf, open the game, play one round, go back.

## Taking over a pull request, and specs

- When you take over a pull request another Work started, read every earlier review comment and
  every test it asked for, and cover each one before you first mark it ready.
- On a spec-only issue, end the turn that posts the spec with the approval question in the
  question box in that same turn, not with a prose summary.

## Running it locally

    python3 scripts/build.py && python3 -m http.server -d _site 8000

The site is served from the root of its own name, and uses only relative links.

A prototype for Eero's phone is served with `python3 scripts/serve_prototype.py <port>`, never
plain `http.server` (#181): the service worker (`public/sw.js`) keeps a played version folder in
its own cache, so the phone never sees the next edit, and the phone cannot clear that cache.
The script answers `sw.js` with a worker that empties every cache, unregisters itself and
reloads the page (a 404 was not enough: Chrome kept the old worker), and sends
`Cache-Control: no-store`. On a phone that had the old worker, the first visit after this still
shows the cached copy; the page then reloads itself with the new one. It listens on 127.0.0.1 only, so give `tailscale serve` a
different port (`--https=8190 http://127.0.0.1:8191`): a server on all addresses takes the
tailnet's port itself, and the phone gets a TLS error.
`scripts/make_icons.py` redraws the app icons (needs Pillow); the PNGs are committed.
