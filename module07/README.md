# Module 7: Error Recovery & Self-Correction

**File:** `module07_error_recovery.py`
**Builds on:** Module 3's tool registry pattern

## Concept

Previously, tool errors were just fed back to the model with no limit —
a confused model could retry the same failing call over and over (up to
`MAX_TURNS`). This module adds two real quality/safety mechanisms:

1. **Retry limiting** — track how many times each tool has failed
   **consecutively**. After a small limit, short-circuit further attempts
   at that tool instead of calling it again.
2. **Reflection (self-correction)** — once the model produces what it
   thinks is a final answer, a **separate critic LLM call** checks it
   against the original task. If the critic finds a problem, the
   critique is fed back as a revision request, for a bounded number of
   rounds.

## What's new since Module 3

| Module 3 | Module 7 |
|---|---|
| Errors fed back with no tracking | `FailureTracker` counts consecutive failures per tool |
| No verification of the final answer | `critique_answer()` — an independent LLM call judges pass/fail |
| Loop stops as soon as no tool call is requested | Loop only truly stops after the critic passes it (or rounds run out) |

## Why the critic is a *separate* call

If the same model, in the same context, critiques its own just-generated
answer, it tends to just agree with itself. `critique_answer()` uses a
fresh, isolated call with only the task and the proposed answer — no
memory of *how* the answer was produced — to get an honest second look.

## Key takeaway

> Real agents fail in two different places: at the **tool level** (an
> action didn't work) and at the **answer level** (all actions "worked"
> but the final synthesis is wrong or incomplete). This module handles
> both, with two different mechanisms.

## Run it

From the project root:

```bash
python module07/module07_error_recovery.py
```

The example task uses an intentionally malformed expression (`'5 +'`) so
you can watch the calculator tool fail, retry, fail again, and then get
short-circuited by `FailureTracker` before a third attempt.

## Things to try

- Lower `MAX_CONSECUTIVE_TOOL_FAILURES` to 1 and watch the short-circuit
  trigger immediately after one failure.
- Feed in a task with a subtly wrong or incomplete answer and watch the
  `[REFLECT]` critique catch it and trigger a revision round.
- Set `MAX_REFLECTION_ROUNDS` to 0 and confirm the agent returns its first
  answer without any self-checking — useful for comparing behavior with
  and without reflection.
