# Module 4: State & Memory Management

**File:** `module04_memory_management.py`
**Builds on:** Module 3

## Concept

Conversation history has grown unbounded so far. Real tasks can run for
dozens of turns and eventually exceed the model's context window (and get
expensive). This module introduces **memory compression**: periodically
summarizing older parts of the conversation down to a compact paragraph,
while keeping the most recent messages verbatim.

- **Short-term memory** — the most recent `KEEP_RECENT_MESSAGES`, kept
  with full fidelity.
- **Long-term memory** — everything older, periodically compressed via a
  separate LLM summarization call.

## What's new since Module 3

| Module 3 | Module 4 |
|---|---|
| History grows forever | `compress_history()` runs every turn, trims once past a threshold |
| No summarization | A separate LLM call summarizes older messages into one `[MEMORY SUMMARY]` message |
| N/A | `find_safe_cut_index()` — the trickiest part of this module |

## The tricky part: safe cut points

The OpenAI-compatible API requires each `role="tool"` message to correspond
to a tool call requested by an assistant message. If you cut history in the
middle of a tool-call/tool-result transaction, the next API call will error.
`find_safe_cut_index()` therefore allows cutting only after an assistant
message that did **not** request a tool, or after **all** tool calls from one
assistant message have received their results. It matches results by
`tool_call_id`, so parallel tool calls are kept together as one transaction.

This function can be difficult to understand line by line, and that is not
required to continue with the course. It is enough to understand its role:
it finds a boundary where history can be compressed without violating the
OpenAI-compatible API's tool-call ordering requirements.

## Key takeaway

> Compression trades fidelity for context-window headroom. The summary
> is a lossy compression of what happened — good enough to keep the task
> going, but you're deliberately discarding detail. Module 5 shows an
> alternative memory strategy (isolation instead of compression) for
> independent subtasks.

## Run it

From the project root:

```bash
python module04/module04_memory_management.py
```

Look for `[MEMORY]` log lines — they only appear once history has grown
past `MAX_MESSAGES_BEFORE_SUMMARY`. The example task is deliberately
multi-step so this triggers at least once.

The prompt asks the model to do the work "one at a time," but that instruction
does not guarantee one task per model call. Depending on the model, it may
request several tools in parallel or complete multiple tasks in one turn.
That produces fewer agent-loop steps, and the entire task may finish before
the history reaches the compression threshold. If no `[MEMORY]` log appears
for this reason, it does not mean the compression logic is broken.

## Things to try

- Lower `MAX_MESSAGES_BEFORE_SUMMARY` to force compression to trigger
  sooner and observe the `[MEMORY]` logs more often.
- Print the full `messages` list right before and after a compression to
  see exactly what got replaced.
- Try a very short task where compression never triggers, and confirm
  `compress_history()` is a no-op in that case (no wasted summarization
  calls when they're not needed).
