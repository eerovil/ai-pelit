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
                   "joulupukki", "tonttu", "poro", "lumiukko", "piparkakku", "harry", "ron", "hermione"]
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


@pytest.mark.parametrize("day,first,cards", [("2026-10-31T12:00:00", "🎃 Halloween", 11), ("2026-11-02T12:00:00", "🎃 Halloween", 16),
                                             ("2026-06-15T12:00:00", "Tavalliset", 11), ("2026-11-03T12:00:00", "🎄 Joulu", 16),
                                             ("2026-12-24T12:00:00", "🎄 Joulu", 16), ("2027-01-01T12:00:00", "Tavalliset", 11)])
def test_costumes_come_first_around_halloween_and_stay_all_year(site, browser, day, first, cards):
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
    assert page.locator("#ai-pelit-asut .asu").count() == cards
    ctx.close()


@pytest.mark.parametrize("day,order", [("2026-10-31T12:00:00", ["🎃 Halloween", "Tavalliset", "⚡ Tylypahka"]),
                                       ("2026-11-01T12:00:00", ["🎃 Halloween", "🎄 Joulu", "Tavalliset", "⚡ Tylypahka"]),
                                       ("2026-12-01T12:00:00", ["🎄 Joulu", "Tavalliset", "⚡ Tylypahka", "🎃 Halloween"]),
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
    # A friend in a room wears another one at the same time, and the choice outlives a reload.
    assert page.evaluate("AiPelitOutfits.get('ron').head") == "ron"
    page.reload()
    assert page.evaluate("AiPelitOutfits.current().id") == "hermione"
    assert errors == []
    ctx.close()


def test_the_tylypahka_cards_fit_a_390_px_phone(site, browser):
    site.build()
    (site.root / "koe").mkdir(exist_ok=True)
    (site.root / "koe" / "index.html").write_text(PAGE)
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.clock.set_fixed_time("2026-06-15T12:00:00")
    page.goto(site.url + "koe/")
    page.evaluate("AiPelitOutfits.open()")
    for k in ["harry", "ron", "hermione"]:
        box = page.locator(f"[data-asu={k}]").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 390 and box["y"] + box["height"] <= 844
    page.locator("[data-asu=ron]").tap()
    assert page.evaluate("AiPelitOutfits.current().id") == "ron"
    assert page.evaluate("document.scrollingElement.scrollWidth") <= 390
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
    assert page.locator("#ai-pelit-asut .asu canvas").first.bounding_box()["height"] == 80
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
    assert page.evaluate("AiPelitOutfits.list().filter(o => !o.halloween && !o.tylypahka && !o.joulu).map(o => o.id)") \
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


def test_a_group_takes_over_the_first_earlier_choice_in_its_fixed_order(site, browser):
    # Review of #315: whichever game opens first, Keihäs's earlier choice wins over Kuula's.
    site.build()
    store = {"ai-pelit:_asut:kuula": "kulta", "ai-pelit:_asut:keihas": "noita", "ai-pelit:_asut:laji-c": "suomi"}
    page = shared_page(site, browser, "laji-c", store)
    assert page.evaluate("AiPelitOutfits.current().id") == "noita"
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:yleisurheilu')") == '"noita"'
    page.context.close()
    # An unknown id in the first is skipped.
    page = shared_page(site, browser, "laji-d", {"ai-pelit:_asut:keihas": "ei-ole", "ai-pelit:_asut:kuula": "kulta"})
    assert page.evaluate("AiPelitOutfits.current().id") == "kulta"
    page.context.close()


INKED = """sel => { const c = document.querySelector(sel), g = c.getContext('2d');
  const d = g.getImageData(0, 0, c.width, c.height).data; let n = 0;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++; return n; }"""

PIXELS = """sel => { const c = document.querySelector(sel);
  return Array.from(c.getContext('2d').getImageData(0, 0, c.width, c.height).data).join(); }"""


def test_the_athletics_picker_shows_the_shared_figure_alive(site, browser):
    # #469: data-share="yleisurheilu" draws AiPelitOutfits.figure() on the cards and in a moving
    # preview at the top, never the game's own draw.
    site.build()
    (site.root / "laji-f").mkdir(exist_ok=True)
    (site.root / "laji-f" / "index.html").write_text(SHARED_PAGE.replace(
        "draw: function () {}", "draw: function () { window.ownDraws = (window.ownDraws || 0) + 1; }") % "laji-f")
    ctx = browser.new_context(viewport={"width": 360, "height": 740})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.clock.set_fixed_time("2026-06-15T12:00:00")
    page.goto(site.url + "laji-f/")
    page.evaluate("AiPelitOutfits.open()")
    assert page.locator("#ai-pelit-asut .asu").count() == 16
    assert page.evaluate(INKED, "[data-asu=suomi] canvas") > 300
    page.wait_for_timeout(300)
    assert page.evaluate(INKED, "#ai-pelit-asut-esikatselu") > 1000
    first = page.evaluate(PIXELS, "#ai-pelit-asut-esikatselu")
    page.wait_for_timeout(1700)
    assert page.evaluate(PIXELS, "#ai-pelit-asut-esikatselu") != first, "the preview stood still"
    assert page.evaluate("window.ownDraws || 0") == 0
    # The preview stops with the picker.
    page.click("#ai-pelit-asut-valmis")
    assert page.locator("#ai-pelit-asut-esikatselu").count() == 0
    # Sideways and low there is no room for it; the cards fit instead.
    page.set_viewport_size({"width": 740, "height": 360})
    page.evaluate("AiPelitOutfits.open()")
    assert page.locator("#ai-pelit-asut-esikatselu").count() == 0
    assert page.locator("#ai-pelit-asut .asu").count() == 16
    assert errors == []
    ctx.close()


def test_a_game_with_its_own_figure_keeps_it_in_the_picker(lib_page):
    # Orava, Trampoliini and Voimistelu keep their own figure (#469): no data-share, so the cards
    # and the hopping preview come from the game's draw (here a red or blue box).
    page, errors = lib_page
    page.evaluate("AiPelitOutfits.open()")
    red = page.evaluate("""() => { const c = document.querySelector('[data-asu=perus] canvas');
      const d = c.getContext('2d').getImageData(c.width / 2, c.height / 2, 1, 1).data; return [d[0], d[1], d[2]]; }""")
    assert red == [255, 0, 0]
    page.wait_for_timeout(300)
    assert page.evaluate(INKED, "#ai-pelit-asut-esikatselu") > 1000
    assert errors == []


def christmas_page(site, browser, day, game="koe", size=(360, 740), store=None):
    site.build()
    (site.root / game).mkdir(exist_ok=True)
    (site.root / game / "index.html").write_text(PAGE.replace('data-game="koe"', f'data-game="{game}"'))
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    for k, v in (store or {}).items():
        ctx.add_init_script(f"localStorage.setItem('{k}', '\"{v}\"')")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.clock.set_fixed_time(day)
    page.goto(site.url + game + "/")
    return page


def test_christmas_costumes_are_picked_in_december_and_wait_over_the_summer(site, browser):
    # #473: the five Christmas costumes, in the picker in November and December only.
    page = christmas_page(site, browser, "2026-12-10T12:00:00")
    page.evaluate("AiPelitOutfits.open()")
    assert page.inner_text("#ai-pelit-asut").count("Hyvää joulua!") == 1
    xmas = page.evaluate("AiPelitOutfits.list().filter(o => o.joulu).map(o => [o.id, o.name, o.head])")
    assert xmas == [["joulupukki", "Joulupukki", "pukki"], ["tonttu", "Tonttu", "tonttu"], ["poro", "Poro", "poro"],
                    ["lumiukko", "Lumiukko", "lumiukko"], ["piparkakku", "Piparkakku", "pipari"]]
    page.click("[data-asu=joulupukki]")
    assert page.evaluate("AiPelitOutfits.current().id") == "joulupukki"
    assert page.errors == []
    page.context.close()
    # In January the game's default is worn, the choice is kept, and a friend's Poro is still found.
    page = christmas_page(site, browser, "2027-01-02T12:00:00", store={"ai-pelit:_asut:koe": "joulupukki"})
    assert page.evaluate("AiPelitOutfits.current().id") == "perus"
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:koe')") == '"joulupukki"'
    assert page.evaluate("AiPelitOutfits.get('poro').head") == "poro"
    page.evaluate("AiPelitOutfits.open()")
    assert page.locator("[data-asu=joulupukki]").count() == 0
    assert "joulua" not in page.inner_text("#ai-pelit-asut")
    page.context.close()
    # Next November it is back.
    page = christmas_page(site, browser, "2027-11-05T12:00:00", store={"ai-pelit:_asut:koe": "joulupukki"})
    assert page.evaluate("AiPelitOutfits.current().id") == "joulupukki"
    page.context.close()


def test_orava_gets_no_christmas_costumes(site, browser):
    # #473, Eero's choice: Orava v6's squirrel draws no costume head for them.
    page = christmas_page(site, browser, "2026-12-24T12:00:00", game="orava")
    assert page.evaluate("AiPelitOutfits.list().some(o => o.joulu)") is False
    page.evaluate("AiPelitOutfits.open()")
    assert "🎄 Joulu" not in page.inner_text("#ai-pelit-asut")
    page.context.close()


def test_the_christmas_heads_draw_from_the_side_and_the_front(lib_page):
    page, errors = lib_page
    seen = page.evaluate("""() => ['pukki', 'tonttu', 'poro', 'lumiukko', 'pipari'].map(k => [1, 'front'].map(face => {
      const c = document.createElement('canvas'); c.width = c.height = 120;
      const g = c.getContext('2d'); AiPelitOutfits.head(g, k, 60, 70, 20, face);
      const d = g.getImageData(0, 0, 120, 120).data, cols = new Set();
      for (let i = 0; i < d.length; i += 4) if (d[i + 3] === 255) cols.add('#' + [d[i], d[i + 1], d[i + 2]].map(v => v.toString(16).padStart(2, '0')).join(''));
      return [...cols];
    }))""")
    look = {"pukki": ["#c8202f", "#f4f4f4"], "tonttu": ["#d42a2a", "#f4f4f4"], "poro": ["#8a5a36", "#e0242a", "#d8c39a"],
            "lumiukko": ["#f6f8fc", "#f07a1a", "#1a1a1a"], "pipari": ["#b8733a", "#ffffff"]}
    for (kind, cols), faces in zip(look.items(), seen):
        for face in faces:
            assert all(c in face for c in cols), (kind, cols, face)
    # The whole front figure too, as the athletics podium draws it.
    assert page.evaluate("""() => { const c = document.createElement('canvas'); c.width = 80; c.height = 120;
      const g = c.getContext('2d'); AiPelitOutfits.joulu.forEach(o => AiPelitOutfits.figure(g, o, 40, 115, 100, { up: 1 })); return true; }""")
    assert errors == []


@pytest.mark.parametrize("size", [(360, 640), (740, 360), (640, 360)])
def test_the_christmas_cards_fit_on_the_screen(site, browser, size):
    page = christmas_page(site, browser, "2026-12-10T12:00:00", size=size)
    page.evaluate("AiPelitOutfits.open()")
    assert page.locator("#ai-pelit-asut .asu").count() == 16
    for k in ["joulupukki", "piparkakku", "hermione", "muumio"]:
        # Upright the grid scrolls inside the picker, as before; sideways every card fits at once.
        if size[1] > size[0]:
            page.locator(f"[data-asu={k}]").scroll_into_view_if_needed()
        box = page.locator(f"[data-asu={k}]").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= size[0] and box["y"] + box["height"] <= size[1], (k, box)
    assert page.errors == []
    page.context.close()


def test_a_games_fixed_canvas_style_leaves_the_picker_in_place(site, browser):
    # #473: Mäkihyppy and Voimistelu style every canvas position:fixed; the preview then lay over
    # "Valmis" once the Christmas group made the picker taller.
    page = christmas_page(site, browser, "2026-12-10T12:00:00")
    page.add_style_tag(content="canvas{position:fixed;left:0;top:0;right:0;bottom:0;width:100%;height:100%}")
    page.evaluate("AiPelitOutfits.open()")
    page.click("[data-asu=noita]")
    page.click("#ai-pelit-asut-valmis")
    assert page.evaluate("AiPelitOutfits.isOpen()") is False
    assert page.errors == []
    page.context.close()
