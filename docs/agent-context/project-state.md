---
document: mwalimukit-project-state
version: 1
updated: 2026-08-22
status: ready
active_task: null
active_chunk: null
checkpoint: none
---

# MwalimuKit Project State

This is the persistent context handoff for agent sessions. Read it before every task. Update it after every completed step, validation result, decision, or scope change.

## How to use this document

- Keep one active task at a time unless the user explicitly asks for parallel work.
- Decompose complex work into chunks of five to seven independently verifiable steps.
- Pause after every chunk and wait for explicit user approval before continuing.
- Never mark work complete without recording validation evidence.
- Keep the next action concrete enough that a new session can resume without reconstructing the conversation.

## Current status

| Field               | Value                                        |
| ------------------- | -------------------------------------------- |
| Status              | Ready for a new task                         |
| Active task         | None                                         |
| Active chunk        | None                                         |
| Last completed step | None                                         |
| Next action         | Capture the user's task and define chunk one |
| Checkpoint          | No approval pending                          |

## Active task

### Requested outcome

_No active task._

### Scope and acceptance criteria

_Populate when a task begins. Use observable outcomes and focused checks._

### Implementation hypothesis

_State one falsifiable hypothesis before the first substantive edit._

### Discriminating check

_Name the cheapest check that could disconfirm the hypothesis._

## Execution plan

### Chunk 1: _not started_

| Step | Expected outcome         | Validation      | Status      |
| ---- | ------------------------ | --------------- | ----------- |
| 1    | _Define before starting_ | _Focused check_ | Not started |
| 2    | _Define before starting_ | _Focused check_ | Not started |
| 3    | _Define before starting_ | _Focused check_ | Not started |
| 4    | _Define before starting_ | _Focused check_ | Not started |
| 5    | _Define before starting_ | _Focused check_ | Not started |

Add steps 6 and 7 only when needed. Start a new chunk only after the current chunk is approved.

## Completed work and evidence

| Date       | Task/chunk          | Completed step                                           | Evidence                                                                                 |
| ---------- | ------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 2026-08-22 | Workflow foundation | Created persistent state and agent workflow instructions | `git diff --check` passed; required workflow phrases and frontmatter boundaries verified |

## In progress

_Nothing is currently in progress._

## Decisions

| Date       | Decision                                                    | Rationale                                                                                                 |
| ---------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 2026-08-22 | Store the handoff in `docs/agent-context/project-state.md`  | Versioned project-local context travels with the repository and is readable by every agent session        |
| 2026-08-22 | Use an always-on instruction plus an on-demand prompt       | The read/update rule must be constant, while the full chunk workflow should be reusable for complex tasks |
| 2026-08-22 | Require five to seven steps per chunk and explicit approval | Limits context drift and gives the user a review gate between execution scopes                            |

## Constraints and risks

- Agent instructions guide behavior but do not provide a hard technical lock against an agent editing before a checkpoint.
- The state document must be updated manually by the active agent after each step; concurrent agents could overwrite it.
- Keep secrets, tokens, credentials, and private user data out of this document.
- Preserve unrelated user changes in the working tree.

## Files changed

- `.github/copilot-instructions.md`
- `.github/prompts/context-driven-task.prompt.md`
- `docs/agent-context/project-state.md`

## Checkpoint

### Review status

No approval pending. The workflow foundation is ready for user review. Future feature work should use the checkpoint template below.

### Checkpoint summary template

Use this format when pausing between chunks:

```text
Chunk: <number and name>
Completed: <steps>
Files changed: <paths>
Validation: <commands and concise results>
Decisions: <new decisions, or none>
Risks/questions: <items, or none>
Next chunk: <five to seven proposed steps>
Approval needed: Reply with "approve" or describe changes.
```
