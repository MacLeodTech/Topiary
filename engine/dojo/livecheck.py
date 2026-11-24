"""`dojo doctor --live`: the readiness rules for a class other people will join (roadmap 3.4, P15).

Pure functions of the resolved settings, so each rule is unit-testable without an engine. `doctor.run_checks` calls
`live_checks` and escalates a few of its own warnings to failures under `--live`; nothing here starts, stops or
changes anything."""
from __future__ import annotations

import hashlib
from typing import Callable, Dict, List, Optional

from . import checks, paths, sizing
from .doctor import FAIL, INFO, OK, WARN, Check

MIN_PASSWORD_LEN = 10
MIN_GATE_CODE_LEN = 8
LIVE_MEM_PER_STUDENT_MB = {"web": 650, "zellij": 100}   # peak, not the 316 MB steady state sizing.py warns on
SIZING_KEYS = ("WEB_TERMINAL_MEM_LIMIT", "WEB_TERMINAL_PIDS_LIMIT", "CODE_SERVER_MAX_HEAP_MB")
PASSWORD_KEYS = ("FACILITATOR_PASSWORD", "FORGEJO_ADMIN_PASSWORD", "TTYD_PASSWORD")
# Titles `doctor` already reports as warnings that a live class cannot live with.
ESCALATE = ("Resource limits", "HTTPS", "Student passwords")


def _dev_ctf_token(key: str, value: str) -> bool:
    """A CTF token that anyone can compute: empty, a dev-ctf-* placeholder, or modules/ctf-range/module.env's
    derivation from an empty GATEWAY_TOKEN."""
    if not value or value.startswith("dev-ctf-"):
        return True
    label = {"CTF_CONTROL_TOKEN": "ctf-range/control", "CTF_BUILD_TOKEN": "ctf-range/build"}.get(key)
    return bool(label) and value == hashlib.sha256(f"{label}:".encode()).hexdigest()[:40]


def live_checks(env: Dict[str, str], operator: Dict[str, str], students: Optional[int], gate_pass: Optional[str],
                origin_of: Callable[[str], str] = lambda key: "environment", workshop: Optional[str] = None,
                image_built: Callable[[str], bool] = lambda tag: True) -> List[Check]:
    """env: the resolved settings (the workshop's when one is named); operator: the operator's own layers only."""
    out: List[Check] = []
    add = out.append
    local = checks.local_only(env)
    if local:
        add(Check(INFO, "Live", "this machine is the only one that can connect (loopback), so the public-run rules "
                  "below are advisory"))
    n = students if students is not None else sizing._int(env, "STUDENT_COUNT", sizing.STUDENT_COUNT_DEFAULT)
    bad = WARN if local else FAIL

    # --- Secrets -------------------------------------------------------------
    empty = [k for k in PASSWORD_KEYS if not env.get(k, "").strip()]
    if empty:
        add(Check(bad, "Empty passwords", ", ".join(empty) + " empty: nobody could sign in with them",
                  f"Run '{paths.PROG} setup' to generate real ones."))
    short = [k for k in PASSWORD_KEYS if env.get(k, "").strip() and len(env[k]) < MIN_PASSWORD_LEN]
    if short:
        add(Check(WARN, "Password length", f"{', '.join(short)} shorter than {MIN_PASSWORD_LEN} characters",
                  "Use at least 10; 'openssl rand -base64 12' makes one."))
    if not env.get("STUDENT_PASSWORD_SEED"):
        add(Check(bad, "Student passwords", "no STUDENT_PASSWORD_SEED: every student shares one Forgejo password",
                  "Add one ('openssl rand -hex 32') or run 'setup'."))
    shared = sorted({k for k in PASSWORD_KEYS if env.get(k) and env.get(k) == env.get("STUDENT_PASSWORD_SEED")})
    shared += [k for k in ("FACILITATOR_PASSWORD",) if env.get(k) and env.get(k) == env.get("STUDENT_PASSWORD")]
    if shared:
        add(Check(WARN, "Shared secrets", f"{', '.join(shared)} equals a student-facing secret",
                  "The facilitator's password must differ from anything a student is given."))
    if gate_pass is not None and len(gate_pass) < MIN_GATE_CODE_LEN:
        add(Check(WARN, "Access code", f"--pass code is {len(gate_pass)} characters; use at least {MIN_GATE_CODE_LEN} for a public run"))
    tokens = [k for k in ("CTF_CONTROL_TOKEN", "CTF_BUILD_TOKEN") if k in env and _dev_ctf_token(k, env[k])]
    if tokens:
        add(Check(bad, "CTF tokens", f"{', '.join(tokens)} empty or a development value (derived from an empty GATEWAY_TOKEN)",
                  "Set GATEWAY_TOKEN in .env; the CTF tokens are derived from it."))

    # --- Sizing for N students -----------------------------------------------
    accounts = n + 1
    need_pids = accounts * sizing._int(env, "WEB_TERMINAL_PIDS_PER_STUDENT", sizing.PIDS_PER_STUDENT)
    have_pids = sizing._int(env, "WEB_TERMINAL_PIDS_LIMIT", 0)
    # The start raises the cap to the class's need (sizing.fit_pids), so a low cap is information; a *workshop* that
    # lowers it below the need is the failure, reported under "Sizing override".
    add(Check(OK if have_pids >= need_pids else INFO, "Pids for the class",
              f"cap {have_pids or 'unset'}; {n} students need {need_pids}" + ("" if have_pids >= need_pids else " (the start raises it)")))
    flavor = (env.get("TERMINAL_FLAVOR") or "web").strip().lower()
    per = LIVE_MEM_PER_STUDENT_MB.get(flavor, LIVE_MEM_PER_STUDENT_MB["web"])
    limit = sizing.mem_mb(env.get("WEB_TERMINAL_MEM_LIMIT") or sizing.MEM_DEFAULT)
    if limit is not None:
        add(Check(OK if accounts * per <= limit else WARN, "Terminal memory",
                  f"{limit} MB for {n} students; peak need ~{accounts * per} MB ({accounts} accounts x {per} MB)",
                  "" if accounts * per <= limit else f"Raise it, or run '{paths.PROG} capacity WORKSHOP --students {n}'."))
    steady = sizing.MEM_PER_STUDENT_MB.get(flavor, sizing.MEM_PER_STUDENT_MB["web"]) * accounts
    floors = {"WEB_TERMINAL_PIDS_LIMIT": need_pids, "WEB_TERMINAL_MEM_LIMIT": steady}
    for key in SIZING_KEYS:
        a, b = operator.get(key, ""), env.get(key, "")
        if a and b and a != b:
            size = sizing._size(key, b)
            below = key in floors and size is not None and size < floors[key]
            add(Check(FAIL if below else WARN, "Sizing override", f"{key} is {b} ({origin_of(key)}), not your {a}"
                      + (f"; below the {floors[key]} the class needs" if below else ""),
                      "The workshop's own setting wins; check it still fits the class."))

    # --- The machine ---------------------------------------------------------
    if workshop:
        tag = f"topiary/web-terminal:{workshop}"
        built = image_built(tag)
        add(Check(OK if built else WARN, "Images built", "the workshop's terminal image is built" if built
                  else f"{tag} is not built; the first start would spend the build time in front of the class",
                  "" if built else f"Run '{paths.PROG} {workshop} --build-only' before class."))
    return out


def escalate(results: List[Check]) -> List[Check]:
    """Under --live these `doctor` warnings are failures."""
    for c in results:
        if c.level == WARN and c.title in ESCALATE:
            c.level = FAIL
    return results
