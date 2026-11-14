#!/usr/bin/env bash
# Checks that every plugin's manifest is valid, the marketplace lists every plugin, and
# every skill is well formed. A plugin in its own repository (study) is listed with a
# github or url source and has no folder here. Also checks
# that no plugin substitutes a credential-like name, and warns when a plugin changed but its version did not.
set -euo pipefail
cd "$(dirname "$0")/.."

for cmd in jq claude; do
  command -v "$cmd" >/dev/null || { echo "FAIL: $cmd is not on PATH"; exit 1; }
done

marketplace=.claude-plugin/marketplace.json
fail=0
err() { echo "FAIL: $*"; fail=1; }
warn() { echo "WARN: $*"; }

# Strict validation, with one warning let through: a plugin with no version, which ships every
# commit as a release (sdlc). The missing-icon note never changes the validator's result.
validate() {
  local out
  out=$(claude plugin validate "$1" --strict 2>&1) && { echo "$out"; return 0; }
  echo "$out"
  echo "$out" | grep -q -F 'version: No version specified' || return 1
  ! echo "$out" | grep -F '❯' | grep -v -F -e 'version: No version specified' -e 'ICON_MISSING' | grep -q .
}

m=$marketplace
jq -e . "$m" >/dev/null || err "$m is not valid JSON"

plugins=$(ls plugins)
listed=$(jq -r '.plugins[] | select((.source | type) != "object" or (.source.source | IN("github", "url") | not)) | .name' "$m" | sort)
[ "$listed" = "$plugins" ] || err "$m lists '$(echo $listed)', expected '$(echo $plugins)'"
for p in $plugins; do
  src=$(jq -r --arg p "$p" '.plugins[] | select(.name == $p) | .source | if type == "object" then .path else . end' "$m")
  [ "${src#./}" = "plugins/$p" ] || err "$m: $p source is '$src', not plugins/$p"
done

for p in $plugins; do
  dir=plugins/$p
  manifest=$dir/.claude-plugin/plugin.json
  jq -e . "$manifest" >/dev/null || err "$manifest is missing or not valid JSON"
  [ "$(jq -r .name "$manifest")" = "$p" ] || err "$dir: name does not match folder '$p'"
  [ -f "$dir/LICENSE" ] || err "$dir: missing LICENSE"
  words=$(sed '/^```/,/^```/d' "$dir/README.md" 2>/dev/null | wc -w)
  [ "$words" -ge 40 ] || err "$dir: README.md missing or under 40 words"

  for skill in "$dir"/skills/*/SKILL.md; do
    [ -e "$skill" ] || continue
    sdir=$(basename "$(dirname "$skill")")
    name=$(sed -n '2,/^---$/s/^name: *//p' "$skill")
    [ "$name" = "$sdir" ] || err "$skill: name '$name' does not match folder '$sdir'"
    sed -n '2,/^---$/p' "$skill" | grep -q '^description: ' || err "$skill: missing description"
  done

  # The plugin directory holds a plugin with a credential-like name inside a ${...} substitution,
  # even a JavaScript template literal (MCP_FORWARDS_CREDENTIAL_ENV). ${user_config.*} is allowed.
  hits=$(git grep -n -o -i -E '\$\{[^}]*(key|token|secret|password|auth)[^}]*\}' -- "$dir" | grep -v -i -F ':${user_config.' || true)
  [ -z "$hits" ] || { err "$dir: credential-like name in a \${...} substitution, which the plugin directory holds; rename it:"; echo "$hits"; }

  validate "$dir" || fail=1
done

# A plugin whose files changed since this branch left origin/main needs a version bump to
# ship. Compares the working tree's tracked files with origin/main as last fetched.
if base=$(git merge-base HEAD origin/main 2>/dev/null); then
  for p in $plugins; do
    f=plugins/$p/.claude-plugin/plugin.json
    git cat-file -e "$base:$f" 2>/dev/null || continue
    version=$(jq -r '.version // empty' "$f") || continue
    [ -n "$version" ] || continue
    if ! git diff --quiet "$base" -- "plugins/$p" && [ "$(git show "$base:$f" | jq -r .version)" = "$version" ]; then
      warn "plugins/$p changed since origin/main but its version is still $version"
    fi
  done
fi

validate . || fail=1

[ "$fail" -eq 0 ] && echo "All checks passed."
exit "$fail"
