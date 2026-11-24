# Releases

What has shipped, newest first. [`ROADMAP.md`](ROADMAP.md) holds what is still open; when an item there is done
and verified, it moves here in a line or two. Detail behind older entries (design, decisions, per-task logs) is in
[`docs/archive/`](docs/archive/), kept for reference and no longer updated.

Entries are grouped by what reached `main`. Dates are commit or merge dates; "locally" means tested on the
WSL2 desktop stack at `http://localhost:8080`.

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
