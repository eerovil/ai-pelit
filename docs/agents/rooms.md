# Live rooms (multiplayer), voice and smooth movement

Read before you design, build or change a game played with friends, or touch `public/rooms.js`, `rooms/`, the room's voice or `public/lib/sulava-*/`.

Moved here unchanged from `AGENTS.md` (#558), which keeps a short form and links here. "Rule N" means the numbered rules in [rules.md](rules.md); a section named in quotes is listed in [AGENTS.md](../../AGENTS.md).

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
    game in a frame under a slim room bar (code, players); the page draws the 🎤 chip over the frame, where it sits in the game alone, so a finger on it stays through a game switch (#394). The game's `rooms.js` talks through
    the page's connection, so a game switch reloads only the frame and the calls stay up; leaving
    the room sends the phone to the game's own page. A game needs nothing for it. A game inside
    another frame keeps the room in its own page, and so do the tests:
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
    the 🎤 chip `rooms.js` draws, and for a second after the lift (#398), the others in the room hear it; the sound goes straight between
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

- **Smooth movement (#480).** A room game draws the other players from
  `<script src="../../../lib/sulava-1/sulava.js"></script>` (the newest folder), loaded before its own
  script: one `AiPelitSulava.track({ keys, angles, jump })` per remote player, `push(stamp, spot)` on each
  message (the stamp is the sending phone's `AiPelitSulava.now()`, sent with the spot; a host forwards a
  friend's spot with the friend's stamp), `snap()` on a jump the game knows of, and `at()` each frame, which
  gives the spot a moment back (0.06–0.25 s, learnt from the messages' gaps) between two spots. The phone's
  own player never goes through it. Like `lib/yleisurheilu-*/` a folder never changes; a fix is
  `sulava-2/`. Last Signal v17 is the model; the other room games with moving players follow, most-played
  first (Eero's choice).

- **Switching games in one room (#354).** Between rounds the host can choose a new game from
  `catalog.json`; only games whose `room.max` fits every member are offered. Every phone follows
  into the new game with the same room code and friend identity (no `bye` when switching), and a
  short sessionStorage handoff tells the next page that its phone is the host. A room is deleted
  immediately when its final member deliberately leaves (including with the "‹ Pelit" chip);
  dropped connections still have six hours to rejoin. On the shelf and friends page, invitations
  are shown with Liity/Ei, not duplicated by the invitation banner.

Before a room-game design, read `public/rooms.js` for a host reload (`_lobby` ends the round),
pause, hello and score caps. Give throws and taps a play number and say what the pause stops.
The host enforces limits from its own clock. Stamp live messages with the capped per-frame clock
that moves the figure, send the sender's running signed angle, and add a stall test. Commit a
counter only after the play is confirmed, and reset it per match.
