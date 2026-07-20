# Module 1: Minimal Agent Loop

**File:** `module01_agent_loop.py`
**Builds on:** Module 0

## Concept

We fix Module 0's "no memory" problem by introducing two things:

1. A **conversation history** (`messages` list) that persists across turns.
2. A **loop** that keeps calling the LLM until a stopping condition is met.

There are still no real tools in this module — the model can only think
in text across multiple turns. The stopping condition is a plain text
marker (`TASK_COMPLETE`) the model is instructed to emit when it's done,
which our code detects and parses.

## What's new since Module 0

| Module 0 | Module 1 |
|---|---|
| One `messages` list per call, discarded after | One `messages` list, appended to and reused every turn |
| No loop | `for turn in range(1, MAX_TURNS + 1): ...` |
| No stopping condition | Text marker `TASK_COMPLETE` checked after each response |

## Key takeaway

> The core of an "agent loop" is just: keep a list, call the LLM, append
> the reply, check if you're done, repeat. Everything else in this course
> (tools, planning, guardrails) is built around this same skeleton.

`MAX_TURNS` acts as a safety valve — always cap loop length, even before
you've added anything else, so a confused model can't run forever.

## Run it

From the project root:

```bash
python module01/module01_agent_loop.py
```

Watch the `[STEP N]` output — it shows exactly what's being sent to the
model and what came back, turn by turn.

## Things to try

- Lower `MAX_TURNS` to 1 and see the "did not finish" fallback message
  fire.
- Change `DONE_MARKER` to something else and update the system prompt to
  match — notice the mechanism doesn't care what the marker text is, only
  that both the prompt and the parsing code agree on it.
- Ask a task that's naturally single-turn (like Module 0's factual
  question) and observe the model still needs to remember to emit the
  marker — this text-marker approach is fragile, which is exactly why
  Module 2 replaces it with structured tool calling.
