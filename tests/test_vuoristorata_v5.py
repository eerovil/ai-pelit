"""Vuoristorata v5 (#459): an automatic ride scored by one hands-up hold control."""

import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/vuoristorata/v5/"
KEY = "ai-pelit:vuoristorata:"


def build(site):
    shutil.copytree(ROOT / "games" / "vuoristorata", site.games / "vuoristorata")
    site.build()


def open_page(site, browser, saves=None, viewport=None, name=None, relay=None):
    if not (site.games / "vuoristorata").exists():
        build(site)
    ctx = browser.new_context(viewport=viewport or {"width": 360, "height": 740}, is_mobile=True,
                              has_touch=True, service_workers="block")
    for save_name, value in (saves or {}).items():
        ctx.add_init_script(f"localStorage.setItem({json.dumps(KEY + save_name)}, {json.dumps(json.dumps(value))})")
    if name:
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    if relay:
        relay.attach(page)
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=20000)
    return ctx, page


def start(page):
    page.click("#aja")
    page.wait_for_function("game.mode === 'ride'", timeout=8000)


def finish_fast(page):
    page.evaluate("""() => {
      for (let n = 0; n < 120000 && game.mode === 'ride'; n++) step(1 / 120);
    }""")
    page.wait_for_function("game.mode === 'done'", timeout=5000)


def test_menu_has_one_control_and_explains_the_ride(site, browser):
    ctx, page = open_page(site, browser)
    try:
        assert "Juna ajaa itse" in page.locator("#menu .help").inner_text()
        assert page.locator("#aja").inner_text() == "Kyytiin!"
        start(page)
        assert page.locator("#kadet").is_visible()
        assert page.locator("#jarru").count() == 0
        assert page.locator("#vauhti").count() == 0
        assert page.errors == []
    finally:
        ctx.close()


def test_no_input_finishes_without_a_crash_and_unlocks_the_next_level(site, browser):
    ctx, page = open_page(site, browser)
    try:
        start(page)
        finish_fast(page)
        assert page.evaluate("game.result.score") == 0
        assert page.evaluate("game.result.stars") == 1
        assert page.locator("#aika").inner_text() == "0 p"
        assert page.evaluate(f"JSON.parse(localStorage.getItem({json.dumps(KEY + 'taso')}))") == 2
        page.click("#uudestaan")
        page.wait_for_function("game.mode === 'ride'", timeout=8000)
        assert page.evaluate("game.car.score") == 0
        assert page.evaluate("game.car.thrillIndex") == 0
        assert page.errors == []
    finally:
        ctx.close()


def test_a_fresh_press_scores_timing_and_the_held_part(site, browser):
    ctx, page = open_page(site, browser)
    try:
        start(page)
        page.evaluate("""() => {
          const z = game.track.thrills[0];
          game.car.s = z.s0 - game.car.v * 0.05;
          game.car.ready = true;
        }""")
        page.locator("#kadet").dispatch_event("pointerdown", {"pointerId": 7, "pointerType": "touch"})
        page.evaluate("""() => {
          const z = game.track.thrills[0];
          for (let n = 0; n < 20000 && game.car.s <= z.s1 + 1; n++) step(1 / 120);
        }""")
        page.locator("#kadet").dispatch_event("pointerup", {"pointerId": 7, "pointerType": "touch"})
        points = page.evaluate("game.car.thrillStates[0].points")
        assert points >= 80
        assert page.evaluate("game.car.score") == points
        assert page.errors == []
    finally:
        ctx.close()


def test_holding_before_the_prompt_does_not_claim_a_section(site, browser):
    ctx, page = open_page(site, browser)
    try:
        page.click("#aja")
        page.locator("#kadet").dispatch_event("pointerdown", {"pointerId": 8, "pointerType": "touch"})
        page.wait_for_function("game.mode === 'ride'", timeout=8000)
        page.evaluate("""() => {
          const z = game.track.thrills[0];
          for (let n = 0; n < 30000 && game.car.s <= z.s1 + 1; n++) step(1 / 120);
        }""")
        assert page.evaluate("game.car.thrillStates[0].claimed") is False
        assert page.evaluate("game.car.score") == 0
        assert page.errors == []
    finally:
        ctx.close()


def test_old_progress_and_times_survive_while_points_are_new(site, browser):
    saves = {"taso": 4, "valittu": 3, "ajat": {"3": 71.4}, "pisteet": {"3": 420}, "tahdet": {"3": 2}}
    ctx, page = open_page(site, browser, saves=saves)
    try:
        assert page.locator("#taso").inner_text() == "Taso 3"
        assert "420 p" in page.locator("#ennatys").inner_text()
        assert page.evaluate(f"JSON.parse(localStorage.getItem({json.dumps(KEY + 'ajat')}))['3']") == 71.4
        assert page.errors == []
    finally:
        ctx.close()


def test_generated_levels_have_scoring_sections_and_finish_automatically(site, browser):
    ctx, page = open_page(site, browser)
    try:
        results = page.evaluate("""() => {
          const out = [];
          for (let level = 1; level <= 20; level++) {
            const tr = makeLevel(level), car = newCar();
            for (let n = 0; n < 120000 && car.fin === null; n++) autoStep(tr, car, 1 / 120);
            out.push([tr.thrills.length, tr.maxScore, car.fin, car.s, tr.finish]);
          }
          return out;
        }""")
        assert all(n >= 1 and maximum == n * 100 for n, maximum, *_ in results)
        assert all(fin is not None and pos >= finish for _, _, fin, pos, finish in results)
        assert page.errors == []
    finally:
        ctx.close()


def test_the_control_and_result_fit_sideways(site, browser):
    ctx, page = open_page(site, browser, viewport={"width": 740, "height": 360})
    try:
        start(page)
        button = page.locator("#kadet").bounding_box()
        assert button and button["x"] >= 0 and button["x"] + button["width"] <= 740
        assert button["y"] >= 0 and button["y"] + button["height"] <= 360
        finish_fast(page)
        assert page.locator("#loppu").evaluate("e => e.scrollHeight <= e.clientHeight")
        assert page.errors == []
    finally:
        ctx.close()


def room_of(site, browser, names):
    build(site)
    relay = Relay()
    pages, contexts = [], []
    for player_name in names:
        ctx, page = open_page(site, browser, name=player_name, relay=relay)
        contexts.append(ctx)
        pages.append(page)
    host, guests = pages[0], pages[1:]
    host.click("#kaverit")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost")
    code = host.evaluate("AiPelitRooms.code")
    for guest in guests:
        guest.click("#kaverit")
        guest.fill("#aipr-codeIn", code)
        guest.click("#aipr-joinBtn")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
    return host, guests, contexts


@pytest.mark.alone
def test_friends_compare_points_and_equal_points_share_a_place(site, browser):
    host, guests, contexts = room_of(site, browser, ["Eero", "Aino", "Ville"])
    try:
        host.click("#aipr-start")
        for page in [host, *guests]:
            page.wait_for_function("net && net.cfg && game.mode === 'ride'", timeout=10000)
        for page, score in zip([host, *guests], [120, 240, 240]):
            page.evaluate("score => { game.car.score = score; game.car.s = game.track.finish - 2; }", score)
        for page in [host, *guests]:
            page.wait_for_selector("#loppu:not(.hidden)", timeout=20000)
        assert host.locator("#loppu-otsikko").inner_text() == "3. sija"
        assert guests[0].locator("#loppu-otsikko").inner_text() == "Voitit kisan!"
        assert guests[1].locator("#loppu-otsikko").inner_text() == "Voitit kisan!"
        assert "240 p" in host.locator("#tulokset").inner_text()
        assert all(page.errors == [] for page in [host, *guests])
    finally:
        for ctx in contexts:
            ctx.close()


# #337 and #355: no crowd noise, and the shared sounds Eero found loud stay soft.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: E402,F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/vuoristorata/v5")
