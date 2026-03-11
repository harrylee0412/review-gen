from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def detect_source_level(fulltext_rows: list[dict[str, str]], evidence_rows: list[dict[str, str]]) -> str:
    md_ready = sum(1 for row in fulltext_rows if row.get("md_status") == "ready")
    fulltext_evidence = sum(1 for row in evidence_rows if row.get("source_level", "").strip().lower() == "full-text")
    if md_ready == 0 and fulltext_evidence == 0:
        return "abstract-only"
    if md_ready > 0 and fulltext_evidence > 0:
        return "full-text"
    return "mixed"


def manifest_fallback_papers(fulltext_rows: list[dict[str, str]], limit: int) -> list[dict[str, Any]]:
    ranked = sorted(fulltext_rows, key=lambda item: (-int(item.get("citations", 0) or 0), str(item.get("year", "")), str(item.get("title", ""))))
    rows: list[dict[str, Any]] = []
    for row in ranked[:limit]:
        rows.append(
            {
                "authors": "",
                "year": row.get("year", ""),
                "title": row.get("title", "Untitled"),
                "journal": row.get("journal", ""),
                "doi": row.get("doi", ""),
            }
        )
    return rows


def top_papers(corpus_rows: list[dict[str, Any]], screening_rows: list[dict[str, str]], limit: int) -> list[dict[str, Any]]:
    screening_map = {row.get("paper_key", ""): row for row in screening_rows}
    preferred: list[dict[str, Any]] = []
    fallback: list[dict[str, Any]] = []
    for row in corpus_rows:
        screen = screening_map.get(row.get("paper_key", ""), {})
        if screen.get("included_title_abstract", "").strip().lower() in {"yes", "y", "true", "1"}:
            preferred.append(row)
        else:
            fallback.append(row)

    def key_func(item: dict[str, Any]) -> tuple[int, str, str]:
        citations = int(item.get("citations", 0) or 0)
        year = str(item.get("year", ""))
        title = str(item.get("title", ""))
        return (-citations, year, title)

    ranked = sorted(preferred, key=key_func) + sorted(fallback, key=key_func)
    return ranked[:limit]


def format_citation(row: dict[str, Any]) -> str:
    authors = row.get("authors", "")
    if isinstance(authors, list):
        author_text = "; ".join(authors)
    else:
        author_text = str(authors)
    bits = [author_text or "Unknown authors", f"({row.get('year', 'n.d.')})", row.get("title", "Untitled"), row.get("journal", "")]
    doi = row.get("doi", "")
    text = ". ".join(bit for bit in bits if bit).strip()
    return f"{text}. DOI: {doi}" if doi else text


def build_plan(workspace: Path, topic: str, word_count: int, top_n: int) -> str:
    corpus_rows = read_jsonl(workspace / "02_corpus" / "master_corpus.jsonl")
    screening_rows = read_csv(workspace / "03_screening" / "screening_table.csv")
    evidence_rows = read_csv(workspace / "03_screening" / "evidence_table.csv")
    fulltext_rows = read_csv(workspace / "04_fulltext" / "fulltext_manifest.csv")

    source_level = detect_source_level(fulltext_rows, evidence_rows)
    md_ready = sum(1 for row in fulltext_rows if row.get("md_status") == "ready")
    included = sum(1 for row in screening_rows if row.get("included_title_abstract", "").strip().lower() in {"yes", "y", "true", "1"})
    selected = top_papers(corpus_rows, screening_rows, top_n) if corpus_rows else manifest_fallback_papers(fulltext_rows, top_n)

    lines = [
        f"# Review Plan: {topic}",
        "",
        "Plan status: DRAFT - requires user confirmation before prose drafting.",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Frozen-Frame Rule",
        "This file is the canonical review framework for the project.",
        "Later literature additions and later writing revisions should be integrated into this structure.",
        "Do not change the section logic or paragraph blueprint unless the author explicitly revises the plan.",
        "",
        "## Corpus Snapshot",
        f"- Workspace: {workspace}",
        f"- Target review length: {word_count}",
        f"- Evidence source level: {source_level}",
        f"- Papers in master corpus: {len(corpus_rows)}",
        f"- Papers marked included at title/abstract stage: {included}",
        f"- Full-text Markdown files ready: {md_ready}",
        "",
        "## Topic Decomposition",
        f"- Topic as provided by the user: {topic}",
        "- Core constructs, concepts, or mechanisms under review: [identify and refine with user]",
        "- Relationship or causal logic implied by the topic: [to confirm]",
        "- If the topic includes more than one concept, specify which concepts need independent review before discussing their relationship: [to confirm]",
        "- If the topic implies mediation, moderation, or another mechanism structure, spell out that logic in plain language here: [to confirm]",
        "- What the final review must explain: [to confirm]",
        "",
        "## Definition And Boundary Decisions",
        "- Construct or concept A: label, anchor definition source(s), definitional nuances, exclusion boundary [to confirm]",
        "- Construct or concept B: label, anchor definition source(s), definitional nuances, exclusion boundary [to confirm if relevant]",
        "- Additional constructs, mediators, moderators, or mechanisms: anchor definitions and boundaries [to confirm if relevant]",
        "- Relationship language that must be defined carefully: [to confirm]",
        "- User-approved working definitions for all constructs used in the review: [must be frozen before drafting]",
        "",
        "## Architecture Decisions To Confirm With The User",
        "- Which sections must exist in the final review: [to confirm]",
        "- Which section should carry the most weight: conceptual foundations / methods / context / contradictions / mechanism logic [to confirm]",
        "- Which literature should be background only versus central to the synthesis: [to confirm]",
        "- Which parts should stay brief and which require deep synthesis: [to confirm]",
        "",
        "## Section Blueprint",
        "### Section 1. Opening Problem And Scope",
        "- Purpose: establish the research problem, scope, and the organizing logic of the review.",
        "- Paragraph 1: motivate the phenomenon and explain why this topic matters.",
        "- Paragraph 2: define the review scope, corpus basis, and what the review will and will not cover.",
        "",
        "### Section 2. Construct Definitions And Conceptual Boundaries",
        "- Purpose: define each construct that matters for the review before moving to claims about relationships.",
        "- Paragraph 1: trace the anchor definition and lineage of construct A.",
        "- Paragraph 2: trace the anchor definition and lineage of construct B or the second major construct, if relevant.",
        "- Paragraph 3: define any mechanism terms, mediator terms, moderator terms, or relationship language that the review relies on.",
        "- Paragraph 4: clarify boundaries, overlaps, and what is explicitly excluded.",
        "",
        "### Section 3. Relationship Or Mechanism Logic",
        "- Purpose: explain how the review understands the main relationship, mechanism, or causal path in the topic.",
        "- Paragraph 1: summarize the baseline relationship or proposition under review.",
        "- Paragraph 2: explain the main theoretical logic supporting that relationship.",
        "- Paragraph 3: identify important competing explanations, conditional logic, or unresolved tensions.",
        "",
        "### Section 4. Methods And Research Designs",
        "- Purpose: show how methods, measures, samples, and research designs shape what the literature can claim.",
        "- Paragraph 1: summarize the main empirical designs and samples used in the literature.",
        "- Paragraph 2: explain how method choices strengthen or limit interpretation.",
        "",
        "### Section 5. Contexts, Settings, And Boundary Conditions",
        "- Purpose: identify where the literature travels well and where it appears context-bound.",
        "- Paragraph 1: synthesize important settings, stages, industries, or country contexts.",
        "- Paragraph 2: connect contextual variation to differences in claims or findings.",
        "",
        "### Section 6. Contradictions, Gaps, And Research Agenda",
        "- Purpose: derive the most important unresolved tension or gap from the earlier synthesis.",
        "- Paragraph 1: surface the strongest contradiction, blind spot, or unresolved issue.",
        "- Paragraph 2: translate that synthesis into a concrete research gap or agenda.",
        "",
        "## Paragraph-Level Editing Notes",
        "- For every paragraph above, specify the exact claim the paragraph must make before drafting.",
        "- For every paragraph above, specify which papers or evidence should anchor the paragraph.",
        "- Delete or merge paragraph slots only after discussing the change with the user.",
        "",
        "## Candidate Core Papers",
    ]

    for row in selected:
        lines.append(f"- {format_citation(row)}")

    lines.extend(
        [
            "",
            "## User Decisions Required Before Writing",
            "- Confirm the construct list and which constructs need standalone definition paragraphs.",
            "- Confirm how the review should describe the relationship or mechanism among those constructs.",
            "- Confirm the section blueprint and the intended function of each section.",
            "- Confirm the paragraph blueprint and which paragraphs can be merged, expanded, or removed.",
            "- Confirm whether the current architecture should be frozen as the execution blueprint.",
            "",
            "## Iteration Rule",
            "Each planning revision should produce a timestamped archive snapshot under `07_plan/history/` before or while updating the live `review_plan.md`.",
            "",
            "## Approval Note",
            "Replace this line after approval: Plan status: APPROVED - framework frozen unless author revises it.",
        ]
    )
    return "\n".join(lines) + "\n"


def archive_snapshot(workspace: Path, plan_text: str) -> Path:
    history_dir = workspace / "07_plan" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = history_dir / f"review_plan__{timestamp}.md"
    archive_path.write_text(plan_text, encoding="utf-8")
    return archive_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a persistent review plan scaffold from a review workspace.")
    parser.add_argument("--workspace", required=True, help="Path to the review workspace.")
    parser.add_argument("--topic", required=True, help="Topic label for the review.")
    parser.add_argument("--word-count", type=int, default=1800, help="Target review length.")
    parser.add_argument("--top-papers", type=int, default=12, help="Number of focal papers to list.")
    parser.add_argument("--output-path", help="Optional path to save the live plan. Defaults to 07_plan/review_plan.md inside the workspace.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace)
    plan = build_plan(workspace, args.topic, args.word_count, args.top_papers)
    path = Path(args.output_path) if args.output_path else workspace / "07_plan" / "review_plan.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan, encoding="utf-8")
    archive_path = archive_snapshot(workspace, plan)
    payload = {
        "plan_path": str(path),
        "archive_path": str(archive_path),
        "workspace": str(workspace),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
