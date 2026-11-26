# Athletics meets

Read for an athletics event (group `yleisurheilu`) or a change to `public/lib/yleisurheilu-*/`. Their shared outfits are under "Outfits" in [online-extras.md](online-extras.md).

Moved here unchanged from `AGENTS.md` (#558), which keeps a short form and links here. "Rule N" means the numbered rules in [rules.md](rules.md); a section named in quotes is listed in [AGENTS.md](../../AGENTS.md).

- **Athletics meets (#165).** A field event (a throw or a jump, group `yleisurheilu`) loads
  `<script src="../../../lib/yleisurheilu-12/kisa.js"></script>` (the newest folder) after `rooms.js` and calls
  `AiPelitKisa.meet({...})`: the library runs the field of twelve, the turns, the standings and
  the results board, the saves and the whole room (host, turns, rejoining, the computer taking an
  away phone's turns), so a new event gets playing with friends without room code of its own. The
  game keeps its own attempt and drawing. The options are listed at the top of `kisa.js`;
  Pituushyppy v8 is the model. At the end, `K.drawPodium(ctx, box)` draws the medal ceremony
  (#176): the top three on the podium, the medals hung around their necks, the final standings
  under it; it stays until the player taps it away (the game passes its taps to `K.skip()`).
  Like `lib/three-r*/`, a folder never changes once published: a fix goes in the next one
  (`yleisurheilu-12/`), used by the next versions. From `yleisurheilu-5/` (#297) the meet waits with
  friends only for the phone on turn (rooms.js `turns()`), a friend may leave and come back
  ("Palaa kierrokseen"), the host skips an away friend's turn, and the game draws the friends not
  on turn as cheering spectators with `K.drawFans(ctx, box)`. From `yleisurheilu-7/` (#341) they stay in
  the background: the game calls `K.drawFans(ctx, {..., walk: true})` early in its scene, before the
  athlete (in a stadium behind the boards, which hide their legs), and offers a tap on its scene to
  `K.tapFans(px)` first, which walks a spectator's own figure there on every phone; nobody walks by
  themselves (Eero's choice). From `yleisurheilu-8/` (#373) the game passes `scroll` too, how many px
  the background behind them has moved since its athlete stood at the start (0 there); a tap on another
  spectator climbs onto their shoulders (a column at most four high), so `K.tapFans(px, py)` takes
  the tap's y too. From `yleisurheilu-9/` (#395) nobody runs after it (Eero's choice): the whole row only
  slides with the background, a little slower than it (0.8 of its speed), and stops when it stops, so it may
  leave the screen until the next turn; legs move only on a tapped walk. From `yleisurheilu-10/` (#469) the podium and the spectators are
  `AiPelitOutfits.figure()`, facing out, with heads that look around and cheer; from `yleisurheilu-11/` the official hangs the medals with its own arms (`figure()`'s `reach`); from `yleisurheilu-12/` (#480) the game passes `glide` (and loads `lib/sulava-1` before it), and the friend on turn glides on the phones watching (Pituushyppy v20 is the model). Moukarinheitto, seen
  from above, uses it too, with no `scroll`, so its row stays where it is. The bar-height format (high jump, pole vault)
  is `korkeus.js` beside `kisa.js`, loaded after it from the same folder (Korkeushyppy v2 from
  `yleisurheilu-1/`). A new format may be added beside them as a new file.
