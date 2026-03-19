# Full-Text Markdown Reading Strategy

Use this note when Markdown already exists and the task is to extract viewpoints, definitions, methods, or findings without wasting context.

## Goal

Move from full-text availability to focused evidence extraction with the least token cost and the lowest hallucination risk.

## Core Principle

Do not read whole papers first. Build attention in layers:

1. map the paper
2. retrieve only the relevant sections
3. read locally coherent chunks
4. update notes or the evidence table
5. only expand outward if the current question is still unresolved

## Reading Layers

### Layer 1: Structural map

Before reading content, inspect:

- title
- abstract
- heading structure
- whether the paper has clear theory, methods, and results sections

This identifies where the answer is likely to live.

### Layer 2: Question-aligned retrieval

Use retrieval purpose deliberately:

- `viewpoint`
  Best for conceptual arguments, contributions, and literature positioning.
- `definition`
  Best for exact conceptual framing and distinctions from related ideas.
- `method`
  Best for data, measures, empirical design, and identification.
- `finding`
  Best for main results, implications, and boundary conditions.

### Layer 3: Neighbor expansion

If one chunk looks important, add its immediate neighbors. This usually preserves local argument flow without pulling the whole section.

### Layer 4: Escalation

Expand to more chunks only when:

- the retrieved text is incomplete
- the chunk contradicts the abstract
- the design is crucial to the user question
- two papers appear to disagree
- the paper is likely a benchmark citation

## Chunking Strategy

The default chunking rule in `review_workflow.py` is intentionally simple:

- split by Markdown headings first
- classify each section by likely role
- break long sections into paragraph-based chunks
- keep a modest overlap so definitions and transitions are not cut off
- skip references by default

Default parameters:

- target size: about 450 words
- overlap: about 80 words

This usually works better than sentence-level splitting because academic claims often unfold across several paragraphs.

## Retrieval Strategy

The retrieval logic is lexical and section-aware.

It scores chunks using:

- query-token matches in title, heading, and content
- extra weight when the heading itself matches the topic
- section boosts based on the active purpose

Section priorities:

- `viewpoint`: abstract, introduction, theory, discussion
- `definition`: abstract, introduction, theory
- `method`: methods, appendix, results
- `finding`: results, discussion, abstract

This is a lightweight first-stage retriever. It saves tokens and gives AI a stable shortlist before synthesis.

## Recommended Reading Order By Task

For contribution mapping:

1. abstract
2. introduction
3. theory or contribution section
4. discussion

For concept definition:

1. abstract
2. introduction
3. theory or literature section
4. discussion if concept boundaries remain unclear

For causal credibility:

1. abstract
2. methods or design
3. results
4. appendix only if the design still looks ambiguous

For variable construction or replication:

1. methods
2. measures
3. appendix
4. notes linked to tables or supplementary material

## Evidence Discipline

After each retrieved chunk, update either:

- `evidence_table.csv`, if the point is stable enough to reuse
- a short memo in `07_plan`, if the point is provisional

Capture only what the text supports:

- question
- claim
- mechanism
- method or data context
- key finding
- scope condition
- limitation

## What Usually Goes Wrong

- reading the whole paper before clarifying the question
- pulling too many chunks from too many papers at once
- mixing abstract claims with full-text claims without labeling them
- retrieving methods when the task is conceptual synthesis
- treating appendices as mandatory instead of conditional

## Practical Rule Of Thumb

If the user asks for the paper's main idea, start with `viewpoint`.
If the user asks what the construct means, start with `definition`.
If the user asks whether the identification is credible, start with `method`.
If the user asks what the paper actually finds, start with `finding`.
