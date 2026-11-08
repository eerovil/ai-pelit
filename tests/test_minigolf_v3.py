"""Minigolf: real pull controls, complete rounds, physics and durable saves."""
import math
import pytest
from conftest import ROOT, turn

URL = 'games/minigolf/v3/'
PLAN = """() => {
 window.planShot = (hole, start, target) => {
   const h=HOLES[hole], goal=target||h.cup, base=Math.atan2(goal[1]-start.y,goal[0]-start.x);
   let best=null, cost=Infinity;
   for(let ai=-24;ai<=24;ai++) for(let pi=3;pi<=100;pi++) {
     const a=base+ai*.025,p=pi/100,b=simulateShot(h,start,a,p,round?round.time:0);
     if(b.water)continue;
     const d=b.holed&&!target?-100:Math.hypot(b.x-goal[0],b.y-goal[1]);
     if(d<cost){cost=d;best={a,p,cost:d};} if(d===-100)return best;
   }
   return best;
 };
 window.runBall = () => { for(let i=0;i<26*60 && round.phase==='roll';i++)step(1/60); };
}"""


def open_game(site, browser, size=(360,740)):
    site.build(ROOT/'games')
    ctx=browser.new_context(viewport={'width':size[0],'height':size[1]},is_mobile=True,has_touch=True)
    p=ctx.new_page(); p.errors=[]
    p.on('pageerror',lambda e:p.errors.append(str(e)))
    p.goto(site.url+URL)
    p.evaluate(PLAN)
    return ctx,p


def pull(p,a,power):
    x,y,dx,dy=p.evaluate('''([a,p])=>{const v=screenVector(Math.cos(a),Math.sin(a));
      return [W/2,H/2,-v[0]*p*Math.min(W,H)*.3,-v[1]*p*Math.min(W,H)*.3];}''',[a,power])
    size=p.viewport_size
    assert 0<=x+dx<size['width'] and 0<=y+dy<size['height']
    p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+dx,y+dy,steps=4);p.mouse.up()


@pytest.mark.parametrize('size',[(360,640),(360,740),(390,844),(740,360)])
def test_controls_and_layout(site,browser,size):
    ctx,p=open_game(site,browser,size)
    for sel in ['#play','#friends','#scores']:
        b=p.locator(sel).bounding_box();assert b['y']>=0 and b['y']+b['height']<=size[1]
    p.click('#play')
    # A tap cannot count as a stroke, nor can a second finger steal a drag.
    p.tap('#c');assert p.evaluate('round.players[0].strokes')==0
    w,h=size;p.mouse.move(w/2,h/2);p.mouse.down();p.mouse.move(w/2,h/2+40)
    p.dispatch_event('#c','pointerdown',{'pointerId':2,'clientX':20,'clientY':200})
    p.dispatch_event('#c','pointerup',{'pointerId':2,'clientX':20,'clientY':260})
    assert p.evaluate('dragging.id')==1 and p.evaluate('round.players[0].strokes')==0
    p.mouse.move(w/2,h/2+1)
    assert p.evaluate('aim&&aim.p===MIN_POWER&&aim.length>0')
    if size==(360,740):p.screenshot(path='/var/tmp/minigolf453_tiny.png')
    p.mouse.up();assert p.evaluate('round.players[0].strokes')==1
    p.evaluate('runBall()')
    assert p.evaluate('Math.hypot(round.players[0].ball.x-HOLES[0].tee[0],round.players[0].ball.y-HOLES[0].tee[1])>.1')
    pull(p,-math.pi/2,1)
    assert p.evaluate('round.players[0].strokes')==2
    p.evaluate('runBall()')
    assert p.evaluate("round.phase !== 'roll'")
    p.evaluate("round.hole=8;round.players[0].scores=[2,2,3,3,3,3,3,3,4];round.phase='end';finishRecord();showCard();for(let i=0;i<10;i++){const r=document.createElement('div');r.textContent=(i+1)+'. Testi 25';$('board').append(r);}")
    for sel in ['#next','#toMenu','#scoreRows']:
        b=p.locator(sel).bounding_box();assert b['y']>=0 and b['y']+b['height']<=size[1]
    assert not p.errors
    ctx.close()


@pytest.mark.parametrize('size',[(360,640),(390,844),(740,360)])
def test_menu_shows_top_ten_and_fits(site,browser,size):
    site.build(ROOT/'games')
    ctx=browser.new_context(viewport={'width':size[0],'height':size[1]},is_mobile=True,has_touch=True)
    rows=[{'rank':i+1,'name':'Testi'+str(i),'score':24+i,'version':1} for i in range(10)]
    ctx.route('**/api/scores?game=minigolf*',lambda r:r.fulfill(json={'rows':rows}))
    # The fullest menu: a record and an unfinished round too.
    ctx.add_init_script("""localStorage.setItem('ai-pelit:minigolf:paras','24');""")
    p=ctx.new_page();p.goto(site.url+URL);p.click('#play');p.evaluate('keepRound()');p.reload()
    p.wait_for_function("$('menuBoard').children.length===10")
    assert p.locator('#menuBoard').inner_text().startswith('1.')
    for sel in ['#best','#play','#resume','#friends','#scores','#menuBoard']:
        b=p.locator(sel).bounding_box();assert b['y']>=0 and b['y']+b['height']<=size[1],sel
    assert p.locator('#menuBoard').bounding_box()['height']>=60
    chip=p.locator('#ai-pelit-tulokset-nappi').bounding_box()
    for sel in ['#play','#resume','#friends','#scores']:
        b=p.locator(sel).bounding_box();assert b['y']+b['height']<=chip['y'] or b['x']+b['width']<=chip['x'],sel
    board=p.locator('#menuBoard').bounding_box()
    assert board['y']+board['height']<=chip['y'] or board['x']+board['width']<=chip['x']
    # All ten can be reached: a finger can scroll the list, and nothing above it blocks that.
    assert p.evaluate("""() => {const b=$('menuBoard');b.scrollTop=9999;
      for(let e=b;e;e=e.parentElement)if(getComputedStyle(e).touchAction==='none')return false;
      return b.scrollTop+b.clientHeight>=b.scrollHeight-1;}""")
    # A list that arrives after the round has started stays out of the way.
    p.click('#play');assert p.evaluate("round.phase")=='aim'
    assert not p.locator('#menuBoard').is_visible()
    ctx.close()


def test_tap_hides_the_notice_without_a_stroke(site,browser):
    ctx,p=open_game(site,browser);p.click('#play')
    assert p.inner_text('#notice').startswith('Reikä 1/9')
    p.tap('#c')
    assert p.inner_text('#notice')==''
    assert p.evaluate("round.players[0].strokes===0&&round.phase==='aim'")
    # A room's next state still carries the notice: it stays hidden, and the next notice shows.
    p.evaluate('updateHUD()');assert p.inner_text('#notice')==''
    p.evaluate("round.notice='Par!';updateHUD()");assert p.inner_text('#notice')=='Par!'
    assert not p.errors;ctx.close()


def test_pointer_release_keeps_scaled_power_above_the_minimum(site,browser):
    ctx,p=open_game(site,browser);p.click('#play')
    p.evaluate('askDraw=()=>{}')
    for requested,effective in [(.01,.1),(.4,.4),(1,1)]:
        p.evaluate("round=fresh([{id:'solo',name:'Sinä'}]);showPlay()")
        pull(p,-math.pi/2,requested)
        assert p.evaluate('round.players[0].strokes')==1
        assert p.evaluate('Math.hypot(round.players[0].ball.vx,round.players[0].ball.vy)')==pytest.approx(effective*4.6,rel=.02)
    assert not p.errors;ctx.close()


def test_cup_water_walls_and_limit(site,browser):
    ctx,p=open_game(site,browser)
    p.click('#play')
    assert p.evaluate("""() => {
      let h=HOLES[0],firm=golfBall(h.cup);firm.vy=-2.2;golfStep(firm,h,FIXED_DT,0);
      let over=golfBall(h.cup);over.vy=-2.4;golfStep(over,h,FIXED_DT,0);
      let fast=golfBall([2,1.35]);fast.vy=-4.6;
      for(let i=0;i<30;i++)golfStep(fast,h,FIXED_DT,i*FIXED_DT);
      return firm.holed&&!over.holed&&!fast.holed;
    }""")
    p.evaluate("round.hole=5;round.players[0].ball=golfBall([2,5]);round.notice='';showPlay()")
    pull(p,-math.pi/2,.45);p.evaluate('runBall()')
    assert p.evaluate('[round.players[0].strokes,round.players[0].ball.x,round.players[0].ball.y]')==[2,2,5]
    p.evaluate('round.players[0].strokes=5')
    pull(p,math.pi/2,.3);p.evaluate('runBall()')
    assert p.evaluate("round.phase==='hole'&&round.players[0].scores[5]===7")
    assert p.evaluate("""() => {
      let seed=17; const rand=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
      for(const h of HOLES)for(let i=0;i<2000;i++) {
        const b=golfBall([.12+rand()*3.76,.12+rand()*7.76]);
        const a=rand()*Math.PI*2;b.vx=Math.cos(a)*MAX_SPEED;b.vy=Math.sin(a)*MAX_SPEED;
        for(let j=0;j<40;j++) {
          golfStep(b,h,FIXED_DT,j*FIXED_DT);
          if(b.x<BALL_RADIUS-1e-6||b.x>h.w-BALL_RADIUS+1e-6||b.y<BALL_RADIUS-1e-6||b.y>h.h-BALL_RADIUS+1e-6)return false;
        }
      }return true;
    }""")
    assert not p.errors;ctx.close()


def test_reload_during_shot_and_turn(site,browser):
    ctx,p=open_game(site,browser);p.click('#play')
    pull(p,-math.pi/2,.6)
    p.reload();p.click('#resume');p.evaluate(PLAN);p.evaluate('runBall()')
    assert p.evaluate('round.players[0].strokes')==1
    before=p.evaluate('[round.hole,round.players[0].strokes,round.players[0].ball]')
    turn(p,{'width':740,'height':360})
    assert p.evaluate('[round.hole,round.players[0].strokes,round.players[0].ball]')==before
    assert not p.errors;ctx.close()


@pytest.mark.parametrize('size',[(360,740),(740,360)])
def test_every_hole_and_second_round_through_controls(site,browser,size):
    ctx,p=open_game(site,browser,size);p.click('#play')
    # Waypoints tell the search how to navigate bends, not how to force a result.
    waypoints={1:[[.7,2.1]],6:[[.7,4.1],[3.1,2.1]]}
    for hole in range(9):
        targets=waypoints.get(hole,[])+[None]*5
        for target in targets:
            if p.evaluate('round.phase')!='aim':break
            plan=p.evaluate('target=>planShot(round.hole,round.players[0].ball,target)',target)
            assert plan is not None
            pull(p,plan['a'],plan['p']);p.evaluate('runBall()')
        score=p.evaluate('round.players[0].scores[round.hole]')
        assert score and score<=p.evaluate('HOLES[round.hole].par+1'),(hole,score)
        assert p.evaluate('round.players[0].ball.holed'),hole
        if hole<8:p.evaluate('step(1.3)')
    assert p.evaluate("round.phase==='end'")
    assert p.evaluate("load('paras',null)===total(round.players[0])")
    # This phone's first score: the nickname question comes over the card, and the score waits for it.
    assert p.locator('#ai-pelit-nimi').is_visible()
    assert p.evaluate("Object.keys(JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono')||'{}')).length")==1
    p.locator('#ai-pelit-tulokset button',has_text='Sulje').click()
    assert p.locator('#next').is_visible()
    p.click('#next');assert p.evaluate("round.hole===0&&round.phase==='aim'&&round.players[0].strokes===0")
    pull(p,-math.pi/2,.58);p.evaluate('runBall()');assert p.evaluate('round.players[0].strokes')==1
    assert not p.errors;ctx.close()


def test_hole_records_show_on_the_card_and_name_is_asked_once(site,browser):
    ctx,p=open_game(site,browser);p.click('#play')
    finish="round.hole=8;round.phase='end';round.players[0].scores=[3,3,3,3,3,3,3,3,3];finishRecord();showCard()"
    p.evaluate("save('reiat',[1,2,2,3,3,3,3,3,4])");p.evaluate(finish)
    rows=p.evaluate("[...$('scoreRows').rows].map(r=>[...r.cells].map(c=>c.textContent))")
    assert rows[0]==['Reikä','Par','Sinä','Ennätys']
    assert rows[1]==['1','2','3','1'] and rows[9]==['9','4','3','3']
    assert rows[10]==['Yht.','26','27','23']
    assert p.locator('#ai-pelit-nimi').is_visible()
    p.locator('#ai-pelit-tulokset button',has_text='Sulje').click()
    for sel in ['#next','#toMenu','#scoreRows']:
        b=p.locator(sel).bounding_box();assert b['y']>=0 and b['y']+b['height']<=740
    p.click('#next');p.evaluate(finish)
    assert p.locator('#ai-pelit-nimi').count()==0
    assert not p.errors;ctx.close()


def test_rotate_while_aiming_preserves_direction_and_power(site,browser):
    ctx,p=open_game(site,browser);p.click('#play')
    p.mouse.move(180,370);p.mouse.down();p.mouse.move(180,425)
    before=p.evaluate('[aim.a,aim.p]')
    turn(p,{'width':740,'height':360})
    p.mouse.move(370,180)
    assert p.evaluate('[aim.a,aim.p]')==pytest.approx(before)
    # Browsers may cancel the pointer during rotation: keep the aim, but never fire by itself.
    p.dispatch_event('#c','pointercancel',{'pointerId':1})
    assert p.evaluate('round.players[0].strokes')==0
    assert p.evaluate('parkedAim')
    p.mouse.up();p.mouse.click(370,180)
    assert p.evaluate('round.players[0].strokes')==1
    assert not p.errors;ctx.close()



@pytest.mark.parametrize('size',[(360,740),(390,844),(740,360)])
def test_aim_line_alone_shows_the_power(site,browser,size):
    """#438: no power bar; the aim line grows longer, thicker and redder with the pull."""
    ctx,p=open_game(site,browser,size);p.click('#play')
    assert p.locator('#power').count()==0
    p.evaluate("window.lines=[];const d=drawAimLine;drawAimLine=(x,y,a,q)=>{lines.push(q);d(x,y,a,q)}")
    w,h=size;p.mouse.move(w/2,h/2);p.mouse.down()
    # Pull straight back from the cup on screen: down upright, left on its side.
    back=(0,1) if h>w else (-1,0)
    p.mouse.move(w/2+back[0]*25,h/2+back[1]*25,steps=2);soft=p.evaluate('aim.p')
    if size==(360,740):p.screenshot(path='/var/tmp/minigolf438_soft.png')
    assert p.evaluate('lines[lines.length-1]')==pytest.approx(soft)
    p.mouse.move(w/2+back[0]*150,h/2+back[1]*150,steps=3);hard=p.evaluate('aim.p')
    if size==(360,740):p.screenshot(path='/var/tmp/minigolf438_hard.png')
    if size==(740,360):p.screenshot(path='/var/tmp/minigolf438_side.png')
    assert soft<.3 and hard==1
    assert p.evaluate('lines[lines.length-1]')==1
    assert p.evaluate('aimLineLength(%s)<aimLineLength(%s)'%(soft,hard))
    assert p.evaluate("aimLineColor(0)")=='rgb(255,242,188)' and p.evaluate("aimLineColor(1)")=='rgb(238,74,52)'
    # The full-power arrow points at the cup and its tip stays on the course and the screen.
    tip=p.evaluate("(()=>{const b=round.players[0].ball,t=[b.x+Math.cos(aim.a)*aimLineLength(1),b.y+Math.sin(aim.a)*aimLineLength(1)];return [t[0],t[1],...P(...t)]})()")
    assert 0<tip[0]<4 and 0<tip[1]<4 and 0<tip[2]<w and 0<tip[3]<h
    # Letting go clears the line; nothing draws it until the next pull.
    p.mouse.up();p.evaluate('runBall()');n=p.evaluate('lines.length');p.evaluate('draw()')
    assert p.evaluate('aim')is None and p.evaluate('lines.length')==n
    assert not p.errors
    ctx.close()
