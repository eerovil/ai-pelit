"""Piano v6: plays sideways too (#95), and portrait stays as v5 drew it."""

import shutil

import pytest

from conftest import ROOT

URL = "games/piano/v6/"
SIZES = [(740, 360), (844, 390), (640, 360)]


@pytest.fixture
def piano_site(site, tmp_path):
    # Only this game is built: other games' half-done versions cannot break this test.
    games = tmp_path / "only"
    shutil.copytree(ROOT / "games" / "piano", games / "piano")
    site.build(games)
    return site


def open_at(browser, site, w, h, level=None):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    if level:
        page.evaluate(f"localStorage.setItem('ai-pelit:piano:taso', '{level}')")
        page.reload()
    return ctx, page


def inside(box, w, h):
    return box and box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= w and box["y"] + box["height"] <= h


@pytest.mark.parametrize("w,h", SIZES)
def test_the_menu_and_end_screen_fit_sideways(piano_site, browser, w, h):
    ctx, page = open_at(browser, piano_site, w, h, level=5)
    page.evaluate("showMenu('Peli päättyi: 12345 pistettä – uusi ennätys! 🏆')")
    assert page.evaluate("document.documentElement.scrollHeight") <= h
    for sel in ("#menu h1", "#result", "#prev", "#next", "#go", "#stats", ".help"):
        assert inside(page.locator(sel).bounding_box(), w, h), sel
    # The arrows and the button are tappable, nothing over them.
    page.click("#prev")
    assert page.evaluate("pick") == 4
    page.click("#next")
    page.click("#go")
    assert page.evaluate("state") == "play" and page.evaluate("level") == 5
    ctx.close()


def test_a_round_runs_sideways_and_real_taps_reach_every_lane(piano_site, browser):
    ctx, page = open_at(browser, piano_site, 740, 360)
    page.click("#go")
    start = page.evaluate("now")
    page.wait_for_timeout(600)
    assert page.evaluate("now") > start + 0.3  # the song's clock runs
    assert page.evaluate("wide") is True
    # Lanes span the width, keys and line inside the screen, the line above the keys.
    lane_x, lane_w, top, hit, btn = page.evaluate("[laneX, laneW, topY, hitY, btnTop]")
    assert lane_x + 4 * lane_w <= 740 and top < hit < btn < 360
    for lane in range(4):
        page.evaluate(f"""() => {{
          const n = cur.notes.filter(m => m.lane === {lane})[0];
          for (const m of cur.notes) {{ m.hit = m !== n; m.missed = false; }}
          now = n.t; window._n = n;
        }}""")
        page.touchscreen.tap(lane_x + (lane + 0.5) * lane_w, (btn + 360) / 2)
        assert page.evaluate("_n.hit") is True, lane
    assert page.evaluate("lives") == 3
    ctx.close()


def test_turning_the_phone_mid_song_keeps_the_round(piano_site, browser):
    ctx, page = open_at(browser, piano_site, 360, 740, level=3)
    page.click("#go")
    page.wait_for_timeout(2500)
    # Every note counts as played, so no miss changes the hearts while the phone turns.
    page.evaluate("score = 750; lives = 2; for (const n of cur.notes) n.hit = true;"
                  "document.fullscreenElement && document.exitFullscreen()")
    before = page.evaluate("[level, now, cur.notes.length]")
    for w, h in [(740, 360), (360, 740), (844, 390)]:
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(300)
        lv, t, count, score, lives, state, wide, btn = page.evaluate(
            "[level, now, cur.notes.length, score, lives, state, wide, btnTop]")
        assert (lv, count, score, lives, state) == (3, before[2], 750, 2, "play")
        assert t > before[1]  # the song went on, not back to its start
        assert wide == (w > h) and btn < h
    ctx.close()


@pytest.mark.parametrize("w,h", [(360, 740), (360, 640)])
def test_portrait_looks_as_in_v5(piano_site, browser, w, h):
    shots = []
    for v in ("v5", "v6"):
        ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
        page = ctx.new_page()
        page.goto(piano_site.url + f"games/piano/{v}/")
        page.evaluate("localStorage.setItem('ai-pelit:piano:taso', '7')")
        page.reload()
        menu = page.screenshot()
        page.click("#go")
        page.evaluate("now = 3; score = 1234; combo = 12; for (const n of cur.notes) if (n.t < 3) n.hit = true;"
                      "state = 'over'; banner = null; draw()")
        shots.append((menu, page.screenshot()))
        ctx.close()
    assert shots[0][0] == shots[1][0]
    assert shots[0][1] == shots[1][1]
