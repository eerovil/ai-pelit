"""Areena in a phone-sized Chromium."""

import pytest

from conftest import ROOT


@pytest.mark.parametrize("version", ["v1", "v2", "v3", "v4"])
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

    phone.relay = relay
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


def test_v3_a_friend_away_at_the_end_gets_the_result_after_a_reload(two_phones):
    host = two_phones("Eero")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest = two_phones("Aino")
    guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    for p in (host, guest):
        p.wait_for_function("net && state === 'fight'", timeout=8000)
    # The friend's phone drops off; the host lets the computer fight on, and wins.
    two_phones.relay.drop(guest)
    host.locator("#aipr-goOn").click(timeout=8000)
    host.evaluate("foe.hp = 1; damage(foe, 20, me.x, me.y, 0)")
    host.wait_for_function("state === 'room'", timeout=8000)
    assert host.locator("#aipr-result").inner_text() == "🏆 Eero voitti!"
    # The friend comes back by reloading the page, and still hears how the fight ended.
    two_phones.relay.back(guest)
    guest.reload()
    guest.wait_for_function("document.getElementById('aipr-result')?.innerText === '💀 Eero voitti'", timeout=8000)
    assert guest.evaluate("state") == "room"
    assert host.errors == [] and guest.errors == []


def open_fight(two_phones, guest_room_name=None):
    host = two_phones("Eero")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest = two_phones("Aino")
    if guest_room_name:
        guest.fill("#aipr-name", guest_room_name)
    guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    for p in (host, guest):
        p.wait_for_function("net && state === 'fight'", timeout=8000)
    return host, guest


def test_v3_a_name_changed_on_the_room_screen_is_the_fighters_name(two_phones):
    host, guest = open_fight(two_phones, "Aino K")
    assert host.locator("#aipr-members li").all_inner_texts() == ["👑 Eero (sinä)", "Aino K"]
    assert host.evaluate("[me.name, foe.name]") == ["Eero", "Aino K"]
    assert guest.evaluate("[me.name, foe.name]") == ["Aino K", "Eero"]
    host.wait_for_timeout(500)
    assert host.evaluate("foe.name") == "Aino K"


DODGE = """(() => { const c = document.getElementById('c'), b = buttons().find(b => b.k === 'dash');
  const ev = t => c.dispatchEvent(new PointerEvent(t, {pointerId: 7, clientX: b.x, clientY: b.y, bubbles: true, cancelable: true}));
  ev('pointerdown'); setTimeout(() => ev('pointerup'), 50); })()"""


def test_v3_the_friend_can_dodge_before_and_after_reloading(two_phones):
    host, guest = open_fight(two_phones)
    for _ in range(2):
        host.wait_for_function("foe.dashCd <= 0", timeout=5000)
        guest.evaluate(DODGE)
        host.wait_for_function("foe.dashCd > 0.5", timeout=3000)
    guest.reload()
    guest.wait_for_function("net && state === 'fight' && !AiPelitRooms.paused", timeout=10000)
    host.wait_for_function("!AiPelitRooms.paused && foe.dashCd <= 0", timeout=10000)
    guest.evaluate(DODGE)
    host.wait_for_function("foe.dashCd > 0.5", timeout=3000)
    assert host.errors == [] and guest.errors == []


def test_v3_the_friends_bow_and_sword_hurt_the_host_and_win(two_phones):
    host, guest = open_fight(two_phones)
    # Real touches on the friend's phone: first the bow from where they stand, then walk up and
    # hold the sword. The host's player does nothing.
    guest.evaluate("""(() => {
      const c = document.getElementById('c');
      const ev = (t, id, x, y) => c.dispatchEvent(new PointerEvent(t, {pointerId: id, clientX: x, clientY: y, bubbles: true, cancelable: true}));
      const at = k => buttons().find(b => b.k === k);
      window.useBow = () => { const b = at('bow'); ev('pointerdown', 2, b.x, b.y); };
      window.useSword = () => {
        ev('pointerup', 2, 0, 0);
        const h = padHome(); ev('pointerdown', 1, h.x, h.y);
        setInterval(() => {
          const dx = foe.x - me.x, dy = foe.y - me.y, d = Math.hypot(dx, dy) || 1;
          ev('pointermove', 1, h.x + dx / d * 45, h.y + dy / d * 45);
        }, 50);
        const s = at('sword'); ev('pointerdown', 3, s.x, s.y);
      };
    })()""")
    guest.evaluate("useBow()")
    host.wait_for_function("me.hp < 100", timeout=8000)
    assert guest.evaluate("me.hp") == 100
    after_bow = host.evaluate("me.hp")
    guest.evaluate("useSword()")
    host.wait_for_function(f"me.hp <= {after_bow} - 16", timeout=10000)
    host.wait_for_function("state === 'room'", timeout=30000)
    guest.wait_for_function("state === 'room'", timeout=8000)
    assert host.locator("#aipr-result").inner_text() == "💀 Aino voitti"
    assert guest.locator("#aipr-result").inner_text() == "🏆 Aino voitti!"
    assert host.errors == [] and guest.errors == []
# CI timing probe for #123, not to be merged
