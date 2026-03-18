from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", re.IGNORECASE)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_doi(text: str) -> str:
    value = normalize_whitespace(text).lower()
    if value.startswith("https://doi.org/"):
        value = value.split("https://doi.org/", 1)[1]
    if value.startswith("http://doi.org/"):
        value = value.split("http://doi.org/", 1)[1]
    return value.strip(" .;,)")


def leading_author_token(authors: Any) -> str:
    if isinstance(authors, list):
        raw = str(authors[0]) if authors else ""
    else:
        text = str(authors or "")
        if ";" in text:
            raw = text.split(";", 1)[0]
        elif "," in text:
            raw = text.split(",", 1)[0]
        else:
            raw = text
    token = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "", raw.lower())
    return token


def extract_dois(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for match in DOI_PATTERN.findall(text):
        doi = normalize_doi(match)
        if doi:
            seen[doi] = None
    return list(seen.keys())


def extract_author_year_pairs(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for segment in re.findall(r"\(([^()]*)\)", text):
        for part in segment.split(";"):
            matched = re.search(r"([A-Za-z\u4e00-\u9fff][^,]{0,60}?),\s*(\d{4}[a-z]?)", part.strip(), re.IGNORECASE)
            if not matched:
                continue
            author_raw = matched.group(1)
            year_raw = matched.group(2)
            author = re.sub(r"\bet al\.?\b", "", author_raw, flags=re.IGNORECASE)
            author = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "", author.lower())
            if author:
                pairs.append((author, year_raw.lower()))
    return pairs


@dataclass
class DoiCheck:
    doi: str
    in_allowlist: bool
    crossref_ok: bool
    openalex_ok: bool


def check_doi_online(doi: str, timeout: int) -> tuple[bool, bool]:
    headers = {"User-Agent": "review-gen-citation-validator/1.0"}
    crossref_ok = False
    openalex_ok = False
    try:
        url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
        resp = requests.get(url, timeout=timeout, headers=headers)
        crossref_ok = resp.status_code == 200
    except Exception:
        crossref_ok = False
    try:
        url = f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='')}"
        resp = requests.get(url, timeout=timeout, headers=headers)
        openalex_ok = resp.status_code == 200
    except Exception:
        openalex_ok = False
    return crossref_ok, openalex_ok


def build_report(
    draft_path: Path,
    allowlist_path: Path,
    doi_checks: list[DoiCheck],
    missing_author_year: list[tuple[str, str]],
    strict_author_year: bool,
) -> tuple[str, bool]:
    fabricated = [row for row in doi_checks if not row.in_allowlist]
    unresolved = [row for row in doi_checks if row.in_allowlist and not (row.crossref_ok or row.openalex_ok)]

    has_errors = bool(fabricated or unresolved or (strict_author_year and missing_author_year))
    lines = [
        "# Citation Audit Report",
        "",
        f"- Draft path: {draft_path}",
        f"- Allowlist path: {allowlist_path}",
        f"- DOI checks: {len(doi_checks)}",
        f"- DOIs outside allowlist: {len(fabricated)}",
        f"- Allowlist DOIs unresolved online: {len(unresolved)}",
        f"- Unmatched in-text author-year citations: {len(missing_author_year)}",
        f"- Strict author-year mode: {strict_author_year}",
        f"- Audit status: {'FAIL' if has_errors else 'PASS'}",
        "",
        "## Findings",
    ]

    if not fabricated and not unresolved and not missing_author_year:
        lines.append("- No issues found.")
        return "\n".join(lines) + "\n", has_errors

    if fabricated:
        lines.append("- DOI appears in draft but not in citation allowlist:")
        for row in fabricated[:80]:
            lines.append(f"  - {row.doi}")
    if unresolved:
        lines.append("- DOI exists in allowlist but was not resolvable via Crossref/OpenAlex:")
        for row in unresolved[:80]:
            lines.append(f"  - {row.doi}")
    if missing_author_year:
        lines.append("- In-text author-year citation could not be mapped to allowlist:")
        for author, year in missing_author_year[:120]:
            lines.append(f"  - {author}, {year}")
    return "\n".join(lines) + "\n", has_errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate review draft citations against allowlist and DOI resolvers.")
    parser.add_argument("--workspace", help="Review workspace path. Used for default allowlist location.")
    parser.add_argument("--draft-path", required=True, help="Draft markdown/text path to validate.")
    parser.add_argument("--allowlist-path", help="Path to citation_allowlist.jsonl.")
    parser.add_argument("--report-path", help="Path to write citation audit report markdown.")
    parser.add_argument("--online-timeout-seconds", type=int, default=12, help="Timeout for DOI resolver checks.")
    parser.add_argument("--skip-online-doi-check", action="store_true", help="Disable Crossref/OpenAlex DOI availability checks.")
    parser.add_argument("--strict-author-year", action="store_true", help="Fail audit when any in-text author-year citation is unmatched.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    draft_path = Path(args.draft_path)
    if not draft_path.exists():
        raise SystemExit(f"Draft file not found: {draft_path}")

    if args.allowlist_path:
        allowlist_path = Path(args.allowlist_path)
    elif args.workspace:
        allowlist_path = Path(args.workspace) / "08_outputs" / "citation_allowlist.jsonl"
    else:
        raise SystemExit("Provide either --allowlist-path or --workspace.")

    allowlist = read_jsonl(allowlist_path)
    if not allowlist:
        raise SystemExit(f"Citation allowlist is empty or missing: {allowlist_path}")

    allowlist_dois = {normalize_doi(str(row.get("doi", ""))) for row in allowlist if normalize_doi(str(row.get("doi", "")))}
    author_year_index = {(leading_author_token(row.get("authors", "")), str(row.get("year", "")).lower()) for row in allowlist}

    text = draft_path.read_text(encoding="utf-8", errors="ignore")
    draft_dois = extract_dois(text)
    draft_author_year = extract_author_year_pairs(text)

    doi_checks: list[DoiCheck] = []
    for doi in draft_dois:
        in_allowlist = doi in allowlist_dois
        crossref_ok = False
        openalex_ok = False
        if in_allowlist and not args.skip_online_doi_check:
            crossref_ok, openalex_ok = check_doi_online(doi, timeout=args.online_timeout_seconds)
        elif in_allowlist and args.skip_online_doi_check:
            crossref_ok = True
        doi_checks.append(
            DoiCheck(
                doi=doi,
                in_allowlist=in_allowlist,
                crossref_ok=crossref_ok,
                openalex_ok=openalex_ok,
            )
        )

    unmatched_author_year: list[tuple[str, str]] = []
    for author, year in draft_author_year:
        if (author, year) not in author_year_index:
            unmatched_author_year.append((author, year))

    report_text, has_errors = build_report(
        draft_path=draft_path,
        allowlist_path=allowlist_path,
        doi_checks=doi_checks,
        missing_author_year=unmatched_author_year,
        strict_author_year=args.strict_author_year,
    )
    report_path = Path(args.report_path) if args.report_path else draft_path.with_name("citation_audit_report.md")
    report_path.write_text(report_text, encoding="utf-8")
    sys.stdout.write(json.dumps({"report_path": str(report_path), "status": "fail" if has_errors else "pass"}, ensure_ascii=False, indent=2) + "\n")
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
