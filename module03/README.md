# Module 3: Tool Registry & Multiple Tools

**File:** `module03_tool_registry.py`
**Builds on:** Module 2

## Concept

Module 2 hardcoded exactly one tool. Real agents need many. This module
introduces a **registry pattern**: a `@tool(...)` decorator that
registers a function's schema and implementation together, in one place,
so adding tool #10 later never requires touching existing code.

We also add three new tools and harden error handling around all of them.

## What's new since Module 2

| Module 2 | Module 3 |
|---|---|
| Manually-written `TOOLS_SCHEMA` list + `TOOL_REGISTRY` dict | `@tool(...)` decorator populates both automatically |
| 1 tool (`calculate`) | 3 tools: `calculate`, `search_web` (stub), `read_file` (real I/O) |
| Basic try/except per tool call | `execute_tool_call()` — a single function covering 3 distinct failure modes |

## The three failure modes handled

1. **Unknown tool** — the model hallucinated a tool name that isn't
   registered.
2. **Bad arguments** — the JSON doesn't parse, or required arguments are
   missing/wrong type.
3. **Tool exception** — the tool ran but raised (e.g. `read_file` on a
   path that doesn't exist).

All three become an `"ERROR: ..."` string returned to the model — nothing
ever raises up and crashes the agent loop.

## Key takeaway

> A tool registry decouples "what tools exist" from "how the loop calls
> them." As your toolset grows from 1 to 50 tools, the loop code doesn't
> change at all — only new `@tool`-decorated functions get added.

`search_web` in this module is a **stub** — it returns a fake canned
string so you can see the tool-calling mechanics work end-to-end without
needing a real search API key. Swap in a real search provider (Tavily,
Bing Search API, SerpAPI, etc.) for production use.

## Run it

From the project root:

```bash
python module03/module03_tool_registry.py
```

## Things to try

- Add a fourth tool of your own using `@tool(...)` and confirm the model
  starts using it without any other code changes.
- Deliberately trigger each of the 3 failure modes (ask for a nonexistent
  file, a tool that doesn't exist, malformed arguments) and watch the
  error strings flow back into the conversation instead of crashing.
- Replace the `search_web` stub with a real API call and observe the rest
  of the harness needs zero changes.
