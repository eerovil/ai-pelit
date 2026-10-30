"""Trampoliini in a phone-sized Chromium: bounces, tricks, falls and levels."""

from conftest import ROOT

URL = "games/trampoliini/v1/"

# Plays one trick as a player would: taps at the bottom of each bounce until the trampoline
# throws as high as it can, then presses the flip button on the mat (and 🌀 for a twist), holds
# the tuck until `lead` radians before the last upright, lets go, and lands.
TRICK = """([n, tw, lead]) => {
  const dt = 1 / 60;
  const run = (cond, max = 30) => { for (let t = 0; t < max && cond(); t += dt) step(dt); };
  stand(0); lastLand = null;
  for (let b = 0; b < 30; b++) {
    run(() => !(phase === 'mat' && J.matT >= CONTACT / 2 - 1e-6));
    if (phase !== 'mat') return { crash: 'phase ' + phase };
    if (J.vin >= T.vMax - 0.05) break;
    tap();
    run(() => phase === 'mat');
  }
  if (n) press(n > 0 ? 1 : -1);
  if (tw) twistTap();
  if (!n) release();
  run(() => phase === 'mat');
  for (let k = 1; k < tw; k++) twistTap();
  if (n) { run(() => phase === 'air' && Math.abs(J.rot) < Math.abs(n) * 2 * Math.PI - lead); release(); }
  run(() => phase === 'air');
  return lastLand;
}"""


def open_game(site, context, level=None):
    site.build(ROOT / "games")
    page = context.new_page()
    if level:
        page.goto(site.url + URL)
        page.evaluate(f"localStorage.setItem('ai-pelit:trampoliini:taso', '{level}')")
    page.goto(site.url + URL)
    return page


def play(page, n, tw):
    """The first release point that lands the trick clean, or None."""
    for i in range(25):
        lead = 0.2 + i * 0.1
        r = page.evaluate(TRICK, [n, tw, lead])
        if r and r.get("trick") == [n, tw] and r.get("clean"):
            return lead
    return None


def test_the_menu_shows_the_level_s_trampoline_and_tricks_and_starts_a_go(site, context):
    page = open_game(site, context)
    assert page.inner_text("#level") == "Taso 1: Iso pihatrampoliini"
    assert page.inner_text("#tasks").split("\n") == ["⭐ Kierrehyppy", "⭐ Voltti taakse", "⭐ Voltti eteen"]
    page.click("#go")
    assert page.evaluate("[phase, hearts, points]") == ["mat", 3, 0]
    assert page.is_visible("#pad button:has-text('Taakse')")


def test_every_level_has_its_own_size_of_trampoline(site, context):
    page = open_game(site, context)
    sizes = page.evaluate("[1, 2, 3, 4, 5].map(n => TRAMPS[levelOf(n).tramp].half)")
    assert len(set(sizes)) == 5


def test_a_tap_at_the_bottom_of_the_bounce_goes_higher_and_no_tap_goes_lower(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("stand(0); J.vin = 5; J.matT = CONTACT / 2; tap(); while (phase === 'mat') step(1 / 60)")
    assert page.evaluate("J.vy") > 5.5
    page.evaluate("stand(0); J.vin = 5; while (phase === 'mat') step(1 / 60)")
    assert page.evaluate("J.vy") < 5
    # Never higher than the trampoline throws.
    page.evaluate("stand(0); J.vin = 30; J.matT = CONTACT / 2; tap(); while (phase === 'mat') step(1 / 60)")
    assert page.evaluate("J.vy") == page.evaluate("T.vMax")


def test_every_trick_of_the_first_ten_levels_can_be_landed(site, context):
    page = open_game(site, context)
    for lv in range(1, 11):
        page.evaluate(f"level = {lv}; setup()")
        for n, tw in page.evaluate("L.tasks"):
            assert play(page, n, tw) is not None, f"level {lv}: {n} turns, {tw} twists"


def test_a_back_flip_scores_and_ticks_off_its_trick(site, context):
    page = open_game(site, context)
    page.click("#go")
    r = page.evaluate(TRICK, [1, 0, 1.2])
    assert r == {"trick": [1, 0], "clean": True}
    assert page.evaluate("tasks.map(k => k.done)") == [False, True, False]
    assert page.evaluate("points") > 25 and page.evaluate("hearts") == 3


def test_holding_the_tuck_into_the_landing_is_a_fall_and_costs_a_heart(site, context):
    page = open_game(site, context)
    page.click("#go")
    r = page.evaluate(TRICK, [1, 0, -2])  # never lets go
    assert r["crash"] == "kaatui"
    assert page.evaluate("[phase, hearts]") == ["down", 2]
    page.evaluate("for (let i = 0; i < 120; i++) step(1 / 60)")
    assert page.evaluate("phase") in ("mat", "air")


def test_off_a_small_trampoline_you_fall_to_the_grass(site, context):
    page = open_game(site, context, level=3)
    page.click("#go")
    assert page.evaluate("T.name") == "Minitrampoliini"
    page.evaluate("stand(0); J.vin = 5; J.vx = 1.5; while (phase !== 'down') step(1 / 60)")
    assert page.evaluate("[lastLand.crash, J.off, hearts]") == ["ohi", True, 2]


def test_the_net_of_the_big_garden_trampoline_keeps_you_on(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("stand(0); J.vin = 6; J.vx = 4; for (let i = 0; i < 200; i++) step(1 / 60)")
    assert page.evaluate("[hearts, J.off]") == [3, False]


def test_three_falls_end_the_go_and_the_menu_offers_it_again(site, context):
    page = open_game(site, context)
    page.click("#go")
    for _ in range(3):
        page.evaluate(TRICK, [1, 0, -2])
        page.evaluate("for (let i = 0; i < 90; i++) step(1 / 60)")
    page.evaluate("for (let i = 0; i < 200 && phase !== 'menu'; i++) step(1 / 60)")
    assert page.evaluate("phase") == "menu"
    assert page.inner_text("#result").startswith("Sydämet loppuivat")
    assert page.inner_text("#go") == "Uudestaan"
    assert page.evaluate("localStorage.getItem('ai-pelit:trampoliini:taso')") is None


def test_doing_every_trick_clears_the_level_saves_the_next_and_sends_the_points(site, context):
    page = open_game(site, context)
    page.click("#go")
    for n, tw in page.evaluate("L.tasks"):
        assert play(page, n, tw) is not None
    page.evaluate("for (let i = 0; i < 200 && phase !== 'menu'; i++) step(1 / 60)")
    assert page.inner_text("#result").startswith("Taso 1 läpi!")
    assert page.inner_text("#level") == "Taso 2: Pieni pihatrampoliini"
    assert page.evaluate("localStorage.getItem('ai-pelit:trampoliini:taso')") == "2"
    pts = page.evaluate("lastResult.points")
    assert page.evaluate("+localStorage.getItem('ai-pelit:trampoliini:ennatys')") == pts
    page.reload()
    assert page.inner_text("#stats").startswith(f"Ennätys {pts} p")
    queue = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))")
    assert queue["trampoliini|main"]["score"] == pts
