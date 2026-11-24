"""The allocator's route table (E11): the status every (method, path) gives an anonymous request, a class login,
the facilitator, and the facilitator with the forgery-guard header. Written before the table replaced the
if-chains in handler.py; the refactor had to leave EXPECTED unchanged. Run from engine/allocator:

  python3 -B -m unittest tests.test_routes -v
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tests.test_handlers import FAC, HandlerTest  # noqa: E402
import handler  # noqa: E402

ROLES = {
    "anon": {},
    "class": {"X-Auth-User": "student"},
    "fac": {"X-Auth-User": FAC},
    "fac+xrw": {"X-Auth-User": FAC, "X-Requested-With": "dojo-admin"},
}
PATHS = {
    "GET": ["/admin/api/stats", "/session-check", "/gate-fail", "/login", "/login?next=/term", "/login/assets/nope",
            "/logout", "/", "/workspace", "/workspace/", "/forgejo-login", "/whoami", "/auth-check",
            "/auth-check-watch", "/admin", "/admin/", "/admin/api/sessions", "/admin/api/status", "/nope",
            "/admin/nope", "/x/../admin", "/session-check/", "/login/"],
    "POST": ["/login", "/assign", "/admin/release/student01", "/admin/reset/student01",
             "/admin/api/forgejo-password/student01", "/admin/release-unused", "/nope", "/admin/nope",
             "/admin/release", "/session-check"],
}
EXPECTED = {
    'GET /admin/api/stats anon': 403,
    'GET /admin/api/stats class': 403,
    'GET /admin/api/stats fac': 200,
    'GET /admin/api/stats fac+xrw': 200,
    'GET /session-check anon': 401,
    'GET /session-check class': 401,
    'GET /session-check fac': 401,
    'GET /session-check fac+xrw': 401,
    'GET /gate-fail anon': 401,
    'GET /gate-fail class': 401,
    'GET /gate-fail fac': 401,
    'GET /gate-fail fac+xrw': 401,
    'GET /login anon': 200,
    'GET /login class': 200,
    'GET /login fac': 200,
    'GET /login fac+xrw': 200,
    'GET /login?next=/term anon': 200,
    'GET /login?next=/term class': 200,
    'GET /login?next=/term fac': 200,
    'GET /login?next=/term fac+xrw': 200,
    'GET /login/assets/nope anon': 404,
    'GET /login/assets/nope class': 404,
    'GET /login/assets/nope fac': 404,
    'GET /login/assets/nope fac+xrw': 404,
    'GET /logout anon': 303,
    'GET /logout class': 303,
    'GET /logout fac': 303,
    'GET /logout fac+xrw': 303,
    'GET / anon': 200,
    'GET / class': 200,
    'GET / fac': 303,
    'GET / fac+xrw': 303,
    'GET /workspace anon': 303,
    'GET /workspace class': 303,
    'GET /workspace fac': 303,
    'GET /workspace fac+xrw': 303,
    'GET /workspace/ anon': 303,
    'GET /workspace/ class': 303,
    'GET /workspace/ fac': 303,
    'GET /workspace/ fac+xrw': 303,
    'GET /forgejo-login anon': 303,
    'GET /forgejo-login class': 303,
    'GET /forgejo-login fac': 303,
    'GET /forgejo-login fac+xrw': 303,
    'GET /whoami anon': 200,
    'GET /whoami class': 200,
    'GET /whoami fac': 200,
    'GET /whoami fac+xrw': 200,
    'GET /auth-check anon': 400,
    'GET /auth-check class': 400,
    'GET /auth-check fac': 400,
    'GET /auth-check fac+xrw': 400,
    'GET /auth-check-watch anon': 403,
    'GET /auth-check-watch class': 403,
    'GET /auth-check-watch fac': 404,
    'GET /auth-check-watch fac+xrw': 404,
    'GET /admin anon': 403,
    'GET /admin class': 403,
    'GET /admin fac': 200,
    'GET /admin fac+xrw': 200,
    'GET /admin/ anon': 403,
    'GET /admin/ class': 403,
    'GET /admin/ fac': 200,
    'GET /admin/ fac+xrw': 200,
    'GET /admin/api/sessions anon': 403,
    'GET /admin/api/sessions class': 403,
    'GET /admin/api/sessions fac': 200,
    'GET /admin/api/sessions fac+xrw': 200,
    'GET /admin/api/status anon': 403,
    'GET /admin/api/status class': 403,
    'GET /admin/api/status fac': 200,
    'GET /admin/api/status fac+xrw': 200,
    'GET /nope anon': 404,
    'GET /nope class': 404,
    'GET /nope fac': 404,
    'GET /nope fac+xrw': 404,
    'GET /admin/nope anon': 403,
    'GET /admin/nope class': 403,
    'GET /admin/nope fac': 404,
    'GET /admin/nope fac+xrw': 404,
    'GET /x/../admin anon': 404,
    'GET /x/../admin class': 404,
    'GET /x/../admin fac': 404,
    'GET /x/../admin fac+xrw': 404,
    'GET /session-check/ anon': 404,
    'GET /session-check/ class': 404,
    'GET /session-check/ fac': 404,
    'GET /session-check/ fac+xrw': 404,
    'GET /login/ anon': 404,
    'GET /login/ class': 404,
    'GET /login/ fac': 404,
    'GET /login/ fac+xrw': 404,
    'GET /admin/admin.css anon': 403,
    'GET /admin/admin.css class': 403,
    'GET /admin/admin.css fac': 200,
    'GET /admin/admin.css fac+xrw': 200,
    'GET /admin/admin.js anon': 403,
    'GET /admin/admin.js class': 403,
    'GET /admin/admin.js fac': 200,
    'GET /admin/admin.js fac+xrw': 200,
    'GET /login/assets/favicon.png anon': 200,
    'GET /login/assets/favicon.png class': 200,
    'GET /login/assets/favicon.png fac': 200,
    'GET /login/assets/favicon.png fac+xrw': 200,
    'GET /login/assets/login.css anon': 200,
    'GET /login/assets/login.css class': 200,
    'GET /login/assets/login.css fac': 200,
    'GET /login/assets/login.css fac+xrw': 200,
    'GET /login/assets/login.js anon': 200,
    'GET /login/assets/login.js class': 200,
    'GET /login/assets/login.js fac': 200,
    'GET /login/assets/login.js fac+xrw': 200,
    'GET /login/assets/logo-dark.png anon': 200,
    'GET /login/assets/logo-dark.png class': 200,
    'GET /login/assets/logo-dark.png fac': 200,
    'GET /login/assets/logo-dark.png fac+xrw': 200,
    'GET /login/assets/logo-light.png anon': 200,
    'GET /login/assets/logo-light.png class': 200,
    'GET /login/assets/logo-light.png fac': 200,
    'GET /login/assets/logo-light.png fac+xrw': 200,
    'GET /workspace/extra.js anon': 200,
    'GET /workspace/extra.js class': 200,
    'GET /workspace/extra.js fac': 200,
    'GET /workspace/extra.js fac+xrw': 200,
    'GET /workspace/mode.js anon': 200,
    'GET /workspace/mode.js class': 200,
    'GET /workspace/mode.js fac': 200,
    'GET /workspace/mode.js fac+xrw': 200,
    'GET /workspace/workspace.css anon': 200,
    'GET /workspace/workspace.css class': 200,
    'GET /workspace/workspace.css fac': 200,
    'GET /workspace/workspace.css fac+xrw': 200,
    'GET /workspace/workspace.js anon': 200,
    'GET /workspace/workspace.js class': 200,
    'GET /workspace/workspace.js fac': 200,
    'GET /workspace/workspace.js fac+xrw': 200,
    'POST /login anon': 401,
    'POST /login class': 401,
    'POST /login fac': 401,
    'POST /login fac+xrw': 401,
    'POST /assign anon': 303,
    'POST /assign class': 303,
    'POST /assign fac': 200,
    'POST /assign fac+xrw': 200,
    'POST /admin/release/student01 anon': 403,
    'POST /admin/release/student01 class': 403,
    'POST /admin/release/student01 fac': 403,
    'POST /admin/release/student01 fac+xrw': 200,
    'POST /admin/reset/student01 anon': 403,
    'POST /admin/reset/student01 class': 403,
    'POST /admin/reset/student01 fac': 403,
    'POST /admin/reset/student01 fac+xrw': 400,
    'POST /admin/api/forgejo-password/student01 anon': 403,
    'POST /admin/api/forgejo-password/student01 class': 403,
    'POST /admin/api/forgejo-password/student01 fac': 403,
    'POST /admin/api/forgejo-password/student01 fac+xrw': 200,
    'POST /admin/release-unused anon': 403,
    'POST /admin/release-unused class': 403,
    'POST /admin/release-unused fac': 403,
    'POST /admin/release-unused fac+xrw': 200,
    'POST /nope anon': 404,
    'POST /nope class': 404,
    'POST /nope fac': 404,
    'POST /nope fac+xrw': 404,
    'POST /admin/nope anon': 403,
    'POST /admin/nope class': 403,
    'POST /admin/nope fac': 404,
    'POST /admin/nope fac+xrw': 404,
    'POST /admin/release anon': 403,
    'POST /admin/release class': 403,
    'POST /admin/release fac': 404,
    'POST /admin/release fac+xrw': 404,
    'POST /session-check anon': 404,
    'POST /session-check class': 404,
    'POST /session-check fac': 404,
    'POST /session-check fac+xrw': 404,
}


def asset_paths():
    return sorted(set(handler.WORKSPACE_ASSETS) | set(handler.ADMIN_ASSETS)
                  | {f"/login/assets/{k}" for k in handler.LOGIN_ASSETS})


class RouteTable(HandlerTest):
    def observe(self):
        out = {}
        with mock.patch.object(handler, "forgejo_login_request", return_value=[]):
            for method, paths in PATHS.items():
                for path in paths + (asset_paths() if method == "GET" else []):
                    for role, hdr in ROLES.items():
                        body = "name=Ada" if method == "POST" else None
                        out[f"{method} {path} {role}"] = self.request(method, path, body=body, headers=hdr)[0]
        return out

    def test_every_route_answers_as_before(self):
        got = self.observe()
        if os.environ.get("DUMP_ROUTES"):
            for k, v in got.items():
                print(f"    {k!r}: {v},")
        self.assertEqual(got, EXPECTED)

    def test_no_gateway_token_is_403_everywhere(self):
        for method, path in (("GET", "/login"), ("GET", "/nope"), ("POST", "/login"), ("POST", "/nope")):
            self.assertEqual(self.request(method, path, body="x=1" if method == "POST" else None,
                                          gateway=False)[0], 403, (method, path))


if __name__ == "__main__":
    unittest.main()
