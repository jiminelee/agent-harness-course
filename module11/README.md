# Module 11: Multi-Agent & Orchestration

**File:** `module11_multi_agent.py`
**Builds on:** Module 3's tool-calling loop shape

## Concept

Module 6 decomposed a task into subtasks, but one agent (fixed toolset,
fixed persona) executed all of them. This module introduces genuinely
different **specialist sub-agents** — a researcher (with real tools) and
a writer (no tools, pure prose) — coordinated by an orchestrator.

The pattern used: **sub-agents as tools**. Each sub-agent is wrapped in a
plain Python function (`delegate_to_researcher`, `delegate_to_writer`)
that *looks like a tool* to the orchestrator LLM. When the orchestrator
"calls" one, a **complete, independent agent loop** runs internally (with
its own system prompt, tools, and turn limit), and its final answer comes
back as the "tool result."

## What's new since Module 3/6

| Module 3/6 | Module 11 |
|---|---|
| One toolset, one persona for the whole run | Multiple personas (`RESEARCHER_SYSTEM_PROMPT`, `WRITER_SYSTEM_PROMPT`), each with their own tools |
| Subtasks executed by the *same* kind of agent | Subtasks routed to genuinely *different* specialist agents |
| `run_tool_calling_loop()` used once | The same generic loop function reused for 3 different agents (researcher, writer, orchestrator) |

## Why this is elegant

From the orchestrator's point of view, delegating to a sub-agent looks
**exactly like calling a tool in Module 3** — it has no idea
`delegate_to_researcher` secretly runs a whole multi-turn agent loop
underneath. All the multi-agent complexity is hidden behind an ordinary
function call, so no new "multi-agent-specific" code is needed in the
orchestrator's loop at all.

## Key takeaway

> A "multi-agent system" is often just: one agent, whose tools happen to
> be other complete agents. The generic tool-calling loop we built in
> Module 3 already supports this — you don't need a different mechanism,
> just a different kind of "tool."

## Run it

From the project root:

```bash
python module11/module11_multi_agent.py
```

Watch the indented `[RESEARCHER | turn N]` and `[WRITER | turn N]` log
lines nested inside the `[ORCHESTRATOR]` run — this nesting is the
multi-agent hierarchy made visible.

## Things to try

- Add a third specialist (e.g. a "fact-checker" agent) and wire it in as
  another `delegate_to_...` tool for the orchestrator.
- Give the researcher and writer agents different models (e.g. a cheaper
  model for research, a stronger one for writing) — since each sub-agent
  loop is independent, this requires no structural changes.
- Combine this with Module 10's tracing: wrap each sub-agent's
  `run_tool_calling_loop()` call in its own `Tracer` to get separate,
  attributable traces per specialist.
