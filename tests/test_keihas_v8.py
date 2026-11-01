"""Keihäänheitto v8: while aiming, the feet show greyed out and do not flash (#313)."""

import test_keihas_v4 as v4

URL = "games/keihas/v8/"
OFF = "#22385a"
# The colour pad k is drawn in, read from the canvas beside its left edge (away from its icon).
COLOR = """() => {
  window.color = k => {
    const b = pads().find(p => p.k === k);
    draw(0);
    const d = x.getImageData(Math.round((b.x + 12) * DPR), Math.round((b.y + b.h / 2) * DPR), 1, 1).data;
    return '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('');
  };
}"""


def open_game(site, context):
    old = v4.URL
    v4.URL = URL
    try:
        page = v4.open_game(site, context)
    finally:
        v4.URL = old
    page.evaluate(COLOR)
    return page


def test_while_aiming_the_feet_are_greyed_out_and_do_not_flash(site, context):
    page = open_game(site, context)
    page.click("#go")
    # Running, every pad works and a foot lights up when pressed.
    run = page.evaluate("ready(); [padOn(1), padOn(2), padOn(3), (press(1), flash[1] > 0), color(1) !== '%s']" % OFF)
    assert run == [True, True, True, True, True]
    # Holding the throw: a step adds nothing, so the feet are off, grey, and a press does not flash them.
    aim = page.evaluate("""th.x = -10; startAim(1); flash[1] = flash[2] = 0;
      const v = th.v; press(2); press(1);
      [th.phase, padOn(1), padOn(2), padOn(3), flash[1], flash[2], th.v === v, color(1), color(2), color(3)]""")
    assert aim[:7] == ["aim", False, False, True, 0, 0, True]
    assert aim[7] == OFF and aim[8] == OFF and aim[9] != OFF
    # Let go: the javelin flies and every pad is off until the next throw.
    fly = page.evaluate("th.aimT = (36 - AIM0) / AIM_RATE; th.ang = 36; release(); flash[3] = 0; startAim(2); [th.phase, padOn(1), padOn(3), flash[3], color(3)]")
    assert fly == ["fly", False, False, 0, OFF]
    assert page.errors == []
