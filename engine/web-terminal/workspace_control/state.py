"""The control plane's shared state (what is running, the per-account locks) and the small helpers every module uses: audit, names, ports.

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import datetime
import json
import re
import threading

from .config import (
    BOT_IDE_PORT_BASE,
    BOT_PREFIX,
    BOT_TERM_PORT_BASE,
    BOT_WATCH_PORT_BASE,
    FACILITATOR_IDE_PORT,
    FACILITATOR_TERM_PORT,
    FACILITATOR_USERNAME,
    IDE_PORT_BASE,
    TERM_PORT_BASE,
    USERNAME_RE,
    WATCH_PORT_BASE,
)

running = {}  # (tool, username) -> subprocess.Popen
running_lock = threading.Lock()
watch_target = {}  # username -> tmux session name the running watch ttyd is attached to
holders = {}  # username -> (Popen of su, unshare's pid, the namespace's init pid)
# One lock per account, held around its slow start-up (the PID namespace holder
# can take seconds) so running_lock only ever guards the dicts and one student's
# start never stalls everyone else's /start, /stop and reset. Order: an account's
# lock first, then running_lock.
user_locks = {}  # username -> threading.Lock; guarded by running_lock


def user_lock(username):
    with running_lock:
        return user_locks.setdefault(username, threading.Lock())


def audit(event, **fields):
    """One JSON line on stdout (the container log) per workspace decision,
    same shape as the allocator's (remediation T1.4, FIND-13). No secrets."""
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
           "event": event}
    rec.update(fields)
    print(json.dumps(rec, separators=(",", ":")), flush=True)


def valid_username(username):
    return bool(USERNAME_RE.match(username))


def student_number(username):
    return int(re.search(r"\d+", username).group())


def port_for(tool, username):
    if username == FACILITATOR_USERNAME:
        return FACILITATOR_IDE_PORT if tool == "ide" else FACILITATOR_TERM_PORT
    if username.startswith(BOT_PREFIX):
        return (BOT_IDE_PORT_BASE if tool == "ide" else BOT_TERM_PORT_BASE) + student_number(username)
    n = student_number(username)
    return (IDE_PORT_BASE if tool == "ide" else TERM_PORT_BASE) + n


def watch_port(username):
    if username.startswith(BOT_PREFIX):
        return BOT_WATCH_PORT_BASE + student_number(username)
    return WATCH_PORT_BASE + student_number(username)
resetting = set()  # accounts with a reset in progress; guarded by running_lock
