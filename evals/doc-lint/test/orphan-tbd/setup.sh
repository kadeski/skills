#!/bin/bash
# Seed the fixture repo into ~/cwd and commit it, with no remote, so the lint runs without an issue tracker.
set -e
python3 "$(dirname "$0")/../../../seed.py" "$(dirname "$0")/fixture" "$HOME"
cd "$HOME/cwd"
git init -q
git add -A
git -c user.name=eval -c user.email=eval@example.com commit -qm "fixture"
