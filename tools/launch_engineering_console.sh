#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -x .venv/bin/python ]]; then
    exec .venv/bin/python tools/hardware_test.py
fi
exec python3 tools/hardware_test.py
