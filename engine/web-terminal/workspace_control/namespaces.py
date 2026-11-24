"""The per-account user/pid namespace holder and the nproc prefix of every launched command.

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import os
import shlex
import subprocess
import time

from .config import BOT_PREFIX, FACILITATOR_USERNAME, TERMINAL_NPROC_LIMIT
from .state import audit, holders

def nproc_prefix(username):
    """`prlimit --nproc=N -- ` for a student's own commands, or "" (knob off,
    the facilitator or a demo bot). Goes outermost, before any `nsenter`, so
    the limit rides down (rlimits survive exec) to the process the student
    actually runs; the root-side helpers are never wrapped."""
    if TERMINAL_NPROC_LIMIT <= 0 or not uses_pid_namespace(username):
        return ""
    return f"prlimit --nproc={TERMINAL_NPROC_LIMIT} -- "


# -- A PID namespace per student (remediation T2.3b, FIND-10) -------------------
# Every account shares this container's PID namespace, so `ps` shows every
# student's command lines (tokens and passwords typed as arguments included).
# Each student's IDE and terminal instead run in a PID namespace of their own,
# with /proc remounted for it, so `ps` shows only their own processes.
#
# Root can't make one here (rootless podman gives no CAP_SYS_ADMIN), but the
# student can, inside a user namespace mapping only their own uid: the
# pattern runner-pool and AppHost already use. The kernel uid is unchanged, so
# DOJO_ISOLATION, file ownership and the SO_PEERCRED brokers see the student.
# A PID namespace ends when its first process does, so one long-lived holder
# per student keeps it (and the tmux server inside it) alive across
# connections; code-server and ttyd's shell join it with nsenter. The
# facilitator and demo bots stay outside. setuid tools (su, sudo, ping) don't
# work inside; no lab uses them. If a namespace can't be made, the workspace
# starts without one and a pidns-unavailable line is logged.
#
# The holder also caps its user namespace at zero nested user namespaces
# before dropping every capability (HOLDER_SH). A student inside can then no
# longer make one of their own (and a network namespace in it), which is the
# usual way into kernel attack surface (nf_tables and friends) from a shell
# in this container, the one that holds every lab secret. Only a process with
# CAP_SYS_RESOURCE in that namespace may raise the limit, and nothing of the
# student's in it has any. SELinux (rootful Podman on macOS) refuses the write;
# the namespace still starts, and pidns-start logs nested_userns=allowed.
# A fresh /proc mount needs the runtime's /proc masks lifted: see
# WEB_TERMINAL_SECURITY_OPT_* in docker-compose.yml.

def uses_pid_namespace(username):
    return username != FACILITATOR_USERNAME and not username.startswith(BOT_PREFIX)


def _children(pid):
    kids = []
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as f:
                ppid = int(f.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            continue
        if ppid == pid:
            kids.append(int(d))
    return kids


def _is_ns_init(pid):
    """True while pid is the first process of a PID namespace below ours
    (its NSpid line has our pid and 1)."""
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("NSpid:"):
                    return line.split()[1:] == [str(pid), "1"]
    except OSError:
        pass
    return False


HOLDER_SH = ("echo 0 > /proc/sys/user/max_user_namespaces; "
             "exec setpriv --inh-caps=-all --ambient-caps=-all --bounding-set=-all sleep infinity")


def _comm(pid):
    try:
        with open(f"/proc/{pid}/comm") as f:
            return f.read().strip()
    except OSError:
        return ""


def _nested_userns(username, init_pid):
    """"blocked" if the student's namespace allows no nested user namespace,
    else "allowed". Read from inside it, as the student: root here can't see
    that namespace's limits (they are per namespace) or the holder's environment."""
    try:
        out = subprocess.run(
            ["su", "-", username, "-c",
             f"nsenter -t {init_pid} -U -p -m --preserve-credentials -- cat /proc/sys/user/max_user_namespaces"],
            capture_output=True, text=True, timeout=5).stdout.split()
    except (OSError, subprocess.SubprocessError):
        out = []
    return "blocked" if out[-1:] == ["0"] else "allowed"


def ensure_holder(username):
    """The init pid of this student's PID namespace, starting its holder
    first if needed; None if one can't be made. Called with user_lock(username) held."""
    held = holders.get(username)
    if held and held[0].poll() is None and _is_ns_init(held[2]):
        return held[2]
    proc = subprocess.Popen(
        ["su", "-", username, "-c",
         f"exec {nproc_prefix(username)}unshare -U --map-current-user --keep-caps -p -f --mount-proc --kill-child "
         f"sh -c {shlex.quote(HOLDER_SH)}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        for unshare_pid in _children(proc.pid):
            for init_pid in _children(unshare_pid):
                # comm turns to sleep once HOLDER_SH has set the limit and dropped capabilities.
                if _is_ns_init(init_pid) and _comm(init_pid) == "sleep":
                    holders[username] = (proc, unshare_pid, init_pid)
                    audit("pidns-start", account=username, holder=init_pid,
                          nested_userns=_nested_userns(username, init_pid))
                    return init_pid
        if proc.poll() is not None:
            break
        time.sleep(0.1)
    proc.kill()
    holders.pop(username, None)
    audit("pidns-unavailable", account=username)
    return None


def ns_prefix(username):
    """`nsenter ... -- ` for this student's namespace, or "" (no namespace:
    the facilitator, a bot, or one couldn't be made). Called with user_lock(username) held."""
    if not uses_pid_namespace(username):
        return ""
    init_pid = ensure_holder(username)
    if init_pid is None:
        return ""
    return f"nsenter -t {init_pid} -U -p -m --preserve-credentials -- "
