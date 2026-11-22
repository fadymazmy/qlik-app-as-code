"""Sheet capture: waiting for the sign-in survives the sign-in's navigations, and asks for a sign-in only
when a sign-in page shows.

Runs headless Google Chrome against a local fake tenant: no tenant, credentials or display needed.
"""
import contextlib
import io
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from valtera import capture, qlik

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class FakeTenant(BaseHTTPRequestHandler):
    """The sheet (on 127.0.0.1) bounces to a cross-site sign-in page (on localhost). Three seconds later
    the person "signs in": the page navigates back to the sheet, whose response is held for 3 s while
    the sign-in page keeps its main thread busy, so the wait loop's 2 s poll is in flight when the
    navigation commits. With a valid session the sheet instead passes through a redirect page (on localhost,
    no sign-in form) that returns to it at once."""

    def do_GET(self):
        port = self.server.server_port
        if self.path.startswith("/session"):
            body = "<script>setTimeout(() => location.replace('http://127.0.0.1:%d/sense/app/a/sheet/s?signed-in'), 2500)</script>" % port
        elif self.path.startswith("/valid"):
            body = "<script>setTimeout(() => location.replace('http://localhost:%d/session'), 300)</script>" % port
        elif self.path.startswith("/login"):
            body = ("<form><input type='email' name='username'><input type='password'></form><script>setTimeout(() => { location.href = 'http://127.0.0.1:%d/sense/app/a/sheet/s?signed-in';"
                    " setTimeout(() => { const t = Date.now(); while (Date.now() - t < 6000) {} }, 100) }, 3000)"
                    "</script>" % port)
        elif self.path.endswith("?signed-in"):
            time.sleep(3)
            body = "<div class='qv-gridcell'>ok</div>"
        else:
            body = "<script>setTimeout(() => location.replace('http://localhost:%d/login'), 300)</script>" % port
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


@unittest.skipIf(sync_playwright is None, "Playwright is not installed")
class SignInWait(unittest.TestCase):
    def open_sheet(self, path):
        """Open the fake tenant's `path` as the capture does; return what it printed."""
        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeTenant)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            try:
                page = browser.new_page()
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    capture._open_sheet(page, "http://127.0.0.1:%d%s" % (server.server_port, path))
                self.assertTrue(page.url.endswith("?signed-in"))
                return out.getvalue()
            finally:
                browser.close()

    def test_navigation_during_the_sign_in_wait_is_tolerated(self):
        self.assertIn("sign in to the tenant", self.open_sheet("/sense/app/a/sheet/s"))

    def test_a_valid_session_is_not_asked_to_sign_in(self):
        self.assertNotIn("sign in to the tenant", self.open_sheet("/valid/sense/app/a/sheet/s"))


def cell(object_id, *lines):
    """A drawn Sheet cell as the Sense client shows it, its text on separate lines."""
    return (f"<div class='qv-gridcell' tid='{object_id}' data-render-state='1'><div class='qv-object-content'>"
            + "".join(f"<div>{line}</div>" for line in lines) + "</div></div>")


@unittest.skipIf(sync_playwright is None, "Playwright is not installed")
class SheetCheck(unittest.TestCase):
    """sheet_check.js on a fake Sheet: a KPI whose value failed shows "-" under its title, also when the KPI is a
    child of a layout container, whose text holds its children's."""

    def check(self, html, cells):
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            try:
                page = browser.new_page()
                page.set_content(html)
                return {r["id"]: r["status"] for r in page.evaluate(capture.CHECK_JS, cells)}
            finally:
                browser.close()

    def test_a_kpi_showing_a_dash_under_its_title_is_an_error(self):
        html = cell("kpi-ok", "Sales YTD", "€1.23 bn") + cell("kpi-failed", "Sales YTD", "-")
        self.assertEqual(self.check(html, [{"id": "kpi-ok", "kpi": True}, {"id": "kpi-failed", "kpi": True}]),
                         {"kpi-ok": "ok", "kpi-failed": "error"})

    def test_a_failed_kpi_inside_a_layout_container_is_an_error(self):
        html = cell("container", "A  ·  Comparison A", "Business Group", "Propulsion", "Sales YTD", "-")
        self.assertEqual(self.check(html, [{"id": "container", "kpi": True}]), {"container": "error"})

    def test_a_dash_in_a_table_is_a_null_cell_not_an_error(self):
        html = cell("table", "Region", "Europe", "-")
        self.assertEqual(self.check(html, [{"id": "table", "kpi": False}]), {"table": "ok"})


class SheetObjects(unittest.TestCase):
    """capture.sheets: the objects of each Sheet to check, a layout container's children included, against a fake
    qlik CLI."""

    OBJECTS = [{"qId": "s1", "qType": "sheet", "title": "One"}, {"qId": "table", "qType": "sn-table"},
               {"qId": "side", "qType": "sn-layout-container"}, {"qId": "side-sales", "qType": "kpi"},
               {"qId": "side-filters", "qType": "filterpane"}]
    PROPERTIES = {"s1": {"rank": 0, "cells": [{"name": "table"}, {"name": "side"}]},
                  "side": {"objects": [{"childRefId": "side-sales"}, {"childRefId": "side-filters"},
                                       {"childRefId": "side-gone"}]}}

    def test_a_container_is_checked_with_its_children(self):
        with mock.patch.object(qlik, "run_json", return_value=self.OBJECTS), \
                mock.patch.object(qlik, "run", lambda *a: json.dumps(self.PROPERTIES.get(a[3], {}))):
            [(sheet_id, title, cells)] = capture.sheets("app")
        self.assertEqual((sheet_id, title), ("s1", "One"))
        self.assertEqual(cells, [{"id": "table", "kpi": False, "children": [], "missing": []},
                                 {"id": "side", "kpi": True, "children": ["side-sales", "side-filters", "side-gone"],
                                  "missing": ["side-gone"]}])


if __name__ == "__main__":
    unittest.main()
