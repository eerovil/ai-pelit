# Agent guide — ai-pelit

AI-made phone games, played from one PWA at https://pelit.vilpponen.fi/. Every version
of every game stays playable. Eero asks for games as AgentDeck Works on this repository; the
issue is the request, in Finnish. Write code comments and pull requests in English; everything a
player sees is Finnish unless the request says otherwise.

## What a request means

- "Uusi peli: …" — a new game. Pick a short slug (lowercase, digits, dashes), make
  `games/<slug>/v1/index.html` and `games/<slug>/game.json`.
- "<Peli> v<N> (<slug>): …" — a new version. Copy the newest version still in `games/<slug>/`
  (usually `v<N-1>/`) to the next free number and change the copy; a withdrawn number (rule 1) is
  skipped for good, so Puhelinkoppi goes from `v2/` to `v5/`. Append the version to `game.json`.
  If the copy is past about 2000 lines in one file, split it into files (rule 2) as part of this
  version, without being asked, and say so in the pull request. Do the same for a new game that
  grows past it.
- Either way, take the game's picture for the shelf (#33): during your mid-play check at
  360 × 740, save a screenshot of a moment that shows the game well and run
  `python3 scripts/make_thumb.py <slug> <screenshot.png>`. It writes `games/<slug>/thumb.webp`.
  A new game needs one (the build refuses a game without it); retake it in a new version when the
  game looks different.
- A game of a kind the shelf gathers (#153; so far "yleisurheilu": athletics events, each its
  own game) adds `"group": "<key>"` to its `game.json`. The shelf then shows it inside that
  group's card. Groups are listed in `GROUPS` in `scripts/build.py`; a new one is added there.
- Ottelu (#168), the athletics match, plays published versions of the field events in a frame,
  unchanged (`LAJIT` in its newest `games/ottelu/v<N>/index.html`): a version it names is never withdrawn
  without a new Ottelu version first. A newer event version joins the match in a new Ottelu version.

How to make a game that plays well (controls, difficulty, saves, layout, tests), from what Eero
asked to change in past versions: [docs/making-games.md](docs/making-games.md). Read it before you
start a new game or version.

## Rules

1. **A published version never changes.** Never edit, move or delete a `games/<slug>/v<N>/` folder
   or its `game.json` entry once it is on `main`; a fix is a new version. CI runs
   `scripts/check_immutable.py` and fails a pull request that does. `games/<slug>/thumb.webp`
   is outside the version folders and may be retaken. The only exception: a version Eero
   explicitly asks to take out of production is added to `WITHDRAWN` in that script (with where
   he said so) in its own pull request, and then deleted whole, folder and entry, in the next.
   Its number is never used again (phones keep the old one cached): the next version skips it.
2. **One folder per version, self-contained.** Plain HTML, CSS and JavaScript in the folder, no
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
   build step: each new version copies the whole folder, and an agent reads only the files its
   change touches. Keep a `lib/three` import in `index.html` itself, because `scripts/build.py`
   and `tests/conftest.py` look for it there. Old versions stay as they are, and none is deleted
   for being big: phones cache only the versions they open, and git stores each copy as a diff.
3. **Include the back chip.** Every version's `index.html` ends its body with
   `<script src="../../../back.js"></script>` (the build refuses one without it). It draws
   "‹ Pelit" in the top-left corner. When the game's own score or buttons are there, move the chip
   with `data-corner="top-right"`, `"bottom-left"` or `"bottom-right"` on that script tag.
4. **Phone first.** Touch only, playable on a 360 × 640 screen, no hover, no keyboard
   needed. Use `100dvh`, safe-area insets, and `touch-action: none` on the play area. Short
   sounds through Web Audio only after the first tap. Portrait first, and sideways too (#95): the
   installed app may turn, so a new version also plays at 740 × 360 — menus and end screens fit
   without scrolling, buttons sit where thumbs rest, and turning the phone mid-round keeps the
   round.
5. **Saves stay on the phone, and survive new versions.** Save only to `localStorage`, under keys
   `ai-pelit:<slug>:<name>` (keys starting `ai-pelit:_` belong to the shared scripts). All versions of a game share those keys: a new version must read
   the previous version's saved data (or migrate it in place) and never rename, reset or clear
   it. Never touch another game's keys.
6. **game.json** — `title`, one-line `description`, optional `group`, and per version `n` (1, 2, 3… in order),
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
    round's end to every phone in it; each phone confirms it, and one that has not (away, or its
    page reloading) gets it again when it is back; `endRound()`. `on('continue', ids)`
    and `on('back', id)`: the computer takes over, and gives back, a phone's player.
  - Every phone: `paused` (stop the clock while true), `once(round)` (save a result only when true),
    `backToRoom(text, 'win'|'lose')` after the game's own end screen, `note(text)`,
    `extra(node)` (the game's own controls under the player list, such as the host's choice of course),
    `on('lobby')` (the host lost the round: stop it), `on('leave', why)` and `on('menu')` (show the
    game's menu again), `me`, `isHost`, `inRoom`.
  - Public rooms (#50): the host's "🌍 Julkinen" switch in the room lists it on every phone's room
    screen for the same game (any version), under "Avoimet huoneet"; one tap joins. A room is
    listed only while it waits between rounds, has space and its host is connected. The list
    shows only the code and the count, not names. A game needs nothing for it.
  - The nickname is the phone's one name (`ai-pelit:_pelaaja:nimi`, as on the high-score lists).
  - The game must still play alone with no room. Tests: `tests/test_rooms_lib.py` has a `Relay`
    that plays the room in Playwright.
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
  `get(id)`. Trampoliini v6 is the model.
- **Athletics meets (#165).** A field event (a throw or a jump, group `yleisurheilu`) loads
  `<script src="../../../lib/yleisurheilu-4/kisa.js"></script>` (the newest folder) after `rooms.js` and calls
  `AiPelitKisa.meet({...})`: the library runs the field of twelve, the turns, the standings and
  the results board, the saves and the whole room (host, turns, rejoining, the computer taking an
  away phone's turns), so a new event gets playing with friends without room code of its own. The
  game keeps its own attempt and drawing. The options are listed at the top of `kisa.js`;
  Pituushyppy v6 is the model. At the end, `K.drawPodium(ctx, box)` draws the medal ceremony
  (#176): the top three on the podium, the medals hung around their necks, the final standings
  under it; it stays until the player taps it away (the game passes its taps to `K.skip()`).
  Like `lib/three-r*/`, a folder never changes once published: a fix goes in the next one
  (`yleisurheilu-5/`), used by the next versions. The bar-height format (high jump, pole vault)
  is `korkeus.js` beside `kisa.js`, loaded after it from the same folder (Korkeushyppy v2 from
  `yleisurheilu-1/`). A new format may be added beside them as a new file.
- `public/scores.js`, `public/rooms.js` and `public/outfits.js` are shared by every version that uses them: change them
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
- The canvas fills `100dvh` with `touch-action: none`; size the renderer from `innerWidth` and
  `innerHeight`. Wrap `new THREE.WebGLRenderer` in `try` and show a Finnish message when the phone
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

## Before you mark the pull request ready

- `python3 -m pytest -q --changed-since origin/main`, `npm test` and `python3 scripts/build.py`
  pass. On a PR also `python3 scripts/check_immutable.py origin/main`. The full browser suite
  never runs, not in CI and not by you (#65, Eero's choice): with `--changed-since` a game's own
  tests run only when the change touches `games/<slug>/` or that game's test file (#37), and a
  change outside `games/` runs only the shared tests, the ones tied to no game. So name a game's
  tests `tests/test_<slug>.py` (or `test_<slug>_<more>.py`, dashes as underscores), or mark a test
  that plays a game with `@pytest.mark.games("<slug>")`. Within a game only the test files of the
  changed versions run (#116): a file tests the `_v<N>` in its name and every `games/<slug>/v<N>`
  written in it. So a new version's tests go in `tests/test_<slug>_v<N>.py`, or name its folder.
  Editing an existing test file of the game runs all of them (they import each other); a new test
  file runs only itself; a version no file names runs all of them.
  GitHub CI runs them on four workers (`-n 4 --dist loadfile -m "not alone"`, pytest-xdist). The
  tests of 3D games (versions that load `lib/three`, marked `alone` by `tests/conftest.py`) never
  run in CI (#123): on GitHub's runner they had to run one at a time and took most of the run.
  They run on the AgentDeck host, two side by side: prove each head you mark ready with
  `~/agentdeck/.venv/bin/agentdeck job submit --verification --session-token <token> --cwd <checkout> -- scripts/host-tests.sh`.
  When you change a shared file (`public/back.js`, `rooms.js`, `scores.js`...), play a game that
  uses it yourself.
- So that green verification job and the pull request's CI are the last checks before release:
  the deck merges only when both are green on the same head. A merge to `main` deploys at once
  (#65): the deploy job runs only `npm test` and the build (seconds), then the rooms Worker and
  the site. `main` runs no browser tests; they already passed on the pull request's head.
- Play it yourself at 360 × 740 in Playwright, and attach screenshots of the shelf and the game
  mid-play to the issue, as AgentDeck's evidence rule says.
- `games/<slug>/thumb.webp` shows the current version mid-play.
- The use-case walkthrough is: open the shelf, open the game, play one round, go back.

## Running it locally

    python3 scripts/build.py && python3 -m http.server -d _site 8000

The site is served from the root of its own name, and uses only relative links.
`scripts/make_icons.py` redraws the app icons (needs Pillow); the PNGs are committed.
