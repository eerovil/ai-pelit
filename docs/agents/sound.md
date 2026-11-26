# Sound effects

Read when a game plays recorded sounds, or for a change to `public/lib/aanet-*/`.

Moved here unchanged from `AGENTS.md` (#558), which keeps a short form and links here. "Rule N" means the numbered rules in [rules.md](rules.md); a section named in quotes is listed in [AGENTS.md](../../AGENTS.md).

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
