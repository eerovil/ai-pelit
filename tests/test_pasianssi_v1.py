"""Pasianssi v1: Klondike rules, phone controls, saves and responsive layout (#382)."""

from conftest import ROOT, turn

URL = "games/pasianssi/v1/"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.errors = []
    page.on("pageerror", lambda error: page.errors.append(str(error)))
    page.wait_for_function("layoutState && layoutState.cw > 0")
    return page


def test_seeded_deal_has_all_cards_once_and_the_right_tableau(site, context):
    page = open_game(site, context)
    state = page.evaluate("deal(382, 1); snapshot()")
    again = page.evaluate("deal(382, 1); snapshot()")
    assert state == again
    cards = [card for pile in state["piles"] for card in pile] + state["stock"]
    assert len(cards) == 52
    assert len({card["s"] + str(card["r"]) for card in cards}) == 52
    assert [len(pile) for pile in state["piles"]] == list(range(1, 8))
    assert len(state["stock"]) == 24
    assert [[card["up"] for card in pile] for pile in state["piles"]] == [
        [False] * i + [True] for i in range(7)
    ]
    assert page.errors == []


def test_rules_tap_priority_reveal_and_undo(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      phase = 'play'; stock = []; waste = []; found = [[], [], [], []];
      piles = [
        [{s:'C',r:9,up:false},{s:'H',r:1,up:true}],
        [{s:'S',r:2,up:true}],
        [{s:'D',r:8,up:true}],
        [], [], [], []
      ];
      moves = []; moveCount = 0; elapsed = 0; started = false; counted = true;
      const legal = [
        canTableau([{s:'H',r:7,up:true}], [{s:'C',r:8,up:true}]),
        canTableau([{s:'H',r:8,up:true}], [{s:'C',r:8,up:true}]),
        canTableau([{s:'S',r:13,up:true}], []),
        canTableau([{s:'S',r:12,up:true}], [])
      ];
      const before = snapshot();
      bestMove({type:'pile',i:0,index:1});
      const after = snapshot();
      const undoOk = undo();
      return {legal, before, after, restored:snapshot(), undoOk};
    }""")
    assert result["legal"] == [True, False, True, False]
    # The ace goes to its foundation before the legal tableau alternative, revealing the nine.
    assert result["after"]["found"][1][-1] == {"s": "H", "r": 1, "up": True}
    assert result["after"]["piles"][0][-1]["up"]
    assert result["undoOk"]
    assert result["restored"]["piles"] == result["before"]["piles"]
    assert result["restored"]["found"] == result["before"]["found"]
    assert result["restored"]["moveCount"] == result["before"]["moveCount"]
    assert result["restored"]["started"]  # undoing the first move must not stop the scoring clock


def test_undo_never_rewinds_time_and_step_counts_a_full_foreground_stall(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      deal(55,1); elapsed=10; drawStock(); elapsed=25; undo();
      const afterUndo={elapsed,started}; step(2);
      return {afterUndo,afterStep:elapsed};
    }""")
    assert result["afterUndo"] == {"elapsed": 25, "started": True}
    assert result["afterStep"] == 27


def test_draw_three_recycles_the_waste_and_saves_every_action(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      deal(9, 3); const firstStock = stock.map(cardId);
      drawStock(); const first = {stock:stock.length,waste:waste.map(cardId),saved:!!localStorage.getItem('ai-pelit:pasianssi:jako1')};
      while (stock.length) drawStock();
      const wasteBefore = waste.map(cardId); drawStock();
      return {first, firstStock, wasteBefore, stockAfter:stock.map(cardId), wasteAfter:waste.length};
    }""")
    assert result["first"]["stock"] == 21
    assert len(result["first"]["waste"]) == 3 and result["first"]["saved"]
    assert result["wasteAfter"] == 0
    assert result["stockAfter"] == list(reversed(result["wasteBefore"]))


def test_a_real_canvas_drag_moves_a_run_to_the_card_under_the_finger(site, context):
    page = open_game(site, context)
    boxes = page.evaluate("""() => {
      phase='play'; stock=[]; waste=[]; found=[[],[],[],[]]; moves=[]; moveCount=0; started=false; counted=true;
      piles=[[{s:'H',r:7,up:true},{s:'C',r:6,up:true}],[{s:'C',r:8,up:true}],[],[],[],[],[]];
      showPlay(); layoutState=layout();
      return [cardRect({type:'pile',i:0,index:0}),cardRect({type:'pile',i:1,index:0})];
    }""")
    source, target = boxes
    page.mouse.move(source["x"] + source["w"] / 2, source["y"] + 8)
    page.mouse.down()
    page.mouse.move(target["x"] + target["w"] / 2, target["y"] + target["h"] / 2, steps=5)
    page.mouse.up()
    assert page.evaluate("piles.map(p => p.map(cardId))")[:2] == [[], ["C8", "H7", "C6"]]
    assert page.evaluate("moveCount") == 1


def test_a_second_finger_and_its_early_release_do_not_replace_the_first_action(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      deal(91,1); const r={...layoutState.stock,w:layoutState.cw,h:layoutState.ch};
      const send=(type,id,x,y)=>c.dispatchEvent(new PointerEvent(type,{pointerId:id,clientX:x,clientY:y,bubbles:true}));
      send('pointerdown',1,r.x+r.w/2,r.y+r.h/2);
      send('pointerdown',2,layoutState.pileX[0]+5,layoutState.tableY+5);
      send('pointerup',2,layoutState.pileX[0]+5,layoutState.tableY+5);
      const before={moves:moveCount,waste:waste.length,active:drag&&drag.id};
      send('pointerup',1,r.x+r.w/2,r.y+r.h/2);
      return {before,after:{moves:moveCount,waste:waste.length,active:drag}};
    }""")
    assert result["before"] == {"moves": 0, "waste": 0, "active": 1}
    assert result["after"] == {"moves": 1, "waste": 1, "active": None}


def test_the_game_still_plays_if_the_sound_library_was_not_cached(site, context):
    context.route("**/lib/aanet-5/aanet.js", lambda route: route.abort())
    page = open_game(site, context)
    page.click("#start")
    page.evaluate("drawStock()")
    assert page.evaluate("[phase, moveCount, waste.length]") == ["play", 1, 1]
    assert page.errors == []


def test_saved_deal_continues_after_reload_without_changing_mode(site, context):
    page = open_game(site, context)
    page.evaluate("deal(1234, 3); drawStock(); elapsed = 47; saveDeal(); chooseDraw(1)")
    before = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:pasianssi:jako1'))")
    page.reload()
    page.click("#continue")
    after = page.evaluate("snapshot()")
    assert after["piles"] == before["piles"]
    assert after["stock"] == before["stock"]
    assert after["waste"] == before["waste"]
    assert after["draw"] == 3
    assert after["elapsed"] >= 47
    assert page.evaluate("menuDraw") == 1
    assert page.errors == []


def test_finish_records_the_win_once_clears_the_save_and_selects_the_board(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      window.scoreCalls = []; window.soundCalls = [];
      window.AiPelitScores = {board:(...a)=>scoreCalls.push(['board',...a]), submit:s=>scoreCalls.push(['submit',s])};
      window.AiPelitAanet = {play:name=>{soundCalls.push(name);return true}};
      phase='play'; draw=3; menuDraw=3; stock=[]; waste=[]; moves=[]; moveCount=12; elapsed=91; started=true; counted=true;
      found = SUITS.map(s => Array.from({length:12},(_,i)=>({s,r:i+1,up:true})));
      piles = SUITS.map(s => [{s,r:13,up:true}]).concat([[],[],[]]);
      saveDeal(); const available=canFinish(); finishAll(); const wins=load('voitot',0); win();
      return {available,phase,wins,best:load('parhaat',{}),saved:localStorage.getItem('ai-pelit:pasianssi:jako1'),calls:scoreCalls,sounds:soundCalls};
    }""")
    assert result["available"] and result["phase"] == "won"
    assert result["wins"] == 1 and result["best"]["3"] == 91
    assert result["saved"] is None
    assert result["calls"][-2:] == [["board", "veto3", "3 korttia"], ["submit", 91]]
    assert result["sounds"].count("voitto") == 1


def test_the_last_cards_can_win_through_ordinary_legal_moves(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      window.AiPelitScores={board(){},submit(){}}; window.AiPelitAanet={play(){return true}};
      phase='play'; draw=1; stock=[]; waste=[]; moves=[]; moveCount=20; elapsed=80; started=true; counted=true;
      found=SUITS.map(s=>Array.from({length:12},(_,i)=>({s,r:i+1,up:true})));
      piles=SUITS.map(s=>[{s,r:13,up:true}]).concat([[],[],[]]);
      const moved=[0,1,2,3].map(i=>bestMove({type:'pile',i,index:0}));
      return {moved,phase,total:found.flat().length};
    }""")
    assert result == {"moved": [True, True, True, True], "phase": "won", "total": 52}


def test_canvas_actions_and_cards_fit_both_phone_orientations(site, context):
    page = open_game(site, context)
    page.click("#start")

    def geometry():
        return page.evaluate("""() => {
          const L=layoutState, rects=[];
          rects.push({...L.stock,w:L.cw,h:L.ch},{...L.waste,w:L.cw,h:L.ch},...L.found.map(r=>({...r,w:L.cw,h:L.ch})));
          piles.forEach((p,i)=>p.forEach((card,j)=>rects.push({x:L.pileX[i],y:L.tableY+j*pileGap(i),w:L.cw,h:L.ch})));
          const chip=document.getElementById('ai-pelit-tulokset-nappi').getBoundingClientRect().toJSON();
          return {w:W,h:H,rects,found:L.found.map(r=>({...r,w:L.cw,h:L.ch})),chip,buttons:[...document.querySelectorAll('#controls button:not(.hidden)')].map(b=>b.getBoundingClientRect().toJSON())};
        }""")

    for size in ({"width": 360, "height": 640}, {"width": 740, "height": 360}, {"width": 390, "height": 844}):
        turn(page, size)
        page.wait_for_function(f"Math.round(W) === {size['width']} && Math.round(H) === {size['height']}")
        g = geometry()
        assert all(r["x"] >= -1 and r["y"] >= -1 and r["x"] + r["w"] <= g["w"] + 1 and r["y"] + r["h"] <= g["h"] + 1 for r in g["rects"])
        assert all(b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= g["w"] and b["y"] + b["height"] <= g["h"] for b in g["buttons"])
        assert all(g["chip"]["y"] + g["chip"]["height"] <= r["y"] or g["chip"]["x"] >= r["x"] + r["w"] or g["chip"]["x"] + g["chip"]["width"] <= r["x"] for r in g["found"])
    assert page.evaluate("stock.length + waste.length + found.flat().length + piles.flat().length") == 52
    assert page.errors == []


def test_a_thirteen_card_run_keeps_every_visible_corner_tappable(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      phase='play'; stock=[]; waste=[]; found=[[],[],[],[]];
      piles=[Array.from({length:13},(_,i)=>({s:i%2?'H':'S',r:13-i,up:true})),[],[],[],[],[],[]];
      layoutState=layout(); const g=pileGap(0), hits=[];
      for(let i=0;i<13;i++){const r=cardRect({type:'pile',i:0,index:i});hits.push(hitAt(r.x+r.w/2,r.y+(i===12?r.h/2:g/2)).index)}
      const last=cardRect({type:'pile',i:0,index:12});return{g,hits,bottom:last.y+last.h,limit:layoutState.bottom};
    }""")
    assert result["g"] >= 8
    assert result["hits"] == list(range(13))
    assert result["bottom"] <= result["limit"] + 1


def test_shared_score_config_has_two_low_time_lists(site, context):
    page = open_game(site, context)
    assert page.evaluate("AiPelitScores.games.pasianssi.order") == "low"
    assert page.evaluate("AiPelitScores.games.pasianssi.lists") == [["veto1", "1 kortti"], ["veto3", "3 korttia"]]
    assert page.evaluate("AiPelitScores.games.pasianssi.score(91)") == "1:31"

