"""
Module 2: Your First Tool
==========================
Goal: Extend the Module 1 loop with ONE real tool: a calculator.

Key new concept: "function calling" / "tool calling".
Instead of the model outputting a text marker like "TASK_COMPLETE" and us
parsing it by hand, we now describe a TOOL to the model using a JSON schema.
The model can then decide to call that tool, and the API response comes back
in a structured format (tool_calls) instead of free text.

The loop shape from Module 1 stays exactly the same:
    1. Send messages to the LLM.
    2. Get a response.
    3. If it's a final answer -> stop.
    4. If it's a tool call -> execute the tool, feed the result back, repeat.

This is the same OpenAI-compatible client as Module 1, so it still works
with OpenAI's real API or a local Ollama server (as long as the specific
Ollama model you use supports tool calling -- e.g. gemma4:e4b does).
"""

import json
from openai import OpenAI

# ---------------------------------------------------------------------------
# CONFIGURATION (same as Module 1 -- change these to switch providers)
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:11434/v1"   # or "https://api.openai.com/v1"
API_KEY = "ollama"                        # or your real OpenAI key
MODEL = "gemma4:e4b"                       # or "gpt-4o-mini" etc.

# Keep provider-specific options out of requests to models that may reject them.
LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

MAX_TURNS = 6

SYSTEM_PROMPT = """You are a helpful assistant with access to tools.
Use the calculate tool whenever the user's task requires arithmetic.
Only give your final answer once you have all the information you need.
"""


# ---------------------------------------------------------------------------
# STEP A: Define the tool itself (the actual Python function that runs)
# ---------------------------------------------------------------------------
def calculate(expression: str) -> str:
    """
    Safely evaluate a basic arithmetic expression, e.g. "12 * (3 + 4)".

    We use Python's eval() here ONLY for teaching simplicity, restricted to
    a tiny safe namespace (no builtins). In a real production harness you
    would use a proper math expression parser instead of eval, because eval
    is dangerous with untrusted input even when restricted like this.
    """
    try:
        # `{"__builtins__": {}}` strips away dangerous built-in functions
        # (like open, import, etc.) so the eval is a bit safer, though still
        # not something you'd want to expose to fully untrusted users.
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        # Tools can fail! Returning the error as a string lets the LLM see
        # what went wrong and decide how to react (e.g. retry, ask user).
        return f"ERROR: could not evaluate '{expression}': {e}"


# ---------------------------------------------------------------------------
# STEP B: Describe the tool to the LLM using the OpenAI tool-calling schema.
# This is the "contract" the model reads to know the tool exists, what it's
# called, what it does, and what arguments it expects.
# ---------------------------------------------------------------------------
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a basic arithmetic expression and return the numeric result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A Python-style arithmetic expression, e.g. '2 + 2' or '(5*3)/2'.",
                    }
                },
                "required": ["expression"],
            },
        },
    }
]

# Registry mapping tool name -> actual Python function to call.
# This pattern (a dict lookup) is what Module 3 will expand into a full
# "tool registry" system when we add many more tools.
TOOL_REGISTRY = {
    "calculate": calculate,
}


def run_agent_loop(user_task: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

    for turn in range(1, MAX_TURNS + 1):
        print(f"\n{'=' * 60}")
        print(f"[STEP {turn}] Sending {len(messages)} messages to the LLM (tools enabled)...")
        print(f"{'=' * 60}")

        # The key difference from Module 1: we pass `tools=TOOLS_SCHEMA`.
        # This tells the API "here are the functions the model is allowed
        # to call if it wants to."
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            **LLM_OPTIONS,
        )
        message = response.choices[0].message

        # Case 1: the model wants to call one or more tools.
        if message.tool_calls:
            print(f"[STEP {turn}] LLM requested {len(message.tool_calls)} tool call(s).")

            # We must append the assistant's tool-call message to history
            # BEFORE appending the tool results, so the conversation stays
            # in the correct order the API expects.
            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"  -> Calling tool '{tool_name}' with args: {tool_args}")

                # Look up and run the actual Python function.
                tool_fn = TOOL_REGISTRY.get(tool_name)
                if tool_fn is None:
                    tool_result = f"ERROR: unknown tool '{tool_name}'"
                else:
                    tool_result = tool_fn(**tool_args)

                print(f"  <- Tool result: {tool_result}")

                # Feed the tool's result back into the conversation with
                # role="tool", linked to the specific tool_call.id so the
                # model knows which call this result answers.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result),
                })

            # Loop again: now the model gets to see the tool result and
            # decide what to do next (call another tool, or give a final answer).
            continue

        # Case 2: the model gave a normal text answer -- no tool call means
        # it considers itself done (this is the standard convention for
        # tool-calling APIs: absence of tool_calls == final answer).
        print(f"[STEP {turn}] LLM gave a final answer (no tool call).")
        return message.content

    print("\n[WARNING] Max turns reached without a final answer.")
    return "(Agent did not finish within the turn limit.)"


if __name__ == "__main__":
    # A task that specifically requires arithmetic, so you can watch the
    # model choose to call the calculator tool instead of guessing the answer.
    task = "What is (438 * 12) - 57, divided by 3? Give me just the final number."
    print(f"USER TASK: {task}")

    result = run_agent_loop(task)

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(result)
    print(f"{'#' * 60}")
