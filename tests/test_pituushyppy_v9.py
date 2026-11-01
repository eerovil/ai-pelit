"""Pituushyppy v9: while aiming, the feet show greyed out and do not flash (#313)."""

import test_pituushyppy_v5 as v5

URL = "games/pituushyppy/v9/"
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
    old = v5.URL
    v5.URL = URL
    try:
        page = v5.open_game(site, context)
    finally:
        v5.URL = old
    page.evaluate(COLOR)
    return page


def test_while_aiming_the_feet_are_greyed_out_and_in_the_air_every_pad_is_the_legs(site, context):
    page = open_game(site, context)
    page.click("#go")
    run = page.evaluate("""if (th.phase === 'wait') { th.t = 99; step(0.001); }
      [padOn(1), padOn(2), padOn(3), (press(1), flash[1] > 0), color(1) !== '%s']""" % OFF)
    assert run == [True, True, True, True, True]
    # Holding the jump: a step adds nothing, so the feet are off, grey, and a press does not flash them.
    aim = page.evaluate("""th.x = -6; startAim(1); flash[1] = flash[2] = 0;
      const v = th.v; press(2); press(1);
      [th.phase, padOn(1), padOn(2), padOn(3), flash[1], flash[2], th.v === v, color(1), color(2), color(3)]""")
    assert aim[:7] == ["aim", False, False, True, 0, 0, True]
    assert aim[7] == OFF and aim[8] == OFF and aim[9] != OFF
    # In the air any pad is the legs, once; after that every pad is off.
    air = page.evaluate("""th.aimT = (20 - AIM0) / AIM_RATE; th.ang = 20; release();
      const a = [th.phase, padOn(1), padOn(3), color(1) !== '%s'];
      press(1); a.push(th.q !== undefined, padOn(1), padOn(3), color(1), color(3)); a""" % OFF)
    assert air == ["fly", True, True, True, True, False, False, OFF, OFF]
    assert page.errors == []
