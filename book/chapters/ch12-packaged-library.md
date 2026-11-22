# Chapter 12. Packaging a Reusable Library — From Scripts to `import`

## What You'll Learn

- How Python packages, modules, and `import` work, just enough to read a small library
- How the core loop from Chapters 1–3 becomes an `Agent` class with a small public interface
- Three concerns that appear once code is reused: **cost tracking, caching, and
  prompt versioning**, and a surprising way caching can go wrong

| You'll need | |
|---|---|
| Previous chapter | Chapters 1–3 (the loop, tools, and registry). Chapter 10 helps with the "why" of prompt versions |
| Code | `module12/agent_harness/` (7 files) and `module12/example_usage.py` |
| Environment | The virtual environment activated, with `ollama serve` running |

---

## 12.1 The Problem: Copy, Paste, Drift

Look back at the modules you've read. Every one starts with the same lines:
`BASE_URL`, `API_KEY`, `MODEL`, `LLM_OPTIONS`, `client = OpenAI(...)`. Most of
them redefine the same `@tool` decorator, the same `calculate`, the same
`search_web`, and their own slightly different `execute_tool_call()`.

That's fine for teaching, because each file stands alone. It's a problem for
real projects:

- **Changing providers means editing every file.**
- **The copies drift apart.** You've seen it: Chapter 3 wrapped `json.loads()`
  in a `try`, and Chapters 10 and 11 didn't. A fix made in one copy doesn't
  reach the others.
- **A new project starts by copying a script**, along with every quirk in it.

The fix is a **library**: one copy of the core, which any project can `import`.

---

## 12.2 Bridge: Packages, Modules, and `import`

If you haven't built a Python package before, here's what you need for this chapter.

**A module is a `.py` file.** `cost.py` is a module named `cost`.

**A package is a folder of modules with an `__init__.py` file.** The
`agent_harness/` folder is a package. When you write `import agent_harness`,
Python runs `agent_harness/__init__.py`.

**`from .cost import CostTracker`** (with a leading dot) means "from the
`cost` module *in this same package*." It's a *relative import*, used inside
a package to refer to its own modules.

**`__init__.py` decides what the package offers.** Here's the whole public
interface of our library:

```python
# module12/agent_harness/__init__.py:21-33
from .config import get_client, MODEL
from .tools import tool, TOOL_REGISTRY, TOOLS_SCHEMA
from .prompts import PromptRegistry
from .cost import CostTracker
from .cache import SimpleCache
from .loop import Agent

__all__ = [
    "get_client", "MODEL",
    "tool", "TOOL_REGISTRY", "TOOLS_SCHEMA",
    "PromptRegistry", "CostTracker", "SimpleCache",
    "Agent",
]
```

Because of these imports, a user can write `from agent_harness import Agent, tool`
without knowing which file each one lives in. `__all__` lists the names the
package considers public.

**How does Python find `agent_harness`?** It searches a list of folders, and
the first one is the folder containing the script you ran. Running
`python module12/example_usage.py` puts `module12/` on that list, and
`agent_harness/` is inside it. (To use the library from anywhere, you'd
install it as a package, which is beyond this chapter.)

**A class bundles state with the functions that use it.** Until now, each
module's loop was a function, and its settings were global constants. An
`Agent` class lets you create several agents, each with its own prompt, tools,
cost counter, and cache, living side by side in one program. That's what
Chapter 11 needed, written by hand.

---

## 12.3 The Big Idea: A Small, Stable Core

The package is deliberately **small**. Here's the layout:

```text
agent_harness/
  __init__.py    # the public interface
  config.py      # BASE_URL / API_KEY / MODEL, in one place
  tools.py       # the @tool decorator, the registry, execute_tool_call()
  prompts.py     # PromptRegistry: versioned system prompts
  cost.py        # CostTracker: token usage → estimated cost
  cache.py       # SimpleCache: skip identical model calls
  loop.py        # the Agent class: the loop, with cost and cache wired in
```

What's **not** in it is just as deliberate: compression (4), persistent
memory (5), planning (6), reflection (7), concurrency (8), confirmation gates
(9), tracing (10), and multi-agent orchestration (11). Those are policies and
workflows you add *around* the core when a project needs them. A core that
absorbs every feature becomes hard to understand and hard to change, which
defeats the point of a library.

Think of it like a kitchen's basic equipment. Every restaurant needs a stove,
knives, and a fridge. Not every restaurant needs a pizza oven. You buy the
basics once and add specialty equipment to suit the menu.

---

## 12.4 Walking Through the Code

### Configuration, once

```python
# module12/agent_harness/config.py:15-21 (comments omitted)
BASE_URL = "http://localhost:11434/v1"   # e.g. "https://api.openai.com/v1" for real OpenAI
API_KEY = "ollama"                        # e.g. your real OpenAI key
MODEL = "gemma4:e4b"                       # e.g. "gpt-4o-mini"

LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}
```

```python
# module12/agent_harness/config.py:31-43 (docstring omitted)
_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    return _client
```

Switching providers is now one edit in one file. `get_client()` creates the
client the first time it's asked and returns the same one after that, so all
agents share a single connection pool. (The leading underscore in `_client`
is a Python convention for "internal; don't use this directly.")

### Tools, once

`tools.py` holds Chapter 3's `@tool` decorator (with Chapter 9's `dangerous`
flag kept as a label, though nothing enforces it here), the two example
tools, and Chapter 3's error handling:

```python
# module12/agent_harness/tools.py:64-86 (docstring and comments omitted)
def execute_tool_call(tool_name: str, arguments_json: str,
                      registry: dict = None) -> str:
    active_registry = registry if registry is not None else TOOL_REGISTRY
    tool_fn = active_registry.get(tool_name)
    if tool_fn is None:
        return f"ERROR: unknown tool '{tool_name}'. Available: {list(active_registry.keys())}"
    try:
        tool_args = json.loads(arguments_json)
    except json.JSONDecodeError as e:
        return f"ERROR: could not parse arguments as JSON: {e}"
    try:
        return str(tool_fn(**tool_args))
    except Exception as e:
        return f"ERROR: tool '{tool_name}' raised an exception: {e}"
```

One new detail: the `registry` argument. Each `Agent` can have its own set of
tools, so execution has to look tools up in *that agent's* registry, not
always the global one. Otherwise an agent could run a tool it was never offered.

### The `Agent` class

```python
# module12/agent_harness/loop.py:28-39 (comments omitted)
def __init__(self, system_prompt: str, tools_schema: list = None,
             tool_registry: dict = None, max_turns: int = 8,
             use_cache: bool = True):
    self.system_prompt = system_prompt
    self.tools_schema = tools_schema if tools_schema is not None else TOOLS_SCHEMA
    self.tool_registry = tool_registry if tool_registry is not None else TOOL_REGISTRY
    self.max_turns = max_turns
    self.client = get_client()
    self.cost = CostTracker()
    self.cache = SimpleCache() if use_cache else None
```

Every setting that used to be a global constant is now a constructor argument
with a sensible default. Each agent gets its **own** `CostTracker` and
`SimpleCache`, so their numbers don't mix.

`run()` is the Chapter 3 loop you know, using `self.` settings. The new part is
the one place where the model is called:

```python
# module12/agent_harness/loop.py:41-60 (docstring omitted)
def _call_llm(self, messages: list):
    if self.cache is not None:
        cached = self.cache.get(MODEL, messages, self.tools_schema)
        if cached is not None:
            print("    [CACHE] hit -- reusing previous response, no API call made.")
            return cached

    response = self.client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=self.tools_schema if self.tools_schema else None,
        **LLM_OPTIONS,
    )
    self.cost.record(response.usage)

    if self.cache is not None:
        self.cache.set(MODEL, messages, self.tools_schema, response)

    return response
```

Check the cache; if it's a miss, call the model, record the cost, store the
response. Because every model call goes through this one method, cost and
caching apply everywhere automatically. That's a big advantage of a library:
a cross-cutting concern lives in one place.

### Cost tracking

```python
# module12/agent_harness/cost.py:22-42 (docstring and comments omitted)
def record(self, usage):
    self.call_count += 1
    if usage is None:
        return
    self.total_input_tokens += getattr(usage, "prompt_tokens", 0) or 0
    self.total_output_tokens += getattr(usage, "completion_tokens", 0) or 0

@property
def estimated_cost_usd(self) -> float:
    input_cost = (self.total_input_tokens / 1000) * PRICE_PER_1K_TOKENS["input"]
    output_cost = (self.total_output_tokens / 1000) * PRICE_PER_1K_TOKENS["output"]
    return round(input_cost + output_cost, 6)
```

Every API response includes a `usage` field reporting how many tokens went in
(`prompt_tokens`) and came out (`completion_tokens`). Paid providers bill by
those numbers, usually at different rates for input and output. The tracker
adds them up and multiplies by `PRICE_PER_1K_TOKENS` from `config.py`.

Those prices are **placeholders**. Real prices vary by provider and model and
change over time, so check your provider's pricing page. With a local Ollama
model, the dollar cost is actually zero, but the token counts are still real
and still worth watching: tokens are what make requests slow.

`@property` lets you read `tracker.estimated_cost_usd` like a variable, while
it's actually computed fresh each time.

### Caching

```python
# module12/agent_harness/cache.py:43-47 (inside _make_key)
payload = json.dumps(
    {"model": model, "messages": [to_plain(m) for m in messages], "tools": tools},
    sort_keys=True,
)
return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

The cache key is a **hash** of the whole request: model, messages, and tools.
A hash function turns any input into a fixed-length fingerprint; identical
input always gives the identical fingerprint. `sort_keys=True` makes sure two
dictionaries with the same contents in a different order produce the same JSON,
and so the same key. If the exact same request comes in again, the stored
response is returned and no model call is made.

### Prompt versions

```python
# module12/agent_harness/prompts.py:28-39 (docstring omitted)
def register(self, name: str, version: str, text: str, activate: bool = True):
    self._prompts.setdefault(name, {})[version] = text
    if activate or name not in self._active_version:
        self._active_version[name] = version

def get(self, name: str, version: str = None) -> tuple:
    version = version or self._active_version[name]
    return self._prompts[name][version], version
```

Prompts change. You reword a sentence to fix one behavior and break another.
`PromptRegistry` keeps every version under a name, tracks which one is active,
and, importantly, `get()` returns **the text and its version together**. That
makes it natural to record "this run used `general_assistant` v2" alongside
a trace (Chapter 10), so when behavior changes, you can tell whether the prompt did.

---

## 12.5 Running It

```bash
python module12/example_usage.py
```

`example_usage.py` is written the way a new project would use the library: it
imports `Agent` and `tool`, registers one new tool of its own
(`celsius_to_fahrenheit`), fetches a versioned prompt, and runs.

```text
Using prompt 'general_assistant' version=v2
USER TASK: Convert 100 Celsius to Fahrenheit, then calculate half of that result.

[Agent] turn 1: sending 2 messages...
[Agent] turn 1: calling tool 'celsius_to_fahrenheit'
[Agent] turn 2: sending 4 messages...
[Agent] turn 2: calling tool 'calculate'
[Agent] turn 3: sending 6 messages...
[Agent] turn 3: final answer produced.

FINAL ANSWER:
The conversion of 100 Celsius to Fahrenheit is 212 degrees. Half of that result is 106.0.

[STATS] 3 LLM call(s), 844 input + 68 output tokens, ~$0.000167 estimated cost | 0 hit(s), 3 miss(es) (0% hit rate)
```

> Run on 2026-11-20 with Ollama `gemma4:e4b`, `openai` 3.57.0, Python 3.14.
> Model output can differ from run to run.

The new tool was picked up with no changes to the library, and the agent used
it alongside the built-in `calculate`. The `[STATS]` line is the payoff: three
model calls, 912 tokens, and an (illustrative) cost, from one method call.
No cache hits, because every request in a single run is different.

---

## 12.6 Experiments: Caching and the Shared Registry

To see the cache, you have to send the same request twice, so we ran the same
task twice on the same `Agent`.

### Caching a mistake

```text
[Agent] turn 1: sending 2 messages...
[Agent] turn 1: calling tool 'calculate'
[Agent] turn 2: sending 4 messages...
[Agent] turn 2: final answer produced.
RUN 1: 1.53s => <|tool_response>
  [STATS] 2 LLM call(s), 410 input + 25 output tokens, ~$0.000076 estimated cost | 0 hit(s), 2 miss(es) (0% hit rate)
[Agent] turn 1: sending 2 messages...
    [CACHE] hit -- reusing previous response, no API call made.
[Agent] turn 1: calling tool 'calculate'
[Agent] turn 2: sending 4 messages...
    [CACHE] hit -- reusing previous response, no API call made.
[Agent] turn 2: final answer produced.
RUN 2: 0.00s => <|tool_response>
  [STATS] 2 LLM call(s), 410 input + 25 output tokens, ~$0.000076 estimated cost | 2 hit(s), 2 miss(es) (50% hit rate)
```

The task was "What is 384712 \* 9931?" The cache worked perfectly: run 2 took
**0.00 seconds** and made no model calls. The call count and token totals
didn't move.

But look at the answer. Both runs returned `<|tool_response>`, the leaked
chat-format fragment we first met in Chapter 6. The calculator ran and got the
right number, and the model's final message was garbage. **The cache saved that
garbage and served it again, instantly and for free.**

A cache doesn't know good responses from bad ones. It stores whatever it gets.
That has two consequences:

- **Validate before you cache.** A response that's empty, or starts with `<|`,
  shouldn't be stored.
- **Caching freezes randomness.** Model output varies from run to run.
  Normally, a retry might succeed where the first attempt failed. With a cache,
  a retry of the same request gets the same failure forever, at least until the
  program restarts.

### When a tool result changes

We registered a `now()` tool that returns the current time, and asked "What
time is it right now?" twice:

```text
[Agent] turn 1: sending 2 messages...
[Agent] turn 1: calling tool 'now'
[Agent] turn 2: sending 4 messages...
[Agent] turn 2: final answer produced.
TIME RUN 1: 1.82s => The current time is 20:16:55 on November 20, 2026.
[Agent] turn 1: sending 2 messages...
    [CACHE] hit -- reusing previous response, no API call made.
[Agent] turn 1: calling tool 'now'
[Agent] turn 2: sending 4 messages...
[Agent] turn 2: final answer produced.
TIME RUN 2: 0.64s => The current time is 20:16:56.
```

The first model call ("call the `now` tool") was a cache hit, since the request
was identical. But **the tool itself ran again**. Only model responses are
cached, not tool results. It returned a new time, so the second request was
different from last time, the cache missed, and the model saw the fresh time.
The answer was correct.

That's the cache key doing its job: anything that changes the request changes
the key. It's also a reminder that tools still run on a cache hit. If a cached
response asks for `send_email`, the email gets sent again.

### The shared registry

After registering `now()`, we created a brand-new agent and listed its tools:

```text
tools visible to a NEW default agent: ['calculate', 'search_web', 'now']
```

`@tool` registers into **one global registry**, and `Agent()` uses that
registry by default. So a tool defined anywhere in your program, even in a file
you didn't write, becomes available to every agent that didn't specify its own
tools. And because the agent keeps a reference to the same global *list*
rather than a copy, tools registered after an agent is created show up in it too.

That's convenient for a quick script and risky in a larger program, especially
combined with Chapter 9's lesson that the harness decides what an agent can do.
For anything important, pass `tools_schema` and `tool_registry` explicitly
(Exercise 3).

---

## 12.7 Common Problems

**`ModuleNotFoundError: No module named 'agent_harness'`.**
Python didn't find the package. Run the script as
`python module12/example_usage.py` from the repository's top-level folder, so
`module12/` (the script's folder) is on Python's search path.

**The cost is never zero, but I'm using Ollama.**
The prices in `config.py` are placeholders applied to any provider. The token
counts are real; the dollar amount isn't, for a local model.

**The second run returns the same wrong answer instantly.**
The cache stored the bad response. See "Caching a mistake." Pass
`use_cache=False` while debugging.

**An agent can use a tool I never gave it.**
It's using the global registry. Pass an explicit `tools_schema` and
`tool_registry` (Exercise 3).

**`[CACHE] hit` never appears.**
Each run creates a new `Agent`, and each agent has its own empty cache. The
cache also disappears when the program exits.

---

## 12.8 Try It Yourself

1. **Run it twice** (easy) — In `example_usage.py`, call `agent.run(task)` a
   second time on the same agent. How long does it take, and what does
   `agent.stats()` say?
2. **A new prompt version** (easy) — Register a `"v3"` of `general_assistant`
   that asks for one-sentence answers, set it active with
   `default_registry.set_active(...)`, and run the example. Does the printed
   version change?
3. **A private toolset** (medium) — Create an agent that can *only* use
   `calculate`:
   ```python
   from agent_harness.tools import calculate
   schema = [s for s in TOOLS_SCHEMA if s["function"]["name"] == "calculate"]
   math_agent = Agent(system_prompt="...", tools_schema=schema,
                      tool_registry={"calculate": calculate})
   ```
   Ask it to search the web. What happens?
4. **Don't cache garbage** (medium) — Change `_call_llm()` so it only stores a
   response if it has tool calls or non-empty text that doesn't start with
   `<|`. Repeat the "Caching a mistake" experiment.
5. **Compose a feature** (challenge) — Add Chapter 7's circuit breaker *around*
   the library without editing `loop.py`: write your own function that wraps
   tools with a failure counter before passing them in a custom `tool_registry`.
   What does this tell you about keeping the core small?

---

## 12.9 Recap

> **A library is one shared copy of the core, with a small interface. Keep the
> core small, and put cross-cutting concerns like cost and caching in the one
> place every call passes through.**

- `agent_harness/` packages config, tools, the loop, cost tracking, caching,
  and prompt versions behind `from agent_harness import Agent, tool`.
- Each `Agent` has its own prompt, tools, cost tracker, and cache.
- In our runs, the cache made a repeat run instant, and also served a broken
  answer a second time. Tools still run on a cache hit.
- `@tool` registers globally, so default agents share every tool. Pass explicit
  tools when it matters.

**In the next chapter**, tools leave our process entirely. With the Model
Context Protocol (MCP), the agent discovers tools that live in a separate server
and calls them over a standard interface.

---

## Solutions and Hints

Solutions to this chapter's exercises are in [Appendix D](../appendices/appendix-d-solutions.md#chapter-12-packaging-a-reusable-library).
