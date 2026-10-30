"""Trampoliini v2: a finger on the screen keeps the knees bent, letting go is the push."""

from conftest import ROOT

URL = "games/trampoliini/v2/"
# Each check steps and reads in one call; the page's own loop is stopped so it cannot step between.
HOLD = "() => { window.__step = step; step = () => {}; }"


def open_game(site, context, width=360):
    site.build(ROOT / "games")
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": 740})
    page.goto(site.url + URL)
    page.click("#go")
    page.evaluate(HOLD)
    return page


def test_holding_keeps_the_knees_bent_and_letting_go_straightens_them(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const s = window.__step; stand(0); J.vin = 6; while (phase === 'mat') s(1 / 60);
      for (let i = 0; i < 10; i++) s(1 / 60);
      const before = legBend(); squatDown(7);
      for (let i = 0; i < 30; i++) s(1 / 60);
      const held = [legBend(), J.pumpT];
      squatUp(7); const pushed = J.pumpT;
      for (let i = 0; i < 15; i++) s(1 / 60);
      return [before, held, pushed, phase === 'air' ? legBend() : -1]; }""")
    before, held, pushed, after = r
    assert before == 0 and held[0] > 0.85 and held[1] is None   # pressing alone is no push
    assert after < 0.05


def test_letting_go_at_the_bottom_of_the_bounce_goes_higher(site, context):
    page = open_game(site, context)
    off = """(release) => { const s = window.__step;
      stand(0); J.vin = 6; squatDown(1);
      while (phase === 'mat') { if (release !== null && J.matT >= release - 1e-6) { squatUp(1); release = null; } s(1 / 60); }
      return J.vy; }"""
    pushed = page.evaluate(off, 0.15)
    held_through = page.evaluate(off, None)   # held through the whole bounce: no push, it dies down
    assert pushed > 6 > held_through


def test_a_finger_pressed_on_the_mat_presses_it_deeper_without_changing_the_bounce(site, context):
    page = open_game(site, context)
    plain, bent = page.evaluate("""() => {
      const s = window.__step, run = b => {
        stand(0); J.vin = 6; J.pumpT = CONTACT / 2; bend = b;
        s(1 / 60); s(1 / 60); const y = J.y; while (phase === 'mat') s(1 / 60); return [y, J.vy]; };
      return [run(0), run(1)]; }""")
    assert bent[0] < plain[0]
    assert bent[1] == plain[1]


def test_letting_go_of_a_flip_button_is_not_a_push_while_another_finger_squats(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const s = window.__step; stand(0); J.vin = 6; J.matT = 0.02;
      squatDown(1); squatUp(2);              // another finger (a button) lifts
      const after_other = [squat, J.pumpT];
      squatUp(1);                             // the squatting finger lets go
      return [after_other, squat, J.pumpT]; }""")
    assert r[0] == [True, None]
    assert r[1] is False and abs(r[2] - 0.02) < 1e-9


def test_the_real_screen_press_and_release_bend_and_push(site, context):
    page = open_game(site, context)
    page.evaluate("() => { const s = window.__step; stand(0); J.vin = 6; while (phase === 'mat') s(1 / 60); }")
    page.mouse.move(180, 400)
    page.mouse.down()
    assert page.evaluate("squat") is True
    page.mouse.up()
    assert page.evaluate("[squat, kick]") == [False, 1]


def test_the_buttons_and_hint_fit_a_390_px_phone(site, context):
    page = open_game(site, context, width=390)
    boxes = [page.locator("#pad button").nth(i).bounding_box() for i in range(3)]
    assert boxes[0]["x"] >= 0 and boxes[2]["x"] + boxes[2]["width"] <= 390
    assert all(b["height"] >= 60 for b in boxes)
    hint = page.evaluate("() => { x.font = '600 14px system-ui,sans-serif'; return x.measureText('Pidä ruutua pohjassa, päästä irti matolla').width; }")
    assert hint < 360 - 20


def test_v2_plays_on_with_v1_s_saved_level_and_record(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:trampoliini:taso', '3'); localStorage.setItem('ai-pelit:trampoliini:ennatys', '210')")
    page.reload()
    assert page.inner_text("#level") == "Taso 3: Minitrampoliini"
    assert page.inner_text("#stats").startswith("Ennätys 210 p")
