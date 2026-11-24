"""tmux/zellij sessions, the runtime directory they live in, and the facilitator's watch ttyd.

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import os
import pwd
import socket
import subprocess
import time

from .config import ZELLIJ, ZELLIJ_TTYD_LOOK
from .state import audit, resetting, running, running_lock, watch_port, watch_target
from .ports import port_open

def _socket_listening(path):
    """A server is accepting on this Unix socket (not just a stale file
    left by one that was killed). Connects and hangs up at once, the same
    liveness probe `tmux`/`zellij list-sessions` make."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(0.2)
    try:
        s.connect(path)
        return True
    except OSError:
        return False
    finally:
        s.close()


# Per-account runtime directory for the terminal server's socket. /tmp is one
# tmpfs shared by every student, so a socket directory there could be
# pre-created by another student (`mkdir /tmp/tmux-<victim uid>`) to deny the
# victim a terminal or plant a socket that fools has_terminal_session. Under
# /run/dojo (0711, root-owned, so no student can create entries) each account
# gets a 0700 directory of its own, handed out by root before any session
# starts. /etc/zsh/zshenv (the zshenv file beside this script) exports
# TMUX_TMPDIR / ZELLIJ_SOCKET_DIR pointing at it for every shell the account runs.
RUNTIME_ROOT = "/run/dojo"
TMUX_SOCKET = RUNTIME_ROOT + "/{uid}/tmux-{uid}/default"
ZELLIJ_SOCKET_DIRS = (RUNTIME_ROOT + "/{uid}/zellij",)


def ensure_runtime_dir(username):
    """Create (or repair) the account's 0700 runtime directory; returns its
    path or None for an unknown account. Idempotent; root only."""
    try:
        uid = pwd.getpwnam(username).pw_uid
    except KeyError:
        return None
    os.makedirs(RUNTIME_ROOT, mode=0o711, exist_ok=True)
    os.chmod(RUNTIME_ROOT, 0o711)
    path = f"{RUNTIME_ROOT}/{uid}"
    if os.path.islink(path) or (os.path.exists(path) and not os.path.isdir(path)):
        os.unlink(path)
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chown(path, uid, -1)
    os.chmod(path, 0o700)
    return path


def has_terminal_session(username):
    """Cheap stand-in for `most_active_session(username) is not None`, for
    the roster poll: no `su` fork, just the account's terminal server
    socket. tmux keeps one server per uid at <runtime dir>/tmux-<uid>/default
    (the PID namespace doesn't change the uid), and that server exits
    with its last session, so a live socket means at least one session.
    Zellij has one socket per running session under
    <runtime dir>/zellij/<contract-version>/."""
    try:
        uid = pwd.getpwnam(username).pw_uid
    except KeyError:
        return False
    if not ZELLIJ:
        return _socket_listening(TMUX_SOCKET.format(uid=uid))
    for top in (d.format(uid=uid) for d in ZELLIJ_SOCKET_DIRS):
        try:
            versions = [e.path for e in os.scandir(top) if e.is_dir(follow_symlinks=False)]
        except OSError:
            continue
        for d in versions:
            try:
                socks = [e.path for e in os.scandir(d)
                         if not e.is_dir(follow_symlinks=False) and not e.is_file(follow_symlinks=False)]
            except OSError:
                continue
            if any(_socket_listening(p) for p in socks):
                return True
    return False
    # Doesn't wait for the port to open -- the caller (do_POST's /start
    # handler) reports actual readiness back via port_open() right after
    # this returns, and the allocator's /auth-check uses that to decide
    # whether to proxy or show a starting page, so nothing here needs to
    # block on the spawn finishing.


def list_sessions(username):
    """This student's tmux sessions as (name, last_activity_unix_ts) pairs
    -- `main` from the standalone Terminal tool, plus one `vscode-<pid>`
    per VS Code terminal (task, split, or extra tab; see
    tmux-terminal.sh). Empty if the account has never opened a terminal at
    all.

    The Zellij flavor has the one `main` session per student and Zellij
    reports no activity time, so each live session counts as active now."""
    ensure_runtime_dir(username)
    if ZELLIJ:
        result = subprocess.run(
            ["su", "-", username, "-c", "zellij list-sessions --short"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return []
        now = int(time.time())
        return [(name, now) for name in result.stdout.split()]
    result = subprocess.run(
        ["su", "-", username, "-c", "tmux list-sessions -F '#{session_name} #{session_activity}'"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    sessions = []
    for line in result.stdout.splitlines():
        name, _, activity = line.rpartition(" ")
        if name and activity.isdigit():
            sessions.append((name, int(activity)))
    return sessions


def most_active_session(username):
    """Whichever of this student's tmux sessions the student is actually
    using right now, regardless of which tool (VS Code or the standalone
    Terminal button) it came from -- gates and targets start_watch. None
    if the account has never opened a terminal (nothing to attach to)."""
    sessions = list_sessions(username)
    if not sessions:
        return None
    return max(sessions, key=lambda s: s[1])[0]


def start_watch(username):
    """Read-only mirror of whichever of the student's tmux sessions was
    most recently active, for a facilitator to watch live. Deliberately no
    -W (ttyd itself won't relay keystrokes) and `tmux attach -r` (tmux also
    marks this client read-only) -- belt and suspenders against a
    facilitator tile accidentally typing into a student's shell. Returns
    False if there's nothing to watch yet.

    Re-evaluates the most-active session on every call (i.e. every time a
    facilitator (re)opens the watch tile -- see allocator/api.py's
    /auth-check-watch) and restarts the mirror if the student has since
    switched to a different terminal. This does not follow a switch that
    happens while the tile is already open and connected -- reopen it to
    re-target."""
    if username in resetting:
        return False
    session = most_active_session(username)
    if session is None:
        return False

    with running_lock:
        key = ("watch", username)
        proc = running.get(key)
        if proc is not None and proc.poll() is None and watch_target.get(username) == session:
            return True  # already watching the right session
        if proc is not None and proc.poll() is None:
            # Student switched terminals -- retarget. Wait for the old
            # ttyd to actually release the port before spawning its
            # replacement on the same one, or a request that lands in
            # between can hit a dead socket (502) while the old process
            # is still tearing down.
            proc.kill()
            proc.wait()

        port = watch_port(username)
        # `zellij watch` is Zellij's own read-only client, the equivalent of
        # `tmux attach -r`; ttyd still has no -W.
        # The tmux watch client gets TERM=screen-256color: set-clipboard (on, for
        # the student's own browser) only forwards a pane's OSC 52 to clients whose
        # terminal has the clipboard feature, which tmux gives xterm* terminals by
        # default and screen* ones not. So a student's OSC 52 escape never reaches
        # the facilitator's clipboard through the tile.
        watch_cmd = f"zellij watch {session}" if ZELLIJ else f"env TERM=screen-256color tmux attach -t {session} -r"
        ensure_runtime_dir(username)
        su_cmd = ["su", "--pty"] if ZELLIJ else ["su"]  # --pty relays tile resizes to zellij watch
        cmd = ["ttyd", "-p", str(port), *(ZELLIJ_TTYD_LOOK if ZELLIJ else []), *su_cmd, "-", username, "-c", watch_cmd]
        running[key] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        watch_target[username] = session
    audit("watch-start", target=username, session=session, port=port)

    for _ in range(50):
        if port_open(port):
            break
        time.sleep(0.1)
    return True
