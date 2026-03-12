from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REVIEW_GEN_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DOWNLOAD_REPO = REVIEW_GEN_ROOT / "backend" / "paper-download-mcp"
DEFAULT_RUNS_ROOT = Path("quality_reports") / "lit_review_runs"

MANIFEST_FIELDS = [
    "paper_key",
    "title",
    "year",
    "journal",
    "doi",
    "citations",
    "full_text_priority",
    "need_full_text",
    "expected_pdf_name",
    "pdf_status",
    "pdf_path",
    "download_status",
    "download_source",
    "download_error",
    "download_batch",
    "md_status",
    "md_path",
    "mineru_batch_id",
    "mineru_error",
]


def slugify(text: str, max_len: int = 80) -> str:
    import re

    cleaned = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", text.strip())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return (cleaned or "review").lower()[:max_len].strip("-") or "review"


def find_workspace(topic: str | None, workspace: str | None) -> Path:
    if workspace:
        return Path(workspace).resolve()
    if not topic:
        raise ValueError("Provide either --workspace or --topic.")
    return (DEFAULT_RUNS_ROOT / slugify(topic)).resolve()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def bootstrap_download_backend(repo_root: Path) -> dict[str, Any]:
    src_root = repo_root / "src"
    if not src_root.exists():
        raise FileNotFoundError(f"paper-download-mcp src directory not found: {src_root}")
    src_root_str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)

    from paper_download_mcp.runtime import RuntimeConfig, get_runtime_config
    from paper_download_mcp.services.download_service import download_many_sync

    return {
        "RuntimeConfig": RuntimeConfig,
        "get_runtime_config": get_runtime_config,
        "download_many_sync": download_many_sync,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download shortlisted papers from a review workspace manifest.")
    parser.add_argument("--topic", help="Review topic. Used to derive the workspace if --workspace is omitted.")
    parser.add_argument("--workspace", help="Existing review workspace path.")
    parser.add_argument("--repo-root", default=os.environ.get("PAPER_DOWNLOAD_MCP_ROOT", str(DEFAULT_DOWNLOAD_REPO)), help="Path to the paper-download-mcp repository. Defaults to the bundled backend or PAPER_DOWNLOAD_MCP_ROOT.")
    parser.add_argument("--parallel", type=int, default=3, help="Parallel paper downloads.")
    parser.add_argument("--email", help="Optional email for Unpaywall-backed resolution.")
    parser.add_argument("--min-priority", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--paper-keys", nargs="*", default=[], help="Optional paper_key whitelist.")
    parser.add_argument("--max-papers", type=int, help="Optional cap. Useful for downloading classics first.")
    parser.add_argument("--all-candidates", action="store_true", help="Download even if pdf_status is already ready.")
    parser.add_argument("--dry-run", action="store_true", help="Only show which papers would be downloaded.")
    return parser.parse_args()


def priority_value(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get((value or "").strip().lower(), 0)


def to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def normalize_pdf_path(path_value: str, fallback: Path) -> Path:
    if path_value:
        path = Path(path_value)
        if path.exists():
            return path
    return fallback


def candidate_rows(rows: list[dict[str, str]], *, min_priority: str, paper_keys: list[str], all_candidates: bool) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    selected: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    wanted_keys = set(paper_keys)
    threshold = priority_value(min_priority)
    for row in rows:
        if wanted_keys and row.get("paper_key", "") not in wanted_keys:
            continue
        if priority_value(row.get("full_text_priority", "")) < threshold:
            continue
        if not row.get("need_full_text", "").strip().lower() in {"yes", "y", "true", "1"}:
            continue
        if not all_candidates and row.get("pdf_status", "") == "ready" and row.get("pdf_path", ""):
            path = Path(row["pdf_path"])
            if path.exists():
                continue
        if not row.get("doi", "").strip():
            skipped.append({
                "paper_key": row.get("paper_key", ""),
                "title": row.get("title", ""),
                "reason": "missing_doi",
            })
            continue
        selected.append(row)

    selected.sort(
        key=lambda row: (
            -priority_value(row.get("full_text_priority", "")),
            -to_int(row.get("citations", 0)),
            -to_int(row.get("year", 0)),
            row.get("title", ""),
        )
    )
    return selected, skipped


def rename_to_expected(downloaded_path: Path, destination_dir: Path, expected_name: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / expected_name
    if downloaded_path.resolve() == destination.resolve():
        return destination
    if destination.exists():
        destination.unlink()
    shutil.move(str(downloaded_path), str(destination))
    return destination


def main() -> int:
    args = parse_args()
    workspace = find_workspace(args.topic, args.workspace)
    manifest_path = workspace / "04_fulltext" / "fulltext_manifest.csv"
    if not manifest_path.exists():
        raise SystemExit("fulltext_manifest.csv is missing. Run prepare-fulltext-manifest first.")

    rows = read_csv_rows(manifest_path)
    if not rows:
        raise SystemExit("fulltext_manifest.csv is empty. Run prepare-fulltext-manifest first.")

    selected, skipped = candidate_rows(
        rows,
        min_priority=args.min_priority,
        paper_keys=args.paper_keys,
        all_candidates=args.all_candidates,
    )
    if args.max_papers is not None:
        selected = selected[: max(0, args.max_papers)]

    batch_label = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = workspace / "04_fulltext" / "download_batches"
    batch_dir.mkdir(parents=True, exist_ok=True)

    preview = [
        {
            "paper_key": row.get("paper_key", ""),
            "title": row.get("title", ""),
            "doi": row.get("doi", ""),
            "priority": row.get("full_text_priority", ""),
            "citations": row.get("citations", ""),
        }
        for row in selected
    ]

    if args.dry_run:
        payload = {
            "workspace": str(workspace),
            "manifest_path": str(manifest_path),
            "download_repo": args.repo_root,
            "batch_label": batch_label,
            "selected_count": len(selected),
            "skipped_without_identifier": skipped,
            "candidates": preview,
            "dry_run": True,
        }
        write_json(batch_dir / f"{batch_label}_dry_run.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not selected:
        payload = {
            "workspace": str(workspace),
            "manifest_path": str(manifest_path),
            "download_repo": args.repo_root,
            "batch_label": batch_label,
            "selected_count": 0,
            "skipped_without_identifier": skipped,
            "candidates": [],
            "dry_run": False,
        }
        write_json(batch_dir / f"{batch_label}.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    modules = bootstrap_download_backend(Path(args.repo_root))
    output_dir = workspace / "04_fulltext" / "pdf_inbox"
    runtime = modules["get_runtime_config"]()
    config = modules["RuntimeConfig"](
        email=args.email or runtime.email,
        default_output_dir=str(output_dir),
    )

    identifiers = [row["doi"] for row in selected]
    results = modules["download_many_sync"](
        config=config,
        identifiers=identifiers,
        output_dir=str(output_dir),
        parallel=args.parallel,
        to_markdown=False,
        md_output_dir=None,
    )

    row_map = {row.get("paper_key", ""): row for row in rows}
    batch_results: list[dict[str, Any]] = []
    for row, result in zip(selected, results):
        manifest_row = row_map[row.get("paper_key", "")]
        record = result.to_dict() if hasattr(result, "to_dict") else vars(result)
        manifest_row["download_batch"] = batch_label
        manifest_row["download_source"] = record.get("source", "") or ""
        manifest_row["download_error"] = record.get("error", "") or ""
        if record.get("success") and record.get("file_path"):
            downloaded = Path(record["file_path"])
            if downloaded.exists():
                final_path = rename_to_expected(downloaded, output_dir, manifest_row.get("expected_pdf_name", downloaded.name))
                manifest_row["pdf_status"] = "ready"
                manifest_row["pdf_path"] = str(final_path)
                manifest_row["download_status"] = "downloaded"
            else:
                manifest_row["pdf_status"] = "missing"
                manifest_row["pdf_path"] = ""
                manifest_row["download_status"] = "download_missing_file"
                if not manifest_row["download_error"]:
                    manifest_row["download_error"] = "Downloader reported success but no local PDF file was found."
        else:
            fallback = output_dir / manifest_row.get("expected_pdf_name", "")
            manifest_row["pdf_status"] = "ready" if fallback.exists() else "missing"
            manifest_row["pdf_path"] = str(fallback) if fallback.exists() else ""
            manifest_row["download_status"] = "failed"
        batch_results.append(
            {
                "paper_key": manifest_row.get("paper_key", ""),
                "title": manifest_row.get("title", ""),
                "doi": manifest_row.get("doi", ""),
                "download_status": manifest_row.get("download_status", ""),
                "download_source": manifest_row.get("download_source", ""),
                "download_error": manifest_row.get("download_error", ""),
                "pdf_path": manifest_row.get("pdf_path", ""),
            }
        )

    for item in skipped:
        row = row_map.get(item["paper_key"])
        if row is not None:
            row["download_batch"] = batch_label
            row["download_status"] = "missing_identifier"
            row["download_error"] = "No DOI available for automated download."

    write_csv(manifest_path, rows, MANIFEST_FIELDS)
    payload = {
        "workspace": str(workspace),
        "manifest_path": str(manifest_path),
        "download_repo": args.repo_root,
        "batch_label": batch_label,
        "selected_count": len(selected),
        "downloaded": sum(1 for item in batch_results if item["download_status"] == "downloaded"),
        "failed": sum(1 for item in batch_results if item["download_status"] != "downloaded"),
        "skipped_without_identifier": skipped,
        "results": batch_results,
        "dry_run": False,
    }
    write_json(batch_dir / f"{batch_label}.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
