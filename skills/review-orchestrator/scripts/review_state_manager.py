from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


APPROVED_PREFIX = "Plan status: APPROVED"
DRAFT_PREFIX = "Plan status: DRAFT"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
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


def plan_path(workspace: Path) -> Path:
    return workspace / "07_plan" / "review_plan.md"


def history_dir(workspace: Path) -> Path:
    return workspace / "07_plan" / "history"


def packet_path(workspace: Path) -> Path:
    return workspace / "08_outputs" / "review_packet.md"


def guardrails_path(workspace: Path) -> Path:
    return workspace / "08_outputs" / "review_guardrails.md"


def get_plan_status(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith("plan status:"):
            if lowered.startswith("plan status: approved"):
                return "approved"
            if lowered.startswith("plan status: draft"):
                return "draft"
            return "other"
    return "missing-status"


def compute_status(workspace: Path) -> dict:
    corpus_rows = read_jsonl(workspace / "02_corpus" / "master_corpus.jsonl")
    fulltext_rows = read_csv(workspace / "04_fulltext" / "fulltext_manifest.csv")
    ready_md = sum(1 for row in fulltext_rows if row.get("md_status") == "ready")
    plan_file = plan_path(workspace)
    packet_file = packet_path(workspace)
    guardrails_file = guardrails_path(workspace)

    plan_exists = plan_file.exists()
    if plan_exists:
        plan_text = plan_file.read_text(encoding="utf-8", errors="ignore")
        current_plan_status = get_plan_status(plan_text)
    else:
        current_plan_status = "missing"

    if not corpus_rows:
        next_skill = "openalex-ajg-insights"
        next_action = "Build or refresh the literature corpus before planning."
        phase = "search"
    elif current_plan_status != "approved":
        next_skill = "management-review-planner"
        next_action = "Refine the review framework, confirm construct definitions, relationship logic, section blueprint, and paragraph blueprint, then wait for user approval."
        phase = "planning"
    else:
        next_skill = "management-review-writer"
        next_action = "Generate or refresh the writing packet and draft inside the approved framework and paragraph blueprint."
        phase = "writing"

    return {
        "workspace": str(workspace),
        "phase": phase,
        "master_corpus_count": len(corpus_rows),
        "fulltext_markdown_ready": ready_md,
        "review_plan_exists": plan_exists,
        "review_plan_status": current_plan_status,
        "review_plan_path": str(plan_file),
        "review_packet_exists": packet_file.exists(),
        "review_guardrails_exists": guardrails_file.exists(),
        "next_skill": next_skill,
        "next_action": next_action,
    }


def replace_status_line(lines: list[str], new_line: str) -> list[str]:
    replaced = False
    output: list[str] = []
    for line in lines:
        if line.strip().lower().startswith("plan status:") and not replaced:
            output.append(new_line)
            replaced = True
        else:
            output.append(line)
    if not replaced:
        if output and output[0].startswith("# Review Plan:"):
            output.insert(2, new_line)
        else:
            output.insert(0, new_line)
    return output


def remove_section(lines: list[str], heading: str) -> list[str]:
    output: list[str] = []
    skip = False
    for line in lines:
        if line.strip() == heading:
            skip = True
            continue
        if skip and line.startswith("## "):
            skip = False
        if not skip:
            output.append(line)
    return output


def append_approval_metadata(lines: list[str], actor: str, note: str, now: str) -> list[str]:
    lines = remove_section(lines, "## Approval Metadata")
    metadata = [
        "## Approval Metadata",
        f"- Recorded at: {now}",
        f"- Recorded by: {actor}",
        f"- Note: {note}",
        "",
    ]
    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.extend(metadata)
    return lines


def archive_snapshot(workspace: Path, plan_text: str, label: str) -> Path:
    target_dir = history_dir(workspace)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = target_dir / f"review_plan__{stamp}__{label}.md"
    archive_path.write_text(plan_text, encoding="utf-8")
    return archive_path


def approve_plan(workspace: Path, approved_by: str, note: str) -> dict:
    path = plan_path(workspace)
    if not path.exists():
        raise FileNotFoundError(f"review_plan.md not found at {path}")
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    now = datetime.now().isoformat(timespec="seconds")
    lines = replace_status_line(lines, f"{APPROVED_PREFIX} - framework frozen unless author revises it.")
    lines = remove_section(lines, "## Approval Note")
    lines = append_approval_metadata(lines, approved_by, note, now)
    plan_text = "\n".join(lines) + "\n"
    path.write_text(plan_text, encoding="utf-8")
    archive_path = archive_snapshot(workspace, plan_text, "approved")
    payload = compute_status(workspace)
    payload.update({
        "updated": "approved",
        "approved_by": approved_by,
        "approval_note": note,
        "approved_at": now,
        "archive_path": str(archive_path),
    })
    return payload


def reopen_plan(workspace: Path, reopened_by: str, note: str) -> dict:
    path = plan_path(workspace)
    if not path.exists():
        raise FileNotFoundError(f"review_plan.md not found at {path}")
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    now = datetime.now().isoformat(timespec="seconds")
    lines = replace_status_line(lines, f"{DRAFT_PREFIX} - reopened for revision before prose drafting.")
    lines = remove_section(lines, "## Approval Note")
    lines = append_approval_metadata(lines, reopened_by, f"REOPENED: {note}", now)
    plan_text = "\n".join(lines) + "\n"
    path.write_text(plan_text, encoding="utf-8")
    archive_path = archive_snapshot(workspace, plan_text, "reopened")
    payload = compute_status(workspace)
    payload.update({
        "updated": "reopened",
        "reopened_by": reopened_by,
        "reopen_note": note,
        "reopened_at": now,
        "archive_path": str(archive_path),
    })
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage orchestration state for literature review workspaces.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_cmd = subparsers.add_parser("status", help="Inspect the current review workflow state.")
    status_cmd.add_argument("--workspace", required=True, help="Path to the review workspace.")

    approve_cmd = subparsers.add_parser("approve-plan", help="Approve the review plan after the user confirms it in chat.")
    approve_cmd.add_argument("--workspace", required=True, help="Path to the review workspace.")
    approve_cmd.add_argument("--approved-by", default="user-confirmed-in-chat")
    approve_cmd.add_argument("--note", default="User explicitly approved the framework in conversation.")

    reopen_cmd = subparsers.add_parser("reopen-plan", help="Reopen the review plan for revision.")
    reopen_cmd.add_argument("--workspace", required=True, help="Path to the review workspace.")
    reopen_cmd.add_argument("--reopened-by", default="user-requested-revision")
    reopen_cmd.add_argument("--note", default="User requested framework revision.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace)
    if args.command == "status":
        payload = compute_status(workspace)
    elif args.command == "approve-plan":
        payload = approve_plan(workspace, args.approved_by, args.note)
    elif args.command == "reopen-plan":
        payload = reopen_plan(workspace, args.reopened_by, args.note)
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
