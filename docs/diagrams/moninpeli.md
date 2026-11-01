# Moninpeli: playing with friends in one room

How 2–8 phones play one game together. One phone makes a room and runs the game; every phone
moves its own player and draws the game from its own side. The room on Cloudflare only passes
messages between the phones. Everything a game needs for a room is one shared script,
`public/rooms.js` (#34): the room screen, reconnecting, the pause for a phone that dropped off, and
saving a round's result once. A game writes only its own part; where a box is a game's, it names
Kirkkis v3 (`games/kirkkis/v3/index.html`, #57), whose messages are `kr`, `ks`, `kme` and `kfin`;
v4 (#67) sends the same, with the seek clock during a recount (`sl`) and a "Kaikki pelastettu!" event.
Kirkkis v2 (#27) keeps its own copy of the whole flow, from before the library.
Voice (#322): while someone holds the 🎤 chip, the others in the room hear them; the sound goes
straight between the phones, and the room only passes on the call's setup messages.

```mermaid
flowchart TD
  subgraph Peli[Pelin oma koodi]
    G1[👥 Pelaa kavereiden kanssa] --> L1
    G2[Kierros alkaa: isäntä pyörittää peliä] --> G3[Isäntä lähettää tilanteen monta kertaa sekunnissa]
    G6[Oma sormi liikuttaa omaa pelaajaa, sijainti isännälle]
    G4[Piirtää pelin oman pelaajan silmin]
    G5[Kierros päättyy: tulos kaikille, myös poissa olleille]
    G7[Tietokone ohjaa poissaolevaa]
  end
  subgraph Lib[rooms.js: yhteinen kaikille peleille]
    L1[Huoneruutu: Luo huone tai Liity koodilla] --> L2[Koodi ja QR-koodi, pelaajalista]
    L10[Avoimet huoneet: liity napautuksella] --> L1
    L2 --> L11[🌍 Julkinen-kytkin isännällä]
    L2 --> L12[Pelin omat valinnat pelaajalistan alla]
    L2 --> L3[Aloita kierros]
    L4[Yhdistää uudelleen, palaa huoneeseen latauksen jälkeen]
    L5{Onko joku kierroksen puhelin poissa?}
    L5 -- Kyllä --> L13{Vuoroissa pelattava peli?}
    L13 -- Ei --> L6[⏸ Odotetaan, isännällä Jatka ilman heitä]
    L13 -- Kyllä, ei hänen vuoronsa --> G2
    L13 -- Kyllä, hänen vuoronsa --> L14[⏸ Odotetaan, isännällä Ohita vuoro]
    L15[↩ Palaa kierrokseen KOOD]
    L7[Tallenna tulos kerran per kierros]
    L8{Väärä peli tai versio?}
    L8 -- Kyllä --> L9[Avaa oikean pelin version]
  end
  subgraph Cloudflare
    C1[Huone: välittää viestit, muistaa pelin ja version]
    C2[Julkisten huoneiden lista]
  end
  subgraph Hylly[Pelihylly]
    S1[Etusivun avoimet huoneet: kaikki pelit, Liity]
  end
  L11 --> C1
  C1 -- julkinen, odottaa, tilaa --> C2
  C2 --> L10
  C2 --> S1
  S1 -- ?huone=KOODI --> L2
  L1 --> C1
  C1 --> L8
  L8 -- Ei --> L2
  L3 --> G2
  G3 --> C1
  G6 --> C1
  C1 --> G4
  C1 --> L4
  L4 --> G2
  C1 --> L5
  L5 -- Ei --> G2
  L6 --> G7
  L14 --> G2
  L15 --> C1
  G7 --> G2
  G2 --> G5
  G5 --> L7
  L7 --> L2
  subgraph Puhe[Puhe: rooms.js, kaikissa huoneissa]
    V1[🎤 Puhe-kytkin huoneruudussa, oletuksena päällä]
    V2[Puhelinyhteys jokaiseen huoneen puhelimeen]
    V3{Pitääkö pelaaja 🎤-nappia pohjassa?}
    V3 -- Kyllä --> V4[Mikrofoni päälle, ääni muille]
    V3 -- Ei --> V5[Mikrofoni kiinni]
    V6[🔊 Nimi puhuu: muut kuulevat]
    V7[🔇 Mykistä pelaaja pelaajalistassa]
  end
  subgraph CfPuhe[Cloudflare: puhe]
    C3[Huone välittää yhteyden avausviestit _rtc kenelle tahansa]
    C4[GET /api/voice/ice: TURN-tunnukset]
    C5[TURN-välityspalvelin, jos suora yhteys ei onnistu]
    C6{Tämän kuun käyttö alle 800 Gt?}
    C7[Koneen tarkistus kerran tunnissa: käyttö Cloudflarelta]
  end
  L2 --> V1
  V1 --> V2
  V2 --> C3
  V2 --> C4
  C7 --> C6
  C4 --> C6
  C6 -- Kyllä --> C5
  V2 -.-> C5
  G2 --> V3
  V4 --> V6
  V7 --> V6
  class G1,G2,G3,G4,G5,G6 teal
  class L1,L2,L3,L4,L7,L9,L10,L11,L12,L15 blue
  class C1,C2,C3,C4,C5,C7 violet
  class V1,V2,V4,V5,V6,V7 blue
  class S1 green
  class L5,L8,L13,V3,C6 amber
  class L6,G7,L14 rose
```

## Colours

- **teal**: the game's own code, the only part a new multiplayer game writes
- **blue**: the shared `public/rooms.js`, the same for every game
- **violet**: the room on Cloudflare (`rooms/worker.js`), which only passes messages on
- **amber**: a check that decides the path
- **rose**: a phone that dropped off
- **green**: the shelf (`public/app.js`)

## Boxes

- **👥 Pelaa kavereiden kanssa**: the game's own menu button; it calls `AiPelitRooms.open()`. The game loads `<script src="../../../rooms.js" data-game="<slug>" data-min="2" data-max="5">` before its own script.
- **Huoneruutu: Luo huone tai Liity koodilla**: `public/rooms.js` `build()` and `render()`, in Finnish, the same in every game. A new room gets a random 4-letter code (no I, O, Q, W, X, Z); a code in use gets another. The name is the phone's one nickname (`ai-pelit:_pelaaja:nimi`, shared with the high-score lists), or an animal name kept in `ai-pelit:_huone:nimi`.
- **Avoimet huoneet: liity napautuksella**: `readList()` and `renderList()` on the first page of the room screen (#50): this game's public rooms from `GET /api/rooms?game=<slug>`, read on opening and every 5 seconds, as buttons "KOOD · 2/5 pelaajaa" (no names). A tap joins like a typed code, so a room of another version opens that version. Hidden until the first answer, so with no connection nothing shows.
- **Etusivun avoimet huoneet: kaikki pelit, Liity**: `showRooms()` in `public/app.js` (#203): at the top of the shelf's front page, every game's public rooms from `GET /api/rooms` (no `game`: up to 30, newest first, each naming its game), read when the shelf shows, every 10 seconds while it is on screen and on coming back to it. Each row is the game's picture and name, "v<N> · koodi KOOD · 2/5 pelaajaa" and "Liity", a link to `games/<slug>/v<v>/?huone=<KOOD>`, which joins that room in the room's own version; back from it goes to the game's page, then the shelf. A game or version the shelf does not have is left out; with no rooms, or when a read gets no answer (also after an earlier one did), the whole section is hidden.
- **🌍 Julkinen-kytkin isännällä**: the host's checkbox in the room (`net.pub`, off for a new room, kept over a reload in `ai-pelit:_huone:nyt`). `tellList()` sends the room `{t: '_list', on}`: on while public, no round runs and the room screen shows on the host (not during the game's own end screen), and again every minute while on.
- **Julkisten huoneiden lista**: one more object of the `Room` class, named `lobby` (`lobby()` in `rooms/worker.js`). Each room's `tell()` puts itself on it while the host's `_list` is on, the host is connected, a game is named and there is space, and takes itself off otherwise. Newest first, at most 10 per game; a listing not refreshed for 3 minutes is dropped. Only `GET /api/rooms?game=` and, for the shelf, `GET /api/rooms` reach it from outside (`publicRooms()` in `server/api.js`).
- **Koodi ja QR-koodi, pelaajalista**: the code, a QR code of `<version>/?huone=<KOODI>` drawn in the page (`qrMatrix()`), and who is in, the host with 👑, someone without a connection greyed out. A QR link joins at once; `rooms.js` then clears `?huone=` from the address and keeps the page's history state, so the "‹ Pelit" chip still knows where up is (#68). On a phone on its side (#95) the room screen is two columns, the code and QR left and the players (in two columns), the game's own choices, 🌍 Julkinen and "Aloita kierros" right, so a full room of 8 fits 740 × 360 without scrolling; a CSS `@media (orientation:landscape) and (max-height:500px)` block in `rooms.js`, so upright nothing changes.
- **Pelin omat valinnat pelaajalistan alla**: `extra(node)` in `public/rooms.js`: a game's own element shown in the room under the player list, kept up to date by the game. Hiihto v3 puts the host's level and style there (`roomControls()`); Ottelu v1 (#168) puts the host's event picker there (`hostPick()`).
- **Aloita kierros**: host only, once `data-min` phones are connected. Sends `_start` with the round id and players, and fires the game's `on('start')` on every phone.
- **Kierros alkaa: isäntä pyörittää peliä**: the game's `on('start')`. The host runs the rules and the clock, and stops the clock while `AiPelitRooms.paused`. Kirkkis: `hostStart()` makes the cast (the phones in the round, then computer players up to five), picks the seeker and sends the round (`kr`); a guest waits for it (`phase = 'wait'`), and builds its cast from it (`castFrom()`).
- **Isäntä lähettää tilanteen monta kertaa sekunnissa**: the game's `AiPelitRooms.send()`. A phone that joined after the round began hears none of it (`net.listening` in `onMessage()`), and waits for the next round. Kirkkis: `hostSend()` (`ks`), 12 times a second, with what happened since (`happen()`).
- **Oma sormi liikuttaa omaa pelaajaa, sijainti isännälle**: a guest moves its own player at once and sends where it is (`send()`); the host hears it in `on('message', (msg, from))`. Kirkkis: `guestStep()` (`kme`).
- **Piirtää pelin oman pelaajan silmin**: the game's drawing, from this phone's player. Kirkkis: `draw()` with the fog cut by that player's field of view.
- **Huone: välittää viestit, muistaa pelin ja version**: `rooms/worker.js` `Room`, in the `ai-pelit-rooms` Worker, at `/api/rooms/<KOODI>` through `server/api.js` (`ROOMS` binding). Each phone connects with a secret key and is known by a hash of it, so nobody can take another phone's place. The host's messages go to all (or `to`), the others' to the host with `from`; `peers` says who is in and connected. It keeps the host's `game`, `v` and `max` (2–8, default 5) and sends `game` and `v` in `peers`. An empty room is forgotten after 6 hours.
- **Väärä peli tai versio?**: `onPeers()` on a guest's first `peers`: the room's `game` and `v` against the page's own. A room that names no game (made by Kirkkis v2, from before the library) is left at once with "Huone on toisessa pelissä."
- **Avaa oikean pelin version**: the guest moves to `../../<game>/v<v>/?huone=<KOODI>`, which joins the room there. Back still goes up (#68): a game opened from the shelf has its page below it, so another version takes the game's place over that same page; another game steps back to the page, which `public/app.js` (`openFromRoom()`) turns into the new game's page once it has loaded, before opening the game over it. When the new game sits under another parent than the old one (a shelf group, #153), `openFromRoom()` first makes the history below its own: from a shelf game into a grouped one it puts the group's page between, from a grouped game into one outside the group it steps back to the group's page and turns that into the new game's page over the shelf; the room screen steps back only once, however many room updates arrive meanwhile. A game opened any other way is simply replaced.
- **Yhdistää uudelleen, palaa huoneeseen latauksen jälkeen**: `connect()` retries with a growing wait; the room this tab is in is kept in `sessionStorage` (`ai-pelit:_huone:nyt`). On every connection a guest says `hello`; the host sends a phone in the round `_start` again and fires `on('hello')`, so the game sends the round as it is. A host that comes back without its round (a reload) sends `_lobby`, and everyone goes back to the room. Kirkkis: `on('hello')` sends that phone `kr`.
- **Onko joku kierroksen puhelin poissa?**: `waitingFor()`: a phone in the round with no connection, unless the computer took it; on a guest also the host, or its own connection. The host sends the names (`_pz`).
- **⏸ Odotetaan, isännällä Jatka ilman heitä**: `renderPause()`: every phone shows who is being waited for; only the host has the button (`goOn()`).
- **Vuoroissa pelattava peli?**: `needs`, set by the game with `AiPelitRooms.turns(id => …)` (#297; the athletics meets of `lib/yleisurheilu-5/`): true while the round needs that phone now, its turn. `waitingFor()` then names only those, so nothing stops while an away phone is not on turn, and a phone that leaves the room keeps its player (`onPeers()` releases no one).
- **⏸ Odotetaan, isännällä Ohita vuoro**: the same pause, but the host's button reads "Ohita vuoro" and fires the game's `on('skip', ids)`; the meet records a missed attempt. The host looks at whom to wait for every 250 ms (`tellPause()` from `renderPause()`), since the turn changes with no room message.
- **↩ Palaa kierrokseen KOOD**: in a game played in turns a guest in a round keeps it in `localStorage` (`ai-pelit:_huone:kesken`, `keepAway()`), so it survives closing the game, and leaving the room mid-round keeps its seat (no `bye` in `leave()`), so a newcomer cannot fill a full room in its place; the first page of the room screen then offers one button back into it (`awayRound()`, same game and version, under 6 hours old). It is forgotten when the round ends for this phone, the host sends it back to the room or says it is not in the round, or the room is gone (`forgetAway()`). A phone that comes back this way after its round ended gets the round's end from the host as any away phone does, and the room screen steps aside for it (`net.rejoin` in `onMessage()`), so the game's own end shows (the athletics podium); the game then goes back to the room.
- **Tietokone ohjaa poissaolevaa**: the game's `on('continue', ids)`; `on('back', id)` when that phone returns. Someone who leaves the room for good is handed over the same way. Kirkkis: `botTakes()`; a hider walks to the nearest hiding place.
- **Kierros päättyy: tulos kaikille, myös poissa olleille**: the host's `deliver(msg)` sends the end to every phone in the round and to no other. Each phone confirms it (`_got`); until then the host keeps it, and sends it again on that phone's `hello`, after that round's `_start` (so a reloaded page knows the round). A page that reloads just as the round ends, seen as connected before its hello, gets it that way. Then `endRound()`. Kirkkis: `end()` delivers `kfin`, the whole finished round and who seeks next.
- **Tallenna tulos kerran per kierros**: the game saves only when `AiPelitRooms.once(round)` is true (kept per tab in `ai-pelit:_huone:kierros`), then `backToRoom(text)` shows the room with the result. Kirkkis: `guestEnd()`, into `ai-pelit:kirkkis:tilasto`, then `note('Seuraavaksi etsii …')`.
- **🎤 Puhe-kytkin huoneruudussa, oletuksena päällä**: "🎤 Puhe" on the room screen (#322), beside 🌍 Julkinen, kept in `ai-pelit:_huone:puhe` (`setVoice()`). Off: no 🎤 chip, no calls, and the other phones are told so (`hi`, `on: false`). Shown in every room, public ones too (Eero's choice, until a friends list exists).
- **Puhelinyhteys jokaiseen huoneen puhelimeen**: `voiceSync()` in `public/rooms.js`: each phone greets each other connected one (`_rtc` `hi`, with its voice switch and a page id `sid`), and the one with the smaller id calls (`dial()`, answered in `pickUp()`): one audio-only `RTCPeerConnection` per pair, at most 7 per phone. Offers, answers and ICE candidates go as `_rtc` messages. A phone that reloaded (new `sid`) is called again; a failed call is tried again after 1, 2, 4… up to 30 seconds. A failure leaves the game as it is.
- **Pitääkö pelaaja 🎤-nappia pohjassa?**: the 🎤 chip (`voiceUI()`, `renderVoice()`), over the game and the room screen while this phone is in a room: upright on the right edge at 38 % height, on its side in the top bar right of the middle (the athletics events' buttons fill both edges). A version may move it with `data-voice-corner` or leave voice out with `data-voice="off"` on its `rooms.js` tag. Push to talk (`press()`, `release()`): pointerdown starts; pointerup, pointercancel or the page going hidden stops. Faded while no call is up; amber while the microphone opens, red while live. A quick tap says "Pidä pohjassa ja puhu."
- **Mikrofoni päälle, ääni muille**: `getUserMedia({audio: {echoCancellation, noiseSuppression}})` on each press (the first asks for permission), its track put on every connection with `replaceTrack()`; on release the track is stopped, so the phone's microphone light is off between presses.
- **🔊 Nimi puhuu: muut kuulevat**: each call's sound plays through its own hidden `<audio>` (`hear()`; a tap anywhere starts one the phone held back); the speaker's name shows next to the chip while they hold theirs (`_rtc` `talk` on and off).
- **🔇 Mykistä pelaaja pelaajalistassa**: a 🔊 button beside each other player who has voice on (`render()`); a tap makes it 🔇 and mutes that player on this phone for as long as it is in the room (`toggleMute()`).
- **Huone välittää yhteyden avausviestit _rtc kenelle tahansa**: `rooms/worker.js` `webSocketMessage()`: a `_rtc` message from any phone goes only to the phone named in `to`, with `from` set, guest to guest too. Every other message is routed as before.
- **GET /api/voice/ice: TURN-tunnukset**: `iceServers()` in `server/api.js`: asks Cloudflare's TURN service for credentials that last 2 hours, kept half an hour (`TURN_KEY_ID`, `TURN_KEY_TOKEN` secrets, bound by `scripts/cloudflare_setup.py` from `~/.local/share/ai-pelit/turn.env`) and returns `iceServers`. Without them, or when Cloudflare does not answer, only Cloudflare's public STUN server. Refused to another site's pages. `getIce()` in `rooms.js` reads it every half hour.
- **TURN-välityspalvelin, jos suora yhteys ei onnistu**: Cloudflare Realtime TURN passes the sound on when two phones cannot reach each other directly (some mobile networks). Nothing is recorded or kept.
- **Tämän kuun käyttö alle 800 Gt?**: `underCap()` in `server/api.js`: the relay is free up to 1000 GB a month and billed after, with no cap at Cloudflare, so credentials are handed out only while this month's row in `turn_usage` (migration 0008) is under `TURN_CAP` (800 GB, Eero's choice) and was written within 3 days. No: only STUN; calls then go only directly. Read at most every 10 minutes.
- **Koneen tarkistus kerran tunnissa: käyttö Cloudflarelta**: `scripts/turn_usage.py`, run hourly from `origin/main` by `scripts/systemd/ai-pelit-turn.timer` on the AgentDeck host: the whole account's TURN bytes this month from Cloudflare's GraphQL (`callsTurnUsageAdaptiveGroups`), written with the admin key to `POST /api/admin/turn-usage`. A host that is off for 3 days turns the relay off.
