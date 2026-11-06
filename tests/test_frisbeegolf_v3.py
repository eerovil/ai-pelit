"""Frisbeegolf: phone controls, all nine holes, flight hazards, saves and room recovery."""
import json
import math

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = 'games/frisbeegolf/v3/'
PLAN = """() => {
 window.finishFlight=()=>{for(let i=0;i<1500&&round.phase==='fly';i++)step(.05);};
 window.planThrow=()=>{
   const h=HOLES[round.hole],lie=current().lie,dist=distance(lie,h.basket);
   const base=Math.atan2(h.basket[0]-lie[0],h.basket[1]-lie[1]);
   let best=null,cost=Infinity;
   const ds=dist<10?[2]:[0,1,2];
   for(const disc of ds){
     const max=dist<10?12:DISCS[disc].range;
     for(let ai=-5;ai<=5;ai++)for(let pi=-4;pi<=4;pi++){
       const angle=base+ai*.035,power=clamp((dist+pi*.6)/max,.06,1);
       const curve=dist<10?0:-DISCS[disc].fade*.009/.22;
       const shot={disc,angle,power,curve,lie:lie.slice(),seed:12345+round.seq*7919};
       const f=fly(shot,h),c=f.holed?-1000:distance(f.lie,h.basket)+(f.penalty?100:0);
       if(c<cost){cost=c;best=shot;}if(c===-1000)return best;
     }
   }
   return best;
 };
}"""


def open_game(site, browser, size=(360, 740)):
    site.build(ROOT / 'games')
    ctx = browser.new_context(viewport={'width': size[0], 'height': size[1]}, is_mobile=True, has_touch=True)
    p = ctx.new_page()
    p.errors = []
    p.on('pageerror', lambda e: p.errors.append(str(e)))
    p.goto(site.url + URL)
    p.wait_for_function('scene3d !== null')
    p.evaluate(PLAN)
    return ctx, p


def pull(p, power, curve=0):
    b = p.locator('#throwPad').bounding_box()
    x, y = b['x'] + b['width'] / 2, b['y'] + 24
    length = p.evaluate('pullLength()')
    assert y + power * length < p.viewport_size['height']
    p.mouse.move(x, y)
    p.mouse.down()
    p.mouse.move(x + curve * 65, y + power * length, steps=4)
    p.mouse.up()


@pytest.mark.parametrize('size', [(360, 640), (360, 740), (390, 844), (740, 360)])
def test_real_controls_and_layout(site, browser, size):
    ctx, p = open_game(site, browser, size)
    for sel in ['#play', '#friends', '#scores', '.instructions']:
        b = p.locator(sel).bounding_box()
        assert b['y'] >= 0 and b['y'] + b['height'] <= size[1], sel
    p.click('#play')
    # Facing follows a drag before release; taps and other pointers do not move it.
    initial = p.evaluate('aim.angle')
    p.mouse.move(100, 240); p.mouse.down(); p.mouse.move(160, 240, steps=4)
    expected = initial + 60 / size[0] * math.pi
    assert p.evaluate('aim.angle') == pytest.approx(expected)
    assert p.evaluate('aimDrag!==null&&current().strokes===0')
    p.dispatch_event('#scene', 'pointerdown', {'pointerId': 42, 'clientX': 10, 'clientY': 240})
    p.dispatch_event('#scene', 'pointermove', {'pointerId': 42, 'clientX': 300, 'clientY': 240})
    p.dispatch_event('#throwPad', 'pointerdown', {'pointerId': 42, 'clientX': 180, 'clientY': 520})
    p.dispatch_event('#scene', 'pointercancel', {'pointerId': 42})
    assert p.evaluate('aim.angle') == pytest.approx(expected)
    assert p.evaluate('aimDrag.id===1&&drag===null')
    p.dispatch_event('#scene', 'pointercancel', {'pointerId': 1})
    p.mouse.up()
    assert p.evaluate('aimDrag===null&&round.phase==="aim"&&current().strokes===0')
    p.mouse.click(100, 240)
    assert p.evaluate('aim.angle') == pytest.approx(expected)
    p.click('#discs button:nth-child(3)')
    assert p.evaluate('aim.disc') == 2
    p.click('#map')
    assert p.evaluate('mapOpen')
    p.click('#map')
    chip = p.locator('#ai-pelit-tulokset-nappi').bounding_box()
    pad = p.locator('#throwPad').bounding_box()
    assert chip['x'] + chip['width'] <= pad['x'] or chip['y'] + chip['height'] <= pad['y']
    # The full pull stays on the screen in both orientations.
    pull(p, 1, .5)
    assert p.evaluate('round.phase') == 'fly'
    assert p.evaluate('current().strokes') == 1
    assert p.evaluate('round.shot.curve') == pytest.approx(.5, abs=.02)
    p.evaluate('finishFlight()')
    assert p.evaluate('round.phase') == 'aim'
    # A tap and pointer cancellation are never a throw.
    pull(p, 0)
    assert p.evaluate('current().strokes') == 1
    b = p.locator('#throwPad').bounding_box()
    p.mouse.move(b['x'] + b['width'] / 2, b['y'] + 20)
    p.mouse.down()
    p.dispatch_event('#throwPad', 'pointercancel', {'pointerId': 1})
    p.mouse.up()
    assert p.evaluate('drag===null')
    assert not p.errors
    ctx.close()


def test_flight_catches_determinism_ghost_and_hazards(site, browser):
    ctx, p = open_game(site, browser)
    result = p.evaluate("""() => {
      const h=HOLES[0],s={lie:[0,0],angle:0,disc:1,power:.5,curve:.2,seed:73};
      const a=fly(s,h),b=fly(s,h),ghost=fly(s,h,false),miss=distance(a.lie,ghost.lie);
      const box={x:0,y:ground(h,...h.basket)+.9,z:45};
      const empty={...h,trees:[],rocks:[],hill:0,wind:[0,0],basket:[100,100],water:[]};
      const w=fly({...s,curve:0,disc:2,power:1},{...empty,water:[{x:0,z:35.6,rx:10,rz:5}]},false);
      const ob=fly({...s,angle:Math.PI/2,curve:0,disc:2,power:1},{...empty,ob:20},false);
      const tree=fly({...s,angle:0,curve:0,disc:2,power:1},{...empty,trees:[[0,12,.5,8,'birch']]},false);
      return {same:JSON.stringify(a)===JSON.stringify(b),miss,slow:catches(h,box,3),fast:catches(h,box,12),
        high:catches(h,{...box,y:3},3),w,ob,tree};
    }""")
    assert result['same'] and result['miss'] < 2
    assert result['slow'] and not result['fast'] and not result['high']
    for key in ['w', 'ob']:
        assert result[key]['penalty'] == 1
    assert result['w']['reason'] == 'water' and result['ob']['reason'] == 'ob'
    assert result['ob']['lie'][0] <= 20
    assert result['tree']['reason'] == 'tree'
    p.click('#play')
    for disc in range(3):
        result = p.evaluate("""disc=>{
          aim.disc=disc;aim.power=.9;aim.curve=.5;refreshPreview();drawScene(0);
          const full=fly({...aim,lie:current().lie,seed:1},HOLES[round.hole],false);
          const end=preview.path.at(-1),want=flightPoint(full,full.duration/3);
          const vertices=scene3d.ghost.geometry.getAttribute('position');
          return {fraction:preview.duration/full.duration,error:Math.hypot(end.x-want.x,end.y-want.y,end.z-want.z),
            lastTime:end.t,limit:preview.duration,marker:!!scene3d.endRing,
            drawn:[vertices.getX(vertices.count-1),vertices.getY(vertices.count-1),vertices.getZ(vertices.count-1)],
            expected:[want.x,want.y+.02,want.z],landingExposed:'lie' in preview};
        }""", disc)
        assert result['fraction'] == pytest.approx(1/3)
        assert result['error'] < 1e-8
        assert result['lastTime'] == result['limit']
        assert result['drawn'] == pytest.approx(result['expected'], abs=1e-5)
        assert not result['marker'] and not result['landingExposed']
    assert not p.errors
    ctx.close()


@pytest.mark.parametrize('kind', ['tree', 'rock'])
def test_collision_lie_allows_next_throw_away(site, browser, kind):
    ctx, p = open_game(site, browser)
    result = p.evaluate("""kind => {
      const h={...HOLES[0],trees:[],rocks:[],hill:0,wind:[0,0],basket:[100,100],water:[]};
      if(kind==='tree')h.trees=[[0,12,.5,8,'birch']];
      else h.rocks=[[0,12,4]];
      const shot={lie:[0,0],angle:0,disc:2,power:1,curve:0,seed:1};
      const first=fly(shot,h,false);
      const second=fly({...shot,lie:first.lie,angle:Math.PI},h,false);
      return {reason:first.reason,clearance:distance(first.lie,[0,12]),
        moved:distance(first.lie,second.lie),next:second.reason};
    }""", kind)
    assert result['reason'] == kind
    assert result['clearance'] > (.6 if kind == 'tree' else 4)
    assert result['moved'] > 10
    assert result['next'] == 'grass'
    assert not p.errors
    ctx.close()


def test_complete_nine_holes_and_second_round(site, browser):
    ctx, p = open_game(site, browser)
    p.evaluate("localStorage.setItem('ai-pelit:_tulokset:lahetetyt',JSON.stringify({'frisbeegolf|main':{score:-30,level:0}}))")
    p.click('#play')
    scores = []
    for hole in range(9):
        for _ in range(6):
            if p.evaluate("round.phase!=='aim'"):
                break
            shot = p.evaluate('planThrow()')
            p.evaluate('(s)=>{aim=s;refreshPreview();renderUI();}', shot)
            pull(p, shot['power'], shot['curve'])
            p.evaluate('finishFlight()')
        assert p.evaluate('current().done'), (hole, p.evaluate('round'))
        scores.append(p.evaluate('current().strokes'))
        assert scores[-1] <= p.evaluate('HOLES[round.hole].par+1')
        if hole < 8:
            p.click('#next')
    assert p.evaluate('round.phase') == 'end'
    assert p.locator('#ai-pelit-nimi').is_visible()
    p.locator('#ai-pelit-tulokset').get_by_role('button', name='Sulje', exact=True).click()
    assert p.evaluate("load('kierroksia',0)") == 1
    assert len(p.evaluate("load('vaylat',[])")) == 9
    assert p.evaluate("load('ennatys',null)") == sum(scores) - 30
    assert p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))['frisbeegolf|v3'].score") == sum(scores) - 30
    assert p.evaluate("[-2,0,5].map(n=>AiPelitScores.scoreText('frisbeegolf',n))") == ['−2', 'E', '+5']
    for sel in ['#next', '#toMenu', '#scoreRows']:
        b = p.locator(sel).bounding_box()
        assert b['y'] >= 0 and b['y'] + b['height'] <= 740
    p.click('#next')
    assert p.evaluate('round.hole===0&&current().strokes===0')
    assert not p.errors
    ctx.close()


def test_reload_rotate_and_midflight_save(site, browser):
    ctx, p = open_game(site, browser)
    p.click('#play')
    pull(p, .4)
    p.evaluate('finishFlight()')
    before = p.evaluate('JSON.stringify(round)')
    p.reload()
    p.click('#resume')
    assert p.evaluate('JSON.stringify(round)') == before
    turn(p, {'width': 740, 'height': 360})
    assert p.evaluate('JSON.stringify(round)') == before
    pull(p, .6)
    p.reload()
    p.click('#resume')
    assert p.evaluate('JSON.stringify(round)') == before
    assert not p.errors
    ctx.close()


@pytest.fixture
def phones(site, browser):
    site.build(ROOT / 'games')
    relay, contexts = Relay(), []
    def phone(name, shell=False, size=(360, 740)):
        ctx = browser.new_context(viewport={'width': size[0], 'height': size[1]}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        if shell:
            ctx.add_init_script('window.__aiPelitHuoneSivu=true;')
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi'," + json.dumps(json.dumps(name)) + ")")
        p = ctx.new_page()
        p.errors = []
        p.on('pageerror', lambda e: p.errors.append(str(e)))
        relay.attach(p)
        p.goto(site.url + URL)
        p.evaluate(PLAN)
        return p
    yield phone, relay
    for ctx in contexts:
        ctx.close()


def make_room(phone, n):
    host = phone('Testi1')
    host.click('#friends'); host.click('#aipr-create')
    host.wait_for_function('R.isHost&&R.members.length===1')
    code, pages = host.evaluate('R.code'), [host]
    for i in range(1, n):
        p = phone('Testi' + str(i + 1)); p.click('#friends'); p.fill('#aipr-codeIn', code); p.click('#aipr-joinBtn')
        p.wait_for_function('R.inRoom'); pages.append(p)
    host.wait_for_function(f'R.members.filter(p=>p.on).length==={n}')
    host.click('#aipr-start')
    for p in pages:
        p.wait_for_function("round&&round.phase==='aim'")
    return pages


@pytest.mark.parametrize('n', [3, 8])
def test_rooms_all_phones_throw_two_holes_reload_and_finish(phones, n):
    phone, relay = phones
    pages = make_room(phone, n); host = pages[0]
    # Each player putts through the real control on two holes; completion advances tee honours.
    for hole in range(2):
        host.evaluate("""round.players.forEach(p=>{p.lie=[HOLES[round.hole].basket[0],HOLES[round.hole].basket[1]-3];});round.seq++;resetAim();showPlay();sendState();""")
        for i, p in enumerate(pages):
            p.wait_for_function(f'round.turn==={i}')
            p.evaluate('aim.angle=0;aim.disc=2;refreshPreview();renderUI();')
            oldseq = p.evaluate('round.seq')
            pull(p, .38)
            host.wait_for_function("round.phase==='fly'")
            if i:
                p.evaluate('(seq)=>R.send({t:"shot",round:roomRound,seq,angle:0,disc:2,power:.3,curve:0})', oldseq)
            host.evaluate('finishFlight()')
        for p in pages:
            p.wait_for_function("round.phase==='hole'")
            assert p.evaluate('round.players.every(p=>p.strokes===1)')
        if hole == 0:
            pages[1].reload(); pages[1].wait_for_function("round&&round.phase==='hole'")
            host.click('#next')
    # Finish delivery while a guest reloads, then prove once-only persistence.
    host.evaluate("""round.hole=8;round.phase='aim';round.turn=0;round.seq++;
      round.players.forEach((p,i)=>{p.scores=[3,3,3,3,4,3,4,3];p.done=i>0;if(i)p.scores.push(4);p.strokes=0;p.lie=[0,137];});resetAim();showPlay();sendState();""")
    pages[1].reload()
    host.evaluate('aim.angle=0;aim.disc=2;refreshPreview();renderUI();')
    pull(host, .38); host.evaluate('finishFlight()')
    for p in pages:
        p.wait_for_function("round&&round.phase==='end'")
        assert p.evaluate("load('kierroksia',0)") == 1
        assert p.locator('#scoreRows details').count() == n
    host.evaluate("R.deliver({t:'result',round:roomRound,state:round})")
    pages[1].reload(); pages[1].wait_for_function("round&&round.phase==='end'")
    assert pages[1].evaluate("load('kierroksia',0)") == 1
    for p in pages:
        assert not p.errors


def test_skip_away_player_and_rejoin(phones):
    phone, relay = phones
    host, guest, other = make_room(phone, 3)
    guest.evaluate('R.leave()')
    host.wait_for_function('R.members.some(p=>!p.on)')
    pull(host, .38); host.evaluate('finishFlight()')
    host.wait_for_function('R.paused'); host.click('#aipr-goOn')
    other.wait_for_function('round.turn===2&&round.players[1].done')
    assert other.evaluate('round.players[1].scores[0]') == 6
    other.wait_for_function('!R.paused')
    assert other.locator('#discs button').first.is_enabled()
    other.locator('#discs button').nth(2).click()
    assert other.evaluate('aim.disc') == 2
    guest.click('#friends'); guest.click('#aipr-again')
    guest.wait_for_function('round&&round.turn===2&&round.players[1].done')
    assert not guest.errors


def test_farthest_disc_throws_first_and_offline_continues(site, browser):
    ctx, p = open_game(site, browser)
    p.click('#play')
    assert p.evaluate("""() => {
      const saved=round;round=fresh([{id:'a',name:'A'},{id:'b',name:'B'},{id:'c',name:'C'}]);
      round.players.forEach((p,i)=>{p.strokes=1;p.lie=[0,10+i*10];});
      const far=nextThrower();round.players[0].done=true;
      const next=nextThrower();round=saved;return far===0&&next===1;
    }""")
    ctx.set_offline(True)
    pull(p, .5)
    p.evaluate('finishFlight()')
    assert p.evaluate('current().strokes') == 1
    assert p.evaluate("load('kierros',null).players[0].strokes") == 1
    assert not p.errors
    ctx.close()


@pytest.mark.parametrize('size', [(360, 640), (390, 844), (740, 360)])
def test_real_room_page_frame_can_play(phones, size):
    phone, relay = phones
    host = phone('Testi1', shell=True, size=size)
    host.click('#friends'); host.click('#aipr-create')
    host.wait_for_url('**/huone/**')
    host.wait_for_function("document.getElementById('game')?.contentWindow?.AiPelitRooms?.isHost")
    hf = host.frame_locator('#game')
    code = host.locator('#code b').inner_text()
    guest = phone('Testi2', shell=True, size=size)
    guest.click('#friends'); guest.fill('#aipr-codeIn', code); guest.click('#aipr-joinBtn')
    guest.wait_for_url('**/huone/**')
    host.wait_for_function("document.getElementById('game').contentWindow.AiPelitRooms.members.filter(p=>p.on).length===2")
    hf.locator('#aipr-start').click()
    hgame = next(f for f in host.frames if '/games/frisbeegolf/' in f.url)
    ggame = next(f for f in guest.frames if '/games/frisbeegolf/' in f.url)
    for f in (hgame, ggame):
        f.wait_for_function("round&&round.phase==='aim'")
        f.evaluate(PLAN)
    mic = host.locator('#aipr-mic')
    mic.wait_for(state='visible')
    m = mic.bounding_box()
    for sel in ['#hud', '#map', '#roster', '#controls']:
        r = hf.locator(sel).bounding_box()
        assert (m['x'] + m['width'] <= r['x'] or r['x'] + r['width'] <= m['x']
                or m['y'] + m['height'] <= r['y'] or r['y'] + r['height'] <= m['y']), sel
    scene = hf.locator('#scene').bounding_box()
    old_angle = hgame.evaluate('aim.angle')
    host.mouse.move(scene['x'] + 100, scene['y'] + 180)
    host.mouse.down(); host.mouse.move(scene['x'] + 140, scene['y'] + 180, steps=4)
    assert hgame.evaluate('aim.angle') == pytest.approx(old_angle + 40 / scene['width'] * math.pi)
    host.mouse.up()
    b = hf.locator('#throwPad').bounding_box()
    x, y = b['x'] + b['width']/2, b['y']+24
    host.mouse.move(x,y); host.mouse.down(); host.mouse.move(x,y+45,steps=4); host.mouse.up()
    hgame.wait_for_function("round.phase==='fly'")
    hgame.evaluate('finishFlight()')
    ggame.wait_for_function('round.turn===1&&round.players[0].strokes===1')
    assert not host.errors and not guest.errors

    hgame.evaluate("round.phase='end';round.hole=8;round.players.forEach(p=>p.scores=[3,3,3,3,4,3,4,3,4]);showCard();")
    for sel in ['#cardTitle', '#scoreRows', '#next']:
        r = hf.locator(sel).bounding_box()
        assert (m['x'] + m['width'] <= r['x'] or r['x'] + r['width'] <= m['x']
                or m['y'] + m['height'] <= r['y'] or r['y'] + r['height'] <= m['y']), sel


def test_legacy_round_keeps_personal_result_without_new_board_score(site, browser):
    ctx, p = open_game(site, browser)
    p.click('#play')
    p.evaluate("""delete round.rules;round.hole=8;round.players[0].scores=[2,2,2,2,2,2,2,2,2];
      round.phase='end';finishRecord();showCard();""")
    assert p.evaluate("load('ennatys',null)") == -12
    assert p.evaluate("load('kierroksia',0)") == 1
    assert not p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono')||'{}')['frisbeegolf|v3']")
    assert 'Vanha kierros, ei tuloslistalle' in p.locator('#cardTotal').inner_text()
    assert not p.errors
    ctx.close()
