#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p "$ROOT/.uv-cache" "$ROOT/.cache"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/.uv-cache}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$ROOT/.cache}"

export CREWAI_DISABLE_TELEMETRY=true
export OTEL_SDK_DISABLED=true

# 优先复用当前 shell 环境；如果 Codex 会话里没有，再补默认值
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:7890}"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7890}"
export http_proxy="${http_proxy:-$HTTP_PROXY}"
export https_proxy="${https_proxy:-$HTTPS_PROXY}"

# 避免误走 SOCKS
unset ALL_PROXY || true
unset all_proxy || true

export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost,::1}"
export no_proxy="${no_proxy:-$NO_PROXY}"

uv run kickoff