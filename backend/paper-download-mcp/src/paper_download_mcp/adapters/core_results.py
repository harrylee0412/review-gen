"""Result adapters from scihub_core to MCP models."""

from __future__ import annotations

import os

from ..models import DownloadResult
from ..scihub_core.models import DownloadResult as CoreDownloadResult


def core_to_mcp_download_result(core_result: CoreDownloadResult) -> DownloadResult:
    """Convert scihub-core download results into MCP-friendly results."""
    doi = core_result.normalized_identifier or core_result.identifier
    file_path = os.path.abspath(core_result.file_path) if core_result.file_path else None
    md_path = os.path.abspath(core_result.md_path) if core_result.md_path else None
    file_size = core_result.file_size
    if file_path and file_size is None and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)

    source = core_result.source
    if not source and isinstance(core_result.metadata, dict):
        source = core_result.metadata.get("source")

    return DownloadResult(
        doi=doi,
        success=core_result.success,
        file_path=file_path,
        file_size=file_size,
        title=core_result.title,
        year=core_result.year,
        source=source,
        download_time=core_result.download_time,
        error=core_result.error,
        md_path=md_path,
        md_success=core_result.md_success,
        md_error=core_result.md_error,
    )
