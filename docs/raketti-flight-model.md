# Raketti flight model

Raketti v2 follows the approved manual, two-dimensional launch → orbit → docking mission. The player chose maximum realism, a 2D view, and no autopilot. Earth, a coplanar station at 400 km, two stages, coasting time acceleration and resumable flight were assumptions in the approved scope. The practice starts are an implementation assumption: they make the three stages learnable without repeatedly spending eight minutes on launch, and never earn full-flight achievements.

The mission starts on a rotating Earth. The station starts at −0.20336 radians from the launch meridian, a launch window that brings the handbook ascent close to the station near its next apoapsis; a different manual ascent still needs the player to correct phasing. Nothing steers, stages, fires an engine or matches station velocity for the player. Instruments calculate the current orbit and explain the next task; the test-only scripted pilot is never shipped with the game.

## Equations and references

All state uses metres, seconds and kilograms in Earth-centred inertial coordinates. The gravitational parameter is 3.986004418 × 10¹⁴ m³/s²; the spherical Earth radius is 6,371,000 m. Positive x points east at launch, positive y points outward from Earth's centre; angles run clockwise from positive y.

- Central gravity: **a = −μ r / |r|³**. The station moves on a circular orbit with **v = √(μ/r)** and **n = √(μ/r³)**. Orbital energy and angular momentum determine periapsis and apoapsis; reaching altitude alone does not mean reaching orbit. [NASA: Flight to Orbit](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/flight-to-orbit/).
- Propellant consumption: **ṁ = F / (Isp g₀)**, with thrust limited to the remaining fuel. Dry and propellant mass contribute to acceleration; staging discards the first stage. [NASA: Ideal Rocket Equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/).
- Atmospheric drag: **D = ½ ρ v² Cd A**, opposing velocity relative to the co-rotating atmosphere. [NASA: Drag Equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-equation/).
- Manual turning applies torque divided by the vehicle's moment of inertia. There is no vacuum damping. Translation thrusters act in body coordinates and consume a separate propellant supply.
- Docking compares nose position and velocity to the station's moving port, including the rotational velocity of each. Capture needs <1.2 m separation, ≤0.25 m/s relative speed, ≤5° alignment error and ≤0.01 rad/s relative spin, approached from the port's front. These are gameplay engineering assumptions, not a claim about an actual docking system. The entire vehicle segment and the previous/current nose, centre and tail trajectories are checked against station solids and the port ring, so fast contact cannot skip an obstacle between ticks.

The fictional launch vehicle starts at 500 tonnes. Stage 1 carries 295 tonnes propellant and 35 tonnes dry mass, with 7 MN thrust and 300–335 s specific impulse. Stage 2 carries 140 tonnes propellant, 29 tonnes dry mass including payload, and 1 tonne RCS propellant, with 1.9 MN thrust and 450 s specific impulse. There is enough delta-v for orbital insertion and rendezvous; consumption and the discarded mass are simulated rather than awarded at milestones.

## Numerical and physical limits

Velocity Verlet uses at most 0.25 s coasting steps, reduced to 0.02 s under thrust, during turning or within 1 km of the station. Time acceleration still runs every substep. The player can choose ×1, ×2 and ×5 during launch, thrust and steering. ×10 and ×100 remain available only above 150 km, beyond 5 km from the station, with engines and thrusters off and angular speed below 0.01 rad/s. Outside those coasting conditions a higher selected rate drops to ×5, not back up automatically. Within 20 m of the port it returns to real time; this cutoff is an implementation assumption for final contact, stated on screen. Pausing and resuming use ×1. Existing v1 saves and achievements use the same keys and shape unchanged.

This is a planar, spherical-Earth two-body simulation, not a validated aerospace training simulator. It omits the Moon, non-spherical gravity, lift, propellant slosh and real engine operating limits. The atmosphere is a scale-height exponential with an altitude cutoff. Passive aerodynamic stability, dynamic-pressure failure and a heat proxy are deliberately simplified. Graphics enlarge the craft; the instruments and collision model use metres. The craft has no re-entry heat shield.

## Flight verification

`tests/test_raketti_v2.py` contains a test-only pilot which operates the same DOM controls as a player. Its reference launch starts nearly vertical, aims about 20° from vertical at 10 km, 40° at 40 km, 65° at 100 km and 80° at 200 km, stages manually, and performs orbital insertion. This is a feasibility check rather than an autopilot available to the player. The full non-practice mission test continues that launch through a coast, main-engine rendezvous and RCS docking in both orientations, using only the manual DOM controls and physics steps. Separate checks exercise repeat practice docking, high-speed and tail-first contacts, an orbit period, fuel consumption, immediate warp cancellation, saves, offline play and touch layouts.

## Faster flight (v2)

Chosen by the owner: acceleration also while not coasting; selectable ×1/×2/×5 under thrust and steering; ×10/×100 for coasting; manual controls, unchanged physics and existing saves; real time near docking contact, with the limit visible.

Assumed (change if the build shows better; say so in the pull request): the final-contact cutoff is 20 m nose-to-port distance; disallowed ×10/×100 is capped at ×5; manual staging preserves ×2/×5. The time button cycles through the currently permitted rates.
