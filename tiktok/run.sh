#!/bin/zsh
# Data-only refresh plus rebuild (no written-lesson updates). For the full teardown, run /retention-teardown in Claude Code.
# Usage: ~/.claude/skills/tiktok-retention-teardown/run.sh [--account <name>] [--surface surface:N] [--skip-gemini]
# The same arguments go to both scripts: build_report.py reads only --account and ignores the rest.
set -e
HERE=${0:A:h}
python3 $HERE/scraping/daily.py "$@"
python3 $HERE/scraping/build_report.py "$@"
