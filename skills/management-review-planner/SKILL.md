---
name: management-review-planner
description: Plan management and strategy literature reviews before drafting, build and freeze a reusable review framework inside the workspace, trace key construct definitions back to anchor sources, and refine the section and paragraph blueprint with the user before handing off to the writing skill.
---

# Management Review Planner

Use this skill before drafting any formal literature review in management, entrepreneurship, innovation, organization theory, or strategy.

This skill sits between corpus-building and prose drafting.

Use it after:

- `openalex-ajg-insights`
- a curated paper list with real citations
- optional full-text Markdown converted from PDFs

Use it before:

- `management-review-writer`
- `review-orchestrator` when the project needs routing and approval handling

## Core Goal

Create a persistent review framework that becomes the canonical outline for the project.

The framework must be stored in the workspace as `07_plan/review_plan.md`, and every planning revision must create a timestamped archive snapshot under `07_plan/history/`.

After the plan is approved:

- later literature additions should be integrated into the existing framework
- later revisions should stay inside the existing framework unless the user explicitly changes it
- the section logic and paragraph blueprint should remain stable during drafting

## Non-Negotiable Planning Rules

1. Start with topic decomposition and construct-definition tracing, not section drafting alone.
2. Let the user topic determine which constructs, concepts, mechanisms, or relationships need review.
3. Identify anchor sources for each construct or mechanism that matters to the review.
4. Propose the section architecture and the paragraph blueprint, but do not freeze them until the user confirms them.
5. Persist the framework in `review_plan.md` before any full prose drafting begins.
6. Archive every planning revision with a timestamp.
7. Do not let the writing skill rewrite the section logic or paragraph blueprint unless the user explicitly changes the plan.

## Workflow

1. Inspect the evidence base.
   - If the user gives a review workspace, use `scripts/build_review_plan.py`.
   - If the user only gives a paper list, manually verify that the listed papers are real.

2. Generate the first planning scaffold.
   - Create `07_plan/review_plan.md`.
   - Also create a timestamped snapshot in `07_plan/history/`.
   - Include topic decomposition, definition decisions, section blueprint, paragraph blueprint, and open decisions.

3. Interact with the user before freezing the plan.
   - Ask for confirmation on constructs, relationships, conceptual boundaries, section logic, and paragraph logic.
   - Revise the plan until the user is satisfied.

4. Wait for explicit user approval.
   - Ask whether the framework should be frozen.
   - After the user says yes, let `review-orchestrator` run the approval command so the user does not edit the file manually.

5. Freeze the framework.
   - Treat it as the canonical execution blueprint for later drafting.

6. Hand off to `management-review-writer`.
   - The writer must follow the approved section and paragraph blueprint and only enrich its content with evidence.

## What The Plan Must Contain

Every approved `review_plan.md` should contain:

- the review topic and target output
- corpus snapshot and evidence level
- topic decomposition into constructs, concepts, mechanisms, and relationships
- anchor definition sources and boundary decisions
- the high-level section architecture
- the paragraph-level blueprint under each main section
- the main tensions, contradictions, and boundary conditions to watch
- user decisions already fixed versus still open

## Platform-Agnostic Quick Start

Use these placeholders on any operating system:

- `<workflow-python>`: the Python interpreter that can run the review scripts
- `<review-gen-home>`: the folder containing the `review-gen` package or its installed skills
- `<review-workspace>`: the target review workspace

```text
python <review-gen-home>/skills/management-review-planner/scripts/build_review_plan.py \
  --workspace <review-workspace> \
  --topic "Entrepreneurial bricolage and innovation" \
  --word-count 1800 \
  --language en \
  --top-papers-mode dynamic
```

如果不传 `--language`，脚本会在交互模式下先询问用户选择 `zh` 或 `en`。  
选择 `zh` 时，脚本要求先把用户在知网按关键词导出的 `.ris` 文件放到 `<review-workspace>/02_corpus/cnki_ris/`（或通过 `--cn-ris-dir` 指定目录），再把这些 RIS 条目写入计划中的中文文献小节。

`--top-papers-mode dynamic` 会优先覆盖 title/abstract 阶段已纳入（included）的高质量文献，不会为了凑固定数量而默认回填未纳入文献。只有显式传 `--allow-fallback` 才会回填。

After generating the scaffold, refine it with the user. When the user explicitly approves the framework, let `review-orchestrator` update the plan status.

## Handoff Rule

Do not start formal review drafting until the user has approved the plan.

If `review_plan.md` is missing or still clearly unapproved, stop the writing handoff and return to planning.

## References

Read only what is needed:

- `references/planning-prompt-templates.md`
- `references/planning-standards.md`
