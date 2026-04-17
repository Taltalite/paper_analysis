#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p "$ROOT/.uv-cache" "$ROOT/.cache"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/.uv-cache}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$ROOT/.cache}"
export PAPER_ANALYSIS_CONFIG_PATH="${PAPER_ANALYSIS_CONFIG_PATH:-$ROOT/config/app.json}"

uv run serve_api
