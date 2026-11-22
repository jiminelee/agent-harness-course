# Build Your Own Agent Harness

> A beginner-friendly companion book to the code in this repository
> (`module00`–`module14`). The code shows *what* each piece does. This book
> explains *why* it's built that way and *what actually happens* when you run it.

- **Who it's for**: Anyone comfortable with basic Python (functions, dicts,
  lists, `for` loops). You don't need to have called an LLM API before; the
  "Before You Begin" chapter covers that.
- **Chapter numbering**: Chapter N maps one-to-one to the `moduleNN` folder
  (Chapter 2 = `module02/`), so you never have to translate between the book
  and the code.
- **Where to start**: [Before You Begin](chapters/before-you-begin.md) sets up
  your computer. Then read Chapters 0–3 in order; after that, follow your interests.

---

## Table of Contents

### [Before You Begin](chapters/before-you-begin.md)
- What an "agent" is, and why it needs a "harness"
- Anatomy of a single LLM API call: `messages`, roles, tokens
- Setting up: a virtual environment, the `openai` package, Ollama, and the `gemma4:e4b` model
- What your computer needs, and how to use a hosted API instead
- How to read this book, and why "my output doesn't match the book" is normal

### Part I. The Skeleton of an Agent — "Agent = Loop + Tools"

| Ch. | Title | The question it answers |
|---|---|---|
| [0](chapters/ch00-no-harness.md) | Life Without a Harness | What can't you do with a single LLM call? |
| [1](chapters/ch01-agent-loop.md) | The Minimal Agent Loop | How do you keep a model going until it says it's done? |
| [2](chapters/ch02-first-tool.md) | Your First Tool | What changes when you hand the model a calculator? |
| [3](chapters/ch03-tool-registry.md) | The Tool Registry | How do you organize ten tools, and what do you do when one fails? |

### Part II. Memory — Within a Session and Beyond It

| Ch. | Title | The question it answers |
|---|---|---|
| [4](chapters/ch04-context-management.md) | Managing Context | When a conversation gets long, how do you shrink it without losing the original task? |
| [5](chapters/ch05-persistent-memory.md) | Persistent Memory | What do you save, and where, so the agent remembers after a restart? |

### Part III. Agents You Can Trust

> **Before Part III**: Chapters 4–11 do *not* stack every earlier feature into
> one growing program. Each one branches off the basic loop from Chapters 1–3
> and focuses on a single feature. ("Why doesn't the Chapter 6 code have
> Chapter 5's memory?" is expected.) The end of Chapter 5 has a diagram of this
> branching structure.

| Ch. | Title | The question it answers |
|---|---|---|
| [6](chapters/ch06-planning.md) | Planning and Task Decomposition | Can you get the agent to make a plan before tackling a big job? |
| [7](chapters/ch07-error-recovery.md) | Error Recovery and Self-Correction | How does an agent fix its own mistakes without retrying forever? |
| [8](chapters/ch08-parallel-execution.md) | Parallel Execution | How much faster is it to run independent tool calls at the same time? |
| [9](chapters/ch09-guardrails.md) | Guardrails and Safety | How do you make the agent ask a human before doing something risky? |
| [10](chapters/ch10-observability.md) | Observability and Debugging | When an agent misbehaves, how do you see what actually happened? |
| [11](chapters/ch11-multi-agent.md) | Multi-Agent Orchestration | Can an agent call another agent the way it calls a tool? |

### Part IV. Toward the Real World

| Ch. | Title | The question it answers |
|---|---|---|
| [12](chapters/ch12-packaged-library.md) | Packaging a Reusable Library | How do you turn a script into a package other projects can `import`? |
| [13](chapters/ch13-mcp-tools.md) | Connecting External Tools with MCP | How do you discover and call tools that live in a separate server process? |
| [14](chapters/ch14-road-to-production.md) | The Road to Production | What else do you need to learn and change before this code serves real users? |

Two Python topics get a short introduction where they're first needed:
`async`/`await` in Chapter 8 (Section 8.3), and packages, modules, `import`,
and classes in Chapter 12 (Section 12.2).

### Appendices
- [A. Glossary](appendices/appendix-a-glossary.md)
- [B. Common Errors and Fixes](appendices/appendix-b-common-errors.md)
- [C. Switching to OpenAI or Another OpenAI-Compatible Provider](appendices/appendix-c-switching-providers.md)
- [D. Exercise Solutions](appendices/appendix-d-solutions.md)

---

## Reading the Book as a Website

The chapters read fine right here on GitHub. To build them into an HTML book
with navigation, search, and drawn diagrams, install [Quarto](https://quarto.org)
and run this from the `book/` folder:

```bash
quarto render
```

Open `_book/index.html` in your browser, or run `quarto preview` for a live
preview that updates as you edit.

## Contributing

If you're writing or revising chapters, see the [Writing Guide](WRITING_GUIDE.md)
for the chapter template, style rules, and checks to run before publishing.

## License

The book and its code are released under the [MIT License](../LICENSE).
