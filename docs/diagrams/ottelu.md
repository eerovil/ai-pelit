# Ottelu: several athletics events in one match

How Ottelu v1 plays (#168); v2 plays the same, but a room starts only once the host has picked at least two events, and the event in the frame gets the phone's safe areas; v3 starts each next event alone in a freshly loaded page. The player, or the host of a room, picks two to five field events and
their order. Each event runs a published version of that event's own game in a frame, unchanged:
`laji.js` stands in for `rooms.js` and changes the shared athletics library as it loads, so the event
has the match's eight athletes, three rounds and saves of its own. Each athlete's best mark becomes
points by the combined-event tables, and the points add up.

```mermaid
flowchart TD
  MENU[Valikko: valitse lajit järjestyksessä] --> Q{Yksin vai huoneessa?}
  Q -- Yksin --> NEW[Uusi ottelu: lajit, taso, 8 urheilijaa]
  Q -- Huone --> ROOM[Huone: isäntä valitsee lajit, Aloita kierros]
  ROOM --> NEW
  NEW --> LOAD[Lajin sivu kehykseen: laji.js rooms.js:n tilalle]
  LOAD --> PATCH[Kirjasto muutetaan: 8 urheilijaa, 3 kierrosta, omat tallennukset]
  PATCH --> PLAY[Laji pelataan kuten omalla sivullaan]
  PLAY --> NET{Huoneessa?}
  NET -- Isäntä --> HOST[Isännän laji vetää kisaa, viestit kääreessä L]
  NET -- Vieras --> GUEST[Vieraan kehys valmis: Lr, isäntä lähettää kisan]
  NET -- Yksin --> RES
  HOST --> RES[Lajin lopputulokset näkyvät]
  GUEST --> RES
  RES --> PTS["Paras tulos pisteiksi: A·(P−B)^C"]
  PTS --> LAST{Viimeinen laji?}
  LAST -- Ei --> BOARD[Pisteet yhteensä, Seuraava laji]
  BOARD --> LOAD
  LAST -- Kyllä --> END[Lopputulokset ja mitalit]
  END --> SAVE[Ennätys, tuloslista lajimäärän mukaan, voitosta seuraava taso]
  SAVE --> MENU
  END --> BACK[Huoneessa: takaisin huoneeseen]
  class MENU,ROOM,BOARD,PLAY blue
  class HOST,GUEST violet
  class Q,NET,LAST amber
  class NEW,LOAD,PATCH,PTS teal
  class RES,END,SAVE,BACK green
```

## Colours

- **blue**: what the player sees and does
- **violet**: phones in a room working together
- **amber**: a check that decides the path
- **teal**: the match's own work: the field, the frame, the points
- **green**: results and saves

## Boxes

- **Valikko: valitse lajit järjestyksessä**: `drawPick()` in `games/ottelu/v1/index.html`; the pick is saved as `ai-pelit:ottelu:lajit`, and two to five events name the match (Kaksiottelu … Viisiottelu).
- **Huone: isäntä valitsee lajit, Aloita kierros**: `hostPick()` moves the same picker into the room screen with `AiPelitRooms.extra()` on the host. v2: `roomStart()` keeps the room's "Aloita kierros" off with the note "Valitse ainakin kaksi lajia." while fewer than two events are picked, and a start that gets through anyway starts nothing (v1 quietly played all five).
- **Uusi ottelu: lajit, taso, 8 urheilijaa**: `newMatch()`; M is plain data, saved as `ai-pelit:ottelu:kesken` alone and sent as `{t: 'M'}` in a room.
- **Lajin sivu kehykseen: laji.js rooms.js:n tilalle**: `lajiHtml()` and `loadEvent()` fetch the event's published page (`LAJIT`: Pituushyppy v4, Korkeushyppy v2, Seiväshyppy v2, Keihäänheitto v4, Moukarinheitto v2), add a `<base>`, hide its menu, (v2) give it this page's safe areas (`safeCss()`: a frame's own `env(safe-area-inset-*)` is 0, so on a phone with a notch the event's panel went under the chips and its buttons into the gesture bar), swap `rooms.js` for `laji.js` and drop `scores.js` and `back.js`.
- **Kirjasto muutetaan: 8 urheilijaa, 3 kierrosta, omat tallennukset**: `patch()`: `rounds()` gets three rounds, `meet()` gets the match's field and names and the slug `ottelu:<event>`, so the event saves under `ai-pelit:ottelu:<event>:…`; `K.step` scores the event as soon as its results appear (`eventScored()`, saved at once, since the library drops the event's own save then) and moves the match on once they have been shown (`eventOver()`). `prefetch()` fetches every event's page and scripts once online, so the service worker keeps them for offline play.
- **Isännän laji vetää kisaa, viestit kääreessä L**: `newProxy()` is the event's `AiPelitRooms`; the event's messages go as `{t: 'L', at, m}`, so one from an event already over never reaches the next.
- **Vieraan kehys valmis: Lr, isäntä lähettää kisan**: a guest's frame sends `{t: 'Lr'}` once loaded; the host's event hears it as `hello` and sends that phone the meet.
- **Pisteet yhteensä, Seuraava laji**: `showBoard()`; "Seuraava" on the host or alone. v3: alone it saves the match, marks the next event in sessionStorage (`ai-pelit:ottelu:seuraava`) and reloads the page (marked `ai-pelit:_jatkuu`, so `back.js` does not count it as a new play), which starts that event at once; a tap inside the event asks for full screen again in a browser tab (`laji.js`), as the reload leaves it: on Eero's phone a second frame swapped into the same page took no taps. In a room the event still changes in place.
- **Paras tulos pisteiksi: A·(P−B)^C**: `LAJIT[…].pts`, World Athletics combined-event tables (the decathlon's jumps and javelin; the hammer by the throws pentathlon), rounded down; no mark is 0 points.
- **Ennätys, tuloslista lajimäärän mukaan, voitosta seuraava taso**: `ended()`; the high-score list is `lajit-<number of events>`.
