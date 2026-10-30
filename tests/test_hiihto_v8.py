"""Hiihto v8 (#95): v7's 3D game plays with the phone turned sideways, and portrait stays as in v7."""

import shutil

import pytest

from conftest import ROOT

URL = "games/hiihto/v8/"
LAYOUT = "[vButton().x, vButton().y, vButton().r, skatePads().map(p => [p.x, p.y, p.w, p.h]), ui.friends && [ui.friends.x, ui.friends.y], ui.wax.map(b => [b.x, b.y, b.w, b.h])]"


def build(site):
    # Only this game: other games' half-done versions in the same checkout must not break the build.
    shutil.copytree(ROOT / "games" / "hiihto", site.games / "hiihto")
    site.build()


def open_game(site, browser, w=740, h=360, url=URL):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{url}")
    page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
    return page


def wait_3d(page):
    page.wait_for_function("!!V3 || no3d", timeout=15000)
    # Headless Chromium draws WebGL in software; without it the game still plays, and says so.
    if page.evaluate("no3d"):
        pytest.skip("this Chromium has no WebGL")


def rects(page):
    """Every menu button as drawn, in screen pixels: [name, left, top, right, bottom]."""
    return page.evaluate("""() => {
      draw();
      const r = c.getBoundingClientRect(), sx = r.width / W, sy = r.height / H, out = [];
      const add = (n, b) => b && out.push([n, r.left + b.x * sx, r.top + b.y * sy, r.left + (b.x + b.w) * sx, r.top + (b.y + b.h) * sy]);
      ui.styles.forEach((b, i) => add('style' + i, b)); ui.wax.forEach((b, i) => add('wax' + i, b));
      add('friends', ui.friends); add('prev', ui.prev); add('next', ui.next);
      return out;
    }""")


def chip(page, sel):
    b = page.locator(sel).bounding_box()
    return [b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"]]


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def turn(page, w, h):
    """Turns the phone. back.js goes fullscreen on the first tap, and Chromium resizes no
    fullscreen window, so leave fullscreen first."""
    page.evaluate("document.fullscreenElement && document.exitFullscreen()")
    page.wait_for_timeout(200)
    page.set_viewport_size({"width": w, "height": h})


def tap(page, name):
    _, l, t, r, b = next(x for x in rects(page) if x[0] == name)
    page.touchscreen.tap((l + r) / 2, (t + b) / 2)


def camera(page):
    """The 3D view as last drawn: its size, the camera's aspect and its lens shift (px down)."""
    return page.evaluate("""() => { draw(); const cm = V3.camera;
      return [V3.w, V3.h, cm.aspect, cm.view && cm.view.enabled ? -cm.view.offsetY : 0]; }""")


@pytest.mark.parametrize("w,h", [(740, 360), (640, 360), (844, 390)])
def test_the_menu_fits_sideways_and_every_button_works(site, browser, w, h):
    build(site)
    page = open_game(site, browser, w, h)
    # A course with the road (the longest menu), and a level each way to go.
    page.evaluate("maxLevel = 4; level = 3; newRace()")
    assert page.evaluate("LAND") is True
    page.wait_for_selector("#ai-pelit-back")
    page.wait_for_selector("#ai-pelit-tulokset-nappi")
    back, scores = chip(page, "#ai-pelit-back"), chip(page, "#ai-pelit-tulokset-nappi")
    found = rects(page)
    assert {n for n, *_ in found} == {"style0", "style1", "wax0", "wax1", "wax2", "wax3", "friends", "prev", "next"}
    for n, l, t, r, b in found:
        assert 0 <= l and r <= w and 0 <= t and b <= h, (n, l, t, r, b)
        assert b - t >= 36, n
        assert not overlaps([l, t, r, b], back) and not overlaps([l, t, r, b], scores), n
    # Taps where the buttons show: the style, the level, then a wax starts the race.
    tap(page, "style1")
    assert page.evaluate("style") == "luistelu"
    tap(page, "style0")
    tap(page, "prev")
    assert page.evaluate("level") == 2
    tap(page, "next")
    assert page.evaluate("level") == 3
    tap(page, "wax1")
    page.wait_for_function("mode === 'count'", timeout=2000)
    assert page.evaluate("net === null && document.getElementById('aipr')?.hidden !== false")
    assert page.errors == []
    page.context.close()


def test_the_friends_button_opens_the_room_sideways(site, browser):
    build(site)
    page = open_game(site, browser)
    tap(page, "friends")
    page.wait_for_function("!!document.getElementById('aipr') && !document.getElementById('aipr').hidden", timeout=2000)
    assert page.evaluate("mode") == "wax"
    page.context.close()


def test_a_race_sideways_survives_turning_the_phone(site, browser):
    build(site)
    page = open_game(site, browser)
    wait_3d(page)
    page.evaluate("level = 1; newRace(); npcs = []; nextVasta = nextSkate = 1e9")
    tap(page, "wax0")
    page.wait_for_function("mode === 'race'", timeout=5000)
    page.evaluate("npcs = []; nextVasta = nextSkate = 1e9")
    # The 3D view fills the wide screen, shifted down so the HUD stays in the sky.
    assert camera(page) == [740, 360, 740 / 360, round(0.06 * 360)]
    # The V button sits low on the left, on screen, and toggles the V step.
    v = page.evaluate("(() => { const b = vButton(); return [b.x, b.y, b.r]; })()")
    assert v[0] - v[2] >= 0 and v[1] + v[2] <= 360 and v[0] < 740 / 4
    page.touchscreen.tap(v[0], v[1])
    assert page.evaluate("P.vMode") is True
    page.touchscreen.tap(v[0], v[1])
    assert page.evaluate("P.vMode") is False
    for _ in range(8):
        page.touchscreen.tap(370, 200)
        page.wait_for_timeout(380)
    z, t = page.evaluate("[P.z, P.t]")
    assert z > 3 and page.evaluate("mode") == "race"
    # Turned upright mid-race: the same race goes on where it was, the 3D view upright too.
    turn(page, 360, 740)
    page.wait_for_function("W === 360 && H === 740 && !LAND")
    page.wait_for_timeout(300)
    z2, t2 = page.evaluate("[P.z, P.t]")
    assert page.evaluate("mode") == "race" and z2 >= z and t2 > t
    assert camera(page) == [360, 740, 360 / 740, 0]
    # And back sideways: still the same race, and a tap still kicks.
    turn(page, 740, 360)
    page.wait_for_function("W === 740 && H === 360 && LAND")
    v0 = page.evaluate("P.v")
    page.wait_for_timeout(400)
    page.touchscreen.tap(370, 200)
    assert page.evaluate("mode") == "race" and page.evaluate("P.z") >= z2
    assert page.evaluate("P.v") > 0 or v0 > 0
    assert camera(page)[:2] == [740, 360]
    assert page.errors == []
    page.context.close()


def test_skating_pads_and_the_road_button_sit_in_the_lower_corners(site, browser):
    build(site)
    page = open_game(site, browser)
    pads = page.evaluate("skatePads().map(p => [p.x, p.y, p.x + p.w, p.y + p.h])")
    assert pads[0][2] < 740 / 4 and pads[1][0] > 740 * 3 / 4
    assert all(0 <= p[0] and p[2] <= 740 and p[3] <= 360 and p[1] > 360 / 2 for p in pads)
    # On level 3 the road: its one button low on the right.
    page.evaluate("level = 3; newRace(); chooseWax(bestFor(style, course.weather.T)); countT = 0.01")
    page.wait_for_function("mode === 'race'", timeout=3000)
    page.evaluate("npcs = []; nextVasta = nextSkate = 1e9; P.z = course.road.z0 - 1; P.v = 1")
    page.wait_for_function("P.road === 'edge'", timeout=5000)
    page.touchscreen.tap(740 - 30 - 115, 360 - 46 - 27)
    page.wait_for_function("P.road === 'off' || P.road === 'walk'", timeout=3000)
    assert page.errors == []
    page.context.close()


def test_the_finish_sideways_fits_and_a_tap_goes_on(site, browser):
    build(site)
    page = open_game(site, browser)
    page.evaluate("level = 1; maxLevel = 1; newRace(); chooseWax(bestFor(style, course.weather.T)); countT = 0.01")
    page.wait_for_function("mode === 'race'", timeout=3000)
    page.evaluate("P.z = course.len - 0.5; P.v = 6; P.t = course.ideal")
    page.wait_for_function("mode === 'done' && resultT > 0.9", timeout=15000)
    box = page.evaluate("(() => { const b = landBox(Math.min(W - SAFE_L - SAFE_R - 24, 560), 206); return [b.px, b.py, b.px + b.pw, b.py + b.ph]; })()")
    assert box[0] >= 0 and box[1] >= 0 and box[2] <= 740 and box[3] <= 360
    page.touchscreen.tap(370, 180)
    page.wait_for_function("mode === 'wax' && level === 2", timeout=2000)
    assert page.errors == []
    page.context.close()


@pytest.mark.parametrize("w,h", [(360, 740), (360, 640)])
def test_portrait_is_laid_out_as_in_v7(site, browser, w, h):
    build(site)
    seen = []
    for url in ["games/hiihto/v7/", URL]:
        page = open_game(site, browser, w, h, url)
        wait_3d(page)
        page.evaluate("draw()")
        seen.append(page.evaluate(LAYOUT) + [camera(page)])
        assert page.errors == []
        page.context.close()
    assert seen[0] == seen[1]
    assert seen[1][-1] == [w, h, w / h, 0]
