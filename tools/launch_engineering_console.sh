#!/usr/bin/env bash
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -x .venv/bin/python ]]; then
    python_bin=.venv/bin/python
else
    python_bin=python3
fi

"$python_bin" tools/hardware_test.py
status=$?
if (( status != 0 )); then
    printf '\nEngineering console exited with status %s.\n' "$status"
    read -r -p 'Press Enter to close this window...' _
fi
exit "$status"
