"""Response formatters for MCP tool outputs."""

import json

from .models import DownloadResult


def format_download_result(result: DownloadResult) -> str:
    """
    Format a single download result as Markdown.

    Args:
        result: DownloadResult object containing download operation details

    Returns:
        Formatted Markdown string with download details or error message
    """
    if result.success:
        # Success case
        lines = ["# Paper Downloaded Successfully", ""]
        lines.append(f"**DOI**: {result.doi}")

        if result.title:
            lines.append(f"**Title**: {result.title}")

        if result.year:
            lines.append(f"**Year**: {result.year}")

        if result.file_path:
            lines.append(f"**File Path**: `{result.file_path}`")

        if result.file_size:
            size_kb = result.file_size / 1024
            lines.append(f"**File Size**: {size_kb:.1f} KB")

        if result.source:
            lines.append(f"**Source**: {result.source}")

        if result.download_time:
            lines.append(f"**Download Time**: {result.download_time:.2f}s")

        if result.md_success is True:
            lines.append("**Markdown Conversion**: Success")
        elif result.md_success is False:
            lines.append("**Markdown Conversion**: Failed (PDF download still succeeded)")

        if result.md_path:
            lines.append(f"**Markdown Path**: `{result.md_path}`")

        if result.md_error:
            lines.append(f"**Markdown Error**: {result.md_error}")

        return "\n".join(lines)
    else:
        # Failure case
        lines = ["# Download Failed", ""]
        lines.append(f"**DOI**: {result.doi}")

        if result.error:
            lines.append(f"**Error**: {result.error}")
        else:
            lines.append("**Error**: Unknown error occurred")

        lines.append("")
        lines.append("**Suggestions**:")
        lines.append("- Verify the DOI is correct (check on doi.org)")
        lines.append("- Try `paper_get_metadata` to check paper availability")
        lines.append("- The paper may be too recent (not yet indexed)")
        lines.append("- Check if the paper is behind a paywall with no open access")

        return "\n".join(lines)


def format_batch_results(results: list[DownloadResult]) -> str:
    """
    Format batch download results as Markdown summary.

    Args:
        results: List of DownloadResult objects

    Returns:
        Formatted Markdown string with summary and detailed results
    """
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful
    total_time = sum(r.download_time for r in results if r.download_time)

    lines = ["# Download Summary", ""]

    # Summary statistics
    lines.append(f"**Total Papers**: {total}")
    lines.append(f"**Successful**: {successful} ({successful / total * 100:.1f}%)")
    lines.append(f"**Failed**: {failed} ({failed / total * 100:.1f}%)")
    lines.append(f"**Total Time**: {total_time:.2f}s")
    lines.append("")

    # Successful downloads
    if successful > 0:
        lines.append("## Successfully Downloaded")
        lines.append("")
        for i, result in enumerate(results, 1):
            if result.success:
                title = result.title or result.doi
                size_kb = result.file_size / 1024 if result.file_size else 0
                source = result.source or "Unknown"
                lines.append(f"{i}. **{title}** ({size_kb:.1f} KB, {source})")
                if result.file_path:
                    lines.append(f"   - Path: `{result.file_path}`")
                if result.md_success is True:
                    lines.append("   - Markdown: Success")
                elif result.md_success is False:
                    lines.append("   - Markdown: Failed")
                if result.md_path:
                    lines.append(f"   - Markdown Path: `{result.md_path}`")
                if result.md_error:
                    lines.append(f"   - Markdown Error: {result.md_error}")
        lines.append("")

    # Failed downloads
    if failed > 0:
        lines.append("## Failed Downloads")
        lines.append("")
        for i, result in enumerate(results, 1):
            if not result.success:
                error = result.error or "Unknown error"
                lines.append(f"{i}. **{result.doi}**")
                lines.append(f"   - Error: {error}")
        lines.append("")

    return "\n".join(lines)


def format_metadata(metadata: dict) -> str:
    """
    Format paper metadata as pretty-printed JSON.

    Args:
        metadata: Dictionary containing paper metadata

    Returns:
        JSON-formatted string with proper indentation
    """
    return json.dumps(metadata, indent=2, ensure_ascii=False)
