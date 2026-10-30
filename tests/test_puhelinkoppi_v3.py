"""Puhelinkoppi v3: a streak of tricks, picked with the spin buttons, is the goal."""

from conftest import ROOT

FLY = """(seconds) => { for (let t = 0; t < seconds && (state === 'air' || state === 'drop' || state === 'settle'); t += 1 / 60) step(1 / 60); return state; }"""

# Throws as the player would: the picked spin, and a flick fast enough for upward speed v0.
THROW = """([kind, v0]) => {
  pick(kind);
  const k = project(pos)[2] / focal();
  throwFromSwipe({ speedUp: v0 * Math.cos(PITCH) / k, speedSide: 0 });
  for (let t = 0; t < 4 && state !== 'result'; t += 1 / 60) step(1 / 60);
  return result;
}"""

NEXT = "resultT = -1e9; onDown({ preventDefault() {} })"  # a tap on the result screen


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/puhelinkoppi/v3/")
    page.evaluate("noise = 0")
    return page


def test_tricks_caught_screen_up_make_a_streak_and_a_wrong_one_ends_it(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:puhelinkoppi:taso', '5')")  # v2's level stays untouched
    assert page.evaluate("[streak, record, trick]") == [0, 0, {"kind": "suora", "n": 0}]
    r = page.evaluate(THROW, ["suora", 3])
    assert (r["kind"], r["streak"], r["record"]) == ("win", 1, True)
    page.evaluate(NEXT)
    assert page.evaluate("trick") == {"kind": "kierre", "n": 1}
    r = page.evaluate(THROW, ["kierre", 2.5])
    assert (r["kind"], r["turns"], r["streak"]) == ("win", 1, 2)
    page.evaluate(NEXT)
    assert page.evaluate("trick") == {"kind": "voltti", "n": 1}
    # A kierre when a voltti was asked: caught screen up, but the streak ends.
    r = page.evaluate(THROW, ["kierre", 2.5])
    assert (r["kind"], r["streak"]) == ("trick", 0)
    page.reload()
    assert page.evaluate("[streak, record, catches]") == [0, 2, 3]
    assert page.evaluate("localStorage.getItem('ai-pelit:puhelinkoppi:taso')") == "5"


def test_every_trick_can_be_thrown_within_the_hand_s_reach(site, context):
    page = open_game(site, context)
    for kind, n in [("suora", 0), ("kierre", 1), ("kierre", 2), ("voltti", 1), ("voltti", 2)]:
        wins = []
        for i in range(46):
            v0 = 2 + i * 0.1
            page.evaluate(f"newRound(); trick = {{ kind: '{kind}', n: {n} }}")
            if page.evaluate(THROW, [kind, v0])["kind"] == "win":
                wins.append(round(v0, 1))
        assert wins, f"{kind} {n} cannot be thrown"


def test_the_streak_survives_closing_the_game_and_a_record_goes_to_the_streak_list(site, context):
    page = open_game(site, context)
    page.evaluate(THROW, ["suora", 3])
    page.reload()
    assert page.evaluate("[streak, record]") == [1, 1]
    queue = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))")
    assert queue["puhelinkoppi|putki"]["score"] == 1 and queue["puhelinkoppi|putki"]["version"] == 3


def test_the_spin_buttons_pick_the_spin_only_before_the_throw(site, context):
    page = open_game(site, context)
    page.click("#spins button:has-text('Voltti')")
    assert page.evaluate("spin") == "voltti"
    assert page.locator("#spins button.on").inner_text().endswith("Voltti")
    page.evaluate("launch({ v0: 6 })")
    page.wait_for_function("document.getElementById('spins').classList.contains('off')")
    page.evaluate("pick; document.querySelector('#spins button[data-spin=kierre]').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))")
    assert page.evaluate("spin") == "voltti"


def test_a_catch_screen_down_or_a_drop_ends_the_streak_but_keeps_the_record(site, context):
    page = open_game(site, context)
    for ending, throw in [("down", "launch({ v0: 3, wx: 5 })"), ("drop", "launch({ v0: 3, vx: 0.5 })")]:
        page.evaluate("localStorage.setItem('ai-pelit:puhelinkoppi:putki-nyt', '3');"
                      "localStorage.setItem('ai-pelit:puhelinkoppi:putki', '5')")
        page.reload()
        page.evaluate("noise = 0")
        assert page.evaluate("[streak, record]") == [3, 5]
        page.evaluate(throw)
        page.evaluate(FLY, 4)
        assert page.evaluate("[result.kind, streak, record]") == [ending, 0, 5]
        assert page.evaluate("localStorage.getItem('ai-pelit:puhelinkoppi:putki-nyt')") == "0"
        page.reload()
        assert page.evaluate("[streak, record]") == [0, 5]
