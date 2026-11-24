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
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import paths, results, state
from .runtime import Runtime
from .stackapi import StackError, call, running

RESULTS_DIR = paths.REPO / "results"


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


def save(rt: Runtime, now: Optional[float] = None) -> Optional[Path]:
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
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return d
