# Review Writing Standards

Use this note when drafting management or strategy literature reviews from a collected corpus.

## Adapted Rules

### 1. Follow the approved architecture

The writer is not the architect. The section logic and paragraph blueprint should already be settled in `review_plan.md`.

### 2. Define every construct before claiming relationships

If the topic involves more than one construct, define them separately before claiming how they relate to one another.

### 3. Write paragraph by paragraph against the blueprint

Each paragraph should fulfill the role assigned in the plan. If a paragraph drifts, fix the paragraph rather than redesign the structure.

### 4. Synthesize; do not catalogue

Each paragraph should make a claim about the literature as a whole rather than list papers.

### 5. Keep claims proportional to the evidence base

Use abstract-only evidence conservatively, and use full-text evidence for finer-grained claims when available.

### 6. Use real citations only

Every in-text citation must correspond to a real paper in the collected corpus or a verified paper the writer explicitly checked.

### 7. Use an allowlist and audit gate

Build `citation_allowlist.jsonl` before drafting and treat it as the citation whitelist for the current review run.  
After drafting, run `validate_draft_citations.py`. If the audit fails, revise the draft before delivery.

## Local Writing Checklist

Before finalizing a review, verify that:

- the approved `review_plan.md` has been followed
- the construct-definition paragraphs match the approved definitions
- the paragraph blueprint has been respected
- citations are real and in APA style by default
- every DOI in the draft appears in `citation_allowlist.jsonl`
- citation audit report is pass
- the concluding gap follows from the synthesis
