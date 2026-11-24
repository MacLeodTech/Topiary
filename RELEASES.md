# Releases

What has shipped, newest first. [`ROADMAP.md`](ROADMAP.md) holds what is still open; when an item there is done
and verified, it moves here in a line or two. Detail behind older entries (design, decisions, per-task logs) is in
[`docs/archive/`](docs/archive/), kept for reference and no longer updated.

Entries are grouped by what reached `main`. Dates are commit or merge dates; "locally" means tested on the
WSL2 desktop stack at `http://localhost:8080`.

## OpenTofu 1.13, item 6.3.1 (2026-11-24)

- `tofu-basics`, `cloud-policy-as-code` and `dojo-introduction` pin OpenTofu 1.13.10 (was 1.12.8), with the new SHA256s for amd64 and arm64 in the Dockerfiles; the version text in the tofu-basics lab, slides and mock changed to match.
- Tested without a stack: the 1.13.10 binary planned the cloud-policy-as-code sample repo with the lab 3, 4, 5 and 7 solutions and both achievement seeds. `tofu show -json` came out identical to 1.12.8's apart from `terraform_version` and `timestamp`, and `conftest` (0.71.0) gave the same results on both; `opa test` (1.21.1) passes 8/8. The sample repo's policy failures are the lab's own starting state.
- Not run: the labs inside a built terminal image (no image build), and `tofu-basics` and `srx-terraform` labs on 1.13.

## Comments: invariants, not history, item 4.4 (2026-11-24)

- Fixed the comments that were wrong: `workspace-control.py` says it threads "as the allocator does" (the allocator is a `ThreadingHTTPServer` too) and names tmux sockets under `<runtime dir>/tmux-<uid>/`, not `/tmp`. The `handler.py` keepalive comment was checked and is correct (Caddy's 60 s is under its 65 s).
- Removed the "remediation T..., FIND-.." tags and the "used to be" / "no longer" phrasing from the comments in `docker-compose.yml`, the Caddyfile and the terminal `entrypoint.sh`; each comment keeps its rule. A grep found about ten such phrases, far fewer than the roadmap's "much of it", so no wider rewrite was done.

## Small scale wins, item 1.6 (2026-11-24)

- The code-server idle timeout default is 600 s (was 900; the reconnection grace stays 300 s, below it). The gate's `gate.js` and `gate.css` carry `Cache-Control: public, max-age=600`; everything with a session or a secret keeps `no-store`.
- Checked and left alone, as triaged 2026-11-23: the 5 s and 10 s healthchecks, the 100 MB zellij warning, and `./dojo prune` for dangling images.

## Lab Info primers leak audit, item 6.1.2 (2026-11-24)

- **Method:** every distinctive string each of the 14 `solve.py` scripts sends (payloads, paths, headers, 200-odd literals) was searched for in the 15 primers; then the primers were searched for the telltale terms of each target's technique (injection strings, mass-assignment fields, metadata and file URLs, traversal, tfstate, git history, TLS-skip flags, shells, `docker.sock`) and every hit was read in context. It was a targeted search plus reading the hits, not a line-by-line read of all 15 primers.
- **Found and fixed:** `sqlmap.md` spelled out the `' OR '1'='1` payload style that `sqli-login`'s solve uses; it now describes the idea without the string. `httpie.md` and `jq.md` used a JSON `"role": "user"` / `select(.role == "admin")` example, one step from `api-mass-assignment`'s `PATCH {"role": "admin"}`; they use a `team` field now. No other solve literal appears in any primer (only the generic `/login`, `/admin` and MIME types).
- **Kept on purpose:** `opa.md`'s toy `input.role == "admin"` policy (the policy-bypass lab has no role), and `ncat.md`'s one-line mention of what a reverse shell is (no command).
- **Stays fixed:** `modules/ctf-range/test_labinfo.py` runs in CI: no solve payload in a primer, the removed phrases stay out, no HTTP-tool primer shows a `role` field. It fails against the old `sqlmap.md` and `httpie.md`.

## Bot lab steps out of the engine, item 4.5 (2026-11-24)

- `step_lab1_*` to `step_lab5_*` and the persona `STEPS` lists moved from `engine/web-terminal/bot-runner.sh` (769 to 528 lines) into `workshops/git-fundamentals/content/bots/steps.sh`. The engine keeps the framework (`run_cmd`, `think`, `narrate`, state, portal login) and the steps several packs share (`step_ensure_clone`, `step_sync_main`, `step_wrap_round`, `cleanup_merged_pr`). The pack's `eval`/rename of `step_lab4_history` is gone: the sample-repo walk is `gf_sample_repo_lab4_history`, the fallback when `lab-history` is missing.
- **Behaviour change for ctf-defend:** it ships no `steps.sh` and used to fall back to the git-fundamentals steps. Nothing documents that as intended (its bots are the attacker swarm), so the new engine default applies: no steps, the bot says so, writes `~/.dojo-bot-done` and idles. Give it a `steps.sh` if git noise on its sample repos is wanted.
- Tested: `bash -n`, dojo suite, `./dojo validate`. Live: `git-fundamentals --test 3 --fast` (all three personas done, expert through Lab 5, intermediate through Lab 4, novice through Lab 2), `dns-as-code --test 2 --fast` (done, no skipped steps), and the no-steps path run directly.

## `workspace-control.py` split into a package, item 4.1 (2026-11-24)

- The 1124-line file is now `engine/web-terminal/workspace_control/`: `config` (env, ports, sizing flags), `state` (what is running, locks, `audit`, names and ports), `procs`, `ports` (listeners, squat sweep), `namespaces` (holder, nproc prefix), `sessions` (tmux/zellij, watch), `workspaces` (start/stop), `accounts` (reset and hooks), `reaper` and `handler` (the HTTP handler and `main`). Every module is under 300 lines (a test keeps it that way). `workspace-control.py` is a 3-line entry point at the same path, so the image's command and healthcheck did not change; the Dockerfile copies the package next to it.
- Code was moved by script from the AST, not retyped. The only edit: a method-local `import json` in the handler went, because the module now imports it at the top. The comment cleanup (4.4) is still a separate item.
- Tests: the three existing suites now patch each name in the module that uses it (e.g. the status tests patch `handler.is_alive`), plus a package smoke test (modules import, the entry point only hands over, `subprocess.Popen` is the reaper's). Web terminal unit tests 30 OK, ruff clean.
- Live: `git-fundamentals --test 3 --fast` (all done, container healthy with 0 restarts, no zombies, roster active) and `--terminal zellij --test 2 --fast` (same), plus a confirmed reset of a bot through the new `accounts.py` (`reset-done`, `ok: true`).

## `./dojo stop --with-repos`, rest of item 3.6 (2026-11-24)

- `./dojo stop --with-repos` (and `down`) also copies every Forgejo repository, the org's and each student's, with full history, into `results/<run>/repos/<owner>/<name>.git`, and records the count in `manifest.json`. It streams one `tar` out of the git server's own container (no Forgejo credentials) and extracts it with Python's `data` filter, so a hostile member cannot write outside the folder. It runs last; a failure is noted under `skipped` and never costs the rest or blocks the stop. Off by default because it can be large.
- Tested: 6 new unit tests (layout, the exact `exec` command, an escaping member, a tar failure, flag off and on, failure noted). Live: `git-fundamentals --test 2 --fast`, `stop --with-repos` saved 3 repos; a saved bot repo cloned and showed the bot's merged "Release both features" PR.

## Result exports through a module hook, item 3.6 (2026-11-24)

- A new `exports` kind in `extensions.json` (`id`, `label`, `upstream`, `path`, `file`, optional `timeout` and `count`), validated by `render_extensions.py` like `resets`. `./dojo stop` fetches each one as the facilitator from inside the service's own container and saves it as `results/<run>/<file>`; a failure goes under `skipped` in `manifest.json` and never blocks the stop. The engine names no module any more (`archive.py` no longer mentions feedback or achievements; `export-feedback` and `export-results` stay as module-named commands in `results.py`).
- Differs from the brief: no separate `EXPORT_TOKEN_<SERVICE>`. The facilitator-gated endpoints the modules already have are reached with the same container-side call as `export-results`, so a new token would only be a second copy of the same trust.
- feedback declares its two exports and achievements three (state, its own CSV, the SOC feed). `achievements.json` is now the service's full state and `achievements.csv` the module's own columns (adds `done`/`total`). `manifest.json` has `counts` (per export that declares `count`) instead of `feedback_answers` and `students_with_progress`.
- Tested: 8 new renderer tests, `test_archive` rewritten around fake exports (7), all suites, ruff, mypy. Live: `ACHIEVEMENTS_ENABLED=1 git-fundamentals --test 2 --fast`, then `./dojo stop` saved `achievements.json`, `achievements.csv`, `achievements-soc.json`, `feedback.json`, `feedback.csv` and `roster.csv`.

## `doctor --live`, item 3.4 (2026-11-24)

- `./dojo doctor [workshop] --live [--students N] [--pass CODE]` adds the public-run rules from the 2026-10-18 P15 design (`engine/dojo/livecheck.py`): empty and short passwords, a missing `STUDENT_PASSWORD_SEED`, the facilitator password equal to a student secret, a short access code, CTF tokens that are empty or derived from an empty gateway token, the terminal's memory for N students, a workshop file that lowers your sizing (named with its file; a failure when below the class's need), and the workshop's terminal image not built. Unlimited cgroups, plain HTTP and a missing seed become failures. On a loopback-only machine the secret rules are warnings. It changes nothing.
- A low pids cap is information, not a failure: the start already raises it (`sizing.fit_pids`). The P15 table's "start refuses" columns were not built; only doctor changed.
- Tested: 14 new unit tests (`tests/test_livecheck.py`), the dojo suite (184), ruff and mypy; run on git-fundamentals and cloud-policy-as-code (reports its `workshop.env` 6g override).

## Per-pod netlab management networks, item 3.3 (2026-11-24)

- Each pod now has its own internal management network `netlab_mgmt_NN` (`10.80.(N+1).0/24`, written by `modules/netlab/generate.py`), so root on a node can no longer ARP-spoof or reach another pod. The terminal, checker and view join every pod network and get node names from generated `extra_hosts` (a container on this many networks has more DNS servers than libc reads).
- `netlab_fw.py` firewalls by pod `/24` and drops new inbound connections on every pod interface; node addresses, the two `hostkeys.py` copies and the view follow the new scheme.
- Tests: new `PerPodManagement` and `InputRulesForManyPods` cases; an older "own networks only" test had been matching nothing and now asserts. All unit suites pass.
- Live (`netlab-ansible --test 2 --fast`, 76 s to healthy): a pod 01 node reaches its own pod and the shared services, not pod 02; the terminal and checker resolve node names; one inbound rule per pod; ansible runs across the new networks; bot 2 finished all labs.

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

## E8 revocable, shorter facilitator session (2026-11-24)

- Cookies carry a per-account epoch; a facilitator `/logout` bumps it (kept in `session-epochs.json` in the allocator volume, survives restarts), so every facilitator cookie dies; class and bot cookies are untouched. Facilitator lifetime is 4 h (`general.facilitator_session_hours`), class stays 12 h. Unit tests added (199 allocator, 170 dojo OK). Live on git-fundamentals: two facilitator cookies both worked, logout on one made both 401, class cookie unaffected, a new sign-in worked, epoch persisted across an allocator restart.

## CI additions, item 4.6 (2026-11-24)

- **Gating jobs:** `python-lint` (ruff `E9,F` over `engine/` and `modules/`, config in `ruff.toml`) and `python-types` (mypy over `engine/dojo`, 25 findings fixed). Both pin their tool versions.
- **Caddy rule:** `caddy-lint.py` fails when a `keepalive` in the Caddyfile is not below the allocator's `IDLE_TIMEOUT` (the E1 invariant).
- **Real bugs ruff found:** a duplicate `student_reset` in `modules/dojo-cloud/cloud-api/server.py` (the first was dead) and a duplicated `IndexTest` class in `ctf-controller` whose first copy never ran.
- Tested: `ruff check engine modules` clean, `mypy -p dojo` clean, `./dojo` suite 170 OK.

## E11 route table in the allocator, item 4.2 (2026-11-24)

- `do_GET` and `do_POST` in `engine/allocator/handler.py` are now one dispatcher (`serve`) over `GET_ROUTES`/`POST_ROUTES` (exact paths) and a short prefix list. The gateway-token check, the `/admin` facilitator gate and the `X-Requested-With` check each run once (a route's `xrw` flag); the forgejo-password route's own copy of that check is gone. Exact-path matching is kept, so `/x/../admin` is a 404.
- **Test first:** `tests/test_routes.py` records the status of 176 (method, path, role) combinations (anonymous, class, facilitator, facilitator with the header) from the old code; it passes unchanged on the new. Allocator suite 197 OK. Not run on a live stack: the test drives the real HTTP server.

## Caddyfile snippets, item 4.3 (2026-11-24)

- The access-code matchers (`@needgate`, `@gateprobe_bad`, `@gateprobe_no`, `@gatebad`) import two snippets, `gate_needs_code` and `gate_wrong_code`, instead of repeating the same two cookie rules. `@ide`/`@term` already shared the `tool_route` snippet.
- Tested: `caddy adapt` of the old and new Caddyfile gives the same JSON (apart from the file name Caddy records), with and without a gate code.

## Phase 1 engine fixes E1-E4 (2026-11-23, branch `fix/phase1-quick-fixes`, not merged)

- **E1:** the allocator waits 65 s for the next request on an idle kept-alive connection (3 s still covers a request's line, headers and body), so it never closes one before Caddy's 60 s keepalive drops it.
- **E2:** wrong passwords on the shared class account no longer feed the per-account guard; the per-address limit (60 a minute) still applies.
- **E3:** the gateway runs with `no-new-privileges`, a read-only root (named `gateway_data` and `gateway_config` volumes, `/tmp` tmpfs) and a 512 pids limit. Untested: a `PUBLIC_BASE_URL` port below 1024.
- **E4:** the Forgejo password reveal is a POST with the `X-Requested-With` check; a GET answers 404.
- Tested: allocator suite 191 OK, `./dojo` suite 170 OK; locally, `git-fundamentals --test 3 --fast` on port 8081: gateway healthy and read-only, 3 bots finished, reveal GET 404 / POST without header 403 / POST with it 200, class login 303 after 8 wrong guesses.
- **Item 1.7 (2026-11-23):** unit tests for `dojo netlab check` (`modules/netlab/test_netlab_cmd.py`), `dojo wan` (`modules/wan-cloud/test_wan_cmd.py`) and the ctf-defend inline `dojo-check` wrapper (`workshops/ctf-defend/test_dojo_check_wrapper.py`, cut from the Dockerfile as written). The healthcheck audit found none missing: dns-api (dns-gate), zone-viewer, dns-admin, cloud-api and wan-api set a `HEALTHCHECK` in their Dockerfiles, and openbao in compose.
- **Load test baseline (2026-11-23, 2.1 part one):** `tools/loadtest.py`, 30 students holding real slots on the Zellij flavor (`./dojo students 30`, then restored), all opening `/term/` at once, then 60 s of polling (portal and `/term/` every 3 s). Result before E5/E6: no 5xx; the burst of 30 first opens took p50 1.9 s, max 2.3 s (all 200); steady `/term/` p50 13 ms, p95 39 ms, max 111 ms; portal p95 50 ms. Slot assignment is rate-limited (10 at once, then 20 a minute), so a 30-student class takes about 1 minute to all get in. Limits: the polled page is one `/term/` request, not a real ttyd page's assets, and the allocator's audit log dedupes `auth-check` lines, so the call count (the thing E5 halves) is not measured yet.
- **E5 and E6 (2026-11-23, branch `fix/phase1-quick-fixes`, not merged):**
  - **E5:** `/ide` and `/term` skip `session_gate`; `/auth-check` reads the signed `dojo_login` cookie itself and ignores `X-Auth-User`/`X-Session-User` from the client (a page load without sign-in still redirects to `/login?next=`). `tool_route` is now one Caddy snippet for both routes. New `/admin/api/stats` (facilitator only) counts requests per route.
  - **E6:** the ready cache keeps an answer `READY_TTL_S` (15 s) instead of 2 s. The brief's idea of replacing `port_open`'s scan with a `connect()` was dropped: the scan also finds a process squatting on a student's port, which is the defence. A workspace that dies inside the window gives a 502 until the entry expires.
  - **Measured** (30 students on Zellij, `/term/`, 60 s of polling; before to after): allocator `/session-check` calls 1420 to 790 (exactly the 630 `/term/` requests), so gate calls per run 2050 to 1420 (31% fewer, one call per `/term` request instead of two); steady `/term/` p50 14 to 6 ms, p95 33 to 22 ms; no 5xx either time. First-open burst p50 1.5 s before, 2.1 s after (workspace start, varies run to run). Not measured: the drop in control calls from the longer ready cache (the allocator's own outgoing calls are not counted).
  - **`/ide` after E5/E6** (10 code-server students, 45 s of polling): no 5xx; first open p50 193 ms (all 200); the steady `/ide/` request answers 302 (code-server's own redirect, so it is not a 200); `/session-check` 171 (the portal's 150 plus sign-ins), `/auth-check` 160, i.e. one allocator call per `/ide` request. The facilitator's `/ide/` returned 200. Killing the facilitator's code-server with `pkill` gave no 502 in 40 s of polling (302 throughout), so either it restarted at once or the kill missed: the E6 trade-off is **not** measured. No "before" for `/ide`.
  - **Live E5 checks:** forged `X-Session-User: admin` with no sign-in gets 401; a page load with none gets 303 to `/login?next=%2Fterm%2F`; the facilitator's `/term/` returns 200. Allocator suite 195 OK.

## Live checks of 2026-10-03/04 (moved here from ROADMAP's "Now" section, 2026-11-23)

The finished part of the old roadmap's "Now" section, kept as it was. What was still open (the Ubuntu WSL/Docker run, the browser looks, closing out student reset) is in ROADMAP Phase 5.

**netlab full-size class run (2026-11-06, locally, rootless podman; moved from ROADMAP 2026-11-23).** with 14 `--fast` bots plus one student account = 15 pods (demo bots get pods too, so `--test 15` is refused): start 13m17s (compose 8m42s), 142 containers, idle memory 2.5 GB used of 14 GB, all 14 bots finished round 1, slides clean on 5 pages, stop 7m10s. testuser12's A10 skip was a kv-v2 mount "upgrading" 400 outlasting the bot's 24 s retry (fixed: 2 min, write and read-back together); the A11 check was vacuous and now asserts the capstone state on both branches (unit-tested, not yet run on a stack).


| Check | Stack | What to confirm |
|---|---|---|
| Vault reset | `vault-fundamentals --test 2 --fast` | **Fixed 2026-10-03** (`fix/vault-reset`): app-db's worker was started with `su-exec`, which the Postgres image no longer has (now `gosu`), and `kv_wipe` failed on an already-empty folder (`bao list -format=json` says `{}`). Two resets in a row of testuser1 passed all 12 steps, locally, and `lab_11.sh` (12 checks) and `lab_12.sh` (9) passed after a reset (rootful Podman on macOS needs `RUNNER_POOL_SECURITY_OPT_1/2` in `.env` for the pool and app-host; `openbao-setup` needed more than 64m). Left: run `vault-fundamentals --test 2 --fast` once on the Ubuntu WSL/Docker host with the two variables unset, to confirm the repeated `no-new-privileges:true` changes nothing there |
| Cloud reset + capstone | `tofu-basics --test 2 --fast` | **Both halves passed 2026-10-04 on the Mac (rootful Podman).** Reset with a non-empty pre-state: testuser1 and testuser2 each given one Running container group, reset of testuser1 ran 9 steps all ok, `dojo-cloud-teardown: removed 1 container group(s), 1 resource group(s)`; afterwards testuser1's was gone, testuser2's still Running, and testuser1's bot restarted from round 1 (so a fresh `ci-hello-dev` appears — don't read that as the old one surviving). Capstone two-step as `student01` (not a bot: bot accounts have no `credential.helper`, so they cannot push outside the bot runner's `GIT_ASKPASS`): two sites from one `for_each` → "Halfway", `tofu destroy` → "Passed! +300". Left: nothing here — the `policyObjects` sub-item became its own finding below |
| Vault capstone two-step | vault stack | **Passed 2026-10-04** (needs `ACHIEVEMENTS_ENABLED=1`; it was 0, so `dojo-check`/`dojo-challenge` were not in the terminal image at all). "Halfway" → rotate `capstone/app` with no push → "Passed! +300", and a push in between answers "main of `<user>`/capstone changed after step 1 passed (a push deploys). Back to step 1". The push case only holds with a gap of more than a second — see the `no_push_since_step` finding below |
| Browser looks (user) | any | Widget frame full height on first load; the Reset dialog's "Also clear their achievements and score" checkbox |

Slide overflow checker: `workshops/assets/slide-overflow.sh <workshop> [page.md ...]`. It timed out after login on dns-as-code (it waited for
`networkidle`, but the portal polls); fixed 2026-10-03 and clean on git-fundamentals (5 pages). **Run on dns-as-code 2026-10-04: the
fix holds (no timeout), and it found 2 overflows** — `cheat-sheet.md` slide 6 `<table>` 110 px past (the `doctor` command table) and
`presentation.md` slide 11 `<p>` 34 px past. Also run on vault-fundamentals the same day (not asked for, but the stack was up):
`index.md`, `lab-index.md` and `labs.md` clean, **`presentation.md` over on 5 slides** — 8 `<li>` 45 px, 10 `<li>` 5 px, 21 `<p>` 10 px,
31 `<p>` 10 px, 49 `<p>` 12 px. So 7 slides across two decks need trimming; the checker itself is now proven on three packs.

Passed 2026-10-03: DNS reset (no purge, PRs kept as Ghost, zone gone, shared records kept, second reset ok), cert reset
(crontab gone, two seeded records, clean reload; the pre-state was not captured) and dojo-introduction `--test 5 --fast` (no skips).

Passed 2026-10-04 (all on the Mac, rootful Podman): the cloud reset and both capstone two-steps above, the dns-as-code slide run,
and dojo-introduction `--test 5 --fast` again now that the bot steps check their results — 5 bots, all 5 finished round 1,
**0 skips and 0 retries** (a skip prints `FAST: <step> failed N times -- skipping it`). The only gateway error in that run was a
single startup 502 on `/slides/` before the presentation container served, after which the stack reached 17 of 17 ready.

Both of the 2026-10-04 findings below are **fixed** (`418d5ad`, unit-tested, no stack needed — see RELEASES.md).

## Dojo Cloud: container creates survive a class-sized burst (2026-11-05, `fix/cloud-create-burst`)

Locally. cloud-policy-as-code stalled with 20 bots in Lab 0's first apply: dockerd in cloud-host answered the burst of
creates after cloud-api's 30 s socket timeout, finished the container anyway (left `Created`), and every retried PUT
then failed on a 409 name conflict, so `apply` said "Still creating..." for good (not a resource limit: 2.7% CPU,
210 of 4096 pids). `docker_api.Executor.create` now waits 120 s, lets 4 creates reach dockerd at a time, removes the
container by name when a create or start fails, and clears a leftover of the same name and creates again on a 409
(6 new tests in `test_executor.py`). Rerun with `--test 20 --fast`: all 20 bots done in about 50 min, Lab 0's apply
done for all 20 within 4 min, no executor errors, no 409s, no 500s.

## Lab reader copy buttons, vault bot blocks, code-server 4.145.0, srx-terraform T6 (2026-11-05, `feat/srx-terraform`)

Locally. **Copy buttons:** every code block in the shared lab reader (all workshops, reveal bodies included, not diagrams) has a Copy button, with an `execCommand` fallback when the clipboard API is refused; Playwright: 16 blocks/16 buttons on vault Lab 5, clipboard text equals the block, the button stays put when a wide block scrolls, no overflow at 390 px. **Vault bot:** `vf_block` and the tests' `md_blocks` counted only ```` ```bash ```` fences after the labs moved to ```` ```sh ````, and blocks had merged; every call is renumbered by content (`--test 2 --fast`: 0 `IndexError`s). **code-server 4.137.0 -> 4.145.0** (not the planned 4.141.0: GHSA-gcvg-jpfh-4xm8 and GHSA-jvcp-w94c-mvvh); builds, `/ide/` serves the workbench. **srx-terraform T6:** Lab 8 shows the expected `grep` output, Lab 3's portal step names the columns to read, Lab 9 opens its pull request with its own `pr.json` block, Lab 1's predictions say to compare with the reveal, and the unconfirmed "a device's `vars` win" line is gone from Lab 5, the slides and the cheat sheet (fast bot: no failing block through `dojo check 9`; Lab 8 outputs match).

**Vault Lab 2 test and bot retries.** `tests/lab_2.sh` is rewritten for Lab 2's 9 merged blocks (and stops with one line if the student account does not exist); locally 14/14 `ok` as `student01`. The bot wraps `bao` so a transient refusal (the just-enabled kv-v2 mount "Upgrading from non-versioned..." 400, connection refused/reset, 502/503) is retried up to 8 times with its stdin kept, instead of losing `team/app` and Lab 6's rendered `app.env`; real errors still fail at once. `--test 3 --fast`: the wrapper caught one transient `kv put team/app`, all bots done, Lab 6 rendered the rotated password, nothing skipped.

## srx-terraform: load, drift, docs check and rehearsal (2026-11-05, `feat/srx-terraform`)

Closes ROADMAP T5 and most of T4, locally. **Load:** `--test 10 --fast` and `--test 15 --fast` ran Labs 0-9 with no failing block (15 bots in under 4 min; terminal container peak ~310% CPU, 690 MB; `wan-api` ~20 MB; no wan-api errors); `./dojo capacity`'s rule of thumb puts this 13 GB machine at ~12 real students (FACILITATOR.md). **Drift:** clicked live; the per-org button no longer makes an unmanaged policy (invisible to `plan`) in an org with no network, it answers 409 with the reason; a new class-wide **Make drift in every org** (`POST /wan/api/drift`) changes each student org's first VLAN and reports changed/skipped, and `plan` shows `~ vlan_id = "999" -> "10"`; both results now survive the portal's re-render. **Mist docs** (WAN config hierarchy page, JVD WAN Edge for SRX): hubs take profiles and spokes templates, as Lab 5 teaches; a device overrides only DNS and the application policy, so Lab 5's Ottawa override is now DNS (`10.10.0.53`) through Labs 5-9, stages, slides and `srx-check` (live: `dojo check 5` all ok), and the renderer notes a device NTP setting as not applied. The renderer no longer emits an untagged `unit 0` beside `vlan-tagging`. `SRX-REVIEW.md` hands the Junos questions the docs don't settle to an SRX engineer. **Rehearsal:** Playwright read all 12 lab pages and 25 slides as a student (no slide overflow, no broken links or console errors); a student-eye read found 11 text slips, fixed (among them Lab 7 now commits `backend.tf`, live-verified with a fast bot through `dojo check 9`); the shared lab reader's tables now scroll inside themselves on phones (390 px: no page overflow on any lab page). 102 wan-api tests pass.

## srx-terraform pack, first live run (2026-11-04, `feat/srx-terraform`)

`srx-terraform --test 1 --fast` ran Labs 0-9 locally (Terraform 1.17.1, the offline `Juniper/mist` 0.11.0 mirror, the Dojo WAN simulator): all ten `dojo check N` passed, no skips. The wan-api suite (98 tests) and the parity test pass. The bot now follows the lab text (`content/bots/labtext.py`), and that run found and fixed five lab bugs: Lab 5 applied before the hub's inventory entry existed; Lab 6's `profile.tf` edit was prose only; Lab 7's lock demo used `terraform console`, which takes no lock (it now holds an `apply` at its question); Lab 8 left the import on an unmerged branch so Lab 9's first plan destroyed `guest`; and the Lab 6 and Lab 9 plan counts were wrong. All ten `dojo check N` pass and no block fails. This closes roadmap T1-T3: the `wan-api` simulator (with the tested and untested endpoints recorded in the plan's section 9.2), the `wan-cloud` module (the `api.mist.com` network alias resolves under podman's aardvark-dns in the live run) and the Junos renderer and Dojo WAN portal. Lab 5 is now "Roles" everywhere (slides, cheat sheets, `dojo check`), matching the hub/spoke model; the labs overview slide is split in two and two other slides trimmed so each fits 16:9 (checked with Playwright).

## Terminal clipboard and colours in the base image (2026-10-29, `feat/netlab-openbao-vault-lab`)

Every terminal image gets `pbcopy`/`pbpaste` (OSC 52 clipboard, tmux `set-clipboard on`) and the shared One Dark `COLORTERM`/`BAT_THEME` in the base zshrc, for both the code-server and Zellij flavors.

## netlab-ansible lab 5: two repos, two vaults (2026-10-29, `feat/netlab-openbao-vault-lab`)

Lab 5 is now "Secrets with OpenBao": the student makes `fw` and `sw` team vaults (child namespaces of `students/<name>`), and
each of two repos (`fw-repo/`, `sw-repo/`) reads its own vault password through its own `vault-pass.sh`, so no `.vault_pass`
file exists. `netlab-ansible` now loads the `openbao` module and mounts its own `compose/openbao-setup.d/` hooks. `dojo netlab
check 5` checks the nodes (`/etc/fw-admin.conf`, `/etc/sw-mgmt.conf`, mode 600) and, in the terminal, that each script,
`secrets.yml` and vault password works and the two differ. Slides 12 and 35-39 now say where Ansible runs and cover `pass`/`gopass`,
a shared control node with Azure Key Vault (and an OpenBao/Vault pop-out) and the three-persona table. Tested locally with
`./dojo netlab-ansible --test 1 --fast`: lab 5 all 12 checks pass, a second run is `changed=0`, the fw token is refused by the sw vault. Student reset is on (`extensions.json` + `reset.hcl`, tenancy hook in one-user mode); tested locally on `student01` through the Roster route: the `fw`/`sw` namespaces were deleted, `students/student01` re-created, and the student's CLI login still worked.
Not run: labs 6-8 and S1-S3 after the change, the facilitator's `/admin` Vault tab, and the lab text typed by hand in a browser.

## Nosy Neighbour easter egg and `regex_not` (2026-10-28, `feat/netlab-followups`)

vault-fundamentals gets a zero-point easter egg for curling another student's slot app on `app-host` (slot apps are public in the class by
design; token audit of every `workshop_lab` service found no holes). The achievements catalog gains `regex_not` (`{user}` is the student's
own account, so their own slot does not count). Unit tests and a store-level check; not run on a live vault stack.

## netlab-ansible capstone on (2026-10-28, `feat/netlab-followups`)

"Rebuild From Clean" is on. `netlab-checker` answers `POST /proof` (token derived from `GATEWAY_TOKEN`, held only by the checker and the
achievements service) with which labs it last saw pass on a user's pod, and the new achievements verb `netlab_labs_passed`
(`modules/achievements/plugins/netlab`) asks it for labs 0-4, 6 and 8 when a student runs `dojo check capstone`. Tested locally with
`./dojo netlab-ansible --test 3 --fast`: the expert and intermediate bots got the capstone (+300), the novice (labs 0-3 only) was told
which labs the checker had not seen pass, and from the novice's terminal `/proof` without or with a wrong token, `/last`, a spoofed
identity and an unsigned adapter event were all refused. The checker's record is in memory (a checker restart means re-running checks).

## netlab per-uid firewall in the terminal (2026-10-28, `feat/netlab-followups`)

Student N's uid (and demo bot K's, pod STUDENT_COUNT+K) can open connections only to pod N's management addresses on `netlab_mgmt`;
root (the facilitator) and the checker and view containers are unaffected. Nodes now have fixed management addresses (pod N owns
`10.80.1.(8N)`..`(8N+7)`, `netlab_mgmt` is `10.80.0.0/22`), and `terminal/start.d/50-netlab.sh` loads a `NETLAB_ISOLATION` chain on
`OUTPUT` with `iptables-restore`. It fails closed: if the rules cannot be loaded and read back, the terminal does not start. Tested
locally: other pods' SSH ports time out for a student and answer for root, `ansible` and `dojo netlab check` work on the student's own
pod, and both bots finished all labs through the firewall. Not covered: root on one's own node shares the management segment (see
`modules/netlab/README.md`).

## netlab module and the `netlab-ansible` workshop (2026-10-28, `feat/netlab-module`)

`modules/netlab`: per-student pods (pc, VLAN switch, Linux firewall, nginx web node) on internal-only networks, a manual and an
automated branch each, root over SSH with a per-pod derived password, capped at 15 students (bots count). Parts: node image,
`generate.py` hook, terminal image (Ansible, ansible-lint offline), the lab 0-8 and S1-S3 seeds and reference solutions, the
`netlab-checker` service, and the read-only `netlab-view` page (student and facilitator). `workshops/netlab-ansible`: slides, lab
reader pages, `FACILITATOR.md`, 12 achievements milestones (`exit_strict`, so a chained line cannot fake a pass) and demo bots for
the expert, intermediate and novice personas (`--test 3 --fast`). Tested locally: labs 0-8 and S1-S3 pass their checkers and unlock
their milestones; the 3 bots ran end to end; a 12-student start takes about 5 minutes. Fixed on the way: MTU pinned to 1500 on data
ports (a bridge dropped oversized frames), the builder's inherited healthcheck, and the management SSH rule in the fw comparison.

## Earlier

Entries from 2026-10-19 and before (CTF packs, the platform reviews, stable image tags, the first workshops) are in
[`docs/archive/RELEASES-to-2026-10-19.md`](docs/archive/RELEASES-to-2026-10-19.md).
