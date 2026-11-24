"""Reaping this container's orphans without losing the exit status of children someone is waiting on.

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import os
import subprocess
import threading
import time
import weakref

# Every Popen this process makes, by pid, so reap_children() leaves their exit
# statuses to subprocess. A blind waitpid(-1) here stole them: subprocess then
# read ECHILD as success, so a failed command looked like returncode 0.
# _tracked_lock is held across the fork and the registration, so the reaper can't
# see a child before it is registered.
_tracked = {}  # pid -> weakref to its subprocess.Popen
_tracked_lock = threading.Lock()


class _TrackedPopen(subprocess.Popen):
    def __init__(self, *args, **kwargs):
        with _tracked_lock:
            super().__init__(*args, **kwargs)
            _tracked[self.pid] = weakref.ref(self)


subprocess.Popen = _TrackedPopen  # subprocess.run() looks Popen up at call time


def _owner_popen(pid):
    """The live Popen that will reap pid itself, or None if pid is an orphan.
    Drops every entry whose Popen is gone or already reaped (its pid may have
    been reused since), so _tracked stays small. Called with _tracked_lock held."""
    for tracked_pid, ref in list(_tracked.items()):
        proc = ref()
        if proc is None or proc.returncode is not None:
            del _tracked[tracked_pid]
    ref = _tracked.get(pid)
    return ref() if ref else None


def reap_children():
    """This process is the container's PID 1 (see entrypoint.sh); nothing
    else reaps the orphans that get reparented to us, so do it ourselves to
    avoid zombie accumulation over a long-running workshop. Peek first
    (WNOWAIT): a child with a Popen is reaped through that Popen, so its exit
    status lands where subprocess.run/wait reads it."""
    while True:
        try:
            info = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOWAIT)
        except ChildProcessError:
            time.sleep(1)
            continue
        except InterruptedError:
            continue
        if info is None:
            continue
        pid = info.si_pid
        with _tracked_lock:
            proc = _owner_popen(pid)
            if proc is None:
                try:
                    os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    pass
                continue
        # Reaped into proc.returncode, or None when another thread is inside
        # proc.wait() right now and is about to reap it; don't spin meanwhile.
        # Its _tracked entry goes stale then and is dropped on the next lookup.
        if proc.poll() is None:
            time.sleep(0.05)
