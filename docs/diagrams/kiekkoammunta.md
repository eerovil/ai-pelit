# Kiekkoammunta: one round of clay shooting

How Kiekkoammunta plays (v1). The player picks trap or skeet, then shoots 25 clay
discs from a view behind the gun. Putting a finger down calls the disc; dragging moves the
sight like a touchpad, and lifting the finger fires. The shot spreads into a growing circle of
pellets, so a disc is hit when it is inside the circle when the pellets get there.

```mermaid
flowchart TD
  A[Menu: Trap or Skeet, best scores] --> B[Stand: next disc of 25]
  B --> C[Finger down: call, disc flies]
  C --> D[Drag: sight follows like a touchpad]
  D --> E[Lift finger: shot]
  E -.-> AU[Sound: shot, disc breaking]
  E --> F{Disc inside the pellet circle when they arrive?}
  F -- Yes --> G[Disc bursts, +1]
  F -- No --> H{Shots left for this disc?}
  H -- Trap: second shot --> C2[Finger down again, drag, lift]
  C2 --> E
  H -- No, or the disc landed --> I[Miss]
  G --> J{Discs left?}
  I --> J
  J -- Yes --> K{Stand done?}
  K -- Trap: 5 discs per stand --> L[Move to next of 5 stands]
  K -- Skeet: station plan --> M[Move round the 8 stations, singles and doubles]
  K -- No --> B
  L --> B
  M --> B
  J -- No --> N[Result: hits of 25, record saved]
  N --> O[High-score list for Trap or Skeet]
  O --> A
  G -.-> SAVE[Save disc result and active double]
  E -.-> SAVE
  SAVE --> RELOAD[Reload: resume the same round]
  class SAVE,RELOAD green
  class A,B,C,D,E,C2 blue
  class F,H,J,K amber
  class G,L,M teal
  class I rose
  class N,O green
  class AU teal
```

## Colours

- **blue**: what the player does
- **amber**: a question the game asks
- **teal**: the game moves on
- **rose**: a miss
- **green**: the result, saved

## Boxes

- **Finger down: call, disc flies**: touching the screen launches the next disc (or a double in skeet) from the trap house or a tower; `games/kiekkoammunta/v1/index.html`, `call()`. The sight starts near the launch path; `prepare()` and `shooter()` set the view for the station.
- **Drag: sight follows like a touchpad**: the sight moves by the finger's movement, not to where the finger is, so the finger never covers the disc; `drag()`.
- **Disc inside the pellet circle when they arrive?**: the pellets take a moment to fly and spread wider the further the disc is, so the player must aim a little ahead of a moving disc; `shotHits()`.
- **Trap: second shot**: trap allows two shots at a disc; skeet allows one, as in the real sport.
- **Skeet: station plan**: the real skeet order of singles and doubles from the high and low towers, 25 discs in all; `SKEET`, including a return to station 4 for both ordered doubles before station 8.
- **Result: hits of 25, record saved**: the best score per discipline is saved at once under `ai-pelit:kiekkoammunta:`; the score goes to that discipline's list.

- **Save disc result and active double**: `keep()` saves results, the remaining target, ammunition and shots in flight in `ai-pelit:kiekkoammunta:kierros`; `resolveDisc()` saves each outcome. `pagehide` and hiding the page also save.
- **Reload: resume the same round**: `resume()` restores the saved round from the menu. Rotation only changes the canvas size; it never resets the round.
- **Sound: shot, disc breaking**: `sound()` uses quiet `lahto` and `lasi` from `lib/aanet-5/`, with a quiet noise fallback after a gesture. No crowd cheers.
