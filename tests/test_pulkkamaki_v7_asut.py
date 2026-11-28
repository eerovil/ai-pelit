"""Pulkkamäki v7 (#568): the rider wears the outfit shared by every 3D game (lib/asut3d-1). v6's
choice carries over, and the costume heads are the shared library's."""
from test_pulkkamaki_v7 import go, open_game

SHARED = "ai-pelit:_asut:3d"


def test_the_v6_choice_carries_over_to_every_3d_game(site, context):
    context.add_init_script("if (!localStorage.getItem('x')) { localStorage.setItem('x', 1); localStorage.setItem('ai-pelit:_asut:pulkkamaki', '\"liila\"'); }")
    page = open_game(site, context)
    assert page.evaluate("outfit.id") == "liila"
    assert page.evaluate(f"localStorage.getItem('ai-pelit:_asut:pulkkamaki')") == '"liila"'
    go(page)
    page.wait_for_function("V3.rigs.get(me.id) && V3.rigs.get(me.id).userData.outfit === 'liila'")
    assert page.errors == []


def test_the_winter_wear_is_the_common_set_and_the_costumes_are_in_the_picker(site, context):
    page = open_game(site, context)
    # The common set's first five are v6's own winter wear, unchanged.
    assert page.evaluate("JSON.stringify(AiPelitOutfits.kolmiD.slice(0, 5)) === JSON.stringify(OUTFITS)")
    ids = page.evaluate("AiPelitOutfits.list().map(o => o.id)")
    assert ids[:5] == ["haalari", "punainen", "vihrea", "liila", "musta"]
    assert {"sankari", "yosankari", "kurpitsa", "vampyyri", "harry"} <= set(ids)
    page.click("#asu")
    page.click("[data-asu=kurpitsa]")
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"kurpitsa"'
    page.evaluate("AiPelitOutfits.close()")
    go(page)
    page.wait_for_function("V3.rigs.get(me.id) && V3.rigs.get(me.id).userData.outfit === 'kurpitsa'")
    # The pumpkin head is the library's own, mesh for mesh.
    n = page.evaluate("""(() => { const c = g => { let n = 0; g.traverse(m => { if (m.isMesh) n++; }); return n; };
        return [c(V3.rigs.get(me.id).userData.P.head), c(AiPelitAsut3d.head(THREE, AiPelitOutfits.get('kurpitsa')))]; })()""")
    assert n[0] == n[1] >= 3
    assert page.errors == []


def test_a_vampire_rider_has_a_cape_and_a_skeleton_ribs(site, context):
    page = open_game(site, context)
    # Counted against a stripeless outfit (the overall's stripe is v6's own piece): body, two arms, head.
    got = page.evaluate("""['vampyyri', 'luuranko', 'punainen'].map(id => {
        const o = AiPelitOutfits.get(id); return [!!o.stripe, makeRig(o).userData.P.torso.children.length]; })""")
    assert [g[0] for g in got] == [False, False, False]
    plain = got[2][1]
    assert plain == 4 and got[0][1] == plain + 1 and got[1][1] == plain + 1
    assert page.errors == []
