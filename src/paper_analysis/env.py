from __future__ import annotations

import os
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_project_dotenv(dotenv_path: Path | None = None) -> bool:
    path = dotenv_path or get_project_root() / ".env"
    if not path.is_file():
        return False

    loaded = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        os.environ[key] = _normalize_env_value(raw_value.strip())
        loaded = True

    return loaded


def _normalize_env_value(raw_value: str) -> str:
    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {'"', "'"}:
        return raw_value[1:-1]
    return raw_value
