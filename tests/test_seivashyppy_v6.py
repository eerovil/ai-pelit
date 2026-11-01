"""Seiväshyppy v6: a pad that does nothing shows greyed out and does not flash (#313): the plant
until the run nears the box, the feet on the pole."""

import test_seivashyppy_v3 as v3

URL = "games/seivashyppy/v6/"
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
    old = v3.URL
    v3.URL = URL
    try:
        page = v3.open_game(site, context)
    finally:
        v3.URL = old
    page.evaluate(COLOR)
    return page


def test_the_plant_wakes_near_the_box_and_the_feet_sleep_on_the_pole(site, context):
    page = open_game(site, context)
    page.click("#go")
    # At the start the feet run and the plant is off: a press there neither plants nor flashes.
    start = page.evaluate("""ready(); flash[3] = 0; hold(1);
      [th.phase, padOn(1), padOn(2), padOn(3), flash[3], color(3), (press(1), flash[1] > 0), color(1) !== '%s']""" % OFF)
    assert start == ["ready", True, True, False, 0, OFF, True, True]
    # Near the box the plant is on; planted, the feet are off and do not flash.
    pole = page.evaluate("""th.x = PLANT_FROM + 0.1; const near = [padOn(3), color(3) !== '%s'];
      th.x = TAKEOFF; th.v = 9; hold(1); flash[1] = flash[2] = 0; press(2);
      near.concat([th.phase, padOn(1), padOn(2), padOn(3), flash[2], color(1), color(2)])""" % OFF)
    assert pole == [True, True, "pole", False, False, True, 0, OFF, OFF]
    assert page.errors == []
