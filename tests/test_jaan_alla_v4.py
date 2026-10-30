"""Jään alla v4 (#106): chapter 3, the ancient ruins and their crystal light puzzles."""

import shutil

import pytest

from conftest import ROOT

URL = "games/jaan-alla/v4/"
SAVE = "ai-pelit:jaan-alla:peli"
# A save from v3 with chapter 2 just finished: no sockets lit, nothing carried yet.
CHAPTER2_DONE = ("{v: 1, t: 2000, flags: {stationLog: true, nordlysLog: true, jaavuoriLog: true, radio: true, aino: true, rescued: true},"
                 " inv: {ruoka: 3, romu: 1, antenni: 1, kristalli: 1}, m: {power: 90, food: 70, hull: 80, air: 100, warm: 100},"
                 " crew: Array.from({length: 12}, (_, i) => ({n: 'x' + i, at: 'station', x: 0, z: 0})),"
                 " sub: {x: -150, y: -60, z: -330, yaw: 0}}")
CHAPTER1_DONE = ("{v: 1, t: 900, flags: {stationLog: true, nordlysLog: true, jaavuoriLog: true, radio: true},"
                 " inv: {ruoka: 3, romu: 1, antenni: 1, kristalli: 1}, sub: {x: 150, y: -12, z: 150, yaw: -0.8}}")
RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"
OVERFLOW = """() => {
  const bad = [];
  for (const el of document.querySelectorAll('#panel:not(.hidden) .card, #panel:not(.hidden) .txt, #menu:not(.hidden) .card'))
    if (el.scrollHeight > el.clientHeight + 1) bad.push('scrolls ' + el.className);
  for (const el of document.querySelectorAll('#panel:not(.hidden) button, #menu:not(.hidden) button')) {
    const r = el.getBoundingClientRect();
    if (r.width && (r.top < 0 || r.left < 0 || r.bottom > innerHeight || r.right > innerWidth)) bad.push('out ' + el.textContent);
  }
  return bad;
}"""

_opened = []


@pytest.fixture(autouse=True)
def _close_pages():
    yield
    while _opened:
        try:
            _opened.pop().close()
        except Exception:
            pass


def open_game(site, browser, w=360, h=740, save=CHAPTER2_DONE):
    shutil.copytree(ROOT / "games" / "jaan-alla", site.games / "jaan-alla")
    site.build()
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    _opened.append(ctx)
    if save:
        ctx.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ sessionStorage.setItem('seeded', '1');"
                            f" localStorage.setItem('{SAVE}', JSON.stringify({save})); }}")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=20000)
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    page.evaluate(RUN)
    return page


def go(page):
    """Continues the saved game and stops the clock: the tests step it themselves."""
    page.click("#jatka")
    page.evaluate("G.hold = true; input.x = input.y = 0; input.up = input.down = false")


def in_ruins(page):
    go(page)
    page.evaluate("sub.pos.set(SITES.rauniot.door.x, SITES.rauniot.door.y, SITES.rauniot.door.z + 4); drawHud()")
    assert page.inner_text("#act") == "Sukella ulos: Muinaiset rauniot"
    page.click("#act")


def at(page, c, r):
    """Swims the diver into cell (c, r) and lets the game see it."""
    page.evaluate(f"diver.pos.set({c} * 4 + 2, 1.3, {r} * 4 + 2); step(1 / 60)")


def test_a_chapter_2_save_goes_on_to_the_ruins(site, browser):
    page = open_game(site, browser)
    assert "Luku 3" in page.inner_text("#menuText")
    go(page)
    page.evaluate("drawHud()")
    assert page.inner_text("#goal") == "Tavoite: Aino pyytää: tutki muinaiset rauniot kanjonin pohjalla."
    assert page.errors == []


def test_the_ruins_stay_sealed_before_chapter_3(site, browser):
    page = open_game(site, browser, save=CHAPTER1_DONE)
    go(page)
    page.evaluate("sub.pos.set(SITES.rauniot.door.x, SITES.rauniot.door.y, SITES.rauniot.door.z + 4); drawHud()")
    assert page.is_hidden("#act")


def test_a_crystal_on_a_socket_opens_its_door(site, browser):
    page = open_game(site, browser)
    in_ruins(page)
    assert page.evaluate("isWall(SITES.rauniot, 4 * 4 + 2, 2 * 4 + 2)") is True
    # An empty socket only says what it needs.
    at(page, 3, 2)
    assert page.evaluate("litCount()") == 0
    at(page, 2, 3)
    assert page.evaluate("G.s.carry") is True
    page.evaluate("drawHud()")
    assert "Vie kristalli tyhjälle jalustalle" in page.inner_text("#goal")
    assert "kristalli mukana" in page.inner_text("#where")
    at(page, 3, 2)
    assert page.evaluate("[litCount(), G.s.carry, isWall(SITES.rauniot, 4 * 4 + 2, 2 * 4 + 2)]") == [1, False, False]
    # The diver swims through the open door; a shut one still stops them.
    page.evaluate("diver.pos.set(3 * 4 + 2, 1.3, 2 * 4 + 2); diver.yaw = -Math.PI / 2; input.y = 1; run(() => diver.pos.x < 6 * 4, 3); input.y = 0")
    assert page.evaluate("diver.pos.x") > 5 * 4
    page.evaluate("diver.pos.set(9 * 4 + 2, 1.3, 2 * 4 + 2); input.y = 1; run(() => true, 2); input.y = 0")
    assert page.evaluate("diver.pos.x") < 10 * 4


def test_only_one_crystal_is_carried_and_any_crystal_fits_any_socket(site, browser):
    page = open_game(site, browser)
    in_ruins(page)
    at(page, 1, 5)    # the crystal down the side passage first
    at(page, 2, 3)    # a second one is left where it is
    assert page.evaluate("[G.s.carry, Object.keys(G.s.taken).filter(k => k.startsWith('rauniot')).length]") == [True, 1]
    at(page, 3, 2)
    assert page.evaluate("litCount()") == 1


def test_every_puzzle_can_be_solved_from_the_airlock(site, browser):
    page = open_game(site, browser)
    solved = page.evaluate("""() => {
        const m = SITES.rauniot.map, lit = {}, used = new Set(), door = { a: '1', b: '2', c: '3' };
        const reach = () => {
            const seen = new Set(), r0 = m.findIndex(row => row.includes('E')), todo = [[m[r0].indexOf('E'), r0]];
            while (todo.length) {
                const [c, r] = todo.pop(), k = c + ',' + r, ch = m[r] && m[r][c];
                if (seen.has(k) || !ch || ch === '#' || (door[ch] && !lit[door[ch]])) continue;
                seen.add(k); todo.push([c + 1, r], [c - 1, r], [c, r + 1], [c, r - 1]);
            }
            return seen;
        };
        for (let n = 0; n < 5; n++) {
            const seen = reach(), cells = [...seen].map(k => k.split(',').map(Number));
            const crystal = cells.find(([c, r]) => m[r][c] === 'C' && !used.has(c + ',' + r));
            const socket = cells.find(([c, r]) => '123'.includes(m[r][c]) && !lit[m[r][c]]);
            if (!crystal || !socket) break;
            used.add(crystal.join(',')); lit[m[socket[1]][socket[0]]] = true;
        }
        const h = m.findIndex(row => row.includes('H'));
        return [Object.keys(lit).length, reach().has(m[h].indexOf('H') + ',' + h)];
    }""")
    assert solved == [3, True]


def test_murals_tell_the_story_once(site, browser):
    page = open_game(site, browser)
    in_ruins(page)
    at(page, 2, 1)
    assert "Valon vartijoiksi" in page.inner_text("#card")
    page.click("#card button:has-text('Jatka')")
    at(page, 2, 1)
    assert page.is_hidden("#panel")


def test_the_heart_wakes_only_with_three_lights_and_ends_chapter_3(site, browser):
    page = open_game(site, browser)
    in_ruins(page)
    page.evaluate("G.s.lit['rauniot:1'] = G.s.lit['rauniot:2'] = true")
    at(page, 19, 1)
    assert page.evaluate("G.s.flags.heart") is None
    page.evaluate("G.s.lit['rauniot:3'] = true; drawHud()")
    assert "Ui Sydämen luo" in page.inner_text("#goal")
    at(page, 19, 1)
    assert page.inner_text("#card h2") == "Sydän herää"
    assert "Luku 3 päättyi" in page.inner_text("#card")
    assert page.evaluate("[G.s.flags.heart, localStorage.getItem('ai-pelit:jaan-alla:luku3') !== null]") == [True, True]
    page.click("#card button:has-text('Jatka')")
    page.evaluate("drawHud()")
    assert "Luku 3 on valmis" in page.inner_text("#goal")
    page.reload()
    page.wait_for_function("window.drawn === true")
    assert "Luvut 1–3" in page.inner_text("#menuText")
    assert page.errors == []


def test_a_reload_keeps_lit_sockets_open_doors_and_the_crystal_in_hand(site, browser):
    page = open_game(site, browser)
    in_ruins(page)
    at(page, 2, 3); at(page, 3, 2); at(page, 1, 5)
    assert page.evaluate("[litCount(), G.s.carry]") == [1, True]
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.click("#jatka")
    page.evaluate("G.hold = true; enterSite('rauniot')")
    assert page.evaluate("[litCount(), G.s.carry, isWall(SITES.rauniot, 4 * 4 + 2, 2 * 4 + 2)]") == [1, True, False]
    assert page.evaluate("items.filter(i => i.k === 'C').length") == 1


@pytest.mark.parametrize("w,h", [(360, 640), (390, 844), (740, 360)])
def test_the_ruins_cards_fit_upright_and_sideways(site, browser, w, h):
    page = open_game(site, browser, w, h)
    in_ruins(page)
    at(page, 2, 1)
    assert page.evaluate(OVERFLOW) == [], "mural"
    page.click("#card button:has-text('Jatka')")
    page.evaluate("G.s.lit['rauniot:1'] = G.s.lit['rauniot:2'] = G.s.lit['rauniot:3'] = true")
    at(page, 19, 1)
    assert page.evaluate(OVERFLOW) == [], "heart"
    assert page.errors == []
