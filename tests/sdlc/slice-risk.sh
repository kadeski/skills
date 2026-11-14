#!/usr/bin/env bash
# End-to-end test that /slice picks its review from the spec's Risk line: two headless `/slice`
# runs in scratch repos with no remote (real model runs: minutes and a few USD each).
#   bash tests/sdlc/slice-risk.sh
#
# Risk: low    -> /verify auto: a reviewer is spawned, the review log is written, and the run
#                 ends with no question asked.
# Risk: normal -> /verify: a reviewer is spawned and the run ends on a question about what to fix
#                 (with no findings, as this fixture usually gives, "anything to fix?": the user signs off).
#
#   ONLY   low or normal: run one case
# See tests/sdlc/slice-lib.sh for MODEL, EFFORT, BUDGET and KEEP.
set -u
source "$(dirname "$0")/slice-lib.sh"
ONLY="${ONLY:-}"
ROOT_WORK="$WORK"

one_case() { # $1 = risk
  WORK="$ROOT_WORK/$1"; REPO="$WORK/repo"; OUT="$WORK/transcript.jsonl"; mkdir -p "$WORK"
  scratch_repo "$REPO" "$1"
  git add -A && git commit -qm "scratch repo" || { fail=$((fail+1)); return; }
  echo "$1 case: $REPO"
  run_slice "/slice docs/specs/slugify.md"

  local tools result last
  tools="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .name' "$OUT")"
  result="$(final_result)"; last="$(last_line)"
  check "$1: the run read the scratch verify/SKILL.md"    has "$(tool_results)" "$mark-verify"
  check "$1: a reviewer was spawned (an Agent tool call)" has "$tools" '^(Agent|Task)$'
  check "$1: bun test passes at HEAD"                      bun test
  if [ "$1" = low ]; then
    check "low: the review log has round 1"                has "$(cat docs/specs/slugify.review.md 2>/dev/null)" 'Review round 1'
    check "low: the final message asks no question"        not has "$last" '\?[^[:alnum:]]*$'
    check "low: no AskUserQuestion call"                    not has "$tools" '^AskUserQuestion$'
  else
    check "normal: the run ends asking what to fix or change" has "$last" '(fix|change)[^?]*\?[^[:alnum:]]*$'
    check "normal: the final message ends on a question"   has "$last" '\?[^[:alnum:]]*$'
  fi
}

[ "$ONLY" = normal ] || one_case low
[ "$ONLY" = low ] || one_case normal
finish
