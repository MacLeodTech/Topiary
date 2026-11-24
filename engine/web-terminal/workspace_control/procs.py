"""Reading the process table: who owns what, and whether an account has a live workspace.

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import os
import pwd

from .state import holders

def _proc_euids():
    """{pid: effective uid} for every process in this container, from one
    pass over /proc (what `pgrep -u` matches on), so /status checks every
    student without forking a pgrep each (REVIEW.md 2.3). Processes inside
    a student's PID namespace show here under their container pids."""
    euids = {}
    try:
        names = os.listdir("/proc")
    except OSError:
        return euids
    for name in names:
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/status") as f:
                for line in f:
                    if line.startswith("Uid:"):
                        euids[int(name)] = int(line.split()[2])
                        break
        except (OSError, ValueError, IndexError):
            continue  # exited mid-scan
    return euids


def is_alive(username, euids=None):
    """Any of this account's processes running, not counting its PID
    namespace holder (which runs for as long as the account is in use).
    `euids` is a _proc_euids() snapshot to share across many accounts."""
    try:
        uid = pwd.getpwnam(username).pw_uid
    except KeyError:
        return False
    if euids is None:
        euids = _proc_euids()
    holder = holders.get(username)
    skip = {holder[1], holder[2]} if holder else set()
    return any(u == uid and pid not in skip for pid, u in euids.items())
