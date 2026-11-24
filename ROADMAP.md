# Roadmap

The single list of open work, **in the order to do it**. Finished work moves to [`RELEASES.md`](RELEASES.md). The old
per-feature plans (design, decisions, task logs) are frozen in [`docs/archive/`](docs/archive/); read them for the
why, but don't update them. When you finish an item: delete it here and add a line to RELEASES.md.

Last updated: 2026-11-24 (merged: 3.3, 3.4, 3.6, 4.1, 4.5, 6.1.2, 1.6, 4.4, 6.3.1; 4.8, 2.6 and 3.5 trimmed; 3.1 decided). The file is now one prioritized flow (phases 0-6), and the 2026-11-23 engine review's
findings (**E1-E12**) are folded in. Earlier versions are in git history (before this change: `d2a37fb`). ·
Cut a feature branch for each new batch of work.

**Effort:** **S** one sitting (an hour or two) · **M** a day or so · **L** several days · **—** no work planned.
**Tags:** **[engine]** edits `engine/`, so ask first (CLAUDE.md) · **[you]** only the user can do it (a browser, another
machine, a decision) · **[stack]** needs a live run (`./dojo <workshop> --test N --fast`, then `./dojo stop`).

**IDs:** each item keeps its old ID (RV, R, D, C, T, P, S, CTF-…), so commits and the review docs still match. **E1-E12**
are new from the 2026-11-23 engine review: a static read of the gateway, allocator, `workspace-control.py`, the `dojo`
CLI and the base compose file. None of them has been reproduced on a stack yet.

## Start here (updated 2026-11-23)

**State (2026-11-24):** everything buildable without you is on `main` (PRs #86-#97): Phases 0-1, E5/E6, and 2.6 (class-sized run, 20 bots), 3.3, 3.4, 3.6, 4.1, 4.5, 6.1.2, 1.6, 4.4, 6.3.1, plus the docs trim and the 3.5 failure-recovery results. Details are in RELEASES. Unit suites pass; the post-merge stack was not re-run live, so run `./dojo git-fundamentals --test 3 --fast` once on a new machine first (`./dojo stop` after). `tools/loadtest.py` is the class-scale load test (`./dojo students N` first, `git checkout dojo.toml` after).

**Next, in order:**
1. **3.1 (E7) [engine, ask first]:** build it. Decided: facilitator tools on `admin.<host>` for `--env home`/`--env prod`, a second port for local runs, and a cookie never set on the student origin. Read the [brief](#e7-facilitator-on-its-own-origin-31) first; it touches the Caddyfile, auth and cookies, so update the diagrams in `engine/README.md`.
2. **0.1 [you]:** the browser check of the watch tile and `pbcopy`.
3. **3.5 [you]:** P12 fresh-machine bootstrap, on a clean machine or WSL distro (this new PC may be that machine).
4. **2.6 leftovers:** shell hook latency, the facilitator VS Code "unknown error" (browser only), 30-35 students (needs a bigger VM than 20 GiB).
5. **4.8 [you: decision]:** `engine/README.md` still repeats `docs/architecture.md` and `docs/security.md`; say which file owns the diagrams, then trim.
6. **2.4/2.5:** netlab start and stop time (need a big netlab stack).
7. Then Phase 3's remainder, Phase 4's remaining refactors, and Phase 5/6 as time allows.

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

Finish before the next `--env prod` class. 3.1 is decided (see its row); build it first, since it decides how 3.2 is built.

| # | Work | Effort | Description |
|---|---|---|---|
| 3.1 | **E7** Facilitator tools on their own origin **[engine]** | M | **Decided 2026-11-24: `admin.<host>` for `--env home` and `--env prod`; local runs get a second port.** [Brief](#e7-facilitator-on-its-own-origin-31). `/admin`, Forgejo, every extension route and the facilitator's own `/ide`/`/term` all share one origin. The `X-Requested-With` check stops forged requests from other sites but not a script running on this origin, so one XSS in Forgejo, a module UI or the CTF view (`'unsafe-inline'`, 1.5) can act as the facilitator: read every Forgejo password, take a Forgejo site-admin session through `/forgejo-login`, reset or release students, or open the facilitator's terminal. Today the only defence is each module's `textContent` rule. Fix: serve `/admin` and the facilitator's tools from a second origin (`admin.<host>` behind the home-lab Caddy; a second port locally), with a cookie that is never set on the student origin. Decision: the hostname scheme for `--env home`/`--env prod`, and whether local runs get it too |
| 3.5 | P12 fresh-machine bootstrap | M | `setup.sh`/`setup.ps1` on a clean machine or WSL distro. Needs a machine you create; the P10 half is done (RELEASES, 2026-11-24). Brief in the 2026-10-18 review |

## Phase 4: engine structure and hygiene

No behaviour change. Every E item in phases 1-4 links to its [execution brief](#execution-briefs-e1-e12). Before each refactor, make sure its tests exist; after it, run unit tests and one bot stack.

| # | Work | Effort | Description |
|---|---|---|---|
| 4.7 | Declarative pack settings | L | `workshop.env`/`module.env` are run with `sh` (`engine/dojo/envfiles.py:92`). TOML, like `dojo.toml`, would make validation and `--dry-run` simpler (2026-10-18 review §3.4). Long term |
| 4.8 | Docs trimming, what is left | S | `engine/README.md` (1135 lines) still repeats `docs/architecture.md` and `docs/security.md` in its Architecture and routing sections. Needs a decision on which file owns the diagrams (CLAUDE.md names the README) before cutting more |

## Execution briefs: E1-E12

One brief per finding from the 2026-11-23 review: where to change, how, how to test, and when it counts as done. All
need **[engine]** approval first. Shared rules: work on a feature branch; run both unit suites
(`PYTHONPATH=engine:$(echo engine/.cache/pylib-*) python3 -B -m unittest discover -s engine/dojo/tests -t engine` and
`cd engine/allocator && python3 -B -m unittest discover -s tests`); a live check uses `--test N --fast`, waits on
`~/.dojo-bot-done` and ends with `./dojo stop`; when it's done, delete the row and the brief here and add a line to RELEASES.


#### E7: facilitator on its own origin (3.1)

- **Decision first [you]:**
  - The hostnames: e.g. `admin.dojo.macleodtech.ca` and `admin.dojoh.macleodtech.ca` on the home-lab Caddy, a second DNS name and certificate each.
  - Locally: a second port (`localhost:8081`), since two ports are two origins.
  - Whether `--env home` must have it, or only `--env prod`.
- **Where:** `engine/gateway/Caddyfile` (a second site block, `{$GATEWAY_ADMIN_LISTEN}`); `engine/gateway/entrypoint.sh`; `engine/dojo/config.py` (new `admin_base_url`/`GATEWAY_ADMIN_LISTEN`); `engine/docker-compose.yml` (a second published port); `engine/allocator/accounts.py` and `handler.py` (cookies); `render_extensions.py` (facilitator-gated routes and `admin_tabs` served on the admin origin); the docs (`docs/security.md` §2, `docs/operations.md`).
- **Design:**
  - The admin origin serves `/admin*`, `/login`, the facilitator's `/ide` and `/term` and facilitator-gated extension routes.
  - The student origin answers `/admin*` with a redirect to the admin origin and refuses a facilitator sign-in (redirects to the admin origin's `/login`).
  - The facilitator's `dojo_login` cookie is host-only on the admin origin (no `Domain=` attribute), so the browser never sends it to the student origin.
  - `/admin` tabs that frame student-origin pages (Forgejo, slides, module UIs) use the student origin's URLs. Framing needs `frame-ancestors` to allow the admin origin; the allocator's CSP is `frame-ancestors 'self'` today.
  - The facilitator has no session on the student origin. Pages that check facilitator identity there (Forgejo admin through `/forgejo-login`) move to the admin origin.
- **Order:** spike the framing first (Forgejo and one module UI framed from the other origin, sign-in inside the frame), then the cookie split, then the routing.
- **Test:**
  - Live **[stack]**: every `/admin` tab loads (P8's list).
  - A script on the student origin can't read `/admin/api/sessions`: fetch it from a page served under `/slides`; it should fail on CORS or a redirect.
  - The facilitator's terminal opens only from the admin origin.
  - `--env home` with the real hostnames **[you]**.
- **Done when:** the P8 pass works on the admin origin and the cross-origin checks fail as they should; `docs/security.md` is updated.

## Phase 5: live checks and browser passes

A backlog, not a blocker: whenever a stack is up for something else, take the matching check from here. A brief for an
agent is built from these lines (say when the stack is torn down).

### 5.1 Stack checks

| # | Check | Effort | Stack / what to confirm |
|---|---|---|---|
| 5.1.1 | Ubuntu WSL/Docker host run **[you: other machine]** | S | `vault-fundamentals --test 2 --fast` with `RUNNER_POOL_SECURITY_OPT_1/2` unset, to confirm the defaults (`no-new-privileges=true`, bare `no-new-privileges`) change nothing on Docker. A reset twice plus labs 11 and 12 already passed on podman here (2026-10-15) |
| 5.1.2 | Student reset: close out | S | R0's no-purge teardown (delete own repos, leave the org, delete the account without purge) is marked "not yet live". Once seen live, move R0-R4 and R3.x to RELEASES (git-fundamentals result: steps 3-5 s, idempotent, a bot restarts from round 1, the optional score clear clears only that student). Status table in [Reference](#student-reset-build-status) |
| 5.1.3 | D1 student `dojo` command | S | Zellij flavor (`dojo fix-terminal` opens the layout tab; `dojo help` in a Zellij pane), a CTF pack (`dojo flag submit`, `dojo reset`, `dojo check` through the ctf-defend wrapper), vault/tofu-basics (`dojo env`), and Tab completion by hand in a browser terminal |
| 5.1.4 | P7 live for the other packs | M | Lab walk-throughs for cert-autorenewal and vault-fundamentals |
| 5.1.5 | P8 on a CTF stack | S | The `/admin` tabs on a CTF stack, and the code-server IDE tab from `/admin` |
| 5.1.6 | PC-S4 (CLOUD-POLICY-AS-CODE-PLAN) | S | Confirm live that cloud-api on `runner_net` with the Dojo Cloud CA works for CI jobs; refresh the plan's stale status line ("not yet live") |
| 5.1.7 | CTF-SPIKES S16, S15, S6 | S each | S16: Zellij flavor reconnect with the tile open, hours of runtime, browser keys. S15 (*check*): can a pack hide the VS Code tab, and does anything else start code-server eagerly. S6 (*check*): the multi-arch skopeo archive (~370 MB, `image load` ~3 min per start): trim to index plus amd64 |
| 5.1.8 | CTF-SPIKES S8 | S | End-to-end TXID check and internal-agent flag wiring (CTF-P5) |
| 5.1.9 | NETLAB-PLAN s9 | S each | Host iptables/nft rule count with the class running; nginx and sshd under load; re-run capability, sysctl and no-new-privileges results under rootless podman (*check*) |
| 5.1.10 | netlab leftovers | S each | Not measured in the 2026-11-06 15-pod run: the checker with 15 pods checking at once, a real student on the stack, start time and idle memory of a 15-student class. The A11 capstone assertion is unit-tested but not yet run on a stack. The checker's rate limit (6 per minute) is tight for testing |
| 5.1.11 | Not verified since `f977209` (code-server memory cut) | S each | tofu-basics `tests/e2e.sh` on the new web-terminal image; `./dojo capacity` printing "Left out N" for a closed tab (dry-run only so far) |
| 5.1.12 | Not exercised in P4/P5 (remediation) | M | 300 app-db connections · the app-host shim on 443 (base URL was plain `http://localhost:8080`) · a real-browser "Release unused" |
| 5.1.13 | Split smoke run (parked 2026-10-03) | M | See [Later: smoke run](#smoke-run) for where it stands |
| 5.1.14 | P11 slide overflow sweep | S | `workshops/assets/slide-overflow.sh <workshop>` over every deck (done so far: dns-as-code, vault-fundamentals, git-fundamentals; the 7 overflowing slides were trimmed 2026-10-15) |

### 5.2 Browser checks **[you]**

| Check | Effort | Description |
|---|---|---|
| Widget and Reset dialog | S | Widget frame at full height on first load (`toast.js` asks the widget to report again once it listens); the Reset dialog's "Also clear their achievements and score" checkbox |
| Achievements looks | S | A red negative score (board, widget, `/admin`) and a negative toast in VS Code; the badge PNG download, capstone badge tier and a typed certificate name; a real student's stale-branch roster PR |
| Hidden-tab toasts | S | With the landing page open in a background tab, an unlock in the VS Code terminal pops up in VS Code (`toast.js` skips polling while `document.hidden`), and the landing page shows queued toasts when it comes to the front |
| CTF Target Viewer card | S | As a student, in a browser (the real-time dwell run and the student SOC feed passed 2026-10-15, RELEASES) |
| C5 untested CLI paths (out of band) | S | `CORP_CA_BUNDLE` for the first-run wheel download behind TLS inspection, and the error without it ([`C5-guide.md`](C5-guide.md) step 2). Everything else passed on macOS (podman) and Docker |

### 5.3 Manual passes **[you]**

Longer browser passes, each a sitting or more.

| Check | Effort | Description |
|---|---|---|
| [Modules browser pass](#modules-browser-pass) | M | Was MODULES-PLAN T3.4: every workshop as a student and as the facilitator (checklist below) |
| tofu-basics T9.9 (browser pass) | M | Labs 0-3 on a rebuilt image (including HCL highlighting in code-server) and labs 4-10 with the portal clicked, not called through the API: Add tag, Save tags, Delete dialog, Browse (to the deployed `dojo/hello` site), Quota tile, Refresh now, and the attention tile reading `code: message` (25a7176, offline-tested only). Facilitator: `/admin` Slides and Dojo Cloud tabs render in their iframes; Terminal, VS Code and Forgejo tabs still fine |
| tofu-basics T9.4 (human dry run, 3-5 people) | L | Run them through Track A only or A + B (about 103 min for both by the lab README's estimates). Note every point of confusion, time the walkthrough against the slide deck's talk timings (guesses so far), then fix labs, slides and README. `workshops/tofu-basics/FACILITATOR.md` says the first real class doubles as this dry run |
| vault-fundamentals | S-M | A person walking labs 7-9 in the UI (the tests make the UI's secret steps with the same API calls), the Runners panel's look beyond screenshots, and "Release unused" in a real browser. The rest of the P4/P5 browser pass was done by the user 2026-09-29 |
| UI changes, weekend of 2026-09-26 | S | The `/admin` sidebar at desktop width and under 700 px, and Mermaid diagrams in the lab reader, light and dark |

#### Modules browser pass

For each workshop: `./dojo stop`, `./dojo <workshop>`, open the base URL as a student and in a private window as
the facilitator.

**Common checks**

| Area | Expect |
|---|---|
| Student landing page | Cards each open (VS Code, Terminal, Forgejo, Slides plus the workshop's own) |
| `/admin` | Roster, VS Code, Terminal, Forgejo and Slides plus the workshop's tab, each loading in its iframe |
| Status strip | Forgejo, Terminals and Slides Ready plus the workshop's own |
| Terminal | `whoami` gives `studentNN`; the workshop's tools run |
| Teardown | `./dojo stop` finishes cleanly |

**Per workshop**

| Workshop | Check |
|---|---|
| git-fundamentals | Lab 1, clone, branch, push, open a PR |
| dns-as-code | `dnscontrol version`; push a branch and open a PR; Actions shows **DNS Preview** green; merge and **DNS Apply** goes green; `dig` shows the record |
| cert-autorenewal | **Site Inspector** card and tab; after Lab 2 step 6 a student's visit shows `http://` → 301 → `https://` with a verified certificate, the second visit is upgraded by HSTS; the facilitator's tab can visit any student's name |
| tofu-basics | **Dojo Cloud** card and tab; the portal opens on the student's subscription; the facilitator's tab shows the progress view; after a Track B `apply` the resource shows in both |

This per-workshop table predates three packs and still needs rows for **vault-fundamentals** (its own browser notes are
in [5.3](#53-manual-passes-you) above), **dojo-introduction** and **cloud-policy-as-code** before the pass is complete.


## Phase 6: content and feature tracks

New teaching material and features. Pick one track at a time; each starts on its own branch.

### 6.1 CTF workshop series

A five-session capture-the-flag series (CTF-1 to CTF-5, packs `ctf-access`, `ctf-server-trust`, `ctf-secrets-config`,
`ctf-trust-chain`, `ctf-defend`). The range, all 14 targets and the CTF-5 defend tooling are built (see RELEASES, "CTF range
build log"). The plan, with its checkpoint, is [`docs/plans/CTF-WORKSHOP-PLAN.md`](docs/plans/CTF-WORKSHOP-PLAN.md); it carries the detail.
`workshops/ctf-defend-test` (the old shared facilitator harness) is deleted; `ctf-secrets-config` and `ctf-trust-chain`
now ship all 3 of their targets each.

| # | Work | Effort | Description |
|---|---|---|---|
| 6.1.1 | Defend pilot **[you]** | M | Defend lab redesign: built and live-verified (RELEASES; as-built contract: plan 8.13; no `INCIDENT.md` gate, decided against 2026-10-15 and removed); open: a pilot with 2-3 people (runbook and report script ready: docs/CTF-PILOT.md) to tune stagger (0.5 x dwell) and dwell. Stretch: `git-secrets` as a fourth target only if a rotation mechanism proves out |
| 6.1.3 | Ramp and scoring design (CTF-SPIKES S13) **[you: decisions]** | M | Ramp curve shape, attention split across up to 4 targets, top-10 formula |
| 6.1.4 | Facilitator-to-bot inject and hint-probe channel (S13, plan 8.5) | M | Not built |
| 6.1.5 | Scanners for targets 8-11 (S17) | M | Semgrep, grype, pip-audit, offline; where findings render, and the stage in runner-pool's job |
| 6.1.6 | Full defend loop on real services (CTF-SPIKES) | M | Against a real git-server clone and the real runner-pool, plus a warm-registry number for the real app image |
| — | Bonus challenges | — | Parked (2026-10-12): the CTF packs are a challenge in themselves, so they get no `dojo challenge` sections. A second, more obscure path per target would be their bonus challenge |

### 6.2 Technology track: SRX with Terraform and Mist (`srx-terraform`)

Plan and spike results: [`docs/plans/SRX-MIST-PLAN.md`](docs/plans/SRX-MIST-PLAN.md). Workshop buckets (`WORKSHOP_TRACK`) are on
`feat/workshop-tracks` (2026-11-04). The spike showed the real `Juniper/mist` provider 0.11.0 running a full SRX build
(apply, empty re-plan, drift, import, destroy) against a fake API answering as `api.mist.com`, offline.

| # | Work | Effort | Description |
|---|---|---|---|
| T4 | SRX engineer review **[you: find a reviewer]** | M | An SRX engineer answers [`SRX-REVIEW.md`](workshops/srx-terraform/SRX-REVIEW.md) (best: `config_cmd` for one hub and one spoke in a real org), then the renderer follows; confirm on a real org the `dns_override`/`ntp_override` flags and device `vars` over site vars |
| — | Netfilter-backed gateways | L | Optional, for traffic tests (SRX-MIST-PLAN) |

### 6.3 Platform features

| # | Work | Effort | Description |
|---|---|---|---|
| 6.3.2 | Achievements Phase 6: certificate **[you: decision]** | S | Certificate, badge PNG and name dialog are done; one decision is left |
| 6.3.3 | D2 Retire the shims | S | Once a live class has used `dojo ...`: drop `dojo-check`/`dojo-challenge`/`lab-prep`/`sensei` as student-facing names (the prompt hook still calls `dojo-check --shell`/`--echo`, which stay) and the old-marker strip in `lab-reader.js` |
| 6.3.4 | D3 `dojo help` per workshop | S | Optional workshop footer (e.g. "start with `dojo prep N` if you join late") from a `dojo-help` text file in `cmd.d`'s sibling; today every workshop shows the same generic footer |
| 6.3.5 | netlab probe agent | S | The checker and `netlab-view` use SSH for now |
| 6.3.6 | netlab capstone record | S | The capstone verifies from the checker's in-memory record, so a checker restart means students re-run their checks |
| 6.3.7 | netlab class ceiling (NETLAB-PLAN s9) | M | Rootless podman cannot hold a 240-container class (`kernel.keys.maxkeys` 200 per uid; stopped at 196): document the ceiling and size classes to it |

### 6.4 On hold

| ID | Work | Effort | Description |
|---|---|---|---|
| RV36 | More workshops (on hold 2026-10-15) | L each | GitOps with a reconciler (Argo CD or Flux on k3s), needs a capacity check; then supply chain (cosign, SBOM), observability as code, secrets rotation |
| RV38 | Reset environment button (on hold 2026-10-15: a full reset is `./dojo stop` and a rebuild; Release all and the per-student reset exist) | M | Asked for 2026-10-02: a button on `/admin` that releases every slot and puts every student back to a fresh start without restarting the stack (between two sessions of a class). Build it on the student reset's per-student hook contract (`STUDENT-RESET-PLAN.md` §4.4): run the reset for every student, then module hooks clear their own state (achievements, sensei, dojo-cloud). Facilitator gate, a typed confirmation, audit line. A smaller first step, **Release all**, only clears the slot table. Rule: **nothing survives `./dojo stop`**; every state file stays in a named volume (`allocator_state` is, verified 2026-10-01), and RV13's CI should fail any compose fragment that writes state outside one. Engine change, approved |

## Later

Follow-ups with no date, known limits, and accepted residuals.

### Accepted residuals (remediation leftovers)

None are Critical or Important.

| ID | Work | Effort | Description |
|---|---|---|---|
| FIND-11 | PowerDNS keys | — | Partial, accepted (2026-10-03): per-student DNS keys and the gate's ownership checks are in; PowerDNS's own key stays a one-way hash of `GATEWAY_TOKEN`, which students never see and which already opens the whole lab |
| FIND-17 | Unseal share | — | Partial, accepted (D9): the single unseal share stays on the setup volume |
| FIND-15 | dojo-cloud socket | — | Accepted, no work: socket `0660 root:cloud`; privileged DinD stays |
| FIND-19 | Plaintext backends | — | Accepted, no work: plaintext to OpenBao and Postgres, documented |

### Smoke run

| Check | Stack | Where it stands |
|---|---|---|
| Split smoke run (parked 2026-10-03) | `smoke.sh cloud-policy-as-code --split each --timeout 60` | First run 2026-10-03: labs 2, 4-7 and 12 ok in 9-18 min. Failed: 3, 9, 10 in lab-prep (provider "Plugin did not respond": the 320 pids cap was hit 333 times; since 2026-10-19 a start sizes the cap from the pack's `WEB_TERMINAL_PIDS_PER_STUDENT=70`); 0-1 (retest.sh killed the bot mid lab 0 apply, leaving a state lock lab-prep 0 never clears: a range starting at 0 should only be watched, not parked and re-prepped); 8 and 11 (pr.yml red: a lab-prep gap. From Lab 8, CI plans the fork's `main` against the cloud, and `lab-prep` pushed the rebuilt state to `main` only from Lab 12, so CI saw the whole policy as drift. Fixed (PR #10): push it from Lab 8. Rerun alone with the fix: labs 8 and 11 PASS). When picked up: a watch-only mode in `retest.sh` for a range starting at 0, then `./dojo stop` (image rebuild for lab-prep and the caps) and rerun the split |

### vault-fundamentals follow-ups

| Work | Effort | Description |
|---|---|---|
| Policy as code for OpenBao | L | Namespace policies in a git repo, changed by PR and applied by CI with drift shown when someone edits in the UI; OpenTofu `vault` provider building on tofu-basics, or `bao policy write` in CI; a lab or its own workshop |
| OpenBao PKI for cert-autorenewal | M | Use OpenBao's PKI engine as the CA in `cert-autorenewal` |
| Mirrored actions in Forgejo | M | Mirror a small pinned set of actions (checkout, a vault-login action) into Forgejo at setup so labs can show `uses:` as companies do |
| Lab 11 restart login | S | Lab 11 should show a restart logging in again (lab 10 ends on that promise) |

### tofu-basics follow-ups

| Work | Effort | Description |
|---|---|---|
| `dcloud` CLI for students | M | `login`, `group list`, `container list/show/logs`; not `dojo`, which is the facilitator's platform CLI |
| CI `plan` on pull requests | M-L | Via Forgejo Actions; needs runner network design like dns-as-code's `runner_net` |
| More Azure-shaped resources | M-L | Virtual network, storage account, if the ARM facade extends cheaply |
| Remote state backend simulation | M | Simulate a remote state backend |
| Stretch labs 11-12 | L | Only if wanted |

### tofu-basics known limits

| Work | Effort | Description |
|---|---|---|
| One container per group | — | Only one container per group and only `dojo/hello:*` images (by design) |
| LRO | M | `Azure-AsyncOperation` is not implemented |
| arm64 | M | Untested: checksums pinned per arch, only amd64 built |
| 20+ students | — | Out of scope; 15 is this box's ceiling |
| T9.8 isolation on real Docker | M | **Deferred:** re-test isolation on real Docker before any non-podman delivery (the privileged-DinD risk is materially higher there); this machine has no Docker |

### Achievements shell hook limits (accepted)

| Work | Effort | Description |
|---|---|---|
| Chained-line exit codes | — | The hook sees only the line's exit code, so in a chained line a failure is credited only where it is provable (the last pipeline of the last list; see `matcher._segment_exits`): `a; git push; echo $?` can't earn `f-rejected` |
| Command text and hand-posted events | — | The hook sends the text of every command to the service (kept nowhere, only matched), and a student can post their own shell events by hand, which earns only what typing the command would |

### Tech to revisit

| Tech | Why parked | Revisit when |
|---|---|---|
| [Keyorix](https://github.com/keyorixhq/keyorix) | Lightweight, self-hosted, AGPL secrets manager (EU-compliance/NIS2 framing, air-gap friendly, two-binary deploy) evaluated 2026-10-05 against OpenBao for the vault lab. Deliberately skips Vault's PKI/dynamic-secrets/auth-method breadth for operational simplicity, so it's not a fit for `secrets-workshop-plan`'s teaching surface — and at ~20 GitHub stars it's too early to build any lab on. Positioning (self-hosted, EU-compliant, air-gapped, fully open source) is attractive and worth a second look once the project has real adoption | It picks up meaningfully more stars/contributors/production users, or a second project with the same positioning (self-hosted + AGPL/OSS + EU-compliance framing) appears and is more mature |
| [Infisical](https://infisical.com/) | Considered as a more mature open-source alternative to Keyorix for a possible "lightweight secrets management" lab (pre-Vault, no dynamic secrets/PKI needed). Its OSS edition's team/org features sit behind commercial billing, which cuts against this platform's preference for fully open, self-hostable tooling | A fully-open tier covers team/org features, or the gap stops mattering for how the platform would use it |

## Housekeeping

| Work | Effort | Description |
|---|---|---|
| Take-home handouts and PowerPoint decks | M | Parked: `handouts/` (lab handouts, starter repos, deck export script), the `.githooks` pre-commit and the CI `handouts` checks were all deleted because they had drifted from the labs. Recover from git history if wanted again |

## Reference

Settled material the work items above point to. Not work items.

### Running on the Mac

On the Mac (rootful Podman + SELinux) start with `--env mac-podman` (sets `RUNNER_POOL_SECURITY_OPT_1=unmask=/proc/*` and
`RUNNER_POOL_SECURITY_OPT_2=label=type:container_engine_t`), or no runner or app can start (`unshare: mount /proc
failed`). Details in `modules/runner-pool/README.md`. The Mac's
published port 8080 can reset connections from the host; reach the gateway from inside the lab network instead, with
`Host: localhost:8080` (the facilitator login is the `/login` cookie, and Reset needs `X-Requested-With: dojo-admin`).
Every `--test` run uses `--fast`.

### Achievements tools and bot rules


Tools (`modules/achievements/tools/`, run from the repo root): `fired.py <workshop>` lists each catalog item with who
earned it and the never-fired ids; `botaudit.py <workshop>` runs every bot command through the real matcher (static:
runtime values, output and `requires` are not known, so its misses need a look, not a fix); `box.py` (usage in its
header) counts challenge boxes on a lab page in headless Chromium. Working rules: every bot run uses `--test --fast`; long waits go to a sub-agent with a
short brief and one blocking wait loop; bots stay lab-only (decided 2026-10-02: challenges are solved by hand, one
solve each per pack); student commands that must reach achievements run in an interactive zsh (tmux), not `zsh -lc`.

### Answers of 2026-10-02


| Question | Answer |
|---|---|
| Reset button | Yes, a full **Reset environment** button on `/admin` (RV38), with Release all as its first step. Nothing may persist past `./dojo stop` |
| Shared helpers (RV20/RV21) | One copy in `modules/_shared/`, copied into `<context>/_shared/` at build time (`SHARED=` in `module.env`) |
| Shared-repo changes on reset (2026-10-03) | Left alone: a student reset never touches what they changed in a shared repo (e.g. dns-as-code `<user>-app` records in `dojo.test` stay) |
| Next workshop | Cloud-Policy-as-Code (RV35), merged to `main` in PR #8 (2026-10-03) |

### Student reset build status

The facilitator resets one student's whole environment. Design: `docs/archive/STUDENT-RESET-PLAN.md`; settled
decisions in [Reference](#student-reset-decisions). **Status 2026-10-02: everything is built; engine plus achievements
passed live on git-fundamentals; the module hooks have since run live (2026-10-03/04); left: 5.1.2.**

| ID | Work | Status |
|---|---|---|
| R0 | Spikes | Done live on git-fundamentals: a reset takes 3-5 s; Forgejo lets the name be made again at once; the new token reaches git; a bot restarts from round 1. Found: **purge** deleted the student's merged PRs, against Q5, so the teardown now deletes their own repos, leaves the org, and deletes the account without purge (falls back to purge if refused, and says so). Not yet live |
| R1 | Engine machinery and Roster UI | Live on git-fundamentals. Added 2026-10-02: `resets` entries may be `"optional": true` (a checkbox in the dialog, off by default, sent as `optional=<ids>`); the terminal reset also removes the student's crontab |
| R2 | Hook contract | Docs in `workshops/README.md` (incl. `optional`) |
| R3.1 | dojo-cloud | Built: `/_dojo/reset/<user>` on cloud-api, teardown through `Portal._purge` and its policy objects (`policy_api.purge`, added with RV35; live: 2026-10-04) |
| R3.2 | openbao | Built: `openbao-reset` relay; `openbao-setup` stays up and runs reset jobs with its own token (the token never moves, unlike R9's wording); one-user mode in `10-tenancy.sh`, `20-ci.sh`, `30-platform.sh` |
| R3.3 | runners | Built: runner-pool stops runners busy with the student's own repos (`/spool/kill/`) |
| R3.4 | vault apps | Built: app-host empties both slots and locks the capstone slot; app-db drops and remakes the student's database (through app-host) |
| R3.5 | DNS packs | Built: dns-gate deletes zones at/under `<user>.<parent>` and their names in shared zones, then re-creates `DNS_GATE_RESET_RECORDS` (cert-autorenewal sets its two seeded A records); cert-autorenewal's webroot moved to `account.d`, with a `reset.d` that removes the old site. Shared-repo records stay by decision (2026-10-03) |
| R3.6 | achievements | Built and live: `achievements-progress` (forgets seeds, watches, half-done two-step checks, Sensei activity) and optional `achievements-score` |
| R4.1 | Docs | Done: `engine/README.md` "Reset a student", `workshops/README.md`, dns-gate and openbao READMEs |
| R4.2 | Live pass per workshop | Done for every hook; left: 5.1.2 |


### Student reset decisions

**Decisions set so far**

| ID | Decision |
|---|---|
| R2 | One student goes back to how they were at stack start; others never notice |
| R3 | The engine orchestrates and resets engine-owned state (terminal home, Forgejo); modules and workshops reset their own state through hooks they declare |
| R4 | A reset keeps the seat |
| R5 | Idempotent and re-runnable |
| R6 | Shared state is not rolled back (a reset may remove what the student owns inside it) |
| R7 | Facilitator-only, per student, typed confirmation |
| R8 | One worker thread in the allocator |
| R9 | OpenBao reset uses a narrow reset token held only in memory by a new resident `openbao-reset` service (minted in remediation T5.3's root window; not the unseal key, not the provisioner token) |
| R10 | `provision-account.sh` first (done), then hardening inside it (done), then the rest |
| D11 | Stays: no long-lived provisioner token |

**Answered by the user (2026-10-01)**

| ID | Answer |
|---|---|
| Q1 | No "reset and release" for now; it can be a second Roster item later |
| Q3 | Shared DNS zone: use the `<author>-...` record naming Sensei's approve mode already enforces; a reset removes the records named after the student |
| Q4 | Accept code-server's browser UI state (cosmetic) |
| Q5 | Shared org repo: close the student's open PRs and delete their branches; leave comments and merged history alone |
| Q6 | Forgejo re-provision: two API calls from the allocator (no bootstrap image needed mid-class) |
| Q7 | Facilitator only (as R7) |

### Achievements design

**Working notes.** Tests: `cd modules/achievements/service && python3 -B -m unittest test_server test_service`;
catalog: `cd ../catalog && python3 -B -m unittest test_catalog`. Logins: class `student` / `student` (POST form on
`/login`, then enter a name); facilitator `admin` / `admin` locally. Post a test event from inside the service
container (`podman exec workshop_achievements python3 ...`, sign with `guards.sign(GATEWAY_TOKEN, user, event, ts,
nonce)`; a nonce can only be used once).

#### Decisions (all settled; IDs are stable, refer to them in commits)

| ID | Area | Decision |
|---|---|---|
| A0 | Toggle | `ACHIEVEMENTS_ENABLED` in `.env`; off means no module, no toasts, no leaderboard, nothing extra loaded |
| A1 | Toasts | Two student modes over the same routes: *split mode* (today's pages, Chrome split screen still works) and opt-in *workspace mode* (`/workspace`, tabbed like `/admin`, portal button, remembered per browser). Toasts appear in the workspace shell (all tabs); portal, lab reader and slides through a same-origin `<script src>`; VS Code through a small bundled code-server extension; Forgejo through its `custom/header` template. No gateway body rewriting. The terminal gets the unlock echoed in colour. Surfaces we can't wire (OpenBao UI etc.) use queued toasts. The landing page shows score and the last 5-10 unlocks |
| A2 | Engine edits | Everything else lives in `modules/achievements/`, the packs and `workshops/assets/`. The engine gets: (1) `dojo` adds `achievements` to the module list when the toggle is on (about 10 lines) and warns if the workshop has no catalog; (2) `render_extensions.py` + `server.py`: a generic `widgets` manifest key (a same-origin `src` framed on the student's landing page: score, completion %, Workshop-complete banner, last 10 unlocks; fixed-template like cards, no raw HTML), the portal's "Open workspace" button and `/workspace`; (3) `engine/presentation/engine.js`: one script tag so slides show toasts; (4) docs in `engine/README.md` and `workshops/README.md`. **No** engine change expected for the shell hook and colour echo, `dojo-check`, student identity, the Forgejo webhook and toast template, the VS Code extension, or the lab reader |
| A3 | Checking | Students run only a thin `dojo-check N` client (no answers in it). The service holds the catalog and checks with its own credentials on networks students can't reach, so a pass can't be posted by hand. Identity: `dojo-check` sends the student's own Forgejo token and the service asks Forgejo who it is (no new token file, no change to `provision-account.sh`). Verifiers (state, for challenges) and event adapters (activity, for milestones) are shipped by the modules that own a backend (A22) |
| A4 | Points | Defaults, settable in `.env` (so `stop` can read them; never `${VAR:?}` in a fragment): milestone 10, funny 0, challenge 100, capstone 300, first blood +25 (capstone +50), class-clear +10 for everyone once the whole class has cleared a challenge. Each hint costs `ACHIEVEMENTS_HINT_PERCENT` (default 25) of the challenge's points, `floor(points * pct / 100)`; after 2 hints the student may reveal the answer and scores 0 for it (it still counts as completed). Score never drops below 0 from hints. Points are awarded once per unlock. First blood, class-clear and the cheater penalty are each switchable |
| A5 | Kinds | *Milestones* fire when the student does something; *challenges* are goal-only and checked by outcome. **One capstone per workshop**, worth more, with a badge tier |
| A6 | Completion (A15) | Based on milestones tagged `core` only, at `ACHIEVEMENTS_COMPLETION_PERCENT` of them (default 80). **Every lab is mandatory**, so every lab milestone is `core`; challenges, capstone and funny unlocks are bonuses and never count. The student's home page shows a running completion percentage and, at completion, a **Workshop complete** banner. |
| A7 | Cheating (A14) | Each fires once per student, none worth more than -1: hand-posted event -1 ("Nice Try, Hackerman"); edited `dojo-check` (client hash mismatch) -1; another student's identity headers -1 ("Identity Crisis"); button masher (rate limit) 0 but shows; poking another student's space: ladder "Oops, you bumped into your neighbour" (0) -> "Curiosity Killed the Cat" (0) -> a related follow-up worth -1 if they keep at it. Honest mistakes must not trip the penalty tiers (thresholds 1/3/8 strikes). These unlocks are shared across workshops and live with the module |
| A8 | Export | Printable HTML `/certificate` (landscape print CSS, browser "Print to PDF", no PDF library). Page 1 the certificate (display name, workshop, class date, points, rank, facilitator signature line from `.env` or blank); page 2 the achievement summary (every unlock with date, challenges cleared with or without hints, any cheater tiers). The certificate is issued on **completion**, not the capstone; the capstone makes it fancier. Also a **badge PNG** drawn client-side on a `<canvas>` (no Credly branding), one design per workshop, two tiers (completion; capstone with stars). Facilitator can override completion in `/admin` |
| A9 | Board | Whole class shown, no top-N. Toasts are only ever for the student's own unlocks (a class-clear bonus arrives as an ordinary personal toast). Sorted by points, ties by who got there first. Facilitator awards and resets change the score directly and are logged. Facilitator sees everything (`/admin` tab): can award manually, reset scores, see the log of check runs (who, when, pass or fail, hints used) |
| A13 | Queue | An unlock is shown once, on the first toast-capable surface that picks it up; the landing page list is the permanent record. The terminal echo does not count as delivered. More than 5 queued collapse into one toast ("You unlocked 6 achievements") linking to the landing page |
| A16 | Names | Export name flow: a dialog asks what to put on it: their current display name, or a typed name or email (offers the part before the `@`). Real names and emails stay on the student's own pages and downloads, stored only in the module volume (wiped by `stop`), never in `/admin`. **Anonymous board** (`ACHIEVEMENTS_ANONYMOUS`): each student gets a unique funny generated name (WildCrab, SpeedyTurtle) for the run, sees "you" highlighted, others can't tell who is who; the facilitator's `/admin` view shows the real mapping |
| A17 | Catalog format | **Modular data, see below.** Supersedes the earlier single `achievements.json` |
| A18 | Challenge seeding | On demand, per student: `dojo-challenge start N` (the command every lab section leads with, 2026-10-12; the lab's **Start challenge** box only builds the repo server-side, since a browser cannot clone into the terminal) creates the student's own challenge repo `{user}/challenge-repo` (student has write access) with seeded commits, branches and per-student values, and clones it into `~/lab`. **Reset** (`dojo-challenge reset N`, also a button) deletes and re-creates it, unlimited times. Hints already used stay counted; points are earned once (only the first clear scores, hints only ever cost) |
| A19 | Sensei bot | Auto-merges the Lab 1 roster PR only (challenge PRs stay the student's own, so bot comments never give hints). Switchable on its own. Reviews each roster PR against catalog rules (allowed files, YAML parses, the student's entry present, nothing else deleted); a good PR is merged through the Forgejo API with a friendly comment, a bad one gets a review comment and is not merged. `/admin` tab lists every PR (auto-merged, waiting, failing and why, minutes stuck) with "merge anyway" and "comment". Stale roster branches are merged with `main` by the bot |
| A20 | **Isolation rules** | Every challenge and capstone: (1) writes only to a space keyed on `{user}`; (2) verifies only that space; (3) depends on no other student (a seeded bot or the facilitator is allowed, only where truly required); (4) changes no shared config (CA lifetime, quota, policy, branch protection, shared zones); (5) has a per-student seed created when opened; (6) is independent of the other challenges (a pass is recorded when checked and never undone by later clean-up). The catalog validator enforces what it can (every challenge declares `space`, every verify assertion is `{user}`-templated, no `peer` dependency unless `facilitator: true`). Full text in `workshops/git-fundamentals/ACHIEVEMENTS.md` |
| A21 | Modular catalog | See "Catalog layout" below |
| A22 | Extension points | Anything that talks to a backend is a **module-owned plug-in**, so a new workshop or module adds achievements without touching the service: verifier verbs, event adapters and seed builders are declared in the owning module's `achievements/` folder |
| A23 | Test approach | Unit tests first for every pure piece (loader, points, queue, names); a live `--test` demo-bot pass per phase; a class-sized concurrency pass (bots doing the same challenge at once, nobody's check affected by anyone else's) before any pack is called done |
| A24 | vault capstone slot | A second app slot per student, `{user}-capstone`, unlocked by `dojo-challenge start capstone`; the lab app keeps running |
| A25 | Challenge repo | One public repo `{user}/challenge-repo` under each student's account for every challenge; only its owner can push |
| A26 | dns-as-code review PR | Sensei only *opens* the `dns-bot` review PR (`SENSEI_SEED`), never approves or merges it |
| A27 | Scope of a score | Individuals only: people may work together, but the lab and the achievements are each student's own |
| A28 | Storage and reset | State lives in a named module volume: it survives restarts within a class and `./dojo stop` removes it. The facilitator's student reset (see [Student reset](#student-reset-build-status)) can clear or keep that student's achievements, their choice at reset time |
| A29 | Branching | `feat/achievements` was cut from `feat/front-door` (both front-door and remediation reached `main` in PR #4, 2026-09-29). The student workspace page is built first (phase 1b) because it is useful with achievements off |
| A30 | Funny unlocks and the Moments table | **Funny unlocks are worth 0 points** (`ACHIEVEMENTS_FUNNY_POINTS`, default 0, only the person launching the lab can raise it) so they never help a score; they just call you out. Each student's landing page has its own **Moments** table, shown only once they have unlocked one: title, the joke, what they did to earn it (the catalog's `when`) and when. It is private to that student (not on the leaderboard, not in anyone else's view), appears in the certificate's summary page, and the facilitator's `/admin` view lists a student's moments too. A funny event still toasts (5 s, no points shown). **Cheating still subtracts** (A7: -1 at most). The catalog validator refuses a positive `points` on a funny unlock or a cheat. |

#### Catalog layout (A17/A21)

Goal: edit one achievement, one lab or one challenge later without touching the rest, and without code changes for a
reworded joke, a changed point value or a new milestone.

```text
workshops/<name>/achievements/
  catalog.json          # workshop id, title, badge art, completion percent (optional override), lab order
  labs/lab1.json ...    # one file per lab: its milestones
  funny.json            # workshop-specific funny unlocks
  challenges/c1.json .. # one file per challenge: goal, hints, answer, space, seed, verify
  capstone.json
  seeds/                # files the seed builders copy (repo skeleton, zone file, tf starter)
modules/achievements/catalog/shared.json     # cheating tiers, cross-workshop funny unlocks
modules/<module>/achievements/verifiers.json # verb names, arguments and the check the module implements
modules/<module>/achievements/events.json    # event adapters the module ships (audit streams, webhooks)
```

- **An item** is `{id, title, joke, points?, core?, when, match?}`. `when` is the human text shown in the review
  markdown; `match` is the structured trigger (`{"source":"shell","cmd":"git commit","exit":0}`, or
  `{"source":"forgejo","event":"pull_request","action":"opened"}`). An item with no `match` is listed but never fires,
  and the validator says so as a warning (an error for a pack with `require_match`).
- **`id` is forever.** Never reused or renamed once a class may have earned it; an item is removed by setting
  `"retired": true` (kept for scoring history, hidden from new classes). A student's earned unlocks are keyed by id,
  so editing the catalog mid-class is safe: new ids appear, retired ones keep their points.
- **Points** come from the kind's default (A4) unless the item sets `points`. `core` is only valid on milestones.
- **Validation at start**, like `extensions.json`: unknown fields, duplicate ids, missing goal/hints/answer, a challenge
  without `space` or with an un-templated assertion, an unknown verifier verb (checked against the modules in this run),
  a `match` source no listed module provides. An error stops the run; warnings print.
- **`ACHIEVEMENTS.md` is generated** by `modules/achievements/catalog/render_md.py` from this data, and a unit test
  fails when the committed markdown is stale. Edit the JSON, never the markdown.
- **Reload:** the catalog is read at service start; the facilitator's `/admin` tab has a "Reload catalog" button, so
  a joke or a point change during a class needs no restart and no `stop`.
- `dojo-introduction` is a tour, not a workshop: no achievements.

#### Per-workshop challenge design (isolation applied, 2026-09-29)

Full text is in each `ACHIEVEMENTS.md`.

| Workshop | Where challenges run | Seeds and extras | Facilitator needed? |
|---|---|---|---|
| git-fundamentals | `{user}/challenge-repo`, a seeded fork of `training/sample-training-repo`; merging into its `main` is safe | Per-student fork, planted commits for C2, conflicting branches and a bad commit for the capstone, the linked `{role}`/`{role_typo}` pair and `{target_line}` lists | No |
| dns-as-code | Student's own zone `{user}.dojo.test` and its repo, never `dojo.test` | Doubled-hostname seed (C1), a pushed "good plus bad record" commit (capstone), `10.20.0.{n}` per student, a `dns-bot` PR opened by Sensei for `d3-review` (A26) | No (peer review only in Lab 3, with the `dns-bot` fallback) |
| cert-autorenewal | Student's own vhost dir `/srv/webroot/{user}/` and names under `{user}.certs.dojo.test` (the DNS gate's per-student key already scopes this) | Wildcard A record `*.{user}.certs.dojo.test` to `demo-app`; two extra vhosts made by the student | No |
| tofu-basics | Student's private Dojo Cloud subscription; own folder `~/challenges/cN` with own state; resources tagged `challenge=cN`; every site name has `{user}` (site labels are class-unique) | Starter `main.tf` for C2 (5 names), empty capstone folder, repo `{user}/site-factory`. Capstone is **two** sites (quota is 2 container groups) | No |
| vault-fundamentals | Student's namespace `students/{user}`, database `app_{user}`, own fork and own slot; new role names (`buddy-{user}`, `c2-app`, `capstone-*`) | `buddy-{user}` identity and two secrets, starter `capstone/` folder. The capstone gets a second app slot, `{user}-capstone` (A24) | No |

#### Detection sources

| Source | Catches |
|---|---|
| Forgejo system webhook | push, branch, PR opened or merged, review, tag (with the username) |
| Shell hook (zsh `preexec`/`precmd`) | commands, exit codes, branch, and output through the tmux pane (`out_regex`) |
| Adapters and the `verify` sweep (`openbao-audit`, `cloud-api` events, the CA, Forgejo state) | "the secret exists", "plan is clean", failure unlocks like "First 403" |
| Lab reader page events | opened or finished lab N (weakest source, not used) |

Vault values are HMACed in the audit log, so only path and operation are usable. Challenges check the **outcome**, not
the command. Approximations are written into each item's `when`.

**Test plan (A12).** Unit tests for every pure piece; live `--test` bot runs per pack asserting on the leaderboard
API; a concurrency run (several bots solving the same challenge at once, no one's state changing another's result);
browser screenshots of toasts on every surface, split and workspace modes, the certificate and badge; and, by the
user, a real class or 3-5 person dry run, the tone of the jokes and the printed certificate.
