"""Invites as phone notifications (#367): the "Ilmoitukset kutsuista" switch on the shelf's friends
page (public/app.js, public/kaverit.js). Headless Chromium has no push service, so the page's
`pushManager` and notification permission are stubbed; the server side is
tests/server/push.test.mjs and the service worker's part tests/server/sw_push.test.mjs."""

import json
import re

from test_kaverit import A, B, phones  # noqa: F401  (the fixture)

ENDPOINT = "https://fcm.googleapis.com/fcm/send/testi"

# The phone's push subscription and permission, kept in this page. `__perm` is what the permission
# prompt answers.
STUB = """
(() => {
  let sub = null, perm = 'default';
  window.__perm = 'granted';
  const pm = {
    getSubscription: async () => sub,
    subscribe: async (o) => {
      window.__key = Array.from(new Uint8Array(o.applicationServerKey));
      window.__visible = o.userVisibleOnly;
      sub = { endpoint: %s, unsubscribe: async () => { sub = null; return true; } };
      return sub;
    },
  };
  Object.defineProperty(ServiceWorkerRegistration.prototype, 'pushManager', { get: () => pm });
  Object.defineProperty(Notification, 'permission', { get: () => perm });
  Notification.requestPermission = async () => (perm = window.__perm);
  window.__setPerm = (p) => { perm = p; };
})();
""" % json.dumps(ENDPOINT)


def friends_page(phones, name="Bertta", stub=STUB):
    phones.api.names.update({A: "Aino", B: "Bertta"})
    phones.api.friends.add(frozenset((A, B)))
    calls = []

    def push(route):
        req = route.request
        calls.append((req.method, json.loads(req.post_data or "{}")))
        route.fulfill(status=200, content_type="application/json", body='{"ok":true}')

    page = phones(name, None, player=B)
    page.context.route(re.compile(r".*/api/push$"), push)
    if stub:
        page.context.add_init_script(stub)
    page.goto(phones.site.url + "#/kaverit")
    page.reload()
    page.wait_for_selector(".push-row")
    return page, calls


def switch(page):
    return page.locator(".push-switch")


def test_the_switch_turns_invite_notifications_on_and_off(phones):
    page, calls = friends_page(phones)
    page.wait_for_function("document.querySelector('.push-switch') && !document.querySelector('.push-switch').disabled")
    assert switch(page).get_attribute("aria-checked") == "false"
    assert switch(page).inner_text() == "Pois"
    assert "Ilmoitukset kutsuista" in page.locator(".push-row").inner_text()
    switch(page).click()
    page.wait_for_function("document.querySelector('.push-switch').getAttribute('aria-checked') === 'true'")
    assert switch(page).inner_text() == "Päällä"
    assert calls == [("POST", {"player": B, "endpoint": ENDPOINT})]
    # Subscribed with the server's public key, for notifications the phone shows.
    key = page.evaluate("window.__key")
    assert len(key) == 65 and key[0] == 4
    assert page.evaluate("window.__visible") is True
    # It stays on across a visit elsewhere and back.
    page.goto(phones.site.url + "#/")
    page.goto(phones.site.url + "#/kaverit")
    page.wait_for_function("document.querySelector('.push-switch').getAttribute('aria-checked') === 'true'")
    switch(page).click()
    page.wait_for_function("document.querySelector('.push-switch').getAttribute('aria-checked') === 'false'")
    assert calls[-1] == ("DELETE", {"player": B, "endpoint": ENDPOINT})
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    assert page.errors == []


def test_permission_refused_says_where_to_allow_it(phones):
    page, calls = friends_page(phones)
    page.evaluate("window.__perm = 'denied'")
    page.wait_for_function("!document.querySelector('.push-switch').disabled")
    switch(page).click()
    page.wait_for_function("document.querySelector('.push-note').textContent.includes('estetty')")
    assert page.locator(".push-note").inner_text() == "Ilmoitukset on estetty puhelimen asetuksista."
    assert switch(page).is_disabled()
    assert calls == []


def test_already_blocked_shows_the_same_note(phones):
    page, _ = friends_page(phones, stub=STUB + "window.__setPerm('denied');")
    page.wait_for_function("document.querySelector('.push-note').textContent.includes('estetty')")
    assert switch(page).is_disabled()


def test_an_iphone_outside_the_installed_app_is_told_to_add_it_to_the_home_screen(phones):
    iphone = """
    Object.defineProperty(navigator, 'userAgent', { get: () => 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1' });
    delete window.PushManager;
    """
    page, _ = friends_page(phones, stub=iphone)
    page.wait_for_function("document.querySelector('.push-note').textContent.includes('kotivalikkoon')")
    assert page.locator(".push-note").inner_text() == "iPhonessa ilmoitukset toimivat, kun pelit on lisätty kotivalikkoon."
    assert switch(page).is_disabled()
    assert page.errors == []


def test_no_nickname_asks_for_one_first(phones):
    page, calls = friends_page(phones, name=None)
    page.wait_for_function("!document.querySelector('.push-switch').disabled")
    switch(page).click()
    page.wait_for_function("document.querySelector('.push-note').textContent.includes('nimimerkki')")
    assert page.locator(".push-note").inner_text() == "Valitse ensin nimimerkki."
    assert switch(page).get_attribute("aria-checked") == "false"
    assert calls == []


def test_the_switch_row_fits_a_390_px_phone_and_turns(phones):
    page, _ = friends_page(phones)
    page.wait_for_function("!document.querySelector('.push-switch').disabled")
    for size in ({"width": 390, "height": 844}, {"width": 740, "height": 360}):
        page.set_viewport_size(size)
        row = page.locator(".push-row").bounding_box()
        sw = page.locator(".push-switch").bounding_box()
        assert page.evaluate("document.documentElement.scrollWidth") <= size["width"]
        assert sw["x"] + sw["width"] <= row["x"] + row["width"]
