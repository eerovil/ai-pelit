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
    assert ids == ["perus", "sini", "kurpitsa", "noita", "haamu", "luuranko", "vampyyri", "muumio",
                   "harry", "ron", "hermione"]
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
    assert page.locator("#ai-pelit-asut .asu").count() == 11
    ctx.close()


@pytest.mark.parametrize("day,order", [("2026-10-31T12:00:00", ["🎃 Halloween", "Tavalliset", "⚡ Tylypahka"]),
                                       ("2026-06-15T12:00:00", ["Tavalliset", "⚡ Tylypahka", "🎃 Halloween"])])
def test_harry_ron_and_hermione_have_a_group_of_their_own(site, browser, day, order):
    # #321: the Tylypahka costumes follow the game's own outfits all year, and every game gets them.
    site.build()
    (site.root / "koe").mkdir(exist_ok=True)
    (site.root / "koe" / "index.html").write_text(PAGE)
    ctx = browser.new_context(viewport={"width": 360, "height": 740})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.clock.set_fixed_time(day)
    page.goto(site.url + "koe/")
    page.evaluate("AiPelitOutfits.open()")
    headings = page.locator("#ai-pelit-asut .asu:first-of-type, #ai-pelit-asut div").all_inner_texts()
    assert [h for h in headings if h in order] == order
    school = page.evaluate("AiPelitOutfits.list().filter(o => o.tylypahka).map(o => [o.name, o.head, !!o.cape])")
    assert school == [["Harry", "harry", True], ["Ron", "ron", True], ["Hermione", "hermione", True]]
    page.click("[data-asu=hermione]")
    assert page.evaluate("AiPelitOutfits.current().id") == "hermione"
    assert errors == []
    ctx.close()


def test_the_tylypahka_heads_draw_their_own_look(lib_page):
    page, errors = lib_page
    # Each head leaves its hair colour on the canvas, Harry his glasses' black, Ron no black.
    seen = page.evaluate("""() => ['harry', 'ron', 'hermione'].map(k => {
      const c = document.createElement('canvas'); c.width = c.height = 80;
      const g = c.getContext('2d'); AiPelitOutfits.head(g, k, 40, 36, 20, 1);
      const d = g.getImageData(0, 0, 80, 80).data, cols = new Set();
      for (let i = 0; i < d.length; i += 4) if (d[i + 3] === 255) cols.add('#' + [d[i], d[i + 1], d[i + 2]].map(v => v.toString(16).padStart(2, '0')).join(''));
      return [...cols];
    })""")
    harry, ron, hermione = seen
    assert "#1d1712" in harry and "#1a1a1a" in harry and "#c0392b" in harry   # hair, glasses, scar
    assert "#d4611c" in ron and "#1a1a1a" not in ron
    assert "#6b3f1f" in hermione
    assert all("#9b1b1b" in s and "#e8b730" in s for s in seen)            # the house scarf
    assert errors == []


def test_turning_the_phone_with_the_picker_open_keeps_it_and_the_choice(lib_page):
    page, errors = lib_page
    page.evaluate("AiPelitOutfits.open()")
    page.click("[data-asu=noita]")
    page.set_viewport_size({"width": 740, "height": 360})
    page.wait_for_timeout(100)
    assert page.evaluate("AiPelitOutfits.isOpen()") is True
    # Sideways the cards are smaller, and all eleven fit with the ready button on screen.
    assert page.locator("#ai-pelit-asut canvas").first.bounding_box()["height"] == 50
    assert page.locator("[data-asu=noita]").get_attribute("class") == "asu valittu"
    last = page.locator("#ai-pelit-asut .asu").last.bounding_box()
    assert last["y"] + last["height"] <= 360
    # A smaller sideways phone too (#321: three groups).
    page.set_viewport_size({"width": 640, "height": 360})
    page.wait_for_timeout(100)
    last = page.locator("#ai-pelit-asut .asu").last.bounding_box()
    assert last["y"] + last["height"] <= 360
    page.set_viewport_size({"width": 360, "height": 740})
    page.wait_for_timeout(100)
    assert page.locator("#ai-pelit-asut canvas").first.bounding_box()["height"] == 80
    assert page.locator("#ai-pelit-asut").count() == 1
    assert errors == []
