"""Frisbeegolf: phone controls, all nine holes, flight hazards, saves and room recovery."""
import json
import math

import pytest
from conftest import ROOT, turn, GPU_ARGS
from test_rooms_lib import Relay

URL = 'games/frisbeegolf/v5/'
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
       const curve=dist<10?0:DISCS[disc].fade*.009/.22;
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


SWIPE = """async ([power, curve, ms]) => {
  // The camera's glide is only known after a frame is drawn, so wait for two still frames.
  for (let still = 0; still < 2;) {
    await new Promise(requestAnimationFrame);
    still = round && round.phase === 'aim' && !scene3d.moving ? still + 1 : 0;
  }
  const c = document.getElementById('scene'), r = c.getBoundingClientRect();
  const x = r.left + r.width * .5, y = r.top + r.height * .72;
  const dy = power * r.height * .4, dx = Math.tan(curve * Math.PI / 6) * dy;
  let t = performance.now();
  Object.defineProperty(performance, 'now', {value: () => t, configurable: true, writable: true});
  c.setPointerCapture = c.releasePointerCapture = () => {};
  const send = (type, px, py) => c.dispatchEvent(new PointerEvent(type, {pointerId: 1, clientX: px, clientY: py,
    bubbles: true, cancelable: true, pointerType: 'touch', isPrimary: true}));
  try { send('pointerdown', x, y); t += ms; send('pointermove', x + dx, y - dy); send('pointerup', x + dx, y - dy); }
  finally { delete performance.now; delete c.setPointerCapture; delete c.releasePointerCapture; }
}"""


def swipe(p, power, curve=0, game=None, root=None, ms=10):
    """Swipe up from the held disc: the swipe's length sets the power, its slant the tilt.

    The swipe's speed counts too, so it is sent as pointer events with the game's clock held
    still: the finger moves in exactly `ms`, whatever the test machine's load."""
    game = game or p
    game.evaluate(SWIPE, [power, curve, ms])


@pytest.mark.parametrize('size', [(360, 640), (360, 740), (390, 844), (740, 360)])
def test_drag_turns_view_and_swipe_throws(site, browser, size):
    ctx, p = open_game(site, browser, size)
    for sel in ['#play', '#friends', '#scores', '.instructions']:
        b = p.locator(sel).bounding_box()
        assert b['y'] >= 0 and b['y'] + b['height'] <= size[1], sel
    p.click('#play')
    p.wait_for_function('!scene3d.moving')
    # A drag away from the held disc turns the first-person view.
    initial = p.evaluate('aim.angle')
    p.mouse.move(60, size[1] * .3); p.mouse.down(); p.mouse.move(120, size[1] * .3, steps=4)
    expected = initial - 60 / size[0] * math.pi
    assert p.evaluate('aim.angle') == pytest.approx(expected)
    assert p.evaluate("drag.type==='aim'&&current().strokes===0")
    p.mouse.up()
    assert p.evaluate("drag===null&&round.phase==='aim'&&current().strokes===0")
    p.mouse.click(60, size[1] * .3)
    assert p.evaluate('aim.angle') == pytest.approx(expected)
    p.click('#map')
    assert p.evaluate('mapOpen')
    p.click('#map')
    # The labels and the notice fit on screen and stay off the held disc and the map button.
    assert p.locator('#notice').inner_text()
    disc = {'x': size[0] * .5 - 60, 'y': size[1] * .72 - 44, 'width': 120, 'height': 88}
    chip = p.locator('#map').bounding_box()
    for sel in ['#powerLabel', '#curveLabel', '#turnLabel', '#notice']:
        b = p.evaluate(f"(()=>{{const r=document.createRange();r.selectNodeContents(document.querySelector('{sel}'));"
                       "const b=r.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height};})()")
        assert b['y'] >= 0 and b['y'] + b['height'] <= size[1], sel
        for other in [disc, chip]:
            assert (b['x'] + b['width'] <= other['x'] or other['x'] + other['width'] <= b['x']
                    or b['y'] + b['height'] <= other['y'] or other['y'] + other['height'] <= b['y']), (sel, b, other)
    # A tap on the disc, or a cancelled swipe, is never a throw.
    swipe(p, 0)
    assert p.evaluate('current().strokes') == 0
    b = p.locator('#scene').bounding_box()
    p.mouse.move(b['width'] * .5, b['height'] * .72); p.mouse.down()
    p.mouse.move(b['width'] * .5, b['height'] * .6, steps=2)
    assert p.evaluate("drag.type==='swipe'")
    p.dispatch_event('#scene', 'pointercancel', {'pointerId': 1})
    p.mouse.up()
    assert p.evaluate("drag===null&&current().strokes===0&&round.phase==='aim'")
    # A slanted swipe throws a tilted disc on its own release path.
    swipe(p, .5, .5)
    assert p.evaluate('round.phase') == 'fly'
    assert p.evaluate('current().strokes') == 1
    assert p.evaluate('round.shot.curve') == pytest.approx(.5, abs=.03)
    assert p.evaluate('round.shot.power') == pytest.approx(.5, abs=.03)
    assert p.evaluate('round.shot.disc') == 1
    assert p.evaluate('Array.isArray(round.shot.velocity)&&Array.isArray(round.shot.origin)')
    p.evaluate('finishFlight()')
    assert p.evaluate('round.phase') == 'aim'
    assert not p.errors
    ctx.close()


def test_swipe_length_limits_power_and_camera_chases_disc(site, browser):
    ctx, p = open_game(site, browser)
    p.click('#play')
    # A fast but short swipe is a soft throw: full power takes 40 % of the screen height.
    swipe(p, .3)
    assert p.evaluate('round.shot.power') == pytest.approx(.3, abs=.03)
    first = p.evaluate('Math.hypot(...round.shot.velocity)')
    p.evaluate('finishFlight()')
    # A long but slow swipe is soft too: 296 px in 300 ms is under half the full speed.
    swipe(p, 1, ms=300)
    assert p.evaluate('round.shot.power') == pytest.approx((296 / 300 / (740 * .0028)) ** 1.25, abs=.03)
    p.evaluate('finishFlight()')
    # Back to the tee, so the full throw is not a putt beside the basket.
    p.evaluate('current().lie=[0,0]')
    swipe(p, 1)
    assert p.evaluate('round.shot.power') == pytest.approx(1, abs=.02)
    assert p.evaluate('Math.hypot(...round.shot.velocity)') > first * 1.5
    # In flight the camera follows a few metres behind the disc.
    gap = p.evaluate("""() => {
      round.time=flight.duration*.5;for(let i=0;i<120;i++)drawScene(.016);
      const d=flightPoint(flight,round.time);return scene3d.camera.position.distanceTo(new scene3d.T.Vector3(d.x,d.y,d.z));
    }""")
    assert 4 < gap < 8
    p.evaluate('finishFlight()')
    # Back on the ground the eyes return to the new lie before the next disc is held.
    p.wait_for_function('!scene3d.moving')
    eye = p.evaluate('(()=>{const l=current().lie;return scene3d.camera.position.distanceTo(new scene3d.T.Vector3(l[0],ground(HOLES[round.hole],...l)+1.5,l[1]));})()')
    assert eye < .05
    assert p.evaluate('scene3d.heldDisc.visible')
    assert not p.errors
    ctx.close()


def test_flight_catches_determinism_ghost_and_hazards(site, browser):
    ctx, p = open_game(site, browser)
    result = p.evaluate("""() => {
      const h=HOLES[0],s={lie:[0,0],angle:0,disc:1,power:.5,curve:.2,seed:73};
      const a=fly(s,h),b=fly(s,h),ghost=fly(s,h,false),miss=distance(a.lie,ghost.lie);
      const box={x:0,y:ground(h,...h.basket)+.9,z:45};
      const empty={...h,trees:[],rocks:[],hill:0,wind:[0,0],basket:[100,100],water:[]};
      // Water where the disc would land, and an out-of-bounds line halfway to its landing.
      const dry=fly({...s,curve:0,disc:2,power:1},empty,false),side=fly({...s,angle:Math.PI/2,curve:0,disc:2,power:1},empty,false);
      const w=fly({...s,curve:0,disc:2,power:1},{...empty,water:[{x:dry.lie[0],z:dry.lie[1],rx:10,rz:5}]},false);
      const ob=fly({...s,angle:Math.PI/2,curve:0,disc:2,power:1},{...empty,ob:side.lie[0]/2},false);
      const tree=fly({...s,angle:0,curve:0,disc:2,power:1},{...empty,trees:[[0,12,.5,8,'birch']]},false);
      return {same:JSON.stringify(a)===JSON.stringify(b),miss,slow:catches(h,box,3),fast:catches(h,box,12),
        high:catches(h,{...box,y:3},3),w,ob,tree,obLine:side.lie[0]/2};
    }""")
    assert result['same'] and result['miss'] < 2
    assert result['slow'] and not result['fast'] and not result['high']
    for key in ['w', 'ob']:
        assert result[key]['penalty'] == 1
    assert result['w']['reason'] == 'water' and result['ob']['reason'] == 'ob'
    assert result['ob']['lie'][0] <= result['obLine']
    assert result['tree']['reason'] == 'tree'
    tilt = p.evaluate("""() => {
      const h={...HOLES[0],trees:[],rocks:[],hill:0,wind:[0,0],basket:[100,100],water:[]};
      const side=curve=>{const f=fly({lie:[0,0],angle:0,disc:1,power:.8,curve,seed:1,origin:[0,1.5,0],velocity:[0,4,22]},h,false);
        return {early:flightPoint(f,f.duration*.3).x,end:flightPoint(f,f.duration).x};};
      return {left:side(1),flat:side(0),right:side(-1)};
    }""")
    # A tilt pulls the disc to one side, the opposite tilt to the other, building up over the flight.
    assert tilt['left']['end'] - tilt['flat']['end'] > 3
    assert tilt['flat']['end'] - tilt['right']['end'] > 3
    assert abs(tilt['left']['early'] - tilt['flat']['early']) < abs(tilt['left']['end'] - tilt['flat']['end'])
    assert not p.errors
    ctx.close()


@pytest.mark.parametrize('kind', ['tree', 'rock'])
def test_collision_lie_allows_next_throw_away(site, browser, kind):
    ctx, p = open_game(site, browser)
    result = p.evaluate("""kind => {
      const h={...HOLES[0],trees:[],rocks:[],hill:0,wind:[0,0],basket:[100,100],water:[]};
      if(kind==='tree')h.trees=[[0,12,.5,8,'birch']];
      else h.rocks=[[0,12,7]];  // tall enough to stand in the higher v5 flight
      const shot={lie:[0,0],angle:0,disc:2,power:1,curve:0,seed:1};
      const first=fly(shot,h,false);
      const second=fly({...shot,lie:first.lie,angle:Math.PI},h,false);
      return {reason:first.reason,clearance:distance(first.lie,[0,12]),
        moved:distance(first.lie,second.lie),next:second.reason};
    }""", kind)
    assert result['reason'] == kind
    assert result['clearance'] > (.6 if kind == 'tree' else 7)
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
            p.evaluate('(s)=>startShot(s)', shot)
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
    assert p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))['frisbeegolf|v5'].score") == sum(scores) - 30
    assert p.evaluate("[-2,0,5].map(n=>AiPelitScores.scoreText('frisbeegolf',n))") == ['−2', 'E', '+5']
    for sel in ['#next', '#toMenu', '#scoreRows']:
        b = p.locator(sel).bounding_box()
        assert b['y'] >= 0 and b['y'] + b['height'] <= 740
    p.click('#next')
    assert p.evaluate('round.hole===0&&current().strokes===0')
    assert not p.errors
    ctx.close()


SWIPE_PLAN = """() => {
  // Try swipes without throwing: each candidate runs the real gesture code up to the launch,
  // is cancelled, and its launch is flown on the side. The best one's aim and swipe are returned.
  const c=document.getElementById('scene'),r=c.getBoundingClientRect(),x=r.left+r.width*.5,y=r.top+r.height*.72;
  const h=HOLES[round.hole],lie=current().lie,dist=distance(lie,h.basket);
  const base=Math.atan2(h.basket[0]-lie[0],h.basket[1]-lie[1]),keep=[view.yaw,view.pitch,aim.angle];
  let t=performance.now();
  Object.defineProperty(performance,'now',{value:()=>t,configurable:true,writable:true});
  c.setPointerCapture=c.releasePointerCapture=()=>{};
  const send=(type,px,py)=>c.dispatchEvent(new PointerEvent(type,{pointerId:1,clientX:px,clientY:py,bubbles:true,cancelable:true,pointerType:'touch',isPrimary:true}));
  let best=null,cost=Infinity;
  try{
    const powers=dist<10?[.15,.25,.35,.45,.55,.7,.85,1]:Array.from({length:19},(_,i)=>.1+i*.05);
    for(let ai=-6;ai<=6&&cost>-1000;ai++)for(const power of powers){
      const yaw=base+ai*.03;view.yaw=aim.angle=yaw;view.pitch=-5;drawScene(0);
      send('pointerdown',x,y);t+=10;send('pointermove',x,y-power*r.height*.4);
      const launch=makeSwipeLaunch(),shot={pitch:launch.pitch,angle:launch.angle,power:aim.power,curve:aim.curve,disc:1,
        lie:lie.slice(),seed:12345+round.seq*7919,origin:launch.origin,velocity:launch.velocity};
      send('pointercancel',x,y);
      const f=fly(shot,h),k=f.holed?-1000:distance(f.lie,h.basket)+(f.penalty?100:0);
      if(k<cost){cost=k;best={yaw,power};}
      if(k===-1000)break;
    }
  }finally{delete performance.now;delete c.setPointerCapture;delete c.releasePointerCapture;
    [view.yaw,view.pitch,aim.angle]=keep;drawScene(0);}
  return best;
}"""


def test_complete_nine_holes_by_swiping(site, browser):
    """The course can be finished with the one disc by swiping alone, and the round goes to the v5 list."""
    ctx, p = open_game(site, browser)
    p.click('#play')
    scores = []
    for hole in range(9):
        for _ in range(8):
            if p.evaluate("round.phase!=='aim'"):
                break
            p.wait_for_function("round.phase==='aim'&&!scene3d.moving")
            plan = p.evaluate(SWIPE_PLAN)
            p.evaluate('(y)=>{view.yaw=aim.angle=y;view.pitch=-5;drawScene(0);}', plan['yaw'])
            strokes = p.evaluate('current().strokes')
            swipe(p, plan['power'])
            assert p.evaluate('current().strokes') == strokes + 1
            assert p.evaluate('round.shot.disc') == 1 and p.evaluate('!!round.shot.velocity')
            p.evaluate('finishFlight()')
        assert p.evaluate('current().done'), (hole, p.evaluate('round'))
        scores.append(p.evaluate('current().strokes'))
        assert scores[-1] <= p.evaluate('HOLES[round.hole].par+1'), hole
        if hole < 8:
            p.click('#next')
    assert p.evaluate('round.phase') == 'end'
    assert p.locator('#ai-pelit-nimi').is_visible()
    total = sum(scores) - 30
    assert p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))['frisbeegolf|v5'].score") == total
    assert p.evaluate("load('ennatys',null)") == total
    assert not p.errors
    ctx.close()


def test_reload_rotate_and_midflight_save(site, browser):
    ctx, p = open_game(site, browser)
    p.click('#play')
    swipe(p, .4)
    p.evaluate('finishFlight()')
    before = p.evaluate('JSON.stringify(round)')
    p.reload()
    p.click('#resume')
    assert p.evaluate('JSON.stringify(round)') == before
    turn(p, {'width': 740, 'height': 360})
    assert p.evaluate('JSON.stringify(round)') == before
    swipe(p, .6)
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
            oldseq = p.evaluate('round.seq')
            swipe(p, .38)
            host.wait_for_function("round.phase==='fly'")
            if i:
                p.evaluate('(seq)=>R.send({t:"shot",round:roomRound,seq,angle:0,disc:1,power:.3,curve:0})', oldseq)
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
    swipe(host, .38); host.evaluate('finishFlight()')
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
    swipe(host, .38); host.evaluate('finishFlight()')
    host.wait_for_function('R.paused'); host.click('#aipr-goOn')
    other.wait_for_function('round.turn===2&&round.players[1].done')
    assert other.evaluate('round.players[1].scores[0]') == 6
    other.wait_for_function('!R.paused')
    swipe(other, .4)
    host.wait_for_function("round.phase==='fly'&&round.players[2].strokes===1")
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
    swipe(p, .5)
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
    hgame.wait_for_function('!scene3d.moving')
    old_angle = hgame.evaluate('aim.angle')
    host.mouse.move(scene['x'] + 60, scene['y'] + scene['height'] * .3)
    host.mouse.down(); host.mouse.move(scene['x'] + 100, scene['y'] + scene['height'] * .3, steps=4)
    assert hgame.evaluate('aim.angle') == pytest.approx(old_angle - 40 / scene['width'] * math.pi)
    host.mouse.up()
    swipe(host, .4, game=hgame, root=hf)
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
    assert not p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono')||'{}')['frisbeegolf|v5']")
    assert 'Vanha kierros, ei tuloslistalle' in p.locator('#cardTotal').inner_text()
    assert not p.errors
    ctx.close()


def test_room_speaking_label_clears_landscape_roster(site, _playwright):
    site.build(ROOT / 'games')
    browser = _playwright.chromium.launch(args=GPU_ARGS + [
        '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'])
    relay, contexts = Relay(), []
    def phone(name):
        ctx = browser.new_context(viewport={'width': 740, 'height': 360}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.grant_permissions(['microphone'])
        ctx.add_init_script('window.__aiPelitHuoneSivu=true;')
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi'," + json.dumps(json.dumps(name)) + ")")
        p = ctx.new_page()
        relay.attach(p)
        p.goto(site.url + URL)
        p.click('#friends')
        return p
    try:
        host = phone('Testi1'); host.click('#aipr-create'); host.wait_for_url('**/huone/**')
        host.wait_for_function("document.getElementById('game')?.contentWindow?.AiPelitRooms?.isHost")
        code = host.locator('#code b').inner_text()
        guest = phone('Testi2'); guest.fill('#aipr-codeIn', code); guest.click('#aipr-joinBtn')
        guest.wait_for_url('**/huone/**')
        for p in (host, guest):
            p.wait_for_function('AiPelitRoomShell.state.voice.calls===1', timeout=15000)
        host.frame_locator('#game').locator('#aipr-start').click()
        host.frame_locator('#game').locator('#controls').wait_for(state='visible')
        mic = guest.locator('#aipr-mic').bounding_box()
        guest.mouse.move(mic['x'] + mic['width']/2, mic['y'] + mic['height']/2)
        guest.mouse.down()
        label = host.locator('#aipr-talk')
        label.wait_for(state='visible')
        host.wait_for_function("document.getElementById('aipr-talk').textContent.includes('Testi2')")
        bubble = label.bounding_box()
        roster = host.frame_locator('#game').locator('#roster').bounding_box()
        hud = host.frame_locator('#game').locator('#hud').bounding_box()
        assert hud['y'] + hud['height'] <= bubble['y']
        assert bubble['y'] + bubble['height'] <= roster['y']
        assert 'Testi2' in label.inner_text()
        guest.mouse.up()
        label.wait_for(state='hidden')
    finally:
        for ctx in contexts:
            ctx.close()
        browser.close()


def test_host_drops_a_bad_swipe_path_but_keeps_the_throw(site, browser):
    """A guest's swipe arrives as numbers; too fast, released far away or not numbers, the
    host flies the plain aimed throw instead of trusting the path."""
    ctx, p = open_game(site, browser)
    p.click('#play')
    p.wait_for_function("round.phase==='aim'")
    result = p.evaluate("""() => {
      const base={angle:0,power:.5,curve:0,disc:1}, eye=ground(HOLES[0],0,0)+1.5, out=[];
      for (const extra of [
        {origin:[0,eye,0],velocity:[0,5,20]},
        {origin:[0,eye,0],velocity:[0,5,60]},
        {origin:[9,eye,0],velocity:[0,5,20]},
        {origin:[0,eye+9,0],velocity:[0,5,20]},
        {origin:[0,eye,0],velocity:[0,'5',20]},
        {origin:[0,eye,0],velocity:[0,5]},
      ]) {
        const ok=startShot({...base,...extra});
        out.push([ok,!!round.shot.velocity]);
        round.phase='aim';current().strokes=0;
      }
      return out;
    }""")
    assert result == [[True, True]] + [[True, False]] * 5
    assert not p.errors
    ctx.close()
