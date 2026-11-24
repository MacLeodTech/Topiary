"""Environment, ports and the sizing flags. Everything else imports its settings from here.

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import json
import os
import re

IDE_PORT_BASE = 9000
TERM_PORT_BASE = 9500
FACILITATOR_IDE_PORT = 9099
FACILITATOR_TERM_PORT = 9599

# Facilitator "watch" mirror of a student's terminal -- a second, read-only
# ttyd attached to the same tmux session as their TERM_PORT_BASE one (see
# start_watch below). Not offered for the facilitator's own account, so no
# FACILITATOR_WATCH_PORT constant.
WATCH_PORT_BASE = 9600

# Separate watch port range for demo/test bots (see BOT_PREFIX above) --
# student_number() below extracts the trailing digits from a username
# regardless of its prefix, so testuser1 and student01 would otherwise both
# resolve to WATCH_PORT_BASE + 1 and collide. STUDENT_COUNT is capped at 99
# (see entrypoint.sh), so WATCH_PORT_BASE's range never reaches here.
BOT_WATCH_PORT_BASE = 9800

# Same collision, same fix, for port_for()'s IDE/term ports -- without
# these, a bot (e.g. testuser1) and a same-numbered student (student01)
# would resolve to the exact same IDE_PORT_BASE/TERM_PORT_BASE port.
BOT_IDE_PORT_BASE = 9700
BOT_TERM_PORT_BASE = 9750

# tmux session name every `term` ttyd process runs inside. Fixed and shared
# across accounts on purpose: tmux sessions are namespaced per-uid (each
# account gets its own socket under /tmp/tmux-<uid>/), so this never
# collides between students.
TMUX_SESSION = "main"

# "web" (VS Code in the browser plus a tmux terminal) or "zellij" (a Zellij
# terminal only: no code-server is ever started). Set by TERMINAL_FLAVOR in
# .env or a workshop.env; the zellij-terminal image also bakes it in.
# The Zellij session name is the same fixed "main", per-uid like tmux's.
TERMINAL_FLAVOR = os.environ.get("TERMINAL_FLAVOR", "web")
if TERMINAL_FLAVOR not in ("web", "zellij"):
    raise SystemExit(f"TERMINAL_FLAVOR must be 'web' or 'zellij', got {TERMINAL_FLAVOR!r}")
ZELLIJ = TERMINAL_FLAVOR == "zellij"
ZELLIJ_SESSION = "main"
# How the browser terminal looks in the Zellij flavor, passed to ttyd as client options: the
# One Dark palette (Zed's default terminal colours, and what Zellij's "onedark" theme, bat and
# micro are set to match), a modern monospace stack (the browser falls back to any monospace it has) and a bar cursor. The
# watch tiles get the same look without the larger font. The font is whatever good monospace
# the viewer's machine has (the browser has no internet at runtime to fetch one), in the
# order terminal apps prefer; TERMINAL_FONT_FAMILY and TERMINAL_FONT_SIZE override it.
ZELLIJ_FONT_FAMILY = os.environ.get("TERMINAL_FONT_FAMILY") or (
    "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Monaco,'Cascadia Mono','Cascadia Code',"
    "Consolas,'DejaVu Sans Mono','Liberation Mono',monospace")
ZELLIJ_FONT_SIZE = os.environ.get("TERMINAL_FONT_SIZE") or "14"
if not (ZELLIJ_FONT_SIZE.isascii() and ZELLIJ_FONT_SIZE.isdigit() and 8 <= int(ZELLIJ_FONT_SIZE) <= 40):
    raise SystemExit(f"TERMINAL_FONT_SIZE must be a whole number from 8 to 40, got {ZELLIJ_FONT_SIZE!r}")
ZELLIJ_TTYD_LOOK = [
    "-t", f"fontFamily={ZELLIJ_FONT_FAMILY}",
    "-t", "cursorStyle=bar",
    "-t", "cursorBlink=true",
    "-t", "theme=" + json.dumps({
        "background": "#282c34", "foreground": "#abb2bf", "cursor": "#528bff",
        "cursorAccent": "#282c34", "selectionBackground": "#3e4451",
        "black": "#282c34", "red": "#e06c75", "green": "#98c379", "yellow": "#e5c07b",
        "blue": "#61afef", "magenta": "#c678dd", "cyan": "#56b6c2", "white": "#abb2bf",
        "brightBlack": "#636d83", "brightRed": "#ea858b", "brightGreen": "#aad581",
        "brightYellow": "#ffd885", "brightBlue": "#73b8f1", "brightMagenta": "#d391e2",
        "brightCyan": "#6ac5d1", "brightWhite": "#c8ccd4",
    }),
]

# Must match the allocator's view of these same values -- entrypoint.sh and
# docker-compose.yml default FACILITATOR_USERNAME to "root", not
# "facilitator", and STUDENT_PREFIX/BOT_PREFIX are configurable too, so none
# of these can be hardcoded here.
FACILITATOR_USERNAME = os.environ.get("FACILITATOR_USERNAME", "root")
STUDENT_PREFIX = os.environ.get("STUDENT_PREFIX", "student")
# Demo/test bot accounts (--test, see entrypoint.sh and README.md's "Demo
# bots" section) -- a second account namespace, same numbering scheme as
# students but never competing with them for a slot. Included here so
# start/stop/status calls for a botN account validate the same way a
# studentNN one does.
BOT_PREFIX = os.environ.get("BOT_PREFIX", "testuser")

# Shared secret proving a request actually came from the allocator, not some
# other container reachable on the internal workshop_lab network (e.g. a
# workshop's own Forgejo Actions runner executing student-authored CI --
# see docker-compose.yml). Required, no default -- fail fast at startup if
# unset, same pattern as allocator/config.py's own required secrets.
CONTROL_TOKEN = os.environ["CONTROL_TOKEN"]

USERNAME_RE = re.compile(
    rf"^({re.escape(FACILITATOR_USERNAME)}|{re.escape(STUDENT_PREFIX)}\d+|{re.escape(BOT_PREFIX)}\d+)$"
)

# Shared, read-only, preinstalled-at-build-time extension set (see
# web-terminal/Dockerfile) -- no per-user copy, no runtime Marketplace
# access (this container has no route to the internet at all once the
# stack is up; see docker-compose.yml's workshop_lab network).
CODE_SERVER_EXTENSIONS_DIR = "/opt/code-server-extensions"

# V8 flags for every node process a student's code-server runs. They are
# passed on node's command line, not through NODE_OPTIONS, because
# code-server strips NODE_OPTIONS from the environment of its extension
# host, pty host and file watcher, but forks all three (and its own wrapper
# forks the server) with the parent's execArgv. Verified via
# /proc/<pid>/cmdline: the extension host, the largest process per
# student, inherits them. Language servers are forked by extensions with
# their own execArgv, so they only get MALLOC_ARENA_MAX from the
# environment.
#
#   --max-old-space-size: caps each process's heap, a safety net under the
#     container-wide mem_limit backstop (docker-compose.yml), not a
#     replacement for it. Per process, so a student's worst case is several
#     times this; see scripts/capacity-calc.sh's CEILING_PER_STUDENT_MB.
#   --max-semi-space-size=2, --optimize-for-size, MALLOC_ARENA_MAX=2: a
#     smaller young generation, V8 preferring memory over speed, and fewer
#     glibc malloc arenas. Measured together on one student (PSS, README +
#     preview, a .yaml, a .tf and the terminal open): 350 -> 316 MB for
#     --optimize-for-size on top of the other two, with every capped
#     process smaller. Costs a little CPU, which lab-sized files don't
#     notice.
#
# Override the cap via env if a workshop's files/extensions genuinely need
# more headroom.
CODE_SERVER_MAX_HEAP_MB = os.environ.get("CODE_SERVER_MAX_HEAP_MB", "384")
if not (CODE_SERVER_MAX_HEAP_MB.isascii() and CODE_SERVER_MAX_HEAP_MB.isdigit()):
    # Interpolated into a shell command below, same as _seconds_env's values.
    raise SystemExit(f"CODE_SERVER_MAX_HEAP_MB must be a whole number of MB, got {CODE_SERVER_MAX_HEAP_MB!r}")
CODE_SERVER_NODE_FLAGS = (
    f"--max-old-space-size={CODE_SERVER_MAX_HEAP_MB} --max-semi-space-size=2 --optimize-for-size"
)

# A tripwire against a fork bomb, not a budget: RLIMIT_NPROC per student uid
# (each student has their own uid), applied with prlimit to everything that
# starts as the student. Threads count against it, hence the high default:
# code-server, language servers, builds and test suites must never notice.
# 0 turns it off. Residual: no per-user memory cap (that needs per-user
# cgroups; the container's mem_limit stays one shared pool).
TERMINAL_NPROC_LIMIT = os.environ.get("TERMINAL_NPROC_LIMIT", "1024")
if not (TERMINAL_NPROC_LIMIT.isascii() and TERMINAL_NPROC_LIMIT.isdigit()):
    # Interpolated into a shell command below.
    raise SystemExit(f"TERMINAL_NPROC_LIMIT must be a whole number (0 = off), got {TERMINAL_NPROC_LIMIT!r}")
TERMINAL_NPROC_LIMIT = int(TERMINAL_NPROC_LIMIT)


def _seconds_env(name, default, floor=None):
    """Non-negative integer seconds from the environment. Interpolated into
    a shell command below, so anything but plain digits fails fast at
    startup instead of being passed through. With `floor`, a non-zero value
    must also be greater than it (0 still means "off")."""
    raw = os.environ.get(name, default)
    if not (raw.isascii() and raw.isdigit()):
        raise SystemExit(f"{name} must be a non-negative integer number of seconds, got {raw!r}")
    value = int(raw)
    if floor is not None and 0 < value <= floor:
        raise SystemExit(f"{name} must be 0 (off) or greater than {floor} seconds, got {value}")
    return value


# What a code-server keeps holding once its browser tab is gone. Measured
# with both bundled language servers active, one student is ~550 MB (PSS)
# before f977209's extension trim and node flags, ~260 MB after, and by
# default a disconnected client's extension host and language servers
# linger for 3 HOURS (VS Code's own reconnection grace time), so a closed
# tab quietly keeps most of that (~330 MB before, ~200 MB after) until then. Two independent
# timers, both counted from the tab closing (an open tab keeps both from
# firing, however idle the student is):
#
#   - RECONNECTION_GRACE: after this long disconnected, the extension host,
#     language servers, and pty host are killed (~200 MB back per student).
#     The code-server process itself stays. A client reconnecting after
#     this is told to reload its window instead of resuming in place.
#   - IDLE_TIMEOUT: after this long with no client at all, the whole
#     code-server exits (code-server judges "no client" from a heartbeat
#     that can be up to ~1 minute stale, so expect up to that much extra). Nothing is lost by it: the next /ide request goes
#     through the allocator's forward_auth -> POST /start/ide/<user> ->
#     start_workspace() below, which sees the dead process and starts a
#     fresh one, and terminals are tmux sessions owned by the student's own
#     uid, so they outlive it.
#
# Keep GRACE below IDLE_TIMEOUT or the idle exit fires first and the
# shorter grace is moot. 0 turns a timer off (VS Code's 3 h grace / no idle
# exit). Neither changes memory while students are actually connected --
# that's what CODE_SERVER_MAX_HEAP_MB and the container limit are for.
# code-server itself refuses --idle-timeout-seconds of 60 or less and would exit at once, with its output discarded
# (start_workspace below), so a too-small value is rejected here at startup instead of failing every /ide.
CODE_SERVER_IDLE_TIMEOUT_SECONDS = _seconds_env("CODE_SERVER_IDLE_TIMEOUT_SECONDS", "900", floor=60)
CODE_SERVER_RECONNECTION_GRACE_SECONDS = _seconds_env("CODE_SERVER_RECONNECTION_GRACE_SECONDS", "300")


def code_server_lifecycle_flags():
    flags = []
    if CODE_SERVER_RECONNECTION_GRACE_SECONDS:
        flags.append(f"--reconnection-grace-time {CODE_SERVER_RECONNECTION_GRACE_SECONDS}")
    if CODE_SERVER_IDLE_TIMEOUT_SECONDS:
        flags.append(f"--idle-timeout-seconds {CODE_SERVER_IDLE_TIMEOUT_SECONDS}")
    return " ".join(flags)
