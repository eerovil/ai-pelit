"""Raketti: manual controls, real orbit dynamics, contact docking and resumable flight."""
import shutil

import pytest

from conftest import ROOT, turn

URL = 'games/raketti/v1/'


def open_game(site, context):
    shutil.copytree(ROOT / 'games/raketti', site.games / 'raketti')
    site.build()
    page = context.new_page()
    page.errors = []
    page.on('pageerror', lambda error: page.errors.append(str(error)))
    page.goto(site.url + URL)
    page.wait_for_function("typeof ship !== 'undefined' && !!document.getElementById('launch')")
    return page


def start(page, button='launch'):
    page.locator('#' + button).click()
    page.evaluate('cancelAnimationFrame(frameId); frameId=0; lastFrame=0')


# A test pilot only: sends the same pointer/range events as the player's controls.
# There is no pilot/controller in the shipped game. Substeps use the real game physics.
PILOT = r"""() => {
 window.controlState = {};
 window.control = (key, value) => {
   window.controlState ||= {};
   if (controlState[key] === value) return;
   const id = {turn:11,forward:12,side:13}[key];
   if (controlState[key]) document.querySelector(`[data-hold="${key}:${controlState[key]}"]`)
     .dispatchEvent(new PointerEvent('pointerup',{pointerId:id,bubbles:true}));
   if (value) document.querySelector(`[data-hold="${key}:${value}"]`)
     .dispatchEvent(new PointerEvent('pointerdown',{pointerId:id,bubbles:true}));
   controlState[key]=value;
 };
 window.power = value => {
   const slider=document.getElementById('throttle'); slider.value=value*100;
   slider.dispatchEvent(new Event('input',{bubbles:true}));
 };
 window.flyDock = () => {
   for(let t=0; t<650 && ship.phase==='flight'; t+=.1) {
     const d=approach(), desired=clamp(-d.along*.03,0,.15);
     const desiredSpin=STATION_N+clamp(wrap(d.p.angle-ship.angle)*.3,-.005,.005);
     control('turn',ship.omega<desiredSpin-.00015?1:ship.omega>desiredSpin+.00015?-1:0);
     control('forward',-d.closing<desired-.004?1:-d.closing>desired+.004?-1:0);
     const radial=-d.cross*.03-d.lateral*.5;
     control('side',radial>.003?-1:radial<-.003?1:0);
     step(.1);
   }
   updateUi(); if(ship.phase!=='flight') showResult();
   return {phase:ship.phase,reason:ship.reason,t:ship.t,rcs:ship.rcs};
 };
}"""


ASCENT = r"""() => {
      let staged=false;
      for(let t=0;t<800 && ship.phase==='flight';t+=.1) {
        const o=orbit(),rad=Math.atan2(ship.x,ship.y),h=o.altitude;
        const pitch=h<2000?0:h<10000?(h-2000)/8000*20:
          h<40000?20+(h-10000)/30000*20:h<100000?40+(h-40000)/60000*25:
          h<200000?65+(h-100000)/100000*15:87;
        let target=rad+pitch*Math.PI/180;
        if(ship.stage===0 && ship.fuel[0]<1) {
          document.getElementById('stage').click(); power(1); staged=true;
        }
        if(o.apo>400000) power(0);
        if(o.toApo<45 && h>200000 && o.peri<390000) {
          power(.6); target=Math.atan2(ship.vx,ship.vy);
        }
        const desired=clamp(wrap(target-ship.angle)*.4,-.015,.015),rate=ship.omega-o.vt/o.r;
        control('turn',rate<desired-.0003?1:rate>desired+.0003?-1:0);
        step(.1); updateUi();
      }
      power(0);control('turn',0);saveFlight();
      return {staged,phase:ship.phase,orbited:ship.orbited,peri:orbit().peri,
        apo:orbit().apo,t:ship.t,fuel:ship.fuel[1],record:achieved.orbit};
    }"""


def test_manual_launch_can_reach_a_stable_orbit(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(PILOT)
    result = page.evaluate(ASCENT)
    assert result['staged'] and result['phase'] == 'flight', result
    assert result['orbited'] and result['record'], result
    assert result['peri'] > 150000 and 300000 < result['apo'] < 600000, result
    assert 700 < result['t'] < 801 and result['fuel'] > 5000
    assert page.errors == []


def test_docking_practice_can_be_completed_twice_with_controls(site, context):
    page = open_game(site, context)
    for _ in range(2):
        start(page, 'practice-dock' if _ == 0 else 'retry')
        page.evaluate(PILOT)
        result = page.evaluate('flyDock()')
        assert result['phase'] == 'docked', result
        assert result['rcs'] > 0 and 100 < result['t'] < 650
        assert page.locator('#result-title').inner_text() == 'Tervetuloa asemalle.'
        assert page.evaluate('achieved.dock') is False  # Practice is not a mission achievement.
    assert page.errors == []


@pytest.mark.parametrize('start_delay', [0, .02])
def test_free_orbit_conserves_energy_and_period(site, context, start_delay):
    page = open_game(site, context)
    start(page, 'practice-orbit')
    # A rendered frame may have advanced the orbit before the test cancels RAF.
    page.evaluate('delay => step(delay)', start_delay)
    result = page.evaluate("""() => {
      const initial=orbit(),x0=ship.x,y0=ship.y;
      const energy0=(ship.vx**2+ship.vy**2)/2-MU/initial.r;
      const period=TAU*Math.sqrt(initial.r**3/MU);
      held.turn=held.forward=held.side=0;
      step(period);
      const o=orbit(),energy=(ship.vx**2+ship.vy**2)/2-MU/o.r;
      return {drift:Math.abs(o.r-initial.r),position:Math.hypot(ship.x-x0,ship.y-y0),
        energy:Math.abs((energy-energy0)/energy0),phase:ship.phase};
    }""")
    assert result['phase'] == 'flight'
    assert result['drift'] < 5 and result['position'] < 20, result
    assert result['energy'] < 1e-6
    assert page.errors == []


def test_raising_orbit_requires_velocity_not_just_height(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      ship=freshFlight('orbit'); ship.vx=0; ship.omega=0;ship.orbited=false;
      paused=false;step(1);
      return {orbited:ship.orbited,peri:orbit().peri,alt:orbit().altitude};
    }""")
    assert result['alt'] > 200000 and result['peri'] < 0 and not result['orbited']
    assert page.errors == []


def test_prograde_burn_raises_opposite_apsis_and_uses_mass(site, context):
    page = open_game(site, context)
    start(page, 'practice-orbit')
    result = page.evaluate("""() => {
      const before=orbit(),m=mass(),fuel=ship.fuel[1];ship.throttle=.2;step(3);
      return {before:before.apo,after:orbit().apo,massUsed:m-mass(),fuelUsed:fuel-ship.fuel[1]};
    }""")
    assert result['after'] > result['before'] + 10000
    assert result['massUsed'] == pytest.approx(result['fuelUsed'], abs=1e-6)
    assert result['fuelUsed'] == pytest.approx(1900000 * .2 / (450 * 9.80665) * 3, rel=1e-6)
    assert page.errors == []


@pytest.mark.parametrize('bad', ['speed', 'angle', 'spin'])
def test_unsafe_contact_is_not_docking(site, context, bad):
    page = open_game(site, context)
    result = page.evaluate("""bad => {
      ship=freshFlight('dock');paused=false;
      const p=station();ship.x=p.px-8-0.5;
      ship.vx=p.pvx;ship.vy=p.pvy+8*STATION_N;
      if(bad==='speed')ship.vx+=2;
      if(bad==='angle') {ship.angle+=.3;ship.x=p.px-Math.sin(ship.angle)*8-.5;ship.y=p.py-Math.cos(ship.angle)*8;}
      if(bad==='spin')ship.omega+=.08;
      step(.02);return {phase:ship.phase,reason:ship.reason};
    }""", bad)
    assert result['phase'] == 'crashed', result
    assert 'Törmäys' in result['reason']
    assert page.errors == []


def test_rcs_translation_and_rotation_keep_momentum_after_release(site, context):
    page = open_game(site, context)
    start(page, 'practice-dock')
    page.evaluate(PILOT)
    result = page.evaluate("""() => {
      const f=ship.rcs;control('forward',1);control('turn',1);step(.2);
      control('forward',0);control('turn',0);const w=ship.omega;step(2);
      return {omega:ship.omega,w,used:f-ship.rcs,held:{...held},phase:ship.phase};
    }""")
    assert result['used'] > 0 and result['w'] > .0012
    assert result['omega'] == pytest.approx(result['w'], abs=1e-10)
    assert result['held'] == {'turn': 0, 'forward': 0, 'side': 0}
    assert page.errors == []


def test_pointer_cancel_and_pause_release_all_thrusters(site, context):
    page = open_game(site, context)
    start(page, 'practice-dock')
    page.locator('[data-hold="turn:1"]').dispatch_event('pointerdown', {'pointerId': 22})
    assert page.evaluate('held.turn') == 1
    page.locator('[data-hold="turn:1"]').dispatch_event('pointercancel', {'pointerId': 22})
    assert page.evaluate('held.turn') == 0
    page.locator('[data-hold="forward:1"]').dispatch_event('pointerdown', {'pointerId': 23})
    page.locator('#pause').click()
    assert page.evaluate('paused && held.forward===0 && pointers.size===0')
    assert page.locator('#pause-panel').is_visible()
    assert page.errors == []


def test_save_reload_and_rotation_preserve_flight(site, context):
    page = open_game(site, context)
    start(page, 'practice-orbit')
    page.evaluate('step(12);saveFlight()')
    saved = page.evaluate('JSON.parse(localStorage.getItem(SAVE_KEY))')
    turn(page, {'width': 740, 'height': 360})
    assert page.evaluate('ship.t') == pytest.approx(saved['t'])
    page.reload()
    assert page.locator('#resume').is_visible()
    page.locator('#resume').click()
    assert page.locator('#pause-panel').is_visible()
    actual = page.evaluate('({...ship})')
    for key in ('x', 'y', 'vx', 'vy', 'angle', 'omega', 'fuel', 'rcs', 't', 'throttle'):
        assert actual[key] == saved[key]
    assert page.evaluate('paused') is True
    page.locator('#continue').click()
    assert page.locator('#overlay').is_hidden()
    assert page.errors == []


@pytest.mark.parametrize('mutation', [
    {'x': None}, {'fuel': [-1, 100]}, {'stage': 7}, {'rcs': -1},
    {'phase': 'flight', 't': -10}, {'omega': 1000}, {'throttle': 2}, {'practice': 'false'},
])
def test_corrupt_save_is_not_resumed(site, context, mutation):
    page = open_game(site, context)
    page.evaluate("""m => {const s={...freshFlight('orbit'),...m};localStorage.setItem(SAVE_KEY,JSON.stringify(s));}""", mutation)
    page.reload()
    assert page.locator('#resume').is_hidden()
    assert page.locator('#launch').is_visible()
    assert page.errors == []


def test_no_fuel_means_no_free_thrust_and_staging_is_manual(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      ship=freshFlight('orbit');paused=false;ship.fuel[1]=0;ship.rcs=0;ship.throttle=1;
      held.forward=1;held.turn=1;const w=ship.omega;step(1);
      return {stage:ship.stage,throttle:ship.throttle,omega:ship.omega,w,mass:mass(),fuel:ship.fuel[1]};
    }""")
    assert result['stage'] == 1 and result['fuel'] == 0 and result['throttle'] == 0
    assert result['mass'] == 29000 and result['omega'] == result['w']
    assert page.errors == []


def test_warp_restrictions_and_near_station_cancellation(site, context):
    page = open_game(site, context)
    start(page, 'practice-orbit')
    assert page.evaluate('canWarp()')
    page.locator('#warp').click()
    assert page.evaluate('warp') == 10
    page.locator('[data-hold="forward:1"]').dispatch_event('pointerdown', {'pointerId': 21})
    assert page.evaluate('warp===1 && !canWarp()')
    page.locator('[data-hold="forward:1"]').dispatch_event('pointerup', {'pointerId': 21})
    assert page.evaluate('canWarp()')
    result = page.evaluate("""() => {
      ship=freshFlight('dock');warp=100;step(.1);return {warp,can:canWarp()};
    }""")
    assert result == {'warp': 1, 'can': False}
    assert page.errors == []


@pytest.mark.parametrize('width,height', [(360, 640), (360, 740), (390, 844), (740, 360)])
def test_phone_screens_help_and_controls_fit(site, browser, width, height):
    context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=True, has_touch=True)
    page = open_game(site, context)
    for selector in ('#menu', '#launch', '#practice-dock'):
        box = page.locator(selector).bounding_box()
        assert box and box['y'] >= 0 and box['y'] + box['height'] <= height, (selector, box)
    page.locator('#menu-help').tap()
    for i in range(6):
        box = page.locator('#help-panel').bounding_box()
        assert box and box['y'] >= 0 and box['y'] + box['height'] <= height, (i, box)
        assert page.locator('#help-close').is_visible()
        if i < 5:
            page.locator('#help-next').tap()
    page.locator('#help-close').tap()
    start(page, 'practice-dock')
    for selector in ('#controls', '#guidance', '#telemetry', '#scene', '#pause'):
        box = page.locator(selector).bounding_box()
        assert box and box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= width + 1 and box['y'] + box['height'] <= height + 1, (selector, box)
    assert page.evaluate('document.documentElement.scrollHeight<=innerHeight')
    assert page.errors == []
    context.close()


def test_offline_play_and_storage_denial(site, context):
    page = open_game(site, context)
    page.evaluate("() => {Storage.prototype.setItem=function(){throw new Error('denied')}}")
    context.set_offline(True)
    start(page, 'practice-dock')
    page.evaluate(PILOT)
    result = page.evaluate('flyDock()')
    assert result['phase'] == 'docked'
    assert page.errors == []


def test_existing_flight_requires_confirmation_before_replacing(site, context):
    page = open_game(site, context)
    start(page, 'practice-orbit')
    page.locator('#pause').click()
    page.locator('#to-menu').click()
    page.locator('#launch').click()
    assert page.locator('#replace-panel').is_visible()
    page.locator('#replace-no').click()
    assert page.evaluate('loadFlight().practice')
    page.locator('#launch').click()
    page.locator('#replace-yes').click()
    assert page.evaluate('!ship.practice && ship.stage===0')
    assert page.errors == []


def test_warp_cancellation_does_not_consume_rest_of_accelerated_frame(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      ship=freshFlight('dock');paused=false;const p=station();
      ship.x=p.px-6000;ship.vx=p.pvx+1000;warp=100;
      advanceFlight(.2);return {t:ship.t,warp,phase:ship.phase,range:approach().range};
    }""")
    assert result['warp'] == 1 and result['t'] < 2, result
    assert result['range'] > 4000 and result['phase'] == 'flight'
    assert page.errors == []


@pytest.mark.parametrize('scenario', ['fast-port', 'tail-hull'])
def test_swept_contact_and_entire_vehicle_collide(site, context, scenario):
    page = open_game(site, context)
    result = page.evaluate("""scenario => {
      ship=freshFlight('dock');paused=false;const p=station();
      if(scenario==='fast-port') {ship.x=p.px-8-6;ship.vx=p.pvx+500;}
      else {ship.x=p.x;ship.y=p.y+17;ship.angle=0;ship.vx=p.vx;ship.vy=p.vy;}
      step(.02);return {phase:ship.phase,reason:ship.reason};
    }""", scenario)
    assert result['phase'] == 'crashed', result
    assert 'Törmäys' in result['reason']
    assert page.errors == []


# Test-only controls for rendezvous and docking; no state placement or teleporting.
MISSION = r"""() => {
 let phase='coast',arrival=ship.t+orbit().toApo,log=[];
 for(let t=0;t<7500 && ship.phase==='flight';t+=.05) {
  const p=station(),d=approach();
  let ax=0,ay=0;
  if(phase==='coast' && ship.t>arrival-300)phase='terminal';
  if(phase==='terminal') {
   const tx=p.px-1500*p.tx,ty=p.py-1500*p.ty,dx=tx-ship.x,dy=ty-ship.y,r=Math.hypot(ship.x,ship.y);
   const tvx=p.pvx+1500*STATION_N*p.rx,tvy=p.pvy+1500*STATION_N*p.ry;
   const tau=clamp(Math.sqrt(Math.hypot(dx,dy)/.1),12,70);
   ax=dx/(tau*tau)+2*(tvx-ship.vx)/tau-MU*tx/Math.hypot(tx,ty)**3+MU*ship.x/r**3;
   ay=dy/(tau*tau)+2*(tvy-ship.vy)/tau-MU*ty/Math.hypot(tx,ty)**3+MU*ship.y/r**3;
   if(d.along < -800 && Math.abs(d.cross)<1000 && d.speed<3){phase='dock';power(0);}
  }
  if(phase==='terminal') {
   const a=Math.hypot(ax,ay),err=wrap(Math.atan2(ax,ay)-ship.angle),des=clamp(err*.15,-.03,.03);
   control('turn',ship.omega<des-.0005?1:ship.omega>des+.0005?-1:0);
   control('forward',0);control('side',0);
   power(Math.abs(err)<.035?clamp(a*mass()/1900000,0,.2):0);
  }else if(phase==='coast'){
   power(0);control('turn',ship.omega>.002?-1:ship.omega<-.002?1:0);control('forward',0);control('side',0);
  }else if(phase==='dock'){
   const tx=p.px-8.6*p.tx,ty=p.py-8.6*p.ty,dx=tx-ship.x,dy=ty-ship.y;
   const r=Math.hypot(ship.x,ship.y),tr=Math.hypot(tx,ty),dist=Math.hypot(dx,dy);
   const tvx=p.pvx+8.6*STATION_N*p.rx,tvy=p.pvy+8.6*STATION_N*p.ry;
   const speed=Math.min(dist*.03,dist<20?.15:.5),vrx=dist?dx/dist*speed:0,vry=dist?dy/dist*speed:0;
   const ax=.2*(tvx-STATION_N*dy+vrx-ship.vx)-MU*tx/tr**3+MU*ship.x/r**3;
   const ay=.2*(tvy+STATION_N*dx+vry-ship.vy)-MU*ty/tr**3+MU*ship.y/r**3;
   const f=ax*Math.sin(ship.angle)+ay*Math.cos(ship.angle),side=ax*Math.cos(ship.angle)-ay*Math.sin(ship.angle);
   const desiredSpin=STATION_N+clamp(wrap(p.angle-ship.angle)*.15,-.025,.025);
   control('turn',ship.omega<desiredSpin-.0005?1:ship.omega>desiredSpin+.0005?-1:0);
   control('forward',f>.002?1:f<-.002?-1:0);control('side',side>.002?1:side<-.002?-1:0);

  }
  step(.05);updateUi();
  if(Math.round(t*20)%10000===0)log.push({t:ship.t,range:d.range,speed:d.speed,fuel:ship.fuel[1],rcs:ship.rcs,phase,alt:orbit().altitude});
 }
 return {log,phase,ship,d:approach()};
}
"""


@pytest.mark.parametrize('size', [(360, 740), (740, 360)])
def test_entire_manual_mission_from_launch_to_docking(site, browser, size):
    context = browser.new_context(viewport={'width': size[0], 'height': size[1]}, is_mobile=True, has_touch=True)
    page = open_game(site, context)
    start(page)
    page.evaluate(PILOT)
    ascent = page.evaluate(ASCENT)
    assert ascent['phase'] == 'flight' and ascent['orbited'], ascent
    page.evaluate(PILOT)
    result = page.evaluate(MISSION)
    assert result['ship']['phase'] == 'docked', result
    assert result['ship']['practice'] is False
    assert result['ship']['fuel'][1] > 0 and result['ship']['rcs'] > 0
    assert page.evaluate('achieved.orbit && achieved.dock')
    assert result['d']['speed'] <= .25
    page.evaluate('showResult()')
    assert page.locator('#result-title').inner_text() == 'Tervetuloa asemalle.'
    page.reload()
    assert page.locator('#achievements').inner_text() == 'SAAVUTETTU · Kiertorata ja telakointi'
    assert page.errors == []
    context.close()


def test_handbook_transfer_phase_and_burn_reach_station_orbit(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      ship=freshFlight('orbit');paused=false;
      const r1=EARTH+250000,r2=EARTH+400000,a=(r1+r2)/2;
      const transferTime=Math.PI*Math.sqrt(a**3/MU);
      const lead=Math.PI-STATION_N*transferTime;
      const dv=Math.sqrt(MU/r1)*(Math.sqrt(2*r2/(r1+r2))-1);
      // Keep the physical station clear of the deliberately unbraked reference intercept.
      ship.stationPhase=lead+.01;ship.vx+=dv;
      step(transferTime);const p=station({...ship,stationPhase:lead});
      return {lead:lead*180/Math.PI,dv,t:transferTime,alt:orbit().altitude,
        range:Math.hypot(ship.x-p.x,ship.y-p.y),phase:ship.phase};
    }""")
    assert result['lead'] == pytest.approx(2.98, abs=.01)
    assert result['dv'] == pytest.approx(43.33, abs=.01)
    assert result['t'] == pytest.approx(2726.49, abs=.1)
    assert result['alt'] == pytest.approx(400000, abs=5)
    assert result['range'] < 10
    assert page.errors == []
