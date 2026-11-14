#!/usr/bin/env bash
# End-to-end test for stop-gate.mjs against a throwaway git repo.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
GATE="$HERE/../../plugins/sdlc/hooks/stop-gate/stop-gate.mjs"
WORK="$(mktemp -d)"
REPO="$WORK/repo"
RUNS="$WORK/runs.log"   # outside the repo, so logging a run doesn't change the fingerprint
mp() { command -v cygpath >/dev/null && cygpath -m "$1" || echo "$1"; }

mkdir -p "$REPO"
cat > "$WORK/check.js" <<EOF
const fs = require('fs');
fs.appendFileSync('$(mp "$RUNS")', 'run\n');
const s = fs.readFileSync('ok.txt', 'utf8').trim();
console.log('checking... state=' + s);
process.exit(s === 'pass' ? 0 : 1);
EOF
CHECK="node $(mp "$WORK/check.js")"

cd "$REPO" && git init -q && git config user.email t@t && git config user.name t
echo fail > ok.txt && git add -A && git commit -qm init

pass=0; fail=0
runs() { [ -f "$RUNS" ] && wc -l < "$RUNS" | tr -d ' ' || echo 0; }
stop() { # $1 = stop_hook_active, rest = command override
  local active="$1"; shift
  printf '{"session_id":"s1","cwd":"%s","hook_event_name":"Stop","stop_hook_active":%s}' "$(mp "$REPO")" "$active" \
    | node "$GATE" "${@:-$CHECK}"
}
expect() { # name, actual, pattern
  if [[ "$2" =~ $3 ]]; then echo "ok   - $1"; pass=$((pass+1)); else echo "FAIL - $1"; echo "       got: ${2:0:300}"; fail=$((fail+1)); fi
}

out=$(stop false); expect "failing checks block (try 1)" "$out" '"decision":"block".*try 1 of 3.*state=fail'
out=$(stop true);  expect "same turn blocks again (try 2)" "$out" 'try 2 of 3'
out=$(stop true);  expect "try 3" "$out" 'try 3 of 3'
out=$(stop true);  expect "cap reached: lets it stop + warns user" "$out" '"systemMessage".*still fails after 3 tries'
before=$(runs)
out=$(stop false); expect "after giving up, unchanged tree: silent" "$out" '^$'
expect "after giving up, unchanged tree: checks not rerun" "$(runs)" "^${before}$"

echo pass > ok.txt
before=$(runs)
out=$(stop false); expect "fixed: passes silently" "$out" '^$'
expect "fixed: checks ran" "$(runs)" "^$((before+1))$"
out=$(stop false); expect "unchanged since green: silent" "$out" '^$'
expect "unchanged since green: checks not rerun" "$(runs)" "^$((before+1))$"

echo new > untracked.txt
out=$(stop false); expect "untracked file change: reruns" "$(runs)" "^$((before+2))$"

git add -A && git commit -qm wip
out=$(stop false); expect "commit of same content: no rerun" "$(runs)" "^$((before+2))$"

echo fail > ok.txt
out=$(stop false); expect "new failure in a new turn blocks again (try 1)" "$out" 'try 1 of 3'

mkdir -p "$WORK/plain" && out=$(printf '{"cwd":"%s"}' "$(mp "$WORK/plain")" | node "$GATE" "$CHECK"; echo "exit=$?")
expect "not a git repo: does nothing" "$out" '^exit=0$'

before=$(runs)
out=$(printf '{"cwd":"%s"}' "$(mp "$REPO")" | node "$GATE" 2>&1; echo "exit=$?")
expect "no argument, no checks file: exit 0, silent" "$out" '^exit=0$'
expect "no argument, no checks file: nothing run" "$(runs)" "^${before}$"

[ -f "$(git rev-parse --git-path claude-stop-gate.json)" ] && [ -z "$(git status --porcelain | grep stop-gate)" ]
expect "state file lives in .git, not the work tree" "$?" '^0$'

# ---- TaskCompleted and .claude/checks.json, in a second repo
TREPO="$WORK/trepo"
mkdir -p "$TREPO/.claude" && cd "$TREPO" && git init -q && git config user.email t@t && git config user.name t
for k in task stop; do
  cat > "$WORK/$k.js" <<EOF
const fs = require('fs');
fs.appendFileSync('$(mp "$RUNS")', '$k\n');
const s = fs.readFileSync('ok.txt', 'utf8').trim();
console.log('$k check... state=' + s);
if (s === 'missing') console.log('cat: fixture.txt: No such file or directory');
process.exit(s === 'pass' || ('$k' === 'task' && s === 'taskpass') ? 0 : 1);
EOF
done
checks() { printf '%s\n' "$1" > .claude/checks.json; }
checks "{ \"stop\": \"node $(mp "$WORK/stop.js")\", \"task\": \"node $(mp "$WORK/task.js")\" }"
echo fail > ok.txt && git add -A && git commit -qm init
truns() { if [ -f "$RUNS" ]; then grep -c "^$1$" "$RUNS"; else echo 0; fi; }
task() { # $1 = task id. Prints stdout, a --stderr-- marker, stderr, then exit=<code>
  local o c
  o=$(printf '{"session_id":"s2","cwd":"%s","hook_event_name":"TaskCompleted","task_id":"%s","task_subject":"slice 1"}' "$(mp "$TREPO")" "$1" \
    | node "$GATE" 2>"$WORK/err"); c=$?
  printf '%s--stderr--%s\nexit=%s' "$o" "$(cat "$WORK/err")" "$c"
}
tstop() { printf '{"session_id":"s2","cwd":"%s","hook_event_name":"Stop","stop_hook_active":false}' "$(mp "$TREPO")" | node "$GATE"; }

t0=$(truns task); s0=$(truns stop)
out=$(task t1); expect "task done, failing check: exit 2" "$out" 'exit=2$'
expect "task done, failing check: the output tail is on stderr" "$out" '--stderr--.*task check\.\.\. state=fail'
expect "task done: runs the checks file's task command, not stop" "$(truns task) $(truns stop)" "^$((t0+1)) ${s0}$"
expect "task done, blocked: stdout is not empty, so a missing-file stderr can't downgrade it" "${out%%--stderr--*}" '[^[:space:]]'
out=$(task t1); expect "same task refused again (try 2)" "$out" 'try 2 of 3.*exit=2$'
out=$(task t1); expect "same task refused again (try 3)" "$out" 'try 3 of 3.*exit=2$'
out=$(task t1); expect "same task a 4th time: let through with a warning" "$out" '"systemMessage".*still fails after 3 tries.*exit=0$'
before=$(truns task)
out=$(task t2); expect "after giving up, unchanged tree: a new task is let through" "$out" '^--stderr--'$'\n''exit=0$'
expect "after giving up, unchanged tree: the task check is not rerun" "$(truns task)" "^${before}$"

echo missing > ok.txt
out=$(task t3); expect "a check that prints 'No such file or directory' still blocks" "$out" 'No such file or directory.*exit=2$'

echo taskpass > ok.txt
t0=$(truns task)
out=$(task t4); expect "task check green: exit 0" "$out" 'exit=0$'
out=$(task t5); expect "unchanged green tree: exit 0" "$out" 'exit=0$'
expect "unchanged green tree: the task check is not rerun" "$(truns task)" "^$((t0+1))$"
s0=$(truns stop)
out=$(tstop); expect "a green task command does not skip the stop command" "$(truns stop)" "^$((s0+1))$"
expect "stop runs the checks file's stop command, and blocks on it" "$out" '"decision":"block".*stop check\.\.\. state=taskpass'

checks "{ \"stop\": \"node $(mp "$WORK/stop.js")\" }"
echo fail > ok.txt; s0=$(truns stop)
out=$(task t6); expect "no task command: task done runs the stop command" "$(truns stop)" "^$((s0+1))$"

for i in 2 3 4; do out=$(task t6); done
expect "no task command: the 4th refusal of a task lets it through" "$out" 'still fails after 3 tries.*exit=0$'
out=$(tstop); expect "giving up on a task doesn't silence the Stop gate on the same command" "$out" '"decision":"block"'
SF="$(git rev-parse --git-path claude-stop-gate.json)"
echo pass > ok.txt; out=$(task t8); echo fail > ok.txt
out=$(task t9); expect "task t9 refused (try 1)" "$out" 'try 1 of 3'
printf '{"session_id":"s9","cwd":"%s","hook_event_name":"Stop"}' "$(mp "$TREPO")" | node "$GATE" >/dev/null
out=$(task t9); expect "another session's run doesn't reset a live task's count (try 2)" "$out" 'try 2 of 3'
jq '.tasks["old:t1"] = {"blocks": 2, "at": 0}' "$SF" > "$SF.new" && mv "$SF.new" "$SF"
out=$(task t9); expect "a fresh count survives another one's expiry (try 3)" "$out" 'try 3 of 3'
expect "a task count older than a day is dropped" "$(jq -r '.tasks | has("old:t1")' "$SF")" '^false$'

before=$(truns task)
out=$(printf '{"session_id":"s2","cwd":"%s","hook_event_name":"TaskCompleted","task_id":"t7"}' "$(mp "$TREPO")" | node "$GATE" "node $(mp "$WORK/task.js")" 2>&1)
expect "a command-line argument wins over the checks file" "$(truns task)" "^$((before+1))$"

echo '{"green":"abc","turn":{"session":"s1","blocks":1}}' > "$(git rev-parse --git-path claude-stop-gate.json)"
echo pass > ok.txt
out=$(tstop 2>&1; echo "exit=$?"); expect "an old-format state file is read without error" "$out" '^exit=0$'

rm -rf "$WORK"
echo "---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
