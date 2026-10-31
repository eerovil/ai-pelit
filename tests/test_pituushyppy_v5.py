"""Pituushyppy v5: the medal ceremony at the end of the meet (public/lib/yleisurheilu-2/kisa.js, #176)."""

import json

import pytest
from conftest import ROOT, turn
from test_pituushyppy_v2 import HELPERS, SEEDED

URL = "games/pituushyppy/v5/"


def open_game(site, context, seed=1):
    site.build(ROOT / "games")
    page = context.new_page()
    page.add_init_script(SEEDED % seed)
    # A nickname, so the high-score list's name box does not open over the end screen.
    page.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def win_meet(page):
    """Jumps six long ones: the meet ends with this phone's jumper first."""
    page.click("#go")
    for _ in range(6):
        page.evaluate("go(9, 20, -0.05); quick()")
    assert page.evaluate("K.comp.over && K.ending.at === 0 && K.ending.t < 0.1")


# How many pixels of the podium's part of the screen are a medal's colour (gold, silver, bronze),
# within a few steps of it.
MEDAL_PIXELS = """() => {
  const top = Math.round((safeT + 44) * DPR), h = Math.round((land ? H - safeT - 52 : 200) * DPR);
  const w = Math.round((land ? W * 0.5 : W) * DPR);
  const d = x.getImageData(0, top, w, h).data, want = [[0xf6, 0xc4, 0x45], [0xdd, 0xe3, 0xea], [0xdd, 0x8d, 0x4c]];
  const n = [0, 0, 0];
  for (let i = 0; i < d.length; i += 4)
    want.forEach((c, k) => { if (Math.abs(d[i] - c[0]) < 6 && Math.abs(d[i + 1] - c[1]) < 6 && Math.abs(d[i + 2] - c[2]) < 6) n[k]++; });
  return n;
}"""


def at(page, t):
    page.evaluate(f"window.texts = []; K.ending.t = {t}; draw()")


def test_the_medals_are_hung_bronze_silver_gold_and_chime(site, context):
    page = open_game(site, context)
    page.evaluate("() => { window.chimes = []; const real = tone; tone = (f, ...a) => { chimes.push(f); real(f, ...a); }; }")
    win_meet(page)
    # Before the ceremony starts there are no medals on the podium (only the blocks' edges, which
    # blend to near silver, so later counts are taken over this one).
    at(page, 0.2)
    base = page.evaluate(MEDAL_PIXELS)
    assert base[0] == 0 and base[2] == 0
    medals = lambda t: (at(page, t), [n - b for n, b in zip(page.evaluate(MEDAL_PIXELS), base)])[1]
    # Each medal comes in its turn: bronze, then silver, then gold.
    gold, silver, bronze = medals(3.2)
    assert bronze > 20 and silver < 5 and gold == 0
    gold, silver, bronze = medals(4.3)
    assert bronze > 20 and silver > 20 and gold == 0
    assert all(n > 20 for n in medals(6.0))
    # Played through, one chime per medal (the gold has two notes).
    page.evaluate("K.ending.t = 0; chimes = []")
    page.evaluate("for (let i = 0; i < 6.5 * 60; i++) step(1 / 60)")
    # Only the ceremony's notes: a record jump's own two notes come a moment late and may land here.
    page.wait_for_function("chimes.includes(1047)", timeout=2000)
    assert [f for f in page.evaluate("chimes") if f in (523, 659, 784, 1047)] == [523, 659, 784, 1047]
    assert page.evaluate("K.ending !== null")
    assert page.is_hidden("#menu")
    assert page.errors == []


def test_alone_a_tap_finishes_the_ceremony_and_the_next_leaves_it(site, context):
    page = open_game(site, context)
    win_meet(page)
    page.evaluate("step(1)")
    page.mouse.click(180, 400)
    # At the end of the ceremony (an animation frame may have run since the tap).
    done = page.evaluate("AiPelitKisa.PODIUM_DONE")
    assert done <= page.evaluate("K.ending.t") < done + 0.5
    assert page.is_hidden("#menu")
    page.mouse.click(180, 400)
    page.evaluate("step(0.01)")
    assert page.is_visible("#menu")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    # Untouched, the end screen stays up for the whole ceremony and then goes to the menu.
    page.click("#go")
    for _ in range(6):
        page.evaluate("go(9, 20, -0.05); quick()")
    page.evaluate("for (let i = 0; i < 10 * 60; i++) step(1 / 60)")
    assert page.is_hidden("#menu")
    page.evaluate("for (let i = 0; i < 1.2 * 60; i++) step(1 / 60)")
    assert page.is_visible("#menu")
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_ceremony_and_the_standings_fit(site, context, size):
    w, h = size
    page = open_game(site, context)
    turn(page, {"width": w, "height": h})
    win_meet(page)
    page.evaluate("K.ending.res.forEach((r, i) => { if (i) r.name = 'Wwwwwwwwwwwwwwwwwwww' + i; })")
    # Every text the ceremony draws, with where it lands.
    page.evaluate("""() => {
      const real = CanvasRenderingContext2D.prototype.fillText, pod = K.drawPodium;
      window.texts = []; let on = false;
      K.drawPodium = (...a) => { on = true; try { pod(...a); } finally { on = false; } };
      CanvasRenderingContext2D.prototype.fillText = function (s, x0, y0) {
        const m = this.getTransform();
        if (on) texts.push([String(s), x0 + m.e / m.a, y0 + m.f / m.d, this.measureText(s).width, this.textAlign]);
        return real.apply(this, arguments);
      };
    }""")
    # Drawn and read in one go: the next animation frame would add its own.
    texts = page.evaluate("() => { texts = []; K.ending.t = 6.5; draw(); return texts; }")
    names = [t for t in texts if t[0].startswith("Www")]
    assert names, "no names drawn"
    for s, x0, y0, tw, align in texts:
        left = x0 - tw if align == "right" else x0 - tw / 2 if align == "center" else x0
        assert left >= 0 and left + tw <= w + 0.5 and 40 <= y0 <= h, (s, x0, y0)
    # Every competitor is on the standings, the last row too.
    rows = [t for t in texts if t[0].endswith(".") and t[0][:-1].isdigit()]
    assert len(rows) == 9  # places 4–12; the top three show medals
    assert all(n > 20 for n in page.evaluate(MEDAL_PIXELS))
    assert page.errors == []


def test_a_place_with_no_valid_mark_gets_no_medal(site, context):
    page = open_game(site, context)
    win_meet(page)
    at(page, 0.2)
    base = page.evaluate(MEDAL_PIXELS)
    # Only two jumpers with a valid mark: the third block stays empty, and nobody gets the bronze.
    page.evaluate("K.ending.res.slice(2).forEach(r => { r.best = -1; r.marks = [-1, -1, -1]; })")
    at(page, 6.5)
    gold, silver, bronze = [n - b for n, b in zip(page.evaluate(MEDAL_PIXELS), base)]
    assert gold > 20 and silver > 20 and bronze < 10  # a medal is 80 or more; confetti edges a few
    assert page.evaluate("K.ending.res.slice(2).every(r => r.best < 0)")
    assert page.errors == []


def test_with_friends_every_phone_shows_the_ceremony(site, browser):
    from test_pituushyppy_v2 import room, jumper_page
    import test_pituushyppy_v2 as v2
    old = v2.URL
    v2.URL = URL
    try:
        relay, pages = room(site, browser, ["Eero", "Aino"])
    finally:
        v2.URL = old
    host = pages[0]
    for _ in range(40):
        if host.evaluate("K.comp === null || K.comp.over"):
            break
        p = jumper_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        p.evaluate("go(8.5, 20, -0.1); quick()")
        host.wait_for_function(f"K.comp.seq > {n} || K.comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("K.ending !== null", timeout=10000)
        # A tap does not skip it in a room: every phone sees the same ceremony.
        p.mouse.click(180, 400)
        assert p.evaluate("K.ending.t") < 1
        p.evaluate("K.ending.t = 6; draw()")
        assert all(n > 20 for n in p.evaluate(MEDAL_PIXELS))
        p.evaluate("K.ending.t = 99; step(0.01)")
        p.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
        assert p.errors == []
    for p in pages:
        p.context.close()
