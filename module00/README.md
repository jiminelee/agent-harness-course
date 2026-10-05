# Module 0: Why a Harness? (Baseline)

**File:** `module00_baseline.py`

## Concept

Before building any agent machinery, this module shows you the plainest
possible thing: one message sent to an LLM, one response received. No
loop, no tools, no memory. This is the baseline every later module
improves on — and the point of this module is to make the LIMITATIONS of
a bare LLM call obvious, so the rest of the course feels motivated rather
than arbitrary.

## What's in the code

`ask_llm_once()` sends exactly one `messages` list containing a single
user message, and returns the single response. That's it — there is no
loop, no `tools=` parameter, no persisted history between calls.

The script deliberately asks three different kinds of questions to expose
three different gaps:

1. **A simple factual question** — a single call handles this fine. Not
   everything needs a harness.
2. **"What is 384712 * 9931?"** — without a real calculator tool, the
   model can only guess/estimate from its training, which is unreliable
   for arbitrary arithmetic. Module 2 fixes this with a real tool.
3. **"What did I just ask you?"** — since no history is kept between
   calls, the model has no idea. Module 1 fixes this by introducing a
   persistent message list.

## Key takeaway

> An "agent" is not a different kind of LLM call. It's the same LLM call,
> wrapped in code that adds a loop, memory, and tools. That wrapping code
> is the "harness" this whole course is about building.

## Run it

From the project root:

```bash
python module00/module00_baseline.py
```

## Things to try

- Change the arithmetic question to something even the model might get
  right by luck (e.g. `2 + 2`) vs. something it almost certainly can't
  (e.g. multiplying two large numbers) — notice the model rarely admits
  uncertainty on its own.
- Try asking a multi-part question in one message and see how the model
  handles it without any decomposition help (compare to Module 6's
  planning approach later).
