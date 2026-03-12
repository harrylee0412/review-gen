"""Runtime configuration access for MCP tool execution."""

from __future__ import annotations

import os
from dataclasses import dataclass

EMAIL_ENV_KEYS = ("PAPER_DOWNLOAD_EMAIL", "SCIHUB_CLI_EMAIL")
OUTPUT_DIR_ENV_KEYS = ("PAPER_DOWNLOAD_OUTPUT_DIR", "SCIHUB_OUTPUT_DIR")
FALLBACK_OUTPUT_DIR = "./downloads"


@dataclass(frozen=True)
class RuntimeConfig:
    """Resolved runtime configuration for tool execution."""

    email: str | None
    default_output_dir: str


def _first_env(keys: tuple[str, ...]) -> str | None:
    """Return the first non-empty environment variable value for the given keys."""
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def get_runtime_config() -> RuntimeConfig:
    """Resolve runtime config with backward-compatible environment variable fallbacks."""
    email = _first_env(EMAIL_ENV_KEYS)
    output_dir = _first_env(OUTPUT_DIR_ENV_KEYS) or FALLBACK_OUTPUT_DIR
    return RuntimeConfig(email=email, default_output_dir=output_dir)
