"""Aitajuoksu v10: the athletics events' outfit set, one choice for every event and Ottelu (#311)."""

import json

import test_aitajuoksu_v5 as v5

URL = "games/aitajuoksu/v10/"
SHARED = "ai-pelit:_asut:yleisurheilu"


def open_game(site, browser, store=None):
    v5.build(site)
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    for k, v in (store or {}).items():
        ctx.add_init_script(f"localStorage.setItem({json.dumps(k)}, {json.dumps(json.dumps(v))})")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    return page


def test_picking_saves_it_for_every_event_and_the_runner_wears_it(site, browser):
    page = open_game(site, browser)
    assert page.inner_text("#asu") == "👕 Asu: Perus"
    page.click("#asu")
    assert page.locator("#ai-pelit-asut [data-asu]").count() == 16  # 7 kits, 6 Halloween, 3 Tylypahka (#321)
    page.click("[data-asu=punainen]")
    page.click("#ai-pelit-asut-valmis")
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"punainen"'
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:aitajuoksu')") == '"punainen"'
    page.click("#go")
    assert page.evaluate("me.asu") == "punainen"
    assert page.evaluate("race.runners.filter(r => r !== me).every(r => !r.asu)")
    page.evaluate("draw()")
    assert page.errors == []
    page.context.close()


def test_an_outfit_picked_in_another_event_is_worn_here(site, browser):
    page = open_game(site, browser, {SHARED: "noita", "ai-pelit:_asut:aitajuoksu": "neon"})
    assert page.inner_text("#asu") == "👕 Asu: Noita"
    page.context.close()


def test_the_games_own_older_choice_is_kept(site, browser):
    page = open_game(site, browser, {"ai-pelit:_asut:aitajuoksu": "neon"})
    assert page.inner_text("#asu") == "👕 Asu: Neon"
    page.context.close()
