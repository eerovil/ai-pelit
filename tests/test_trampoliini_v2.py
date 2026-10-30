"""Trampoliini v2: every tap bends the legs and presses the mat."""

from conftest import ROOT

URL = "games/trampoliini/v2/"
# Each check steps and reads in one call: the page's own loop keeps stepping between calls.
HOLD = "() => { window.__step = step; step = () => {}; }"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.click("#go")
    page.evaluate(HOLD)
    return page


def test_a_tap_in_the_air_bends_the_knees_and_they_straighten_again(site, context):
    page = open_game(site, context)
    bends = page.evaluate("""() => {
      const s = window.__step; stand(0); J.vin = 6; while (phase === 'mat') s(1 / 60);
      for (let i = 0; i < 20; i++) s(1 / 60);
      const before = legBend(); tap(); const now = legBend();
      for (let i = 0; i < 15; i++) s(1 / 60);
      return [before, now, legBend(), phase]; }""")
    assert bends[0] == 0 and bends[1] > 0.8 and bends[2] == 0 and bends[3] == "air"


def test_a_tap_on_the_mat_presses_it_deeper_but_the_bounce_is_the_same(site, context):
    page = open_game(site, context)
    plain, kicked = page.evaluate("""() => {
      const s = window.__step, run = k => {
        stand(0); J.vin = 6; J.matT = 0; J.pumpT = CONTACT / 2; kick = k;
        s(1 / 60); s(1 / 60); const y = J.y; while (phase === 'mat') s(1 / 60); return [y, J.vy]; };
      return [run(0), run(1)]; }""")
    assert kicked[0] < plain[0]          # deeper into the mat
    assert kicked[1] == plain[1]         # the take-off speed only depends on the timing


def test_every_tap_bends_the_legs_even_when_it_does_not_count(site, context):
    page = open_game(site, context)
    # High in the air, far from the mat: no pump, but the legs still answer the tap.
    r = page.evaluate("""() => {
      const s = window.__step; stand(0); J.vin = 7; while (phase === 'mat') s(1 / 60);
      for (let i = 0; i < 30; i++) s(1 / 60);
      tap(); return [legBend() > 0.8, J.pumpT]; }""")
    assert r == [True, None]


def test_v2_plays_on_with_v1_s_saved_level_and_record(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:trampoliini:taso', '3'); localStorage.setItem('ai-pelit:trampoliini:ennatys', '210')")
    page.reload()
    assert page.inner_text("#level") == "Taso 3: Minitrampoliini"
    assert page.inner_text("#stats").startswith("Ennätys 210 p")


def test_a_flip_button_on_the_mat_and_a_second_tap_kick_too_but_only_the_first_push_counts(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const s = window.__step; stand(0); J.vin = 6; J.matT = CONTACT / 2;
      press(1); const first = [legBend() > 0.8, J.pumpT];
      for (let i = 0; i < 6; i++) s(1 / 60);
      const faded = legBend(); tap();
      return [first, faded < legBend(), J.pumpT, J.queued]; }""")
    assert r[0] == [True, 0.15] and r[1] is True
    assert r[2] == 0.15 and r[3] == 1   # the second tap kicks the legs again but is not a second push


def test_the_buttons_fit_a_390_px_phone(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.set_viewport_size({"width": 390, "height": 740})
    page.goto(site.url + URL)
    page.click("#go")
    boxes = [page.locator("#pad button").nth(i).bounding_box() for i in range(3)]
    assert boxes[0]["x"] >= 0 and boxes[2]["x"] + boxes[2]["width"] <= 390
    assert all(b["height"] >= 60 for b in boxes)
