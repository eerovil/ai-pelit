# The rules, in full

Read before a game's first push, and whenever a short rule in `AGENTS.md` leaves a question.

Moved here unchanged from `AGENTS.md` (#558), which keeps a short form and links here. "Rule N" means the numbered rules in [rules.md](rules.md); a section named in quotes is listed in [AGENTS.md](../../AGENTS.md).

## Rules

1. **A published version never changes; only the newest is kept.** Never edit a
   `games/<slug>/v<N>/` folder or its `game.json` entry once it is on `main`; a fix is a new
   version (#346, Eero's choice). The phone's offline cache keeps a version folder for good, so
   only a new address brings it new code. A new version moves the old folder away whole (above),
   and its `game.json` entry stays as the game's history, shown on the game's page. CI runs
   `scripts/check_immutable.py`: it fails a pull request that edits a published folder, deletes
   one in part or without a newer one, changes an entry, or reuses a number. It compares with
   where the branch left the ref it is given (`git merge-base HEAD <ref>`, the ref itself when git
   cannot tell), so a version `main` published since is not blamed on the branch (#555); a new
   version's number is still checked against the ref's tip too.
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
6. **game.json** — `title`, one-line `description`, `category` (or a `group` that gives one), and per version `n` (rising, never reused),
   `date` (YYYY-MM-DD, the merge day), `note` (one Finnish sentence: what changed), `request`
   (the issue text) and `issue` (`eerovil/ai-pelit#<n>`). An older entry may still carry
   `"ottelu": false` as history (Ottelu is gone, #469); a new one needs none.

7. **Pin what the owner said.** Pin every behaviour the owner stated in a test before the first
   push, and ask before building or dropping a mechanic the approved spec does not have.
8. **One step, several events.** When one step can cross several events (meter full, obstacle,
   landing, finish), resolve them in time order inside the step, one exactly at the step's end
   included. Computer players and meters move only after the start. Test each ordering.
9. **Scores you can reach.** Measure the best possible score with the real judge spread, and set
   a computer opponent's cap per case from a simulation.
10. **Shared global scope.** A game's classic scripts share one global scope: grep the version
   folder before adding a top-level name. Before changing the shape of a saved unfinished round,
   read "Progress and saves" in `docs/making-games.md`: it gets a new key, while lasting saves
   stay shared (rule 5).
11. **Gestures.** Track the largest displacement during a touch, not where it ends.
