# Appendix C. Switching to OpenAI or Another Provider

Every module in this book talks to its model through the official `openai`
Python package, using the OpenAI-compatible request format. By default, that
request goes to Ollama on your own computer. You can send it to OpenAI's API, or
to another OpenAI-compatible provider, by changing three settings.

This appendix shows where those settings are, how to keep your API key out of
your code, and what may behave differently once you switch.

---

## C.1 The Three Settings

Every module defines the same three constants near the top of the file:

```python
BASE_URL = "http://localhost:11434/v1"   # where requests go
API_KEY = "ollama"                        # your key (Ollama ignores it)
MODEL = "gemma4:e4b"                       # which model answers
```

To use OpenAI instead:

```python
BASE_URL = "https://api.openai.com/v1"
API_KEY = "sk-..."          # your real key (see C.3 for a better way)
MODEL = "gpt-4o-mini"       # or another model that supports tool calling
```

The model name in the code comments, `gpt-4o-mini`, is just an example. Check
your provider's documentation for the models currently available, and pick one
that supports **tool calling**, since every module from Chapter 2 on depends on it.

### A fourth line you don't need to touch

```python
LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}
```

With Ollama, the modules send `reasoning_effort="none"` to turn off the model's
extended "thinking" mode, which keeps answers fast and the logs easy to read.
Not every provider or model accepts that option, so it's sent **only** when
`API_KEY` is the placeholder `"ollama"`. As soon as you put in a real key, the
option is dropped automatically.

---

## C.2 Where the Settings Live

Modules 0–11 are standalone scripts, so each has its own copy. Change the file
for the chapter you're running:

| Chapter | File |
|---|---|
| 0–11 | `moduleNN/moduleNN_*.py`, for example `module03/module03_tool_registry.py` |
| 12 | `module12/agent_harness/config.py` (one place for the whole package) |
| 13 | `module13/module13_mcp_tools.py` (only the model side; the MCP server needs no key) |

This repetition is exactly the problem Chapter 12 solves: in the packaged
library, provider settings live in one file.

---

## C.3 Keep Your Key Out of the Code

Writing a real API key into a source file is risky. It's easy to commit it to
Git by accident, and anyone who sees the file can use your account. A simple
improvement is to read the key from an **environment variable**:

```python
import os

API_KEY = os.environ["OPENAI_API_KEY"]
```

Then set the variable in your terminal before running the module.

On macOS or Linux:

```bash
export OPENAI_API_KEY="sk-..."
```

On Windows (PowerShell):

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

The variable lasts until you close that terminal. Because `API_KEY` is no longer
`"ollama"`, `LLM_OPTIONS` is automatically left empty.

For anything beyond learning, use a proper secrets manager. Chapter 14,
Section 14.3, explains why.

---

## C.4 What Changes When You Switch

The code works the same way with any OpenAI-compatible provider. The behavior
around it may not. Here's what to expect.

### Your output will differ from the book's logs

Every log in this book came from `gemma4:e4b`, a small model running locally. A
larger hosted model will often make fewer of the mistakes the chapters show.
For example, it may get Chapter 0's big multiplication right, follow Chapter 1's
`TASK_COMPLETE` instruction exactly, or never leak `<|tool_response>`
(Chapters 6 and 12).

That doesn't make the lessons obsolete. Every model makes mistakes; bigger ones
just make them less often, and sometimes more convincingly. To see a safeguard
work, you may need to provoke the failure on purpose, as some chapters do.

### Providers are stricter or looser in different ways

- **Message order.** In Chapter 4, Exercise 5, Ollama silently accepted a `tool`
  message that had no matching tool call. OpenAI's API rejects that request with
  an error. Code that only ever runs against a permissive server can hide bugs
  that a stricter one reveals.
- **Unsupported options.** Some providers reject parameters they don't
  recognize. That's why `reasoning_effort` is only sent to Ollama.
- **Feature support varies.** Tool calling, parallel tool calls, and reported
  token usage aren't supported identically everywhere. If something fails only
  on one provider, check that provider's compatibility notes.

### Cost becomes real

With Ollama, running the examples costs nothing but electricity. With a hosted
API, every call is billed by the token. The examples in this book are small,
but some chapters make many calls per run: Chapter 11 made 7 model calls for one
paragraph, and Chapter 4's tight-compression experiment ran 20 turns plus a
summary each turn. Check your provider's pricing, and consider setting a
spending limit in your account.

Chapter 12's `CostTracker` shows an *estimated* cost using placeholder prices
from `config.py`. Replace them with your provider's real prices if you want the
estimate to mean something.

### Rate limits appear

Hosted APIs limit how many requests you can make per minute and how many can run
at once. Chapter 8's semaphore (`MAX_CONCURRENT_CALLS`) is there for exactly
this reason. If you see rate-limit errors (often HTTP 429), lower the limit or
wait and try again.

### Speed changes

A hosted model may be much faster than a local one, or slower if the service is
busy. Either way, Chapter 8's lesson still holds: measure the whole run, because
the model calls usually dominate.

---

## C.5 Other OpenAI-Compatible Providers

Many tools and services accept the same request format: local servers such as
LM Studio or vLLM, and various hosted providers. Using one works the same way:
set `BASE_URL` to the address the provider documents (it usually ends in `/v1`),
set `API_KEY` to the key it gives you (or any non-empty string, if it doesn't
check), and set `MODEL` to a name it recognizes.

"Compatible" rarely means identical. Before relying on one, check that it
supports tool calling, and run Chapter 2's module as a quick test: if the model
calls `calculate` and the loop ends with the right answer, the basics work.

---

## C.6 Quick Checklist

- [ ] Changed `BASE_URL`, `API_KEY`, and `MODEL` in the file for the chapter
      you're running (or in `config.py` for Chapter 12)
- [ ] Chose a model that supports tool calling
- [ ] Loaded the key from an environment variable rather than writing it in the file
- [ ] Checked pricing, and set a spending limit if your provider offers one
- [ ] Ran `python module02/module02_first_tool.py` to confirm tool calling works
