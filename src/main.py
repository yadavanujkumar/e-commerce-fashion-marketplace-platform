from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class MainConfig:
    enabled: bool = True


class Main:
    def __init__(self, config: MainConfig | None = None) -> None:
        self.config = config or MainConfig()

    def run(self, payload: str) -> dict[str, str]:
        if not payload or not payload.strip():
            raise ValueError("payload must be non-empty")
        logger.info("processing payload in main")
        return {"status": "ok", "value": payload.strip()}


def build_main_service() -> Main:
    return Main()
