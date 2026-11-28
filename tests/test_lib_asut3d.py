"""The 3D games' outfits (#568): public/lib/asut3d-1/asut3d.js, on a test-only game
(tests/fixtures/asut3d-demo.html), the smallest whole use of it."""

import io
from pathlib import Path

import pytest
from PIL import Image

from conftest import make_game

# Draws with three.js, so it runs alone (#116), as the 3D games' tests do.
pytestmark = pytest.mark.alone

DEMO = (Path(__file__).parent / "fixtures" / "asut3d-demo.html").read_text()
HEADS = ["pumpkin", "witch", "ghost", "skull", "vampire", "mummy", "pukki", "tonttu", "poro", "lumiukko",
         "pipari", "harry", "ron", "hermione", "naamio", None]


def open_demo(site, context, store=None):
    make_game(site.games, "asudemo", [DEMO])
    site.build()
    for k, v in (store or {}).items():
        context.add_init_script(f"localStorage.setItem('{k}', '\"{v}\"')")
    page = context.new_page()
    page.set_viewport_size({"width": 360, "height": 740})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}games/asudemo/v1/")
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=15000)
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    return page


def test_setup_gives_the_button_the_picker_and_the_games_default(site, context):
    page = open_demo(site, context)
    # The game's default first, then the rest of the common set, then the costumes.
    ids = page.evaluate("AiPelitOutfits.list().map(o => o.id)")
    assert ids[:7] == ["sankari", "haalari", "punainen", "vihrea", "liila", "musta", "yosankari"]
    assert {"kurpitsa", "harry", "joulupukki"} <= set(ids)
    assert page.evaluate("outfit.id") == "sankari"
    # Given a container, setup() made the "👕 Asu" button in it, and the button opens the picker.
    button = page.locator("#valikko button")
    assert button.inner_text() == "👕 Asu"
    button.click()
    assert page.evaluate("AiPelitOutfits.isOpen()") is True
    page.click("[data-asu=vampyyri]")
    page.wait_for_function("fig.userData.outfit === 'vampyyri'")
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:3d')") == '"vampyyri"'
    assert page.errors == []


def test_a_figure_has_every_joint_and_draws_in_the_outfit(site, context):
    page = open_demo(site, context, {"ai-pelit:_asut:3d": "haalari"})
    joints = page.evaluate("Object.keys(fig.userData.joints).sort()")
    assert joints == sorted(["body", "head", "armL", "armR", "elbL", "elbR", "handL", "handR",
                             "legL", "legR", "kneeL", "kneeR"])
    # About 1.8 tall (2 with a beanie), the soles at y 0.
    # Measured with the waving arm (the demo's animation) down at the side.
    lo, hi = page.evaluate("""(() => { fig.userData.joints.armR.rotation.z = 0; fig.updateMatrixWorld(true);
        const b = new THREE.Box3().setFromObject(fig); return [b.min.y, b.max.y]; })()""")
    assert abs(lo) < 0.005 and 1.7 < hi < 2.0
    # The middle of the picture is the blue overall.
    img = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    r, g, b = img.getpixel((img.width // 2, img.height // 2))
    assert b > r + 40 and b > g, (r, g, b)
    assert page.errors == []


@pytest.mark.parametrize("kind", HEADS)
def test_every_head_builds_round_a_unit_head(site, context, kind):
    page = open_demo(site, context)
    size, meshes = page.evaluate("""k => { const o = Object.assign({}, AiPelitOutfits.get('haalari'), { head: k });
        const h = AiPelitAsut3d.head(THREE, o); const b = new THREE.Box3().setFromObject(h);
        let n = 0; h.traverse(m => { if (m.isMesh) n++; });
        return [[b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z], n]; }""", kind)
    assert meshes >= 2
    # About a unit head: hats and antlers reach up, long hair down; nothing far to the sides.
    assert all(abs(v) < 1.9 for v in size[0:1] + size[2:4] + size[5:6]), size
    assert size[4] < 3.2 and size[1] > -1.75, size


def test_capes_and_ribs_only_for_the_outfits_that_have_them(site, context):
    page = open_demo(site, context)
    got = page.evaluate("""['vampyyri', 'luuranko', 'haalari', 'sankari'].map(id => { const o = AiPelitOutfits.get(id);
        const t = AiPelitAsut3d.torso(THREE, o, { w: 0.5, h: 0.6, d: 0.3 });
        return [!!AiPelitAsut3d.cape(THREE, o), t ? t.children.length : 0]; })""")
    # The vampire's cape; the skeleton's spine and three ribs; the overall's stripe; the hero nothing.
    assert got == [[True, 0], [False, 4], [False, 1], [False, 0]]
