"""Jään alla v2 (#95): v1's game plays with the phone turned sideways, and portrait stays as in v1."""

import shutil

import pytest

from conftest import ROOT, turn

URL = "games/jaan-alla/v2/"
SAVE = "ai-pelit:jaan-alla:peli"
SAVED = "{v: 1, t: 300, flags: {stationLog: true}, inv: {ruoka: 5, romu: 3, antenni: 0, kristalli: 0}, sub: {x: -50, y: -30, z: -60, yaw: 1}}"

# Steps the game by hand, 1/60 s at a time, while cond() holds or max seconds pass.
RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"

# Every open card or menu that scrolls, and every button of it outside the screen.
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
    # Close every context a test opened even when it fails, so its 3D loop does not slow the next.
    yield
    while _opened:
        ctx = _opened.pop()
        try:
            ctx.close()
        except Exception:
            pass


def open_game(site, browser, w=740, h=360, save=None):
    # Only this game: other games' half-done versions in the same checkout must not break the build.
    shutil.copytree(ROOT / "games" / "jaan-alla", site.games / "jaan-alla")
    site.build()
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    _opened.append(ctx)
    if save:
        ctx.add_init_script(f"localStorage.setItem('{SAVE}', JSON.stringify({save}))")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=20000)
    # Headless Chromium draws WebGL in software (SwiftShader); without it the page says so instead.
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    page.evaluate(RUN)
    return page


def box(page, sel):
    return page.locator(sel).bounding_box()


def inside(b, w, h):
    return b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h


def overlaps(a, b):
    return (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"]
            and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"])


def test_the_menu_fits_sideways_and_its_buttons_work(site, browser):
    page = open_game(site, browser, save=SAVED)
    assert page.evaluate(OVERFLOW) == []
    for sel in ("#jatka", "#uusi"):
        assert inside(box(page, sel), 740, 360), sel
    assert not overlaps(box(page, "#ai-pelit-back"), box(page, "#menu .card h1"))
    page.click("#uusi")
    assert "Paina uudelleen" in page.inner_text("#uusi")
    page.click("#jatka")
    assert page.evaluate("[G.mode, Math.round(sub.pos.x), G.s.inv.romu]") == ["sub", -50, 3]
    assert page.errors == []


@pytest.mark.parametrize("w,h", [(740, 360), (640, 360), (844, 390)])
def test_every_story_card_fits_sideways_without_scrolling(site, browser, w, h):
    page = open_game(site, browser, w, h)
    page.click("#uusi")
    assert page.evaluate(OVERFLOW) == [], "story"
    page.click("#card button:has-text('Sukella!')")
    page.evaluate("G.hold = true")
    cards = {
        # The station with every button and a message: the fullest card.
        "station": "Object.assign(G.s.flags, { stationLog: true }); Object.assign(G.s.inv, { antenni: 1, kristalli: 1, romu: 1 });"
                   "G.s.varasto = true; G.s.storeAt = G.s.t; G.s.m.hull = 50; dock();"
                   "[...document.querySelectorAll('#card button')].find(b => b.textContent.includes('Radiomasto')).click()",
        "log": "G.s.flags.stationLog = false; dock(); [...document.querySelectorAll('#card button')].find(b => b.textContent.includes('Ohjauskeskus')).click()",
        "radio": "Object.assign(G.s.flags, { stationLog: true, radio: true }); dock();"
                 "[...document.querySelectorAll('#card button')].find(b => b.textContent.includes('Radiomasto')).click()",
        "bag": "G.s.m.hull = 50; G.s.inv.romu = 1; drawHud(); document.getElementById('bag').click()",
        "nordlys": "enterSite('nordlys'); diver.pos.set(13 * 4 + 2, 1.3, 1 * 4 + 2); step(1 / 60)",
    }
    for name, js in cards.items():
        page.evaluate("document.getElementById('panel').classList.add('hidden'); G.paused = false; if (G.mode === 'dive') leaveSite()")
        page.evaluate(js)
        assert page.is_visible("#panel"), name
        assert page.evaluate(OVERFLOW) == [], name
        assert not overlaps(box(page, "#ai-pelit-back"), box(page, "#card")), name
    assert page.errors == []


def test_a_round_plays_sideways_with_the_hud_in_one_row_and_the_controls_in_the_corners(site, browser):
    page = open_game(site, browser)
    page.click("#uusi")
    page.click("#card button:has-text('Sukella!')")
    page.evaluate("G.hold = true; input.x = input.y = 0; drawHud()")
    b = {k: box(page, "#" + k) for k in ("meters", "goalbar", "bag", "stick", "up", "down")}
    b["back"] = box(page, "#ai-pelit-back")
    # One row along the top: chip, meters, goal, bag, side by side.
    assert b["goalbar"]["y"] + b["goalbar"]["height"] < 80
    for x, y in (("back", "meters"), ("meters", "goalbar"), ("goalbar", "bag"), ("back", "goalbar")):
        assert not overlaps(b[x], b[y]), (x, y)
    # The stick in the lower left, up and down in the lower right, all below the HUD.
    for k in ("stick", "up", "down"):
        assert inside(b[k], 740, 360), k
        assert b[k]["y"] > b["goalbar"]["y"] + b["goalbar"]["height"], k
    assert b["stick"]["x"] < 60 and b["up"]["x"] > 600
    # The round runs: the stick drives SISU forward.
    z0 = page.evaluate("sub.pos.z")
    page.evaluate("input.y = 1; run(() => true, 3); input.y = 0")
    assert page.evaluate("sub.pos.z") < z0 - 15
    # The action button near the station sits in the right-hand column, inside the screen.
    page.evaluate("input.y = 1; run(() => !currentAction(), 10); input.y = 0; drawHud()")
    assert page.inner_text("#act") == "Telakoidu asemalle"
    act = box(page, "#act")
    assert inside(act, 740, 360) and act["x"] > 370
    page.click("#act")
    assert page.inner_text("#card h2") == "Aurora-asema A-3"
    assert page.errors == []


def test_turning_the_phone_mid_round_keeps_the_round_and_the_view_follows(site, browser):
    page = open_game(site, browser, 360, 740)
    page.click("#uusi")
    page.click("#card button:has-text('Sukella!')")
    page.evaluate("G.hold = true; input.y = 1; run(() => true, 2); input.y = 0")
    before = page.evaluate("[G.mode, G.s.t, sub.pos.x, sub.pos.y, sub.pos.z]")
    for w, h in ((740, 360), (360, 740), (844, 390)):
        turn(page, {"width": w, "height": h})
        page.wait_for_function(f"innerWidth === {w} && innerHeight === {h}", timeout=20000)
        page.wait_for_function(f"Math.abs(camera.aspect - {w / h}) < 0.01", timeout=20000)
        canvas = page.evaluate("[document.getElementById('c').width, document.getElementById('c').height]")
        assert abs(canvas[0] / canvas[1] - w / h) < 0.02
        now = page.evaluate("[G.mode, G.s.t, sub.pos.x, sub.pos.y, sub.pos.z]")
        assert now == before, (w, h)
    # And it keeps going from there.
    page.evaluate("input.y = 1; run(() => true, 1); input.y = 0")
    assert page.evaluate("G.s.t") > before[1]
    assert page.is_hidden("#menu") and page.is_visible("#stick")
    assert page.errors == []
