#!/usr/bin/env bash
# Run the benchmark without having to remember the venv path.
#   bash bench.sh            both systems, both tiers
#   bash bench.sh --tier A   the real, adversarial set only
#   bash bench.sh --system jev
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/python run.py "$@"
