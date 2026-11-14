#!/bin/bash
# Build the base commit and the work commit, then leave the repo at the work.
exec bash "$(dirname "$0")/../../setup_repo.sh" "$(dirname "$0")/fixture"
