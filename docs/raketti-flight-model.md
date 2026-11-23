# Raketti flight model

Raketti v3 (#548) replaces v2's real-scale Earth with tiny bodies, one finger and short trips. The
owner found v2 too realistic: too hard and too slow. They chose a new version (v2 deleted), tiny
bodies seen in one view that zooms by itself, a one-finger drag stick, short trips with no time
warp, then a Moon base built one part a trip and a real journey to Mars. There is still no
autopilot: the player flies every push, and the hint at the bottom says what to do next.

## The world

Game metres and seconds, in a 2D frame centred on Earth: +y is up from the launch pad, angles run
clockwise from straight up, as a drag on the screen does. Earth stands still; the Moon and the rock
circle it; Earth circles the Sun, so in this frame the Sun and Mars move round Earth.

| Body | Radius | Surface pull | Where | Sphere | Safe landing |
|---|---|---|---|---|---|
| Earth (Maa) | 60 | 14 | middle | 1100 | 6 m/s |
| Moon (Kuu) | 16 | 9.5 | 420 from Earth | 125 | 5 m/s |
| Rock (Pikkukivi) | 4 | 0.5 | 250 from Earth | 24 | 3 m/s |
| Sun (Aurinko) | 320 | — | Earth circles it at AU = 8000, year 420 s | everywhere else | — |
| Mars | 30 | 7 | 1.524 AU from the Sun | 500 | 5 m/s |

The station circles 100 from Earth's middle; it docks within 3 m at up to 3 m/s. The Moon base
stands on top of the Moon (it never turns) and takes a landing within ±0.4 rad of it.

## Pull: one body at a time

Inside the Moon's, the rock's or Mars's sphere only that body pulls, and the ship is carried along
with it; inside Earth's sphere only Earth; further out only the Sun (patched conics). So an orbit
never drifts by itself, and the numbers the hints read (lowest and highest point) are exact.

## Rockets

Each trip names its rocket (`ROCKETS` in `physics.js`): push in m/s², fuel as Δv in m/s, and how
fast the nose turns toward the finger.

| Rocket | Push | Fuel | Turn | Trips |
|---|---|---|---|---|
| Raketti | 32 | 340 | 14 rad/s | the first six, Mars (40 % full at the start) |
| Kiitäjä | 38 | 340 | 18 rad/s | the solar panel |
| Rahtiraketti | 21 | 400 | 5 rad/s | the fuel tank and the fuel factory |

## Control

The finger's drag from where it touched is the stick: its direction is where the nose turns, and its
length the push, as the square of the drag past an 8 px dead zone, full at 80 px. The engine pushes
only once the nose is within 60° of the drag, less the further off it is. A ship standing on a body
lifts off only when its push up beats the pull.

## Steps and time

Velocity Verlet with the push held over each fixed 1/120 s step. Time runs at 1 normally, eases to
0.5 while the engine burns and to 0.35 for fine moves (a correction, the last metres of a landing or
docking, the end of a wait); the nose turns as fast on screen however slow time runs. A wait with a
known length ("Odota 12 s") can be skipped with a tap: the flight then runs faster until a second
before its end (Mars's waits are minutes long). There is no other time warp.

## Mars

The Mars trip starts with 40 % of a tank, flies to the Moon base and fills up there at 120 m/s a
second (the base must be built; only this trip refuels there). Its window opens about 150 s in; the hint counts it down. From the
Moon it pushes out along Earth's own way round the Sun, so the ship leaves Earth's sphere onto a
half-ellipse out to Mars's circle; out round the Sun small corrections bend the path past Mars,
and it lands there like on the Moon. A whole trip followed by the hints takes about 9 minutes.

## Stars and saves

A trip gives a star for arriving, one for fuel left over its limit, and one for a soft finish (a
landing at half the safe speed or slower, a docking at 1.5 m/s or slower, an orbit with eccentricity
0.25 or less). A trip opens once the one before it has a star; Mars therefore opens after the whole
base. The flight in progress is saved under `ai-pelit:raketti:matka`, and stars under
`ai-pelit:raketti:tahdet`. A saved flight is resumed only when every number in it makes sense, so
v2's saves (another shape) are left unread.
