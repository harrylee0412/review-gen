from __future__ import annotations

import argparse
import csv
import json
import re
import sys
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
        # If screening has not happened yet, avoid returning an empty list.
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


def normalize_language(raw: str) -> str:
    value = (raw or "").strip().lower()
    mapping = {
        "en": "en",
        "english": "en",
        "英文": "en",
        "zh": "zh",
        "zh-cn": "zh",
        "chinese": "zh",
        "中文": "zh",
    }
    if value in mapping:
        return mapping[value]
    raise ValueError(f"Unsupported language input: {raw}")


def choose_language(language_arg: str | None) -> str:
    if language_arg:
        return normalize_language(language_arg)

    if not sys.stdin.isatty():
        return "en"

    while True:
        try:
            picked = input("请选择计划撰写语言（中文/英文，输入 zh/en）: ").strip()
        except EOFError:
            return "en"
        try:
            return normalize_language(picked)
        except ValueError:
            print("无法识别输入，请输入 zh 或 en。")


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
        if not line:
            continue
        if len(line) < 6 or line[2:6] != "  - ":
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


def load_cn_ris_papers(ris_dir: Path, limit: int) -> tuple[list[dict[str, Any]], int]:
    files = sorted(ris_dir.glob("*.ris"))
    papers: list[dict[str, Any]] = []
    for path in files:
        papers.extend(parse_ris_text(read_text_fallback(path)))
    selected: list[dict[str, Any]] = []
    for row in papers:
        selected.append(
            {
                "authors": row.get("authors", []),
                "year": row.get("year", ""),
                "title": row.get("title", "Untitled"),
                "journal": row.get("journal", ""),
                "doi": row.get("doi", ""),
            }
        )
        if limit > 0 and len(selected) >= limit:
            break
    return selected, len(files)


def build_plan(
    workspace: Path,
    topic: str,
    word_count: int,
    top_n: int,
    top_mode: str,
    allow_fallback: bool,
    language: str,
    cn_ris_dir: Path,
) -> tuple[str, int, int]:
    corpus_rows = read_jsonl(workspace / "02_corpus" / "master_corpus.jsonl")
    screening_rows = read_csv(workspace / "03_screening" / "screening_table.csv")
    evidence_rows = read_csv(workspace / "03_screening" / "evidence_table.csv")
    fulltext_rows = read_csv(workspace / "04_fulltext" / "fulltext_manifest.csv")

    source_level = detect_source_level(fulltext_rows, evidence_rows)
    md_ready = sum(1 for row in fulltext_rows if row.get("md_status") == "ready")
    included = sum(1 for row in screening_rows if row.get("included_title_abstract", "").strip().lower() in {"yes", "y", "true", "1"})
    if corpus_rows:
        selected, selection_meta = top_papers(corpus_rows, screening_rows, top_n, top_mode, allow_fallback)
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
    chinese_papers: list[dict[str, Any]] = []
    cn_ris_file_count = 0
    if language == "zh":
        cn_limit = top_n if top_n > 0 else to_int(selection_meta.get("selection_target", 0))
        if cn_limit <= 0:
            cn_limit = 120
        chinese_papers, cn_ris_file_count = load_cn_ris_papers(cn_ris_dir, cn_limit)
        if not chinese_papers:
            raise FileNotFoundError(
                f"中文模式需要先准备知网 RIS 文件。请按关键词在知网导出 RIS 后放入目录: {cn_ris_dir}"
            )

    lines = [
        f"# Review Plan: {topic}",
        "",
        "Plan status: DRAFT - requires user confirmation before prose drafting.",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"Requested writing language: {'Chinese (zh)' if language == 'zh' else 'English (en)'}",
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
        f"- CNKI RIS files loaded: {cn_ris_file_count if language == 'zh' else 0}",
        f"- Core-paper selection mode: {selection_meta['selection_mode']}",
        f"- Core-paper selection target: {selection_meta['selection_target']}",
        f"- Core-paper pool (included/fallback): {selection_meta['included_pool']} / {selection_meta['fallback_pool']}",
        f"- Core papers selected (included/fallback): {selection_meta['selected_from_included']} / {selection_meta['selected_from_fallback']}",
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

    if language == "zh":
        lines.extend(
            [
                "",
                "## Candidate Chinese-Language Papers (From CNKI RIS)",
            ]
        )
        for row in chinese_papers:
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
    return "\n".join(lines) + "\n", len(chinese_papers), cn_ris_file_count


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
    parser.add_argument("--top-papers", type=int, default=0, help="Paper cap. In dynamic mode, 0 means auto-size.")
    parser.add_argument(
        "--top-papers-mode",
        choices=["dynamic", "fixed", "all-included"],
        default="dynamic",
        help="Selection strategy for core papers. Default keeps high-coverage dynamic selection over screened-in papers.",
    )
    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Backfill with non-included papers when included papers are fewer than the target.",
    )
    parser.add_argument("--language", choices=["en", "zh"], help="Writing language for the review plan. If omitted and interactive, the script prompts the user.")
    parser.add_argument("--cn-ris-dir", help="Folder containing user-exported CNKI RIS files. Defaults to <workspace>/02_corpus/cnki_ris.")
    parser.add_argument("--output-path", help="Optional path to save the live plan. Defaults to 07_plan/review_plan.md inside the workspace.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace)
    language = choose_language(args.language)
    cn_ris_dir = Path(args.cn_ris_dir) if args.cn_ris_dir else workspace / "02_corpus" / "cnki_ris"
    plan, chinese_count, cn_ris_file_count = build_plan(
        workspace,
        args.topic,
        args.word_count,
        args.top_papers,
        args.top_papers_mode,
        args.allow_fallback,
        language=language,
        cn_ris_dir=cn_ris_dir,
    )
    path = Path(args.output_path) if args.output_path else workspace / "07_plan" / "review_plan.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan, encoding="utf-8")
    archive_path = archive_snapshot(workspace, plan)
    payload = {
        "plan_path": str(path),
        "archive_path": str(archive_path),
        "workspace": str(workspace),
        "language": language,
        "cn_ris_dir": str(cn_ris_dir),
        "cn_ris_files_loaded": cn_ris_file_count,
        "chinese_papers_added": chinese_count,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
