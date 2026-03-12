# PDF To Markdown Pipeline

Use this note when the user wants to move from shortlisted papers to machine-readable full text.

## Why This Pipeline Exists

Large models usually do a poor job with raw PDFs. The safer workflow is:

1. shortlist the needed papers
2. download or collect the PDFs
3. standardize filenames
4. convert PDFs to Markdown
5. chunk the Markdown
6. retrieve only the relevant chunks

## PDF Acquisition Strategy

There are now two acquisition paths:

- manual collection into `04_fulltext/pdf_inbox`
- incremental downloading through `scripts/download_manifest_papers.py`

The automated path is useful when the review already has a `fulltext_manifest.csv` and the user wants to fetch classic or priority papers first, then return later for additional papers.

Recommended order:

1. run `prepare-fulltext-manifest`
2. run `download_manifest_papers.py --min-priority high --max-papers N` for foundational papers
3. inspect the updated manifest
4. manually supplement any papers that still need special handling
5. only then run MinerU conversion

## PDF Storage Rules

Store PDFs in:

- `04_fulltext/pdf_inbox`
  Newly collected or newly downloaded files waiting for conversion.
- `04_fulltext/pdf_archive`
  Original files retained after conversion.
- `04_fulltext/download_batches`
  JSON summaries of incremental download attempts.

Preferred filename rule:

`YEAR__FirstAuthor__ShortTitle.pdf`

Examples:

- `2005__Baker__Creating_Something_from_Nothing.pdf`
- `2021__Reypens__Beyond_Bricolage.pdf`

Why this rule helps:

- filenames are readable
- the same stem can be reused for Markdown folders
- manual checking is easy
- chunk retrieval can map a Markdown folder back to a paper key

The automated downloader renames successful downloads to the manifest's `expected_pdf_name`, so manual and automatic acquisition stay aligned.

## Manifest Strategy

Use `04_fulltext/fulltext_manifest.csv` as the operational checklist.

Key fields:

- `expected_pdf_name`
- `pdf_status`
- `pdf_path`
- `download_status`
- `download_source`
- `download_error`
- `download_batch`
- `md_status`
- `md_path`
- `mineru_batch_id`
- `mineru_error`

This makes it easy to see:

- which important papers are still missing
- which PDFs were downloaded automatically
- which download attempts failed and why
- which papers still need manual intervention
- which conversions failed
- which papers already have usable Markdown

## MinerU API Notes

Official docs:

- [MinerU API docs](https://mineru.net/doc/docs/index.html?theme=light&v=1.0)
- [MinerU output files](https://opendatalab.github.io/MinerU/reference/output_files/)

Useful details from the docs:

- local-file batch upload uses `POST /api/v4/file-urls/batch`
- the request must include `Authorization: Bearer <token>`
- the response returns a `batch_id` and upload URLs
- after uploading each file with `PUT`, MinerU auto-submits the parsing task
- batch status polling uses `GET /api/v4/extract-results/batch/{batch_id}`
- successful results expose `full_zip_url`
- Markdown and JSON are default output formats
- `content_list.json` is useful for future secondary parsing if needed

## Env File Rule

Keep MinerU credentials in a dedicated env file, for example:

`04_fulltext/mineru.env`

Template:

```env
MINERU_API_KEY=
MINERU_ACCESS_KEY=replace-with-your-access-key
MINERU_SECRET_KEY=replace-with-your-secret-key
MINERU_API_BASE_URL=https://mineru.net
MINERU_MODEL_VERSION=vlm
MINERU_LANGUAGE=en
MINERU_ENABLE_FORMULA=true
MINERU_ENABLE_TABLE=true
MINERU_IS_OCR=false
```

Store a direct MinerU token in `MINERU_API_KEY` if you have one. Otherwise store `MINERU_ACCESS_KEY` and `MINERU_SECRET_KEY`; the workflow script will try to exchange them for a JWT through the OpenXLab SDK before calling MinerU. Do not hardcode any credential in scripts, notes, or chat responses.

## When To Turn On OCR

Leave OCR off by default for born-digital PDFs.

Turn OCR on when:

- the PDF is scanned
- extracted text is clearly broken
- the paper is image-heavy or contains inaccessible text layers

## Practical Sequence

1. Run `prepare-fulltext-manifest`.
2. Download a first batch of classics or manually collect the missing PDFs.
3. Put all PDFs into `pdf_inbox` using the naming rule.
4. Create `mineru.env` from `mineru.env.example`.
5. Run `convert-pdfs-with-mineru`.
6. Check `fulltext_manifest.csv` for failed or missing outputs.
7. Only then run `chunk-markdown` and retrieval.
