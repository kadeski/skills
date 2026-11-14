#!/usr/bin/env bash
# End-to-end test that /slice ticks each slice as a task, so the project's TaskCompleted gate
# runs: one headless `/slice` run in a scratch repo (a real model run: minutes, a few USD).
#   bash tests/sdlc/slice-gate.sh
#
# The scratch repo's .claude/checks.json runs `bun test` and a check that stands in for one only
# the gate runs (a slow suite, an environment check): it does nothing when run by hand, and under
# the gate (CLAUDE_PROJECT_DIR is set for hooks, not for the Bash tool) it asks for a CHANGELOG.md
# line with a token that exists only outside the repo. So the slice's first completion is refused
# by construction, whatever the run checked first, and the refusal says how to fix it.
# See tests/sdlc/slice-lib.sh for MODEL, EFFORT, BUDGET and KEEP.
set -u
source "$(dirname "$0")/slice-lib.sh"

scratch_repo "$REPO" low
TOKEN="gate-$RANDOM$RANDOM"
cat > "$WORK/gate-only.mjs" <<EOF
import { readFileSync } from "node:fs";
if (!process.env.CLAUDE_PROJECT_DIR) process.exit(0); // run by hand: nothing to check
const line = "- slugify: $TOKEN";
if (readFileSync("CHANGELOG.md", "utf8").includes(line)) process.exit(0);
console.log("changelog: CHANGELOG.md needs this exact line for src/slugify.ts: " + line);
process.exit(1);
EOF
printf '# Changelog\n\n- clamp: keep a number inside a range\n' > CHANGELOG.md
CHECK="bun test && node $(command -v cygpath >/dev/null && cygpath -m "$WORK/gate-only.mjs" || echo "$WORK/gate-only.mjs")"
printf '{ "stop": "bun test", "task": "%s" }\n' "$CHECK" > .claude/checks.json
git add -A && git commit -qm "scratch repo" || exit 2
BASE="$(git rev-parse HEAD)"
echo "scratch repo: $REPO"

run_slice "/slice docs/specs/slugify.md"

# Each TaskUpdate that marks a task completed, in order, with the result that answered it.
completions="$(jq -rs '
  (map(select(.type=="user") | .message.content | arrays | .[] | select(.type=="tool_result")
       | {key: .tool_use_id, value: (.content | if type=="array" then map(.text // "") | join("") else tostring end)})
   | from_entries) as $res
  | map(select(.type=="assistant") | .message.content[]? | select(.type=="tool_use" and .name=="TaskUpdate"
       and .input.status=="completed") | ($res[.id] // "" | gsub("\n"; " ")))
  | .[]' "$OUT")"
first_completion="$(head -1 <<<"$completions")"
# A completion after the first refusal whose result is not hook feedback: the gate accepted it.
accepted_after="$(awk 'f && NF && !/hook feedback/ {n++} /TaskCompleted hook feedback/ {f=1} END {print n+0}' <<<"$completions")"
state_file="$(git rev-parse --git-path claude-stop-gate.json)"
skills_loaded="$(jq -r 'select(.subtype=="init") | .skills[]' "$OUT")"

check "a task was created for the slice"                     has "$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .name' "$OUT")" '^TaskCreate$'
# User skills are off (weekly is one, not copied here), so the slice that loaded is the scratch copy.
check "slice is loaded and user skills are not (no weekly)"  test -n "$(grep -x slice <<<"$skills_loaded")" -a -z "$(grep -x weekly <<<"$skills_loaded")"
check "the gate refused a completion: the gate-only check failed" has "$completions" 'TaskCompleted hook feedback.*CHANGELOG.md needs this exact line'
check "the first completion was the refused one"             has "$first_completion" 'TaskCompleted hook feedback'
check "a later completion of the task was accepted"          test "$accepted_after" -ge 1
check "the gate recorded the task command green"             jq -e --arg c "$CHECK" '.checks[$c].green' "$state_file"
check "CHANGELOG.md has the token line at HEAD"             has "$(git show HEAD:CHANGELOG.md)" "slugify: $TOKEN"
check "the run made a commit"                                test "$(git rev-list --count "$BASE..HEAD")" -ge 1
check "bun test passes at HEAD"                              bun test
finish
