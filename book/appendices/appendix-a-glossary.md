# Appendix A. Glossary

Terms are listed alphabetically. The chapter in parentheses is where the term
is first explained in detail.

---

**Agent** (Before You Begin) — A program that works toward a task over several
steps, deciding what to do next, using tools, and reading the results, until it
decides it's done. The decisions come from a language model; everything else
comes from the harness.

**Allowlist** (Chapters 9, 13) — A list of things that are explicitly permitted,
with everything else refused. Safer than a *blocklist*, which tries to name
everything forbidden. Module 13's set of discovered tool names is an allowlist.

**Assistant message** (Chapter 1) — A message with `role: "assistant"`: something
the model said. It may contain text, tool calls, or both.

**`async` / `await`** (Chapter 8) — Python keywords for concurrent code. An
`async def` function returns a *coroutine*; `await` runs it and lets other
coroutines run while it waits.

**Atomic write** (Chapter 5) — Saving a file so that readers see either the
complete old version or the complete new version, never a half-written file.
Done by writing a temporary file and swapping it in with `os.replace()`.

**Audit log** (Chapter 9) — A permanent, timestamped record of every sensitive
action an agent attempted, whether it was approved, denied, or blocked.

**Cache** (Chapter 12) — Stored results of earlier requests, reused when an
identical request comes in. Module 12 caches model responses, keyed by a hash of
the request.

**Checkpoint** (Chapters 5, 14) — Saved execution state that lets an
interrupted task resume where it stopped. Not implemented in this book.

**Circuit breaker** (Chapter 7) — A mechanism that stops calling something after
it has failed several times in a row. Module 7's `FailureTracker` is one.

**Client (MCP)** (Chapter 13) — The part of a host application that talks to an
MCP server. In this book, the SDK's `Client` class.

**Concurrency** (Chapter 8) — Making progress on several tasks during the same
period, usually by switching to another task while one is waiting.

**Context** (Chapter 4) — Everything the model sees in one request: the system
prompt, the task, and any summary, messages, and tool results.

**Context window** (Chapter 4) — The maximum amount of text, measured in tokens,
that a model can read in one request.

**Coroutine** (Chapter 8) — The object created by calling an `async def`
function. It does nothing until it's awaited or passed to something like
`asyncio.gather`.

**Critic** (Chapter 7) — A separate model call that reviews a proposed answer
and returns a verdict, used to trigger revisions.

**Dataclass** (Chapter 4) — A Python class, marked with `@dataclass`, whose
`__init__` is generated automatically from its fields.

**Decorator** (Chapter 3) — A function that receives another function and
returns it, possibly changed or registered somewhere. Written with `@` above a
`def`. A *decorator factory* takes arguments and returns a decorator, like
`@tool(...)`.

**Golden dataset** (Chapter 14) — A collection of representative tasks with
known good outcomes, used to measure an agent's quality before changes ship.

**Harness** (Before You Begin) — The code around a language model that gives it
a conversation history, a loop, tools, and rules. The subject of this book.

**Hash** (Chapter 12) — A fixed-length fingerprint computed from any input.
Identical inputs always produce identical hashes. Module 12 uses SHA-256 to make
cache keys.

**Host (MCP)** (Chapter 13) — The application that runs the model and the agent
loop and connects to MCP servers to use their tools.

**Human in the loop** (Chapter 9) — A design where a person must approve certain
actions before they happen.

**Idempotency** (Chapter 14) — The property that doing something twice has the
same effect as doing it once. Important for retrying actions with side effects.

**JSON Lines** (Chapters 9, 10) — A file format with one JSON object per line.
Easy to append to and to read back one record at a time; common for logs.

**JSON Schema** (Chapter 2) — A standard way to describe the shape of JSON data.
Tool schemas use it to describe a tool's arguments.

**Loop** (Chapter 1) — The repeated cycle at the heart of an agent: send the
messages, read the reply, act on it, and repeat until done.

**MCP (Model Context Protocol)** (Chapter 13) — A standard for how applications
discover and call tools (and other capabilities) provided by separate programs.

**`MAX_TURNS`** (Chapter 1) — The hard limit on how many times the loop runs,
so a confused model can't run forever. Every module has one.

**Messages** (Before You Begin, Chapter 1) — The list of dictionaries, each with
a `role` and `content`, that makes up a conversation. The agent's only memory
within a run.

**Model** (Before You Begin) — Short for *large language model* (LLM): a program
that reads text and writes text. This book uses `gemma4:e4b` through Ollama.

**Module** (Chapter 12) — In Python, a single `.py` file. (In this book, also
one of the numbered folders, `module00/` through `module14/`.)

**Ollama** (Before You Begin) — A free program that runs language models on your
own computer and serves them through an OpenAI-compatible API.

**OpenAI-compatible** (Before You Begin) — Describes an API that accepts the same
request format as OpenAI's, so the `openai` package can talk to it by changing
`base_url`.

**Orchestrator** (Chapter 11) — An agent that coordinates other agents by
delegating work to them, here by calling them as tools.

**Package** (Chapter 12) — A folder of Python modules with an `__init__.py`
file, importable as a unit. `agent_harness/` is one.

**Path traversal** (Chapter 9) — Using `..` or absolute paths to reach files
outside the folder a program is supposed to stay in.

**Persistent memory** (Chapter 5) — Facts saved outside the program, here in a
JSON file, so they survive between runs.

**Plan → execute → synthesize** (Chapter 6) — A pattern where one model call
splits a task into subtasks, each subtask runs separately, and a final call
combines the results.

**Prompt** (Chapter 1) — The text given to a model. The *system prompt* is the
standing instructions in the `system` message.

**Prompt injection** (Chapters 5, 14) — Text that tries to give a model
instructions from somewhere other than the user, such as a file, a web page, or
a tool result.

**Prompt versioning** (Chapter 12) — Keeping every version of a prompt under a
name and a version tag, so you can tell which version produced a given run.

**Rate limit** (Chapter 8) — A provider's cap on how many requests you can make
in a period of time, or how many can be in flight at once.

**Registry** (Chapter 2) — A dictionary mapping tool names to the functions that
implement them.

**Role** (Before You Begin) — Who a message is from: `system`, `user`,
`assistant`, or `tool`.

**Sandbox** (Chapter 14) — An isolated environment that limits what code can
access, such as files, network, and memory.

**Schema** (Chapter 2) — See *tool schema* and *JSON Schema*.

**Semaphore** (Chapter 8) — A counter of permits that limits how many tasks can
run a section of code at the same time.

**Server (MCP)** (Chapter 13) — A program that offers tools through MCP. It has
no model and makes no decisions.

**Step** (Chapter 4) — One assistant message plus all the tool results it asked
for. Module 4 summarizes whole steps so requests and results stay together.

**stdio** (Chapter 13) — A program's standard input and output streams. Module
13's client and server exchange MCP messages over them.

**Structured output** (Chapter 6) — Asking the model to reply in a fixed format,
such as JSON, so code can read the reply reliably.

**Stub** (Chapter 3) — A placeholder implementation that returns fake data, like
this book's `search_web`.

**Sub-agent** (Chapter 11) — A complete agent that another agent uses as a tool.

**Summary** (Chapter 4) — A condensed version of older steps that replaces them
in the context. Always lossy.

**Synthesis** (Chapter 6) — The final step that combines subtask results into
one answer.

**Token** (Before You Begin) — The unit of text a model reads and writes. In
English, roughly four characters on average.

**Tool** (Chapter 2) — A function the harness lets the model ask for. The model
never runs it; the harness does.

**Tool call** (Chapter 2) — A structured request from the model to run a named
tool with specific arguments, found in `message.tool_calls`.

**`tool_call_id`** (Chapter 2) — The ID that pairs each tool result with the
tool call it answers.

**Tool result** (Chapter 2) — A message with `role: "tool"` containing a tool's
output, sent back to the model.

**Tool schema** (Chapter 2) — The description of a tool that the model reads:
its name, what it does, and its arguments as JSON Schema.

**Trace** (Chapter 10) — A structured, saved record of every model call and tool
call in a run, with inputs, outputs, and timings.

**Turn** (Chapter 1) — One pass through the agent loop: one model call and
whatever the harness does with the reply.

**Virtual environment** (Before You Begin) — A private set of Python packages for
one project, created with `python -m venv`.
