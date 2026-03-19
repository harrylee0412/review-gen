# CLAUDE.md — review-gen workflow instructions

This project is a multi-stage literature review toolkit for management research.
Claude Code should act as the **review-orchestrator** and route tasks to the correct skill automatically.

## Project layout

```
backend/openalex-ajg-mcp/   # OpenAlex + AJG search backend
backend/paper-download-mcp/  # PDF download backend
skills/
  openalex-ajg-insights/     # search, corpus, download, convert, chunk
  management-review-planner/ # plan framework before drafting
  management-review-writer/  # draft prose from approved plan
  review-orchestrator/       # workflow coordination rules
```

## Subagent delegation strategy

To preserve main-conversation context, delegate heavy work to subagents via the Agent tool.
Each subagent runs in its own context window and returns only a summary.

### Stage 1 — Corpus building (subagent)

When the user asks to search, collect, or prepare literature, spawn a subagent with this prompt pattern:

> You are working on a literature review project. Read `skills/openalex-ajg-insights/SKILL.md` for full instructions.
> Workspace: <review-workspace>
> Task: [user's specific request — search, merge corpus, download PDFs, convert with MinerU, chunk, etc.]
> Scripts are in `skills/openalex-ajg-insights/scripts/`.
> When done, return a concise summary of what was created/updated and any issues encountered.

### Stage 2 — Plan building (subagent)

When the corpus is ready and the user wants a review framework, spawn a subagent:

> You are working on a literature review project. Read `skills/management-review-planner/SKILL.md` for full instructions.
> Workspace: <review-workspace>
> Task: Build or revise `07_plan/review_plan.md` for topic "[topic]".
> Run `skills/management-review-planner/scripts/build_review_plan.py` with appropriate flags.
> Return the generated plan summary and list of open decisions for user review.

### Stage 3 — Plan refinement (main agent)

After the planning subagent returns, the main agent presents the plan to the user in conversation.
Discuss, refine, and iterate here — this keeps the interactive back-and-forth in the main context where it belongs.

Do NOT delegate plan discussion to a subagent. The user needs to see and approve the framework directly.

### Stage 4 — Writing (subagent)

Only after the user explicitly approves the plan. Spawn a subagent:

> You are working on a literature review project. Read `skills/management-review-writer/SKILL.md` for full instructions.
> Workspace: <review-workspace>
> Task: Draft the literature review following the approved `07_plan/review_plan.md`.
> First run `skills/management-review-writer/scripts/build_review_packet.py` to generate the writing packet and citation allowlist.
> Then draft the review. Then run `skills/management-review-writer/scripts/validate_draft_citations.py` to audit citations.
> Return: draft location, citation audit result, and any flagged issues.

### When to use subagents vs. main agent

| Task | Where |
|------|-------|
| Literature search, download, conversion | Subagent |
| Corpus merge, manifest preparation | Subagent |
| Plan generation | Subagent |
| Plan review, discussion, approval | Main agent |
| Prose drafting | Subagent |
| Citation audit | Subagent |
| Final review and delivery discussion | Main agent |

Rule of thumb: file-heavy and script-heavy work → subagent. User interaction and decisions → main agent.

## Non-negotiable gates

- **No drafting before plan approval.** If `07_plan/review_plan.md` is missing or unapproved, route to planner.
- **No final delivery before citation audit passes.** Run `validate_draft_citations.py` before treating a draft as final.
- **No citations outside allowlist** unless explicitly verified and added.

## Plan approval flow

1. Planning subagent produces `review_plan.md` and returns summary
2. Main agent presents plan to user for discussion
3. User explicitly says "approved" / "freeze" / "确认"
4. Main agent runs: `python skills/review-orchestrator/scripts/review_state_manager.py approve-plan --workspace <workspace> --approved-by user-confirmed-in-chat`
5. Only then spawn writing subagent

## Key conventions

- Workspace paths use placeholders: `<review-workspace>`, `<review-gen-home>`
- All scripts are platform-agnostic (PowerShell, bash, macOS)
- PDF download is incremental — skips already-downloaded papers
- MinerU API key goes in `04_fulltext/mineru.env`
- Chinese literature RIS files go in `02_corpus/cnki_ris/`
- `--top-papers-mode dynamic` prefers screened-in papers over backfill

## When adding new literature after plan approval

- Preserve the existing framework by default
- Only reopen the plan if the user explicitly asks to revise the structure
- Record reopen events with timestamped snapshots

## Commit style

Use imperative mood, concise subject line. Examples from this repo:
- "Add dynamic paper selection and citation audit workflow"
- "Integrate manifest-driven paper downloads"
- "Bundle openalex backend into review-gen"
