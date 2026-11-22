"""Entry point: python -m valtera {build,verify,clean} <app-name>"""
import argparse

from valtera import build, cleanup, qlik, verify


def main():
    p = argparse.ArgumentParser(prog="python -m valtera")
    sub = p.add_subparsers(dest="command", required=True)
    for name, text in [("build", "generate, upload, build, reload and verify the App"),
                       ("verify", "compare measures with the Reference calculator and capture each Sheet"),
                       ("clean", "remove what the build created for this app name")]:
        c = sub.add_parser(name, help=text)
        c.add_argument("app_name", help="app name, starting with claude- (e.g. claude-valtera-<branch>)")
        if name != "clean":
            c.add_argument("--no-capture", action="store_true",
                           help="skip the Sheet capture (for a machine without a signed-in browser)")
        if name == "build":
            c.add_argument("--sheet", action="append", default=[], metavar="FILE",
                           help="also build this Sheet file, e.g. a test fixture (repeatable)")
    a = p.parse_args()
    try:
        if a.command == "build":
            build.build(a.app_name, capture=not a.no_capture, extra_sheets=a.sheet)
        elif a.command == "verify":
            verify.verify(a.app_name, capture=not a.no_capture)
        else:
            cleanup.clean(a.app_name)
    except qlik.QlikError as e:
        raise SystemExit(f"FAIL: {e}")


if __name__ == "__main__":
    main()
