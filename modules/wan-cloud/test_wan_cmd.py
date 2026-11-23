"""`dojo wan` (terminal/cmd.d/wan): the sub-command dispatch, exit codes and output, with the API faked."""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import unittest
from unittest import mock

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "terminal", "cmd.d", "wan")


def load():
    loader = importlib.machinery.SourceFileLoader("dojo_wan_cmd", PATH)
    spec = importlib.util.spec_from_loader("dojo_wan_cmd", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class WanCmdTest(unittest.TestCase):
    def setUp(self):
        self.wan = load()
        self.wan.TOKEN, self.wan.ORG = "tok", "org1"
        self.api = {}
        patch = mock.patch.object(self.wan, "get", side_effect=lambda p, text=False: self.api[p])
        patch.start()
        self.addCleanup(patch.stop)

    def run_main(self, *argv):
        out = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(out):
            try:
                self.wan.main(list(argv))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue()

    def test_no_arguments_prints_usage_and_succeeds(self):
        code, out = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("dojo wan <sub>", out)

    def test_unknown_subcommand_exits_2(self):
        self.assertEqual(self.run_main("bogus")[0], 2)
        self.assertEqual(self.run_main("config")[0], 2)  # needs a device

    def test_needs_a_login(self):
        self.wan.TOKEN = ""
        code, _ = self.run_main("whoami")
        self.assertEqual(code, "dojo wan: no Dojo WAN login in this shell. Open a new terminal tab.")

    def test_whoami(self):
        code, out = self.run_main("whoami")
        self.assertEqual(code, 0)
        self.assertIn("org id: org1", out)

    def test_delivery_prints_a_table(self):
        self.api["/orgs/org1/dojo/delivery"] = [{"model": "SRX320", "serial": "S1", "mac": "aa", "magic": "M"}]
        code, out = self.run_main("delivery")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0].split(), ["model", "serial", "mac", "magic"])
        self.assertEqual(out.splitlines()[1].split(), ["SRX320", "S1", "aa", "M"])

    def test_config_finds_a_device_by_name_or_mac(self):
        self.api["/orgs/org1/sites"] = [{"id": "s1"}]
        self.api["/sites/s1/devices"] = [{"id": "d1", "name": "Hub", "mac": "AA:BB"}]
        self.api["/sites/s1/devices/d1/dojo/config"] = "set system host-name hub\n"
        for wanted in ("hub", "aa:bb"):
            code, out = self.run_main("config", wanted)
            self.assertEqual((code, out), (0, "set system host-name hub\n"))

    def test_config_unknown_device_exits_1(self):
        self.api["/orgs/org1/sites"] = []
        code, out = self.run_main("config", "nope")
        self.assertEqual(code, 1)
        self.assertIn("no device named nope", out)

    def test_events_shows_the_last_15(self):
        self.api["/orgs/org1/dojo/events"] = [{"ts": i, "actor": "a", "action": "x", "path": "/p"} for i in range(20)]
        code, out = self.run_main("events")
        self.assertEqual(len(out.splitlines()), 15)
        self.assertTrue(out.startswith("5  a"))


if __name__ == "__main__":
    unittest.main()
