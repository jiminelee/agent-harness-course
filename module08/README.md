# Module 8: Guardrails & Safety

**File:** `module08_guardrails.py`
**Builds on:** Module 6's error-handling patterns

## Concept

Until now, any tool the model requested was executed immediately and
automatically. That's fine for read-only tools (`calculate`,
`search_web`), but dangerous for tools that **modify** something (delete a
file, send an email, spend money). This module adds three concrete safety
layers:

1. **Human-in-the-loop confirmation** — tools marked `dangerous=True`
   pause the loop and require an explicit human "yes" (via terminal input)
   before running. The model cannot bypass this.
2. **Input validation** — arguments are validated strictly *before*
   confirmation or execution (rejecting suspicious paths, oversized
   inputs, etc.) — never trust model-generated arguments blindly.
3. **Audit logging** — every dangerous-action attempt (approved, denied,
   or rejected by validation) is recorded with a timestamp, regardless of
   the outcome.

## What's new since Module 6

| Module 6 | Module 8 |
|---|---|
| No distinction between tool risk levels | `dangerous=True` flag on the `@tool` decorator |
| No human approval step | `request_human_confirmation()` — blocks on real terminal input |
| No input sanitization | `validate_tool_args()` — checked before confirmation/execution |
| No persistent record of sensitive actions | `AUDIT_LOG` + `audit()` — every attempt recorded |

## The new tool: `delete_file`

Marked `dangerous=True`, this tool demonstrates the full gate: validation
first (rejecting path traversal / absolute paths), then human confirmation
second, then execution only if both pass.

## Key takeaway

> Guardrails live in the **harness**, not in the prompt. The model doesn't
> need to know a tool is "dangerous" — the code enforces the gate
> regardless of what the model says or how convincingly it argues for
> running the action.

## Run it

From the project root:

```bash
python module08/module08_guardrails.py
```

This script actually pauses for real `y/N` terminal input when the model
requests `delete_file` — run it interactively to see the full flow,
including what happens when you type `n`.

## Things to try

- Type `n` at the confirmation prompt and observe the `DENIED` message
  flow back to the model, and how it responds to being refused.
- Add a second dangerous tool of your own (e.g. `send_email`) and confirm
  it automatically gets the confirmation gate just by setting
  `dangerous=True`.
- Print `AUDIT_LOG` at the end of a run where you deny an action, and
  confirm the denial is recorded even though nothing was actually
  executed.
