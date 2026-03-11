# Review Prompt Templates

Use these templates after the planning stage.

The templates are adapted to the local review workspace created by `openalex-ajg-insights` and frozen by `management-review-planner`.

## Universal Rule Before Drafting

Before every drafting pass, reread:

- `review_plan.md`
- `review_packet.md`
- `review_guardrails.md`

Treat `review_plan.md` as the canonical structure and paragraph blueprint. Do not change its architecture unless the user explicitly revises the plan.

## Template A: Abstract-Only Review Draft

```text
You are writing a management or strategy literature review. Based on the approved review plan, paper list, and abstract-level evidence I provide, write an English literature review on 【TOPIC】 in approximately 【WORD_COUNT】 words.

Follow these rules strictly.

Write only in connected academic paragraphs. Do not use bullet points. Do not turn the review into a paper-by-paper summary. Use APA-style in-text citations by default. Every definition, concept, author claim, and empirical conclusion must be supported by a real source. Do not invent references, findings, methods, page numbers, or DOIs. Follow the approved `review_plan.md` as the fixed framework and paragraph blueprint. In the construct-definition sections, trace key constructs back to anchor sources and stay aligned with the approved working definitions and conceptual boundaries. Because the current evidence base is primarily abstract-level, stay within the limits of abstract-only evidence and do not infer design details, identification strategies, or boundary conditions that are not explicitly visible. Emphasize synthesis rather than cataloguing.
```

## Template B: Mixed Review Draft

```text
You are writing a management or strategy literature review. Based on the approved review plan, paper list, abstract-level evidence, full-text Markdown excerpts, and evidence-table notes I provide, write an English literature review on 【TOPIC】 in approximately 【WORD_COUNT】 words.

Write in formal academic paragraphs only. Do not use bullet points. Use APA-style in-text citations by default, and ensure that every construct definition, theoretical claim, empirical finding, and methodological judgment is tied to a real source. Do not fabricate any citation or overstate what the evidence supports. Follow the approved `review_plan.md` as the canonical framework and paragraph blueprint. Do not rewrite the architecture unless the user explicitly changes the plan. In the early conceptual sections, trace key constructs back to anchor sources, distinguish overlapping constructs, and keep the prose aligned with the approved definition and boundary decisions.
```

## Template C: Full-Text Review Draft

```text
You are writing a management or strategy literature review. Based on the approved review plan, full-text Markdown evidence, paper list, and any necessary abstract-level information I provide, write an English literature review on 【TOPIC】 in approximately 【WORD_COUNT】 words.

Write the full review in polished academic paragraphs without bullet points. Use APA-style in-text citations by default. Center the review on synthesis rather than sequential summaries of papers. Follow the approved `review_plan.md` as the canonical section and paragraph architecture for the draft. Keep the definition and conceptual-boundary sections tightly anchored to source-traced definitions and the approved working definitions. Distinguish clearly between what authors argue, what their evidence shows, and what your synthesis concludes.
```

## Anti-Overflow Reminder Prompt

```text
Before drafting, reread `review_plan.md`, `review_guardrails.md`, and `review_packet.md`. Treat them as the canonical memory for the review. Do not proceed until you have aligned the current draft with those files.
```

## Follow-Up Prompts

1. `Keep the citations and the approved architecture, but compress this review to 【WORD_COUNT】 words while preserving the planned logic.`
2. `Keep the current citations and the approved plan, but rewrite the review so that it reads more like a journal literature review section and less like a report.`
3. `Strengthen the construct-definition and boundary discussion without adding unsupported claims.`
4. `Strengthen the discussion of contradictions and boundary conditions without changing the approved framework.`
5. `Audit every major claim for source support and flag sentences whose evidence base is weak or ambiguous.`
