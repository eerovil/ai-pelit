"""The friends watching stand still and only slide with the background (#395, yleisurheilu-9),
and climb onto each other (#373), played in Pituushyppy's newest version with the real room helpers.
"""
import json

import pytest

from test_yleisurheilu_vuorot import newest, on_turn, play, room


def watching(site, browser, names=("Eero", "Aino", "Ville")):
    path = newest("pituushyppy")
    relay, pages, code = room(site, browser, path, list(names))
    host = pages[0]
    turn = on_turn(host)
    for p in pages:
        p.wait_for_function(f"K.current() && K.current().p === {json.dumps(turn)}")
        p.wait_for_function(f"K.fanSpots.length === {len(names) - 1}", timeout=8000)
    athletes = {p.evaluate("AiPelitRooms.me"): p for p in pages}
    athlete = athletes[turn]
    fans = [p for p in pages if p is not athlete]
    return relay, pages, athlete, fans


def install_fake_scroll(page):
    """Override only the row's scroll input; the real animation frame keeps drawing."""
    page.evaluate("""() => {
      window.__spectatorScroll = 0;
      const original = K.drawFans;
      K.drawFans = function (ctx, box) {
        window.__spectatorCtx = ctx;
        window.__spectatorBox = { ...box };
        return original(ctx, { ...box, scroll: window.__spectatorScroll });
      };
    }""")
    page.wait_for_function("window.__spectatorBox && K.fanSpots.length > 0")


def fan_x(page, id_):
    return page.evaluate("(id) => K.fanSpots.find(f => f.id === id)?.x", id_)


def close_pages(pages):
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_the_row_slides_a_little_slower_than_the_background_and_stops_with_it(site, browser):
    _, pages, _, fans = watching(site, browser)
    page = fans[0]
    install_fake_scroll(page)
    fid = page.evaluate("K.mine().id")
    start = fan_x(page, fid)
    page.evaluate("window.__spectatorScroll = 100")
    # The background has moved 100 px: the spectator is 80 px along at once, with no running.
    page.wait_for_function("""({ id, start }) => {
      const x = K.fanSpots.find(f => f.id === id)?.x;
      return x !== undefined && Math.abs(x - (start - 80)) < 0.5;
    }""", arg={"id": fid, "start": start}, timeout=2000)
    # The background stands still, and so do they: nobody moves by themselves.
    page.wait_for_timeout(1000)
    assert abs(fan_x(page, fid) - (start - 80)) < 0.5
    # They come back only with the background.
    page.evaluate("window.__spectatorScroll = 0")
    page.wait_for_function("""({ id, start }) => {
      const x = K.fanSpots.find(f => f.id === id)?.x;
      return x !== undefined && Math.abs(x - start) < 0.5;
    }""", arg={"id": fid, "start": start}, timeout=2000)
    close_pages(pages)


def test_legs_stay_still_as_the_row_slides_and_move_on_a_tapped_walk(site, browser):
    _, pages, _, fans = watching(site, browser)
    page = fans[0]
    install_fake_scroll(page)
    sliding = page.evaluate("""() => new Promise(done => {
      const t0 = performance.now(), steps = [], gaps = [];
      const look = () => {
        const t = (performance.now() - t0) / 1000;
        window.__spectatorScroll = t * 100;
        steps.push(...K.fanSpots.map(f => f.step));
        const xs = K.fanSpots.map(f => f.x).sort((a, b) => a - b);
        if (xs.length === 2) gaps.push(xs[1] - xs[0]);
        if (t < 1) requestAnimationFrame(look); else done({ steps, gaps });
      };
      look();
    })""")
    assert sliding["steps"] and all(s == 0 for s in sliding["steps"]), "legs moved with no walk"
    assert max(sliding["gaps"]) - min(sliding["gaps"]) < 0.5, "the row did not slide as one"
    # A tap clear of the others walks my own figure, and then the legs go.
    walked = page.evaluate("""() => new Promise(done => {
      window.__spectatorScroll = 0;
      requestAnimationFrame(() => requestAnimationFrame(() => {
        const me = K.mine().id, mine = K.fanSpots.find(f => f.id === me);
        const other = K.fanSpots.find(f => f.id !== me);
        const room = mine.x < other.x ? -1 : 1;
        K.tapFans(mine.x + room * 25);
        const t0 = performance.now(), steps = [];
        const look = () => {
          steps.push(K.fanSpots.find(f => f.id === me).step);
          if (performance.now() - t0 < 500) requestAnimationFrame(look); else done(steps);
        };
        look();
      }));
    })""")
    assert any(abs(s) > 0.05 for s in walked), "a tapped walk moved no legs"
    close_pages(pages)


def test_tap_accounts_for_my_own_lag_and_keeps_spot_normalized(site, browser):
    _, pages, _, fans = watching(site, browser)
    page = fans[0]
    install_fake_scroll(page)
    me = page.evaluate("K.mine().id")
    first = fan_x(page, me)
    page.evaluate("window.__spectatorScroll = 120")
    page.wait_for_function(
        "(a) => K.fanSpots.find(f => f.id === a.id)?.x < a.first - 4",
        arg={"id": me, "first": first}, timeout=5000,
    )
    # Infer the lag from the unchanged rest spot. The tap must add that lag back.
    report = page.evaluate("""() => {
      const me = K.mine().id, mine = K.fanSpots.find(f => f.id === me);
      const l = 12 + 40 * 0.4, r = SW - 12 - 40 * 0.4, w = r - l;
      const all = K.comp.throwers.filter(t => t.p !== null);
      const rest = l + (all.findIndex(f => f.id === me) + 0.5) / all.length * w;
      const lag = rest - mine.x;
      const x = 50;
      const expected = Math.max(0, Math.min(1, (x + lag - l) / w));
      K.tapFans(x);
      return { expected, actual: K.spot[me], lag };
    }""")
    assert abs(report["lag"] - 96) < 1  # 0.8 of the background's 120 px
    assert report["actual"] is not None
    assert abs(report["actual"] - report["expected"]) < 0.01
    close_pages(pages)


def test_offscreen_cheer_is_drawn_in_a_bubble_at_the_row_edge(site, browser):
    _, pages, _, fans = watching(site, browser)
    page = fans[0]
    install_fake_scroll(page)
    fid = page.evaluate("K.mine().id")
    report = page.evaluate("""id => {
      const box = __spectatorBox, ctx = __spectatorCtx;
      window.__spectatorScroll = 2000;
      const old = ctx.roundRect, bubbles = [];
      K.cheers[id] = { at: performance.now(), text: 'Hyvä!' };
      ctx.roundRect = function (x, y, w, h, rad) {
        if (h >= 20 && w >= 30 && y < box.bottom - box.h) bubbles.push({ x, y, w, h });
        return old.apply(this, arguments);
      };
      try { K.drawFans(ctx, { ...box, scroll: 2000 }); }
      finally { ctx.roundRect = old; }
      return { boxes: bubbles, left: box.left, right: box.right,
        visible: K.fanSpots.some(f => f.id === id) };
    }""", arg=fid)
    assert not report["visible"], "the spectator must be outside the screen"
    assert report["boxes"], "the cheer bubble must still be drawn"
    assert any(b["x"] >= report["left"] and b["x"] + b["w"] <= report["right"] + 1
               for b in report["boxes"])
    close_pages(pages)


def test_two_phones_see_a_column_and_dropping_its_base(site, browser):
    _, pages, athlete, fans = watching(site, browser, ("Eero", "Aino", "Ville"))
    top = next(p for p in fans if p is not pages[0])
    base = next(p for p in fans if p is not top)
    top_id = top.evaluate("K.mine().id")
    base_id = base.evaluate("K.mine().id")
    # A tap on another figure climbs onto that figure, through the host's go validation.
    top.evaluate("""id => {
      const p = K.fanSpots.find(f => f.id === id);
      K.tapFans(p.x, p.y - 20);
    }""", base_id)
    for p in pages:
        p.wait_for_function("([t, b]) => K.on[t] === b", arg=[top_id, base_id], timeout=5000)
        p.wait_for_function("""([t, b]) => {
          const a = K.fanSpots.find(f => f.id === t), c = K.fanSpots.find(f => f.id === b);
          return a && c && Math.abs((c.y - a.y) - 32.8) < 3 && Math.abs(a.x - c.x) < 10;
        }""", arg=[top_id, base_id], timeout=5000)
    # The base taps empty ground: the upper spectator hops down in both browsers.
    base.wait_for_timeout(350)  # finish join animation
    base.evaluate("""() => {
      const mine = K.fanSpots.find(f => f.id === K.mine().id);
      K.tapFans(mine.x > 160 ? 34 : SW - 34);
    }""")
    for p in pages:
        p.wait_for_function("t => !K.on[t]", arg=top_id, timeout=5000)
        p.wait_for_function("""t => {
          const f = K.fanSpots.find(f => f.id === t);
          const base = K.fanSpots.find(p => p.id !== t);
          return f && base && Math.abs(f.y - base.y) < 2;
        }""", arg=top_id, timeout=5000)
    # Rejoining a column gets the host's authoritative K.on snapshot after reload.
    top.wait_for_timeout(350)
    top.evaluate("""id => {
      const p = K.fanSpots.find(f => f.id === id);
      K.tapFans(p.x, p.y - 20);
    }""", base_id)
    for p in pages:
        p.wait_for_function("([t, b]) => K.on[t] === b", arg=[top_id, base_id], timeout=5000)
    top.reload()
    top.wait_for_function("K.comp && !K.comp.wait && K.fanSpots.length >= 2", timeout=10000)
    top.wait_for_function("([t, b]) => K.on[t] === b", arg=[top_id, base_id], timeout=5000)
    close_pages(pages)


def test_fifth_spectator_cannot_climb_a_column_of_four(site, browser):
    _, pages, athlete, fans = watching(site, browser,
        ("Eero", "Aino", "Ville", "Onni", "Iida", "Olli"))
    ids = [p.evaluate("K.mine().id") for p in fans]
    # Use a different phone for every climb so the per-phone 300 ms tap throttle doesn't interfere.
    for i in range(1, 5):
        climber = fans[i]
        target_id = ids[i - 1]
        climber.evaluate("""id => {
          const p = K.fanSpots.find(f => f.id === id);
          K.tapFans(p.x, p.y - 20);
        }""", target_id)
        if i < 4:
            for p in pages:
                p.wait_for_function("([a, b]) => K.on[a] === b", arg=[ids[i], target_id], timeout=5000)
        else:
            for p in pages:
                p.wait_for_function("id => !K.on[id]", arg=ids[i], timeout=5000)
    for p in pages:
        assert p.evaluate("Object.keys(K.on).length") == 3
    close_pages(pages)


SCROLLING = ["pituushyppy", "keihas", "kuula", "korkeushyppy", "seivashyppy", "makihyppy"]


@pytest.mark.parametrize("slug", SCROLLING)
def test_each_event_scrolls_from_zero_at_the_start(site, browser, slug):
    """Each event's scroll is 0 while its athlete stands at the start, so the friends stand where
    they always did until the camera moves."""
    relay, pages, code = room(site, browser, newest(slug), ["Eero", "Aino", "Ville"])
    host = pages[0]
    turn = on_turn(host)
    page = next(p for p in pages if p.evaluate("AiPelitRooms.me") != turn)
    page.wait_for_function("K.fanSpots.length === 2", timeout=8000)
    page.evaluate("""() => {
      const original = K.drawFans;
      K.drawFans = function (ctx, box) { window.__scroll = box.scroll; return original(ctx, box); };
    }""")
    page.wait_for_function("window.__scroll !== undefined")
    page.wait_for_timeout(600)
    assert abs(page.evaluate("window.__scroll")) < 1
    close_pages(pages)


def climb(page, onto):
    page.evaluate("""id => { const p = K.fanSpots.find(f => f.id === id); K.tapFans(p.x, p.y - 20); }""", onto)


def test_two_climb_onto_the_same_friend_at_once(site, browser):
    """Two phones climb onto the same friend at the same moment: the host stacks them one over
    the other, and every phone ends with the same column."""
    _, pages, athlete, fans = watching(site, browser, ("Eero", "Aino", "Ville", "Iida"))
    ids = [p.evaluate("K.mine().id") for p in fans]
    climb(fans[1], ids[0])
    climb(fans[2], ids[0])
    for p in pages:
        p.wait_for_function("([a, b]) => !!K.on[a] && !!K.on[b]", arg=[ids[1], ids[2]], timeout=5000)
    ons = [p.evaluate("JSON.stringify(Object.entries(K.on).sort())") for p in pages]
    assert len(set(ons)) == 1, ons
    # One column: the two are on the base and on each other, not both on the base.
    on = dict(json.loads(ons[0]))
    a, b = ids[1], ids[2]
    assert (on[a], on[b]) in ((ids[0], a), (b, ids[0])), on
    close_pages(pages)


def test_the_column_comes_down_when_its_base_is_on_turn(site, browser):
    """The friend at the bottom gets the turn: the one on their shoulders hops down, on every phone."""
    _, pages, athlete, fans = watching(site, browser, ("Eero", "Aino", "Ville"))
    base, top = fans
    base_id, top_id = base.evaluate("K.mine().id"), top.evaluate("K.mine().id")
    base_p = base.evaluate("AiPelitRooms.me")
    climb(top, base_id)
    for p in pages:
        p.wait_for_function("([t, b]) => K.on[t] === b", arg=[top_id, base_id], timeout=5000)
    host = pages[0]
    phones = {p.evaluate("AiPelitRooms.me"): p for p in pages}
    play(host, phones, lambda pid: pid == base_p)
    for p in pages:
        p.wait_for_function(f"K.current() && K.current().p === {json.dumps(base_p)}", timeout=5000)
    for p in (athlete, top):
        p.wait_for_function("t => K.fanSpots.length && !K.on[t]", arg=top_id, timeout=5000)
    close_pages(pages)
