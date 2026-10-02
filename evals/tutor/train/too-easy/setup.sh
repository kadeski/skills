#!/bin/bash
exec python3 "$(dirname "$0")/../../../seed.py" "$(dirname "$0")/fixture" "$HOME"
