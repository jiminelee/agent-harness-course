# Module 9: Observability & Debugging

**File:** `module09_observability.py`
**Builds on:** Module 3's tool registry pattern

## Concept

When something goes wrong deep inside a multi-turn, multi-tool agent run,
"read the print statements" doesn't scale. This module introduces
**structured tracing**: every meaningful step (an LLM call, a tool call)
becomes a well-defined event — `{step, type, input, output, duration_ms,
timestamp}` — saved to disk as JSON, plus a small viewer to read it back.

## What's new since Module 3

| Module 3 | Module 9 |
|---|---|
| Loosely-formatted `print()` statements | Structured event dicts via the `Tracer` class |
| Nothing persisted | `tracer.save()` writes a full JSON trace to disk |
| No way to review a past run | `print_trace_summary()` — a readable timeline from a saved trace file |
| LLM calls and tool calls not distinguished in logs | Each traced as a separate `event_type` ("llm_call" vs "tool_call") |

## Why separate LLM-call and tool-call events

Keeping them as distinct trace events lets you later ask precise
questions like "was the slowness in this run caused by the LLM or by a
slow tool?" — something loose print statements can't answer after the
fact.

## Key takeaway

> A trace is a debugging artifact you can revisit **after** a run ends —
> e.g. after a user reports "the agent gave a weird answer" and you need
> to reconstruct exactly what happened, in what order, and how long each
> step took.

## Run it

From the project root:

```bash
python module09/module09_observability.py
```

This produces `agent_trace.json` in the `module09` directory, then
immediately loads and prints it via `print_trace_summary()`.

## Things to try

- Open the generated `agent_trace.json` directly and look at its
  structure — try writing a one-line filter like
  `[e for e in trace if e["type"] == "tool_call" and e["duration_ms"] > 500]`.
- Deliberately trigger a tool error and see `is_error: true` appear in
  that event, with an `[ERR]` marker in the printed summary.
- Run the script twice with different tasks and compare the two saved
  trace files side by side.
