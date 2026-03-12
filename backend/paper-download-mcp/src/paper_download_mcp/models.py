"""Pydantic models for MCP tool inputs and internal data structures."""

from dataclasses import dataclass

from pydantic import BaseModel, Field


class DownloadPaperInput(BaseModel):
    """Input schema for single paper download tool."""

    identifier: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="DOI or URL of the paper to download (e.g., '10.1038/nature12373' or 'https://doi.org/...')",
    )
    output_dir: str | None = Field(
        default="./downloads",
        description="Directory to save the downloaded PDF (default: './downloads')",
    )


class BatchDownloadInput(BaseModel):
    """Input schema for batch paper download tool."""

    identifiers: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of DOIs or URLs to download (1-50 papers)",
    )
    output_dir: str | None = Field(
        default="./downloads",
        description="Directory to save the downloaded PDFs (default: './downloads')",
    )


class GetMetadataInput(BaseModel):
    """Input schema for paper metadata retrieval tool."""

    identifier: str = Field(..., description="DOI or URL of the paper to retrieve metadata for")


@dataclass
class DownloadResult:
    """Internal data class for download operation results."""

    doi: str
    success: bool
    file_path: str | None = None
    file_size: int | None = None
    title: str | None = None
    year: int | None = None
    source: str | None = None
    download_time: float | None = None
    error: str | None = None
    md_path: str | None = None
    md_success: bool | None = None
    md_error: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "doi": self.doi,
            "success": self.success,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "title": self.title,
            "year": self.year,
            "source": self.source,
            "download_time": self.download_time,
            "error": self.error,
            "md_path": self.md_path,
            "md_success": self.md_success,
            "md_error": self.md_error,
        }
