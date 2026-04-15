#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/web"

export PAPER_ANALYSIS_CONFIG_PATH="${PAPER_ANALYSIS_CONFIG_PATH:-$ROOT/config/app.json}"

npm run dev
