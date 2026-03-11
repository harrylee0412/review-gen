# Orchestration Rules

Use this note when coordinating the literature-review workflow across subagents.

## Controller Responsibilities

The orchestrator should:

- inspect the workspace state
- identify the correct next subagent
- enforce the plan-approval gate before drafting
- preserve the approved section and paragraph blueprint by default
- record approval or reopening events and save timestamped plan snapshots

## Approval Rule

Plan approval is a conversational decision, not a manual file-editing task.

The correct workflow is:

1. planner produces `review_plan.md`
2. user reviews and discusses the section and paragraph blueprint
3. user explicitly says the framework is approved
4. orchestrator runs the approval command and records the approval in the plan file and history archive

## Reopen Rule

If the user wants to change the architecture, paragraph logic, construct definitions, or relationship logic, the orchestrator should reopen the plan and route the project back to the planner.
