# Roadmap

The single list of open work, **in the order to do it**. Finished work moves to [`RELEASES.md`](RELEASES.md). The old
per-feature plans (design, decisions, task logs) are frozen in [`docs/archive/`](docs/archive/); read them for the
why, but don't update them. When you finish an item: delete it here and add a line to RELEASES.md.

Last updated: 2026-11-24 (3.3 done). The file is now one prioritized flow (phases 0-6), and the 2026-11-23 engine review's
findings (**E1-E12**) are folded in. Earlier versions are in git history (before this change: `d2a37fb`). ·
Cut a feature branch for each new batch of work.

**Effort:** **S** one sitting (an hour or two) · **M** a day or so · **L** several days · **—** no work planned.
**Tags:** **[engine]** edits `engine/`, so ask first (CLAUDE.md) · **[you]** only the user can do it (a browser, another
machine, a decision) · **[stack]** needs a live run (`./dojo <workshop> --test N --fast`, then `./dojo stop`).

**IDs:** each item keeps its old ID (RV, R, D, C, T, P, S, CTF-…), so commits and the review docs still match. **E1-E12**
are new from the 2026-11-23 engine review: a static read of the gateway, allocator, `workspace-control.py`, the `dojo`
CLI and the base compose file. None of them has been reproduced on a stack yet.

## Start here (updated 2026-11-23)

**State:** Phase 0 (the 2026-11-08 review branch and `chore/centralize-plans`), Phase 1 (E1-E4, the 1.7 tests; 1.5/1.6 triaged) and Phase 2's E5/E6 are on `main`. Details are in RELEASES. Both unit suites pass; E1-E5 passed on a live stack. `tools/loadtest.py` is the class-scale load test (`./dojo students N` first, `git checkout dojo.toml` after).

**Next, in order:**
1. **0.1 [you]:** the browser check of the watch tile and `pbcopy` (everything else in Phase 0 passed).
2. **2.6 [stack, ask first]:** the class-sized run (about 20 bots, 2.1's script) that closes Phase 2. It also settles two open measurements: E6's 502-after-death trade-off (kill a code-server and time the recovery; the first try with `pkill` showed no 502, so check the kill landed) and a real page's assets for the `/ide` call count.
3. **3.1 (E7) [you: decision]:** pick the admin hostnames for `--env home`/`--env prod` and whether local runs get a second port; then build it.
4. **2.4/2.5:** netlab start and stop time (need a big netlab stack; slow on 13 GB).
5. Then 3.4-3.6, Phase 4 refactors, and Phase 5/6 as time allows.

## The flow at a glance

| Phase | Goal | Size | Done when |
|---|---|---|---|
| [0](#phase-0-land-the-2026-11-08-review-branch) | Land the 2026-11-08 review branch | S | Browser check passed; both branches merged |
| [1](#phase-1-quick-fixes-correctness-and-hardening) | Quick fixes: one regression, small hardening, small scale wins | 1-2 days | Unit tests pass; one bot stack passes |
| [2](#phase-2-class-scale-performance) | Class-scale performance, measured before and after | M-L | The load test shows the gain; class-sized run passes |
| [3](#phase-3-public-run-readiness) | Public-run readiness: blast radius, sessions, pre-class checks | M-L | Done before the next `--env prod` class |
| [4](#phase-4-engine-structure-and-hygiene) | Engine structure and hygiene | M | Each refactor passes unit tests and one bot stack |
| [5](#phase-5-live-checks-and-browser-passes) | Live checks and browser passes (backlog) | ongoing | Run alongside phases 1-4 whenever a stack is up |
| [6](#phase-6-content-and-feature-tracks) | Content and feature tracks | L | — |
| [Later](#later) | Follow-ups, known limits, accepted residuals, tech to revisit | — | — |

**Why this order.** Phase 1 holds a likely regression (E1) and fixes that each take under an hour. Phase 2 comes before
the class-sized run, so that run checks the fixes instead of measuring known waste, and it starts with a baseline
measurement. Phase 3 is the one design decision (E7) and has to be settled before a public class, not after. Phase 4's
refactors come after the behaviour fixes, so a refactor never hides a regression, and before new content, so new
packs don't copy the old patterns. Phase 5 is not a blocker: whenever a stack is up for something else, take the
matching check from it.

## Phase 0: land the 2026-11-08 review branch

| # | Work | Effort | Description |
|---|---|---|---|
| 0.1 | Browser check **[you]** | S | The watch tile and `pbcopy` in the student's own browser. Everything else passed live 2026-11-09 (log below) |

**What the branch holds.** A read-only review of `304ead5..9108cac` (security, scale, gaps); the fixes are committed
from f29ebbe on and unit-tested (170 OK).

The batch 1-3 fixes:
- netlab `clean()` crash fixed;
- node healthcheck 10 s → 30 s;
- S1: per-node host keys from the seed, plus `known_hosts`, with host-key checking on in the checker, view, terminal and the five `ansible.cfg` files;
- S4: `NETLAB_INPUT` drops new inbound connections on netlab_mgmt;
- S2: a CTF student token can redeploy only the base image or its own tags;
- Forgejo WAL, repo indexer off, log level Warn;
- gateway keepalive 2 s → 60 s;
- ~~`./dojo stop` removes containers 8 at a time~~ (reverted in 0ef506d: no faster; see item 1);
- a terminal memory-cap warning at start;
- docs pack lists;
- S3: tmux/zellij sockets in `/run/dojo/<uid>` (0700), via `ensure_runtime_dir()`, a new `/etc/zsh/zshenv` and `provision-account.sh`;
- S5: the watch client attaches with `TERM=screen-256color`, so OSC 52 doesn't reach the facilitator (tested on local tmux 3.6). Live-check: the roster terminal dot, the watch tile, `pbcopy` in the student's own browser, zellij, and that the zellij image's own zshenv still has its lines.

**Live-check log (2026-11-09).**

| # | Work | Effort | Description |
|---|---|---|---|
| — | Live check: passed | — | Run 2026-11-09, locally on port 8081 (VS Code on Windows held 8080 under mirrored WSL networking).
**git-fundamentals `--test 3 --fast`: all passed.** Bots done; Forgejo WAL on; sockets in `/run/dojo/<uid>` (0700); a planted `/tmp/tmux-<uid>` no longer blocks a terminal; the roster shows terminal state; stop took 30 s with nothing left behind.
**netlab-ansible `--test 2 --fast`: all passed on the rerun.** Host keys match `known_hosts`; no ssh prompt; nodes can't reach `web-terminal:7682`; the `mgmt_iface` (no `ip`) and bot `/run/dojo/<uid>` fixes hold (terminal RestartCount 0, `NETLAB_INPUT` present); both bots passed A1-A11 incl. A5 (only the expected pre-lab demo FAILs); testuser1 done in 16 min, testuser2 in 26 (slower, never stalled); stop 2m35s, nothing left.
**zellij (`git-fundamentals --terminal zellij --test 3 --fast`): passed.** `/etc/zsh/zshenv` has the `/run/dojo/$UID` block first, then the zellij layer's lines; sockets live in `/run/dojo/<uid>/zellij/` under the 0700 dir (zellij still writes only its log to `/tmp/zellij-<uid>/`); bots done; about 76 MB RSS per student (the memory warning guesses 100 MB).
**15-pod stop: back to plain `down` (0ef506d).** `netlab-ansible --test 14 --fast` (15 pods; generate.py caps netlab at 15 students, and `--test 15` adds a 16th), 142 containers, compose up 7-8 min. 8 parallel `rm -f -t 0` before `down`: **11m35s** (netavark veth and dependency races, then `down` retried every container). One `rm -f -t 0 --depend <ids>`: **7m42s** (434 s in the rm, still ~3 s per container, plus a netavark error). Plain `down`: **7m48s**. Same cost, so the pre-pass is gone and stop prints how long `down` took; the ~3 s per rootless container is the open item in the netlab entry below. Not checked: the watch tile and `pbcopy` in a real browser. |

## Phase 1: quick fixes, correctness and hardening

Each is small. Batch them on one branch, then run both unit suites and one bot stack
(`git-fundamentals --test 3 --fast`, then `./dojo stop`).

| # | Work | Effort | Description |
|---|---|---|---|
| 1.5 | Still open from 2026-10-18 (2026-11-08 item 4). **Triaged 2026-11-23, none done:** the CTF `view.py` CSP wraps the intentionally vulnerable target apps, which use inline scripts, so only E7's separate origin fixes it; the gate token is hashed in the browser (`gate.js`), so a salt needs a per-run value in the page; narrowing the content mount needs a per-pack list (cloud-policy and srx `lab-prep` read solutions and stages from it); `CLIENT_HASH` is a design question; the terminal pids limit is already sized per class (`sizing.py`), so drop it | S each | The whole content dir (cloud-policy solutions, srx stages) is mounted in the terminal (`engine/docker-compose.yml:243`); the `--pass` gate token is unsalted sha256 (`start.py:341`); the CTF `view.py` CSP still allows `'unsafe-inline'` (also lowers E7's risk); achievements `CLIENT_HASH` hashes a file students can read; the terminal pids limit is one fixed total |
| 1.6 | Small scale wins (2026-11-08 item 5). **Triaged 2026-11-23:** `./dojo prune` already exists (hook it into stop if wanted); keep the 100 MB zellij warning (76 MB measured plus headroom); the 5 s and 10 s healthchecks gate startup, so slowing them costs start time for little gain. Open: `Cache-Control` on static assets, code-server idle timeout | S | Forgejo and dojo-cloud healthchecks at 5 s, the ctf-range and runner-pool ones at 10 s → 15-30 s; `Cache-Control: max-age` on secret-free static assets in the Caddyfile (now `no-store`); prune about 2.5 GB of dangling images (hook `maintain.py`'s removal into stop or a `./dojo prune`); code-server idle timeout 900 s → 300-600 s?; the memory warning guesses 100 MB per zellij student, measured about 76 MB (2026-11-09): lower it? |

## Phase 2: class-scale performance

Measure first (2.1), fix (2.2-2.5), then prove it at class size (2.6).

| # | Work | Effort | Description |
|---|---|---|---|
| 2.1 | P9 load test (script `tools/loadtest.py`, `/admin/api/stats` counts allocator requests) **[stack]** | S left | Done for `/term` (30 students, Zellij) and `/ide` (10 code-server students) after E5/E6 (RELEASES). Left: the `/ide` run has no "before" (needs the old commit), and E6's 502-after-death trade-off is untested (see RELEASES); rerun at class size in 2.6 (30-60 students, a real page's assets). Run it with `./dojo students N` first and `git checkout dojo.toml` after |
| 2.4 | Netlab start and size (2026-11-08 item 3) | M/L | Create and start the pods in parallel batches (compose up took 8m42s for 142 containers); longer term, pc/sw/fw in one container per branch via netns (about halves start, stop and memory) |
| 2.5 | Netlab stop time | S | Stopping a 138-container stack takes about 7 minutes: a rootless `podman rm` costs about 3 s per container here, not helped by `-t 0`, parallel removal, cgroupfs or no network (measured 2026-10-28; the parallel pre-pass was reverted 2026-11-09, 0ef506d). Cause not found (storage or conmon?): try `podman system` options or fewer containers per pod |
| 2.6 | N3 9.4: class-sized run, what is left **[stack]** | S | Run on git-fundamentals with 20 bots (RELEASES, 2026-11-24). Left: shell hook latency (not measured), the **facilitator VS Code tab "unknown error"** (bots never go through the gateway's `/ide`, so only a browser can reproduce it), and 30-35 students, which needs a bigger Podman machine than the 20 GiB here. Rerun 2.1 at class size |
| 2.7 | CTF class numbers (CTF-SPIKES S9/S14) | M | Persona-swarm tuning, cold start at 40 students, queue concurrency, idle timeout: class-only numbers, take them in 2.6 |

## Phase 3: public-run readiness

Finish before the next `--env prod` class. Settle 3.1's decision first: it decides how 3.2 is built.

| # | Work | Effort | Description |
|---|---|---|---|
| 3.1 | **E7** Facilitator tools on their own origin **[engine] [you: decision]** | M | [Brief](#e7-facilitator-on-its-own-origin-31). `/admin`, Forgejo, every extension route and the facilitator's own `/ide`/`/term` all share one origin. The `X-Requested-With` check stops forged requests from other sites but not a script running on this origin, so one XSS in Forgejo, a module UI or the CTF view (`'unsafe-inline'`, 1.5) can act as the facilitator: read every Forgejo password, take a Forgejo site-admin session through `/forgejo-login`, reset or release students, or open the facilitator's terminal. Today the only defence is each module's `textContent` rule. Fix: serve `/admin` and the facilitator's tools from a second origin (`admin.<host>` behind the home-lab Caddy; a second port locally), with a cookie that is never set on the student origin. Decision: the hostname scheme for `--env home`/`--env prod`, and whether local runs get it too |

| 3.4 | P15 `doctor --live`: pre-class readiness check | M | Design in [`docs/reviews/2026-10-18.md`](docs/reviews/2026-10-18.md) (P13/P15); not built |



| 3.5 | P12 fresh-machine bootstrap | M | `setup.sh`/`setup.ps1` on a clean machine or WSL distro. Needs a machine you create; the P10 half is done (RELEASES, 2026-11-24). Brief in the 2026-10-18 review |
