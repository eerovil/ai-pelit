"""Pituushyppy v6: the podium stays until the player leaves it (public/lib/yleisurheilu-3/kisa.js, #176)."""

import test_pituushyppy_v2 as v2
import test_pituushyppy_v5 as v5
from test_pituushyppy_v5 import MEDAL_PIXELS

URL = "games/pituushyppy/v6/"


def open_game(site, context):
    old = v5.URL
    v5.URL = URL
    try:
        return v5.open_game(site, context)
    finally:
        v5.URL = old


def tap(page):
    page.mouse.click(180, 400)
    page.evaluate("step(0.01)")


def test_alone_the_podium_stays_until_a_tap_after_the_ceremony(site, context):
    page = open_game(site, context)
    v5.win_meet(page)
    # A whole minute later the podium is still there, with the hint to tap.
    page.evaluate("for (let i = 0; i < 60 * 60; i++) step(1 / 60)")
    assert page.evaluate("K.ending !== null")
    assert page.is_hidden("#menu")
    texts = page.evaluate("""() => {
      const real = CanvasRenderingContext2D.prototype.fillText, out = [];
      CanvasRenderingContext2D.prototype.fillText = function (s) { out.push(String(s)); return real.apply(this, arguments); };
      try { draw(); } finally { CanvasRenderingContext2D.prototype.fillText = real; }
      return out;
    }""")
    assert "Napauta jatkaaksesi" in texts
    tap(page)
    assert page.is_visible("#menu")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    # A tap during the ceremony finishes it; only the next one leaves.
    page.click("#go")
    for _ in range(6):
        page.evaluate("go(9, 20, -0.05); quick()")
    page.evaluate("step(1)")
    tap(page)
    done = page.evaluate("AiPelitKisa.PODIUM_DONE")
    assert done <= page.evaluate("K.ending.t") < done + 0.5
    assert page.is_hidden("#menu")
    tap(page)
    assert page.is_visible("#menu")
    assert page.errors == []


def test_with_friends_each_phone_leaves_the_podium_by_its_own_tap(site, browser):
    old = v2.URL
    v2.URL = URL
    try:
        relay, pages = v2.room(site, browser, ["Eero", "Aino"])
    finally:
        v2.URL = old
    host = pages[0]
    for _ in range(40):
        if host.evaluate("K.comp === null || K.comp.over"):
            break
        p = v2.jumper_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        p.evaluate("go(8.5, 20, -0.1); quick()")
        host.wait_for_function(f"K.comp.seq > {n} || K.comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("K.ending !== null", timeout=10000)
        # In a room a tap does not skip the ceremony: every phone sees all of it.
        tap(p)
        assert p.evaluate("K.ending !== null && K.ending.t < 1")
        # Played through and a minute more, the podium is still there.
        p.evaluate("for (let i = 0; i < 70 * 60; i++) step(1 / 60)")
        assert p.evaluate("K.ending !== null")
        p.evaluate("draw()")  # the steps above draw nothing: draw the podium as it is now
        assert all(n > 20 for n in p.evaluate(MEDAL_PIXELS))
    # The host leaves to the room; Aino's phone keeps the podium until she taps too.
    tap(host)
    host.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
    assert pages[1].evaluate("K.ending !== null")
    tap(pages[1])
    pages[1].wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
    for p in pages:
        assert p.evaluate("localStorage.getItem('ai-pelit:pituushyppy:kisat')") == "1"
        assert p.errors == []
    for p in pages:
        p.context.close()
