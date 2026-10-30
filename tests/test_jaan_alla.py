"""Jään alla, the story survival game under the ice on the shared three.js (#106), in a phone-sized Chromium."""

import pytest

from conftest import ROOT

URL = "games/jaan-alla/v1/"
SAVE = "ai-pelit:jaan-alla:peli"

# Steps the game by hand, 1/60 s at a time, while cond() holds or max seconds pass.
RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"


def open_game(site, context, save=None):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    if save:
        page.goto(site.url + URL)
        page.evaluate(f"localStorage.setItem('{SAVE}', JSON.stringify({save}))")
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=15000)
    # Headless Chromium draws WebGL in software (SwiftShader); without it the page says so instead.
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    page.evaluate(RUN)
    return page, errors


def new_game(site, context):
    page, errors = open_game(site, context)
    page.click("#uusi")
    page.click("#card button:has-text('Sukella!')")
    # The tests step the game themselves; the page keeps drawing.
    page.evaluate("G.hold = true; input.x = input.y = 0; input.up = input.down = false")
    return page, errors


def test_a_new_game_tells_the_story_and_points_at_the_station(site, context):
    page, errors = open_game(site, context)
    assert page.is_hidden("#jatka")
    page.click("#uusi")
    assert "SISU" in page.inner_text("#card")
    page.click("#card button:has-text('Sukella!')")
    page.evaluate("drawHud()")
    assert page.inner_text("#goal").startswith("Tavoite: Telakoidu Aurora-asemalle")
    assert page.is_visible("#stick") and page.is_visible("#up") and page.is_visible("#down")
    assert page.is_hidden("#mAir")
    assert errors == []


def test_the_stick_drives_sisu_forward_and_it_uses_power(site, context):
    page, _ = new_game(site, context)
    z0, p0 = page.evaluate("[sub.pos.z, G.s.m.power]")
    page.evaluate("input.y = 1; run(() => true, 3); input.y = 0")
    z1, p1 = page.evaluate("[sub.pos.z, G.s.m.power]")
    assert z1 < z0 - 15
    assert p1 < p0
    # Down sinks it, and the floor stops it.
    page.evaluate("input.down = true; run(() => true, 30); input.down = false")
    assert page.evaluate("sub.pos.y >= floorY(sub.pos.x, sub.pos.z) + 2.3")


def test_ramming_the_floor_hurts_the_hull_and_a_wreck_of_a_hull_goes_home(site, context):
    page, _ = new_game(site, context)
    page.evaluate("sub.pos.set(-100, floorY(-100, -100) + 4, -100); sub.vel.set(0, -14, 0); run(() => G.s.m.hull === 100, 0.5)")
    assert page.evaluate("G.s.m.hull") < 100
    page.evaluate("G.s.m.hull = 1; sub.pos.set(-100, floorY(-100, -100) + 4, -100); sub.vel.set(0, -14, 0); run(() => G.s.m.hull === 1, 0.5)")
    assert page.evaluate("[G.s.m.hull, Math.round(sub.pos.x), G.mode]") == [40, 0, "sub"]
    assert "SISU vaurioitui" in page.inner_text("#card")


def test_docking_at_the_station_reads_the_log_and_saves(site, context):
    page, errors = new_game(site, context)
    page.evaluate("input.y = 1; run(() => !currentAction(), 10); input.y = 0; drawHud()")
    assert page.inner_text("#act") == "Telakoidu asemalle"
    page.click("#act")
    assert page.inner_text("#card h2") == "Aurora-asema A-3"
    page.click("#card button:has-text('Ohjauskeskus')")
    assert "RV Nordlysiin" in page.inner_text("#card")
    page.click("#card button:has-text('Takaisin')")
    page.click("#card button:has-text('Varasto')")
    assert page.evaluate("[G.s.inv.ruoka, G.s.inv.romu]") == [4, 1]
    page.click("#card button:has-text('Lähde telakasta')")
    page.evaluate("drawHud()")
    assert "RV Nordlys" in page.inner_text("#goal")
    saved = page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}'))")
    assert saved["flags"]["stationLog"] is True and saved["varasto"] is True
    assert errors == []


def test_every_thing_inside_every_place_can_be_reached_from_the_airlock(site, context):
    page, _ = open_game(site, context)
    lost = page.evaluate("""() => {
        const out = [];
        for (const id in SITES) {
            const m = SITES[id].map, seen = new Set();
            let r0 = m.findIndex(row => row.includes('E')), todo = [[m[r0].indexOf('E'), r0]];
            while (todo.length) {
                const [c, r] = todo.pop(), k = c + ',' + r;
                if (seen.has(k) || !m[r] || !m[r][c] || m[r][c] === '#') continue;
                seen.add(k);
                todo.push([c + 1, r], [c - 1, r], [c, r + 1], [c, r - 1]);
            }
            m.forEach((row, r) => [...row].forEach((ch, c) => { if (ch !== '#' && !seen.has(c + ',' + r)) out.push(id + ' ' + c + ',' + r); }));
            if (new Set(m.map(row => row.length)).size !== 1) out.push(id + ' ragged');
        }
        return out;
    }""")
    assert lost == []


def test_diving_into_nordlys_finds_the_log_and_scrap_and_comes_back(site, context):
    page, errors = new_game(site, context)
    page.evaluate("G.s.flags.stationLog = true; sub.pos.set(SITES.nordlys.door.x, SITES.nordlys.door.y, SITES.nordlys.door.z + 5); drawHud()")
    assert page.inner_text("#act") == "Sukella ulos: RV Nordlys"
    page.click("#act")
    assert page.evaluate("[G.mode, G.s.m.air]") == ["dive", 100]
    page.evaluate("drawHud()")
    assert page.is_visible("#mAir")
    # Swim along the corridor: air runs down, and the scrap in the workshop (7,1) is picked up on touch.
    page.evaluate("input.y = 1; run(() => true, 2); input.y = 0")
    assert page.evaluate("G.s.m.air") < 100
    page.evaluate("diver.pos.set(7 * 4 + 2, 1.3, 1 * 4 + 2); step(1 / 60)")
    assert page.evaluate("G.s.inv.romu") == 1
    page.evaluate("diver.pos.set(13 * 4 + 2, 1.3, 1 * 4 + 2); step(1 / 60)")
    assert page.evaluate("G.s.flags.nordlysLog") is True
    assert "jäävuoren luoliin" in page.inner_text("#card")
    page.click("#card button:has-text('Jatka')")
    # Taken things stay taken.
    page.evaluate("leaveSite(); enterSite('nordlys')")
    assert page.evaluate("items.filter(i => i.k === 'R' || i.k === 'L').length") == 2
    page.evaluate("diver.pos.set(1 * 4 + 2, 1.8, 3 * 4 + 2); drawHud()")
    assert page.inner_text("#act") == "Palaa SISUun"
    page.click("#act")
    assert page.evaluate("G.mode") == "sub"
    assert errors == []


def test_running_out_of_air_brings_the_diver_back_and_air_pockets_refill(site, context):
    page, _ = new_game(site, context)
    page.evaluate("enterSite('jaavuori'); diver.pos.set(7 * 4 + 2, 2, 1 * 4 + 2); G.s.m.air = 30; run(() => true, 1)")
    assert page.evaluate("G.s.m.air") > 60
    page.evaluate("diver.pos.set(4 * 4 + 2, 2, 2 * 4 + 2); G.s.m.air = 1; run(() => G.mode === 'dive', 3)")
    assert page.evaluate("G.mode") == "sub"
    assert "Ilma loppui" in page.inner_text("#card")


def test_the_squid_grabs_sisu_near_the_crystal_cave(site, context):
    page, _ = new_game(site, context)
    page.evaluate("squid.state = 'patrol'; sub.pos.copy(squid.pos); sub.pos.x += 10; sub.pos.y = Math.max(sub.pos.y, floorY(sub.pos.x, sub.pos.z) + 3)")
    page.evaluate("run(() => G.s.m.hull === 100, 10)")
    assert page.evaluate("[G.s.m.hull, squid.state]") == [80, "back"]


def test_fish_and_kelp_feed_the_pilot_and_eating_fills_the_food_meter(site, context):
    page, _ = new_game(site, context)
    page.evaluate("const s = SCHOOLS[0]; sub.pos.set(s.x, s.y, s.z); step(1 / 60); step(1 / 60)")
    assert page.evaluate("G.s.inv.ruoka") == 3
    page.evaluate("sub.pos.set(KELP.x, floorY(KELP.x, KELP.z) + 6, KELP.z); step(1 / 60)")
    assert page.evaluate("G.s.inv.ruoka") == 4
    page.evaluate("G.s.m.food = 10; drawHud()")
    page.click("#bag")
    page.click("#card button:has-text('Syö')")
    assert page.evaluate("[G.s.inv.ruoka, Math.round(G.s.m.food)]") == [3, 45]


def test_bringing_the_antenna_crystal_and_scrap_home_fixes_the_radio_and_ends_chapter_one(site, context):
    page, _ = new_game(site, context)
    page.evaluate("Object.assign(G.s.flags, { stationLog: true, nordlysLog: true, jaavuoriLog: true }); G.s.inv.antenni = 1")
    page.evaluate("drawHud()")
    assert "kristalli" in page.inner_text("#goal")
    page.evaluate("G.s.inv.kristalli = 1; G.s.inv.romu = 1; dock()")
    page.click("#card button:has-text('Radiomasto')")
    assert "2 romua" in page.inner_text("#card")
    page.evaluate("G.s.inv.romu = 2")
    page.click("#card button:has-text('Radiomasto')")
    assert page.inner_text("#card h2") == "Radio toimii!"
    assert "Luku 1 päättyi" in page.inner_text("#card")
    assert page.evaluate("[G.s.flags.radio, G.s.inv.romu, localStorage.getItem('ai-pelit:jaan-alla:luku1') !== null]") == [True, 0, True]


def test_continue_picks_up_the_saved_game(site, context):
    save = "{v: 1, t: 300, flags: {stationLog: true}, inv: {ruoka: 5, romu: 3, antenni: 0, kristalli: 0}, sub: {x: -50, y: -30, z: -60, yaw: 1}}"
    page, errors = open_game(site, context, save)
    assert page.is_visible("#jatka")
    page.click("#jatka")
    assert page.evaluate("[G.mode, Math.round(sub.pos.x), G.s.inv.romu, G.s.m.hull]") == ["sub", -50, 3, 100]
    page.evaluate("drawHud()")
    assert "RV Nordlys" in page.inner_text("#goal")
    # A new game asks once more before it replaces the save.
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true")
    page.click("#uusi")
    assert "Paina uudelleen" in page.inner_text("#uusi")
    assert errors == []


def test_things_found_out_of_order_still_count_and_a_reload_mid_dive_resumes_in_sisu(site, context):
    page, _ = new_game(site, context)
    # The crystal first, before any log: kept, and the goal still starts from the station.
    page.evaluate("enterSite('kristalli'); diver.pos.set(1 * 4 + 2, 1.3, 5 * 4 + 2); step(1 / 60)")
    assert page.evaluate("G.s.inv.kristalli") == 1
    page.click("#card button:has-text('Jatka')")
    page.evaluate("drawHud()")
    assert "Aurora-asemalle ja lue" in page.inner_text("#goal")
    # Fish and kelp at once both count.
    page.evaluate("leaveSite(); SCHOOLS[1].x = KELP.x; SCHOOLS[1].z = KELP.z; SCHOOLS[1].y = floorY(KELP.x, KELP.z) + 6;"
                  "sub.pos.set(KELP.x, SCHOOLS[1].y, KELP.z); const n = G.s.inv.ruoka; step(1 / 60); window.got = G.s.inv.ruoka - n")
    assert page.evaluate("got") == 2
    # With every log read, the crystal step is skipped straight to the radio.
    page.evaluate("Object.assign(G.s.flags, { stationLog: true, nordlysLog: true, jaavuoriLog: true }); G.s.inv.antenni = 1; drawHud()")
    assert "korjaa radiomasto" in page.inner_text("#goal")
    # A reload while diving continues in SISU with what was found.
    page.evaluate("enterSite('nordlys'); saveGame()")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.click("#jatka")
    assert page.evaluate("[G.mode, G.s.inv.kristalli, G.s.inv.antenni]") == ["sub", 1, 1]


@pytest.mark.parametrize("width,height", [(360, 640), (390, 844)])
def test_the_controls_and_meters_fit_a_small_phone(site, browser, width, height):
    phone = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
    page, _ = new_game(site, phone)
    page.evaluate("G.s.flags.stationLog = true; sub.pos.set(SITES.nordlys.door.x, SITES.nordlys.door.y, SITES.nordlys.door.z + 5); drawHud()")
    # In SISU the bag button shows; in a dive the air meter makes four meters.
    bag = page.evaluate("document.getElementById('bag').getBoundingClientRect().left")
    page.evaluate("enterSite('nordlys'); diver.pos.set(1 * 4 + 2, 1.8, 3 * 4 + 2); drawHud()")  # at the airlock
    box = page.evaluate("""() => {
        const r = id => document.getElementById(id).getBoundingClientRect();
        const tops = [...document.querySelectorAll('#meters .m')].map(m => Math.round(m.getBoundingClientRect().top));
        return { rows: new Set(tops).size, meters: r('meters').right, goal: r('goalbar').bottom,
                 stick: r('stick'), up: r('up'), act: r('act'), w: innerWidth, h: innerHeight };
    }""")
    assert box["rows"] == 1
    assert 0 < box["meters"] <= bag
    for k in ("stick", "up", "act"):
        assert 0 <= box[k]["left"] and box[k]["right"] <= box["w"] and box[k]["bottom"] <= box["h"], k
        assert box[k]["top"] > box["goal"], k
    assert box["stick"]["right"] < box["act"]["left"]
    phone.close()
