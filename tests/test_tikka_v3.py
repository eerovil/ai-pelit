"""Tikanheitto v3: Vapaa heitto, free throwing on either board with no computer and no rounds (#147)."""

import pytest
from conftest import ROOT, turn

URL = "games/tikka/v3/"

# Steps the game by hand, 1/60 s at a time, until cond() is false or max seconds pass.
RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"


def open_game(site, context, saved=None):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    for k, v in (saved or {}).items():
        page.evaluate(f"localStorage.setItem('ai-pelit:tikka:{k}', '{v}')")
    if saved:
        page.goto(site.url + URL)
    page.evaluate(RUN)
    return page


def throw_turn(page, mx, my):
    for _ in range(3):
        page.evaluate(f"throwAt({mx}, {my}); run(() => flying !== null, 2)")
    page.evaluate("run(() => pause > 0, 3)")


def test_free_throwing_on_the_cottage_board_goes_on_past_ten_rounds(site, context):
    page = open_game(site, context, {"mokki": 231})
    page.click("#frees button[data-b=mokki]")
    assert page.evaluate("[phase, mode, players.length, players[0].ai, scoreAt(0, 0).label]") == ["play", "vapaa", 1, None, "10"]
    assert page.is_visible("#stop")
    for _ in range(11):
        throw_turn(page, 0, 0)
    throw_turn(page, 0, 100)   # three fives
    assert page.evaluate("[phase, freeTurns, freeBest, freeAvg()]") == ["play", 12, 30, "28,8"]
    page.click("#stop")
    assert page.inner_text("#result") == "Vapaa heitto: 12 kierrosta, keskiarvo 28,8 p, paras 30 p"
    assert not page.is_visible("#stop")
    # Free throwing sets no record and leaves the old one alone.
    assert page.evaluate("localStorage.getItem('ai-pelit:tikka:mokki')") == "231"
    assert page.errors == []


def test_free_throwing_on_the_darts_board_and_the_board_is_remembered(site, context):
    page = open_game(site, context)
    page.click("#frees button[data-b=darts]")
    assert page.evaluate("[mode, freeBoard, scoreAt(0, -103).label]") == ["vapaa", "darts", "T20"]
    throw_turn(page, 0, -103)
    assert page.evaluate("[freeTurns, freeBest, players[0].score]") == [1, 180, 180]
    assert page.evaluate("localStorage.getItem('ai-pelit:tikka:vapaa')") == "darts"
    page.click("#stop")
    assert page.inner_text("#result") == "Vapaa heitto: 1 kierros, keskiarvo 180 p, paras 180 p"
    # The other modes still play as before.
    page.click("#go")
    assert page.evaluate("[mode, scoreAt(0, 0).label]") == ["mokki", "10"]
    assert not page.is_visible("#stop")
    assert page.errors == []


def test_stopping_mid_turn_counts_only_whole_turns(site, context):
    page = open_game(site, context)
    page.click("#frees button[data-b=mokki]")
    page.evaluate("throwAt(0, 0); run(() => flying !== null, 2)")
    page.click("#stop")
    assert page.inner_text("#result") == ""
    assert page.evaluate("phase") == "menu"
    assert page.errors == []


def test_turning_the_phone_keeps_free_throwing_and_its_tally(site, context):
    page = open_game(site, context)
    turn(page, {"width": 360, "height": 740})
    page.click("#frees button[data-b=mokki]")
    throw_turn(page, 0, 0)
    turn(page, {"width": 740, "height": 360})
    assert page.evaluate("[phase, mode, freeTurns]") == ["play", "vapaa", 1]
    b = page.locator("#stop").bounding_box()
    assert b["x"] + b["width"] <= 740 and b["y"] + b["height"] <= 360
    page.click("#stop")
    assert page.evaluate("phase") == "menu"
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (740, 360), (640, 360), (390, 844)])
def test_the_menu_fits_without_scrolling(site, context, size):
    w, h = size
    page = open_game(site, context, {"mokki": 231, "ennatys": 412, "voitot": 3})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    boxes = {}
    for sel in ("#go", "#multi", "#frees", "#kisa", "#go501", "#opps", "#stats", "#menu .help"):
        b = boxes[sel] = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    for a in boxes:
        for b in boxes:
            if a < b:
                p, q = boxes[a], boxes[b]
                assert p["x"] + p["width"] <= q["x"] or q["x"] + q["width"] <= p["x"] or \
                    p["y"] + p["height"] <= q["y"] or q["y"] + q["height"] <= p["y"], (a, b)
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 740), (740, 360), (390, 844)])
def test_the_free_panel_has_no_text_on_text_or_under_the_stop_button(site, context, size):
    w, h = size
    page = open_game(site, context)
    turn(page, {"width": w, "height": h})
    page.click("#frees button[data-b=darts]")
    throw_turn(page, 0, -103)
    page.evaluate("for (let i = 0; i < 2; i++) { throwAt(0, -103); run(() => flying !== null, 2); } draw()")
    texts = page.evaluate("panelTexts")
    stop = page.locator("#stop").bounding_box()
    texts.append({"text": "stop", "x0": stop["x"], "x1": stop["x"] + stop["width"], "y0": stop["y"], "y1": stop["y"] + stop["height"]})
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            assert a["x1"] <= b["x0"] or b["x1"] <= a["x0"] or a["y1"] <= b["y0"] or b["y1"] <= a["y0"], (a, b)
    assert page.errors == []


def test_a_reload_mid_free_throwing_keeps_the_saves_and_the_board_choice(site, context):
    page = open_game(site, context, {"mokki": 231, "ennatys": 412, "voitot": 3, "vastus": "kova"})
    page.click("#frees button[data-b=darts]")
    throw_turn(page, 0, 0)
    page.reload()
    page.evaluate(RUN)
    # A reload ends the free session, like leaving it; every earlier save is still there.
    assert page.evaluate("[phase, freeBoard, opp]") == ["menu", "darts", "kova"]
    assert page.inner_text("#stats") == "Ennätykset: Mökkitikka 231 p · Pistekisa 412 p · Voittoja tietokoneesta 3"
    assert page.errors == []
