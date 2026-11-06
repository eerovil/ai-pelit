"""Puhelinkoppi: recorded sounds from the shared library (#226), and drawing only when the screen changes (#415)."""

import shutil

from conftest import ROOT

URL = "games/puhelinkoppi/v9/"
FLY = """(seconds) => { for (let t = 0; t < seconds && (state === 'air' || state === 'drop' || state === 'settle'); t += 1 / 60) step(1 / 60); return state; }"""

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""
SOUNDS = ["suhahdus", "osuma", "tomahdys", "lasi", "voitto", "tappio"]


def open_game(site, browser):
    shutil.copytree(ROOT / "games" / "puhelinkoppi", site.games / "puhelinkoppi")
    site.build()
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    # A nickname, so the first catch does not open the scores panel's name question.
    ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_selector("#ai-pelit-tulokset-nappi")
    page.evaluate("noise = 0")
    page.evaluate(SPY)
    return ctx, page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_throw_a_catch_a_drop_and_a_wrong_side_each_sound(site, browser):
    ctx, page = open_game(site, browser)
    page.mouse.click(180, 100)  # the first tap turns sound on
    page.wait_for_function(f"{SOUNDS!r}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('osuma', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")

    page.evaluate("newRound(); launch({ v0: 3 })")
    assert page.evaluate(FLY, 3) == "result"
    assert page.evaluate("result.kind") == "win"
    assert played(page) == ["suhahdus", "osuma", "voitto"]

    page.evaluate("noise = 0; newRound(); launch({ v0: 3, vx: 0.5 })")
    page.evaluate(FLY, 3)
    assert page.evaluate("result.kind") == "drop"
    assert played(page) == ["suhahdus", "suhahdus", "tomahdys", "lasi"]

    page.evaluate("noise = 0; newRound(); launch({ v0: 3, wx: 5 })")
    page.evaluate(FLY, 3)
    assert page.evaluate("result.kind") == "down"
    assert played(page) == ["suhahdus", "osuma", "tappio"]
    assert page.errors == []
    ctx.close()


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    shutil.copytree(ROOT / "games" / "puhelinkoppi", site.games / "puhelinkoppi")
    site.build()
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    ctx.route("**/*.mp3", lambda route: route.abort())
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_selector("#ai-pelit-tulokset-nappi")
    page.evaluate(SPY)
    page.mouse.click(180, 100)
    page.evaluate("noise = 0; newRound(); launch({ v0: 3, vx: 0.5 })")
    page.evaluate(FLY, 3)
    assert page.evaluate("result.kind") == "drop"
    assert played(page) == []
    assert page.errors == []
    ctx.close()


def test_v5_saves_are_read_as_they_are(site, browser):
    ctx, page = open_game(site, browser)
    page.evaluate("""() => {
      for (const [k, v] of [['taso', 4], ['paras', 6], ['kopit', 9], ['haasteet', 2]]) localStorage.setItem('ai-pelit:puhelinkoppi:' + k, JSON.stringify(v));
    }""")
    page.goto(site.url + URL)
    page.wait_for_selector("#ai-pelit-tulokset-nappi")
    assert page.evaluate("[level, best, catches, challenges]") == [4, 6, 9, 2]
    assert page.errors == []
    ctx.close()


# #337: no crowd noise; #355: on aanet-5, the sounds Eero found too loud softer.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/puhelinkoppi/v9")


# #415: the screen is still before the throw and on the result, so nothing is drawn there.
COUNT = """() => { window.draws = 0; const real = draw; window.draw = () => { draws++; real(); }; }"""
QUIET = 700  # ms: about 40 frames, had it gone on drawing


def still(page):
    """Waits for the drawing to stop, then says whether it stayed stopped."""
    page.wait_for_function("!moving()", timeout=8000)
    page.wait_for_timeout(100)
    before = page.evaluate("draws")
    page.wait_for_timeout(QUIET)
    return page.evaluate("draws") == before


def counted(site, browser):
    ctx, page = open_game(site, browser)
    page.evaluate(COUNT)
    return ctx, page


def canvas_drawn(page):
    return page.evaluate("""() => {
      const d = x.getImageData(c.width / 2, c.height / 2, 1, 1).data; return d[3] === 255;
    }""")


def test_nothing_is_drawn_before_the_throw_even_after_a_tap(site, browser):
    ctx, page = counted(site, browser)
    assert still(page)
    assert page.evaluate("draws") == 0
    page.touchscreen.tap(180, 150)
    assert page.evaluate("state") == "ready"
    assert still(page)
    assert page.errors == []
    ctx.close()


def test_a_throw_is_drawn_to_its_end_and_then_the_drawing_stops(site, browser):
    ctx, page = counted(site, browser)
    page.evaluate("noise = 0; newRound(); launch({ v0: 3, vx: 0.6 })")
    page.wait_for_function("state === 'result'", timeout=8000)
    assert page.evaluate("draws") > 20
    assert page.evaluate("result.kind") == "drop"
    assert still(page)
    assert page.evaluate("shake") == 0
    assert page.errors == []
    ctx.close()


def test_a_catch_with_the_hand_raised_lets_the_camera_arrive_and_rest(site, browser):
    ctx, page = counted(site, browser)
    page.evaluate("""noise = 0; newRound(); handY = 0.6; pos = add(hand(), mul(N, REST)); launch({ v0: 3 })""")
    page.wait_for_function("state === 'result'", timeout=8000)
    assert page.evaluate("result.kind") == "win"
    assert still(page)
    assert page.evaluate("camY === camTarget() && camY > 0.2")
    assert page.errors == []
    ctx.close()


def test_the_next_round_is_drawn_after_a_result_at_rest(site, browser):
    ctx, page = counted(site, browser)
    page.evaluate("noise = 0; newRound(); launch({ v0: 3, vx: 0.6 })")
    page.wait_for_function("state === 'result'", timeout=8000)
    assert still(page)
    page.wait_for_function("performance.now() - resultT > 520")
    before = page.evaluate("draws")
    page.touchscreen.tap(180, 150)
    page.wait_for_function(f"draws > {before}")
    assert page.evaluate("state") == "ready"
    assert still(page)
    ctx.close()


def test_dragging_the_hand_draws_and_a_swipe_throws_from_rest(site, browser):
    ctx, page = counted(site, browser)
    assert still(page)
    start = page.evaluate("[...project(pos).slice(0, 2), handX]")
    page.mouse.move(start[0], start[1])
    page.mouse.down()
    page.mouse.move(start[0] + 40, start[1], steps=4)
    page.wait_for_function("draws > 0")
    assert page.evaluate("handX") > start[2]
    assert page.evaluate("state") == "ready"
    page.mouse.up()
    assert still(page)  # the hand was only moved: no throw, and the screen rests where it is

    drawn = page.evaluate("draws")
    page.evaluate("swipe = null; throwFromSwipe({ speedUp: 3000, speedSide: 0, offX: 0, offY: 0 })")
    assert page.evaluate("state") == "air"
    page.wait_for_function(f"draws > {drawn + 5}")
    assert page.errors == []
    ctx.close()


def test_a_new_size_redraws_the_wiped_canvas_and_keeps_the_round(site, browser):
    ctx, page = counted(site, browser)
    assert still(page)
    page.set_viewport_size({"width": 740, "height": 360})
    page.wait_for_function("draws > 0 && LAND")
    assert canvas_drawn(page)
    assert page.evaluate("state") == "ready"
    assert still(page)
    ctx.close()


def test_coming_back_to_the_page_draws_again(site, browser):
    ctx, page = counted(site, browser)
    assert still(page)
    for event in ("document.dispatchEvent(new Event('visibilitychange'))",
                  "window.dispatchEvent(new Event('pageshow'))",
                  "c.dispatchEvent(new Event('contextrestored'))"):
        before = page.evaluate("draws")
        page.evaluate(event)
        page.wait_for_function(f"draws > {before}")
    ctx.close()


def test_a_first_frame_after_rest_moves_a_normal_step(site, browser):
    ctx, page = counted(site, browser)
    assert still(page)
    page.wait_for_timeout(300)
    # A long rest must not count as time in the air.
    y = page.evaluate("""() => new Promise(done => {
      noise = 0; newRound(); launch({ v0: 3 });
      const y0 = pos[1], real = window.draw;
      window.draw = () => { window.draw = real; real(); done(pos[1] - y0); };
    })""")
    assert 0 < y < 3 * 0.03
    ctx.close()
