"""Voimistelu v6: plays sideways too (#95), with the words in side columns and the hall in the middle."""

import shutil

import pytest

from conftest import ROOT, turn

LANDSCAPE = [{"width": 740, "height": 360}, {"width": 844, "height": 390}, {"width": 640, "height": 360}]


def build_game(site):
    # Only this game, so another game's unfinished version cannot break the build.
    if not (site.games / "voimistelu").exists():
        shutil.copytree(ROOT / "games" / "voimistelu", site.games / "voimistelu")
        site.build()


def open_game(site, browser, size, fullscreen=True):
    build_game(site)
    ctx = browser.new_context(viewport=size, is_mobile=True, has_touch=True)
    # A nickname already given, so the high-score list does not ask for one over the score board.
    ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    if not fullscreen:
        # back.js goes fullscreen on the first touch, Chromium will not resize a fullscreen window, and
        # leaving fullscreen does not settle headless: never enter it, so set_viewport_size can turn the phone.
        ctx.add_init_script("Element.prototype.requestFullscreen = function () { return Promise.resolve(); }")
    page = ctx.new_page()
    page.goto(f"{site.url}games/voimistelu/v6/")
    page.wait_for_function("S > 0")
    return ctx, page


def inside(box, size):
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= size["width"] and box["y"] + box["height"] <= size["height"]


@pytest.mark.parametrize("size", LANDSCAPE)
def test_sideways_the_chips_fit_and_the_hall_sits_between_the_side_columns(site, browser, size):
    ctx, page = open_game(site, browser, size)
    for sel in ("#ai-pelit-back", "#ai-pelit-tulokset-nappi"):
        box = page.locator(sel).bounding_box()
        assert box and inside(box, size), sel
        # Nothing covers the chip: a tap in its middle lands on it.
        hit = page.evaluate("([x, y, sel]) => { const e = document.elementFromPoint(x, y); return !!e && !!e.closest(sel); }",
                            [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, sel])
        assert hit, sel
    lay = page.evaluate("({ W, H, L: sideL(), R: sideR(), S, bars: BARS.map(sc), floor: sc([0, FLOOR])[1] })")
    assert lay["W"] == size["width"] and lay["H"] == size["height"]
    assert lay["L"] > 100 and lay["R"] > 100
    for bx, by in lay["bars"]:
        assert lay["L"] < bx < lay["W"] - lay["R"]
        assert 0 < by < lay["H"]
    assert lay["floor"] < lay["H"] - 10
    # Larger than the hall fitted to the width of a portrait phone turned sideways would be.
    assert lay["S"] > size["height"] / 8
    ctx.close()


def test_sideways_the_camera_keeps_the_body_in_the_middle_strip(site, browser):
    ctx, page = open_game(site, browser, LANDSCAPE[0])
    for launch in ("{ x: 1, y: 0.3, vx: 8, vy: 3, phi: Math.PI / 2 }", "{ x: 0, y: 0.5, vy: 11, phi: Math.PI }",
                   "{ x: -1, y: 0.5, vx: -6, vy: 9, phi: -Math.PI / 2, w: 3 }"):
        page.evaluate(f"newRoutine(); launchAir({launch})")
        worst = page.evaluate("""() => new Promise(done => { let worst = -Infinity, n = 0;
          (function check() {
            const b = bodyPoints();
            if (n > 0) for (const k in b) { const [px, py] = sc(b[k]); worst = Math.max(worst, sideL() - px, px - (W - sideR()), SAFE_T - py, py - (H - SAFE_B)); }
            if (mode === 'air' && n++ < 600) requestAnimationFrame(check); else done(worst);
          })(); })""")
        assert worst <= 0, launch
    ctx.close()


def test_a_round_plays_sideways_and_turning_the_phone_keeps_it(site, browser):
    size = LANDSCAPE[0]
    ctx, page = open_game(site, browser, size, fullscreen=False)
    # Hold a finger on the hall: the swing runs on the game's own loop.
    page.mouse.move(size["width"] / 2, size["height"] / 2)
    page.mouse.down()
    page.wait_for_timeout(300)
    assert page.evaluate("hold") is True
    th0 = page.evaluate("th")
    page.wait_for_timeout(400)
    page.mouse.up()
    assert page.evaluate("[mode, hold]") == ["bar", False]
    assert page.evaluate("th") != th0
    # Mid-round, with a move done and the gymnast in the air.
    page.evaluate("""() => { addElement('Jättikierto', 0.2); const a = Math.PI - 0.6, r = R_EXT, T = 0.7;
      launchAir({ x: r * Math.sin(a), y: -r * Math.cos(a), vx: -2 * r * Math.sin(a) / T, vy: G * T / 2, phi: a, w: 1.2 / T }); }""")
    before = page.evaluate("({ names: elements.map(e => e.name), routines, mode })")
    for turned in ({"width": 360, "height": 740}, size):
        turn(page, turned)
        page.wait_for_function(f"W === {turned['width']} && H === {turned['height']}")
        page.wait_for_timeout(100)
        now = page.evaluate("({ names: elements.map(e => e.name), routines, mode, side: sideL() })")
        assert now["names"] == before["names"] and now["routines"] == before["routines"]
        assert now["mode"] in ("air", "bar")
        assert (now["side"] > 0) == (turned["width"] > turned["height"])
    ctx.close()


def test_sideways_the_score_board_fits_in_two_columns(site, browser):
    for size in LANDSCAPE:
        ctx, page = open_game(site, browser, size)
        page.evaluate("""() => { newRoutine(); for (let i = 0; i < 9; i++) addElement('Liike ' + i, 0.1);
          deductions.push(['Askel', 0.1]); touch = { fall: false, stuck: true, saltos: 1, halves: 0 }; finish(); resultT = 2; }""")
        page.wait_for_timeout(100)
        lay = page.evaluate("resultLayout")
        # All ten rows fit the low screen, and the board with the tap for a new routine stays on it.
        assert lay["rows"] == 10
        assert lay["bottom"] <= size["height"] and lay["tapY"] < lay["bottom"]
        page.evaluate("resultT = 2")
        page.mouse.click(size["width"] / 2, size["height"] / 2)
        assert page.evaluate("mode") == "bar"
        ctx.close()
