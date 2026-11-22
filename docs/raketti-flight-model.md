# Raketti flight model

Raketti v3 (#548) replaces v2's real-scale Earth with a small, friendly Earth–Moon system. The owner found v2 too realistic: too hard and too slow. They chose a new version rather than a new game, no carry-over from v2's saves, a Moon trip of about 5–10 minutes, more trips than the Moon, and Moon orbit from the pad in under 5 minutes, built so that a Mars trip can be added later. There is still no autopilot: the player flies every burn, and the instruments only explain the next step.

## The system

All state is in metres, seconds and kilograms, in a 2D Earth-centred frame: +x east of the launch pad, +y up from it, angles clockwise from +y. Earth stands still and has no rotating atmosphere; the Moon and the rock move on fixed circular orbits around it. All bodies live in one list (`BODIES` in `physics.js`), so a later version can add the Sun and Mars.

| Body | Radius | Surface gravity | Orbit around Earth | Notes |
|---|---|---|---|---|
| Earth (Maa) | 500 km | 9.8 m/s² | — | Exponential air up to 40 km, scale height 4.5 km |
| Moon (Kuu) | 80 km | 1.4 m/s² | 5000 km | Numbers read against it within 530 km |
| Rock (Pikkukivi) | 3 km | 0.03 m/s² | 2000 km | Numbers read against it within 30 km |

The station circles 100 km above Earth. An orbit 80 km up needs about 2.1 km/s, and a launch to 80 km about 3 km/s of Δv.

The ship is one stage: 4 t dry, 26 t fuel, specific impulse 380 s, about 7.5 km/s of Δv when full. Its engine never pushes harder than 20 m/s², so a light, nearly empty ship is as easy to fly as a full one. Small translation thrusters give 0.3 m/s² from their own 300 m/s supply. The parachute (Earth only) has a drag area of 3000 m²: a ship with a typical amount of fuel left falls at 5–7 m/s under it.

## Equations

- Gravity is the sum of every body's pull, **a = −Σ μ r / |r|³**, so the Moon really does pull a ship in Earth orbit. The numbers the player reads (lowest and highest point of the orbit) are the two-body orbit around the nearest body. [NASA: Flight to Orbit](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/flight-to-orbit/)
- Fuel use follows **ṁ = F / (Isp g₀)**, and Δv left is the rocket equation **v_e ln(m / m_dry)**. [NASA: Ideal Rocket Equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/)
- Drag is **½ ρ v² A** against the ship's velocity, with a 5 m² ship and a 3000 m² parachute. [NASA: Drag Equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-equation/)
- Steering is not physical on purpose (the owner asked for easier steering): the turn buttons set a turn rate (15°/s, then 60°/s after 0.4 s) and letting go stops it. The point buttons (along the motion, against it, straight up) turn the nose at up to 90°/s and keep it there, measured against the nearest body, or the station within 20 km.

## Steps and time warp

Velocity Verlet with the thrust held over the step. Steps are 0.02 s under thrust, while turning, on a surface or within 2 km of the station; otherwise 1 % of the time to the nearest surface at the current speed, up to 5 s. Under the open parachute a step stays short against the parachute's slowing rate. Time warp changes only how much flight time a frame covers. The step limit is the same at every speed (×1 takes frame-sized steps, smaller still), so ×1000 flies nearly the same path as ×1: a test keeps them within 1 km.

The allowed warp (`maxWarp`) is ×1 within 500 m of a surface or 50 m of the port, ×5 under thrust or near a body, ×100 at middle distance, ×1000 far out. Under the open parachute it is ×100 above 300 m. The turn buttons count real seconds, so a tap turns the nose as far at ×5 as at ×1. The parachute opens only while the ship falls. A higher selected rate drops by itself.

## Trips and stars

Six trips (`TRIPS` in `trips.js`), each opening the next: Kiertoradalle, Avaruusasemalle, Kuun kiertoradalle, Kuuhun, Kuusta kotiin, Pikkukivelle. Each gives one star for arriving, one for Δv left over a per-trip limit, and one for a soft finish (half the landing limits, docking under 0.25 m/s, or an orbit with eccentricity ≤ 0.1). After a star on Kiertoradalle, the other trips can also start from a ready, round 80 km orbit with 4300 m/s of Δv.

## Flight verification

`tests/test_raketti_v3.py` has test-only pilots that set the same things the controls set (throttle, nose, point mode, thrusters, warp), never shipped with the game. With ×2 under thrust and the highest allowed warp while coasting, they took these real (played) times when the trips were tuned:

| Trip | Played time | Δv left |
|---|---|---|
| Pad → Moon orbit | about 3 min 10 s | about 3400 m/s |
| Pad → Moon landing | about 4 min 20 s | about 1900 m/s |
| Pad → Moon → Earth | about 8 min 30 s | about 1200 m/s |
| Pad → rock landing | about 4 min 40 s | about 3200 m/s |

A person flies less exactly than the pilots, so the star limits sit a little under these. Separate tests check the landing, docking and parachute limits, the nose holding after a turn, the time-warp limits, saves, unlocks and layouts.

This is a planar, toy-scale simulation for a game, not an aerospace model: Earth is far smaller and denser than the real one, its air does not rotate, the parachute is huge and there is no re-entry heating.
