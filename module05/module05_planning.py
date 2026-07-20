"""
Module 5: Planning & Task Decomposition
==========================================
Goal: Up to now, our agent has handled tasks turn-by-turn, reactively --
it never explicitly thinks "here is my overall plan" before diving in.
For complex, multi-part tasks this reactive style can wander or forget
the big picture.

New pattern: PLAN-THEN-EXECUTE.
  Step 1 (PLAN):    Ask the LLM to break the user's task into an ordered
                     list of concrete subtasks, returned as structured JSON
                     (not free text) so our code can reliably loop over it.
  Step 2 (EXECUTE):  Run each subtask through a small tool-calling loop
                     (same mechanics as Module 3), one subtask at a time,
                     collecting each subtask's result.
  Step 3 (SYNTHESIZE): Ask the LLM to combine all subtask results into one
                     coherent final answer for the user.

This is the same "plan -> execute -> synthesize" shape used by many
production agent frameworks (often called "planner/executor" or
"orchestrator/worker" -- Module 10 will build on this further with actual
separate sub-agents).
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

MAX_TURNS_PER_SUBTASK = 4  # each subtask gets its own small tool-calling loop

# ---------------------------------------------------------------------------
# TOOL REGISTRY (same focused calculate/search_web set as Module 4)
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
# STEP 1: PLANNING
# ---------------------------------------------------------------------------
def generate_plan(user_task: str) -> list:
    """
    Asks the LLM to decompose the user's task into an ordered list of
    concrete subtasks, returned as JSON so our Python code can reliably
    iterate over it (no fragile text parsing needed).
    """
    print(f"\n{'=' * 60}")
    print("[PLAN] Asking the LLM to decompose the task into subtasks...")
    print(f"{'=' * 60}")

    planning_prompt = f"""Break the following task into a short ordered list of
concrete subtasks that, when completed in order, fully accomplish the task.
Keep the list as small as possible (2-5 subtasks). Respond with ONLY a JSON
array of strings, nothing else -- no markdown, no explanation.

Task: {user_task}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": planning_prompt}],
        **LLM_OPTIONS,
    )
    raw = response.choices[0].message.content.strip()

    # Models sometimes wrap JSON in markdown code fences despite instructions
    # not to -- strip those defensively so json.loads doesn't choke on them.
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw

    try:
        subtasks = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: if the model didn't cooperate with JSON formatting,
        # just treat the whole task as a single subtask rather than crashing.
        print(f"[PLAN] Could not parse plan as JSON, falling back to single-step plan. Raw: {raw}")
        subtasks = [user_task]

    print(f"[PLAN] Decomposed into {len(subtasks)} subtask(s):")
    for i, st in enumerate(subtasks, 1):
        print(f"  {i}. {st}")

    return subtasks


# ---------------------------------------------------------------------------
# STEP 2: EXECUTION (one small tool-calling loop per subtask)
# ---------------------------------------------------------------------------
def execute_subtask(subtask: str, subtask_number: int) -> str:
    """
    Runs a single subtask through its own small agent loop (same
    tool-calling mechanics as Module 3), completely independent of other
    subtasks' conversation history. This keeps each subtask's context small
    and focused -- a form of memory management by ISOLATION rather than
    compression (contrast with Module 4's approach).
    """
    print(f"\n{'-' * 60}")
    print(f"[EXECUTE {subtask_number}] Working on subtask: {subtask}")
    print(f"{'-' * 60}")

    messages = [
        {"role": "system", "content": "You are executing one specific subtask of a larger plan. "
                                       "Use tools if helpful. Give a concise final result."},
        {"role": "user", "content": subtask},
    ]

    for turn in range(1, MAX_TURNS_PER_SUBTASK + 1):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            **LLM_OPTIONS,
        )
        message = response.choices[0].message

        if message.tool_calls:
            print(f"  [subtask {subtask_number}, turn {turn}] requested "
                  f"{len(message.tool_calls)} tool call(s)")
            messages.append(message)
            for tool_call in message.tool_calls:
                tool_result = execute_tool_call(tool_call)
                print(f"    -> {tool_call.function.name}({tool_call.function.arguments}) => {tool_result[:120]}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
            continue

        print(f"  [subtask {subtask_number}] result: {message.content[:200]}")
        return message.content

    return "(subtask did not finish within its turn limit)"


# ---------------------------------------------------------------------------
# STEP 3: SYNTHESIS
# ---------------------------------------------------------------------------
def synthesize_final_answer(user_task: str, subtask_results: list) -> str:
    """
    Combines all subtask results into one coherent answer. This is a plain
    text-in/text-out LLM call, no tools needed here -- by this point all the
    factual legwork is already done.
    """
    print(f"\n{'=' * 60}")
    print("[SYNTHESIZE] Combining subtask results into a final answer...")
    print(f"{'=' * 60}")

    results_block = "\n".join(
        f"Subtask {i+1}: {r}" for i, r in enumerate(subtask_results)
    )
    synthesis_prompt = f"""Original task: {user_task}

Here are the results of each subtask that was completed to accomplish it:
{results_block}

Write one clear, concise final answer for the user that combines these
results appropriately.
"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": synthesis_prompt}],
        **LLM_OPTIONS,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# TOP-LEVEL ORCHESTRATION
# ---------------------------------------------------------------------------
def run_plan_and_execute(user_task: str) -> str:
    plan = generate_plan(user_task)

    subtask_results = []
    for i, subtask in enumerate(plan, 1):
        result = execute_subtask(subtask, i)
        subtask_results.append(result)

    return synthesize_final_answer(user_task, subtask_results)


if __name__ == "__main__":
    task = (
        "Figure out 18% of 250, look up 'agent harness design patterns', "
        "and figure out how many days are in 6 weeks, then summarize all "
        "three findings together."
    )
    print(f"USER TASK: {task}")

    result = run_plan_and_execute(task)

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(result)
    print(f"{'#' * 60}")
