"""Kirkkis v6: four maps to pick from, and running is heard (#109)."""

import shutil

import pytest

from conftest import ROOT
from test_kirkkis_v3 import phones  # noqa: F401 (a fixture)

URL = "games/kirkkis/v6/"
RUN = "s => { for (let i = 0; i < s * 30; i++) step(1 / 30); }"
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


def inside(page, selector):
    """Every element matching `selector` is visible and wholly on the screen."""
    vw, vh = page.evaluate("[innerWidth, innerHeight]")
    loc = page.locator(selector)
    assert loc.count()
    for i in range(loc.count()):
        b = loc.nth(i).bounding_box()
        assert b is not None, selector
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= vw and b["y"] + b["height"] <= vh, (selector, b)


@pytest.mark.parametrize("name", MAPS)
def test_every_map_plays_whole_rounds_alone(site, browser, name):
    ctx, page = open_game(site, browser)
    page.click(f"#maps button[data-map={name}]")
    r = page.evaluate("""() => ({ map: mapId, spots: SPOTS.length, bushes: SPOTS.filter(s => s.bush).length,
      // every hiding place a computer hider may pick can be walked to from the base
      lost: SPOTS.filter(s => dist(s, BASE) < 19 && dist(findPath(BASE, s).at(-1) || BASE, s) > 0.6).length,
      free: walkable(BASE.x + 1.1, BASE.y) })""")
    assert r["map"] == name and r["spots"] > 40 and r["bushes"] > 5 and r["lost"] == 0 and r["free"]
    rounds = page.evaluate("""() => { const out = [];
      for (let r = 0; r < 4; r++) {
        newRound(r % 2 ? 'seek' : 'hide'); let t = 0;
        while (phase !== 'menu' && t < 260) { step(1 / 30); t += 1 / 30; }
        out.push({ menu: phase === 'menu', map: mapId, next: !!nextSeeker });
      } return out; }""")
    assert all(x["menu"] and x["map"] == name and x["next"] for x in rounds)
    assert page.errors == []
    ctx.close()


def test_the_map_is_kept_on_the_phone_and_old_saves_still_read(site, browser):
    old = "localStorage.setItem('ai-pelit:kirkkis:tilasto', JSON.stringify({ kierrokset: 3, pelastuit: 2, kirkattiin: 1, kirkkasit: 4 }))"
    ctx, page = open_game(site, browser, init=old)
    assert page.locator("#total").inner_text() == "Kierroksia 3 · pelastuit 2 · nimesit 4"
    # A phone that played v5 starts on the old yard.
    assert page.evaluate("mapId") == "piha"
    assert page.locator("#maps button.on").inner_text().split() == ["🏡", "Piha"]
    page.click("#maps button[data-map=metsa]")
    page.reload()
    assert page.evaluate("[mapId, WW, WH]") == ["metsa", 34, 48]
    assert page.locator("#maps button.on").inner_text().split() == ["🌲", "Metsä"]
    page.click("#hide")
    page.evaluate(RUN, 3)
    assert page.evaluate("phase") == "count" and page.evaluate("mapId") == "metsa"
    assert page.errors == []
    ctx.close()


# The player seeks on the old yard, and a hider is behind the shed's corner, out of sight, 5 m away.
BEHIND_SHED = """() => { newRound('seek'); for (let i = 0; i < 10.2 * 30; i++) step(1 / 30);
  const h = bots[0]; for (const b of bots) { b.x = 28; b.y = 42; b.goal = b.spot = { x: 28, y: 42 }; b.path = []; b.brave = 999; }
  player.x = 10.5; player.y = 36; player.a = 0; h.x = 6; h.y = 40.5; h.goal = h.spot = { x: 6, y: 40.5 };
  return [phase, canSee(player, h), dist(player, h)]; }"""


def test_running_is_heard_through_walls_and_sneaking_is_not(site, browser):
    ctx, page = open_game(site, browser)
    phase, sees, d = page.evaluate(BEHIND_SHED)
    assert phase == "seek" and not sees and d < 7
    # Sneaking past: nothing.
    page.evaluate("bots[0].moving = 2; step(1 / 30); bots[0].moving = 2; step(1 / 30)")
    assert page.evaluate("prints.length") == 0
    # Running: footprints where the steps were.
    page.evaluate("() => { const h = bots[0]; h.path = [{ x: 6, y: 44 }]; h.goal = null; h.run = true; for (let i = 0; i < 6; i++) step(1 / 30); }")
    assert page.evaluate("prints.length") > 0
    assert page.evaluate("Math.hypot(prints[0].x - 6, prints[0].y - 40.5)") < 1.5
    # Once the steps stop, the footprints fade.
    page.evaluate("() => { const h = bots[0]; h.run = false; h.x = h.spot.x = 28; h.y = h.spot.y = 42; h.goal = h.spot; h.path = []; }")
    page.evaluate(RUN, 1.5)
    assert page.evaluate("prints.length") == 0
    assert page.errors == []
    ctx.close()


def test_the_computer_seeker_goes_to_look_where_it_heard_running(site, browser):
    ctx, page = open_game(site, browser)
    i = page.evaluate("""() => { newRound('hide'); for (let i = 0; i < 10.2 * 30; i++) step(1 / 30);
      player.x = 28; player.y = 42; player.st = 'saved';
      const h = bots.find(b => b !== seeker); for (const b of bots) if (b !== seeker && b !== h) { b.st = 'saved'; }
      seeker.x = 10.5; seeker.y = 36; seeker.a = 0; seeker.goal = { x: 12, y: 30 }; seeker.path = []; seeker.look = 0;
      h.x = 6; h.y = 40.5; h.st = 'hiding'; h.left = true; h.run = true; h.moving = 3.7; h.goal = BASE; h.path = [];
      return people.indexOf(h); }""")
    assert not page.evaluate(f"canSee(seeker, people[{i}])")
    page.evaluate("seekerBot(seeker, 1 / 30)")
    g = page.evaluate("seeker.goal")
    assert g is not None and abs(g["x"] - 6) < 1 and abs(g["y"] - 40.5) < 1
    assert page.errors == []
    ctx.close()


@pytest.mark.parametrize("width,height", [(360, 640), (740, 360), (640, 360)])
def test_the_menu_with_the_maps_fits_upright_and_sideways(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    page.evaluate("stats.kierrokset = 12; newRound('hide'); played = true; nextSeeker = bots[1]; showMenu()")
    for sel in ["#menu h1", "#hide", "#seek", "#maps button", "#multi", "#result", "#info", "#total"]:
        inside(page, sel)
    assert page.evaluate("menu.scrollHeight <= menu.clientHeight && menu.scrollWidth <= menu.clientWidth")
    for name in MAPS:
        page.click(f"#maps button[data-map={name}]", trial=True)  # nothing covers them
    assert page.errors == []
    ctx.close()


def test_with_friends_the_host_picks_the_map_and_every_phone_plays_it(phones):  # noqa: F811
    host = phones("Eero", URL)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest = phones("Aino", URL)
    guest.click("#multi")
    guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    guest.click("#aipr-joinBtn")
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length > 1")
    assert guest.locator("#aipr-extra").inner_text() == "Huoneen tekijä valitsee kentän."
    host.click("#aipr-extra button[data-map=kirkko]")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    guest.wait_for_function("phase === 'count' && people.length === 5")
    assert host.evaluate("mapId") == "kirkko" and guest.evaluate("[mapId, WW, BASE.y]") == ["kirkko", 36, 30]
    # Alone again, the guest's own map is back.
    assert guest.evaluate("soloMap") == "piha"
    assert host.errors == [] and guest.errors == []
