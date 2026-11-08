# Making a good game — best practices

AGENTS.md says what a game must do (the rules, the folders, the shared scripts). This guide says
how to make one that plays well, from what Eero asked to change after playing. Each point names
the version that taught it, so you can read the code that fixed it.

## Before you write code

- **Read the request as a player would.** A short request ("Kirkkis peli", "Lentopallo. Sivusta
  kuvattu 1v1") names the heart of the game; build that well before adding extras. When it names
  a real sport, game or tradition, get its words and rules right from a real source: Kirkkis v4
  had to replace made-up calls ("Kirkkis Aino!") with the real ones ("Ainon nimet!").
- **Know what a round is.** Decide how a round starts, what the player does every second, how it
  ends, and what makes them want another. Write it down in the pull request before you build.
- **Look at a game that is close.** Copy what works: the menu and end screen of a recent game,
  the room handling of one that uses `rooms.js`, the 3D setup of Pallorata or Hiihto v7.

## Controls that feel right

- **Every control answers at once, and visibly.** Trampoliini v2: pressing bends the knees and
  holding keeps them bent, letting go is the jump; v1's plain jump button "was not satisfying".
  Show the press in the character, not only in the button.
- **Be generous with timing.** A tap a little late still counts (Sormiskeitti v4: a tap just past
  the ramp's edge is still a perfect ollie). A hit window is the same length in time for every
  note or obstacle, never smaller when things move fast (Piano v4). One press takes one target,
  the oldest one in reach (Piano v5).
- **Help the player's aim a little.** Voimistelu v4–v5: in the air the arms turn towards a bar
  that is near, so a near miss is caught. The player should lose to their own mistake, not to a
  few pixels.
- **Show what the player needs to judge.** If a rhythm, speed or zone matters, draw it: Hiihto v4
  added a speed reading at the top and a rhythm bar, Piano v4 lit the hit zone on every lane.
- **A tap lands where the finger is.** Size the drawing from the canvas's own box
  (`getBoundingClientRect()`) and read every touch against that same box. Hiihto v5 drew for
  `innerWidth × innerHeight` but stretched the canvas to `100dvh`; on phones where the two differ
  every menu tap landed below the button (fixed in v6).
- **Keep buttons apart, and act on the finger lifting.** Hiihto v5: picking a wax sometimes
  opened the friends game, because the buttons were close and acted on touch-down. Put a button
  that leaves the screen away from the ones used every round, and fire it on `pointerup` inside
  the button.
- **Never swap one game frame for another in the same page.** Ottelu v1–v2 (#168) ran each
  event in an `<iframe>` and, between events, removed it and added a new one. On Eero's phone the
  second frame then took no taps at all, every time (the first frame, and the same event after a
  reload, played fine). The test phone and headless Chromium did not show it, and adb taps
  reached the game, so neither proves a fix. Load the page afresh for each new frame (Ottelu v3
  reloads between events), and let Eero try a preview (`wrangler pages deploy … --branch`) on his
  own phone before calling a touch bug fixed. In the #388 prototype both a frame given a new
  address and a frame replaced by a new one kept their taps on his phone, so the cause is not
  known; the room page (`public/huone/`) changes its frame's address, and the next change of the
  kind needs his phone again.
- **A frame gets no safe areas.** Inside an `<iframe>`, `env(safe-area-inset-*)` is 0; the page
  around it must hand them in (Ottelu v2 sets the frame's `#safe` padding).
- **A frame's window outlives its page.** After the frame loads a new page, `contentWindow` is the
  same window with a new document, so anything watching the old one is dead (`w.win.document !==
  w.doc` in `rooms.js`). Test several loads in a row, and that nothing piles up.
- **A pull-back fits on the screen.** A control the finger drags away from (a sling, a throw
  pulled back) needs its whole range between the start point and the screen's edge, plus the
  finger. Curling v1 put the stone 74 px above the bottom for a 190 px pull, so upright only the
  weakest throws were possible; v2 places it `pull + 30` px above the edge (#293). Test it with a
  drag that stays on the screen, as a finger must: a mouse can run past the edge and hide the fault.
- **Two thumbs, two corners.** Put the buttons a round uses most where thumbs rest: the lower
  corners in landscape, the lower edge in portrait. Leave the top-left for the "‹ Pelit" chip.
- **Sound follows the game, not the finger.** Piano v5 plays each note when the song reaches it;
  a tap does not play it. Short sounds, only after the first tap (Web Audio rule in AGENTS.md).
- **Real sounds over beeps.** A thud or a footstep from the shared library
  (`lib/aanet-5/`, "Sound effects" in AGENTS.md) tells the player what happened better than a
  tone. Pituushyppy v7: the sand. Each sound stands alone: a file that fails to load must not
  silence another event or its beep, so test the partly loaded cases too.
- **No crowd noise, no loud sounds (#337, Eero's choice).** No applause, shouting crowd, crowd's
  "ooh" or cheer: a good moment gets a quiet short blip (`onnistui` at about 0.3), a near miss or a
  fall nothing more than its own thud. Keep every sound about as loud as the rest; `aanet-5`
  has the softer files Eero picked by ear (#355) and plays its loudest quieter. A cheer or other
  sound that every phone in a room plays at each friend's tap is quieter still (0.08, #355).

- A choice a player repeats turn after turn gets one step for all of them: Korkeushyppy v13 and Seiväshyppy v14 (#399) pick the next height from a panel, not pass ten heights one at a time.
- **Judge a tap at its own moment** (#404). A game moves only when a frame is drawn, so a tap
  between frames reads a moving value up to 17 ms old, and in a game about timing that is real
  points. When a tap is scored by where something moving is, run the game on to `e.timeStamp` in
  the input handler first: `catchUp(e)` in Moukarinheitto v12 (`docs/diagrams/reilu-ajoitus.md`).
  With fixed physics steps, run the whole steps and add the rest when judging (Trampoliini v11).
  Run the whole gap, in bounded steps, before the clock moves on, and test a gap near the bound.

## Difficulty

- **Every level can be beaten.** Sormiskeitti v2: level 8 could not be passed. Write a test that
  plays or checks each level's layout, as Orava's test checks every cone can be reached.
- **The computer must not be too strong or too weak.** Areena v2 had to be made easier (slower,
  weaker opponent); Lentopallo v3 harder, because standing still and sending every ball back won
  half the points. Try the laziest way to play and the most reckless; neither should win easily.
  A computer player gets a small, random error and a reaction time, not perfect play.
- **The field stays playable for a whole game.** Mölkky v1: pins knocked over slid and rolled so far that late in a game every one stood past the longest throw, or off the screen to the sides. Play a whole game of computer throws in a test and check the targets stay within reach and in view (Mölkky v2).
- **Doing nothing must not score.** Tikanheitto v1–v6: the sight stayed on the 10 and the hand hardly swayed, so tapping alone gave a perfect 300, and the top of the list was full of them. v7's hand shakes, settles and tires, and the sight leaves the target after each dart. Measure a whole game played the laziest way, and read the live high-score list: a list topped by the highest possible score says the game is too easy.
- **Harder rules start a new list.** When points no longer compare with the old ones (Mäkihyppy v9, Tikanheitto v7), give the new game its own list and its own saved best and keep the old list beside it: a phone that holds a best it can no longer beat would never send a score again.
- **A script's hit is not a person's.** Kiekkoammunta v1: a scripted drag hit skeet's crossing discs, but only inside about 0.02 s, and Eero found it too hard. For a moving target, work out how much timing a hit forgives and test that a person's 60 ms still hits (v2).
- **Start easy and grow.** The first round teaches the game. New things arrive in later levels
  (Orava: the marten from level 2, the hawk from level 3; Hiihto: a road crossing on levels 3, 5, 7).

## Progress and saves

- **Save the moment it is earned.** Save the level reached and the best score as soon as they
  happen, not only at the end of a perfect run: Sormiskeitti v3 ("Ei tallennu progress"),
  Piano v2 (save after every song, even without a fail).
- **Continue where the player was.** Start at the highest level reached and let them pick an
  earlier one (Piano v3). A new level gives fresh lives.
- **A saved round in a new shape gets a new key.** Lasting saves (level, records) are shared by
  every version, but a version that saves an unfinished round in a different shape keeps it under
  its own key (Pilkkiminen v2 `kisa2`, v3 `kisa3`): a phone that still has an older version
  cached (only the newest is kept since #346, but a phone may open its old copy until the next
  update) must never find a save that version cannot read.
- **A reload is not a lost round.** If the page reloads or the phone turns mid-round, the round
  goes on or comes back (Jään alla saves the submarine's place on each dive; rule 4 in AGENTS.md
  for turning).

## Screens and layout

- **Design for portrait and landscape from the first version.** Every game needed a new version
  for landscape (#95). Menus and end screens fit without scrolling in both (two columns sideways),
  and turning the phone keeps the round.
- **Check the small phone too.** Play at 360 × 640 (rule 4's smallest), 360 × 740 and 390 px wide,
  and sideways at 740 × 360, each size and state the request names. Long Finnish words and many
  player names must still fit (Hiihto v6's waiting line). Check full screens, not only empty ones,
  and the fastest state of the game. Open a new page per orientation; resize a live page only to
  test turning mid-round.
- **The end screen says what happened and offers the next step.** The result, the record, and one
  big button to play again; the round's high-score list if the game has one.
- **Tell players apart.** The player's own character must stand out from the computer's
  (Kaahari: the yellow driver was too like the player's own kart).

## Playing with friends

- **Use `rooms.js`, and test with three or more phones.** Hiihto v6 had to make sure races of more
  than two work. Test a phone reloading mid-round and a phone that leaves, through real browser
  actions: every promised player count, a rejoin that cleans up what the phone held, two phones
  acting at once, several turns with no input, and a new round after a finished one. Keep players
  under a stable id, not a place in a list, and reset their positions on start.
- **The host decides.** One phone runs the round (who scored, a false start, the course) and the
  others draw what it sends; each phone may check its own collisions (Kaahari v2) when that feels
  fairer, but the result comes from the host.
- **The game still plays alone.** Computer players fill the empty places.

## 3D

- Use the shared three.js and the "3D games" part of AGENTS.md. Keep the game's rules in plain
  numbers and draw them with three.js, so tests can drive the game without WebGL.
- A slow phone runs short of pixels, not shapes: step down the pixel ratio, then the shadows.

## Build it so it can be tested

- **Keep the game's state where a test can reach it.** Top-level variables and a `step(dt)`
  function let a test set up a scene and run the game frame by frame (see `run()` and `step(1 / 60)` in `tests/test_orava_v4.py`).
  A test that waits on real time is slow and flaky on CI.
- **Test what a player would complain about**: a level that cannot be passed, a tap that misses,
  a save that is lost, a second round after a finished one, a 390 px phone, a timeout, running out
  of what a round spends, a finish tapped twice, a reload at each change of mode, an old result left
  showing after a mode switch. Test the whole change of state, not only the helper or the win.
- **Set up by state, play by real controls.** A test may place the scene, but proves a game can be
  played only through the taps a player makes, and it asserts the game's own decision, never a
  state it forced.
- **A flaky test wants a signal, not a longer wait.** Wait on observable state with a predicate that
  returns a boolean (an async helper's Promise is always truthy), such as the guest's first snapshot
  before the host acts. Run a tightly timed change in one `page.evaluate`, seed randomness, and
  assert stable state, never animated pixels. Never weaken an assertion, and treat a browser error
  in a passing test as a failure.
- **Split a big version into files** once it passes about 2000 lines (#161): `index.html` plus a
  few plain `.js` files in the same folder, each one part of the game (world, screens, sound),
  loaded with classic `<script src>` tags. A file you can read whole is one you can change safely.
- **Play it yourself before you hand it over**, a whole round and a second one, in both
  orientations. Fix what feels wrong even if no test says so.

## Phone gotchas

What only showed on a real phone, never in the headless tests. When you hit a new one, add a line
here in the same pull request (AGENTS.md says so), naming the version that taught it.

- A page in a frame that loads the next page fires `visibilitychange` hidden on its way out, and anything held there goes with it, so what a finger holds through a change belongs on the page around the frame. With the first finger on that page, Chromium sends the frame pointer events but no touch events, so read pointers (room page, #394).
- Full screen asked for inside a frame fills the screen with that frame alone, over everything on the page around it: Ottelu v7's events in a room hid the room bar and the 🎤, so `back.js` passes such a request on to the room page (#394).
- **Not `100dvh`.** Yöajo v1 (#181), seen on Eero's Android phone: in the installed app, which
  opens full screen, the bottom of the game was under the screen's edge until the system bars were
  swiped in and out. The likely cause, not proven (a test phone did not show it), is `100dvh`
  keeping the height from before full screen. Fill the screen with a fixed box (`position:fixed;
  top:0; bottom:0`) and compare its `getBoundingClientRect()` with the size you drew for every
  frame (`fitCheck()` in Yöajo v2's `ui.js`); listen to `fullscreenchange` too.
- **A prototype the phone never updates.** Yöajo v4's prototype (#181): `sw.js` served the played
  version folder from its cache, so Eero saw no edit and could not clear it on the phone. Serve a
  prototype with `scripts/serve_prototype.py` (AGENTS.md, "Running it locally").
- **The iPhone's silent switch mutes Web Audio** (#381, reported by Eero; the same as stemmanauhat-cf#100): Safari treats a page's Web Audio as ringer sound. `back.js` sets `navigator.audioSession.type = 'playback'` (iOS 17 and later) for every game, so a game needs nothing; one that records sets `'play-and-record'` first, as `rooms.js` does. The phone also stops the sound on a lock, a call or another app, in a state (`interrupted`) a check for `'suspended'` misses; `back.js` resumes it on the next tap and when the page is back (Piano v10).
- **A held button selects text on an iPhone** (#457, Raketti v2's thrusters): Safari reads only `-webkit-user-select`, so `user-select:none` alone left the page's text selectable on a long press. `back.js` now turns selection and the copy callout off in every game (text fields keep it), so a game needs nothing; a rule of a game's own still wins.
- **A still game must not draw every frame.** Pasianssi v1 (#382) heated the phone: redrawing the whole table 60 times a second with nothing moving took 45–48 % of the test phone's processor, against 29 % on its home screen, and no test or screenshot showed it. A game that waits for the player draws only when something changes (`ask()` in Pasianssi v2), and watches the canvas's size with a `ResizeObserver` instead of a check every frame. An easing that only ever gets nearer (a camera, Puhelinkoppi v9) must land on its target, or it never rests.
- **Something that moves forever keeps a still game awake.** Marjakori's idle hint wobbles for as long as nobody plays, so drawing only on a change would still have drawn 60 times a second. As a page element with a CSS animation (`#hint` in Marjakori v2) it needs no canvas redraw, but the phone still shows a new frame each time: an untouched level took 25 % of the test phone's processor with the hint, 16 % without it (home screen 17 %, canvas hint 41 %).
- **A full-screen gradient is the dearest thing to fill every frame.** Skuutti v4 (#414) stayed at 30 frames a second on the test phone, its graphics process busy, until the sky stopped being filled each frame. Turning parts off, one at a time, on the phone found it (the fence, ramp and rider made no difference). Put what never moves on a canvas of its own under the game's and clear the top one each frame (60 frames a second): copying a finished picture over the whole screen each frame reached only 42. Text is the dearest thing for the processor: write a score strip only when it changes.
- **Any picture moving 60 times a second costs a fixed price.** On the test phone Skuutti v5 (#414) cost 30–32 % of the processor at 60 frames a second even with one small canvas and a rectangle, and 19–20 % with nothing changing, whatever the size: drawing less stops helping there, and only fewer frames lower it. Steady 30 cost 28 %.
- **A tap lands where the finger is** (Hiihto v5, see "Controls that feel right"): draw for the
  canvas's own box, not `innerWidth × innerHeight`.

## When a change is about feel

When Eero is unsure how something should feel ("prototyyppi:" in the request, as in Trampoliini v3
and Voimistelu v4), build the change in the new version, let him play it on his phone, and tune
it from what he says before marking it ready. Remove any testing buttons first (Voimistelu v5).

A room game message exceeding `MSG_MAX` in `rooms/worker.js` (64 000 characters; 16 000 until #375) is silently discarded by the Worker, and the phone it was for waits for good (Last Signal v15, #375). Send large multiplayer state per recipient, split it into smaller packets, and apply only a complete snapshot. Measure `JSON.stringify` with all fields, including the recipient `to` (Pilkkiminen v5, #345).
