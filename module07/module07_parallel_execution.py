"""
Module 7: Parallel Execution & Performance
=============================================
Goal: Every module so far executed tool calls and subtasks SEQUENTIALLY,
one at a time, even when they had no dependency on each other. That wastes
time (and sometimes money, if you're paying per-request overhead) when
calls are independent -- e.g. the model asking for 3 web searches at once,
or Module 5's independent subtasks.

New concepts:
  1. ASYNC EXECUTION: use Python's asyncio + the async OpenAI client to run
     independent tool calls or subtasks CONCURRENTLY instead of in a loop.
  2. RATE LIMITING: concurrency isn't free -- most API providers cap how
     many requests you can have in flight at once. We use an
     asyncio.Semaphore to cap concurrency ourselves, so we get the speed
     benefit without tripping the provider's rate limits.
  3. COST/LATENCY TRADEOFF: parallel calls finish faster (lower latency)
     but can spike your cost/rate-limit usage all at once. Sequential calls
     are slower but smoother. We print timing so you can SEE the difference.

We reuse the tool registry and tool-calling loop shape from earlier
modules, converted to async.

LEARNING RESOURCE: If you are not yet familiar with Python's asyncio, refer
to https://realpython.com/async-io-python/ before or while working through
this module.
"""

import asyncio
import json
import time
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
MODEL = "gemma4:e4b"

# Keep provider-specific options out of requests to models that may reject them.
LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}

# AsyncOpenAI is the async counterpart to the OpenAI client used in earlier
# modules -- same OpenAI-compatible protocol, just non-blocking.
client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)

MAX_TURNS = 6

# Caps how many tool executions (or LLM calls) can be in flight at once.
# Tune this down if your provider rate-limits you; tune it up if you have
# headroom and want more speed.
MAX_CONCURRENT_CALLS = 3
rate_limiter = asyncio.Semaphore(MAX_CONCURRENT_CALLS)

SYSTEM_PROMPT = """You are a helpful assistant with access to tools:
calculate and search_web. When a task has multiple independent parts,
feel free to request multiple tool calls at once.
"""

# ---------------------------------------------------------------------------
# TOOL REGISTRY (async versions of Module 3's tools)
# ---------------------------------------------------------------------------
TOOL_REGISTRY = {}
TOOLS_SCHEMA = []


def tool(description: str, parameters: dict, required: list):
    def decorator(fn):
        TOOL_REGISTRY[fn.__name__] = fn
        TOOLS_SCHEMA.append({
            "type": "function",
            "function": {
                "name": fn.__name__,
                "description": description,
                "parameters": {"type": "object", "properties": parameters, "required": required},
            },
        })
        return fn
    return decorator


@tool(
    description="Evaluate a basic arithmetic expression and return the numeric result.",
    parameters={"expression": {"type": "string", "description": "e.g. '2 + 2'"}},
    required=["expression"],
)
async def calculate(expression: str) -> str:
    # No real I/O here, but we still make it `async` so it fits uniformly
    # into the async tool-calling loop below (a real async tool -- like a
    # network-bound search -- would `await` something inside).
    return str(eval(expression, {"__builtins__": {}}, {}))


@tool(
    description="Search the web for a query and return a short summary of results.",
    parameters={"query": {"type": "string", "description": "The search query string."}},
    required=["query"],
)
async def search_web(query: str) -> str:
    """
    STUB, but with a simulated network delay (asyncio.sleep) so you can
    actually OBSERVE the benefit of running several of these concurrently
    instead of one after another.
    """
    await asyncio.sleep(1.5)  # pretend this is a slow network call
    return f"[STUB RESULT] Pretend web search results for: '{query}'."


async def execute_tool_call(tool_call) -> str:
    """
    Same error handling as Module 3/6, but async, and wrapped with the
    rate limiter semaphore so we never exceed MAX_CONCURRENT_CALLS
    simultaneous tool executions -- even if the model requests many more
    than that at once.
    """
    async with rate_limiter:
        tool_name = tool_call.function.name
        tool_fn = TOOL_REGISTRY.get(tool_name)
        if tool_fn is None:
            return f"ERROR: unknown tool '{tool_name}'."
        try:
            tool_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            return f"ERROR: could not parse arguments as JSON: {e}"
        try:
            return str(await tool_fn(**tool_args))
        except Exception as e:
            return f"ERROR: tool '{tool_name}' raised an exception: {e}"


async def run_agent_loop(user_task: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

    for turn in range(1, MAX_TURNS + 1):
        print(f"\n{'=' * 60}")
        print(f"[STEP {turn}] Sending {len(messages)} messages to the LLM...")
        print(f"{'=' * 60}")

        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            **LLM_OPTIONS,
        )
        message = response.choices[0].message

        if message.tool_calls:
            n = len(message.tool_calls)
            print(f"[STEP {turn}] LLM requested {n} tool call(s). "
                  f"Executing {'concurrently' if n > 1 else ''}...")
            messages.append(message)

            # THE KEY LINE OF THIS MODULE: instead of a `for` loop calling
            # tools one at a time, we launch them all as coroutines and use
            # asyncio.gather to run them CONCURRENTLY, then wait for all
            # results together. The rate_limiter semaphore inside
            # execute_tool_call() still caps true concurrency.
            start = time.monotonic()
            results = await asyncio.gather(*[
                execute_tool_call(tc) for tc in message.tool_calls
            ])
            elapsed = time.monotonic() - start
            print(f"[STEP {turn}] All {n} tool call(s) finished in {elapsed:.2f}s "
                  f"(sequential would have taken roughly {n * 1.5:.2f}s for the search tool alone).")

            for tool_call, tool_result in zip(message.tool_calls, results):
                print(f"  -> {tool_call.function.name}({tool_call.function.arguments}) "
                      f"=> {tool_result[:120]}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
            continue

        print(f"[STEP {turn}] LLM gave a final answer (no tool call).")
        return message.content

    return "(Agent did not finish within the turn limit.)"


async def main():
    # A task specifically designed to make the model want to issue several
    # INDEPENDENT search_web calls at once, so you can watch them run
    # concurrently rather than one after another.
    task = (
        "Search the web separately for these 3 topics: 'agent harness "
        "design', 'LLM tool calling', and 'async rate limiting'. "
        "Then briefly summarize each."
    )
    print(f"USER TASK: {task}")

    overall_start = time.monotonic()
    result = await run_agent_loop(task)
    overall_elapsed = time.monotonic() - overall_start

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(result)
    print(f"\nTotal wall-clock time: {overall_elapsed:.2f}s")
    print(f"{'#' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
