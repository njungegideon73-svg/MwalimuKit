---
name: context-driven-task
description: Execute a MwalimuKit task through a persistent project state document, five-to-seven-step chunks, and explicit user approval checkpoints.
agent: agent
---

# Context-Driven Task

Use this prompt for any task that may take more than a few focused edits.

## Start here

Read [docs/agent-context/project-state.md](../../docs/agent-context/project-state.md) before planning or editing. The state document is the handoff from prior sessions and must travel with this task.

Record the requested outcome, current baseline, and first chunk in the state document. State one falsifiable implementation hypothesis and one cheap check that could disconfirm it before editing.

## Plan in chunks

Decompose the work into chunks of five to seven steps. A step should be small enough to validate independently and should name its expected evidence. Do not plan or execute the next chunk until the current chunk has passed its checkpoint.

## Execute one chunk

For each step in the active chunk:

1. Make the smallest necessary change.
2. Run the narrowest useful validation.
3. Update `docs/agent-context/project-state.md` immediately with the result.

If validation fails, keep the state marked `in progress`, record the failure and likely cause, repair only that chunk, and rerun the same check. Do not hide unrelated failures.

## Mandatory checkpoint

When all steps in the chunk are complete, update the state document and stop. Present:

- the chunk completed
- files changed
- validation commands and results
- decisions made
- risks or unresolved questions
- the proposed next chunk
- the exact approval needed to continue

Wait for explicit user approval. “Continue”, “approve”, or an equivalent instruction is required before starting another chunk. Start each approved chunk in a new agent session with the state document passed in as its handoff, then reread it before working. If the user requests changes, record them in the state document and revise the current chunk rather than silently advancing.
