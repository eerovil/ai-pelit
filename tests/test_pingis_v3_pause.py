"""Pingis v2 (#531): a game alone can be paused and quit mid-way."""
import json

from test_pingis_v3 import go, open_game, saved


def test_pause_stops_the_ball_and_resume_goes_on(site, context):
    page = open_game(site, context, saves={"taso": "1"})
    assert page.locator("#pause").is_hidden()  # not in the menu
    go(page)
    page.wait_for_function("!document.getElementById('pause').hidden")
    box = page.locator("#pause").bounding_box()
    assert box["x"] + box["width"] <= 360 and box["x"] > 360 / 2 and box["y"] < 80
    page.evaluate("() => { game.sc = [5, 3]; saveSolo(); game.wait = 0; tryServe(0, 0); }")
    page.click("#pause")
    assert page.evaluate("mode") == "paused"
    assert page.locator("#paused").is_visible() and page.locator("#pause").is_hidden()
    assert page.locator("#pauseScore").inner_text() == "Keskitaso · 5–3"
    # The ball stays where it was while paused.
    z = page.evaluate("game.flight.ball.z")
    page.wait_for_timeout(300)
    assert page.evaluate("game.flight.ball.z") == z
    page.click("#resume")
    assert page.evaluate("mode") == "play" and page.locator("#paused").is_hidden()
    page.wait_for_function(f"game.flight && game.flight.ball.z !== {z}", timeout=3000)
    assert page.evaluate("game.sc") == [5, 3]
    assert page.errors == []


def test_quit_drops_the_save_and_counts_nothing(site, context):
    page = open_game(site, context, saves={"taso": "0", "voitot": json.dumps({"0": [2, 1]})})
    go(page)
    page.evaluate("() => { game.sc = [2, 7]; saveSolo(); }")
    assert saved(page, "kesken")["sc"] == [2, 7]
    page.click("#pause")
    page.click("#quit")
    assert page.evaluate("mode") == "menu" and page.locator("#menu").is_visible()
    assert saved(page, "kesken") is None
    assert saved(page, "voitot") == {"0": [2, 1]}
    page.reload()
    page.wait_for_function("mode === 'menu'", timeout=20000)
    assert page.errors == []


def test_hiding_the_page_pauses_and_sideways_the_pause_fits(site, context):
    page = open_game(site, context, width=740, height=360)
    go(page)
    page.evaluate("() => { Object.defineProperty(document, 'hidden', { value: true, configurable: true }); document.dispatchEvent(new Event('visibilitychange')); }")
    assert page.evaluate("mode") == "paused"
    for sel in ("#resume", "#quit", "#pauseTitle"):
        b = page.locator(sel).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= 360, sel
    assert page.errors == []


def test_a_finished_game_cannot_be_paused(site, context):
    # After the last point the result is already counted: no pause, no quit around it.
    page = open_game(site, context, saves={"taso": "0"})
    go(page)
    page.evaluate("() => { game.sc = [10, 3]; game.ph = 'play'; game.flight = newFlight(0, 1, false, [0,0.3,-1,0,0,3,0]); soloPoint(game.flight, 0); }")
    page.wait_for_function("document.getElementById('pause').hidden")
    page.evaluate("pauseGame()")
    assert page.evaluate("mode") == "play"
    page.wait_for_function("mode === 'end'", timeout=5000)
    assert saved(page, "voitot") == {"0": [1, 0]}
    assert page.errors == []


def test_a_finger_on_the_table_keeps_its_bat_through_the_pause(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("""() => document.getElementById('c').dispatchEvent(new PointerEvent('pointerdown',
      { pointerId: 7, clientX: 180, clientY: 600, bubbles: true, pointerType: 'touch' }))""")
    page.click("#pause")
    page.click("#resume")
    assert page.evaluate("finger") == 7
    x = page.evaluate("bats[0].tx")
    page.evaluate("""() => document.getElementById('c').dispatchEvent(new PointerEvent('pointermove',
      { pointerId: 7, clientX: 260, clientY: 600, bubbles: true, pointerType: 'touch' }))""")
    assert page.evaluate("bats[0].tx") > x
    assert page.errors == []


def test_a_saved_game_reopens_paused_and_can_be_quit(site, context):
    page = open_game(site, context, saves={"kesken": json.dumps({"lvl": 1, "sc": [3, 6], "first": 0})})
    page.wait_for_function("mode === 'paused'", timeout=20000)
    assert page.locator("#paused").is_visible()
    assert page.locator("#pauseScore").inner_text() == "Keskitaso · 3–6"
    page.click("#quit")
    assert page.evaluate("mode") == "menu" and saved(page, "kesken") is None
    assert page.errors == []
