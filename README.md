# review-gen

`review-gen` is a long-horizon literature review toolkit for management, strategy, entrepreneurship, innovation, and organization research. It connects literature search, corpus construction, full-text collection, PDF-to-Markdown conversion, chunk retrieval, review planning, plan approval, and review drafting into one stable multi-agent workflow.

## Platform-Agnostic Mode

This version is designed to be platform-agnostic. The core scripts no longer depend on fixed Windows paths. Replace three placeholders when you run the toolkit:

- `<workflow-python>`: the Python interpreter that can run the review scripts
- `<review-gen-home>`: the folder containing the `review-gen` package
- `<review-workspace>`: the folder for one specific literature review project

The same workflow logic can therefore be used from Windows PowerShell, macOS Terminal, or a Linux shell. The main difference is only the local path you supply.

## Requirements

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

The current toolkit depends on:

- `requests`
- `openxlab-dev`

Notes:

- `openxlab-dev` is used when you authenticate MinerU through `MINERU_ACCESS_KEY` and `MINERU_SECRET_KEY`.
- If you only use a direct MinerU bearer token in `MINERU_API_KEY`, the OpenXLab path is not required logically, but it is still included in `requirements.txt` for convenience.
- Literature search through `openalex-ajg-insights` also depends on a local clone of `openalex-ajg-mcp`, which is not bundled inside this repository.

## What The Toolkit Contains

The package currently includes four skills:

- `openalex-ajg-insights`
  Searches ranked journals, preserves search corpora, prepares full-text manifests, converts PDFs to Markdown with MinerU, and retrieves abstract or full-text viewpoints efficiently.
- `management-review-planner`
  Builds and iteratively refines the review framework before drafting begins.
- `management-review-writer`
  Turns the approved framework and collected evidence into formal literature review prose.
- `review-orchestrator`
  Routes the project to the next subagent, checks project state, and handles plan approval or reopening after explicit user confirmation.

## Planning Logic

The planner no longer assumes a single focal concept. Instead, it starts from the user topic and the available literature, then decomposes the topic into constructs, concepts, mechanisms, and relationships that need to be reviewed.

The planning sequence is:

1. trace construct definitions and conceptual boundaries
2. propose the section-level architecture
3. specify the paragraph-level blueprint inside each section
4. refine the framework with the user before freezing it

This means the planner can support single-concept reviews, two-concept relationship reviews, mediation logic, moderation logic, or more open-ended conceptual topics without forcing them into a rigid preset template.

## Planning Archives

Every planner revision writes the active framework to `07_plan/review_plan.md` and also creates a timestamped snapshot in `07_plan/history/`.

This gives you two layers of planning records:

- the current live execution framework in `review_plan.md`
- a full checkpoint history in `07_plan/history/*.md`

When the plan is approved or reopened, the orchestrator also leaves a timestamped status snapshot. This makes framework iteration auditable over time.

## MinerU Authentication

MinerU credentials are intentionally kept outside the code in a dedicated env file, usually:

`04_fulltext/mineru.env`

The workflow supports two authentication paths:

1. `MINERU_API_KEY`
   Use this when you already have a direct MinerU token.

2. `MINERU_ACCESS_KEY` + `MINERU_SECRET_KEY`
   Use these when you authenticate through the OpenXLab SDK. The workflow will try to exchange them for a JWT before calling MinerU.

The request header is normalized automatically to:

`Authorization: Bearer <token>`

A typical env file looks like this:

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

Recommended practice:

- prefer `MINERU_API_KEY` if you already have a working MinerU bearer token
- otherwise store `MINERU_ACCESS_KEY` and `MINERU_SECRET_KEY`
- never hardcode credentials in scripts, notes, or prompts

## Recommended Workflow

1. Use `openalex-ajg-insights` to build the corpus.
2. Use `management-review-planner` to generate the first `review_plan.md`.
3. Refine the section and paragraph blueprint with the user.
4. Let every planning revision create a timestamped archive checkpoint.
5. After explicit user confirmation, let `review-orchestrator` approve the plan.
6. Use `management-review-writer` to draft the review inside the approved framework.

## Directory Layout

```text
review-gen/
├── README.md
├── README_zh.md
├── requirements.txt
└── skills/
    ├── openalex-ajg-insights/
    ├── management-review-planner/
    ├── management-review-writer/
    └── review-orchestrator/
```

## Suggested Usage Order

In long-running projects, start with `openalex-ajg-insights`, then let `review-orchestrator` decide whether the workspace should move into planning or writing.
