"""Korkeushyppy v3: the medal ceremony, and the podium stays until a tap (yleisurheilu-4, #176)."""

import pytest
from conftest import ROOT, turn

import test_korkeushyppy_v2 as old
from test_pituushyppy_v5 import MEDAL_PIXELS

URL = "games/korkeushyppy/v3/"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.add_init_script(old.SEEDED % 1)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    # A nickname, so the high-score list's name box does not open over the end screen.
    page.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    page.goto(site.url + URL)
    page.evaluate(old.HELPERS)
    return page


def win_meet(page):
    page.click("#go")
    for _ in range(80):
        if page.evaluate("K.comp.over"):
            break
        page.evaluate("""ready(); if (soleWinner(mine()) && bestOf(mine()) >= 1.95) { stopMeet(); quick(); } else good()""")
    assert page.evaluate("K.comp.over && K.ending.place === 1")


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
    # The heights on the podium are the standings' best heights.
    assert page.evaluate("K.ending.res.slice(0, 3).every(r => r.best > 1)")
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
    url = old.URL
    old.URL = URL
    try:
        relay, pages = old.room(site, browser, ["Eero", "Aino"])
    finally:
        old.URL = url
    host = pages[0]
    for _ in range(60):
        if host.evaluate("K.comp === null || K.comp.over"):
            break
        p = old.jumper_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        p.evaluate("""mine().rec.filter(r => r && r.includes('O')).length < 2 ? good() : bad()""")
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


def test_a_shared_place_shares_the_medal(site, context):
    page = open_game(site, context)
    win_meet(page)
    page.evaluate("K.ending.t = 0.2; draw()")
    base = page.evaluate(MEDAL_PIXELS)
    # The second jumper ties the winner on the countback: both share the 1st place, the next is 3rd.
    page.evaluate("const r = K.ending.res; r[1].best = r[0].best; r[1].place = 1;")
    texts = page.evaluate("""() => {
      const real = CanvasRenderingContext2D.prototype.fillText, pod = K.drawPodium, out = [];
      K.drawPodium = (...a) => {
        CanvasRenderingContext2D.prototype.fillText = function (s) { out.push(String(s)); return real.apply(this, arguments); };
        try { pod(...a); } finally { CanvasRenderingContext2D.prototype.fillText = real; }
      };
      K.ending.t = 6.5; draw(); K.drawPodium = pod;
      return out;
    }""")
    gold, silver, bronze = [n - b for n, b in zip(page.evaluate(MEDAL_PIXELS), base)]
    # Two golds on the podium, no silver, the bronze for the 3rd.
    assert gold > 40 and silver < 5 and bronze > 20
    assert texts.count("🥇") == 2 and texts.count("🥈") == 0 and texts.count("🥉") == 1
    assert texts.count("1") >= 2 and "2" not in [t for t in texts if t in ("1", "2", "3")]
    assert page.errors == []
