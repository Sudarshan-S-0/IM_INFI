from __future__ import annotations

import logging
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


# Configure a single logger instance.
logger = logging.getLogger("workflow_agent")
logger.setLevel(logging.INFO)

if not logger.handlers:
    logs_dir = _project_root() / "workflow_agent" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "verification.log"

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Also log to console for interactive runs.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def log_info(message: str) -> None:
    logger.info(message)


def log_error(message: str) -> None:
    logger.error(message)

