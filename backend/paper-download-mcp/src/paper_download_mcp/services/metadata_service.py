"""Blocking metadata workflow used by MCP tools."""

from __future__ import annotations

from typing import Any

from ..runtime import RuntimeConfig
from ..scihub_core.core.doi_processor import DOIProcessor
from ..scihub_core.core.year_detector import YearDetector
from ..scihub_core.sources.arxiv_source import ArxivSource
from ..scihub_core.sources.unpaywall_source import UnpaywallSource


def get_metadata_sync(*, config: RuntimeConfig, identifier: str) -> dict[str, Any]:
    """Fetch metadata from arXiv/Unpaywall/Crossref with current tool semantics."""
    doi = DOIProcessor().normalize_doi(identifier)
    metadata: dict[str, Any] = {"doi": doi, "available_sources": []}
    available_sources: list[str] = []

    arxiv_source = ArxivSource(timeout=10)
    if arxiv_source.can_handle(doi):
        try:
            arxiv_data = arxiv_source.get_metadata(doi)
            if arxiv_data:
                metadata.update(arxiv_data)
                available_sources.append("arXiv")
            else:
                metadata["error"] = "Metadata not available from arXiv. Please verify the ID."
        except Exception as e:
            metadata["arxiv_error"] = str(e)

        metadata["available_sources"] = available_sources
        return metadata

    try:
        if config.email:
            unpaywall = UnpaywallSource(email=config.email, timeout=10)
            unpaywall_data = unpaywall.get_metadata(doi)
            if unpaywall_data:
                metadata.update(unpaywall_data)
                if unpaywall_data.get("is_oa"):
                    available_sources.append("Unpaywall")

                year = unpaywall_data.get("year")
                if year and year < 2021:
                    available_sources.append("Sci-Hub")
    except Exception as e:
        metadata["unpaywall_error"] = str(e)

    if "year" not in metadata or not metadata["year"]:
        try:
            year = YearDetector().get_year(doi)
            if year:
                metadata["year"] = year
                if year < 2021 and "Sci-Hub" not in available_sources:
                    available_sources.append("Sci-Hub")
        except Exception as e:
            metadata["crossref_error"] = str(e)

    metadata["available_sources"] = available_sources
    if not available_sources:
        metadata["error"] = (
            "Metadata not available from Unpaywall or Crossref. Please verify the DOI is correct."
        )
    return metadata
