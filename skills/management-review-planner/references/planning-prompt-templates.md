# Planning Prompt Templates

Use these templates when creating or revising the review framework before drafting.

## Template A: First Planning Pass

```text
You are planning a management or strategy literature review, not drafting it yet. Based on the corpus snapshot and paper list I provide, create a review framework for 【TOPIC】.

Do not write the literature review itself. First produce a planning document that will become the persistent framework for later drafting. Decompose the topic into the constructs, concepts, mechanisms, and relationships that matter for the review. Then build a stable review architecture that the writer will later execute.

The plan must do five things. First, clarify which constructs or concepts need separate definition tracing. Second, explain what relationship, mechanism, or question links those constructs. Third, propose a section-by-section architecture for the review. Fourth, specify a paragraph-level blueprint under each main section, so later drafting can focus on execution rather than redesign. Fifth, list the decisions that still need confirmation from the user.

Do not assume only one focal concept. Infer the necessary conceptual pieces from the topic and the literature, then present them for confirmation. If the topic implies a main effect, mediation logic, moderation logic, or another relationship structure, make that explicit in plain language, but do not lock it in until the user confirms it.
```

## Template B: Plan Refinement With User Feedback

```text
Revise the existing `review_plan.md` using the user feedback I provide. Keep the approved architecture unless the user explicitly asks to change it. Update the topic decomposition, definition-and-boundary decisions, section blueprint, and paragraph blueprint as needed. After revising the live plan, save a timestamped archive snapshot so the iteration history remains visible.
```

## Template C: Freeze The Plan

```text
Convert the current planning draft into a frozen review framework. Keep the user-approved construct definitions, relationship logic, section architecture, and paragraph blueprint explicit. Add a short note that future literature additions should be integrated into this framework unless the author later revises it.
```

## Planner Questions To Resolve With The User

1. `Which constructs or concepts need separate definition tracing in this review?`
2. `What exact relationship, mechanism, or question links those constructs?`
3. `Which sections should structure the review, and which section should carry the most weight?`
4. `What should each section's paragraphs accomplish?`
5. `Which parts of the architecture are now fixed, and which still need revision?`
