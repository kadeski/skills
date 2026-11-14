# Shared setup for the headless /slice tests (slice-gate.sh, slice-pr.sh, slice-risk.sh). Source it.
# Each test makes a scratch repo with one passing bun test, the gate and rules from
# hooks/project-settings.example.json, a one-slice spec, and copies of the skills under test,
# then runs `claude -p "/slice ..."` there and checks the transcript, the gate state and git.
#
#   MODEL, EFFORT, BUDGET   passed to claude (default opus, medium, 5 USD)
#   KEEP                    directory for the scratch repo and the transcript (default: a new temp dir)
# --setting-sources project keeps user-level skills and settings out, so the copies under test run.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS="$(cd "$HERE/../../plugins/sdlc" && pwd)"
MODEL="${MODEL:-opus}"; EFFORT="${EFFORT:-medium}"; BUDGET="${BUDGET:-5}"
WORK="${KEEP:-$(mktemp -d)}"
REPO="$WORK/repo"
OUT="$WORK/transcript.jsonl"
mark="scratch-copy-$$-$RANDOM"
pass=0; fail=0

need() { for c in "$@"; do command -v "$c" >/dev/null || { echo "$(basename "$0"): $c not found"; exit 2; }; done; }
need claude git bun jq node

# scratch_repo <dir> <risk>: a git repo on main with clamp() and its test, the gate, the example
# settings, a CLAUDE.md naming `bun test` as the checks, and docs/specs/slugify.md with one slice.
# If <dir> is already a clone, its files are replaced and the caller commits the result.
scratch_repo() {
  local dir="$1" risk="$2"
  if [ -d "$dir/.git" ]; then
    (cd "$dir" && git rm -rqf --ignore-unmatch . >/dev/null)
  else
    mkdir -p "$dir" && (cd "$dir" && git init -q -b main)
  fi
  mkdir -p "$dir/src" "$dir/docs/specs" "$dir/.claude/hooks" "$dir/.claude/skills" && cd "$dir" || exit 2
  git config user.email t@t && git config user.name t
  cat > CLAUDE.md <<'EOF'
# sdlc-scratch

A throwaway repo made by a test in kadeski/skills for one headless run. Nothing here ships.

- **Checks:** `bun test`.
- **Specs:** `docs/specs/`.
EOF
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
  cat > docs/specs/slugify.md <<EOF
# Slugify

Tier: 2 · Status: building · Risk: $risk
<!-- Status: draft -> building -> done -->

## Goal

\`slugify(title)\` turns a post title into the slug used in its URL.

## Done when

- [ ] \`bun test\` -> passes, with \`src/slugify.test.ts\` checking that \`slugify("Hello, World!")\` is \`"hello-world"\` and \`slugify("  --A  b__c--  ")\` is \`"a-b-c"\`

## Out of scope

- Unicode transliteration, a length limit, or any caller of \`slugify\`.

## Decisions

- none

## Open questions

- none

## Slices

- [ ] 1. \`slugify(title: string): string\` in \`src/slugify.ts\` lowercases the title, turns each run of characters other than a-z and 0-9 into one dash, and drops a dash at either end - test: the two examples in Done when - copy: \`src/clamp.ts\`
EOF
  cp "$SKILLS/hooks/project-settings.example.json" .claude/settings.json
  cp "$SKILLS/hooks/stop-gate/stop-gate.mjs" .claude/hooks/stop-gate.mjs
  printf '{ "stop": "bun test" }\n' > .claude/checks.json
  # Each skill copy ends in a marker line, so a tool result that holds the marker read that copy.
  local s
  for s in slice verify lesson; do
    cp -R "$SKILLS/skills/$s" ".claude/skills/$s"
    printf '\n<!-- %s-%s -->\n' "$mark" "$s" >> ".claude/skills/$s/SKILL.md"
  done
  echo ".claude/skills/" >> .git/info/exclude   # the skills under test never land in the run's commits
}

# run_slice <prompt>: one headless run in $PWD, transcript to $OUT.
# MSYS_NO_PATHCONV: Git Bash on Windows would turn "/slice ..." into a file path.
run_slice() {
  MSYS_NO_PATHCONV=1 claude -p "$1" --setting-sources project --strict-mcp-config \
    --model "$MODEL" --effort "$EFFORT" --max-budget-usd "$BUDGET" --permission-mode auto \
    --no-session-persistence --output-format stream-json --verbose < /dev/null 2> "$WORK/stderr.log" \
    | grep '^{' > "$OUT"
  echo "transcript:   $OUT   cost: $(jq -rs 'map(select(.type=="result")) | last | .total_cost_usd // "?"' "$OUT") USD"
}

check() { # name, command...
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "ok   - $name"; pass=$((pass+1)); else echo "FAIL - $name"; fail=$((fail+1)); fi
}
not() { ! "$@"; }
has() { grep -Eq -- "$2" <<<"$1"; }
final_result() { jq -rs 'map(select(.type=="result")) | last | .result // ""' "$OUT"; }
tool_results() {
  jq -r 'select(.type=="user") | .message.content | arrays | .[] | select(.type=="tool_result")
    | .content | if type=="array" then map(.text // "") | join("") else tostring end' "$OUT"
}
# The last non-blank line of the final message, past code fences.
last_line() { grep -v -e '^[[:space:]]*$' -e '^[[:space:]]*```' <<<"$(final_result)" | tail -1; }
finish() { echo "---- $pass passed, $fail failed"; [ "$fail" -eq 0 ]; }
