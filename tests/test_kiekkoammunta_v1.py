"""Clay shooting: actual drag/release, both complete rounds, saves and phone layouts."""
import pytest
from conftest import ROOT, turn

URL = 'games/kiekkoammunta/v1/'


def open_game(site, browser, size=(360, 740)):
    site.build(ROOT / 'games')
    context = browser.new_context(viewport=dict(zip(('width', 'height'), size)), is_mobile=True, has_touch=True)
    context.add_init_script('window.requestAnimationFrame = () => 0;')
    context.route('**/api/scores?*', lambda r: r.fulfill(json={'rows': [
        {'rank': i+1, 'name': 'Testi '+str(i+1), 'score': 25-i} for i in range(10)]}))
    p = context.new_page()
    p.errors = []
    p.on('pageerror', lambda e: p.errors.append(str(e)))
    p.goto(site.url + URL)
    p.evaluate('window.realCatchUp=catchUp;catchUp=()=>{};lastTime=0;draw()')
    return context, p


def shot(p, hit=True):
    # Freeze the real clock; advance flight deliberately, but all aiming/firing uses pointers.
    w, h = p.viewport_size.values()
    p.evaluate('lastTime=performance.now()+1e7')
    p.mouse.move(w/2, h*.72)
    p.mouse.down()
    p.evaluate('step(.45);lastTime=performance.now()+1e7')
    delta = p.evaluate('''hit => {
      const d=round.mode==='trap'?round.discs[0]:round.discs[round.shotIndex];
      const t=direction(d).distance/PELLETS;
      const a=direction({...d,x:d.x+d.vx*t,y:d.y+d.vy*t-1.5*t*t,z:d.z+d.vz*t});
      return [(a.yaw-round.aim.yaw)*scale/1.6+(hit?0:90),-(a.pitch-round.aim.pitch)*scale/1.6];
    }''', hit)
    x, y = w/2+delta[0], h*.72+delta[1]
    assert 0 <= x < w and 0 <= y < h, (x, y, w, h)
    p.mouse.move(x, y, steps=3)
    p.mouse.up()
    p.evaluate('step(.2);draw()')


def settle(p):
    p.evaluate("for(let i=0;i<600&&['flight','gap'].includes(round.phase);i++)step(1/60);draw()")


@pytest.mark.parametrize('mode', ['trap', 'skeet'])
@pytest.mark.parametrize('size', [(360, 740), (740, 360)])
def test_whole_round_and_another(site, browser, mode, size):
    context, p = open_game(site, browser, size)
    p.click('#'+mode)
    p.evaluate('() => {window.sent=[];AiPelitScores.submit=s=>sent.push([round.mode,s]);}')
    for _ in range(25 if mode == 'trap' else 17):
        shots = p.evaluate('entry()[1].length')
        for _ in range(shots):
            shot(p)
        settle(p)
    assert p.evaluate('[round.phase,count(),round.results.filter(v=>v===null).length]') == ['end', 25, 0]
    assert p.evaluate('sent') == [[mode, 25]]
    assert p.evaluate("best(round.mode)") == 25
    p.wait_for_function("document.querySelector('#board').children.length===10", polling=50)
    assert p.locator('#resultScore').inner_text() == '25/25'
    p.click('#again')
    assert p.evaluate('[round.index,count(),round.phase]') == [0, 0, 'ready']
    shot(p); settle(p)
    assert p.evaluate('count()') == 1
    assert not p.errors
    context.close()


def test_trap_second_shot_and_skeet_one_per_target(site, browser):
    context, p = open_game(site, browser)
    p.click('#trap'); shot(p, False)
    assert p.evaluate('[round.phase,round.ammo,count()]') == ['flight', 1, 0]
    shot(p); settle(p)
    assert p.evaluate('count()') == 1
    p.click('#pause'); p.click('#skeet'); shot(p, False)
    assert p.evaluate('round.results[0]') is False
    p.evaluate('fire();step(.3)')
    assert p.evaluate('count()') == 0
    settle(p)
    assert p.evaluate('entry()') == [1, 'HL']
    p.evaluate('call()')
    assert p.evaluate('round.discs.length') == 2
    assert not p.errors
    context.close()


def test_lead_is_needed_and_pattern_misses(site, browser):
    context, p = open_game(site, browser); p.click('#skeet')
    assert p.evaluate('''() => {
      round.index=6;prepare();call();step(.5);
      const d=round.discs[0],a=direction(d),t=a.distance/PELLETS;
      const lead=direction({...d,x:d.x+d.vx*t,y:d.y+d.vy*t-1.5*t*t,z:d.z+d.vz*t});
      const future={...d,x:d.x+d.vx*t,y:d.y+d.vy*t-1.5*t*t,z:d.z+d.vz*t};
      return !shotHits(a,future)&&shotHits(lead,future)&&!shotHits({yaw:2,pitch:1},future);
    }''')
    context.close()


def test_reload_keeps_double_hit_ammo_and_pending_shot(site, browser):
    context, p = open_game(site, browser); p.click('#skeet')
    shot(p); settle(p); shot(p)
    assert p.evaluate('round.results.slice(0,2)') == [True, True]
    before=p.evaluate('[round.index,round.ammo,round.discs,round.results]')
    p.reload(); p.evaluate('catchUp=()=>{}'); p.click('#resume')
    assert p.evaluate('[round.index,round.ammo,round.discs,round.results]') == before
    shot(p); settle(p)
    assert p.evaluate('count()') == 3
    p.evaluate('call();fire();keep()')
    assert p.evaluate('round.shots.length') == 1
    before=p.evaluate('[round.ammo,round.shotIndex,round.shots]')
    p.reload();p.evaluate('catchUp=()=>{}');p.click('#resume')
    assert p.evaluate('[round.ammo,round.shotIndex,round.shots]') == before
    assert not p.errors
    context.close()


@pytest.mark.parametrize('size', [(360,640),(360,740),(390,844),(740,360)])
def test_layout_and_rotation(site,browser,size):
    context,p=open_game(site,browser,size)
    for sel in ['#trap','#skeet']:
        b=p.locator(sel).bounding_box()
        assert b['y']>=0 and b['y']+b['height']<=size[1]
    p.click('#trap');shot(p);settle(p)
    state=p.evaluate('[round.index,round.results,round.aim]')
    turn(p, {'width':740,'height':360})
    assert p.evaluate('[round.index,round.results,round.aim]')==state
    # Fully populated result must keep actions and all ten rows reachable.
    p.evaluate("round.index=24;round.offset=24;round.results=Array(24).fill(true).concat(null);prepare()")
    shot(p);settle(p)
    p.wait_for_function("document.querySelector('#board').children.length===10", polling=50)
    for sel in ['#again','#toMenu','#board']:
        b=p.locator(sel).bounding_box()
        assert b['y']>=0 and b['y']+b['height']<=360
    assert p.evaluate("document.querySelector('#board').scrollHeight>document.querySelector('#board').clientHeight")
    assert not p.errors
    context.close()


def test_skeet_sequence_and_taps_without_aiming(site,browser):
    context,p=open_game(site,browser)
    assert p.evaluate('SKEET.reduce((n,e)=>n+e[1].length,0)')==25
    assert p.evaluate('SKEET.slice(13)')==[[4,'HL'],[4,'LH'],[8,'H'],[8,'L']]
    p.click('#trap')
    for _ in range(25):
        p.evaluate('lastTime=performance.now()+1e7')
        p.tap('#c');settle(p)
    assert p.evaluate('count()')<5
    assert not p.errors
    context.close()


def test_other_pointer_and_cancel_never_shoot(site,browser):
    context,p=open_game(site,browser);p.click('#trap')
    p.mouse.move(180,520);p.mouse.down()
    p.dispatch_event('#c','pointerdown',{'pointerId':12,'clientX':30,'clientY':520})
    p.dispatch_event('#c','pointerup',{'pointerId':12,'clientX':30,'clientY':520})
    assert p.evaluate('round.ammo')==2
    p.dispatch_event('#c','pointercancel',{'pointerId':1})
    assert p.evaluate('round.ammo')==2
    assert p.evaluate('pointer') is None
    context.close()


def test_two_trap_shots_in_flight_and_input_time(site, browser):
    context,p=open_game(site,browser);p.click('#trap')
    assert p.evaluate('''() => {
      call();step(.5);
      round.aim={yaw:1,pitch:.8};fire();
      const d=round.discs[0],t=direction(d).distance/PELLETS;
      round.aim=direction({...d,x:d.x+d.vx*t,y:d.y+d.vy*t-1.5*t*t,z:d.z+d.vz*t});
      fire();step(.3);
      return round.results[0]===true&&round.ammo===0;
    }''')
    settle(p)
    assert p.evaluate('''() => {
      call();lastTime=1000;realCatchUp(1499);
      return Math.abs(round.time-.499)<1e-8&&Math.abs(round.discs[0].age-.499)<1e-8;
    }''')
    assert not p.errors
    context.close()


def test_offline_score_queue_and_two_lists(site,browser):
    context,p=open_game(site,browser)
    context.route('**/api/**',lambda r:r.abort())
    p.evaluate("localStorage.setItem('ai-pelit:_pelaaja:kysytty','true')")
    for mode in ['trap','skeet']:
        p.click('#'+mode)
        p.evaluate("round.index=plan().length-1;round.offset=24;round.results=Array(24).fill(false).concat(null);prepare()")
        shot(p);settle(p)
        p.wait_for_function("document.querySelector('#board').textContent.includes('verkkoyhteyden')",polling=50)
        p.click('#toMenu')
    queued=p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))")
    assert {(v['game'],v['board'],v['score']) for v in queued.values()}=={('kiekkoammunta','trap',1),('kiekkoammunta','skeet',1)}
    assert p.evaluate("AiPelitScores.scoreText('kiekkoammunta',18)")=='18/25'
    assert not p.errors
    context.close()


@pytest.mark.parametrize('damage', [
    "r.index=25", "r.offset=7", "r.ammo=-1", "r.shots=[{delay:1}]",
    "r.phase='flight';r.discs=[{done:false}]",
])
def test_invalid_save_does_not_offer_broken_resume(site,browser,damage):
    context,p=open_game(site,browser);p.click('#trap')
    p.evaluate("() => {const r=JSON.parse(localStorage.getItem(KEY+'kierros'));"+damage+";localStorage.setItem(KEY+'kierros',JSON.stringify(r));}")
    p.evaluate('showMenu()')
    assert p.locator('#resume').is_hidden()
    p.click('#skeet')
    assert p.evaluate('round.phase')=='ready'
    assert not p.errors
    context.close()


def test_long_stall_stops_at_next_ready_target(site,browser):
    context,p=open_game(site,browser);p.click('#trap')
    assert p.evaluate('''() => {
      call();lastTime=1000;realCatchUp(86401000);
      return round.index===1&&round.phase==='ready'&&round.results[0]===false&&
        round.results.slice(1).every(v=>v===null)&&validSaved(load('kierros',null));
    }''')
    context.close()


def test_live_animation_receives_real_pointer_events(site,browser):
    site.build(ROOT/'games')
    context=browser.new_context(viewport={'width':360,'height':740},is_mobile=True,has_touch=True)
    p=context.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    p.goto(site.url+URL);p.click('#trap')
    p.mouse.move(180,520);p.mouse.down()
    p.wait_for_function('round.discs[0].age>.1')
    p.mouse.move(200,490);p.mouse.up()
    assert p.evaluate('round.shotIndex')==1
    p.wait_for_function("round.phase==='ready'&&round.index===1")
    assert p.evaluate("validSaved(load('kierros',null))")
    p.click('#pause')
    p.wait_for_function('raf===0')
    assert not errors
    context.close()
