"""Last Signal v9 (#160): a chart of the whole sea in the navigation room, filled in by exploring (contacts heard, then
known, then seen), an autopilot set from it that drives SISU in real time while the person walks inside, and the
iceberg's caves as a dark maze of short passages that only a lamp lights, its walls staying drawn once lit.
Otherwise v9 plays as v8: v8's tests (and through them v7's, v6's, v5's and v4's) run here on v9 too."""

import json

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
import test_last_signal_v6 as v6
import test_last_signal_v7 as v7
import test_last_signal_v8 as v8
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)

URL = "games/last-signal/v9/"
SAVE = v4.SAVE


@pytest.fixture(autouse=True)
def _v9(monkeypatch):
    for m in (v4, v5, v6, v7, v8):
        monkeypatch.setattr(m, "URL", URL)


# v8's tests (with v7's, v6's, v5's and v4's), on v9, but for the ones about the navigation room's buttons (the chart
# is its first button now, the lab its second, and the logbook and the host's way back to the room are in the lab's
# card) and the iceberg's old great hall. The tests below cover those.
CHANGED = ("test_samples_are_studied_in_the_lab_for_a_lasting_help", "test_the_harpoon_lab_and_galley_fit_upright_and_sideways",
           "test_the_host_takes_everyone_to_the_room_and_the_next_round_goes_on_with_the_same_save",
           "test_inside_nordlys_the_rooms_are_named_and_the_iceberg_hall_widens_the_view")
for _name in dir(v8):
    if _name.startswith("test_") and not _name.startswith(CHANGED):
        globals()[_name + "_v8"] = getattr(v8, _name)


def act(page, text):
    """v8's act; the logbook is in the lab's card since v9."""
    if text == "Lokikirja":
        v8.act(page, "Laboratorio")
        page.click("#card button:has-text('Lokikirja')")
        return
    v8.act(page, text)


@pytest.fixture(autouse=True)
def _helpers(monkeypatch):
    monkeypatch.setattr(v4, "act", act)
    monkeypatch.setattr(v4, "dive_at", v7.dive_at)


open_game, inside, walk = v4.open_game, v4.inside, v4.walk
ready, toast = v6.ready, v6.toast

# Glides this phone's diver along the maze from the way in to crossing `n`, as a swim along the passages would, the
# lamp facing the way it goes.
GLIDE = """(n) => {
  const adj = new Map();
  for (const [a, b] of MAZE.edges) { adj.set(a, (adj.get(a) || []).concat(b)); adj.set(b, (adj.get(b) || []).concat(a)); }
  const start = 4 * MAZE.cols, prev = new Map([[start, -1]]), q = [start];
  for (let h = 0; h < q.length; h++) for (const m of adj.get(q[h]) || []) if (!prev.has(m)) { prev.set(m, q[h]); q.push(m); }
  const path = []; for (let k = n; k !== -1 && k != null; k = prev.get(k)) path.unshift(MAZE_P[k]);
  const pts = [[2075, 49.5], [2090, 48.5]].concat(path);
  for (let k = 1; k < pts.length; k++) {
    const [ax, ay] = pts[k - 1], [bx, by] = pts[k], n2 = Math.ceil(Math.hypot(bx - ax, by - ay) / 0.1);
    for (let s = 1; s <= n2; s++) {
      diver.x = ax + (bx - ax) * s / n2; diver.y = ay + (by - ay) * s / n2;
      const a = Math.atan2(by - ay, bx - ax); diver.dir = Math.cos(a) >= 0 ? 1 : -1;
      diver.ang = diver.dir > 0 ? a : Math.PI - a; if (diver.ang > Math.PI) diver.ang -= 2 * Math.PI;
      diver.air = 60; step(1 / 60); if (G.paused) closeCard();
    }
  }
  return path.length;
}"""


def cave_dive(page):
    page.evaluate("const s = BERG_SITE; sub.x = s.spot[0]; sub.y = s.spot[1]; sub.vx = sub.vy = 0; G.mode = 'home';"
                  " crew.suit = true; crew.kit = 'tank'; startDive(); if (G.paused) closeCard()")
    assert page.evaluate("G.mode") == "dive"


def chart(page):
    """Inside SISU, to the navigation room and its chart."""
    if page.evaluate("G.mode") != "home":
        inside(page)
    walk(page, "kartta")
    assert page.inner_text("#act") == "🗺️ Merikartta"
    page.click("#act")
    assert page.is_visible("#chart")
    first_card(page)


def first_card(page):
    """The chart's own card the first time it opens: what its marks mean."""
    if page.is_visible("#panel"):
        assert "❓ sonar kuuli" in page.inner_text("#card")
        page.click("#card button:has-text('Selvä')")
        assert page.evaluate("G.paused") is True


# ---------- the maze ----------

def test_the_iceberg_caves_are_a_maze_of_short_narrow_passages_with_dead_ends(site, browser):
    page = open_game(site, browser)
    ready(page)
    m = page.evaluate("""(() => {
      const lens = MAZE.edges.map(([a, b]) => Math.hypot(MAZE_P[a][0] - MAZE_P[b][0], MAZE_P[a][1] - MAZE_P[b][1]));
      const deg = {}; for (const [a, b] of MAZE.edges) { deg[a] = (deg[a] || 0) + 1; deg[b] = (deg[b] || 0) + 1; }
      return { n: MAZE.edges.length, longest: Math.max(...lens), widest: Math.max(...BERG.caves.map(c => c[4])),
        ends: Object.values(deg).filter(d => d === 1).length, nodes: MAZE_P.filter(Boolean).length }; })()""")
    # every crossing joined, a few loops, each passage one step of the maze, and plenty of dead ends
    assert m["nodes"] - 1 <= m["n"] <= m["nodes"] + 6
    assert m["longest"] < 10 and m["widest"] <= 5.5 and m["ends"] >= 8
    # the same maze on every phone: it comes from a fixed seed
    first = page.evaluate("JSON.stringify(MAZE.edges)")
    page.reload()
    page.wait_for_function("window.drawn === true")
    assert page.evaluate("JSON.stringify(MAZE.edges)") == first
    # the passages are water and the ice between them solid, and SISU cannot squeeze in
    assert page.evaluate("MAZE.edges.every(([a, b]) => !diverHits((MAZE_P[a][0] + MAZE_P[b][0]) / 2, (MAZE_P[a][1] + MAZE_P[b][1]) / 2))")
    assert page.evaluate("subHits(2110, 46)") is True
    assert page.errors == []


def test_every_cave_find_is_at_its_own_place_and_reachable_with_air_to_spare(site, browser):
    page = open_game(site, browser)
    ready(page)
    cave = page.evaluate("ITEMS.filter(it => it.site === 'jaavuori').map(it => [it.id, it.k, it.x, it.y])")
    # the same 17 finds as before, by the same numbers, so an old save's "taken" still means the same thing
    assert [c[0] for c in cave] == [f"jaavuori:{n}" for n in range(17)]
    assert [c[1] for c in cave] == ["ilma"] * 5 + ["ruoka", "osa", "ruoka", "loki", "antenni", "osa", "osa", "ruoka", "laake",
                                                   "osa", "loki", "nayte"]
    assert all(page.evaluate(f"!diverHits({x}, {y})") for _, _, x, y in cave)
    reach = page.evaluate(v4.REACH)["jaavuori"]
    for k, x, y, d in reach["items"]:
        assert d is not None, (k, x, y)
    assert page.errors == []


def test_inside_the_iceberg_it_is_dark_and_only_what_a_lamp_lights_shows(site, browser):
    page = open_game(site, browser)
    ready(page)
    cave_dive(page)
    assert page.evaluate("bergView()") is False  # still out in the open sea by the way in
    page.evaluate(f"({GLIDE})(4 * MAZE.cols + 1)")
    assert page.evaluate("bergView()") is True
    # The lamp's light stops at the ice: no ray of it ends inside a wall deeper than its glow on the face.
    deep = page.evaluate("""(() => { const l = lampOf(diver), p = lampPoly(l[0], l[1], l[2], 0.55, l[3], l[4]);
      let worst = 0; for (let k = 0; k < p.length; k += 2) worst = Math.max(worst, caveD(p[k], p[k + 1])); return worst; })()""")
    assert deep < 1.2
    # A find behind the ice does not show through it; one in plain sight does.
    assert page.evaluate("sightTo(diver.x, diver.y, ...MAZE_P[10 + 8 * MAZE.cols])") is False
    assert page.evaluate("sightTo(diver.x, diver.y, diver.x + 0.5, diver.y)") is True
    # The dark: the middle of the screen is lit, a far corner of the berg pitch black.
    px = page.evaluate("""(() => { draw(); const d = dctx.getImageData(0, 0, dark.width, dark.height).data, w = dark.width;
      const at = (x, y) => d[(Math.round(y * DPR) * w + Math.round(x * DPR)) * 4 + 3];
      const [fx, fy] = [G.view.ox + 2180 * G.view.sc, G.view.oy + 95 * G.view.sc];
      return [at(W / 2, H / 2), fx > 0 && fx < W && fy > 0 && fy < H ? at(fx, fy) : 255]; })()""")
    assert px[0] < 60 and px[1] > 250
    assert page.errors == []


def test_the_walls_a_lamp_lit_stay_drawn_and_are_saved(site, browser):
    page = open_game(site, browser)
    ready(page)
    assert page.evaluate("caveSeen.reduce((a, b) => a + b, 0)") == 0
    cave_dive(page)
    page.evaluate(f"({GLIDE})(10 + 1 * MAZE.cols)")
    lit = page.evaluate("caveSeen.reduce((a, b) => a + b, 0)")
    assert lit > 40
    # only what was lit: the far bottom corner of the maze is still unmapped
    assert page.evaluate("caveSeen[rvAt(...MAZE_P[0 + 8 * MAZE.cols])]") == 0
    page.evaluate("const a = airlock(); diver.x = a.x; diver.y = a.y; endDive(false); save()")
    saved = page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).cave")
    assert saved
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.evaluate(v4.RUN)
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard(); step(1 / 60)")
    assert page.evaluate("caveSeen.reduce((a, b) => a + b, 0)") == lit
    assert page.errors == []


# ---------- the chart ----------

def test_the_chart_opens_only_in_the_navigation_room_and_fills_in_as_the_sea_is_explored(site, browser):
    page = open_game(site, browser)
    v4.new_game(page)
    page.evaluate("step(1 / 60)")
    # Only the navigation room has it.
    inside(page)
    for room in ("keittio", "ohjaamo", "punkka", "paja", "varasto", "puvut"):
        walk(page, room)
        assert "Merikartta" not in page.inner_text("#pad")
    walk(page, "kartta")
    assert page.inner_text("#act") == "🗺️ Merikartta"
    assert page.inner_text("#act2") == "🔬 Laboratorio"
    page.click("#act")
    first_card(page)
    assert page.is_visible("#chart") and page.evaluate("G.paused") is True
    # At first only the sea round SISU is drawn; the far wrecks are unexplored.
    start = page.evaluate("chartSeen.reduce((a, b) => a + b, 0)")
    assert 0 < start < 60
    assert page.evaluate("chartSeen[Math.floor((1180 - CH.x0) / CH.s) + Math.floor((220 - CH.y0) / CH.s) * CH.w]") == 0
    page.click("#chartX")
    assert page.is_visible("#chart") is False and page.evaluate("G.paused") is False
    # A ping draws the floor round SISU onto the chart.
    page.evaluate("closeHome(); doPing(); step(1 / 60)")
    assert page.evaluate("chartSeen.reduce((a, b) => a + b, 0)") > start * 5
    page.evaluate("save()")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).chart.length") > 100
    assert page.errors == []


def test_a_contact_is_heard_then_known_then_seen(site, browser):
    page = open_game(site, browser)
    v4.new_game(page)
    page.evaluate("sub.x = 760; sub.y = 60; run(() => true, 0.3)")
    know = "knowOf(contacts().find(c => c.id === 'polaris'))"
    # Within the sonar's hearing the wreck is a ❓ on the chart, an unknown contact.
    assert page.evaluate(know) == 1
    # A ping close enough names its kind.
    page.evaluate("sub.x = 1000; sub.y = 150; doPing(); run(() => true, 0.3)")
    assert page.evaluate(know) == 2
    # Up close, in SISU's lamp, it is seen: its name.
    page.evaluate("const s = SITES.find(s => s.id === 'polaris'); sub.x = s.x - 30; sub.y = s.y + 6; sub.dir = sub.face = 1;"
                  " run(() => true, 0.3)")
    assert page.evaluate(know) == 3
    inside(page)
    walk(page, "kartta")
    page.click("#act")
    first_card(page)
    page.evaluate("CV.x = 1180; CV.y = 230; CV.z = 1; drawChart()")
    # A tap on it on the chart tells what it is.
    page.evaluate("""(() => { const r = $('chartC').getBoundingClientRect(), k = contacts().find(c => c.id === 'polaris');
      window.tapAt = [r.left + r.width / 2 + (k.x - CV.x) * CV.z, r.top + r.height / 2 + (k.y - CV.y) * CV.z]; })()""")
    x, y = page.evaluate("tapAt")
    page.mouse.click(x, y)
    assert page.inner_text("#pickName") == "Polaris"
    assert "m SISUsta" in page.inner_text("#pickTxt")
    assert page.errors == []


def test_only_what_a_lamp_lights_goes_on_the_chart_and_a_contact_astern_is_not_seen(site, browser):
    page = open_game(site, browser)
    v4.new_game(page)
    # SISU faces east without pinging: the sea 60 m ahead is on the chart, the sea 60 m astern is not.
    page.evaluate("sub.x = 700; sub.y = 60; sub.dir = sub.face = 1; chartSeen.fill(0); run(() => true, 0.3)")
    sq = "(x, y) => chartSeen[Math.floor((x - CH.x0) / CH.s) + Math.floor((y - CH.y0) / CH.s) * CH.w]"
    assert page.evaluate(f"({sq})(sub.x + 14 + 50, sub.y)") == 1
    assert page.evaluate(f"({sq})(sub.x - 60, sub.y)") == 0
    # A known wreck 40 m astern, out of the beam and the glow, stays known; facing it, the beam shows it.
    page.evaluate("""(() => { const s = SITES.find(s => s.id === 'polaris'); G.s.known.polaris = G.s.heard.polaris = 1;
      sub.x = s.x + s.w * C + 40; sub.y = s.y + 4; sub.dir = sub.face = 1; run(() => true, 0.5); })()""")
    know = "knowOf(contacts().find(c => c.id === 'polaris'))"
    assert page.evaluate(know) == 2
    page.evaluate("sub.dir = sub.face = -1; run(() => true, 0.5)")
    assert page.evaluate(know) == 3
    assert page.errors == []


def test_no_light_reaches_the_chart_through_ice(site, browser):
    page = open_game(site, browser)
    v4.new_game(page)
    # SISU by the iceberg's west face, its beam pointing into the ice: the sea before the face is charted, the maze
    # behind it is not, though the beam's reach would cover it.
    page.evaluate("sub.x = 2040; sub.y = 30; sub.vx = sub.vy = 0; sub.dir = sub.face = 1; chartSeen.fill(0); mapStep()")
    sq = "(x, y) => chartSeen[Math.floor((x - CH.x0) / CH.s) + Math.floor((y - CH.y0) / CH.s) * CH.w]"
    assert page.evaluate("60 * LAMP[G.s.up.lamp] + 14 + sub.x > 2110 && inBerg(2090, 30)") is True
    assert page.evaluate(f"({sq})(2070, 30)") == 1
    assert page.evaluate(f"({sq})(2110, 30)") == 0
    assert page.errors == []


def test_an_older_save_starts_its_chart_from_what_it_knew_and_gets_back_a_guide_left_in_the_ice(site, browser):
    s = v5.save_with(known={"kontti": True, "asema": True}, flags={"pinged": True, "koti": True, "kontti": True},
                     guides=[[2200, 120], [1150, 225]], inv={"ohjain": 1})
    page = open_game(site, browser, save=json.dumps(s))
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard(); step(1 / 60)")
    assert page.evaluate("[!!G.s.heard.kontti, !!G.s.heard.asema, !!G.s.seen.kontti, !!G.s.seen.asema]") == [True, True, True, False]
    assert page.evaluate("chartSeen.reduce((a, b) => a + b, 0)") > 0
    # the guide in what is ice now is back in the stores; the one at the wreck stays
    assert page.evaluate("[G.s.guides, G.s.inv.ohjain]") == [[[1150, 225]], 2]
    assert page.evaluate("'seed' in G.s") is False
    assert page.errors == []


@pytest.mark.parametrize("w,h", [(360, 740), (390, 844), (740, 360)])
def test_the_chart_and_the_lab_fit_upright_and_sideways(site, browser, w, h):
    page = open_game(site, browser, w, h)
    ready(page)
    page.evaluate("doPing(); step(1 / 60); for (const it of ITEMS.concat(ICE_ITEMS)) if (it.k === 'nayte') G.s.got[it.id] = true")
    chart(page)
    page.evaluate("CV.sel = 'kontti'; drawChart()")
    assert page.is_visible("#chartPick")
    assert page.evaluate(v4.OVERFLOW) == []
    for b in ("#zIn", "#zOut", "#zSisu", "#chartX", "#pickGo"):
        box = page.locator(b).bounding_box()
        assert box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= w and box["y"] + box["height"] <= h, b
    # the pick panel and the buttons do not overlap
    pick, close = page.locator("#chartPick").bounding_box(), page.locator("#chartX").bounding_box()
    assert pick["x"] + pick["width"] <= close["x"] or pick["y"] + pick["height"] <= close["y"]
    page.click("#zIn")
    page.click("#zOut")
    page.click("#chartX")
    page.click("#act2")
    assert page.evaluate(v4.OVERFLOW) == []
    page.click("#card button:has-text('Tutki: Lähteiden bakteerimatto')")
    assert page.evaluate(v4.OVERFLOW) == []
    assert page.errors == []


# ---------- the autopilot ----------

def test_the_autopilot_drives_to_a_known_contact_while_the_person_eats_inside(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("G.s.up.hull = 2; G.s.known.polaris = G.s.heard.polaris = 1; G.s.inv.ruoka = 2; G.s.m.food = 50")
    chart(page)
    page.evaluate("CV.sel = 'polaris'; drawChart()")
    assert page.inner_text("#pickGo") == "🧭 Autopilotti tänne"
    page.click("#pickGo")
    assert page.evaluate("G.auto && G.auto.id") == "polaris"
    assert "Autopilotti: kohti HYLKY" in toast(page)
    assert "Autopilotti → HYLKY" in page.inner_text("#chartAuto")
    page.click("#chartX")
    # While SISU drives itself, the person walks to the galley and eats.
    x0 = page.evaluate("sub.x")
    walk(page, "keittio")
    assert page.evaluate("sub.x") > x0 + 20
    v4.act(page, "Syö annos")
    assert page.evaluate("G.s.inv.ruoka") == 1
    assert "🧭" in page.inner_text("#depth")
    hull = page.evaluate("G.s.m.hull")
    page.evaluate("run(() => G.auto, 200)")
    spot = page.evaluate("SITES.find(s => s.id === 'polaris').spot")
    assert page.evaluate("G.auto") is None
    assert abs(page.evaluate("sub.x") - spot[0]) < 4 and abs(page.evaluate("sub.y") - spot[1]) < 4
    assert "Perillä: Polaris" in toast(page)
    # no scrape on the way, and hunger ran while SISU travelled
    assert page.evaluate("G.s.m.hull") == hull
    assert page.evaluate("G.s.m.food") < 85
    assert page.errors == []


def test_the_autopilot_will_not_go_to_an_unknown_contact_or_deeper_than_the_hull_and_the_helm_stops_it(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("G.s.heard.polaris = 1; G.s.heard.saga = G.s.known.saga = 1; G.s.known.kontti = 1")
    chart(page)
    page.evaluate("CV.sel = 'polaris'; drawChart()")
    assert page.inner_text("#pickGo") == "🧭 Tunnista ensin" and page.is_disabled("#pickGo")
    page.evaluate("CV.sel = 'saga'; drawChart()")
    assert page.inner_text("#pickGo") == "🧭 Liian syvällä: runko 160 m" and page.is_disabled("#pickGo")
    # A known place within the hull's depth: it goes, and taking the helm stops it.
    page.evaluate("CV.sel = 'kontti'; drawChart()")
    page.click("#pickGo")
    assert page.evaluate("G.auto && G.auto.id") == "kontti"
    page.click("#pickGo")
    assert page.evaluate("G.auto") is None and "Autopilotti pois" in toast(page)
    page.click("#pickGo")
    page.click("#chartX")
    page.evaluate("run(() => true, 1)")
    page.click("#home")
    assert page.evaluate("[G.mode, G.auto]") == ["sub", None]
    assert "Autopilotti pois" in toast(page)
    assert page.errors == []


def test_the_autopilot_waits_while_the_player_dives_and_a_reload_leaves_sisu_where_it_was(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("G.s.up.hull = 2; G.s.known.nordvik = 1; G.mode = 'home'; crew.room = 'kartta'; doAct('me', 'auto', 'nordvik');"
                  " run(() => true, 4)")
    assert page.evaluate("G.auto && G.auto.id") == "nordvik"
    # Out through the airlock mid-trip: SISU holds still while the diver is out, and drives on once they are back.
    page.evaluate("crew.suit = true; crew.kit = 'tank'; startDive(); if (G.paused) closeCard(); run(() => true, 1)")
    x = page.evaluate("sub.x")
    page.evaluate("run(() => true, 3)")
    assert abs(page.evaluate("sub.x") - x) < 0.5 and page.evaluate("!!G.auto") is True
    page.evaluate("const a = airlock(); diver.x = a.x; diver.y = a.y; endDive(false); closeCard(); run(() => true, 3)")
    assert page.evaluate("sub.x") > x + 10
    # A reload mid-trip: the autopilot is off, and SISU is where it was last saved, not back at the start.
    page.evaluate("save()")
    saved = page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).sub.x")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.evaluate(v4.RUN)
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard(); step(1 / 60)")
    assert page.evaluate("G.auto") is None
    assert abs(page.evaluate("sub.x") - saved) < 1 and saved > 400
    assert page.errors == []


def test_with_the_chart_open_alone_the_autopilot_trip_still_maps_saves_and_makes_hungry(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("G.s.up.hull = 2; G.s.known.nordvik = 1; G.s.m.food = 80; G.s.flags.merikartta = true")
    chart(page)
    page.evaluate("CV.sel = 'nordvik'; drawChart()")
    page.click("#pickGo")
    seen = page.evaluate("chartSeen.reduce((a, b) => a + b, 0)")
    page.evaluate("run(() => true, 20)")
    assert page.evaluate("G.paused") is True and page.evaluate("!!G.auto") is True
    assert page.evaluate("chartSeen.reduce((a, b) => a + b, 0)") > seen
    assert page.evaluate("G.s.m.food") < 80
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).sub.x") > 400
    assert page.errors == []


def test_surfaced_in_one_opening_the_autopilot_still_goes_to_another(site, browser):
    page = open_game(site, browser)
    ready(page)
    v6.surface(page)
    page.evaluate("G.s.up.hull = 2; G.s.known.railo1 = 1; G.mode = 'home'; crew.room = 'kartta'; doAct('me', 'auto', 'railo1');"
                  " run(() => true, 1)")
    assert page.evaluate("G.auto && G.auto.id") == "railo1"
    page.evaluate("run(() => G.auto, 200)")
    assert page.evaluate("[G.auto, surfaced(), holeAt(sub.x)]") == [None, True, 1]
    assert page.errors == []


def test_in_the_dark_a_cave_find_shows_only_where_a_lamp_lights_it(site, browser):
    page = open_game(site, browser)
    ready(page)
    cave_dive(page)
    page.evaluate(f"({GLIDE})(4 * MAZE.cols + 1); draw()")
    # Just behind the diver, in plain sight but outside the beam and the glow: hidden, and so is its sparkle.
    hidden = page.evaluate("""(() => { const [x, y, mid, len, near] = lampOf(diver);
      const it = { site: 'jaavuori', x: diver.x - Math.cos(mid) * (near + 1.5), y: diver.y - Math.sin(mid) * (near + 1.5) };
      const ahead = { site: 'jaavuori', x: diver.x + Math.cos(mid) * 1.5, y: diver.y + Math.sin(mid) * 1.5 };
      return [caveHidden(it, diver), caveHidden(ahead, diver)]; })()""")
    assert hidden == [True, False]
    assert page.errors == []


def test_stopping_the_autopilot_at_speed_leaves_sisu_still_at_the_helm(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("G.s.up.hull = 2; G.s.known.nordvik = 1; G.mode = 'home'; crew.room = 'kartta'; doAct('me', 'auto', 'nordvik');"
                  " run(() => true, 8)")
    assert page.evaluate("Math.hypot(sub.vx, sub.vy)") > 5
    page.evaluate("answer(doAct('me', 'autostop'))")
    assert page.evaluate("[G.auto, sub.vx, sub.vy]") == [None, 0, 0]
    # again at speed, then straight to the helm with the stick let go
    page.evaluate("doAct('me', 'auto', 'nordvik'); run(() => true, 6)")
    assert page.evaluate("Math.hypot(sub.vx, sub.vy)") > 5
    page.click("#home")
    x = page.evaluate("sub.x")
    page.evaluate("input.x = input.y = 0; run(() => true, 2)")
    assert page.evaluate("[G.mode, G.auto]") == ["sub", None]
    assert abs(page.evaluate("sub.x") - x) < 0.5
    assert page.errors == []


def test_in_the_dark_iceberg_a_guide_and_a_friend_s_hose_show_only_in_lamp_light(site, browser):
    page = open_game(site, browser)
    ready(page)
    cave_dive(page)
    page.evaluate(f"({GLIDE})(4 * MAZE.cols + 1); draw()")
    # A crossing on the screen that no lamp lights (behind ice).
    spot = page.evaluate("""(() => { const v = G.view;
      return MAZE_P.filter(p => p && !litAt(p[0], p[1]) && Math.hypot(p[0] - diver.x, p[1] - diver.y) < 12
        && v.ox + p[0] * v.sc > 20 && v.ox + p[0] * v.sc < W - 20 && v.oy + p[1] * v.sc > 120 && v.oy + p[1] * v.sc < H - 200)[0]; })()""")
    assert spot
    px = """(() => { draw(); const v = G.view, d = ctx.getImageData(Math.round((v.ox + %s * v.sc) * DPR) - 6, Math.round((v.oy + %s * v.sc) * DPR) - 6, 12, 12).data;
      let m = 0; for (let k = 0; k < d.length; k += 4) m = Math.max(m, d[k] + d[k + 1] + d[k + 2]); return m; })()""" % (spot[0], spot[1])
    dark = page.evaluate(px)
    # A guide clamped there, and a friend beside this diver (lit by both lamps) whose hose bends round that corner.
    page.evaluate(f"""G.s.guides.push([{spot[0]}, {spot[1]}]);
      net = {{ host: true, others: {{ x: {{ name: 'Aino', mode: 'dive', x: diver.x, y: diver.y, tx: diver.x, ty: diver.y, dir: 1,
        suit: true, kit: 'hose', ang: 0, walkT: 0, hose: [0, 0, {spot[0]}, {spot[1]}] }} }}, names: {{ x: 'Aino' }},
        cols: {{ x: '#3fcf7f' }}, helm: null }}""")
    assert page.evaluate(px) <= dark + 30
    # Without the dark (the diver out of the berg's view), the same guide and hose do show there: the test can see them.
    page.evaluate("window.bergView = () => false")
    assert page.evaluate(px) > dark + 100
    page.evaluate("net = null")
    assert page.errors == []


def test_the_autopilot_finds_its_way_under_the_iceberg_and_up_an_opening(site, browser):
    page = open_game(site, browser)
    ready(page)
    trips = page.evaluate("""(() => {
      const out = [];
      for (const [hull, from, id] of [[3, [2050, 52], 'itarailo'], [6, [2424, 105], 'nordlys'], [6, [3452, 879], 'railo1']]) {
        G.s.up.hull = hull; G.s.m.hull = 100; sub.x = from[0]; sub.y = from[1]; sub.vx = sub.vy = 0;
        G.s.known[id] = 1; G.mode = 'home'; crew.room = 'kartta';
        doAct('me', 'auto', id);
        run(() => G.auto, 400);
        out.push([id, !G.auto, Math.round(sub.x), Math.round(sub.y), Math.round(G.s.m.hull)]);
      }
      return out; })()""")
    for id_, done, x, y, hull in trips:
        assert done, id_
        assert hull >= 90, (id_, hull)  # at most a glowing fish's bump in the deep, no scraping
    assert page.evaluate("surfaced()") is True
    assert page.errors == []


def test_a_friend_sets_the_autopilot_and_sisu_moves_on_every_phone(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    host.evaluate("G.s.up.hull = 2; G.s.known.polaris = G.s.heard.polaris = 1; sub.vx = sub.vy = 0; save()")
    host.click("#home")
    v5.close_cards(host)
    v5.stand(aino, "kartta")
    aino.click("#act")
    first_card(aino)
    aino.wait_for_function("G.s.known.polaris")
    aino.evaluate("CV.sel = 'polaris'; drawChart()")
    aino.click("#pickGo")
    host.wait_for_function("G.auto && G.auto.id === 'polaris'")
    aino.wait_for_function("G.auto && G.auto.name === 'HYLKY'")
    x0 = aino.evaluate("sub.x")
    aino.wait_for_function(f"sub.x > {x0} + 30", timeout=15000)
    # the host is the one at the lab meanwhile: the logbook and the way back to the room are in the lab's card
    v5.stand(host, "kartta")
    host.click("#act2")
    assert "Huoneeseen" in host.inner_text("#card") and "Lokikirja" in host.inner_text("#card")
    for p in (host, aino):
        assert p.errors == []


# ---------- v8's tests about the navigation room, as it is now ----------

def test_a_trip_ends_when_the_host_takes_everyone_to_the_room(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    host.evaluate("G.s.up.hull = 2; G.s.known.polaris = 1; G.mode = 'home'; crew.room = 'kartta'; act('auto', 'polaris')")
    host.wait_for_function("G.auto && G.auto.id === 'polaris'")
    host.evaluate("toRoom()")
    for p in (host, aino):
        p.wait_for_function("!document.getElementById('aipr').hidden && G.mode === 'menu'")
    assert host.evaluate("G.auto") is None
    host.click("#aipr-start")
    for p in (host, aino):
        p.wait_for_function("G.s && G.mode !== 'wait' && G.mode !== 'menu'")
    host.click("#home")
    v5.close_cards(host)
    x = host.evaluate("sub.x")
    host.wait_for_timeout(1500)
    host.evaluate("drawHud()")
    assert abs(host.evaluate("sub.x") - x) < 0.5
    assert host.evaluate("G.auto") is None and "🧭" not in host.inner_text("#depth")
    for p in (host, aino):
        assert p.errors == []


def test_a_friend_s_open_chart_closes_when_the_host_ends_the_round(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    v5.stand(aino, "kartta")
    aino.click("#act")
    first_card(aino)
    assert aino.is_visible("#chart")
    host.evaluate("toRoom()")
    for p in (host, aino):
        p.wait_for_function("!document.getElementById('aipr').hidden && G.mode === 'menu'")
    assert aino.is_visible("#chart") is False
    host.click("#aipr-start")
    for p in (host, aino):
        p.wait_for_function("G.s && G.mode !== 'wait' && G.mode !== 'menu'")
    aino.evaluate("closeCard()")
    assert aino.is_visible("#chart") is False and aino.evaluate("G.paused") is False
    for p in (host, aino):
        assert p.errors == []


def test_samples_are_studied_in_the_lab_and_the_logbook_is_in_its_card(site, browser):
    page = open_game(site, browser)
    ready(page)
    v4.dive_at(page, "asema")
    v4.take(page, "it.k === 'nayte' && it.site === 'asema'")
    page.evaluate("const a = airlock(); diver.x = a.x; diver.y = a.y; drawHud()")
    page.click("#act")
    walk(page, "kartta")
    assert page.inner_text("#roomName") == "LABRA JA KARTAT"
    assert page.inner_text("#act2") == "🔬 Laboratorio (1)"
    page.click("#act2")
    page.click("#card button:has-text('Tutki: Merivesinäyte')")
    assert "Tästä lähtien: SISU kulkee 10 % nopeammin." in page.inner_text("#card")
    page.click("#card button:has-text('Jatka')")
    assert "Huoneeseen" not in page.inner_text("#card")
    page.click("#card button:has-text('Lokikirja')")
    assert "📓 Lokikirja" in page.inner_text("#card")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).lab") == {"vesi": True}
    assert page.errors == []


def test_the_host_takes_everyone_to_the_room_from_the_lab_card(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    host.click("#home")
    v5.close_cards(host)
    v5.stand(host, "kartta")
    host.click("#act2")
    host.click("#card button:has-text('Huoneeseen')")
    for p in (host, aino):
        p.wait_for_function("!document.getElementById('aipr').hidden && G.mode === 'menu'")
    host.click("#aipr-start")
    for p in (host, aino):
        p.wait_for_function("G.s && G.s.day === 4 && G.mode !== 'wait' && G.mode !== 'menu'")


def test_inside_nordlys_the_view_widens_and_the_iceberg_s_hall_holds_its_sample(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("G.s.up.hull = 6")
    v4.dive_at(page, "nordlys")
    page.evaluate("const s = SITES.find(s => s.id === 'nordlys'); diver.x = s.x - 30; diver.y = s.y")
    small = page.evaluate("diveScale()")
    page.evaluate("const s = SITES.find(s => s.id === 'nordlys'); diver.x = s.x + 20; diver.y = s.y + 12")
    assert page.evaluate("diveScale()") < small
    assert page.evaluate("(() => { const it = ITEMS.find(it => it.sample === 'jaa'); return Math.hypot(it.x - HALL.x, it.y - HALL.y) < 5.5"
                         " && inCave(it.x, it.y); })()")
    assert page.errors == []
