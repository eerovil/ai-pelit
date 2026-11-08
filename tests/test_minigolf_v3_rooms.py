"""Minigolf's host owns turns, including reloads, skipping and final delivery."""
import json
import math
import pytest
from conftest import ROOT
from test_rooms_lib import Relay
from test_minigolf_v3 import pull, PLAN

@pytest.fixture
def golf_phones(site,browser):
    site.build(ROOT/'games');relay=Relay();contexts=[]
    def phone(name):
        ctx=browser.new_context(viewport={'width':360,'height':740},is_mobile=True,has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi',"+json.dumps(json.dumps(name))+")")
        p=ctx.new_page();p.errors=[];p.on('pageerror',lambda e:p.errors.append(str(e)))
        relay.attach(p);p.goto(site.url+'games/minigolf/v3/');p.evaluate(PLAN)
        return p
    yield phone
    for c in contexts:
        for p in c.pages:
            if not p.is_closed():p.evaluate('R.leave()')
    for c in contexts:c.close()


def room(phone,n):
    host=phone('Testi1');host.click('#friends');host.click('#aipr-create')
    host.wait_for_function('R.isHost&&R.members.length===1')
    code=host.evaluate('R.code');pages=[host]
    for i in range(1,n):
        p=phone('Testi'+str(i+1));p.click('#friends');p.fill('#aipr-codeIn',code);p.click('#aipr-joinBtn')
        p.wait_for_function('R.inRoom');pages.append(p)
    host.wait_for_function(f'R.members.filter(p=>p.on).length==={n}')
    host.click('#aipr-start')
    for p in pages:p.wait_for_function("round&&round.phase==='aim'")
    return pages


@pytest.mark.parametrize('n',[2,3,6])
def test_every_player_can_putt_and_reload(golf_phones,n):
    pages=room(golf_phones,n);host=pages[0]
    host.tap('#c')
    assert host.evaluate("round.players[0].strokes===0&&round.phase==='aim'")
    # Another phone cannot play the host's turn.
    pages[-1].evaluate("R.send({t:'shot',round:roomRound,seq:round.seq,a:0,p:1})")
    # Every phone shows who plays, in the ball's colour, clear of the course.
    for p in pages:
        assert p.locator('#who span').count()==n
        assert p.locator('#who .on').inner_text()=='Testi1'
        box=p.locator('#who').bounding_box();assert box['y']+box['height']<=p.evaluate('P(0,0)[1]-.12*scale')+1
        for row in p.locator('#who span').all():
            b=row.bounding_box();assert b['x']>=0 and b['x']+b['width']<=360
    pages[1].evaluate("window.heard=[];const s=sound;sound=(n,v)=>{heard.push(n);s(n,v)}")
    for i,p in enumerate(pages):
        p.wait_for_function(f'round.turn==={i}')
        assert host.evaluate('round.players[round.turn].strokes')==0
        pull(p,-math.pi/2,.25)
        host.wait_for_function("round.phase==='roll'")
        # The same shot arriving twice is still one stroke.
        if i==1:p.evaluate("R.send({t:'shot',round:roomRound,seq:round.seq,a:0,p:1})")
        host.evaluate('runBall()')
    for p in pages:p.wait_for_function('round.turn===0&&round.players.every(p=>p.strokes===1)')
    assert 'puu' in pages[1].evaluate('heard')
    guest=pages[1];guest.reload()
    guest.wait_for_function('round&&round.players.every(p=>p.strokes===1)')
    assert guest.evaluate('round.seq')==host.evaluate('round.seq')
    for p in pages:assert not p.errors


def test_host_reload_sends_everyone_back_to_the_room(golf_phones):
    host,guest=room(golf_phones,2)
    pull(host,-math.pi/2,.25);host.evaluate('runBall()')
    guest.wait_for_function('round.turn===1')
    host.reload()
    guest.wait_for_function('round===null&&!R.paused')
    host.wait_for_function('R.isHost&&R.members.filter(p=>p.on).length===2')
    host.click('#aipr-start')
    for p in (host,guest):
        p.wait_for_function("round&&round.phase==='aim'&&round.hole===0&&round.players.every(p=>p.strokes===0)")
        assert not p.errors


@pytest.mark.parametrize('n',[2,3])
def test_starting_player_rotates_each_hole_and_next_round(golf_phones,n):
    pages=room(golf_phones,n);host=pages[0]
    assert host.evaluate('[round.hole,round.starterId===round.players[0].id,round.turn]')==[0,True,0]
    # Finish each hole by state, but enter the next one through the game's real control.
    for hole in range(1,9):
        host.evaluate("""round.players.forEach(p=>p.scores[round.hole]=3);
          round.phase='hole';showCard();sendState();""")
        host.click('#next')
        expected=hole%n
        for p in pages:p.wait_for_function(f'round.hole==={hole}&&round.turn==={expected}')
        assert host.evaluate(f'round.starterId===round.players[{expected}].id')
        if n==3 and hole==4:
            pages[1].reload()
            pages[1].wait_for_function(f'round&&round.hole===4&&round.turn==={expected}&&round.starterId===round.players[{expected}].id')
        if n==3 and hole==1:host.screenshot(path='/var/tmp/minigolf453_rotation.png')
    # The next full round continues with the player after hole 9's starter.
    host.evaluate("""round.players.forEach(p=>p.scores[8]=3);round.phase='end';
      finishRecord();R.deliver({t:'result',round:roomRound,state:round});R.endRound();showCard();sendState();""")
    for p in pages:
        p.wait_for_function("round&&round.phase==='end'")
        p.click('#next')
    host.wait_for_function("R.isHost&&!R.canStop")
    host.reload()
    for p in pages[1:]:p.wait_for_function('round===null')
    host.wait_for_function(f'R.isHost&&R.members.filter(p=>p.on).length==={n}')
    host.click('#aipr-start')
    expected=9%n
    for p in pages:p.wait_for_function(f"round&&round.hole===0&&round.turn==={expected}&&round.starterId===round.players[{expected}].id")
    for p in pages:assert not p.errors


def test_skip_rejoin_delivery_once_and_next_round(golf_phones):
    pages=room(golf_phones,3);host,guest,other=pages
    guest.evaluate('R.leave()');host.wait_for_function('R.members.some(p=>!p.on)')
    pull(host,-math.pi/2,.25);host.evaluate('runBall()')
    host.wait_for_function('R.paused');host.click('#aipr-goOn')
    other.wait_for_function('round.turn===2&&round.players[1].scores[0]===7')
    guest.click('#friends');guest.click('#aipr-again')
    guest.wait_for_function('round&&round.turn===2&&round.players[1].scores[0]===7')
    # Last hole: set up the final putt, then finish by the actual pointer control.
    host.evaluate("""round.hole=8;round.turn=0;round.seq++;round.phase='aim';round.notice='';
      round.players.forEach((p,i)=>{p.scores=[2,2,3,3,3,3,3,3];if(i)p.scores.push(3);p.strokes=0;p.ball=golfBall([2,1.7]);});
      showPlay();sendState();""")
    for p in pages:p.wait_for_function('round.hole===8&&round.turn===0')
    # Reload a guest while the final result is delivered.
    guest.reload();pull(host,-math.pi/2,.22);host.evaluate('runBall()')
    for p in pages:p.wait_for_function("round&&round.phase==='end'")
    for p in pages:
        assert p.evaluate("load('kaverit',{}).rounds")==1
        assert p.evaluate("load('paras',null)") is None
        assert p.evaluate("load('reiat',null)") is None
    host.evaluate("R.deliver({t:'result',round:roomRound,state:round})")
    guest.reload();guest.wait_for_function("round&&round.phase==='end'")
    assert guest.evaluate("load('kaverit',{}).rounds")==1
    for p in pages:
        if not p.locator('#aipr').is_visible():p.click('#next')
        assert p.locator('#aipr details summary').inner_text().startswith('Tuloskortti')
    host.click('#aipr-start')
    for p in pages:
        p.wait_for_function("round&&round.phase==='aim'&&round.hole===0&&round.players.every(p=>p.strokes===0)")
        assert not p.errors
    host.evaluate('R.stopRound()')
    for p in pages:p.wait_for_function('round===null')


def test_others_see_the_pullers_power_line(golf_phones):
    """#438: the line is the only power display, so every phone in the room draws it."""
    host,guest=room(golf_phones,2)
    guest.evaluate("window.lines=[];const d=drawAimLine;drawAimLine=(x,y,a,q)=>{lines.push(q);d(x,y,a,q)}")
    assert guest.locator('#power').count()==0
    host.mouse.move(180,370);host.mouse.down();host.mouse.move(180,520,steps=4)
    guest.wait_for_function("aim&&aim.p===1&&lines.length&&lines[lines.length-1]===1")
    host.mouse.up();host.wait_for_function("round.phase==='roll'")
    guest.wait_for_function("aim===null")


def test_host_clamps_a_guests_tiny_visible_putt(golf_phones):
    host,guest=room(golf_phones,2)
    # Move to the guest's turn without changing the behavior under test.
    host.evaluate("round.turn=1;round.seq++;sendState();askDraw=()=>{}")
    guest.wait_for_function('round.turn===1')
    guest.evaluate("R.send({t:'shot',round:roomRound,seq:round.seq,a:0,p:.01})")
    host.wait_for_function("round.phase==='roll'")
    assert host.evaluate("[round.players[1].strokes,round.players[1].ball.vx,round.players[1].ball.vy]")==pytest.approx([1,.1*4.6,0])
    guest.wait_for_function("round.phase==='roll'&&round.players[1].strokes===1")
