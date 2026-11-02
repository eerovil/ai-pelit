"""Aitajuoksu v10: the athletics events' outfit set, one choice for every event and Ottelu (#311)."""

import json
import shutil

from conftest import ROOT

URL = "games/aitajuoksu/v12/"
SHARED = "ai-pelit:_asut:yleisurheilu"


def build(site):
    # Only this game, so another game's work in progress does not stop the build.
    if not (site.games / "aitajuoksu").exists():
        shutil.copytree(ROOT / "games" / "aitajuoksu", site.games / "aitajuoksu")
        site.build()


def open_game(site, browser, store=None):
    build(site)
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


# #337: no crowd noise; #355: on aanet-5, the sounds Eero found too loud softer.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/aitajuoksu/v12")
