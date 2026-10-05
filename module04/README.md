# Module 4: Context Management

**File:** `module04_memory_management.py`
**Builds on:** Module 3

## Concept

Long tasks accumulate more history than we want to send on every model call.
This module introduces **conversation compression**: summarize older completed
execution steps, while keeping the original task and recent steps verbatim.

An **execution step** is one assistant response plus **all** the tool results
it requested. Two tools requested in the same response belong to one step,
not two. A final answer ends this example's loop and needs no further storage.

We keep four pieces of context:

| State | Purpose | What compression does |
|---|---|---|
| `system_prompt` | Agent instructions | Keeps it unchanged |
| `task` | Original user request, including constraints | Keeps it unchanged |
| `summary` | Facts and progress from earlier steps | Updates it with older steps |
| `recent_steps` | Recent completed steps, with full tool arguments and results | Keeps the most recent steps verbatim |

This is **in-session context management**. The summary is not persistent
long-term memory: nothing is saved to disk, and a new run starts fresh.
A checkpoint is different again: it records execution state so interrupted
work can resume. Neither persistent memory nor checkpointing is implemented here.

## What's new since Module 3

| Module 3 | Module 4 |
|---|---|
| One growing list of messages | Original task + summary + recent completed steps |
| Every result stays in history | Older steps are replaced by an LLM summary |
| Loop sends its message list directly | `build_messages()` assembles the API request |

The learning pattern is:

```text
previous summary + older completed steps -> updated summary
original task + updated summary + recent steps -> next model call
```

## Keep steps together from the start

Instead of cutting an arbitrary message list and then checking whether tool
calls still match their results, the loop creates a local `step`. It adds the
assistant response and every requested tool's result, then appends the
**completed** step to `recent_steps`. A tool error is also recorded as a result.

Compression only slices the list of completed steps. It cannot separate a
tool request from its results because they are stored in the same step.
There is no need to scan tool-call IDs to find a safe cut point.

The OpenAI-compatible message format still exists at the API boundary:
the loop converts each SDK response into a plain dictionary once, and
`build_messages()` flattens the recent steps when making a request. The
compression policy doesn't need to inspect those API relationships.

## Read the code in this order

1. `Context`: the four pieces of state above.
2. `compress_history()`: split older/recent steps, summarize, then replace.
3. `build_messages()`: assemble the context for the next API call.
4. `run_agent_loop()`: collect all tool results before publishing each step.

`MAX_STEPS_BEFORE_SUMMARY = 3` triggers compression when there are **more than
three** completed steps. `KEEP_RECENT_STEPS = 2` retains the last two. Keep
`1 <= KEEP_RECENT_STEPS <= MAX_STEPS_BEFORE_SUMMARY` when changing these values.

Each summary includes the previous summary so still-relevant facts can carry
forward across repeated compressions. The summarizer sees the original task,
tool arguments, and results, and is asked to retain facts, decisions, completed
work, and remaining work. An empty summary or API error stops the run without
replacing the existing context; retry policies belong to the recovery lesson.

## Key takeaway

> Preserve important boundaries when recording history, and compression
> becomes a simple policy: summarize old steps, retain recent steps, and
> keep the original request. A summary is still lossy background context,
> not an authoritative replacement for the task or the original evidence.

Step counts are deliberately easy to teach, but do **not** enforce a token
budget: one tool result, the original task, or a summary can itself be large.
The summary's 200-word target is a prompt instruction, not a hard limit.
Token-aware budgeting and oversized tool-result handling are extensions.

## Run it

From the project root with the virtual environment activated:

```bash
python module04/module04_memory_management.py
```

Watch `[STEP]` and `[CONTEXT]` logs. The example asks for five operations, but
a model may batch several tools into one response. It may therefore finish
before compression triggers. Lower the threshold (and keep the retention
setting valid) to make compression more likely. `search_web` remains a stub.


## Things to try

- Set both thresholds to `1`, then compare the context before and after
  compression on a multi-step task.
- Put an important constraint in the original task. Check that it remains
  unchanged in `build_messages()` even after repeated compression.
- Inspect which facts survive several summaries. Does the model still have
  enough information to finish correctly?
- Return a very large tool result and explain why counting steps alone
  doesn't guarantee that a request fits the context window.
- Compare this approach with Module 6's isolated subtask contexts.

Next, [Module 5](../module05/README.md) stores selected project knowledge in
JSON so it survives across runs.
