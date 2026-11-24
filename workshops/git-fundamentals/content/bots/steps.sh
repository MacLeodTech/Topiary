# Workshop bot steps for git-fundamentals (see engine/web-terminal/bot-runner.sh's BOT_STEPS_FILE).
# Walks Labs 1-5 (step_lab1_* .. step_lab5_*, below), using the engine's shared steps (step_ensure_clone,
# step_sync_main, step_wrap_round), and adds two things on top:
#   * Lab 1 step 9's wrong-branch drill (step_gf_wrong_branch), right after the Lab 1 PR step. It is
#     the only step that earns `l1-rescue`, so without it a --test run leaves every bot one core
#     milestone short and `l1-rescue` never gets a class-clear bonus.
#   * the three challenges (c1 The Hotfix, c2 The Detective, capstone The Great Merge) right before
#     step_wrap_round, each one the way the lab page says to do it: `dojo challenge start`, work in
#     ~/lab/challenge-repo, `dojo check`.
# Each challenge step ends with `dojo check ID`, so the result is in the bot's log (~/.dojo-bot.log)
# and in `dojo check status` for that account.

# -- Labs 1-5 -------------------------------------------------------------------------------------
step_lab1_branch_and_edit() {
  cd "$REPO_DIR" || return 1
  local branch; branch="$(branch_name "add-${BOT_USER}")"
  narrate "Lab 1, steps 2-5 -- branch, edit the roster, review, commit"
  run_cmd "git checkout -B '$branch' main"

  local roster="roster/team.yaml"
  if [ ! -f "$roster" ]; then
    # A workshop other than git-fundamentals won't have this file --
    # fall back to something generic so the bot still has real content
    # to commit instead of failing outright.
    roster="NOTES-${BOT_USER}.md"
    narrate "roster/team.yaml not found (not the git-fundamentals content) -- using $roster instead"
  fi

  printf -- '- name: %s (demo bot, round %s)\n  role: QA\n' "$BOT_USER" "$ROUND" >> "$roster"
  orient
  run_cmd "git status"
  run_cmd "git diff"

  if [ $(( ROUND % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) committing before staging, on purpose, to show what that looks like"
    run_cmd "git commit -m 'Add $BOT_USER to team roster'"
    narrate "right -- nothing was staged. Fixing that."
  fi

  orient
  run_cmd "git add '$roster'"
  run_cmd "git commit -m 'Add $BOT_USER to team roster (round $ROUND)'"
  run_cmd "git log -1"
}

step_lab1_push_and_pr() {
  cd "$REPO_DIR" || return 1
  local branch; branch="$(branch_name "add-${BOT_USER}")"
  narrate "Lab 1, step 6 -- push (try the bare form first, like the lab shows)"
  run_cmd "git push"
  narrate "no upstream yet, as expected -- setting one"
  run_cmd "git push -u origin '$branch'"

  narrate "Lab 1, step 7 -- open a pull request"
  local pr_json pr_number head="$branch"
  # From a fork, the PR's head names the fork's owner: "<owner>:<branch>".
  [ "$FORGEJO_FORK_WORKFLOW" = 1 ] && head="$BOT_USER:$branch"
  pr_json="$(api_curl -X POST "$API/repos/$FORGEJO_ORG/$FORGEJO_REPO/pulls" \
    -H 'Content-Type: application/json' \
    -d "{\"head\":\"$head\",\"base\":\"main\",\"title\":\"[$BOT_USER] Add to roster (round $ROUND)\",\"body\":\"Demo bot activity -- safe to review and merge live, or close.\"}")"
  pr_number="$(printf '%s' "$pr_json" | grep -o '"number":[0-9]*' | head -1 | cut -d: -f2)"
  if [ -n "$pr_number" ]; then
    narrate "opened PR #$pr_number for $branch"
    PENDING_PR_BRANCH="$branch"
    PENDING_PR_NUMBER="$pr_number"
  else
    narrate "PR open failed or already exists for $branch -- will re-check next round"
  fi
}

step_lab2_review_and_undo() {
  cd "$REPO_DIR" || return 1
  narrate "Lab 2 -- reviewing and undoing before a commit"
  orient
  run_cmd "echo '- name: Test Entry' >> roster/team.yaml"
  run_cmd "git status"
  run_cmd "git restore roster/team.yaml"
  run_cmd "git status"

  run_cmd "echo '- name: Another Test' >> roster/team.yaml"
  run_cmd "git add roster/team.yaml"
  run_cmd "git status"
  run_cmd "git restore --staged roster/team.yaml"
  run_cmd "git status"
  run_cmd "git restore roster/team.yaml"

  run_cmd "touch scratch.log"
  run_cmd "git status"
  run_cmd "echo '*.log' >> .gitignore"
  run_cmd "git status"
  run_cmd "rm -f scratch.log .gitignore"
  run_cmd "git status"
}

step_lab3_stash() {
  # Follows lab3.md: a fresh practice branch with a commit of its own, an
  # unfinished edit on it, a stash to visit main, then apply, pop and clean up.
  # (It used to stash on main and pop onto the lab 1 branch, whose roster had
  # its own line at the same end of the file: a conflict every time.)
  cd "$REPO_DIR" || return 1
  narrate "Lab 3 -- stashing"
  local branch; branch="$(branch_name "stash-demo")"
  # A retry restarts the step from the top: drop what the failed attempt left.
  git restore --staged --worktree roster/team.yaml 2>/dev/null
  git stash clear 2>/dev/null
  orient
  run_cmd "git checkout main" || return 1
  run_cmd "git checkout -B '$branch'" || return 1
  run_cmd "git branch --show-current"
  run_cmd "echo '- name: ${BOT_USER} (stash demo)' >> roster/team.yaml"
  run_cmd "git add roster/team.yaml"
  run_cmd "git commit -m 'Add my entry'" || return 1
  run_cmd "echo '- name: Work In Progress' >> roster/team.yaml"
  run_cmd "git status"
  run_cmd "git checkout main" || narrate "refused, as the lab says: switching would overwrite the unsaved edit"
  run_cmd "git branch --show-current"
  run_cmd "git stash" || return 1
  run_cmd "git status"
  run_cmd "git stash list"
  run_cmd "git checkout main" || return 1
  run_cmd "git status"
  run_cmd "git log --oneline -3"
  run_cmd "git checkout '$branch'" || return 1
  run_cmd "git stash apply" || return 1
  run_cmd "git status"
  run_cmd "git stash list"
  run_cmd "git restore roster/team.yaml"
  run_cmd "git stash pop" || return 1
  run_cmd "git diff"
  run_cmd "git stash list"
  run_cmd "git restore roster/team.yaml"
  run_cmd "git checkout main" || return 1
  run_cmd "git branch -D '$branch'"
}

gf_sample_repo_lab4_history() {
  cd "$REPO_DIR" || return 1
  narrate "Lab 4 -- investigating history"
  run_cmd "git log --oneline -5"
  run_cmd "git log --oneline --graph --all -10"
  local last_hash; last_hash="$(git log -1 --format=%H 2>/dev/null)"
  [ -n "$last_hash" ] && run_cmd "git show --stat $last_hash"
  run_cmd "git blame roster/team.yaml | tail -5"

  local branch; branch="$(branch_name "lab4-explore")"
  orient
  run_cmd "git checkout -B '$branch'"
  run_cmd "echo '- name: Branch Explorer' >> roster/team.yaml"
  run_cmd "git add roster/team.yaml"
  run_cmd "git commit -m 'Lab 4: branch comparison example'"
  run_cmd "git diff main..$branch"

  if [ $(( (ROUND + 1) % MISTAKE_MOD )) -eq "$MISTAKE_REM" ]; then
    narrate "(demo) trying to clean up without switching off the branch first"
    run_cmd "git branch -D '$branch'"
    narrate "right -- can't delete the branch you're currently on. Switching first."
  fi
  run_cmd "git checkout main"
  run_cmd "git branch -D '$branch'"
}

step_lab5_conflict() {
  cd "$REPO_DIR" || return 1
  narrate "Lab 5, part A -- causing and resolving a merge conflict"
  orient
  local a b
  a="$(branch_name "conflict-a")"
  b="$(branch_name "conflict-b")"

  run_cmd "git checkout main"
  run_cmd "git checkout -B '$a'"
  run_cmd "sed -i 's/role: .*Engineer/role: Senior Engineer/' roster/team.yaml 2>/dev/null || echo '  role: Senior Engineer' >> roster/team.yaml"
  run_cmd "git add roster/team.yaml"
  run_cmd "git commit -m 'conflict-a: update role'"

  run_cmd "git checkout main"
  run_cmd "git checkout -B '$b'"
  run_cmd "sed -i 's/role: .*Engineer/role: Principal Engineer/' roster/team.yaml 2>/dev/null || echo '  role: Principal Engineer' >> roster/team.yaml"
  run_cmd "git add roster/team.yaml"
  run_cmd "git commit -m 'conflict-b: update role'"

  run_cmd "git merge '$a'"
  narrate "conflict, as expected -- resolving by keeping the incoming version"
  run_cmd "grep -v -E '^(<<<<<<<|=======|>>>>>>>)' roster/team.yaml > roster/team.yaml.resolved && mv roster/team.yaml.resolved roster/team.yaml"
  run_cmd "git add roster/team.yaml"
  run_cmd "git commit --no-edit"

  run_cmd "git checkout main"
  run_cmd "git branch -D '$a' '$b'"
}

step_lab5_undo() {
  cd "$REPO_DIR" || return 1
  narrate "Lab 5, part B -- safely undoing a change"
  local branch; branch="$(branch_name "undo-demo")"
  run_cmd "git checkout -B '$branch'"
  run_cmd "echo '- name: Oops Entry' >> roster/team.yaml"
  run_cmd "git add roster/team.yaml"
  run_cmd "git commit -m 'Oops, wrong entry'"
  run_cmd "git reset --soft HEAD~1"
  run_cmd "git status"
  # --soft kept the change staged: commit it again, then drop it for good (one commit back again, as Lab 5 does).
  run_cmd "git commit -m 'Oops, wrong entry'"
  run_cmd "git reset --hard HEAD~1"
  run_cmd "git status"

  run_cmd "echo '- name: Reverted Later' >> roster/team.yaml"
  run_cmd "git add roster/team.yaml"
  run_cmd "git commit -m 'Example commit to revert'"
  run_cmd "git log --oneline -1"
  run_cmd "git revert HEAD --no-edit"
  run_cmd "git log --oneline -2"

  run_cmd "git checkout main"
  run_cmd "git branch -D '$branch'"
}

# How far into the curriculum each persona gets per round -- this, plus the
# delay ranges set above, is what makes the expert visibly "further along"
# than the novice over the course of a demo: the novice's round never even
# includes the Lab 3-5 steps, no matter how long it runs. Sized so that in
# roughly a 10-minute demo window (see engine/README.md) the expert cycles
# through the whole list a couple of times, the intermediate bot gets
# through Lab 4 once or twice, and the novice is still visibly working
# through Lab 1/Lab 2 material by the time you'd wrap up a live walkthrough.
case "$PERSONA" in
  expert)
    STEPS=(
      step_ensure_clone
      step_sync_main
      step_lab1_branch_and_edit
      step_lab1_push_and_pr
      step_lab2_review_and_undo
      step_lab3_stash
      step_lab4_history
      step_lab5_conflict
      step_lab5_undo
      step_wrap_round
    )
    ;;
  intermediate)
    STEPS=(
      step_ensure_clone
      step_sync_main
      step_lab1_branch_and_edit
      step_lab1_push_and_pr
      step_lab2_review_and_undo
      step_lab3_stash
      step_lab4_history
      step_wrap_round
    )
    ;;
  novice)
    STEPS=(
      step_ensure_clone
      step_sync_main
      step_lab1_branch_and_edit
      step_lab1_push_and_pr
      step_lab2_review_and_undo
      step_wrap_round
    )
    ;;
esac

# -- Challenges and the wrong-branch drill ---------------------------------------------------------
GF_REPO="$BOT_USER/challenge-repo"
GF_DIR="$HOME/lab/challenge-repo"

gf_start() { # start challenge $1 from a clean copy and cd into it
  cd "$HOME/lab" && rm -rf "$GF_DIR"
  printf '%s@dojo:~$ dojo challenge reset %s\n' "$BOT_USER" "$1"
  GF_OUT="$(dojo challenge reset "$1" 2>&1)"; local rc=$?
  printf '%s\n' "$GF_OUT"
  [ "$rc" = 0 ] || return 1
  cd "$GF_DIR" || return 1
  git config user.name "$BOT_USER"; git config user.email "$BOT_USER@example.com"
}

gf_open_pr() { # $1 = branch, $2 = title; echoes the PR number
  api_curl -X POST "$API/repos/$GF_REPO/pulls" -H 'Content-Type: application/json' \
    -d "{\"head\":\"$1\",\"base\":\"main\",\"title\":\"$2\"}" | grep -o '"number":[0-9]*' | head -1 | cut -d: -f2
}

step_gf_wrong_branch() {
  # Lab 1 step 9: commit on `main` by mistake, carry the commit to a branch, put `main` back.
  # Entirely local -- nothing is pushed and `main` is only ever reset to what the server already
  # has, so this touches no shared state. Earns f-main ("Living Dangerously", worth nothing) on the
  # commit and l1-rescue on the reset; the branch is what tells l1-rescue from Lab 5's l5-reset, so
  # the reset has to happen while on `main`.
  cd "$REPO_DIR" || return 1
  local branch notes; branch="$(branch_name "notes")"; notes="notes-${BOT_USER}.md"
  narrate "Lab 1, step 9 -- the mistake everyone makes once: editing straight on main"
  run_cmd "git checkout main"
  # A restart re-enters the whole step, so drop anything a half-finished run left behind.
  git branch -D "$branch" >/dev/null 2>&1
  run_cmd "printf '# Notes from round %s\\n' '$ROUND' > '$notes'"
  run_cmd "git add '$notes'"
  run_cmd "git commit -m 'Add $BOT_USER notes (round $ROUND)'"
  run_cmd "git log --oneline -2"
  narrate "...that went on main. Label the commit first, then move main off it"
  run_cmd "git branch '$branch'"
  run_cmd "git log --oneline --graph --decorate -2"
  run_cmd "git fetch"
  run_cmd "git reset --hard origin/main"
  run_cmd "git status"
  narrate "main is back to the server's version -- and the commit is safe on $branch"
  run_cmd "git checkout '$branch'"
  run_cmd "git log --oneline -1"
  run_cmd "git checkout main"
  run_cmd "git branch -d '$branch'"
  narrate "-d refuses an unmerged branch, as the lab says -- forcing it, this was only a drill"
  run_cmd "git branch -D '$branch'"
}

step_gf_c1() {
  narrate "Challenge c1 -- The Hotfix"
  gf_start c1 || return 1
  run_cmd "git switch -c hotfix-$BOT_USER"
  # Only the process is checked: change the line under my own name.
  run_cmd "sed -i '/^- name: $BOT_USER\$/{n;s/role: .*/role: Software Engineer/}' roster/team.yaml"
  run_cmd "git diff --stat"
  run_cmd "git commit -am 'hotfix: fix my role'"
  run_cmd "git push -u origin hotfix-$BOT_USER"
  local n; n="$(gf_open_pr "hotfix-$BOT_USER" "hotfix: fix my role")"
  narrate "opened PR #${n:-?} in $GF_REPO"
  [ -n "$n" ] || return 1
  run_cmd "dojo check c1"
}

step_gf_c2() {
  narrate "Challenge c2 -- The Detective"
  gf_start c2 || return 1
  local line hash who
  # The goal sentence ("...introduced `meetings_per_day: 11`..."), wherever the
  # challenge text puts it: it used to be a "Goal: " line, now it is under "## Goal".
  line="$(printf '%s\n' "$GF_OUT" | sed -n 's/.*introduced `\([^`]*\)`.*/\1/p' | head -1)"
  [ -n "$line" ] || { narrate "could not read the target line from the goal"; return 1; }
  run_cmd "git log -S'$line' --format='%h %an' -- config/settings.yaml"
  hash="$(git log -S"$line" --format=%h -- config/settings.yaml | tail -1)"
  who="$(git log -S"$line" --format=%an -- config/settings.yaml | tail -1)"
  run_cmd "git switch -c case-$BOT_USER"
  run_cmd "echo '$hash $who' > answer.txt"
  run_cmd "git add answer.txt"
  run_cmd "git commit -m 'Case closed'"
  run_cmd "git push -u origin case-$BOT_USER"
  run_cmd "dojo check c2"
}

step_gf_capstone() {
  narrate "Capstone -- The Great Merge"
  gf_start capstone || return 1
  run_cmd "git switch -c release-$BOT_USER"
  run_cmd "git merge origin/feature-a"
  run_cmd "git merge origin/feature-b"   # conflicts in CHANGELOG.md: expected
  run_cmd "sed -i '/^<<<<<<< /d;/^=======\$/d;/^>>>>>>> /d' CHANGELOG.md"
  run_cmd "git add CHANGELOG.md"
  run_cmd "git commit --no-edit"
  run_cmd "git log --oneline"
  run_cmd "git revert --no-edit \$(git log --format=%h --grep='Make deploys faster' -1)"
  run_cmd "git rm -q debug.log"
  run_cmd "echo '*.log' >> .gitignore"
  run_cmd "git add .gitignore"
  run_cmd "git commit -m 'Stop tracking logs'"
  run_cmd "git push -u origin release-$BOT_USER"
  local n; n="$(gf_open_pr "release-$BOT_USER" "Release both features")"
  narrate "opened PR #${n:-?} in $GF_REPO"
  [ -n "$n" ] || return 1
  api_curl -X POST "$API/repos/$GF_REPO/pulls/$n/merge" -H 'Content-Type: application/json' -d '{"Do":"merge"}'
  run_cmd "dojo check capstone"
}

# Lab 4 runs in the practice repo `lab-history` builds (~/lab/history-repo), not the sample repo.
# It follows lab4.md: browse, filter, show, blame/log -p, the pickaxe hunt for the leaked key, then the
# throwaway-branch diff. Without `lab-history` (an image built before it existed) it falls back to
# gf_sample_repo_lab4_history, the walk over the sample repo defined with the other labs above.
step_lab4_history() {
  if ! command -v lab-history >/dev/null 2>&1; then gf_sample_repo_lab4_history; return; fi
  narrate "Lab 4 -- investigating a longer history (lab-history practice repo)"
  run_cmd "lab-history"
  cd "$HOME/lab/history-repo" || return 1
  git config user.name "$BOT_USER"; git config user.email "$BOT_USER@example.com"
  run_cmd "git log --oneline --graph --all"
  run_cmd "git log --oneline --author=Bob"
  run_cmd "git log --oneline --since=2026-08-07"
  run_cmd "git log --stat --oneline -4"
  local db; db="$(git log --format=%h --grep='Add database settings' -1)"
  run_cmd "git show $db"
  run_cmd "git blame config/app.yaml"
  run_cmd "git log -p config/app.yaml | head -60"
  narrate "hunting for the leaked key"
  run_cmd "git log -S'Dkx8Q~' --oneline"
  local added; added="$(git log -S'Dkx8Q~' --format=%h | tail -1)"
  run_cmd "git show $added"
  command -v gitleaks >/dev/null 2>&1 && run_cmd "gitleaks git -v --no-banner ."

  local branch; branch="$(branch_name "lab4-explore")"
  run_cmd "git checkout -b '$branch'"
  run_cmd "sed -i 's/port: 8080/port: 9090/' config/app.yaml"
  run_cmd "git add config/app.yaml"
  run_cmd "git commit -m 'Lab 4: branch comparison example'"
  run_cmd "git diff main..$branch"
  run_cmd "git checkout main"
  run_cmd "git branch -D '$branch'"
  cd "$REPO_DIR" || return 1
}

# The wrong-branch drill follows the Lab 1 PR step (every persona reaches Lab 1, so every bot runs
# it); the challenges go after the labs, just before the round ends, and only where dojo challenge
# exists (achievements off = no challenges).
gf_challenges=0
command -v dojo challenge >/dev/null 2>&1 && gf_challenges=1
gf_steps=()
for s in "${STEPS[@]}"; do
  [ "$s" = step_wrap_round ] && [ "$gf_challenges" = 1 ] && gf_steps+=(step_gf_c1 step_gf_c2 step_gf_capstone)
  gf_steps+=("$s")
  [ "$s" = step_lab1_push_and_pr ] && gf_steps+=(step_gf_wrong_branch)
done
STEPS=("${gf_steps[@]}")
