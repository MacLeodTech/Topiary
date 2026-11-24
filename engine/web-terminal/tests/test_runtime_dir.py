"""Per-account tmux/zellij socket directory and the watch client's TERM (S3, S5).

Run: cd engine/web-terminal && python3 -B -m unittest discover -s tests
"""
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
with mock.patch.dict("os.environ", {"CONTROL_TOKEN": "test"}):
    from workspace_control import sessions as wc


class RuntimeDir(unittest.TestCase):
    def test_sockets_live_under_the_private_dir_not_tmp(self):
        self.assertFalse(wc.TMUX_SOCKET.startswith("/tmp"))
        self.assertTrue(wc.TMUX_SOCKET.startswith(wc.RUNTIME_ROOT + "/{uid}/"))
        for d in wc.ZELLIJ_SOCKET_DIRS:
            self.assertTrue(d.startswith(wc.RUNTIME_ROOT + "/{uid}/"))

    def test_ensure_creates_0700_replacing_a_planted_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            me = os.getuid()
            with mock.patch.object(wc, "RUNTIME_ROOT", t + "/dojo"), \
                 mock.patch.object(wc.pwd, "getpwnam", return_value=mock.Mock(pw_uid=me)):
                os.makedirs(t + "/dojo")
                os.symlink("/tmp", f"{t}/dojo/{me}")
                path = wc.ensure_runtime_dir("alice")
                self.assertEqual(path, f"{t}/dojo/{me}")
                self.assertFalse(os.path.islink(path))
                self.assertEqual(os.stat(path).st_mode & 0o777, 0o700)
                self.assertEqual(os.stat(t + "/dojo").st_mode & 0o777, 0o711)

    def test_unknown_account(self):
        with mock.patch.object(wc.pwd, "getpwnam", side_effect=KeyError):
            self.assertIsNone(wc.ensure_runtime_dir("nobody-here"))


class WatchClipboard(unittest.TestCase):
    def test_tmux_watch_client_is_not_an_xterm(self):
        src = (HERE / "workspace_control" / "sessions.py").read_text()
        self.assertIn("env TERM=screen-256color tmux attach -t {session} -r", src)

    def test_shell_scripts_use_the_private_dir(self):
        self.assertIn("TMUX_TMPDIR", (HERE / "zshenv").read_text())
        self.assertIn("TMUX_TMPDIR", (HERE / "tmux-terminal.sh").read_text())


if __name__ == "__main__":
    unittest.main()
