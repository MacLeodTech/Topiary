"""Student reset: account hooks, removing an account's files, the reset itself.

Part of workspace-control (see workspace-control.py); moved from one file, code unchanged."""

import os
import pwd
import shutil
import subprocess

from .state import audit, resetting, running_lock
from .workspaces import stop_user

# -- Student reset (docs/archive/STUDENT-RESET-PLAN.md §4.2 step 5) -------------
# The allocator resets the student's Forgejo account first, then calls
# POST /reset/<user>: run the reset.d hooks, remove the home and the
# student's files in the shared temp directories, provision the account again
# as start-up does (provision-account.sh, which also signs git in to the new
# Forgejo account), then run the account.d hooks. Every step is idempotent, so
# a failed reset is retried by running it again.
RESET_MARK_DIR = "/run/dojo-reset"  # bot-supervisor.sh leaves a marked bot alone
HOOK_DIRS = {"reset": "/etc/dojo/reset.d", "account": "/etc/dojo/account.d"}
HOOK_TIMEOUT = 60
PROVISION_TIMEOUT = 120  # provision-account.sh waits up to 60 s for Forgejo
TEMP_DIRS = ("/tmp", "/var/tmp", "/dev/shm")
# Where cron keeps each account's crontab (Debian's cron; busybox crond uses the same path). A
# student's job (cert-autorenewal's Lab 4 renewal) would otherwise keep running after a reset.
CRON_SPOOLS = ("/var/spool/cron/crontabs",)


def _last_line(text):
    lines = [line for line in (text or "").strip().splitlines() if line.strip()]
    return lines[-1][:200] if lines else ""


def _run_step(step_id, cmd, timeout):
    """Run cmd and report it. The exit code comes from a wrapping sh, which
    prints it last: reap_children() may reap our direct child first, and
    subprocess then reports 0 whatever happened."""
    wrapped = ["sh", "-c", '"$@"; echo "dojo-exit=$?"', "sh", *cmd]
    try:
        out = subprocess.run(wrapped, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"id": step_id, "ok": False, "detail": f"timed out after {timeout} s"}
    except OSError as exc:
        return {"id": step_id, "ok": False, "detail": str(exc)[:200]}
    lines = out.stdout.rstrip("\n").split("\n")
    code = lines[-1][len("dojo-exit="):] if lines[-1].startswith("dojo-exit=") else ""
    stdout = "\n".join(lines[:-1]) if code else out.stdout
    detail = _last_line(out.stderr) or _last_line(stdout)
    return {"id": step_id, "ok": code == "0", "detail": detail}


def run_account_hooks(kind, username):
    """One result per /etc/dojo/<kind>.d/*.sh, run in name order with the
    account as its only argument. A failed hook doesn't stop the others."""
    hook_dir = HOOK_DIRS[kind]
    try:
        names = sorted(n for n in os.listdir(hook_dir) if n.endswith(".sh"))
    except FileNotFoundError:
        return []
    return [_run_step(f"{kind}.d/{n}", ["sh", os.path.join(hook_dir, n), username], HOOK_TIMEOUT)
            for n in names if os.path.isfile(os.path.join(hook_dir, n))]


def remove_account_files(username):
    """The home, the account's crontab, and whatever it owns at the top of
    the shared temp directories (tmux sockets, vault lab 6's /dev/shm files).
    rmtree never follows symlinks, and the student's processes are already
    gone."""
    uid = pwd.getpwnam(username).pw_uid
    removed = 0
    if os.path.lexists(f"/home/{username}"):
        shutil.rmtree(f"/home/{username}")
        removed += 1
    for spool in CRON_SPOOLS:
        tab = os.path.join(spool, username)
        if os.path.isfile(tab) and not os.path.islink(tab):
            os.unlink(tab)
            os.utime(spool)     # cron re-reads the spool when its mtime changes
            removed += 1
    for top in TEMP_DIRS:
        try:
            entries = list(os.scandir(top))
        except FileNotFoundError:
            continue
        for entry in entries:
            try:
                if entry.stat(follow_symlinks=False).st_uid != uid:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    shutil.rmtree(entry.path)
                else:
                    os.unlink(entry.path)
                removed += 1
            except FileNotFoundError:
                pass
    return removed


def reset_user(username):
    """Steps 5 of a reset for one student or bot. Returns (ok, steps), or
    None when a reset of this account is already running."""
    with running_lock:
        if username in resetting:
            return None
        resetting.add(username)
    os.makedirs(RESET_MARK_DIR, mode=0o700, exist_ok=True)
    mark = os.path.join(RESET_MARK_DIR, username)
    open(mark, "w").close()
    audit("reset-start", account=username)
    steps = []
    try:
        stop_user(username)
        steps += run_account_hooks("reset", username)
        stop_user(username)  # anything a hook or the bot supervisor started meanwhile
        try:
            steps.append({"id": "files", "ok": True,
                          "detail": f"{remove_account_files(username)} removed"})
        except OSError as exc:
            steps.append({"id": "files", "ok": False, "detail": str(exc)[:200]})
        steps.append(_run_step("provision", ["/usr/local/lib/dojo/provision-account.sh", username],
                               PROVISION_TIMEOUT))
        steps += run_account_hooks("account", username)
    finally:
        try:
            os.unlink(mark)
        except FileNotFoundError:
            pass
        with running_lock:
            resetting.discard(username)
    ok = all(s["ok"] for s in steps)
    audit("reset-done", account=username, ok=ok,
          failed=[s["id"] for s in steps if not s["ok"]])
    return ok, steps
