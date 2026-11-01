"""Aitajuoksu v9: a pad that does nothing shows greyed out and does not flash (#313)."""

from conftest import ROOT

import test_aitajuoksu_v2 as v2
from test_aitajuoksu_v4 import open_game, start_running

URL = "games/aitajuoksu/v9/"
OFF = "#22385a"
# The colour pad k is drawn in, read from the canvas beside its left edge (away from its icon).
COLOR = """() => {
  window.color = k => {
    const b = pads().find(p => p.k === k);
    draw();
    const d = x.getImageData(Math.round((b.x + 12) * DPR), Math.round((b.y + b.h / 2) * DPR), 1, 1).data;
    return '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('');
  };
}"""


def test_at_the_start_only_the_feet_are_on(site, context):
    page = open_game(site, context, URL)
    page.evaluate(COLOR)
    page.click("#go")
    page.evaluate("race.runners.forEach(r => { r.ai.jumpy = null; }); race.gunAt = 99")
    # Waiting for the gun a step is a false start, so the feet stay on; the jump does nothing.
    cd = page.evaluate("[race.phase, padOn(1), padOn(2), padOn(3), (flash[3] = 0, press(3), flash[3]), color(3), color(1) !== '%s']" % OFF)
    assert cd == ["cd", True, True, False, 0, OFF, True]
    assert page.errors == []


def test_over_a_hurdle_and_past_the_line_the_pads_are_off(site, context):
    page = open_game(site, context, URL)
    page.evaluate(COLOR)
    start_running(page)
    run = page.evaluate("[padOn(1), padOn(2), padOn(3), color(3) !== '%s', (press(1), flash[1] > 0)]" % OFF)
    assert run == [True, True, True, True, True]
    # In the air every pad is off: a step adds no speed and does not flash.
    air = page.evaluate("""press(3); tick(0.05); flash[1] = flash[2] = flash[3] = 0; const v = me.v; press(2); press(3);
      [me.y > 0 || me.vy > 0, padOn(1), padOn(2), padOn(3), flash[2], flash[3], me.v <= v, color(1), color(2), color(3)]""")
    assert air == [True, False, False, False, 0, 0, True, OFF, OFF, OFF]
    # Stumbling, the same.
    assert page.evaluate("me.y = 0; me.vy = 0; me.stum = 0.5; [padOn(1), padOn(3)]") == [False, False]
    # Past the line, the same.
    assert page.evaluate("me.stum = 0; me.fin = 12.3; flash[1] = 0; press(1); [padOn(1), padOn(3), flash[1], color(1)]") == [False, False, 0, OFF]
    assert page.errors == []


def test_with_no_hurdles_the_jump_is_off(site, context):
    page = open_game(site, context, URL)
    page.evaluate(COLOR)
    page.evaluate("hurdles = false")
    start_running(page)
    flat = page.evaluate("[race.hurdles, padOn(1), padOn(3), (flash[3] = 0, press(3), flash[3]), me.vy, color(3)]")
    assert flat == [False, True, False, 0, 0, OFF]
    assert page.errors == []


def test_after_a_false_start_the_feet_are_off_until_the_start_is_called_again(site, context):
    page = open_game(site, context, URL)
    page.evaluate(COLOR)
    page.click("#go")
    page.evaluate("race.runners.forEach(r => { r.ai.jumpy = null; }); race.gunAt = 99; race.cdT = SET_AT + 0.1")
    # A step after "Valmiit…" is a false start: the whistle blows and every pad is grey.
    fs = page.evaluate("press(1); [race.phase, me.card, padOn(1), padOn(2), padOn(3), (flash[2] = 0, press(2), flash[2]), color(1)]")
    assert fs == ["false", 1, False, False, False, 0, OFF]
    # The start is called again: the feet are on, the jump still off.
    page.wait_for_function("race.phase === 'cd'", timeout=6000)
    assert page.evaluate("[padOn(1), padOn(2), padOn(3), color(1) !== '%s']" % OFF) == [True, True, False, True]
    assert page.errors == []


def test_with_friends_a_red_card_greys_out_the_jump_too_after_the_gun(site, browser):
    site.build(ROOT / "games")
    old = v2.URL
    v2.URL = URL
    try:
        host, guest = v2.room_of_two_at_set(site, browser)
    finally:
        v2.URL = old
    guest.evaluate(COLOR)
    # Aino's second false start: a red card.
    host.evaluate("race.runners[1].card = 1; falseStart(race.runners[1])")
    guest.wait_for_function("me.card === 2", timeout=3000)
    host.wait_for_function("race.phase === 'cd'", timeout=5000)
    host.evaluate("race.gunAt = 0.1")
    guest.wait_for_function("race.phase === 'run'", timeout=5000)
    # After the gun the out runner's pads are all grey, and neither a step nor a jump moves them.
    out = guest.evaluate("""flash[1] = flash[3] = 0; press(1); press(3);
      [padOn(1), padOn(2), padOn(3), flash[1], flash[3], me.vy, me.v, color(1), color(3)]""")
    assert out == [False, False, False, 0, 0, 0, 0, OFF, OFF]
    # The host, still in the race, can jump.
    assert host.evaluate("[me.card, padOn(3)]") == [0, True]
    assert host.errors == guest.errors == []
    for p in (host, guest):
        p.context.close()
