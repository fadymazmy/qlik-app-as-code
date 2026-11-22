"""Clean-up command: removes what the build created for one app name, and nothing another app still needs.

That is the app, the theme and the extensions named after the app, and the local work directory. The data
files are shared: each build claims the `valtera-data-<hash>/` folder it loads from with a marker file
`apps/<app-name>.txt` in it. Clean removes the app's marker, and the folder (with the datasets Qlik made for
its files) only when no other app's marker is left. The shared space is left in place.

Every id goes to the CLI after `--`: Qlik can assign an id that starts with "-", which would read as a flag.
"""
import shutil

from valtera import qlik
from valtera.build import DATA_PREFIX, check_name, claim_name, extension_names
from valtera.paths import workdir


def release_data(app_name, conn):
    """Remove `app_name`'s marker from each shared data folder, and a folder once no marker is left in it."""
    for folder, folder_id in qlik.data_folders(conn, DATA_PREFIX).items():
        claims = {n: f["id"] for n, f in qlik.data_files(conn, folder).items() if n.startswith(f"{folder}/apps/")}
        mine = claim_name(folder, app_name)
        if mine not in claims:
            continue
        if claims.keys() == {mine}:
            qlik.run("data-file", "rm", "--", folder_id)
            print(f"removed data-file folder {folder}/ (no other app loads from it)")
        else:
            qlik.run("data-file", "rm", "--", claims[mine])
            print(f"kept data-file folder {folder}/: {len(claims) - 1} other app(s) load from it")


def clean(app_name):
    check_name(app_name)
    space_id = qlik.find_space()
    if space_id:
        item = qlik.find_app(space_id, app_name)
        if item:
            qlik.run("app", "rm", "--", item["resourceId"])
            print(f"removed app {app_name} ({item['resourceId']})")
        release_data(app_name, qlik.datafiles_connection(space_id))
    for kind, name in [("theme", app_name), *(("extension", n) for n in extension_names(app_name).values())]:
        found = qlik.find(kind, name)
        if found:
            qlik.run(kind, "rm", "--", found)
            print(f"removed {kind} {name} ({found})")
    if workdir(app_name).exists():
        shutil.rmtree(workdir(app_name))
        print(f"removed {workdir(app_name).relative_to(workdir(app_name).parents[1])}")
    print("clean: done")
