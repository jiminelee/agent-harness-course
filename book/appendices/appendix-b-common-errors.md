# Appendix B. Common Errors and Fixes

This appendix collects the "Common Problems" from every chapter, grouped by
what you see. Find your symptom, apply the fix, and follow the chapter
reference if you want the full explanation.

- **Part 1** covers setup problems that stop anything from running.
- **Part 2** lists error messages, alphabetically by the start of the message.
- **Part 3** covers programs that run but don't do what you expected.
- **Part 4** covers runs that are slow.

---

## Part 1. Setup

**`ModuleNotFoundError: No module named 'openai'`**
Your virtual environment isn't active, or the package was installed somewhere
else. Activate it (`source .venv/bin/activate` on macOS/Linux) and run
`python -m pip install openai`. (Before You Begin, Chapter 0)

**`Connection refused`, or `APIConnectionError`**
The Ollama server isn't running. Run `ollama serve` in another terminal and
leave it open. (Chapters 0, 2)

**`model "gemma4:e4b" not found` (a 404 error)**
The model hasn't been downloaded. Run `ollama pull gemma4:e4b`, then check
`ollama list`. (Chapter 0)

**`SyntaxError` or `TypeError` mentioning `|` in a type hint, such as `str | None`**
Your Python is older than 3.10. Modules 5 and 9 need 3.10 or newer. Check
with `python --version`. (Before You Begin)

**`ImportError: cannot import name 'MCPServer'` (or `Client`)**
The wrong `mcp` version is installed, or it's in a different environment.
Activate the Chapter 13 environment and run
`python -m pip install -r module13/requirements.txt`. (Chapter 13)

**`ModuleNotFoundError: No module named 'agent_harness'`**
Python can't find the package. Run `python module12/example_usage.py` from the
repository's top-level folder, so the script's folder is on Python's search
path. (Chapter 12)

**The script can't find a file I know exists**
Relative paths are resolved from the folder you ran `python` from, unless the
module deliberately anchors them to its own folder (Modules 5, 9, and 10 do).
Run from the top-level folder, or use an absolute path. (Chapter 3)

---

## Part 2. Error Messages

**`(Agent did not finish within the turn limit.)` or `[WARNING] Max turns reached`**
The loop hit `MAX_TURNS`. The model kept calling tools, or never produced its
stop signal. Print the messages to see what it was doing. This is the safety
valve working as intended. (Chapters 1, 4)

**`(No final text from the model; see tool results above.)`**
The model called a tool, then returned an empty final message. The tool
results in the log show what actually happened. (Chapter 5)

**`(RESEARCHER did not finish within its turn limit.)` or `(subtask did not finish within its turn limit)`**
A sub-agent or subtask used all its turns. The message becomes that step's
result, and the run continues. (Chapters 6, 11)

**`[PLAN] Could not parse plan as JSON, falling back to single-step plan.`**
The planner replied with prose or broken JSON. The run continues with the whole
task as one subtask. Print the raw reply to see what came back. (Chapter 6)

**`[REFLECT] Could not parse critique JSON, defaulting to pass.`**
The critic's reply wasn't JSON, so the answer was accepted without review.
(Chapter 7)

**`EOFError: EOF when reading a line`**
A confirmation prompt had no terminal to read from. Run Module 9 from a real,
interactive terminal. (Chapter 9)

**`ERROR: invalid arguments for '...': ... got an unexpected keyword argument ...`**
The model used the wrong argument name. In Module 3 and later, this goes back to
the model as a tool result, and it can try again. (Chapter 3)

**`ERROR: rejected suspicious path '...'`**
Module 9's validation only allows files directly inside `module09/`. Subfolders,
`..`, and absolute paths are refused on purpose. (Chapter 9)

**`ERROR: tool 'read_memory' failed: Expecting ',' delimiter...`**
`memory.json` contains invalid JSON, probably after a hand edit. Look for a
missing comma, a trailing comma, or single quotes. Fix it or delete the file.
(Chapter 5)

**`ERROR: unknown tool '...'`**
The model asked for a tool that isn't registered for this agent. In Module 12,
check whether the agent was given its own `tool_registry`. (Chapters 3, 12)

**`json.decoder.JSONDecodeError` (crash)**
The model sent broken tool arguments, and this module doesn't catch it.
Modules 2, 10, and 11 don't wrap `json.loads()` in a `try`; Chapter 3 shows the
fix. (Chapters 2, 10, 11)

**`RuntimeError: Invalid structured content returned by tool ...`**
An MCP tool returned a result that didn't match its declared output type
(for example, an overflow to infinity). The client rejects it, and Module 13
stops the run. (Chapter 13)

**`RuntimeWarning: coroutine '...' was never awaited`**
You called an `async def` function without `await`. (Chapter 8)

**`SyntaxError: 'await' outside async function`**
`await` only works inside `async def`. Start async code with
`asyncio.run(main())`. (Chapter 8)

**`TypeError: ... got an unexpected keyword argument ...` (crash)**
Same as the "invalid arguments" error above, in Module 2, which doesn't catch it.
(Chapter 2)

**`ValueError: Require 1 <= KEEP_RECENT_STEPS <= MAX_STEPS_BEFORE_SUMMARY`**
Module 4's settings are invalid. Keep at least one recent step, and no more than
the summary threshold. (Chapter 4)

**`ValueError: Summarizer returned no text; context was not changed`**
The summarizer came back empty. The run stops rather than continuing with a
broken context. Run it again. (Chapter 4)

**Protocol or parsing errors from MCP after editing the server**
The server printed something to standard output, which is the protocol channel.
Print debug output to `sys.stderr`. (Chapter 13)

---

## Part 3. It Runs, But...

### The answer is wrong, empty, or strange

**The final answer is empty**
In Module 1, the model may have replied with only `TASK_COMPLETE`, after putting
its answer in an earlier message. (Chapter 1)

**The final answer is only part of what the model wrote**
In a multi-turn task, Module 1 returns only the message containing the marker.
(Chapter 1)

**A result is `<|tool_response>`**
The model leaked a fragment of its internal chat format instead of writing a
reply. Treat it as a failed step. Module 12's cache will store it if you let it.
(Chapters 6, 12)

**The answer contains numbers or facts no tool produced**
The model computed or invented them, often in a synthesis or summary step.
Compare the answer with the tool results in the log or trace. (Chapters 6, 10)

**The answer reports "findings" from a search**
The search tool is a stub that returns nothing real. The model filled the gap.
(Chapters 3, 10, 11)

**The definitions change from run to run**
They're coming from the model's own knowledge, not from a source.
(Chapter 11)

**The final answer is missing a detail from an early step**
Context compression dropped it from the summary. (Chapter 4)

**The second run returns the same wrong answer instantly**
Module 12's cache stored the bad response. Use `use_cache=False` while
debugging. (Chapter 12)

**The answer starts with "The final polished text is:"**
Module 11's orchestrator wrapped the writer's output. (Chapter 11)

### The agent doesn't do what you asked

**The model answers without calling the tool**
Check that the model supports tool calling (`ollama show <model>`, look for
`tools`), that `tools=` is being sent, and whether the task was simply easy
enough to do without a tool. (Chapter 2)

**The model *says* it will use a tool, then stops**
`tools=` wasn't sent, but the prompt mentions the tool. (Chapter 2)

**A new tool is never used**
Check whether the system prompt lists the tools by name, which hides new ones.
(Chapter 3)

**A tool's name in the schema is wrong**
The decorator uses the function's name. Rename the function. (Chapter 3)

**The agent can use a tool you never gave it**
Module 12's default agents share one global registry. Pass `tools_schema` and
`tool_registry` explicitly. (Chapter 12)

**The orchestrator answers by itself without delegating**
Make the system prompt firmer, or run it again. (Chapter 11)

**The model never calls `delete_file`**
Small models sometimes answer in text. Run it again or rephrase. (Chapter 9)

**A subtask says "Please provide..."**
It depends on an earlier result it can't see, because Module 6 isolates
subtasks. (Chapter 6)

**The agent says a fact isn't saved, but it's in the file**
The fact is under a different key than the one the model guessed. (Chapter 5)

**The agent repeats a step it already did**
A summary dropped the record of that step. (Chapter 4)

**The answer is 52, but there are no `[MCP CALL]` lines**
The model did the arithmetic itself instead of using the MCP tools. (Chapter 13)

### The safeguards don't behave as expected

**The loop stopped too early**
Module 1's marker check matches the word anywhere, even when the model only
mentions it. (Chapter 1)

**The circuit breaker never trips**
The model isn't retrying; it reads one error and moves on. (Chapter 7)

**The critic's feedback says the answer is wrong, but it passed**
The verdict field came before the reasoning. Put `feedback` first. (Chapter 7)

**The critic approves an answer with a wrong number**
It has no way to check arithmetic or facts. (Chapter 7)

**Compression never happens**
The task finished in too few steps, often because the model batched tool calls.
Lower the thresholds. (Chapter 4)

**`[CACHE] hit` never appears**
Each `Agent` has its own cache, and the cache is lost when the program exits.
(Chapter 12)

### Files and output

**I can't find `memory.json`**
It's in `module05/`, created on the first save, and ignored by Git. (Chapter 5)

**There's no `agent_trace.json`**
The run didn't finish normally, so the trace was never saved. (Chapter 10)

**The trace is cut off**
Model-call events are deliberately condensed. (Chapter 10)

**Every run overwrites the last trace or audit log**
Module 10 overwrites its file, and Module 9's audit log is only in memory.
(Chapters 9, 10)

**The script seems frozen**
It's probably waiting for you at a confirmation prompt (Module 9), or it's
`tool_server.py`, which waits for MCP input and shouldn't be started by hand
(Module 13). (Chapters 9, 13)

**My output doesn't match the book**
Expected. Models vary from run to run. Check the shape of the run instead: which
tools were called, in what order, and how the harness responded.
(Before You Begin)

---

## Part 4. Slow Runs

**The first request takes a long time**
Ollama loads the model into memory on first use. Later requests are faster.
(Chapter 0)

**Every turn is slower than the last**
The whole conversation is resent each turn, so requests keep growing.
(Chapters 1, 4)

**A run is slower than in earlier chapters**
Extra model calls: summaries (Chapter 4), critiques (Chapter 7), or sub-agents
(Chapter 11). Count the calls.

**Parallel execution isn't faster**
The model asked for one tool per step, the concurrency limit is 1, or the tools
don't wait on anything. (Chapter 8)

**Tools got faster, but the run barely did**
The model calls take most of the time. Measure the whole run. (Chapter 8)
