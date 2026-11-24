"""workspace_control/ is one package behind a thin entry script (roadmap 4.1): every module imports on its own,
the entry point only hands over to it, and no module grows back into the old 1100-line file.

Run: cd engine/web-terminal && python3 -B -m unittest discover -s tests
"""
import importlib
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
MODULES = ("config", "state", "procs", "ports", "namespaces", "sessions", "workspaces", "accounts", "reaper", "handler")


class Package(unittest.TestCase):
    def test_every_module_imports(self):
        with mock.patch.dict("os.environ", {"CONTROL_TOKEN": "test"}):
            for name in MODULES:
                importlib.import_module(f"workspace_control.{name}")

    def test_the_package_lists_exactly_these_modules(self):
        files = {p.stem for p in (HERE / "workspace_control").glob("*.py")} - {"__init__"}
        self.assertEqual(files, set(MODULES))

    def test_no_module_is_big_again(self):
        for name in MODULES:
            n = len((HERE / "workspace_control" / f"{name}.py").read_text().splitlines())
            self.assertLess(n, 300, f"{name}.py has {n} lines")

    def test_the_entry_script_only_hands_over(self):
        src = (HERE / "workspace-control.py").read_text()
        code = [l for l in src.split('"""')[2].splitlines() if l.strip()]
        self.assertEqual(code, ["from workspace_control.handler import main", 'if __name__ == "__main__":', "    main()"])

    def test_the_reaper_wraps_popen_once_the_package_is_loaded(self):
        with mock.patch.dict("os.environ", {"CONTROL_TOKEN": "test"}):
            from workspace_control import handler, reaper  # noqa: F401
        self.assertIs(subprocess.Popen, reaper._TrackedPopen)

    def test_main_is_the_handlers(self):
        with mock.patch.dict("os.environ", {"CONTROL_TOKEN": "test"}):
            from workspace_control import handler
        self.assertTrue(callable(handler.main))


if __name__ == "__main__":
    unittest.main()
