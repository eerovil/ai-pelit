"""Vuoristorata v2 (#234): recorded sounds from the shared library public/lib/aanet-2/."""

import json

import test_vuoristorata as v1

URL = "games/vuoristorata/v2/"
NAMES = ["valinta", "onnistui", "rullaus", "ketju", "nousu", "voitto", "kolari", "kirkuna", "jarru"]

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


def open_page(site, browser, saves=None, no_sound_files=False):
    v1.build(site)
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    if no_sound_files:
        ctx.route("**/*.mp3", lambda route: route.abort())
    for k, v in (saves or {}).items():
        ctx.add_init_script(f"localStorage.setItem({json.dumps(v1.KEY + k)}, {json.dumps(json.dumps(v))})")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=20000)
    page.evaluate(SPY)
    return ctx, page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def riding(page):
    # The first tap turns sound on; then wait until every sound is loaded and plays.
    page.click("#aja")
    page.wait_for_function(f"{json.dumps(NAMES)}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.wait_for_function("game.mode === 'ride'", timeout=8000)
    played(page)


def test_the_count_down_and_the_start_sound(site, browser):
    ctx, page = open_page(site, browser)
    try:
        riding(page)
        page.evaluate("game.mode = 'count'; game.count = 1.01; step(0.02)")
        assert played(page) == ["valinta"]
        page.evaluate("game.count = 0.001; step(0.01)")
        assert played(page) == ["onnistui"]
        assert page.errors == []
    finally:
        ctx.close()


def test_the_chain_clanks_on_the_lift_and_the_wheels_rumble_by_speed(site, browser):
    ctx, page = open_page(site, browser)
    try:
        riding(page)
        on_lift = page.evaluate("""() => { const o = game.track.S.find(o => o.kind === 'lift');
            game.car.s = o.s + 1; game.car.v = 7; sound(game.car); return [chainL.vol, rumble.vol, rumble.rate]; }""")
        assert on_lift[0] > 0
        page.wait_for_function("chainL.playing() && rumble.playing()", timeout=5000)
        slow, fast = page.evaluate("""() => { const o = game.track.S.find(o => o.kind === 'straight' && o.s > 150);
            game.car.s = o.s; game.car.v = 5; sound(game.car); const a = [chainL.vol, rumble.rate];
            game.car.v = 25; sound(game.car); return [a, [chainL.vol, rumble.rate]]; }""")
        assert slow[0] == 0 and fast[0] == 0
        assert fast[1] > slow[1]
        # The beeps stand aside while the recorded rumble plays.
        assert page.evaluate("sound(game.car); rumble.playing()")
        assert page.errors == []
    finally:
        ctx.close()


def test_riders_scream_into_a_drop_and_the_brakes_hiss(site, browser):
    ctx, page = open_page(site, browser)
    try:
        riding(page)
        page.evaluate("""() => { const o = game.track.S.find(o => o.kind === 'drop');
            game.car.s = o.s; game.car.v = 10; game.car.brake = false; sound(game.car); sound(game.car); }""")
        assert played(page) == ["kirkuna"]
        page.evaluate("game.car.brake = true; sound(game.car); sound(game.car); game.car.brake = false; sound(game.car);"
                      " game.car.brake = true; sound(game.car)")
        assert played(page) == ["jarru", "jarru"]
        assert page.errors == []
    finally:
        ctx.close()


def test_a_bolt_a_crash_and_the_finish(site, browser):
    ctx, page = open_page(site, browser)
    try:
        riding(page)
        page.evaluate("""() => { const pk = game.track.pickups[0];
            game.car.s = pk.s - 0.3; game.car.v = 2; step(1 / 60); }""")
        assert "nousu" in played(page)
        page.evaluate("crash('side')")
        assert played(page) == ["kolari"]
        assert page.evaluate("rumble.vol") == 0
        page.wait_for_function("game.mode === 'ride'", timeout=8000)
        page.evaluate("auto = true; game.car.s = game.track.finish - 30; game.car.check = game.car.s")
        page.wait_for_function("game.mode === 'done'", timeout=20000)
        assert "voitto" in played(page)
        assert page.errors == []
    finally:
        ctx.close()


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    # The sound files fail: every sound is the game's own beep, and the ride goes on.
    ctx, page = open_page(site, browser, no_sound_files=True)
    try:
        page.click("#aja")
        page.wait_for_function("game.mode === 'ride'", timeout=8000)
        page.evaluate("auto = true; game.car.s = game.track.finish - 30; game.car.check = game.car.s")
        page.wait_for_function("game.mode === 'done'", timeout=20000)
        assert played(page) == []
        assert page.evaluate("rumble.playing()") is False
        assert page.errors == []
    finally:
        ctx.close()


def test_v1_saves_are_read_as_they_are(site, browser):
    ctx, page = open_page(site, browser, saves={"taso": 4, "valittu": 3, "ajat": {"3": 71.4}, "tahdet": {"3": 2}})
    try:
        assert page.locator("#taso").inner_text() == "Taso 3"
        assert "1.11.4" in page.locator("#ennatys").inner_text()
        assert page.errors == []
    finally:
        ctx.close()


def test_two_at_once_a_restart_and_back_to_the_menu(site, browser):
    ctx, page = open_page(site, browser)
    try:
        riding(page)
        # Braking as the car goes over into a drop: both sound, once each.
        page.evaluate("""() => { const o = game.track.S.find(o => o.kind === 'drop');
            game.car.s = o.s; game.car.v = 10; game.car.brake = true; sound(game.car); sound(game.car); }""")
        assert sorted(played(page)) == ["jarru", "kirkuna"]
        # A derail quiets the rumble; once the car is back on the track it rumbles again, and the
        # next drop screams again.
        page.evaluate("game.car.brake = false; crash('air')")
        assert played(page) == ["kolari"]
        page.wait_for_function("game.mode === 'ride'", timeout=8000)
        page.evaluate("game.car.v = 15; sound(game.car)")
        assert page.evaluate("rumble.vol") > 0
        page.evaluate("""() => { const o = game.track.S.filter(o => o.kind === 'drop').at(-1);
            game.car.s = o.s; game.car.v = 10; sound(game.car); }""")
        assert played(page) == ["kirkuna"]
        # A new ride after the menu starts quiet and counts down again.
        page.evaluate("quiet(); game.mode = 'menu'")
        assert page.evaluate("[rumble.vol, chainL.vol]") == [0, 0]
        page.evaluate("startRide()")
        assert played(page) == ["valinta"]
        assert page.errors == []
    finally:
        ctx.close()
