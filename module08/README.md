# Module 8: Parallel Execution & Performance

**File:** `module08_parallel_execution.py`
**Builds on:** Module 3's tool registry pattern

## Concept

Every module so far executed tool calls **sequentially**, one at a time,
even when they had no dependency on each other. This wastes time when
calls are genuinely independent (e.g. the model requesting 3 unrelated web
searches in one turn). This module introduces:

1. **Async execution** — using `asyncio` + `AsyncOpenAI` to run
   independent tool calls concurrently instead of in a `for` loop.
2. **Rate limiting** — an `asyncio.Semaphore` caps how many calls can be
   in flight at once, so you get the speed benefit without exceeding your
   provider's rate limits.
3. **Cost/latency tradeoff** — parallel calls finish faster but spike
   usage all at once; sequential calls are slower but smoother. Timing is
   printed so you can see the difference directly.

If you are not yet familiar with Python's `asyncio`, refer to
[Python's asyncio: A Hands-On Walkthrough](https://realpython.com/async-io-python/)
before or while working through this module.

## What's new since Module 3

| Module 3 | Module 8 |
|---|---|
| `OpenAI` (sync client) | `AsyncOpenAI` (async client) |
| `for tool_call in message.tool_calls:` (sequential) | `asyncio.gather(*[execute_tool_call(tc) for tc in message.tool_calls])` (concurrent) |
| No concurrency cap | `asyncio.Semaphore(MAX_CONCURRENT_CALLS)` |
| No timing instrumentation | Wall-clock timing printed per batch of tool calls |

## Why `search_web` has a fake delay

`search_web` in this module calls `await asyncio.sleep(1.5)` before
returning its stub result, simulating a slow network call. This is what
lets you actually *observe* the benefit of concurrency — with 3 searches
requested at once, sequential execution would take ~4.5s, while concurrent
execution (bounded by the semaphore) finishes in roughly the time of the
single slowest call.

## Key takeaway

> Concurrency is a free win only for genuinely independent work. It also
> isn't free of risk — that's what the semaphore is for: capping how much
> you do at once so you don't overwhelm a rate-limited API.

## Run it

From the project root:

```bash
python module08/module08_parallel_execution.py
```

Compare the printed "finished in Xs" line against the "sequential would
have taken roughly Ys" estimate in the same log line.

## Things to try

- Lower `MAX_CONCURRENT_CALLS` to 1 and confirm the timing degrades back
  toward sequential-speed, even though the code still uses
  `asyncio.gather`.
- Increase the simulated delay in `search_web` and watch the speed-up
  become more dramatic with more independent calls.
- Apply the same `asyncio.gather` pattern to Module 6's independent
  subtasks — a natural extension combining planning with parallelism.
