# PDF To Markdown Pipeline

Use this note when the user wants to move from shortlisted papers to machine-readable full text.

## Why This Pipeline Exists

Large models usually do a poor job with raw PDFs. The safer workflow is:

1. collect the needed PDFs
2. standardize filenames
3. convert PDFs to Markdown
4. chunk the Markdown
5. retrieve only the relevant chunks

## PDF Storage Rules

Store PDFs in:

- `04_fulltext/pdf_inbox`
  Newly collected files waiting for conversion.
- `04_fulltext/pdf_archive`
  Original files retained after conversion.

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

## Manifest Strategy

Use `04_fulltext/fulltext_manifest.csv` as the operational checklist.

Key fields:

- `expected_pdf_name`
- `pdf_status`
- `pdf_path`
- `md_status`
- `md_path`
- `mineru_batch_id`
- `mineru_error`

This makes it easy to see:

- which important papers are still missing
- which PDFs have been uploaded
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
2. Ask the user to collect the missing PDFs.
3. Put the PDFs into `pdf_inbox` using the naming rule.
4. Create `mineru.env` from `mineru.env.example`.
5. Run `convert-pdfs-with-mineru`.
6. Check `fulltext_manifest.csv` for failed or missing outputs.
7. Only then run `chunk-markdown` and retrieval.