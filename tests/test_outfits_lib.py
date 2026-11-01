"""The shared outfit picker, public/outfits.js (#158), on a page of its own."""

import pytest

from conftest import ROOT

PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<body><script src="../outfits.js" data-game="koe"></script>
<script>
var changed = [];
AiPelitOutfits.setup({
  outfits: [{ id: 'perus', name: 'Perus', top: '#f00' }, { id: 'sini', name: 'Sininen', top: '#00f' }],
  draw: function (g, o, w, h) { g.fillStyle = o.top; g.fillRect(0, 0, w, h); if (o.head) AiPelitOutfits.head(g, o.head, w / 2, h / 3, 10, 1); },
  change: function (o) { changed.push(o.id); },
});
</script></body>"""


@pytest.fixture
def lib_page(site, browser):
    site.build()
    (site.root / "koe").mkdir(exist_ok=True)
    (site.root / "koe" / "index.html").write_text(PAGE)
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + "koe/")
    yield page, errors
    ctx.close()


def test_the_costumes_follow_the_games_own_outfits_and_the_first_is_the_default(lib_page):
    page, errors = lib_page
    ids = page.evaluate("AiPelitOutfits.list().map(o => o.id)")
    assert ids == ["perus", "sini", "kurpitsa", "noita", "haamu", "luuranko", "vampyyri", "muumio"]
    assert page.evaluate("AiPelitOutfits.current().id") == "perus"
    assert page.evaluate("AiPelitOutfits.get('noita').halloween") is True
    assert page.evaluate("AiPelitOutfits.get('ei-ole').id") == "perus"   # a friend's unknown outfit
    assert errors == []


def test_picking_saves_per_game_and_tells_the_game(lib_page):
    page, errors = lib_page
    page.evaluate("AiPelitOutfits.open()")
    page.click("[data-asu=haamu]")
    assert page.evaluate("changed") == ["haamu"]
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:koe')") == '"haamu"'
    assert page.evaluate("AiPelitOutfits.current().id") == "haamu"
    page.click("#ai-pelit-asut-valmis")
    assert page.evaluate("AiPelitOutfits.isOpen()") is False
    assert errors == []


@pytest.mark.parametrize("day,first", [("2026-10-31T12:00:00", "🎃 Halloween"), ("2026-11-02T12:00:00", "🎃 Halloween"),
                                       ("2026-06-15T12:00:00", "Tavalliset"), ("2026-11-03T12:00:00", "Tavalliset")])
def test_costumes_come_first_around_halloween_and_stay_all_year(site, browser, day, first):
    site.build()
    (site.root / "koe").mkdir(exist_ok=True)
    (site.root / "koe" / "index.html").write_text(PAGE)
    ctx = browser.new_context(viewport={"width": 360, "height": 740})
    page = ctx.new_page()
    page.clock.set_fixed_time(day)
    page.goto(site.url + "koe/")
    page.evaluate("AiPelitOutfits.open()")
    headings = page.locator("#ai-pelit-asut .asu").first.evaluate("b => b.previousElementSibling.textContent")
    assert headings == first
    assert page.locator("#ai-pelit-asut .asu").count() == 8
    ctx.close()


def test_turning_the_phone_with_the_picker_open_keeps_it_and_the_choice(lib_page):
    page, errors = lib_page
    page.evaluate("AiPelitOutfits.open()")
    page.click("[data-asu=noita]")
    page.set_viewport_size({"width": 740, "height": 360})
    page.wait_for_timeout(100)
    assert page.evaluate("AiPelitOutfits.isOpen()") is True
    # Sideways the cards are smaller, and all eight fit with the ready button on screen.
    assert page.locator("#ai-pelit-asut canvas").first.bounding_box()["height"] == 58
    assert page.locator("[data-asu=noita]").get_attribute("class") == "asu valittu"
    last = page.locator("#ai-pelit-asut .asu").last.bounding_box()
    assert last["y"] + last["height"] <= 360
    page.set_viewport_size({"width": 360, "height": 740})
    page.wait_for_timeout(100)
    assert page.locator("#ai-pelit-asut canvas").first.bounding_box()["height"] == 80
    assert page.locator("#ai-pelit-asut").count() == 1
    assert errors == []


SHARED_PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<body><script src="../outfits.js" data-game="%s" data-share="yleisurheilu"></script>
<script>AiPelitOutfits.setup({ outfits: AiPelitOutfits.yleisurheilu, draw: function () {} });</script></body>"""


def shared_page(site, browser, slug, store):
    (site.root / slug).mkdir(exist_ok=True)
    (site.root / slug / "index.html").write_text(SHARED_PAGE % slug)
    ctx = browser.new_context(viewport={"width": 360, "height": 740})
    for k, v in store.items():
        ctx.add_init_script(f"localStorage.setItem('{k}', '\"{v}\"')")
    page = ctx.new_page()
    page.goto(site.url + slug + "/")
    return page


def test_a_shared_choice_is_one_for_the_whole_group(site, browser):
    # #311: picked in one athletics event, worn in another; its own older choice only until then.
    site.build()
    page = shared_page(site, browser, "laji-a", {"ai-pelit:_asut:laji-a": "kulta"})
    assert page.evaluate("AiPelitOutfits.current().id") == "kulta"
    assert page.evaluate("AiPelitOutfits.list().filter(o => !o.halloween).map(o => o.id)") \
        == ["perus", "suomi", "musta", "punainen", "vihrea", "kulta", "neon"]
    page.evaluate("AiPelitOutfits.open()")
    page.click("[data-asu=noita]")
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:yleisurheilu')") == '"noita"'
    # Also under the game's own key, which its older versions read.
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:laji-a')") == '"noita"'
    other = shared_page(site, browser, "laji-b", {"ai-pelit:_asut:yleisurheilu": "noita", "ai-pelit:_asut:laji-b": "suomi"})
    assert other.evaluate("AiPelitOutfits.current().id") == "noita"
    page.context.close()
    other.context.close()


def test_without_data_share_the_choice_stays_the_games_own(lib_page):
    page, errors = lib_page
    page.evaluate("AiPelitOutfits.open()")
    page.click("[data-asu=sini]")
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:yleisurheilu')") is None
    assert errors == []
