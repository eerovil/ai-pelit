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
  own phone before calling a touch bug fixed.
- **A frame gets no safe areas.** Inside an `<iframe>`, `env(safe-area-inset-*)` is 0; the page
  around it must hand them in (Ottelu v2 sets the frame's `#safe` padding).
- **Two thumbs, two corners.** Put the buttons a round uses most where thumbs rest: the lower
  corners in landscape, the lower edge in portrait. Leave the top-left for the "‹ Pelit" chip.
- **Sound follows the game, not the finger.** Piano v5 plays each note when the song reaches it;
  a tap does not play it. Short sounds, only after the first tap (Web Audio rule in AGENTS.md).

## Difficulty

- **Every level can be beaten.** Sormiskeitti v2: level 8 could not be passed. Write a test that
  plays or checks each level's layout, as Orava's test checks every cone can be reached.
- **The computer must not be too strong or too weak.** Areena v2 had to be made easier (slower,
  weaker opponent); Lentopallo v3 harder, because standing still and sending every ball back won
  half the points. Try the laziest way to play and the most reckless; neither should win easily.
  A computer player gets a small, random error and a reaction time, not perfect play.
- **Start easy and grow.** The first round teaches the game. New things arrive in later levels
  (Orava: the marten from level 2, the hawk from level 3; Hiihto: a road crossing on levels 3, 5, 7).

## Progress and saves

- **Save the moment it is earned.** Save the level reached and the best score as soon as they
  happen, not only at the end of a perfect run: Sormiskeitti v3 ("Ei tallennu progress"),
  Piano v2 (save after every song, even without a fail).
- **Continue where the player was.** Start at the highest level reached and let them pick an
  earlier one (Piano v3). A new level gives fresh lives.
- **A reload is not a lost round.** If the page reloads or the phone turns mid-round, the round
  goes on or comes back (Jään alla saves the submarine's place on each dive; rule 4 in AGENTS.md
  for turning).

## Screens and layout

- **Design for portrait and landscape from the first version.** Every game needed a new version
  for landscape (#95). Menus and end screens fit without scrolling in both (two columns sideways),
  and turning the phone keeps the round.
- **Check the small phone too.** Play at 360 × 740 and 390 px wide, and sideways at 740 × 360.
  Long Finnish words and many player names must still fit (Hiihto v6's waiting line).
- **The end screen says what happened and offers the next step.** The result, the record, and one
  big button to play again; the round's high-score list if the game has one.
- **Tell players apart.** The player's own character must stand out from the computer's
  (Kaahari: the yellow driver was too like the player's own kart).

## Playing with friends

- **Use `rooms.js`, and test with three or more phones.** Hiihto v6 had to make sure races of more
  than two work. Test a phone reloading mid-round and a phone that leaves.
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
  function let a test set up a scene and run the game frame by frame (see `tests/test_orava.py`).
  A test that waits on real time is slow and flaky on CI.
- **Test what a player would complain about**: a level that cannot be passed, a tap that misses,
  a save that is lost, a second round after a finished one, a 390 px phone.
- **Split a big version into files** once it passes about 2000 lines (#161): `index.html` plus a
  few plain `.js` files in the same folder, each one part of the game (world, screens, sound),
  loaded with classic `<script src>` tags. A file you can read whole is one you can change safely.
- **Play it yourself before you hand it over**, a whole round and a second one, in both
  orientations. Fix what feels wrong even if no test says so.

## Phone gotchas

What only showed on a real phone, never in the headless tests. When you hit a new one, add a line
here in the same pull request (AGENTS.md says so), naming the version that taught it.

- **Not `100dvh`.** Yöajo v1 (#181): the installed app opens full screen, and on Android `100dvh`
  kept the old, smaller-screen height, so the bottom of the game was under the screen's edge until
  the system bars were swiped in and out. Fill the screen with a fixed box (`position:fixed;
  top:0; bottom:0`) and compare its `getBoundingClientRect()` with the size you drew for every
  frame (`fitCheck()` in Yöajo v2's `ui.js`); listen to `fullscreenchange` too.
- **A tap lands where the finger is** (Hiihto v5, see "Controls that feel right"): draw for the
  canvas's own box, not `innerWidth × innerHeight`.

## When a change is about feel

When Eero is unsure how something should feel ("prototyyppi:" in the request, as in Trampoliini v3
and Voimistelu v4), build the change in the new version, let him play it on his phone, and tune
it from what he says before marking it ready. Remove any testing buttons first (Voimistelu v5).
