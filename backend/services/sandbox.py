from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SandboxConfig:
    enabled: bool = False
    image: str | None = None
    cpu_limit: float | None = None
    memory_limit_mb: int | None = None
    timeout_seconds: int = 30
    network_disabled: bool = True
    read_only_filesystem: bool = True


class SandboxService:
    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()

    def is_available(self) -> bool:
        return self.config.enabled and self.config.image is not None

    def execute(self, code: str, language: str):
        raise RuntimeError("Code execution is disabled in the initial build. Use a secure sandbox before enabling it.")
