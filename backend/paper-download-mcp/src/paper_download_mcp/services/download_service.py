"""Blocking download workflows used by MCP tools."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..adapters.core_results import core_to_mcp_download_result
from ..models import DownloadResult
from ..runtime import RuntimeConfig
from ..scihub_core.client import SciHubClient
from ..scihub_core.core.doi_processor import DOIProcessor


def _build_client(
    *,
    config: RuntimeConfig,
    output_dir: str | None,
    to_markdown: bool,
    md_output_dir: str | None,
) -> SciHubClient:
    """Create a configured SciHubClient instance for tool execution."""
    return SciHubClient(
        email=config.email or "",
        output_dir=output_dir or config.default_output_dir,
        convert_to_md=to_markdown,
        md_output_dir=md_output_dir,
        enable_core=False,
        fast_fail=True,
    )


def download_many_sync(
    *,
    config: RuntimeConfig,
    identifiers: list[str],
    output_dir: str | None,
    to_markdown: bool,
    md_output_dir: str | None,
    delay_seconds: int = 2,
    parallel: int = 10,
) -> list[DownloadResult]:
    """Download multiple papers with optional parallel workers using blocking core APIs."""
    results: list[DownloadResult] = []
    parallel = max(1, parallel)
    client = _build_client(
        config=config,
        output_dir=output_dir,
        to_markdown=to_markdown,
        md_output_dir=md_output_dir,
    )

    if parallel == 1 or len(identifiers) <= 1:
        for index, identifier in enumerate(identifiers):
            try:
                results.append(core_to_mcp_download_result(client.download_paper(identifier)))
            except Exception as e:
                results.append(DownloadResult(doi=identifier, success=False, error=str(e)))

            if index < len(identifiers) - 1:
                time.sleep(delay_seconds)
        return results

    unique_tasks = _build_parallel_unique_tasks(identifiers)
    workers = min(parallel, len(unique_tasks))
    unique_results: list[DownloadResult | None] = [None] * len(unique_tasks)
    ordered_results: list[DownloadResult | None] = [None] * len(identifiers)

    def _download_one(task_index: int, identifier: str) -> tuple[int, DownloadResult]:
        try:
            result = core_to_mcp_download_result(client.download_paper(identifier))
        except Exception as e:
            result = DownloadResult(doi=identifier, success=False, error=str(e))
        return task_index, result

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_task_index = {
            executor.submit(_download_one, task_index, representative): task_index
            for task_index, (representative, _original_indices) in enumerate(unique_tasks)
        }
        for future in as_completed(future_to_task_index):
            task_index, result = future.result()
            unique_results[task_index] = result

    for task_index, (_representative, original_indices) in enumerate(unique_tasks):
        mapped_result = unique_results[task_index]
        if mapped_result is None:
            continue
        for original_index in original_indices:
            ordered_results[original_index] = mapped_result

    return [result for result in ordered_results if result is not None]


def _build_parallel_unique_tasks(identifiers: list[str]) -> list[tuple[str, list[int]]]:
    """
    Build unique parallel download tasks and preserve mapping back to input positions.

    We normalize identifiers to avoid downloading the same paper concurrently via
    equivalent DOI forms (e.g. raw DOI and doi.org URL), which can race on output file writes.
    """
    doi_processor = DOIProcessor()
    grouped_indices: dict[str, list[int]] = {}

    for index, identifier in enumerate(identifiers):
        normalized = doi_processor.normalize_doi(identifier)
        grouped_indices.setdefault(normalized, []).append(index)

    tasks: list[tuple[str, list[int]]] = []
    for indices in grouped_indices.values():
        representative = identifiers[indices[0]]
        tasks.append((representative, indices))

    return tasks
