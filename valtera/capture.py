"""Sheet capture: opens each Sheet in a signed-in browser, saves a screenshot and fails on any object
that is not rendered, empty or in error.

Qlik's reporting API cannot be used (it rejects Custom Extensions and exports PDF only), so this drives
the installed Google Chrome through Playwright with a persistent profile outside the repo. The first run
opens a Chrome window: sign in to the tenant there once and the session is kept for later runs.
"""
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

from valtera import qlik

CHECK_JS = (Path(__file__).parent / "sheet_check.js").read_text()
STATE_JS = (Path(__file__).parent / "state_check.js").read_text()
PROFILE = Path(os.environ.get("VALTERA_CHROME_PROFILE", Path.home() / ".cache" / "claude-valtera" / "chrome-profile"))
SIGN_IN_WAIT_S = 300
RENDER_WAIT_S = 60
SETTLE_S = 3
VIEWPORT = {"width": 1440, "height": 900}
# A sign-in form: the tenant's sign-in page asks for an email address first, then a password.
SIGN_IN_FORM = "input[type=email], input[type=password], input[name=username]"


def sheets(app_id):
    """[(sheet id, title, [cell])] in rank order, a cell being {"id", "kpi", "children", "missing"}: the object
    its Sheet cell declares, whether it is a KPI or a layout container holding one, the children a layout
    container places (`objects[].childRefId`) and those of them the App does not hold."""
    objects = qlik.run_json("app", "object", "ls", "-a", app_id)
    types = {o["qId"]: o["qType"] for o in objects}

    def properties(object_id):
        return json.loads(qlik.run("app", "object", "properties", object_id, "-a", app_id))

    def cell(object_id):
        children = ([c["childRefId"] for c in properties(object_id).get("objects", [])]
                    if types.get(object_id) == "sn-layout-container" else [])
        return {"id": object_id, "kpi": "kpi" in [types.get(i) for i in [object_id, *children]],
                "children": children, "missing": [c for c in children if c not in types]}
    out = []
    for o in objects:
        if o["qType"] == "sheet":
            props = properties(o["qId"])
            out.append((props.get("rank", 0), o["qId"], o["title"], [cell(c["name"]) for c in props.get("cells", [])]))
    return [s[1:] for s in sorted(out)]


def _open_sheet(page, url):
    """Go to the sheet; if the tenant asks for a sign-in, wait for the person to sign in in the window. A valid
    session can pass through redirects on the way, so the person is asked only once a sign-in form shows."""
    page.goto(url)
    deadline = time.time() + SIGN_IN_WAIT_S
    warned = False
    while not page.locator(".qv-gridcell").count():
        if time.time() > deadline:
            raise qlik.QlikError("the sheet did not open; sign in to the tenant in the capture browser "
                                 "window, then run verify again")
        if not warned and page.locator(SIGN_IN_FORM).count():
            print("  sign in to the tenant in the Chrome window that opened (waiting up to 5 minutes)")
            warned = True
        page.wait_for_timeout(2000)


def _wait_rendered(page, cells):
    deadline = time.time() + RENDER_WAIT_S
    while time.time() < deadline:
        if all(r["status"] != "not rendered" for r in page.evaluate(CHECK_JS, cells)):
            break
        page.wait_for_timeout(1000)
    page.wait_for_timeout(SETTLE_S * 1000)
    return page.evaluate(CHECK_JS, cells)


@contextmanager
def browser_page():
    """A page of the installed Google Chrome with the capture's persistent profile, closed afterwards."""
    from playwright.sync_api import sync_playwright

    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            str(PROFILE), channel="chrome", headless=False, viewport=VIEWPORT)
        try:
            yield browser.pages[0] if browser.pages else browser.new_page()
        finally:
            browser.close()


def evaluate_in_states(page, app_id, app_url, sides, measures):
    """Evaluate master measures inside alternate states, each after its own selection, in one engine
    session opened from the signed-in browser (qlik-cli cannot select in an alternate state).
    `sides` is {state: {field: value}}, `measures` a list of library ids; returns {state: [cell]}."""
    _open_sheet(page, app_url)
    return page.evaluate(STATE_JS, {"appId": app_id, "sides": sides, "measures": measures})


def capture_sheets(page, app_id, app_url, out_dir):
    """Capture every Sheet of the App into `out_dir`; return a list of failure labels."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    failures = []
    for sheet_id, title, cells in sheets(app_id):
        _open_sheet(page, f"{app_url}/sheet/{sheet_id}/state/analysis")
        results = _wait_rendered(page, cells)
        shot = out_dir / f"{sheet_id}.png"
        page.screenshot(path=str(shot))
        print(f"  {title}: {shot}")
        if not cells:
            failures.append(f"{title}: no objects")
            print("    FAIL the Sheet has no objects")
        for c, r in zip(cells, results):
            if c["missing"]:  # a child the container places but the App does not hold leaves its slot empty
                r = dict(r, status="missing children", text=", ".join(c["missing"]))
            ok = r["status"] == "ok"
            held = f" (holds {', '.join(c['children'])})" if c["children"] else ""
            print(f"    {'ok  ' if ok else 'FAIL'} {r['id']}{held}: {r['status']} {r['text']!r}")
            if not ok:
                failures.append(f"{title}/{r['id']} {r['status']}")
    return failures
