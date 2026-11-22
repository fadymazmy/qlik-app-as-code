"""The data upload and its clean-up against a fake qlik CLI: a build sends only the files the tenant does not
hold, gives up on a stuck upload and retries it, and clean leaves data another app still loads. No tenant needed."""
import io
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from valtera import build, cleanup, qlik


def write(folder, files):
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text)
    return sorted(folder.glob("*.csv"))


class DataFolder(unittest.TestCase):
    def test_same_bytes_share_a_folder_and_other_bytes_do_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = write(Path(tmp) / "a", {"sales.csv": "x\n1\n", "budget.csv": "y\n2\n"})
            b = write(Path(tmp) / "b", {"sales.csv": "x\n1\n", "budget.csv": "y\n2\n"})
            c = write(Path(tmp) / "c", {"sales.csv": "x\n1\n", "budget.csv": "y\n3\n"})
            self.assertEqual(build.data_folder(a), build.data_folder(b))
            self.assertNotEqual(build.data_folder(a), build.data_folder(c))
            self.assertRegex(build.data_folder(a), r"^valtera-data-[0-9a-f]{12}$")

    def test_the_script_loads_from_the_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            build.assemble_app("claude-test", Path(tmp), folder="valtera-data-0123456789ab")
            first = (Path(tmp) / "script.qvs").read_text().splitlines()[0]
        self.assertEqual(first, "SET vDataFolder='lib://:DataFiles/valtera-data-0123456789ab/';")


class FakeTenant:
    """The data files of one space, with qlik.run_slow failing the first `failures` uploads."""

    def __init__(self, files=None, failures=0):
        self.files = dict(files or {})  # name: size
        self.uploads = []
        self.failures = failures

    def data_files(self, conn, folder):
        return {n: {"id": f"id:{n}", "size": s} for n, s in self.files.items() if n.startswith(folder + "/")}

    def run_slow(self, *args, label, timeout):
        name, path = args[args.index("--name") + 1], args[args.index("--file") + 1]
        self.uploads.append((args[1], name))
        if self.failures:
            self.failures -= 1
            raise qlik.QlikError("stopped after 1 s without finishing")
        self.files[name] = Path(path).stat().st_size


class UploadData(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.files = write(self.work / "data", {"sales.csv": "x\n1\n", "budget.csv": "y\n22\n"})
        self.folder = build.data_folder(self.files)

    def tearDown(self):
        self.tmp.cleanup()

    def upload(self, tenant, app_name="claude-a"):
        with mock.patch.object(qlik, "datafiles_connection", return_value="conn"), \
                mock.patch.object(qlik, "data_files", tenant.data_files), \
                mock.patch.object(qlik, "run_slow", tenant.run_slow), \
                mock.patch.object(build.time, "sleep"), redirect_stdout(io.StringIO()):
            return build.upload_data(app_name, self.files, "space", self.work)

    def test_first_build_uploads_every_file_and_its_claim(self):
        tenant = FakeTenant()
        self.assertEqual(self.upload(tenant), self.folder)
        self.assertEqual(sorted(n for _, n in tenant.uploads), sorted(
            [f"{self.folder}/apps/claude-a.txt", f"{self.folder}/budget.csv", f"{self.folder}/sales.csv"]))

    def test_second_app_sends_only_its_claim(self):
        tenant = FakeTenant()
        self.upload(tenant, "claude-a")
        tenant.uploads.clear()
        self.upload(tenant, "claude-b")
        self.assertEqual(tenant.uploads, [("create", f"{self.folder}/apps/claude-b.txt")])

    def test_rebuild_sends_nothing(self):
        tenant = FakeTenant()
        self.upload(tenant)
        tenant.uploads.clear()
        self.upload(tenant)
        self.assertEqual(tenant.uploads, [])

    def test_a_file_of_another_size_is_replaced(self):
        tenant = FakeTenant()
        self.upload(tenant)
        tenant.files[f"{self.folder}/sales.csv"] = 1
        tenant.uploads.clear()
        self.upload(tenant)
        self.assertEqual(tenant.uploads, [("update", f"{self.folder}/sales.csv")])

    def test_a_failed_upload_is_retried(self):
        tenant = FakeTenant(failures=build.UPLOAD_ATTEMPTS - 1)
        self.upload(tenant)
        self.assertIn(f"{self.folder}/sales.csv", tenant.files)

    def test_it_gives_up_after_the_last_attempt(self):
        tenant = FakeTenant(failures=build.UPLOAD_ATTEMPTS)
        with self.assertRaises(qlik.QlikError):
            self.upload(tenant)
        self.assertEqual(len(tenant.uploads), build.UPLOAD_ATTEMPTS)

    def test_no_retry_once_a_parallel_build_has_uploaded_the_file(self):
        tenant = FakeTenant(failures=1)
        real, calls = tenant.data_files, []

        def data_files(conn, folder):  # the parallel build finishes while this one waits to retry
            calls.append(folder)
            if len(calls) == 2:
                tenant.files[f"{self.folder}/apps/claude-a.txt"] = (self.work / "claim.txt").stat().st_size
            return real(conn, folder)

        tenant.data_files = data_files
        self.upload(tenant)
        self.assertEqual(len(tenant.uploads), 3)  # claim (failed), budget, sales: the claim is not sent again


class ReleaseData(unittest.TestCase):
    def release(self, files):
        removed = []
        with mock.patch.object(qlik, "data_folders", return_value={"valtera-data-1": "folder-1"}), \
                mock.patch.object(qlik, "data_files", lambda conn, folder: {
                    n: {"id": f"id:{n}", "size": 1} for n in files if n.startswith(folder + "/")}), \
                mock.patch.object(qlik, "run", lambda *args: removed.append(args[-1])), \
                redirect_stdout(io.StringIO()):
            cleanup.release_data("claude-a", "conn")
        return removed

    def test_keeps_a_folder_another_app_still_claims(self):
        removed = self.release(["valtera-data-1/sales.csv", "valtera-data-1/apps/claude-a.txt",
                                "valtera-data-1/apps/claude-b.txt"])
        self.assertEqual(removed, ["id:valtera-data-1/apps/claude-a.txt"])

    def test_removes_the_folder_with_the_last_claim(self):
        removed = self.release(["valtera-data-1/sales.csv", "valtera-data-1/apps/claude-a.txt"])
        self.assertEqual(removed, ["folder-1"])

    def test_leaves_a_folder_the_app_never_claimed(self):
        removed = self.release(["valtera-data-1/sales.csv", "valtera-data-1/apps/claude-b.txt"])
        self.assertEqual(removed, [])


class IdsAfterDoubleDash(unittest.TestCase):
    """Qlik can assign an id that starts with "-"; every id the build or clean passes to the CLI comes after
    `--`, so the CLI cannot read it as a flag."""

    def calls(self, action):
        calls = []
        with mock.patch.object(qlik, "run", lambda *args, **kw: calls.append(args)), \
                mock.patch.object(qlik, "find", lambda kind, name: {"theme": "-theme", "extension": "-ext"}[kind]), \
                mock.patch.object(qlik, "find_space", return_value="space"), \
                mock.patch.object(qlik, "find_app", return_value={"resourceId": "-app"}), \
                mock.patch.object(qlik, "datafiles_connection", return_value="conn"), \
                mock.patch.object(qlik, "data_folders", return_value={"valtera-data-1": "-folder"}), \
                mock.patch.object(qlik, "data_files", return_value={"valtera-data-1/apps/claude-a.txt": {
                    "id": "-claim", "size": 1}}), \
                redirect_stdout(io.StringIO()):
            action()
        return calls

    def assert_ids_after_dash(self, calls, ids):
        for args in calls:
            for i in ids & set(args):
                with self.subTest(call=args):
                    self.assertIn("--", args)
                    self.assertGreater(args.index(i), args.index("--"))
        self.assertEqual(ids, {a for args in calls for a in args} & ids, "every id was passed")

    def test_theme_and_extension_patch(self):
        self.assert_ids_after_dash(self.calls(lambda: (build.upload("theme", "claude-a", Path("t.zip")),
                                                       build.upload("extension", "claude-a-x", Path("x.zip")))),
                                   {"-theme", "-ext"})

    def test_clean(self):
        self.assert_ids_after_dash(self.calls(lambda: cleanup.clean("claude-a")),
                                   {"-app", "-folder", "-theme", "-ext"})

    def test_a_data_file_update(self):
        calls = []

        def run_slow(*args, label, timeout):
            calls.append(args)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(qlik, "run_slow", run_slow), \
                redirect_stdout(io.StringIO()):
            path = Path(tmp) / "sales.csv"
            path.write_text("x")
            build.put_data_file(path, "f/sales.csv", "conn", "f", {"id": "-file", "size": 2})
        self.assert_ids_after_dash(calls, {"-file"})


class RunSlow(unittest.TestCase):
    """qlik.run_slow against a fake `qlik` executable on PATH."""

    def run_fake(self, script, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "qlik"
            fake.write_text(f"#!/bin/sh\n{script}\n")
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"PATH": f"{tmp}{os.pathsep}{os.environ['PATH']}"}), redirect_stdout(out):
                try:
                    return qlik.run_slow("data-file", "create", label="sales.csv", **kwargs), out.getvalue()
                except qlik.QlikError as e:
                    return e, out.getvalue()

    def test_a_stuck_upload_is_stopped_and_shows_progress_meanwhile(self):
        result, printed = self.run_fake("exec sleep 30",timeout=1.5, every=0.5)
        self.assertIsInstance(result, qlik.QlikError)
        self.assertIn("stopped after", str(result))
        self.assertIn("sales.csv:", printed)

    def test_returns_the_output(self):
        result, _ = self.run_fake("echo done", timeout=5)
        self.assertEqual(result.strip(), "done")

    def test_a_failure_carries_the_error(self):
        result, _ = self.run_fake("echo 'Error: 423 Locked' >&2; exit 1", timeout=5)
        self.assertIn("423 Locked", str(result))


if __name__ == "__main__":
    unittest.main()
