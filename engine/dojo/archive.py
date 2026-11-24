"""`dojo stop` saves what the class produced before it deletes the volumes.

Writes results/<date>_<time>_<workshop>/ (git-ignored; it holds student comments and scores):

  manifest.json    which workshop, the command that started it, when it started and stopped, how long, who
                   was in it, which services ran, and what was saved or skipped and why
  roster.csv       who signed in and whether they were a demo bot
  <file>           one per `exports` entry that a running module declares in its extensions.json (a module's
                   answers, scores, ...): the engine fetches each as the facilitator and never
                   names a module (workshops/README.md, "Result exports")

Best effort: every part is tried on its own, a failure is recorded in the manifest and never stops the
teardown. A stack nobody used (no sign-ins and nothing an export counts) saves nothing."""
from __future__ import annotations

import csv
import io
import json
import subprocess
import tarfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import paths, results, state
from .runtime import Runtime
from .stackapi import StackError, call, running

RESULTS_DIR = paths.REPO / "results"


FORGE_SERVICE = "git-server"
FORGE_REPOS = "/data/git/repositories"   # where Forgejo keeps every bare repo, the org's and each student's


def save_repos(rt: Runtime, dest: Path) -> int:
    """Copy every bare repository out of Forgejo into DEST/<owner>/<name>.git (clone-able, history and all) and
    return how many. Streams one tar from the git server's own container, so no Forgejo credentials are involved.
    Raises StackError when the git server isn't running or the copy fails."""
    from .stackapi import find_container
    c = find_container(rt, FORGE_SERVICE)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.Popen([rt.cli, "exec", c.name, "tar", "-C", FORGE_REPOS, "-cf", "-", "."],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise StackError(f"Could not read the repositories: {exc}")
    assert proc.stdout is not None and proc.stderr is not None
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
            tar.extractall(dest, filter="data")   # refuses absolute paths, links out of DEST and device nodes
    except (tarfile.TarError, OSError) as exc:
        proc.kill()
        raise StackError(f"Could not copy the repositories: {exc}")
    err = proc.stderr.read().decode(errors="replace").strip()
    if proc.wait() != 0:
        raise StackError(f"Could not read the repositories ({err[-200:] or 'tar failed'}).")
    return sum(1 for p in dest.glob("*/*.git") if p.is_dir())


EXTENSIONS_FILE = paths.ENGINE / ".generated" / "allocator" / "extensions.json"


def declared_exports() -> List[Dict[str, Any]]:
    """The merged `exports` entries of this run's manifests (render_extensions.py wrote them at start)."""
    try:
        data = json.loads(EXTENSIONS_FILE.read_text())
    except (OSError, ValueError):
        return []
    items = data.get("exports") if isinstance(data, dict) else None
    return [e for e in items or [] if isinstance(e, dict) and e.get("file") and e.get("upstream") and e.get("path")]


def fetch_export(rt: Runtime, export: Dict[str, Any]) -> Tuple[str, int]:
    """(file text, count) of one declared export; count is the size of its `count` key (0 when it has none).
    Raises StackError when the service isn't running or refuses."""
    service, _, port = str(export["upstream"]).partition(":")
    status, body = call(rt, service, "GET", export["path"], port=int(port or 8080), timeout=int(export.get("timeout", 30)))
    if status != 200:
        raise StackError(f"{export.get('label') or export.get('id')}: {service} refused the export (HTTP {status}).")
    count = 0
    key = export.get("count")
    if key and isinstance(body, dict):
        value = body.get(key)
        count = len(value) if isinstance(value, (list, dict)) else int(bool(value))
    text = body if isinstance(body, str) else json.dumps(body, indent=2) + "\n"
    return (text if text.endswith("\n") else text + "\n"), count


def _roster_csv(rows: List[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["id", "name", "bot", "active"])
    for r in rows:
        w.writerow([r.get("studentId", ""), r.get("name") or "", r.get("ip") == "bot", bool(r.get("active"))])
    return buf.getvalue()


def _folder(workshop: str, now: float) -> Path:
    base = f"{time.strftime('%Y-%m-%d_%H%M', time.localtime(now))}_{workshop or 'stack'}"
    d, n = RESULTS_DIR / base, 2
    while d.exists():
        d = RESULTS_DIR / f"{base}-{n}"
        n += 1
    return d


def save(rt: Runtime, now: Optional[float] = None, with_repos: bool = False) -> Optional[Path]:
    """Write the session folder for the stack that is up now; None when there is nothing worth keeping."""
    now = now or time.time()
    cur = state.read_current()
    got: Dict[str, Any] = {}       # file -> text
    notes: Dict[str, str] = {}     # part -> why it was skipped
    services = sorted({c.service for c in running(rt)})

    roster: List[Dict[str, Any]] = []
    try:
        roster = results.roster(rt)
        got["roster.csv"] = _roster_csv(roster)
    except StackError as exc:
        notes["roster"] = str(exc)

    counts: Dict[str, int] = {}    # export id -> its size, for the ones that declare a `count`
    for export in declared_exports():
        try:
            text, n = fetch_export(rt, export)
        except StackError as exc:
            notes[str(export.get("id") or export["file"])] = str(exc)
            continue
        got[export["file"]] = text
        if export.get("count"):
            counts[str(export["id"])] = n

    humans = [r for r in roster if r.get("ip") != "bot"]
    if not roster and not any(counts.values()):
        return None
    started = cur.started_at if cur and cur.started_at else None
    manifest = {
        "workshop": cur.workshop if cur else "",
        "command": cur.command if cur else "",
        "profile": cur.env_name if cur else None,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started)) if started else None,
        "stopped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
        "duration_minutes": round((now - started) / 60, 1) if started else None,
        "students": len(humans), "demo_bots": len(roster) - len(humans),
        "counts": counts,
        "services": services, "saved": sorted(got), "skipped": notes,
    }
    d = _folder(str(manifest["workshop"]), now)
    d.mkdir(parents=True)
    for name, text in got.items():
        (d / name).write_text(text)
    if with_repos:   # last, and after the folder exists: the repos can be large and must never cost the rest
        try:
            manifest["repos"] = save_repos(rt, d / "repos")
        except StackError as exc:
            notes["repos"] = str(exc)
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return d
