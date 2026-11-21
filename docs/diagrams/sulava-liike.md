# Sulava liike: toisten pelaajien piirtäminen huoneessa

How a phone in a room draws the other players smoothly between the host's messages (#480).
Each phone keeps the last few positions it heard for every other player and draws them a short
moment in the past, gliding between the two messages around that moment, so an uneven gap between
messages no longer shows as a jerk. The shared part is `public/lib/sulava-1/sulava.js`; the game
sends as often as before, adds the sending phone's clock to each spot, and draws the others from it.
Last Signal v17 is the first game on it, Kirkkis v12 the second, Kaaosrata v9 the third, Hiihto v13 the fourth, Lentopallo v8 the fifth, and Lattia on laavaa v1 (#488) and Pesis v1 (#504) use it from their first version; the other room games with moving players follow, most-played first.

```mermaid
flowchart TD
  subgraph Host[Isäntäpuhelin]
    H1[Pelaa kierrosta] --> H2[Lähettää tilan pelin omaan tahtiin, jokainen paikka lähettäjänsä kellolla]
  end
  subgraph Relay[Cloudflaren huone]
    R1[Välittää viestin]
  end
  subgraph Guest[Vieraan puhelin]
    G1[Viesti saapuu, epätasaisin välein] --> G2{Hyppäsikö pelaaja tai kävikö lähettäjän kello taaksepäin?}
    G2 -- Kyllä --> G3[Tyhjennä muisti, piirrä heti uuteen paikkaan]
    G2 -- Ei --> G4[Lisää paikka muistiin leimansa kanssa]
    G5[Joka ruudunpäivitys: piirtohetki = nyt − viive] --> G6{Onko piirtohetken molemmin puolin viesti?}
    G6 -- Kyllä --> G7[Liu'u kahden viestin välillä]
    G6 -- Ei, viesti myöhässä --> G8{Alle 0,25 s yli uusimman?}
    G8 -- Kyllä --> G9[Jatka samaa vauhtia eteenpäin]
    G8 -- Ei --> G10[Pysähdy viimeiseen paikkaan]
    G9 --> G13[Seuraava viesti korjaa arvauksen: ero liukuu pois 0,1 sekunnissa]
    G11[Viive mukautuu: viestien väli + vaihtelu, 0,06–0,25 s]
    G12[Oma pelaaja liikkuu sormen mukaan heti, ei viivettä]
  end
  H2 --> R1 --> G1
  G4 -.-> G6
  G11 -.-> G5
  class H1,H2 blue
  class R1 violet
  class G1,G2,G3,G4 teal
  class G5,G6,G7,G8,G9,G10,G11,G13 amber
  class G12 green
```

## Colours

- **blue**: the host phone's own game code, unchanged
- **violet**: the room on Cloudflare (`rooms/`), unchanged
- **teal**: a message arriving on a guest, stored by `sulava.js`
- **amber**: drawing each frame, done by `sulava.js`
- **green**: the phone's own player, which stays as it is now

## Boxes

- **Lähettää tilan pelin omaan tahtiin, jokainen paikka lähettäjänsä kellolla**: the send rate stays as each game had it: about 10–12 a second in most, 20 in Lentopallo v8 (`net.sendT = 0.05`). Last Signal v17: `mine()` and `subPack()` in `games/last-signal/v17/play.js` add `stamp()` (the phone's `AiPelitSulava.now()`); a host forwards a friend's spot in `snapshot()` as it came (`o.tx`, `o.ty`, `o.ta`, `o.hoseIn`) with the friend's own stamp (`o.st`), and SISU as the friend at the helm sent it (`net.subT`), so a repeated spot is heard once and no phone smooths twice. Kirkkis v12: `kme`, `kr` and `ks` carry `s` (`AiPelitSulava.now()`), and `stateOf()` adds a friend's own stamp (`ts`) as each row's seventh, null for the host's and the computer's players, whose time is the message's `s`; a guest snaps a person's track when that source changes (the computer takes over a friend or gives them back, `guestState()`), and the host resets it on `on('back')`. When the round itself moves or stops someone ("Kaikki pelastettu!" puts the seeker back at the base; Hippa freezes the one tagged), every phone starts that person's track again (`restart()` in `show()`), because a friend's next rows still carry their last stamp: a guest snaps it to the spot in the message that told of it (`p.heard`), and the host, whose rules keep the newest spot, draws that spot while the track is empty, so both draw it from the next frame until a new spot starts the glide. Kaaosrata v9: `p` and `s` carry `s`; the host sends a friend's row on as it came (`hd`), with the friend's stamp as its [12], null for the host's own and the computer's runners. Hiihto v13: `p` and `s` carry `st` (their `s` was already the skier's row), and a friend's row carries their stamp as its [11]; the host no longer carries a friend on at their speed between messages, so it sends on the spot they sent. Lentopallo v8: `p` and `s` carry `ck` (`s` already used `st` for the rally's state), and a friend's row carries their stamp as its [5]; the host's rules take a friend's newest spot at once, where v7 chased it.
- **Hyppäsikö pelaaja tai kävikö lähettäjän kello taaksepäin?**: `push()` in `public/lib/sulava-1/sulava.js` starts the track again when the move from the last spot is longer than its `jump` (Last Signal: 8 m for a person, 40 m for SISU; Kirkkis and Kaaosrata: 3 m; Hiihto: 15 m along the trail; Lentopallo: 2 m), or the stamp is over a second older than the newest (the sender's page reloaded). The game calls `snap()` itself on a jump it knows of (Last Signal: a change of place, `setOther()`; SISU at rest, its speed 0 after the driver let go and its spot the one heard last, `setSubT()` and `stopSub()`; with no speed but a new spot, drawn to an opening's middle, it glides, so it is not driven on past where it stopped). Kaaosrata snaps a runner back on their feet after a fall (`heard()`: the fall heard before, none now), as the checkpoint may be nearer than 3 m. Lentopallo starts every track again at a new rally (`newRally()` on the host, the change to `serve` in `applySnapshot()` on a guest), and the host drops a friend's spots until their first one sent after they heard of it, marked `j` (half a second at most), so a spot from the last rally does not pull them off their serving spot. Last Signal also keeps a diver's hose points with their stamps and draws the ones of the moment drawn (`tr.time`), so the hose waits with the body it ends at.
- **Lisää paikka muistiin leimansa kanssa**: keeps the last 8 spots; a spot older than or equal to the newest is dropped. Each track learns its own offset to the sender's clock, the smallest (arrival − stamp) of the last 2 s, so phones' clocks are never compared.
- **Viive mukautuu: viestien väli + vaihtelu, 0,06–0,25 s**: the delay is the usual gap between spots plus twice how late they usually come (over the earliest of the last 2 s), limited to `minDelay`–`maxDelay` (0.06–0.25 s), so a steady connection waits less.
- **Liu'u kahden viestin välillä**: `at()`: a straight-line blend of the track's `keys`; keys named in `angles` take the short way round. The moment drawn follows a change of offset or delay at most 20 % faster or slower than real time, and jumps to it after a frame gap over a second (the page slept); then, until a new spot comes, the player waits at the newest spot known instead of going on past it.
- **Jatka samaa vauhtia eteenpäin**: extrapolates from the last two spots, at most `extra` (0.25 s) past the newest, and not at all when those two are over 0.5 s apart. When a spot then comes that says the guess was off (the player had started or stopped), the difference between what was drawn and what the spots now say is drawn away over about 0.1 s (`EASE`), not in one frame.
- **Seuraava viesti korjaa arvauksen: ero liukuu pois 0,1 sekunnissa**: when a spot comes after a frame drawn on that guess, `at()` works out what that frame should have drawn by the spots now known and draws the difference away over about 0.1 s (`EASE`), instead of in one frame (a player who had started or stopped walking).
- **Oma pelaaja liikkuu sormen mukaan heti, ei viivettä**: the phone's own kart or player is never passed through the library. Kirkkis v12's host keeps a friend's newest spot for its rules (seeing, naming, tagging) and only draws the smoothed one: `frame()` puts it in place for `draw()` and back after. Kaaosrata v9 does the same on every phone for the other phones' runners (`asDrawn()` and `putBack()` in `frame()`), so the finish uses the newest spot; its `bumps()`, which push only this phone's own runners, meet the others where they are drawn (the same swap in `tick()`, #480's D11), so a bump happens where the player sees it. Hiihto v13 swaps the drawn spot in for `draw()` only (`asDrawn()` in `frame()`); the places use the newest spot, and skiers ski through each other, so there is no bump. Lentopallo v8 swaps it in for `draw()` only (`loop()`); a ball held for the serve is drawn in the drawn server's hands. Pesis v1 is the one exception: a guest predicts nothing, so it draws every player through the library, its own too (`drawnSpots()` in `games/pesis/v1/index.html`). Its own runner or fielder is moved only by the host's rules from the foot presses it sends, and shows a moment late, as the others do.
