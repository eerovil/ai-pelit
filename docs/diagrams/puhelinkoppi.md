# Puhelinkoppi: one throw, from swipe to catch

How one Puhelinkoppi throw plays (v1). The player's finger moves the hand, with the phone in it; a quick flick up
throws it, the hand's speed sets the height and where the finger first touched the phone sets the spin. The phone then
flies as a real rigid box, in all three directions and turning about all three axes: an end-over-end flip turns into a twist by itself (the middle axis
is unstable), a spin about the long axis stays steady. The player moves the hand under it, sideways and up or down, while
the arm reaches forward or back by itself; a catch screen up passes the level, and more turns or the
top end away earn the level's optional extra challenge.

```mermaid
flowchart TD
  A[Puhelin kämmenellä, ruutu ylöspäin] --> B[Heittoliike: käsi nykäisee ylös]
  B --> C[Nopeus = korkeus, aloituskohta = pyöriminen]
  C --> D[Lento: painovoima ja jäykän kappaleen pyöriminen]
  D --> E[Pelaaja siirtää kättä sormella, käsivarsi kurottaa syvyyssuunnassa]
  E --> F{Osuuko käteen?}
  F -- Ei --> G[Kolaus: puhelin putoaa lattialle]
  F -- Kyllä --> H[Puhelin asettuu alemmalle kyljelleen]
  H --> I{Ruutu ylöspäin?}
  I -- Ei --> J[Väärin päin]
  I -- Kyllä --> L[KOPPI! Taso nousee]
  L --> K{Lisähaaste: kierrokset ja yläpää poispäin?}
  K -- Kyllä --> M[Tähti ⭐]
  G --> A
  J --> A
  L --> A
  M --> A
  class A,B,E blue
  class F,I,K amber
  class C,D,H teal
  class L,M green
  class G,J rose
```

## Colours

- **blue**: what the player sees and does
- **amber**: a check that decides the result
- **teal**: the physics of the throw and the landing
- **green**: a pass, saved on the phone
- **rose**: a fail; the same level again

## Boxes

- **Puhelin kämmenellä, ruutu ylöspäin**: `newRound()` in `games/puhelinkoppi/v1/index.html`; the palm is tilted towards the player, as you hold a phone to read it.
- **Heittoliike: käsi nykäisee ylös**: `onMove()` moves the hand, and the phone in it, with the finger; `onUp()` throws when the hand was moving up faster than 1 m/s at the end, otherwise the phone stays in the hand.
- **Nopeus = korkeus, aloituskohta = pyöriminen**: `throwFromSwipe()`: the phone leaves with the hand's upward speed over the last 90 ms (2–6.5 m/s); starting below the phone's middle gives an end-over-end flip, at a side a twist about the long axis, sideways speed a drift.
- **Lento: painovoima ja jäykän kappaleen pyöriminen**: `physics()`: flight in all three directions (`launch()` pushes the phone a little towards the player, as the tilted palm does); Euler's equations for a 7.5 × 15.5 × 0.8 cm box (RK4, 1 ms steps) and a quaternion orientation; `launch()` adds a small random wobble, as no hand throws perfectly.
- **Pelaaja siirtää kättä sormella, käsivarsi kurottaa syvyyssuunnassa**: dragging anywhere during the flight moves the hand sideways and up or down, from 30 cm below to 60 cm above where it started (`moveHand()`). The finger has only two directions, so the arm follows the phone in depth by itself, at most 1.5 m/s and 45 cm forward or back (`step()`).
- **Osuuko käteen?**: when the phone comes down to the palm, it must be within 8.5 cm sideways of the hand's middle; a phone the hand was raised past falls on.
- **Puhelin asettuu alemmalle kyljelleen**: `caught()`: the phone settles flat on whichever face points more down, keeping its heading.
- **Lisähaaste: kierrokset ja yläpää poispäin?**: `spec()`: optional, never needed to pass. Level 2 asks one turn; level 3 also the top end pointing away; then more turns. A turn is two times the screen changes from up to down.
- **KOPPI! Taso nousee**: `finish()` saves `taso`, `paras` and `kopit` under `ai-pelit:puhelinkoppi:`.
- **Tähti ⭐**: a met extra challenge adds to `haasteet`, shown as ⭐ in the corner.
