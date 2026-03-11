---
name: management-review-writer
description: Draft management and strategy literature reviews from an OpenAlex review workspace or a curated paper list, using paragraph-only academic prose, real APA citations, and synthesis across theory, methods, and context. Use only after an approved review plan exists.
---

# Management Review Writer

Use this skill after the planning stage, when the user wants a literature review draft in management, entrepreneurship, organization theory, innovation, or strategy.

This skill is the writing handoff for review workspaces created with:

- `openalex-ajg-insights`
- `management-review-planner`
- a curated paper list with real citations
- optional full-text Markdown converted from PDFs

## Precondition

Do not start formal drafting until an approved `review_plan.md` exists. In long-running projects, let `review-orchestrator` enforce this gate.

That plan is the frozen execution blueprint for the project. The writer should enrich its sections and paragraphs with evidence, not redesign the architecture. If the user wants the structure to change, return to `management-review-planner` first.

## Non-Negotiable Writing Rules

1. Write in paragraphs, not bullet points, unless the user explicitly asks for another format.
2. Default to English prose unless the user asks for another language.
3. Use academically credible language, not blog tone.
4. Every definition, concept, empirical claim, and contrast must be tied to a real source.
5. Default to APA-style in-text citation.
6. Never fabricate references, page numbers, methods, or findings.
7. Prefer synthesis over paper-by-paper summaries.
8. Follow the approved `review_plan.md` as the canonical structure.
9. Do not change the section logic or paragraph blueprint unless the author explicitly revises the plan.
10. Trace key construct definitions back to anchor sources and keep the draft aligned with the approved working definitions in the plan.
11. If the evidence base is abstract-only, label that limitation in the prose and avoid full-text claims.

## Anti-Overflow Rule

When the review may require multiple drafting turns, always persist the writing constraints outside the live context window.

Use `scripts/build_review_packet.py` to generate:

- `review_packet.md`
- `review_guardrails.md`

Before any new drafting or revision pass, reread all three files first:

- `review_plan.md`
- `review_packet.md`
- `review_guardrails.md`

Treat them as the canonical writing memory for the review.

## Workflow

1. Check that `review_plan.md` exists and is approved.
   - If it is missing or still unapproved, stop and hand back to `management-review-planner` through `review-orchestrator`.

2. Inspect the available evidence base.
   - If the user gives a review workspace, use `scripts/build_review_packet.py`.
   - If the user only gives a paper list, manually verify that every cited paper is real.

3. Determine the source level.
   - `abstract-only`: use only safe abstract claims.
   - `mixed`: combine abstract screening with retrieved full-text chunks.
   - `full-text`: rely primarily on evidence extracted from Markdown or evidence tables.

4. Draft inside the frozen framework.
   - Keep the section architecture from `review_plan.md`.
   - Keep the paragraph blueprint from `review_plan.md`.
   - Use evidence to deepen each planned paragraph rather than redesigning the draft.

## Platform-Agnostic Quick Start

Use these placeholders on any operating system:

- `<workflow-python>`: the Python interpreter that can run the review scripts
- `<review-gen-home>`: the folder containing the `review-gen` package or its installed skills
- `<review-workspace>`: the target review workspace

```text
python <review-gen-home>/skills/management-review-writer/scripts/build_review_packet.py \
  --workspace <review-workspace> \
  --topic "Entrepreneurial bricolage and innovation" \
  --word-count 1800 \
  --output-path <review-workspace>/08_outputs/review_packet.md
```

Then reread the plan, packet, and guardrails before drafting the review in prose.

## References

Read only what is needed:

- `references/review-writing-standards.md`
- `references/review-prompt-templates.md`
