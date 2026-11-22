"""Build command: takes an empty space to a working, verified App.

Order: generate data, ensure the space, upload the data files, upload the theme and the Custom Extensions,
create or find the app, add the alternate states its objects name, build it from the App definition
(which reloads it), verify.
"""
import hashlib
import json
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

from valtera import data, qlik, verify
from valtera.paths import APP_DIR, EXT_DIR, THEME_DIR, workdir

SEED = 2026
SIZE = 500_000
DATA_PREFIX = "valtera-data-"
UPLOAD_ATTEMPTS = 5
UPLOAD_MIN_RATE = 20_000  # bytes a second below which an upload attempt is given up
RETRY_WAIT = 60


def merge(base, over):
    """Deep-merge dicts; lists and scalars from `over` replace those in `base`."""
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = merge(base[k], v) if k in base else v
        return out
    return over


def with_defaults(entry):
    """Overlay each object in a {qProperty, qChildren} entry on the client's default tree for its type."""
    prop = entry["qProperty"]
    default = APP_DIR / "defaults" / f"{prop['qInfo']['qType']}.json"
    if default.exists():
        prop = merge(json.loads(default.read_text()), prop)
    return {"qProperty": prop, "qChildren": [with_defaults(c) for c in entry["qChildren"]]}


def extension_names(app_name):
    """{source folder in extensions/: tenant-wide extension name}. The name is `<app-name>-<folder>`, so
    each app name uploads its own copy and parallel branches never overwrite each other's extensions."""
    return {d.name: f"{app_name}-{d.name}" for d in sorted(EXT_DIR.iterdir()) if (d / "src").is_dir()}


def with_header(entry, header):
    """Put the shared header (Navigation Bar and filter strip) on top of a Sheet, with ids unique to it."""
    prefix = entry["qProperty"]["qInfo"]["qId"] + "-"

    def prefixed(child):
        prop = child["qProperty"]
        return {"qProperty": dict(prop, qInfo=dict(prop["qInfo"], qId=prefix + prop["qInfo"]["qId"])),
                "qChildren": [prefixed(c) for c in child["qChildren"]]}

    prop = entry["qProperty"]
    cells = [dict(c, name=prefix + c["name"]) for c in header["cells"]]
    return {"qProperty": dict(prop, cells=cells + prop.get("cells", [])),
            "qChildren": [prefixed(c) for c in header["qChildren"]] + entry["qChildren"]}


def with_bounds(entry):
    """Give each cell of a Sheet the `bounds` Qlik also needs: its col, row, colspan and rowspan in percent
    of the Sheet's grid."""
    prop = entry["qProperty"]
    cols, rows = prop["columns"], prop["rows"]

    def bounds(c):
        return {"x": round(c["col"] / cols * 100, 4), "y": round(c["row"] / rows * 100, 4),
                "width": round(c["colspan"] / cols * 100, 4), "height": round(c["rowspan"] / rows * 100, 4)}
    return dict(entry, qProperty=dict(prop, cells=[dict(c, bounds=bounds(c)) for c in prop["cells"]]))


def with_theme_colours(node, colours):
    """Replace each theme variable (`@pos`) in a Sheet's strings, colour expressions included, by its colour in
    theme/theme.json `_variables`: Qlik resolves theme variables only inside the theme itself."""
    if isinstance(node, dict):
        return {k: with_theme_colours(v, colours) for k, v in node.items()}
    if isinstance(node, list):
        return [with_theme_colours(v, colours) for v in node]
    if not isinstance(node, str):
        return node

    def colour(match):
        if match[0] not in colours:
            raise SystemExit(f"{match[0]} is not a variable in theme/theme.json: {node}")
        return colours[match[0]]
    return re.sub(r"@\w+", colour, node)


def name_extensions(entry, names):
    """Replace each extension's folder name (as written in app/) by its tenant-wide extension name."""
    prop = entry["qProperty"]
    if prop.get("visualization") in names:
        prop["visualization"] = prop["qInfo"]["qType"] = names[prop["visualization"]]
    for cell in prop.get("cells", []):
        cell["type"] = names.get(cell["type"], cell["type"])
    for child in entry["qChildren"]:
        name_extensions(child, names)
    return entry


def assemble_app(app_name, out, extra_sheets=(), folder=None):
    """Write the qlik app build inputs for `app_name` into `out`, plus any extra Sheet files (test fixtures).
    `folder` is the data-file folder the script loads from (vDataFolder); tests that load no data leave it out."""
    if out.exists():
        shutil.rmtree(out)
    (out / "objects").mkdir(parents=True)
    script = (APP_DIR / "script.qvs").read_text()
    if folder:
        script = f"SET vDataFolder='lib://:DataFiles/{folder}/';\n{script}"
    (out / "script.qvs").write_text(script)
    for name in ["measures.json", "dimensions.json", "variables.json"]:
        shutil.copy(APP_DIR / name, out / name)
    appprops = json.loads((APP_DIR / "appprops.json").read_text())
    appprops["theme"] = app_name
    (out / "objects" / "appprops.json").write_text(json.dumps(appprops, indent=1))
    header = json.loads((APP_DIR / "header.json").read_text())
    names = extension_names(app_name)
    colours = json.loads((THEME_DIR / "theme.json").read_text())["_variables"]
    for sheet in [*sorted((APP_DIR / "sheets").glob("*.json")), *map(Path, extra_sheets)]:
        entry = with_theme_colours(with_bounds(with_header(json.loads(sheet.read_text()), header)), colours)
        entry = name_extensions(with_defaults(entry), names)
        (out / "objects" / sheet.name).write_text(json.dumps(entry, indent=1, ensure_ascii=False))
    (out / "config.yml").write_text(
        "script: script.qvs\nmeasures: measures.json\ndimensions: dimensions.json\nvariables: variables.json\n"
        "objects: objects/*.json\n")


def package_theme(theme_name, zip_path):
    """Zip the theme under `theme_name`, which is also its qext name."""
    qext = {"name": theme_name, "type": "theme", "version": "1.0.0", "author": "claude",
            "description": "Valtera Sales Dashboard dark theme (built from code)"}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{theme_name}/{theme_name}.qext", json.dumps(qext, indent=1))
        for f in sorted(THEME_DIR.iterdir()):
            z.write(f, f"{theme_name}/{f.name}")


def package_extension(folder, ext_name, out_dir):
    """Build extensions/<folder> with Qlik's nebula CLI (`nebula build`, then `nebula sense`) and zip it
    as `ext_name`; return the zip path. nebula names the files after the folder, so they are renamed."""
    nebula = EXT_DIR / "node_modules" / ".bin" / "nebula"
    if not nebula.exists():
        raise SystemExit("the extension tooling is not installed: run `nvm use && npm ci --prefix extensions`")
    out = (out_dir / ext_name).resolve()  # nebula runs in the source folder
    if out.exists():
        shutil.rmtree(out)
    for args in (["build", "--sourcemap", "false"], ["sense", "--output", out]):
        if subprocess.run([nebula, *args], cwd=EXT_DIR / folder).returncode != 0:
            raise SystemExit(f"nebula {args[0]} failed for extensions/{folder} (it needs Node 24: `nvm use`)")
    qext = json.loads((out / f"{folder}.qext").read_text())
    (out / f"{folder}.qext").unlink()
    (out / f"{ext_name}.qext").write_text(json.dumps(dict(qext, name=ext_name), indent=2))
    (out / f"{folder}.js").rename(out / f"{ext_name}.js")
    zip_path = out_dir / f"{ext_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(p for p in out.rglob("*") if p.is_file()):
            z.write(f, f"{ext_name}/{f.relative_to(out)}")
    return zip_path


def check_name(app_name):
    if not app_name.startswith("claude-"):
        raise SystemExit(f"app name must start with 'claude-' (it also names the tenant-wide theme): {app_name}")


def data_folder(files):
    """The shared data-file folder for these generated files: `valtera-data-<hash of their names and bytes>`.
    Builds of the same data share one copy; different data gets its own folder, so no build overwrites
    data another app loads."""
    h = hashlib.sha256()
    for f in sorted(files):
        h.update(f"{f.name}\0{f.stat().st_size}\0".encode())
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    return DATA_PREFIX + h.hexdigest()[:12]


def claim_name(folder, app_name):
    """The marker file saying `app_name` loads from `folder`; clean removes the folder with the last one."""
    return f"{folder}/apps/{app_name}.txt"


def upload_timeout(size):
    """Seconds one upload attempt may take: two minutes plus the file at UPLOAD_MIN_RATE bytes a second."""
    return 120 + size / UPLOAD_MIN_RATE


def put_data_file(path, name, conn, folder, held):
    """Upload `path` as `name` unless the tenant already holds a file of that name and size. Each attempt is
    resumable and stopped after upload_timeout(); a failed attempt is retried and the next one resumes it."""
    size = path.stat().st_size
    label = f"{name} ({size / 1e6:.1f} MB)"
    for attempt in range(1, UPLOAD_ATTEMPTS + 1):
        if held and held["size"] == size:
            print(f"  {label}: already on the tenant")
            return
        args = ("data-file", "update") if held else ("data-file", "create")
        print(f"  {label}: uploading (attempt {attempt}/{UPLOAD_ATTEMPTS}, "
              f"gives up after {upload_timeout(size) / 60:.0f} min)", flush=True)
        start = time.monotonic()
        try:
            qlik.run_slow(*args, "--file", path, "--name", name, "--connectionId", conn, "--resumable",
                          *(("--", held["id"]) if held else ()), label=label, timeout=upload_timeout(size))
            print(f"  {label}: uploaded in {time.monotonic() - start:.0f} s")
            return
        except qlik.QlikError as e:
            print(f"  {label}: {e}", flush=True)
            if attempt == UPLOAD_ATTEMPTS:
                raise
        time.sleep(RETRY_WAIT)  # a stopped resumable upload stays locked (HTTP 423) for a short while
        held = qlik.data_files(conn, folder).get(name)  # a parallel build may have uploaded it meanwhile


def upload_data(app_name, files, space_id, work):
    """Make sure the tenant holds `files` in their shared data folder, claim the folder for `app_name`
    and return the folder's name. Only the files the tenant does not already hold are sent."""
    conn = qlik.datafiles_connection(space_id)
    folder = data_folder(files)
    claim = work / "claim.txt"
    claim.write_text(f"{app_name} loads its data from {folder}/; `clean {app_name}` removes this file.\n")
    held = qlik.data_files(conn, folder)
    print(f"  {folder}/: {len(files)} files, {sum(f.stat().st_size for f in files) / 1e6:.1f} MB")
    for path, name in [(claim, claim_name(folder, app_name)), *((f, f"{folder}/{f.name}") for f in files)]:
        put_data_file(path, name, conn, folder, held.get(name))
    return folder


def upload(kind, name, zip_path):
    """Create the tenant-wide `kind` ("theme" or "extension") called `name` from `zip_path`, or patch it."""
    found = qlik.find(kind, name)
    if found:
        qlik.run(kind, "patch", "--file", zip_path, "--", found)  # an id may start with "-"
    else:
        qlik.run(kind, "create", "--file", zip_path)


def alternate_states(objects_dir):
    """The alternate states the assembled objects name in `qStateName`, sorted."""
    def names(node):
        if isinstance(node, dict):
            yield from ([node["qStateName"]] if node.get("qStateName") not in (None, "", "$") else [])
            for v in node.values():
                yield from names(v)
        elif isinstance(node, list):
            for v in node:
                yield from names(v)
    return sorted({n for f in objects_dir.glob("*.json") for n in names(json.loads(f.read_text()))})


def add_states(app_id, states):
    """Add each alternate state the app lacks with `qlik app state add` (a state only declared in the app
    properties is listed but does not work). Existing states are kept, so a rebuild changes nothing."""
    existing = set(qlik.run_json("app", "state", "ls", "-a", app_id) or [])
    for state in states:
        if state not in existing:
            qlik.run("app", "state", "add", state, "-a", app_id)
        print(f"  state {state}{'' if state in existing else ' added'}")


def build(app_name, capture=True, extra_sheets=()):
    check_name(app_name)
    work = workdir(app_name)

    print("1/7 generate data")
    data.generate(seed=SEED, size=SIZE, out_dir=work / "data")

    print(f"2/7 ensure space {qlik.SPACE}")
    space_id = qlik.find_space() or qlik.run_json("space", "create", "--name", qlik.SPACE, "--type", "shared")["id"]

    print("3/7 upload data files")
    start = time.monotonic()
    data_at = upload_data(app_name, sorted((work / "data").glob("*.csv")), space_id, work)
    print(f"  done in {time.monotonic() - start:.0f} s")

    print(f"4/7 upload theme {app_name} and extensions")
    package_theme(app_name, work / "theme.zip")
    upload("theme", app_name, work / "theme.zip")
    for folder, ext_name in extension_names(app_name).items():
        upload("extension", ext_name, package_extension(folder, ext_name, work / "extensions"))
        print(f"  {ext_name}")

    print(f"5/7 create or find app {app_name}")
    item = qlik.find_app(space_id, app_name)
    app_id = item["resourceId"] if item else qlik.run_json(
        "app", "create", "--attributes-name", app_name, "--attributes-spaceId", space_id)["attributes"]["id"]
    print(f"  {app_id}")

    print("6/7 build and reload")
    assemble_app(app_name, work / "app", extra_sheets, data_at)
    add_states(app_id, alternate_states(work / "app" / "objects"))
    qlik.run("app", "build", "-a", app_id, "-c", "config.yml", stream=True, cwd=work / "app")

    print("7/7 verify")
    verify.verify(app_name, capture=capture)
