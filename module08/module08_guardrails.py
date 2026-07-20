"""
Module 8: Guardrails & Safety
===============================
Goal: So far, ANY tool the model requests gets executed immediately and
automatically. That's fine for read-only tools like calculate/search_web,
but dangerous for tools that MODIFY something (delete a file, send an
email, spend money, etc.). This module adds three concrete safety layers:

  1. HUMAN-IN-THE-LOOP CONFIRMATION: tools marked as "dangerous" pause the
     loop and require an explicit human "yes" before running -- the model
     cannot bypass this by itself.
  2. INPUT VALIDATION: before even asking for confirmation, we validate the
     tool's arguments strictly (right types, no obviously malicious paths,
     etc.) so garbage/malicious input is rejected early.
  3. AUDIT LOGGING: every dangerous action attempt (approved, denied, or
     blocked by validation) is recorded in an audit log, independent of
     whether it succeeded -- this is critical for debugging and compliance
     in a real deployment.

We go back to the synchronous client (like Modules 1-6) here since
guardrails are a orthogonal concern to async/parallel execution (Module 7)
-- in a real system you'd combine both.
"""

import json
import os
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
MODULE_DIR = Path(__file__).resolve().parent

SYSTEM_PROMPT = """You are a helpful assistant with access to tools:
calculate, search_web, and delete_file. delete_file is a DANGEROUS
operation and will require human confirmation -- explain to the user
clearly what you are about to delete and why before calling it.
"""

# ---------------------------------------------------------------------------
# AUDIT LOG
# ---------------------------------------------------------------------------
# In a real system this would go to a proper logging service / database,
# not an in-memory list -- but the PRINCIPLE is the same: every sensitive
# action attempt gets a permanent, timestamped record, regardless of outcome.
AUDIT_LOG = []


def audit(event: str, **details):
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **details}
    AUDIT_LOG.append(entry)
    print(f"[AUDIT] {entry}")


# ---------------------------------------------------------------------------
# TOOL REGISTRY, EXTENDED WITH A "dangerous" FLAG
# ---------------------------------------------------------------------------
TOOL_REGISTRY = {}
TOOLS_SCHEMA = []
DANGEROUS_TOOLS = set()  # names of tools that require human confirmation


def tool(description: str, parameters: dict, required: list, dangerous: bool = False):
    """
    Same registry decorator as earlier modules, with one new parameter:
    `dangerous`. Marking a tool dangerous=True is what triggers the
    confirmation gate in execute_tool_call() below -- everything else about
    a dangerous tool (its schema, its implementation) looks completely
    normal to the model, on purpose. The model doesn't need to know it's
    "asking permission" -- the harness enforces that regardless of what the
    model does or doesn't say.
    """
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
        if dangerous:
            DANGEROUS_TOOLS.add(fn.__name__)
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


@tool(
    description="Permanently delete a file at the given path. THIS CANNOT BE UNDONE.",
    parameters={"path": {"type": "string", "description": "Path to the file to delete."}},
    required=["path"],
    dangerous=True,   # <-- this is what makes it require confirmation
)
def delete_file(path: str) -> str:
    target = (MODULE_DIR / path).resolve()
    os.remove(target)
    return f"Deleted file: {path}"


# ---------------------------------------------------------------------------
# INPUT VALIDATION
# ---------------------------------------------------------------------------
def validate_tool_args(tool_name: str, tool_args: dict) -> str | None:
    """
    Runs basic sanity checks BEFORE we even consider confirmation or
    execution. Returns an error string if validation fails, or None if the
    arguments look acceptable. This is intentionally simple (a real system
    would have much more thorough validation per tool), but demonstrates
    the principle: never trust model-generated arguments blindly, even for
    tools that aren't "dangerous."
    """
    if tool_name == "delete_file":
        path = tool_args.get("path", "")
        # Reject obviously unsafe patterns -- path traversal, absolute
        # paths outside an expected sandbox directory, etc. A real system
        # would resolve the path and check it's within an allowed root.
        target = (MODULE_DIR / path).resolve()
        if Path(path).is_absolute() or target.parent != MODULE_DIR:
            return f"ERROR: rejected suspicious path '{path}' (path traversal or absolute path not allowed)."
        if not path.strip():
            return "ERROR: empty path not allowed."

    if tool_name == "calculate":
        expr = tool_args.get("expression", "")
        if len(expr) > 200:
            return "ERROR: expression too long, rejected."

    return None  # looks fine


# ---------------------------------------------------------------------------
# HUMAN-IN-THE-LOOP CONFIRMATION
# ---------------------------------------------------------------------------
def request_human_confirmation(tool_name: str, tool_args: dict) -> bool:
    """
    Pauses execution and asks a REAL human (via terminal input) to approve
    or deny a dangerous action. This is the actual safety boundary -- no
    matter how convincingly the model argues for it, dangerous tools cannot
    run without this step returning True.
    """
    print(f"\n{'!' * 60}")
    print(f"CONFIRMATION REQUIRED: the agent wants to run '{tool_name}'")
    print(f"Arguments: {tool_args}")
    print(f"{'!' * 60}")
    answer = input("Approve this action? [y/N]: ").strip().lower()
    return answer == "y"


def execute_tool_call(tool_call) -> str:
    tool_name = tool_call.function.name
    tool_fn = TOOL_REGISTRY.get(tool_name)

    if tool_fn is None:
        audit("unknown_tool_requested", tool_name=tool_name)
        return f"ERROR: unknown tool '{tool_name}'."

    try:
        tool_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        audit("invalid_json_args", tool_name=tool_name, error=str(e))
        return f"ERROR: could not parse arguments as JSON: {e}"

    # STEP 1: validation, before we even think about confirmation.
    validation_error = validate_tool_args(tool_name, tool_args)
    if validation_error:
        audit("validation_rejected", tool_name=tool_name, args=tool_args, reason=validation_error)
        return validation_error

    # STEP 2: confirmation gate, only for tools marked dangerous.
    if tool_name in DANGEROUS_TOOLS:
        approved = request_human_confirmation(tool_name, tool_args)
        audit("confirmation_decision", tool_name=tool_name, args=tool_args, approved=approved)
        if not approved:
            return f"DENIED: the human operator did not approve running '{tool_name}' with {tool_args}."

    # STEP 3: actually execute, now that validation + (if needed) approval passed.
    try:
        result = str(tool_fn(**tool_args))
        audit("tool_executed", tool_name=tool_name, args=tool_args, success=True)
        return result
    except Exception as e:
        audit("tool_exception", tool_name=tool_name, args=tool_args, error=str(e))
        return f"ERROR: tool '{tool_name}' raised an exception: {e}"


def run_agent_loop(user_task: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

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
            print(f"[STEP {turn}] LLM requested {len(message.tool_calls)} tool call(s).")
            messages.append(message)
            for tool_call in message.tool_calls:
                print(f"  -> Tool requested: '{tool_call.function.name}' "
                      f"args={tool_call.function.arguments}")
                tool_result = execute_tool_call(tool_call)
                print(f"  <- Result: {tool_result[:150]}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
            continue

        print(f"[STEP {turn}] LLM gave a final answer (no tool call).")
        return message.content

    return "(Agent did not finish within the turn limit.)"


if __name__ == "__main__":
    # First, create a harmless throwaway file so the agent has something
    # real (but low-stakes) to delete, to demonstrate the confirmation flow.
    demo_path = "scratch_demo_file.txt"
    with open(MODULE_DIR / demo_path, "w") as f:
        f.write("This is a throwaway file created for Module 8's demo.\n")

    task = f"Please delete the file at '{demo_path}' since we no longer need it."
    print(f"USER TASK: {task}")

    result = run_agent_loop(task)

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(result)
    print(f"{'#' * 60}")

    print(f"\nFull audit log ({len(AUDIT_LOG)} entries):")
    for entry in AUDIT_LOG:
        print(f"  {entry}")
