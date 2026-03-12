"""Download tool for one or more papers."""

import asyncio

from ..adapters.core_results import core_to_mcp_download_result
from ..formatters import format_batch_results
from ..runtime import get_runtime_config
from ..server import mcp
from ..services.download_service import download_many_sync

MAX_BATCH_SIZE = 50
BATCH_DELAY_SECONDS = 2
DEFAULT_PARALLEL_DOWNLOADS = 10
MAX_PARALLEL_DOWNLOADS = 50

# Backward-compatible export for tests and external imports.
_format_core_result = core_to_mcp_download_result


@mcp.tool()
async def paper_download(
    identifiers: list[str],
    output_dir: str | None = None,
    parallel: int = DEFAULT_PARALLEL_DOWNLOADS,
    to_markdown: bool = False,
    md_output_dir: str | None = None,
) -> str:
    """
    Download one or more academic papers by DOI, arXiv ID, or URL.
    Runs with configurable parallel workers (1-50 max, default parallel=10).
    When `parallel=1`, items are processed sequentially with a 2s delay between items.
    Optionally converts PDFs to Markdown in `md_output_dir` (default: `<output_dir>/md`).

    Source behavior:
    - arXiv IDs: arXiv is prioritized first.
    - DOI/URL inputs: OA sources are preferred (OpenAlex, Unpaywall, direct OA URLs).
    - CORE is disabled by default in MCP runtime configuration.
    - Sci-Hub is only considered for DOI-based flows, mainly as fallback for older/unknown-year papers.
    - For papers detected as 2021 or later, routing is OA-only (Sci-Hub skipped).

    Args:
        identifiers: List of DOIs, arXiv IDs, or URLs
        output_dir: Save directory (default runtime fallback: `PAPER_DOWNLOAD_OUTPUT_DIR` or `./downloads`)
        parallel: Number of concurrent downloads (1-50, default: 10)
        to_markdown: Convert downloaded PDFs to Markdown (default: False)
        md_output_dir: Directory for generated Markdown files (default: '<output_dir>/md')

    Returns:
        Markdown summary with statistics, successes, and failures

    Examples:
        paper_download(["10.1038/nature12373"])  # single item
        paper_download(["10.1038/nature12373", "2301.00001"])  # multiple items
    """
    if not identifiers:
        return (
            "# Error\n\nNo identifiers provided. Please provide at least one DOI, arXiv ID, or URL."
        )

    if len(identifiers) > MAX_BATCH_SIZE:
        return (
            "# Error\n\n"
            f"Too many identifiers ({len(identifiers)}). "
            f"Maximum {MAX_BATCH_SIZE} papers per batch.\n\n"
            "**Suggestion**: Split into multiple smaller batches."
        )

    if parallel < 1 or parallel > MAX_PARALLEL_DOWNLOADS:
        return (
            "# Error\n\n"
            f"Invalid `parallel` value: {parallel}. "
            f"Allowed range is 1-{MAX_PARALLEL_DOWNLOADS}."
        )

    results = await asyncio.to_thread(
        download_many_sync,
        config=get_runtime_config(),
        identifiers=identifiers,
        output_dir=output_dir,
        parallel=parallel,
        to_markdown=to_markdown,
        md_output_dir=md_output_dir,
        delay_seconds=BATCH_DELAY_SECONDS,
    )

    return format_batch_results(results)
