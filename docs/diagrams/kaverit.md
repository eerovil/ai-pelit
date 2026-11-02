# Kaverit: friend list, what friends play, room invites

How two phones become friends, how each sees what the other is playing right now, and how one
invites the other into its room (#324). Friends are made only in a game room: one phone taps
"➕ Kaveriksi" beside another player, and that player accepts. Every game version already loads
`public/back.js`, so the "now playing" signal and the banners reach every game with no new game
version.

```mermaid
flowchart TD
  subgraph Huone[Pelihuone: public/rooms.js ja rooms/worker.js]
    R0[Huone kertoo jokaisen pelaajan kaveritunnuksen]
    R1[➕ Kaveriksi pelaajan nimen vieressä]
    R3[Kaveripyyntö: Hyväksy tai Ei]
    R4[📨 Kutsu kaveri]
  end
  subgraph Peli[Jokainen pelin versio ja hylly]
    B1[kaverit.js: kerro 30 s välein mitä pelaan]
    B2[Banneri: kaveripyyntö tai kutsu]
    R2[Pelin versio avautuu ?huone=KOODI ja liittyy huoneeseen]
  end
  subgraph Hylly[Pelihylly: public/app.js]
    H1[👫 Kaverit -sivu: pyynnöt ja kaverilista]
    H6[Kuka pelaa mitä nyt]
    H7[Etusivu: kutsut ja kaveripyynnöt]
    H8[Poista kaveri]
  end
  subgraph Palvelin[server/api.js ja D1]
    S1[Kaveripyynnöt: voimassa 7 päivää]
    S2{Hyväksyikö?}
    S3[Kaverit molempiin suuntiin]
    S4[Missä kukin on nyt]
    S5{Ovatko kavereita?}
    S6[Kutsut: voimassa 10 min]
  end
  R0 --> R1
  R1 --> S1
  S1 --> R3
  S1 --> B2
  S1 --> H1
  R3 --> S2
  H1 --> S2
  B2 --> S2
  S2 -- Kyllä --> S3
  S2 -- Ei --> S9[Pyyntö piiloon: kysyjä näkee yhä Pyydetty]
  H8 --> S3
  B1 --> S4
  S3 --> H1
  S4 --> H6
  S6 --> H7
  R4 --> S5
  S5 -- Kyllä --> S6
  S6 -- vastaus seuraavaan 30 s ilmoitukseen --> B2
  B2 -- Liity --> R2
  H7 -- Liity --> R2

  class R1,R3,H8,S2 amber
  class B1,S4,H6 teal
  class R4,S5,S6,B2,R2,H7 violet
  class R0,S1,S3,H1,S9 blue
```

## Colours

- **amber**: what the player taps to make, accept or end a friendship
- **blue**: friendships and friend requests kept on the server
- **teal**: the "now playing" signal and where it shows
- **violet**: an invite into a room, from send to join

## Boxes

- **Huone kertoo jokaisen pelaajan kaveritunnuksen**: a phone with a nickname joins the room with `fid` (a hash of its secret player id); `rooms/worker.js` keeps it and sends it in each member of `peers`.
- **➕ Kaveriksi pelaajan nimen vieressä**: on the room screen in `public/rooms.js`, beside each other player who has a `fid` and is not yet a friend; sends `POST /api/friends/requests`. Turns into "Pyydetty". A phone with only an animal name is first asked for a nickname; once the server takes it (a taken name keeps the row open with the reason, `setName()` and `nameError()` in `public/kaverit.js`; so does a name the admin rejected later, which every friends answer reports in `me`), it joins the room again on a new connection (`rejoinWithFid()`), so the others see its nickname and friend id, and the request is sent.
- **Kaveripyyntö: Hyväksy tai Ei**: shown on the room screen of the phone asked (it checks for requests every 10 s while the room screen is open), on the shelf (front page and `#/kaverit`), and as a banner in a game once the phone has a friend.
- **Kaverit molempiin suuntiin**: the `friends` table in `migrations/0007_friends.sql`, one row per pair; made when a request is accepted, removed both ways.
- **kaverit.js: kerro 30 s välein mitä pelaan**: `ping()` in `public/kaverit.js` sends `POST /api/presence {player, game, version}` while the page is visible, only on a phone that has a friend. `public/back.js` only loads `kaverit.js` in every game; the shelf loads it from `public/index.html`.
- **Missä kukin on nyt**: the `presence` table; a row older than 90 s means the friend is not playing now, its time shows as "nähty … sitten".
- **📨 Kutsu kaveri**: a button on the room screen, shown on a phone with friends; it lists them (playing a game first, then browsing the shelf, then the rest) and sends `POST /api/invites`; the button reads "Kutsutaan…", then "Kutsuttu ✓" for the invite's 10 minutes, after which the friend may be invited again.
- **Banneri: kaveripyyntö tai kutsu**: `drawBanner()` in `public/kaverit.js`, on every page that loads it, from the requests and invites in the latest answer. "Liity" first leaves the room the phone is in, as "Poistu huoneesta" does (`AiPelitRooms.leave()`), then opens the new room so that back still goes up (`openInvite()`, the same handoff as a room code for another game in `rooms.js`, finished by `openFromRoom()` in `public/app.js`): game → its page → the shelf, never back into the game the phone was playing. On the shelf's front page and friends page `public/app.js` sets both `quietRequests` and `quietInvites` (#354), so requests and invites show in the page's own lists and no banner shows there; on a game's or a group's page a request comes as the banner; on a room screen requests show in its own list.
- **Etusivu: kutsut ja kaveripyynnöt**: `drawPlaying()` in `public/app.js` (#354): pending room invites ("Kutsut", Liity / Ei, `inviteRow()`) above friend requests (Hyväksy / Ei), above "Avoimet huoneet"; the friends page lists the same invites at its top. The front page no longer lists friends playing; who plays what shows only on the friends page. A phone with a nickname but no friends yet sends no "now playing", so the front page reads `GET /api/friends` every 30 s while it shows (`watch(true, 30e3, true)`), and a new request or invite appears without leaving the page.
- **Pyyntö piiloon: kysyjä näkee yhä Pyydetty**: "Ei" marks the request declined (`migrations/0008_friend_request_declined.sql`); the asked phone no longer sees it, and the asking phone keeps "Pyydetty" until it is a week old, so a "no" is never shown.
