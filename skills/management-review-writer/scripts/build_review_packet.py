from __future__ import annotations

import argparse
import csv
import json
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


def choose_template(source_level: str) -> str:
    mapping = {
        "abstract-only": "Template A: Abstract-Only Review Draft",
        "mixed": "Template B: Mixed Review Draft",
        "full-text": "Template C: Full-Text Review Draft",
    }
    return mapping[source_level]


def manifest_fallback_papers(fulltext_rows: list[dict[str, str]], limit: int) -> list[dict[str, Any]]:
    ranked = sorted(
        fulltext_rows,
        key=lambda item: (str(item.get("year", "")), str(item.get("title", ""))),
    )
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


def build_guardrails(source_level: str, topic: str, word_count: int) -> str:
    lines = [
        f"# Review Guardrails: {topic}",
        "",
        "These guardrails are the canonical writing memory for the review.",
        "Reread this file together with `review_plan.md` and `review_packet.md` before every new drafting or revision pass.",
        "",
        "## Non-Negotiable Rules",
        "- Default to English academic prose unless the user explicitly asks for another language.",
        "- Write only in connected paragraphs. Do not use bullet points unless the user explicitly requests them.",
        "- Use real APA-style in-text citations by default.",
        "- Every concept definition, claim, contrast, and empirical conclusion must be tied to a real source.",
        "- Never fabricate references, page numbers, methods, findings, or boundary conditions.",
        "- Follow the approved `review_plan.md` as the canonical structure.",
        "- Do not change the top-level framework unless the author explicitly revises the plan.",
        "- Trace key construct definitions back to anchor sources and stay aligned with the approved working definitions.",
        "- Prioritize synthesis over paper-by-paper summary.",
        "- Organize the core review around theory, methods, and context whenever the topic allows.",
        "- Explicitly surface consensus, disagreement, contradiction, boundary conditions, and research gaps.",
        "- Match every claim to the available source level and do not overstate abstract-only evidence.",
        "",
        "## Current Assignment",
        f"- Topic: {topic}",
        f"- Target word count: {word_count}",
        f"- Evidence source level: {source_level}",
        "",
        "## Source-Level Rules",
    ]

    if source_level == "abstract-only":
        lines.extend(
            [
                "- Stay within title-and-abstract evidence.",
                "- Do not infer research design details, causal identification, or nuanced moderators unless explicitly stated.",
                "- Make the abstract-only limitation visible in the prose when it matters for interpretation.",
            ]
        )
    elif source_level == "mixed":
        lines.extend(
            [
                "- Combine abstract screening with retrieved full-text evidence carefully.",
                "- Distinguish abstract-based observations from full-text-supported claims when confidence differs.",
                "- Use full-text chunks to clarify definitions, mechanisms, methods, and contested findings.",
            ]
        )
    else:
        lines.extend(
            [
                "- Rely primarily on full-text Markdown and evidence-table notes.",
                "- Distinguish clearly between what authors argue, what their evidence shows, and what the synthesis concludes.",
                "- Use abstracts only as supporting metadata rather than the main evidence source.",
            ]
        )

    lines.extend(
        [
            "",
            "## Structure Rules",
            "- Open by defining the problem, scope, and organizing logic.",
            "- Early in the review, trace the core construct definitions to anchor sources and clarify conceptual boundaries.",
            "- Develop the body through synthesis rather than cataloguing individual papers.",
            "- End with a research gap or agenda that follows from the preceding synthesis.",
            "",
            "## Anti-Overflow Reminder",
            "- If the drafting task spans multiple turns, paste or reread this file first.",
            "- If context becomes tight, keep `review_plan.md`, this file, and `review_packet.md` in view and retrieve only the evidence needed for the current paragraph.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_packet(workspace: Path, topic: str, word_count: int, top_n: int) -> str:
    corpus_path = workspace / "02_corpus" / "master_corpus.jsonl"
    screening_path = workspace / "03_screening" / "screening_table.csv"
    evidence_path = workspace / "03_screening" / "evidence_table.csv"
    fulltext_path = workspace / "04_fulltext" / "fulltext_manifest.csv"
    chunk_path = workspace / "06_chunks" / "chunk_index.jsonl"
    plan_path = workspace / "07_plan" / "review_plan.md"

    corpus_rows = read_jsonl(corpus_path)
    screening_rows = read_csv(screening_path)
    evidence_rows = read_csv(evidence_path)
    fulltext_rows = read_csv(fulltext_path)
    chunk_rows = read_jsonl(chunk_path)

    source_level = detect_source_level(fulltext_rows, evidence_rows)
    md_ready = sum(1 for row in fulltext_rows if row.get("md_status") == "ready")
    included = sum(1 for row in screening_rows if row.get("included_title_abstract", "").strip().lower() in {"yes", "y", "true", "1"})
    selected = top_papers(corpus_rows, screening_rows, top_n) if corpus_rows else manifest_fallback_papers(fulltext_rows, top_n)

    if not plan_path.exists():
        plan_status = "missing"
        plan_note = "No review_plan.md found. Run management-review-planner and get user approval before formal drafting."
    else:
        text = plan_path.read_text(encoding="utf-8", errors="ignore")
        status_line = next((line.strip() for line in text.splitlines() if line.strip().lower().startswith("plan status:")), "")
        plan_status = "approved" if status_line.lower().startswith("plan status: approved") else "present-unapproved"
        plan_note = "review_plan.md found. Follow it as the canonical structure." if plan_status == "approved" else "review_plan.md exists but does not appear approved yet. Confirm the plan before drafting."

    lines = [
        f"# Review Packet: {topic}",
        "",
        "## Corpus Snapshot",
        f"- Workspace: {workspace}",
        f"- Target word count: {word_count}",
        f"- Source level: {source_level}",
        f"- Papers in master corpus: {len(corpus_rows)}",
        f"- Papers marked included at title/abstract stage: {included}",
        f"- Full-text Markdown files ready: {md_ready}",
        f"- Evidence-table rows: {len(evidence_rows)}",
        f"- Chunk rows: {len(chunk_rows)}",
        "",
        "## Plan Status",
        f"- Review plan path: {plan_path}",
        f"- Review plan status: {plan_status}",
        f"- Planner note: {plan_note}",
        "",
        "## Hard Constraints",
        "- Write in paragraphs, not bullets.",
        "- Default to English academic prose.",
        "- Use real APA-style in-text citations.",
        "- Every concept, definition, and claim must have a real source.",
        "- Synthesize rather than summarizing paper by paper.",
        "- Follow the approved `review_plan.md` as the fixed framework.",
        "- Do not change the top-level plan unless the user explicitly revises it.",
        "- Trace key construct definitions back to anchor sources and keep the draft aligned with the approved working definitions.",
        "- Organize the review around theory, methods, and context whenever possible.",
        "- Explicitly identify consensus, tensions, contradictions, and research gaps.",
        "- Do not overstate evidence beyond the available source level.",
        "- Before every new drafting pass, reread `review_plan.md` and `review_guardrails.md`.",
        "",
        "## Recommended Prompt Template",
        f"- {choose_template(source_level)}",
        "",
        "## Suggested Core Papers",
    ]

    for row in selected:
        lines.append(f"- {format_citation(row)}")

    lines.extend(
        [
            "",
            "## Drafting Instructions",
            f"Use the {source_level} evidence base to write a {word_count}-word review on {topic}.",
            "The opening paragraph should define the problem and scope.",
            "The next conceptual paragraph(s) should trace the core construct definitions to anchor sources and clarify conceptual boundaries.",
            "The middle paragraphs should synthesize theory, methods, and context within the approved framework and paragraph blueprint.",
            "The final paragraph should derive a research gap from the synthesis rather than state a generic future-research sentence.",
            "",
            "## Follow-Up Prompts",
            "1. Compress the review to a shorter target without losing theory, methods, context, or construct-definition clarity.",
            "2. Strengthen the synthesis so the draft reads like a journal literature review rather than a report, while keeping the approved plan intact.",
            "3. Expand the disagreement and boundary-condition discussion using only supported evidence.",
            "4. Strengthen the definition-lineage and conceptual-boundary section without adding unsupported claims.",
            "5. Audit every major claim for source support and flag weakly supported sentences.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a review-writing packet from a review workspace.")
    parser.add_argument("--workspace", required=True, help="Path to the review workspace.")
    parser.add_argument("--topic", required=True, help="Topic label for the review.")
    parser.add_argument("--word-count", type=int, default=1800, help="Target review length.")
    parser.add_argument("--top-papers", type=int, default=12, help="Number of focal papers to list.")
    parser.add_argument("--output-path", help="Optional path to save the packet.")
    parser.add_argument("--guardrails-path", help="Optional path to save the persistent writing guardrails.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace)
    packet = build_packet(workspace, args.topic, args.word_count, args.top_papers)
    source_level = detect_source_level(
        read_csv(workspace / "04_fulltext" / "fulltext_manifest.csv"),
        read_csv(workspace / "03_screening" / "evidence_table.csv"),
    )
    guardrails = build_guardrails(source_level, args.topic, args.word_count)
    if args.output_path:
        path = Path(args.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(packet, encoding="utf-8")
        guardrails_path = Path(args.guardrails_path) if args.guardrails_path else path.with_name("review_guardrails.md")
        guardrails_path.write_text(guardrails, encoding="utf-8")
    else:
        print(packet, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




