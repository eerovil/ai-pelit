"""Moukarinheitto v3: the medal ceremony, and the podium stays until a tap (yleisurheilu-3, #176)."""

import pytest
from conftest import ROOT, turn

import test_moukari_v2 as v4
from test_pituushyppy_v5 import MEDAL_PIXELS

URL = "games/moukari/v3/"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.add_init_script(v4.SEEDED % 1)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    # A nickname, so the high-score list's name box does not open over the end screen.
    page.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    page.goto(site.url + URL)
    page.evaluate(v4.HELPERS)
    return page


def win_meet(page):
    page.click("#go")
    for _ in range(6):
        page.evaluate("spin(4, 0.01, 0); quick()")
    assert page.evaluate("K.comp.over && K.ending.at === 0")


def tap(page):
    page.mouse.click(180, 400)
    page.evaluate("step(0.01)")


def test_the_medals_are_hung_and_the_podium_stays_until_a_tap(site, context):
    page = open_game(site, context)
    win_meet(page)
    page.evaluate("K.ending.t = 0.2; draw()")
    base = page.evaluate(MEDAL_PIXELS)
    # A minute later all three medals are on and the podium is still there.
    page.evaluate("for (let i = 0; i < 60 * 60; i++) step(1 / 60); draw()")
    assert page.evaluate("K.ending !== null")
    assert page.is_hidden("#menu")
    assert all(n - b > 20 for n, b in zip(page.evaluate(MEDAL_PIXELS), base))
    tap(page)
    assert page.is_visible("#menu")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    # A tap during the ceremony finishes it; only the next one leaves.
    win_meet(page)
    page.evaluate("step(1)")
    tap(page)
    done = page.evaluate("AiPelitKisa.PODIUM_DONE")
    assert done <= page.evaluate("K.ending.t") < done + 0.5
    assert page.is_hidden("#menu")
    tap(page)
    assert page.is_visible("#menu")
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (390, 844), (740, 360)])
def test_the_podium_fits(site, context, size):
    w, h = size
    page = open_game(site, context)
    turn(page, {"width": w, "height": h})
    win_meet(page)
    texts = page.evaluate("""() => {
      const real = CanvasRenderingContext2D.prototype.fillText, pod = K.drawPodium, out = [];
      K.drawPodium = (...a) => {
        CanvasRenderingContext2D.prototype.fillText = function (s, x0, y0) {
          out.push([String(s), x0, y0, this.measureText(s).width, this.textAlign]); return real.apply(this, arguments);
        };
        try { pod(...a); } finally { CanvasRenderingContext2D.prototype.fillText = real; }
      };
      K.ending.t = 6.5; draw(); K.drawPodium = pod;
      return out;
    }""")
    assert len(texts) > 20
    for s, x0, y0, tw, align in texts:
        left = x0 - tw if align == "right" else x0 - tw / 2 if align == "center" else x0
        assert left >= 0 and left + tw <= w + 0.5 and 40 <= y0 <= h, (s, x0, y0)
    assert page.errors == []


def test_with_friends_each_phone_leaves_the_podium_by_its_own_tap(site, browser):
    old = v4.URL
    v4.URL = URL
    try:
        relay, pages = v4.room(site, browser, ["Eero", "Aino"])
    finally:
        v4.URL = old
    host = pages[0]
    for _ in range(40):
        if host.evaluate("K.comp === null || K.comp.over"):
            break
        p = v4.thrower_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        p.evaluate("spin(4, 0.01, 0); quick()")
        host.wait_for_function(f"K.comp.seq > {n} || K.comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("K.ending !== null", timeout=10000)
        tap(p)  # in a room a tap does not skip the ceremony
        assert p.evaluate("K.ending !== null && K.ending.t < 1")
        p.evaluate("for (let i = 0; i < 70 * 60; i++) step(1 / 60)")
        assert p.evaluate("K.ending !== null")
    tap(host)
    host.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
    assert pages[1].evaluate("K.ending !== null")
    tap(pages[1])
    pages[1].wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
    for p in pages:
        assert p.errors == []
        p.context.close()
