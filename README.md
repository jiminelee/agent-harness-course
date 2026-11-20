# Building an Agent Harness — A Hands-On Course

This course teaches you how an "AI agent" is really built, one concept at
a time, by growing a single project from a 1-turn LLM call into a
production-shaped agent harness with tools, memory management, planning,
error recovery, guardrails, observability, multi-agent orchestration, and
a packaged reusable library, followed by external tool integration through MCP.

## Who this is for

You already know Python and have called an LLM API before (OpenAI,
Anthropic, etc.). You don't need any prior "agent framework" experience —
in fact, this course deliberately avoids frameworks like LangChain/AutoGen
so you build the underlying mechanics yourself and understand exactly what
those frameworks are doing under the hood.

## Philosophy

Every module **builds on concepts from the previous modules**. By the end,
you will have watched one project grow from ~40 lines to a multi-file core
package, with advanced policies and workflows demonstrated in focused
standalone modules. You'll understand each piece because you built it
incrementally rather than being handed a finished framework.

All code uses the **OpenAI-compatible API format**, via the official
`openai` Python SDK. The examples are tested with Ollama's compatible
endpoint and use the same request shape as:
- OpenAI's real API
- A local [Ollama](https://ollama.com) server (`ollama serve`, OpenAI-compat
  mode at `http://localhost:11434/v1`)
- Other OpenAI-compatible providers (vLLM, LM Studio, together.ai, etc.)

You switch between the default Ollama setup and OpenAI by changing three
constants (`BASE_URL`, `API_KEY`, `MODEL`) at the top of each file. Exact
feature and parameter support varies among other compatible providers, so
check the provider's compatibility documentation when using one.

## Setup

Use **Python 3.10 or newer**. Modules 5 and 9 use the `str | None` type-hint
syntax added in 3.10, and Module 13's MCP SDK requires it. Check your version
with `python3 --version`.

Create and activate a project-local virtual environment, then install the
dependency inside it:

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install openai
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install openai
```

Run the module commands below while the virtual environment is activated.
When finished, leave it with `deactivate`.

Module 13 additionally uses the official MCP Python SDK's `MCPServer` and
`Client` APIs. Its requirements pin `openai==3.19.2`, which is older than the
version the other modules were tested with, so install them in a separate
virtual environment and use that environment only for Module 13:

```bash
python3 -m venv .venv13
source .venv13/bin/activate
python -m pip install -r module13/requirements.txt
```

If using Ollama locally:
```bash
ollama pull gemma4:e4b   # recommended default for this course
ollama serve
```

`gemma4:e4b` is the recommended default for this course. With the default
Ollama configuration, the examples send `reasoning_effort="none"` so the
agent-loop and tool-calling behavior stays easy to observe while learning.
That provider-specific option is omitted after replacing the dummy `ollama`
API key with a real provider key, because not every model supports it.

Whichever variant you choose, set the same model name in each module's
`MODEL` constant.

If using real OpenAI, set `BASE_URL = "https://api.openai.com/v1"` and
`API_KEY` to your real key in the config section of whichever module
you're running.

Each implementation module has a standalone entry point:
```bash
python module00/module00_baseline.py
python module01/module01_agent_loop.py
# ...etc
python module13/inspect_tools.py       # MCP only; no model needed
python module13/module13_mcp_tools.py   # agent using MCP tools
```

## Module Index

| Module | Topic | What gets added |
|---|---|---|
| [0](module00/README.md) | Why a Harness? | Baseline: a single LLM call, no loop, no tools |
| [1](module01/README.md) | Minimal Agent Loop | Multi-turn loop + conversation history |
| [2](module02/README.md) | Your First Tool | Real tool/function calling (a calculator) |
| [3](module03/README.md) | Tool Registry & Multiple Tools | Decorator-based registry, robust error handling |
| [4](module04/README.md) | Context Management | Summarize older execution steps while preserving the original task |
| [5](module05/README.md) | Persistent Memory | JSON knowledge storage, retrieval, updates, and deletion across runs |
| [6](module06/README.md) | Planning & Task Decomposition | Plan → Execute → Synthesize pattern |
| [7](module07/README.md) | Error Recovery & Self-Correction | Retry limits + reflection/critique loop |
| [8](module08/README.md) | Parallel Execution & Performance | Async tool calls, rate limiting |
| [9](module09/README.md) | Guardrails & Safety | Human-in-the-loop confirmation, input validation, audit log |
| [10](module10/README.md) | Observability & Debugging | Structured tracing, saved JSON traces, trace viewer |
| [11](module11/README.md) | Multi-Agent & Orchestration | Sub-agents-as-tools pattern (researcher + writer) |
| [12](module12/README.md) | Practical Deployment | Packaged reusable library: cost tracking, caching, prompt versioning |
| [13](module13/README.md) | MCP: External Tools | MCPServer + Client, discovery and execution through a local tool server |
| [14](module14/README.md) | Production Roadmap | What to study and harden after completing the course |

## Companion Book

The [`book/`](book/README.md) folder contains a beginner-friendly companion
book, *Build Your Own Agent Harness*. The module READMEs are short
references; the book explains why each piece is built the way it is, walks
through the code, shows real output from running every module (including the
model's mistakes), and helps when you get stuck.

- **Chapter N goes with `moduleNN/`**, so you can move between the book and
  the code without translating.
- Start with [Before You Begin](book/chapters/before-you-begin.md), which
  covers setup, then read [Chapter 0](book/chapters/ch00-no-harness.md).
- The appendices collect a [glossary](book/appendices/appendix-a-glossary.md),
  [common errors and fixes](book/appendices/appendix-b-common-errors.md),
  [how to switch providers](book/appendices/appendix-c-switching-providers.md),
  and [exercise solutions](book/appendices/appendix-d-solutions.md).

The chapters are Markdown files that read fine on GitHub. To build them into
an HTML book with navigation and search, install [Quarto](https://quarto.org)
and run:

```bash
cd book
quarto render
```

The output goes to `book/_book/` (Git-ignored). Use `quarto preview` instead
to open a live preview in your browser.

## Files in this project

```
module00/                     # Modules 0-11 each contain a script and README
  README.md
  module00_baseline.py
module01/
  README.md
  module01_agent_loop.py
# ... module02/ through module11/ follow the same pattern
# Module 5 creates memory.json to persist project knowledge
module12/
  README.md
  example_usage.py
  agent_harness/              # packaged reusable library
    __init__.py
    config.py
    tools.py
    prompts.py
    cost.py
    cache.py
    loop.py
module13/
  README.md
  requirements.txt           # verified MCP + model SDK versions
  tool_server.py             # independent MCP tool provider
  inspect_tools.py           # discover/call tools without an LLM
  module13_mcp_tools.py       # agent loop using MCP tools
module14/
  README.md                   # roadmap from educational code to production
book/                         # companion book (see "Companion Book" above)
  README.md                   # table of contents and writing guidelines
  _quarto.yml                 # Quarto book configuration
  chapters/                   # Before You Begin + Chapters 0-14
  appendices/                 # Appendices A-D
README.md                     # this file
```

## How to work through this course

1. Read a module's README (linked above) before running its code —
   each one explains the new concept and exactly what changed from the
   previous module. For a slower, more detailed explanation, read the
   matching chapter of the companion book.
2. Run the script and watch the step-by-step console output — every
   module prints what it's doing at each step so you can follow the
   mechanics live, not just read about them.
3. Try the "Things to try" section at the end of each module README —
   small modifications that deepen your understanding.
4. Move to the next module once you're comfortable with the current one's
   code. Modules 4-11 are focused variations on the core loop rather than
   a cumulative implementation of every earlier feature.

Modules 4 and 5 distinguish in-session context compression from persistent
knowledge: first summarize completed execution steps, then save selected
facts across runs in JSON.

By Module 12, you'll have a small reusable core library
(`module12/agent_harness/`) that a new project could `import` directly
instead of copy-pasting a script. Modules 4-11 remain focused examples of
advanced features you can compose around that core.

Module 13 then uses the familiar loop to discover and call tools in a
separate MCP server. Start with its model-free inspection script before
running the agent. Finish with Module 14's production roadmap.

## Caveat: Educational Use Only

This project is intentionally designed for teaching. The examples favor
clarity and incremental learning over production-grade security,
reliability, performance, and optimization. Some implementations are
deliberately simplified, including tool validation, permission controls,
error handling, retries, caching, cost tracking, logging, and secret
management.

Before adapting any part of this project for production, perform a full
security and architecture review. At a minimum, consider strict input and
output validation, sandboxing and least-privilege access, authentication
and authorization, secure secret storage, rate limits and timeouts,
failure recovery, persistent state, privacy and data retention,
observability, testing, dependency management, model behavior evaluation,
scalability, latency, and cost controls. The sample code should be treated
as a learning foundation, not as production-ready software.

## Fun Fact

I also used AI while developing this project.

I defined the goals, curriculum, architecture, module boundaries, and implementation constraints. 
AI helped accelerate coding, review, documentation, and refinement.

That process reinforced one of the central ideas behind the course:

AI can generate and improve individual pieces of work, but the surrounding system still needs clear goals, structure, constraints, evaluation, and human judgment.

The same principle applies when building agents. A capable model is only one component. Reliable behavior comes from how the complete system is designed around it.
