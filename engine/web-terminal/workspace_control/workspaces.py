"""Starting and stopping one account's code-server and ttyd.

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import subprocess

from .config import (
    CODE_SERVER_EXTENSIONS_DIR,
    CODE_SERVER_NODE_FLAGS,
    TMUX_SESSION,
    ZELLIJ,
    ZELLIJ_FONT_SIZE,
    ZELLIJ_SESSION,
    ZELLIJ_TTYD_LOOK,
    code_server_lifecycle_flags,
)
from .state import audit, holders, port_for, resetting, running, running_lock, user_lock, watch_target
from .namespaces import nproc_prefix, ns_prefix
from .sessions import ensure_runtime_dir

def start_workspace(tool, username):
    key = (tool, username)
    with user_lock(username):
        with running_lock:
            proc = running.get(key)
            if proc is not None and proc.poll() is None:
                return  # already running
            if username in resetting:
                return  # the allocator fences this too; /start reports not ready

        port = port_for(tool, username)
        home = f"/home/{username}"
        ensure_runtime_dir(username)
        ns = ns_prefix(username)
        if tool == "ide":
            cmd = [
                "su", "-", username, "-c",
                f"export MALLOC_ARENA_MAX=2; "
                f"exec {nproc_prefix(username)}{ns}/usr/lib/code-server/lib/node {CODE_SERVER_NODE_FLAGS} /usr/lib/code-server "
                f"--bind-addr 0.0.0.0:{port} --auth none "
                f"--disable-telemetry --disable-update-check --disable-workspace-trust "
                f"{code_server_lifecycle_flags()} "
                f"--extensions-dir {CODE_SERVER_EXTENSIONS_DIR} {home}/lab",
            ]
        elif ZELLIJ:
            # Same reasoning as the tmux branch below: ttyd execs this per
            # websocket connection, and `attach --create` makes the session
            # (the "dojo" layout from /etc/zellij) on the first connect and
            # reattaches on every one after. cd first: the layout's panes
            # start in the directory the session is created from.
            # `su --pty`, not plain `su -c`: without it su starts the command in a
            # new session, so the browser window's later resizes (ttyd resizes
            # this pty) never reach Zellij and the layout stays at its first size.
            cmd = ["ttyd", "-p", str(port), "-W", "-t", f"fontSize={ZELLIJ_FONT_SIZE}", *ZELLIJ_TTYD_LOOK, "su", "--pty", "-", username,
                   "-c", f"cd \"$HOME/lab\" && exec {nproc_prefix(username)}{ns}zellij attach --create {ZELLIJ_SESSION}"]
        else:
            # Wrapped in tmux, not a bare login shell: ttyd execs this
            # command fresh for every websocket connection, so without
            # tmux a second connection (e.g. a facilitator's watch tile)
            # would land in its own brand-new shell instead of seeing the
            # student's actual live session. `new-session -A` creates the
            # session on the first connect and reattaches on every one
            # after, including the student's own reconnects/extra tabs.
            # Inside the student's PID namespace, like the IDE (whose VS Code
            # terminals start tmux there too), so the tmux server lives there.
            cmd = ["ttyd", "-p", str(port), "-W", "-t", "fontSize=16", "su", "-", username,
                   "-c", f"exec {nproc_prefix(username)}{ns}tmux new-session -A -s {TMUX_SESSION} -c \"$HOME/lab\""]

        with running_lock:
            if username in resetting:
                return  # a reset began while the namespace was being set up
            running[key] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    audit("workspace-start", account=username, tool=tool, port=port)


def stop_user(username):
    stale = []
    # The account's lock waits out a start in progress, so it can't spawn
    # after this and outlive the stop.
    with user_lock(username), running_lock:
        for key in list(running):
            if key[1] == username:
                stale.append(running.pop(key))
        watch_target.pop(username, None)
        holders.pop(username, None)  # pkill below ends it; the next start makes a new one
    # ttyd runs as root, so the pkill below can't reach it. Left alive it would keep
    # its port and keep execing `nsenter` against the old (now dead) PID namespace.
    for proc in stale:
        if proc.poll() is None:
            proc.kill()
    for proc in stale:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    subprocess.run(["pkill", "-KILL", "-u", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    audit("workspace-stop", account=username)
