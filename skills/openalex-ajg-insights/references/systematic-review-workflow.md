# Systematic Review Workflow

Use this note when the user wants a reusable review corpus instead of a one-off literature scan.

## Goal

Turn repeated topic searches into a cumulative review workspace that preserves:

- every raw search run
- a deduplicated master corpus
- title and abstract screening decisions
- full-text collection status
- full-text evidence extraction

## Recommended Workspace Layout

`review_workflow.py init-workspace` creates this structure:

- `01_search/raw_json`
  Store raw JSON from each `openalex_ajg_bridge.py` run.
- `01_search/exports`
  Store optional Excel or RIS exports.
- `02_corpus`
  Store the deduplicated master corpus.
- `03_screening`
  Store `screening_table.csv` and `evidence_table.csv`.
- `04_fulltext/pdf_inbox`
  Store manually collected PDFs waiting for conversion.
- `04_fulltext/pdf_archive`
  Store original PDFs after conversion.
- `05_mineru/raw_zip`
  Store raw MinerU zip packages.
- `05_mineru/extracted`
  Store extracted Markdown and JSON outputs.
- `05_mineru/batch_jobs`
  Store MinerU request and polling snapshots.
- `06_chunks`
  Store chunk indexes for retrieval.
- `07_plan`
  Store synthesis notes and memo drafts.
- `08_outputs`
  Store review outputs prepared for the user.

## Recommended Order

1. Search broadly enough to avoid missing obvious anchor papers.
2. Save each run into `01_search/raw_json`.
3. Merge all runs into a master corpus.
4. Screen by title and abstract.
5. Create a full-text shortlist.
6. Ask the user to collect only the needed PDFs.
7. Convert PDFs to Markdown.
8. Chunk and retrieve before synthesizing.
9. Update `evidence_table.csv` as full-text insights accumulate.

## Screening Guidance

The title and abstract screen should answer only three questions:

- Is this paper genuinely about the concept, or only mentioning it?
- Is it central enough to stay in the review?
- Does the review need the full text, or is the abstract sufficient?

Use these fields in `screening_table.csv`:

- `included_title_abstract`
  Mark `yes` or `no`.
- `exclusion_reason`
  Briefly record why a paper is out.
- `need_full_text`
  Mark `yes` only when the project needs deeper reading.
- `screening_notes`
  Keep this short and factual.

## Evidence Table Guidance

`evidence_table.csv` should only be updated after reading either the abstract carefully or the retrieved full-text chunks.

Prefer short, reusable entries:

- `research_question`
- `core_claim`
- `mechanism`
- `data_context`
- `method_design`
- `main_finding`
- `boundary_condition`
- `limitation`
- `source_level`

Use `source_level` to mark whether the row is based on `abstract-only` or `full-text`.

## What Not To Do

- Do not overwrite raw search outputs.
- Do not treat the master corpus as the evidence table.
- Do not collect full text for every paper by default.
- Do not ask AI to read entire PDFs directly.
