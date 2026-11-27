"""Seittisankari v5 (#565): the story, Tarina. Eight chapters of missions with cutscenes and radio
lines, Komisario Kallio and the gang boss Varjo; new missions (a window cleaner to reach, Varjo's
three-hit helicopter, robbers who leap away, a falling person, three bombs, the money bag) and
time limits in chapters 5–8 with a retry (Eero's choices).

The game loads lib/three, so these tests are `alone` and run on the AgentDeck host."""
import json

import pytest

from test_seittisankari_v5 import KEY, open_game

KINDS = [
    ["katto", "katto", "katto"],
    ["rosvot", "pakenevat"],
    ["rosvot", "auto", "paketti"],
    ["torni", "putoava", "auto"],
    ["pelasta", "putoava", "pelasta"],
    ["pakenevat", "heli"],
    ["pommit", "auto", "heli"],
    ["torni", "boss"],
]

# Finish the mission now (or its next roof): stand on its roof, catch its crooks (a hanging person
# let go first), reach its cleaner.
FINISH = """(w => {
  const h = w.hero;
  if (!isCrook(w.kind)) {
    const b = CITY[w.goal], t = roofTop(b);
    h.x = t.x; h.y = t.y; h.z = t.z; h.st = 'ground'; h.vx = h.vy = h.vz = 0;
  } else for (const k of w.crooks) {
    if (k.type === 'apu') { h.x = k.x; h.y = k.y; h.z = k.z; }
    else { if (k.type === 'putoava') k.falling = true; while (!k.caught) catchCrook(k); }
  }
})"""


def chapter_list(page):
    return page.evaluate("""[...document.querySelectorAll('#chList button')].map(b => [b.textContent, b.disabled])""")


def test_the_menu_has_tarina_and_the_chapter_list_opens_one_chapter_at_a_time(site, context):
    page = open_game(site, context)
    assert page.locator("#story").inner_text() == "📖 Tarina · Luku 1/8"
    page.click("#story")
    rows = chapter_list(page)
    assert len(rows) == 8
    assert rows[0] == ["1. Ensimmäinen ilta", False]
    assert all(d for _, d in rows[1:]) and rows[7][0] == "🔒 8. Huipulla"
    page.evaluate(f"localStorage.setItem('{KEY}tarina', JSON.stringify({{done: 3, best: {{0: 61.5, 1: 90, 2: 75}}}}))")
    page.click("#chBack"); page.click("#story")
    rows = chapter_list(page)
    assert [d for _, d in rows] == [False] * 4 + [True] * 4
    assert rows[0][0] == "1. Ensimmäinen ilta ✔ 1:01,5"
    assert page.locator("#chSub").inner_text() == "Luku 4/8"
    assert page.errors == []


def test_every_chapter_runs_its_missions_in_order_and_no_early_chapter_has_a_limit(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(finish => {
      const out = [];
      for (let ch = 0; ch < STORY.length; ch++) {
        const w = storyWorld(ch, null), kinds = [], lims = [];
        startMission(w, rng(ch + 1));
        for (let n = 0; n < 9 && !w.chDone; n++) {
          kinds.push(w.kind); lims.push(w.lim);
          let got = false;
          for (let i = 0; i < 6 && !got; i++) { finish(w); got = stepRound(w, STEP, rng(n + 7)); }
          if (!got) return ['stuck', ch, n, w.kind];
        }
        out.push({ kinds, lims, done: w.chDone, said: STORY[ch].steps.every(s => WHO[s.say[0]] && s.say[1].length <= 44),
          cuts: [STORY[ch].intro, STORY[ch].outro, ...STORY[ch].steps.map(s => s.cut || [])].every(c => c.every(l => WHO[l[0]] && l[1].length <= 60)) });
      }
      return out;
    })(""" + FINISH + ")")
    assert [c["kinds"] for c in r] == KINDS
    assert all(c["done"] and c["said"] and c["cuts"] for c in r)
    assert all(lim == 0 for c in r[:4] for lim in c["lims"])
    # Chapters 5–8: every crook or rescue mission has its limit, a roof none.
    limits = {"rosvot": 120, "heli": 150, "pelasta": 90, "boss": 240, "pakenevat": 150, "pommit": 150}
    for c in r[4:]:
        assert c["lims"] == [limits.get(k, 0) for k in c["kinds"]]


def test_a_chapter_opens_with_its_cutscene_plays_to_the_end_and_unlocks_the_next(site, context):
    page = open_game(site, context)
    page.click("#story")
    page.click("#chList button >> nth=0")
    assert page.locator("#cut").is_visible()
    assert page.locator("#cutTitle").inner_text() == "Luku 1 · Ensimmäinen ilta"
    # A look over the city, Kallio on a roof, then the first mission's roof with its radio line.
    assert page.evaluate("cut.shots.map(s => s.k)") == ["city", "roof", "target"]
    assert page.locator("#cutLine").is_hidden()
    # The cutscene pauses the game: nothing moves behind it.
    t0 = page.evaluate("[world.t, world.gt]")
    page.wait_for_timeout(300)
    assert page.evaluate("mode === 'cut' && [world.t, world.gt]") == t0
    page.click("#cut")                                     # tap: the city shot ends early
    assert page.locator("#cutWho").inner_text() == "Komisario Kallio"
    assert page.locator("#cutText").inner_text() == "Hei, sinä siellä seinällä! Olen komisario Kallio."
    page.click("#cut"); page.click("#cut")
    assert page.evaluate("cut.shots[cut.i].k") == "target"
    assert page.locator("#cutText").inner_text() == "Kiipeä tuon matalan talon katolle."
    assert page.locator("#cutTap").inner_text() == "Aloita ▶"
    page.wait_for_timeout(200)
    cam = page.evaluate("L3D.camAt()")
    flag = page.evaluate("[world.flag.x, world.flag.y, world.flag.z]")
    assert 10 < sum((a - b) ** 2 for a, b in zip(cam, flag)) ** 0.5 < 30
    page.click("#cut")
    page.wait_for_function("mode === 'play' && world.kind === 'katto'")
    assert page.locator("#cut").is_hidden()
    # The radio line plays over the round, which goes on under it.
    assert page.evaluate("world.radio.who") == "K"
    page.wait_for_function("world.t > 0.3")
    # The first roof is a low one close by.
    near = page.evaluate("(() => { const b = CITY[world.goal], t = roofTop(b); return [b.h, Math.hypot(t.x - world.hero.x, t.z - world.hero.z)]; })()")
    assert 20 <= near[0] <= 45 and 30 <= near[1] <= 110
    for step in range(3):
        page.evaluate(FINISH + "(world)")
        page.wait_for_function(f"world.story.step === {step + 1} || world.chDone")
    # The chapter is saved as done at once, before its closing cutscene.
    saved = json.loads(page.evaluate(f"localStorage.getItem('{KEY}tarina')"))
    assert saved["done"] == 1 and saved["cur"] is None and saved["best"]["0"] > 0
    page.wait_for_function("mode === 'cut'", timeout=6000)
    assert page.locator("#cutTitle").inner_text() == "Luku 1 valmis!"
    assert page.evaluate("cut.shots.map(s => s.k)") == ["roof"]
    page.click("#cutSkip")
    assert page.locator("#endTitle").inner_text() == "Luku 1 valmis!"
    assert "uusi ennätys" in page.locator("#endNote").inner_text()
    assert page.locator("#next").inner_text() == "Luku 2: Kattovarkaat ▶"
    page.click("#next")
    assert page.locator("#cutTitle").inner_text() == "Luku 2 · Kattovarkaat"
    page.click("#cutSkip")
    page.wait_for_function("mode === 'play' && world.kind === 'rosvot' && world.crooks.length === 3")
    # A mission with a cutscene of its own: first a moment of play (the "done" text), then the
    # scene, Kallio on the roof and the leaping robbers, then on with the play.
    page.evaluate(FINISH + "(world)")
    page.wait_for_function("world.kind === 'pakenevat'")
    assert page.evaluate("mode") == "play"
    page.wait_for_function("mode === 'cut'", timeout=4000)
    assert page.evaluate("cut.shots.map(s => s.k)") == ["roof", "target"]
    assert page.locator("#cutTitle").is_hidden()
    assert page.locator("#cutText").inner_text() == "Nuo rosvot ovat nopeampia."
    page.click("#cutSkip")
    page.wait_for_function("mode === 'play' && world.kind === 'pakenevat' && !world.cutQ")
    assert page.errors == []


def test_the_last_chapters_closing_scene_shows_varjo_webbed_and_no_helicopter(site, context):
    page = open_game(site, context)
    page.evaluate(f"localStorage.setItem('{KEY}tarina', JSON.stringify({{done: 7, best: {{}}}}))")
    page.click("#story")
    page.click("#chList button >> nth=7")
    page.click("#cutSkip")
    page.evaluate("world.story.step = 1; startMission(world)")
    page.evaluate(FINISH + "(world)")
    page.wait_for_function("mode === 'cut'", timeout=6000)
    r = page.evaluate("[cut.shots.map(s => s.k), cutView(0).actors.map(a => [a.id, !!a.caught])]")
    assert r[0] == ["varjo", "roof"]
    assert ["varjo", True] in r[1] and not any(a == "kopteri" for a, _ in r[1])
    page.click("#cutSkip")
    assert page.locator("#endTitle").inner_text() == "Kaupunki on turvassa!"
    assert page.locator("#next").is_hidden()
    assert page.errors == []


def test_a_window_cleaner_is_saved_within_3_m_and_never_webbed(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const out = [];
      for (let s = 1; s <= 20; s++) {
        const w = newWorld(); w.story = { ch: 4, step: 0 }; startMission(w, rng(s));
        const k = w.crooks[0], b = CITY[k.box], h = w.hero;
        const d = Math.hypot(roofTop(b).x - h.x, roofTop(b).z - h.z);
        const onWall = (k.nx > 0 ? Math.abs(k.x - b.x1) : k.nx < 0 ? Math.abs(k.x - b.x0) : k.nz > 0 ? Math.abs(k.z - b.z1) : Math.abs(k.z - b.z0)) < 0.5;
        // 4 m off: not saved; 2.9 m: saved, and lifted onto the roof.
        h.x = k.x + k.nx * 4; h.y = k.y; h.z = k.z + k.nz * 4; h.st = 'air';
        stepRound(w, STEP, rng(s)); const far = k.caught;
        // Veto cannot web him: aim straight at him.
        const aimed = aimCrook(h, Math.atan2(-k.nx, -k.nz), 0, w.crooks);
        h.x = k.x + k.nx * 2.9; h.z = k.z + k.nz * 2.9;
        const got = stepRound(w, STEP, rng(s));
        out.push({ y: k.y, top: b.h, d, onWall, far, aimed: !!aimed, got, caught: k.caught, ny: k.y, kind: w.chDone ? null : w.kind });
      }
      return out;
    })()""")
    for c in r:
        assert c["onWall"] and 120 <= c["d"] <= 300 + 20
        assert not c["far"] and not c["aimed"]
        assert c["got"] is True and c["caught"] and c["ny"] == c["top"]   # standing on the roof
    page.goto(page.url)
    ys = page.evaluate("""(() => { const out = []; for (let s = 1; s <= 30; s++) { const k = newCleaner(newHero(LX(2) + 20, 0, LX(2) + 20, 0), rng(s)); out.push(k.y); } return out; })()""")
    assert min(ys) >= 20 and max(ys) <= 60


def test_varjos_helicopter_takes_three_hits_and_breaks_free_after_each(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const w = newWorld(); w.story = { ch: 7, step: 1 }; startMission(w, rng(5));
      const k = w.crooks[0], out = { type: k.type, lim: w.lim, hits: [] };
      for (let n = 0; n < 3; n++) {
        const x0 = k.x, z0 = k.z;
        catchCrook(k, rng(n + 2));
        const to = k.to ? Math.hypot(k.to.x - x0, k.to.z - z0) : 0;
        let done = false;
        for (let i = 0; i < 600; i++) done = stepRound(w, STEP, rng(n)) || done;   // 5 s
        out.hits.push({ hp: k.hp, caught: k.caught, to, moved: Math.hypot(k.x - x0, k.z - z0), done, chDone: w.chDone });
      }
      return out;
    })()""")
    assert r["type"] == "boss" and r["lim"] == 240
    for h in r["hits"][:2]:
        assert not h["caught"] and not h["done"]
        assert h["to"] >= 140 and h["moved"] > 40          # it flies off at once
    assert [h["hp"] for h in r["hits"]] == [2, 1, 0]
    assert r["hits"][2]["caught"] and r["hits"][2]["done"] and r["hits"][2]["chDone"]


def test_a_mission_out_of_time_fails_and_starts_again_but_done_wins_the_same_step(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(finish => {
      const w = newWorld(); w.story = { ch: 5, step: 0 }; startMission(w, rng(3));
      w.gt = w.lim - STEP / 2; w.ct = 50;
      const fail = stepRound(w, STEP, rng(3));
      const after = { fail: w.fail && w.fail.kind, crooks: w.crooks.length };
      const still = stepRound(w, 1, rng(3));                 // nothing goes on after a fail
      retryMission(w, rng(4));
      const again = { kind: w.kind, gt: w.gt, ct: w.ct, crooks: w.crooks.length, fail: w.fail };
      // The limit and the last catch in one step: done.
      w.gt = w.lim - STEP / 2; finish(w);
      const both = stepRound(w, STEP, rng(5));
      return { fail, after, still, again, both, step: w.story.step };
    })(""" + FINISH + ")")
    assert r["fail"] == "fail" and r["after"] == {"fail": "pakenevat", "crooks": 0}
    assert r["still"] is False
    assert r["again"]["kind"] == "pakenevat" and r["again"]["gt"] == 0 and r["again"]["crooks"] == 3 and r["again"]["fail"] is None
    assert r["again"]["ct"] > 50                               # the chapter's clock counts every try
    assert r["both"] is True and r["step"] == 1


def test_out_of_time_shows_a_card_to_try_again(site, context):
    page = open_game(site, context)
    page.evaluate(f"localStorage.setItem('{KEY}tarina', JSON.stringify({{done: 5, best: {{}}}}))")
    page.click("#story")
    page.click("#chList button >> nth=4")
    page.click("#cutSkip")
    page.wait_for_function("mode === 'play' && world.kind === 'pelasta'")
    assert page.evaluate("world.lim") == 90
    page.evaluate("world.gt = world.lim - 0.05")
    page.wait_for_function("mode === 'card'")
    assert page.locator("#cardTitle").inner_text() == "Liian myöhään!"
    assert "verkkoon" in page.locator("#cardLines").inner_text()
    assert page.locator("#cardGo").inner_text() == "Yritä uudelleen"
    page.click("#cardGo")
    page.wait_for_function("mode === 'play' && world.kind === 'pelasta' && !world.fail && world.gt < 1")
    assert page.errors == []


def test_leaving_mid_chapter_keeps_its_step_and_clock_and_never_touches_the_free_city(site, context):
    page = open_game(site, context)
    page.evaluate(f"""localStorage.setItem('{KEY}tarina', JSON.stringify({{done: 3, best: {{}}}}));
      localStorage.setItem('{KEY}tehtavat', '7');
      localStorage.setItem('{KEY}kierros2', JSON.stringify({{h: {{x: 10, y: 0, z: 10, yaw: 0, st: 'air'}}, g: 5, gt: 3}}))""")
    before = page.evaluate(f"['tehtavat', 'kierros2', 'tehtava4'].map(k => localStorage.getItem('{KEY}' + k))")
    page.click("#story")
    page.click("#chList button >> nth=3")
    page.click("#cutSkip")
    page.wait_for_function("mode === 'play' && world.kind === 'torni'")
    page.evaluate(FINISH + "(world)")
    page.wait_for_function("mode === 'cut' && world.story.step === 1 && world.kind === 'putoava'", timeout=4000)
    page.click("#cutSkip")
    page.wait_for_function("mode === 'play'")
    # (Far enough from the hanging person that he does not let go.)
    pos = page.evaluate("world.gt = 12.5; [Math.round(world.hero.x), Math.round(world.hero.z)]")
    page.click("#quit")
    page.reload()
    page.wait_for_function("mode === 'menu'")
    page.click("#story")
    assert chapter_list(page)[3][0] == "4. Viesti tornissa · jatka"
    page.click("#chList button >> nth=3")
    page.wait_for_function("mode === 'play'")     # straight on, no cutscene
    r = page.evaluate("[world.story.ch, world.story.step, world.kind, world.gt, world.crooks.length, Math.round(world.hero.x), Math.round(world.hero.z)]")
    assert r[:3] == [3, 1, "putoava"] and abs(r[3] - 12.5) < 0.5 and r[4] == 1 and r[5:] == pos
    after = page.evaluate(f"['tehtavat', 'kierros2', 'tehtava4'].map(k => localStorage.getItem('{KEY}' + k))")
    assert after == before
    # The free city still opens its own round and count.
    page.click("#quit"); page.click("#free")
    page.wait_for_function("mode === 'play' && world && !world.story")
    assert page.evaluate("world.done") == 7 and page.evaluate("world.goal") == 5
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (740, 360)])
def test_the_chapter_list_and_cutscenes_fit_upright_and_sideways(site, context, size):
    page = open_game(site, context, *size)
    page.click("#story")
    for sel in ["#chList button >> nth=0", "#chList button >> nth=7", "#chBack"]:
        b = page.locator(sel).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= size[1] and b["x"] + b["width"] <= size[0], sel
    page.click("#chList button >> nth=0")
    b = page.locator("#cutTitle").bounding_box()
    assert b["y"] >= 0 and b["x"] >= 0 and b["x"] + b["width"] <= size[0]
    page.click("#cut")
    for sel in ["#cutSkip", "#cutLine", "#cutTap"]:
        b = page.locator(sel).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= size[1] and b["x"] >= 0 and b["x"] + b["width"] <= size[0], sel
    # The talk never covers the skip button.
    a, b = page.locator("#cutSkip").bounding_box(), page.locator("#cutLine").bounding_box()
    assert a["y"] + a["height"] < b["y"]
    # Out of time: the card to try again fits too.
    page.click("#cutSkip")
    page.evaluate("world.story.ch = 4; world.lim = 90; world.gt = 89.99; world.kind = 'pelasta'; world.crooks = [newCleaner(world.hero, rng(1))]")
    page.wait_for_function("mode === 'card'")
    for sel in ["#cardTitle", "#cardLines", "#cardGo", "#cardAlt"]:
        b = page.locator(sel).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= size[1], sel


# A quick player: Veto-pulls toward the target whenever it is not already flying, webs a crook
# in reach, else runs at it. The limits are at least twice its slowest time (rule 9).
BOT = """((ch, step, seed) => {
  const r = rng(seed), w = newWorld(); w.story = { ch, step }; startMission(w, r);
  const h = w.hero;
  let t = 0, next = 0;
  while (t < 600) {
    const left = w.crooks.filter(k => !k.caught);
    const k = left.reduce((p, q) => !p || Math.hypot(q.x - h.x, q.y - h.y, q.z - h.z) < Math.hypot(p.x - h.x, p.y - h.y, p.z - h.z) ? q : p, null);
    const g = k ? { x: k.x, y: k.y + (k.type === 'apu' ? 0 : CROOK_MID[k.type]), z: k.z } : CITY[w.goal] ? roofTop(CITY[w.goal]) : h;
    const yaw = Math.atan2(g.x - h.x, g.z - h.z);
    let pull = null;
    if (t >= next && h.st !== 'pull') {
      next = t + 0.25;
      if (k && k.type !== 'apu') {          // in reach: aim at its middle and shoot
        let ay = yaw, ap = 0;
        for (let i = 0; i < 3; i++) { const o = aimRay(h, ay, ap); ay = Math.atan2(g.x - o.ox, g.z - o.oz); ap = -Math.atan2(g.y - o.oy, Math.hypot(g.x - o.ox, g.z - o.oz)); }
        if (aimCrook(h, ay, ap, w.crooks) === k) catchCrook(k, r);
      }
      const here = Math.hypot(g.x - h.x, g.y - h.y, g.z - h.z);
      let best = null, bd = here - 4;
      for (let dy = -0.8; dy <= 0.81; dy += 0.2) for (let p = -1; p <= 1.1; p += 0.15) {
        const hit = aimPull(h, yaw + dy, p);
        if (!hit) continue;
        const s = pullSpot(hit), d = Math.hypot(g.x - s.x, g.y - s.y, g.z - s.z);
        if (d < bd) { bd = d; best = hit; }
      }
      pull = best;
    }
    stepHero(h, { ix: 0, iy: pull || h.st === 'wall' && g.y > h.y ? -1 : -1, jump: false, web: false, yaw, pull }, STEP);
    const got = stepRound(w, STEP, r); t += STEP;
    if (got === true) return t;
    if (w.kind === 'pelasta' && w.crooks[0] && w.crooks[0].caught) return t;
  }
  return 999;
})"""


# The falling person (chapter 5's step 2) has no clock: he fails by himself when he reaches the street.
@pytest.mark.parametrize("ch,step", [(4, 0), (4, 2), (5, 0), (5, 1), (6, 0), (6, 2), (7, 1)])
def test_each_time_limit_is_at_least_twice_a_quick_players_time(site, context, ch, step):
    page = open_game(site, context)
    times = page.evaluate(f"[1, 2, 3, 4, 5].map(s => ({BOT})({ch}, {step}, s * 11))")
    lim = page.evaluate(f"(() => {{ const w = newWorld(); w.story = {{ ch: {ch}, step: {step} }}; return missionFor(w).lim; }})()")
    print("chapter", ch + 1, "step", step + 1, "limit", lim, "bot times", [round(t, 1) for t in times])
    assert max(times) < 999, times
    assert lim >= 2 * max(times), (lim, times)


def test_leaping_robbers_jump_to_another_roof_when_the_hero_comes_near(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const out = [];
      for (let s = 1; s <= 10; s++) {
        const w = newWorld(); w.story = { ch: 1, step: 1 }; startMission(w, rng(s));
        const k = w.crooks[0], h = w.hero, b0 = k.box;
        // Far off: they stay.
        h.x = k.x + 60; h.y = k.y; h.z = k.z; h.st = 'air';
        for (let i = 0; i < 60; i++) stepRound(w, STEP, rng(s));
        const stay = k.box === b0 && !k.jump;
        // 10 m off at the same height: a leap to another roof.
        h.x = k.x + 10; h.z = k.z; h.y = k.y;
        let leapt = null;
        for (let i = 0; i < 240 && !leapt; i++) { stepRound(w, STEP, rng(s)); if (k.jump) leapt = Object.assign({}, k.jump); }
        if (!leapt) { out.push({ stay, leapt: false }); continue; }
        let top = 0;
        for (let i = 0; i < 240 && k.jump; i++) { stepRound(w, STEP, rng(s)); top = Math.max(top, k.y); }
        const b1 = CITY[k.box];
        out.push({ stay, leapt: true, d: Math.hypot(leapt.x1 - leapt.x0, leapt.z1 - leapt.z0), dh: Math.abs(b1.h - CITY[b0].h),
          moved: k.box !== b0, onRoof: Math.abs(k.y - b1.h) < 0.01, arc: top > Math.max(leapt.y0, leapt.y1), cd: k.cd,
          caught: catchCrook(k, rng(1)) && k.caught });
      }
      return out;
    })()""")
    leaps = [c for c in r if c["leapt"]]
    assert all(c["stay"] for c in r) and len(leaps) >= 8, r
    for c in leaps:
        assert 10 <= c["d"] <= 55 and c["dh"] <= 25 and c["moved"] and c["onRoof"] and c["arc"], c
        assert c["cd"] > 4 and c["caught"], c          # a rest after landing; a web still catches him


def test_a_falling_person_falls_when_the_hero_comes_and_is_caught_or_lost(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const mk = s => { const w = newWorld(); w.story = { ch: 3, step: 1 }; startMission(w, rng(s)); return w; };
      const w = mk(3), k = w.crooks[0], h = w.hero, b = CITY[k.box];
      const out = { type: k.type, top: b.h, y0: k.y, d0: Math.hypot(k.x - h.x, k.z - h.z) };
      out.noCatch = catchCrook(k) || k.caught;                // hanging: a web does not take him
      out.noAim = !aimCrook(h, Math.atan2(k.x - h.x, k.z - h.z), 0, w.crooks);
      h.x = k.x + k.nx * 75; h.z = k.z + k.nz * 75; h.y = 0; h.st = 'ground';
      stepRound(w, STEP, rng(1)); out.far = k.falling;
      h.x = k.x + k.nx * 65; h.z = k.z + k.nz * 65;
      stepRound(w, STEP, rng(1)); out.near = k.falling;
      const y1 = k.y; for (let i = 0; i < 120; i++) stepRound(w, STEP, rng(1));
      out.v = y1 - k.y;                                      // m in 1 s
      out.caught = catchCrook(k) && k.caught;
      let got = false; for (let i = 0; i < 120 * 60 && got !== true; i++) got = stepRound(w, STEP, rng(1));
      out.got = got; out.step = w.story.step;
      // Not caught: at the street the police net takes him and the mission starts again.
      const w2 = mk(4), k2 = w2.crooks[0];
      w2.hero.x = k2.x + k2.nx * 20; w2.hero.z = k2.z + k2.nz * 20;
      let f = false; for (let i = 0; i < 120 * 60 && f !== 'fail'; i++) f = stepRound(w2, STEP, rng(1));
      out.lost = f; out.failKind = w2.fail && w2.fail.kind;
      retryMission(w2, rng(5)); out.again = [w2.kind, w2.crooks[0].falling, w2.fail];
      return out;
    })()""")
    assert r["type"] == "putoava" and abs(r["y0"] - (r["top"] - 1.9)) < 0.01
    assert 50 <= r["top"] <= 150
    assert not r["noCatch"] and r["noAim"]
    assert not r["far"] and r["near"]
    assert abs(r["v"] - 5) < 0.2
    assert r["caught"] and r["got"] is True and r["step"] == 2
    assert r["lost"] == "fail" and r["failKind"] == "putoava"
    assert r["again"] == ["putoava", False, None]


def test_three_bombs_and_the_money_bag_are_roofs_in_a_row_under_one_clock(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const run = (ch, step) => {
        const w = newWorld(); w.story = { ch, step }; startMission(w, rng(9));
        const h = w.hero, goals = [], parts = [];
        let got = false;
        for (let n = 0; n < 6 && got !== true; n++) {
          goals.push(w.goal); w.gt += 10;
          const t = roofTop(CITY[w.goal]); h.x = t.x; h.y = t.y; h.z = t.z; h.st = 'ground';
          got = stepRound(w, STEP, rng(n)); parts.push(w.part ? w.part.kind : null);
        }
        const lim = missionFor(Object.assign(newWorld(), { story: { ch, step } })).lim;
        return { kind: STORY[ch].steps[step].k, lim, goals, parts, got };
      };
      return [run(6, 0), run(2, 2)];
    })()""")
    bombs, bag = r
    assert bombs["kind"] == "pommit" and bombs["lim"] == 150
    assert len(bombs["goals"]) == 3 and len(set(bombs["goals"])) == 3 and bombs["got"] is True
    assert bombs["parts"][:2] == ["pommit", "pommit"]
    assert bag["kind"] == "paketti" and bag["lim"] == 0
    assert len(bag["goals"]) == 2 and bag["goals"][0] != bag["goals"][1] and bag["got"] is True
    assert bag["parts"][0] == "paketti"
