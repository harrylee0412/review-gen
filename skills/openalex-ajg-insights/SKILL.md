---
name: openalex-ajg-insights
description: Search ABS/AJG-ranked literature through the bundled openalex-ajg-mcp backend, preserve review corpora for systematic literature reviews, convert collected PDFs to Markdown with MinerU, and retrieve abstract or full-text viewpoints efficiently.
---

# OpenAlex AJG Insights

Use this skill when the task is a literature review, gap scan, theory-building exercise, journal-targeted search, or any research workflow that needs business and management papers filtered by ABS/AJG and then upgraded into a reusable review corpus.

## Bundled Backend

This skill now ships with an embedded `openalex-ajg-mcp` backend inside the `review-gen` repository.

Default backend location:

- `<review-gen-home>/backend/openalex-ajg-mcp`

If needed, you can still override the backend location with:

- `--repo-root <path>`
- `OPENALEX_AJG_MCP_ROOT=<path>`

This means a fresh machine only needs to clone `review-gen` and install `requirements.txt`; a second standalone clone of `openalex-ajg-mcp` is no longer required for the default workflow.

## Core Scripts

- `scripts/openalex_ajg_bridge.py`
  Use for search, journal scans, and report summaries.
- `scripts/review_workflow.py`
  Use for systematic-review workspaces, corpus merging, full-text manifests, MinerU conversion, Markdown chunking, and retrieval.

## Default Decision Rules

1. Start with abstract screening.
2. Upgrade to full text only for necessary papers.
3. When the user wants a reusable or systematic review, create a review workspace.
4. When the user has collected PDFs, convert them to Markdown before asking AI to read them.
5. When the user asks for viewpoints from full text, do not load whole papers at once.
6. For long-running review projects, hand off to `review-orchestrator` after the corpus is ready.

## Platform-Agnostic Quick Start

Use these placeholders on any operating system:

- `<workflow-python>`: the Python interpreter that can run the workflow scripts
- `<review-gen-home>`: the folder containing the `review-gen` package or its installed skills
- `<review-workspace>`: the target review workspace

### A. Initialize a workspace

```text
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  init-workspace \
  --topic "Entrepreneurial bricolage"
```

### B. Search through the bundled backend

```text
python <review-gen-home>/skills/openalex-ajg-insights/scripts/openalex_ajg_bridge.py \
  search-abs \
  --query "AI agents" \
  --field "INFO MAN" \
  --min-rank "4*" \
  --year-start 2023 \
  --limit 10
```

### C. Merge raw search results into a corpus

```text
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  merge-search-results
```

### D. Prepare the full-text manifest

```text
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  prepare-fulltext-manifest --min-priority medium
```

### E. Convert PDFs to Markdown with MinerU

```text
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  convert-pdfs-with-mineru \
  --env-path <review-workspace>/04_fulltext/mineru.env
```

### F. Chunk and retrieve before reading

```text
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  chunk-markdown
```

```text
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --format markdown \
  --workspace <review-workspace> \
  retrieve-chunks \
  --query "What is the paper's core view?" \
  --purpose viewpoint \
  --top-k 6 \
  --include-neighbors
```

### G. Hand off to the orchestrator

- Use `review-orchestrator` to decide whether the project should go to planning or writing next.

## How To Think While Using This Skill

- For a fast literature scan, stay at the abstract layer.
- For a structured review, keep four layers separate:
  - raw search layer
  - merged corpus and screening layer
  - full-text evidence layer
  - frozen review-plan layer
- For full-text work, retrieve only the chunks needed for the active question.

## References

Read only what the request needs:

- `references/systematic-review-workflow.md`
- `references/pdf-fulltext-pipeline.md`
- `references/full-text-reading-strategy.md`
