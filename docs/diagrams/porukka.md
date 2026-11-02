# Porukka: pelihuone säilyy, vaikka peli vaihtuu (#354)

One room can be used for a whole games evening. The room's creator chooses the next game **between rounds**; nobody needs a new invite or room code. The game picker reads the current `catalog.json` and offers only games with room capacity for all members. A disconnected member still occupies a place. The phone that created the room keeps its host role through a short sessionStorage handoff.

```mermaid
flowchart TD
  A[Host makes a room] --> B[Room code and members]
  B --> C[Round starts]
  C --> D[Round ends]
  D --> E{Host chooses a new game?}
  E -- No --> C
  E -- Yes --> F[Picker: catalog games with enough room.max]
  F --> G[Host saves short-lived handoff]
  G --> H[Host opens new game with the same room code]
  H --> I[Worker updates game, version and max on the same room]
  I --> J[Worker sends peers with the new game]
  J --> K[Guest phones navigate to the new game]
  K --> B
  B --> L{Last member leaves intentionally?}
  L -- Yes --> M[Delete room and public listing immediately]
  L -- No: connection drops --> N[Keep membership for up to 6 hours]
  N --> B
  class A,B,C,D,H,I,J,K blue
  class E,L amber
  class F,G violet
  class M green
  class N teal
```

The same shared `public/rooms.js` and `rooms/worker.js` work with published games without changing their version directories. Host transitions do not send `bye`; a deliberate leave does. The usual game back-chip navigation remains intact.

The shelf and friends page show **Kutsut** (pending room invitations) above **Kaveripyynnöt**, with `Liity` and `Ei`. Friend activity remains on the friends page but is no longer shown on the front page. Invitation banners do not duplicate those entries.

The second part of #354, web push notifications for invitations while the site is closed, is implemented separately and does not change this room-switching flow.
