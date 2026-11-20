# Build Your Own Agent Harness (working title)

> A beginner-friendly companion book to the code in this repository
> (`module00`–`module14`). The code shows *what* each piece does. This book
> explains *why* it's built that way and *what actually happens* when you run it.

- **Who it's for**: Anyone comfortable with basic Python (functions, dicts,
  lists, `for` loops). You don't need to have called an LLM API before; the
  "Before You Begin" chapter covers that.
- **Chapter numbering**: Chapter N maps one-to-one to the `moduleNN` folder
  (Chapter 2 = `module02/`), so you never have to translate between the book
  and the code.
- **Draft status**: ✅ first draft done · 📝 in progress · ⬜ not started

---

## Table of Contents

### Before You Begin ⬜
- What an "agent" is, and why it needs a "harness"
- Anatomy of a single LLM API call: `messages`, roles (system / user / assistant), tokens
- Setting up: a virtual environment, the `openai` package, installing Ollama and pulling `gemma4:e4b`
- Will my computer handle it? Realistic memory and speed expectations, and how to switch to the OpenAI API instead
- How to read this book: how chapters are laid out, how to read the run logs, and why "my output doesn't match the book" is normal

### Part I. The Skeleton of an Agent — "Agent = Loop + Tools"

| Ch. | Title | The question it answers | Status |
|---|---|---|---|
| [0](chapters/ch00-no-harness.md) | Life Without a Harness | What can't you do with a single LLM call? | ✅ |
| [1](chapters/ch01-agent-loop.md) | The Minimal Agent Loop | How do you keep a model going until it says it's done? | ✅ |
| [2](chapters/ch02-first-tool.md) | Your First Tool | What changes when you hand the model a calculator? | ✅ pilot |
| [3](chapters/ch03-tool-registry.md) | The Tool Registry | How do you organize ten tools, and what do you do when one fails? | ✅ |

### Part II. Memory — Within a Session and Beyond It

| Ch. | Title | The question it answers | Status |
|---|---|---|---|
| [4](chapters/ch04-context-management.md) | Managing Context | When a conversation gets long, how do you shrink it without losing the original task? | ✅ |
| [5](chapters/ch05-persistent-memory.md) | Persistent Memory | What do you save, and where, so the agent remembers after a restart? | ✅ |

### Part III. Agents You Can Trust

> **Read this map before Part III**: Chapters 4–11 do *not* stack every
> earlier feature into one growing program. Each one branches off the basic
> loop from Chapters 1–3 and focuses on a single feature. ("Why doesn't the
> Chapter 6 code have Chapter 5's memory?" is expected.) The end of Chapter 5
> has a diagram of this branching structure.

| Ch. | Title | The question it answers | Status |
|---|---|---|---|
| [6](chapters/ch06-planning.md) | Planning and Task Decomposition | Can you get the agent to make a plan before tackling a big job? | ✅ |
| [7](chapters/ch07-error-recovery.md) | Error Recovery and Self-Correction | How does an agent fix its own mistakes without retrying forever? | ✅ |
| [8](chapters/ch08-parallel-execution.md) | Parallel Execution | How much faster is it to run independent tool calls at the same time? | ✅ |
| [9](chapters/ch09-guardrails.md) | Guardrails and Safety | How do you make the agent ask a human before doing something risky? | ✅ |
| [10](chapters/ch10-observability.md) | Observability and Debugging | When an agent misbehaves, how do you see what actually happened? | ✅ |
| [11](chapters/ch11-multi-agent.md) | Multi-Agent Orchestration | Can an agent call another agent the way it calls a tool? | ✅ |

### Part IV. Toward the Real World

| Ch. | Title | The question it answers | Status |
|---|---|---|---|
| [12](chapters/ch12-packaged-library.md) | Packaging a Reusable Library | How do you turn a script into a package other projects can `import`? | ✅ |
| [13](chapters/ch13-mcp-tools.md) | Connecting External Tools with MCP | How do you discover and call tools that live in a separate server process? | ✅ |
| [14](chapters/ch14-road-to-production.md) | The Road to Production | What else do you need to learn and change before this code serves real users? | ✅ |

- Packages, modules, `import`, and classes are introduced in Chapter 12, Section 12.2
- `async`/`await` basics are covered in Chapter 8, Section 8.3 (Chapter 13 relies on them)

### Appendices ⬜
- A. Glossary
- B. Common Errors and Fixes (collected from each chapter's "Common Problems")
- C. Switching to OpenAI or Another OpenAI-Compatible Provider
- D. Exercise Solutions

---

## Chapter Template (all chapters)

The Chapter 2 pilot follows this template. New chapters should keep the same order.

1. **What You'll Learn** — at most three goals, prerequisites, and the relevant code file
2. **The Problem** — a scene where the previous chapter's code *actually* falls short (a real run log when possible)
3. **The Big Idea** — an analogy and a diagram first, no code yet
4. **Walking Through the Code** — excerpts of *only what changed* since the last chapter, with file paths and line numbers
5. **Running It** — the command, the real output, and a line-by-line reading of that output
6. **Common Problems** — where beginners get stuck, and how to get unstuck
7. **Try It Yourself** — three to five exercises, easiest first. Solutions at the end of the chapter (Appendix D in the final version)
8. **Recap** — one key sentence and a bridge to the next chapter

## Writing Guidelines

- **Only real run logs.** Note the run date, model, and SDK version next to each
  log, and remind readers that model output varies from run to run.
- **The repository code is the source of truth.** Label every excerpt with its
  source, e.g. `module02/module02_first_tool.py:49-67`. When the code changes,
  update the excerpts and line numbers too. (This can be automated later with
  Quarto's code-include features.)
- **Voice and spelling**: American English, second person ("you"), friendly but
  precise. Define a term the first time it appears; code identifiers
  (`tool_calls`, `messages`) stay in code formatting.
- **Don't overclaim.** Say "you can't *trust* the model's arithmetic," not
  "the model can't do arithmetic" — match what we actually observed.
- **Format**: Markdown with Quarto-compatible syntax (callout blocks, Mermaid
  diagrams). It reads fine on GitHub and can later be built into a website,
  PDF, or ePub with Quarto.
