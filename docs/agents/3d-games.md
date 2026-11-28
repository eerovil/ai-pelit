# 3D games

Read for a game that uses three.js, or a change to `public/lib/three-r*/`.

Moved here unchanged from `AGENTS.md` (#558), which keeps a short form and links here. "Rule N" means the numbered rules in [rules.md](rules.md); a section named in quotes is listed in [AGENTS.md](../../AGENTS.md).

## 3D games (three.js)

A game that wants real 3D (a camera, lights, solid shapes) uses three.js from the site's shared
folder (#99), not hand-made projection maths:

```html
<canvas id="c"></canvas>
<script type="module">
import * as THREE from '../../../lib/three-r187/three.module.js';
const c = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas: c, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
// scene, PerspectiveCamera, lights, meshes; on resize: renderer.setSize(innerWidth, innerHeight, false),
// camera.aspect = innerWidth / innerHeight, camera.updateProjectionMatrix().
renderer.setAnimationLoop(() => renderer.render(scene, camera));
</script>
```

- Use the newest `public/lib/three-r*/` folder. A published library folder never changes
  (`scripts/check_immutable.py` fails a pull request that edits one): a newer three.js goes in a
  new `three-r<N>/` folder, copied unchanged from the npm package's `build/` with its `LICENSE`
  and a `SOURCE` line, in its own pull request. Old games keep the release they were made with.
- Core three.js only. An add-on (a model loader, camera controls) is copied into the game's own
  folder as one file, with its import of `three` changed to the relative path above.
- The canvas fills the screen as a fixed box (rule 4, not `100dvh`) with `touch-action: none`; size
  the renderer from the canvas's own size (`clientWidth`, `clientHeight`). Wrap `new THREE.WebGLRenderer` in `try` and show a Finnish message when the phone
  cannot draw 3D.
- The phone downloads the library (about 420 KB compressed) the first time it opens a 3D game,
  and `sw.js` keeps it for offline play. `scripts/build.py` refuses a version that loads a
  `lib/` file that is not there.
- Turning an existing 2D game into 3D (Hiihto v7, #103): keep its classic `<script>`, so its
  functions stay global for its tests and for the inline scripts after it, and load three.js with
  `import('../../../lib/three-r187/three.module.js').then(m => …)`. Put the WebGL canvas under the
  game's own canvas (`pointer-events:none` on it) and keep drawing the menus and HUD on the 2D one,
  cleared each frame. Vertex colours are linear: fill them from `new THREE.Color('#hex')`.
- A cheap phone is short of pixels, not of shapes: on a 2017 Huawei P8 lite, shadows and the pixel
  ratio decided the frame rate, a thousand instanced spruces hardly did. Measure the first seconds of
  play and step the pixel ratio down, then the shadows off (`tune()` in Hiihto v7).
- `tests/fixtures/three-demo.html` is a complete small example (a lit, spinning cube), and
  `tests/test_lib_three.py` shows how to check a 3D game draws (headless Chromium has WebGL).

## Outfits in a 3D game

Every 3D game shares one outfit choice and one set (#568, Eero's choice); the newest
`public/lib/asut3d-<N>/asut3d.js` builds the outfit's 3D pieces. To dress a player:

1. Load `<script src="../../../outfits.js" data-game="<slug>" data-share="3d"></script>` and
   `<script src="../../../lib/asut3d-1/asut3d.js"></script>` before the game's own scripts.
2. `let outfit = AiPelitAsut3d.setup({ default: '<id>', button: '<menu button or its box>',
   change(o) { outfit = o; /* rebuild the player */ } })`. It returns the worn outfit, puts the
   default first, and wires (or, given a box, makes) the "👕 Asu" button. The cards show the
   shared front figure, the same in every 3D game. `change` also runs when the page comes back
   into view wearing another outfit (picked in another 3D game meanwhile).
3. A game with no body of its own takes `AiPelitAsut3d.figure(THREE, outfit)`: a 1.8-tall person,
   feet at y 0, facing +z, with the joints in `userData.joints`. A game with its own body takes
   `head(THREE, o)` (radius 1, facing +z: every costume's head, the hero mask, a face with hair or
   a beanie), `cape(THREE, o, { w, h })` and `torso(THREE, o, { w, h, d, round })` (ribs, a stripe);
   each of the last two is null when the outfit has none.
4. Rebuild the player when `outfit.id` changes. In a room, send the id with the player and build
   friends from `AiPelitOutfits.get(id)`; their name colours stay the game's own.

`tests/fixtures/asut3d-demo.html` is the smallest whole use, Seittisankari v6 the model with its
own body joints (`figure()`), Pulkkamäki v7 the model with its own body (`head()`, `cape()`), Vuoristorata v9 a seated rider (`figure()` with bent legs) and
first-person sleeves in the outfit's colours.
A fix to the library is the next folder (rule 1).

A test whose game loads `lib/three` is marked `alone` even when its phones draw 2D, unless the
file sets a `games` marker (`tests/conftest.py`); check the marking before the first queued run.
