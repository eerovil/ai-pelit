"""Kirkkis v7: Piilosta and Hippa beside Kirkkis, a sprint, and three ways to steer (#137)."""

import shutil

import pytest

from conftest import ROOT
from test_kirkkis_v3 import phones  # noqa: F401 (a fixture)
from test_kirkkis_v6 import inside

URL = "games/kirkkis/v7/"
RUN = "s => { for (let i = 0; i < s * 30; i++) step(1 / 30); }"
MODES = ["kirkkis", "piilosta", "hippa"]
MAPS = ["piha", "koulu", "metsa", "kirkko"]


def open_game(site, browser, width=360, height=740, init=None):
    # Only this game is built, so another game's half-made version cannot break the test.
    shutil.copytree(ROOT / "games" / "kirkkis", site.games / "kirkkis", dirs_exist_ok=True)
    site.build()
    ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
    if init:
        ctx.add_init_script(init)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    return ctx, page


@pytest.mark.parametrize("mode", MODES)
def test_every_game_plays_whole_rounds_alone_on_every_map(site, browser, mode):
    ctx, page = open_game(site, browser)
    page.click(f"#modes button[data-mode={mode}]")
    for name in MAPS:
        page.click(f"#maps button[data-map={name}]")
        rounds = page.evaluate("""() => { const out = [];
          for (let r = 0; r < 2; r++) {
            newRound(r % 2 ? 'seek' : 'hide'); let t = 0;
            while (phase !== 'menu' && t < 260) { step(1 / 30); t += 1 / 30; }
            out.push({ menu: phase === 'menu', mode, map: mapId, next: !!nextSeeker, t });
          } return out; }""")
        assert all(r["menu"] and r["mode"] == mode and r["map"] == name and r["next"] for r in rounds), rounds
    assert page.errors == []
    ctx.close()


def test_piilosta_seen_is_found_and_nobody_races_to_the_base(site, browser):
    ctx, page = open_game(site, browser)
    page.click("#modes button[data-mode=piilosta]")
    r = page.evaluate("""() => { newRound('seek'); for (let i = 0; i < 10.2 * 30; i++) step(1 / 30);
      const h = bots[0]; for (const b of bots) { b.x = 28; b.y = 42; b.goal = b.spot = { x: 28, y: 42 }; b.path = []; }
      player.x = 15; player.y = 30; player.a = Math.PI / 2; h.x = 15; h.y = 34; h.goal = h.spot = { x: 15, y: 34 };
      step(1 / 30); return [phase, h.st, firstCaught === h, timer > 100]; }""")
    assert r == ["seek", "caught", True, True]
    assert page.evaluate("bots.filter(b => b.st === 'saved').length") == 0
    assert page.errors == []
    ctx.close()


def test_hippa_a_touch_makes_it_and_there_is_no_tag_back(site, browser):
    ctx, page = open_game(site, browser)
    page.click("#modes button[data-mode=hippa]")
    r = page.evaluate("""() => { newRound('seek'); for (let i = 0; i < 3.2 * 30; i++) step(1 / 30);
      const h = bots[0]; for (const b of bots) { b.x = 28; b.y = 42; b.goal = null; b.path = []; b.ctrl = 'still'; }
      player.x = 15; player.y = 30; h.x = 15.5; h.y = 30; step(1 / 30);
      return [phase, seeker === h, player.role, h.freeze > 0, player.st]; }""")
    assert r == ["seek", True, "hider", True, "hiding"]
    # Right back: no tag back, even when still touching after the count.
    page.evaluate(RUN, 2)
    assert page.evaluate("seeker === bots[0]")
    page.evaluate("bots[0].noBack = 0; step(1 / 30)")
    assert page.evaluate("seeker === player && statsH.hippasit === 1")
    # Whoever is it at the end lost, and is it next.
    page.evaluate("timer = 0.01; step(1 / 30)")
    page.evaluate(RUN, 3)
    assert page.evaluate("[phase, nextSeeker === player, statsH.jait]") == ["menu", True, 1]
    assert page.locator("#result").inner_text() == "Jäit hipaksi! 😅"
    assert page.errors == []
    ctx.close()


def test_the_computer_it_chases_what_it_sees(site, browser):
    ctx, page = open_game(site, browser)
    page.click("#modes button[data-mode=hippa]")
    t = page.evaluate("""() => { newRound('hide'); for (let i = 0; i < 3.2 * 30; i++) step(1 / 30);
      for (const b of bots) if (b !== seeker) { b.x = 28; b.y = 42; b.ctrl = 'still'; }
      player.x = 15; player.y = 30; seeker.x = 15; seeker.y = 34; seeker.a = -Math.PI / 2; seeker.freeze = 0;
      let t = 0; while (seeker !== player && t < 5) { step(1 / 30); t += 1 / 30; } return t; }""")
    assert t < 3
    assert page.errors == []
    ctx.close()


def test_a_far_push_sprints_runs_out_of_breath_and_it_comes_back(site, browser):
    ctx, page = open_game(site, browser)
    page.click("#hide")
    # A short push walks, a push past the outer ring sprints.
    page.evaluate("() => { joy = { id: 1, ox: 60, oy: 500, x: 110, y: 500 }; player.x = 3; player.y = 20.5; step(1 / 30); }")
    assert page.evaluate("[player.moving, player.spr]") == [4, False]
    page.evaluate("() => { joy.x = 160; for (let i = 0; i < 15; i++) step(1 / 30); }")
    assert page.evaluate("player.moving") == pytest.approx(6.0, abs=0.01)
    page.evaluate(RUN, 3.5)
    assert page.evaluate("[player.winded, player.moving]") == [True, 4]
    page.evaluate("letGo()")
    page.evaluate(RUN, 2)
    assert page.evaluate("player.winded") is False
    assert page.errors == []
    ctx.close()


def test_two_thumbs_walk_one_way_and_look_another(site, browser):
    ctx, page = open_game(site, browser)
    page.click("#hide")
    box = page.evaluate("[innerWidth, innerHeight]")
    page.evaluate(RUN, 0.5)
    # Real touches: the left thumb walks right, the right thumb looks up.
    page.evaluate(f"""() => {{
      const ev = (t, id, x, y) => c.dispatchEvent(new PointerEvent(t, {{ pointerId: id, clientX: x, clientY: y, bubbles: true }}));
      c.setPointerCapture = () => {{}};
      ev('pointerdown', 1, 80, {box[1] - 150}); ev('pointermove', 1, 140, {box[1] - 150});
      ev('pointerdown', 2, {box[0] - 80}, {box[1] - 150}); ev('pointermove', 2, {box[0] - 80}, {box[1] - 220});
    }}""")
    x0 = page.evaluate("player.x")
    page.evaluate(RUN, 1)
    r = page.evaluate("[player.x, player.a]")
    assert r[0] > x0 + 2 and abs(r[1] + 1.5708) < 0.1
    # Letting go of the eyes: the eyes turn the way one walks again.
    page.evaluate("() => c.dispatchEvent(new PointerEvent('pointerup', { pointerId: 2, bubbles: true }))")
    page.evaluate(RUN, 0.5)
    assert abs(page.evaluate("player.a")) < 0.1
    assert page.errors == []
    ctx.close()


def test_sight_has_no_length_and_the_screen_shows_more_ahead(site, browser):
    for w, h in [(360, 740), (740, 360)]:
        ctx, page = open_game(site, browser, w, h)
        page.click("#hide")
        page.evaluate(RUN, 11)
        # Across the open middle of the school yard, 20 m off: seen (v1–v6 saw 10 m).
        r = page.evaluate("""() => { const o = bots.find(b => b !== seeker && b !== player);
          player.x = 15; player.y = 22; player.a = Math.PI / 2; o.x = 15; o.y = 42.5; o.ctrl = 'still';
          return [clearSight(player, o), canSee(player, o)]; }""")
        assert r[0] == r[1]
        page.evaluate("() => { loadMap('koulu'); }")
        r = page.evaluate("""() => { const o = bots.find(b => b !== seeker && b !== player);
          player.x = 26.5; player.y = 29.5; player.a = Math.PI / 2; o.x = 26.5; o.y = 37.5 + 0; return dist(player, o) > 7 && canSee(player, o); }""")
        assert r
        # Wherever the player looks, most of the screen is ahead (unless the yard fits across), and the player stays on it.
        out = page.evaluate("""() => { loadMap('piha'); const o = []; player.x = 15; player.y = 22;
          for (let k = 0; k < 8; k++) { player.a = k * Math.PI / 4; for (let i = 0; i < 40; i++) draw();
            const px = sx(player.x), py = sy(player.y);
            o.push(px > 40 && px < innerWidth - 40 && py > 40 && py < innerHeight - 40
              && (Math.cos(player.a) * (innerWidth / 2 - px) + Math.sin(player.a) * (innerHeight / 2 - py)) >= -1); } return o; }""")
        assert all(out), out
        assert page.errors == []
        ctx.close()


def test_side_vision_shows_only_someone_moving_and_the_seeker_goes_to_look(site, browser):
    ctx, page = open_game(site, browser)
    r = page.evaluate("""() => { newRound('hide'); for (let i = 0; i < 10.2 * 30; i++) step(1 / 30);
      player.x = 28; player.y = 42; player.st = 'saved';
      const h = bots.find(b => b !== seeker); for (const b of bots) if (b !== seeker && b !== h) b.st = 'saved';
      // On the open yard, 9 m off to the seeker's side: too wide for the sharp view.
      const look = () => { seeker.x = 15; seeker.y = 28; seeker.a = 0; seeker.look = 0; seeker.goal = { x: 16, y: 28 }; seeker.path = []; seeker.heardT = -99; };
      look(); h.x = 19; h.y = 36; h.st = 'hiding'; h.moving = 0;
      const still = [canSee(seeker, h), glimpses(seeker, h)];
      h.moving = 2;
      const moving = [canSee(seeker, h), glimpses(seeker, h)];
      seekerBot(seeker, 1 / 30); const sneak = seeker.goal;
      look(); h.moving = 3.7; seekerBot(seeker, 1 / 30);
      return [still, moving, sneak, seeker.goal]; }""")
    assert r[0] == [False, False] and r[1] == [False, True]
    assert r[2]["x"] == 16  # sneaking at the side of its eye goes unnoticed
    assert abs(r[3]["x"] - 19) < 1 and abs(r[3]["y"] - 36) < 1  # running does not
    assert page.errors == []
    ctx.close()


def test_far_off_the_seeker_cannot_tell_who_it_is(site, browser):
    ctx, page = open_game(site, browser)
    r = page.evaluate("""() => { newRound('seek'); for (let i = 0; i < 10.2 * 30; i++) step(1 / 30);
      for (const b of bots) { b.ctrl = 'still'; b.x = 28; b.y = 42; }
      const h = bots[0]; player.x = 15; player.y = 25; player.a = Math.PI / 2; h.x = 15; h.y = 39;
      step(1 / 30); const far = [canSee(player, h), h.st, unknown(h)];
      player.y = 30; step(1 / 30); return [far, h.st, unknown(h)]; }""")
    assert r == [[True, "hiding", True], "spotted", False]
    assert page.errors == []
    ctx.close()


def test_old_saves_still_read_and_each_game_keeps_its_own_tally(site, browser):
    old = "localStorage.setItem('ai-pelit:kirkkis:tilasto', JSON.stringify({ kierrokset: 3, pelastuit: 2, kirkattiin: 1, kirkkasit: 4 }))"
    ctx, page = open_game(site, browser, init=old)
    assert page.locator("#total").inner_text() == "Kierroksia 3 · pelastuit 2 · nimesit 4"
    assert page.locator("#modes button.on").inner_text() == "⛪ Kirkkis"
    page.click("#modes button[data-mode=piilosta]")
    assert page.locator("#total").inner_text() == ""
    assert page.locator("#hide").inner_text() == "🙈 Piiloudu"
    page.click("#modes button[data-mode=hippa]")
    assert page.locator("#seek").inner_text() == "✋ Ole hippa"
    page.reload()
    assert page.evaluate("soloMode") == "hippa"
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kirkkis:tilasto')).kirkkasit") == 4
    assert page.errors == []
    ctx.close()


@pytest.mark.parametrize("width,height", [(360, 640), (390, 844), (740, 360), (844, 390), (640, 360)])
def test_the_menu_fits_upright_and_sideways(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    page.evaluate("stats.kierrokset = 12; newRound('hide'); played = true; nextSeeker = bots[1]; lastRes = ['Pelastuit! 🎉', 'win']; showMenu()")
    for sel in ["#menu h1", "#modes button", "#hide", "#seek", "#maps button", "#multi", "#result", "#info", "#total"]:
        inside(page, sel)
    assert page.evaluate("menu.scrollHeight <= menu.clientHeight && menu.scrollWidth <= menu.clientWidth")
    assert page.errors == []
    ctx.close()


def test_with_friends_the_host_picks_hippa_and_a_tag_reaches_the_guest(phones):  # noqa: F811
    host = phones("Eero", URL)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest = phones("Aino", URL)
    guest.click("#multi")
    guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    guest.click("#aipr-joinBtn")
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length > 1")
    assert guest.locator("#aipr-extra").inner_text() == "Huoneen tekijä valitsee pelin ja kentän."
    host.click("#aipr-extra button[data-mode=hippa]")
    host.click("#aipr-extra button[data-map=koulu]")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    guest.wait_for_function("phase === 'count' && people.length === 5")
    assert guest.evaluate("[mode, mapId]") == ["hippa", "koulu"]
    # The host makes the guest it; the guest's phone hears who is it.
    host.wait_for_function("phase === 'seek'")
    host.evaluate("""() => { const g = people.find(p => p.ctrl === 'remote');
      for (const b of bots) b.ctrl = 'still';
      setIt(people.find(p => p.ctrl === 'still' && p !== g)); seeker.st = 'seek'; seeker.freeze = 0; seeker.noBack = 0;
      seeker.x = g.x; seeker.y = g.y; }""")
    guest.wait_for_function("seeker === player && player.freeze > 0")
    assert host.errors == [] and guest.errors == []


def test_a_guest_back_mid_wait_after_a_tag_still_waits(phones):  # noqa: F811
    host = phones("Eero", URL)
    host.click("#modes button[data-mode=hippa]")
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest = phones("Aino", URL)
    guest.click("#multi")
    guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    guest.click("#aipr-joinBtn")
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length > 1")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    host.wait_for_function("phase === 'seek' && mode === 'hippa'")
    # The guest has just been tagged, and waits a long while (so the reload cannot outlast it).
    host.evaluate("""() => { const g = people.find(p => p.ctrl === 'remote'); for (const b of bots) b.ctrl = 'still';
      setIt(g); g.st = 'seek'; g.freeze = 60; for (const p of people) if (p !== g) p.st = 'hiding'; }""")
    guest.reload()
    guest.wait_for_function("phase === 'seek' && seeker === player && player.freeze > 30")
    # Moving anyway: the host keeps the guest where it is.
    x0 = host.evaluate("people.find(p => p.ctrl === 'remote').x")
    guest.evaluate("() => { joy = { id: 1, ox: 60, oy: 500, x: 160, y: 500 }; player.freeze = 0; }")
    guest.wait_for_timeout(600)
    assert host.evaluate("people.find(p => p.ctrl === 'remote').x") == x0
    assert host.errors == [] and guest.errors == []


@pytest.mark.parametrize("mode,guides", [("kirkkis", True), ("piilosta", False), ("hippa", False)])
def test_only_kirkkis_shows_the_way_to_the_base(site, browser, mode, guides):
    ctx, page = open_game(site, browser)
    page.click(f"#modes button[data-mode={mode}]")
    page.click("#hide")
    page.evaluate(RUN, 12)
    # Far from the base: count the arrow and the base's ring drawn in one frame.
    drawn = page.evaluate("""() => { player.x = 3; player.y = 42; let arrows = 0, rings = 0;
      const da = drawBaseArrow; drawBaseArrow = () => { arrows++; da(); };
      const arc = x.arc.bind(x); x.arc = (cx, cy, r, ...a) => { if (cx === BASE.x && cy === BASE.y && r === BASE_REACH) rings++; return arc(cx, cy, r, ...a); };
      draw(); x.arc = arc; drawBaseArrow = da; return [arrows, rings]; }""")
    assert drawn == ([1, 1] if guides else [0, 0])
    assert page.errors == []
    ctx.close()
