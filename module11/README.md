# Module 11: Practical Deployment — Packaging a Reusable Library

**Files:** `agent_harness/` (package) + `example_usage.py`
**Builds on:** The core loop and tool registry from Modules 1-3

## Concept

Every module so far was a standalone script. This final module packages
the core tool-calling loop, tool registry, and tool-error handling into a
small, **reusable library**. It also introduces three concerns that become
important when the same core is reused by multiple applications:

1. **Cost monitoring** — when an API response includes token usage,
   `CostTracker` accumulates it into an estimated running dollar cost. It
   still counts calls from providers that omit usage metadata.
2. **Caching** — identical requests (same model + messages + tools) are
   served from an in-memory cache instead of paying for/waiting on a
   duplicate LLM call.
3. **Prompt versioning** — system prompts are registered with explicit
   version tags, so an application can record exactly which prompt version
   produced a run.

This package intentionally contains a **minimal core**, not every feature
from the course. Memory compression, planning, reflection/retries, human
confirmation, tracing, and multi-agent orchestration remain in Modules
4-10 as patterns you can compose around this Agent. Keeping that boundary
visible is part of the packaging lesson: a reusable core does not need to
absorb every policy and workflow.

## Package layout

```
agent_harness/
  __init__.py    # public API: Agent, tool, get_client, etc.
  config.py      # BASE_URL / API_KEY / MODEL in ONE place (Ollama <-> OpenAI switch point)
  tools.py       # the @tool decorator + registry (Module 3's pattern, packaged)
  prompts.py     # PromptRegistry — versioned system prompts
  cost.py        # CostTracker — token usage -> estimated cost
  cache.py       # SimpleCache — hash-keyed response cache
  loop.py        # the Agent class — the core loop, with caching + cost wired in
example_usage.py # a new project's-eye view of using the packaged core
```

## What's new in the packaging step

| Before | Module 11 |
|---|---|
| Config constants copy-pasted at the top of every script | `config.py` — one place to switch providers for the whole project |
| Tool registry re-declared per script | `tools.py` — shared, importable registry |
| String constants for system prompts | `prompts.py` — `PromptRegistry` with explicit versions |
| No cost visibility | `cost.py` — `CostTracker`, summarized via `agent.stats()` |
| No caching | `cache.py` — `SimpleCache`, hit/miss rate reported via `agent.stats()` |
| A single `run_agent_loop()` function per script | `Agent` class — instantiable, multiple independent agents can coexist |

## Using it

```python
from agent_harness import Agent, tool

@tool(description="...", parameters={...}, required=[...])
def my_tool(...):
    ...

agent = Agent(system_prompt="You are a helpful assistant.")
answer = agent.run("do something")
print(agent.stats())   # cost + cache summary
```

Compare this to Module 1's ~100 lines just to get a basic loop running —
this is the payoff of building everything incrementally: the core library
is small and clean specifically because every piece in it was
already understood, module by module.

## Key takeaway

> Packaging isn't just "moving code into files" — it's making the
> non-functional concerns (cost, caching, prompt versioning) first-class
> parts of the interface, so every future project using this library gets
> them automatically instead of everyone re-inventing them per script.

## Run it

From the project root:

```bash
python module11/example_usage.py
```

## Things to try

- In `example_usage.py`, call `agent.run(task)` a second time with the same
  Agent instance and task. The second call produces `[CACHE] hit` messages
  because `SimpleCache` lives in that process. Running the script as a new
  process starts with an empty cache again.
- Register a new prompt version in `prompts.py` via
  `default_registry.register(...)` and switch to it with
  `default_registry.set_active(...)` — confirm the printed version tag
  changes accordingly.
- Instantiate two `Agent`s with different system prompts and tool subsets
  (echoing Module 10's researcher/writer split) and compare their
  `agent.stats()` independently.
- Swap `SimpleCache`'s in-memory dict for a real persistent store (e.g.
  Redis) as a production-hardening exercise — the interface (`get`/`set`)
  is designed to make that swap straightforward.

---

This is the final implementation module of the course. You've gone from a
1-turn LLM call (Module 0), through memory, planning, recovery, guardrails,
observability, and orchestration patterns, to packaging the reusable core.
The earlier modules show how to compose their advanced policies and
workflows around that core when a project needs them.
