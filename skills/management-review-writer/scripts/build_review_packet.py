from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


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


def priority_value(raw: str) -> int:
    value = (raw or "").strip().lower()
    return {"high": 3, "medium": 2, "low": 1}.get(value, 0)


def rank_hint(search_scope: str) -> int:
    lowered = (search_scope or "").lower()
    if "4*" in lowered:
        return 3
    if re.search(r"(^|[^0-9])4([^0-9]|$)", lowered):
        return 2
    if re.search(r"(^|[^0-9])3([^0-9]|$)", lowered):
        return 1
    return 0


def dynamic_target_size(pool_size: int, explicit_limit: int) -> int:
    if pool_size <= 0:
        return 0
    if explicit_limit > 0:
        return min(pool_size, explicit_limit)
    if pool_size <= 120:
        return pool_size
    if pool_size <= 300:
        return max(40, int(round(pool_size * 0.85)))
    if pool_size <= 600:
        return max(80, int(round(pool_size * 0.70)))
    return min(pool_size, 420)


def sort_key(row: dict[str, Any], screen: dict[str, str]) -> tuple[int, int, int, int, str]:
    return (
        -rank_hint(str(row.get("search_scope", ""))),
        -priority_value(str(row.get("full_text_priority", ""))),
        -to_int(row.get("citations", 0)),
        -to_int(row.get("year", 0)),
        str(row.get("title", "")),
    )


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


def top_papers(
    corpus_rows: list[dict[str, Any]],
    screening_rows: list[dict[str, str]],
    limit: int,
    mode: str,
    allow_fallback: bool,
) -> tuple[list[dict[str, Any]], dict[str, int | str]]:
    screening_map = {row.get("paper_key", ""): row for row in screening_rows}
    preferred: list[dict[str, Any]] = []
    fallback: list[dict[str, Any]] = []
    for row in corpus_rows:
        screen = screening_map.get(row.get("paper_key", ""), {})
        if screen.get("included_title_abstract", "").strip().lower() in {"yes", "y", "true", "1"}:
            preferred.append(row)
        else:
            fallback.append(row)

    preferred_sorted = sorted(preferred, key=lambda item: sort_key(item, screening_map.get(item.get("paper_key", ""), {})))
    fallback_sorted = sorted(fallback, key=lambda item: sort_key(item, screening_map.get(item.get("paper_key", ""), {})))
    preferred_count = len(preferred_sorted)
    fallback_count = len(fallback_sorted)

    if mode == "all-included":
        target = preferred_count
    elif mode == "fixed":
        target = preferred_count if limit <= 0 else min(preferred_count, limit)
    else:
        target = dynamic_target_size(preferred_count if preferred_count > 0 else len(corpus_rows), limit)

    selected_from_preferred = preferred_sorted[:target]
    selected_from_fallback: list[dict[str, Any]] = []
    if not selected_from_preferred and fallback_sorted:
        selected_from_fallback = fallback_sorted[:target or dynamic_target_size(fallback_count, limit)]
    elif allow_fallback and len(selected_from_preferred) < target:
        gap = target - len(selected_from_preferred)
        selected_from_fallback = fallback_sorted[:gap]

    selected = selected_from_preferred + selected_from_fallback
    return selected, {
        "selection_mode": mode,
        "selection_target": target,
        "included_pool": preferred_count,
        "fallback_pool": fallback_count,
        "selected_total": len(selected),
        "selected_from_included": len(selected_from_preferred),
        "selected_from_fallback": len(selected_from_fallback),
    }


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


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_title(text: str) -> str:
    lowered = normalize_whitespace(text).lower()
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def normalize_doi(text: str) -> str:
    value = normalize_whitespace(text).lower()
    if value.startswith("https://doi.org/"):
        value = value.split("https://doi.org/", 1)[1]
    if value.startswith("http://doi.org/"):
        value = value.split("http://doi.org/", 1)[1]
    return value


def leading_author(authors: Any) -> str:
    if isinstance(authors, list):
        if not authors:
            return "unknown"
        base = authors[0]
    else:
        text = str(authors or "")
        if ";" in text:
            base = text.split(";", 1)[0]
        elif "," in text:
            base = text.split(",", 1)[0]
        else:
            base = text
    base = normalize_whitespace(base)
    if not base:
        return "unknown"
    token = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "", base.lower())
    return token or "unknown"


def citekey_from_row(row: dict[str, Any], source: str) -> str:
    year = str(row.get("year", "") or "nd")
    author = leading_author(row.get("authors", ""))
    title = normalize_title(str(row.get("title", "")))
    title_head = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title)[:24] or "untitled"
    return f"{source}:{author}{year}:{title_head}"


def read_text_fallback(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def ris_year(value: str) -> str:
    text = value.strip()
    for idx, ch in enumerate(text):
        if ch.isdigit():
            chunk = text[idx:idx + 4]
            if len(chunk) == 4 and chunk.isdigit():
                return chunk
    return ""


def parse_ris_text(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {"authors": []}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or len(line) < 6 or line[2:6] != "  - ":
            continue
        tag = line[:2]
        value = line[6:].strip()
        if tag == "TY":
            current = {"authors": []}
            continue
        if tag == "ER":
            if any(current.get(key) for key in ("title", "authors", "year", "journal", "doi")):
                records.append(current)
            current = {"authors": []}
            continue
        if tag in {"AU", "A1"}:
            current.setdefault("authors", []).append(value)
        elif tag in {"TI", "T1"} and value:
            current["title"] = value
        elif tag in {"JO", "T2", "JF", "JA"} and value and not current.get("journal"):
            current["journal"] = value
        elif tag in {"PY", "Y1"} and value and not current.get("year"):
            current["year"] = ris_year(value)
        elif tag == "DO" and value:
            current["doi"] = value
    if any(current.get(key) for key in ("title", "authors", "year", "journal", "doi")):
        records.append(current)
    return records


def load_cn_ris_papers(ris_dir: Path) -> tuple[list[dict[str, Any]], int]:
    files = sorted(ris_dir.glob("*.ris"))
    rows: list[dict[str, Any]] = []
    for path in files:
        rows.extend(parse_ris_text(read_text_fallback(path)))
    return rows, len(files)


def build_citation_allowlist(
    corpus_rows: list[dict[str, Any]],
    screening_rows: list[dict[str, str]],
    cn_ris_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    screening_map = {row.get("paper_key", ""): row for row in screening_rows}
    has_screening = bool(screening_rows)
    entries: list[dict[str, Any]] = []

    for row in corpus_rows:
        paper_key = row.get("paper_key", "")
        screen = screening_map.get(paper_key, {})
        included = screen.get("included_title_abstract", "").strip().lower() in {"yes", "y", "true", "1"}
        if has_screening and not included:
            continue
        doi = normalize_doi(str(row.get("doi", "")))
        entries.append(
            {
                "source": "openalex_corpus",
                "paper_key": paper_key,
                "title": normalize_whitespace(str(row.get("title", ""))),
                "year": str(row.get("year", "")),
                "journal": normalize_whitespace(str(row.get("journal", ""))),
                "authors": row.get("authors", []),
                "doi": doi,
                "citations": to_int(row.get("citations", 0)),
                "search_scope": row.get("search_scope", ""),
                "included_title_abstract": included,
            }
        )

    for row in cn_ris_rows:
        title = normalize_whitespace(str(row.get("title", "")))
        if not title:
            continue
        doi = normalize_doi(str(row.get("doi", "")))
        key_seed = f"cnki::{title}::{row.get('year', '')}::{doi}"
        key_hash = hashlib.sha1(key_seed.encode("utf-8")).hexdigest()[:16]
        entries.append(
            {
                "source": "cnki_ris",
                "paper_key": f"cnki::{key_hash}",
                "title": title,
                "year": str(row.get("year", "")),
                "journal": normalize_whitespace(str(row.get("journal", ""))),
                "authors": row.get("authors", []),
                "doi": doi,
                "citations": 0,
                "search_scope": "cnki_ris",
                "included_title_abstract": True,
            }
        )

    dedup: dict[str, dict[str, Any]] = {}
    for row in entries:
        doi = row.get("doi", "")
        title = normalize_title(str(row.get("title", "")))
        key = f"doi::{doi}" if doi else f"title::{title}::{row.get('year', '')}"
        current = dedup.get(key)
        if current is None or to_int(row.get("citations", 0)) > to_int(current.get("citations", 0)):
            dedup[key] = row

    final_rows = sorted(
        dedup.values(),
        key=lambda row: (
            -rank_hint(str(row.get("search_scope", ""))),
            -to_int(row.get("citations", 0)),
            -to_int(row.get("year", 0)),
            str(row.get("title", "")),
        ),
    )
    for row in final_rows:
        row["citekey"] = citekey_from_row(row, str(row.get("source", "catalog")))
        row["citation_id"] = row.get("paper_key", "")

    return final_rows, {
        "entries_before_dedup": len(entries),
        "entries_after_dedup": len(final_rows),
        "from_openalex": sum(1 for row in final_rows if row.get("source") == "openalex_corpus"),
        "from_cnki_ris": sum(1 for row in final_rows if row.get("source") == "cnki_ris"),
        "with_doi": sum(1 for row in final_rows if row.get("doi")),
    }


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
    packet, _, _, _ = build_packet_with_mode(
        workspace=workspace,
        topic=topic,
        word_count=word_count,
        top_n=top_n,
        top_mode="dynamic",
        allow_fallback=False,
    )
    return packet


def build_packet_with_mode(
    workspace: Path,
    topic: str,
    word_count: int,
    top_n: int,
    top_mode: str,
    allow_fallback: bool,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    corpus_rows = read_jsonl(workspace / "02_corpus" / "master_corpus.jsonl")
    screening_rows = read_csv(workspace / "03_screening" / "screening_table.csv")
    evidence_rows = read_csv(workspace / "03_screening" / "evidence_table.csv")
    fulltext_rows = read_csv(workspace / "04_fulltext" / "fulltext_manifest.csv")
    chunk_rows = read_jsonl(workspace / "06_chunks" / "chunk_index.jsonl")
    plan_path = workspace / "07_plan" / "review_plan.md"

    source_level = detect_source_level(fulltext_rows, evidence_rows)
    md_ready = sum(1 for row in fulltext_rows if row.get("md_status") == "ready")
    included = sum(1 for row in screening_rows if row.get("included_title_abstract", "").strip().lower() in {"yes", "y", "true", "1"})
    if corpus_rows:
        selected, selection_meta = top_papers(corpus_rows, screening_rows, top_n, mode=top_mode, allow_fallback=allow_fallback)
    else:
        fallback_limit = top_n if top_n > 0 else dynamic_target_size(len(fulltext_rows), 0)
        selected = manifest_fallback_papers(fulltext_rows, fallback_limit)
        selection_meta = {
            "selection_mode": "manifest-fallback",
            "selection_target": fallback_limit,
            "included_pool": 0,
            "fallback_pool": len(fulltext_rows),
            "selected_total": len(selected),
            "selected_from_included": 0,
            "selected_from_fallback": len(selected),
        }

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
        f"- Core-paper selection mode: {selection_meta['selection_mode']}",
        f"- Core-paper selection target: {selection_meta['selection_target']}",
        f"- Core-paper pool (included/fallback): {selection_meta['included_pool']} / {selection_meta['fallback_pool']}",
        f"- Core papers selected (included/fallback): {selection_meta['selected_from_included']} / {selection_meta['selected_from_fallback']}",
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
        "- Build and use `citation_allowlist.jsonl`; do not cite papers outside this allowlist unless manually verified and added.",
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
    return "\n".join(lines) + "\n", corpus_rows, screening_rows, fulltext_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a review-writing packet from a review workspace.")
    parser.add_argument("--workspace", required=True, help="Path to the review workspace.")
    parser.add_argument("--topic", required=True, help="Topic label for the review.")
    parser.add_argument("--word-count", type=int, default=1800, help="Target review length.")
    parser.add_argument("--top-papers", type=int, default=0, help="Paper cap. In dynamic mode, 0 means auto-size.")
    parser.add_argument(
        "--top-papers-mode",
        choices=["dynamic", "fixed", "all-included"],
        default="dynamic",
        help="Selection strategy for suggested core papers.",
    )
    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Backfill with non-included papers when included papers are fewer than the target.",
    )
    parser.add_argument("--output-path", help="Optional path to save the packet.")
    parser.add_argument("--guardrails-path", help="Optional path to save the persistent writing guardrails.")
    parser.add_argument("--citation-allowlist-path", help="Optional path to save citation allowlist JSONL.")
    parser.add_argument("--cn-ris-dir", help="Optional folder containing CNKI RIS files to include in citation allowlist.")
    parser.add_argument("--exclude-cn-ris-in-allowlist", action="store_true", help="Do not include CNKI RIS entries in citation allowlist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace)
    packet, corpus_rows, screening_rows, _ = build_packet_with_mode(
        workspace,
        args.topic,
        args.word_count,
        args.top_papers,
        top_mode=args.top_papers_mode,
        allow_fallback=args.allow_fallback,
    )
    source_level = detect_source_level(
        read_csv(workspace / "04_fulltext" / "fulltext_manifest.csv"),
        read_csv(workspace / "03_screening" / "evidence_table.csv"),
    )
    guardrails = build_guardrails(source_level, args.topic, args.word_count)
    cn_ris_rows: list[dict[str, Any]] = []
    if not args.exclude_cn_ris_in_allowlist:
        cn_ris_dir = Path(args.cn_ris_dir) if args.cn_ris_dir else workspace / "02_corpus" / "cnki_ris"
        if cn_ris_dir.exists():
            cn_ris_rows, _ = load_cn_ris_papers(cn_ris_dir)
    allowlist_rows, allowlist_meta = build_citation_allowlist(corpus_rows, screening_rows, cn_ris_rows)
    if args.output_path:
        path = Path(args.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(packet, encoding="utf-8")
        guardrails_path = Path(args.guardrails_path) if args.guardrails_path else path.with_name("review_guardrails.md")
        guardrails_path.write_text(guardrails, encoding="utf-8")
        allowlist_path = Path(args.citation_allowlist_path) if args.citation_allowlist_path else workspace / "08_outputs" / "citation_allowlist.jsonl"
        write_jsonl(allowlist_path, allowlist_rows)
        summary_path = allowlist_path.with_suffix(".summary.json")
        summary_path.write_text(json.dumps(allowlist_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(packet, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




