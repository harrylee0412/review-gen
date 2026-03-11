---
name: review-orchestrator
description: Coordinate long-running literature review projects across the search, planning, and writing subagents. Use when the user wants the system to decide the next stage, enforce plan approval before drafting, or manage the review workflow over time.
---

# Review Orchestrator

Use this skill when the user wants the literature-review system to behave like a coordinated multi-agent workflow rather than a set of manually switched skills.

This skill acts as the controller for three subagents:

- `openalex-ajg-insights` for literature collection and evidence preparation
- `management-review-planner` for framework design and iterative plan refinement
- `management-review-writer` for prose drafting inside the approved framework

## Core Principle

Keep the workflow file-based and transparent, but let the controller decide which subagent should act next.

## Gatekeeping Rules

1. Do not send the project to the writer until the user has explicitly approved the review plan in the conversation.
2. After the user says the plan is approved, update the plan status through the orchestration script. Do not ask the user to manually edit the file.
3. When the plan is approved or reopened, record that state and create a timestamped archive snapshot under `07_plan/history/`.
4. When new literature is added after plan approval, preserve the existing framework by default.
5. Only reopen the plan if the user explicitly asks to revise the framework.

## Workflow

1. Inspect the workspace state with `scripts/review_state_manager.py status`.
2. Route to the correct subagent.
3. If the user explicitly approves the plan, run `approve-plan`.
4. If the user explicitly wants to revise the framework, run `reopen-plan` and return to the planner.
5. Keep all handoffs grounded in workspace files rather than ephemeral chat memory.

## What To Ask The User

When a draft plan is ready, ask directly whether the framework should be frozen.

If the user says yes, run the approval command yourself.

## Platform-Agnostic Quick Start

Use these placeholders on any operating system:

- `<workflow-python>`: the Python interpreter that can run the orchestration script
- `<review-gen-home>`: the folder containing the `review-gen` package or its installed skills
- `<review-workspace>`: the target review workspace

```text
python <review-gen-home>/skills/review-orchestrator/scripts/review_state_manager.py \
  status \
  --workspace <review-workspace>
```

After the user explicitly approves the framework:

```text
python <review-gen-home>/skills/review-orchestrator/scripts/review_state_manager.py \
  approve-plan \
  --workspace <review-workspace> \
  --approved-by user-confirmed-in-chat
```

## References

Read only what is needed:

- `references/orchestration-rules.md`
