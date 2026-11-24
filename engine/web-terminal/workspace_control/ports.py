"""Listeners on the workspace port ranges, and the sweep that evicts a squatter.

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import os
import pwd
import time

from .state import audit, port_for

# Port squatting (REVIEW.md P4): every account shares this container's network
# namespace, and DOJO_ISOLATION only filters outgoing connections, so nothing
# stops a student binding another account's IDE/term/watch port before its real
# process does. The gateway would then proxy that account's traffic, cookies
# and all, to the student. So a port only counts as ready when every listener on
# it belongs to the account it serves: root for ttyd (term and watch), the
# account itself for its code-server. Anyone else's listener there is killed.
WORKSPACE_PORT_RANGES = ((9000, 9099), (9500, 9899))
SQUAT_SWEEP_S = 3


def _listeners():
    """{port: [(uid, inode)]} of every listening TCP socket in this container."""
    found = {}
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(path) as f:
                next(f)
                for line in f:
                    fields = line.split()
                    if fields[3] != "0A":  # TCP_LISTEN
                        continue
                    port = int(fields[1].rsplit(":", 1)[1], 16)
                    found.setdefault(port, []).append((int(fields[7]), fields[9]))
        except (OSError, ValueError, IndexError, StopIteration):
            continue
    return found


def _owner_allowed(port, uid):
    if uid == 0:
        return True
    try:
        return port_for("ide", pwd.getpwuid(uid).pw_name) == port
    except (KeyError, AttributeError):
        return False  # no such account, or one without a student number


def _evict(port, squatters):
    """Kill whatever holds these sockets and log who it was."""
    links = {f"socket:[{inode}]" for _uid, inode in squatters}
    pids = []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            fds = os.listdir(f"/proc/{d}/fd")
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink(f"/proc/{d}/fd/{fd}") in links:
                    pids.append(int(d))
                    break
            except OSError:
                continue
    for pid in pids:
        try:
            os.kill(pid, 9)
        except OSError:
            pass
    for uid in sorted({uid for uid, _inode in squatters}):
        try:
            account = pwd.getpwuid(uid).pw_name
        except KeyError:
            account = str(uid)
        audit("port-squat", port=port, account=account, killed=pids)


def port_open(port, listeners=None):
    """Ready to proxy: something listens on port and all of it is the right owner's."""
    held = (listeners if listeners is not None else _listeners()).get(port, [])
    squatters = [entry for entry in held if not _owner_allowed(port, entry[0])]
    if squatters:
        _evict(port, squatters)
        return False
    return bool(held)


def sweep_squatters():
    """Catch a squatter before anyone asks for its port, and one that binds
    after a workspace exits."""
    while True:
        time.sleep(SQUAT_SWEEP_S)
        listeners = _listeners()
        for port in listeners:
            if any(lo <= port <= hi for lo, hi in WORKSPACE_PORT_RANGES):
                port_open(port, listeners)
