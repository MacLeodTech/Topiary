#!/usr/bin/env python3
"""Class-scale load test (ROADMAP 2.1, P9): N signed-in demo-bot students hit the gateway the way a class does.

Needs a running stack with at least N student slots (`./dojo students 30`, then start; put dojo.toml back after):

    ./dojo git-fundamentals --terminal zellij
    python3 -B tools/loadtest.py --base http://localhost:8081 --bots 30 --tool term --seconds 60
    ./dojo stop

What it does, per simulated student, over real HTTP through the gateway (so Caddy, the allocator and web-terminal all see it):
  1. signs in with the class login at /login and claims a slot with POST /assign (the class password is read from
     the allocator container unless --password is given);
  2. burst: every bot opens /<tool>/ at the same moment (the "everyone opens VS Code" moment), then waits until its
     workspace answers 200 (not the 202 starting page);
  3. steady: every bot, every 3 s, polls the portal (GET /) and opens one page of the tool (GET /<tool>/),
     like the class page and an open editor tab do.
It prints, per request kind, the count, status histogram and p50/p95/p99/max latency, and the allocator's own
per-event counts for the run (from `podman logs`; skipped if podman is absent). Standard library only.
"""
import argparse
import http.cookiejar
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

assigned = [0]                    # simulated students signed in and holding a slot
results = defaultdict(list)       # kind -> [(seconds, status)]
lock = threading.Lock()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def record(kind, started, status):
    with lock:
        results[kind].append((time.monotonic() - started, status))


def fetch(opener, kind, url, data=None):
    started = time.monotonic()
    try:
        with opener.open(urllib.request.Request(url, data=data), timeout=30) as r:
            r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        e.read()
        status = e.code
    except Exception as e:  # noqa: BLE001 - a refused or timed-out request is a result, not a crash
        status = type(e).__name__
    record(kind, started, status)
    return status


def login(base, user, password):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)
    data = urllib.parse.urlencode({"username": user, "password": password, "next": "/"}).encode()
    if fetch(opener, "login", base + "/login", data) != 303:
        return None
    name = urllib.parse.urlencode({"name": "load " + str(id(jar) % 10000)}).encode()
    for _ in range(40):  # a new slot is rate-limited (10 at once, then 20 a minute), as for a class arriving together
        if fetch(opener, "assign", base + "/assign", name) in (200, 303):
            return opener
        time.sleep(5)
    return None


def bot(base, user, password, tool, seconds, go, ready_after):
    opener = login(base, user, password)
    if opener is None:
        return
    with lock:
        assigned[0] += 1
    go.wait()
    t0 = time.monotonic()
    while time.monotonic() < t0 + ready_after:           # burst: open the tool until the workspace answers
        if fetch(opener, f"burst /{tool}/", f"{base}/{tool}/") == 200:
            break
        time.sleep(1)
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:                   # steady polling, `seconds` after this bot's burst
        tick = time.monotonic()
        fetch(opener, "portal /", base + "/")
        fetch(opener, f"steady /{tool}/", f"{base}/{tool}/")
        time.sleep(max(0, 3 - (time.monotonic() - tick)))


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p))] if values else 0.0


def report():
    print(f"\n{'kind':<22}{'n':>7}{'p50':>9}{'p95':>9}{'p99':>9}{'max':>9}  statuses")
    for kind in sorted(results):
        secs = [s for s, _ in results[kind]]
        hist = Counter(str(st) for _, st in results[kind])
        print(f"{kind:<22}{len(secs):>7}{pct(secs, .5) * 1000:>8.0f}ms{pct(secs, .95) * 1000:>7.0f}ms"
              f"{pct(secs, .99) * 1000:>7.0f}ms{max(secs) * 1000:>7.0f}ms  {dict(hist)}")
    bad = sum(1 for rows in results.values() for _, st in rows if not isinstance(st, int) or st >= 500)
    print(f"\nrequests: {sum(len(r) for r in results.values())}   5xx or failed: {bad}")


def allocator_events(since):
    try:
        out = subprocess.run(["podman", "logs", "--since", since, "workshop_allocator"], capture_output=True,
                             text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return
    import json
    counts = Counter()
    for line in (out.stdout + out.stderr).splitlines():
        try:
            counts[json.loads(line).get("event", "?")] += 1
        except ValueError:
            pass
    print("allocator events during the run:", dict(counts.most_common()) or "(none read)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--bots", type=int, default=30)
    ap.add_argument("--tool", choices=("ide", "term"), default="term")
    ap.add_argument("--seconds", type=int, default=60, help="steady-polling time after the burst")
    ap.add_argument("--burst-wait", type=int, default=120, help="longest wait for every workspace to answer 200")
    ap.add_argument("--password", help="the class password (default: read from the allocator container)")
    ap.add_argument("--user", default="student", help="the class username")
    a = ap.parse_args()
    password = a.password
    if not password:
        try:
            env = subprocess.run(["podman", "exec", "workshop_allocator", "printenv", "TTYD_PASSWORD"],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            env = ""
        password = env or "student"
    go = threading.Event()
    threads = [threading.Thread(target=bot, daemon=True,
                                args=(a.base.rstrip("/"), a.user, password, a.tool, a.seconds, go, a.burst_wait))
               for i in range(1, a.bots + 1)]
    for t in threads:
        t.start()
    for _ in range(300):                   # sign in and claim slots first, then everyone opens the tool at once
        if assigned[0] >= a.bots:
            break
        time.sleep(1)
    go.set()
    since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    t0 = time.monotonic()
    for t in threads:
        t.join()
    print(f"{a.bots} bots, /{a.tool}/, {time.monotonic() - t0:.0f} s after the burst began")
    report()
    allocator_events(since)
    return 0


if __name__ == "__main__":
    sys.exit(main())
