"""Piano v4: the hit zone is drawn, and it is the same time window for every note."""

from conftest import ROOT

URL = "games/piano/v4/"


def start_at(site, context, level):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate(f"localStorage.setItem('ai-pelit:piano:taso', '{level}')")
    page.reload()
    page.click("#go")
    page.evaluate("state = 'menu'")  # hold the clock; each check sets the time itself
    return page


# Press a note's lane `off` seconds from its beat; returns [hit, hearts left]. The note has no
# other note in its lane within 0.35 s: a press that close to another one goes to the nearer.
TRY = """off => {
  const n = cur.notes.find(m => !m.hit && !m.missed &&
    !cur.notes.some(o => o !== m && o.lane === m.lane && Math.abs(o.t - m.t) < 0.35));
  now = n.t + off; state = 'play'; tap(n.lane); state = 'menu';
  return [n.hit, lives];
}"""


def test_the_slowest_and_the_fastest_song_have_the_same_window(site, context):
    for level in (1, 13):  # Tuiki tuiki tähtönen and Tulimyrsky
        page = start_at(site, context, level)
        assert page.evaluate(TRY, -0.15) == [True, 3], level
        assert page.evaluate(TRY, 0.15) == [True, 3], level
        page.close()


def test_the_drawn_zone_is_that_window_at_the_fall_speed(site, context):
    page = start_at(site, context, 1)
    slow = page.evaluate("[zonePx(GOOD), GOOD / lead(level) * (hitY - topY)]")
    assert abs(slow[0] - slow[1]) < 0.01
    page.evaluate("level = 13; startLevel(); state = 'menu'")
    fast = page.evaluate("zonePx(GOOD)")
    # A faster-falling note crosses more pixels in the same time, so its zone is taller.
    assert fast > slow[0] * 1.4


def test_a_note_lights_up_while_it_is_in_the_zone(site, context):
    page = start_at(site, context, 1)
    page.evaluate("now = cur.notes[0].t - 0.3")
    assert page.evaluate("inZone(cur.notes[0])") is False
    page.evaluate("now = cur.notes[0].t - 0.1")
    assert page.evaluate("inZone(cur.notes[0])") is True
    # Its middle is on the line at its beat.
    page.evaluate("now = cur.notes[0].t")
    assert page.evaluate("yOf(cur.notes[0].t) === hitY") is True


def test_two_lanes_in_the_zone_at_once_both_hit(site, context):
    page = start_at(site, context, 13)
    page.evaluate("""() => {
      const [a] = cur.notes; const b = cur.notes.find(n => n.lane !== a.lane);
      now = (a.t + b.t) / 2; window._pair = [a, b];
      state = 'play'; tap(b.lane); tap(a.lane); state = 'menu';
    }""")
    assert page.evaluate("[_pair.every(n => n.hit), lives]") == [True, 3]


def test_a_press_between_two_close_notes_in_a_lane_takes_the_nearer(site, context):
    page = start_at(site, context, 13)
    pair = page.evaluate("""() => {
      for (let i = 0; i < cur.notes.length; i++) for (let k = i + 1; k < cur.notes.length; k++) {
        const a = cur.notes[i], b = cur.notes[k];
        if (a.lane === b.lane && b.t - a.t < 0.32) {
          now = b.t - 0.03; state = 'play'; tap(b.lane); state = 'menu';
          return [a.hit, b.hit, lives];
        }
      }
    }""")
    assert pair == [False, True, 3]


def test_the_zone_follows_a_new_level_after_a_reload(site, context):
    page = start_at(site, context, 13)
    fast = page.evaluate("zonePx(GOOD)")
    page.evaluate("localStorage.setItem('ai-pelit:piano:taso', '13')")
    page.reload()
    page.click("#prev"); page.click("#prev"); page.click("#prev"); page.click("#prev")
    page.click("#go")
    assert page.evaluate("[level, zonePx(GOOD) < " + str(fast) + "]") == [9, True]


def test_the_zone_fits_a_390_px_phone(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.click("#go")
    # The zone's upper half and the line sit above the keys; the lane is a quarter of the width.
    assert page.evaluate("[hitY - zonePx(GOOD) > topY + 20, hitY < btnTop, Math.round(laneW)]") == [True, True, 98]
    ctx.close()
