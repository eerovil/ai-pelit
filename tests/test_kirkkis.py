"""Kirkkis in a phone-sized Chromium, driven through the game's own step() and its people."""

from conftest import ROOT

# Runs the game for `s` seconds in small steps, synchronously.
RUN = "s => { for (let i = 0; i < s * 30; i++) step(1 / 30); }"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{site.url}games/kirkkis/v1/")
    page.errors = errors
    return page


def test_sight_is_a_field_of_view_blocked_by_walls_and_bushes(site, context):
    page = open_game(site, context)
    seen = page.evaluate("""() => {
      const o = { x: 15, y: 22, a: 0, st: 'seek' };
      const at = (x, y) => canSee(o, { x, y });
      return {
        ahead: at(22, 22),                                   // in front, in the open
        behind: at(8, 22),                                   // behind the back
        near: at(14.2, 22),                                  // right behind, but close enough to hear
        far: at(15 + 11, 22),                                // past the view's reach
        wall: canSee({ x: 13, y: 13, a: -Math.PI / 2, st: 'seek' }, { x: 7, y: 1 }) === false
          && canSee({ x: 7, y: 12, a: -Math.PI / 2, st: 'seek' }, { x: 7, y: 1.2 }) === false,
        bushFar: canSee({ x: 15, y: 17, a: -Math.PI / 2, st: 'seek' }, { x: 15, y: 11 }),
        bushNear: canSee({ x: 15, y: 13.2, a: -Math.PI / 2, st: 'seek' }, { x: 15, y: 11 }),
        shut: canSee({ x: 15, y: 22, a: 0, st: 'count' }, { x: 18, y: 22 }),
      };
    }""")
    assert seen == {"ahead": True, "behind": False, "near": True, "far": False, "wall": True,
                    "bushFar": False, "bushNear": True, "shut": False}


def test_a_bush_counts_as_searched_only_from_close_enough_to_see_into_it(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { const s = SPOTS.find(s => s.bush && Math.hypot(s.x - 15, s.y - 11) < 1);
      const far = { x: s.x, y: s.y + 6, a: -Math.PI / 2, st: 'seek' }, near = { x: s.x, y: s.y + 2, a: -Math.PI / 2, st: 'seek' };
      return [seesPoint(far, s), spotChecked(far, s), spotChecked(near, s)]; }""")
    assert r == [True, False, True]
    # In play: a seeker passing a bush at 6 m leaves it on the list of places to search.
    page.evaluate("newRound('seek'); for (let i = 0; i < 301; i++) step(1 / 30)")
    page.evaluate("""() => { seeker.x = 15; seeker.y = 17; seeker.a = -Math.PI / 2; SPOTS.forEach(s => { s.seen = -99; }); spotScan = 0; step(1 / 30); }""")
    assert page.evaluate("SPOTS.filter(s => s.bush && Math.hypot(s.x - 15, s.y - 11) < 1.6).every(s => s.seen < 0)")


def test_every_hiding_place_is_out_of_sight_of_the_base_and_reachable(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => SPOTS.map(s => [s.bush || !clearSight(BASE, s), findPath(BASE, s).length > 0, dist(s, BASE) >= 7])""")
    assert len(r) > 40
    assert all(all(row) for row in r)


def test_the_seeker_who_sees_a_hider_and_reaches_the_base_first_calls_kirkkis(site, context):
    page = open_game(site, context)
    page.evaluate("newRound('seek')")
    assert page.evaluate("[phase, player.role, player.st]") == ["count", "seeker", "count"]
    # Eyes shut while counting: nobody is seen, the player cannot move.
    page.evaluate("joy = { ox: 100, oy: 100, x: 160, y: 100 }")
    page.evaluate(RUN, 2)
    assert page.evaluate("hiders().every(h => h.st === 'hiding')")
    assert abs(page.evaluate("dist(player, BASE)") - 1.1) < 0.01
    page.evaluate("joy = null")
    page.evaluate(RUN, 8.1)
    assert page.evaluate("phase") == "seek"
    # Aino stands in the open in front of the player, far from the base.
    page.evaluate("""() => { const a = bots[0]; a.spot = a.goal = { x: 15, y: 31 }; a.x = 15; a.y = 31; a.path = []; a.left = true;
      a.brave = 999; for (const b of bots.slice(1)) { b.x = 2.5; b.y = 24; b.goal = b.spot = { x: 2.5, y: 24 }; b.path = []; b.brave = 999; }
      player.x = 15; player.y = 25; player.a = Math.PI / 2; }""")
    page.evaluate("step(1 / 30)")
    assert page.evaluate("bots[0].st") == "spotted"
    # The spotted hider races for the base; the player is already right next to it.
    page.evaluate("player.x = 15; player.y = 23; step(1 / 30)")
    assert page.evaluate("bots[0].st") == "caught"
    assert page.evaluate("firstCaught === bots[0]")
    assert page.errors == []


def test_a_hider_who_reaches_the_base_first_is_saved_and_it_is_kept(site, context):
    page = open_game(site, context)
    page.evaluate("newRound('hide')")
    assert page.evaluate("[player.role, !!seeker.isPlayer, seeker.st]") == ["hider", False, "count"]
    # Run away, wait out the count behind the house, then sneak back while the seeker is away.
    page.evaluate("player.x = 6; player.y = 0.6")
    page.evaluate(RUN, 10.1)
    assert page.evaluate("[phase, player.left]") == ["seek", True]
    page.evaluate("seeker.x = 26; seeker.y = 42; seeker.a = Math.PI / 2; seeker.goal = { x: 26, y: 43 }; seeker.path = []")
    page.evaluate("player.x = 15; player.y = 20.9; step(1 / 30)")
    assert page.evaluate("player.st") == "saved"
    # The rest of the round plays out by itself, and the result is saved on the phone.
    page.evaluate("for (let t = 0; t < 130 && phase !== 'menu'; t += 1 / 30) step(1 / 30)")
    assert page.evaluate("phase") == "menu"
    stats = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kirkkis:tilasto'))")
    assert stats["kierrokset"] == 1 and stats["pelastuit"] == 1
    assert page.locator("#result").inner_text() == "Pelastuit! 🎉"
    assert page.errors == []


def test_a_hider_who_is_seen_away_from_the_base_is_caught_by_the_computer_seeker(site, context):
    page = open_game(site, context)
    page.evaluate("newRound('hide'); player.x = 6; player.y = 0.6")
    page.evaluate(RUN, 10.1)
    page.evaluate("""() => { player.x = 15; player.y = 31; seeker.x = 15; seeker.y = 26; seeker.a = Math.PI / 2;
      for (const b of hiders()) if (b !== player) { b.st = 'saved'; } bots.forEach(b => { if (b !== seeker) b.st = 'caught'; }); }""")
    # Keep one other hider in the round so it does not end at once.
    page.evaluate("""() => { const o = bots.find(b => b !== seeker); o.st = 'hiding'; o.x = 2.5; o.y = 24; o.goal = o.spot = { x: 2.5, y: 24 }; o.brave = 999; }""")
    page.evaluate("step(1 / 30)")
    assert page.evaluate("player.st") == "spotted"
    # The player stands still; the seeker runs back to the base.
    page.evaluate(RUN, 4)
    assert page.evaluate("player.st") == "caught"
    assert page.errors == []


def test_rounds_against_the_computer_end_and_the_first_caught_seeks_next(site, context):
    page = open_game(site, context)
    results = page.evaluate("""() => { const out = [];
      for (let r = 0; r < 6; r++) {
        newRound(r % 2 ? 'seek' : 'hide'); let t = 0;
        while (phase !== 'menu' && t < 130) { step(1 / 30); t += 1 / 30; }
        out.push({ t, menu: phase === 'menu', next: nextSeeker.name, first: firstCaught ? firstCaught.name : null, seeker: seeker.name });
      } return out; }""")
    for r in results:
        assert r["menu"] and r["t"] < COUNT_PLUS_SEEK
        assert r["next"] == (r["first"] or r["seeker"])
    assert page.errors == []


COUNT_PLUS_SEEK = 10 + 100 + 3
