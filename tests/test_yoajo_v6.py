"""Yöajo v6 (#235): v5 with recorded sounds from the shared library public/lib/aanet-2/ (#205)."""

from conftest import ROOT
from test_yoajo_v4 import BOT

URL = "games/yoajo/v6/"
SOUNDS = ["moottori", "sade", "naksu", "tomahdys", "kamera", "virhe", "torvi", "suhahdus", "kitka", "kolari", "lasi", "voitto"]

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

# Leg n, clock held, nobody else on the road; then setup, then secs of driving at a steady speed.
DRIVE = """([n, setup, secs]) => { HOLD = true; maxLeg = 8; newLeg(n); mode = 'drive'; things = []; events = [];
  road.cams = []; road.holes = []; P.v = 25; heard.splice(0); eval(setup);
  for (let i = 0; i < 60 * secs && mode === 'drive'; i++) { P.v = Math.max(P.v, 20); P.lat = LANE; step(1 / 60); engineSound(); }
  return mode; }"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    page.evaluate(SPY)
    return page


def sound_on(page):
    # Sound starts with the first tap; a tap on the title presses nothing.
    page.mouse.click(180, 30)
    page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('naksu', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def drive(page, setup="", secs=1, n=1):
    return page.evaluate(DRIVE, [n, setup, secs])


def test_every_leg_can_still_be_driven(site, context):
    page = open_game(site, context)
    legs = page.evaluate(BOT, list(range(1, 9)))
    assert all(r["mode"] == "done" for r in legs), [(r["n"], r["why"]) for r in legs]
    assert page.errors == []


def test_the_lights_the_menu_a_pothole_and_a_fine_sound(site, context):
    page = open_game(site, context)
    sound_on(page)
    drive(page, "toggleLights()", 0)
    assert played(page) == ["naksu"]
    drive(page, "road.holes = [{ s: P.s + 2, lat: LANE - 0.75, r: 0.4, hit: false }]")
    assert "tomahdys" in played(page)
    drive(page, "road.cams = [{ s: P.s + 2, done: false }]; P.v = 40")
    assert played(page) == ["kamera", "virhe"]
    # A tap on a menu button clicks.
    page.evaluate("mode = 'pause'; act({ id: 'jatka' })")
    assert played(page) == ["naksu"]
    assert page.errors == []


def test_a_dazzled_driver_honks_and_a_truck_whooshes_by(site, context):
    page = open_game(site, context)
    sound_on(page)
    drive(page, "P.high = true; add('vastaan', { s: P.s + 85, lat: -LANE, v: -20, high: true })", 0.2)
    assert "torvi" in played(page)
    drive(page, "add('vastaan', { s: P.s + 12, lat: -LANE, v: -22, truck: true, len: 17, wid: 2.55 })", 0.5)
    assert played(page).count("suhahdus") == 1
    assert page.evaluate("[tally.haikaisyt, mode]") == [0, "drive"]
    assert page.errors == []


def test_a_crash_screeches_crashes_and_breaks_glass_and_a_leg_ends_on_the_tune(site, context):
    page = open_game(site, context)
    sound_on(page)
    drive(page, "crash('Törmäsit hirveen.')", 0)
    assert played(page) == ["kitka", "kolari", "lasi"]
    # A walker who jumped aside is no crash: only the screech.
    drive(page, "crash('Vaaratilanne: jalankulkija joutui hyppäämään ojaan.')", 0)
    assert played(page) == ["kitka"]
    drive(page, "P.s = road.len - 5", 2)
    assert page.evaluate("mode") == "done" and "voitto" in played(page)
    assert page.errors == []


def test_the_engine_follows_the_speed_and_rain_falls_on_wet_legs(site, context):
    page = open_game(site, context)
    sound_on(page)
    page.wait_for_function("engine.playing() && rain.playing()", timeout=5000)
    drive(page, "", 0.2, 1)
    slow = page.evaluate("[engine.rate, engine.vol, rain.vol]")
    assert slow[1] > 0 and slow[2] == 0   # a dry leg: no rain
    drive(page, "P.v = 30", 0.2, 2)
    fast = page.evaluate("[engine.rate, engine.vol, rain.vol]")
    assert fast[0] > slow[0] and fast[2] > 0   # leg 2 is wet
    page.evaluate("preview(1); engineSound()")
    assert page.evaluate("[engine.vol, rain.vol]") == [0, 0]   # silent on the menu
    assert page.errors == []
