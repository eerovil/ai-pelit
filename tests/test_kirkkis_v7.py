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


@pytest.mark.parametrize("ctl", ["nappi", "tyonto", "kaksi"])
def test_sprint_is_faster_runs_out_and_comes_back(site, browser, ctl):
    ctx, page = open_game(site, browser, init=f"localStorage.setItem('ai-pelit:kirkkis:ohjaus', '\"{ctl}\"')")
    page.evaluate("newRound('hide'); player.x = 3; player.y = 20.5; player.a = 0")
    W = page.evaluate("innerWidth")
    # The finger lands on the left half, and pushes far (or holds ⚡ too).
    page.evaluate(f"""() => {{ joy = {{ id: 1, ox: 60, oy: 500, x: 60 + {ctl == 'nappi' and 50 or 100}, y: 500 }};
      dash = {'{ id: 2 }' if ctl == 'nappi' else 'null'}; }}""")
    page.evaluate("() => { player.x = 3; player.y = 20.5; for (let i = 0; i < 15; i++) step(1 / 30); }")
    fast = page.evaluate("player.moving")
    assert fast == pytest.approx(6.0, abs=0.01)
    page.evaluate(RUN, 3.5)
    assert page.evaluate("[player.winded, player.moving]") == [True, 4]
    page.evaluate("letGo()")
    page.evaluate(RUN, 2)
    assert page.evaluate("player.winded") is False
    assert W == 360
    assert page.errors == []
    ctx.close()


def test_two_thumbs_walk_one_way_and_look_another(site, browser):
    ctx, page = open_game(site, browser)
    page.click("#ctl button[data-ctl=kaksi]")
    page.reload()
    assert page.evaluate("ctl") == "kaksi"
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
    for sel in ["#menu h1", "#modes button", "#hide", "#seek", "#maps button", "#ctl button", "#multi", "#result", "#info", "#total"]:
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
