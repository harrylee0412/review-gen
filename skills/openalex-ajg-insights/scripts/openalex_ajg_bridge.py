from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

REVIEW_GEN_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPO_ROOT = REVIEW_GEN_ROOT / "backend" / "openalex-ajg-mcp"


def bootstrap_repo(repo_root: Path) -> dict[str, Any]:
    src_root = repo_root / "src"
    if not src_root.exists():
        raise FileNotFoundError(f"Repository source folder not found: {src_root}")

    data_csv = repo_root / "data" / "ajg_2024_template.csv"
    if not data_csv.exists():
        raise FileNotFoundError(f"ABS/AJG CSV not found: {data_csv}")

    src_root_str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)

    from openalex_mcp.abs_loader import ABSCache
    from openalex_mcp.client import OpenAlexClient
    from openalex_mcp.report_generator import generate_excel_report
    from openalex_mcp.utils import reconstruct_abstract, works_to_ris_block

    return {
        "ABSCache": ABSCache,
        "OpenAlexClient": OpenAlexClient,
        "generate_excel_report": generate_excel_report,
        "reconstruct_abstract": reconstruct_abstract,
        "works_to_ris_block": works_to_ris_block,
        "data_csv": data_csv,
    }


def add_render_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format.",
    )
    parser.add_argument(
        "--output-path",
        help="Optional path to write the rendered output.",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge script for the bundled or user-specified openalex-ajg-mcp installation."
    )
    parser.add_argument(
        "--repo-root",
        default=os.environ.get("OPENALEX_AJG_MCP_ROOT", str(DEFAULT_REPO_ROOT)),
        help="Path to the openalex-ajg-mcp repository. Defaults to the bundled backend or OPENALEX_AJG_MCP_ROOT.",
    )
    add_render_args(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    search_abs = subparsers.add_parser("search-abs", help="Search ABS/AJG-ranked journals.")
    search_abs.add_argument("--query", required=True, help="Search query.")
    search_abs.add_argument("--field", default="", help="ABS/AJG field code.")
    search_abs.add_argument(
        "--min-rank",
        default="3",
        choices=("3", "4", "4*"),
        help="Minimum journal rank.",
    )
    search_abs.add_argument("--year-start", type=int, default=2020, help="Start year.")
    search_abs.add_argument("--limit", type=int, default=15, help="Maximum results.")
    search_abs.add_argument(
        "--export-dir",
        help="Optional directory for Excel and RIS exports.",
    )
    add_render_args(search_abs)

    search_journal = subparsers.add_parser("search-journal", help="Search a specific journal.")
    search_journal.add_argument("--journal-name", required=True, help="Journal name.")
    search_journal.add_argument("--query", required=True, help="Search query or * for all.")
    search_journal.add_argument("--year-start", type=int, default=2020, help="Start year.")
    search_journal.add_argument("--limit", type=int, default=15, help="Maximum results.")
    search_journal.add_argument(
        "--export-dir",
        help="Optional directory for Excel and RIS exports.",
    )
    add_render_args(search_journal)

    summarize_report = subparsers.add_parser(
        "summarize-report",
        help="Summarize an exported Excel report.",
    )
    summarize_report.add_argument("--file-path", required=True, help="Excel report path.")
    add_render_args(summarize_report)

    return parser.parse_args()


def normalize_limit(limit: int) -> int:
    if limit <= 0:
        return 0
    return min(limit, 2000)


def extract_authors(work: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for authorship in work.get("authorships", []):
        name = (authorship.get("author") or {}).get("display_name")
        if name:
            names.append(name)
    return names


def abstract_from_work(work: dict[str, Any], reconstruct_abstract: Any) -> str:
    inverted = work.get("abstract_inverted_index")
    if not inverted:
        return ""
    return reconstruct_abstract(inverted).strip()


def tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9]{3,}", query.lower())
    return [token for token in tokens if token not in {"the", "and", "for", "with"}]


def matches_query(text: str, query_tokens: list[str]) -> bool:
    lowered = text.lower()
    return bool(query_tokens) and any(token in lowered for token in query_tokens)


def estimate_full_text_need(paper: dict[str, Any], query_tokens: list[str]) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []

    abstract_text = paper["abstract"]
    combined_text = f'{paper["title"]} {abstract_text}'.strip()

    if not abstract_text:
        score += 3
        reasons.append("OpenAlex does not provide an abstract for this paper.")
    else:
        abstract_word_count = paper["abstract_word_count"]
        if abstract_word_count < 80:
            score += 2
            reasons.append("The abstract is short and may omit design details.")
        elif abstract_word_count < 140:
            score += 1
            reasons.append("The abstract is concise, so contribution details may be compressed.")

    if query_tokens and not matches_query(combined_text, query_tokens):
        score += 1
        reasons.append("The match may depend on context beyond the title and abstract.")

    citations = paper["citations"]
    if citations >= 100:
        score += 2
        reasons.append("The paper is highly cited and may be a cornerstone reference.")
    elif citations >= 30:
        score += 1
        reasons.append("The paper is well cited and could deserve a deeper read.")

    year = paper["year"]
    if isinstance(year, int) and year >= date.today().year - 1:
        score += 1
        reasons.append("The paper is recent and may need a full-text check for methods and framing.")

    if score >= 4:
        priority = "high"
    elif score >= 2:
        priority = "medium"
    else:
        priority = "low"

    if not reasons:
        reasons.append("The abstract is likely enough for an initial screening pass.")

    return {
        "priority": priority,
        "reasons": reasons,
        "heuristic_only": True,
    }


def work_to_record(work: dict[str, Any], reconstruct_abstract: Any, query_tokens: list[str]) -> dict[str, Any]:
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    abstract = abstract_from_work(work, reconstruct_abstract)
    record = {
        "title": work.get("title") or "Untitled",
        "year": work.get("publication_year"),
        "journal": source.get("display_name") or "Unknown Journal",
        "authors": extract_authors(work),
        "citations": work.get("cited_by_count", 0),
        "doi": work.get("doi") or "",
        "openalex_id": work.get("id") or "",
        "landing_page_url": primary_location.get("landing_page_url") or "",
        "abstract": abstract,
        "abstract_word_count": len(abstract.split()) if abstract else 0,
    }
    record["full_text_priority"] = estimate_full_text_need(record, query_tokens)
    return record


def export_results(
    export_dir: str | None,
    works: list[dict[str, Any]],
    file_stem: str,
    generate_excel_report: Any,
    works_to_ris_block: Any,
) -> dict[str, str] | None:
    if not export_dir:
        return None

    export_root = Path(export_dir)
    export_root.mkdir(parents=True, exist_ok=True)

    excel_path = export_root / f"{file_stem}.xlsx"
    ris_path = export_root / f"{file_stem}.ris"

    generate_excel_report(works, str(excel_path))
    ris_path.write_text(works_to_ris_block(works), encoding="utf-8")

    return {
        "excel": str(excel_path),
        "ris": str(ris_path),
    }


def sanitize_file_stem(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "openalex_results"


def find_journal(abs_cache: Any, journal_name: str) -> tuple[str, str]:
    if abs_cache.df is None or abs_cache.df.empty:
        raise ValueError("ABS/AJG cache is empty.")

    matches = abs_cache.df[
        abs_cache.df["Journal Title"].str.contains(journal_name, case=False, regex=False)
    ]
    if matches.empty:
        raise ValueError(f"Journal not found in ABS/AJG list: {journal_name}")

    exact = matches[matches["Journal Title"].str.lower() == journal_name.lower()]
    row = exact.iloc[0] if not exact.empty else matches.iloc[0]
    parts = [part.strip() for part in str(row["ISSN"]).replace(";", ",").split(",") if part.strip()]
    if not parts:
        raise ValueError(f"Journal found but ISSN missing: {journal_name}")

    return parts[0], str(row["Journal Title"])


async def run_search_abs(args: argparse.Namespace, modules: dict[str, Any]) -> dict[str, Any]:
    abs_cache = modules["ABSCache"](str(modules["data_csv"]))
    client = modules["OpenAlexClient"]()

    field = args.field.strip() or None
    issns = abs_cache.get_issns(field=field, min_rank=args.min_rank)
    if not issns:
        raise ValueError("No journals matched the requested field and rank.")

    works, has_more = await client.search_works(
        args.query,
        issns,
        limit=normalize_limit(args.limit),
        sort="publication_date:desc",
    )
    filtered_works = [work for work in works if (work.get("publication_year") or 0) >= args.year_start]
    query_tokens = tokenize_query(args.query)
    papers = [
        work_to_record(work, modules["reconstruct_abstract"], query_tokens)
        for work in filtered_works
    ]

    exports = export_results(
        args.export_dir,
        filtered_works,
        sanitize_file_stem(f"abs_{field or 'all'}_{args.min_rank}_{args.query}"),
        modules["generate_excel_report"],
        modules["works_to_ris_block"],
    )

    return {
        "search_type": "abs",
        "query": args.query,
        "field": field or "",
        "min_rank": args.min_rank,
        "year_start": args.year_start,
        "limit": args.limit,
        "count": len(papers),
        "has_more": has_more,
        "papers": papers,
        "exports": exports,
    }


async def run_search_journal(args: argparse.Namespace, modules: dict[str, Any]) -> dict[str, Any]:
    abs_cache = modules["ABSCache"](str(modules["data_csv"]))
    client = modules["OpenAlexClient"]()

    journal_issn, resolved_name = find_journal(abs_cache, args.journal_name)
    works, has_more = await client.search_works(
        args.query,
        [journal_issn],
        limit=normalize_limit(args.limit),
        sort="publication_date:desc",
    )
    filtered_works = [work for work in works if (work.get("publication_year") or 0) >= args.year_start]
    query_tokens = tokenize_query(args.query)
    papers = [
        work_to_record(work, modules["reconstruct_abstract"], query_tokens)
        for work in filtered_works
    ]

    exports = export_results(
        args.export_dir,
        filtered_works,
        sanitize_file_stem(f"journal_{resolved_name}_{args.query}"),
        modules["generate_excel_report"],
        modules["works_to_ris_block"],
    )

    return {
        "search_type": "journal",
        "journal_name": args.journal_name,
        "resolved_journal_name": resolved_name,
        "query": args.query,
        "year_start": args.year_start,
        "limit": args.limit,
        "count": len(papers),
        "has_more": has_more,
        "papers": papers,
        "exports": exports,
    }


def summarize_report(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"Excel report not found: {file_path}")

    import pandas as pd

    df = pd.read_excel(file_path)
    if df.empty:
        return {
            "file_path": str(file_path),
            "count": 0,
            "years": {},
            "top_authors": [],
            "top_cited": [],
        }

    year_counts = {
        int(year): int(count)
        for year, count in df["Year"].value_counts().sort_index().items()
        if str(year).lower() != "nan"
    }

    author_counts: dict[str, int] = {}
    for authors in df["Authors"].dropna().astype(str):
        for author in [part.strip() for part in authors.split(",") if part.strip()]:
            author_counts[author] = author_counts.get(author, 0) + 1

    top_authors = [
        {"author": author, "papers": count}
        for author, count in sorted(author_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]

    top_cited = []
    for _, row in df.sort_values(by="Citations", ascending=False).head(10).iterrows():
        year_value = row.get("Year")
        top_cited.append(
            {
                "title": row.get("Title", ""),
                "year": int(year_value) if str(year_value).lower() != "nan" else None,
                "journal": row.get("Journal", ""),
                "citations": int(row.get("Citations", 0)),
                "doi": row.get("DOI", ""),
            }
        )

    return {
        "file_path": str(file_path),
        "count": int(len(df)),
        "year_start": int(df["Year"].min()),
        "year_end": int(df["Year"].max()),
        "years": year_counts,
        "top_authors": top_authors,
        "top_cited": top_cited,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    if payload.get("search_type") in {"abs", "journal"}:
        lines = [
            f"# OpenAlex AJG Search: {payload['query']}",
            "",
            "## Scope",
            f"- Search type: {payload['search_type']}",
            f"- Count: {payload['count']}",
            f"- Has more: {payload['has_more']}",
        ]
        if payload.get("field") is not None:
            lines.append(f"- Field: {payload.get('field', '') or 'ALL'}")
        if payload.get("min_rank"):
            lines.append(f"- Min rank: {payload['min_rank']}")
        if payload.get("resolved_journal_name"):
            lines.append(f"- Journal: {payload['resolved_journal_name']}")

        lines.extend(["", "## Papers"])
        for paper in payload["papers"]:
            lines.extend(
                [
                    "",
                    f"### {paper['title']}",
                    f"- Year: {paper['year']}",
                    f"- Journal: {paper['journal']}",
                    f"- Citations: {paper['citations']}",
                    f"- DOI: {paper['doi'] or 'N/A'}",
                    f"- Full-text priority: {paper['full_text_priority']['priority']}",
                    f"- Abstract: {paper['abstract'] or 'N/A'}",
                ]
            )
        return "\n".join(lines)

    lines = [
        "# Literature Report Summary",
        "",
        f"- File: {payload['file_path']}",
        f"- Count: {payload['count']}",
        f"- Year range: {payload.get('year_start')} to {payload.get('year_end')}",
        "",
        "## Year counts",
    ]
    for year, count in payload["years"].items():
        lines.append(f"- {year}: {count}")

    lines.extend(["", "## Top authors"])
    for item in payload["top_authors"]:
        lines.append(f"- {item['author']}: {item['papers']}")

    lines.extend(["", "## Top cited papers"])
    for item in payload["top_cited"]:
        lines.append(f"- {item['year']} | {item['title']} | {item['citations']}")

    return "\n".join(lines)


def emit_output(payload: dict[str, Any], output_format: str, output_path: str | None) -> None:
    rendered = (
        json.dumps(payload, indent=2, ensure_ascii=False)
        if output_format == "json"
        else render_markdown(payload)
    )

    if output_path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")


async def async_main(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root)
    modules = bootstrap_repo(repo_root)

    if args.command == "search-abs":
        return await run_search_abs(args, modules)
    if args.command == "search-journal":
        return await run_search_journal(args, modules)
    if args.command == "summarize-report":
        return summarize_report(Path(args.file_path))

    raise ValueError(f"Unsupported command: {args.command}")


def main() -> int:
    args = parse_args()
    try:
        payload = asyncio.run(async_main(args))
    except Exception as exc:
        error_payload = {"error": str(exc)}
        emit_output(error_payload, args.format, args.output_path)
        return 1

    emit_output(payload, args.format, args.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


