"""Yöajo (#181): a night drive up Valtatie 4, drawn in 3D with the shared three.js."""

import pytest

from conftest import ROOT, turn

URL = "games/yoajo/v1/"

# A careful driver: keeps to the lane, overtakes only when nobody is coming, dips the high beams
# for oncoming cars and cars ahead, slows for bad road, moose and the speed limits (at most 90 on
# snow), gets out of the way of an oncoming overtaker, and stops for coffee when sleepy.
BOT = """(legs) => { maxLeg = 8; const out = [];
  for (const n of legs) { newLeg(n); HOLD = true;
    for (let i = 0; i < 60 * 400 && mode === 'drive'; i++) {
      let want = LANE;
      const slow = things.find(t => t.v >= 0 && t.lat > -1 && t.s > P.s - 3 && t.s - P.s < 50 && t.kind !== 'takaa' && t.kind !== 'hirvi' && t.kind !== 'poro');
      const onc = things.some(t => t.v < 0 && t.s > P.s - 5 && t.s - P.s < 330 && vehicle(t));
      const head = things.find(t => t.v < 0 && t.lat > 0.5 && t.s > P.s && t.s - P.s < 260);
      if (slow && !onc && slow.kind !== 'kavelija') want = -LANE;
      if (slow && slow.kind === 'kavelija' && !onc) want = slow.lat > 0 ? 0 : LANE;
      const beside = things.find(t => t.v >= 0 && vehicle(t) && t.kind !== 'takaa' && t.lat > 0 && t.s - P.s > -7 && t.s - P.s < 7);
      if (beside && P.lat < 0.5) want = -LANE;
      if (head) want = 4.0;
      const deer = things.find(t => (t.kind === 'hirvi' || t.kind === 'poro') && t.s > P.s && t.s - P.s < 120 && Math.abs(t.lat) < 6);
      const bay = road.bays.find(b => P.s > b.s0 - 5 && P.s < b.s1 - 10);
      const rest = bay && P.tired > 0.15;
      if (rest) want = 7;
      const err = P.lat - want + (P.vl - curveAt(P.s) * P.v * P.v * 0.55) * 0.35;
      input.left = err > 0.15; input.right = err < -0.15;
      const holey = road.holes.some(h => h.s > P.s - 3 && h.s - P.s < 70);
      const lim = holey ? 45 : Math.min(limitAt(P.s + 40), limitAt(P.s), (leg.weather === 'lumi' || leg.weather === 'pyry') ? 90 : 200);
      input.brake = P.v * 3.6 > lim + 3 || (deer && P.v > 4) || (rest && P.v > 2) || (head && P.v > 12)
        || (slow && want === LANE && slow.kind !== 'kavelija' && P.v > slow.v - 0.5 && slow.s - P.s < 35);
      P.high = !things.some(t => t.v < 0 && vehicle(t) && t.s > P.s && t.s - P.s < 320) && !things.some(t => t.v > 0 && vehicle(t) && t.s > P.s && t.s - P.s < 70);
      step(1 / 60);
    }
    out.push({ n, mode, why: crashWhy, T, par: parTime(), points, tally: Object.assign({}, tally), stars: result && result.stars });
  }
  return out; }"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    return page


def drive(page, setup, secs=1.0):
    """Starts leg 1 (or the one setup picks), holds the clock, sets the moment, runs it secs."""
    return page.evaluate(f"""() => {{ HOLD = true; maxLeg = 8; newLeg(1); things = []; events = [];
      {setup};
      for (let i = 0; i < 60 * {secs} && mode === 'drive'; i++) step(1 / 60);
      return {{ mode, why: crashWhy, points, tally: Object.assign({{}}, tally), msgs: msgs.map(m => m.text) }}; }}""")


def test_every_leg_can_be_driven_to_the_town(site, context):
    page = open_game(site, context)
    legs = page.evaluate(BOT, list(range(1, 9)))
    for r in legs:
        assert r["mode"] == "done", r
        # Within the target time, without fines or dazzling anyone: all three stars are possible.
        assert r["stars"] >= 2 or r["T"] < r["par"] * 1.15, r
    # Each leg with a rest area was driven with a coffee break.
    assert all(r["tally"]["tauko"] == 1 for r in legs if r["n"] >= 3)
    assert page.errors == []


def test_doing_nothing_ends_in_the_ditch(site, context):
    page = open_game(site, context)
    r = drive(page, "", 60)
    assert r["mode"] == "crash" and "ojaan" in r["why"]


def test_dipping_for_an_oncoming_car_scores_and_dazzling_it_costs(site, context):
    page = open_game(site, context)
    # High beams on, a car comes over the hill; dipped while it is still far: points.
    r = drive(page, "P.lat = LANE; P.high = true; P.v = 20; add('vastaan', { s: P.s + 500, lat: -LANE, v: -25 });"
                    "for (let i = 0; i < 60 * 3; i++) step(1 / 60); P.high = false;", 4)
    assert r["tally"]["valot"] == 1 and r["tally"]["haikaisyt"] == 0 and r["points"] == 20, r
    # Kept on: the other driver is dazzled and flashes back.
    r = drive(page, "P.high = true; P.v = 20; add('vastaan', { s: P.s + 500, lat: -LANE, v: -25 });", 9)
    assert r["tally"]["haikaisyt"] == 1 and r["points"] == -30, r
    assert "Häikäisit vastaantulijaa -30" in r["msgs"]
    # Dazzling the car ahead through its mirrors costs too.
    r = drive(page, "P.high = true; P.v = 20; add('auto', { s: P.s + 40, v: 20 });", 3)
    assert r["tally"]["haikaisyt"] == 1, r


def test_an_overtake_scores_and_a_close_pass_of_a_walker_costs(site, context):
    page = open_game(site, context)
    r = drive(page, "P.v = 25; add('traktori', { s: P.s + 12, lat: 2.4, v: 7 }); P.lat = -LANE;", 3)
    assert r["mode"] == "drive" and r["tally"]["ohitukset"] == 1 and r["points"] == 40, r
    r = drive(page, "P.v = 25; P.lat = 2.4; add('kavelija', { s: P.s + 20, lat: 4.1, v: 1.3, reflector: true });", 2)
    assert r["mode"] == "drive" and r["tally"]["lahelta"] == 1, r
    r = drive(page, "P.v = 25; P.lat = 0; add('kavelija', { s: P.s + 20, lat: 4.1, v: 1.3, reflector: true });", 2)
    assert r["tally"]["lahelta"] == 0 and r["points"] == 20, r


def test_a_speed_camera_fines_only_speeding(site, context):
    page = open_game(site, context)
    r = drive(page, "road.cams.push({ s: P.s + 20, done: false }); P.v = 120 / KMH;", 0.7)
    assert r["tally"]["sakot"] == 1 and r["points"] == -150 and page.evaluate("flash > 0"), r
    r = drive(page, "road.cams.push({ s: P.s + 20, done: false }); P.v = limitAt(P.s + 20) / KMH; input.brake = false;", 1)
    assert r["tally"]["sakot"] == 0 and r["points"] == 25, r


def test_a_moose_on_the_road_must_be_braked_for(site, context):
    page = open_game(site, context)
    r = drive(page, "P.v = 25; add('hirvi', { s: P.s + 60, lat: LANE, dir: 1, walk: 0, stop: false, wait: 0 });", 4)
    assert r["mode"] == "crash" and r["why"] == "Törmäsit hirveen.", r
    r = drive(page, "P.v = 25; add('hirvi', { s: P.s + 60, lat: LANE, dir: 1, walk: 0, stop: false, wait: 0 }); input.brake = true;", 4)
    assert r["mode"] == "drive", r


def test_potholes_at_speed_burst_a_tyre(site, context):
    page = open_game(site, context)
    holes = "for (let k = 1; k <= 6; k++) for (const d of [-0.75, 0.75]) road.holes.push({ s: P.s + k * GAP, lat: LANE + d, r: 0.6 });"
    r = drive(page, "P.v = 28; P.lat = LANE; " + holes.replace("GAP", "12"), 3)
    assert r["mode"] == "crash" and "Rengas" in r["why"], r
    # Slowly through them, nothing happens.
    r = drive(page, "P.v = 8; P.lat = LANE; " + holes.replace("GAP", "3"), 2.5)
    assert r["mode"] == "drive" and r["tally"]["kuopat"] == 0, r


def test_a_sleepy_driver_falls_asleep_without_coffee(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(3); things = []; events = [];
      // Steered by hand down the middle of the lane, never stopping (and no potholes).
      road.holes = [];
      for (let i = 0; i < 60 * 400 && mode === 'drive'; i++) { P.lat = LANE; P.vl = 0; step(1 / 60); }
      return { mode, why: crashWhy, s: P.s, bay: road.bays[0].s1, len: leg.len }; }""")
    assert r["mode"] == "crash" and r["why"] == "Nukahdit rattiin.", r
    # Asleep after the rest area, before the town: there was a chance to stop.
    assert r["bay"] < r["s"] < r["len"], r
    # Stopping at the rest area wakes the driver.
    r = page.evaluate("""() => { HOLD = true; newLeg(3); things = []; events = [];
      const b = road.bays[0]; P.s = b.s0 + 5; P.tired = 0.7; P.lat = 7; P.v = 2;
      for (let i = 0; i < 60 * 3; i++) step(1 / 60);
      return { mode, tired: P.tired, tauko: tally.tauko }; }""")
    assert r == {"mode": "drive", "tired": pytest.approx(0, abs=0.01), "tauko": 1}


def test_a_finished_leg_is_saved_and_opens_the_next(site, context):
    page = open_game(site, context)
    assert page.evaluate("[maxLeg, level]") == [1, 1]
    r = page.evaluate("""() => { HOLD = true; newLeg(1); things = []; events = []; P.s = leg.len - 0.1; P.v = 25; T = 50; points = 100; step(1 / 60);
      return { mode, stars: result.stars }; }""")
    assert r == {"mode": "done", "stars": 3}
    page.reload()
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    assert page.evaluate("[maxLeg, stars[1], bests[1] > 100, level]") == [2, 3, True, 2]
    assert page.errors == []


def test_the_buttons_drive_the_car(site, context):
    page = open_game(site, context)

    def centre(id_):
        return page.evaluate(f"(() => {{ draw(); const b = btns.find(b => b.id === '{id_}'); return [b.x + b.w / 2, b.y + b.h / 2]; }})()")

    page.touchscreen.tap(*centre("aja"))
    page.wait_for_function("mode === 'drive'")
    page.evaluate("HOLD = true")
    page.touchscreen.tap(*centre("lights"))
    assert page.evaluate("P.high") is True
    # Holding the left button steers left; lifting the finger stops it.
    x, y = centre("left")
    cdp = page.context.new_cdp_session(page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]})
    page.wait_for_function("input.left === true")
    lat = page.evaluate("P.lat")
    page.evaluate("for (let i = 0; i < 30; i++) step(1 / 60)")
    assert page.evaluate("P.lat") < lat - 0.3
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    page.wait_for_function("input.left === false")
    page.touchscreen.tap(*centre("pause"))
    assert page.evaluate("mode") == "pause"
    assert page.errors == []


@pytest.mark.parametrize("size", [{"width": 360, "height": 640}, {"width": 740, "height": 360}])
def test_every_button_fits_on_the_screen(site, context, size):
    page = open_game(site, context)
    turn(page, size)
    page.wait_for_function(f"W === {size['width']} && H === {size['height']}")
    for setup in ["preview(1)", "newLeg(1)", "newLeg(1); P.s = leg.len; step(1 / 60)", "newLeg(1); crash('Kolari!')"]:
        boxes = page.evaluate(f"() => {{ HOLD = true; maxLeg = 8; {setup}; draw(); return btns.map(b => [b.id, b.x, b.y, b.w, b.h]); }}")
        assert boxes, setup
        for id_, bx, by, bw, bh in boxes:
            assert bx >= 0 and by >= 0 and bx + bw <= size["width"] + 0.5 and by + bh <= size["height"] + 0.5, (setup, id_)
        # No two buttons overlap.
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                assert a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1] or a[2] + a[4] <= b[2] or b[2] + b[4] <= a[2], (setup, a, b)


def test_the_night_is_drawn_in_3d(site, context):
    page = open_game(site, context)
    page.wait_for_function("!!V3 || no3d", timeout=15000)
    if page.evaluate("no3d"):
        pytest.skip("this Chromium has no WebGL")
    page.evaluate("HOLD = true; maxLeg = 8; newLeg(7); things = []; events = []; add('vastaan', { s: P.s + 80, lat: -LANE, v: -25 }); add('hirvi', { s: P.s + 40, lat: 6, dir: -1, walk: 2, stop: false, wait: 0 }); draw3d(); draw()")
    r = page.evaluate("""() => ({ world: V3.built === road, cars: V3.meshes.size, snow: !!V3.weather && V3.weather.userData.snow,
      beam: V3.beam.intensity > 0, other: V3.other.intensity > 0 })""")
    assert r == {"world": True, "cars": 2, "snow": True, "beam": True, "other": True}
    assert page.errors == []
