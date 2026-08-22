# MwalimuKit Agent Workflow

## Required context handoff

Before doing any work, read [the project state](../docs/agent-context/project-state.md). Treat it as the source of truth for the active task, completed work, constraints, decisions, validation results, and next action.

At the start of a new task or session:

1. Read the state document before searching broadly or editing files.
2. Reconcile the user's request with the state document. Do not silently discard unfinished work, constraints, or decisions.
3. If the state is missing, stale, or contradictory, pause and ask the user to confirm the intended starting point.
4. Add the task to the state document before the first substantive edit.

## Chunked execution

Break complex work into chunks of **five to seven concrete steps**. Each step must have one observable outcome and a focused validation check. Do not run a long task as one uninterrupted conversation.

For every chunk:

1. Write the chunk plan and its acceptance checks in the state document.
2. Execute only that chunk.
3. After each step, update the state document with what changed, validation evidence, and any new risks or decisions.
4. At the end of the chunk, run its validation checks and update the state document.
5. Stop and present a checkpoint summary for user review. Do not begin the next chunk until the user explicitly approves it.

If the user approves the next chunk, start that chunk in a new agent session with this state document as the handoff, then reread it before working. If the user changes scope, record the change as a decision before continuing.

## State document updates

The state document is a living handoff, not a final report. Keep it concise and factual. Preserve completed history, but move stale detail into the relevant checkpoint rather than deleting decisions or validation evidence. Never claim a step is complete without evidence.

Every update must keep these sections accurate:

- current status and active chunk
- completed work and validation evidence
- in-progress work and next action
- constraints, risks, and unresolved questions
- decisions and their rationale
- files changed
- checkpoint awaiting approval, when applicable

Use the state document as the memory passed into every new agent session.
