# Releases

What has shipped, newest first. [`ROADMAP.md`](ROADMAP.md) holds what is still open; when an item there is done
and verified, it moves here in a line or two. Detail behind older entries (design, decisions, per-task logs) is in
[`docs/archive/`](docs/archive/), kept for reference and no longer updated.

Entries are grouped by what reached `main`. Dates are commit or merge dates; "locally" means tested on the
WSL2 desktop stack at `http://localhost:8080`.


## Class-sized run (2.6) and failure recovery (3.5 P10) (2026-11-24)

Both on git-fundamentals, Podman on macOS (libkrun, 20 GiB machine), main at `93f692c`.

- **20 bots, `--fast`:** stack up in 24 s; all 20 bots finished; every student unlocked 22-28 achievements (574 toasts), none lost. No tracebacks in
  terminal, allocator or achievements. `/admin/`, `/admin/api/stats` and `/achievements-admin/` answered in 7-47 ms during the run. Terminal used 790 MB of
  3.2 GB. The only gateway errors were two 502s on `/slides/` while presentation was still starting.
- **Kill one service during a 5-bot round (`podman kill`):** allocator, git-server, gateway and achievements each stayed down, with no restart in two minutes.
  The bots still finished (5/5), but with the allocator down `/login` was 502 and with the gateway down nothing answered. `podman kill` marks a container as
  stopped on purpose, so the restart policy is skipped; `./dojo restart` brings it back.
- **A real crash (kill -9 on the container's process from the VM):** `unless-stopped` works. Back to healthy in about 6 s (git-server), 18 s (allocator, gateway,
  achievements, terminal). The terminal restart ends every student's code-server, ttyd and tmux session; nothing was checked on what a student sees afterwards.
- **Ctrl-C during `./dojo <workshop>`:** exits 130 and leaves the containers coming up (`bootstrap` still `Created`); running the same command again finishes cleanly.
  A corrupt `engine/.build-state/current.json` shows `status` as "not recorded", and a start refuses to run over the stack and says to run `./dojo stop`.
- Not covered: ctf-controller (needs a CTF stack), `./dojo restart` mid-start, and a student's view after a terminal crash.

## Docs trimming, part of item 4.8 (2026-11-24, `docs/trim-4.8`)

- RELEASES.md is down from 980 to about 160 lines: entries before 2026-10-19 moved to `docs/archive/RELEASES-to-2026-10-19.md`, unchanged.
- `docs/architecture.md` network table gains `netlab_mgmt`; it was the only network a module declares that the table missed.
- `engine/README.md` "Student credentials" now points to `docs/security.md` for the formula and keeps the file-level detail.
- Already done, no change: the root README lists all five CTF sessions, and the repo CLAUDE.md names no pack list to update.
