#!/usr/bin/env bash
# End-to-end test of the sdlc plugin's gate: with only the plugin loaded (`--plugin-dir`, and a
# scratch repo with no .claude/settings.json; --setting-sources project keeps user settings out),
# a stop is refused while the repo's .claude/checks.json check fails.
# A real model run (under a minute, cents): bash tests/sdlc/plugin-gate.sh
#   MODEL, BUDGET   passed to claude (default haiku, 0.5 USD)
#   KEEP            directory for the scratch repo and the transcript (default: a new temp dir)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILLS="$(cd "$HERE/../../plugins/sdlc" && pwd)"
MODEL="${MODEL:-haiku}"; BUDGET="${BUDGET:-0.5}"
WORK="${KEEP:-$(mktemp -d)}"
REPO="$WORK/repo"; OUT="$WORK/transcript.jsonl"; RUNS="$WORK/runs.log"
mp() { command -v cygpath >/dev/null && cygpath -m "$1" || echo "$1"; }
for c in claude git jq node; do command -v "$c" >/dev/null || { echo "plugin-gate.sh: $c not found"; exit 2; }; done

mkdir -p "$REPO/.claude" && cd "$REPO" || exit 2
git init -q -b main && git config user.email t@t && git config user.name t
# The check logs each run outside the repo and always fails, with a line the test looks for.
cat > "$WORK/check.js" <<JS
require('fs').appendFileSync('$(mp "$RUNS")', 'run\n');
console.log('plugin-gate-check: deliberately failing');
process.exit(1);
JS
printf '{ "stop": "node %s" }\n' "$(mp "$WORK/check.js")" > .claude/checks.json
echo hi > README.md && git add -A && git commit -qm init

claude -p "Reply with the single word ok. Don't run any tools or edit any files; if a hook says checks fail, say so in one line and stop." \
  --plugin-dir "$(mp "$SKILLS")" --setting-sources project --strict-mcp-config \
  --model "$MODEL" --max-budget-usd "$BUDGET" --no-session-persistence \
  --output-format stream-json --verbose < /dev/null 2> "$WORK/stderr.log" | grep '^{' > "$OUT"
echo "transcript: $OUT"

pass=0; fail=0
check() { local name="$1"; shift; if "$@" >/dev/null 2>&1; then echo "ok   - $name"; pass=$((pass+1)); else echo "FAIL - $name"; fail=$((fail+1)); fi; }
check "no settings file in the repo: only the plugin can bring the hook" test ! -e .claude/settings.json
check "the plugin's gate ran the checks file's command"  test -s "$RUNS"
check "the gate refused the stop (Stop hook feedback, try 1)" grep -q "stop-gate, try 1 of 3" "$OUT"
check "the refusal reached Claude with the check output" grep -q 'plugin-gate-check: deliberately failing' "$OUT"
echo "---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
