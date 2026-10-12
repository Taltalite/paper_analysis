#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PAPER_ANALYSIS_CONFIG_PATH="${PAPER_ANALYSIS_CONFIG_PATH:-$ROOT/config/app.json}"

exec bash "$ROOT/scripts/run.sh" serve_api
