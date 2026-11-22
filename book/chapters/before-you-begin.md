# Before You Begin

This short chapter gets you ready for the rest of the book. It explains what an
agent and a harness are, shows you the shape of a single call to a language
model, and walks you through setting up everything you need to run the code.

If you've already called an LLM API from Python and have Ollama running, you
can skim Sections 1 and 2 and go straight to Section 3 to check your setup.

---

## 1. What This Book Is About

### What's an agent?

You've probably used a chatbot: you type a question, it types an answer. An
**agent** goes further. You give it a *task*, and it works toward that task on
its own, over several steps: it decides what to do next, uses **tools** (a
calculator, a web search, a file reader), looks at the results, and keeps
going until it's done.

Under the hood, an agent uses the same kind of language model as a chatbot.
The model itself can only do one thing: read text and write text. Everything
else, the steps, the tools, the memory, the decision to stop, is ordinary code
written around the model.

### What's a harness?

That surrounding code is the **harness**. It's the part that:

- keeps track of the conversation, since the model remembers nothing on its own
- runs a loop, so the model can take more than one step
- gives the model tools, and actually runs them when the model asks
- decides when to stop, and what the model is and isn't allowed to do

This book builds a harness from scratch, one idea at a time. We deliberately
don't use agent frameworks (LangChain, AutoGen, and others), because they hide
exactly the mechanics you're here to learn. By the end, you'll understand what
those frameworks do under the hood.

### How the book and the code fit together

The book comes with a code repository. **Chapter N goes with the `moduleNN`
folder**: Chapter 2 is `module02/`, Chapter 13 is `module13/`, and so on. Each
module is a small, runnable program, and each chapter explains one module.

---

## 2. One Call to a Language Model

Every chapter builds on a single operation: sending text to a model and getting
text back. Here's what that looks like in Python, using the official `openai`
package:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

response = client.chat.completions.create(
    model="gemma4:e4b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "In one sentence, what is a language model?"},
    ],
)

print(response.choices[0].message.content)
```

Three ideas in this snippet show up on almost every page of the book.

**`messages` is a conversation, written as a list.** Each item is a dictionary
with a `role` (who's speaking) and `content` (what they said). The model reads
the whole list and writes the next message.

**There are four roles.**

| Role | Who it is | First appears |
|---|---|---|
| `system` | Standing instructions for the model ("You are a helpful assistant") | Chapter 1 |
| `user` | You, or your program speaking on your behalf | Chapter 0 |
| `assistant` | The model's replies | Chapter 1 |
| `tool` | The result of a tool the model asked for | Chapter 2 |

**Models read and write tokens, not characters.** A *token* is a chunk of
text, often a whole short word or a piece of a longer one. In English, a token
averages roughly four characters. Tokens matter for two reasons: every model
has a limit on how many it can read at once (its *context window*), and paid
APIs charge by the token. Chapter 4 and Chapter 12 come back to both.

### Why `openai` if we're not using OpenAI?

The code in this book talks to a model running on your own computer, through a
program called **Ollama**. Ollama understands the same request format as
OpenAI's API, an arrangement often called "OpenAI-compatible." That means the
official `openai` package works with it unchanged. You just point it at a
different address (`base_url`).

The same code also works with OpenAI itself, and with many other providers
that use the same format. Switching is a matter of changing three settings.
Appendix C shows how, and what to watch out for.

---

## 3. Setting Up

You'll need about 30 minutes, most of it waiting for downloads.

### What you need

| Requirement | Why |
|---|---|
| **Python 3.10 or newer** | Some modules use syntax added in 3.10, such as `str \| None` (Modules 5 and 9), and the MCP package in Module 13 requires it |
| **About 10 GB of free disk space** | The model file is 9.6 GB |
| **A computer with at least 16 GB of memory** | Recommended for running an 8-billion-parameter model comfortably. Less may work, but slowly |
| **Ollama** | Runs the model locally. Free, for macOS, Windows, and Linux |
| **A terminal** | Every example is run from the command line |

You don't need a GPU or an API key. If your computer can't run the model
well, see "Using a hosted API instead" at the end of this section.

### Step 1: Get the code

Clone or download the repository, then open a terminal in its top-level
folder, the one containing `README.md` and the `module00/` through `module14/`
folders. **Run every command in this book from that folder.**

### Step 2: Create a virtual environment

A *virtual environment* is a private set of Python packages for one project, so
this book's packages don't interfere with anything else on your computer.

On macOS or Linux:

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

On Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

When it's active, your prompt usually starts with `(.venv)`. You'll need to
activate it again each time you open a new terminal. When you're done for the
day, type `deactivate`.

Check your Python version while you're here:

```bash
python --version
```

It should say 3.10 or higher.

### Step 3: Install the `openai` package

```bash
python -m pip install --upgrade pip
```

```bash
python -m pip install openai
```

This is the only package Chapters 0–12 need. Chapter 13 needs two more, with
specific versions; see "A note about Chapter 13" below.

### Step 4: Install Ollama and download the model

Download Ollama from [ollama.com](https://ollama.com) and install it. Then
download the model this book uses:

```bash
ollama pull gemma4:e4b
```

This is the 9.6 GB download, so it may take a while. When it's done, confirm
that it's there:

```bash
ollama list
```

You should see `gemma4:e4b` in the list.

### Step 5: Start the model server

```bash
ollama serve
```

This command keeps running and doesn't return you to the prompt. That's normal:
it's a server waiting for requests. Leave it running and **open a second
terminal** for everything else (remember to activate the virtual environment
there, too). On some systems, the Ollama app starts the server for you
automatically, in which case `ollama serve` reports that the address is already
in use, and you can skip this step.

### Step 6: Check that everything works

In your second terminal, run:

```bash
python module00/module00_baseline.py
```

After a short pause (the first request loads the model into memory, which can
take a while), you should see three questions and three answers, starting with:

```text
============================================================
[SINGLE CALL] Sending one message to the LLM (no loop, no tools)...
============================================================
REQUEST: In one sentence, what is an 'agent harness'?
RESPONSE: ...
```

If you see answers, you're ready for Chapter 0. If you see an error, check
Appendix B, which collects every common error in the book.

### A note about Chapter 13

Chapter 13 uses the MCP Python SDK, and it pins exact versions that were tested
together: `mcp==2.2.0` and `openai==3.19.2`. That `openai` version is older
than the one Chapters 0–12 were run with (3.57.0). Installing it into your main
environment would replace the newer one.

The simplest way to avoid surprises is a second virtual environment just for
Chapter 13:

```bash
python3 -m venv .venv13
```

```bash
source .venv13/bin/activate
```

```bash
python -m pip install -r module13/requirements.txt
```

Use `.venv13` for Chapter 13 and `.venv` for everything else. Chapter 13
repeats this when you get there.

### Using a hosted API instead

If the local model is too slow on your computer, you can run every chapter
against a hosted, OpenAI-compatible API instead. You'll need an account and an
API key with that provider, and you'll pay per token, usually a small amount
for this book's examples. Appendix C explains exactly which three lines to
change in each module, and how hosted models may behave differently from the
logs in this book.

---

## 4. How to Read This Book

### The shape of a chapter

Every chapter from 0 to 13 follows the same pattern, so you always know where
you are:

1. **What You'll Learn** — the goals, and the code file for the chapter
2. **The Problem** — something the previous chapter's code can't do, or does badly
3. **The Big Idea** — an everyday analogy and a diagram, before any code
4. **Walking Through the Code** — only the parts that are new
5. **Running It** — the command, real output, and how to read it
6. **Common Problems** — where readers get stuck
7. **Try It Yourself** — exercises, easiest first, with solutions in Appendix D
8. **Recap** — the one sentence to remember, and a bridge to the next chapter

Chapter 14 is different: it has no code, and it looks back at the whole book.

### Code excerpts

Excerpts in the book are labeled with the file and line numbers they come from:

```python
# module02/module02_first_tool.py:49-67 (some comments omitted)
```

Open that file in your editor to see the excerpt in context. The repository is
always the source of truth: if the book and the code ever disagree, trust the code.

### The run logs are real

Every output in this book was captured from an actual run, and each log is
labeled with the date, model, and package versions, like this:

> Run on 2026-11-20 with Ollama `gemma4:e4b`, `openai` 3.57.0, Python 3.14.

**Your output will be different, and that's expected.** Language models don't
give the same answer twice. Wording changes, numbers of steps change, and
sometimes a model that got something right in the book will get it wrong for
you, or the other way around. What should match is the *shape* of the run: which
tools get called, in roughly what order, and how the harness responds.

Many chapters deliberately show the model failing: confidently wrong arithmetic,
invented "research," ignored instructions. Those failures are the most important
part of the book. Every safeguard in the code exists because of a failure like
the ones you'll see.

### Reading order

Chapters 0–3 build on each other, so read them in order. Chapters 4–11 each
branch off Chapter 3 and add one idea, so after Chapter 3 you can read them in
any order, though the book's order works well. (The end of Chapter 5 has a map
of how the modules relate.) Chapters 12 and 13 assume you've read Chapters 1–3
and Chapter 8's introduction to `async`.

### A word about safety

The code in this book is written to be easy to read, not to be safe for real
users. Tools use `eval()`, secrets are written directly into files, and there's
no sandboxing. Run it on your own computer, for learning. Chapter 14 explains
what would have to change before any of it served real people.

---

Ready? Turn to Chapter 0.
