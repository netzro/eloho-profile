#!/usr/bin/env bash
# Eloho CLI runner — Autonomous NGX Investment Agent
# Usage: ./run.sh [command] [options]
# Examples:
#   ./run.sh prices                  # Fetch & display current prices
#   ./run.sh prices --notify         # Fetch prices + Telegram alert
#   ./run.sh decide --dry-run        # Preview next DCA round (no save)
#   ./run.sh decide --commit         # Run DCA round + notify
#   ./run.sh decide --commit --json  # Run DCA round, output JSON
#   ./run.sh invoice --notify        # Stripe invoice for last round
#   ./run.sh report                  # Full portfolio report
#   ./run.sh report --json           # Portfolio report as JSON
#   ./run.sh status                  # System health check

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
uv run python -m eloho "$@"
