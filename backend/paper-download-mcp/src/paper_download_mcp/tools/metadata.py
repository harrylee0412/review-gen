"""Metadata retrieval tool for academic papers."""

import asyncio

from ..formatters import format_metadata
from ..runtime import get_runtime_config
from ..server import mcp
from ..services.metadata_service import get_metadata_sync


@mcp.tool()
async def paper_get_metadata(identifier: str) -> str:
    """
    Get paper metadata without downloading (fast, <1s).

    Sources: Unpaywall, Crossref, arXiv APIs
    Returns: title, authors, year, journal, OA status, available sources
    Notes:
    - arXiv identifiers are resolved via arXiv metadata APIs.
    - For DOI inputs, `available_sources` reflects routing semantics:
      - OA sources (Unpaywall) when available.
      - `Sci-Hub` is listed only when publication year is inferred as < 2021.

    Args:
        identifier: DOI, arXiv ID, or URL

    Returns:
        JSON with metadata fields

    Examples:
        paper_get_metadata("10.1038/nature12373")  # DOI
        paper_get_metadata("2301.00001")  # arXiv ID
    """

    metadata = await asyncio.to_thread(
        get_metadata_sync,
        config=get_runtime_config(),
        identifier=identifier,
    )

    return format_metadata(metadata)
