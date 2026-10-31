"""Last Signal v5 (#138): friends (2–4 phones) come into the host's game to help. The game and its save are the host's;
each friend has their own person who walks SISU's rooms and dives, whoever takes the helm first drives, finds and
stores go to whoever asks first, each diver has their own air, the story's moments show on every phone, and the
night comes when everyone is in the bunk room. Alone it plays as v4: v4's tests run here on v5 too."""

import json
import shutil

import pytest

import test_last_signal_v4 as v4
from conftest import ROOT
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)
from test_rooms_lib import Relay

URL = "games/last-signal/v5/"
SAVE = v4.SAVE


@pytest.fixture(autouse=True)
def _v5(monkeypatch):
    monkeypatch.setattr(v4, "URL", URL)


# Alone, v5 is v4: every v4 test, on v5.
for _name in dir(v4):
    if _name.startswith("test_"):
        globals()[_name + "_alone"] = getattr(v4, _name)


def save_with(**over):
    s = {"v": 1, "day": 4, "t": 900, "sub": {"x": 575, "y": 100, "dir": 1}, "m": {"food": 60, "health": 80, "hull": 90},
         "inv": {"ruoka": 1, "laake": 1, "osat": 2, "vahvistin": 0, "antenni": 0, "kortti": 0},
         "up": {"hull": 1, "tank": 1, "lamp": 1}, "got": {}, "known": {"kontti": True},
         "flags": {"pinged": True, "koti": True}, "finds": [], "findN": 3}
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(s.get(k), dict):
            s[k] = {**s[k], **v}
        else:
            s[k] = v
    return s


def room(site, browser, names=("Eero", "Aino", "Ville"), saves=None, w=360, h=740):
    """Phones in one room, each with its nickname (and its own save, if given); the first makes the room and
    starts. Returns the pages once every phone is in the game, the cards closed."""
    saves = saves or [save_with()] + [None] * (len(names) - 1)
    shutil.copytree(ROOT / "games" / "last-signal", site.games / "last-signal")
    site.build()
    relay = Relay()
    pages = []
    for n, name in enumerate(names):
        ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
        _opened.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        if saves and saves[n]:
            ctx.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ sessionStorage.setItem('seeded', '1');"
                                f" localStorage.setItem('{SAVE}', {json.dumps(json.dumps(saves[n]))}); }}")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.wait_for_function("window.drawn === true")
        page.evaluate(v4.RUN)
        pages.append(page)
    host, guests = pages[0], pages[1:]
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    for g in guests:
        g.click("#multi")
        g.fill("#aipr-codeIn", code)
        g.click("#aipr-joinBtn")
        g.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length > 1")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(pages)}")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("G.s && G.mode !== 'wait' && G.mode !== 'menu'")
    # Every friend is seen by the host, and the host by every friend.
    host.wait_for_function(f"Object.values(net.others).filter(o => o.mode !== 'wait').length === {len(guests)}")
    for g in guests:
        g.wait_for_function("Object.values(net.others).some(o => o.mode === 'sub')")
    return pages


def close_cards(*pages):
    for p in pages:
        p.evaluate("closeCard()")


def stand(page, room_id):
    """Puts the person in the middle of a room, standing still, as walking there would."""
    page.evaluate(f"""(() => {{ const r = ROOMS.find(r => r.id === '{room_id}');
      Object.assign(crew, {{ x: (Math.max(r.x0, -11) + Math.min(r.x1, 11.8)) / 2, y: r.deck ? LOW : UP, to: null, moving: false,
        climbing: false }}); enterRoom(true); drawHud(); }})()""")
    assert page.evaluate("crew.room") == room_id


def toast(page):
    return page.evaluate("$('toast').classList.contains('hidden') ? '' : $('toast').textContent")


def test_friends_come_into_the_hosts_game_and_their_own_save_stays_as_it_was(site, browser):
    own = save_with(day=9, inv={"ruoka": 5})
    host, aino, ville = room(site, browser, saves=[save_with(), own, None])
    # The host is at the helm of their own game; the friends stand in the control room of the same SISU.
    assert host.evaluate("[G.mode, G.s.day]") == ["sub", 4]
    for g in (aino, ville):
        assert g.evaluate("[G.mode, crew.room, G.s.day, G.s.inv.ruoka]") == ["home", "ohjaamo", 4, 1]
        assert "Mukana SISUssa" in g.inner_text("#card")
        assert "Eero" in g.inner_text("#card")
        assert g.evaluate(v4.OVERFLOW) == []
    close_cards(aino, ville)
    # The friend eats from the host's stores; their own save is never written.
    stand(aino, "keittio")
    aino.click("#act")
    host.wait_for_function("G.s.inv.ruoka === 0")
    aino.wait_for_timeout(500)
    assert json.loads(aino.evaluate(f"localStorage.getItem('{SAVE}')")) == own
    assert ville.evaluate(f"localStorage.getItem('{SAVE}')") is None
    assert host.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).inv.ruoka") == 0
    # Each sees the others: names over the people inside SISU, in their own colours.
    host.click("#home")
    close_cards(host)
    host.wait_for_function("Object.values(net.others).every(o => o.mode === 'home')")
    assert sorted(host.evaluate("Object.values(net.others).map(o => o.name)")) == ["Aino", "Ville"]
    assert len(set(host.evaluate("Object.values(net.cols)"))) == 3
    for p in (host, aino, ville):
        assert p.errors == []


def test_whoever_takes_the_helm_first_drives_and_the_others_see_who(site, browser):
    host, aino, ville = room(site, browser)
    close_cards(host, aino, ville)
    # The host drives: in the control room the helm button names them and cannot be pressed.
    aino.wait_for_function("net.helm === AiPelitRooms.hostId")
    stand(aino, "ohjaamo")
    assert aino.inner_text("#act") == "⛵ Eero ruorissa"
    assert aino.is_disabled("#act")
    aino.click("#home")
    aino.wait_for_function("$('toast').textContent === 'Eero on ruorissa'")
    assert aino.evaluate("G.mode") == "home"
    # The host goes inside. The helm is in the control room: from the galley the ⛵ corner button only says so, and
    # an ask from there is refused by the host too.
    host.click("#home")
    close_cards(host)
    aino.wait_for_function("!net.helm")
    ville.wait_for_function("!net.helm")
    stand(ville, "keittio")
    ville.click("#home")
    assert toast(ville) == "Kävele ohjaamoon: ruori on siellä"
    ville.evaluate("AiPelitRooms.send({ t: 'do', a: 'helm', p: mine() })")
    ville.wait_for_function("$('toast').textContent === 'Ruoriin pääsee ohjaamosta'")
    assert ville.evaluate("G.mode") == "home" and host.evaluate("net.helm") is None
    # In the control room the first friend to ask gets the helm, the second is told who has it.
    stand(ville, "ohjaamo")
    aino.evaluate("toHelm()")
    aino.wait_for_function("G.mode === 'sub'")
    ville.evaluate("toHelm()")
    ville.wait_for_function("$('toast').textContent === 'Aino on ruorissa'")
    ville.wait_for_function("net.helm && net.helm !== AiPelitRooms.me")
    ville.evaluate("drawHud()")
    assert ville.inner_text("#act") == "⛵ Aino ruorissa"
    # Aino drives SISU; the host's SISU (and the save) goes with her.
    x0 = host.evaluate("sub.x")
    aino.evaluate("input.x = 1")
    host.wait_for_function(f"sub.x > {x0 + 5}")
    aino.evaluate("input.x = 0")
    host.wait_for_function(f"JSON.parse(localStorage.getItem('{SAVE}')).sub.x > {x0 + 5}", timeout=8000)
    for p in (host, aino, ville):
        assert p.errors == []


def test_two_friends_eating_the_last_ration_the_first_one_gets_it(site, browser):
    host, aino, ville = room(site, browser, saves=[save_with(m={"food": 40}, inv={"ruoka": 1}), None, None])
    close_cards(host, aino, ville)
    for g in (aino, ville):
        stand(g, "keittio")
    aino.evaluate("act('eat')")
    ville.evaluate("act('eat')")
    host.wait_for_function("G.s.inv.ruoka === 0 && G.s.m.food > 70")
    said = []
    for g in (aino, ville):
        g.wait_for_function("!$('toast').classList.contains('hidden')")
        said.append(toast(g))
    assert sorted(said) == ["Lämmin ateria. Olo paranee.", "Ruoka loppui juuri."]
    # The shared stores show on every phone: the galley's button is out of food for both.
    for g in (aino, ville):
        g.wait_for_function("G.s.inv.ruoka === 0")
        g.evaluate("drawHud()")
        assert g.is_disabled("#act")


def dive(page):
    """From inside SISU: the suit on and out of the airlock."""
    stand(page, "puvut")
    page.click("#act")
    stand(page, "ilmalukko")
    page.click("#act")
    page.wait_for_function("G.mode === 'dive'")


def test_each_diver_has_their_own_air_and_haul_and_sisu_waits_for_them(site, browser):
    host, aino, ville = room(site, browser, saves=[save_with(inv={"ruoka": 0}), None, None])
    close_cards(host, aino, ville)
    host.evaluate("sub.x = SITES.find(s => s.id === 'kontti').spot[0]; sub.y = SITES.find(s => s.id === 'kontti').spot[1]")
    for g in (aino, ville):
        g.wait_for_function("Math.abs(sub.x - 575) < 1 && Math.abs(sub.vx) < 0.5")
        dive(g)
    host.wait_for_function("Object.values(net.others).every(o => o.mode === 'dive')")
    # Two divers, two tanks.
    assert aino.evaluate("diver.air") > 50 and ville.evaluate("diver.air") > 50
    # A find goes to the first diver to reach it: once taken it is gone from everyone's sea, and a diver who
    # touched it at the same moment hears who got it.
    food = aino.evaluate("ITEMS.filter(it => it.site === 'kontti' && it.k === 'ruoka').map(it => [it.id, it.x, it.y])")
    aino.evaluate("G.hold = true")
    ville.evaluate("G.hold = true")
    for g in (aino, ville):
        g.evaluate(f"diver.x = {food[0][1]}; diver.y = {food[0][2]}; step(1 / 60)")
    aino.evaluate("G.hold = false")
    ville.evaluate("G.hold = false")
    aino.wait_for_function("G.carry.length === 1")
    ville.wait_for_function("$('toast').textContent === 'Aino ehti ensin'")
    assert ville.evaluate("G.carry.length") == 0
    ville.wait_for_function(f"!itemHere(ITEMS.find(it => it.id === '{food[0][0]}'))")
    ville.evaluate(f"diver.x = {food[1][1]}; diver.y = {food[1][2]}")
    ville.wait_for_function("G.carry.length === 1")
    # SISU holds still while friends are out, and the helm says why.
    x0 = host.evaluate("sub.x")
    host.evaluate("input.x = 1")
    host.wait_for_function("$('toast').textContent.startsWith('Odota: ')")
    host.evaluate("input.x = 0")
    assert abs(host.evaluate("sub.x") - x0) < 0.5
    # Ville runs out of air: only his haul is lost, and his find waits in place again.
    health = host.evaluate("G.s.m.health")
    ville.evaluate("diver.air = 0.01")
    ville.wait_for_function("G.mode === 'home'")
    assert "Happi loppui" in ville.inner_text("#card")
    host.wait_for_function(f"!G.held['{food[1][0]}'] && G.s.m.health < {health - 20}")
    assert aino.evaluate("[G.mode, G.carry.length]") == ["dive", 1]
    # Aino swims home: her find goes into the host's stores.
    aino.evaluate("diver.x = airlock().x; diver.y = airlock().y; drawHud()")
    aino.click("#act")
    host.wait_for_function("G.s.inv.ruoka === 1")
    aino.wait_for_function("$('toast').textContent.startsWith('Kotona')")
    assert aino.evaluate("[G.mode, crew.room]") == ["home", "ilmalukko"]
    for p in (host, aino, ville):
        assert p.errors == []


def test_the_night_comes_when_everyone_is_in_the_bunk_room_and_every_phone_gets_the_day(site, browser):
    host, aino, ville = room(site, browser)
    close_cards(host, aino, ville)
    host.click("#home")
    close_cards(host)
    stand(host, "punkka")
    stand(aino, "punkka")
    host.wait_for_function("Object.values(net.others).filter(o => o.mode === 'home').length === 2")
    host.wait_for_function("people().filter(p => p.room === 'punkka').length === 2")
    aino.click("#act")
    aino.wait_for_function("$('toast').textContent === 'Kaikki punkkaan: odotetaan Ville'")
    assert host.evaluate("G.s.day") == 4
    stand(ville, "punkka")
    host.wait_for_function("people().every(p => p.room === 'punkka')")
    aino.click("#act")
    for p in (host, aino, ville):
        p.wait_for_function("G.s.day === 5 && $('card').textContent.includes('Päivä 5')")


def test_the_radio_s_last_signal_shows_on_every_phone(site, browser):
    host, aino, ville = room(site, browser, saves=[save_with(inv={"vahvistin": 1, "antenni": 1}), None, None])
    close_cards(host, aino, ville)
    stand(aino, "ohjaamo")
    aino.wait_for_function("G.s.inv.antenni === 1")
    aino.evaluate("drawHud()")
    aino.click("#act2")
    for p in (host, aino, ville):
        p.wait_for_function("$('card').textContent.includes('Viimeinen signaali')")
    assert host.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).flags.end") is True
    # Each phone closes its own card: chapter 2 opens on Ville's, the others keep theirs.
    ville.click("#card button:has-text('Luku 2')")
    assert "Mannerrinne" in ville.inner_text("#card")
    assert "Viimeinen signaali" in aino.inner_text("#card")


def test_a_friend_whose_page_reloads_is_back_in_the_game(site, browser):
    host, aino, ville = room(site, browser)
    close_cards(host, aino, ville)
    ville.reload()
    ville.wait_for_function("typeof G === 'object' && G.s && G.mode === 'home'", timeout=10000)
    assert ville.evaluate("[G.s.day, crew.room]") == [4, "ohjaamo"]
    host.wait_for_function("Object.values(net.others).every(o => o.mode === 'home')")
    assert ville.evaluate(f"localStorage.getItem('{SAVE}')") is None


def test_the_host_takes_everyone_to_the_room_and_the_next_round_goes_on_with_the_same_save(site, browser):
    host, aino = room(site, browser, names=("Eero", "Aino"))
    close_cards(host, aino)
    host.click("#home")
    close_cards(host)
    stand(host, "kartta")
    assert host.inner_text("#act2") == "👥 Huoneeseen"
    host.click("#act2")
    for p in (host, aino):
        p.wait_for_function("!document.getElementById('aipr').hidden && G.mode === 'menu'")
    host.click("#aipr-start")
    for p in (host, aino):
        p.wait_for_function("G.s && G.s.day === 4 && G.mode !== 'wait' && G.mode !== 'menu'")
    assert host.evaluate("G.mode") == "sub"


@pytest.mark.parametrize("w,h", [(740, 360), (390, 844)])
def test_it_fits_sideways_and_on_a_390_px_phone_with_friends(site, browser, w, h):
    host, aino = room(site, browser, names=("Eero", "Aino"), w=w, h=h)
    assert aino.evaluate(v4.OVERFLOW) == []
    close_cards(host, aino)
    stand(aino, "kartta")
    assert aino.evaluate(v4.OVERFLOW) == []


def test_when_the_host_s_page_reloads_everyone_goes_back_to_the_room_and_the_game_goes_on(site, browser):
    host, aino = room(site, browser, names=("Eero", "Aino"))
    close_cards(host, aino)
    host.reload()
    host.wait_for_function("typeof G === 'object' && AiPelitRooms.isHost && !document.getElementById('aipr').hidden")
    aino.wait_for_function("G.mode === 'menu' && !document.getElementById('aipr').hidden")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    for p in (host, aino):
        p.wait_for_function("G.s && G.s.day === 4 && G.mode !== 'wait' && G.mode !== 'menu'")
    assert aino.evaluate(f"localStorage.getItem('{SAVE}')") is None
    for p in (host, aino):
        assert p.errors == []


def test_four_phones_play_one_game_each_as_their_own_person(site, browser):
    pages = room(site, browser, names=("Eero", "Aino", "Ville", "Sanni"))
    host, guests = pages[0], pages[1:]
    close_cards(*pages)
    # Everyone is in the host's game, each friend their own person in their own colour, the host at the helm.
    assert host.evaluate("[G.mode, G.s.day]") == ["sub", 4]
    assert sorted(host.evaluate("Object.values(net.others).map(o => o.name)")) == ["Aino", "Sanni", "Ville"]
    assert len(set(host.evaluate("Object.values(net.cols)"))) == 4
    # Each goes their own way: one eats, one puts on a suit, one goes to the bunk.
    for g, r in zip(guests, ["keittio", "puvut", "punkka"]):
        stand(g, r)
    guests[0].click("#act")
    guests[1].click("#act")
    host.wait_for_function("G.s.inv.ruoka === 0")
    host.wait_for_function("""people().map(p => p.room).sort().join() === ',keittio,punkka,puvut'""")
    for g in guests[1:]:
        g.wait_for_function("Object.values(net.others).filter(o => o.mode === 'home').length === 2")
    # Sanni sees Ville in his suit.
    guests[2].wait_for_function("Object.values(net.others).find(o => o.name === 'Ville').suit")
    # Only the host's save is written.
    for g in guests:
        assert g.evaluate(f"localStorage.getItem('{SAVE}')") is None
    host.wait_for_function(f"JSON.parse(localStorage.getItem('{SAVE}')).inv.ruoka === 0")
    for p in pages:
        assert p.errors == []
