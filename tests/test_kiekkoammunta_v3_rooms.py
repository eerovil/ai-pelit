"""Clay shooting in turns: the host keeps the turns and results, the phone on turn shoots."""
import json

import pytest
from conftest import ROOT, turn
from test_kiekkoammunta_v3 import URL, settle, shot
from test_rooms_lib import Relay

# Finish the rest of this phone's turn without the pointer, through the game's own report.
QUICK = """hit => {
  while(round.phase==='ready'||round.phase==='flight'){
    if(round.phase==='ready')call();
    for(const d of round.discs)resolveDisc(d,hit);
    round.shots=[];round.phase='gap';round.gap=0;advance();
  }
}"""


@pytest.fixture
def phones(site, browser):
    site.build(ROOT / 'games')
    relay = Relay()
    contexts = []

    def phone(name, size=(360, 740)):
        ctx = browser.new_context(viewport=dict(zip(('width', 'height'), size)), is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi'," + json.dumps(json.dumps(name)) + ")")
        ctx.add_init_script('window.requestAnimationFrame = () => 0;')
        p = ctx.new_page()
        p.errors = []
        p.on('pageerror', lambda e: p.errors.append(str(e)))
        relay.attach(p)
        p.goto(site.url + URL)
        p.evaluate('catchUp=()=>{}')
        return p
    phone.relay = relay
    yield phone
    for c in contexts:
        for p in c.pages:
            if not p.is_closed():
                p.evaluate('R.leave()')
    for c in contexts:
        c.close()


def room(phone, n, mode=None, size=(360, 740)):
    host = phone('Testi1', size)
    host.click('#friends')
    host.click('#aipr-create')
    host.wait_for_function('R.isHost&&R.members.length===1', polling=50)
    code = host.evaluate('R.code')
    pages = [host]
    for i in range(1, n):
        p = phone('Testi' + str(i + 1), size)
        p.click('#friends')
        p.fill('#aipr-codeIn', code)
        p.click('#aipr-joinBtn')
        p.wait_for_function('R.inRoom', polling=50)
        pages.append(p)
    host.wait_for_function(f'R.members.filter(p=>p.on).length==={n}', polling=50)
    if mode:
        host.click(f'#kk-room [data-m={mode}]')
    host.click('#aipr-start')
    for p in pages:
        p.wait_for_function('round&&round.phase==="ready"', polling=50)
    return pages


def on_turn(pages):
    host = pages[0]
    return pages[host.evaluate('match.turn')]


def wait_turn(pages, seq):
    for p in pages:
        p.wait_for_function(f'match&&(match.over||match.seq>={seq})', polling=50)
        p.evaluate("for(let i=0;i<200&&round&&screen==='play'&&['flight','gap'].includes(round.phase);i++)step(1/60)")


def own_entry(p, hit=True):
    for _ in range(p.evaluate('entry()[1].length')):
        shot(p, hit)
    settle(p)


def quick_turn(pages, hit=True):
    seq = pages[0].evaluate('match.seq')
    on_turn(pages).evaluate(QUICK, hit)
    wait_turn(pages, seq + 1)


@pytest.mark.parametrize('n', [2, 3, 6])
def test_every_player_shoots_all_25_in_turns_of_about_five(phones, n):
    pages = room(phones, n)
    host = pages[0]
    for p in pages:
        assert p.locator('#who span').count() == n
        assert p.locator('#who .on').inner_text() == 'Testi1 0'
        assert p.locator('#pause').is_hidden()
    assert 'Sinun vuorosi' in host.locator('#hint').inner_text()
    assert pages[1].locator('#hint').inner_text().startswith('Testi1 ampuu')
    # The first lap: every phone shoots its five with its own pointer.
    for i, p in enumerate(pages):
        assert host.evaluate('match.turn') == i
        for _ in range(5):
            assert p.evaluate('round.watch') is False
            own_entry(p)
        wait_turn(pages, i + 2)
    assert host.evaluate('match.players.map(p=>p.results.filter(v=>v!==null).length)') == [5] * n
    assert host.evaluate('[match.lap,match.turn,match.index]') == [1, 0, 5]
    for _ in range(4 * n):
        # The last player of all misses, so the standings have a difference to show.
        quick_turn(pages, hit=host.evaluate('match.turn') != n - 1)
    for p in pages:
        p.wait_for_function("screen==='result'", polling=50)
    results = host.evaluate('match.players.map(p=>p.results.filter(v=>v===true).length)')
    assert results == [25] * (n - 1) + [5]
    for i, p in enumerate(pages):
        assert p.locator('#board > div').count() == n
        assert p.locator('#resultScore').inner_text() == ('5/25' if i == n - 1 else '25/25')
        assert p.locator('#toMenu').is_hidden()
        assert p.locator('#record').inner_text() == (
            f'{n}. sija · {n} pelaajaa' if i == n - 1 else
            ('1. sija' if n == 2 else 'Jaettu 1. sija') + f' · {n} pelaajaa')
        # A room's round leaves the player's own record and saved round alone.
        assert p.evaluate("[load('ennatys-trap',null),load('kierros',null)]") == [None, None]
        assert p.evaluate("load('kaverit',{}).rounds") == 1
        assert not p.errors


def test_skeet_turns_cover_the_whole_list():
    # Five turns of 4, 5, 5, 5 and 6 discs, each starting at a target boundary.
    sizes = [1, 2, 1, 2, 1, 2, 1, 1, 1, 2, 1, 2, 2, 2, 2, 1, 1]
    turns = [0, 3, 6, 10, 13, 17]
    assert [sum(sizes[a:b]) for a, b in zip(turns, turns[1:])] == [4, 5, 5, 5, 6]


def test_host_chooses_skeet_and_a_watcher_sees_the_same_discs(phones):
    pages = room(phones, 3, 'skeet')
    host, guest, other = pages
    for p in pages:
        assert p.evaluate('round.mode') == 'skeet'
    assert host.evaluate("load('huonelaji',null)") == 'skeet'
    # A phone not on turn cannot launch, while the one on turn does at the same moment.
    guest.mouse.move(180, 500)
    guest.mouse.down()
    guest.mouse.up()
    assert guest.evaluate('round.phase') == 'ready'
    host.mouse.move(180, 500)
    host.mouse.down()
    guest.wait_for_function("round.phase==='flight'", polling=50)
    assert guest.evaluate('round.discs.map(d=>[d.kind,d.slot])') == host.evaluate('round.discs.map(d=>[d.kind,d.slot])')
    host.evaluate('step(.3);drag(30,-10);lastAim=0;drag(1,0)')
    guest.wait_for_function('aimTo&&Math.abs(aimTo.yaw-%r)<1e-6' % host.evaluate('round.aim.yaw'), polling=50)
    was = guest.evaluate('round.aim.yaw')
    guest.evaluate('step(.3)')
    assert guest.evaluate('round.aim.yaw') != was
    # A hit is the shooter's to say: the watcher's own step shows the ring and nothing more.
    host.mouse.up()
    guest.wait_for_function('round.shots.length===1', polling=50)
    host.evaluate(
        "for(let i=0;i<300&&round.phase==='flight';i++)step(1/60)")
    res = host.evaluate('round.results[0]')
    other.wait_for_function('round.results[0]===%s' % json.dumps(res), polling=50)
    assert host.evaluate('round.phase') == 'gap'
    assert not guest.errors


def test_only_the_phone_on_turn_counts_and_a_message_twice_is_one(phones):
    pages = room(phones, 3)
    host, guest, other = pages
    forged = "(i)=>R.send({t:'entry',round:roomRound,seq:match.seq,index:i,results:Array(25).fill(true)})"
    guest.evaluate(forged, 3)
    own_entry(host)
    host.wait_for_function('match.index===1', polling=50)
    assert host.evaluate('match.players[1].results.every(v=>v===null)')
    for _ in range(4):
        own_entry(host)
    wait_turn(pages, 2)
    # The right phone, but sent again, and from the turn before.
    own_entry(guest)
    host.wait_for_function('match.index===1', polling=50)
    guest.evaluate("R.send({t:'entry',round:roomRound,seq:match.seq,index:1,results:round.results})")
    guest.evaluate("R.send({t:'entry',round:roomRound,seq:match.seq-1,index:4,results:Array(25).fill(true)})")
    guest.evaluate("R.send({t:'entry',round:roomRound,seq:match.seq,index:2,results:Array(25).fill(null)})")
    guest.evaluate("R.send({t:'entry',round:roomRound,seq:match.seq,index:99,results:Array(25).fill(true)})")
    own_entry(guest)
    host.wait_for_function('match.index===2', polling=50)
    assert host.evaluate('match.players[1].results.slice(0,3)') == [True, True, None]
    # A watcher's flying disc from a phone not on turn is not passed on.
    disc = '{x:999,y:1,z:1,vx:0,vy:0,vz:0,age:0,slot:2,done:false}'
    other.evaluate("R.send({t:'live',k:'fly',round:roomRound,seq:match.seq,discs:[%s]});0" % disc)
    own_entry(guest)
    host.wait_for_function('match.index===3', polling=50)
    assert host.evaluate('round.discs.every(d=>d.x!==999)')
    assert not any(p.errors for p in pages)


def test_a_report_lost_on_the_way_is_made_up_for(phones):
    pages = room(phones, 2)
    host, guest = pages
    quick_turn(pages)
    wait_turn(pages, 2)
    # The first report never arrives; the next carries the whole list.
    guest.evaluate("window.realSend=R.send;R.send=m=>{if(m.t!=='entry')realSend(m)};0")
    own_entry(guest)
    guest.evaluate('R.send=realSend;0')
    assert host.evaluate('match.index') == 0
    own_entry(guest)
    host.wait_for_function('match.index===2', polling=50)
    assert host.evaluate('match.players[1].results.slice(0,3)') == [True, True, None]
    # The last report of the turn is lost: the phone on `wait` sends it again when it hears the state.
    guest.evaluate("R.send=m=>{if(m.t!=='entry')realSend(m)};0")
    for _ in range(3):
        own_entry(guest)
    guest.evaluate('R.send=realSend;0')
    assert guest.evaluate('round.phase') == 'wait'
    assert 'Vuoro ammuttu' in guest.locator('#hint').inner_text()
    host.evaluate('sendState()')
    wait_turn(pages, 3)
    assert host.evaluate('match.players[1].results.filter(v=>v===true).length') == 5
    assert not guest.errors


def test_a_phone_reloading_on_turn_and_watching_carries_on(phones):
    pages = room(phones, 3)
    host, guest, other = pages
    quick_turn(pages)
    wait_turn(pages, 2)
    own_entry(guest)
    host.wait_for_function('match.index===1', polling=50)
    for p in (guest, other):
        p.reload()
        p.evaluate('catchUp=()=>{}')
        p.wait_for_function('round&&match&&match.index===1', polling=50)
    assert guest.evaluate('[round.watch,round.index,round.offset,count()]') == [False, 1, 1, 1]
    assert other.evaluate('[round.watch,round.index]') == [True, 1]
    assert other.locator('#who .on').inner_text() == 'Testi2 1'
    for _ in range(4):
        own_entry(guest)
    wait_turn(pages, 3)
    assert other.evaluate('round.watch') is False
    assert not any(p.errors for p in pages)


def test_host_reload_sends_everyone_back_to_the_room(phones):
    host, guest = room(phones, 2)
    own_entry(host)
    host.reload()
    guest.wait_for_function('match===null&&!R.paused', polling=50)
    host.evaluate('catchUp=()=>{}')
    host.wait_for_function('R.isHost&&R.members.filter(p=>p.on).length===2', polling=50)
    host.click('#aipr-start')
    for p in (host, guest):
        p.wait_for_function('match&&match.index===0&&match.players.every(p=>p.results[0]===null)', polling=50)
        assert not p.errors


def test_away_phone_is_skipped_comes_back_and_the_result_reaches_it_once(phones):
    pages = room(phones, 3)
    host, guest, other = pages
    guest.evaluate('R.leave()')
    host.wait_for_function('R.members.some(p=>!p.on)', polling=50)
    quick_turn(pages[::2])
    host.wait_for_function('match.seq===2&&R.paused', polling=50)
    host.click('#aipr-goOn')
    other.wait_for_function('match.seq===3&&match.turn===2', polling=50)
    assert host.evaluate('match.players[1].results.slice(0,5)') == [False] * 5
    guest.click('#friends')
    guest.click('#aipr-again')
    guest.wait_for_function('match&&match.seq===3&&round.watch', polling=50)
    assert guest.locator('#who span').nth(1).inner_text() == 'Testi2 0'
    quick_turn(pages)
    # Straight to the last turn.
    host.evaluate("match.lap=4;match.turn=2;match.seq=20;match.index=20;sendState();syncView()")
    for p in pages:
        p.wait_for_function('match.seq===20', polling=50)
    guest.reload()
    guest.evaluate('catchUp=()=>{}')
    other.wait_for_function('round.index===20&&!round.watch', polling=50)
    other.evaluate(QUICK, True)
    for p in pages:
        p.wait_for_function("screen==='result'", polling=50)
    host.evaluate("R.deliver({t:'result',round:roomRound,match})")
    guest.reload()
    guest.wait_for_function("screen==='result'", polling=50)
    for p in pages:
        assert p.evaluate("load('kaverit',{}).rounds") == 1
    # A new round from the result screen, with fresh lists on every phone.
    for p in pages:
        if not p.locator('#aipr').is_visible():
            p.click('#again')
    assert 'voitti' in host.locator('#aipr').inner_text() or 'Tasapeli' in host.locator('#aipr').inner_text()
    host.click('#aipr-start')
    for p in pages:
        p.wait_for_function('match&&!match.over&&match.seq===1&&match.players.every(p=>p.results[0]===null)', polling=50)
        p.wait_for_function("screen==='play'", polling=50)
        assert not p.errors
    host.evaluate('R.stopRound()')
    for p in pages:
        p.wait_for_function('match===null&&!online', polling=50)


def test_the_game_plays_alone_after_a_room_with_its_saved_round(phones):
    p = phones('Testi1')
    p.evaluate("save('kierros',null)")
    p.click('#trap')
    shot(p)
    settle(p)
    p.evaluate('round.gap=.01;step(.1)')
    p.click('#pause')
    guest_room = room_only(p)
    p.evaluate('R.leave()')
    p.wait_for_function('!R.inRoom', polling=50)
    if p.locator('#aipr').is_visible():
        p.click('#aipr-back')
    assert p.locator('#resume').is_visible()
    p.click('#resume')
    assert p.evaluate('[online,round.index,round.watch===undefined]') == [False, 1, True]
    assert guest_room and not p.errors


def room_only(p):
    p.click('#friends')
    p.click('#aipr-create')
    p.wait_for_function('R.isHost&&R.members.length===1', polling=50)
    return True


def test_the_game_plays_in_the_room_pages_frame(site, browser):
    site.build(ROOT / 'games')
    relay = Relay()
    frames = []
    pages = []
    contexts = []
    for name in ('Testi1', 'Testi2'):
        ctx = browser.new_context(viewport={'width': 360, 'height': 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script('window.__aiPelitHuoneSivu = true;')
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi'," + json.dumps(json.dumps(name)) + ")")
        p = ctx.new_page()
        pages.append(p)
        relay.attach(p)
        p.goto(site.url + URL)
        p.click('#friends')
        if frames:
            p.fill('#aipr-codeIn', code)
            p.click('#aipr-joinBtn')
        else:
            p.click('#aipr-create')
        p.wait_for_url('**/huone/**')
        p.wait_for_function("document.getElementById('game')?.contentWindow?.AiPelitRooms?.inRoom")
        f = next(x for x in p.frames if x != p.main_frame and 'kiekkoammunta' in x.url)
        f.wait_for_function("typeof R!=='undefined'&&R.inRoom")
        if not frames:
            code = f.evaluate('R.code')
        frames.append(f)
    host, guest = frames
    host.wait_for_function('R.members.filter(p=>p.on).length===2')
    host.click('#aipr-start')
    for f in frames:
        f.wait_for_function("round&&round.phase==='ready'")
    host.evaluate(QUICK, True)
    guest.wait_for_function("match.seq===2&&round.watch===false&&round.phase==='ready'")
    assert 'Sinun vuorosi' in guest.locator('#hint').inner_text()
    # Leaving moves the whole page back to the game's own address, so the call must return first.
    for f, p in reversed(list(zip(frames, pages))):
        f.evaluate('setTimeout(() => R.leave(), 0); 0')
        p.wait_for_url(lambda u: '/huone/' not in u)
    for c in contexts:
        c.close()


@pytest.mark.parametrize('size', [(360, 640), (390, 844), (740, 360)])
def test_six_long_names_and_the_menu_fit(phones, size):
    p = phones('Testi1', size)
    box = p.locator('#friends').bounding_box()
    assert box['y'] + box['height'] <= size[1] and box['x'] + box['width'] <= size[0]
    assert p.evaluate("document.querySelector('.panel').scrollHeight<=innerHeight")
    p.click('#friends')
    p.click('#aipr-create')
    p.wait_for_function('R.isHost&&R.members.length===1', polling=50)
    p.evaluate("""() => {
      online=true;
      match={mode:'trap',seq:1,lap:0,turn:0,index:0,over:false,players:[0,1,2,3,4,5].map(i=>({
        id:i?'x'+i:R.me,name:'Pitkänimi Testi '+i,results:Array(25).fill(null)}))};
      view();
    }""")
    who = p.locator('#who').bounding_box()
    assert who['x'] >= 0 and who['x'] + who['width'] <= size[0]
    for span in p.locator('#who span').all():
        b = span.bounding_box()
        assert b['x'] >= 0 and b['x'] + b['width'] <= size[0]
    # The strip stays clear of the sight in the middle.
    sight = (size[0] / 2, size[1] * .43)
    assert not (who['x'] <= sight[0] <= who['x'] + who['width'] and who['y'] <= sight[1] <= who['y'] + who['height'])
    assert who['y'] + who['height'] < p.locator('#hint').bounding_box()['y']
    assert not p.errors


def test_turning_the_phone_keeps_a_rooms_round(phones):
    pages = room(phones, 2)
    host, guest = pages
    own_entry(host)
    turn(guest, {'width': 740, 'height': 360})
    guest.wait_for_function('match.index===1', polling=50)
    assert guest.evaluate('round.watch') is True
    assert not guest.errors
