"""`dojo stop` saves the roster and every module export to results/ first (engine/dojo/archive.py)."""
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from dojo import archive
from dojo.stackapi import StackError

ROSTER = [{"studentId": "student01", "name": "Ada", "ip": "10.0.0.5", "active": True},
          {"studentId": "testuser1", "name": "bot", "ip": "bot", "active": True}]
FEEDBACK = {"questions": {"q1": "Overall"}, "answers": [{"q1": 5, "comment": "great"}]}
# What two modules declare in extensions.json "exports" (engine/allocator/render_extensions.py), as merged.
EXPORTS = [
    {"id": "fb-json", "label": "Feedback", "upstream": "feedback:8080", "path": "/feedback-admin/api/export?format=json",
     "file": "feedback.json", "count": "answers", "timeout": 30},
    {"id": "fb-csv", "label": "Feedback CSV", "upstream": "feedback:8080", "path": "/feedback-admin/api/export?format=csv",
     "file": "feedback.csv", "timeout": 30},
    {"id": "scores", "label": "Scores", "upstream": "scorer:9000", "path": "/api/scores", "file": "scores.json", "timeout": 20},
]
ANSWERS = {("feedback", "/feedback-admin/api/export?format=json"): (200, FEEDBACK),
           ("feedback", "/feedback-admin/api/export?format=csv"): (200, "q1,comment\n5,great\n"),
           ("scorer", "/api/scores"): (200, {"students": [{"user": "student01", "score": 40}]})}


class ArchiveBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name) / "results"
        self.calls = []
        for p in (mock.patch.object(archive, "RESULTS_DIR", self.dir),
                  mock.patch.object(archive, "running", return_value=[SimpleNamespace(service="gateway"),
                                                                       SimpleNamespace(service="feedback")]),
                  mock.patch.object(archive.state, "read_current",
                                    return_value=SimpleNamespace(workshop="git-fundamentals", env_name=None,
                                                                 started_at=1_000_000.0,
                                                                 command="./dojo git-fundamentals"))):
            p.start()
            self.addCleanup(p.stop)

    def patch_data(self, roster=ROSTER, exports=EXPORTS, answers=ANSWERS):
        def fake_call(rt, service, method, path, **kw):
            self.calls.append((service, path, kw.get("port"), kw.get("timeout")))
            got = answers[(service, path)]
            if isinstance(got, Exception):
                raise got
            return got
        roster_mock = mock.Mock(side_effect=roster) if isinstance(roster, Exception) else mock.Mock(return_value=roster)
        for target, name, value in ((archive.results, "roster", roster_mock), (archive, "declared_exports", mock.Mock(return_value=exports)),
                                    (archive, "call", fake_call)):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)


class ArchiveTest(ArchiveBase):
    def test_saves_a_folder_named_for_the_workshop_with_a_manifest(self):
        self.patch_data()
        d = archive.save(mock.Mock(), now=1_000_000.0 + 3600)
        self.assertTrue(d.name.endswith("_git-fundamentals"))
        m = json.loads((d / "manifest.json").read_text())
        self.assertEqual((m["workshop"], m["students"], m["demo_bots"], m["counts"], m["duration_minutes"]),
                         ("git-fundamentals", 1, 1, {"fb-json": 1}, 60.0))
        self.assertEqual(sorted(m["saved"]), ["feedback.csv", "feedback.json", "roster.csv", "scores.json"])
        self.assertIn("5,great", (d / "feedback.csv").read_text())
        self.assertEqual(json.loads((d / "scores.json").read_text())["students"][0]["score"], 40)
        self.assertNotIn("10.0.0.5", (d / "roster.csv").read_text())  # no addresses

    def test_each_export_is_fetched_from_its_own_service_port_and_timeout(self):
        self.patch_data()
        archive.save(mock.Mock())
        self.assertIn(("scorer", "/api/scores", 9000, 20), self.calls)
        self.assertIn(("feedback", "/feedback-admin/api/export?format=json", 8080, 30), self.calls)

    def test_an_export_that_fails_is_recorded_and_the_rest_saved(self):
        answers = {**ANSWERS, ("feedback", "/feedback-admin/api/export?format=json"): StackError("No 'feedback' container is running"),
                   ("scorer", "/api/scores"): (500, "boom")}
        self.patch_data(answers=answers)
        d = archive.save(mock.Mock())
        m = json.loads((d / "manifest.json").read_text())
        self.assertEqual(sorted(m["skipped"]), ["fb-json", "scores"])
        self.assertIn("HTTP 500", m["skipped"]["scores"])
        self.assertTrue((d / "feedback.csv").exists())
        self.assertFalse((d / "feedback.json").exists())

    def test_a_stack_that_declares_no_exports_still_saves_its_roster(self):
        self.patch_data(exports=[])
        d = archive.save(mock.Mock())
        self.assertEqual(json.loads((d / "manifest.json").read_text())["saved"], ["roster.csv"])

    def test_an_unused_stack_saves_nothing(self):
        answers = {**ANSWERS, ("feedback", "/feedback-admin/api/export?format=json"): (200, {"questions": {}, "answers": []})}
        self.patch_data(roster=[], answers=answers)
        self.assertIsNone(archive.save(mock.Mock()))
        self.assertFalse(self.dir.exists())

    def test_the_engine_names_no_module(self):
        src = Path(archive.__file__).read_text().lower()
        self.assertNotIn("achievements", src)
        self.assertNotIn("feedback", src)

    def test_two_saves_in_one_minute_do_not_overwrite(self):
        self.patch_data()
        a = archive.save(mock.Mock(), now=1_000_000.0)
        b = archive.save(mock.Mock(), now=1_000_000.0)
        self.assertNotEqual(a, b)


def tar_stream(members):
    """A tar of {path: bytes} (a path ending in / is a directory), as the git server's `tar -cf -` would send."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            if name.endswith("/"):
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                t.addfile(info)
            else:
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))
    return io.BytesIO(buf.getvalue())


class FakeTar:
    def __init__(self, stream, code=0, err=b""):
        self.stdout, self.stderr, self.code = stream, io.BytesIO(err), code

    def wait(self):
        return self.code

    def kill(self):
        pass


GOOD = {"alice/": b"", "alice/work.git/": b"", "alice/work.git/HEAD": b"ref: refs/heads/main\n",
        "org/": b"", "org/sample.git/": b"", "org/sample.git/HEAD": b"ref: refs/heads/main\n"}


class RepoSaveTest(ArchiveBase):
    def popen(self, stream, **kw):
        return mock.patch.object(archive.subprocess, "Popen", return_value=FakeTar(stream, **kw))

    def forge(self):
        p = mock.patch("dojo.stackapi.find_container", return_value=SimpleNamespace(name="workshop_forge"))
        p.start()
        self.addCleanup(p.stop)

    def test_every_repo_lands_under_owner_and_name(self):
        self.forge()
        dest = self.dir / "repos"
        with self.popen(tar_stream(GOOD)):
            n = archive.save_repos(mock.Mock(cli="podman"), dest)
        self.assertEqual(n, 2)
        self.assertEqual((dest / "alice" / "work.git" / "HEAD").read_text(), "ref: refs/heads/main\n")

    def test_the_tar_is_read_from_the_git_servers_own_container(self):
        self.forge()
        with self.popen(tar_stream(GOOD)) as popen:
            archive.save_repos(mock.Mock(cli="podman"), self.dir / "repos")
        self.assertEqual(popen.call_args[0][0],
                         ["podman", "exec", "workshop_forge", "tar", "-C", "/data/git/repositories", "-cf", "-", "."])

    def test_a_member_that_escapes_the_folder_is_not_written(self):
        self.forge()
        evil = tar_stream({"../../escaped.txt": b"x", **GOOD})
        with self.popen(evil):
            try:
                archive.save_repos(mock.Mock(cli="podman"), self.dir / "repos")
            except StackError:
                pass
        self.assertFalse((self.dir / "escaped.txt").exists())
        self.assertFalse((self.dir.parent / "escaped.txt").exists())

    def test_tar_failing_is_a_stack_error_with_its_message(self):
        self.forge()
        with self.popen(tar_stream(GOOD), code=1, err=b"tar: /data/git/repositories: No such file"):
            with self.assertRaisesRegex(StackError, "No such file"):
                archive.save_repos(mock.Mock(cli="podman"), self.dir / "repos")

    def test_save_adds_repos_only_when_asked_and_records_the_count(self):
        self.forge()
        self.patch_data()
        plain = archive.save(mock.Mock(cli="podman"), now=1_000_000.0)
        self.assertFalse((plain / "repos").exists())
        self.assertNotIn("repos", json.loads((plain / "manifest.json").read_text()))
        with self.popen(tar_stream(GOOD)):
            d = archive.save(mock.Mock(cli="podman"), now=1_000_100.0, with_repos=True)
        self.assertEqual(json.loads((d / "manifest.json").read_text())["repos"], 2)

    def test_a_failed_copy_is_noted_and_the_rest_is_kept(self):
        self.patch_data()
        with mock.patch("dojo.stackapi.find_container", side_effect=StackError("No 'git-server' container is running")):
            d = archive.save(mock.Mock(cli="podman"), with_repos=True)
        m = json.loads((d / "manifest.json").read_text())
        self.assertIn("git-server", m["skipped"]["repos"])
        self.assertIn("roster.csv", m["saved"])


if __name__ == "__main__":
    unittest.main()
