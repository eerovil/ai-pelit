"""No text selection (#457): on an iPhone, holding a game's button down (Raketti's thrusters) started
selecting the page's text. public/back.js turns selection off in every game, the shelf and the room
page in their own CSS; text fields still select and edit.

Chromium has no iPhone long press, so these check the styles Safari reads (-webkit-user-select,
-webkit-touch-callout) and that a double tap on text selects nothing."""

from conftest import game_page, make_game

BODY = (
    '<p id="teksti">Pitkä teksti jota ei saa valita</p><button id="nappi">Suutin</button>'
    '<input id="nimi" value="Nimimerkki"><textarea id="viesti">Viesti</textarea>'
    '<p id="oma" style="user-select:text;-webkit-user-select:text">Pelin oma tyyli rivissä</p>'
    '<style>#oma2, .oma3 { -webkit-user-select: text; user-select: text; -webkit-touch-callout: default; }</style>'
    '<p id="oma2">Pelin oma sääntö</p><div class="oma3"><span id="oma3">Lapsi</span></div>'
    '<div id="muokattava" contenteditable="true">Muokattava <b id="lihava">teksti</b></div>'
)

STYLE = """sel => {
  const s = getComputedStyle(document.querySelector(sel));
  return [s.userSelect, s.webkitUserSelect, s.webkitTouchCallout];
}"""


def open_game(site, context):
    make_game(site.games, "pomppu", [game_page("v1", body=BODY)])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    return page


def test_a_game_page_selects_no_text(site, context):
    page = open_game(site, context)
    for sel in ("body", "#teksti", "#nappi"):
        user, webkit, callout = page.evaluate(STYLE, sel)
        assert (user, webkit) == ("none", "none"), sel
        assert callout in ("none", None), sel  # Chromium may not know -webkit-touch-callout
    page.dblclick("#teksti")
    page.click("#nappi", delay=800)
    assert page.evaluate("getSelection().toString()") == ""
    css = page.evaluate("document.getElementById('ai-pelit-ei-valintaa').textContent")
    assert "-webkit-user-select:none" in css and "-webkit-touch-callout:none" in css


def test_a_games_own_rule_does_not_make_text_selectable(site, context):
    """The issue asks for no selection everywhere: a game's own user-select:text (inline, by id,
    by class, inherited by a child) loses to the shared rule."""
    page = open_game(site, context)
    for sel in ("#oma", "#oma2", "#oma3"):
        assert page.evaluate(STYLE, sel)[:2] == ["none", "none"], sel
        page.dblclick(sel)
        assert page.evaluate("getSelection().toString()") == "", sel


def test_text_fields_and_editable_elements_still_select(site, context):
    page = open_game(site, context)
    for sel in ("#nimi", "#viesti", "#muokattava", "#lihava"):
        assert page.evaluate(STYLE, sel)[:2] == ["text", "text"], sel
    page.fill("#nimi", "Testi")
    assert page.input_value("#nimi") == "Testi"
    page.dblclick("#lihava")
    assert page.evaluate("getSelection().toString()").strip() == "teksti"


def test_the_shelf_and_the_room_page_select_no_text(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector(".card")
    assert page.evaluate(STYLE, ".card")[:2] == ["none", "none"]
    page.dblclick(".card h2")
    assert page.evaluate("getSelection().toString()") == ""
    page.goto(f"{site.url}huone/")
    assert page.evaluate(STYLE, "body")[:2] == ["none", "none"]


FRAME = '<p id="f">Lajin teksti</p><button id="fb">Hyppää</button><input id="fi" value="x">'


def test_frames_without_back_js_select_no_text_after_each_load(site, context):
    """Ottelu's events play in frames without back.js (#168): each frame, two at once, one added
    after the page loaded, and a frame that loads its next event, all get the rule."""
    script = (
        "window.addFrame = () => { const f = document.createElement('iframe');"
        f" f.srcdoc = {FRAME!r}; document.body.appendChild(f); return document.querySelectorAll('iframe').length; }};"
    )
    body = f'<iframe id="eka" srcdoc=\'{FRAME}\'></iframe>'
    make_game(site.games, "pomppu", [game_page("v1", body=body, script=script)])
    site.build()
    page = context.new_page()
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{site.url}games/pomppu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    page.evaluate("addFrame()")

    def frames_ok():
        return page.evaluate("""() => [...document.querySelectorAll('iframe')].map(f => {
          const d = f.contentDocument, s = sel => getComputedStyle(d.querySelector(sel)).webkitUserSelect;
          return d.querySelector('#f') ? [s('#f'), s('#fb'), s('#fi'), d.querySelectorAll('#ai-pelit-ei-valintaa').length] : null;
        })""")

    page.wait_for_function("[...document.querySelectorAll('iframe')].every(f => f.contentDocument?.getElementById('ai-pelit-ei-valintaa') && f.contentDocument?.querySelector('#f'))")
    assert frames_ok() == [["none", "none", "text", 1]] * 2
    # The next event loads in the same frame: the new document gets the rule too.
    page.evaluate(f"document.getElementById('eka').srcdoc = {FRAME!r} + '<p>seuraava</p>'")
    page.wait_for_function("document.getElementById('eka').contentDocument.body?.textContent.includes('seuraava') && document.getElementById('eka').contentDocument.getElementById('ai-pelit-ei-valintaa')")
    assert frames_ok() == [["none", "none", "text", 1]] * 2
    page.frame_locator("#eka").locator("#f").dblclick()
    assert page.evaluate("document.getElementById('eka').contentWindow.getSelection().toString()") == ""


def test_a_reload_keeps_one_rule(site, context):
    page = open_game(site, context)
    page.reload()
    page.wait_for_selector("#ai-pelit-back")
    assert page.evaluate("document.querySelectorAll('#ai-pelit-ei-valintaa').length") == 1
    assert page.evaluate(STYLE, "#nappi")[1] == "none"
