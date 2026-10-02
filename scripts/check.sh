#!/usr/bin/env bash
# Checks that every tool's manifest agrees and every skill is well formed.
set -euo pipefail
cd "$(dirname "$0")/.."

manifests=(.claude-plugin/plugin.json plugin.json .cursor-plugin/plugin.json gemini-extension.json)
fail=0
err() { echo "FAIL: $*"; fail=1; }

for f in "${manifests[@]}" .claude-plugin/marketplace.json .agents/plugins/marketplace.json; do
  jq -e . "$f" >/dev/null || err "$f is not valid JSON"
done

for key in name version; do
  values=$(for f in "${manifests[@]}"; do jq -r ".$key" "$f"; done | sort -u)
  [ "$(echo "$values" | wc -l)" -eq 1 ] || err "$key differs across manifests: $(echo $values)"
done

for skill in skills/*/SKILL.md; do
  dir=$(basename "$(dirname "$skill")")
  name=$(sed -n '2,/^---$/s/^name: *//p' "$skill")
  [ "$name" = "$dir" ] || err "$skill: name '$name' does not match folder '$dir'"
  sed -n '2,/^---$/p' "$skill" | grep -q '^description: ' || err "$skill: missing description"
done

claude plugin validate . --strict || fail=1
claude plugin validate .claude-plugin/plugin.json --strict || fail=1

[ "$fail" -eq 0 ] && echo "All checks passed."
exit "$fail"
