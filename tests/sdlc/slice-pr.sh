#!/usr/bin/env bash
# End-to-end test that /slice ends in a PR only where CI exists: two headless `/slice` runs
# (real model runs: minutes and a few USD each).
#   bash tests/sdlc/slice-pr.sh
#
# With CI: the scratch repo is a clone of $GH_REPO, a GitHub repo kept for this test. The script
#   commits the fixture (a CI workflow, the spec, the code) on top of its main and pushes it, so the
#   run's branch shares history with main. Expect: the run is on its own branch, the branch is
#   pushed, and an open PR's body carries the Risk line, the done-when output and how to undo it.
#   The PR is closed and its branch deleted on exit; main keeps one fixture commit per run.
# Without CI: a local repo with a local bare remote and no workflow. Expect: commits on main,
#   nothing pushed, no `gh pr create`.
#
#   GH_REPO   the scratch GitHub repo (default kadeski/sdlc-scratch). It must exist; the test
#             doesn't create it. `gh repo create kadeski/sdlc-scratch --private --add-readme`
#   ONLY      ci or noci: run one case
# See tests/sdlc/slice-lib.sh for MODEL, EFFORT, BUDGET and KEEP. The spec is Risk: low, so the review
# is /verify auto and neither run ends on a question.
set -u
source "$(dirname "$0")/slice-lib.sh"
need gh
GH_REPO="${GH_REPO:-kadeski/sdlc-scratch}"; ONLY="${ONLY:-}"
ROOT_WORK="$WORK"

ci_case() {
  WORK="$ROOT_WORK/ci"; REPO="$WORK/repo"; OUT="$WORK/transcript.jsonl"; mkdir -p "$WORK"
  gh repo view "$GH_REPO" >/dev/null 2>&1 || { echo "slice-pr.sh: $GH_REPO not found; create it first (see the header)"; fail=$((fail+1)); return; }
  gh repo clone "$GH_REPO" "$REPO" -- -q || { fail=$((fail+1)); return; }
  scratch_repo "$REPO" low
  mkdir -p .github/workflows
  cat > .github/workflows/ci.yml <<'EOF'
name: ci
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
      - run: bun test
EOF
  git add -A && git commit -qm "scratch fixture for tests/sdlc/slice-pr.sh" && git push -q origin HEAD:main || { fail=$((fail+1)); return; }
  local base; base="$(git rev-parse HEAD)"
  echo "ci case: $REPO ($GH_REPO)"

  run_slice "/slice docs/specs/slugify.md"

  local branch pr body
  branch="$(git branch --show-current)"
  pr="$(gh pr list --repo "$GH_REPO" --head "$branch" --state open --json number --jq '.[0].number // empty')"
  body="$(test -n "$pr" && gh pr view "$pr" --repo "$GH_REPO" --json body --jq .body)"
  # Clean up whatever happens below: close the PR and delete the branch.
  trap 'test -n "$pr" && gh pr close "$pr" --repo "$GH_REPO" --delete-branch >/dev/null 2>&1; test -n "$branch" -a "$branch" != main && git push -q origin --delete "$branch" >/dev/null 2>&1' RETURN

  # The order of tool calls: `gh pr create` must come before the reviewer (the first Agent call).
  local order pr_at agent_at
  order="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use")
    | if .name=="Agent" or .name=="Task" then "AGENT" elif ((.input.command? // "") | test("gh pr create")) then "PR" else "-" end' "$OUT")"
  pr_at="$(grep -nx PR <<<"$order" | head -1 | cut -d: -f1)"; agent_at="$(grep -nx AGENT <<<"$order" | head -1 | cut -d: -f1)"
  check "ci: the run works on a branch named for the spec (slugify)" test "$branch" = slugify
  check "ci: the PR was opened before the review (call $pr_at < $agent_at)" test -n "$pr_at" -a -n "$agent_at" -a "${pr_at:-0}" -lt "${agent_at:-0}"
  check "ci: the branch is pushed, at the run's last commit"  test "$(git ls-remote origin "refs/heads/$branch" | cut -f1)" = "$(git rev-parse HEAD)"
  check "ci: main on GitHub didn't move"                      test "$(git ls-remote origin refs/heads/main | cut -f1)" = "$base"
  check "ci: an open PR exists for the branch (#$pr)"        test -n "$pr"
  check "ci: the PR body carries the Risk line"               has "$body" 'Risk:\**[[:space:]]*low'
  check "ci: the PR body carries the done-when output"        has "$body" '[0-9]+ pass'
  check "ci: the PR body says how to undo the change"         has "$body" '[Rr]evert'
  check "ci: the run didn't merge it"                         test "$(gh pr view "$pr" --repo "$GH_REPO" --json state --jq .state 2>/dev/null)" = OPEN
}

noci_case() {
  WORK="$ROOT_WORK/noci"; REPO="$WORK/repo"; OUT="$WORK/transcript.jsonl"; mkdir -p "$WORK"
  git init -q --bare -b main "$WORK/remote.git"
  scratch_repo "$REPO" low
  git add -A && git commit -qm "scratch repo" && git remote add origin "$WORK/remote.git" && git push -q origin main || { fail=$((fail+1)); return; }
  local base; base="$(git rev-parse HEAD)"
  echo "no-ci case: $REPO"

  run_slice "/slice docs/specs/slugify.md"

  local cmds; cmds="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .input.command? // empty' "$OUT")"
  check "no ci: the work is committed locally"                test "$(git rev-list --count "$base..HEAD")" -ge 1
  check "no ci: the remote has only main"                     test "$(git --git-dir="$WORK/remote.git" for-each-ref --format=x refs/heads | wc -l | tr -d ' ')" = 1
  check "no ci: the remote's main didn't move"                test "$(git --git-dir="$WORK/remote.git" rev-parse main)" = "$base"
  check "no ci: no gh pr create"                              not has "$cmds" 'gh pr create'
}

[ "$ONLY" = noci ] || ci_case
[ "$ONLY" = ci ] || noci_case
finish
