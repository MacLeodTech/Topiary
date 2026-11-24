"""The HTTP handler (the control port) and main().

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import hmac
import http.server
import json
import shutil
import threading
import urllib.parse

from .config import CONTROL_TOKEN, FACILITATOR_USERNAME, TERMINAL_FLAVOR, TERMINAL_NPROC_LIMIT, ZELLIJ
from .state import port_for, valid_username
from .procs import _proc_euids, is_alive
from .ports import port_open, sweep_squatters
from .sessions import has_terminal_session, start_watch
from .workspaces import start_workspace, stop_user
from .accounts import reset_user
from .reaper import reap_children

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "WorkspaceControl/1.0"

    def log_message(self, fmt, *args):
        pass

    def send_json_ok(self, data=None):
        body = json.dumps(data or {}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        token = self.headers.get("X-Control-Token", "")
        return hmac.compare_digest(token, CONTROL_TOKEN)

    def do_GET(self):
        if not self.authorized():
            self.send_response(403)
            self.end_headers()
            return
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/status":
            qs = urllib.parse.parse_qs(parsed.query)
            users = (qs.get("users") or [""])[0].split(",")
            # "watchable" mirrors start_watch's own readiness check
            # (most_active_session != None) without the side effect of
            # actually spawning a watch ttyd -- the roster poll uses it to
            # know when a freshly-joined student's tile can connect its
            # iframe on its own, instead of waiting for a manual reload.
            # One /proc pass and one socket probe per account, no forks
            # (REVIEW.md 2.3): this runs every few seconds while the
            # roster is open.
            euids = _proc_euids()
            result = {
                u: {"active": is_alive(u, euids), "watchable": has_terminal_session(u)}
                for u in users if u and valid_username(u)
            }
            self.send_json_ok(result)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if not self.authorized():
            self.send_response(403)
            self.end_headers()
            return
        parsed = urllib.parse.urlsplit(self.path)
        parts = parsed.path.strip("/").split("/")

        if len(parts) == 3 and parts[0] == "start":
            _, tool, username = parts
            if tool not in ("ide", "term", "watch") or not valid_username(username):
                self.send_response(400)
                self.end_headers()
                return
            if tool == "ide" and ZELLIJ:
                self.send_response(404)  # this flavor has no IDE; code-server is never started
                self.end_headers()
                return
            if tool == "watch":
                # No facilitator self-watch -- watch_port()/student_number()
                # assume a studentNN account, and it wouldn't mean anything
                # anyway.
                if username == FACILITATOR_USERNAME:
                    self.send_response(400)
                    self.end_headers()
                    return
                if not start_watch(username):
                    self.send_response(409)  # no term session for this student yet
                    self.end_headers()
                    return
                self.send_json_ok()
            else:
                start_workspace(tool, username)
                # Reported straight back to the allocator's /auth-check,
                # which proxies once this is true and shows a starting page
                # (that reloads itself) otherwise -- see allocator/api.py's
                # handle_auth_check. Checked fresh every call (not just
                # right after a spawn) since this same endpoint is hit on
                # every /ide or /term request, not only the first.
                self.send_json_ok({"ready": port_open(port_for(tool, username))})
            return

        if len(parts) == 2 and parts[0] == "reset":
            # Synchronous; the allocator's reset worker waits for it with its
            # own long timeout. Never the facilitator's account.
            username = parts[1]
            if not valid_username(username) or username == FACILITATOR_USERNAME:
                self.send_response(400)
                self.end_headers()
                return
            result = reset_user(username)
            if result is None:
                self.send_response(409)  # already being reset
                self.end_headers()
                return
            ok, steps = result
            self.send_json_ok({"ok": ok, "steps": steps})
            return

        if len(parts) == 2 and parts[0] == "stop":
            username = parts[1]
            if not valid_username(username):
                self.send_response(400)
                self.end_headers()
                return
            stop_user(username)
            self.send_json_ok()
            return

        self.send_response(404)
        self.end_headers()


def main():
    if ZELLIJ and shutil.which("zellij") is None:
        raise SystemExit("TERMINAL_FLAVOR=zellij but this image has no zellij: build the "
                         "zellij-terminal image (dojo does when the flavor is set).")
    print(f"terminal flavor: {TERMINAL_FLAVOR}", flush=True)
    threading.Thread(target=reap_children, daemon=True).start()
    threading.Thread(target=sweep_squatters, daemon=True).start()
    print(f"per-student process limit (RLIMIT_NPROC): "
          f"{TERMINAL_NPROC_LIMIT or 'off'}", flush=True)
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 7682), Handler)
    server.serve_forever()
