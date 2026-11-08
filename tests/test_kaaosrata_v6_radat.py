"""The four obstacle courses: timing, old records, complete races and room handoff (#454)."""
import json

import pytest

from conftest import ROOT, ROOMS_IN_GAME
from test_rooms_lib import Relay

URL = 'games/kaaosrata/v6/'
COURSES = ['main', 'hihna', 'laatat', 'finaali']


def open_game(site, context):
    site.build(ROOT / 'games')
    page = context.new_page()
    page.errors = []
    page.on('pageerror', lambda error: page.errors.append(str(error)))
    page.goto(site.url + URL)
    return page


@pytest.mark.parametrize('size', [(360, 640), (360, 740), (740, 360)])
def test_every_course_fits_and_rotation_keeps_the_round(site, browser, size):
    ctx = browser.new_context(viewport={'width': size[0], 'height': size[1]}, has_touch=True)
    try:
        ctx.add_init_script("Element.prototype.requestFullscreen = undefined")
        page = open_game(site, ctx)
        for course in COURSES:
            page.evaluate('(id) => {useCourse(id);showMenu();}', course)
            assert page.locator('#course-name').inner_text()
            for selector in ['#course-picker', '#go', '#multi', '#stats', '.help']:
                box = page.locator(selector).bounding_box()
                assert box['x'] >= 0 and box['y'] >= 0, (selector, box)
                assert box['x'] + box['width'] <= size[0] + 1, (selector, box)
                assert box['y'] + box['height'] <= size[1] + 1, (selector, box)
            page.click('#go')
            assert page.evaluate('race.phase') == 'cd'
            page.evaluate("race.phase='run';race.clock=10;me.y=2;window.roundBefore= race;draw()")
            page.set_viewport_size({'width': size[1], 'height': size[0]})
            assert page.evaluate("race === window.roundBefore && race.clock >= 10 && course.id === " + json.dumps(course))
            page.set_viewport_size({'width': size[0], 'height': size[1]})
            page.evaluate('race=null;me=null;showMenu()')
        assert page.errors == []
    finally:
        ctx.close()


def test_belts_carry_a_runner_and_tiles_warn_then_drop_them(site, context):
    page = open_game(site, context)
    result = page.evaluate('''() => {
      useCourse('hihna');soloRace();race.phase='run';
      const b=BELTS[0];Object.assign(me,{x:0,y:b.y0+2});
      const velocity=groundAt(me.x,me.y,0);const y=me.y;move(me,0.05,0);
      const carried=me.y-y;
      useCourse('laatat'); const tile=TILES[0],px=tile.x0+1,py=tile.y0+1;
      const on=groundAt(px,py,-tile.ph+0.1);
      const warning=tileOn(tile,-tile.ph+tile.on-0.3);
      const off=groundAt(px,py,-tile.ph+tile.on+0.1);
      Object.assign(me,{x:px,y:py,z:0,vx:0,vy:0,off:0});
      for(let i=0;i<8;i++)move(me,1/60,tile.on+0.2);
      return {velocity,carried,on,warning,off,fall:me.fall};
    }''')
    assert result['velocity'] == {'vx': 0, 'vy': -2}
    assert result['carried'] == pytest.approx(-0.1)
    assert result['on'] is not None and result['warning'] is True
    assert result['off'] is None and result['fall'] > 0
    assert page.errors == []


def test_best_computer_finishes_each_course_in_ten_seeded_races(site, context):
    page = open_game(site, context)
    results = page.evaluate('''() => {
      const final=RADAT.find(c=>c.id==='finaali');
      if (!final.mov || ['stones','sweepers','pushers','bumpers','discs','belts','tiles','hammers'].some(k=>!final[k].length)) throw Error('The final must include every obstacle type');
      const all=[];
      for(const course of RADAT) {
        useCourse(course.id);const times=[];
        for(let seed=1;seed<=10;seed++) {
          let rng=seed;const real=Math.random;
          Math.random=()=>((rng=Math.imul(rng,1664525)+1013904223>>>0)/4294967296);
          try {
            const r=runner('bot','Bot','#fff','cpu',true,1);
            newRace('solo','',[r]);race.phase='run';me=null;
            for(let i=0;i<course.limit*60 && r.fin===null;i++) {
              race.clock=(i+1)/60;think(r,1/60,race.clock);move(r,1/60,race.clock);
            }
            times.push(r.fin);
          } finally {Math.random=real;}
        }
        all.push({id:course.id,limit:course.limit,times});
      }
      race=null;return all;
    }''')
    for result in results:
        assert sum(t is not None and 0 < t < result['limit'] for t in result['times']) >= 9, result
    assert page.errors == []


def test_chooser_records_and_score_lists_survive_reload(site, context):
    page = open_game(site, context)
    page.evaluate('''() => {
      save('ennatys',61.2);save('ennatys:hihna',72.3);save('ennatys:laatat',83.4);save('ennatys:finaali',94.5);
      save('taso',3);save('kisat',12);save('voitot',4);
    }''')
    page.reload()
    for i, name in enumerate(['Puomipuisto', 'Hihnatehdas', 'Laattalaakso', 'Kaaosfinaali']):
        assert page.locator('#course-name').inner_text() == name
        assert ['61,20', '72,30', '83,40', '94,50'][i] in page.locator('#stats').inner_text()
        assert 'Taso 3' in page.locator('#foe').inner_text()
        page.click('#course-next')
        page.reload()
    assert page.evaluate("load('ennatys')") == 61.2
    # Complete a new course and ensure it saves and queues only that course's record.
    page.click('#course-next')
    page.click('#go')
    page.evaluate("race.phase='run';race.clock=40;Object.assign(me,{x:0,y:FIN-0.02,vy:5,cp:CPS.length-2});input.y=1;tick(0.03);finish(standings());")
    assert page.evaluate("load('ennatys:hihna')") < 41
    assert page.evaluate("load('ennatys')") == 61.2
    queued = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))")
    assert any(q['game'] == 'kaaosrata' and q['board'] == 'hihna' for q in queued.values()), queued
    assert page.errors == []


def test_three_phones_follow_host_course_reload_and_next_round(site, browser):
    site.build(ROOT / 'games')
    relay = Relay()
    contexts = []
    def phone(name):
        ctx = browser.new_context(viewport={'width': 360, 'height': 740}, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(ROOMS_IN_GAME)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page(); page.errors = []
        page.on('pageerror', lambda error: page.errors.append(str(error)))
        relay.attach(page); page.goto(site.url + URL)
        return page
    try:
        host = phone('Testi A');host.click('#multi');host.click('#aipr-create')
        host.wait_for_function('R.isHost && R.members.length===1')
        code = host.evaluate('R.code')
        guests = [phone('Testi B'), phone('Testi C')]
        for page in guests:
            page.click('#multi');page.fill('#aipr-codeIn',code);page.click('#aipr-joinBtn')
            page.wait_for_function('R.inRoom && R.members.length>1')
            assert not page.locator('#room-course').is_visible()
        host.wait_for_function('R.members.length===3')
        host.locator('#room-course button').last.click()  # Hihnatehdas
        host.locator('#room-course button').last.click()  # Laattalaakso
        host.click('#aipr-start')
        for page in [host,*guests]:
            page.wait_for_function("race && race.phase==='run' && course.id==='laatat'")
        guests[0].reload()
        guests[0].wait_for_function("race && race.phase==='run' && course.id==='laatat' && race.clock>2")
        host.evaluate('R.stopRound()')
        for page in [host,*guests]:
            page.wait_for_function('race===null')
        host.locator('#room-course button').last.click()  # Kaaosfinaali
        host.click('#aipr-start')
        for page in [host,*guests]:
            page.wait_for_function("race && race.phase==='run' && course.id==='finaali'")
            assert page.errors == []
        # Finish through the actual guest -> host -> delivered results path.
        for i, page in enumerate([host, *guests]):
            page.evaluate('(time)=>{me.fin=time;me.best=FIN;me.y=FIN;guestTick(1)}', 40+i)
        host.wait_for_function('race.runners.filter(r=>!r.bot).every(r=>r.fin!==null)')
        # Lose one phone's end packet before it can acknowledge it.
        missed_id = guests[0].evaluate('R.me')
        relay_message = relay.message
        def lose_end(room, sender, text):
            message = json.loads(text)
            if message.get('t') == 'end' and message.get('to') == missed_id:
                return
            relay_message(room, sender, text)
        relay.message = lose_end
        host.evaluate('race.clock=50;hostTick(0.1)')
        for page in [host, guests[1]]:
            page.wait_for_function("race && race.phase==='done'")
            assert page.evaluate("load('ennatys:finaali')") is not None
            assert page.evaluate("load('ennatys',null)") is None
            assert page.evaluate("Object.values(JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))).some(q=>q.board==='finaali')")
        # No snapshot is sent by a host already showing results: the end must identify its course.
        count = guests[0].evaluate("load('kisat',0)")
        relay.message = relay_message
        guests[0].reload()
        guests[0].wait_for_function("race && race.phase==='done' && course.id==='finaali'")
        assert guests[0].evaluate("load('kisat')") == count + 1
        assert guests[0].evaluate("load('ennatys:finaali')") == 41
        assert guests[0].evaluate("load('ennatys',null)") is None
        for page in [host,*guests]: assert page.errors == []
    finally:
        for ctx in contexts: ctx.close()
