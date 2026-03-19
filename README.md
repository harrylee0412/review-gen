# review-gen

`review-gen` is a workflow toolkit for long-horizon literature reviews in management, strategy, entrepreneurship, innovation, and organization studies.

It is designed for one practical goal: **turn a large paper library into a controlled, auditable review pipeline** instead of ad-hoc prompting.

## What It Does

1. Search high-quality journals through ABS/AJG-aware OpenAlex queries.
2. Build and maintain a reusable corpus workspace.
3. Prioritize and download full text incrementally from a manifest.
4. Convert PDF to Markdown (MinerU) and chunk text for retrieval.
5. Build a frozen review plan before drafting.
6. Draft review prose under plan constraints.
7. Prevent citation hallucination with allowlist + DOI audit.

## System Architecture

The system is split into four skills plus two embedded backends.

### Skills

- `openalex-ajg-insights`
  Search, merge corpus, prepare full-text manifest, download PDFs incrementally, convert PDFs to Markdown, and retrieve chunks.
- `management-review-planner`
  Build `review_plan.md`, archive plan revisions, support EN/ZH planning, and use dynamic core-paper selection.
- `management-review-writer`
  Build `review_packet.md` and `review_guardrails.md`, generate `citation_allowlist.jsonl`, and support draft citation auditing.
- `review-orchestrator`
  Enforce workflow gates: plan approval before drafting, citation audit before final delivery.

### Embedded Backends

- `backend/openalex-ajg-mcp`
- `backend/paper-download-mcp`

## Workspace Contract (Single Source of Truth)

Each project uses one workspace (`<review-workspace>`) with stable folders:

```text
01_search/      # raw search outputs
02_corpus/      # merged corpus (master_corpus.jsonl)
03_screening/   # screening and evidence tables
04_fulltext/    # manifest + PDF inbox/archive
05_mineru/      # MinerU raw/extracted outputs
06_chunks/      # chunk index for retrieval
07_plan/        # live plan + history snapshots
08_outputs/     # packets, drafts, citation allowlist, audit report
```

Key control files:

- `02_corpus/master_corpus.jsonl`
- `03_screening/screening_table.csv`
- `04_fulltext/fulltext_manifest.csv`
- `07_plan/review_plan.md`
- `08_outputs/review_packet.md`
- `08_outputs/citation_allowlist.jsonl`
- `08_outputs/citation_audit_report.md`

## End-to-End Workflow

Use placeholders:

- `<workflow-python>`
- `<review-gen-home>`
- `<review-workspace>`

### 1) Initialize workspace

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  init-workspace \
  --topic "Your topic"
```

### 2) Search ABS/AJG journals (default limit increased)

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/openalex_ajg_bridge.py \
  search-abs \
  --query "Your query" \
  --field "INFO MAN" \
  --min-rank "4" \
  --year-start 2018 \
  --limit 50
```

### 3) Merge corpus and prepare full-text manifest

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  merge-search-results

python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  prepare-fulltext-manifest --min-priority medium
```

### 4) Download priority papers incrementally

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/download_manifest_papers.py \
  --workspace <review-workspace> \
  --min-priority high \
  --max-papers 10
```

### 5) Convert PDFs and chunk Markdown

```bash
python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  convert-pdfs-with-mineru \
  --env-path <review-workspace>/04_fulltext/mineru.env

python <review-gen-home>/skills/openalex-ajg-insights/scripts/review_workflow.py \
  --workspace <review-workspace> \
  chunk-markdown
```

### 6) Build plan (dynamic high-quality selection)

```bash
python <review-gen-home>/skills/management-review-planner/scripts/build_review_plan.py \
  --workspace <review-workspace> \
  --topic "Your topic" \
  --word-count 2500 \
  --language en \
  --top-papers-mode dynamic \
  --top-papers 0
```

Notes:

- `dynamic` mode prioritizes screened-in (`included`) papers.
- It does not backfill low-value non-included papers unless `--allow-fallback` is set.
- Chinese planning supports CNKI RIS from `02_corpus/cnki_ris/`.

### 7) Build writing packet and citation allowlist

```bash
python <review-gen-home>/skills/management-review-writer/scripts/build_review_packet.py \
  --workspace <review-workspace> \
  --topic "Your topic" \
  --top-papers-mode dynamic \
  --top-papers 0 \
  --output-path <review-workspace>/08_outputs/review_packet.md
```

### 8) Validate citations before final delivery

```bash
python <review-gen-home>/skills/management-review-writer/scripts/validate_draft_citations.py \
  --workspace <review-workspace> \
  --draft-path <review-workspace>/08_outputs/review_draft.md
```

Audit checks:

- DOI in draft must exist in `citation_allowlist.jsonl`.
- DOI can be resolver-checked via Crossref/OpenAlex.
- Optional strict mode checks author-year mapping.

## Quality Gates (Non-Negotiable)

1. No prose drafting before plan approval.
2. No final delivery before citation audit passes.
3. No citation outside allowlist unless explicitly verified and added.

## Platform and Setup

Install the base dependencies:

```bash
pip install -r requirements.txt
```

### MinerU API for PDF-to-Markdown

In this project, the MinerU integration is mainly used to convert collected PDF papers into Markdown so the downstream chunking, retrieval, planning, and drafting steps work on clean text instead of raw PDFs.

How to get the API:

1. Register or sign in on the [MinerU official site](https://mineru.net/).
2. Apply for an API token from the MinerU web console after login. The official API docs describe this token as a token "obtained from the official website", but do not publish a stable deep link to the token page, so the safest entry is the main site after login.
3. Read the official API docs before use:
   - [MinerU API docs (EN)](https://mineru.net/doc/docs/index_en/)
   - [MinerU API docs (ZH)](https://mineru.net/doc/docs/)
   - [Rate limits / quota notes](https://mineru.net/doc/docs/limit/)
4. Put the token into `04_fulltext/mineru.env` as:

```env
MINERU_API_KEY=your-token-from-mineru
```

Notes:

- The official docs state that API calls require an `Authorization: Bearer <token>` header.
- The API is currently in beta, and the published limits include up to 200 MB and 600 pages per file, with 2000 pages per day at the highest priority tier per account.

The toolkit is path-agnostic and works in PowerShell, macOS Terminal, and Linux shells.

## Repository Layout

```text
review-gen/
├── backend/
│   ├── openalex-ajg-mcp/
│   └── paper-download-mcp/
├── README.md
├── README_zh.md
├── requirements.txt
└── skills/
    ├── openalex-ajg-insights/
    ├── management-review-planner/
    ├── management-review-writer/
    └── review-orchestrator/
```
