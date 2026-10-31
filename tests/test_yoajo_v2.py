"""Yöajo v2 (#181): the game fits the screen as soon as it opens, also after going full screen."""

from conftest import ROOT

URL = "games/yoajo/v2/"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    return page


def bottom_of_buttons(page):
    return page.evaluate("(() => { draw(); return Math.max(...btns.map(b => b.y + b.h)); })()")


def test_the_canvases_fill_the_screen_not_100dvh(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => ['c', 'g'].map(id => { const b = document.getElementById(id).getBoundingClientRect(); return [b.top, b.height]; })""")
    assert r == [[0, 740], [0, 740]]
    assert "100dvh" not in page.evaluate("[...document.styleSheets[0].cssRules].map(r => r.cssText).join(' ')")


def test_a_screen_that_grows_or_shrinks_is_measured_again(site, context):
    page = open_game(site, context)
    # Going full screen makes the screen taller, showing the bars again shorter. The canvas box
    # is compared with the size drawn for every frame, so even a change no event announced is
    # caught: here the size is made wrong behind the game's back.
    for h in (820, 640):
        page.set_viewport_size({"width": 360, "height": h})
        page.evaluate("H = 1000")
        page.wait_for_function(f"H === {h}")
        assert bottom_of_buttons(page) <= h
    page.evaluate("document.dispatchEvent(new Event('fullscreenchange'))")
    assert page.evaluate("H") == 640
    assert page.errors == []


def test_saves_from_v1_carry_on_and_a_leg_plays(site, context):
    context.add_init_script("""if (!sessionStorage.seeded) { sessionStorage.seeded = 1;
      localStorage.setItem('ai-pelit:yoajo:taso', '3'); localStorage.setItem('ai-pelit:yoajo:ajettu', '2');
      localStorage.setItem('ai-pelit:yoajo:tahdet', '{"1":3,"2":2}'); localStorage.setItem('ai-pelit:yoajo:pisteet', '{"1":372}'); }""")
    page = open_game(site, context)
    assert page.evaluate("[maxLeg, driven, stars[2], bests[1], level]") == [3, 2, 2, 372, 3]
    from test_yoajo import BOT
    r = page.evaluate(BOT, [1])
    assert r[0]["mode"] == "done", r
    assert page.errors == []
