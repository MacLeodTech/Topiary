"""The HTTP request handler: plumbing, identity, and GET/POST routing to views and api.
"""
import hmac
import http.server
import json
import socket
import threading
import time
import urllib.parse
from typing import Callable, NamedTuple

from accounts import LOGIN_ASSETS, read_session, SESSION_COOKIE
from allocation import forgejo_login_request, local_path, slots, _state_lock, token_index
import allocation
from api import ApiMixin
from config import (
    COOKIE_NAME, COOKIE_SECURE, FACILITATOR_USERNAME, FORGEJO_ADMIN_PASSWORD, FORGEJO_ADMIN_USER, FORGEJO_ORG,
    FORGEJO_REPO, GATEWAY_TOKEN, _short,
)
import config
from dojo_secret import forgejo_password
from pages import ADMIN_ASSETS, CSP, NO_STORE_HEADERS, page, WORKSPACE_ASSETS
from views import ViewsMixin


# How many requests each route has served since start, for the facilitator's
# /admin/api/stats (the load test, ROADMAP 2.1, counts allocator calls with it).
# Keyed "METHOD /first/two" so the table stays small whatever clients ask for.
_REQUEST_COUNTS = {}
_REQUEST_COUNTS_LOCK = threading.Lock()
_STARTED = time.time()


def count_request(method, path):
    key = f"{method} /" + "/".join(path.split("/")[1:3])
    with _REQUEST_COUNTS_LOCK:
        if key in _REQUEST_COUNTS or len(_REQUEST_COUNTS) < 100:
            _REQUEST_COUNTS[key] = _REQUEST_COUNTS.get(key, 0) + 1


def request_counts():
    with _REQUEST_COUNTS_LOCK:
        return {"since": _STARTED, "counts": dict(_REQUEST_COUNTS)}


class Handler(ViewsMixin, ApiMixin, http.server.BaseHTTPRequestHandler):
    server_version = "AllocatorHTTP/1.1"
    # Keep-alive: Caddy calls /session-check (and /auth-check for /ide and
    # /term) on every gated request, and with HTTP/1.0 each of those was a
    # new TCP connection and a new thread. A reply keeps the connection open
    # only if it has a Content-Length and the request's body was read in
    # full; anything else is sent with Connection: close (end_headers).
    protocol_version = "HTTP/1.1"
    # Per-connection socket timeout. Each connection has its own thread
    # (AllocatorServer), so a client that connects and then sends slowly or
    # not at all only holds its own thread, for at most this long per read,
    # and never delays anyone else. 3 s is plenty for any legitimate request
    # (all local; control_request/forgejo_login_request have their own
    # CONTROL_TIMEOUT). It covers the request line, headers and body.
    timeout = 3
    # How long an idle kept-alive connection waits for its next request.
    # Rule: gateway/Caddyfile's allocator_timeouts `keepalive` must stay
    # under this, so Caddy drops an idle connection before this side does
    # and never sends a request down one that is closing (a POST on such a
    # connection would get a 502; Go retries only idempotent requests).
    IDLE_TIMEOUT = 65

    def send_response(self, code, message=None):
        self._sent_length = False
        super().send_response(code, message)

    def send_header(self, keyword, value):
        if keyword.lower() == "content-length":
            self._sent_length = True
        super().send_header(keyword, value)

    def end_headers(self):
        """A reply without Content-Length, or one whose request left body bytes
        unread, closes the connection: the client could not otherwise tell
        where this reply ends, or this side where the next request starts."""
        if not getattr(self, "_sent_length", True) or self.close_connection:
            super().send_header("Connection", "close")
        super().end_headers()

    def body_unread(self, read):
        """True (and the connection is closed after this reply) when the
        request declared more body than `read` bytes, or a chunked one."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = -1
        if length != read or "Transfer-Encoding" in self.headers:
            self.close_connection = True
            return True
        return False

    def log_message(self, fmt, *args):
        pass  # keep container logs quiet; nothing sensitive is worth logging by default

    def handle_one_request(self):
        """Wait up to IDLE_TIMEOUT for the next request to start, then give it
        the short `timeout`. An audit line for any handler that crashes (the
        traceback still goes to stderr), so a broken page shows up in the
        JSON log."""
        try:
            self.connection.settimeout(self.IDLE_TIMEOUT)
            try:
                if not self.rfile.peek(1):
                    self.close_connection = True
                    return
            finally:
                self.connection.settimeout(self.timeout)
            super().handle_one_request()
        except (ConnectionError, socket.timeout):
            raise
        except Exception as exc:
            config.audit("error", method=getattr(self, "command", None),
                  path=(getattr(self, "path", "") or "").split("?", 1)[0][:200],
                  exc=type(exc).__name__, detail=_short(str(exc)))
            raise

    # -- helpers ---------------------------------------------------------
    def send_html(self, body, status=200, headers=None):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Content-Security-Policy", CSP)
        for k, v in (headers or {}):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(encoded)

    def send_asset(self, content_type, body):
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, data, status=200, headers=None):
        encoded = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        for k, v in (headers or {}):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(encoded)

    def gateway_authorized(self):
        """True only if this request carries the shared secret Caddy alone
        knows (see GATEWAY_TOKEN above) -- mirrors workspace-control.py's
        own authorized()/CONTROL_TOKEN check byte for byte. Checked first,
        in do_GET/do_POST, before any path parsing or resolve_identity()
        call: resolve_identity() trusts X-Auth-User, and this is the only
        thing standing between that trust and any other container on the
        shared workshop_lab network forging it."""
        token = self.headers.get("X-Gateway-Token", "")
        return hmac.compare_digest(token, GATEWAY_TOKEN)

    def refuse_non_facilitator(self, path):
        """403 and True for any /admin path unless the gateway named the
        facilitator. Caddy's @admin block already lets only the facilitator's
        login reach /admin*; this keeps a routing slip (a new extension route,
        a matcher change) from opening the roster, passwords or Release."""
        if not (path == "/admin" or path.startswith("/admin/")):
            return False
        if self.resolve_identity()[0] == FACILITATOR_USERNAME:
            return False
        self.send_response(403)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def get_cookie(self):
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{COOKIE_NAME}="):
                return part[len(COOKIE_NAME) + 1:]
        return None

    def resolve_identity(self, account=None):
        """Return (username_for_control_plane, student_id_or_None) for the
        current request, or (None, None) if it isn't valid.

        Facilitator identity comes from X-Auth-User. gateway/Caddyfile sets
        it on every request from the signed dojo_login cookie (session_gate:
        /session-check answers X-Session-User, copied upstream with header_up,
        which overwrites anything the client sent). gateway_authorized() has
        already proved the request came through Caddy. A student identity, by
        contrast, only ever comes from the dojo_session cookie minted when
        they claim a slot via /assign.
        """
        # `account` is the signed login cookie's owner when the caller has
        # read it itself (/auth-check does); then the header is not consulted.
        facilitator = (account == FACILITATOR_USERNAME) if account is not None \
            else self.headers.get("X-Auth-User") == FACILITATOR_USERNAME
        if facilitator:
            return FACILITATOR_USERNAME, None
        token = self.get_cookie()
        if token is None:
            return None, None
        with _state_lock:
            sid = token_index.get(token)
            if sid is not None and slots[sid]["token"] == token and slots[sid]["name"] is not None:
                return sid, sid
        return None, None

    def client_ip(self):
        # gateway/Caddyfile (allocator_timeouts) replaces X-Forwarded-For with
        # {client_ip}: the connecting address, or with GATEWAY_TRUSTED_PROXIES
        # set, the browser's address read right to left past that proxy. The
        # last entry is used so a direct, older-style "a, b" chain still keys
        # on the hop Caddy saw. Used for the login and access-code limits and
        # the roster, never for an identity decision.
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[-1].strip()
        return self.client_address[0]

    # Real form bodies here are tiny (a name, capped at 60 chars, is the
    # only field any form on this service ever submits) -- capping well
    # above that but far below "attacker-declared Content-Length" stops a
    # client from making a request thread allocate or block on reading an
    # enormous declared body.
    MAX_BODY_BYTES = 4096

    def read_body(self):
        """Read the request body, once, before do_POST routes or rejects anything.
        On a kept-alive connection unread bytes would be parsed as the next
        request; on a closing one they make the kernel send RST instead of
        FIN, which can reach the client before it reads the reply: it gets
        ConnectionResetError, not the 403/404 it was sent. A body over the cap
        still leaves bytes behind (body_unread then closes the connection); no
        real form comes near it."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        length = max(0, min(length, self.MAX_BODY_BYTES))
        body = self.rfile.read(length) if length else b""
        self.body_unread(len(body))
        return body

    def read_form_body(self):
        parsed = urllib.parse.parse_qs(self.body.decode("utf-8", errors="replace"))
        return {k: v[0] for k, v in parsed.items()}

    # -- GET routes ----------------------------------------------------
    # -- routing -----------------------------------------------------------
    def serve(self, method, routes, prefixes):
        """The one dispatcher behind do_GET and do_POST: the gateway-token check, the /admin facilitator gate, the
        forgery-guard header where a route asks for it, then the route. Exact paths only (so /x/../admin is just
        a 404), plus the few prefix routes whose tail is an id or a file name."""
        if not self.gateway_authorized():
            self.send_response(403)
            self.end_headers()
            return
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        count_request(method, path)
        if self.refuse_non_facilitator(path):
            return
        route, rest = routes.get(path), ""
        if route is None:
            for prefix, candidate in prefixes:
                if path.startswith(prefix):
                    route, rest = candidate, path[len(prefix):]
                    break
        if route is None:
            self.send_response(404)
            self.end_headers()
            return
        if route.xrw and self.headers.get("X-Requested-With") != "dojo-admin":
            # The facilitator's dojo_login cookie rides along on any same-site request (SameSite=Lax), including
            # one a page in another tab triggers. A cross-site form cannot set this header, and a cross-site
            # fetch() that tries to would need a CORS preflight this server never answers.
            self.send_response(403)
            self.end_headers()
            return
        route.fn(self, parsed, rest)

    def do_GET(self):
        self.body_unread(0)  # a GET with a body (none is ever sent) closes the connection
        self.serve("GET", GET_ROUTES, GET_PREFIXES)

    def do_POST(self):
        self.body = self.read_body()  # before any reply, even a rejection: see read_body
        self.serve("POST", POST_ROUTES, POST_PREFIXES)

    # -- GET routes ----------------------------------------------------------
    def get_login(self, parsed, rest):
        nxt = self.login_next(urllib.parse.parse_qs(parsed.query).get("next", [""])[0])
        if self.session_account():
            self.redirect(nxt)
        else:
            self.send_html(self.render_login(nxt=nxt), headers=NO_STORE_HEADERS)

    def get_login_asset(self, parsed, rest):
        asset = LOGIN_ASSETS.get(rest)
        if asset is None:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", asset[0])
        self.send_header("Content-Length", str(len(asset[1])))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(asset[1])

    def get_logout(self, parsed, rest):
        self.redirect("/login", cookies=[self.session_cookie("", 0)])

    def get_front_page(self, parsed, rest):
        username, sid = self.resolve_identity()
        if username == FACILITATOR_USERNAME:
            # /admin is the facilitator's one canonical page (own tool
            # links + roster) -- send them there instead of rendering
            # student-shaped content at "/".
            self.send_response(303)
            self.send_header("Location", "/admin")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif sid is not None:
            self.send_html(self.render_confirmation(sid), headers=NO_STORE_HEADERS)
        else:
            self.send_html(self.render_name_form())

    def get_workspace(self, parsed, rest):
        username, sid = self.resolve_identity()
        if username == FACILITATOR_USERNAME:
            # The facilitator's workspace is /admin.
            self.redirect("/admin")
        elif sid is None:
            self.redirect("/")
        else:
            self.send_html(self.render_workspace(sid), headers=NO_STORE_HEADERS)

    def get_forgejo_login(self, parsed, rest):
        # Deliberately NOT under /git/* -- Caddy's @git matcher is a
        # raw prefix match ("/git*"), so a path starting with "/git"
        # here would be routed straight to Forgejo instead of us.
        username, sid = self.resolve_identity()
        if username is None:
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if allocation.RESETS.fenced(username):
            self.send_html(page("Resetting", "<main><h1>Your environment is being reset</h1>"
                                "<p>Reload this page in a few seconds.</p></main>"),
                           status=503, headers=NO_STORE_HEADERS)
            return
        if username == FACILITATOR_USERNAME:
            forgejo_user, password = FORGEJO_ADMIN_USER, FORGEJO_ADMIN_PASSWORD
        else:
            forgejo_user, password = sid, forgejo_password(sid)
        cookies = forgejo_login_request(forgejo_user, password)
        config.audit("forgejo-login", account=username, target=forgejo_user,
              result="ok" if cookies else "failed")
        # ?next=<path>: signed in to Forgejo, go on to another page on
        # this site (a module's OIDC sign-in, say). Anything else: the repo.
        nxt = urllib.parse.parse_qs(parsed.query).get("next", [""])[0]
        self.send_response(303)
        self.send_header("Location", local_path(nxt) or f"/git/{FORGEJO_ORG}/{FORGEJO_REPO}")
        for cookie in cookies:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def get_whoami(self, parsed, rest):
        # The browser's own student ID, for pages that personalise themselves (the lab reader swaps it in for
        # "studentXX"). null for the facilitator and for a browser holding no slot.
        _, sid = self.resolve_identity()
        self.send_json({"user": sid}, headers=NO_STORE_HEADERS)

    def get_admin_page(self, parsed, rest):
        # Facilitator only: Caddy's @admin session gate, then refuse_non_facilitator().
        self.send_html(self.render_facilitator_workspace())

    def get_asset(self, parsed, rest):
        self.send_asset(*(WORKSPACE_ASSETS.get(parsed.path) or ADMIN_ASSETS[parsed.path]))

    # -- POST routes ---------------------------------------------------------
    def post_release(self, parsed, rest):
        self.handle_release(rest)

    def post_reset(self, parsed, rest):
        self.handle_reset(rest)  # the typed id rides in the body

    def post_forgejo_password(self, parsed, rest):
        self.handle_forgejo_password(rest)

    # -- front door (/login) ---------------------------------------------
    def session_cookie(self, value, max_age):
        cookie = f"{SESSION_COOKIE}={value}; HttpOnly; Path=/; SameSite=Lax; Max-Age={max_age}"
        return cookie + "; Secure" if COOKIE_SECURE else cookie

    def session_account(self):
        """The account the browser's login cookie was issued to, or None."""
        for part in self.headers.get("Cookie", "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == SESSION_COOKIE:
                return read_session(value)
        return None

    @staticmethod
    def login_next(value):
        """Where to go after signing in: a path on this site, never the login
        page itself, else the front page."""
        value = local_path(value or "")
        return value if value and not value.startswith("/login") else "/"

    def redirect(self, location, cookies=()):
        self.send_response(303)
        self.send_header("Location", location)
        for cookie in cookies:
            self.send_header("Set-Cookie", cookie)
        for k, v in NO_STORE_HEADERS:
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()


class Route(NamedTuple):
    fn: Callable
    xrw: bool = False   # needs the X-Requested-With: dojo-admin forgery guard


_H = Handler
GET_ROUTES = {
    "/admin/api/stats": Route(lambda h, p, r: h.send_json(request_counts(), headers=NO_STORE_HEADERS)),
    "/session-check": Route(lambda h, p, r: h.handle_session_check(p)),
    "/gate-fail": Route(lambda h, p, r: h.handle_gate_fail()),
    "/login": Route(_H.get_login),
    "/logout": Route(_H.get_logout),
    "/": Route(_H.get_front_page),
    "/workspace": Route(_H.get_workspace),
    "/workspace/": Route(_H.get_workspace),
    "/forgejo-login": Route(_H.get_forgejo_login),
    "/whoami": Route(_H.get_whoami),
    "/auth-check": Route(lambda h, p, r: h.handle_auth_check(p)),
    "/auth-check-watch": Route(lambda h, p, r: h.handle_auth_check_watch(p)),
    "/admin": Route(_H.get_admin_page),
    "/admin/": Route(_H.get_admin_page),
    "/admin/api/sessions": Route(lambda h, p, r: h.handle_sessions_api()),
    "/admin/api/status": Route(lambda h, p, r: h.handle_status_api()),
    **{path: Route(_H.get_asset) for path in (*WORKSPACE_ASSETS, *ADMIN_ASSETS)},
}
GET_PREFIXES = [("/login/assets/", Route(_H.get_login_asset))]
POST_ROUTES = {
    "/login": Route(lambda h, p, r: h.handle_login()),
    "/assign": Route(lambda h, p, r: h.handle_assign()),
    "/admin/release-unused": Route(lambda h, p, r: h.handle_release_unused(), xrw=True),
}
POST_PREFIXES = [
    ("/admin/release/", Route(_H.post_release, xrw=True)),
    ("/admin/reset/", Route(_H.post_reset, xrw=True)),
    ("/admin/api/forgejo-password/", Route(_H.post_forgejo_password, xrw=True)),
]
