# Module 5: Planning & Task Decomposition

**File:** `module05_planning.py`
**Builds on:** Module 4 (uses the same tool registry pattern from Module 3)

## Concept

So far, the agent has handled tasks reactively, turn by turn, with no
explicit "here's my overall plan" step. For complex, multi-part tasks this
can wander or lose the big picture. This module introduces the
**plan-then-execute** pattern:

1. **Plan** — ask the LLM to decompose the task into an ordered list of
   concrete subtasks, returned as structured JSON.
2. **Execute** — run each subtask through its own small tool-calling loop,
   one at a time, collecting results.
3. **Synthesize** — combine all subtask results into one coherent final
   answer.

## What's new since Module 4

| Module 4 | Module 5 |
|---|---|
| One long-running conversation, compressed over time | Each subtask gets its own short, independent conversation |
| Memory managed by **compression** | Memory managed by **isolation** — subtasks don't share context at all |
| Reactive, turn-by-turn behavior | An explicit up-front plan drives execution |

## Structured output for planning

`generate_plan()` asks the model to respond with **only a JSON array of
strings** — no prose, no markdown. This is more reliable to parse than
free text, though the code still defensively handles models that wrap the
JSON in code fences, and falls back to a single-subtask plan if parsing
fails entirely (a broken plan should never crash the whole task).

## Key takeaway

> "Isolation" and "compression" (Module 4) are two different answers to
> the same problem: keeping context manageable. Isolation works well when
> subtasks are genuinely independent; compression works better when one
> continuous thread of reasoning needs to span many turns.

## Run it

From the project root:

```bash
python module05/module05_planning.py
```

Watch the `[PLAN]`, `[EXECUTE N]`, and `[SYNTHESIZE]` log sections — they
correspond directly to the three-step pattern above.

## Things to try

- Print the raw plan JSON before parsing to see exactly what the model
  produced.
- Feed in a single-step task and observe the plan collapses to one
  subtask — the pattern still works, just with less to do.
- Force a JSON parse failure (e.g. by tweaking the planning prompt to
  encourage prose) and confirm the fallback to a single-subtask plan kicks
  in instead of crashing.
