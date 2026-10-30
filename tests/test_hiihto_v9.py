"""Hiihto v9 (#103): v7's 3D, with finer skiers, smoother animation, drawn spruces and ski grooves."""

import io
import json

import pytest
from PIL import Image

from conftest import ROOT, wait_for_worker
from test_hiihto import BOT
from test_rooms_lib import Relay

URL = "games/hiihto/v9/"


def open_game(site, context, url=URL):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{url}")
    page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
    return page


def wait_3d(page):
    page.wait_for_function("!!V3 || no3d", timeout=15000)
    # Headless Chromium draws WebGL in software; without it the game still plays, and says so.
    if page.evaluate("no3d"):
        pytest.skip("this Chromium has no WebGL")


def colours(page):
    img = Image.open(io.BytesIO(page.screenshot())).convert("RGB").resize((36, 74))
    return len(img.getcolors(1 << 16))


def test_the_trail_skiers_and_spruces_are_drawn_in_3d(site, context):
    page = open_game(site, context)
    wait_3d(page)
    page.evaluate("chooseWax(bestWax(course.weather.T)); mode = 'race'; P.z = 30; P.v = 4; for (let i = 0; i < 30; i++) step(1 / 60); draw()")
    world = page.evaluate("""() => ({
      trees: V3.world.children.filter(o => o.isInstancedMesh).map(o => o.count),
      rigs: V3.rigs.size, me: V3.rigs.has(P), others: npcs.filter(o => o.z > P.z - 6 && o.z < P.z + 170).length,
      shadows: V3.renderer.shadowMap.enabled && V3.sun.castShadow,
      behind: V3.camera.position.z > -P.z && V3.camera.position.y > heightAt(P.z) })""")
    # The spruces beside the trail and a forest further out, a skier for each one in sight, the
    # camera behind and above the player's own skier.
    assert len(world["trees"]) == 2 and min(world["trees"]) > 100
    assert world["me"] and world["rigs"] == world["others"] + 1
    assert world["shadows"] and world["behind"]
    # The 2D canvas over it is see-through: the picture is the 3D world, not one flat colour.
    assert colours(page) > 40
    assert page.errors == []


def test_saves_from_v6_carry_on(site, context):
    context.add_init_script("""if (!sessionStorage.seeded) { sessionStorage.seeded = 1;
      localStorage.setItem('ai-pelit:hiihto:taso', '3'); localStorage.setItem('ai-pelit:hiihto:tyyli', '"luistelu"');
      localStorage.setItem('ai-pelit:hiihto:ajat', '{"1":200}'); localStorage.setItem('ai-pelit:hiihto:luistelu-ajat', '{"2":150}'); }""")
    page = open_game(site, context)
    assert page.evaluate("[maxLevel, level, style, bests[1], sBests[2]]") == [3, 3, "luistelu", 200, 150]
    # A race won in v7 saves where v6 keeps it.
    page.evaluate("setStyle('perinteinen'); level = 1; newRace()")
    r = page.evaluate(BOT)
    assert r["mode"] == "done" and r["stars"] >= 1, r
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:hiihto:ajat'))[1]") < 200
    assert page.evaluate("localStorage.getItem('ai-pelit:hiihto:taso')") == "3"
    assert page.errors == []


@pytest.mark.parametrize("st", ["perinteinen", "luistelu"])
def test_a_whole_race_draws_every_moment(site, context, st):
    page = open_game(site, context)
    wait_3d(page)
    # Level 3 has the road: on foot, the skis on the shoulder, then on again.
    page.evaluate(f"style = '{st}'; level = 3; newRace()")
    # The bot never changes lanes, so nobody else is on the trail (others are drawn in other tests).
    run = """() => { chooseWax(bestFor(style, course.weather.T)); countT = 0; step(1 / 60);
      npcs = []; nextVasta = nextSkate = 1e9;
      const seen = new Set(); let next = 0;
      for (let i = 0; i < 60 * 900 && mode === 'race'; i++) {
        const g = gradeAt(P.z + 2);
        if (onRoad(P)) { if (P.t >= next) { roadTap(P); next = P.t + 0.5; } }
        else { P.vMode = style === 'perinteinen' && g > 0.075; P.hold = g < -0.02;
          if (!P.hold && P.t >= next) { style === 'luistelu' ? push(P, -P.side) : kick(P); next = P.t + 0.38; } }
        physics(P, 1 / 60); world(1 / 60); if (P.z >= course.len) finish();
        if (i % 20 === 0) seen.add(P.road || (P.fallT > 0 ? 'fall' : P.hold ? 'tuck' : P.vMode ? 'vee' : 'ski'));
        // Every moment that changes the picture is drawn, the rest now and then: software WebGL is slow.
        if (i % 150 === 0 || (onRoad(P) && i % 10 === 0)) draw();
      }
      draw();
      return { mode, seen: [...seen] };
    }"""
    r = page.evaluate(run)
    assert r["mode"] == "done"
    assert {"walk", "done", "tuck"} <= set(r["seen"]), r
    assert page.errors == []


def test_speech_bubbles_sit_over_the_skier_who_speaks(site, context):
    page = open_game(site, context)
    wait_3d(page)
    page.evaluate("chooseWax(1); mode = 'race'; npcs = []; addGranny(P.z + 10); say(npcs[0], 'Hei!'); draw()")
    p = page.evaluate("screenOf(npcs[0].z, npcs[0].x, 2.0)")
    assert 0 < p["x"] < 360 and 100 < p["y"] < 600, p
    # The granny is ahead on the player's own track: the bubble is over the middle of the screen.
    assert abs(p["x"] - 180) < 90


def test_a_tap_on_a_button_as_it_shows_presses_it(site, browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = open_game(site, ctx)
    page.evaluate("c.style.cssText = 'top:0;height:110%'; resize()")
    page.wait_for_function("H === c.getBoundingClientRect().height")
    b = page.evaluate("""() => { draw(); const b = ui.styles[1], r = c.getBoundingClientRect();
      return [r.left + (b.x + b.w / 2) * r.width / W, r.top + (b.y + b.h / 2) * r.height / H]; }""")
    page.touchscreen.tap(*b)
    assert page.evaluate("style") == "luistelu"
    assert page.errors == []
    ctx.close()


def test_it_plays_in_3d_offline(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(f"{site.url}{URL}")
    wait_3d(page)
    context.set_offline(True)
    try:
        page.goto(f"{site.url}{URL}")
        page.wait_for_function("!!V3 || no3d", timeout=15000)
        assert page.evaluate("!!V3")
    finally:
        context.set_offline(False)


def test_a_friend_skis_in_3d_in_their_colour(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    pages = []
    for name in ["Eero", "Aino"]:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.wait_for_function("typeof course === 'object'")
        pages.append(page)
    host, guest = pages
    host.evaluate("draw(); down(1, ui.friends.x + 5, ui.friends.y + 5); up(1, ui.friends.x + 5, ui.friends.y + 5)")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest.evaluate("AiPelitRooms.open()")
    guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("net && net.cfg && mode === 'wax'", timeout=6000)
        wait_3d(p)
        p.evaluate("draw(); const r = ui.wax[bestFor(style, course.weather.T)]; down(1, r.x + 5, r.y + 5); up(1, r.x + 5, r.y + 5)")
    # Software WebGL draws two pages slowly, and a frame moves the clock at most 0.05 s: no countdown.
    host.wait_for_function("mode === 'count'", timeout=20000)
    host.evaluate("countT = 0")
    for p in pages:
        p.wait_for_function("mode === 'race'", timeout=20000)
        p.evaluate("npcs = []; nextVasta = nextSkate = 1e9")
    guest.evaluate("P.z = 30")
    host.evaluate("P.z = 20")
    host.wait_for_function("net.skiers[1].z > 25", timeout=15000)
    host.evaluate("draw()")
    friend = host.evaluate("""() => { const k = net.skiers[1], r = V3.rigs.get(k);
      return r && [r.root.visible, r.mats.coat.color.equals(new THREE.Color(k.color))]; }""")
    assert friend == [True, True]
    assert host.errors == guest.errors == []
    for p in pages:
        p.context.close()


def test_each_ski_has_a_groove_in_the_classic_tracks(site, context):
    page = open_game(site, context)
    wait_3d(page)
    page.evaluate("level = 3; newRace(); draw()")
    # A groove under each of the player's skis, cut 4 cm into the snow, and none on the road.
    r = page.evaluate("""() => [GROOVES.map(g => lifted(100, g)), lifted(100, LX[1]),
      lifted(course.road.z0 + 4, GROOVES[2]), GROOVES[3] - GROOVES[2]]""")
    assert all(abs(d + 0.04) < 1e-9 for d in r[0]) and r[1] == 0 and r[2] == 0
    assert abs(r[3] - 0.24) < 1e-9


def test_the_skier_blends_from_one_pose_to_the_next(site, context):
    page = open_game(site, context)
    wait_3d(page)
    page.evaluate("chooseWax(1); mode = 'race'; npcs = []; nextVasta = nextSkate = 1e9; P.z = 30; draw()")
    # A fall tips the skier over over a few frames, not at once.
    falls = page.evaluate("""() => { P.fallT = 1.6; const r = V3.rigs.get(P), out = [];
      for (let i = 0; i < 6; i++) { V3.last = performance.now() - 33; draw(); out.push(r.sm.fall); } return out; }""")
    assert 0 < falls[0] < 0.5 and falls == sorted(falls) and falls[-1] > 0.8
    # The stride: after a kick the drawn skis swing from one side to the other, and stay there
    # while gliding (left ski ahead is positive).
    stride = page.evaluate("""() => { P.fallT = 0; P.invT = 0; const r = V3.rigs.get(P);
      const at = d => { P.side = 1; P.lastKick = P.t - d;
        for (let i = 0; i < 12; i++) { V3.last = performance.now() - 33; draw(); }
        return r.skis[0].position.z - r.skis[1].position.z; };
      return [0, 0.6].map(at); }""")
    assert stride[0] < -0.4 and stride[1] > 0.4, stride
    assert page.errors == []


def test_a_phone_held_at_30_frames_keeps_its_full_picture(site, context):
    page = open_game(site, context)
    wait_3d(page)
    # A screen capped at 30 a second (battery saving) is not slow: nothing steps down.
    r = page.evaluate("""() => { mode = 'race'; V3.tuned = false; V3.warm = false; V3.tt = V3.tn = 0;
      const pr = V3.renderer.getPixelRatio(); for (let i = 0; i < 400; i++) tune(1000 / 30);
      return [pr, V3.renderer.getPixelRatio(), V3.renderer.shadowMap.enabled, V3.tuned]; }""")
    assert r[0] == r[1] and r[2] is True and r[3] is True
    # A phone at 15 a second draws fewer pixels.
    r = page.evaluate("""() => { V3.tuned = false; V3.warm = true; V3.tt = V3.tn = 0; V3.renderer.setPixelRatio(2);
      for (let i = 0; i < 60; i++) tune(1000 / 15); return V3.renderer.getPixelRatio(); }""")
    assert r == 1.5
