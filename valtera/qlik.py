"""Thin wrapper around the `qlik` CLI. The tenant and key come from the active qlik-cli context."""
import json
import subprocess
import time

SPACE = "claude-dashboard-dev"


class QlikError(RuntimeError):
    pass


def run(*args, stream=False, cwd=None):
    """Run `qlik <args>`. With stream=True the output goes straight to the terminal."""
    cmd = ["qlik", *map(str, args)]
    if stream:
        if subprocess.run(cmd, cwd=cwd).returncode != 0:
            raise QlikError(f"qlik {args[0]} {args[1]} failed")
        return None
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise QlikError(f"{' '.join(cmd[:3])} failed: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def run_slow(*args, label, timeout, every=30):
    """Run `qlik <args>` for a step that can take minutes (a data-file upload). Prints `label` with the
    elapsed time every `every` seconds, so a slow run is visibly slow, and stops it after `timeout` seconds."""
    cmd = ["qlik", *map(str, args)]
    start = time.monotonic()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    while True:
        left = timeout - (time.monotonic() - start)
        try:
            out, err = p.communicate(timeout=max(0, min(every, left)))
            break
        except subprocess.TimeoutExpired:
            if left <= every:
                p.kill()
                p.communicate()
                raise QlikError(f"{' '.join(cmd[:3])} stopped after {timeout:.0f} s without finishing")
            print(f"    {label}: {time.monotonic() - start:.0f} s", flush=True)
    if p.returncode != 0:
        raise QlikError(f"{' '.join(cmd[:3])} failed: {err.strip() or out.strip()}")
    return out


def run_json(*args):
    out = run(*args, "--json")
    return json.loads(out) if out.strip() else None


def find_space():
    """The id of the shared space, or None."""
    for s in run_json("space", "ls", "--name", SPACE) or []:
        if s["name"] == SPACE:
            return s["id"]
    return None


def find_app(space_id, name):
    """The item for the app called `name` in the space, or None."""
    items = run_json("item", "ls", "--spaceId", space_id, "--resourceType", "app", "--name", name) or []
    matches = [i for i in items if i["name"] == name]
    if len(matches) > 1:
        raise QlikError(f"more than one app called {name} in {SPACE}")
    return matches[0] if matches else None


def datafiles_connection(space_id):
    conns = json.loads(run("raw", "get", "v1/data-files/connections", "--query", f"spaceId={space_id}"))
    return conns[0]["id"]


def data_folders(connection_id, prefix):
    """{name: id} of the top-level data-file folders whose name starts with `prefix`."""
    return {f["name"]: f["id"] for f in run_json(
        "data-file", "ls", "--connectionId", connection_id, "--includeFolders", "--excludeFiles",
        "--excludeSubFolders", "--baseNameWildcard", f"{prefix}*", "--limit", "100") or []}


def data_files(connection_id, folder):
    """{path name: {"id", "size"}} of every file under `folder`, sub-folders included."""
    return {f["name"]: {"id": f["id"], "size": f["size"]} for f in run_json(
        "data-file", "ls", "--connectionId", connection_id, "--folderPath", folder, "--limit", "100") or []}


def find(kind, name):
    """The id of the tenant-wide `kind` ("theme" or "extension") called `name`, or None."""
    for t in run_json(kind, "ls") or []:
        if t["name"] == name:
            return t["id"]
    return None
