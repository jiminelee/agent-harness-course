"""
Module 4: State & Memory Management
=====================================
Goal: So far, our conversation history (`messages`) has grown forever.
That's fine for a 3-turn demo, but real agent tasks can run for dozens of
turns and eventually blow past the LLM's context window (and get expensive).

New concept: MEMORY COMPRESSION.
  - Short-term memory: the most recent N messages, kept verbatim so the
    model has full fidelity on what just happened.
  - Long-term memory: everything older gets periodically SUMMARIZED (using
    the LLM itself, in a separate call) down to a compact paragraph, which
    replaces the original messages in the history.

The tricky part: we must never cut the history in the MIDDLE of a
tool-call/tool-result transaction, because each "tool" role message must
remain associated with the assistant message that requested it. So we only
compress up to a SAFE BOUNDARY: the most
recent point where either an assistant message finished without requesting a
tool, or every tool call from an assistant message has received its result.

The registry pattern, error handling, and main loop shape carry over from
Module 3. To keep this memory lesson focused, this module uses only the
calculate and search_web tools.
"""

import json
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

MAX_TURNS = 20

# Memory management knobs:
MAX_MESSAGES_BEFORE_SUMMARY = 8   # trigger a compression once history grows past this
KEEP_RECENT_MESSAGES = 4          # always keep at least this many recent messages verbatim

SYSTEM_PROMPT = """You are a helpful assistant with access to tools:
calculate and search_web. Some older parts of this conversation
may have been summarized into a single message labeled [MEMORY SUMMARY] --
treat that summary as reliable background context.
"""

# ---------------------------------------------------------------------------
# TOOL REGISTRY (Module 3's pattern, with a smaller tool set for this lesson)
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
    """STUB -- see Module 3 notes. Replace with a real search API in production."""
    return f"[STUB RESULT] Pretend web search results for: '{query}'."


def execute_tool_call(tool_call) -> str:
    tool_name = tool_call.function.name
    tool_fn = TOOL_REGISTRY.get(tool_name)
    if tool_fn is None:
        return f"ERROR: unknown tool '{tool_name}'."
    try:
        tool_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        return f"ERROR: could not parse arguments as JSON: {e}"
    try:
        return str(tool_fn(**tool_args))
    except Exception as e:
        return f"ERROR: tool '{tool_name}' raised an exception: {e}"


# ---------------------------------------------------------------------------
# MEMORY COMPRESSION LOGIC (the new part in this module)
# ---------------------------------------------------------------------------
def message_to_text(msg) -> str:
    """
    Converts a message (which may be a plain dict OR an SDK message object
    with tool_calls) into a simple text line, purely for feeding into the
    summarizer prompt below. This is a display/summarization concern only --
    it is NOT what gets sent back to the main chat completion call.
    """
    if isinstance(msg, dict):
        role = msg.get("role")
        content = msg.get("content") or ""
        if role == "tool":
            return f"[tool result] {content}"
        return f"[{role}] {content}"
    else:
        # SDK message object (assistant message with possible tool_calls)
        role = msg.role
        if getattr(msg, "tool_calls", None):
            calls = ", ".join(tc.function.name for tc in msg.tool_calls)
            return f"[{role}] (requested tools: {calls})"
        return f"[{role}] {msg.content or ''}"


def find_safe_cut_index(messages) -> int:
    """
    Scans messages (skipping the system prompt at index 0) looking for the
    LAST index within the "older" portion of history where it is safe to
    cut. A safe boundary is either:
      - an assistant message that did not request tools, or
      - the final tool result belonging to an assistant's complete set of
        tool calls.

    Tracking tool_call IDs matters because one assistant message may request
    several tools. We must not cut after only some of their results.

    LEARNING NOTE: This is one of the more intricate functions in the course,
    and you do not need to understand every line to continue. The important
    idea is simply that it finds a safe history boundary while satisfying the
    OpenAI-compatible API's tool-call ordering requirements.

    Returns the index to cut AFTER (inclusive), or 0 if no safe point is
    found (meaning: don't compress anything yet).
    """
    # We only search within the "older" region -- i.e. excluding the most
    # recent KEEP_RECENT_MESSAGES, which must stay untouched regardless.
    boundary_search_end = len(messages) - KEEP_RECENT_MESSAGES

    safe_index = 0
    pending_tool_call_ids = set()

    for i in range(1, boundary_search_end):  # start at 1 to skip system prompt
        msg = messages[i]
        role = msg["role"] if isinstance(msg, dict) else msg.role
        tool_calls = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)

        if role == "assistant":
            if tool_calls:
                pending_tool_call_ids = {
                    call.get("id") if isinstance(call, dict) else call.id
                    for call in tool_calls
                }
            else:
                pending_tool_call_ids.clear()
                safe_index = i
            continue

        if role == "tool" and pending_tool_call_ids:
            tool_call_id = msg.get("tool_call_id") if isinstance(msg, dict) else msg.tool_call_id
            pending_tool_call_ids.discard(tool_call_id)
            if not pending_tool_call_ids:
                safe_index = i

    return safe_index


def compress_history(messages) -> list:
    """
    If history has grown past MAX_MESSAGES_BEFORE_SUMMARY, summarize the
    older portion (up to the last safe cut point) into a single compact
    message, and splice it back into the history in place of the originals.
    """
    if len(messages) <= MAX_MESSAGES_BEFORE_SUMMARY:
        return messages  # nothing to do yet

    cut_index = find_safe_cut_index(messages)
    if cut_index <= 0:
        print("[MEMORY] History is long, but no safe cut point found yet. Skipping compression this turn.")
        return messages

    old_portion = messages[1:cut_index + 1]      # everything to summarize (excluding system prompt)
    recent_portion = messages[cut_index + 1:]     # everything to keep verbatim

    print(f"[MEMORY] Compressing {len(old_portion)} old messages into a summary "
          f"(keeping {len(recent_portion)} recent messages verbatim)...")

    transcript = "\n".join(message_to_text(m) for m in old_portion)

    # We use a SEPARATE, throwaway LLM call to do the summarization itself.
    # This call has nothing to do with the main agent loop's tools/state --
    # it's just a plain text-in, text-out request.
    summary_response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Summarize the following agent conversation history "
                                           "concisely, keeping any concrete facts, numbers, or "
                                           "decisions that matter for continuing the task."},
            {"role": "user", "content": transcript},
        ],
        **LLM_OPTIONS,
    )
    summary_text = summary_response.choices[0].message.content

    print(f"[MEMORY] Summary produced ({len(summary_text)} chars):\n---\n{summary_text}\n---")

    summary_message = {"role": "user", "content": f"[MEMORY SUMMARY] {summary_text}"}

    # New history = system prompt + summary + untouched recent messages.
    return [messages[0], summary_message] + recent_portion


def run_agent_loop(user_task: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

    for turn in range(1, MAX_TURNS + 1):
        # Check and compress BEFORE sending, so the LLM call itself always
        # sees an already-trimmed history.
        messages = compress_history(messages)

        print(f"\n{'=' * 60}")
        print(f"[STEP {turn}] Sending {len(messages)} messages to the LLM...")
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
                print(f"  -> Tool requested: '{tool_call.function.name}' args={tool_call.function.arguments}")
                tool_result = execute_tool_call(tool_call)
                print(f"  <- Result: {tool_result[:200]}")
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
    # A multi-part task designed to run long enough to actually trigger
    # memory compression at least once, so you can watch [MEMORY] logs fire.
    task = (
        "Do the following one at a time, using tools where relevant: "
        "1) calculate 12*7, 2) search the web for 'agent memory patterns', "
        "3) calculate 340/4, 4) search the web for 'context window limits', "
        "5) calculate 99*3, then give me one final summary of all 5 results."
    )
    print(f"USER TASK: {task}")

    result = run_agent_loop(task)

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(result)
    print(f"{'#' * 60}")
