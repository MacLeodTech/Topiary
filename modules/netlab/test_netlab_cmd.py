"""`dojo netlab check` (terminal/cmd.d/netlab): the key lookup, the request it sends, the exit codes and the output,
with netlab-checker faked by a local HTTP server."""
import contextlib
import http.server
import importlib.machinery
import importlib.util
import io
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "terminal", "cmd.d", "netlab")


def load():
    loader = importlib.machinery.SourceFileLoader("dojo_netlab_cmd", PATH)
    spec = importlib.util.spec_from_loader("dojo_netlab_cmd", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class Checker(http.server.BaseHTTPRequestHandler):
    reply = (200, {"lab": "A5", "ok": True, "assertions": []})
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Checker.seen.append((self.path, body))
        code, payload = Checker.reply
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


class NetlabCmdTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Checker)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.mod = load()
        self.mod.ADDR = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.conf = tempfile.TemporaryDirectory()
        self.addCleanup(self.conf.cleanup)
        self.mod.CONF = self.conf.name
        Checker.seen.clear()
        Checker.reply = (200, {"lab": "A5", "ok": True, "assertions": [{"name": "ping", "ok": True, "detail": "ok"}]})

    def key(self, text="k1"):
        with open(os.path.join(self.conf.name, "netlab-check-key"), "w") as f:
            f.write(text + "\n")

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch.dict(os.environ, {"NETLAB_CHECK_USER": "student03"}):
            code = self.mod.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_bad_arguments_print_usage_and_return_2(self):
        for argv in ((), ("check",), ("run", "A5")):
            self.assertEqual(self.run_main(*argv)[0], 2, argv)

    def test_missing_key_returns_2_without_asking(self):
        code, _, err = self.run_main("check", "A5")
        self.assertEqual(code, 2)
        self.assertIn("No check key", err)
        self.assertEqual(Checker.seen, [])

    def test_all_pass_returns_0_and_posts_user_key_lab(self):
        self.key()
        code, out, _ = self.run_main("check", "A5")
        self.assertEqual(code, 0)
        self.assertIn("PASS  ping: ok", out)
        self.assertIn("all checks passed", out)
        self.assertEqual(Checker.seen, [("/check", {"user": "student03", "key": "k1", "lab": "A5"})])

    def test_a_failed_assertion_returns_1(self):
        self.key()
        Checker.reply = (200, {"lab": "A5", "ok": False,
                               "assertions": [{"name": "route", "ok": False, "detail": "missing"}]})
        code, out, _ = self.run_main("check", "A5")
        self.assertEqual(code, 1)
        self.assertIn("FAIL  route: missing", out)

    def test_checker_refusal_returns_2_with_its_message(self):
        self.key()
        Checker.reply = (429, {"error": "slow down"})
        code, _, err = self.run_main("check", "A5")
        self.assertEqual(code, 2)
        self.assertIn("(429): slow down", err)

    def test_unreachable_checker_returns_2(self):
        self.key()
        import socket
        with socket.socket() as s:  # a port nobody listens on: refused at once
            s.bind(("127.0.0.1", 0))
            self.mod.ADDR = f"http://127.0.0.1:{s.getsockname()[1]}"
        code, _, err = self.run_main("check", "A5")
        self.assertEqual(code, 2)
        self.assertIn("Could not reach the checker", err)

    def test_output_is_made_printable(self):
        self.assertEqual(self.mod.clean("a\x1b[31mb\n"), "a?[31mb?")
        self.assertEqual(self.mod.clean("x" * 20, 10), "xxxxxxx...")


if __name__ == "__main__":
    unittest.main()
