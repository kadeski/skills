#!/bin/bash
# Seed a verify case: fixture/cwd is the repo after the work, fixture/base holds the
# files as they were before it, and fixture/base-new.txt lists the files the work added.
# Builds two commits in ~/cwd, the base and one slice commit, so verify has a range to
# review, and leaves the tree at the work. No remote, so nothing is pushed or posted.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
python3 "$here/../seed.py" "$1" "$HOME"
cd "$HOME/cwd"
g() { git -c user.name=eval -c user.email=eval@example.com "$@"; }
cp -a . "$HOME/.work"
cp -a "$HOME/base/." .
while read -r f; do [ -n "$f" ] && rm -f "$f"; done < "$HOME/base-new.txt"
git init -q -b main
g add -A
g commit -qm "msgq: queue"
cp -a "$HOME/.work/." .
g add -A
g commit -qm "limit: slice 1 51st scheduled message is refused with 409"
rm -rf "$HOME/.work" "$HOME/base" "$HOME/base-new.txt"
