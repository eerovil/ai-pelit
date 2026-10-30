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
