"""Areena in a phone-sized Chromium."""

import pytest

from conftest import ROOT


@pytest.mark.parametrize("version", ["v1", "v2", "v3"])
def test_the_countdown_shows_3_2_1_then_fight(site, context, version):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/areena/{version}/")
    page.fill("#name", "Testi")
    page.click("#go")
    seen = []
    for _ in range(60):
        label = page.evaluate("state === 'count' ? countText() : state")
        if not seen or seen[-1] != label:
            seen.append(label)
        if label == "fight":
            break
        page.wait_for_timeout(100)
    assert seen == ["3", "2", "1", "TAISTELE!", "fight"]
    assert page.evaluate("me.name") == "Testi"


def test_v2_is_easier_than_v1_on_the_same_level(site, context):
    site.build(ROOT / "games")
    found = {}
    for version in ("v1", "v2"):
        page = context.new_page()
        page.goto(f"{site.url}games/areena/{version}/")
        page.evaluate("localStorage.setItem('ai-pelit:areena:taso', '3')")
        page.reload()
        page.click("#go")
        found[version] = page.evaluate("[foe.max, foe.speed]")
        page.close()
    assert found["v2"][0] < found["v1"][0]
    assert found["v2"][1] < found["v1"][1]


@pytest.fixture
def two_phones(site, browser):
    from test_rooms_lib import Relay

    site.build(ROOT / "games")
    relay = Relay()
    contexts = []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(f"{site.url}games/areena/v3/")
        page.fill("#name", name)
        page.click("#multi")
        return page

    yield phone
    for ctx in contexts:
        ctx.close()


def test_v3_two_phones_fight_each_other_online(two_phones):
    host = two_phones("Eero")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    guest = two_phones("Aino")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.wait_for_timeout(200)
    assert host.locator("#aipr-members li").all_inner_texts() == ["👑 Eero (sinä)", "Aino"]
    host.click("#aipr-start")
    for p in (host, guest):
        p.wait_for_function("net && state === 'fight'", timeout=8000)
    # Each phone sees its own fighter at the bottom, under the name typed in Areena's menu.
    assert host.evaluate("[me.name, foe.name]") == ["Eero", "Aino"]
    guest.wait_for_function("foe.name === 'Eero'")
    assert guest.evaluate("me.name") == "Aino"
    assert host.evaluate("me.y > foe.y") and guest.evaluate("me.y > foe.y")
    # The friend's stick moves the friend's fighter on the host: up on the friend's screen is
    # towards the host's fighter, so down on the host's.
    y0 = host.evaluate("foe.y")
    guest.evaluate("""(() => { const c = document.getElementById('c'), h = padHome();
      const ev = (t, x, y) => c.dispatchEvent(new PointerEvent(t, {pointerId: 1, clientX: x, clientY: y, bubbles: true, cancelable: true}));
      ev('pointerdown', h.x, h.y); ev('pointermove', h.x, h.y - 45); })()""")
    host.wait_for_function(f"foe.y > {y0} + 40")
    # The host's fighter loses: both phones go back to the room screen with the result.
    host.evaluate("me.hp = 1; damage(me, 20, foe.x, foe.y, 0)")
    host.wait_for_function("state === 'room'", timeout=8000)
    guest.wait_for_function("state === 'room'", timeout=8000)
    assert host.locator("#aipr-result").inner_text() == "💀 Aino voitti"
    assert guest.locator("#aipr-result").inner_text() == "🏆 Aino voitti!"
    assert host.errors == [] and guest.errors == []
