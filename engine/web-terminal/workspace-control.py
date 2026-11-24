#!/usr/bin/env python3
"""Internal-only control plane for per-student code-server/ttyd processes.

Runs as root (same trust model this container already had when it ran
`exec ttyd ... login` continuously -- see entrypoint.sh) inside the
web-terminal container, listening on the workshop_lab-internal network only
(never published through the gateway). The allocator service is the only
caller, deciding *who* gets a workspace; this process only manages the OS
processes that back it, so no docker.sock or cross-container privilege is
ever needed (see workshops/dns-as-code/compose/runner/Dockerfile for why
that's a hard constraint in this stack).

Uses ThreadingHTTPServer deliberately (as the allocator does): the only
shared mutable state here is `running`, guarded by a lock, and each
handler's real work is a short-lived subprocess/pgrep call -- serializing
those on one thread would make Release feel laggy for no benefit.
"""

from workspace_control.handler import main

if __name__ == "__main__":
    main()
