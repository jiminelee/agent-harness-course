"""
Module 3: Tool Registry & Multiple Tools
==========================================
Goal: In Module 2 we had exactly one hardcoded tool. Real agents have many.
This module introduces a REGISTRY PATTERN so adding a new tool means writing
one function with a decorator -- nothing else needs to change in the loop.

We also harden error handling for three realistic failure modes:
  1. The model requests a tool that doesn't exist.
  2. The model's arguments don't match what the tool expects (missing/invalid).
  3. The tool itself throws an exception while running (already handled a bit
     in Module 2, we make it more general here).

New tools added this module:
  - calculate      (carried over from Module 2)
  - search_web     (STUBBED -- returns fake canned results; swap in a real
                     search API like Tavily/Bing/Google in production)
  - read_file       (reads a real local text file, with proper error handling)
"""

import json
import traceback
from openai import OpenAI

# ---------------------------------------------------------------------------
# CONFIGURATION (same pattern as Modules 1-2)
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:11434/v1"   # or "https://api.openai.com/v1"
API_KEY = "ollama"
MODEL = "gemma4:e4b"

# Keep provider-specific options out of requests to models that may reject them.
LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

MAX_TURNS = 8

SYSTEM_PROMPT = """You are a helpful assistant with access to multiple tools:
calculate, search_web, and read_file. Choose the right tool for each part of
the task. Only give a final answer once you have everything you need.
"""

# ---------------------------------------------------------------------------
# TOOL REGISTRY PATTERN
# ---------------------------------------------------------------------------
# Instead of manually maintaining a TOOLS_SCHEMA list AND a TOOL_REGISTRY dict
# by hand (as in Module 2), we use a decorator that populates both at once,
# right next to the function definition. This scales much better as the
# number of tools grows -- adding tool #10 doesn't require touching any
# existing code, just adding a new @tool(...)-decorated function.

TOOL_REGISTRY = {}   # name -> python function
TOOLS_SCHEMA = []    # name -> JSON schema description sent to the LLM


def tool(description: str, parameters: dict, required: list):
    """
    Decorator factory that registers a function as an agent tool.

    - description: human/LLM-readable explanation of what the tool does.
    - parameters: JSON-schema "properties" dict describing each argument.
    - required: list of argument names that must be provided.
    """
    def decorator(fn):
        TOOL_REGISTRY[fn.__name__] = fn
        TOOLS_SCHEMA.append({
            "type": "function",
            "function": {
                "name": fn.__name__,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required,
                },
            },
        })
        return fn
    return decorator


# ---------------------------------------------------------------------------
# TOOL DEFINITIONS
# ---------------------------------------------------------------------------

@tool(
    description="Evaluate a basic arithmetic expression and return the numeric result.",
    parameters={
        "expression": {"type": "string", "description": "e.g. '2 + 2' or '(5*3)/2'"}
    },
    required=["expression"],
)
def calculate(expression: str) -> str:
    """Same as Module 2's calculator tool."""
    result = eval(expression, {"__builtins__": {}}, {})
    return str(result)


@tool(
    description="Search the web for a query and return a short summary of results.",
    parameters={
        "query": {"type": "string", "description": "The search query string."}
    },
    required=["query"],
)
def search_web(query: str) -> str:
    """
    STUB IMPLEMENTATION for learning purposes only.

    In a real harness, this function would call a real search API
    (e.g. Tavily, Bing Search API, SerpAPI) and return actual results.
    Here we just return a fake canned string so you can see the tool-calling
    mechanics work end-to-end without needing an API key for a search
    provider on top of your LLM provider.
    """
    return f"[STUB RESULT] Pretend web search results for: '{query}'. (Replace this function body with a real search API call.)"


@tool(
    description="Read the full contents of a local text file, given its path.",
    parameters={
        "path": {"type": "string", "description": "Filesystem path to a text file."}
    },
    required=["path"],
)
def read_file(path: str) -> str:
    """
    A REAL tool (unlike search_web above) -- actually reads from disk.
    Demonstrates proper error handling: a missing file should NOT crash
    the whole agent loop, it should return an error string the LLM can react to.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# TOOL EXECUTION WITH ROBUST ERROR HANDLING
# ---------------------------------------------------------------------------
def execute_tool_call(tool_call) -> str:
    """
    Executes a single tool call safely, covering all three failure modes
    described at the top of this file. Always returns a string (never
    raises), because a tool result must be feedable back to the LLM no
    matter what happened.
    """
    tool_name = tool_call.function.name

    # Failure mode 1: unknown tool name (model hallucinated a tool that
    # doesn't exist in our registry).
    tool_fn = TOOL_REGISTRY.get(tool_name)
    if tool_fn is None:
        return f"ERROR: unknown tool '{tool_name}'. Available tools: {list(TOOL_REGISTRY.keys())}"

    # Failure mode 2: the arguments aren't valid JSON, or are missing
    # required fields. We check this BEFORE calling the function so a bad
    # call doesn't produce a confusing Python-level TypeError.
    try:
        tool_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        return f"ERROR: could not parse arguments as JSON: {e}"

    try:
        return str(tool_fn(**tool_args))
    except TypeError as e:
        # Usually means required args were missing or extra/unknown args
        # were passed -- a mismatch between what the model sent and what
        # the function signature expects.
        return f"ERROR: invalid arguments for '{tool_name}': {e}"
    except Exception as e:
        # Failure mode 3: the tool ran but threw an exception internally
        # (e.g. read_file on a path that doesn't exist).
        # We deliberately don't crash the agent loop -- we hand the error
        # back to the model as a string so it can decide what to do next
        # (e.g. try a different path, apologize to the user, etc.).
        return f"ERROR: tool '{tool_name}' raised an exception: {e}"


def run_agent_loop(user_task: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

    for turn in range(1, MAX_TURNS + 1):
        print(f"\n{'=' * 60}")
        print(f"[STEP {turn}] Sending {len(messages)} messages "
              f"({len(TOOLS_SCHEMA)} tools available)...")
        print(f"{'=' * 60}")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            **LLM_OPTIONS,
        )
        message = response.choices[0].message

        if message.tool_calls:
            print(f"[STEP {turn}] LLM requested {len(message.tool_calls)} tool call(s).")
            messages.append(message)

            for tool_call in message.tool_calls:
                print(f"  -> Tool requested: '{tool_call.function.name}' "
                      f"args={tool_call.function.arguments}")

                # All error handling now lives inside execute_tool_call,
                # keeping this loop body simple and readable.
                tool_result = execute_tool_call(tool_call)

                print(f"  <- Result: {tool_result[:200]}"
                      f"{'...' if len(tool_result) > 200 else ''}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
            continue

        print(f"[STEP {turn}] LLM gave a final answer (no tool call).")
        return message.content

    print("\n[WARNING] Max turns reached without a final answer.")
    return "(Agent did not finish within the turn limit.)"


if __name__ == "__main__":
    # A task that plausibly needs BOTH the calculator and the (stub) search
    # tool, so you can watch the model pick different tools across turns.
    task = (
        "Search the web for 'current agent harness best practices', then "
        "calculate 15% of 240, and combine both findings into one short summary."
    )
    print(f"USER TASK: {task}")

    result = run_agent_loop(task)

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(result)
    print(f"{'#' * 60}")
