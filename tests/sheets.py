"""The Sheets as the build assembles them, for the tests that read them. No tenant needed."""
import json
import tempfile
from functools import lru_cache
from pathlib import Path

from valtera import build
from valtera.paths import APP_DIR

# Every master measure id in the App definition.
MEASURE_IDS = {m["qInfo"]["qId"] for m in json.loads((APP_DIR / "measures.json").read_text())}


def objects(entry):
    """The properties of an entry and of every object under it, the entry first."""
    yield entry["qProperty"]
    for child in entry["qChildren"]:
        yield from objects(child)


@lru_cache(maxsize=None)
def _assembled():
    with tempfile.TemporaryDirectory() as tmp:
        build.assemble_app("claude-test", Path(tmp))
        return {p.stem: json.loads(p.read_text()) for p in (Path(tmp) / "objects").glob("*.json")}


def assembled(sheet):
    """The Sheet `sheet` (its file name without .json) as the build writes it for an app called claude-test."""
    return _assembled()[sheet]


def own(sheet):
    """(cells, {object id: properties}) of what the Sheet holds without the shared header and the Sheet itself."""
    entry, prefix = assembled(sheet), sheet + "-"
    cells = [c for c in entry["qProperty"]["cells"] if not c["name"].startswith(prefix)]
    return cells, {o["qInfo"]["qId"]: o for o in list(objects(entry))[1:] if not o["qInfo"]["qId"].startswith(prefix)}
