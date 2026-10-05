"""
Module 10: Observability & Debugging
======================================
Goal: When something goes wrong deep inside a multi-turn, multi-tool agent
run, "read the print statements" doesn't scale -- you need a STRUCTURED,
SAVED record of exactly what happened, in what order, and how long each
step took. That's what a "trace" is.

New concepts:
  1. TRACING: every meaningful step (an LLM call, a tool call) becomes a
     structured event: {step number, type, input, output, duration, timestamp}.
     Unlike our earlier print() statements, this is machine-readable and
     persisted to disk -- you can load it later, diff two runs, or build a
     UI on top of it.
  2. STRUCTURED LOGGING: instead of loosely formatted print strings, every
     event is a well-defined dict, making it easy to filter/query
     ("show me all tool calls that took >2 seconds", "show me all errors").
  3. A TRACE VIEWER: a small function that reads a saved trace and prints a
     clean, readable timeline -- the debugging workflow you'd actually use
     after a failed run.

We use the same tool registry as earlier modules, but wrap the whole loop
in a Tracer that captures everything for later inspection.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
MODEL = "gemma4:e4b"

# Keep provider-specific options out of requests to models that may reject them.
LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

MAX_TURNS = 8
TRACE_FILE = Path(__file__).resolve().parent / "agent_trace.json"

SYSTEM_PROMPT = """You are a helpful assistant with access to tools:
calculate and search_web.
"""

# ---------------------------------------------------------------------------
# TOOL REGISTRY (same as earlier modules)
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
def calculate(expression: str) -> str:
    return str(eval(expression, {"__builtins__": {}}, {}))


@tool(
    description="Search the web for a query and return a short summary of results.",
    parameters={"query": {"type": "string", "description": "The search query string."}},
    required=["query"],
)
def search_web(query: str) -> str:
    return f"[STUB RESULT] Pretend web search results for: '{query}'."


def execute_tool_call_raw(tool_name: str, tool_args: dict) -> str:
    """Plain execution, no tracing here -- tracing wraps this from outside."""
    tool_fn = TOOL_REGISTRY.get(tool_name)
    if tool_fn is None:
        return f"ERROR: unknown tool '{tool_name}'."
    try:
        return str(tool_fn(**tool_args))
    except Exception as e:
        return f"ERROR: tool '{tool_name}' raised an exception: {e}"


# ---------------------------------------------------------------------------
# TRACER
# ---------------------------------------------------------------------------
class Tracer:
    """
    Collects structured events for one agent run. Each event is a plain
    dict, which makes the whole trace trivially JSON-serializable and easy
    to query later (e.g. `[e for e in trace if e["type"] == "tool_call" and e["duration_ms"] > 2000]`).
    """
    def __init__(self, run_id: str = None):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.events = []

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def record(self, event_type: str, step: int, input_data, output_data, duration_ms: float, **extra):
        event = {
            "run_id": self.run_id,
            "step": step,
            "type": event_type,
            "timestamp": self._now(),
            "input": input_data,
            "output": output_data,
            "duration_ms": round(duration_ms, 1),
            **extra,
        }
        self.events.append(event)
        # We still print a short line live, for immediate feedback -- but
        # the FULL detail lives in the saved trace, not just the terminal.
        print(f"[TRACE] step={step} type={event_type} duration={event['duration_ms']}ms")

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.events, f, indent=2, ensure_ascii=False)
        print(f"[TRACE] Saved {len(self.events)} events to '{path}'")


def run_agent_loop(user_task: str, tracer: Tracer) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

    for turn in range(1, MAX_TURNS + 1):
        print(f"\n{'=' * 60}")
        print(f"[STEP {turn}] Sending {len(messages)} messages to the LLM...")
        print(f"{'=' * 60}")

        start = time.monotonic()
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            **LLM_OPTIONS,
        )
        duration_ms = (time.monotonic() - start) * 1000
        message = response.choices[0].message

        # Trace the LLM call itself: what we sent (condensed) and what came back.
        tracer.record(
            event_type="llm_call",
            step=turn,
            input_data=f"{len(messages)} messages (last: {messages[-1].get('content', '')[:100] if isinstance(messages[-1], dict) else '...'})",
            output_data=(
                f"tool_calls={[tc.function.name for tc in message.tool_calls]}"
                if message.tool_calls else f"text={message.content[:150]}"
            ),
            duration_ms=duration_ms,
        )

        if message.tool_calls:
            messages.append(message)
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                start = time.monotonic()
                tool_result = execute_tool_call_raw(tool_name, tool_args)
                duration_ms = (time.monotonic() - start) * 1000

                # Trace the tool call as its own event, separate from the
                # LLM call that requested it -- this separation is exactly
                # what lets you later ask "was the slowness the LLM or the tool?"
                tracer.record(
                    event_type="tool_call",
                    step=turn,
                    input_data={"tool": tool_name, "args": tool_args},
                    output_data=tool_result,
                    duration_ms=duration_ms,
                    is_error=tool_result.startswith("ERROR:"),
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
            continue

        return message.content

    return "(Agent did not finish within the turn limit.)"


# ---------------------------------------------------------------------------
# TRACE VIEWER
# ---------------------------------------------------------------------------
def print_trace_summary(path: str):
    """
    Loads a saved trace file and prints a clean, human-readable timeline.
    This is the tool you'd reach for AFTER a run to understand what
    happened -- e.g. after a user reports "the agent gave a weird answer."
    """
    with open(path, "r", encoding="utf-8") as f:
        events = json.load(f)

    print(f"\n{'=' * 70}")
    print(f"TRACE SUMMARY ({len(events)} events, run_id={events[0]['run_id'] if events else 'n/a'})")
    print(f"{'=' * 70}")

    total_duration = sum(e["duration_ms"] for e in events)
    error_count = sum(1 for e in events if e.get("is_error"))

    for e in events:
        marker = "[ERR]" if e.get("is_error") else "     "
        print(f"{marker} [step {e['step']}] {e['type']:10s} "
              f"{e['duration_ms']:>8.1f}ms  |  in: {str(e['input'])[:60]}")
        print(f"                              out: {str(e['output'])[:60]}")

    print(f"{'-' * 70}")
    print(f"Total time across all events: {total_duration:.1f}ms | Errors: {error_count}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    tracer = Tracer()

    task = "Calculate 42*8, then search the web for 'agent tracing best practices', then summarize both."
    print(f"USER TASK: {task}")

    result = run_agent_loop(task, tracer)

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(result)
    print(f"{'#' * 60}")

    tracer.save(TRACE_FILE)
    print_trace_summary(TRACE_FILE)
