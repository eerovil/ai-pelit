"""Minigolf's host owns turns, including reloads, skipping and final delivery."""
import json
import math
import pytest
from conftest import ROOT
from test_rooms_lib import Relay
from test_minigolf_v1 import pull, PLAN

@pytest.fixture
def golf_phones(site,browser):
    site.build(ROOT/'games');relay=Relay();contexts=[]
    def phone(name):
        ctx=browser.new_context(viewport={'width':360,'height':740},is_mobile=True,has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi',"+json.dumps(json.dumps(name))+")")
        p=ctx.new_page();p.errors=[];p.on('pageerror',lambda e:p.errors.append(str(e)))
        relay.attach(p);p.goto(site.url+'games/minigolf/v1/');p.evaluate(PLAN)
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
    # Another phone cannot play the host's turn.
    pages[-1].evaluate("R.send({t:'shot',round:roomRound,seq:round.seq,a:0,p:1})")
    for i,p in enumerate(pages):
        p.wait_for_function(f'round.turn==={i}')
        assert host.evaluate('round.players[round.turn].strokes')==0
        pull(p,-math.pi/2,.25)
        host.wait_for_function("round.phase==='roll'")
        host.evaluate('runBall()')
    for p in pages:p.wait_for_function('round.turn===0&&round.players.every(p=>p.strokes===1)')
    guest=pages[1];guest.reload()
    guest.wait_for_function('round&&round.players.every(p=>p.strokes===1)')
    assert guest.evaluate('round.seq')==host.evaluate('round.seq')
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
