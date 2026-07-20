"""
Module 6: Error Recovery & Self-Correction
=============================================
Goal: So far, tool errors just got fed back to the model with no limit --
a model could theoretically retry the same failing tool call forever
(within MAX_TURNS). This module adds two real safety/quality mechanisms:

  1. RETRY LIMITING: track how many times each tool has failed
     CONSECUTIVELY. After a small limit, we stop letting the model retry
     blindly and instead tell it to give up on that approach.

  2. REFLECTION (self-correction): once the model produces what it thinks
     is a final answer, we don't return it immediately. Instead we run a
     SEPARATE "critic" LLM call that checks the answer against the original
     task. If the critic finds a problem, we feed that critique back to the
     model as a new instruction to revise -- for a bounded number of rounds.

These two mechanisms cover the two main ways agents fail:
  - Failing at the TOOL level (a single action didn't work).
  - Failing at the ANSWER level (all actions "worked" but the final
    synthesis is wrong, incomplete, or doesn't answer the actual question).
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

MAX_TURNS = 10
MAX_CONSECUTIVE_TOOL_FAILURES = 2   # per tool name, before we tell the model to stop trying it
MAX_REFLECTION_ROUNDS = 2           # how many times we'll ask the model to self-correct

SYSTEM_PROMPT = """You are a helpful assistant with access to tools:
calculate and search_web. If a tool keeps failing, try a
different approach instead of repeating the exact same call.
"""

# ---------------------------------------------------------------------------
# TOOL REGISTRY (same focused calculate/search_web set as Modules 4/5)
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
    # Deliberately unmodified from earlier modules -- eval() will raise for
    # malformed expressions, which is exactly what lets us demo retry logic.
    return str(eval(expression, {"__builtins__": {}}, {}))


@tool(
    description="Search the web for a query and return a short summary of results.",
    parameters={"query": {"type": "string", "description": "The search query string."}},
    required=["query"],
)
def search_web(query: str) -> str:
    """STUB -- see Module 3 notes."""
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
# NEW: RETRY TRACKING
# ---------------------------------------------------------------------------
class FailureTracker:
    """
    Tracks CONSECUTIVE failures per tool name. A success resets the
    counter for that tool back to zero -- we only care about a tool
    repeatedly failing in a row, not its failures scattered across an
    otherwise-successful conversation.
    """
    def __init__(self, max_consecutive: int):
        self.max_consecutive = max_consecutive
        self.counts = {}  # tool_name -> consecutive failure count

    def record(self, tool_name: str, succeeded: bool):
        if succeeded:
            self.counts[tool_name] = 0
        else:
            self.counts[tool_name] = self.counts.get(tool_name, 0) + 1

    def is_exhausted(self, tool_name: str) -> bool:
        return self.counts.get(tool_name, 0) >= self.max_consecutive


def run_tool_calling_loop(messages: list, failure_tracker: FailureTracker) -> str:
    """
    The familiar tool-calling loop from Module 3, now with retry-limit
    awareness baked in. Returns the final text answer once the model stops
    requesting tools.
    """
    for turn in range(1, MAX_TURNS + 1):
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
            messages.append(message)
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name

                # If this tool has already failed too many times in a row,
                # short-circuit WITHOUT even calling it again -- this is
                # what actually prevents wasted API calls / infinite retries.
                if failure_tracker.is_exhausted(tool_name):
                    print(f"  -> Skipping '{tool_name}': too many consecutive failures.")
                    tool_result = (
                        f"ERROR: '{tool_name}' has failed "
                        f"{failure_tracker.max_consecutive} times in a row. "
                        f"Do not retry it the same way -- try a different "
                        f"approach or inform the user it's not possible."
                    )
                else:
                    print(f"  -> Calling '{tool_name}' with args={tool_call.function.arguments}")
                    tool_result = execute_tool_call(tool_call)
                    succeeded = not tool_result.startswith("ERROR:")
                    failure_tracker.record(tool_name, succeeded)
                    status = "OK" if succeeded else f"FAILED ({failure_tracker.counts[tool_name]}x in a row)"
                    print(f"  <- [{status}] {tool_result[:150]}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
            continue

        print(f"[STEP {turn}] LLM gave a final answer (no tool call).")
        return message.content

    return "(Agent did not finish within the turn limit.)"


# ---------------------------------------------------------------------------
# NEW: REFLECTION / SELF-CORRECTION
# ---------------------------------------------------------------------------
def critique_answer(user_task: str, answer: str) -> dict:
    """
    A separate LLM call acting purely as a CRITIC -- it does not have tools
    and does not know about the agent's internal process, only the original
    task and the proposed answer. This separation matters: a model
    critiquing its own freshly-generated answer in the SAME context tends to
    just agree with itself, so we ask for the critique with fresh eyes and
    structured JSON output.
    """
    print(f"\n{'=' * 60}")
    print("[REFLECT] Critiquing the proposed answer...")
    print(f"{'=' * 60}")

    critique_prompt = f"""Original task: {user_task}

Proposed answer: {answer}

Does this answer fully and correctly address the task? Respond with ONLY a
JSON object: {{"passes": true or false, "feedback": "short explanation"}}
"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": critique_prompt}],
        **LLM_OPTIONS,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw

    try:
        verdict = json.loads(raw)
    except json.JSONDecodeError:
        # If the critic itself fails to format correctly, default to
        # "passes" so a broken critic doesn't trap the agent in an infinite
        # revision loop.
        print(f"[REFLECT] Could not parse critique JSON, defaulting to pass. Raw: {raw}")
        verdict = {"passes": True, "feedback": ""}

    print(f"[REFLECT] passes={verdict.get('passes')} feedback={verdict.get('feedback')}")
    return verdict


def run_agent_with_self_correction(user_task: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]
    failure_tracker = FailureTracker(MAX_CONSECUTIVE_TOOL_FAILURES)

    answer = run_tool_calling_loop(messages, failure_tracker)

    for round_num in range(1, MAX_REFLECTION_ROUNDS + 1):
        verdict = critique_answer(user_task, answer)
        if verdict.get("passes"):
            print(f"[REFLECT] Answer passed on round {round_num}. Returning it.")
            return answer

        print(f"[REFLECT] Answer failed critique (round {round_num}). Asking model to revise...")
        # Feed the critique back in as a new user turn and let the model
        # (with its tools still available) try again.
        messages.append({"role": "assistant", "content": answer})
        messages.append({
            "role": "user",
            "content": f"A reviewer found an issue with your last answer: "
                       f"{verdict.get('feedback')}. Please revise your answer accordingly.",
        })
        answer = run_tool_calling_loop(messages, failure_tracker)

    print("[REFLECT] Max reflection rounds reached. Returning best available answer.")
    return answer


if __name__ == "__main__":
    # This expression is intentionally malformed to demonstrate the retry
    # limiter: eval() will raise on it every single time, so you should see
    # the tool fail twice and then get short-circuited without a 3rd call.
    task = "Calculate the result of '5 +' (yes, that's intentionally broken), then explain what happened."
    print(f"USER TASK: {task}")

    result = run_agent_with_self_correction(task)

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(result)
    print(f"{'#' * 60}")
