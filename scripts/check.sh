#!/usr/bin/env bash
# Checks that every plugin's manifests agree, every marketplace lists every plugin it
# should, and every skill is well formed. A plugin with only .claude-plugin/plugin.json
# is Claude-only: it is listed in the Claude Code marketplace and no other. Also checks
# that the tutor.js VERSION moves with the copies of it, and warns when a plugin changed
# but its version did not.
set -euo pipefail
cd "$(dirname "$0")/.."

for cmd in jq claude; do
  command -v "$cmd" >/dev/null || { echo "FAIL: $cmd is not on PATH"; exit 1; }
done

marketplaces=(.claude-plugin/marketplace.json .agents/plugins/marketplace.json .cursor-plugin/marketplace.json)
fail=0
err() { echo "FAIL: $*"; fail=1; }
warn() { echo "WARN: $*"; }

for f in "${marketplaces[@]}"; do
  jq -e . "$f" >/dev/null || err "$f is not valid JSON"
done

plugins=$(ls plugins)
claude_only() { [ ! -e "plugins/$1/plugin.json" ] && [ ! -e "plugins/$1/.cursor-plugin/plugin.json" ]; }
multi_agent=$(for p in $plugins; do claude_only "$p" || echo "$p"; done)
for m in "${marketplaces[@]}"; do
  expected=$plugins
  [ "$m" = .claude-plugin/marketplace.json ] || expected=$multi_agent
  listed=$(jq -r '.plugins[].name' "$m" | sort)
  [ "$listed" = "$expected" ] || err "$m lists '$(echo $listed)', expected '$(echo $expected)'"
  for p in $expected; do
    src=$(jq -r --arg p "$p" '.plugins[] | select(.name == $p) | .source | if type == "object" then .path else . end' "$m")
    [ "${src#./}" = "plugins/$p" ] || err "$m: $p source is '$src', not plugins/$p"
  done
done

for p in $plugins; do
  dir=plugins/$p
  manifests=("$dir/.claude-plugin/plugin.json")
  claude_only "$p" || manifests+=("$dir/plugin.json" "$dir/.cursor-plugin/plugin.json")
  for f in "${manifests[@]}"; do
    jq -e . "$f" >/dev/null || err "$f is missing or not valid JSON"
  done
  [ "$(jq -r .name "$dir/.claude-plugin/plugin.json")" = "$p" ] || err "$dir: name does not match folder '$p'"
  for key in name version; do
    values=$(for f in "${manifests[@]}"; do jq -r ".$key" "$f"; done | sort -u)
    [ "$(echo "$values" | wc -l)" -eq 1 ] || err "$dir: $key differs across manifests: $(echo $values)"
  done
  [ -f "$dir/LICENSE" ] || err "$dir: missing LICENSE"
  words=$(sed '/^```/,/^```/d' "$dir/README.md" 2>/dev/null | wc -w)
  [ "$words" -ge 40 ] || err "$dir: README.md missing or under 40 words"

  for skill in "$dir"/skills/*/SKILL.md; do
    sdir=$(basename "$(dirname "$skill")")
    name=$(sed -n '2,/^---$/s/^name: *//p' "$skill")
    [ "$name" = "$sdir" ] || err "$skill: name '$name' does not match folder '$sdir'"
    sed -n '2,/^---$/p' "$skill" | grep -q '^description: ' || err "$skill: missing description"
  done

  claude plugin validate "$dir" --strict || fail=1
done

# The page runtime's VERSION, the demo seed's goal/main.tutorJs and the SKILL.md example
# must be bumped together.
tutor=plugins/tutor/skills/tutor
js=$(sed -n 's/^ *const VERSION = \([0-9][0-9]*\);.*/\1/p' "$tutor/tutor.js")
seed=$(jq -r '.[] | select(.collection == "goal" and .doc_id == "main") | .data.tutorJs' demo/tutor/seed.json) || seed=
example=$(sed -n 's/.*"tutorJs": *\([0-9][0-9]*\).*/\1/p' "$tutor/SKILL.md" | sort -u)
[ -n "$js" ] && [ "$seed" = "$js" ] && [ "$example" = "$js" ] \
  || err "tutor.js VERSION is '$js' in $tutor/tutor.js, goal/main.tutorJs is '$seed' in demo/tutor/seed.json and the example tutorJs is '$(echo $example)' in $tutor/SKILL.md; bump them together"

# A plugin whose files changed since this branch left origin/main needs a version bump to
# ship. Compares the working tree's tracked files with origin/main as last fetched.
if base=$(git merge-base HEAD origin/main 2>/dev/null); then
  for p in $plugins; do
    f=plugins/$p/.claude-plugin/plugin.json
    git cat-file -e "$base:$f" 2>/dev/null || continue
    version=$(jq -r .version "$f") || continue
    if ! git diff --quiet "$base" -- "plugins/$p" && [ "$(git show "$base:$f" | jq -r .version)" = "$version" ]; then
      warn "plugins/$p changed since origin/main but its version is still $version"
    fi
  done
fi

claude plugin validate . --strict || fail=1

[ "$fail" -eq 0 ] && echo "All checks passed."
exit "$fail"
