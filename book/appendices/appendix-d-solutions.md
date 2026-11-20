# Appendix D. Exercise Solutions

Solutions and hints for every chapter's "Try It Yourself" exercises.
Where an answer depends on what the model does, it describes what happened
in our runs; yours may differ. Try each exercise before reading its solution.

- [Chapter 0: Life Without a Harness](#chapter-0-life-without-a-harness)
- [Chapter 1: The Minimal Agent Loop](#chapter-1-the-minimal-agent-loop)
- [Chapter 2: Your First Tool](#chapter-2-your-first-tool)
- [Chapter 3: The Tool Registry](#chapter-3-the-tool-registry)
- [Chapter 4: Managing Context](#chapter-4-managing-context)
- [Chapter 5: Persistent Memory](#chapter-5-persistent-memory)
- [Chapter 6: Planning and Task Decomposition](#chapter-6-planning-and-task-decomposition)
- [Chapter 7: Error Recovery and Self-Correction](#chapter-7-error-recovery-and-self-correction)
- [Chapter 8: Parallel Execution](#chapter-8-parallel-execution)
- [Chapter 9: Guardrails and Safety](#chapter-9-guardrails-and-safety)
- [Chapter 10: Observability and Debugging](#chapter-10-observability-and-debugging)
- [Chapter 11: Multi-Agent Orchestration](#chapter-11-multi-agent-orchestration)
- [Chapter 12: Packaging a Reusable Library](#chapter-12-packaging-a-reusable-library)
- [Chapter 13: Connecting External Tools With MCP](#chapter-13-connecting-external-tools-with-mcp)

---

## Chapter 0: Life Without a Harness

**1. Easy math.** `2 + 2` is almost always right. With big numbers, the model usually gives
a confident answer with no warning, even when it's wrong. It rarely says
"I might be wrong" unless you ask it to.

**2. Same question, three times.** The wording changes every time, and with harder questions the facts or
numbers can change too. This is why later chapters never rely on the model
giving the exact same output twice.

**3. Add a system message.** The answer gets squeezed into five words (or close to it). A system
message is how you give the model standing instructions. Starting in
Chapter 1, every module uses one.

**4. Fake a memory.** Something like:

```python
messages = [
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "The capital of France is Paris."},
    {"role": "user", "content": "What did I just ask you?"},
]
```

The model will now say you asked about the capital of France. The model
didn't remember anything. *You* handed it the conversation. Memory lives
in your code, not in the model, and that's the key idea of Chapter 1.

---

## Chapter 1: The Minimal Agent Loop

**1. Pull the safety valve.** After one turn, there's no marker, so the loop ends with the warning and
returns `"(Agent did not finish within the turn limit.)"`. The safety valve
works even when everything else goes wrong.

**2. Print the transcript.** You should see `system`, `user`, then alternating `assistant` and `user`
("Continue...") entries: two new messages per turn, matching the 2 → 4 → 6
counts in the log.

**3. Break it, then fix it better.** With only `after.strip()`, the default task comes back empty whenever the
model puts the marker at the end, which in our runs was every time. For
the second part, one approach:

```python
before, after = assistant_reply.split(DONE_MARKER, 1)
final_answer = after.strip() or before.strip()
if not final_answer:
    earlier = [m["content"] for m in messages[:-1] if m["role"] == "assistant"]
    final_answer = earlier[-1].strip() if earlier else ""
```

`messages[:-1]` skips the reply we just appended (the bare marker). Notice
how much code it now takes to answer "what did the model mean?" That's
the cost of a text protocol, and the reason Chapter 2 moves away from it.

**4. Rename the marker.** Thanks to the f-string, the system prompt picks up the new marker
automatically, so nothing else has to change. If the prompt said
`TASK_COMPLETE` while the code checked for `ALL_DONE`, the model would
never "finish," and you'd hit `MAX_TURNS` every time.

**5. Ask for the impossible.** The model never writes the marker, so after six turns you hit the
`MAX_TURNS` warning. Watch the message count grow by two every step.
Without `MAX_TURNS`, this would run (and bill you) forever.

---

## Chapter 2: Your First Tool

**1. Go big.** The correct answer is `3820574872`. When we ran it while writing this
chapter, the model called `calculate('384712 * 9931')` and replied
"384712 * 9931 is **3,820,574,872**." As long as the model calls the tool,
`eval` does the math exactly, so a wrong answer means the model skipped the tool.

**2. Take away the menu.** There's no tool call; the answer arrives in STEP 1. It may be right, or it
may be wrong like in Section 2.1. Because the system prompt still says "use
calculate," you may also get a reply that only *talks about* using the tool
(see Section 2.6).

**3. The power of a description.** There's no single right answer. The model can often guess from the name
(`calculate`) alone, but its behavior may wobble from run to run. The more
tools you have, the more the quality of each `description` matters.

**4. One step at a time.** Each tool call adds one STEP and two `messages` (the order plus the result).
When we ran it, the model made three calls: `438 * 12` → `5256 - 57` →
`5199 / 3`, giving STEP 1 (2 messages) → STEP 2 (4) → STEP 3 (6) → STEP 4
(8, final answer). Notice the model copied the previous result (`5256`) into
the next expression. That's proof it read the `role="tool"` message. Small
models sometimes ignore the instruction and do it all in one call.

**5. Add a tool.** Three places: ① the `count_chars` function, ② a new entry in `TOOLS_SCHEMA`,
and ③ `"count_chars": count_chars` in `TOOL_REGISTRY`. You may also want ④ a
mention in the system prompt. Forget ② and the model won't know the tool
exists; forget ③ and you'll get an `unknown tool` error.

---

## Chapter 3: The Tool Registry

**1. Break it on purpose.** Both are caught by (3) as invalid arguments. `read_file(**{})` is missing
the required `path` argument. With a JSON list, `**` fails because it
needs a dictionary. Both raise `TypeError` before the tool's code ever runs.

**2. Add a fourth tool.** Something like:

```python
from datetime import datetime

@tool(description="Return the current local date and time.", parameters={}, required=[])
def get_current_time() -> str:
    return datetime.now().isoformat(timespec="seconds")
```

The registry and schema update themselves. Depending on the model, it may
use the tool right away or may stick to the three tools the system prompt
names. Updating the prompt (Section 3.8) makes it reliable.

**3. Let the model recover.** Small models often give up after one error and report it, like the
`notes.txt` run in Section 3.7. One way to help is to make the error more
useful, for example by adding a short list of files in the current folder
to the "No such file" message. Better error messages are one of the
cheapest ways to make an agent smarter.

**4. Fix the misleading error.** One approach is to check the arguments against the function's signature
*before* calling it, using `inspect.signature(tool_fn).bind(**tool_args)`.
`bind()` raises `TypeError` only when the arguments don't fit. Wrap that
in its own `try` and report invalid arguments there; then call the
function in a separate `try` where any exception, including `TypeError`,
counts as an exception inside the tool.

**5. Make the stub honest.** When we tried it, all three runs reported honestly, for example: "The web
search for 'current agent harness best practices' returned no specific
results. Additionally, 15% of 240 is 36.0." A clear "nothing found" got a
clear answer, while the vague placeholder got invented findings. Your
results may vary, but the lesson holds: tool output should say plainly what happened
("No results found for X") instead of looking like real data, and when it
matters, the system prompt should tell the model not to invent facts that
no tool returned.

---

## Chapter 4: Managing Context

**1. Compress every step.** In our run, compression ran four times, once before each of steps 3–6.
Each summary added the newest result to the list and kept the earlier ones,
for example "Calculate 340/4: Completed, result is 85.0." The context size
leveled off around 1,400–1,600 characters (Section 4.5).

**2. Protect a constraint.** In our two runs with the default settings, the final answer was in ALL
CAPS both times. The instruction is in `context.task`, which
`build_messages()` sends word for word every time, and compression never
touches it. (One of those runs did redo two searches after compression;
protecting the task doesn't protect the record of what's been done.)

**3. Measure it yourself.** Your numbers will be close but not identical: the model's wording and
tool-call ids change every run, so message sizes shift by a few characters.

**4. Make the tool results big.** Now each step is a few thousand characters, and the summary is a few
hundred, so each compression removes most of a step's size. This is the
situation compression was designed for.

**5. Break the step rule.** It depends on the provider, and the answer is a little alarming. When we
sent Ollama a `tool` result with no matching request, it **accepted it
without any error** and the model simply carried on. OpenAI's API, by
contrast, rejects such a request with an error saying a `tool` message
must follow an assistant message that has `tool_calls`. A provider that
silently accepts a broken conversation is worse than one that rejects it,
because you never find out. Because `compress_history()` only ever removes
whole steps, it can't create this situation on any provider.

---

## Chapter 5: Persistent Memory

**1. Edit the notebook yourself.** It reports your edited value. The file is the agent's only memory between
runs, so whatever the file says is the truth as far as the agent knows. That's
handy for fixing mistakes, and it's also why the file must be treated as
data rather than trusted instructions.

**2. Run Test 1 yourself.** With the original `read_memory`, our model said it didn't have the
version saved. With the improved version, it found the `runtime` entry
both times. Your model may behave differently, which is the point:
behavior that depends on the prompt can vary, while behavior in code doesn't.

**3. Two keys, two answers.** Answers vary: the model may pick one, mention both, or ask which is right.
A good answer mentions both and flags the conflict. The real fix is to
prevent it: reuse keys when updating, or have `remember` check for entries
with similar content (much harder than it sounds).

**4. Add a timestamp.** `validate_entry`, `load_entries`, `read_memory`, and `remember` all assume
the value is a plain string. Old files will fail validation unless you
convert them or accept both formats. This is a *schema migration*, and it's
why you should design the format before you have lots of saved data.

**5. Enforce "save only when asked".** Something like this at the top of `remember` and `forget`:

```python
if input(f"Allow the agent to change memory '{key}'? [y/N] ").strip().lower() != "y":
    return "The user declined this memory change."
```

Test 2 can no longer save anything without your approval. The cost is an
interruption on every save, even the ones you asked for. Chapter 9 explores
how to choose which actions need approval.

---

## Chapter 6: Planning and Task Decomposition

**1. See the raw plan.** Results vary. In all of our runs the plan parsed successfully, either as
plain JSON or after the fence-stripping step. Code fences are common with
many models and prompts, which is why the code handles them.

**2. A one-step task.** Usually one subtask, sometimes two (e.g. "compute" and "report"). The
pattern still works; it just has less to do.

**3. Validate the plan.** For example:

```python
if not (isinstance(subtasks, list) and subtasks
        and all(isinstance(s, str) and s.strip() for s in subtasks)):
    print(f"[PLAN] Unexpected plan shape, falling back. Raw: {raw}")
    subtasks = [user_task]
```

**4. Pass the evidence along.** Collect a list of `f"{name}({arguments}) → {result}"` strings as tools run,
and return them joined with the final message. The synthesizer can now copy
`45.0` and `42` instead of recomputing them. That matters a lot more for
numbers it can't easily work out itself.

**5. Let subtasks see earlier results.** Keep a running list of results in `run_plan_and_execute()` and pass it in,
e.g. `{"role": "user", "content": f"Results so far:\n{previous}\n\nYour subtask: {subtask}"}`.
Combined with Exercise 4, subtask 2 can see `391` and call
`calculate("391 + 100")`. Notice that you've given up some isolation:
every subtask's context now grows with the number of earlier results.

---

## Chapter 7: Error Recovery and Self-Correction

**1. A hair trigger.** After the first failure. The second call is skipped, and the model gets the
"has failed 1 times in a row" message. (The grammar isn't perfect for a
limit of 1; you could fix the message too.)

**2. Turn off the editor.** The loop runs zero times, so it returns the first answer without any
critique. Useful for comparing behavior with and without the editor.

**3. Reasoning first.** In our tests, yes: the critic failed the 591 answer both times and passed
the 491 answer both times (Section 7.6).

**4. A stricter `passes`.** `bool("false")` is `True`, because any non-empty string is truthy, so the
current code would accept the answer. Use
`if verdict.get("passes") is True:` instead. Model output is text, and
text that *looks* like a boolean isn't one.

**5. Give the critic evidence.** One approach: collect every `role="tool"` message's content from `messages`
and add a line like `Tool results gathered: ...` to the critique prompt.
With the real product in front of it, the critic has something concrete to
compare against. This moves the critic away from "fresh eyes" toward
"checker with evidence," which is usually the better trade for factual tasks.

---

## Chapter 8: Parallel Execution

**1. One table only.** About 4.5 seconds: the three searches wait for the single permit one after
another, exactly like the `for` loop.

**2. Predict, then measure.** Three rounds (3 + 3 + 1), so about 4.5 seconds.

**3. Time the model, too.** In our runs, the two model calls took about 11.5 of the 13 seconds, roughly
90%. On a fast hosted API, model calls are quicker, but they're still
usually the largest share.

**4. Fix the estimate.** For example:
`searches = sum(tc.function.name == "search_web" for tc in message.tool_calls)`
and use `searches * 1.5` in the message.

**5. Parallel subtasks.** On a hosted API, the subtasks overlap and the total time drops. On a local
Ollama server, the requests may queue up and finish no faster than before.
This is a good example of an optimization whose benefit depends on
something outside your code.

---

## Chapter 9: Guardrails and Safety

**1. Say no, then ask again.** The model usually calls `delete_file` again, and the gate appears again:
every call goes through `execute_tool_call()`, and nothing remembers an
earlier denial. Whether that's what you want is a design decision. Some
systems remember a denial for the rest of the session.

**2. A second dangerous tool.** Yes. The gate checks `tool_name in DANGEROUS_TOOLS`, which the decorator
fills in automatically.

**3. A permanent audit log.** Add these lines to `audit()`:

```python
with open(MODULE_DIR / "audit.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(entry) + "\n")
```

One JSON object per line ("JSON Lines") is a common format for logs: easy
to append to, and easy to read back one line at a time.

**4. A scratch-folder allowlist.** Define `SCRATCH_DIR = MODULE_DIR / "scratch"`, use it in place of
`MODULE_DIR` in both `delete_file` and the validation, and check
`target.parent != SCRATCH_DIR`.

**5. Show the human more.** People approve what they understand. "delete_file {'path': 'notes.txt'}"
is easy to wave through. "notes.txt, 48 KB, first line: 'Q3 budget draft'"
makes the consequences concrete. A confirmation prompt is only as good as
the information it shows.

---

## Chapter 10: Observability and Debugging

**1. Never lose a trace.** For example:

```python
try:
    result = run_agent_loop(task, tracer)
    ...
finally:
    tracer.save(TRACE_FILE)
```

After Ctrl+C, the file is written with every event recorded so far.

**2. Write as you go.** Add to the end of `record()`:

```python
with open(TRACE_FILE.with_suffix(".jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")
```

With the simulated crash, the file has three lines: one model call and two
tool calls.

**3. Ask the trace a question.** For our run, it prints
`[('calculate', '336'), ('search_web', "[STUB RESULT] Pretend web search results for: 'agent tracing best practices'.")]`.

**4. A fuller trace.** A full trace lets you reconstruct the whole conversation, but it's much
bigger, and it may contain things you shouldn't keep, like personal data a
user typed in. Real systems often store full traces briefly and condensed
traces long-term, and redact sensitive fields.

**5. Catch the hallucination automatically.** Matching sentences to sources is hard because the model rarely quotes. It
paraphrases, combines, and adds its own knowledge. This is why many
production systems ask the model to *cite* which tool result supports each
claim, and then check the citations, rather than trying to reverse-engineer
them afterward.

---

## Chapter 11: Multi-Agent Orchestration

**1. Count the calls.** Wrap the method once at the top of `run_orchestrator()` or in your own
script:

```python
real_create = client.chat.completions.create
count = 0
def counted(**kwargs):
    global count
    count += 1
    return real_create(**kwargs)
client.chat.completions.create = counted
```

You'll usually see 7: three orchestrator turns, two or three researcher
turns, and one writer turn. It changes if the researcher searches more or less.

**2. See the handoffs.** In our runs, the orchestrator always condensed and rephrased the notes, and
added its own instructions about tone. Sometimes it also added details, so
compare carefully.

**3. An honest researcher.** With nothing real to go on, the writer should produce a short paragraph
saying the information couldn't be found, or the orchestrator may decide not
to call the writer at all. Either is more honest than a confident paragraph
built on nothing.

**4. Skip the copy.** One approach: in `delegate_to_writer`, store the writer's output in a
variable outside the function, and after `run_orchestrator()` returns,
return that stored text if it exists. In our runs, this would save one call
and about 5–6 seconds.

**5. A fact-checker.** Have `delegate_to_researcher` return both its notes and the list of
`role="tool"` contents from its `messages` (you'll need to change
`run_tool_calling_loop()` to return those too). With stub searches, a good
fact-checker should flag nearly every claim, which is the right answer.

---

## Chapter 12: Packaging a Reusable Library

**1. Run it twice.** The second run should take close to zero seconds, with `[CACHE] hit` on
every model call, and the call count and token totals in `stats()` stay the
same while the hit count goes up. (If a tool result changes between runs, as
with `now()`, later calls miss.)

**2. A new prompt version.** Yes: `get()` returns the active version along with the text, and the example
prints it. Recording that version with each run is what makes a "this broke
when we changed the prompt" bug traceable.

**3. A private toolset.** The search tool isn't in its schema, so the model doesn't know it exists.
It will usually answer from its own knowledge or say it can't search. If it
asks for `search_web` anyway, `execute_tool_call()` looks in the agent's own
registry and returns "unknown tool."

**4. Don't cache garbage.** For example, in `_call_llm()`:

```python
msg = response.choices[0].message
ok = msg.tool_calls or (msg.content and not msg.content.startswith("<|"))
if self.cache is not None and ok:
    self.cache.set(MODEL, messages, self.tools_schema, response)
```

The bad answer is no longer cached, so the second run makes fresh model
calls and may get a good answer.

**5. Compose a feature.** Wrap each function: `def guarded(*args, **kwargs):` that checks a counter,
calls the original, and updates the counter on `"ERROR:"` results. Build a
new registry of guarded functions and pass it to `Agent`. The core didn't
need to change, which is exactly the benefit of keeping it small and
letting policies wrap around it.

---

## Chapter 13: Connecting External Tools With MCP

**1. Add a tool on the server.** No. The inspector discovers `subtract` and prints its generated schema. The
host only knows names it discovered, so new server tools need no host changes.

**2. Use it.** It should call `multiply(6, 7)` and then `subtract(42, 2)`. If it doesn't,
check that you restarted (each run starts a fresh server, so a new run is
enough).

**3. Description matters.** The description becomes empty or a generic fallback, depending on the SDK.
With only two clearly named tools, the model usually still chooses well. With
dozens of similar tools, good descriptions matter much more.

**4. An allowlist.** Filter with `tools = [t for t in tools if t.name in ALLOWED]` right after
discovery. The model never sees `multiply`, so it can't request it. It may do
the multiplication itself or say it can't, which is a good reason to check
the logs rather than the answer.

**5. Tell the errors apart.** Check the exception message (or type) in the `except` block. If it's the
structured-content validation error, return
`f"ERROR: tool '{name}' returned a result that doesn't match its schema: {exc}"`.
The model then sees the problem, and the run continues.
