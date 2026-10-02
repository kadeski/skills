#!/usr/bin/env bash
# Checks that every plugin's manifests agree, every marketplace lists every plugin,
# and every skill is well formed.
set -euo pipefail
cd "$(dirname "$0")/.."

marketplaces=(.claude-plugin/marketplace.json .agents/plugins/marketplace.json .cursor-plugin/marketplace.json)
fail=0
err() { echo "FAIL: $*"; fail=1; }

for f in "${marketplaces[@]}"; do
  jq -e . "$f" >/dev/null || err "$f is not valid JSON"
done

plugins=$(ls plugins)
for m in "${marketplaces[@]}"; do
  listed=$(jq -r '.plugins[].name' "$m" | sort)
  [ "$listed" = "$plugins" ] || err "$m lists '$(echo $listed)', plugins/ has '$(echo $plugins)'"
  for p in $plugins; do
    src=$(jq -r --arg p "$p" '.plugins[] | select(.name == $p) | .source | if type == "object" then .path else . end' "$m")
    [ "${src#./}" = "plugins/$p" ] || err "$m: $p source is '$src', not plugins/$p"
  done
done

for p in $plugins; do
  dir=plugins/$p
  manifests=("$dir/.claude-plugin/plugin.json" "$dir/plugin.json" "$dir/.cursor-plugin/plugin.json")
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

claude plugin validate . --strict || fail=1

[ "$fail" -eq 0 ] && echo "All checks passed."
exit "$fail"
