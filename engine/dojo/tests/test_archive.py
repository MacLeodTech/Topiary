"""`dojo stop` saves the roster and every module export to results/ first (engine/dojo/archive.py)."""
import json
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


class ArchiveTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
