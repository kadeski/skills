#!/usr/bin/env bash
# End-to-end test for `/next <issue> auto`: one headless run in a scratch repo.
# It is a real model run (minutes, and it costs money), so run it by hand: bash tests/sdlc/next-auto.sh
#
# It makes a scratch git repo with one small test, files a small issue in $GH_REPO, copies the
# skills under test into the scratch repo's .claude/skills/, runs `claude -p "/next <issue> auto"`
# there, and checks the transcript, the issue and the git log.
# --setting-sources project keeps user-level skills out: a user-level skill wins over a project
# one of the same name, so without it the installed skills would run, not the copies under test.
#
#   GH_REPO               repo that holds the test issue (default kadeski/sdlc-scratch, private)
#   MODEL, EFFORT, BUDGET passed to claude (default opus, medium, 5 USD)
#   AUTO=0                run `/next <issue>` with no auto: the run must print its contract,
#                         wait for a go and do no work
#   RED=0                 leave the red-commit rule out of the scratch CLAUDE.md: the run should
#                         then make one commit per slice, the test and the code together
#   KEEP                  directory for the scratch repo and the transcript (default: a new temp dir)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILLS="$(cd "$HERE/../../plugins/sdlc" && pwd)"
export GH_REPO="${GH_REPO:-kadeski/sdlc-scratch}"
MODEL="${MODEL:-opus}"; EFFORT="${EFFORT:-medium}"; BUDGET="${BUDGET:-5}"; RED="${RED:-1}"; AUTO="${AUTO:-1}"
WORK="${KEEP:-$(mktemp -d)}"
REPO="$WORK/repo"
OUT="$WORK/transcript.jsonl"
for c in claude gh git bun jq; do
  command -v "$c" >/dev/null || { echo "next-auto.sh: $c not found"; exit 2; }
done

# --- the scratch repo: one passing test, a CLAUDE.md that asks for a red commit, no remote
mkdir -p "$REPO/src" "$REPO/.claude/skills" && cd "$REPO" || exit 2
git init -q -b main && git config user.email t@t && git config user.name t
cat > CLAUDE.md <<'EOF'
# sdlc-scratch

A throwaway repo made by `tests/sdlc/next-auto.sh` in kadeski/skills for one headless test run. Nothing here ships.

- **Plan:** GitHub issues in the repo the `GH_REPO` environment variable names. `gh issue view <N>` and `gh issue comment <N>` reach it. This repo has no remote.
- **Checks:** `bun test`.
- **Commits:** commit the failing test on its own before the code that makes it pass (red, then green).
- **Close-out:** post the done-check output as a comment on the issue. Do not push, open a PR or close the issue.
EOF
[ "$RED" = 1 ] || { grep -v '^- \*\*Commits:\*\*' CLAUDE.md > CLAUDE.md.new && mv CLAUDE.md.new CLAUDE.md; }
printf '{\n  "name": "sdlc-scratch",\n  "private": true,\n  "type": "module"\n}\n' > package.json
cat > src/clamp.ts <<'EOF'
/** Keep `n` inside the range `min` to `max`. */
export function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}
EOF
cat > src/clamp.test.ts <<'EOF'
import { expect, test } from "bun:test";
import { clamp } from "./clamp";

test("clamp keeps a number inside the range", () => {
  expect(clamp(5, 0, 10)).toBe(5);
  expect(clamp(-3, 0, 10)).toBe(0);
  expect(clamp(42, 0, 10)).toBe(10);
});
EOF
# verify and lesson are copied because /next auto reads verify for its review step, and lesson
# when the run made a mistake worth one. This item is clean, so the run
# gets no findings: the fix-or-reject rules, the 3-round cap and /lesson auto are not exercised here.
# Each copy ends in a marker line, so a tool result that holds the marker read that copy to its end.
mark="scratch-copy-$$-$RANDOM"
for s in next slice verify lesson; do
  cp -R "$SKILLS/skills/$s" ".claude/skills/$s"
  printf '\n<!-- %s-%s -->\n' "$mark" "$s" >> ".claude/skills/$s/SKILL.md"
done
echo ".claude/" >> .git/info/exclude   # the skills under test never land in the run's commits
git add -A && git commit -qm "scratch repo" || exit 2
BASE="$(git rev-parse HEAD)"

# --- the item: one obvious behavior with its own done check (Tier 1)
cat > "$WORK/issue.md" <<'EOF'
A test fixture filed by `tests/sdlc/next-auto.sh`. A headless run works it in a scratch repo, and the script closes it afterwards.

**What:** add `slugify(title: string): string` in `src/slugify.ts`: lowercase the title, turn each run of characters other than a-z and 0-9 into one dash, and drop a dash at either end.

**Done when:** `bun test` passes with `src/slugify.test.ts` checking that `slugify("Hello, World!")` is `"hello-world"` and `slugify("  --A  b__c--  ")` is `"a-b-c"`.
EOF
url="$(gh issue create --title "Scratch item for tests/sdlc/next-auto.sh: add slugify(title)" --body-file "$WORK/issue.md")" \
  || { echo "next-auto.sh: could not file the issue in $GH_REPO"; exit 2; }
ISSUE="${url##*/}"
echo "scratch repo: $REPO"
echo "issue:        https://github.com/$GH_REPO/issues/$ISSUE"

# --- the run (MSYS_NO_PATHCONV: Git Bash on Windows would turn "/next ..." into a file path)
prompt="/next $ISSUE auto"; [ "$AUTO" = 1 ] || prompt="/next $ISSUE"
MSYS_NO_PATHCONV=1 claude -p "$prompt" --setting-sources project --strict-mcp-config \
  --model "$MODEL" --effort "$EFFORT" --max-budget-usd "$BUDGET" --permission-mode auto \
  --no-session-persistence --output-format stream-json --verbose > "$OUT" 2> "$WORK/stderr.log"
echo "claude exit:  $?   transcript: $OUT"

# --- the checks
pass=0; fail=0
check() { # name, command...
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "ok   - $name"; pass=$((pass+1)); else echo "FAIL - $name"; fail=$((fail+1)); fi
}
not() { ! "$@"; }
result="$(jq -rs 'map(select(.type=="result")) | last | .result // ""' "$OUT")"
tools="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use")
  | [.name, (.input.file_path // .input.skill // "")] | @tsv' "$OUT")"
comments="$(gh issue view "$ISSUE" --json comments --jq '[.comments[].body] | join("\n")')"
results="$(jq -r 'select(.type=="user") | .message.content | arrays | .[] | select(.type=="tool_result")
  | .content | if type=="array" then map(.text // "") | join("") else tostring end' "$OUT")"
last_line="$(grep -v -e '^[[:space:]]*$' -e '^[[:space:]]*```' <<<"$result" | tail -1)"   # past blank and fence lines
inputs="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .input | tojson' "$OUT")"
has() { grep -Eq -- "$2" <<<"$1"; }
holds() { test -n "$2" && grep -Fq -- "$2" <<<"$1"; }
n="$(git rev-list --count "$BASE..HEAD")"

if [ "$AUTO" != 1 ]; then
  # Typed by hand, /next still stops at its contract: nothing is built or posted before a go.
  check "the run ends on the go question"               has "$result" 'go, pick another, or adjust'
  check "the run made no commit (made $n)"              test "$n" -eq 0
  check "nothing was posted on the issue"               test -z "$comments"
  check "the transcript has no Skill tool call"         not has "$tools" '^Skill'
  gh issue close "$ISSUE" --reason "not planned" >/dev/null
  echo "---- $pass passed, $fail failed"
  [ "$fail" -eq 0 ]; exit
fi

# slice 1: the contract is posted and the run starts without a go
check "the run does not end on the go question"       not has "$result" 'go, pick another, or adjust'
check "the final message does not end on a question"  not has "$last_line" '\?[^[:alnum:]]*$'
check "the issue has the contract (Item:)"            has "$comments" 'Item:'
check "the contract sizes the item Tier 1"            has "$comments" 'Tier:\**[[:space:]]*1'
check "the contract's Then: line is stop"             has "$comments" 'Then:\**[[:space:]]*"?stop'

# slice 2: slice/SKILL.md is read as a file, never called through the Skill tool.
# The read counts whether it is a Read call or a `cat` in a Bash call: the check is that the
# scratch copy's last line came back in a tool result.
check "a tool result holds the scratch slice/SKILL.md" holds "$results" "$mark-slice"
check "the transcript has no Skill tool call"         not has "$tools" '^Skill'

# review: the auto run reads verify/SKILL.md as a file, a separate agent
# reviews the work, and the run ends with a review log on the issue, with no question asked.
check "a tool result holds the scratch verify/SKILL.md" holds "$results" "$mark-verify"
check "a reviewer was spawned (an Agent tool call)"   has "$tools" "^(Agent|Task)$(printf '\t')"
check "the issue has a review log (Review round 1)"   has "$comments" 'Review round 1'
check "the review log gives the reviewer's counts"    has "$comments" 'Done when: [0-9]+/[0-9]+ pass'

# slice 3: /slice commits the failing test, then the code, when the project asks for it
first="$(git rev-list --reverse "$BASE..HEAD" | head -1)"
first_files="$(git diff-tree --no-commit-id --name-only -r "${first:-HEAD}")"
last_files="$(git diff-tree --no-commit-id --name-only -r HEAD)"
tests_at() { # commit, dir name: run bun test on a clean checkout of that commit
  git worktree add -q --detach "$WORK/$2" "$1" && (cd "$WORK/$2" && bun test > "$WORK/$2.log" 2>&1)
}
first_exit="$(tests_at "${first:-HEAD}" first; echo $?)"
last_exit="$(tests_at HEAD last; echo $?)"
if [ "$RED" = 1 ]; then
  # A red commit, then a green one. The red commit may also hold an empty stub: a test that
  # imports a missing module fails on the import, and slice/SKILL.md asks for a failure on the assertion.
  check "the run made at least two commits (made $n)"   test "$n" -ge 2
  check "the first commit holds the test"               test -n "$first" -a -n "$(grep '\.test\.' <<<"$first_files")"
  check "bun test fails at the first commit (red)"      test -n "$first" -a "$first_exit" != 0
  check "the red failure is an assertion"               grep -q 'expect(received)' "$WORK/first.log"
  check "the red failure is not a missing module"       not grep -q 'Cannot find module' "$WORK/first.log"
  check "the first commit is named as slice names a red commit" has "$(git log -1 --format=%s "${first:-HEAD}")" 'slice [0-9]+ red'
  check "only red commits touch a test file"            test -n "$first" -a -z "$(git log --format=%s "$BASE..HEAD" -- '*.test.*' | grep -Ev 'slice [0-9]+ red')"
  check "the last commit changes code"                  test "$n" -ge 1 -a -n "$(grep -v '\.test\.' <<<"$last_files")"
else
  # The project asks for no red commit: the slice's one commit holds the test and the code.
  check "the first commit holds the test and the code"  test -n "$first" -a -n "$(grep '\.test\.' <<<"$first_files")" -a -n "$(grep -v '\.test\.' <<<"$first_files")"
  check "bun test passes at the first commit"           test -n "$first" -a "$first_exit" = 0
fi
check "bun test passes at the last commit (green)"    test "$n" -ge 1 -a "$last_exit" = 0

gh issue close "$ISSUE" --reason "not planned" >/dev/null
echo "---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
