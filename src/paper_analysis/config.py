from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int


@dataclass(frozen=True)
class AppConfig:
    backend: ServerConfig
    frontend: ServerConfig

    @property
    def backend_base_url(self) -> str:
        return f"http://{self.backend.host}:{self.backend.port}"

    @property
    def frontend_base_url(self) -> str:
        return f"http://{self.frontend.host}:{self.frontend.port}"

    @property
    def cors_origins(self) -> list[str]:
        origins = {self.frontend_base_url}
        if self.frontend.host == "127.0.0.1":
            origins.add(f"http://localhost:{self.frontend.port}")
        if self.frontend.host == "localhost":
            origins.add(f"http://127.0.0.1:{self.frontend.port}")
        return sorted(origins)


def get_default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "app.json"


@lru_cache(maxsize=1)
def get_app_config() -> AppConfig:
    config_path = Path(os.getenv("PAPER_ANALYSIS_CONFIG_PATH", str(get_default_config_path())))
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return AppConfig(
        backend=ServerConfig(**payload["backend"]),
        frontend=ServerConfig(**payload["frontend"]),
    )
