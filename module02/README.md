# Module 2: Your First Tool

**File:** `module02_first_tool.py`
**Builds on:** Module 1

## Concept

This module introduces **function/tool calling** — the mechanism that
lets an LLM actually *do* things instead of only producing text. We add
exactly one tool: a calculator.

Instead of parsing a text marker (Module 1's approach), we now describe a
tool to the model using a JSON schema. The model can request to call it,
and the API returns a structured `tool_calls` field instead of free text.

## What's new since Module 1

| Module 1 | Module 2 |
|---|---|
| No tools, text marker for "done" | One real tool (`calculate`), JSON-schema described |
| Manual text parsing (`DONE_MARKER`) | Structured `message.tool_calls` from the API |
| No way to actually run code | `calculate()` runs a real Python `eval()` |
| Loop stops on marker text | Loop stops when `message.tool_calls` is empty (no tool requested = final answer) |

## How the loop changed shape

```
1. Send messages (with tools= schema) to the LLM.
2. If the LLM requests a tool call:
     - Run the real Python function.
     - Append a role="tool" message with the result.
     - Go back to step 1.
3. If the LLM gives a normal text answer (no tool call):
     - That's the final answer. Stop.
```

This "no tool call = done" convention is standard across OpenAI-compatible
tool-calling APIs, and it's simpler and more reliable than Module 1's text
marker.

## Key takeaway

> Tool calling turns "the model describes what it wants to do" into "the
> model requests a specific, executable action with structured arguments."
> Your code executes the action and feeds the *result* back in — the
> model never runs code itself, it only asks your harness to.

## Run it

From the project root:

```bash
python module02/module02_first_tool.py
```

Watch for lines like:
```
-> Calling tool 'calculate' with args: {'expression': '...'}
<- Tool result: ...
```

## Things to try

- Give the model an arithmetic task complex enough that it clearly can't
  do it reliably in its head (e.g. large multiplication) and confirm it
  reaches for the tool instead of guessing.
- Try removing the `tools=TOOLS_SCHEMA` argument from the API call and see
  the model fall back to guessing — this shows the tools parameter is
  what makes tool calling possible at all.
- Deliberately pass a malformed expression and see how the tool's
  exception is turned into an error string fed back to the model (a
  preview of Module 3's more general error handling).
